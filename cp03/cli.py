"""Source-only synthetic CP03 previews; NEVER accepts an asset path."""
from __future__ import annotations
import argparse
import json
from .runtime import demo_morph, demo_motion


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog='MMD Lab CP03 synthetic')
    p.add_argument('mode', choices=('morph', 'motion'))
    ns = p.parse_args(argv)
    report = demo_morph() if ns.mode == 'morph' else demo_motion()
    print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
    # WARN indicates correctly processed synthetic diagnostics, not process failure.
    return 0 if report['status'] in ('PASS', 'WARN') else 3


if __name__ == '__main__':
    raise SystemExit(main())
