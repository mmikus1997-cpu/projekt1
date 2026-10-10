# M6 — zamknięcie zakresu przebudowy mapy

## Naprawione w tym etapie
1. Trasy NPC są wyznaczane po grafie odcinków `roads[].path`, według odległości. Auto kończy na najbliższym dojeździe należącym do dróg danej dzielnicy, a nie jedzie prostą linią przez teren do pinezki lokalu. Powrót odwraca tę samą trasę. Brak połączenia nie tworzy sztucznego skrótu.
2. Odliczania popytu, podróży i pracowników oraz pozycje aut korzystają z korekty czasu serwera.
3. Układ panelu zależy od szerokości dostępnej mapie, po odjęciu nawigacji. Poniżej 760 px tej przestrzeni używany jest panel dolny, zamiast ściskać okolicę panelem bocznym.
4. Imię pracownika i pozostały czas są w osobnych wierszach — długie nazwisko nie wypycha licznika poza panel.
5. Po terminie zmiany panel pobiera ponownie ekipę. Co 30 sekund odświeżane są także dane mapy i otwartego panelu usługi. Zakończona zmiana nie pozostaje stale na komunikacie „kończy zmianę”.
6. Model czasu pracownika używa jawnej granicy liczbowej zamiast przesunięcia bitowego zależnego od platformy.

Backend i zasady ekonomii nie były zmieniane.

## Zamknięcie wymagań mapy M1–M6
| Wymaganie | Stan / realizacja |
|---|---|
| Spójny malowany region pod pinezkami | `world.jpg`, przełączana warstwa grafiki; konfiguracja w `map_data.json` |
| Usługi rozłożone po mapie | 12 usług w konfiguracji, rozłożonych między osiem dzielnic |
| Widok bliższej okolicy | 8 osobnych grafik regionów; statyczny kadr, panel danych nad mapą, powrót do świata |
| Dekoracyjne obrzeża | Punkty nie leżą na granicy planszy; minimalny odstęp środka punktu od granicy: dzielnice 225, usługi 76, landmarki 156 jednostek planszy |
| Pracownik w usłudze | Awatar, postęp i czas zmiany; bez pracownika pozostaje wysyłka NPC; po zakończeniu odświeżenie |
| Dzielnica gracza | 18 wariantów grafik, cztery etapy, czas budowy, panele po kliknięciu; wykonane w poprzednich etapach |
| Auta po drogach | M6 usuwa końcowy odcinek przez teren. Geometria dróg nadal pochodzi z ręcznie dopasowanego JSON-a |
| Łatwa podmiana grafik | `assets/images/map/PROMPTY.md`, `assets/images/district/PROMPTY.md`, ścieżki w JSON i grafiki w assets |

## Testy końcowe
- **Flutter: 33/33 zaliczone** — w tym 18 testów tras/zegara oraz 2 testy modelu i panelu pracownika.
- **Backend: 482/482 zaliczone**, 6 istniejących ostrzeżeń testów/deprecacji.
- `flutter analyze lib`: brak błędów, dwa wcześniejsze ostrzeżenia o nieużywanych parametrach HUD/Klubu.
- Flutter Web: udana kompilacja.
- Playwright: 1280×900, 800×900, 400×740, 320×740; wejście do Centrum, wybór Kawiarni, panel usługi, akcja NPC i powrót do świata. Brak wykrytych wyjątków i overflow.
- Osobny wariant przeglądarkowy z testową odpowiedzią `/npcs` potwierdził panel z pracownikiem i przycisk „Wyślij kolejnego NPC” na czterech szerokościach. Ta odpowiedź była podmieniana wyłącznie w przeglądarce testowej; zapis konta nie był zmieniany.
- Test widgetowy: pracownik i postęp na szerokości 320 px, a następnie odświeżenie po końcu zmiany i powrót przycisku wysyłki.
- Dla każdej z 12 usług sprawdzono wszystkie odcinki trasy: każdy leży na odcinku zapisanej sieci dróg. To kontrola geometrii JSON-a, nie automatyczna ocena pikseli namalowanej jezdni.

Zrzuty: `app/shots/m6-region-*.jpg`, `m6-service-*.jpg`.

## Kod
- `app/lib/features/map/map_routes.dart`: graf dróg, projekcja na dojazd, najkrótsza trasa.
- `map_layout.dart`: połączenie grafu z konfiguracją usług.
- `map_providers.dart`, `map_rides.dart`: korekta zegara.
- `map_screen.dart`, `map_panel.dart`: responsywność i odświeżanie.
- `app/test/map_routes_test.dart`, `map_worker_test.dart`.
- `app/tools/test_map_m6.cjs`; `M6_WORKER_FIXTURE=1` włącza wariant z pracownikiem.

Przykład użycia algorytmu:
```dart
final pts = routeOnRoads(
  lines,
  district(homeDistrict).pos,
  slot.pos,
  destinationLines: access,
);
return toWork ? pts : pts.reversed.toList();
```

Commit bazowy M6: `f9ba12d`; uzupełnienie o aktualizację pracowników zapisane w kolejnym commicie.

## Paczka i ograniczenia
Aktualny `city-empire-online-0.60.0-gdd32.zip` zawiera źródła, backend, gotowy WWW, grafiki, lokalny silnik CanvasKit i fonty. Instrukcja: `URUCHOMIENIE-PELNA-GRA.md`. Archiwum nie zawiera baz kont, sekretów ani środowiska Python. Numer paczki pozostaje 0.60.0 zgodnie z zasadą jednej paczki; aktualność określa raport M6 i `SHA256.txt` obok archiwum.

Zakończono zakres przebudowy mapy i Dzielnicy. Nie oznacza to wdrożenia produkcyjnego ani ukończenia wszystkich przyszłych funkcji GDD; natywne APK/IPA nie są częścią tego zakresu. Instalację testowano wcześniej na Linuxie, nie na Windows/macOS.
