# MMD Lab isolation and safety contract

- This project is independent of `D:\MMD\mmd-asset-registry` and its CP20 source/gates. CP20_CLOSEOUT remains HOLD.
- No access to real PMX/VMD by default; use only synthetic fixtures until separate Owner permission.
- Model Doctor and Motion Peek open models **read-only**, limited scope; do not represent them as repair engines or fully conformant parsers.
- No dynamic plugin loading, imported arbitrary entrypoint, network requests, implicit shell execution or auto-install.
- Extension manifests are checked against reviewed built-in allowlist; untrusted manifests are not execution authority.
- No `git add/commit/push/merge` in default launchers. A separate explicit user action creates the new remote and publishes.
- No server or Studio IPC exists in CP01; future IPC must version request/response schemas, permissions and revocation.
- Source artifacts are portable; evidence goes outside repo on Windows and never overwrites an earlier run.
- Every CMD must save unique TXT/JSON, print evidence paths and true exit code, and open **exactly one** Notepad TXT on PASS/FAIL/HOLD when available.
