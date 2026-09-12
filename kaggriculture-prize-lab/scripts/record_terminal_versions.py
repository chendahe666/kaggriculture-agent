"""Generate the initial P2a per-artifact reports from frozen empirical results."""
import json
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]

def main():
    summary = json.loads((LAB/'results/terminal-20260912/development-summary.json').read_text(encoding='utf-8'))
    manifest = json.loads((LAB/'experiments/track-terminal-20260912/manifest-file-v2.json').read_text(encoding='utf-8'))
    root = LAB/'reports/versions'
    root.mkdir(exist_ok=True)
    for name in ('depth1','depth2','depth3','transport'):
        r = summary['variants'][name]
        text = f'''# P2a / {name}

Parent: COK V10 `1c7335f698692f1c7bac34913a9ededc0f736dfb2b51346a4fa59098ab471d01`.
Candidate: `experiments/track-terminal-20260912/{name}/main.py`.
SHA256: `{manifest['variants'][name]['sha256']}`.

Hypothesis: state-based last-day work/transport/liquidation can recover reachable value. Method: {'preserve remaining production and directly return finished workers' if name=='transport' else 'bounded task-chain beam, depth '+name[-1]+', with joint claims and safe deposits'}. Shared resources: unit actions, cargo/shed capacity, sale slots and shared prices. No neural training or online LLM.

Evaluation: 1.32.7, full720 states, four named responsive families, development seeds91101/91102 both seats, explicit module.agent. Actual {r['games']} candidate games matched to the same16 controls. Baseline {r['baseline_points']}/16 points; candidate {r['candidate_points']}/16; mean margin gain {r['mean_margin_gain']}; outcome flips +{r['positive_outcome_flips']}/-{r['negative_outcome_flips']}. All clean {r['all_clean']}; max observed call {r['max_call_ms']}ms. Not an independent holdout or rating forecast.

Decision: REJECT AS SUBMISSION ARTIFACT. Official loader selects the last newly inserted helper rather than the redefined agent. Explicit function experiment is algorithmic evidence only. Retain the failure and use separately hashed {name}-file revision for any subsequent file-based work. No baseline replacement or Kaggle submission.

Full diagnosis and methodological limits: [P2a report](../p2a-20260912-report.md). Raw paired rows: results/terminal-20260912/development. Git version timestamp is actual checkpoint time, not a fabricated earlier experiment time.
'''
        path = root/f'P2a-{name}.md'
        if path.exists() and path.read_text(encoding='utf-8') != text:
            raise ValueError(f'Frozen initial report differs: {path}')
        path.write_text(text, encoding='utf-8')
        text2 = f'''# P2a / {name}-file — entrypoint repair

Candidate SHA256: `{manifest['variants'][name+'-file']['sha256']}`.
Parent algorithm: `{name}` / `{manifest['variants'][name]['sha256']}`.

Change: append a uniquely named `_terminal_submission_entrypoint(obs, config=None)` after all helpers. This fixes the official loader dictionary-insertion-order issue; no task/market policy change. The original algorithmic results belong to their original hashes, not this file.

Validation at initial checkpoint: 3 official-loader regression tests pass, including four revision names, failure reproduction on old artifact, and loader/explicit-function action parity on selected observations. Full720-state tests are tracked separately in the P2 result index, not asserted complete here.

Decision: RESEARCH ONLY / NOT PROMOTED. No release gate passed or Kaggle submission. Further paired testing and whole-track review are required. [Details](../p2a-20260912-report.md).
'''
        path2 = root/f'P2a-{name}-file.md'
        if path2.exists() and path2.read_text(encoding='utf-8') != text2:
            raise ValueError('Frozen initial entrypoint report differs')
        path2.write_text(text2, encoding='utf-8')
    print('Recorded eight artifact-specific P2a reports; old artifacts explicitly non-submittable.')

if __name__ == '__main__':
    main()
