# Benchmark Summary: scale5-scale-selection

- Generated: `2026-09-02T16:53:19.872797+00:00`
- Agent: `experiments\scale\scale_5_main.py`
- SHA256: `51aa1e2fdf99800eed46b9966991bf6b7ff286ecee982521d0583a43c88ab607`
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
- Slowest agent call: `0.291 ms`

## Overall

- Wins / draws / losses: `60 / 0 / 0`
- Win rate: `100.0%`
- Median cash: `7461.5`
- Worst cash: `6079`
- Best cash: `8059`
- Median cash delta: `4461.5`
- Worst cash delta: `2372`

## End state

- Median / max unused seeds: `0 / 0`
- Median unsold shed items: `0`
- Median carried items: `0`
- Median remaining plant tiles: `0`
- Max immature wheat tiles: `0`
- Median unique plant tiles used: `5`
- Median harvest actions: `35`
- Median mature wait: `13 steps`
- Max mature wait: `18 steps`
- Unharvested mature tiles: `0`

## By opponent and side

| Opponent | Side | Done | W-D-L | Win rate | Median cash | Worst cash | Median delta | Worst delta |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| pass | 0 | 10/10 | 10-0-0 | 100.0% | 7441.5 | 7035 | 4441.5 | 4035 |
| pass | 1 | 10/10 | 10-0-0 | 100.0% | 7441.5 | 7035 | 4441.5 | 4035 |
| random | 0 | 10/10 | 10-0-0 | 100.0% | 7638.5 | 6079 | 7638.5 | 6079 |
| random | 1 | 10/10 | 10-0-0 | 100.0% | 7619 | 7194 | 7619 | 6974 |
| starter | 0 | 10/10 | 10-0-0 | 100.0% | 7551.5 | 6111 | 3908 | 2372 |
| starter | 1 | 10/10 | 10-0-0 | 100.0% | 7551.5 | 6111 | 3908 | 2372 |

## Interpretation boundary

This is a local engineering benchmark. It verifies completion, stability,
and paired behavior against fixed built-in opponents. It does not estimate
or predict the live Kaggle skill rating.
The built-in `random` opponent can vary across reruns even with the same
environment seed. Use `pass` and `starter` for exact deterministic regression,
and use `random` only as a repeated stochastic robustness probe.
