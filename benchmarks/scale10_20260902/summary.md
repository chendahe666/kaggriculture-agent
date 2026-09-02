# Benchmark Summary: scale10-scale-selection

- Generated: `2026-09-02T16:53:20.133154+00:00`
- Agent: `experiments\scale\scale_10_main.py`
- SHA256: `cae24b088aacebcbea040f0b449fe627757a9da7a98945d9a58c8971fbe4204c`
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
- Plant-to-weed transitions: `975`
- Slowest agent call: `0.488 ms`

## Overall

- Wins / draws / losses: `60 / 0 / 0`
- Win rate: `100.0%`
- Median cash: `6894.5`
- Worst cash: `5869`
- Best cash: `7812`
- Median cash delta: `4108.5`
- Worst cash delta: `2514`

## End state

- Median / max unused seeds: `2 / 7`
- Median unsold shed items: `0`
- Median carried items: `0`
- Median remaining plant tiles: `0`
- Max immature wheat tiles: `0`
- Median unique plant tiles used: `10`
- Median harvest actions: `31`
- Median mature wait: `18 steps`
- Max mature wait: `24 steps`
- Unharvested mature tiles: `11`

## By opponent and side

| Opponent | Side | Done | W-D-L | Win rate | Median cash | Worst cash | Median delta | Worst delta |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| pass | 0 | 10/10 | 10-0-0 | 100.0% | 7190 | 6545 | 4190 | 3545 |
| pass | 1 | 10/10 | 10-0-0 | 100.0% | 6671 | 6070 | 3671 | 3070 |
| random | 0 | 10/10 | 10-0-0 | 100.0% | 7123.5 | 5869 | 7123.5 | 5869 |
| random | 1 | 10/10 | 10-0-0 | 100.0% | 6864 | 5925 | 6864 | 5925 |
| starter | 0 | 10/10 | 10-0-0 | 100.0% | 7026.5 | 6160 | 3470.5 | 2533 |
| starter | 1 | 10/10 | 10-0-0 | 100.0% | 6828 | 6018 | 3237.5 | 2514 |

## Interpretation boundary

This is a local engineering benchmark. It verifies completion, stability,
and paired behavior against fixed built-in opponents. It does not estimate
or predict the live Kaggle skill rating.
The built-in `random` opponent can vary across reruns even with the same
environment seed. Use `pass` and `starter` for exact deterministic regression,
and use `random` only as a repeated stochastic robustness probe.
