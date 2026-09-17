"""Reproducible AST-based extraction; no downloaded notebook execution."""
import ast
import hashlib
import json
from pathlib import Path
LAB=Path(__file__).resolve().parents[1]
parent=LAB/'experiments/track-r3-20260917/clean/main.py'
donor=LAB/'inbox/g4-20260917/sources/v47/main.py'
raw=parent.read_bytes();assert hashlib.sha256(raw).hexdigest()=='dc3d7927e264e3823578dcb75c07ba95cf8ac94b54f607ae1a7d6284417f1885'
source=donor.read_text(encoding='utf-8');tree=ast.parse(source)
names={'_v44y_price','_v44y_params','_v44y_lockstep','_v44y_factor_margin','_v44y_reorder','_v44y_clone_gate'}
helpers='\n\n'.join(ast.get_source_segment(source,n) for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names)
assert len([n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names])==6
header='\n# G4: market helpers adapted from Ahmed Berat Ozer V47 and Seyit Kaan Gunes, Apache-2.0.\nimport itertools as _v44y_it\n_V44Y_REPORT=dict(v44y_reorder_turns=0,v44y_reorder_gain=0.0,v44y_errors=0)\n'
overlay=(LAB/'scripts/g4_overlay.py').read_text(encoding='utf-8')
for name,m,p in [('C',False,False),('M',True,False),('P',False,True),('MP',True,True)]:
    patch=header+helpers+f'\n_G4_M={m!r}\n_G4_P={p!r}\n'+overlay
    data=raw+patch.encode();path=LAB/f'experiments/track-g4-20260917/{name}/main.py'
    compile(data,str(path),'exec');path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():assert path.read_bytes()==data,'Frozen candidate cannot be overwritten'
    else:
        with path.open('xb') as f:f.write(data)
    manifest=dict(name=name,parent=str(parent.relative_to(LAB)),parent_sha256=hashlib.sha256(raw).hexdigest(),donor_sha256=hashlib.sha256(donor.read_bytes()).hexdigest(),sha256=hashlib.sha256(data).hexdigest(),patch=patch)
    mp=path.parent/'manifest.json'
    if not mp.exists():mp.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(name,manifest['sha256'])

# A public integrated challenger, archived separately from our original probes.
# Byte-identical intake preserves tested donor code and all upstream attribution.
path=LAB/'experiments/track-g4-20260917/public-v47/main.py'
path.parent.mkdir(parents=True,exist_ok=True)
data=donor.read_bytes()
if path.exists():assert path.read_bytes()==data
else:
    with path.open('xb') as f:f.write(data)
manifest=dict(name='public-v47',source='https://www.kaggle.com/code/ahmedberatozer/kaggriculture-v47-reactive-market-coordination',
    sha256=hashlib.sha256(data).hexdigest(),baseline_sha256=hashlib.sha256(raw).hexdigest(),
    license='Apache-2.0; embedded upstream notices retained',original_strategy_authorship=False,
    changes='Public same-lineage integrated upgrade versus R3; no untested G4 patches merged. Byte-identical V47 intake.',formal_promotion=False)
mp=path.parent/'manifest.json'
if not mp.exists():mp.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print('public-v47',manifest['sha256'])
