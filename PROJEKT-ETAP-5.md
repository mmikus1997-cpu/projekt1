# PROJEKT ETAP 5: walka [GDD v3.1 5.1–5.4], rewizja 2 (Klasa = Taktyka)

Gałąź `feature/gdd-v31-migration`. Diffy kodu serwera. Rewizja 2 to commity `5c50036` i `8f20b27`; wcześniejsze commity Etapu 5 podane dla kompletności.

## 5c50036: feat(combat): Klasa = Taktyka (Bokser=Presja, Obrońca=Kontrola, Szybki=Kontra), RPS klas +15%/+10% pasywki, ripost, FATIGUE od 21. rundy, logi akcji pod Fluttera, usunięcie wyboru taktyki i szablonów obrony [GDD v3.1 5.1]

```diff
commit 5c50036904594f8828b2b18a98286350ae29d97e
Author: City Empire Dev <dev@city-empire.local>
Date:   Tue Oct 6 17:16:45 2026 +0000

    feat(combat): Klasa = Taktyka (Bokser=Presja, Obrońca=Kontrola, Szybki=Kontra), RPS klas +15%/+10% pasywki, ripost, FATIGUE od 21. rundy, logi akcji pod Fluttera, usunięcie wyboru taktyki i szablonów obrony [GDD v3.1 5.1]

diff --git a/server/app.py b/server/app.py
--- a/server/app.py
+++ b/server/app.py
@@ -88,7 +88,6 @@ class Action(Strict):
  staff:str|None=None
  district:str|None=None
  amount:int|None=None
-class Tactic(Strict):style:Literal['presja','kontrola','kontra']
 
 class Invite(Strict):
  target_id:int
@@ -304,7 +303,7 @@ def create_app(db_path=None,clock=None,bootstrap_path=None,mode=None):
   eventsRecent=[dict(id=r['id'],kind=r['kind'],payload=json.loads(r['payload'] or '{}'),created_at=r['created_at'],read=r['read_at'] is not None) for r in c.execute('SELECT id,kind,payload,created_at,read_at FROM game_events WHERE character_id=? ORDER BY id DESC LIMIT 8',(ch['id'],))]  # 0.59 Chmurka
   holders={r['district']:dict(tag=r['tag'],name=r['name'],since=r['since']) for r in c.execute('SELECT t.district,t.since,o.tag,o.name FROM territory_state t JOIN organizations o ON o.id=t.org_id WHERE t.world_id=?',(wid,)).fetchall()}  # 0.45: kto rządzi dzielnicą
   # 2.1c GDD v3.1: surowce wycofane — materials/matBuy/matBase puste, zgodność ze starym UI
-  return dict(territory=holders,eventsRecent=eventsRecent,timedEvent=E.timed_event(now()),state=s,character={**{k:ch[k] for k in ('id','nickname','rating','wins','losses','draws')},'classType':ch['class_type'],'classEvolution':ch['class_evolution'],'currentLocation':ch['current_location'],'dungeonProgress':ch['dungeon_progress'],'evolutionCode':s.get('evolutionCode'),'tactic':s.get('tactic')},titles=[dict(code=r['code'],label=r['label']) for r in c.execute('SELECT code,label FROM character_titles WHERE character_id=? ORDER BY id DESC LIMIT 12',(ch['id'],))],distinction=E.distinction_state(c,ch['id'],now()),travelInfo=travel_api['info'](c,ch['id']),dungeon=dungeon_api['payload'](c,ch,s),racing=sports_api['payload'](c,u,wid),activity=[dict(r) for r in c.execute('SELECT day,deeds,cash,xp FROM char_daily WHERE character_id=? ORDER BY day DESC LIMIT 14',(ch['id'],))],world=w,serverTime=now(),away=away,notices=notices,eventsUnread=eventsUnread,dmUnread=c.execute('SELECT count(*) FROM dm_messages WHERE world_id=? AND recipient_id=? AND read_at IS NULL',(wid,ch['id'])).fetchone()[0],cityEvent=city_api['current'](c,wid),era=city_api['era'](c,wid),chronicle=chron_api['feed'](c,wid),shop=shop_api['summary'](c,u['id']),catalog=dict(items=E.ITEMS+E.DUNGEON_ITEMS,gameLooks=AV.GAME_LOOKS,ventures=list(E.VENTURES.values()),contracts=[{**x,'duration':round(x['duration']/w['speed']),'mult':E.price_mult(wid,x['id'],day),'hop':E.hop_bonus(x)} for x in E.CONTRACTS],trainingDuration=round(5*E.MINUTE/w['speed']),upgradeDuration=round(10*E.MINUTE/w['speed']),residences=E.RESIDENCES,rests=[{**r,'duration':round(r['duration']/w['speed'])} for r in E.RESTS],regenPerHour=E.regen(s)*w['speed'],vehicles=E.GARAGE,staffOffers=[dict(slot=k,**v) for k,v in E.STAFF.items()],prices={x['id']:E.price_mult(wid,x['id'],day) for x in E.CONTRACTS},tender=E.daily_tender(wid,ch['id'],day),materials={},matBuy={},matBase={},buildings=E.BUILDINGS,buildingMax=E.BUILDING_MAX,buildingCosts=E.BUILDING_UPGRADE_COST,buildingMaxes=E.BUILDING_MAXES,buildingCostsBy=E.BUILDING_COSTS,buildingVaults=E.BUILDING_VAULTS,hallCost=E.HALL_UNLOCK_COST,npcRoutes=[{**x,'duration':round(x['minutes']*E.MINUTE/w['speed'])} for x in E.NPC_ROUTES],routeVehMult=E.VEH_MULT,allyBuildings=E.ALLY_BUILDINGS,allyMax=E.ALLY_MAX,allyCost=E.ALLY_COST,districts=districts,investStep=E.INVEST_STEP,investCap=E.INVEST_CAP),message=message)
+  return dict(territory=holders,eventsRecent=eventsRecent,timedEvent=E.timed_event(now()),state=s,character={**{k:ch[k] for k in ('id','nickname','rating','wins','losses','draws')},'classType':ch['class_type'],'classEvolution':ch['class_evolution'],'currentLocation':ch['current_location'],'dungeonProgress':ch['dungeon_progress'],'evolutionCode':s.get('evolutionCode'),'tactic':combat.class_tactic(E.effective(s),ch['class_type'])},titles=[dict(code=r['code'],label=r['label']) for r in c.execute('SELECT code,label FROM character_titles WHERE character_id=? ORDER BY id DESC LIMIT 12',(ch['id'],))],distinction=E.distinction_state(c,ch['id'],now()),travelInfo=travel_api['info'](c,ch['id']),dungeon=dungeon_api['payload'](c,ch,s),racing=sports_api['payload'](c,u,wid),activity=[dict(r) for r in c.execute('SELECT day,deeds,cash,xp FROM char_daily WHERE character_id=? ORDER BY day DESC LIMIT 14',(ch['id'],))],world=w,serverTime=now(),away=away,notices=notices,eventsUnread=eventsUnread,dmUnread=c.execute('SELECT count(*) FROM dm_messages WHERE world_id=? AND recipient_id=? AND read_at IS NULL',(wid,ch['id'])).fetchone()[0],cityEvent=city_api['current'](c,wid),era=city_api['era'](c,wid),chronicle=chron_api['feed'](c,wid),shop=shop_api['summary'](c,u['id']),catalog=dict(items=E.ITEMS+E.DUNGEON_ITEMS,gameLooks=AV.GAME_LOOKS,ventures=list(E.VENTURES.values()),contracts=[{**x,'duration':round(x['duration']/w['speed']),'mult':E.price_mult(wid,x['id'],day),'hop':E.hop_bonus(x)} for x in E.CONTRACTS],trainingDuration=round(5*E.MINUTE/w['speed']),upgradeDuration=round(10*E.MINUTE/w['speed']),residences=E.RESIDENCES,rests=[{**r,'duration':round(r['duration']/w['speed'])} for r in E.RESTS],regenPerHour=E.regen(s)*w['speed'],vehicles=E.GARAGE,staffOffers=[dict(slot=k,**v) for k,v in E.STAFF.items()],prices={x['id']:E.price_mult(wid,x['id'],day) for x in E.CONTRACTS},tender=E.daily_tender(wid,ch['id'],day),materials={},matBuy={},matBase={},buildings=E.BUILDINGS,buildingMax=E.BUILDING_MAX,buildingCosts=E.BUILDING_UPGRADE_COST,buildingMaxes=E.BUILDING_MAXES,buildingCostsBy=E.BUILDING_COSTS,buildingVaults=E.BUILDING_VAULTS,hallCost=E.HALL_UNLOCK_COST,npcRoutes=[{**x,'duration':round(x['minutes']*E.MINUTE/w['speed'])} for x in E.NPC_ROUTES],routeVehMult=E.VEH_MULT,allyBuildings=E.ALLY_BUILDINGS,allyMax=E.ALLY_MAX,allyCost=E.ALLY_COST,districts=districts,investStep=E.INVEST_STEP,investCap=E.INVEST_CAP),message=message)
  def audit(c,uid,event,details):c.execute('INSERT INTO audit(actor_id,event,details,created_at) VALUES(?,?,?,?)',(uid,event,packed(details),now()))
  def check_tactic(t):
   if t not in combat.BEATS:fail(422,'Nieznana taktyka.')
@@ -340,7 +339,7 @@ def create_app(db_path=None,clock=None,bootstrap_path=None,mode=None):
   if not preview_sessions:fail(404,'Nie znaleziono zasobu.')
   routes={
    'GET':r'/(?:me|shop|worlds|account/(?:export|security|profile|rankings)|avatar/catalog|admin/(?:overview|reports|backups|worlds/[1-9][0-9]*/summary)|staff/appeals|worlds/[1-9][0-9]*/(?:state|services|npcs|assistant|milestones|players|elo-season|pvp|pvp/targets|community|sports2|racing/open|organizations/[1-9][0-9]*|chat/(?:world|organization)|dm|dm/[1-9][0-9]*)|matches/[1-9][0-9]*|ranking/global/season/[1-9][0-9]*|ranking/global/[1-9][0-9]*)',
-   'POST':r'/(?:auth/logout|worlds/[1-9][0-9]*/npcs/(?:recruit|batch|manager|feed|[1-9][0-9]*/(?:dispatch|recall|feed))|worlds/[1-9][0-9]*/services/[a-z]+/unlock|worlds/[1-9][0-9]*/server_reset|setup/claim|guardian/(?:verify|resend)|account/(?:birth-date|delete|delete/cancel|password|sessions/revoke|blocks/remove|appeals)|admin/(?:worlds|backups|notices|notices/[1-9][0-9]*/delete|events|events/[1-9][0-9]*/cancel|reports/[1-9][0-9]*/resolve)|staff/appeals/[1-9][0-9]*/resolve|organization-invites/[1-9][0-9]*/(?:accept|decline)|org-applications/[1-9][0-9]*/(?:accept|decline)|shop/(?:gate|checkout|equip|guardian|guardian/revoke)|worlds/[1-9][0-9]*/(?:character(?:/evolve)?|actions|challenges|tactic|class|distinction/claim|travel(?:/(?:arrive|speedup))?|location|avatar|wardrobe|dungeon/floor|racing(?:/(?:horse|npc|open|join/[1-9][0-9]*|cancel/[1-9][0-9]*|breed|stable))?|sports/(?:tournament|agility|archery|swim)|pvp(?:/(?:defense|attack/[1-9][0-9]*))?|organizations(?:/(?:invite|building|leave|transfer|remove-member|apply|fund|invest|announcement|role|contract(?:/cancel)?))?|chat/(?:world|organization)|dm/[1-9][0-9]*|events/read|reports|blocks)|challenges/[1-9][0-9]*/(?:accept|decline))',
+   'POST':r'/(?:auth/logout|worlds/[1-9][0-9]*/npcs/(?:recruit|batch|manager|feed|[1-9][0-9]*/(?:dispatch|recall|feed))|worlds/[1-9][0-9]*/services/[a-z]+/unlock|worlds/[1-9][0-9]*/server_reset|setup/claim|guardian/(?:verify|resend)|account/(?:birth-date|delete|delete/cancel|password|sessions/revoke|blocks/remove|appeals)|admin/(?:worlds|backups|notices|notices/[1-9][0-9]*/delete|events|events/[1-9][0-9]*/cancel|reports/[1-9][0-9]*/resolve)|staff/appeals/[1-9][0-9]*/resolve|organization-invites/[1-9][0-9]*/(?:accept|decline)|org-applications/[1-9][0-9]*/(?:accept|decline)|shop/(?:gate|checkout|equip|guardian|guardian/revoke)|worlds/[1-9][0-9]*/(?:character(?:/evolve)?|actions|challenges|class|distinction/claim|travel(?:/(?:arrive|speedup))?|location|avatar|wardrobe|dungeon/floor|racing(?:/(?:horse|npc|open|join/[1-9][0-9]*|cancel/[1-9][0-9]*|breed|stable))?|sports/(?:tournament|agility|archery|swim)|pvp(?:/(?:defense|attack/[1-9][0-9]*))?|organizations(?:/(?:invite|building|leave|transfer|remove-member|apply|fund|invest|announcement|role|contract(?:/cancel)?))?|chat/(?:world|organization)|dm/[1-9][0-9]*|events/read|reports|blocks)|challenges/[1-9][0-9]*/(?:accept|decline))',
    'PATCH':r'/admin/(?:worlds|accounts)/[1-9][0-9]*',
   }
   if not re.fullmatch(routes[data.method],data.path):fail(404,'Nieobsługiwana operacja podglądu.')
@@ -553,17 +552,7 @@ def create_app(db_path=None,clock=None,bootstrap_path=None,mode=None):
    c.execute('UPDATE characters SET state_json=? WHERE id=?',(packed(s),ch['id']));result=state_response(c,u,wid,message)
    c.execute('INSERT INTO operations VALUES(?,?,?,?,?,?)',(u['id'],wid,key,fingerprint,packed(result),now()))
    return result
- @app.post('/api/worlds/{wid}/tactic')
- def set_tactic(wid:int,data:Tactic,request:Request,u=Depends(auth)):
-  rate(request,'tactic-'+str(u['id']),10,E.HOUR)
-  # 0.41: jednorazowy wybór taktyki (Presja/Kontrola/Kontra) — przed pierwszym PvP (2 lvl); Loch (3 lvl) używa tych samych parametrów.
-  with db.tx() as c:
-   w=world(c,wid,True);ch=own(c,u['id'],wid);s=state_of(c,ch,w)
-   if s.get('tactic'):fail(409,'Taktyka została już wybrana — wybór jest jednorazowy i nieodwracalny.')
-   s['tactic']=data.style
-   c.execute('UPDATE characters SET state_json=? WHERE id=?',(json.dumps(s,ensure_ascii=False,separators=(',',':')),ch['id']))
-   audit(c,u['id'],'tactic.set',dict(style=data.style))
-   return dict(ok=True,tactic=data.style,seq=combat.style_seq(data.style),message='Taktyka wybrana — obowiązuje w każdym PvP i w całym Lochu.')
+ # 5.1 GDD v3.1: endpoint POST /api/worlds/{wid}/tactic usunięty — Klasa = Taktyka (combat.CLASS_TACTIC)
  @app.get('/api/worlds/{wid}/players')
  def players(wid:int,u=Depends(auth)):
   with db.tx() as c:season_api['ensure'](c)  # 5.4: ranking Elo zawsze z bieżącego sezonu
@@ -610,13 +599,12 @@ def create_app(db_path=None,clock=None,bootstrap_path=None,mode=None):
    if extra.blocked(c,u['id'],d['account_id']):fail(409,'Kontakt został zablokowany.')
    sa=state_of(c,a,w)
    if E.level(sa['xp'])<2:fail(409,'Wyzwania PvP odblokowują się na 2. poziomie.')
-   if not sa.get('tactic'):fail(409,'Najpierw wybierz taktykę walki — wybór jednorazowy, na wejściu w Wyzwania PvP.')
    daily_limit(c,a['id']);daily_limit(c,d['id']);pair_limit(c,a['id'],d['id'])
    if c.execute("SELECT count(*) FROM challenges WHERE attacker_id=? AND status='pending' AND expires_at>?",(a['id'],now())).fetchone()[0]>=3:fail(409,'Masz już trzy oczekujące wyzwania.')
    if c.execute("SELECT 1 FROM challenges WHERE status='pending' AND expires_at>? AND ((attacker_id=? AND defender_id=?) OR (attacker_id=? AND defender_id=?))",(now(),a['id'],d['id'],d['id'],a['id'])).fetchone():fail(409,'Wyzwanie tej pary już oczekuje.')
-   snapshot=dict(stats=E.effective(sa),tactic=sa['tactic'])
+   snapshot=dict(stats=E.effective(sa),cls=a['class_type'],tactic=combat.class_tactic(E.effective(sa),a['class_type']))  # 5.1: Klasa = Taktyka
    cid=c.execute('INSERT INTO challenges(world_id,attacker_id,defender_id,attacker_snapshot,created_at,expires_at) VALUES(?,?,?,?,?,?)',(wid,a['id'],d['id'],packed(snapshot),now(),now()+24*E.HOUR)).lastrowid
-   return dict(id=cid,message='Wysłano wyzwanie — walczy Twoja zapisana taktyka.')
+   return dict(id=cid,message='Wysłano wyzwanie — walczysz taktyką swojej klasy.')
  @app.post('/api/challenges/{cid}/accept')
  def accept(cid:int,data:Accept,u=Depends(auth)):
   with db.tx() as c:
@@ -632,8 +620,7 @@ def create_app(db_path=None,clock=None,bootstrap_path=None,mode=None):
    if extra.blocked(c,u['id'],d['account_id']):fail(409,'Kontakt został zablokowany.')
    daily_limit(c,a['id']);daily_limit(c,d['id']);pair_limit(c,a['id'],d['id'])
    snapshot=json.loads(q['attacker_snapshot']);ds=state_of(c,d,w)
-   if not ds.get('tactic'):fail(409,'Najpierw wybierz taktykę walki — wybór jednorazowy, na wejściu w Wyzwania PvP.')
-   report=combat.fight(snapshot['stats'],E.effective(ds),snapshot['tactic'],ds['tactic'],(E.level(json.loads(a['state_json']).get('xp',0)),E.level(ds.get('xp',0))))  # 5.2: HP z poziomem
+   report=combat.fight(snapshot['stats'],E.effective(ds),levels=(E.level(json.loads(a['state_json']).get('xp',0)),E.level(ds.get('xp',0))),classes=(snapshot.get('cls') or a['class_type'],d['class_type']))  # 5.1: Klasa = Taktyka; 5.2: HP z poziomem
    report['names']=[a['nickname'],d['nickname']];report['characterIds']=[a['id'],d['id']];report['ranked']=True
    report['avatars']=[AV.brief(json.loads(a['state_json'])),AV.brief(ds)]  # 0.47: awatary i sprzet zawodnikow w raporcie
    report['gear']=[AV.gear(json.loads(a['state_json'])),AV.gear(ds)]
diff --git a/server/combat.py b/server/combat.py
--- a/server/combat.py
+++ b/server/combat.py
@@ -1,7 +1,7 @@
 import math
 import random
 import secrets
-BEATS={'presja':'kontrola','kontrola':'kontra','kontra':'presja'}
+BEATS={'presja':'kontrola','kontrola':'kontra','kontra':'presja'}  # (legacy) RPS taktyk — od 5.1 RPS klas: CLASS_BEATS
 def clamp(v,a,b):return max(a,min(b,v))
 # 5.1 GDD v3.1: walka do 0 HP — bez limitu rund; bezpiecznik: po 1000 rundach remis
 MAX_ROUNDS_GUARD=1000
@@ -11,26 +11,44 @@ def hp_v2(cha,level):return 80+2*cha+level      # Walka 2.0: PvP, turnieje
 def profile(stats,level=1):
  s,i,r,c,t=[10+10*math.log(x/10) for x in stats]
  return dict(hp=hp_v1(stats[3],level),damage=50+s+.2*t,received=60/(60+i),crit=.05+.6*t/(t+40),reflex=r,effective=[s,i,r,c,t])
-def fight(a,b,ta,tb,levels=(1,1)):
- seed=secrets.randbits(32);rng=random.Random(seed);profiles=[profile(a,levels[0]),profile(b,levels[1])];hp=[p['hp'] for p in profiles];tactics=[ta,tb];events=[];winner=None
+# 5.1 GDD v3.1 (uproszczenie): Klasa = Taktyka na stałe — bez wyboru taktyki przed walką (1-Click Fights)
+CLASS_TACTIC={'Bokser':'presja','Obrońca':'kontrola','Szybki':'kontra'}
+CLASS_BEATS={'Bokser':'Obrońca','Obrońca':'Szybki','Szybki':'Bokser'}  # RPS przejęte z taktyk
+ADV_DMG=1.15      # przewaga klasowa: +15% obrażeń
+ADV_PASSIVE=1.10  # przewaga klasowa: +10% siły pasywki klasy
+FATIGUE_FROM=20   # FATIGUE: od 21. rundy +5% obrażeń obu stron za każdą rundę ponad 20
+FATIGUE_STEP=0.05
+SZYBKI_RIPOSTE=0.8  # pasywka Szybkiego (Kontra): riposta 80% szybkiego ciosu po udanym uniku — domyka trójkąt RPS
+def fatigue(round_no):return FATIGUE_STEP*max(0,round_no-FATIGUE_FROM)
+def class_tactic(stats,cls=None):return CLASS_TACTIC[pvp_class(stats,cls)]
+def class_seq(stats,cls=None):return style_seq(class_tactic(stats,cls))
+def advantage(c1,c2):return CLASS_BEATS.get(c1)==c2
+def fight(a,b,ta=None,tb=None,levels=(1,1),classes=(None,None)):
+ # ta/tb ignorowane (zgodność wywołań) — taktyka wynika z klasy
+ seed=secrets.randbits(32);rng=random.Random(seed);profiles=[profile(a,levels[0]),profile(b,levels[1])];hp=[p['hp'] for p in profiles];events=[];winner=None
+ cls=[pvp_class(a,classes[0]),pvp_class(b,classes[1])];tactics=[CLASS_TACTIC[cls[0]],CLASS_TACTIC[cls[1]]]
+ adv=[advantage(cls[0],cls[1]),advantage(cls[1],cls[0])]
  hit=[clamp(.8+.4*(profiles[i]['reflex']-profiles[1-i]['reflex'])/(profiles[i]['reflex']+profiles[1-i]['reflex']+40),.65,.95) for i in [0,1]]
  first=clamp(.5+.2*(profiles[0]['reflex']-profiles[1]['reflex'])/(profiles[0]['reflex']+profiles[1]['reflex']+40),.35,.65)
  for round_ in range(1,MAX_ROUNDS_GUARD+1):  # 5.1: do 0 HP; winner=None po bezpieczniku = remis
+  fm=1+fatigue(round_)
   for attacker in ([0,1] if rng.random()<first else [1,0]):
    defender=1-attacker;landed=rng.random()<hit[attacker];critical=False;damage=0
    if landed:
-    critical=rng.random()<profiles[attacker]['crit'];buff=1.08 if BEATS[tactics[attacker]]==tactics[defender] else 1
-    damage=max(1,profiles[attacker]['damage']*profiles[defender]['received']*rng.uniform(.85,1.15)*(2 if critical else 1)*buff);hp[defender]=max(0,hp[defender]-damage)
-   events.append(dict(round=round_,attacker=attacker,defender=defender,landed=landed,critical=critical,damage=damage,hp=hp.copy()))
+    critical=rng.random()<profiles[attacker]['crit']*(ADV_PASSIVE if adv[attacker] else 1);buff=ADV_DMG if adv[attacker] else 1
+    damage=max(1,profiles[attacker]['damage']*profiles[defender]['received']*rng.uniform(.85,1.15)*(2 if critical else 1)*buff*fm);hp[defender]=max(0,hp[defender]-damage)
+   events.append(dict(round=round_,attacker=attacker,defender=defender,landed=landed,critical=critical,damage=damage,hp=hp.copy(),fatigue=round(fm-1,2),
+    attacker_action='PUNCH_HEAVY' if critical else 'PUNCH_FAST',defender_reaction='TAKE_HIT' if landed else 'DODGE_SIDE',
+    result='CRITICAL_HIT' if critical else 'FULL_HIT' if landed else 'MISSED'))  # 5.1: logi pod animacje Fluttera
    if hp[defender]<=0:winner=attacker;break
   if winner is not None:break
- return dict(version='0.2-server',seed=seed,stats=[a,b],tactics=tactics,profiles=profiles,events=events,winner=winner,rounds=round_,finalHp=hp,authoritative=True)
+ return dict(version='0.3-class',seed=seed,stats=[a,b],classes=cls,tactics=tactics,advantage=adv,profiles=profiles,events=events,winner=winner,rounds=round_,finalHp=hp,authoritative=True)
 
 # --- 0.28 PvP 2.0: wyzwania bezpośrednie — symultaniczne 3 sloty akcji. ---
 # 1.6 GDD v3.1: wersje formuł silnika (zmiana formuł = podbicie wersji)
 ENGINE_V1_LEGACY='1.0';ENGINE_V2_LEGACY='2.0'  # wiersze bez wersji = formuły sprzed Etapu 5
-ENGINE_V1='1.1'  # fight(): sparing — 5.1/5.2: do 0 HP, HP = 200 + 5×Cha + 2×Lvl
-ENGINE_V2='2.1'  # simultaneous(): PvP, turniej — 5.1/5.2: do 0 HP, HP = 80 + 2×Cha + Lvl (Loch: HP wg 1.0)
+ENGINE_V1='1.2'  # fight(): sparing — 5.1: klasa=taktyka, RPS klas, FATIGUE, do 0 HP; 5.2: HP = 200 + 5×Cha + 2×Lvl
+ENGINE_V2='2.2'  # simultaneous(): PvP, turniej, Loch — 5.1: klasa=taktyka, RPS klas, FATIGUE, do 0 HP; 5.2: HP = 80 + 2×Cha + Lvl (Loch: HP wg 1.0)
 PVP_ACTIONS=('fast','heavy','dodge')
 PVP_DEFAULT_DEFENSE=['fast','dodge','heavy']
 # 0.41: jednorazowy styl walki („Zdecyduj, jak walczysz”) — wspólny parametr PvP i Lochu.
@@ -63,73 +81,87 @@ def pvp_class(stats,cls=None):
  return ['Bokser','Obrońca','Szybki','Obrońca','Szybki'][dom]
 def simultaneous(a_stats,d_stats,a_seq,d_seq,seed,a_cls=None,d_cls=None,a_evo=None,d_evo=None,levels=(1,1),hp_mode='v2'):
  # Kolejność w rundzie wg Refleksu (Szybki ma +3); unik blokuje cios przeciwnika,
- # Obrońca po skutecznym uniku kontratakuje 40% szybkiego ciosu; HP z kondycji (Charyzma).
- rng=random.Random(seed)
- a_seq=[PVP_ALIAS.get(x,x) for x in a_seq];d_seq=[PVP_ALIAS.get(x,x) for x in d_seq]
+ # Obrońca przy wzajemnym uniku kontratakuje 40% szybkiego ciosu; HP z Charyzmy i poziomu.
+ # 5.1: a_seq/d_seq=None → sekwencja z klasy (Klasa = Taktyka); RPS klas (+15% dmg, +10% pasywki); FATIGUE od 21. rundy.
  a_cls,d_cls=pvp_class(a_stats,a_cls),pvp_class(d_stats,d_cls)
+ a_seq=[PVP_ALIAS.get(x,x) for x in (a_seq or style_seq(CLASS_TACTIC[a_cls]))];d_seq=[PVP_ALIAS.get(x,x) for x in (d_seq or style_seq(CLASS_TACTIC[d_cls]))]
  a_evo=a_evo if a_evo in EVOLUTIONS else None
  d_evo=d_evo if d_evo in EVOLUTIONS else None
+ cls=(a_cls,d_cls);evos=(a_evo,d_evo);stats=(a_stats,d_stats)
+ adv=[advantage(a_cls,d_cls),advantage(d_cls,a_cls)]
+ pm=[ADV_PASSIVE if adv[0] else 1.0,ADV_PASSIVE if adv[1] else 1.0]  # mnożnik pasywki klasy
  hpf=hp_v1 if hp_mode=='v1' else hp_v2  # 5.2: Loch używa HP z Walki 1.0
  hp=[float(hpf(a_stats[3],levels[0])),float(hpf(d_stats[3],levels[1]))]
  hp_start=[round(hp[0],1),round(hp[1],1)]
  landed=[0,0]
  winded=[False,False]
- init=[a_stats[2]+(3 if a_cls=='Szybki' else 0),d_stats[2]+(3 if d_cls=='Szybki' else 0)]
+ init=[a_stats[2]+(3*pm[0] if a_cls=='Szybki' else 0),d_stats[2]+(3*pm[1] if d_cls=='Szybki' else 0)]
  def pot(side,act):
-  s=(a_stats,d_stats)[side];cls=(a_cls,d_cls)[side];evo=(a_evo,d_evo)[side];v=0.0
-  if act=='fast':v=5+0.45*s[0]+(1 if cls=='Szybki' else 0)
+  s=stats[side];c=cls[side];evo=evos[side];v=0.0
+  if act=='fast':v=5+0.45*s[0]+(1*pm[side] if c=='Szybki' else 0)
   elif act=='heavy':
-   v=9+0.75*s[0]+(2 if cls=='Bokser' else 0)
+   v=9+0.75*s[0]+(2*pm[side] if c=='Bokser' else 0)
    if evo=='zelazna-piesc':v*=1.15
   if evo=='mistrz-ringu' and landed[side]:v*=1+0.05*landed[side]
   if evo=='blyskawica' and winded[side]:v*=1.25
   return v
+ def strike(side,acts,fat):
+  """Jedna wymiana: (obrażenia, attacker_action, defender_reaction, result) albo None, gdy zawodnik nie atakuje."""
+  me,op=acts[side],acts[1-side];c,oc=cls[side],cls[1-side];evo,oevo=evos[side],evos[1-side]
+  if me in ('fast','heavy'):v=pot(side,me);action='PUNCH_FAST' if me=='fast' else 'PUNCH_HEAVY'
+  elif me=='dodge' and c=='Obrońca' and (op=='dodge' or (op in ('fast','heavy') and not advantage(oc,c))):v=pot(side,'fast')*(0.75 if evo=='zelazny-straznik' else 0.4)*pm[side];action='KNEE_STRIKE'  # riposta Obrońcy po uniku (dawniej tylko przy wzajemnym uniku); nie działa na klasę z przewagą (Bokser)
+  elif me=='dodge' and c=='Szybki' and op in ('fast','heavy') and not advantage(oc,c):v=pot(side,'fast')*SZYBKI_RIPOSTE*pm[side];action='KNEE_STRIKE'  # Kontra: riposta po uniku; nie działa na klasę z przewagą (Obrońca)
+  else:return None
+  reaction,result='TAKE_HIT','FULL_HIT'
+  if op=='dodge' and action!='KNEE_STRIKE':
+   through=min(1.0,fat)  # FATIGUE: zmęczony unik przepuszcza coraz większą część ciosu — gwarancja KO
+   v*=through
+   if through<=0:reaction,result=('PARRY_HAND','PARRIED') if oc=='Obrońca' else ('DODGE_SIDE','MISSED')
+   else:reaction,result='GUARD_BLOCK','BLOCKED_PARTIAL'
+  elif me==op and me in ('fast','heavy'):  # zderzenie ciosów = częściowy blok
+   v*=0.55 if me=='fast' else (1.0 if evo=='zelazna-piesc' else 0.8)
+   if evo=='murarz-ringu':v*=0.8
+   reaction,result='GUARD_BLOCK','BLOCKED_PARTIAL'
+  if oevo=='nokaut-fantom':v*=0.9
+  if v>0 and adv[side]:
+   v*=ADV_DMG
+   if result=='FULL_HIT':result='CRITICAL_HIT'  # trafienie z przewagą klasową
+  v*=1+fat
+  return round(v,1),action,reaction,result
  rounds=[];winner=None
  r=-1;streak=[0,0];quiet=0;stalemate=False
- PERIOD=math.lcm(len(a_seq),len(d_seq))  # silnik deterministyczny: 2 okresy bez obrażeń = pat na zawsze
- while hp[0]>0 and hp[1]>0 and r+1<MAX_ROUNDS_GUARD:  # 5.1: do 0 HP (dawniej 3 rundy)
-  r+=1
-  aa,dd=a_seq[r%len(a_seq)],d_seq[r%len(d_seq)];hp_before=tuple(hp)
-  # 5.1 anty-pat: trzeci unik z rzędu nie działa (zawodnik „łapie zadyszkę”) — bez tego szablon 3× unik byłby nie do pokonania
-  tired=[False,False];acts=[aa,dd]
+ PERIOD=math.lcm(len(a_seq),len(d_seq))
+ while hp[0]>0 and hp[1]>0 and r+1<MAX_ROUNDS_GUARD:  # 5.1: do 0 HP; 1000 rund = awaryjny bezpiecznik (remis)
+  r+=1;fat=fatigue(r+1)
+  aa,dd=a_seq[r%len(a_seq)],d_seq[r%len(d_seq)]
+  # anty-pat: trzeci unik z rzędu nie działa (zadyszka)
+  tired=[False,False];raw=[aa,dd]
   for i in (0,1):
-   if acts[i]=='dodge':
+   if raw[i]=='dodge':
     tired[i]=streak[i]>=2;streak[i]+=1
    else:streak[i]=0
-  if tired[0]:aa='tired'
-  if tired[1]:dd='tired'
-  cf=0.75 if a_evo=='zelazny-straznik' else 0.4
-  df=0.75 if d_evo=='zelazny-straznik' else 0.4
-  pot_a=pot(0,aa) if dd!='dodge' else (round(pot(0,'fast')*cf,1) if a_cls=='Obrońca' and aa=='dodge' else 0)
-  pot_d=pot(1,dd) if aa!='dodge' else (round(pot(1,'fast')*df,1) if d_cls=='Obrońca' and dd=='dodge' else 0)
-  if aa=='fast' and dd=='fast':
-   pot_a=round(pot_a*0.55,1);pot_d=round(pot_d*0.55,1)
-   if a_evo=='murarz-ringu':pot_a=round(pot_a*0.8,1)
-   if d_evo=='murarz-ringu':pot_d=round(pot_d*0.8,1)
-  if aa=='heavy' and dd=='heavy':
-   pot_a=round(pot_a*(1.0 if a_evo=='zelazna-piesc' else 0.8),1);pot_d=round(pot_d*(1.0 if d_evo=='zelazna-piesc' else 0.8),1)
-   if a_evo=='murarz-ringu':pot_a=round(pot_a*0.8,1)
-   if d_evo=='murarz-ringu':pot_d=round(pot_d*0.8,1)
-  if a_evo=='nokaut-fantom':pot_d=round(pot_d*0.9,1)
-  if d_evo=='nokaut-fantom':pot_a=round(pot_a*0.9,1)
+  acts=[('tired' if tired[i] else raw[i]) for i in (0,1)]
+  ex=[strike(0,acts,fat),strike(1,acts,fat)]
   first=0 if init[0]>=init[1] else 1
-  order=[(first,pot_a if first==0 else pot_d),(1-first,pot_d if first==0 else pot_a)]
-  dealt=[0,0]
-  for side,value in order:
-   opp=1-side
-   if hp[side]<=0 or hp[opp]<=0 or value<=0:continue  # 5.1: znokautowany w tej rundzie nie oddaje ciosu
-   hp[opp]=max(0,hp[opp]-value);dealt[side]=value
-  if a_evo=='nokaut-fantom' and aa=='dodge' and dd!='dodge':hp[0]=min(hp_start[0],round(hp[0]+15,1))
-  if d_evo=='nokaut-fantom' and dd=='dodge' and aa!='dodge':hp[1]=min(hp_start[1],round(hp[1]+15,1))
-  if winded[0] and dealt[0]>0:winded[0]=False
-  if winded[1] and dealt[1]>0:winded[1]=False
-  winded[0]=aa=='dodge' and dd!='dodge';winded[1]=dd=='dodge' and aa!='dodge'
+  dealt=[0,0];exchanges=[]
+  for side in (first,1-first):
+   e=ex[side];opp=1-side
+   if e is None or hp[side]<=0 or hp[opp]<=0:continue  # znokautowany w tej rundzie nie oddaje ciosu
+   v=e[0]
+   if v>0:hp[opp]=max(0,round(hp[opp]-v,1));dealt[side]=v
+   exchanges.append(dict(striker=side,attacker_action=e[1],defender_reaction=e[2],result=e[3],damage=v,hp=[round(hp[0],1),round(hp[1],1)]))
+  if a_evo=='nokaut-fantom' and acts[0]=='dodge' and acts[1]!='dodge' and hp[0]>0:hp[0]=min(hp_start[0],round(hp[0]+15,1))
+  if d_evo=='nokaut-fantom' and acts[1]=='dodge' and acts[0]!='dodge' and hp[1]>0:hp[1]=min(hp_start[1],round(hp[1]+15,1))
+  winded[0]=acts[0]=='dodge' and acts[1]!='dodge';winded[1]=acts[1]=='dodge' and acts[0]!='dodge'
   if dealt[0]>0:landed[0]+=1
   if dealt[1]>0:landed[1]+=1
-  rounds.append(dict(r=r+1,a=acts[0],d=acts[1],tired=tired,pot_a=pot_a,pot_d=pot_d,dealt=[dealt[0],dealt[1]],hp=[round(hp[0],1),round(hp[1],1)],first=first))
-  quiet=quiet+1 if tuple(hp)==hp_before else 0
-  if quiet>=2*PERIOD+2:stalemate=True;break  # 5.1: wczesny remis — wynik identyczny jak po 1000 rundach, bez pustego raportu
- winner=None if hp[0]>0 and hp[1]>0 else (0 if hp[0]>0 else 1)  # 5.1: bezpiecznik 1000 rund = remis
+  head=exchanges[0] if exchanges else dict(attacker_action=None,defender_reaction=None,result=None)
+  rounds.append(dict(r=r+1,a=raw[0],d=raw[1],tired=tired,fatigue=round(fat,2),pot_a=ex[0][0] if ex[0] else 0,pot_d=ex[1][0] if ex[1] else 0,dealt=[dealt[0],dealt[1]],hp=[round(hp[0],1),round(hp[1],1)],first=first,
+   attacker_action=head['attacker_action'],defender_reaction=head['defender_reaction'],result=head['result'],exchanges=exchanges))  # 5.1: logi pod animacje Fluttera
+  # pat dowodliwy dopiero przy pełnym zmęczeniu (unik nic nie blokuje): 2 okresy sekwencji bez obrażeń = obie strony bierne na zawsze
+  quiet=quiet+1 if fat>=1 and dealt==[0,0] else 0
+  if quiet>=2*PERIOD+2:stalemate=True;break
+ winner=None if hp[0]>0 and hp[1]>0 else (0 if hp[0]>0 else 1)  # remis tylko po bezpieczniku 1000 rund
  # 0.48: tor prezentacji — zdarzenia 1:1 z autorytatywnym przebiegiem (tylko odczyt rund),
  # żeby odtworzenie animacji pokazywało dokładnie tę walkę, którą rozstrzygnął serwer.
  events=[];run=list(hp_start)
@@ -143,4 +175,4 @@ def simultaneous(a_stats,d_stats,a_seq,d_seq,seed,a_cls=None,d_cls=None,a_evo=No
    run[opp]=round(min(run[opp],start[opp]),1)
    events.append(dict(round=rd['r'],attacker=side,defender=opp,landed=True,critical=False,damage=dealt,hp=[round(x,1) for x in run]))
  profiles=[dict(hp=hp_start[0]),dict(hp=hp_start[1])]
- return dict(stalemate=stalemate,version='0.5-evo1',classes=[a_cls,d_cls],evolutions=[a_evo,d_evo],seqs=[a_seq,d_seq],seed=seed,rounds=rounds,winner=winner,finalHp=[round(hp[0],1),round(hp[1],1)],hpStart=hp_start,initiative=[init[0],init[1]],authoritative=True,events=events,profiles=profiles)
+ return dict(stalemate=stalemate,version='0.6-class',classes=[a_cls,d_cls],tactics=[CLASS_TACTIC[a_cls],CLASS_TACTIC[d_cls]],advantage=adv,evolutions=[a_evo,d_evo],seqs=[a_seq,d_seq],seed=seed,rounds=rounds,winner=winner,finalHp=[round(hp[0],1),round(hp[1],1)],hpStart=hp_start,initiative=[init[0],init[1]],authoritative=True,events=events,profiles=profiles)
diff --git a/server/dungeon.py b/server/dungeon.py
--- a/server/dungeon.py
+++ b/server/dungeon.py
@@ -43,7 +43,7 @@ def install(app,d,E,combat):
         progress=ch['dungeon_progress'] or 0
         nxt=None if progress>=100 else FLOORS[progress//10]
         return dict(progress=progress,atGate=ch['current_location']=='brama-lochow',completed=progress>=100,
-            locked=E.level(s['xp'])<3,reqLevel=3,tactic=s.get('tactic'),tacticSet=bool(s.get('tactic')),
+            locked=E.level(s['xp'])<3,reqLevel=3,tactic=combat.class_tactic(E.effective(s),ch['class_type']),tacticSet=True,  # 5.1: Klasa = Taktyka
             nextFloor=None if not nxt else dict(n=nxt['n'],name=nxt['name'],cls=nxt['cls'],cash=30+30*nxt['n'],xp=8+4*nxt['n']),
             loot=[i for i in s.get('dungeonLoot',[])],lootNames={i['id']:i['name'] for i in E.DUNGEON_ITEMS})
 
@@ -56,8 +56,7 @@ def install(app,d,E,combat):
             if (ch['current_location'] or 'ulica')!='brama-lochow':fail(409,'Wejście do Lochu prowadzi spod Bramy Lochu — zmień lokację w profilu.')
             s0=json.loads(ch['state_json'])  # 0.41: Loch od 3. poziomu, parametry walki = zapisana taktyka z PvP
             if E.level(s0['xp'])<3:fail(409,'Loch odblokowuje się na 3. poziomie — zdobyj XP w kontraktach.')
-            if not s0.get('tactic'):fail(409,'Najpierw wybierz taktykę walki — wybór jednorazowy, tak jak w PvP.')
-            seq=combat.style_seq(s0['tactic'])
+            seq=combat.class_seq(E.effective(s0),ch['class_type'])  # 5.1 GDD v3.1: Klasa = Taktyka
             progress=ch['dungeon_progress'] or 0
             if progress>=100:fail(409,'Loch opanowany w 100% — poczekaj na nowy zjazd.')
             npc=FLOORS[progress//10]
diff --git a/server/economy.py b/server/economy.py
--- a/server/economy.py
+++ b/server/economy.py
@@ -295,6 +295,7 @@ def business_sync(b,from_,now,rates,speed,boost_until=0,cap_mult=1.0):
   accrue(a,z,boost_until>=z)
   if u and z==u['end']:b['level']=u['target'];b['upgrade']=None
 def sync(s,now,speed):
+ for k in ('tactic','pvpDefense'):s.pop(k,None)  # 5.1 GDD v3.1: Klasa = Taktyka — wybór taktyki i szablony obrony usunięte ze stanu (migracja leniwa)
  for key,value in (('residence',None),('rest',None),('lastAction',now),('vehicle',None),('garage',[]),('garageUp',{}),('staff',{}),('buildings',dict(BUILDING_START)),('invested',{}),('tenderDone',None),('horse',None),('pvpDefense',None),('npcRoutes',dict(runs=[],done=0,cash=0,xp=0))):
   # States saved by earlier development builds predate 0.8/0.9 keys; absent keys default safely.
   if key not in s:s[key]=value
diff --git a/server/pvp.py b/server/pvp.py
--- a/server/pvp.py
+++ b/server/pvp.py
@@ -2,7 +2,7 @@
 
 0.42 Auto-atak: atak rozstrzyga się OD RAZU na zapisanych taktykach obu stron (payload
 ignorowany) — obrońca nie musi być online ani nic potwierdzać; jego taktyka z 0.41 jest jego
-głosem. Kolejność obrony: taktyka > szablon pvpDefense (legacy) > sekwencja zrównoważona.
+głosem. 5.1 GDD v3.1: Klasa = Taktyka (Bokser=Presja, Obrońca=Kontrola, Szybki=Kontra) — bez szablonów.
 Silnik symultaniczny stoi w combat.simultaneous (kolejność wg Refleksu, pasywki klasowe:
 Bokser/Szybki/Obrońca). Obrońca walczy według własnego zapisanego szablonu taktycznego
 (state_json.pvpDefense), więc atak rozstrzyga się od razu — bez czekania na akceptację.
@@ -26,9 +26,6 @@ PVP_REWARDS={'win':dict(cash=500,xp=50,prestige=1),'loss':dict(cash=100,xp=10,pr
 class Attack(BaseModel):
     seq:list[str]|None=None  # 0.42: zignorowane — walka zawsze na zapisanych taktykach (Auto-atak)
 
-class Defense(BaseModel):
-    seq:list[str]=Field(min_length=3,max_length=3)
-
 
 def install(app,d,E,combat,city):
     from . import avatar as avatar_mod
@@ -71,15 +68,7 @@ def install(app,d,E,combat,city):
                 out.append(dict(id=r['id'],nickname=r['nickname'],level=E.level(xp),cls=combat.pvp_class(stats,r['class_type']),rating=int(round(r['rating']/10)*10),skin=r['skin'],district=r['current_district'] or 1,avatar=av))
             return dict(targets=out,note='Szacunkowy rating i klasa — dokładne statystyki pozostają tajemnicą do pierwszej rundy.')
 
-    @app.post('/api/worlds/{wid}/pvp/defense')
-    def set_defense(wid:int,data:Defense,request:Request,u=Depends(auth)):
-        rate(request,'pvp-defense-'+str(u['id']),10,3600000)
-        seq=norm(data.seq)
-        with db.tx() as c:
-            world(c,wid,True);ch=own(c,u['id'],wid)
-            s=load(c,ch['id']);s['pvpDefense']=seq;save(c,ch['id'],s)
-            audit(c,u['id'],'pvp.defense',dict(seq=seq))
-            return dict(ok=True,defense=seq,message='Szablon obrony zapisany — Twoi przeciwnicy zobaczą go w akcji.')
+    # 5.1 GDD v3.1: POST /pvp/defense (szablon obrony) usunięty — Klasa = Taktyka
 
     @app.post('/api/worlds/{wid}/pvp/attack/{target_id}')
     def attack(wid:int,target_id:int,data:Attack,request:Request,u=Depends(auth)):
@@ -96,14 +85,10 @@ def install(app,d,E,combat,city):
             d.limit(c,a['id']);d.limit(c,t['id']);d.pair(c,a['id'],t['id'])  # 5.3: limit pary także w PvP 2.0
             s_a=load(c,a['id']);s_d=load(c,t['id'])
             if E.level(s_a.get('xp') or 0)<2:fail(409,'Wyzwania PvP odblokowują się na 2. poziomie.')
-            if not s_a.get('tactic'):fail(409,'Najpierw wybierz taktykę walki — wybór jednorazowy, na wejściu w Wyzwania PvP.')
-            a_seq=combat.style_seq(s_a['tactic'])
-            fb=s_d.get('tactic') or s_d.get('pvpDefense') or 'zrowna'  # taktyka > szablon (legacy) > zrównoważona
-            if isinstance(fb,str):d_tac=fb if fb in combat.STYLE else 'zrowna';d_seq=combat.style_seq(d_tac)
-            else:d_tac='szablon';d_seq=list(fb)
-            report=combat.simultaneous(E.effective(s_a),E.effective(s_d),a_seq,list(d_seq),secrets.randbits(32),a_cls=a['class_type'],d_cls=t['class_type'],a_evo=s_a.get('evolutionCode'),d_evo=s_d.get('evolutionCode'),levels=(E.level(s_a.get('xp') or 0),E.level(s_d.get('xp') or 0)))
+            # 5.1 GDD v3.1: Klasa = Taktyka — sekwencje obu stron wynikają z klas (None → combat.CLASS_TACTIC)
+            report=combat.simultaneous(E.effective(s_a),E.effective(s_d),None,None,secrets.randbits(32),a_cls=a['class_type'],d_cls=t['class_type'],a_evo=s_a.get('evolutionCode'),d_evo=s_d.get('evolutionCode'),levels=(E.level(s_a.get('xp') or 0),E.level(s_d.get('xp') or 0)))
             report['names']=[a['nickname'],t['nickname']];report['characterIds']=[a['id'],t['id']];report['ranked']=True
-            report['tactics']=[s_a['tactic'],d_tac];report['stats']=[E.effective(s_a),E.effective(s_d)]
+            report['stats']=[E.effective(s_a),E.effective(s_d)]
             report['avatars']=[avatar_mod.brief(s_a),avatar_mod.brief(s_d)];report['gear']=[avatar_mod.gear(s_a),avatar_mod.gear(s_d)]  # 0.47
             expected=1/(1+10**((t['rating']-a['rating'])/400))
             score=1 if report['winner']==0 else 0 if report['winner']==1 else 0.5
@@ -116,7 +101,7 @@ def install(app,d,E,combat,city):
                 reward(c,t['id'],'draw' if report['winner'] is None else 'win' if report['winner']==1 else 'loss')]
             report['rewards']=rw
             bid=c.execute('INSERT INTO pvp_battles(world_id,attacker_id,defender_id,report_json,rating_json,created_at,combat_version) VALUES(?,?,?,?,?,?,?)',(wid,a['id'],t['id'],json.dumps(report,ensure_ascii=False,separators=(',',':')),json.dumps([change,-change]),now(),combat.ENGINE_V2)).lastrowid
-            city['emit'](c,wid,[t['id']],'pvp_attacked',dict(attacker=a['nickname'],result='win' if report['winner']==1 else 'loss' if report['winner']==0 else 'draw',change=round(-change,1),seq=a_seq,battle=bid))
+            city['emit'](c,wid,[t['id']],'pvp_attacked',dict(attacker=a['nickname'],result='win' if report['winner']==1 else 'loss' if report['winner']==0 else 'draw',change=round(-change,1),seq=report['seqs'][0],battle=bid))
             audit(c,u['id'],'pvp.attack',dict(battle=bid,target=t['id'],winner=report['winner']))
             return dict(ok=True,battle=bid,report=report,ratingChanges=[change,-change],rewards=rw,combat_version=combat.ENGINE_V2)
 
diff --git a/server/sports2.py b/server/sports2.py
--- a/server/sports2.py
+++ b/server/sports2.py
@@ -30,7 +30,6 @@ def install(app,d,E,combat):
     def combat_ready(c,ch):
         s=load(c,ch['id'])
         if E.level(s.get('xp') or 0)<2:fail(409,'Wyzwania PvP odblokowują się na 2. poziomie.')
-        if not s.get('tactic'):fail(409,'Najpierw wybierz taktykę walki — wybór jednorazowy, na wejściu w Wyzwania PvP.')
         if s.get('travel_destination'):fail(409,'Jesteś w drodze — zawody poczekają na przyjazd.')
         return s
 
@@ -49,7 +48,7 @@ def install(app,d,E,combat):
             if t['runs']>=2:fail(409,'Limit: 2 turnieje na dobę UTC — ring musi odetchnąć.')
             s['cash']-=200;s['energy']-=30;t['runs']+=1
             a_cls=combat.pvp_class(s['stats'],ch['class_type']) if hasattr(combat,'pvp_class') else 'Bokser'
-            seq=combat.style_seq(s['tactic'])
+            seq=combat.class_seq(E.effective(s),ch['class_type'])  # 5.1 GDD v3.1: Klasa = Taktyka
             rounds=[];wins=0
             for i,(name,npc_stats,npc_seq) in enumerate(TOURN_NPC):
                 rep=combat.simultaneous(E.effective(s),npc_stats,seq,list(npc_seq),now()+i*7919,a_cls=ch['class_type'],d_cls=None,levels=(E.level(s['xp']),E.level(s['xp'])))  # 5.2: rywal turnieju na poziomie gracza
```

## 8f20b27: feat(pvp): limit pary podniesiony do 4 walk na 24 h [GDD v3.1 5.3]

```diff
commit 8f20b2709f08b9821371d745e81287eacc811cc8
Author: City Empire Dev <dev@city-empire.local>
Date:   Tue Oct 6 17:16:54 2026 +0000

    feat(pvp): limit pary podniesiony do 4 walk na 24 h [GDD v3.1 5.3]

diff --git a/server/app.py b/server/app.py
--- a/server/app.py
+++ b/server/app.py
@@ -308,7 +308,7 @@ def create_app(db_path=None,clock=None,bootstrap_path=None,mode=None):
  def check_tactic(t):
   if t not in combat.BEATS:fail(422,'Nieznana taktyka.')
  RANKED_DAILY=15  # 5.3 GDD v3.1: wspólny limit walk rankingowych (wyzwania 1.0 + PvP 2.0) na dobę UTC
- PAIR_MAX=3       # 5.3: z tym samym przeciwnikiem najwyżej 3 walki w oknie 24 h (4. zablokowana) — decyzja usera
+ PAIR_MAX=4       # 5.3 (spec rev. 2): z tym samym przeciwnikiem najwyżej 4 walki w oknie 24 h (5. zablokowana)
  def daily_limit(c,cid):
   season_api['ensure'](c)  # 5.4: przed walką rankingową zamknij zakończony sezon Elo (leniwie)
   day=now()//(24*E.HOUR)*(24*E.HOUR)
```

## 7cac8ac: feat(combat): walka do 0 HP z bezpiecznikiem 1000 rund, nowe HP 1.0/2.0, anty-pat uniku, KO bez kontry [GDD v3.1 5.1–5.2]

```diff
commit 7cac8ac065125183d3c13ae1f9f6bd98a71ac04c
Author: City Empire Dev <dev@city-empire.local>
Date:   Tue Oct 6 16:36:13 2026 +0000

    feat(combat): walka do 0 HP z bezpiecznikiem 1000 rund, nowe HP 1.0/2.0, anty-pat uniku, KO bez kontry [GDD v3.1 5.1–5.2]

diff --git a/server/app.py b/server/app.py
--- a/server/app.py
+++ b/server/app.py
@@ -626,7 +626,7 @@ def create_app(db_path=None,clock=None,bootstrap_path=None,mode=None):
    daily_limit(c,a['id']);daily_limit(c,d['id']);pair_limit(c,a['id'],d['id'])
    snapshot=json.loads(q['attacker_snapshot']);ds=state_of(c,d,w)
    if not ds.get('tactic'):fail(409,'Najpierw wybierz taktykę walki — wybór jednorazowy, na wejściu w Wyzwania PvP.')
-   report=combat.fight(snapshot['stats'],E.effective(ds),snapshot['tactic'],ds['tactic'])
+   report=combat.fight(snapshot['stats'],E.effective(ds),snapshot['tactic'],ds['tactic'],(E.level(json.loads(a['state_json']).get('xp',0)),E.level(ds.get('xp',0))))  # 5.2: HP z poziomem
    report['names']=[a['nickname'],d['nickname']];report['characterIds']=[a['id'],d['id']];report['ranked']=True
    report['avatars']=[AV.brief(json.loads(a['state_json'])),AV.brief(ds)]  # 0.47: awatary i sprzet zawodnikow w raporcie
    report['gear']=[AV.gear(json.loads(a['state_json'])),AV.gear(ds)]
@@ -650,7 +650,7 @@ def create_app(db_path=None,clock=None,bootstrap_path=None,mode=None):
   with db.read() as c:
    r=c.execute('SELECT m.*,a.account_id a_uid,d.account_id d_uid FROM matches m JOIN characters a ON a.id=m.attacker_id JOIN characters d ON d.id=m.defender_id WHERE m.id=?',(mid,)).fetchone()
    if not r or u['id'] not in (r['a_uid'],r['d_uid']):fail(404,'Raport nie jest dostępny.')
-   return {'report':json.loads(r['report_json']),'match_id':mid,'combat_version':r['combat_version'] or combat.ENGINE_V1}  # 1.6: fallback dla starych walk
+   return {'report':json.loads(r['report_json']),'match_id':mid,'combat_version':r['combat_version'] or combat.ENGINE_V1_LEGACY}  # 1.6: fallback dla starych walk (formuły sprzed 5.x)
  @app.get('/api/admin/worlds/{wid}/summary')
  def world_summary(wid:int,u=Depends(admin)):
   # wyłącznie odczyt: obraz świata dla administratora (ludzie, cele, orgs, kronika, dev-sklep)
diff --git a/server/combat.py b/server/combat.py
--- a/server/combat.py
+++ b/server/combat.py
@@ -3,14 +3,19 @@ import random
 import secrets
 BEATS={'presja':'kontrola','kontrola':'kontra','kontra':'presja'}
 def clamp(v,a,b):return max(a,min(b,v))
-def profile(stats):
+# 5.1 GDD v3.1: walka do 0 HP — bez limitu rund; bezpiecznik: po 1000 rundach remis
+MAX_ROUNDS_GUARD=1000
+# 5.2 GDD v3.1: nowe HP (Charyzma = surowa statystyka efektywna, Level = poziom postaci)
+def hp_v1(cha,level):return 200+5*cha+2*level   # Walka 1.0: sparing, Loch
+def hp_v2(cha,level):return 80+2*cha+level      # Walka 2.0: PvP, turnieje
+def profile(stats,level=1):
  s,i,r,c,t=[10+10*math.log(x/10) for x in stats]
- return dict(hp=500+10*c,damage=50+s+.2*t,received=60/(60+i),crit=.05+.6*t/(t+40),reflex=r,effective=[s,i,r,c,t])
-def fight(a,b,ta,tb):
- seed=secrets.randbits(32);rng=random.Random(seed);profiles=[profile(a),profile(b)];hp=[p['hp'] for p in profiles];tactics=[ta,tb];events=[];winner=None
+ return dict(hp=hp_v1(stats[3],level),damage=50+s+.2*t,received=60/(60+i),crit=.05+.6*t/(t+40),reflex=r,effective=[s,i,r,c,t])
+def fight(a,b,ta,tb,levels=(1,1)):
+ seed=secrets.randbits(32);rng=random.Random(seed);profiles=[profile(a,levels[0]),profile(b,levels[1])];hp=[p['hp'] for p in profiles];tactics=[ta,tb];events=[];winner=None
  hit=[clamp(.8+.4*(profiles[i]['reflex']-profiles[1-i]['reflex'])/(profiles[i]['reflex']+profiles[1-i]['reflex']+40),.65,.95) for i in [0,1]]
  first=clamp(.5+.2*(profiles[0]['reflex']-profiles[1]['reflex'])/(profiles[0]['reflex']+profiles[1]['reflex']+40),.35,.65)
- for round_ in range(1,101):
+ for round_ in range(1,MAX_ROUNDS_GUARD+1):  # 5.1: do 0 HP; winner=None po bezpieczniku = remis
   for attacker in ([0,1] if rng.random()<first else [1,0]):
    defender=1-attacker;landed=rng.random()<hit[attacker];critical=False;damage=0
    if landed:
@@ -23,8 +28,9 @@ def fight(a,b,ta,tb):
 
 # --- 0.28 PvP 2.0: wyzwania bezpośrednie — symultaniczne 3 sloty akcji. ---
 # 1.6 GDD v3.1: wersje formuł silnika (zmiana formuł = podbicie wersji)
-ENGINE_V1='1.0'  # fight(): sparing, Loch (do 100 rund)
-ENGINE_V2='2.0'  # simultaneous(): PvP 2.0, turniej (3 rundy)
+ENGINE_V1_LEGACY='1.0';ENGINE_V2_LEGACY='2.0'  # wiersze bez wersji = formuły sprzed Etapu 5
+ENGINE_V1='1.1'  # fight(): sparing — 5.1/5.2: do 0 HP, HP = 200 + 5×Cha + 2×Lvl
+ENGINE_V2='2.1'  # simultaneous(): PvP, turniej — 5.1/5.2: do 0 HP, HP = 80 + 2×Cha + Lvl (Loch: HP wg 1.0)
 PVP_ACTIONS=('fast','heavy','dodge')
 PVP_DEFAULT_DEFENSE=['fast','dodge','heavy']
 # 0.41: jednorazowy styl walki („Zdecyduj, jak walczysz”) — wspólny parametr PvP i Lochu.
@@ -55,7 +61,7 @@ def pvp_class(stats,cls=None):
   if cls in ('Bokser','Obrońca','Szybki'):return cls
  dom=max(range(5),key=lambda i:stats[i])
  return ['Bokser','Obrońca','Szybki','Obrońca','Szybki'][dom]
-def simultaneous(a_stats,d_stats,a_seq,d_seq,seed,a_cls=None,d_cls=None,a_evo=None,d_evo=None):
+def simultaneous(a_stats,d_stats,a_seq,d_seq,seed,a_cls=None,d_cls=None,a_evo=None,d_evo=None,levels=(1,1),hp_mode='v2'):
  # Kolejność w rundzie wg Refleksu (Szybki ma +3); unik blokuje cios przeciwnika,
  # Obrońca po skutecznym uniku kontratakuje 40% szybkiego ciosu; HP z kondycji (Charyzma).
  rng=random.Random(seed)
@@ -63,7 +69,8 @@ def simultaneous(a_stats,d_stats,a_seq,d_seq,seed,a_cls=None,d_cls=None,a_evo=No
  a_cls,d_cls=pvp_class(a_stats,a_cls),pvp_class(d_stats,d_cls)
  a_evo=a_evo if a_evo in EVOLUTIONS else None
  d_evo=d_evo if d_evo in EVOLUTIONS else None
- hp=[80+1.5*a_stats[3],80+1.5*d_stats[3]]
+ hpf=hp_v1 if hp_mode=='v1' else hp_v2  # 5.2: Loch używa HP z Walki 1.0
+ hp=[float(hpf(a_stats[3],levels[0])),float(hpf(d_stats[3],levels[1]))]
  hp_start=[round(hp[0],1),round(hp[1],1)]
  landed=[0,0]
  winded=[False,False]
@@ -78,8 +85,18 @@ def simultaneous(a_stats,d_stats,a_seq,d_seq,seed,a_cls=None,d_cls=None,a_evo=No
   if evo=='blyskawica' and winded[side]:v*=1.25
   return v
  rounds=[];winner=None
- for r in range(3):
+ r=-1;streak=[0,0]
+ while hp[0]>0 and hp[1]>0 and r+1<MAX_ROUNDS_GUARD:  # 5.1: do 0 HP (dawniej 3 rundy)
+  r+=1
   aa,dd=a_seq[r%len(a_seq)],d_seq[r%len(d_seq)]
+  # 5.1 anty-pat: trzeci unik z rzędu nie działa (zawodnik „łapie zadyszkę”) — bez tego szablon 3× unik byłby nie do pokonania
+  tired=[False,False];acts=[aa,dd]
+  for i in (0,1):
+   if acts[i]=='dodge':
+    tired[i]=streak[i]>=2;streak[i]+=1
+   else:streak[i]=0
+  if tired[0]:aa='tired'
+  if tired[1]:dd='tired'
   cf=0.75 if a_evo=='zelazny-straznik' else 0.4
   df=0.75 if d_evo=='zelazny-straznik' else 0.4
   pot_a=pot(0,aa) if dd!='dodge' else (round(pot(0,'fast')*cf,1) if a_cls=='Obrońca' and aa=='dodge' else 0)
@@ -99,7 +116,7 @@ def simultaneous(a_stats,d_stats,a_seq,d_seq,seed,a_cls=None,d_cls=None,a_evo=No
   dealt=[0,0]
   for side,value in order:
    opp=1-side
-   if hp[opp]<=0 or value<=0:continue
+   if hp[side]<=0 or hp[opp]<=0 or value<=0:continue  # 5.1: znokautowany w tej rundzie nie oddaje ciosu
    hp[opp]=max(0,hp[opp]-value);dealt[side]=value
   if a_evo=='nokaut-fantom' and aa=='dodge' and dd!='dodge':hp[0]=min(hp_start[0],round(hp[0]+15,1))
   if d_evo=='nokaut-fantom' and dd=='dodge' and aa!='dodge':hp[1]=min(hp_start[1],round(hp[1]+15,1))
@@ -108,9 +125,8 @@ def simultaneous(a_stats,d_stats,a_seq,d_seq,seed,a_cls=None,d_cls=None,a_evo=No
   winded[0]=aa=='dodge' and dd!='dodge';winded[1]=dd=='dodge' and aa!='dodge'
   if dealt[0]>0:landed[0]+=1
   if dealt[1]>0:landed[1]+=1
-  rounds.append(dict(r=r+1,a=aa,d=dd,pot_a=pot_a,pot_d=pot_d,dealt=[dealt[0],dealt[1]],hp=[round(hp[0],1),round(hp[1],1)],first=first))
- if hp[0]==hp[1]:winner=0 if init[0]>=init[1] else 1
- else:winner=0 if hp[0]>hp[1] else 1
+  rounds.append(dict(r=r+1,a=acts[0],d=acts[1],tired=tired,pot_a=pot_a,pot_d=pot_d,dealt=[dealt[0],dealt[1]],hp=[round(hp[0],1),round(hp[1],1)],first=first))
+ winner=None if hp[0]>0 and hp[1]>0 else (0 if hp[0]>0 else 1)  # 5.1: bezpiecznik 1000 rund = remis
  # 0.48: tor prezentacji — zdarzenia 1:1 z autorytatywnym przebiegiem (tylko odczyt rund),
  # żeby odtworzenie animacji pokazywało dokładnie tę walkę, którą rozstrzygnął serwer.
  events=[];run=list(hp_start)
diff --git a/server/dungeon.py b/server/dungeon.py
--- a/server/dungeon.py
+++ b/server/dungeon.py
@@ -66,7 +66,7 @@ def install(app,d,E,combat):
             cunning=E.effective(s)[4]
             npc_red=min(6,max(0,cunning-10)//10*2)  # 0.35: Spryt — NPC traci 2% potencjału za każde 10 pkt (cap 6%)
             npc_stats=[round(v*(100-npc_red)/100,1) for v in npc['stats']]
-            report=combat.simultaneous(E.effective(s),npc_stats,seq,list(npc['seq']),secrets.randbits(32),a_cls=ch['class_type'],d_cls=npc['cls'],a_evo=s.get('evolutionCode'))
+            report=combat.simultaneous(E.effective(s),npc_stats,seq,list(npc['seq']),secrets.randbits(32),a_cls=ch['class_type'],d_cls=npc['cls'],a_evo=s.get('evolutionCode'),levels=(E.level(s['xp']),2*npc['n']),hp_mode='v1')  # 5.2: HP wg Walki 1.0, NPC poziom 2×piętro
             win=report['winner']==0
             loot=None;rewards=dict(cash=0,xp=0)
             if win:
diff --git a/server/pvp.py b/server/pvp.py
--- a/server/pvp.py
+++ b/server/pvp.py
@@ -98,7 +98,7 @@ def install(app,d,E,combat,city):
             fb=s_d.get('tactic') or s_d.get('pvpDefense') or 'zrowna'  # taktyka > szablon (legacy) > zrównoważona
             if isinstance(fb,str):d_tac=fb if fb in combat.STYLE else 'zrowna';d_seq=combat.style_seq(d_tac)
             else:d_tac='szablon';d_seq=list(fb)
-            report=combat.simultaneous(E.effective(s_a),E.effective(s_d),a_seq,list(d_seq),secrets.randbits(32),a_cls=a['class_type'],d_cls=t['class_type'],a_evo=s_a.get('evolutionCode'),d_evo=s_d.get('evolutionCode'))
+            report=combat.simultaneous(E.effective(s_a),E.effective(s_d),a_seq,list(d_seq),secrets.randbits(32),a_cls=a['class_type'],d_cls=t['class_type'],a_evo=s_a.get('evolutionCode'),d_evo=s_d.get('evolutionCode'),levels=(E.level(s_a.get('xp') or 0),E.level(s_d.get('xp') or 0)))
             report['names']=[a['nickname'],t['nickname']];report['characterIds']=[a['id'],t['id']];report['ranked']=True
             report['tactics']=[s_a['tactic'],d_tac];report['stats']=[E.effective(s_a),E.effective(s_d)]
             report['avatars']=[avatar_mod.brief(s_a),avatar_mod.brief(s_d)];report['gear']=[avatar_mod.gear(s_a),avatar_mod.gear(s_d)]  # 0.47
@@ -120,7 +120,7 @@ def install(app,d,E,combat,city):
         rows=c.execute('SELECT id,attacker_id,defender_id,report_json,created_at,combat_version FROM pvp_battles WHERE world_id=? AND (attacker_id=? OR defender_id=?) ORDER BY id DESC LIMIT 5',(wid,me['id'],me['id'])).fetchall()
         out=[]
         for r in rows:
-            rep=json.loads(r['report_json']);out.append(dict(id=r['id'],created_at=r['created_at'],names=rep.get('names'),winner=rep.get('winner'),classes=rep.get('classes'),combat_version=r['combat_version'] or combat.ENGINE_V2))
+            rep=json.loads(r['report_json']);out.append(dict(id=r['id'],created_at=r['created_at'],names=rep.get('names'),winner=rep.get('winner'),classes=rep.get('classes'),combat_version=r['combat_version'] or combat.ENGINE_V2_LEGACY))
         return out
 
     return dict(recent=recent,norm=norm)
diff --git a/server/sports2.py b/server/sports2.py
--- a/server/sports2.py
+++ b/server/sports2.py
@@ -52,7 +52,7 @@ def install(app,d,E,combat):
             seq=combat.style_seq(s['tactic'])
             rounds=[];wins=0
             for i,(name,npc_stats,npc_seq) in enumerate(TOURN_NPC):
-                rep=combat.simultaneous(E.effective(s),npc_stats,seq,list(npc_seq),now()+i*7919,a_cls=ch['class_type'],d_cls=None)
+                rep=combat.simultaneous(E.effective(s),npc_stats,seq,list(npc_seq),now()+i*7919,a_cls=ch['class_type'],d_cls=None,levels=(E.level(s['xp']),E.level(s['xp'])))  # 5.2: rywal turnieju na poziomie gracza
                 won=rep['winner']==0
                 if rep['winner']==0:wins+=1
                 rounds.append(dict(opponent=name,hp=rep['finalHp'],hpStart=rep['hpStart'],winner=rep['winner'],classes=rep.get('classes'),rounds=rep['rounds']))
```

## 00e7af3: feat(pvp): nagrody za każdy mecz dla obu stron, limit 15 walk/dobę UTC, para max 3 walki na 24 h [GDD v3.1 5.3]

```diff
commit 00e7af321d9168adf1b799b5517bdc34c25f6a48
Author: City Empire Dev <dev@city-empire.local>
Date:   Tue Oct 6 16:41:05 2026 +0000

    feat(pvp): nagrody za każdy mecz dla obu stron, limit 15 walk/dobę UTC, para max 3 walki na 24 h [GDD v3.1 5.3]

diff --git a/server/app.py b/server/app.py
--- a/server/app.py
+++ b/server/app.py
@@ -307,12 +307,16 @@ def create_app(db_path=None,clock=None,bootstrap_path=None,mode=None):
  def audit(c,uid,event,details):c.execute('INSERT INTO audit(actor_id,event,details,created_at) VALUES(?,?,?,?)',(uid,event,packed(details),now()))
  def check_tactic(t):
   if t not in combat.BEATS:fail(422,'Nieznana taktyka.')
+ RANKED_DAILY=15  # 5.3 GDD v3.1: wspólny limit walk rankingowych (wyzwania 1.0 + PvP 2.0) na dobę UTC
+ PAIR_MAX=3       # 5.3: z tym samym przeciwnikiem najwyżej 3 walki w oknie 24 h (4. zablokowana) — decyzja usera
  def daily_limit(c,cid):
   day=now()//(24*E.HOUR)*(24*E.HOUR)
   row=c.execute('SELECT used FROM ranked_usage WHERE character_id=? AND day=?',(cid,day)).fetchone()
-  if row and row['used']>=5:fail(409,'Wykorzystano 5 pojedynków rankingowych na dobę UTC.')
+  if row and row['used']>=RANKED_DAILY:fail(409,f'Wykorzystano {RANKED_DAILY} walk rankingowych na dobę UTC.')
  def pair_limit(c,a,b):
-  if c.execute('SELECT 1 FROM matches WHERE ((attacker_id=? AND defender_id=?) OR (attacker_id=? AND defender_id=?)) AND created_at>?',(a,b,b,a,now()-24*E.HOUR)).fetchone():fail(409,'Ta para może rozegrać punktowany pojedynek raz na 24 godziny.')
+  since=now()-24*E.HOUR;q='SELECT count(*) FROM {} WHERE ((attacker_id=? AND defender_id=?) OR (attacker_id=? AND defender_id=?)) AND created_at>?'
+  n=sum(c.execute(q.format(t),(a,b,b,a,since)).fetchone()[0] for t in ('matches','pvp_battles'))
+  if n>=PAIR_MAX:fail(409,f'Z tym przeciwnikiem walczysz najwyżej {PAIR_MAX} razy na 24 godziny — wybierz kogoś innego.')
 
  @app.get('/')
  def index():return FileResponse(ROOT/'web'/'index.html',headers={'Cache-Control':'no-cache'})
@@ -636,6 +640,8 @@ def create_app(db_path=None,clock=None,bootstrap_path=None,mode=None):
     day=now()//(24*E.HOUR)*(24*E.HOUR)
     c.execute('INSERT INTO ranked_usage(character_id,day,used) VALUES(?,?,1) ON CONFLICT(character_id,day) DO UPDATE SET used=used+1',(row['id'],day))
     c.execute('UPDATE characters SET rating=rating+?,wins=wins+?,losses=losses+?,draws=draws+? WHERE id=?',(delta,int(report['winner']==index),int(report['winner'] is not None and report['winner']!=index),int(report['winner'] is None),row['id']))
+   rw=[pvp_api['reward'](c,row['id'],'draw' if report['winner'] is None else 'win' if report['winner']==i else 'loss') for i,row in ((0,a),(1,d))]
+   report['rewards']=rw  # 5.3 GDD v3.1: nagrody dla obu stron
    mid=c.execute('INSERT INTO matches(world_id,challenge_id,attacker_id,defender_id,report_json,created_at,combat_version) VALUES(?,?,?,?,?,?,?)',(q['world_id'],cid,a['id'],d['id'],packed(report),now(),combat.ENGINE_V1)).lastrowid
    c.execute("UPDATE challenges SET status='accepted' WHERE id=?",(cid,));return dict(report=report,match_id=mid)
  @app.post('/api/challenges/{cid}/decline')
@@ -835,7 +841,7 @@ def create_app(db_path=None,clock=None,bootstrap_path=None,mode=None):
  city_api=city_events.install(app,SimpleNamespace(db=db,now=now,fail=fail,admin=admin,audit=audit,chronicle=chron_api),E)
  travel_api=travel.install(app,SimpleNamespace(db=db,now=now,fail=fail,world=world,own=own,auth=auth,rate=rate,audit=audit,era=city_api['era']),E)
  sports_api=sports.install(app,SimpleNamespace(db=db,now=now,fail=fail,world=world,own=own,auth=auth,rate=rate,audit=audit,chron=chron_api),E)
- pvp_api=pvp_mod.install(app,SimpleNamespace(db=db,now=now,fail=fail,world=world,own=own,auth=auth,rate=rate,audit=audit,extra=extra,limit=daily_limit),E,combat,city_api)
+ pvp_api=pvp_mod.install(app,SimpleNamespace(db=db,now=now,fail=fail,world=world,own=own,auth=auth,rate=rate,audit=audit,extra=extra,limit=daily_limit,pair=pair_limit),E,combat,city_api)
  dungeon_api=dungeon_mod.install(app,SimpleNamespace(db=db,now=now,fail=fail,world=world,own=own,auth=auth,rate=rate,audit=audit),E,combat)
  sports2_api=sports2_mod.install(app,SimpleNamespace(db=db,now=now,fail=fail,world=world,own=own,auth=auth,rate=rate,audit=audit),E,combat)
  services_api=services_mod.install(app,SimpleNamespace(db=db,world=world,own=own,auth=auth,now=now,fail=fail,rate=rate,audit=audit),E)  # 2.2 GDD v3.1
diff --git a/server/pvp.py b/server/pvp.py
--- a/server/pvp.py
+++ b/server/pvp.py
@@ -20,6 +20,9 @@ CREATE TABLE IF NOT EXISTS pvp_battles(id INTEGER PRIMARY KEY AUTOINCREMENT,worl
 CREATE INDEX IF NOT EXISTS pvp_battles_world ON pvp_battles(world_id,created_at);
 '''
 
+# 5.3 GDD v3.1: nagrody za każdy zakończony mecz rankingowy — dla obu stron (decyzja usera), także w wyzwaniach 1.0
+PVP_REWARDS={'win':dict(cash=500,xp=50,prestige=1),'loss':dict(cash=100,xp=10,prestige=0),'draw':dict(cash=200,xp=25,prestige=0)}
+
 class Attack(BaseModel):
     seq:list[str]|None=None  # 0.42: zignorowane — walka zawsze na zapisanych taktykach (Auto-atak)
 
@@ -90,7 +93,7 @@ def install(app,d,E,combat,city):
             if t['banned']:fail(409,'Ten mieszkaniec jest niedostępny.')
             if t['travel_destination']:fail(409,'Cel jest w drodze — poczekaj, aż dotrze na miejsce.')
             if extra.blocked(c,u['id'],t['account_id']):fail(409,'Kontakt został zablokowany.')
-            d.limit(c,a['id']);d.limit(c,t['id'])
+            d.limit(c,a['id']);d.limit(c,t['id']);d.pair(c,a['id'],t['id'])  # 5.3: limit pary także w PvP 2.0
             s_a=load(c,a['id']);s_d=load(c,t['id'])
             if E.level(s_a.get('xp') or 0)<2:fail(409,'Wyzwania PvP odblokowują się na 2. poziomie.')
             if not s_a.get('tactic'):fail(409,'Najpierw wybierz taktykę walki — wybór jednorazowy, na wejściu w Wyzwania PvP.')
@@ -109,10 +112,22 @@ def install(app,d,E,combat,city):
             for cid,delta,is_win,is_loss in [(a['id'],change,report['winner']==0,report['winner']==1),(t['id'],-change,report['winner']==1,report['winner']==0)]:
                 c.execute('INSERT INTO ranked_usage(character_id,day,used) VALUES(?,?,1) ON CONFLICT(character_id,day) DO UPDATE SET used=used+1',(cid,day))
                 c.execute('UPDATE characters SET rating=rating+?,wins=wins+?,losses=losses+?,draws=draws+? WHERE id=?',(delta,int(is_win),int(is_loss),int(report['winner'] is None or (not is_win and not is_loss)),cid))
+            rw=[reward(c,a['id'],'draw' if report['winner'] is None else 'win' if report['winner']==0 else 'loss'),
+                reward(c,t['id'],'draw' if report['winner'] is None else 'win' if report['winner']==1 else 'loss')]
+            report['rewards']=rw
             bid=c.execute('INSERT INTO pvp_battles(world_id,attacker_id,defender_id,report_json,rating_json,created_at,combat_version) VALUES(?,?,?,?,?,?,?)',(wid,a['id'],t['id'],json.dumps(report,ensure_ascii=False,separators=(',',':')),json.dumps([change,-change]),now(),combat.ENGINE_V2)).lastrowid
             city['emit'](c,wid,[t['id']],'pvp_attacked',dict(attacker=a['nickname'],result='win' if report['winner']==1 else 'loss' if report['winner']==0 else 'draw',change=round(-change,1),seq=a_seq,battle=bid))
             audit(c,u['id'],'pvp.attack',dict(battle=bid,target=t['id'],winner=report['winner']))
-            return dict(ok=True,battle=bid,report=report,ratingChanges=[change,-change],combat_version=combat.ENGINE_V2)
+            return dict(ok=True,battle=bid,report=report,ratingChanges=[change,-change],rewards=rw,combat_version=combat.ENGINE_V2)
+
+    def reward(c,cid,result):
+        """5.3: gotówka + XP na postać, Punkt Prestiżu na konto (za wygraną)."""
+        r=PVP_REWARDS[result];row=c.execute('SELECT state_json,account_id FROM characters WHERE id=?',(cid,)).fetchone()
+        s=json.loads(row['state_json']);s['cash']=s.get('cash',0)+r['cash'];s['xp']=s.get('xp',0)+r['xp']
+        E.log(s,f"⚔️ Walka rankingowa: {'wygrana' if result=='win' else 'przegrana' if result=='loss' else 'remis'} — +{r['cash']} $, +{r['xp']} XP"+(', +1 Punkt Prestiżu' if r['prestige'] else '')+'.',now())
+        c.execute('UPDATE characters SET state_json=? WHERE id=?',(json.dumps(s,ensure_ascii=False,separators=(',',':')),cid))
+        if r['prestige']:c.execute('UPDATE accounts SET prestige_points=prestige_points+? WHERE id=?',(r['prestige'],row['account_id']))
+        return dict(result=result,**r)
 
     def recent(c,u,wid):
         me=c.execute('SELECT id FROM characters WHERE account_id=? AND world_id=?',(u['id'],wid)).fetchone()
@@ -123,4 +138,4 @@ def install(app,d,E,combat,city):
             rep=json.loads(r['report_json']);out.append(dict(id=r['id'],created_at=r['created_at'],names=rep.get('names'),winner=rep.get('winner'),classes=rep.get('classes'),combat_version=r['combat_version'] or combat.ENGINE_V2_LEGACY))
         return out
 
-    return dict(recent=recent,norm=norm)
+    return dict(recent=recent,norm=norm,reward=reward)
```

## bab0e6a: feat(ranking): miesięczne sezony Elo per świat — nagrody Top 10/100/1000, reset Elo 1. dnia miesiąca, ranking XP bez nowych sezonów [GDD v3.1 5.4]

```diff
commit bab0e6acd8873aa23f34cfd67d59c1b47af658c8
Author: City Empire Dev <dev@city-empire.local>
Date:   Tue Oct 6 16:46:26 2026 +0000

    feat(ranking): miesięczne sezony Elo per świat — nagrody Top 10/100/1000, reset Elo 1. dnia miesiąca, ranking XP bez nowych sezonów [GDD v3.1 5.4]

diff --git a/server/app.py b/server/app.py
--- a/server/app.py
+++ b/server/app.py
@@ -22,6 +22,7 @@ from pydantic import BaseModel, ConfigDict, Field
 from . import age as AGE
 from . import services as services_mod  # 2.2 GDD v3.1: lokacje usługowe
 from . import npc as npc_mod  # 2.3 GDD v3.1: NPC z 3 emocjami
+from . import seasons as seasons_mod  # 5.4 GDD v3.1: miesięczne sezony Elo
 from . import longplay as longplay_mod
 from . import prestige as prestige_mod  # 4.5 GDD v3.1: Sala Chwały i RESET  # 3.4 GDD v3.1: kamienie milowe długiej gry
 from . import assistant as assistant_mod  # 2.6 GDD v3.1: Asystent Podróży (doradca)
@@ -310,6 +311,7 @@ def create_app(db_path=None,clock=None,bootstrap_path=None,mode=None):
  RANKED_DAILY=15  # 5.3 GDD v3.1: wspólny limit walk rankingowych (wyzwania 1.0 + PvP 2.0) na dobę UTC
  PAIR_MAX=3       # 5.3: z tym samym przeciwnikiem najwyżej 3 walki w oknie 24 h (4. zablokowana) — decyzja usera
  def daily_limit(c,cid):
+  season_api['ensure'](c)  # 5.4: przed walką rankingową zamknij zakończony sezon Elo (leniwie)
   day=now()//(24*E.HOUR)*(24*E.HOUR)
   row=c.execute('SELECT used FROM ranked_usage WHERE character_id=? AND day=?',(cid,day)).fetchone()
   if row and row['used']>=RANKED_DAILY:fail(409,f'Wykorzystano {RANKED_DAILY} walk rankingowych na dobę UTC.')
@@ -337,7 +339,7 @@ def create_app(db_path=None,clock=None,bootstrap_path=None,mode=None):
   # Cookie / Authorization / custom request headers. Never an external HTTP proxy.
   if not preview_sessions:fail(404,'Nie znaleziono zasobu.')
   routes={
-   'GET':r'/(?:me|shop|worlds|account/(?:export|security|profile|rankings)|avatar/catalog|admin/(?:overview|reports|backups|worlds/[1-9][0-9]*/summary)|staff/appeals|worlds/[1-9][0-9]*/(?:state|services|npcs|assistant|milestones|players|pvp|pvp/targets|community|sports2|racing/open|organizations/[1-9][0-9]*|chat/(?:world|organization)|dm|dm/[1-9][0-9]*)|matches/[1-9][0-9]*|ranking/global/season/[1-9][0-9]*|ranking/global/[1-9][0-9]*)',
+   'GET':r'/(?:me|shop|worlds|account/(?:export|security|profile|rankings)|avatar/catalog|admin/(?:overview|reports|backups|worlds/[1-9][0-9]*/summary)|staff/appeals|worlds/[1-9][0-9]*/(?:state|services|npcs|assistant|milestones|players|elo-season|pvp|pvp/targets|community|sports2|racing/open|organizations/[1-9][0-9]*|chat/(?:world|organization)|dm|dm/[1-9][0-9]*)|matches/[1-9][0-9]*|ranking/global/season/[1-9][0-9]*|ranking/global/[1-9][0-9]*)',
    'POST':r'/(?:auth/logout|worlds/[1-9][0-9]*/npcs/(?:recruit|batch|manager|feed|[1-9][0-9]*/(?:dispatch|recall|feed))|worlds/[1-9][0-9]*/services/[a-z]+/unlock|worlds/[1-9][0-9]*/server_reset|setup/claim|guardian/(?:verify|resend)|account/(?:birth-date|delete|delete/cancel|password|sessions/revoke|blocks/remove|appeals)|admin/(?:worlds|backups|notices|notices/[1-9][0-9]*/delete|events|events/[1-9][0-9]*/cancel|reports/[1-9][0-9]*/resolve)|staff/appeals/[1-9][0-9]*/resolve|organization-invites/[1-9][0-9]*/(?:accept|decline)|org-applications/[1-9][0-9]*/(?:accept|decline)|shop/(?:gate|checkout|equip|guardian|guardian/revoke)|worlds/[1-9][0-9]*/(?:character(?:/evolve)?|actions|challenges|tactic|class|distinction/claim|travel(?:/(?:arrive|speedup))?|location|avatar|wardrobe|dungeon/floor|racing(?:/(?:horse|npc|open|join/[1-9][0-9]*|cancel/[1-9][0-9]*|breed|stable))?|sports/(?:tournament|agility|archery|swim)|pvp(?:/(?:defense|attack/[1-9][0-9]*))?|organizations(?:/(?:invite|building|leave|transfer|remove-member|apply|fund|invest|announcement|role|contract(?:/cancel)?))?|chat/(?:world|organization)|dm/[1-9][0-9]*|events/read|reports|blocks)|challenges/[1-9][0-9]*/(?:accept|decline))',
    'PATCH':r'/admin/(?:worlds|accounts)/[1-9][0-9]*',
   }
@@ -564,6 +566,7 @@ def create_app(db_path=None,clock=None,bootstrap_path=None,mode=None):
    return dict(ok=True,tactic=data.style,seq=combat.style_seq(data.style),message='Taktyka wybrana — obowiązuje w każdym PvP i w całym Lochu.')
  @app.get('/api/worlds/{wid}/players')
  def players(wid:int,u=Depends(auth)):
+  with db.tx() as c:season_api['ensure'](c)  # 5.4: ranking Elo zawsze z bieżącego sezonu
   with db.read() as c:
    world(c,wid,True);own(c,u['id'],wid)
    ts=now()
@@ -841,6 +844,8 @@ def create_app(db_path=None,clock=None,bootstrap_path=None,mode=None):
  city_api=city_events.install(app,SimpleNamespace(db=db,now=now,fail=fail,admin=admin,audit=audit,chronicle=chron_api),E)
  travel_api=travel.install(app,SimpleNamespace(db=db,now=now,fail=fail,world=world,own=own,auth=auth,rate=rate,audit=audit,era=city_api['era']),E)
  sports_api=sports.install(app,SimpleNamespace(db=db,now=now,fail=fail,world=world,own=own,auth=auth,rate=rate,audit=audit,chron=chron_api),E)
+ season_api=seasons_mod.install(app,db,SimpleNamespace(now=now,auth=auth,own=own),E)  # 5.4 GDD v3.1: miesięczne sezony Elo
+ app.state.seasons=season_api
  pvp_api=pvp_mod.install(app,SimpleNamespace(db=db,now=now,fail=fail,world=world,own=own,auth=auth,rate=rate,audit=audit,extra=extra,limit=daily_limit,pair=pair_limit),E,combat,city_api)
  dungeon_api=dungeon_mod.install(app,SimpleNamespace(db=db,now=now,fail=fail,world=world,own=own,auth=auth,rate=rate,audit=audit),E,combat)
  sports2_api=sports2_mod.install(app,SimpleNamespace(db=db,now=now,fail=fail,world=world,own=own,auth=auth,rate=rate,audit=audit),E,combat)
@@ -884,7 +889,10 @@ def create_app(db_path=None,clock=None,bootstrap_path=None,mode=None):
  purge_guardian_expired();purge_due()
  def sweep():
   while True:
-   time.sleep(600);purge_guardian_expired();purge_due();purge_rate_limits();npc_api['sweep']()  # 1.5: co 10 min; 2.3: emocje i ucieczka NPC offline
+   time.sleep(600);purge_guardian_expired();purge_due();purge_rate_limits();npc_api['sweep']()
+   try:
+    with db.tx() as c:season_api['ensure'](c)  # 5.4: domknięcie sezonu Elo także bez ruchu graczy
+   except Exception:pass
  threading.Thread(target=sweep,daemon=True).start()
  return app
 
diff --git a/server/features.py b/server/features.py
--- a/server/features.py
+++ b/server/features.py
@@ -92,6 +92,9 @@ CREATE INDEX IF NOT EXISTS dm_inbox ON dm_messages(world_id,recipient_id,id DESC
 # 0.12/0.34: 28-dniowe sezony rankingowe — wspólne dla rankingów i Er świata (city_events.era_of).
 SEASON_ANCHOR=1767571200000;SEASON_LEN=28*86400000
 def season_of(t):return max(1,(t-SEASON_ANCHOR)//SEASON_LEN+1)
+# 5.4 GDD v3.1: ranking XP jest całoroczny — archiwa/tytuły XP tylko dla starych sezonów 28-dniowych 1..9;
+# od października 2026 (sezon 10) sezony są miesięczne i dotyczą Elo (server/seasons.py).
+XP_SEASON_LAST=9
 
 class DmSend(Strict):
  text:str=Field(min_length=1,max_length=500)
@@ -197,7 +200,7 @@ def install(app,d):
  def ensure_seasons(c,cur):
   for w in c.execute('SELECT id,name FROM worlds ORDER BY id').fetchall():
    done={r['season'] for r in c.execute('SELECT season FROM season_archive WHERE world_id=?',(w['id'],))}
-   for sn in range(1,cur):
+   for sn in range(1,min(cur,XP_SEASON_LAST+1)):  # 5.4: XP bez nowych sezonów
     if sn in done:continue
     top=c.execute('SELECT ch.id,ch.nickname,json_extract(ch.state_json,"$.xp") xp FROM characters ch JOIN accounts a ON a.id=ch.account_id WHERE ch.world_id=? AND a.banned=0 ORDER BY xp DESC,ch.id LIMIT 10',(w['id'],)).fetchall()
     c.execute('INSERT INTO season_archive(season,world_id,payload,created_at) VALUES(?,?,?,?)',(sn,w['id'],json.dumps([dict(cid=r['id'],nickname=r['nickname'],xp=r['xp'] or 0,level=E.level(r['xp'] or 0)) for r in top],ensure_ascii=False,separators=(',',':')),now()))
@@ -206,7 +209,7 @@ def install(app,d):
     for cid in chars:emit(c,w['id'],[cid],'season.end',{'season':sn,'world':w['name'],'place':place.get(cid)})
   # 0.13 reputation titles: granted once per finished season, purely cosmetic (no stats, no cash).
   titled={r['season'] for r in c.execute('SELECT DISTINCT season FROM character_titles')}
-  for sn in range(1,cur):
+  for sn in range(1,min(cur,XP_SEASON_LAST+1)):  # 5.4: brak nowych tytułów XP
    if sn in titled or not c.execute('SELECT 1 FROM season_archive WHERE season=?',(sn,)).fetchone():continue
    entries=[]
    for r in c.execute('SELECT payload,world_id FROM season_archive WHERE season=?',(sn,)).fetchall():
diff --git a/server/seasons.py b/server/seasons.py
new file mode 100644
--- /dev/null
+++ b/server/seasons.py
@@ -0,0 +1,100 @@
+"""5.4 GDD v3.1: miesięczne sezony rankingowe Elo (per świat).
+
+Sezon = miesiąc kalendarzowy UTC. Numeracja (rok-2026)*12+miesiąc — październik 2026 = 10,
+czyli ciągłość ze starymi 28-dniowymi sezonami XP (ostatni archiwizowany = 9, patrz features.XP_SEASON_LAST).
+Zamknięcie sezonu (leniwe: przed każdą walką rankingową, w rankingu graczy i w wątku sweep):
+  - ranking świata po rating DESC, id; nagradzani tylko gracze z ≥1 walką rankingową w sezonie,
+  - Top 10: ramka diamentowa + 600💎 + Tytuł Sezonu; Top 100: ramka złota + 200💎; Top 1000: ramka srebrna + 50💎,
+  - 💎 trafiają na postać (s['diamonds']), ramki do s['frames'] (zachowywane przy resecie),
+  - reset Elo wszystkich postaci świata do 1000.
+Ranking XP pozostaje całoroczny, bez sezonów (decyzja usera).
+"""
+import datetime
+import json
+
+from fastapi import Depends
+
+MONTHLY_START = 10          # pierwszy sezon miesięczny (październik 2026)
+RATING_START = 1000
+TIERS = ((10, 'diamond', 600, 'Diamentowa'), (100, 'gold', 200, 'Złota'), (1000, 'silver', 50, 'Srebrna'))
+
+SCHEMA = '''
+CREATE TABLE IF NOT EXISTS elo_seasons(world_id INTEGER NOT NULL REFERENCES worlds(id),season INTEGER NOT NULL,closed_at INTEGER NOT NULL,players INTEGER NOT NULL,PRIMARY KEY(world_id,season));
+CREATE TABLE IF NOT EXISTS elo_season_results(world_id INTEGER NOT NULL,season INTEGER NOT NULL,character_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,place INTEGER NOT NULL,rating REAL NOT NULL,tier TEXT NOT NULL,diamonds INTEGER NOT NULL,PRIMARY KEY(world_id,season,character_id));
+'''
+
+
+def month_season(t):
+    d = datetime.datetime.fromtimestamp(t / 1000, datetime.timezone.utc)
+    return (d.year - 2026) * 12 + d.month
+
+
+def bounds(sn):
+    """[początek, koniec) sezonu w ms UTC — koniec = 00:00 UTC pierwszego dnia następnego miesiąca."""
+    y, m = 2026 + (sn - 1) // 12, (sn - 1) % 12 + 1
+    ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
+    ms = lambda a, b: int(datetime.datetime(a, b, 1, tzinfo=datetime.timezone.utc).timestamp() * 1000)
+    return ms(y, m), ms(ny, nm)
+
+
+def tier_of(place):
+    for limit, code, dia, label in TIERS:
+        if place <= limit:
+            return code, dia, label
+    return None
+
+
+def install(app, db, d, E):
+    with db.tx() as c:
+        c.executescript(SCHEMA)
+
+    def emit(c, wid, cid, kind, payload):
+        c.execute('INSERT INTO game_events(world_id,character_id,kind,payload,created_at) VALUES(?,?,?,?,?)', (wid, cid, kind, json.dumps(payload, ensure_ascii=False, separators=(',', ':')), d.now()))
+
+    def close(c, wid, sn):
+        start, end = bounds(sn)
+        rows = c.execute('''SELECT ch.id,ch.rating,ch.state_json FROM characters ch JOIN accounts a ON a.id=ch.account_id
+            WHERE ch.world_id=? AND a.banned=0 AND EXISTS(SELECT 1 FROM ranked_usage r WHERE r.character_id=ch.id AND r.day>=? AND r.day<? AND r.used>0)
+            ORDER BY ch.rating DESC,ch.id LIMIT 1000''', (wid, start, end)).fetchall()
+        for place, r in enumerate(rows, 1):
+            code, dia, label = tier_of(place)
+            s = json.loads(r['state_json'])
+            frame = f'season-{sn}-{code}'
+            s.setdefault('frames', [])
+            if frame not in s['frames']:
+                s['frames'].append(frame)
+            s['diamonds'] = s.get('diamonds', 0) + dia
+            E.log(s, f'🏆 Koniec sezonu {sn}: miejsce {place} — ramka {label}, +{dia} 💎.', d.now())
+            c.execute('UPDATE characters SET state_json=? WHERE id=?', (json.dumps(s, ensure_ascii=False, separators=(',', ':')), r['id']))
+            if code == 'diamond':
+                c.execute('INSERT INTO character_titles(character_id,season,code,label,granted_at) VALUES(?,?,?,?,?)', (r['id'], sn, 'season_top10', f'Tytuł Sezonu {sn} — Top 10', d.now()))
+            c.execute('INSERT INTO elo_season_results(world_id,season,character_id,place,rating,tier,diamonds) VALUES(?,?,?,?,?,?,?)', (wid, sn, r['id'], place, r['rating'], code, dia))
+            emit(c, wid, r['id'], 'season.reward', {'season': sn, 'place': place, 'tier': code, 'diamonds': dia, 'frame': frame, 'title': code == 'diamond'})
+        c.execute('UPDATE characters SET rating=? WHERE world_id=?', (RATING_START, wid))   # reset Elo
+        c.execute('INSERT INTO elo_seasons(world_id,season,closed_at,players) VALUES(?,?,?,?)', (wid, sn, d.now(), len(rows)))
+
+    def ensure(c):
+        """Zamyka wszystkie zakończone, niezamknięte sezony (≥ MONTHLY_START) we wszystkich światach."""
+        cur = month_season(d.now())
+        if cur <= MONTHLY_START:
+            return 0
+        n = 0
+        for w in c.execute('SELECT id FROM worlds ORDER BY id').fetchall():
+            done = {r['season'] for r in c.execute('SELECT season FROM elo_seasons WHERE world_id=?', (w['id'],))}
+            for sn in range(MONTHLY_START, cur):
+                if sn not in done:
+                    close(c, w['id'], sn); n += 1
+        return n
+
+    @app.get('/api/worlds/{wid}/elo-season')
+    def elo_season(wid: int, u=Depends(d.auth)):
+        with db.tx() as c:
+            ensure(c)
+            ch = d.own(c, u['id'], wid)
+            sn = month_season(d.now()); start, end = bounds(sn)
+            last = c.execute('SELECT season,place,tier,diamonds,rating FROM elo_season_results WHERE character_id=? ORDER BY season DESC LIMIT 12', (ch['id'],)).fetchall()
+            return dict(season=sn, monthly=sn >= MONTHLY_START, startsAt=start, endsAt=end, rating=ch['rating'],
+                        tiers=[dict(top=t[0], tier=t[1], diamonds=t[2], frame=t[3], title=t[1] == 'diamond') for t in TIERS],
+                        history=[dict(r) for r in last])
+
+    return dict(ensure=ensure, month_season=month_season, bounds=bounds)
```

## 0b378a9: fix(combat): wczesne wykrycie pata (2 okresy sekwencji bez obrażeń = remis), test lochu na Kontrolę [GDD v3.1 5.1]

```diff
commit 0b378a993f58a1518d0a508389b55866aa7152d0
Author: City Empire Dev <dev@city-empire.local>
Date:   Tue Oct 6 17:00:01 2026 +0000

    fix(combat): wczesne wykrycie pata (2 okresy sekwencji bez obrażeń = remis), test lochu na Kontrolę [GDD v3.1 5.1]

diff --git a/server/combat.py b/server/combat.py
--- a/server/combat.py
+++ b/server/combat.py
@@ -85,10 +85,11 @@ def simultaneous(a_stats,d_stats,a_seq,d_seq,seed,a_cls=None,d_cls=None,a_evo=No
   if evo=='blyskawica' and winded[side]:v*=1.25
   return v
  rounds=[];winner=None
- r=-1;streak=[0,0]
+ r=-1;streak=[0,0];quiet=0;stalemate=False
+ PERIOD=math.lcm(len(a_seq),len(d_seq))  # silnik deterministyczny: 2 okresy bez obrażeń = pat na zawsze
  while hp[0]>0 and hp[1]>0 and r+1<MAX_ROUNDS_GUARD:  # 5.1: do 0 HP (dawniej 3 rundy)
   r+=1
-  aa,dd=a_seq[r%len(a_seq)],d_seq[r%len(d_seq)]
+  aa,dd=a_seq[r%len(a_seq)],d_seq[r%len(d_seq)];hp_before=tuple(hp)
   # 5.1 anty-pat: trzeci unik z rzędu nie działa (zawodnik „łapie zadyszkę”) — bez tego szablon 3× unik byłby nie do pokonania
   tired=[False,False];acts=[aa,dd]
   for i in (0,1):
@@ -126,6 +127,8 @@ def simultaneous(a_stats,d_stats,a_seq,d_seq,seed,a_cls=None,d_cls=None,a_evo=No
   if dealt[0]>0:landed[0]+=1
   if dealt[1]>0:landed[1]+=1
   rounds.append(dict(r=r+1,a=acts[0],d=acts[1],tired=tired,pot_a=pot_a,pot_d=pot_d,dealt=[dealt[0],dealt[1]],hp=[round(hp[0],1),round(hp[1],1)],first=first))
+  quiet=quiet+1 if tuple(hp)==hp_before else 0
+  if quiet>=2*PERIOD+2:stalemate=True;break  # 5.1: wczesny remis — wynik identyczny jak po 1000 rundach, bez pustego raportu
  winner=None if hp[0]>0 and hp[1]>0 else (0 if hp[0]>0 else 1)  # 5.1: bezpiecznik 1000 rund = remis
  # 0.48: tor prezentacji — zdarzenia 1:1 z autorytatywnym przebiegiem (tylko odczyt rund),
  # żeby odtworzenie animacji pokazywało dokładnie tę walkę, którą rozstrzygnął serwer.
@@ -140,4 +143,4 @@ def simultaneous(a_stats,d_stats,a_seq,d_seq,seed,a_cls=None,d_cls=None,a_evo=No
    run[opp]=round(min(run[opp],start[opp]),1)
    events.append(dict(round=rd['r'],attacker=side,defender=opp,landed=True,critical=False,damage=dealt,hp=[round(x,1) for x in run]))
  profiles=[dict(hp=hp_start[0]),dict(hp=hp_start[1])]
- return dict(version='0.5-evo1',classes=[a_cls,d_cls],evolutions=[a_evo,d_evo],seqs=[a_seq,d_seq],seed=seed,rounds=rounds,winner=winner,finalHp=[round(hp[0],1),round(hp[1],1)],hpStart=hp_start,initiative=[init[0],init[1]],authoritative=True,events=events,profiles=profiles)
+ return dict(stalemate=stalemate,version='0.5-evo1',classes=[a_cls,d_cls],evolutions=[a_evo,d_evo],seqs=[a_seq,d_seq],seed=seed,rounds=rounds,winner=winner,finalHp=[round(hp[0],1),round(hp[1],1)],hpStart=hp_start,initiative=[init[0],init[1]],authoritative=True,events=events,profiles=profiles)
```
