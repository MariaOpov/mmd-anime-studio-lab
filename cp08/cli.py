"""CP08 CLI: no user-provided asset path, extension id or plugin code."""
from __future__ import annotations
import sys,json
from .guard import GuardedSession
M='org.mmdstudio.smart-morph-plus'
T='org.mmdstudio.motion-lab'

def main(argv=None):
    args=sys.argv[1:] if argv is None else argv
    s=GuardedSession()
    if args==['plugins']:
        output={'ok':True,'checkpoint':'LAB_CP08','snapshot':s.snapshot()}
    elif args==['demo']:
        output={'ok':True,'checkpoint':'LAB_CP08','result':s.run([M,T]),'snapshot':s.snapshot()}
        output['ok']=output['result']['ok']
    elif args==['fault-demo']:
        first=s.run([M],_synthetic_fail_step=M)
        second=s.run([M],_synthetic_fail_step=M)
        blocked=s.run([M])
        healthy=s.run([T])
        reset=s.reset(M)
        recovered=s.run([M])
        ok=(first.get('error')=='HOLD_SYNTHETIC_EXTENSION_FAILURE'
            and second.get('quarantined') is True
            and blocked.get('error')=='HOLD_QUARANTINED'
            and healthy.get('ok') is True and reset.get('ok') is True
            and recovered.get('ok') is True)
        output={'ok':ok,'checkpoint':'LAB_CP08','first':first,'second':second,
                'blocked':blocked,'other_extension':healthy,
                'reset':reset,'recovered':recovered,'snapshot':s.snapshot()}
    else:
        print('HOLD_CP08_SYNTAX plugins | demo | fault-demo',file=sys.stderr)
        return 4
    print(json.dumps(output,indent=2,ensure_ascii=False,sort_keys=True))
    return 0 if output['ok'] else 5

if __name__=='__main__':raise SystemExit(main())
