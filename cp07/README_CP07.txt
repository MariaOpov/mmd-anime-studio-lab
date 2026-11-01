LAB-CP07 — TRANSACTIONAL EXTENSION EXECUTION (SOURCE-ONLY)

Deterministic, bounded plan for four pinned CP04 extensions.
Activates prerequisites in topological order, executes only requested modules,
releases new session grants in reverse order on success or failure.
Existing active sessions stay active; failed cleanup/state mismatch yields HOLD.
No arbitrary plugins, real PMX/VMD, file writes, imports from untrusted
manifests, network, third-party installation, Qt or GUI testing.

CP01–CP06 files remain byte-exact. All CP07 operations are synthetic and
single-process; this is not an OS sandbox or robust crash-recovery system.
CMD launcher writes one unique TXT/JSON pair and opens exactly one Notepad.
