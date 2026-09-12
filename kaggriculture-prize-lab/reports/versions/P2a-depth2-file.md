# P2a / depth2-file — entrypoint repair

Candidate SHA256: `c06dc267e07ce5b07e8bf5380104dc3c87efbbbcdaf72386677ba31e7bb55624`.
Parent algorithm: `depth2` / `0692a62a180906eca9ea292d1a9badcbbfe09659790105f53b98f9a71f0c2b57`.

Change: append a uniquely named `_terminal_submission_entrypoint(obs, config=None)` after all helpers. This fixes the official loader dictionary-insertion-order issue; no task/market policy change. The original algorithmic results belong to their original hashes, not this file.

Validation at initial checkpoint: 3 official-loader regression tests pass, including four revision names, failure reproduction on old artifact, and loader/explicit-function action parity on selected observations. Full720-state tests are tracked separately in the P2 result index, not asserted complete here.

Decision: RESEARCH ONLY / NOT PROMOTED. No release gate passed or Kaggle submission. Further paired testing and whole-track review are required. [Details](../p2a-20260912-report.md).
