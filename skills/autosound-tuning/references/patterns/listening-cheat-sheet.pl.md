# Ściąga do odsłuchu — słowa na to, co słyszysz, i dokąd każde z nich prowadzi

> 🧩 **Tłumaczenie** [`listening-cheat-sheet.md`](listening-cheat-sheet.md) — plik angielski jest
> źródłem; identyfikatory (`c01`…, nazwy tras, kody utworów) są te same, różni się tylko tekst. Utwory
> i wskazówki „gdzie słuchać” — w [`test-tracks.md`](test-tracks.md). Narzędzia czytają oba pliki przez
> `rew_tool/listening.py` po identyfikatorach. Uzgodnione z autorem 25.08.2026.

## Zanim zagra jakikolwiek utwór — trzy rzeczy, które sesja musi wiedzieć

1. **Jaką bibliotekę naprawdę masz.** Każdy utwór w teście odsłuchowym jest nazywany z biblioteką
   (`CarMus #NN` · `Chesky Ch.NN` · płyta `EMMA` / `AYA` · zestaw mono · streaming z dokładną wersją).
   Goły numer to nie utwór. Jeśli nie masz żadnej ze znanych bibliotek — powiedz to: sesja pracuje wtedy
   na **Twoich ulubionych utworach** i na opisie materiału (głęboki bas · wokal kobiecy · gitara
   akustyczna · gęsty rock · orkiestra).
2. **Co dla Ciebie znaczy „było”.** Porównanie z poprzednim strojeniem jest możliwe tylko, jeśli z nim
   przyszedłeś (jego slot zachowano przy intake) — albo w drugim przejściu fazy 4, gdzie „było” to
   pierwsze przejście. Strojenie zbudowane od zera nie ma „było”.
3. **Z czym porównujesz.** Strojenie dla siebie: A/B z poprzednim strojeniem warto robić, slot jest obok.
   Strojenie na zawody: porównuj z **wzorcem** — własnym doświadczeniem, dobrym systemem domowym albo
   samochodami-laureatami, w których siedziałeś. Samego dźwięku nie da się długo pamiętać; **zapamiętaj
   emocję**, jaką dał wzorzec, i porównuj emocję, nie szczegóły (praktyka autora; lepszy przepis mile
   widziany).

## Pierwszy odsłuch — usłysz swój system przed jakimkolwiek werdyktem (5 minut)

Zaraz po technicznym zamknięciu, przed formalnym przejściem — trasa `first` poniżej:

1. **Jeden ulubiony, dobrze znany Ci utwór.** Bez werdyktu — to Ty poznajesz system.
2. **Prawdziwe nagranie mono ze streamingu** (`mono/merrill` albo `mono/byrds` w `test-tracks.md`).
   Jedno pytanie: **gdzie jest obraz?** Ciasny punkt na środku, na wysokości deski rozdzielczej, który nie
   pływa — to środek sceny i pierwsze prawdziwe osiągnięcie, które masz już w kieszeni.
3. **`CarMus#01`** (jeśli masz): skala, przestrzeń, rozdzielczość, makrodynamika — „poziom systemu od
   razu”.

Potem — przejażdżka. Słuchanie męczy; przejścia poniżej **celowo dzielą się na krótkie posiedzenia** —
posłuchaj, pojedź, wróć, posłuchaj znowu. W drodze uszy się resetują.

## Cechy — słownik

`label` to krótka forma do menu; `name` — pełna. „Brzmi dobrze” i „brzmi źle” to dwa samodzielne
zwroty, pisane tak, by wstawić je w zdanie. `route` to krok metody, do którego idzie ✗ (stół 1.3 =
złącza, 1.4 = poziomy, 2.1 = zgrubna EQ, 3.3 = dokładna EQ po MMM). Cecha oznaczona „wyższa liga” nie
jest na pierwsze przejście.

| id | label | name | sounds right | sounds wrong | where a ✗ goes |
|---|---|---|---|---|---|
| c01 | środek mono | Środek mono — fundament L/R | ciasny punkt na środku, na wysokości, który stoi w miejscu | rozmyty, wędruje w lewo lub w prawo, szeroki, albo zmienia miejsce z nutą | fundament: poziomy L/R, czas dojścia, polaryzacja (stół 1.3 / 1.4) — nigdy EQ obrazu |
| c02 | pozycje | Pozycje L · LC · C · RC · R | każdy instrument to jeden punkt na swoim miejscu | pozycje ściśnięte ku środkowi albo dwie dzielą jedno miejsce | poziomy L/R; stromość zboczy zwrotnic w strefie nakładania się średnicy (1.2 / 1.4) |
| c03 | ostrość | Ostrość i rozmiar obrazu | hierarchia rozmiarów — bas największy, trójkąt najmniejszy; wokal trzyma rozmiar na wszystkich nutach | każdy obraz tego samego rozmiaru; wokal rośnie albo pływa na niektórych nutach | styk średniotonowy↔wysokotonowy (1.3); poziomy (1.4) |
| c04 | balans | Balans tonalny | instrumenty grają razem, nic nie wystaje, bez „koca na głośnikach” | cienko, grubo lub mętnie, jasno lub krzykliwie, koc na głośnikach | szerokie nachylenie względem celu MMM (3.3); ostre pasmo dostaje jedno punktowe cięcie (3.3) |
| c05 | punch / szew | Punch i szew sub↔midbas | uderzenie ląduje w piersi, sub nie odpada pod nim, dwa basy czyta się osobno | wiotki, rozmyty, przesuszony, niski bas odrywa się od stopy, albo papka | styk sub↔midbas (1.3); L/R midbasów 100–200 Hz (1.3) |
| c06 | sub <40 | Sub poniżej 40 Hz | trzyma, pod kontrolą, na granicy wciąż muzycznie | buczy, wysycha albo wydaje niemuzyczne dźwięki na granicy | dolnoprzepust i poziom suba (1.2 / 1.4); ochrona głośnika |
| c07 | góra / sybilanty | Góra i sybilanty | „s” i „sz” naturalne, ani się nie odrywają, ani nie znikają; talerze — trwałe migotanie | sybilanty odrywają się lub znikają; talerze jak żuta folia albo głuche „pssz” | punktowe cięcia w warstwie wirtualnej (3.3); styk średniotonowy↔wysokotonowy (1.3) |
| c08 | kłucie w głosie | Głos — kłujące pasma w średnicy | naturalny głos, osadzony w piersi, bez nacisku | wierci w uszach, naciska albo brzmi anorektycznie, bez ciała | własne pasmo kłucia (3.3) — nie fundament |
| c09 | głębia | Głębia i przestrzeń | scena za maską, warstwy czytelne, szept pod solówką wciąż słyszalny | płaski obraz, wszystko z przodu | styk średniotonowy↔wysokotonowy (1.3) albo góra gorętsza od basu (3.3) |
| c10 | separacja | Separacja pod obciążeniem | mikrozdarzenia zostają osobno, gdy miks jest gęsty | papka, nuda albo przytłoczenie | zwykle za dużo EQ — zdejmij część (2.1 / 3.3); rzadko styk (1.3) |
| c11 | atak | Atak i transjenty | początek uderzenia ostry, bębny napięte | początki rozmyte, bębny miękkie | kontrola wzmacniacza i głośników, nie EQ; styk midbas↔średniotonowy (1.3) |
| c12 | uniwersalność | Uniwersalność między nagraniami | różne nagrania brzmią różnie | „następna w radiu” — wszystko podobne | nachylenie albo przesada w EQ (3.3) |
| c13 | długi odsłuch | Długi odsłuch — album, 15–20 min, na luzie | pozostaje lekki i zapraszający | męczy: grubo, jasno lub ciemno (nachylenie), albo martwo, sucho, klinicznie (przekorygowanie) | nachylenie → szerokie nachylenie po MMM, nigdy wąskie wycięcia; martwo → zdejmij EQ, nie dodawaj (3.3) |
| c14 | tekstura basu | Tekstura niskich częstotliwości — kontrabas | sprężyście, z ciałem i detalem | nadęty, dudniący albo przesuszony i cienki | poziomy i szew sub↔midbas (1.3 / 1.4); szerokie nachylenie (3.3) |
| c15 | wysokość / szerokość | Wysokość i szerokość sceny — wyższa liga | scena na wysokości deski rozdzielczej i sięga za słupki A z czystymi krawędziami | opada na podłogę na niektórych nutach, albo krawędzie postrzępione i scena się sypie | styk średniotonowy↔wysokotonowy (1.3); poziomy L/R (1.4) — druga wizyta w fazie 4 |
| c17 | +6 dB | To samo, o dwa lub trzy kroki głośności głośniej | balans, punch i głosy trzymają to, co trzymały na poziomie roboczym | coś, co było równe, zaczyna naciskać, albo pojawia się ostrość, której nie było | to, na co wskazuje cichsze przejście — ale werdykt GŁOŚNIEJ to ten, który słyszy sędzia (EMMA Judge Book 2024 §4.5, „Overall Spectral Balance at higher volume”) |
| c16 | dynamika | Dynamika przy głośności — zapas | od cicho do głośno bez wysiłku, szczyty czyste | szczyty się spłaszczają lub zniekształcają, dźwięk dusi się przy głośności | struktura wzmocnienia i granice głośników — nie EQ; filtry ochronne (1.2) |

Kolejność ma znaczenie: **najpierw c01 – c03.** Jeśli środek albo pozycje nie przechodzą, reszty za
wcześnie oceniać.

## Która korekta wskazuje na którą cechę

Narzędzia EQ podają cechę przy każdej propozycji, więc ucho sprawdza to samo, co poruszył pomiar
(`eq_propose`, `ear_suspects`):

| korekta | cecha |
|---|---|
| kształt L/R pary (`lr:*`) | c01 środek mono, c02 pozycje |
| rezonans suba / midbasu albo to, co *dudni* (`res:low`, `boom`, `boxy`) | c14 tekstura basu, c05 punch / szew, c06 sub < 40 |
| rezonans średnicy, to, co *nosowe* lub *kłuje* w średnicy (`res:mid`, `nasal`, `harsh`) | c08 kłucie w głosie |
| rezonans tweetera, to, co *kłuje* lub jest *syczące* (`res:high`, `harsh`, `sibilant`) | c07 góra / sybilanty |
| barwa pary względem celu (`tone:*`) | c04 balans tonalny |

Jedna reguła dla nich wszystkich: pasmo, którego A/B nie słyszy, to pasmo, którego strojenie nie potrzebuje.

## Trasy — uporządkowane pary utwór × cecha

Trasa to tylko kolejność. Słowa pochodzą z tabeli wyżej; gdzie słuchać w utworze — z wiersza powiązania
w `test-tracks.md`. `first` to pięciominutowe poznanie; `short` mieści się w jednym posiedzeniu między
przejażdżkami; `full` jest na zamknięcie albo przed zawodami, w kilku posiedzeniach, z długim odsłuchem
jako osobną przejażdżką.

| route | # | track | characteristic |
|---|---|---|---|
| first | 1 | own/favourite | c04 |
| first | 2 | mono/merrill | c01 |
| first | 3 | CarMus#01 | c04 |
| short | 1 | mono/merrill | c01 |
| short | 2 | CarMus#02 | c04 |
| short | 3 | CarMus#26 | c05 |
| short | 4 | CarMus#06 | c07 |
| full | 1 | mono/merrill | c01 |
| full | 2 | EMMA/positions | c02 |
| full | 3 | CarMus#07 | c03 |
| full | 4 | CarMus#02 | c04 |
| full | 5 | CarMus#26 | c05 |
| full | 6 | CarMus#25 | c05 |
| full | 7 | CarMus#24 | c06 |
| full | 8 | CarMus#06 | c07 |
| full | 9 | CarMus#08 | c08 |
| full | 10 | CarMus#07 | c09 |
| full | 11 | CarMus#15 | c10 |
| full | 12 | CarMus#10 | c11 |
| full | 13 | CarMus#17 | c12 |
| full | 14 | CarMus#11 | c14 |
| full | 15 | own/album | c13 |
| full | 16 | CarMus#02 | c17 |
| full | 17 | CarMus#26 | c17 |
| full | 18 | CarMus#08 | c17 |
| league | 1 | Ch.23 | c15 |
| league | 2 | Ch.05 | c09 |
| league | 3 | Ch.29 | c16 |
| league | 4 | CarMus#26 | c17 |
| league | 5 | CarMus#08 | c17 |

## Cztery nawyki, dzięki którym werdykty z różnych dni są porównywalne

Wyniesione z praktyki i nic nie kosztują (hub `PAS-003`):

1. **Jeden utwór, jedna wada, trzy odpowiedzi.** Zapytaj o JEDNĄ rzecz i przyjmij jedną z opcji: *trzyma ·
   wróciło / inne / lepiej · tak samo · gorzej*. Werdykt sformułowany w ten sposób można zestawić z
   werdyktem z innego dnia; „brzmi dobrze” — nie. **Zapisz przy tym pozycje pokręteł** — werdykt przy
   innej pozycji to werdykt o innym systemie (`process.py … capture-knobs`, `phase_0_baseline.md` §3).
2. **Para utworów na jeden krok.** Jeden pokazuje wadę, drugi pokazuje cenę: lekarstwo wymierzone w
   nosowy nalot w jednym wokalu nie może odebrać osadzenia w piersi innemu (`CarMus#05 ↔ #08`), a góra
   podbita dla jednego utworu musi wciąż przejść ten, który mówi „więcej góry nie trzeba”
   (`AYA/glockenspiel`).
3. **Przejście przy +6 dB** dla wszystkiego, o czym decydujesz (`c17`). Sędziowie tak słuchają (EMMA Judge
   Book 2024 §4.5), a pewnego wieczoru kandydat był „w porządku” na poziomie roboczym i „na krawędzi”
   głośniej — mając tylko ciche przejście, ten werdykt zostałby błędnie odnotowany.
4. **Liczba i ucho obok siebie, żadne nie tłumaczy drugiego na siłę.** W jednej z sesji pomiar mówił:
   „góra jest 2 dB poniżej celu”, a ucho: „więcej góry nie trzeba” — odnotowano oba, a cel określono
   jako NASZ, a nie sędziego. Pomiar, który stoi w sprzeczności z uważnym uchem, to spostrzeżenie, a nie
   błąd do przegadania.

## Dwa presety dla środka — poziomem albo czasem (faza 2c)

Protokół badań (RES-011, wg Lee 2010, notatek Audiofrog do UMI-1, EMMA Judge Book 2024, AES20). **A** to baza, jak
stoi po „każda strona w całości": dojścia wyrównane na fotel, bliska strona przyciągnięta gainem. **B** to to samo
przyciągnięcie czasem: bliska strona później o 0,15–0,30 ms ze zmniejszonym cięciem, głośność wyrównana
(`rew_tool/scene_presets.py`). Oba ciągną środek tak samo daleko; ucho porównuje mechanizm.

**Przed odsłuchem**
1. Mono szum różowy daje JEDEN obraz między głośnikami. Dwa źródła → złe opóźnienie albo polaryzacja, nie centrowanie.
2. Nazwij przewidziane przyciągnięcie każdego presetu (`f` z arkusza, czas i poziom osobno). Para, której przyciągnięcia
   różnią się o mniej niż 10 % pół-sceny, jest „pewnie niesłyszalna — oba są dobre"; B zbudowane z A różni się tylko mechanizmem.
3. Oba presety grają na fotelu równie głośno, w granicach 0,5 dB: cięcie ścisza A, a głośniejszy wygrywa.
4. Kanał centralny na czas porównania wyłączony; fotel i głowa tam, gdzie stał mikrofon; jedna umiarkowana głośność.

**Słuchaj**
5. Mono szum różowy w całym paśmie, potem pasmami (UMI-1, utwory 2–5): jeden punkt? Gdzie?
6. Utwór z pięcioma pozycjami (EMMA, utwory 2–6, albo UMI-1, utwory 6–10): **czy C jest dokładnie pośrodku między
   najdalszym lewym i prawym, które słyszysz, a LC i RC znów pośrodku?** Zapisz miejsce i rozmiar każdego obrazu.
7. Głos pośrodku, potem **wybrzmiewający** wysoki instrument pośrodku (smyczki, organy, trzymana trąbka): to samo miejsce?
   Środek, który wędruje z wysokością dźwięku, sędziowie odejmują; podejrzany jest panning czasem.
8. Przesuń głowę o 3–5 cm w lewo i w prawo: jak daleko środek idzie za nią i czy się rozdwaja?

**Przełączaj i kończ**
9. Ten sam fragment, szybkie przełączanie, A-B-B-A, trzy rundy; w ciemno, jeśli przycisk może nacisnąć ktoś inny.
10. **Stop**, gdy trzy rundy nie dają stałej różnicy (w ciemno: 4 lub mniej trafień z 6): zostaje A, które ma mniej
    ustawień. Usłyszaną różnicę nazwij słowami sceny — miejsce, rozmiar, wysokość, głowa — i wtedy wybierz.
11. **Jeśli środek wędruje z wysokością w OBU presetach, przerwij centrowanie:** to niedopasowanie pasma L/P — wróć do 2a,
    najpierw dopasuj pary.

## Jak zgłaszać, co słyszysz

Nazwij cechę, kierunek i utwór: *„CarMus#07 — kontrabas się nadyma; wokal trzyma”* — to pełny raport.
Binarnie też dobrze: 🟢 / ❌ na parę. Sesja zapisuje każdy werdykt w dzienniku projektu w chwili, gdy
pada (`process.py listening-verdict`: kilka par i Twoje własne słowa w jednym wpisie, ze znacznikiem
wersji ledgera, której słuchałeś), i prowadzi każde ❌ do jego kroku; większość poprawek robi się przy
stole z już zebranych solo — nowy pomiar jest potrzebny tylko wtedy, gdy zmienił się sprzęt albo
instalacja. Spojrzenie wstecz to filtr po dzienniku: wszystkie werdykty dla jednego utworu albo jednej
cechy, po wersjach.
