# Autosound Tuning Skill

🇬🇧 [English](README.md) · 🇩🇪 [Deutsch](README.de.md) · 🇵🇱 **Polski** · 🇺🇦 [Українська](README.uk.md) · ❓ [FAQ](FAQ.md) · <img src="assets/icons/roadmap.svg" width="14" height="14" valign="middle" alt="Roadmap" /> [Roadmap (EN, szkic)](ROADMAP.md)

**W jednym zdaniu:** skill dla Claude, który prowadzi cię do czystego, przejrzystego, zrównoważonego brzmienia w *twoim* aucie. Wnosi całe rzemiosło do twojego konkretnego zestawu, czyta twoje pomiary z REW i pomaga wybrać każdą zmianę.

- **Współpracuje z REW**: pobiera pomiary przez API, zapisuje obliczone filtry EQ z powrotem w REW, skąd eksportujesz je do swojego DSP
- **Diagnozuje, zanim naprawi**: określa podatność na EQ, odbicia (problemy fazowe) i granice zniekształceń każdego głośnika na podstawie pomiaru bazowego, zanim zaproponuje jakąkolwiek zmianę zwrotnicy lub EQ
- **Zna rzemiosło**: krzywe docelowe, praktyki strojenia, proces krok po kroku
- **Ścieżki testowe**: czego słuchać i na której ścieżce (opisy, nie audio)
- **Uczy się twojego zestawu**: gromadzi wiedzę o aucie i sprzęcie, tylko za twoją zgodą

> [!CAUTION]
> AI może pomylić się w liczbach. Zawsze sprawdzaj częstotliwości zwrotnic, nachylenia filtrów i wartości EQ w swoim DSP, zanim wyłączysz wyciszenie, zwłaszcza przy głośnikach wysokotonowych, i zaczynaj od niskiej głośności.

## Spis treści

- [Dla kogo i dlaczego](#dla-kogo-i-dlaczego)
- [Jak wygląda prawdziwa praca i synergia różnych AI](#jak-wygląda-prawdziwa-praca-i-synergia-różnych-ai)
- [Pierwsze kroki](#pierwsze-kroki)
- [Polecane modele, tryby i moje doświadczenie](#polecane-modele-tryby-i-moje-doświadczenie)
- [Pełna konfiguracja i FAQ](#pełna-konfiguracja-i-faq)
- [Co tu jest](#co-tu-jest)
- [Dzielenie się doświadczeniem](#dzielenie-się-doświadczeniem)
- [Wsparcie](#wsparcie)
- [Licencja](#licencja)

## Dla kogo i dlaczego

* **Dla kogo:** Dla tych, którzy budują dźwięk w samochodzie i uczą się tego rzemiosła. To twój egzoszkielet: on niesie wiedzę i doświadczenie rzemiosła, ty wnosisz uszy i ręce na DSP.
* **Dlaczego:** Strojenie to lawina: zbyt wiele metod, parametrów i reguł, by utrzymać je w głowie, i łatwo zanurzyć się w jednym szczególe i zgubić cały obraz. Skill jest twoim nawigatorem: trzyma wiedzę, wskazuje te kilka zmian, które naprawdę się liczą, i utrzymuje w polu widzenia kompromis między sceną a balansem tonalnym. Twoje ucho jest ostatecznym sędzią.

Obejmuje pełne strojenie: od nowego projektu przez zwrotnice, korekcję czasową, fazę, EQ kanałowy i sumaryczny oraz budowę sceny, aż po voicing pod własny gust — plus opcjonalne warstwy przestrzenne (komplementarny **center-fill** i różnicowy **rear-fill**, oba przepisy zweryfikowane w praktyce). Każda zmiana przechodzi przez pętlę recenzji **Generator ↔ Krytyk ↔ Arbiter**: jedno AI proponuje, drugie kwestionuje, ty decydujesz.

## Jak wygląda prawdziwa praca i synergia różnych AI

Trzy głosy: **ty** na miejscu odsłuchowym, **Claude** prowadzący proces, **Gemini** kwestionujący każdy ruch.

> **Ty (Arbiter):** Kontrabas trochę dudni. A kiedy przesunąłem opóźnienia na słuch, bas brzmiał lepiej — wprowadźmy moje wartości?
>
> **Claude (Generator):** Najpierw sprawdzone na świeżych pomiarach: twoje opóźnienia są już optymalne — twoje ucho polubiło coś innego. Prawdziwi winowajcy to dwa wąskie rezonanse drzwi i zbyt głośna lewa strona. Proponuję trzy chirurgiczne cięcia.
>
> **Gemini (Krytyk):** Sprzeciw: jedno z tych cięć siedzi w punkcie podziału zwrotnicy — może zepsuć tam sumowanie.
>
> **Claude:** Sprawdzone na pomiarach — ten podział faktycznie robi się *lepszy*. Ale twoja wątpliwość kazała mi spojrzeć głębiej i masz rację: to nie tylko midbas, średniak też jest tam zbyt głośny. Poprawiony plan: każdy głośnik dostaje własne cięcie.
>
> **Gemini:** Teraz zgoda.
>
> **Ty:** Wprowadzone. Dudnienie zniknęło… ale subwoofer teraz gra z tyłu!
>
> **Claude:** Mój błąd — dwa moje filtry nakładają się i tną głębiej niż zamierzone. Łagodzę jeden.
>
> **Ty:** Bas wrócił do przodu — ale siedzi nisko. Chcę go na szybie, tam gdzie był wcześniej.
>
> **Claude:** To stara wada podpierała obraz w górze. Nie przywrócimy tej wady — zamiast tego delikatne, symetryczne podbicie na EQ na obu średniakach, żeby wysokość wróciła bez przekosu.
>
> **Ty:** …Bas jest na masce! Zostawiam tak.

Około czterdziestu minut od „dudni" do „bas jest na masce" — problem, który zwykle pochłania tygodnie prób i błędów prowadzonych przez fora. Każdy uczestnik złapał coś, co przeoczyli inni, a pętla to wszystko rozwiązała. Pełna techniczna wersja, z każdą liczbą: [studium przypadku](case-study-mode-a-bass-2026-07-15.md).

**Matematyka pod maską** — biblioteka skryptów, która przetwarza ogromne zbiory danych lokalnie i nie spala tokenów modelu:

- **Mapa wad kabiny i instalacji jeszcze przed strojeniem** — zera drzwiowe, odbicia i „kieszenie" L/P, których żaden stereo EQ nie wypełni, są mapowane z pierwszych pomiarów — dzięki temu EQ jest planowany *wokół* kabiny, zamiast z nią walczyć;
- **Wieloskalowe czytanie krzywych** — każda krzywa jest czytana z trzech „odległości" (trend → kształt → drobne szczegóły), a każde znalezisko idzie do właściwego narzędzia: voicing, weryfikacja, chirurgiczne cięcie, albo „zostaw, to kabina";
- **Sumowanie fazowe odporne na jitter** — poprawki punktów podziału zwrotnic są oceniane pod małym dryfem opóźnienia/poziomu, żeby przetrwały rzeczywisty świat, zamiast wygrywać w jednym brzytwo-ostrym punkcie;
- **Modele filtrów zweryfikowane sprzętowo** — każdy proponowany EQ/all-pass jest symulowany na twoich *zmierzonych* odpowiedziach, zanim go wpiszesz;
- **Bramka „podatności na wzmocnienie" excess-phase** — odróżnia dołek, który można wypełnić, od zera interferencyjnego: żaden głośnik nie będzie walczył z fizyką;
- **Triangulacja przyjścia z czterech estymatorów** — cztery niezależne odczyty czasowe muszą się zgodzić, zanim jakiekolwiek opóźnienie zostanie ruszone;
- **Odczyt zniekształceń świadomy tonu podstawowego** — skoki THD są sprawdzane względem poziomu tonu podstawowego, więc zero pokojowe nigdy nie jest błędnie zdiagnozowane jako uszkodzony głośnik.

## Pierwsze kroki

Ten skill działa jako wtyczka do **Claude Code** (oficjalnego agenta terminalowego od Anthropic). Jeśli go jeszcze nie masz, w FAQ poniżej znajdziesz gotowe do wklejenia kroki instalacji na macOS/Windows; wymagana jest płatna subskrypcja Claude, a ścieżki kosztowe opisuje FAQ. Tam też przeczytasz, [dlaczego pełna sesja zużywa mniej tokenów, niż można by się spodziewać](FAQ.md#why-a-full-session-uses-fewer-tokens-than-youd-expect).

Uruchom poniższe polecenia w aktywnej sesji Claude Code **jedno po drugim** (nie kopiuj i nie wklejaj ich razem):

```bash
/plugin marketplace add ayukhno/autosound-tuning-skill
```

```bash
/plugin install autosound-tuning
```

```bash
/reload-plugins
```

*Następnie rozpocznij strojenie, mówiąc:* **"tune a new car from scratch"** (lub po polsku: *"nastrój nowe auto od zera"*).

> **Wyzwalanie — dodaj słowo o car audio.** Skill budzi się na to, *o co pytasz*, więc samo `resume` go nie uruchomi (zbyt ogólne — może dotyczyć dowolnego projektu). Dodaj jedno słowo domenowe: **„wróćmy do strojenia car audio"**, **„kontynuuj strojenie auta"**, **„jaki jest obecny stan DSP / zwrotnic"**. Tak samo przy starcie od zera: nazwij auto/audio, nie tylko „pomóż mi".

**Start z Gemini jako prowadzącym:** jeszcze nie tak szybko jak z Claude Code, przynajmniej na razie. Nie ma do tego instalatora wtyczki, ale najszybsza droga to skierować agentową sesję Gemini (Antigravity CLI lub dowolny Gemini z dostępem do plików i powłoki) na repozytorium i poprosić wprost:

> Clone https://github.com/ayukhno/autosound-tuning-skill, read `skills/autosound-tuning/SKILL.md`, and follow that method as your operating instructions for this session.

Więcej szczegółów w FAQ.

## Polecane modele, tryby i moje doświadczenie

Skill obsługuje dwa sposoby działania, uszeregowane według niezawodności. Wybierz w zależności od tego, jak ważne jest to konkretne strojenie i ile konfiguracji chcesz wykonać:

| Tryb | Konfiguracja | Niezawodność | Kompromis |
| :--- | :--- | :--- | :--- |
| **A: Claude + Gemini** | Claude prowadzi (Sonnet 5 / Fable 5), Gemini recenzuje (poziom Pro — obecnie 3.1 Pro — dla trudnych decyzji akustycznych, Flash dla rutyny) | Najwyższa | Dwie AI do skonfigurowania; wyłapuje więcej, wolniej przy każdej decyzji |
| **B: Solo (Claude lub Gemini)** | Jeden model prowadzi i sam siebie recenzuje; eskalacja do mocniejszego poziomu przy trudnych decyzjach o zwrotnicach (Claude Opus 4.8 lub wyższy poziom Gemini) | Niższa, zależy od wybranego modelu | Tylko jedna perspektywa; Gemini solo daje śmiałe, niestandardowe propozycje, ale trzeba ręcznie sprawdzić liczby |

**Moje własne doświadczenie jak dotąd** (to na razie tylko moje doświadczenie; gdy więcej osób nastroi z tym skillem, chcę, żeby to było doświadczenie społeczności, a nie tylko moje):

* **Claude prowadzi, Gemini recenzuje (tryb A):** stabilnie, ale porusza się małymi krokami, więc może wydawać się trochę wolne. Trzeba zapłacić przynajmniej za Claude. Darmowy Gemini też działa, ale czasem trafia na swoje limity. Jeszcze jedno, co zauważyłem: Sonnet jest niezawodny, ale ostrożny, i często zatrzymuje się, by pytać o rzeczy, które Opus zwykle rozstrzyga sam, szybciej. Za to Sonnet oszczędniej gospodaruje tokenami, więc rzadziej trafiasz na limity użycia.
* **Gemini prowadzi, z Claude lub mocniejszym modelem Gemini jako recenzentem:** dużo szybciej. Po dwóch pełnych rundach pomiarowych miałem już pierwszą działającą wersję. Ale później w sesji może zacząć halucynować lub gubić wcześniejsze decyzje, do tego stopnia, że chciałem wrócić do Claude. Nie próbowałem tego z darmowym Gemini, przez limity — żeby je znieść, potrzebne jest płatne konto rozliczeniowe Google Cloud ([ścieżki kosztowe w FAQ](FAQ.md#subscription-options-quotas--budgets-as-of-july-2026) opisują aktualne szczegóły depozytu i darmowych kredytów, które często się zmieniają). Jeśli i tak płacisz za dostęp do API, tryb A wychodzi ogólnie taniej.
* **Ręczna wersja krok po kroku (bez lokalnych skryptów):** działa, ale sam proces kopiuj-wklej jest nerwowo napięty. Trzeba uważać, żeby po drodze niczego nie zgubić. Po pełnej sesji z prawdziwą pamięcią między wiadomościami trudno się do tego zmusić z powrotem.
* **Który model jak dotąd jest najbardziej niezawodny jako prowadzący:** **Claude Opus** dawał dotychczas najstabilniejsze wyniki. **Sonnet 5** działa, ale jak dotąd wydaje się mniej pewny siebie w tej roli — warto na razie dokładniej sprawdzać jego decyzje. **Fable 5** dał najlepszy wynik ze wszystkich modeli: przeprowadził audyt i przebudował skill, jednocześnie prowadząc pełną sesję strojenia (zob. [audit-fable-2026-07-11.md](audit-fable-2026-07-11.md)), a potem poprowadził drugą pełną sesję w aucie według uproszczonych zasad — ten strój jest obecnie moim najlepszym wynikiem pod względem brzmienia. **Gemini** stracił trochę możliwości wraz ze wzrostem złożoności regulaminu; po tym, jak audyt go uprościł, Gemini 3.1 Pro znów sprawdziło się w roli **Krytyka**, a Gemini jako *prowadzący* pod nowymi zasadami wciąż nie jest zweryfikowany — czekamy na opinie społeczności.

## Pełna konfiguracja i FAQ

Potrzebujesz pomocy w konfiguracji Claude Code, uruchomieniu na **Windows**, konfiguracji **Gemini Critic** (w tym darmowego, opartego na przeglądarce środowiska przez **Google AI Studio**) lub wyborze mikrofonu?

Zobacz nasze **[FAQ.md](FAQ.md)**.

## Co tu jest

```
autosound-tuning-skill/        wtyczka Claude Code
└── skills/autosound-tuning/    skill
    ├── SKILL.md        punkt wejścia — mapa procesu, cykl życia sesji, role
    ├── references/     dokumenty na żądanie (fazy, diagnostyka, EQ, filtry, scena,
    │                   ścieżki testowe, REW API, Helix, metoda recenzji, intake …)
    ├── knowledge/      zgromadzone profile aut i DSP (cars/, dsp/)
    ├── rew_tool/       most do REW API, analiza, generowanie krzywych docelowych, wersjonowany stan
    ├── scripts/        wrappery kanału Krytyk/Doradca (Gemini, Claude, Codex)
    └── curves.html     wizualizator krzywych docelowych
```

▶ **[Otwórz wizualizator krzywych docelowych online](https://ayukhno.github.io/autosound-tuning-skill/curve-visualizer.html?lang=pl)** (lub otwórz `skills/autosound-tuning/curves.html` lokalnie) — przeciągnij własną krzywą lub standardową z [Nono Tuning Tool](https://nonotuningtool.com), kliknij prawym przyciskiem myszy na dowolny punkt wykresu, aby zobaczyć przewodnik charakterystyk częstotliwości, i porównuj krzywe obok siebie. To pojedynczy samodzielny plik (działa offline) — użyj **Zapisz jako** w przeglądarce, aby zachować własną kopię; wbudowane krzywe i import przeciągnięciem działają dalej.

Niezależna metoda recenzji (Krytyk/Doradca/Arbiter, anti-anchoring) jest dołączona jako `references/core/review-loop.md`; [studium przypadku](case-study-mode-a-bass-2026-07-15.md) pokazuje ją w akcji przy prawdziwym trudnym przypadku.

Osobna, bezstanowa wersja metody do czatu webowego, bez lokalnej instalacji, znajduje się w gałęzi [manual_step-by-step](https://github.com/ayukhno/autosound-tuning-skill/tree/manual_step-by-step).

## Dzielenie się doświadczeniem

Skill uczy się z każdego strojenia: zbiera ten feedback wprost w terminalu, gdy pracujesz, a nie przez formularz. Na zakończenie, gdy jesteś zadowolony z brzmienia, pyta, co pomogło, co było nie tak, i o każdą osobliwość DSP/auta, na którą trafiłeś. **Za twoją wyraźną zgodą** proponuje wtedy podzielić się *uogólnialnymi* wnioskami, aby rozwijać wspólną metodę i bibliotekę `knowledge/`.

Zbiera **tylko metodę i klasy sprzętu**: zachowanie kabiny, klasę DSP/sprzętu, które techniki zadziałały. **Nigdy danych osobowych, nigdy pełnych pomiarów;** widzisz dokładnie, co jest udostępniane, i decydujesz pozycja po pozycji. Potwierdzone wnioski trafiają do skilla z atrybucją.

## Wsparcie

Skill jest **darmowy i otwarty** (CC BY-SA) — i taki pozostanie; nic nie jest ukryte za płatnością. Jeśli pomógł i chcesz podziękować, są dwa dobrowolne kanały:

💜 **[GitHub Sponsors](https://github.com/sponsors/ayukhno)** · ☕ **[Skarbonka na Monobank](https://send.monobank.ua/jar/8wThVcodjm)** — jedno dotknięcie, bez konta; przyjmuje Apple Pay, Google Pay, Visa, Mastercard.

## Licencja

[CC BY-SA 4.0](LICENSE): używaj, adaptuj, udostępniaj; zachowaj pochodne otwarte i podaj autorstwo. To dzieło metodyczne/wiedzowe, więc share-alike utrzymuje zgromadzone doświadczenie społeczności otwartym.

Kod i skrypty (`rew_tool/`, `scripts/` oraz inne pliki .py/.sh) są na [licencji MIT](LICENSE-CODE). Zasoby stron trzecich wymieniono w [LICENSES/NOTICE.md](LICENSES/NOTICE.md).
