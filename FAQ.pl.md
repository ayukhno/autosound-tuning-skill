# FAQ — Często zadawane pytania dotyczące strojenia systemów car audio

🇬🇧 [English](FAQ.md) · 🇩🇪 [Deutsch](FAQ.de.md) · 🇵🇱 **Polski** · 🇺🇦 [Українська](FAQ.uk.md) · 📄 [README](README.pl.md) · <img src="assets/icons/roadmap.svg" width="14" height="14" valign="middle" alt="Roadmap" /> [Roadmap (EN, szkic)](ROADMAP.md)

Rzeczywiste pytania użytkowników dotyczące instalacji i konfiguracji systemu za pomocą tego narzędzia. [README](README.pl.md) to wersja skrócona; ta strona zawiera wszystkie szczegóły.

---

## Spis treści

- [Wybór ścieżki](#wybór-ścieżki)
  - [Cztery warianty użycia](#cztery-warianty-użycia)
  - [Który wariant wybrać?](#który-wariant-wybrać)
  - [Jak sprawdzić zainstalowaną wersję?](#jak-sprawdzić-zainstalowaną-wersję)
  - [Jak pozostać na stabilnej linii 2.x](#jak-pozostać-na-stabilnej-linii-2x)
  - [Przejście z 2.x na 3.x](#przejście-z-2x-na-3x)
  - [Główne zmiany w wersji 3.x](#główne-zmiany-w-wersji-3x)
- [Filozofia i architektura: po co nam AI?](#filozofia-i-architektura-po-co-nam-ai)
  - [Misja i koncepcja](#misja-i-koncepcja)
  - [Dlaczego to wyspecjalizowany skill, a nie zwykły czat?](#dlaczego-to-wyspecjalizowany-skill-a-nie-zwykły-czat)
  - [Mapa strojenia: fazy −1…5 i podejście „Najpierw przy biurku”](#mapa-strojenia-fazy-15-i-podejście-najpierw-przy-biurku)
  - [Czego ta metoda kategorycznie odmawia?](#czego-ta-metoda-kategorycznie-odmawia)
  - [Które modele AI są oficjalnie wspierane?](#które-modele-ai-są-oficjalnie-wspierane)
  - [Warianty subskrypcji i budżet na AI](#warianty-subskrypcji-i-budżet-na-ai)
  - [Dlaczego rzeczywiste zużycie tokenów jest niższe, niż się wydaje?](#dlaczego-rzeczywiste-zużycie-tokenów-jest-niższe-niż-się-wydaje)
- [Pierwsza instalacja (macOS i Windows)](#pierwsza-instalacja-macos-i-windows)
  - [Automatyczna instalacja](#automatyczna-instalacja)
  - [Gdzie są instalowane komponenty?](#gdzie-są-instalowane-komponenty)
  - [Pierwsze uruchomienie i logowanie](#pierwsze-uruchomienie-i-logowanie)
  - [Aktualizacja, blokowanie wersji i usuwanie](#aktualizacja-blokowanie-wersji-i-usuwanie)
- [Aplikacja graficzna Autosound TCC](#aplikacja-graficzna-autosound-tcc)
  - [Co to jest i czy jest mi potrzebne?](#co-to-jest-i-czy-jest-mi-potrzebne)
  - [Praca na dwa okna (Terminal + Grafika)](#praca-na-dwa-okna-terminal--grafika)
  - [Modele AI w aplikacji](#modele-ai-w-aplikacji)
  - [Aktualizacje i zgłaszanie błędów](#aktualizacje-i-zgłaszanie-błędów)
- [Autonomiczny Krytyk AI Gemini/Antigravity](#autonomiczny-krytyk-ai-geminiantigravity)
  - [Instalacja dla macOS i Windows (Zalecana)](#instalacja-dla-macos-i-windows-zalecana)
  - [Wariant rezerwowy: Bezpośredni klucz API Gemini](#wariant-rezerwowy-bezpośredni-klucz-api-gemini)
  - [Czy można pracować tylko w Gemini, bez Claude?](#czy-można-pracować-tylko-w-gemini-bez-claude)
- [Przeprowadzanie pomiarów](#przeprowadzanie-pomiarów)
  - [Pomiar fazy: Mikrofony XLR kontra USB (UMIK-1/2)](#pomiar-fazy-mikrofony-xlr-kontra-usb-umik-12)
  - [Czy można zmierzyć fazę na UMIK-1?](#czy-można-zmierzyć-fazę-na-umik-1)
  - [Zasady nazewnictwa pomiarów w REW](#zasady-nazewnictwa-pomiarów-w-rew)
  - [Sesja pomiarowa (Capture): dlaczego tylko filtry ochronne?](#sesja-pomiarowa-capture-dlaczego-tylko-filtry-ochronne)
  - [Po co są pozycje p1…p9 i kontrola czasu ctl?](#po-co-są-pozycje-p1p9-i-kontrola-czasu-ctl)
- [Krzywe docelowe (Target Curves)](#krzywe-docelowe-target-curves)
  - [Jak stworzyć i skonfigurować własną krzywą docelową?](#jak-stworzyć-i-skonfigurować-własną-krzywą-docelową)
- [Projekt na dysku i DSP](#projekt-na-dysku-i-dsp)
  - [Struktura folderu projektu i kopia zapasowa](#struktura-folderu-projektu-i-kopia-zapasowa)
  - [Kompatybilność z procesorami i import filtrów do DSP](#kompatybilność-z-procesorami-i-import-filtrów-do-dsp)
  - [Praca ze zwrotnicami pasywnymi (tweeter + średniotonowy na jednym kanale)](#praca-ze-zwrotnicami-pasywnymi-tweeter--średniotonowy-na-jednym-kanale)
  - [Gdzie znaleźć pełną listę możliwości metody?](#gdzie-znaleźć-pełną-listę-możliwości-metody)

---

## Wybór ścieżki

### Cztery warianty użycia

* 🖥️ **Wariant 1 · Wersja 3.x w oknie graficznym (Autosound TCC)**
  Najbardziej zautomatyzowana i przejrzysta ścieżka. Instalator konfiguruje Claude Code, Pythona, rdzeń metody, interfejs graficzny oraz automatycznego krytyka AI.
  * **Wymagania:** macOS lub Windows, płatny Claude Pro/Max, wersja beta REW z włączonym API, ~700 MB wolnego miejsca na dysku.
  * **Zalety:** Widzisz strukturę systemu, wykresy pomiarów, plan krok po kroku i okno czatu w jednym wygodnym interfejsie. Stan jest zapisywany automatycznie, a każdą operację w rejestrze wersji można cofnąć jednym kliknięciem.
  * **Wady:** Aplikacja graficzna jest stosunkowo nowym produktem i obecnie znajduje się w fazie testów beta.

* 💻 **Wariant 2 · Wersja 3.x w terminalu**
  Ten sam nowoczesny rdzeń i poziom automatyzacji, ale interakcja odbywa się wyłącznie tekstowo w konsoli. Instalacja za pomocą instalatora z flagą `--terminal`.
  * **Wymagania:** Te same subskrypcje i REW z API, ale bez potrzeby posiadania nakładki graficznej.
  * **Zalety:** Maksymalna prędkość działania, minimalne zużycie zasobów systemowych. Projekty są w pełni kompatybilne z programem graficznym TCC (będziesz mógł otworzyć ten sam folder w interfejsie graficznym później).

* 🏆 **Wariant 3 · Linia 2.x (Sprawdzony mistrz)**
  Stabilna wtyczka dla Claude Code, na stałe zablokowana na wersji `v2.8.3` (gałąź `2.x`). To właśnie ten algorytm strojenia doprowadził auta do czterech mistrzowskich pucharów EMMA i AYA w 2026 roku.
  * **Wymagania:** Płatny Claude Pro, wersja beta REW z API, praca w terminalu.
  * **Zalety:** Sprawdzony w czasie i na zawodach, absolutnie stabilny algorytm. Otrzymuje wyłącznie krytyczne poprawki błędów (bugfixy), nowe funkcje nie są tu celowo dodawane.
  * **Wady:** Brak automatycznej kontroli stanów przez maszynę (wszystko prowadzone jest ręcznie w plikach tekstowych Markdown), brak podejścia „Najpierw przy biurku” oraz nowoczesnych narzędzi obliczeniowych.

* 🌐 **Wariant 4 · Czat internetowy (Bez instalacji oprogramowania)**
  W pełni ręczny, krok po kroku proces strojenia za pomocą gałęzi [manual_step-by-step](https://github.com/ayukhno/autosound-tuning-skill/tree/manual_step-by-step).
  * **Wymagania:** Darmowa usługa Google AI Studio lub dowolny czat internetowy z AI według Twojego wyboru.
  * **Zalety:** Całkowicie za darmo. Nie wymaga instalacji żadnego oprogramowania ani narzędzi programistycznych na Twoim komputerze. Idealne do zapoznania się z logiką metody.
  * **Wady:** Każdy krok wykonuje się wyłącznie ręcznie (kopiowanie promptów, samodzielny eksport plików tekstowych z REW), brak integracji przez API oraz automatycznej weryfikacji obliczeń przez skrypty lokalne.

---

### Który wariant wybrać?

* **Chcesz maksimum automatyzacji i grafiki:** Wybierz **Wariant 1 (TCC)**.
* **Wolisz konsolę bez zbędnego oprogramowania:** Wybierz **Wariant 2 (3.x Terminal)**.
* **Szukasz sprawdzonej mistrzowskiej stabilności:** Wybierz **Wariant 3 (2.8.3)**.
* **Chcesz bezpłatnie przetestować logikę metody:** Wybierz **Wariant 4 (czat internetowy)**.

> [!NOTE]
> Nie jesteś zablokowany w jednym rozwiązaniu: projekty linii 3.x bez problemu otwierają się zarówno w konsoli, jak i w programie graficznym TCC, a przejście ze starszej wersji 2.x na 3.x jest całkowicie zautomatyzowane.

---

### Jak sprawdzić zainstalowaną wersję?

* **Po wpisanej komendzie:** Jeśli instalowałeś wtyczkę komendą `/plugin install autosound-tuning` wewnątrz Claude Code — masz wersję **2.x**. Jeśli uruchamiałeś skrypt instalacyjny w jednej linii (`curl … | bash` lub `irm … | iex`) — masz wersję **3.x**.
* **Po zawartości folderu projektu:** Jeśli folder zawiera plik `dsp-state-current.md` — to projekt **2.x**. Jeśli folder zawiera maszynowe pliki `project.json` oraz `process-state.json` — to projekt **3.x**.
* **Przez interfejs aplikacji:** W aplikacji TCC przejdź do menu *Diagnostics → Installation*.

---

### Jak pozostać na stabilnej linii 2.x

Zwykła automatyczna aktualizacja wtyczek nie przeniesie Cię na wersję 3.x bez Twojej zgody. Jednak jeśli chcesz całkowicie zamrozić wersję i lokalnie kontrolować proces otrzymywania poprawek dla gałęzi 2.x, sklonuj repozytorium samodzielnie:

```bash
git clone -b 2.x https://github.com/ayukhno/autosound-tuning-skill.git ~/autosound-2x
```

Następnie wewnątrz Claude Code wykonaj poniższe dwie komendy:
```bash
/plugin marketplace add ~/autosound-2x
/plugin install autosound-tuning
```
Teraz Twoja wtyczka odwołuje się do folderu lokalnego. Będziesz mógł ją aktualizować w razie potrzeby zwykłą komendą `git -C ~/autosound-2x pull`.

---

### Przejście z 2.x na 3.x

W systemie może być aktywna tylko jedna taka wtyczka jednocześnie. Przed instalacją nowej wersji 3.x koniecznie usuń starą wersję 2.x wewnątrz Claude Code:

```
/plugin uninstall autosound-tuning
/plugin marketplace remove autosound-tuning-skill
```

Po instalacji nowej wersji 3.x możesz zaimportować obecny stan samochodu (aktywne filtry zwrotnicy, opóźnienia, poziomy głośności, korektor i profil DSP) do nowego formatu za pomocą automatycznego migratora:

```sh
python3 ~/.claude/skills/.autosound-tuning-src/skills/autosound-tuning/rew_tool/state/migrate.py <ścieżka-do-starego-projektu> --into <ścieżka-do-nowego-projektu>
```

---

### Główne zmiany w wersji 3.x

* 📦 **Projekt jako struktura danych:** Wszystkie parametry systemu są zapisywane w plikach `project.json` oraz `process-state.json`. AI odczytuje dokładne fakty maszynowe, zamiast próbować przypomnieć je sobie z tekstowej historii dialogu.
* 🛋️ **Podejście „Najpierw przy biurku”:** Zamiast wielu wyjazdów do auta — **jedna sesja na pełne pomiary** (faza 0) i **jedna krótka na weryfikację** (faza 3). Cała dalsza analiza, obliczanie częstotliwości odcięcia zwrotnic, zgrywanie faz i ustawianie korektora są wykonywane przy biurku na podstawie dokładnej prognozy wirtualnej.
* 🧮 **Weryfikacja matematyczna:** Specjalne lokalne skrypty analizują wykresy pod kątem kryterium minimalnych strat fazowych, ograniczają dobroć (Q) korektora na podstawie rozrzutu punktów pomiarowych i automatycznie wykrywają przesunięcia czasowe mikrofonu.
* 🛑 **Automatyczne odmowy:** Jeśli pomiary wejściowe są sprzeczne, mikrofon wykazuje zbyt duży błąd czasowy lub brakuje pomiaru niektórych kanałów — system zatrzyma obliczenia i odrzuci rundę pomiarową zamiast generować niedokładne lub niebezpieczne dla głośników rezultaty.

---

## Filozofia i architektura: po co nam AI?

### Misja i koncepcja

Tworzymy **inteligentny egzoszkielet** do strojenia dźwięku. Człowiek (Arbiter) zawsze pozostaje najważniejszym ogniwem — słucha systemu, ocenia głębokość, wysokość i stabilność sceny dźwiękowej i podejmuje ostateczne decyzje.

AI przejmuje na siebie rutynowe obliczenia i fizykę kabiny: analizuje fazy, oblicza dokładne opóźnienia czasowe na łączeniach pasm i steruje programem REW przez jego API, zwalniając Twój czas na kreatywne słuchanie muzyki.

---

### Dlaczego to wyspecjalizowany skill, a nie zwykły czat?

* **Eliminacja utraty pamięci (memory drift):** Każdy standardowy czat z AI po kilku godzinach rozmowy zaczyna zapominać początkowe wartości, mylić poziomy głośności czy częstotliwości odcięcia. Nasz system zapisuje obecny stan projektu w pliku `project.json` na Twoim dysku. AI odczytuje ten plik przy każdym nowym zapytaniu — jego pamięć nie jest „przypominana”, lecz bezpiecznie odczytywana z dysku.
* **Wyspecjalizowana baza wiedzy:** Skill zawiera sztywne zasady bezpieczeństwa dla ochrony tweeterów, algorytmy zgrywania fazowego, gotowe krzywe docelowe oraz logikę analizy wnętrza pojazdu, o których ogólne modele AI nie mają zielonego pojęcia.
* **Lokalne przetwarzanie przez REW API:** Surowe dane pomiarowe (tysiące punktów na jeden wykres) są przetwarzane przez lokalne skrypty Pythona w milisekundy. AI otrzymuje na czacie jedynie zwięzłe matematyczne podsumowanie, co wyklucza błędy ręcznego kopiowania liczb i oszczędza Twoje pieniądze.

---

### Mapa strojenia: fazy −1…5 i podejście „Najpierw przy biurku”

| Faza | Gdzie się odbywa | Co dokładnie jest wykonywane | Wynik etapu |
| :--- | :--- | :--- | :--- |
| **−1 Przygotowanie** | przy biurku | Wprowadzanie parametrów auta, głośników, możliwości DSP i wybór krzywej docelowej. | Utworzenie pliku `project.json` oraz konfiguracji. |
| **0 Zdjęcie danych** | w aucie (1 raz) | Pomiar każdego głośnika z osobna z filtrami **ochronnymi** (HPF); pomiary sweep oraz RTA w ruchu. | Jedna wysokiej jakości i zweryfikowana runda pomiarowa. |
| **1 Fundament** | przy biurku | Obliczanie częstotliwości odcięcia zwrotnic, poziomów głośności, opóźnień i polaryzacji na bazie prognozy fazy. | Podstawowa konfiguracja systemu w rejestrze wersji. |
| **2 Korektor (EQ)** | przy biurku | EQ przychodzi **pakietami**: rezonanse przetwornika → wyrównanie lewa/prawa → ton do celu. Domyślnie tylko podcięcia, do 6 pasm na kanał. Każdy pakiet to jedna decyzja „tak/nie” i nowa wersja rejestru. | Gotowe pliki eksportu ustawień dla Twojego DSP. |
| **3 Werdykt** | w aucie (krótko) | Wprowadzenie wartości do DSP. Kontrola wejściowa automatycznie sprawdza, czy rzeczywiste pomiary pokrywają się z prognozą. | W pełni zweryfikowane i zablokowane techniczne strojenie. |
| **4 Słuchanie** | w aucie | Utwory testowe (płyty EMMA/AYA, CarMus, Chesky) i ściągawka „na co zwracać uwagę”. Jeśli coś dudni lub kłuje w uszy — skill tworzy listę podejrzanych i poprawia pasmo po paśmie w teście A/B (do 3 rund). | Żywe werdykty odsłuchowe powiązane z wersjami. |
| **5 Wariacje** | przy biurku/w aucie | Konfiguracja dodatkowych presetów (pod różne gatunki muzyczne, kanał centralny itp.) bez zmian bazy technicznej. | Dodatkowe presety brzmienia w systemie. |

> [!NOTE]
> Jeśli rzeczywiste pomiary w samochodzie na Fazie 3 rozjadą się z prognozą matematyczną, system automatycznie cofnie krok wstecz i przejdzie do klasycznego, iteracyjnego algorytmu strojenia krok po kroku.

---

### Czego ta metoda kategorycznie odmawia?

* **Zapisywania ustawień bezpośrednio do Twojego DSP** — wprowadzanie parametrów w programie procesora zawsze pozostaje po Twojej stronie.
* **Obliczania opóźnień na podstawie jednego pomiaru** — wymagane są minimum 4 niezależne oceny czasu przybycia dźwięku.
* **Podbijania dźwięku w strefach dziur fazowych (akustycznych zer)** — takie dziury są wywoływane przez interferencję fal w kabinie, a nie przez sam głośnik. Wyrównanie ich poprzez podbicie pasma jest **zasadniczo niemożliwe**: w punkcie odsłuchu nic się nie zmieni, a głośnik i wzmacniacz będą skrajnie przeciążone. Dziurę, którą można bezpiecznie wyrównać, system odróżnia dzięki analizie fazy nadmiarowej (*Excess phase* w REW) — korygowane są wyłącznie obszary minimalnofazowe.
* **Pracy z pomiarami niskiej jakości** — wykryte przesunięcie czasowe mikrofonu (dryft temperatury) lub brak filtrów ochronnych spowoduje natychmiastowe odrzucenie całej rundy pomiarowej.

---

### Które modele AI są oficjalnie wspierane?

* 🧠 **Główny model (Generator):** Claude Opus (z ustawieniem wysiłku intelektualnego `xhigh`).
* 👁️ **Krytyk AI (Recenzent):** Gemini Pro (High).

*Stan na sierpień 2026.* Technologie AI rozwijają się błyskawicznie. Jeśli czytasz ten tekst znacznie później, zweryfikuj obecne rekomendacje dla równoważnych modeli.

> [!IMPORTANT]
> **Nie zmniejszaj poziomu wysiłku Claude poniżej `xhigh`.**
> Słabsze modele lub niższe poziomy wysiłku nie zgłoszą błędu — po prostu po cichu zgodzą się z każdą Twoją akcją i wymyślą parametry technicznie nie do zrealizowania.

---

### Warianty subskrypcji i budżet na AI

* **Wariant 1 (Zalecany podstawowy): Claude Pro ($20/mies.) + darmowy Gemini jako Krytyk**
  Najlepszy balans niezawodności i kosztów. Użyj darmowego klucza API Gemini wygenerowanego w Google AI Studio. Subskrypcję Claude Pro można anulować od razu po zakończeniu strojenia samochodu.
* **Wariant 2 (Oszczędny kompromis): Tylko Gemini ($10 przedpłaty w Google Cloud)**
  Maksymalnie tanio, ale wymaga od Ciebie samodzielnego sprawdzenia każdej cyfry i regularnego czyszczenia kontekstu rozmowy komendą `/clear` przed każdą nową fazą, ponieważ nie ma niezależnego krytyka AI do nadzoru.
* **Wariant 3 (Profesjonalny): Claude Pro ($20) + płatne API Gemini Cloud**
  Całkowity brak jakichkolwiek limitów prędkości zapytań i wyczerpania limitów. Optymalne do profesjonalnego i regularnego strojenia wielu samochodów.

---

### Dlaczego rzeczywiste zużycie tokenów jest niższe, niż się wydaje?

1. Lokalne skrypty Pythona kompresują tysiące punktów pomiarowych REW do krótkich raportów tekstowych. Surowe wykresy nie trafiają na czat.
2. Cała historia projektu jest zapisywana na dysku, więc AI nie musi odczytywać całej ścieżki od samego początku przy każdym zapytaniu.
3. Działa zasada ruchomego okna — ładowane są tylko dane dotyczące obecnej aktywnej fazy pracy. Płacisz za **decyzje**, a nie za przesyłanie danych.

---

## Pierwsza instalacja (macOS i Windows)

### Automatyczna instalacja

Będziesz potrzebować laptopa, mikrofonu pomiarowego, procesora DSP oraz płatnej subskrypcji **Claude Pro lub Max**.

<details>
<summary><b>Instrukcja dla macOS</b></summary>

1. Otwórz program **Terminal** (naciśnij klawisze `Cmd + Spacja` → wpisz `Terminal` → naciśnij `Enter`).
2. Wklej poniższą komendę i naciśnij `Enter`:
   ```bash
   curl -fsSL https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/main/install.sh | bash
   ```
3. Skrypt może poprosić o hasło do Twojego Maca w celu instalacji oficjalnego pakietu Apple Command Line Tools (git). Poczekaj 10–20 minut.

</details>

<details>
<summary><b>Instrukcja dla Windows</b></summary>

1. Otwórz program **Windows PowerShell** (naciśnij klawisz `Win` → wpisz `powershell` → naciśnij `Enter`).
2. Wklej poniższą komendę i naciśnij `Enter`:
   ```powershell
   irm https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/main/install.ps1 | iex
   ```
3. Jeśli w systemie nie ma programu Git, kliknij **Tak** w oknie zapytania o uprawnienia. Skrypt utworzy również wygodny skrót **REW (API on)** na Twoim Pulpicie.

</details>

---

### Gdzie są instalowane komponenty?

Wszystkie pliki są zapisywane wyłącznie w obrębie Twojego profilu użytkownika:

| Komponent | Gdzie jest zapisywany | Po co jest potrzebny |
| :--- | :--- | :--- |
| **Claude Code** | Oficjalne środowisko Anthropic | Główny asystent AI prowadzący proces |
| **Metoda strojenia** | `~/.claude/skills/.autosound-tuning-src` | Folder, w którym Claude Code szuka umiejętności i narzędzi |
| **Autosound TCC** | Folder użytkownika i skrót na Pulpicie | Aplikacja graficzna oraz izolowane środowisko Python 3.12 |
| **Narzędzie `agy`** | Profil użytkownika | Narzędzie od Google do szybkiej komunikacji w tle z Krytykiem Gemini |

---

### Pierwsze uruchomienie i logowanie

1. **Logowanie do Claude:** Pod koniec instalacji skrypt automatycznie uruchomi komendę `claude auth login`. Zaloguj się w przeglądarce na swoje płatne konto i kliknij przycisk **Authorize**.
2. **Logowanie do Gemini:** Uruchom jeden raz w nowym oknie terminala komendę `agy` i zaloguj się na swoje konto Google.
3. **Rozpoczęcie pracy:** Utwórz pusty folder na pliki samochodu (np. `MojeStrojenie`). Otwórz go w aplikacji **Autosound TCC** (przyciskiem *Browse…*) lub w nowym terminalu (`cd ścieżka` → wpisz `claude`) i napisz na czacie: **„skonfigurujmy nowe auto od zera”** (lub po angielsku: *"tune a new car from scratch"*).

---

### Aktualizacja, blokowanie wersji i usuwanie

* **Aktualizacja:** Uruchom tę samą linię instalacyjną ponownie. Skrypt automatycznie pobierze najnowszy tag `v3.*` (jest to wersja przedpremierowa, a nie stabilna gałąź — stabilna to linia 2.8.x) i nie naruszy Twoich projektów.
* **Blokowanie wersji:** Użyj flag `--skill-ref v3.0.33` oraz `--tcc-ref v0.1.22` — podawaj je jako **parę**: te dwie wersje zostały wydane i przetestowane razem, a mieszana para jest nieprzetestowana na macOS lub `-SkillRef` oraz `-TccRef` na Windows podczas instalacji.
* **Usuwanie:** Uruchom instalator z flagą `--uninstall` (lub dodatkowo `--all` dla pełnego oczyszczenia środowisk). Foldery Twoich projektów nigdy nie zostaną usunięte.

---

## Aplikacja graficzna Autosound TCC

### Co to jest i czy jest mi potrzebne?

Program [TCC](https://github.com/ayukhno/autosound-tcc) pozwala na wygodną pracę z metodą w oknie graficznym na macOS oraz Windows. Widzisz strukturę systemu, wykresy REW, plan krok po kroku oraz okno czatu z AI na jednym ekranie. Program nie jest obowiązkowy — możesz w pełni nastroić auto za pomocą interfejsu tekstowego Claude Code, ponieważ wszystkie dane projektu są zapisywane w zwykłych plikach maszynowych na dysku. Aplikacja jest młodsza niż sama metoda strojenia i obecnie ma status wersji beta.

### Praca na dwa okna (Terminal + Grafika)

Program oraz terminal korzystają z tych samych plików projektu. Możesz swobodnie przełączać się między nimi: wszelkie kroki czy wersje ustawień utworzone w konsoli są natychmiast widoczne w interfejsie graficznym i na odwrót.

### Modele AI w aplikacji

Aplikacja korzysta z Twojego płatnego taryfy Claude (przez oficjalne Anthropic SDK) oraz darmowego konta Google przez lokalne narzędzie `agy` do pracy krytyka AI. Alternatywne modele stają się dostępne tylko pod warunkiem aktywacji systemu `omp` (rozliczane osobno).

### Aktualizacje i zgłaszanie błędów

Program aktualizuje się automatycznie wraz z rdzeniem matematycznym. Sprawdzić obecne wersje można w zakładce *Diagnostics → Installation*. Błędy interfejsu zgłaszaj przez przycisk *Report a problem* na GitHubie programu TCC, a błędy logiki strojenia — w repozytorium samego skilla.

---

## Autonomiczny Krytyk AI Gemini/Antigravity

Podwójny cykl weryfikacji (Generator ↔ Krytyk Gemini) całkowicie wyklucza subiektywne błędy matematyczne modeli. Krytyk wychwytuje to, czego pierwsze AI nie zauważa we własnej pracy. Działa automatycznie w tle przez lokalny skrypt — nie trzeba niczego ręcznie przenosić ani kopiować. Jest to opcjonalne, ale właśnie stąd uzyskasz największe korzyści dla efektu końcowego.

### Instalacja dla macOS i Windows (Zalecana)

Oficjalny klient **Antigravity CLI (`agy`)** od Google nie wymaga kluczy API i korzysta z darmowego logowania OAuth przez przeglądarkę.

1. **Instalacja:** Instalator dodał już to narzędzie automatycznie. W celu ręcznej instalacji wykonaj:
   * *macOS:* `curl -fsSL https://antigravity.google/cli/install.sh | bash`
   * *Windows:* `irm https://antigravity.google/cli/install.ps1 | iex`
2. **Logowanie:** Uruchom komendę `agy` w nowym terminalu, zaloguj się w przeglądarce na konto Google, które ma dostęp do Antigravity, po czym wróć do konsoli i wpisz `/quit`.
3. **Test:** Sprawdź działanie komendą `agy -p "Hello, world!"`.

---

### Wariant rezerwowy: Bezpośredni klucz API Gemini

Na systemie Linux lub przy wyczerpaniu limitów Antigravity możesz używać darmowych kluczy Gemini API bezpośrednio:

1. Pobierz darmowy klucz API na stronie **[aistudio.google.com/apikey](https://aistudio.google.com/apikey)**.
2. Utwórz plik tekstowy `.critic-env` w folderze **Twojego projektu** (wewnątrz `rew_analitic/` lub w katalogu, z którego uruchamiasz pracę) i zapisz tam:
   ```env
   GEMINI_API_KEY=twoj_klucz_tutaj
   ```
3. Skrypty automatycznie wykryją klucz i przejdą na bezpośrednie zapytania HTTPS do Gemini API.

> [!TIP]
> Jeśli klucz ani narzędzie `agy` nie zostaną znalezione, system automatycznie przejdzie w rezerwowy tryb pracy w tle (Autopilot self-loop) lub zaproponuje ręczne kopiowanie propozycji przez schowek (Clipboard Mode).

---

### Czy można pracować tylko w Gemini, bez Claude?

Tak, ale jako uruchomienie ręczne, a nie automatyczna instalacja. Daj sesji agencyjnej Gemini (z dostępem do plików i terminala) bezpośrednie polecenie:

> Clone `https://github.com/ayukhno/autosound-tuning-skill`, read `skills/autosound-tuning/SKILL.md`, and follow that method as your operating instructions for this session.

Ponieważ nie ma tam mechanizmu ruchomego okna, przy długich sesjach Gemini może stopniowo tracić dokładność. Najbardziej stabilny darmowy wariant to **Wariant 4** (gotowe prompty dla [Google AI Studio](https://aistudio.google.com/) na gałęzi [manual_step-by-step](https://github.com/ayukhno/autosound-tuning-skill/tree/manual_step-by-step)).

---

## Przeprowadzanie pomiarów

### Pomiar fazy: Mikrofony XLR kontra USB (UMIK-1/2)

* **Mikrofony XLR (Behringer ECM8000, Beyerdynamic MM1 itp.):** Podłączane przez zewnętrzną kartę dźwiękową. Pozwalają na użycie **fizycznej pętli zwrotnej (loopback)** — kabla łączącego wyjście karty z jej wolnym wejściem. Daje to komputerowi sprzętowe, absolutnie stabilne odniesienie czasu startu pomiaru z dokładnością do jednej próbki (sample).
* **Mikrofony USB (UMIK-1 / UMIK-2):** Podłączane bezpośrednio do portu USB. Nie posiadają wejścia analogowego, dlatego podłączenie fizycznego kabla loopback jest niemożliwe.

---

### Czy można zmierzyć fazę na UMIK-1?

**Tak.** W celu uzyskania dokładnych danych fazy użyj w REW funkcji **Acoustic Timing Reference (akustyczne odniesienie czasu)**. Przed rozpoczęciem każdego sygnału pomiarowego karta dźwiękowa odtwarza krótki sygnał o wysokiej częstotliwości („chirp”) przez jeden wybrany głośnik (zazwyczaj najbliższy mikrofonowi tweeter), który służy jako punkt zerowy odniesienia czasu dla mierzonego kanału.

Szczegółową konfigurację REW dla mikrofonów USB znajdziesz w poradniku wideo: [Measuring Speaker Phase in REW](https://www.youtube.com/watch?v=El-kwZ5_nnU).

> [!WARNING]
> **Zdejmuj wszystkie pomiary bez przerwy za jednym razem i koniecznie zmierz pierwszy głośnik ponownie na końcu sesji!**
> * **Dryft temperatury powietrza niszczy dokładność:** Prędkość dźwięku zależy od temperatury powietrza w kabinie. Zmiana temperatury o zaledwie kilka stopni przesuwa czas przybycia sygnału o ułamki milisekund. Jest to krytyczne dla zgrywania fazowego głośników średnio- i wysokotonowych na częstotliwościach podziału zwrotnicy.
> * **Przesunięcie kumuluje się bezpośrednio od uruchomień pomiarów:** Jeden głośnik, mierzony 6 razy z rzędu w ciągu 18 minut, przesunął czas przybycia dźwięku o jedną próbkę (10 mikrosekund, co odpowiada przesunięciu mikrofonu o ~3.6 mm). Przesunięcie zależało od uruchomień pomiarów, a nie od samego czasu oczekiwania.
> * **Koniecznie wykonaj pomiar kontrolny pierwszego głośnika na końcu sesji:** Kontrola wejściowa w wersji 3.x automatycznie porówna te dwa pomiary z dokładnością do ułamków próbek i po prostu odrzuci całą serię pomiarów, jeśli wykryje niebezpieczny dryft temperatury lub systemowe przesunięcie czasu.

---

### Zasady nazewnictwa pomiarów w REW

Narzędzia obliczeniowe szukają odpowiednich wykresów wyłącznie po ich nazwach w REW:

* `m-L_01 (sw)` — kanał `m-L` (lewy średniotonowy), runda pomiarowa `01`, pomiar sweep.
* `m-L_01 (rta)` — pomiar w ruchu (RTA, moving-mic average) dla tego samego głośnika.
* `sw_01 (sw)`, `w-R_01 (sw)`, `tw-L_01 (sw)` — subwoofer, prawy woofer (midbas), lewy tweeter odpowiednio.
* `L_01 (rta)`, `ALL_01 (rta)` — sumaryczny pomiar RTA całej lewej strony lub całego systemu razem.
* `m-L p5_01 (sw)` — pomiar głośnika w osobnym punkcie kontrolnym przestrzeni `p5` (dopuszczalna jest również nazwa `m-L_01 (sw) p5`).
* `m-L-ctl1_01 (sw)` i `m-L-ctl3_01 (sw)` — kontrola czasu: pierwszy otwiera serię pomiarów głośnika, drugi ją zamyka (w aucie te same dwa pomiary można nazwać jako `m-L_01ctl` i `m-L_01rep`).
* `m-L_final (sw)` — pomiar weryfikacyjny po zapisaniu ostatecznych parametrów.

Pełny schemat przeprowadzania pomiarów oraz ich kolejność zostały opisane w dokumencie [`references/phases/capture-session-sheet.md`](skills/autosound-tuning/references/phases/capture-session-sheet.md).

---

### Sesja pomiarowa (Capture): dlaczego tylko filtry ochronne?

> [!IMPORTANT]
> **REW musi być otwarty przez cały czas pracy:** skill odczytuje pomiary bezpośrednio z aktywnego okna programu przez API, a nie z plików wyeksportowanych na dysk.

Sesja pomiarowa to pomiar każdego głośnika z osobna przy zastosowaniu w DSP **wyłącznie filtrów ochronnych** (High-Pass / HPF dla średniotonowych i tweeterów na bezpiecznej częstotliwości, aby nie uległy uszkodzeniu podczas głośnego pomiaru sweep). Żadnych roboczych zwrotnic, opóźnień ani korektora nie wolno włączać — potrzebujemy czystej fizycznej charakterystyki głośnika w kabinie samochodu. Skrypty matematyczne automatycznie „odejmą” wpływ filtra ochronnego przed obliczeniem filtracji roboczej, co gwarantuje idealną dokładność zgrywania fazowego.

*Ważne:* Wycisz (Mute) wszystkie nieaktywne kanały bezpośrednio w programie procesora DSP. Utrzymuj stabilny poziom głośności karty dźwiękowej i radia przez cały czas trwania sesji pomiarowej.

---

### Po co są pozycje p1…p9 i kontrola czasu ctl?

* **Określenie natury dziur i pików:** Rzeczywiste rezonanse własne głośnika pozostają stabilne na wykresie przy przesunięciu mikrofonu o kilka centymetrów (można je korygować korektorem). Akustyczne dziury wywołane odbiciami dźwięku od szyb czy foteli przesuwają się chaotycznie po częstotliwości przy ruchu mikrofonu — ich podbijanie korektorem jest bezcelowe i niebezpieczne, dlatego AI ignoruje takie obszary.
* **Obliczanie dobroci (Q):** Rozrzut pomiarów w punktach `p1…p9` wokół głowy kierowcy pozwala na dokładne obliczenie bezpiecznej granicy dobroci filtrów korektora.
* **Kontrola dryftu czasu:** Powtórne pomiary punktu centralnego `ctl` pozwalają systemowi na matematyczną kompensację fizycznego dryftu czasu karty dźwiękowej podczas sesji pomiarowej.

---

## Krzywe docelowe (Target Curves)

### Jak stworzyć i skonfigurować własną krzywą docelową?

Nie istnieje jedna „prawidłowa” krzywa docelowa — to Twoja wstępna hipoteza robocza, którą będziesz dopasowywać na słuch po uzyskaniu podstawowego strojenia technicznego.

1. **Zleć obliczenie AI:** Opisz swoje ulubione gatunki muzyczne, preferowany poziom głośności odsłuchu, życzenia dotyczące znanych krzywych docelowych (np.: *„weź za podstawę ResoNix Accurate, ale dodaj +2 dB najniższego basu na subwooferze i zrób wysokie tony nieco łagodniejszymi”*) lub skargi na dźwięk (*dudni, kłuje w uszy, brak przestrzeni*). Skrypt wygeneruje plik krzywej, zapisze go w folderze projektu i zbuduje indywidualne krzywe docelowe dla każdego przetwornika.
2. **Narysuj ręcznie:** Wejdź na darmową stronę internetową **Nono Tuning Tool** ([nonotuningtool.com](https://nonotuningtool.com) → sekcja *Custom Target Curve*), narysuj myszką swoją krzywą, wyeksportuj plik `.txt` i wrzuć go do folderu swojego projektu.
3. **Porównaj wykresy docelowe:** Skorzystaj z naszego interaktywnego wizualizatora online:
   **[Otwórz wizualizator krzywych docelowych online](https://ayukhno.github.io/autosound-tuning-skill/_curve-visualizer.html?lang=pl)**. Tutaj możesz porównać swoją krzywą bezpośrednio ze standardami branżowymi SQ-Comp-Ref, ResoNix, Audiofrog, Harman, Jazzi czy Whitledge. Kliknięcie prawym przyciskiem myszy na dowolny punkt wykresu wyświetli wyjaśnienie dotyczące znaczenia brzmieniowego danego zakresu częstotliwości.

---

## Projekt na dysku i DSP

### Struktura folderu projektu i kopia zapasowa

Jeden folder na Twoim dysku zawiera kompletną dokumentację i konfigurację Twojego systemu:

| Plik / Folder | Zawartość | Po co jest potrzebny |
| :--- | :--- | :--- |
| **`project.json`** | Dane techniczne systemu | Kanały głośników, wyjścia DSP, profil procesora, specyfikacja mikrofonu i aktywna krzywa docelowa. |
| **`registry.json`** | Rejestr wersji strojenia | Pełna, chronologiczna historia wszystkich filtrów zwrotnicy, opóźnień, poziomów głośności i pasm korektora. |
| **`process-state.json`** | Bieżący stan techniczny | Informacja o aktywnej fazie procesu oraz pomyślnie zweryfikowanych pomiarach. |
| **`autosound_context.md`** | Kontekst auta i notatki | Indywidualny słownik car audio Twojego auta, cechy instalacji i Twoje oceny odsłuchowe. |
| **`*.txt` / `*.json`** | Krzywe docelowe i eksporty DSP | Pliki konfiguracyjne do importu do Twojego DSP oraz pliki krzywych dla programu REW. |

> [!IMPORTANT]
> **Dbaj o kopię zapasową tych małych plików tekstowych i JSON.**
> Skrajnie duże pliki pomiarowe REW `.mdat` (od 16 do 112 MB na plik) nie muszą być koniecznie archiwizowane, ponieważ pomiary można wykonać ponownie w każdej chwili. Nasz instalator oferuje opcję automatycznego, bezpłatnego i prywatnego backupu folderu projektu na GitHubie.

---

### Kompatybilność z procesorami i import filtrów do DSP

Skill oblicza dokładne wartości filtrów i zapisuje je do pliku:

* **Audiotec Fischer (Helix / MATCH / BRAX):** Rodzina procesorów, na której bezpośrednio tworzono i optymalizowano tę metodę. Generowany jest gotowy plik Full EQ, który oficjalny program DSP PC-Tool importuje jednym kliknięciem dla wszystkich kanałów jednocześnie.
* **Inne procesory DSP:** Tworzony jest standardowy plik eksportu w formacie REW Generic (do 20 pasm EQ) lub rozszerzony plik zwrotnicy. W celu wygodnego półautomatycznego wprowadzania wartości za pomocą makr klawiatury użyj darmowego narzędzia: [REW-EQ-CopyPaste-Assistant](https://github.com/IvanBakhmutov/REW-EQ-CopyPaste-Assistant).
* **Kontrola kompatybilności:** Skrypty automatycznie porównują każdy obliczony filtr z rzeczywistymi technicznymi ograniczeniami Twojego modelu procesora (dostępne pasma, częstotliwość próbkowania, typy filtrów) przed wygenerowaniem plików eksportu.

---

### Praca ze zwrotnicami pasywnymi (tweeter + średniotonowy na jednym kanale)

Para głośników na zwrotnicy pasywnej jest traktowana przez system jako **jeden wspólny kanał**: otrzymuje jeden wspólny pomiar, jedno opóźnienie, wspólny poziom głośności oraz jeden zestaw pasm korektora.

Wszystko inne działa jak zwykle, a wypadkowe pasmo przenoszenia zostanie odwzorowane fizycznie poprawnie — włączając w to ewentualne problemy fazowe w punkcie podziału zwrotnicy pasywnej. Tego jednak, czego żaden program na świecie nie zrobi z zewnątrz, to wyrównanie opóźnień lub fazy między tweeterem a średniotonowym **wewnątrz** tej pasywnej grupy. Do tego niezbędny jest system w pełni aktywny (poka-kanałowy).

---

### Gdzie znaleźć pełną listę możliwości metody?

Szczegółowy przegląd wszystkich 68 możliwości i narzędzi systemu (z dokładnymi komendami tekstowymi, warunkami odmowy, etapem rozwoju i uzasadnieniem naukowym) znajduje się w interaktywnej tablicy Capabilities-board:
[`references/core/capabilities.md`](skills/autosound-tuning/references/core/capabilities.md).
