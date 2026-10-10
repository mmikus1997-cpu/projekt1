# Raport 2 — Mechaniki (v0.59.0, stan kodu)

Zasada: wszystko z kodu `online/server/`. **BRAK** oznacza, że w kodzie tego nie ma, a **DO WERYFIKACJI** — że kod jest niejednoznaczny. Czas jest liczony wyłącznie po stronie serwera, w ms. `speed` to mnożnik tempa świata.

## 2.1 Waluty, sinki i faucety

| Waluta | Gdzie | Uwagi |
|---|---|---|
| Gotówka `$` | `state.cash` | jedyna waluta w grze; start 300 $ (świat testowy 3000) — economy.py:183 |
| Energia | `state.energy` | zasób akcji (2.2) |
| XP | `state.xp` | progres (2.3) |
| Surowce | `state.materials` (tworzywa, ruda, drewno) | półwaluta, sprzedawana za $ |
| Fundusz organizacji | `organizations.fund` | $ wpłacone przez członków |
| PLN (dev) | `shop_purchases.cents` | **bez realnych płatności**, kasa pozorowana — shop.py:28 |
| Waluta premium (gemy itp.) | — | **BRAK** |

**Faucety ($ wchodzi do gry)**

| Źródło | Kwota | Źródło w kodzie |
|---|---|---|
| Odbiór kontraktu | cena z katalogu × dzienny kurs 0,85–1,15 × (1 + inwestycje% + dystans%) ×1,25 VIP × event | economy.py:151,164–167,314–318 |
| Przetarg dzienny | cena ×1,10–1,30, 1 dziennie | economy.py:158–160 |
| Praca zdalna PC | 150 $ (+ do 30% z Int), 25 XP, 10 energii, 15 min | economy.py:20,316 |
| Firmy idle (Courier/Café/Studio) | stawka/h wg poziomu, skarbiec max 24 h | economy.py:188–200 |
| Sprzedaż surowców | cena dzielnicy × ilość × event | economy.py:270–280 |
| Trasy NPC | baza × mnożnik auta × (1 + 2%·(Garaż−1)) × event | economy.py:137–139, 481 |
| Loch | 30 + 30·piętro $, 8 + 4·piętro XP | dungeon.py:73 |
| Turniej / Agility | 1200/400 $ / score·2 $ | sports2.py |
| Hipodrom | pula 3 × wpisowe (150 $), podział 60/30/10 | sports.py:20–22,63,106 |
| Pakiet startowy (dev) | +5000 $ | shop.py:20 |

**Sinki ($ wychodzi z gry)**

| Sink | Koszt | Źródło |
|---|---|---|
| Trening | 50 $ (−do 9% z Charyzmą) + 5 energii | economy.py:329 |
| Przedmioty | cena (−do 9% z Charyzmą) | economy.py:345 |
| Firmy | Café 2500, Studio 4000; rozbudowy wg COSTS | economy.py:9–11,59–62 |
| Rezydencje, pojazdy, ulepszenia aut, serwis | katalog (Raport 1) | economy.py:374–438 |
| Pracownicy | 250–500 $ / 24 h | economy.py:75–79 |
| Budynki dzielnicy | 500/1500/3000/6000; Sala Chwały 10 000 | economy.py:90–92 |
| Inwestycje w dzielnice | 100–5000 jednorazowo, max 20 000/dzielnicę | economy.py:142–143,456 |
| Podróż busem | 20 $ | travel.py:19 |
| Wpisowe sportowe | turniej 200, agility 50, łucznictwo 30, hipodrom 50 | sports2.py, sports.py:20 |
| Konie, hodowla | cena konia; hodowla 300 $ | sports.py:151,170 |
| Fundusz organizacji | 50–5000 na wpłatę | features.py:25 |
| Garderoba awatara | cena elementu | app.py (wardrobe) |

**Ryzyko ekonomii:** pula hipodromu (3 × wpisowe) jest większa od wpłat 1–2 graczy, więc część nagród powstaje z niczego (sports.py:63,106).

## 2.2 Energia

| Parametr | Wartość | Źródło |
|---|---|---|
| Limit | 240 | economy.py:225 |
| Start | 120 (test 240) | economy.py:183 |
| Regeneracja | (10 + regen rezydencji)/h × speed | economy.py:185,225 |
| Odpoczynek | +gain po czasie (do limitu 240) | economy.py:464–468 |
| Energiapak (dev) | +100, max 2/dobę UTC | shop.py:21 |

| Co zużywa energię | Koszt | Źródło |
|---|---|---|
| Kontrakt | `energy` z katalogu | economy.py:302 |
| Przetarg | jak kontrakt | economy.py:453 |
| Praca zdalna | 10 | economy.py:20 |
| Trening | 5 | economy.py:329 |
| Trening domowy | 12 | economy.py:336 |
| Wydobycie surowca | `mat.energy` | economy.py:266 |
| Loch (piętro) | 8 | dungeon.py:15 |
| Turniej | 30 | sports2.py |
| Agility | 15 | sports2.py |
| Łucznictwo | 10 | sports2.py |
| Pływanie | 10 | sports2.py |
| Trasy NPC, PvP, hipodrom, podróż | 0 (**BRAK** kosztu energii) | economy.py:471, pvp.py, sports.py |

## 2.3 EXP i poziomy

| Parametr | Wartość | Źródło |
|---|---|---|
| Poziom | `floor((1+√(1+8·xp/100))/2)` (krok kolejnego progu rośnie o 100 XP) | economy.py `level` |
| Zapis poziomu | nie jest zapisywany, liczony z xp | — |
| Maks. poziom | **BRAK** limitu | — |
| Źródła XP | kontrakty (×event), praca zdalna 25, trasy NPC, Loch 8+4·n, turniej 150/60/10, agility 12+score/2 | economy.py:317, dungeon.py:73, sports2.py |
| XP za PvP / trening | **BRAK** (trening daje +1 do statystyki) | economy.py:311 |
| Bramki poziomowe | PvP ≥2, Loch ≥3, hipodrom ≥5, ewolucja ≥10, poziom kontraktów/przedmiotów/aut/rezydencji z katalogu | pvp.py, dungeon.py:58, sports.py:19, features.py:302 |

## 2.4 Kontrakty

| Reguła | Wartość | Źródło |
|---|---|---|
| Koszt | tylko energia, bez $ | economy.py:302 |
| Wymagania | poziom; lokalizacja `d` (trzeba dojechać koleją) | economy.py:299–300 |
| Kolejka | max 4, sekwencyjnie | economy.py:301 |
| Skrócenie czasu | pojazd + Siła (0,4%/pkt, max 20) — łącznie max 50% | economy.py:303 |
| Wypłata | cena × kurs dnia zakończenia (0,85–1,15, ten sam dla świata) × (1 + min(15, inwestycje/1000) + Spryt·0,5 (max 25) + 4%·przystanki)% | economy.py:151,162–167 |
| VIP | +25% $ | economy.py:315 |
| Event czasowy | mnożnik `contract_cash` / `contract_xp` | economy.py:316 |
| Zużycie auta | +6 wear/kontrakt; przy 100 brak bonusu, potrzebny serwis | economy.py:318–320 |
| Przetarg dzienny | 1/dobę UTC, kontrakty ≥20 min, cena ×1,10–1,30, wygasa o północy UTC | economy.py:158–160, 447 |
| Praca zdalna | wymaga mieszkania, Ery II i 7 dni stażu; 1 naraz | economy.py:382–389 |
| Przyspieszenie (dev) | −50% trwającego zlecenia, 3/dobę | shop.py:22 |
| Blokady | w podróży nie działa | economy.py:261 |

## 2.5 Trasy NPC a kontrakty

| Cecha | Trasy NPC (0.56) | Kontrakty |
|---|---|---|
| Kto pracuje | kierowca NPC + auto z garażu | postać |
| Koszt | 0 $ i 0 energii | energia |
| Równoległość | sloty = poziom Rezydencji (1–5) | kolejka 4, sekwencyjna |
| Wymagania | auto w garażu, nie w innej trasie | poziom, lokalizacja |
| Wymagany poziom postaci / koszt trasy | **BRAK** | — |
| Nagroda | baza × VEH_MULT auta × (1 + 2%·(Garaż−1)) × event `route_cash` + XP | economy.py:137–139,481–492 |
| Offline | tak (odbiór `route_claim` zbiorczo) | economy.py:481 |
| Blokada podróży | nie dotyczy | — |

## 2.6 Idle — Kawiarnia (i inne firmy)

| Parametr | Wartość | Źródło |
|---|---|---|
| Corner Café | od poziomu 2, cena 2500 $ | economy.py:60 |
| Stawka $/h (poziom 1–4) | 30 / 45 / 65 / 90 | economy.py:10 |
| Rozbudowy | 1500 / 3500 / 7000 $, 10 min ×(−10%/poziom Szybkiej Budowy) | economy.py:11,371 |
| City Courier (start) | 40/55/75/100/135/175/225 $/h; koszty 1000…24000 | economy.py:8–9 |
| Studio Forma | od poziomu 3, 4000 $; 55/80/115/160 | economy.py:61 |
| Limit skarbca | 24 h × stawka × (1 + Siła·2%, max 40%) | economy.py:194,226 |
| Barista | 250 $ → +25% na 24 h | economy.py:77 |
| Era I | firmy max do poziomu 2 | economy.py:368 |
| Odbiór | tylko w dzielnicy 2 (Zakłady Miejskie) | economy.py:295 |
| Anti-cheat | stan liczony na serwerze; `lastTick=max(lastTick, now)` (cofnięcie zegara nic nie daje); idempotencja operacji (tabela `operations`); rate-limity | economy.py:225, app.py |
| Anti-cheat klienta (automaty, boty) | **BRAK** | — |

## 2.7 Walka

**Klasy** (combat.py:28–39): Bokser (+2 mocny cios), Obrońca (kontra 40% po uniku), Szybki (+3 inicjatywy, +1 szybki cios). Ewolucje od 10 poziomu: zelazna-piesc, mistrz-ringu, blyskawica, zelazny-straznik, murarz-ringu, nokaut-fantom (features.py:300–315).

**Walka 1.0** (sparing i Loch, `combat.fight`):

| Element | Formuła |
|---|---|
| Statystyka efektywna | `10+10·ln(x/10)` |
| HP | `500+10·Charyzma` |
| Obrażenia | `50+Siła+0,2·Spryt`, ×0,85–1,15 |
| Redukcja | ×`60/(60+Inteligencja)` |
| Kryt | `0,05+0,6·t/(t+40)`, ×2 |
| Trafienie / inicjatywa | z Refleksu (z clampami) |
| Taktyka (BEATS) | ×1,08 |
| Limit | 100 rund |
| Seed | `secrets.randbits(32)` |

**PvP 2.0 / Turniej / Loch** (`combat.simultaneous`):

| Element | Formuła |
|---|---|
| Rundy | 3, sekwencja 3 akcji: unik / mocny_cios / szybki_cios |
| HP | `80+1,5·Charyzma` |
| Szybki cios | `5+0,45·Siła` (+1 Szybki) |
| Mocny cios | `9+0,75·Siła` (+2 Bokser) |
| Unik | blokuje cios; Obrońca kontruje 40% szybkiego |
| Zderzenia | szybki na szybki ×0,55; mocny na mocny ×0,8 |
| Wynik | więcej HP; przy remisie wyższa inicjatywa (Refleks); w praktyce deterministyczny |

## 2.8 PvP

| Reguła | Wartość | Źródło |
|---|---|---|
| Wymagania | poziom ≥2 i ustawiona taktyka | pvp.py |
| Cele | top 20 wg ratingu (rating zaokrąglony do 10) | pvp.py |
| Limit dzienny | 5 walk rankingowych / dobę UTC (`ranked_usage`) | app.py daily_limit |
| Cooldown pary | ta sama para max raz na 24 h (`matches`) | app.py pair_limit |
| Blokady | w podróży, cel zbanowany, blokada kontaktu | pvp.py |
| Rating | Elo, K=24: `E=1/(1+10^((Rt−Ra)/400))`, `Δ=24·(wynik−E)` | pvp.py:88–90 |
| Obrona | zapisana sekwencja `pvpDefense` (obrońca offline) | pvp.py |
| Nagrody $/XP za PvP | **BRAK** (tylko rating i W/L/R) | pvp.py |
| Sezony | archiwum `season_archive`, ranking globalny sezonowy | app.py |

## 2.9 Gildie (organizacje / sojusze)

| Reguła | Wartość | Źródło |
|---|---|---|
| Członkostwo | 1 organizacja na postać | features.py:326 |
| Max członków | 20 | features.py:341,361,376,394 |
| Max organizacji / świat | 200 | features.py:327 |
| Nazwa / skrót | 3–32 znaki / 2–5 A–Z0–9, unikalne | features.py:322 |
| Koszt założenia | **BRAK** | features.py:320 |
| Role | leader, officer, member | features.py:36–38 |
| Lider | nadaje role, przekazuje przywództwo; odejście tylko jako ostatni członek (wtedy organizacja jest usuwana) | features.py:536–553,560 |
| Oficer (i lider) | zaproszenia, rozpatrywanie podań, usuwanie członków, ogłoszenia, kontrakty org., inwestycje funduszu, budynki sojuszu | features.py:229 (`officer`) |
| Członek | wpłata do funduszu, czat organizacji, odejście | features.py:423 |
| Fundusz | wpłata 50–5000 $ z gotówki postaci | features.py:25,423–431 |
| Budynki sojuszu | Szybka Budowa −10%, Tanie Naprawy −15%, Wolność −10% podróży na poziom; max 3; koszt 2000/5000/10000 z funduszu | economy.py:104–112 |
| Kontrakty org. | prestiż (100–20 000, dzielnica) / zbiórka (200–50 000), 24–168 h, 1 aktywny; status done/missed | features.py:31–35,502–509,163–180 |
| Nagroda za kontrakt org. | **DO WERYFIKACJI** (kod zmienia tylko status) | features.py:172 |
| Podania | tekst 10–200; limit 5/h | features.py:22–24,369 |

## 2.10 Terytoria i wpływy

| Reguła | Wartość | Źródło |
|---|---|---|
| Dzielnice inwestycyjne | Zakłady Miejskie, Centrum, Portowe, Biznesowe, Sportowe, Lasy Wschodnie | economy.py:80 |
| Wpływ organizacji | inwestycja funduszu 100–5000 na raz | features.py:26–28,437–447 |
| Przejęcie | dzielnica należy do organizacji z największą sumą `org_investments`, przy remisie niższe id | features.py:134–144 |
| Historia | `territory_log`, audyt `territory.claim` | features.py:142 |
| Prywatny wpływ gracza | +1% $ z kontraktów w dzielnicy na 1000 $ (max 15%) + Spryt | economy.py:162 |
| Bonus ekonomiczny za posiadanie terytorium | **BRAK** (tylko prestiż i wyświetlanie) | app.py:276 |
| Zanik wpływów | **BRAK** | — |

## 2.11 Czat

| Reguła | Wartość | Źródło |
|---|---|---|
| Kanały | `world` i `organization` | features.py:232–235 |
| DM | osobne wątki, 30/h na postać (rate 60/h) | features.py:646,653 |
| Długość | 1–300 znaków | features.py:47–48 |
| Limit | 40 wiadomości/h na konto, min 3 s odstępu | features.py:590–591 |
| Idempotencja | `client_id` (ponowienie nie dubluje) | features.py:585 |
| Wyciszenie | `chat_mutes` (do czasu) | features.py:589 |
| Zgłoszenia | `reports` (12/h) → kolejka staff (wyciszenie/ban/odrzucenie) | features.py:597 |
| Blokady | `social_blocks` (blokują też PvP i DM) | features.py |
| Odwołania | 1/24 h, rozpatruje staff | features.py:721 |
| Automatyczny filtr wulgaryzmów | **DO WERYFIKACJI** (`text()` normalizuje treść) | features.py:582 |

## 2.12 Sklep (dev)

| SKU | Cena | Działanie | Limit |
|---|---|---|---|
| vip30 | 19,99 zł | VIP 30 dni (+25% $ z kontraktów, rama) | sumuje się |
| vip7 | 7,99 zł | VIP 7 dni | sumuje się |
| starter | 9,99 zł | 5000 $, 3 przedmioty, natychmiastowy odpoczynek | raz na konto |
| energy | 4,99 zł | +100 energii | 2/dobę UTC |
| speedup | 2,99 zł | −50% trwającego zlecenia | 3/dobę UTC |
| skin_copper / skin_gold / skin_neon | 3,99 / 5,99 / 9,99 zł | kosmetyka | raz |

Źródło: shop.py:17–26. **8 SKU** (wcześniejsze „6 produktów” liczyło skórki jako 1 pozycję — DO WERYFIKACJI z GDD).

| Zasada | Wartość | Źródło |
|---|---|---|
| Płatności | **BRAK realnych** — `paid_dev`; w produkcji Play Billing / Apple IAP | shop.py:28 |
| Domyślnie | zakupy wyłączone (`spending_enabled=0`) | shop.py:32 |
| Bramka | oświadczenie 16+ albo zgoda opiekuna; `minor=true` wymaga zapisanej zgody | shop.py:29,139 |
| Zgoda opiekuna | imię + limit tygodniowy 500–20 000 gr (5–200 zł); jedna aktywna; możliwe cofnięcie | shop.py:36,49,151 |
| Limit tygodniowy | suma `cents` od początku tygodnia UTC + cena ≤ limit | shop.py:77,197 |
| Rate | checkout 10/h | shop.py:178 |
| Lootboxy | **BRAK** (świadomie) | — |

## 2.13 Dyscypliny sportowe

| Dyscyplina | Wymagania | Koszt | Zasady | Nagroda | Limit | Źródło |
|---|---|---|---|---|---|---|
| Sparing bokserski (ring) | taktyka | 0 | wyzwanie gracza, walka 1.0 (challenges/accept) | rating | 5 rankingowych/dobę, para 1/24 h | app.py, combat.py |
| Turniej bokserski | — | 200 $ + 30 energii | 3 walki z NPC (PvP 2.0) | 3/3: 1200 $ + 150 XP; 2/3: 400 $ + 60 XP; mniej: 10 XP | 2/dobę, rate 10/h | sports2.py |
| Agility psów („wystawa”) | — | 50 $ + 15 energii | score `30+(R−10)·0,8+(Spryt−10)·0,6+los`, 10–120, oceny A–E | XP `12+score/2`, $ `score·2` | rate 20/h | sports2.py |
| Łucznictwo | — | 30 $ + 10 energii | wynik 0–30 z Int i Refleksu vs rekord rywala z top 20 (brak = 14) | tylko bilans W/R/P, **BRAK $/XP** | rate 20/h | sports2.py |
| Pływanie | — | 10 energii | kondycja +6–12 (max 30), okno 48 h | +Charyzma `min(5, kondycja/6)` | rate 30/h | sports2.py |
| Hipodrom — NPC | poziom 5, dzielnica 6, koń | 50 $ | wyścig z 2 NPC | pula 150 $: 90/45/15 | rate 20/h | sports.py:18–22,195 |
| Hipodrom — pojedynek | jw. | 50 $ (obaj gracze) | otwarty wyścig, 1 naraz, możliwe odwołanie ze zwrotem | pula 150 $: 60/30/10 | rate 10/h | sports.py:212–255 |
| Hodowla koni | 2 konie | 300 $ | źrebak gen+1 (speed/stamina z rodziców) | nowy koń | 1/24 h | sports.py:159–181 |
| Loch (10 pięter) | poziom 3, taktyka | 8 energii | PvP 2.0 vs boss piętra | 30+30·n $, 8+4·n XP; unikaty na p. 3/6/10 | rate 30/h | dungeon.py:15–17,52–82 |
| Obstawianie zakładów | — | — | — | **BRAK** (świadomie) | — | — |
