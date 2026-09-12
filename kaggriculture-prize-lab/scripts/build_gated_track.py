from pathlib import Path
import hashlib,json
LAB=Path(__file__).resolve().parents[1]
root=LAB/'experiments/track-market-20260911'
source=root/'integrated/main.py'
target=root/'gated/main.py';target.parent.mkdir(parents=True,exist_ok=True)
target.write_text(source.read_text(encoding='utf-8')+'\n'+(root/'gate_overlay.py').read_text(encoding='utf-8'),encoding='utf-8')
(target.parent/'manifest.json').write_text(json.dumps({'parent_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'gate':'step>=240, 60/64 public worker-position equality, economic tile distance<=3'},indent=2),encoding='utf-8')
print(target)
