# LAB-CP01 — Twelve roles, eight active roles, three concurrent lanes maximum

These are **work ownership roles**, not claims of running twelve separate cloud agents.

| ID | Role | Ownership | Activation |
|---|---|---|---|
| W01 | Architecture & Core | `src/mmd_lab/core.py`, API contracts | CP01 |
| W02 | PMX Processing | PMX reader/validation tests | CP01 |
| W03 | VMD Processing | VMD reader/validation tests | CP01 |
| W04 | Extension SDK & Host | `src/mmd_lab/host.py`, manifests | CP01 |
| W05 | Desktop UI | `src/mmd_lab/ui.py`, later Qt UI | CP02 |
| W06 | 3D Rendering | `ui/viewport` in CP03 only | CP02 |
| W07 | QA | `tests/`, synthetic fixtures | CP01 |
| W08 | Security & Build | launchers, policy, CI, release | CP01 |
| W09 | Smart Morph & Facial | future `extensions/smart_morph/` | CP03 |
| W10 | AI Motion & Lip Sync | future optional plugin only | CP04 |
| W11 | Wardrobe / Assets | future optional plugin only | CP03 |
| W12 | Studio Integration | future versioned IPC adapter | CP04 |

**CP01 currently implemented:** W01–W04 and W07–W08 deliver working source/testing foundation; W05 retains R0 GUI without the new Qt migration; W06 is role-reserved, not a functional 3D renderer. W09–W12 are inactive.

**Coordination:** maximum 3 simultaneous, disjoint source-owning lanes; W01 approves cross-module contracts, W07 independently validates, W08 guards releases. Never allow multiple roles to rewrite the same path concurrently.
