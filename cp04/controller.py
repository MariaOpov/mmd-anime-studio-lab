"""Composition layer for CP01 + CP03 tools; CP01/CP02/CP03 remain immutable.

Each controller is session-local, no filesystem paths accepted from callers.
Every demo reads only SHA-pinned synthetic fixtures through trusted builtins.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
from cp02.controller import LabController
from cp03.runtime import demo_morph, demo_motion
from .registry import metadata

LEGACY = {
    'pmx': 'org.mmdstudio.model-doctor',
    'vmd': 'org.mmdstudio.motion-peek',
}
EXTRA = {
    'morph': 'org.mmdstudio.smart-morph-plus',
    'motion': 'org.mmdstudio.motion-lab',
}
PINS = {
    'pmx': ('SYNTHETIC_DEMO.pmx', '017a357d4eec6281bf92167973e52826f91902aa18d83d7fc1e64b2c57af2dd2', 149),
    'vmd': ('SYNTHETIC_DEMO.vmd', 'd1bef01ceb9a91a4df08d18ab96c94fafe8662fb32c7318f0262bbf70aa6bca5', 453),
}
ROOT = Path(__file__).resolve().parents[1]


class UnifiedLabHost:
    """Four allowlisted tools; session-only enable/disable, no plugin dynamic exec."""
    def __init__(self):
        self.legacy = LabController()
        self.extra = {entry['id']: entry for entry in metadata()}
        if set(self.extra) != set(EXTRA.values()):
            raise RuntimeError('HOLD_EXTENSION_REGISTRY_UNEXPECTED')
        self.extra_enabled = set(self.extra)

    def snapshot(self) -> dict:
        old = self.legacy.snapshot()['extensions']
        new = [{**dict(self.extra[ext_id]), 'enabled': ext_id in self.extra_enabled,
                'source': 'CP03_SYNTHETIC_ONLY'} for ext_id in sorted(self.extra)]
        return {'checkpoint': 'LAB_CP04', 'status': 'PASS',
                'mode': 'OFFLINE_SYNTHETIC_READ_ONLY',
                'extensions': [{**e, 'source': 'CP01_BUNDLED'} for e in old] + new,
                'extension_count': 4, 'writes': False, 'network': False,
                'real_assets': False}

    def set_enabled(self, ext_id: str, enabled: bool) -> dict:
        if type(ext_id) is not str or type(enabled) is not bool:
            return {'ok': False, 'error': 'HOLD_INVALID_EXTENSION_OR_VALUE'}
        if ext_id in self.legacy.host.extensions:
            result = self.legacy.set_enabled(ext_id, enabled)
            return {'ok': True, 'snapshot': self.snapshot()} if result.get('ok') else result
        if ext_id in self.extra:
            if enabled:
                self.extra_enabled.add(ext_id)
            else:
                self.extra_enabled.discard(ext_id)
            return {'ok': True, 'snapshot': self.snapshot()}
        return {'ok': False, 'error': 'HOLD_UNKNOWN_EXTENSION'}

    @staticmethod
    def _check_legacy_fixture(kind: str) -> None:
        name, digest, size = PINS[kind]
        path = ROOT / 'src' / 'mmd_lab' / 'demo_synthetic' / name
        if (path.is_symlink() or any(p.is_symlink() for p in path.parents)
                or not path.is_file() or path.stat().st_size != size
                or hashlib.sha256(path.read_bytes()).hexdigest() != digest):
            raise ValueError('HOLD_LEGACY_FIXTURE_PIN')

    def demo(self, kind: str) -> dict:
        if type(kind) is not str or kind not in (LEGACY | EXTRA):
            return {'ok': False, 'error': 'HOLD_EXTERNAL_ASSET_IO_NOT_AUTHORIZED_CP04'}
        ext_id = (LEGACY | EXTRA)[kind]
        enabled = (ext_id in self.legacy.host.enabled if kind in LEGACY
                   else ext_id in self.extra_enabled)
        if not enabled:
            return {'ok': False, 'error': 'HOLD_EXTENSION_DISABLED', 'extension_id': ext_id}
        if kind in LEGACY:
            try:
                self._check_legacy_fixture(kind)
            except (OSError, ValueError):
                return {'ok': False, 'error': 'HOLD_LEGACY_FIXTURE_PIN'}
            data = self.legacy.demo(kind)
            return {'ok': True, 'extension_id': ext_id, 'report': data['report'],
                    'source': 'BUNDLED_SYNTHETIC_ONLY'} if data.get('ok') else data
        from cp03.runtime import FixtureHold
        try:
            report = demo_morph() if kind == 'morph' else demo_motion()
        except (OSError, ValueError, FixtureHold):
            return {'ok': False, 'error': 'HOLD_CP03_SYNTHETIC_FIXTURE_PIN'}
        return {'ok': True, 'extension_id': ext_id, 'report': report,
                'source': 'BUNDLED_SYNTHETIC_ONLY'}
