# PROJEKT — Etap 8 (GDD v3.1)

Decyzje zatwierdzone przez usera przed implementacją:
- capy = cap × min(stat,30)/30, start od 10 pkt;
- prosta federacja: zaproszenie, max 3 sojusze, udziały sumowane;
- BP Premium tylko za 400💎, SKU PLN wyłączone;
- i18n pełne pl/en/de/fr;
- staż +10%/+5% dla całego $ z pracy.

| Punkt | Pliki | Mechanizm | Kompatybilność |
|---|---|---|---|
| 8.1 | `longplay.py` | tabela `STAZ`, `grant_staz` idempotentne (`s['staz']`) | addytywne pola stanu |
| 8.2 | `economy.py` | `pve_pct(s,i)` w kontraktach/firmach/transporcie | PvP bez zmian |
| 8.3 | `economy.py`, `features.py` | `INVEST_CAP=None`, próg 55%, tabele `federations*` (CREATE IF NOT EXISTS), `TERRITORY_HOOK` | migracja addytywna |
| 8.4 | `battlepass.py` (nowy), hooki `E.BP_HOOK` | stan w `s['bp']`, klucz sezonu `YYYY-MM` | brak wpływu na stare zapisy |
| 8.5 | `err_i18n.py` (nowy), `i18n/errors.json`, `app.py` | tłumaczenie `detail` w handlerze wyjątków | teksty pl bez zmian |
| 8.6 | `app.py` | endpoint składany z istniejących funkcji | tylko odczyt |
