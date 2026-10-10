# 📊 RAPORT 1: KATALOGI I DANE GRY — City Empire v0.59.0

**Źródło:** wartości wyciągnięte **programowo** (import modułów `server/*.py` i zrzut stałych), nie przepisane ręcznie.
Odnośniki `plik:linia` wskazują definicję. Czas w grze: wartości w minutach/godzinach to czas **przy tempie świata ×1**. Serwer dzieli je przez `speed` świata.

> Legenda statystyk (indeksy 0–4, kolejność z klienta `web/app.js:7`): **Siła · Inteligencja · Refleks · Charyzma · Spryt**.
> Zapis `bonus [a,b,c,d,e]` oznacza punkty do tych pięciu statystyk.

---

## 1.1 BUDYNKI DZIELNICY (`economy.py:82–93`, od 0.55.0)

**Wspólne zasady (dla wszystkich budynków):**
- Poziomy **1–5** (`BUILDING_MAX=5`). Start: wszystkie na poziomie 1, Sala Chwały na 0 (`BUILDING_START`).
- Koszt rozbudowy z poziomu *n* na *n+1* (`BUILDING_UPGRADE_COST=[0,500,1500,3000,6000]`): **1→2: 500 $ · 2→3: 1 500 $ · 3→4: 3 000 $ · 4→5: 6 000 $**. Od 1 do 5 łącznie **11 000 $** na budynek.
- Rozbudowa jest **natychmiastowa** (bez czasu budowy). Akcja: `upgrade_building`.
- Sam poziom budynku **nie daje premii liczbowej**, z dwoma wyjątkami (Rezydencja i Garaż, opisane niżej, od 0.56). Budynek to „drzwi” do widoku z funkcjami.

| Klucz | Nazwa | Ikona | Co robi (widok w kliencie) | Max | Efekt samego poziomu |
|---|---|---|---|---|---|
| `residence` | Rezydencja | 🏠 | Zakup mieszkania (regeneracja energii), odpoczynki, trening domowy | 5 | **Liczba kierowców Tras NPC = poziom** (1–5 tras naraz) |
| `garage` | Garaż | 🚗 | Kupno, ulepszanie i serwis aut + panel Tras NPC | 5 | **Wypłata Tras NPC +2% za każdy poziom ponad 1** (max +8%) |
| `cafe` | Kawiarnia | ☕ | Podsumowanie nieobecności + skarbiec dochodu pasywnego | 5 | brak |
| `gym` | Siłownia | 💪 | Statystyki postaci, trening, wyposażenie | 5 | brak |
| `club` | Sala Klubowa | 🥊 | Hub 8 kart dyscyplin (Ring/PvP, lochy, hipodrom…) | 5 | brak |
| `hall` | Sala Chwały | 🏆 | Tablica osiągnięć, historia, wykres dzienny | 1* | brak |

\* **Sala Chwały — odblokowanie, nie rozbudowa:** wymaga wszystkich 5 pozostałych budynków na poziomie 5 + jednorazowo **10 000 $** (`HALL_UNLOCK_COST`). Po odblokowaniu: poziom 1. Pełna droga do Sali Chwały kosztuje 5 × 11 000 + 10 000 = **65 000 $**.

---

## 1.2 FIRMY — DOCHÓD PASYWNY (`economy.py:8–11, 59–61`)

Dochód narasta w **skarbcu** firmy w $ na godzinę i ma limit **24 h** (`rate × 24`). Odbiera się go akcją `collect`. Rozbudowa trwa **10 min** i można ją skrócić Szybką Budową sojuszu.

| Firma | Odblokowanie | Cena zakupu | Dochód $/h na poziomach | Koszty rozbudowy |
|---|---|---|---|---|
| **City Courier** (firma startowa) | od początku | — | 40 · 55 · 75 · 100 · 135 · 175 · 225 (7 poz.) | 1 000 · 2 500 · 5 000 · 9 000 · 15 000 · 24 000 |
| **Corner Café** (`cafe`) | poziom 2 | 2 500 $ | 30 · 45 · 65 · 90 (4 poz.) | 1 500 · 3 500 · 7 000 |
| **Studio Forma** (`studio`) | poziom 3 | 4 000 $ | 55 · 80 · 115 · 160 (4 poz.) | 2 400 · 5 000 · 10 000 |

- Koszt rozbudowy obniża **Inteligencja** (do −15%, `economy.py:370`).
- Liczbę dostępnych firm limituje era: `business` = 2 w Erze I, 7 od Ery II.

### Personel firm (`STAFF`, `economy.py:75`)
| Pracownik | Firma | Koszt | Efekt | Czas |
|---|---|---|---|---|
| Kurier junior | City Courier | 300 $ | dochód +25% | 24 h |
| Barista | Corner Café | 250 $ | dochód +25% | 24 h |
| Trener personalny | Studio Forma | 500 $ | dochód +25% | 24 h |

---

## 1.3 KONTRAKTY (`economy.py:12–20`)

Kontrakt kosztuje energię, trwa określony czas i daje $ oraz EXP. Musi być wykonany **w dzielnicy, w której stoi gracz** (pole `d`). Czas skracają auto (`discount`) i Siła, łącznie maksymalnie o **50%**. Każdy kontrakt zużywa auto o **+6%**.

| ID | Nazwa | Dzielnica (`d`) | Czas | Energia | $ | EXP | Od poz. |
|---|---|---|---|---|---|---|---|
| `inventory` | Inwentaryzacja lokalu | Centrum (3) | 5 min | 5 | 50 | 10 | 1 |
| `delivery` | Dostawa do Lasów Wschodnich | Lasy Wschodnie (8) | 10 min | 10 | 100 | 20 | 1 |
| `event` | Obsługa wydarzenia | Centrum (3) | 20 min | 20 | 200 | 40 | 2 |
| `campaign` | Kampania lokalnej marki | ⚠️ „Dzielnica kreatywna” (6) | 25 min | 25 | 230 | 60 | 2 |
| `audit` | Audyt procesów dostaw | Biznesowe (5) | 30 min | 30 | 300 | 60 | 3 |
| `logistics` | Koordynacja transportu | Portowe (4) | 40 min | 40 | 400 | 80 | 3 |
| `expo` | Koordynacja targów biznesowych | ⚠️ „Centrum konferencyjne” (7) | 60 min | 60 | 660 | 100 | 4 |
| `fleet` | Kontrakt flotowy | Portowe (4) | 8 h | 80 | 1 600 | 240 | 5 |
| `branch` | Zarządzanie filią | Biznesowe (5) | 24 h | 140 | 6 000 | 900 | 7 |
| `remote` | Zlecenie specjalne · praca zdalna | dowolna (PC) | 15 min | 10 | 150 | 25 | od Ery II (`pc`) |

⚠️ **Niespójność w danych:** `campaign` i `expo` mają w polu `district` stare nazwy. Według mapy d6 = **Sportowe**, a d7 = **Kopalnia** (lokacja surowcowa). Kontrakt `expo` jest więc przypisany do kopalni. Do decyzji w GDD.

**Modyfikatory wypłaty:** Inteligencja podnosi stawkę pracy zdalnej (do +30%). VIP daje +25% gotówki z kontraktów. Event „Gorączka Kontraktów” daje +25% $, a „Tydzień Nauki” +50% EXP.

---

## 1.4 SUROWCE I HANDEL (`economy.py:23–26`, od 0.54.0)

| Surowiec | Ikona | Gdzie zbierać | Energia/zbiór | Cena bazowa |
|---|---|---|---|---|
| Tworzywa | 🧱 | Zakłady Miejskie (d2) | 12 | 20 $ |
| Ruda | ⛏️ | Kopalnia (d7) | 14 | 30 $ |
| Drewno | 🌲 | Lasy Wschodnie (d8) | 10 | 14 $ |

- Jeden zbiór daje **2–4 sztuki**. Sprzedaż jest możliwa **tylko w miastach**: d1, d3, d4, d5, d6.
- **Mnożnik ceny skupu w mieście** (`MATERIAL_BUY`):

| Miasto | Tworzywa | Ruda | Drewno |
|---|---|---|---|
| Ostoja (d1) | ×1.0 | ×1.0 | **×1.5** |
| Centrum (d3) | **×1.5** | ×1.0 | ×1.0 |
| Portowe (d4) | ×1.0 | **×1.5** | ×1.0 |
| Biznesowe (d5) | ×1.25 | ×1.25 | ×1.25 |
| Sportowe (d6) | ×1.1 | ×1.1 | ×1.3 |

Event „Dzień Targowy” daje +30% do każdej sprzedaży.

---

## 1.5 MAPA I PODRÓŻE (`travel.py:17–22`, `economy.py:163`)

| ID | Lokacja | Typ | Odległość koleją od Ostoi (`HOPS`) |
|---|---|---|---|
| 1 | Ostoja | miasto (start) | 0 |
| 2 | Zakłady Miejskie | surowce | 1 |
| 3 | Centrum | miasto | 1 |
| 4 | Portowe | miasto | 2 |
| 5 | Biznesowe | miasto | 2 |
| 6 | Sportowe | miasto | 1 |
| 7 | Kopalnia | surowce | 2 |
| 8 | Lasy Wschodnie | surowce | 1 |

**Środki transportu:**
- **Bus:** 20 $. Czas `5 min × odległość`, minimum **60 s**.
- **Auto:** 20% czasu busa (−80%), minimum 1 s. Wymaga sprawnego auta.
- **Autostop:** darmowy, czas losowy. Ryzyko pecha 15% (−10 energii). Refleks zmniejsza ryzyko (do 3%) i skraca czas (do −25%).

**Era a mapa:** lokacje miejskie odblokowuje era (`districts` w tabeli er). Lokacje surowcowe (2, 7, 8) są **zawsze otwarte**. Budynek sojuszu „Wolność” skraca podróże o 10% na poziom.

---

## 1.6 POJAZDY — GARAŻ (`economy.py:68–73, 134, 168–177`)

| ID | Nazwa | Cena | Od poz. | Skrócenie kontraktów | Serwis | Mnożnik Tras NPC | Uwagi |
|---|---|---|---|---|---|---|---|
| `rower` | Rower dostawczy | 600 $ | 1 | −10% | 150 $ | ×0.85 | — |
| `sedan` | Sedan Miejski | 4 200 $ | 3 | −24% | 800 $ | ×1.15 | — |
| `furgonetka` | Furgonetka | 2 400 $ | 4 | −20% | 500 $ | ×1.00 | — |
| `bus` | Bus flotowy | 7 000 $ | 6 | −30% | 1 400 $ | ×1.25 | **premium**, od Ery III |
| `supercar` | Hiper Widok GT | 16 000 $ | 8 | −42% | 2 400 $ | ×1.45 | **tylko VIP** |

- **Zużycie:** +6% za kontrakt. Przy 100% auto nie daje premii i wymaga **serwisu** (Tanie Naprawy sojuszu: −15% za poziom).
- **Ulepszenia** (`GARAGE_UP_MAX=3`, silnik/zawieszenie/lakier): każdy poziom to **+4 pkt** skrócenia kontraktów. Koszt poziomu *n*: `cena × 0.4 × n` (zaokrąglone do 10 $), np. rower 240/480/720 $.
- **Miejsca parkingowe:** 1 (auto w użyciu) + `slots` rezydencji + 1 za każde 20 pkt Charyzmy powyżej 10.

---

## 1.7 REZYDENCJE / MIESZKANIA (`economy.py:63–66, 185`)

Energia: limit **240**, regeneracja **10/h + premia mieszkania** (× tempo świata).

| ID | Nazwa | Od poz. | Cena | Regen | Odpoczynek | Miejsca w garażu |
|---|---|---|---|---|---|---|
| `studio-flat` | Kawalerka na Przedmieściach | 1 | 1 200 $ | +2/h | +0% | 0 |
| `center-apartment` | Apartament z Miejscem Parkingowym | 3 | 6 000 $ | +4/h | +10% | 1 |
| `green-villa` | Willa z Garażem Podziemnym | 5 | 20 000 $ | +8/h | +25% | 3 |

Nie da się „zejść” do mieszkania z gorszą regeneracją. Własne mieszkanie odblokowuje też **trening domowy** (sama energia, bez opłaty).

### Odpoczynki (`RESTS`, `economy.py:144`)
| ID | Nazwa | Czas | Energia | Wymagane mieszkanie (tier) |
|---|---|---|---|---|
| `nap` | Krótki sen | 20 min | +10 | 1 (Kawalerka) |
| `night` | Nocny odpoczynek | 4 h | +70 | 2 (Apartament) |
| `spa` | Weekend w spa | 8 h | +160 | 3 (Willa) |

Energia z odpoczynku rośnie o `restBonus` mieszkania. Nadwyżka ponad 240 przepada.

---

## 1.8 TRASY NPC (`economy.py:95–103`, od 0.56.0)

| ID | Nazwa | Linia | Czas | $ (baza) | EXP |
|---|---|---|---|---|---|
| `courier` | Kurierka miejska | Ostoja ↔ Zakłady Miejskie | 15 min | 180 | 8 |
| `tram` | Tramwaj towarowy | Centrum ↔ Portowe | 30 min | 380 | 16 |
| `portbiz` | Port–Biznes | Portowe ↔ Biznesowe | 45 min | 620 | 26 |
| `ring` | Ring sportowy | Biznesowe ↔ Sportowe | 60 min | 900 | 40 |
| `timber` | Tarcica z Lasów | Lasy Wschodnie ↔ Zakłady Miejskie | 75 min | 1 150 | 55 |
| `ore` | Transport rudy | Kopalnia Rudy ↔ Biznesowe | 90 min | 1 500 | 70 |

**Wypłata** = `baza × mnożnik pojazdu × (1 + 0.02 × (poziom Garażu − 1))`, a w czasie eventu „Szczyt Przewozów” jeszcze ×1.5.
**Sloty** to poziom Rezydencji (1–5). Jedno auto może jechać tylko jedną trasą naraz. Trasy jadą też offline. Wszystkie trasy są dostępne od początku (bez bramek poziomu i ery).

---

## 1.9 PRZEDMIOTY — WYPOSAŻENIE (`economy.py:30–57, 239`)

**Sloty (7):** rękawice, strój, buty, akcesorium, kask, plecak, amulet. Przedmioty kupuje się za $. **Bez losowania i bez setów.**

| ID | Nazwa | Slot | Cena | Bonus [Si,In,Re,Ch,Sp] | Poz. | Tier |
|---|---|---|---|---|---|---|
| basic-gloves | Rękawice treningowe | gloves | 0 | — | — | start |
| basic-shirt | Strój klubowy | shirt | 0 | — | — | start |
| basic-shoes | Buty sportowe | shoes | 0 | — | — | start |
| basic-accessory | Opaska treningowa | accessory | 0 | — | — | start |
| basic-helmet | Kask treningowy | helmet | 0 | — | — | start |
| basic-backpack | Plecak podróżny | backpack | 0 | — | — | start |
| basic-amulet | Sznurek z krzemieniem | amulet | 0 | — | — | start |
| tactical-band | Opaska taktyczna | accessory | 200 | [0,0,0,1,2] | — | sklep |
| urban-gloves | Rękawice Urban | gloves | 250 | [2,0,0,0,0] | — | sklep |
| sprint-shoes | Buty Sprint | shoes | 300 | [0,0,2,0,0] | — | sklep |
| focus-shirt | Strój Focus | shirt | 350 | [0,2,0,1,0] | — | sklep |
| trekker-pack | Plecak Trekker | backpack | 450 | [0,0,1,0,1] | 2 | Specjalistyczne |
| counter-gloves | Rękawice Counter | gloves | 500 | [2,0,0,0,2] | — | sklep |
| focus-amulet | Amulet Skupienia | amulet | 500 | [0,2,0,0,0] | 2 | Specjalistyczne |
| charm-amulet | Amulet Charyzmy | amulet | 650 | [0,0,0,2,0] | 3 | Specjalistyczne |
| analyst-band | Opaska Analyst | accessory | 750 | [0,3,0,0,2] | 2 | Specjalistyczne |
| agile-shoes | Buty Agile | shoes | 750 | [0,0,3,0,2] | 2 | Specjalistyczne |
| spartan-helmet | Hełm Spartan | helmet | 800 | [2,0,0,0,1] | 2 | Specjalistyczne |
| captain-shirt | Strój Captain | shirt | 1 200 | [0,2,0,4,0] | 3 | Specjalistyczne |
| **buty-cienia** | Buty Cienia | shoes | — | [0,0,2,0,1] | — | **unikat lochu (piętro 3)** |
| **rekawice-lochu** | Rękawice Lochu | gloves | — | [2,0,0,0,1] | — | **unikat lochu (piętro 6)** |
| **korona-wladcy** | Korona Władcy Lochu | accessory | — | [2,2,0,2,0] | — | **unikat lochu (piętro 10)** |
| **helm-lochu** | Hełm Lochu | helmet | — | [1,0,0,0,1] | — | unikat (w katalogu, brak w `LOOT_FLOORS`) |

---

## 1.10 POSTAĆ: KLASY, EWOLUCJE, STATYSTYKI (`economy.py:179–183`, `combat.py:37–39`)

- **Start:** 300 $ (świat testowy: 3 000 $), 120 energii (testowy: 240), statystyki [10,10,10,10,10] albo startowe klasy.
- **Poziom z EXP:** `level = floor((1 + √(1 + 8·xp/100)) / 2)`. Kolejne progi: 0 · 100 · 300 · 600 · 1 000 · 1 500 … EXP (próg poziomu *n* to 50·n·(n−1)).
- **Trening:** +1 do statystyki, 5 min, 50 $ (Charyzma do −9%) + 5 energii. Kolejka maksymalnie 4. Trening domowy: tylko energia.

| Klasa | Ikona | Startowe [Si,In,Re,Ch,Sp] | Pasywka |
|---|---|---|---|
| **Bokser** | 🥊 | [14,8,10,10,8] | Mocny cios +2 obrażeń w PvP |
| **Obrońca** | 🛡️ | [8,14,8,12,8] | Kontratak po skutecznym uniku (40% szybkiego ciosu) |
| **Szybki** | ⚡ | [8,8,14,8,12] | Inicjatywa +3 Refleksu |

**Ewolucje (2 na klasę):**
| ID | Klasa | Nazwa | Pasywka | Efekt |
|---|---|---|---|---|
| mistrz-ringu | Bokser | 👑 Mistrz Ringu | Rytm | celny cios +5% do następnego (kumuluje się) |
| zelazna-piesc | Bokser | 👊 Żelazna Pięść | Nokaut | mocne ciosy +15%, przełamują blok |
| murarz-ringu | Obrońca | 🧱 Murarz Ringu | Garda | −20% obrażeń w zderzeniach |
| zelazny-straznik | Obrońca | ⚔️ Żelazny Strażnik | Riposta | kontratak 40% → 75% |
| blyskawica | Szybki | ⚡ Błyskawica | Kontra z Impetem | po uniku następny cios ×1.25 |
| nokaut-fantom | Szybki | 👤 Nokaut Fantom | Nieuchwytny | obrażenia ×0.9, unik leczy +15 HP |

**Co robią statystyki poza walką:**
- **Siła:** skraca kontrakty (wspólny limit 50% razem z autem).
- **Inteligencja:** wyższe stawki pracy zdalnej (do +30%), tańsze rozbudowy firm (do −15%).
- **Refleks:** autostop (mniejsze ryzyko, krótszy czas).
- **Charyzma:** tańszy trening (do −9%), +1 miejsce parkingowe za 20 pkt.
- **Spryt:** używany w walce i w wyścigach (u NPC jako `cunning`).

---

## 1.11 WALKA I PvP (`combat.py:4–36`)

- **Akcje w rundzie:** `fast` (szybki cios), `heavy` (mocny cios), `dodge` (unik). Domyślna obrona offline: fast → dodge → heavy.
- **Style (taktyka, układ kamień-papier-nożyce)** (`BEATS`): **Presja → bije Kontrolę → bije Kontrę → bije Presję**. Przewaga daje **+8% obrażeń**.

| Styl | Ikona | Sekwencja | Bije |
|---|---|---|---|
| Presja | ⚡ | fast, heavy, fast | Kontrolę |
| Kontrola | 🛡️ | fast, dodge, heavy | Kontrę |
| Kontra | 🎯 | dodge, fast, dodge | Presję |

- PvP jest asynchroniczne, od **2. poziomu**. Taktykę wybiera się raz na walkę. Obowiązuje limit dzienny i limit per para graczy (`pvp.py`).
- RNG: ziarno `secrets.randbits(32)`, więc walkę można odtworzyć (replay).

---

## 1.12 LOCHY (`dungeon.py:15–17`)

Lochy są dostępne od **3. poziomu**. Każda próba kosztuje **8 energii**. Jest **10 pięter** i na każdym przeciwnik NPC.

| Piętro | Przeciwnik | Klasa | Statystyki [Si,In,Re,Ch,Sp] | Łup |
|---|---|---|---|---|
| 1 | Szczur z Kanałów | Szybki | [6,6,7,5,7] | — |
| 2 | Beczkowy Golem | Obrońca | [9,7,6,8,6] | — |
| 3 | Nurka Zwis | Szybki | [10,8,11,7,10] | **Buty Cienia** |
| 4 | Kanalarz Glo | Bokser | [13,8,9,9,8] | — |
| 5 | Pani Mgły | Obrońca | [10,14,9,12,9] | — |
| 6 | Rdza | Szybki | [12,10,14,9,13] | **Rękawice Lochu** |
| 7 | Oberwany Sufit | Bokser | [16,10,10,11,9] | — |
| 8 | Dwoje Oczu | Szybki | [14,12,16,11,15] | — |
| 9 | Strażnik Bramy | Obrońca | [15,17,12,16,12] | — |
| 10 | Władca Lochu | Bokser | [21,18,17,20,17] | **Korona Władcy Lochu** |

Łup jest **stały** (określone piętro daje określony przedmiot) — nic nie jest losowane.

---

## 1.13 SALA KLUBOWA — SPORT (`sports.py:18–33`)

**Hipodrom:** w dzielnicy **Sportowe (d6)**, od **5. poziomu**. Wpisowe **50 $**, **bez obstawiania**. Pula dzielona **60 / 30 / 10%** na miejsca 1–3. Puchar daje **+25 prestiżu**.

| Koń | Cena | Szybkość | Wytrzymałość | Od poz. |
|---|---|---|---|---|
| Mustang | 800 $ | 3 | 3 | 5 |
| Pełnej krwi | 3 000 $ | 5 | 4 | 6 |
| Czempion | 8 000 $ | 6 | 6 | 8 |

**Rywale NPC na torze:** Ryszard „Roko” (Ch 8 / Sp 6 / szyb. 3 / wytrz. 3), Basia Błyskawica (5/9/4/4), Tadeusz „Truchł” (7/7/2/5).

**Sekcja boksowa:** sparingi na poziomach `rookie`, `clubmate`, `challenger`. Ring i taktyka działają w arenie (PvP).

> Hub Sali Klubowej pokazuje **8 kart dyscyplin** (`web/online-game.js`, `SPORTS`). Dyscypliny spoza hipodromu i boksu są w `sports2.py`. Ich szczegóły trafią do raportu o mechanikach.

---

## 1.14 SOJUSZE — BUDYNKI (`economy.py:104–118`, od 0.57.0)

Sojusz ma limit **20 członków**. Budynki kupuje lider lub oficer **z funduszu sojuszu** (wpłata członka: 50–5 000 $ jednorazowo). Poziomy **1–3**, koszt kolejnych poziomów: **2 000 / 5 000 / 10 000 $**.

| ID | Nazwa | Ikona | Efekt na poziom | Max (poz. 3) |
|---|---|---|---|---|
| `fast_build` | Szybka Budowa | 🏗️ | rozbudowa firmy −10% czasu | −30% |
| `cheap_repair` | Tanie Naprawy | 🔧 | serwis auta −15% | −45% |
| `freedom` | Wolność | 🕊️ | podróże −10% czasu | −30% |

**Inwestycje dzielnicowe organizacji:** krok **1 000 $**, limit **20 000 $** (`INVEST_STEP/CAP`). Suma inwestycji decyduje o **wpływach (terytorium)** w dzielnicy.

---

## 1.15 EWENTY CZASOWE (`economy.py:121–133`, od 0.58.0)

Okna trwają **6 h** i są globalne (liczone z zegara serwera), w stałej kolejności:

| # | ID | Nazwa | Efekt |
|---|---|---|---|
| 1 | `gold_rush` | 💼 Gorączka Kontraktów | kontrakty +25% $ |
| 2 | `route_rush` | 🚚 Szczyt Przewozów | Trasy NPC +50% $ |
| 3 | `study` | 📚 Tydzień Nauki | kontrakty +50% EXP |
| 4 | `market` | 🪵 Dzień Targowy | sprzedaż surowców +30% $ |

Cały cykl trwa 24 h. Nazwa „Tydzień Nauki” jest myląca: to okno 6 h.

---

## 1.16 ERY ŚWIATA (`city_events.py:13–19`)

Era zależy od dnia od utworzenia świata. Era I zaczyna się w dniu 1, a kolejne w dniach 3/5/7+ (tabela `[3,5,6,8]` w kliencie).

| Era | Nazwa | Dzielnice miejskie | Firmy | Praca zdalna (PC) | Premium (auta) |
|---|---|---|---|---|---|
| I | Czas Pionierów | 3 | 2 | ✗ | ✗ |
| II | Rozwój Przemysłu | 5 | 7 | ✓ | ✗ |
| III | Wielki Biznes | 6 | 7 | ✓ | ✓ |
| IV | Metropolia & Epilog | 8 | 7 | ✓ | ✓ |

**Sezony rankingowe:** 28 dni (`features.py:93`, `SEASON_LEN`). Koniec sezonu daje tytuły **kosmetyczne**. Postać nie jest resetowana.

---

## 1.17 SKLEP DEV (`shop.py:17–29`)

**Bez prawdziwych płatności.** Zakupy są **domyślnie wyłączone**. Małoletni wymagają zgody opiekuna z limitem tygodniowym 500–20 000 (`shop.py:44–49`).

| SKU | Nazwa | Cena (pozorowana) | Efekt | Limit |
|---|---|---|---|---|
| `vip30` | VIP · 30 dni | 19,99 zł | **+25% gotówki z kontraktów**, złota rama, auto VIP | — |
| `vip7` | VIP · 7 dni | 7,99 zł | jak wyżej, okresy się sumują | — |
| `starter` | Pakiet startowy | 9,99 zł | 5 000 $ + 3 przedmioty Specjalistyczne + natychmiastowy odpoczynek | raz na konto |
| `energy` | Energiapak +100 | 4,99 zł | +100 energii (nadwyżka ponad 240 przepada) | 2 / dobę UTC |
| `speedup` | Przyspieszenie zlecenia | 2,99 zł | trwające zlecenie krótsze o 50% | 3 / dobę UTC |
| `skin_copper` | Skórka: Miedź | 3,99 zł | rama profilu (kosmetyka) | — |
| `skin_gold` | Skórka: Złoto | 5,99 zł | rama profilu (kosmetyka) | — |
| `skin_neon` | Skórka: Neon | 9,99 zł | rama profilu (kosmetyka) | — |

**Brak** drugiej waluty (diamentów), lootboxów i losowych nagród za pieniądze. Uwaga: VIP (+25% $) i starter dają przewagę ekonomiczną, więc to nie jest wyłącznie kosmetyka.

---

## 1.18 AWATAR (`avatar.py:10–43`)

- **Ciało:** 2 sylwetki (m/k), 6 odcieni skóry, 6 fryzur (Łysina, Krótkie, Boczne, Kręcone, Długie, Jeż), 8+ kolorów włosów.
- **14 kategorii × 10 elementów = 140 elementów** (ceny w $, część z flagą VIP): Okulary, Czapki, Kapelusze, Kolczyki, Naszyjniki, Pierścionki, Koszulki, Bluzy, Kurtki, Spodnie, Spodenki, Skarpetki, Buty, Plecaki.
- **Wygląd wyposażenia z gry:** 23 przedmioty z §1.9 mają własny wygląd na awatarze i zakrywają odpowiadające elementy (np. kask zakrywa czapkę i kapelusz).

---

## 1.19 POZOSTAŁE KATALOGI

- **Dystynkcje dnia** (`MARKS`, raz na dobę UTC, kosmetyczne): Kontrakt dnia · Trening dnia · Dochód dnia · Wsparcie organizacji · Inwestycja dzielnicowa · Praca na PC dnia · Wypoczynek dnia.
- **Lokacje fabularne** (`LOCATIONS`): Ulica · Siłownia · Klub Sportowy · Targ · Brama Lochu.
- **Kronika miasta:** limit 300 wpisów na świat (`chronicle.py:13`).
- **Zdarzenia gracza:** maksymalnie 100 na postać, z czego 8 ostatnich trafia do Chmurki powiadomień.

---

### 🔧 Poprawki do wcześniejszego audytu (wynikające z tego raportu)
1. **Klasy:** w kodzie są **Bokser, Obrońca i Szybki**. Obrońca i Szybki zgadzają się z briefem, a „Atakujący” to w kodzie Bokser.
2. **VIP:** daje **+25% gotówki z kontraktów** (a nie tylko kosmetykę i jedno auto).
