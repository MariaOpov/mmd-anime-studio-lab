from __future__ import annotations
import argparse
import json
from pathlib import Path
from .host import ExtensionHost


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description='MMD Anime Studio Lab CP01 (offline, read-only)')
    sub = p.add_subparsers(dest='command', required=True)
    check = sub.add_parser('inspect', help='Inspect a PMX or VMD file, without modifying it')
    check.add_argument('path')
    check.add_argument('--json', action='store_true', help='Print report as JSON')
    sub.add_parser('plugins', help='List built-in extensions')
    sub.add_parser('gui', help='Start desktop GUI')
    args = p.parse_args(argv)
    host = ExtensionHost()
    if args.command == 'plugins':
        for ext in host.extensions.values():
            print(f'{ext.id} | {ext.version} | {ext.suffix} | {ext.capability}')
        return 0
    if args.command == 'gui':
        from .ui import launch
        launch(host)
        return 0
    permitted = (Path(__file__).resolve().parent / 'demo_synthetic').resolve()
    target = Path(args.path).expanduser().resolve()
    if not target.is_relative_to(permitted):
        print('HOLD_CP01_SYNTHETIC_ONLY: external asset path denied')
        return 4
    rep = host.run(target)
    if args.json:
        print(json.dumps(rep.as_dict(), ensure_ascii=False, indent=2))
    else:
        print(f'{rep.tool}: {rep.filename}: {rep.status}')
        for key, value in rep.summary.items():
            print(f'  {key}: {value}')
        for item in rep.findings:
            print(f'  [{item.severity}] {item.code}: {item.message}')
    return 0 if rep.status in ('PASS', 'WARN') else 2
