# Benchmark Summary: v5_final_cycle5

- Generated: `2026-09-02T17:29:40.743023+00:00`
- Agent: `main.py`
- SHA256: `66a7f783db07a0f9122ee732a4a574487f9240ab64255c4212d322d9f4c4cd6d`
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
- Funding shortfall orders: `0`
- Hire orders: `1740`
- Hand non-PASS actions: `18327`
- Slowest agent call: `29.888 ms`

## Overall

- Wins / draws / losses: `60 / 0 / 0`
- Win rate: `100.0%`
- Median cash: `8618`
- Worst cash: `7356`
- Best cash: `12964`
- Median cash delta: `5670.5`
- Worst cash delta: `4356`
- Median realized sale revenue: `6332`
- Median realized average sale price: `38.145`
- Median revenue per land-day: `39.278`
- Median revenue per non-PASS unit action: `9.021`
- Median / max peak shed items: `24 / 28`
- Worst minimum cash: `2675`

## End state

- Median / max unused seeds: `6 / 6`
- Median / max unsold shed items: `0 / 0`
- Median / max carried items: `0 / 0`
- Median / max remaining plant tiles: `0 / 0`
- Max immature wheat tiles: `0`
- Median unique plant tiles used: `6`
- Median harvest actions: `22`
- Median mature wait: `12 steps`
- Max mature wait: `16 steps`
- Unharvested mature tiles: `0`

## By opponent and side

| Opponent | Side | Done | W-D-L | Win rate | Median cash | Worst cash | Median delta | Worst delta |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| pass | 0 | 10/10 | 10-0-0 | 100.0% | 8670.5 | 7356 | 5670.5 | 4356 |
| pass | 1 | 10/10 | 10-0-0 | 100.0% | 8670.5 | 7356 | 5670.5 | 4356 |
| random | 0 | 10/10 | 10-0-0 | 100.0% | 8742 | 7564 | 8742 | 7564 |
| random | 1 | 10/10 | 10-0-0 | 100.0% | 8611 | 7713 | 8611 | 7713 |
| starter | 0 | 10/10 | 10-0-0 | 100.0% | 8493.5 | 7937 | 4929 | 4417 |
| starter | 1 | 10/10 | 10-0-0 | 100.0% | 8493.5 | 7937 | 4929 | 4417 |

## Interpretation boundary

This is a local engineering benchmark. It verifies completion, stability,
and paired behavior against fixed built-in opponents. It does not estimate
or predict the live Kaggle skill rating.
The built-in `random` opponent can vary across reruns even with the same
environment seed. Use `pass` and `starter` for exact deterministic regression,
and use `random` only as a repeated stochastic robustness probe.
