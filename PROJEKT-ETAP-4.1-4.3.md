# Projekt: Etap 4.1–4.3 (budynki dzielnicy i skarbce idle), GDD v3.1

**Status:** zmiany są w working tree **bez commita** i czekają na akceptację. Pełny diff serwera jest w `DIFF-ETAP-4.1-4.3.patch`.
Pliki: `server/economy.py`, `server/app.py`, 5 poprawionych testów i nowy `tests/test_buildings_v2.py` (8 testów).

## Decyzje usera (ankieta)
| temat | decyzja |
|---|---|
| Bramka Sali Chwały | każdy budynek na swoim maksimum: Rezydencja 5, Garaż 5, Kawiarnia 10, Klub Nocny 7, Sala Klubowa 1 |
| Corner Café | usunięta, zostaje tylko budynek Kawiarnia |
| Siłownia | znika jako budynek, bez zwrotu |
| Odbiór skarbców | z dowolnego miejsca |

## 4.1 Sześć budynków
```
BUILDINGS      = residence, garage, cafe, nightclub(NOWY), club, hall      ('gym' usunięty)
BUILDING_START = residence 1, garage 1, cafe 1, nightclub 0, club 1, hall 0
BUILDING_MAXES = residence 5, garage 5, cafe 10, nightclub 7, club 1, hall 1
```
**Koszt wejścia na kolejny poziom** (indeks = obecny poziom):

| budynek | koszty |
|---|---|
| Rezydencja, Garaż | bez zmian: 500 / 1500 / 3000 / 6000 |
| Kawiarnia | 500 / 1500 / 3000 / 6000 / 10 000 / 16 000 / 25 000 / 38 000 / 55 000 (razem 155 000 $) |
| Klub Nocny | **budowa 5000 $**, potem 4000 / 8000 / 15 000 / 25 000 / 40 000 / 60 000 (razem 157 000 $) |
| Sala Klubowa | max 1, bez rozbudowy |

⚠️ Kwoty Kawiarni 6–10 i całego Klubu Nocnego to **moja propozycja**, bo GDD ich nie podaje. Zwrot inwestycji przy Klubie lvl 1 to ok. 62 h, a każdy kolejny poziom zwraca się w 2–3 dni gry.

**Bramka Sali Chwały:** wszystkie 5 budynków na swoim maksimum + 10 000 $. Kto już ma otwartą Salę, zachowuje ją.

**Leniwa migracja w `sync()`** (idempotentna, bez flagi wersji):
- `gym` usunięty ze stanu, bez zwrotu;
- `club` przycięty do 1, bez zwrotu (ta sama zasada co przy Siłowni);
- **Corner Café:** niezebrany skarbiec trafia do gotówki, a poziom budynku Kawiarnia = max(poziom budynku, poziom Café). Opłata za zakup Café (2500 $) nie wraca.
- dochodzi `s['vaults'] = {cafe, nightclub}`.

## 4.2 / 4.3 Skarbce idle
Stawki $/h per poziom rosną geometrycznie od wartości z GDD:
```
Kawiarnia  (24 h): 30 41 55 75 101 137 186 252 342 465
Klub Nocny (72 h): 80 127 202 320 508 806 1280
```
- Naliczanie w `sync()` przez istniejące `business_sync`, więc działa offline. Pojemność to 24 h lub 72 h × bonus Siły (jak u firm).
- **Barista** (stanowisko 250 $) dalej daje +25%, teraz do budynku Kawiarnia.
- **Odbiór z dowolnego miejsca:**
  - `collect_nightclub` (nowa akcja);
  - `collect {business:"cafe"}` / `{business:"nightclub"}`.
  Firmy (kurier, Studio) dalej odbiera się tylko w dzielnicy 2.
- **Zgodność ze starymi przyciskami:**
  - `buy_business cafe` zwraca 409 „Corner Café została zamknięta — Kawiarnia to teraz budynek w Twojej dzielnicy.”;
  - `upgrade cafe` przekierowuje na rozbudowę budynku.
- **API:**
  - nowe w `catalog`: `buildingMaxes`, `buildingCostsBy`, `buildingVaults`;
  - stare klucze zostają;
  - podsumowanie nieobecności zawiera skarbce budynków;
  - lista graczy (`biz`) pokazuje poziom Kawiarni i Klubu.

**⚠️ Skutek ekonomiczny:** każdy gracz od startu ma Kawiarnię lvl 1, czyli **30 $/h idle za darmo**. Wcześniej trzeba było kupić Café za 2500 $ od lvl 2. Tak wynika z GDD, ale zaznaczam to wprost.

## Testy
- **pytest: 381 passed** (było 373, doszło 8 nowych).
- **Poprawione stare testy** (zmieniły się tylko asercje dotyczące Café i Siłowni):
  - `test_api` (×2): skarbiec Café zamieniony na `vaults.cafe`;
  - `test_buildings`: nowy katalog, start i bramka;
  - `test_idle`: skarbiec 30 → 52, bo dochodzi dochód Kawiarni;
  - `test_presence`, `test_travel`: zamiast zakupu Café zakup Studio Forma.
- **E2E: 34/36.**
  - `test-orgcontracts` i `test-qol` przeszły dopiero przy powtórce.
  - `test-orgs` i pierwsze podejście `test-online` padły na timeoutach przed krokami z kawiarnią. Przy pojedynczym uruchomieniu `test-orgs` przeszedł, a `test-online` doszedł do kroku z Café (opisany niżej).
  - **Dwie porażki to stary web, który nie zna nowych reguł:**

| test | przyczyna | propozycja (zmiana tylko w teście, bez JS) |
|---|---|---|
| `test-district` | stary web pokazuje przycisk „Otwórz Salę Chwały” tylko przy starym warunku (Siłownia i Sala Klubowa na 5), więc w starym webie nie da się otworzyć Sali | seed z nowymi maksimami i otwarcie przez `Network.action({action:'upgrade_building',building:'hall'})`; lista kart zostaje |
| `test-online` | krok `cafe-buy`: przycisku zakupu Café już nie ma | zastąpić zakupem Studio Forma (`studio`) |

Stary web po tej zmianie (zostaje do Fluttera, bez poprawek JS):
- karta Siłowni bez poziomu;
- brak widoku Klubu Nocnego;
- bramka Sali w starym webie jest nieosiągalna, ale serwer działa poprawnie.

## Plan po akceptacji
1. Poprawić 2 testy E2E jak w tabeli i uruchomić pełne E2E.
2. Dwa commity: `feat(buildings): 6 budynków … [GDD v3.1 4.1]` oraz `feat(buildings): skarbce Kawiarni lvl 10 i Klubu Nocnego 72 h … [GDD v3.1 4.2–4.3]`.
3. Przejść do 4.4 (Buffet) i 4.5 (RESET): najpierw projekt z pytaniami, m.in. o Punkty Prestiżu i tabele (zapis przez migracje).
