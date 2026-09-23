# FAQ — Häufig gestellte Fragen zur Car-Audio-Abstimmung

🇬🇧 [English](FAQ.md) · 🇩🇪 **Deutsch** · 🇵🇱 [Polski](FAQ.pl.md) · 🇺🇦 [Українська](FAQ.uk.md) · 📄 [README](README.de.md) · <img src="assets/icons/roadmap.svg" width="14" height="14" valign="middle" alt="Roadmap" /> [Roadmap (EN, Entwurf)](ROADMAP.md)

Echte Benutzerfragen zur Installation und Abstimmung deines Systems mit diesem Tool. [README](README.de.md) ist die Kurzversion; diese Seite enthält alle Details.

---

## Inhalt

- [Wahl des Weges](#wahl-des-weges)
  - [Vier Optionen zur Nutzung](#vier-optionen-zur-nutzung)
  - [Welche Option soll ich wählen?](#welche-option-soll-ich-wählen)
  - [Wie ermittle ich die bereits installierte Version?](#wie-ermittle-ich-die-bereits-installierte-version)
  - [Wie bleibe ich auf der stabilen 2.x-Linie?](#wie-bleibe-ich-auf-der-stabilen-2x-linie)
  - [Wechsel von 2.x auf 3.x](#wechsel-von-2x-auf-3x)
  - [Hauptänderungen in 3.x](#hauptänderungen-in-3x)
- [Philosophie und Architektur: Wozu KI?](#philosophie-und-architektur-wozu-ki)
  - [Mission und Konzept](#mission-und-konzept)
  - [Warum ist dies ein spezialisierter Skill und kein normaler Chat?](#warum-ist-dies-ein-spezialisierter-skill-und-kein-normaler-chat)
  - [Ablaufplan: Phasen −1…5 und der „Schreibtisch zuerst“-Ansatz](#ablaufplan-phasen-15-und-der-schreibtisch-zuerst-ansatz)
  - [Was lehnt die Methode kategorisch ab?](#was-lehnt-die-methode-kategorisch-ab)
  - [Welche KI-Modelle werden offiziell unterstützt?](#welche-ki-modelle-werden-offiziell-unterstützt)
  - [Abonnement-Optionen und KI-Budget](#abonnement-optionen-und-ki-budget)
  - [Warum sind die tatsächlichen Token-Kosten niedriger als gedacht?](#warum-sind-die-tatsächlichen-token-kosten-niedriger-als-gedacht)
- [Erstinstallation (macOS und Windows)](#erstinstallation-macos-und-windows)
  - [Automatische Installation](#automatische-installation)
  - [Wohin werden die Komponenten installiert?](#wohin-werden-die-komponenten-installiert)
  - [Erststart und Account-Anmeldung](#erststart-und-account-anmeldung)
  - [Aktualisierung, Version fixieren und Deinstallation](#aktualisierung-version-fixieren-und-deinstallation)
- [Grafische Desktop-App Autosound TCC](#grafische-desktop-app-autosound-tcc)
  - [Was ist das und brauche ich es?](#was-ist-das-und-brauche-ich-es)
  - [Arbeiten auf zwei Fenstern (Terminal + Grafik)](#arbeiten-auf-zwei-fenstern-terminal--grafik)
  - [KI-Modelle in der App](#ki-modelle-in-der-app)
  - [Updates und Fehlermeldungen](#updates-und-fehlermeldungen)
- [Eigenständiger KI-Reviewer Gemini/Antigravity](#eigenständiger-ki-reviewer-geminiantigravity)
  - [Installation für macOS und Windows (Empfohlen)](#installation-für-macos-und-windows-empfohlen)
  - [Fallback-Option: Direkter Gemini API-Key](#fallback-option-direkter-gemini-api-key)
  - [Kann ich die Methode komplett in Gemini ausführen?](#kann-ich-die-methode-komplett-in-gemini-ausführen)
- [Messungen durchführen](#messungen-durchführen)
  - [Phasenmessung: XLR-Mikrofone vs. USB (UMIK-1/2)](#phasenmessung-xlr-mikrofone-vs-usb-umik-12)
  - [Kann ich die Phase mit einem UMIK-1 messen?](#kann-ich-die-phase-mit-einem-umik-1-messen)
  - [Regeln für die Benennung von Messungen in REW](#regeln-für-die-benennung-von-messungen-in-rew)
  - [Einmessung (Capture-Session): Warum nur Schutzfilter?](#einmessung-capture-session-warum-nur-schutzfilter)
  - [Wozu dienen die Positionen p1…p9 und die Zeitkontrolle ctl?](#wozu-dienen-die-positionen-p1p9-und-die-zeitkontrolle-ctl)
- [Zielkurven (Target Curves)](#zielkurven-target-curves)
  - [Wie erstelle und konfiguriere ich meine eigene Zielkurve?](#wie-erstelle-und-konfiguriere-ich-meine-eigene-zielkurve)
- [Projekt auf der Festplatte und DSP](#projekt-auf-der-festplatte-und-dsp)
  - [Struktur des Projektordners und Datensicherung](#struktur-des-projektordners-und-datensicherung)
  - [Kompatibilität mit Prozessoren und Filter-Import in den DSP](#kompatibilität-mit-prozessoren-und-filter-import-in-den-dsp)
  - [Arbeiten mit passiven Frequenzweichen (Hochtöner + MT auf einem Kanal)](#arbeiten-mit-passiven-frequenzweichen-hochtöner--mt-auf-einem-kanal)
  - [Wo finde ich die vollständige Liste der Funktionen der Methode?](#wo-finde-ich-die-vollständige-liste-der-funktionen-der-methode)

---

## Wahl des Weges

### Vier Optionen zur Nutzung

* 🖥️ **Option 1 · Version 3.x im grafischen Fenster (Autosound TCC) — [Empfohlen]**  
  Der am stärksten automatisierte und visuellste Weg. Der Installer richtet Claude Code, Python, den Kern der Methode, die grafische Benutzeroberfläche und den automatischen KI-Reviewer ein.
  * **Voraussetzungen:** macOS oder Windows, kostenpflichtiges Claude Pro/Max, REW-Beta mit aktiviertem API; die App vergrößert den Download um etwa 700 MB.
  * **Vorteile:** Du siehst den Systembaum, die Messkurven, den Schritt-für-Schritt-Plan und das Chat-Fenster in einer einzigen Benutzeroberfläche. Der Zustand wird automatisch auf der Festplatte gespeichert und Aktionen im Versionsregister werden nachverfolgt.
  * **Nachteile:** Die grafische App ist jünger als die zugrundeliegende Abstimmungsmethode und befindet sich derzeit im Beta-Status.

* 💻 **Option 2 · Version 3.x im Terminal (Claude Code oder Headless-Plugin)**  
  Exakt derselbe moderne Kern, dieselben Berechnungstools und derselbe Automatisierungsgrad, aber die Interaktion erfolgt textbasiert in der Konsole. Installiert mit dem Flag `--terminal` (oder über das Claude Code-Plugin).
  * **Voraussetzungen:** Die gleichen Abonnements und REW-Beta mit aktiviertem API, jedoch ohne die grafische Benutzeroberfläche.
  * **Vorteile:** Maximale Ausführungsgeschwindigkeit, kein GUI-Overhead, ideal für Konsolen-Liebhaber. Projekte sind zu 100 % kompatibel mit der grafischen TCC-App.

* 🏆 **Option 3 · Die 2.x-Linie (Der bewährte Champion)**  
  Das klassische Plugin für Claude Code, fest fixiert auf Version `v2.8.3` (Zweig `2.x`). Mit diesem Algorithmus abgestimmt, holte das Auto des Autors 2026 Auszeichnungen bei EMMA- und AYA-Meisterschaften.
  * **Voraussetzungen:** Kostenpflichtiges Claude Pro, REW-Beta mit aktiviertem API, Arbeit im Terminal.
  * **Vorteile:** Ein fester, wettbewerbserprobter Algorithmus. Erhält nur noch kritische Fehlerbehebungen, ohne neue Funktionen.
  * **Nachteile:** Manuelle Zustandsüberwachung in Text-Markdown-Dateien (`dsp-state-current.md`), keine automatisierte virtuelle „Schreibtisch zuerst“-Prognose und keine modernen Berechnungstools.

* 🌐 **Option 4 · Web-Chat (Ohne Programminstallation)**  
  Ein vollständig manueller Schritt-für-Schritt-Abstimmungsablauf über den [manual_step-by-step-Zweig](https://github.com/ayukhno/autosound-tuning-skill/tree/manual_step-by-step).
  * **Voraussetzungen:** Kostenloses Google AI Studio oder ein beliebiger Web-Chat mit einer KI deiner Wahl.
  * **Vorteile:** Vollständig kostenlos. Erfordert keinerlei Installation von Software oder Entwicklerwerkzeugen auf deinem Computer.
  * **Nachteile:** Jeder Schritt wird manuell ausgeführt (Kopieren von Prompts, eigenständiger Export von Textdateien aus REW), keine API-Integration und keine Überprüfung der Berechnungen durch lokale Skripte.

---

### Welche Option soll ich wählen?

* **Du möchtest maximale Automatisierung und visuelles Feedback:** Wähle **Option 1 (TCC)**.
* **Du bevorzugst die Konsole und maximale Geschwindigkeit:** Wähle **Option 2 (3.x Terminal)**.
* **Du möchtest das bewährte, wettbewerbserprobte Legacy-Plugin:** Wähle **Option 3 (2.8.3)**.
* **Du möchtest die Logik kostenlos ohne lokale Software testen:** Wähle **Option 4 (Web-Chat)**.

> [!NOTE]
> Du bist nicht auf eine einzige Wahl festgelegt: Projekte der 3.x-Linie lassen sich nahtlos sowohl in der Konsole als auch im grafischen TCC-Programm öffnen.

---

### Wie ermittle ich die bereits installierte Version?

* **Anhand des verwendeten Befehls:** Wenn du das Plugin mit dem Befehl `/plugin install autosound-tuning` in Claude Code installiert hast, nutzt du die Version **2.x**. Wenn du das Ein-Zeilen-Installationsskript (`curl … | bash` oder `irm … | iex`) ausgeführt hast, nutzt du die Version **3.x**.
* **Am Inhalt des Projektordners:** Wenn der Ordner eine Datei namens `dsp-state-current.md` enthält, handelt es sich um ein **2.x**-Projekt. Wenn der Ordner die maschinenlesbaren Dateien `project.json` und `process-state.json` enthält, ist es ein **3.x**-Projekt.
* **Über die Programmoberfläche:** Gehe in der TCC-App auf *Diagnostics → Installation*.

---

### Wie bleibe ich auf der stabilen 2.x-Linie?

Das standardmäßige automatische Plugin-Update stellt dich nicht ohne deine Zustimmung auf Version 3.x um. Wenn du die Version jedoch vollständig einfrieren und Updates auf dem 2.x-Zweig lokal kontrollieren möchtest, klone das Repository selbst:

```bash
git clone -b 2.x https://github.com/ayukhno/autosound-tuning-skill.git ~/autosound-2x
```

Führe dann diese zwei Befehle in einem Terminal aus:
```bash
claude plugin marketplace add ~/autosound-2x
claude plugin install autosound-tuning
```
Nun zeigt dein Plugin auf deinen lokalen Ordner. Du kannst es bei Bedarf jederzeit mit einem einfachen `git -C ~/autosound-2x pull` aktualisieren.

---

### Wechsel von 2.x auf 3.x

Es kann immer nur ein solches Plugin gleichzeitig im System aktiv sein. Bevor du Version 3.x installierst, stelle sicher, dass du die alte 2.x-Version deinstallierst (in einem Terminal):

```
claude plugin uninstall autosound-tuning
claude plugin marketplace remove autosound-tuning-skill
```

Nach der Installation von Version 3.x kannst du ein bestehendes Fahrzeugprojekt mit dem automatischen Migrator in das neue Maschinenformat überführen:

```sh
python3 ~/.claude/skills/.autosound-tuning-src/skills/autosound-tuning/rew_tool/state/migrate.py <path-to-old-project> --into <path-to-new-project>
```
*(Hinweis: Überprüfe nach der Migration das Kanal-Mapping und die Lautsprecher-Spezifikationen).*

---

### Hauptänderungen in 3.x

* 📦 **Projekt als Datenstruktur:** Alle Systemparameter werden auf der Festplatte in `project.json` und `process/process-state.json` gespeichert. Die KI liest Maschinenfakten von der Festplatte, anstatt sich auf das Chat-Gedächtnis zu verlassen.
* 🛋️ **Der „Schreibtisch zuerst“-Ansatz:** Statt vieler Fahrten zum Auto — **eine disziplinierte Sitzung für die akustische Einmessung** (Phase 0) und **ein kurzer Besuch zur Verifizierung** (Phase 3). Die gesamte Analyse, Frequenzweichen-Berechnung, Phasenabstimmung und das EQ-Design werden am Schreibtisch durchgeführt.
* 🧮 **Mathematische Verifizierung:** Spezielle lokale Python-Skripte analysieren Kurven auf minimalen Phasenverlust, bewerten den Start des Impulseintreffens und prüfen die Zeitstabilität des Mikrofons.
* 🛑 **Strukturierte Schleusen:** Wenn Eingangsmessungen übermäßige Zeitdrift, fehlende Kanäle oder verletzte Sicherheitsgrenzen aufweisen, stoppt das System und benennt das Problem, bevor es fortfährt.

---

## Philosophie und Architektur: Wozu KI?

### Mission und Konzept

Wir erschaffen ein **intellektuelles Exoskelett** für die Klangabstimmung. Der Mensch (Arbiter) bleibt immer das entscheidende Glied — er hört das System, beurteilt Tiefe, Höhe und Stabilität der Bühne und trifft die endgültigen Entscheidungen.

Die KI übernimmt routinemäßige Berechnungen und die Akustik des Innenraums: Sie analysiert Impulseintreffen, Phasenkurven, berechnet Laufzeiten an Frequenzweichen-Übergängen und interagiert über die API mit REW, wodurch dir Zeit für den kreativen Teil des Musikhörens frei wird.

---

### Warum ist dies ein spezialisierter Skill und kein normaler Chat?

* **Zustand auf Festplatte gespeichert:** Ein standardmäßiger KI-Chat vergisst im Laufe einer langen Sitzung Ausgangswerte, verwechselt Pegel oder verändert Trennfrequenzen. Unser System schreibt den Projektzustand auf die Festplatte. Die KI liest diese Datei bei jedem Schritt — ihr Kontext stützt sich auf den Zustand auf der Festplatte, nicht auf den Chat-Pufferspeicher.
* **Spezialisiertes akustisches Fachwissen:** Der Skill enthält feste Sicherheitsregeln zum Schutz der Lautsprecher, Phasenabstimmungs-Logik, vorkonfigurierte Zielkurven und Heuristiken zur Innenraumakustik, über die allgemeine KI-Modelle nicht verfügen.
* **Lokale Verarbeitung über REW-API:** Rohdaten der Messungen (Tausende Punkte pro Kurve) werden von lokalen Python-Skripten in Millisekunden verarbeitet. Die KI erhält im Chat nur prägnante mathematische Zusammenfassungen, was Zeit und Token-Budget spart.

---

### Ablaufplan: Phasen −1…5 und der „Schreibtisch zuerst“-Ansatz

| Phase | Wo stattfindend | Was wird getan | Ergebnis der Phase |
| :--- | :--- | :--- | :--- |
| **−1 Vorbereitung** | am Schreibtisch | Eingabe des Basis-Setups (Lautsprecherkanäle, DSP-Ausgänge, DSP-Profil, Mikrofon, Referenzsitz). Etwa 17 Antworten vorab; der Rest wird von der Phase erfragt, die ihn benötigt. | `project.json` und Konfigurationsdateien erstellt. |
| **0 Einmessung (Capture)** | im Auto (1 Mal) | Messung jedes Lautsprechers mit **aktivierten Schutzfiltern** (Sweeps auf Stativ `(sw)` und Moving-Mic `(rta)`). Festlegung der Zielkurve nach der Einmessung. | Verifizierte Basis-Messrunde und aktive Zielkurve. |
| **1 Fundament** | am Schreibtisch | Du beschreibst deine Trennfrequenz-Wünsche in eigenen Worten, und sie werden gegen die harten Grenzen geprüft. Die KI bietet höchstens drei Frequenzweichen-Varianten an — die beste, welche die Mathematik findet, und jene aus deinen Wünschen, jede mit ihrem Preis — und du wählst aus. Treiber-Resonanzen und ein grober EQ pro Treiber werden hier behandelt; Pegel, Polaritäten und Laufzeiten werden von Hand am Start jedes Impulses abgelesen; die Summen werden prognostiziert und beschrieben. | Basis-Abstimmung des Systems im Versionsregister. |
| **2 Equalizer** | am Schreibtisch | Der zweite Teil des EQ, in **Paketen** und in dieser Reihenfolge: Links/Rechts-Paare pro Band → die Übergänge jeder Seite → Sub mit Mitteltönern → jede Seite komplett → alles zusammen → Center → Rear. Standard ist **nur Absenkungen** (cuts only), max. 6 Bänder pro Kanal. Jedes Paket ist eine einzelne „Ja/Nein“-Entscheidung und eine neue Registerversion. | Fertige EQ-Konfiguration zum Importieren in den DSP. |
| **3 Urteil (Verdict)** | im Auto (kurz) | Übertragen der Parameter in den DSP. Der Verifizierungs-Sweep prüft automatisch, ob reale Messungen mit mathematischen Prognosen übereinstimmen. Verbindliche Hörbewertung. | Eine vollständig verifizierte, fixierte technische Abstimmung. |
| **4 Hören** | im Auto | Test-Tracks (EMMA/AYA-Discs, CarMus, Chesky) und ein Spickzettel „Worauf zu achten ist“. Wenn etwas dröhnt oder scharf klingt, listet der Skill verdächtige Bänder auf und testet sie einzeln im A/B-Vergleich (drei Verdächtige × drei Runden, dann Stopp). | Mit Versionen verknüpfte Hör-Urteile. |
| **5 Variationen** | Schreibtisch / im Auto | Einrichten zusätzlicher Presets (verschiedene Musikgenres, alternative Klangcharakteristik) auf der technischen Basis. | Zusätzliche Klang-Presets im DSP. |

---

### Was lehnt die Methode kategorisch ab?

* **Direktes Schreiben von Parametern in deinen DSP** — das Eingeben der Werte in die Prozessor-Software bleibt immer deine Aufgabe.
* **Berechnung von Laufzeiten mittels Auto-Delay-Tools oder Kreuzkorrelation** — akustische Laufzeiten werden manuell anhand des ersten Anstiegs der Impulsantwort ($t_0$) geprüft. Auto-Delay-Schätzungstools in REW sind strikt verboten.
* **Anheben von Frequenzen in akustischen Nullen (Auslöschungszonen)** — Auslöschungseinbrüche entstehen durch Grenzflächenreflexionen, nicht durch den Lautsprecher selbst. Sie per EQ aufzufüllen ist zwecklos: Eine Anhebung belastet nur Verstärker und Lautsprecher und ändert an der Hörposition nichts. Die Methode begrenzt jeden Boost auf maximal +6 dB, und ein Einbruch, der mehr erfordern würde, ist fast sicher eine Auslöschung. Einbrüche, die sicher korrigiert werden können, werden über die *Excess phase*-Analyse in REW ermittelt.
* **Fortfahren mit fehlerhaften Messungen** — eine erkannte Zeitdrift zwischen Kontroll-Sweeps der Sitzung oder fehlende Schutzfilter werden beanstandet, bevor fortgefahren wird.

---

### Welche KI-Modelle werden offiziell unterstützt?

* 🧠 **Hauptmodell (Generator):** **Claude Opus** (konfiguriert mit der Denkstufe `xhigh`; `max` für komplexe Phasenabstimmung).
* 👁️ **KI-Reviewer (Critic):** **Gemini Pro (High)** über Google Antigravity (`agy`) oder direkten API-Key.
* 🛠️ **Weitere Reviewer:** Die Auswahl in TCC bietet auch Codex (und mit `--with-omp` weitere Modelle) für die Rolle des Reviewers an. Der Generator bleibt Claude.

*Stand September 2026.* Modellnamen ändern sich schnell. Wird eines der hier genannten abgelehnt (wenn `agy` etwa antwortet, dass das Modell an deinem Standort nicht unterstützt wird), wähle ein anderes aus `agy models`.

> [!IMPORTANT]
> **Senke Claudes Denkstufe nicht unter `xhigh`.**  
> Schwächere Modelle oder niedrigere Denkstufen melden keine Fehler — sie stimmen fehlerhaften Eingaben stillschweigend zu, halluzinieren unmögliche akustische Parameter oder übersehen Phasenauslöschungen.

---

### Abonnement-Optionen und KI-Budget

* **Option 1 (Empfohlen): Claude Pro ($20/Monat) oder Max + kostenloses Gemini über Antigravity (`agy`)**  
  Die beste Balance aus Zuverlässigkeit und Kosten. Der Reviewer läuft über Googles `agy`-CLI, angemeldet mit deinem Google-Konto. Ein Pauschal-Abonnement deckt deine Sitzungen ohne streckenbasierte Token-Abrechnung ab und kann gekündigt werden, sobald du dein Auto fertig abgestimmt hast.
* **Option 2 (Pay-as-you-go-API):**  
  Den gesamten Abstimmungszyklus rein über nutzungsbasierte API-Tokens laufen zu lassen, summiert sich schnell. Eigene Messung des Autors: Allein die Phasen 0–2 über die Pay-as-you-go-Gemini-API kosteten etwa 20 $ — noch vor jeglichen Hörrunden. Ein festes Monatsabonnement ist spürbar wirtschaftlicher.
* **Option 3 (Direkter Gemini API-Key):**  
  Sind die Kontingente der Antigravity-CLI erschöpft, kann ein kostenloser oder bezahlter API-Key aus dem Google AI Studio als Fallback genutzt werden. Der Schlüssel wandert in den Schlüsselspeicher des Betriebssystems (siehe [Fallback-Option](#fallback-option-direkter-gemini-api-key)).

---

### Warum sind die tatsächlichen Token-Kosten niedriger als gedacht?

1. Lokale Python-Skripte komprimieren Tausende von REW-Messpunkten in prägnante mathematische Zusammenfassungen. Rohgraphen werden niemals in den Chat gekippt.
2. Der Projektzustand liegt auf der Festplatte, sodass die KI nicht bei jeder Anfrage den gesamten Gesprächsverlauf neu liest.
3. Es wird das Prinzip des gleitenden Fensters angewendet — es werden nur Daten geladen, die die gerade aktive Phase betreffen.

---

## Erstinstallation (macOS und Windows)

### Automatische Installation

Du benötigst einen Laptop, ein Messmikrofon, einen DSP-Prozessor im Auto und ein kostenpflichtiges **Claude Pro oder Max**-Abonnement.

<details>
<summary><b>Anleitung für macOS</b></summary>

1. Öffne das **Terminal** (drücke `Cmd + Leertaste` → tippe `Terminal` ein → drücke `Enter`).
2. Füge folgenden Befehl ein und drücke `Enter`:
   ```bash
   curl -fsSL https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/v3.0.61/install.sh | bash
   ```
3. Falls Apples Command Line Tools fehlen, öffnet sich einmalig das offizielle Installationsfenster von Apple — klicke auf Installieren. Das Skript selbst fragt niemals nach deinem Passwort. Warte 10–20 Minuten.

</details>

<details>
<summary><b>Anleitung für Windows</b></summary>

1. Öffne die **Windows PowerShell** (drücke Start → tippe `powershell` ein → drücke `Enter`).
2. Füge folgenden Befehl ein und drücke `Enter`:
   ```powershell
   irm https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/v3.0.61/install.ps1 | iex
   ```
3. Falls Git fehlt, erlaube dessen Installation. Das Skript erstellt außerdem eine Verknüpfung für **REW (API on)** auf deinem Desktop.

</details>

---

### Wohin werden die Komponenten installiert?

Alle Dateien werden innerhalb deines Benutzerprofils gespeichert:

| Komponente | Installationspfad | Zweck |
| :--- | :--- | :--- |
| **Claude Code** | Offizielles Anthropic-Verzeichnis | Der Haupt-KI-Assistent, der durch den Prozess leitet |
| **Abstimmungsmethode** | `~/.claude/skills/.autosound-tuning-src`, verlinkt als `~/.claude/skills/autosound-tuning` | Der Checkout der Methode und der Name, unter dem Claude Code sie findet |
| **Python 3.12** | `~/.local/bin/python3` (über `uv`) | Führt die lokalen Tools der Methode aus |
| **Autosound TCC** | Benutzerordner & Desktop-Verknüpfung | Die grafische App und eine isolierte Python 3.12-Umgebung |
| **`agy`-Tool** | Benutzerprofil | Google-CLI-Tool für die schnelle Kommunikation mit dem Gemini-Critic |
| **Reviewer-Konfiguration** | `~/.config/autosound/critic-env` (`%APPDATA%\autosound\critic-env` unter Windows) | Modell des Reviewers und optionaler API-Key — außerhalb jedes Projekts |
| **`gh`, `omp`** | Benutzerprofil — nur auf Anfrage (`--github`, `--with-omp`) | GitHub-Backup-Helfer; alternative Modelle |

---

### Erststart und Account-Anmeldung

1. **Anmeldungen am Ende der Installation:** Der Installer meldet dich bei Claude an (im Browser mit deinem Account einloggen und autorisieren), bietet die Gemini-Anmeldung über `agy` an (Enter meldet an, `s` überspringt) sowie GitHub, falls `gh` installiert ist.
2. **REW-API aktivieren:**  
   *Hinweis: REW muss die Beta-Version sein (das aktuelle Release V5.31.3 und frühere haben keine API).*  
   Gehe auf *Preferences → API*, setze das Häkchen bei **Start the API when REW starts** und klicke auf **Start server** (Port `4735`). Starte REW unter Windows über die Verknüpfung **REW (API on)**.
3. **Arbeitsbeginn:** Erstelle einen leeren Ordner für dein Auto (z. B. `MeinAutoTuning`). Öffne ihn in **Autosound TCC** (wähle Claude Opus und Gemini Pro) oder in einem Terminal (`cd MeinAutoTuning`, dann `claude`) und schreibe in den Chat: **„Abstimmung für ein neues Auto von Grund auf starten“** (oder auf Englisch: *"tune a new car from scratch"*).

---

### Aktualisierung, Version fixieren und Deinstallation

* **Skill aktualisieren:** Du kannst den Skill direkt in TCC aktualisieren oder den Installationsbefehl einfach erneut im Terminal ausführen. Das Skript lädt das neueste `v3.*`-Tag herunter (die `v3.0.*`-Tags sind Vorab-Releases bis 3.1.0; die wettbewerbserprobte stabile Linie ist 2.8.x) und rührt deine Projektdateien nicht an.
* **TCC aktualisieren:** Die Update-Schaltfläche in TCC liefert den Update-Befehl zur Ausführung im Terminal (eine laufende Anwendung kann ihre eigene ausführbare Datei nicht überschreiben).
* **Optionen:** Sie stehen unter macOS hinter `bash -s --` und unter Windows hinter der Form `& ([scriptblock]::Create((irm …)))` (beide dargestellt in der [README](README.de.md#installation-und-start-version-3x--beta)): `--terminal` / `-Terminal` (keine App), `--github` / `-GitHub`, `--with-omp` / `-WithOmp`, `--no-reviewer` / `-NoReviewer`, `--dry-run` / `-DryRun`.
* **Version fixieren:** `--skill-ref` und `--tcc-ref` (`-SkillRef` und `-TccRef` unter Windows) pinnen die Methode und die App auf die gemeinsam veröffentlichten Versionen — gib die beiden als **Paar** an oder gar nicht; ein gemischtes Paar ist ungetestet.
* **Deinstallation:** Führe den Installer mit `--uninstall` (`-Uninstall`) aus; `--all` entfernt zusätzlich uv, Claude Code und `~/.claude` sowie `agy`/`gh`/`omp`, falls der Installer sie dort abgelegt hat — er fragt vorher nach. Deine Projektordner werden niemals gelöscht.

---

## Grafische Desktop-App Autosound TCC

### Was ist das und brauche ich es?

Die App [TCC](https://github.com/ayukhno/autosound-tcc) ermöglicht es dir, in einem grafischen Fenster unter macOS und Windows zu arbeiten. Du siehst den Systembaum, REW-Graphen, den Schritt-für-Schritt-Plan und den KI-Chat auf einem einzigen Bildschirm. Die App ist optional — du kannst ein Auto komplett über das Terminal abstimmen, da alle Projektdaten in standardmäßigen Maschinendateien auf der Festplatte gespeichert werden.

📘 [TCC in eight screens (EN)](https://github.com/ayukhno/autosound-tcc/blob/main/docs/guide/QUICK-GUIDE.md) · [The TCC window, panel by panel (EN)](https://github.com/ayukhno/autosound-tcc/blob/main/docs/guide/REFERENCE.md) · [The house curve in TCC (EN)](https://github.com/ayukhno/autosound-tcc/blob/main/docs/guide/HOUSE-CURVE.md)

### Arbeiten auf zwei Fenstern (Terminal + Grafik)

Die App und das Terminal greifen auf exakt dieselben Projektdateien zu. Du kannst deine interaktive Sitzung im Terminal ausführen und TCC parallel als visuellen Echtzeit-Monitor geöffnet lassen: Es zeigt den Lautsprecherbaum, Kurvenüberlagerungen und Änderungen im Versionsregister live an, während sie geschehen.

### KI-Modelle in der App

Die App nutzt dein Claude-Abonnement (über das Anthropic-SDK) und dein Google-Konto über `agy` für den KI-Reviewer. Die Modellauswahl in TCC spiegelt die empfohlenen Kombinationen wider. Alternative Modelle über `omp` werden nur hinzugefügt, wenn dies angefordert wurde (`--with-omp`).

### Updates und Fehlermeldungen

TCC prüft auf Updates für Skill und App. Melde UI-Fehler im [GitHub-Repository von TCC](https://github.com/ayukhno/autosound-tcc/issues) und mathematische Abstimmungsprobleme im [Repository des Skills](https://github.com/ayukhno/autosound-tuning-skill/issues).

---

## Eigenständiger KI-Reviewer Gemini/Antigravity

Der Review-Zyklus aus zwei KIs (Generator ↔ Gemini Critic) fängt Fehler ab, die ein einzelnes Modell macht und selbst nicht sieht. Er läuft vollautomatisch im Hintergrund über ein lokales Skript — manuelles Kopieren ist nicht nötig. Was optional ist, ist dieser *automatische Kanal*, nicht die Zweitmeinung selbst: Ist kein Kanal eingerichtet, fügst du das Paket von Hand in den Chat einer anderen KI ein. Den Review komplett zu überspringen, ist der größte Qualitätsverlust in der Methode.

### Installation für macOS und Windows (Empfohlen)

Die offizielle **Antigravity CLI (`agy`)** benötigt keinen API-Key — du authentifizierst dich im Browser mit deinem Google-Konto.

1. **Installation:** Der Installer richtet dies automatisch ein. Für eine manuelle Installation führe aus:
   * *macOS:* `curl -fsSL https://antigravity.google/cli/install.sh | bash`
   * *Windows:* `irm https://antigravity.google/cli/install.ps1 | iex`
2. **Anmeldung:** Führe `agy` in einem neuen Terminal aus, melde dich im Browser mit deinem Google-Konto an, kehre dann zur Konsole zurück und tippe `/quit`.
3. **Wähle das Modell des Reviewers** — es gibt keinen Standardwert. Trage eine ID aus `agy models` (die linke Spalte; eine Pro-`-high`-Stufe) in die Konfigurationsdatei des Reviewers ein, `~/.config/autosound/critic-env` (`%APPDATA%\autosound\critic-env` unter Windows), als Zeile wie etwa:
   ```env
   AUTOSOUND_CRITIC_MODEL=gemini-3.1-pro-high
   ```
   Die App setzt dies über ihre eigene Auswahlliste. Wenn `agy` antwortet, dass das Modell an deinem Standort nicht unterstützt wird, wähle eine andere ID aus der Liste.
4. **Prüfung:**
   ```bash
   python3 ~/.claude/skills/autosound-tuning/scripts/autosound_ai.py doctor
   ```
   `doctor` benennt das Modell, die CLI und den Schlüssel, die es gefunden hat, führt einen kurzen Live-Aufruf durch und gibt für jedes Problem den passenden Fix aus.

---

### Fallback-Option: Direkter Gemini API-Key

Wenn dir `agy` nicht zur Verfügung steht oder du dessen Kontingente erschöpfst, kannst du einen kostenlosen Gemini-API-Key direkt verwenden. Ist ein Schlüssel vorhanden, ruft der Reviewer **zuerst** die API auf und `agy` nur dann, wenn dieser Aufruf fehlschlägt.

1. Hole dir einen kostenlosen API-Key auf **[aistudio.google.com/apikey](https://aistudio.google.com/apikey)** — aktuelle Schlüssel beginnen mit `AQ.`.
2. Speichere ihn einmalig mit dem eigenen Befehl des Reviewers. Er fragt den Schlüssel ab, ohne ihn anzuzeigen, und verwahrt ihn im macOS-Schlüsselbund (unter Windows in einem Speicher, den nur deine Anmeldung öffnet; andernorts und wann immer der Speicher nicht verfügbar ist, in der Konfigurationsdatei des Reviewers mit Rechten 600). Eine Schlüsselzeile, die du von Hand in `critic-env` einträgst, hat Vorrang vor dem Speicher. Niemals in einem Projektordner, einem Shell-Profil oder einer Umgebungsvariable: Jedes Programm kann ihn dort lesen, und eine aus dem Dock gestartete App sieht ihn nicht.
   ```bash
   python3 ~/.claude/skills/autosound-tuning/scripts/autosound_ai.py key set google
   # Windows: python3 "$HOME\.claude\skills\autosound-tuning\scripts\autosound_ai.py" key set google
   ```
   Ein bereits in `~/.zshrc` (oder in den Windows-Benutzervariablen) exportierter Schlüssel wird mit `… key move-shell` übertragen, das vorher nachfragt. `… key status` zeigt, wo jeder Schlüssel liegt, niemals den Schlüssel selbst.
3. Benenne ein Modell, das der Schlüssel aufrufen kann: `doctor` gibt die eigene Liste des Schlüssels aus (zum Beispiel `gemini-pro-latest`). Dessen IDs unterscheiden sich von denen von `agy`.

Ein projektlokales `.critic-env`, das einen Schlüssel enthält und das Git erfassen würde, wird abgewiesen. `doctor` gibt niemals den Schlüssel aus, nur dessen Form (`current` / `OLD`) und woher er stammt.

> [!TIP]
> Wenn kein Kanal antwortet, verweigert der Reviewer die Ausführung (Exit-Code 4): Er listet auf warum, speichert das Paket im Projektordner unter `process/reviews/` und kopiert es in die Zwischenablage — füge es in den Chat einer beliebigen KI ein.

---

### Kann ich die Methode komplett in Gemini ausführen?

Ja, aber als manueller Durchlauf und nicht als automatisierte Pipeline. Gib deiner Gemini-Sitzung folgenden Prompt:

> Clone `https://github.com/ayukhno/autosound-tuning-skill`, read `skills/autosound-tuning/SKILL.md`, and follow that method as your operating instructions for this session.

Da es im standardmäßigen Web-Chat keinen Mechanismus für ein gleitendes Fenster gibt, kann die Präzision bei langen Sitzungen nachlassen. Die unterstützte kostenlose Option ist **Option 4** ([manual_step-by-step-Zweig](https://github.com/ayukhno/autosound-tuning-skill/tree/manual_step-by-step)).

---

## Messungen durchführen

### Phasenmessung: XLR-Mikrofone vs. USB (UMIK-1/2)

* **XLR-Mikrofone (Behringer ECM8000, Beyerdynamic MM1 etc.):** Werden über ein externes Audio-Interface mit einem **Hardware-Loopback-Kabel** angeschlossen (ein Ausgang wird direkt in einen freien Eingang zurückgeführt). Dies liefert eine hardware-stabile, sample-genaue Ankunftszeit-Referenz (ein Sample ≈ 10 µs bei 96 kHz).
* **USB-Mikrofone (UMIK-1 / UMIK-2):** Werden direkt über USB angeschlossen. Sie verfügen über eigene digitale Taktgeber getrennt vom Audio-Interface und haben kein physikalisches Loopback, weshalb sie eine akustische Zeitreferenz benötigen.
* **Audio-Verbindung:** Verwende ein physisches Kabel (AUX 3,5 mm, direktes USB-Audio oder optisch). **Vermeide Bluetooth für Sweeps:** Drahtlose Verbindungen verursachen Paket-Jitter und variable Latenzen, welche die Genauigkeit der akustischen Zeitreferenz beeinträchtigen.

---

### Kann ich die Phase mit einem UMIK-1 messen?

**Ja.** Nutze dazu die **akustische Zeitreferenz (Acoustic Timing Reference)** in REW. Vor dem Abspielen des Mess-Sweeps gibt REW ein kurzes, hochfrequentes Signal (einen „Chirp“) über den Ausgang ab, den du als Zeitreferenz wählst, und dieser Chirp ist der Nullpunkt für den gemessenen Kanal.

Eine detaillierte REW-Konfiguration für USB-Mikrofone findest du in der Videoanleitung: [Measuring Speaker Phase in REW](https://www.youtube.com/watch?v=El-kwZ5_nnU).

> [!WARNING]
> **Führe Messungen mit dem Mikrofon auf einem Stativ durch und wiederhole den Kontroll-Sweep am Ende!**
> * **Temperaturdrift der Innenraumluft:** Die Schallgeschwindigkeit ändert sich mit der Temperatur im Innenraum. Wenige Grad Unterschied verschieben die Ankunftszeiten um Dutzende Mikrosekunden.
> * **Drift summiert sich mit jedem Sweep:** Ein Lautsprecher, der über 18 Minuten hinweg 6 Mal hintereinander gemessen wurde, verschob sich um ein Sample (10 µs, was einer Verschiebung des Mikrofons um ~3,6 mm entspricht) — verursacht durch die laufenden Sweeps, nicht bloß durch das Verstreichen der Zeit.
> * **Stativ-Platzierung:** Platziere das Mikrofon auf Ohrhöhe für den im Projekt definierten **Referenzsitz**, ausgerichtet an physischen Markierungen, und bewege es nicht, bis der Block abgeschlossen ist.
> * **Kontroll-Sweep:** Das Messen des Anfangskanals (`ctl1`) und dessen Wiederholung am Ende (`ctl3`) ermöglicht es der Prüfung, jede Zeitdrift zu benennen, bevor die Runde geschlossen wird; ob du neu misst, ist deine Entscheidung.

---

### Regeln für die Benennung von Messungen in REW

Berechnungstools finden Messungen strikt anhand ihrer Namen in REW:

* `m-L_1 (sw)` — Kanal `m-L` (linker Mitteltöner), Messreihe `1`, Sweep-Messung. Ein DSP-Zustand kann mehrere Serien haben; die Nummer ist auch nicht die Versionsnummer des Registers.
* `m-L_1 (rta)` — Moving-Mic-RTA-Messung für denselben Lautsprecher.
* `tw-L_1 (sw)`, `w-R_1 (sw)`, `sw_1 (sw)` — linker Hochtöner, rechter Tieftöner (Mittelbass / Midbass), Subwoofer.
* `L_1 (rta)`, `ALL_1 (rta)` — Summen-RTA der kompletten linken Seite oder des Gesamtsystems.
* `m-L p5_1 (sw)` — der Lautsprecher am räumlichen Kontrollpunkt `p5` (wird auch als `m-L_1 (sw) p5` gelesen).
* `m-L-ctl1_1 (sw)` und `m-L-ctl3_1 (sw)` — Zeitkontrolle: Die erste eröffnet die Lautsprecherserie, die zweite schließt sie ab; es gibt kein `ctl2` (im Auto als `m-L_1ctl` und `m-L_1rep` eingegeben, bedeuten sie dasselbe).
* `m-L_final (sw)` — Verifizierungsmessung nach dem Speichern der finalen Parameter.
* `w-L (imp)` — Impedanzmessung eines Treibers; sie ist nicht an einen DSP-Zustand gebunden und trägt keine Seriennummer.
* Text nach der Methode macht daraus **eine weitere Messung derselben Serie**: `r-L_17 (sw) noXO` ist nicht `r-L_17 (sw)`.

Titel werden exakt so abgeglichen, wie sie eingegeben wurden. Ein Titel, der nicht zu dem passt, was der Schritt erwartet, ist eine Frage, die die KI dir stellt — niemals eine Vermutung.

Der vollständige Messablauf ist in [`references/phases/capture-session-sheet.md`](skills/autosound-tuning/references/phases/capture-session-sheet.md) beschrieben.

---

### Einmessung (Capture-Session): Warum nur Schutzfilter?

> [!IMPORTANT]
> **REW muss während des gesamten Prozesses geöffnet bleiben:** Der Skill liest Kurven direkt über die API aus dem aktiven REW-Fenster, nicht aus auf die Festplatte exportierten Dateien.
>
> **Schutzfilter BLEIBEN während der Einmessung AKTIV:** Hochpassfilter (HPF) für empfindliche Hoch- und Mitteltöner müssen im DSP aktiv bleiben, um sie während der Mess-Sweeps zu schützen.

* **Schutzfilter-Regel:** Der schützende HPF muss **$\ge 1{,}1 \times Fs$ (empfohlen bis zu $1{,}5 \times Fs$) mit einer Flankensteilheit von $\ge 24$ dB/Okt.** betragen (LR4 oder BW4). Ist $Fs$ unbekannt, schlage den Wert im Datenblatt des Herstellers nach und gib ihn im Projekt an.
* **Aktive Filter deaktiviert:** Betriebs-EQ (leer), Laufzeiten (auf 0 gesetzt) und Polaritäten (normal) müssen sauber sein. Erfasse jeden Schutzfilter in der Capture-Runde (die App fragt danach; im Terminal erfasst es die Sitzung): Die Tools rechnen ihn dann aus diesem Solo heraus, bevor die gemeinsame Phase ermittelt wird. Ein als `OFF` erfasster Kanal wird unverändert eingelesen.
* **Pegel in dBFS:** Stelle die Sweep-Lautstärke so ein, dass die Spitze des lautesten Treibers (Subwoofer) bei $-5\dots-10$ dBFS liegt und der leiseste Treiber deutlich über dem Grundrauschen des Innenraums liegt. Prüfe die Geräuschpegel bei ausgeschaltetem und bei laufendem Motor. Schalte alle inaktiven Kanäle in deiner DSP-Software stumm und halte die Lautstärke von Soundkarte und Head-Unit während der gesamten Sitzung unverändert.
* **Klang des Mittelbass-Sweeps:** Ein Mittelbass, der ohne LPF gemessen wird, erzeugt bei hohen Frequenzen während des Sweeps ein raues, kratziges Geräusch. Das sind normale **Membranresonanzen (Cone Breakup)** am oberen Ende seines Übertragungsbereichs; der Treiber nimmt keinen Schaden.

---

### Wozu dienen die Positionen p1…p9 und die Zeitkontrolle ctl?

* **Unterscheidung von Treiber- und Einbauresonanzen von Innenraumreflexionen:** Resonanzen bleiben stabil, wenn die Mikrofonposition leicht verschoben wird (sicher per EQ zu korrigieren). Nullen durch Innenraumreflexionen verschieben sich auf der Frequenzachse drastisch — sie anzuheben ist zwecklos.
* **Berechnung der Grenzen für die EQ-Filtergüte (Q):** Die räumliche Varianz über `p1…p9` bestimmt die sicheren Grenzen für die Filtergüte des Equalizers.
* **Überwachung der Zeitdrift:** Der eröffnende und der abschließende `ctl`-Sweep erkennen Takt- oder Temperaturdrift während der Sitzung.

---

## Zielkurven (Target Curves)

### Wie erstelle und konfiguriere ich meine eigene Zielkurve?

Eine Zielkurve ist eine anfängliche klangliche Hypothese, die du nach dem Erstellen der technischen Basis-Abstimmung nach Gehör verfeinerst.

1. **Aus etablierten Kurven auswählen:** Wähle aus kalibrierten Zielkurven — SQ-Comp-Ref (die eigene der Methode), ResoNix, Audiofrog, Harman, Jazzi und Whitledge — passend zu deinen Hörvorlieben. Das Skript `target_bands.py` berechnet aus deiner gewählten Kurve und den Trennfrequenzen die Zielverläufe für jedes einzelne Chassis.
2. **Manuell zeichnen:** Nutze das kostenlose [Nono Tuning Tool](https://nonotuningtool.com) (Bereich *Custom Target Curve*), um einen Verlauf zu zeichnen und eine `.txt`-Zieldatei zu exportieren.
3. **Online vergleichen:** Entdecke unseren interaktiven Visualisierer:  
   👉 **[Zielkurven-Visualisierer online öffnen](https://ayukhno.github.io/autosound-tuning-skill/_curve-visualizer.html?lang=de)**. Ein Rechtsklick auf einen beliebigen Punkt im Diagramm erklärt, wie sich dieser Frequenzbereich auf den Klang auswirkt.

📘 [The house curve in TCC (EN)](https://github.com/ayukhno/autosound-tcc/blob/main/docs/guide/HOUSE-CURVE.md)

---

## Projekt auf der Festplatte und DSP

### Struktur des Projektordners und Datensicherung

Dein Projektverzeichnis speichert die vollständige Konfiguration und die Abstimmungshistorie deines Fahrzeugs:

| Datei / Verzeichnis | Inhalt | Zweck |
| :--- | :--- | :--- |
| **`project.json`** | Systemkonfiguration | Lautsprecherkanäle, DSP-Ausgänge, Profil, Mikrofon-Spezifikationen, Zielkurve. |
| **`state/versions/` + `slots.json`** | Versionsregister | Chronologische Historie aller Frequenzweichen, Laufzeiten, Pegel und EQs. |
| **`process/process-state.json`** | Prozess-Status | Nachverfolgung der aktiven Phase und Verifizierungsprotokolle. |
| **`autosound_context.md`** | Fahrzeugkontext | Fahrzeug-Wörterbuch, Einbau-Layout, Innenraum-Notizen. |
| **`*.txt` / `*.json`** | Kurven & DSP-Exporte | Zielkurven und generierte EQ-Parameterdateien. |

> [!IMPORTANT]
> **Lokale `.mdat`-Kopien aufbewahren:** Die Methode verlangt, bei der technischen Abnahme und zum Sitzungsabschluss eine lokale Kopie der REW-`.mdat`-Dateien aufzubewahren. Große `.mdat`-Dateien (jeweils 16–112 MB) bleiben außerhalb von Git; deine lokalen Kopien müssen stets erhalten bleiben. Für ein kostenloses privates Backup des Projektordners auf GitHub installiere mit `--github` (`-GitHub` unter Windows) und bitte die KI um ein Backup des Projekts: Sie bietet das Repository an, erstellt nichts ohne dein Ja und weiß, was draußen bleibt.

---

### Kompatibilität mit Prozessoren und Filter-Import in den DSP

> ⚠️ **Wichtig:**  
> Die Methode berechnet die Filter. Laufzeiten und Pegel werden vom Einsteller immer **manuell** eingegeben, ebenso wie Frequenzweichen, es sei denn, ein Einfüge-Tool übernimmt sie aus dem unten genannten Extended-Export. Ein Datei-Import überträgt ausschließlich den **EQ**.

* **Audiotec Fischer (Helix / MATCH / BRAX):** Erzeugt eine importfertige Full-EQ-Datei, die das DSP PC-Tool für alle Kanäle in einem Schritt lädt.
* **Andere DSP-Prozessoren:** Exportiert REW Generic EQ-Dateien (20 Slots) oder Generic/Extended mit integrierten Frequenzweichen. Für die schnelle Parametereingabe in andere DSP-Software über Tastatur-Makros nutze den kostenlosen [REW-EQ-CopyPaste-Assistant](https://github.com/IvanBakhmutov/REW-EQ-CopyPaste-Assistant).
* **Kompatibilitätsprüfung:** Vor dem Export vergleichen Skripte jeden berechneten Filter mit den Grenzen deines DSP-Modells (verfügbare Bänder, Sampling-Rate, Filtertypen) und weisen auf Abweichungen hin.
* **Werksradios (OEM Head Units):** Die empfohlene Praxis ist es, Werksradios über einen sauberen, direkten digitalen oder analogen Eingang (DAP, USB, optisch) in den DSP zu **umgehen (Bypass)**, anstatt zu versuchen, das werkseitige Klang- und Loudness-Processing zu de-equalisieren.

---

### Arbeiten mit passiven Frequenzweichen (Hochtöner + MT auf einem Kanal)

Ein Treiberpaar an einer passiven Frequenzweiche wird als **ein einzelner gemeinsamer DSP-Kanal** behandelt: Es erhält eine Messung, eine gemeinsame Laufzeit, einen gemeinsamen Pegel und einen Satz EQ-Filter.

Alles andere funktioniert wie gewohnt, und der Summenfrequenzgang ist physikalisch korrekt — einschließlich etwaiger Phasenprobleme am passiven Übergang. Was keine Software von außen tun kann, ist, Laufzeit oder Phase zwischen Hoch- und Mitteltöner **innerhalb** dieser passiven Gruppe anzugleichen: Dazu benötigt jeder Treiber seinen eigenen DSP-Kanal.

---

### Wo finde ich die vollständige Liste der Funktionen der Methode?

Eine detaillierte Übersicht über jedes Tool und jeden Befehl befindet sich im Capabilities-Board:
[`references/core/capabilities.md`](skills/autosound-tuning/references/core/capabilities.md).  
Befehle filtern mit: `python3 ~/.claude/skills/autosound-tuning/rew_tool/capabilities.py find "phase"`.
