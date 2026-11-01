LAB-CP05 / Extension SDK & Permission Gates

CP01-CP04 sources are immutable. This is an add-only SDK proof of concept.
Supports 4 bundled synthetic-only extensions already exposed by CP04.
Default deny: each invocation needs explicit session-local grant for one exact
extension + capability. Grants are random opaque tokens, never saved to disk.
Denies unknown versions, paths, arbitrary arguments, unapproved entrypoints,
network access, file writes, and loading external plugins. No real model IO.

Manual commands after install (one NOTEPAD per run, evidence automatic):
  RUN_CP05_QA.cmd
  RUN_CP05_DEMO.cmd

NOTE: This is not a security sandbox for untrusted Python code. Third-party
plugins must eventually run in separate restricted processes with OS policy.
LAB CP02 GUI remains deferred. Qt is not required for CP05.
