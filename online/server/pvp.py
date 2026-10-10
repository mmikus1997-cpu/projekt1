"""0.28 Wyzwania PvP 2.0: lista celów, atak z 3 slotami akcji, raport rundowy.

0.42 Auto-atak: atak rozstrzyga się OD RAZU na zapisanych taktykach obu stron (payload
ignorowany) — obrońca nie musi być online ani nic potwierdzać; jego taktyka z 0.41 jest jego
głosem. 5.1 GDD v3.1: Klasa = Taktyka (Bokser=Presja, Obrońca=Kontrola, Szybki=Kontra) — bez szablonów.
Silnik symultaniczny stoi w combat.simultaneous (kolejność wg Refleksu, pasywki klasowe:
Bokser/Szybki/Obrońca). Obrońca walczy według własnego zapisanego szablonu taktycznego
(state_json.pvpDefense), więc atak rozstrzyga się od razu — bez czekania na akceptację.
Walka jest rankingowa: wspólny limit 5 na dobę (ranked_usage), aktualizacja Elo obu stron,
pełny raport JSON (rounds) pod odtworzenie animacji oraz zdarzenie w Centrum Zdarzeń obrońcy.
"""
import json
import secrets

from fastapi import Depends, Request
from pydantic import BaseModel, Field

SCHEMA='''
CREATE TABLE IF NOT EXISTS pvp_battles(id INTEGER PRIMARY KEY AUTOINCREMENT,world_id INTEGER NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,attacker_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,defender_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,report_json TEXT NOT NULL,rating_json TEXT NOT NULL DEFAULT '',created_at INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS pvp_battles_world ON pvp_battles(world_id,created_at);
'''

# 5.3 GDD v3.1: nagrody za każdy zakończony mecz rankingowy — dla obu stron (decyzja usera), także w wyzwaniach 1.0
PVP_REWARDS={'win':dict(cash=500,xp=50,prestige=1),'loss':dict(cash=100,xp=10,prestige=0),'draw':dict(cash=200,xp=25,prestige=0)}

class Attack(BaseModel):
    seq:list[str]|None=None  # 0.42: zignorowane — walka zawsze na zapisanych taktykach (Auto-atak)


def install(app,d,E,combat,city):
    from . import avatar as avatar_mod
    db,now,fail,world,own,auth,rate,audit,extra=d.db,d.now,d.fail,d.world,d.own,d.auth,d.rate,d.audit,d.extra
    c=db.connect()
    try:
        c.executescript(SCHEMA)
        # 1.6 GDD v3.1: wersja silnika w pvp_battles (stare wiersze = NULL → fallback '2.0')
        if 'combat_version' not in {r[1] for r in c.execute('PRAGMA table_info(pvp_battles)')}:c.execute('ALTER TABLE pvp_battles ADD COLUMN combat_version TEXT')
        c.commit()
    finally:c.close()

    def norm(seq):
        mapped=[combat.PVP_ALIAS.get(str(x).strip().lower(),'') for x in seq]
        if not all(mapped) or len(mapped)!=3:fail(422,'Sekwencja to dokładnie 3 akcje: unik, mocny_cios albo szybki_cios.')
        return mapped

    def load(c,cid):
        return json.loads(c.execute('SELECT state_json FROM characters WHERE id=?',(cid,)).fetchone()[0])

    def save(c,cid,s):
        s['lastAction']=now()
        c.execute('UPDATE characters SET state_json=? WHERE id=?',(json.dumps(s,ensure_ascii=False,separators=(',',':')),cid))

    @app.get('/api/worlds/{wid}/pvp/targets')
    def targets(wid:int,district:int=None,u=Depends(auth)):
        with db.read() as c:
            world(c,wid)
            me=c.execute('SELECT id FROM characters WHERE account_id=? AND world_id=?',(u['id'],wid)).fetchone()
            if not me:fail(404,'Najpierw stwórz postać w tym świecie.')
            sql="SELECT c.id,c.nickname,c.rating,c.state_json,json_extract(c.state_json,'$.xp') xp,json_extract(c.state_json,'$.stats') stats,c.current_district,c.class_type,coalesce(ss.skin,'') skin FROM characters c JOIN accounts a ON a.id=c.account_id AND a.banned=0 LEFT JOIN shop_state ss ON ss.account_id=c.account_id WHERE c.world_id=? AND c.id!=?"
            args=[wid,me['id']]
            if district is not None:sql+=' AND c.current_district=?';args.append(district)
            sql+=' ORDER BY c.rating DESC LIMIT 20'
            out=[]
            for r in c.execute(sql,args):
                stats=json.loads(r['stats']);xp=r['xp'] or 0
                st=json.loads(r['state_json']) if 'state_json' in r.keys() else None
                av=avatar_mod.brief(st) if st else None
                out.append(dict(id=r['id'],nickname=r['nickname'],level=E.level(xp),cls=combat.pvp_class(stats,r['class_type']),rating=int(round(r['rating']/10)*10),skin=r['skin'],district=r['current_district'] or 1,avatar=av))
            return dict(targets=out,note='Szacunkowy rating i klasa — dokładne statystyki pozostają tajemnicą do pierwszej rundy.')

    # 5.1 GDD v3.1: POST /pvp/defense (szablon obrony) usunięty — Klasa = Taktyka

    class EvolveChoice(BaseModel):
        model_config={'extra':'forbid'}
        choice:str=Field(min_length=3,max_length=24)
    @app.post('/api/worlds/{wid}/pvp/evolve')
    def pvp_evolve(wid:int,data:EvolveChoice,request:Request,u=Depends(auth)):
        # Klub (Flutter): ewolucja klasy wg poziomu PvP — etap I od PvP 5, etap II od PvP 10; wybór jednorazowy.
        rate(request,'pvp-evolve-'+str(u['id']),10,3600000)
        code=data.choice.strip().lower()
        with db.tx() as c:
            world(c,wid,True);ch=own(c,u['id'],wid)
            if not ch['class_type']:fail(409,'Najpierw wybierz klasę — odblokowuje się razem z PvP.')
            s=json.loads(ch['state_json'])
            st=combat.evolution_status(ch['class_type'],ch['wins'],ch['losses'],ch['draws'],s.get('evolutionCode'),s.get('evolution2Code'))
            nxt=st['next']
            if not nxt:fail(409,'Masz już obie ewolucje klasy.')
            if not nxt['available']:fail(409,f"Ewolucja {'I' if nxt['stage']==1 else 'II'} wymaga poziomu PvP {nxt['reqLevel']} — masz {st['pvpLevel']}.")
            if code not in [o['code'] for o in nxt['options']]:fail(422,'Ta ewolucja nie należy do Twojej klasy albo do bieżącego etapu.')
            if nxt['stage']==1:s['evolutionCode']=code
            else:s['evolution2Code']=code
            c.execute('UPDATE characters SET state_json=?,class_evolution=? WHERE id=?',(json.dumps(s,ensure_ascii=False,separators=(',',':')),nxt['stage']+1,ch['id']))
            st=combat.evolution_status(ch['class_type'],ch['wins'],ch['losses'],ch['draws'],s.get('evolutionCode'),s.get('evolution2Code'))
            pick=st['evolution1'] if nxt['stage']==1 else st['evolution2']
            return dict(ok=True,stage=nxt['stage'],picked=pick,evolution=st,message=f"{pick['icon']} Ewolucja {'I' if nxt['stage']==1 else 'II'}: {pick['label']} — {pick['desc']}")
    @app.post('/api/worlds/{wid}/pvp/attack/{target_id}')
    def attack(wid:int,target_id:int,data:Attack,request:Request,u=Depends(auth)):
        rate(request,'pvp-attack-'+str(u['id']),30,3600000)  # 0.42 Auto-atak: payload bez znaczenia
        with db.tx() as c:
            w=world(c,wid,True);a=own(c,u['id'],wid)
            if a['id']==target_id:fail(409,'Nie atakujesz samego siebie.')
            if a['travel_destination']:fail(409,'Jesteś w drodze — wyzwania poczekają na przyjazd.')
            t=c.execute("SELECT c.*,a.banned,a.id t_account FROM characters c JOIN accounts a ON a.id=c.account_id WHERE c.id=? AND c.world_id=?",(target_id,wid)).fetchone()
            if not t:fail(404,'Nie ma takiego mieszkańca w tym świecie.')
            if t['banned']:fail(409,'Ten mieszkaniec jest niedostępny.')
            if t['travel_destination']:fail(409,'Cel jest w drodze — poczekaj, aż dotrze na miejsce.')
            if extra.blocked(c,u['id'],t['account_id']):fail(409,'Kontakt został zablokowany.')
            d.limit(c,a['id']);d.limit(c,t['id']);d.pair(c,a['id'],t['id'])  # 5.3: limit pary także w PvP 2.0
            s_a=load(c,a['id']);s_d=load(c,t['id'])
            if E.level(s_a.get('xp') or 0)<2:fail(409,'Wyzwania PvP odblokowują się na 2. poziomie.')
            # 5.1 GDD v3.1: Klasa = Taktyka — sekwencje obu stron wynikają z klas (None → combat.CLASS_TACTIC)
            report=combat.simultaneous(E.effective(s_a),E.effective(s_d),None,None,secrets.randbits(32),a_cls=a['class_type'],d_cls=t['class_type'],a_evo=s_a.get('evolutionCode'),d_evo=s_d.get('evolutionCode'),levels=(E.level(s_a.get('xp') or 0),E.level(s_d.get('xp') or 0)),a_evo2=s_a.get('evolution2Code'),d_evo2=s_d.get('evolution2Code'),a_gear=s_a.get('equipped'),d_gear=s_d.get('equipped'))  # Combat 3.0: broń i pancerz z ekwipunku
            report['names']=[a['nickname'],t['nickname']];report['characterIds']=[a['id'],t['id']];report['ranked']=True
            report['stats']=[E.effective(s_a),E.effective(s_d)]
            report['avatars']=[avatar_mod.brief(s_a),avatar_mod.brief(s_d)];report['gear']=[avatar_mod.gear(s_a),avatar_mod.gear(s_d)]  # 0.47
            expected=1/(1+10**((t['rating']-a['rating'])/400))
            score=1 if report['winner']==0 else 0 if report['winner']==1 else 0.5
            change=24*(score-expected);report['ratingChanges']=[change,-change]
            day=now()//(24*E.HOUR)*(24*E.HOUR)
            for cid,delta,is_win,is_loss in [(a['id'],change,report['winner']==0,report['winner']==1),(t['id'],-change,report['winner']==1,report['winner']==0)]:
                c.execute('INSERT INTO ranked_usage(character_id,day,used) VALUES(?,?,1) ON CONFLICT(character_id,day) DO UPDATE SET used=used+1',(cid,day))
                c.execute('UPDATE characters SET rating=rating+?,wins=wins+?,losses=losses+?,draws=draws+? WHERE id=?',(delta,int(is_win),int(is_loss),int(report['winner'] is None or (not is_win and not is_loss)),cid))
            rw=[reward(c,a['id'],'draw' if report['winner'] is None else 'win' if report['winner']==0 else 'loss'),
                reward(c,t['id'],'draw' if report['winner'] is None else 'win' if report['winner']==1 else 'loss')]
            report['rewards']=rw
            bid=c.execute('INSERT INTO pvp_battles(world_id,attacker_id,defender_id,report_json,rating_json,created_at,combat_version) VALUES(?,?,?,?,?,?,?)',(wid,a['id'],t['id'],json.dumps(report,ensure_ascii=False,separators=(',',':')),json.dumps([change,-change]),now(),combat.ENGINE_V2)).lastrowid
            if E.BP_HOOK[0]:E.BP_HOOK[0](c,a['id'],'pvp')  # 8.4 GDD v3.1: XP przepustki za walkę PvP
            city['emit'](c,wid,[t['id']],'pvp_attacked',dict(attacker=a['nickname'],result='win' if report['winner']==1 else 'loss' if report['winner']==0 else 'draw',change=round(-change,1),seq=report.get('seqs',[None])[0],battle=bid))
            audit(c,u['id'],'pvp.attack',dict(battle=bid,target=t['id'],winner=report['winner']))
            return dict(ok=True,battle=bid,report=report,ratingChanges=[change,-change],rewards=rw,combat_version=combat.ENGINE_V2)

    def reward(c,cid,result):
        """5.3: gotówka + XP na postać, Punkt Prestiżu na konto (za wygraną)."""
        r=PVP_REWARDS[result];row=c.execute('SELECT state_json,account_id FROM characters WHERE id=?',(cid,)).fetchone()
        s=json.loads(row['state_json']);s['cash']=s.get('cash',0)+r['cash'];s['xp']=s.get('xp',0)+r['xp']
        E.log(s,f"⚔️ Walka rankingowa: {'wygrana' if result=='win' else 'przegrana' if result=='loss' else 'remis'} — +{r['cash']} $, +{r['xp']} XP"+(', +1 Punkt Prestiżu' if r['prestige'] else '')+'.',now())
        c.execute('UPDATE characters SET state_json=? WHERE id=?',(json.dumps(s,ensure_ascii=False,separators=(',',':')),cid))
        if r['prestige']:c.execute('UPDATE accounts SET prestige_points=prestige_points+? WHERE id=?',(r['prestige'],row['account_id']))
        return dict(result=result,**r)

    def recent(c,u,wid):
        me=c.execute('SELECT id FROM characters WHERE account_id=? AND world_id=?',(u['id'],wid)).fetchone()
        if not me:return []
        rows=c.execute('SELECT id,attacker_id,defender_id,report_json,created_at,combat_version FROM pvp_battles WHERE world_id=? AND (attacker_id=? OR defender_id=?) ORDER BY id DESC LIMIT 5',(wid,me['id'],me['id'])).fetchall()
        out=[]
        for r in rows:
            rep=json.loads(r['report_json']);out.append(dict(id=r['id'],created_at=r['created_at'],names=rep.get('names'),winner=rep.get('winner'),classes=rep.get('classes'),combat_version=r['combat_version'] or combat.ENGINE_V2_LEGACY))
        return out

    return dict(recent=recent,norm=norm,reward=reward)
