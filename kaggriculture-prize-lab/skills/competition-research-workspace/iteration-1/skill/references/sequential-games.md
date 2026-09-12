# Sequential and adversarial competitions

## Formulation controls the algorithm menu

Specify legal observation/history, action constraints, transition uncertainty,
information asymmetry, reward timing, horizon and opponent response. A known engine
may yield a partially observed stochastic game. Use beliefs, sampled plausible hidden
states or robust scenarios when useful; privileged simulator state is not an inference
feature. Opponents' future actions are not known.

Use accurate, cheap transitions for planning or training. Learning another world
model must justify its cost through speed, missing dynamics or generalization. Learned
policy/value models can still accelerate or extend exact-simulator search. Compare
combinations, not a false choice between all-rules and all-neural.

Rolling-horizon planning needs terminal value, constraints or longer scenarios to
account for consequences beyond the truncated horizon; otherwise profitable delayed
investments may be rejected. More search on a biased model can become more confidently
wrong. Measure performance versus simulations/depth and inference time.

Replay imitation can initialize a policy or teach value/intent, but expert-state
accuracy is not closed-loop strength. A learner visits different states. Collect
corrections there only when an executable/legal expert or verified search teacher
exists; historical tapes cannot answer new states. Unavailable teacher information
cannot enter student inputs. Hindsight labels need explicit limits and observation-
only evaluation. Do not call pseudolabeling from fixed tapes standard DAgger.

Use terminal official outcomes for selection. Dense rewards may aid optimization
but change the task; check shaping assumptions and the unshaped objective. Cost,
production and inventory are diagnostics unless they are the actual contest metric.
Budget imitation/RL/search probes separately and compare at equal deployment limits,
while reporting different development compute. Function approximation, bootstrapping
and off-policy learning can destabilize training; a reward curve alone is insufficient.

## Evaluate an ecology, not only a champion

Maintain responsive historical policies, independent source/behavior families and
specialists revealing exploitable weaknesses. Separate training, development and
reserved evaluation opponents. Renamed clones are not diversity. Document identity,
version, seat and response capability; fixed tapes are not real best-response tests.

Construct an empirical payoff matrix when practical. For this exact symmetric
two-player zero-sum example, entries are win probability minus .5:

| Row vs column | A | B | C |
|---|---:|---:|---:|
| A | 0 | .2 | -.2 |
| B | -.2 | 0 | .2 |
| C | .2 | -.2 | 0 |

Each pure policy has a weakness; uniform episode-level mixing yields centered payoff
zero against these three columns. This says nothing about unseen policies or an
estimated matrix without uncertainty. Multiplayer/general-sum games are not automatically
zero-sum. Opponent-weighted expected score and worst-family performance answer different
questions. Estimate likely matches from permitted past data; report stress results
separately. A conservative mixture need not maximize prizes under the actual distribution.
Choose risk tradeoffs before final results; never quietly replace the official metric.

Approximate best responses and population/meta-game methods can reveal weaknesses.
A successful attack witnesses vulnerability; failure of searched exploiters does not
upper-bound global exploitability. No-regret guarantees depend on information/action/
game assumptions. Regret against the opponent's realized sequence is not the outcome
if a changed policy makes that opponent adapt differently. Check errata before coding.

## Combine policies coherently

Selecting a whole policy per episode differs from averaging actions per turn. Discrete
averages may be invalid; resource commitments and layouts can make even legal mixtures
incoherent. Midgame gates need compatible states, resource arbitration and tested
recovery. Compare episode mixing, contextual selection or distillation only where
implementable. A fallback must handle changed states, not just resume an old action index.

## Minimum evaluation contract

Correctness/runtime gates; baseline/candidate against identical opponent versions and
random inputs, both seats if meaningful; official outcomes; family/seat/time slices,
uncertainty and win-to-loss regressions. Strategies may consume RNG differently, so
paired seeds need not give identical future worlds. Use episodes or seed/seat blocks,
not frames. State whether uncertainty covers seeds in a fixed pool or new families.
Test A/B/A+B shared-resource interactions, then reserve fresh confirmation. No exact
leaderboard rating claim without prospective calibration.

Sources: B1/B2/B3/P2/P4 in sources.md. Matrix and contest-transfer rules are synthesis.
