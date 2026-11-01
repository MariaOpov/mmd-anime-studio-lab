"""Offline CLI for pinned-source inspection/export; no Git operations."""
import json, os, sys, uuid
from pathlib import Path
from datetime import datetime
from .repo_export import audit, export, GateHold

def destination():
    if os.name=='nt' and Path(r'D:\Assets').is_dir():
        root=Path(r'D:\Assets\MMDAnimeStudioLab\Staging')
    elif os.name=='nt':
        root=Path(os.environ.get('LOCALAPPDATA',str(Path.cwd())))/'MMDAnimeStudioLab'/'Staging'
    else:
        root=Path(os.environ.get('MMD_LAB_CP10_STAGING',str(Path.cwd().parent/'lab_cp10_staging')))
    stamp=datetime.now().strftime('%Y%m%dT%H%M%S_%f')+'_'+uuid.uuid4().hex[:8]
    return root/('MMD_LAB_CP10_SOURCE_SNAPSHOT_'+stamp+'.zip')

def main(argv=None,root=None):
    args=list(sys.argv[1:] if argv is None else argv)
    repo=Path.cwd() if root is None else Path(root)
    if len(args)!=1 or args[0] not in ('audit','export'):
        print(json.dumps({'ok':False,'error':'HOLD_COMMAND_DENIED'}))
        return 4
    try:
        obj=audit(repo) if args[0]=='audit' else export(repo,destination())
        print(json.dumps(obj,ensure_ascii=False,indent=2))
        return 0
    except (GateHold,OSError,ValueError) as exc:
        print(json.dumps({'ok':False,'error':str(exc)}))
        return 4

if __name__=='__main__':raise SystemExit(main())
