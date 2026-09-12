"""Build separate immutable A+B and B artifacts from the reviewed P2 overlays."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
ROOT = LAB / 'experiments/track-terminal-20260912'


def main():
    source = ROOT / 'depth2-file/main.py'
    parent = source.read_bytes()
    assert hashlib.sha256(parent).hexdigest() == 'c06dc267e07ce5b07e8bf5380104dc3c87efbbbcdaf72386677ba31e7bb55624'
    overlay = (ROOT / 'timing_overlay.py').read_bytes()
    manifest = {'built_utc': datetime.now(timezone.utc).isoformat(),
                'parent_sha256': hashlib.sha256(parent).hexdigest(),
                'overlay_sha256': hashlib.sha256(overlay).hexdigest(), 'variants': {}}
    for name, timing_only in [('timing-file', True), ('depth2-timing-file', False)]:
        payload = parent + f'\nTERMINAL_TIMING_ONLY={timing_only!r}\n'.encode() + overlay
        path = ROOT / name / 'main.py'
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.read_bytes() != payload:
            raise SystemExit(f'Frozen version differs: {name}; create a new revision')
        path.write_bytes(payload)
        manifest['variants'][name] = {'timing_only': timing_only,
                                      'sha256': hashlib.sha256(payload).hexdigest()}
    destination = ROOT / 'manifest-timing-v1.json'
    if destination.exists():
        previous = json.loads(destination.read_text(encoding='utf-8'))
        assert previous['variants'] == manifest['variants']
        assert previous['overlay_sha256'] == manifest['overlay_sha256']
    else:
        destination.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(manifest))


if __name__ == '__main__':
    main()
