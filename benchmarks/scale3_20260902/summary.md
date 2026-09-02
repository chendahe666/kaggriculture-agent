# Benchmark Summary: scale3-scale-selection

- Generated: `2026-09-02T16:53:19.876105+00:00`
- Agent: `main.py`
- SHA256: `4cbd0c52d003b76ac046b3f3dfad731ec8e23c47803e745eba07230b6c55cfbb`
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
- Slowest agent call: `0.276 ms`

## Overall

- Wins / draws / losses: `60 / 0 / 0`
- Win rate: `100.0%`
- Median cash: `5883`
- Worst cash: `5200`
- Best cash: `6133`
- Median cash delta: `2839.5`
- Worst cash delta: `1410`

## End state

- Median / max unused seeds: `0 / 0`
- Median unsold shed items: `0`
- Median carried items: `0`
- Median remaining plant tiles: `0`
- Max immature wheat tiles: `0`
- Median unique plant tiles used: `3`
- Median harvest actions: `21`
- Median mature wait: `8 steps`
- Max mature wait: `10 steps`
- Unharvested mature tiles: `0`

## By opponent and side

| Opponent | Side | Done | W-D-L | Win rate | Median cash | Worst cash | Median delta | Worst delta |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| pass | 0 | 10/10 | 10-0-0 | 100.0% | 5839.5 | 5539 | 2839.5 | 2539 |
| pass | 1 | 10/10 | 10-0-0 | 100.0% | 5839.5 | 5539 | 2839.5 | 2539 |
| random | 0 | 10/10 | 10-0-0 | 100.0% | 5938 | 5200 | 5938 | 5200 |
| random | 1 | 10/10 | 10-0-0 | 100.0% | 5898.5 | 5643 | 5898.5 | 5643 |
| starter | 0 | 10/10 | 10-0-0 | 100.0% | 5886.5 | 5586 | 2304 | 1410 |
| starter | 1 | 10/10 | 10-0-0 | 100.0% | 5886.5 | 5586 | 2304 | 1410 |

## Interpretation boundary

This is a local engineering benchmark. It verifies completion, stability,
and paired behavior against fixed built-in opponents. It does not estimate
or predict the live Kaggle skill rating.
The built-in `random` opponent can vary across reruns even with the same
environment seed. Use `pass` and `starter` for exact deterministic regression,
and use `random` only as a repeated stochastic robustness probe.
