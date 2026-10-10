# Grafiki mapy — prompty i podmiana

Wszystkie grafiki opisuje `assets/data/map_data.json` → sekcja `art`. **Podmiana = nowy plik w tej samej ścieżce, kod się nie zmienia.**
Brak pliku albo błąd ładowania → aplikacja rysuje dotychczasowy teren wektorowy (fallback).

## Wspólny styl (doklejać do każdego promptu)
> hand-painted top-down game map, mobile city-builder style, slight isometric feel, soft daylight, gentle shadows, rich detail, warm saturated colors, no text, no labels, no UI, no icons, no borders

## 1. Mapa świata — `world.jpg`
- Proporcje **10:7** (np. 2000×1400), JPG ~85%.
- Referencja układu: `art_src/world_guide.jpg` (generowana z map_data.json; podać generatorowi jako obraz wejściowy „keep exact layout”).
- Po wygenerowaniu na nowo dopasuj `x`/`y` dzielnic i usług w map_data.json (współrzędne planszy 1600×1120).

Prompt:
> Turn this color-blocked layout sketch into a richly detailed hand-painted top-down game world map. Keep the EXACT layout: sea at the bottom and bottom-left with sandy beaches and a small forested island; a winding river from the northern mountains down to the sea; a small lake east of downtown. Dense modern downtown with glass office towers in the middle (two clusters split by the river, bridges); coastal resort town with hotels, pools and palm trees at bottom-left; harbour with docks, cranes, ships and a lighthouse at the bottom; industrial zone with factories, chimneys, warehouses and a railway at top-left; mountain mining village with an open-pit quarry at top-right; sports park with a stadium, football pitches, tennis courts and a running track at bottom-right; dense pine forest with a round lodge village on the right. Paved roads connect the towns. Farmland, meadows and small villages in between. Edges purely decorative: snowy rocky mountains along the top, thick forests on the left and right, open ocean at the bottom. + wspólny styl

## 2. Widoki okolic (zoom 2. poziomu) — `region_1.jpg` … `region_8.jpg`
- Proporcje **10:7** (np. 1000×700 lub większe), JPG ~85%.
- `map_data.json` → `art.regions["<id dzielnicy>"].rect` = fragment planszy [x, y, w, h], który przedstawia grafika.
  Pinezki usług liczone są z tych samych współrzędnych planszy, więc grafika musi zachować układ wycinka.
- Referencja: `art_src/crop_<id>.jpg` (wycinek world.jpg z prostokąta `rect`) — podać jako obraz wejściowy.
- Brak pliku → aplikacja pokazuje powiększony wycinek world.jpg.

Wspólny początek promptu:
> Repaint this map fragment as a much more detailed close-up of the same area, keeping the EXACT same layout and positions.

| Plik | Dzielnica | Treść promptu (po wspólnym początku, przed stylem) |
|---|---|---|
| region_1 | Nadmorskie | Seaside resort district: large hotels with pools and palm trees, beach with umbrellas and loungers, colorful houses with red roofs, a library building, small plaza, cars on roads. |
| region_2 | Przemysłowe | Industrial district: brick factories with smoking chimneys, warehouses, a cleaning company depot with vans, a courier parcel depot with trucks, railway with freight wagons, containers, forklifts. |
| region_3 | Centrum | Downtown district: glass skyscrapers, a modern private clinic, a cozy cafe with outdoor tables, a corner mini-market, plazas with trees and fountains, busy streets with cars and buses. |
| region_4 | Portowe | Harbour district: piers, cargo ships, fishing boats, blue gantry cranes, containers, red-white lighthouse, warehouses, an office building with a call center. |
| region_5 | Biznesowe | Business district: bank and corporate headquarters, glass offices, a marketing agency, a graphic design studio in a loft, rooftop gardens, a small lake with a park. |
| region_6 | Sportowe | Sports district: oval stadium, football pitches, tennis courts, running track, small amusement park with a ferris wheel, parking, beach at the bottom. |
| region_7 | Kopalnia | Mountain mining district: terraced open-pit mine with dump trucks and excavators, mine headframe tower, machinery repair workshop, wooden miners' cabins, snowy mountains. |
| region_8 | Lasy Wschodnie | Forest district: dense pine forest, a round village of wooden houses, a forest hotel lodge with a terrace, sawmill with log piles, forest paths, a deer. |

## Dzielnica gracza (M5) — `assets/images/district/`

Podkłady `ground_{1..4}.jpg` (1400×784; etapy: Pustkowie, Plac Budowy, Zorganizowany Hub, Metropolia) — generowane na szkicu układu `art_src/district/guide.jpg` (6 parcel + skrzyżowanie dróg), potem `resize(1000,700)` → `crop(0,70,1000,630)`.

Budynki `{id}_{1..3}.png` — wariant wg postępu poziomu (`level/max`: <0,34 → 1, <0,67 → 2, reszta → 3). Generować na białym tle, potem `python3 tools/cut_bg.py wej.jpg assets/images/district/{id}_{n}.png`.
Wspólny dopisek do każdego promptu: *„Isometric 3/4 view, hand-painted mobile city-builder style, soft contact shadow, centered, plain pure white background, no ground, no text”*, poprzedzony „Single isolated building game asset: …”.

| plik | opis |
|---|---|
| residence_1/2/3 | drewniany domek z gankiem / piętrowy dom z balkonem / nowoczesna willa z basenem i palmami |
| garage_1/2/3 | blaszany garaż z oponami / ceglany warsztat z 3 bramami / szklany salon aut z 5 stanowiskami |
| cafe_1/2/3 | kiosk z kawą i markizą / przytulna ceglana kawiarnia z tarasem / dwupiętrowa restauracja z tarasem na dachu |
| nightclub_1/2/3 | mały bar z neonem kieliszka / dwupiętrowy klub z neonami i bramkarzem / wielki klub z kopułą, reflektorami, czerwonym dywanem |
| club_1/2/3 | siłownia w garażu z workiem / ceglany klub bokserski / nowoczesna arena walk |
| hall_1/2/3 | mały pawilon z gablotą trofeów / neoklasyczna hala z kolumnami / złota Sala Chwały z posągiem i fontannami |

Brak pliku → gra pokazuje niższy wariant, a gdy nie ma żadnego — bryłę wektorową.
