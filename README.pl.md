# Autosound Tuning Skill

🇬🇧 [English](README.md) · 🇩🇪 [Deutsch](README.de.md) · 🇵🇱 **Polski**

**W jednym zdaniu:** skill dla Claude, który pomaga stroić car-audio — czyta twoje pomiary z REW, analizuje je, podpowiada ustawienia i potrafi wgrać EQ z powrotem do REW.

- 📊 **Współpracuje z REW** przez jego API — pobiera pomiary, wgrywa z powrotem filtry EQ
- 🎯 **Zna rzemiosło** — krzywe docelowe, praktyki strojenia i wbudowany proces krok po kroku
- 🎧 **Ścieżki testowe** — na co zwracać uwagę i na której ścieżce (opisy, nie pliki audio)
- 🚗 **Uczy się twojego setupu** — gromadzi wiedzę o aucie i sprzęcie z perspektywy strojenia (tylko za twoją zgodą)

**Skill** dla [Claude](https://claude.com/claude-code) do strojenia car-audio DSP za pomocą [REW](https://www.roomeqwizard.com/) — od zupełnie nowego projektu (wywiad o sprzęcie + celach, wybór krzywej docelowej, weryfikacja instalacji) przez zwrotnice, korekcję czasową, fazę, korekcję EQ per-kanał i sumaryczną, imaging/scenę, aż po voicing pod gust klienta. Koduje **metodę** opartą na pomiarach (pętla recenzji Generator ↔ Krytyk ↔ Arbiter) plus rosnącą bibliotekę wypracowanych technik diagnostycznych.

Skill to **metoda, nie maszyna.** Żadne pomiary ani stany DSP konkretnego auta tu nie leżą — zostają w projekcie samego stroiciela. To repo dostarcza proces wielokrotnego użytku, działający z **dowolnym autem / dowolnym DSP**.

> Zbudowany i sprawdzony w zawodach na VW Passat B8 / Helix DSP Ultra S (zwycięstwo w AYA), ale specyfika auta/DSP jest wydzielona do profilu + biblioteki `knowledge/`, więc nowy projekt to tylko „wybierz dane wejściowe“.

## Co jest w środku

```
skills/
├── autosound-tuning/      główny skill
│   ├── SKILL.md           punkt wejścia (mapa procesu, cykl życia sesji, role)
│   ├── references/        dokumenty na żądanie: fazy, diagnostyka, wzorce EQ, typy filtrów,
│   │                      scena/głębia, zawody, ścieżki testowe, voicing-na-słuch,
│   │                      REW-API, specyfika Helix, intake, feedback
│   ├── knowledge/         zgromadzone profile aut i DSP (cars/, dsp/)
│   └── scripts/           przykładowy kanał Krytyka (opcjonalne narzędzia rigu)
└── review-loop/           skill siostrzany: orkiestracja niezależnej recenzji (niezależna od dostawcy)
```

Te dwa skille to **para** — `autosound-tuning` odwołuje się do `review-loop` po protokół recenzji. Zainstaluj oba.

## Pierwsze kroki — nowy w Claude Code / w terminalu?

Ten skill działa w **Claude Code**, narzędziu terminalowym. Jeśli używałeś tylko czatu desktop/web, oto jednorazowa konfiguracja.

**Dlaczego Claude Code (a nie aplikacja web / Cowork):** strojenie jest iteracyjne — pomiar → analiza → zmiana → ponowny pomiar — na danych tekstowych/liczbowych (eksporty CSV/pliki tekstowe z REW, konfiguracje DSP, logi iteracji). Terminal + git dają parsowanie, skrypty i pełną historię zmian. Cowork jest nastawiony na operacje na plikach w innych aplikacjach — tu zbędny.

**1. Zainstaluj Claude Code** (macOS / zsh; wymaga Node.js 18+ i płatnego planu Claude — Pro / Max / Team / Enterprise; darmowy plan nie wystarczy):
```bash
node --version                                   # Node.js 18 lub nowszy
mkdir -p ~/.npm-global && npm config set prefix '~/.npm-global'
echo 'export PATH="$HOME/.npm-global/bin:$PATH"' >> ~/.zshrc && source ~/.zshrc
npm install -g @anthropic-ai/claude-code
claude --version                                 # sprawdź
```

**2. Utwórz folder projektu i uruchom:**
```bash
mkdir ~/car-audio-setup && cd ~/car-audio-setup
claude                                            # pierwsze uruchomienie otworzy przeglądarkę do logowania
```

**3. Nie przekombinuj struktury.** Zacznij od pustego folderu. Wrzuć pierwszy eksport REW (`.txt`/`.csv`) taki, jaki jest, prowadź jeden plik notatek markdown (tylko dopisywanie), a foldery (`measurements/`, `configs/`, `eq-log/`) niech powstaną, gdy naprawdę będą potrzebne.

**4. Twoja pierwsza wiadomość = „krok 0“.** Opisz system w jednej wiadomości: auto + układ głośników (ile dróg, sub?), model DSP (Helix / Audison / inny), sprzęt pomiarowy (mikrofon, interfejs) oraz czy masz już pomiary, czy startujesz od sprzętu. Skill przejmie dalej — i **najpierw zapyta o preferowany język pracy** (angielski / Twój ojczysty, jeśli wspierany: EN · UK · DE · PL), aby rozmowa i pliki projektu powstały w nim. Następnie: intake → sprawdzenie toru sygnału → kalibracja mikrofonu → pierwszy sweep → …

(Potem zainstaluj sam skill — następna sekcja.)

## Wymagania

- **Claude Code** (lub claude.ai ze skillami).
- **REW** z włączonym serwerem API (`localhost:4735`), skalibrowany mikrofon pomiarowy.
- **Oprogramowanie Twojego DSP** i sposób na wgranie EQ (import z pliku idealny; dla 30+ DSP bez importu zobacz [REW-EQ-CopyPaste-Assistant](https://github.com/IvanBakhmutov/REW-EQ-CopyPaste-Assistant)).
- **Opcjonalnie:** drugi model AI jako „Krytyk“ (dowolny dostawca — role są niezależne od dostawcy). Bez niego rolę recenzenta pełni człowiek; proces nadal działa.

## Instalacja

**Najprościej — niech Claude zainstaluje za Ciebie.** Otwórz Claude Code i po prostu poproś, np.:

> *„Sklonuj https://github.com/ayukhno/autosound-tuning-skill do folderu tymczasowego, a potem skopiuj dwa **wewnętrzne** foldery skilli — `skills/autosound-tuning` i `skills/review-loop` — do mojego `~/.claude/skills/` na poziomie użytkownika, tak aby `SKILL.md` każdego skilla trafił bezpośrednio do `~/.claude/skills/<nazwa>/SKILL.md`. Nie klonuj całego repo do folderu skilli.“*

Claude umieści **oba** skille (to para) tam, gdzie wybierzesz:

- **Poziom użytkownika — `~/.claude/skills/`** *(zalecane)*: dostępny w **każdym** folderze, w którym otworzysz Claude Code. Wybierz, jeśli będziesz stroić więcej niż jedno auto lub chcesz mieć go zawsze pod ręką.
- **Poziom projektu — `<twoj-projekt>/.claude/skills/`**: tylko w tym jednym projekcie. Wybierz, by repo jednego auta było samowystarczalne.

> ⚠️ **Częsty błąd instalacji:** nie klonuj repo *do* `~/.claude/skills/autosound-tuning/`. To zagnieżdża `SKILL.md` o jeden poziom za głęboko (`…/autosound-tuning/skills/autosound-tuning/SKILL.md`) i Claude Code zgłasza **`Unknown skill: autosound-tuning`** (albo w ogóle nie proponuje skilla). Zawsze kopiuj **wewnętrzne** foldery `skills/*`, tak aby `SKILL.md` był *bezpośrednio* w folderze skilla.

**Albo ręcznie:**
```bash
git clone https://github.com/ayukhno/autosound-tuning-skill.git
# poziom użytkownika (dostępne wszędzie) — skopiuj WEWNĘTRZNE foldery skilli:
cp -R autosound-tuning-skill/skills/autosound-tuning ~/.claude/skills/
cp -R autosound-tuning-skill/skills/review-loop      ~/.claude/skills/
# …albo poziom projektu: te same dwa foldery do  twoj-projekt/.claude/skills/

# weryfikacja — każda linia musi wypisać ścieżkę (SKILL.md jest BEZPOŚREDNIO w folderze skilla):
ls ~/.claude/skills/autosound-tuning/SKILL.md
ls ~/.claude/skills/review-loop/SKILL.md
```

**Po instalacji uruchom nową sesję Claude Code** — skille są ładowane przy starcie.

**Rozwiązywanie problemów — `Unknown skill` / skill się nie uruchamia:** prawie zawsze to powyższe zagnieżdżenie. Jeśli `ls ~/.claude/skills/autosound-tuning/SKILL.md` zawodzi, ale `…/autosound-tuning/skills/autosound-tuning/SKILL.md` istnieje, sklonowałeś całe repo do folderu skilla. Napraw to, potem zrestartuj Claude Code:
```bash
mv ~/.claude/skills/autosound-tuning ~/.claude/skills/autosound-tuning-repo
cp -R ~/.claude/skills/autosound-tuning-repo/skills/autosound-tuning ~/.claude/skills/
cp -R ~/.claude/skills/autosound-tuning-repo/skills/review-loop      ~/.claude/skills/
rm -rf ~/.claude/skills/autosound-tuning-repo
```

Następnie otwórz Claude Code w projekcie i powiedz np. *„nastrój nowe auto od zera“* / *"tune a new car from scratch"* — skill zacznie od **intake** (`references/project-intake.md`): quickstart, wywiad o sprzęcie + celach, wybór krzywej docelowej (bez domyślnej — wybierana z Tobą), weryfikacja instalacji i wygenerowanie plików projektu.

## Podziel się doświadczeniem

Skill **uczy się z każdego strojenia — i zbiera ten feedback wprost w terminalu, podczas pracy, a nie przez formularz do wypełnienia.** Na zakończenie (Faza 7) uruchamia krótki rytuał: pyta, co naprawdę pomogło, co było nie tak, i o każdą osobliwość DSP/auta — a następnie, **za Twoją wyraźną zgodą**, proponuje udostępnić *uogólnialne* wnioski.

**Po co jest końcowa ankieta i co zbiera:** by rozwijać wspólną metodę + bibliotekę `knowledge/`. Zbiera **tylko metodę + klasy sprzętu** — zachowanie nadwozia/kabiny, DSP/procesor i klasę sprzętu, oraz które techniki zadziałały. **Nigdy danych osobowych, nigdy pełnych pomiarów.** Widzisz dokładnie, co zostałoby udostępnione, i decydujesz pozycja po pozycji.

Potwierdzone wnioski trafiają do skilla i profili `knowledge/` aut/DSP (z atrybucją). Wskazówki sprzeczne z istniejącymi ustaleniami są zachowywane jako *warianty*, nie usuwane — inna kabina może je uczynić słusznymi.

*(Wolisz GitHub? Nadal możesz otworzyć [zgłoszenie field-feedback](../../issues/new?template=field-feedback.md) — ta sama zasada: tylko metoda/klasy sprzętu.)*

## Wsparcie

Skill jest **darmowy i otwarty** (CC BY-SA) i taki pozostanie — nic nie jest zablokowane za płatnością. Jeśli pomógł ci dostroić system i chcesz podziękować, jest **dobrowolna skarbonka**, bez żadnej presji:

☕ **[Wesprzyj ten skill — skarbonka Monobank](https://send.monobank.ua/jar/8wThVcodjm)** 🤝

Jedno dotknięcie, bez konta; strona przyjmuje też karty zagraniczne (Apple/Google Pay, Visa/Mastercard).

## Licencja

[CC BY-SA 4.0](LICENSE) — używaj, adaptuj, udostępniaj; zachowaj pochodne otwarte i podaj autorstwo. To dzieło metodyczne/wiedzowe, więc share-alike utrzymuje zgromadzone doświadczenie społeczności otwartym.
