# REAL-STORE — projekt integracji sklepów (Play Billing / Apple IAP)

**Status: DOKUMENT PLANU. Nic z poniższego nie jest zaimplementowane ani uruchomione.**
Twarda zasada obowiązująca od 0.14 i nienaruszalna w wersji deweloperskiej: **kasa pozorowana
(`paid_dev`), zero prawdziwych płatności**. Ten dokument opisuje, co musiałoby powstać — i co
zostało już przygotowane projektowo — zanim w ogóle zadecydujemy o starcie real-store.

Wersje: uzupełnione w 0.22. Podstawa zgodności: MONETYZACJA.md (decyzje 0.14, CPC, RODO art. 8).

---

## 1. Zakres produktów (mapowanie na istniejące SKU)

| SKU | Typ | Realizacja w sklepie |
|---|---|---|
| vip30 / vip7 | trwała (okresowa) subskrypcja jednorazowa | produkt niestronicowany na konto gracza; okresy sumują się (logika `vip_until` już jest) |
| starter | jednorazowy na konto/świat | non-consumable; flaga `starter` już zapobiega duplikatom |
| energy / speedup | konsumowalne z limitem dziennym | consumable; limity 2/dobę i 3/dobę UTC liczone serwerowo (już są) |
| skin_copper / gold / neon | trwałe kosmetyki | non-consumable; własność w `shop_purchases` (już jest) |

Bez zmian pozostaje oferta: **6 produktów**, ceny 2,99–19,99 zł widoczne przed zakupem.

## 2. Architektura docelowa (wspólna dla obu sklepów)

1. Klient kupuje w sklepie platformy (Play Billing / StoreKit) — **aplikacja nigdy nie dotyka
   bramek płatniczych ani kart**.
2. Serwer waliduje paragon/podpis zakupu (Google Play Developer API / App Store Server API)
   **serwerowo**, idempotentnie (unikalne transaction/order id), dopiero potem przyznaje efekt
   (ta sama ścieżka co dzisiejszy `shop_checkout`, ale z realnym `status='paid'`).
3. `shop_purchases` zyskuje kolumny: `store` ('play'|'appstore'), `store_tx_id` UNIQUE,
   `receipt_payload` (skrót), `refunded_at`. Migracja additive, zgodna z obecną strukturą.
4. Zwroty: webhook/ankieta stanu zakupu → oznaczenie `refunded_at` + odebranie efektu
   kosmetycznego/okresowego (VIP wygasa naturalnie; skórka blokowana; konsumowane — bez odbioru,
   zgodnie z praktyką platform).

## 3. Google Play — wymagania do spełnienia przy etapie real-store

- **Play Billing** dla wszystkich dóbr cyfrowych (żadnych obejść; alternatywne programy
  rozliczeniowe — tylko jeśli kiedyś dostępne i warunkowe, decyzja osobna).
- **Grupa docelowa vs Families:** gra jest dla nastolatków i dorosłych, **nie deklarujemy „dla
  dzieci"** (ranking wiekowy uczciwy: teen/12+). Gdyby kiedykolwiek wybrano „wszystkie wieki",
  obowiązują wymagania Families (SDK dziecięce, ograniczenia reklam) — obecnie niepotrzebne.
- **Data safety + polityka prywatności**: sekcja płatności (dane transakcji u operatora sklepu),
  RODO art. 8 (próg 16 lat w PL, zgoda opiekuna — zrealizowane w 0.19), usuwanie konta w aplikacji
  (**zrealizowane wcześniej**: panel konta → usuwanie z potwierdzeniem hasła).
- Kwestionariusz zawartości: UGC (czat) — **moderacja, zgłoszenia i blokady już istnieją**;
  opisać je w deklaracji.

## 4. Apple App Store — wymagania do spełnienia przy etapie real-store

- **IAP** dla wszystkich dóbr cyfrowych (bez linków do zewnętrznych płatności, chyba że program
  alternatywny obejmie nasz region — decyzja osobna, ryzykowna).
- **§5.1.1(v): usuwanie konta w aplikacji** — od 30.06.2022 obowiązkowe; **już zrealizowane**.
- **§1.2 UGC**: filtrowanie, zgłoszenia, blokady, szybka reakcja, kontakt publiczny —
  **fundamenty istnieją** (moderatorzy, zgłoszenia czatu i ogłoszeń, blokady kont); przed
  submitem dopracować SLA reakcji i widoczność kontaktu.
- Review Kids: **nie aplikować** (nie targetujemy dzieci); ostrożnie z hasłami marketingowymi
  skierowanymi do dzieci — CPC (Star Stable) karano właśnie za bezpośrednie apele zakupowe do dzieci.

## 5. CPC / UE — stan i braki do domknięcia dopiero przy real-store

Zasady CPC (21.03.2025) vs nasz produkt:
- ✅ ceny w PLN widoczne przed zakupem (bez zacierania kosztów, bez wymuszonej nadwyżki waluty —
  nie mamy waluty pośredniej w ogóle);
- ✅ zero lootboxów i zero presji czasu (odliczanie liczników zakupowych nie istnieje);
- ✅ zakupy domyślnie wyłączone (brama + oświadczenie + zgoda opiekuna dla <16);
- ⬜ **prawo odstąpienia** i informacja o warunkach zwrotu w UI — do dorobienia przy etapie
  real-store (pole tekstowe + ścieżka reklamacyjna w panelu konta);
- ⬜ jasne rozróżnienie w komunikatach: „płacisz sklepowi platformy, nie nam bezpośrednio".

## 6. Kolejność prac (po decyzji biznesowej)

1. Audyt prawny oferty i komunikatów (PL/UE) + decyzja podmiotu sprzedającego i regionów.
2. Konta deweloperskie sklepów, umowy, podatki/vat na dobra cyfrowe.
3. Implementacja serwerowej walidacji paragonów (idempotentna) + migracja additive z pkt 2.
4. Klient: Play Billing / StoreKit; flaga konfiguracyjna `payments: real|dev` — dev zostaje jako
   tryb testowy na zawsze.
5. Soft-launch: jeden produkt (np. VIP 7) na zamkniętej grupie; dopiero potem pełna oferta.
6. Telemetria nadużyć (zwroty, refund abuse) i dopiero wtedy skale decyzje o promocjach.

## 7. Ryzyka / otwarte pytania (decyzje właściciela)

- prowizje sklepów (15–30%) vs cena netto; możliwa korekta cennika przy wejściu do sklepów;
- podatek/regiony (UE: cyfrowe usługi — VAT miejsca konsumenta);
- czy w ogóle wchodzić na sklepy przed zakończeniem fazy testowej — produkt jest oznaczony
  jako wersja rozwojowa w wielu miejscach UI (banery, stopki, disclaimer);
- obsługa zwrotów i reklamacji wymaga kanału kontaktu ze graczami (obecnie brak stałego wsparcia).

**Decyzja o starcie real-store jest świadomie odłożona.** Wersja dev nie ucierpi: ścieżka
`paid_dev` pozostaje trybem testowym i edukacyjnym także po ewentualnym starcie sklepów.
