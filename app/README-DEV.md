# City Empire — aplikacja Flutter (Web / iOS / Android)

## Uruchomienie lokalnie (PC)
    flutter pub get
    flutter run -d chrome --web-port=8080 --dart-define=API_BASE=http://localhost:3000
Backend: `cd ../online && CITY_PORT=3000 python3 -m uvicorn server.app:app --port 3000`.
Uwaga: przy osobnych portach (8080 ↔ 3000) przeglądarka wysyła nagłówek Origin z innego portu, a backend odrzuca POST z obcego originu (403).
Najprościej użyć serwera podglądu (ten sam origin):

    flutter build web --release -O1
    python3 tools/serve_web.py --port 8080      # serwuje build/web + proxy /api → :3000

## Mobile
    flutter run -d android --dart-define=API_BASE=http://10.0.2.2:3000   # emulator Androida
    flutter run -d ios     --dart-define=API_BASE=http://localhost:3000

## Ważne fakty o backendzie
- Sesja: token (`previewSessionToken`, tryb development) + `X-CSRF-Token`, nie JWT.
- Każdy POST: ciało JSON (inaczej 415) + `Idempotency-Key` (dokłada AuthInterceptor).
- Brak Socket.IO — `SocketClient` wyłączony (`--dart-define=REALTIME=1`), dane odświeżane co 30 s.
- 💎 nie ma w /dashboard — pobierane z /gear.
