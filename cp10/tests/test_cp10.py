import json, pathlib, tempfile, unittest, shutil, zipfile
from unittest.mock import patch
from cp10 import cli
from cp10.repo_export import safe_relative, GateHold, pinned_file_inventory, export, audit

ROOT=pathlib.Path(__file__).resolve().parents[2]
class CP10Tests(unittest.TestCase):
    def test_audit_pins(self): self.assertEqual(audit(ROOT)['total_files'],132)
    def test_audit_safe_flags(self):
        a=audit(ROOT)
        self.assertFalse(a['git_write']); self.assertFalse(a['network']);self.assertFalse(a['real_assets'])
    def test_count_by_cp(self):
        self.assertEqual(audit(ROOT)['counts'],{'CP01':25,'CP02':13,'CP03':13,'CP04':14,'CP05':12,'CP06':12,'CP07':11,'CP08':10,'CP09':12,'CP10':10})
    def test_cli_audit(self): self.assertEqual(cli.main(['audit'],ROOT),0)
    def test_cli_denies_path(self): self.assertEqual(cli.main(['audit','C:\\file'],ROOT),4)
    def test_cli_denies_unapproved(self): self.assertEqual(cli.main(['git-init'],ROOT),4)
    def test_cli_denies_empty(self): self.assertEqual(cli.main([],ROOT),4)
    def test_path_good(self): self.assertEqual(safe_relative('src/mmd_lab/core.py'),'src/mmd_lab/core.py')
    def test_path_traversal(self):
        with self.assertRaises(GateHold):safe_relative('../secrets')
    def test_path_backslash(self):
        with self.assertRaises(GateHold):safe_relative('..\\secrets')
    def test_path_drive(self):
        with self.assertRaises(GateHold):safe_relative('C:/secrets')
    def test_path_absolute(self):
        with self.assertRaises(GateHold):safe_relative('/tmp/secrets')
    def test_path_duplicate_slash(self):
        with self.assertRaises(GateHold):safe_relative('foo//bar')
    def test_path_reserved(self):
        with self.assertRaises(GateHold):safe_relative('x/CON/file')
    def test_inventory_has_no_git(self):
        self.assertTrue(all('/.git/' not in '/'+x['path'] and not x['path'].startswith('.git/') for x in pinned_file_inventory(ROOT)))
    def test_inventory_has_no_media_outside_fixture(self):
        for e in pinned_file_inventory(ROOT):
            if pathlib.PurePosixPath(e['path']).suffix.lower() in ('.pmx','.vmd'):
                self.assertTrue(e['path'].startswith('src/mmd_lab/demo_synthetic/'))
    def test_export_external(self):
        with tempfile.TemporaryDirectory() as d:
            target=pathlib.Path(d)/'snapshot.zip'
            r=export(ROOT,target)
            self.assertEqual(r['source_files'],132)
            with zipfile.ZipFile(target) as z:
                self.assertEqual(len(z.namelist()),133)
                self.assertTrue(any(s.endswith('SOURCE_SNAPSHOT_CP10.json') for s in z.namelist()))
                self.assertFalse(any('/.git/' in x or x.endswith('.pyc') for x in z.namelist()))
    def test_export_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            target=pathlib.Path(d)/'snap.zip';target.write_bytes(b'keep')
            with self.assertRaises(GateHold):export(ROOT,target)
            self.assertEqual(target.read_bytes(),b'keep')
    def test_export_no_write_inside_root(self):
        with self.assertRaises(GateHold):export(ROOT,ROOT/'temp.zip')
    def test_source_not_mutated(self):
        before={e['path']:e['sha256'] for e in pinned_file_inventory(ROOT)}
        with tempfile.TemporaryDirectory() as d:export(ROOT,pathlib.Path(d)/'snapshot.zip')
        self.assertEqual(before,{e['path']:e['sha256'] for e in pinned_file_inventory(ROOT)})
    def test_injected_temp_tamper_is_denied(self):
        with tempfile.TemporaryDirectory() as d:
            shadow=pathlib.Path(d)/'lab';shadow.mkdir()
            # manifest with a bad pin must not be interpreted as trusted.
            (shadow/'PACKAGE_MANIFEST_SHA256.json').write_text('{}')
            with self.assertRaises(GateHold):pinned_file_inventory(shadow)
    def test_read_only_snapshot(self):
        with tempfile.TemporaryDirectory() as d:
            target=pathlib.Path(d)/'source.zip'
            r=export(ROOT,target)
            self.assertFalse(r['git_write']); self.assertFalse(r['network']); self.assertFalse(r['real_assets'])
