# P2a / transport-file — entrypoint repair

Candidate SHA256: `901cf683dc605906f6014427a75e4cb9ce8ac97502bd8fdf1c0e1aeb5fc304df`.
Parent algorithm: `transport` / `5ca5804f7f0f9c89c4c758b2e83d7e70f504f10d45f028accd06adef5eb4df3f`.

Change: append a uniquely named `_terminal_submission_entrypoint(obs, config=None)` after all helpers. This fixes the official loader dictionary-insertion-order issue; no task/market policy change. The original algorithmic results belong to their original hashes, not this file.

Validation at initial checkpoint: 3 official-loader regression tests pass, including four revision names, failure reproduction on old artifact, and loader/explicit-function action parity on selected observations. Full720-state tests are tracked separately in the P2 result index, not asserted complete here.

Decision: RESEARCH ONLY / NOT PROMOTED. No release gate passed or Kaggle submission. Further paired testing and whole-track review are required. [Details](../p2a-20260912-report.md).
