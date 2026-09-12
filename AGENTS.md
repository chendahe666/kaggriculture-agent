# AGENTS.md

## Current research override — 2026-09-11

The user authorized GitHub version records at this repository and explicitly allowed
replacing the old root code. Root main.py now tracks the unchanged COK V10 online
baseline; V4.2 is recoverable at c7bbcd6. Read kaggriculture-prize-lab/AGENTS.md and
its referenced workflow before current research. The older phase order below is
historical, not a requirement to restart V0 work. Each candidate gets an individual
commit and version report; push verified commits without rewriting history. This
GitHub authorization is not Kaggle submission authorization. Current track release
requires the newer research gates and explicit user submission consent. Do not
publish raw replays, credentials, or source with unverified redistribution rights.

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

- The user granted standing approval on 2026-09-02 for the unified evaluation suite,
  the farm-hand experiment after its prerequisite gates, and upload of final candidates
  that pass the plan's gates. This approval remains active until the user changes it.
- Do not upload a candidate that fails a gate, publish competition code elsewhere,
  change repository visibility, or expose credentials.
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
- After every Kaggle submission, create or update a durable human-side report under
  `reports/submissions/`. It must contain a validation report, an optimization report,
  and a natural-language five-minute briefing covering what changed, why it changed,
  what was actually verified, what remains uncertain, and the next recommendation.
- Report `Pending` honestly. When server validation, replay, logs, or rating arrive,
  update the same submission report instead of replacing its earlier evidence.
- Repeat this reporting protocol after every submission until the user changes it.
- A candidate that passes the current plan may be submitted under the standing approval;
  stop only when credentials, an external confirmation step, a rules question, or a
  materially broader publication requires the user.
