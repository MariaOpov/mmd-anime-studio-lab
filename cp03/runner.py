"""Independent CP03 offline QA/demo runner: one unique TXT + JSON + Notepad."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
CP01_MANIFEST_PIN = 'dafb4eac987d6a3422df79c7d48e787a76dfafd70dcd5841bb9a252b00ce4add'
CP02_MANIFEST_PIN = '44858f980df6fa150951d879506452ea995ae847717ee56551069c0b3b3ffe6f'


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify() -> None:
    for label, rel, pin, count in (
        ('CP01', 'PACKAGE_MANIFEST_SHA256.json', CP01_MANIFEST_PIN, 24),
        ('CP02', 'cp02/PACKAGE_CP02_SHA256.json', CP02_MANIFEST_PIN, 12),
        ('CP03', 'cp03/PACKAGE_CP03_SHA256.json', None, 12),
    ):
        man = ROOT / rel
        if pin and sha(man) != pin:
            raise ValueError(label + '_MANIFEST_SHA_MISMATCH')
        files = json.loads(man.read_text(encoding='utf-8'))['files']
        if len(files) != count:
            raise ValueError(label + '_MANIFEST_COUNT_MISMATCH')
        for e in files:
            p = Path(e['path'])
            if p.is_absolute() or '..' in p.parts or (ROOT / p).is_symlink():
                raise ValueError(label + '_UNSAFE_PATH')
            dest = ROOT / p
            if not dest.is_file() or dest.stat().st_size != e['bytes'] or sha(dest) != e['sha256']:
                raise ValueError(label + '_FILE_SHA_MISMATCH_' + str(p))


def run(mode: str) -> int:
    if os.name == 'nt' and Path(r'D:\Assets').is_dir():
        evidence = Path(r'D:\Assets\MMDAnimeStudioLab\Evidence')
    elif os.name == 'nt':
        evidence = Path(os.environ.get('LOCALAPPDATA', str(ROOT))) / 'MMDAnimeStudioLab' / 'Evidence'
    else:
        evidence = ROOT / 'Evidence'
    evidence.mkdir(parents=True, exist_ok=True)
    token = datetime.now().strftime('%Y%m%dT%H%M%S_%f') + '_PID' + str(os.getpid()) + '_' + uuid.uuid4().hex[:8]
    base = evidence / ('MMD_LAB_CP03_' + mode.upper() + '_' + token)
    txt, result_json = Path(str(base) + '.txt'), Path(str(base) + '.json')
    exit_code, result = 4, 'HOLD'
    with txt.open('x', encoding='utf-8') as f:
        f.write('CHECKPOINT=LAB_CP03_' + mode.upper() + '\nMODE=OFFLINE_SYNTHETIC_SOURCE_ONLY\n')
        f.write('GIT_WRITE=NONE\nNETWORK=NONE\nREAL_ASSETS=NONE\nGUI=NOT_STARTED\n')
        try:
            verify()
            f.write('GATE_CP01_CP02_CP03_PINS=PASS\n')
            env = os.environ.copy()
            env['PYTHONPATH'] = str(ROOT) + os.pathsep + str(ROOT / 'src') + os.pathsep + env.get('PYTHONPATH', '')
            commands = ([[sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'cp03/tests', '-v']]
                        if mode == 'qa' else [[sys.executable, '-B', '-m', 'cp03.cli', which] for which in ('morph', 'motion')])
            for cmd in commands:
                f.write('COMMAND=' + ' '.join(cmd) + '\n'); f.flush()
                p = subprocess.run(cmd, cwd=ROOT, env=env, stdout=f, stderr=subprocess.STDOUT, check=False)
                if p.returncode:
                    exit_code, result = p.returncode, 'FAIL'
                    break
            else:
                exit_code, result = 0, 'PASS'
        except Exception as ex:
            f.write('GATE=HOLD_' + type(ex).__name__ + ':' + str(ex) + '\n')
        f.write(f'RESULT={result}\nEXIT_CODE={exit_code}\n')
    try:
        result_json.write_text(json.dumps({'checkpoint': 'LAB_CP03_' + mode.upper(), 'result': result,
            'exit_code': exit_code, 'txt': str(txt)}, indent=2), encoding='utf-8')
    except OSError as ex:
        print('RESULT_JSON=FAIL ' + str(ex), flush=True)
        if exit_code == 0:
            exit_code, result = 6, 'FAIL'
            with txt.open('a', encoding='utf-8') as f:
                f.write('RESULT_JSON=FAIL\nRESULT=FAIL\nEXIT_CODE=6\n')
    print(f'EVIDENCE_TXT={txt}\nRESULT_JSON={result_json}\nRESULT={result}\nEXIT_CODE={exit_code}', flush=True)
    if os.name == 'nt':
        try: subprocess.Popen(['notepad.exe', str(txt)], close_fds=True)
        except OSError as ex: print('NOTEPAD=HOLD ' + str(ex), flush=True)
    return exit_code


if __name__ == '__main__':
    if len(sys.argv) != 2 or sys.argv[1] not in ('qa', 'demo'):
        raise SystemExit('Usage: runner.py qa|demo')
    raise SystemExit(run(sys.argv[1]))
