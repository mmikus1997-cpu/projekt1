# CITY EMPIRE — online 0.55.0

Działająca wersja rozwojowa: konta i postacie, legalne kontrakty, firmy, rezydencja z odpoczynkiem, sportowe PvP, niezależne światy, organizacje i czat. **Bez prawdziwych płatności.** Nie jest to wydanie produkcyjne ani certyfikacja bezpieczeństwa, RODO czy zgodności ze sklepami.

## 0.55.0 — „Moja dzielnica": 6 budynków zastępuje zakładki
- **Rewolucja UI (decyzja usera: budynki ZASTĘPUJĄ zakładki).** „Moja dzielnica" to teraz siatka 6 budynków: Rezydencja 🏠 (odpoczynek), Garaż 🚗 (5 aut, ulepszenia, serwis), Kawiarnia ☕ (idle offline — podsumowanie nieobecności „Witaj z powrotem" + skarbiec), Siłownia 💪 (Statystyki i trening + ekwipunek), Sala Klubowa 🥊 (hub mini-gier i PvP), Sala Chwały 🏆 (bramka poziomów).
- **Poziomy budynków 1–5:** koszty 500/1500/3000/6000 $ (`BUILDING_UPGRADE_COST`), stan `state.buildings`, akcja API `upgrade_building` + katalog (`buildings`/`buildingMax=5`/`buildingCosts`/`hallCost=10000`). Sala Chwały: opłata 10 000 $ wymaga 5 budynków na poziomie 5 (409 w przeciwnym razie); po odblokowaniu tablica 6 wierszy + tytuły + historia + wykres dzienny (historia widoczna także pod bramką).
- **Sala Klubowa = hub kart:** 8 kart dyscyplin (`#club-hub .club-card[data-tab]`) zamiast paska zakładek; przycisk „Wróć do Sali Klubowej" (`#club-back`); pane dyscyplin `#sport-pane-<key>`; automatyczne przejście z mapy (Loch→Ring, Hipodrom→Jazda konna) bez zmian.
- **Sidebar okrojony:** Moja dzielnica, Kontrakty, Firma, Mapa, Społeczność, Ranking (+ panele dev). Podróże (mapa miasta, autobus) w „Mojej dzielnicy"; mini-mapa: klik w kropkę = okno dzielnicy, klik w CTA = wielka mapa.
- **Naprawki:** kontrakty nie blokują erą lokacji surowcowych (surowce zawsze otwarte — spójne z mapą i `travel.py`); balans `</div>` w arenie (banner wyniku wypadał z `#view-arena` do ukrytego panelu — powtórka PvP nieklikalna); layout Sali Chwały na 320 px (`.hall-row` wrap); notka Garażu w Firmie aktualizuje do nowego budynku.
- **Testy: pytest 204/204** (nowy `test_buildings.py`: katalog, koszty, sufit poziomu, bramka i odblokowanie Sali Chwały, walidacja 409); **E2E 37/37 CJS + shot510/512/513/520** (nowy `test-district.cjs`: 6 kart, hub klubu 8 kart, bramka→odblokowanie, rozbudowa, 0 błędów JS). `manage.py grant-cash` do testowego zasilania.

## 0.54.0 — „Mapa": 5 miast + 3 lokacje surowcowe, wydobycie i skup surowców
- **Mapa przebudowana: 8 dzielnic → 5 miast + 3 lokacje surowcowe** (decyzja: mapa ZASTĘPUJE dzielnice). Miasta: Ostoja 🏠, Centrum 🏛️, Portowe ⚓, Biznesowe 💼, Sportowe 🏟️. Lokacje surowcowe **zawsze otwarte** (bez bramek Er): Zakłady Miejskie 🏭 = tworzywa, Kopalnia ⛏️ = ruda, Lasy Wschodnie 🌲 = drewno. Brama Lochu zostaje w Lasach Wschodnich.
- **Wydobycie i skup:** w lokacji surowcowej kopiesz surowiec (energia 10–14/kurs), w każdym mieście sprzedajesz po cenie miasta (Ostoja ×1.0, Portowe ×1.5 ruda, Biznesowe ×1.25, Sportowe ×1.3 drewno). Panel w oknie dzielnicy (`mapMatPanel`) + badge MIASTO/LOKACJA SUROWCOWA.
- **Ery i mapa:** Era I = miasta 1–3, II = +Biznesowe, III = +Sportowe (loch), IV = wszystkie; surowce otwarte od startu. Kalendarz Er: III = dzielnice 1–6 (poprawka).
- **Inwestycje:** 6 dzielnic (Zakłady Miejskie, Centrum, Portowe, Biznesowe, Sportowe, Lasy Wschodnie); stare nazwy remapowane w `sync()` (`INVEST_RENAME`) — bez migracji ręcznej.
- **Pinezki mapy:** City Courier + Magazyny (d2), Hala Targów (d4), Brama Lochu (d8); nowe grafiki `loc-quarry.jpg`, `loc-forest.jpg`.
- **Naprawki:** dispatcher `data-game` przeniesiony na poziom `document` (przyciski akcji w oknach dialogowych nie działały poza widokami); etykiety „Powrót do: Ostoja"; copy podróży i huba.
- **Testy: pytest 200/200** (nowy `test_materials.py`: bramki 409, przepływ gather→sell, ceny per miasto); **E2E 30/30 CJS + shot510/513/520 PASS** (shot520: przepływ wydobycie→sprzedaż na world 2 ×60).

## 0.53.0 — Klub Sportowy: Postać i trening + Wyzwania PvP w klubie
- **Klub Sportowy to teraz hub rozwoju i walki.** Zakładki „Postać i trening" i „Wyzwania PvP" przeniesione do Klubu Sportowego (obok Boksu, Koni, Agility, Siłowni, Łucznictwa, Pływania i Ringu — 9 zakładek).
- Z bocznej nawigacji znikają osobne „Postać i trening" i „Wyzwania PvP" — zostaje jeden skrót „Klub sportowy". Wszystkie dotychczasowe wejścia (kafel „Rozwijaj postać", pinezka „Trening", skróty PvP) prowadzą teraz do odpowiedniej zakładki klubu.
- To pierwszy etap redesignu „miasto gracza" (Sala Klubowa = hub mini-gier i PvP wg nowej wizji mapy).
- Testy: **pytest 197**; E2E **shot520/economy/idle/garage/online/classes/dungeon/evolutions PASS** (każdy przez `qa-suite.sh`); zaktualizowano nawigację w 14 plikach testów (przekierowania do klubu, `#pvp-mount`). Health **0.53.0**.

## 0.52.3 — „HUD na wierzchu": kafelki szybkie w nagłówku, sprzątanie huba
- Kafelki szybkie (KONTRAKTY / CITY COURIER / postać) przeniesione z dołu huba do nagłówka, obok „CITY LAB · Twój niezależny świat" — jeden rząd z tytułem, tuż nad HUD-em.
- Kafelki kompaktowe: opisy ukryte, mniejsze ikony i przyciski — mniej scrollowania do paska miasta.
- Usunięto pasek „Witaj z powrotem · X poza miastem" z „Moje Miasto" (w Rezydencji zostaje — tam obsługuje odbiory po nieobecności; hook testów `.away-box` nietknięty).
- Testy: **pytest 197**; E2E **economy/idle/garage/online/classes/dungeon/evolutions PASS** (przez `qa-suite.sh` — świeża baza na każdy test); **shot520.cjs** + asercje 0.52.3 (kafelki w nagłówku w jednym rzędzie z tytułem, kompaktowe, brak paska powrotu w Mieście, Rezydencja zachowana). Naprawiono martwy hook `[data-invite]` → `[data-attack]` w `test-classes.cjs`. Health **0.52.3**.

## 0.52.2 — „Dzień w mieście": okno po zalogowaniu, tło mapy, grafiki lokalizacji

- **Okno „Dzień w mieście"** po wejściu na świat (po samouczku): codzienny briefing z **3 zdjęciami** (Port/Biznes/Arena), sekcją **„Witaj z powrotem"** (podsumowanie nieobecności + CTA „Odbierz dochód"/„Odbiór zleceń") i **„Przetarg dnia"** (CTA „Przyjmij przetarg"). Wszystko w jednym oknie, zamykane po akcji.
- **Tło wielkiej mapy**: `bigmap-world` z fotografią miasta + przyciemnieniem (pan/zoom razem z mapą).
- **Okna lokalizacji z grafikami**: hero-obraz dzielnicy/miejsca w oknach mapy (`MAP_ART` — 8 dzielnic na 5 grafikach) zamiast pustego okna; **klikalne listy miejsc** w oknie dzielnicy prowadzą wprost do lokalizacji (`data-map-go`).
- **Mini-mapa**: klik w lokalizację (numer) otwiera okno jej dzielnicy z grafiką i miejscami.
- Dokończono usuwanie „Twój kolejny krok" (martwa funkcja `roadmapHTML` wycięta z extras.js).
- Testy: **pytest 197**; E2E **economy/idle/garage/online PASS**; **shot520.cjs** rozszerzone (tło bigmap, okno dzielnicy z miejscami, klik z mini-mapy, brief 3 zdjęcia+przetarg; zrzuty `screens52/04–05`). Zaktualizowano testy z reloadami (zamykanie briefu). Health **0.52.2**.

## 0.52.1 — Mini-mapa z tłem, samouczek znika po 4/4, usuwanie „Twój kolejny krok"

- Tło mini-mapy (`mini-map-btn`) z `city-map.jpg`; panel „Pierwsze kroki" chowa się sam po ukończeniu 4/4; panel „Twój kolejny krok" usunięty z huba. Testy: pytest 197, E2E zestaw PASS, shot520 (asercje tła/roadamy).

## 0.52.0 — „LIFE CITY": nowy skin graficzny + wygenerowane arty (inspiracja: makieta gracza)

- **Dwie autorskie grafiki AI** (`web/art/`): **okładka** — nadbrzeżna metropolia nocą z palmami i sportowym autem (tło ekranu „Wybierz swój świat"), **mapa dzielnicy** — izometryczny port ze stadionem, parkiem i przemysłem (tło wielkiej mapy na hubie). Konwersja do lekkich JPEG (197/247 KB).
- **Nowa trasa serwera `GET /art/{name}`** — serwowanie plików z `web/art` z walidacją nazwy (regex + whitelist rozszerzeń; trawersacja → 404; cache 24 h).
- **Skin „granat + electric blue"** (wariant zmiennych tylko w `.online-version`): tło #0b1220, panele #101b2d, akcent niebieski #4aa8ff (złote CTA → niebieskie jak na makiecie), aktywne pozycje menu i karty światów w niebieskich poświatach; hub dostaje fotograficzną mapę z pinami (SVG-art mapy schowany, legenda zostaje).
- Zero zmian w geometrii widoków, hookach testów i logice — warstwa czysto wizualna na bazie 0.51.3.
- Testy: **pytest 197** (+ trasa /art w grain), E2E **economy/idle/garage/online PASS**, nowy **tests/shot520.cjs** (weryfikacja tła mapy, 0 błędów JS; zrzuty `screens52/01–03`). Health **0.52.0**.

## 0.51.3 — „Gęstość III": ranking, społeczność, przedsiębiorstwa, postać, konto

- **Ranking**: wiersze tabel 19→10px paddingu, rating 16→14px — 200 przeciwników zamiast 60 na ekranie; karty kawiarni (café-panel 25→14–16px, grafika 193→150px), kroki samouczka 15→10px, wiersze PvP (opponent/challenge 17–18→10–11px), statystyki admina, tożsamość konta, czat 380→300px.
- Zero zmian w strukturze HTML i JS — wyłącznie wartości CSS (desktop ≥901px, mobile nietknięty).
- Testy: **pytest 197**; E2E **qol/hub/economy/shop/idle PASS, smoke-451 czysty**; nowy **tests/shot513.cjs** — audyt 5 widoków (ranking/społeczność/przedsiębiorstwa/postać/sklep) z zrzutami `screens51/09–13` i kontrolą overflow/błędów JS. Health **0.51.3**.

## 0.51.2 — Karty światów: szczegóły w popoverze, przycisk „Wejdź do postaci" stoi w miejscu

- **Fix rozjeżdżania okładki**: „szczegóły po najechaniu" (`.world-more`) rozwijały się w flow karty — przycisk wejścia uciekał w dół, a sąsiednia karta rozciągała się do równej wysokości (pusta dziura). Teraz (desktop >680px) szczegóły to **pływający popover pod kartą** (position:absolute, cień, mostek 9px przeciw znikaniu przy przejściu myszy): karta i grid pozostają nieruszone, `align-items:start` na `.world-grid`.
- **Mobile (≤680px) bez zmian**: szczegóły nadal zawsze widoczne inline (hover nie istnieje na dotyku).
- Testy: **pytest 197**, **test-online (28 layoutów) PASS**, nowy **tests/shot512.cjs** (asercje: przycisk Δ0px i sąsiad Δ0px podczas hovera, popover widoczny/absolutny, mobile inline; zrzuty `screens51/06–08`). Health **0.51.2**.

## 0.51.1 — „Gęstość II": Arena PvP, dialogi i topbar dociągnięte do standardu minimalizmu

- **Arena PvP kompaktowa**: portret zawodnika 232→188px, ciaśniejsze .fighter-top/.fighter-details/.duel (22→16px), mniejsze kafle taktyk i pasek kondycji 7→6px — sparring z turniejem mieści się w ~1,5 ekranu zamiast 3.
- **Topbar 76→56px**, tytuły widoków .page-title 27→34→24px, marginesy nagłówków 27→16px — spójna skala z 0.51.0.
- **Dialogi odchudzone**: szerokość 620→560px, padding 23→16–18px, nagłówki 20→17px.
- Kontynuacja 0.51.0 bez zmian w szablonie HTML (selektory te same, tylko wartości); zero dotknięć logiki.
- Testy: **pytest 197**; E2E **test-online (28 layoutów) PASS, test-avatar 24/24, economy/idle/garage/shop/qol/hub PASS, smoke-451 czysty**; zrzut `screens51/05-arena-desktop.png`. Health **0.51.1**.

## 0.51.0 — „Gęstość i minimalizm": redesign UI/UX

- **Gęstość globalna (desktop)**: padding paneli 23px → 14–16px, cieńsze separatory + delikatny cień zamiast twardych ramek, mniejsze tytuły widoków i paski podsumowania — więcej treści na ekranie bez utraty czytelności (ciemny motyw bez zmian).
- **Przetarg dnia = poziomy pasek akcji** (~56px zamiast dużej karty): gwiazdka · tytuł+zegar · nazwa zlecenia z nagrodą (💸/⭐/⚡/🔒) · przycisk „Przyjmij przetarg". 
- **Karty zleceń = kompaktowe wiersze** (ikona | eyebrow+nazwa | metryki | cena+akcje): pełna lista 9 kontraktów bez pustej czarnej przestrzeni; opis i dzielnica schowane (nazwa ma tooltip), na mobile wiersz savvy zawija się pod ikonę; 390px bez overflow.
- **Hub „Moje miasto" dwukolumnowy**: treść po lewej, po prawej **mini-mapa (max ~250px wysokości) nad „Pierwszymi krokami"**; kafle szybsze i mniejsze; stopka doklejona do dołu ekranu przy krótkich widokach.
- **„Witaj z powrotem" = smukły pasek-alertu** z licznikami-chipami (zlecenia/treningi/skarbce/odpoczynek) i przyciskiem **×**; duży blok z siatką zniknął — informacja ta sama, miejsce czterokrotnie mniejsze.
- **Rezydencja**: mieszkania w **trójkontowej siatce** (`repeat(auto-fit,minmax(272px,1fr))`, ikona na górze, opis pod spodem, cena+przycisk na dole), węższy panel Odpoczynku; Garaż bez pustych przestrzeni w opisach.
- **Sidebar kompakt**: niższe pozycje menu, mniejszy panel gracza (GOTÓWKA/ENERGIA/XP bliżej siebie) — nawigacja zajmuje mniej pionu.
- Haki testów zachowane: `.tender-panel`+„Przetarg dnia", `.away-box`+„Witaj z powrotem"+`[data-away-dismiss]` (X też go niesie), `.mini-map-panel`/`.mm-dot.me`/`.mini-map-cta`. Wersja **0.51.0** (health, stopka, okładka „DEV 0.51.0"). Testy: **pytest 197**; E2E **test-economy/idle/garage/shop/online/qol/hub/map PASS, test-avatar 24/24, smoke-451 czysty**; zrzuty `screens51/01–04` (hub/kontrakty/rezydencja desktop + hub mobile).

## 0.50.0 — Chip auta w HUD i spójne wejścia do klubu z mapy

- **Chip aktywnego auta w sidebarze** (pod energią/XP): 🚚 ikona, nazwa auta i zużycie; przy 100% chip czerwienieje („serwis!"), a klik przenosi prosto do zakładki 🚗 Garaż w Rezydencji. Chip aktualizuje się w czasie realnym razem z resztą HUD (kryje się, gdy nie masz auta). Spina garaż 0.49 z HUD-em.
- **Miejsca klubu z mapy otwierają właściwą zakładkę**: 🚪 Brama Lochu → **🐉 Ring**, 🏇 Hipodrom → **🏇 Jazda Konna**, 🥊 Klub Sportowy → **🥊 Boks/MMA**. Działa zarówno z „Wejdź", jak i z „Jedź i wejdź (20 $)" — zakładka ustawia się po wejściu na arenę. Dotąd wszystkie trzy prowadziły na Boks/MMA, a loch „gubił się" po przebudowie 0.49.1.
- **Porządki CSS**: z arkuszy zniknęły martwe reguły po panelach usuniętych w 0.49.1 (`.fx-demo` ×10 w style.css, `.arena-mode-panel` ×9 + `.demo-time-buttons` w game.css) — budowany `index.html` jest czystszy.
- Wersja **0.50.0** (health i stopka). Testy: **pytest 197**; **test-garage** rozszerzony o 0.50 (chip: widoczność po zakupie, nazwa+0%, klik→Garaż; mapa: Hipodrom→Konie i Loch→Ring z ustawieniem zakładki, na świeżej bazie z cofniętą datą świata do Ery 4 i postacią w dzielnicy miejsca); regresja **test-online PASS, test-avatar 24/24**, smoke/shop/qol/hub/economy PASS; zrzut `screens49/20-hud-chip.png`.

## 0.49.1 — Klub Sportowy: czystszy ekran, Brama Lochu jako zakładka „Ring"

- **Zakładka „Ring" (🐉)** — siódma zakładka Klubu Sportowego, obok Boks/MMA…Pływanie. **Brama Lochu** (do tej pory przyklejona na dole widoku w każdej zakładce) mieszka teraz **tylko tam**: progres pięter, CTA lokacji i walki. Raporty pojedynków zostają wspólne dla całego klubu.
- **Usunięty panel „Klub sportowy / Moja postać"** z góry widoku — nic nie wnosił: postać jest (i zawsze była) domyślnym zawodnikiem sparingu. Tryb Laboratorium pozostaje: przycisk „Laboratorium" w sidebarze prowadzi na arenę w trybie testowym i otwiera dialog balansu; w dialogu jest teraz **„Wróć do mojej postaci"**, żeby jednym kliknięciem wyjść z trybu lab.
- **Usunięty pasek „SPRAWDŹ EFEKT"** (Cios / Parada / unik / + Krytyk) — podgląd pojedynczych akcji nie musi okupować stałego miejsca; logika żyje w `previewMotion()` (używana też przez testy animacji), pasek i jego CSS zniknęły z widoku.
- Wersja **0.49.1**; testy: **pytest 197**, E2E **test-dungeon** (loch w zakładce Ring: progres 0% → CTA → walka → dialog wygranej), **test-avatar 24/24** (podgląd ruchu przez `previewMotion`), **test-online PASS**, garage/economy/smoke/shop/qol/hub PASS; screeny `screens49/10–11` (Boks bez pasków, Ring z Lochu). Stary `test-combat-motion.cjs` wycofany (opisywał UI sprzed 0.48 — pokrycie przejął test-avatar). Health **0.49.1**.

## 0.49 — Garaż w Rezydencji: 5 aut z grafikami, ulepszenia, VIP; HUD w sidebarze; scalone statystyki

- **Garaż jak zakładka Rezydencji**: widok „Rezydencja” ma teraz zakładki **🏡 Dom / 🚗 Garaż** (ten sam wzór co dyscypliny Klubu Sportowego). W zakładce Garaż: **5 samochodów z autorskimi grafikami SVG** (Rower dostawczy, Furgonetka, Sedan Miejski, Bus flotowy, Hiper Widok GT), kupno, wybór aktywnego auta, **ulepszenia (3 poziomy: silnik, zawieszenie, lakier — każde +4 p.p. rabatu czasu, koszt rosnący 40/80/120% ceny)** i **naprawa/serwis** po zużyciu 100%. Pasek stanu: auta w garażu vs miejsca parkingowe (rezydencja + Charyzma), przypomnienie +6% zużycia za zlecenie.
- **Auto VIP**: **Hiper Widok GT** (lvl 8, 16 000 $, rabat 42%) ma złotą plakietę 👑 VIP i złotą ramę karty — bez aktywnej sesji VIP przycisk jest zablokowany z komunikatem, a serwer niezależnie odrzuca zakup (druga brama w `buy_vehicle`). VIP w duchu istniejącego sklepu dev: bez prawdziwych płatności.
- **Przeniesienie garażu z Przedsiębiorstw**: w „Przedsiębiorstwa” został zespół (pracownicy na dobę), a sekcja Pojazdy to czytelna nota z przyciskiem „Otwórz garaż w Rezydencji” (stare e2e zaktualizowane).
- **HUD w sidebarze**: pasek (nick · poziom i świat, GOTÓWKA, ENERGIA z paskiem, XP, przycisk **Konto**) siedzi teraz w sidebarze — pod logo i wyborem świata, **przed „Twoje miasto”**; topbar jest czystszy, a także na wąskich ekranach HUD przechodzi w wersję ikon (64 px sidebar).
- **Scalony panel rozwoju**: „TWOJA POSTAĆ” + „Centrum szkoleniowe” + „Statystyki w akcji” + „Zaplanowane treningi” to jeden kompaktowy panel **„Statystyki i trening”** — wiersz statystyki pokazuje teraz wartość (z bonusami z eq) i przycisk „+ Trenuj” obok efektów; kolejka treningów pod spodem. Więcej miejsca, prostsze informacje, zero duplikacji.
- **Porządki**: usunięte martwe pozostałości paneli wyzwań (`incoming/outgoing` w showPvp, handler `data-invite`) — stringi „Otrzymane wyzwania” i „Wysłane zaproszenia” nie występują nigdzie w UI.
- **Serwer**: `GARAGE` = 5 aut z polami `img`/`vip`; akcja **`upgrade_vehicle`** (limit 3 poziomy/auto, stan `garageUp` w zapisie postaci z migracją starych kont); `vehicle_discount` sumuje rabat auta + ulepszenia; `buy_vehicle` dostaje bramę `vip` (sprawdzaną z `shop_state.vip_until`); health **0.49.0**.
- Testy: **pytest 197** (+4: katalog 5 aut z grafikami/VIP, kupno+ulepszenia+stacking rabatu z capem parkingowym, zużycie→0 rabatu+serwis, brama VIP bez/z sesją); E2E **test-garage** (nowy: kolejność HUD w sidebarze, scalony panel, zakładki, 5 grafik, VIP-lock, kupno/ulepszenia/naprawa, cap parkingowy, nota w firmach, 390 px) + **test-avatar 24/24**, **test-online PASS**, smoke/shop/qol/hub/economy PASS; 7 screenów w `screens49/`. Health **0.49.0**.

## 0.48 — Płeć awatara, PvP bez wyzwań (Pisz/Gildia), animacje zawsze włączone z wariantami

- **Płeć awatara (👨/👩)**: przełącznik w kreatorze postaci i edytorze; sylwetka kobieca = węższa klatka, szersze biodra, lżejsze ramione (osobne kształty SVG). Płeć przechowuje i waliduje serwer (m/k; starsze postacie → m); 🎲 Losuj losuje też płeć; klasa .av-g-k rozpoznaje sylwetkę wszędzie.
- **Wiersz rywala PvP bez „Wyzwij”**: ⚡ Atakuj · 💬 Napisz · 🛡️ Gildia. Napisz otwiera DM z rywalem; Gildia tylko dla lidera/officera organizacji — potwierdzenie + POST /organizations/invite (limity 1/24 h bez zmian). Sekcje „Otrzymane/Wysłane wyzwania” zniknęły; dialog Auto-ataku ma ▶ Odtwórz raport — natychmiastową animowaną powtórkę walki.
- **Animacje walki zawsze włączone**: „Wyłącz animacje” usunięte; zostaje tempo 1×/2×/4× i „Pomiń”. Odtwarzanie deterministyczne: 5 wariantów lotu ataku (prosty, górniak, obrót, zwód, seria z duchem drugiego pocisku) i 4 warianty pracy tarczy obrońcy (podniesienie, ukos, wybijenie, absorpcja), wybierane z numeru rundy — powtórka pokazuje to samo.
- **Grafika pod każdą akcję**: pocisk to rzeczywisty przedmiot zawodnika (🥊 pięść z rękawic, 🦵 but, 🪖 hełm — hełm koziołkuje, but wchodzi pod kątem) w barwach założonego itemu; niecelny atak odbija się od tarczy; uniki = 4 pozy awatara (odchylenie, przykuc, przeskok, weave), trafienia = 3 pozy + osobny krytyk.
- **Sparing w Klubie na awatarach**: partner treningowy ma stabilny losowy wygląd (per przeciwnik) i podstawowy zestaw sprzętu w ruchach.
- **Serwer**: silnik simultaneous dźwiga prezentacyjny tor events+profiles (1:1 z autorytatywnym przebiegiem — wynik, Elo i taktyki bez zmian); panel PvP zwraca myOrg (id/tag/canInvite); katalog z bodies.genders; atak bez taktyki prowadzi do karty wyboru zamiast błędu.
- Testy: **pytest 193** (+2: płeć w brief/validate + myOrg w panelu PvP; katalog z genders); E2E **test-avatar 24/24** i **test-online PASS** (PvP przepisane: bez Wyzwij/accept, auto-atak → dialog → animacja z avatars+gear, 28 layoutów w tym PvP na 320 px); regresja smoke/shop/qol/hub PASS. Health **0.48.0**.

## 0.47 — Awatar wchodzi do gry: sprzęt zmienia wygląd, PvP pokazuje awatary, karty światów kompaktowe

- **Losowy wygląd jednym klikiem**: przycisk **🎲 Losuj** w kreatorze postaci (i w edytorze awatara) — losuje karnację, fryzurę, kolor i strój z rzeczy zwykłych (bez VIP, chyba że VIP jest aktywny).
- **Zasada nakładania jak w grach**: klik w rzecz z **tej samej kategorii podmienia** ją automatycznie; **kategorie konfliktowe (czapka ⇄ kapelusz, spodnie ⇄ spodenki) blokują klik z tostem** „Nie można nosić jednocześnie…" — nic nie zdejmuje się po cichu. Klik w założoną rzecz zdejmuje ją. Te same reguły pilnuje serwer (`server/avatar.py`: SLOT_OF + COVERS).
- **Wszystkie rzeczy awatara w Sklepie w grze**: sekcja **„Garderoba awatara"** (140 kosmetyk, 14 kategorii × 10, 3×VIP każda) w zakładce **Sklep** w menu bocznym — kupno za gotówkę z gry, „Załóż" zmienia wygląd od razu.
- **Sprzęt ze statami zmienia wygląd awatara**: pełne połączenie gear↔avatar — 19 przedmiotów gry (rękawice, buty, hełmy, plecaki, amulety, stroje…) ma przypisane warstwy `gameLooks`; kupno/założenie itemu **widocznie zmienia awatara** wszędzie (profil, EQ, PvP, karta świata). Nowa postać startuje ubrana w 7×basic.
- **PvP pokazuje zawodników**: raporty ataku/przyjęcia wyzwania i odtwarzania zapisanych walk dźwigają `avatars` (wygląd obu graczy) + `gear` (co mają założone); portrety na arenie to **żywe awatary obu graczy**, a każdy cios pokazuje **chip ruchu z konkretnej rzeczy** — „🥊 Cios · Rękawice treningowe", „🦵 Kop · Buty sportowe", „🪖 Uderzenie hełmem · Kask treningowy" (kolejność wg założonego sprzętu; czysta prezentacja — wynik liczy serwer). Lista przeciwników PvP też ma mini-awatary.
- **Edycja awatara w grze**: przycisk **„🧍 Edytuj awatara"** na ekranie postaci (nagłówek profilu + kafelek w siatce EQ) otwiera edytor (ciało + 14 kategorii, 🎲 Losuj, zasady podmian/blokad) i zapisuje przez `POST /worlds/{id}/avatar`.
- **Karty wyboru światów mniejsze**: siatka kompaktowa (min. 228px), mniejsza typografia; pełne szczegóły (otwarcie, era, sezon, ogłoszenia, zastrzeżenia) **na hover/focus** z podpowiedzią „ℹ️ szczegóły po najechaniu"; na dotyku rozwinięte domyślnie.
- **Serwer (0.47)**: katalog dźwiga `gameLooks` (mapowanie item↔warstwa), `players()`/`targets()`/raporty PvP zwracają `avatar`/`avatars`+`gear`; kompozycja warstw z covers w `server/avatar.py`. Ikony hełm/plecak/amulet w zestawie UI.
- Testy: **pytest 191** (+9 testów 0.47: kształt katalogu z gameLooks, reguły slotów/podmian, kompozycja gameLooks z covers, 7×basic start, kreacja z awatarem, kupno/przymiarka/VIP, rankingi, raport PvP z awatarami, katalog bez sesji); E2E **+`tests/test-avatar.cjs` (19 asercji)**: kompaktowe karty+hover, 🎲, konflikt czapka⇄kapelusz z tostem, podmiana w kategorii, awatar na profilu/EQ/arenie/kanie świata, Garderoba 14×10, chip ruchu z założonego itemu; regresja **test-online / smoke-451 / shop / qol / hub — PASS**. Health **0.47.0**.

## 0.45 — Interaktywna mapa: kontrakty jako lokalizacje, władza dzielnic, dojazd z bonusem

- **Klik w ikonę = wejście**: każda pinezka (miejsce, zlecenie, dzielnica) otwiera karta lokalizacji z CTA — „Wejdź", gdy jesteś na miejscu, albo **„🚌 Jedź i wejdź (20 $)"**, które startuje podróż i prowadzi do widoku po przyjeździe (podwójna podróż zablokowana).
- **Nakierowanie = okienko**: hover/tap na pinezce pokazuje szybką kartę — nazwa, dzielnica, opis, **które przedsiębiorstwo (organizacja) rządzi dzielnicą** albo status neutralnej, a dla zamkniętych — **odliczanie dni do otwarcia w kolejnej Erze** (dzień X/28, jak na karcie świata) wraz z wymaganiami (✓/✗: poziom, taktyka, obecność w dzielnicy).
- **Władza dzielnic w pakiecie stanu**: `territory` (tag+nazwa organizacji i od kiedy rządzi — z tabeli 0.11) dolejwa się do mapy i dialogów; „Kliknij: podróż" tam, gdzie trzeba.
- **Kontrakty jako lokalizacje na mapie** (jak City Courier): każde zlecenie ma swoją dzielnicę i pinezkę; przyjęcie kontraktu **wymaga bycia w jej dzielnicy** (serwer: 409 z nazwą lokalizacji). Karty w Zleceniach pokazują lokalizację, stan „Poza dzielnicą" i przycisk „🚌 Jedź (20 $)".
- **Bonus za dojazd rozdzielony na kontrakty**: +4% za każdy przystanek kolejowy od Mojego Miasta (Port/Biznesowa/Konferencyjna +8%, Centrum/Kreatywna/Przedmieścia +4%) — liczony serwerowo przy odbiorze i pokazywany na kartach; kontrakty z zamkniętych Er są oznaczone „Otwarcie w Erze N".
- **Nawigacja mapy**: wejście w mapę **centruje na obecnym kaflu** (zoom 1), scroll/pinch przybliżają **do kursora** (0.5–2.2×), a sterowanie (＋/−/Wyśrodkuj/📸/🔊) siedzi w **lewym górnym rogu**.
- Testy: pytest **182 passed** (formuły z bonusem dojazdu, brama dzielnic); E2E **29/29** (map/economy/online/features/idle dostosowane: seedy dzielnic + starzenie światów do Er III/IV tam, gdzie kontrakty tego wymagają). Health **0.45.0**.

## 0.46 — Awatar: kreator przy tworzeniu postaci, garderoba, ranking przed grą

- **Własny awatar od pierwszego logowania**: kreator „Nowa postać" otwiera się razem z **żywym, animowanym awatarem** (oddycha, mruga, kołyszy się — SVG, `prefers-reduced-motion` uszanowane). Zakładka Ciało: 6 karnacji, 6 fryzur, 8 kolorów włosów. Dalej **14 kategorii garderoby**: okulary, czapki, kapelusze, kolczyki, naszyjniki, pierścionki, koszulki, bluzy, kurtki, spodnie, spodenki, skarpetki, buty i plecaki — **po 10 rzeczy w każdej (140 łącznie), w tym dokładnie 3×👑 VIP w każdej kategorii**. Rzeczy zwykłe wybierasz na start **gratis**; VIP-owe odblokowuje aktywny VIP.
- **Awatar żyje poza grą**: mini-awatar przy **nicku** na ekranie światów (klik dalej otwiera profil), duży animowany awatar na **karcie każdego świata**, awatar per postać w **profilu konta**. Wygląd zapisany na serwerze (`state_json.avatar`) — podąża za kontem wszędzie.
- **Garderoba w sklepie**: nowa sekcja z pełnym katalogiem — kupno za **gotówkę z gry** („Kup · 60 $", zakłada od razu), „Załóż"/„Założona" przełącza wygląd bez kosztów, rzeczy VIP zablokowane bez aktywnego VIP. Zero wpływu na statystyki, ekonomię i PvP — czysta kosmetyka.
- **Ranking przed grą**: nowy przycisk **🥇 Ranking** obok Konta — dialog z **globalnym rankingiem sezonu (TOP 10 + Twoja najlepsza pozycja)** i **TOP 10 + pozycją każdego świata, gdzie masz postać**. Pełne rankingi (Elo, archiwa) dalej w grze.
- **Serwer (0.46)**: `GET /api/avatar/catalog`, `POST /worlds/{id}/avatar` (przymiarka: tylko posiadane rzeczy), `POST /worlds/{id}/wardrobe` (kupno: unikalność, VIP, saldo), `GET /api/account/rankings`; walidacja wyglądu w jednym miejscu (`server/avatar.py`), awatar doklejony do `/api/worlds`, profilu i kreacji postaci. Koperta preview rozszerzona o nowe ścieżki.
- Testy: **pytest 188** (+6: kształt katalogu, reguły walidacji, kreacja z awatarem, kupno/przymiarka/VIP, rankingi konta, brak dostępu bez sesji); E2E **30/30** (+`test-avatar`: kreator→zapis→kupno→ekran światów→ranking→profil). Health **0.46.0**.

## 0.45.2 — Profil konta przed grą + naprawa wejścia do świata

- **Klik w własny nick = profil z osiągnięciami**: na ekranie wyboru światów przy „Kontu" stoi teraz chip **👤 nick**; otwiera dialog „Profil · nazwa" (nowy `GET /api/account/profile`, tylko do odczytu) — dla każdej postaci na każdym świecie: poziom i pasek XP (obecny/następny próg), kasa, klasa i ewolucja, Elo i bilans PvP (W/L/D), postęp w lochu, liczba „uczynków" (kontrakty+treninki+odbiory) oraz **tytuły** (do 24 + licznik „+N"). Wszystko widać **przed** wejściem do gry, dokładnie te dane co w profilu w grze.
- **Wejście do świata znowu działa**: logowanie → „Wejdź do postaci" kończyło się toastem „Nieprawidłowa odpowiedź serwera", bo `GET /api/worlds/{id}/state` zwracał 500 (`AttributeError` w `economy.sync` przy nietypowym kształcie zapisu: `staff`/`garage`/`invested` złe typy, `residence` nie-string, brak `completed.*`). `sync()` ma teraz strażniki typów i domyślne klucze — uszkodzony/recznie odtworzony stan nie blokuje wejścia (a zostaje poprawiony w locie).
- **Regresja przy okazji**: „Wyloguj" przestało reagować (przy wstawianiu `case 'profile'` wypadł `case 'logout'` z dispatchera kliknięć) — przywrócone; smoke potwierdza powrót do formularza logowania.
- **Porządki w danych dev**: z rankingu w1 zniknęły 18 śmieciowych tytułów sezonowych przypisanych do konta testowego z 0 XP.
- Testy: pytest **182 passed**; E2E bateria **29/29**; smoke wejścia (login → CITY LAB → profil → światy) i weryfikacja na żywym podglądzie (rejestracja → profil → wejście → wylogowanie, 0 błędów JS). Health **0.45.2**.

## 0.45.1 — Szlify mapy i naprawa „Przyspiesz (VIP)"

- **Przyspieszenie podróży działa**: przycisk „⚡ Przyspiesz (VIP)" padał na błędzie zasięgów (`timerText is not defined` — extras.js nie widzi helperów areny); teraz ma własny formater, a przy okazji wszystkie gołe wołania `renderRacing()` w extras są zabezpieczone przez `window.renderRacing`.
- **Zoom z centrum**: scroll i przyciski ＋/− przybliżają względem **środka viewportu** (0.5×–2.2×, pinch też), a nie „z rogu".
- **Podpowiedź pod kursorem**: karta szybkiej podpowiedzi na mapie pojawia się teraz przy kursorze (z klepsydrami krawędzi), nie w losowym miejscu.
- **Mgły mówią, kiedy**: najechanie na 🚧 pokazuje „Otwarcie w Erze N (nazwa) — za X dni (dziś dzień Y/28)", otwarte dzielnice mają dopisek obecnej Ery; dialog zablokowanego miejsca też podaje dni.
- Testy: pytest **182 passed**; E2E 9/9 regresji (map/hub/travel/economy/racing/online/features/idle/shop) + smoke zoom/hover/speedup. Health **0.45.1**.

## 0.44 — EQ à la Tibia, loch w Klubie Sportowym, sparingowcy na start

- **Wyposażenie jak w klasycznych RPG**: zamiast czterech osobnych kart jest **paperdoll** — postać na środku, wokół cztery realne sloty (Rękawice, Strój, Obuwie, Akcesorium) z podświetleniem założonej rzeczy i czytelnymi pustymi slotami („Kup sprzęt w Sklepie i plecaku"), plus cztery sloty-zapowiedzi (Amulet, Plecak, Tarcza, Nakrycie — „wkrótce"). Na wąskich ekranach figura idzie na górę, duchy slotów znikają.
- **Loch przeniesiony do Klubu Sportowego**: panel „Brama Lochu" stoi teraz w zakładce 🥊 Boks/MMA (PvE obok turnieju), nie w „Postaci i treningu". Przyciski i logika bez zmian (CTA lokacji, walka na taktyce PvP, progres w profilu).
- **Statystyki w akcji bez sd**: wszystkie procenty zaokrąglone do 1 miejsca z przecinkiem (koniec z „0,9999999999999"), wiersze z łagodniejszym tłem; wielki zielony „check" dystynkcji ma wreszcie sanity rozmiaru (20 px).
- **Sklep i plecak bliżej oka**: wiersze z delikatnym gradientem, zaokrągleniem i podświetleniem kursora, ceny w ciepłym złocie z tabularnymi cyframi; karta sklepu bez zmian funkcjonalnych (testy cen 250/228 $ przechodzą).
- **Konta sparingowe (0.44, narzędzie)**: `tools/seed_sparring.py` idempotentnie tworzy pięciu rywali w świecie gracza (postać + klasa + taktyka przez API, XP w bazie) — PvP ma cel od pierwszego wejścia.
- Testy: pytest **182 passed**; E2E **29/29** (test-dungeon przeniesiony za lochem do klubu). Health **0.44.0**.

## 0.43 — Klub Sportowy: hub dyscyplin, karta zawodnika przy PvP, podróż po dochód

- **Klub Sportowy zamiast jednej areny**: nad areną jest pasek zakładek — 🥊 **Boks/MMA** (PvP+PvE, turnieje, rankingi, lochy), 🏇 **Jazda Konna** (wyścigi, skoki, ujeżdżenie + stajnia i hodowla), 🐕 **Agility Psów** (tor przeszkód, ocena tresury), 🏋️ **Siłownia** (trening statystyk, regeneracja), 🎯 **Łucznictwo** (PvP celności), 🏊 **Pływanie** (kondycja → boost ❤️ Charyzmy). Wybór zapamiętywany lokalnie, panele dokarmiane z `GET /sports2`.
- **Nowe dyscypliny serwerowo**: turniej MMA (3 rundy, 2/dobę, nagrody wg bilansu), agility (score 10–120 + oceny A–E, rekordy), łucznictwo PvP na zapisany rekord (rywal z globalnego rankingu `luk.best`, fallback „Mistrz Kolegium"), pływanie (kondycja ≤30, okno 48 h, bonus Charyzmy do +5 liczony w `economy.effective`).
- **Hipodrom rośnie**: trzy konkurencje (wyścigi/skoki/ujeżdżenie z różnymi wagami statów), hodowla (300 $, cooldown 24 h, źrebak gen+1) i wybór stajni (boks/kojca/pastwisko) — każdy koń może stać gdzie innego.
- **Karta zawodnika przy pierwszym PvP**: kreator postaci wraca do równych 10×5 (bez Bokser/Obrońcy/Szybkiego); klasa + taktyka wybierane są **raz**, w oknie przed pierwszym wejściem w ranking (dialog `chooseFightSetup`, POST `/worlds/{wid}/class`, 409 przy próbie ponownego wyboru). Profil i statystyki przeliczane jak wcześniej.
- **HUD areny**: usunięty „Wstrzymaj", tempo ×1/×2/×4 i „Pomiń animację" siedzą przy sterowaniu walki, efekty (Cios/Parada/unik/✦ Krytyk) nad portretami zawodników, demonstracja fx nad stopką duelu; wyłączenie animacji zapisywane na zawsze (localStorage).
- **Biznes**: bramka „odbierz dochód" poza dzielnicą firmy ma teraz gotową akcję **„Jedź i odbierz"** (podróż + powrót do odbioru jednym klikiem).
- Testy: `test_sports2.py` (4), `test_classes.py` +jednorazowość karty, `test_horse_racing.py` +konkurencje/hodowla/stajnia — **182 passed**; E2E 29/29 (test-classes przepisany pod 0.43, test-racing na 3 konkurencje, orgcontracts/evolutions bez klasy w kreacji). Health **0.43.0**.

## 0.42 — Auto-atak: natychmiastowy pojedynek rankingowy z listy rywali

- **„⚡ Atakuj" obok „Wyzwij"**: każdy wiersz rywala w panelu Wyzwań PvP dostaje przycisk **Auto-ataku** — klik i walka rozstrzyga się **od razu** (silnik symultaniczny 0.28), bez czekania na akceptację i bez bycia online po drugiej stronie. Obrońcę reprezentuje **jego zapisana taktyka z 0.41** (głos, którego nie musi oddawać na żywo); bez taktyki i szablonu — sekwencja zrównoważona.
- **Kontrakt 0.42**: payload `/pvp/attack/{id}` jest **ignorowany** (`{}` albo cokolwiek — nawet błędna sekwencja nie zwraca 422); walka zawsze na zapisanych wyborach: atakujący = jego taktyka, obrońcy = taktyka > `pvpDefense` (legacy) > zrównoważona. Raport zyskuje `tactics` (etykiety rozstrzygnięcia) i `stats` (efektywne staty obu stron), a zdarzenie dla obrońcy (`pvp_attacked`) nadal dociera do Centrum Zdarzeń po jego powrocie.
- **Te same bramki co wyzwania**: Auto-atak wymaga **2 lvl + zapisanej taktyki** (409 z tymi samymi komunikatami), limit **5 pojedynków rankingowych/dobę UTC** współdzielony z wyzwaniami, blokady, podróże (atakujący i cel) — bez zmian. Elo przepływa do tych samych tabel (`ranked_usage`, `pvp_battles`) i raport jest w pełni odtwarzalny.
- **Wynik w dialogu, nie w kinie**: po auto-ataku dialog pokazuje wynik (Wygrana/Porażka/Remis), taktyki obu stron i **delta Elo**, panel się odświeża (licznik „Dzisiaj: X / 5 walk UTC"), a pełną animację można obejrzeć z „Zapisanych pojedynków".
- **Poprawka z_okopów**: ułamkowe Elo (auto-atak między różnymi ratingami) wystawało surowym `999.1723853265561` w „Twojej historii" i rozpychało layout @768 — **rating w UI jest teraz zawsze zaokrąglany** (historia, ranking, panel PvP), serwer dalej liczy na floatach dla dokładności.
- Testy: `test_pvp_active.py` przepisany pod 0.42 (payload ignorowany, taktyki w raporcie, bramki lvl/taktyka, fallback obrońcy), `test_classes.py` +dokarmienie atakującego, `test-online.cjs` +scenariusz Auto-ataku (przycisk, dialog z Elo i taktykami, licznik 2/5). Health **0.42.0**.

## 0.41 — PvP 2.0: ranking jako przeciwnicy, taktyka jednorazowa, bramki poziomów, obowiązkowa klasa

- **Klub Sportowy = tylko wyzwania PvP 2.0**: endpoint `/spar` **usunięty** (404), z UI zniknęły selecty taktyki przy zaproszeniu/przyjęciu, a panel prowadzi nagłówek „WYZWANIA PvP — przeciwnicy prosto z rankingu". Laboratorium (`arena-mode=lab`) zostaje wyłącznie jako lokalny tryb testowy: `#fight-btn` jest ukryty poza labem, a start silnika w trybie postaci jest no-op (walka zawsze z raportu serwerowego).
- **Taktyka (Presja/Kontrola/Kontra) wybierana RAZ** — nie przed logowaniem, tylko **przed pierwszym wejściem w PvP w grze**: `POST /worlds/{wid}/tactic` (rate 10/h) zapisuje `state.tactic`, przy drugim wyborze zwraca 409 „wybór jest jednorazowy i nieodwracalny". Dialog `N.chooseTactic()` otwiera się sam, gdy panel PvP wykryje brak taktyki; `invite/accept` ignorują taktykę w payloadzie — walka zawsze na zapisanych wyborach obu graczy (snapshot atakującego mrozi staty+taktykę z momentu zaproszenia).
- **Przeciwnicy z rankingu**: lista wyzwanych to wszyscy inni gracze świata z `#N rankingu` przy nicku (kolejność jak w rankingu Elo); pvp/targets (top20 rating) zostaje jako wewnętrzne źródło ataków rankingowych.
- **Bramki poziomów**: PvP od **2 lvl** (panel z kłódką i komunikatem, serwer 409 „odblokowują się na 2. poziomie"), Lochy od **3 lvl** (payload `locked/reqLevel=3`, serwer 409 na wejście/walkę). **Lochy nie mają własnego wyboru taktyki** — walczą sekwencją z zapisanej taktyki PvP (`combat.style_seq`); payload `seq` jest ignorowany (zgodność starych klientów).
- **Klasa postaci obowiązkowa**: kreator postaci wymusza wybór Bokser/Obrońca/Szybki (radio `required` + walidacja submit + jasny hint „jednorazowa i nieodwracalna"); API akceptuje `null` wyłącznie dla zgodności (stare zapisy → 10/10/10/10/10 i klasa z dominanty w walce).
- Testy: `tests/test_tactics.py` (nowy, 3), pełny pytest **175 PASS**, bateria E2E **28/28 PASS** (test-online: dialog taktyki + PvP od 2 lvl + ranking jako przeciwnicy + lab bez sparingu; test-dungeon: seed XP→lvl3 + kreator taktyki przy 1. walce + `[data-dungeon-fight]` bez wartości; test-combat-motion: PvP na seedach + lab; wszystkie kreacje postaci w E2E klikają klasę). Health **0.41.0**.

## 0.40 — Wizytówki firm, kongestia kolejowa, sesja foto mapy

- **Wizytówki firm**: `/players` dokleja `biz` (poziomy: courier zawsze, cafe/studio gdy kupione) — **wyłącznie graczom online** (offline = `null`, spójnie z dzielnicą z 0.37). Kafel firmy na mapie dostaje **⭐×N** (N = online właściciele), a klik → dialog z listą kart: nick, poziom, poziom firmy, dzielnica, 🟢 i przycisk **„Wyślij DM"** (dataset `data-dm-pid` na poziomie document → `GameApp.mapOpenDm`; osobny atrybut, żeby nie kolidować z dymkami `.content`).
- **Kongestia kolejowa**: `/players` dokleja `origin` (dzielnica startowa podróży, tylko online). Klient liczy BFS-em (ta sama funkcja `mapRoute`) obciążenie każdej krawędzi liczbą graczy w drodze → szyna dostaje **złoty kolor, szerokość 3+N×1,3 (cap) i tooltip „Ruch kolejowy: N w drodze"**. Odświeżanie z cyklem presence (45 s / wejście na mapę) — świadomie bez realtime; trasy pojedynczych graczy nie są nigdzie wypisywane (tylko zagregowana szerokość).
- **Sesja foto**: przycisk 📸 w panelu mapy → render **canvas 1200×800** (szyny, 8 węzłów ze stanem: zamknięte z Erą, Twoja dzielnica z aureolą „TY", cel ⛳) + pasek statystyk (nick, poziom, kasa, XP, Era, sezon) → **PNG do pobrania** (`city-empire-mapa.png`). Zero uploadu, zero serwera — czysty klient; kopia dataURL w `window.__lastPhoto` (dla testów).
- Serwer: tylko wzbogacenie `/players` (`biz`, `origin` — oba online-only) + health 0.40.0; zero nowych zasad. Testy: `test_presence.py` +1 (zakup firmy przez świat testowy: podróż→settle→poziom 2→kasa, `biz`, `origin` d2→d3, offline=null), `test-map.cjs` +wizytówka/kongestia/foto.
- Lekcje: (1) kolejny eksport z IIFE — `GameApp.mapLoadPlayers` obok `mapOpenDm` (stały wzorzec); (2) Playwright uznaje pionowe linie SVG za „niewidoczne" (zerowy bbox) — czekać na `state:'attached'`.

## 0.39 — Skrzynka DM, kafelki hubów na mapie, dźwięki podróży

- **Skrzynka DM w Społeczności**: panel „Wiadomości" — lista wątków (nick, ostatnia wiadomość, godzina, **licznik nieprzeczytanych**), klik → istniejący dialog DM. Serwer: kolumna `read_at` w `dm_messages` (additive ALTER), otwarcie wątku oznacza wiadomości partnera jako przeczytane (GET w `db.tx`), lista wątków zwraca `unread`, a **packet stanu ma globalne `dmUnread`** — plakietka na „Społeczność" w nav sumuje eventy+DM (mechanizm 0.x `updateBadge`). V1 bez osobnej skrzynki unread realtime — licznik żyje z 5-sekundowego polla.
- **Kafelki hubów na mapie**: 📋 **Biuro Zleceń** (Centrum, d3) → widok Kontraktów i ⚔️ **Arena Pojedynków** (Klub Sportowy, d6) → panel PvP (programowy klik `#nav-pvp` — skrót działa z dialogu mapy). Arena w zablokowanej w Erze I dzielnicy renderuje się jako plac budowy — świat pozostaje spójny z bramkami Er.
- **Dźwięki podróży**: WebAudio (zero plików, zero sieci) — dwutonowy motyw przy **odjeździe** (klik „Bus"/„Autostop") i odwrotny przy **przyjeździe** (wykrycie przejścia „w drodze→na miejscu" w `updateTravelOverlay`). Przełącznik 🔊/🔇 w panelu mapy, preferencja w `localStorage` (`ce-sound`), bardzo cicho (gain ~0,045); AudioContext tworzone leniwie po geście.
- **Naprawy architektury (wykute E2E)**: (1) `online-game.js` to jedna IIFE — `mapOpenDm` był prywatny, kliknięcie wątku w skrzynce cicho nic nie robiło → **`GameApp.mapOpenDm` wystawione publicznie**, extras woła przez mostek; (2) `p.click` Playwrighta na przycisku dialogu ma in-flight retry, który dolatuje i **zamyka świeżo otwarty dialog** (flap w baterii) → wszystkie zamknięcia dialogów w testach atomowe (`clickAt`); (3) test-chronicle: czekanie na *widoczność pierwszego elementu* bywa loterią pod obciążeniem → czekamy na wpis `city_done` w DOM.
- Serwer: poza DM (`read_at`, `unread`, `dmUnread`) zero zmian zasad; health 0.39.0. Testy: `tests/test_dm.py` +1 (unread/odczyt/packet), `tests/test-map.cjs` +skrzynka/kafelki/dźwięk, test-chronicle utwardzony.

## 0.38 — DM z mapy, eventy i sezon na mapie, mini-mapa w hubie

- **DM z mapy**: dymki obecności (0.37) są klikalne — klik otwiera dialog z kartą rozmówcy (nick, poziom, 🟢/⚪) i **wątkiem DM**: wysyłka, auto-scroll, poll co 6 s (sam się wyłącza po zamknięciu dialogu). Serwer: tabela `dm_messages` + `GET/POST /worlds/{wid}/dm[/{pid}]` i `GET /worlds/{wid}/dm` (lista wątków). **Filtry jak na czacie** (bez linków/e-maili), mute czatu obowiązuje, blokady symetryczne (409 w obie strony), limity: 3 s między wiadomościami, 30 DM/h, 60 żądań/h na konto. V1 celowo bez skrzynki unread — wejście tylko z mapy.
- **Eventy na mapie**: aktywny event miejski (0.16, `packet.cityEvent`) dostaje żółtą odznakę 📣 na właściwej dzielnicy (mapowanie tekstowej dzielnicy admina na id mapy: Centrum→3, Port→4, biznesowa→5, kreatywna→6, konferencyjna→7, Przedmieścia→8; cel ogólnomiejski XP→3). Klik → dialog z opisem, postępem i czasem. Obok flaga 🏁 sezonu rankingowego (0.34) na Centrum: numer sezonu i dni do końca, klik → dialog z zasadami podsumowania.
- **Mini-mapa w hubie**: widok „Moje Miasto" dostaje panel z miniaturą mapy (szyny + 8 węzłów, 📍 Twoja dzielnica, ⛳ cel w podróży, pulsujący punkt 🚌), podpis „STOISZ W / W DRODZE" i klik → wielka mapa (spójna nawigacja hub→mapa).
- **Serwer**: poza DM zero zmian zasad; eventy i sezon korzystają z istniejących danych w `packet`. **Lekcja z okopów (2×)**: w trybie preview przeglądarka idzie przez kopertę `POST /api/preview/request`, której allowlista regex (GET/POST) musi znać każde NOWE ścieżki — bez wpisu `dm|dm/{pid}` dostajemy 404 „Nieobsługiwana operacja podglądu" (TestClient tego nie łapie, bo idzie wprost w trasy). Druga lekcja: zombie-uvicorn trzymający port testowy sprawia, że „nowy" serwer nie wstaje, a testy strzelają do starego kodu — przed baterią zamykamy porty (kill -9 po pid z `ss`).
- Testy: `tests/test_dm.py` (4: przepływ, self/404, blokady symetryczne + odblokowanie, limity i mute), `tests/test-map.cjs` rozszerzony o mini-mapę, odznaki, DM z odpowiedzią przez poll i admin-event przez `manage.py grant-admin`.

## 0.37 — Żywa mapa: trasa i marker w ruchu, obecność graczy, klikalne budynki, mgła wojny er

- **Żywa mapa**: w trakcie podróży na mapie rysuje się **złota trasa po linii kolejowej** (BFS po krawędziach, animowane przerywanie w kierunku celu), a po trasie jedzie **marker 🚌/🚶** (requestAnimationFrame; pozycja liczona z `travel.started`/`until`, więc dokładna także po wejściu w środek podróży — nowa kolumna `travel_started` na serwerze). Po timerze overlay i ⛳ na dzielnicy-celu działają jak wcześniej.
- **Obecność graczy (presence)**: `GET /players` zwraca teraz `online`, `district` i `traveling` — **dzielnic publikujemy wyłącznie graczom online** (i siebie; offline = `null`), bazując na `sessions.last_seen` (okno 5 min). Mapa pokazuje **dymki 🧍nick** na dzielnicach (max 3 + „+N"), odświeżane co 45 s; własny marker to nadal 📍. Nicki i tak są publiczne w rankingu — presence jest tylko współrzędną, bez śledzenia w czasie rzeczywistym (anti-hunting: wolne odświeżanie, brak historii).
- **Klikalne budynki**: 12 miejsc z 0.36 to teraz **przyciski** — klik otwiera dialog z opisem i skrótem nawigacyjnym (Urząd/Giełda/Redakcja → Moje Miasto; Courier/Café/Studio/Magazyny → Przedsiębiorstwa; Klub/Hipodrom → Klub Sportowy; Hala Targów/Brama Lochu → Postać). Własna firma ma ⭐ i „Zarządzaj", wolne miejsce „Lokuj firmę". Delegacja klików budynków siedzi na `.content`, a nawigacja z dialogu (`data-map-go`) na `document` — dialog żyje poza `.content` (lekcja z 0.36).
- **Mgła wojny er**: zamknięte dzielnice (Era-gating z 0.33) renderują się jako **place budowy** — desenie, wygaszone kolory, 🚧 zamiast realnych firm (detale ukryte do otwarcia), podpis „Plac budowy · Era N". Popup z bramką ery bez zmian; serwer wciąż jedynym autorytetem (409).
- Serwer (poza presence i `travel_started`) bez zmian funkcjonalnych; health 0.37.0. Testy: `tests/test_presence.py` (2), `tests/test-map.cjs` rozszerzony o mgłę, dymki, budynki, trasę i animację — klik testowy uczyniono **atomowym** (query+dispatch w jednym zadaniu JS; 5-sekundowy poll-render potrafił odpiąć węzeł między resolwem a dispatchem — flak wykuty w baterii).

## 0.36 — Wielka Mapa Miasta: przesuwalna mapa 8 dzielnic w klimacie Plemion/Rail Nation

- **Nowa zakładka „Mapa"** (`#nav-map`, widok `map`): wielka mapa miasta (świat 1800×1200 px) w przewijalnym oknie — **pan myszą i palcem** (pointer events, też multi-touch pinch), **zoom kółkiem/przyciskami/pinch** (0,5×–1,8×), przycisk „Wyśrodkuj" (centruje na bieżącej dzielnicy; pierwsze otwarcie też). Odróżnienie kliku od przeciągnięcia progą 6 px (drag nie otwiera popupów).
- **8 dzielnic na mapie** w siatce miejskiej (Port na północy, Centrum w środku, Przedmieścia na południu itd.), połączone **koleją miejską** (linia SVG, klimat Rail Nation). Każdy kafel: numer, ikona, nazwa, status, markery przedsiębiorstw; **bramki Er z 0.33**: zamknięte dzielnice przygaszone z 🔒 i informacją, w której erze się otworzą; bieżąca dzielnica ma 📍 „Jesteś tutaj", cel podróży ⛳ (kolor zielony).
- **Przedsiębiorstwa na mapie**: City Courier, Corner Café, Studio Forma, Klub Sportowy, Hipodrom, Brama Lochu, Urząd, Giełda i in. — własne firmy oznaczone ⭐ (świecą); dane z `state.ventures`, katalogu i lokacji.
- **Podróż kliknięciem**: popup dzielnicy (dialog) z **🚌 Bus 20 $** i **🚶 Autostop 0 $**; w drodze popup pokazuje cel i kieruje do overlaya; zamknięta dzielnica tłumaczy bramkę ery. Obsługa podróży z mapy siedzi na `document` (dialog żyje poza kontenerem `.content`, więc delegacja `.content` by go nie łapała — pułapka znaleziona sutanną).
- **Serwer bez zmian funkcjonalnych** (health 0.36.0): mapa korzysta wyłącznie z istniejących danych (`travelInfo`, `era`, katalog, stan) i istniejącego `POST /travel` z bramkami ery/409. Stary formularz podróży w „Postać i trening" zostaje (dostępność), a kafel huba „Mapa Świata" prowadzi teraz do nowej zakładki.
- Testy: sutanna `tests/test-map.cjs` (8 dzielnic, 5 zablokowanych w Erze I, ⭐ na własnym przedsiębiorstwie, pan myszą zmienia transform, drag nie klika, popup bramki ery, podróż Bussem z mapy → overlay + ⛳ na celu; zero błędów JS). Poprawiono przy okazji uszkodzony tag `<article class="gear-item">` (regresja edycji 0.35, wyłapana rewizją kodu).

## 0.35 — Statystyki ogólne w grze: 💪🧠⚡❤️🎯 wpływają na ekonomię, podróże i loch

- **Zasada**: bonusy liczą się z **punktów efektywnych powyżej 10** (podstawa + wyposażenie) — postać 10×5 ma dokładnie dotychczasowe wartości (zero kary, zero bonusu); wszystko deterministyczne i liczone na serwerze (klient tylko pokazuje lustra). Capy twarde.
- **💪 Siła**: kontrakty **−0,4%/pkt czasu** (cap 20%, wspólny limit z pojazdem 50%) · pojemność skarbca firmy **+2%/pkt** (cap +40%).
- **🧠 Inteligencja**: praca zdalna na PC **+0,6%/pkt gotówki przy odbiorze** (cap +30%) · koszt rozbudowy firmy **−0,3%/pkt** (cap −15%, komunikat „zaoszczędziła X $").
- **⚡ Refleks**: autostop — **ryzyko nieudanego stopu −0,5 p.p./pkt** (baza 15%, min. 3%; roll ratunkowy po losowaniu) i **czas drogi −1%/pkt** (cap −25%).
- **❤️ Charyzma**: ceny wyposażenia **−0,3%/pkt** (cap −9%; sklep pokazuje stare-ceny przekreślone) i wejściówki treningowe (50 → 46 $ przy capie) · **parking +1 miejsce/20 pkt** (sąsiedzi pozwalają parkować).
- **🎯 Spryt**: bonus wpływów inwestycji dzielnicowych **+0,5%/pkt** (cap +25%; płynie też do wypłat kontraktów przez `invest_bonus`) · **NPC lochu −2% siły/10 pkt** (cap −6%).
- **UI**: nowy panel **„Statystyki w akcji"** w profilu — żywa lista wszystkich bonusów (zero przy 10×5, pełne wartości i capy po treningu); lustra liczb w sklepie (cena), widoku firmy (koszt rozbudowy, pojemność skarbca z adnotacją „Siła +X%") i etykiecie autostopu na mapie.
- Testy: `tests/test_stats.py` (5 scenariuszy: matematyka Siły na kontraktach i cap skarbca via `business_sync`, Inteligencja na PC i rozbudowie, Refleks ratunkowy i czas autostopu baseline-vs-30, Charyzma na sklepie/treningu/parkingu z bramką baseline, Spryt na wpływach (cap) i sile NPC w lochu) + sutanna `test-stats.cjs` (panel baseline→50×5 z capami, lustra 228 $ i 880 $). Naprawiono przy okazji regressję z edycji: `buy` znowu dokłada przedmiot do plecaka (dodany test E2E w sutannie features).

## 0.34 — Sezonowe Podsumowanie i kalendarz Er (domknięcie cyklu)

- **Kalendarz Er na karcie świata**: lista światów (`/api/worlds`) dokleja per-świat `era` z bieżącą erą, dniem cyklu, **następną erą z terminem** („Era 3 (Wielki Biznes) za 6 dni — dzielnice 1–7") oraz **epilogiem** (Era IV/finał). Karta świata pokazuje też linię sezonową: „🏁 Sezon N kończy się za X dni — podsumowanie topki i tytuły kosmetyczne".
- **Spięcie z istniejącymi sezonami** (zero nowego systemu): 28-dniowe sezony rankingowe z 0.12/0.13 (`SEASON_ANCHOR/SEASON_LEN` wyniesione na poziom modułu `features`) są teraz częścią payloadu ery — `era.season = {n, endsAt, daysLeft}` według tego samego zegara; chip Ery na hubie/mapie dopisuje „Sezon N: X dni do podsumowania".
- **Podsumowanie jak działało**: `ensure_seasons` archiwizuje topkę XP (`season_archive`, PK sezon+świat — idempotentnie), emituje `season.end` i przyznaje **tylko kosmetyczne tytuły** (Mistrz/Elita Sezonu, Lider Świata → `character_titles`, zero statystyk i gotówki). Test potwierdza, że Er-y nie naruszyły tej machinerii (archiwum + tytuły po 29 dniach).
- **Payload ery**: `next` (n/label/districts/inDays — sufit dni), `epilog` (Era IV), `season`; strefa czasowa liczenia to UTC-milisekundy serwera.
- Testy: `tests/test_season.py` (3 scenariusze: kalendarz karty świata dni 1→29 z terminami następnych er, spójność `era.season` ze wspólnym zegarem 28-dniowym, nietknięta machineria sezonowa — archiwum, topka, tytuły) + sutanna `tests/test-season.cjs` (karta świata z kalendarzem i sezonem, chip z licznikiem podsumowania, payload `era.next/season`; zero błędów JS).

## 0.33 — System Er Świata: 28-dniowy cykl żywotności (Rail Nation style)

- **Harmonogram** (miasto/city_events.py, liczony od `created_at` świata): **Era I** (dni 1–7, Czas Pionierów) — dzielnice 1–3, firmy najwyżej poziom 2; **Era II** (8–14, Rozwój Przemysłu) — dzielnice 4–5, przepustka na pracę zdalną na PC; **Era III** (15–21, Wielki Biznes) — dzielnice 6–7 (Hipodrom!), pojazdy klasy premium; **Era IV** (22–28+, Metropolia & Epilog) — dzielnica 8, wpis finałowy w Kronice i przygotowanie do sezonowego podsumowania.
- **Logika serwerowa**: kolumna `world_era` w tabeli `worlds` (schema + additive ALTER dla starych baz) przeliczana leniwie przy odczycie stanu — zmiana ery zapisuje **wpis w Kronice Miasta** (kind `era`). Próba podróży poza zakres ery → `409 „Dzielnica niedostępna w obecnej Erze świata."` (travel.py). Bramki ery w `economy.action` (parametr `era`): rozbudowa firmy 2→3 w Erze I blokowana, praca PC dopiero od Ery II (kolejność: mieszkanie → przepustka ery → brama 7 dni), pojazdy premium (`GARAGE.premium`, Bus flotowy) od Ery III.
- **UI**: wskaźnik `🏛️ Era II / IV · Rozwój Przemysłu (Dzień 10/28)` w Hubie „Moje Miasto" (nad kaflami) i w panelu Mapy (także w drodze); zamknięte dzielnice na mapie są wyłączone z selekta z podpowiedzią „· Era III 🔒"; chip pokazuje skrót korzyści ery (dzielnice / cap firm / praca PC / premium).
- **Kluczowe niuanse kompatybilności**: rozliczenia rozbudowy i brama 7-dniowa zachowały stare semantyki (settle w przedziale `from_ < end <= now`; przepustka PC sprawdza erę przed wiekiem, komunikat zawiera „7 dni"); skoki zegara ≥7 dni unieważniają sesję, więc testy przechodzą ery przez przesunięcie `created_at` świata. Zaktualizowano fixture'y testowe (travel/pvp/hub d5+, hipodrom 16 dni, parking bus) — mechanika pozostała bit w bit dla młodych światów.
- Testy: `tests/test_eras.py` (4 scenariusze: harmonogram dni 1→32 z automatycznymi przejściami + kolumna `world_era` + kronika, blokady podróży w 4 erach z dokładnym komunikatem 409, cap firm poziom 2 w Erze I → otwarcie w II, przepustka PC i pojazdy premium w II/III) + asercja chipa w sutannie `test-hub.cjs`; świat w sutannie wyścigów postarzany do Ery III (hipodrom d6).

## 0.32 — Ewolucje I stopnia: pasywki klasowe od 10 poziomu

- **Katalog** (`combat.EVOLUTIONS`): **Bokser** → 👑 Mistrz Ringu („Rytm": każdy celny cios zwiększa potencjał następnego o +5%, kumuluje się w walce) albo 👊 Żelazna Pięść („Nokaut": ciosy mocne +15%, w zderzeniu mocnych przełama blok — bez redukcji 20%); **Obrońca** → 🧱 Murarz Ringu („Garda": w zderzeniach fast-fast/heavy-heavy −20% otrzymywanych obrażeń) albo ⚔️ Żelazny Strażnik („Riposta": kontratak po udanym uniku 40% → 75% szybkiego ciosu); **Szybki** → ⚡ Błyskawica („Kontra z Impetem": po udanym uniku następny celny cios ×1,25) albo 👤 Nokaut Fantom („Nieuchwytny": ×0,9 otrzymywanych obrażeń, udany unik leczy +15 HP do limitu).
- **Endpoint** `POST /api/worlds/{wid}/character/evolve` `{evolution_code}` (features.py): walidacje — poprawny kod i zgodność z `class_type` (422), **poziom ≥ 10** (409, komunikat z aktualnym poziomem), **jednorazowość** (`class_evolution` 1→2 + `state_json.evolutionCode`; drugi wybór = 409). Limit 10/h, audit `character.evolve`.
- **Silnik** `combat.simultaneous(...,a_evo,d_evo)` (raport 0.5-evo1): pasywki wpięte w istniejące punkty potencjału/zderzeń/kontrataków — deterministycznie, bez RNG; baseline bez ewolucji **bit w bit jak 0.28** (potwierdzone regresją). Pasywki płyną przez PvP (obie strony) i Loch (tylko gracz). Uwaga semantyczna: „35% szans na darmowy kontratak" (Riposta) odwzorowano deterministycznie jako +35 p.p. do siły kontrataku, a „+10% szansy na unik" (Nieuchwytny) jako globalną redukcję otrzymywanych obrażeń ×0,9 — silnik 0.28 nie rzuca kostkami.
- **UI**: od 10 poziomu karta postaci pokazuje baner „DOSTĘPNA EWOLUCJA KLASOWA!" z dwiema kartami specjalizacji (ikona, nazwa, pasywka, efekt); wybór jednym kliknięciem (obsługa „klik bez wyboru" = toast), po wyborze linia klasy pokazuje 👑/🧱/⚡ z nazwą pasywki, baner znika. Linia klasy przestała pokazywać mylące „Ewolucja I" przed wyborem.
- Testy: `tests/test_evolutions.py` (10 scenariuszy: 6 pasywek liczonych w silniku baseline-vs-ewolucja, ignorowanie nieznanych kodów, brama 10 poziomu, jednorazowość, zgodność klasy, przepływ przez PvP i Loch) + sutanna `tests/test-evolutions.cjs` (baner od 10 poziomu, 2 karty, wybór Riposty, zniknięcie banera, linia klasy; 0 błędów JS). Zaktualizowano `tests/test-classes.cjs` do nowej semantyki linii klasy.

## 0.31 — Lochy: wyprawa spod Bramy Lochu, 10 pięter vs NPC, unikatowe przedmioty

- **Wejście**: lokacja `brama-lochow` (0.30) staje się bramą Lochu — walka wymaga przejścia z profilu przyciskiem „Przejdź do: Brama Lochu"; bramki: lokacja, brak podróży (0.25), progres < 100%.
- **10 pięter**: od Szczura z Kanałów po Władcę Lochu — każde piętro to jedna walka silnikiem symultanicznym PvP (0.28) vs NPC o rosnących statystykach i własnej klasie (Bokser/Obrońca/Szybki z pasywkami). Gracz wybiera taktykę 3-zagrań (Agresywna/Zrównoważona/Defensywna); wygrana = +10% `dungeon_progress` (0–100%), **gotówka 30+30·piętro $ i XP z gry** (60 $/12 XP za piętro 1 → 330 $/48 XP za piętro 10); porażka kosztuje wyłącznie 8 energii. Zero Elo/rankingu, zero realnych pieniędzy; limit 30 walk/h, audit `dungeon.floor`.
- **Unikatowe przedmioty** (jednorazowe na postać, `E.DUNGEON_ITEMS`): piętro 3 → **Buty Cienia** (+2 Refleks, +1 Spryt), piętro 6 → **Rękawice Lochu** (+2 Siła, +1 Spryt), piętro 10 → **Korona Władcy Lochu** (+2 Siła, +2 Int, +2 Charyzma). Wpadają do plecaka, zakładają się zwykłym „Załóż"; sklep pokazuje je z plakietką „Skarb Lochu 💎" bez możliwości zakupu (serwer odrzuca 409). Statystyki liczą się w `E.effective` i we wszystkich walkach.
- **UI**: nowy panel „Brama Lochu" w profilu — pasek progresu 0–100%, następne piętro z nazwą i klasą NPC, trzy przyciski taktyki, lista zdobionych unikatów; wynik walki w modalu (rundy, HP po walce, loot) + odświeżenie stanu.
- Testy: `tests/test_dungeon.py` (5 scenariuszy: bramki lokacji/podróży/sekwencji, wygrana→progres→nagrody→loot jednorazowy, porażka kosztuje tylko energię, unikaty dają statystyki i są niekupowalne, katalog 15 itemów i nietknięty ranking) oraz sutanna `tests/test-classes.cjs`/`test-dungeon.cjs` (pełny przelot: CTA lokacji, walka, dialog, pasek 10%).

## 0.30 — Klasy i Baza: wybór klasy przy tworzeniu postaci, lokacje, bezpieczna migracja

- **Migracja additive (bezpieczna)**: tabela `characters` dostaje 4 kolumny przez warunek `PRAGMA table_info` + `ALTER TABLE ADD COLUMN` (ten sam wzorzec co konta): `class_type` (NULL = postać starsza, klasa wyliczana z dominanty), `class_evolution` (default 1), `current_location` (default `'ulica'`), `dungeon_progress` (default 0). Stare bazy i stare wiersze przechodzą bez ryzyka — testowane na legacy DB bez nowych kolumn.
- **Wybór klasy przy tworzeniu**: `POST /api/worlds/{wid}/character` przyjmuje `class_type` (bokser/obronca/szybki; inna wartość = 422). Statystyki startowe (każda klasa łącznie 50 pkt): **Bokser** [Siła 14, Int 8, Refleks 10, Charyzma 10, Spryt 8], **Obrońca** [8, 14, 8, 12, 8], **Szybki** [8, 8, 14, 8, 12]. Kreator (dialog „Nowa postać") pokazuje 3 karty z rozkładem i pasywką; **brak wyboru = równe 10/10/10/10/10** (pełna kompatybilność z istniejącymi flow i testami).
- **Jedna klasa w PvP**: wybrana klasa zastępuje wyliczanie z dominanty — `combat.pvp_class(stats,cls)` i `combat.simultaneous(...,a_cls,d_cls)` dostają klasę wprost (lista celów 0.28 pokazuje klasę wybraną, silnik stosuje pasywki: Bokser mocniejszy cios, Obrońca kontratak po uniku, Szybki inicjatywa +3). Postacie bez `class_type` walczyją jak dotychczas.
- **Lokacje postaci**: `current_location` to własne pojęcie (ulica/silownia/klub/targ/brama-lochow), niezależne od dzielnic 0.25; `POST /api/worlds/{wid}/location` (limit 60/h, audit `location.move`, 422 dla nieznanej). Profil pokazuje klasę, ewolucję, lokację i postęp lochu; `dungeon_progress` czeka na przyszłe mechaniki.
- **Podłoga statystyk silnika UI** obniżona z 10 do 5 (klasy startują od 8; krzywe logarytmiczne `profile()` pozostają poprawne); walidacja 422 na akcjach bez zmian.
- Testy: `tests/test_classes.py` (5 scenariuszy: migracja legacy, statystyki/payload 3 klas + 422, kompatybilność bez klasy, ruch po lokacjach, PvP z klasami wybranymi — targets + silnik + atak E2E) i sutanna `tests/test-classes.cjs` (3 karty w kreatorze bez defaultu, wybór Szybkiego, 8/8/14/8/12, linia klasy w profilu; zero błędów JS).

## 0.29 — Hub „Moje Miasto", pasek powrotu, overlay podróży (Przyspiesz = VIP) i czat w dymkach

- **Hub „Moje Miasto"**: widok miasta to teraz siatka 6 interaktywnych kafli (Moje Miasto · Przedsiębiorstwa · Rezydencja & Garaż · Klub Sportowy & Wyścigi Konne · Arena PvP & Wyzwania · Mapa Świata/Podróże) z podświetleniem bieżącego miejsca i dopiskiem „· W DRODZE" na kafli mapy podczas podróży. Kafle prowadzą do tych samych widoków co menu boczne (delegacja `[data-hub]`).
- **Pasek powrotu**: w każdym widoku szczegółowym i panelu zewnętrznym (sklep, PvP, ranking, administracja) na górze pojawia się `⬅ Powrót do: Moje Miasto` — jeden klik wraca do huba (sekcja areny ma go na stałe w szablonie).
- **Overlay podróży**: podczas podróży (autobus/autostop/auto, 0.25) u góry ekranu lepi się pasek „W drodze do: [Dzielnica]… Pozostało: MM:SS" z animowanym paskiem; dla posiadaczy **VIP** (`state_json.vipUntil` ze sklepu projektowego) aktywny jest przycisk **⚡ Przyspiesz** → `POST /api/worlds/{wid}/travel/speedup` skraca pozostały czas o połowę (min. 1 s; kolejne użycia działają na ½ z ½; limit 20/h; audit `travel.speedup`). Bez VIP: czytelny komunikat 403 o funkcji VIP. Zero nacisku czasowego — overlay tylko informuje.
- **Czat w dymkach**: wiadomości czatu (świat i organizacji) renderowane jako dymki — **własne po prawej ze złotym gradientem**, **inne po lewej na szarym** z nickiem i **skrótem organizacji** (`org_tag` dokleja serwer: tag z `organizations` po członkostwie, fallback `tag` założyciela dla lidera).
- Testy: `tests/test_hub_ui.py` (bramka VIP speedup: 409 poza podróżą → 403 bez VIP → skrócenie czasu i drugi speedup; `org_tag` w czacie dla członka i lidera) oraz sutanna `tests/test-hub.cjs` (6 kafli, nawigacja kaflami i powroty, overlay z MM:SS bez przycisku VIP dla zwykłego gracza, własny dymek czatu; zero błędów JS).

## 0.28 — Wyzwania PvP 2.0: lista celów, ocena siły i atak 3-slotowy

- **Lista celów** `GET /api/worlds/{wid}/pvp/targets?district=N` (bez parametru = „ogólna arena”): aktywni mieszkańcy świata (limit 20 wg ratingu) z nickiem, poziomem, **klasą** (Bokser/Obrońca/Szybki z dominanty statystyk), **szacunkowym ratingiem Elo** (zaokrąglonym do 10) i wyposażoną skórką. **Dokładne statystyki nie opuszczają serwera** — ocena ryzyka należy do gracza.
- **Atak bezpośredni** `POST /pvp/attack/{target_id}` z sekwencją 3 akcji (`unik`, `mocny_cios`, `szybki_cios` + aliasy PL). Obrońca walczy wg **własnego zapisanego szablonu taktycznego** (`POST /pvp/defense`, domyślnie szybki-unik-mocny), więc walka rozstrzyga się natychmiast. Silnik symultaniczny (`combat.simultaneous`, wersja raportu 0.4-pvp2): kolejność w rundzie wg **Refleksu** (Szybki +3), pasywki klasowe (Bokser mocniejszy cios, Szybki inicjatywa, Obrońca kontruje po skutecznym uniku), HP z kondycji (Charyzmy); unik anuluje cios przeciwnika.
- **Rozliczenie**: wspólny rankingowy limit **5 walk/dobę** (ranked_usage, obie strony), aktualizacja **Elo** (K=24, jak klasyczne wyzwania) i liczników wins/losses, pełny **raport rundowy JSON** zapisany w nowej tabeli `pvp_battles` (pod odtworzenie animacji 0.7.1) oraz **zdarzenie w Centrum Zdarzeń obrońcy** (0.12, rodzaj `pvp_attacked` z wynikiem i zmianą ratingu). Bramki: zakaz ataku samego siebie, ataku w drodze i celu w drodze (integracja z 0.25); blokady kontaktów respektowane.
- Testy: `tests/test_pvp_active.py` (6 scenariuszy: determinizm i pasywki klas w silniku, lista celów bez statystyk z klasami/skórkami/filtram dzielnic, pełny obieg ataku z matematyką Elo ±12 przy ratingach 1000 i zapisami pvp_battles/ranked_usage/zdarzenia, aliasy PL i walidacje 422, limit 5/dobę, bramki podróży).

## 0.27 — Klub Sportowy 2.0: sekcja boksowa i hipodrom (zawody konne)

- **Sekcja boksowa**: ring sparingowy, taktyki i treningi działają jak dotychczas (arena 0.2/0.7) — hipodrom dołączył do tego samego widoku Klubu Sportowego jako panel nad ringiem (podczas walki panel ustępuje miejsca animacji).
- **Hipodrom (Dzielnica Kreatywna, dzielnica 6, od 5 poziomu postaci)**: konie z parametrami Szybkość/Wytrzymałość (Mustang 800 $, Pełnej krwi 3000 $, Czempion 8000 $ — progi poziomu 5/6/8). Wynik wyścigu wyliczany deterministycznie z **charyzmy dżokeja (kondycja), sprytu (tor jazdy) i statystyk konia** (wagi 3×S, 2,5×W, 2×Ch, 1,5×Sp) z seedowanym rozstrojeniem ±12% — pełna powtarzalność z seeda wyścigu.
- **Zawody**: wyścig z dżokejami NPC (trzy Starty) oraz **otwarte pojedynki między graczami** (autor otwiera, rywal dołącza, trzeci start NPC) — wpisowe 50 $ wirtualnych zasila pulę dzieloną **60/30/10 %** dla miejsc 1–3. Odwołanie otwartego wyścigu zwraca wpisowe. To **zawody umiejętności, nie zakłady**: bez obstawiania, kursów i realnych pieniędzy (dev-sklep nie ma żadnego udziału — testowane).
- **Puchar (1. miejsce)** → wpis w Kronice Miasta (0.17, rodzaj `hipodrom`) i **+25 prestiżu organizacji** dżokeja (pseudodzielnica „Hipodrom”, poza wpływami terytorialnymi 0.11). Brama: poziom 5, pobyt w dzielnicy 6 (integracja z podróżami 0.25), własny koń, zakaz startu w drodze.
- Testy: `tests/test_horse_racing.py` (6 scenariuszy: scoring/split 60-30-10, bramy i pełna matematyka gotówki, puchar→kronika→prestiż org ×2, cykl pojedynku open/join/cancel z rozliczeniem obu graczy, **zero śladu realnych pieniędzy** — `shop_purchases` puste i brak zdarzeń `shop.*`, payload z listą otwartych wyścigów) oraz sutanna `tests/test-racing.cjs` (UI: panel hipodromu, zakup Czempiona, dojazd na tor, wyścig NPC z tabelą 3 miejsc; brak błędów JS).

## 0.26 — Rezydencja 2.0: regeneracja, garaż i praca zdalna

- **Warianty mieszkań z miejscami parkingowymi** (`RESIDENCES` + pole `slots`): Kawalerka na Przedmieściach (0 miejsc — auto w użyciu pod chmurką), Apartament z Miejscem Parkingowym (1 miejsce), Willa z Garażem Podziemnym (3 miejsca, nadal najwyższa regeneracja 8/h i odpoczynek +25%). Kupno pojazdu sprawdza pojemność „1 auto w użyciu + miejsca rezydencji” (409 z komunikatem, gdy brak); posiadane floty sprzed 0.26 zostają (bez eksmisji), rozbudowa rezydencji działa jak dotychczas.
- **Trening domowy** (`home_train`): +1 punkt statystyki za samą energię (12), bez opłat trenerskich klubu, ale wolniej (10 min vs 5). Wymaga własnego mieszkania; wspólna kolejka treningów i odbiór jak w klubie.
- **Praca zdalna na PC** (`remote_work`, „Zlecenie specjalne”): stała stawka 150 $ + 25 XP za sesję 15 min (tempo świata skaluje), koszt 10 energii, jedno aktywne naraz, nie zużywa auta. **Brama 7 dni**: dostępna, gdy wiek postaci **albo** świata wynosi co najmniej 7 dni (`created_at`); wymaga mieszkania; w drodze niedostępna (jak każda praca stacjonarna).
- **Dystynkcja dnia (0.23) rozszerzona**: odbiór pełnego wypoczynku (`rest_claim`) i odebranie pracy zdalnej kwalifikują dnia — nowe znaki „Wypoczynek dnia” i „Praca na PC dnia”; liczniki ekonomii dnia (0.24) także je chwytają.
- Testy: `tests/test_residence_v2.py` (6 scenariuszy: brama 7 dni obiema ścieżkami, pełny obieg pracy zdalnej ze stałą stawką i znakiem dnia, trening domowy bez opłat, parkowanie 0/1/3 miejsc wraz z awansami mieszkań, regeneracja 12/h i bonus willi ×1,25, katalog z `slots`) — plus 21/21 sutann przeglądarkowych.

## 0.25 — Mapa 8 dzielnic i podróże (firmy w Strefie Przemysłowej)

- **8 dzielnic miasta**: 1 Moje Miasto (start), 2 Strefa Przemysłowa (firmy), 3 Centrum, 4 Port, 5 Dzielnica Biznesowa, 6 Dzielnica Kreatywna, 7 Centrum Konferencyjne, 8 Przedmieścia Wschodnie. Stan postaci: additive kolumny `current_district` (domyślnie 1), `travel_destination`, `travel_until`, `travel_mode` + nowa tabela `vehicles(id, character_id, type, condition, speed_bonus)` (rejestr pojazdów; konta sprzed 0.25 dostają swój garaż dopisany przy pierwszym użyciu).
- **Podróże** `POST /api/worlds/{wid}/travel` (target 1–8): **bus** 20 $, 5 min × odległość / tempo świata (min. 60 s); **autostop** 0 $, losowe 3–10 min / tempo, 15% szansy na −10 energii; **własne auto** wymaga sprawnego pojazdu z rejestru (`condition > 0`), czas = 20% czasu busa (min. 1 s). `POST /travel/arrive` rozlicza przyjazd; odczyt stanu dociąga zakończone podróże leniwie (lazy settle). W trakcie drogi **blokada pracy stacjonarnej**: kontrakty (start i odbiór), treningi, zlecenie dnia → 409 z czytelnym komunikatem. Rate limit 20/h.
- **Separacja biznesów**: firmy logowo działają w **dzielnicy 2** — kupno nowej firmy, odbiór dochodu i rozbudowa (buy_business/collect/upgrade) wymagają pobytu na miejscu (409 z komunikatem „Strefa Przemysłowa”). Widok firm dostaje czytelny baner z drogą do dzielnicy 2, a panel „Twoja historia” — formularz podróży (cel + transport, odliczanie w drodze, przycisk „Ogłoś przyjazd”).
- Testy: `tests/test_travel.py` (10 scenariuszy: opłata i czas busa, tempo świata, autostop z ryzykiem energii, auto z rejestrem i serwisem, walidacje 422, podwójna podróż 409, bramka dzielnicy 2, blokady w drodze + działanie po przyjeździe, lazy settle, 401/404); legacy `test_api`/`test_features`/`test-online.cjs`/`test-features.cjs` dostały seed `current_district=2` tam, gdzie scenariusze dotykają firm.

## 0.24 — Ekonomia w liczbach: dzienne wykresy (gracz i administrator)

- **Agregaty dnia liczone w transakcjach czynów** (zero estymacji): ukończony kontrakt (z deltą gotówki i XP), ukończony trening, odbiór dochodu, wpłata do funduszu organizacji, inwestycja dzielnicowa → `char_daily` (per postać) i `world_daily` (per świat) — tabele additive z PRIMARY KEY (obiekt, doba UTC). Zakupy dev-sklepu na świecie dopisują centy do `world_daily.shop_cents` (VIP kontowy — poza licznikiem świata).
- **Wykres 14 dni (SVG inline, bez bibliotek)** w panelu „Twoja historia” (Postać): słupki czynów (złoto) i gotówki (zieleń) z podpowiedziami dnia/XP; pusty stan ma czytelną zachętę. **Panel administratora → Podsumowanie świata** dostaje ten sam wykres (czyny + dev-sklep w zł).
- Payload stanu: `activity` (do 14 wierszy); podsumowanie świata: `daily` (do 14 wierszy). Odczyt czysty, okno nigdy nie przekracza dwóch tygodni.
- Testy: `tests/test_econstats.py` (pusty start, fund→kontrakt z deltą gotówki/XP, spójność gracz↔świat, centy sklepu tylko po stronie świata, podział dób, cap 14 wierszy, izolacja światów) oraz `tests/test-econstats.cjs` (UI: pusta zachęta → pierwszy słupek po wpłacie; wykres w dialogu admina dla tej samej doby; brak błędów JS, brak przepełnienia na 390 px).

## 0.23 — Dystynkcja dnia (codzienny zaszczyt)

- **Raz na dobę UTC** postać może odebrać **dystynkcję dnia** — czysto kosmetyczny zaszczyt za zapracowany czyn. Dopuszczne czynności: **ukończony kontrakt** (odbiór nagrody), **ukończony trening**, **odbiór dochodu z firmy**, **wpłata do funduszu organizacji**, **inwestycja dzielnicowa** (własna albo organizacji). Znaczek dnia nosi nazwę ostatniego czynu (np. „Wsparcie organizacji”).
- **Zero presji**: bez serii/streaków (nie da się „zepsuć”), bez liczników czasowych, bez zakupów, bez losowości, zero statystyk i gotówki. Licznik „łącznie” tylko rośnie; każdy dzień zaczyna się czysto.
- Blok w panelu **„Twoja historia”** (Postać): trzy stany — informacja o zasadach / „gotowa do odbioru: Za: ⟨czyn⟩” z przyciskiem / chip „Dystynkcja dnia · ⟨czyn⟩” z licznikiem.
- Mechanika serwerowa: `daily_actions` (znak czynu dnia, upsert — liczy się najnowszy) + `daily_distinctions` (UNIQUE postać+doba; tabele additive). Znacznik powstaje **w tej samej transakcji co czyn** (hook w `/actions` dla claim_contract/claim_training/collect oraz w wpłacie i inwestycji organizacji); `POST /worlds/{wid}/distinction/claim` — 409 bez czynu, 409 przy drugim odbiorze tego samego dnia; stan świata dostaje `distinction={eligible,claimed,pending,count}`.
- Testy: `tests/test_daily_distinction.py` (409 bez czynu, cykl fund→claim→409, reset doby, kontrakt i trening jako czyny przez prawdziwe `/actions`, izolacja światów, unikalność doby w bazie) oraz `tests/test-distinction.cjs` (UI: stan początkowy → wpłata → odbiór → chip z licznikiem; brak błędów JS, brak przepełnienia na 390 px).

## 0.22 — Podsumowanie świata dla administratora + plan real-store

- **Przycisk „Podsumowanie” przy każdym świecie w panelu administracyjnym** — dialog tylko-do-odczytu: mieszkańcy (liczba + suma XP miasta), najnowszy mieszkaniec, cel miasta (aktywny z postępem albo ostatni los), organizacje (liczba + top 5 z prestiżem), kontrakty org (aktywne/zaliczone/przepadłe), kronika i aktywne ogłoszenia (liczby), dev-sklep per świat (zakupy pozorowane + suma w zł; VIP jest kontowy — poza licznikiem świata), mieszkańcy z VIP, top 5 graczy.
- Endpoint `GET /api/admin/worlds/{wid}/summary` — wyłącznie admin (403 dla gracza, 401 bez sesji, 404 dla nieznanego świata i organizacji z obcego świata nie dotyczy — liczy wyłącznie dane danego świata); trasa na allowliście GET transportu podglądowego.
- **`REAL-STORE.md`** — nowy dokument planu integracji sklepów (Play Billing / Apple IAP): mapowanie SKU, architektura walidacji paragonów serwerowo, checklisty Google/Apple/CPC z oznaczeniem co już jest spełnione projektowo (usuwanie konta, moderacja UGC, ceny przed zakupem, domyślnie wyłączone zakupy, zero lootboxów) i co dopiero powstanie; decyzja o starcie świadomie odłożona. Zero kodu płatności.
- Testy: `tests/test_world_summary.py` (pełny obraz świata 1: ludzie, cel, org, kontrakt, kronika, sklep, VIP; pusty świat 2; 403/401/404) oraz `tests/test-adminsummary.cjs` (UI: dialog z podsumowaniem z wiersza świata; gracz nie widzi przycisku i dostaje odmowę; brak błędów JS, brak przepełnienia na 390 px).

## 0.21 — Wizytówka organizacji (publiczny profil)

- **Przycisk „Profil” przy każdej organizacji w katalogu Społeczności** — dialog dostępny dla każdego mieszkańca świata (także bez własnej organizacji): nazwa [skrót], opis, lider, data założenia, liczebność (X / 20), prestiż, **wpływy terytorialne**, liczba ukończonych kontraktów oraz **historia organizacji z kroniki** (założenie, zaliczone i przepadłe cele — do 6 najnowszych wpisów).
- Endpoint `GET /api/worlds/{wid}/organizations/{oid}` — tylko odczyt, scoping per świat (organizacja z innego świata → 404), zero statystyk i gotówki; czysto opisowa (zgodnie z linią reputacyjną gry).
- Testy: `tests/test_org_profile.py` (pełny obraz po zaliczonym kontrakcie: skład, prestiż, wpływy, historia org_done→org_founded, brak sesji → 401, złe id / obcy świat → 404) oraz `tests/test-orgprofile.cjs` (UI: sąsiad otwiera wizytówkę z katalogu i widzi pełny dialog z historią; brak błędów JS, brak przepełnienia na 390 px).

## 0.20 — Balans/QoL: czysta konsola, „Pokaż hasło”, osłona Energiapaka, „Twoja historia”

- **Czysta konsola przy rejestracji**: atrybut `pattern` loginu był niepoprawny pod nowym parserem Chrome (flaga `v` wymaga escapowania `-` w klasie znaków; dodatkowo w szablonie JS backslash wymaga podwojenia, inaczej znika w DOM). Console error zniknął — testowany w przeglądarce.
- **„Pokaż hasło”** w oknie logowania i rejestracji (hasło + powtórzenie): przełącznik typu pola, dostępny z klawiatury.
- **Osłona Energiapaka (przejrzystość opłat, duch CPC)**: przy ≥140/240 energii karta ostrzega „część zakupu przepadnie”; przy pełnej (240) przycisk jest zablokowany („Pełna energia”) — zakup, który by się zmarnował, nie dojdzie do skutku. Stan 120 → 150 → 240 przetestowany w UI.
- **Panel „Twoja historia” w Postaci**: kontrakty ukończone, treningi, pojedynki (wygrane, rating) oraz **chipy odznak** („Pionier: …”, tytuły sezonowe) — dotąd widoczne tylko w rankingu. Payload stanu dostaje `titles` (do 12 najnowszych, `{code,label}`); czysto opisowe, zero statystyk.
- Testy: `tests/test_profile_titles.py` (puste domyślnie, odznaka Pioniera po wspólnym celu, limit 12 najnowszych) oraz `tests/test-qol.cjs` (czysta konsola, przełącznik haseł, trzy stany Energiapaka, panel historii z odznaką zasianą do QA-bazy; brak błędów JS, brak przepełnienia na 390 px).

## 0.19 — Zgoda opiekuna (RODO art. 8) + projekty sklepów

- **Ścieżka „mam mniej niż 16 lat” w bramce zakupów**: włączenie wydatków wymaga najpierw zapisanej zgody opiekuna (serwer: 422 bez zgody). Formularz zgody: imię i nazwisko opiekuna (3–60 znaków) + **tygodniowy limit wydatków** (presety 5/10/20/50 zł).
- **Limit tygodniowy egzekwowany serwerowo** przy każdym zakupie — tydzień liczony od poniedziałku 00:00 UTC, wydatki w groszach (`shop_purchases.cents`, migracja additive); nadwyżka → 409 z jasnym komunikatem. Energiapak 4,99 zł mieści się w limicie 5 zł; kolejny zakup już nie.
- **Cofnięcie zgody opiekuna** (dialog potwierdzenia w sklepie) natychmiast wyłącza zakupy na koncie; jedna aktywna zgoda na konto (częściowy indeks UNIQUE); ślady w dzienniku: `shop.guardian_consent`, `shop.guardian_revoke`.
- Ścieżka 16+ bez zmian (jedno oświadczenie). Kasa pozorowana — **nadal zero prawdziwych płatności**; rozdział „Projekty sklepów” (Play Billing / Apple IAP / CPC) to wyłącznie plan w `MONETYZACJA.md`.
- Testy: `tests/test_guardian.py` (blokada <16 bez zgody, walidacje formularza, limit tygodniowy + reset tygodnia, revokacja zamyka zakupy, ścieżka 16+ bez regresji) oraz `tests/test-guardian.cjs` (UI: pole minor odsłania formularz zgody, zakup w limicie, 409 limitu w toaście, cofnięcie dialogiem, ścieżka dorosłego jednym kliknięciem; brak błędów JS, brak przepełnienia na 390 px).

## 0.18 — Tablica ogłoszeń świata

- **Panel „Tablica ogłoszeń” w Społeczności** (nad centrum zdarzeń): publiczna lista komunikatów administracji z chipem zasięgu (GLOBALNE / TEN ŚWIAT) i datą. Gracze widzą do 10 najnowszych ogłoszeń z ostatnich 7 dni; świeża treść przy każdym otwarciu Społeczności (ogłoszenia jadą też w odpowiedzi `/community`).
- **Administrator publikuje z panelu** („Nowe ogłoszenie”): treść 3–500 znaków, zasięg „wszystkie światy” albo konkretny świat (404 dla nieznanego świata). Baner nad grą nadal pokazuje najnowsze ogłoszenie z przyciskiem OK (bez zmian w tej ścieżce).
- **Nowość: usuwanie ogłoszeń** — przycisk „Usuń” w panelu administracyjnym (lista 20 najnowszych z nazwą świata i datą; POST `/api/admin/notices/{id}/delete`, 404 bez wpisu, 403 dla gracza, ślad w dzienniku `notice.delete`). Cap 20 wpisów w tabeli bez zmian.
- Testy: `tests/test_notice_board.py` (zasięg per świat, okno 7 dni, walidacje 422/404/403, limit 20, payload społeczności, dziennik) oraz `tests/test-board.cjs` (UI: publikacja z panelu dla świata i globalnie, baner + dismiss, chipy zasięgu, usuwanie i aktualizacja obu widoków; brak błędów JS, brak przepełnienia na 390 px).

## 0.17 — Kronika miasta: historia wspólnych chwil

- **Panel „Kronika miasta” w Miasto** (pod kartą celu): publiczna, tylko-do-czytania historia świata. Zapisują się wyłącznie momenty „międzyludzkie”: założenie organizacji, ogłoszenie wspólnego wyzwania miasta (0.16) oraz jego los — zaliczone (chip „ZALICZONE”), przepadłe, anulowane — a także kontrakt organizacji (0.15) zaliczony lub przepadły. Stan gry dostaje 15 najnowszych wpisów, baza trzyma 300 na świat (auto-przycinanie).
- **Wpis powstaje w tej samej transakcji co fakt** — kronika nigdy nie kłamie i nigdy niczego nie zmienia: zero statystyk, gotówki i losowości. Wpisy są per świat (scoping testowany), najnowsze na górze, z chipem rodzaju i datą.
- **Bonus: naprawiony pozostałościowy błąd 0.15** — formularz kontraktu organizacji pokazywał zawsze ukryty wybór dzielnicy; od teraz rodzaj „prestiż w dzielnicy” odsłania wybierak dzielnic (i chowa go z powrotem dla zbiórki). Testowane w UI.
- Nowy moduł `server/chronicle.py` (tabela `chronicle` — migracja additive; hooki w `city_events.py` i `features.py`). Testy: `tests/test_chronicle.py` (pełna historia miasta i organizacji, wpis prestiżowy z dzielnicą, scoping światów, limit 300, kontrakt przepadły) oraz `tests/test-chronicle.cjs` (UI: założenie organizacji → wpis; panel admina → wyzwanie → wpis u gracza i admina; inwestycja zalicza cel → wpis „ZALICZONE” na szczycie; przełączanie dzielnicy w formularzu kontraktu; brak błędów JS, brak przepełnienia na 390 px).

## 0.16 — Eventy miejskie: wspólny cel całego świata

- **Administrator uruchamia event** (panel → „Event miejski”): nazwa, opis, rodzaj celu, czas (24 h – 14 dni). Jeden aktywny event na świat (indeks częściowy). Bez eventów od administratora miasto żyje normalnie — zgodnie z zasadą „admin decyduje, kiedy”.
- **Dwa rodzaje wspólnego celu:** „XP miasta — wszyscy razem” (suma XP mieszkańców; 100–500 000) oraz „Prestiż organizacji w dzielnicy” (100–50 000 $). Postęp liczy się **od bazy z chwila utworzenia** — wcześniejsze XP i inwestycje się nie liczą; uczciwy start dla wszystkich.
- **Karta celu w Miasto**: nazwa, opis, pasek postępu i termin — pierwsza rzecz widoczna po wejściu do miasta. Zaliczenie lub wygaśnięcie rozlicza się leniwie przy odczycie stanu.
- **Nagroda czysto reputacyjna**: odznaka-tytuł **„Pionier: ⟨nazwa eventu⟩”** dla mieszkańców świata w chwili zaliczenia (widoczna jako chip w globalnym rankingu) + zdarzenia w centrum (utworzenie, „zaliczony!”, wygaśnięcie, anulowanie). Zero premii do siły, zero wypłat, zero losowości — test porównuje statystyki przed/po.
- Administrator widzi listę eventów z postępem i może zakończyć aktywny event (z powiadomieniem miasta).
- Nowy moduł `server/city_events.py` (tabela `city_events` — migracja additive). Testy: `tests/test_city_events.py` (przepływ XP i prestiżu, baza od zera, odznaki tylko przy zaliczeniu, wygaśnięcie i anulowanie bez odznak, walidacje i bramy administracyjne) oraz `tests/test-cityevent.cjs` (pełna ścieżka UI: panel admina → formularz → karta w Miasto → inwestycja zalicza cel → odznaka w centrum zdarzeń; brak błędów JS, brak przepełnienia na 390 px).

## 0.15 — Dopracowanie sklepu + kontrakty organizacyjne (wspólne cele)

### Sklep: VIP w HUD, skórki w widoku postaci
- **Chip VIP w HUD** z datą zakończenia („VIP · do 28.10.2026, 20:02") przy nicku; znika automatycznie po upływie okresu.
- **Wybór skórki w widoku postaci** (panel profilu): chipy „Domyślna / Miedź / Złoto / Neon" tylko z posiadanych skórek; zmiana ramy działa od razu, bez przeładowania. Skórki pozostają czysto kosmetyczne.
- Podsumowanie sklepu w stanie gry uzupełnione o `ownedSkins` (dane własnego konta — bez wycieku).

### Kontrakty organizacyjne — wspólne cele ekipy
- **Oficer+ ustawia cel**: „Zbiórka do funduszu" (200–50 000 $) albo „Prestiż w dzielnicy" (100–20 000 $), czas 24 h / 48 h / 7 dni. Jeden aktywny kontrakt na organizację (indeks częściowy w bazie), postęp liczony od bazy z chwili ustawienia — wcześniejsze wpłaty się nie liczą.
- **Postęp na żywo**: pasek z licznikiem w panelu organizacji widoczny dla wszystkich członków; wpłaty do funduszu i inwestycje dzielnicowe automatycznie zaliczają cel.
- **Nagroda czysto reputacyjna**: licznik „Ukończone kontrakty: N" przy organizacji + zdarzenia w centrum (utworzenie, „Cel osiągnięty!", wygaśnięcie, anulowanie). Zero premii do siły, zero wypłat — testy porównują statystyki i gotówkę przed/po.
- Przedawnione cele wygasają leniwie („wygasł bez realizacji"); officer może anulować z potwierdzeniem.
- Testy: `tests/test_org_contracts.py` (przepływ fundusz/prestiż, baza od zera, bramy oficerskie, walidacje, jedno aktywne, anulowanie, leniwe przedawnienie, brak bonusów mocy) oraz `tests/test-orgcontracts.cjs` (pełna ścieżka UI: cel → wpłaty obu członków → pasek → licznik + zdarzenia; brak błędów JS, brak przepełnienia na 390 px).

## 0.14 — Sklep (wersja rozwojowa): ceny w zł, pozorowana kasa, brama opiekuna

- **Bez prawdziwych płatności — zasada twarda.** „Kup” symuluje transakcję (status zamówienia `paid_dev`),
  wszystko z pełnym audytem z ceną. Produkcja: wyłącznie Play Billing / Apple IAP (MONETYZACJA.md §2a).
- **Zakupy domyślnie wyłączone** na każdym koncie; włączenie wymaga oświadczenia „16+ albo zgoda opiekuna”
  (RODO art. 8, dev-stub pełnej ścieżki). Wyłączenie w każdej chwili. Bez kont oznaczonych wiekiem nie
  zbieramy daty urodzenia — stan na oświadczeniu, zgodnie z decyzją 0.14.
- **Oferta wg decyzji (pełna tabela):** VIP 30 dni 19,99 zł / 7 dni 7,99 zł (+25% gotówki z kontraktów na
  wszystkie postacie konta, okresy sumują się), Pakiet startowy 9,99 zł (raz na konto: +5 000 $, zestaw
  Specjalistyczne, 1× natychmiastowy odpoczynek), Energiapak 4,99 zł (+100 energii, klamra 240, limit
  2/dobę UTC), Przyspieszenie zlecenia 2,99 zł (skraca trwające zlecenie o połowę, limit 3/dobę UTC),
  Skórki ramki profilu 3,99–9,99 zł (czysto kosmetyczne). Zero lootboxów, zero presji czasowej, ceny
  w realnej walucie zawsze przed zakupem.
- Zakupy światowe (startowy/energia/przyspieszenie) wymagają aktywnej postaci w świecie; kontowe (VIP,
  skórki) działają globalnie. Nowa postać dziedziczy aktywny VIP.
- Nowy moduł `server/shop.py` (tabele `shop_state`, `shop_purchases`, `shop_usage` — migracje additive),
  panel „Sklep” z banerem dev, historią zamówień i limitem dziennym; VIP/skórki widoczne w HUD i panelu konta.
- Testy: `tests/test_shop.py` (brama i oświadczenie, audyt `paid_dev`, bonus VIP +25% mierzalny na tym
  samym kontrakcie, startowy raz na konto z natychmiastowym odpoczynkiem, limity dobowe i klamra energii,
  skórki kup/zakłoń, podsumowanie stanu bez wycieku historii) oraz `tests/test-shop.cjs` (cała ścieżka
  w UI: baner, ceny, brama z oświadczeniem, VIP + skórka na HUD, limit energii, odmowa przy braku zlecenia).

## 0.13 — Tytuły sezonowe: nagrody czysto reputacyjne

- **Kto dostaje tytuł:** przy leniwej finalizacji zakończonego sezonu — **Mistrz Sezonu** (1. miejsce globalne), **Elita Sezonu** (2–3 globalnie) oraz **Lider Świata ⟨nazwa⟩** dla najlepszego gracza każdego świata niezależnie od wyniku globalnego (jeden gracz może mieć oba — np. mistrz globalny i lider swojego świata).
- **Tylko kosmetyka:** tytuły nic nie zmieniają w rozgrywce — test porównuje statystyki i gotówkę mistrza przed i po nadaniu. W zdarzeniach pojawia się komunikat „Zdobywasz tytuł… (kosmetyka — bez wpływu na siłę)".
- **Gdzie widać:** złote chipy przy nicku w globalnym TOP 50 i w archiwach sezonów oraz wiersz „Tytuły: …" przy „Twojej pozycji globalnej". Tytuły archiwizują się wraz z TOP 10 świata (pole `cid` w archiwum pozwala dociągnąć tytuły w widoku sezonu).
- Nowa tabela `character_titles` (UNIQUE na postać+kod+sezon — nadanie raz na sezon, idempotentne przy wielokrotnych odczytach rankingu). Migracja w 100% additive.
- Testy: `tests/test_season_titles.py` (nadanie dla 6 zakończonych sezonów po skoku zegara, mistrz/2×elita/2×lider świata, publikacja w TOP 50 i archiwum, brak zmian statystyk, idempotencja, żaden tytuł nie sięga sezonu bieżącego).

## 0.12 — Globalny ranking z sezonami + centrum zdarzeń

### Sezony i ranking globalny
- **Sezon = 28-dniowe okno rywalizacji** (kotwica: poniedziałek 2026-01-05 UTC). Punktacja globalna to **XP kariery** — rośnie od kontraktów i treningu, niczego nie kupisz. Postacie, majątek i organizacje **nigdy się nie resetują**; sezony porządkują wyłącznie rywalizację.
- **Panel „Globalny ranking · sezony"** pod tabelą świata (Ranking świata): TOP 50 wszystkich światów (postać, świat, poziom, XP, skrót organizacji), „Twoja pozycja globalna" i chipy sezonów — bieżący plus archiwa.
- **Archiwizacja leniwa**: pierwsze sięgnięcie po ranking po zakończeniu sezonu finalizuje TOP 10 każdego świata do tabeli `season_archive` i wysyła postaciom zdarzenie „Sezon zakończony" z miejscem w świecie. Archiwum sezonu pokazuje połączone TOP 10 wszystkich światów.
- Widoczność publiczna: ranking ujawnia wyłącznie nick, świat, poziom, XP i skrót organizacji (test blokuje wyciek pól prywatnych).

### Centrum zdarzeń (powiadomienia w grze)
- Nowa tabela `game_events` — feed per postać (ostatnie 100, podgląd 30 w UI). Odznaka z liczbą nieprzeczytanych na przycisku „Społeczność" (aktualizowana po każdej akcji i na wejściu).
- Zdarzenia: **podanie do organizacji** (dla lidera i oficerów), **przyjęcie/odrzucenie** (dla kandydata), **zaproszenie**, **dołączenie gościa**, **ogłoszenie organizacji**, **zmiana rangi**, **przejęcie/utrata wpływów** (dla obu organizacji), **koniec sezonu**.
- Panel „Centrum zdarzeń" nad społecznością: nieprzeczytane podświetlone, przycisk „Oznacz wszystkie jako przeczytane". Bez e-maili i powiadomień zewnętrznych — wszystko w grze (RODO-friendly).
- Endpointy: POST `/worlds/{wid}/events/read` ({all:true} lub {ids}); licznik `eventsUnread` w stanie i społeczności. Migracje w 100% additive (2 nowe tabele).
- Testy: `tests/test_events_global.py` (feed zdarzeń wszystkie rodzaje, ranking międzyświatowy, archiwizacja sezonów, brak resetów, brak wycieku pól) oraz `tests/test-events.cjs` (odznaka → wiersz zdarzenia → oznacz przeczytane → zdarzenie przyjęcia u kandydata → panel sezonowy; transport podglądu, brak błędów JS, brak przepełnienia na 390 px).

## 0.11 — Wpływy terytorialne: dzielnice pod flagami organizacji

- **Zasada jednego zdania:** suma inwestycji organizacji w dzielnicy (prestiż z 0.10) decyduje, czyja flaga wisi nad dzielnicą. Wpływy dają wyłącznie rozgłos — nie zmieniają stawek kontraktów, statystyk, ani prywatnych bonusów dzielnicowych (testy blokują próby копiowania do stanu postaci).
- **Przejęcia są zapisywane**: tabela `territory_state` trzyma obecnego posiadacza każdej dzielnicy, a `territory_log` kronikę zmian (kto, co, od kogo, kiedy; ostatnie 8 wpisów widocznych w UI). Remis prestiżu rozstrzyga starsza organizacja (deterministycznie, niższy id).
- **Panel „Wpływy w dzielnicach"** w Społeczności: każdy dystrykt z flagą lidera, sumą prestiżu, datą przejęcia i pozycją własnej organizacji („2. miejsce · 400 $"); niżej „Kronika wpływów" z ostatnimi przejęciami.
- **Chipy flagowe**: organizacja widzi swoje dzielnice przy nazwie („Wpływy: Port"), a katalog pokazuje chipy u organizacji-posiadaczy. Oficer po inwestycji, która przebija prestiż rywala, dostaje toast „Nowe wpływy: [TAG] przejmuje Dzielnicę!".
- Bez nowych endpointów: dane wpływów jadą w	payloadzie społeczności; inwestycja organizacji zwraca `claimed`/`held`. Migracje w 100% additive (dwie nowe tabele).
- Testy: `tests/test_territory.py` (przejęcie + kronika + remis, zero bonusów mocy/kasy, bramy oficerskie i widok obserwatora) oraz `tests/test-territory.cjs` (pełny scenariusz UI: zdobycie Portu, przejęcie przez rywala, chipy po obu stronach, brak błędów JS, brak przepełnienia na 390 px).

## 0.10 — Organizacje 2.0: podania, rangi, fundusz i prestiż

- **Podania kandydatów**: gracz bez organizacji składa podanie (10–200 znaków) do wybranej organizacji prosto z katalogu w Społeczności; limit 5 podań/h, jedno oczekujące na organizację, maksymalnie 20 organizacji na świecie, wygasają po 7 dniach. Lider i oficerowie widzą podania w panelu organizacji i przyjmują/odrzucają je jednym kliknięciem; przyjęcie automatycznie odrzuca pozostałe podania kandydata.
- **Rangi**: Lider / Oficer / Członek. Oficer zaprasza, publikuje ogłoszenia, inwestuje fundusz, rozpatruje podania i usuwa zwykłych członków. Tylko lider mianuje/zbiera officerów, przekazuje przywództwo (stary lider zostaje oficerem) i usuwa kogokolwiek. Odejście ostatniego lidera wymaga wcześniejszego przekazania roli.
- **Fundusz organizacji**: każdy członek może wpłacić 50–5 000 $ ze swojej gotówki. Fundusz zasila wyłącznie inwestycje dzielnicowe — nie ma wypłat, zwrotów ani żadnej drogi do osobistego wzbogacenia (potwierdzone testami: statystyki i kasa wpłacającego bez zmian).
- **Inwestycje = prestiż**: oficer inwestuje 100–5 000 $ z funduszu w dzielnicę (limit 20 000 $/dzielnica jak przy inwestycjach prywatnych, 20/h). Suma inwestycji organizacji to **prestiż** — widoczny w katalogu organizacji i w panelu „Prestiż dzielnicowy” (TOP 10 świata). Prestiż NIE zmienia stawek kontraktów, statystyk ani bonusów prywatnych dzielnic — to czysto reputacyjna rywalizacja.
- **Ogłoszenia organizacji**: oficer+/lider publikuje komunikat (3–200 znaków, bez linków) widoczny dla członków w panelu organizacji po każdej zmianie; nowe podanie, wpłata czy inwestycja odświeżają widok wszystkim po ponownym wejściu do Społeczności.
- Testy: `tests/test_orgs2.py` (bramy rang, przepływ podania + blokady, fundusz bez bonusów mocy, ogłoszenia + migracja legacy) oraz `tests/test-orgs.cjs` (pełny scenariusz w prawdziwym UI: założenie, podanie z katalogu, przyjęcie, wpłata, inwestycja, ogłoszenie, ranking; transport podglądu, brak błędów JS, brak przepełnienia na 390 px).

## 0.9 — Głębsza gospodarka + bezpieczeństwo i RODO

### Gospodarka
- **Przetarg dnia**: jedna spersonalizowana, overMarketowa propozycja dziennie (10–30% powyżej stawki), wygasa z końcem doby UTC. Deterministyczna z (świat, postać, dzień) — serwer ją liczy, klient tylko pokazuje.
- **Ceny kontraktów zmienne**: codziennie każdy kontrakt ma mnożnik 0,85–1,15 wspólny dla całego świata (karta pokazuje „+X% dziś”); wypłata liczona jest na serwerze według dnia zakończenia zlecenia.
- **Pojazdy z zużyciem**: Rower dostawczy 600 $ (−10% czasu zleceń, poziom 1), Furgonetka 2 400 $ (−20%, poziom 4), Bus flotowy 7 000 $ (−30%, poziom 6). Każde ukończone zlecenie to +6% zużycia; przy 100% pojazd traci rabat do czasu płatnego serwisu.
- **Pracownicy na dobę**: Kurier junior (300 $), Barista (250 $), Trener personalny (500 $) — +25% dochodu przypisanej firmy przez 24 h, bez długów i bez odnawiania automatycznego.
- **Inwestycje dzielnicowe**: 100–5 000 $ na transakcję, do 20 000 $ na dzielnicę; każde 1 000 $ daje +1% stawek kontraktów w tej dzielnicy (do +15%). Sumy świata liczy nowa tabela `investments` — podstawa pod przyszłą rywalizację prestiżową.

### Bezpieczeństwo i RODO
- **Zgoda wieku przy rejestracji** (art. 8 RODO, polski próg 16 lat): obowiązkowe oświadczenie „16+ albo zgoda opiekuna”; zapisywane na koncie jako atestacji, nie weryfikacja tożsamości.
- **Limit 8 kont na adres** (jednokierunkowy skrót adresu, bez zapisu adresu) — przeciwdziałanie farmieniu.
- **Karencja usunięcia konta 7 dni**: konto znika natychmiast (wylogowanie, blokada), dane opuszczają bazę po karencji (sweep przy starcie i co 15 min); anulowanie hasłem w panelu konta.
- **Rola moderatora**: osobno od administratora — tylko kolejka zgłoszeń i odwołań; nadaje/odbiera administrator w panelu; granice pokryte testami.
- **Odwołania od kar czatu**: raz na dobę, priorytet w panelu zgłoszeń; uwzględnienie zdejmuje wyciszenie.
- **Ogłoszenia administratora**: globalne lub na wskazany świat, baner w grze z potwierdzeniem, retencja 7 dni; pole ogłoszenia także przy tworzeniu świata.

## 0.8 — Powrót do gry: rezydencja, odpoczynek, skrzynka powrotna

- **Rezydencje** (Przedsiębiorstwa → nowa zakładka i pin na mapie): Kawalerka 1 200 $ (od poziomu 1, +2 energii/h), Apartament w Centrum 6 000 $ (poziom 3, +4/h, odpoczynek +10%), Willa w Zielonej Oazie 20 000 $ (poziom 5, +8/h, odpoczynek +25%). Wyższy próg zastępuje poprzedni bez zwrotu; rezydencja należy do postaci w danym świecie.
- **Odpoczynek** działa jak zlecenie na energię: Krótki sen 20 min (+10), Nocny 4 h (+70, próg 2), Weekend w spa 8 h (+160, próg 3). Bonus procentowy rezydencji zwiększa zysk. Jeden odpoczynek naraz; nie blokuje kontraktów ani treningów; nadwyżka ponad 240 energii przepada z uczciwym komunikatem; przypomnienie o nieodebranym odpoczynku ląduje w historii.
- **Skrzynka powrotna**: po ponad 30 minutach gry (przeliczonych tempem świata) serwer sam przygotowuje podsumowanie nieobecności — ukończone zlecenia i treningi, suma skarbców, ukończony odpoczynek — i pokazuje je na starcie (Miasto i Rezydencja). Jednorazowe potwierdzenie przyciskiem „Otwórz miasto”.
- **Kontrakty długodystansowe**: Kontrakt flotowy 8 h (poziom 5, 1 600 $ / 240 XP) i Zarządzanie filią 24 h (poziom 7, 6 000 $ / 900 XP) — powód, żeby wrócić następnego dnia. Katalog rośnie do 9 kontraktów.
- Regeneracja bazowa bez mieszkania bez zmian (10/h); HUD, Kontrakty i Rezydencja pokazują aktualne tempo. Stare stany postaci uruchamiają się bez migracji (brakujące klucze dopisuje serwer).
- Testy: `tests/test_idle.py` (zegar wstrzykiwany: regeneracja, progi rezydencji, przepadnięcie nadwyżki, jednorazowość skrzynki, progi poziomów nowych kontraktów, stare zapisy) oraz `tests/test-idle.cjs` (zakup rezydencji, licznik 600→720/h, śpij/odbierz, skrzynka po okresie ciszy, brak nadmiarowego przewijania na 390 px; transport podglądu bez cookies i nagłówków).

## Poprawka 0.7.1 — widoczność animacji walki

W zwykłej konfiguracji odtworzono działające efekty. Wykryto też wariant, w którym systemowe `prefers-reduced-motion` ukrywało całą warstwę rękawic, blokowało przełącznik i automatycznie ustawiało tempo 4×. Nie potwierdzono, jakie ustawienie było aktywne w przeglądarce użytkownika.

- Systemowe ograniczenie ruchu jest nadal respektowane domyślnie. Gracz może teraz świadomie włączyć efekty lokalnym przyciskiem w klubie albo przełącznikiem u góry; wybór zapisuje się w przeglądarce, jeśli pamięć jest dostępna.
- Panel **Animacje walki** jawnie pokazuje włączenie/wyłączenie i systemową przyczynę. Przy włączeniu wybierane jest tempo 1×; nie ma automatycznej zmiany na 4× przez ustawienie systemowe.
- Powtórka, sparing, podgląd pojedynczego efektu i PvP przewijają do zawodników przed rozpoczęciem animacji. Wcześniej przycisk powtórki mógł zostawić portrety poza ekranem.
- Nie zmieniono gospodarki, obliczeń walki ani zapisanych danych. Przełącznik wpływa wyłącznie na prezentację.
- Powtórka i każdy start pojedynku przewijają widok do kart zawodników; panel pokazuje przycisk „Zwolnij do 1×”, gdy odtwarzanie jest przyspieszone.
- `npm run test:combat-ui` na osobnym serwerze QA sprawdza faktyczny ruch rękawicy i jej widoczność w obszarze ekranu, cios/paradę/krytyk na 1440 i 390 px, ustawienie systemowe, zapisane wyłączenie, ponowne włączenie/reload, prawdziwy sparing oraz PvP i replay bez zmiany Elo. Także z usuniętymi cookies i dodatkowymi nagłówkami.
- Poprawki uboczne znalezione przy testach: stan preferencji ruchu jest deklarowany przed pierwszym `renderConfig()` (wcześniej init rzucał `Cannot access 'motionChoice' before initialization`), a wzór loginu ma `-` na początku klasy znaków, bo Chrome kompiluje atrybut `pattern` z flagą `v`. Testy społeczności czekają teraz na odświeżenie panelu po przekazaniu lidera i opuszczeniu organizacji — wcześniejsze asercje bywały wyprzedzać render (ok. 1 na 3 przebiegi).

## Co nowego w 0.7

### Rozgrywka
- **7 kontraktów**: dotychczasowe 5 oraz Kampania lokalnej marki (poziom 2) i Koordynacja targów biznesowych (poziom 4).
- **Studio Forma**, trzecia firma obok City Courier i Corner Café: poziom postaci 3, otwarcie 4 000 $, osobny skarbiec, 4 poziomy firmy. Dochód bazowy 55/80/115/160 $ na godzinę; rozbudowy 2 400/5 000/10 000 $. Rozbudowa trwa 10 minut / tempo świata.
- 3 nowe przedmioty: Opaska Analyst i Buty Agile od poziomu 2, Strój Captain od poziomu 3. Łącznie 12 przedmiotów, w tym 4 startowe. Katalog klienta i bonusy pochodzą z katalogu serwera; blokady poziomu obowiązują również w API.
- Ekran miasta pokazuje kolejne cele rozwoju. Nie dają dodatkowych premii ani punktów do rankingów.
- Balans liczbowy jest propozycją do dalszych testów, nie zamkniętym projektem gospodarki.

### Społeczność
- Menu **Społeczność**: organizacja, zaproszenia, katalog organizacji i czat.
- Jedna organizacja na postać i świat. Bezpłatne utworzenie, unikalna nazwa i skrót w świecie, opis publiczny. Limit etapu: 200 organizacji na świat, 20 członków w organizacji. Bez wspólnej waluty, skarbca i premii ekonomicznych.
- Lider zaprasza, usuwa członków i przekazuje rolę. Zaproszenie trwa 24 h, jedną postać można zaprosić raz na 24 h z tej samej organizacji. Lider z innymi członkami nie może odejść ani usunąć konta przed przekazaniem roli. Odejście samotnego lidera rozwiązuje organizację i usuwa jej czat.
- Czat świata i czat organizacji. Historia ostatnich 60 wiadomości, odświeżanie co 6 s przy otwartym panelu. Nowi członkowie widzą dostępną historię swojej organizacji. Brak wiadomości prywatnych i załączników.
- Wiadomość do 300 znaków; odstęp 3 s, do 40 wiadomości na godzinę na konto, wspólnie dla światów. Identyfikator klienta chroni przed zdublowaniem wiadomości przy ponowieniu, także równoległym.
- Treści użytkowników są wyświetlane jako tekst, nigdy wykonywany HTML. Prosty filtr adresów/linków nie jest kompletnym filtrem danych osobowych ani nieodpowiednich treści.
- **Zgłoś** przekazuje treść i powód moderatorowi. Administrator widzi tylko zgłoszone wiadomości, także organizacyjne; może odrzucić zgłoszenie, ukryć treść albo ukryć ją i wyciszyć konto na 24 h. Ukrycie nie usuwa treści z bazy. Decyzje trafiają do dziennika.
- **Zablokuj kontakt** działa między kontami na wszystkich światach: wzajemne ukrycie wiadomości, blokowanie zaproszeń organizacyjnych i nowych wyzwań PvP; oczekujące wyzwania są odrzucane. Blokada nie usuwa członkostwa ani publicznej pozycji w rankingu. Cofnięcie: Konto → Zablokowane kontakty.
- To test bez stale obsługiwanej moderacji. Przed publicznym udostępnieniem młodzieży potrzebne są m.in. obsada, procedury, publiczny kontakt, reakcja na nadużycia, moderacja nazw/opisów, odwołania i właściwa retencja. Obecne narzędzia nie zapewniają kompletnej ochrony niepełnoletnich.

### Konto i kopie
- **Konto → Zmień hasło**: potwierdzenie starym hasłem, minimum 4 znaki w development / 12 w production, wylogowanie wszystkich sesji. Równoległa zmiana nie nadpisze nowszego hasła.
- **Aktywne sesje**: data utworzenia, ostatnia aktywność, termin ważności i oznaczenie bieżącej. Można zakończyć wybraną inną sesję albo wszystkie pozostałe, po potwierdzeniu hasłem. Publiczne identyfikatory sesji nie są tokenami ani ich skrótami. To lista sesji, nie rozpoznanych urządzeń. Starsze sesje zachowano; brak historycznej daty utworzenia jest jawnie oznaczony.
- Eksport uwzględnia własne wiadomości, zgłoszenia, blokady, członkostwa, otrzymane zaproszenia, organizacje prowadzone, wyciszenie i metadane sesji. Nie zawiera haseł ani sekretów sesji.
- Usuwanie konta obejmuje powiązane dane społecznościowe w aktywnej bazie. Dawniejsze dane mogą pozostać w kopiach do usunięcia tych kopii przez operatora. Przed publikacją potrzebna jest formalna polityka retencji i procedura usunięć także po odtworzeniu kopii.
- **Administracja → Kopie zapasowe**: stan i utworzenie lokalnej kopii. Automatycznie przy starcie procesu i co 10 minut, dopóki proces działa. Kopie SQLite wykonywane przez backup API, z kontrolą `quick_check`, powiązań i sumą SHA-256. Pliki prywatne 0600, brak pobierania przez HTTP.
- Usługa zachowuje po 6 własnych kopii `auto-*` i `manual-*`. Nie usuwa starszych kopii właściciela `city-empire-*`. Retencja jest liczbową rotacją, nie gwarancją usunięcia po określonej liczbie dni.
- **To kopie na tej samej maszynie, nie zewnętrzny backup ani stały hosting.** Przygotowanie i ograniczenia: [WDROZENIE.md](WDROZENIE.md). Nie wykupiono ani nie uruchomiono hostingu produkcyjnego.

## Szybki test

1. Otwórz **podgląd na żywo CITY EMPIRE · Online 0.7**. Na logowaniu sprawdź **DEV 0.7.1**. Sam `web/index.html` potrzebuje API i nie jest już grą offline.
2. Zaloguj się istniejącym kontem albo utwórz testowe. Login: 3–24 znaki; minimum hasła testowego: 4. Nie używaj hasła z innych usług ani danych wrażliwych. Brak odzyskiwania hasła i zbierania e-maili.
3. Wybierz **CITY LAB** i utwórz postać po zaakceptowaniu testowego charakteru świata. Start: 3 000 $, 240 energii, mała firma i 4 przedmioty. Tempo ×60: dostawa 10 s, trening/inwentaryzacja 5 s.
4. Odbieraj kontrakty, trenuj, kupuj sprzęt. Corner Café od poziomu 2 za 2 500 $, Studio Forma od poziomu 3 za 4 000 $.
5. Otwórz **Społeczność**. Drugie konto w osobnej przeglądarce/oknie prywatnym i na tym samym świecie pozwoli sprawdzić zaproszenia, czat organizacyjny i dobrowolne PvP. Nie tworzymy botów udających graczy.
6. Sprawdź **Konto**: hasło, sesje, blokady, eksport i usuwanie. Te przyciski wykonują prawdziwe operacje, nie makiety. Zmianę hasła testuj na swoim koncie testowym; nie ma procedury odzyskiwania.
7. Postać na **CITY 1** ma oddzielne 300 $, 120 energii i własny rozwój. Nie ma transferów między światami.

## Zachowane zasady i systemy

- Jedna postać na konto na świat, wymuszona przez bazę; niezależne gospodarki. Stare światy nie są resetowane przy otwarciu nowych. Administrator wybiera termin, bez obowiązkowych premier kwartalnych.
- Koszty, czas, nagrody, regenerację, zakupy i pojedynki rozlicza serwer. Przeglądarka tylko prezentuje stan. Cztery miejsca w kolejce zadań; pięć statystyk bez klas; trening kosztuje gotówkę i energię.
- City Courier, Corner Café i Studio Forma zarabiają także offline. Pojemność skarbców: 24 rzeczywiste godziny produkcji. Tempo świata mnoży dochód/regenerację i dzieli czas, nie mnoży cen ani nagród pojedynczego kontraktu.
- Transakcje SQLite `BEGIN IMMEDIATE`, WAL i klucze idempotencji dla gospodarki. API nie przyjmuje klientowskiej gotówki, XP, czasu zakończenia czy wyniku walki.
- Asynchroniczne, dobrowolne PvP między graczami tego samego świata: zapis zestawu wyzywającego, akceptacja rywala, serwerowy raport i Elo w jednej transakcji. Powtórna akceptacja nie liczy drugi raz wyniku.
- Elo startuje od 1 000, K=24; 5 walk na dobę UTC, jedna punktowana walka pary na 24 h, do 3 oczekujących wyzwań. Brak nagród pieniężnych/XP i strat ekwipunku za PvP. Limit dzienny nie znika po usunięciu konta przeciwnika.
- Zachowane wyraźne animacje lecącej rękawicy, parady i krytyka. Replay/skip odtwarza raport, nie nalicza wyniku. Serwerowy generator walk różni się od lokalnego laboratorium; klient odtwarza zdarzenia, nie przelicza wyniku z samego ziarna.
- Sparing „Moja postać”: serwerowy, bez nagród i Elo. Laboratorium: lokalne testy bez wpływu na postęp.
- Ranking oddzielny dla świata; testowe światy oznaczone. Listy graczy do 200 postaci. Brak rankingu globalnego, normalizacji wieku światów i wdrożonych osiągnięć konta.
- Administrator otwiera/planuje światy, steruje rejestracją/przerwą, publikuje komunikaty i zawiesza konta. Zamknięcie rejestracji nie odcina istniejących postaci. Baner nowego świata sprawdzany co 30 s.
- Limit 300 logicznych identyfikatorów światów nie oznacza przetestowanej wydajności 300 aktywnych serwerów. To jedna aplikacja i jedna baza SQLite.

## Logowanie w ograniczonym podglądzie — zachowany transport 0.6.2

Pierwsza poprawka 0.6.1 nie wystarczała, bo nadal wymagała dodatkowych nagłówków. Działający wariant 0.6.2, potwierdzony przez użytkownika, jest zachowany:

1. Development login/register prosi o token przez JSON `preview_session: true`.
2. Kolejne uwierzytelnione operacje idą jako JSON do `/api/preview/request`: sesja, CSRF, metoda, zamknięta ścieżka, dane i identyfikator operacji. Wymagany tylko standardowy Content-Type. Nowe endpointy 0.7 dodano do jawnej listy dozwolonych tras.
3. Adapter wywołuje istniejące endpointy w pamięci przez ASGI. Nie jest zewnętrznym proxy, nie przyjmuje dowolnych URL, rekursji, query ani przechodzenia po katalogach. Wszystkie kontrole sesji, roli, CSRF, banów, limitów i ekonomii pozostają aktywne.
4. Token jest w `sessionStorage`, nigdy w URL/localStorage. Przy zablokowanej pamięci karty pozostaje tylko w pamięci strony; po odświeżeniu trzeba się zalogować. Błędny token nie może zastąpić tożsamości poprawnym cookie.
5. Production wyłącza adapter, wydawanie tokenów podglądu i auth Bearer. Korzysta z cookies HttpOnly; przy HTTPS Secure/SameSite=None/Partitioned, lokalnie Lax. Token CSRF i kontrola Origin/JSON nadal obowiązują.

Token rozwojowy jest czytelny dla JavaScript — to kompromis podglądu i ryzyko w razie XSS, nie wzorzec certyfikowanego wdrożenia. **Nie loguj treści żądań adaptera**, haseł ani nagłówków autoryzacji. Kody CE-AUTH-01/02 nie ujawniają sekretów.

Zewnętrzny odczyt publicznego adresu podglądu przez narzędzia był blokowany ochroną platformy (403 przed aplikacją). Nie omijamy tej ochrony i nie traktujemy tego jako testu ruchu przez interfejs platformy. Ograniczenia sprawdzamy w kontrolowanej przeglądarce z usuwaniem cookies i dodatkowych nagłówków.

## Uruchomienie i administrator

Python 3.11+; testowany Python 3.13:

```bash
cd city-empire/online
python -m pip install -r requirements.txt
bash start.sh
```

`0.0.0.0:3000`; względne adresy `/api/...`, bez klientowskiego localhost. Zmienne:

| Zmienna | Domyślnie / znaczenie |
|---|---|
| `CITY_MODE` | `development`; alternatywa `production`, nie certyfikat gotowości |
| `CITY_PORT` | `3000` |
| `CITY_DB` | `data/city_empire.sqlite3` |
| `CITY_SETUP_FILE` | `data/administrator-setup.txt` |
| `CITY_BACKUP_DIR` | `backups/` obok pliku bazy, czyli domyślnie `data/backups/` |

Build: `python build.py`. **Nie serwuj katalogu projektu przez `http.server` ani jako publiczny katalog statyczny.** FastAPI udostępnia stronę i konkretne API, nie bazę, kopie ani źródła. Po odtworzeniu środowiska mogą zniknąć procesy i zależności; `bash start.sh` odtwarza zależności, ale nie zapewnia ciągłości hostingu.

Pierwszy administrator wymaga prywatnego, jednorazowego kodu `data/administrator-setup.txt` → Konto → Aktywacja administratora. Pierwszy rejestrujący się gracz nie dostaje tej roli automatycznie. Nie publikuj kodu. Po wykorzystaniu plik jest usuwany. Role operator zmienia lokalnie:

```bash
python manage.py grant-admin login
python manage.py revoke-admin login
python manage.py expire-sessions
```

Zmiana roli unieważnia sesje tego konta i trafia do dziennika. Ostatniego administratora nie można usunąć ani zdegradować.

## Kopie i próba odtworzenia

```bash
# Kopia właściciela w online/backups/, poza automatyczną rotacją:
python manage.py backup
# Weryfikacja istniejącej kopii:
python manage.py --db backups/NAZWA.sqlite3 verify-backup
# Próba odtworzenia tylko do NOWEGO, nieaktywnego pliku:
python manage.py --db backups/NAZWA.sqlite3 rehearse-restore --output rehearsal/restore.sqlite3
```

Próba nie nadpisuje istniejących plików. Nie odtwarzaj na działającą bazę. Instrukcja właściwego przełączenia i ograniczenia są w [WDROZENIE.md](WDROZENIE.md). Archiwalna kopia sprzed etapu 0.7 pozostaje w `backups/city-empire-20260928-131359.sqlite3`; archiwum wcześniejszych źródeł w `../archive/online-v062-source.tar.gz`.

## Testy 0.7

**42 testy API**: 25 dotychczasowych oraz 17 nowych, m.in. izolacja światów/organizacji, role, zaproszenia, blokady kont, idempotencja i limity czatu, zgłoszenia/wyciszenie, eksport/usuwanie lidera, sesje, zmiana hasła, równoległe żądania, migracja starej sesji, kopie i odtworzenie. Testy używają tymczasowych baz; `tests/conftest.py` izoluje również aplikację tworzoną podczas importu modułu.

### Podgląd a restarty środowiska

Podgląd Arena działa w ulotnym środowisku: przerwa lub przeładowanie piaskownicy zabija proces gry i kasuje zainstalowane zależności, a przeglądarka pokazuje wtedy `502 Bad Gateway`. To nie jest błąd aplikacji ani utrata danych — plik bazy zostaje w `data/`. Uruchomienie `bash start.sh` przywraca grę na tych samych kontach.

`bash serve-forever.sh` dokłada pętlę nadzoru: po awarii procesu (wyjątek, OOM) serwer wstaje ponownie w 2 s. Nie zapobiega to przeładowaniu samego środowiska — do nieprzerwanej dostępności 24/7 potrzebny jest stały hosting (`WDROZENIE.md`).

```bash
python -m pytest -q
npm ci
npx playwright install --with-deps chromium
```

Testy przeglądarkowe uruchamiaj wyłącznie na **świeżej, osobnej bazie QA**:

```bash
CITY_DB=tests/qa07.sqlite3 CITY_SETUP_FILE=tests/qa07-setup.txt \
CITY_BACKUP_DIR=tests/qa07-backups CITY_PORT=3001 bash start.sh
# W drugim terminalu:
TEST_BASE_URL=http://127.0.0.1:3001 npm run test:auth-ui
TEST_BASE_URL=http://127.0.0.1:3001 TEST_STRIP_HEADERS=1 TEST_SETUP_FILE=tests/qa07-setup.txt npm run test:ui
TEST_BASE_URL=http://127.0.0.1:3001 TEST_DB=tests/qa07.sqlite3 npm run test:features-ui
TEST_BASE_URL=http://127.0.0.1:3001 npm run test:combat-ui
```

Rejestracja konta jest limitowana do 8 prób na 15 minut z jednego adresu IP. Dlatego każdy zestaw testów wymaga własnej, świeżej bazy — inaczej testy kończą się `429 Too Many Requests`, co nie jest błędem aplikacji. Skrót `tests/qa-suite.sh NAZWA PORT ...uruchamia jeden zestaw na jednorazowej bazie, a po teście sam ją usuwa:

```bash
bash tests/qa-suite.sh qa-auth 3002 node tests/test-auth-preview.cjs
bash tests/qa-suite.sh qa-game 3003 node tests/test-online.cjs
bash tests/qa-suite.sh qa-feat 3004 node tests/test-features.cjs
bash tests/qa-suite.sh qa-fx   3005 node tests/test-combat-motion.cjs
```

- Auth: osadzona ramka, brak cookies i dodatkowych nagłówków, hasło 4-znakowe, reload, revokacja, błędne hasło, brak sessionStorage. Atrapa rodzica wyłącza tylko lokalną kontrolę sieci Chromium, nie auth/CSRF aplikacji.
- Dotychczasowy pełny przebieg: 2 konta, kontrakty, trening/sprzęt/kawiarnia, PvP/animacje/replay/Elo, światy, admin i 28 układów responsywnych.
- Nowy przebieg: organizacja/zaproszenie/dołączenie/przekazanie/odejście, prywatne kanały, dosłowny HTML w UGC, zgłoszenie/blokada/cofnięcie, panel moderatora/kopie, Studio Forma, nowy sprzęt, unieważnienie innej sesji i zmiana hasła; społeczność w 4 szerokościach. Wszystkie wywołania idą bez cookies i niestandardowych nagłówków.
- Test nowych funkcji używa narzędzia operatora i podnosi stan **wyłącznie własnej postaci w bazie QA** do testów sprzętu/studia. Nigdy nie wskazuj głównej bazy.
- Sprawdzono integralność i odtworzono przedetapową kopię do osobnego pliku. Przed ponownym uruchomieniem głównej gry konta, skróty haseł, postacie i światy były identyczne z kopią sprzed prac. Nie resetowano danych użytkownika.

Ostrzeżenie deprecacyjne Starlette TestClient/httpx nie oznacza błędu testów. Zrzuty kontrolne znajdują się w `tests/`; nie są dodatkowymi funkcjami gry.

## Pliki

- `server/app.py`: bazowy schemat, sesje, API gospodarki/PvP/światów, adapter podglądu.
- `server/features.py`: organizacje, czat, moderacja, konta i migracja metadanych sesji.
- `server/backups.py`: lokalne kopie i harmonogram procesu.
- `server/economy.py`, `combat.py`: autorytatywne reguły gospodarki i raporty walk.
- `web/network.js`, `extras.js`, `online-game.js`: połączenie z API i widoki gry.
- `web/app.js`, `effects.js`, `engine.js`: animacje i laboratorium; `game-core.js`: pomocnicze definicje dawnego prototypu, nie źródło stanu online.
- `web/template.html` i CSS: źródła; `web/index.html`: wynik builda.
- `manage.py`, `start.sh`, `build.py`, `WDROZENIE.md`: obsługa środowiska.

## Kolejne etapy / granice wydania

Stałe wdrożenie, zewnętrzne szyfrowane kopie i monitoring; audyt i testy obciążenia; role rozdzielone/MFA/odzyskiwanie kont; retencja danych i procedury RODO; pełna moderacja UGC i zabezpieczenia dla niepełnoletnich; przeciwdziałanie farmieniu wieloma kontami; ranking globalny i kosmetyczne osiągnięcia; większe systemy organizacji; aplikacje Android/iOS i przegląd wymagań sklepów.

Monetyzacja pozostaje osobnym etapem. Przyjęty kierunek dopuszcza płatne przyspieszenia wpływające na tempo rozwoju, siłę i rywalizację — nie zmieniono go na wyłącznie kosmetyczny. Osiągnięcia mają być kosmetyczne, bez premii ekonomicznych. **Obecna wersja niczego nie sprzedaje.**

## 0.56.0 — Trasy NPC
- Panel **🚚 Trasy NPC** w Garażu: 6 tras (15–90 min, 180–1500 $, 8–70 XP).
- Kierowcy z Rezydencji: **poziom budynku Rezydencja = liczba tras jednocześnie** (1–5).
- Pojazd z Garażu wpływa na wypłatę (rower ×0,85 … Hiper Widok GT ×1,45); Garaż +2% za każdy poziom ponad 1.
- Kierowcy jeżdżą offline — po powrocie „Odbierz gotowe trasy” daje kasę i EXP. Jeden pojazd = jedna trasa naraz.
- API: `route_dispatch {route, vehicle}`, `route_claim`; katalog `npcRoutes`, `routeVehMult`.

## 0.57.0 — Sojusze
- Organizacja = **Sojusz** z 3 wspólnymi budynkami (Społeczność → panel „Budynki sojuszu”), poziomy 1–3.
- Kupuje lider lub oficer **z funduszu sojuszu**: 2 000 / 5 000 / 10 000 $ za poziom.
- 🏗️ **Szybka Budowa** — rozbudowa firmy −10%/poz. · 🔧 **Tanie Naprawy** — serwis auta −15%/poz. · 🕊️ **Wolność** — podróże −10%/poz.
- Premie działają dla każdego członka; członkowie dostają powiadomienie o rozbudowie.
- API: `POST /api/worlds/{wid}/organizations/building {building}`; katalog `allyBuildings/allyMax/allyCost`.

## 0.58.0 — Eventy czasowe
- Globalna rotacja eventów w **oknach 6 h** (z zegara serwera, te same dla wszystkich graczy), cykl 4 eventów:
  💼 Gorączka Kontraktów (+25% gotówki z kontraktów) · 🚚 Szczyt Przewozów (+50% z Tras NPC) · 📚 Tydzień Nauki (+50% EXP z kontraktów) · 🪵 Dzień Targowy (+30% ze sprzedaży surowców).
- Baner w Mojej dzielnicy: nazwa, opis, odliczanie do końca, zapowiedź następnego.
- Premia liczy się w momencie odbioru (kontrakt/trasa) lub sprzedaży.
- API: `timedEvent` w pakiecie stanu (`id,name,icon,desc,effect,mult,start,end,next`).

## 0.59.0 — Chmurka powiadomień
- Pływający dzwonek 🔔 (prawy dolny róg) z licznikiem: gotowe rzeczy + nieprzeczytane zdarzenia.
- Dymek: **Gotowe do odbioru** (Trasy NPC, kontrakty, trening, odpoczynek — klik przenosi do budynku) i **Zdarzenia** (8 ostatnich z serwera, „Oznacz przeczytane”).
- Wyskakująca chmurka, gdy coś nowego stanie się gotowe; klik poza dymkiem zamyka.
- API: `eventsRecent` w pakiecie stanu (8 ostatnich `game_events` z flagą `read`); nowe zdarzenie `org.building` ma tekst.
