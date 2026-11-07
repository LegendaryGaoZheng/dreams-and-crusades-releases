"""Read-only compact JFR/frame diagnostics, stdlib Python and JDK 21+.

python -B _five/analyze_jfr_compact.py RUN --log-utc-offset +08:00 --top 20
python -B _five/analyze_jfr_compact.py --self-test
python -B _five/analyze_jfr_compact.py --render-blocks PROFILE main 3

Compile JfrCompact.java first; this wrapper never compiles or starts the game.
Only the report goes to stdout; extractor statistics inherit stderr. No JSON
export, temporary recording, or report file is created. Time checks and analysis
are reused unchanged from analyze_jfr_frames.
"""
import argparse
import io
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

import analyze_jfr_frames as shared

JAVA = r'C:\Program Files\Eclipse Adoptium\jdk-24.0.2.12-hotspot\bin\java.exe'
CLASSDIR = Path(__file__).resolve().parent / 'perf' / 'tools' / 'jfr-compact-classes'
COVERAGE = [
    'Compact extraction retains samples only for exact Render thread by default, or an explicit original javaName AND javaThreadId selection; no implicit main alias.',
    'All requested duration events are retained on all threads, including GC/park/monitor/safepoint; only Render thread carries stacks.',
    'event_coverage.seen and per-window sample counts are retained Render thread samples, NOT whole-process sample totals; missing sample types do not prove absence elsewhere.',
    'Stacks contain at most 32 method type/name frames and a truncation flag; classLoader/module and other stack metadata are intentionally omitted.',
    'Extractor missing/null field and omitted sample counts are on inherited stderr, not captured in this report.',
]


def decorate(report):
    report['extraction'] = {
        'mode': 'jdk.jfr.consumer.RecordingFile compact streaming bare JSON array',
        'sample_thread': 'Render thread',
        'duration_threads': 'all',
        'duration_stack_thread': 'Render thread',
        'stack_frame_limit': 32,
        'sample_counts_scope': 'retained Render thread observations only; not full-process sample totals',
        'timestamps': 'unmodified RecordedEvent.getStartTime/getDuration; no fitted offset',
        'extractor_statistics': 'inherited stderr; not captured',
    }
    # Do not mutate shared.LIMITATIONS, which the shared analyzer returns directly.
    report['limitations'] = list(report.get('limitations', [])) + COVERAGE
    return report


def stop_owned(proc):
    """Reap our extractor even on parser errors, consumer errors or Ctrl+C."""
    if proc.poll() is None:
        try:
            proc.terminate()
        except ProcessLookupError:
            pass
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


class IdentityAudit:
    """Explicit, reversible canonical view; extractor JSON keeps original identity."""
    def __init__(self, name, thread_id, evidence, result):
        self.name, self.thread_id, self.evidence = name, thread_id, evidence
        self.mapped_samples = self.mapped_durations = 0
        self.phases = {}
        for phase, clock, dt, screen in result['frames']:
            bucket = self.phases.setdefault(phase, {'range_ms': [clock - dt, clock],
                                                    'selected_samples': 0, 'render_evidence_samples': 0,
                                                    'render_method_counts': {}})
            bucket['range_ms'][0] = min(bucket['range_ms'][0], clock - dt)
            bucket['range_ms'][1] = max(bucket['range_ms'][1], clock)

    @staticmethod
    def strong(method):
        if not isinstance(method, str):
            return False
        cls, _, name = method.rpartition('.')
        return ((cls == 'net.minecraft.client.Minecraft' and name in ('run', 'runTick'))
                or (cls in ('net.minecraft.client.renderer.GameRenderer',
                            'net.minecraft.client.renderer.LevelRenderer') and name.startswith('render')))

    def events(self, events):
        for event in events:
            values = event.get('values')
            if not isinstance(values, dict):
                yield event
                continue
            sample = event.get('type') in shared.SAMPLES
            key = 'sampledThread' if sample else 'eventThread'
            raw = values.get(key)
            if not isinstance(raw, dict):
                yield event
                continue
            selected = raw.get('javaName') == self.name and raw.get('javaThreadId') == self.thread_id
            if selected:
                if sample:
                    self.mapped_samples += 1
                    try:
                        when = shared.timestamp_ms(values.get('startTime'))
                    except (ValueError, TypeError, OverflowError, OSError):
                        when = None
                    # Java checks the full recorded stack, not only the retained 32 frames.
                    methods = values.get('renderIdentityEvidence') or []
                    methods = [m for m in methods if self.strong(m)] if isinstance(methods, list) else []
                    for bucket in self.phases.values():
                        lo, hi = bucket['range_ms']
                        if when is not None and lo <= when < hi:
                            bucket['selected_samples'] += 1
                            if methods:
                                bucket['render_evidence_samples'] += 1
                                for method in set(methods):
                                    counts = bucket['render_method_counts']
                                    counts[method] = counts.get(method, 0) + 1
                else:
                    self.mapped_durations += 1
            if selected or raw.get('javaName') == 'Render thread':
                canonical = dict(raw, originalJavaName=raw.get('javaName'),
                                 originalJavaThreadId=raw.get('javaThreadId'),
                                 javaName='Render thread' if selected else '[unselected raw] Render thread')
                event = dict(event, values=dict(values, **{key: canonical}))
            yield event

    def finish(self, report):
        report['extraction']['explicit_thread_identity'] = {
            'original_javaName': self.name, 'original_javaThreadId': self.thread_id,
            'match': 'exact name AND id; no inferred or global main alias',
            'canonical_javaName_for_shared_analysis': 'Render thread',
            'raw_identity_preserved': 'extractor original name/id; canonical objects also carry originalJavaName/originalJavaThreadId',
            'operator_verification': self.evidence,
            'verification_method': 'full recorded sample stacks tested for Minecraft.run/runTick or GameRenderer/LevelRenderer.render*; actual phase time gates, no offset fitting',
            'mapped_samples_all_times': self.mapped_samples,
            'mapped_duration_events_all_times': self.mapped_durations,
            'phase_evidence': self.phases,
        }
        if not any(b['render_evidence_samples'] for b in self.phases.values()):
            report['errors'].append('explicit render identity has no Minecraft.run/runTick or GameRenderer/LevelRenderer.render* sample evidence in any recorded frame phase; correlation refused')
            report['correlation_enabled'] = False
            report['phases'] = []
            report['longest_frames_over100ms'] = []
        return report


def run_compact(path, java, classdir, consume, identity=None):
    command = [str(java), '-cp', str(classdir), 'JfrCompact', str(path)]
    if identity is not None:
        command += ['--render-thread-name', identity.name, '--render-thread-id', str(identity.thread_id)]
    # Inherit stderr: no stderr pipe deadlock, full-output capture or temp JSON.
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=None,
                            text=True, encoding='utf-8', errors='strict')
    try:
        events = shared.stream_events(proc.stdout)
        report = consume(identity.events(events) if identity is not None else events)
        proc.stdout.close()
        code = proc.wait()
        if code:
            raise RuntimeError('JfrCompact exited %d; see inherited stderr' % code)
        report = decorate(report)
        return identity.finish(report) if identity is not None else report
    except BaseException:
        try:
            proc.stdout.close()
        finally:
            stop_owned(proc)
        raise


def render_blocks(profile, name, thread_id, java=JAVA, classdir=CLASSDIR):
    """Stream bounded raw block diagnostics, preserving original thread identity."""
    if thread_id <= 0:
        raise ValueError('positive Java thread id required')
    command = [str(java), '-cp', str(classdir), 'JfrCompact', '--render-blocks', str(profile), name, str(thread_id)]
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=None,
                            text=True, encoding='utf-8', errors='strict')
    try:
        sys.stdout.write('[')
        first = True
        for event in shared.stream_events(proc.stdout):
            if not first:
                sys.stdout.write(',\n')
            sys.stdout.write(json.dumps(event, ensure_ascii=False, allow_nan=False))
            first = False
        proc.stdout.close()
        code = proc.wait()
        if code:
            raise RuntimeError('JfrCompact render-blocks exited %d' % code)
        sys.stdout.write(']\n')
    except BaseException:
        try:
            proc.stdout.close()
        finally:
            stop_owned(proc)
        raise


def self_test():
    # Existing fixtures exercise independent clock gates, GC/park overlap, parser
    # bounds, malformed exports and correlation refusal; no subprocess/JFR I/O.
    base_checks = shared.self_test()
    t = shared.timestamp_ms('2026-11-04T01:00:00Z')
    result = {'frame_columns': ['phase', 'clock_ms', 'dt_ms', 'screen'],
              'failed': False, 'run': {}, 'frames': [['base', t + 200, 200, '']]}
    lines = ['[2026-11-04 09:00:00] [PERF2] PHASE ' + json.dumps({'phase': 'base', 'clock_ms': t})]
    fixtures = [
        {'type': 'jdk.ExecutionSample', 'values': {
            'startTime': '2026-11-04T01:00:00.100Z',
            'sampledThread': {'javaName': 'Render thread'},
            'stackTrace': {'frames': [{'method': {'type': {'name': 'org/lwjgl/opengl/GL20C'},
                                                    'name': 'glCompileShader'}}], 'truncated': True}}},
        {'type': 'jdk.ThreadPark', 'values': {'startTime': '2026-11-04T01:00:00.050Z',
            'duration': 'PT0.2S', 'eventThread': {'javaName': 'Worker'}}},
        {'type': 'jdk.GCPhasePause', 'values': {'startTime': '2026-11-04T01:00:00.100Z',
            'duration': 'PT0.05S', 'eventThread': {'javaName': None}}},
    ]
    payload = json.dumps(fixtures)
    def consume(events):
        return shared.analyze({'success': True}, result, lines, events, 20, shared.offset('+08:00'))
    class FakeProcess:
        def __init__(self, text, code=0, running=False, resist=False):
            self.stdout = io.StringIO(text)
            self.code, self.running, self.resist = code, running, resist
            self.terminated = self.killed = self.reaped = False
        def poll(self):
            return None if self.running else self.code
        def terminate(self):
            self.terminated = True
            if not self.resist:
                self.running = False
        def kill(self):
            self.killed, self.running = True, False
        def wait(self, timeout=None):
            if self.running and timeout is not None:
                raise subprocess.TimeoutExpired('fixture', timeout)
            self.reaped = True
            return self.code
    proc = FakeProcess(payload)
    with patch.object(subprocess, 'Popen', return_value=proc) as popen:
        report = run_compact(Path('fixture-not-opened.jfr'), 'java-fixture', 'classes-fixture', consume)
    assert proc.reaped and proc.stdout.closed
    assert popen.call_args.kwargs['stderr'] is None
    assert popen.call_args.args[0] == ['java-fixture', '-cp', 'classes-fixture', 'JfrCompact', 'fixture-not-opened.jfr']
    assert report['correlation_enabled'], report['errors']
    assert report['longest_frames_over100ms'][0]['render_samples'] == 1
    assert abs(report['longest_frames_over100ms'][0]['all_duration_union_overlap_ms'] - 150) < .001
    assert report['extraction']['duration_threads'] == 'all'
    assert shared.LIMITATIONS[-1] not in COVERAGE
    for text, code, consumer in [('[{', 0, consume), (payload, 7, consume),
                                  (payload, 0, lambda events: (_ for _ in ()).throw(KeyboardInterrupt()))]:
        proc = FakeProcess(text, code=code, running=(code == 0), resist=True)
        with patch.object(subprocess, 'Popen', return_value=proc):
            try:
                run_compact(Path('fixture-not-opened.jfr'), 'java-fixture', 'classes-fixture', consumer)
            except (ValueError, RuntimeError, KeyboardInterrupt):
                pass
            else:
                raise AssertionError('failure accepted')
        assert proc.reaped and proc.stdout.closed
        if code == 0:
            assert proc.terminated and proc.killed
    proc = FakeProcess(payload)
    diagnostic_output = io.StringIO()
    with patch.object(subprocess, 'Popen', return_value=proc) as popen, patch.object(sys, 'stdout', diagnostic_output):
        render_blocks(Path('fixture-not-opened.jfr'), 'main', 3, 'java-fixture', 'classes-fixture')
    assert json.loads(diagnostic_output.getvalue()) == fixtures
    assert popen.call_args.args[0][-4:] == ['--render-blocks', 'fixture-not-opened.jfr', 'main', '3']
    assert proc.reaped and proc.stdout.closed
    proc = FakeProcess('[{', running=True, resist=True)
    with patch.object(subprocess, 'Popen', return_value=proc), patch.object(sys, 'stdout', io.StringIO()):
        try:
            render_blocks(Path('fixture-not-opened.jfr'), 'main', 3)
        except ValueError:
            pass
        else:
            raise AssertionError('bad block diagnostic accepted')
    assert proc.reaped and proc.terminated and proc.killed and proc.stdout.closed
    selected_fixture = json.loads(payload)
    selected_fixture[0]['values']['sampledThread'] = {'javaName': 'main', 'javaThreadId': 3}
    selected_fixture[0]['values']['renderIdentityEvidence'] = ['net.minecraft.client.Minecraft.runTick']
    audit = IdentityAudit('main', 3, 'fixture verified raw stack', result)
    proc = FakeProcess(json.dumps(selected_fixture))
    with patch.object(subprocess, 'Popen', return_value=proc) as popen:
        aliased = run_compact(Path('fixture-not-opened.jfr'), 'java-fixture', 'classes-fixture', consume, audit)
    assert popen.call_args.args[0][-4:] == ['--render-thread-name', 'main', '--render-thread-id', '3']
    assert aliased['correlation_enabled'], aliased['errors']
    assert aliased['longest_frames_over100ms'][0]['render_samples'] == 1
    proof = aliased['extraction']['explicit_thread_identity']
    assert proof['phase_evidence']['base']['render_evidence_samples'] == 1
    assert selected_fixture[0]['values']['sampledThread']['javaName'] == 'main'
    mapped = list(IdentityAudit('main', 3, 'fixture', result).events(iter(selected_fixture)))
    assert mapped[0]['values']['sampledThread']['originalJavaName'] == 'main'
    assert mapped[0]['values']['sampledThread']['javaThreadId'] == 3
    for bad_id, evidence, when in [(4, ['net.minecraft.client.Minecraft.runTick'], '2026-11-04T01:00:00.100Z'),
                                   (3, ['org.lwjgl.opengl.GL.<clinit>'], '2026-11-04T01:00:00.100Z'),
                                   (3, ['net.minecraft.client.Minecraft.runTick'], '2026-11-04T01:00:01Z')]:
        bad_fixture = json.loads(json.dumps(selected_fixture))
        bad_fixture[0]['values']['renderIdentityEvidence'] = evidence
        bad_fixture[0]['values']['startTime'] = when
        audit = IdentityAudit('main', bad_id, 'fixture', result)
        rejected = audit.finish(decorate(consume(audit.events(iter(bad_fixture)))))
        assert not rejected['correlation_enabled'] and not rejected['phases']
        assert any('explicit render identity' in error for error in rejected['errors'])
    return {'self_test': 'PASS', 'scope': 'in-memory fixtures and mocked subprocess only; no profile/game/file writes',
            'shared_checks': base_checks['checks'],
            'compact_checks': ['bare-array schema', 'other-thread/null-thread GC and park retained without stacks',
                               'render stack/truncation', 'streamed command and inherited stderr',
                               'parser failure cleanup', 'extractor nonzero rejection',
                               'KeyboardInterrupt terminate/timeout/kill/wait', 'coverage disclosure',
                               'explicit exact name AND Java id selection with raw identity preservation',
                               'phase strong-render evidence counts',
                               'wrong id, GL-init-only and out-of-phase evidence reject correlation',
                               'raw render-blocks command, streaming schema and parser-failure child cleanup']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('run', nargs='?', type=Path)
    parser.add_argument('--java', default=JAVA, type=Path)
    parser.add_argument('--classdir', default=CLASSDIR, type=Path)
    parser.add_argument('--top', type=int, default=20, help='global longest >100ms frames (1..100); default 20')
    parser.add_argument('--top20', dest='top', action='store_const', const=20, help='alias for --top 20')
    parser.add_argument('--log-utc-offset', type=shared.offset)
    parser.add_argument('--render-thread-name', help='explicit original JFR javaName; requires id and verification text')
    parser.add_argument('--render-thread-id', type=int, help='explicit original JFR Java thread id (not OS id)')
    parser.add_argument('--render-thread-evidence', help='operator verification from this recording thread diagnosis; included verbatim in report')
    parser.add_argument('--render-blocks', nargs=3, metavar=('PROFILE', 'NAME', 'ID'), help='raw selected monitor-enter/park events >=100ms, at most 64 frames; no full analysis')
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args(argv)
    if args.self_test:
        print(json.dumps(self_test(), ensure_ascii=False, indent=2))
        return 0
    if args.render_blocks:
        try:
            profile, name, thread_id = args.render_blocks
            render_blocks(Path(profile), name, int(thread_id), args.java, args.classdir)
            return 0
        except (OSError, ValueError, RuntimeError) as exc:
            print('render-blocks failed: ' + str(exc), file=sys.stderr)
            return 2
    if not args.run or not 1 <= args.top <= 100:
        parser.error('provide RUN and --top in 1..100')
    explicit_identity = any(v is not None for v in (args.render_thread_name, args.render_thread_id, args.render_thread_evidence))
    if explicit_identity and (not args.render_thread_name or not args.render_thread_id
                              or args.render_thread_id <= 0 or not args.render_thread_evidence):
        parser.error('explicit mapping requires --render-thread-name, positive --render-thread-id, and --render-thread-evidence')
    try:
        validation = shared.read_object(args.run / 'validation.json')
        result = shared.read_object(args.run / 'perf-result.json')
        with (args.run / 'console.log').open(encoding='utf-8-sig', errors='replace') as stream:
            lines = [line for line in stream if '[PERF2]' in line and 'PHASE' in line]
        def consume(events):
            return shared.analyze(validation, result, lines, events, args.top, args.log_utc_offset)
        identity = IdentityAudit(args.render_thread_name, args.render_thread_id, args.render_thread_evidence, result) if explicit_identity else None
        report = run_compact(args.run / 'profile.jfr', args.java, args.classdir, consume, identity)
        report['run'] = str(args.run.resolve())
        report['source'] = 'JfrCompact RecordingFile streaming stdout'
        code = 2 if report['errors'] else 0
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, OverflowError) as exc:
        report = decorate({'schema': 'jfr_frames_diagnostic_v1', 'correlation_enabled': False,
                           'errors': [str(exc)],
                           'failure_policy': 'No permission bypass or retry; no partial correlation report.',
                           'benefit_summary': 'refused'})
        code = 2
    print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    return code


if __name__ == '__main__':
    sys.exit(main())
