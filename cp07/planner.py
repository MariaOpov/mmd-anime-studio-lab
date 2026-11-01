"""Pure dependency-aware execution planning; exact bundled extension IDs only."""
from __future__ import annotations
from cp06.catalog import IDS, BUILTIN_DEPENDENCIES
from cp06.graph import plan_dependencies, DependencyHold

class PlanHold(ValueError):
    pass

def build_plan(requested, graph=None):
    if type(requested) not in (list, tuple) or not 1 <= len(requested) <= len(IDS):
        raise PlanHold('HOLD_REQUEST_SHAPE')
    if any(type(e) is not str or e not in IDS for e in requested):
        raise PlanHold('HOLD_REQUEST_UNTRUSTED_EXTENSION')
    if len(requested) != len(set(requested)):
        raise PlanHold('HOLD_DUPLICATE_REQUEST')
    deps = dict(BUILTIN_DEPENDENCIES) if graph is None else graph
    if type(deps) is not dict or set(deps) != set(IDS):
        raise PlanHold('HOLD_GRAPH_ALLOWLIST')
    try:
        order = plan_dependencies(deps,requested)
    except DependencyHold as exc:
        raise PlanHold(str(exc)) from exc
    return {'checkpoint':'LAB_CP07',
            'requested':tuple(sorted(requested)),
            'activation_order':order,
            'execution_order':tuple(item for item in order if item in requested),
            'mode':'SYNTHETIC_ONLY', 'writes':False,'network':False,
            'real_assets':False}
