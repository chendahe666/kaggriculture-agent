"""Mechanical isolated builds, retaining original attribution and byte hash."""
from pathlib import Path
import hashlib
import json

LAB = Path(__file__).resolve().parents[1]
ROOT = LAB/'experiments/track-feed-20260912'


def main():
    source = (LAB/'public-baseline-v10/main.py').read_bytes()
    assert hashlib.sha256(source).hexdigest() == '1c7335f698692f1c7bac34913a9ededc0f736dfb2b51346a4fa59098ab471d01'
    overlay = (ROOT/'overlay.py').read_text(encoding='utf-8')
    manifest = {'baseline_sha256': hashlib.sha256(source).hexdigest(), 'variants': {}}
    for name, mode, horizon in [('netting', 'netting', 6), ('reserve6', 'reserve', 6), ('jit1', 'reserve', 1)]:
        path = ROOT/name/'main.py'
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = source + f'\nFEED_MODE={mode!r}\nFEED_HORIZON={horizon}\n'.encode() + overlay.encode('utf-8')
        if path.exists() and path.read_bytes() != payload:
            raise SystemExit('Frozen candidate exists with different bytes; use a new version')
        path.write_bytes(payload)
        manifest['variants'][name] = {'sha256': hashlib.sha256(payload).hexdigest(), 'mode': mode, 'horizon': horizon}
    availability = (ROOT/'availability_overlay.py').read_bytes()
    for name, busy, day in [('jit-busy', True, False), ('jit-return', False, True), ('jit-aware', True, True)]:
        path = ROOT/name/'main.py'
        path.parent.mkdir(parents=True, exist_ok=True)
        settings = f"\nFEED_MODE='reserve'\nFEED_HORIZON=1\nFEED_BUSY={busy}\nFEED_DAY_RETURN={day}\n"
        payload = source + settings.encode() + overlay.encode('utf-8') + b'\n' + availability
        if path.exists() and path.read_bytes() != payload:
            raise SystemExit('Frozen candidate exists with different bytes; use a new version')
        path.write_bytes(payload)
        manifest['variants'][name] = {'sha256': hashlib.sha256(payload).hexdigest(), 'busy': busy, 'day_return': day}
    path = ROOT/'idle-delivery/main.py'
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = source + b'\n' + (ROOT/'delivery_overlay.py').read_bytes()
    if path.exists() and path.read_bytes() != payload:
        raise SystemExit('Frozen delivery candidate differs; use a new version')
    path.write_bytes(payload)
    manifest['variants']['idle-delivery'] = {'sha256': hashlib.sha256(payload).hexdigest(), 'mode': 'otherwise-idle premium logistics', 'occupancy_trigger': 80}
    path = ROOT/'delivery-early/main.py'
    path.parent.mkdir(parents=True, exist_ok=True)
    delivery = (ROOT/'delivery_overlay.py').read_text(encoding='utf-8')
    assert delivery.count('if total < 80:') == 1
    payload = source + b'\n' + delivery.replace('if total < 80:', 'if total < 0:').encode('utf-8')
    if path.exists() and path.read_bytes() != payload:
        raise SystemExit('Frozen early delivery differs')
    path.write_bytes(payload)
    manifest['variants']['delivery-early'] = {'sha256': hashlib.sha256(payload).hexdigest(), 'occupancy_trigger': 0}
    path = ROOT/'feed-guard/main.py'
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = source + b"\nFEED_MODE='reserve'\nFEED_HORIZON=1\nFEED_BUSY=True\nFEED_DAY_RETURN=True\n" + overlay.encode('utf-8') + b'\n' + availability + b'\n' + (ROOT/'guard_overlay.py').read_bytes()
    if path.exists() and path.read_bytes() != payload:
        raise SystemExit('Frozen guard differs')
    path.write_bytes(payload)
    manifest['variants']['feed-guard'] = {'sha256': hashlib.sha256(payload).hexdigest(), 'mode': 'append imminent deficit only; preserve original orders'}
    (ROOT/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(manifest))


if __name__ == '__main__':
    main()
