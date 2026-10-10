# PROJEKT — Combat 3.0 (do akceptacji, kod NIE jest jeszcze pisany)

> Status: **ZATWIERDZONY (D1–D5) i WDROŻONY** — `server/combat.py` ENGINE 3.0, backup `combat.py.backup_v23`.
> Liczby poniżej pochodzą z prototypu `online/tools/combat3_sim.py` (osobny skrypt, serwer go nie importuje).
> Symulacja: 300–2000 walk na każdą parę, deterministyczny seed.

> ⚠️ **Długiej specyfikacji walki z jednej z wcześniejszych wiadomości nie ma w kontekście, który mam dostępny.**
> Projekt opiera się na 7 wytycznych z Twojej ostatniej wiadomości. Jeśli tamta specyfikacja mówi coś innego
> (nazwy akcji, wzory, liczby), wklej ją ponownie, a dopasuję projekt przed pisaniem kodu.

---

## 1. Co się zmienia — w skrócie

| Obszar | Teraz (2.3) | Combat 3.0 |
|---|---|---|
| Wybór ruchu | RPS: Presja / Kontrola / Kontra wg klasy | **usunięty** — każda akcja to niezależne rzuty |
| Obrażenia | wzór ze Siły | **zakres broni (Rękawice)** × Siła |
| Losowość | sekwencje + bonus przewagi | osobny rzut na: unik, blok, crit, obrażenia |
| Efekty | brak | **StatusEffects** (np. `nextAttackDamageBonus`) |
| Koniec walki | limit rund | **Fatigue od 21. rundy**, gwarantowany KO |

## 2. Broń — slot Rękawice daje zakres obrażeń

| Rękawice | Zakres DMG |
|---|---|
| gołe pięści (brak) | **15–25** |
| Podstawowe | 20–30 |
| T1 (szare) | 30–45 |
| T2 (zielone) | 45–65 |
| T3 (niebieskie) | 65–90 |
| T4 (fioletowe) | **85–115** |

Wzór: `dmg = U(min,max) × (1 + 0.02 × Siła)`. Przykład: Siła 30 daje ×1.6.
Bonusy statystyk z Rękawic (np. 💪+4) zostają bez zmian.

## 3. Przebieg rundy

1. **Inicjatywa** (rzut co rundę): `Refleks + U(0,20)`. Szybki dostaje +5. Kto ma więcej, uderza pierwszy. Każdy wykonuje 1 akcję na rundę.
2. **Typ ciosu** (rzut): `PUNCH_HEAVY` ×1.6 z szansą wg klasy (Bokser 1/6, pozostali 1/10). W przeciwnym razie `PUNCH_FAST`.
3. **Reakcja obrońcy** (niezależne rzuty, po kolei):
   - **Unik** `DODGE_SIDE`: `10% + 50% × (Ref_o − Ref_a)/(Ref_o + Ref_a)`. Szybki dostaje +8 pp. Zakres 3–40%. Unik oznacza 0 obrażeń.
   - **Blok** `GUARD_BLOCK`: `15% + 50% × (Int_o − Siła_a)/(Int_o + Siła_a)`, zakres 5–40%. Obrażenia ×0.5.
   - W pozostałych przypadkach `TAKE_HIT`.
4. **Crit** (osobny rzut): `5% + 0.3% × Spryt` plus stosy Szybkiego. Crit mnoży obrażenia ×1.75 (`CRITICAL_HIT`).
5. **Obrażenia** (osobny rzut z zakresu broni), następnie modyfikatory klasy, StatusEffects i Fatigue.
6. **Przewaga statystyk** z balansu 2.3 zostaje: współczynnik `keff` tłumi szanse uniku i bloku słabszego gracza.

## 4. Klasy

| Klasa | Mechanika (zgodnie z wytycznymi) | Dodatki z balansu prototypu |
|---|---|---|
| 🥊 **Bokser** | **1/6 szansy na Mocny Cios** (×1.6). Ewolucje podnoszą tę szansę | pasywnie +12% obrażeń; bez tego Bokser przegrywał z obiema klasami |
| 🛡️ **Obrońca** | **−20% otrzymywanych obrażeń**. **1/8 szansy na Kontrę** (`KNEE_STRIKE`, 60% ciosu) po udanym bloku | blok −5 pp; bez tego wygrywał 95% walk z Bokserem |
| ⚡ **Szybki** | **30% szansy na Kontrę po uniku**. Każde trafienie +5% do critu (max +25%), stos zeruje się po cricie | unik +8 pp, inicjatywa +5 |

### StatusEffects (lista per zawodnik, zapisywana w raporcie walki)
- `nextAttackDamageBonus` +20%: po udanym bloku (każda klasa), zużywa się przy następnym ciosie.
- `critStacks`: stosy Szybkiego.
- Format: `{id, value, turns|null}`, więc łatwo dodawać kolejne (np. ogłuszenie).

### Ewolucje: mapowanie na nowe parametry (propozycja)
| Ewolucja | Efekt w 3.0 |
|---|---|
| Bokser I: zelazna-piesc / mistrz-ringu | Mocny Cios 1/6 → 1/4 / +8% obrażeń po każdym trafieniu z rzędu (max 3) |
| Bokser II: czempion / niszczyciel | HP +12% / Mocny Cios ×1.6 → ×1.9 |
| Obrońca I: murarz / zelazny-straznik | redukcja 20% → 28% / Kontra 1/8 → 1/5 |
| Obrońca II: bastion / mistrz-riposty | blok +8 pp / Kontra 100% → 150% obrażeń |
| Szybki I: blyskawica / nokaut-fantom | Kontra po uniku 30% → 42% / unik +6 pp |
| Szybki II: cien / zabojca | inicjatywa +5, stos critu 5 → 7% / crit ×1.75 → ×2.1 |

## 5. Fatigue
- Od **21. rundy**: otrzymywane obrażenia ×`(1 + 0.10 × (runda − 20))`.
- Jednocześnie szanse uniku i bloku spadają o 10 pp na rundę.
- Po 30. rundzie obrona wynosi 0, a obrażenia są podwójne, więc walka zawsze kończy się KO. Remisy znikają, poza obustronnym KO w tej samej wymianie.

## 6. Wyniki symulacji (prototyp po strojeniu)

**Równe statystyki 20, gołe pięści** (wiersz atakuje, % wygranych / średnio rund):

| | vs Bokser | vs Obrońca | vs Szybki |
|---|---|---|---|
| Bokser | 52% / 23 | 38% / 26 | 41% / 24 |
| Obrońca | 64% / 26 | 49% / 29 | 55% / 27 |
| Szybki | 58% / 24 | 45% / 27 | 49% / 25 |

Wszystkie pary mieszczą się w przedziale 36–64%. To nie jest sztywny cykl jak w RPS, tylko lekkie przewagi.

**Przewaga statystyk** (najgorsza para klas): staty ×1.25 dają 91% wygranych, ×1.5 dają 99,8%, ×2 dają 100%. Warunek „×2 = pewna wygrana” jest spełniony.

**Broń przy równych statach** (Bokser vs Bokser):

| | Wygrane | Średnio rund |
|---|---|---|
| T1 vs gołe pięści | 100% | 13,5 |
| T2 vs T1 | 95% | 9,4 |
| T4 vs T3 | 77% | 5,3 |

HP przyjęte w prototypie: `500 + 10 × Charyzma + 8 × lvl`.

⚠️ **Ostrzeżenie:** przy tych zakresach broń dominuje nad statystykami, a walki T3/T4 są krótkie (około 5 rund). Proponuję jedno z dwóch (decyzja **D2**):
- **(a)** skalować HP z tierem zbroi, np. pozostałe sloty seta dają HP;
- **(b)** spłaszczyć zakresy, np. T4 = 55–75.

## 7. Wpływ na resztę systemu
- `server/combat.py`: nowy silnik `ENGINE='3.0'`, napisany od nowa. Stary plik zostaje jako backup (`combat.py.backup_v23`).
- Stare raporty walk mają pole `engine` i dalej się wyświetlają.
- PvP (`pvp.py`), Boks/MMA, Ring/Loch (NPC dostają „broń” wg piętra) i turnieje używają tego samego silnika.
- Raport walki zachowuje dotychczasowe klucze (`attacker_action`, `defender_reaction`, `result`, `damage`, `hp`). Dochodzą `rolls` (rzuty), `effects` i `fatigue`. Ekran walki we Flutterze dostaje drobne rozszerzenie: zakres broni i ikony efektów.
- Pole „taktyka” zostaje jako nazwa klasy. RPS (`CLASS_BEATS`, bonus przewagi taktyki) usuwamy. Migracja bazy nie jest potrzebna.
- Seed losowania jest zapisywany w raporcie, więc każdą walkę można odtworzyć (testy i spory).
- Testy: przepisanie testów walki; nowe testy determinizmu, Fatigue (KO ≤ 40 rund), ×2 stat = 100% i macierzy klas 30–70%.

## 8. Decyzje do podjęcia
- **D1:** Akceptujesz dodatki balansowe: Bokser +12% obrażeń, Obrońca −5 pp bloku, stos critu Szybkiego 5%/25%?
- **D2:** Dominacja broni: (a) HP ze zbroi, (b) płaskie zakresy, czy (c) zostawić tak jak jest?
- **D3:** Mapowanie ewolucji z tabeli w sekcji 4: OK?
- **D4:** Fatigue: +10% na rundę od 21. rundy. OK?
- **D5:** Wklejasz ponownie długą specyfikację (jeśli coś w niej się różni), czy działam według tego projektu?

---

## 9. Wdrożenie — parametry ostateczne (po kalibracji na prawdziwym silniku)

| Parametr | Wartość |
|---|---|
| HP | `300 + 6×Charyzma + 6×lvl + HP pancerza` (Czempion ×1,12) |
| Pancerz/biżuteria — na część (D2 a) | T1 +30 HP / 1% DEF · T2 +60 / 1,5% · T3 +100 / 2% · T4 +150 / 2,5% · stare przedmioty +15 HP · cap DEF 35% |
| Broń | jak w sekcji 2 (stare rękawice sklepowe 25–35) |
| Fatigue | od 21. rundy: obrażenia +10%/rundę, unik i blok −10 pp/rundę (D4) |

**Wyniki na silniku 3.0** (lvl 15, staty 20): macierz klas 45–63% · walki obu stron w setach T3 ≈ 11,7 rundy, T4 ≈ 12,2 rundy (cel 8–15 ✅) · ×2 statystyk = 100% · KO zawsze ≤ 40 rund.

**Loch (decyzja wdrożeniowa):** statystyki NPC są strojone pod progresję pięter, więc NPC walczy **bronią tego samego tieru co gracz**;
przewagę dają pancerz gracza i ewolucje, boss dostaje 3 części pancerza. Efekt: równe staty ≈ 40% (boss ≈ 20–30%), staty +20% ≈ 75–100%.
Wariant „broń NPC wg poziomu” odrzucony — boss 10. piętra był nie do pokonania nawet przy 3× lepszych statach.
**Turniej:** rywal w lustrzanym ekwipunku gracza. **PvP i wyzwania rankingowe:** ekwipunek obu stron.
