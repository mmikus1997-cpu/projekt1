# MONETYZACJA — projekt 0.8 (bez kodu sklepu)

**Status: dokument projektowy. Gra niczego nie sprzedaje; żadna płatność nie jest podłączona.**

Przyjęty kierunek (zaakceptowany przez Ciebie): dopuszczamy **płatne przyspieszenia wpływające
na tempo rozwoju, siłę i rywalizację** — nie zmieniamy go na wyłącznie kosmetyczny. Osiągnięcia
pozostają kosmetyczne. Poniższe liczby są propozycjami do osobnej decyzji, nie decyzjami.

## 1. Oferta

| Produkt | Treść | Cena (projekt) | Uzasadnienie |
|---|---|---|---|
| VIP · subskrypcja 30 dni | +25% gotówki z kontraktów, złota rama profilu, powiadomienia push | 19,99 zł | stały dochód, przewaga umiarkowana i widoczna cenowo |
| VIP · pakiet 7 dni | to samo, krócej | 7,99 zł | próg wejścia niższy |
| Pakiet startowy (raz) | 5 000 $, zestaw Specjalistyczne, natychmiastowy odpoczynek | 9,99 zł | jednorazowo na konto, klasyczny „starter” |
| Energiapak | +100 energii natychmiast (limit 2/dzień) | 4,99 zł | opcjonalna energia z Twojej listy; limit chroni rytm gry |
| Przyspieszenie zlecenia | skróć trwające zlecenie o 50% (limit 3/dzień) | 2,99 zł | płatna akceleracja wpływa na tempo, nie zmienia wyników PvP |
| Skórki i stroje | rękawice/strój z efektami wizualnymi na arenie | 3,99–9,99 zł | czysto kosmetyczne, zero statystyk |

Zasady graniczne: żadnych losowych pudełek (brak mechanizmu lootbox i związanych z nim projektów
regulacji), żadnej sprzedaży waluty pośredniej w 1. wersji (prostsza transparentność cen),
bez ofert „tylko teraz” liczonych w minutach.

## 2. Zgodność — wiążące wymagania, nie opisy

- **Ceny zawsze w prawdziwej walucie, widoczne przed zakupem** — zasada koordynowanej akcji CPC
  przeciwko grom (2025): jasna cena oferty zakupu waluty i dóbr za nią, także przy wymianach
  pośrednich; nie zmuszamy do kupowania nadwyżek.
- **Presja czasowa**: koordynowana akcja CPC wskazała nierówność „ofert ograniczonych czasowo”
  (sprawa Star Stable). Nasze pakiety są stałe w sklepie; sezonowe motywy pokazujemy z datą
  początkową i końcową, bez odliczajek naciskających na dziecko.
- **Dzieci**: publiczność to nastolatki i dorośli. Zakupy: domyślnie wyłączone wydatki na
  prawdziwe pieniądze dla kont oznaczonych jako młodsze, brak bezpośrednich zachęt do kupowania
  lub proszenia rodziców (zgodnie z zasadami CPC publikowanymi 21.03.2025).
- **RODO, art. 8**: dla usług oferowanych bezpośrednio dzieciom poniżej 16 lat podstawą przetwarzania
  zgoda rodzica (Polska przyjęła próg 16 lat). Wymaga to projektu zgody opiekuna przed zakupami —
  wpisane do listy zadań, nie do kodu.
- **Apple §1.2 / §5.1.1(v), Google Families/Play Billing**: digital goods wyłącznie przez Play Billing
  / IAP sklepu; filtry, zgłoszenia i blokady już mamy; usuwanie konta w aplikacji już jest
  (z karencją do zaprojektowania). Klasyfikacja wiekowa i kwestionariusze sklepów — osobny etap.
- **Polska**: projekt ustawy o losowości płatnych przedmiotów wirtualnych pozostaje projektem
  (sejm.gov.pl, druk 2356) — nie losem; i tak nie planujemy losowych pudełek.

## 2a. Decyzje podjęte (0.14) — obowiązujące

- **Oferta: pełna tabela z sekcji 1** (6 produktów, ceny jak w tabeli: 19,99 / 7,99 / 9,99 / 4,99 / 2,99 / 3,99–9,99 zł).
- **Energiapak: limit 2/dobę UTC** (zgodnie z projektem).
- **Zakupy domyślnie WYŁĄCZONE dla każdego konta**; włączenie wymaga oświadczenia „16+ albo zgoda opiekuna"
  (dev-stub ścieżki z RODO art. 8). Wyłączenie w każdej chwili, z audytem.
- **Sklep dev działa** (zakładka „Sklep"): realne ceny w zł widoczne zawsze przed zakupem, kasa pozorowana
  (status zamówienia `paid_dev`), pełny audyt z ceną, **zero prawdziwych płatności**. W produkcji: wyłącznie
  Play Billing / Apple IAP — własna bramka odpada w 1. wersji.
- Zaimplementowane efekty: VIP +25% gotówki z kontraktów (działa na wszystkie postacie konta, okresy się sumują),
  pakiet startowy raz na konto (+5 000 $, zestaw Specjalistyczne, 1× natychmiastowy odpoczynek),
  Energiapak (+100, klamra 240, limit 2/dzień), przyspieszenie zlecenia o połowę (limit 3/dzień),
  skórki ramki profilu (kosmetyka, zero statystyk).

## 3. Lista zadań do przyszłego etapu (w kolejności)

1. Decyzja o cenniku i limicie Energiapaka (powyższa tabela jako punkt wyjścia).
2. Projekt zgody opiekuna (RODO art. 8) i domyślne wyłączone zakupy dla młodszych kont.
3. Implementacja sklepów: Play Billing + Apple IAP + brak własnej bramki płatności w 1. wersji.
4. Testy i kwestionariusze sklepów (ranking wiekowy, Families), polityka prywatności z sekcją płatności.
5. Telemetria i reagowanie na nadużycia (zwroty, refund abuse) — po uruchomieniu.

Nic z powyższego nie rusza bieżącego kodu: sklep pojawi się jako osobny moduł po Twojej decyzji
o cenniku i zgodności.

---

## 4. Realizacja 0.19 — zgoda opiekuna (RODO art. 8) w produkcie

Zrealizowane w wersji deweloperskiej (kasa pozorowana, bez prawdziwych płatności):

- **Ścieżka <16 lat w bramce zakupów**: oświadczenie + deklaracja wieku; dla osób poniżej 16 lat włączenie zakupów wymaga zapisanej zgody opiekuna (serwer odmawia 422 bez zgody).
- **Zgoda opiekuna**: imię i nazwisko opiekuna (3–60 znaków) + tygodniowy limit wydatków 5–200 zł (presety: 5/10/20/50). Jedna aktywna zgoda na konto (indeks częściowy); tabela `guardian_consents` — migracja additive.
- **Limit tygodniowy egzekwowany serwerowo** przy każdym zakupie (poniedziałek 00:00 UTC jako początek tygodnia; nadwyżka → 409 z komunikatem po polsku). Wydatki liczone numerycznie (grosze) w `shop_purchases.cents`.
- **Cofnięcie zgody** (panel sklepu → dialog potwierdzenia) natychmiast wyłącza zakupy na koncie — zgodnie z zasadą, że to opiekun decyduje. Ślad w dzienniku: `shop.guardian_consent`, `shop.guardian_revoke`.
- Ścieżka 16+ bez zmian (jedno oświadczenie); starsze konta nie mają dodatkowego typu „opiekun".

## 5. Projekty sklepów — etap real-store (PLAN, nic z tego nie jest uruchomione)

Twarda zasada: wersja deweloperska nigdy nie dotyka prawdziwych płatności. Poniższa lista to przygotowanie
do przyszłego etapu (osobna decyzja, osobny kod, osobne konta sklepów):

1. **Google Play**: integracja Play Billing dla dóbr cyfrowych (VIP, pakiety, skórki — wyłącznie w tej samej aplikacji); deklaracja grupy docelowej i ranking wiekowy; jeśli „dla wszystkich" — wymagania Families (SDK dziecięce, domyślne wyłączone wydatki — już spełnione projektowo); usuwanie konta w aplikacji (już jest: panel konta); polityka prywatności z sekcją płatności i RODO art. 8.
2. **Apple App Store**: IAP dla dóbr cyfrowych; reguła usuwania konta w aplikacji (§5.1.1(v), od 30.06.2022 — spełnione); filtrowanie/zgłaszanie UGC (czat już ma zgłoszenia i moderację); przegląd Kids wymaga osobnej decyzji — nie deklarować „dla dzieci" bez potrzeby.
3. **CPC/UE**: ceny w PLN widoczne przed zakupem (jest); bez losowości płatnej (jest: zero lootboxów); bez presji czasu (jest); jasność przewalutowań (nie dotyczy: brak waluty pośredniej); prawo odstąpienia i zwroty — dopiero przy realnych płatnościach; zakupy domyślnie wyłączone (jest).
4. **Kolejność wdrożenia**: (a) audyt prawny oferty i komunikatów, (b) konta deweloperskie sklepów + podatek/regiony, (c) biblioteki rozliczeń + walidacja paragonów serwerowo, (d) soft-launch na jednym produkcie, (e) dopiero potem pełna oferta.

Status: punkty 1–3 to wymagania i mapowanie na istniejące funkcje; punkt 4 wymaga osobnej decyzji biznesowej. Żaden element nie jest implementowany w tym repo do czasu tej decyzji.
