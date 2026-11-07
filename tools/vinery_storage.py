"""Build the cross-mod bottle rendering candidate, then optionally apply to local dev."""
import argparse
from copy import copy
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from workflow import DEV, ROOT, STAGING, VERSIONS, guarded, sha

NAME = 'letsdo-vinery-neoforge-1.5.6.jar'
INPUT = '8a4cbcf80fd2089545c769bb1b665dcdd17a56c285cc0bb66b9881a3b53df327'
PREFIX = 'net/satisfy/vinery/client/render/block/storage/'
CLASSES = ['BottleRenderer', 'BigBottleRenderer', 'WineBoxRenderer']
NESTED = 'META-INF/jars/foundation-neoforge-1.0.7.jar'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply-dev', action='store_true')
    args = parser.parse_args()
    stage = guarded(STAGING / 'vinery-storage', STAGING)
    stage.mkdir(parents=True, exist_ok=True)
    source = guarded(DEV / 'mods' / NAME, DEV)
    if sha(source) != INPUT:
        raise ValueError('Expected the P11 Vinery baseline, refusing to overwrite')
    before = stage / 'before.jar'
    if before.exists() and sha(before) != INPUT:
        raise ValueError('Existing backup differs')
    if not before.exists():
        shutil.copy2(source, before)
    asm = VERSIONS.parent / 'libraries/org/ow2/asm/asm/9.8/asm-9.8.jar'
    java = ROOT / 'tools/VineryStoragePatch.java'
    # Java source launch rejects a UTF-8 BOM.
    patched = {}
    with ZipFile(source) as archive:
        if any(n.upper().endswith(('.SF', '.RSA', '.DSA')) for n in archive.namelist()):
            raise ValueError('Signed JAR')
        foundation = archive.read(NESTED)
        assert hashlib.sha256(foundation).hexdigest() == '590cbea7b6eba0a10e07cb7a0b0db3d86131a235053c28c204b67ead9f12bfdc'
        with ZipFile(io.BytesIO(foundation)) as nested:
            assert 'net/satisfy/foundation/storage/BottleGroupRenderer.class' in nested.namelist()
        for name in CLASSES:
            member = PREFIX + name + '.class'
            original, output = stage / (name + '.class'), stage / (name + '.patched.class')
            original.write_bytes(archive.read(member))
            subprocess.run(['java', '-cp', str(asm), str(java), str(original), str(output)], check=True)
            patched[member] = output.read_bytes()
        helper = stage / 'DshBottleState.class'
        subprocess.run(['java', '-cp', str(asm), str(java), 'helper', str(helper)], check=True)
        patched[PREFIX + helper.name] = helper.read_bytes()
        candidate = stage / NAME
        with ZipFile(candidate, 'w') as output:
            for member in archive.infolist():
                output.writestr(copy(member), patched.get(member.filename, archive.read(member)))
            output.writestr(PREFIX + helper.name, helper.read_bytes())
        with ZipFile(candidate) as output:
            assert set(output.namelist()) - set(archive.namelist()) == {PREFIX + helper.name}
            changed = [n for n in archive.namelist() if output.read(n) != archive.read(n)]
            assert set(changed) == {PREFIX + n + '.class' for n in CLASSES}
    record = dict(input_sha256=INPUT, output_sha256=sha(candidate),
                  foundation_sha256=hashlib.sha256(foundation).hexdigest(),
                  changed=changed, added=PREFIX + helper.name,
                  validation='Member diff and bytecode checked; game rendering pending')
    (stage / 'record.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    if args.apply_dev:
        assert sha(source) == INPUT and sha(before) == INPUT
        temporary = guarded(source.with_suffix('.jar.storage-tmp'), DEV)
        if temporary.exists():
            raise ValueError('Existing temporary candidate')
        shutil.copyfile(candidate, temporary)
        assert sha(temporary) == record['output_sha256']
        try:
            temporary.replace(source)
        except PermissionError:
            temporary.unlink()
            raise SystemExit('Dev Vinery JAR is in use. Exit the local dev game, then retry --apply-dev.')
        assert sha(source) == record['output_sha256']
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
