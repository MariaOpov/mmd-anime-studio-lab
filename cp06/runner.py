"""CP06 only: repeatable QA/demo, SHA preflight, one evidence TXT+JSON + Notepad."""
from __future__ import annotations
import json,os,subprocess,sys,uuid,hashlib,traceback
from datetime import datetime
from pathlib import Path
from cp04.manifest_checks import verify_manifest
ROOT=Path(__file__).resolve().parents[1]
PINS=(('PACKAGE_MANIFEST_SHA256.json','dafb4eac987d6a3422df79c7d48e787a76dfafd70dcd5841bb9a252b00ce4add',24),
 ('cp02/PACKAGE_CP02_SHA256.json','44858f980df6fa150951d879506452ea995ae847717ee56551069c0b3b3ffe6f',12),
 ('cp03/PACKAGE_CP03_SHA256.json','3d2ab130d92e29cee4c045ddbc43e838a6671bdbf3ec54221a2a96889ad38379',12),
 ('cp04/PACKAGE_CP04_SHA256.json','feb7ffb51d1a5b8b6b3826e0be869ff9ad20daf992de8669141b51faad648414',13),
 ('cp05/PACKAGE_CP05_SHA256.json','3863853662e0b656a4475956e357acab3b44e3477fe805b44404905bc70f9cc4',11))

def main(mode):
    if mode not in ('qa','demo'):return 4
    if os.name=='nt' and Path(r'D:\Assets').is_dir():evidence=Path(r'D:\Assets\MMDAnimeStudioLab\Evidence')
    elif os.name=='nt':evidence=Path(os.environ.get('LOCALAPPDATA',str(ROOT)))/'MMDAnimeStudioLab'/'Evidence'
    else:evidence=ROOT/'Evidence'
    evidence.mkdir(parents=True,exist_ok=True)
    stamp=datetime.now().strftime('%Y%m%dT%H%M%S_%f')+'_PID'+str(os.getpid())+'_'+uuid.uuid4().hex[:8]
    txt=evidence/('MMD_LAB_CP06_'+mode.upper()+'_'+stamp+'.txt')
    js=evidence/('MMD_LAB_CP06_'+mode.upper()+'_'+stamp+'.json')
    rc,result=4,'HOLD'
    with txt.open('x',encoding='utf-8') as f:
        f.write('CHECKPOINT=LAB_CP06_'+mode.upper()+'\nMODE=OFFLINE_SYNTHETIC_ONLY\nGIT_WRITE=NONE\nNETWORK=NONE\nREAL_ASSETS=NONE\nGUI=NOT_STARTED\n')
        try:
            counts=[verify_manifest(ROOT,p,h,n) for p,h,n in PINS]
            m=ROOT/'cp06'/'PACKAGE_CP06_SHA256.json'
            verify_manifest(ROOT,'cp06/PACKAGE_CP06_SHA256.json',None,11)
            f.write('GATE_PRIOR_PINNED=PASS_'+','.join(map(str,counts))+'\nGATE_CP06_FILES=PASS_12\n')
            env=os.environ.copy();env['PYTHONPATH']=str(ROOT)+os.pathsep+str(ROOT/'src')+os.pathsep+env.get('PYTHONPATH','')
            cmds=([[sys.executable,'-B','-m','unittest','discover','-s','cp06/tests','-v']]
                 if mode=='qa' else [[sys.executable,'-B','-m','cp06.cli',*x] for x in [('plugins',),('graph',),('demo','morph'),('demo','motion')]])
            for cmd in cmds:
                f.write('COMMAND='+' '.join(cmd)+'\n');f.flush()
                c=subprocess.run(cmd,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT).returncode
                f.write('COMMAND_EXIT='+str(c)+'\n');f.flush()
                if c:rc,result=5,'FAIL';break
            else:rc,result=0,'PASS'
        except Exception as exc:
            f.write('GATE=HOLD_'+type(exc).__name__+':'+str(exc)+'\n')
        f.write('RESULT='+result+'\nEXIT_CODE='+str(rc)+'\n')
    try:js.write_text(json.dumps({'checkpoint':'LAB_CP06_'+mode.upper(),'result':result,'exit_code':rc,'evidence_txt':str(txt)},indent=2),encoding='utf-8')
    except OSError:
        if rc==0:rc,result=6,'FAIL'
        with txt.open('a',encoding='utf-8') as f:f.write('RESULT_JSON=FAIL\nRESULT='+result+'\nEXIT_CODE='+str(rc)+'\n')
    print('EVIDENCE_TXT='+str(txt)+'\nRESULT_JSON='+str(js)+'\nRESULT='+result+'\nEXIT_CODE='+str(rc))
    if os.name=='nt':
        try:subprocess.Popen(['notepad.exe',str(txt)],close_fds=True)
        except OSError as e:print('NOTEPAD=HOLD_'+str(e))
    return rc
if __name__=='__main__':raise SystemExit(main(sys.argv[1]) if len(sys.argv)==2 else 4)
