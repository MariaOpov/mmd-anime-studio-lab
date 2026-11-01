LAB-CP09 | SOURCE CONSOLIDATION + UNIFIED RUNTIME (synthetic-only)

This checkpoint adds one API/CLI facade over the already accepted CP05->CP08 extension host.
The four extension implementations stay byte-for-byte identical. It does NOT
implement PMX/VMD writes, real asset access, a Studio bridge or GUI changes.

After Windows deployment PASS, use RUN_CP09_DEMO.cmd, or in CMD from D:\MMD\mmd-anime-studio-lab first set PYTHONPATH:
  set "PYTHONPATH=%CD%\src;%CD%;%PYTHONPATH%"
  py -3.12 -B -m cp09.cli status
  py -3.12 -B -m cp09.cli readiness
  py -3.12 -B -m cp09.cli plan both
  py -3.12 -B -m cp09.cli run both

GitHub repository is NOT created automatically. No git init/commit/push.
The user must explicitly create/review a new GitHub remote later.

CP02 Qt GUI still HOLD_DEFERRED. CP20 canonical Studio stays HOLD and untouched.
