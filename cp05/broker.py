"""Session-scoped permission broker; no filesystem/network or arbitrary entrypoint API.

This is a cooperative Python API boundary, NOT an OS sandbox. All allowed code
is trusted and SHA-pinned by the installer. No untrusted third-party code runs.
"""
from __future__ import annotations
import secrets
from cp04.controller import UnifiedLabHost
from .contract import verify_contract, negotiate

KIND = {
  'pmx': ('org.mmdstudio.model-doctor', 'read_model'),
  'vmd': ('org.mmdstudio.motion-peek', 'read_motion'),
  'morph': ('org.mmdstudio.smart-morph-plus', 'synthetic_morph_preview'),
  'motion': ('org.mmdstudio.motion-lab', 'synthetic_motion_diagnostics'),
}

class PermissionBroker:
    def __init__(self):
        self.contract = verify_contract()
        self.host = UnifiedLabHost()
        self.grants: dict[str, str] = {}  # opaque token -> exact extension id
        self._events: list[dict] = []
        self._known = {item['id']:item for item in self.host.snapshot()['extensions']}
        if (len(self._known)!=4 or
            {item['id']:item['capability'] for item in self._known.values()}
               != {ext:cap for ext,cap in KIND.values()}):
            raise RuntimeError('HOLD_CP04_CAPABILITY_DRIFT')

    def _audit(self, code: str, ext: str | None = None):
        # Bounded in-memory only, no secrets/tokens/paths; no logging raw requests.
        self._events.append({'event':code, 'extension_id':ext})
        if len(self._events)>64: del self._events[:-64]

    def audit(self):
        return [dict(e) for e in self._events]

    def catalog(self, sdk_version='0.1'):
        if not negotiate(sdk_version)['ok']:
            return {'ok':False,'error':'HOLD_UNSUPPORTED_SDK_VERSION'}
        items = self.host.snapshot()['extensions']
        return {'ok':True,'sdk_version':'0.1','extensions':[
            {'id':e['id'],'name':e['name'],'version':e['version'],
             'capability':e['capability'],'enabled':e['enabled'],
             'permission':'SESSION_ONLY_DEFAULT_DENY'} for e in items],
             'real_assets':False,'writes':False,'network':False}

    def grant(self, extension_id, capability, sdk_version='0.1'):
        if not negotiate(sdk_version)['ok']:
            return {'ok':False,'error':'HOLD_UNSUPPORTED_SDK_VERSION'}
        if type(extension_id) is not str or type(capability) is not str or (
            extension_id,capability) not in KIND.values():
            self._audit('GRANT_DENIED')
            return {'ok':False,'error':'HOLD_CAPABILITY_NOT_ALLOWLISTED'}
        if not self._enabled(extension_id):
            self._audit('GRANT_DISABLED',extension_id)
            return {'ok':False,'error':'HOLD_EXTENSION_DISABLED'}
        token=secrets.token_hex(24)
        self.grants[token]=extension_id
        self._audit('GRANTED',extension_id)
        return {'ok':True,'token':token,'scope':'BUNDLED_SYNTHETIC_ONLY','expires':'END_OF_SESSION'}

    def _enabled(self,extension_id):
        return next((e['enabled'] for e in self.host.snapshot()['extensions']
                    if e['id']==extension_id),False)

    def revoke(self, token):
        if type(token) is not str or token not in self.grants:
            self._audit('REVOKE_DENIED')
            return {'ok':False,'error':'HOLD_UNKNOWN_GRANT'}
        ext=self.grants.pop(token)
        self._audit('REVOKED',ext)
        return {'ok':True}

    def set_enabled(self,extension_id,enabled):
        if type(extension_id) is not str or type(enabled) is not bool:
            return {'ok':False,'error':'HOLD_INVALID_EXTENSION_OR_VALUE'}
        out=self.host.set_enabled(extension_id,enabled)
        if not out.get('ok'): return out
        # Always drop old grants when state toggles to prevent stale capability reuse.
        self.grants={k:v for k,v in self.grants.items() if v!=extension_id}
        self._audit('TOGGLE',extension_id)
        return {'ok':True,'enabled':enabled}

    def execute(self,request):
        # Exact shape: extra keys including path/filename are forbidden before any demo IO.
        if type(request) is not dict or set(request)!= {'sdk_version','kind','extension_id','capability','token','arguments'}:
            self._audit('EXECUTE_SHAPE_DENIED')
            return {'ok':False,'error':'HOLD_REQUEST_SHAPE'}
        if not negotiate(request['sdk_version'])['ok']:
            return {'ok':False,'error':'HOLD_UNSUPPORTED_SDK_VERSION'}
        kind=request['kind']; ext=request['extension_id']; cap=request['capability']; token=request['token']
        if (type(kind) is not str or kind not in KIND or type(ext) is not str or
                type(cap) is not str or KIND.get(kind)!=(ext,cap)):
            self._audit('EXECUTE_CAPABILITY_DENIED')
            return {'ok':False,'error':'HOLD_COMMAND_CAPABILITY_MISMATCH'}
        if type(request['arguments']) is not dict or request['arguments']!={}:
            self._audit('EXECUTE_ARGS_DENIED',ext)
            return {'ok':False,'error':'HOLD_EXTERNAL_INPUT_NOT_ALLOWED'}
        if type(token) is not str or self.grants.get(token)!=ext:
            self._audit('EXECUTE_GRANT_DENIED',ext)
            return {'ok':False,'error':'HOLD_PERMISSION_REQUIRED'}
        if not self._enabled(ext):
            self._audit('EXECUTE_DISABLED',ext)
            return {'ok':False,'error':'HOLD_EXTENSION_DISABLED'}
        response=self.host.demo(kind)
        self._audit('EXECUTED' if response.get('ok') else 'EXECUTION_HOLD',ext)
        return {'ok':bool(response.get('ok')),'extension_id':ext,
                'report':response.get('report')} if response.get('ok') else response
