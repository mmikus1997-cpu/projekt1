# CITY EMPIRE
## Ekonomia pierwszych siedmiu dni — propozycja v0.1

**Status:** roboczy projekt do prototypu, nie zatwierdzony balans produkcyjny.
**Zakres:** samouczek i siedem pełnych dób po jego zakończeniu.

Dokument uzupełnia wizję gry, ale nie zastępuje głównego dokumentu projektowego. Wszystkie kwoty, czasy, limity i właściwości produktów poniżej są propozycjami. Nie ustalono cen w PLN ani przelicznika premium. Dokument nie jest opinią prawną ani potwierdzeniem zgodności ze sklepami.

## 1. Ustalenia, których nie zmieniamy

- Gra dla nastolatków i dorosłych, bez planowanych treści 18+. Minimalny wiek i klasyfikacje pozostają do ustalenia.
- Płatne przyspieszenie może wpływać na siłę i rankingi.
- Jedno konto główne, maksymalnie jedna postać na danym świecie.
- Niezależne gospodarki; brak przenoszenia postępów między światami.
- Nowe światy uruchamiane decyzją administratora, bez obowiązkowego cyklu kwartalnego.
- Osiągnięcia konta są pamiątkowe; nie dają energii, pieniędzy ani statystyk.
- Telefon, tablet i przeglądarka; aplikacja PC opcjonalnie.

## 2. Cel pierwszego tygodnia

Gracz ma zrozumieć relację między kontraktami, treningiem i biznesem oraz podjąć pierwsze samodzielne decyzje. Nie powinien potrzebować zakupu, aby utrzymać podstawowy rozwój.

Pętla: **kontrakty → gotówka → trening lub inwestycja → nowe możliwości**.
Równolegle: **przedsiębiorstwo → dochód offline → reinwestycja albo rozwój postaci**.

Nie projektujemy jeszcze rynku między graczami, pełnej ekonomii samochodów ani nagród turniejowych. Ich późniejsze dodanie wymaga ponownego przeliczenia modelu.

## 3. Samouczek — sesja startowa

Cel: około 10–15 minut, do sprawdzenia w prototypie.

| Krok | Efekt |
|---|---|
| Utworzenie postaci | Pięć statystyk po 10 punktów; 500 gotówki; 120 energii samouczkowej |
| Krótkie zadania wprowadzające | Łącznie 500 dodatkowej gotówki |
| Podstawowe wyposażenie | Wydatek 100 gotówki, nauka zakładania przedmiotów |
| Otwarcie mikrofirmy kurierskiej | Wydatek 600 gotówki; przedsiębiorstwo poziomu 1 |
| Trening i sparing instruktażowy | Wyjaśnienie zasad, bez trwałych punktów statystyk i XP uwzględnianych w tabelach |
| Zakończenie | 300 gotówki, firma poziomu 1 i wyposażenie podstawowe |

Energia samouczkowa jest oddzielnym, bezpłatnym zasobem szkoleniowym. Niewykorzystana część nie przechodzi do regularnej gospodarki. W prototypie trzeba jasno pokazać przejście do zwykłej energii i zapewnić możliwość kontynuowania gry; saldo początkowe zwykłej energii nie jest uwzględnione w siedmiodniowym benchmarku.

Samochód użytkowy można pokazać jako pojazd służbowy mikrofirmy bez wartości odsprzedaży. Nie staje się przez to dodatkową nagrodą ekonomiczną. Prywatne samochody i wille projektujemy później.

## 4. Energia i aktywności

| Parametr | Propozycja |
|---|---:|
| Naturalna regeneracja | 10 energii na godzinę |
| Podstawowa pojemność | 240 energii, czyli 24 godziny regeneracji |
| Kontrakt podstawowy | 10 energii, 10 minut |
| Nagroda kontraktu | 100 gotówki i 20 XP |
| Trening podstawowy | 5 energii, 50 gotówki, 5 minut |
| Efekt treningu | +1 punkt wybranej statystyki |

Kontrakty początkowe mają gwarantowany wynik, nie losują strat. Wysokość nagrody i koszt są widoczne przed startem. Kolejki kontraktów i treningu są osobne i dostępne również bez VIP. Gracz może zlecić serię do czterech operacji; energia i gotówka są rezerwowane przy zlecaniu, bez zadłużania postaci. Brak obowiązku klikania po każdym pojedynczym treningu.

Koszt 50 za punkt jest ceną roboczą zakresu początkowego, a nie obietnicą stałego kosztu przez całą grę. Skalowanie kosztów, progi statystyk i dalsza progresja wymagają projektu przed publicznym wdrożeniem.

## 5. Pierwszy biznes

Mikrofirma kurierska generuje przewidywalny dochód. Podane stawki są dochodem netto, już po umownych kosztach działalności — nie odejmujemy drugi raz ukrytego utrzymania.

| Poziom | Dochód netto / godz. | Koszt awansu na ten poziom |
|---|---:|---:|
| 1 | 40 | 600 w samouczku |
| 2 | 55 | 1 000 |
| 3 | 75 | 2 500 |
| 4 | 100 | 5 000 |
| 5 | 135 | 9 000 |
| 6 | 175 | 15 000 |
| 7 | 225 | 24 000 |

Skarbiec mieści 24 godziny dochodu przy aktualnej stawce. Pełny skarbiec zatrzymuje dalszą produkcję, ale nie odbiera już zgromadzonych środków. Zmiana stawki nie przelicza wstecz dotychczasowego dochodu. Firma nie bankrutuje podczas nieobecności gracza.

W modelu inwestycje wykonywane są na koniec doby, a nowa stawka obowiązuje od następnej doby. Nie modelujemy jeszcze czasu budowy ani zakupów w środku dnia. To uproszczenie obliczeniowe, nie propozycja wymuszania inwestowania o północy w prawdziwej grze.

Pierwsza firma jest wprowadzeniem. Docelowo firmy powinny oferować wybory specjalizacji, nie tylko przycisk podnoszenia poziomu.

## 6. VIP i dodatkowa energia — wariant do porównania

| Wariant | Regeneracja naturalna / doba | Dodatkowa energia | Łącznie w benchmarku |
|---|---:|---:|---:|
| Bezpłatny | 240 | 0 | 240 |
| VIP | 240 | 60 z VIP | 300 |
| VIP + limit uzupełnień | 240 | 60 z VIP + 120 z uzupełnień | 420 |

Propozycja: dwa uzupełnienia po 60 energii na dobę serwera. Limit dotyczy łącznie wszystkich przedmiotów i zakupów należących do tej kategorii, aby nie można było ominąć go inną nazwą produktu. Nagroda VIP także jest stała, nie kumuluje się bez końca.

Bonusy trafiają do odrębnej puli dodatkowej energii, aby nie blokować naturalnej regeneracji. Pule i zasady ich wykorzystania muszą być widoczne. Niewykorzystane, zakupione uzupełnienia pozostają przedmiotami do późniejszego użycia; nie należy mylić limitu użycia z terminem ważności zakupionego dobra.

W tym wariancie VIP nie daje dodatkowego mnożnika dochodu, XP ani siły. Takie mnożniki nie są wykluczone z całego projektu, ale nie zostały uwzględnione w obliczeniach. Proponowany okres zakupu VIP: 30 dni, bez automatycznego odnawiania w pierwszej wersji. Cena nieustalona.

Wille, kolejne źródła regeneracji i promocje wymagają osobnego budżetu energii — nie można po prostu dopisać ich ponad limity i nadal powoływać się na wyniki tej symulacji.

## 7. Założenia obliczeń

To deterministyczny model arkuszowy wykonany skryptem Python, nie test z graczami ani symulacja walk.

- Siedem pełnych dób po samouczku, saldo początkowe 300 gotówki.
- Pełne wykorzystanie naturalnej regeneracji; brak przepełnienia energii i skarbca.
- Brak dodatkowej energii początkowej, bonusu za zapis i innych promocji.
- W każdym wariancie ta sama strategia: tyle samo kontraktów co pojedynczych treningów.
- Dochód firmy naliczany według poziomu na początku doby.
- Po wykonaniu aktywności całe dostępne saldo może finansować kolejne poziomy firmy, jeśli wystarcza na ich koszt.
- Brak zakupów wyposażenia po samouczku, wpływów z PvP, handlu i wydatków organizacyjnych.
- Brak losowości, nieudanych kontraktów i przerw w aktywności.
- Nie modelujemy kolejności operacji wewnątrz dnia. Wykonalność harmonogramu, płynność w trakcie dnia i wygoda kolejek wymagają testu prototypu.

Założenia dają porównywalny, aktywny scenariusz odniesienia. Nie oznaczają, że typowy użytkownik uzyska dokładnie taki wynik.

### Dzienne wykorzystanie energii

| Wariant | Kontrakty | Treningi | Zużycie energii | XP | Nowe punkty statystyk | Gotówka z kontraktów minus trening |
|---|---:|---:|---:|---:|---:|---:|
| Bezpłatny | 16 | 16 | 240 | 320 | 16 | 800 |
| VIP | 20 | 20 | 300 | 400 | 20 | 1 000 |
| VIP + limit uzupełnień | 28 | 28 | 420 | 560 | 28 | 1 400 |

Czas samych kontraktów wynosi odpowiednio 160, 200 i 280 minut dziennie; treningów 80, 100 i 140 minut. To czas pracy systemów, nie czas patrzenia na ekran. Kolejki mogą działać równolegle.

### Wynik na koniec każdej doby

W komórkach: **poziom firmy / dostępna gotówka**.

| Doba | Bezpłatny | VIP | VIP + limit uzupełnień |
|---|---:|---:|---:|
| 1 | 2 / 1 060 | 2 / 1 260 | 2 / 1 660 |
| 2 | 3 / 680 | 3 / 1 080 | 3 / 1 880 |
| 3 | 3 / 3 280 | 3 / 3 880 | 4 / 80 |
| 4 | 4 / 880 | 4 / 1 680 | 4 / 3 880 |
| 5 | 4 / 4 080 | 4 / 5 080 | 4 / 7 680 |
| 6 | 4 / 7 280 | 4 / 8 480 | 5 / 2 480 |
| 7 | 5 / 1 480 | 5 / 2 880 | 5 / 7 120 |

### Podsumowanie siedmiu dób

| Wynik | Bezpłatny | VIP | VIP + limit uzupełnień |
|---|---:|---:|---:|
| Ukończone kontrakty | 112 | 140 | 196 |
| XP zdobyte w okresie | 2 240 | 2 800 | 3 920 |
| Nowe punkty statystyk | 112 | 140 | 196 |
| Suma pięciu statystyk ze startowymi 50 | 162 | 190 | 246 |
| Poziom firmy | 5 | 5 | 5 |
| Wydatki na ulepszenia firmy po samouczku | 17 500 | 17 500 | 17 500 |
| Gotówka po inwestycjach | 1 480 | 2 880 | 7 120 |
| Docelowy dochód firmy na koniec okresu / godz. | 135 | 135 | 135 |

Nie przeliczamy XP na poziom postaci: krzywa poziomów nie została jeszcze zaprojektowana. Suma statystyk nie jest wzorem siły bojowej.

## 8. Wnioski z obliczeń

1. Sam VIP daje w tym scenariuszu 25% więcej aktywności, XP i nowych punktów statystyk niż wariant bezpłatny.
2. Maksymalne uzupełnienia z VIP dają 75% więcej tych przyrostów. To wyraźna płatna przewaga, nie kosmetyka.
3. Całkowita suma statystyk po tygodniu wynosi 246 wobec 162, czyli około 52% więcej, ale nie oznacza 52% wyższej szansy wygranej. Potrzebna jest formuła PvP.
4. Wszyscy dochodzą do firmy poziomu 5, lecz wariant maksymalny osiąga poziomy 4 i 5 o dobę wcześniej oraz ma większą rezerwę gotówki.
5. Strategia maksymalnego reinwestowania potrafi pozostawić bardzo niskie saldo, np. 80 gotówki po trzeciej dobie. W prototypie warto sugerować rezerwę, nie blokując samodzielnej decyzji gracza.
6. Pod koniec okresu biznes staje się dużym źródłem dochodu. Kolejne firmy mogą mocno przyspieszyć inflację. Nie wolno ekstrapolować tygodnia na miesiące bez ponownego modelowania.
7. Równa liczba kontraktów i treningów to tylko jedna strategia. Przed zatwierdzeniem potrzebne są warianty przedsiębiorcy, sportowca i gracza nieregularnego.

## 9. Proponowane doświadczenie kolejnych dni

Są to cele obserwacji, a nie sztywny kalendarz blokujący zawartość.

| Dzień | Cel projektowy |
|---|---|
| 1 | Gracz umie uruchomić kontrakt, trening i odebrać dochód |
| 2 | Rozumie wybór między ulepszeniem firmy a statystyką |
| 3 | Poznaje alternatywne kontrakty o porównywalnej opłacalności |
| 4 | Wypróbowuje sportową rywalizację; test początkowo bez nagród ekonomicznych |
| 5 | Widzi cel współpracy i zapowiedź organizacji |
| 6 | Potrafi ocenić, co zmienia zakup i czy go potrzebuje |
| 7 | Wybiera długoterminowy cel: kolejna firma, rozwój sportowy lub organizacja |

Wprowadzenie nagród PvP, nowych stawek kontraktów i dodatkowych biznesów zmieni wyniki finansowe; powyższa tabela nie dodaje ich do obliczeń.

## 10. Zasady chroniące grywalność

- Brak utraty całej grywalności z powodu kliniki lub wyczerpania energii.
- Planowanie, przegląd firm, wyposażenie, rankingi i taktyka bez kosztu energii.
- Brak obowiązkowej serii logowań resetującej się po dniu przerwy w pierwszym prototypie.
- Uzupełnienie energii nie kupuje zwycięstwa w konkretnej walce ani ponownego losowania wyniku.
- Bonus za wcześniejszy zapis nie mnoży się przez liczbę postaci na starych światach.
- Docelowo testujemy awarie, jednokrotne przyznawanie nagród, wyścigi równoległych zleceń oraz potwierdzanie zakupów po stronie backendu.

## 11. Co trzeba sprawdzić przed zatwierdzeniem balansu

- Model godzinowy: startowa energia, przepełnienie, kolejki, czas ulepszeń i płynność.
- Gracz logujący się raz dziennie, co drugi dzień i kilka razy dziennie.
- Dalsze 30 i 90 dni, różne strategie oraz koszty wyposażenia.
- Wpływ różnic statystyk na PvP i dobór przeciwników.
- Bonus nowego serwera oraz darmowy VIP w osobnej symulacji, nie ukryte w bazie.
- Zakres VIP, serwerowy portfel premium i ceny — osobny projekt produktów.
- Zasady wieku, kont niepełnoletnich, zakupów, moderacji, RODO i wymagania sklepów — osobny przegląd przed publikacją.

**Rekomendowany następny moduł: statystyki i sportowe PvP**, aby sprawdzić, jak przyrosty z tej ekonomii przekładają się na rzeczywistą przewagę.
