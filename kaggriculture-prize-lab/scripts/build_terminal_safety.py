"""Append reviewed interface repairs without overwriting frozen timing v1 files."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
ROOT = LAB / 'experiments/track-terminal-20260912'


def main():
    parents = json.loads((ROOT / 'manifest-timing-v1.json').read_text(encoding='utf-8'))
    overlay = (ROOT / 'safety_overlay.py').read_bytes()
    manifest = {'built_utc': datetime.now(timezone.utc).isoformat(),
                'overlay_sha256': hashlib.sha256(overlay).hexdigest(), 'variants': {}}
    for old, new in [('timing-file', 'timing-safe-file'), ('depth2-timing-file', 'depth2-timing-safe-file')]:
        original = (ROOT / old / 'main.py').read_bytes()
        assert hashlib.sha256(original).hexdigest() == parents['variants'][old]['sha256']
        payload = original + b'\n\n' + overlay
        path = ROOT / new / 'main.py'
        if path.exists() and path.read_bytes() != payload:
            raise SystemExit('Frozen version differs: ' + new)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        manifest['variants'][new] = {'parent': old, 'parent_sha256': hashlib.sha256(original).hexdigest(),
                                     'sha256': hashlib.sha256(payload).hexdigest()}
    destination = ROOT / 'manifest-timing-safety-v1.json'
    if destination.exists():
        old = json.loads(destination.read_text(encoding='utf-8'))
        assert old['variants'] == manifest['variants'] and old['overlay_sha256'] == manifest['overlay_sha256']
    else:
        destination.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(manifest))


if __name__ == '__main__':
    main()
