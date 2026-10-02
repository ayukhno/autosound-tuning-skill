# KI-Assistent für Car-HiFi (Autosound Tuning Skill)

🇬🇧 [English](README.md) · 🇩🇪 **Deutsch** · 🇵🇱 [Polski](README.pl.md) · 🇺🇦 [Українська](README.uk.md) · ❓ [FAQ](FAQ.de.md) · 📘 [TCC guide (EN)](https://github.com/ayukhno/autosound-tcc/blob/main/docs/guide/QUICK-GUIDE.md) · <img src="assets/icons/roadmap.svg" width="14" height="14" valign="middle" alt="Roadmap" /> [Roadmap (EN)](ROADMAP.md)

**Einfach gesagt:** Das ist dein persönlicher KI-Car-Audio-Tuning-Master. Du willst eine perfekte Bühne und eine ausgewogene tonale Balance, aber Diagramme, Phasen und Laufzeiten wirken zu kompliziert? Dieser Assistent übernimmt den schwierigen Teil. Er liest deine Mikrofonmessungen ein und führt dich Schritt für Schritt zum perfekten Klang.

- **Du misst — die KI rechnet:** Sie arbeitet mit der REW-Software zusammen, analysiert die Akustik deines Innenraums und schlägt dir exakte Einstellungen für EQ, Frequenzweichen und Laufzeitkorrektur vor.
- **Minimale Zeit im Auto:** Die Hauptberechnungen finden zu Hause am Schreibtisch statt. Du machst im Auto nur die ersten Messungen und kehrst dann mit einsatzbereiten Werten zurück, um dir das Ergebnis anzuhören und Schritt für Schritt ins Detail-Tuning einzusteigen.
- **Schreibt nichts in deinen DSP — du lädst es selbst:** Der Assistent greift niemals direkt auf deinen Prozessor zu. Er zeigt dir Zahlen und Diagramme und bereitet den EQ für den Import vor: Bei einem Helix wandert die gesamte Full-EQ-Bank über das DSP PC-Tool in einem Schritt hinein, und bei Prozessoren ohne Datei-Import fügt der kostenlose [REW-EQ-CopyPaste-Assistant](https://github.com/IvanBakhmutov/REW-EQ-CopyPaste-Assistant) die Werte ein. Du entscheidest, was übernommen wird.
- **Kein gewöhnlicher Chat:** Der Projektstatus und alle Einstellungen werden in Dateien auf deiner Festplatte gespeichert, sodass zwischen den Sitzungen nichts „vergessen“ wird und du jederzeit einen Schritt zurückgehen kannst.
- **Zwei KIs, und dein Gehör entscheidet:** Eine KI schlägt Einstellungen vor, eine zweite prüft sie. Die Prüfung ist fester Bestandteil der Methode; lediglich die automatische Verbindung zwischen beiden ist optional — ohne sie fügst du das Paket von Hand in einen beliebigen KI-Chat ein. Die letzte Instanz ist dein Gehör: Du hörst probe und entscheidest, statt nur abzunicken.
- **Arbeitet mit Fakten:** Die KI rät keine Einstellungen. Wenn Messungen fehlerhaft sind oder nicht ausreichen, schlägt eine Prüfung an und bittet dich, die Messung zu wiederholen — oder wissentlich fortzufahren und das Fehlerrisiko in Kauf zu nehmen.

## Im Wettbewerb erprobt

Mit Version 2.x dieser Methode holte das Auto des Autors im Jahr 2026 vier Auszeichnungen bei **EMMA**- und **AYA**-Meisterschaften (der erste Pokal wurde geholt, bevor alles in einen Skill gebündelt wurde, mithilfe von KI-Hinweisen aus denselben Diagrammen – was dieses Projekt überhaupt erst inspirierte). Version 3.1 mit grafischer Benutzeroberfläche ist das aktuelle Release. Die fünfte Auszeichnung — 3. Platz beim **German EMMA Final 2026** — kam mit 3.x, indem das bestehende Tuning verfeinert statt von Grund auf neu eingemessen wurde. Die 2.8.x-Reihe hinter den ersten vier ist weiterhin verfügbar: siehe FAQ, [Pfad 3](FAQ.de.md#vier-optionen-zur-nutzung).

<p align="left">
  <img src="assets/awards/aya-may26-einsteiger5000.jpg" height="120" alt="AYA May 2026, Einsteiger 5000, 1st place">
  &nbsp;&nbsp;&nbsp;
  <img src="assets/awards/aya-jul26-amateur5000.jpg" height="120" alt="AYA July 2026, Amateur 5000, 1st place">
  &nbsp;&nbsp;&nbsp;
  <img src="assets/awards/aya-aug26-amateur5000.jpg" height="120" alt="AYA August 2026, Amateur 5000, 2nd place">
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
  <img src="assets/awards/emma-aug26-entry-unlimited.jpg" height="120" alt="EMMA Sound Off 2026, SQ Entry Unlimited, 3rd place">
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
  <img src="assets/awards/emma-sep26-final-entry-unlimited.jpg" height="120" alt="German EMMA Final 2026, Frankfurt, SQ Entry Unlimited, 3rd place">
</p>

*Auch deine Anlage kann wie ein Champion klingen!*

> [!CAUTION]
> Die KI ist ein Assistent, aber die Verantwortung liegt bei dir. Ein Tippfehler bei einer manuell eingegebenen Zahl kann einen Hochtöner zerstören. Prüfe Trennfrequenzen immer, bevor du die Stummschaltung aufhebst, und beginne grundsätzlich mit geringer Lautstärke.

## Was du für den Start brauchst

Die App lässt sich mit einem einzigen Befehl installieren. An Hardware und Abonnements benötigst du Folgendes:

1. **Messmikrofon** (z. B. UMIK-1 oder vorzugsweise ein XLR-Mikrofon mit Audio-Interface und physischem Loopback).
2. **Prozessor (DSP)** in deinem Auto.
3. **REW-Software (Room EQ Wizard)** — die **Beta-Version** ist erforderlich (der aktuelle Release-Build, V5.31.3 vom Juli 2024, hat keinerlei API — prüfe Help → About, bevor du startest). Lade dir den Beta-Build von [roomeqwizard.com/beta.html](https://www.roomeqwizard.com/beta.html) herunter. Gehe nach dem Starten von REW auf *Preferences → API*, aktiviere **Start the API when REW starts** und klicke auf **Start server**.
4. **Kostenpflichtiges Claude-Abonnement (Pro oder Max)** — Claude übernimmt die Hauptarbeit; dies ist der unterstützte Weg und die App ist dafür ausgelegt. Andere KIs können den Durchlauf über `omp` steuern (wird nur auf Anfrage installiert) — auf eigenes Risiko.

*(Empfohlen: ein kostenloses GitHub-Konto, um deinen Tuning-Verlauf in einem privaten Repository zu sichern.)*

## Installation und Start

**Standardmäßig richtet der Installer Folgendes ein:** Claude Code, die Tuning-Methode samt den von ihren Tools benötigten Python-Bibliotheken, die Desktop-App **Autosound TCC** und den Gemini-Reviewer (`agy`). Das dauert 10–20 Minuten. Je nach System fragen andere Installer währenddessen eventuell nach Berechtigungen — das ist normal (Details in den FAQ).

**macOS** — öffne das Terminal (⌘-Leertaste, tippe „terminal“, Enter) und füge Folgendes ein:
```sh
curl -fsSL https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/v3.0.66/install.sh | bash
```

**Windows** — öffne PowerShell (Start, tippe „powershell“, Enter) und füge Folgendes ein:
```powershell
irm https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/v3.0.66/install.ps1 | iex
```
*(Die Version in der Adresse pinnt nur den Installer selbst; es wird immer das neueste Release installiert.)*

**Optionen:**

| Funktion | macOS | Windows |
|---|---|---|
| andere Modelle als Claude, über `omp` | `--with-omp` | `-WithOmp` |
| das Projekt-Backup auf GitHub (ein privates Repository; die Keys bleiben außen vor) | `--github` | `-GitHub` |
| die Methode ohne die App (nur Terminal) | `--terminal` | `-Terminal` |
| den Plan anzeigen und nichts ändern | `--dry-run` | `-DryRun` |

Mit Optionen — zum Beispiel `omp` und dem GitHub-Backup — unter macOS:
```sh
curl -fsSL https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/v3.0.66/install.sh | bash -s -- --with-omp --github
```
und unter Windows als zwei Zeilen:
```powershell
$i = irm https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/v3.0.66/install.ps1
& ([scriptblock]::Create($i)) -WithOmp -GitHub
```

**Bereits in Claude Code?** Die Methode lässt sich auch als Plugin installieren:
```sh
claude plugin marketplace add ayukhno/autosound-tuning-skill
claude plugin install autosound-tuning
```
Ein Plugin bringt nur die Dateien der Methode mit: Tippe in der ersten Sitzung **`/autosound-tuning:setup`** ein — es prüft das Plugin anhand seines signierten Releases und installiert den Rest. Die TCC-Desktop-App ist so nicht enthalten; füge sie mit `/autosound-tuning:setup app` (oder `/autosound-tuning:install-tcc`) hinzu.

**Nach der Installation:**
1. Der letzte Schritt des Installers meldet dich an: bei Claude, dann beim Gemini-Reviewer (`agy`) und bei GitHub, falls du es ausgewählt hast.
2. Öffne die **Autosound TCC**-App von deinem Desktop.
3. Erstelle einen leeren Ordner für dein Auto (z. B. `MyCarTuning`) und wähle ihn in der App aus, mit **AI main: Claude Opus (SDK)** und **AI critic: Gemini Pro (High)** — oder **Gemini Flash (High)**, falls dir Pro nicht angeboten wird.
4. **Wichtig:** Belasse den Effort von Claude Opus auf `xhigh` oder höher (der Standardwert; `max` für schwierige Schritte).
5. Tippe im App-Chat: **"tune a new car from scratch"**. Die KI beginnt mit Fragen und nimmt dich an die Hand.

▶ **Zielkurven:** Die Methode bringt ihre eigene Kurve für Wettbewerbe mit: **SQ-Comp-Ref**. Der **[Target Curve Visualizer](https://ayukhno.github.io/autosound-tuning-skill/_curve-visualizer.html?lang=de)** analysiert und vergleicht Kurven nebeneinander — SQ-Comp-Ref, deine eigenen aus REW oder die Standardkurven aus dem [Nono Tuning Tool](https://nonotuningtool.com) — und speichert diejenige, die du auswählst. Wie man eine auswählt: der [Leitfaden für Zielkurven](skills/autosound-tuning/references/patterns/target-curves/target_curves_guide.md).

## So sieht der Tuning-Prozess aus

1. **Vorbereitung zu Hause:** Du informierst die KI über deine Anlage (welche Lautsprecher, welcher Prozessor).
2. **Messungen im Auto (einmalig):** Mit Schutzfiltern auf dem DSP misst du jedes Chassis einzeln in einer einzigen Sitzung ein; die TCC-App leitet dich Schritt für Schritt hindurch. Das Tuning wird anschließend am Schreibtisch entworfen.
3. **Mathematik am Schreibtisch:** Du sitzt an deinem Computer (ohne das Auto in der Nähe). Die KI analysiert die Messungen, bindet den Subwoofer an den Tiefmitteltöner an, gleicht die Bühne an und berechnet den EQ. Am Schreibtisch werden die Ergebnisse nur prognostiziert; im Auto werden sie anschließend überprüft.
4. **Zurück im Auto — überprüfen, korrigieren, feintunen:** Trage die Werte in den DSP ein, prüfe sie mit ein paar Kontrollmessungen sowie nach Gehör und korrigiere, was noch nicht passt. Danach folgt das Feintuning, das man am besten direkt im Auto mit dem fähigsten Modell macht (derzeit Claude Fable): Du sagst der KI, was du hörst, und je besser es klingen soll, desto mehr Runden sind nötig. Das Arbeiten am Schreibtisch ist ebenfalls möglich — das Modell und die Methode passen sich an.

## Feedback, Support und Datenschutz

**Datenschutz:** Der Skill lernt aus jedem Tuning und sendet nur mit deiner ausdrücklichen Einwilligung generalisierte Erkenntnisse an eine gemeinsame Wissensdatenbank. Er sammelt niemals personenbezogene Daten und überträgt niemals vollständige Messungen.

**Probleme und Fehler:**
- Wenn etwas mit der Tuning-Logik selbst nicht stimmt: [Öffne ein Issue auf GitHub (autosound-tuning-skill)](https://github.com/ayukhno/autosound-tuning-skill/issues/new/choose).
- Wenn das Problem die Benutzeroberfläche (Autosound TCC) betrifft — schreibe an das [TCC-App-Repository](https://github.com/ayukhno/autosound-tcc/issues/new/choose).
- Kein GitHub-Account? Frage in der Session ("report a bug") oder nutze das Meldefenster von TCC: Dein Bericht geht stattdessen über ein Google Form an den Autor — reiner Text.

Dieses Tool ist **völlig kostenlos**. Der Code und die Skripte sind unter **MIT** lizenziert, die Dokumentation und die Methode selbst unter **CC BY-SA 4.0**.

**Credits:** Ein Teil der DSP-Mathematik wurde aus [Resonalyze](https://github.com/DIMOSUS/Resonalyze) von DIMOSUS (MIT) portiert — [`LICENSES/NOTICE.md`](LICENSES/NOTICE.md).

Wenn es dir wochenlange Tuning-Zeit erspart hat und du dem Autor danken möchtest, kannst du das hier tun:
💜 **[GitHub Sponsors](https://github.com/sponsors/ayukhno)** · ☕ **[Monobank Jar (UA)](https://send.monobank.ua/jar/8wThVcodjm)**

**Guten Klang!**
