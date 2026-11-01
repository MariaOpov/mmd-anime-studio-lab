"""CP05 QA or demo with one unique TXT/JSON evidence and one Windows Notepad."""
from __future__ import annotations
import json,os,subprocess,sys,uuid,hashlib
from datetime import datetime
from pathlib import Path
from cp04.manifest_checks import verify_all, verify_manifest
ROOT=Path(__file__).resolve().parents[1]
CP04_PIN='feb7ffb51d1a5b8b6b3826e0be869ff9ad20daf992de8669141b51faad648414'
CP05_PIN=None
CP05_FILES=11

def main(mode):
    if mode not in ('qa','demo'): return 4
    if os.name=='nt' and Path(r'D:\Assets').is_dir(): evidence=Path(r'D:\Assets\MMDAnimeStudioLab\Evidence')
    elif os.name=='nt': evidence=Path(os.environ.get('LOCALAPPDATA',str(ROOT)))/'MMDAnimeStudioLab'/'Evidence'
    else: evidence=ROOT/'Evidence'
    evidence.mkdir(parents=True,exist_ok=True)
    t=datetime.now().strftime('%Y%m%dT%H%M%S_%f')+'_PID'+str(os.getpid())+'_'+uuid.uuid4().hex[:8]
    txt=evidence/('MMD_LAB_CP05_'+mode.upper()+'_'+t+'.txt')
    js=evidence/('MMD_LAB_CP05_'+mode.upper()+'_'+t+'.json')
    result,rc='HOLD',4
    with txt.open('x',encoding='utf-8') as f:
        f.write('CHECKPOINT=LAB_CP05_'+mode.upper()+'\nMODE=OFFLINE_SDK_SYNTHETIC_ONLY\n')
        f.write('GIT_WRITE=NONE\nNETWORK=NONE\nREAL_ASSETS=NONE\nGUI=NOT_STARTED\n')
        try:
            counts=verify_all(ROOT,CP04_PIN)
            m=ROOT/'cp05'/'PACKAGE_CP05_SHA256.json'
            actual=hashlib.sha256(m.read_bytes()).hexdigest()
            verify_manifest(ROOT,'cp05/PACKAGE_CP05_SHA256.json',CP05_PIN,CP05_FILES)
            f.write('GATE_CP01_CP02_CP03_CP04='+','.join(map(str,counts))+'\nGATE_CP05=PASS_'+str(CP05_FILES+1)+'\n')
            env=os.environ.copy();env['PYTHONPATH']=str(ROOT)+os.pathsep+str(ROOT/'src')+os.pathsep+env.get('PYTHONPATH','')
            cmds=([[sys.executable,'-B','-m','unittest','discover','-s','cp05/tests','-v']]
                  if mode=='qa' else [[sys.executable,'-B','-m','cp05.cli',*args] for args in
                  [('plugins',),('deny','morph'),('demo','morph'),('demo','motion')]])
            for cmd in cmds:
                f.write('COMMAND='+' '.join(cmd)+'\n');f.flush()
                c=subprocess.run(cmd,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT).returncode
                f.write('COMMAND_EXIT='+str(c)+'\n');f.flush()
                if c!=0: rc,result=5,'FAIL';break
            else: rc,result=0,'PASS'
        except Exception as exc:
            f.write('GATE=HOLD_'+type(exc).__name__+':'+str(exc)+'\n')
        f.write('RESULT='+result+'\nEXIT_CODE='+str(rc)+'\n')
    try:js.write_text(json.dumps({'checkpoint':'LAB_CP05_'+mode.upper(),'result':result,'exit_code':rc,'evidence_txt':str(txt)},indent=2),encoding='utf-8')
    except OSError:
        if rc==0:rc,result=6,'FAIL'
        with txt.open('a',encoding='utf-8') as f:f.write('RESULT_JSON=FAIL\nRESULT='+result+'\nEXIT_CODE='+str(rc)+'\n')
    print('EVIDENCE_TXT='+str(txt)+'\nRESULT_JSON='+str(js)+'\nRESULT='+result+'\nEXIT_CODE='+str(rc),flush=True)
    if os.name=='nt':
        try:subprocess.Popen(['notepad.exe',str(txt)],close_fds=True)
        except OSError as exc:print('NOTEPAD=HOLD_'+str(exc))
    return rc

if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit(4)
    raise SystemExit(main(sys.argv[1]))
