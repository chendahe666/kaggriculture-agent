# P2a / depth1

Parent: COK V10 `1c7335f698692f1c7bac34913a9ededc0f736dfb2b51346a4fa59098ab471d01`.
Candidate: `experiments/track-terminal-20260912/depth1/main.py`.
SHA256: `7e1225a6b67800ce70544162f594a6a4626c756ea547ff47bb6d84cb44dfbe0d`.

Hypothesis: state-based last-day work/transport/liquidation can recover reachable value. Method: bounded task-chain beam, depth 1, with joint claims and safe deposits. Shared resources: unit actions, cargo/shed capacity, sale slots and shared prices. No neural training or online LLM.

Evaluation: 1.32.7, full720 states, four named responsive families, development seeds91101/91102 both seats, explicit module.agent. Actual 16 candidate games matched to the same16 controls. Baseline 14.0/16 points; candidate 14.0/16; mean margin gain 376.1875; outcome flips +0/-0. All clean True; max observed call 170.966ms. Not an independent holdout or rating forecast.

Decision: REJECT AS SUBMISSION ARTIFACT. Official loader selects the last newly inserted helper rather than the redefined agent. Explicit function experiment is algorithmic evidence only. Retain the failure and use separately hashed depth1-file revision for any subsequent file-based work. No baseline replacement or Kaggle submission.

Full diagnosis and methodological limits: [P2a report](../p2a-20260912-report.md). Raw paired rows: results/terminal-20260912/development. Git version timestamp is actual checkpoint time, not a fabricated earlier experiment time.
