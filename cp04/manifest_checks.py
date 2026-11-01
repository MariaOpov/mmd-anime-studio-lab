"""Cross-platform SHA verification of all prior approved add-only payloads."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from pathlib import PurePosixPath
CP01='dafb4eac987d6a3422df79c7d48e787a76dfafd70dcd5841bb9a252b00ce4add'
CP02='44858f980df6fa150951d879506452ea995ae847717ee56551069c0b3b3ffe6f'
CP03='3d2ab130d92e29cee4c045ddbc43e838a6671bdbf3ec54221a2a96889ad38379'


def digest(path: Path): return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_manifest(root: Path, path: str, pin: str|None, count: int) -> int:
    manifest = root.joinpath(*PurePosixPath(path).parts)
    if not manifest.is_file() or manifest.is_symlink() or (pin is not None and digest(manifest)!=pin):
        raise ValueError('HOLD_MANIFEST_PIN_'+path)
    entries = json.loads(manifest.read_text(encoding='utf-8'))['files']
    if type(entries) is not list or len(entries)!=count:
        raise ValueError('HOLD_MANIFEST_COUNT_'+path)
    seen = set()
    for e in entries:
        if type(e) is not dict or set(e)!={'path','bytes','sha256'}:
            raise ValueError('HOLD_MANIFEST_ENTRY_'+path)
        s=e['path']
        if type(s) is not str or not s or '\\' in s or ':' in s or s.startswith('/') or s in seen or any(x in ('','.','..') for x in s.split('/')):
            raise ValueError('HOLD_MANIFEST_PATH_'+str(s))
        seen.add(s)
        p=root.joinpath(*PurePosixPath(s).parts)
        if (not p.resolve().is_relative_to(root.resolve()) or not p.is_file() or
                p.is_symlink() or p.stat().st_size != e['bytes'] or digest(p)!=e['sha256']):
            raise ValueError('HOLD_MANIFEST_FILE_'+s)
    return count


def verify_all(root: Path, cp04_pin: str|None=None) -> tuple[int,int,int,int]:
    return (verify_manifest(root,'PACKAGE_MANIFEST_SHA256.json',CP01,24),
            verify_manifest(root,'cp02/PACKAGE_CP02_SHA256.json',CP02,12),
            verify_manifest(root,'cp03/PACKAGE_CP03_SHA256.json',CP03,12),
            verify_manifest(root,'cp04/PACKAGE_CP04_SHA256.json',cp04_pin,13))
