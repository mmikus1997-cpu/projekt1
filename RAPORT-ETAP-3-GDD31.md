# Raport: Etap 3 (Auta), migracja do GDD v3.1

Gałąź `feature/gdd-v31-migration`, od `e5ade38` (koniec Etapu 2) do `ae6972c`.
Zmiany tylko w backendzie, bez frontendu vanilla JS. UI zrobimy we Flutterze.

## Commity
| commit | zadanie |
|---|---|
| `621b799` | 3.1 Katalog 5+1 aut, leniwa migracja garaży, SQL `npcs`/`vehicles` |
| `6070be3` | 3.2 Paliwo per auto, spalanie za przystanek, przesiadka do busa, tankowanie (VIP −20%) |
| `50243f5` | 3.1 E2E `test-district`: 6 kart aut |
| `7b8aae4` | 3.3 Zużycie per auto, serwis wskazanego auta, Automatyczny Mechanik |
| `ae6972c` | 3.4 Licznik dni aktywności i Mistrz Rankingu za 7 dni |

## Testy
- **pytest: 373 passed**, przed Etapem 3 było 366. Nowe pliki testów: `test_wear.py` (5), `test_milestones.py` (2), wcześniej `test_fuel.py` i `test_garage_v2.py`.
- **E2E: 36/36 PASS.** `test-chronicle` przeszedł dopiero przy powtórce; to znany niestabilny test, niezwiązany z autami.

## 3.3 Mechanik
- **Gdzie jest zużycie:** źródłem prawdy jest `s['cars'][vid]['wear']` (0–100). Pole `s['vehicle']['wear']` zostaje jako lustro aktywnego auta, więc stary kod i web działają bez zmian.
- **Migracja:** leniwa, w `sync()`. Aktywne auto przejmuje dotychczasowe zużycie, pozostałe auta startują od 0%. Gdy coś zapisze wprost do starego pola, ten zapis wygrywa (zgodność wstecz).
- **Zużycie 100%:**
  - gracz traci rabat czasu kontraktu (`vehicle_discount = 0`);
  - NPC traci przyspieszenie (`travel_ms`: współczynnik nie lepszy niż 1,0);
  - NPC nie zużywają aut.
- **`service_vehicle {vehicle?}`:** serwisuje wskazane auto, a bez parametru aktywne. Koszt to `service` z cennika × zniżka sojuszu `cheap_repair`.
- **`auto_mechanic`:** wszystkie auta wracają do 0% za 2000 $ (VIP 1000 $). Gdy nie ma nic do naprawy, zwraca 409.
- Tabela `vehicles.condition` jest synchronizowana przy obu akcjach.

**Naprawiony przy okazji błąd z 0.59:** przełączenie auta na inne i z powrotem zerowało zużycie, co dawało darmowy serwis. Teraz każde auto pamięta własne zużycie.

**Zmiana zachowania (do Twojej decyzji):** ręczny serwis działa przy każdym zużyciu > 0%. Wcześniej był możliwy dopiero przy 100%.

## 3.4 Mistrz Rankingu
- **Nowy moduł `server/longplay.py`** z tabelą `longplay_milestones(character_id, active_days, last_active_utc, claimed_milestones)`. Tabela powstaje przez `CREATE IF NOT EXISTS`, kompatybilnie wstecz.
- **Liczenie dni:** hak w `own()` liczy każde żądanie do świata. Pierwsze żądanie w nowym dniu UTC dodaje 1 do `active_days`; kolejne tego dnia kończą się na jednym SELECT. Dni nie muszą być kolejne.
- **Nagroda przy ≥7 dniach (jednorazowa):**
  - auto `mistrz` trafia do garażu (nie zajmuje miejsca) z pełnym bakiem i 0% zużycia;
  - gdy gracz nie ma aktywnego auta, Mistrz staje się aktywny;
  - wpis w dzienniku postaci, zdarzenie `milestone.unlocked` i wpis w audycie;
  - ta sama odpowiedź API już zawiera nagrodę.
- **Nowy endpoint `GET /api/worlds/{wid}/milestones`** pod Fluttera: postęp i odebrane nagrody. Jest dodany do allowlisty.

## Świadomie pominięte (zgodnie z ustaleniami)
- **Blokada auta na czas naprawy:** obecny spec jej nie wymaga, serwis działa natychmiast.
- **Mechanik za 50💎 / VIP 25💎:** czeka za `feature_flag_premium_currency=False` i zostanie dodany razem z walutą.
- **Stary web:** przy Mistrzu widać przycisk kupna za 0 $ (serwer odrzuca go błędem 409). UI zostaje dla Fluttera.
