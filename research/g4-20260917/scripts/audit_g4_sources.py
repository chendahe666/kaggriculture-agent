"""Static scan including embedded source literals; never executes candidate code."""
import ast
import base64
import hashlib
import json
import zlib
from pathlib import Path
LAB=Path(__file__).resolve().parents[1]
rows=[];seen=set()
def scan(name,source):
    sha=hashlib.sha256(source.encode()).hexdigest()
    if sha in seen:return
    seen.add(sha);tree=ast.parse(source)
    imports=sorted({ast.unparse(n) for n in ast.walk(tree) if isinstance(n,(ast.Import,ast.ImportFrom))})
    dynamic=[ast.unparse(n.func) for n in ast.walk(tree) if isinstance(n,ast.Call) and ast.unparse(n.func) in ('exec','eval','open','__import__','compile')]
    suspicious=[ast.unparse(n.func) for n in ast.walk(tree) if isinstance(n,ast.Call) and any(x in ast.unparse(n.func).lower() for x in ('subprocess','socket','requests','urlopen','unlink','rmtree','system','popen','read_text','write_text','read_bytes','write_bytes'))]
    rows.append(dict(name=name,text_sha256=sha,imports=imports,dynamic_calls=dynamic,suspicious_calls=suspicious))
    for n in ast.walk(tree):
        if not isinstance(n,ast.Constant) or not isinstance(n.value,(str,bytes)) or len(n.value)<200:continue
        values=[n.value]
        for dec in (base64.b64decode,base64.b85decode):
            try:values.append(zlib.decompress(dec(n.value)))
            except Exception:pass
        for s in values:
            try:
                s=s.decode() if isinstance(s,bytes) else s
                if 'def ' not in s and 'import ' not in s:continue
                ast.parse(s)
            except (UnicodeError,SyntaxError,ValueError):continue
            scan(name+'/embedded',s)

for name in ('v47','independent'):
    scan(name,(LAB/f'inbox/g4-20260917/sources/{name}/main.py').read_text(encoding='utf-8'))
scan('medgm',(LAB/'inbox/g4-20260917/medgm/main.py').read_text(encoding='utf-8'))
target=LAB/'results/g4-20260917/source-audit.json'
target.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
for row in rows:print(json.dumps(row))
