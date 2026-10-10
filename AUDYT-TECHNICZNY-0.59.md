# 🎮 AUDYT TECHNICZNY — CITY EMPIRE (LIFE CITY)

**Wersja audytowana:** 0.59.0 (brief podaje 0.58 — kod w repo jest o jedno wydanie nowszy)
**Zakres:** cały backend Python (`server/*.py`, `manage.py`, `build.py`, `tools/`) — 3 785 linii
**Metoda:** przegląd kodu z workspace + grep wzorców ryzyka + wiedza z 47 testów pytest i 41 testów E2E (wszystkie zielone w 0.59.0)

> ⚠️ **Uwaga wstępna:** w wiadomości nie było wklejonego kodu, a treść urwała się po Sekcji 2. Audyt opiera się na **rzeczywistym kodzie z repozytorium** i obejmuje Sekcje 1–2 w zadanym formacie. Pozostałe sekcje mogę dopisać, gdy prześlesz ich specyfikację.

---

## ⚠️ ROZBIEŻNOŚCI: BRIEF vs. KOD (przeczytaj najpierw)

Kontekst w briefie w kilku miejscach opisuje inną grę niż ta, która jest w repozytorium. Audyt ocenia **kod**, nie brief:

| Brief mówi | Kod faktycznie robi |
|---|---|
| Gra mobilna | Webowa (responsywny HTML/JS); brak aplikacji natywnej |
| 5 miast do wyboru | 1 mapa świata: 5 dzielnic miejskich + 3 lokacje surowcowe (d2/d7/d8) |
| Kawiarnia 4h + **Klub Nocny 12h** | Kawiarnia (skarbiec idle, cap 24h). **Brak klubu nocnego** — „Sala Klubowa” to sporty (decyzja: gra dla nastolatków, bez treści 18+) |
| NPC transportują surowce w kontraktach | Trasy NPC (0.56) to osobny system; kontrakty to zlecenia gracza |
| Klasy Obrońca/Atakujący/Szybki | Klasy w kodzie: **Bokser, Obrońca, Szybki** (`combat.py:37`) — „Atakujący” = Bokser |
| Gildie max 100 graczy | Organizacje/Sojusze: **limit 20 członków** (`features.py:341,361,376`) |
| Łucznictwo, pływanie, wystawa psów | ✅ Są w `sports2.py`: łucznictwo, pływanie, Agility psów (= „wystawa”), turniej bokserski; do tego ring, hipodrom i Loch (poprawka) |
| **Diamenty (waluta premium)** | **Brak drugiej waluty.** Sklep dev bez prawdziwych płatności, zakupy domyślnie OFF |
| VIP + Veteran do −75% kosztów | VIP = **+25% gotówki z kontraktów** + złota rama + auto VIP; Veteran = bramka 7 dni. **Brak zniżek −75%** |
| Normal 7 dni = 3 ery | **4 ery** (Pionierów → Przemysł → Wielki Biznes → Metropolia), dzień 1/3/5/7+ |
| Sety Basic/Medium/Super/Ultra | Pojedyncze przedmioty + unikaty z lochów; brak systemu setów |
| PEGI 12+ | Projekt zakłada nastolatków + RODO <16 (zgoda opiekuna w `shop.py`) |

**Wniosek:** albo brief opisuje *docelową* wizję (wtedy to backlog ~6 dużych systemów), albo pochodzi z innego dokumentu. Przed migracją trzeba to rozstrzygnąć — od tego zależy model danych w PostgreSQL.

---

═══════════════════════════════════════════════════════════
## 📊 SEKCJA 1: EXECUTIVE SUMMARY
═══════════════════════════════════════════════════════════

- **Jakość kodu: 5/10** — logika poprawna i gęsto przetestowana, ale styl „jedna linia = pięć instrukcji” (średnio ~140 znaków/linię, `;`-łańcuchy) utrudnia czytanie i review.
- **Architektura: 6/10** — sensowny podział domenowy i autorytatywny serwer, ale stan gracza to jeden blob JSON (`characters.state_json`) i dwa pliki-giganty (`app.py`, `features.py`).
- **Bezpieczeństwo: 7/10** — Argon2, CSRF z `hmac.compare_digest`, `BEGIN IMMEDIATE`, idempotencja, parametryzowany SQL, rate limiting; minusy: deklaratywna weryfikacja wieku, rosnąca bez końca tabela limitów.
- **Skalowalność: 3/10** — SQLite + jeden proces + polling co 5 s + zapis całego stanu przy każdej akcji: sufit to setki, nie tysiące graczy jednocześnie.
- **Gotowość do produkcji: 4/10** — gotowe na zamkniętą betę (Docker, systemd, kopie co 10 min); niegotowe na sklepy mobilne i publiczny start.
- **Największa mocna strona:** reguły gry są w 100% po stronie serwera, transakcyjne i idempotentne — klient nie może oszukać ekonomii.
- **Największa słabość:** stan gracza jako jeden nietypowany słownik JSON — bez schematu, bez indeksów, bez możliwości zapytań i z migracjami w `sync()`.
- **Migrować czy przepisać?** **Przepisać warstwę techniczną, przenieść reguły:** reguły z `economy.py`/`combat.py` i 88 testów to najcenniejszy kapitał — trzeba je przenieść 1:1 jako specyfikację, a infrastrukturę (DB, sesje, API) zbudować od nowa w NestJS.

---

═══════════════════════════════════════════════════════════
## 🔍 SEKCJA 2: ANALIZA PLIK PO PLIKU
═══════════════════════════════════════════════════════════

### 📄 app.py
**Rola:** Rdzeń aplikacji FastAPI: schemat bazy i migracje addytywne, konta/sesje/CSRF, rate limiting, światy, postacie, główny endpoint akcji i pakiet stanu. Skleja wszystkie pozostałe moduły (`features`, `travel`, `shop`, `pvp`…).
**Linie kodu:** 758 (107 funkcji/endpointów)
**Ocena:** 6/10

✅ **Mocne strony:**
- Hasła Argon2 (`argon2.PasswordHasher`), tokeny `secrets.token_urlsafe(32)`, w bazie tylko hash SHA-256 tokenu sesji (l. 31, 230).
- CSRF przez nagłówek `x-csrf-token` porównywany `hmac.compare_digest` (l. 209); cookie `httponly` + `secure` (l. 240).
- Idempotencja akcji: tabela `operations` + odcisk żądania — powtórzony klucz zwraca zapisaną odpowiedź, inny payload → 409 (l. 425–430).

❌ **Słabe strony:**
- Plik-gigant: schemat SQL, auth, admin, akcje i pakiet stanu w jednym miejscu; funkcje zagnieżdżone w `create_app` (nie da się ich testować osobno).
- Pakiet stanu (`/state`) wykonuje kilkanaście zapytań i jest odpytywany co 5 s przez każdego klienta.
- Migracje schematu ręcznie przez `PRAGMA table_info` + `ALTER TABLE` przy starcie — brak wersjonowania migracji.

🐛 **Wykryte bugi/luki:**
1. [Linia 122, 219–227] — tabela `rate_limits` nigdy nie jest czyszczona (`INSERT OR REPLACE`, brak `DELETE`); klucz zawiera username, więc próby z losowymi nazwami powiększają ją bez końca — **NISKI**.
2. [Linia ~436] — `s['ally']` jest wstrzykiwane do stanu przed akcją i **zapisywane do `state_json`**; po wyjściu z sojuszu zostaje stara wartość do następnej akcji (premia „wisi” w stanie) — **NISKI**.
3. [Linia 240] — `samesite='none'` przy `secure` (potrzebne dla podglądu w iframe) zwiększa powierzchnię CSRF; chroni tylko nagłówek CSRF — **NISKI** (ochrona działa, ale warto mieć tryb produkcyjny `lax`).

🔒 **Problemy bezpieczeństwa:**
- Brak nagłówków bezpieczeństwa (CSP, `X-Frame-Options`, HSTS) po stronie aplikacji — zależne od reverse proxy.
- Rate limit trzymany w SQLite — przy wielu instancjach przestanie działać (wymaga Redis).
- `UPDATE worlds SET '+key+'` (l. 588) — **bezpieczne** (klucze ze schematu Pydantic `WorldUpdate`), ale wzorzec łatwo skopiować w niebezpieczne miejsce.

💡 **Rekomendacje:**
- Rozbić na `auth.py`, `worlds.py`, `actions.py`, `state.py`, `schema.py`; `create_app` tylko składa routery.
- Dodać okresowe `DELETE FROM rate_limits WHERE until_at < ?` (np. w pętli kopii zapasowych).
- Nie zapisywać pól wyliczanych (`ally`) do stanu — przekazywać je argumentem do `E.action`.

🔄 **Jak przepisać na NestJS:**
```typescript
src/modules/auth/            // rejestracja, logowanie, sesje, CSRF guard
├── auth.controller.ts
├── auth.service.ts          // argon2 (pakiet "argon2"), tokeny
├── auth.module.ts
├── guards/csrf.guard.ts
├── guards/session.guard.ts
└── dto/ (register.dto.ts, login.dto.ts)
src/modules/worlds/          // światy, admin
src/modules/actions/         // POST /actions + IdempotencyInterceptor
src/modules/state/           // pakiet stanu -> docelowo push przez Socket.io
src/common/interceptors/idempotency.interceptor.ts
src/common/guards/throttler (@nestjs/throttler + Redis storage)
```

---

### 📄 economy.py
**Rola:** Autorytatywny silnik ekonomii: kontrakty, trening, firmy, garaż, rezydencje, surowce, budynki dzielnicy, Trasy NPC, budynki sojuszu i eventy czasowe. Wywoływany wyłącznie wewnątrz transakcji zapisu.
**Linie kodu:** 523
**Ocena:** 7/10

✅ **Mocne strony:**
- Czyste funkcje na słowniku stanu, czas wstrzykiwany (`now`, `speed`) — deterministyczne i świetnie testowalne (fałszywy zegar w testach).
- Spójny mechanizm błędów `RuleError` → 409 z czytelnym komunikatem dla gracza.
- Dane gry jako stałe (`GARAGE`, `NPC_ROUTES`, `ALLY_BUILDINGS`, `TIMED_EVENTS`) — łatwe do przeniesienia do konfiguracji/bazy.

❌ **Słabe strony:**
- Jedna funkcja `action()` z długim łańcuchem `elif kind==…` (~30 gałęzi) — każdy nowy system ją wydłuża.
- `sync()` pełni rolę migratora stanu (dodaje brakujące klucze, naprawia typy) — dowód na brak schematu.
- Liczby balansu rozsiane po kodzie (np. `10*MINUTE`, `240` energii, `0.02` za poziom garażu).

🐛 **Wykryte bugi/luki:**
1. [Linia 486] — `route_claim`: `next(y for y in NPC_ROUTES if …)` bez wartości domyślnej; jeśli trasa zniknie z katalogu w nowej wersji, każde odebranie rzuci `StopIteration` → **500 i trwale zablokowany odbiór** — **WYSOKI**.
2. [Linia 436] — `service_vehicle`: `next(g for g in GARAGE …)` bez default — auto usunięte z katalogu → 500 — **ŚREDNI**.
3. [Eventy czasowe] — premia liczy się w chwili **odbioru**, nie ukończenia: gracz może przetrzymać gotowe kontrakty/trasy do okna „Gorączki”/„Szczytu” i zgarnąć +25–50% — **ŚREDNI** (exploit ekonomii).
4. [Trasy NPC] — auto wysłane w trasę może jednocześnie służyć do podróży gracza (`travel.py` sprawdza tylko stan techniczny) — **ŚREDNI** (niespójność zasad).
5. [Linia 118] — `ally_mult` z nieznanym kluczem → `StopIteration` (dziś tylko wywołania wewnętrzne) — **NISKI**.

🔒 **Problemy bezpieczeństwa:**
- Brak (moduł nie dotyka I/O). Walidacja wejścia opiera się na katalogach (`if not r: raise RuleError`) — poprawnie.
- Ryzyko pośrednie: brak górnych limitów na `cash`/`xp` (int bez sufitu) — przy przyszłych bugach łatwo o inflację bez alarmu.

💡 **Rekomendacje:**
- `next(..., None)` + łagodna obsługa „nieznanej trasy” (zwrot pojazdu bez nagrody).
- Zapisywać przy biegu/kontrakcie `bonus_at_finish` (mnożnik w chwili `end`), a nie w chwili odbioru.
- Zamienić łańcuch `elif` na rejestr handlerów `ACTIONS = {'route_dispatch': route_dispatch, …}`.

🔄 **Jak przepisać na NestJS:**
```typescript
src/modules/economy/
├── economy.module.ts
├── actions/                       // jeden handler = jedna akcja
│   ├── action-handler.interface.ts
│   ├── contract.handler.ts
│   ├── route-dispatch.handler.ts
│   └── upgrade-building.handler.ts
├── catalog/                       // GARAGE, NPC_ROUTES, TIMED_EVENTS jako JSON/DB
│   └── catalog.service.ts
├── rules/timed-events.service.ts
├── errors/rule.error.ts           // -> HttpException 409
└── dto/action.dto.ts              // class-validator, discriminated union
```

---

### 📄 features.py
**Rola:** Warstwa społeczna: organizacje/sojusze (role, fundusz, budynki, kontrakty organizacji), czat i DM, zdarzenia (`game_events`), terytoria i wpływy, ranking, profile, dystynkcje dnia. Drugi co do wielkości moduł.
**Linie kodu:** 756 (99 funkcji/endpointów)
**Ocena:** 5/10

✅ **Mocne strony:**
- Spójne uprawnienia: `officer(c, ch)` jako jedna bramka dla akcji lidera/oficera; limity członków egzekwowane w 3 ścieżkach (zaproszenie/podanie/akceptacja).
- Filtr treści czatu: usuwa znaki sterujące i blokuje linki/e-maile (ochrona małoletnich).
- `emit()` przycina zdarzenia do 100 na postać — tabela nie puchnie.

❌ **Słabe strony:**
- Zbyt wiele domen w jednym pliku (organizacje, czat, DM, terytoria, ranking, sezony).
- Ciężkie zapytanie `community` (podzapytania `count`/`sum` per organizacja) wykonywane przy każdym otwarciu panelu.
- Migracje schematu wymieszane z logiką endpointów.

🐛 **Wykryte bugi/luki:**
1. [Linia 341/361/376] — limit 20 członków sprawdzany `count(*)` przed insertem; w SQLite z `BEGIN IMMEDIATE` jest bezpieczny, ale po migracji na PostgreSQL (READ COMMITTED) **powstanie race condition** — **ŚREDNI** (przy migracji).
2. [Funkcja `text()`] — regex domen `\b(?:[\w-]+\.)+[a-zA-Z]{2,}\b` blokuje niewinne teksty typu „np.ok”, „gg.wp” — **NISKI** (fałszywe alarmy moderacji).
3. [`emit`] — dwa zapytania (`INSERT` + `DELETE … NOT IN (SELECT … LIMIT 100)`) na **każdego** odbiorcę; zdarzenie dla 20 członków = 40 zapytań — **NISKI** (wydajność).

🔒 **Problemy bezpieczeństwa:**
- Czat bez limitu częstotliwości per użytkownik w tym module (rate limit globalny) — ryzyko spamu.
- Brak automatycznej moderacji wulgaryzmów (wymóg sklepów dla gier z czatem i małoletnimi) — jest tylko zgłaszanie i blokowanie.

💡 **Rekomendacje:**
- Podzielić na `orgs.py`, `chat.py`, `territory.py`, `events.py`.
- Przy migracji: limit członków jako ograniczenie w bazie (licznik + `CHECK`) albo `SELECT … FOR UPDATE` na organizacji.
- Dodać filtr słów (lista PL) + limit np. 1 wiadomość/2 s.

🔄 **Jak przepisać na NestJS:**
```typescript
src/modules/alliances/        // organizacje, role, fundusz, budynki sojuszu
├── alliances.controller.ts
├── alliances.service.ts
├── alliances.module.ts
└── dto/ (create-alliance.dto.ts, ally-build.dto.ts, fund.dto.ts)
src/modules/chat/             // gateway Socket.io + moderacja
├── chat.gateway.ts
├── moderation.service.ts
src/modules/notifications/    // game_events -> push Socket.io + FCM
src/modules/territory/
```

---

### 📄 travel.py
**Rola:** Mapa 8 lokacji i podróże (bus z opłatą, auto, autostop z losowym czasem). Leniwe rozliczanie przyjazdu (`lazy`/`settle`) przy dowolnym odczycie stanu.
**Linie kodu:** 149
**Ocena:** 7/10

✅ **Mocne strony:**
- Leniwe rozliczanie (`lazy`) — brak cronów, przyjazd liczy się przy następnym żądaniu.
- Przejrzysty wzór czasu (`base*CAR_SHARE`, minimum 60 s dla busa) z jedną funkcją `travel_ms`.
- Wpływ statystyk (Refleks) ograniczony limitem (cap 25%) — brak przegięć balansu.

❌ **Słabe strony:**
- Mieszane style kodu (4 spacje tutaj, 1 spacja w reszcie projektu).
- Dzielnice zakodowane na sztywno jako lista krotek (`DISTRICTS`) — zduplikowane z klientem.
- Losowość autostopu przez moduł `random` (wystarczające dla gry, ale nieaudytowalne).

🐛 **Wykryte bugi/luki:**
1. [Linia ~116] — auto w Trasie NPC może być użyte do podróży (sprawdzany tylko `condition>0`) — **ŚREDNI** (patrz economy.py).
2. [Linia 112–115] — nieudany autostop zabiera 10 energii, nawet gdy podróż nie zostanie rozpoczęta z innego powodu później w tej samej funkcji (kolejność walidacji) — **NISKI** (do weryfikacji testem).

🔒 **Problemy bezpieczeństwa:**
- Brak istotnych: walidacja `target_district` przez Pydantic, czas liczony po stronie serwera.

💡 **Rekomendacje:**
- Blokada pojazdu w trasie: `if veh in [r['vehicle'] for r in s['npcRoutes']['runs']]: fail(...)`.
- Przenieść `DISTRICTS` do wspólnego katalogu serwowanego klientowi.

🔄 **Jak przepisać na NestJS:**
```typescript
src/modules/travel/
├── travel.controller.ts
├── travel.service.ts        // travelMs(), settle()
├── travel.module.ts
├── map.catalog.ts
└── dto/start-travel.dto.ts
// settle -> BullMQ delayed job ("arrive") zamiast leniwego odczytu
```

---

### 📄 shop.py
**Rola:** Sklep deweloperski (bez realnych płatności): 6 produktów, Energiapak 2/dzień, VIP, zgody opiekuna z tygodniowym limitem dla małoletnich. Zakupy domyślnie wyłączone.
**Linie kodu:** 230
**Ocena:** 7/10

✅ **Mocne strony:**
- Zgodność z kierunkiem prawnym: brak lootboxów, brak losowych nagród za pieniądze, zakupy OFF domyślnie.
- Zgoda opiekuna jako osobna encja z unikalnym indeksem aktywnej zgody (`guardian_active`).
- Tygodniowy limit wydatków (`weekly_limit` 500–20 000) egzekwowany po stronie serwera.

❌ **Słabe strony:**
- Brak integracji z prawdziwymi płatnościami (Apple IAP / Google Play Billing) — świadomie, ale to największy brak przed sklepami.
- Waluta limitu i ceny w jednym miejscu z logiką — trudne do lokalizacji.
- Brak historii zwrotów/reklamacji.

🐛 **Wykryte bugi/luki:**
1. [Linia 44] — `minor: bool = False` — **wiek deklaruje sam użytkownik**; dziecko może zaznaczyć „dorosły” i ominąć zgodę opiekuna — **WYSOKI** (prawny, nie techniczny).
2. [Dostęp do limitu] — `week_spent` liczone zapytaniem przy każdym zakupie bez blokady wiersza; po migracji na Postgres dwa równoległe zakupy mogą przekroczyć limit — **ŚREDNI** (przy migracji).

🔒 **Problemy bezpieczeństwa:**
- Przy realnych płatnościach konieczna weryfikacja paragonów po stronie serwera (App Store Server API / Play Developer API) — dziś brak.

💡 **Rekomendacje:**
- Age gate przy rejestracji (data urodzenia) + zgoda rodzica przez e-mail dla <16 (RODO art. 8, w PL próg 16).
- Przy migracji: limity wydatków w transakcji z `SELECT … FOR UPDATE`.
- Utrzymać zasadę „brak losowych nagród za walutę” także dla przyszłych Diamentów.

🔄 **Jak przepisać na NestJS:**
```typescript
src/modules/shop/
├── shop.controller.ts
├── shop.service.ts
├── shop.module.ts
├── iap/apple-receipt.service.ts
├── iap/google-billing.service.ts
├── guardian/guardian.service.ts
└── dto/ (purchase.dto.ts, guardian-consent.dto.ts)
```

---

### 📄 sports.py
**Rola:** Sala Klubowa: hipodrom (konie mustang/thoroughbred/champion, wpisowe bez obstawiania) i Ring/boks. Logika wyników sportowych i nagród.
**Linie kodu:** 280
**Ocena:** 6/10

✅ **Mocne strony:**
- Wpisowe stałe w $, **bez zakładów i bez losowej nagrody za pieniądze** — bezpieczne wobec ustawy hazardowej.
- Konie jako katalog z parametrami — łatwo dodać kolejne.
- Wynik liczony na serwerze.

❌ **Słabe strony:**
- Mieszanie danych, logiki i endpointów w jednym pliku.
- Duplikacja wzorców z `sports2.py` (dwa pliki o tej samej odpowiedzialności).
- 1 połykany wyjątek (`except Exception`) — błędy mogą znikać bez logu.

🐛 **Wykryte bugi/luki:**
1. [`except Exception`] — połknięty błąd bez logowania utrudni diagnostykę na produkcji — **NISKI**.
2. [Wyścigi] — losowy wynik wyścigu z płatnym wpisowym: prawnie OK (nagroda za udział, nie zakład), ale **wymaga opisu w regulaminie**, żeby nie zostało uznane za grę losową — **ŚREDNI** (prawny).

🔒 **Problemy bezpieczeństwa:**
- Brak dziennych limitów udziału w wyścigach w tym module (do weryfikacji) — ryzyko farmienia.

💡 **Rekomendacje:**
- Połączyć `sports.py` + `sports2.py` w moduł `club` z podmodułami dyscyplin.
- Logować każdy wyjątek (`logger.exception`).

🔄 **Jak przepisać na NestJS:**
```typescript
src/modules/club/
├── club.module.ts
├── racing/ (racing.controller.ts, racing.service.ts, horses.catalog.ts)
├── boxing/ (boxing.controller.ts, boxing.service.ts)
└── dto/enter-race.dto.ts
```

---

### 📄 sports2.py
**Rola:** Kolejne dyscypliny Sali Klubowej (rozszerzenie z późniejszej wersji). Wspólny hub 8 kart dyscyplin.
**Linie kodu:** 151
**Ocena:** 5/10

✅ **Mocne strony:**
- Mały, skupiony plik.
- Korzysta z tych samych wzorców nagród co `sports.py`.
- Testowany E2E (karty klubu, powrót do hubu).

❌ **Słabe strony:**
- Nazwa `sports2` nic nie mówi — dług techniczny „dopisz obok”.
- Duplikacja z `sports.py`.
- Brak wspólnego interfejsu dyscypliny.

🐛 **Wykryte bugi/luki:**
1. [Cały plik] — brak wspólnej abstrakcji: nowa dyscyplina wymaga zmian w 2 plikach serwera i w kliencie — **NISKI** (utrzymanie).

🔒 **Problemy bezpieczeństwa:**
- Brak specyficznych.

💡 **Rekomendacje:**
- Interfejs `Discipline { id, enter(), resolve(), rewards }` i rejestr dyscyplin.

🔄 **Jak przepisać na NestJS:**
```typescript
src/modules/club/disciplines/
├── discipline.interface.ts
├── discipline.registry.ts
└── <nazwa>.discipline.ts   // jedna klasa na dyscyplinę
```

---

### 📄 pvp.py
**Rola:** Asynchroniczne PvP: wyzwania, mecze, limit dzienny i limit par (`daily_limit`, `pair_limit`), taktyka raz na walkę, od 2. poziomu. Używa silnika `combat.py`.
**Linie kodu:** 122
**Ocena:** 7/10

✅ **Mocne strony:**
- Limity dzienne i per para graczy — ochrona przed farmieniem jednego przeciwnika.
- Asynchroniczność: obrona gracza offline według zapisanej taktyki.
- Bramki poziomowe (PvP od 2 lvl).

❌ **Słabe strony:**
- Ranking (rating) aktualizowany prostą formułą w tej samej transakcji — brak historii zmian ELO.
- Brak systemu matchmakingu (wybór przeciwnika z listy).
- Ściśle sprzężony z tabelą `characters`.

🐛 **Wykryte bugi/luki:**
1. [Limity] — limit liczony `count(*)` po dacie — po migracji na Postgres wymaga blokady albo unikalnego licznika dziennego — **ŚREDNI** (przy migracji).
2. [Rating] — brak dolnego progu ratingu do wyszukiwania przeciwników → silni gracze mogą bić najsłabszych (balans) — **NISKI**.

🔒 **Problemy bezpieczeństwa:**
- Wynik walki serwerowy, seed z `secrets.randbits` — brak możliwości manipulacji przez klienta.

💡 **Rekomendacje:**
- Matchmaking w przedziale ±X ratingu; historia meczów z deltą ratingu.

🔄 **Jak przepisać na NestJS:**
```typescript
src/modules/pvp/
├── pvp.controller.ts
├── pvp.service.ts
├── matchmaking.service.ts   // Redis sorted set po ratingu
├── pvp.module.ts
└── dto/challenge.dto.ts
```

---

### 📄 combat.py
**Rola:** Deterministyczny silnik walki: profile postaci, HP, taktyki, przebieg rund z ziarnem RNG. Ziarno zapisywane, więc walkę można odtworzyć (replay).
**Linie kodu:** 124
**Ocena:** 8/10

✅ **Mocne strony:**
- Ziarno z `secrets.randbits(32)` + `random.Random(seed)` — walka **odtwarzalna** (replay w kliencie) i nieprzewidywalna dla gracza.
- Czysta funkcja bez I/O — idealna do testów i przeniesienia.
- Taktyki jako parametr, nie zakodowane warunki.

❌ **Słabe strony:**
- Formuły obrażeń jako „magiczne liczby” w kodzie.
- Brak wersji silnika w zapisie walki (zmiana balansu = stare replaye odtworzą się inaczej).
- Gęsty zapis utrudnia review balansu.

🐛 **Wykryte bugi/luki:**
1. [Linia 58] — replay używa bieżącej wersji formuł; po zmianie balansu stary zapis pokaże **inny przebieg niż faktyczny wynik** — **ŚREDNI**.

🔒 **Problemy bezpieczeństwa:**
- Brak: RNG po stronie serwera, ziarno nieznane klientowi przed walką.

💡 **Rekomendacje:**
- Zapisywać `engine_version` przy walce; przy migracji przenieść silnik do TS 1:1 i **porównać wyniki dla tych samych ziaren** (test zgodności).

🔄 **Jak przepisać na NestJS:**
```typescript
src/modules/combat/
├── combat.engine.ts        // czysta funkcja simulate(a, b, seed, version)
├── rng.ts                  // seedowany PRNG (np. mulberry32) – identyczny w Flutterze do replay
├── combat.module.ts
└── combat.engine.spec.ts   // golden tests: seed -> oczekiwany przebieg
```

---

### 📄 dungeon.py
**Rola:** Lochy (Ring) od 3. poziomu: przeciwnicy NPC i unikalne przedmioty (`DUNGEON_ITEMS`). Nagrody bez losowania za pieniądze.
**Linie kodu:** 90
**Ocena:** 7/10

✅ **Mocne strony:**
- Mały, czytelny zakres.
- Unikaty zdobywane grą, nie zakupem — zgodne z zakazem lootboxów.
- Korzysta z silnika `combat.py`.

❌ **Słabe strony:**
- Przedmioty lochów zdefiniowane w `economy.py`, logika tutaj — rozproszenie.
- Brak cooldownu/energii jako jawnego parametru w katalogu.
- Mało poziomów trudności.

🐛 **Wykryte bugi/luki:**
1. [Unikaty] — po zdobyciu wszystkich unikatów lochy nie dają nagrody wartej czasu (pętla bez celu) — **NISKI** (design).

🔒 **Problemy bezpieczeństwa:**
- Brak specyficznych.

💡 **Rekomendacje:**
- Katalog lochów (poziomy, przeciwnicy, nagrody) jako dane; przenieść `DUNGEON_ITEMS` do katalogu lochów.

🔄 **Jak przepisać na NestJS:**
```typescript
src/modules/dungeon/
├── dungeon.controller.ts
├── dungeon.service.ts
├── dungeon.catalog.ts
└── dungeon.module.ts
```

---

### 📄 city_events.py
**Rola:** Ery świata (4 ery liczone od dnia utworzenia świata) i wspólne cele miejskie tworzone przez admina z odznaką Pioniera. Decyduje o odblokowaniu dzielnic i firm.
**Linie kodu:** 150
**Ocena:** 7/10

✅ **Mocne strony:**
- Ery jako dane (`ERAS` z `districts`, `business`, `pc`, `premium`) — przejrzyste odblokowania.
- Ery wyliczane z czasu (bez cronów).
- Nagrody wyłącznie kosmetyczne (odznaki) — bezpieczne wobec pay-to-win.

❌ **Słabe strony:**
- Tabela er powiązana z regułami klienta (rozjazd naprawiany po stronie klienta w 0.55 — `lockD`).
- Brak wsparcia dla serwerów Endless/Event z briefu.
- Logika „dnia” oparta o `created_at` świata — brak pauzy/przesunięcia er.

🐛 **Wykryte bugi/luki:**
1. [Linia 21] — era liczona z `created_at` świata; ręczne otwarcie świata później niż utworzenie skraca pierwszą erę — **NISKI**.

🔒 **Problemy bezpieczeństwa:**
- Tworzenie celów tylko dla admina — poprawnie zabezpieczone dependency `admin`.

💡 **Rekomendacje:**
- Liczyć ery od `opens_at`; dodać typ świata (`normal/endless/event`) z własną tabelą er.

🔄 **Jak przepisać na NestJS:**
```typescript
src/modules/eras/
├── eras.service.ts          // currentEra(world, now)
├── eras.catalog.ts
src/modules/city-goals/
├── city-goals.controller.ts // @Roles('admin')
├── city-goals.service.ts
└── dto/create-goal.dto.ts
```

---

### 📄 chronicle.py
**Rola:** Kronika miasta: wpisy o założeniu organizacji, celach, wpływach, tworzone w tej samej transakcji co fakt. Limit 300 wpisów na świat.
**Linie kodu:** 67
**Ocena:** 8/10

✅ **Mocne strony:**
- Zapis w tej samej transakcji co zdarzenie — brak rozjazdu kroniki ze stanem.
- Limit 300/świat — tabela nie rośnie.
- Funkcje-fabryki wpisów (`org_founded`, `org_done`…) — czytelne.

❌ **Słabe strony:**
- Teksty po polsku zakodowane w serwerze — brak i18n.
- Formatowanie liczb (`fmt`) zdublowane z klientem.
- Brak typów wpisów jako enum.

🐛 **Wykryte bugi/luki:**
1. Brak istotnych bugów — **—**.

🔒 **Problemy bezpieczeństwa:**
- Nazwy organizacji trafiają do kroniki — klient musi je escapować (robi to przez `esc()`); po stronie serwera brak sanityzacji HTML — **NISKI** (bezpieczne, dopóki klient escapuje).

💡 **Rekomendacje:**
- Zapisywać `kind` + `payload`, a tekst renderować w kliencie (i18n, Flutter `intl`).

🔄 **Jak przepisać na NestJS:**
```typescript
src/modules/chronicle/
├── chronicle.service.ts     // write(tx, kind, payload)
├── chronicle.controller.ts
└── chronicle.module.ts
```

---

### 📄 avatar.py
**Rola:** Edytor awatara: katalog elementów (włosy, kolczyki, ubrania) z cenami w $ i flagą VIP, zapis wyglądu postaci. Czysta kosmetyka.
**Linie kodu:** 163
**Ocena:** 6/10

✅ **Mocne strony:**
- Kosmetyka bez wpływu na siłę — brak pay-to-win.
- Elementy VIP oznaczone flagą w katalogu.
- Walidacja wyboru względem katalogu po stronie serwera.

❌ **Słabe strony:**
- Katalog jako bardzo długie krotki `('Nazwa',cena,vip,'#kolor','#kolor')` — nieczytelne i podatne na pomyłki pozycji.
- Kolory/grafika awatara definiowane w backendzie.
- Brak wersjonowania katalogu.

🐛 **Wykryte bugi/luki:**
1. [Linia 17] — literówka w danych: „Szafiowe Wiszące” → „Szafirowe” — **NISKI**.

🔒 **Problemy bezpieczeństwa:**
- Brak specyficznych.

💡 **Rekomendacje:**
- Katalog jako JSON z nazwanymi polami (`{name, price, vip, base, highlight}`); w Flutterze renderowanie warstwowe.

🔄 **Jak przepisać na NestJS:**
```typescript
src/modules/avatar/
├── avatar.controller.ts
├── avatar.service.ts
├── avatar.catalog.json
└── dto/update-avatar.dto.ts
```

---

### 📄 backups.py
**Rola:** Automatyczne kopie bazy SQLite co 10 minut (retencja 6 na rodzaj) i kopia przy starcie, plus lista kopii dla admina. Działa jako zadanie asyncio w cyklu życia aplikacji.
**Linie kodu:** 65
**Ocena:** 6/10

✅ **Mocne strony:**
- Zapis do pliku tymczasowego i atomowe podmienienie (brak uszkodzonych kopii).
- Retencja — dysk się nie zapełnia.
- Błędy kopii widoczne dla admina (`self.error`).

❌ **Słabe strony:**
- Kopie lokalne (`local_only=True`) — awaria dysku = utrata danych i kopii (offsite tylko w osobnym skrypcie `deploy/backup-offsite.sh`).
- 3 bloki `except Exception` — błędy logowane ogólnikowo.
- Rozwiązanie specyficzne dla SQLite (nie przeniesie się na Postgres).

🐛 **Wykryte bugi/luki:**
1. [Linia 54/58] — błąd kopii logowany jednym zdaniem bez szczegółów wyjątku — **NISKI**.
2. [Retencja] — brak testu odtwarzania kopii (restore) — **ŚREDNI** (kopia nietestowana = brak kopii).

🔒 **Problemy bezpieczeństwa:**
- Kopie zawierają dane osobowe (RODO) — brak szyfrowania kopii.

💡 **Rekomendacje:**
- Po migracji: `pg_dump` + WAL archiving (np. pgBackRest) do S3-zgodnego magazynu, szyfrowane; comiesięczny test restore.

🔄 **Jak przepisać na NestJS:**
```typescript
// Kopie poza aplikacją: managed PostgreSQL (backup PITR) albo kontener z pgBackRest.
src/modules/admin/backups/
├── backups.controller.ts   // tylko status/lista dla admina
└── backups.service.ts
```

---

### 📄 manage.py
**Rola:** CLI administracyjne: uruchomienie serwera, nadanie gotówki (`grant-cash`), operacje adminowe na bazie. Używane w testach E2E do ustawiania stanu.
**Linie kodu:** 85
**Ocena:** 6/10

✅ **Mocne strony:**
- Przydatne narzędzia dev/QA (`--db X grant-cash`).
- Prosty `argparse`.
- Korzysta z tych samych modułów co serwer.

❌ **Słabe strony:**
- `grant-cash` bez wpisu do audytu (do weryfikacji) — zmiany ekonomii poza śladem.
- Brak potwierdzeń dla operacji destrukcyjnych.
- Brak ochrony przed uruchomieniem na produkcyjnej bazie.

🐛 **Wykryte bugi/luki:**
1. [`grant-cash`] — możliwość modyfikacji stanu produkcji bez audytu — **ŚREDNI** (operacyjny).

🔒 **Problemy bezpieczeństwa:**
- Dostęp = dostęp do serwera; brak osobnych uprawnień.

💡 **Rekomendacje:**
- Każda komenda zapisuje `audit`; flaga `--i-know-this-is-production`.

🔄 **Jak przepisać na NestJS:**
```typescript
// nest-commander
src/cli/
├── grant-cash.command.ts
└── cli.module.ts
```

---

### 📄 build.py
**Rola:** Skleja `template.html` + JS + CSS w jeden plik `web/index.html`. Prosty „bundler” bez zależności.
**Linie kodu:** 9
**Ocena:** 6/10

✅ **Mocne strony:** zero zależności; jeden plik wynikowy (proste wdrożenie); szybki.
❌ **Słabe strony:** brak minifikacji i cache-bustingu; brak source map; brak modułów ES (globalne obiekty `Network`, `GameApp`, `Extras`).
🐛 **Wykryte bugi/luki:** 1. Zapomniany `build.py` po zmianie JS = stary klient na produkcji (zdarzało się w trakcie prac) — **NISKI**.
🔒 **Problemy bezpieczeństwa:** inline skrypty uniemożliwiają ścisłe CSP (`script-src 'self'`).
💡 **Rekomendacje:** w docelowym stacku zbędne (Flutter build); do tego czasu — build w Dockerfile, nie ręcznie.
🔄 **Jak przepisać na NestJS:** nie dotyczy — zastąpione przez `flutter build web/apk/ipa` + CI.

---

### 📄 tools/seed_sparring.py
**Rola:** Skrypt QA tworzący postacie do sparingów PvP na bazie testowej.
**Linie kodu:** 63
**Ocena:** 6/10

✅ **Mocne strony:** przyspiesza testy PvP; izolowany od serwera; czytelny cel.
❌ **Słabe strony:** pisze bezpośrednio do SQLite z pominięciem reguł gry; brak flagi „tylko baza testowa”; brak testów.
🐛 **Wykryte bugi/luki:** 1. Możliwe uruchomienie na produkcji — **NISKI**.
🔒 **Problemy bezpieczeństwa:** brak.
💡 **Rekomendacje:** przenieść do `prisma/seed.ts` z blokadą `NODE_ENV !== 'production'`.
🔄 **Jak przepisać na NestJS:** `prisma/seed.ts` + `npm run seed:sparring`.

---

### 📄 \_\_init\_\_.py
**Rola:** Pusty znacznik pakietu `server`. **Linie kodu:** 0. **Ocena:** — (nie dotyczy).

---

## 📌 TOP 10 PRIORYTETÓW (z Sekcji 2)

| # | Problem | Plik | Stopień | Wysiłek |
|---|---|---|---|---|
| 1 | Wiek deklarowany checkboxem (RODO art. 8, sklepy) | shop.py / rejestracja | WYSOKI | M |
| 2 | `StopIteration` przy trasie usuniętej z katalogu → zablokowany odbiór | economy.py:486 | WYSOKI | S |
| 3 | Exploit eventów: przetrzymywanie odbioru do okna premii | economy.py | ŚREDNI | S |
| 4 | Auto w trasie NPC używane jednocześnie do podróży | travel.py / economy.py | ŚREDNI | S |
| 5 | Replay walki bez wersji silnika | combat.py | ŚREDNI | S |
| 6 | Brak testu odtwarzania kopii + kopie nieszyfrowane | backups.py | ŚREDNI | M |
| 7 | `grant-cash` bez audytu | manage.py | ŚREDNI | S |
| 8 | Stan gracza jako blob JSON (blokuje skalowanie i analitykę) | app.py / economy.py | ARCHITEKTURA | L |
| 9 | Race conditions limitów po przejściu na Postgres | features/shop/pvp | ŚREDNI (migracja) | M |
| 10 | `rate_limits` rośnie bez końca | app.py | NISKI | S |

S = godziny, M = 1–3 dni, L = tydzień+ (dla jednej osoby part-time).
