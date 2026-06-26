# Autosound Tuning Skill

🇬🇧 [English](README.md) · 🇩🇪 [Deutsch](README.de.md) · 🇵🇱 **Polski** · 🇺🇦 [Українська](README.uk.md)

**W jednym zdaniu:** skill dla Claude, który pomaga stroić car-audio — czyta twoje pomiary z REW, analizuje je, podpowiada ustawienia i potrafi wgrać EQ z powrotem do REW.

- 📊 **Współpracuje z REW** przez API — pobiera pomiary, wgrywa filtry EQ z powrotem
- 🎯 **Zna rzemiosło** — krzywe docelowe, praktyki strojenia, proces krok po kroku
- 🎧 **Ścieżki testowe** — czego słuchać i na której ścieżce (opisy, nie audio)
- 🚗 **Uczy się twojego zestawu** — gromadzi wiedzę o aucie i sprzęcie, tylko za twoją zgodą

Obejmuje pełne strojenie — od nowego projektu (wywiad o sprzęcie + celach, wybór krzywej docelowej, kontrola montażu) przez zwrotnice, korekcję czasową, fazę, EQ kanałowy i sumaryczny oraz budowę sceny, aż po voicing pod własny gust — sterowane pętlą recenzji Generator ↔ Krytyk ↔ Arbiter. To **metoda, nie maszyna**: pomiary żadnego auta ani stan DSP tu nie są przechowywane (zostają w twoim projekcie), więc działa z **dowolnym autem / dowolnym DSP**.

> Zbudowany i sprawdzony w boju na VW Passat B8 / Helix DSP Ultra S (wygrana na zawodach AYA); specyfika auta/DSP jest wydzielona do profilu + biblioteki `knowledge/`, więc nowy projekt to po prostu „wybierz dane wejściowe”.

## Co tu jest

```
autosound-tuning-skill/        wtyczka Claude Code
└── skills/autosound-tuning/    skill
    ├── SKILL.md        punkt wejścia — mapa procesu, cykl życia sesji, role
    ├── references/     dokumenty na żądanie (fazy, diagnostyka, EQ, filtry, scena,
    │                   ścieżki testowe, REW API, Helix, metoda recenzji, intake …)
    ├── knowledge/      zgromadzone profile aut i DSP (cars/, dsp/)
    └── scripts/        przykładowe narzędzia kanału Krytyka (opcjonalne)
```

Jeden skill — niezależna metoda recenzji (Krytyk/Doradca/Arbiter, anti-anchoring) jest dołączona jako `references/review-loop.md`.

## Pierwsze kroki — nowy w Claude Code?

Ten skill działa w **Claude Code**, narzędziu w terminalu. Strojenie jest iteracyjne (mierz → analizuj → zmień → zmierz ponownie) na danych tekstowych/liczbowych, więc terminal + git — parsowanie, skrypty, pełna historia zmian — pasują znacznie lepiej niż aplikacja webowa.

**1. Zainstaluj Claude Code** (macOS / zsh; wymaga Node.js 18+ i płatnego planu Claude — Pro / Max / Team / Enterprise):
```bash
node --version                                   # Node.js 18 lub nowszy
mkdir -p ~/.npm-global && npm config set prefix '~/.npm-global'
echo 'export PATH="$HOME/.npm-global/bin:$PATH"' >> ~/.zshrc && source ~/.zshrc
npm install -g @anthropic-ai/claude-code
claude --version                                 # weryfikacja
```

**2. Utwórz folder projektu i uruchom:**
```bash
mkdir ~/car-audio-setup && cd ~/car-audio-setup
claude                                            # pierwsze uruchomienie otworzy przeglądarkę do logowania
```

**3. Zacznij prosto.** Pusty folder, pierwszy eksport REW wrzucony bez zmian, jeden dopisywany log notatek — pozwól podfolderom pojawić się, gdy naprawdę będą potrzebne.

**4. Twoja pierwsza wiadomość = „krok 0”.** Opisz swój system: auto + układ głośników (ile dróg, sub?), model DSP, sprzęt pomiarowy, i czy masz już pomiary. Resztę przejmuje skill — i **najpierw pyta o preferowany język pracy** (EN · UK · DE · PL), aby rozmowa i pliki projektu powstawały w nim.

## Wymagania

- **Claude Code** (lub claude.ai ze skillami).
- **REW** z włączonym serwerem API (`localhost:4735`) i skalibrowany mikrofon.
- **Oprogramowanie twojego DSP** + sposób na wgranie EQ (import pliku idealnie; dla 30+ DSP bez importu zob. [REW-EQ-CopyPaste-Assistant](https://github.com/IvanBakhmutov/REW-EQ-CopyPaste-Assistant)).
- **Opcjonalnie:** drugi model AI jako „Krytyk” (dowolny dostawca). Bez niego recenzję robi człowiek; proces nadal działa.

## Instalacja

Zainstaluj jako **wtyczkę Claude Code** — jeden marketplace, jedna komenda, bez ręcznego kopiowania:
```
/plugin marketplace add ayukhno/autosound-tuning-skill
/plugin install autosound-tuning
```
**Następnie uruchom nową sesję Claude Code** (wtyczki ładują się przy starcie) i powiedz np. *„nastrój nowe auto od zera”* — skill zaczyna od **intake'u**: szybki start, wywiad o sprzęcie + celach, wybór krzywej docelowej (wybierany z tobą), kontrola montażu, generowanie plików projektu. Aktualizacja później: `/plugin update autosound-tuning`.

*(Wolisz ręczny checkout? Sklonuj repo i zrób symlink **wewnętrznego** folderu `skills/autosound-tuning` do `~/.claude/skills/`. ⚠️ Nie klonuj całego repo *do* `~/.claude/skills/autosound-tuning/` — `SKILL.md` trafi wtedy o poziom za głęboko i Claude zgłosi `Unknown skill`.)*

## Dzielenie się doświadczeniem

Skill **uczy się z każdego strojenia — i zbiera ten feedback wprost w terminalu, gdy pracujesz, a nie przez formularz.** Na zakończenie (Faza 7) pyta, co pomogło, co było nie tak, i o każdą osobliwość DSP/auta, na którą trafiłeś — następnie, **za twoją wyraźną zgodą**, proponuje podzielić się *uogólnialnymi* wnioskami (aby rozwijać wspólną metodę + bibliotekę `knowledge/`).

Zbiera **tylko metodę + klasy sprzętu** — zachowanie kabiny, klasę DSP/sprzętu, które techniki zadziałały. **Nigdy danych osobowych, nigdy pełnych pomiarów;** widzisz dokładnie, co jest udostępniane, i decydujesz pozycja po pozycji. Potwierdzone wnioski trafiają do skilla z atrybucją; sprzeczne wskazówki są zachowywane jako *warianty*, nie usuwane. *(Wolisz GitHub? Otwórz [zgłoszenie field-feedback](../../issues/new?template=field-feedback.md) — ta sama zasada.)*

## Wsparcie

Skill jest **darmowy i otwarty** (CC BY-SA) i taki pozostanie — nic nie jest zablokowane za płatnością. Jeśli pomógł i chcesz podziękować, jest **dobrowolna skarbonka**, bez żadnej presji:

☕ **[Wesprzyj ten skill — skarbonka Monobank](https://send.monobank.ua/jar/8wThVcodjm)** 🤝

Jedno dotknięcie, bez konta; strona przyjmuje też karty zagraniczne (Apple/Google Pay, Visa/Mastercard).

## Licencja

[CC BY-SA 4.0](LICENSE) — używaj, adaptuj, udostępniaj; zachowaj pochodne otwarte i podaj autorstwo. To dzieło metodyczne/wiedzowe, więc share-alike utrzymuje zgromadzone doświadczenie społeczności otwartym.
