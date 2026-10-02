# FAQ — Häufig gestellte Fragen zur Car-Audio-Abstimmung

🇬🇧 [English](FAQ.md) · 🇩🇪 **Deutsch** · 🇵🇱 [Polski](FAQ.pl.md) · 🇺🇦 [Українська](FAQ.uk.md) · 📘 [TCC full guide (EN)](https://github.com/ayukhno/autosound-tcc/blob/main/docs/guide/REFERENCE.md) · <img src="assets/icons/roadmap.svg" width="14" height="14" valign="middle" alt="Roadmap" /> [Roadmap (EN)](ROADMAP.md)

Echte Fragen auf dem Weg von der Installation bis zum eingemessenen Auto. Die [README](README.de.md) ist die Kurzfassung; [Advanced Setup](ADVANCED.md) behandelt das Terminal, andere Installationswege, Versionen und das manuelle Einrichten des Reviewers.

---

## Inhaltsverzeichnis

- [Hier verwendete Begriffe](#hier-verwendete-begriffe)
- [Erste Schritte](#erste-schritte)
  - [Bevor du startest](#bevor-du-startest)
  - [Welcher Weg ist der richtige für den Einstieg?](#welcher-weg-ist-der-richtige-für-den-einstieg)
  - [Automatische Installation](#automatische-installation)
  - [Von der Installation ins Auto](#von-der-installation-ins-auto)
  - [Aktualisierung](#aktualisierung)
- [Sicherheit und KI-Modelle](#sicherheit-und-ki-modelle)
  - [Was weigert sich die Methode kategorisch zu tun?](#was-weigert-sich-die-methode-kategorisch-zu-tun)
  - [Welche KI-Modelle werden offiziell unterstützt?](#welche-ki-modelle-werden-offiziell-unterstützt)
- [Grafische Desktop-App Autosound TCC](#grafische-desktop-app-autosound-tcc)
  - [Was ist das und brauche ich es?](#was-ist-das-und-brauche-ich-es)
  - [Control mode: die Session im Terminal](#control-mode-die-session-im-terminal)
  - [Updates und Fehlermeldungen](#updates-und-fehlermeldungen)
- [Der KI-Reviewer](#der-ki-reviewer)
  - [Wenn der Reviewer nicht antwortet](#wenn-der-reviewer-nicht-antwortet)
- [Messungen durchführen](#messungen-durchführen)
  - [Phasenmessung: XLR-Mikrofone vs. USB (UMIK-1/2)](#phasenmessung-xlr-mikrofone-vs-usb-umik-12)
  - [Kann ich die Phase mit einem UMIK-1 messen?](#kann-ich-die-phase-mit-einem-umik-1-messen)
  - [Regeln für die Benennung von Messungen in REW](#regeln-für-die-benennung-von-messungen-in-rew)
  - [Capture Session: Warum nur Schutzfilter?](#capture-session-warum-nur-schutzfilter)
- [Zielkurven](#zielkurven)
  - [Wie erstelle und konfiguriere ich meine eigene Zielkurve?](#wie-erstelle-und-konfiguriere-ich-meine-eigene-zielkurve)
- [Projekt auf der Festplatte und DSP](#projekt-auf-der-festplatte-und-dsp)
  - [Kompatibilität mit Prozessoren und Filter-Import in den DSP](#kompatibilität-mit-prozessoren-und-filter-import-in-den-dsp)
  - [Arbeiten mit passiven Frequenzweichen (Hochtöner + Mitteltöner auf einem Kanal)](#arbeiten-mit-passiven-frequenzweichen-hochtöner--mitteltöner-auf-einem-kanal)
  - [Backup](#backup)

---

## Hier verwendete Begriffe

- **Die Methode (der Skill):** die Einmessanweisungen und Werkzeuge, denen Claude folgt. Sie läuft innerhalb von **Claude Code**, einem Claude-Programm auf deinem Computer – nicht im Chat in deinem Browser.
- **Die Session:** eine Unterhaltung mit Claude über dein Auto, im Chatfenster von TCC oder in einem Terminal.
- **TCC:** die Desktop-App (Autosound TCC), die dein Projekt anzeigt und die Session für dich ausführt.
- **Der Reviewer:** eine zweite KI (Gemini), die jeden Vorschlag prüft, bevor du ihn siehst. **Das Paket:** das Textbündel mit einem Vorschlag, das an den Reviewer geht.
- **API (in REW):** die Schnittstelle, über die die Methode deine Messungen aus REW einliest. Sie muss in REW aktiviert sein.
- **Sweep:** REWs Testton, der über einen einzelnen Lautsprecher abgespielt wird. **RTA (MMM):** eine Messung, die durchgeführt wird, während du das Mikrofon langsam um deinen Kopf bewegst.
- **Treiber:** ein Lautsprecher. **Fs:** die Resonanzfrequenz eines Treibers aus seinem Datenblatt.
- **HPF / LPF:** Hochpass- / Tiefpassfilter – die Filter im DSP, die tiefe bzw. hohe Frequenzen von einem Treiber fernhalten.
- **dBFS:** die Pegelanzeige in REW; 0 dBFS ist das Maximum.

---

## Erste Schritte

### Bevor du startest

- **Ein Laptop** – er kommt für die Messungen mit ins Auto.
- **Ein Messmikrofon:** ein **UMIK-1 reicht aus** (ein XLR-Mikrofon mit Audio-Interface ist präziser). Lade seine Kalibrierungsdatei anhand der Seriennummer von der Website des Herstellers herunter und lade sie in REW.
- **Ein Kabel vom Laptop zum DSP** – 3,5-mm-Klinke (AUX), USB-Audio oder optisch. Kein Bluetooth: Dessen Latenz schwankt zwischen den Sweeps.
- **Ein DSP** in deinem Auto.
- **REW beta**, installiert **vor** dem Installer (unter Windows legt der Installer dann eine Verknüpfung **REW (API on)** auf deinem Desktop an). Lade es unter [roomeqwizard.com/beta.html](https://www.roomeqwizard.com/beta.html) herunter; das Release-Build hat keine API.
- **Ein kostenpflichtiges Claude-Abonnement (Pro oder Max)** auf [claude.ai](https://claude.ai) – der Installer meldet dich damit an.
- **Ein Google-Konto** – für den Gemini-Reviewer; du meldest dich einmal im Browser an.
- **Die Fs deiner Treiber** aus ihren Datenblättern – für die Schutzfilter. Kein Datenblatt (Werkslautsprecher)? Sag es der KI; die Methode kann sie auch messen.

<a id="four-paths-of-usage"></a>

### Welcher Weg ist der richtige für den Einstieg?

- 🖥️ **Option 1 · Version 3.x im grafischen Fenster (Autosound TCC) – [Empfohlen]**  
  Der am stärksten automatisierte und visuelle Weg. Der Installer richtet Claude Code, die Methode samt ihren Python-Bibliotheken, die TCC-Desktop-App und den Gemini-Reviewer (agy) ein.
  - **Voraussetzungen:** macOS oder Windows, Claude Pro/Max, REW beta mit aktivierter API; TCC vergrößert den Download um etwa 700 MB.
  - **Vorteile:** Du siehst den Systembaum, Messkurven, den Schritt-für-Schritt-Plan und das Chatfenster in einer einzigen Oberfläche. Der Zustand wird automatisch auf der Festplatte gespeichert und Aktionen in der Versionsregistrierung werden nachverfolgt.
  - **Nachteile:** TCC ist jünger als die Methode.

Andere Wege – Version 3 rein im Terminal oder als Claude Code-Plugin, das Verbleiben auf der älteren 2.x-Reihe oder ein Web-Chat – findest du in [Advanced Setup](ADVANCED.md#other-ways-to-use-the-method).

> [!NOTE]
> Du bist nicht auf eine einzige Option festgelegt: Projekte der 3.x-Reihe öffnen sich nahtlos sowohl in einer Terminal-Session als auch in TCC.

### Automatische Installation
Du benötigst einen Laptop, ein Messmikrofon, einen DSP-Prozessor im Auto und ein **Claude Pro or Max**-Konto.

<details>
<summary><b>Anleitung für macOS</b></summary>

- Öffne das **Terminal** (drücke `Cmd + Space` → tippe `Terminal` ein → drücke `Enter`).
- Füge den folgenden Befehl ein und drücke `Enter`:
   ```bash
   curl -fsSL https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/v3.0.66/install.sh | bash
   ```
- Je nach System fragen andere Installer möglicherweise nach Berechtigungen; das ist normal. Warte 10–20 Minuten.

</details>

<details>
<summary><b>Anleitung für Windows</b></summary>

- Öffne die **Windows PowerShell** (drücke Start → tippe `powershell` ein → drücke `Enter`).
- Füge den folgenden Befehl ein und drücke `Enter`:
   ```powershell
   irm https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/v3.0.66/install.ps1 | iex
   ```
- Je nach System fragen andere Installer möglicherweise nach Berechtigungen; das ist normal. Das Skript erstellt eine Verknüpfung namens **REW (API on)** auf deinem Desktop.

</details>

### Von der Installation ins Auto

1. **Anmelden.** Der letzte Schritt des Installers öffnet zweimal deinen Browser: für Claude, dann für Google für den Reviewer (und GitHub, falls du danach gefragt hast). Einen Schritt übersprungen? Führe den Installer erneut aus – er bietet die Anmeldungen wieder an.
2. **REW starten** mit aktivierter API: unter Windows über die Verknüpfung **REW (API on)**; unter macOS in REW unter *Preferences → API* die Option **Start the API when REW starts** aktivieren und (einmalig) auf **Start server** klicken.
3. **TCC öffnen**, einen leeren Ordner für dein Auto anlegen (z. B. `MyCarTuning`) und diesen auswählen.
4. **Modelle auswählen** am unteren Rand des TCC-Fensters: **AI main** – Claude Opus, **Effort** – x-high (der Standardwert), **AI critic** – Gemini Pro (High), oder Gemini Flash (High), falls dir Pro nicht angeboten wird. Für das spätere Feintuning im Auto stelle **AI main** dort auf das leistungsfähigste Modell um (derzeit Claude Fable).
5. **Eingeben** im Chat von TCC: **"tune a new car from scratch"**. Die KI fragt nach deinem System und deinen Zielen und plant anschließend die Messungen.
6. **Im Auto** listet TCC jede Messung namentlich unter *In focus now* auf. Führe sie in REW genau unter diesem Namen durch und drücke dann auf **⬇**, um sie einzulesen. Wenn alle erfasst sind, drücke auf **Done**.
7. **Am Schreibtisch** entwirft die KI das Tuning; **zurück im Auto** trägst du die Werte in den DSP ein, überprüfst sie und stimmst nach Gehör fein ab.

### Aktualisierung

Aktualisiere innerhalb von TCC oder führe den Installationsbefehl erneut aus: Er installiert das neueste Release, prüft dessen Signatur und tastet deine Projektordner nicht an. Die Update-Schaltfläche in TCC selbst gibt den auszuführenden Befehl aus (TCC kann sich nicht selbst ersetzen, während es läuft). Weitere Optionen: [Advanced Setup](ADVANCED.md#the-installer).

---

## Sicherheit und KI-Modelle

### Was weigert sich die Methode kategorisch zu tun?
- **Parameter direkt in deinen DSP schreiben** – das Eintragen von Werten in die Prozessor-Software bleibt immer deine eigene Aufgabe.
- **Laufzeiten anhand von Auto-Delay-Tools oder Kreuzkorrelation berechnen** – akustische Delays werden manuell anhand des ersten Anstiegs der Impulsantwort ($t_0$) ermittelt. Automatische Laufzeitschätzungstools in REW sind streng verboten.
- **Frequenzen in akustischen Auslöschungen (Auslöschungszonen) anheben** – Auslöschungstäler entstehen durch Grenzflächenreflexionen, nicht durch den Lautsprecher selbst. Sie per EQ aufzufüllen ist zwecklos: Eine Anhebung belastet nur Verstärker und Lautsprecher und ändert an der Hörposition nichts. Die Methode begrenzt jede Anhebung auf maximal +6 dB, und ein Tal, das mehr erfordern würde, ist mit an Sicherheit grenzender Wahrscheinlichkeit eine Auslöschung. Einbrüche, die sicher korrigiert werden können, werden mittels *Excess phase*-Analyse in REW identifiziert.
- **Mit fehlerhaften Messungen fortfahren** – ein erkannter Timing-Drift oder fehlende Schutzfilter werden beanstandet, bevor fortgefahren wird.

---

### Welche KI-Modelle werden offiziell unterstützt?
- 🧠 **Hauptmodell (Generator):** **Claude Opus** (konfiguriert mit `xhigh`-Effort-Level oder höher; `max` für schwierige Schritte). Das Feintuning im Auto wird am besten mit dem leistungsfähigsten Modell durchgeführt (derzeit Claude Fable). Andere KIs können den Ablauf auch über `omp` steuern (wird nur auf Anfrage mit `--with-omp` installiert) – auf eigenes Risiko.
- 👁️ **KI-Reviewer (Critic):** **Gemini Pro (High)** über Google Antigravity (`agy`), oder **Gemini Flash (High)**, falls Pro (High) nicht angeboten wird. Mit einer Google Cloud-Anmeldung (ADC, das kostenlose Testguthaben) lautet das Reviewer-Modell **Gemini 3.8 Flash (High)** (`gemini-3.8-flash-high`).
- 🛠️ **Andere Reviewer:** Die Auswahlliste von TCC bietet für die Rolle des Reviewers auch Codex (und mit `--with-omp` weitere Modelle) an.
- 🧪 **Vom Autor getestet:** Gemini über Antigravity (`agy`) als Haupt-KI im Terminal, mit Codex als Reviewer und TCC im [Control mode](#control-mode-die-session-im-terminal).

*Stand: September 2026.* Modelle ändern sich schnell; betrachte die Namen hier daher als Beispiele: TCC und die Methode lesen die aktuelle Liste des jeweiligen Anbieters ein und bieten an, was heute verfügbar ist. Wenn ein hier genanntes Modell abgelehnt wird, wähle ein anderes aus dieser Liste.

> [!IMPORTANT]
> **Belasse Claudes Effort-Level bei `xhigh` oder höher (`max` für schwierige Schritte).**  
> Der Autor hat das Feintuning im Auto mit Claude Fable 5 durchgeführt.

---

## Grafische Desktop-App Autosound TCC

### Was ist das und brauche ich es?
[TCC](https://github.com/ayukhno/autosound-tcc) ermöglicht dir das Arbeiten in einem grafischen Fenster unter macOS und Windows. Du siehst den Lautsprecherbaum, REW-Graphen, den Schritt-für-Schritt-Plan und den Chat auf einem Bildschirm. TCC ist optional – du kannst ein Auto vollständig in der Session einmessen, da alle Projektdaten in Standarddateien auf der Festplatte gespeichert werden.

📘 [TCC in acht Bildschirmen (EN)](https://github.com/ayukhno/autosound-tcc/blob/main/docs/guide/QUICK-GUIDE.md) · [Das TCC-Fenster, Panel für Panel (EN)](https://github.com/ayukhno/autosound-tcc/blob/main/docs/guide/REFERENCE.md) · [Die House-Curve in TCC (EN)](https://github.com/ayukhno/autosound-tcc/blob/main/docs/guide/HOUSE-CURVE.md)

### Control mode: die Session im Terminal

Für eine Session, die im Terminal läuft – mit Claude Code oder mit einer anderen KI wie Gemini über `agy`. **Control mode** (in der Kopfzeile von TCC) verschiebt TCC auf die rechte Bildschirmhälfte und überlässt den Rest dem Terminal: Du tippst im Terminal, und TCC zeigt, was die Session schreibt (*Monitoring*), die Tabellen und deine Panels. **Done** und **Listening** erreichen die Session als Signale; **Active TCC** bringt das vollständige Fenster zurück.

📘 [Control mode im TCC-Leitfaden (EN)](https://github.com/ayukhno/autosound-tcc/blob/main/docs/guide/REFERENCE.md#control-mode)

### Updates und Fehlermeldungen
TCC sucht nach Updates für den Skill und TCC.

So meldest du Probleme:
- Auf GitHub: Melde UI-Fehler im [TCC GitHub repository](https://github.com/ayukhno/autosound-tcc/issues) und Einmessprobleme im [skill repository](https://github.com/ayukhno/autosound-tuning-skill/issues).
- Ohne GitHub-Konto: Bitte die Session darum ("report a bug") oder nutze das Meldefenster von TCC; die Meldungen gehen über ein Google Form an den Autor.

---

## Der KI-Reviewer

Der Zwei-KI-Prüfzyklus (Generator ↔ Gemini Critic) fängt Fehler ab, die einem einzelnen Modell entgehen. Er läuft über ein lokales Skript automatisch im Hintergrund ab – manuelles Kopieren ist nicht nötig.

Der automatische Kanal ist optional, das Review selbst jedoch nicht: Ist kein Kanal eingerichtet, fügst du das Review-Paket manuell in den Chat einer anderen KI ein. Das vollständige Überspringen des Reviews ist der mit Abstand größte Qualitätsverlust bei dieser Methode.

### Wenn der Reviewer nicht antwortet

> [!TIP]
> Wenn kein Kanal antwortet, verweigert der Reviewer den Vorgang (Exit-Code 4): Er listet die Gründe auf, speichert das Paket unter `process/reviews/` im Projekt und kopiert es in die Zwischenablage – füge es in den Chat einer beliebigen KI ein. Kopiere anschließend die Antwort des Reviewers zurück in den Chat der Session.

Den Reviewer manuell einrichten – das Modell, Google Clouds ADC, ein API-Key: [Advanced Setup](ADVANCED.md#the-reviewer-by-hand).

---

## Messungen durchführen

### Phasenmessung: XLR-Mikrofone vs. USB (UMIK-1/2)
- **XLR-Mikrofone (Behringer ECM8000, Beyerdynamic MM1 usw.):** Angeschlossen über ein externes Audio-Interface mit einem Hardware-Loopback-Kabel (ein Ausgang wird direkt mit einem freien Eingang verbunden). Dies liefert eine exakte Hardware-Timing-Referenz.
- **USB-Mikrofone (UMIK-1 / UMIK-2):** Direkt über USB angeschlossen. Ihnen fehlt ein physischer Loopback und sie benötigen eine akustische Timing-Referenz.
- **Audioverbindung:** Verwende ein physisches Kabel (3,5-mm-Klinke/AUX, direktes USB-Audio oder optisch). Vermeide Bluetooth für Sweeps: Die kabellose Latenz schwankt zwischen den Sweeps und beeinträchtigt die Timing-Genauigkeit.

---

### Kann ich die Phase mit einem UMIK-1 messen?
**Ja.** Verwende die **Acoustic Timing Reference** in REW. Vor dem Abspielen des Mess-Sweeps spielt REW einen kurzen Chirp über den Lautsprecher ab, der als Timing-Referenz ausgewählt wurde, um den zeitlichen Nullpunkt festzulegen.

> [!WARNING]
> **Führe Messungen mit dem Mikrofon auf einem Stativ durch und wiederhole den Kontroll-Sweep am Ende!**
> - **Drift der Innenraumtemperatur:** Die Schallgeschwindigkeit ändert sich mit der Temperatur im Fahrzeuginnenraum und verschiebt die Laufzeiten.
> - **Positionierung des Stativs:** Platziere das Mikrofon auf Ohrhöhe am Referenzsitzplatz. Bewege das Stativ nicht, bis der Sweep-Block abgeschlossen ist (~25 Minuten).
> - **Kontroll-Sweep:** Das Messen des Anfangskanals (`ctl1`) und dessen Wiederholung am Ende (`ctl3`) prüft auf einen Timing-Drift, bevor die Runde abgeschlossen wird.

Für eine detaillierte REW-Konfiguration für USB-Mikrofone siehe die Videoanleitung: [Measuring Speaker Phase in REW](https://www.youtube.com/watch?v=El-kwZ5_nnU).

---

### Regeln für die Benennung von Messungen in REW

Mit TCC ist jede Messung, die ein Schritt benötigt, namentlich unter *In focus now* aufgeführt: Führe sie in REW exakt unter diesem Namen durch und drücke dann auf **⬇**. Wenn du in einem Terminal arbeitest, benennst du sie selbst. In beiden Fällen findet der Skill Messungen ausschließlich anhand ihrer Namen in REW:

- `m-L_1 (sw)` — Kanal `m-L` (Mitteltöner links), Messreihe `1`, Sweep-Messung.
- `m-L_1 (rta)` — Moving-Mic-RTA-Messung für denselben Lautsprecher.
- `tw-L_1 (sw)`, `w-R_1 (sw)`, `sw_1 (sw)` — Hochtöner links, Tieftöner rechts (TMT), Subwoofer.
- `L_1 (rta)`, `ALL_1 (rta)` — Summen-RTA der gesamten linken Seite bzw. des gesamten Systems.
- `m-L p5_1 (sw)` — der Lautsprecher am räumlichen Messpunkt `p5` (wird auch als `m-L_1 (sw) p5` gelesen).
- `m-L-ctl1_1 (sw)` und `m-L-ctl3_1 (sw)` — Timing-Kontrolle: Die erste öffnet die Lautsprecherreihe, die zweite schließt sie ab; es gibt kein `ctl2` (im Auto als `m-L_1ctl` und `m-L_1rep` eingegeben, bedeuten sie dasselbe).
- `m-L_final (sw)` — Verifikationsmessung nach dem Speichern der endgültigen Parameter.
- `w-L (imp)` — Impedanzmessung eines Treibers (trägt keine Seriennummer).
- Text nach der Methode macht daraus eine weitere Messung derselben Reihe: `r-L_17 (sw) noXO` ist nicht `r-L_17 (sw)`.

Titel werden exakt so abgeglichen, wie sie eingegeben wurden. Wenn ein Titel nicht dem entspricht, was der Schritt erwartet, fragt die Session nach, anstatt zu raten.

Der vollständige Messablauf ist in [`references/phases/capture-session-sheet.md`](skills/autosound-tuning/references/phases/capture-session-sheet.md) beschrieben.

---

### Capture Session: Warum nur Schutzfilter?
> [!IMPORTANT]
> **REW muss während des gesamten Prozesses geöffnet bleiben:** Der Skill liest Kurven über die API direkt aus dem aktiven REW-Fenster aus, nicht aus auf die Festplatte exportierten Dateien.
>
> **Schutzfilter BLEIBEN während der Erfassung AKTIV:** Hochpassfilter (HPF) für empfindliche Hoch- und Mitteltöner müssen im DSP aktiv bleiben, um sie bei den Mess-Sweeps zu schützen.

- **Schutzfilter-Regel:** Der schützende HPF muss **$\ge 1.1 \times Fs$ (empfohlen bis zu $1.5 \times Fs$) mit einer Flankensteilheit von $\ge 24$ dB/Okt.** betragen (LR4 oder BW4). Ist $Fs$ unbekannt, schlage den Wert im Datenblatt des Herstellers nach und gib ihn im Projekt an.
- **Sonstige DSP-Signalverarbeitung deaktiviert:** Betriebs-EQs (leer), Delays (auf 0 gesetzt) und Polaritäten (normal) müssen neutral sein. Miss jeden Treiber einzeln. Erfasse jeden Schutzfilter während der Erfassungsrunde (TCC fragt danach; im Terminal erfasst es die Session): Die Methode rechnet ihn wieder heraus, bevor die gemeinsame Phase analysiert wird. Ein als `OFF` erfasster Kanal wird so übernommen, wie er ist.
- **Pegel in dBFS:** Stelle die Sweep-Lautstärke so ein, dass die Spitze des lautesten Treibers (Subwoofer) bei $-5\dots-10$ dBFS liegt und der leiseste Treiber deutlich über dem Grundrauschen des Innenraums liegt. Schalte alle inaktiven Kanäle in deiner DSP-Software stumm und belasse die Lautstärke von Soundkarte und Head-Unit während der gesamten Session unverändert.
- **Klang des Tiefmitteltöner-Sweeps:** Ein Tiefmitteltöner (Midbass), der ohne LPF gemessen wird, erzeugt bei hohen Frequenzen während des Sweeps ein raues, kratziges Geräusch. Das sind normale Membranaufbrüche am oberen Ende seines Frequenzbereichs; der Treiber nimmt dabei keinen Schaden.

---

## Zielkurven

### Wie erstelle und konfiguriere ich meine eigene Zielkurve?
Eine Zielkurve gibt dir eine klangliche Ausgangsbasis. Nach dem Basis-Tuning verfeinerst du sie nach Gehör.

- **Aus etablierten Kurven auswählen:** Wähle aus kalibrierten Zielkurven – SQ-Comp-Ref (die Wettbewerbskurve der Methode), ResoNix, Audiofrog, Harman, Jazzi und Whitledge – passend zu deinen Hörgewohnheiten. Das Skript `target_bands.py` berechnet anhand deiner gewählten Kurve und Trennfrequenzen die Zielfrequenzgänge pro Treiber.
- **Manuell zeichnen:** Nutze das kostenlose [Nono Tuning Tool](https://nonotuningtool.com) (Bereich *Custom Target Curve*), um einen Frequenzgang zu gestalten und eine `.txt`-Zieldatei zu exportieren.
- **Online vergleichen:** Nutze den Target Curve Visualizer, um Kurven zu vergleichen (SQ-Comp-Ref, deine eigenen aus REW und Standardkurven aus dem Nono Tuning Tool):  
  👉 **[Target Curve Visualizer online öffnen](https://ayukhno.github.io/autosound-tuning-skill/_curve-visualizer.html?lang=de)**. Ein Rechtsklick auf einen beliebigen Punkt im Diagramm erklärt, wie sich dieser Frequenzbereich auf den Klang auswirkt.

📘 [Die House-Curve in TCC (EN)](https://github.com/ayukhno/autosound-tcc/blob/main/docs/guide/HOUSE-CURVE.md)

---

## Projekt auf der Festplatte und DSP

### Kompatibilität mit Prozessoren und Filter-Import in den DSP
> [!IMPORTANT]
> Die Methode berechnet die Filter. Delays und Pegel (Gains) werden **manuell** eingetragen, ebenso Trennfrequenzen (Crossover), sofern kein Paste-Tool diese aus dem unten genannten Extended-Export übernimmt. Ein Datei-Import überträgt ausschließlich **EQs**.

- **Audiotec Fischer (Helix / MATCH / BRAX):** Erzeugt eine importfertige Full-EQ-Datei, die das DSP PC-Tool für alle Kanäle in einem Schritt lädt.
- **Andere DSP-Prozessoren:** Exportiert REW Generic-EQ-Dateien (20 Slots) oder Generic/Extended mit integrierten Trennfrequenzen. Für eine schnelle Parametereingabe in andere DSP-Software nutze den [REW-EQ-CopyPaste-Assistant](https://github.com/IvanBakhmutov/REW-EQ-CopyPaste-Assistant).
- **Kompatibilitätsprüfung:** Vor dem Export prüft die Methode jeden berechneten Filter gegen die Limits deines DSP-Modells (verfügbare Bänder, Sampling-Rate, Filtertypen) und weist auf Abweichungen hin.
- **OEM-Head-Units:** Umgehe Werksradios über einen sauberen digitalen oder analogen Eingang (DAP, USB, optisch) in den DSP, anstatt zu versuchen, werksseitige Klang- und Loudness-Verbiegungen mühsam zu entzerren.

---

### Arbeiten mit passiven Frequenzweichen (Hochtöner + Mitteltöner auf einem Kanal)
Ein Treiberpaar, das sich eine passive Frequenzweiche teilt, wird wie **ein einzelner gemeinsamer DSP-Kanal** behandelt: Es erhält eine Messung, ein gemeinsames Delay, einen gemeinsamen Pegel und einen gemeinsamen Satz EQ-Filter.

Alles andere funktioniert wie gewohnt. Keine Software kann Zeit oder Phase zwischen Hochtöner und Mitteltöner innerhalb dieser passiven Gruppe abgleichen: Dafür benötigt jeder Treiber seinen eigenen DSP-Kanal.

---

### Backup

Große REW-`.mdat`-Dateien verbleiben auf deinem Computer: Behalte sie. Für ein privates Backup des Projektordners auf GitHub installiere mit `--github` (`-GitHub` unter Windows) und bitte die Session darum, das Projekt zu sichern – ohne dein Einverständnis wird nichts erstellt. Was sich im Ordner befindet: [Advanced Setup](ADVANCED.md#project-folder-structure-and-backup).
