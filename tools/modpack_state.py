"""Read-only inventory of standard and AutoModpack managed files."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath


def digest(path, algorithm='sha256'):
    return hashlib.new(algorithm, path.read_bytes()).hexdigest()


def managed_files(instance):
    instance = instance.resolve()
    config = instance / 'automodpack/automodpack-client.json'
    if not config.exists():
        return None, {}
    selected = json.loads(config.read_text(encoding='utf-8')).get('selectedModpack', '')
    if not selected:
        return None, {}
    if selected in {'.', '..'} or '/' in selected or '\\' in selected or ':' in selected:
        raise ValueError('Invalid selected modpack')
    root = (instance / 'automodpack/modpacks' / selected).resolve()
    root.relative_to(instance)
    manifest = root / 'automodpack-content.json'
    if not manifest.exists():
        raise ValueError('Selected pack has no manifest')
    entries = {}
    for row in json.loads(manifest.read_text(encoding='utf-8'))['list']:
        name = row['file'].removeprefix('/')
        parts = PurePosixPath(name)
        if not name or '\\' in name or ':' in name or '..' in parts.parts or parts.is_absolute():
            raise ValueError('Unsafe manifest path')
        if name.casefold() in entries:
            raise ValueError('Duplicate manifest path')
        (root / name).resolve().relative_to(root)
        entries[name.casefold()] = row
    return root, entries


def resolve_source(instance, relative):
    """Resolve an explicitly selected publication input; no recursive inclusion."""
    instance = instance.resolve()
    normal = (instance / relative).resolve()
    normal.relative_to(instance)
    root, entries = managed_files(instance)
    item = entries.get(relative.casefold())
    if item is not None:
        managed = (root / item['file'].removeprefix('/')).resolve()
        managed.relative_to(root)
        if not managed.is_file() or digest(managed, 'sha1') != item['sha1']:
            raise ValueError('Managed input is missing or differs: ' + relative)
        # Editable config is intentionally read from the running instance.
        if item.get('editable') and normal.is_file():
            return normal
        if relative.startswith('mods/') and normal.is_file() and digest(normal) != digest(managed):
            raise ValueError('Conflicting enabled copies: ' + relative)
        return managed
    if not normal.is_file():
        raise ValueError('Selected input not found: ' + relative)
    return normal


def audit(instance):
    instance = instance.resolve()
    root, entries = managed_files(instance)
    problems, managed = [], []
    for key, item in sorted(entries.items()):
        if not key.startswith('mods/') or not key.endswith('.jar'):
            continue
        path = root / item['file'].removeprefix('/')
        ok = path.is_file() and path.stat().st_size == int(item['size']) and digest(path, 'sha1') == item['sha1']
        managed.append({'file': item['file'], 'verified': ok})
        if not ok:
            problems.append('Missing or changed managed JAR: ' + item['file'])
    if root:
        for path in (root / 'mods').glob('*.jar'):
            if ('mods/' + path.name).casefold() not in entries:
                problems.append('Unlisted managed JAR may be loaded: ' + path.name)
    standard = []
    for path in sorted((instance / 'mods').glob('*.jar')):
        row = entries.get(('mods/' + path.name).casefold())
        if path.name == 'automodpack-mc1.21.1-neoforge-4.0.7.jar':
            role = 'bootstrap'
        elif row:
            role = 'managed compatibility copy'
            if digest(path, 'sha1') != row['sha1']:
                problems.append('Conflicting compatibility copy: ' + path.name)
        else:
            role = 'unmanaged'
            problems.append('Enabled JAR outside managed manifest: ' + path.name)
        standard.append({'file': path.name, 'role': role, 'sha256': digest(path)})
    if not any(row['role'] == 'bootstrap' for row in standard):
        problems.append('AutoModpack bootstrap missing')
    mode = 'local-development' if root and (root / '.dsh-local-profile').is_file() else 'remote-managed'
    return {'instance': str(instance), 'managed_root': str(root), 'profile_mode': mode, 'managed_jars': managed,
            'standard_jars': standard, 'problems': problems, 'consistent': not problems}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--instance', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.instance)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result['consistent'] else 1)
