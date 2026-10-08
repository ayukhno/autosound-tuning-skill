# FAQ — Często zadawane pytania dotyczące strojenia systemów car audio

🇬🇧 [English](FAQ.md) · 🇩🇪 [Deutsch](FAQ.de.md) · 🇵🇱 **Polski** · 🇺🇦 [Українська](FAQ.uk.md) · 📘 [TCC full guide (EN)](https://github.com/ayukhno/autosound-tcc/blob/main/docs/guide/REFERENCE.md) · <img src="assets/icons/roadmap.svg" width="14" height="14" valign="middle" alt="Roadmap" /> [Roadmap (EN)](ROADMAP.md)

Prawdziwe pytania na drodze od instalacji do nastrojonego auta. [README](README.pl.md) to wersja skrócona; [Advanced Setup](ADVANCED.md) opisuje terminal, inne sposoby instalacji, wersje oraz ręczną konfigurację recenzenta.

---

## Spis treści

- [Pojęcia używane w tekście](#pojęcia-używane-w-tekście)
- [Pierwsze kroki](#pierwsze-kroki)
  - [Zanim zaczniesz](#zanim-zaczniesz)
  - [Jak najlepiej zacząć?](#jak-najlepiej-zacząć)
  - [Automatyczna instalacja](#automatyczna-instalacja)
  - [Od instalacji do auta](#od-instalacji-do-auta)
  - [Aktualizacja](#aktualizacja)
- [Bezpieczeństwo i modele AI](#bezpieczeństwo-i-modele-ai)
  - [Czego metoda kategorycznie odmawia?](#czego-metoda-kategorycznie-odmawia)
  - [Które modele AI są oficjalnie wspierane?](#które-modele-ai-są-oficjalnie-wspierane)
- [Graficzna aplikacja desktopowa Autosound TCC](#graficzna-aplikacja-desktopowa-autosound-tcc)
  - [Czym jest i czy jej potrzebuję?](#czym-jest-i-czy-jej-potrzebuję)
  - [Control mode: sesja w terminalu](#control-mode-sesja-w-terminalu)
  - [Aktualizacje i zgłaszanie błędów](#aktualizacje-i-zgłaszanie-błędów)
- [Recenzent AI](#recenzent-ai)
  - [Jeśli recenzent nie odpowiada](#jeśli-recenzent-nie-odpowiada)
- [Wykonywanie pomiarów](#wykonywanie-pomiarów)
  - [Pomiar fazy: mikrofony XLR vs. USB (UMIK-1/2)](#pomiar-fazy-mikrofony-xlr-vs-usb-umik-12)
  - [Czy mogę mierzyć fazę za pomocą UMIK-1?](#czy-mogę-mierzyć-fazę-za-pomocą-umik-1)
  - [Zasady nazewnictwa pomiarów w REW](#zasady-nazewnictwa-pomiarów-w-rew)
  - [Sesja pomiarowa: dlaczego tylko filtry ochronne?](#sesja-pomiarowa-dlaczego-tylko-filtry-ochronne)
- [Krzywe docelowe](#krzywe-docelowe)
  - [Jak stworzyć i skonfigurować własną krzywą docelową?](#jak-stworzyć-i-skonfigurować-własną-krzywą-docelową)
- [Projekt na dysku i DSP](#projekt-na-dysku-i-dsp)
  - [Kompatybilność z procesorami i import filtrów do DSP](#kompatybilność-z-procesorami-i-import-filtrów-do-dsp)
  - [Praca ze zwrotnicami pasywnymi (tweeter + midrange na jednym kanale)](#praca-ze-zwrotnicami-pasywnymi-tweeter--midrange-na-jednym-kanale)
  - [Kopia zapasowa](#kopia-zapasowa)

---

## Pojęcia używane w tekście

- **Metoda (skill):** instrukcje strojenia i narzędzia, którymi kieruje się Claude. Działa wewnątrz **Claude Code** — programu Claude na twoim komputerze, a nie na czacie w przeglądarce.
- **Sesja:** pojedyncza rozmowa z Claude o twoim aucie, w oknie czatu TCC lub w terminalu.
- **TCC:** aplikacja desktopowa (Autosound TCC), która wyświetla twój projekt i prowadzi sesję za ciebie.
- **Recenzent:** drugie AI (Gemini), które weryfikuje każdą propozycję, zanim ją zobaczysz. **Pakiet:** paczka tekstowa z propozycją, która trafia do recenzenta.
- **API (w REW):** połączenie, przez które metoda odczytuje twoje pomiary z REW. Musi być włączone w REW.
- **Sweep:** sygnał testowy REW, odtwarzany przez jeden głośnik. **RTA (MMM):** pomiar wykonywany podczas powolnego poruszania mikrofonem wokół głowy.
- **Przetwornik (driver):** pojedynczy głośnik. **Fs:** częstotliwość rezonansowa przetwornika z jego karty katalogowej.
- **HPF / LPF:** filtr górnoprzepustowy / dolnoprzepustowy — filtry w DSP odcinające od głośnika odpowiednio niskie lub wysokie częstotliwości.
- **dBFS:** wskaźnik poziomu w REW; 0 dBFS to maksimum skali.

---

## Pierwsze kroki

### Zanim zaczniesz

- **Laptop** — zabierasz go do auta na czas pomiarów.
- **Mikrofon pomiarowy:** **UMIK-1 wystarczy** (mikrofon XLR z interfejsem audio jest bardziej precyzyjny). Pobierz jego plik kalibracyjny na podstawie numeru seryjnego ze strony producenta i wczytaj go do REW.
- **Przewód z laptopa do DSP** — AUX 3,5 mm, USB audio lub optyczny. Nie Bluetooth: jego opóźnienie zmienia się między kolejnymi sweepami.
- **DSP** w twoim samochodzie.
- **REW beta**, zainstalowane **przed** instalatorem (na Windowsie instalator doda wtedy skrót **REW (API on)** na twoim Pulpicie). Pobierz je ze strony [roomeqwizard.com/beta.html](https://www.roomeqwizard.com/beta.html); wersja stabilna (release) nie ma API.
- **Płatna subskrypcja Claude (Pro lub Max)** na [claude.ai](https://claude.ai) — instalator zaloguje cię za jej pomocą.
- **Konto Google** — dla recenzenta Gemini; logujesz się jednorazowo w przeglądarce.
- **Fs twoich głośników** z ich kart katalogowych — do filtrów ochronnych. Brak karty katalogowej (głośniki fabryczne)? Powiedz o tym AI; metoda potrafi to również zmierzyć.

<a id="four-paths-of-usage"></a>

### Jak najlepiej zacząć?

- 🖥️ **Opcja 1 · Wersja 3.x w oknie graficznym (Autosound TCC) — [Zalecana]**  
  Najbardziej zautomatyzowana i wizualna ścieżka. Instalator konfiguruje Claude Code, metodę wraz z jej bibliotekami w Pythonie, aplikację desktopową TCC oraz recenzenta Gemini (agy).
  - **Wymagania:** macOS lub Windows, Claude Pro/Max, REW beta z włączonym API; TCC dodaje około 700 MB do pobieranych plików.
  - **Zalety:** Widzisz strukturę systemu, krzywe pomiarowe, plan krok po kroku oraz okno czatu w jednym interfejsie. Stan jest zapisywany automatycznie na dysku, a działania są rejestrowane w historii wersji.
  - **Wady:** TCC jest młodsze niż sama metoda.

Inne sposoby — wersja 3 wyłącznie w terminalu lub jako wtyczka do Claude Code, pozostanie przy starszej linii 2.x albo czat w przeglądarce — opisano w [Advanced Setup](ADVANCED.md#other-ways-to-use-the-method).

> [!NOTE]
> Nie jesteś uwiązany do jednego wyboru: projekty z linii 3.x otwierają się bez problemu zarówno w sesji terminalowej, jak i w TCC.

### Automatyczna instalacja
Będziesz potrzebować laptopa, mikrofonu pomiarowego, procesora DSP w aucie oraz konta **Claude Pro lub Max**.

<details>
<summary><b>Instrukcja dla macOS</b></summary>

- Otwórz **Terminal** (naciśnij `Cmd + Space` → wpisz `Terminal` → naciśnij `Enter`).
- Wklej poniższe polecenie i naciśnij `Enter`:
   ```bash
   curl -fsSL https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/v3.1.2/install.sh | bash
   ```
- W zależności od systemu inne instalatory mogą poprosić o uprawnienia; to normalne. Poczekaj 10–20 minut.

</details>

<details>
<summary><b>Instrukcja dla Windows</b></summary>

- Otwórz **Windows PowerShell** (naciśnij Start → wpisz `powershell` → naciśnij `Enter`).
- Wklej poniższe polecenie i naciśnij `Enter`:
   ```powershell
   irm https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/v3.1.2/install.ps1 | iex
   ```
- W zależności od systemu inne instalatory mogą poprosić o uprawnienia; to normalne. Skrypt utworzy skrót **REW (API on)** na twoim Pulpicie.

</details>

### Od instalacji do auta

1. **Zaloguj się.** Ostatni krok instalatora dwukrotnie otwiera przeglądarkę: najpierw logowanie do Claude, potem do Google dla recenzenta (oraz GitHub, jeśli wybrano tę opcję). Pominąłeś któryś krok? Uruchom instalator ponownie — zaproponuje logowanie jeszcze raz.
2. **Uruchom REW** z włączonym API: na Windowsie ze skrótu **REW (API on)**; na macOS w REW w *Preferences → API* zaznacz **Start the API when REW starts** i kliknij **Start server** (jednorazowo).
3. **Otwórz TCC**, utwórz pusty folder dla swojego auta (np. `MyCarTuning`) i go wybierz.
4. **Wybierz modele** na dole okna TCC: **AI main** — Claude Opus, **Effort** — x-high (domyślny), **AI critic** — Gemini Pro (High) lub Gemini Flash (High), jeśli Pro nie jest ci oferowany. Do późniejszego dostrajania w aucie przełącz tam **AI main** na model o najwyższych możliwościach (obecnie Claude Fable).
5. **Wpisz** na czacie TCC: **"tune a new car from scratch"**. AI zapyta o twój system i twoje cele, a następnie zaplanuje pomiary.
6. **W aucie** TCC wskaże każdy pomiar z nazwy w sekcji *In focus now*. Wykonaj go w REW pod dokładnie tą nazwą, a następnie kliknij **⬇**, aby go wczytać. Gdy wszystkie będą gotowe, kliknij **Done**.
7. **Przy biurku** AI zaprojektuje strojenie; **z powrotem w aucie** wprowadzasz wartości do DSP, sprawdzasz je i dostrajasz brzmienie na ucho.

### Aktualizacja

Zaktualizuj z poziomu TCC lub uruchom ponownie polecenie instalacyjne: instaluje ono najnowsze wydanie, sprawdza jego podpis cyfrowy i nie modyfikuje twoich folderów z projektami. Przycisk aktualizacji w samym TCC wyświetla polecenie do uruchomienia (TCC nie może podmienić samego siebie podczas działania). Więcej opcji: [Advanced Setup](ADVANCED.md#the-installer).

---

## Bezpieczeństwo i modele AI

### Czego metoda kategorycznie odmawia?
- **Bezpośredniego wpisywania parametrów do twojego DSP** — wprowadzanie wartości do oprogramowania procesora zawsze pozostaje twoim działaniem.
- **Obliczania opóźnień na podstawie narzędzi auto-delay lub korelacji wzajemnej (cross-correlation)** — opóźnienia akustyczne są analizowane ręcznie na podstawie początkowego narastania odpowiedzi impulsowej ($t_0$). Narzędzia automatycznego szacowania opóźnień w REW są surowo zabronione.
- **Podbijania częstotliwości w zerach akustycznych (strefach znoszenia / cancellation zones)** — zapadłości wynikające ze znoszenia fal są powodowane odbiciami od przegród i powierzchni, a nie samym głośnikiem. Wypełnianie ich za pomocą EQ jest bezcelowe: podbicie obciąża jedynie wzmacniacz i głośnik, nie zmieniając niczego w miejscu odsłuchu. Metoda ogranicza jakiekolwiek podbicie do maksymalnie +6 dB, a zapadłość wymagająca więcej to niemal na pewno znoszenie fal. Zapadłości bezpieczne do korekcji są identyfikowane za pomocą analizy *Excess phase* w REW.
- **Kontynuowania pracy z wątpliwymi pomiarami** — wykryty dryf czasowy (timing drift) lub brak filtrów ochronnych zostaną zasygnalizowane przed przejściem dalej.

---

### Które modele AI są oficjalnie wspierane?
- 🧠 **Główny model (Generator):** **Claude Opus** (skonfigurowany z poziomem Effort `xhigh` lub wyższym; `max` dla trudnych kroków). Precyzyjne dostrajanie w aucie najlepiej wykonać z modelem o najwyższych możliwościach (obecnie Claude Fable). Inne AI również mogą prowadzić proces poprzez `omp` (instalowane wyłącznie na życzenie, z flagą `--with-omp`) — na własne ryzyko.
- 👁️ **Recenzent AI (Krytyk):** **Gemini Pro (High)** poprzez Google Antigravity (`agy`) lub **Gemini Flash (High)** tam, gdzie Pro (High) nie jest oferowany. Przy logowaniu przez Google Cloud (ADC, bezpłatny okres próbny) modelem recenzenta jest **Gemini 3.8 Flash (High)** (`gemini-3.8-flash-high`).
- 🛠️ **Inni recenzenci:** selektor w TCC oferuje również model Codex (oraz, z flagą `--with-omp`, inne modele) w roli recenzenta.
- 🧪 **Przetestowane przez autora:** Gemini poprzez Antigravity (`agy`) jako główne AI w terminalu, z modelem Codex jako recenzentem i TCC w trybie [Control mode](#control-mode-sesja-w-terminalu).

*Stan na wrzesień 2026 r.* Modele zmieniają się szybko, więc traktuj podane tu nazwy jako przykłady: TCC oraz metoda pobierają aktualną listę od każdego dostawcy i oferują to, co jest dostępne w danej chwili. Jeśli model wymieniony tutaj zostanie odrzucony, wybierz inny z tej listy.

> [!IMPORTANT]
> **Utrzymuj poziom Effort modelu Claude na poziomie `xhigh` lub wyższym (`max` dla trudnych kroków).**  
> Autor przeprowadził precyzyjne dostrajanie w aucie na modelu Claude Fable 5.

---

## Graficzna aplikacja desktopowa Autosound TCC

### Czym jest i czy jej potrzebuję?
[TCC](https://github.com/ayukhno/autosound-tcc) pozwala pracować w oknie graficznym na macOS i Windows. Widzisz drzewo głośników, wykresy z REW, plan krok po kroku oraz czat na jednym ekranie. TCC jest opcjonalne — możesz nastroić auto całkowicie w sesji, ponieważ wszystkie dane projektu są zapisywane w standardowych plikach na dysku.

📘 [TCC w ośmiu ekranach (EN)](https://github.com/ayukhno/autosound-tcc/blob/main/docs/guide/QUICK-GUIDE.md) · [Okno TCC, panel po panelu (EN)](https://github.com/ayukhno/autosound-tcc/blob/main/docs/guide/REFERENCE.md) · [Krzywa house curve w TCC (EN)](https://github.com/ayukhno/autosound-tcc/blob/main/docs/guide/HOUSE-CURVE.md)

### Control mode: sesja w terminalu

Dla sesji działającej w terminalu — z Claude Code lub z innym AI, takim jak Gemini poprzez `agy`. Tryb **Control mode** (w nagłówku TCC) przesuwa TCC na prawą połowę ekranu, a resztę pozostawia dla terminala: piszesz w terminalu, a TCC pokazuje to, co wypisuje sesja (*Monitoring*), tabele oraz twoje panele. Przyciski **Done** i **Listening** docierają do sesji jako sygnały; **Active TCC** przywraca pełne okno.

📘 [Control mode w przewodniku po TCC (EN)](https://github.com/ayukhno/autosound-tcc/blob/main/docs/guide/REFERENCE.md#control-mode)

### Aktualizacje i zgłaszanie błędów
TCC sprawdza dostępność aktualizacji skilla oraz samego TCC.

Aby zgłaszać problemy:
- Na GitHubie: błędy interfejsu zgłaszaj w [repozytorium TCC na GitHubie](https://github.com/ayukhno/autosound-tcc/issues), a kwestie strojenia w [repozytorium skilla](https://github.com/ayukhno/autosound-tuning-skill/issues).
- Bez konta na GitHubie: poproś o to sesję ("report a bug") lub skorzystaj z okna zgłoszeń w TCC; raporty trafiają do autora poprzez Google Form.

---

## Recenzent AI

Cykl recenzji z udziałem dwóch modeli AI (Generator ↔ Gemini Critic) wyłapuje błędy, które pojedynczy model mógłby przeoczyć. Działa automatycznie w tle za pośrednictwem lokalnego skryptu — nie jest wymagane żadne ręczne kopiowanie.

Kanał automatyczny jest opcjonalny, ale sama recenzja nie: bez skonfigurowanego kanału wklejasz pakiet recenzji do czatu innego AI ręcznie. Całkowite pominięcie recenzji to największa pojedyncza strata jakości w całej metodzie.

### Jeśli recenzent nie odpowiada

> [!TIP]
> Jeśli żaden kanał nie odpowiada, recenzent zgłasza odmowę (kod wyjścia 4): wypisuje powód, zapisuje pakiet w `process/reviews/` w projekcie i kopiuje go do schowka — wklej go do czatu dowolnego AI. Następnie wklej odpowiedź recenzenta z powrotem do czatu sesji.

Ręczna konfiguracja recenzenta — model, ADC w Google Cloud, klucz API: [Advanced Setup](ADVANCED.md#the-reviewer-by-hand).

---

## Wykonywanie pomiarów

### Pomiar fazy: mikrofony XLR vs. USB (UMIK-1/2)
- **Mikrofony XLR (Behringer ECM8000, Beyerdynamic MM1 itp.):** Podłączane przez zewnętrzny interfejs audio ze sprzętowym kablem loopback (wyjście wpięte bezpośrednio z powrotem do wolnego wejścia). Zapewnia to dokładny sprzętowy punkt odniesienia czasu.
- **Mikrofony USB (UMIK-1 / UMIK-2):** Podłączane bezpośrednio przez USB. Nie mają fizycznego loopbacka i wymagają akustycznego punktu odniesienia czasu (acoustic timing reference).
- **Połączenie audio:** Użyj fizycznego przewodu (AUX 3,5 mm, bezpośrednie audio USB lub optyk). Unikaj Bluetooth do sweepów: opóźnienie bezprzewodowe zmienia się między sweepami i pogarsza dokładność czasową.

---

### Czy mogę mierzyć fazę za pomocą UMIK-1?
**Tak.** Użyj opcji **Acoustic Timing Reference** w REW. Przed odtworzeniem sweepa pomiarowego REW odtwarza krótki ćwierk (chirp) przez głośnik wybrany jako referencja czasowa, aby ustalić punkt zerowy na osi czasu.

> [!WARNING]
> **Wykonuj pomiary z mikrofonem na statywie i powtórz sweep kontrolny na końcu!**
> - **Dryf temperatury powietrza w kabinie:** Prędkość dźwięku zmienia się wraz z temperaturą w kabinie, co wpływa na czas dotarcia fali.
> - **Ustawienie statywu:** Umieść mikrofon na wysokości uszu dla miejsca referencyjnego. Nie ruszaj statywu, dopóki cała seria sweepów nie zostanie ukończona (~25 minut).
> - **Sweep kontrolny:** Pomiar kanału otwierającego (`ctl1`) i powtórzenie go na końcu (`ctl3`) pozwala sprawdzić dryf czasowy przed zamknięciem rundy pomiarowej.

Szczegółową konfigurację REW dla mikrofonów USB przedstawiono w wideoporadniku: [Measuring Speaker Phase in REW](https://www.youtube.com/watch?v=El-kwZ5_nnU).

---

### Zasady nazewnictwa pomiarów w REW

W TCC każdy pomiar wymagany przez dany krok jest wymieniony z nazwy w sekcji *In focus now*: wykonaj go w REW pod dokładnie taką nazwą, a następnie kliknij **⬇**. Pracując w terminalu, nazywasz je samodzielnie. W obu przypadkach skill wyszukuje pomiary ściśle według ich nazw w REW:

- `m-L_1 (sw)` — kanał `m-L` (lewy średniotonowy), seria pomiarowa `1`, pomiar sweepem.
- `m-L_1 (rta)` — pomiar RTA metodą poruszanego mikrofonu (moving-mic) dla tego samego głośnika.
- `tw-L_1 (sw)`, `w-R_1 (sw)`, `sw_1 (sw)` — lewy tweeter, prawy woofer (midbass), subwoofer.
- `L_1 (rta)`, `ALL_1 (rta)` — sumaryczny pomiar RTA całej lewej strony lub całego systemu.
- `m-L p5_1 (sw)` — głośnik w przestrzennym punkcie kontrolnym `p5` (odczytywane także jako `m-L_1 (sw) p5`).
- `m-L-ctl1_1 (sw)` oraz `m-L-ctl3_1 (sw)` — kontrola czasu: pierwszy otwiera serię pomiarów głośnika, drugi ją zamyka; nie ma `ctl2` (wpisywane w aucie jako `m-L_1ctl` i `m-L_1rep`, oznaczają to samo).
- `m-L_final (sw)` — pomiar weryfikacyjny po zapisaniu ostatecznych parametrów.
- `w-L (imp)` — pomiar impedancji przetwornika (nie zawiera numeru serii).
- Tekst po oznaczeniu metody tworzy kolejny pomiar z tej samej serii: `r-L_17 (sw) noXO` to nie to samo co `r-L_17 (sw)`.

Tytuły są dopasowywane dokładnie według wpisanej nazwy. Jeśli tytuł nie odpowiada temu, czego oczekuje dany krok, sesja zapyta cię o to, zamiast zgadywać.

Kompletny przebieg sesji pomiarowej opisano w [`references/phases/capture-session-sheet.md`](skills/autosound-tuning/references/phases/capture-session-sheet.md).

---

### Sesja pomiarowa: dlaczego tylko filtry ochronne?
> [!IMPORTANT]
> **REW musi pozostać otwarte przez cały proces:** skill odczytuje krzywe bezpośrednio z aktywnego okna REW przez API, a nie z plików wyeksportowanych na dysk.
>
> **Filtry ochronne POZOSTAJĄ WŁĄCZONE podczas pomiarów:** Filtry górnoprzepustowe (HPF) dla delikatnych tweeterów i głośników średniotonowych muszą pozostać aktywne w DSP, aby chronić je podczas sweepów pomiarowych.

- **Zasada filtrów ochronnych:** Ochronny filtr HPF musi wynosić **$\ge 1.1 \times Fs$ (zalecane do $1.5 \times Fs$), ze spadkiem $\ge 24$ dB/okt.** (LR4 lub BW4). Jeśli $Fs$ nie jest znane, sprawdź wartość w karcie katalogowej producenta i podaj ją w projekcie.
- **Pozostałe przetwarzanie w DSP wyłączone:** Robocze EQ (puste), opóźnienia (ustawione na 0) oraz polaryzacje (normalne) muszą być wyczyszczone. Mierz każdy przetwornik z osobna. Zapisz każdy filtr ochronny podczas rundy pomiarowej (TCC o to zapyta; w terminalu rejestruje to sesja): metoda zdejmie jego wpływ przed odczytem fazy wypadkowej. Kanał zarejestrowany jako `OFF` jest odczytywany w stanie zastanym.
- **Poziomy w dBFS:** Ustaw głośność sweepa tak, aby szczyt najgłośniejszego głośnika (subwoofera) wynosił $-5\dots-10$ dBFS, a najcichszy głośnik grał wyraźnie powyżej poziomu szumów tła w kabinie. Wycisz wszystkie nieaktywne kanały w oprogramowaniu DSP i nie zmieniaj poziomu głośności karty dźwiękowej ani jednostki głównej przez całą sesję.
- **Dźwięk sweepa midbassu:** Midbass mierzony bez filtru LPF wydaje ostry, chropowaty dźwięk na wysokich częstotliwościach podczas odtwarzania sweepa. To normalne zjawisko rezonansu membrany (cone breakup) na górnym skraju jej pasma; głośnik nie ulega uszkodzeniu.

---

## Krzywe docelowe

### Jak stworzyć i skonfigurować własną krzywą docelową?
Krzywa docelowa daje ci wyjściowy balans brzmienia. Po bazowym nastrojeniu dopracowujesz go na ucho.

- **Wybierz spośród uznanych krzywych:** Wybierz spośród skalibrowanych krzywych docelowych — SQ-Comp-Ref (zawodnicza krzywa metody), ResoNix, Audiofrog, Harman, Jazzi oraz Whitledge — w zależności od swoich preferencji brzmieniowych. Skrypt `target_bands.py` oblicza docelowe kształty pasm dla poszczególnych głośników na podstawie wybranej krzywej i punktów podziału zwrotnicy.
- **Narysuj ręcznie:** Użyj darmowego narzędzia [Nono Tuning Tool](https://nonotuningtool.com) (sekcja *Custom Target Curve*), aby wyrysować charakterystykę i wyeksportować plik docelowy `.txt`.
- **Porównaj online:** Użyj narzędzia Target Curve Visualizer, aby porównać krzywe (SQ-Comp-Ref, twoją własną z REW oraz standardowe krzywe z Nono Tuning Tool):  
  👉 **[Otwórz Target Curve Visualizer online](https://ayukhno.github.io/autosound-tuning-skill/_curve-visualizer.html?lang=pl)**. Kliknięcie prawym przyciskiem myszy w dowolny punkt na wykresie wyjaśnia, jak dany zakres częstotliwości wpływa na brzmienie.

📘 [Krzywa house curve w TCC (EN)](https://github.com/ayukhno/autosound-tcc/blob/main/docs/guide/HOUSE-CURVE.md)

---

## Projekt na dysku i DSP

### Kompatybilność z procesorami i import filtrów do DSP
> [!IMPORTANT]
> Metoda oblicza filtry. Opóźnienia i wzmocnienia (gain) wprowadza się **ręcznie**, podobnie jak zwrotnice, chyba że narzędzie do wklejania pobierze je z formatu Extended opisanego poniżej. Import pliku przenosi wyłącznie **EQ**.

- **Audiotec Fischer (Helix / MATCH / BRAX):** Generuje gotowy do zaimportowania plik Full EQ, który DSP PC-Tool wczytuje dla wszystkich kanałów w jednym kroku.
- **Inne procesory DSP:** Eksportuje pliki REW Generic EQ (20 slotów) lub Generic/Extended ze zwrotnicami w treści pliku. Do szybkiego wprowadzania parametrów w innym oprogramowaniu DSP użyj narzędzia [REW-EQ-CopyPaste-Assistant](https://github.com/IvanBakhmutov/REW-EQ-CopyPaste-Assistant).
- **Sprawdzanie kompatybilności:** Przed eksportem metoda sprawdza każdy obliczony filtr pod kątem ograniczeń twojego modelu DSP (dostępne pasma, częstotliwość próbkowania, typy filtrów) i sygnalizuje wszelkie odchyłki.
- **Fabryczne jednostki główne (OEM):** Omiń fabryczne jednostki główne, doprowadzając czysty sygnał cyfrowy lub analogowy (DAP, USB, optyk) bezpośrednio do DSP, zamiast próbować de-equalizować fabryczne przetwarzanie barwy i loudness.

---

### Praca ze zwrotnicami pasywnymi (tweeter + midrange na jednym kanale)
Para głośników podłączona przez wspólną zwrotnicę pasywną jest traktowana jako **jeden wspólny kanał DSP**: otrzymuje jeden pomiar, wspólne opóźnienie, wspólne wzmocnienie (gain) oraz jeden zestaw filtrów EQ.

Cała reszta działa tak jak zwykle. Żadne oprogramowanie nie wyrówna czasu ani fazy pomiędzy tweeterem a głośnikiem średniotonowym w ramach takiej grupy pasywnej: aby to zrobić, każdy głośnik wymaga własnego kanału DSP.

---

### Kopia zapasowa

Duże pliki `.mdat` programu REW pozostają na twoim komputerze: zachowaj je. Aby utworzyć prywatną kopię zapasową folderu projektu na GitHubie, zainstaluj narzędzie z flagą `--github` (`-GitHub` w systemie Windows) i poproś sesję o wykonanie kopii zapasowej projektu — nic nie zostanie utworzone bez twojej zgody. Zawartość folderu: [Advanced Setup](ADVANCED.md#project-folder-structure-and-backup).
