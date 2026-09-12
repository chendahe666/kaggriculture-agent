# P2a / depth1-file — entrypoint repair

Candidate SHA256: `f6c12107f65c4f344dc2eaafebc744510f51a0eb10e4c705f2808bbebd512674`.
Parent algorithm: `depth1` / `7e1225a6b67800ce70544162f594a6a4626c756ea547ff47bb6d84cb44dfbe0d`.

Change: append a uniquely named `_terminal_submission_entrypoint(obs, config=None)` after all helpers. This fixes the official loader dictionary-insertion-order issue; no task/market policy change. The original algorithmic results belong to their original hashes, not this file.

Validation at initial checkpoint: 3 official-loader regression tests pass, including four revision names, failure reproduction on old artifact, and loader/explicit-function action parity on selected observations. Full720-state tests are tracked separately in the P2 result index, not asserted complete here.

Decision: RESEARCH ONLY / NOT PROMOTED. No release gate passed or Kaggle submission. Further paired testing and whole-track review are required. [Details](../p2a-20260912-report.md).
