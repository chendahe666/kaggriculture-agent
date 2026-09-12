"""Mechanical isolated track builds, retaining upstream notices and hashes."""
from pathlib import Path
import hashlib,json
LAB=Path(__file__).resolve().parents[1]
root=LAB/'experiments/track-market-20260911'
source=(LAB/'public-baseline-v10/main.py').read_text(encoding='utf-8')
overlay=(root/'overlay.py').read_text(encoding='utf-8')
variants={'rank':(False,True,False),'sweep':(True,False,False),
          'sweep-rank':(True,True,False),'integrated':(True,True,True)}
manifest={'baseline_sha256':hashlib.sha256((LAB/'public-baseline-v10/main.py').read_bytes()).hexdigest(),'variants':{}}
for name,(sweep,rank,project) in variants.items():
    settings=f'\nTRACK_SWEEP={sweep}\nTRACK_RANK={rank}\nTRACK_PROJECT_OBSERVER={project}\nTRACK_PRICE_FLOOR=0.35\n'
    path=root/name/'main.py'
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(source+settings+overlay,encoding='utf-8')
    manifest['variants'][name]={'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'sweep':sweep,'rank':rank,'project_observer':project}
(root/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps(manifest))
