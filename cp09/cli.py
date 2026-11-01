"""One command surface for four bundled extensions. Reject arbitrary input."""
from __future__ import annotations
import json
import sys
from pathlib import Path
from .api import StudioLabAPI
from .readiness import report


def dispatch(argv):
    if type(argv) not in (tuple, list) or any(type(a) is not str for a in argv):
        return {'ok': False, 'error': 'HOLD_CP09_SYNTAX'}
    args = list(argv)
    if args == ['status']:
        return StudioLabAPI().status()
    if args == ['readiness']:
        return report(Path(__file__).resolve().parent.parent)
    if len(args) == 2 and args[0] in ('plan', 'run') and args[1] in ('morph', 'motion', 'both'):
        api = StudioLabAPI()
        return api.plan(args[1]) if args[0] == 'plan' else api.run(args[1])
    return {'ok': False, 'error': 'HOLD_CP09_SYNTAX',
            'usage': 'status | readiness | plan morph|motion|both | run morph|motion|both'}


def main(argv=None):
    output = dispatch(sys.argv[1:] if argv is None else argv)
    print(json.dumps(output, sort_keys=True, ensure_ascii=False, indent=2))
    return 0 if output.get('ok') is True else 4

if __name__ == '__main__':
    raise SystemExit(main())
