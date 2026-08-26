# FAQ — Häufig gestellte Fragen zur Car-Audio-Abstimmung

🇬🇧 [English](FAQ.md) · 🇩🇪 **Deutsch** · 🇵🇱 [Polski](FAQ.pl.md) · 🇺🇦 [Українська](FAQ.uk.md) · 📄 [README](README.de.md) · <img src="assets/icons/roadmap.svg" width="14" height="14" valign="middle" alt="Roadmap" /> [Roadmap (EN, Entwurf)](ROADMAP.md)

Echte Benutzerfragen zur Installation und Abstimmung Ihres Systems mit diesem Tool. [README](README.de.md) ist die Kurzversion; diese Seite enthält alle Details.

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

* 🖥️ **Option 1 · Version 3.x im grafischen Fenster (Autosound TCC)**
  Der am stärksten automatisierte und visuellste Weg. Der Installer richtet Claude Code, Python, den Kern der Methode, die grafische Benutzeroberfläche und den automatischen KI-Reviewer ein.
  * **Voraussetzungen:** macOS oder Windows, kostenpflichtiges Claude Pro/Max, REW-Beta mit aktiviertem API, ~700 MB freier Speicherplatz.
  * **Vorteile:** Sie sehen den Systembaum, die Messkurven, den Schritt-für-Schritt-Plan und das Chat-Fenster in einer einzigen Benutzeroberfläche. Der Zustand wird automatisch gespeichert, und jede Aktion im Versionsregister kann mit einem Klick rückgängig gemacht werden.
  * **Nachteile:** Die grafische App ist noch sehr jung und befindet sich derzeit im Beta-Test.

* 💻 **Option 2 · Version 3.x im Terminal**
  Derselbe moderne Kern und Automatisierungsgrad, aber die Interaktion erfolgt ausschließlich textbasiert in der Konsole. Wird über den Installer mit dem Flag `--terminal` eingerichtet.
  * **Voraussetzungen:** Die gleichen Abonnements und REW mit API, jedoch ohne grafische Oberfläche.
  * **Vorteile:** Maximale Arbeitsgeschwindigkeit, minimaler Systemressourcenverbrauch. Projekte sind vollständig kompatibel mit der grafischen TCC-App (Sie können denselben Ordner später in der GUI öffnen).

* 🏆 **Option 3 · Die 2.x-Linie (Der bewährte Champion)**
  Das stabile Plugin für Claude Code, fest fixiert auf der Version `v2.8.3` (Zweig `2.x`). Mit genau diesem Algorithmus abgestimmt, holte das Auto des Autors 2026 vier Auszeichnungen bei EMMA und AYA.
  * **Voraussetzungen:** Kostenpflichtiges Claude Pro, REW-Beta mit API, Arbeit im Terminal.
  * **Vorteile:** Ein über Jahre und Wettbewerbe bewährter, absolut stabiler Algorithmus. Erhält nur noch kritische Fehlerbehebungen (Bugfixes), neue Funktionen werden hier nicht mehr hinzugefügt.
  * **Nachteile:** Keine automatische Zustandsüberwachung (alles wird manuell in Text-Markdown-Dateien geführt), kein „Schreibtisch zuerst“-Ansatz und keine modernen Berechnungstools.

* 🌐 **Option 4 · Web-Chat (Ohne Programminstallation)**
  Manuelles, schrittweises Abstimmen über den [manual_step-by-step-Zweig](https://github.com/ayukhno/autosound-tuning-skill/tree/manual_step-by-step).
  * **Voraussetzungen:** Kostenloses Google AI Studio oder ein beliebiger Web-Chat mit einer KI Ihrer Wahl.
  * **Vorteile:** Absolut kostenlos. Erfordert keine Installation von Software oder Entwicklerwerkzeugen auf Ihrem Computer. Perfekt, um die Logik der Methode kennenzulernen.
  * **Nachteile:** Jeder Schritt wird rein manuell ausgeführt (Kopieren von Prompts, eigenständiger Export von Textdateien aus REW), keine API-Integration und keine automatische Überprüfung der Berechnungen durch lokale Scripte.

---

### Welche Option soll ich wählen?

* **Sie möchten maximale Automatisierung und Grafik:** Wählen Sie **Option 1 (TCC)**.
* **Sie bevorzugen die Konsole ohne zusätzliche Software:** Wählen Sie **Option 2 (3.x Terminal)**.
* **Sie suchen bewährte Meisterschaftsstabilität:** Wählen Sie **Option 3 (2.8.3)**.
* **Sie möchten die Logik kostenlos testen:** Wählen Sie **Option 4 (Web-Chat)**.

> [!NOTE]
> Sie sind nicht an eine einzige Entscheidung gebunden: Projekte der 3.x-Linie lassen sich problemlos sowohl in der Konsole als auch im grafischen TCC-Programm öffnen, und der Übergang von Version 2.x auf 3.x ist vollkommen automatisiert.

---

### Wie ermittle ich die bereits installierte Version?

* **Anhand des verwendeten Befehls:** Wenn Sie das Plugin mit dem Befehl `/plugin install autosound-tuning` in Claude Code installiert haben, nutzen Sie die Version **2.x**. Wenn Sie das Ein-Zeilen-Installationsskript (`curl … | bash` oder `irm … | iex`) ausgeführt haben, nutzen Sie die Version **3.x**.
* **Am Inhalt des Projektordners:** Wenn der Ordner die Datei `dsp-state-current.md` enthält, handelt es sich um ein **2.x**-Projekt. Wenn der Ordner die maschinenlesbaren Dateien `project.json` und `process-state.json` enthält, ist es ein **3.x**-Projekt.
* **Über die Programmoberfläche:** Gehen Sie in der TCC-App auf das Menü *Diagnostics → Installation*.

---

### Wie bleibe ich auf der stabilen 2.x-Linie?

Das normale automatische Plugin-Update wird Sie nicht unaufgefordert auf die 3.x-Version umstellen. Wenn Sie die Version jedoch vollständig einfrieren und die Fehlerbehebungen für den 2.x-Zweig lokal kontrollieren möchten, klonen Sie das Repository selbst:

```bash
git clone -b 2.x https://github.com/ayukhno/autosound-tuning-skill.git ~/autosound-2x
```

Führen Sie anschließend in Claude Code diese zwei Befehle aus:
```bash
/plugin marketplace add ~/autosound-2x
/plugin install autosound-tuning
```
Nun verweist Ihr Plugin auf den lokalen Ordner. Sie können es bei Bedarf mit einem einfachen `git -C ~/autosound-2x pull` aktualisieren.

---

### Wechsel von 2.x auf 3.x

Es kann immer nur ein solches Plugin gleichzeitig im System aktiv sein. Bevor Sie die Version 3.x installieren, müssen Sie die alte Version 2.x in Claude Code deinstallieren:

```
/plugin uninstall autosound-tuning
/plugin marketplace remove autosound-tuning-skill
```

Nach der Installation der neuen Version 3.x können Sie den aktuellen Zustand des Fahrzeugs (aktive Trennfrequenzen, Laufzeitkorrekturen, Pegel, Equalizer und DSP-Profil) mit einem automatischen Migrationsskript in das neue Format übertragen:

```sh
python3 ~/.claude/skills/.autosound-tuning-src/skills/autosound-tuning/rew_tool/state/migrate.py <pfad-zum-alten-projekt> --into <pfad-zum-neuen-projekt>
```

---

### Hauptänderungen in 3.x

* 📦 **Projekt als Datenstruktur:** Alle Systemparameter werden in den Dateien `project.json` und `process-state.json` gespeichert. Die KI liest präzise Fakten, anstatt zu versuchen, sich an diese aus dem Textverlauf des Chats zu erinnern.
* 🛋️ **Der „Schreibtisch zuerst“-Ansatz:** Statt vieler Fahrten zum Auto — **eine Sitzung für die vollständige akustische Vermessung** (Phase 0) und **eine kurze zur Überprüfung** (Phase 3). Die gesamte weitere Analyse, die Berechnung der Trennfrequenzen, die Phasenabstimmung und die Equalizer-Einstellungen werden am Schreibtisch auf Basis einer präzisen virtuellen Prognose durchgeführt.
* 🧮 **Mathematische Verifizierung:** Spezielle lokale Skripte analysieren die Kurven nach dem Kriterium der minimalen Phasenverluste, begrenzen die Filtergüte (Q) des Equalizers basierend auf der Streuung der Messpunkte und erkennen automatisch Zeitfehler des Mikrofons.
* 🛑 **Automatische Verweigerung:** Wenn die Eingangsmessungen widersprüchlich sind, das Mikrofon einen zu großen Zeitfehler aufweist oder Kanäle fehlen, bricht das System die Berechnungen ab und lehnt die Messrunde ab, um ungenaue oder für die Lautsprecher gefährliche Ergebnisse zu verhindern.

---

## Philosophie und Architektur: Wozu KI?

### Mission und Konzept

Wir erschaffen ein **intellektuelles Exoskelett** für die Klangabstimmung. Der Mensch (Arbiter/Schiedsrichter) bleibt immer das entscheidende Glied — er hört das System, beurteilt die Tiefe, Höhe und Stabilität der Bühne und trifft die endgültigen Entscheidungen.

Die KI übernimmt die routinemäßigen Berechnungen und die Physik des Innenraums: Sie analysiert Phasen, berechnet die exakte Laufzeitkorrektur an den Übergängen der Frequenzbereiche und steuert REW über das API, um Ihnen Zeit für das kreative Musikmachen zu schenken.

---

### Warum ist dies ein spezialisierter Skill und kein normaler Chat?

* **Vermeidung von Gedächtnisverlust (Memory Drift):** Jeder normale KI-Chat vergisst nach einigen Stunden Unterhaltung die Ausgangswerte, verwechselt Pegel oder Trennfrequenzen. Unser System speichert den aktuellen Projektzustand in der Datei `project.json` auf Ihrer Festplatte. Die KI liest diese Datei bei jeder neuen Anfrage — ihr Gedächtnis wird nicht „erinnert“, sondern zuverlässig geladen.
* **Spezialisiertes Car-Audio-Wissen:** Der Skill enthält feste Sicherheitsregeln zum Schutz der Hochtöner, Phasenabstimmungs-Algorithmen, vorgefertigte Zielkurven und die Logik zur Analyse des Fahrzeuginnenraums, von denen allgemeine KI-Modelle keine Ahnung haben.
* **Lokale Verarbeitung über REW-API:** Die Rohdaten der Messungen (Tausende von Punkten pro Kurve) werden von lokalen Python-Skripten in Millisekunden verarbeitet. Die KI erhält im Chat nur eine prägnante mathematische Zusammenfassung. Dies schließt manuelle Übertragungsfehler aus und spart Token-Kosten.

---

### Ablaufplan: Phasen −1…5 und der „Schreibtisch zuerst“-Ansatz

| Phase | Wo stattfindend | Was wird getan | Ergebnis der Phase |
| :--- | :--- | :--- | :--- |
| **−1 Vorbereitung** | am Schreibtisch | Eingabe der Fahrzeugdaten, Lautsprecher, DSP-Optionen und Auswahl der Zielkurve. | Erstellung der `project.json` und der Konfiguration. |
| **0 Messung** | im Auto (1 Mal) | Messung jedes Lautsprechers einzeln mit **Schutzfiltern** (HPF); Sweeps und RTA-Messungen während der Fahrt. | Eine geprüfte und qualitativ hochwertige Messrunde. |
| **1 Fundament** | am Schreibtisch | Berechnung der Trennfrequenzen, Pegel, Laufzeitkorrekturen und Polarität basierend auf der Phasenprognose. | Basis-Abstimmung des Systems im Versionsregister. |
| **2 Equalizer** | am Schreibtisch | EQ erfolgt in **Paketen**: Resonanzen der Treiber → Links/Rechts-Vergleich → Anpassung an die Zielkurve. Standardmäßig nur Absenkungen, max. 6 Bänder pro Kanal. Jedes Paket bedeutet eine Entscheidung „Ja/Nein“ und eine neue Registerversion. | Fertige Exportdateien der Einstellungen für Ihren DSP. |
| **3 Urteil** | im Auto (kurz) | Eingabe der Werte in den DSP. Der Eingangs-Check prüft, ob die realen Messungen mit der mathematischen Prognose übereinstimmen. | Vollständig verifizierte und fixierte technische Abstimmung. |
| **4 Hören** | im Auto | Test-Tracks (EMMA/AYA-Discs, CarMus, Chesky) und ein Spickzettel „Worauf zu achten ist“. Wenn etwas dröhnt oder scharf klingt, erstellt der Skill eine Verdachtsliste und korrigiert Band für Band im A/B-Vergleich (max. 3 Runden). | Live-Hörprotokolle, die an die Versionen gekoppelt sind. |
| **5 Variationen** | am Schreibtisch/im Auto | Abstimmung zusätzlicher Presets (für verschiedene Musikrichtungen, Center-Kanal etc.) ohne Änderung der technischen Basis. | Zusätzliche Klang-Presets im System. |

> [!NOTE]
> Sollten die realen Messungen im Auto in Phase 3 von der mathematischen Prognose abweichen, setzt das System den Schritt automatisch zurück und wechselt zum klassischen, schrittweisen Abstimmungsverfahren.

---

### Was lehnt die Methode kategorisch ab?

* **Direktes Schreiben von Daten in Ihren DSP** — die Eingabe der Parameter im DSP-Programm bleibt immer in Ihrer Hand.
* **Berechnung der Laufzeitkorrektur auf Basis einer einzigen Messung** — es werden mindestens 4 unabhängige Zeitmessungen benötigt.
* **Anheben von Frequenzen in Bereichen von Phasenauslöschungen (akustischen Nullen)** — solche Einbrüche entstehen durch Interferenzen im Innenraum, nicht durch den Lautsprecher. Ein Auffüllen durch Erhöhung des Pegels ist **prinzipiell unmöglich**: Am Hörplatz ändert sich nichts, während Lautsprecher und Verstärker überlastet werden. Einbrüche, die angehoben werden dürfen, unterscheidet das System präzise durch die Analyse der Exzess-Phase (*Excess phase* in REW) — nur die minimalphasigen Bereiche werden korrigiert.
* **Arbeiten mit minderwertigen Messungen** — ein erkannter Zeitfehler des Mikrofons (Temperaturdrift) oder fehlende Schutzfilter führen zur sofortigen Ablehnung der gesamten Messrunde.

---

### Welche KI-Modelle werden offiziell unterstützt?

* 🧠 **Hauptmodell (Generator):** Claude Opus (mit der Einstellung `xhigh` für maximale Denkleistung).
* 👁️ **KI-Reviewer (Kritiker):** Gemini Pro (High).

*Stand August 2026.* KI-Technologien entwickeln sich rasant. Wenn Sie diesen Text deutlich später lesen, prüfen Sie bitte die aktuellen Empfehlungen für äquivalente Modelle.

> [!IMPORTANT]
> **Senken Sie die Denkleistung von Claude nicht unter `xhigh`.**
> Schwächere Modelle oder geringere Denkstufen melden keinen Fehler — sie stimmen einfach stumm allem zu und erfinden technisch unbrauchbare Werte.

---

### Abonnement-Optionen und KI-Budget

* **Option 1 (Empfohlene Basis): Claude Pro ($20/Monat) + kostenloses Gemini als Reviewer**
  Die beste Balance aus Zuverlässigkeit und Kosten. Nutzen Sie einen kostenlosen API-Schlüssel von Gemini, den Sie im Google AI Studio erhalten. Das Claude Pro Abonnement kann sofort nach der Abstimmung des Autos gekündigt werden.
* **Option 2 (Günstiger Kompromiss): Nur Gemini ($10 Prepaid-Guthaben auf Google Cloud)**
  Extrem kostengünstig, erfordert jedoch, dass Sie jeden Wert selbst überprüfen und den Chatverlauf vor jeder neuen Phase mit dem Befehl `/clear` leeren, da kein unabhängiger Reviewer zur Kontrolle bereitsteht.
* **Option 3 (Professionell): Claude Pro ($20) + kostenpflichtiges Gemini Cloud API**
  Völlige Freiheit von Geschwindigkeitsbegrenzungen oder Kontingentbeschränkungen. Optimal für gewerbliche und regelmäßige Systemabstimmungen an vielen Fahrzeugen.

---

### Warum sind die tatsächlichen Token-Kosten niedriger als gedacht?

1. Lokale Python-Skripte komprimieren Tausende von REW-Messpunkten in kurze Textberichte. Rohkurven gelangen nicht in den Chat.
2. Der gesamte Projektverlauf wird auf der Festplatte gespeichert, sodass die KI nicht bei jeder Anfrage den kompletten Verlauf neu lesen muss.
3. Es wird das Prinzip des gleitenden Fensters angewendet — es werden nur die Daten der aktuellen Arbeitsphase geladen. Sie zahlen für **Entscheidungen**, nicht für Datenübertragung.

---

## Erstinstallation (macOS und Windows)

### Automatische Installation

Sie benötigen ein Notebook, ein Messmikrofon, einen DSP-Prozessor und ein kostenpflichtiges **Claude Pro oder Max** Abonnement.

<details>
<summary><b>Anleitung für macOS</b></summary>

1. Öffnen Sie die App **Terminal** (drücken Sie `Cmd + Leertaste` → geben Sie `Terminal` ein → drücken Sie `Enter`).
2. Fügen Sie folgenden Befehl ein und drücken Sie `Enter`:
   ```bash
   curl -fsSL https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/main/install.sh | bash
   ```
3. Das Skript fragt Sie möglicherweise einmal nach dem Passwort Ihres Mac, um die offiziellen Apple Command Line Tools (git) zu installieren. Warten Sie ca. 10–20 Minuten.

</details>

<details>
<summary><b>Anleitung für Windows</b></summary>

1. Öffnen Sie die App **Windows PowerShell** (drücken Sie die `Windows-Taste` → geben Sie `powershell` ein → drücken Sie `Enter`).
2. Fügen Sie folgenden Befehl ein und drücken Sie `Enter`:
   ```powershell
   irm https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/main/install.ps1 | iex
   ```
3. Falls Git nicht auf Ihrem System vorhanden ist, bestätigen Sie die Installation mit **Ja**. Das Skript erstellt außerdem eine Verknüpfung für **REW (API on)** auf Ihrem Desktop.

</details>

---

### Wohin werden die Komponenten installiert?

Alle Dateien werden ausschließlich innerhalb Ihres Benutzerprofils gespeichert:

| Komponente | Installationspfad | Zweck |
| :--- | :--- | :--- |
| **Claude Code** | Offizielles Anthropic-Verzeichnis | Der Haupt-KI-Assistent, der den Prozess leitet |
| **Methode** | `~/.claude/skills/.autosound-tuning-src` | Der Ordner, in dem Claude Code nach Skills sucht |
| **Autosound TCC** | Benutzerordner und Desktop-Verknüpfung | Die grafische App und eine isolierte Python 3.12 Umgebung |
| **Befehlszeilentool `agy`** | Benutzerprofil | Tool von Google zur schnellen Hintergrundkommunikation mit dem Gemini-Reviewer |

---

### Erststart und Account-Anmeldung

1. **Anmeldung bei Claude:** Am Ende der Installation öffnet das Skript automatisch den Befehl `claude auth login`. Melden Sie sich im Browser mit Ihrem kostenpflichtigen Account an und klicken Sie auf **Authorize**.
2. **Anmeldung bei Gemini:** Führen Sie einmalig in einem neuen Terminal-Fenster den Befehl `agy` aus und melden Sie sich mit dem Google-Konto an, das Zugang zu Antigravity hat.
3. **Arbeitsbeginn:** Erstellen Sie einen leeren Ordner für das Fahrzeug (z.B. `MeinAutoTuning`). Öffnen Sie diesen in der App **Autosound TCC** (über den Button *Browse…*) oder in einem neuen Terminal-Fenster (`cd pfad` → Befehl `claude` eingeben) und schreiben Sie in den Chat: **„Abstimmung für ein neues Auto von Grund auf starten“** (oder auf Englisch: *"tune a new car from scratch"*).

---

### Aktualisierung, Version fixieren und Deinstallation

* **Aktualisierung:** Führen Sie dieselbe Installationszeile einfach erneut aus. Das Skript lädt automatisch das neueste Tag `v3.*` herunter (dies ist ein Vorab-Release, kein stabiler Zweig — stabil ist die 2.8.x-Linie) und lässt Ihre Projekte unberührt.
* **Version fixieren:** Nutzen Sie die Parameter `--skill-ref v3.0.32` und `--tcc-ref v0.1.12` unter macOS oder `-SkillRef` und `-TccRef` unter Windows während der Installation.
* **Deinstallation:** Führen Sie den Installer mit dem Parameter `--uninstall` aus (oder zusätzlich `--all` für eine vollständige Bereinigung der Entwicklungsumgebungen). Ihre Projektordner werden niemals gelöscht.

---

## Grafische Desktop-App Autosound TCC

### Was ist das und brauche ich es?

Die App [TCC](https://github.com/ayukhno/autosound-tcc) ermöglicht es Ihnen, komfortabel im grafischen Fenster unter macOS und Windows zu arbeiten. Sie sehen den Systemaufbau, die REW-Messungen, den Ablaufplan und den KI-Chat auf einem Bildschirm. Die App ist optional — Sie können Ihr Auto komplett über die Konsole mit Claude Code abstimmen, da alle Projektdaten in gewöhnlichen maschinenlesbaren Dateien auf der Festplatte gespeichert werden. Die App ist jünger als die eigentliche Methode und befindet sich derzeit im Beta-Status.

### Arbeiten auf zwei Fenstern (Terminal + Grafik)

Die App und das Terminal greifen auf exakt dieselben Projektdateien zu. Sie können frei zwischen ihnen wechseln: Alle in der Konsole erstellten Schritte oder Registerversionen werden sofort in der grafischen Oberfläche angezeigt und umgekehrt.

### KI-Modelle in der App

Die App nutzt Ihr kostenpflichtiges Claude-Abonnement (über das offizielle Anthropic-SDK) und Ihr kostenloses Google-Konto über das lokale `agy`-Tool für den KI-Reviewer. Alternative Modelle stehen nur zur Verfügung, wenn Sie das `omp`-System aktivieren (gesonderte Abrechnung).

### Updates und Fehlermeldungen

Die App aktualisiert sich automatisch zusammen mit dem mathematischen Kern. Sie können die installierten Versionen im Menü *Diagnostics → Installation* überprüfen. Fehler in der Benutzeroberfläche melden Sie bitte über den Button *Report a problem* auf GitHub für die TCC-App, Fehler in der Abstimmungslogik im Repository des Skills selbst.

---

## Eigenständiger KI-Reviewer Gemini/Antigravity

Die doppelte Überprüfung (Generator ↔ Gemini-Kritiker) schließt menschliche und mathematische Fehler der Modelle nahezu vollständig aus. Der Reviewer erkennt Unstimmigkeiten, die dem primären KI-Modell entgehen. Er läuft vollkommen im Hintergrund über ein lokales Skript ab — Sie müssen keine Daten manuell hin und her kopieren. Das ist zwar optional, liefert jedoch den größten Nutzen für das Endergebnis.

### Installation für macOS und Windows (Empfohlen)

Das offizielle Befehlszeilentool **Antigravity CLI (`agy`)** von Google benötigt keine API-Keys und nutzt eine einfache, kostenlose Browser-Anmeldung (OAuth).

1. **Installation:** Der Installer hat dieses Tool bereits automatisch eingerichtet. Für eine manuelle Installation führen Sie folgendes aus:
   * *macOS:* `curl -fsSL https://antigravity.google/cli/install.sh | bash`
   * *Windows:* `irm https://antigravity.google/cli/install.ps1 | iex`
2. **Anmeldung:** Starten Sie den Befehl `agy` im neuen Terminal, melden Sie sich im Browser mit einem Google-Konto an, kehren Sie zur Konsole zurück und geben Sie `/quit` ein.
3. **Test:** Prüfen Sie die Funktion mit dem Befehl `agy -p "Hello, world!"`.

---

### Fallback-Option: Direkter Gemini API-Key

Unter Linux oder bei Erschöpfung des Antigravity-Budgets können Sie einen kostenlosen Gemini-API-Key direkt eintragen:

1. Holen Sie sich einen kostenlosen API-Key auf **[aistudio.google.com/apikey](https://aistudio.google.com/apikey)**.
2. Erstellen Sie eine Textdatei namens `.critic-env` im Ordner **Ihres Projekts** (entweder im Ordner `rew_analitic/` oder in dem Verzeichnis, aus dem Sie die Arbeit starten) und tragen Sie dort ein:
   ```env
   GEMINI_API_KEY=ihr_api_key_hier
   ```
3. Die Skripte erkennen den Schlüssel automatisch und senden direkte HTTPS-Anfragen an das Gemini-API.

> [!TIP]
> Falls weder das `agy`-Tool noch ein API-Key gefunden werden, wechselt das System automatisch in den integrierten Hintergrund-Modus (Autopilot self-loop) oder bietet Ihnen den manuellen Zwischenablage-Modus (Clipboard Mode) an.

---

### Kann ich die Methode komplett in Gemini ausführen?

Ja, aber nur als manueller Durchlauf, nicht als automatisierte Installation. Geben Sie der Gemini-Session (mit Dateizugriff und Systemsteuerung) den direkten Befehl:

> Clone https://github.com/ayukhno/autosound-tuning-skill, read `skills/autosound-tuning/SKILL.md`, and follow that method as your operating instructions for this session.

Da dort der Mechanismus des gleitenden Fensters fehlt, neigt Gemini bei längeren Sitzungen zu Präzisionsverlusten. Die stabilste kostenlose Option ist daher **Option 4** (die fertigen Schritt-für-Schritt-Prompts für das [Google AI Studio](https://aistudio.google.com/) im [manual_step-by-step-Zweig](https://github.com/ayukhno/autosound-tuning-skill/tree/manual_step-by-step)).

---

## Messungen durchführen

### Phasenmessung: XLR-Mikrofone vs. USB (UMIK-1/2)

* **XLR-Mikrofone (Behringer ECM8000, Beyerdynamic MM1 etc.):** Werden über ein externes Audio-Interface angeschlossen. Sie ermöglichen eine **physikalische Rückschleife (Loopback)** — ein Kabel, das den Ausgang des Interfaces direkt mit einem freien Eingang verbindet. Dies gibt dem PC eine absolut zeitstabile, auf ein Sample exakte Referenz für den Start der Messung.
* **USB-Mikrofone (UMIK-1 / UMIK-2):** Werden direkt am USB-Port des Notebooks betrieben. Sie besitzen keinen analogen Eingang, weshalb ein physisches Loopback-Kabel nicht möglich ist.

---

### Kann ich die Phase mit einem UMIK-1 messen?

**Ja.** Nutzen Sie dazu in REW die Funktion **Acoustic Timing Reference (akustische Zeitreferenz)**. Vor jedem eigentlichen Messsignal gibt die Soundkarte ein kurzes, hochfrequentes Signal (einen „Chirp“) über einen festgelegten Referenzlautsprecher (meist der dem Mikrofon am nächsten gelegene Hochtöner) ab. Dieses Signal dient als zeitlicher Nullpunkt für den zu messenden Kanal.

Eine Videoanleitung zur REW-Konfiguration für USB-Mikrofone finden Sie im Tutorial von RAW-Cat: [Measuring Speaker Phase in REW](https://www.youtube.com/watch?v=El-kwZ5_nnU).

> [!WARNING]
> **Führen Sie alle Messungen zügig am Stück durch und messen Sie den ersten Kanal am Ende noch einmal!**
> * **Die Temperatur im Innenraum verändert die Schallgeschwindigkeit:** Eine Erwärmung oder Abkühlung um wenige Grad verschiebt die Laufzeit des Schalls um Sekundenbruchteile. Für die präzise Phasenabstimmung von Mittel- und Hochtönern an den Trennfrequenzen ist dies absolut kritisch.
> * **Der Zeitfehler summiert sich mit der Anzahl der Messungen:** Ein Lautsprecher, der über einen Zeitraum von 18 Minuten 6 Mal hintereinander gemessen wurde, zeigte am Ende eine Zeitverschiebung von einem Sample (10 Mikrosekunden, was einer physikalischen Verschiebung des Mikrofons um ~3,6 mm entspricht). Diese Abweichung resultiert direkt aus den gestarteten Messungen, nicht aus der bloßen Wartezeit.
> * **Machen Sie am Ende immer eine Kontrollmessung des ersten Lautsprechers:** Der Eingangs-Check in Version 3.x vergleicht diese beiden Messungen auf Bruchteile eines Samples genau und weist die gesamte Messrunde ab, falls eine zu große Temperatur- oder Systemdrift erkannt wird.

---

### Regeln für die Benennung von Messungen in REW

Die Berechnungs-Tools suchen nach den passenden Kurven ausschließlich anhand der REW-Namen:

* `m-L_01 (sw)` — Kanal `m-L` (linker Mitteltöner), Messrunde `01`, Sweep-Messung.
* `m-L_01 (rta)` — RTA-Messung während der Fahrt (moving-mic average) für denselben Lautsprecher.
* `sw_01 (sw)`, `w-R_01 (sw)`, `tw-L_01 (sw)` — Subwoofer, rechter Tieftöner (Woofer), linker Hochtöner (Tweeter).
* `L_01 (rta)`, `ALL_01 (rta)` — Summenmessung der kompletten linken Seite bzw. des Gesamtsystems via RTA.
* `m-L p5_01 (sw)` — Messung des Lautsprechers an der speziellen räumlichen Position `p5` (alternativ auch `m-L_01 (sw) p5`).
* `m-L-ctl1_01 (sw)` und `m-L-ctl3_01 (sw)` — Zeitkontrolle: Die erste Messung startet die Serie, die zweite schließt sie ab (im Auto können diese auch als `m-L_01ctl` und `m-L_01rep` benannt werden).
* `m-L_final (sw)` — Verifizierungsmessung nach der endgültigen Fixierung der Parameter.

Das genaue Messverfahren und die Reihenfolge sind im Dokument [`references/phases/capture-session-sheet.md`](skills/autosound-tuning/references/phases/capture-session-sheet.md) beschrieben.

---

### Einmessung (Capture-Session): Warum nur Schutzfilter?

> [!IMPORTANT]
> **REW muss während der gesamten Arbeit geöffnet bleiben:** Der Skill liest die Kurven direkt über das API aus dem aktiven REW-Fenster, nicht aus exportierten Dateien auf der Festplatte.

Die Einmessung (Capture-Session) ist eine Messung jedes einzelnen Lautsprechers separat mit **ausschließlich aktiven Schutzfiltern** im DSP (ein Hochpassfilter / HPF auf einer absolut sicheren Frequenz für Mittel- und Hochtöner, damit diese beim lauten Sweep-Signal keinen Schaden nehmen). Trennfrequenzen, EQ-Bänder oder Laufzeitkorrekturen müssen vollständig deaktiviert sein — wir benötigen den unverfälschten physikalischen Frequenzgang des Chassis im Gehäuse bzw. in der Tür. Die Berechnungs-Skripte rechnen den Einfluss des Schutzfilters vor der Abstimmung automatisch heraus, was eine perfekte Phasenprognose garantiert.

*Wichtig:* Schalten Sie alle unbeteiligten Kanäle direkt über die DSP-Software stumm (Mute). Halten Sie die Lautstärke der Soundkarte und des Radios während der gesamten Messsession absolut konstant.

---

### Wozu dienen die Positionen p1…p9 und die Zeitkontrolle ctl?

* **Erkennung der Ursache von Einbrüchen und Peaks:** Echte Gehäuseresonanzen des Lautsprechers bleiben auf den Kurven ortsstabil, auch wenn das Mikrofon um einige Zentimeter verschoben wird (diese können per EQ korrigiert werden). Akustische Auslöschungen durch Reflexionen an Scheiben oder Verkleidungen verschieben sich bei Mikrofonbewegungen extrem stark auf der Frequenzachse — ein Anheben per EQ ist hier wirkungslos und schädlich, weshalb die KI diese Bereiche ignoriert.
* **Berechnung der Filtergüte (Q):** Die Verteilung der Messungen auf den Positionen `p1…p9` um den Kopf des Fahrers herum ermöglicht die präzise Berechnung der maximalen Filtergüte des Equalizers für jedes Band.
* **Kontrolle der Zeitdrift:** Die wiederholten Kontrollmessungen der Zentralposition `ctl` erlauben es dem System, die physikalische Zeitdrift der Soundkarte während der Messreihe mathematisch exakt zu kompensieren.

---

## Zielkurven (Target Curves)

### Wie erstelle und konfiguriere ich meine eigene Zielkurve?

Es gibt keine allgemeingültige „perfekte“ Zielkurve — sie ist Ihre persönliche Ausgangshypothese, die Sie nach der ersten technischen Abstimmung ganz nach Ihrem Gehör feinjustieren werden.

1. **Abstimmung durch die KI erstellen lassen:** Beschreiben Sie Ihre bevorzugten Musikrichtungen, Ihren bevorzugten Abhörpegel, Wünsche bezüglich bekannter Kurven (z.B.: *„nimm als Basis ResoNix Accurate, aber füge dem Subwoofer +2 dB Tiefbass hinzu und mache die Höhen etwas weicher“*) oder klangliche Probleme (*dröhnt, klingt spitz, kein Raumklang*). Das Skript generiert die Kurvendatei, legt sie im Projektordner ab und berechnet die individuellen Zielkurven für jedes Chassis.
2. **Manuell zeichnen:** Besuchen Sie die kostenlose Website **Nono Tuning Tool** ([nonotuningtool.com](https://nonotuningtool.com) → Bereich *Custom Target Curve*), zeichnen Sie Ihre Wunschkurve mit der Maus, exportieren Sie die `.txt`-Datei und legen Sie diese im Projektordner ab.
3. **Zielkurven vergleichen:** Nutzen Sie unseren interaktiven Online-Visualisierer:
   **[Zielkurven-Visualisierer online öffnen](https://ayukhno.github.io/autosound-tuning-skill/_curve-visualizer.html?lang=de)**. Hier können Sie Ihre Kurve direkt mit den Industriestandards SQ-Comp-Ref, ResoNix, Audiofrog, Harman, Jazzi oder Whitledge vergleichen. Ein Rechtsklick auf einen beliebigen Punkt der Kurve zeigt Ihnen eine Erklärung zur klanglichen Relevanz dieses Frequenzbereichs.

---

## Projekt auf der Festplatte und DSP

### Struktur des Projektordners und Datensicherung

Ein einziger Ordner auf Ihrer Festplatte enthält die vollständige Dokumentation und Konfiguration Ihres Systems:

| Datei / Verzeichnis | Inhalt | Zweck |
| :--- | :--- | :--- |
| **`project.json`** | Technische Basisdaten | Lautsprecherkanäle, DSP-Ausgänge, DSP-Profil, Mikrofon-Spezifikationen und aktive Zielkurve. |
| **`registry.json`** | Abstimmungsregister | Lückenlose, chronologische Historie aller Trennfrequenzen, Pegel, Polaritäten und EQ-Bänder. |
| **`process-state.json`** | Aktueller technischer Status | Information über die aktive Phase des Prozesses und die erfolgreich geprüften Messungen. |
| **`autosound_context.md`** | Fahrzeugkontext und Notizen | Einzigartiger Car-Audio-Wortschatz Ihres Fahrzeugs, Besonderheiten des Einbaus und Höreindrücke. |
| **`*.txt` / `*.json`** | Zielkurven und DSP-Exporte | Konfigurationsdateien für den Import in Ihren DSP und Zielkurven-Kurvendaten für REW. |

> [!IMPORTANT]
> **Sichern Sie diese kleinen Text- und JSON-Dateien sorgfältig.**
> Die extrem großen REW-Messdateien `.mdat` (16 bis 112 MB pro Datei) müssen Sie nicht zwingend sichern, da sie jederzeit neu gemessen werden können. Unser Installer bietet Ihnen die Option, ein kostenloses, privates GitHub-Repository für ein automatisches Backup Ihres Projektordners einzurichten.

---

### Kompatibilität mit Prozessoren und Filter-Import in den DSP

Der Skill berechnet die exakten Filterwerte und schreibt sie in eine Datei:

* **Audiotec Fischer (Helix / MATCH / BRAX):** Das System, auf dem diese Methode entwickelt und optimiert wurde. Es wird eine fertige Full EQ-Datei generiert, welche die offizielle DSP PC-Tool Software mit einem Klick für alle Kanäle gleichzeitig importieren kann.
* **Andere DSP-Prozessoren:** Es wird eine Standard-Exportdatei im REW Generic Format (bis zu 20 EQ-Bänder) oder eine erweiterte Frequenzweichen-Exportdatei erzeugt. Für die komfortable halbautomatische Eingabe der Werte per Tastatur-Makro nutzen Sie das kostenlose Tool: [REW-EQ-CopyPaste-Assistant](https://github.com/IvanBakhmutov/REW-EQ-CopyPaste-Assistant).
* **Kompatibilitätsprüfung:** Die Skripte vergleichen jeden berechneten Filter vor dem Export automatisch mit den echten technischen Grenzen Ihres DSP-Modells (verfügbare Bänder, Rechenrate, Filtertypen) und weisen auf Abweichungen hin.

---

### Arbeiten mit passiven Frequenzweichen (Hochtöner + MT auf einem Kanal)

Ein Lautsprecherpaar an einer passiven Weiche wird vom System als **ein einziger Kanal** behandelt: Es erhält eine gemeinsame Messung, eine gemeinsame Laufzeitkorrektur, einen gemeinsamen Pegel und einen gemeinsamen Satz an EQ-Bändern.

Alles andere funktioniert wie gewohnt, und der Summenfrequenzgang wird physikalisch korrekt abgebildet — inklusive eventueller Phasenprobleme im Bereich der Trennung der passiven Weiche. Was jedoch kein Programm der Welt von außen tun kann: Die Laufzeiten oder Phasen zwischen Hoch- und Mitteltöner **innerhalb** dieser passiven Gruppe anzugleichen. Dafür ist ein vollaktives System (Poka-Kanal-Ansteuerung) zwingend erforderlich.

---

### Wo finde ich die vollständige Liste der Funktionen der Methode?

Eine detaillierte Übersicht über alle 68 Fähigkeiten und Werkzeuge des Systems (mit den genauen Textbefehlen, Abbruchbedingungen, Entwicklungsstadium und wissenschaftlicher Begründung) finden Sie im interaktiven Capabilities-Board:
[`references/core/capabilities.md`](skills/autosound-tuning/references/core/capabilities.md).
