# Autosound Tuning Skill

🇬🇧 [English](README.md) · 🇩🇪 [Deutsch](README.de.md) · 🇵🇱 **Polski** · 🇺🇦 [Українська](README.uk.md) · [FAQ](FAQ.md)

**W jednym zdaniu:** skill dla Claude, który prowadzi cię do czystego, przejrzystego, zrównoważonego brzmienia w *twoim* aucie. Wnosi całe rzemiosło do twojego konkretnego zestawu, czyta twoje pomiary z REW i pomaga wybrać każdą zmianę.

- **Współpracuje z REW**: pobiera pomiary przez API, zapisuje obliczone filtry EQ z powrotem w REW, skąd eksportujesz je do swojego DSP
- **Zna rzemiosło**: krzywe docelowe, praktyki strojenia, proces krok po kroku
- **Ścieżki testowe**: czego słuchać i na której ścieżce (opisy, nie audio)
- **Uczy się twojego zestawu**: gromadzi wiedzę o aucie i sprzęcie, tylko za twoją zgodą

> [!CAUTION]
> AI może pomylić się w liczbach. Zawsze sprawdzaj częstotliwości zwrotnic, nachylenia filtrów i wartości EQ w swoim DSP, zanim wyłączysz wyciszenie, zwłaszcza przy głośnikach wysokotonowych, i zaczynaj od niskiej głośności.

## Dla kogo i dlaczego

* **Dla kogo:** Dla tych, którzy budują dźwięk w samochodzie i uczą się tego rzemiosła. To twój egzoszkielet (napędzany twoim słuchem i działaniami tam, gdzie nie ma bezpośrednich interfejsów oprogramowania), który zarządza wiedzą i doświadczeniem, żebyś mógł nastroić dźwięk swojego auta.
* **Dlaczego:** Strojenie to lawina: zbyt wiele metod, parametrów i reguł, by utrzymać je w głowie, i łatwo zanurzyć się w jednym szczególe i zgubić cały obraz. Skill jest twoim nawigatorem: trzyma wiedzę, wskazuje te kilka zmian, które naprawdę się liczą, i utrzymuje w polu widzenia kompromis między sceną a balansem tonalnym. Twoje ucho jest ostatecznym sędzią.

Obejmuje pełne strojenie, od nowego projektu przez zwrotnice, korekcję czasową, fazę, EQ kanałowy i sumaryczny, budowę sceny, aż po voicing pod własny gust, sterowane pętlą recenzji **Generator ↔ Krytyk ↔ Arbiter**.

## Pierwsze kroki

Ten skill działa jako wtyczka do **Claude Code** (oficjalnego agenta terminalowego od Anthropic). Jeśli go jeszcze nie masz, w FAQ poniżej znajdziesz gotowe do wklejenia kroki instalacji na macOS/Windows (wymagana jest płatna subskrypcja Claude; ścieżki kosztowe też w FAQ).

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

## Polecane modele, tryby i moje doświadczenie

Skill obsługuje dwa sposoby działania, uszeregowane według niezawodności. Wybierz w zależności od tego, jak ważne jest to konkretne strojenie i ile konfiguracji chcesz wykonać:

| Tryb | Konfiguracja | Niezawodność | Kompromis |
| :--- | :--- | :--- | :--- |
| **A: Claude + Gemini** | Claude Sonnet 5 prowadzi, Gemini recenzuje (2.5 Pro dla trudnych decyzji akustycznych, 2.5 Flash dla rutyny) | Najwyższa | Dwie AI do skonfigurowania; wyłapuje więcej, wolniej przy każdej decyzji |
| **B: Solo (Claude lub Gemini)** | Jeden model prowadzi i sam siebie recenzuje; eskalacja do mocniejszego poziomu przy trudnych decyzjach o zwrotnicach (Claude Opus 4.8 lub wyższy poziom Gemini) | Niższa, zależy od wybranego modelu | Tylko jedna perspektywa; Gemini solo daje śmiałe, niestandardowe propozycje, ale trzeba ręcznie sprawdzić liczby |

**Moje własne doświadczenie jak dotąd** (to na razie tylko moje doświadczenie; gdy więcej osób nastroi z tym skillem, chcę, żeby to było doświadczenie społeczności, a nie tylko moje):

* **Claude prowadzi, Gemini recenzuje (tryb A):** stabilnie, ale porusza się małymi krokami, więc może wydawać się trochę wolne. Trzeba zapłacić przynajmniej za Claude. Darmowy Gemini też działa, ale czasem trafia na swoje limity. Jeszcze jedno, co zauważyłem: Sonnet jest niezawodny, ale ostrożny, i często zatrzymuje się, by pytać o rzeczy, które Opus zwykle rozstrzyga sam, szybciej.
* **Gemini prowadzi, z Claude lub mocniejszym modelem Gemini jako recenzentem:** dużo szybciej. Po dwóch pełnych rundach pomiarowych miałem już pierwszą działającą wersję. Ale później w sesji może zacząć halucynować lub gubić wcześniejsze decyzje, do tego stopnia, że chciałem wrócić do Claude. Nie próbowałem tego z darmowym Gemini, przez limity. Darmowy poziom Gemini ma twarde limity zapytań; żeby je znieść, potrzebne jest płatne konto rozliczeniowe Google Cloud, do którego aktywacji trzeba wpłacić minimum $10, a dla niektórych kart (np. ukraińskich) jest to realne obciążenie, nie tylko blokada środków. Nowe konta dostają przy tym obecnie też $300 darmowego kredytu, który wystarczy na całe strojenie, ale ten kredyt wygasa po 3 miesiącach i jest to bieżąca promocja, a nie gwarantowany warunek na przyszłość. Jeśli i tak płacisz za dostęp do API, tryb A wychodzi ogólnie taniej.
* **Ręczna wersja krok po kroku (bez lokalnych skryptów):** działa, ale sam proces kopiuj-wklej jest nerwowo napięty. Trzeba uważać, żeby po drodze niczego nie zgubić. Po pełnej sesji z prawdziwą pamięcią między wiadomościami trudno się do tego zmusić z powrotem.

**Start z Gemini jako prowadzącym:** jeszcze nie tak szybko jak z Claude Code, przynajmniej na razie. Nie ma do tego instalatora wtyczki, ale najszybsza droga to skierować agentową sesję Gemini (Antigravity CLI lub dowolny Gemini z dostępem do plików i powłoki) na repozytorium i poprosić wprost:

> Clone https://github.com/ayukhno/autosound-tuning-skill, read `skills/autosound-tuning/SKILL.md`, and follow that method as your operating instructions for this session.

Więcej szczegółów w FAQ.

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

Niezależna metoda recenzji (Krytyk/Doradca/Arbiter, anti-anchoring) jest dołączona jako `references/core/review-loop.md`.

Osobna, bezstanowa wersja metody do czatu webowego, bez lokalnej instalacji, znajduje się w gałęzi [manual_step-by-step](https://github.com/ayukhno/autosound-tuning-skill/tree/manual_step-by-step).

## Dzielenie się doświadczeniem

Skill uczy się z każdego strojenia: zbiera ten feedback wprost w terminalu, gdy pracujesz, a nie przez formularz. Na zakończenie, gdy jesteś zadowolony z brzmienia, pyta, co pomogło, co było nie tak, i o każdą osobliwość DSP/auta, na którą trafiłeś. **Za twoją wyraźną zgodą** proponuje wtedy podzielić się *uogólnialnymi* wnioskami, aby rozwijać wspólną metodę i bibliotekę `knowledge/`.

Zbiera **tylko metodę i klasy sprzętu**: zachowanie kabiny, klasę DSP/sprzętu, które techniki zadziałały. **Nigdy danych osobowych, nigdy pełnych pomiarów;** widzisz dokładnie, co jest udostępniane, i decydujesz pozycja po pozycji. Potwierdzone wnioski trafiają do skilla z atrybucją.

## Wsparcie

Skill jest **darmowy i otwarty** (CC BY-SA). Jeśli pomógł i chcesz podziękować, jest **dobrowolna skarbonka**:

☕ **[Wesprzyj ten skill na Monobank](https://send.monobank.ua/jar/8wThVcodjm)**

Jedno dotknięcie, bez konta; strona przyjmuje też karty zagraniczne (Apple/Google Pay, Visa/Mastercard).

## Licencja

[CC BY-SA 4.0](LICENSE): używaj, adaptuj, udostępniaj; zachowaj pochodne otwarte i podaj autorstwo. To dzieło metodyczne/wiedzowe, więc share-alike utrzymuje zgromadzone doświadczenie społeczności otwartym.
