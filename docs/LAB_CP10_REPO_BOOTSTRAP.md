# LAB-CP10: GitHub readiness (no Git writes)

- Windows local root: `D:\MMD\mmd-anime-studio-lab`.
- GitHub destination **proposed, not created**: `MariaOpov/mmd-anime-studio-lab`.
- `python -B -m cp10.cli audit`: read-only SHA256 validation, checkpoints CP01–CP10.
- `python -B -m cp10.cli export`: writes an immutable source ZIP **outside** the repo, under `D:\Assets\MMDAnimeStudioLab\Staging` (or `%LOCALAPPDATA%` fallback), including only pinned source files and a machine-readable inventory.
- `.github/workflows/ci-lab-all.yml` is prepared but not yet executed on GitHub. Existing CP01 CI file stays unchanged.
- CP01–CP09 source files are never overwritten by CP10; no installer writes to the main Studio repository.
- Existing `.gitignore` excludes personal media and evidence. Export includes only two synthetic PMX/VMD fixtures.
- For remote creation later, Owner should create **empty** repository at https://github.com/new . Review exported snapshot, source tree and LICENSE choice before any explicit local Git init/add/commit/push. No automated Git writes in CP10.
- User may defer GUI. PySide6 is not required for source audit or export.
