# Autosound Tuning Skill

🇬🇧 [English](README.md) · 🇩🇪 **Deutsch** · 🇵🇱 [Polski](README.pl.md) · 🇺🇦 [Українська](README.uk.md) · ❓ [FAQ](FAQ.md) · <img src="assets/icons/roadmap.svg" width="14" height="14" valign="middle" alt="Roadmap" /> [Roadmap (EN, Entwurf)](ROADMAP.md)

**In einem Satz:** ein KI-Assistent für das Einmessen deines Autos. Er liest deine REW-Messungen,
entwirft die Abstimmung am Schreibtisch aus einer einzigen Messsitzung und führt dich durch
Trennfrequenzen, Laufzeiten, Phase und EQ — eine geprüfte Änderung nach der anderen.

- **Arbeitet mit REW**: holt deine Messungen über dessen API und gibt den fertigen EQ als Datei
  zurück, die dein DSP importiert.
- **Entwirft am Schreibtisch, prüft im Auto** *(3.x)*: eine disziplinierte Messsitzung, danach
  werden Trennfrequenz, Laufzeit und jeder Filter an der **vorhergesagten** Summe deiner eigenen
  gemessenen Chassis gewählt — und das Auto bekommt einen kurzen Besuch zur Bestätigung.
- **Erst Diagnose, dann Eingriff**: Reflexionen, Auslöschungen und Chassis-Resonanzen des Innenraums
  werden aus den Basismessungen bestimmt, bevor irgendetwas vorgeschlagen wird — und eine Senke, die
  EQ füllen kann, wird von einer Auslöschung unterschieden, die er nicht füllen kann.
- **Fasst deinen Prozessor nie an**: im Auto ändert sich nichts, solange du es nicht selbst
  einträgst. Abtippen heißt das nicht: das Helix PC-Tool importiert den exportierten EQ in einem
  Zug, REWs Generic-Format deckt die meisten anderen Prozessoren ab, und für die ohne Dateiimport —
  Musway, ESX, Zapco — gibt es einen
  [Copy-Paste-Helfer](https://github.com/IvanBakhmutov/REW-EQ-CopyPaste-Assistant).
- **Kennt das Handwerk**: Zielkurven, Schutzfilter, die Reihenfolge „Phase zuerst", einen Prozess
  Schritt für Schritt, und welcher Testtrack wofür da ist.
- **Lernt dein System kennen**: sammelt Wissen über dein Auto und deine Technik — nur mit deiner
  Zustimmung.

## Im Wettbewerb bewiesen

Mit der **2.x-Linie** dieser Methode hat mein eigenes Auto 2026 vier Auszeichnungen geholt:

- **1. Platz, Einsteiger 5000 — AYA, Lemgo, 30. Mai 2026.** Mit Graphenanalyse und Gemini als
  Ratgeber: der Arbeitsablauf, aus dem später dieser Skill wurde.
- **1. Platz, Amateur 5000 — AYA, Horst, 25. Juli 2026.** Eine Klasse höher, mit dem Skill selbst
  und den eigenen Ohren.
- **2. Platz, Amateur 5000 — AYA, Schmallenberg, 15. August 2026.** Ein anderer Klangrichter als im
  Juli; sein Wertungsbogen ist der Eingang für die nächste Runde.
- **3. Platz, SQ Entry Unlimited — EMMA Sound Off 2026, Schmallenberg, 15. August 2026.** Erster
  Antritt nach EMMA-Reglement, am selben Tag und mit derselben Abstimmung wie das AYA oben.

<p align="left">
  <img src="assets/awards/aya-may26-einsteiger5000.jpg" width="100" alt="AYA Mai 2026, Einsteiger 5000, 1. Platz">
  &nbsp;&nbsp;&nbsp;
  <img src="assets/awards/aya-jul26-amateur5000.jpg" width="100" alt="AYA Juli 2026, Amateur 5000, 1. Platz">
  &nbsp;&nbsp;&nbsp;
  <img src="assets/awards/aya-aug26-amateur5000.jpg" width="100" alt="AYA August 2026, Amateur 5000, 2. Platz">
  &nbsp;&nbsp;&nbsp;
  <img src="assets/awards/emma-aug26-entry-unlimited.jpg" width="60" alt="EMMA Sound Off 2026, SQ Entry Unlimited, 3. Platz">
</p>

*Dein Pokal könnte hier stehen.*

> [!CAUTION]
> KI kann sich in Zahlen irren. Prüfe Trennfrequenzen, Flankensteilheiten und EQ-Werte im Prozessor
> immer nach, bevor du stummschaltest — bei Hochtönern besonders — und fang leise an.

## Wähle deinen Weg

Vier Wege hinein, von „das Ganze in einem Desktop-Fenster" bis „heute Abend im Browser ausprobieren".
Es ist dieselbe Methode; verschieden sind der Grad der Automatisierung, wie erprobt sie ist und was
sie dich an Einrichtung kostet. **Die Auszeichnungen oben stammen von Weg 3.**

| Nr. | Weg | Was du brauchst | Was du bekommst | Der Haken |
| :-- | :--- | :--- | :--- | :--- |
| **1** | **3.x im Fenster** — der [Ein-Zeilen-Installer](#loslegen), der [TCC](https://github.com/ayukhno/autosound-tcc) gleich mitbringt | Ein kostenpflichtiges Claude-Abo, eine REW-Beta mit eingeschalteter API und rund 700 MB Plattenplatz; Claude Code und Python bringt der Installer selbst mit | Die ganze Methode mit DSP-Baum, deinen REW-Kurven, dem Plan und der KI nebeneinander in einem Fenster — macOS und Windows — über denselben Projektdateien wie im Terminal | Eine Vorabversion, und die App ist jünger als die Methode, die sie ausführt. Modelle außer Claude und Gemini kommen über `omp` und werden getrennt abgerechnet |
| **2** | **3.x im Terminal** — derselbe Installer mit `--terminal` | Dasselbe, ohne die App | Das Projekt als Daten (ein Register, aus dem du in einem Schritt zurückrollst), der Schreibtisch-Weg, EQ in Paketen durch Gates, die Eingabekontrolle, Werkzeuge, die **verweigern** statt „keine Einwände" zu melden, und Korrekturen, die dich als Tags erreichen | Eine Vorabversion: die abschließende vollständige Abstimmungsprüfung vor 3.1.0 läuft noch. Alles passiert in Text |
| **3** | **Die 2.x-Linie — die erprobte** ⭐ [`v2.8.3`](https://github.com/ayukhno/autosound-tuning-skill/releases/tag/v2.8.3), Branch [`2.x`](https://github.com/ayukhno/autosound-tuning-skill/tree/2.x) | Claude Code + ein kostenpflichtiges Claude-Abo, eine REW-Beta mit eingeschalteter API, ein `/plugin install` | Die vollständige iterative Methode: REW über die API gelesen, die Analyse-Skripte, die Schleife Generator ↔ Kritiker ↔ Schiedsrichter. **Die vier Auszeichnungen oben wurden damit erarbeitet** | Nur Terminal, keine App. Das Projekt ist Prosa, der gültige Stand wird also nachgelesen statt maschinell geprüft; der Schreibtisch-Weg und die neueren Werkzeuge fehlen. Ab hier nur noch Korrekturen |
| **4** | **Web-Chat, nichts installiert** — der Branch [manual_step-by-step](https://github.com/ayukhno/autosound-tuning-skill/tree/manual_step-by-step) | Browser, kostenloses Gemini oder ein beliebiger Chat, REW zum Messen und Exportieren | Die Schritte der Methode als Copy-Paste-Prompts; eine Passdatei mit den Einstellungen deines Autos, die bei jedem Schritt vollständig neu geschrieben wird | Alles von Hand: keine REW-Automatik, kein Gedächtnis zwischen den Schritten, keine zweite KI als Prüfer. Kostenlos — und der schwächste der vier |

**Kurz.** Die aktuelle Methode wollen und lieber sehen als tippen — Weg 1. Im Terminal zu Hause —
Weg 2. Genau das haben wollen, was die Pokale geholt hat — **Weg 3**, und kein Update holt dich
davon herunter. Die Methode erst ausprobieren, bevor etwas installiert wird — Weg 4, dann
entscheiden. Die Wege 1, 2 und 3 lesen dein Auto über REWs API und schreiben nie in deinen
Prozessor.

Die Einzelheiten — was der Installer wohin legt, was sich in 3.x geändert hat und wie man von einem
Weg auf den anderen wechselt — stehen im [FAQ](FAQ.md#choosing-a-path) (auf Englisch).

## Inhalt

- [Wähle deinen Weg](#wähle-deinen-weg)
- [Für wen das ist](#für-wen-das-ist)
- [Was du brauchst](#was-du-brauchst)
- [Loslegen](#loslegen)
- [Wie eine Abstimmung abläuft](#wie-eine-abstimmung-abläuft)
- [Wie sich eine Sitzung anhört](#wie-sich-eine-sitzung-anhört)
- [Welche Modelle](#welche-modelle)
- [Die Mathematik darunter](#die-mathematik-darunter)
- [Was hier drin ist](#was-hier-drin-ist)
- [Ein Problem melden](#ein-problem-melden)
- [Deine Erfahrung beitragen](#deine-erfahrung-beitragen)
- [Unterstützen](#unterstützen)
- [Lizenz](#lizenz)

## Für wen das ist

Für alle, die den Klang im eigenen Auto aufbauen und das Handwerk lernen. Es ist dein Exoskelett:
es trägt das Wissen und die Erfahrung, du bringst die Ohren und die Hände am DSP mit.

Einmessen ist eine Lawine. Es gibt mehr Methoden, Parameter und Faustregeln, als ein Kopf hält, und
man taucht schnell in ein Detail ab und verliert das Ganze. Der Skill hält das Wissen, zeigt auf die
wenigen Änderungen, die etwas bewirken, und behält den Kompromiss zwischen Bühne und Tonalität im
Blick. Dein Ohr entscheidet zuletzt.

Er deckt eine vollständige Abstimmung ab: vom neuen Projekt über Trennfrequenzen, Laufzeiten, Phase,
kanalweisen und summierten EQ bis zur Bühne und zum Abschmecken nach Geschmack — dazu die optionalen
räumlichen Ebenen (ein ergänzender **Center-Fill** und ein differenzieller **Rear-Fill**, beide im
Feld erprobt). Jede Änderung durchläuft die Schleife **Generator ↔ Kritiker ↔ Schiedsrichter**: eine
KI schlägt vor, eine andere widerspricht, du entscheidest.

## Was du brauchst

**Eine frische Maschine ist der Normalfall.** Entwicklerwerkzeuge — Python, git, Claude Code —
müssen nicht vorher da sein: der Installer unten bringt sie mit, dazu die Methode, die App und den
Gemini-Prüfer.

Was er dir nicht besorgen kann, weil es deins ist:

- **[REW](https://www.roomeqwizard.com/) — eine Beta-Version** mit eingeschalteter API. Alles, was
  der Skill über dein Auto weiß, kommt darüber, und **die API gibt es nur in den Betas**: die
  Release-Version (V5.31.3, Juli 2024) hat den Reiter *API* in den Einstellungen gar nicht — und
  genau die liefert dir die Websuche. Nimm den Build von
  [roomeqwizard.com/beta.html](https://www.roomeqwizard.com/beta.html) — die Dateien liegen bei
  AV NIRVANA, dem REW-Forum. Dann in REW: *Preferences → API*, **Start the API when REW starts**
  ankreuzen und **Start server** drücken; das Feld meldet dann *„API server is running on port
  4735"*, und ab da kommt sie mit REW hoch. Dieses Feld ist unter macOS und Windows gleich; unter
  Windows legt der Installer zusätzlich eine Verknüpfung **REW (API on)** auf den Desktop, die REW
  mit eingeschalteter API startet. **Lass REW offen**, solange du abstimmst: die Methode liest die
  Messungen aus dem laufenden Fenster über diese API, nicht aus exportierten Dateien.
- **Ein kalibriertes Messmikrofon und einen DSP, in den du eintippen kannst.** Jeder Prozessor geht.
  Für Phase und Zeit schlägt XLR mit physischem Loopback die USB-Variante:
  [warum, im FAQ](FAQ.md#measuring-phase--time-alignment-umik-1-vs-xlr-microphones).
- **Ein kostenpflichtiges Claude-Abo (Pro oder Max).** Siehe
  [die Pläne und was eine Sitzung kostet](FAQ.md#subscription-options-quotas--budgets-as-of-july-2026).
- **Netz dort, wo das Auto steht.** Die KI läuft in der Cloud, also endet die Sitzung in einer
  Tiefgarage ohne Empfang, bevor sie beginnt — sorg vorher für Mobilfunk oder WLAN. Die Skripte und
  die Messungen selbst brauchen kein Netz; das Gespräch schon.

Eine zweite KI als Prüfer ist optional und trägt den größten Teil des Nutzens. Der Installer bringt
dafür Googles `agy` mit und bietet die Anmeldung am Ende an; ohne ihn arbeitet der Skill allein und
sagt dir das — nachrüsten kannst du jederzeit.

**Ein GitHub-Konto lohnt sich, nötig ist es für die Installation nicht.** Die Installation verlangt
nirgends eine Anmeldung, und beide Repositories sind öffentlich. Der Grund für ein Konto ist dein
eigenes Projekt — und gemeint sind nicht die rohen Sweeps: die sind 16 bis 112 MB pro Stück, sie
bleiben auf deiner Platte, und bräuchtest du sie je wieder, würdest du neu messen. Aufzuheben lohnt
sich, was du **geschlussfolgert** hast: das Register jeder Trennfrequenz, Laufzeit, Verstärkung und
jedes Filters, das Journal, wie du dahin gekommen bist, die DSP-Sicherungen, die die Abstimmung
zurückholen, die Zielkurven und die Analysenotizen. Kleine Dateien — und kein Nachmessen bringt sie
zurück. Der Installer fragt, ob du sie in ein **privates** GitHub-Repository sichern willst, und
richtet dafür `gh` ein; die Sicherung selbst passiert, wenn du die KI darum bittest — sie weiß, was
draußen bleibt. Ein kostenloses Konto reicht.

## Loslegen

Eine Zeile installiert alles: Claude Code, die Methode, die
[TCC-App](https://github.com/ayukhno/autosound-tcc), Gemini als Prüfer und `omp`, das der App
Modelle jenseits von Claude erlaubt. Sie zeigt, was schon da ist, listet alles auf, was sie lädt,
und woher, fragt einmal — und läuft dann zehn bis zwanzig Minuten allein. Die einzige Unterbrechung
kommt direkt nach dieser Frage: auf einem Mac, mit dem nie programmiert wurde, fragt sie einmal nach
deinem Mac-Passwort, für Apples Command Line Tools; unter Windows zeigt sie einen Berechtigungsdialog
für Git. Am Ende meldet sie dich im Browser an: zuerst Claude (das ist Pflicht), dann Prüfer und
GitHub, falls gewünscht — jeweils mit Enter oder später.

*(Das sind die Wege 1 und 2 aus [der Auswahl](#wähle-deinen-weg). Für Weg 3 — den mit den Pokalen —
stehen die beiden Plugin-Befehle im [README des 2.x-Branches](https://github.com/ayukhno/autosound-tuning-skill/blob/2.x/README.md#getting-started).)*

**macOS** — Terminal öffnen (⌘-Leertaste, „terminal" tippen, Enter) und einfügen:

```sh
curl -fsSL https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/main/install.sh | bash
```

**Windows** — PowerShell öffnen (Start, „powershell" tippen, Enter) und einfügen:

```powershell
irm https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/main/install.ps1 | iex
```

Etwas weglassen: `--terminal` (ohne App), `--no-reviewer`, `--no-github` oder `--no-omp`, nach
`bash -s --` unter macOS; unter Windows dieselben vier als `-Terminal`, `-NoReviewer`, `-NoGitHub`,
`-NoOmp` in der Form `& ([scriptblock]::Create((irm <diese URL>))) -Terminal`. Dieselbe Zeile noch
einmal ausgeführt aktualisiert alles; `--uninstall` / `-Uninstall` entfernt, was der Installer
angelegt hat, und nie einen Projektordner.

Dann anfangen. Leg einen Ordner für das Auto an — alles zu diesem Auto lebt darin, eine Kopie des
Ordners ist also eine Kopie der ganzen Abstimmung — und öffne ihn auf einem der beiden Wege:

**Im Terminal.** Öffne ein **neues** Terminalfenster (das, aus dem du installiert hast, sieht das
gerade Installierte nicht), dann:

```sh
mkdir -p ~/Autosound/mein-auto && cd ~/Autosound/mein-auto
```

```sh
claude
```

*Und dann anfangen mit:* **„tune a new car from scratch"** (oder auf Deutsch: „lass uns das Auto von
Grund auf einmessen").

**In der App.** Doppelklick auf **Autosound TCC** auf dem Desktop, *Browse…* zum Ordner (ein neuer,
leerer ist richtig), Modelle wählen — Claude Opus (SDK) als *AI main*, Gemini Pro (High) als *AI
critic* — *Open* drücken und dasselbe im Panel rechts sagen, in beliebiger Sprache.

Beides ist ein Projekt, nicht zwei: die Methode schreibt die Projektdateien, die App liest sie — du
kannst heute im Fenster arbeiten und morgen im Terminal.

> **Auslöser: ein Wort aus dem Car-Hifi.** Der Skill wacht bei dem auf, **was du fragst**, ein bloßes
> `resume` zündet ihn also nicht — das könnte jedes Projekt sein. Nimm ein Wort aus der Domäne dazu:
> **„Auto-DSP weiter einmessen"**, **„continue tuning the car"**, **„wie ist mein aktueller
> Trennfrequenz-Stand"**. Dasselbe für den Start: nenne das Auto oder den Klang, nicht nur „hilf
> mir".

> **Modell und Aufwand VOR der ersten Nachricht setzen.** Beides gilt für die Sitzung und wird
> danach von nichts mehr angehoben. Stand August 2026: **Claude Opus auf `xhigh`**, geprüft von
> **Gemini Pro (High)**. [Warum die billigeren Kombinationen leise scheitern](#welche-modelle).

Du kommst vom **2.x-Plugin** oder willst **Gemini** als Fahrer? Beides steht im FAQ:
[Wechsel 2.x → 3.x](FAQ.md#moving-from-2x-to-3x) (erst das Plugin entfernen — zwei Skills gleichen
Namens bleiben beide aktiv) und
[Gemini als Fahrer](FAQ.md#can-i-ask-gemini-to-install-and-run-the-skill-itself-without-claude-code).

## Wie eine Abstimmung abläuft

Beim 3.x-Weg gehst du am Anfang und am Ende ins Auto; die eigentliche Arbeit dazwischen passiert am Schreibtisch. Zwei Fahrten zum Auto,
eine Sitzung am Schreibtisch dazwischen; das **Register** auf der Platte ist die einzige Wahrheit
(alle Trennfrequenzen, Laufzeiten, Pegel, Polaritäten und Filter, jeweils mit der Version, in der
sie entstanden), und jeder Vorschlag landet dort als neue Version, aus der du in einem Schritt
zurückrollst.

1. **Vorbereitung, am Schreibtisch.** Das Auto, die Chassis, der DSP und was er kann, das Mikrofon
   und die Zielkurve — geklärt, bevor jemand im Auto sitzt, damit dort nichts überrascht.
2. **Eine Messsitzung, im Auto.** Jedes Chassis allein, nur mit **Schutzfiltern** — ein Hochpass auf
   Mittel- und Hochtönern und sonst nichts —, damit die Aufnahme das Chassis und den Innenraum
   trägt, nicht eine Abstimmung. Ein Tiefmitteltöner (TMT) in der Tür ohne Tiefpass klingt oben rau: das sind
   Membranaufbruch, genau den soll der Sweep zeigen, und kaputt geht dabei nichts.
   Sweeps und eine Wedelmessung in einem Zug, dazu ein paar Kontrollpositionen um
   den Kopf. Bevor du aussteigst, wird die Runde geprüft: sind alle Chassis dabei, ist die Zeit
   zwischen erstem und letztem Sweep stehen geblieben, sind die Schutzfilter protokolliert.
3. **Entwurf, am Schreibtisch.** Trennfrequenzen, Pegel, Laufzeiten und Polarität werden an der aus
   deinen gemessenen Chassis **vorhergesagten** Summe gewählt, mit den Filtern des DSP darin: jeder
   Übergang danach bewertet, wie wenig er verliert, und eine Laufzeit, die um eine ganze Periode
   (360°) danebenliegt, wird beim Namen genannt. Der EQ kommt in Paketen, in dieser Reihenfolge:
   die eigenen Resonanzen eines Chassis (nur wo die Spitze über alle Kontrollpositionen stehen
   bleibt und minimalphasig ist), die Links/Rechts-Form, dann die Tonalität zur Zielkurve. Nur
   Absenkungen, wenn du nichts anderes sagst. Jedes Paket ist eine Entscheidung und eine
   Registerversion; heraus kommt eine Exportdatei für den Prozessor.
4. **Prüfung, im Auto — kurz.** Du trägst die Zahlen aus dem Blatt in den Prozessor ein. Die
   Eingabekontrolle bestätigt Chassis für Chassis, dass am Hörplatz genau das ankommt,
   was am Schreibtisch entworfen wurde — oder benennt das eine, das abweicht, und warum. Danach das, was der
   Schreibtisch nicht kann: Fein-EQ auf dem Mittel der Wedelmessung und A/B mit einem Band nach
   dem anderen, wobei die Methode dein „das schneidet" oder „das dröhnt" in eine kurze, sortierte
   Verdächtigenliste übersetzt — höchstens drei Runden.
5. **Hören.** Testtracks, ein Spickzettel, worauf zu achten ist, und das Urteil, notiert gegen die
   Version, die es verdient hat.
6. **Geschmack.** Presets auf einer virtuellen Ebene, damit die technische Abstimmung darunter
   unangetastet bleibt.

In der App sieht man denselben Weg: den DSP-Baum, die von REW gemessenen Kurven, den Plan mit seinen
Schritten, die Registerversionen und die KI im Seitenpanel. Die App liest dieselben Dateien, die die
Methode schreibt — ein Schritt im Terminal ist im Fenster sichtbar und umgekehrt.

Gehen Schreibtisch und Auto auseinander, fällt der Weg auf die iterative Schleife zurück, mit der
die Pokale geholt wurden, und das Register hält fest, wo. Der ganze Weg, Phase für Phase, steht in
[`references/phases/virtual-first.md`](skills/autosound-tuning/references/phases/virtual-first.md);
die Phasendateien dahinter listet [`SKILL.md`](skills/autosound-tuning/SKILL.md).

## Wie sich eine Sitzung anhört

Drei Stimmen: **du** auf dem Hörplatz, **Claude** führt den Prozess, **Gemini** widerspricht bei
jedem Zug. Eine kurze Veranschaulichung der Schleife auf dem Schreibtisch-Weg — die Form des
Gesprächs, kein Protokoll:

> **Du (Schiedsrichter):** Der Bass ist dünn, und er zieht auf die Beifahrerseite.
>
> **Claude (Generator):** Vor jedem EQ: in der vorhergesagten Summe liegt der Übergang Sub↔TMT bei 80 Hz 4 dB unter jedem der beiden allein. Das ist eine Zeitfrage, keine Tonfrage. Zwei Laufzeiten passen gleich gut auf den Amplitudengang — 3,4 ms und 3,4 minus eine ganze Periode.
>
> **Gemini (Kritiker):** Dann sag, welche davon zur gemessenen Ankunftszeit passt. Ein Kandidat, der um eine ganze Periode danebenliegt, sieht am Übergang identisch aus und bricht eine Oktave darüber völlig ein.
>
> **Claude:** Die aus der gemessenen Impulsantwort gelesene Ankunft sagt 3,4 ms; der Zwilling verliert 2 dB bei 300 Hz. Ich nehme 3,4 — als Version abgelegt, die sich in einem Schritt zurückrollen lässt.
>
> **Du:** Eingetragen. Jetzt mittig — aber ein Ton dröhnt.
>
> **Claude:** Die Eingabekontrolle sagt, am Hörplatz kommt bis auf 0,6 dB das an, was der Schreibtisch vorhergesagt hat — es liegt also nicht an der Laufzeit. 63 Hz bleibt über alle neun Positionen um deinen Kopf stehen, das macht es zum Innenraum, und eine Raummode darf der EQ absenken: ein Band, −4 dB, Q 3, auf dem TMT-Paar.
>
> **Gemini:** Einverstanden — und prüf, dass dieselbe Absenkung nicht zweimal verlangt wird: unter 80 Hz überlappen Sub und TMT.
>
> **Du:** Besser. So bleibt's.

Jeder Schritt dort ist eine von den Werkzeugen gerechnete Zahl statt einer Faustregel, und jeder ist
eine Version im Register, in einem Schritt zurückrollbar. Eine echte Sitzung mit allen Zahlen — ein
harter Fall mit einer Raummode, in dieser Schleife gelöst — steht in
[der Fallstudie](community-inbox/case-studies/case-study-mode-a-bass-2026-07-15.md).

## Welche Modelle

**Generator: Claude Opus, Aufwand `xhigh`. Prüfer: Gemini Pro (High).** Das ist die eine
Kombination, mit der diese Methode von Anfang bis Ende gefahren wurde. Alles andere ist ein
Experiment, das du machst — und als solches zu lesen.

Es zählt wegen der **Form** des Scheiterns. **Ein schwächeres Modell bricht nicht mit einem Fehler
ab, es stimmt dir zu.** Ein dokumentierter Lauf schloss die Phasen −1 bis 3 in einer Sitzung ab und
meldete Trennfrequenzen, Laufzeiten auf 0,1 ms, EQ „innerhalb ±0,5 dB" und ein Hörurteil — für ein
Auto, in dem niemand gesessen hatte. Nichts an diesem Protokoll sah kaputt aus. Es war nur keine
Abstimmung.

| Modus | Aufbau | Verlässlichkeit |
| :--- | :--- | :--- |
| **A: Claude + Gemini** | Claude führt, Gemini prüft | Am höchsten: zwei Perspektiven, langsamer pro Entscheidung |
| **B: Solo** | ein Modell führt und prüft sich selbst | Geringer: eine Perspektive, und seine Zahlen will man nachrechnen |

Womit fahren, nach meiner bisherigen Erfahrung:

* **Opus**, die Voreinstellung fürs Einmessen. Es hält eine lange Sitzung zusammen und entscheidet
  dort, wo ein schwächeres Modell nachfragt. `xhigh` ist die Untergrenze; in den harten Kurven Max.
* **Sonnet**, nicht für eine komplexe Abstimmung. Vorsichtig, und es verliert den Faden, sobald
  Fakten über eine lange Sitzung zusammengeführt werden müssen. Gut für kurze, klar begrenzte
  Schritte.
* **Fable**, für Forschung. Wo es darum geht, einen neuen Ansatz zu finden statt einen bekannten
  anzuwenden, kamen hier die besten Ideen von ihm.
* **Gemini**, als Kritiker, auf einer Pro-Stufe. Als Fahrer ist es unter den aktuellen Regeln
  ungeprüft.

Modelle und Stufen verschieben sich von Monat zu Monat, nimm das also als Ausgangspunkt und nicht
als Urteil, und probier selbst. Was sich nicht verschiebt, ist die Form des Scheiterns: was immer du
wählst — ein Modell, das weniger denken soll, sagt dir das nicht. Einrichtungsdetails, auch ein
kostenloser Prüfer im Browser über Google AI Studio, stehen im [FAQ](FAQ.md) (auf Englisch).

## Die Mathematik darunter

Eine Bibliothek lokaler Skripte zerkaut die großen Datenmengen, damit die Modelle keine Token dafür
ausgeben — und keine Zahl raten, die man rechnen kann:

- **Eine Fehlerkarte von Innenraum und Einbau, vor jeder Abstimmung.** Türauslöschungen, Reflexionen
  und Links/Rechts-„Taschen", die kein Stereo-EQ füllt, werden aus den ersten Sweeps bestimmt —
  damit der EQ-Plan **um** den Innenraum herum arbeitet, statt gegen ihn.
- **Die Summe wird vorhergesagt, nicht erhofft.** Jedes Chassis-Paar wird aus seinen gemessenen
  Antworten mit den Filtern des DSP summiert; Laufzeit und Polarität werden danach gewählt, wie
  wenig der Übergang verliert, der Kandidat eine ganze Periode daneben wird benannt, und vier
  unabhängige Zeitmessungen müssen übereinstimmen, bevor eine Laufzeit angefasst wird.
- **Kein Chassis wird zu physikalisch Unmöglichem gezwungen.** Eine füllbare Senke und eine Interferenz-
  auslöschung sehen im Diagramm gleich aus; unterschieden werden sie über die Excess-Phase (in REW:
  *Excess phase*) — angehoben werden darf nur die füllbare.
- **Der Kurve wird nur dort vertraut, wo sie über alle Messpositionen stabil bleibt.** Die Streuung über die Positionen
  um den Kopf, gemessen **in deinem** Auto, sagt, welche Merkmale stehen bleiben (das Chassis) und
  welche mit dem Mikrofon wandern (der Sitzplatz) — und legt fest, wie schmal ein Filter sein darf,
  Band für Band.
- **EQ kommt als Pakete durch Gates**: Resonanzen → Links/Rechts-Form → Tonalität, standardmäßig nur
  Absenkungen; und „das schneidet" wird zu einer kurzen Verdächtigenliste, sortiert danach, wie laut
  das Ohr sie hört, jede mit einem A/B.
- **Jeder vorgeschlagene Filter wird auf deinen eigenen Messungen simuliert**, bevor du ihn
  eintippst, unter kleinem Laufzeit- und Pegeldrift bewertet — damit er die Wirklichkeit übersteht
  statt an einem Punkt zu gewinnen — und nach der Eingabe von der Eingabekontrolle bestätigt.
- **Eine Prüfung ohne ihre Eingangsdaten VERWEIGERT.** Sie meldet nie „keine Einwände", weil Daten
  fehlen: keine Laufzeit aus einer einzigen Schätzung, kein EQ auf einer Messrunde, die gedriftet
  ist, keine Runde ohne protokollierte Schutzfilter.

Alles, was die Methode kann — nach deiner Absicht sortiert statt nach Dateinamen — steht auf einer
Tafel: [`references/core/capabilities.md`](skills/autosound-tuning/references/core/capabilities.md)
— 67 Fähigkeiten in 13 Richtungen, jede mit dem Befehl, mit dem, was sie braucht und ohne was sie
verweigert, und mit dem Verweis, wo die Begründung steht. Ein Prüfer in der Testsuite hält die Tafel
ehrlich gegenüber dem Code. Jedes `rew_tool`-Modul hat seinen eigenen `--selftest`, verankert an
Definitionen statt an der eigenen Ausgabe, und
[`scripts/run-selftests.sh`](scripts/run-selftests.sh) fährt sie alle.

## Was hier drin ist

```
autosound-tuning-skill/
├── install.sh · install.ps1 · install.cmd    der Installer für macOS und Windows
├── skills/autosound-tuning/                  der Skill (ein Claude-Code-Plugin)
│   ├── SKILL.md         Einstieg — Prozesskarte, Sitzungsablauf, Rollen
│   ├── references/      die Doktrin: core/ (Fähigkeitentafel, Review-Schleife, wovor die
│   │                    Werkzeuge verweigern …), phases/ (−1…5, virtual-first),
│   │                    patterns/, tooling/
│   ├── knowledge/       gesammelte Auto- und DSP-Profile (cars/, dsp/)
│   ├── rew_tool/        REW-Brücke, Analyse, Vorhersage und Prüfung, EQ-Vorschläge,
│   │                    Register und Prozess — jedes Modul mit eigenem --selftest
│   ├── scripts/         der Kanal für Ratgeber / Kritiker (Gemini, Claude, Codex)
│   ├── evals/           wacht der Skill bei der richtigen Anfrage auf
│   └── curves.html      Zielkurven-Visualizer
├── scripts/             Release-Prüfungen: run-selftests.sh, tag-check.sh, installer-consistency.py
├── community-inbox/     Fallstudien und Beiträge aus der Community
└── CHANGELOG.md         jeder Tag mit einer Upgrade-Notiz
```

▶ **[Den Zielkurven-Visualizer online öffnen](https://ayukhno.github.io/autosound-tuning-skill/_curve-visualizer.html?lang=de)** — zieh deine eigene Kurve hinein oder eine Standardkurve aus dem [Nono Tuning Tool](https://nonotuningtool.com), Rechtsklick auf einen Punkt zeigt den Charakter dieser Frequenz, und Kurven lassen sich nebeneinander vergleichen. Eine einzige eigenständige Datei, läuft also offline; mit „Speichern unter" behältst du eine Kopie.

Die Methode der unabhängigen Prüfung (Kritiker/Ratgeber/Schiedsrichter, Anti-Ankereffekt) ist in
[`references/core/review-loop.md`](skills/autosound-tuning/references/core/review-loop.md)
beschrieben.

Die App hat ihr eigenes Repository, [autosound-tcc](https://github.com/ayukhno/autosound-tcc); der
Installer holt von beiden den neuesten Tag — den der App und den der Methode (`v3.*`) — und legt die
Methode nach `~/.claude/skills/autosound-tuning`, wo Claude Code sie findet. Welche App- und welche
Methodenversion bei dir laufen, steht in der App unter *Diagnostics → Installation*.

## Ein Problem melden

Alles, was kaputt war, falsch war oder dich aufgehalten hat: **[ein Issue eröffnen](https://github.com/ayukhno/autosound-tuning-skill/issues/new/choose)**
— das Beta-Formular hat Felder für den Hergang und die Versionen. Es ist der Eingang der Methode
selbst; Probleme mit der App gehören [in deren Repository](https://github.com/ayukhno/autosound-tcc/issues/new/choose),
und TCC füllt die Hälfte dieses Formulars für dich aus (*Diagnostics → Installation → Report a
problem*). Ein Issue lässt sich beantworten, eine Chat-Nachricht nicht.

## Deine Erfahrung beitragen

Der Skill lernt aus jeder Abstimmung: er sammelt Rückmeldungen direkt im Terminal, während du
arbeitest, nicht über ein Formular. Zum Abschluss, wenn du mit dem Klang zufrieden bist, fragt er,
was geholfen hat, was danebenlag und über welche Eigenheit von DSP oder Auto du gestolpert bist.
Danach bietet er **mit deiner ausdrücklichen Zustimmung** an, die **verallgemeinerbaren** Lehren zu
teilen — für die gemeinsame Methode und die Bibliothek `knowledge/`.

Er erfasst **nur Methoden- und Geräteklassen**: das Verhalten des Innenraums, die Geräteklasse,
welche Techniken funktioniert haben. **Nie persönliche Daten, nie vollständige Messungen.** Du
siehst genau, was geteilt wird, und stimmst Punkt für Punkt zu. Bestätigte Lehren fließen mit
Namensnennung in den Skill ein.

## Unterstützen

Der Skill ist **frei und offen** (CC BY-SA) und bleibt es. Nichts hängt hinter einer Bezahlschranke.
Wenn er geholfen hat und du danke sagen willst, gibt es zwei freiwillige Wege:

💜 **[GitHub Sponsors](https://github.com/sponsors/ayukhno)** · ☕ **[Monobank-Sammelglas](https://send.monobank.ua/jar/8wThVcodjm)** — ein Tipp, kein Konto nötig; nimmt Apple Pay, Google Pay, Visa, Mastercard.

## Lizenz

[CC BY-SA 4.0](LICENSE): benutzen, anpassen, weitergeben; Abgeleitetes offen halten und die Quelle
nennen. Es ist Methoden- und Wissensarbeit, und Share-alike hält die Erfahrung der Community offen.

Code und Skripte (`rew_tool/`, `scripts/`, weitere .py/.sh) stehen unter der
[MIT-Lizenz](LICENSE-CODE). Materialien Dritter sind in [LICENSES/NOTICE.md](LICENSES/NOTICE.md)
aufgeführt.
