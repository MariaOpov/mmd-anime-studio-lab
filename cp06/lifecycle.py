"""Session-only orchestration. Approved bundled code only; no external assets."""
from __future__ import annotations
from cp05.broker import PermissionBroker
from .catalog import BUILTIN_DEPENDENCIES, BY_ID, IDS, verify_catalog
from .graph import plan_dependencies, DependencyHold

class ExtensionLifecycle:
    def __init__(self, graph=None):
        self.broker=PermissionBroker()
        self._catalog=verify_catalog(self.broker)
        self._graph=dict(BUILTIN_DEPENDENCIES) if graph is None else graph
        # Prevent user-supplied graphs from expanding execution allowlist.
        if type(self._graph) is not dict or set(self._graph)!=set(IDS):
            raise DependencyHold('HOLD_RUNTIME_GRAPH_SCOPE')
        for item in IDS:plan_dependencies(self._graph,[item])
        self._tokens={}
        self._events=[]

    def _record(self,action,ext):
        self._events.append({'action':action,'extension_id':ext})
        if len(self._events)>64:del self._events[:-64]

    def events(self):return [dict(item) for item in self._events]

    def snapshot(self):
        current={e['id']:e for e in self.broker.catalog()['extensions']}
        return {'checkpoint':'LAB_CP06','sdk_version':'0.1',
                'mode':'OFFLINE_SYNTHETIC_ONLY', 'network':False,
                'real_assets':False,'writes':False,
                'extensions':[{'id':ext,'version':current[ext]['version'],
                               'enabled':current[ext]['enabled'],
                               'lifecycle':'ACTIVE' if ext in self._tokens else
                               ('READY' if current[ext]['enabled'] else 'DISABLED'),
                               'dependencies':list(self._graph[ext])} for ext in IDS]}

    def _enabled(self,ext):
        return any(e['id']==ext and e['enabled'] for e in self.broker.catalog()['extensions'])

    def activate(self, ext):
        if type(ext) is not str or ext not in BY_ID:
            return {'ok':False,'error':'HOLD_UNKNOWN_EXTENSION'}
        if ext in self._tokens:
            return {'ok':True,'state':'ACTIVE','already_active':True}
        if not self._enabled(ext):
            return {'ok':False,'error':'HOLD_EXTENSION_DISABLED'}
        needed=plan_dependencies(self._graph,[ext])
        prereqs=[key for key in needed if key!=ext]
        if any(key not in self._tokens for key in prereqs):
            return {'ok':False,'error':'HOLD_DEPENDENCIES_NOT_ACTIVE',
                    'required':prereqs}
        _,cap=BY_ID[ext]
        result=self.broker.grant(ext,cap)
        if not result.get('ok'):return result
        self._tokens[ext]=result['token']
        self._record('ACTIVATED',ext)
        return {'ok':True,'state':'ACTIVE','already_active':False}

    def deactivate(self,ext):
        if type(ext) is not str or ext not in BY_ID:
            return {'ok':False,'error':'HOLD_UNKNOWN_EXTENSION'}
        if ext not in self._tokens:
            return {'ok':True,'state':'READY' if self._enabled(ext) else 'DISABLED',
                    'already_inactive':True}
        dependents=sorted(item for item in self._tokens if item!=ext and
                          ext in plan_dependencies(self._graph,[item]))
        if dependents:
            return {'ok':False,'error':'HOLD_ACTIVE_DEPENDENTS','dependents':dependents}
        token=self._tokens[ext]
        result=self.broker.revoke(token)
        if not result.get('ok'):return result
        del self._tokens[ext]
        self._record('DEACTIVATED',ext)
        return {'ok':True,'state':'READY' if self._enabled(ext) else 'DISABLED',
                'already_inactive':False}

    def set_enabled(self,ext,enabled):
        if type(ext) is not str or ext not in BY_ID or type(enabled) is not bool:
            return {'ok':False,'error':'HOLD_INVALID_TOGGLE'}
        if not enabled and ext in self._tokens:
            return {'ok':False,'error':'HOLD_ACTIVE_EXTENSION_DEACTIVATE_FIRST'}
        if not enabled and any(other in self._tokens and ext in plan_dependencies(self._graph,[other])
                               for other in IDS if other!=ext):
            return {'ok':False,'error':'HOLD_ACTIVE_DEPENDENTS'}
        out=self.broker.set_enabled(ext,enabled)
        if out.get('ok'):
            self._record('ENABLED' if enabled else 'DISABLED',ext)
        return out

    def execute(self,ext):
        if type(ext) is not str or ext not in BY_ID:
            return {'ok':False,'error':'HOLD_UNKNOWN_EXTENSION'}
        if ext not in self._tokens:
            return {'ok':False,'error':'HOLD_EXTENSION_NOT_ACTIVE'}
        kind,cap=BY_ID[ext]
        response=self.broker.execute({'sdk_version':'0.1','kind':kind,
            'extension_id':ext,'capability':cap,'token':self._tokens[ext],
            'arguments':{}})
        self._record('EXECUTED' if response.get('ok') else 'EXECUTION_HOLD',ext)
        return response
