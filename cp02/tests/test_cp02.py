from __future__ import annotations
import hashlib
import json
from pathlib import Path
import unittest
from cp02.controller import DEMO_ROOT, LabController

ROOT = Path(__file__).resolve().parents[2]
PIN = 'dafb4eac987d6a3422df79c7d48e787a76dfafd70dcd5841bb9a252b00ce4add'


class CP02Tests(unittest.TestCase):
    def setUp(self):
        self.lab = LabController()

    def test_cp01_pinned_original_manifest(self):
        p = ROOT / 'PACKAGE_MANIFEST_SHA256.json'
        self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(), PIN)
        entries = json.loads(p.read_text(encoding='utf-8'))['files']
        self.assertEqual(len(entries), 24)
        for ent in entries:
            target = ROOT / ent['path']
            self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(), ent['sha256'])

    def test_two_only_trusted_modules(self):
        exts = self.lab.snapshot()['extensions']
        self.assertEqual({x['id'] for x in exts}, {'org.mmdstudio.model-doctor', 'org.mmdstudio.motion-peek'})
        self.assertTrue(all(x['enabled'] for x in exts))

    def test_snapshot_offline_only(self):
        self.assertEqual(self.lab.snapshot()['mode'], 'OFFLINE_SYNTHETIC_READONLY')

    def test_toggle_extension_is_session_only(self):
        name = 'org.mmdstudio.motion-peek'
        self.assertTrue(self.lab.set_enabled(name, False)['ok'])
        self.assertFalse(next(x for x in self.lab.snapshot()['extensions'] if x['id'] == name)['enabled'])
        self.assertTrue(self.lab.set_enabled(name, True)['ok'])

    def test_toggle_unknown_rejected(self):
        self.assertFalse(self.lab.set_enabled('some.new.plugin', True)['ok'])

    def test_toggle_wrong_type_rejected(self):
        self.assertFalse(self.lab.set_enabled('org.mmdstudio.motion-peek', 'true')['ok'])

    def test_external_file_strings_rejected(self):
        for value in ('D:\\MMD\\model.pmx', '../external.pmx', '', 'SYNTHETIC_DEMO.pmx', 'vmd/../pmx', None):
            with self.subTest(value=value):
                self.assertFalse(self.lab.demo(value)['ok'])

    def test_synthetic_pmx_expected_warn(self):
        res = self.lab.demo('pmx')
        self.assertTrue(res['ok'])
        self.assertEqual(res['report']['status'], 'WARN')
        self.assertEqual(res['report']['tool'], 'model_doctor')

    def test_synthetic_vmd_expected_pass(self):
        res = self.lab.demo('vmd')
        self.assertTrue(res['ok'])
        self.assertEqual(res['report']['status'], 'PASS')
        self.assertEqual(res['report']['summary']['bone_keyframes'], 3)

    def test_disabled_demo_gives_error_report(self):
        self.lab.set_enabled('org.mmdstudio.model-doctor', False)
        res = self.lab.demo('pmx')
        self.assertTrue(res['ok'])
        self.assertEqual(res['report']['status'], 'FAIL')
        self.assertEqual(res['report']['findings'][0]['code'], 'EXTENSION_DISABLED')

    def test_fixture_paths_only_under_synthetic(self):
        self.assertTrue((DEMO_ROOT / 'SYNTHETIC_DEMO.pmx').resolve().is_relative_to(DEMO_ROOT.resolve()))
        self.assertTrue((DEMO_ROOT / 'SYNTHETIC_DEMO.vmd').resolve().is_relative_to(DEMO_ROOT.resolve()))

    def test_html_csp_no_network(self):
        html = (ROOT / 'cp02' / 'web' / 'index.html').read_text(encoding='utf-8')
        self.assertIn("default-src 'none'", html)
        self.assertIn("connect-src 'none'", html)
        self.assertIn('qrc:///qtwebchannel/qwebchannel.js', html)
        self.assertNotIn('https://', html)
        self.assertNotIn('http://', html)

    def test_js_uses_textcontent_not_innerhtml(self):
        js = (ROOT / 'cp02' / 'web' / 'app.js').read_text(encoding='utf-8')
        self.assertIn('textContent', js)
        self.assertNotIn('.innerHTML', js)
        self.assertIn('backend.demo', js)

    def test_desktop_import_lazy_optional(self):
        src = (ROOT / 'cp02' / 'desktop.py').read_text(encoding='utf-8')
        self.assertIn('from PySide6.QtWebChannel import QWebChannel', src)
        self.assertIn('HOLD_MISSING_PYSIDE6_QTWEBENGINE', src)
        self.assertIn('LocalContentCanAccessRemoteUrls, False', src)
        self.assertIn('request.block(True)', src)


if __name__ == '__main__':
    unittest.main()
