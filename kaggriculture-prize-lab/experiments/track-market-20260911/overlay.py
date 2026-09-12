"""Track M overlay for COK: public observations only; no future opponent tape.

This file is appended mechanically to the frozen Apache-2.0 source. It is not
an independent agent and is not approved for submission. Keep all attribution.
"""
_TRACK_PREMIUM = ('MELON', 'STRAWBERRY', 'MILK', 'WOOL')
_TRACK_BASE_PRICE = {'MELON':250, 'STRAWBERRY':120, 'MILK':160, 'WOOL':200}
_TRACK_PARAMS = {
    'MELON': (250,300,'log',.2,'sq',3.6),
    'STRAWBERRY': (120,100,'sqrt',.7,'linear',1.6),
    'MILK': (160,122,'sqrt',.6,'linear',1.6),
    'WOOL': (200,105,'log',.2,'sq',3.2),
}

def _track_price(item, inventory):
    base, scale, below, low, above, high = _TRACK_PARAMS[item]
    def shape(name, value):
        value=max(0,value)
        if name=='linear': return value
        if name=='sq': return value*value
        if name=='sqrt': return math.sqrt(value)
        return math.log1p(value)
    if inventory < 10000:
        value=base + low*base*shape(below,10000-inventory)/shape(below,scale)
    else:
        value=base - high*base*shape(above,inventory-10000)/shape(above,scale)
    return max(1,round(value))

def _track_revenue(item, inventory, quantity):
    revenue=0
    for _ in range(max(0,quantity)):
        price=_track_price(item, inventory)
        revenue+=price
        # Critical engine behavior: $1 sales do not increase supply.
        inventory+=int(price>1)
    return revenue,inventory

def _track_rank(action, obs):
    """Reorder only premium SELL slots; leave feed/buy/land/hire slots fixed.

    The baseline already controls its own order movement. This overlay never
    moves a new sale over a cash/feed barrier and never merges across purchases.
    Ranking uses executable after-worker stock, not requested oversell amounts.
    """
    orders=action['market']
    remaining=_v5_projected_shed(obs,action)
    inventory=obs['market']['inventory']
    ranked=[]
    for index, order in enumerate(orders):
        if len(order)<3 or order[0]!='SELL' or order[1] not in _TRACK_PREMIUM:
            continue
        item=order[1]
        quantity=min(max(0,int(order[2])),remaining.get(item,0))
        remaining[item]=remaining.get(item,0)-quantity
        now,later_inventory=_track_revenue(item,inventory[item],quantity)
        delayed,_=_track_revenue(item,later_inventory,quantity)
        ranked.append((now-delayed,-index,order))
    ranked.sort(reverse=True)
    replacements=iter(r[2] for r in ranked)
    action['market']=[next(replacements) if len(o)>=3 and o[0]=='SELL' and o[1] in _TRACK_PREMIUM else o for o in orders]
    return action

def _track_sweep(action, obs):
    """Sell replenished premium demand, capped by projected available stock.

    Premium items are never feed/seed/animal inputs. This adds no worker action,
    changes no farm layout and incurs no speculative future-sale repayment.
    The underlying route's later SELLs remain, bounded by actual stock there.
    """
    step=int(obs['step'])
    if step<120 or step>=716:
        return action
    stock=_v5_projected_shed(obs,action)
    orders=action['market']
    shops=obs['town']['unlocked_shops']
    for item in _TRACK_PREMIUM:
        demand=_meta_town_demand(step-1,shops,item)
        if demand<=0 or obs['market']['prices'][item] < _TRACK_BASE_PRICE[item]*TRACK_PRICE_FLOOR:
            continue
        requested=sum(max(0,int(o[2])) for o in orders if len(o)>=3 and o[:2]==['SELL',item])
        extra=min(demand,max(0,stock.get(item,0)-requested))
        if extra<=0:
            continue
        existing=next((o for o in orders if len(o)>=3 and o[:2]==['SELL',item]),None)
        if existing is not None:
            existing[2]+=extra
        elif len(orders)<10:
            orders.append(['SELL',item,extra])
    return action

_TRACK_ORIGINAL_AGENT=agent
_TRACK_CACHE={0:None,1:None}

def agent(obs, config=None):
    seat=int(obs['player'])
    step=int(obs['step'])
    signature=_action_cache_signature(obs)
    cached=_TRACK_CACHE[seat]
    if step>0 and cached and cached[0]==signature:
        return copy.deepcopy(cached[1])
    action=_copy_action(_TRACK_ORIGINAL_AGENT(obs,config))
    if TRACK_SWEEP:
        action=_track_sweep(action,obs)
    if TRACK_RANK:
        action=_track_rank(action,obs)
    # Observer and action cache must see the actual submitted action, not the
    # pre-overlay one. This avoids false opponent-supply attribution next turn.
    state=_META_STATE[seat]
    _meta_remember_market(obs,step,action,state)
    if TRACK_PROJECT_OBSERVER:
        state['prev_shed']=_v5_projected_shed(obs,action)
    _TRACK_CACHE[seat]=(signature,copy.deepcopy(action))
    return action
