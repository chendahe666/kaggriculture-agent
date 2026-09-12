# P2a / depth2-file — entrypoint repair

Candidate SHA256: `c06dc267e07ce5b07e8bf5380104dc3c87efbbbcdaf72386677ba31e7bb55624`.
Parent algorithm: `depth2` / `0692a62a180906eca9ea292d1a9badcbbfe09659790105f53b98f9a71f0c2b57`.

Change: append a uniquely named `_terminal_submission_entrypoint(obs, config=None)` after all helpers. This fixes the official loader dictionary-insertion-order issue; no task/market policy change. The original algorithmic results belong to their original hashes, not this file.

Validation at initial checkpoint: 3 official-loader regression tests pass, including four revision names, failure reproduction on old artifact, and loader/explicit-function action parity on selected observations. Full720-state tests are tracked separately in the P2 result index, not asserted complete here.

Decision: RESEARCH ONLY / NOT PROMOTED. No release gate passed or Kaggle submission. Further paired testing and whole-track review are required. [Details](../p2a-20260912-report.md).

## R1 online exploration, 2026-09-12

Subsequent P2b same-case development results: 37W/0T/3L over40games vs baseline35W/2T/3L; margin delta+379.325. This does not change the historical initial-checkpoint claim above. No additional Arlene stress result exists for this version.

Following the user's explicit request to try two candidates despite unpassed statistical promotion gates, this unchanged SHA was uploaded as submission **56180702**, server time **2026-09-12T07:03:34.037Z**. Upload accepted, initially PENDING. Extra actual-path double-seat checks each completed720frames, bothDONE, no stderr and exact prior rewards; max own framework call75.572/69.509ms, overage60seconds. Not a statistical promotion or a rating-uplift claim. [R1 record](../online-exploration-20260912.md).
