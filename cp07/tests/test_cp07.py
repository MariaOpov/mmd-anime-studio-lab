import unittest,json
from io import StringIO
from contextlib import redirect_stdout,redirect_stderr
from cp06.catalog import IDS
from cp06.lifecycle import ExtensionLifecycle
from cp07.planner import build_plan,PlanHold
from cp07.transaction import TransactionSession
from cp07.cli import main
M='org.mmdstudio.smart-morph-plus';D='org.mmdstudio.model-doctor';V='org.mmdstudio.motion-peek';T='org.mmdstudio.motion-lab'
class CP07Tests(unittest.TestCase):
 def setUp(self):self.s=TransactionSession()
 def test_four_pinned_only(self):self.assertEqual(len(IDS),4)
 def test_plan_deterministic(self):self.assertEqual(self.s.plan([T,M]),self.s.plan([M,T]))
 def test_plan_no_writes(self):self.assertFalse(self.s.plan([M])['writes'])
 def test_plan_no_network(self):self.assertFalse(self.s.plan([M])['network'])
 def test_plan_no_real_assets(self):self.assertFalse(self.s.plan([M])['real_assets'])
 def test_plan_one_extension(self):self.assertEqual(self.s.plan([M])['execution_order'],(M,))
 def test_plan_two_extensions(self):self.assertEqual(set(self.s.plan([M,T])['execution_order']),{M,T})
 def test_plan_reject_empty(self):self.assertFalse(self.s.run([])['ok'])
 def test_plan_reject_wrong_type(self):self.assertFalse(self.s.run('morph')['ok'])
 def test_plan_reject_duplicate(self):self.assertEqual(self.s.run([M,M])['error'],'HOLD_DUPLICATE_REQUEST')
 def test_plan_reject_unknown(self):self.assertEqual(self.s.run(['other'])['error'],'HOLD_REQUEST_UNTRUSTED_EXTENSION')
 def test_plan_reject_path(self):self.assertFalse(self.s.run(['D:/asset.pmx'])['ok'])
 def test_plan_reject_non_str(self):self.assertFalse(self.s.run([True])['ok'])
 def test_plan_reject_too_many(self):self.assertFalse(self.s.run(list(IDS)+[M])['ok'])
 def test_plan_reject_external_graph(self):
  with self.assertRaisesRegex(PlanHold,'ALLOWLIST'):build_plan([M],{'evil':()})
 def test_plan_reject_cycle(self):
  g={k:() for k in IDS};g[M]=(D,);g[D]=(M,)
  with self.assertRaisesRegex(PlanHold,'CYCLE'):build_plan([M],g)
 def test_plan_reject_missing(self):
  g={k:() for k in IDS};g[M]=('untrusted',)
  with self.assertRaisesRegex(PlanHold,'MISSING'):build_plan([M],g)
 def test_dependency_order(self):
  g={k:() for k in IDS};g[M]=(D,);g[T]=(M,)
  self.assertEqual(build_plan([T],g)['activation_order'],(D,M,T))
 def test_success(self):self.assertTrue(self.s.run([M,T])['ok'])
 def test_execution_two(self):self.assertEqual(len(self.s.run([M,T])['executed']),2)
 def test_execution_only_requested(self):
  g={k:() for k in IDS};g[M]=(D,);s=TransactionSession(ExtensionLifecycle(graph=g));r=s.run([M]);self.assertEqual(r['executed'],[M])
 def test_dependencies_auto_activate(self):
  g={k:() for k in IDS};g[M]=(D,);s=TransactionSession(ExtensionLifecycle(graph=g));r=s.run([M]);self.assertEqual(r['activated_temporary'],[D,M])
 def test_temporary_release(self):self.assertEqual(len(self.s.run([M])['released_temporary']),1)
 def test_state_restored_success(self):self.assertTrue(self.s.run([M])['state_restored'])
 def test_initial_stays_ready(self):self.assertTrue(all(e['lifecycle']=='READY' for e in self.s.snapshot()['extensions']))
 def test_preexisting_preserved(self):
  self.s.lifecycle.activate(D);r=self.s.run([D,M]);self.assertTrue(r['ok']);self.assertEqual(r['preexisting_preserved'],[D]);self.assertEqual(next(x['lifecycle'] for x in self.s.snapshot()['extensions'] if x['id']==D),'ACTIVE')
 def test_preexisting_not_revoked(self):
  self.s.lifecycle.activate(M);r=self.s.run([M]);self.assertEqual(r['activated_temporary'],[]);self.assertEqual(r['released_temporary'],[])
 def test_fault_rolls_back(self):
  r=self.s.run([M,T],_test_fail_step=M);self.assertFalse(r['ok']);self.assertTrue(r['state_restored']);self.assertEqual(r['released_temporary'],r['activated_temporary'][::-1])
 def test_fault_in_dependency(self):
  g={k:() for k in IDS};g[M]=(D,);s=TransactionSession(ExtensionLifecycle(graph=g));r=s.run([M],_test_fail_step=D);self.assertTrue(r['state_restored']);self.assertEqual(r['released_temporary'],[D])
 def test_invalid_fault(self):self.assertEqual(self.s.run([M],_test_fail_step=T)['error'],'HOLD_INVALID_SYNTHETIC_FAULT')
 def test_fault_preserves_preexisting(self):
  self.s.lifecycle.activate(D);r=self.s.run([D,M],_test_fail_step=M);self.assertFalse(r['ok']);self.assertEqual(r['preexisting_preserved'],[D])
 def test_disabled_extension_holds(self):
  self.s.lifecycle.set_enabled(M,False);r=self.s.run([M]);self.assertFalse(r['ok']);self.assertTrue(r['state_restored'])
 def test_invalid_grant_not_in_report(self):
  r=self.s.run([M]);self.assertNotIn('token',json.dumps(r).lower())
 def test_run_no_real_assets(self):self.assertFalse(self.s.run([M])['real_assets'])
 def test_run_no_file_writes(self):self.assertFalse(self.s.run([M])['writes'])
 def test_run_no_network(self):self.assertFalse(self.s.run([M])['network'])
 def test_session_isolated(self):self.assertEqual(self.s.snapshot(),TransactionSession().snapshot())
 def test_cli_plugins(self):
  with redirect_stdout(StringIO()):self.assertEqual(main(['plugins']),0)
 def test_cli_plan(self):
  with redirect_stdout(StringIO()):self.assertEqual(main(['plan']),0)
 def test_cli_demo(self):
  with redirect_stdout(StringIO()):self.assertEqual(main(['demo']),0)
 def test_cli_reject_path(self):
  with redirect_stderr(StringIO()):self.assertEqual(main(['demo','C:/model.pmx']),4)
 def test_cli_reject_install(self):
  with redirect_stderr(StringIO()):self.assertEqual(main(['install','extension']),4)
 def test_active_multi_execution_doesnt_stop_active(self):
  self.s.lifecycle.activate(M);self.s.lifecycle.activate(T);r=self.s.run([T,M]);self.assertTrue(r['ok']);self.assertEqual(len(r['preexisting_preserved']),2)
 def test_dependency_preexisting(self):
  g={k:() for k in IDS};g[M]=(D,);s=TransactionSession(ExtensionLifecycle(graph=g));s.lifecycle.activate(D);r=s.run([M]);self.assertEqual(r['activated_temporary'],[M]);self.assertTrue(r['state_restored'])
 def test_repeated_transaction(self):self.assertTrue(all(self.s.run([M])['ok'] for _ in range(3)))
 def test_snapshot_no_token(self):self.assertNotIn('token',json.dumps(self.s.snapshot()).lower())
