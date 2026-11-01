"""One-command Windows launcher, one unique evidence TXT opened in one Notepad."""
from __future__ import annotations
from datetime import datetime
from pathlib import Path
import json
import hashlib
import os
import subprocess
import sys
import traceback
import uuid

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"


def evidence_root() -> Path:
    if os.name == "nt":
        if Path(r"D:\Assets").is_dir():
            return Path(r"D:\Assets\MMDAnimeStudioLab\Evidence")
        return Path(os.environ.get("LOCALAPPDATA", str(ROOT))) / "MMDAnimeStudioLab" / "Evidence"
    return ROOT / "Evidence"


def verify_manifest() -> tuple[bool, str]:
    try:
        manifest = json.loads((ROOT / "PACKAGE_MANIFEST_SHA256.json").read_text(encoding="utf-8"))
        if manifest.get("checkpoint") != "LAB_CP01" or not isinstance(manifest.get("files"), list):
            return False, "HOLD: invalid CP01 manifest"
        for entry in manifest["files"]:
            relative = Path(entry["path"])
            if relative.is_absolute() or ".." in relative.parts:
                return False, "HOLD: unsafe manifest path"
            target = (ROOT / relative).resolve()
            if not target.is_relative_to(ROOT.resolve()) or not target.is_file():
                return False, f"HOLD: missing/unsafe file: {relative}"
            if (target.stat().st_size != entry["bytes"] or
                    hashlib.sha256(target.read_bytes()).hexdigest() != entry["sha256"]):
                return False, f"HOLD: checksum mismatch: {relative}"
        return True, f"PASS_MANIFEST_SHA256_{len(manifest['files'])}"
    except (OSError, ValueError, KeyError, TypeError) as ex:
        return False, f"HOLD: manifest verification failed: {type(ex).__name__}"


def safe_root() -> tuple[bool, str]:
    root = ROOT.resolve()
    if os.name == "nt":
        protected = Path(r"D:\MMD\mmd-asset-registry").resolve()
        if root == protected or protected in root.parents:
            return False, "HOLD: Lab launcher is inside protected Studio repository"
    if not (SRC / "mmd_lab" / "core.py").is_file():
        return False, "HOLD: missing CP01 src/mmd_lab/core.py"
    if not (ROOT / "tests" / "test_lab.py").is_file():
        return False, "HOLD: missing synthetic tests"
    if sys.version_info < (3, 12):
        return False, f"HOLD: Python >=3.12 required; found {sys.version.split()[0]}"
    verified, status = verify_manifest()
    if not verified:
        return False, status
    return True, "PASS_ISOLATED_LAB_ROOT / " + status


def run(mode: str) -> int:
    evidence = evidence_root()
    try:
        evidence.mkdir(parents=True, exist_ok=True)
    except OSError as ex:
        print(f"HOLD: evidence folder unavailable: {ex}", flush=True)
        return 4
    token = datetime.now().strftime('%Y%m%dT%H%M%S_%f') + '_PID' + str(os.getpid()) + '_' + uuid.uuid4().hex[:8]
    prefix = f"MMD_LAB_CP01_{mode.upper()}_{token}"
    txt = evidence / (prefix + '.txt')
    result = evidence / (prefix + '.json')
    code = 4
    state = "HOLD"
    try:
        ok, msg = safe_root()
        with txt.open('x', encoding='utf-8') as out:
            out.write(f"CHECKPOINT=LAB_CP01\nMODE={mode.upper()}\nGATE_ROOT={msg}\n")
            out.write("CANONICAL_REPO_WRITE=NO\nGIT_WRITE=NO\nREAL_ASSET_IO=DENIED_BY_DEFAULT_CP01\n")
            out.write(f"PYTHON={sys.version}\nROOT={ROOT}\n\n")
            out.flush()
            if not ok:
                out.write("RESULT=HOLD\n")
            elif mode == 'preflight':
                out.write("GATE_SOURCES=PASS\nGATE_ISOLATION=PASS\nRESULT=PASS\n")
                code = 0
                state = "PASS"
            else:
                args = ([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'] if mode == 'qa'
                        else [sys.executable, '-m', 'mmd_lab', 'gui'])
                env = os.environ.copy()
                env['PYTHONPATH'] = str(SRC) + os.pathsep + env.get('PYTHONPATH', '')
                completed = subprocess.run(args, cwd=ROOT, env=env, stdout=out,
                                           stderr=subprocess.STDOUT, check=False)
                code = completed.returncode
                state = 'PASS' if code == 0 else 'FAIL'
            out.write(f"\nRESULT={state}\nEXIT_CODE={code}\n")
    except Exception:
        state = 'FAIL'
        code = 5
        with txt.open('a', encoding='utf-8') as out:
            out.write(traceback.format_exc())
            out.write(f"\nRESULT={state}\nEXIT_CODE={code}\n")
    try:
        result.write_text(json.dumps({'checkpoint': 'LAB_CP01', 'mode': mode,
                                      'result': state, 'exit_code': code,
                                      'evidence_txt': str(txt), 'repo_writes': False},
                                     indent=2), encoding='utf-8')
    except OSError as ex:
        print(f"RESULT_JSON_WRITE_FAILED={ex}", flush=True)
        code = code or 6
    print(f"EVIDENCE_TXT={txt}\nRESULT_JSON={result}\nRESULT={state}\nEXIT_CODE={code}", flush=True)
    if os.name == 'nt':
        try:
            subprocess.Popen(['notepad.exe', str(txt)], close_fds=True)
        except OSError as ex:
            print(f"NOTEPAD=HOLD {ex}", flush=True)
    return code


if __name__ == '__main__':
    if len(sys.argv) != 2 or sys.argv[1] not in ('qa', 'gui', 'preflight'):
        raise SystemExit('Usage: python launcher.py qa|gui|preflight')
    raise SystemExit(run(sys.argv[1]))
