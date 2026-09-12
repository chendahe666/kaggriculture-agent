"""Pin downloaded policy files; source count is not independent family count."""
import hashlib,json
from pathlib import Path
LAB=Path(__file__).resolve().parents[1]
specs=[
 ('k320','candidate/main.py','reconstructed_mixed_route','same-lineage control','Apache-2.0','https://www.kaggle.com/code/raykkretzschmar/kaggriculture-rank-your-agent'),
 ('cok','public-baseline-v10/main.py','reconstructed_mixed_route','adaptive market control','Apache-2.0','https://github.com/COK-ZhangZiliang/Kaggriculture'),
 ('igor','public-igor-20260911/main.py','reconstructed_mixed_route','multi-route/layout fallback','license verification pending; evaluation only, do not redistribute','https://www.kaggle.com/code/flexonafft/kaggriculture-multi-route-farming-agent'),
 ('seyam','public-seyam-v21/main.py','closed_loop_expert_route','public V18/C20 expert controller plus recovery','MIT repository; Apache-2.0 embedded policy','https://github.com/Seyamalam/Kaggriculture'),
 ('lonespear','public-lonespear/main.py','greedy_dynamic_lineage','dynamic mixed livestock tasks','MIT','https://github.com/lonespear/kaggriculture'),
 ('herd','public-lonespear/main_bigherd.py','greedy_dynamic_lineage','milk flooding stress variant','MIT','https://github.com/lonespear/kaggriculture'),
 ('crop','public-lonespear/main_v9.py','greedy_dynamic_lineage','older melon/goose crop-heavy stress','MIT','https://github.com/lonespear/kaggriculture'),
]
rows=[]
for name,path,family,behavior,license,url in specs:
    file=LAB/path
    rows.append({'name':name,'path':path,'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),
                 'family':family,'behavior':behavior,'license':license,'source':url,'captured_date':'2026-09-11'})
(LAB/'opponent-pool.json').write_text(json.dumps({'version':'pool-20260911-v1','classification':'conservative manual lineage groups; provisional, not inferred from number of files','opponents':rows},indent=2),encoding='utf-8')
print('Registered',len(rows),'policies,',len({r['family'] for r in rows}),'conservative lineages')
