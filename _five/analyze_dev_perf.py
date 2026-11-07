"""Read-only dev actual-map performance diagnostics (Python 3.9+, stdlib only).

Usage: python -B _five/analyze_dev_perf.py RUN [RUN ...] [--format console|json]
       python -B _five/analyze_dev_perf.py --self-test
No game/process invocation, JFR decoding, or output-file writes. Redirect stdout
explicitly to save JSON. Pilot/invalid runs remain diagnostic and NEVER enter
formal groups. Formal groups are descriptive, not evidence of a performance gain.
"""
import argparse
from collections import Counter, defaultdict
import io
import json
import math
from pathlib import Path
import re
import statistics
import sys

PHASES = ('warmup', 'base', 'new', 'settle', 'loaded')
CONFIG_KEYS = ('test_only', 'source', 'irisflw', 'pilot', 'clock',
               'warmup_seconds', 'phase_seconds', 'settle_seconds', 'hops',
               'hop_interval_ms', 'route_x', 'route_y', 'route_z', 'step')
DURATION = re.compile(r'([0-9]+(?:\.[0-9]+)?)\s*(ns|us|µs|ms|s)\s*$')
GC = re.compile(r'\[gc\s*\]\s+GC\(\d+\)\s+(.*)$')
SAFE = re.compile(r'\bTotal:\s*([0-9]+(?:\.[0-9]+)?)\s*(ns|us|µs|ms|s)\b', re.I)
UNIFORM = re.compile(r'Shader (.+?) could not find uniform named (\S+) in the specified shader program\.', re.I)
BEHIND = re.compile(r'Running\s+([0-9]+(?:\.[0-9]+)?)\s*ms\s+or\s+(\d+)\s+ticks behind')
MARKER = re.compile(r'\[PERF2\]\s+(PHASE|ROUTE_COMPLETE)\s+(\{.*\})')
LIMITATIONS = [
    'Millisecond frame clock is opaque (not assumed epoch); positive dt samples only, as recorded by probe.',
    'Probe v1 excluded transition gaps; v2 records boundary intervals under the previous phase and exports transitions. Inspect boundaries before attributing a long frame to a phase. Zero-ms frames remain excluded.',
    'Log phase attribution uses PHASE/ROUTE_COMPLETE line order, not absolute frame timestamps; async logging and boundary-spanning events are approximate.',
    'GC Pause and safepoint TOTAL overlap; never sum them. TOTAL includes reaching/leaving safepoint, not just At safepoint.',
    "Can't keep up reported ms is backlog, not a measured disjoint server stall; sums can overlap.",
    'Prefer console.log; acceptance-latest.log is fallback only, never added again. Missing/incomplete logs mean unknown coverage, not proof of zero events.',
    'JFR is only inventoried; no JFR subprocess, full decoding or generated files. No GPU timing, causality, significance or benefit claim.',
    'Formal cohorts match saved config except irisflw/rep AND measured viewport width/height; missing viewport is ineligible. A single initial viewport cannot detect later resizing.',
    'Saved config/viewport matching does not verify mod/world hashes or machine/environment equivalence.',
]


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def milliseconds(value, unit):
    return float(value) * {'ns': 1e-6, 'us': .001, 'µs': .001, 'ms': 1., 's': 1000.}[unit]


def duration_stats(values):
    return {'count': len(values), 'total_ms': sum(values),
            'max_ms': max(values) if values else None,
            'mean_ms': statistics.mean(values) if values else None}


def frame_stats(rows):
    """Match PM_summary, explicitly retaining its descending-index p99 convention."""
    if not rows:
        return {'frames': 0}
    times = sorted((r[2] for r in rows), reverse=True)
    n = len(times)
    total = sum(times)
    worst_n = max(1, math.ceil(n * .01))
    return {'frames': n, 'seconds': total / 1000., 'avg_fps': 1000. * n / total,
            'one_percent_low': 1000. * worst_n / sum(times[:worst_n]),
            'p99_ms': times[math.floor(n * .01)], 'max_frame_ms': times[0],
            'stalls100': sum(t > 100 for t in times),
            'stalls250': sum(t > 250 for t in times),
            'stalls1000': sum(t > 1000 for t in times),
            'stall_time_ms': sum(t for t in times if t > 100),
            'screen_frames': sum(r[3] != '' for r in rows),
            'first_clock_ms': rows[0][1], 'last_clock_ms': rows[-1][1]}


def new_log_bucket():
    return {'gc_pause': [], 'gc_concurrent': [], 'safepoint_total': [],
            'server_behind': [], 'server_ticks': 0, 'veil': Counter(), 'veil_warnings': 0}


def parse_log(lines):
    """Streaming parse. Only completed GC summary rows, not stats/start duplicates."""
    buckets = defaultdict(new_log_bucket)
    anchors, marker_errors = [], []
    phase = 'unassigned'
    complete = route_complete = failed = False
    line_count = 0
    for line_count, line in enumerate(lines, 1):
        marker = MARKER.search(line)
        if marker:
            try:
                payload = json.loads(marker[2])
                next_phase = payload['phase'] if marker[1] == 'PHASE' else 'done'
                if next_phase not in PHASES + ('done',) or not number(payload.get('clock_ms')):
                    raise ValueError('unknown phase or invalid clock')
                phase = next_phase
                anchors.append({'phase': phase, 'clock_ms': payload['clock_ms'],
                                'line': line_count, 'log_prefix': line[:marker.start()].strip()})
            except (ValueError, KeyError, TypeError) as exc:
                marker_errors.append('line %s: %s' % (line_count, exc))
        route_complete |= '[PERF2] ROUTE_COMPLETE ' in line
        complete |= '[PERF2] COMPLETE ' in line
        failed |= '[PERF2] FAILED ' in line or '[PERF2] ROUTE_FAILED ' in line
        bucket = buckets[phase]
        gc = GC.search(line)
        if gc:
            text = gc[1]
            duration = DURATION.search(text)
            if duration:
                ms = milliseconds(duration[1], duration[2])
                if text.startswith('Pause '):
                    bucket['gc_pause'].append(ms)
                elif text.startswith('Concurrent '):
                    bucket['gc_concurrent'].append(ms)
        if re.search(r'\[safepoint\s*\]', line):
            total = SAFE.search(line)
            if total:
                bucket['safepoint_total'].append(milliseconds(total[1], total[2]))
        if "Can't keep up!" in line and re.search(r'\[Server thread/WARN\]', line):
            behind = BEHIND.search(line)
            if behind:
                bucket['server_behind'].append(float(behind[1]))
                bucket['server_ticks'] += int(behind[2])
        if re.search(r'\[Veil/[^\]]*\]', line, re.I) and '/WARN]' in line:
            bucket['veil_warnings'] += 1
            uniform = UNIFORM.search(line)
            if uniform:
                bucket['veil'][(uniform[1], uniform[2])] += 1
    def summarize(bucket):
        pairs = bucket['veil']
        uniforms = Counter()
        for (_, name), count in pairs.items():
            uniforms[name] += count
        return {'gc_pause': duration_stats(bucket['gc_pause']),
                'gc_concurrent_completed_segments_not_stw': duration_stats(bucket['gc_concurrent']),
                'safepoint_total': duration_stats(bucket['safepoint_total']),
                'server_cant_keep_up_reported_behind': dict(duration_stats(bucket['server_behind']), ticks_behind_sum=bucket['server_ticks']),
                'veil_missing_uniform': {'occurrences': sum(pairs.values()), 'unique_shader_uniform_pairs': len(pairs),
                                         'unique_uniforms': len(uniforms), 'by_uniform': dict(sorted(uniforms.items()))},
                'veil_warn_lines': bucket['veil_warnings']}
    overall = new_log_bucket()
    for bucket in buckets.values():
        for key in ('gc_pause', 'gc_concurrent', 'safepoint_total', 'server_behind'):
            overall[key].extend(bucket[key])
        overall['veil'].update(bucket['veil'])
        overall['server_ticks'] += bucket['server_ticks']
        overall['veil_warnings'] += bucket['veil_warnings']
    return {'lines': line_count, 'anchors': anchors, 'marker_errors': marker_errors,
            'complete': complete, 'route_complete': route_complete, 'failed': failed,
            'overall': summarize(overall),
            'by_phase': {p: summarize(b) for p, b in buckets.items()}}


def check_route(route, cfg):
    errors = []
    hops = cfg.get('hops')
    if not isinstance(hops, int) or isinstance(hops, bool) or hops < 0:
        return ['invalid config hops']
    if not isinstance(route, list):
        return ['route is not a list']
    if len(route) != 2 * (hops + 1):
        errors.append('route count: expected %s, got %s' % (2 * (hops + 1), len(route)))
    if any(not isinstance(r, dict) or r.get('phase') not in ('new', 'loaded') for r in route):
        errors.append('unknown/malformed route row')
    last_clock = None
    for phase in ('new', 'loaded'):
        rows = [r for r in route if isinstance(r, dict) and r.get('phase') == phase]
        if [r.get('hop') for r in rows] != list(range(hops + 1)):
            errors.append(phase + ': hop sequence mismatch')
        for row in rows:
            hop = row.get('hop')
            if not number(hop):
                errors.append(phase + ': invalid hop')
                continue
            for axis in ('x', 'y', 'z'):
                origin = cfg.get('route_' + axis)
                step = cfg.get('step')
                if not number(origin) or not number(step) or not number(row.get(axis)):
                    errors.append(phase + ': invalid coordinate/config ' + axis)
                elif abs(row[axis] - (origin + (hop * step if axis == 'x' else 0))) >= .1:
                    errors.append('%s hop %s: coordinate %s mismatch' % (phase, hop, axis))
            clock = row.get('clock_ms')
            if not number(clock) or (last_clock is not None and clock < last_clock):
                errors.append(phase + ': invalid/decreasing route clock')
            if number(clock):
                last_clock = clock
    if [r.get('phase') for r in route if isinstance(r, dict)] != ['new'] * (hops + 1) + ['loaded'] * (hops + 1):
        errors.append('route phase order mismatch')
    return errors


def analyze_data(validation, cfg, result, logs):
    errors, warnings = [], []
    if validation.get('success') is not True:
        errors.append('validation.success is not true')
    configs = (cfg, validation.get('config', {}), result.get('run', {}))
    if any(not isinstance(c, dict) for c in configs):
        errors.append('missing/malformed saved configs')
        configs = tuple(c if isinstance(c, dict) else {} for c in configs)
    for key in CONFIG_KEYS:
        if key not in cfg or any(c.get(key) != cfg.get(key) for c in configs):
            errors.append('missing/conflicting config ' + key)
    if cfg.get('test_only') is not True or cfg.get('source') != 'dev_actual_map':
        errors.append('not isolated dev_actual_map config')
    if type(cfg.get('irisflw')) is not bool:
        errors.append('irisflw is not boolean')
    pilot = any(c.get('pilot') is True for c in configs) or validation.get('pilot') is True
    pilot_known = all(type(c.get('pilot')) is bool for c in configs) and type(validation.get('pilot')) is bool
    if not pilot_known or any(c.get('pilot') != validation.get('pilot') for c in configs):
        errors.append('missing/conflicting pilot flags')
    if result.get('failed') is not False:
        errors.append('result.failed is not false')
    viewport = result.get('viewport')
    if not isinstance(viewport, dict) or any(type(viewport.get(k)) is not int or viewport[k] <= 0 for k in ('width', 'height')):
        errors.append('missing/invalid measured viewport: cannot compare resolution')
        viewport = None
    else:
        viewport = {k: viewport[k] for k in ('width', 'height')}
    route_errors = check_route(result.get('route'), cfg)
    errors.extend(route_errors)
    groups = defaultdict(list)
    frames = result.get('frames', [])
    if result.get('frame_columns') != ['phase', 'clock_ms', 'dt_ms', 'screen']:
        errors.append('unexpected frame_columns')
    if not isinstance(frames, list):
        frames = []
        errors.append('frames is not a list')
    last_clock, phase_order = None, []
    malformed = 0
    for row in frames:
        if not isinstance(row, list) or len(row) != 4 or row[0] not in PHASES or not number(row[1]) or not number(row[2]) or row[2] <= 0 or not isinstance(row[3], str):
            malformed += 1
            continue
        if last_clock is not None and row[1] <= last_clock:
            errors.append('non-increasing frame clock')
        last_clock = row[1]
        if not phase_order or phase_order[-1] != row[0]:
            phase_order.append(row[0])
        groups[row[0]].append(row)
    if malformed:
        errors.append('%s malformed/nonpositive frame rows' % malformed)
    if phase_order != list(PHASES):
        errors.append('frame phase order mismatch')
    phases = {p: frame_stats(groups[p]) for p in PHASES}
    summaries = result.get('summaries', [])
    if not isinstance(summaries, list):
        summaries = []
    for phase, stats in phases.items():
        matching = [s for s in summaries if isinstance(s, dict) and s.get('phase') == phase]
        if stats['frames'] <= 10:
            errors.append(phase + ': <=10 recorded frames')
        if len(matching) != 1:
            errors.append(phase + ': missing/duplicate summary')
        elif any(not number(matching[0].get(k)) or not math.isclose(matching[0][k], stats[k], rel_tol=1e-7, abs_tol=1e-6)
                 for k in ('frames', 'seconds', 'avg_fps', 'one_percent_low', 'p99_ms', 'max_frame_ms', 'stalls100', 'stalls250', 'stalls1000', 'stall_time_ms', 'screen_frames') if k in stats):
            errors.append(phase + ': probe summary differs from raw frames')
        if stats.get('screen_frames', 0):
            warnings.append(phase + ': GUI screen present in sampled frames')
    if not logs.get('complete') or not logs.get('route_complete') or logs.get('failed'):
        errors.append('log COMPLETE/ROUTE_COMPLETE missing or failure marker present')
    if logs.get('marker_errors'):
        errors.append('malformed phase marker')
    if [a['phase'] for a in logs.get('anchors', [])] != list(PHASES) + ['done']:
        errors.append('log phase marker order/integrity mismatch')
    anchors = {a['phase']: a['clock_ms'] for a in logs.get('anchors', [])}
    longest = []
    for phase in PHASES:
        for row in sorted(groups[phase], key=lambda r: r[2], reverse=True)[:5]:
            longest.append({'phase': phase, 'clock_ms': row[1], 'dt_ms': row[2], 'screen': row[3],
                            'phase_offset_ms': row[1] - anchors[phase] if phase in anchors else None})
    errors = list(dict.fromkeys(errors))
    eligible = not errors and not pilot and pilot_known
    return {'classification': 'pilot_diagnostic' if pilot else ('formal_candidate' if eligible else 'invalid_diagnostic'),
            'formal_eligible': eligible, 'pilot': pilot, 'errors': errors, 'warnings': warnings,
            'exclusion_reasons': errors + (['pilot excluded from formal A/B'] if pilot else []),
            'config': cfg, 'viewport': viewport, 'route_check': {'success': not route_errors, 'errors': route_errors},
            'phases': phases, 'longest_frames_top5_per_phase': longest, 'logs': logs}


def read_object(path):
    with path.open(encoding='utf-8-sig') as stream:
        data = json.load(stream)
    if not isinstance(data, dict):
        raise ValueError('expected JSON object: ' + path.name)
    return data


def analyze_run(path):
    out = {'run': str(path.resolve())}
    try:
        validation = read_object(path / 'validation.json')
        cfg = read_object(path / 'perf-config.json')
        result = read_object(path / 'perf-result.json')
        log = path / 'console.log'
        if not log.is_file():
            log = path / 'acceptance-latest.log'
        with log.open(encoding='utf-8-sig', errors='replace') as stream:
            logs = parse_log(stream)
        logs['source'] = log.name
        out.update(analyze_data(validation, cfg, result, logs))
        jfr = path / 'profile.jfr'
        out['jfr'] = {'exists': jfr.is_file(), 'bytes': jfr.stat().st_size if jfr.is_file() else None, 'parsed': False}
    except (OSError, ValueError, TypeError, KeyError, OverflowError) as exc:
        out.update({'classification': 'invalid_diagnostic', 'formal_eligible': False,
                    'errors': [str(exc)], 'exclusion_reasons': [str(exc)]})
    return out


def formal_groups(runs):
    """No pilot/failed fallback, no pooled-frame pseudoreplication or gain claim."""
    cohorts = defaultdict(list)
    for run in runs:
        if run['formal_eligible']:
            key = json.dumps({'config': {k: v for k, v in run['config'].items() if k not in ('irisflw', 'rep')},
                              'viewport': run['viewport']}, sort_keys=True)
            cohorts[key].append(run)
    answer = []
    for key, cohort in cohorts.items():
        groups = {}
        for mode in (False, True):
            selected = [r for r in cohort if r['config']['irisflw'] is mode]
            phases = {}
            for phase in PHASES:
                metrics = {}
                for metric in ('avg_fps', 'one_percent_low', 'p99_ms', 'max_frame_ms', 'stalls100', 'stalls250', 'stalls1000', 'stall_time_ms'):
                    values = [r['phases'][phase][metric] for r in selected]
                    metrics[metric] = {'n_runs': len(values), 'mean': statistics.mean(values) if values else None,
                                       'median': statistics.median(values) if values else None,
                                       'min': min(values) if values else None, 'max': max(values) if values else None}
                phases[phase] = metrics
            reps = [r['config'].get('rep') for r in selected]
            groups['on' if mode else 'off'] = {'n_runs': len(selected), 'runs': [r['run'] for r in selected],
                                                'reps': reps, 'duplicate_rep_labels': len(set(map(str, reps))) != len(reps), 'phases': phases}
        answer.append({'matching_config': json.loads(key), 'both_arms_present': all(g['n_runs'] for g in groups.values()), 'arms': groups})
    return answer


def self_test():
    cfg = dict(zip(CONFIG_KEYS, (True, 'dev_actual_map', False, False, 'opaque ms', 15, 20, 5, 1, 2000, 12000, 160, 12000, 32)))
    cfg['rep'] = 1
    frames, summaries, route, lines = [], [], [], []
    for i, phase in enumerate(PHASES):
        start = 100000 + i * 10000  # Deliberately NOT epoch.
        lines.append('[23:59:59] [Server thread/INFO] [KubeJS Server/]: [PERF2] PHASE ' + json.dumps({'phase': phase, 'clock_ms': start}))
        rows = [[phase, start + j * 200, 200, '' if j != 2 else 'TestScreen'] for j in range(1, 13)]
        frames.extend(rows)
        summaries.append(dict(frame_stats(rows), phase=phase))
        if phase in ('new', 'loaded'):
            route.extend({'phase': phase, 'hop': hop, 'clock_ms': start + hop * 2000, 'x': 12000 + hop * 32, 'y': 160, 'z': 12000} for hop in range(2))
        if phase == 'base':
            lines.extend(['[date][2.0s][info][gc,start ] GC(2) Pause Init Mark',
                          '[date][2.0s][info][gc ] GC(2) Pause Init Mark 0.040ms',
                          '[date][2.0s][info][gc,stats ] Pause Init Mark (G) 999 us',
                          '[date][2.0s][info][gc ] GC(2) Concurrent marking 9000.0ms',
                          '[date][2.0s][info][safepoint ] Safepoint "test", At safepoint: 10 ns, Total: 1200000 ns, Threads: 1',
                          "[00:00:01] [Server thread/WARN] [minecraft/MinecraftServer]: Can't keep up! Is the server overloaded? Running 4522ms or 90 ticks behind",
                          '[00:00:01] [Render thread/WARN] [Veil/]: Shader p could not find uniform named x in the specified shader program.',
                          '[00:00:01] [Render thread/WARN] [Veil/]: unrelated warning about uniforms',
                          '[00:00:01] [Render thread/WARN] [Iris/]: Shader p could not find uniform named z in the specified shader program.'])
    lines.extend(['[PERF2] ROUTE_COMPLETE ' + json.dumps({'clock_ms': 150000}), '[PERF2] COMPLETE {}'])
    logs = parse_log(io.StringIO('\n'.join(lines)))
    result = {'run': dict(cfg), 'viewport': {'width': 1540, 'height': 692}, 'failed': False, 'frames': frames, 'summaries': summaries, 'route': route,
              'frame_columns': ['phase', 'clock_ms', 'dt_ms', 'screen']}
    validation = {'success': True, 'pilot': False, 'config': dict(cfg)}
    report = analyze_data(validation, cfg, result, logs)
    assert report['formal_eligible'], report['errors']
    off = dict(report, run='fixture-off')
    on = dict(report, run='fixture-on', config=dict(cfg, irisflw=True))
    assert len(formal_groups([off, on])) == 1
    assert formal_groups([off, on])[0]['both_arms_present']
    other_resolution = dict(on, viewport={'width': 1920, 'height': 1080})
    separated = formal_groups([off, other_resolution])
    assert len(separated) == 2 and not any(g['both_arms_present'] for g in separated)
    saved_viewport = result.pop('viewport')
    assert not analyze_data(validation, cfg, result, logs)['formal_eligible']
    result['viewport'] = saved_viewport
    assert logs['overall']['gc_pause']['count'] == 1
    assert math.isclose(logs['overall']['gc_pause']['total_ms'], .04)
    assert logs['overall']['gc_concurrent_completed_segments_not_stw']['total_ms'] == 9000
    assert math.isclose(logs['overall']['safepoint_total']['total_ms'], 1.2)
    assert logs['by_phase']['base']['server_cant_keep_up_reported_behind']['total_ms'] == 4522
    assert logs['overall']['veil_missing_uniform']['occurrences'] == 1
    assert logs['overall']['veil_warn_lines'] == 2
    assert report['phases']['base']['stalls100'] == 12
    assert report['longest_frames_top5_per_phase'][0]['phase_offset_ms'] == 200
    validation['success'] = False
    assert not analyze_data(validation, cfg, result, logs)['formal_eligible']
    validation['success'] = True
    for c in (validation, validation['config'], result['run'], cfg):
        c['pilot'] = True
    pilot = analyze_data(validation, cfg, result, logs)
    assert pilot['classification'] == 'pilot_diagnostic' and not pilot['formal_eligible']
    assert formal_groups([dict(pilot, run='fixture')]) == []
    result['route'][0]['y'] = 999
    assert not analyze_data(validation, cfg, result, logs)['route_check']['success']
    assert frame_stats([['base', 1, 100, ''], ['base', 2, 250, ''], ['base', 3, 1000, '']])['stalls250'] == 1
    return {'self_test': 'PASS', 'scope': 'in-memory fixtures only; no game or files written',
            'checks': ['non-epoch phase clock', 'GC Pause vs concurrent/start/stats', 'safepoint TOTAL units',
                       'phase backlog', 'Veil exact uniform missing', 'frame thresholds', 'validation gate', 'pilot exclusion', 'route XYZ',
                       'same-resolution arms merge', 'different-resolution arms separate', 'missing viewport excluded']}


def console_summary(report):
    for run in report['runs']:
        print('%s: %s; formal=%s' % (run['run'], run['classification'], run['formal_eligible']))
        if run.get('viewport'):
            print('  measured viewport: %sx%s' % (run['viewport']['width'], run['viewport']['height']))
        for reason in run.get('exclusion_reasons', []):
            print('  EXCLUDE: ' + reason)
        for phase, stats in run.get('phases', {}).items():
            if stats['frames']:
                print('  %-6s n=%d fps=%.2f 1%%low=%.2f p99=%.2fms max=%.2fms >100/250/1000=%d/%d/%d screen=%d' %
                      (phase, stats['frames'], stats['avg_fps'], stats['one_percent_low'], stats['p99_ms'], stats['max_frame_ms'],
                       stats['stalls100'], stats['stalls250'], stats['stalls1000'], stats['screen_frames']))
        if 'logs' in run:
            for phase, bucket in [('overall', run['logs']['overall'])] + list(run['logs']['by_phase'].items()):
                print('  log %-10s GC-pause=%.3fms(%d) safepoint-TOTAL=%.3fms(%d) backlog=%.1fms(%d) Veil-missing=%d' %
                      (phase, bucket['gc_pause']['total_ms'], bucket['gc_pause']['count'], bucket['safepoint_total']['total_ms'],
                       bucket['safepoint_total']['count'], bucket['server_cant_keep_up_reported_behind']['total_ms'],
                       bucket['server_cant_keep_up_reported_behind']['count'], bucket['veil_missing_uniform']['occurrences']))
        for warning in run.get('warnings', []):
            print('  WARN: ' + warning)
    print('Formal matched-config cohorts: %d (descriptive only; no gain claim)' % len(report['formal_groups']))
    for index, group in enumerate(report['formal_groups'], 1):
        print('  cohort %s: off=%s on=%s both=%s' % (index, group['arms']['off']['n_runs'], group['arms']['on']['n_runs'], group['both_arms_present']))
    print('Use --format json for full per-phase aggregates, anchors and limitations.')
    for item in LIMITATIONS:
        print('LIMIT: ' + item)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('runs', nargs='*', type=Path, help='one or more completed dev run directories')
    parser.add_argument('--format', choices=('json', 'console'), default='json')
    parser.add_argument('--self-test', action='store_true', help='run in-memory fixtures, no filesystem writes')
    args = parser.parse_args(argv)
    if args.self_test:
        print(json.dumps(self_test(), ensure_ascii=False, indent=2))
        return 0
    if not args.runs:
        parser.error('provide at least one run directory or --self-test')
    # Resolve/deduplicate so repeating a directory cannot inflate a formal arm.
    paths = list(dict.fromkeys(p.resolve() for p in args.runs))
    runs = [analyze_run(p) for p in paths]
    report = {'schema': 'dev_perf_analysis_v1', 'runs': runs, 'formal_groups': formal_groups(runs), 'limitations': LIMITATIONS}
    if args.format == 'json':
        print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    else:
        console_summary(report)
    return 2 if any(r.get('errors') for r in runs) else 0


if __name__ == '__main__':
    sys.exit(main())
