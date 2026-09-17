"""Generate app narrative from the reviewed companion report; preserve app identity."""
import json
import re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];APP=ROOT/'reports/r3-app'
data=json.loads((ROOT/'results/r3-20260917/reviewed-report.json').read_text(encoding='utf-8'))
old=json.loads((APP/'src/data.json').read_text(encoding='utf-8'))
data['id']=old['id'];data['report']['asOf']='2026-09-17'
data['buildStatus']='complete'
text=(ROOT/'reports/r3-20260917-report.md').read_text(encoding='utf-8')
parts=text.split('\n## ')[1:];sections=[]
for i,part in enumerate(parts):
    title=part.split('\n',1)[0]
    q={0:['online','confirmation','release'],1:['online','development'],2:['audits'],3:['references'],4:['development','confirmation'],5:['confirmation','release'],6:['references','release']}[i]
    chunks=re.split(r'(\n\|[^\n]*\|\n\|[-:| ]+\|\n(?:\|[^\n]*\|\n?)+)', '\n## '+part.strip()+'\n')
    blocks=[]
    for j,chunk in enumerate(chunks):
        if not chunk.strip():continue
        if chunk.lstrip().startswith('|'):
            lines=chunk.strip().splitlines();headers=[x.strip() for x in lines[0].strip('|').split('|')]
            rows=[{f'c{k}':x.strip() for k,x in enumerate(line.strip('|').split('|'))} for line in lines[2:]]
            blocks.append(dict(kind='table',id=f'r3-table-{i}-{j}',columns=[dict(field=f'c{k}',label=h) for k,h in enumerate(headers)],rows=rows))
        else:blocks.append(dict(kind='prose',id=f'r3-prose-{i}-{j}',body=chunk.strip()))
    sections.append(dict(id=f'r3-section-{i}',title=title,queryIds=q,blocks=blocks))
previews={
'https://github.com/Kaggle/kaggle-environments/tree/master/kaggle_environments/envs/kaggriculture':dict(title='Kaggle 官方引擎',summary='已核对交易锁步、工作与市场顺序、库存和现金结算；本轮下载源码与本机引擎哈希一致。',source='Kaggle',date='2026-09-17',approvedForReport=True),
'https://www.kaggle.com/code/nathanjacob/kaggriculture-pipe-8-clean-opening':dict(title='Pipe-8 clean opening',summary='公开源码取消开局小麦往返交易并清理下一步订单。本轮作为冻结的响应式对手，不将标题分数作为实测强度。',source='Nathan Jacob / Kaggle',approvedForReport=True)}
(APP/'src/content/report/narrative.json').write_text(json.dumps(dict(sections=sections,sourcePreviews=previews),ensure_ascii=False,indent=2),encoding='utf-8')
(APP/'src/data.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
