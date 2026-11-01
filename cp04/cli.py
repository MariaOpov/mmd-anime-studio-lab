"""CP04 offline integration CLI; no file path argument is supported."""
from __future__ import annotations
import json
import sys
from .controller import UnifiedLabHost


def main(argv=None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1 or args[0] not in ('plugins', 'pmx', 'vmd', 'morph', 'motion'):
        print('HOLD_CP04_SYNTAX: plugins|pmx|vmd|morph|motion', file=sys.stderr)
        return 4
    host = UnifiedLabHost()
    result = host.snapshot() if args[0] == 'plugins' else host.demo(args[0])
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if (args[0] == 'plugins' or result.get('ok')) else 4

if __name__ == '__main__':
    raise SystemExit(main())
