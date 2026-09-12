import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from collect_elite_corpus import public_completed
from elite_economics import audit, stock
from research_cycle import engine, make
from validate_elite_dataset import validate_records


class EliteTests(unittest.TestCase):
    def test_dataset_does_not_invent_download_timestamp(self):
        row = {'episode_id': 1, 'download_completed_utc': None, 'acquisition_time_basis': 'client_clock',
               'audit_status': 'pass', 'state_mismatches': 0, 'rewards_match': True,
               'split': 'development', 'raw_replay_redistributed': False}
        self.assertIn('unknown acquisition time must be labelled a proxy', validate_records([], [row], [], []))
        row['acquisition_time_basis'] = 'filesystem_mtime_proxy_only'
        self.assertEqual(validate_records([], [row], [], []), [])

    def test_dataset_rejects_duplicate_episode(self):
        row = {'episode_id': 1, 'download_completed_utc': None, 'acquisition_time_basis': 'filesystem_mtime_proxy_only',
               'audit_status': 'pass', 'state_mismatches': 0, 'rewards_match': True,
               'split': 'development', 'raw_replay_redistributed': False}
        self.assertIn('duplicate primary key', validate_records([], [row, row], [], []))

    def test_public_selection_is_chronological_and_unfiltered_on_winner(self):
        rows = [{'id': i, 'endTime': f'2026-09-12T0{i}:00:00', 'type': kind,
                 'state': 'COMPLETED', 'winner': i % 2}
                for i, kind in ((1, 'PUBLIC'), (2, 'PUBLIC'), (3, 'VALIDATION'))]
        self.assertEqual([r['id'] for r in public_completed(rows)], [2, 1])

    def test_stock_excludes_seeds_and_includes_carried(self):
        self.assertEqual(stock({'shed': {'WHEAT': 3}, 'inventories': [{'WHEAT': 2}],
                                'seeds': {'WHEAT': 99}})['WHEAT'], 5)

    def test_audit_full_episode_and_exact_flow(self):
        original = engine._apply_unit_action
        def policy(obs):
            return {'farmer': ['PASS'], 'hands': [],
                    'market': [['BUY_PRODUCT', 'WHEAT', 2]] if obs.step == 0 else
                              [['SELL', 'WHEAT', 1]] if obs.step == 1 else []}
        env = make('kaggriculture', configuration={'seed': 91201}, debug=False)
        env.run([policy, policy])
        payload = {'steps': env.steps, 'configuration': dict(env.configuration),
                   'info': dict(env.info, EpisodeId=1, TeamNames=['a', 'b']),
                   'rewards': [s.reward for s in env.steps[-1]]}
        result = audit(payload)
        self.assertTrue(result['valid'])
        for player in result['players']:
            self.assertEqual(player['purchased_units']['BUY_PRODUCT:WHEAT'], 2)
            self.assertEqual(player['sold_units']['WHEAT'], 1)
            self.assertEqual(player['final_wheat'], 1)
            self.assertEqual(player['cash_balance_error'], 0)
            self.assertEqual(player['wheat_balance_error'], 0)
        self.assertIs(engine._apply_unit_action, original)


if __name__ == '__main__':
    unittest.main()
