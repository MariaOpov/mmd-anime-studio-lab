"""In-process circuit breaker around CP07 transactions; no OS process isolation.

A synthetic test fault may be injected only via a private keyword argument.
External asset/plugin paths and dynamic imports are not supported. An
unattributed transaction fault is never ascribed to an innocent extension;
failed rollback latches the whole session unsafe until reconstruction.
"""
from __future__ import annotations
from cp06.catalog import IDS
from cp07.transaction import TransactionSession
from cp07.planner import PlanHold

class GuardedSession:
    def __init__(self, transaction=None, *, threshold=2):
        if type(threshold) is not int or not 1 <= threshold <= 5:
            raise ValueError('HOLD_THRESHOLD_BOUND')
        self.transaction=TransactionSession() if transaction is None else transaction
        if not isinstance(self.transaction,TransactionSession):
            raise TypeError('HOLD_TRANSACTION_TYPE')
        self.threshold=threshold
        self._strikes={ext:0 for ext in IDS}
        self._quarantined=set()
        self._unsafe=False
        self._events=[]
        self._busy=False

    def _event(self, code, ext=None):
        self._events.append({'code':code,'extension_id':ext})
        if len(self._events)>64:self._events=self._events[-64:]

    def events(self):
        return [dict(e) for e in self._events]

    def snapshot(self):
        return {'checkpoint':'LAB_CP08','threshold':self.threshold,
                'strikes':{e:self._strikes[e] for e in sorted(IDS)},
                'quarantined':sorted(self._quarantined),'session_unsafe':self._unsafe,
                'lifecycle':self.transaction.snapshot(),
                'network':False,'real_assets':False,'writes':False}

    def reset(self,ext):
        if type(ext) is not str or ext not in IDS:
            return {'ok':False,'error':'HOLD_UNKNOWN_EXTENSION','writes':False}
        if self._busy or self._unsafe:
            return {'ok':False,'error':'HOLD_SESSION_UNSAFE_OR_BUSY','writes':False}
        self._strikes[ext]=0
        self._quarantined.discard(ext)
        self._event('MANUAL_RESET',ext)
        return {'ok':True,'extension_id':ext,'quarantined':False,'writes':False}

    def run(self,requested, *, _synthetic_fail_step=None):
        if self._busy:
            return {'ok':False,'error':'HOLD_GUARD_BUSY','writes':False}
        if self._unsafe:
            return {'ok':False,'error':'HOLD_SESSION_UNSAFE_RECREATE','writes':False}
        try:plan=self.transaction.plan(requested)
        except (PlanHold,ValueError,TypeError):
            return {'ok':False,'error':'HOLD_INVALID_PLAN','writes':False}
        affected=tuple(plan['activation_order'])
        blocked=sorted(set(affected)&self._quarantined)
        if blocked:
            return {'ok':False,'error':'HOLD_QUARANTINED','blocked':blocked,'writes':False}
        if _synthetic_fail_step is not None and (type(_synthetic_fail_step) is not str or _synthetic_fail_step not in affected):
            return {'ok':False,'error':'HOLD_INVALID_TEST_FAULT','writes':False}
        self._busy=True
        try:
            # CP07 owns activation, dependency handling, cleanup and grant release.
            result=self.transaction.run(requested,_test_fail_step=_synthetic_fail_step)
        except Exception:
            self._unsafe=True
            self._event('SESSION_EXCEPTION')
            return {'ok':False,'error':'HOLD_UNSAFE_TRANSACTION_EXCEPTION','writes':False}
        finally:self._busy=False
        if type(result) is not dict or type(result.get('ok')) is not bool:
            self._unsafe=True
            self._event('UNSAFE_RESULT')
            return {'ok':False,'error':'HOLD_UNSAFE_TRANSACTION_RESPONSE','writes':False}
        if result.get('state_restored') is not True or result.get('error') in ('HOLD_CLEANUP_INCOMPLETE','HOLD_STATE_NOT_RESTORED'):
            self._unsafe=True
            self._event('UNSAFE_STATE')
            return {'ok':False,'error':'HOLD_SESSION_UNSAFE_RECREATE','writes':False}
        if result['ok']:
            for ext in affected:self._strikes[ext]=0
            self._event('SUCCESS')
            return {'ok':True,'result':'PASS','executed':list(result['executed']),
                    'state_restored':True,'writes':False,'network':False,'real_assets':False}
        if result.get('error')=='HOLD_SYNTHETIC_INJECTED_FAILURE' and _synthetic_fail_step is not None:
            ext=_synthetic_fail_step
            self._strikes[ext]=min(self.threshold,self._strikes[ext]+1)
            if self._strikes[ext]>=self.threshold:
                self._quarantined.add(ext)
                self._event('QUARANTINE',ext)
            else:self._event('FAULT',ext)
            return {'ok':False,'error':'HOLD_SYNTHETIC_EXTENSION_FAILURE',
                    'extension_id':ext,'strikes':self._strikes[ext],
                    'quarantined':ext in self._quarantined,'state_restored':True,'writes':False}
        self._event('UNATTRIBUTED_HOLD')
        return {'ok':False,'error':'HOLD_TRANSACTION_FAILURE_UNATTRIBUTED',
                'state_restored':True,'writes':False}
