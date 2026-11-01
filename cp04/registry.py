"""Explicit CP04 manifests/entrypoints. Never execute/import based on manifest input."""
from __future__ import annotations
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parent
MANIFESTS = {
    'org.mmdstudio.smart-morph-plus': ('smart_morph_plus.json', 'Smart Morph+',
        'builtin:cp03.runtime.demo_morph', 'synthetic_morph_preview', '30ccf16d71406d51f03b3a98be1384435930eb239839890d57153163ef71ced9'),
    'org.mmdstudio.motion-lab': ('motion_lab.json', 'Motion Lab',
        'builtin:cp03.runtime.demo_motion', 'synthetic_motion_diagnostics', '6b180aed9c680b459af8ee5aeaa60ab846cf0f1d01e037043805950a82b140e3'),
}

class ExtensionHold(RuntimeError):
    pass


def metadata() -> list[dict]:
    result = []
    for ext_id, (name, title, entrypoint, capability, digest) in MANIFESTS.items():
        path = ROOT / 'manifests' / name
        if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ExtensionHold('HOLD_MANIFEST_PIN_' + ext_id)
        try:
            obj = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError) as exc:
            raise ExtensionHold('HOLD_MANIFEST_PARSE_' + ext_id) from exc
        if (type(obj) is not dict or set(obj) != {'id','name','version','api_version',
                'entrypoint','capabilities','file_access','network','writes'} or
            obj['id'] != ext_id or obj['name'] != title or
            obj['version'] != '0.4.0-dev' or obj['api_version'] != '0.1' or
            obj['entrypoint'] != entrypoint or obj['capabilities'] != [capability] or
            obj['file_access'] != 'bundled_fixture_only' or
            obj['network'] is not False or obj['writes'] is not False):
            raise ExtensionHold('HOLD_MANIFEST_CONTRACT_' + ext_id)
        result.append({'id': ext_id, 'name': title, 'version': obj['version'],
                       'capability': capability, 'entrypoint': entrypoint})
    return result
