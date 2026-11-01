import json, unittest
from io import StringIO
from contextlib import redirect_stdout,redirect_stderr
from cp06.catalog import IDS, BY_ID, BUILTIN_DEPENDENCIES
from cp06.graph import plan_dependencies,DependencyHold
from cp06.lifecycle import ExtensionLifecycle
from cp06.cli import main
class CP06Tests(unittest.TestCase):
    def setUp(self):self.life=ExtensionLifecycle();self.m='org.mmdstudio.smart-morph-plus';self.d='org.mmdstudio.model-doctor'
    def test_four_bundled_only(self):self.assertEqual(len(IDS),4)
    def test_no_invented_dependencies(self):self.assertTrue(all(not x for x in BUILTIN_DEPENDENCIES.values()))
    def test_initial_ready(self):self.assertTrue(all(x['lifecycle']=='READY' for x in self.life.snapshot()['extensions']))
    def test_snapshot_no_network_real_write(self):
        x=self.life.snapshot();self.assertEqual((x['network'],x['real_assets'],x['writes']),(False,False,False))
    def test_activate_morph(self):self.assertTrue(self.life.activate(self.m)['ok'])
    def test_activate_idempotent(self):self.life.activate(self.m);self.assertTrue(self.life.activate(self.m)['already_active'])
    def test_execute_requires_active(self):self.assertEqual(self.life.execute(self.m)['error'],'HOLD_EXTENSION_NOT_ACTIVE')
    def test_execute_after_active(self):self.life.activate(self.m);self.assertTrue(self.life.execute(self.m)['ok'])
    def test_stop_revokes_token(self):self.life.activate(self.m);self.life.deactivate(self.m);self.assertFalse(self.life.execute(self.m)['ok'])
    def test_stop_idempotent(self):self.assertTrue(self.life.deactivate(self.m)['already_inactive'])
    def test_toggle_disabled(self):self.life.set_enabled(self.m,False);self.assertEqual(self.life.activate(self.m)['error'],'HOLD_EXTENSION_DISABLED')
    def test_toggle_active_denied(self):self.life.activate(self.m);self.assertEqual(self.life.set_enabled(self.m,False)['error'],'HOLD_ACTIVE_EXTENSION_DEACTIVATE_FIRST')
    def test_toggle_after_stop(self):self.life.activate(self.m);self.life.deactivate(self.m);self.assertTrue(self.life.set_enabled(self.m,False)['ok'])
    def test_disable_only_one(self):self.life.set_enabled(self.m,False);self.assertTrue(self.life.activate(self.d)['ok'])
    def test_unknown_activation(self):self.assertFalse(self.life.activate('thirdparty')['ok'])
    def test_wrong_type_activation(self):self.assertFalse(self.life.activate(['a'])['ok'])
    def test_unknown_execution(self):self.assertFalse(self.life.execute('unknown')['ok'])
    def test_unknown_deactivation(self):self.assertFalse(self.life.deactivate('other')['ok'])
    def test_toggle_wrong_boolean(self):self.assertFalse(self.life.set_enabled(self.m,1)['ok'])
    def test_events_defensive_copy(self):
        self.life.activate(self.m);events=self.life.events();events[0]['action']='tamper';self.assertEqual(self.life.events()[0]['action'],'ACTIVATED')
    def test_events_no_grant_tokens(self):
        self.life.activate(self.m);self.assertNotIn(next(iter(self.life._tokens.values())),json.dumps(self.life.events()))
    def test_session_not_reused(self):
        self.life.activate(self.m);self.assertFalse(ExtensionLifecycle().execute(self.m)['ok'])
    def test_graph_deterministic(self):
        g={'scene':['motion','morph'],'motion':['pmx'],'morph':['pmx'],'pmx':[]}
        self.assertEqual(plan_dependencies(g,['scene']),('pmx','morph','motion','scene'))
    def test_graph_reordered_dict_same(self):
        a={'a':['b','c'],'b':[],'c':[]};b={'c':[],'b':[],'a':['c','b']}
        self.assertEqual(plan_dependencies(a,['a']),plan_dependencies(b,['a']))
    def test_graph_cycle(self):
        with self.assertRaisesRegex(DependencyHold,'CYCLE'):plan_dependencies({'a':['b'],'b':['a']},['a'])
    def test_graph_missing(self):
        with self.assertRaisesRegex(DependencyHold,'MISSING'):plan_dependencies({'a':['b']},['a'])
    def test_graph_duplicate(self):
        with self.assertRaisesRegex(DependencyHold,'DUPLICATE'):plan_dependencies({'a':['b','b'],'b':[]},['a'])
    def test_graph_size_limit(self):
        with self.assertRaisesRegex(DependencyHold,'SHAPE'):plan_dependencies({str(i):[] for i in range(33)},['0'])
    def test_graph_edge_limit(self):
        with self.assertRaisesRegex(DependencyHold,'EDGE_LIMIT'):plan_dependencies({str(i):[str(j) for j in range(8)] for i in range(17)},['16'])
    def test_graph_empty_selection(self):
        with self.assertRaisesRegex(DependencyHold,'SELECTION'):plan_dependencies({'a':[]},[])
    def test_graph_bad_selection_type(self):
        with self.assertRaisesRegex(DependencyHold,'SELECTION'):plan_dependencies({'a':[]},'a')
    def test_graph_bool_node(self):
        with self.assertRaisesRegex(DependencyHold,'ID'):plan_dependencies({True:[]},[True])
    def test_graph_reject_other_runtime_id(self):
        with self.assertRaisesRegex(DependencyHold,'SCOPE'):ExtensionLifecycle(graph={'evil':[]})
    def test_dependency_requires_active(self):
        g={k:tuple() for k in IDS};g[self.m]=(self.d,)
        l=ExtensionLifecycle(graph=g)
        self.assertEqual(l.activate(self.m)['error'],'HOLD_DEPENDENCIES_NOT_ACTIVE')
    def test_dependency_then_activate(self):
        g={k:tuple() for k in IDS};g[self.m]=(self.d,)
        l=ExtensionLifecycle(graph=g);l.activate(self.d)
        self.assertTrue(l.activate(self.m)['ok'])
    def test_active_dependent_blocks_stop(self):
        g={k:tuple() for k in IDS};g[self.m]=(self.d,)
        l=ExtensionLifecycle(graph=g);l.activate(self.d);l.activate(self.m)
        self.assertEqual(l.deactivate(self.d)['error'],'HOLD_ACTIVE_DEPENDENTS')
    def test_active_dependent_blocks_disable(self):
        g={k:tuple() for k in IDS};g[self.m]=(self.d,)
        l=ExtensionLifecycle(graph=g);l.activate(self.d);l.activate(self.m)
        self.assertEqual(l.set_enabled(self.d,False)['error'],'HOLD_ACTIVE_EXTENSION_DEACTIVATE_FIRST')
    def test_cli_plugins(self):
        with redirect_stdout(StringIO()):self.assertEqual(main(['plugins']),0)
    def test_cli_morph(self):
        with redirect_stdout(StringIO()):self.assertEqual(main(['demo','morph']),0)
    def test_cli_motion(self):
        with redirect_stdout(StringIO()):self.assertEqual(main(['demo','motion']),0)
    def test_cli_graph(self):
        with redirect_stdout(StringIO()):self.assertEqual(main(['graph']),0)
    def test_cli_path_denied(self):
        with redirect_stderr(StringIO()):self.assertEqual(main(['demo','C:/real.pmx']),4)
    def test_cli_install_denied(self):
        with redirect_stderr(StringIO()):self.assertEqual(main(['install','plugin']),4)
