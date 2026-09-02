# AGENTS.md

## Project mission

Build a reliable, submission-safe Kaggriculture agent through evidence-driven
iterations. Correctness, reproducibility, and explainability take priority over
one lucky score.

## Submission invariants

- Keep `main.py` standalone and independent of local logs, tests, and user files.
- Do not add network calls, external API calls, credentials, or absolute local paths.
- Keep `agent(obs)` as the final top-level callable in `main.py`.
- Always return the complete action shape with `farmer`, `hands`, and `market`.
- Preserve a safe `PASS` fallback for missing, malformed, or unexpected state.
- Design normal per-turn work to remain comfortably below the one-second action limit.

## Required validation

- Use Python 3.13 on this machine.
- After changing agent behavior, run `py -3.13 -B test_local.py`.
- Verify the official environment loads the submission by file path through
  `env.run(["main.py", opponent])`; an imported-function test alone is insufficient.
- Do not report a build as successful unless a full 720-step episode finishes with
  both agents `DONE`, zero returned-shape errors, and zero uncaught exceptions.
- When a benchmark runner exists, run the frozen seed/opponent/side suite after each
  meaningful strategy change.
- Treat Kaggle server validation, episodes, replays, and logs as higher-priority
  evidence than local expectations.

## Experiment discipline

- Change one strategy hypothesis at a time.
- Freeze and identify the baseline before changing behavior.
- Compare candidates with the baseline using identical seeds, opponents, and player
  positions.
- Report per-condition results plus median, worst case, paired differences, failures,
  and runtime; do not report only the best or average score.
- Do not infer leaderboard strength from one local game against `starter`.
- Distinguish final in-game coins from the Kaggle skill rating.
- Label predicted improvements as hypotheses until replayed and measured.
- Preserve rejected experiments and explain why they were rejected.
- End each experiment with exactly one recommendation: `promote`, `hold`, or `reject`.

## Scope boundaries

- Do not submit to Kaggle, replace an active submission, publish competition code,
  change repository visibility, or expose credentials without explicit user approval.
- Do not combine multiple major strategy layers in one experiment. Multiple tiles,
  farm hands, crop selection, market timing, animals, land expansion, search, and
  reinforcement learning should be introduced and evaluated separately.
- Do not introduce reinforcement learning until deterministic scheduling, economics,
  and multi-seed evaluation are stable.
- Preserve unrelated user changes and keep a recoverable Git history.

## Work order

Follow `DEVELOPMENT_PLAN.md`. The default sequence is:

1. Measurement and paired benchmarks.
2. Endgame guard.
3. Three-to-five-tile task scheduling.
4. Scale comparison and inventory boundaries.
5. Farm-hand cost-benefit tests.
6. Crop and market experiments.
7. Robustness, final regression, and user-approved submission.

Do not skip an exit gate merely because a later feature appears more interesting.

## Project evidence

- Read `KAGGRICULTURE_AGENT_DEVELOPMENT_GUIDE_ZH.md` for the full learning guide.
- Read `run_report.md` for the verified V0 environment and run result.
- Use `logs/episode_001.log` as the primary local evidence for original V0 behavior.
- Keep durable experiment results in files rather than relying on chat history.

## Communication contract

- Explain user-facing outcomes in Chinese unless the user asks otherwise.
- Lead with the measured outcome, then show the evidence and remaining risk.
- Before implementation, state the single hypothesis and acceptance gate.
- After implementation, report the exact tests actually run and identify anything not
  tested.
- Stop for user approval before a Kaggle submission or another external publication.

