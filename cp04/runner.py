"""CP04 runner; unique TXT/JSON evidence + exactly one Notepad (Windows)."""
from __future__ import annotations
import hashlib, json, os, subprocess, sys, uuid
from datetime import datetime
from pathlib import Path
from .manifest_checks import verify_all

ROOT = Path(__file__).resolve().parents[1]


def run(mode: str) -> int:
    if os.name == 'nt' and Path(r'D:\Assets').is_dir():
        evidence = Path(r'D:\Assets\MMDAnimeStudioLab\Evidence')
    elif os.name == 'nt':
        evidence = Path(os.environ.get('LOCALAPPDATA', str(ROOT))) / 'MMDAnimeStudioLab' / 'Evidence'
    else:
        evidence = ROOT / 'Evidence'
    evidence.mkdir(parents=True, exist_ok=True)
    key = datetime.now().strftime('%Y%m%dT%H%M%S_%f') + '_PID' + str(os.getpid()) + '_' + uuid.uuid4().hex[:8]
    txt = evidence/('MMD_LAB_CP04_'+mode.upper()+'_'+key+'.txt')
    js = evidence/('MMD_LAB_CP04_'+mode.upper()+'_'+key+'.json')
    result, rc = 'HOLD', 4
    with txt.open('x', encoding='utf-8') as out:
        out.write('CHECKPOINT=LAB_CP04_'+mode.upper()+'\nMODE=OFFLINE_SYNTHETIC_BRIDGE_ONLY\n')
        out.write('GIT_WRITE=NONE\nNETWORK=NONE\nREAL_ASSETS=NONE\nGUI=NOT_STARTED\n')
        try:
            counts = verify_all(ROOT)
            out.write('PINNED_CP01_CP02_CP03_CP04=PASS_' + '_'.join(map(str, counts)) + '\n')
            env = os.environ.copy()
            env['PYTHONPATH'] = str(ROOT) + os.pathsep + str(ROOT/'src') + os.pathsep + env.get('PYTHONPATH','')
            cmds = ([[sys.executable, '-B', '-m', 'unittest', 'discover', '-s','cp04/tests','-v']]
                    if mode=='qa' else [[sys.executable,'-B','-m','cp04.cli',kind]
                    for kind in ('plugins','morph','motion')])
            for cmd in cmds:
                out.write('COMMAND=' + ' '.join(cmd) + '\n'); out.flush()
                cp = subprocess.run(cmd, cwd=ROOT, env=env, stdout=out, stderr=subprocess.STDOUT)
                out.write('COMMAND_EXIT=' + str(cp.returncode) + '\n')
                if cp.returncode:
                    result, rc = 'FAIL', 5
                    break
            else: result, rc = 'PASS', 0
        except Exception as exc:
            out.write('GATE=HOLD_' + type(exc).__name__ + ':' + str(exc) + '\n')
        out.write('RESULT=' + result + '\nEXIT_CODE=' + str(rc) + '\n')
    try:
        js.write_text(json.dumps({'checkpoint': 'LAB_CP04_'+mode.upper(), 'result': result,
                       'exit_code': rc, 'evidence_txt':str(txt)}, indent=2), encoding='utf-8')
    except OSError as exc:
        print('RESULT_JSON=FAIL '+str(exc))
        if rc==0:
            result, rc='FAIL',6
            with txt.open('a',encoding='utf-8') as out:
                out.write('RESULT_JSON=FAIL\nRESULT=FAIL\nEXIT_CODE=6\n')
    print('EVIDENCE_TXT='+str(txt)+'\nRESULT_JSON='+str(js)+'\nRESULT='+result+'\nEXIT_CODE='+str(rc))
    if os.name=='nt':
        try: subprocess.Popen(['notepad.exe', str(txt)], close_fds=True)
        except OSError as exc: print('NOTEPAD=HOLD '+str(exc))
    return rc

if __name__=='__main__':
    if len(sys.argv)!=2 or sys.argv[1] not in ('qa','demo'):
        raise SystemExit('Usage: python -m cp04.runner qa|demo')
    raise SystemExit(run(sys.argv[1]))
