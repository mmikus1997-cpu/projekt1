# M5 — dopasowanie budynków Dzielnicy

Podgląd: **1010-1147**. Commit aplikacji: `7943888`.

## Zmiany
- 18 nowych grafik: sześć rodzin budynków × trzy warianty rozwoju.
- Wspólna perspektywa frontalna z góry; usunięte osobne podesty i rozległe dekoracje wychodzące poza bryłę.
- Nowy plac budowy w tej samej perspektywie.
- Osobne pozycje i rozmiary wszystkich sześciu parceli dla każdego z czterech etapów.
- Delikatniejszy cień kontaktowy; zachowana korekcja kolorów według etapu.
- Mechanika poziomów, czas budowy i panele po kliknięciu pozostają bez zmian. Backend w tym etapie nie był edytowany.

## Sprawdzenie
- Pytest: **479 passed**, 6 ostrzeżeń.
- Flutter analyze: brak błędów; dwa wcześniejsze ostrzeżenia w `hud_bar.dart` i `club_screen.dart`.
- Flutter Web: kompilacja udana, nowy build wdrożony do podglądu.
- Playwright: desktop 1280×900 i telefon 400×850; przejście do Dzielnicy, otwarcie i zamknięcie panelu Rezydencji; brak wykrytych wyjątków i komunikatów overflow.
- Kontaktówka: 72 kombinacje (6 budynków × 3 warianty × 4 etapy). Sprawdzone granice obrazów względem zdefiniowanych parceli. Jest to kontrola geometrii i przegląd wizualny, nie automatyczna ocena zgodności perspektywy.
- Zrzuty: `app/shots/aligned-desktop.jpg`, `aligned-mobile.jpg`, `aligned-*-panel.jpg`, `aligned-stage-1.jpg` … `aligned-stage-4.jpg`; kontaktówka `district-art-72.jpg`.

## Kod i podmiana grafiki
`app/lib/features/district/district_visual.dart` — geometria `_plotsByStage` i cienie `_Blend`.
`app/assets/images/district/PROMPTY.md` — opis kamery, prompty i instrukcja podmiany.
`app/tools/prepare_district_sprites.py` — przygotowanie PNG z arkuszy.
`app/tools/district_art_review.py` — kontaktówka i kontrola granic.
`app/tools/test_district_art.cjs` — test przeglądarkowy (Playwright).

## Kopie i porządek
Poprzednie grafiki i kod: `app/backups/district-before-aligned.tar.gz` oraz historia Git. Starsze automatyczne kopie lokalnej bazy zachowano bezstratnie w `online/data/backups/archiwum-przed-m5-grafika.tar.gz` (weryfikacja bajtowa przed usunięciem luźnych kopii); najnowsza kopia SQLite pozostała osobno. Usunięto `.dart_tool` i wynikowy katalog `build` po wdrożeniu.

## Paczka
`city-empire-online-0.60.0-gdd32.zip` zawiera aktualny kod backendu i Fluttera (wersja źródłowa; gotowy build dostępny w podglądzie), bez baz kont, sekretów, historii Git i cache. Numer 0.60.0 zachowano zgodnie z zasadą jednej paczki. Grafika wymaga oceny użytkownika w podglądzie przed kolejnym etapem.
