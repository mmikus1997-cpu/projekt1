# Etap 3: projekt zadań 3.1 (Katalog Garażu) i 3.2 (Benzyna)

Stan wyjściowy: `e5ade38`, gałąź `feature/gdd-v31-migration`. Kodu jeszcze nie zmieniałem.

## Ustalenia z analizy kodu (wpływają na projekt)

| # | Co jest dziś | Konsekwencja |
|---|---|---|
| A | `E.GARAGE`: rower 600, furgonetka 2400, sedan 4200, bus 7000 (premium, Era III), supercar 16000 (VIP) | Nowy katalog zastępuje listę. Bramki Ery III i VIP do decyzji (D3). |
| B | Zużycie `wear` ma **tylko auto aktualnie wybrane** (`s['vehicle'] = {id, wear}`). Pozostałe auta w garażu nie mają żadnego stanu. | Paliwo musi być **osobne dla każdego auta**, więc wprowadzam `s['cars'][id] = {fuel}`. Przeniesienie `wear` do tej samej struktury zostawiam na 3.3. |
| C | Stan aut jest w dwóch miejscach: `state_json.garage` (logika gry) i tabela `vehicles` (tylko sprawdzenie `condition>0` w travel i asystencie) | Paliwo trafia tylko do `state_json`. Tabela `vehicles` zostaje bez zmian i jest dalej synchronizowana jak dziś. Usunięcie dublowania to osobny temat. |
| D | `HOPS` nie ma wpisu dla dzielnicy 1, więc lokacje w Nadmorskiem mają 0 przystanków | Spalanie liczone jest **minimum za 1 przystanek** na każdy odcinek. |
| E | Podróż gracza ma odległość `abs(cel − bieżąca)`, a nie `HOPS` | Spalanie gracza = odległość × spalanie auta (spójne z liczeniem czasu w travel). |
| F | **Tabela `longplay_milestones` nie istnieje.** Nie ma jej w kodzie, migracjach ani raportach Etapu 1 (1.7 i 1.8 dotyczyły innych rzeczy; 1.8 to bramka wieku). Nie ma też licznika dni online. | Zadanie 3.4 wymaga nowej tabeli i śledzenia aktywności. To pytanie D1. |
| G | Identyfikatory aut występują w kilkudziesięciu plikach testów, a frontend web korzysta z grafik `img` | Mapowanie według **typu auta** zachowuje identyfikatory `sedan` i `furgonetka`, więc zmian w testach jest mało. Nowe auta dostają istniejące grafiki, żeby stary web działał bez zmian w JS. |

---

## 3.1: Katalog Garażu (5 aut + 1 bonusowe)

### Proponowane parametry

| id | Nazwa | Cena | Poziom | Rabat czasu kontraktów | Dojazd NPC (×) | Spalanie / przystanek | Cena 1% baku | Serwis | Grafika (web) |
|---|---|---|---|---|---|---|---|---|---|
| `dostawczak` | Dostawczak | 2 000 | 1 | 10% | 1.2 | 4% | 1 $ | 300 | `rower`* |
| `sedan` | Sedan | 8 000 | 3 | 20% | 0.8 | 3% | 1.5 $ | 800 | `sedan` |
| `van` | Van Rodzinny | 15 000 | 5 | 26% | 0.9 | 5% | 2 $ | 1 400 | `bus` |
| `furgonetka` | Furgonetka | 25 000 | 7 | 32% | 0.85 | 5% | 2.5 $ | 2 000 | `furgonetka` |
| `suv` | SUV | 50 000 | 10 | 40% | 0.7 | 6% | 3 $ | 3 000 | `supercar` |
| `mistrz` | Mistrz Rankingu | — (nagroda) | 1 | 45% | 0.6 | 3% | 2 $ | 2 000 | `supercar` |

\* Grafiki tymczasowe, dopóki Flutter nie dostanie nowych; dla `dostawczak` lepiej pasuje `furgonetka`, do decyzji.

- `mistrz`: `buyable=False`; `buy_vehicle` zwraca 409 „Tego auta nie da się kupić — to nagroda za 7 dni gry”.
- Pojemność garażu bez zmian: Rezydencja + Charyzma, maksymalnie 5 aut. Auto `mistrz` **nie zajmuje miejsca** (bonus), więc zgodnie z „shipped guard” zostaje 5 miejsc.
- Bonus `garageUp` (ulepszenia) przechodzi na nowe identyfikatory razem z autem.
- **Dlaczego dojazd 1.2 dla Dostawczaka:** zastępuje rower (było 1.4), więc tani start nadal jest wolniejszy od autobusu ×2.0, ale szybszy niż on.

### Migracja starych aut (leniwa, przy pierwszym odczycie postaci, z wersją `s['garageV']=2`)

**Propozycja: mapowanie według typu auta**, bo zachowuje identyfikatory i nikt nie traci na wartości:

| Stare (cena) | → Nowe (cena) | Różnica |
|---|---|---|
| rower (600) | dostawczak (2 000) | +1 400 |
| sedan (4 200) | sedan (8 000) | +3 800 |
| furgonetka (2 400) | furgonetka (25 000) | **+22 600** ⚠ |
| bus (7 000) | van (15 000) | +8 000 |
| supercar (16 000) | suv (50 000) | +34 000 |

Wariant alternatywny to **mapowanie według pozycji w cenniku**: rower→dostawczak, furgonetka→sedan, sedan→van, bus→furgonetka, supercar→suv. Jest sprawiedliwszy (nikt nie dostaje dużego prezentu), ale zmienia znaczenie identyfikatorów `sedan` i `furgonetka`. To oznacza mylące logi i dużo zmian w testach. Pytanie D2.

**Migracja dotyka:** `s['garage']`, `s['vehicle']['id']` (z zachowaniem `wear`), `s['garageUp']`, `s['travelCar']`, `s['npcRoutes'].runs[].vehicle` (trwające stare trasy), `npcs.assigned_car_id` (migracja SQL przy starcie), `vehicles.type` (migracja SQL).

### Diff 3.1 (skrót)
```diff
--- server/economy.py
-GARAGE=[
- dict(id='rower',name='Rower dostawczy',price=600,discount=10,level=1,service=150,...),
- dict(id='furgonetka',name='Furgonetka',price=2400,discount=20,level=4,service=500,...),
- dict(id='sedan',name='Sedan Miejski',price=4200,discount=24,level=3,service=800,...),
- dict(id='bus',name='Bus flotowy',price=7000,discount=30,level=6,service=1400,...,premium=True,...),
- dict(id='supercar',name='Hiper Widok GT',price=16000,discount=42,level=8,service=2400,...,vip=True,...),
-]
+# 3.1 GDD v3.1: katalog 5 aut + nagroda „Mistrz Rankingu” (fuel = spalanie % / przystanek, fuelPrice = $ za 1% baku)
+GARAGE=[
+ dict(id='dostawczak',name='Dostawczak',price=2000,discount=10,level=1,service=300,fuel=4,fuelPrice=1.0,img='rower',...),
+ dict(id='sedan',name='Sedan',price=8000,discount=20,level=3,service=800,fuel=3,fuelPrice=1.5,img='sedan',...),
+ dict(id='van',name='Van Rodzinny',price=15000,discount=26,level=5,service=1400,fuel=5,fuelPrice=2.0,img='bus',...),
+ dict(id='furgonetka',name='Furgonetka',price=25000,discount=32,level=7,service=2000,fuel=5,fuelPrice=2.5,img='furgonetka',...),
+ dict(id='suv',name='SUV',price=50000,discount=40,level=10,service=3000,fuel=6,fuelPrice=3.0,img='supercar',...),
+ dict(id='mistrz',name='Mistrz Rankingu',price=0,discount=45,level=1,service=2000,fuel=3,fuelPrice=2.0,img='supercar',
+      buyable=False,bonus=True,description='Nagroda za 7 dni gry. Nie zajmuje miejsca w garażu.'),
+]
+GARAGE_V=2
+LEGACY_CARS={'rower':'dostawczak','bus':'van','supercar':'suv'}   # sedan i furgonetka bez zmiany id (D2)
+def migrate_garage(s):
+ # 3.1: leniwa migracja aut z katalogu 0.59 (idempotentna, wersjonowana)
+ if s.get('garageV',1)>=GARAGE_V:return False
+ m=lambda v:LEGACY_CARS.get(v,v)
+ s['garage']=list(dict.fromkeys(m(v) for v in s.get('garage') or []))
+ if s.get('vehicle'):s['vehicle']['id']=m(s['vehicle']['id'])
+ s['garageUp']={m(k):v for k,v in (s.get('garageUp') or {}).items()}
+ if s.get('travelCar'):s['travelCar']=m(s['travelCar'])
+ for r in (s.get('npcRoutes') or {}).get('runs',[]):r['vehicle']=m(r.get('vehicle'))
+ s['garageV']=GARAGE_V;return True
```
```diff
--- server/economy.py (buy_vehicle)
-  if g.get('premium') and era<3:raise RuleError('Pojazdy klasy premium ...')
-  if g.get('vip') and not vip:raise RuleError('Hiper Widok GT to samochód VIP ...')
+  if not g.get('buyable',True):raise RuleError('Tego auta nie da się kupić — to nagroda za 7 dni gry.')
-  if len(s['garage'])>=cap:...
+  if len([v for v in s['garage'] if not car(v).get('bonus')])>=cap:...   # auto-nagroda nie zajmuje miejsca
```
```diff
--- server/services.py
-TRAVEL_FACTOR = {'supercar': 0.6, 'sedan': 0.8, 'furgonetka': 1.0, 'bus': 1.0, 'rower': 1.4}
+TRAVEL_FACTOR = {'mistrz': 0.6, 'suv': 0.7, 'sedan': 0.8, 'furgonetka': 0.85, 'van': 0.9, 'dostawczak': 1.2}  # 3.1
--- server/npc.py / travel.py (migracja SQL przy starcie, jednorazowa)
+UPDATE npcs SET assigned_car_id=CASE assigned_car_id WHEN 'rower' THEN 'dostawczak' WHEN 'bus' THEN 'van' WHEN 'supercar' THEN 'suv' ELSE assigned_car_id END;
+UPDATE vehicles SET type=CASE type WHEN 'rower' THEN 'dostawczak' WHEN 'bus' THEN 'van' WHEN 'supercar' THEN 'suv' ELSE type END;
```
`VEH_MULT` (mnożnik wypłaty starych tras) dostaje nowe klucze, żeby odbiór tras sprzed zmiany działał po migracji.

**Testy 3.1:** migracja (każde stare auto, `vehicle`/`wear`, `garageUp`, trwająca stara trasa, NPC w trakcie zmiany z `rower`), idempotentność, brak możliwości kupna `mistrz`, `mistrz` nie zajmuje miejsca, ceny i poziomy. Dodatkowo zamiana `rower`/`bus`/`supercar` na nowe identyfikatory w istniejących testach (bez zmiany asercji, poza kwotami zależnymi od ceny).

---

## 3.2: Benzyna (`fuel`, 0–100%)

### Model
- **Stan:** `s['cars'] = {id: {'fuel': 0..100}}`. Nowe auto ma pełny bak, migracja ustawia 100% wszystkim posiadanym autom.
- **Spalanie:** `fuel_per_leg = max(1, przystanki) × car.fuel` (%).
  - **NPC:** odcinek = dojazd do pracy albo powrót; przystanki = `HOPS[dzielnica usługi]`.
  - **Gracz:** przystanki = `abs(cel − bieżąca)`.
- **Gracz:** paliwo pobierane przy starcie podróży autem. Za mało paliwa na całą trasę → **409** „Za mało paliwa (X%, potrzeba Y%). Zatankuj albo jedź autobusem.”
- **NPC (bez psucia deterministycznego `advance()`):**
  - Przy wysłaniu **paliwo auta przechodzi do zmiany** (nowa kolumna `shift_fuel`). Auto i tak jest zablokowane przy NPC przez całą zmianę, więc nie ma konfliktu.
  - `_start_leg` z autem: jeśli `shift_fuel ≥ potrzeba`, odejmuje; w przeciwnym razie **przesiadka do autobusu**: `shift_bus=1`, `travel_ms` przeliczone na autobus (×2,0), bilet doliczony. Zdarzenie `fuel_out` daje powiadomienie „X: skończyło się paliwo, wraca autobusem”.
  - Na koniec zmiany (`done`) pozostałe `shift_fuel` wraca do `s['cars'][auto].fuel`, w tym samym miejscu co wypłata.
  - **Wysyłka autem z pustym bakiem** (za mało na pierwszy odcinek): NPC jedzie **autobusem**, auto zostaje w garażu, komunikat to wyjaśnia (zgodnie z treścią zadania „auto nie wyjeżdża, NPC przesiada się do busa”). `batch cars=auto` i AI Manager **pomijają** auta bez paliwa na pełny kurs.
  - `estimate()` (asystent, `best`, manager) automatycznie uwzględnia paliwo, bo symuluje te same odcinki: przesiadki i bilety po skończeniu paliwa są w prognozie.
- **Tankowanie:** akcja `refuel {vehicle, amount?}` (domyślnie do pełna):
  - koszt = `ceil(% × fuelPrice × (0,8 przy VIP))`;
  - możliwe w każdej dzielnicy, ale nie w trakcie podróży i nie dla auta, które jest na zmianie NPC (paliwo jest wtedy w `shift_fuel`).
- **Paliwo a koszt dojazdu (przykład: Kurier, d=2, 1 przystanek, zmiana z 2 odcinkami):**
  - autobus: 2×20 $ = 40 $ biletów i ×2,0 czasu;
  - Dostawczak: 2×4% × 1 $ = 8 $;
  - SUV: 2×6% × 3 $ = 36 $, ale dojazd ×0,7.
  - Auto opłaca się zawsze czasem, a tanie auta także pieniędzmi.

### Diff 3.2 (skrót)
```diff
--- server/economy.py
+def car(vid):return next((g for g in GARAGE if g['id']==vid),{})
+def fuel_need(vid,hops):return max(1,int(hops))*car(vid).get('fuel',0)              # 3.2: % baku na odcinek
+def fuel_of(s,vid):return float(((s.get('cars') or {}).get(vid) or {}).get('fuel',100))
+def refuel_cost(s,vid,pct,now):return math.ceil(pct*car(vid)['fuelPrice']*(0.8 if s.get('vipUntil',0)>now else 1))
 ...
+ elif kind=='refuel':
+  vid=p.get('vehicle') or ''
+  if vid not in s['garage']:raise RuleError('Tego auta nie ma w Garażu.')
+  if traveling:raise RuleError('Zatankujesz po przyjeździe.')
+  if vid in (s.get('npcCars') or {}):raise RuleError('To auto jest na zmianie z NPC — zatankujesz po powrocie.')
+  have=fuel_of(s,vid);pct=min(100-have,float(p.get('amount') or 100-have))
+  if pct<=0:raise RuleError('Bak jest pełny.')
+  cost=refuel_cost(s,vid,pct,now);spend(s,cash=cost)
+  s.setdefault('cars',{}).setdefault(vid,{})['fuel']=have+pct
+  message='⛽ '+car(vid)['name']+': +'+str(round(pct))+'% za '+str(cost)+' $'+(' (VIP −20%)' if s.get('vipUntil',0)>now else '')+'.'
--- server/travel.py (start_travel, mode == 'car')
+                need = E.fuel_need(veh, abs(data.target_district - current))
+                if E.fuel_of(s, veh) < need: fail(409, f'Za mało paliwa ({round(E.fuel_of(s, veh))}%, potrzeba {need}%). Zatankuj albo jedź autobusem.')
+                s.setdefault('cars', {}).setdefault(veh, {})['fuel'] = E.fuel_of(s, veh) - need
--- server/npc.py
+    ('shift_fuel', 'REAL'),      # 3.2: paliwo auta przekazane na zmianę (wraca do garażu na koniec)
+    ('shift_fuel_need', 'REAL'), # 3.2: % na jeden odcinek
 def _start_leg(n, phase, t):
+    if n.get('assigned_car_id') and not n.get('shift_bus'):
+        if (n.get('shift_fuel') or 0) + EPS >= (n.get('shift_fuel_need') or 0):
+            n['shift_fuel'] -= n['shift_fuel_need']
+        else:                                   # 3.2: pusty bak → przesiadka do autobusu do końca zmiany
+            n['shift_bus'] = 1; n['travel_ms'] = n['bus_travel_ms']; evs.append(dict(kind='fuel_out'))
 def _finish(n, t, evs):
-    evs.append(dict(kind='done', ..., car=n.get('assigned_car_id'), ...))
+    evs.append(dict(kind='done', ..., car=n.get('assigned_car_id'), fuel=n.get('shift_fuel'), ...))
 # settle → handle('done'): s['cars'][car]['fuel'] = ev['fuel'] (razem z wypłatą, jeden zapis stanu)
```
(`_start_leg` dostaje listę zdarzeń jako parametr; czas autobusu dla tej usługi jest liczony przy wysłaniu i zapisywany w zmianie, kolumna `bus_travel_ms`).

**API:** `catalog.garage[]` dostaje pola `fuel`, `fuelPrice`, `buyable`, `bonus`; stan: `s.cars` (paliwo każdego auta); `public(npc)` dostaje `fuel` (paliwo w trakcie zmiany); asystent dostaje alert `low_fuel` (<20%) i porady podróży uwzględniające paliwo (`car.fuelNeed`, `car.fuel`, rekomendacja autobusu przy braku paliwa).

**Testy 3.2:** spalanie gracza (pobranie, 409 przy braku paliwa), tankowanie (koszt, VIP −20%, pełny bak, w podróży, auto na zmianie NPC), NPC: dokładne spalanie za odcinek, zwrot reszty na koniec, przesiadka do autobusu w trakcie zmiany (czas ×2, bilet, zdarzenie), wysyłka z pustym bakiem jedzie autobusem, `batch`/manager pomijają puste auta, `estimate()` = wypłata także przy przesiadce, Darmowa Komunikacja przy przesiadce.

---

## Plan commitów
1. `feat(garage): katalog 5+1 aut, leniwa migracja garaży i SQL npcs/vehicles [GDD v3.1 3.1]`
2. `feat(garage): paliwo per auto — spalanie za przystanek (gracz i NPC), przesiadka do busa, tankowanie z VIP −20% [GDD v3.1 3.2]`

Po każdym commicie pytest, a po obu pełna regresja E2E.
