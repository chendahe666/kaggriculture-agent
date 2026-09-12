"""Predeclared track ablations, two development seeds; never publishes/submits."""
from research_cycle import LAB,load_agent,run_game,aggregate,dump,sha
variants=['rank','sweep','sweep-rank']
opponents={'cok':LAB/'public-baseline-v10/main.py','igor':LAB/'public-igor-20260911/main.py',
           'lonespear':LAB/'public-lonespear/main.py'}
for variant in variants:
    candidate=LAB/f'experiments/track-market-20260911/{variant}/main.py'
    output=LAB/f'results/track-{variant}-screen.json'
    matches=[]
    manifest={'candidate_sha256':sha(candidate),'opponents':{k:sha(v) for k,v in opponents.items()},'split':'development_screen_91101_91102'}
    for name,path in opponents.items():
        for seed in [91101,91102]:
            for seat in (0,1):
                ours=load_agent(candidate);theirs=load_agent(path)
                players=[ours.agent,theirs.agent] if seat==0 else [theirs.agent,ours.agent]
                row=run_game(players,{'seed':seed,'episodeSteps':720})
                row.update(opponent=name,seed=seed,seat=seat,evidence='closed_loop')
                row['margin']=row['rewards'][seat]-row['rewards'][1-seat]
                matches.append(row)
                dump(output,{'manifest':manifest,'matches':matches,'summary':aggregate(matches,200)})
                print(variant,name,seed,seat,row['margin'],flush=True)
    dump(output,{'manifest':manifest,'matches':matches,'summary':aggregate(matches)})
