# Raport 5 — Akcje `POST /api/worlds/{wid}/actions` (v0.59.0)

Pole `action` przyjmuje 27 wartości (`Literal` w app.py), a logika jest w `economy.apply` (economy.py). Błąd reguły zwraca 409 `{detail}`.
W podróży zablokowane są: contract, train, tender_accept, home_train, remote_work, gather, sell_materials (economy.py:261). collect, upgrade i buy_business działają tylko w dzielnicy 2 (economy.py:295).

| # | kind | Co robi | Koszt | Nagroda | Źródło |
|---|---|---|---|---|---|
| 1 | contract | Dodaje kontrakt do kolejki (max 4), wymaga poziomu i lokalizacji | energia z katalogu | (przy odbiorze) | economy.py:296 |
| 2 | claim_contract | Odbiera ukończony kontrakt | — | $ wg 2.4 + XP; auto +6 wear | economy.py:306 |
| 3 | train | Trening statystyki (kolejka 4, 5 min) | 50 $ (−Charyzma do 9%) + 5 energii | (przy odbiorze) | economy.py:324 |
| 4 | claim_training | Odbiera trening | — | +1 do statystyki | economy.py:306 |
| 5 | home_train | Trening w mieszkaniu | 12 energii | +1 do statystyki po odbiorze | economy.py:331 |
| 6 | buy | Kupno przedmiotu (poziom, bez unikatów z Lochu) | cena (−Charyzma do 9%) | przedmiot | economy.py:338 |
| 7 | equip | Zakłada posiadany przedmiot | — | statystyki przedmiotu | economy.py:338 |
| 8 | buy_business | Kupno Café / Studia | 2500 / 4000 $ | firma idle | economy.py:350 |
| 9 | collect | Wypłata skarbca firmy (min 1 $) | — | $ ze skarbca | economy.py:356 |
| 10 | upgrade | Rozbudowa firmy (10 min, Era I max poz. 2) | COSTS (−Int) | wyższa stawka | economy.py:356 |
| 11 | tutorial_dismiss | Zamyka samouczek | — | — | economy.py:373 |
| 12 | buy_residence | Zakup lepszej rezydencji | cena | regeneracja, sloty garażu, odpoczynki | economy.py:374 |
| 13 | rest_start | Start odpoczynku (wymagany tier rezydencji) | wg RESTS (Raport 1) | (przy odbiorze) | economy.py:390 |
| 14 | rest_claim | Odbiór odpoczynku | — | +energia (do 240) | economy.py:464 |
| 15 | buy_vehicle | Zakup auta (poziom, Era III premium, VIP, miejsce) | cena | auto w garażu | economy.py:407 |
| 16 | equip_vehicle | Wybór auta w użyciu | — | skrócenie kontraktów | economy.py:419 |
| 17 | upgrade_vehicle | Ulepszenie auta (max 3) | koszt ulepszenia | +zniżka czasu | economy.py:424 |
| 18 | service_vehicle | Serwis przy wear 100 | serwis (−15%/poz. Tanie Naprawy) | wear 0 | economy.py:433 |
| 19 | hire_staff | Pracownik na 24 h | 250–500 $ | +25% dochodu firmy | economy.py:439 |
| 20 | tender_accept | Dzienny przetarg (1/dobę) | energia | $ ×1,10–1,30 + XP | economy.py:447 |
| 21 | invest | Prywatna inwestycja w dzielnicę | 100–5000 $ (max 20 000) | +1%/1000 $ do kontraktów w dzielnicy | economy.py:456 |
| 22 | remote_work | Praca zdalna PC (mieszkanie, Era II, 7 dni) | 10 energii | 150 $ (+Int do 30%), 25 XP | economy.py:382 |
| 23 | gather | Wydobycie w lokacji surowcowej | energia surowca | 2–4 szt. | economy.py:262 |
| 24 | sell_materials | Sprzedaż w mieście (dzielnice 1, 3–6) | — | cena dzielnicy × ilość × event | economy.py:270 |
| 25 | upgrade_building | Poziom budynku dzielnicy (max 5) lub otwarcie Sali Chwały | 500/1500/3000/6000; Sala Chwały 10 000 | bonusy budynku | economy.py:281 |
| 26 | route_dispatch | Wysłanie kierowcy NPC autem z garażu | 0 | (przy odbiorze) | economy.py:471 |
| 27 | route_claim | Zbiorczy odbiór gotowych tras | — | $ (auto × Garaż × event) + XP | economy.py:481 |

Poza `/actions` (osobne endpointy, Raport 4): podróże, PvP, Loch, sporty, hipodrom, organizacje, sklep, awatar, klasa i ewolucja.

---

# Raport 6 — UI (web/, vanilla JS, SPA)

**Styl:** granat `#0b1220`, electric blue `#4aa8ff`, złoto `#c9a227` / `#d4af37` / `#d4af70`, linie `#20304b` / `#33517c`, zieleń `#7fb069`, biel `#ffffff`. Font: `Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif` (style.css), monospace dla liczb. Grafiki są tłami (`web/art/`).

| Element | Opis | Źródło |
|---|---|---|
| Ekran logowania / rejestracji | przełącznik `data-auth-mode`, zgody | network.js, template.html |
| Wybór świata | karty światów, „Wejdź do postaci” | online-game.js |
| Tworzenie postaci | nick, klasa, awatar | online-game.js, avatar.js |
| Sidebar + HUD | gotówka, energia, poziom, nawigacja | online-game.js |
| Nawigacja | `#nav-city` (Moja dzielnica), `#nav-map` (Mapa), `#nav-contracts` (Kontrakty), `#nav-business` (Firmy), `#nav-community` (Społeczność), `#nav-ranking`, `#nav-shop`, `#nav-report`, `#nav-rules`, `#nav-lab`, `#nav-worlds`, `#nav-admin` | template.html |
| Moja dzielnica | 6 budynków (Rezydencja, Garaż, Kawiarnia, Siłownia, Klub, Sala Chwały) z kartami `.bld-level` | online-game.js (0.55) |
| Mapa | mapa miasta zamiast 8 dzielnic, podróż bus/auto, mini-mapa `.mini-map-cta` | online-game.js (0.54) |
| Klub sportowy | turniej, agility, łucznictwo, pływanie, hipodrom, Loch/Ring | extras.js |
| Trasy NPC | `routesPanelHTML` | online-game.js (0.56) |
| Sojusz | budynki sojuszu, fundusz, kontrakty, czat | online-game.js (0.57) |
| Event czasowy | `.tev-panel` | online-game.js (0.58) |
| Chmurka powiadomień | `#notif-bell` | online-game.js (0.59) |
| Sklep | bramka 16+/opiekun, 8 SKU, baner „dev” | online-game.js |
| Lista dokładnych przycisków per ekran | **DO WERYFIKACJI** (generowane dynamicznie w JS) | — |

---

# Raport 7 — Testy

**pytest:** 47 plików, 229 funkcji `test_`. Top 10 według liczby testów:

| # | Plik | Testów | Zakres |
|---|---|---|---|
| 1 | test_api.py | 26 | auth, CSRF, stan, akcje, idempotencja |
| 2 | test_features.py | 17 | organizacje, czat, moderacja, terytoria |
| 3 | test_avatar.py | 11 | awatar, garderoba |
| 4 | test_travel.py | 10 | podróże, blokady |
| 5 | test_evolutions.py | 10 | ewolucje klas |
| 6 | test_pvp_active.py | 7 | PvP 2.0, limity, Elo |
| 7 | test_horse_racing.py | 7 | hipodrom, hodowla |
| 8 | test_shop.py | 6 | bramka, opiekun, limity |
| 9 | test_residence_v2.py | 6 | rezydencje, odpoczynki |
| 10 | test_preview_transport.py | 6 | tunel podglądu |

**E2E (Playwright CJS):** 41 plików. 10 najważniejszych:

| # | Plik | Zakres |
|---|---|---|
| 1 | test-online.cjs | pełny przepływ: rejestracja → postać → gra |
| 2 | test-economy.cjs | kontrakty, trening, zakupy |
| 3 | test-idle.cjs | Kawiarnia i skarbiec |
| 4 | test-map.cjs | mapa i podróże |
| 5 | test-district.cjs | Moja dzielnica, budynki |
| 6 | test-routes.cjs | trasy NPC |
| 7 | test-alliance.cjs | sojusze, budynki sojuszu |
| 8 | test-shop.cjs / test-guardian.cjs | sklep i zgoda opiekuna |
| 9 | test-dungeon.cjs | Loch |
| 10 | test-notif.cjs / test-timedevent.cjs | powiadomienia i eventy |

Uruchamianie: `pytest tests/`; E2E: `bash tests/qa-suite.sh NAZWA PORT node tests/X.cjs`.

---

# Bonus — liczby

| Miara | Wartość |
|---|---|
| Python (server/, 15 plików) | 3 628 linii (długie, gęste linie) |
| JS (web/, 8 plików) | 2 187 linii |
| CSS (web/) | 1 128 linii |
| Testy py / CJS | 5 688 / 2 718 linii |
| Tabele | 43 |
| Endpointy | 105 (8 publicznych, 83 zalogowanych, 3 staff, 11 admin) |
| Akcje `/actions` | 27 |
| Testy | 229 pytest w 47 plikach + 41 E2E |
| Baza dev | `data/city_empire.sqlite3` 596 KB |
