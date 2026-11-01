"""Exact SDK v0.1 handshake and PINNED contract; no dynamic schema execution."""
from __future__ import annotations
import json
import hashlib
from pathlib import Path
from . import SDK_VERSION
CONTRACT_SHA256 = 'b4b938a55cf6d7c9e9172e2003bf05e7e355985d104809549f4f95b1618786ce'
PATH=Path(__file__).resolve().parent/'sdk_contract.json'
KEYS=frozenset(('checkpoint','sdk_version','operations','security'))
OP_NAMES=['catalog','grant','revoke','execute','set_enabled']
SECURITY={'default_grant':'deny','scope':'bundled_synthetic_only','network':False,
          'real_assets':False,'file_writes':False,'dynamic_imports':False,'grant_persistence':False}

class ContractHold(RuntimeError): pass

def verify_contract():
    if PATH.is_symlink() or not PATH.is_file() or hashlib.sha256(PATH.read_bytes()).hexdigest()!=CONTRACT_SHA256:
        raise ContractHold('HOLD_SDK_CONTRACT_PIN')
    try: data=json.loads(PATH.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc: raise ContractHold('HOLD_SDK_CONTRACT_PARSE') from exc
    if (type(data) is not dict or set(data)!=KEYS or
        data['checkpoint']!='LAB_CP05' or data['sdk_version']!=SDK_VERSION or
        data['operations']!=OP_NAMES or data['security']!=SECURITY):
        raise ContractHold('HOLD_SDK_CONTRACT_FIELDS')
    return {'sdk_version':SDK_VERSION,'security':dict(SECURITY)}

def negotiate(version):
    return {'ok':True,'sdk_version':SDK_VERSION} if type(version) is str and version==SDK_VERSION else {'ok':False,'error':'HOLD_UNSUPPORTED_SDK_VERSION'}
