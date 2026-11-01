from __future__ import annotations
import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from cp04.controller import UnifiedLabHost, LEGACY, EXTRA
from cp04.registry import metadata, ExtensionHold
from cp04.cli import main
from cp04 import controller, registry


class CP04Tests(unittest.TestCase):
    def setUp(self):
        self.host = UnifiedLabHost()

    def test_exact_four_extensions(self):
        self.assertEqual({e['id'] for e in self.host.snapshot()['extensions']}, set(LEGACY.values()) | set(EXTRA.values()))

    def test_snapshot_explicit_safety(self):
        obj = self.host.snapshot()
        self.assertEqual(obj['extension_count'], 4)
        self.assertFalse(obj['writes'])
        self.assertFalse(obj['network'])
        self.assertFalse(obj['real_assets'])

    def test_order_deterministic(self):
        self.assertEqual(self.host.snapshot(), UnifiedLabHost().snapshot())

    def test_all_four_synthetic_demos(self):
        for kind in ('pmx', 'vmd', 'morph', 'motion'):
            with self.subTest(kind=kind):
                data = self.host.demo(kind)
                self.assertTrue(data['ok'])
                self.assertFalse(data['report'].get('writes', False))
                self.assertEqual(data['source'], 'BUNDLED_SYNTHETIC_ONLY')

    def test_morph_warn_expected(self):
        rep = self.host.demo('morph')['report']
        self.assertEqual(rep['status'], 'WARN')
        self.assertEqual(rep['collisions'][0]['vertex'], 1)

    def test_motion_warn_expected(self):
        rep = self.host.demo('motion')['report']
        self.assertEqual(rep['status'], 'WARN')
        self.assertEqual(rep['summary']['bone_keyframes'], 3)

    def test_legacy_vmd_status_pass(self):
        self.assertEqual(self.host.demo('vmd')['report']['status'], 'PASS')

    def test_unknown_demo_rejected(self):
        self.assertFalse(self.host.demo('c:/users/test/demo.pmx')['ok'])

    def test_arbitrary_path_denied(self):
        self.assertFalse(self.host.demo('../model.pmx')['ok'])

    def test_wrong_demo_types_rejected(self):
        for bad in (None, 0, True, {}, [], b'morph'):
            self.assertFalse(self.host.demo(bad)['ok'])

    def test_legacy_disable(self):
        ext_id = LEGACY['pmx']
        self.assertTrue(self.host.set_enabled(ext_id, False)['ok'])
        self.assertEqual(self.host.demo('pmx')['error'], 'HOLD_EXTENSION_DISABLED')

    def test_new_disable(self):
        ext_id = EXTRA['morph']
        self.assertTrue(self.host.set_enabled(ext_id, False)['ok'])
        self.assertEqual(self.host.demo('morph')['error'], 'HOLD_EXTENSION_DISABLED')

    def test_reenable_morph(self):
        ext_id = EXTRA['morph']
        self.host.set_enabled(ext_id, False)
        self.assertTrue(self.host.set_enabled(ext_id, True)['ok'])
        self.assertTrue(self.host.demo('morph')['ok'])

    def test_toggle_only_one_extension(self):
        self.host.set_enabled(EXTRA['motion'], False)
        self.assertTrue(self.host.demo('morph')['ok'])
        self.assertTrue(self.host.demo('vmd')['ok'])

    def test_toggle_not_persisted_across_sessions(self):
        self.host.set_enabled(EXTRA['motion'], False)
        self.assertTrue(UnifiedLabHost().demo('motion')['ok'])

    def test_toggle_bad_id_rejected(self):
        self.assertFalse(self.host.set_enabled('arbitrary.module', True)['ok'])

    def test_toggle_bad_value_rejected(self):
        self.assertFalse(self.host.set_enabled(EXTRA['motion'], 1)['ok'])

    def test_toggle_bad_id_type_rejected(self):
        self.assertFalse(self.host.set_enabled(None, True)['ok'])

    def test_fixed_registry_entries(self):
        self.assertEqual(len(metadata()), 2)
        self.assertTrue(all(e['entrypoint'].startswith('builtin:cp03.runtime.') for e in metadata()))

    def test_reject_tampered_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            testdir = Path(td)
            (testdir / 'manifests').mkdir()
            for ent in metadata():
                name = registry.MANIFESTS[ent['id']][0]
                p = testdir/'manifests'/name
                p.write_bytes((registry.ROOT/'manifests'/name).read_bytes())
            (testdir/'manifests'/'motion_lab.json').write_text('{}', encoding='utf-8')
            with patch.object(registry, 'ROOT', testdir):
                with self.assertRaises(ExtensionHold): metadata()

    def test_no_dynamic_entrypoint_import(self):
        source = (registry.ROOT / 'registry.py').read_text(encoding='utf-8')
        self.assertNotIn('importlib', source)
        self.assertNotIn('exec(', source)
        self.assertNotIn('eval(', source)

    def test_pinned_legacy_fixture(self):
        for kind, (name, digest, size) in controller.PINS.items():
            file = controller.ROOT/'src'/'mmd_lab'/'demo_synthetic'/name
            self.assertEqual(file.stat().st_size, size)
            self.assertEqual(hashlib.sha256(file.read_bytes()).hexdigest(), digest)

    def test_reject_legacy_tampered_fixture(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            f = base/'src'/'mmd_lab'/'demo_synthetic'/'SYNTHETIC_DEMO.pmx'
            f.parent.mkdir(parents=True)
            f.write_bytes(b'BAD')
            with patch.object(controller, 'ROOT', base):
                self.assertEqual(self.host.demo('pmx')['error'], 'HOLD_LEGACY_FIXTURE_PIN')

    def test_cli_plugins(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(main(['plugins']), 0)
        self.assertEqual(json.loads(out.getvalue())['extension_count'], 4)

    def test_cli_motion(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(main(['motion']), 0)
        self.assertEqual(json.loads(out.getvalue())['report']['status'], 'WARN')

    def test_cli_reject_filepath(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(['morph', 'asset.pmx']), 4)

    def test_cli_reject_unapproved_command(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(['load']), 4)

    def test_no_qt_dependency(self):
        source = (registry.ROOT/'controller.py').read_text(encoding='utf-8')
        self.assertNotIn('PySide6', source)

    def test_no_source_changes_to_legacy(self):
        self.assertEqual(self.host.legacy.snapshot()['checkpoint'], 'LAB_CP02')

if __name__ == '__main__':
    unittest.main()
