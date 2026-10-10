# Raport: Etap 4 (budynki, idle, Buffet, RESET), migracja do GDD v3.1

Gałąź `feature/gdd-v31-migration`, od `ae6972c` (koniec Etapu 3) do `ee69294`. Zmiany tylko w backendzie: 18 plików, +562 / −77 linii.

## Commity
| commit | zadanie |
|---|---|
| `778e28d` | 4.1–4.3: 6 budynków, Kawiarnia lvl 10 (24 h), Klub Nocny lvl 7 (72 h), usunięcie Corner Café i Siłowni |
| `9fd448e` | E2E: bramka Sali Chwały przez API, brak zakupu Corner Café |
| `ee69294` | 4.4–4.5: Buffet w Rezydencji i prestiżowy RESET w Sali Chwały |

**Odstępstwo od zasady „jedna zmiana = jeden commit”:** 4.1 z 4.2–4.3 oraz 4.4 z 4.5 trafiły do wspólnych commitów. Te zmiany przeplatają się w tych samych hunkach `economy.py`, `npc.py` i `app.py`, więc rozdzielenie byłoby sztuczne i ryzykowne.

## Testy
- **pytest: 390 passed** (Etap 3 kończył się na 373).
- **Nowe pliki testów:** `test_buildings_v2.py` (8), `test_buffet.py` (5), `test_reset.py` (4).
- **E2E: 36/36 PASS, bez powtórek.** Seria szła w dwóch połowach, żeby reset sandboxa nie przerwał całości.

## 4.1–4.3 (zaakceptowane wcześniej)
Szczegóły są w `PROJEKT-ETAP-4.1-4.3.md`.

**Zmiana w E2E `test-online`:** zakupu Studio Forma nie dało się zrobić, bo postać testowa nie ma wymaganego 3. poziomu. Test sprawdza więc teraz, że przycisku zakupu Café nie ma. Zmiana dotyczy tylko testu, bez JS.

## 4.4 Buffet w Rezydencji
- **`upgrade_buffet`** (akcja w `/actions`): wymaga Rezydencji na poziomie ≥ 2. Koszty poziomów 1/2/3 to **1500 / 4000 / 10 000 $** (moja propozycja, GDD ich nie podaje). Stan trzymam w `s['buffet']`.
- **Posiłki** (zgodnie ze specyfikacją):

| poziom | posiłek | koszt | sytość | nastrój | energia |
|---|---|---|---|---|---|
| 1 | Zwykłe jedzenie | 10 $ | +15 | – | – |
| 2 | Dobre jedzenie | 25 $ | +25 | +5 | – |
| 3 | Premium catering | 60 $ | +40 | +15 | +5 |

  Wartości obcinam do 100. Domyślnie wybierany jest najlepszy posiłek dostępny w Buffecie. Posiłek jest możliwy, gdy sytość < 100.
- **`POST /api/worlds/{wid}/npcs/feed {npc_id, meal?}`** to nowe `feed_npc`.
  - Masowo: batch `action="all_to_buffet"` (+ `meal?`); stare `feed` działa jako alias.
  - Stary `POST /npcs/{id}/feed` zostaje dla zgodności, ale działa na zasadach Buffetu.
- **Przemęczenie:** jeśli jego jedyną przyczyną był głód (energia i nastrój ≥ 30), a po posiłku sytość ≥ 30, przemęczenie znika od razu. Przy innej przyczynie obowiązuje dotychczasowy próg 40.
- **AI Manager** zamawia najlepszy posiłek z Buffetu. Bez Buffetu nie karmi.
- **Asystent** w alercie „głodny” podaje posiłek i cenę albo radzi zbudować Buffet.

**⚠️ Skutek do Twojej decyzji:** bez Buffetu, czyli przy Rezydencji lvl 1, NPC **nie da się nakarmić**. Wcześniej prowizorka za 30 $ działała zawsze. Nowy gracz musi więc rozbudować Rezydencję (500 $) i kupić Buffet (1500 $), zanim nakarmi pierwszych NPC. Jeśli to za ostre, mogę dać „Zwykłe jedzenie” bez Buffetu.

## 4.5 Sala Chwały i prestiżowy RESET
- Bramka Sali Chwały pochodzi z 4.1: wszystkie budynki na max + 10 000 $.
- **`POST /api/worlds/{wid}/server_reset {confirm_text?}`**. Serwer pilnuje wszystkich trzech kroków:
  1. **Bez `confirm_text`:** zwraca podsumowanie (numer resetu, bonus po resecie, Punkty Prestiżu, diamenty, liczba NPC, listy „zeruje / zachowuje”) i uzbraja reset.
  2. **`confirm_text`** musi brzmieć dokładnie „RESET POTWIERDZAM”, inaczej 422.
  3. **Wykonanie** najwcześniej **10 s** po kroku 1 (inaczej 409 „Odczekaj jeszcze X s”), najpóźniej 10 min.
- **Zeruje:**
  - gotówkę do kwoty startowej (300 $);
  - budynki (w tym Salę Chwały i Buffet) i skarbce;
  - NPC (usuwani z bazy razem z trwającymi zmianami);
  - auta (z Mistrzem) i tabelę `vehicles`;
  - konia i stajnię;
  - statystyki do [10×5] i ewolucję (`class_evolution=1`);
  - AI Managera, personel firm i licznik dyspozytora.
- **Zachowuje:** awatar i kosmetyki, VIP (`shop_state`), stan nieznanych kluczy (pod przyszły Battle Pass), Punkty Prestiżu, a także XP i poziom, ekwipunek, firmy, ranking i tytuły.
- **Diamenty:** `s['diamonds']` trafia do `accounts.premium_currency`.
- **Nagrody:**
  - `accounts.prestige_points` +1;
  - stały bonus dochodu +10% za każdy reset, maksymalnie +50%, zapisany w `s['prestige']`;
  - ramka `s['frame']='reset-N'` i tytuł „Reset #N”.
- **Bonus dochodu** obejmuje kontrakty, odbiory skarbców (firmy, Kawiarnia, Klub Nocny) i wypłaty NPC.
- **Ślady:** kronika miasta (`server_reset`), audyt (`server.reset`), powiadomienie `prestige.reset`, historia w nowej tabeli `server_resets`.
- **Schemat:** migracja addytywna, `accounts` dostaje kolumny `premium_currency` i `prestige_points` (DEFAULT 0).

**Do Twojej decyzji:**
1. **Co zostaje po resecie:** XP i poziom, ekwipunek, firmy (kurier, Studio), ranking i tytuły. Specyfikacja ich nie wymienia, więc ich nie zeruję. Pełny „nowy start” od lvl 1 to zmiana jednej funkcji (`wipe`).
2. **Gotówka po resecie:** wraca do kwoty startowej 300 $, a nie do 0.
3. **Psy:** w grze nie są posiadanym zasobem (występują tylko w opisie toru agility), więc nie ma czego zerować.
4. **Battle Pass i diamenty:** jeszcze nie istnieją (Etap 8, flaga premium wyłączona). Mechanizm przeniesienia diamentów jest gotowy i przetestowany na `s['diamonds']`.
5. **Brak idempotencji:** endpoint resetu nie korzysta z mechanizmu kluczy idempotencji. Krok 3 jest jednak jednorazowy: po resecie Sala Chwały jest wyzerowana, więc kolejne wywołanie zwraca 409.

## Stary web (zostaje do Fluttera, bez zmian w JS)
Nie ma widoków Buffetu, Klubu Nocnego ani Resetu. Karta Siłowni wisi bez poziomu, a przycisk Sali Chwały działa według starej bramki. Wszystkie nowe funkcje są dostępne wyłącznie przez API.
