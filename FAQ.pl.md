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

* 🖥️ **Wariant 1 · Wersja 3.x w oknie graficznym (Autosound TCC) — [Zalecany]**  
  Najbardziej zautomatyzowana i przejrzysta ścieżka. Instalator konfiguruje Claude Code, Pythona, rdzeń metody, interfejs graficzny oraz automatycznego krytyka AI.
  * **Wymagania:** macOS lub Windows, płatny Claude Pro/Max, wersja beta REW z włączonym API; aplikacja dodaje około 700 MB do pobieranych danych.
  * **Zalety:** Widzisz strukturę systemu, wykresy pomiarów, plan krok po kroku i okno czatu w jednym interfejsie. Stan jest zapisywany automatycznie na dysku, a działania w rejestrze wersji są śledzone.
  * **Wady:** Aplikacja graficzna jest młodsza niż sama metoda strojenia i obecnie ma status wersji beta.

* 💻 **Wariant 2 · Wersja 3.x w terminalu (Claude Code lub wtyczka headless)**  
  Dokładnie ten sam nowoczesny rdzeń, narzędzia obliczeniowe i poziom automatyzacji, ale interakcja odbywa się tekstowo w konsoli. Instalowany z flagą `--terminal` (lub przez wtyczkę Claude Code).
  * **Wymagania:** Te same subskrypcje i wersja beta REW z włączonym API, ale bez interfejsu graficznego.
  * **Zalety:** Maksymalna prędkość działania, zerowy narzut GUI, idealne dla miłośników konsoli. Projekty są w 100% kompatybilne z aplikacją graficzną TCC.

* 🏆 **Wariant 3 · Linia 2.x (Sprawdzony mistrz)**  
  Klasyczna wtyczka dla Claude Code, zablokowana na wersji `v2.8.3` (gałąź `2.x`). Nastrojony tym algorytmem samochód autora zdobył w 2026 roku nagrody na mistrzostwach EMMA i AYA.
  * **Wymagania:** Płatny Claude Pro, wersja beta REW z włączonym API, praca w terminalu.
  * **Zalety:** Ustalony, sprawdzony na zawodach algorytm. Otrzymuje wyłącznie krytyczne poprawki błędów, bez dodawania nowych funkcji.
  * **Wady:** Ręczne śledzenie stanu w tekstowych plikach Markdown (`dsp-state-current.md`), brak automatycznej prognozy wirtualnej „Najpierw przy biurku” i brak nowoczesnych narzędzi obliczeniowych.

* 🌐 **Wariant 4 · Czat internetowy (Bez instalacji oprogramowania)**  
  W pełni ręczny, prowadzony krok po kroku proces strojenia za pośrednictwem [gałęzi manual_step-by-step](https://github.com/ayukhno/autosound-tuning-skill/tree/manual_step-by-step).
  * **Wymagania:** Darmowe Google AI Studio lub dowolny czat internetowy z wybraną przez ciebie AI.
  * **Zalety:** Całkowicie za darmo. Nie wymaga instalacji żadnego oprogramowania ani narzędzi programistycznych na twoim komputerze.
  * **Wady:** Każdy krok wykonuje się ręcznie (kopiowanie promptów, samodzielny eksport plików tekstowych z REW), brak integracji przez API i brak weryfikacji obliczeń przez lokalne skrypty.

---

### Który wariant wybrać?

* **Chcesz maksimum automatyzacji i informacji wizualnej:** Wybierz **Wariant 1 (TCC)**.
* **Wolisz konsolę i maksymalną prędkość:** Wybierz **Wariant 2 (3.x Terminal)**.
* **Chcesz klasycznej, sprawdzonej na zawodach wtyczki:** Wybierz **Wariant 3 (2.8.3)**.
* **Chcesz przetestować logikę za darmo bez lokalnego oprogramowania:** Wybierz **Wariant 4 (Czat internetowy)**.

> [!NOTE]
> Nie jesteś zablokowany w jednym wyborze: projekty linii 3.x otwierają się bez problemu zarówno w konsoli, jak i w programie graficznym TCC.

---

### Jak sprawdzić zainstalowaną wersję?

* **Po wpisanej komendzie:** Jeśli instalowałeś wtyczkę komendą `/plugin install autosound-tuning` wewnątrz Claude Code, używasz wersji **2.x**. Jeśli uruchamiałeś skrypt instalacyjny w jednej linii (`curl … | bash` lub `irm … | iex`), używasz wersji **3.x**.
* **Po zawartości folderu projektu:** Jeśli folder zawiera plik `dsp-state-current.md`, to projekt **2.x**. Jeśli folder zawiera maszynowe pliki `project.json` oraz `process-state.json`, to projekt **3.x**.
* **Przez interfejs aplikacji:** W aplikacji TCC przejdź do *Diagnostics → Installation*.

---

### Jak pozostać na stabilnej linii 2.x

Standardowa automatyczna aktualizacja wtyczki nie przeniesie cię na wersję 3.x bez twojej zgody. Jednak jeśli chcesz całkowicie zamrozić wersję i lokalnie kontrolować aktualizacje na gałęzi 2.x, sklonuj repozytorium samodzielnie:

```bash
git clone -b 2.x https://github.com/ayukhno/autosound-tuning-skill.git ~/autosound-2x
```

Następnie wykonaj te dwie komendy w terminalu:
```bash
claude plugin marketplace add ~/autosound-2x
claude plugin install autosound-tuning
```
Teraz twoja wtyczka wskazuje na twój lokalny folder. Możesz ją zaktualizować w dowolnym momencie za pomocą prostego `git -C ~/autosound-2x pull`.

---

### Przejście z 2.x na 3.x

W systemie może być aktywna tylko jedna taka wtyczka jednocześnie. Przed instalacją wersji 3.x koniecznie usuń starą wersję 2.x (w terminalu):

```
claude plugin uninstall autosound-tuning
claude plugin marketplace remove autosound-tuning-skill
```

Po zainstalowaniu wersji 3.x możesz przenieść istniejący projekt auta do nowego formatu maszynowego za pomocą automatycznego migratora:

```sh
python3 ~/.claude/skills/.autosound-tuning-src/skills/autosound-tuning/rew_tool/state/migrate.py <path-to-old-project> --into <path-to-new-project>
```
*(Uwaga: zweryfikuj przypisanie kanałów i specyfikacje głośników po przeprowadzeniu migracji).*

---

### Główne zmiany w wersji 3.x

* 📦 **Projekt jako struktura danych:** Wszystkie parametry systemu są zapisywane na dysku w `project.json` i `process/process-state.json`. AI odczytuje fakty maszynowe z dysku, zamiast polegać na pamięci czatu.
* 🛋️ **Podejście „Najpierw przy biurku”:** Zamiast wielu wyjazdów do auta — **jedna zdyscyplinowana sesja na zdjęcie danych akustycznych** (Faza 0) i **jedna krótka wizyta weryfikacyjna** (Faza 3). Cała analiza, obliczenia zwrotnic, wyrównanie fazy i projektowanie EQ są wykonywane przy biurku.
* 🧮 **Weryfikacja matematyczna:** Dedykowane lokalne skrypty Pythona analizują krzywe pod kątem minimalnych strat fazy, oceniają początek narastania impulsu i sprawdzają stabilność czasową mikrofonu.
* 🛑 **Bramki strukturalne:** Jeśli pomiary wejściowe wykazują nadmierny dryft czasowy, brakujące kanały lub naruszone limity bezpieczeństwa, system zatrzymuje się i nazywa problem przed przejściem dalej.

---

## Filozofia i architektura: po co nam AI?

### Misja i koncepcja

Tworzymy **inteligentny egzoszkielet** do strojenia dźwięku. Człowiek (Arbiter) zawsze pozostaje najważniejszym ogniwem — słucha systemu, ocenia głębokość, wysokość i stabilność sceny dźwiękowej i podejmuje ostateczne decyzje.

AI przejmuje na siebie rutynowe obliczenia i akustykę kabiny: analizuje czasy przybycia impulsów, krzywe fazowe, oblicza opóźnienia na połączeniach pasm (stykach) i komunikuje się z REW przez API, uwalniając twój czas na twórczą część słuchania muzyki.

---

### Dlaczego to wyspecjalizowany skill, a nie zwykły czat?

* **Stan zapisywany na dysku:** Standardowy czat AI zapomina początkowe wartości, myli poziomy głośności lub zmienia częstotliwości podziału zwrotnicy w trakcie długiej sesji. Nasz system zapisuje stan projektu na dysku. AI odczytuje ten plik na każdym kroku — jej kontekst jest oparty na stanie z dysku, a nie na pamięci bufora czatu.
* **Specjalistyczna wiedza z dziedziny akustyki:** Skill zawiera ścisłe zasady bezpieczeństwa chroniące głośniki, logikę wyrównywania fazy, wstępnie skonfigurowane krzywe docelowe oraz heurystyki akustyki kabiny, których ogólne modele AI nie posiadają.
* **Lokalne przetwarzanie przez REW API:** Surowe dane pomiarowe (tysiące punktów na krzywą) są przetwarzane lokalnie przez skrypty Pythona w milisekundy. AI otrzymuje na czacie jedynie zwięzłe podsumowania matematyczne, oszczędzając czas i budżet tokenów.

---

### Mapa strojenia: fazy −1…5 i podejście „Najpierw przy biurku”

| Faza | Gdzie się odbywa | Co jest wykonywane | Wynik etapu |
| :--- | :--- | :--- | :--- |
| **−1 Przygotowanie** | przy biurku | Wprowadzanie konfiguracji bazowej (kanały głośników, wyjścia DSP, profil DSP, mikrofon, miejsce odniesienia). Około 17 odpowiedzi na wstępie; o resztę pyta ta faza, która tego potrzebuje. | Utworzone `project.json` i pliki konfiguracyjne. |
| **0 Zdjęcie danych** | w aucie (1 raz) | Pomiar każdego głośnika z **włączonymi filtrami ochronnymi** (sweepy na statywie `(sw)` i mikrofon w ruchu `(rta)`). Finalizacja krzywej docelowej po zdjęciu danych. | Zweryfikowana bazowa runda pomiarowa i aktywna krzywa docelowa. |
| **1 Fundament** | przy biurku | Opisujesz swoje życzenia dotyczące zwrotnicy własnymi słowami, a one są sprawdzane pod kątem sztywnych limitów. AI oferuje co najwyżej trzy warianty zwrotnicy — najlepszy, jaki znajdzie matematyka, oraz te zbudowane z twoich życzeń, każdy z jego kosztem — a ty wybierasz. Rezonanse przetworników i zgrubne EQ każdego głośnika są rozwiązywane tutaj; poziomy, polaryzacje i opóźnienia są odczytywane ręcznie z początku każdego impulsu; sumy są prognozowane i opisywane. | Bazowe strojenie systemu w rejestrze wersji. |
| **2 Korektor** | przy biurku | Druga część EQ, w **pakietach** i w następującej kolejności: pary lewa/prawa na pasmo → połączenia pasm każdej strony → sub z midami → każda strona w całości → wszystko razem → głośnik centralny → tył. Domyślnie **tylko podcięcia**, maks. 6 pasm na kanał. Każdy pakiet to pojedyncza decyzja „tak/nie” i nowa wersja rejestru. | Gotowa do importu konfiguracja EQ dla DSP. |
| **3 Werdykt** | w aucie (krótko) | Wgrywanie parametrów do DSP. Sweep weryfikacyjny automatycznie sprawdza, czy rzeczywiste pomiary pokrywają się z prognozami matematycznymi. Obowiązkowa ocena odsłuchowa. | W pełni zweryfikowane, zablokowane strojenie techniczne. |
| **4 Słuchanie** | w aucie | Utwory testowe (płyty EMMA/AYA, CarMus, Chesky) i ściągawka „na co zwracać uwagę”. Jeśli coś dudni lub brzmi ostro, skill sporządza listę podejrzanych pasm i testuje je pojedynczo w teście A/B (trzech podejrzanych × trzy rundy, potem stop). | Werdykty odsłuchowe powiązane z wersjami. |
| **5 Wariacje** | biurko / w aucie | Konfiguracja dodatkowych presetów (różne gatunki muzyczne, inny charakter brzmienia) na bazie fundamentu technicznego. | Dodatkowe presety brzmienia w DSP. |

---

### Czego ta metoda kategorycznie odmawia?

* **Wprowadzania parametrów bezpośrednio do twojego DSP** — wprowadzanie wartości do oprogramowania procesora zawsze pozostaje twoim działaniem.
* **Obliczania opóźnień na podstawie narzędzi automatycznych (auto-delay) lub korelacji wzajemnej** — opóźnienia akustyczne są sprawdzane ręcznie na podstawie początkowego narastania odpowiedzi impulsowej ($t_0$). Narzędzia automatycznego szacowania opóźnień w REW są surowo zabronione.
* **Podbijania częstotliwości w akustycznych zerach (strefach znoszenia fal)** — zapady wynikające ze znoszenia fal są powodowane przez odbicia od przegród, a nie przez sam głośnik. Wypełnianie ich za pomocą EQ jest bezcelowe: podbicie obciąża jedynie wzmacniacz i głośnik, nie zmieniając niczego w miejscu odsłuchu. Metoda ogranicza jakiekolwiek podbicie do +6 dB, a zapad, który wymagałby więcej, jest niemal na pewno znoszeniem fal. Zapady bezpieczne do skorygowania są identyfikowane za pomocą analizy *Excess phase* w REW.
* **Kontynuowania pracy z wątpliwymi pomiarami** — wykryty dryft czasowy między kontrolnymi sweepami sesji lub brakujące filtry ochronne zostaną zasygnalizowane przed przejściem dalej.

---

### Które modele AI są oficjalnie wspierane?

* 🧠 **Główny model (Generator):** **Claude Opus** (skonfigurowany z poziomem wysiłku `xhigh`; `max` dla złożonego wyrównywania fazy).
* 👁️ **Recenzent AI (Krytyk):** **Gemini Pro (High)** przez Google Antigravity (`agy`) lub bezpośredni klucz API.
* 🛠️ **Inni recenzenci:** Selektor w TCC oferuje również model Codex (a z flagą `--with-omp` także inne modele) do roli recenzenta. Generatorem pozostaje Claude.

*Stan na wrzesień 2026.* Nazwy modeli szybko się zmieniają. Jeśli któryś z wymienionych tutaj zostanie odrzucony (na przykład `agy` odpowie, że model nie jest obsługiwany w twojej lokalizacji), wybierz inny z listy `agy models`.

> [!IMPORTANT]
> **Nie obniżaj poziomu wysiłku Claude poniżej `xhigh`.**  
> Słabsze modele lub niższe poziomy wysiłku nie zgłoszą błędów — po cichu zgodzą się z niepoprawnymi danymi wejściowymi, zhalucynują niemożliwe parametry akustyczne lub przeoczą znoszenie fazowe.

---

### Warianty subskrypcji i budżet na AI

* **Wariant 1 (Zalecany): Claude Pro ($20/mies.) lub Max + darmowy Gemini przez Antigravity (`agy`)**  
  Najlepszy balans niezawodności i kosztów. Recenzent działa przez CLI `agy` od Google po zalogowaniu się na konto Google. Stała subskrypcja pokrywa twoje sesje bez naliczania opłat za tokeny i można ją anulować zaraz po zakończeniu strojenia samochodu.
* **Wariant 2 (API rozliczane według zużycia — Pay-as-you-go):**  
  Przeprowadzenie pełnego cyklu strojenia wyłącznie przez tokeny API rozliczane według zużycia szybko generuje koszty. Pomiary samego autora: same Fazy 0–2, uruchomione przez płatne API Gemini, kosztowały około $20 — i to przed jakimikolwiek rundami odsłuchowymi. Stała miesięczna subskrypcja jest zauważalnie bardziej opłacalna.
* **Wariant 3 (Bezpośredni klucz API Gemini):**  
  Jeśli limity Antigravity CLI zostaną wyczerpane, jako wariant rezerwowy można wykorzystać darmowy lub płatny klucz API z Google AI Studio. Klucz trafia do magazynu kluczy systemu operacyjnego (zobacz [Wariant rezerwowy](#wariant-rezerwowy-bezpośredni-klucz-api-gemini)).

---

### Dlaczego rzeczywiste zużycie tokenów jest niższe, niż się wydaje?

1. Lokalne skrypty Pythona kompresują tysiące punktów pomiarowych REW do zwięzłych podsumowań matematycznych. Surowe wykresy nigdy nie trafiają na czat.
2. Stan projektu znajduje się na dysku, więc AI nie odczytuje na nowo całej historii rozmowy przy każdym zapytaniu.
3. Stosowana jest zasada ruchomego okna — ładowane są tylko dane powiązane z aktualnie aktywną fazą.

---

## Pierwsza instalacja (macOS i Windows)

### Automatyczna instalacja

Będziesz potrzebować laptopa, mikrofonu pomiarowego, procesora DSP w aucie oraz płatnej subskrypcji **Claude Pro lub Max**.

<details>
<summary><b>Instrukcja dla macOS</b></summary>

1. Otwórz program **Terminal** (naciśnij klawisze `Cmd + Spacja` → wpisz `Terminal` → naciśnij `Enter`).
2. Wklej poniższą komendę i naciśnij `Enter`:
   ```bash
   curl -fsSL https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/v3.0.61/install.sh | bash
   ```
3. Jeśli brakuje narzędzi Apple Command Line Tools, oficjalne okno instalatora Apple otworzy się jeden raz — kliknij Zainstaluj. Sam skrypt nigdy nie prosi o twoje hasło. Poczekaj 10–20 minut.

</details>

<details>
<summary><b>Instrukcja dla Windows</b></summary>

1. Otwórz program **Windows PowerShell** (naciśnij Start → wpisz `powershell` → naciśnij `Enter`).
2. Wklej poniższą komendę i naciśnij `Enter`:
   ```powershell
   irm https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/v3.0.61/install.ps1 | iex
   ```
3. Jeśli brakuje programu Git, zezwól na jego instalację. Skrypt utworzy również skrót **REW (API on)** na twoim Pulpicie.

</details>

---

### Gdzie są instalowane komponenty?

Wszystkie pliki są zapisywane w obrębie twojego profilu użytkownika:

| Komponent | Ścieżka instalacji | Przeznaczenie |
| :--- | :--- | :--- |
| **Claude Code** | Oficjalny katalog Anthropic | Główny asystent AI prowadzący proces |
| **Metoda strojenia** | `~/.claude/skills/.autosound-tuning-src`, podlinkowany jako `~/.claude/skills/autosound-tuning` | Kopia robocza metody i nazwa, pod którą znajduje ją Claude Code |
| **Python 3.12** | `~/.local/bin/python3` (przez `uv`) | Uruchamia lokalne narzędzia metody |
| **Autosound TCC** | Folder użytkownika i skrót na Pulpicie | Aplikacja graficzna oraz izolowane środowisko Python 3.12 |
| **Narzędzie `agy`** | Profil użytkownika | Narzędzie CLI od Google do szybkiej komunikacji z Krytykiem Gemini |
| **Konfiguracja recenzenta** | `~/.config/autosound/critic-env` (`%APPDATA%\autosound\critic-env` w Windows) | Model recenzenta i opcjonalny klucz API — poza każdym projektem |
| **`gh`, `omp`** | Profil użytkownika — tylko na żądanie (`--github`, `--with-omp`) | Pomocnik kopii zapasowej na GitHubie; alternatywne modele |

---

### Pierwsze uruchomienie i logowanie

1. **Logowanie pod koniec instalacji:** Instalator loguje cię do Claude (zaloguj się swoim kontem w przeglądarce i autoryzuj), oferuje logowanie do Gemini przez `agy` (Enter loguje, `s` pomija) oraz GitHub, jeśli zainstalowano `gh`.
2. **Włącz API w REW:**  
   *Uwaga: REW musi być w wersji beta (obecne wydanie V5.31.3 i wcześniejsze nie mają API).*  
   Przejdź do *Preferences → API*, zaznacz **Start the API when REW starts** i kliknij **Start server** (port `4735`). W systemie Windows uruchom REW ze skrótu **REW (API on)**.
3. **Rozpoczęcie pracy:** Utwórz pusty folder na swój samochód (np. `MyCarTuning`). Otwórz go w **Autosound TCC** (wybierz Claude Opus i Gemini Pro) lub w terminalu (`cd MyCarTuning`, a następnie `claude`) i wpisz na czacie: **„skonfigurujmy nowe auto od zera”** (lub po angielsku: *"tune a new car from scratch"*).

---

### Aktualizacja, blokowanie wersji i usuwanie

* **Aktualizacja skilla:** Możesz zaktualizować skilla bezpośrednio w TCC lub po prostu ponownie uruchomić polecenie instalacji w terminalu. Skrypt pobiera najnowszy tag `v3.*` (tagi `v3.0.*` są wersjami przedpremierowymi aż do 3.1.0; sprawdzona na zawodach stabilna linia to 2.8.x) i nie dotyka plików twojego projektu.
* **Aktualizacja TCC:** Przycisk aktualizacji wewnątrz aplikacji TCC podaje polecenie aktualizacji do uruchomienia w terminalu (działająca aplikacja nie może nadpisać własnego pliku wykonywalnego).
* **Opcje:** podaje się je po `bash -s --` na macOS oraz po formule `& ([scriptblock]::Create((irm …)))` w Windows (obie pokazane w [README](README.pl.md#jak-zainstalować-i-zacząć-wersja-3x--beta)): `--terminal` / `-Terminal` (bez aplikacji), `--github` / `-GitHub`, `--with-omp` / `-WithOmp`, `--no-reviewer` / `-NoReviewer`, `--dry-run` / `-DryRun`.
* **Blokowanie wersji:** `--skill-ref` oraz `--tcc-ref` (`-SkillRef` i `-TccRef` w Windows) przypinają metodę i aplikację do wersji wydanych razem — podawaj obie jako **parę** albo wcale; para mieszana nie jest przetestowana.
* **Deinstalacja:** Uruchom instalator z flagą `--uninstall` (`-Uninstall`); flaga `--all` usuwa dodatkowo uv, Claude Code i `~/.claude`, a także `agy`/`gh`/`omp`, jeśli zostały zainstalowane przez instalator — najpierw zapyta o zgodę. Foldery twoich projektów nigdy nie są usuwane.

---

## Aplikacja graficzna Autosound TCC

### Co to jest i czy jest mi potrzebne?

Aplikacja [TCC](https://github.com/ayukhno/autosound-tcc) pozwala pracować w oknie graficznym na macOS i Windows. Widzisz drzewo systemu, wykresy REW, plan krok po kroku i czat AI na jednym ekranie. Aplikacja jest opcjonalna — możesz nastroić samochód całkowicie przez terminal, ponieważ wszystkie dane projektu są zapisywane w standardowych plikach maszynowych na dysku.

📘 [TCC in eight screens (EN)](https://github.com/ayukhno/autosound-tcc/blob/main/docs/guide/QUICK-GUIDE.md) · [The TCC window, panel by panel (EN)](https://github.com/ayukhno/autosound-tcc/blob/main/docs/guide/REFERENCE.md) · [The house curve in TCC (EN)](https://github.com/ayukhno/autosound-tcc/blob/main/docs/guide/HOUSE-CURVE.md)

### Praca na dwa okna (Terminal + Grafika)

Aplikacja i terminal uzyskują dostęp do dokładnie tych samych plików projektu. Możesz prowadzić interaktywną sesję w terminalu, trzymając jednocześnie otwarte TCC obok jako wizualny monitor w czasie rzeczywistym: wyświetla ono drzewo głośników, nakładanie się krzywych i zmiany w rejestrze wersji na bieżąco.

### Modele AI w aplikacji

Aplikacja korzysta z twojej subskrypcji Claude (przez Anthropic SDK) oraz twojego konta Google przez `agy` dla recenzenta AI. Wybór modeli w TCC odzwierciedla zalecane kombinacje. Alternatywne modele przez `omp` są dodawane tylko wtedy, gdy o to poprosisz (`--with-omp`).

### Aktualizacje i zgłaszanie błędów

TCC sprawdza aktualizacje skilla i aplikacji. Błędy interfejsu użytkownika zgłaszaj w [repozytorium TCC na GitHubie](https://github.com/ayukhno/autosound-tcc/issues), a problemy z matematyką strojenia w [repozytorium skilla](https://github.com/ayukhno/autosound-tuning-skill/issues).

---

## Autonomiczny Krytyk AI Gemini/Antigravity

Podwójny cykl weryfikacji przez dwa AI (Generator ↔ Krytyk Gemini) wychwytuje błędy, które pojedynczy model popełnia i których sam nie widzi. Działa automatycznie w tle za pośrednictwem lokalnego skryptu — nie jest potrzebne żadne ręczne kopiowanie. To, co jest opcjonalne, to ten *automatyczny kanał*, a nie sama druga opinia: bez skonfigurowanego kanału wklejasz pakiet do czatu innego AI ręcznie. Całkowite pominięcie recenzji to największa pojedyncza strata jakości w tej metodzie.

### Instalacja dla macOS i Windows (Zalecana)

Oficjalne narzędzie **Antigravity CLI (`agy`)** nie wymaga klucza API — uwierzytelniasz się w przeglądarce za pomocą swojego konta Google.

1. **Instalacja:** Instalator konfiguruje to automatycznie. W celu instalacji ręcznej uruchom:
   * *macOS:* `curl -fsSL https://antigravity.google/cli/install.sh | bash`
   * *Windows:* `irm https://antigravity.google/cli/install.ps1 | iex`
2. **Logowanie:** Uruchom `agy` w nowym terminalu, zaloguj się w przeglądarce za pomocą konta Google, a następnie wróć do konsoli i wpisz `/quit`.
3. **Wybierz model recenzenta** — nie ma domyślnego. Wpisz identyfikator z `agy models` (lewa kolumna; poziom Pro `-high`) do pliku konfiguracyjnego recenzenta, `~/.config/autosound/critic-env` (`%APPDATA%\autosound\critic-env` w Windows), jako linijkę taką jak:
   ```env
   AUTOSOUND_CRITIC_MODEL=gemini-3.1-pro-high
   ```
   Aplikacja ustawia go z poziomu własnego selektora. Jeśli `agy` odpowie, że dany model nie jest obsługiwany w twojej lokalizacji, wybierz inny identyfikator z listy.
4. **Sprawdzenie:**
   ```bash
   python3 ~/.claude/skills/autosound-tuning/scripts/autosound_ai.py doctor
   ```
   Polecenie `doctor` podaje nazwę modelu, CLI i znaleziony klucz, wykonuje jedno krótkie wywołanie testowe na żywo i wyświetla rozwiązanie w razie jakichkolwiek problemów.

---

### Wariant rezerwowy: Bezpośredni klucz API Gemini

Jeśli `agy` nie jest dla ciebie dostępne lub wyczerpiesz jego limity, możesz użyć bezpośrednio darmowego klucza Gemini API. W przypadku obecności klucza recenzent wywołuje API **w pierwszej kolejności**, a `agy` tylko wtedy, gdy to wywołanie się nie powiedzie.

1. Pobierz darmowy klucz API na stronie **[aistudio.google.com/apikey](https://aistudio.google.com/apikey)** — obecne klucze zaczynają się od `AQ.`.
2. Zapisz go raz za pomocą dedykowanego polecenia recenzenta. Pyta ono o klucz bez wyświetlania go i przechowuje go w pęku kluczy macOS (w Windows w magazynie, który otwiera tylko twoje logowanie; gdzie indziej oraz gdy magazyn jest niedostępny — w pliku konfiguracyjnym recenzenta z uprawnieniami 600). Linijka klucza wpisana do `critic-env` ręcznie ma pierwszeństwo przed magazynem. Nigdy nie przechowuj go w folderze projektu, profilu powłoki ani zmiennej środowiskowej: każdy program może go tam odczytać, a aplikacja uruchomiona z Docka go nie widzi.
   ```bash
   python3 ~/.claude/skills/autosound-tuning/scripts/autosound_ai.py key set google
   # Windows: python3 "$HOME\.claude\skills\autosound-tuning\scripts\autosound_ai.py" key set google
   ```
   Klucz wyeksportowany już w `~/.zshrc` (lub w zmiennych środowiskowych użytkownika Windows) przenosi się za pomocą `… key move-shell`, które najpierw pyta o zgodę. Polecenie `… key status` pokazuje, gdzie znajduje się każdy klucz, nigdy nie wyświetlając samego klucza.
3. Wskaż model, który ten klucz może wywołać: polecenie `doctor` wyświetla własną listę dla klucza (na przykład `gemini-pro-latest`). Jego identyfikatory różnią się od tych w `agy`.

Lokalny dla projektu plik `.critic-env`, który zawiera klucz i który mógłby zostać przechwycony przez git, jest odrzucany. Polecenie `doctor` nigdy nie wyświetla klucza, a jedynie jego format (`current` / `OLD`) oraz skąd pochodzi.

> [!TIP]
> Jeśli żaden kanał nie odpowiada, recenzent zgłasza odmowę (kod wyjścia 4): wymienia powody, zapisuje pakiet w folderze `process/reviews/` projektu i kopiuje go do schowka — wklej go do czatu dowolnego AI.

---

### Czy można pracować tylko w Gemini, bez Claude?

Tak, ale jako proces ręczny, a nie automatyczny potok. Wprowadź prompt w swojej sesji Gemini:

> Clone `https://github.com/ayukhno/autosound-tuning-skill`, read `skills/autosound-tuning/SKILL.md`, and follow that method as your operating instructions for this session.

Ponieważ w standardowym czacie internetowym nie ma mechanizmu ruchomego okna, precyzja może spadać podczas długich sesji. Wspieraną opcją bezkosztową jest **Wariant 4** ([gałąź manual_step-by-step](https://github.com/ayukhno/autosound-tuning-skill/tree/manual_step-by-step)).

---

## Przeprowadzanie pomiarów

### Pomiar fazy: Mikrofony XLR kontra USB (UMIK-1/2)

* **Mikrofony XLR (Behringer ECM8000, Beyerdynamic MM1 itp.):** Podłączane przez zewnętrzną kartę dźwiękową z **fizyczną pętlą zwrotną (hardware loopback)** (wyjście połączone kablem bezpośrednio z wolnym wejściem). Daje to stabilne sprzętowo odniesienie czasu nadejścia z dokładnością do jednej próbki (jedna próbka ≈ 10 µs przy 96 kHz).
* **Mikrofony USB (UMIK-1 / UMIK-2):** Podłączane bezpośrednio przez USB. Mają niezależny zegar cyfrowy od interfejsu audio i nie posiadają fizycznego loopbacku, co wymaga akustycznego odniesienia czasu.
* **Połączenie audio:** Użyj fizycznego przewodu (AUX 3,5 mm, bezpośrednie audio USB lub kabel optyczny). **Unikaj Bluetooth do sweepów:** połączenia bezprzewodowe wprowadzają jitter pakietów i zmienną latencję, co pogarsza dokładność akustycznego odniesienia czasu.

---

### Czy można zmierzyć fazę na UMIK-1?

**Tak.** Użyj **Acoustic Timing Reference** w REW. Przed odtworzeniem sweepu pomiarowego REW odtwarza krótki sygnał o wysokiej częstotliwości („chirp”) przez wyjście wybrane przez ciebie jako odniesienie czasu, a ten chirp stanowi punkt zerowy dla mierzonego kanału.

Szczegółową konfigurację REW dla mikrofonów USB znajdziesz w poradniku wideo: [Measuring Speaker Phase in REW](https://www.youtube.com/watch?v=El-kwZ5_nnU).

> [!WARNING]
> **Wykonuj pomiary z mikrofonem na statywie i powtórz sweep kontrolny na końcu!**
> * **Dryft temperatury powietrza w kabinie:** Prędkość dźwięku zmienia się wraz z temperaturą w kabinie. Zmiana o kilka stopni przesuwa czasy przybycia o dziesiątki mikrosekund.
> * **Dryft kumuluje się z każdym sweepem:** jeden głośnik mierzony 6 razy z rzędu w ciągu 18 minut przesunął się o jedną próbkę (10 µs, czyli tyle samo, co przesunięcie mikrofonu o ~3,6 mm) — od samego wykonywania sweepów, a nie tylko od upływu czasu.
> * **Ustawienie statywu:** Umieść mikrofon na wysokości uszu dla **miejsca odniesienia** (reference seat) zdefiniowanego w projekcie, z odniesieniem do fizycznych znaczników, i nie poruszaj nim, dopóki blok nie zostanie ukończony.
> * **Sweep kontrolny:** Zmierzenie kanału otwierającego (`ctl1`) i powtórzenie go na końcu (`ctl3`) pozwala sprawdzianowi nazwać jakikolwiek dryft czasowy przed zamknięciem rundy; decyzja o ewentualnym powtórzeniu pomiaru należy do ciebie.

---

### Zasady nazewnictwa pomiarów w REW

Narzędzia obliczeniowe szukają pomiarów ściśle według ich nazw w REW:

* `m-L_1 (sw)` — kanał `m-L` (lewy średniotonowy), seria pomiarowa `1`, pomiar sweep. Stan DSP może mieć kilka serii; ten numer nie jest również numerem wersji rejestru.
* `m-L_1 (rta)` — pomiar RTA mikrofonem w ruchu dla tego samego głośnika.
* `tw-L_1 (sw)`, `w-R_1 (sw)`, `sw_1 (sw)` — lewy tweeter, prawy woofer (midbas), subwoofer.
* `L_1 (rta)`, `ALL_1 (rta)` — sumaryczny pomiar RTA całej lewej strony lub całego systemu.
* `m-L p5_1 (sw)` — głośnik w przestrzennym punkcie kontrolnym `p5` (odczytywane także jako `m-L_1 (sw) p5`).
* `m-L-ctl1_1 (sw)` i `m-L-ctl3_1 (sw)` — kontrola czasu: pierwszy otwiera serię pomiarów głośnika, drugi ją zamyka; nie ma `ctl2` (wpisywane w aucie jako `m-L_1ctl` i `m-L_1rep`, oznaczają to samo).
* `m-L_final (sw)` — pomiar weryfikacyjny po zapisaniu ostatecznych parametrów.
* `w-L (imp)` — pomiar impedancji przetwornika; nie jest powiązany ze stanem DSP i nie posiada numeru serii.
* Tekst po oznaczeniu metody sprawia, że jest to **inny pomiar tej samej serii**: `r-L_17 (sw) noXO` to nie to samo co `r-L_17 (sw)`.

Tytuły są dopasowywane dokładnie tak, jak zostały wpisane. Tytuł, który nie pasuje do tego, czego oczekuje dany krok, to pytanie, które AI zadaje tobie — nigdy zgadywanie.

Pełny przebieg pomiarów został opisany w [`references/phases/capture-session-sheet.md`](skills/autosound-tuning/references/phases/capture-session-sheet.md).

---

### Sesja pomiarowa (Capture): dlaczego tylko filtry ochronne?

> [!IMPORTANT]
> **REW musi pozostać otwarty przez cały proces:** skill odczytuje krzywe bezpośrednio z aktywnego okna REW przez API, a nie z plików wyeksportowanych na dysk.
>
> **Filtry ochronne POZOSTAJĄ WŁĄCZONE podczas pomiarów:** Filtry górnoprzepustowe (HPF) na delikatnych tweeterach i głośnikach średniotonowych muszą pozostać aktywne w DSP, aby chronić je podczas sweepów pomiarowych.

* **Zasada filtra ochronnego:** Ochronny HPF musi wynosić **$\ge 1.1 \times Fs$ (zalecane do $1.5 \times Fs$), ze spadkiem $\ge 24$ dB/okt.** (LR4 lub BW4). Jeśli $Fs$ nie jest znane, sprawdź wartość w karcie katalogowej producenta i podaj ją w projekcie.
* **Filtry robocze wyłączone:** Robocze EQ (puste), opóźnienia (ustawione na 0) i polaryzacje (normalne) muszą być czyste. Zapisz każdy filtr ochronny w rundzie zdjęcia danych (aplikacja o to pyta; w terminalu rejestruje to sesja): narzędzia następnie odejmą go z tego pomiaru solo przed odczytem fazy wypadkowej na styku. Kanał zarejestrowany jako `OFF` jest odczytywany w postaci, w jakiej się znajduje.
* **Poziomy w dBFS:** Ustaw głośność sweepu tak, aby szczyt najgłośniejszego przetwornika (subwoofera) wynosił $-5\dots-10$ dBFS, a najcichszy przetwornik znajdował się znacznie powyżej poziomu szumów tła w kabinie. Sprawdź poziom szumów przy wyłączonym i włączonym silniku. Wycisz (Mute) wszystkie nieaktywne kanały w oprogramowaniu DSP i zachowaj niezmienioną głośność karty dźwiękowej oraz jednostki głównej (radia) przez całą sesję.
* **Dźwięk sweepu midbasu:** Midbas mierzony bez filtra LPF wyda szorstki, chrapliwy dźwięk na wysokich częstotliwościach podczas sweepu. Jest to normalny **breakup membrany** (cone breakup) na górnym skraju jego pasma; przetwornik nie jest uszkodzony.

---

### Po co są pozycje p1…p9 i kontrola czasu ctl?

* **Odróżnianie rezonansów głośnika i montażu od odbić w kabinie:** Rezonanse pozostają stabilne przy niewielkim przesunięciu pozycji mikrofonu (bezpieczne do korygowania EQ). Zera wynikające z odbić w kabinie gwałtownie zmieniają częstotliwość — podbijanie ich jest bezcelowe.
* **Obliczanie limitów dobroci Q korektora:** Wariancja przestrzenna w punktach `p1…p9` wyznacza bezpieczne granice dobroci Q filtrów korektora.
* **Monitorowanie dryftu czasowego:** Otwierający i zamykający sweep `ctl` wykrywają dryft zegara lub temperatury podczas sesji.

---

## Krzywe docelowe (Target Curves)

### Jak stworzyć i skonfigurować własną krzywą docelową?

Krzywa docelowa to wstępna hipoteza tonalna, którą dopracowujesz na ucho po ustaleniu bazowego strojenia technicznego.

1. **Wybierz spośród uznanych krzywych:** Wybierz spośród skalibrowanych celów — SQ-Comp-Ref (własna krzywa metody), ResoNix, Audiofrog, Harman, Jazzi i Whitledge — w zależności od tego, co lubisz słyszeć. Skrypt `target_bands.py` oblicza indywidualne kształty docelowe dla każdego przetwornika na podstawie wybranej krzywej i punktów podziału zwrotnicy.
2. **Narysuj ręcznie:** Skorzystaj z bezpłatnego narzędzia [Nono Tuning Tool](https://nonotuningtool.com) (sekcja *Custom Target Curve*), aby ukształtować charakterystykę i wyeksportować plik docelowy `.txt`.
3. **Porównaj online:** Wypróbuj nasz interaktywny wizualizator:  
   👉 **[Otwórz wizualizator krzywych docelowych online](https://ayukhno.github.io/autosound-tuning-skill/_curve-visualizer.html?lang=pl)**. Kliknięcie prawym przyciskiem myszy na dowolny punkt wykresu wyjaśnia, jak dany zakres częstotliwości wpływa na dźwięk.

📘 [The house curve in TCC (EN)](https://github.com/ayukhno/autosound-tcc/blob/main/docs/guide/HOUSE-CURVE.md)

---

## Projekt na dysku i DSP

### Struktura folderu projektu i kopia zapasowa

Katalog twojego projektu przechowuje pełną konfigurację oraz historię strojenia twojego pojazdu:

| Plik / Folder | Zawartość | Przeznaczenie |
| :--- | :--- | :--- |
| **`project.json`** | Konfiguracja systemu | Kanały głośników, wyjścia DSP, profil, specyfikacja mikrofonu, krzywa docelowa. |
| **`state/versions/` + `slots.json`** | Rejestr wersji | Chronologiczna historia zwrotnic, opóźnień, poziomów i EQ. |
| **`process/process-state.json`** | Status procesu | Śledzenie aktywnej fazy i logi weryfikacji. |
| **`autosound_context.md`** | Kontekst pojazdu | Słownik auta, układ instalacji, notatki o kabinie. |
| **`*.txt` / `*.json`** | Krzywe i eksporty DSP | Krzywe docelowe i wygenerowane pliki parametrów EQ. |

> [!IMPORTANT]
> **Zachowaj lokalne kopie `.mdat`:** Metoda wymaga zachowania lokalnej kopii plików `.mdat` z REW w momencie odbioru technicznego i zakończenia sesji. Duże pliki `.mdat` (po 16–112 MB każdy) pozostają poza gitem; twoje lokalne kopie muszą być zawsze zachowane. W celu bezpłatnego, prywatnego backupu folderu projektu na GitHubie zainstaluj z flagą `--github` (`-GitHub` w Windows) i poproś AI o utworzenie kopii zapasowej projektu: zaoferuje repozytorium, niczego nie utworzy bez twojej zgody i wie, co powinno pozostać poza kopią.

---

### Kompatybilność z procesorami i import filtrów do DSP

> ⚠️ **Ważne:**  
> Metoda oblicza filtry. Opóźnienia i wzmocnienia są zawsze wprowadzane **ręcznie** przez stroiciela, podobnie jak zwrotnice, chyba że narzędzie do wklejania pobierze je z poniższego eksportu Extended. Import pliku przenosi wyłącznie **EQ**.

* **Audiotec Fischer (Helix / MATCH / BRAX):** Generuje gotowy do zaimportowania plik Full EQ, który DSP PC-Tool wczytuje dla wszystkich kanałów w jednym kroku.
* **Inne procesory DSP:** Eksportuje pliki REW Generic EQ (20 slotów) lub Generic/Extended ze zwrotnicami w treści pliku. Do szybkiego wprowadzania parametrów do innego oprogramowania DSP za pomocą makr klawiatury użyj darmowego narzędzia [REW-EQ-CopyPaste-Assistant](https://github.com/IvanBakhmutov/REW-EQ-CopyPaste-Assistant).
* **Kontrola kompatybilności:** Przed eksportem skrypty porównują każdy obliczony filtr z ograniczeniami twojego modelu DSP (dostępne pasma, częstotliwość próbkowania, typy filtrów) i sygnalizują wszelkie odchylenia.
* **Fabryczne jednostki główne (OEM):** Zalecaną praktyką jest **ominięcie** (bypass) fabrycznych jednostek głównych przy użyciu czystego, bezpośredniego wejścia cyfrowego lub analogowego (DAP, USB, optyk) do DSP, zamiast prób de-equalizacji fabrycznych korekcji barwy i przetwarzania loudness.

---

### Praca ze zwrotnicami pasywnymi (tweeter + średniotonowy na jednym kanale)

Para przetworników podłączona przez zwrotnicę pasywną jest traktowana jako **jeden wspólny kanał DSP**: otrzymuje jeden pomiar, wspólne opóźnienie, wspólne wzmocnienie i jeden zestaw filtrów EQ.

Wszystko inne działa jak zwykle, a łączna odpowiedź jest poprawna fizycznie — włączając w to wszelkie problemy fazowe na połączeniu pasywnym (styku). Czego żadne oprogramowanie nie jest w stanie zrobić z zewnątrz, to wyrównać czasu lub fazy między tweeterem a głośnikiem średniotonowym **wewnątrz** tej grupy pasywnej: do tego każdy przetwornik potrzebuje własnego kanału DSP.

---

### Gdzie znaleźć pełną listę możliwości metody?

Szczegółowy przegląd każdego narzędzia i polecenia znajduje się w tablicy możliwości (Capabilities board):
[`references/core/capabilities.md`](skills/autosound-tuning/references/core/capabilities.md).  
Filtruj polecenia za pomocą: `python3 ~/.claude/skills/autosound-tuning/rew_tool/capabilities.py find "phase"`.
