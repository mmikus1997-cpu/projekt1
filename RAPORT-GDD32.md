# RAPORT — GDD v3.2: NPC, Kierowcy, Taxi, Logistyka, Lojalność (backend)

Gałąź: `feature/gdd-v32` (od `feature/gdd-v31-migration` @ `a037399`). Projekt: `PROJEKT-GDD32-NPC.md` (zaakceptowany z D1–D7 i A1).
Backupy przed zmianami: `server/{npc,services,economy,assistant,app}.py.backup_v31` (backupy `*_v059` nietknięte).

## Commity

| # | Commit | Zakres |
|---|---|---|
| 1 | `1e7dd48` feat(npc): role SERVICE/DRIVER, limit 20 … [GDD v3.2 1] | role, `POST /npcs/{id}/role`, limit 20, Rezydencja ×4, #16–20 = 30 000 $, D2 |
| 2 | `f4d7173` refactor(npc): rozliczenie na poziomie postaci … [GDD v3.2 3] | `settle_character`, sweep po postaciach (osobne transakcje); reguły bez zmian, 432/432 testów |
| 3 | `aa536b0` feat(npc): dyspozytor kursów … [GDD v3.2 3] | tabela `npc_rides`, przydział kierowca + auto, łączenie pasażerów, fallback autobus, D5, D6 |
| 4 | `e612e3b` feat(npc): Shift Taxi … [GDD v3.2 2] | `POST /npcs/{id}/taxi`, 40 $/h × auto, paliwo/zużycie wg czasu, recall, D4 |
| 5 | `e259ae6` test(npc): kierowca_rajdowy tylko dla DRIVER … [GDD v3.2 4] | testy Zad. 4 (sam kod wszedł w commitach 1/3/4) |
| 6 | `df26fe1` feat(npc): lojalność … [GDD v3.2 5] | lojalność, status Lojalny, zdarzenie i wpis w dzienniku |
| 7 | `09b5a40` feat(api): dashboard v3.2 + i18n … [GDD v3.2] | `/dashboard` npc.byRole/drivers/loyal/rides, 13 komunikatów en/de/fr, raport |

## Co działa (wg zadań GDD)

**Zad. 1 — limit 20 i role.**
- Rekrutacja `{role:'service'|'driver'}`, zmiana roli tylko dla wolnego NPC, maks. raz na 24 h.
- Kierowca nie pracuje w usługach (409).
- Cechy losowane z puli roli: `analityk` tylko dla usług, `kierowca_rajdowy` tylko dla kierowców.
- Migracja przy pierwszym starcie:
  - NPC z dawną cechą `kierowca` → `role='driver'`, cecha `kierowca_rajdowy` (D2);
  - trwające zmiany dokończą się po staremu (`shift_legacy=1`), a kierowca z takiej zmiany staje się DRIVER-em po jej końcu.

**Zad. 3 — logistyka (zamiast auto-pilota aut).**
- Każde rozliczenie obejmuje całą ekipę postaci (`settle_character`), a zdarzenia są przetwarzane w kolejności czasowej.
- W chwili startu odcinka dyspozytor:
  - wybiera wolnego kierowcę: energia ≥ 30, najdłużej wolny;
  - wybiera wolne auto z paliwem na kurs: preferowane, a w drugiej kolejności najszybsze;
  - sadza pasażerów jadących w tym samym kierunku do tej samej dzielnicy (Dostawczak 1, Sedan 2, Van/Furgonetka 3, SUV/Mistrz 4);
  - nadwyżkę wiezie kolejnym kierowcą, a resztę autobusem: 20 $, 2× dłużej, zdarzenie `npc.bus_fallback`, gra nie czeka.
- Rodzaje kursów:
  - DROP: tam z pasażerami i powrót pustym autem;
  - PICKUP: dojazd po pasażerów na pusto, potem powrót z nimi;
  - pasażer zawsze jedzie jeden odcinek.
- Koszty: paliwo za oba odcinki, zużycie 1% na hop, u rajdowego 2% (D6).
- Auto bez kierowcy → 409. Bez kierowców ekipa jeździ autobusem.
- Kursy blokują auta także dla podróży gracza (`npcCars`). Sam gracz dalej jeździ bez kierowcy (A1).
- Bonus auto-pilota 0/5/10/15% za długość zmiany zostaje (D7).
- Kierowca w kursie traci emocje w tempie −4/−1/−2 na godzinę. Kursy trwają minuty, więc kierowca szybko wraca do regeneracji.

**Zad. 2 — Taxi.**
- Wolny kierowca jeździ 2, 4 albo 8 h. Zarobek to 40 $/h × mnożnik auta, ×0,5 przy przemęczeniu, ×1,05 u lojalnego, z prestiżem i bez bonusu terytorium.
- Koszty i zmęczenie:
  - paliwo 1 hop/h, zużycie 1%/h (rajdowy 2%), naliczane proporcjonalnie do przejechanego czasu;
  - emocje kierowcy: −6/−3/−3 na godzinę.
- Zmiana kończy się wcześniej, gdy skończy się paliwo, energia spadnie do 30 albo gracz ją odwoła (wypłata za przepracowany czas).
- Taxi blokuje kierowcę i auto do końca (D4).
- Netto na godzinę, po paliwie i serwisie: od 7,5 $ (Furgonetka) do 33,5 $ (Sedan). Zawsze na plusie, zawsze poniżej najsłabszej usługi (50 $/h). Sprawdza to test.

**Zad. 4.**
- NPC nie uciekają; burnout ×0,5 działa także na Taxi.
- `kierowca_rajdowy` działa tylko u DRIVER-a: −20% czasu jazdy kursu, zużycie ×2.
- U pasażera i w autobusie cecha nie działa.

**Zad. 5 — lojalność.**
- `advance()` tnie odcinki o północy UTC i liczy minimum emocji w dobie.
- +1 za pełną dobę bez spadku poniżej 50, pod warunkiem że NPC był zatrudniony przez całą dobę. Maks. +1 na dobę, liczone także offline. Lojalność nie spada (D3).
- Przy 100:
  - wpis w dzienniku gracza i zdarzenie `npc.loyal` z tekstem „Twój NPC {imię} staje się wobec Ciebie lojalny!”;
  - zarobek +5% (usługi i Taxi);
  - cecha traci negatywne efekty (ambitny bez kary nastroju, pracoholik bez szybszego zmęczenia, śpioch bez −10%, rajdowy bez ×2).

## API dla Fluttera (nowe i zmienione)

- `POST /npcs/recruit {role}` · `POST /npcs/{id}/role {role}` · `POST /npcs/{id}/taxi {hours: 2|4|8, car_id?}` · `POST /npcs/{id}/recall` (także Taxi).
- `POST /npcs/{id}/dispatch`: `car_id` = auto preferowane. Odpowiedź zawiera `transport: car|bus` i `rideId`, a komunikat podaje auto i kierowcę.
- `POST /npcs/batch` (dispatch): łączy pasażerów w kursy; `results[].car` i `rideCount`. `cars` jest ignorowane, bo transport zawsze dobiera dyspozytor.
- `GET /npcs`:
  - nowe pola NPC: `role, roleLabel, duty, busyUntil, rideCar, transport, rideId, prefCar, legacy, loyalty, loyal, loyalSince, taxiUntil, taxiCash, traitActive`;
  - nowe pola listy: `rides[]` (aktywne kursy: kierowca, auto, pasażerowie, czasy), `drivers{total,free}`, `byRole`, `seats`.
- `GET /dashboard` → `npc.byRole, npc.drivers, npc.loyal, npc.rides`.
- Allowlista podglądu: `npcs/{id}/(role|taxi)`.

## Testy

- **pytest: 454 passed** (było 432). Nowe: `tests/test_gdd32.py`, 22 testy:
  - role, limit 20 i cennik, migracja D2;
  - pojemność aut i nadwyżka do autobusu, zmęczony kierowca, pełna zmiana z kosztami, rajdowy;
  - Taxi: kalibracja, burnout, pusty bak, energia, recall, blokada auta, opłacalność;
  - lojalność: +1 na dobę, maks. 1, brak spadku, status Lojalny, dziennik;
  - dashboard i i18n;
  - **determinizm**: jedno rozliczenie po 30 h daje identyczną gotówkę, auta, kursy, emocje i lojalność jak rozliczanie co 10 min.
- Test determinizmu wykrył prawdziwy błąd lojalności: minimum doby pomijało odcinek kończący się o północy. Naprawiony przed commitem.
- **Świadomie zaktualizowane stare testy.** Zakładały „auto przypięte do NPC”, a teraz sprawdzają nowe reguły:
  - `test_npc_shift`: walidacja wysyłki, auto na starej trasie → autobus, `npcCars`;
  - `test_fuel`: paliwo zużywane przez kursy, a nie przez zmianę; przesiadka do autobusu przez fallback;
  - `test_npc_batch`: łączenie trzech NPC w jednym SUV-ie;
  - `test_npc_manager`: `pref_car`;
  - `test_assistant`: auta tylko z kierowcą, nowa porada `need_driver`.
- **E2E (stary frontend, regresja): 36/36 PASS** (`e2e-part.sh`, obie połowy, bez powtórek).

## Poprawione przy okazji

- `/dashboard` → `npc.capacity` było zawsze `null` (zły klucz `capacity` zamiast `slots`).

## Nie zrobione / do decyzji

- Opcja AI Managera `taxi_idle` (wolni kierowcy sami jeżdżą Taxi) z §7 projektu jest **odłożona**. Wysyłanie kierowców przez managera offline wymaga osobnego kroku w pętli zdarzeń. Mogę ją dodać jako kolejny commit.
- Asystent (`/assistant`) prognozuje transport w przybliżeniu: auto, jeśli teraz jest wolny kierowca. Rozliczenie jest dokładne.
- Stary frontend (`online/web/`) jest zamknięty i nie pokazuje ról ani Taxi. To zadanie dla Fluttera (ekran „Ekipa”).
