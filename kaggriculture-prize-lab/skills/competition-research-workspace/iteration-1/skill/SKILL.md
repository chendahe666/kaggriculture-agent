---
name: competition-research
description: "Research and improve data-competition solutions through problem formulation, validation, diverse algorithm experiments, and evidence-backed memory. Use for Kaggle-style prediction competitions, simulation/optimization contests, game-playing agents, leaderboard plateaus, opponent/replay analysis, model-versus-search decisions, or requests to grow a competition research workflow. Not for ordinary model implementation without a competition or evaluation-design question."
metadata:
  version: "0.1.0"
---

# Competition Research

Turn observations into falsifiable experiments, not a growing list of patches.
Keep a strong baseline as a **control, not a boundary on the search space**.
This skill improves research practice; it neither guarantees prizes nor trains
the assistant's underlying model weights. Follow the user's language.

## Route before acting

Read project instructions, actual current state, rules/evaluation contract, latest
results and data provenance. Historical reports are not current authorization.
Announce this skill and this round's hypothesis before experiments.

Read the appropriate references fully:

- Prediction/ranking/forecasting: [prediction.md](references/prediction.md).
- Sequential decisions, simulators or opponents: [sequential-games.md](references/sequential-games.md).
- Every research/growth round: [research-and-growth.md](references/research-and-growth.md).
- Literature selection, attribution or model claims: [sources.md](references/sources.md).
- Reusing/updating memory: inspect [lessons.json](lessons.json); its statuses are not interchangeable.

Hybrid contests need both prediction and sequential references. Do not read every
reference merely to produce a short status answer. Do not run experiments when
the user only asks for an explanation or diagnosis.

## 1. Write the actual problem contract

Capture what is known, missing and inferred:

| Question | Required distinction |
|---|---|
| Objective | Official metric/aggregation vs training loss, shaping and diagnostics |
| Generalization | New rows, entities, time windows, environments or responsive opponents |
| Available information | Feature availability at prediction/action time vs privileged offline labels |
| Decisions | Single prediction vs actions that change future observations and rewards |
| Constraints | Runtime, memory, package/network rules, permitted data, licenses and budget |
| Authority | Local research vs baseline replacement, spending, publication and submission |

Verify current official rules before relying on changing limits. Never infer that
a known simulator gives the agent access to its hidden state or future RNG.
Ask only for missing information that materially changes safe progress; give an
exact acquisition guide if the user must supply it.

## 2. Establish an evidence ladder

Keep separate: implementation correctness → intervention coverage → mechanism
effect → full-task result → generalization → online outcome. Passing one does
not establish the next. A zero-activation intervention is untested, not improved.

Check a small end-to-end case and domain invariants before expensive comparison.
For learned models, inspect real inputs/labels and tiny-set fit; for planners,
inspect action legality, transitions, deadlines and state recovery. Reconcile
measurement errors before attributing failures to algorithms.

Freeze development, selection and confirmatory roles before adaptive search.
Previously inspected holdouts become development data. Match uncertainty units
to dependence: rows are not independent when grouped; frames are not episodes;
cloned opponents are not new strategy families. Report effect sizes, regressions,
uncertainty and what the interval does **not** cover. No fabricated rating mapping.

## 3. Open a small, heterogeneous method portfolio

Select methods because they attack a diagnosed bottleneck; not because their names
sound advanced. Do not require exhausting hand-written rules before trying learning.

- Prediction: representation/feature reformulation; linear/tree/neural models;
  retrieval or pretrained models where permitted; calibrated, complementary ensembles.
- Sequential: exact/approximate planning; rolling-horizon search with terminal value;
  imitation; value/policy learning; model-based or model-free RL; coherent hybrids.
- Adversarial: responsive policy populations, historical opponents, specialist
  exploiters, empirical payoff analysis and opponent-distribution adaptation.
- LLM-assisted: offline hypothesis/code/candidate generation plus executable
  verifiers and an archive; learned teachers or distilled policies if justified.

Choose a few genuinely distinct probes under a stated total budget. Include a cheap
control, marginal compute cost and a learning/search-budget curve. If budget is
unknown, propose a capped pilot rather than authorizing paid resources. Early low-
fidelity tests must preserve what matters (late payoff, rare events, group/time
structure); check their ability to rank candidates before using them to prune.

Distinguish performance below a fixed budget from scaling potential. A more complex
method can fail through implementation, insufficient data, optimization, mismatch
or resource limits; one failed configuration does not reject its entire family.

## 4. Pre-register and run a research track

Before each round state: hypothesis, competing explanation, changed/frozen modules,
shared resources, data/opponent split, budget, metrics and falsification condition.
Preserve executable champions and candidate hashes. When modules share resources,
test A, B and A+B against the same control, with explicit arbitration and recovery.
Do not combine individually favorable local deltas as if they were additive.

Use cheap screens for search and fresh matched evaluation for confirmation. Do not
optimize a judge on a batch and claim independent validation on that batch. Guard
generated candidate code with a suitable sandbox and authorized resource boundaries;
do not execute untrusted downloaded programs merely because they promise high scores.

Only the official objective promotes a candidate, subject to correctness, resource
and agreed robustness constraints. Better diagnostics or imitation accuracy alone
do not promote. Report tradeoffs rather than secretly redefining the objective.

Accumulate a coherent track before proposing an online challenge. A literature
review or passing this skill's tests is not a strategy experiment or submission.

## 5. Report, generalize and grow

End each round with hypothesis/method, actual evaluation and results, causal limits,
coupling/regressions, decision, and the next informative experiment or real blocker.
Record failures and negative results. Separate model failure from evaluator failure.

For each proposed lesson record scope, evidence, counterexamples and a test that
could overturn it. Literature-derived guidance starts as `literature_guidance`;
project findings stay `local_evidence`; broader empirical claims require independent
validation in the claimed scope. A theory's assumptions travel with its guarantee.

Version updates in project history; test the changed skill on forward cases against
the prior/no-skill workflow. Run `scripts/validate_lessons.py` after memory edits.
Do not silently edit external personal skills, freeze every old rule forever, copy
private data into memory, or claim automatic background learning. This skill's own
growth is authorized only within the user's task and resource boundaries.

Pause when further progress needs a genuinely missing permission, representative
data, compute or official clarification; say what can still be done locally.
Do not call a local plateau proof that the competition is solved or impossible.
