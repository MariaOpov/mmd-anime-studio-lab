"""CP02 UI controller over the untouched CP01 ExtensionHost, synthetic demos only."""
from __future__ import annotations
from pathlib import Path
from mmd_lab.host import ExtensionHost

DEMO_ROOT = Path(__file__).resolve().parents[1] / 'src' / 'mmd_lab' / 'demo_synthetic'
DEMO_NAMES = {'pmx': 'SYNTHETIC_DEMO.pmx', 'vmd': 'SYNTHETIC_DEMO.vmd'}


class LabController:
    def __init__(self, host: ExtensionHost | None = None):
        self.host = host if host is not None else ExtensionHost()

    def snapshot(self) -> dict:
        return {
            'checkpoint': 'LAB_CP02',
            'mode': 'OFFLINE_SYNTHETIC_READONLY',
            'extensions': [
                {'id': ext.id, 'name': ext.name, 'version': ext.version,
                 'description': ext.description, 'suffix': ext.suffix,
                 'capability': ext.capability, 'enabled': ext.id in self.host.enabled}
                for ext in self.host.extensions.values()
            ],
            'features': ['MMD Doctor', 'Motion Peek'],
            'limits': 'No external assets, model writes, editor tools, networking, or arbitrary plugins.',
        }

    def set_enabled(self, ext_id: str, enabled: bool) -> dict:
        if type(ext_id) is not str or type(enabled) is not bool or ext_id not in self.host.extensions:
            return {'ok': False, 'error': 'HOLD_UNKNOWN_EXTENSION_OR_INVALID_VALUE'}
        if enabled:
            self.host.enabled.add(ext_id)
        else:
            self.host.enabled.discard(ext_id)
        return {'ok': True, 'snapshot': self.snapshot()}

    def demo(self, kind: str) -> dict:
        if type(kind) is not str or kind not in DEMO_NAMES:
            return {'ok': False, 'error': 'HOLD_EXTERNAL_ASSETS_NOT_AUTHORIZED_CP02'}
        name = DEMO_NAMES[kind]
        path = DEMO_ROOT / name
        if not path.is_file() or path.is_symlink():
            return {'ok': False, 'error': 'HOLD_SYNTHETIC_FIXTURE_UNAVAILABLE'}
        # The GUI runner verifies the pinned CP01 24-file manifest prior to launching.
        rep = self.host.run(path)
        return {'ok': True, 'report': rep.as_dict(), 'source': 'BUNDLED_SYNTHETIC_ONLY'}
