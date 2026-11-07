"""Stage pinned food/cosmetic mods and exact data fixes; apply only to local dev."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from zipfile import ZipFile
import tomllib

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from workflow import DEV, ROOT, STAGING, guarded
from tools.modpack_state import audit, managed_files

STAGE = STAGING / 'develop-food-20261107'
PROFILE = 'dreams-and-crusades-local-develop'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def stage():
    import urllib.request
    STAGE.mkdir(parents=True, exist_ok=True)
    (STAGE / 'downloads').mkdir(exist_ok=True)
    if not (STAGE / 'downloads.json').exists():
        shutil.copy2(ROOT / 'pack/develop-mods.json', STAGE / 'downloads.json')
    rows = json.loads((STAGE / 'downloads.json').read_text(encoding='utf-8'))
    overlays = {}
    inventory = []
    for row in rows:
        path = STAGE / 'downloads' / row['filename']
        if not path.exists():
            with urllib.request.urlopen(row['url'], timeout=60) as response:
                data = response.read()
            assert hashlib.sha512(data).hexdigest() == row['sha512']
            path.write_bytes(data)
        assert sha(path) == row['sha256']
        with ZipFile(path) as z:
            meta = tomllib.loads(z.read('META-INF/neoforge.mods.toml').decode())
            row['metadata'] = [{'modId': x['modId'], 'version': row['version']} for x in meta['mods']]
            recipes = {}
            for name in z.namelist():
                if name.startswith('data/') and '/recipe/' in name and name.endswith('.json'):
                    recipes[name] = json.loads(z.read(name))
            inventory.append({'project': row['project'], 'recipes': recipes})
            if row['project'] == 'crabbers-delight':
                name = 'data/crabbersdelight/recipe/integration/create/compacting/coconut_milk.json'
                recipe = recipes[name]
                assert recipe['results'][0]['id'] == 'hearthandharvest:coconut_milk'
                recipe['results'][0]['id'] = 'crabbersdelight:coconut_milk'
                overlays[name] = recipe
            if row['project'] == 'cosmeticarmours':
                name = 'data/cosmeticarmoursmod/recipe/sword_sheath_gilded_netherite_rec.json'
                recipe = recipes[name]
                assert recipe['ingredients'][0]['item'] == 'cosmeticweaponsmod:gilded_netherite_sword'
                assert 'neoforge:conditions' not in recipe
                recipe['neoforge:conditions'] = [{'type': 'neoforge:mod_loaded', 'modid': 'cosmeticweaponsmod'}]
                overlays[name] = recipe
    overlays['data/forge/tags/item/tools/knives.json'] = {'replace': False, 'values': ['#c:tools/knife']}
    output = STAGE / 'overlays'
    for name, value in overlays.items():
        dump(output / name, value)
    dump(STAGE / 'recipe-inventory.json', inventory)
    dump(STAGE / 'reviewed-mods.json', rows)
    return rows, overlays


def apply(rows, overlays):
    require_game_closed()
    # Only a verified dev path is accepted; guards reject junction escape.
    config_path = guarded(DEV / 'automodpack/automodpack-client.json', DEV)
    current, _ = managed_files(DEV)
    if not current:
        raise ValueError('No baseline selected')
    target = guarded(DEV / 'automodpack/modpacks' / PROFILE, DEV)
    if target.exists():
        raise ValueError('Local develop snapshot already exists')
    backup = STAGE / 'before'
    backup.mkdir(exist_ok=False)
    original_config = config_path.read_bytes()
    (backup / 'automodpack-client.json').write_bytes(original_config)
    bootstrap = guarded(DEV / 'mods/automodpack-mc1.21.1-neoforge-4.0.7.jar', DEV)
    shutil.copy2(bootstrap, backup / 'automodpack.jar')
    baseline = {str(p.relative_to(current)): sha(p) for p in current.rglob('*') if p.is_file()}
    shutil.copytree(current, target)
    assert baseline == {str(p.relative_to(target)): sha(p) for p in target.rglob('*') if p.is_file()}
    manifest_path = target / 'automodpack-content.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest['modpackName'] = PROFILE
    def add_manifest(name, data, kind):
        manifest['list'] = [x for x in manifest['list'] if x['file'] != '/' + name]
        manifest['list'].append({'file': '/' + name, 'size': str(len(data)), 'sha1': hashlib.sha1(data).hexdigest(),
                                 'murmur': '0', 'type': kind, 'editable': False, 'forceCopy': False})
    for row in rows:
        src = STAGE / 'downloads' / row['filename']
        dest = target / 'mods' / row['filename']
        assert not dest.exists()
        shutil.copy2(src, dest)
        add_manifest('mods/' + row['filename'], dest.read_bytes(), 'mod')
    runtime_changes = []
    for name in overlays:
        relative = 'kubejs/' + name
        src = STAGE / 'overlays' / name
        dest = guarded(DEV / relative, DEV)
        if dest.exists():
            raise ValueError('Existing runtime overlay requires review: ' + relative)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        managed = target / relative
        managed.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, managed)
        add_manifest(relative, managed.read_bytes(), 'other')
        runtime_changes.append({'path': relative, 'sha256': sha(dest)})
    dump(manifest_path, manifest)
    (target / '.dsh-local-profile').write_text('Local develop snapshot. No remote update or publication.\n', encoding='utf-8')
    patched = STAGING / 'update-pilot/bridge/automodpack-mc1.21.1-neoforge-4.0.7-dsh2.jar'
    with ZipFile(patched) as z:
        assert b'.dsh-local-profile' in z.read('META-INF/dsh-sources/Preload.java')
    assert sha(patched) == json.loads((patched.parent / 'record.json').read_text())['output_sha256']
    shutil.copy2(patched, bootstrap)
    config = json.loads(original_config)
    config['selectedModpack'] = PROFILE
    config['updateSelectedModpackOnLaunch'] = False
    config['selfUpdater'] = False
    # Local snapshot is deliberately absent from installed remote hosts.
    config.get('installedModpacks', {}).pop(PROFILE, None)
    dump(config_path, config)
    assert baseline == {str(p.relative_to(current)): sha(p) for p in current.rglob('*') if p.is_file()}
    state = audit(DEV)
    assert state['consistent'], state['problems']
    dump(STAGE / 'after.json', state)
    dump(STAGE / 'install.json', {'profile': PROFILE, 'previous_profile': current.name,
         'baseline_sha256': baseline, 'bootstrap_sha256': sha(bootstrap), 'config_sha256': sha(config_path),
         'runtime_changes': runtime_changes, 'worlds_touched': False,
         'status': 'files installed; game launch and multiplayer not tested'})


def require_game_closed():
    result = subprocess.run(['powershell', '-NoProfile', '-Command',
        "@(Get-CimInstance Win32_Process -Filter \"Name = 'java.exe' OR Name = 'javaw.exe'\" | Where-Object { $_.CommandLine -match 'net.minecraft|forgeclient|BootstrapLauncher' }).Count"],
        check=True, capture_output=True, text=True)
    if int(result.stdout.strip()):
        raise ValueError('Minecraft is running; exit normally before applying or rolling back')


def rollback():
    require_game_closed()
    record = json.loads((STAGE / 'install.json').read_text(encoding='utf-8'))
    config = guarded(DEV / 'automodpack/automodpack-client.json', DEV)
    bootstrap = guarded(DEV / 'mods/automodpack-mc1.21.1-neoforge-4.0.7.jar', DEV)
    assert sha(config) == record['config_sha256'], 'Client config changed; manual review required'
    assert sha(bootstrap) == record['bootstrap_sha256'], 'Bootstrap changed; manual review required'
    for row in record['runtime_changes']:
        assert sha(guarded(DEV / row['path'], DEV)) == row['sha256'], 'Overlay changed; manual review required'
    for row in record['runtime_changes']:
        guarded(DEV / row['path'], DEV).unlink()
    shutil.copy2(STAGE / 'before/automodpack.jar', bootstrap)
    shutil.copy2(STAGE / 'before/automodpack-client.json', config)
    print('Runtime rolled back; develop snapshot retained for audit. Revert source commits separately if required.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument('--apply-dev', action='store_true')
    actions.add_argument('--rollback', action='store_true')
    args = parser.parse_args()
    if args.rollback:
        rollback()
        raise SystemExit(0)
    rows, overlays = stage()
    if args.apply_dev:
        apply(rows, overlays)
    print(json.dumps({'mods': len(rows), 'overlays': list(overlays), 'applied': args.apply_dev}))
