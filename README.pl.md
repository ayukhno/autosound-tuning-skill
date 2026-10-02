# Asystent AI do strojenia car audio (Autosound Tuning Skill)

🇬🇧 [English](README.md) · 🇩🇪 [Deutsch](README.de.md) · 🇵🇱 **Polski** · 🇺🇦 [Українська](README.uk.md) · ❓ [FAQ](FAQ.pl.md) · 📘 [TCC guide (EN)](https://github.com/ayukhno/autosound-tcc/blob/main/docs/guide/QUICK-GUIDE.md) · <img src="assets/icons/roadmap.svg" width="14" height="14" valign="middle" alt="Roadmap" /> [Roadmap (EN)](ROADMAP.md)

**W prostych słowach:** To twój osobisty mistrz strojenia car audio oparty na AI. Chcesz idealnej sceny dźwiękowej i wyrównanej równowagi tonalnej, ale wykresy, fazy i opóźnienia wydają się zbyt skomplikowane? Ten asystent weźmie najtrudniejsze na siebie. Odczytuje twoje pomiary mikrofonowe i prowadzi cię krok po kroku do idealnego dźwięku.

- **Ty mierzysz — AI liczy:** Współpracuje z oprogramowaniem REW, analizuje akustykę kabiny twojego auta i proponuje dokładne ustawienia EQ, zwrotnic oraz wyrównania czasowego.
- **Minimum czasu w aucie:** Główne obliczenia odbywają się przy biurku w domu. W aucie wykonujesz tylko wstępne pomiary, a potem wracasz z gotowymi wartościami, aby odsłuchać rezultat i krok po kroku zagłębić się w zaawansowane strojenie.
- **Nic nie zapisuje w twoim DSP — wgrywasz sam:** Asystent nigdy nie ingeruje bezpośrednio w procesor. Pokazuje ci liczby oraz wykresy i przygotowuje EQ do importu: w procesorach Helix cały bank Full EQ wgrywa się przez DSP PC-Tool w jednym kroku, a w przypadku procesorów bez importu z pliku darmowy [REW-EQ-CopyPaste-Assistant](https://github.com/IvanBakhmutov/REW-EQ-CopyPaste-Assistant) wkleja go za ciebie. To ty decydujesz, co trafia do procesora.
- **To nie jest zwykły czat:** Stan projektu i wszystkie ustawienia są zapisywane w plikach na twoim dysku, więc nic nie zostanie „zapomniane” między sesjami i zawsze możesz cofnąć się o krok.
- **Dwa AI, a decyduje twoje ucho:** jedno AI proponuje ustawienia, drugie je sprawdza. Weryfikacja jest częścią metody; opcjonalne jest tylko automatyczne połączenie między nimi — bez niego wklejasz pakiet do dowolnego czatu AI ręcznie. Ostatecznym sędzią jest twoje ucho: słuchasz i decydujesz, a nie tylko zatwierdzasz.
- **Działa na faktach:** AI nie zgaduje ustawień. Jeśli pomiary są błędne lub niewystarczające, weryfikacja to wyłapie i poprosi cię o powtórzenie pomiaru — albo o świadome kontynuowanie z akceptacją ryzyka błędu.

## Sprawdzone na zawodach

Dzięki wersji 2.x tej metody samochód autora zdobył w 2026 roku cztery nagrody na mistrzostwach **EMMA** i **AYA** (pierwsza nagroda została zdobyta jeszcze przed zebraniem metody w skill, z wykorzystaniem podpowiedzi AI z tych samych wykresów, co stało się inspiracją dla tego projektu). Wersja 3.1, z interfejsem graficznym, to aktualne wydanie. Piąta nagroda — 3. miejsce na **German EMMA Final 2026** — przypadła wersji 3.x za dopracowanie istniejącego strojenia, a nie strojenie od zera. Linia 2.8.x stojąca za pierwszymi czterema nagrodami jest nadal dostępna: zobacz FAQ, [wariant 3](FAQ.pl.md#cztery-warianty-użycia).

<p align="left">
  <img src="assets/awards/aya-may26-einsteiger5000.jpg" height="120" alt="AYA May 2026, Einsteiger 5000, 1st place">
  &nbsp;&nbsp;&nbsp;
  <img src="assets/awards/aya-jul26-amateur5000.jpg" height="120" alt="AYA July 2026, Amateur 5000, 1st place">
  &nbsp;&nbsp;&nbsp;
  <img src="assets/awards/aya-aug26-amateur5000.jpg" height="120" alt="AYA August 2026, Amateur 5000, 2nd place">
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
  <img src="assets/awards/emma-aug26-entry-unlimited.jpg" height="120" alt="EMMA Sound Off 2026, SQ Entry Unlimited, 3rd place">
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
  <img src="assets/awards/emma-sep26-final-entry-unlimited.jpg" height="120" alt="German EMMA Final 2026, Frankfurt, SQ Entry Unlimited, 3rd place">
</p>

*Twój system też może zagrać po mistrzowsku!*

> [!CAUTION]
> AI to asystent, ale odpowiedzialność spoczywa na tobie. Ręcznie wpisana liczba z literówką może spalić tweeter. Zawsze sprawdzaj częstotliwości podziału zwrotnic przed wyłączeniem wyciszenia i zawsze zaczynaj od niskiego poziomu głośności.

## Czego potrzebujesz na start

Aplikację instaluje się jednym poleceniem. Pod kątem sprzętu i subskrypcji będziesz potrzebować:

1. **Mikrofon pomiarowy** (np. UMIK-1, a najlepiej mikrofon XLR z interfejsem audio i fizyczną pętlą loopback).
2. **Procesor (DSP)** w twoim aucie.
3. **Oprogramowanie REW (Room EQ Wizard)** — wymagana jest **wersja beta** (obecne oficjalne wydanie, V5.31.3 z lipca 2024 r., w ogóle nie ma API — sprawdź Help → About przed rozpoczęciem). Pobierz wersję beta ze strony [roomeqwizard.com/beta.html](https://www.roomeqwizard.com/beta.html). Po uruchomieniu REW przejdź do *Preferences → API*, zaznacz **Start the API when REW starts** i kliknij **Start server**.
4. **Płatna subskrypcja Claude (Pro lub Max)** — Claude wykonuje najcięższą pracę; to oficjalnie wspierany wariant i aplikacja powstała właśnie pod niego. Inne AI mogą prowadzić proces przez `omp` (instalowany tylko na twoje życzenie) — na własne ryzyko.

*(Zalecane: darmowe konto GitHub, aby tworzyć kopię zapasową historii strojenia w prywatnym repozytorium).*

## Jak zainstalować i uruchomić

**Domyślnie instalator konfiguruje:** Claude Code, metodę strojenia wraz z bibliotekami Pythona, których potrzebują jej narzędzia, aplikację desktopową **Autosound TCC** oraz recenzenta Gemini (`agy`). Trwa to 10–20 minut. W zależności od twojego systemu inne instalatory mogą po drodze prosić o uprawnienia — to normalne (szczegóły w FAQ).

**macOS** — otwórz Terminal (⌘-Spacja, wpisz „terminal”, Enter) i wklej:
```sh
curl -fsSL https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/v3.0.66/install.sh | bash
```

**Windows** — otwórz PowerShell (Start, wpisz „powershell”, Enter) i wklej:
```powershell
irm https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/v3.0.66/install.ps1 | iex
```
*(Wersja w adresie przypina sam instalator; zawsze instaluje on najnowsze wydanie).*

**Opcje:**

| Co robi | macOS | Windows |
|---|---|---|
| modele inne niż Claude, przez `omp` | `--with-omp` | `-WithOmp` |
| kopia zapasowa projektu na GitHub (prywatne repozytorium; klucze pozostają poza nim) | `--github` | `-GitHub` |
| metoda bez aplikacji (tylko terminal) | `--terminal` | `-Terminal` |
| pokaż plan i nic nie zmieniaj | `--dry-run` | `-DryRun` |

Z opcjami — na przykład z `omp` i kopią zapasową na GitHub — na macOS:
```sh
curl -fsSL https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/v3.0.66/install.sh | bash -s -- --with-omp --github
```
a na Windows, w dwóch linijkach:
```powershell
$i = irm https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/v3.0.66/install.ps1
& ([scriptblock]::Create($i)) -WithOmp -GitHub
```

**Korzystasz już z Claude Code?** Metodę można zainstalować również jako plugin:
```sh
claude plugin marketplace add ayukhno/autosound-tuning-skill
claude plugin install autosound-tuning
```
Plugin pobiera tylko pliki metody: podczas pierwszej sesji wpisz **`/autosound-tuning:setup`** — sprawdza ono plugin pod kątem podpisanego wydania i instaluje całą resztę. Aplikacja desktopowa TCC nie jest w ten sposób dołączana; dodaj ją za pomocą `/autosound-tuning:setup app` (lub `/autosound-tuning:install-tcc`).

**Po instalacji:**
1. Ostatni krok instalatora loguje cię: do Claude, następnie do recenzenta Gemini (`agy`) oraz do GitHub, jeśli wybrano tę opcję.
2. Otwórz aplikację **Autosound TCC** ze swojego pulpitu.
3. Utwórz pusty folder dla swojego samochodu (np. `MyCarTuning`) i wybierz go w aplikacji, z ustawieniami **AI main: Claude Opus (SDK)** i **AI critic: Gemini Pro (High)** — lub **Gemini Flash (High)**, jeśli wersja Pro nie jest u ciebie dostępna.
4. **Ważne:** utrzymaj parametr effort dla Claude Opus na poziomie `xhigh` lub wyższym (wartość domyślna; `max` dla trudnych kroków).
5. Wpisz na czacie aplikacji: **"tune a new car from scratch"**. AI zacznie zadawać pytania i poprowadzi cię za rękę.

▶ **Krzywe docelowe:** metoda zawiera własną krzywą stworzoną na zawody, **SQ-Comp-Ref**. Narzędzie **[Target Curve Visualizer](https://ayukhno.github.io/autosound-tuning-skill/_curve-visualizer.html?lang=pl)** analizuje i porównuje krzywe zestawione obok siebie — SQ-Comp-Ref, twoje własne z REW lub standardowe z [Nono Tuning Tool](https://nonotuningtool.com) — i zapisuje tę, którą wybierzesz. Jak wybrać krzywą: [przewodnik po krzywych docelowych](skills/autosound-tuning/references/patterns/target-curves/target_curves_guide.md).

## Jak wygląda proces strojenia

1. **Przygotowanie w domu:** Opowiadasz AI o swoim systemie (jakie głośniki, jaki procesor).
2. **Pomiary w aucie (jednorazowo):** z filtrami ochronnymi na DSP mierzysz każdy przetwornik z osobna, w trakcie jednej sesji; aplikacja TCC prowadzi cię przez to krok po kroku. Projekt strojenia powstaje potem przy biurku.
3. **Obliczenia przy biurku:** Siedzisz przy komputerze (z dala od auta). AI analizuje pomiary, zgrywa subwoofer z midbasem, wyrównuje scenę dźwiękową i wylicza EQ. Przy biurku jedynie przewidujesz rezultaty; samochód następnie je weryfikuje.
4. **Z powrotem w aucie — weryfikacja, korekta, precyzyjne strojenie:** wprowadzasz wartości do DSP, sprawdzasz je za pomocą kilku pomiarów oraz na ucho i korygujesz to, co się nie zgadza. Następnie przychodzi pora na precyzyjne strojenie, najlepiej wykonywane bezpośrednio w samochodzie z najbardziej zaawansowanym modelem (obecnie Claude Fable): opisujesz AI to, co słyszysz, a im lepsze brzmienie chcesz osiągnąć, tym więcej rund to wymaga. Praca przy biurku też jest możliwa — model i metoda się dostosują.

## Opinie, wsparcie i prywatność

**Prywatność:** Skill uczy się na każdym strojeniu i tylko za twoją wyraźną zgodą wysyła uogólnione wnioski do współdzielonej bazy wiedzy. Nigdy nie zbiera danych osobowych ani nie przesyła pełnych pomiarów.

**Zgłaszanie problemów i błędów:**
- Jeśli coś jest nie tak z samą logiką strojenia: [otwórz zgłoszenie na GitHub (autosound-tuning-skill)](https://github.com/ayukhno/autosound-tuning-skill/issues/new/choose).
- Jeśli problem dotyczy interfejsu graficznego (Autosound TCC) — napisz w [repozytorium aplikacji TCC](https://github.com/ayukhno/autosound-tcc/issues/new/choose).
- Nie masz konta na GitHub? Napisz podczas sesji ("report a bug") lub skorzystaj z okna zgłoszeń w TCC: twoje zgłoszenie trafi do autora przez Google Form — wyłącznie w formie tekstu.

To narzędzie jest **całkowicie darmowe**. Kod i skrypty są licencjonowane na warunkach **MIT**, a sama dokumentacja i metoda na **CC BY-SA 4.0**. 

**Podziękowania:** część obliczeń matematycznych DSP została przeniesiona z projektu [Resonalyze](https://github.com/DIMOSUS/Resonalyze) autorstwa DIMOSUS (MIT) — [`LICENSES/NOTICE.md`](LICENSES/NOTICE.md).

Jeśli narzędzie zaoszczędziło ci tygodnie pracy nad strojeniem i chcesz podziękować autorowi, możesz to zrobić tutaj:
💜 **[GitHub Sponsors](https://github.com/sponsors/ayukhno)** · ☕ **[Monobank Jar (UA)](https://send.monobank.ua/jar/8wThVcodjm)**

**Dobrego brzmienia!**
