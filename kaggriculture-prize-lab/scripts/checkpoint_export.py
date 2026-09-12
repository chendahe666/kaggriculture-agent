"""Byte-preserving, allowlisted export; never git-add, commit, delete or push."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

LAB = Path(__file__).resolve().parents[1]
EXCLUDED = {'.git', '__pycache__', '.pytest_cache', '.local-tmp', 'dist', 'inbox', 'online-replays'}
TREES = ('candidate', 'experiments', 'official', 'results', 'scripts', 'submissions', 'tests', 'reports', 'licenses', 'datasets')


def release_safe(path):
    rel = path.relative_to(LAB).as_posix()
    # Intermediate audits contain private-inventory snapshots; publish only
    # curated economic tables, not these replay-level reconstruction artifacts.
    return not rel.startswith(('results/elite-20260912/audits/', 'results/elite-20260912/own-audits/'))
PUBLIC = {
    'public-baseline-v10': ('main.py', 'LICENSE', 'THIRD_PARTY_NOTICES.md'),
    'public-seyam-v21': ('main.py', 'LICENSE', 'THIRD_PARTY_NOTICES.md'),
    'public-lonespear': ('main.py', 'main_bigherd.py', 'main_v9.py', 'LICENSE'),
}


def selected_files():
    paths = [p for p in LAB.iterdir() if p.is_file() and p.suffix in ('.md', '.json')]
    paths += [LAB / '.gitattributes', LAB / '.gitignore']
    for folder in TREES:
        root = LAB / folder
        if root.exists():
            paths.extend(p for p in root.rglob('*') if p.is_file()
                         and not any(part in EXCLUDED for part in p.relative_to(LAB).parts)
                         and release_safe(p)
                         and p.suffix in ('.py', '.md', '.json', '.jsonl', '.txt'))
    for folder, files in PUBLIC.items():
        paths.extend(LAB / folder / name for name in files)
    return sorted(set(paths))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Verify existing export without writing')
    args = parser.parse_args()
    repo = LAB.parent / 'kaggriculture-agent'
    if not (repo / '.git').exists():
        raise SystemExit('Expected sibling Git repository; run from original research workspace.')
    remote = subprocess.check_output(['git', '-C', str(repo), 'remote', 'get-url', 'origin'], text=True).strip()
    if remote != 'https://github.com/chendahe666/kaggriculture-agent.git':
        raise SystemExit('Unexpected destination remote; inspect before exporting.')
    target = repo / LAB.name
    dirty = subprocess.check_output(['git', '-C', str(repo), 'status', '--porcelain',
                                     '--untracked-files=no', '--', LAB.name], text=True)
    if dirty.strip() and not args.check:
        raise SystemExit('Tracked archive edits are present; inspect and commit them before exporting.')
    if target.is_symlink() or (target.exists() and target.resolve().parent != repo.resolve()):
        raise SystemExit('Destination must remain directly inside the approved repository.')
    records = []
    for source in selected_files():
        rel = source.relative_to(LAB)
        destination = target / rel
        if not source.is_file() or source.is_symlink():
            raise SystemExit(f'Missing or symlink source: {rel}')
        if not destination.resolve().is_relative_to(target.resolve()):
            raise SystemExit(f'Destination escaped archive: {rel}')
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        if not args.check:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        if not destination.is_file() or hashlib.sha256(destination.read_bytes()).hexdigest() != digest:
            raise SystemExit(f'Export mismatch: {rel}')
        records.append({'path': rel.as_posix(), 'sha256': digest, 'bytes': source.stat().st_size})
    manifest = target / 'archive-manifest.json'
    payload = {'format': 1, 'files': records, 'excluded': ['raw replays', 'elite intermediate private-inventory audit snapshots', 'credentials', 'Igor source (license unverified)', 'nested Git metadata', 'binary archives']}
    if args.check:
        if json.loads(manifest.read_text(encoding='utf-8')) != payload:
            raise SystemExit('Archive manifest differs from the selected source files.')
    else:
        manifest.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'{"Verified" if args.check else "Exported"} {len(records)} byte-identical files; no Git operation performed.')


if __name__ == '__main__':
    main()
