"""Only pre-bundled, SHA-pinned synthetic fixtures are reachable via this API."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from .morph import blend_preview
from .motion import timeline_diagnostics

ROOT = Path(__file__).resolve().parents[1]
MORPH = ROOT / 'cp03' / 'fixtures' / 'morph_demo.json'
VMD = ROOT / 'src' / 'mmd_lab' / 'demo_synthetic' / 'SYNTHETIC_DEMO.vmd'
# These hashes are filled from the actual bytes in the build process.
MORPH_SHA256 = '3c3c48b5daf000559a559a3e3eacf676a1739533161bea8bd80a5a498b082643'
VMD_SHA256 = 'd1bef01ceb9a91a4df08d18ab96c94fafe8662fb32c7318f0262bbf70aa6bca5'


class FixtureHold(RuntimeError):
    pass


def _read_pinned(path: Path, expected: str, limit: int) -> bytes:
    # No caller-supplied paths and no symlinks; fixture directories are package-owned.
    if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
        raise FixtureHold('HOLD_SYMLINK_FIXTURE')
    if not path.is_file() or path.stat().st_size > limit:
        raise FixtureHold('HOLD_FIXTURE_MISSING_OR_OVERSIZE')
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected:
        raise FixtureHold('HOLD_FIXTURE_SHA_MISMATCH')
    return data


def demo_morph(weights: dict | None = None) -> dict:
    data = json.loads(_read_pinned(MORPH, MORPH_SHA256, 100_000).decode('utf-8'))
    return blend_preview(data, {'smile': 0.7, 'cheek_raise': 0.5} if weights is None else weights)


def demo_motion() -> dict:
    return timeline_diagnostics(_read_pinned(VMD, VMD_SHA256, 8 * 1024 * 1024))
