"""Sub-round M2: public worker-history gate; separate from frozen M1 files."""
_TRACK_ENABLED_AGENT=agent
_TRACK_SIMILARITY={0:{'last':-1,'history':[]},1:{'last':-1,'history':[]}}

def agent(obs,config=None):
    seat=int(obs['player']);step=int(obs['step'])
    state=_TRACK_SIMILARITY[seat]
    if step==0 or step<state['last']:
        state={'last':-1,'history':[]};_TRACK_SIMILARITY[seat]=state
    if step!=state['last']:
        left,right=obs['farms']
        same=left['farmer']==right['farmer'] and left['hands']==right['hands']
        state['history'].append(bool(same));state['history']=state['history'][-64:]
        state['last']=step
    enabled=(step>=240 and len(state['history'])==64 and sum(state['history'])>=60
             and _v8_public_route_distance(obs)<=3)
    return _TRACK_ENABLED_AGENT(obs,config) if enabled else _TRACK_ORIGINAL_AGENT(obs,config)
