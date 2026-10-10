CITY EMPIRE — pakiet wdrożeniowy 0.8.0
======================================

Zawartość:
- Dockerfile               obraz produkcyjny (stałe zależności, użytkownik nie-root, healthcheck).
- docker-compose.yml       przykładowe uruchomienie z wolumenami na dane i kopie.
- city-empire.service      jednostka systemd z Restart=always i ProtectSystem=strict.
- backup-offsite.sh        wzorzec eksportu kopii poza maszynę (uruchamiać z cron/timer).

Kolejność pierwszego wdrożenia:
1. Postaw maszynę, zainstaluj Dockera lub Pythona 3.13 + venv.
2. Skopiuj wydanie (server/, web/, requirements.txt, build.py) — nigdy katalogu data/ z wersji deweloperskiej.
3. Uruchom usługę. Przy pierwszym starcie powstanie baza i plik data/administrator-setup.txt z jednorazowym
   kodem administratora — użyj go w grze („Konto” → aktywacja administratora), potem plik sam znika.
4. Zweryfikuj: GET /api/health zwraca status ok; panel administratora pokazuje kopie automatyczne.
5. Ustaw backup-offsite.sh w cronie (np. co godzinę) i sprawdź odtworzenie na osobnej maszynie
   (manage.py verify-backup + rehearse-restore).

Czego ten pakiet NIE robi:
- nie konfiguruje domeny, HTTPS ani reverse proxy (przykład: Caddy/nginx z nagłówkami Host/X-Forwarded-Proto),
- nie wysyła alarmów na zewnątrz — log procesu i panel kopii to jedyne źródła sygnałów dopóki nie podłączysz
  własnego monitoringu (np. healthcheck + uptime-kuma, alerty na mail/telegram),
- nie gwarantuje dopuszczenia sklepów — to osobna ścieżka (MONETYZACJA.md).
