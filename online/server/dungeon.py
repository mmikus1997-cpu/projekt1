"""Lochy spod Bramy Lochu — walki silnikiem 2.0 (combat.simultaneous) z NPC.

0.31: 10 pięter, progres 0-100% w characters.dungeon_progress.
6.x GDD v3.1: trzy tryby, każdy liniowy (piętro walczy się raz, dropy przy pierwszym zwycięstwie):
  - Normal (Ring)  10×10 = 100 pięter · od 3. poziomu  ·  8 energii · dropy przedmiotów,
  - Hard            2×10 =  20 pięter · od 7. poziomu  · 15 energii · kosmetyka + $$ + XP,
  - Nightmare       3×10 =  30 pięter · od 15. poziomu · 25 energii · konie/psy premium + $$$ + XP.
Każda seria (10 pięter) ma własny motyw; bossowie serii stoją na pozycjach 3, 6 i 10.
Walki: HP wg Walki 1.0 (200 + 5×Cha + 2×Lvl), logi akcji pod animacje Fluttera (5.1).
Historia walk: tabela dungeon_runs; rekordy trybów: kolumny dungeon_normal/hard/nightmare.
Zero rankingu/Elo i zero realnych pieniędzy; losowość dropu jest deterministyczna (hash postaci i piętra).
"""
import hashlib
import json
import random
import secrets

from fastapi import Depends, Request
from pydantic import BaseModel
from typing import Literal
from . import gear as G

ENERGY=8  # zgodność wsteczna: koszt Normal
LOOT_FLOORS={3:'buty-cienia',6:'rekawice-lochu',9:'helm-lochu',10:'korona-wladcy'}  # unikaty serii 1 Normal (1.9: Hełm na p. 9)
BOSS_POS=(3,6,10)
DROP_CHANCE=0.10  # 6.1: zwykli przeciwnicy Normal
# 6.1 (decyzja usera): dropy z istniejących przedmiotów zestawu — czapka, rękawice, pierścień, pas, buty, spodnie, koszulka, naszyjnik;
# bez kuponów/akcesoriów/plecaków. Sloty ring/belt/pants dołączą automatycznie, gdy pojawią się przedmioty (Etap 7).
DROP_SLOTS=('helmet','gloves','ring','belt','shoes','pants','shirt','amulet')

# Seria 1 Normal — oryginalne 10 pięter (0.31); szablon pozycji dla kolejnych serii
FLOORS=[
 dict(n=1,name='Szczur z Kanałów',cls='szybki',stats=[6,6,7,5,7],seq=['fast','dodge','heavy']),
 dict(n=2,name='Beczkowy Golem',cls='obronca',stats=[9,7,6,8,6],seq=['heavy','dodge','fast']),
 dict(n=3,name='Nurka Zwis',cls='szybki',stats=[10,8,11,7,10],seq=['fast','fast','dodge']),
 dict(n=4,name='Kanalarz Glo',cls='bokser',stats=[13,8,9,9,8],seq=['heavy','heavy','dodge']),
 dict(n=5,name='Pani Mgły',cls='obronca',stats=[10,14,9,12,9],seq=['dodge','fast','heavy']),
 dict(n=6,name='Rdza',cls='szybki',stats=[12,10,14,9,13],seq=['fast','dodge','fast']),
 dict(n=7,name='Oberwany Sufit',cls='bokser',stats=[16,10,10,11,9],seq=['heavy','fast','heavy']),
 dict(n=8,name='Dwoje Oczu',cls='szybki',stats=[14,12,16,11,15],seq=['dodge','fast','fast']),
 dict(n=9,name='Strażnik Bramy',cls='obronca',stats=[15,17,12,16,12],seq=['dodge','heavy','fast']),
 dict(n=10,name='Władca Lochu',cls='bokser',stats=[21,18,17,20,17],seq=['heavy','heavy','fast']),
]
ARCHETYPES=['Rekrut','Zabijaka','Herszt','Osiłek','Mistrzyni Uników','Czempion','Taran','Cień','Strażnik','Władca']

# Tryby: motywy serii (dopełniacz do nazw NPC), mnożnik siły serii, poziom NPC, nagrody
MODES={
 'normal':dict(label='Normal (Ring)',level=3,energy=8,
  themes=['Kanałów','Doków','Złomowiska','Metra','Hal Targowych','Elektrowni','Wieżowców','Katakumb','Lodowni','Wulkanu'],
  mult=lambda s:1+0.35*(s-1),npc_level=lambda f:2*f if f<=10 else 10+f,
  cash=lambda f:30+30*f,xp=lambda f:8+4*f),
 'hard':dict(label='Hard',level=7,energy=15,
  themes=['Stalowej Areny','Czarnego Ringu'],
  mult=lambda s:2.0+0.6*(s-1),npc_level=lambda f:30+2*f,
  cash=lambda f:400+200*f,xp=lambda f:80+25*f),
 'nightmare':dict(label='Nightmare',level=15,energy=25,
  themes=['Koszmaru','Otchłani','Zaćmienia'],
  mult=lambda s:3.4+0.8*(s-1),npc_level=lambda f:60+2*f,
  cash=lambda f:1500+600*f,xp=lambda f:250+50*f),
}
MODE_COLUMN={'normal':'dungeon_normal','hard':'dungeon_hard','nightmare':'dungeon_nightmare'}

# 6.2: kosmetyka Hard (kolekcja s['cosmetics'] / ramki s['frames']; bez wpływu na statystyki)
def hard_cosmetic(series,pos):
    t=MODES['hard']['themes'][series-1]
    return {3:dict(id=f'npc-outfit-hard-{series}',kind='npc_outfit',name=f'Strój NPC „{t}”'),
            6:dict(id=f'car-skin-hard-{series}',kind='car_skin',name=f'Skórka auta „{t}”'),
            10:dict(id=f'dungeon-hard-{series}',kind='frame',name=f'Ramka „Pogromca {t}”')}[pos]
# 6.3: zwierzęta premium Nightmare (konie → stajnia z hodowlą 0.43, psy → psiarnia-kolekcja s['dogs'])
PREMIUM_HORSES=['Nocny Ogier','Otchłanny Arab','Zaćmiony Fryz']
PREMIUM_DOGS=['Koszmarny Dog','Ogar Otchłani','Wilczarz Zaćmienia']
def nightmare_pets(series,pos):
    out=[]
    if pos in (6,10):out.append(dict(kind='horse',key=f'stable-premium-{series}-{pos}',breed=f'premium-{series}',name=PREMIUM_HORSES[series-1]+(' (Legenda)' if pos==10 else ''),
        speed=7+series+(1 if pos==10 else 0),stamina=7+series+(1 if pos==10 else 0),gen=1,premium=True))
    if pos in (3,10):out.append(dict(kind='dog',key=f'kennel-premium-{series}-{pos}',breed=f'premium-{series}',name=PREMIUM_DOGS[series-1]+(' (Legenda)' if pos==10 else ''),
        speed=6+series+(1 if pos==10 else 0),stamina=6+series+(1 if pos==10 else 0),gen=1,premium=True))
    return out

def total_floors(mode):return 10*len(MODES[mode]['themes'])

def npc_for(mode,floor):
    """Przeciwnik piętra (1-based). Seria 1 Normal = oryginalne FLOORS."""
    series,pos=(floor-1)//10+1,(floor-1)%10+1
    t=FLOORS[pos-1];m=MODES[mode]
    if mode=='normal' and series==1:name=t['name'];stats=list(t['stats'])
    else:name=ARCHETYPES[pos-1]+' '+m['themes'][series-1];stats=[round(v*m['mult'](series),1) for v in t['stats']]
    return dict(n=floor,series=series,pos=pos,boss=pos in BOSS_POS,theme=m['themes'][series-1],name=name,cls=t['cls'],stats=stats,seq=list(t['seq']),level=m['npc_level'](floor))

class FloorIn(BaseModel):
    seq:list[str]|None=None  # ignorowane — Klasa = Taktyka (5.1)
    mode:Literal['normal','hard','nightmare']='normal'

SCHEMA='''
CREATE TABLE IF NOT EXISTS dungeon_runs(id INTEGER PRIMARY KEY AUTOINCREMENT,character_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,mode TEXT NOT NULL,floor INTEGER NOT NULL,win INTEGER NOT NULL,rounds INTEGER NOT NULL,rewards_json TEXT NOT NULL,report_json TEXT NOT NULL,combat_version TEXT NOT NULL,created_at INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS dungeon_runs_char ON dungeon_runs(character_id,id DESC);
'''


def install(app,d,E,combat):
    db,now,fail,world,own,auth,rate,audit=d.db,d.now,d.fail,d.world,d.own,d.auth,d.rate,d.audit
    with db.tx() as c:
        c.executescript(SCHEMA)
        cols={r[1] for r in c.execute('PRAGMA table_info(characters)')}
        for col in MODE_COLUMN.values():  # 6.4: migracja addytywna — rekordy trybów
            if col not in cols:c.execute(f'ALTER TABLE characters ADD COLUMN {col} INTEGER NOT NULL DEFAULT 0')

    def drop_pool(boss,series=1):
        """7.x GDD v3.1: drop z setów — serie 1–5: zwykli T1, bossowie T2; serie 6–10: zwykli T2, bossowie T3."""
        tier=(1 if series<=5 else 2)+(1 if boss else 0)
        return [i for i in G.ITEMS if i['tier']==tier]

    def rng_for(cid,mode,floor):
        h=hashlib.sha256(f'{cid}:{mode}:{floor}'.encode()).digest()
        return random.Random(int.from_bytes(h[:8],'big'))

    def best(ch,mode):
        v=ch[MODE_COLUMN[mode]] or 0
        if mode=='normal' and not v and (ch['dungeon_progress'] or 0)>0:v=(ch['dungeon_progress'] or 0)//10  # stary progres 0-100% (10 pięter)
        return v

    def give_item(s,item_id):
        """Pierwsza sztuka → ekwipunek; duplikat → plecak (s['backpack']) — decyzja gracza (Etap 7)."""
        if item_id not in s['inventory']:s['inventory'].append(item_id);return 'inventory'
        s.setdefault('backpack',[]).append(item_id);return 'backpack'

    def item_name(item_id):
        if item_id in G.BY_ID:
            it=G.BY_ID[item_id];return G.tr('pl','slot.'+it['slot'])+' · '+G.tr('pl','set.'+it['set'])
        return next((i['name'] for i in E.ITEMS+E.DUNGEON_ITEMS if i['id']==item_id),item_id)

    def mode_info(ch,s,mode):
        m=MODES[mode];b=best(ch,mode);tot=total_floors(mode);nxt=None if b>=tot else npc_for(mode,b+1)
        return dict(mode=mode,label=m['label'],reqLevel=m['level'],energy=m['energy'],locked=E.level(s['xp'])<m['level'],
            best=b,floors=tot,series=len(m['themes']),themes=m['themes'],completed=b>=tot,
            nextFloor=None if not nxt else dict(n=nxt['n'],series=nxt['series'],pos=nxt['pos'],boss=nxt['boss'],theme=nxt['theme'],name=nxt['name'],cls=nxt['cls'],cash=m['cash'](nxt['n']),xp=m['xp'](nxt['n'])))

    def payload(c,ch,s):
        modes={k:mode_info(ch,s,k) for k in MODES};nm=modes['normal']
        # pola 0.31 (zgodność ze starym UI): progres = % Normal (100 pięter → 1 piętro = 1%)
        return dict(progress=nm['best'],atGate=ch['current_location']=='brama-lochow',completed=nm['completed'],
            locked=nm['locked'],reqLevel=nm['reqLevel'],tactic=combat.class_tactic(E.effective(s),ch['class_type']),tacticSet=True,
            nextFloor=nm['nextFloor'],modes=modes,
            loot=[i for i in s.get('dungeonLoot',[])],lootNames={i['id']:i['name'] for i in E.DUNGEON_ITEMS},
            backpack=list(s.get('backpack',[])),cosmetics=list(s.get('cosmetics',[])),dogs=list((s.get('dogs') or {}).values()))

    @app.post('/api/worlds/{wid}/dungeon/floor')
    def floor_fight(wid:int,data:FloorIn,request:Request,u=Depends(auth)):
        rate(request,'dungeon-'+str(u['id']),30,3600000)
        mode=data.mode;m=MODES[mode]
        with db.tx() as c:
            world(c,wid,True);ch=own(c,u['id'],wid)
            if ch['travel_destination']:fail(409,'Jesteś w drodze — Loch poczeka na twój powrót.')
            if (ch['current_location'] or 'ulica')!='brama-lochow':fail(409,'Wejście do Lochu prowadzi spod Bramy Lochu — zmień lokację w profilu.')
            s=json.loads(ch['state_json'])
            if E.level(s['xp'])<m['level']:fail(409,f"Loch {m['label']} odblokowuje się na {m['level']}. poziomie — zdobywaj XP w kontraktach i PvP.")
            b=best(ch,mode)
            if b>=total_floors(mode):fail(409,f"Loch {m['label']} opanowany w 100% — poczekaj na nowy zjazd.")
            npc=npc_for(mode,b+1)
            E.spend(s,energy=m['energy'])
            cunning=E.effective(s)[4]
            npc_red=min(6,max(0,cunning-10)//10*2)  # 0.35: Spryt — NPC traci 2% potencjału za każde 10 pkt (cap 6%)
            npc_stats=[round(v*(100-npc_red)/100,1) for v in npc['stats']]
            # 6.4: silnik 2.0 (logi akcji pod Fluttera), Klasa = Taktyka, HP wg Walki 1.0
            report=combat.simultaneous(E.effective(s),npc_stats,None,list(npc['seq']),secrets.randbits(32),a_cls=ch['class_type'],d_cls=npc['cls'],
                a_evo=s.get('evolutionCode'),a_evo2=s.get('evolution2Code'),levels=(E.level(s['xp']),npc['level']),a_gear=s.get('equipped'),d_gear=combat.npc_loadout(s.get('equipped'),npc.get('boss',False)))  # Combat 3.0: NPC z bronią i pancerzem wg poziomu
            report['names']=[ch['nickname'],npc['name']];report['stats']=[E.effective(s),npc_stats]  # Flutter FightScreen: nazwy i statystyki obu stron
            win=report['winner']==0
            loot=None;drops=[];cosm=[];pets=[];rewards=dict(cash=0,xp=0)
            if win:
                if E.BP_HOOK[0]:E.BP_HOOK[0](c,ch['id'],'dungeon')  # 8.4 GDD v3.1: XP przepustki
                rewards=dict(cash=m['cash'](npc['n']),xp=m['xp'](npc['n']))
                s['cash']+=rewards['cash'];s['xp']+=rewards['xp']
                if mode=='normal':
                    lid=LOOT_FLOORS.get(npc['n'])  # unikaty serii 1 (jednorazowo)
                    if lid and lid not in s.get('dungeonLoot',[]):
                        s.setdefault('dungeonLoot',[]).append(lid);give_item(s,lid)
                        loot=next(i for i in E.DUNGEON_ITEMS if i['id']==lid)
                        drops.append(dict(id=lid,name=loot['name'],to='inventory',unique=True))
                    rng=rng_for(ch['id'],mode,npc['n'])
                    if npc['boss'] and loot:pass  # boss serii 1 z unikatem — unikat jest jego dropem
                    elif npc['boss'] or rng.random()<DROP_CHANCE:  # 6.1: boss 100%, zwykły 10%
                        it=rng.choice(drop_pool(npc['boss'],npc['series']))
                        s.setdefault('backpack',[]).append(it['id'])  # 7.1: przedmioty setów żyją w plecaku (nagroda może przekroczyć pojemność)
                        drops.append(dict(id=it['id'],name=item_name(it['id']),to='backpack',unique=False,tier=it['tier']))
                elif mode=='hard' and npc['boss']:
                    cm=hard_cosmetic(npc['series'],npc['pos'])
                    if cm['kind']=='frame':
                        s.setdefault('frames',[])
                        if cm['id'] not in s['frames']:s['frames'].append(cm['id'])
                    else:
                        s.setdefault('cosmetics',[])
                        if cm['id'] not in s['cosmetics']:s['cosmetics'].append(cm['id'])
                    cosm.append(cm)
                elif mode=='nightmare' and npc['boss']:
                    for p in nightmare_pets(npc['series'],npc['pos']):
                        entry={k:v for k,v in p.items() if k!='kind'}
                        if p['kind']=='horse':s.setdefault('horses',{})[p['key']]=entry  # hodowla 0.43 widzi je od razu
                        else:s.setdefault('dogs',{})[p['key']]=entry
                        pets.append(p)
                col=MODE_COLUMN[mode]
                if mode=='normal':
                    c.execute(f'UPDATE characters SET state_json=?,{col}=?,dungeon_progress=? WHERE id=?',(json.dumps(s,ensure_ascii=False,separators=(',',':')),npc['n'],npc['n'],ch['id']))
                else:
                    c.execute(f'UPDATE characters SET state_json=?,{col}=? WHERE id=?',(json.dumps(s,ensure_ascii=False,separators=(',',':')),npc['n'],ch['id']))
                extra=''.join([' Drop: '+x['name']+(' (do plecaka)' if x['to']=='backpack' else '')+'.' for x in drops]+[' Kosmetyk: '+x['name']+'.' for x in cosm]+[' Zwierzę premium: '+x['name']+'.' for x in pets])
                message='Pokonano: '+npc['name']+'. +'+str(rewards['cash'])+' $, +'+str(rewards['xp'])+' XP.'+extra
            else:
                c.execute('UPDATE characters SET state_json=? WHERE id=?',(json.dumps(s,ensure_ascii=False,separators=(',',':')),ch['id']))
                message=npc['name']+' okazał się twardszy. Zbierz siły, doćwicz i spróbuj ponownie.'
            rw=dict(rewards,drops=drops,cosmetics=cosm,pets=pets)
            c.execute('INSERT INTO dungeon_runs(character_id,mode,floor,win,rounds,rewards_json,report_json,combat_version,created_at) VALUES(?,?,?,?,?,?,?,?,?)',
                (ch['id'],mode,npc['n'],int(win),len(report['rounds']),json.dumps(rw,ensure_ascii=False),json.dumps(report,ensure_ascii=False,separators=(',',':')),combat.ENGINE_V2,now()))
            c.execute('DELETE FROM dungeon_runs WHERE character_id=? AND id NOT IN (SELECT id FROM dungeon_runs WHERE character_id=? ORDER BY id DESC LIMIT 200)',(ch['id'],ch['id']))  # limit historii
            audit(c,u['id'],'dungeon.floor',dict(mode=mode,floor=npc['n'],win=win))
            newbest=npc['n'] if win else b
            return dict(ok=True,mode=mode,cleared=win,floor=npc['n'],series=npc['series'],boss=npc['boss'],best=newbest,
                progress=(newbest if mode=='normal' else None),report=report,rewards=rewards,drops=drops,cosmetics=cosm,pets=pets,
                loot=(dict(id=loot['id'],name=loot['name']) if loot else None),combat_version=combat.ENGINE_V2,message=message)

    @app.get('/api/worlds/{wid}/dungeon/history')
    def history(wid:int,u=Depends(auth)):
        """6.4: historia przejść i statystyki per tryb (rekord, próby, zwycięstwa)."""
        with db.read() as c:
            world(c,wid,True);ch=own(c,u['id'],wid)
            stats={}
            for mode in MODES:
                r=c.execute('SELECT count(*) n,coalesce(sum(win),0) w FROM dungeon_runs WHERE character_id=? AND mode=?',(ch['id'],mode)).fetchone()
                stats[mode]=dict(best=best(ch,mode),floors=total_floors(mode),attempts=r['n'],wins=r['w'])
            runs=[dict(id=r['id'],mode=r['mode'],floor=r['floor'],win=bool(r['win']),rounds=r['rounds'],rewards=json.loads(r['rewards_json']),combatVersion=r['combat_version'],createdAt=r['created_at'])
                  for r in c.execute('SELECT id,mode,floor,win,rounds,rewards_json,combat_version,created_at FROM dungeon_runs WHERE character_id=? ORDER BY id DESC LIMIT 50',(ch['id'],))]
            return dict(stats=stats,runs=runs)

    @app.get('/api/worlds/{wid}/dungeon/runs/{rid}')
    def run_report(wid:int,rid:int,u=Depends(auth)):
        """Pełny raport walki z historii (odtworzenie animacji we Flutterze)."""
        with db.read() as c:
            world(c,wid,True);ch=own(c,u['id'],wid)
            r=c.execute('SELECT report_json,mode,floor,win,combat_version FROM dungeon_runs WHERE id=? AND character_id=?',(rid,ch['id'])).fetchone()
            if not r:fail(404,'Nie znaleziono walki.')
            return dict(mode=r['mode'],floor=r['floor'],win=bool(r['win']),combat_version=r['combat_version'],report=json.loads(r['report_json']))

    return dict(payload=payload,npc_for=npc_for,drop_pool=drop_pool)
