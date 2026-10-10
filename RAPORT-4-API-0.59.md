# Raport 4 — API (v0.59.0)

Źródło: introspekcja `app.routes` (FastAPI). Razem: **105** tras. Wszystkie POST zalogowane wymagają nagłówka CSRF; autoryzacja = cookie sesji.

## Publiczne (8)

| Metoda | Ścieżka | Opis | Body | Źródło |
|---|---|---|---|---|
| GET | `/` | Strona gry (SPA). | — | app.py:288 |
| GET | `/art/{name}` | Grafika z web/art. | — | app.py:290 |
| GET | `/api/health` | Status serwera, wersja i czas serwera. | — | app.py:297 |
| GET | `/api/auth/config` | Konfiguracja logowania (tryb podglądu). | — | app.py:299 |
| POST | `/api/preview/request` | Tunel żądań dla podglądu w iframe (sesja+CSRF w body). | `session,csrf,method,path,payload,idempotency_key` | app.py:301 |
| GET | `/api/setup/status` | Czy konto administratora zostało już przejęte. | — | app.py:324 |
| POST | `/api/auth/register` | Rejestracja konta (zgoda wymagana). | `username,password,preview_session,consent` | app.py:327 |
| POST | `/api/auth/login` | Logowanie. | `username,password,preview_session,consent` | app.py:342 |

## Zalogowane (83)

| Metoda | Ścieżka | Opis | Body | Źródło |
|---|---|---|---|---|
| GET | `/api/me` | Dane zalogowanego konta, token CSRF i czas serwera. | — | app.py:351 |
| POST | `/api/auth/logout` | Wylogowanie (unieważnia sesję). | — | app.py:353 |
| POST | `/api/setup/claim` | Przejęcie roli admina kodem z pliku setup. | `code` | app.py:357 |
| GET | `/api/worlds` | Lista światów i postaci gracza. | — | app.py:367 |
| POST | `/api/worlds/{wid}/character` | Utworzenie (jedynej) postaci w świecie. | `nickname,accept_test_reset,class_type,avatar` | app.py:374 |
| POST | `/api/worlds/{wid}/class` | Wybór klasy postaci. | `class_type` | app.py:395 |
| POST | `/api/worlds/{wid}/location` | Zmiana lokacji (stary ruch, poza koleją). | `location` | app.py:408 |
| GET | `/api/worlds/{wid}/state` | Pełny stan postaci + terytoria, eventy, event czasowy. | — | app.py:419 |
| POST | `/api/worlds/{wid}/actions` | Wykonanie akcji ekonomicznej (patrz Raport 5). | `action,contract,task_id,stat,item,business,material,building,route,residence,rest,vehicle,staff,district,amount` | app.py:422 |
| POST | `/api/worlds/{wid}/tactic` | Ustawienie taktyki walki. | `style` | app.py:450 |
| GET | `/api/worlds/{wid}/players` | Lista graczy świata. | — | app.py:461 |
| GET | `/api/worlds/{wid}/pvp` | Panel PvP: wyzwania, mecze, limity. | — | app.py:483 |
| POST | `/api/worlds/{wid}/challenges` | Wysłanie wyzwania PvP (stary system) / zaproszenie do organizacji (features.py). | `target_id,tactic` | app.py:494 |
| POST | `/api/challenges/{cid}/accept` | Akceptacja wyzwania PvP. | `tactic` | app.py:511 |
| POST | `/api/challenges/{cid}/decline` | Odrzucenie wyzwania PvP. | — | app.py:539 |
| GET | `/api/matches/{mid}` | Raport meczu. | — | app.py:546 |
| GET | `/api/account/export` | Eksport danych konta (RODO). | — | app.py:605 |
| GET | `/api/account/profile` | Profil konta. | — | app.py:616 |
| GET | `/api/avatar/catalog` | Katalog elementów awatara. | — | app.py:628 |
| POST | `/api/worlds/{wid}/avatar` | Założenie elementów awatara. | `avatar` | app.py:633 |
| POST | `/api/worlds/{wid}/wardrobe` | Zakup elementu garderoby awatara. | `item` | app.py:646 |
| GET | `/api/account/rankings` | Rankingi konta we wszystkich światach. | — | app.py:664 |
| POST | `/api/account/delete` | Zlecenie usunięcia konta (okres karencji). | `password` | app.py:684 |
| POST | `/api/account/delete/cancel` | Anulowanie usunięcia konta. | `password` | app.py:700 |
| GET | `/api/worlds/{wid}/community` | Panel społeczności: organizacje, kronika, terytoria. | — | features.py:244 |
| GET | `/api/worlds/{wid}/organizations/{oid}` | Profil organizacji. | — | features.py:277 |
| POST | `/api/worlds/{wid}/distinction/claim` | Odbiór dziennej dystynkcji. | — | features.py:290 |
| POST | `/api/worlds/{wid}/character/evolve` | Ewolucja klasy (od 10 poziomu, jednorazowo). | `evolution_code` | features.py:300 |
| POST | `/api/worlds/{wid}/organizations` | Założenie organizacji. | `name,tag,description` | features.py:319 |
| POST | `/api/worlds/{wid}/organizations/invite` | Wysłanie wyzwania PvP (stary system) / zaproszenie do organizacji (features.py). | `target_id` | features.py:334 |
| POST | `/api/organization-invites/{iid}/{decision}` | Akceptacja/odrzucenie zaproszenia do organizacji. | — | features.py:347 |
| POST | `/api/worlds/{wid}/organizations/apply` | Podanie o przyjęcie do organizacji. | `org_id,text` | features.py:367 |
| POST | `/api/org-applications/{aid}/{decision}` | Rozpatrzenie podania (lider/oficer). | — | features.py:382 |
| POST | `/api/worlds/{wid}/organizations/building` | Rozbudowa budynku sojuszu z funduszu. | `building` | features.py:405 |
| POST | `/api/worlds/{wid}/organizations/fund` | Wpłata gotówki do funduszu organizacji. | `amount` | features.py:422 |
| POST | `/api/worlds/{wid}/organizations/invest` | Inwestycja funduszu w dzielnicę (wpływy/terytorium). | `district,amount` | features.py:436 |
| POST | `/api/worlds/{wid}/events/read` | Oznaczenie powiadomień jako przeczytane. | `ids,all` | features.py:461 |
| GET | `/api/ranking/global/season/{sn}` | Ranking globalny archiwalnego sezonu. | — | features.py:469 |
| GET | `/api/ranking/global/{wid}` | Ranking globalny świata. | — | features.py:482 |
| POST | `/api/worlds/{wid}/organizations/contract` | Kontrakt organizacji (prestiż/zbiórka). | `kind,district,target,hours` | features.py:500 |
| POST | `/api/worlds/{wid}/organizations/contract/cancel` | Anulowanie kontraktu organizacji. | — | features.py:515 |
| POST | `/api/worlds/{wid}/organizations/announcement` | Ogłoszenie organizacji. | `text` | features.py:525 |
| POST | `/api/worlds/{wid}/organizations/role` | Nadanie roli member/officer (lider). | `target_id,role` | features.py:535 |
| POST | `/api/worlds/{wid}/organizations/leave` | Opuszczenie organizacji. | — | features.py:545 |
| POST | `/api/worlds/{wid}/organizations/{operation}` | Przekazanie lidera / usunięcie członka. | `target_id` | features.py:556 |
| GET | `/api/worlds/{wid}/chat/{kind}` | Odczyt czatu world/organization. | — | features.py:572 |
| POST | `/api/worlds/{wid}/chat/{kind}` | Wysłanie wiadomości na czat. | `text,client_id` | features.py:580 |
| POST | `/api/worlds/{wid}/reports` | Zgłoszenie wiadomości. | `message_id,reason` | features.py:595 |
| POST | `/api/worlds/{wid}/blocks` | Zablokowanie gracza. | `target_id` | features.py:605 |
| GET | `/api/worlds/{wid}/dm` | Lista rozmów prywatnych. | — | features.py:615 |
| GET | `/api/worlds/{wid}/dm/{pid}` | Wątek DM. | — | features.py:634 |
| POST | `/api/worlds/{wid}/dm/{pid}` | Wysłanie DM. | `text` | features.py:644 |
| POST | `/api/account/blocks/remove` | Odblokowanie konta. | `account_id` | features.py:657 |
| GET | `/api/account/security` | Sesje i bezpieczeństwo konta. | — | features.py:661 |
| POST | `/api/account/password` | Zmiana hasła. | `current_password,new_password` | features.py:669 |
| POST | `/api/account/sessions/revoke` | Unieważnienie sesji. | `password,session_id` | features.py:680 |
| POST | `/api/account/appeals` | Odwołanie od kary. | `text` | features.py:714 |
| GET | `/api/shop` | Sklep: produkty, stan, zgody, limity. | — | shop.py:117 |
| POST | `/api/shop/gate` | Włączenie/wyłączenie zakupów (oświadczenie 16+/opiekun). | `enable,statement,minor` | shop.py:133 |
| POST | `/api/shop/guardian` | Zapis zgody opiekuna z limitem tygodniowym. | `guardian_name,weekly_limit` | shop.py:148 |
| POST | `/api/shop/guardian/revoke` | Cofnięcie zgody opiekuna. | — | shop.py:157 |
| POST | `/api/shop/equip` | Założenie skórki ramki. | `skin` | shop.py:167 |
| POST | `/api/shop/checkout` | Zakup SKU (dev, bez realnych płatności). | `sku,wid` | shop.py:176 |
| POST | `/api/worlds/{wid}/travel` | Start podróży bus/auto. | `target_district,mode` | travel.py:90 |
| POST | `/api/worlds/{wid}/travel/arrive` | Zakończenie podróży. | — | travel.py:124 |
| POST | `/api/worlds/{wid}/travel/speedup` | Przyspieszenie podróży. | — | travel.py:134 |
| POST | `/api/worlds/{wid}/racing/horse` | Zakup konia. | `horse` | sports.py:143 |
| POST | `/api/worlds/{wid}/racing/breed` | Hodowla źrebaka (300 $, co 24 h). | — | sports.py:159 |
| POST | `/api/worlds/{wid}/racing/stable` | Wybór konia ze stajni. | `key` | sports.py:183 |
| POST | `/api/worlds/{wid}/racing/npc` | Wyścig z NPC. | `comp` | sports.py:195 |
| POST | `/api/worlds/{wid}/racing/open` | Otwarcie wyścigu dla graczy. | — | sports.py:212 |
| GET | `/api/worlds/{wid}/racing/open` | Lista otwartych wyścigów. | — | sports.py:225 |
| POST | `/api/worlds/{wid}/racing/join/{rid}` | Dołączenie do wyścigu. | — | sports.py:232 |
| POST | `/api/worlds/{wid}/racing/cancel/{rid}` | Odwołanie własnego wyścigu (zwrot wpisowego). | — | sports.py:254 |
| GET | `/api/worlds/{wid}/pvp/targets` | Cele PvP 2.0 (top 20). | — | pvp.py:49 |
| POST | `/api/worlds/{wid}/pvp/defense` | Sekwencja obrony PvP 2.0. | `seq` | pvp.py:67 |
| POST | `/api/worlds/{wid}/pvp/attack/{target_id}` | Atak PvP 2.0 (sekwencja 3 akcji). | `seq` | pvp.py:77 |
| POST | `/api/worlds/{wid}/dungeon/floor` | Walka na piętrze Lochu. | `seq` | dungeon.py:50 |
| POST | `/api/worlds/{wid}/sports/tournament` | Turniej bokserski (3 walki z NPC). | — | sports2.py:39 |
| POST | `/api/worlds/{wid}/sports/agility` | Agility psów. | — | sports2.py:68 |
| POST | `/api/worlds/{wid}/sports/archery` | Łucznictwo. | — | sports2.py:91 |
| POST | `/api/worlds/{wid}/sports/swim` | Pływanie (kondycja). | — | sports2.py:120 |
| GET | `/api/worlds/{wid}/sports2` | Stan dyscyplin sports2. | — | sports2.py:140 |

## Moderacja (staff) (3)

| Metoda | Ścieżka | Opis | Body | Źródło |
|---|---|---|---|---|
| GET | `/api/admin/reports` | Kolejka zgłoszeń (moderacja). | — | features.py:694 |
| POST | `/api/admin/reports/{rid}/resolve` | Rozpatrzenie zgłoszenia (wyciszenie/ban/odrzucenie). | `action,note` | features.py:701 |
| POST | `/api/staff/appeals/{aid}/resolve` | Rozpatrzenie odwołania. | `uphold,note` | features.py:728 |

## Admin (11)

| Metoda | Ścieżka | Opis | Body | Źródło |
|---|---|---|---|---|
| GET | `/api/admin/worlds/{wid}/summary` | Podsumowanie świata dla admina. | — | app.py:552 |
| GET | `/api/admin/overview` | Przegląd serwera dla admina. | — | app.py:571 |
| POST | `/api/admin/worlds` | Utworzenie świata. | `name,kind,opens_at,registration_open,speed` | app.py:574 |
| PATCH | `/api/admin/worlds/{wid}` | Zmiana rejestracji/przerwy/ogłoszenia świata. | `registration_open,maintenance,announcement` | app.py:584 |
| PATCH | `/api/admin/accounts/{uid}` | Ban / nadanie moderatora. | `banned,moderator` | app.py:590 |
| POST | `/api/admin/notices` | Ogłoszenie admina. | `text,world_id` | app.py:713 |
| POST | `/api/admin/notices/{nid}/delete` | Usunięcie ogłoszenia. | — | app.py:722 |
| GET | `/api/admin/backups` | Lista kopii bazy. | — | features.py:739 |
| POST | `/api/admin/backups` | Utworzenie kopii bazy. | — | features.py:741 |
| POST | `/api/admin/events` | Event miejski admina. | `world_id,name,description,kind,district,target,hours` | city_events.py:104 |
| POST | `/api/admin/events/{eid}/cancel` | Anulowanie eventu. | — | city_events.py:126 |

Uwaga: limity zapytań (`rate(...)`) opisano w Raporcie 2; `actions` przyjmuje `action` z 27 wartości (Raport 5).