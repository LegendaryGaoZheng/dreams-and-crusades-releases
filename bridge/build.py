"""Build the LGPL AutoModpack 4.0.7 D&C bridge with pinned upstream inputs."""
import argparse
from copy import copy
import hashlib
import json
from pathlib import Path
import subprocess
import urllib.request
from zipfile import ZipFile, ZipInfo

BASELINE = 'c76ac8e4c754ba39d1baee3a8ac146be9bfddfad58fa10cc48527d4accd47ce7'
SOURCE_SHA = '2e1777937f535e24ba02124ece0e0575155982f11f1271e21cb7078bb2f510cb'
OWNER = 'pl/skidam/automodpack_loader_core/client/'
NAME = 'automodpack-mc1.21.1-neoforge-4.0.7.jar'
MOD_URL = 'https://cdn.modrinth.com/data/k68glP2e/versions/QpFRQTSU/' + NAME
SOURCE_URL = 'https://raw.githubusercontent.com/Skidamek/AutoModpack/v4.0.7/loader/core/src/main/java/' + OWNER + 'ModpackUpdater.java'


def download(path, url, expected):
    if not path.exists():
        with urllib.request.urlopen(url, timeout=30) as response:
            content = response.read()
        if hashlib.sha256(content).hexdigest() != expected:
            raise ValueError('Upstream input hash mismatch')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError('Existing input hash mismatch')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, default=Path(__file__).resolve().parents[1] / '.stage/update-pilot')
    args = parser.parse_args()
    stage = args.workspace.resolve()
    stage.mkdir(parents=True, exist_ok=True)
    original = stage / NAME
    source = stage / 'upstream-ModpackUpdater.java'
    download(original, MOD_URL, BASELINE)
    download(source, SOURCE_URL, SOURCE_SHA)
    text = source.read_text(encoding='utf-8')
    old = '                    } else {\n                        startUpdate(filesToUpdate);\n                    }'
    assert text.count(old) == 1
    text = text.replace(old, '                    } else {\n                        showDangerScreen(parentScreen, filesToUpdate);\n                    }')
    old = '            // DOWNLOAD\n'
    assert text.count(old) == 1
    text = text.replace(old, old + '            DshReleaseSources.refresh();\n')
    old = '                    List<String> urls = new ArrayList<>();'
    assert text.count(old) == 1
    text = text.replace(old, '                    List<String> urls = new ArrayList<>(DshReleaseSources.urls(serverItem));')
    build = stage / 'bridge'
    build.mkdir(exist_ok=True)
    (build / 'ModpackUpdater.java').write_text(text, encoding='utf-8')
    helper = Path(__file__).resolve().parent / 'DshReleaseSources.java'
    deps = [original]
    for group, artifact, version, checksum in [
        ('com/google/code/gson','gson','2.13.2','dd0ce1b55a3ed2080cb70f9c655850cda86c206862310009dcb5e5c95265a5e0'),
        ('org/apache/logging/log4j','log4j-api','2.25.2','9fd66c9fe0bea06fa9666c147989a46cafaa92b4a88753697d3945cc43338cbb')]:
        url = f'https://repo.maven.apache.org/maven2/{group}/{artifact}/{version}/{artifact}-{version}.jar'
        path = stage / 'dependencies' / (artifact + '.jar')
        download(path, url, checksum)
        deps.append(path)
    classes = build / 'classes'
    import os
    subprocess.run(['javac','--release','21','-encoding','UTF-8','-cp',os.pathsep.join(map(str,deps)),
                    '-d',str(classes),str(build/'ModpackUpdater.java'),str(helper)],check=True)
    replacements={p.relative_to(classes).as_posix():p.read_bytes() for p in classes.rglob('*.class')}
    assert set(replacements)=={OWNER+n+'.class' for n in ['ModpackUpdater','DshReleaseSources','DshReleaseSources$Entry']}
    additions = {
        'META-INF/dsh-sources/ModpackUpdater.java': text.encode(),
        'META-INF/dsh-sources/DshReleaseSources.java': helper.read_bytes(),
        'META-INF/dsh-sources/build.py': Path(__file__).read_bytes(),
        'META-INF/DREAMS-CRUSADES.txt': b'Modified AutoModpack 4.0.7 D&C bridge dsh1. LGPL-3.0.\nSource and rebuild instructions included in META-INF/dsh-sources and public release repository.\nUpstream https://github.com/Skidamek/AutoModpack/tree/v4.0.7\n'
    }
    output = build / 'automodpack-mc1.21.1-neoforge-4.0.7-dsh1.jar'
    with ZipFile(original) as before, ZipFile(output,'w') as after:
        for member in before.infolist():
            after.writestr(copy(member),replacements.get(member.filename,before.read(member)))
        for name,data in {**replacements,**additions}.items():
            if name not in before.namelist():
                after.writestr(ZipInfo(name,(2026,11,5,0,0,0)),data)
    with ZipFile(original) as before, ZipFile(output) as after:
        changed=[n for n in before.namelist() if before.read(n)!=after.read(n)]
        assert changed==[OWNER+'ModpackUpdater.class']
    record=dict(input_sha256=BASELINE,source_sha256=SOURCE_SHA,
                output_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),changed=changed,
                added=sorted((set(replacements)-set(changed)) | set(additions)))
    (build/'record.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(record,indent=2))


if __name__=='__main__':main()
