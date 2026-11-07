"""Run AutoModpack's native content and TLS transport pilot inside a fresh stage."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from workflow import ROOT, STAGING, VERSIONS, guarded

NAME = 'automodpack-mc1.21.1-neoforge-4.0.7.jar'
SHA = 'c76ac8e4c754ba39d1baee3a8ac146be9bfddfad58fa10cc48527d4accd47ce7'
URL = 'https://cdn.modrinth.com/data/k68glP2e/versions/QpFRQTSU/' + NAME


def main():
    stage = guarded(STAGING / 'update-pilot', STAGING)
    stage.mkdir(parents=True, exist_ok=True)
    jar = stage / NAME
    if not jar.exists():
        with urllib.request.urlopen(URL, timeout=30) as response:
            data = response.read()
        if hashlib.sha256(data).hexdigest() != SHA:
            raise ValueError('Upstream download hash differs')
        jar.write_bytes(data)
    if hashlib.sha256(jar.read_bytes()).hexdigest() != SHA:
        raise ValueError('Expected pinned AutoModpack 4.0.7')
    jars = [jar]
    libraries = VERSIONS.parent / 'libraries'
    for group in ['io/netty', 'com/google/code/gson/gson', 'org/apache/logging/log4j']:
        folder = libraries / group
        for artifact in ([folder] if group.endswith('/gson') else folder.iterdir()):
            if artifact.name == 'netty-all':
                continue
            versions = [p for p in artifact.iterdir() if p.is_dir()]
            if versions:
                version = max(versions, key=lambda p: tuple(map(int, re.findall(r'\d+', p.name))))
                jars.extend(version.glob('*.jar'))
    index = 1
    while (stage / f'native-{index:02d}').exists():
        index += 1
    run = stage / f'native-{index:02d}'
    run.mkdir()
    (run / 'log4j2.xml').write_text(
        '<Configuration><Appenders><Console name="out"><PatternLayout pattern="%level %msg%n%throwable"/>'
        '</Console></Appenders><Loggers><Root level="info"><AppenderRef ref="out"/></Root>'
        '</Loggers></Configuration>', encoding='utf-8')
    command = ['java', '-cp', ';'.join(map(str, jars)), str(ROOT / 'tools/AutoModpackPilot.java')]
    result = subprocess.run(command, cwd=run, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=55)
    (run / 'pilot.log').write_bytes(result.stdout)
    transport_passed = result.returncode == 0 and b'PILOT_PASS' in result.stdout
    accepted = transport_passed and b'POLICY_FAIL' not in result.stdout
    report = dict(accepted=accepted, transport_passed=transport_passed, exit_code=result.returncode, automodpack_sha256=SHA,
                  test='Native content generation and TLS transfer, not PCL or Minecraft',
                  pending=['live connection interruption', 'complete pack update', 'multiplayer'],
                  policy_failure='Native loader deletes unregistered files inside its managed directory' if not accepted else None)
    (run / 'result.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(run)
    print(result.stdout.decode('utf-8', errors='replace')[-6500:])
    if not transport_passed:
        raise SystemExit(1)
    if not accepted:
        raise SystemExit(2)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
