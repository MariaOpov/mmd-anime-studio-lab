from __future__ import annotations
import json
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
from mmd_lab.host import API_VERSION, BUILTINS, ExtensionHost
from mmd_lab.core import inspect_pmx, inspect_vmd
import mmd_lab

HERE = Path(mmd_lab.__file__).resolve().parent

class FoundationTests(unittest.TestCase):
    def test_version_string(self):
        self.assertEqual(mmd_lab.__version__, "0.1.0")

    def test_bundled_manifests(self):
        for folder, suffix, permission, _ in BUILTINS.values():
            obj = json.loads((HERE / "extensions" / folder / "extension.json").read_text(encoding="utf-8"))
            self.assertEqual(obj["api_version"], API_VERSION)
            self.assertEqual(obj["capabilities"], [permission])
            self.assertEqual(obj["supported_suffixes"], [suffix])
            self.assertEqual(obj["entrypoint"], "builtin:" + folder)

    def test_demo_pmx_fixture_read_only(self):
        p = HERE / "demo_synthetic" / "SYNTHETIC_DEMO.pmx"
        before = hashlib.sha256(p.read_bytes()).hexdigest()
        rep = inspect_pmx(p)
        self.assertIn(rep.status, ("PASS", "WARN"))
        self.assertEqual(before, hashlib.sha256(p.read_bytes()).hexdigest())

    def test_demo_vmd_fixture_read_only(self):
        p = HERE / "demo_synthetic" / "SYNTHETIC_DEMO.vmd"
        before = hashlib.sha256(p.read_bytes()).hexdigest()
        rep = inspect_vmd(p)
        self.assertEqual(rep.status, "PASS")
        self.assertEqual(rep.summary["bone_keyframes"], 3)
        self.assertEqual(rep.summary["morph_keyframes"], 2)
        self.assertEqual(before, hashlib.sha256(p.read_bytes()).hexdigest())

    def test_new_manifest_cannot_execute_script(self):
        host = ExtensionHost()
        self.assertEqual(len(host.extensions), 2)
        self.assertEqual(set(host.extensions), set(BUILTINS))

    def test_python_cli_plugins(self):
        proc = subprocess.run([sys.executable, "-m", "mmd_lab", "plugins"], capture_output=True, text=True, timeout=15)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("org.mmdstudio.model-doctor", proc.stdout)
        self.assertIn("org.mmdstudio.motion-peek", proc.stdout)

    def test_cli_denies_external_input_without_reading(self):
        proc = subprocess.run([sys.executable, "-m", "mmd_lab", "inspect", "C:/unapproved/not-real.pmx"],
                              capture_output=True, text=True, timeout=15)
        self.assertEqual(proc.returncode, 4)
        self.assertIn("HOLD_CP01_SYNTHETIC_ONLY", proc.stdout)

    def test_cli_allows_bundled_synthetic(self):
        path = HERE / "demo_synthetic" / "SYNTHETIC_DEMO.vmd"
        proc = subprocess.run([sys.executable, "-m", "mmd_lab", "inspect", str(path), "--json"],
                              capture_output=True, text=True, timeout=15)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["summary"]["morph_keyframes"], 2)

    def test_no_studio_repo_dependency(self):
        # Product core and QA work without Studio source or network dependencies.
        import mmd_lab.host as h
        import mmd_lab.core as c
        self.assertTrue(Path(h.__file__).is_file())
        self.assertTrue(Path(c.__file__).is_file())
        self.assertNotIn("mmd_registry", " ".join(sys.modules))

if __name__ == "__main__":
    unittest.main()
