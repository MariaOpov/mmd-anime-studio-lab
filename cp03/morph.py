"""Deterministic bounded morph blend *preview* for synthetic JSON offsets only.

No PMX parser or PMX/model write path. Offsets are input from a test fixture.
The CP01 ExtensionHost is not modified and does not load this module.
"""
from __future__ import annotations

import math
from collections import defaultdict


class MorphHold(ValueError):
    """Malformed/unsafe synthetic morph request."""


def _number(value, label: str, max_abs: float = 10000.0) -> float:
    if type(value) not in (int, float) or not math.isfinite(value) or abs(value) > max_abs:
        raise MorphHold('INVALID_' + label)
    return float(value)


def blend_preview(document: dict, weights: dict) -> dict:
    """Blend vertex offsets, reporting vertex collisions and opposition, without IO."""
    if type(document) is not dict or type(weights) is not dict:
        raise MorphHold('INVALID_DOCUMENT_OR_WEIGHTS')
    vertex_count = document.get('vertex_count')
    morphs = document.get('morphs')
    if type(vertex_count) is not int or not 1 <= vertex_count <= 100000:
        raise MorphHold('INVALID_VERTEX_COUNT')
    if type(morphs) is not list or not 1 <= len(morphs) <= 128:
        raise MorphHold('INVALID_MORPH_COUNT')
    names = set()
    contributions = defaultdict(list)
    touched_by = defaultdict(set)
    for morph in morphs:
        if type(morph) is not dict:
            raise MorphHold('INVALID_MORPH')
        name = morph.get('name')
        offsets = morph.get('offsets')
        if type(name) is not str or not name or len(name) > 80 or name in names:
            raise MorphHold('INVALID_OR_DUPLICATE_NAME')
        if type(offsets) is not list or len(offsets) > 100000:
            raise MorphHold('INVALID_OFFSETS')
        names.add(name)
        local_seen = set()
        for point in offsets:
            if type(point) is not dict or set(point) != {'vertex', 'delta'}:
                raise MorphHold('INVALID_OFFSET_SHAPE')
            idx, delta = point['vertex'], point['delta']
            if type(idx) is not int or idx < 0 or idx >= vertex_count or idx in local_seen:
                raise MorphHold('INVALID_OR_DUPLICATE_VERTEX')
            if type(delta) is not list or len(delta) != 3:
                raise MorphHold('INVALID_DELTA')
            vec = tuple(_number(v, 'DELTA') for v in delta)
            local_seen.add(idx)
            # Zero-weight contributions don't imply a collision.
            if name in weights:
                w = _number(weights[name], 'WEIGHT', 1.0)
                if not 0 <= w <= 1:
                    raise MorphHold('WEIGHT_OUT_OF_RANGE')
            else:
                w = 0.0
            if w and any(vec):
                contributions[idx].append((name, tuple(w * v for v in vec)))
                touched_by[idx].add(name)
    if not all(type(k) is str and k in names for k in weights):
        raise MorphHold('UNKNOWN_WEIGHT_NAME')
    # Validate weights for zero-offset morphs too.
    for name, value in weights.items():
        if not 0 <= _number(value, 'WEIGHT', 1.0) <= 1:
            raise MorphHold('WEIGHT_OUT_OF_RANGE')
    result = []
    conflicts = []
    max_magnitude = 0.0
    for idx in sorted(contributions):
        parts = sorted(contributions[idx], key=lambda x: x[0])
        delta = [math.fsum(p[1][axis] for p in parts) for axis in range(3)]
        magnitude = math.sqrt(sum(x * x for x in delta))
        max_magnitude = max(max_magnitude, magnitude)
        result.append({'vertex': idx, 'delta': [round(v, 6) for v in delta]})
        if len(touched_by[idx]) >= 2:
            opposing = any(
                left[1][axis] * right[1][axis] < 0
                for i, left in enumerate(parts) for right in parts[i+1:] for axis in range(3)
            )
            conflicts.append({'vertex': idx, 'morphs': sorted(touched_by[idx]),
                              'opposing_axis': opposing})
    return {
        'checkpoint': 'LAB_CP03', 'operation': 'SMART_MORPH_PREVIEW',
        'mode': 'SYNTHETIC_NO_ASSET_IO_NO_MODEL_WRITE',
        'status': 'WARN' if conflicts else 'PASS',
        'vertex_count': vertex_count, 'active_morphs': sorted(k for k, v in weights.items() if v > 0),
        'affected_vertices': len(result), 'offset_preview': result,
        'collisions': conflicts, 'max_displacement': round(max_magnitude, 6),
        'writes': False,
    }
