# Asystent AI do strojenia car audio (Autosound Tuning Skill)

🇬🇧 [English](README.md) · 🇩🇪 [Deutsch](README.de.md) · 🇵🇱 **Polski** · 🇺🇦 [Українська](README.uk.md) · ❓ [FAQ](FAQ.md) · <img src="assets/icons/roadmap.svg" width="14" height="14" valign="middle" alt="Roadmap" /> [Roadmap (EN)](ROADMAP.md)

**Prostymi słowami:** To twój osobisty mistrz AI do strojenia car audio. Chcesz idealnej sceny i równego balansu tonalnego, ale wykresy, fazy i opóźnienia wydają ci się zbyt skomplikowane? Ten asystent weźmie najtrudniejsze na siebie. Czyta twoje pomiary z mikrofonu i krok po kroku prowadzi cię do idealnego dźwięku.

- **Ty mierzysz — AI liczy:** Współpracuje z programem REW, analizuje akustykę twojej kabiny i proponuje dokładne ustawienia dla korektora, zwrotnic i opóźnień (time alignment).
- **Minimum czasu w aucie:** Główne obliczenia odbywają się przy biurku w domu. W samochodzie wykonujesz tylko początkowe pomiary, a potem wracasz z gotowymi liczbami, aby posłuchać rezultatu i wejść w głębokie strojenie krok po kroku.
- **Nic nie zapisuje w twoim DSP — ty to wpisujesz:** Asystent nigdy nie ingeruje bezpośrednio w twój procesor. Pokazuje ci tylko liczby i wykresy; ty podejmujesz decyzję i wpisujesz je ręcznie.
- **To nie jest zwykły czat:** Stan projektu i wszystkie ustawienia są zapisywane w plikach na twoim dysku, więc nic nie "zapomina się" między sesjami i zawsze można cofnąć się o krok.
- **Dwa AI (opcjonalnie):** System może używać dwóch AI (Claude i Gemini). Jedno proponuje ustawienia, drugie je krytykuje i sprawdza. Ale ostatecznym sędzią jest twoje ucho: słuchasz i decydujesz, a nie tylko ślepo zatwierdzasz ich pomysły.
- **Pracuje na faktach:** Weryfikacja, której brakuje danych, odmawia działania. AI nie zgaduje ustawień — jeśli pomiary zostały wykonane nieprawidłowo lub jest ich za mało, konkretna weryfikacja po prostu odmówi obliczeń i się zatrzyma.

## Sprawdzone na zawodach

Dzięki wersji 2.x tej metody, samochód autora zdobył cztery nagrody w 2026 roku na mistrzostwach **EMMA** i **AYA** (pierwsza nagroda została zdobyta jeszcze przed sformowaniem metody w skill, za pomocą wskazówek AI z tych samych wykresów, co dało pomysł na jego stworzenie). Najnowsza wersja 3.x (z interfejsem graficznym) jest obecnie w fazie beta i jeszcze nie udowodniła swojej wartości na zawodach, dlatego dla gwarantowanego rezultatu wiele osób wybiera sprawdzoną wersję 2.8.x.

<p align="left">
  <img src="assets/awards/aya-may26-einsteiger5000.jpg" height="120" alt="AYA Maj 2026, Einsteiger 5000, 1. miejsce">
  &nbsp;&nbsp;&nbsp;
  <img src="assets/awards/aya-jul26-amateur5000.jpg" height="120" alt="AYA Lipiec 2026, Amateur 5000, 1. miejsce">
  &nbsp;&nbsp;&nbsp;
  <img src="assets/awards/aya-aug26-amateur5000.jpg" height="120" alt="AYA Sierpień 2026, Amateur 5000, 2. miejsce">
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
  <img src="assets/awards/emma-aug26-entry-unlimited.jpg" height="120" alt="EMMA Sound Off 2026, SQ Entry Unlimited, 3. miejsce">
</p>

*Twój system też może brzmieć na poziomie mistrzów!*

> [!CAUTION]
> AI to asystent, ale odpowiedzialność spoczywa na tobie. Ręcznie wpisana liczba z błędem może spalić głośnik wysokotonowy (tweeter). Zawsze sprawdzaj częstotliwości cięcia przed włączeniem dźwięku i zawsze zaczynaj od niskiej głośności.

## Czego potrzebujesz na start

Nie musisz być programistą — program instaluje się jednym poleceniem. Ale jeśli chodzi o sprzęt i subskrypcje, będziesz potrzebować:

1. **Mikrofon pomiarowy** (np. UMIK-1, a najlepiej mikrofon XLR z kartą dźwiękową i fizycznym loopbackiem).
2. **Procesor (DSP)** w twoim aucie.
3. **Program REW (Room EQ Wizard)** — obowiązkowo **wersja beta** (w zwykłej wersji release w ogóle nie ma zakładki API). Pobierz wersję beta z [roomeqwizard.com/beta.html](https://www.roomeqwizard.com/beta.html). Po uruchomieniu REW wejdź w *Preferences → API*, zaznacz **Start the API when REW starts** i kliknij **Start server**.
4. **Płatna subskrypcja Claude (Pro lub Max)** — to AI wykonuje główną pracę i rozwiązuje skomplikowane zadania matematyczne. Bez internetu przy aucie sesja nie zadziała.

*(Polecamy również posiadanie darmowego konta GitHub, aby automatycznie zapisywać historię strojenia w prywatnym repozytorium).*

## Jak zainstalować i zacząć (Wersja 3.x — Beta)

Stworzyliśmy instalator, który sam pobierze wszystko, co potrzebne i przygotuje wygodną **aplikację graficzną (Autosound TCC)**. Proces zajmuje 10–20 minut (na systemie macOS system raz poprosi o hasło, na Windows pokaże okno uprawnień dla Git).

**macOS** — otwórz Terminal (naciśnij ⌘-Space, wpisz "terminal", Enter) i wklej:
```sh
curl -fsSL https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/main/install.sh | bash
```

**Windows** — otwórz PowerShell (naciśnij Start, wpisz "powershell", Enter) i wklej:
```powershell
irm https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/main/install.ps1 | iex
```

**Po instalacji:**
1. Na pulpicie pojawi się aplikacja **Autosound TCC**. Otwórz ją.
2. Utwórz nowy, pusty folder dla swojego auta (np. `MyCarTuning`) i wybierz go w programie.
3. **WAŻNE:** Przed pierwszą wiadomością upewnij się, że poziom wysiłku (effort) dla **Claude Opus** jest ustawiony nie niżej niż `xhigh` (to wartość domyślna). Do bardzo trudnych kroków używaj `max`. Jest to krytyczne: słabszy model nie zatrzymuje się przy błędzie, po prostu zgadza się z tobą, co prowadzi do "cichych porażek" w ustawieniach. *Uwaga: zmiana poziomu ma zastosowanie dopiero w następnej sesji.*
4. Wpisz w czacie aplikacji: **"tune a new car from scratch"**. AI zacznie zadawać pytania i poprowadzi cię za rękę.

▶ **[Otwórz Target Curve Visualizer online](https://ayukhno.github.io/autosound-tuning-skill/_curve-visualizer.html?lang=pl)** — przeciągnij swoją krzywą lub standardową z [Nono Tuning Tool](https://nonotuningtool.com), porównuj wykresy i zapisuj u siebie.

---

**Sprawdzona na zawodach wersja 2.8.x** — [ścieżka 3 w FAQ](FAQ.md#the-four-paths-and-what-each-costs-you) (po angielsku)

Jeśli chcesz użyć dokładnie tej samej wersji **2.8.x**, którą wygrywano zawody, działa ona wyłącznie przez terminal. Zamiast powyższych skryptów, w terminalu z już zainstalowanym `claude` (Claude Code) wykonaj dwa polecenia:
```sh
claude plugin marketplace add ayukhno/autosound-tuning-skill
claude plugin install autosound-tuning
```
*(Jeśli `claude` nie jest jeszcze zainstalowane, możesz je dodać za pomocą oficjalnego skryptu: `curl -fsSL https://claude.ai/install.sh | sh`, lub awaryjnie przez npm).*

## Jak wygląda proces strojenia

1. **Przygotowanie w domu:** Opowiadasz AI o swoim systemie (jakie głośniki, jaki procesor).
2. **Pomiary w aucie (jeden raz):** Siadasz w samochodzie z mikrofonem, włączasz podstawowe filtry zabezpieczające na procesorze i po prostu nagrywasz serię sweepów dla każdego głośnika. *Uwaga: midbas bez filtra dolnoprzepustowego (LPF) brzmi ostro na górze podczas sweepu — to normalne (break-up membrany), nie przerywaj pomiarów.*
3. **Matematyka przy biurku:** Siadasz do komputera (bez auta obok). AI analizuje pomiary, zgrywa subwoofer z midbasem, wyrównuje scenę, oblicza korektor. Biurko jedynie przewiduje wyniki; auto potem je weryfikuje. Jeśli podczas weryfikacji prognozy biurka nie zgadzają się z rzeczywistością — system cofa kroki.
4. **Przyjemność w aucie:** Wracasz do samochodu, wpisujesz gotowe liczby do procesora, puszczasz testowe oraz ulubione utwory i cieszysz się dźwiękiem. Jeśli coś trochę buczy, „kłuje w ucho” lub „scena jest nie na miejscu” — mówisz o tym AI, a wy punktowo korygujecie problem.

## Opinie, wsparcie i prywatność

**Prywatność:** Skill uczy się z każdego strojenia i tylko za twoją wyraźną zgodą wysyła uogólnione lekcje do wspólnej bazy wiedzy. Nigdy nie zbiera danych osobowych i nie wysyła pełnych pomiarów.

**Problemy i błędy:**
- Jeśli coś jest nie tak z samą logiką strojenia: [Otwórz issue na GitHub (autosound-tuning-skill)](https://github.com/ayukhno/autosound-tuning-skill/issues/new/choose).
- Jeśli problem dotyczy interfejsu graficznego (Autosound TCC) — napisz w [repozytorium aplikacji TCC](https://github.com/ayukhno/autosound-tcc/issues/new/choose).

To narzędzie jest **całkowicie darmowe**. Kod i skrypty są na licencji **MIT**, a dokumentacja i sama metoda na **CC BY-SA 4.0**. 

Jeśli zaoszczędziło ci to tygodnie czasu na strojenie i chcesz podziękować autorowi, możesz to zrobić tutaj:
💜 **[GitHub Sponsors](https://github.com/sponsors/ayukhno)** · ☕ **[Słoik w Monobank (UA)](https://send.monobank.ua/jar/8wThVcodjm)**

**Dobrego dźwięku!**
