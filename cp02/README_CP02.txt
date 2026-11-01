MMD Anime Studio Lab CP02 / PySide6 Qt Workspace (read-only)

Add-only separate workspace, does not alter CP01's 24 pinned files or Studio CP20.
The GUI requires an existing local PySide6 installation containing QtWebEngineWidgets.
The deployment deliberately does NOT install third-party modules or access network.
CP01's existing Tk GUI remains usable unchanged.

RUN_CP02_QA.cmd: verifies CP01+CP02 pinned files and runs CP02-only synthetic tests.
RUN_CP02_GUI.cmd: verifies pins then opens PySide6/QtWebEngine UI, one evidence TXT/JSON
under D:\Assets\MMDAnimeStudioLab\Evidence; opens exactly one Notepad at finish.

If GUI returns HOLD_MISSING_PYSIDE6_QTWEBENGINE, do not infer a broken CP01.
Install Qt dependency only after separate approval and review of PySide6/Qt licensing.

Only Demo PMX and Demo VMD are accepted; no real asset reads or writes.
No process IPC to MMD Studio; no Git changes; no plugin code loaded from disk manifests.
Status: CP02 QA can PASS without Qt; Qt GUI smoke on Windows remains UNVERIFIED.
