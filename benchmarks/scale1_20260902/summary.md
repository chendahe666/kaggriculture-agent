# Benchmark Summary: scale1-scale-selection

- Generated: `2026-09-02T16:53:19.882393+00:00`
- Agent: `experiments\scale\scale_1_main.py`
- SHA256: `74392472159a1a8ca28450581c8619db5fe69069802de1339e3ffc706bcb9dd7`
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
- Slowest agent call: `0.252 ms`

## Overall

- Wins / draws / losses: `60 / 0 / 0`
- Win rate: `100.0%`
- Median cash: `3978`
- Worst cash: `3799`
- Best cash: `4068`
- Median cash delta: `971`
- Worst cash delta: `48`

## End state

- Median / max unused seeds: `0 / 0`
- Median unsold shed items: `0`
- Median carried items: `0`
- Median remaining plant tiles: `0`
- Max immature wheat tiles: `0`
- Median unique plant tiles used: `1`
- Median harvest actions: `7`
- Median mature wait: `2 steps`
- Max mature wait: `2 steps`
- Unharvested mature tiles: `0`

## By opponent and side

| Opponent | Side | Done | W-D-L | Win rate | Median cash | Worst cash | Median delta | Worst delta |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| pass | 0 | 10/10 | 10-0-0 | 100.0% | 3971 | 3799 | 971 | 799 |
| pass | 1 | 10/10 | 10-0-0 | 100.0% | 3971 | 3799 | 971 | 799 |
| random | 0 | 10/10 | 10-0-0 | 100.0% | 3993.5 | 3892 | 3993.5 | 3892 |
| random | 1 | 10/10 | 10-0-0 | 100.0% | 3977.5 | 3919 | 3977.5 | 3781 |
| starter | 0 | 10/10 | 10-0-0 | 100.0% | 3953.5 | 3828 | 391 | 48 |
| starter | 1 | 10/10 | 10-0-0 | 100.0% | 3953.5 | 3828 | 391 | 48 |

## Interpretation boundary

This is a local engineering benchmark. It verifies completion, stability,
and paired behavior against fixed built-in opponents. It does not estimate
or predict the live Kaggle skill rating.
The built-in `random` opponent can vary across reruns even with the same
environment seed. Use `pass` and `starter` for exact deterministic regression,
and use `random` only as a repeated stochastic robustness probe.
