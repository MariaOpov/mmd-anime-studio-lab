# MMD Anime Studio Lab — LAB-CP01 Foundation

**Repository proposed:** `MariaOpov/mmd-anime-studio-lab`  
**Windows root:** `D:\MMD\mmd-anime-studio-lab`  
**Status:** CP01 offline source foundation, independent from `MariaOpov/mmd-asset-registry`.

## Actually implemented

- Python 3.12+ package using `src/` layout with CLI `mmd-lab` and Tkinter R0 prototype GUI.
- Bundled, allowlisted Extension Host with two built-ins: MMD Doctor (limited PMX read-only inspection) and Motion Peek (VMD bone/morph counts).
- Synthetic PMX/VMD demo fixtures, original R0 regression suite and new CP01 package/CLI/isolation tests.
- Unique Windows evidence TXT/JSON under `D:\Assets\MMDAnimeStudioLab\Evidence` when `D:\Assets` exists; otherwise `%LOCALAPPDATA%\MMDAnimeStudioLab\Evidence`.
- One Notepad window automatically opened by each CMD on PASS, FAIL or HOLD, if Notepad is installed.
- GitHub Actions **definition only**, not executed on GitHub; intended to run on Windows Python 3.12 after a separate repository is created/pushed.

## Not implemented / not claimed

- New remote GitHub repository is **NOT created** by this artifact. No Git initialization, stage/commit/push or protected-repo writes performed.
- PySide6/QtWebEngine UI, WebGL2 viewer and Studio IPC are **planned** for later CPs; R0 Tkinter UI is retained.
- No third-party plugin execution, no editing PMX/VMD, no external asset inspection in CP01 GUI/CLI, no AI training/inference, no physics/animation playback, no full PMX/VMD validation.
- CP20 remains **HOLD**; this Lab package does not modify or access CP20 protected worktrees.

## Windows quick start (single command each)

1. Extract the ZIP into `D:\MMD\` (the archive itself contains the new `mmd-anime-studio-lab` directory). Do not extract inside any existing MMD Studio repo.
2. Inside `D:\MMD\mmd-anime-studio-lab`, install **Python 3.12** with Tkinter. Run `RUN_CP01_PREFLIGHT.cmd` (includes source SHA256 integrity checks).
3. Run `RUN_CP01_QA.cmd`. Evidence opens automatically in Notepad; verify PASS.
4. Run `RUN_MMD_LAB.cmd`. Click `Demo PMX` / `Demo VMD` using **only bundled synthetic fixtures**. On closing GUI, a unique TXT opens.
5. Optional developer mode: `python -m pip install -e .` then `python -m mmd_lab plugins`. CP01 CLI inspection accepts only bundled synthetic demo paths.

**Important:** Do not use the Lab GUI on personal or real PMX/VMD until that input scope has been separately authorized. The synthetic demos are explicitly provided to test without them.

## GitHub creation and first push (separate explicit action)

Create an **empty** repository at GitHub named `mmd-anime-studio-lab` under `MariaOpov` (do not initialize README/LICENSE/.gitignore, as this package contains its own). After CP01 QA PASS and reviewing the file tree, in a terminal within the NEW root only:

```cmd
git init -b main
git add .
git commit -m "feat: bootstrap MMD Anime Studio Lab CP01"
git remote add origin https://github.com/MariaOpov/mmd-anime-studio-lab.git
git push -u origin main
```

Do not run these commands inside `D:\MMD\mmd-asset-registry`. No GitHub remote operations are part of the bundled launchers. Git ignore protects usual real MMD assets; check `git status` before any commit.

## CP roadmap

- **LAB-CP01:** package foundation + QA + CI definition (this archive).
- **LAB-CP02:** independent PySide6/QtWebEngine UI + Qt WebChannel bridge, tests first.
- **LAB-CP03:** WebGL2 workspace and more detailed PMX/VMD diagnostics; Smart Morph after review.
- **LAB-CP04:** versioned Studio IPC, opt-in read-only integration after Studio approval.

See `docs/WORKERS.md` and `docs/BOUNDARIES.md`. License intentionally undecided; review project licensing and third-party obligations before distribution.
