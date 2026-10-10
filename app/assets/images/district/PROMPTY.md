# Dzielnica — grafiki dopasowane do planu (M5)

## Kamera i styl
Malowana ilustracja city-builder, widok frontalny z góry (około 65°). Przednia krawędź budynku pozioma, boki biegną ku górze obrazu. Widać dużo dachu i skróconą przednią elewację, nie boczną ścianę. Światło z lewego górnego rogu. Przygaszone kolory, miękkie kontury. Bez izometrycznych podestów, terenu, płyty chodnikowej i długich wypalonych cieni.

## Arkusze
Źródła: `art_src/district/sheet_aligned_1.jpg` … `sheet_aligned_3.jpg`.
Układ 3 × 2: Rezydencja / Kawiarnia / Klub Nocny; Garaż / Sala Klubowa / Sala Chwały.
Warianty: skromny / rozwinięty / prestiżowy. Powiązanie z poziomami zachowuje `buildingTier` — nie zmienia zasad ani liczby poziomów.

Prompt bazowy: "Six isolated building sprites, 3 columns by 2 rows, white background, generous gutters, no grid lines or text. Frontal birdseye camera, roof-dominant view, front edges exactly horizontal, side edges vertical, only front facade visible. Muted hand-painted city-builder style, warm upper-left light. No isometric rotation, no paving slabs, land tiles or platforms. Residence, green-awning cafe, purple-accent nightclub, garage, social club, civic hall."

Dla wariantu 2: "Upgrade architecture while retaining identical camera, layout and palette: dormers, rooftop cafe terrace, subtle marquee, improved garage, covered club entrance, copper civic dome."

Dla wariantu 3: "Prestigious architecture, sandstone mansion with slate roofs, roof garden cafe, art deco nightclub without lasers, premium garage, grand social club with skylight, civic hall with bronze-gold dome. Compact rectangular footprints, no detached landscaping."

## Obróbka i kontrola
`python3 tools/prepare_district_sprites.py` wycina obiekty i tło.
`python3 tools/district_art_review.py` tworzy kontaktówkę 72 kombinacji (6 budynków × 3 warianty × 4 etapy) i sprawdza granice renderowania.
Pozycje parceli: `_plotsByStage` w `district_visual.dart`; kolory i cień: `_Blend`.
Tła: `ground_1.jpg` … `ground_4.jpg`, proporcje 1000:560. Można podmienić bez zmiany mechaniki; po zmianie geometrii dróg trzeba ponownie dopasować parcele.

Budowa: osobny `construction.png`, źródło `construction_aligned.jpg`; identyczna kamera, niewysokie ceglane ściany i więźba, bez podestu i dźwigu. Rusztowania rozbudowy pozostają warstwą Fluttera.
