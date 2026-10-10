# Raport Etap 7: Ekwipunek, sety, crafting, sklep, kupony, i18n [GDD v3.1 7.1–7.6]

Gałąź `feature/gdd-v31-migration`. Projekt: `PROJEKT-ETAP-7.md`.

**Commity:**
- `8dd44ef` feat(economy): hak bonusów setów w `effective`, zamknięcie starego sklepu [7.2–7.3]
- `6051069` feat(gear): nowy moduł `server/gear.py` + `server/i18n/*.json` + podpięcie w `app.py` [7.1–7.6]
- `74e1c72` feat(dungeon): drop z Lochu Normal z setów [7.1]

Diff względem Etapu 6: 15 plików, +912/−31. Backupy `economy.py`, `app.py` i `dungeon.py` (`*.backup_v059`) są nietknięte. `gear.py` i i18n to nowe pliki.

## 7.1 Ekwipunek i plecak
- **8 slotów:** gloves (rękawice/broń), shoes, pants, belt, shirt, head (bandana/kask), amulet, ring (pierścionek zamiast kolczyków).
- **Plecak** (`s['backpack']`): start 5 miejsc.
  - Za $: miejsca 6–10 na poziomach 5/10/15/20/25, kolejno 500/1500/5000/15000/50000 $.
  - Za 💎: miejsca 11–15, kolejno 50/100/200/400/800 💎, dopiero po wykupieniu miejsc za $. Maksimum 15.
- **Stare sloty:** założenie `head` zdejmuje stary `helmet`, a `ring` zdejmuje `accessory`. Stare przedmioty zostają w kolekcji `inventory`, nic nie znika.
- **Loch Normal:**
  - serie 1–5: zwykli dają T1, bossowie T2;
  - serie 6–10: zwykli dają T2, bossowie T3;
  - drop trafia do plecaka (duplikaty też, bez zamiany na $);
  - unikaty serii 1 bez zmian.

## 7.2 Sety (9 × 8 części = 72 przedmioty)
| Tier | Sety | Bonus jednej części (lvl 1) |
|---|---|---|
| T1 szary | Uliczny (Siła), Akademicki (Int), Sprinterski (Refleks) | +3 do jednej statystyki |
| T2 zielony | Portowy (Siła/Cha), Cienia (Refleks/Spryt) | +4 i +3 |
| T3 niebieski | Mistrzowski, Gwardyjski | +7 do statystyki klasowej |
| T4 fioletowy | Legendarny, Cesarski | tryb A +5 do wszystkich albo tryb B +12 do klasowej; wybór przy zakładaniu |

- **Statystyka klasowa:** Bokser → Siła, Obrońca → Inteligencja, Szybki → Refleks.
- **Skalowanie:** bonus × (1 + 0,02·(lvl−1)), np. lvl 26 daje ×1,5.
- **Komplet** 8 części jednego setu: +30%.

## 7.3 Sklep w Sali Klubowej
- `GET/POST /gear/shop`: 8 losowych przedmiotów z rotacją co 6 h.
  - Strefa 1 Pancerz: 5 sztuk (buty, spodnie, pasek, koszulka, bandana).
  - Strefa 2 Biżuteria i Broń: 3 sztuki (rękawice, naszyjnik, pierścionek).
  - Oferta jest stała w oknie 6 h i zależy od postaci; widać tylko przedmioty dostępne dla jej poziomu. Każdą ofertę można kupić raz na okno.
- **Ceny:**
  - T1: 400 $;
  - T2: 1500 $ (lvl 5);
  - T3: 6000 $ albo 3000 $ + 15💎 (lvl 10);
  - T4: 20000 $ + 60💎 (lvl 15).
- **Kupony** to stałe produkty: XP 3000 $ / 15💎, Akcja 1500 $ / 8💎, Kontrakt 2000 $ / 10💎.
- 💎 za konkretny przedmiot: 0% losowości.
- **Stary sklep** (`buy`) zwraca 409 z odesłaniem do Sali Klubowej. Flaga `E.LEGACY_SHOP_OPEN=False`.

## 7.4 Crafting 3 → 1
- `POST /gear/craft {items:[3 id]}`: 3 przedmioty z tego samego tieru dają losowy przedmiot tieru wyżej.
- Koszt: 500 $, 2000 $ oraz 10000 $ + 20💎.
- Wynik pochodzi z seeda (postać + licznik akcji). Ponowienie żądania nie zmienia wyniku, a każdy craft jest audytowany.

## 7.5 Kupony (max 100 każdego)
- **XP:** +100% XP z akcji przez 1 h; kumuluje się czasowo.
- **Natychmiastowa Akcja:** kończy najbliższe trwające zadanie (kontrakt albo trening), reszta kolejki przesuwa się razem z nim.
- **Kontrakt:** następny odebrany kontrakt daje +10% $ i XP.

## 7.6 i18n i waluty
- `server/i18n/{pl,en,de,fr}.json` (55 kluczy, identyczny zestaw w każdym pliku) oraz `GET /api/i18n/{lang}`.
- **Kolejność wyboru języka:**
  1. `accounts.language`, ustawiane przez `POST /api/account/language` (migracja addytywna);
  2. `Accept-Language` (pierwszy obsługiwany język);
  3. pl.
- `GET /api/shop/prices?currency=PLN|EUR|USD|GBP`: przeliczone ceny SKU, tylko do wyświetlania (`displayOnly`). Kursy stałe: EUR 0,23, USD 0,25, GBP 0,20 za 1 zł.

## ⚠️ Do decyzji / interpretacje
1. **Podział 9 setów:** przyjąłem T1 = 3, T2 = 2, T3 = 2, T4 = 2. Specyfikacja mówiła o 3 setach na tier, co daje 12.
2. **Liczby ze specyfikacji** (+3; +4/+3; +12; +5) potraktowałem jako bonus jednej części. Pełny T4 tryb B to +125 do statystyki klasowej na lvl 15 (8 × 12 × 1,28 × 1,3). Jest bardzo mocny, do przejrzenia balansu.
3. **Crafting T3 → T4 za 💎 daje losowy wynik.** To Twoja decyzja, ale jest to płatna losowość za walutę premium. Teraz 💎 pochodzą wyłącznie z nagród (flaga OFF), więc ryzyko prawne jest niskie. Po włączeniu kupowania 💎 za PLN ten crafting podpadnie pod regulacje lootboxów (szczególnie u nastolatków). Zalecam wtedy wybór setu docelowego.
4. **Szansa 5%/3% na darmowy kupon przy zakupie została usunięta.** Zgodnie z Twoją odpowiedzią kupony są stałymi produktami. Mogę przywrócić tę szansę dla zakupów za $.
5. **Kupon Kontrakt** daje +10% nagrody zamiast „+10% statystyk”. **Kupon XP** działa na akcje (kontrakty, treningi), a nie na PvP ani Loch.
6. **Pojemność plecaka blokuje tylko zakupy i zdejmowanie przedmiotów.** Drop z Lochu i crafting mogą ją przekroczyć, żeby nagroda nie przepadła.
7. **Bramka sklepu to Sala Klubowa na poziomie ≥1.** Każda postać startuje z poziomem 1, więc w praktyce sklep jest dostępny od razu i nie wymaga przebywania w budynku.
8. **i18n obejmuje tylko nowe moduły.** Przetłumaczenie istniejących polskich komunikatów (kilkaset tekstów) proponuję w Etapie 8.
9. **Stary vanilla frontend nadal pokazuje stary sklep, ale kupno zwraca 409.** Zgodnie z zasadą nie ruszałem UI, bo nowe ekrany powstaną we Flutterze.

## Testy
- **pytest: 420 passed** (było 410).
  - Nowy `tests/test_gear.py`: 11 testów.
  - Przepisane 2 testy w `test_dungeon_v6.py` (drop z setów).
  - 5 testów starej mechaniki zakupu używa jawnej fikstury `legacy_shop`.
- **E2E:** wynik poniżej.

## Wynik E2E
**36/36 PASS.** Pierwszy przebieg dał 34/36: `test-features` i `test-online` kupowały przedmioty w starym sklepie przez stary UI. Testy sprawdzają teraz, że zakup jest odrzucany, a przedmiot nie trafia do ekwipunku (commit `test(e2e): …`). Po zmianie oba przechodzą.
