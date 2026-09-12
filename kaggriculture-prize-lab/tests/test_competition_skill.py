"""Bookkeeping regressions only; these tests do not measure contest performance."""
import copy
import importlib.util
import json
from pathlib import Path
import re
import unittest

SKILL = Path(__file__).resolve().parents[1] / 'skills' / 'competition-research'
spec = importlib.util.spec_from_file_location('competition_lesson_validator', SKILL / 'scripts' / 'validate_lessons.py')
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


class CompetitionSkillTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((SKILL / 'lessons.json').read_text(encoding='utf-8'))

    def test_initial_store_is_valid_and_not_empirically_promoted(self):
        self.assertEqual(validator.validate(self.data), [])
        self.assertTrue(all(x['status'] in {'literature_guidance', 'hypothesis'} for x in self.data['lessons']))

    def test_duplicate_id_rejected(self):
        self.data['lessons'].append(copy.deepcopy(self.data['lessons'][0]))
        self.assertTrue(any('duplicate' in e for e in validator.validate(self.data)))

    def test_scope_required(self):
        self.data['lessons'][0]['scope'] = ''
        self.assertTrue(any('scope' in e for e in validator.validate(self.data)))

    def test_empirical_status_requires_evidence(self):
        self.data['lessons'][0]['status'] = 'local_evidence'
        self.assertTrue(any('empirical' in e for e in validator.validate(self.data)))

    def test_cross_context_cannot_reuse_same_context(self):
        item = self.data['lessons'][0]
        item.update(status='cross_context_evidence', evidence=['experiment-A'], validations=[
            {'context': 'same-game', 'independent': True, 'artifact': 'A'},
            {'context': 'same-game', 'independent': True, 'artifact': 'B'},
        ])
        self.assertTrue(any('two named' in e for e in validator.validate(self.data)))

    def test_retirement_requires_reason(self):
        self.data['lessons'][0]['status'] = 'retired'
        self.assertTrue(any('retirement' in e for e in validator.validate(self.data)))

    def test_all_main_relative_links_resolve_and_catalog_has_ten_sources(self):
        content = (SKILL / 'SKILL.md').read_text(encoding='utf-8')
        for link in re.findall(r'\]\(([^)]+)\)', content):
            self.assertTrue((SKILL / link).is_file(), link)
        catalog = (SKILL / 'references' / 'sources.md').read_text(encoding='utf-8')
        self.assertEqual(re.findall(r'^### (B[1-5]|P[1-5]) —', catalog, re.M),
                         [f'B{i}' for i in range(1, 6)] + [f'P{i}' for i in range(1, 6)])


if __name__ == '__main__':
    unittest.main()
