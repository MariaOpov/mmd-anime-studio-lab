"""Bounded source-only readiness: verify exact CP01–CP08 manifest pins.

Does not execute git, open .git, access MMD assets, or contact GitHub.
Only known manifest-listed paths inside the installed Lab are inspected.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path, PurePosixPath

# SHA256 pins are copied verbatim from the previously accepted installers.
# Count is the number of listed file entries (excluding the checkpoint manifest itself).
PINS = (
    ('CP01', 'PACKAGE_MANIFEST_SHA256.json', 'dafb4eac987d6a3422df79c7d48e787a76dfafd70dcd5841bb9a252b00ce4add', 24),
    ('CP02', 'cp02/PACKAGE_CP02_SHA256.json', '44858f980df6fa150951d879506452ea995ae847717ee56551069c0b3b3ffe6f', 12),
    ('CP03', 'cp03/PACKAGE_CP03_SHA256.json', '3d2ab130d92e29cee4c045ddbc43e838a6671bdbf3ec54221a2a96889ad38379', 12),
    ('CP04', 'cp04/PACKAGE_CP04_SHA256.json', 'feb7ffb51d1a5b8b6b3826e0be869ff9ad20daf992de8669141b51faad648414', 13),
    ('CP05', 'cp05/PACKAGE_CP05_SHA256.json', '3863853662e0b656a4475956e357acab3b44e3477fe805b44404905bc70f9cc4', 11),
    ('CP06', 'cp06/PACKAGE_CP06_SHA256.json', '2ab69503b1cd109ce91cb3c42a0a32556c3a82fc83d119c4bcf6e482e7e761d7', 11),
    ('CP07', 'cp07/PACKAGE_CP07_SHA256.json', '23be07aba60bb313cf760790fcf79b3722cc0c0bb92a63907ed4216c80525bb8', 10),
    ('CP08', 'cp08/PACKAGE_CP08_SHA256.json', '3c6ba8e8b92ee3f91a7007863fcda44dc56507946025e558b81ecd8d97f279fe', 9),
)

class ReadinessHold(ValueError):
    pass


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _link(path):
    return path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction())


def _safe_path(root, raw):
    if (type(raw) is not str or not raw or raw.startswith('/') or '\\' in raw
            or ':' in raw or any(x in ('', '.', '..') for x in raw.split('/'))
            or PurePosixPath(raw).as_posix() != raw):
        raise ReadinessHold('HOLD_CP09_UNSAFE_RELATIVE_PATH')
    target = root.joinpath(*raw.split('/'))
    if not target.resolve().is_relative_to(root.resolve()):
        raise ReadinessHold('HOLD_CP09_OUTSIDE_LAB_ROOT')
    p = target.parent
    while p != root:
        if _link(p):
            raise ReadinessHold('HOLD_CP09_SYMLINK_PARENT')
        p = p.parent
    if _link(target):
        raise ReadinessHold('HOLD_CP09_SYMLINK_FILE')
    return target


def verify_pins(root):
    root = Path(root).absolute()
    if not root.is_dir() or _link(root) or root.name.lower() != 'mmd-anime-studio-lab':
        raise ReadinessHold('HOLD_CP09_ROOT')
    # No generic path scanning; only known manifest and declared file reads.
    counts = {}
    seen_global = set()
    for label, name, manifest_pin, count in PINS:
        m = _safe_path(root, name)
        if not m.is_file() or _sha(m) != manifest_pin:
            raise ReadinessHold('HOLD_'+label+'_MANIFEST_SHA')
        try:
            data = json.loads(m.read_text(encoding='utf-8'))
            entries = data['files']
        except (ValueError, KeyError, OSError, TypeError) as exc:
            raise ReadinessHold('HOLD_'+label+'_MANIFEST_PARSE') from exc
        if type(entries) is not list or len(entries) != count:
            raise ReadinessHold('HOLD_'+label+'_MANIFEST_COUNT')
        for entry in entries:
            if type(entry) is not dict or set(entry) != {'path', 'bytes', 'sha256'}:
                raise ReadinessHold('HOLD_'+label+'_ENTRY_SHAPE')
            raw = entry['path']
            if raw in seen_global or raw == name:
                raise ReadinessHold('HOLD_CP09_DUPLICATE_SOURCE')
            seen_global.add(raw)
            dest = _safe_path(root, raw)
            if (not dest.is_file() or type(entry['bytes']) is not int
                    or dest.stat().st_size != entry['bytes']
                    or type(entry['sha256']) is not str or _sha(dest) != entry['sha256']):
                raise ReadinessHold('HOLD_'+label+'_FILE_SHA')
        counts[label] = count + (label != 'CP01')
    return counts


def report(root):
    root = Path(root).absolute()
    try:
        counts = verify_pins(root)
    except (ReadinessHold, OSError) as exc:
        return {'ok': False, 'checkpoint': 'LAB_CP09', 'error': str(exc),
                'git_write': False, 'network': False, 'real_assets': False}
    return {'ok': True, 'checkpoint': 'LAB_CP09', 'api_version': '0.1',
            'source_state': 'SOURCE_PINS_PASS', 'file_pins': counts,
            'total_pinned_files': sum(counts.values()),
            'git_repo_created_by_cp09': False, 'remote_setup': 'NOT_PERFORMED',
            'git_write': False, 'network': False, 'real_assets': False}
