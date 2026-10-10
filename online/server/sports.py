"""0.27 Klub Sportowy 2.0: sekcja boksowa (sparing i taktyka — arena/spar) oraz hipodrom.

Hipodrom stoi w Dzielnicy Kreatywnej (dzielnica 6), dostępny od 5 poziomu postaci.
Wynik wyścigu wyliczamy z atrybutów: kondycji dżokeja (Charyzma), sprytu (tor jazdy)
i statystyk konia (Szybkość/Wytrzymałość), z deterministycznym rozstrojeniem z seeda
wyścigu — zero losowości niezależnej od umiejętności. Wpisowe (50 $ wirtualnych) zasila
pulę nagród sportowych: 60/30/10 % dla miejsc 1–3. To zawody umiejętności, nie zakłady:
nie ma obstawiania, kursów ani realnych pieniędzy — dev-sklep nie ma tu żadnego udziału.
Puchar (1. miejsce) trafia do Kroniki Miasta (0.17) i podnosi prestiż organizacji
dżokeja (+25 w pseudodzielnic „Hipodrom", poza systemem wpływów terytorialnych 0.11).
"""
import json

from fastapi import Depends, Request
from pydantic import BaseModel, Field
from typing import Literal

HIP_DISTRICT = 6
HIP_LEVEL = 5
HIP_ENTRY = 50
CUP_PRESTIGE = 25
SPLIT = (60, 30, 10)
HORSES = [
 dict(id='mustang',name='Mustang',price=800,speed=3,stamina=3,level=5,description='Zwarty, niezawodny koń na start przygody z torem.'),
 dict(id='thoroughbred',name='Pełnej krwi',price=3000,speed=5,stamina=4,level=6,description='Szybki galop i rdzenna klasa torów wyścigowych.'),
 dict(id='champion',name='Czempion',price=8000,speed=6,stamina=6,level=8,description='Zawodnik stajni: maksimum szybkości i wytrzymałości.'),
]
NPC_RUNNERS = [
 dict(name='Ryszard „Roko”',charisma=8,cunning=6,speed=3,stamina=3),
 dict(name='Basia Błyskawica',charisma=5,cunning=9,speed=4,stamina=4),
 dict(name='Tadeusz „Truchł”',charisma=7,cunning=7,speed=2,stamina=5),
]
BOXING = dict(id='boks',name='Sekcja boksowa',spar=['rookie','clubmate','challenger'],note='Ring sparingowy i taktyka działają w arenie poniżej — bez zmian od 0.2/0.7.')

SCHEMA = '''
CREATE TABLE IF NOT EXISTS horse_races(id INTEGER PRIMARY KEY AUTOINCREMENT,world_id INTEGER NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,kind TEXT NOT NULL,creator_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,creator_json TEXT NOT NULL DEFAULT '',opponent_id INTEGER REFERENCES characters(id) ON DELETE SET NULL,status TEXT NOT NULL DEFAULT 'open',entry INTEGER NOT NULL DEFAULT 50,pot INTEGER NOT NULL DEFAULT 0,seed INTEGER NOT NULL DEFAULT 0,result_json TEXT NOT NULL DEFAULT '',created_at INTEGER NOT NULL,finished_at INTEGER);
CREATE INDEX IF NOT EXISTS horse_races_world ON horse_races(world_id,status,id DESC);
'''


class Horse(BaseModel):
    horse: Literal['mustang','thoroughbred','champion']


class StablePick(BaseModel):
    key:str


class RaceComp(BaseModel):
    comp:Literal['wyscigi','skoki','ujezdzanie']='wyscigi'


def _hash(*parts):
    import hashlib
    return int.from_bytes(hashlib.sha256('|'.join(str(x) for x in parts).encode()).digest()[:8],'big')


def _race_seed(wid,cid,race_id,ts):
    return _hash('race',wid,cid,race_id,ts) % (2**31)


def COMP_WEIGHTS():
    # 0.43: trzy konkurencje hipodromu — wyścigi (szybkość), skoki (wytrzymałość+spryt), ujeżdżenie (charyzma+spryt).
    return {'wyscigi':(3.0,2.5,2.0,1.5),'skoki':(1.8,3.0,1.2,2.0),'ujezdzanie':(1.0,1.5,3.0,2.5)}


def run_score(speed,stamina,charisma,cunning,seed_i,comp='wyscigi'):
    # Kondycja dżokeja (Charyzma) i spryt (tor) ważą wspólną stawkę ze statami konia;
    # rozstrojenie ±12% jest deterministyczne i opisane seedem wyścigu.
    ws=COMP_WEIGHTS().get(comp or 'wyscigi',COMP_WEIGHTS()['wyscigi'])
    base=ws[0]*speed+ws[1]*stamina+ws[2]*charisma+ws[3]*cunning
    return round(base*(0.88+0.24*((seed_i*2654435761+1013904223)%1000)/1000),2)


def resolve(entries,seed,comp='wyscigi'):
    scored=[dict(e,score=run_score(e['speed'],e['stamina'],e['charisma'],e['cunning'],seed+i*7919,comp)) for i,e in enumerate(entries)]
    scored.sort(key=lambda x:-x['score'])  # stabilnie: remis zachowuje kolejność startową
    return scored


def split_pot(pot):
    a,b,c=SPLIT
    return pot*a//100,pot*b//100,pot*c//100


def install(app,d,E):
    from . import travel as _travel
    db,now,fail,world,own,auth,rate,audit,chron=d.db,d.now,d.fail,d.world,d.own,d.auth,d.rate,d.audit,d.chron
    c=db.connect()
    try:c.executescript(SCHEMA);c.commit()
    finally:c.close()
    hip_name=_travel.name_of(HIP_DISTRICT)

    def load(c,cid):
        return json.loads(c.execute('SELECT state_json FROM characters WHERE id=?',(cid,)).fetchone()[0])

    def save(c,cid,s):
        s['lastAction']=now()
        c.execute('UPDATE characters SET state_json=? WHERE id=?',(json.dumps(s,ensure_ascii=False,separators=(',',':')),cid))

    def gated(c,ch,s):
        if E.level(s['xp'])<HIP_LEVEL:fail(409,'Hipodrom dostępny od '+str(HIP_LEVEL)+'. poziomu postaci — najpierw treningi.')
        if (ch['current_district'] or 1)!=HIP_DISTRICT:fail(409,'Tor wyścigowy jest w dzielnicy '+hip_name+' (dzielnica '+str(HIP_DISTRICT)+') — pojedź tam z mapy miasta.')
        if ch['travel_destination']:fail(409,'Jesteś w drodze — zawody poczekają na przyjazd.')

    def need_horse(s):
        if not s.get('horse'):fail(409,'Nie masz konia — kup w stajni hipodromu.')
        return s['horse']

    def entry_of(cid,c):
        ch=c.execute('SELECT nickname FROM characters WHERE id=?',(cid,)).fetchone()
        s=load(c,cid);h=s.get('horse') or dict(speed=2,stamina=2)
        j=dict(charisma=s['stats'][3],cunning=s['stats'][4])
        return dict(cid=cid,name=ch['nickname'],speed=h.get('speed',2),stamina=h.get('stamina',2),charisma=j['charisma'],cunning=j['cunning'])

    def cup(c,wid,nick,org_id):
        chron['record'](c,wid,'hipodrom',nick+' wygrywa wyścig na hipodromie','Puchar '+hip_name+' za wspólną pracę konia i dżokeja. Zawody umiejętności — bez zakładów i bez realnych pieniędzy.',hip_name)
        if org_id:
            c.execute('INSERT INTO org_investments(org_id,district,total) VALUES(?, ?, ?) ON CONFLICT(org_id,district) DO UPDATE SET total=total+?',(org_id,'Hipodrom',CUP_PRESTIGE,CUP_PRESTIGE))

    def org_of(c,cid):
        r=c.execute('SELECT org_id FROM org_members WHERE character_id=? LIMIT 1',(cid,)).fetchone()
        if r:return r[0]
        r=c.execute('SELECT id FROM organizations WHERE leader_id=? LIMIT 1',(cid,)).fetchone()  # lider założyciel przed pierwszym zapisem członkostwa
        return r[0] if r else None

    def finish(c,wid,race,entries,seed,participants):
        # wspólna rozliczanie: tabela miejsc, wypłaty 60/30/10, puchar dla zwycięzcy
        scored=resolve(entries,seed,race.get('comp','wyscigi'))
        table=[dict(name=e['name'],score=e['score']) for e in scored]
        p1,p2,p3=split_pot(race['pot']);payouts=[p1,p2,p3]
        for i,e in enumerate(scored):
            if e.get('cid') is None:continue  # dżokej NPC — nagroda zostaje na torze
            s=load(c,e['cid']);s['cash']+=payouts[i];save(c,e['cid'],s)
            net=payouts[i]-race['entry']
            E.bump(c,wid,e['cid'],now(),deeds=1,cash=net if net else 0)
        winner=scored[0]
        if winner.get('cid') is not None:cup(c,wid,winner['name'],org_of(c,winner['cid']))
        c.execute('UPDATE horse_races SET status=?,result_json=?,finished_at=? WHERE id=?',('done',json.dumps(dict(table=table,payouts=payouts),ensure_ascii=False),now(),race['id']))
        audit(c,participants,'racing.'+race['kind'],dict(race=race['id'],winner=winner['name'],pot=race['pot']))
        return dict(ok=True,table=table,payouts=payouts,pot=race['pot'])

    @app.post('/api/worlds/{wid}/racing/horse')
    def buy_horse(wid:int,data:Horse,request:Request,u=Depends(auth)):
        rate(request,'racing-horse-'+str(u['id']),10,3600000)
        row=next((h for h in HORSES if h['id']==data.horse),None)
        with db.tx() as c:
            world(c,wid,True);ch=own(c,u['id'],wid);s=load(c,ch['id'])
            if E.level(s['xp'])<row['level']:fail(409,'Ten koń wymaga poziomu '+str(row['level'])+'.')
            if (s.get('horse') or {}).get('id')==row['id']:fail(409,'Ten koń już stoi w Twojej stajni.')
            E.spend(s,cash=row['price'])
            s['horse']=dict(id=row['id'],name=row['name'],speed=row['speed'],stamina=row['stamina'])
            st=s.setdefault('horses',{})  # 0.43: stajnia pod hodowlę
            st.setdefault('stable-'+row['id'],dict(key='stable-'+row['id'],breed=row['id'],name=row['name'],speed=row['speed'],stamina=row['stamina'],gen=1))
            save(c,ch['id'],s);audit(c,u['id'],'racing.horse',dict(horse=row['id']))
            return dict(ok=True,horse=s['horse'],message='Nowy mieszkaniec stajni: '+row['name']+'.')


    @app.post('/api/worlds/{wid}/racing/breed')
    def breed(wid:int,request:Request,u=Depends(auth)):
        rate(request,'racing-breed-'+str(u['id']),5,3600000)
        with db.tx() as c:
            w=world(c,wid,True);ch=own(c,u['id'],wid);s=load(c,ch['id'])
            gated(c,ch,s)
            st=s.setdefault('horses',{})
            if s.get('horse') and ('stable-'+s['horse']['id']) not in st:  # migracja: aktywny koń zawsze w stajni
                st['stable-'+s['horse']['id']]=dict(key='stable-'+s['horse']['id'],breed=s['horse']['id'],name=s['horse']['name'],speed=s['horse']['speed'],stamina=s['horse']['stamina'],gen=1)
            if len(st)<2:fail(409,'Hodowla wymaga dwóch różnych koni w stajni — dokup drugą rasę.')
            if now()<s.get('breedAt',0):fail(409,'Stajnia odpoczywa — kolejny źrebak nie wcześniej niż po 24 h.')
            E.sync(s,now(),w['speed']);E.spend(s,cash=300)
            keys=sorted(st)[:2]
            pa,pb=st[keys[0]],st[keys[1]]
            seed=_hash('foal',ch['id'],now())%997
            sp=max(1,round((pa['speed']+pb['speed'])/2)+((seed%3)-1))
            stm=max(1,round((pa['stamina']+pb['stamina'])/2)+(((seed//3)%3)-1))
            name='Źrebak '+['Bursztyn','Fiołka','Kometka','Iskra','Zefirek'][seed%5]
            key='foal-'+str(now())[-7:]+str(seed%97)
            foal=dict(key=key,breed='foal',name=name,speed=sp,stamina=stm,gen=max(pa.get('gen',1),pb.get('gen',1))+1)
            st[key]=foal;s['breedAt']=now()+24*3600000
            save(c,ch['id'],s);audit(c,u['id'],'racing.breed',dict(foal=key))
            return dict(ok=True,foal=foal,stable=list(st.values()),message=name+' przychodzi na świat — gen '+str(foal['gen'])+'.')

    @app.post('/api/worlds/{wid}/racing/stable')
    def stable_pick(wid:int,data:StablePick,request:Request,u=Depends(auth)):
        rate(request,'racing-stable-'+str(u['id']),20,3600000)
        with db.tx() as c:
            world(c,wid,True);ch=own(c,u['id'],wid);s=load(c,ch['id'])
            st=s.get('horses') or {}
            e=st.get(data.key)
            if not e:fail(404,'Nie ma takiego konia w Twojej stajni.')
            s['horse']=dict(id=e['breed'],name=e['name'],speed=e['speed'],stamina=e['stamina'])
            save(c,ch['id'],s);audit(c,u['id'],'racing.stable',dict(key=data.key))
            return dict(ok=True,horse=s['horse'],message='Aktywny koń: '+e['name']+'.')

    @app.post('/api/worlds/{wid}/racing/npc')
    def race_npc(wid:int,data:RaceComp,request:Request,u=Depends(auth)):
        comp=data.comp if data.comp in COMP_WEIGHTS() else 'wyscigi'
        rate(request,'racing-npc-'+str(u['id']),20,3600000)
        with db.tx() as c:
            w=world(c,wid,True);ch=own(c,u['id'],wid);s=load(c,ch['id'])
            gated(c,ch,s);horse=need_horse(s)
            E.sync(s,now(),w['speed']);E.spend(s,cash=HIP_ENTRY);save(c,ch['id'],s)
            seed=_race_seed(wid,ch['id'],0,now())
            entries=[dict(cid=ch['id'],name=ch['nickname'],speed=horse['speed'],stamina=horse['stamina'],charisma=s['stats'][3],cunning=s['stats'][4])]+[dict(cid=None,**n) for n in NPC_RUNNERS[:2]]
            race=dict(id=0,kind='npc',comp=comp,pot=3*HIP_ENTRY,entry=HIP_ENTRY)
            result=finish(c,wid,race,entries,seed,ch['id'])
            result_json=json.dumps(dict(table=result['table'],payouts=result['payouts']),ensure_ascii=False)
            c.execute('INSERT INTO horse_races(world_id,kind,creator_id,creator_json,status,entry,pot,seed,result_json,created_at,finished_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(wid,comp if comp!='wyscigi' else 'npc',ch['id'],json.dumps(dict(name=ch['nickname'],horse=horse,comp=comp)),'done',HIP_ENTRY,3*HIP_ENTRY,seed,result_json,now(),now()))
            place=next((i+1 for i,e in enumerate(result['table']) if e['name']==ch['nickname']),3)
            return dict(ok=True,place=place,payout=result['payouts'][place-1],table=result['table'])

    @app.post('/api/worlds/{wid}/racing/open')
    def race_open(wid:int,request:Request,u=Depends(auth)):
        rate(request,'racing-open-'+str(u['id']),10,3600000)
        with db.tx() as c:
            w=world(c,wid,True);ch=own(c,u['id'],wid);s=load(c,ch['id'])
            gated(c,ch,s);horse=need_horse(s)
            if c.execute("SELECT 1 FROM horse_races WHERE creator_id=? AND status='open'",(ch['id'],)).fetchone():fail(409,'Masz już otwarty wyścig — poczekaj na rywala albo go odwołaj.')
            E.sync(s,now(),w['speed']);E.spend(s,cash=HIP_ENTRY);save(c,ch['id'],s)
            seed=_race_seed(wid,ch['id'],1,now())
            cu=c.execute('INSERT INTO horse_races(world_id,kind,creator_id,creator_json,status,entry,pot,seed,created_at) VALUES(?,?,?,?,?,?,?,?,?)',(wid,'duel',ch['id'],json.dumps(dict(name=ch['nickname'],speed=horse['speed'],stamina=horse['stamina'],charisma=s['stats'][3],cunning=s['stats'][4])),'open',HIP_ENTRY,HIP_ENTRY,seed,now()))
            audit(c,u['id'],'racing.open',dict(race=cu.lastrowid))
            return dict(ok=True,race=cu.lastrowid,message='Wyścig otwarty — czeka na rywala z sąsiedniej boksowni.')

    @app.get('/api/worlds/{wid}/racing/open')
    def race_list(wid:int,u=Depends(auth)):
        with db.read() as c:
            world(c,wid)
            rows=c.execute("SELECT r.id,r.entry,r.created_at,ch.nickname FROM horse_races r JOIN characters ch ON ch.id=r.creator_id WHERE r.world_id=? AND r.status='open' ORDER BY r.id DESC LIMIT 20",(wid,)).fetchall()
            return dict(open=[dict(id=r['id'],entry=r['entry'],created_at=r['created_at'],creator=r['nickname']) for r in rows])

    @app.post('/api/worlds/{wid}/racing/join/{rid}')
    def race_join(wid:int,rid:int,request:Request,u=Depends(auth)):
        rate(request,'racing-join-'+str(u['id']),20,3600000)
        with db.tx() as c:
            w=world(c,wid,True);ch=own(c,u['id'],wid);s=load(c,ch['id'])
            race=c.execute('SELECT * FROM horse_races WHERE id=? AND world_id=?',(rid,wid)).fetchone()
            if not race:fail(404,'Nie ma takiego wyścigu.')
            if race['status']!='open':fail(409,'Ten wyścig już się rozpoczął albo został zakończony.')
            if race['creator_id']==ch['id']:fail(409,'Nie rywalizujesz sam ze sobą — poczekaj na rywala.')
            gated(c,ch,s);need_horse(s)
            creator=json.loads(race['creator_json'])
            E.sync(s,now(),w['speed']);E.spend(s,cash=race['entry']);save(c,ch['id'],s)
            seed=race['seed'] or _race_seed(wid,ch['id'],rid,now())
            entries=[dict(cid=race['creator_id'],**{k:creator[k] for k in ('name','speed','stamina','charisma','cunning')}),
                     dict(cid=ch['id'],name=ch['nickname'],speed=s['horse']['speed'],stamina=s['horse']['stamina'],charisma=s['stats'][3],cunning=s['stats'][4]),
                     dict(cid=None,**NPC_RUNNERS[2])]
            race=dict(id=rid,kind='duel',pot=3*race['entry'],entry=race['entry'])
            result=finish(c,wid,race,entries,seed,ch['id'])
            c.execute('UPDATE horse_races SET opponent_id=?,pot=? WHERE id=?',(ch['id'],3*race['entry'],rid))
            place=next((i+1 for i,e in enumerate(result['table']) if e['name']==ch['nickname']),3)
            return dict(ok=True,place=place,payout=result['payouts'][place-1],table=result['table'],cash=s['cash'])

    @app.post('/api/worlds/{wid}/racing/cancel/{rid}')
    def race_cancel(wid:int,rid:int,request:Request,u=Depends(auth)):
        rate(request,'racing-cancel-'+str(u['id']),10,3600000)
        with db.tx() as c:
            world(c,wid,True);ch=own(c,u['id'],wid)
            race=c.execute('SELECT * FROM horse_races WHERE id=? AND world_id=?',(rid,wid)).fetchone()
            if not race:fail(404,'Nie ma takiego wyścigu.')
            if race['creator_id']!=ch['id']:fail(403,'Tylko autor może odwołać wyścig.')
            if race['status']!='open':fail(409,'Tego wyścigu nie da się już odwołać.')
            s=load(c,ch['id']);s['cash']+=race['entry'];save(c,ch['id'],s)
            c.execute("UPDATE horse_races SET status='cancelled',finished_at=? WHERE id=?",(now(),rid))
            audit(c,u['id'],'racing.cancel',dict(race=rid,refund=race['entry']))
            return dict(ok=True,message='Wyścig odwołany — wpisowe wróciło do kieszeni.')

    def payload(c,u,wid):
        ch=c.execute('SELECT id,nickname,state_json,current_district,travel_destination FROM characters WHERE account_id=? AND world_id=?',(u['id'],wid)).fetchone()
        if not ch:return dict(horse=None,open=[],recent=[])
        s=json.loads(ch['state_json'])
        horse=s.get('horse')
        open_races=[dict(r) for r in c.execute("SELECT r.id,r.entry,r.created_at,ch.nickname creator FROM horse_races r JOIN characters ch ON ch.id=r.creator_id WHERE r.world_id=? AND r.status='open' AND r.creator_id!=? ORDER BY r.id DESC LIMIT 8",(wid,ch['id']))]
        recent=[dict(r) for r in c.execute("SELECT kind,result_json,finished_at FROM horse_races WHERE world_id=? AND status='done' AND (creator_id=? OR opponent_id=?) ORDER BY id DESC LIMIT 5",(wid,ch['id'],ch['id']))]
        for r in recent:
            try:r['table']=json.loads(r.pop('result_json'))['table']
            except Exception:r['table']=[]
        return dict(horse=horse,open=open_races,recent=recent,entry=HIP_ENTRY,level=E.level(s['xp']),hipLevel=HIP_LEVEL,district=ch['current_district'] or 1,hipDistrict=HIP_DISTRICT,hipName=hip_name,traveling=bool(ch['travel_destination']),horses=[dict(id=h['id'],name=h['name'],price=h['price'],level=h['level'],speed=h['speed'],stamina=h['stamina']) for h in HORSES],stable=[dict(v) for v in (s.get('horses') or {}).values()],breedAt=s.get('breedAt',0))

    return dict(payload=payload,HORSES=HORSES,resolve=resolve,run_score=run_score,split_pot=split_pot,BOXING=BOXING)
