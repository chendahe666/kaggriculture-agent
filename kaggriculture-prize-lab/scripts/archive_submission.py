"""Immutable local source freezes. No Kaggle uploads and no implicit Git pushes."""
import argparse
import difflib
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
ROOT = LAB / 'version-archive'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def immutable(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != raw:
            raise ValueError(f'Frozen bytes differ: {path}')
    else:
        with path.open('xb') as f:
            f.write(raw)


def save(path, obj):
    immutable(path, (json.dumps(obj, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))


def freeze(source, baseline, name, notes):
    raw, base = source.read_bytes(), baseline.read_bytes()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    target = ROOT / 'pre-submit' / f'{stamp}-{digest(raw)[:12]}'
    immutable(target / 'main.py', raw)
    immutable(target / 'baseline.py', base)
    immutable(target / 'NOTES.md', notes.read_bytes())
    save(target / 'manifest.json', {'name': name, 'pre_submit_verified_utc': now(), 'submission_id': None,
        'submitted_utc': None, 'sha256': digest(raw), 'baseline_sha256': digest(base),
        'source': str(source), 'baseline': str(baseline), 'bytes': len(raw),
        'authorization': 'Freeze only; does not authorize or perform an upload'})
    print(target)


def historical(snapshot):
    records = json.loads((LAB / 'monitoring/source-bindings.json').read_text(encoding='utf-8'))
    data = json.loads(snapshot.read_text(encoding='utf-8'))
    for row in sorted(data['submissions'], key=lambda r: r['date']):
        sid = str(row['ref'])
        folder = ROOT / 'submissions' / sid
        binding = records.get(sid)
        manifest_path = folder / 'manifest.json'
        if manifest_path.exists():
            old = json.loads(manifest_path.read_text(encoding='utf-8'))
            if old.get('sha256') and digest((folder / 'main.py').read_bytes()) != old['sha256']:
                raise ValueError(f'Archive corruption: {sid}')
            continue
        manifest = {'submission_id': row['ref'], 'submitted_utc': row['date'], 'archived_utc': now(),
            'pre_submit_verified_utc': None, 'code_created_utc': None, 'archive_kind': 'historical_backfill',
            'initial_archive_score_observation': {'score': row['publicScore'], 'observed_utc': data['started_utc']},
            'server_status_at_archive': row['status'], 'description': row['description'],
            'snapshot': snapshot.name, 'sha256': None, 'binding_status': 'metadata_only_source_unresolved',
            'notes': 'Server timestamps are distinct from present archival time; missing times are not reconstructed.'}
        if binding:
            raw = (LAB / binding['source']).read_bytes()
            if digest(raw) != binding['sha256'] or len(raw) != row['totalBytes']:
                raise ValueError(f'Source/receipt mismatch: {sid}')
            manifest.update(binding)
            manifest.update({'bytes': len(raw), 'binding_status': 'local_historical_evidence_and_server_byte_count_not_server_download_hash'})
            immutable(folder / 'main.py', raw)
            if binding.get('baseline'):
                base = (LAB / binding['baseline']).read_bytes()
                if digest(base) != binding['baseline_sha256']:
                    raise ValueError(f'Baseline mismatch: {sid}')
                immutable(ROOT / 'baselines' / digest(base) / 'main.py', base)
                patch = ''.join(difflib.unified_diff(base.decode('utf-8-sig').splitlines(True), raw.decode('utf-8-sig').splitlines(True), fromfile='baseline/main.py', tofile='candidate/main.py'))
                immutable(folder / 'changes.patch', patch.encode('utf-8'))
            for rel in binding.get('reports', []):
                immutable(folder / 'reports' / Path(rel).name, (LAB / rel).read_bytes())
            for rel in binding.get('licenses', []):
                immutable(folder / 'licenses' / Path(rel).name, (LAB / rel).read_bytes())
            if binding.get('attempt'):
                attempt = json.loads((LAB / binding['attempt']).read_text(encoding='utf-8'))
                if attempt['sha256'] != binding['sha256']:
                    raise ValueError('Attempt hash mismatch')
                manifest['pre_submit_verified_utc'] = attempt['started_utc']
                manifest['pre_submit_time_basis'] = 'persisted hash-checked upload attempt; not code creation time'
        save(manifest_path, manifest)
        print(f'{sid}: {manifest["binding_status"]}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command', required=True)
    f = sub.add_parser('freeze')
    for key in ('source', 'baseline', 'notes'):
        f.add_argument('--' + key, type=Path, required=True)
    f.add_argument('--name', required=True)
    h = sub.add_parser('historical')
    h.add_argument('--snapshot', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'freeze':
        freeze(args.source, args.baseline, args.name, args.notes)
    else:
        historical(args.snapshot)
