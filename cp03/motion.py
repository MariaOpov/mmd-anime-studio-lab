"""Bounded VMD 0002 bone/morph timeline diagnostics from in-memory bytes.

Observational only. This is NOT a general VMD validator: subsequent tracks are
not parsed, no pose/motion interpolation, IK, camera or export support.
"""
from __future__ import annotations

import math
import struct
from collections import defaultdict


class MotionHold(ValueError):
    """Malformed or unsupported VMD binary."""


MAX_INPUT = 8 * 1024 * 1024
MAX_KEYS = 50000


def _name(raw: bytes) -> str:
    return raw.split(b'\x00', 1)[0].decode('shift_jis', errors='replace')


def timeline_diagnostics(data: bytes) -> dict:
    if type(data) is not bytes or len(data) < 58 or len(data) > MAX_INPUT:
        raise MotionHold('INVALID_VMD_SIZE_OR_TYPE')
    pos = 0

    def take(size: int) -> bytes:
        nonlocal pos
        if size < 0 or pos + size > len(data):
            raise MotionHold('TRUNCATED_VMD')
        b = data[pos:pos + size]
        pos += size
        return b

    if take(30).split(b'\x00', 1)[0] != b'Vocaloid Motion Data 0002':
        raise MotionHold('UNSUPPORTED_VMD_VERSION')
    model = _name(take(20))

    def count(length: int) -> int:
        n = struct.unpack('<I', take(4))[0]
        if n > MAX_KEYS or n * length > len(data) - pos:
            raise MotionHold('IMPOSSIBLE_OR_TRUNCATED_KEY_COUNT')
        return n

    bone_count = count(111)
    bones = defaultdict(list)
    errors = []
    warns = []
    for _ in range(bone_count):
        rec = take(111)
        name = _name(rec[:15])
        frame = struct.unpack_from('<I', rec, 15)[0]
        xyz = struct.unpack_from('<3f', rec, 19)
        quat = struct.unpack_from('<4f', rec, 31)
        if not all(math.isfinite(v) for v in xyz + quat):
            errors.append({'code': 'NONFINITE_BONE_VALUE', 'bone': name, 'frame': frame})
        else:
            norm = math.sqrt(sum(x*x for x in quat))
            if norm < 0.00001 or abs(norm - 1.0) > 0.2:
                warns.append({'code': 'NONUNIT_QUATERNION', 'bone': name, 'frame': frame})
        bones[name].append((frame, xyz))
    morph_count = count(23)
    morphs = defaultdict(list)
    for _ in range(morph_count):
        rec = take(23)
        name = _name(rec[:15])
        frame = struct.unpack_from('<I', rec, 15)[0]
        weight = struct.unpack_from('<f', rec, 19)[0]
        if not math.isfinite(weight):
            errors.append({'code': 'NONFINITE_MORPH_WEIGHT', 'morph': name, 'frame': frame})
        elif not 0 <= weight <= 1:
            warns.append({'code': 'MORPH_WEIGHT_OUT_OF_RANGE', 'morph': name, 'frame': frame})
        morphs[name].append(frame)
    max_frame = 0
    for name in sorted(bones):
        frames = sorted(bones[name], key=lambda entry: entry[0])
        seen = set()
        prev = None
        for frame, xyz in frames:
            max_frame = max(max_frame, frame)
            if frame in seen:
                warns.append({'code': 'DUPLICATE_BONE_FRAME', 'bone': name, 'frame': frame})
            seen.add(frame)
            if prev is not None and frame > prev[0] and all(math.isfinite(v) for v in xyz + prev[1]):
                speed = math.dist(prev[1], xyz) / (frame - prev[0])
                if speed > 2.0:
                    warns.append({'code': 'LARGE_POSITION_STEP', 'bone': name, 'frame': frame,
                                  'units_per_frame': round(speed, 6)})
            prev = (frame, xyz)
    for name in sorted(morphs):
        seen = set()
        for frame in sorted(morphs[name]):
            max_frame = max(max_frame, frame)
            if frame in seen:
                warns.append({'code': 'DUPLICATE_MORPH_FRAME', 'morph': name, 'frame': frame})
            seen.add(frame)
    return {
        'checkpoint': 'LAB_CP03', 'operation': 'MOTION_TIMELINE_DIAGNOSTICS',
        'mode': 'SYNTHETIC_NO_ASSET_IO_NO_MOTION_WRITE',
        'status': 'FAIL' if errors else ('WARN' if warns else 'PASS'),
        'summary': {'model': model, 'bone_keyframes': bone_count, 'morph_keyframes': morph_count,
                    'unique_bones': len(bones), 'unique_morphs': len(morphs),
                    'max_frame': max_frame, 'remaining_bytes_unparsed': len(data) - pos},
        'errors': errors, 'warnings': warns,
        'scope': 'VMD 0002 bone/morph records only; later tracks not parsed',
        'writes': False,
    }
