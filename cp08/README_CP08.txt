LAB-CP08 — IN-PROCESS FAULT CONTAINMENT (SOURCE-ONLY)

BUNDLED-only four CP04 extensions; CP01-CP07 byte-exact.
Guards CP07 transactional execution with per-extension, per-session failure
strikes and threshold-limited quarantine. Other healthy extensions can proceed.
A quarantined dependency blocks its dependents. Manual per-extension reset is
explicit and never restores an unsafe/unclean transaction session.

Scope: synthetic fixtures and test-only fault injection. No real PMX/VMD,
no network, file output, GUI, Qt, dynamic plugin load or plugin installation.
This is NOT hard process isolation, timeout enforcement, deadlock protection,
crash recovery, or third-party plugin security sandbox.
