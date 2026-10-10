# RAPORT — Etap 8 migracji GDD v3.1 (backend)

Gałąź `feature/gdd-v31-migration`, zakres `9356130..ec54784` (7 commitów, 27 plików, +2154/−57).
Backupy `*.backup_v059` są nienaruszone. Frontend vanilla JS bez zmian (UI → Flutter).

## Wyniki
| Kontrola | Wynik |
|---|---|
| pytest (pełny) | **431 passed**; `tests/test_stage8.py` 11/11 |
| E2E Playwright | **36/36** (`test-economy`, `test-online` zaktualizowane pod 8.2; `test-chronicle` przeszedł przy powtórce — znany niestabilny) |
| Podgląd | :3000 działa na HEAD |

## Commity
| Commit | Punkt | Zakres |
|---|---|---|
| `9b5d671` | 8.1 | `longplay.py`: tabela stażu 7/14/30/90/180/365/1000 dni, nagrody jednorazowe (idempotentne), `/monuments` |
| `9ca749f` | 8.2 (+8.1) | `stat_pct`/`pve_pct`: cap × min(stat,30)/30; staż +10%/+5% w `prestige_mult` dla całego $ z pracy |
| `b1aa674` | 8.3 | bez limitu 20 000 $, kontrola >55%, federacje (max 3 sojusze), +5% $ z pracy NPC (`TERRITORY_HOOK`) |
| `c6c4ff6` | 8.4 | `server/battlepass.py`: sezon = miesiąc UTC, 30 × 100 XP, darmowa ścieżka + Premium 400💎, 12 motywów |
| `ecdd77d` | 8.6 | `GET /api/worlds/{wid}/dashboard` + allowlista tras Etapu 8 |
| `0a7f2a3` | 8.5 | `server/err_i18n.py` + `i18n/errors.json`: komunikaty 4xx po en/de/fr |
| `ec54784` | test | E2E: oczekiwane XP i premia uwzględniają capy 8.2 |

## 8.1 Staż
| Dni | Tytuł | Nagrody |
|---|---|---|
| 7 | Debiutant | auto Mistrz Rankingu, Kawiarnia lvl 1, 50💎, +10% dochodu na stałe |
| 14 | Praktykant | Rezydencja lvl 2, Klub Nocny lvl 1, 70💎 |
| 30 | Weteran | pies, koń, 100💎 |
| 90 | Legenda | outfit, 300💎 |
| 180 | Magnat | ramka, kolor nicku, 500💎 |
| 365 | Ikona | pomnik na mapie (`GET /monuments`), 1000💎 |
| 1000 | Założyciel | rola Discord, ankiety, +5% dochodu |

Budynki są tylko podnoszone, nigdy obniżane. 💎 są przyznawane z nagród, więc flaga premium-currency nie przeszkadza.

## 8.2 Capy PvE
Siła −10% czasu kontraktów, Inteligencja +15% firmy, Refleks −10% transportu, Charyzma +15% zarobków, Spryt +10% kontraktów (XP). Bonus = cap × min(stat,30)/30. Powyżej 30 pkt statystyka działa tylko w PvP.
Skutek uboczny (zamierzony): postać startowa (10 pkt) ma od razu 1/3 capu, np. Spryt +3,33%. Dlatego zaktualizowano 2 testy E2E.

## 8.3 Terytorium
- Limit 20 000 $ na dzielnicę został usunięty (`INVEST_CAP=None`). **Do decyzji:** pojedyncza wpłata nadal mieści się w 100–5000 $ (ochrona przed pomyłką). Mogę ją znieść.
- Kontrola: sojusz (lub federacja) z >55% udziałów. Bez tego dzielnica jest neutralna. **Do decyzji:** w logu zdarzeń zostaje wtedy etykieta „(rozwiązana)”.
- Federacje: `GET/POST /federations`, `POST /federations/invite {tag}`, `/federations/{fid}/accept`, `/federations/leave`. Max 3 sojusze, udziały się sumują.
- Członkowie kontrolującego sojuszu dostają +5% $ z pracy swoich NPC w tej dzielnicy.

## 8.4 Battle Pass
- Sezon `YYYY-MM` (UTC), reset 1. dnia miesiąca o 00:00 UTC. 30 poziomów po 100 XP.
- Źródła XP: praca NPC 10, PvP 15, Lochy 20, rozbudowa 30.
- Premium kosztuje 400💎, SKU 29,99 zł jest wyłączone.
- 12 motywów miesięcznych bez powtórek (konie, psy, ramki, auta, outfity). Unikaty z kluczem sezonu na lvl 5/10/15/20/25/30.
- Endpointy: `GET /battlepass`, `POST /battlepass/premium`, `POST /battlepass/claim {level, track}`. Bez losowości.

## 8.5 i18n komunikatów błędów
- Komunikaty w kodzie zostają po polsku, więc stare klienty dostają je bez zmian. Handler `HTTPException` i `RuleError` tłumaczy `detail` słownikiem fragmentów: 360 fragmentów × en/de/fr, jedno przejście regexem, najdłuższe najpierw. Wstawki dynamiczne (kwoty, poziomy, nazwy) zostają.
- Język ustalany w kolejności: `accounts.language` (`POST /account/language`) → `Accept-Language` → pl.
- Ograniczenia:
  - komunikaty już będące kluczami `err.*` (gear/sklep) zostały nietknięte, bo tłumaczy je dotąd istniejący mechanizm;
  - domyślne 422 walidacji Pydantic (lista pól) nie są tłumaczone, to struktura dla klienta, nie tekst.

## 8.6 Dashboard
`GET /api/worlds/{wid}/dashboard` zwraca w jednym żądaniu: `state` (postać), `npc` (lista + `byStatus`), `assistant` (8 h), `events`, `vaults` (skarbce + suma), `battlepass`, `milestones`. Bez postaci w świecie: 403/404.

## Uwagi do akceptacji
1. Czy znieść też limit pojedynczej wpłaty 100–5000 $?
2. Czy w logu zastąpić etykietę „(rozwiązana)” etykietą „(neutralna)”?
3. Zmiany 8.2 podnoszą zarobki/XP startowych postaci o kilka %. Na razie zostawiam to zgodnie z GDD.
