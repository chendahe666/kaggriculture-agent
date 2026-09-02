# Benchmark Summary: v1-endgame-guard

- Generated: `2026-09-02T16:43:53.596653+00:00`
- Agent: `main.py`
- SHA256: `c77b217c4da4f818fe0b5250340cdf400b489a90a2777746cac60c8f45da8f00`
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
- Slowest agent call: `1.640 ms`

## Overall

- Wins / draws / losses: `60 / 0 / 0`
- Win rate: `100.0%`
- Median cash: `3966`
- Worst cash: `3799`
- Best cash: `4072`
- Median cash delta: `971`
- Worst cash delta: `48`

## End state

- Median / max unused seeds: `0 / 0`
- Median unsold shed items: `0`
- Median carried items: `0`
- Median remaining plant tiles: `0`
- Max immature wheat tiles: `0`

## By opponent and side

| Opponent | Side | Done | W-D-L | Win rate | Median cash | Worst cash | Median delta | Worst delta |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| pass | 0 | 10/10 | 10-0-0 | 100.0% | 3971 | 3799 | 971 | 799 |
| pass | 1 | 10/10 | 10-0-0 | 100.0% | 3971 | 3799 | 971 | 799 |
| random | 0 | 10/10 | 10-0-0 | 100.0% | 3994 | 3809 | 3994 | 3809 |
| random | 1 | 10/10 | 10-0-0 | 100.0% | 3957.5 | 3908 | 3957.5 | 3908 |
| starter | 0 | 10/10 | 10-0-0 | 100.0% | 3953.5 | 3828 | 391 | 48 |
| starter | 1 | 10/10 | 10-0-0 | 100.0% | 3953.5 | 3828 | 391 | 48 |

## Interpretation boundary

This is a local engineering benchmark. It verifies completion, stability,
and paired behavior against fixed built-in opponents. It does not estimate
or predict the live Kaggle skill rating.
The built-in `random` opponent can vary across reruns even with the same
environment seed. Use `pass` and `starter` for exact deterministic regression,
and use `random` only as a repeated stochastic robustness probe.
