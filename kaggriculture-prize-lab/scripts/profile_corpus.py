"""Observed strategy profiles; orders are requests, not actual production."""
import json
from pathlib import Path
from collections import Counter
from analyze_online_replays import player_snapshot,action_summary,similarity
LAB=Path(__file__).resolve().parents[1]
manifest=json.loads((LAB/'results/public-corpus-20260911.json').read_text(encoding='utf-8'))
seen=set();records=[]
for metadata in manifest['matches']:
    if metadata['episode_id'] in seen:continue
    seen.add(metadata['episode_id'])
    replay=json.loads((LAB/metadata['path']).read_text(encoding='utf-8'))
    profiles=[]
    for seat in (0,1):
        profiles.append({'name':replay['info']['TeamNames'][seat], 'seat':seat,
                         'reward':replay['rewards'][seat],
                         'snapshots':{str(t):player_snapshot(replay['steps'][t],seat) for t in (71,167,359,551,719)},
                         'actions':action_summary(replay['steps'],seat)})
    records.append({'episode_id':metadata['episode_id'],'source':metadata['source'],
                    'shops':replay['steps'][-1][0]['observation']['town']['unlocked_shops'],
                    'similarity':similarity(replay['steps']),'players':profiles})
(LAB/'results/current-strategy-profiles.json').write_text(json.dumps(records,indent=2,ensure_ascii=False),encoding='utf-8')
for row in records:
    if row['source']!='top5_public':continue
    print('episode',row['episode_id'],'worker_similarity',row['similarity']['worker_action_fraction'])
    for player in row['players']:
        farm=player['snapshots']['551']
        print(json.dumps({'name':player['name'],'money':player['reward'],'day22_assets':farm['tiles'],
                          'hands':farm['hands'],'quadrants':len(farm['quadrants']),
                          'work_requests':player['actions']['worker_actions']},ensure_ascii=False))
