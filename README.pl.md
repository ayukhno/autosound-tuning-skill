# Asystent AI do strojenia car audio (Autosound Tuning Skill)

🇬🇧 [English](README.md) · 🇩🇪 [Deutsch](README.de.md) · 🇵🇱 **Polski** · 🇺🇦 [Українська](README.uk.md) · ❓ [FAQ](FAQ.pl.md) · 📘 [TCC quick guide (EN)](https://github.com/ayukhno/autosound-tcc/blob/main/docs/guide/QUICK-GUIDE.md)

**Mówiąc prosto:** To Twój osobisty mistrz strojenia car audio oparty na AI. Chcesz idealnej sceny dźwiękowej i wyrównanego balansu tonalnego, ale wykresy, fazy i opóźnienia wydają się zbyt skomplikowane? Ten asystent zajmie się najtrudniejszą częścią. Odczytuje Twoje pomiary z mikrofonu i prowadzi Cię krok po kroku do perfekcyjnego dźwięku.

- **Ty mierzysz — AI liczy:** Współpracuje z programem REW, analizuje akustykę Twojej kabiny i proponuje dokładne ustawienia EQ, zwrotnic oraz korekcji czasowej.
- **Minimum czasu w aucie:** Główne obliczenia odbywają się przy biurku w domu. W samochodzie robisz tylko wstępne pomiary, a potem wracasz z gotowymi wartościami, aby odsłuchać efekt i krok po kroku przejść do dogłębnego strojenia.
- **Nic nie zapisuje w Twoim DSP — to Ty wgrywasz ustawienia:** Asystent nigdy nie modyfikuje Twojego procesora bezpośrednio. Pokazuje Ci liczby i wykresy oraz przygotowuje EQ do importu: w procesorach Helix cały bank Full EQ wgrywa się przez DSP PC-Tool w jednym kroku, a dla procesorów bez importu z pliku bezpłatny [REW-EQ-CopyPaste-Assistant](https://github.com/IvanBakhmutov/REW-EQ-CopyPaste-Assistant) wkleja je za Ciebie. To Ty decydujesz, co trafia do urządzenia.
- **To nie jest zwykły czat:** Stan projektu i wszystkie ustawienia są zapisywane w plikach na Twoim dysku, dzięki czemu nic nie zostaje „zapomniane” między sesjami i zawsze możesz cofnąć się o krok.
- **Dwa AI, a decyduje Twoje ucho:** jedno AI proponuje ustawienia, drugie je weryfikuje. Weryfikacja jest częścią metody; opcjonalne jest tylko automatyczne połączenie między nimi — bez niego wklejasz pakiet do dowolnego czatu AI ręcznie. Ostatecznym sędzią jest Twoje ucho: słuchasz i decydujesz, a nie po prostu zatwierdzasz.
- **Opiera się na faktach:** AI nie zgaduje ustawień. Jeśli pomiary są błędne lub niewystarczające, weryfikacja to wychwyci i poprosi Cię o powtórzenie pomiaru — albo o świadome kontynuowanie z zaakceptowaniem ryzyka błędu.

## Sprawdzone na zawodach

Dzięki wersji 2.x tej metody samochód autora zdobył w 2026 roku cztery nagrody na mistrzostwach **EMMA** i **AYA** (pierwsza nagroda została zdobyta jeszcze przed zebraniem metody w skill, przy użyciu wskazówek AI z tych samych wykresów, co stało się inspiracją dla tego projektu). Wersja 3.1, z interfejsem graficznym, jest wydaniem bieżącym. Piąta nagroda — 3. miejsce na zawodach **German EMMA Final 2026** — została zdobyta z wersją 3.x dzięki dopracowaniu istniejącego strojenia, a nie strojeniu od zera. Linia 2.8.x stojąca za pierwszymi czterema jest nadal dostępna: zobacz FAQ, [ścieżka 3](FAQ.pl.md#four-paths-of-usage).

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

*Twój system też może brzmieć po mistrzowsku!*

> [!CAUTION]
> AI jest asystentem, ale odpowiedzialność spoczywa na Tobie. Ręcznie wpisana wartość z literówką może spalić głośnik wysokotonowy. Zawsze sprawdzaj częstotliwości podziału zwrotnic przed wyłączeniem wyciszenia dźwięku i zawsze zaczynaj od niskiego poziomu głośności.

## Czego potrzebujesz na start

Aplikację instaluje się jednym poleceniem. Ze sprzętu i subskrypcji będziesz potrzebować:

1. **Mikrofon pomiarowy** (np. UMIK-1 lub najlepiej mikrofon XLR z interfejsem audio i fizycznym loopbackiem).
2. **Procesor dźwięku (DSP)** w Twoim samochodzie.
3. **Oprogramowanie REW (Room EQ Wizard)** — wymagana jest **wersja beta** (obecne oficjalne wydanie, V5.31.3 z lipca 2024 r., nie posiada API w ogóle — sprawdź Help → About przed rozpoczęciem). Pobierz wersję beta z [roomeqwizard.com/beta.html](https://www.roomeqwizard.com/beta.html). Po uruchomieniu REW przejdź do *Preferences → API*, zaznacz **Start the API when REW starts** i kliknij **Start server**.
4. **Płatna subskrypcja Claude (Pro lub Max)** — Claude wykonuje najcięższą pracę; to oficjalnie wspierana ścieżka i aplikacja jest zbudowana właśnie pod nią. Inne modele AI mogą prowadzić proces za pośrednictwem `omp` (instalowanego tylko na Twoje życzenie) — na własne ryzyko.

*(Zalecane: darmowe konto GitHub, aby tworzyć kopię zapasową historii strojenia w prywatnym repozytorium).*

## Jak zainstalować i uruchomić

**Domyślnie instalator konfiguruje:** Claude Code, metodę strojenia wraz z bibliotekami Pythona wymaganymi przez jej narzędzia, aplikację desktopową **Autosound TCC** oraz recenzenta Gemini (`agy`). Trwa to 10–20 minut za pierwszym razem na Macu bez narzędzi programistycznych, w przeciwnym razie kilka minut. W zależności od Twojego systemu inne instalatory mogą po drodze poprosić o uprawnienia — to normalne (szczegóły w FAQ).

**macOS** — otwórz Terminal (⌘-Spacja, wpisz „terminal”, Enter) i wklej:
```sh
curl -fsSL https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/v3.1.2/install.sh | bash
```

**Windows** — otwórz PowerShell (Start, wpisz „powershell”, Enter) i wklej:
```powershell
irm https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/v3.1.2/install.ps1 | iex
```
*(Wersja w adresie przypina sam instalator; zawsze instaluje on najnowsze wydanie).*

**Opcje:**

| Co robi | macOS | Windows |
|---|---|---|
| modele inne niż Claude, przez `omp` | `--with-omp` | `-WithOmp` |
| kopia zapasowa projektu na GitHub (prywatne repozytorium; klucze pozostają poza nim) | `--github` | `-GitHub` |
| metoda bez aplikacji (tylko terminal) | `--terminal` | `-Terminal` |
| pokazuje plan i niczego nie zmienia | `--dry-run` | `-DryRun` |

Z opcjami — na przykład `omp` i kopią zapasową na GitHub — na macOS:
```sh
curl -fsSL https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/v3.1.2/install.sh | bash -s -- --with-omp --github
```
a na Windows, w dwóch wierszach:
```powershell
$i = irm https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/v3.1.2/install.ps1
& ([scriptblock]::Create($i)) -WithOmp -GitHub
```
**Jak się zakończyło**, widać w kodzie wyjścia instalatora: `0` gotowe · `1` zatrzymano — metoda nie została zainstalowana ani zmieniona · `2` błędna opcja dla `install.sh` albo nieprawidłowy `-Channel` lub `-Plugin` dla `install.ps1` (sam PowerShell odrzuca opcję, której nie zna, z `1`) · `3` zainstalowane, ale niegotowe, jego ostatnie linie wskazują, czego brakuje i co zrobić.

**Korzystasz już z Claude Code?** Metodę można zainstalować także jako wtyczkę:
```sh
claude plugin marketplace add ayukhno/autosound-tuning-skill
claude plugin install autosound-tuning
```
Wtyczka pobiera wyłącznie pliki metody: podczas pierwszej sesji wpisz **`/autosound-tuning:setup`** — polecenie sprawdzi wtyczkę pod kątem podpisanego wydania i doinstaluje resztę. Aplikacja desktopowa TCC nie jest w ten sposób dołączana; dodaj ją za pomocą `/autosound-tuning:setup app` (lub `/autosound-tuning:install-tcc`).

**Po instalacji:**
1. Ostatni krok instalatora loguje Cię: najpierw do Claude, potem do recenzenta Gemini (`agy`) oraz do GitHub, jeśli wybrano tę opcję.
2. Otwórz aplikację **Autosound TCC** ze swojego pulpitu.
3. Utwórz pusty folder dla swojego samochodu (np. `MyCarTuning`) i wybierz go w aplikacji, ustawiając **AI main: Claude Opus (SDK)** oraz **AI critic: Gemini Pro (High)** — lub **Gemini Flash (High)**, jeśli wersja Pro nie jest u Ciebie dostępna.
4. **Ważne:** utrzymaj Effort dla Claude Opus na poziomie `xhigh` lub wyższym (domyślnie; `max` w przypadku trudnych kroków).
5. Wpisz w czacie aplikacji: **"tune a new car from scratch"**. AI zacznie zadawać pytania i poprowadzi Cię za rękę.

Wolisz rozmawiać z AI w terminalu? To również działa i wielu uważa to za wygodniejsze rozwiązanie: miej obok otwarte TCC w **Control mode**, gdzie widzisz i kontrolujesz każdy parametr w trakcie trwania sesji ([przewodnik po TCC](https://github.com/ayukhno/autosound-tcc/blob/main/docs/guide/REFERENCE.md#control-mode), [FAQ](FAQ.pl.md#control-mode-sesja-w-terminalu)).

▶ **Krzywe docelowe:** metoda zawiera własną krzywą stworzoną pod zawody, **SQ-Comp-Ref**. Narzędzie **[Target Curve Visualizer](https://ayukhno.github.io/autosound-tuning-skill/_curve-visualizer.html?lang=pl)** analizuje i porównuje krzywe zestawione obok siebie — SQ-Comp-Ref, Twoje własne z REW lub standardowe z [Nono Tuning Tool](https://nonotuningtool.com) — i zapisuje tę, którą wybierzesz. Jak wybrać krzywą: [przewodnik po krzywych docelowych](skills/autosound-tuning/references/patterns/target-curves/target_curves_guide.md).

## Jak wygląda proces strojenia

1. **Przygotowanie w domu:** Opowiadasz AI o swoim systemie (jakie głośniki, jaki procesor).
2. **Pomiary w aucie (jednorazowo):** z filtrami ochronnymi na DSP mierzysz każdy głośnik z osobna podczas jednej sesji; aplikacja TCC prowadzi Cię przez ten proces krok po kroku. Następnie całe strojenie jest projektowane przy biurku.
3. **Matematyka przy biurku:** Siedzisz przy komputerze (bez konieczności przebywania w samochodzie). AI analizuje pomiary, łączy subwoofer z midbasem, wyrównuje scenę dźwiękową i oblicza EQ. Biurko pozwala jedynie przewidzieć rezultaty; samochód następnie je weryfikuje.
4. **Z powrotem w aucie — weryfikacja, korekta, precyzyjne dostrajanie:** wprowadzasz wartości do DSP, sprawdzasz je za pomocą kilku pomiarów oraz na ucho i poprawiasz to, co się nie zgadza. Następnie przychodzi pora na precyzyjne dostrajanie, które najlepiej przeprowadzić w aucie z najbardziej zaawansowanym modelem (obecnie Claude Fable): mówisz AI, co słyszysz — im lepsze brzmienie chcesz osiągnąć, tym więcej rund to wymaga. Praca przy biurku również jest możliwa — model i metoda dostosowują się do warunków.

## Opinie, wsparcie i prywatność

**Prywatność:** Skill uczy się na każdym strojeniu i wyłącznie za Twoją wyraźną zgodą przesyła uogólnione wnioski do współdzielonej bazy wiedzy. Nigdy nie zbiera danych osobowych i nigdy nie wysyła pełnych pomiarów.

**Problemy i błędy:**
- Jeśli coś jest nie tak z samą logiką strojenia: [Otwórz zgłoszenie na GitHub (autosound-tuning-skill)](https://github.com/ayukhno/autosound-tuning-skill/issues/new/choose).
- Jeśli problem dotyczy interfejsu graficznego (Autosound TCC) — napisz w [repozytorium aplikacji TCC](https://github.com/ayukhno/autosound-tcc/issues/new/choose).
- Nie masz konta GitHub? Powiedz podczas sesji ("report a bug") lub skorzystaj z okna zgłoszeń w TCC: Twój raport trafi do autora za pośrednictwem Google Form — wyłącznie w formie tekstu.

To narzędzie jest **całkowicie darmowe**. Kod i skrypty są objęte licencją **MIT**, a sama dokumentacja i metoda licencją **CC BY-SA 4.0**.

**Podziękowania:** część obliczeń matematycznych DSP została przeniesiona z projektu [Resonalyze](https://github.com/DIMOSUS/Resonalyze) autorstwa DIMOSUS (MIT) — [`LICENSES/NOTICE.md`](LICENSES/NOTICE.md).

Jeśli zaoszczędziło Ci to tygodnie strojenia i chcesz podziękować autorowi, możesz zrobić to tutaj:
💜 **[GitHub Sponsors](https://github.com/sponsors/ayukhno)** · ☕ **[Monobank Jar (UA)](https://send.monobank.ua/jar/8wThVcodjm)**

**Dobrego brzmienia!**
