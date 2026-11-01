"""Bounded in-process transaction for existing CP06 lifecycle + CP05 grants.

No file IO, external extensions, scheduler, concurrency or persistent changes.
Execution success *and* failure release only the grants activated by this run.
Pre-existing active extensions remain untouched. A failed cleanup returns HOLD.
"""
from __future__ import annotations
from cp06.lifecycle import ExtensionLifecycle
from .planner import build_plan, PlanHold

class TransactionSession:
    def __init__(self, lifecycle=None):
        self.lifecycle=ExtensionLifecycle() if lifecycle is None else lifecycle
        if not isinstance(self.lifecycle,ExtensionLifecycle):
            raise TypeError('HOLD_LIFECYCLE_TYPE')
        self._busy=False

    def snapshot(self):
        # A safe CP06 copy; never includes grants or tokens.
        return self.lifecycle.snapshot()

    def plan(self,requested):
        return build_plan(requested,self.lifecycle._graph)

    def run(self, requested, *, _test_fail_step=None):
        """Return sanitized report; failure injection only for synthetic unit tests."""
        if self._busy:
            return {'ok':False,'error':'HOLD_TRANSACTION_BUSY','writes':False}
        try:
            plan=self.plan(requested)
        except PlanHold as exc:
            return {'ok':False,'error':str(exc),'writes':False}
        if _test_fail_step is not None and (type(_test_fail_step) is not str or
                                             _test_fail_step not in plan['activation_order']):
            return {'ok':False,'error':'HOLD_INVALID_SYNTHETIC_FAULT','writes':False}
        preexisting={item['id'] for item in self.snapshot()['extensions']
                     if item['lifecycle']=='ACTIVE'}
        created=[];executed=[];cleanup=[];error=None
        self._busy=True
        try:
            # Deterministic, serialized activation in dependency order.
            for ext in plan['activation_order']:
                if ext not in preexisting:
                    response=self.lifecycle.activate(ext)
                    if not response.get('ok'):
                        error='HOLD_ACTIVATE';break
                    created.append(ext)
                if ext==_test_fail_step:
                    error='HOLD_SYNTHETIC_INJECTED_FAILURE';break
            if error is None:
                for ext in plan['execution_order']:
                    response=self.lifecycle.execute(ext)
                    if not response.get('ok'):
                        error='HOLD_EXECUTE';break
                    executed.append(ext)
        except Exception:
            error='HOLD_TRANSACTION_RUNTIME_EXCEPTION'
        finally:
            # A cleanup failure must never be concealed by a successful execution.
            for ext in reversed(created):
                try:
                    response=self.lifecycle.deactivate(ext)
                    if response.get('ok'):
                        cleanup.append(ext)
                    else:
                        cleanup.append('HOLD_CLEANUP_'+ext)
                except Exception:
                    cleanup.append('HOLD_CLEANUP_'+ext)
            self._busy=False
        cleanup_ok=len(cleanup)==len(created) and all(item in created for item in cleanup)
        if not cleanup_ok: error='HOLD_CLEANUP_INCOMPLETE'
        post_active={item['id'] for item in self.snapshot()['extensions']
                     if item['lifecycle']=='ACTIVE'}
        if post_active != preexisting: error='HOLD_STATE_NOT_RESTORED'
        return {'ok':error is None,'error':error,'checkpoint':'LAB_CP07',
                'requested':list(plan['requested']),
                'activation_order':list(plan['activation_order']),
                'executed':executed,'activated_temporary':created,
                'released_temporary':cleanup,'preexisting_preserved':sorted(preexisting & post_active),
                'state_restored':post_active==preexisting,
                'network':False,'real_assets':False,'writes':False}
