# Raport Etap 6: Lochy [GDD v3.1 6.1–6.4]

Gałąź `feature/gdd-v31-migration`, commity `6c13de7` (backend + pytest) i `1ef9ddb` (E2E). Backup: `server/dungeon.py.backup_v059`.
Zmienione pliki: `server/dungeon.py` (+237/−51), `server/app.py` (allowlista GET), `tests/test_dungeon.py`, nowy `tests/test_dungeon_v6.py`, `tests/test-dungeon.cjs`.

> Uwaga: 6.1–6.4 to jeden plik i wspólna pętla walki, więc backend wszedł jednym commitem zamiast czterech. Mogę go rozbić, jeśli trzeba.

## 6.1 Normal (Ring), 10 serii × 10 pięter
- Serie: Kanały, Doki, Złomowisko, Metro, Hale Targowe, Elektrownia, Wieżowce, Katakumby, Lodownia, Wulkan.
- Seria 1 to oryginalne 10 pięter (zgodność wsteczna, w tym unikaty i Hełm Lochu na 9).
- Wymagany poziom 3, koszt 8 energii.
- **Interpretacja do potwierdzenia:** „PvP Lvl 3” rozumiem jako poziom postaci, tak jak bramka z 0.41.
- Piętra liniowe, bez powtórek. Po 100. piętrze odpowiedź 409 „opanowany”.
- **Drop:**
  - zwykli przeciwnicy mają 10% szansy, bossowie (pozycje 3, 6, 10) 100%;
  - pula to tylko przedmioty zestawu ze sklepu i unikaty, bez akcesoriów, plecaka i kuponów;
  - boss losuje z górnej połowy puli według sumy bonusów;
  - losowanie jest deterministyczne (sha256 z postaci, trybu i piętra), więc ponowna próba po porażce nie zmienia wyniku;
  - duplikat trafia do `s['backpack']`, bez zamiany na $.
  - W teście 63 zwykłych pięter dało liczbę dropów w paśmie ~10%.
- **Progres:** `dungeon_progress` = piętro Normal, czyli 1 piętro = 1%. Stare konta (0.31–0.59) są przeliczane leniwie: piętro = stary % / 10.

## 6.2 Hard, 2 × 10
- Serie Stalowa Arena i Czarny Ring; wymagany poziom 7, koszt 15 energii.
- Każde piętro daje $ i XP.
- Bossowie dają kosmetykę do `s['cosmetics']`:
  - pozycja 3: `npc-outfit-hard-N`;
  - pozycja 6: `car-skin-hard-N`;
  - pozycja 10: ramka `dungeon-hard-N` w `s['frames']`.
- Kosmetyka nie wpływa na statystyki i zostaje po resecie.

## 6.3 Nightmare, 3 × 10
- Serie Koszmar, Otchłań, Zaćmienie; wymagany poziom 15, koszt 25 energii.
- **Nagrody od bossów:**
  - pozycja 3: pies premium do `s['dogs']` (kolekcja, bez mechaniki);
  - pozycja 6: koń premium do istniejącej stajni (hodowla działa);
  - pozycja 10: pies i koń „Legenda”.
- Konie premium mają szybkość i wytrzymałość 7+s (Legenda +1), więc są lepsze od Czempiona (6/6).

## 6.4 Historia i silnik
- Kolumny `dungeon_normal/hard/nightmare` (najwyższe piętro w trybie) są dodawane migracją kompatybilną wstecz.
- Tabela `dungeon_runs` trzyma ostatnie 200 prób na postać.
- **Endpointy:**
  - `POST /dungeon/floor {mode}`;
  - `GET /dungeon/history`: rekordy, liczba prób i wygranych w każdym trybie, lista prób;
  - `GET /dungeon/runs/{id}`: pełny raport rund dla Fluttera; cudza próba zwraca 404.
- Walki idą na silniku 2.0 (`simultaneous`, `exchanges` w rundach), HP = 200 + 5·Cha + 2·Lvl.
- `state.dungeon.modes` podaje dla każdego trybu: best, locked, nextFloor.

## Balans do akceptacji
| Tryb | Mnożnik siły serii s | Poziom NPC dla piętra f | $ za piętro | XP za piętro |
|---|---|---|---|---|
| Normal | 1+0.35(s−1) | 2f (f≤10), potem 10+f | 30+30f | 8+4f |
| Hard | 2.0+0.6(s−1) | 30+2f | 400+200f | 80+25f |
| Nightmare | 3.4+0.8(s−1) | 60+2f | 1500+600f | 250+50f |

Suma statystyk NPC: Normal od 31 (piętro 1) przez 93 (piętro 10) do 386 (piętro 100); Hard od 62 do 242; Nightmare od 105 do 465.

## Testy
- **pytest:** 410 passed, w tym 6 nowych w `test_dungeon_v6.py`: struktura, bramki i energia, pula i boss, ~10% i plecak, kosmetyka i zwierzęta, historia i silnik. Wcześniej było 404.
- **E2E:** wynik w sekcji niżej. `test-dungeon.cjs` sprawdza teraz pasek 1%.
- Frontend vanilla JS nie był zmieniany (UI trybów i historii będzie we Flutterze).

## Wynik E2E
36/36 PASS. `test-dungeon` za pierwszym razem nie przeszedł, bo czekał na `progress===10`. Po poprawce na 1 przechodzi; poprawka weszła do commita E2E.
