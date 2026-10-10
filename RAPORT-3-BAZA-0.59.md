# Raport 3 — Baza danych (v0.59.0)

SQLite (WAL), plik `data/city_empire.sqlite3` (596 KB w środowisku dev). Tabel: **43**. 🔑 = klucz główny.

| # | Tabela | Kolumny |
|---|---|---|
| 1 | `accounts` | 🔑id:INTEGER, username:TEXT, password_hash:TEXT, role:TEXT, banned:INTEGER, created_at:INTEGER, deletion_at:INTEGER, consent:TEXT, ip_hash:TEXT |
| 2 | `appeals` | 🔑id:INTEGER, account_id:INTEGER, text:TEXT, status:TEXT, resolution:TEXT, created_at:INTEGER, resolved_at:INTEGER, resolved_by:INTEGER |
| 3 | `audit` | 🔑id:INTEGER, actor_id:INTEGER, event:TEXT, details:TEXT, created_at:INTEGER |
| 4 | `challenges` | 🔑id:INTEGER, world_id:INTEGER, attacker_id:INTEGER, defender_id:INTEGER, attacker_snapshot:TEXT, status:TEXT, created_at:INTEGER, expires_at:INTEGER |
| 5 | `char_daily` | 🔑character_id:INTEGER, 🔑day:INTEGER, deeds:INTEGER, cash:INTEGER, xp:INTEGER |
| 6 | `character_titles` | 🔑id:INTEGER, character_id:INTEGER, season:INTEGER, code:TEXT, label:TEXT, granted_at:INTEGER |
| 7 | `characters` | 🔑id:INTEGER, account_id:INTEGER, world_id:INTEGER, nickname:TEXT, state_json:TEXT, rating:REAL, wins:INTEGER, losses:INTEGER, draws:INTEGER, created_at:INTEGER, class_type:TEXT, class_evolution:INTEGER, current_location:TEXT, dungeon_progress:INTEGER, current_district:INTEGER, travel_destination:INTEGER, travel_until:INTEGER, travel_mode:TEXT, travel_started:INTEGER |
| 8 | `chat_messages` | 🔑id:INTEGER, world_id:INTEGER, org_id:INTEGER, author_id:INTEGER, body:TEXT, client_id:TEXT, created_at:INTEGER, hidden:INTEGER |
| 9 | `chat_mutes` | 🔑account_id:INTEGER, until_at:INTEGER |
| 10 | `chat_reports` | 🔑id:INTEGER, message_id:INTEGER, reporter_id:INTEGER, reason:TEXT, status:TEXT, note:TEXT, created_at:INTEGER, resolved_at:INTEGER |
| 11 | `chronicle` | 🔑id:INTEGER, world_id:INTEGER, kind:TEXT, title:TEXT, description:TEXT, district:TEXT, created_at:INTEGER |
| 12 | `city_events` | 🔑id:INTEGER, world_id:INTEGER, name:TEXT, description:TEXT, kind:TEXT, district:TEXT, target:INTEGER, baseline:INTEGER, deadline:INTEGER, status:TEXT, created_by:INTEGER, created_at:INTEGER, done_at:INTEGER |
| 13 | `daily_actions` | 🔑character_id:INTEGER, 🔑day:INTEGER, kind:TEXT, updated_at:INTEGER |
| 14 | `daily_distinctions` | 🔑id:INTEGER, character_id:INTEGER, world_id:INTEGER, day:INTEGER, kind:TEXT, created_at:INTEGER |
| 15 | `dm_messages` | 🔑id:INTEGER, world_id:INTEGER, sender_id:INTEGER, recipient_id:INTEGER, body:TEXT, created_at:INTEGER, read_at:INTEGER |
| 16 | `game_events` | 🔑id:INTEGER, world_id:INTEGER, character_id:INTEGER, kind:TEXT, payload:TEXT, created_at:INTEGER, read_at:INTEGER |
| 17 | `guardian_consents` | 🔑id:INTEGER, account_id:INTEGER, guardian_name:TEXT, weekly_limit:INTEGER, created_at:INTEGER, revoked_at:INTEGER |
| 18 | `horse_races` | 🔑id:INTEGER, world_id:INTEGER, kind:TEXT, creator_id:INTEGER, creator_json:TEXT, opponent_id:INTEGER, status:TEXT, entry:INTEGER, pot:INTEGER, seed:INTEGER, result_json:TEXT, created_at:INTEGER, finished_at:INTEGER |
| 19 | `investments` | 🔑character_id:INTEGER, 🔑district:TEXT, total:INTEGER |
| 20 | `matches` | 🔑id:INTEGER, world_id:INTEGER, challenge_id:INTEGER, attacker_id:INTEGER, defender_id:INTEGER, report_json:TEXT, created_at:INTEGER |
| 21 | `meta` | 🔑key:TEXT, value:TEXT |
| 22 | `notices` | 🔑id:INTEGER, world_id:INTEGER, text:TEXT, author_id:INTEGER, created_at:INTEGER |
| 23 | `operations` | 🔑account_id:INTEGER, 🔑world_id:INTEGER, 🔑key:TEXT, request_hash:TEXT, response_json:TEXT, created_at:INTEGER |
| 24 | `org_applications` | 🔑id:INTEGER, org_id:INTEGER, character_id:INTEGER, text:TEXT, status:TEXT, created_at:INTEGER, expires_at:INTEGER |
| 25 | `org_contracts` | 🔑id:INTEGER, world_id:INTEGER, org_id:INTEGER, kind:TEXT, district:TEXT, target:INTEGER, base:INTEGER, deadline:INTEGER, status:TEXT, created_by:INTEGER, created_at:INTEGER, done_at:INTEGER |
| 26 | `org_investments` | 🔑org_id:INTEGER, 🔑district:TEXT, total:INTEGER |
| 27 | `org_invites` | 🔑id:INTEGER, org_id:INTEGER, target_id:INTEGER, status:TEXT, created_at:INTEGER, expires_at:INTEGER |
| 28 | `org_members` | 🔑character_id:INTEGER, org_id:INTEGER, joined_at:INTEGER, role:TEXT |
| 29 | `organizations` | 🔑id:INTEGER, world_id:INTEGER, name:TEXT, tag:TEXT, description:TEXT, leader_id:INTEGER, created_at:INTEGER, buildings:TEXT, fund:INTEGER, announcement:TEXT |
| 30 | `pvp_battles` | 🔑id:INTEGER, world_id:INTEGER, attacker_id:INTEGER, defender_id:INTEGER, report_json:TEXT, rating_json:TEXT, created_at:INTEGER |
| 31 | `ranked_usage` | 🔑character_id:INTEGER, 🔑day:INTEGER, used:INTEGER |
| 32 | `rate_limits` | 🔑key:TEXT, count:INTEGER, until_at:INTEGER |
| 33 | `season_archive` | 🔑season:INTEGER, 🔑world_id:INTEGER, payload:TEXT, created_at:INTEGER |
| 34 | `sessions` | 🔑token_hash:TEXT, account_id:INTEGER, csrf:TEXT, expires_at:INTEGER, sid:TEXT, created_at:INTEGER, last_seen:INTEGER |
| 35 | `shop_purchases` | 🔑id:INTEGER, account_id:INTEGER, sku:TEXT, price:TEXT, status:TEXT, world_id:INTEGER, created_at:INTEGER, cents:INTEGER |
| 36 | `shop_state` | 🔑account_id:INTEGER, spending_enabled:INTEGER, enabled_at:INTEGER, vip_until:INTEGER, starter:INTEGER, skin:TEXT |
| 37 | `shop_usage` | 🔑account_id:INTEGER, 🔑sku:TEXT, 🔑day:INTEGER, count:INTEGER |
| 38 | `social_blocks` | 🔑account_id:INTEGER, 🔑target_account:INTEGER, display_name:TEXT, created_at:INTEGER |
| 39 | `territory_log` | 🔑id:INTEGER, world_id:INTEGER, district:TEXT, org_id:INTEGER, prev_org_id:INTEGER, at:INTEGER |
| 40 | `territory_state` | 🔑world_id:INTEGER, 🔑district:TEXT, org_id:INTEGER, since:INTEGER |
| 41 | `vehicles` | 🔑id:INTEGER, character_id:INTEGER, type:TEXT, condition:INTEGER, speed_bonus:INTEGER |
| 42 | `world_daily` | 🔑world_id:INTEGER, 🔑day:INTEGER, deeds:INTEGER, cash:INTEGER, xp:INTEGER, shop_cents:INTEGER |
| 43 | `worlds` | 🔑id:INTEGER, name:TEXT, kind:TEXT, opens_at:INTEGER, registration_open:INTEGER, speed:INTEGER, maintenance:INTEGER, announcement:TEXT, created_at:INTEGER, world_era:INTEGER |

## Klucze `characters.state_json`

| Klucz | Typ | Znaczenie | Źródło |
|---|---|---|---|
| version | int | wersja schematu stanu (1) | economy.py:183 |
| offset | int | przesunięcie zegara (testy) | economy.py:183 |
| lastTick | ms | ostatnia synchronizacja (nie cofa się) | economy.py:225 |
| cash | int | gotówka $ | economy.py:183 |
| xp | int | doświadczenie (poziom liczony z xp, nie zapisywany) | economy.py |
| energy | float | energia 0–240 | economy.py:225 |
| stats | [5] | Siła, Inteligencja, Refleks, Charyzma, Spryt | economy.py:183 |
| business | obj | City Courier {level, vault, upgrade} | economy.py:183 |
| contracts | list | kolejka kontraktów (max 4) | economy.py:301 |
| training | list | kolejka treningów (max 4) | economy.py:324 |
| inventory / equipped | list / obj | przedmioty i 7 slotów | economy.py:183 |
| completed | obj | liczniki contracts/training/collected/rests | economy.py |
| sequence | int | licznik id zadań | economy.py |
| history | list | dziennik zdarzeń | economy.py |
| ventures | obj | cafe / studio (null = nie kupiono) | economy.py:229 |
| tutorialDismissed | bool | samouczek zamknięty | economy.py:373 |
| residence, rest | id / obj | rezydencja, trwający odpoczynek | economy.py:204 |
| lastAction | ms | ostatnia akcja | economy.py:204 |
| vehicle, garage, garageUp | obj / list / obj | auto w użyciu (wear), garaż, ulepszenia | economy.py:204 |
| staff | obj | pracownicy: klucz → koniec umowy | economy.py:204 |
| invested | obj | prywatne inwestycje w dzielnice | economy.py:204 |
| tenderDone | day | dzień przyjęcia przetargu | economy.py:204 |
| materials | obj | tworzywa/ruda/drewno | economy.py:212 |
| buildings | obj | residence/garage/cafe/gym/club 1–5, hall 0/1 | economy.py:93 |
| horse | obj | aktywny koń | sports.py |
| pvpDefense | list | sekwencja obrony PvP 2.0 | pvp.py |
| npcRoutes | obj | runs, done, cash, xp | economy.py:216 |
| ally | obj | poziomy budynków sojuszu (kopia) | economy.py:117 |
| avatar | obj | body, worn, owned | app.py:392 |
| breedAt | ms | blokada hodowli 24 h | sports.py:179 |
| dungeonLoot | list | unikaty z Lochu | dungeon.py:77 |
| evolutionCode | str | ewolucja klasy | features.py:315 |
| horses | obj | stajnia | sports.py:153 |
| restInstant | int | natychmiastowy odpoczynek (starter) | shop.py:210 |
| sports2 | obj | tourn, agil, luk, swim | sports2.py |
| tactic | str | taktyka walki 1.0 | app.py:457 |
| vipUntil | ms | VIP do | app.py:388, shop.py:109 |

## Przykład stanu nowej postaci (świat zwykły)

```json
{
 "version": 1,
 "offset": 0,
 "lastTick": 1780000000000,
 "cash": 300,
 "xp": 0,
 "energy": 120.0,
 "stats": [
  10,
  10,
  10,
  10,
  10
 ],
 "business": {
  "level": 1,
  "vault": 0,
  "upgrade": null
 },
 "contracts": [],
 "training": [],
 "inventory": [
  "basic-gloves",
  "basic-shirt",
  "basic-shoes",
  "basic-accessory",
  "basic-helmet",
  "basic-backpack",
  "basic-amulet"
 ],
 "equipped": {
  "gloves": "basic-gloves",
  "shirt": "basic-shirt",
  "shoes": "basic-shoes",
  "accessory": "basic-accessory",
  "helmet": "basic-helmet",
  "backpack": "basic-backpack",
  "amulet": "basic-amulet"
 },
 "completed": {
  "contracts": 0,
  "training": 0,
  "collected": 0,
  "rests": 0
 },
 "sequence": 0,
 "history": [],
 "ventures": {
  "cafe": null,
  "studio": null
 },
 "tutorialDismissed": false,
 "residence": null,
 "rest": null,
 "lastAction": 1780000000000,
 "vehicle": null,
 "garage": [],
 "garageUp": {},
 "staff": {},
 "invested": {},
 "tenderDone": null,
 "materials": {
  "tworzywa": 0,
  "ruda": 0,
  "drewno": 0
 },
 "buildings": {
  "residence": 1,
  "garage": 1,
  "cafe": 1,
  "gym": 1,
  "club": 1,
  "hall": 0
 },
 "horse": null,
 "pvpDefense": null,
 "npcRoutes": {
  "runs": [],
  "done": 0,
  "cash": 0,
  "xp": 0
 }
}
```

Świat testowy: cash 3000, energy 240 (economy.py:183).
