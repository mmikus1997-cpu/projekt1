# Raport: Etap 1 migracji GDD v3.1 (naprawy krytyczne)

Gałąź: `feature/gdd-v31-migration` (repozytorium `city-empire/online`)
Punkt wyjścia: `f512bdf` (v0.59.0) → koniec etapu: `ad02406`
Zmiany: 19 plików, +937 / −34 linii, **13 commitów**, w każdym jedna zmiana

## Wynik regresji

| Pakiet | Przed etapem | Po etapie |
|---|---|---|
| pytest | 216 passed | **273 passed, 0 failed** (+57 nowych testów) |
| E2E Playwright | — | **37/37 OK** (33 PASS + 3 skrypty bez błędów: `probe-energy`, `smoke-451`, `test-avatar`; `test-econstats` PASS po ponownym uruchomieniu) |

Sprostowanie do Raportu 7: w repozytorium jest **37** testów E2E (`tests/*.cjs` bez `shot*`), a nie 41. Testów pytest przed etapem było **216**, a nie 229. Obie wcześniejsze liczby pochodziły z grepa, który liczył też pliki i funkcje niebędące testami.

## Zadania

| # | Zadanie | Commit | Pliki | Nowe testy |
|---|---|---|---|---|
| 1.1 | `route_claim`: brak trasy w katalogu nie daje już 500; auto wraca do garażu, wpis w dzienniku | `2633a0a` | economy.py | 2 |
| 1.2 | `service_vehicle`: wycofany model jest odstawiany z użycia bez opłaty | `c05de23` | economy.py | 2 |
| 1.3 | Exploit eventów: mnożnik zamrażany przy starcie (`ev`); stare zadania liczone z `end` | `ed01430` | economy.py | 4 |
| 1.4 | Auto nie może być jednocześnie w trasie NPC i w podróży (oba kierunki) | `2b1f501` | travel.py, economy.py | 5 |
| 1.5 | `rate_limits`: indeks na `until_at` + czyszczenie co 10 min (wpisy starsze niż 24 h) | `1b5fabf` | app.py | 3 |
| 1.6 | `combat_version` w `matches` (1.0) i `pvp_battles` (2.0), migracja addytywna, wartość domyślna dla starych walk | `ab460c7` | combat.py, app.py, pvp.py | 4 |
| 1.7 | `manage.py`: operator (`os_user`, host, argv), `cash_before`/`cash_after`, audit `backup` | `230fd61` | manage.py | 4 |
| 1.8 A1 | Data urodzenia przy rejestracji, minimum 12 lat, poniżej 16 lat zgoda opiekuna, token jako SHA-256, Mailer dev-stub | `c8552db` | age.py (nowy), app.py | 10 |
| 1.8 A2 | `/api/me` → `ageGate`; `POST /account/birth-date` (poniżej 12 lat: usunięcie konta); `POST /guardian/verify` | `c8da173` | app.py | 8 |
| 1.8 A3 | Blokada kont `pending` w `auth()`; usuwanie po 7 dniach; `POST /guardian/resend` | `d4bd049` | app.py | 7 |
| 1.8 A4 | Sklep: `minor` liczony z daty urodzenia; `checkout` ponownie sprawdza wiek | `377f9af` | shop.py | 5 |
| 1.9 | Hełm Lochu wypada na 9. piętrze (Strażnik Bramy) | `50546e8` | dungeon.py | 2 |
| 1.10 | „Tydzień Nauki” → „Dzień Nauki” (ikona 📚 w osobnym polu) | `ad02406` | economy.py | 1 |

## Zmiany w bazie (wszystkie addytywne, stare bazy migrują się przy starcie)

| Tabela | Zmiana |
|---|---|
| `rate_limits` | indeks `rate_limits_until` |
| `matches`, `pvp_battles` | kolumna `combat_version TEXT` (NULL = stara walka) |
| `accounts` | `birth_date`, `guardian_email`, `guardian_status` (domyślnie `'none'`), `guardian_token_hash`, `guardian_token_exp` |
| `state_json` | nowe klucze: `ev` (w kontraktach i trasach), `travelCar` |

## Nowe endpointy

| Metoda | Ścieżka | Dostęp |
|---|---|---|
| POST | `/api/account/birth-date` | zalogowany (działa też dla konta `pending`) |
| POST | `/api/guardian/verify` | publiczny (token od opiekuna) |
| POST | `/api/guardian/resend` | zalogowany `pending`, limit 3 na dobę |

Wszystkie są dopisane do allowlisty tunelu podglądu.

## Backupy (oryginały v0.59, nie są w git)

`server/economy.py`, `travel.py`, `app.py`, `combat.py`, `pvp.py`, `shop.py`, `dungeon.py` oraz `manage.py` z sufiksem `.backup_v059`; pełna kopia folderu: `server.backup_v059/`.

## Otwarte sprawy

1. **Faza B zadania 1.8 (frontend):**
   - pole daty urodzenia i e-maila opiekuna w rejestracji;
   - ekran „uzupełnij datę”;
   - ekran „czekamy na opiekuna” z przyciskiem ponownej wysyłki;
   - strona weryfikacji dla opiekuna;
   - po tym włączenie `CITY_REQUIRE_BIRTH_DATE=1`.

   Do tego czasu flaga jest wyłączona, a obecny UI działa bez zmian.
2. **Mailer** jest dev-stubem (token trafia do logu). Przed premierą trzeba podpiąć SMTP albo zewnętrzną usługę.
3. **Niestabilne testy E2E:** `test-routes` i `test-econstats` sporadycznie nie przechodzą przy starcie Chromium; przy ponownym uruchomieniu przechodzą.
4. **Środowisko:** sandbox często resetuje pip i Playwright, za każdym razem instaluję je ponownie. Dane autora commitów są w `~/.gitconfig`, bo platforma nie zapisuje `.git/config`.
