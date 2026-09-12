import copy
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from paired_release_gate import bounded_mean_betting, clopper_pearson_upper, evaluate_release


def fixture(n=90, families=5, candidate_points=1.0, baseline_points=0.0):
    seeds = list(range(92000, 92000 + n))
    p = {"split": "confirmation", "unopened_at_freeze": True, "seeds": seeds,
         "baseline_sha256": "a" * 64, "candidate_sha256": "b" * 64,
         "engine_sha256": "e" * 64,
         "opponents": {f"opp{i}": {"family": f"family{i}", "sha256": f"{i + 1:064x}"}
                       for i in range(families)}}
    rows = []
    for name, opponent in p["opponents"].items():
        for seed in seeds:
            for seat in (0, 1):
                for variant, points in (("baseline", baseline_points), ("candidate", candidate_points)):
                    own, other = (10, 0) if points == 1 else (0, 10) if points == 0 else (10, 10)
                    rows.append({"variant": variant, "family": opponent["family"], "opponent": name,
                                 "seed": seed, "seat": seat, "rewards": [own, other] if seat == 0 else [other, own],
                                 "statuses": ["DONE", "DONE"], "frames": 720, "errors": [],
                                 "max_call_ms": [2, 2], "split": "confirmation",
                                 "candidate_sha256": p[variant + "_sha256"],
                                 "opponent_sha256": opponent["sha256"], "engine_sha256": p["engine_sha256"]})
    return rows, p


def gate(rows, p, **kwargs):
    return evaluate_release(rows, p, resamples=1000, **kwargs)


class PairedReleaseGateTests(unittest.TestCase):
    def test_positive_confirmation_passes(self):
        rows, p = fixture()
        r = gate(rows, p)
        self.assertTrue(r["passed"], r)
        self.assertEqual(r["paired_games"], 900)
        self.assertEqual(r["independent_seed_blocks"], 90)
        self.assertGreater(r["primary"]["lower_bound_975"], 0)
        self.assertTrue(r["primary"]["reject_nonpositive_mean"])
        self.assertLess(r["per_family"]["family0"]["regression_probability_upper"], .05)

    def test_negative_confirmation_does_not_pass(self):
        rows, p = fixture(candidate_points=0, baseline_points=1)
        r = gate(rows, p)
        self.assertFalse(r["passed"])
        self.assertLess(r["primary"]["bootstrap_diagnostic"]["interval_95"][1], 0)
        self.assertFalse(r["primary"]["reject_nonpositive_mean"])
        self.assertEqual(r["outcome_flips"]["win_to_loss"], 900)

    def test_zero_difference_does_not_create_certainty(self):
        rows, p = fixture(candidate_points=1, baseline_points=1)
        r = gate(rows, p)
        self.assertFalse(r["passed"])
        self.assertTrue(r["primary"]["bootstrap_diagnostic"]["empirical_degenerate"])
        self.assertLess(r["primary"]["lower_bound_975"], 0)
        self.assertEqual(r["primary"]["e_value_at_zero"], 1)
        self.assertGreater(r["primary"]["bootstrap_diagnostic"]["interval_95"][1], 0)
        self.assertTrue(r["checks"]["simultaneous_family_noninferiority"])

    def test_thirty_seeds_do_not_certify_five_percent_no_regression(self):
        rows, p = fixture(n=30)
        r = gate(rows, p)
        self.assertTrue(r["checks"]["minimum_new_seeds_per_family"])
        self.assertFalse(r["checks"]["simultaneous_family_noninferiority"])
        self.assertFalse(r["passed"])

    def test_missing_pair_or_seat_is_invalid(self):
        rows, p = fixture()
        r = gate(rows[:-1], p)
        self.assertEqual(r["decision"], "INVALID")
        self.assertTrue(any("missing paired/seat" in e for e in r["errors"]))

    def test_duplicate_key_is_invalid(self):
        rows, p = fixture()
        r = gate(rows + [copy.deepcopy(rows[0])], p)
        self.assertTrue(any("duplicate row key" in e for e in r["errors"]))

    def test_insufficient_families_or_seed_count(self):
        for n, families in ((29, 5), (90, 4)):
            with self.subTest(n=n, families=families):
                rows, p = fixture(n=n, families=families)
                self.assertFalse(gate(rows, p)["passed"])

    def test_clone_family_inflation_is_invalid(self):
        rows, p = fixture()
        p["opponents"]["opp1"]["sha256"] = p["opponents"]["opp0"]["sha256"]
        for row in rows:
            if row["opponent"] == "opp1":
                row["opponent_sha256"] = p["opponents"]["opp0"]["sha256"]
        self.assertTrue(any("cloned" in e for e in gate(rows, p)["errors"]))

    def test_development_or_opened_confirmation_is_invalid(self):
        rows, p = fixture()
        rows[0]["split"] = "development"
        self.assertTrue(any("split" in e for e in gate(rows, p)["errors"]))
        rows, p = fixture()
        self.assertTrue(any("opened" in e for e in gate(rows, p, opened_seeds=[92000])["errors"]))
        p["split"] = "development"
        self.assertTrue(any("development" in e for e in gate(rows, p)["errors"]))

    def test_mixed_policy_opponent_engine_hashes_are_invalid(self):
        for key in ("candidate_sha256", "opponent_sha256", "engine_sha256"):
            with self.subTest(key=key):
                rows, p = fixture()
                rows[0][key] = "f" * 64
                self.assertTrue(gate(rows, p)["errors"])

    def test_recorded_failure_or_timeout_rejects(self):
        for field, value in (("statuses", ["ERROR", "DONE"]), ("frames", 719),
                             ("errors", ["error"]), ("max_call_ms", [1001, 1001])):
            with self.subTest(field=field):
                rows, p = fixture()
                rows[0][field] = value
                r = gate(rows, p)
                self.assertEqual(r["decision"], "REJECT")
                self.assertFalse(r["passed"])

    def test_nonfinite_rewards_are_invalid(self):
        rows, p = fixture()
        rows[0]["rewards"][0] = math.nan
        self.assertTrue(gate(rows, p)["errors"])

    def test_identical_family_seed_signals_use_synchronized_bootstrap(self):
        rows, p = fixture(n=90, baseline_points=.5)
        for row in rows:
            if row["variant"] == "candidate" and row["seed"] % 3 == 0:
                row["rewards"] = [0, 10] if row["seat"] == 0 else [10, 0]
        r = gate(rows, p)
        self.assertFalse(r["primary"]["bootstrap_diagnostic"]["empirical_degenerate"])
        self.assertEqual(r["primary"]["bootstrap_diagnostic"]["empirical_bootstrap_95"], r["per_family"]["family0"]["empirical_bootstrap_95"])

    def test_family_equal_weight_not_opponent_count(self):
        rows, p = fixture(n=90, baseline_points=.5)
        p["opponents"]["extra"] = {"family": "family0", "sha256": "d" * 64}
        extra = []
        for row in rows:
            if row["opponent"] == "opp0":
                copied = copy.deepcopy(row)
                copied.update(opponent="extra", opponent_sha256="d" * 64)
                extra.append(copied)
            if row["family"] == "family0" and row["variant"] == "candidate":
                row["rewards"] = [0, 10] if row["seat"] == 0 else [10, 0]
        for row in extra:
            if row["variant"] == "candidate":
                row["rewards"] = [0, 10] if row["seat"] == 0 else [10, 0]
        r = gate(rows + extra, p)
        self.assertAlmostEqual(r["primary"]["mean_paired_gain"], .3)

    def test_exact_binomial_endpoints_and_known_small_case(self):
        self.assertAlmostEqual(clopper_pearson_upper(0, 90, .01), 1 - .01 ** (1 / 90))
        self.assertEqual(clopper_pearson_upper(90, 90, .01), 1)
        # P(Binomial(2,p) <= 1) = 1-p**2 = alpha.
        self.assertAlmostEqual(clopper_pearson_upper(1, 2, .05), math.sqrt(.95), places=12)

    def test_sparse_positive_bootstrap_is_not_release_evidence(self):
        # This observed sample is plausible under P(D=.1)=.10, P(D=-1)=.015,
        # P(D=0)=.885, whose true macro mean is -.005. A sparse positive
        # sample without the rare negative tail must not auto-release.
        rows, p = fixture(candidate_points=.5, baseline_points=.5)
        for row in rows:
            if row["variant"] == "candidate" and row["family"] == "family0" and row["seed"] < 92010:
                row["rewards"] = [10, 0] if row["seat"] == 0 else [0, 10]
        r = gate(rows, p)
        self.assertGreater(r["primary"]["bootstrap_diagnostic"]["interval_95"][0], 0)
        self.assertTrue(r["checks"]["simultaneous_family_noninferiority"])
        self.assertFalse(r["passed"])
        self.assertLess(r["primary"]["lower_bound_975"], 0)
        self.assertLess(r["primary"]["e_value_at_zero"], 40)

    def test_betting_uses_fixed_grid_and_matches_direct_product(self):
        values = [.1] * 10 + [0] * 80
        result = bounded_mean_betting(values)
        grid = [.05, .1, .2, .4, .6, .8, .95, 1]
        expected = sum(math.prod(1 + stake * value for value in values) for stake in grid) / len(grid)
        self.assertEqual(result["lambda_grid"], grid)
        self.assertEqual(result["lambda_weights"], [.125] * 8)
        self.assertAlmostEqual(result["e_value_at_zero"], expected, places=12)
        self.assertEqual(result["alpha"], .025)

    def test_betting_exact_null_rejection_probability_small_distribution(self):
        # IID {-0.25,+0.75}, P(+0.75)=.25, has mean exactly zero.
        # Enumerate binomial counts, not simulated games or random samples.
        n, rejection_probability = 20, 0.0
        for k in range(n + 1):
            result = bounded_mean_betting([.75] * k + [-.25] * (n - k))
            if result["reject_nonpositive_mean"]:
                rejection_probability += math.comb(n, k) * .25 ** k * .75 ** (n - k)
        self.assertLessEqual(rejection_probability, .025)

    def test_betting_endpoints_and_validation(self):
        self.assertEqual(bounded_mean_betting([-1] * 90)["lower_bound_975"], -1)
        self.assertGreater(bounded_mean_betting([1] * 90)["lower_bound_975"], 0)
        for values in ([], [math.nan], [1.001], [-1.001], [True]):
            with self.subTest(values=values):
                with self.assertRaises(ValueError):
                    bounded_mean_betting(values)


if __name__ == "__main__":
    unittest.main()
