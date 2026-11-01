LAB-CP06 — EXTENSION LIFECYCLE + DEPENDENCY RESOLUTION (SOURCE-ONLY)

Scope: four trusted CP04 bundled extensions, using CP05 default-deny grants.
Stable states: READY, ACTIVE, DISABLED. activate => session grant; stop => revoke.
No persistence, arbitrary plugin load, third-party code, real PMX/VMD reads,
asset writing, install/uninstall plugin operations, network or Qt dependency.

Actual four bundled modules have NO declared hard interdependencies. The
synthetic planner validates topological order, missing dependency and cycles;
a future approved release can pin a nonempty graph after auditing actual needs.

CP01–CP05 files must remain SHA-identical. Add-only CP06 source and SHA manifest.
Windows: RUN_CP06_QA.cmd and RUN_CP06_DEMO.cmd write TXT/JSON and open one Notepad.
CP02 GUI acceptance remains deferred. This is not an untrusted-code OS sandbox.
