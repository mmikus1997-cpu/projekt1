# RAPORT: Etap 5, walka [GDD v3.1 5.1–5.4], rewizja 2: Klasa = Taktyka

**Status:** zaimplementowane i przetestowane, czeka na akceptację.
**Gałąź:** `feature/gdd-v31-migration` · **Diffy:** `PROJEKT-ETAP-5.md`
**Testy:** pytest **404 passed** · E2E **36/36 PASS** (1 retry: `test-chronicle`, znany niestabilny)

## Commity rewizji 2

| Commit | Zakres |
|---|---|
| `5c50036` | 5.1: Klasa = Taktyka, RPS klas, riposty, FATIGUE, logi pod Fluttera, usunięcie wyboru taktyki i szablonów obrony |
| `8f20b27` | 5.3: limit pary 3 → 4 walki na 24 h |
| `c574057` | E2E: okno PvP bez wyboru taktyki, Loch na klasie Szybki |

Z rewizji 1 zostają bez zmian: 5.2 HP (`7cac8ac`), 5.3 nagrody i limit 15/dobę (`00e7af3`), 5.4 sezony (`bab0e6a`). Frontend vanilla nietknięty.

## 5.1 Klasa = Taktyka, walka do 0 HP, FATIGUE

### Klasa → taktyka (na stałe)
| Klasa | Taktyka | Sekwencja |
|---|---|---|
| ⚔️ Bokser (ATTACKER) | 🔥 Presja | Cios → Mocny → Cios |
| 🛡️ Obrońca (DEFENDER) | 🛡️ Kontrola | Cios → Unik → Mocny |
| 💨 Szybki (FAST) | 🎯 Kontra | Unik → Cios → Unik |

- Postać bez wybranej klasy walczy klasą wynikającą z dominującej statystyki (jak dotąd).
- **Usunięte:**
  - `POST /api/worlds/{wid}/tactic`;
  - `POST /api/worlds/{wid}/pvp/defense` (szablon obrony to też wybór taktyki);
  - bramki „Najpierw wybierz taktykę” w PvP, wyzwaniach, Lochu i turnieju;
  - pola `tactic` i `pvpDefense` w stanie postaci: usuwane leniwie przy `sync`. Bez zmian w schemacie SQL, bo to pola w JSON.
- `character.tactic` w pakiecie stanu jest wyliczane z klasy, tylko do odczytu. Dzięki temu obecne UI nie pokazuje już wyboru taktyki, a okno pojawia się tylko wtedy, gdy postać nie ma klasy.

### Przewaga klasowa (RPS)
Bokser > Obrońca > Szybki > Bokser. Klasa z przewagą dostaje:
- +15% obrażeń;
- +10% siły pasywki klasy:
  - Bokser: premia do mocnego ciosu;
  - Szybki: premia do szybkiego ciosu i do inicjatywy;
  - Obrońca: siła riposty.

Działa w obu silnikach. W 1.0, gdzie klasy nie mają pasywek, +10% dotyczy szansy na krytyka.

### ⚠️ Co musiałem dodać, żeby trójkąt RPS w ogóle działał
Przy stałych sekwencjach o wyniku decyduje dopasowanie akcji, a nie +15%. Bez dodatkowych reguł:
- Szybki przegrywał z Bokserem przy równych statystykach;
- Obrońca i Szybki nie mogli się nawzajem trafić: każdy cios trafiał w unik, więc było 1000 rund remisu.

Dodałem:
1. **Riposta Obrońcy** (40% szybkiego ciosu, z ewolucją Żelazny Strażnik 75%) po uniku każdego ciosu. Wcześniej działała tylko przy wzajemnym uniku.
2. **Riposta Szybkiego** (80% szybkiego ciosu) po udanym uniku.
3. **Riposta nie działa na klasę, która ma nad nami przewagę.** Obrońca nie riposuje Boksera, Szybki nie riposuje Obrońcy.

**Wynik:** przy równych statystykach trójkąt działa we wszystkich 9 sprawdzonych konfiguracjach (poziomy 1/10/30 × trzy zestawy statystyk). Przy przewadze statystyk ×1,2 klasa kontrowana potrafi wygrać w parach z Bokserem.

**Wyjątek:** Szybki nie wygrywa z Obrońcą nawet przy statystykach ×1,6, bo przed fazą FATIGUE obrażenia zadaje tylko Obrońca. To twarda kontra; do decyzji, czy tak ma zostać.

### Walka do 0 HP i FATIGUE
- Brak limitu rund. 1000 rund zostaje jako awaryjny bezpiecznik (remis).
- **FATIGUE:** od 21. rundy obrażenia obu stron rosną o +5% za każdą rundę (runda 21: +5%, runda 30: +50%).
- **Moje uzupełnienie:** w fazie FATIGUE unik przepuszcza też tę samą część ciosu (runda 21: 5%, od rundy 40: 100%). Sam wzrost obrażeń nie daje nokautu, gdy każdy cios trafia w unik (0 × 1,5 = 0), a specyfikacja wymaga gwarancji KO. Takie trafienie ma w logu wynik `BLOCKED_PARTIAL`.
- **Efekt:** we wszystkich 9 parach klas walka kończy się nokautem. Remis zostaje tylko wtedy, gdy obie strony nic nie robią (same uniki), co przy sekwencjach klas nie występuje. Taki przypadek jest wykrywany dopiero przy pełnym zmęczeniu, zamiast liczyć 1000 pustych rund.
- Reguła „trzeci unik z rzędu nie działa” zostaje jako zabezpieczenie, ale żadna sekwencja klasy jej nie uruchamia.

### Logi pod animacje Fluttera
Każda runda (`rounds[]`) ma pola `attacker_action`, `defender_reaction`, `result` (pierwsza wymiana w rundzie), `fatigue` oraz `exchanges[]`, czyli obie wymiany w kolejności inicjatywy. Każda wymiana zawiera `striker`, `attacker_action`, `defender_reaction`, `result`, `damage` i `hp`.

| Sytuacja | attacker_action | defender_reaction | result |
|---|---|---|---|
| Szybki / mocny cios trafia | `PUNCH_FAST` / `PUNCH_HEAVY` | `TAKE_HIT` | `FULL_HIT` |
| Trafienie klasy z przewagą | `PUNCH_*` | `TAKE_HIT` | `CRITICAL_HIT` |
| Riposta po uniku | `KNEE_STRIKE` | `TAKE_HIT` | `FULL_HIT` / `CRITICAL_HIT` |
| Unik (cel Obrońca) | `PUNCH_*` | `PARRY_HAND` | `PARRIED` |
| Unik (inny cel) | `PUNCH_*` | `DODGE_SIDE` | `MISSED` |
| Zderzenie ciosów albo unik w fazie FATIGUE | `PUNCH_*` | `GUARD_BLOCK` | `BLOCKED_PARTIAL` |

W walce 1.0 (Sparing) każde zdarzenie ma te same pola:
- akcja: `PUNCH_HEAVY` przy krytyku, w pozostałych przypadkach `PUNCH_FAST`;
- reakcja: `TAKE_HIT` albo `DODGE_SIDE`;
- wynik: `CRITICAL_HIT` / `FULL_HIT` / `MISSED`.

Wersje silnika: `ENGINE_V1 = 1.2`, `ENGINE_V2 = 2.2`. Stare raporty bez wersji pokazują `1.0`/`2.0`.

## 5.2 HP (bez zmian względem rewizji 1)
- Walka 1.0 (Sparing, Loch): `200 + 5×Cha + 2×Lvl`.
- Walka 2.0 (PvP, turnieje): `80 + 2×Cha + Lvl`.

## 5.3 Nagrody PvP
- Wygrana: 500 $ + 50 XP + 1 PP. Przegrana: 100 $ + 10 XP. Remis: 200 $ + 25 XP.
- Nagrody dostają obie strony, w PvP 2.0 i w wyzwaniach 1.0.
- Limit 15 walk rankingowych na dobę UTC.
- **Limit pary:** maks. **4** walki z tym samym przeciwnikiem w oknie 24 h; piąta jest blokowana (409). Liczone razem z wyzwaniami 1.0.

## 5.4 Rankingi miesięczne (bez zmian względem rewizji 1)
- Sezon Elo per świat = miesiąc UTC. Reset do 1000 o 00:00 UTC 1. dnia miesiąca.
- Nagrody: Top 10 ramka diamentowa + 600💎 + tytuł; Top 100 ramka złota + 200💎; Top 1000 ramka srebrna + 50💎.
- Ranking XP jest all-time (Świątynia Sławy), bez resetów.

## Testy
- **Nowe lub przepisane:**
  - `test_tactics.py`: endpointy usunięte, taktyka z klasy, usuwanie starego pola, bramki;
  - `test_combat_v5.py`: trójkąt RPS, rampa FATIGUE, słownik logów, dawny pat kończy się KO;
  - `test_pvp_active.py`: sekwencje z klas, logi w raporcie, limit pary 4.
- **Zaktualizowane:** `test_api`, `test_classes` (inicjatywa 13,3 z pasywką), `test_evolutions` (riposta Szybkiego, tolerancja zaokrągleń), `test_sports2`, `test_combat_version`.
- **E2E:** `test-classes` (w oknie 0 taktyk), `test-online` (okno tylko bez klasy), `test-dungeon` (klasa Szybki).

## Do decyzji
1. Reguły ripost (pkt „Co musiałem dodać”): OK?
2. Unik w fazie FATIGUE przepuszcza część ciosu: OK? Bez tego KO nie jest gwarantowane.
3. Szybki przeciw Obrońcy to twarda kontra (nie do wygrania statystykami): zostawić czy złagodzić?
4. W obecnym UI postać bez klasy wchodzi do Lochu klasą z dominującej statystyki, bo okno klasy pokazuje się tylko w PvP. We Flutterze proponuję wymagać wyboru klasy przy tworzeniu postaci.
