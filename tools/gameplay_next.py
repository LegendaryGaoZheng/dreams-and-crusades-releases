"""Build the version-pinned Vinery candidate without editing the instance."""
import argparse
from pathlib import Path
import subprocess
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from workflow import DEV, ROOT, STAGING, VERSIONS, guarded, sha

VINERY = 'letsdo-vinery-neoforge-1.5.6.jar'
ORIGINAL = '7e5e4e901a599a499bd510490ec12e72e8547e53b61790778fa7848852c451ec'
CLASS = 'net/satisfy/vinery/core/block/entity/FermentationBarrelBlockEntity.class'


def wine(source):
    if sha(source) != ORIGINAL:
        raise ValueError('Expected unmodified Vinery 1.5.6')
    stage = guarded(STAGING / 'gameplay-next/wine', STAGING)
    stage.mkdir(parents=True, exist_ok=True)
    original = stage / 'FermentationBarrelBlockEntity.class'
    patched = stage / 'patched.class'
    output = stage / VINERY
    asm = VERSIONS.parent / 'libraries/org/ow2/asm/asm/9.8/asm-9.8.jar'
    with zipfile.ZipFile(source) as archive:
        if any(n.upper().startswith('META-INF/') and n.upper().endswith(('.SF', '.RSA', '.DSA', '.EC'))
               for n in archive.namelist()):
            raise ValueError('Signed JAR cannot be patched')
        original.write_bytes(archive.read(CLASS))
        subprocess.run(['java', '-cp', str(asm), str(ROOT / 'tools/VineryBatchPatch.java'),
                        str(original), str(patched)], check=True)
        with zipfile.ZipFile(output, 'w') as result:
            for member in archive.infolist():
                result.writestr(member, patched.read_bytes() if member.filename == CLASS else archive.read(member))
    print(output, sha(output))
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['wine'])
    parser.add_argument('--source', type=Path, default=DEV / 'mods' / VINERY)
    args = parser.parse_args()
    wine(args.source)
