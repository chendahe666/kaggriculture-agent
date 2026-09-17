"""Literal-only extraction; never executes public notebook code."""
import ast
import base64
import gzip
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]/'inbox/r3-20260917/sources'
for name in ('jaxa','pipe8','v46'):
    notebook=json.loads(next((ROOT/name).glob('*.ipynb')).read_text(encoding='utf-8'));values={}
    for cell in notebook['cells']:
        if cell['cell_type']!='code':continue
        tree=ast.parse(''.join(cell['source']))
        for node in tree.body:
            if not isinstance(node,ast.Assign) or not isinstance(node.targets[0],ast.Name):continue
            key=node.targets[0].id
            if key in ('BLOB','MAIN_SHA256','EXPECTED_SHA256','AGENT_GZ_B64','EXPECTED_MAIN_SHA256'):
                values[key]=ast.literal_eval(node.value)
            if key=='SOURCE_BYTES':values[key]=b''.join(ast.literal_eval(node.value.args[0]))
    if name=='jaxa':raw=gzip.decompress(base64.b85decode(values['BLOB']));expected=values['MAIN_SHA256']
    elif name=='pipe8':raw=gzip.decompress(base64.b64decode(values['AGENT_GZ_B64']));expected=values['EXPECTED_SHA256']
    else:raw=values['SOURCE_BYTES'];expected=values['EXPECTED_MAIN_SHA256']
    assert hashlib.sha256(raw).hexdigest()==expected
    target=ROOT/name/'main.py'
    if target.exists():assert target.read_bytes()==raw
    else:target.write_bytes(raw)
    tree=ast.parse(raw.decode('utf-8'))
    print(name,len(raw),expected)
    print('imports',sorted({ast.unparse(n) for n in ast.walk(tree) if isinstance(n,(ast.Import,ast.ImportFrom))}))
    print('dynamic calls',[ast.unparse(n.func) for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id in ('exec','eval','open','__import__')])
