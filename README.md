# Kaggriculture Agent V0

## Goal

Minimal working Kaggriculture agent: correctness, stability, observability, and simplicity take priority over score.

## Files

- `main.py` — standalone Kaggle submission entry point exposing `agent(obs)`.
- `test_local.py` — full 720-step local episode runner against the official deterministic `starter` agent.
- `requirements.txt` — the single required top-level dependency.
- `run_report.md` — parameters and results from the final actual local run.
- `logs/episode_001.log` — first observation, compact turn decisions, next-observation outcomes, and the final episode summary.
- `KAGGRICULTURE_AGENT_DEVELOPMENT_GUIDE_ZH.md` — Chinese 60-minute onboarding, Agentic AI collaboration guide, and 3-to-7-day development roadmap.
- `AGENTS.md` — persistent repository rules for Codex and other compatible coding agents.
- `DEVELOPMENT_PLAN.md` — phased Day 1–7 execution plan with measurable exit gates.

## Setup

```bash
python -m pip install -r requirements.txt
```

On Windows, if `python` is only the Microsoft Store alias, use the installed launcher explicitly:

```powershell
py -3.13 -m pip install -r requirements.txt
```

## Local Test

```bash
python test_local.py
```

On this verified Windows setup:

```powershell
py -3.13 test_local.py
```

The runner uses seed `20260901`, validates every action's schema before passing it to the environment, and writes `logs/episode_001.log`.

## Submission

Upload `main.py` by itself. The installed official guide confirms that a standalone file is supported and requires `main.py` at the submission root with an `agent` function. `main.py` uses only the Python standard library and does not need the local test runner or logs.

## Current Strategy

The farmer stays on the initial owned tile and repeats a deterministic wheat cycle: buy one seed, plant it, water it once each game day, harvest on the verified day-four maximum-yield point, allow the end-of-day inventory transfer to the shed, and sell shed wheat. All farm hands pass (the agent never hires them). Missing or unexpected state falls back to the verified `PASS` action shape.

Submission mode is quiet by default. For compact local stdout diagnostics from `main.py`, set `KAGGRICULTURE_DEBUG=1`. Set `KAGGRICULTURE_DEBUG_VERBOSE=1` as well to include the first raw observation and exception observations.

## Known Limitations

- Uses only one of 25 initially unlocked tiles.
- Does not move, hire farm hands, unlock land, raise animals, or use fertilizer.
- Does not adapt crop choice or sale timing to dynamic prices or town demand.
- Does not model the opponent or optimize the final partially completed crop cycle.
- Its exception fallback preserves episode stability but cannot repair a fundamentally malformed environment observation.
