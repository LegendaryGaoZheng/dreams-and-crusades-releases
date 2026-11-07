"""Read-only Release directory archive; exclude saves, backups and credentials."""
from pathlib import Path
import hashlib
import json
import re
from zipfile import ZipFile, ZIP_DEFLATED, ZIP_STORED

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path('C:/Users/Legen/Desktop/游戏/.minecraft/versions/梦想与远征_Release')
OUT = ROOT / '.stage/release-instance-20261107'


def excluded(relative):
    parts = [p.lower() for p in relative.parts]
    name = parts[-1]
    if parts[0] == 'saves': return 'world/save'
    if any(p in {'backups', 'backup', '_backups', '_backup'} or '_backup' in p for p in parts): return 'backup'
    if name.endswith(('.bak', '.orig', '_bak', '.dat_old', '.pre_questfix')): return 'backup'
    if name in {'automodpack-client-secrets.json', 'automodpack-secrets.json', 'accounts.json', 'launcher_accounts.json', 'key.pem', 'private-key.pem'}: return 'credential/private key'
    return None


def main():
    global OUT
    index = 1
    while OUT.exists():
        index += 1
        OUT = ROOT / '.stage' / ('release-instance-20261107-' + str(index).zfill(2))
    OUT.mkdir(parents=True, exist_ok=False)
    files, omitted = [], []
    for path in sorted(SOURCE.rglob('*')):
        if not path.is_file(): continue
        relative = path.relative_to(SOURCE)
        if path.resolve() != path.absolute(): raise ValueError('Source alias/reparse point requires review: ' + str(relative))
        reason = excluded(relative)
        if reason:
            omitted.append({'path': relative.as_posix(), 'reason': reason}); continue
        files.append((relative, path))
    archive = OUT / 'dreams-and-crusades-release-instance-20261107.zip'
    manifest = []
    with ZipFile(archive, 'w', allowZip64=True) as z:
        for relative, path in files:
            before = path.stat()
            try:
                data = path.read_bytes()
            except PermissionError as error:
                (OUT / 'failure.json').write_text(json.dumps({'path': relative.as_posix(), 'reason': 'locked/unreadable source file'}, ensure_ascii=False), encoding='utf-8')
                raise RuntimeError('Source file locked: ' + str(relative)) from error
            # Do not publish actual credentials accidentally embedded in text logs/configs.
            if path.suffix.lower() in {'.json', '.txt', '.log', '.toml', '.properties', '.cfg', '.ini'}:
                text = data.decode('utf-8', errors='ignore')
                token = re.search(r'gh[pousr]_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{30,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----', text)
                credential = re.search(r'"(?:accessToken|refreshToken|clientToken|password)"\s*:\s*"([^"\s]{12,})"', text, re.I)
                if token or credential:
                    omitted.append({'path': relative.as_posix(), 'reason': 'credential detected in text'}); continue
            after = path.stat()
            if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                raise ValueError('Source changed while reading: ' + str(relative))
            kind = ZIP_STORED if path.suffix.lower() in {'.jar', '.zip', '.png', '.gz'} else ZIP_DEFLATED
            z.writestr(relative.as_posix(), data, compress_type=kind, compresslevel=1 if kind == ZIP_DEFLATED else None)
            manifest.append({'path': relative.as_posix(), 'size': len(data), 'sha256': hashlib.sha256(data).hexdigest(), 'mtime_ns': after.st_mtime_ns})
    # Verify every archive member against the read-time file manifest.
    with ZipFile(archive) as z:
        assert set(z.namelist()) == {r['path'] for r in manifest}
        for row in manifest:
            assert hashlib.sha256(z.read(row['path'])).hexdigest() == row['sha256']
            path = SOURCE / row['path']
            stat = path.stat()
            if (stat.st_size, stat.st_mtime_ns) != (row['size'], row['mtime_ns']):
                raise ValueError('Source changed during archive: ' + row['path'])
    summary = {'source': str(SOURCE), 'files': manifest, 'excluded': omitted,
        'archive': archive.name, 'bytes': archive.stat().st_size,
        'sha256': hashlib.file_digest(archive.open('rb'), 'sha256').hexdigest(),
        'format': 'exact instance-directory archive, not a tested standalone installer'}
    (OUT / 'manifest.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'archive': str(archive), 'included': len(manifest), 'excluded': len(omitted), 'bytes': summary['bytes'], 'sha256': summary['sha256']}))


if __name__ == '__main__': main()
