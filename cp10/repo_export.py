"""CP10 conservative, offline Git-ready source snapshot from exact pinned files only.

No network, Git write, asset discovery, installer, dynamic plugin import, or GUI.
"""
from __future__ import annotations
from pathlib import Path, PurePosixPath
from datetime import datetime
import hashlib, json, os, zipfile, stat

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
CP09_PIN = '3e9718711545de4d9a52e4c0811104ba6724c3e8daad0e582cef9bbfad91c91d'

PINS = PINS + (('CP09','cp09/PACKAGE_CP09_SHA256.json',CP09_PIN,11),)
CP10_MANIFEST='cp10/PACKAGE_CP10_SHA256.json'
class GateHold(ValueError):
    pass

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def safe_relative(path: str) -> str:
    if not isinstance(path,str) or not path or path.startswith('/') or '\\' in path or ':' in path:
        raise GateHold('HOLD_INVALID_PATH')
    parts=path.split('/')
    if any(x in ('','.','..') for x in parts):
        raise GateHold('HOLD_INVALID_PATH_PART')
    if PurePosixPath(path).as_posix()!=path:
        raise GateHold('HOLD_NONCANONICAL_PATH')
    if any(x.rstrip(' .').casefold() in ('con','prn','aux','nul','com1','lpt1') for x in parts):
        raise GateHold('HOLD_RESERVED_WINDOWS_PATH')
    return path

def read_checked(root: Path, rel: str, max_bytes: int=8_000_000) -> bytes:
    safe_relative(rel)
    if root.is_symlink() or (hasattr(root,'is_junction') and root.is_junction()):
        raise GateHold('HOLD_LINK_ROOT')
    p=root.joinpath(*rel.split('/'))
    base=root.resolve(strict=True)
    if not p.resolve().is_relative_to(base):
        raise GateHold('HOLD_OUTSIDE_ROOT')
    parent=p.parent
    while parent!=root:
        if parent.is_symlink() or (hasattr(parent,'is_junction') and parent.is_junction()):
            raise GateHold('HOLD_LINK_PARENT')
        parent=parent.parent
    if p.is_symlink() or (hasattr(p,'is_junction') and p.is_junction()) or not p.is_file():
        raise GateHold('HOLD_MISSING_OR_LINK_FILE_'+rel)
    if p.stat().st_size>max_bytes:
        raise GateHold('HOLD_SIZE_LIMIT_'+rel)
    return p.read_bytes()

def pinned_file_inventory(root: Path) -> list[dict]:
    if not root.is_dir():
        raise GateHold('HOLD_ROOT_MISSING')
    paths={}
    for name, manifest, expected, count in PINS:
        raw=read_checked(root,manifest)
        if digest(raw)!=expected:
            raise GateHold('HOLD_MANIFEST_PIN_'+name)
        try:
            entries=json.loads(raw)['files']
        except (ValueError, KeyError, TypeError) as exc:
            raise GateHold('HOLD_MANIFEST_PARSE_'+name) from exc
        if type(entries) is not list or len(entries)!=count:
            raise GateHold('HOLD_ENTRY_COUNT_'+name)
        for entry in entries:
            if (type(entry) is not dict or set(entry)!={'path','bytes','sha256'} or
                type(entry['bytes']) is not int or entry['bytes']<0 or
                type(entry['sha256']) is not str or len(entry['sha256'])!=64):
                raise GateHold('HOLD_ENTRY_SHAPE_'+name)
            rel=safe_relative(entry['path'])
            key=rel.casefold()
            if key in paths:
                raise GateHold('HOLD_DUPLICATE_PATH_'+rel)
            blob=read_checked(root,rel)
            if len(blob)!=entry['bytes'] or digest(blob)!=entry['sha256']:
                raise GateHold('HOLD_FILE_PIN_'+name+'_'+rel)
            paths[key]={'path':rel,'bytes':len(blob),'sha256':digest(blob),'checkpoint':name}
        key=manifest.casefold()
        if key in paths: raise GateHold('HOLD_DUPLICATE_MANIFEST')
        paths[key]={'path':manifest,'bytes':len(raw),'sha256':expected,'checkpoint':name}
    # The CP10 installer pin protects this manifest; runtime validates its contents too.
    raw=read_checked(root,CP10_MANIFEST)
    try:entries=json.loads(raw)['files']
    except (ValueError,KeyError,TypeError) as exc:raise GateHold('HOLD_CP10_MANIFEST_PARSE') from exc
    if type(entries) is not list or len(entries)!=9:
        raise GateHold('HOLD_CP10_ENTRY_COUNT')
    for entry in entries:
        if type(entry) is not dict or set(entry)!={'path','bytes','sha256'}:
            raise GateHold('HOLD_CP10_ENTRY_SHAPE')
        rel=safe_relative(entry['path'])
        key=rel.casefold()
        if key in paths:raise GateHold('HOLD_DUPLICATE_PATH_'+rel)
        blob=read_checked(root,rel)
        if len(blob)!=entry['bytes'] or digest(blob)!=entry['sha256']:
            raise GateHold('HOLD_CP10_FILE_PIN_'+rel)
        paths[key]={'path':rel,'bytes':len(blob),'sha256':digest(blob),'checkpoint':'CP10'}
    paths[CP10_MANIFEST.casefold()]={'path':CP10_MANIFEST,'bytes':len(raw),'sha256':digest(raw),'checkpoint':'CP10'}
    return sorted(paths.values(),key=lambda e:e['path'])

def audit(root: Path) -> dict:
    files=pinned_file_inventory(root)
    counts={}
    for entry in files:counts[entry['checkpoint']]=counts.get(entry['checkpoint'],0)+1
    return {'checkpoint':'LAB_CP10','mode':'OFFLINE_PINNED_SOURCE_ONLY',
            'ok':True,'total_files':len(files),'counts':counts,
            'git_write':False,'network':False,'real_assets':False,
            'repository_created':False,'git_remote_verified':False,
            'preview_only':True,'gui_required':False}

def export(root: Path, target: Path) -> dict:
    files=pinned_file_inventory(root)
    if not target.is_absolute() or target.suffix.lower()!='.zip':
        raise GateHold('HOLD_BAD_EXPORT_PATH')
    if target.resolve().is_relative_to(root.resolve()):
        raise GateHold('HOLD_EXPORT_INSIDE_REPO')
    if target.exists():raise GateHold('HOLD_EXPORT_EXISTS')
    target.parent.mkdir(parents=True,exist_ok=True)
    try:
        with zipfile.ZipFile(target,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
            for info in files:
                rel=info['path']
                data=read_checked(root,rel)
                if digest(data)!=info['sha256']:raise GateHold('HOLD_EXPORT_SOURCE_CHANGED')
                zi=zipfile.ZipInfo('mmd-anime-studio-lab/'+rel,date_time=(2020,1,1,0,0,0))
                zi.compress_type=zipfile.ZIP_DEFLATED
                zi.external_attr=0o100644<<16
                z.writestr(zi,data)
            manifest={'checkpoint':'LAB_CP10','kind':'PINNED_SOURCE_SNAPSHOT',
                      'git_write':False,'network':False,'files':files}
            zi=zipfile.ZipInfo('mmd-anime-studio-lab/SOURCE_SNAPSHOT_CP10.json',date_time=(2020,1,1,0,0,0))
            zi.compress_type=zipfile.ZIP_DEFLATED
            zi.external_attr=0o100644<<16
            z.writestr(zi,(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode())
        with zipfile.ZipFile(target) as z:
            if z.testzip() is not None or len(z.namelist())!=len(files)+1:
                raise GateHold('HOLD_EXPORT_INTEGRITY')
        return {'ok':True,'source_files':len(files),'zip_entries':len(files)+1,
                'source_zip':str(target),'sha256':digest(target.read_bytes()),
                'git_write':False,'network':False,'real_assets':False}
    except Exception:
        try:target.unlink()
        except OSError:pass
        raise
