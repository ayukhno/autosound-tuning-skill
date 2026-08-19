# Autosound Tuning Skill

🇬🇧 [English](README.md) · 🇩🇪 [Deutsch](README.de.md) · 🇵🇱 **Polski** · 🇺🇦 [Українська](README.uk.md) · ❓ [FAQ](FAQ.md) · <img src="assets/icons/roadmap.svg" width="14" height="14" valign="middle" alt="Roadmap" /> [Roadmap (EN, szkic)](ROADMAP.md)

**W jednym zdaniu:** asystent AI do strojenia dźwięku w twoim aucie. Czyta twoje pomiary z REW i
prowadzi cię przez zwrotnice, wyrównanie czasowe, fazę i EQ — po jednej sprawdzonej zmianie naraz.

- **Działa z REW**: pobiera twoje pomiary przez API i zapisuje wyliczone filtry EQ z powrotem do
  REW, skąd je eksportujesz
- **Najpierw diagnozuje, potem naprawia**: znajduje w pierwszych pomiarach odbicia kabiny, wycięcia
  i zniekształcenia głośników, zanim zaproponuje choć jedną zmianę
- **Nigdy nie dotyka twojego procesora**: w aucie nic się nie zmienia, dopóki sam tego nie wpiszesz.
  Nie znaczy to jednak przepisywania wszystkiego ręcznie: REW eksportuje twój EQ jako plik, który
  Helix PC-Tool importuje za jednym razem, a dla procesorów bez importu pliku jest
  [pomocnik kopiuj-wklej](https://github.com/IvanBakhmutov/REW-EQ-CopyPaste-Assistant) — Musway, ESX,
  Zapco
- **Zna rzemiosło**: krzywe docelowe, kolejność „najpierw faza, potem EQ", proces krok po kroku i to,
  którego utworu testowego słuchać i po co
- **Uczy się twojego zestawu**: gromadzi wiedzę o aucie i sprzęcie, wyłącznie za twoją zgodą

Strojone tą metodą, moje własne auto zdobyło w **2026 dwa pierwsze miejsca w klasie na zawodach
AYA**: Einsteiger 5000 w maju — z analizą wykresów i pracą z Gemini, z której później wyrósł ten
skill — a potem Amateur 5000 w lipcu, już samym skillem i własnym słuchem.

<p align="left">
  <img src="assets/awards/aya-may26-einsteiger5000.jpg" width="100" alt="AYA May 2026 Einsteiger 5000">
  &nbsp;&nbsp;&nbsp;
  <img src="assets/awards/aya-jul26-amateur5000.jpg" width="100" alt="AYA Jul 2026 Amateur 5000">
</p>

> [!CAUTION]
> AI potrafi pomylić się w liczbach. Zawsze sprawdź częstotliwości zwrotnic, nachylenia i wartości
> EQ w swoim DSP, zanim odciszysz — zwłaszcza na głośnikach wysokotonowych — i zacznij cicho.

> [!NOTE]
> **Wolisz okno od terminala?** [TCC](https://github.com/ayukhno/autosound-tcc), towarzysząca
> aplikacja desktopowa, prowadzi tę samą metodę w oknie: drzewo DSP, twoje krzywe z REW, plan i AI w
> bocznym panelu. Jedna linia poniżej instaluje ją również, o ile nie powiesz inaczej. Jest młoda —
> sprawdzoną drogą jest metoda w terminalu.

## Spis treści

- [Dla kogo to jest](#dla-kogo-to-jest)
- [Czego potrzebujesz](#czego-potrzebujesz)
- [Jak zacząć](#jak-zacząć)
- [Jak naprawdę brzmi sesja](#jak-naprawdę-brzmi-sesja)
- [Które modele wybrać](#które-modele-wybrać)
- [Matematyka pod maską](#matematyka-pod-maską)
- [Co tu jest](#co-tu-jest)
- [Podziel się doświadczeniem](#podziel-się-doświadczeniem)
- [Wsparcie](#wsparcie)
- [Licencja](#licencja)

## Dla kogo to jest

Dla każdego, kto buduje dźwięk we własnym aucie i uczy się rzemiosła. To twój egzoszkielet: on niesie
wiedzę i doświadczenie, ty wnosisz uszy i ręce na DSP.

Strojenie to lawina. Metod, parametrów i reguł kciuka jest więcej, niż ktokolwiek mieści w głowie, i
łatwo zanurkować w jeden szczegół, gubiąc całość. Skill trzyma wiedzę, wskazuje te kilka zmian, które
naprawdę ważą, i pilnuje kompromisu między sceną a balansem tonalnym. Ostatnim sędzią jest twoje
ucho.

Obejmuje pełne strojenie: od nowego projektu przez zwrotnice, wyrównanie czasowe, fazę, EQ na kanał i
sumaryczne, po budowę sceny i strojenie pod własny gust — plus opcjonalne warstwy przestrzenne
(komplementarny **center-fill** i różnicowy **rear-fill**, oba sprawdzone w praktyce). Każda zmiana
przechodzi przez pętlę **Generator ↔ Krytyk ↔ Arbiter**: jedna AI proponuje, druga podważa, ty
decydujesz.

## Czego potrzebujesz

**Czysta maszyna to normalny przypadek.** Instalator poniżej przynosi ze sobą Claude Code, Pythona,
metodę, aplikację desktopową i recenzenta Gemini. Nic nie musi być zainstalowane wcześniej.

Trzech rzeczy nie załatwi za ciebie, bo są twoje:

- **[REW](https://www.roomeqwizard.com/)** z włączonym API. Wszystko, co skill wie o twoim aucie,
  przychodzi tą drogą. Na macOS: otwórz *Preferences → API*, zaznacz **Start the API when REW
  starts** i naciśnij **Start server**; panel pokaże wtedy *"API server is running on port 4735"*, a
  od tej pory API wstaje razem z REW. Na Windows tego pola nie ma, więc instalator kładzie na
  pulpicie skrót **REW (API on)**, który uruchamia REW z włączonym API — uruchamiaj REW z niego.
- **Skalibrowany mikrofon pomiarowy i DSP, do którego można wpisywać wartości.** Każdy procesor się
  nadaje. Dla fazy i czasu XLR z fizyczną pętlą zwrotną bije USB:
  [dlaczego, w FAQ](FAQ.md#measuring-phase--time-alignment-umik-1-vs-xlr-microphones).
- **Płatna subskrypcja Claude (Pro albo Max).** Zobacz
  [plany i to, ile kosztuje sesja](FAQ.md#subscription-options-quotas--budgets-as-of-july-2026).

Druga AI jako recenzent jest opcjonalna — i to właśnie z niej płynie większość korzyści. Instalator
przynosi do tego `agy` od Google i proponuje logowanie na końcu; bez recenzenta skill pracuje sam i
mówi ci o tym, a dodać go można później.

**Konto GitHub warto mieć i nie jest potrzebne do instalacji.** Instalacja nigdzie cię nie loguje,
oba repozytoria są publiczne. Powodem, by mieć konto, jest twój własny projekt — i nie chodzi o surowe
pomiary: te ważą po 16–112 MB, zostają na twoim dysku, a gdybyś ich kiedyś potrzebował, zmierzyłbyś
ponownie. Warto zachować wszystko, co *ustaliłeś*: rejestr każdej zwrotnicy, opóźnienia, wzmocnienia i
filtra, dziennik drogi do tego, kopie konfiguracji DSP, które odtwarzają strojenie, krzywe docelowe i
notatki z analiz. Małe pliki, których żadne ponowne mierzenie nie przywróci. Instalator pyta, czy
kopiować je do **prywatnego** repozytorium GitHub, i jeśli tak — instaluje `gh` i loguje go; sama
kopia powstaje wtedy, gdy powiesz AI, żeby zarchiwizowała projekt — ona wie, co zostaje poza. Darmowe
konto wystarczy.

## Jak zacząć

Jedna linia instaluje wszystko: Claude Code, metodę,
[aplikację TCC](https://github.com/ayukhno/autosound-tcc), Gemini jako recenzenta i `omp` — to on
pozwala aplikacji oferować modele inne niż Claude. Pokazuje, co już jest na maszynie, wypisuje
wszystko, co pobierze i skąd, pyta raz — a potem idzie sam przez dziesięć do dwudziestu minut. Jedyna
przerwa przychodzi tuż po tym pytaniu: na Macu, na którym nigdy nie programowano, poprosi raz o hasło
do Maca dla Apple Command Line Tools; na Windows pokaże jedno okno uprawnień — dla Gita. Na końcu
zaloguje cię w przeglądarce: najpierw Claude (to obowiązkowe), potem recenzent i GitHub, jeśli ich
chcesz — każdy na Enter albo później.

**macOS** — otwórz Terminal (⌘-Spacja, wpisz "terminal", Enter) i wklej:

```sh
curl -fsSL https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/main/install.sh | bash
```

**Windows** — otwórz PowerShell (Start, wpisz "powershell", Enter) i wklej:

```powershell
irm https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/main/install.ps1 | iex
```

Żeby coś pominąć: `--terminal` (bez aplikacji), `--no-reviewer`, `--no-github` albo `--no-omp` — na
macOS po `bash -s --`; na Windows te same cztery jako `-Terminal`, `-NoReviewer`, `-NoGitHub`,
`-NoOmp` w formie `& ([scriptblock]::Create((irm <ten url>))) -Terminal`. Ponowne uruchomienie tej
samej linii **aktualizuje** wszystko; `--uninstall` / `-Uninstall` usuwa to, co instalator założył —
i nigdy folderu projektu.

Potem start. Zrób folder dla auta — wszystko o tym aucie mieszka w nim, więc kopia folderu to kopia
całego strojenia — i otwórz go na jeden z dwóch sposobów:

**W terminalu.** Otwórz *nowe* okno terminala (to, z którego instalowałeś, nie widzi świeżo
zainstalowanych rzeczy), a potem:

```sh
mkdir -p ~/Autosound/my-car && cd ~/Autosound/my-car
```

```sh
claude
```

*Następnie zacznij strojenie słowami:* **„nastrójmy nowe auto od zera"**.

**W aplikacji.** Kliknij dwukrotnie **Autosound TCC** na pulpicie, *Browse…* do folderu (nowy, pusty
jest właściwy), wybierz modele — Claude Opus (SDK) jako *AI main*, Gemini Pro (High) jako *AI critic*
— naciśnij *Open* i powiedz to samo w panelu po prawej, w dowolnym języku:
*„nastrójmy to auto od zera"*.

To jeden projekt, nie dwa: metoda zapisuje pliki projektu, aplikacja je czyta — możesz jednego dnia
pracować w oknie, a następnego w terminalu.

> **Wyzwalanie: dodaj słowo o car audio.** Skill budzi się od *tego, o co pytasz*, więc samo `resume`
> go nie uruchomi — mogłoby dotyczyć dowolnego projektu. Dodaj jedno słowo z dziedziny:
> **„wróćmy do strojenia car audio"**, **„kontynuujmy strojenie auta"**, **„jaki jest teraz stan DSP /
> zwrotnic"** — albo we własnym języku („продовжити тюн авто", „Auto-DSP weiter einmessen", "resume
> my car-audio tune"). Tak samo przy starcie od zera: nazwij auto albo dźwięk, nie tylko „pomóż mi".

> **Model i poziom wysiłku ustaw PRZED pierwszą wiadomością.** Są stałe dla sesji i nic ich później
> nie podniesie. Stan na sierpień 2026: **Claude Opus na `xhigh`**, z **Gemini Pro (High)** jako
> recenzentem. [Dlaczego tańsze kombinacje zawodzą po cichu](#które-modele-wybrać).

<details>
<summary>Inne drogi: Gemini za kierownicą albo wtyczka 2.x, którą możesz już mieć</summary>

**Z Gemini za kierownicą.** Instalatora wtyczki nie ma, ale możesz skierować agentową sesję Gemini
(Antigravity CLI albo dowolne Gemini z dostępem do plików i powłoki) na to repozytorium:

> Clone https://github.com/ayukhno/autosound-tuning-skill, read `skills/autosound-tuning/SKILL.md`,
> and follow that method as your operating instructions for this session.

**Masz już zainstalowaną wtyczkę 2.x?** Wtedy jesteś na linii 2.x, pozostaje wspierana i żadna
aktualizacja cię z niej nie zdejmie: wpis w marketplace wskazuje dokładny commit, a nie gałąź. Twoje
istniejące projekty pozostają tam czytelne.

Linia powyżej instaluje 3.x, która zapisuje projekt jako pliki czytelne maszynowo zamiast prozy,
rejestruje proces — i którą czyta TCC. Jeden skill na maszynę: dwie wtyczki dostarczające skill o tej
samej nazwie zostają obie aktywne, a która odpowie — sprawa przypadku. Więc najpierw usuń wtyczkę, w
Claude Code:

```
/plugin uninstall autosound-tuning
```

```
/plugin marketplace remove autosound-tuning-skill
```

Twoje projekty 2.x nie są konwertowane. 3.x importuje **bieżący** stan auta do **nowego** projektu i
zostawia stary nietknięty:

```sh
python3 ~/.claude/skills/.autosound-tuning-src/skills/autosound-tuning/rew_tool/state/migrate.py <old-project> --into <new-project>
```

Przenoszą się kanały i ich wyjścia, zwrotnice, opóźnienia, wzmocnienia, polaryzacja, EQ i profil DSP.
Dziennik i starsze migawki zostają — świadomie: 2.x nigdy nie zapisywała, które fakty obowiązywały
kiedy, więc przeniesienie jej historii oznaczałoby jej wymyślenie.
</details>

## Jak naprawdę brzmi sesja

Trzy głosy: **ty** na miejscu odsłuchowym, **Claude** prowadzi proces, **Gemini** podważa każdy ruch.

> **Ty (Arbiter):** Kontrabas trochę dudni. A kiedy ruszyłem opóźnienia na słuch, bas się poprawił —
> wpiszemy moje wartości?
>
> **Claude (Generator):** Najpierw sprawdziłem to na świeżych pomiarach: twoje opóźnienia są już
> optymalne — twojemu uchu spodobało się co innego. Prawdziwi winowajcy to dwa wąskie rezonanse drzwi
> i gorąca lewa strona. Proponuję trzy chirurgiczne cięcia.
>
> **Gemini (Krytyk):** Sprzeciw: jedno z tych cięć leży w obszarze zwrotnicy — to może zepsuć tam
> sumowanie.
>
> **Claude:** Sprawdzone na pomiarach — ten styk wręcz się *poprawia*. Ale twoja wątpliwość kazała mi
> spojrzeć głębiej i masz rację: to nie tylko nisko-średniotonowy, średniotonowy też jest tam gorący.
> Poprawiony plan: każdy głośnik dostaje własne cięcie.
>
> **Gemini:** Teraz się zgadzam.
>
> **Ty:** Wpisane. Dudnienie zniknęło… ale subwoofer lokalizuje się teraz za mną!
>
> **Claude:** Mój błąd — dwa moje filtry nakładają się i tną głębiej, niż zamierzałem. Łagodzę jeden.
>
> **Ty:** Bas znów jest z przodu — ale siedzi nisko. Chcę go wyżej, na szybie, tak jak był.
>
> **Claude:** Starą wysokość trzymała właśnie ta wada. Wady nie przywracamy — zamiast tego łagodne
> symetryczne podbicie EQ na obu średniotonowych, żeby wysokość wróciła bez przekosu.
>
> **Ty:** …Sub jest na masce! Zostawiam tak.

Około czterdziestu minut od „dudni" do „sub jest na masce" — przy problemie, który zwykle zjada
tygodnie prób według porad z forum. Każdy uczestnik złapał coś, co umknęło pozostałym. Pełna wersja
techniczna, z wszystkimi liczbami, jest w
[studium przypadku](community-inbox/case-studies/case-study-mode-a-bass-2026-07-15.md).

## Które modele wybrać

**Generator: Claude Opus, wysiłek `xhigh`. Recenzent: Gemini Pro (High).** To jedyna kombinacja,
którą tę metodę przeprowadzono od początku do końca. Wszystko inne jest eksperymentem, który
prowadzisz ty — i tak też warto to czytać.

Ma to znaczenie ze względu na *kształt* awarii. **Słabszy model nie zatrzymuje się z błędem — on się
z tobą zgadza.** Jeden udokumentowany przebieg zamknął fazy −1 do 3 za jednym posiedzeniem i zdał
raport z punktów zwrotnic, opóźnień co do 0,1 ms, EQ „w granicach ±0,5 dB" i werdyktu odsłuchowego —
dla auta, w którym nikt nie siedział. Nic w tym zapisie nie wyglądało na zepsute. To po prostu nie
było strojenie.

| Tryb | Układ | Niezawodność |
| :--- | :--- | :--- |
| **A: Claude + Gemini** | Claude prowadzi, Gemini recenzuje | Najwyższa: dwie perspektywy, wolniej na decyzję |
| **B: Solo** | jeden model prowadzi i sam siebie recenzuje | Niższa: jedna perspektywa, a jej liczby chce się sprawdzić ręcznie |

Czym prowadzić, z mojego dotychczasowego doświadczenia:

* **Opus**, domyślny wybór do strojenia. Trzyma długą sesję w całości i decyduje tam, gdzie słabszy
  model zatrzymuje się, żeby zapytać. `xhigh` to podłoga; na trudnych zakrętach ustaw Max.
* **Sonnet**, nie do złożonego strojenia. Ostrożny i gubi wątek, gdy fakty trzeba zestawiać przez
  długą sesję. Dobry do krótkich, ograniczonych kroków.
* **Fable**, do badania. Tam, gdzie zadaniem jest znaleźć nowe podejście, a nie zastosować znane, to
  od niego przyszły tu najlepsze pomysły.
* **Gemini**, jako Krytyk, na poziomie Pro. Jako prowadzący, przy obecnych zasadach, niezweryfikowany.

Modele i poziomy zmieniają się z miesiąca na miesiąc, więc traktuj to jako punkt wyjścia, a nie
werdykt, i sprawdź sam. Co się nie zmienia, to kształt awarii: cokolwiek wybierzesz, model
poproszony, by myśleć mniej, sam ci tego nie powie. Szczegóły konfiguracji, w tym darmowy recenzent w
przeglądarce przez Google AI Studio, są w [FAQ](FAQ.md).

## Matematyka pod maską

Biblioteka lokalnych skryptów przemiela duże zbiory danych, żeby modele nie wydawały na nie tokenów:

- **Mapa wad kabiny i montażu, zbudowana przed jakimkolwiek strojeniem.** Wycięcia drzwiowe, odbicia
  i lewo-prawe „kieszenie", których żaden stereofoniczny EQ nie wypełni, znajdowane są w pierwszych
  pomiarach — żeby plan EQ pracował *wokół* kabiny, zamiast z nią walczyć.
- **Cztery niezależne odczyty czasu muszą się zgodzić**, zanim tknie się jakiekolwiek opóźnienie.
- **Żaden głośnik nie jest zmuszany do walki z fizyką.** Możliwe do wypełnienia zapadnięcie i
  wycięcie interferencyjne wyglądają na wykresie tak samo; test fazy je rozróżnia, a podbicie dostaje
  tylko to pierwsze.
- **Każdy proponowany filtr jest symulowany na twoich własnych zmierzonych krzywych**, zanim go
  wpiszesz, i oceniany przy niewielkim dryfie opóźnienia i poziomu — żeby przetrwał w realnym
  świecie, a nie wygrywał w jednym punkcie „na ostrzu".

## Co tu jest

```
autosound-tuning-skill/        wtyczka do Claude Code
└── skills/autosound-tuning/    sam skill
    ├── SKILL.md        punkt wejścia — mapa procesu, cykl sesji, role
    ├── references/     dokumenty na żądanie (fazy, diagnostyka, EQ, filtry, scena,
    │                   utwory testowe, REW API, Helix, metoda recenzji, wywiad …)
    ├── knowledge/      zebrane profile aut i DSP (cars/, dsp/)
    ├── rew_tool/       most do REW API, analiza, krzywe docelowe, wersjonowany stan
    ├── scripts/        opakowania kanałów Krytyka/Doradcy (Gemini, Claude, Codex)
    └── curves.html     wizualizator krzywych docelowych
```

▶ **[Otwórz wizualizator krzywych docelowych online](https://ayukhno.github.io/autosound-tuning-skill/_curve-visualizer.html?lang=pl)** — przeciągnij własną krzywą albo standardową z [Nono Tuning Tool](https://nonotuningtool.com), kliknij prawym na dowolnym punkcie, żeby zobaczyć charakter częstotliwości, i porównuj krzywe obok siebie. Jeden samodzielny plik, więc działa offline; zachowaj kopię przez „Zapisz jako".

Metoda niezależnej recenzji (Krytyk/Doradca/Arbiter, przeciw zakotwiczeniu) jest opisana w
`references/core/review-loop.md`. Bezstanowa wersja metody do zwykłego czatu w przeglądarce, bez
lokalnej instalacji, znajduje się w gałęzi
[manual_step-by-step](https://github.com/ayukhno/autosound-tuning-skill/tree/manual_step-by-step).

## Podziel się doświadczeniem

Skill uczy się z każdego strojenia: zbiera opinie wprost w terminalu podczas pracy, a nie przez
formularz. Na zakończenie, gdy jesteś już zadowolony z dźwięku, pyta, co pomogło, co było nie tak i na
jakie dziwactwo DSP albo auta trafiłeś. Potem, **wyłącznie za twoją wyraźną zgodą**, proponuje
podzielić się *uogólnialnymi* wnioskami — żeby rosły wspólna metoda i biblioteka `knowledge/`.

Zapisuje **wyłącznie metodę i klasy sprzętu**: zachowanie kabiny, klasę urządzeń, które techniki
zadziałały. **Nigdy danych osobowych, nigdy pełnych pomiarów.** Widzisz dokładnie, co jest
udostępniane, i zgadzasz się osobno na każdy punkt. Potwierdzone wnioski trafiają do skilla z
podaniem autorstwa.

## Wsparcie

Skill jest **darmowy i otwarty** (CC BY-SA) i taki pozostanie. Nic nie jest schowane za opłatą. Jeśli
pomógł i chcesz podziękować, są dwie dobrowolne drogi:

💜 **[GitHub Sponsors](https://github.com/sponsors/ayukhno)** · ☕ **[Słoik Monobank](https://send.monobank.ua/jar/8wThVcodjm)** — jedno dotknięcie, bez konta; przyjmuje Apple Pay, Google Pay, Visa, Mastercard.

## Licencja

[CC BY-SA 4.0](LICENSE): używaj, adaptuj, dziel się; trzymaj pochodne otwarte i podawaj autorstwo. To
praca metodyczna i wiedzowa, więc share-alike trzyma doświadczenie społeczności otwartym.

Kod i skrypty (`rew_tool/`, `scripts/` i pozostałe pliki .py/.sh) są na
[licencji MIT](LICENSE-CODE). Materiały osób trzecich wymieniono w
[LICENSES/NOTICE.md](LICENSES/NOTICE.md).
