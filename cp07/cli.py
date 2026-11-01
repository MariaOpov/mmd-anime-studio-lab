"""Synthetic-only readout; no arbitrary paths, plugins, or CLI fault injection."""
from __future__ import annotations
import json,sys
from cp06.catalog import IDS
from .transaction import TransactionSession

def main(argv=None):
    args=sys.argv[1:] if argv is None else argv
    session=TransactionSession()
    morph='org.mmdstudio.smart-morph-plus'
    motion='org.mmdstudio.motion-lab'
    if args == ['plan']:
        p=session.plan([morph,motion]);result={'ok':True,**{k:list(v) if type(v) is tuple else v for k,v in p.items()}}
    elif args==['demo']:
        result=session.run([morph,motion])
    elif args==['plugins']:
        result={'ok':True,'checkpoint':'LAB_CP07','extensions':[{'id':e['id'],'lifecycle':e['lifecycle']} for e in session.snapshot()['extensions']],
                'mode':'SYNTHETIC_ONLY','writes':False,'network':False,'real_assets':False}
    else:
        print('HOLD_CP07_SYNTAX plugins | plan | demo',file=sys.stderr)
        return 4
    print(json.dumps(result,indent=2,sort_keys=True,ensure_ascii=False))
    return 0 if result.get('ok') else 5
if __name__=='__main__':raise SystemExit(main())
