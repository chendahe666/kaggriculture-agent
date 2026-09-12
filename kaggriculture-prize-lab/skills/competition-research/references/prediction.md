# Prediction competitions: choose validation before architecture

## Match deployment, not a universal split recipe

Identify the prediction timestamp, entity, target horizon and metric aggregation.
Use random splits when intended examples are plausibly exchangeable. Use group
splits for genuinely unseen entities, temporal splits for future prediction, or
combined designs when both claims matter. Purging/embargo is justified by overlapping
label windows or information availability, not by the word finance. Future prediction
for existing entities and generalization to unseen entities are different targets.

Build a feature-availability table. A post-prediction event is not rescued by dropping
its timestamp. Fit imputers, scaling, feature selection and target encoders inside
training folds, with cross-fitting for target-dependent features. Unsupervised access
to test features is a rules- and deployment-dependent transduction question; it is
not universally legal or forbidden. Never use unavailable labels.

Maintain identical splits for candidate comparisons. Fold-score standard deviation
is not automatically a standard error: overlapping training sets induce dependence.
Resample at the actual independent unit and state the estimand. Adaptive search needs
untouched confirmation or a defensible sequential protocol. Avoid precise confidence
from a handful of dependent folds.

Confirmation must compare the selected challenger with the retained competitive
control, using a matched training cutoff/retraining schedule. Do not quietly replace
that control with a weaker seasonal/null baseline or retrain only the challenger on
more data. With a tight fit budget, freeze both models for confirmation and reserve
post-selection refitting; distinguish absolute usefulness from incremental improvement.

## Diagnose before choosing capacity

Inspect labels, raw samples, duplicates, missingness, entity/time concentration,
feature distributions, score contributions and error slices. Negative controls and
tiny-set overfit expose wiring/optimization errors; they do not establish generalization.
A weak neural result alone does not prove tabular trees always win.

Compare a simple baseline, a strong low-cost model and one justified alternative
representation/capacity family. Plot train/validation curves versus data and compute.
Improving train but worsening validation requires a different intervention from
failure to fit a tiny clean dataset. Search must respect the total competition budget.

A domain classifier distinguishing train from test can localize detectable covariate
shift. Use held-out predictions and inspect influential features. High AUC does not
prove target leakage; low AUC does not exclude conditional shift. Reweighting is a
hypothesis, not an automatic cure; validate support and effective sample size.

## Ensemble because errors complement, not because models multiply

Use aligned out-of-fold predictions and inspect joint residuals or metric-specific
disagreements. Train stackers on genuinely OOF inputs; tune weights without converting
the final test to development. Account for complete inference cost and preprocessing
compatibility. Average outputs only when their meaning and scale align. Rank transforms
suit some ranking metrics but can destroy calibration required by others.

A public-LB gain accompanied by worse credible local validation is not automatically
better. Check sampling, uncertainty, leakage and distribution changes. Neither public
LB nor local CV is infallible; do not choose whichever favors the candidate.

## Minimum outputs

Availability contract; split IDs/hashes; feature/model variants; OOF outputs or
reproduction; metric and uncertainty at the correct unit; slice regressions; relevant
learning/compute curves; holdout usage; inference and license/dependency inventory.
Keep private data outside the public skill.

Sources: B4/B5/P1/P5 in sources.md. Transfer guidance is synthesis, not a universal theorem.
