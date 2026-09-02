# Benchmark Summary: v4-one-hand-six-near

- Generated: `2026-09-02T17:01:28.021663+00:00`
- Agent: `main.py`
- SHA256: `65c1b247435f8413506dc1986f19ad32b623983dd6207b0bc23bacae2b490914`
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
- Plant-to-weed transitions: `0`
- Unit tile-action conflicts: `0`
- Hire orders: `1740`
- Hand non-PASS actions: `17880`
- Slowest agent call: `1.796 ms`

## Overall

- Wins / draws / losses: `60 / 0 / 0`
- Win rate: `100.0%`
- Median cash: `8456`
- Worst cash: `6441`
- Best cash: `9001`
- Median cash delta: `5344.5`
- Worst cash delta: `3441`

## End state

- Median / max unused seeds: `0 / 0`
- Median unsold shed items: `0`
- Median carried items: `0`
- Median remaining plant tiles: `0`
- Max immature wheat tiles: `0`
- Median unique plant tiles used: `6`
- Median harvest actions: `22`
- Median mature wait: `12 steps`
- Max mature wait: `16 steps`
- Unharvested mature tiles: `0`

## By opponent and side

| Opponent | Side | Done | W-D-L | Win rate | Median cash | Worst cash | Median delta | Worst delta |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| pass | 0 | 10/10 | 10-0-0 | 100.0% | 8243.5 | 6441 | 5243.5 | 3441 |
| pass | 1 | 10/10 | 10-0-0 | 100.0% | 8243.5 | 6441 | 5243.5 | 3441 |
| random | 0 | 10/10 | 10-0-0 | 100.0% | 8566.5 | 7928 | 8566.5 | 7928 |
| random | 1 | 10/10 | 10-0-0 | 100.0% | 8594 | 7186 | 8594 | 7186 |
| starter | 0 | 10/10 | 10-0-0 | 100.0% | 8453.5 | 7421 | 4857 | 3957 |
| starter | 1 | 10/10 | 10-0-0 | 100.0% | 8453.5 | 7421 | 4857 | 3957 |

## Interpretation boundary

This is a local engineering benchmark. It verifies completion, stability,
and paired behavior against fixed built-in opponents. It does not estimate
or predict the live Kaggle skill rating.
The built-in `random` opponent can vary across reruns even with the same
environment seed. Use `pass` and `starter` for exact deterministic regression,
and use `random` only as a repeated stochastic robustness probe.
