LAB-CP04 — Extension Host Integration (source-only, synthetic-only)

Keeps CP01/CP02/CP03 source 100% immutable. CP04 adds an explicit
composition host exposing four reviewed extensions; two CP03 adapters
are registered through a SHA-pinned static registry, never manifest-loaded code.

Usage after deployment (NO GUI, NO NETWORK):
    call "D:\MMD\mmd-anime-studio-lab\RUN_CP04_DEMO.cmd"
    call "D:\MMD\mmd-anime-studio-lab\RUN_CP04_QA.cmd"
The launchers set the required local Python path for the composition host.

The examples only use SHA-pinned bundled synthetic fixtures. PMX/VMD files
provided by callers cannot be opened using this CP04 interface.
Extension enable/disable is session-local and not persisted.
No PMX/VMD export, write, realtime preview, arbitrary plugins, AI or Qt.
Later GUI acceptance remains deferred; main Studio CP20 remains HOLD.
