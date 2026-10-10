# City Empire — pełna paczka gry 0.60.0 + aktualizacje M6

Zawiera backend Python, źródła aplikacji Flutter, gotowy frontend WWW (`app/web_release`), grafiki, testy i dokumentację. Gotowy frontend uwzględnia poprawki Dzielnicy (18 nowych grafik, panele budynków, czas rozbudowy) oraz M6 mapy (trasy po drogach, czas serwera, responsywność, odświeżanie pracowników).

Nie zawiera lokalnych kont, sesji, bazy zapisów graczy, sekretów, cache, środowiska Python, SDK Flutter ani historii Git. Nowa instalacja korzysta z własnej bazy. Administrator otwiera światy; konta demonstracyjne z podglądu nie są przenoszone.

## Uruchomienie lokalne (Python 3.11+; zalecany 3.13)
Rozpakuj ZIP. Polecenia wykonuj w katalogu głównym paczki.

1. Utwórz środowisko: `python -m venv .venv`.
2. Aktywuj je:
   - Windows PowerShell: `.venv\Scripts\Activate.ps1`
   - Linux/macOS: `source .venv/bin/activate`
3. Zainstaluj zależności: `python -m pip install -r online/requirements.txt`.
4. Uruchom oba serwery: `python uruchom_gre.py`.
5. Otwórz w przeglądarce na tym samym komputerze: **http://localhost:8080**.
6. Zatrzymanie: Ctrl+C w terminalu.

Adres localhost służy wyłącznie lokalnie uruchomionej paczce, nie podglądowi Arena. Port 8080 obsługuje Flutter oraz proxy API; port 3000 — backend. Uruchamiacz domyślnie udostępnia oba serwery tylko na komputerze lokalnym. Opcja `--host 0.0.0.0` udostępnia WWW w sieci; używaj jej tylko w zaufanej sieci. Porty można zmienić: `python uruchom_gre.py --api-port 3001 --web-port 8081`. Nie jest to konfiguracja produkcyjna.

Przy pierwszym uruchomieniu backend tworzy bazę i plik inicjalizacji administratora `online/data/administrator-setup.txt`. Chroń ten plik i postępuj zgodnie z zapisanymi w nim instrukcjami. Więcej informacji o zarządzaniu: `online/README.md` oraz `online/manage.py --help`.

Gotowa aplikacja webowa nie wymaga kompilacji Fluttera. Dołączony silnik CanvasKit, Inter oraz zestaw fontów pomocniczych ładują się lokalnie z paczki. Przepływ Dzielnicy przetestowano przy zablokowanych połączeniach zewnętrznych; nie sprawdzono w tym trybie każdego ekranu i każdego znaku Unicode. Instalacja zależności Pythona wymaga internetu (lub osobno przygotowanego zestawu pakietów). To nie jest instalator offline ani aplikacja .exe/.apk.

## Zmiany w kodzie Flutter
Zainstaluj Flutter zgodny z `app/pubspec.yaml` (ten build wykonano Flutterem 3.47.6), następnie w katalogu `app`:

```
flutter pub get
flutter build web -O1 --no-wasm-dry-run
```

Serwer WWW preferuje `app/build/web`, jeśli taki katalog z plikiem `main.dart.js` istnieje; w przeciwnym razie używa dołączonego `app/web_release`.

## Testy
W katalogu `online`: `python -m pytest -q`.
Ostatnie testy: backend 482 zaliczone, Flutter 33 zaliczone. Sprawdzono świeżą instalację na Linuxie oraz pełny przebieg rozbudowy i odbioru skarbca przez przeglądarkę. Nie przeprowadzono instalacji na Windows ani macOS. Archiwum zweryfikowano testem integralności ZIP.

Pakowanie gotowego frontendu ustawia `canvasKitBaseUrl` na lokalny `canvaskit/`; skrypt `tools/package_game.py` dołącza wariant podstawowy i Chromium z wyniku kompilacji. Zwykła ponowna kompilacja Fluttera może domyślnie używać CDN.
