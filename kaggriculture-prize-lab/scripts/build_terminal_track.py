"""Mechanical, immutable baseline + reviewed terminal overlay builds."""
from pathlib import Path
import hashlib
import json

LAB = Path(__file__).resolve().parents[1]
ROOT = LAB/'experiments/track-terminal-20260912'

def main():
    base = (LAB/'public-baseline-v10/main.py').read_bytes()
    assert hashlib.sha256(base).hexdigest() == '1c7335f698692f1c7bac34913a9ededc0f736dfb2b51346a4fa59098ab471d01'
    overlay = (ROOT/'planner_overlay.py').read_bytes()
    manifest = {'baseline_sha256': hashlib.sha256(base).hexdigest(), 'variants': {}}
    variants = [('depth1', 1, 'planner'), ('depth2', 2, 'planner'), ('depth3', 3, 'planner'), ('transport', 1, 'transport')]
    variants += [(name+'-file', depth, mode) for name, depth, mode in list(variants)]
    for name, depth, mode in variants:
        path = ROOT/name/'main.py'
        payload = base + f'\nTERMINAL_DEPTH={depth}\nTERMINAL_MODE={mode!r}\n'.encode() + overlay
        if name.endswith('-file'):
            # Redefining the old `agent` key does not change Python dict insertion
            # order. The official loader selects the last callable VALUE, so the
            # entrypoint must have a fresh name following all overlay helpers.
            payload += b'\n\ndef _terminal_submission_entrypoint(obs, config=None):\n    return agent(obs, config)\n'
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.read_bytes() != payload:
            raise SystemExit(f'Frozen version differs: {name}; use a new revision')
        path.write_bytes(payload)
        manifest['variants'][name] = {'depth': depth, 'mode': mode, 'sha256': hashlib.sha256(payload).hexdigest()}
    (ROOT/'manifest-file-v2.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(manifest))

if __name__ == '__main__':
    main()
