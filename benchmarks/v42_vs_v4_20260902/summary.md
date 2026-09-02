# Benchmark Summary: v42_vs_v4

- Generated: `2026-09-02T17:47:40.248932+00:00`
- Agent: `main.py`
- SHA256: `74fec72134bb79222543a872c37751c8bc6611e22ebd9e791b143dd5c8b43dae`
- Python: `3.13.12`
- kaggle-environments: `1.32.7`
- Seeds: `[20261001, 20261002, 20261003, 20261004, 20261005, 20261006, 20261007, 20261008, 20261009, 20261010, 20261011, 20261012, 20261013, 20261014, 20261015, 20261016, 20261017, 20261018, 20261019, 20261020]`
- Opponents: `['file:experiments/hands/hand1_6near_main.py']`
- Sides: `[0, 1]`

## Gate

**PASS**

- Completed: `40/40`
- Shape-invalid actions: `0`
- Wrapper exceptions: `0`
- Agent internal exceptions: `0`
- Runner errors: `0`
- Plant-to-weed transitions: `0`
- Unit tile-action conflicts: `0`
- Funding shortfall orders: `0`
- Hire orders: `1160`
- Hand non-PASS actions: `11920`
- Slowest agent call: `31.665 ms`

## Overall

- Wins / draws / losses: `40 / 0 / 0`
- Win rate: `100.0%`
- Median cash: `7802`
- Worst cash: `6343`
- Best cash: `8424`
- Median cash delta: `26.5`
- Worst cash delta: `10`
- Median realized sale revenue: `5261`
- Median realized average sale price: `31.316`
- Median revenue per land-day: `32.21`
- Median revenue per non-PASS unit action: `7.548`
- Median / max peak shed items: `24 / 100`
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
| file:experiments/hands/hand1_6near_main.py | 0 | 20/20 | 20-0-0 | 100.0% | 7802 | 6343 | 26.5 | 10 |
| file:experiments/hands/hand1_6near_main.py | 1 | 20/20 | 20-0-0 | 100.0% | 7802 | 6343 | 26.5 | 10 |

## Interpretation boundary

This is a local engineering benchmark. It verifies completion, stability,
and paired behavior against fixed built-in opponents. It does not estimate
or predict the live Kaggle skill rating.
The built-in `random` opponent can vary across reruns even with the same
environment seed. Use `pass` and `starter` for exact deterministic regression,
and use `random` only as a repeated stochastic robustness probe.
