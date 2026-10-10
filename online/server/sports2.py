"""0.43 Klub Sportowy · nowe dyscypliny: Turniej Boksu/MMA, Agility psów, Łucznictwo (PvP celności), Pływanie (kondycja).

Zasady wspólne z 0.41/0.42: wszystko na zapisanych wyborach gracza (taktyka/klasa), wpisowe w
wirtualnych $, zero zakładów i zero prawdziwych płatności. Każda dyscyplina ma koszt energii,
limit szybkości (rate) i liczniki w state_json.sports2. Łucznictwo to asynchroniczne PvP
celności: rywalem jest najlepszy wynik zawodnika z rankingu (zapisany, jak taktyka) — nie
musi być online. Pływanie buduje kondycję (okno 48 h), która podnosi Charyzmę w E.effective.
Silnik ringowy: combat.simultaneous (ten sam co PvP) — turniej to 3 rundy z NPC.
"""
import json
from typing import Optional

from fastapi import Depends, Request
from pydantic import BaseModel


class AttemptIn(BaseModel):
    skip: bool = False   # QA 5: pominięcie czekania Kuponem Akcji (coupons.instant)

def install(app,d,E,combat):
    db,now,fail,world,own,auth,rate,audit=d.db,d.now,d.fail,d.world,d.own,d.auth,d.rate,d.audit

    def load(c,cid):
        return json.loads(c.execute('SELECT state_json FROM characters WHERE id=?',(cid,)).fetchone()[0])

    def save(c,cid,s):
        s['lastAction']=now()
        c.execute('UPDATE characters SET state_json=? WHERE id=?',(json.dumps(s,ensure_ascii=False,separators=(',',':')),cid))

    def s2(s):
        return s.setdefault('sports2',{})

    def day():
        return now()//(24*3600000)

    def combat_ready(c,ch):
        s=load(c,ch['id'])
        if E.level(s.get('xp') or 0)<2:fail(409,'Wyzwania PvP odblokowują się na 2. poziomie.')
        if s.get('travel_destination'):fail(409,'Jesteś w drodze — zawody poczekają na przyjazd.')
        return s

    # QA 5: rywale turnieju PvE osłabieni o 35% (były 38/52/66 Siły) — turniej ma być realnie wygrywalny
    TOURN_SCALE=0.65
    TOURN_NPC=[(n,[round(x*TOURN_SCALE) for x in st],sq) for n,st,sq in (('Kolegialny Nowicjusz',[38,38,38,38,38],['fast','fast','dodge']),('Czeladnik Ringu',[52,46,50,44,46],['heavy','fast','dodge']),('Mistrz Kolegium',[66,58,62,56,58],['dodge','heavy','fast']))]

    # QA 5: 3 podejścia na dobę — 1. od razu, 2. po 5 min, 3. po 15 min od poprzedniego; reset o północy (UTC)
    WAITS=(0,5*60000,15*60000)

    def attempts(s,key):
        a=s2(s).setdefault(key,{'day':0,'n':0,'last':0})
        if a.get('day')!=day():a.update(day=day(),n=0,last=0)
        return a

    def attempt_view(s,key):
        a=attempts(s,key);n=a['n']
        ready=None if n>=3 else (a['last']+WAITS[n] if n else 0)
        return dict(n=n,max=3,readyAt=ready,resetAt=(day()+1)*24*3600000,coupons=int((s.get('coupons') or {}).get('instant',0)))

    def take_attempt(s,key,skip):
        a=attempts(s,key)
        if a['n']>=3:fail(409,'Wykorzystano 3 podejścia — kolejne po północy.')
        ready=a['last']+WAITS[a['n']] if a['n'] else 0
        used_coupon=False
        if now()<ready:
            if not skip:fail(409,f'Następne podejście za {max(1,(ready-now()+59999)//60000)} min — albo użyj Kuponu Akcji.')
            cp=s.setdefault('coupons',{})
            if int(cp.get('instant',0))<1:fail(409,'Nie masz Kuponu Akcji — kupisz go w Sklepie.')
            cp['instant']=int(cp['instant'])-1;used_coupon=True
        a['n']+=1;a['last']=now()
        return a['n'],used_coupon

    @app.post('/api/worlds/{wid}/sports/tournament')
    def tournament(wid:int,request:Request,u=Depends(auth)):
        rate(request,'sports-tourn-'+str(u['id']),10,3600000)
        with db.tx() as c:
            world(c,wid,True);ch=own(c,u['id'],wid)
            s=combat_ready(c,ch)
            if s['cash']<200:fail(409,'Wpisowe do turnieju: 200 $ — za mało gotówki.')
            if s['energy']<30:fail(409,'Turniej kosztuje 30 energii — odpocznij i wróć.')
            t=s2(s).setdefault('tourn',{'day':0,'runs':0,'best':0})
            if t.get('day')!=day():t['day']=day();t['runs']=0
            if t['runs']>=2:fail(409,'Limit: 2 turnieje na dobę UTC — ring musi odetchnąć.')
            s['cash']-=200;s['energy']-=30;t['runs']+=1
            a_cls=combat.pvp_class(s['stats'],ch['class_type']) if hasattr(combat,'pvp_class') else 'Bokser'
            seq=combat.class_seq(E.effective(s),ch['class_type'])  # 5.1 GDD v3.1: Klasa = Taktyka
            rounds=[];wins=0
            for i,(name,npc_stats,npc_seq) in enumerate(TOURN_NPC):
                rep=combat.simultaneous(E.effective(s),npc_stats,seq,list(npc_seq),now()+i*7919,a_cls=ch['class_type'],d_cls=None,a_evo=s.get('evolutionCode'),a_evo2=s.get('evolution2Code'),levels=(E.level(s['xp']),E.level(s['xp'])),a_gear=s.get('equipped'),d_gear=s.get('equipped'))  # Combat 3.0: rywal turnieju w lustrzanym ekwipunku  # 5.2: rywal turnieju na poziomie gracza
                won=rep['winner']==0
                if rep['winner']==0:wins+=1
                rounds.append(dict(opponent=name,hp=rep['finalHp'],hpStart=rep['hpStart'],winner=rep['winner'],classes=rep.get('classes'),rounds=rep['rounds']))
            if wins==3:prize_cash,prize_xp,msg=1200,150,'Turniej zdominowany — 3 z 3! Puchar i pełna nagroda.'
            elif wins==2:prize_cash,prize_xp,msg=400,60,'Dobre 2 z 3 — nagroda pocieszenia i szacunek szatni.'
            else:prize_cash,prize_xp,msg=0,10,'Ring nauczy Cię pokory. Wpisowe zostaje na torze.'
            s['cash']+=prize_cash;s['xp']=s.get('xp',0)+prize_xp
            t['best']=max(t.get('best',0),wins)
            save(c,ch['id'],s)
            audit(c,u['id'],'sports.tournament',dict(wins=wins,prize=prize_cash))
            return dict(ok=True,wins=wins,prize=dict(cash=prize_cash,xp=prize_xp),message=msg,rounds=rounds,runsLeft=2-t['runs'],state=dict(tourn=t))

    # QA 5: Agility psów przeniesione do sports3.py (psiarnia, rasy, szkolenie, smaczek, limit 10/4 h)

    @app.post('/api/worlds/{wid}/sports/archery')
    def archery(wid:int,request:Request,data:Optional[AttemptIn]=None,u=Depends(auth)):
        """QA 5: Łucznictwo — każde podejście: +3/6/10% maks. energii (stack do północy) i natychmiast +20% energii."""
        rate(request,'sports-archery-'+str(u['id']),30,3600000)
        with db.tx() as c:
            w=world(c,wid,True);ch=own(c,u['id'],wid)
            s=load(c,ch['id']);E.sync(s,now(),w['speed'])
            if s.get('travel_destination'):fail(409,'Jesteś w drodze — strzelnica poczeka na przyjazd.')
            n,coupon=take_attempt(s,'archery3',bool(data and data.skip))
            cap=E.energy_max(s);s['energyMax']=cap
            gain=round(cap*0.20);before=s['energy'];s['energy']=min(cap,s['energy']+gain)
            st=s['stats'];seed=now()+ch['id']*101
            mine=max(0,min(30,int(10+(st[1]-10)*0.45+(st[2]-10)*0.25+(seed%7)-1)))
            lk=s2(s).setdefault('luk',{'best':0,'wins':0,'losses':0,'draws':0})
            new_record=mine>lk['best'];lk['best']=max(lk['best'],mine)
            save(c,ch['id'],s)
            audit(c,u['id'],'sports.archery',dict(n=n,mine=mine,coupon=coupon))
            return dict(ok=True,n=n,mine=mine,newRecord=new_record,energyGain=round(s['energy']-before),energyMax=cap,
                        maxPct=E.ARCHERY_MAX_PCT[n],attempt=attempt_view(s,'archery3'),
                        message=f'🎯 Seria {n}/3: {mine} pkt · maks. energia +{E.ARCHERY_MAX_PCT[n]}% ({cap}) · +{round(s["energy"]-before)}⚡ od razu.')

    @app.post('/api/worlds/{wid}/sports/swim')
    def swim(wid:int,request:Request,data:Optional[AttemptIn]=None,u=Depends(auth)):
        """QA 5: Pływanie — +3/6/10% statystyki klasowej i +1/3/5% regeneracji energii (stack do północy)."""
        rate(request,'sports-swim-'+str(u['id']),30,3600000)
        with db.tx() as c:
            w=world(c,wid,True);ch=own(c,u['id'],wid)
            s=load(c,ch['id']);E.sync(s,now(),w['speed'])
            if s.get('travel_destination'):fail(409,'Jesteś w drodze — basen poczeka na przyjazd.')
            n,coupon=take_attempt(s,'swim3',bool(data and data.skip))
            stat=E.CLASS_STAT.get(ch['class_type']) if ch['class_type'] else None
            if stat is None:stat=max(range(5),key=lambda i:s['stats'][i])   # bez klasy: najmocniejsza statystyka
            s2(s)['swim3']['stat']=stat
            save(c,ch['id'],s)
            audit(c,u['id'],'sports.swim',dict(n=n,stat=stat,coupon=coupon))
            return dict(ok=True,n=n,stat=stat,statPct=E.SWIM_STAT_PCT[n],regenPct=E.SWIM_REGEN_PCT[n],attempt=attempt_view(s,'swim3'),
                        message=f'🏊 Seria {n}/3: {E.STAT_NAMES[stat]} +{E.SWIM_STAT_PCT[n]}% · regeneracja energii +{E.SWIM_REGEN_PCT[n]}% do północy.')

    @app.get('/api/worlds/{wid}/sports2')
    def sports2_state(wid:int,u=Depends(auth)):
        with db.read() as c:
            world(c,wid)
            ch=c.execute('SELECT id,class_type,state_json FROM characters WHERE account_id=? AND world_id=?',(u['id'],wid)).fetchone()
            if not ch:fail(404,'Najpierw stwórz postać w tym świecie.')
            s=json.loads(ch['state_json'])
            m=s2(s)
            sw=m.get('swim') or {}
            bonus=min(5,(sw.get('kondycja') or 0)//6) if (s.get('lastTick') or 0)<sw.get('until',0) else 0
            t=m.get('tourn') or {}
            sw3=m.get('swim3') or {}
            return dict(ok=True,tourn=dict(runs=t.get('runs',0) if t.get('day')==day() else 0,best=t.get('best',0)),agil=m.get('agil') or {'best':0,'runs':0},luk=m.get('luk') or {'best':0,'wins':0,'losses':0,'draws':0},swim=dict(kondycja=0,until=0,bonus=0),
                        archery=dict(attempt_view(s,'archery3'),maxPct=E.ARCHERY_MAX_PCT[E.daily_stack(dict(s,lastTick=now()),'archery3')],energyMax=E.energy_max(dict(s,lastTick=now()))),
                        swim3=dict(attempt_view(s,'swim3'),stat=sw3.get('stat'),statPct=E.SWIM_STAT_PCT[E.daily_stack(dict(s,lastTick=now()),'swim3')],regenPct=E.SWIM_REGEN_PCT[E.daily_stack(dict(s,lastTick=now()),'swim3')]))
