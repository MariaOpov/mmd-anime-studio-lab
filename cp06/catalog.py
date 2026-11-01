"""Locked, explicit lifecycle metadata; never loads third-party executable code."""
from __future__ import annotations
from cp05.broker import KIND

IDS = tuple(sorted({v[0] for v in KIND.values()}))
# The actual four bundled modules are currently independent; do not invent hard
# dependencies. Dependency graphs are exercised using synthetic test records.
BUILTIN_DEPENDENCIES = {key: () for key in IDS}
BY_ID = {extension_id: (kind, capability) for kind, (extension_id, capability) in KIND.items()}


def verify_catalog(broker):
    catalog = broker.catalog()
    if not catalog.get('ok') or catalog.get('sdk_version') != '0.1':
        raise ValueError('HOLD_CP05_CATALOG')
    entries = catalog.get('extensions')
    if type(entries) is not list or len(entries) != 4:
        raise ValueError('HOLD_CATALOG_COUNT')
    if {item['id']: item['capability'] for item in entries} != {
        extension_id: cap for extension_id, (_, cap) in BY_ID.items()
    }:
        raise ValueError('HOLD_CATALOG_DRIFT')
    return {item['id']: {'id': item['id'], 'name': item['name'],
                          'version': item['version'], 'capability': item['capability'],
                          'enabled': item['enabled']} for item in entries}
