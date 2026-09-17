"""Static source-only traversal; never executes downloaded programs."""
import ast
import base64
import zlib
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
rows=[];seen=set()
def scan(name,src):
    digest=hashlib.sha256(src.encode()).hexdigest()
    if digest in seen:return
    seen.add(digest);tree=ast.parse(src)
    imports=sorted({ast.unparse(n) for n in ast.walk(tree) if isinstance(n,(ast.Import,ast.ImportFrom))})
    calls=[ast.unparse(n)[:250] for n in ast.walk(tree) if isinstance(n,ast.Call) and ast.unparse(n.func) in ('exec','eval','open','__import__','compile')]
    row=dict(name=name,sha256=digest,bytes=len(src),imports=imports,dynamic_calls=calls)
    rows.append(row);print(json.dumps(row))
    for node in ast.walk(tree):
        if not isinstance(node,ast.Constant) or not isinstance(node.value,(str,bytes)) or len(node.value)<200:continue
        raw=node.value
        tries=[raw]
        for decode in (base64.b64decode,base64.b85decode):
            try:tries.append(zlib.decompress(decode(raw)))
            except Exception:pass
        for val in tries:
            try:
                val=val.decode() if isinstance(val,bytes) else val
                if 'def ' not in val and 'import ' not in val:continue
                ast.parse(val)
            except (UnicodeError,SyntaxError,ValueError):continue
            scan(name+'/embedded',val)

for name in ('jaxa','pipe8'):
    scan(name,(ROOT/f'inbox/r3-20260917/sources/{name}/main.py').read_text(encoding='utf-8'))
(ROOT/'results/r3-20260917/static-source-audit.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
