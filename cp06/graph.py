"""Bounded deterministic dependency resolution, no package downloads/imports.

Runtime currently has no hard dependencies between bundled extensions. The
resolver supports synthetic graphs so a later approved catalog can use it.
"""
from __future__ import annotations
MAX_NODES=32
MAX_EDGES=128

class DependencyHold(ValueError):
    pass

def plan_dependencies(graph, selected):
    if type(graph) is not dict or not 1 <= len(graph) <= MAX_NODES:
        raise DependencyHold('HOLD_GRAPH_SHAPE')
    normalized={}
    edges=0
    for node, parents in graph.items():
        if type(node) is not str or not node or len(node)>128:
            raise DependencyHold('HOLD_DEPENDENCY_ID')
        if type(parents) not in (tuple, list):
            raise DependencyHold('HOLD_DEPENDENCY_SHAPE')
        if len(parents)!=len(set(map(repr,parents))):
            raise DependencyHold('HOLD_DUPLICATE_DEPENDENCY')
        if any(type(p) is not str or not p or len(p)>128 for p in parents):
            raise DependencyHold('HOLD_DEPENDENCY_ID')
        edges+=len(parents)
        if edges>MAX_EDGES: raise DependencyHold('HOLD_GRAPH_EDGE_LIMIT')
        normalized[node]=tuple(sorted(parents))
    if type(selected) not in (list, tuple) or not selected:
        raise DependencyHold('HOLD_SELECTION_SHAPE')
    if len(selected)>MAX_NODES or any(type(n) is not str for n in selected):
        raise DependencyHold('HOLD_SELECTION_SHAPE')
    if len(selected)!=len(set(selected)):
        raise DependencyHold('HOLD_SELECTION_DUPLICATE')
    output=[];temporary=set();complete=set()
    def visit(node):
        if node not in normalized: raise DependencyHold('HOLD_MISSING_DEPENDENCY')
        if node in temporary: raise DependencyHold('HOLD_DEPENDENCY_CYCLE')
        if node in complete:return
        temporary.add(node)
        for prerequisite in normalized[node]:visit(prerequisite)
        temporary.remove(node);complete.add(node);output.append(node)
    for node in sorted(selected):visit(node)
    return tuple(output)
