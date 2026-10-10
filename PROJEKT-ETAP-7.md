# Projekt Etap 7: Ekwipunek, sety, crafting, sklep, kupony, i18n [GDD v3.1 7.1–7.6]

## Decyzje usera (ask_user)
- **Sety:** 9 setów w tierach T1–T4. Każdy set ma wszystkie 8 slotów (czapka, koszulka, rękawice, naszyjnik, pierścionek, pasek, spodnie, buty). Komplet = 8 części daje +30%.
- **Crafting:** wynik losowy na każdym etapie, także Niebieski→Fioletowy za 💎. User akceptuje ryzyko; flaga prawna opisana w raporcie.
- **Sklep:** kupony są stałymi produktami. Oferta przedmiotów to 8 losowych sztuk z rotacją co 6 h. Gracz widzi, co kupuje, więc nie ma płatnej losowości.
- **Stare przedmioty:** sety zastępują stary sklep. Akcja `buy` dostaje 409 (flaga `E.LEGACY_SHOP_OPEN=False`), a przedmioty graczy zostają.

## Interpretacje (do potwierdzenia)
1. **Podział 9 setów:** T1 = 3, T2 = 2, T3 = 2, T4 = 2, bo 9 nie dzieli się na 4.
2. **Wartości w specyfikacji traktuję jako bonus jednej części przy poziomie 1:**
   - T1: +3 do jednej statystyki;
   - T2: +4 i +3;
   - T3: +7 do statystyki klasowej;
   - T4: tryb A +5 do wszystkich albo tryb B +12 do klasowej.
3. **Skalowanie z poziomem:** bonus × (1 + 0,02·(lvl−1)). Na lvl 26 daje to ×1,5.
4. **Statystyka klasowa:** Bokser → Siła, Obrońca → Inteligencja, Szybki → Refleks.
5. **Pojemność plecaka:** start 5 miejsc.
   - Za $: miejsca 6–10 na poziomach 5/10/15/20/25, kolejno 500/1500/5000/15000/50000 $.
   - Za 💎: miejsca 11–15, kolejno 50/100/200/400/800 💎, dopiero po wykupieniu wszystkich miejsc za $.
   - Limit dotyczy tylko kupowania. Nagrody z Lochu i crafting mogą przekroczyć limit, żeby nic nie przepadło.
6. **Szansa 5%/3% na kupon przy zakupie:** zastąpiona stałymi kuponami w sklepie.
7. **Kupon Kontrakt +10%:** następny odebrany kontrakt daje +10% $ i XP. Zastępuje to „+10% statystyk”, bo wypłata kontraktu i tak zależy od statystyk.
8. **Kupon XP:** podwaja XP z akcji (kontrakty, treningi) przez 1 h. Nie dotyczy PvP ani Lochu.
9. **i18n:** tłumaczone są nazwy i komunikaty nowych modułów (sety, sloty, tiery, błędy ekwipunku). Pełne tłumaczenie istniejących polskich tekstów to osobny duży zakres (proponuję Etap 8).
10. **Waluty:** przelicznik służy tylko do wyświetlania cen SKU (zakupy domyślnie OFF, PLN zablokowane). Kursy są stałe w konfiguracji.

## Ceny setów
| Tier | Kolor | Poziom | Cena |
|---|---|---|---|
| T1 | szary | 1 | 400 $ |
| T2 | zielony | 5 | 1500 $ |
| T3 | niebieski | 10 | 6000 $ albo 3000 $ + 15💎 |
| T4 | fioletowy | 15 | 20000 $ + 60💎 |

**Kupony:**
- XP: 3000 $ albo 15💎;
- Natychmiastowa Akcja: 1500 $ albo 8💎;
- Kontrakt: 2000 $ albo 10💎.

## Architektura
- Nowy moduł `server/gear.py`: katalog 72 przedmiotów, bonusy, endpointy.
- `E.effective` dolicza `GEAR_HOOK(s)`; nieznane id przedmiotów są pomijane zamiast rzucać StopIteration.
- **Stan postaci:**
  - `s['backpack']`: plecak, lista z duplikatami;
  - `s['equipped'][slot]`;
  - `s['gearModes']`: tryb T4 per slot;
  - `s['bagUnlocks']`: `{cash, dia}`;
  - `s['coupons']`;
  - `s['xpBoostUntil']`, `s['contractBoost']`;
  - `s['shopBought']`.
- **Stare sloty:**
  - założenie `head` zdejmuje stary `helmet`, założenie `ring` zdejmuje `accessory`;
  - stary `backpack` (slot) zostaje do czasu Fluttera.
- **Loch:** pula dropu Normal przechodzi na sety.
  - serie 1–5: zwykli dają T1, bossowie T2;
  - serie 6–10: zwykli dają T2, bossowie T3;
  - unikaty serii 1 zostają.
- **Endpointy (`/api/worlds/{wid}/…`):**
  - GET: `gear`, `gear/shop`;
  - POST: `gear/equip`, `gear/unequip`, `gear/bag/unlock`, `gear/craft`, `gear/shop/buy`, `gear/coupon/use`.
- **Endpointy globalne:** GET `/api/i18n/{lang}`, GET `/api/shop/prices?currency=`, POST `/api/account/language`.
- **Migracja:** kolumna `accounts.language` (NULL = nagłówek `Accept-Language`, domyślnie pl).
