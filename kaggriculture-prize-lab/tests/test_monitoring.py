import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + '.py'))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


m = load('monitor_scores')
a = load('archive_submission')


class MonitoringTests(unittest.TestCase):
    def game(self):
        return dict(id=1, type='PUBLIC', state='COMPLETED', agents=[dict(submissionId=1, reward=10), dict(submissionId=2, reward=5)])

    def test_outcome(self):
        self.assertEqual(m.outcome(self.game(), 1), 'win')
        self.assertEqual(m.outcome(self.game(), 2), 'loss')

    def test_sdk_enum(self):
        row=self.game();row['type']='EPISODE_TYPE_PUBLIC'
        self.assertEqual(m.stats([row],1)['win'],1)
        del row['agents'][0]['reward']
        self.assertEqual(m.stats([row],1)['unknown_completed_public'],1)
        row['type']='EPISODE_TYPE_VALIDATION'
        self.assertEqual(m.stats([row],1)['n'],0)

    def test_pending_and_validation_excluded(self):
        for key, value in [('state', 'PENDING'), ('type', 'VALIDATION')]:
            row = self.game()
            row[key] = value
            self.assertIsNone(m.outcome(row, 1))

    def test_missing_not_zero(self):
        row = self.game()
        del row['agents'][0]['reward']
        self.assertIsNone(m.outcome(row, 1))
        self.assertEqual(m.stats([row], 1)['unknown_completed_public'], 1)
        row['agents'][0]['reward'] = 0
        self.assertEqual(m.outcome(row, 1), 'loss')

    def test_score_missing_and_boundaries(self):
        for value in [None, '', 'nan', 'inf']:
            self.assertIsNone(m.number(value))
        self.assertEqual(m.band(1200), 'middle_1200_1599')
        self.assertEqual(m.band(1600), 'high_>=1600')
        self.assertEqual(m.band(None), 'unknown')

    def test_frozen_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'main.py'
            a.immutable(p, b'one')
            a.immutable(p, b'one')
            with self.assertRaises(ValueError):
                a.immutable(p, b'two')
            self.assertEqual(p.read_bytes(), b'one')

    def test_ties_and_empty(self):
        row = self.game()
        row['agents'][1]['reward'] = 10
        self.assertEqual(m.stats([row], 1)['outcome_rate'], .5)
        self.assertIsNone(m.stats([], 1)['outcome_rate'])


if __name__ == '__main__':
    unittest.main()
