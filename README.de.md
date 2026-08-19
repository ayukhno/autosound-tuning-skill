# Autosound Tuning Skill

🇬🇧 [English](README.md) · 🇩🇪 **Deutsch** · 🇵🇱 [Polski](README.pl.md) · 🇺🇦 [Українська](README.uk.md) · ❓ [FAQ](FAQ.md) · <img src="assets/icons/roadmap.svg" width="14" height="14" valign="middle" alt="Roadmap" /> [Roadmap (EN, Entwurf)](ROADMAP.md)

**In einem Satz:** ein KI-Assistent für das Einmessen deines Autos. Er liest deine REW-Messungen und
führt dich durch Trennfrequenzen, Laufzeitkorrektur, Phase und EQ — eine geprüfte Änderung nach der
anderen.

- **Arbeitet mit REW**: holt deine Messungen über die API und schreibt die berechneten EQ-Filter
  zurück nach REW, von wo du sie exportierst
- **Diagnostiziert, bevor es korrigiert**: findet Reflexionen, Auslöschungen und Verzerrung der
  Chassis in den ersten Sweeps, bevor auch nur eine Änderung vorgeschlagen wird
- **Fasst deinen Prozessor nie an**: im Auto ändert sich nichts, was du nicht selbst einträgst. Das
  heißt aber nicht, alles abzutippen: REW exportiert deinen EQ als Datei, die das Helix PC-Tool in
  einem Zug importiert, und für Prozessoren ohne Dateiimport gibt es einen
  [Copy-Paste-Helfer](https://github.com/IvanBakhmutov/REW-EQ-CopyPaste-Assistant) — Musway, ESX,
  Zapco
- **Kennt das Handwerk**: Zielkurven, die Reihenfolge „erst Phase, dann EQ", einen Schritt-für-
  Schritt-Prozess und welcher Testtrack wofür taugt
- **Lernt dein Setup**: sammelt Wissen über Auto und Technik — nur mit deiner Zustimmung

Mit dieser Methode eingemessen, holte mein eigenes Auto **2026 zwei Klassensiege bei AYA-Wettbewerben**:
Einsteiger 5000 im Mai, mit der Graphenanalyse-und-Gemini-Arbeitsweise, aus der später dieser Skill
wurde, dann Amateur 5000 im Juli mit dem Skill selbst und den eigenen Ohren.

<p align="left">
  <img src="assets/awards/aya-may26-einsteiger5000.jpg" width="100" alt="AYA May 2026 Einsteiger 5000">
  &nbsp;&nbsp;&nbsp;
  <img src="assets/awards/aya-jul26-amateur5000.jpg" width="100" alt="AYA Jul 2026 Amateur 5000">
</p>

> [!CAUTION]
> KI kann sich bei Zahlen irren. Prüfe Trennfrequenzen, Flankensteilheiten und EQ-Werte immer in
> deinem DSP, bevor du stummschaltest — besonders bei Hochtönern — und fang leise an.

> [!NOTE]
> **Lieber ein Fenster als ein Terminal?** [TCC](https://github.com/ayukhno/autosound-tcc), die
> begleitende Desktop-App, fährt dieselbe Methode in einem Fenster: DSP-Baum, deine REW-Kurven, der
> Plan und die KI in einer Seitenleiste. Die eine Zeile unten installiert sie mit, sofern du nichts
> anderes sagst. Sie ist jung — der erprobte Weg ist die Methode im Terminal.

## Inhalt

- [Für wen das ist](#für-wen-das-ist)
- [Was du brauchst](#was-du-brauchst)
- [Loslegen](#loslegen)
- [Wie eine Sitzung wirklich klingt](#wie-eine-sitzung-wirklich-klingt)
- [Welche Modelle](#welche-modelle)
- [Die Mathematik darunter](#die-mathematik-darunter)
- [Was hier drin ist](#was-hier-drin-ist)
- [Erfahrung beitragen](#erfahrung-beitragen)
- [Unterstützen](#unterstützen)
- [Lizenz](#lizenz)

## Für wen das ist

Für alle, die den Klang im eigenen Auto aufbauen und das Handwerk lernen. Er ist dein Exoskelett: er
trägt das Wissen und die Erfahrung, du bringst die Ohren und die Hände am DSP mit.

Einmessen ist eine Lawine. Es gibt mehr Methoden, Parameter und Faustregeln, als ein Mensch im Kopf
behält, und man taucht schnell in ein Detail ab und verliert das Ganze. Der Skill hält das Wissen,
zeigt auf die wenigen Änderungen, die zählen, und behält den Kompromiss zwischen Bühne und
tonaler Balance im Blick. Der letzte Richter ist dein Ohr.

Er deckt ein komplettes Tuning ab: vom neuen Projekt über Trennfrequenzen, Laufzeit, Phase, EQ pro
Kanal und in Summe bis zur Abbildung und zum Abstimmen nach Geschmack — dazu die optionalen
räumlichen Schichten (ein komplementärer **Center-Fill** und ein differenzieller **Rear-Fill**,
beide im Feld erprobt). Jede Änderung läuft durch die Schleife **Generator ↔ Kritiker ↔
Schiedsrichter**: eine KI schlägt vor, eine andere widerspricht, du entscheidest.

## Was du brauchst

**Eine frische Maschine ist der Normalfall.** Der Installer unten bringt Claude Code, Python, die
Methode, die Desktop-App und den Gemini-Reviewer mit. Vorher muss nichts installiert sein.

Drei Dinge kann er dir nicht besorgen, weil sie dir gehören:

- **[REW](https://www.roomeqwizard.com/) — eine Beta-Version**, mit eingeschalteter API. Alles, was
  der Skill über dein Auto weiß, kommt dadurch, und **die API gibt es nur in den Betas**: die
  Release-Version (V5.31.3, Juli 2024) hat in den Einstellungen überhaupt keinen *API*-Reiter — und
  genau die findet die Websuche. Hol die Version hier:
  [roomeqwizard.com/beta.html](https://www.roomeqwizard.com/beta.html) — die Dateien liegen bei
  AV NIRVANA, dem REW-Forum. Dann in REW: *Preferences → API* öffnen, **Start the API when REW
  starts** anhaken und **Start server** drücken; das Feld zeigt dann *"API server is running on port
  4735"*, und ab da kommt sie mit REW hoch. Dieses Feld ist unter macOS und Windows gleich; unter
  Windows legt der Installer zusätzlich eine Verknüpfung **REW (API on)** auf den Desktop, die REW
  mit eingeschalteter API in einem Klick startet.
- **Ein kalibriertes Messmikrofon und ein DSP, in den du Werte eintippen kannst.** Jeder Prozessor
  geht. Für Phase und Laufzeit schlägt XLR mit physischem Loopback die USB-Lösung:
  [warum, im FAQ](FAQ.md#measuring-phase--time-alignment-umik-1-vs-xlr-microphones).
- **Ein bezahltes Claude-Abo (Pro oder Max).** Siehe
  [die Tarife und was eine Sitzung kostet](FAQ.md#subscription-options-quotas--budgets-as-of-july-2026).

Eine zweite KI als Reviewer ist optional — und genau daher kommt der größte Teil des Nutzens. Der
Installer bringt dafür Googles `agy` mit und bietet die Anmeldung am Ende an; ohne Reviewer läuft
der Skill allein und sagt dir das auch, und du kannst ihn später nachrüsten.

**Ein GitHub-Konto lohnt sich und ist zum Installieren nicht nötig.** Die Installation meldet dich
nirgends an, beide Repositories sind öffentlich. Der Grund für ein Konto ist dein eigenes Projekt —
und zwar nicht die rohen Sweeps: die sind 16 bis 112 MB pro Stück, bleiben auf deiner Platte, und
wenn du sie je wieder bräuchtest, würdest du neu messen. Bewahrenswert ist alles, was du
*geschlossen* hast: das Register jeder Trennfrequenz, Laufzeit, Verstärkung und jedes Filters, das
Journal des Wegs dorthin, die DSP-Backups, die das Tuning wiederherstellen, die Zielkurven und die
Analysenotizen. Kleine Dateien, die kein Nachmessen zurückbringt. Der Installer fragt, ob sie in ein
**privates** GitHub-Repository gesichert werden sollen, und legt dafür GitHubs `gh` bereit und
meldet es an; das Sichern selbst passiert, wenn du der KI sagst, sie soll das Projekt sichern — sie
weiß, was draußen bleibt. Ein kostenloses Konto reicht.

## Loslegen

Eine Zeile installiert alles: Claude Code, die Methode, die
[TCC-Desktop-App](https://github.com/ayukhno/autosound-tcc), Gemini als Reviewer und `omp` — das ist
es, was der App andere Modelle als Claude anbieten lässt. Sie zeigt, was schon auf der Maschine ist,
listet alles auf, was sie herunterlädt und woher, fragt einmal — und läuft dann zehn bis zwanzig
Minuten allein weiter. Die eine Unterbrechung kommt direkt nach dieser Frage: auf einem Mac, mit dem
nie programmiert wurde, fragt sie einmal nach deinem Mac-Passwort für Apples Command Line Tools;
unter Windows zeigt sie einen Berechtigungsdialog, für Git. Am Ende meldet sie dich im Browser an:
zuerst Claude (das ist Pflicht), dann Reviewer und GitHub, wenn du sie willst — jeweils mit Enter,
oder später.

**macOS** — Terminal öffnen (⌘-Leertaste, "terminal" tippen, Enter) und einfügen:

```sh
curl -fsSL https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/main/install.sh | bash
```

**Windows** — PowerShell öffnen (Start, "powershell" tippen, Enter) und einfügen:

```powershell
irm https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/main/install.ps1 | iex
```

Um etwas wegzulassen: `--terminal` (ohne App), `--no-reviewer`, `--no-github` oder `--no-omp`, unter
macOS nach `bash -s --`; unter Windows dieselben vier als `-Terminal`, `-NoReviewer`, `-NoGitHub`,
`-NoOmp` in der Form `& ([scriptblock]::Create((irm <diese URL>))) -Terminal`. Dieselbe Zeile
nochmals ausgeführt **aktualisiert** alles; `--uninstall` / `-Uninstall` entfernt, was der Installer
angelegt hat — und nie einen Projektordner.

Dann geht es los. Leg einen Ordner für das Auto an — alles zu diesem Auto lebt darin, eine Kopie des
Ordners ist also eine Kopie des ganzen Tunings — und öffne ihn auf einem der beiden Wege:

**Im Terminal.** Öffne ein *neues* Terminalfenster (das, aus dem du installiert hast, sieht das
gerade Installierte nicht), dann:

```sh
mkdir -p ~/Autosound/my-car && cd ~/Autosound/my-car
```

```sh
claude
```

*Dann starte das Tuning mit:* **„messen wir ein neues Auto von Grund auf ein"**.

**In der App.** Doppelklick auf **Autosound TCC** auf dem Desktop, *Browse…* zum Ordner (ein neuer,
leerer ist richtig), die Modelle wählen — Claude Opus (SDK) als *AI main*, Gemini Pro (High) als
*AI critic* — *Open* drücken und dasselbe im Panel rechts sagen, in jeder Sprache:
*„lass uns dieses Auto von Grund auf einmessen"*.

Das ist ein Projekt, nicht zwei: die Methode schreibt die Projektdateien, die App liest sie — du
kannst einen Tag im Fenster und den nächsten im Terminal arbeiten.

> **Auslösen: nimm ein Car-Audio-Wort dazu.** Der Skill wacht davon auf, *was du fragst*, ein nacktes
> `resume` weckt ihn also nicht — das könnte jedes Projekt meinen. Nimm ein Fachwort dazu:
> **„Auto-DSP weiter einmessen"**, **„weiter mit dem Einmessen"**, **„wie ist der aktuelle DSP-/
> Trennfrequenz-Stand"** — oder in deiner Sprache („продовжити тюн авто", "wróćmy do strojenia car
> audio", "resume my car-audio tune"). Dasselbe für den Neustart: nenne das Auto oder den Klang,
> nicht nur „hilf mir".

> **Modell und Aufwand vor der ersten Nachricht setzen.** Beide sind für die Sitzung fest, und
> nichts hebt sie später an. Stand August 2026: **Claude Opus auf `xhigh`**, mit **Gemini Pro
> (High)** als Reviewer. [Warum die billigeren Kombinationen leise versagen](#welche-modelle).

<details>
<summary>Andere Wege hinein: Gemini als Fahrer, oder das 2.x-Plugin, das du vielleicht schon hast</summary>

**Mit Gemini am Steuer.** Einen Plugin-Installer gibt es nicht, aber du kannst eine agentische
Gemini-Sitzung (Antigravity CLI oder ein beliebiges Gemini mit Datei- und Shell-Zugriff) auf das
Repository richten:

> Clone https://github.com/ayukhno/autosound-tuning-skill, read `skills/autosound-tuning/SKILL.md`,
> and follow that method as your operating instructions for this session.

**Schon das 2.x-Plugin installiert?** Dann bist du auf der 2.x-Linie, sie bleibt unterstützt, und
kein Update holt dich davon herunter: der Marketplace-Eintrag nennt einen exakten Commit statt eines
Branches. Deine bestehenden Projekte bleiben dort lesbar.

Die Zeile oben installiert 3.x, die ein Projekt als maschinenlesbare Dateien statt als Prosa
speichert, den Prozess mitschreibt — und die TCC liest. Ein Skill pro Maschine: zwei Plugins, die
einen Skill gleichen Namens mitbringen, bleiben beide aktiv, und welches antwortet, ist Glückssache.
Also zuerst das Plugin entfernen, in Claude Code:

```
/plugin uninstall autosound-tuning
```

```
/plugin marketplace remove autosound-tuning-skill
```

Deine 2.x-Projekte werden nicht konvertiert. 3.x importiert den **aktuellen** Stand des Autos in ein
**neues** Projekt und lässt das alte unberührt:

```sh
python3 ~/.claude/skills/.autosound-tuning-src/skills/autosound-tuning/rew_tool/state/migrate.py <old-project> --into <new-project>
```

Kanäle samt Ausgängen, Trennfrequenzen, Laufzeiten, Pegel, Polarität, EQ und das DSP-Profil ziehen
mit um. Journal und ältere Snapshots bleiben bewusst zurück: 2.x hat nie festgehalten, welche Fakten
wann galten — ihre Historie mitzunehmen hieße, sie zu erfinden.
</details>

## Wie eine Sitzung wirklich klingt

Drei Stimmen: **du** auf dem Hörplatz, **Claude** führt den Prozess, **Gemini** widerspricht bei
jedem Schritt.

> **Du (Schiedsrichter):** Der Kontrabass dröhnt etwas. Und als ich die Laufzeiten nach Gehör
> verschoben habe, wurde der Bass besser — tragen wir meine Werte ein?
>
> **Claude (Generator):** Erst gegen frische Messungen geprüft: deine Laufzeiten sind bereits
> optimal — deinem Ohr hat etwas anderes gefallen. Die wahren Übeltäter sind zwei schmale
> Türresonanzen und eine heiße linke Seite. Ich schlage drei chirurgische Absenkungen vor.
>
> **Gemini (Kritiker):** Einspruch: eine dieser Absenkungen liegt in einem Übergangsbereich — das
> kann die Summation dort zerstören.
>
> **Claude:** An den Messungen geprüft — dieser Übergang wird sogar *besser*. Aber dein Zweifel hat
> mich tiefer schauen lassen, und du liegst richtig: es ist nicht nur der Tiefmitteltöner, auch der
> Mitteltöner ist dort heiß. Neuer Plan: jedes Chassis bekommt seine eigene Absenkung.
>
> **Gemini:** Jetzt einverstanden.
>
> **Du:** Eingetragen. Das Dröhnen ist weg… aber der Subwoofer ortet jetzt hinter mir!
>
> **Claude:** Mein Fehler — zwei meiner Filter überlappen und senken tiefer ab als gewollt. Ich
> entschärfe einen.
>
> **Du:** Der Bass ist wieder vorn — sitzt aber tief. Ich will ihn oben an der Scheibe, wie vorher.
>
> **Claude:** Die alte Höhe kam von genau diesem Fehler. Den holen wir nicht zurück — stattdessen
> eine sanfte symmetrische EQ-Anhebung auf beiden Mitteltönern, damit die Höhe ohne Schieflage
> zurückkommt.
>
> **Du:** …Der Sub steht auf der Motorhaube! So bleibt es.

Etwa vierzig Minuten von „es dröhnt" bis „der Sub steht auf der Haube" — bei einem Problem, das sonst
Wochen an Forum-Trial-and-Error frisst. Jeder Beteiligte hat etwas gefangen, das die anderen
übersehen haben. Die vollständige technische Fassung, mit allen Zahlen, steht in der
[Fallstudie](community-inbox/case-studies/case-study-mode-a-bass-2026-07-15.md).

## Welche Modelle

**Generator: Claude Opus, Aufwand `xhigh`. Reviewer: Gemini Pro (High).** Das ist die eine
Kombination, mit der diese Methode durchgehend gefahren wurde. Alles andere ist ein Experiment, das
du fährst — und so sollte man es auch lesen.

Es zählt wegen der *Form* des Versagens. **Ein schwächeres Modell hält nicht mit einem Fehler an, es
stimmt dir zu.** Ein dokumentierter Lauf schloss die Phasen −1 bis 3 in einer Sitzung und meldete
Trennfrequenzen, Laufzeiten auf 0,1 ms genau, EQ „innerhalb ±0,5 dB" und ein Hörurteil — zu einem
Auto, in dem niemand gesessen hatte. Nichts in diesem Protokoll sah kaputt aus. Es war nur kein
Einmessen.

| Modus | Aufbau | Verlässlichkeit |
| :--- | :--- | :--- |
| **A: Claude + Gemini** | Claude führt, Gemini prüft | Am höchsten: zwei Perspektiven, langsamer pro Entscheidung |
| **B: Solo** | ein Modell führt und prüft sich selbst | Geringer: eine Perspektive, und die Zahlen will man von Hand nachrechnen |

Womit fahren, nach meiner bisherigen Erfahrung:

* **Opus**, die Voreinstellung fürs Einmessen. Hält eine lange Sitzung zusammen und entscheidet
  dort, wo ein schwächeres Modell stehen bleibt und fragt. `xhigh` ist die Untergrenze; in schweren
  Kurven auf Max.
* **Sonnet**, nicht für ein komplexes Tuning. Vorsichtig, und verliert den Faden, sobald Fakten über
  eine lange Sitzung zusammengeführt werden müssen. Gut für kurze, abgegrenzte Schritte.
* **Fable**, für die Recherche. Wo es darum geht, einen neuen Ansatz zu finden statt einen bekannten
  anzuwenden, kamen hier die besten Ideen von ihm.
* **Gemini**, als Kritiker, auf einer Pro-Stufe. Als Fahrer unter den aktuellen Regeln nicht
  verifiziert.

Modelle und Stufen verschieben sich von Monat zu Monat — nimm das als Startpunkt, nicht als Urteil,
und probiere selbst. Was sich nicht verschiebt, ist die Form des Versagens: was du auch wählst, ein
Modell, das weniger denken soll, sagt es dir nicht. Details zur Einrichtung, samt einem kostenlosen
Browser-Reviewer über Google AI Studio, stehen im [FAQ](FAQ.md).

## Die Mathematik darunter

Eine Bibliothek lokaler Skripte kaut die großen Datenmengen durch, damit die Modelle keine Token
darauf verwenden:

- **Eine Fehlerkarte von Innenraum und Einbau, erstellt vor jedem Tuning.** Türauslöschungen,
  Reflexionen und Links/Rechts-„Taschen", die kein Stereo-EQ füllt, werden in den ersten Sweeps
  gefunden — damit der EQ-Plan *um* den Innenraum herum arbeitet, statt gegen ihn.
- **Vier unabhängige Laufzeit-Lesungen müssen übereinstimmen**, bevor eine Laufzeit angefasst wird.
- **Kein Chassis muss gegen die Physik kämpfen.** Eine füllbare Senke und eine Interferenz-
  auslöschung sehen im Diagramm gleich aus; ein Phasentest trennt sie, und angehoben wird nur die
  füllbare.
- **Jedes vorgeschlagene Filter wird auf deinen eigenen gemessenen Kurven simuliert**, bevor du es
  eintippst, und unter kleinem Laufzeit- und Pegeldrift bewertet — damit es die reale Welt übersteht
  und nicht nur an einem Messerpunkt gewinnt.

## Was hier drin ist

```
autosound-tuning-skill/        ein Claude-Code-Plugin
└── skills/autosound-tuning/    der Skill
    ├── SKILL.md        Einstiegspunkt — Prozesskarte, Sitzungsablauf, Rollen
    ├── references/     Dokumente auf Abruf (Phasen, Diagnostik, EQ, Filter, Bühne,
    │                   Testtracks, REW-API, Helix, Review-Methode, Intake …)
    ├── knowledge/      gesammelte Auto- und DSP-Profile (cars/, dsp/)
    ├── rew_tool/       REW-API-Brücke, Analyse, Zielkurven, versionierter Zustand
    ├── scripts/        Wrapper für die Kritiker-/Berater-Kanäle (Gemini, Claude, Codex)
    └── curves.html     Zielkurven-Visualizer
```

▶ **[Zielkurven-Visualizer online öffnen](https://ayukhno.github.io/autosound-tuning-skill/_curve-visualizer.html?lang=de)** — zieh deine eigene Kurve hinein oder eine Standardkurve aus dem [Nono Tuning Tool](https://nonotuningtool.com), Rechtsklick auf einen Punkt zeigt den Frequenzcharakter, und Kurven lassen sich nebeneinander vergleichen. Eine einzige eigenständige Datei, funktioniert also offline; mit „Speichern unter" eine Kopie behalten.

Die Methode der unabhängigen Begutachtung (Kritiker/Berater/Schiedsrichter, Anti-Anchoring) ist in
`references/core/review-loop.md` beschrieben. Eine zustandslose Web-Chat-Fassung der Methode, ohne
lokale Installation, liegt im Branch
[manual_step-by-step](https://github.com/ayukhno/autosound-tuning-skill/tree/manual_step-by-step).

## Erfahrung beitragen

Der Skill lernt aus jedem Tuning: er sammelt Rückmeldung direkt im Terminal während der Arbeit, nicht
über ein Formular. Zum Abschluss, wenn du mit dem Klang zufrieden bist, fragt er, was geholfen hat,
was danebenlag und auf welche DSP- oder Auto-Eigenheit du gestoßen bist. Danach bietet er **nur mit
deiner ausdrücklichen Zustimmung** an, die *verallgemeinerbaren* Lehren zu teilen — damit die
gemeinsame Methode und die `knowledge/`-Bibliothek wachsen.

Erfasst werden **nur Methode und Geräteklassen**: Verhalten des Innenraums, Klasse der Technik,
welche Techniken funktioniert haben. **Nie persönliche Daten, nie vollständige Messungen.** Du siehst
genau, was geteilt wird, und stimmst pro Punkt zu. Bestätigte Lehren fließen mit Nennung in den Skill
ein.

## Unterstützen

Der Skill ist **kostenlos und offen** (CC BY-SA) und bleibt es. Nichts steht hinter einer Bezahlung.
Wenn er geholfen hat und du danke sagen möchtest, gibt es zwei freiwillige Wege:

💜 **[GitHub Sponsors](https://github.com/sponsors/ayukhno)** · ☕ **[Monobank-Sparglas](https://send.monobank.ua/jar/8wThVcodjm)** — ein Tipp, kein Konto nötig; nimmt Apple Pay, Google Pay, Visa, Mastercard.

## Lizenz

[CC BY-SA 4.0](LICENSE): nutzen, anpassen, weitergeben; Ableitungen offen halten und Urheber nennen.
Es ist eine Methoden- und Wissensarbeit, deshalb hält Share-alike die Erfahrung der Community offen.

Code und Skripte (`rew_tool/`, `scripts/` und weitere .py/.sh-Dateien) stehen unter der
[MIT-Lizenz](LICENSE-CODE). Materialien Dritter sind in [LICENSES/NOTICE.md](LICENSES/NOTICE.md)
aufgeführt.
