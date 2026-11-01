"""One consolidated Windows evidence TXT, plus JSON; one Notepad on finish."""
from __future__ import annotations
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback
import uuid

ROOT = Path(__file__).resolve().parents[1]
CP01_MANIFEST_PIN = 'dafb4eac987d6a3422df79c7d48e787a76dfafd70dcd5841bb9a252b00ce4add'


def evidence_dir() -> Path:
    if os.name == 'nt' and Path('D:/Assets').exists():
        return Path(r'D:\Assets\MMDAnimeStudioLab\Evidence')
    if os.name == 'nt':
        return Path(os.environ.get('LOCALAPPDATA', str(ROOT))) / 'MMDAnimeStudioLab' / 'Evidence'
    return ROOT / 'Evidence'


def verify_pins() -> tuple[bool, str]:
    try:
        root = ROOT.resolve()
        if os.name == 'nt':
            protected = Path(r'D:\MMD\mmd-asset-registry').resolve()
            if root == protected or protected in root.parents:
                return False, 'HOLD_PROTECTED_STUDIO_ROOT'
        orig = ROOT / 'PACKAGE_MANIFEST_SHA256.json'
        if hashlib.sha256(orig.read_bytes()).hexdigest() != CP01_MANIFEST_PIN:
            return False, 'HOLD_CP01_MANIFEST_CHANGED'
        for label, source, count in (
            ('CP01', orig, 24), ('CP02', ROOT / 'cp02' / 'PACKAGE_CP02_SHA256.json', 0),
        ):
            blob = json.loads(source.read_text(encoding='utf-8'))
            entries = blob.get('files')
            if not isinstance(entries, list) or len(entries) < count:
                return False, 'HOLD_' + label + '_MANIFEST_INVALID'
            for ent in entries:
                relative = Path(ent['path'])
                if relative.is_absolute() or '..' in relative.parts:
                    return False, 'HOLD_MANIFEST_UNSAFE_PATH'
                target = (ROOT / relative).resolve()
                if not target.is_relative_to(root) or not target.is_file():
                    return False, 'HOLD_' + label + '_FILE_UNSAFE_OR_MISSING: ' + str(relative)
                if target.stat().st_size != ent['bytes'] or hashlib.sha256(target.read_bytes()).hexdigest() != ent['sha256']:
                    return False, 'HOLD_' + label + '_SHA_MISMATCH: ' + str(relative)
        return True, 'PASS_CP01_24_AND_CP02_PINNED_FILES'
    except (OSError, TypeError, KeyError, ValueError) as exc:
        return False, 'HOLD_PIN_CHECK: ' + type(exc).__name__


def run(mode: str) -> int:
    folder = evidence_dir()
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print('HOLD_EVIDENCE_DIR: ' + str(exc))
        return 4
    token = datetime.now().strftime('%Y%m%dT%H%M%S_%f') + '_PID' + str(os.getpid()) + '_' + uuid.uuid4().hex[:8]
    prefix = 'MMD_LAB_CP02_' + mode.upper() + '_' + token
    txt = folder / (prefix + '.txt')
    result_json = folder / (prefix + '.json')
    exit_code, status = 4, 'HOLD'
    try:
        with txt.open('x', encoding='utf-8') as f:
            f.write(f'CHECKPOINT=LAB_CP02\nMODE={mode.upper()}\nROOT={ROOT}\n')
            f.write('CANONICAL_REPO_ACCESS=NONE\nGIT_WRITE=NONE\nNETWORK=NONE\nREAL_ASSET_IO=DENIED\n')
            f.write(f'PYTHON={sys.version.split()[0]}\n')
            verified, gate = verify_pins()
            f.write(f'GATE_PIN={gate}\n')
            if sys.version_info < (3, 12) or not verified:
                f.write('RESULT=HOLD\nEXIT_CODE=4\n')
            else:
                if mode == 'qa':
                    cmd = [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'cp02/tests', '-v']
                elif mode == 'gui':
                    cmd = [sys.executable, '-B', '-m', 'cp02.desktop']
                else:
                    raise ValueError('unknown CP02 mode')
                env = os.environ.copy()
                env['PYTHONPATH'] = str(ROOT / 'src') + os.pathsep + str(ROOT) + os.pathsep + env.get('PYTHONPATH', '')
                f.write('COMMAND=' + ' '.join(cmd) + '\n')
                f.flush()
                process = subprocess.run(cmd, cwd=ROOT, env=env, stdout=f,
                                         stderr=subprocess.STDOUT, check=False)
                exit_code = process.returncode
                status = 'PASS' if exit_code == 0 else ('HOLD' if exit_code == 4 else 'FAIL')
                f.write(f'\nRESULT={status}\nEXIT_CODE={exit_code}\n')
    except Exception:
        exit_code, status = 5, 'FAIL'
        with txt.open('a', encoding='utf-8') as f:
            f.write(traceback.format_exc() + '\nRESULT=FAIL\nEXIT_CODE=5\n')
    try:
        result_json.write_text(json.dumps({'checkpoint': 'LAB_CP02', 'mode': mode,
            'result': status, 'exit_code': exit_code, 'evidence_txt': str(txt),
            'repo_git_write': False, 'real_asset_io': False}, indent=2), encoding='utf-8')
    except OSError as exc:
        print(f'RESULT_JSON=HOLD {exc}', flush=True)
        if exit_code == 0:
            exit_code, status = 6, 'FAIL'
            with txt.open('a', encoding='utf-8') as f:
                f.write('RESULT_JSON=FAIL\nRESULT=FAIL\nEXIT_CODE=6\n')
    print(f'EVIDENCE_TXT={txt}\nRESULT_JSON={result_json}\nRESULT={status}\nEXIT_CODE={exit_code}', flush=True)
    if os.name == 'nt':
        try:
            subprocess.Popen(['notepad.exe', str(txt)], close_fds=True)
        except OSError as exc:
            print('NOTEPAD=HOLD ' + str(exc), flush=True)
    return exit_code


if __name__ == '__main__':
    if len(sys.argv) != 2 or sys.argv[1] not in ('qa', 'gui'):
        raise SystemExit('Usage: python cp02/runner.py qa|gui')
    raise SystemExit(run(sys.argv[1]))
