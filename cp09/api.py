"""Single stable public façade around existing CP06–CP08 code.

No Qt, no network, no PMX/VMD file IO, no dynamic plugin loading.
The four bundled extension IDs remain the only runnable operations.
"""
from __future__ import annotations
from cp08.guard import GuardedSession
from cp06.catalog import IDS

MORPH = 'org.mmdstudio.smart-morph-plus'
MOTION = 'org.mmdstudio.motion-lab'
KINDS = {'morph': (MORPH,), 'motion': (MOTION,), 'both': (MOTION, MORPH)}

class StudioLabAPI:
    """In-memory session. Construct a fresh instance for each independent user session."""
    def __init__(self, guard=None):
        self._guard = GuardedSession() if guard is None else guard
        if not isinstance(self._guard, GuardedSession):
            raise TypeError('HOLD_CP09_GUARD_TYPE')

    def status(self):
        snap = self._guard.snapshot()
        return {'ok': True, 'checkpoint': 'LAB_CP09', 'api_version': '0.1',
                'mode': 'OFFLINE_SYNTHETIC_ONLY', 'extension_count': len(IDS),
                'extensions': snap['lifecycle']['extensions'],
                'quarantined': snap['quarantined'], 'session_unsafe': snap['session_unsafe'],
                'network': False, 'real_assets': False, 'writes': False}

    def plan(self, kind):
        if type(kind) is not str or kind not in KINDS:
            return {'ok': False, 'error': 'HOLD_CP09_UNKNOWN_OPERATION', 'writes': False}
        try:
            plan = self._guard.transaction.plan(list(KINDS[kind]))
        except (ValueError, TypeError):
            return {'ok': False, 'error': 'HOLD_CP09_PLAN', 'writes': False}
        return {'ok': True, 'checkpoint': 'LAB_CP09', 'api_version': '0.1',
                'operation': kind, 'requested': list(plan['requested']),
                'activation_order': list(plan['activation_order']),
                'execution_order': list(plan['execution_order']),
                'network': False, 'real_assets': False, 'writes': False}

    def run(self, kind):
        if type(kind) is not str or kind not in KINDS:
            return {'ok': False, 'error': 'HOLD_CP09_UNKNOWN_OPERATION', 'writes': False}
        report = self._guard.run(list(KINDS[kind]))
        return {'ok': report.get('ok') is True, 'checkpoint': 'LAB_CP09',
                'api_version': '0.1', 'operation': kind, 'result': report,
                'session_unsafe': self._guard.snapshot()['session_unsafe'],
                'network': False, 'real_assets': False, 'writes': False}
