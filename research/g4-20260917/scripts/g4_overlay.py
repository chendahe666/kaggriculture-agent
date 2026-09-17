# G4 original integration, Apache-2.0; appended to frozen R3.
# Market lockstep helpers below are extracted with notices from Ahmed Berat Ozer
# V47 / Seyit Kaan Gunes v44y (Apache-2.0). Opponent stock is a hypothesis only.
_G4_PARENT = agent
_G4_STATES = {}
_G4_REPORT = {}

def _g4_state(obs):
    player=int(obs['player']);step=int(obs['step']);st=_G4_STATES.get(player)
    if st is None or step<=st['step']:
        st={'step':-1,'pending':[], 'credit':0,'pickup':{},'sites':set()}
        _G4_STATES[player]=st
        _G4_REPORT.clear()
        _G4_REPORT.update(proposed=0,accepted=0,rejected=0,confirmed=0,partial=0,pickups=0,placements=0,extra_sales=0,market_reorders=0,errors=0)
    st['step']=step
    return st

def _g4_cash_bound(obs,action,orders):
    """Conservative prefix cash: no future sale credit; fixed-price obligations.

    This is an admission check, not escrow; actual partial executions are observed.
    Product buys use a two-player maximum requested-quantity stress quote, capped
    by the official request limit, rather than pretending observed prices stay fixed.
    """
    farm=obs['farms'][int(obs['player'])]
    cash=float(farm['money']);hires=int(farm.get('hires_today',0));land=len(farm['unlocked_quadrants'])
    params=_v44y_params(obs)
    for o in orders:
        if not o:continue
        if o[0]=='HIRE':cash-=_v219_fib(hires);hires+=1
        elif o[0]=='BUY_LAND':cash-=(1000,2000,4000)[min(2,max(0,land-1))];land+=1
        elif len(o)>=3 and o[0]=='BUY_ANIMAL':cash-=max(0,int(o[2]))*{'COW':400,'SHEEP':500,'GOOSE':300}[o[1]]
        elif len(o)>=3 and o[0]=='BUY_SEED':cash-=max(0,int(o[2]))*{'WHEAT':10,'CARROT':20,'TOMATO':50,'STRAWBERRY':100,'MELON':80}[o[1]]
        elif len(o)>=3 and o[0]=='BUY_PRODUCT':
            q=max(0,int(o[2]));inv=int(obs['market']['inventory'][o[1]])
            cash-=q*_r37_market_price(o[1],inv-q-100,params)
        if cash<100:return cash
    return cash

def _g4_resolve(obs,action,intents):
    """Single admission/arbitration path for purchase and ordering intentions."""
    out=action;claimed=set();accepted=[]
    for intent in intents:
        _G4_REPORT['proposed']+=1
        slot=intent['slot'];orders=out.get('market',[])
        if slot in claimed or not intent['precondition'] or len(orders)>10:
            _G4_REPORT['rejected']+=1;continue
        if intent['kind']=='purchase':
            if slot>=len(orders) or orders[slot]!=intent['expected']:
                _G4_REPORT['rejected']+=1;continue
            trial=[list(o) for o in orders];trial[slot]=list(intent['replacement'])
            if _g4_cash_bound(obs,out,trial)<100:
                _G4_REPORT['rejected']+=1;continue
        elif intent['kind']=='ordering':
            trial=intent['orders']
            if len(trial)!=len(orders) or sorted(map(tuple,trial))!=sorted(map(tuple,orders)):
                _G4_REPORT['rejected']+=1;continue
            # Every non-cash sale is an immutable barrier: feed, fertilizer,
            # purchases and fixed-price financing all keep their slot.
            cash_items={'MILK','WOOL','EGG','TOMATO','CARROT','STRAWBERRY','MELON'}
            if any(a!=b and (not a or a[0]!='SELL' or a[1] not in cash_items or not b or b[0]!='SELL' or b[1] not in cash_items) for a,b in zip(orders,trial)):
                _G4_REPORT['rejected']+=1;continue
        else:raise ValueError('unknown intention')
        out=dict(out,market=trial);claimed.add(slot);accepted.append(intent)
        _G4_REPORT['accepted']+=1
    return out,accepted

def _g4_herd(obs,action,st):
    farm=obs['farms'][int(obs['player'])];private=obs['private'];shed=private['shed']
    inventories=private['inventories'];positions=[farm['farmer'],*farm['hands']]
    # Reconcile receipts against post-work stock, not requested quantities.
    if st['pending']:
        expected=st['pending'][0]['before'];qty=sum(p['qty'] for p in st['pending'])
        got=min(qty,max(0,int(shed.get('SHEEP',0))-expected))
        st['credit']+=got;_G4_REPORT['confirmed']+=got;_G4_REPORT['partial']+=int(got<qty)
        st['pending']=[]
    for actor,p in list(st['pickup'].items()):
        got=max(0,int(inventories[actor].get('SHEEP',0))-p['before']) if actor<len(inventories) else 0
        st['credit']=max(0,st['credit']-min(got,p['qty']))
    st['pickup']={}
    st['credit']=min(st['credit'],max(0,int(shed.get('SHEEP',0))))
    # Intents never spend the same discretionary cash twice; native commands
    # and all existing orders are included in each sequential admission check.
    intents=[];day=int(obs['step'])//24
    if 8<=day<=11 and 'YARN_STORE' in obs['town']['unlocked_shops']:
        for i,o in enumerate(action.get('market',[])):
            if len(o)==3 and o[:2]==['BUY_ANIMAL','COW'] and 1<=int(o[2])<=2:
                intents.append(dict(kind='purchase',slot=i,precondition=True,expected=list(o),replacement=['BUY_ANIMAL','SHEEP',int(o[2])]))
    out,accepted=_g4_resolve(obs,action,intents)
    if accepted:
        before=int(projected_shed(action,FarmView(obs)).get('SHEEP',0))
        st['pending']=[dict(before=before,qty=int(i['replacement'][2])) for i in accepted]
    commands=[list(out.get('farmer') or ['PASS']),*[list(c) for c in out.get('hands',[])]]
    cow_stock=max(0,int(shed.get('COW',0)));sheep_stock=min(st['credit'],max(0,int(shed.get('SHEEP',0))))
    used_sites=set()
    for actor,cmd in enumerate(commands[:len(positions)]):
        x,y=positions[actor];inv=inventories[actor];tile=farm['tiles'][y][x]
        if cmd[:2]==['PICKUP','COW']:
            qty=max(1,int(cmd[2])) if len(cmd)>2 else 1
            if cow_stock>=qty:cow_stock-=qty;continue
            if x in (4,5) and y in (4,5) and sheep_stock>=qty and not any(inv.get(a,0) for a in ('COW','SHEEP','GOOSE')):
                cmd[1]='SHEEP';sheep_stock-=qty
                st['pickup'][actor]=dict(before=int(inv.get('SHEEP',0)),qty=qty)
                _G4_REPORT['pickups']+=qty
        elif cmd[:2]==['PLACE','COW'] and not inv.get('COW',0) and inv.get('SHEEP',0):
            if isinstance(tile,dict) and tile.get('kind')=='PASTURE' and not tile.get('animal') and (x,y) not in used_sites:
                cmd[1]='SHEEP';used_sites.add((x,y));st['sites'].add((x,y));_G4_REPORT['placements']+=1
    out=dict(out,farmer=commands[0],hands=commands[1:])
    # WOOL has no production-input obligation. Use actual projected shed stock,
    # never imagined harvest credit; preserve every existing market order.
    if st['sites']:
        stock=projected_shed(out,FarmView(obs));orders=[list(o) for o in out.get('market',[])]
        sold=sum(int(o[2]) for o in orders if len(o)>=3 and o[:2]==['SELL','WOOL'])
        extra=max(0,int(stock.get('WOOL',0))-sold)
        if extra and len(orders)<10:
            orders.append(['SELL','WOOL',extra]);out=dict(out,market=orders);_G4_REPORT['extra_sales']+=extra
    return out

def _g4_market(obs,action):
    if int(obs['step'])<216 or not _v44y_clone_gate(obs):return action
    orders=action.get('market',[]);cash_items={'MILK','WOOL','EGG','TOMATO','CARROT','STRAWBERRY','MELON'}
    # Exclude all purchases from the predictive model: unlike the donor's
    # money-unbounded simulator, we do not compare financing-sensitive lists.
    if any(not o or len(o)!=3 or o[0]!='SELL' or o[1] not in cash_items for o in orders):return action
    candidate=_v44y_reorder(obs,action)
    if candidate==action:return action
    out,accepted=_g4_resolve(obs,action,[dict(kind='ordering',slot=-1,precondition=True,orders=candidate['market'])])
    _G4_REPORT['market_reorders']+=bool(accepted)
    return out

def g4_agent(observation,configuration=None):
    action=_G4_PARENT(observation,configuration)
    st=_g4_state(observation)
    standard=configuration is None or all(configuration.get(k,v)==v for k,v in [('boardSize',10),('turnsPerDay',24),('shedCapacity',100),('maxMarketOrdersPerTurn',10),('farmHandCostMult',1)])
    if not standard:return action
    if _G4_P:action=_g4_herd(observation,action,st)
    if _G4_M:action=_g4_market(observation,action)
    race=_RACE_STATE.get(int(observation['player']))
    if (_G4_M or _G4_P) and race is not None and race.get('prev_action') is not None:race['prev_action']=action
    return action

g4_agent.telemetry=_G4_REPORT
