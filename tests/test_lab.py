from __future__ import annotations
import hashlib
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from mmd_lab.core import MAX_BYTES, inspect_pmx, inspect_vmd
from mmd_lab.host import ExtensionHost
import mmd_lab.host as host_module


def i32(n):
    return struct.pack('<i', n)


def ptext(text):
    data = text.encode('utf-8')
    return i32(len(data)) + data


def pmx(*, textures=(), invalid_index=False, weight=0, version=2.0,
        flags=b'\x01\x00\x01\x01\x01\x01\x01\x01', face_count=3):
    b = io.BytesIO()
    b.write(b'PMX ' + struct.pack('<fB', version, len(flags)) + flags)
    for s in ('Miku', 'Miku', 'Description', ''):
        b.write(ptext(s))
    b.write(i32(1))  # exactly one vertex
    b.write(bytes(32))  # xyz, normal, uv
    b.write(bytes([weight]))
    if weight == 0:
        b.write(bytes([0]))  # index of BDEF1 bone
    elif weight == 1:
        b.write(bytes(2 + 4))
    elif weight == 2 or weight == 4:
        b.write(bytes(4 + 16))
    elif weight == 3:
        b.write(bytes(2 + 4 + 36))
    b.write(bytes(4))
    b.write(i32(face_count))
    b.write(bytes([1 if invalid_index else 0]) * face_count)
    b.write(i32(len(textures)))
    for name in textures:
        b.write(ptext(name))
    return b.getvalue()


def vmd(*, bone_frames=(10,), morph_frames=(20,), truncate=False, header=b'Vocaloid Motion Data 0002'):
    b = io.BytesIO()
    b.write(header.ljust(30, b'\0'))
    b.write('Miku'.encode('shift_jis').ljust(20, b'\0'))
    b.write(i32(len(bone_frames)))
    for frame in bone_frames:
        b.write('bone'.encode('shift_jis').ljust(15, b'\0'))
        b.write(struct.pack('<I', frame))
        b.write(bytes(92))
    b.write(i32(len(morph_frames)))
    for frame in morph_frames:
        b.write('blink'.encode('shift_jis').ljust(15, b'\0'))
        b.write(struct.pack('<I', frame))
        b.write(bytes(4))
    data = b.getvalue()
    return data[:-5] if truncate else data


class LabTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def save(self, name, data):
        p = self.root / name
        p.write_bytes(data)
        return p

    def test_pmx_valid_metadata(self):
        report = inspect_pmx(self.save('okay.pmx', pmx()))
        self.assertEqual(report.status, 'PASS')
        self.assertEqual(report.summary['vertices'], 1)
        self.assertEqual(report.summary['triangles_by_indices'], 1)
        self.assertEqual(report.summary['pmx_version'], 2.0)

    def test_pmx_qdef_supported(self):
        rep = inspect_pmx(self.save('qdef.pmx', pmx(weight=4, version=2.1)))
        self.assertEqual(rep.status, 'PASS')

    def test_pmx_invalid_face_reference(self):
        rep = inspect_pmx(self.save('bad.pmx', pmx(invalid_index=True)))
        self.assertEqual(rep.status, 'FAIL')
        self.assertTrue(any(x.code == 'INVALID_VERTEX_REFERENCE' for x in rep.findings))

    def test_pmx_missing_texture(self):
        rep = inspect_pmx(self.save('missing.pmx', pmx(textures=('textures/missing.png',))))
        self.assertEqual(rep.status, 'WARN')
        self.assertTrue(any(x.code == 'MISSING_TEXTURE' for x in rep.findings))

    def test_pmx_existing_texture(self):
        tex = self.root / 'textures'
        tex.mkdir()
        (tex / 'okay.png').write_bytes(b'asset-placeholder')
        rep = inspect_pmx(self.save('found.pmx', pmx(textures=(r'textures\okay.png',))))
        self.assertEqual(rep.status, 'PASS')

    def test_pmx_absolute_texture_not_opened(self):
        rep = inspect_pmx(self.save('absolute.pmx', pmx(textures=(r'C:\Users\me\private.png',))))
        self.assertEqual(rep.status, 'WARN')
        self.assertTrue(any(x.code == 'EXTERNAL_TEXTURE_PATH' for x in rep.findings))

    def test_pmx_path_traversal_blocked(self):
        rep = inspect_pmx(self.save('escape.pmx', pmx(textures=('..\\secret.png',))))
        self.assertEqual(rep.status, 'WARN')
        self.assertTrue(any(x.code == 'ESCAPING_TEXTURE_PATH' for x in rep.findings))

    def test_pmx_duplicate_texture(self):
        rep = inspect_pmx(self.save('duplicate.pmx', pmx(textures=('x.png', 'X.PNG'))))
        self.assertTrue(any(x.code == 'DUPLICATE_TEXTURE_PATH' for x in rep.findings))

    def test_pmx_bad_magic(self):
        rep = inspect_pmx(self.save('badmagic.pmx', b'nothing'))
        self.assertEqual(rep.status, 'FAIL')

    def test_pmx_invalid_globals(self):
        rep = inspect_pmx(self.save('flags.pmx', pmx(flags=b'\x03'*8)))
        self.assertEqual(rep.status, 'FAIL')

    def test_pmx_invalid_weight_type(self):
        rep = inspect_pmx(self.save('weights.pmx', pmx(weight=9)))
        self.assertEqual(rep.status, 'FAIL')

    def test_pmx_non_triangulated_index(self):
        rep = inspect_pmx(self.save('triangles.pmx', pmx(face_count=2)))
        self.assertEqual(rep.status, 'WARN')

    def test_pmx_truncated_payload(self):
        rep = inspect_pmx(self.save('truncated.pmx', pmx()[:-3]))
        self.assertEqual(rep.status, 'FAIL')

    def test_pmx_file_not_modified(self):
        asset = self.save('unchanged.pmx', pmx())
        original_hash = hashlib.sha256(asset.read_bytes()).hexdigest()
        inspect_pmx(asset)
        self.assertEqual(original_hash, hashlib.sha256(asset.read_bytes()).hexdigest())

    def test_pmx_size_cap(self):
        asset = self.root / 'oversized.pmx'
        with asset.open('wb') as stream:
            stream.truncate(MAX_BYTES + 1)  # sparse file, no large fixture allocation
        rep = inspect_pmx(asset)
        self.assertEqual(rep.status, 'FAIL')
        self.assertIn('safety limit', rep.findings[-1].message)

    def test_vmd_valid_counts(self):
        rep = inspect_vmd(self.save('okay.vmd', vmd(bone_frames=(1, 10), morph_frames=(32,))))
        self.assertEqual(rep.status, 'PASS')
        self.assertEqual(rep.summary['bone_keyframes'], 2)
        self.assertEqual(rep.summary['morph_keyframes'], 1)
        self.assertEqual(rep.summary['max_bone_or_morph_frame'], 32)

    def test_vmd_empty_tracks(self):
        rep = inspect_vmd(self.save('empty.vmd', vmd(bone_frames=(), morph_frames=())))
        self.assertEqual(rep.status, 'PASS')
        self.assertEqual(rep.summary['unique_morphs'], 0)

    def test_vmd_truncated(self):
        rep = inspect_vmd(self.save('truncated.vmd', vmd(truncate=True)))
        self.assertEqual(rep.status, 'FAIL')

    def test_vmd_old_format_rejected(self):
        rep = inspect_vmd(self.save('old.vmd', vmd(header=b'Vocaloid Motion Data 0001')))
        self.assertEqual(rep.status, 'FAIL')

    def test_host_lists_two_allowlisted_extensions(self):
        host = ExtensionHost()
        self.assertEqual(set(host.extensions), set(host_module.BUILTINS))
        self.assertEqual(len(host.extensions), 2)

    def test_host_routes_by_suffix(self):
        host = ExtensionHost()
        asset = self.save('file.pmx', pmx())
        self.assertEqual(host.run(asset).tool, 'model_doctor')

    def test_disabled_extension(self):
        host = ExtensionHost()
        host.enabled.clear()
        rep = host.run(self.save('asset.vmd', vmd()))
        self.assertEqual(rep.status, 'FAIL')
        self.assertEqual(rep.findings[0].code, 'EXTENSION_DISABLED')

    def test_unsupported_file_no_exec(self):
        host = ExtensionHost()
        rep = host.run(self.save('external.py', b'print("hi")'))
        self.assertEqual(rep.status, 'FAIL')
        self.assertEqual(rep.findings[0].code, 'UNSUPPORTED_FILE')

    def test_untrusted_manifest_rejected(self):
        manifest = self.root / 'extensions' / 'model_doctor'
        manifest.mkdir(parents=True)
        obj = json.loads((host_module.ROOT / 'extensions/model_doctor/extension.json').read_text())
        obj['entrypoint'] = 'python:bad_module'
        (manifest / 'extension.json').write_text(json.dumps(obj))
        with patch.object(host_module, 'ROOT', self.root):
            with self.assertRaises(ValueError):
                ExtensionHost()


if __name__ == '__main__':
    unittest.main()
