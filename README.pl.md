# Autosound Tuning Skill

🇬🇧 [English](README.md) · 🇩🇪 [Deutsch](README.de.md) · 🇵🇱 **Polski** · 🇺🇦 [Українська](README.uk.md) · ❓ [FAQ](FAQ.md) · <img src="assets/icons/roadmap.svg" width="14" height="14" valign="middle" alt="Roadmap" /> [Roadmap (EN, szkic)](ROADMAP.md)

**W jednym zdaniu:** asystent AI do strojenia dźwięku w twoim aucie. Czyta twoje pomiary z REW,
projektuje strojenie przy biurku na podstawie jednej sesji pomiarowej i prowadzi cię przez
zwrotnice, korekcję czasową, fazę i EQ — po jednej sprawdzonej zmianie naraz.

- **Pracuje z REW**: pobiera pomiary przez jego API i oddaje gotowy EQ jako plik, który zaimportuje
  twój procesor.
- **Projektuje przy biurku, sprawdza w aucie** *(3.x)*: jedna zdyscyplinowana sesja pomiarowa, a
  potem każdy punkt podziału, opóźnienie i filtr wybierane są na **przewidzianej** sumie twoich
  własnych zmierzonych głośników — a do auta wracasz raz, żeby to potwierdzić.
- **Najpierw diagnoza, potem naprawa**: odbicia, wygaszenia i rezonanse kabiny są znajdowane w
  pomiarach bazowych, zanim padnie jakakolwiek propozycja — a dołek, który da się podnieść
  korekcją, jest odróżniany od wygaszenia interferencyjnego, którego podnieść się nie da.
- **Nigdy nie pisze do twojego procesora**: w aucie nic się nie zmieni, dopóki sam tego nie
  wprowadzisz. To nie znaczy przepisywania z palca: oprogramowanie Helix / MATCH (PC-Tool) importuje wyeksportowany EQ za
  jednym razem, format REW Generic obsługuje większość innych procesorów, a dla tych bez importu
  plików — Musway, ESX, Zapco — jest
  [pomocnik kopiuj-wklej](https://github.com/IvanBakhmutov/REW-EQ-CopyPaste-Assistant).
- **Zna rzemiosło**: krzywe docelowe, filtry zabezpieczające, kolejność „najpierw faza", proces krok po
  kroku i to, którego utworu testowego słuchać i po co.
- **Uczy się twojego systemu**: gromadzi wiedzę o twoim aucie i sprzęcie — wyłącznie za twoją zgodą.

## Sprawdzone na zawodach

Z **linią 2.x** tej metody moje własne auto zdobyło w 2026 roku cztery nagrody:

- **1. miejsce, Einsteiger 5000 — AYA, Lemgo, 30 maja 2026.** Analiza wykresów i rady Gemini: ten
  sposób pracy stał się później tym skillem.
- **1. miejsce, Amateur 5000 — AYA, Horst, 25 lipca 2026.** Klasa wyżej — już samym skillem i
  własnymi uszami.
- **2. miejsce, Amateur 5000 — AYA, Schmallenberg, 15 sierpnia 2026.** Inny sędzia od brzmienia niż
  w lipcu; jego karta ocen jest materiałem wejściowym do następnej rundy.
- **3. miejsce, SQ Entry Unlimited — EMMA Sound Off 2026, Schmallenberg, 15 sierpnia 2026.**
  Pierwszy start według regulaminu EMMA, tego samego dnia i z tym samym strojeniem co AYA powyżej.

<p align="left">
  <img src="assets/awards/aya-may26-einsteiger5000.jpg" width="100" alt="AYA maj 2026, Einsteiger 5000, 1. miejsce">
  &nbsp;&nbsp;&nbsp;
  <img src="assets/awards/aya-jul26-amateur5000.jpg" width="100" alt="AYA lipiec 2026, Amateur 5000, 1. miejsce">
  &nbsp;&nbsp;&nbsp;
  <img src="assets/awards/aya-aug26-amateur5000.jpg" width="100" alt="AYA sierpień 2026, Amateur 5000, 2. miejsce">
  &nbsp;&nbsp;&nbsp;
  <img src="assets/awards/emma-aug26-entry-unlimited.jpg" width="60" alt="EMMA Sound Off 2026, SQ Entry Unlimited, 3. miejsce">
</p>

*Twoja nagroda też może tu stanąć.*

> [!CAUTION]
> AI potrafi pomylić się w liczbach. Zawsze sprawdź częstotliwości podziału, nachylenia i wartości
> EQ w procesorze, zanim odciszysz — zwłaszcza na głośnikach wysokotonowych — i zaczynaj cicho.

## Wybierz sposób pracy

Cztery drogi — od „wszystko w oknie aplikacji" do „spróbować dziś wieczorem w przeglądarce". Metoda
jest ta sama; różni je to, ile w niej automatu, jak bardzo jest sprawdzona i ile kosztuje cię
konfiguracja. **Nagrody powyżej zdobyto drogą 3.**

| Nr | Droga | Czego potrzebujesz | Co dostajesz | Haczyk |
| :-- | :--- | :--- | :--- | :--- |
| **1** | **3.x w oknie** — [instalator w jednej linii](#jak-zacząć), który przynosi ze sobą [TCC](https://github.com/ayukhno/autosound-tcc) | Płatny plan Claude, beta REW z włączonym API i ~700 MB na dysku; Claude Code i Pythona instalator przyniesie sam | Cała metoda razem ze strukturą kanałów procesora, twoimi krzywymi z REW, planem i AI obok siebie w jednym oknie — macOS i Windows — na tych samych plikach projektu, co terminal | Wersja przedpremierowa, a aplikacja jest młodsza niż metoda, którą uruchamia. Modele inne niż Claude i Gemini idą przez `omp` i są rozliczane osobno |
| **2** | **3.x w terminalu** — ten sam instalator z `--terminal` | To samo, bez aplikacji | Projekt jako dane (rejestr, z którego cofasz się jednym ruchem), droga „najpierw biurko", EQ w pakietach przez bramki kontrolne, weryfikacja po wprowadzeniu, narzędzia, które **odmawiają** zamiast meldować „brak zastrzeżeń", i poprawki docierające do ciebie tagami | Wersja przedpremierowa: trwa ostatnie pełne sprawdzenie strojeniem przed 3.1.0. Wszystko dzieje się tekstem |
| **3** | **Linia 2.x — sprawdzona** ⭐ [`v2.8.3`](https://github.com/ayukhno/autosound-tuning-skill/releases/tag/v2.8.3), gałąź [`2.x`](https://github.com/ayukhno/autosound-tuning-skill/tree/2.x) | Claude Code + płatny plan Claude, beta REW z włączonym API, jedno `/plugin install` | Pełna metoda iteracyjna: REW czytany przez API, skrypty analizy, pętla Generator ↔ Krytyk ↔ Arbiter. **Cztery nagrody powyżej zrobiono właśnie nią** | Tylko terminal, bez aplikacji. Projekt jest prozą, więc obowiązujący stan się odczytuje, a nie sprawdza maszynowo; drogi „najpierw biurko" i nowszych narzędzi tu nie ma. Dalej już tylko poprawki |
| **4** | **Czat w przeglądarce, nic nie instalujesz** — gałąź [manual_step-by-step](https://github.com/ayukhno/autosound-tuning-skill/tree/manual_step-by-step) | Przeglądarka, darmowy Gemini albo dowolny czat, REW do mierzenia i eksportu | Kroki metody jako prompty do wklejenia; plik-paszport z ustawieniami auta, przepisywany w całości na każdym kroku | Cała robota ręcznie: bez automatyki REW, bez pamięci między krokami, bez drugiej AI jako recenzenta. Za darmo — i najsłabsza z czterech |

**Krótko.** Chcesz aktualnej metody i wolisz patrzeć niż pisać — droga 1. Mieszkasz w terminalu —
droga 2. Chcesz dokładnie tego, czym zdobyto nagrody — **droga 3**, i żadna aktualizacja cię z niej
nie ruszy. Chcesz spróbować metody, zanim cokolwiek zainstalujesz — droga 4, a potem zdecydujesz.
Drogi 1, 2 i 3 czytają auto przez API REW i nigdy nie piszą do procesora.

Szczegóły każdej — co instalator gdzie kładzie, co się zmieniło w 3.x i jak przejść z jednej drogi
na drugą — są w [FAQ](FAQ.md#choosing-a-path) (po angielsku).

## Spis treści

- [Wybierz sposób pracy](#wybierz-sposób-pracy)
- [Dla kogo to jest](#dla-kogo-to-jest)
- [Czego potrzebujesz](#czego-potrzebujesz)
- [Jak zacząć](#jak-zacząć)
- [Jak przebiega strojenie](#jak-przebiega-strojenie)
- [Jak brzmi sesja](#jak-brzmi-sesja)
- [Jakie modele wybrać](#jakie-modele-wybrać)
- [Matematyka pod maską](#matematyka-pod-maską)
- [Co jest w środku](#co-jest-w-środku)
- [Jak zgłosić problem](#jak-zgłosić-problem)
- [Podziel się doświadczeniem](#podziel-się-doświadczeniem)
- [Wsparcie](#wsparcie)
- [Licencja](#licencja)

## Dla kogo to jest

Dla każdego, kto buduje dźwięk we własnym aucie i uczy się rzemiosła. To twój egzoszkielet: on niesie
wiedzę i doświadczenie, ty wnosisz uszy i ręce na procesorze.

Strojenie to lawina zmiennych. Metod, parametrów i reguł kciuka jest więcej, niż mieści się w głowie, i łatwo
zanurkować w jeden szczegół, a zgubić całość. Skill trzyma wiedzę, wskazuje te kilka zmian, które
naprawdę ważą, i pilnuje kompromisu między sceną a barwą. Ostatnim sędzią jest twoje ucho.

Obejmuje pełne strojenie: od nowego projektu przez zwrotnice, korekcję czasową, fazę, EQ kanałowe i
sumaryczne, aż po scenę i doprawianie do gustu — plus opcjonalne warstwy przestrzenne
(uzupełniający **center-fill** i różnicowy **rear-fill**, oba sprawdzone w praktyce). Każda zmiana
przechodzi przez pętlę **Generator ↔ Krytyk ↔ Arbiter**: jedna AI proponuje, druga oponuje,
decydujesz ty.

## Czego potrzebujesz

**Czysta maszyna to normalny przypadek.** Narzędzi programistycznych — Pythona, gita, Claude Code —
nie trzeba mieć wcześniej: instalator poniżej przyniesie je sam, razem z metodą, aplikacją i
recenzentem Gemini.

Czego przynieść nie może, bo to twoje:

- **[REW](https://www.roomeqwizard.com/) — wersja beta** z włączonym API. Wszystko, co skill wie o
  twoim aucie, przychodzi właśnie tędy, a **API jest tylko w betach**: wersja wydana (V5.31.3,
  lipiec 2024) w ogóle nie ma zakładki *API* w ustawieniach — a to właśnie ją podsuwa wyszukiwarka.
  Weź build z [roomeqwizard.com/beta.html](https://www.roomeqwizard.com/beta.html) — pliki leżą na
  AV NIRVANA, forum REW. Potem w REW: *Preferences → API*, zaznacz **Start the API when REW starts**
  i naciśnij **Start server**; panel pokaże *„API server is running on port 4735"* — od tej pory
  wstaje razem z REW. Ten panel jest taki sam na macOS i Windows; na Windows instalator kładzie
  jeszcze na pulpicie skrót **REW (API on)**, który uruchamia REW z włączonym API jednym kliknięciem.
  **Zostaw REW otwarty** przez cały czas strojenia: metoda czyta pomiary z działającego okna przez
  to API, a nie z wyeksportowanych plików.
- **Kalibrowany mikrofon pomiarowy i procesor, w który da się wpisywać liczby.** Każdy procesor się
  nadaje. Do fazy i czasu karta z wejściem XLR i fizyczną pętlą zwrotną bije mikrofony USB (np. UMIK-1):
  [dlaczego, w FAQ](FAQ.md#measuring-phase--time-alignment-umik-1-vs-xlr-microphones).
- **Płatna subskrypcja Claude (Pro albo Max).** Zobacz
  [plany i koszt sesji](FAQ.md#subscription-options-quotas--budgets-as-of-july-2026).
- **Zasięg tam, gdzie stoi auto.** AI działa w chmurze, więc w podziemnym parkingu bez sygnału sesja
  po prostu nie ruszy — zadbaj wcześniej o internet mobilny albo Wi-Fi. Same skrypty i pomiary sieci
  nie potrzebują; potrzebuje jej rozmowa.

Druga AI jako recenzent jest opcjonalna i to z niej płynie większość pożytku. Instalator przynosi w
tym celu `agy` od Google i proponuje logowanie na końcu; bez niego skill pracuje sam i mówi ci o
tym, a recenzenta możesz dodać później.

**Konto GitHub warto mieć, a do instalacji nie jest potrzebne.** Instalacja nigdzie nie każe się
logować, oba repozytoria są publiczne. Powodem, by je mieć, jest twój własny projekt — i nie chodzi
o surowe sweepy: te ważą po 16–112 MB, zostają na twoim dysku, a gdybyś ich kiedyś potrzebował,
zmierzyłbyś od nowa. Warto zachować to, do czego **doszedłeś**: rejestr każdego podziału,
opóźnienia, wzmocnienia i filtra, dziennik tego, jak do tego doszedłeś, kopie konfiguracji
procesora, które przywracają strojenie, krzywe docelowe i notatki z analiz. Małe pliki — a żadne
ponowne mierzenie ich nie odtworzy. Instalator pyta, czy chcesz kopię w **prywatnym** repozytorium
GitHub, i jeśli tak, stawia `gh` i loguje je; sama kopia powstaje wtedy, gdy powiesz AI, żeby zrobiła
backup projektu — ona wie, co zostaje na zewnątrz. Darmowe konto wystarczy.

## Jak zacząć

Jedna linia instaluje wszystko: Claude Code, metodę,
[aplikację TCC](https://github.com/ayukhno/autosound-tcc), Gemini jako recenzenta i `omp`, dzięki
któremu aplikacja może proponować modele inne niż Claude. Pokazuje, co już jest na maszynie, wypisuje
wszystko, co pobierze, i skąd, pyta raz — a potem przez dziesięć do dwudziestu minut pracuje sama.
Jedyna przerwa przychodzi zaraz po tym pytaniu: na Macu, na którym nigdy nie programowano, poprosi
raz o hasło do Maca — dla Apple Command Line Tools; na Windows pokaże jedno okno uprawnień dla Gita.
Na końcu loguje cię w przeglądarce: najpierw Claude (to obowiązkowe), potem recenzent i GitHub, jeśli
chcesz — każde przez Enter albo później.

*(To drogi 1 i 2 z [tabeli wyboru](#wybierz-sposób-pracy). Dla drogi 3 — tej z nagrodami — dwie
komendy wtyczki są w [README gałęzi 2.x](https://github.com/ayukhno/autosound-tuning-skill/blob/2.x/README.md#getting-started).)*

**macOS** — otwórz Terminal (⌘-Spacja, wpisz „terminal", Enter) i wklej:

```sh
curl -fsSL https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/main/install.sh | bash
```

**Windows** — otwórz PowerShell (Start, wpisz „powershell", Enter) i wklej:

```powershell
irm https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/main/install.ps1 | iex
```

Żeby coś pominąć: `--terminal` (bez aplikacji), `--no-reviewer`, `--no-github` albo `--no-omp`, po
`bash -s --` na macOS; na Windows te same cztery jako `-Terminal`, `-NoReviewer`, `-NoGitHub`,
`-NoOmp` w postaci `& ([scriptblock]::Create((irm <ten adres>))) -Terminal`. Ponowne uruchomienie tej
samej linii wszystko aktualizuje; `--uninstall` / `-Uninstall` usuwa to, co instalator postawił, i
nigdy folderu projektu.

Potem start. Zrób folder dla auta (wszystko o tym aucie będzie w nim mieszkać, więc kopia folderu to
kopia całego strojenia) i otwórz go na jeden z dwóch sposobów:

**W terminalu.** Otwórz **nowe** okno terminala (to, z którego instalowałeś, nie widzi tego, co
przed chwilą doszło), a potem:

```sh
mkdir -p ~/Autosound/moje-auto && cd ~/Autosound/moje-auto
```

```sh
claude
```

*I zacznij strojenie słowami:* **„tune a new car from scratch"** (albo po polsku: „nastrójmy to auto
od zera").

**W aplikacji.** Kliknij dwukrotnie **Autosound TCC** na pulpicie, *Browse…* do folderu (nowy, pusty
jest właściwy), wybierz modele — Claude Opus (SDK) jako *AI main*, Gemini Pro (High) jako *AI
critic* — naciśnij *Open* i powiedz to samo w panelu po prawej, w dowolnym języku.

To jeden projekt, nie dwa: metoda pisze pliki projektu, aplikacja je czyta — więc dziś możesz
pracować w oknie, a jutro w terminalu.

> **Wyzwalacz: nazwij coś z car audio.** Skill budzi się na **to, o co pytasz**, więc samo `resume`
> go nie odpali — to mógłby być dowolny projekt. Dodaj jedno słowo z dziedziny: **„wróćmy do
> strojenia car audio"**, **„continue tuning the car"**, **„jaki mam teraz stan procesora /
> podziałów"**. Tak samo przy starcie: nazwij auto albo dźwięk, a nie tylko „pomóż mi".

> **Model i wysiłek ustaw PRZED pierwszą wiadomością.** Są ustalone na całą sesję i nic ich potem nie
> podniesie. Stan na sierpień 2026: **Claude Opus na `xhigh`**, z **Gemini Pro (High)** jako
> recenzentem. [Dlaczego tańsze kombinacje zawodzą po cichu](#jakie-modele-wybrać).

Przychodzisz z **wtyczki 2.x** albo chcesz, żeby prowadził **Gemini**? Jedno i drugie jest w FAQ:
[przejście 2.x → 3.x](FAQ.md#moving-from-2x-to-3x) (najpierw usuń wtyczkę — dwa skille o tej samej
nazwie zostają aktywne oba) i
[Gemini jako prowadzący](FAQ.md#can-i-ask-gemini-to-install-and-run-the-skill-itself-without-claude-code).

## Jak przebiega strojenie

Droga 3.x: zaczynasz i kończysz w aucie, a całe projektowanie robisz przy biurku. Dwa wyjazdy do auta, jedno posiedzenie przy
biurku między nimi; **rejestr** na dysku jest jedynym źródłem prawdy (wszystkie podziały,
opóźnienia, wzmocnienia, polaryzacje i filtry, każde z wersją, w której powstało), a każda
propozycja ląduje w nim nową wersją, z której cofasz się jednym ruchem.

1. **Przygotowanie, przy biurku.** Auto, głośniki, procesor i to, co potrafi, mikrofon i krzywa
   docelowa — uzgodnione, zanim ktokolwiek usiądzie w aucie, żeby tam nic nie zaskakiwało.
2. **Jedna sesja pomiarowa, w aucie.** Każdy głośnik osobno, wyłącznie z **filtrami zabezpieczającymi** —
   górnoprzepustowy na średniotonowych i wysokotonowych, i nic więcej — żeby nagranie niosło
   głośnik i kabinę, a nie strojenie. Midbas w drzwiach zmierzony sweepem bez filtra dolnego brzmi
   u góry ostro: to break-up membrany, właśnie jego sweep ma pokazać, i nic się przy tym nie psuje.
   Sweepy i przejście ruchomym mikrofonem (MMM) za jednym razem, plus kilka pozycji kontrolnych wokół
   głowy. Zanim wysiądziesz, runda jest sprawdzana: czy są wszystkie głośniki, czy czas między
   pierwszym a ostatnim sweepem stoi w miejscu, czy filtry zabezpieczające są zapisane.
3. **Projekt, przy biurku.** Podziały, poziomy, opóźnienia i polaryzacja wybierane są na sumie
   **przewidzianej** z twoich zmierzonych głośników razem z filtrami samego procesora: każde
   połączenie pasm oceniane po tym, jak mało energii traci, a opóźnienie przesunięte o pełny okres (360°) jest
   od razu wychwytywane. EQ przychodzi pakietami, w tej kolejności: własne rezonanse głośnika (tylko
   tam, gdzie szczyt stoi w miejscu na wszystkich pozycjach kontrolnych i jest minimalnofazowy),
   kształt lewo-prawo, a potem barwa do krzywej docelowej. Domyślnie tylko cięcia. Każdy pakiet to
   jedna decyzja i jedna wersja rejestru; na wyjściu jest plik eksportu dla procesora.
4. **Sprawdzenie, w aucie — krótkie.** Przenosisz liczby z arkusza do procesora. Weryfikacja po
   wprowadzeniu potwierdza, głośnik po głośniku, że system w aucie odtwarza to, co zaprojektowano przy biurku — albo
   wskazuje ten jeden, który się nie zgadza, i dlaczego. Potem to, czego biurko nie potrafi:
   dokładne EQ na średniej z ruchomego mikrofonu (MMM) i A/B po jednym paśmie, gdzie metoda zamienia twoje
   „tnie w uszy" albo „dudni" na krótką, uszeregowaną listę podejrzanych — najwyżej trzy rundy.
5. **Słuchanie.** Utwory testowe, ściągawka „czego słuchać" i werdykt zapisany przy tej wersji,
   która na niego zasłużyła.
6. **Gust.** Presety na warstwie wirtualnej, żeby strojenie techniczne pod spodem zostało nietknięte.

W aplikacji tę samą drogę widać oczami: strukturę kanałów procesora, krzywe zmierzone przez REW, plan z
krokami, wersje rejestru i AI w panelu bocznym. Aplikacja czyta te same pliki, które pisze metoda —
krok zrobiony w terminalu widać w oknie i odwrotnie.

Kiedy biurko i auto się rozjeżdżają, droga cofa się do pętli iteracyjnej, którą zdobyto nagrody, a
rejestr zapisuje gdzie. Cała droga, faza po fazie, jest w
[`references/phases/virtual-first.md`](skills/autosound-tuning/references/phases/virtual-first.md);
pliki faz za nią wymienia [`SKILL.md`](skills/autosound-tuning/SKILL.md).

## Jak brzmi sesja

Trzy głosy: **ty** na miejscu odsłuchowym, **Claude** prowadzi proces, **Gemini** oponuje przy
każdym ruchu. Krótka ilustracja pętli na drodze „najpierw biurko" — kształt rozmowy, nie stenogram:

> **Ty (Arbiter):** Bas jest chudy i ciągnie na stronę pasażera.
>
> **Claude (Generator):** Przed jakimkolwiek EQ: w przewidzianej sumie zgranie sub↔midbas przy 80 Hz leży 4 dB niżej niż każdy z nich osobno. To pytanie o czas, nie o barwę. Dwa opóźnienia pasują do amplitudy jednakowo dobrze — 3,4 ms i 3,4 minus jeden pełny okres.
>
> **Gemini (Krytyk):** To powiedz, które z nich potwierdza czas dotarcia. Opóźnienie przesunięte o pełny okres wygląda na zgraniu identycznie i rozsypuje się oktawę wyżej.
>
> **Claude:** Czas dotarcia odczytany ze zmierzonej odpowiedzi impulsowej mówi 3,4 ms; bliźniak traci 2 dB przy 300 Hz. Biorę 3,4 — zapisane jako wersja, z której cofa się jednym ruchem.
>
> **Ty:** Wprowadzone. Teraz jest w centrum — ale jedna nuta dudni.
>
> **Claude:** Weryfikacja po wprowadzeniu mówi, że auto zgadza się z biurkiem co do 0,6 dB, więc to nie opóźnienia. 63 Hz stoi w miejscu na wszystkich dziewięciu pozycjach wokół twojej głowy, a to znaczy kabina — i mod kabiny EQ ma prawo ściąć: jedno pasmo, −4 dB, Q 3, na parze midbasów.
>
> **Gemini:** Zgoda — i sprawdź, czy o to samo cięcie nie prosisz dwa razy: poniżej 80 Hz sub i midbas się nakładają.
>
> **Ty:** Lepiej. Zostawiamy.

Każdy krok tutaj to liczba policzona przez narzędzia, a nie reguła z palca, i każdy jest wersją w
rejestrze, cofalną jednym ruchem. Prawdziwa sesja rozpisana ze wszystkimi liczbami — trudny przypadek
z modem kabiny, rozwiązany tą samą pętlą — jest w
[studium przypadku](community-inbox/case-studies/case-study-mode-a-bass-2026-07-15.md).

## Jakie modele wybrać

**Generator: Claude Opus, wysiłek `xhigh`. Recenzent: Gemini Pro (High).** To jedyna kombinacja,
którą tę metodę przejechano od początku do końca. Wszystko inne jest eksperymentem, który robisz ty
— i tak też warto to czytać.

Kluczowe jest to, **w jaki sposób** model się myli. **Słabszy model nie zatrzymuje się z błędem — on się z tobą
zgadza.** Jeden udokumentowany przebieg zamknął fazy od −1 do 3 w jednym posiedzeniu i zaraportował
częstotliwości podziału, opóźnienia z dokładnością 0,1 ms, EQ „w granicach ±0,5 dB" i werdykt
odsłuchowy — dla auta, w którym nikt nie siedział. Nic w tym zapisie nie wyglądało na zepsute. To
po prostu nie było strojenie.

| Tryb | Układ | Niezawodność |
| :--- | :--- | :--- |
| **A: Claude + Gemini** | Claude prowadzi, Gemini recenzuje | Najwyższa: dwie perspektywy, wolniej na każdą decyzję |
| **B: Solo** | jeden model prowadzi i sam siebie sprawdza | Niższa: jedna perspektywa, a jego liczby chce się przeliczyć ręcznie |

Czym prowadzić, z mojego dotychczasowego doświadczenia:

* **Opus** — domyślny wybór do strojenia. Trzyma długą sesję w kupie i decyduje tam, gdzie słabszy
  model przystaje, żeby zapytać. `xhigh` to minimum; na trudnych zakrętach ustaw Max.
* **Sonnet** — nie do złożonego strojenia. Ostrożny i gubi wątek, gdy fakty trzeba zszywać przez
  długą sesję. Dobry do krótkich, ograniczonych kroków.
* **Fable** — do badań. Tam, gdzie zadaniem jest znaleźć nowe podejście, a nie zastosować znane, dał
  tu najlepsze pomysły.
* **Gemini** — jako Krytyk, na poziomie Pro. Jako prowadzący, przy obecnych regułach, jest
  niesprawdzony.

Modele i poziomy zmieniają się z miesiąca na miesiąc, więc traktuj to jako punkt wyjścia, a nie
wyrok, i sprawdź sam. Nie zmienia się sposób, w jaki to zawodzi: cokolwiek wybierzesz, model poproszony o
mniejszy wysiłek sam ci tego nie powie. Szczegóły konfiguracji, w tym darmowy recenzent w
przeglądarce przez Google AI Studio, są w [FAQ](FAQ.md) (po angielsku).

## Matematyka pod maską

Biblioteka lokalnych skryptów przemiela wielkie zbiory danych, żeby modele nie wydawały na nie
tokenów — i nie zgadywały liczby, którą da się policzyć:

- **Mapa wad kabiny i montażu, zbudowana przed jakimkolwiek strojeniem.** Wygaszenia w drzwiach,
  odbicia i „kieszenie" lewo-prawo, których żaden EQ stereo nie wypełni, są znajdowane w pierwszych
  sweepach — żeby plan EQ pracował **wokół** kabiny, a nie z nią walczył.
- **Suma jest przewidywana, a nie wyczekiwana.** Każda para głośników jest sumowana z ich
  zmierzonych odpowiedzi razem z filtrami procesora; opóźnienie i polaryzacja wybierane są po tym,
  jak mało traci połączenie pasm, opóźnienie przesunięte o pełny okres jest od razu wychwytywane, a zanim ruszy
  się opóźnienie, cztery niezależne odczyty czasu muszą się zgodzić.
- **Żaden głośnik nie jest posyłany do walki z fizyką.** Dołek, który da się wypełnić, i wygaszenie
  interferencyjne wyglądają na wykresie tak samo; rozróżnia je test fazy nadmiarowej (w REW:
  *Excess phase*) — podnosić wolno tylko ten pierwszy.
- **Krzywej wierzy się na tej szerokości, na której jest prawdziwa.** Rozrzut po pozycjach wokół
  głowy, zmierzony **w twoim** aucie, mówi, które cechy stoją w miejscu (głośnik), a które jadą za
  mikrofonem (miejsce siedzące) — i ustala, jak wąski może być filtr, pasmo po paśmie.
- **EQ jest proponowane pakietami przez bramki**: rezonanse → kształt lewo-prawo → barwa, domyślnie
  tylko cięcia; a „tnie w uszy" zamienia się w krótką listę podejrzanych, uszeregowaną po tym, jak
  głośno słyszy je ucho, każdy z jednym A/B.
- **Każdy proponowany filtr jest symulowany na twoich własnych pomiarach**, zanim go wpiszesz,
  oceniany przy małym dryfie opóźnienia i poziomu — żeby przetrwał rzeczywistość, a nie wygrywał w
  jednym punkcie — i potwierdzany weryfikacją po wprowadzeniu.
- **Sprawdzenie bez swoich danych wejściowych ODMAWIA.** Nigdy nie melduje „brak zastrzeżeń" z
  powodu braku danych: żadnego opóźnienia z jednego estymatora, żadnego EQ na rundzie pomiarowej,
  która odjechała, żadnej rundy bez zapisanych filtrów zabezpieczających.

Wszystko, co metoda potrafi — ułożone według twojego zamiaru, a nie nazw plików — jest na jednej
tablicy: [`references/core/capabilities.md`](skills/autosound-tuning/references/core/capabilities.md)
— 67 możliwości w 13 kierunkach, każda z komendą, z tym, czego wymaga i bez czego odmówi, oraz ze
wskazaniem, gdzie przeczytać uzasadnienie. Sprawdzarka w zestawie testów trzyma tablicę w zgodzie z
kodem. Każdy moduł `rew_tool` ma własny `--selftest`, zakotwiczony w definicjach, a nie we własnym
wyniku, a [`scripts/run-selftests.sh`](scripts/run-selftests.sh) uruchamia je wszystkie.

## Co jest w środku

```
autosound-tuning-skill/
├── install.sh · install.ps1 · install.cmd    instalator dla macOS i Windows
├── skills/autosound-tuning/                  skill (wtyczka Claude Code)
│   ├── SKILL.md         punkt wejścia — mapa procesu, cykl sesji, role
│   ├── references/      doktryna: core/ (tablica możliwości, pętla recenzji, czego
│   │                    narzędzia odmawiają…), phases/ (−1…5, virtual-first),
│   │                    patterns/, tooling/
│   ├── knowledge/       zebrane profile aut i procesorów (cars/, dsp/)
│   ├── rew_tool/        most do REW, analiza, przewidywanie i sprawdzanie, propozycje EQ,
│   │                    rejestr i proces — każdy moduł z własnym --selftest
│   ├── scripts/         kanał Doradcy / Krytyka (Gemini, Claude, Codex)
│   ├── evals/           czy skill budzi się na właściwe pytanie
│   └── curves.html      wizualizator krzywych docelowych
├── scripts/             kontrole wydania: run-selftests.sh, tag-check.sh, installer-consistency.py
├── community-inbox/     studia przypadków i doświadczenie społeczności
└── CHANGELOG.md         każdy tag z notatką o aktualizacji
```

▶ **[Otwórz wizualizator krzywych docelowych online](https://ayukhno.github.io/autosound-tuning-skill/_curve-visualizer.html?lang=pl)** — przeciągnij własną krzywą albo standardową z [Nono Tuning Tool](https://nonotuningtool.com), kliknij prawym na dowolnym punkcie, żeby zobaczyć charakter tej częstotliwości, i porównuj krzywe obok siebie. Jeden samodzielny plik, więc działa offline; „Zapisz jako" zostawia ci kopię.

Metoda niezależnej recenzji (Krytyk/Doradca/Arbiter, przeciw zakotwiczeniu) jest opisana w
[`references/core/review-loop.md`](skills/autosound-tuning/references/core/review-loop.md).

Aplikacja ma własne repozytorium, [autosound-tcc](https://github.com/ayukhno/autosound-tcc);
instalator bierze najnowszy tag każdego z nich — aplikacji i metody (`v3.*`) — i kładzie metodę w
`~/.claude/skills/autosound-tuning`, gdzie znajduje ją Claude Code. Którą wersję aplikacji i którą
wersję metody masz u siebie, widać w aplikacji w *Diagnostics → Installation*.

## Jak zgłosić problem

Wszystko, co się zepsuło, było błędne albo cię zatrzymało: **[otwórz issue](https://github.com/ayukhno/autosound-tuning-skill/issues/new/choose)**
— formularz raportu bety ma pola na przebieg zdarzeń i na wersje. To skrzynka samej metody; problemy
z aplikacją idą [do jej repozytorium](https://github.com/ayukhno/autosound-tcc/issues/new/choose), a
TCC wypełnia połowę tego formularza za ciebie (*Diagnostics → Installation → Report a problem*). Na
issue da się odpowiedzieć, na wiadomość na czacie nie.

## Podziel się doświadczeniem

Skill uczy się z każdego strojenia: zbiera opinie wprost w terminalu, w trakcie pracy, a nie przez
formularz. Na zakończenie, gdy jesteś już zadowolony z brzmienia, pyta, co pomogło, co było nie tak
i na jakie dziwactwo procesora albo auta trafiłeś. Potem, **za twoją wyraźną zgodą**, proponuje
podzielić się **uogólnialnymi** wnioskami — żeby rosły wspólna metoda i biblioteka `knowledge/`.

Zbiera **wyłącznie klasę metody i sprzętu**: zachowanie kabiny, klasę sprzętu, które techniki
zadziałały. **Nigdy danych osobowych i nigdy pełnych pomiarów.** Widzisz dokładnie, czym się
dzielisz, i zgadzasz się punkt po punkcie. Potwierdzone wnioski trafiają do skilla z podaniem
autorstwa.

## Wsparcie

Skill jest **darmowy i otwarty** (CC BY-SA) i taki zostanie. Nic nie jest schowane za opłatą. Jeśli
pomógł i chcesz podziękować, są dwa dobrowolne kanały:

💜 **[GitHub Sponsors](https://github.com/sponsors/ayukhno)** · ☕ **[Słoik w Monobank](https://send.monobank.ua/jar/8wThVcodjm)** — jedno tapnięcie, bez zakładania konta; przyjmuje Apple Pay, Google Pay, Visa, Mastercard.

## Licencja

[CC BY-SA 4.0](LICENSE): używaj, adaptuj, rozpowszechniaj; pochodne trzymaj otwarte i podawaj
autorstwo. To praca metodyczna i wiedzowa, a share-alike trzyma doświadczenie społeczności otwartym.

Kod i skrypty (`rew_tool/`, `scripts/`, inne .py/.sh) są na [licencji MIT](LICENSE-CODE). Materiały
osób trzecich wymieniono w [LICENSES/NOTICE.md](LICENSES/NOTICE.md).
