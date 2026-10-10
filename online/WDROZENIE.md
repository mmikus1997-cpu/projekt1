# CITY EMPIRE 0.7 — przygotowanie stałego wdrożenia

**Status: instrukcja i przygotowane narzędzia, nie uruchomiona usługa produkcyjna.** Nie kupiono serwera, domeny ani magazynu kopii. Podgląd Arena jest środowiskiem rozwojowym; procesy mogą być zatrzymywane. Zapisane pliki nie są gwarancją dostępności ani niezależnego odtworzenia po awarii.

**0.55.0:** Serwer + klient: akcja `upgrade_building` (model `Action`, pole `building`), katalog `buildings`/`buildingMax`/`buildingCosts`/`hallCost`, stan `state.buildings` (start: hall=0, reszta=1; migracja `sync()` dokłada klucz `buildings`); `manage.py grant-cash <user> <kwota>`. Klient: budynki zastępują zakładki (widoki `residence/garage/cafe/character/arena/hall`), hub klubu z kartami dyscyplin. Kontrakty: erowe zamknięcie tylko miast (surowce otwarte). Rebuild `python3 build.py` wymagany.
**0.54.0:** Serwer + klient: nowe akcje `gather`/`sell_materials` (model `Action`), katalog materiałów (`materials`/`matBuy`/`matBase`), renamy dzielnic w `travel.py`/`economy.py` + remap `INVEST_RENAME` w `sync()` (automatyczny, bez migracji SQL). Wymagany rebuild `python3 build.py` + restart serwera. Nowe pliki: `web/art/loc-quarry.jpg`, `web/art/loc-forest.jpg`.
**0.53.0:** Wyłącznie CSS/JS/HTML klienta (zakładki klubu + przekierowania nawigacji). Wymagany rebuild `python3 build.py`. Bez zmian serwera i reguł gry. Testy E2E zaktualizowane pod nową nawigację.
**0.52.3:** Wyłącznie CSS/JS klienta (układ nagłówka huba, kompresja kafelków, usunięcie paska powrotu z huba). Wymagany rebuild `python3 build.py` (CSS inline w index.html). Bez zmian serwera i reguł gry.
**0.52.2:** Klient: okno briefu po wejściu na świat (stan `packet.away` + `catalog.tender` — bez nowych endpointów); akcje przez istniejące `actions` (`tender_accept`) i `data-map-go`; grafiki w `web/art/loc-*.jpg` serwowane istniejącą trasą `GET /art/{name}`. Zero zmian reguł gry i transportu.
**0.52.1:** Wyłącznie CSS/JS klienta: tło mini-mapy, warunek widoczności „Pierwszych kroków", usunięcie panelu z huba. Bez zmian serwera.
**0.52.0:** Skin prezentacyjny: dwie grafiki (web/art/*.jpg) serwowane nową trasą GET /art/{name} (walidacja nazwy, brak listingu, trawersacja niemożliwa); zmienne kolorów nadpisane wyłącznie w zakresie .online-version — wszystkie reguły gry, akcje i transport bez zmian.
**0.51.3:** Wyłącznie wartości CSS (desktop ≥901px) w istniejących selektorach — paddingi wierszy rankingów, paneli społeczności i kart firm; HTML/JS/endpointy nietknięte, reguły gry bez zmian.
**0.51.2:** Zmiana czysto prezentacyjna okładki autoryzacji: popover szczegółów świata nie zmienia żadnych danych ani akcji (wejście do świata nadal przez `data-world` z pełną walidacją); breakpoint 680px rozdziela popover (desktop) od inline (mobile/dotyk).
**0.51.1:** Wyłącznie wartości CSS (desktop ≥901px) w istniejących selektorach — portrety, paddingi, wysokość topbara; HTML i JS nietknięte. Zero wpływu na reguły gry, akcje i transport.
**0.51.0:** Redesign czysto prezentacyjny: nowe klasy (`.tender-bar`, `.ab-*`, `.hub-side`) i kompozycje flex/grid w CSS — zero nowych endpointów, akcji i pól stanu; wszystkie akcje (przetarg, kontrakty, mieszkania, odpoczynek) idą istniejącymi ścieżkami z walidacją serwera. Nadpisania gęstości ograniczone do `@media(min-width:901px)`, więc bazowe reguły mobile pozostają nietknięte (28 layoutów test-online bez zmian). `.away-box` i `.tender-panel` zachowują selektory i teksty testów E2E.
**0.50.0:** Chip auta to czysta prezentacja stanu (`state.vehicle` + katalog) — nie dodaje żadnych uprawnień ani akcji; akcje garażu nadal idą przez serwer z pełną walidacją. Routing z mapy tylko wybiera zakładkę UI (`setSportTab`), nie omija bram poziomów/er — te nadal egzekwuje dialog mapy i serwer.

**0.49.1:** Zmiany czysto prezentacyjno-nawigacyjne: loch podpięto pod istniejący mechanizm zakładek (render panelu w `applySportTab`), tryb Laboratorium nadal ustawia wyłącznie lokalne, testowe zestawy statystyk (bez wpływu na prawdziwy postęp), a brama VIP/lochu nie zmieniła zasad (loch od 3. poziomu, 8 energii/piętro). Usunięte elementy (panel trybu, pasek podglądu) nie miały żadnej roli reguł gry.

**0.49:** Garaż to część gry, nie kosmetyka: ulepszenia i VIP są egzekwowane serwerowo (`upgrade_vehicle` z limitem 3 poziomów i stanem `garageUp`; brama VIP w `buy_vehicle` czytana z `shop_state.vip_until`), a rabat czasu liczy się zawsze z jednego źródła (`vehicle_discount` = auto + ulepszenia, 0 przy zużyciu 100%). Migracja starych zapisów dodaje `garageUp` automatycznie — nic nie trzeba robić ręcznie. Panel wyzwań PvP został doczyszczony (martwe filtry i handler usunięte).

**0.48:** Animacje są wyłącznie wizualizacją autorytatywnego raportu: warianty lotu, tarczy i póz wybrane deterministycznie z numeru rundy — powtórka jest wierna, wyniku nie da się „animować na inny”. Płeć to cecha wyglądu (walidowana po stronie serwera), bez jakichkolwiek różnic statystyk. Zaproszenia do gildii przechodzą przez istniejący endpoint organizacji z pełnymi limitami i blokadami kontaktu; panel PvP ujawnia wyłącznie dane publiczne (tag gildii zapraszającego). „Napisz” otwiera istniejący, moderowany DM.

**0.47:** Sprzęt↔wygląd: `gameLooks` w katalogu mapuje przedmioty gry na warstwy awatara (kompozycja i covers nadal w `server/avatar.py`); raporty PvP (`accept`, `attack`, odtwarzanie) i listy (`players`, `pvp/targets`) ujawniają wyłącznie wygląd i nazwy założonych rzeczy — nigdy statystyk przeciwnika. Chip ruchu na arenie to prezentacja ostatniego ciosu; wynik i tak liczy wyłącznie serwer. Karty światów: szczegóły przeniesione do rozwijanej sekcji hover/focus (na dotyku rozwinięte) — bez utraty informacji RODO/test-disclaimer.

**0.46:** Awatar to wyłącznie warstwa prezentacji: katalog i reguły noszenia liczy `server/avatar.py` (serwer), klient tylko renderuje SVG; rzeczy zmieniają wygląd, nigdy statystyki. VIP jest czytany z istniejącego `shop_state` (ta sama bramka co sklep) — awatar nie tworzy nowej monetyzacji ani presji: rzeczy VIP nie mają countdownów, a „gratis na start" dotyczy tylko rzeczy zwykłych. `GET /api/account/rankings` ujawnia wyłącznie publiczne rankingi (TOP 10 światów + globalny) — te same, które widać w grze; jest w allowliście GET koperty preview. Kupno garderoby idzie przez zwykłe `db.tx()` z audytem i limitami częstotliwości.

**0.45.2:** `economy.sync` dostał strażniki typów wejścia (staff/garage/invested/residence/completed) — to sama witalizacja kształtu zapisu, żadnych nowych reguł ani ścieżek zapisu. `GET /api/account/profile` jest tylko-do-odczytu, dziedziczy uwierzytelnianie sesyjne i ujawnia wyłącznie dane, które gracz i tak widzi po zalogowaniu (własne postacie) — dla RODO neutralne; endpoint jest w allowliście GET koperty preview. Klik w nick nie tworzy nowych uprawnień. Usunięcie 18 tytułów z konta testowego to jednorazowa operacja danych w środowisku dev (bez wpływu na mechanikę tytułów).

**0.45.1:** Poprawki prezentacyjne: zoom z centrum i podpowiedzi przy kursorze nie zmieniają żadnych reguł; naprawiony „Przyspiesz (VIP)" to wyłącznie formater czasu po stronie klienta — serwerowa połowa pozostałego czasu i bramka VIP (state_json `vipUntil`) działały od 0.14 bez zmian.

**0.45:** Brama „kontrakt w swojej dzielnicy" i bonus za dojazd są liczone wyłącznie serwerowo (E.action + payout), więc UI nie może ich obejść — podróż jest częścią ekonomii, a nie kosmetyką. Dane o władzy dzielnic pochodzą z jedynej źródła prawdy (territory_state z 0.11) i są tylko odczytywane. Odliczenia Er używają istniejącego kalendarza światów — brak nowych liczników do windowania presji.

**0.44:** Zmiany 0.44 są czysto prezentacyjno-nawigacyjne plus jedno narzędzie operatorskie: paperdoll ekwipunku, przeniesienie lochu do klubu i zaokrąglenia bonusów nie dotykają żadnej reguły serwera (statystyki, ceny i walki liczy dalej wyłącznie backend). `seed_sparring.py` tworzy wyłącznie zwykłe konta testowe tym samym API co gracze — bez podkręconych uprawnień, z hasłem zgłoszonym właścicielowi; w produkcji skrypt pozostaje narzędziem administratora, nie częścią instalacji gracza.

**0.43:** Nowe endpointy sportu dziedziczą te same bramki co reszta gry: koszt Energii i dobowe limity liczone serwerowo, rekordy i rankingi per-świat, brak jakichkolwiek realnych pieniędzy (wpisowe hipodromu wyłącznie w wirtualnych $, zero obstawiania — zasada z 0.31 bez zmian). Karta zawodnika (klasa) przesunięta z kreacji do pierwszego PvP zmniejsza powierzchnię RODO: konto tworzy postać bez domysłów gameplayowych, a wybór trwały i jednorazowy następuje w momencie, gdy gracz świadomie wchodzi w rywalizację. Bonus pływania jest częścią deterministycznego liczenia statów po stronie serwera (0.35) — UI tylko czyta.

**0.42:** Auto-atak nie otwiera nowych dróg do nadużyć: to ten sam rankingowy silnik co wyzwania (ten sam limit dobowy, blokady, bramki lvl 2 i wymóg taktyki), tylko bez kroki czekania — obrońca jest reprezentowany wyłącznie przez swój trwały zapis (taktyka/szablon), więc „auto" nie sięga po nic, czego gracz nie zapisał świadomie. Payload ataku jest ignorowany, więc nie da się dołożyć sobie lepszej sekwencji niż zapisana taktyka. Ułamkowe Elo to kwestia prezentacji — zaokrąglamy wyłącznie w UI, stan serwera pozostaje dokładny.

**0.41:** Taktyka to atrybut postaci (state_json), wybierany raz i weryfikowany serwerowo przy każdym starcie walki — nie ma ścieżki, by wybrać ją drugi raz albo narzucić taktykę przeciwnikowi payloadem. Bramki poziomów (PvP 2, Loch 3) egzekwowane po stronie serwera (409), UI pokazuje je tylko jako komunikat. Loch bez własnego wyboru taktyki: używa zapisanego wyboru PvP gracza, więc „zero wyboru przed walką" nie oznacza braku zgody na zasady — gracz świadomie wybrał styl przy PvP. Obowiązkowa klasa wymuszona jest w UI; API zostawia null wyłącznie dla starych zapisów (walka liczy klasę z dominanty, jak wcześniej). PvP pozostaje w pełni konsensualne (wyzwanie+przyjęcie), loch dalej bez realnej kasy i bez Elo.

**0.40:** `biz` i `origin` w `/players` to rozszerzenie presence o te same gwarancje prywatności: tylko online (5-min okno last_seen), offline = null, zero historii i zero tras pojedynczych graczy — na mapie ląduje wyłącznie zagregowana szerokość linii. Sesja foto jest w 100% kliencka (canvas→PNG), więc żaden materiał nie opuszcza przeglądarki. Firmy w wizytówkach pokazują tylko poziom — nie kasy ani skarbców.

**0.39:** Skrzynka DM dziedziczy całą higienę 0.38 (filtry, mute, blokady, limity); read_at to wyłącznie wygoda odbiorcy (nadawca nie dowiaduje się więcej), a `dmUnread` publikowane jest tylko w packetcie właściciela. Dźwięki: syntetyczne WebAudio, brak zasobów i telemetrii, domyślnie włączone ale bardzo ciche, wyłączane jednym klikiem (localStorage). Nowe ogony architektury: eksporty z IIFE online-game idą przez `GameApp.*` (nigdy gołe nazwy), a testy nie mieszają `p.click` na dialogach z atomowymi dispatchami.

**0.38:** DM to osobna tabela z twardymi limitami i pełnym dziedziczeniem moderacji czatu (filtry treści, mute, symetryczne blokady) — żadnych luk w stronie bezpieczeństwa; dzienica w presence i tak publikowana tylko dla online (0.37). Event/sezon/mini-mapa to stricte prezentacja istniejących danych. Nowe ścieżki MUSZĄ trafić do allowlisty koperty preview (GET i POST) — to stały krok przy każdym nowym endpoincie.

**0.37:** Presence i `travel_started` to jedyne zmiany serwerowe: `/players` dokleja `online/district/traveling` (district tylko dla online — prywatność offline'owców), a `travel_started` to kolumna audytowa podróży. Animacja trasy, mgła i skróty budynków liczone wyłącznie po stronie klienta; bramki Er i tak weryfikuje serwer (409). Presence nie ma historii ani realtime — celowo (anty-stalking).

**0.36:** Wielka Mapa Miasta to wyłącznie warstwa prezentacji nad istniejącym API (`travelInfo`, `era`, katalog, `POST /travel` z bramkami ery) — zero migracji, zero nowych endpointów; interakcje (pan/pinch/wheel/klik-vs-drag) liczone po stronie klienta, a podróżowanie z mapy przechodzi przez te same bramki co formularz, więc serwer pozostaje jedynym autorytetem.

**0.35:** Staty ogólne to funkcje pomocnicze `over()/stat_pct()` w `economy` — jeden wzorzec (punkty efektywne powyżej 10, cap procentowy) wpięty w istniejące branche (kontrakty, sync skarbca, claim PC, rozbudowa, buy/trening, parking, invest_bonus) oraz w autostop (`travel`) i siłę NPC (`dungeon`). Bez migracji i bez nowych tabel; postać 10×5 jest matematycznie bit-w-bit jak dotychczas, więc wszystkie stare flow i testy przeszły bez zmian.

**0.34:** 0.34 nie tworzy nowego systemu podsumowań — spina Er-y z istniejącymi sezonami rankingowymi: stałe `SEASON_*` wyniesione na poziom modułu (zachowanie identyczne), payload ery i karta świata tylko odczytują wspólne zegary; archiwum, zdarzenia `season.end` i tytuły kosmetyczne pozostają dokładnie te same (PK sezon+świat chroni przed dublami).

**0.33:** Er-y to jedna kolumna `worlds.world_era` (additive ALTER, przeliczana leniwie z `created_at` — źródłem prawdy jest wiek świata, kolumna to projektowa skrótowa informacja i wyzwalacz wpisu w Kronice). Wszystkie bramki (podróże, cap firm, praca PC, pojazdy premium) to pojedyncze warunki przy istniejących sprawdzeniach — świat testowy i świeże światy standardowe zachowują dotychczasowe flow, a „stary" kod rozliczeń (settle co do tika, brama 7 dni) pozostał nietknięty.

**0.32:** Ewolucje to zero migracji — kolumna `class_evolution` (0.30) zmienia znaczenie wartości (1 = brak, 2 = I stopień wybrany), kod pasywki ląduje w `state_json.evolutionCode`. Silnik symultaniczny dostaje dwa opcjonalne parametry; przy `None` wynik jest bit w bit identyczny z 0.28 (regresja 152 testów). Pasywki probabilistyczne ze specyfikacji odwzorowano deterministycznie (Riposta +35 p.p., Nieuchwytny ×0,9) — gra nie rzuca kostkami, więc postęp zależy wyłącznie od decyzji i treningu.

**0.31:** Lochy stoją w całości na istniejących fundamentach: kolumna `dungeon_progress` z 0.30, silnik symultaniczny z 0.28, system equip/ekwipunku i ekonomia gry — nowy moduł `server/dungeon.py` nie migruje żadnych tabel i nie dotyka rankingu (zero Elo) ani dev-sklepu (unikaty nie są kupowalne, serwer odrzuca zakup 409). NPC i nagrody są deterministyczne z definicji (seed tylko znacznik), więc postęp nie zależy od szczęścia — od treningu.

**0.30:** Klasy i Baza to wyłącznie migracja additive — 4 kolumny `characters` (wzorzec PRAGMA+ALTER jak przy kontach), bez zmian istniejących tabel, ekonomii ani endpointów; `class_type` NULL zachowuje stare zachowanie (klasa z dominanty), brak wyboru w kreatorze = równe statystyki 10×5, więc wszystkie istniejące flow i automatyczne testy przechodzą bez edycji. Podłoga statystyk w silniku UI (10→5) dotyczy tylko walidacji klienta — serwer pozostaje autorytetem.

**0.29:** 0.29 jest czysto addytywne: overlay podróży i dymki czatu to tylko warstwa prezentacji istniejących danych (serwer dokłada wyłącznie nullowalne `org_tag` do wiadomości i nowy endpoint `travel/speedup` bramkowany VIP z `state_json.vipUntil` — ten sam zakup co +25% gotówki z kontraktów; speedup nie dotyka dev-sklepu ani prawdziwych płatności). Kafle huba i pasek powrotu to nawigacja po istniejących widokach, bez zmian stanu.

**0.28:** PvP 2.0 to nowy moduł `server/pvp.py` (tabela `pvp_battles`; szablon obrony w stanie postaci) i silnik `combat.simultaneous` — klasyczne wyzwania i sparingi zostały nietknięte; limit 5 walk/dobę i Elo współdzielone ze starym systemem (jedna drabinka, zero podwójnego liczenia).

**0.27:** hipodrom to nowy moduł `server/sports.py` (tabela `horse_races`, konie w stanie postaci — zero migracji istniejących tabel); wyniki deterministyczne z seeda; wpisanie pucharu do kroniki i +25 prestiżu organizacji dzieje się w transakcji wyścigu; świadomie zero mechanik zakładów — tylko wpisowe sportowe i nagrody za miejsca.

**0.26:** rezydencja 2.0 to zero migracji — pole `slots` w katalogu `RESIDENCES` i dwa nowe rodzaje akcji w `economy.action`; brama 7 dni pracy zdalnej liczy się z kolumn `created_at` (postać ALBO świat) w warstwie API; parkowanie to warunek przy zakupie pojazdu (bez eksmisji istniejących flot).

**0.25:** mapa dzielnic to wyłącznie additive kolumny `characters` + tabela `vehicles`; rozliczanie podróży jest deterministyczne (serwer: czas/opłata z definicji, losowanie tylko autostopu) i dociągane leniwie przy odczycie stanu; bramka firm to jeden warunek w `economy.action` (parametry `district`/`traveling` z warstwy API).

**0.24:** agregaty ekonomii to dwie tabele additive (`world_daily`, `char_daily`, PK obiekt+doba UTC) zasilane w transakcjach czynów; wykresy to SVG renderowane klientowo (bez bibliotek); okno 14 dni.

**0.23:** dystynkcja dnia = dwie tabele additive (`daily_actions` z upsertem dnia, `daily_distinctions` z UNIQUE postać+doba); znaczniki w transakcjach czynów; świadomie bez serii/streaków (bez pętli przymusu).

**0.22:** podsumowanie świata to wyłącznie odczyt istniejących tabel (trasa `admin/worlds/{wid}/summary` na allowliście GET); `REAL-STORE.md` to dokument planu — żaden kod płatności nie powstał.

**0.21:** wizytówka organizacji to wyłącznie odczyt (`GET /worlds/{wid}/organizations/{oid}`); dane z istniejących tabel (organizations, org_members, org_investments, territory_state, org_contracts, chronicle); trasa dopisana do allowlisty GET transportu podglądowego.

**0.20:** bez migracji — `titles` to odczyt istniejącej tabeli `character_titles` w stanie świata (LIMIT 12); zmiany UI: pattern loginu `[A-Za-z0-9_\-]` (flaga `v` Chrome), przełączniki haseł, osłona Energiapaka (ostrzeżenie ≥140, blokada przy 240).

**0.19:** zgoda opiekuna to jedna nowa tabela (`guardian_consents`, częściowy indeks aktywnej zgody) + kolumna `shop_purchases.cents` (ALTER additive). Nowe endpointy `/shop/guardian` i `/shop/guardian/revoke` są na allowliście transportu podglądu. Limit tygodniowy liczy poniedziałek 00:00 UTC.

**0.18:** tablica ogłoszeń re-use tabelę `notices` (bez migracji); nowe jest tylko POST `/api/admin/notices/{id}/delete`; lista ogłoszeń jedzie w stanie świata i w odpowiedzi `/community` (okno 7 dni, LIMIT 10).

**0.17:** kronika (`chronicle`) jest additive i tylko-do-czytania; wpis powstaje w transakcji faktującej, limit 300 wpisów na świat; brak nowych endpointów — feed jedzie w stanie świata.

**0.16:** eventy miejskie rozliczają się leniwie przy odczycie stanu (zaliczenie/wygaśnięcie); tabela `city_events` jest additive. Tworzy je wyłącznie administrator.

**0.15:** kontrakty organizacyjne to jedna nowa tabela (`org_contracts` z częściowym indeksem jedno-aktywnego) — additive; wygasanie liczy się leniwie przy odczycie społeczności.

**0.14:** sklep jest dev-only — `paid_dev` i pozorowana kasa; przed jakimkolwiek uruchomieniem prawdziwych płatności: integracja Play Billing/Apple IAP, ścieżka zgody opiekuna (RODO art. 8), kwestionariusze sklepów. Tabele sklepu są additive.

**0.13:** tytuły sezonowe nadają się wyłącznie podczas leniwej finalizacji (raz na sezon, UNIQUE w bazie); tabela `character_titles` jest additive.

**0.12:** sezony archiwizują się leniwie — finalizacja liczb następuje przy pierwszym udanym odczycie rankingu po zakończeniu sezonu; przy zatrzymanej usłudze terminy i tak doliczą się przy następnym starcie. Tabele `game_events` (retencja: 100 zdarzeń na postać) i `season_archive` są additive.

**0.11:** wpływy terytorialne to dwie nowe tabele (`territory_state`, `territory_log`) — start na istniejącej bazie nie wymaga kroków; kronika rośnie tylko przy zmianie posiadacza dzielnicy.

**0.10:** migracje organizacji 2.0 (kolumny `org_members.role`, `organizations.fund/announcement`, tabele `org_applications`/`org_investments`) są w pełni additive — start na istniejącej bazie nie wymaga żadnych kroków, liderzy dostają rolę `leader` automatycznie.

**0.9:** karencja usuwania kont wymaga uruchomionego procesu (sweep przy starcie i co 15 min) — przy zatrzymanej usłudze terminy się nie liczą, dane czekają; zewnętrzne powiadomienia o karach/odwołaniach nadal nie istnieją. Rola moderatora i limit kont na adres są opisane w README 0.9.

**Dodane w 0.8: pakiet `deploy/`** — Dockerfile (stałe zależności, nie-root, healthcheck), docker-compose (wolumeny data/backups), `city-empire.service` (systemd, `Restart=always`, `ProtectSystem=strict`), `backup-offsite.sh` (eksport kopii poza maszynę + weryfikacja `quick_check`) i `deploy/README.txt` z kolejnością wdrożenia oraz jawną listą, czego pakiet nie robi (domena/HTTPS, alarmy zewnętrzne, certyfikacja sklepów). Szczegóły monetyzacji: `MONETYZACJA.md` (tylko projekt, bez kodu sklepu).

## 1. Decyzje przed przeniesieniem

- Wybrać hosting, lokalizację danych, budżet, domenę, operatora i zakres pilotażu. Dla danych osobowych zweryfikować umowę powierzenia, podwykonawców, transfery i obowiązki administratora danych.
- Ustalić wymagany maksymalny ubytek danych (RPO), czas odtworzenia (RTO), retencję kopii, monitoring i dyżury. Obecna częstotliwość 10 minut nie jest gwarancją żadnego SLA.
- Ustalić procedurę kont testowych i haseł. Zmiana `CITY_MODE` na production wymusza 12 znaków tylko dla nowych haseł, **nie zmienia ani nie blokuje automatycznie istniejących krótkich haseł**. Przed publicznym startem potrzebne są kontrolowane przejście i silne hasła, bez samowolnego kasowania kont użytkowników.
- Nadal brakuje MFA, odzyskiwania kont, rozdzielonych ról moderator/operator, zewnętrznego audytu i testów obciążenia. Dostęp do szerokiej publiczności, zwłaszcza niepełnoletnich, wymaga dodatkowej oceny i zabezpieczeń.

## 2. Minimalna architektura małego, kontrolowanego pilotażu

```text
Przeglądarka → HTTPS / reverse proxy → jeden proces aplikacji → lokalny trwały dysk SQLite
                                                        ↘ lokalne kopie 0600
                                                           ↘ szyfrowany magazyn poza serwerem (do wdrożenia)
```

- Jeden proces/worker aplikacji. Harmonogram kopii działa w tym procesie, nie w niezależnym schedulerze. Nie uruchamiać wielu workerów z tym harmonogramem bez dalszej przebudowy.
- Dedykowany nieuprzywilejowany użytkownik systemowy; oddzielnie katalog kodu, danych i kopii. Dysk trwały, nie efemeryczny katalog kontenera. Nie wystawiać bazy na sieciowym systemie plików bez sprawdzenia zgodności blokad SQLite.
- W produkcji reverse proxy i aplikacja pod **tym samym originem**. Klient używa względnych `/api`. Bez wildcard CORS i bez zewnętrznego localhost w JavaScript.
- HTTPS, automatyczne odnowienie certyfikatu, firewall. Backend niedostępny bezpośrednio z Internetu; proxy nadpisuje Host/X-Forwarded-Proto, nie przepuszcza dowolnych wartości klienta. Uvicorn ufa wyłącznie ustalonemu adresowi proxy.
- Reverse proxy nie serwuje katalogu projektu. Nie konfigurować aliasów do `data/`, `backups/`, źródeł, plików środowiska i kodu instalacyjnego.
- Wybrać i przetestować własną politykę osadzania (`frame-ancestors`), ograniczenia hostów i CSP; prototyp celowo pozwala na ramkę podglądu oraz inline JS/CSS. Przed publikacją potrzebne utwardzenie i niezależny przegląd.

Przykładowe zmienne na docelowej maszynie (ścieżki tworzy i chroni operator):

```ini
CITY_MODE=production
CITY_DB=/var/lib/city-empire/city_empire.sqlite3
CITY_SETUP_FILE=/var/lib/city-empire/administrator-setup.txt
CITY_BACKUP_DIR=/var/backups/city-empire
```

Przykładowa komenda **na osobnym serwerze za lokalnym reverse proxy**, po instalacji zależności i `python build.py`:

```bash
python -m uvicorn server.app:app --host 127.0.0.1 --port 3000 \
  --workers 1 --proxy-headers --forwarded-allow-ips=127.0.0.1
```

Nie jest to komenda dla podglądu Arena: tutaj `bash start.sh` poprawnie nasłuchuje na `0.0.0.0`. Na stałym serwerze potrzebny jest dodatkowo nadzorca procesu (np. systemd), restart po awarii, kontrola uprawnień i trwały katalog roboczy. Nie instalować zależności dynamicznie przy każdym restarcie produkcji; budować i testować konkretne wydanie.

## 3. Kopie: co jest zaimplementowane

- `server/backups.py`: kopia przy starcie i co 10 min, dopóki działa proces; ręczna z panelu admina, do 3/h na konto/adres zgodnie z limitem prototypu.
- `sqlite3.Connection.backup` zamiast kopiowania aktywnego pliku z pominięciem WAL.
- Kontrola `quick_check` i `foreign_key_check`, manifest z czasem UTC, rozmiarem, SHA-256. Pliki 0600, kopia powstaje jako plik częściowy i zostaje przemianowana po sprawdzeniu.
- Po 6 ostatnich kopii `auto-*` i `manual-*` tworzonych przez usługę. Własne `city-empire-*` operatora są poza rotacją.
- Domyślnie `data/backups/`; CLI `python manage.py backup` domyślnie zapisuje w `online/backups/`. Te dwa katalogi są celowo rozróżnione.
- Stan panelu jest lokalny, bez pobierania plików przez API. Błąd kopii widać w panelu i logu procesu, lecz **nie wysyła on zewnętrznego alarmu**.
- Nie są wdrożone: szyfrowanie kopii aplikacyjne, wysyłka poza hosta, automatyczne testy odtworzenia na niezależnej maszynie, monitorowanie ciągłości i formalna retencja czasowa. To osobny etap.

Kopie zawierają hasze haseł, sesje i treści użytkowników. Chronić jak bazę; nie publikować w repozytorium. Backup nie zastępuje obsługi usuwania danych. Należy ustalić okres retencji i rejestr usunięć pozwalający nie przywrócić kont/danych usuniętych po dacie odzyskiwanej kopii. Sama rotacja liczby plików nie spełnia tej procedury.

## 4. Bezpieczna próba odtworzenia — bez ruszania gry

```bash
# Wybierz istniejącą kopię, nie aktywną bazę:
python manage.py --db backups/KOPIA.sqlite3 verify-backup
python manage.py --db backups/KOPIA.sqlite3 rehearse-restore \
  --output rehearsal/restore-2026-09-28.sqlite3
python manage.py --db rehearsal/restore-2026-09-28.sqlite3 verify-backup
```

`rehearse-restore` odrzuca istniejący plik docelowy. Weryfikuje kopię, wykonuje backup API do nowej bazy i pokazuje liczby kont/postaci/światów. Próba nie loguje tokenów, haseł ani treści graczy.

Jeśli potrzebny jest test odtworzonej aplikacji: uruchomić ją na odizolowanym porcie/maszynie, z osobnymi CITY_DB/CITY_SETUP_FILE/CITY_BACKUP_DIR. Wyłączyć dostęp graczy i unieważnić odzyskane sesje w tej kopii. Używać źródeł kompatybilnych ze schematem; migracje uruchamiają się przy imporcie aplikacji. **Nie uruchamiać dawnych źródeł 0.6.2 bezpośrednio na schemacie 0.7.**

Próba wykonana podczas etapu 0.7: przedetapową kopię sprawdzono i odtworzono do osobnego pliku QA, nie do aktywnej bazy. Dodatkowe testy automatyczne obejmują kopię schematu 0.7 z danymi i sprawdzają brak naruszeń FK.

## 5. Rzeczywiste przełączenie po awarii lub migracji — procedura operatora

1. Zaplanować przerwę, powiadomić graczy i zablokować ruch. Zatrzymać wszystkie procesy korzystające z bazy, nie tylko widoczny frontend.
2. Zachować komplet dotychczasowych plików bazy/WAL/SHM do diagnostyki, w prywatnym katalogu. Nie kasować w ciemno plików WAL.
3. Zweryfikować wybraną kopię i odtworzyć ją do **nowej ścieżki**. Nie nadpisywać działającego pliku. Zastosować zgodne źródła i migracje. Przy rollbacku kodu dobrać zgodną kopię bazy — może to oznaczać utratę postępu od daty kopii, wymagającą jawnej decyzji i komunikatu.
4. W odtworzonej bazie unieważnić odzyskane sesje: `python manage.py --db NOWA_BAZA expire-sessions`. Uwzględnić blokady/usunięcia/zmiany haseł od daty kopii zgodnie z wcześniej ustaloną procedurą; nie pomijać tego kroku.
5. Zmienić CITY_DB na nową, zweryfikowaną ścieżkę, ustawić uprawnienia i właściwego właściciela. Przeprowadzić zamknięty test logowania, postaci, ekonomii, PvP, społeczności i administratora. Sprawdzić utworzenie nowej kopii.
6. Dopiero po odbiorze dopuścić ruch, monitorować błędy i ogłosić stan. Zachować prywatnie poprzedni zestaw przez zatwierdzony czas retencji.

Żadne z tych przełączeń nie zostało wykonane na danych użytkownika podczas obecnej rozbudowy.

## 6. Lista odbioru przed publikacją

- [ ] Rzeczywiście trwały dysk, ograniczone uprawnienia, monitoring procesu/miejsca/opóźnień/błędów/kopii.
- [ ] HTTPS, dozwolone hosty, poprawne proxy i cookies; produkcyjny adapter podglądu zwraca 404; brak sekretów w logach.
- [ ] Silne hasła istniejących kont, procedura odzyskiwania, MFA i rozdzielenie ról.
- [ ] Szyfrowane kopie poza hostem, uzgodniona retencja i regularne niezależne odtworzenie.
- [ ] Testy obciążenia i konkurencji; plan rozwoju bazy/kolejek zamiast deklaracji niezmierzonej skali.
- [ ] Obsługa zgłoszeń, kontakt do operatora, moderacja publicznych nazw i opisów, odwołania, ochrona niepełnoletnich.
- [ ] Dokumenty, podstawy przetwarzania, retencja i procedury praw osób; ocena wymogów sklepów/odbiorców.
- [ ] Oddzielny przegląd płatności, przejrzystości cen i ochrony konsumenta, jeśli zostaną dodane. Obecnie brak płatności.

Instrukcja jest technicznym przygotowaniem, nie opinią prawną, gwarancją zgodności ani zastępstwem audytu.

- 0.56.0 Trasy NPC: nowe pole stanu `npcRoutes` (migracja automatyczna w sync), brak zmian schematu SQL. Test: tests/test_routes.py, tests/test-routes.cjs.
- 0.57.0 Sojusze: kolumna `organizations.buildings` TEXT (migracja addytywna przy starcie). Test: tests/test_alliance.py, tests/test-alliance.cjs.
- 0.58.0 Eventy czasowe: bez zmian schematu. Testy CJS z twardymi kwotami EXP/kasy są event-aware (test-online, test-routes). Nowe: tests/test_timed_events.py, tests/test-timedevent.cjs.
- 0.59.0 Chmurka powiadomień: bez zmian schematu. Testy: tests/test_notif.py, tests/test-notif.cjs; test-timedevent niezależny od pory dnia.
