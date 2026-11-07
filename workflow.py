"""Safe workspace entry point. Run with python -B workflow.py --help."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
VERSIONS = Path.home() / 'Desktop/游戏/.minecraft/versions'
DEV = VERSIONS / '梦想与远征_dev'
RELEASE = VERSIONS / '梦想与远征_Release'
WORLD = DEV / 'saves/perf_oldworld_20261103'
STAGING = ROOT / '.stage'
QUESTS = Path('config/ftbquests/quests')
PERF = ROOT / '_five/perf/dev-20261104'
sys.path[:0] = [str(ROOT / '_five'), str(ROOT / '_struct')]


def guarded(path, base):
    """Reject aliases and reparse points, including inside the allowed tree."""
    if not path.is_absolute() or '..' in path.parts or path == base or not path.is_relative_to(base):
        raise ValueError(f'Target outside approved directory: {path}')
    for part in (*reversed(path.parents), path):
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 1024:
            raise ValueError(f'Reparse point: {part}')
    if path.resolve() != path or base.resolve() != base:
        raise ValueError(f'Path alias: {path}')
    return path


def dev_target(path):
    relative = guarded(path, DEV).relative_to(DEV)
    if relative.parts[0] not in {'config', 'mods', 'kubejs', 'resourcepacks', 'shaderpacks',
                                 'schematics', 'options.txt', 'saves'}:
        raise ValueError(f'Unapproved dev target: {relative}')
    if relative.parts[0] == 'saves' and not path.is_relative_to(WORLD):
        raise ValueError(f'Unapproved test world: {relative}')
    return path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def report(value):
    print(json.dumps(value, ensure_ascii=False, indent=2))


def preflight():
    from perf_suite import require_idle
    from dev_perf_suite import DIRS, reject_lanserverproperties
    require_idle()
    setup = json.loads((PERF / 'setup.json').read_text(encoding='utf-8'))
    if Path(setup['dev_world']) != WORLD:
        raise ValueError('Unexpected performance test world')
    snapshot = guarded(Path(setup['immutable_world']), PERF)
    for folder in [*(DEV / d for d in DIRS), WORLD, snapshot, PERF / 'baseline']:
        base = DEV if folder.is_relative_to(DEV) else PERF
        guarded(folder, base)
        if not folder.is_dir():
            raise ValueError(f'Missing directory: {folder}')
        for member in folder.rglob('*'):
            guarded(member, base)
            if member.is_file() and member.stat().st_nlink != 1:
                raise ValueError(f'Hardlinked performance input or target: {member}')
    for path in (DEV / 'options.txt', WORLD / 'level.dat'):
        if not dev_target(path).is_file() or path.stat().st_nlink != 1:
            raise ValueError(f'Missing file: {path}')
    for path in ('options.txt', 'mods'):
        guarded(PERF / 'baseline' / path, PERF)
    reject_lanserverproperties(PERF / 'baseline/mods')
    reject_lanserverproperties(DEV / 'mods')
    if not any(p.name.lower().startswith('e4mc') and p.suffix == '.jar'
               for p in (PERF / 'baseline/mods').iterdir()):
        raise ValueError('Missing enabled e4mc in performance baseline')


def quest_edit(quest_id, locale, title):
    path = guarded(ROOT / 'pack/quests/lang' / f'{locale}.snbt', ROOT / 'pack/quests')
    source = path.read_bytes().decode('utf-8')
    key = rf'quest\.{quest_id}\.title'
    pattern = re.compile(rf'(?m)^([ \t]*{key}:[ \t]*)"(?:\\.|[^"\\])*"([ \t]*\r?)$')
    edited, count = pattern.subn(
        lambda m: m[1] + json.dumps(title, ensure_ascii=False) + m[2], source)
    if count != 1:
        raise ValueError('Expected one existing title in this locale')
    return path, edited.encode('utf-8')


def legacy_quest_chapters(path):
    path = guarded(Path(os.path.abspath(path)), STAGING)
    if path.name != 'chapters' or not path.is_dir():
        raise ValueError('Pass a disposable chapters copy under .stage')
    for entry in path.iterdir():
        guarded(entry, STAGING)
        if not entry.is_file() or entry.stat().st_nlink != 1:
            raise ValueError(f'Expected a private chapter file: {entry}')
    return str(path)


def stage(args):
    if args.apply_dev and args.kind != 'quest':
        raise ValueError('Only an explicit quest title change can be applied to dev')
    relative = QUESTS / 'lang' / f'{args.locale}.snbt' if args.kind == 'quest' else Path('waymarker.nbt')
    if args.kind == 'quest':
        if not re.fullmatch(r'[0-9A-F]{16}', args.id or '') or not args.title or any(ord(c) < 32 for c in args.title):
            raise ValueError('Provide --id (uppercase hex) and a single-line --title')
        source, content = quest_edit(args.id, args.locale, args.title)
    elif args.kind == 'building':
        import gzip
        import nbt
        ints = lambda values: nbt.ListTag(nbt.TAG_INT, map(nbt.Int, values))
        content = gzip.compress(nbt.dumps({
            'DataVersion': nbt.Int(3955), 'size': ints([1, 2, 1]),
            'palette': nbt.ListTag(nbt.TAG_COMPOUND, [{'Name': nbt.Str('minecraft:stone_bricks')},
                                                     {'Name': nbt.Str('minecraft:torch')}]),
            'blocks': nbt.ListTag(nbt.TAG_COMPOUND, [
                {'pos': ints([0, height, 0]), 'state': nbt.Int(height)} for height in range(2)]),
            'entities': nbt.ListTag(nbt.TAG_COMPOUND, []),
        }), mtime=0)
        source = Path(__file__)
    target = dev_target(DEV / relative) if args.apply_dev else None
    if target:
        from perf_suite import require_idle
        require_idle()
        if not target.is_file() or target.stat().st_nlink != 1 or sha(target) != sha(source):
            raise ValueError('Dev quest differs from reviewed source; reconcile before applying')
    record = {'task': args.kind, 'source': str(source.relative_to(ROOT)), 'baseline_sha256': sha(source),
              'output': relative.as_posix(), 'output_sha256': hashlib.sha256(content).hexdigest(),
              'dev_target': str(target) if target else None,
              'verification': 'only the existing localized title was replaced' if args.kind == 'quest' else 'verify building with NBT reader',
              'rollback': 'restore before.snbt after checking current hash' if target else 'discard stage directory'}
    if args.kind == 'quest':
        record['edit'] = {'id': args.id, 'locale': args.locale, 'title': args.title}
    if args.command == 'plan':
        report(record)
        return
    guarded(STAGING / 'check', STAGING)
    STAGING.mkdir(exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix=f'{args.kind}-', dir=STAGING))
    output = guarded(run / relative, STAGING)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(content)
    if target:
        shutil.copyfile(target, run / 'before.snbt')
    (run / 'record.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    if target:
        require_idle()
        dev_target(target)
        if sha(target) != record['baseline_sha256']:
            raise ValueError('Dev quest changed during staging')
        with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as temp:
            temp.write(content)
        pending = Path(temp.name)
        try:
            os.replace(pending, dev_target(target))
        finally:
            pending.unlink(missing_ok=True)
    report(dict(record, stage=str(run)))


def verify(args):
    if args.kind == 'perf':
        preflight()
        report({'performance_preflight': 'passed'})
        if args.pilot:
            subprocess.run([sys.executable, '-B', str(ROOT / '_five/dev_perf_suite.py'),
                            '--pilot', '--spark-background', 'off'], check=True)
        return
    if args.pilot or not args.artifact:
        raise ValueError('Provide --artifact for static verification')
    artifact = guarded(Path(os.path.abspath(args.artifact)), STAGING)
    record = json.loads(guarded(artifact / 'record.json', STAGING).read_text(encoding='utf-8'))
    output = guarded(artifact / record['output'], artifact)
    if record['task'] != args.kind or sha(output) != record['output_sha256']:
        raise ValueError('Artifact does not match its staging record')
    if args.kind == 'quest':
        edit = record['edit']
        if edit['locale'] not in ('en_us', 'zh_cn') or not re.fullmatch(r'[0-9A-F]{16}', edit['id']):
            raise ValueError('Invalid quest record')
        source, expected = quest_edit(edit['id'], edit['locale'], edit['title'])
        if sha(source) != record['baseline_sha256'] or output.read_bytes() != expected:
            raise ValueError('Quest artifact differs from the expected single-title edit')
    if args.kind == 'building':
        from nbt_read import load
        template = load(str(output))
        if (template['size'] != [1, 2, 1] or template['entities']
                or [entry['Name'] for entry in template['palette']] != ['minecraft:stone_bricks', 'minecraft:torch']
                or template['blocks'] != [{'pos': [0, 0, 0], 'state': 0},
                                          {'pos': [0, 1, 0], 'state': 1}]):
            raise ValueError('Unexpected waymarker structure')
    report({'verified': str(output)})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    doctor = commands.add_parser('doctor')
    doctor.add_argument('--mods', action='store_true', help='Verify the managed mod manifest and standard compatibility copies')
    for name in ('plan', 'stage'):
        cmd = commands.add_parser(name)
        cmd.add_argument('kind', choices=['quest', 'building'])
        cmd.add_argument('--locale', choices=['en_us', 'zh_cn'], default='en_us')
        cmd.add_argument('--id')
        cmd.add_argument('--title')
        cmd.add_argument('--apply-dev', action='store_true')
    check = commands.add_parser('verify')
    check.add_argument('kind', choices=['quest', 'building', 'perf'])
    check.add_argument('--artifact')
    check.add_argument('--pilot', action='store_true')
    args = parser.parse_args()
    if args.command == 'doctor':
        if args.mods:
            from tools.modpack_state import audit
            state = audit(DEV)
            report(state)
            if not state['consistent']:
                raise SystemExit(1)
            return
        report({'python': sys.version.split()[0], 'git': bool(shutil.which('git')),
                'dev': DEV.is_dir(), 'release': RELEASE.is_dir(), 'world': WORLD.is_dir(),
                'quest_source': (ROOT / 'pack/quests').is_dir(),
                'local_perf_baseline': (PERF / 'setup.json').is_file()})
    elif args.command == 'verify':
        verify(args)
    else:
        stage(args)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        sys.exit(str(exc))
