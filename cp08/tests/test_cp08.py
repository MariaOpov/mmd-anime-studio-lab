import unittest,json
from io import StringIO
from contextlib import redirect_stdout,redirect_stderr
from cp06.catalog import IDS
from cp06.lifecycle import ExtensionLifecycle
from cp07.transaction import TransactionSession
from cp08.guard import GuardedSession
from cp08.cli import main
M='org.mmdstudio.smart-morph-plus';T='org.mmdstudio.motion-lab';D='org.mmdstudio.model-doctor'
class CP08Tests(unittest.TestCase):
 def setUp(self):self.s=GuardedSession()
 def fail(self,ext=M):return self.s.run([ext],_synthetic_fail_step=ext)
 def test_four_only(self):self.assertEqual(len(IDS),4)
 def test_threshold_default(self):self.assertEqual(self.s.threshold,2)
 def test_threshold_min(self):self.assertEqual(GuardedSession(threshold=1).threshold,1)
 def test_threshold_max(self):self.assertEqual(GuardedSession(threshold=5).threshold,5)
 def test_threshold_zero_rejected(self):
  with self.assertRaises(ValueError):GuardedSession(threshold=0)
 def test_threshold_large_rejected(self):
  with self.assertRaises(ValueError):GuardedSession(threshold=6)
 def test_threshold_bool_rejected(self):
  with self.assertRaises(ValueError):GuardedSession(threshold=True)
 def test_transaction_type_rejected(self):
  with self.assertRaises(TypeError):GuardedSession(transaction={})
 def test_initial_no_quarantine(self):self.assertEqual(self.s.snapshot()['quarantined'],[])
 def test_success(self):self.assertTrue(self.s.run([M])['ok'])
 def test_success_no_writes(self):self.assertFalse(self.s.run([M])['writes'])
 def test_success_no_network(self):self.assertFalse(self.s.run([M])['network'])
 def test_success_no_real_assets(self):self.assertFalse(self.s.run([M])['real_assets'])
 def test_fault_single_strike(self):self.assertEqual(self.fail()['strikes'],1)
 def test_fault_second_quarantines(self):
  self.fail();self.assertTrue(self.fail()['quarantined'])
 def test_fault_restores_state(self):self.assertTrue(self.fail()['state_restored'])
 def test_quarantine_blocks(self):
  self.fail();self.fail();self.assertEqual(self.s.run([M])['error'],'HOLD_QUARANTINED')
 def test_quarantine_does_not_activate(self):
  self.fail();self.fail();before=self.s.transaction.snapshot();self.s.run([M]);self.assertEqual(before,self.s.transaction.snapshot())
 def test_other_extension_healthy(self):
  self.fail();self.fail();self.assertTrue(self.s.run([T])['ok'])
 def test_other_extension_strikes_independent(self):
  self.fail();self.fail(T);self.assertEqual(self.s.snapshot()['strikes'][T],1)
 def test_reset_recovers(self):
  self.fail();self.fail();self.s.reset(M);self.assertTrue(self.s.run([M])['ok'])
 def test_reset_scope(self):
  self.fail();self.fail(T);self.s.reset(M);self.assertEqual(self.s.snapshot()['strikes'][T],1)
 def test_reset_unknown(self):self.assertFalse(self.s.reset('evil')['ok'])
 def test_reset_type(self):self.assertFalse(self.s.reset(True)['ok'])
 def test_snapshot_defensive(self):
  snap=self.s.snapshot();snap['strikes'][M]=100;self.assertEqual(self.s.snapshot()['strikes'][M],0)
 def test_events_defensive(self):
  self.fail();e=self.s.events();e[0]['code']='CHANGED';self.assertNotEqual(self.s.events()[0]['code'],'CHANGED')
 def test_events_bounded(self):
  for _ in range(80):self.s.reset(M)
  self.assertEqual(len(self.s.events()),64)
 def test_events_no_secret(self):
  self.fail();self.assertNotIn('token',json.dumps(self.s.events()).lower())
 def test_invalid_plan_empty(self):self.assertEqual(self.s.run([])['error'],'HOLD_INVALID_PLAN')
 def test_invalid_plan_duplicate(self):self.assertEqual(self.s.run([M,M])['error'],'HOLD_INVALID_PLAN')
 def test_invalid_plan_path(self):self.assertEqual(self.s.run(['D:/file.pmx'])['error'],'HOLD_INVALID_PLAN')
 def test_invalid_plan_type(self):self.assertEqual(self.s.run([1])['error'],'HOLD_INVALID_PLAN')
 def test_invalid_test_fault(self):self.assertEqual(self.s.run([M],_synthetic_fail_step=T)['error'],'HOLD_INVALID_TEST_FAULT')
 def test_no_mutation_on_invalid_fault(self):
  self.s.run([M],_synthetic_fail_step=T);self.assertEqual(self.s.snapshot()['strikes'][M],0)
 def test_success_clears_strikes(self):
  self.fail();self.s.run([M]);self.assertEqual(self.s.snapshot()['strikes'][M],0)
 def test_threshold_one(self):
  a=GuardedSession(threshold=1);self.assertTrue(a.run([M],_synthetic_fail_step=M)['quarantined'])
 def test_quarantined_dependency_blocks(self):
  graph={k:() for k in IDS};graph[T]=(M,)
  a=GuardedSession(TransactionSession(ExtensionLifecycle(graph=graph)))
  a.run([M],_synthetic_fail_step=M);a.run([M],_synthetic_fail_step=M)
  self.assertEqual(a.run([T])['error'],'HOLD_QUARANTINED')
 def test_dependency_fault_attributed(self):
  graph={k:() for k in IDS};graph[T]=(M,)
  a=GuardedSession(TransactionSession(ExtensionLifecycle(graph=graph)))
  self.assertEqual(a.run([T],_synthetic_fail_step=M)['extension_id'],M)
 def test_busy_rejected(self):
  self.s._busy=True;self.assertEqual(self.s.run([M])['error'],'HOLD_GUARD_BUSY')
 def test_busy_reset_rejected(self):
  self.s._busy=True;self.assertFalse(self.s.reset(M)['ok'])
 def test_unsafe_rejected(self):
  self.s._unsafe=True;self.assertEqual(self.s.run([M])['error'],'HOLD_SESSION_UNSAFE_RECREATE')
 def test_unsafe_reset_rejected(self):
  self.s._unsafe=True;self.assertFalse(self.s.reset(M)['ok'])
 def test_preserve_preexisting_active(self):
  self.s.transaction.lifecycle.activate(D);self.fail();snap=self.s.transaction.snapshot()
  self.assertEqual(next(x['lifecycle'] for x in snap['extensions'] if x['id']==D),'ACTIVE')
 def test_disabled_unattributed_no_quarantine(self):
  self.s.transaction.lifecycle.set_enabled(M,False)
  result=self.s.run([M]);self.assertEqual(result['error'],'HOLD_TRANSACTION_FAILURE_UNATTRIBUTED')
  self.assertEqual(self.s.snapshot()['strikes'][M],0)
 def test_unsafe_state_latch(self):
  class Broken(TransactionSession):
   def run(self,*args,**kw):return {'ok':False,'error':'HOLD_STATE_NOT_RESTORED','state_restored':False}
  a=GuardedSession(Broken());self.assertTrue(a.run([M])['error'].startswith('HOLD_SESSION_UNSAFE'))
  self.assertTrue(a.snapshot()['session_unsafe'])
 def test_exception_latches(self):
  class Broken(TransactionSession):
   def run(self,*args,**kw):raise RuntimeError('sensitive private message')
  a=GuardedSession(Broken());result=a.run([M]);self.assertEqual(result['error'],'HOLD_UNSAFE_TRANSACTION_EXCEPTION')
  self.assertNotIn('private',json.dumps(result).lower())
 def test_cli_plugins(self):
  with redirect_stdout(StringIO()):self.assertEqual(main(['plugins']),0)
 def test_cli_demo(self):
  with redirect_stdout(StringIO()):self.assertEqual(main(['demo']),0)
 def test_cli_fault_demo(self):
  with redirect_stdout(StringIO()):self.assertEqual(main(['fault-demo']),0)
 def test_cli_reject_asset(self):
  with redirect_stderr(StringIO()):self.assertEqual(main(['demo','D:/file.pmx']),4)
 def test_cli_reject_install(self):
  with redirect_stderr(StringIO()):self.assertEqual(main(['install']),4)
 def test_no_qt_import(self):
  import sys
  self.assertNotIn('PySide6',sys.modules)
