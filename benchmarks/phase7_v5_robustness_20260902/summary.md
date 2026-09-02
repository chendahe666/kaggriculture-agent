# Benchmark Summary: phase7_v5_robustness

- Generated: `2026-09-02T17:34:22.884805+00:00`
- Agent: `main.py`
- SHA256: `66a7f783db07a0f9122ee732a4a574487f9240ab64255c4212d322d9f4c4cd6d`
- Python: `3.13.12`
- kaggle-environments: `1.32.7`
- Seeds: `[20261001, 20261002, 20261003, 20261004, 20261005, 20261006, 20261007, 20261008, 20261009, 20261010, 20261011, 20261012, 20261013, 20261014, 20261015, 20261016, 20261017, 20261018, 20261019, 20261020]`
- Opponents: `['pass', 'random', 'starter', 'file:baselines/v0_main.py', 'file:experiments/hands/hand1_6near_main.py']`
- Sides: `[0, 1]`

## Gate

**FAIL**

- Completed: `200/200`
- Shape-invalid actions: `0`
- Wrapper exceptions: `0`
- Agent internal exceptions: `0`
- Runner errors: `0`
- Plant-to-weed transitions: `2`
- Unit tile-action conflicts: `0`
- Funding shortfall orders: `0`
- Hire orders: `5800`
- Hand non-PASS actions: `60979`
- Slowest agent call: `22.892 ms`

## Overall

- Wins / draws / losses: `170 / 0 / 30`
- Win rate: `85.0%`
- Median cash: `8480`
- Worst cash: `6770`
- Best cash: `13245`
- Median cash delta: `5339`
- Worst cash delta: `-501`
- Median realized sale revenue: `6138`
- Median realized average sale price: `37.096`
- Median revenue per land-day: `38.199`
- Median revenue per non-PASS unit action: `8.813`
- Median / max peak shed items: `24 / 34`
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
- Max mature wait: `18 steps`
- Unharvested mature tiles: `0`

## By opponent and side

| Opponent | Side | Done | W-D-L | Win rate | Median cash | Worst cash | Median delta | Worst delta |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| pass | 0 | 20/20 | 20-0-0 | 100.0% | 8537 | 7086 | 5537 | 4086 |
| pass | 1 | 20/20 | 20-0-0 | 100.0% | 8537 | 7086 | 5537 | 4086 |
| random | 0 | 20/20 | 20-0-0 | 100.0% | 8728.5 | 7663 | 8728.5 | 7663 |
| random | 1 | 20/20 | 20-0-0 | 100.0% | 8528.5 | 7336 | 8528.5 | 7336 |
| starter | 0 | 20/20 | 20-0-0 | 100.0% | 8659 | 7346 | 5190.5 | 3978 |
| starter | 1 | 20/20 | 20-0-0 | 100.0% | 8659 | 7346 | 5190.5 | 3978 |
| file:baselines/v0_main.py | 0 | 20/20 | 20-0-0 | 100.0% | 8591 | 7207 | 4622 | 3431 |
| file:baselines/v0_main.py | 1 | 20/20 | 20-0-0 | 100.0% | 8591 | 7207 | 4622 | 3431 |
| file:experiments/hands/hand1_6near_main.py | 0 | 20/20 | 5-0-15 | 25.0% | 7928 | 6770 | -174 | -501 |
| file:experiments/hands/hand1_6near_main.py | 1 | 20/20 | 5-0-15 | 25.0% | 7928 | 6770 | -174 | -501 |

## Interpretation boundary

This is a local engineering benchmark. It verifies completion, stability,
and paired behavior against fixed built-in opponents. It does not estimate
or predict the live Kaggle skill rating.
The built-in `random` opponent can vary across reruns even with the same
environment seed. Use `pass` and `starter` for exact deterministic regression,
and use `random` only as a repeated stochastic robustness probe.
