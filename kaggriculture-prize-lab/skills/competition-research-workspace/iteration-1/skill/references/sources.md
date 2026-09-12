# Source and access ledger — five books, five practitioner texts

Research access: 2026-09-12 UTC (2026-09-11 America/Chicago). Publication dates below
are not access dates. This ledger reports actual coverage, not claims of reading all
five books cover to cover. No book PDF, full post or third-party implementation is
redistributed. Skill guidance is original cross-source synthesis with explicit limits.
Recheck current contest/model facts independently; these historical texts are not current
product specifications. Source additions require a versioned catalog/validator update.

## Books

### B1 — Algorithms for Decision Making

Mykel J. Kochenderfer, Tim A. Wheeler, Kyle H. Wray. MIT Press, 2022.
[Author site and legal PDF](https://algorithmsbook.com/decisionmaking/);
[publisher](https://mitpress.mit.edu/9780262047012/algorithms-for-decision-making/).

Read: author-provided 700-page PDF, footer revision 2025-09-21; selected §6.6
(printed pp.121–122), §9.1–9.2 (181–183), §18.1–18.2 (355–359), with partial checks
of §9.4–9.5 and §18.3–18.4. Web's Drive viewer failed; approved anonymous read-only
access parsed the author-linked PDF in memory. No complete-book reading claim.

Role: experiment information value, bounded online planning, imitation under changed
state distributions. Limits: uncertain value estimates, biased models and inaccessible
experts matter; fixed replays cannot label arbitrary learner-visited states.

### B2 — Multiagent Systems: Algorithmic, Game-Theoretic, and Logical Foundations

Yoav Shoham, Kevin Leyton-Brown. Cambridge University Press, 2009.
[Author site](https://www.masfoundations.org/);
[authorized manuscript](https://www.masfoundations.org/download.html);
[chapter 7 errata](https://www.masfoundations.org/wiki/TWiki/bin/view.cgi/Main/LearningTeachingErrata).

Read: public Revision 1.1, ©2009/2010, 532 PDF pages, with pagination different from
the printed edition. Selected §3.4.1, §7.1 (public pp.199–205), §7.2 (206–210),
§7.5–7.6 (220–223), and chapter-7 errata. The errata page is a contributor-maintained
record, not a proof that every proposed correction is author-verified.

Role: strategic response and limits of learning guarantees. The regret benchmark
fixes realized opponent actions; it does not model every changed-policy response.
Registered sign/probability issues in public §7.5 require checking original sources
before implementation. Finite-pool performance is not global equilibrium evidence.

### B3 — Reinforcement Learning: An Introduction, Second Edition

Richard S. Sutton, Andrew G. Barto. MIT Press, 2018.
[Author edition page](http://incompleteideas.net/book/the-book-2nd.html);
[author's revised PDF](http://incompleteideas.net/book/RLbook2020.pdf);
[publisher](https://mitpress.mit.edu/9780262039246/reinforcement-learning/).

Read: formal second edition ©2018/2020, 548 PDF pages; §2.5 (32–33), §4.6 (86–87),
§8.2–8.3 (161–168), §11.3 (264–265). Anonymous read-only access parsed the authorized
PDF in memory after web-reader failure. An earlier “second edition, in progress”
Stanford-hosted draft was excluded; it is not the formal 2018 edition.

Role: separate model, value and policy updates; nonstationarity and unstable learning
combinations. These results do not authorize changing the contest's objective, nor
guarantee arbitrary replay-trained neural agents converge.

### B4 — An Introduction to Statistical Learning, with Applications in Python

Gareth James, Daniela Witten, Trevor Hastie, Robert Tibshirani, Jonathan Taylor. 2023.
[Author site](https://www.statlearning.com/);
[publisher](https://link.springer.com/book/10.1007/978-3-031-38747-0);
[official chapter-5 lab](https://islp.readthedocs.io/en/latest/labs/Ch05-resample-lab.html);
[official chapter-8 lab](https://islp.readthedocs.io/en/latest/labs/Ch08-baggboost-lab.html).

Read: author metadata, entire official resampling lab, and tree/pruning/bagging/random-
forest portions of the chapter-8 lab. Direct book PDF was not retrievable in this
session. This is **selected official companion study**, not book-chapter or whole-book
reading. The source is retained for its directly inspectable validation examples.

Role: validation variance, fold-dependent preprocessing and model comparisons.
Overlapping repeated splits do not yield independent score samples. One lab's random-
forest/bagging comparison does not rank all algorithms in every competition.

### B5 — The Kaggle Book: Data analysis and machine learning for competitive data science

Konrad Banachewicz, Luca Massaron. Packt, first edition, 2022.
[Publisher](https://www.packtpub.com/en-fr/product/the-kaggle-book-9781801817479);
[public adversarial-validation preview](https://www.packtpub.com/en-BE/product/the-kaggle-book-9781801817479/chapter/designing-good-validation-8/section/using-adversarial-validation-ch08lvl1sec43);
[official companion notebook](https://github.com/PacktPublishing/The-Kaggle-Book/blob/main/chapter_06/adversarial-validation-example.ipynb).

Read: publisher metadata, accessible preview introduction (indexed publisher text),
and the complete official adversarial-validation notebook code via public raw GitHub.
Did not execute that notebook or access the paywalled chapter. Second edition (2025)
exists; its metadata/repository TOC were checked, but its contents were not studied,
so this ledger deliberately cites the first edition. Do not represent it as the latest.

Role: investigate train/test separability before interpreting leaderboard mismatch.
Domain-classifier AUC is a diagnostic, not proof of target leakage or a guarantee
that reweighting fixes shift. Do not blindly inherit incidental notebook slicing.

## Interviews and public posts

### P1 — AXA Winners’ Interview: Learning Telematic Fingerprints From GPS Data

Kaggle Team interviews Team Driving It: Scott Hartshorn, Janto Oellrich, Andrei
Varanovich. 2015-04-20. The team placed second.
[Kaggle's migrated official blog](https://medium.com/kaggle-blog/axa-winners-interview-learning-telematic-fingerprints-from-gps-data-768ac9658d18).

Read full main interview. Role: task-specific validation and complementary information
sources. Its constructed proxy labels, ranking transform and historical compute
claims are contest-specific, not general recipes or current hardware estimates.

### P2 — The Bitter Lesson

Rich Sutton. 2019-03-13.
[Original](http://www.incompleteideas.net/IncIdeas/BitterLesson.html);
[UT Austin's two-page original print](https://www.cs.utexas.edu/~eunsol/courses/data/bitter_lesson.pdf);
[reproduction declaring permission](https://bitterlesson.ai/).

Original site timed out. Read complete university-hosted print and cross-checked the
authorized reproduction. Role: investigate methods that can exploit more computation.
This is a long-run research position, not a fixed-budget superiority theorem or a
reason to remove all domain constraints.

### P3 — AlphaEvolve: A Gemini-powered coding agent for designing advanced algorithms

AlphaEvolve team, Google DeepMind. 2025-05-14.
[Official blog](https://deepmind.google/blog/alphaevolve-a-gemini-powered-coding-agent-for-designing-advanced-algorithms/).

Read full blog main text and acknowledgements, not the linked white paper.
Role: executable evaluation and a feedback-driven candidate archive for LLM program
generation. Contest holdouts, sandboxing and anti-shortcut tests are additional
transfer requirements; the blog does not prove this project's ranking improvement.

### P4 — AlphaStar: Grandmaster level in StarCraft II using multi-agent reinforcement learning

The AlphaStar team, DeepMind. 2019-10-30.
[Official blog](https://deepmind.google/blog/alphastar-grandmaster-level-in-starcraft-ii-using-multi-agent-reinforcement-learning/).

Read complete main text and action-limit notes. Role: historical policies, specialists
and diverse learning opponents. Its compute, demonstration data and game interface
cannot be transferred wholesale. A local league is not proof of global robustness.

### P5 — A Recipe for Training Neural Networks

Andrej Karpathy. 2019-04-25.
[Author blog](https://karpathy.github.io/2019/04/25/recipe/).

Read complete main text. Role: distinguish silent implementation mistakes, fitting
failure and generalization failure. Tiny-set fit is diagnostic only. Historical
ensemble gains/model counts and 2019 capability remarks are not timeless rules.

## Selection limits

These ten works cover statistics, planning, RL, strategic interaction and practical
research, not all competition domains. FunSearch overlaps P3; January-2019 AlphaStar
was replaced by the more developed October account. Popular decision books were not
prioritized because inspectable algorithm/evaluation methods are more immediately
actionable here. This is a purpose-fit selection, not an objective top-ten ranking.
