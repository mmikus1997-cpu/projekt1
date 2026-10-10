# CITY EMPIRE
## Pięć statystyk i sportowe PvP — projekt v0.2

**Status:** propozycja do prototypu, nie zatwierdzony balans produkcyjny.
**Powiązanie:** „Ekonomia pierwszych siedmiu dni v0.1”.
**Wykonana weryfikacja:** 300 000 pojedynków modelu v0.2, po 20 000 dla każdego z 15 scenariuszy. Wcześniej sprawdzono 220 000 pojedynków wzoru v0.1. Nie są to testy z użytkownikami ani testy gotowej aplikacji.

## 1. Założenia

- Gracz nie wybiera niezmiennej klasy.
- Pojedynek jest automatyczny; przed startem znaczenie mają statystyki, wyposażenie i taktyka.
- Backend rozstrzyga walkę, a interfejs odtwarza raport. Pominięcie animacji nie zmienia wyniku.
- Płatne przyspieszenie może zwiększać siłę. Silnik walki nie sprawdza kwoty wydanej przez gracza i nie manipuluje wynikiem według zakupów.
- Walka ma stylizowaną oprawę sportową bez krwi i śmierci. HP opisujemy jako kondycję w danym pojedynku.
- Rywalizacja sportowa nie jest obowiązkowa do rozwijania przedsiębiorstw.
- Nie wprowadzamy zakładów, płatnego ponawiania wyniku ani odbierania majątku pokonanemu.

## 2. Statystyki

| Statystyka | Znaczenie w pojedynku v0.2 | Kierunek zastosowań poza walką — jeszcze bez mnożników |
|---|---|---|
| Siła | Podstawowe obrażenia | Kontrakty fizyczne, wymagania wyposażenia sportowego |
| Inteligencja | Obrona techniczna, mniejsze otrzymywane obrażenia | Planowanie, kontrakty specjalistyczne, zarządzanie |
| Refleks | Trafienie, unikanie trafień i kolejność akcji | Precyzja, zawody czasowe, wybrane kontrakty |
| Charyzma | Opanowanie i determinacja; większa pula kondycji | Negocjacje, relacje z klientami, organizacje |
| Spryt | Trafienia krytyczne i niewielki wkład w obrażenia | Wybór rozwiązań kontraktu, wyzwania strategiczne |

Wpływ charyzmy na kondycję to umowna mechanika gry, nie twierdzenie o fizjologii. Powinien być wyjaśniony w interfejsie jako utrzymanie opanowania podczas rywalizacji.

Zastosowania gospodarcze wymagają osobnego projektu. Nie dodajemy ich potajemnie do poprzedniej ekonomii: każda premia do przychodu zmienia obliczenia siedmiu dni.

## 3. Malejący wpływ statystyk na walkę

Pierwszy wzór używający statystyk bezpośrednio dawał zbyt jednostronne starcia. Zamiast zmieniać zaakceptowany kierunek płatnego przyspieszenia, sprawdzono malejący wpływ kolejnych punktów.

Dla każdej statystyki surowej x:

**W(x) = 10 + 10 × ln(x / 10)**

W tym prototypie x wynosi co najmniej 10; brak kar obniżających statystyki poniżej tej wartości. ln oznacza logarytm naturalny. Gdy w przyszłości pojawią się debuffy, trzeba jawnie ustalić dolne ograniczenia.

| Statystyka surowa | Wartość używana przez walkę, około |
|---|---:|
| 10 | 10,00 |
| 20 | 16,93 |
| 40 | 23,86 |
| 80 | 30,79 |
| 160 | 37,73 |

Każdy dodatkowy punkt nadal pomaga, ale nie proporcjonalnie. Nie normalizujemy wszystkich postaci do tej samej siły i nie odbieramy zakupionego postępu. Transformacja jest wspólna dla wszystkich i musi być opisana, a wyliczone parametry widoczne.

Ryzyko: przy bardzo wysokich statystykach wzrost może wydawać się zbyt mały. Model trzeba sprawdzić dla 30, 90 i 365 dni, zanim ten wzór zostanie utrwalony w produkcji.

## 4. Dokładny wzór pojedynku

S, I, R, C i T oznaczają przeliczone wartości kolejno: siły, inteligencji, refleksu, charyzmy i sprytu. Spryt oznaczono T, aby nie mylić go z siłą.

### Parametry

- Maksymalna kondycja: **HP = 500 + 10 × C**.
- Podstawowe obrażenia: **D = 50 + S + 0,2 × T**.
- Mnożnik otrzymywanych obrażeń: **M = 60 / (60 + I)**.
- Szansa krytyczna: **K = 0,05 + 0,6 × T / (T + 40)**.
- Krytyk: **2 × obrażenia**, bez osobnej drastycznej animacji.
- Szansa trafienia atakującego A w obrońcę B:
  **P = clamp(0,80 + 0,4 × (R_A − R_B) / (R_A + R_B + 40), 0,65, 0,95)**.
- Szansa, że A wykona pierwszą akcję danej rundy:
  **Q = clamp(0,50 + 0,2 × (R_A − R_B) / (R_A + R_B + 40), 0,35, 0,65)**.

clamp ogranicza wynik do wskazanego przedziału. Szansę pierwszej akcji losujemy ponownie na początku każdej rundy. Drugi zawodnik odpowiada tylko wtedy, gdy nadal ma kondycję powyżej zera.

### Rozstrzygnięcie akcji

1. Losowanie trafienia.
2. Jeśli trafiono: losowanie krytyka oraz mnożnika obrażeń z przedziału 0,85–1,15.
3. Obrażenia = **max(1, D_atakującego × M_obrońcy × mnożnik losowy × mnożnik krytyka × mnożnik taktyki)**.
4. Zmniejszenie kondycji przeciwnika.
5. Koniec, jeżeli jego kondycja spadnie do zera lub poniżej.

Model liczy na liczbach zmiennoprzecinkowych. Zaokrąglenie do prezentacji nie może zmieniać wyniku backendu; produkcyjny sposób reprezentacji liczb wymaga ustalenia. Bezpiecznik to 100 rund: jeśli nikt nie wygra, wynik jest remisem. W wykonanych testach nie wystąpiły takie remisy.

W modelu walki trwały średnio około 12 rund w podstawowych scenariuszach. Docelowy czas animacji: około 20–35 sekund, z opcją przyspieszenia i pominięcia dostępną dla wszystkich. To cel interfejsu, nie zmierzony czas gotowej animacji.

## 5. Taktyka

Trzy taktyki, wybierane przed zgłoszeniem do pojedynku:

| Taktyka | Ma przewagę nad | Przegrywa zależność taktyczną z |
|---|---|---|
| Presja | Kontrolą | Kontrą |
| Kontrola | Kontrą | Presją |
| Kontra | Presją | Kontrolą |

Przewaga daje **8% do zadawanych obrażeń**. Przegrana zależność nie nakłada drugiej kary. Przy takich samych taktykach nie ma premii.

Taktyka przeciwnika jest ukryta do rozstrzygnięcia; zgłoszenie blokuje własny wybór. W przeciwnym razie drugi wybierający miałby darmową przewagę. W tej wersji taktyka nie jest dodatkowo powiązana ze statystykami, więc żaden wariant rozwoju nie dostaje premii poza opisanym wzorem.

To prosty mechanizm startowy. Bez dodatkowej informacji o stylu rywala może być odbierany jako zgadywanie; należy sprawdzić, czy rzeczywiście daje interesujące decyzje. Nie należy reklamować go jako głębokiego systemu strategicznego.

## 6. Wyposażenie i warianty rozwoju

Proponowane cztery miejsca: rękawice, strój, obuwie, akcesorium sportowe. Wyposażenie dodaje jawne punkty do statystyk surowych, a dopiero potem stosowany jest wzór W. W pierwszym prototypie bez dodatkowych ukrytych mnożników, płatnych losowych przedmiotów i efektów aktywowanych w środku walki.

W wykonanych testach wyposażenie nie daje bonusów — badamy wyłącznie statystyki i taktykę. Nie określono jeszcze cen i parametrów przedmiotów.

### Przykładowe warianty o tej samej sumie 190 punktów

Kolejność: siła / inteligencja / refleks / charyzma / spryt.

| Wariant | Rozkład | Wygrane przeciw 38/38/38/38/38 przy tej samej taktyce |
|---|---|---:|
| Zbalansowany | 38 / 38 / 38 / 38 / 38 | 50,1% |
| Uderzeniowy | 60 / 30 / 35 / 30 / 35 | 47,0% |
| Techniczny | 35 / 50 / 45 / 30 / 30 | 48,3% |
| Wytrzymałościowy | 35 / 35 / 30 / 60 / 30 | 48,8% |
| Kontrujący | 35 / 30 / 50 / 30 / 45 | 45,4% |

Nazwy są opisami przykładowych rozkładów, nie klasami do wybrania przy rejestracji. Wyniki nie dowodzą, że warianty są optymalne ani że zbadano wszystkie ich wzajemne starcia. Model lekko premiuje rozwój zrównoważony; wariant kontrujący wymaga uwagi.

Skrajne inwestowanie wszystkich 140 nowych punktów w jedną statystykę dawało zaledwie około 0,9–3,3% zwycięstw przeciw zbalansowanemu wariantowi. To ostrzeżenie dla projektu: jeśli docelowo obiecamy skuteczność takich sportowych specjalizacji, obecny wzór nie spełnia obietnicy. Dopuszczamy gospodarcze specjalizacje, ale nie wymagamy od nich sukcesów sportowych do dalszego rozwoju.

## 7. Płatna przewaga po pierwszym tygodniu

### Dane wejściowe z ekonomii v0.1

Pięć statystyk startowych po 10 punktów i możliwie równomiernie rozdzielony przyrost:

- Bez zakupów: **33 / 33 / 32 / 32 / 32**, suma 162.
- VIP: **38 / 38 / 38 / 38 / 38**, suma 190.
- VIP i maksymalne uzupełnienia: **50 / 49 / 49 / 49 / 49**, suma 246.

To scenariusze aktywnego gracza z poprzedniego modelu, a nie gwarantowane tempo postępu. Brak bonusu za wcześniejszy zapis na serwer.

### Wyniki — procent zwycięstw pierwszego wymienionego zawodnika

| Porównanie | Pierwszy wzór v0.1 | Proponowany wzór v0.2 |
|---|---:|---:|
| Identyczne postacie | 50,4% | 50,1% |
| VIP przeciw bezpłatnemu | 85,2% | 64,3% |
| VIP + uzupełnienia przeciw bezpłatnemu | 99,9% | 82,4% |
| VIP + uzupełnienia przeciw VIP | 97,5% | 71,4% |
| Identyczne statystyki, przewaga taktyki pierwszego | 62,4% | 61,4% |
| Bezpłatny z przewagą taktyki przeciw maksymalnemu | 0,4% | 27,5% |

Każda komórka pochodzi z 20 000 walk danego modelu. W v0.2 wykonano 15 scenariuszy, łącznie 300 000 walk. Użyto lokalnego generatora pseudolosowego ze stałym ziarnem 20260927 dla odtwarzalności eksperymentu; nie jest to rozwiązanie dla produkcyjnego serwera.

Dla wyników v0.2 w głównych scenariuszach orientacyjny błąd losowy przy poziomie 95% wynosi około ±0,5–0,7 punktu procentowego. Nie obejmuje to niepewności wynikającej z uproszczeń samego modelu. Wyniki nie stanowią prognozy odsetka wygranych wszystkich realnych użytkowników danego produktu.

**Wniosek:** płatna przewaga jest wyraźna, ale nie daje niemal pewnego zwycięstwa w każdej z tych par. Nadal 82,4% oznacza jednostronną parę — nie powinna być standardowym doborem przeciwników w lidze wyrównanej. Lepsza taktyka pomaga, lecz nie kasuje różnicy rozwoju.

## 8. Trzy zastosowania pojedynków

### A. Liga sportowa — wyrównane pary

- Gracz zgłasza postać do asynchronicznej kolejki z utrwalonym wyposażeniem, statystykami i taktyką.
- Serwer łączy dwa zgłoszenia; obecność obu graczy w czasie animacji nie jest potrzebna.
- Propozycja: do pięciu rozliczonych walk rankingowych na dobę serwera na postać, bez dokupywania prób w pierwszej wersji.
- Zakupy nadal pomagają przez szybszy rozwój i dostęp do mocniejszych rywali. Nie kupują bezpośrednio punktów rankingu.
- Przy połączeniu zużywa się zgłoszenie obu stron. Jedna aktywna kolejka na postać. Niesparowane zgłoszenie może wygasnąć lub zostać anulowane bez zużycia walki.
- Punkty otrzymuje się za wynik, nie za samo zgłoszenie.

Dobór powinien uwzględniać siłę zestawu oraz wynik sportowy. Nie wystarczy sam poziom postaci ani informacja o VIP. Kandydackie okno to przewidywana szansa zwycięstwa około 35–65%, ale szybki i skalibrowany estymator tej szansy nie został jeszcze zbudowany. Nie wykonujemy 20 000 symulacji dla każdej pary w działającej grze.

Przy braku odpowiedniego rywala pokazujemy oczekiwanie lub proponujemy sparing z NPC bez punktów ligowych. Nie rozszerzamy po cichu doboru do zdecydowanie silniejszych przeciwników. Trzeba sprawdzić dostępność par na małych i starych serwerach.

### B. Wyzwanie konkretnego gracza

Dobrowolny pojedynek towarzyski po przyjęciu zaproszenia. Brak nagród ekonomicznych i zmiany rankingu. Pozwala testować zestawy bez tworzenia farmy nagród na zaprzyjaźnionych kontach. Techniczne limity częstotliwości chronią usługę przed spamem.

### C. Turnieje otwarte — etap późniejszy

Miejsce na rywalizację o dominację, gdzie silniejszy rozwój daje wyraźną korzyść, a pary nie zawsze są wyrównane. Zasady kwalifikacji, drabinki, harmonogram i nagrody wymagają odrębnego projektu. Nie implementujemy ich w pierwszym prototypie.

## 9. Ranking ligi

Propozycja początkowa: Elo, 1000 punktów na start, K = 24.

- Oczekiwany wynik A: **E_A = 1 / (1 + 10^((rating_B − rating_A)/400))**.
- Wynik S: 1 za zwycięstwo, 0 za porażkę, 0,5 za remis.
- Zmiana A: **24 × (S − E_A)**; zmiana B jest przeciwna.
- Wewnętrznie przechowujemy precyzyjniejszą wartość, a zaokrąglamy jedynie widok.
- Pierwsze dziesięć walk oznaczamy jako klasyfikacyjne, z tym samym K w prototypie.
- Maksymalnie jeden punktowany pojedynek tej samej pary w ciągu 24 godzin, bez względu na inicjatora.

Elo opisuje wyniki w puli przeciwników, nie obiektywną moc konta. Łączenie doboru według siły z Elo może tworzyć odseparowane grupy o nieporównywalnych punktach. Dlatego prototyp traktuje to jako ranking danej ligi/puli; ligi, awanse i porównywalność między pulami wymagają dalszej walidacji. Nie ogłaszamy najwyższego Elo automatycznie „najsilniejszą postacią serwera”.

Ten projekt nie ustala punktacji globalnej między światami. Nie tworzy też rankingu osiągnięć. Nagrody pieniężne i XP z PvP pozostają wyłączone w pierwszym teście, aby nie zmieniać niezauważenie ekonomii v0.1.

## 10. Kondycja, klinika i sankcje

HP w raporcie jest kondycją konkretnego pojedynku. Na potrzeby pierwszego prototypu przed kolejnym pojedynkiem jest resetowane — przegrana nie blokuje gry i nie tworzy długu leczenia.

Klinika sportowa i utrzymujące się urazy pozostają w planie świata, lecz nie wchodzą jeszcze do formuły. Nie dodajemy kar, których wpływu ekonomicznego nie zmierzono. Późniejsze urazy mogą ograniczać aktywności sportowe, nie całe konto.

## 11. Raport i bezpieczeństwo

Raport pokazuje zwycięzcę, zmianę punktów, statystyki startowe, sprzęt, taktyki, listę akcji i wersję zasad. HP w interfejsie nie spada wizualnie poniżej zera.

Backend musi:

1. Sprawdzić właściciela postaci, świat, limity i aktualność zgłoszenia.
2. Utrwalić stan obu zawodników przy zapisie zgłoszeń; późniejsze ulepszenie nie zmienia trwającej walki.
3. Używać nieprzewidywalnego dla klienta źródła losowości, nie stałego ziarna demonstracyjnego.
4. Jednokrotnie rozliczyć walkę, limity i ranking w spójnej operacji; ponowienie żądania zwraca ten sam wynik.
5. Zapisać wersję algorytmu i dane potrzebne do audytu, bez ujawniania przyszłych wyników losowych.
6. Chronić przed wieloma równoległymi zgłoszeniami, ustawianiem wyników i farmieniem kont.

Ponowne otwarcie raportu odtwarza zapisane zdarzenia, a nie losuje pojedynku od nowa.

## 12. Rekomendacja dalszych prac

Przyjąć v0.2 jako kandydat do prototypu, a nie ostatecznie zatwierdzony silnik.

Przed wdrożeniem sprawdzić:
- pełną macierz umiarkowanych wariantów rozwoju i różne taktyki;
- sprzęt, próby skrajnych konfiguracji i optymalizację statystyk;
- 30, 90 i 365 dni progresji;
- modele doboru i lig przy małej liczbie użytkowników;
- wpływ nagród PvP na gospodarkę;
- czy gracze rozumieją malejące korzyści i odczuwają postęp;
- moderację wyzwań oraz odpowiednią oprawę wiekową gotowej gry.

**Kolejny praktyczny etap:** interaktywny prototyp pojedynku, pokazujący dwie karty postaci, taktyki, paski kondycji i zapisane akcje. Następnie dopiero ustalanie nagród oraz cen produktów.
