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
| c16 | dynamika | Dynamika przy głośności — zapas | od cicho do głośno bez wysiłku, szczyty czyste | szczyty się spłaszczają lub zniekształcają, dźwięk dusi się przy głośności | struktura wzmocnienia i granice głośników — nie EQ; filtry ochronne (1.2) |

Kolejność ma znaczenie: **najpierw c01 – c03.** Jeśli środek albo pozycje nie przechodzą, reszty za
wcześnie oceniać.

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
| league | 1 | Ch.23 | c15 |
| league | 2 | Ch.05 | c09 |
| league | 3 | Ch.29 | c16 |

## Jak zgłaszać, co słyszysz

Nazwij cechę, kierunek i utwór: *„CarMus#07 — kontrabas się nadyma; wokal trzyma”* — to pełny raport.
Binarnie też dobrze: 🟢 / ❌ na parę. Sesja zapisuje każdy werdykt w dzienniku projektu w chwili, gdy
pada (`process.py listening-verdict`: kilka par i Twoje własne słowa w jednym wpisie, ze znacznikiem
wersji ledgera, której słuchałeś), i prowadzi każde ❌ do jego kroku; większość poprawek robi się przy
stole z już zebranych solo — nowy pomiar jest potrzebny tylko wtedy, gdy zmienił się sprzęt albo
instalacja. Spojrzenie wstecz to filtr po dzienniku: wszystkie werdykty dla jednego utworu albo jednej
cechy, po wersjach.
