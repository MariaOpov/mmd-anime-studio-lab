"""Minimal CLI for repeatable synthetic-only lifecycle demos."""
from __future__ import annotations
import json, sys
from .catalog import BY_ID
from .graph import plan_dependencies
from .lifecycle import ExtensionLifecycle

def main(argv=None):
    args=sys.argv[1:] if argv is None else argv
    runtime=ExtensionLifecycle()
    if args==['plugins']:
        out={'ok':True,'snapshot':runtime.snapshot()}
    elif args==['demo','morph'] or args==['demo','motion']:
        wanted = 'org.mmdstudio.smart-morph-plus' if args[-1]=='morph' else 'org.mmdstudio.motion-lab'
        started=runtime.activate(wanted)
        inspected=runtime.execute(wanted) if started.get('ok') else started
        stopped=runtime.deactivate(wanted) if started.get('ok') else {'ok':False}
        out={'ok':bool(started.get('ok') and inspected.get('ok') and stopped.get('ok')),
             'extension_id':wanted,'active_result':inspected,
             'stopped':stopped.get('ok'),'snapshot':runtime.snapshot()}
    elif args==['graph']:
        graph={'pmx':(),'morph':('pmx',),'motion':('pmx',), 'scene':('morph','motion')}
        out={'ok':True,'synthetic_graph_order':list(plan_dependencies(graph,['scene']))}
    else:
        print('HOLD_CP06_SYNTAX plugins | demo morph|motion | graph',file=sys.stderr)
        return 4
    print(json.dumps(out,indent=2,ensure_ascii=False,sort_keys=True))
    return 0 if out.get('ok') else 5
if __name__=='__main__':raise SystemExit(main())
