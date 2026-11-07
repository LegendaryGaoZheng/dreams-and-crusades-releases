"""Read-only, stdlib JFR/frame diagnostics; Python 3.9+.

python -B _five/analyze_jfr_frames.py RUN --top 5
python -B _five/analyze_jfr_frames.py RUN --input-json exported-jfr.json
python -B _five/analyze_jfr_frames.py --self-test

Normal use invokes jfr print, NOT the game. --input-json and --self-test never
invoke JFR. Only stdout JSON is written; JFR stderr inherits the terminal.
No offset is fitted to the opaque frame clock. Correlation requires independently
compatible PHASE log timestamps AND actual JFR/frame range overlap. Time-only log
prefixes verify time-of-day, not a separate date. Default log timezone is the
machine's local timezone; use --log-utc-offset +08:00 when analyzing elsewhere.
"""
import argparse
from bisect import bisect_left
from collections import Counter
from datetime import datetime, timedelta, timezone
import io
import json
import math
from pathlib import Path
import re
import subprocess
import sys

JFR = r'C:\Program Files\Eclipse Adoptium\jdk-24.0.2.12-hotspot\bin\jfr.exe'
EVENTS = ('jdk.ExecutionSample', 'jdk.NativeMethodSample', 'jdk.GCPhasePause',
          'jdk.GarbageCollection', 'jdk.ThreadPark', 'jdk.JavaMonitorEnter',
          'jdk.JavaMonitorWait', 'jdk.SafepointBegin', 'jdk.SafepointStateSynchronization',
          'jdk.SafepointCleanup', 'jdk.SafepointCleanupTask', 'jdk.SafepointEnd')
SAMPLES = set(EVENTS[:2])
LIMITATIONS = [
    'Samples are observations, NOT wall-time shares, causal attribution or predicted gains.',
    'Zero/missing samples/events cannot exclude GPU stalls, GC, native work or unrecorded events.',
    'Duration overlap is clipped to each window. GC/safepoint and nested events overlap: never add their totals.',
    'GarbageCollection duration includes concurrent work; it is NOT a stop-the-world pause.',
    'Phase windows span recorded frame intervals; boundary intervals belong to the recorded previous phase.',
    'JFR event time ranges are observed ranges, not proof of recording/settings completeness.',
    'ThreadPark/monitor events on other threads are context, not Render thread blocking evidence.',
    'Stack classifications are path hints only; only explicit GL compile/link entrypoints get shader_GL_compile_link.',
    'Time compatibility is necessary, not proof that an opaque clock is epoch; no offset fitting is performed.',
    'Bounded stack/detail/interval output may truncate; affected counters explicitly disclose this.',
]


def number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def stream_events(stream, chunk_size=65536, max_event_chars=4 * 1024 * 1024):
    """Incrementally decode ONE event, never the entire JFR JSON.

    Accept the standard jfr print {recording:{events:[...]}} envelope or a bare
    fixture array. Strict envelope/tail and separators reject truncated exports.
    Memory is bounded by max_event_chars plus a chunk; oversized events fail.
    """
    decoder = json.JSONDecoder()
    buf, eof = '', False

    def more():
        nonlocal buf, eof
        text = stream.read(chunk_size)
        if text:
            buf += text
        else:
            eof = True

    envelope = None
    while envelope is None:
        more()
        buf = buf.lstrip('\ufeff \t\r\n')
        if buf.startswith('['):
            envelope, buf = 'array', buf[1:]
        else:
            match = re.match(r'\{\s*"recording"\s*:\s*\{\s*"events"\s*:\s*\[', buf)
            if match:
                envelope, buf = 'jfr', buf[match.end():]
            elif eof or len(buf) > 65536:
                raise ValueError('unsupported/truncated JFR JSON envelope')
    first = True
    while True:
        buf = buf.lstrip()
        while not buf and not eof:
            more()
            buf = buf.lstrip()
        if buf.startswith(']'):
            buf = buf[1:]
            break
        if not first:
            if not buf.startswith(','):
                raise ValueError('missing event separator or truncated events array')
            buf = buf[1:].lstrip()
        while True:
            # A comma can be the last byte of a chunk; a refill may start with
            # indentation. raw_decode does not skip leading JSON whitespace.
            buf = buf.lstrip()
            if len(buf) > max_event_chars + chunk_size:
                raise ValueError('event exceeds bounded parser limit')
            try:
                event, end = decoder.raw_decode(buf)
                if end > max_event_chars:
                    raise ValueError('event exceeds bounded parser limit')
                break
            except json.JSONDecodeError as exc:
                if eof:
                    raise ValueError('malformed/truncated event JSON') from exc
                more()
        if not isinstance(event, dict):
            raise ValueError('event must be an object')
        yield event
        buf = buf[end:]
        first = False
    while not eof:
        if len(buf) > 65536:
            raise ValueError('unexpected oversized JSON trailer')
        more()
    if not re.fullmatch(r'\s*' if envelope == 'array' else r'\s*\}\s*\}\s*', buf):
        raise ValueError('invalid JFR JSON trailer')


def timestamp_ms(value):
    if not isinstance(value, str):
        raise ValueError('missing ISO event timestamp')
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        raise ValueError('JFR timestamp has no UTC offset')
    return dt.timestamp() * 1000


def duration_ms(value):
    # jfr print --json emits ISO-8601 Duration strings, e.g. PT0.002S.
    if not isinstance(value, str):
        raise ValueError('duration is not an ISO Duration string')
    m = re.fullmatch(r'PT(?:(\d+(?:\.\d+)?)H)?(?:(\d+(?:\.\d+)?)M)?(?:(\d+(?:\.\d+)?)S)?', value)
    if not m or not any(m.groups()):
        raise ValueError('unsupported duration: ' + value)
    return sum(float(v or 0) * scale for v, scale in zip(m.groups(), (3600000, 60000, 1000)))


def thread_name(thread):
    return (thread.get('javaName') or thread.get('osName') or '<unknown>') if isinstance(thread, dict) else '<unknown>'


def stack_of(values):
    trace = values.get('stackTrace') or {}
    if not isinstance(trace, dict):
        return (), False
    out = []
    for frame in (trace.get('frames') or [])[:32]:
        method = frame.get('method') or {}
        cls = method.get('type') or {}
        name = cls.get('name', '?') if isinstance(cls, dict) else str(cls)
        out.append(name.replace('/', '.') + '.' + str(method.get('name', '?')))
    return tuple(out), trace.get('truncated') is True


def categories(stack):
    text = ' '.join(stack).lower()
    rules = {
        'shader_GL_compile_link': r'\b(?:ngl|gl)(?:compileshader|linkprogram)\b',
        'GLsync_wait_path': r'(?:glclientwaitsync|glwaitsync|glfinish|fence.*wait)',
        'buffer_upload_path': r'(?:glbuffersubdata|glbufferdata|glmapbuffer|gltexsubimage|upload|stagingbuffer)',
        'world_generation_path': r'(?:chunkgenerator|noisebasedchunk|worldgen|chunkstatus|surfacebuilder)',
        'meshing_path': r'(?:meshing|chunkbuilder|chunkbuild|rebuildtask|sectioncompiler|blockrenderer)',
    }
    found = [name for name, pattern in rules.items() if re.search(pattern, text)]
    return found or ['other_or_unknown']


def overlap(a, b, c, d):
    return max(0., min(b, d) - max(a, c))


def add_union(intervals, start, end, cap=4096):
    """Maintain disjoint clipped intervals; bounded, exact until cap is reached."""
    if end <= start:
        return True
    first = bisect_left(intervals, (start, -math.inf))
    if first and intervals[first - 1][1] >= start:
        first -= 1
    last = first
    while last < len(intervals) and intervals[last][0] <= end:
        lo, hi = intervals[last]
        start, end = min(start, lo), max(end, hi)
        last += 1
    if len(intervals) - (last - first) + 1 > cap:
        return False
    intervals[first:last] = [(start, end)]
    return True


def log_anchors(lines, tz=None, tolerance_ms=2000):
    anchors, errors = [], []
    for lineno, line in enumerate(lines, 1):
        marker = re.search(r'\[PERF2\]\s+PHASE\s+(\{.*\})', line)
        if not marker:
            continue
        try:
            payload = json.loads(marker[1])
            clock = payload['clock_ms']
            if not number(clock):
                raise ValueError('invalid clock_ms')
            # Date-bearing prefixes are checked in addition to time-of-day.
            prefix = line[:marker.start()]
            tm = re.search(r'(?<!\d)(\d{2}):(\d{2}):(\d{2})(?:[.,](\d{1,3}))?', prefix)
            if not tm:
                raise ValueError('no log time prefix')
            dt = datetime.fromtimestamp(clock / 1000, tz=tz).astimezone(tz)
            h, m, s = map(int, tm.groups()[:3])
            if h > 23 or m > 59 or s > 59:
                raise ValueError('invalid log time')
            log_ms = ((h * 60 + m) * 60 + s) * 1000 + int((tm[4] or '0').ljust(3, '0'))
            clock_ms = ((dt.hour * 60 + dt.minute) * 60 + dt.second) * 1000 + dt.microsecond / 1000
            diff = abs(clock_ms - log_ms)
            diff = min(diff, 86400000 - diff)
            date = re.search(r'(?<!\d)(\d{4})[-/](\d{2})[-/](\d{2})(?!\d)', prefix)
            if date and tuple(map(int, date.groups())) != (dt.year, dt.month, dt.day):
                raise ValueError('log date incompatible with clock candidate')
            if diff > tolerance_ms:
                raise ValueError('log time incompatible with clock candidate')
            anchors.append({'phase': payload['phase'], 'clock_ms': clock, 'line': lineno,
                            'difference_ms': diff, 'date_checked': bool(date)})
        except (ValueError, KeyError, TypeError, OverflowError, OSError) as exc:
            errors.append('PHASE line %d: %s' % (lineno, exc))
    if not anchors:
        errors.append('no compatible PHASE anchors')
    return anchors, errors


class Bucket:
    def __init__(self, label, start, end, frame=None):
        self.label, self.start, self.end, self.frame = label, start, end, frame
        self.samples, self.kinds, self.paths = Counter(), Counter(), Counter()
        self.total_samples = self.missing_stacks = self.stack_overflow = self.truncated = 0
        self.durations = {}
        self.union = []
        self.union_complete = True
        self.details = []
        self.detail_overflow = 0

    def accept(self, kind, values, start, end, stack, truncated):
        if kind in SAMPLES:
            if not self.start <= start < self.end or thread_name(values.get('sampledThread')) != 'Render thread':
                return
            self.total_samples += 1
            self.kinds[kind] += 1
            self.truncated += int(truncated)
            if not stack:
                self.missing_stacks += 1
            elif stack in self.samples or len(self.samples) < 1024:
                self.samples[stack] += 1
            else:
                self.stack_overflow += 1
            self.paths.update(categories(stack))
            return
        ms = overlap(self.start, self.end, start, end)
        if not ms:
            return
        name = thread_name(values.get('eventThread'))
        key = (kind, name)
        if key not in self.durations and len(self.durations) >= 512:
            key = ('<other duration/thread keys>', '<bounded overflow>')
        item = self.durations.setdefault(key, {'count': 0, 'overlap_ms_sum_not_disjoint': 0., 'max_overlap_ms': 0.})
        item['count'] += 1
        item['overlap_ms_sum_not_disjoint'] += ms
        item['max_overlap_ms'] = max(item['max_overlap_ms'], ms)
        self.union_complete &= add_union(self.union, max(start, self.start), min(end, self.end))
        if len(self.details) < 30:
            self.details.append({'type': kind, 'thread': name, 'start_ms': start, 'duration_ms': end - start,
                                 'overlap_ms': ms, 'stack': list(stack), 'path_hints': categories(stack)})
        else:
            self.detail_overflow += 1

    def report(self):
        return {'phase': self.label, 'window_ms': [self.start, self.end], 'frame': self.frame,
                'render_samples': self.total_samples, 'sample_event_types': dict(self.kinds),
                'samples_missing_stack': self.missing_stacks, 'samples_truncated_stack': self.truncated,
                'samples_unlisted_stack_capacity': self.stack_overflow,
                'top_render_stacks': [{'count': n, 'stack': list(s), 'path_hints': categories(s)}
                                      for s, n in self.samples.most_common(10)],
                'sample_path_hint_counts_nonexclusive': dict(self.paths),
                'duration_by_type_thread': [dict(type=k[0], thread=k[1], **v) for k, v in sorted(self.durations.items())],
                'all_duration_union_overlap_ms': sum(b - a for a, b in self.union),
                'duration_union_complete': self.union_complete,
                'duration_union_meaning': 'Any selected duration, including concurrent GC/other threads; NOT render blocked time.',
                'duration_details_first30': self.details, 'duration_details_omitted': self.detail_overflow}


def analyze(validation, result, lines, events, top=5, tz=None):
    errors = []
    frames = result.get('frames')
    if not isinstance(frames, list) or not frames:
        raise ValueError('missing/empty frames')
    if result.get('frame_columns') != ['phase', 'clock_ms', 'dt_ms', 'screen']:
        raise ValueError('unexpected frame_columns')
    groups = {}
    previous = None
    for row in frames:
        if (not isinstance(row, list) or len(row) != 4 or not isinstance(row[0], str)
                or not number(row[1]) or not number(row[2]) or row[2] <= 0 or not isinstance(row[3], str)):
            raise ValueError('malformed frame row')
        if previous is not None and row[1] <= previous:
            raise ValueError('non-increasing frame clock')
        previous = row[1]
        groups.setdefault(row[0], []).append(row)
    buckets, longest = [], []
    for phase, rows in groups.items():
        buckets.append(Bucket(phase, min(r[1] - r[2] for r in rows), max(r[1] for r in rows)))
    for row in sorted((r for r in frames if r[2] > 100), key=lambda r: r[2], reverse=True)[:top]:
        longest.append(Bucket(row[0], row[1] - row[2], row[1],
                              {'clock_ms': row[1], 'dt_ms': row[2], 'screen': row[3]}))
    start, end = min(b.start for b in buckets), max(b.end for b in buckets)
    anchors, clock_errors = log_anchors(lines, tz)
    leading_gaps = []
    for anchor in anchors:
        matching = next((b for b in buckets if b.label == anchor['phase']), None)
        allowance = 5000
        if anchor['phase'] == 'warmup':
            configured = (result.get('run') or {}).get('warmup_seconds', 0)
            if number(configured) and configured > 0:
                # Server login precedes the first post-load client RenderFramePre.
                # Permit only this configured warmup gap; never fit a clock offset.
                allowance = max(allowance, configured * 1000 + 5000)
        if matching is None or not matching.start - allowance <= anchor['clock_ms'] <= matching.end:
            clock_errors.append('PHASE clock outside matching frame phase: ' + str(anchor['phase']))
        elif matching.start > anchor['clock_ms']:
            leading_gaps.append({'phase':anchor['phase'],'unmeasured_leading_ms':matching.start-anchor['clock_ms'],
                                 'reason':'No recorded frame intervals; not zero-cost loading and not complete startup coverage'})
    seen = Counter()
    ranges = {}
    malformed = Counter()
    unknown = Counter()
    any_actual_overlap = False
    for event in events:
        kind, values = event.get('type'), event.get('values')
        if kind not in EVENTS:
            unknown[str(kind)[:200]] += 1
            if len(unknown) > 64:
                raise ValueError('too many unexpected event types')
            continue
        seen[kind] += 1
        try:
            if not isinstance(values, dict):
                raise ValueError('missing event values')
            a = timestamp_ms(values.get('startTime'))
            b = a if kind in SAMPLES else a + duration_ms(values.get('duration'))
            if not number(a) or not number(b):
                raise ValueError('nonfinite event time')
        except (ValueError, TypeError, OverflowError, OSError):
            malformed[kind] += 1
            continue
        r = ranges.setdefault(kind, [a, b])
        r[0], r[1] = min(r[0], a), max(r[1], b)
        actual = start <= a < end if kind in SAMPLES else overlap(start, end, a, b) > 0
        any_actual_overlap |= actual
        if not clock_errors and actual:
            stack, truncated = stack_of(values)
            for bucket in buckets + longest:
                bucket.accept(kind, values, a, b, stack, truncated)
    if not any_actual_overlap:
        clock_errors.append('no actual JFR event/frame time overlap; opaque clock is not aligned')
    if malformed:
        errors.append('malformed event times/durations; coverage incomplete')
    if validation.get('success') is not True:
        errors.append('validation.success is not true; benefit summary refused')
    if result.get('failed') is not False:
        errors.append('result.failed is not false')
    errors.extend(clock_errors)
    pilot = validation.get('pilot') is True or (result.get('run') or {}).get('pilot') is True
    compatible = not clock_errors
    return {'schema': 'jfr_frames_diagnostic_v1', 'classification': 'pilot_diagnostic' if pilot else 'diagnostic_only',
            'validation_success': validation.get('success') is True, 'benefit_summary': 'refused: diagnostic only; no gain or causality inference',
            'errors': errors, 'correlation_enabled': compatible,
            'clock_check': {'candidate': 'raw clock as Unix milliseconds, accepted only after independent checks; no fitted offset',
                            'frame_range_ms': [start, end], 'phase_anchors': anchors,
                            'log_timezone': str(tz) if tz else 'machine local timezone', 'errors': clock_errors,
                             'unmeasured_phase_leading_gaps': leading_gaps},
            'event_coverage': {'requested': list(EVENTS), 'seen': dict(seen),
                               'missing': [k for k in EVENTS if not seen[k]], 'ranges_ms': ranges,
                               'malformed_time_or_duration': dict(malformed), 'unexpected': dict(unknown)},
            'phases': [b.report() for b in buckets] if compatible else [],
            'longest_frames_over100ms': [b.report() for b in longest] if compatible else [],
            'limitations': LIMITATIONS}


def run_jfr(path, executable, consume):
    command = [str(executable), 'print', '--json', '--events', ','.join(EVENTS), '--stack-depth', '32', str(path)]
    # stderr is inherited: no pipe deadlock, no unbounded temporary file.
    # Any Popen/pipe permission error is returned to caller; never retry/bypass.
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=None, text=True, encoding='utf-8', errors='strict')
    try:
        report = consume(stream_events(proc.stdout))
        proc.stdout.close()
        code = proc.wait()
        if code:
            raise RuntimeError('jfr print exited %d; see inherited stderr' % code)
        return report
    except BaseException:
        proc.stdout.close()
        if proc.poll() is None:
            proc.terminate()
        proc.wait()
        raise


def read_object(path):
    with path.open(encoding='utf-8-sig') as stream:
        obj = json.load(stream)
    if not isinstance(obj, dict):
        raise ValueError('expected JSON object: ' + str(path))
    return obj


def offset(value):
    match = re.fullmatch(r'([+-])(\d{2}):(\d{2})', value)
    if not match or int(match[2]) > 23 or int(match[3]) > 59:
        raise argparse.ArgumentTypeError('expected +08:00 or -05:00')
    minutes = (int(match[2]) * 60 + int(match[3])) * (1 if match[1] == '+' else -1)
    return timezone(timedelta(minutes=minutes))


def self_test():
    base = timestamp_ms('2026-11-04T01:00:00Z')
    result = {'frame_columns': ['phase', 'clock_ms', 'dt_ms', 'screen'], 'failed': False,
              'run': {}, 'frames': [['base', base + 200, 200, ''], ['base', base + 250, 50, '']]}
    lines = ['[2026-11-04 09:00:00] [PERF2] PHASE ' + json.dumps({'phase': 'base', 'clock_ms': base})]
    stack = {'frames': [{'method': {'type': {'name': 'org/lwjgl/opengl/GL20C'}, 'name': 'glCompileShader'}}]}
    def event(kind, when, dur=None, thread='Render thread'):
        values = {'startTime': when, 'stackTrace': stack,
                  ('sampledThread' if kind in SAMPLES else 'eventThread'): {'javaName': thread}}
        if dur is not None:
            values['duration'] = dur
        return {'type': kind, 'values': values}
    fixtures = [event('jdk.ExecutionSample', '2026-11-04T01:00:00.100Z'),
                event('jdk.NativeMethodSample', '2026-11-04T01:00:00.150Z'),
                event('jdk.ExecutionSample', '2026-11-04T01:00:00.100Z', thread='Worker'),
                event('jdk.ThreadPark', '2026-11-04T01:00:00.050Z', 'PT0.2S'),
                event('jdk.GCPhasePause', '2026-11-04T01:00:00.100Z', 'PT0.05S', 'GC Thread')]
    encoded = json.dumps({'recording': {'events': fixtures}})
    assert list(stream_events(io.StringIO(encoded), chunk_size=7)) == fixtures
    assert list(stream_events(io.StringIO('[]'), chunk_size=1)) == []
    for broken in (encoded[:-2], '[{},]', '[{} {}]', '{"other":[]}'):
        try:
            list(stream_events(io.StringIO(broken), chunk_size=3))
        except ValueError:
            pass
        else:
            raise AssertionError('accepted malformed export')
    try:
        list(stream_events(io.StringIO('[{"x":"' + 'x' * 100 + '"}]'), chunk_size=3, max_event_chars=32))
    except ValueError:
        pass
    else:
        raise AssertionError('event bound not enforced')
    report = analyze({'success': True}, result, lines, iter(fixtures), tz=offset('+08:00'))
    assert report['correlation_enabled'], report['errors']
    frame = report['longest_frames_over100ms'][0]
    assert frame['render_samples'] == 2
    assert abs(frame['all_duration_union_overlap_ms'] - 150) < .001
    assert sum(d['overlap_ms_sum_not_disjoint'] for d in frame['duration_by_type_thread']) == 200
    assert frame['sample_path_hint_counts_nonexclusive']['shader_GL_compile_link'] == 2
    assert categories(('ShaderManager.compile',)) == ['other_or_unknown']
    assert overlap(0, 100, 100, 200) == 0
    bad = dict(result, frames=[['base', 100200, 200, '']])
    assert not analyze({'success': True}, bad, lines, iter(fixtures), tz=offset('+08:00'))['correlation_enabled']
    wrong_date = [lines[0].replace('2026-11-04', '2026-11-03')]
    assert not analyze({'success': True}, result, wrong_date, iter(fixtures), tz=offset('+08:00'))['phases']
    wrong_time = [lines[0].replace('09:00:00', '08:00:00')]
    assert not analyze({'success': True}, result, wrong_time, iter(fixtures), tz=offset('+08:00'))['correlation_enabled']
    future = [event('jdk.ExecutionSample', '2026-11-05T01:00:00Z')]
    assert not analyze({'success': True}, result, lines, iter(future), tz=offset('+08:00'))['correlation_enabled']
    assert analyze({'success': False, 'pilot': True}, result, lines, iter(fixtures), tz=offset('+08:00'))['errors']
    assert duration_ms('PT1M0.25S') == 60250
    intervals = []
    assert add_union(intervals, 0, 5, 1)
    assert not add_union(intervals, 10, 15, 1)
    assert intervals == [(0, 5)]
    return {'self_test': 'PASS', 'scope': 'pure in-memory fixtures; no JFR/game subprocess or artifact writes',
            'checks': ['chunk boundaries', 'strict envelope/tail', 'truncation/trailing comma', 'event memory bound',
                       'sampledThread vs eventThread', 'Render thread filter', 'ISO time/duration',
                       'overlap clipping and non-additive union', 'explicit GL classification',
                       'opaque/nonoverlapping clock rejection', 'log date/time rejection', 'validation/pilot', 'interval bound']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('run', nargs='?', type=Path)
    parser.add_argument('--input-json', type=Path, help='existing jfr print JSON; never invoke JFR')
    parser.add_argument('--jfr', default=JFR, type=Path)
    parser.add_argument('--top', type=int, default=5, help='global longest >100ms frames (1..100)')
    parser.add_argument('--log-utc-offset', type=offset, help='timezone of console prefix, e.g. +08:00; default machine local')
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args(argv)
    if args.self_test:
        print(json.dumps(self_test(), ensure_ascii=False, indent=2))
        return 0
    if not args.run or not 1 <= args.top <= 100:
        parser.error('provide RUN and --top in 1..100')
    try:
        validation = read_object(args.run / 'validation.json')
        result = read_object(args.run / 'perf-result.json')
        # PHASE anchors only: do not retain the complete console log.
        with (args.run / 'console.log').open(encoding='utf-8-sig', errors='replace') as stream:
            lines = [line for line in stream if '[PERF2]' in line and 'PHASE' in line]
        def consume(events):
            return analyze(validation, result, lines, events, args.top, args.log_utc_offset)
        if args.input_json:
            with args.input_json.open(encoding='utf-8-sig') as stream:
                report = consume(stream_events(stream))
        else:
            report = run_jfr(args.run / 'profile.jfr', args.jfr, consume)
        report['run'] = str(args.run.resolve())
        report['source'] = str(args.input_json) if args.input_json else 'jfr print streaming stdout'
        code = 2 if report['errors'] else 0
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, OverflowError) as exc:
        report = {'schema': 'jfr_frames_diagnostic_v1', 'correlation_enabled': False,
                  'errors': [str(exc)], 'failure_policy': 'No permission bypass or retry; no partial correlation report.',
                  'benefit_summary': 'refused'}
        code = 2
    print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    return code


if __name__ == '__main__':
    sys.exit(main())
