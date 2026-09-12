"""Register reviewed read-only downloads without executing their code."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

LAB = Path(__file__).resolve().parents[1]

def main():
    pool = json.loads((LAB/'opponent-pool.json').read_text(encoding='utf-8'))
    src = LAB/'inbox/opponents/deepesh-20260912.py'
    target = LAB/'public-deepesh-20260912'
    target.mkdir(exist_ok=True)
    for source, name in [(src, 'main.py'), (LAB/'inbox/opponents/deepesh-20260912-LICENSE.txt', 'LICENSE')]:
        out = target/name
        if out.exists() and out.read_bytes() != source.read_bytes():
            raise ValueError('Frozen opponent differs')
        shutil.copyfile(source, out)
    pool['version'] = 'pool-p2-20260912-v1'
    pool['opponents'].append({
        'name': 'deepesh', 'path': 'public-deepesh-20260912/main.py',
        'sha256': hashlib.sha256(src.read_bytes()).hexdigest(),
        'family': 'single_farmer_staple_greedy', 'behavior': 'one farmer WHEAT priority harvest/water/weed/plant; weak low-supply control',
        'license': 'MIT; LICENSE downloaded and retained',
        'source': 'https://github.com/deepeshumrao/kaggriculture-agent/blob/main/deliverables/kaggriculture_submission.py',
        'registered_utc': datetime.now(timezone.utc).isoformat(),
        'download_time_precision': 'file mtime proxy, exact start/end not recorded',
        'download_completed_mtime_utc': datetime.fromtimestamp(src.stat().st_mtime, timezone.utc).isoformat(),
        'safety_review': 'Full 134-line stdlib source read; no file/network/process/code-loading calls. Own farm/stock observations only.',
        'strength_limit': 'Not an elite agent. Does not establish high-rating robustness.'})
    notebook = LAB/'inbox/opponents/maverickss26-audit-20260912/kaggriculture-v1.ipynb'
    assert hashlib.sha256(notebook.read_bytes()).hexdigest() == '6b413ab926685074bc7044a1de752c2af288366771f1539eeb511558b176bd5b'
    cell = json.loads(notebook.read_text(encoding='utf-8'))['cells'][18]['source']
    text = ''.join(cell) if isinstance(cell, list) else cell
    assert text.startswith('%%writefile main.py\n')
    payload = text.split('\n',1)[1].encode('utf-8')
    assert hashlib.sha256(payload).hexdigest() == '7ae4354862f4674155b788526e442da8edcf0dbe57cee808fed9fb629e0c0fa8'
    mav = LAB/'public-maverick-20260912'
    mav.mkdir(exist_ok=True)
    if (mav/'main.py').exists() and (mav/'main.py').read_bytes()!=payload:
        raise ValueError('Frozen Maverick changed')
    (mav/'main.py').write_bytes(payload)
    shutil.copyfile(LAB/'public-baseline-v10/LICENSE', mav/'LICENSE')
    pool['opponents'].append({
        'name': 'maverick', 'path': 'public-maverick-20260912/main.py',
        'sha256': hashlib.sha256(payload).hexdigest(), 'family': 'sticky_zoned_crop_economy',
        'behavior': 'persistent jobs, zoned multi-worker melon/wheat economy, demand-sensitive planting and reserve/price-floor sales',
        'license': 'Apache-2.0 notebook v1; license text and original attribution retained',
        'source': 'https://www.kaggle.com/code/maverickss26/kaggriculture-v1',
        'source_notebook_sha256': hashlib.sha256(notebook.read_bytes()).hexdigest(),
        'provenance': 'inbox/opponents/fifth-family-source-audit-20260912.json',
        'safety_review': 'Agent auditor and root read complete 16129-char cell18; collections/math only, no network/process/file I/O or dynamic code execution.',
        'classification_limit': 'Provisional manually reviewed behavior family, not measured elite strength; legacy price formulas and no explicit final-day DROP.'})
    pool['version'] = 'pool-p2-20260912-v2'
    (LAB/'opponent-pool-p2.json').write_text(json.dumps(pool, indent=2)+'\n', encoding='utf-8')
    print('Registered P2 pool: five provisional source/behavior families; execution audit required, not yet release-ready.')

if __name__ == '__main__':
    main()
