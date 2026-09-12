"""Summarize already-graded forward outputs; never grade by keywords or fabricate usage."""
import hashlib
import json
from pathlib import Path
import statistics

LAB = Path(__file__).resolve().parents[1]
SKILL = LAB / 'skills' / 'competition-research'
WORK = LAB / 'skills' / 'competition-research-workspace' / 'iteration-1'


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def main():
    evals = json.loads((SKILL / 'evals' / 'evals.json').read_text(encoding='utf-8'))['evals']
    runs = []
    names = {1: 'prediction-validation', 2: 'nontransitive-policies', 3: 'bounded-search-learning'}
    for case in evals:
        eval_root = WORK / f"eval-{case['id']}"
        write_json(eval_root / 'eval_metadata.json', {
            'eval_id': case['id'], 'eval_name': names[case['id']],
            'prompt': case['prompt'], 'expectations': case['expectations'],
            'skill_version': '0.1.0', 'runs_per_configuration': 1,
        })
        for config in ('with_skill', 'without_skill'):
            run_root = eval_root / config
            output = run_root / 'outputs' / 'answer.md'
            grading = json.loads((run_root / 'grading.json').read_text(encoding='utf-8'))
            items = grading['expectations']
            if [x['text'] for x in items] != case['expectations']:
                raise ValueError(f'Grader changed the frozen expectations: {run_root}')
            passed = sum(x['passed'] is True for x in items)
            summary = {'passed': passed, 'failed': len(items) - passed,
                       'total': len(items), 'pass_rate': passed / len(items)}
            if grading['summary'] != summary:
                raise ValueError(f'Inconsistent grade summary: {run_root}')
            result = dict(summary, time_seconds=None, tokens=None, errors=None,
                          output_chars=len(output.read_text(encoding='utf-8')))
            runs.append({'eval_id': case['id'], 'eval_name': names[case['id']],
                         'configuration': config, 'run_number': 1, 'result': result,
                         'expectations': items, 'output_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
                         'notes': ['Final-output grading only; full executor trace and token/timing metadata unavailable.']})
    summary = {}
    for config in ('with_skill', 'without_skill'):
        values = [x['result']['pass_rate'] for x in runs if x['configuration'] == config]
        selected = [x['result'] for x in runs if x['configuration'] == config]
        summary[config] = {'pass_rate': {'mean': statistics.mean(values), 'stddev': statistics.stdev(values)},
                           'time_seconds': None, 'tokens': None,
                           'assertions_passed': sum(x['passed'] for x in selected),
                           'assertions_total': sum(x['total'] for x in selected)}
    summary['delta'] = {'pass_rate': summary['with_skill']['pass_rate']['mean'] - summary['without_skill']['pass_rate']['mean'],
                        'time_seconds': None, 'tokens': None}
    benchmark = {
        'metadata': {'skill_name': 'competition-research', 'skill_version': '0.1.0',
                     'timestamp': '2026-09-12', 'evals_run': [1, 2, 3], 'runs_per_configuration': 1,
                     'executor': 'Codex fresh-context subagents, inherited model/effort; no model override',
                     'grader': 'Independent Codex subagent, configuration-visible, final outputs only'},
        'runs': runs, 'run_summary': summary,
        'notes': [
            'This is a small diagnostic pilot, not evidence of competition-score improvement.',
            'Stddev is across heterogeneous prompts, not repeat-run sampling uncertainty.',
            'Prompts and expectations were frozen before execution; v0.1.0 snapshot is retained.',
            'No executor token or duration data returned; null means unavailable, not zero.',
            'Eval-1 missed a confirmation-control defect despite a passing assertion; see qualitative review.',
            'Eval-3 curve assertion was graded strictly for concrete data/search levels, not time checkpoints alone.',
        ],
    }
    write_json(WORK / 'benchmark.json', benchmark)
    lines = ['# Skill diagnostic benchmark — v0.1.0', '',
             '|Case|With skill|Without skill|', '|---|---:|---:|']
    for case in evals:
        matched = [x for x in runs if x['eval_id'] == case['id']]
        a, b = [x['result'] for x in matched]
        lines.append(f"|{names[case['id']]}|{a['passed']}/{a['total']}|{b['passed']}/{b['total']}|")
    lines += ['', 'Micro totals: ' + ' vs '.join(f"{summary[c]['assertions_passed']}/{summary[c]['assertions_total']}" for c in ('with_skill', 'without_skill')), '',
              'One run per case/configuration. No significance, score-uplift or efficiency claim.',
              'See benchmark.json and each grading.json for evidence and important assertion gaps.', '']
    (WORK / 'benchmark.md').write_text('\n'.join(lines), encoding='utf-8')
    regression = WORK.parent / 'iteration-2'
    if (regression / 'prompt.md').exists():
        prompt = (regression / 'prompt.md').read_text(encoding='utf-8').split('预注册评分：')[0].split('\n\n', 1)[1].strip()
        write_json(regression / 'eval-4' / 'eval_metadata.json', {
            'eval_id': 4, 'eval_name': 'matched-control-and-scope-regression', 'prompt': prompt,
            'configurations': {'with_skill': '0.1.1', 'previous_skill': '0.1.0'},
            'reviewer': 'Primary agent, unblinded final-output inspection',
        })
    print(json.dumps({c: {'passed': summary[c]['assertions_passed'], 'total': summary[c]['assertions_total']}
                      for c in ('with_skill', 'without_skill')}))


if __name__ == '__main__':
    main()
