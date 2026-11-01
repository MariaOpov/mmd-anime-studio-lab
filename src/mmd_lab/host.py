"""Explicit allowlisted extension host. No arbitrary manifest-driven imports."""
from __future__ import annotations
from dataclasses import dataclass
import json
from pathlib import Path
from .core import Report, inspect_pmx, inspect_vmd

ROOT = Path(__file__).resolve().parent
API_VERSION = '0.1'

# Only bundled, reviewed entrypoints can execute. A new manifest does not run code.
BUILTINS = {
    'org.mmdstudio.model-doctor': ('model_doctor', '.pmx', 'read_model', inspect_pmx),
    'org.mmdstudio.motion-peek': ('motion_peek', '.vmd', 'read_motion', inspect_vmd),
}


@dataclass(frozen=True)
class Extension:
    id: str
    name: str
    version: str
    description: str
    suffix: str
    capability: str


class ExtensionHost:
    def __init__(self) -> None:
        self.extensions: dict[str, Extension] = {}
        for ext_id, (folder, suffix, capability, _) in BUILTINS.items():
            manifest_path = ROOT / 'extensions' / folder / 'extension.json'
            obj = json.loads(manifest_path.read_text(encoding='utf-8'))
            if (obj.get('id') != ext_id or obj.get('api_version') != API_VERSION
                    or obj.get('capabilities') != [capability]
                    or obj.get('supported_suffixes') != [suffix]
                    or obj.get('entrypoint') != f'builtin:{folder}'):
                raise ValueError(f'Rejected untrusted or incompatible extension manifest: {folder}')
            self.extensions[ext_id] = Extension(ext_id, obj['name'], obj['version'], obj['description'], suffix, capability)
        self.enabled: set[str] = set(self.extensions)

    def run(self, input_file: str | Path) -> Report:
        path = Path(input_file).expanduser()
        suffix = path.suffix.lower()
        for ext_id, (_, supported_suffix, _, callback) in BUILTINS.items():
            if suffix == supported_suffix:
                if ext_id not in self.enabled:
                    rep = Report('extension_host', path.name)
                    rep.add('ERROR', 'EXTENSION_DISABLED', f'{ext_id} is disabled')
                    return rep
                return callback(path)
        report = Report('extension_host', path.name)
        report.add('ERROR', 'UNSUPPORTED_FILE', 'R0 only supports .pmx and .vmd')
        return report
