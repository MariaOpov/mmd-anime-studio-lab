"""Tests only for CP09. All inputs are bundled synthetic; no asset or Git IO."""
from __future__ import annotations
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from cp09.api import StudioLabAPI, MORPH, MOTION
from cp09.cli import dispatch
from cp09.readiness import PINS, ReadinessHold, report, verify_pins, _safe_path

ROOT = Path(__file__).resolve().parents[2]

class CP09Tests(unittest.TestCase):
    def setUp(self):
        self.api = StudioLabAPI()

    def test_status(self):
        s=self.api.status()
        self.assertTrue(s['ok'])
        self.assertEqual(s['checkpoint'],'LAB_CP09')
        self.assertEqual(s['api_version'],'0.1')

    def test_exact_four_extensions(self):
        s=self.api.status()
        self.assertEqual(s['extension_count'],4)
        self.assertEqual(len(s['extensions']),4)

    def test_status_only_bundled(self):
        self.assertEqual({e['id'] for e in self.api.status()['extensions']},
            {'org.mmdstudio.model-doctor', 'org.mmdstudio.motion-peek',MORPH,MOTION})

    def test_status_ready(self):
        self.assertTrue(all(e['lifecycle']=='READY' for e in self.api.status()['extensions']))

    def test_status_safety(self):
        s=self.api.status()
        self.assertFalse(s['network']);self.assertFalse(s['writes']);self.assertFalse(s['real_assets'])

    def test_plan_morph(self):
        self.assertEqual(self.api.plan('morph')['execution_order'],[MORPH])

    def test_plan_motion(self):
        self.assertEqual(self.api.plan('motion')['execution_order'],[MOTION])

    def test_plan_both(self):
        self.assertEqual(self.api.plan('both')['execution_order'],[MOTION,MORPH])

    def test_plan_deterministic(self):
        self.assertEqual(self.api.plan('both'),self.api.plan('both'))

    def test_plan_no_state_change(self):
        before=self.api.status()
        self.api.plan('both')
        self.assertEqual(before,self.api.status())

    def test_plan_bad_string(self):
        self.assertEqual(self.api.plan('../secret.pmx')['error'],'HOLD_CP09_UNKNOWN_OPERATION')

    def test_plan_bad_type(self):
        for bad in (None,True,3,{},['both']):
            self.assertFalse(self.api.plan(bad)['ok'])

    def test_run_morph(self):
        self.assertEqual(self.api.run('morph')['result']['executed'],[MORPH])

    def test_run_motion(self):
        self.assertEqual(self.api.run('motion')['result']['executed'],[MOTION])

    def test_run_both(self):
        r=self.api.run('both')
        self.assertTrue(r['ok']);self.assertEqual(r['result']['executed'],[MOTION,MORPH])

    def test_run_clean_session(self):
        before=self.api.status()
        self.api.run('both')
        self.assertEqual(before,self.api.status())

    def test_run_repeat(self):
        self.assertTrue(self.api.run('both')['ok'])
        self.assertTrue(self.api.run('both')['ok'])

    def test_run_no_tokens(self):
        self.assertNotIn('token',json.dumps(self.api.run('both')))

    def test_run_safe_flags(self):
        s=self.api.run('both')
        self.assertFalse(s['network']);self.assertFalse(s['real_assets']);self.assertFalse(s['writes'])

    def test_run_unknown(self):
        self.assertFalse(self.api.run('foo')['ok'])

    def test_run_only_reads_bundled_synthetic_fixtures(self):
        # Reading the SHA-pinned bundled demo fixtures is allowed. Real assets are not.
        allowed={ROOT/'cp03'/'fixtures'/'morph_demo.json',
                 ROOT/'src'/'mmd_lab'/'demo_synthetic'/'SYNTHETIC_DEMO.vmd'}
        original=Path.read_bytes
        observed=[]
        def checked_read(path):
            self.assertIn(path,allowed)
            observed.append(path)
            return original(path)
        with patch.object(Path,'read_bytes',checked_read):
            self.assertTrue(self.api.run('both')['ok'])
        self.assertEqual(set(observed),allowed)

    def test_api_bad_guard(self):
        with self.assertRaises(TypeError):StudioLabAPI(object())

    def test_cli_status(self):
        self.assertTrue(dispatch(['status'])['ok'])

    def test_cli_plan(self):
        self.assertTrue(dispatch(['plan','both'])['ok'])

    def test_cli_run(self):
        self.assertTrue(dispatch(['run','both'])['ok'])

    def test_cli_unknown(self):
        self.assertFalse(dispatch(['install','../plugin.py'])['ok'])

    def test_cli_no_path(self):
        self.assertFalse(dispatch(['run','C:/asset.pmx'])['ok'])

    def test_cli_wrong_arity(self):
        self.assertFalse(dispatch(['run','both','--file','x'])['ok'])

    def test_cli_non_string_rejected(self):
        self.assertFalse(dispatch(['run',True])['ok'])

    def test_pinned_sources(self):
        counts=verify_pins(ROOT)
        self.assertEqual(sum(counts.values()),109)
        self.assertEqual(len(counts),8)

    def test_readiness(self):
        d=report(ROOT)
        self.assertTrue(d['ok']);self.assertEqual(d['total_pinned_files'],109)
        self.assertFalse(d['git_write'])

    def test_readiness_no_remote_claim(self):
        self.assertEqual(report(ROOT)['remote_setup'],'NOT_PERFORMED')

    def test_manifest_tamper_denied(self):
        from cp09 import readiness
        true_sha=readiness._sha
        with patch.object(readiness,'_sha',side_effect=lambda p:'0'*64 if p.name=='PACKAGE_CP08_SHA256.json' else true_sha(p)):
            self.assertEqual(readiness.report(ROOT)['error'],'HOLD_CP08_MANIFEST_SHA')

    def test_manifest_file_tamper_denied(self):
        from cp09 import readiness
        true_sha=readiness._sha
        with patch.object(readiness,'_sha',side_effect=lambda p:'0'*64 if p.name=='guard.py' else true_sha(p)):
            self.assertEqual(readiness.report(ROOT)['error'],'HOLD_CP08_FILE_SHA')

    def test_relative_path_rejects_traversal(self):
        for bad in ('../secret','a/../secret','C:/a','/root','./x','a\\x','a//b'):
            with self.subTest(bad=bad), self.assertRaises(ReadinessHold):
                _safe_path(ROOT,bad)

    def test_relative_path_portable(self):
        self.assertEqual(_safe_path(ROOT,'cp08/guard.py'),ROOT/'cp08'/'guard.py')

    def test_wrong_root_denied(self):
        self.assertFalse(report(ROOT.parent)['ok'])

    def test_no_qt_dependency(self):
        self.assertNotIn('PySide6',sys.modules)

    def test_contract_exact(self):
        p=ROOT/'cp09'/'contract.json'
        obj=json.loads(p.read_text(encoding='utf-8'))
        self.assertEqual(obj['api_version'],'0.1')
        self.assertFalse(obj['external_plugin_loading'])
        self.assertEqual(obj['studio_bridge'],'NOT_CONNECTED')

    def test_pins_complete(self):
        self.assertEqual([label for label,*_ in PINS],['CP01','CP02','CP03','CP04','CP05','CP06','CP07','CP08'])

    def test_cli_subprocess(self):
        for args in (['status'],['plan','both'],['run','both']):
            p=subprocess.run([sys.executable,'-B','-m','cp09.cli',*args],cwd=ROOT,
                capture_output=True,text=True,check=False)
            self.assertEqual(p.returncode,0,p.stderr)
            self.assertTrue(json.loads(p.stdout)['ok'])

if __name__ == '__main__':unittest.main()
