"""Build a reviewed release manifest and content-addressed GitHub Release assets.

No game files are changed. Selection JSON is an explicit list of relative paths.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from workflow import DEV, ROOT, STAGING, guarded
from tools.modpack_state import resolve_source

REPOSITORY = 'LegendaryGaoZheng/dreams-and-crusades-releases'
VERSION = re.compile(r'[0-9]+\.[0-9]+\.[0-9]+(?:-[a-z0-9.-]+)?')
DENIED = {'saves', 'playerdata', 'stats', 'advancements', 'logs', 'screenshots',
          'xaero', 'xaeroworldmap', 'xaerowaypoints', 'pcl', 'backups', '.git',
          '.private', 'cache'}
ROOTS = {'mods', 'kubejs', 'config', 'resourcepacks'}
BAD_NAMES = {'options.txt', 'servers.dat', 'usercache.json', 'usernamecache.json',
             'whitelist.json', 'ops.json', 'accounts.json', 'launcher_accounts.json'}


def safe_name(value):
    path = PurePosixPath(value)
    if not isinstance(value, str) or '\\' in value or ':' in value or value != path.as_posix():
        raise ValueError(f'Invalid relative path: {value!r}')
    if path.is_absolute() or len(path.parts) < 2 or any(p in {'.', '..', ''} for p in path.parts):
        raise ValueError(f'Invalid relative path: {value!r}')
    if path.parts[0] not in ROOTS or any(p.lower() in DENIED or p.startswith('.') for p in path.parts):
        raise ValueError(f'Personal or unsupported path: {value}')
    if path.name.lower() in BAD_NAMES or path.suffix.lower() in {'.log', '.jfr', '.bak', '.pem', '.key', '.disabled'}:
        raise ValueError(f'Excluded file: {value}')
    if any(term in path.name.lower() for term in ('account', 'credential', 'secret', 'token', 'password')):
        raise ValueError(f'Sensitive filename: {value}')
    return path


def validate_manifest(value):
    if value.get('format') != 1 or value.get('repository') != REPOSITORY:
        raise ValueError('Unexpected manifest origin or schema')
    if not VERSION.fullmatch(value.get('version', '')):
        raise ValueError('Invalid release version')
    seen = set()
    for item in value['files']:
        path = safe_name(item['path']).as_posix()
        if path.casefold() in seen:
            raise ValueError('Duplicate path')
        seen.add(path.casefold())
        if not re.fullmatch('[a-f0-9]{64}', item['sha256']) or type(item['size']) is not int or item['size'] < 0:
            raise ValueError('Invalid fingerprint')
        if not item['url'].startswith('https://'):
            raise ValueError('HTTPS download URL required')
    return value


def build(source, selection, version, previous=None):
    if not VERSION.fullmatch(version):
        raise ValueError('Use a release version such as 1.0.3-pilot.1')
    if source.resolve() != source:
        raise ValueError('Source aliases are not allowed')
    files = []
    blobs = {}
    seen = set()
    for selected in selection:
        item = {'path': selected} if isinstance(selected, str) else selected
        relative = safe_name(item['path'])
        name = relative.as_posix()
        if name.casefold() in seen:
            raise ValueError('Duplicate selection')
        seen.add(name.casefold())
        path = resolve_source(source, name)
        guarded(path, source)
        data = path.read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        url = item.get('url')
        if url is None:
            if item.get('redistribution_approved') is not True:
                raise ValueError(f'Explicit distribution review required: {name}')
            asset = sha + '.bin'
            blobs[asset] = data
            url = f'https://github.com/{REPOSITORY}/releases/download/v{version}/{asset}'
        files.append(dict(path=name, size=len(data), sha256=sha, url=url))
    removed = []
    if previous is not None:
        validate_manifest(previous)
        for item in previous['files']:
            if item['path'].casefold() not in seen:
                removed.append(dict(path=item['path'], expected_sha256=item['sha256']))
    manifest = dict(format=1, repository=REPOSITORY, version=version,
                    previous_version=previous['version'] if previous else None,
                    minecraft='1.21.1', loader='neoforge', loader_version='21.1.264',
                    files=sorted(files, key=lambda x: x['path']), removed=removed)
    return validate_manifest(manifest), blobs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selection', required=True, type=Path)
    parser.add_argument('--version', required=True)
    parser.add_argument('--previous', type=Path)
    parser.add_argument('--notes', required=True, type=Path, help='Reviewed Markdown for this exact release version')
    args = parser.parse_args()
    notes = args.notes.read_text(encoding='utf-8-sig')
    if args.notes.suffix.lower() != '.md' or args.version not in notes or len(notes.strip()) < 80:
        raise ValueError('A substantive Markdown changelog naming this version is required')
    selection = json.loads(args.selection.read_text(encoding='utf-8-sig'))
    previous = json.loads(args.previous.read_text(encoding='utf-8-sig')) if args.previous else None
    manifest, blobs = build(DEV, selection, args.version, previous)
    output = guarded(STAGING / 'releases' / args.version, STAGING)
    output.mkdir(parents=True, exist_ok=False)
    for name, data in blobs.items():
        (output / name).write_bytes(data)
    (output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (output / 'CHANGELOG.md').write_text(notes, encoding='utf-8')
    print(output)


if __name__ == '__main__':
    main()
