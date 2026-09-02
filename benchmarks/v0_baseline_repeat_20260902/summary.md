# Benchmark Summary: v0-baseline-repeat

- Generated: `2026-09-02T16:39:07.651875+00:00`
- Agent: `main.py`
- SHA256: `9f5c949b88b47451500de13c6e5399cea4958e0cb0c1aa2c0042f4d3d4fe6a2d`
- Python: `3.13.12`
- kaggle-environments: `1.32.7`
- Seeds: `[20260901, 20260902, 20260903, 20260904, 20260905, 20260906, 20260907, 20260908, 20260909, 20260910]`
- Opponents: `['pass', 'random', 'starter']`
- Sides: `[0, 1]`

## Gate

**PASS**

- Completed: `60/60`
- Shape-invalid actions: `0`
- Wrapper exceptions: `0`
- Agent internal exceptions: `0`
- Runner errors: `0`
- Slowest agent call: `1.442 ms`

## Overall

- Wins / draws / losses: `60 / 0 / 0`
- Win rate: `100.0%`
- Median cash: `3955`
- Worst cash: `3779`
- Best cash: `4048`
- Median cash delta: `951`
- Worst cash delta: `28`

## By opponent and side

| Opponent | Side | Done | W-D-L | Win rate | Median cash | Worst cash | Median delta | Worst delta |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| pass | 0 | 10/10 | 10-0-0 | 100.0% | 3951 | 3779 | 951 | 779 |
| pass | 1 | 10/10 | 10-0-0 | 100.0% | 3951 | 3779 | 951 | 779 |
| random | 0 | 10/10 | 10-0-0 | 100.0% | 3973.5 | 3892 | 3973.5 | 3892 |
| random | 1 | 10/10 | 10-0-0 | 100.0% | 3955 | 3831 | 3934 | 3464 |
| starter | 0 | 10/10 | 10-0-0 | 100.0% | 3933.5 | 3808 | 371 | 28 |
| starter | 1 | 10/10 | 10-0-0 | 100.0% | 3933.5 | 3808 | 371 | 28 |

## Interpretation boundary

This is a local engineering benchmark. It verifies completion, stability,
and paired behavior against fixed built-in opponents. It does not estimate
or predict the live Kaggle skill rating.
