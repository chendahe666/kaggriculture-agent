# P2b / depth2-timing-file — joint planner and market time v1

Candidate SHA256: `de4f002b5bd990728b8d31d3ea47a0788d5dbb20a9cf3edf92239e7aabe1e6cd`.
Planning parent: `c06dc267e07ce5b07e8bf5380104dc3c87efbbbcdaf72386677ba31e7bb55624`.
Baseline: COK `1c7335f698692f1c7bac34913a9ededc0f736dfb2b51346a4fa59098ab471d01`.
Engine: `bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e`.

Hypothesis/method: combine depth-2 terminal harvest/delivery planning with guarded delayed selling; price feedback can also change future task selection. Joint A/B/AB comparison, not an assumed sum of local improvements.

Evaluation: 40 full development games with five provisional families, seeds 91101–91104, both seats; same-case baseline/A/B controls reused. 160 rows are the whole four-arm comparison, not 160 new AB games. Plus one duplicate full economic diagnosis and two actual-file-path duplicate smoke games for this hash. No untouched confirmation.

Results: 37W/0D/3L, 37/40 outcome points versus baseline 36/40; only two COK mirror draws turn into wins. Mean margin gain +510.1; relative to A +130.775, coin interaction +88.225, outcome interaction zero. Still -78/-79 coin regressions in two Deepesh scenarios; no outcome downgrades. All 40 games clean/720/DONE, final carried stock zero. Economic diagnosis reconciles cash/material exactly for one former negative example. Both raw-file smoke rewards match; local framework own maxima 73.469/70.620 ms, not an online guarantee.

Decision: REJECT AS SUBMISSION / retain research evidence. Shares v1 financing/phantom-debt interface defects reproduced after this run. A new safety hash must earn its own evidence. Neither mean coins nor mirror-only outcome gain establishes prize-level strength; release gate not opened, COK unchanged, no Kaggle upload.

Full report: [P2b](../p2b-20260912-report.md). Interaction data: `results/terminal-20260912/p2b-interactions.json`; raw-file checks: `results/terminal-20260912/file-smoke/`.
