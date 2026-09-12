# P2a / depth3-file — entrypoint repair

Candidate SHA256: `d8d8b3b0b6bfdf88b890791f597ec147ab616f936a2a576fb1c954983fe518a8`.
Parent algorithm: `depth3` / `448d398eedba9cbffc6abcec0ab214a4910c5c917f43c2457fe730dd4d43db84`.

Change: append a uniquely named `_terminal_submission_entrypoint(obs, config=None)` after all helpers. This fixes the official loader dictionary-insertion-order issue; no task/market policy change. The original algorithmic results belong to their original hashes, not this file.

Validation at initial checkpoint: 3 official-loader regression tests pass, including four revision names, failure reproduction on old artifact, and loader/explicit-function action parity on selected observations. Full720-state tests are tracked separately in the P2 result index, not asserted complete here.

Decision: RESEARCH ONLY / NOT PROMOTED. No release gate passed or Kaggle submission. Further paired testing and whole-track review are required. [Details](../p2a-20260912-report.md).
