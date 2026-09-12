# P2b / timing-file — terminal selling time v1

Candidate SHA256: `6509cee22521b47a0e4f33b923dd48d4740f9864c5c79a01296b6d3cb0cc10fb`.
Baseline: COK `1c7335f698692f1c7bac34913a9ededc0f736dfb2b51346a4fa59098ab471d01`.
Engine: `bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e`.

Hypothesis/method: keep baseline work actions, defer selected last-day sales until known NPC demand when full legal public history, capacity, cash and order-slot checks allow. Frozen v1 implementation; source remains archived despite discovered defects.

Evaluation: 40 full development games, five provisional source/behavior families (COK, Seyam, Lonespear, Deepesh, Maverick), seeds 91101–91104, both seats. Same-case controls reused. Score win1/tie0.5/loss0; no untouched confirmation. Official last-callable selection, but instrumented function timing is not container certification.

Results: 35W/2D/3L, 36/40 outcome points, identical to baseline. Mean paired coin-margin gain +42.55; actual quantities unchanged and total sale revenue +1702. All games 720 states, DONE/DONE, no errors or final carried goods. Three raw preterminal fingerprints differ; causes remain unverified, all retained in primary results.

Decision: REJECT AS SUBMISSION / retain research evidence. Independent interface tests show later fixed sales incorrectly counted toward earlier HIRE financing and canceled early sales could leave phantom forward debts. 17 initial timing tests passed but did not cover those defects; 8 later safety tests demonstrate them and their repair in a NEW hash. No Kaggle submission or baseline replacement.

Full report: [P2b](../p2b-20260912-report.md). Paired table: `results/terminal-20260912/p2b-interactions.json`. New safety revision is separately versioned, not retroactively credited here.
