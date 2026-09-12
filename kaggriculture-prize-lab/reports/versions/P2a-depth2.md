# P2a / depth2

Parent: COK V10 `1c7335f698692f1c7bac34913a9ededc0f736dfb2b51346a4fa59098ab471d01`.
Candidate: `experiments/track-terminal-20260912/depth2/main.py`.
SHA256: `0692a62a180906eca9ea292d1a9badcbbfe09659790105f53b98f9a71f0c2b57`.

Hypothesis: state-based last-day work/transport/liquidation can recover reachable value. Method: bounded task-chain beam, depth 2, with joint claims and safe deposits. Shared resources: unit actions, cargo/shed capacity, sale slots and shared prices. No neural training or online LLM.

Evaluation: 1.32.7, full720 states, four named responsive families, development seeds91101/91102 both seats, explicit module.agent. Actual 16 candidate games matched to the same16 controls. Baseline 14.0/16 points; candidate 14.0/16; mean margin gain 428.75; outcome flips +0/-0. All clean True; max observed call 223.165ms. Not an independent holdout or rating forecast.

Decision: REJECT AS SUBMISSION ARTIFACT. Official loader selects the last newly inserted helper rather than the redefined agent. Explicit function experiment is algorithmic evidence only. Retain the failure and use separately hashed depth2-file revision for any subsequent file-based work. No baseline replacement or Kaggle submission.

Full diagnosis and methodological limits: [P2a report](../p2a-20260912-report.md). Raw paired rows: results/terminal-20260912/development. Git version timestamp is actual checkpoint time, not a fabricated earlier experiment time.
