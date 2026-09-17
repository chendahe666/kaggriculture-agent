"""Literal extraction only; downloaded notebook cells are never executed."""
import ast
import hashlib
import json
from pathlib import Path
LAB=Path(__file__).resolve().parents[1]
ROOT=LAB/'inbox/g4-20260917/sources'
for name in ('v47','independent'):
    nb=json.loads(next((ROOT/name).glob('*.ipynb')).read_text(encoding='utf-8'))
    raw=None;expected=None
    for cell in nb['cells']:
        if cell['cell_type']!='code':continue
        source=''.join(cell['source'])
        if source.startswith('%%writefile main.py'):
            raw=source.split('\n',1)[1].encode();continue
        try:tree=ast.parse(source)
        except SyntaxError:continue
        for n in tree.body:
            if not isinstance(n,ast.Assign) or not isinstance(n.targets[0],ast.Name):continue
            if n.targets[0].id=='SOURCE_BYTES':raw=b''.join(ast.literal_eval(n.value.args[0]))
            if n.targets[0].id=='EXPECTED_MAIN_SHA256':expected=ast.literal_eval(n.value)
    assert raw is not None
    if expected:assert hashlib.sha256(raw).hexdigest()==expected
    p=ROOT/name/'main.py'
    if p.exists():assert p.read_bytes()==raw
    else:
        with p.open('xb') as f:f.write(raw)
    print(name,len(raw),hashlib.sha256(raw).hexdigest())
    print('imports',sorted({ast.unparse(n) for n in ast.walk(ast.parse(raw)) if isinstance(n,(ast.Import,ast.ImportFrom))}))
    if name=='v47':
        old=(LAB/'inbox/r2-20260916/sources/v46/extracted-main.py').read_bytes()
        print('extends exact v46',raw.startswith(old),'old_bytes',len(old))
