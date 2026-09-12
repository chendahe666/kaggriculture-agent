import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from validate_research_memory import LAB, MEMORY, SNAPSHOT, bounded_path, digest, validate


class ResearchMemoryTests(unittest.TestCase):
    def setUp(self):
        self.memory = json.loads(MEMORY.read_text(encoding='utf-8'))

    def test_frozen_evidence_and_metrics(self):
        result = validate(self.memory)
        snapshot = json.loads(SNAPSHOT.read_text(encoding='utf-8'))
        self.assertEqual(snapshot['memory_sha256'], digest(MEMORY))
        for key, value in result.items():
            self.assertEqual(snapshot[key], value)

    def test_false_numeric_claim_rejected(self):
        bad = copy.deepcopy(self.memory)
        bad['assertions'][0]['expected'] = 999
        with self.assertRaisesRegex(ValueError, 'Metric mismatch'):
            validate(bad)

    def test_hypothesis_cannot_become_validated_by_relabeling(self):
        bad = copy.deepcopy(self.memory)
        bad['hypotheses'][0]['status'] = 'validated'
        with self.assertRaisesRegex(ValueError, 'explicit versioned review'):
            validate(bad)

    def test_counterexample_cannot_become_strategy_rule(self):
        bad = copy.deepcopy(self.memory)
        bad['rules'][0]['prompt_use'] = 'always_buy_more'
        with self.assertRaisesRegex(ValueError, 'beyond its scope'):
            validate(bad)

    def test_dependency_cycle_rejected(self):
        bad = copy.deepcopy(self.memory)
        bad['tracks'][0]['depends_on'] = ['R']
        with self.assertRaisesRegex(ValueError, 'dependency cycle'):
            validate(bad)

    def test_evidence_cannot_escape_lab(self):
        with self.assertRaisesRegex(ValueError, 'Outside research root'):
            bounded_path(LAB, '../AGENTS.md')


if __name__ == '__main__':
    unittest.main()
