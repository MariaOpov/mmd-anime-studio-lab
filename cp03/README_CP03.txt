MMD ANIME STUDIO LAB - LAB-CP03 / SOURCE-ONLY EXPERIMENT
=======================================================

Two *analysis-only* modules, not integrated in CP01 ExtensionHost and not GUI.

1. cp03.morph: bounded synthetic JSON morph vertex offset blend preview,
   collision/opposition report, deterministic sorted output; no PMX writes.
2. cp03.motion: VMD 0002 read-only bone/morph keyframe diagnostics from
   SHA-pinned CP01 SYNTHETIC_DEMO.vmd; no animation editor/export.

Expected: synthetic PMX Doctor output remains CP01 WARN, synthetic VMD
in CP03 reports WARN for zero quaternions; these are diagnostics, not crashes.

No Qt, network, package install, Git operations or real asset input.
CP01/CP02 files unchanged; 33 + 14 prior tests are intentionally NOT rerun.

RUN: py -3.12 -B -m cp03.cli morph
     py -3.12 -B -m cp03.cli motion
     py -3.12 -B -m unittest discover -s cp03/tests -v

ROADMAP: Future plugin registration and actual PMX morph extraction require
separate owner-scoped permission and test acceptance. No production claim.
