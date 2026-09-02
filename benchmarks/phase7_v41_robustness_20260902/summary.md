# Benchmark Summary: phase7_v41_robustness

- Generated: `2026-09-02T17:40:19.530692+00:00`
- Agent: `main.py`
- SHA256: `a775325b2ebcfb4217773ede5bb223210c0596e625e4b2a14d3ed5a88c27888a`
- Python: `3.13.12`
- kaggle-environments: `1.32.7`
- Seeds: `[20261001, 20261002, 20261003, 20261004, 20261005, 20261006, 20261007, 20261008, 20261009, 20261010, 20261011, 20261012, 20261013, 20261014, 20261015, 20261016, 20261017, 20261018, 20261019, 20261020]`
- Opponents: `['pass', 'random', 'starter', 'file:baselines/v0_main.py', 'file:experiments/hands/hand1_6near_main.py']`
- Sides: `[0, 1]`

## Gate

**PASS**

- Completed: `200/200`
- Shape-invalid actions: `0`
- Wrapper exceptions: `0`
- Agent internal exceptions: `0`
- Runner errors: `0`
- Plant-to-weed transitions: `0`
- Unit tile-action conflicts: `0`
- Funding shortfall orders: `0`
- Hire orders: `5800`
- Hand non-PASS actions: `59600`
- Slowest agent call: `32.332 ms`

## Overall

- Wins / draws / losses: `180 / 16 / 4`
- Win rate: `90.0%`
- Median cash: `8089`
- Worst cash: `6246`
- Best cash: `9001`
- Median cash delta: `4389`
- Worst cash delta: `-9`
- Median realized sale revenue: `5548`
- Median realized average sale price: `33.024`
- Median revenue per land-day: `33.968`
- Median revenue per non-PASS unit action: `7.96`
- Median / max peak shed items: `24 / 96`
- Worst minimum cash: `2835`

## End state

- Median / max unused seeds: `0 / 0`
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
| pass | 0 | 20/20 | 20-0-0 | 100.0% | 8450.5 | 7181 | 5450.5 | 4181 |
| pass | 1 | 20/20 | 20-0-0 | 100.0% | 8450.5 | 7181 | 5450.5 | 4181 |
| random | 0 | 20/20 | 20-0-0 | 100.0% | 8697.5 | 7157 | 8697.5 | 7157 |
| random | 1 | 20/20 | 20-0-0 | 100.0% | 8396.5 | 6753 | 8396.5 | 6493 |
| starter | 0 | 20/20 | 20-0-0 | 100.0% | 8070.5 | 6400 | 4333.5 | 2696 |
| starter | 1 | 20/20 | 20-0-0 | 100.0% | 8070.5 | 6400 | 4333.5 | 2696 |
| file:baselines/v0_main.py | 0 | 20/20 | 20-0-0 | 100.0% | 7888.5 | 6316 | 4056.5 | 2765 |
| file:baselines/v0_main.py | 1 | 20/20 | 20-0-0 | 100.0% | 7888.5 | 6316 | 4056.5 | 2765 |
| file:experiments/hands/hand1_6near_main.py | 0 | 20/20 | 10-8-2 | 50.0% | 7785.5 | 6246 | 4 | -9 |
| file:experiments/hands/hand1_6near_main.py | 1 | 20/20 | 10-8-2 | 50.0% | 7785.5 | 6246 | 4 | -9 |

## Interpretation boundary

This is a local engineering benchmark. It verifies completion, stability,
and paired behavior against fixed built-in opponents. It does not estimate
or predict the live Kaggle skill rating.
The built-in `random` opponent can vary across reruns even with the same
environment seed. Use `pass` and `starter` for exact deterministic regression,
and use `random` only as a repeated stochastic robustness probe.
