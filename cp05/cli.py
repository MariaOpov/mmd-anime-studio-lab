"""Offline SDK CLI; accepts only exact demo selectors, never paths or plugin code."""
from __future__ import annotations
import json
import sys
from .broker import PermissionBroker, KIND

def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if args == ['plugins']:
        result=PermissionBroker().catalog()
    elif len(args)==2 and args[0] in ('demo','deny') and args[1] in KIND:
        broker=PermissionBroker(); ext,cap=KIND[args[1]]
        result= {'ok':False,'error':'HOLD_PERMISSION_REQUIRED'}
        if args[0]=='demo':
            grant=broker.grant(ext,cap)
            if not grant['ok']:
                result=grant
            else:
                result=broker.execute({'sdk_version':'0.1','kind':args[1],
                    'extension_id':ext,'capability':cap,'token':grant['token'],'arguments':{}})
    else:
        print('HOLD_CP05_SYNTAX plugins | demo|deny pmx|vmd|morph|motion',file=sys.stderr)
        return 4
    print(json.dumps(result,sort_keys=True,ensure_ascii=False,indent=2))
    # Deny is a negative-control smoke test.
    if len(args)==2 and args[0]=='deny':
        return 0 if not result['ok'] and result['error']=='HOLD_PERMISSION_REQUIRED' else 5
    return 0 if result.get('ok') else 4
if __name__=='__main__': raise SystemExit(main())
