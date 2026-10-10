# PROJEKT ARCHITEKTURY — GDD v3.2: NPC, Kierowcy, Taxi, Logistyka, Lojalność

Status: **do akceptacji, kodu backendu jeszcze nie ma.**
Baza: gałąź `feature/gdd-v31-migration` @ `895b72a` (432 testy pytest).
Pliki objęte zmianą: `server/npc.py` (główny), `server/services.py` (czas dojazdu), `server/economy.py` (paliwo i zużycie aut), `server/assistant.py`, `server/app.py` (sweep, allowlista, dashboard).
Backupy `*.backup_v059` zostają nietknięte. Nowe backupy dostają suffix `.backup_v31`.

---

## 0. Diagnoza: dlaczego nie wystarczy „dopisać kierowcę”

Dziś każda zmiana NPC to **niezależna maszyna stanów** w `advance(n, now)`:

```
to_work → working →(energia ≤ 30)→ to_home → sleeping →(energia ≥ 90)→ to_work … → koniec → wypłata
```

- Auto jest przypięte do jednego NPC na całą zmianę (`assigned_car_id`).
- Paliwo przechodzi na zmianę (`shift_fuel`).
- Zmiany nie zużywają aut.
- `settle()` i `sweep_npcs()` rozliczają każdy NPC osobno, w dowolnej kolejności. Działa to tylko dlatego, że NPC na siebie nie wpływają.

W v3.2 NPC zaczynają od siebie zależeć: SERVICE potrzebuje wolnego DRIVER-a z wolnym autem dokładnie w chwili, gdy zaczyna odcinek. Czasy odcinków są dynamiczne: powrót „bo zmęczony” wypada w różnych chwilach u różnych NPC.

Rozliczanie NPC pojedynczo dawałoby wyniki zależne od kolejności i od tego, czy gracz był online. Dlatego:

> **Kluczowa decyzja: rozliczenie przenosimy z poziomu NPC na poziom POSTACI.**
> `settle_character(cid, t)` przetwarza wszystkie NPC gracza naraz, w kolejności czasowej zdarzeń (symulacja zdarzeń dyskretnych). Przydział kierowcy i auta odbywa się w momencie startu odcinka.

Wszystkie emocje nadal zmieniają się liniowo w odcinkach, a przyszłe zdarzenia są deterministyczne. Dzięki temu da się to policzyć dokładnie, także offline, bez zegara działającego „na żywo”.

---

## 1. Model danych (migracje addytywne, kompatybilne wstecz)

### 1.1 Nowe kolumny `npcs` (ALTER TABLE, jak dotychczasowe `SHIFT_COLUMNS`)

| Kolumna | Typ | Znaczenie |
|---|---|---|
| `role` | `TEXT NOT NULL DEFAULT 'service'` | `service` / `driver` (Zad. 1) |
| `duty` | `TEXT` | kierowca: `ferry` (kurs z pasażerami lub dojazd po nich), `taxi`, NULL = wolny |
| `busy_until` | `INTEGER` | kierowca: koniec bieżącego kursu albo zmiany Taxi (ms) |
| `ride_car` | `TEXT` | auto, którym kierowca aktualnie jedzie |
| `taxi_until` | `INTEGER` | koniec zmiany Taxi |
| `taxi_hours` | `INTEGER` | 2 / 4 / 8 |
| `taxi_cash` | `REAL NOT NULL DEFAULT 0` | zarobek brutto Taxi (naliczany w odcinkach) |
| `taxi_mult` | `REAL NOT NULL DEFAULT 1` | mnożnik stawki zamrożony przy starcie (auto) |
| `loyalty` | `INTEGER NOT NULL DEFAULT 0` | 0–100 (Zad. 5) |
| `loyal_since` | `INTEGER` | chwila osiągnięcia 100 |
| `loy_day` | `INTEGER` | indeks bieżącej doby UTC (`t // 86 400 000`) |
| `loy_min` | `REAL` | najniższa emocja w bieżącej dobie |
| `leg_mode` | `TEXT` | bieżący odcinek SERVICE: `car` / `bus` |
| `leg_ride` | `INTEGER` | id kursu (`npc_rides`), którym jedzie |
| `shift_legacy` | `INTEGER NOT NULL DEFAULT 0` | 1 = zmiana rozpoczęta przed v3.2, dokończona po staremu |

### 1.2 Nowa tabela `npc_rides` (kursy: blokada aut, historia, widok dla Fluttera)

```sql
CREATE TABLE IF NOT EXISTS npc_rides(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  character_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
  driver_id INTEGER NOT NULL REFERENCES npcs(id) ON DELETE CASCADE,
  car_id TEXT NOT NULL,
  kind TEXT NOT NULL,              -- drop (do pracy) | pickup (z pracy) | taxi
  district INTEGER,                -- dzielnica usługi (taxi: NULL)
  depart_at INTEGER NOT NULL,      -- wyjazd kierowcy z Rezydencji
  meet_at INTEGER NOT NULL,        -- drop: start z pasażerami; pickup: odbiór pasażerów
  arrive_at INTEGER NOT NULL,      -- pasażerowie u celu
  back_at INTEGER NOT NULL,        -- kierowca i auto z powrotem w garażu (koniec blokady)
  passengers TEXT NOT NULL,        -- JSON [npc_id…]
  fuel REAL NOT NULL DEFAULT 0, wear REAL NOT NULL DEFAULT 0, cash INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS npc_rides_busy ON npc_rides(character_id, back_at);
```

- Auto jest zajęte, gdy istnieje kurs z `back_at > t`.
- Zastępuje to obecne `cars_in_use()` (liczone z `assigned_car_id` NPC) i jest używane także przez `vehicle_busy_until` przy podróży gracza.
- Sprzątanie: kursy starsze niż 7 dni usuwa sweep.

### 1.3 Stan postaci (`state_json`): bez nowych struktur

Paliwo i zużycie dalej siedzą per auto w `s['cars'][id]` (3.2/3.3). Zmienia się tylko to, **kto** je zużywa: kursy i Taxi, zamiast `shift_fuel` przypiętego do NPC.

---

## 2. Zadanie 1: limit 20 NPC i role

- `MAX_NPC = 20`.
- **Pojemność Rezydencji:** obecnie poziom × 3, maks. 15. Proponuję **poziom × 4 = 4/8/12/16/20** (Rezydencja ma maks. 5 poziomów). ➜ **Decyzja D1.**
- **Cennik rekrutacji:** #1–3 500, #4–6 1500, #7–10 5000, #11–15 15 000, **#16–20 30 000** (propozycja). ➜ D1.
- `POST /npcs/recruit {role: 'service'|'driver'}`: rola wybierana przy rekrutacji, domyślnie `service`.
- `POST /npcs/{nid}/role {role}`: zmiana roli tylko dla wolnego NPC (bez zmiany i kursu), maks. 1 na 24 h.
- Uprawnienia ról:

| Akcja | SERVICE | DRIVER |
|---|---|---|
| zmiana w usłudze (`dispatch`, batch, AI Manager) | ✅ | ❌ 409 „Kierowca nie pracuje w usługach” |
| Shift Taxi | ❌ 409 | ✅ |
| prowadzenie auta z garażu | ❌ | ✅ |

- **Auta z garażu do transportu NPC wymagają DRIVER-a.**
  - `dispatch` z `car_id`, gdy gracz nie ma żadnego kierowcy → 409 „Zatrudnij kierowcę, aby wozić ekipę autem”.
  - Bez kierowcy wszystko jedzie autobusem.
- **Założenie A1:** podróże samego gracza po mapie (`travel`, `travelCar`) nie wymagają kierowcy, bo gracz prowadzi sam. Auto zajęte przez kurs NPC jest jednak niedostępne dla gracza (jak dziś).

---

## 3. Zadanie 3: logistyka (serce zmiany)

### 3.1 Pojemność aut (pasażerowie, bez kierowcy)

```python
SEATS = {'dostawczak': 1, 'sedan': 2, 'van': 3, 'furgonetka': 3, 'suv': 4, 'mistrz': 4}
```

### 3.2 Kurs = zarezerwowany przedział czasu kierowcy i auta

Czas jednego odcinka: `T = S.travel_ms(usługa, auto, cecha_kierowcy, zużyte)`. To ta sama funkcja co dziś, ale cecha brana jest od **kierowcy**, nie pasażera.

```
DROP (do pracy):     depart = meet = t0      arrive = t0 + T        back = t0 + 2T   (powrót pustym autem)
PICKUP (z pracy):    depart = t0 − T         meet = t0  arrive = t0 + T    back = t0 + T
```

- Pasażer zawsze jedzie **jeden odcinek T**. Dojazd kierowcy „po” pasażera to koszt kierowcy, nie czas pasażera. Dyspozytor zna moment powrotu z wyprzedzeniem, bo emocje są liniowe.
- Bez tego Dostawczak (×1,2, łącznie z dojazdem po pasażera 2,4×) byłby wolniejszy od autobusu (2,0×).

### 3.3 Dyspozytor `allocate(chwila t0, kierunek, dzielnica, [pasażerowie])`

1. **Kandydaci-kierowcy:** `role='driver'`, `duty IS NULL` (nie w kursie, nie na Taxi), `busy_until ≤ depart`, energia ≥ 30 (zmęczony nie prowadzi). Kolejność: najdłużej wolny, potem id (determinizm).
2. **Kandydaci-auta:**
   - w garażu i wolne (`back_at ≤ depart`);
   - nieużywane w podróży gracza;
   - z paliwem na odcinek (drop: 2 odcinki, pickup: 2 odcinki);
   - preferowane: auto wskazane przez gracza → ostatnie auto kierowcy → najszybsze.
   - Zużyte w 100% może jechać, ale wolniej (3.3).
3. **Łączenie pasażerów:** wszyscy SERVICE z odcinkiem w **tej samej chwili, w tym samym kierunku i do tej samej dzielnicy** jadą jednym autem do jego pojemności. Nadwyżka idzie kolejnym kierowcą, a reszta autobusem. W praktyce łączy się wysyłka grupowa (batch) i wspólny koniec zmiany. Powroty „bo zmęczony” są zwykle pojedyncze.
4. **Brak pary kierowca + auto → autobus (fallback z Zad. 3):**
   - czas `bus_travel_ms` (×2,0, jak dziś);
   - bilet `BUS_FARE = 20 $` doliczany do `shift_fares`;
   - Darmowa Komunikacja = 0 $, jak dziś;
   - zdarzenie `npc.bus_fallback`;
   - gra nigdy nie czeka na kierowcę.
5. **Zapis:**
   - wiersz `npc_rides`;
   - kierowca dostaje `duty='ferry'`, `busy_until=back`, `ride_car`;
   - z `s['cars'][car]` zdejmowane jest paliwo, a zużycie rośnie;
   - pasażer dostaje `leg_mode='car'`, `leg_ride`, `phase_until = arrive`.

**Zużycie auta za kurs:** `WEAR_PER_HOP = 1` (% na odcinek-hop, oba kierunki). Cecha `kierowca_rajdowy` daje ×2. **Paliwo:** `E.fuel_need(car, hops)` za każdy przejechany odcinek, także pusty.

### 3.4 Silnik: `settle_character(c, cid, wid, t)`

Zastępuje pętlę `settle()` per NPC. **Każde rozliczenie (odczyt, akcja, sweep) dotyczy zawsze wszystkich NPC postaci.** To niezmiennik całego systemu.

```
wczytaj wszystkich NPC postaci + state_json
kolejka = dla każdego NPC: chwila jego NAJBLIŻSZEGO zdarzenia wymagającego koordynacji
          (start odcinka to_work/to_home, koniec kursu kierowcy, koniec Taxi, wysyłka AI Managera)
pętla (bezpiecznik 20 000 kroków):
    e = zdarzenie o najmniejszej chwili (remis → id NPC)       # porządek deterministyczny
    jeśli e.chwila > t: przerwij
    advance(npc, e.chwila, stop_before_leg=True)               # emocje, zarobek, przemęczenie, lojalność
    jeśli e = żądanie odcinka:
        zbierz WSZYSTKIE żądania o tej samej chwili / kierunku / dzielnicy  (łączenie)
        dla kierowcy-kandydata: najpierw advance(kierowca, depart)  (energia ≥ 30?)
        allocate(...) → kurs autem albo autobus → start odcinka
    jeśli e = koniec kursu: kierowca duty=NULL (wraca do bezczynności w Rezydencji)
    jeśli e = koniec Taxi: wypłata (§4), duty=NULL
    jeśli e = AI Manager: obecna logika manager_dispatch(), z przydziałem przez allocate()
    przelicz następne zdarzenie dla dotkniętych NPC
na koniec: advance(każdy NPC, t); zapis NPC, kursów i state_json w JEDNEJ transakcji
```

- **`advance()` zostaje** jako czysta funkcja emocji i zarobku w odcinkach o stałych stawkach. Dostaje parametr `stop_before_leg`: zatrzymuje się w chwili, gdy NPC chce zacząć odcinek, i zwraca żądanie zamiast samodzielnie wybierać transport. Cała matematyka 2.3c (przemęczenie, histereza), 2.4 (cykl zmiany) i 2.6 (prognozy) zostaje bez zmian.
- **Kierowca to też NPC z emocjami.** Stawki zależą od jego stanu:
  - `ferry`: jazda, energia −4/h, nastrój −1/h, sytość −2/h (odcinki trwają minuty, więc wpływ jest mały);
  - `taxi`: jak w §4;
  - wolny: jak dziś (Rezydencja, +10 energii/h).
- **Prognozy (`estimate`, asystent, batch):** liczone na kopii z założeniem „auto, jeśli teraz jest wolna para kierowca + auto, inaczej autobus”. To prognoza, a rozliczenie jest dokładne. API dostaje pole `transport: 'car'|'bus'`.

### 3.5 Gracz offline: dlaczego wynik jest poprawny

- `sweep()` (co 10 min) iteruje **po postaciach** (`SELECT DISTINCT character_id FROM npcs`, partie po 100), nie po NPC. Każda postać ma osobną transakcję, więc błąd jednej nie cofa innych.
- Zdarzenia zawsze są przetwarzane w kolejności czasowej, a rezerwacje kierowców są robione na chwilę `depart` z przeszłości. Wynik jest więc **taki sam, niezależnie od tego, czy rozliczenie nastąpiło co 10 min, raz po 3 dniach, czy przy każdym kliknięciu.**
- **Jedyne przybliżenie:** rezerwacja pickup z `depart = t0 − T` sprzed poprzedniego rozliczenia (T to minuty) jest dozwolona, jeśli kierowca był wtedy wolny. Jego emocje za ten odcinek liczą się od `max(depart, updated_at)`.
- **Test kontrolny** (obowiązkowy): ten sam scenariusz rozliczony jednym `settle` po 48 h oraz co 10 min daje identyczną gotówkę, emocje, lojalność, paliwo, zużycie i listę kursów.
- **Wydajność:** maks. 20 NPC. Doba to rząd kilkudziesięciu zdarzeń na postać, a tydzień offline kilka tysięcy kroków na czystym Pythonie (milisekundy).

### 3.6 Zmiany w trwających zmianach (migracja)

- Zmiany trwające w chwili wdrożenia dostają `shift_legacy=1` i kończą się według starych zasad (auto przypięte, `shift_fuel`). Kod legacy zostaje jako gałąź w `advance()`.
- Nowe zmiany idą przez dyspozytora. Po ok. 12 h od wdrożenia legacy wygasa samo.
- Istniejący NPC dostają `role='service'`, z wyjątkiem cechy `kierowca`. ➜ **Decyzja D2.**

---

## 4. Zadanie 2: Shift Taxi

`POST /npcs/{nid}/taxi {hours: 2|4|8, car_id?}`: tylko DRIVER, wolny, energia ≥ 40, wolne auto z paliwem na ≥ 1 h.

- Kierowca i auto są zablokowani do `taxi_until`. Kurs `kind='taxi'` w `npc_rides`. **Kierowca na Taxi nie wozi ekipy**, więc SERVICE jadą wtedy autobusem.
- `POST /npcs/{nid}/recall` dla Taxi: koniec teraz, wypłata za przepracowany czas.
- **Zarobek (z anonimowych zleceń, deterministyczny, bez losowości):**

```
taxi_cash += TAXI_RATE × VEH_MULT[auto] × h × (0,5 jeśli przemęczony) × (1,05 jeśli lojalny) × (1 + cecha.earn)
TAXI_RATE = 40 $/h      VEH_MULT (już istnieje): dostawczak .85, furgonetka 1.0, sedan 1.15, van 1.25, suv/mistrz 1.45
```

- **Burnout obcina Taxi o połowę** (Zad. 4), w tym samym miejscu co `shift_cash`.
- Bonus terytorium 8.3 (+5%) **nie dotyczy** Taxi, bo to nie praca w dzielnicy. Prestiż (4.5) i XP Battle Pass za zmianę NPC: **tak**.
- **Koszty Taxi** (zużywane w trakcie, liczone w odcinkach jak emocje):
  - paliwo `1 hop/h × car.fuel` % baku;
  - zużycie `1 %/h` (rajdowy 2 %/h);
  - pusty bak: zmiana kończy się wcześniej, zdarzenie `npc.taxi_fuel_out`;
  - zużycie 100%: Taxi jedzie dalej, auto wymaga serwisu (jak w 3.3).
- **Emocje kierowcy na Taxi:** energia −6/h, nastrój −3/h, sytość −3/h (poziom Kuriera). Przy energii ≤ 30 kierowca kończy zmianę wcześniej i wraca, z wypłatą za przepracowany czas.

**Kalibracja** (na 1 h Taxi, kierowca bez cech, brutto i po kosztach paliwa i serwisu):

| Auto | Zarobek $/h | Paliwo $/h | Serwis $/h (1%) | **Netto $/h** |
|---|---|---|---|---|
| Dostawczak | 34 | 4 | 3 | **27** |
| Sedan | 46 | 4,5 | 8 | **33,5** |
| Van | 50 | 10 | 14 | **26** |
| Furgonetka | 40 | 12,5 | 20 | **7,5** |
| SUV | 58 | 18 | 30 | **10** |
| Mistrz | 58 | 6 | 20 | **32** |

- Najsłabsza usługa ma 50 $/h (Minimarket), a typowe 90–220 $/h. Taxi jest wyraźnie mniej opłacalne, ale zawsze dodatnie, więc pokrywa paliwo i serwis.
- Ciężkie auta słabo nadają się do Taxi. To celowa decyzja: małe auta na Taxi, duże do wożenia ekipy.

---

## 5. Zadanie 4: cechy i burnout

- **Burnout bez zmian:** NPC nigdy nie znika, którakolwiek emocja < 30 daje zarobek ×0,5, wyjście przy wszystkich ≥ 40. **Rozszerzenie: ×0,5 także dla `taxi_cash`.**
- **Cechy według ról** (losowanie przy rekrutacji z puli roli):

| Cecha | Rola | Efekt | Negatyw (zdejmowany przez lojalność) |
|---|---|---|---|
| pracoholik | obie | +10% zarobku (usługi / Taxi) | energia w pracy 1,2× szybciej |
| spioch | obie | regeneracja snu +30% | −10% zarobku |
| ambitny | obie | +15% zarobku | nastrój 1,5× szybciej |
| optymista | obie | nastrój spada 2× wolniej | — |
| analityk | **service** | +15% w pracy biurowej | — |
| **kierowca_rajdowy** | **driver** | czas jazdy −20% (min. 30 s) | **zużycie auta ×2** |

- Obecna cecha `kierowca` zmienia nazwę na `kierowca_rajdowy`. **Działa wyłącznie dla roli DRIVER.** U SERVICE `travel` = 1,0, bo pasażer nie prowadzi. Dla zgodności zostaje alias `kierowca` → `kierowca_rajdowy`.
- Czas jazdy kursu bierze cechę **kierowcy**. Autobus nie bierze żadnej cechy.

---

## 6. Zadanie 5: lojalność

- **Śledzenie doby (w `advance()`, bez osobnego zadania cron):**
  - `_segment_end()` dostaje dodatkową granicę: północ UTC (`(loy_day + 1) × 86 400 000`). Każdy odcinek mieści się więc w jednej dobie.
  - Emocje są liniowe w odcinku, więc minimum w odcinku to minimum z jego końców: `loy_min = min(loy_min, energia, nastrój, sytość)` na początku i końcu odcinka.
  - Na granicy doby: jeśli `loy_min ≥ 50` **i** NPC był zatrudniony przez całą dobę (`hired_at ≤ początek doby`), to `loyalty = min(100, loyalty + 1)`. Potem reset `loy_min` i `loy_day += 1`.
  - Maks. +1 na dobę wynika z konstrukcji. Offline działa tak samo, bo sweep rozlicza kolejne północe po kolei.
- Lojalność nie spada (GDD tego nie wymaga). ➜ **Decyzja D3:** opcjonalnie −1 za dobę w burnoucie.
- **Przy 100:**
  - `loyal_since = t`;
  - zdarzenie `npc.loyal` z tekstem „Twój NPC {imię} staje się wobec Ciebie lojalny!” (dziennik gracza + powiadomienie);
  - efekt stały: zarobek ×1,05 (usługi i Taxi);
  - funkcja `trait_of(n)` dla lojalnego zwraca cechę **bez negatywów**: bez `energy_drain`, `mood_drain` i ujemnego `earn`, a `wear` = ×1.
  - Jedno miejsce w kodzie, więc działa wszędzie: emocje, prognozy, AI Manager.
- 100 dni bez spadku poniżej 50 to cel endgame, wymagający karmienia (Buffet) i odpoczynku.

---

## 7. API (pod Fluttera) — zmiany

| Endpoint | Zmiana |
|---|---|
| `GET /npcs` | + `role`, `duty`, `busyUntil`, `loyalty`, `loyal`, `transport` (bieżący odcinek: car/bus), `rides` (aktywne kursy: kierowca, auto, pasażerowie, czasy), `drivers` {total, free}, `seats` per auto |
| `POST /npcs/recruit` | + `{role}` |
| `POST /npcs/{nid}/role` | **nowy**: zmiana roli |
| `POST /npcs/{nid}/dispatch` | `car_id` = **preferowane** auto; odpowiedź + `transport`, `rideId`; DRIVER → 409 |
| `POST /npcs/batch` | wysyłka grupowa łączy pasażerów w kursy (pojemność); wynik zawiera listę kursów |
| `POST /npcs/{nid}/taxi` | **nowy**: `{hours: 2|4|8, car_id?}` |
| `POST /npcs/{nid}/recall` | obsługuje także Taxi |
| `POST /npcs/manager` | + opcja `taxi_idle` (wolni kierowcy jeżdżą Taxi, gdy nikt nie potrzebuje transportu; domyślnie OFF) |
| `GET /dashboard` | `npc.byRole`, `npc.drivers`, `npc.loyal` |

Allowlista podglądu dostaje `npcs/[id]/(role|taxi)`. Komunikaty błędów dostają tłumaczenia w `i18n/errors.json` (8.5).

---

## 8. Plan wdrożenia (commity, każdy z pytest)

1. `feat(npc): role SERVICE/DRIVER, limit 20, pojemność Rezydencji [GDD v3.2 1]`: migracja kolumn, recruit/role, blokady akcji.
2. `refactor(npc): rozliczenie na poziomie postaci (settle_character) bez zmiany reguł [GDD v3.2 3]`: **najpierw sam refactor**, z dowodem, że stare 432 testy przechodzą bez zmian (transport jeszcze po staremu).
3. `feat(npc): dyspozytor kursów — kierowca + auto + pasażerowie, pojemność, fallback autobus [GDD v3.2 3]`.
4. `feat(npc): Shift Taxi [GDD v3.2 2]`.
5. `feat(npc): kierowca_rajdowy tylko dla DRIVER, burnout na Taxi [GDD v3.2 4]`.
6. `feat(npc): lojalność [GDD v3.2 5]`.
7. Aktualizacja asystenta, AI Managera, dashboardu i allowlisty, potem raport `RAPORT-GDD32.md` + E2E.

**Nowe testy** (`tests/test_gdd32.py`):
- limit 20 i cennik;
- uprawnienia ról;
- pojemność każdego auta (5 pasażerów na Sedan = 2 + 2 + 1 autobusem przy 2 kierowcach…);
- fallback autobusowy (20 $, ×2,0, Darmowa Komunikacja = 0 $);
- kierowca zmęczony < 30 nie prowadzi;
- Taxi: kalibracja z tabeli, paliwo, zużycie, burnout ×0,5, wcześniejszy koniec przy pustym baku i przy energii 30;
- rajdowy: −20% tylko u kierowcy i zużycie ×2;
- lojalność: +1 na dobę, brak przy minimum < 50, maks. +1, 100 → zdarzenie + 5% + brak negatywów;
- **determinizm (settle jednorazowy vs co 10 min)**;
- migracja trwającej zmiany legacy.

Regresja: 432 testy + E2E 36/36. Testy, które dziś zakładają „auto przypięte do NPC” (`test_fuel`, `test_npc_shift`, `test_npc_batch`), będą świadomie zaktualizowane i opisane w raporcie.

---

## 9. Decyzje do akceptacji

| # | Pytanie | Moja propozycja |
|---|---|---|
| **D1** | Pojemność 20: jak skalować Rezydencję? Cena #16–20? | poziom × 4 (4/8/12/16/20); #16–20 = 30 000 $ |
| **D2** | Istniejący NPC z cechą `kierowca` | automatycznie `role='driver'` (gracz nie traci sensu cechy); reszta `service` |
| **D3** | Czy lojalność może spadać? | nie (zgodnie z GDD); opcjonalnie −1 za dobę w burnoucie |
| **D4** | Kierowca na Taxi a potrzeba transportu ekipy | Taxi blokuje kierowcę do końca zmiany (prosto, przewidywalnie) |
| **D5** | Odcinek „z powrotem do pracy” po śnie bez kierowcy | też autobus (spójnie z powrotem); alternatywa: NPC czeka na kierowcę |
| **D6** | Zużycie aut przez kursy ekipy (dziś zmiany NPC w ogóle nie zużywają aut) | 1% na hop (rajdowy 2%), bo kierowca realnie jeździ |
| **D7** | Bonus auto-pilota (2/4/8/12 h → 0/5/10/15%) | zostaje: zmienia się transport, nie długość zmian |
| **A1** | Podróże samego gracza autem bez kierowcy | dozwolone (gracz prowadzi sam) |
