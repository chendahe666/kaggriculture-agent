# K320 V23 current submission freeze

This directory freezes the unmodified current candidate for a first Kaggle
score check.

- Agent version: `K320-adaptive-rank1-no-late-seed`
- Source artifact: Rayk Notebook V23, downloaded 2026-09-02
- Expected `main.py` SHA-256: `6c709f6d3ce6cf221a9495de7e716fcd1b660e3bbc8ee5679b63233d0265a812`
- `submission.tar.gz` SHA-256: `949f128b7a4e6d4d870a58a4ffc3c2c56a597d6efe71b81f63761fb3c8c4aea3`
- Archive size: 99,205 bytes
- Local direct panel versus COK V10: 0/8, mean margin -1487.25
- Purpose: obtain a real Kaggle leaderboard observation before optimization

Upload `dist/submission.tar.gz`. The archive contains `main.py` at its root,
the Apache 2.0 license, and the third-party notice.

The package was built twice with the same SHA-256. Its archived `main.py` was
compiled and imported successfully, exposes a callable `agent`, and matches the
frozen source hash above.

No Kaggle score is claimed until the remote submission reaches a completed,
scored state.
