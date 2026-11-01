from __future__ import annotations
import copy
import hashlib
import io
import json
import math
from contextlib import redirect_stdout
from pathlib import Path
import struct
import unittest
from unittest import mock

from cp03 import cli, runtime
from cp03.morph import blend_preview, MorphHold
from cp03.motion import timeline_diagnostics, MotionHold, MAX_INPUT


class CP03Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = json.loads(runtime.MORPH.read_text(encoding='utf-8'))
        cls.data = runtime.VMD.read_bytes()

    def test_pinned_cp01_fixture(self):
        self.assertEqual(hashlib.sha256(self.data).hexdigest(), runtime.VMD_SHA256)

    def test_pinned_cp03_fixture(self):
        self.assertEqual(hashlib.sha256(runtime.MORPH.read_bytes()).hexdigest(), runtime.MORPH_SHA256)

    def test_morph_demo_collision_warn(self):
        r = runtime.demo_morph()
        self.assertEqual(r['status'], 'WARN')
        self.assertEqual(r['collisions'][0]['vertex'], 1)

    def test_morph_preview_no_writes(self):
        self.assertIs(runtime.demo_morph()['writes'], False)

    def test_morph_preview_determinism(self):
        self.assertEqual(runtime.demo_morph(), runtime.demo_morph())

    def test_zero_weights_no_affected_vertices(self):
        r = blend_preview(self.source, {})
        self.assertEqual(r['status'], 'PASS')
        self.assertEqual(r['affected_vertices'], 0)

    def test_single_morph_no_collision(self):
        r = blend_preview(self.source, {'blink': 1.0})
        self.assertEqual(r['status'], 'PASS')
        self.assertEqual(r['affected_vertices'], 2)

    def test_opposing_axis_detection(self):
        r = blend_preview(self.source, {'smile': 1, 'counter_smile': 1})
        self.assertTrue(r['collisions'][0]['opposing_axis'])

    def test_source_not_mutated(self):
        data = copy.deepcopy(self.source)
        blend_preview(data, {'smile': 0.5})
        self.assertEqual(data, self.source)

    def test_invalid_vertex_index_rejected(self):
        data = copy.deepcopy(self.source)
        data['morphs'][0]['offsets'][0]['vertex'] = 200
        with self.assertRaises(MorphHold): blend_preview(data, {})

    def test_duplicate_local_vertex_rejected(self):
        data = copy.deepcopy(self.source)
        data['morphs'][0]['offsets'].append(copy.deepcopy(data['morphs'][0]['offsets'][0]))
        with self.assertRaises(MorphHold): blend_preview(data, {})

    def test_bad_weight_rejected(self):
        for weight in (-.2, 1.2, float('inf'), True):
            with self.subTest(weight=weight):
                with self.assertRaises(MorphHold): blend_preview(self.source, {'smile': weight})

    def test_unknown_weight_rejected(self):
        with self.assertRaises(MorphHold): blend_preview(self.source, {'__unknown__': 1})

    def test_nonfinite_delta_rejected(self):
        data = copy.deepcopy(self.source)
        data['morphs'][0]['offsets'][0]['delta'][1] = float('nan')
        with self.assertRaises(MorphHold): blend_preview(data, {'smile': 1})

    def test_duplicate_names_rejected(self):
        data = copy.deepcopy(self.source)
        data['morphs'][1]['name'] = 'smile'
        with self.assertRaises(MorphHold): blend_preview(data, {})

    def test_bounded_vertex_count(self):
        data = copy.deepcopy(self.source)
        data['vertex_count'] = 100001
        with self.assertRaises(MorphHold): blend_preview(data, {})

    def test_motion_demo_read_only(self):
        r = runtime.demo_motion()
        self.assertTrue(r['writes'] is False)
        self.assertEqual((r['summary']['bone_keyframes'], r['summary']['morph_keyframes']), (3, 2))

    def test_motion_demo_limited_scope(self):
        r = runtime.demo_motion()
        self.assertIn('later tracks not parsed', r['scope'])
        self.assertEqual(r['summary']['remaining_bytes_unparsed'], 16)

    def test_motion_nonunit_quat_warn(self):
        self.assertIn('NONUNIT_QUATERNION', [x['code'] for x in runtime.demo_motion()['warnings']])

    def test_motion_bad_signature(self):
        data = b'bad' + self.data[3:]
        with self.assertRaises(MotionHold): timeline_diagnostics(data)

    def test_motion_truncated(self):
        with self.assertRaises(MotionHold): timeline_diagnostics(self.data[:120])

    def test_motion_massive_count(self):
        data = bytearray(self.data)
        struct.pack_into('<I', data, 50, 60000)
        with self.assertRaises(MotionHold): timeline_diagnostics(bytes(data))

    def test_motion_nonfinite_quat_error(self):
        data = bytearray(self.data)
        struct.pack_into('<f', data, 54+31, float('nan'))
        self.assertEqual(timeline_diagnostics(bytes(data))['status'], 'FAIL')

    def test_motion_duplicate_bone_frame(self):
        data = bytearray(self.data)
        struct.pack_into('<I', data, 54+111+15, 0)
        codes = [x['code'] for x in timeline_diagnostics(bytes(data))['warnings']]
        self.assertIn('DUPLICATE_BONE_FRAME', codes)

    def test_motion_large_pos_jump(self):
        data = bytearray(self.data)
        struct.pack_into('<f', data, 54+111+19, 100.0)
        codes = [x['code'] for x in timeline_diagnostics(bytes(data))['warnings']]
        self.assertIn('LARGE_POSITION_STEP', codes)

    def test_motion_morph_weight_range(self):
        data = bytearray(self.data)
        off = 54 + (3*111) + 4 + 19
        struct.pack_into('<f', data, off, 1.5)
        codes = [x['code'] for x in timeline_diagnostics(bytes(data))['warnings']]
        self.assertIn('MORPH_WEIGHT_OUT_OF_RANGE', codes)

    def test_motion_wrong_input_type(self):
        with self.assertRaises(MotionHold): timeline_diagnostics('not bytes')

    def test_runtime_blocks_tampered_fixture(self):
        with mock.patch.object(runtime, 'MORPH_SHA256', '0'*64):
            with self.assertRaises(runtime.FixtureHold): runtime.demo_morph()

    def test_runtime_does_not_open_external_asset(self):
        # The only public demo entrypoints take no path, or weights for JSON fixture.
        with self.assertRaises(TypeError): runtime.demo_motion(Path('other.vmd'))
        with self.assertRaises(TypeError): runtime.demo_morph(path='other.pmx')

    def test_cli_both_demos(self):
        for key in ('morph', 'motion'):
            with self.subTest(key=key), redirect_stdout(io.StringIO()) as buff:
                self.assertEqual(cli.main([key]), 0)
                self.assertEqual(json.loads(buff.getvalue())['checkpoint'], 'LAB_CP03')

    def test_no_dependency_on_qt(self):
        import sys
        self.assertNotIn('PySide6', sys.modules)


    def test_morph_scaled_preview(self):
        r = blend_preview(self.source, {'smile': 0.5})
        target = next(x for x in r['offset_preview'] if x['vertex'] == 1)
        self.assertEqual(target['delta'], [0.05, 0.1, 0.0])

    def test_morph_weight_order_independent(self):
        a = blend_preview(self.source, {'smile': 0.7, 'cheek_raise': 0.3})
        b = blend_preview(self.source, {'cheek_raise': 0.3, 'smile': 0.7})
        self.assertEqual(a, b)

    def test_motion_duplicate_morph_frame(self):
        data = bytearray(self.data)
        start = 54 + (3 * 111) + 4
        struct.pack_into('<I', data, start + 23 + 15, 8)
        self.assertIn('DUPLICATE_MORPH_FRAME',
                      [x['code'] for x in timeline_diagnostics(bytes(data))['warnings']])


if __name__ == '__main__': unittest.main()
