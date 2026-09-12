"""Exact official raw-Python loader regression; explicit module.agent is insufficient."""
from pathlib import Path
import sys
import unittest

LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB/'scripts'))
from research_cycle import make, load_agent
from kaggle_environments.agent import get_last_callable

class TerminalEntrypointTests(unittest.TestCase):
    def test_loader_selects_fresh_name_for_all_file_versions(self):
        for name in ('depth1','depth2','depth3','transport'):
            path = LAB/f'experiments/track-terminal-20260912/{name}-file/main.py'
            actual = get_last_callable(path.read_text(encoding='utf-8'), path=str(path))
            self.assertEqual(actual.__name__, '_terminal_submission_entrypoint')
            self.assertEqual(actual.__globals__['TERMINAL_MODE'], 'transport' if name=='transport' else 'planner')

    def test_old_frozen_artifact_reproduces_loader_defect(self):
        path = LAB/'experiments/track-terminal-20260912/depth2/main.py'
        actual = get_last_callable(path.read_text(encoding='utf-8'), path=str(path))
        self.assertEqual(actual.__name__, '_terminal_transport')

    def test_exact_loader_and_explicit_function_match_on_observations(self):
        env = make('kaggriculture', configuration={'seed':91101}, debug=False)
        env.reset(2)
        for name in ('depth1','depth2','depth3','transport'):
            path = LAB/f'experiments/track-terminal-20260912/{name}-file/main.py'
            actual = get_last_callable(path.read_text(encoding='utf-8'), path=str(path))
            explicit = load_agent(path).agent
            for step in (0,1,695,696,700,718):
                obs = dict(env.state[0].observation)
                obs.update(step=step,day=step//24,hour=step%24)
                self.assertEqual(actual(obs,env.configuration), explicit(obs,env.configuration))

if __name__ == '__main__':
    unittest.main()
