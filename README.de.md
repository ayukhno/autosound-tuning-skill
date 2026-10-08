# KI-Assistent für Car-HiFi (Autosound Tuning Skill)

🇬🇧 [English](README.md) · 🇩🇪 **Deutsch** · 🇵🇱 [Polski](README.pl.md) · 🇺🇦 [Українська](README.uk.md) · ❓ [FAQ](FAQ.de.md) · 📘 [TCC quick guide (EN)](https://github.com/ayukhno/autosound-tcc/blob/main/docs/guide/QUICK-GUIDE.md)

**Einfach gesagt:** Das ist dein persönlicher KI-Car-Audio-Tuning-Meister. Du willst eine perfekte Bühne und eine saubere tonale Balance, aber Diagramme, Phasen und Laufzeiten wirken zu kompliziert? Dieser Assistent übernimmt die schwierigen Schritte. Er liest deine Mikrofonmessungen ein und führt dich Schritt für Schritt zum perfekten Klang.

- **Du misst – die KI rechnet:** Sie arbeitet mit der REW-Software zusammen, analysiert die Akustik deines Innenraums und schlägt exakte Einstellungen für EQ, Trennfrequenzen und Laufzeitkorrektur vor.
- **Minimale Zeit im Auto:** Die Hauptberechnungen finden zu Hause am Schreibtisch statt. Du machst im Auto nur die ersten Messungen und kehrst dann mit fertigen Werten zurück, um das Ergebnis probezuhören und Schritt für Schritt tiefer ins Tuning einzusteigen.
- **Schreibt nichts in deinen DSP – du lädst es:** Der Assistent greift niemals direkt auf deinen Prozessor zu. Er zeigt dir Werte und Diagramme und bereitet den EQ für den Import vor: Bei einem Helix wird die komplette Full-EQ-Bank über das DSP PC-Tool in einem Schritt importiert, und bei Prozessoren ohne Datei-Import fügt der kostenlose [REW-EQ-CopyPaste-Assistant](https://github.com/IvanBakhmutov/REW-EQ-CopyPaste-Assistant) sie ein. Du entscheidest, was eingespielt wird.
- **Kein gewöhnlicher Chat:** Der Projektstatus und alle Einstellungen werden in Dateien auf deiner Festplatte gespeichert, sodass zwischen den Sitzungen nichts „vergessen“ wird und du jederzeit einen Schritt zurückgehen kannst.
- **Zwei KIs, und dein Gehör entscheidet:** Eine KI schlägt Einstellungen vor, eine zweite prüft sie. Die Prüfung ist Teil der Methode; nur die automatische Verknüpfung zwischen ihnen ist optional – ohne sie fügst du das Paket manuell in einen beliebigen KI-Chat ein. Die letzte Instanz ist dein Gehör: Du hörst probe und entscheidest, statt nur abzunicken.
- **Arbeitet mit Fakten:** Die KI rät keine Einstellungen. Wenn die Messungen fehlerhaft oder unzureichend sind, fängt eine Prüfung das ab und fordert dich auf, die Messung zu wiederholen – oder wissentlich fortzufahren und das Fehlerrisiko in Kauf zu nehmen.

## Im Wettbewerb bewährt

Mit Version 2.x dieser Methode holte das Auto des Autors 2026 vier Auszeichnungen bei Meisterschaften von **EMMA** und **AYA** (die erste Auszeichnung wurde gewonnen, bevor sie in einen Skill gebündelt wurde, mithilfe von KI-Hinweisen aus denselben Diagrammen – was dieses Projekt überhaupt erst inspirierte). Version 3.1 mit grafischer Benutzeroberfläche ist das aktuelle Release. Die fünfte Auszeichnung – 3. Platz beim **German EMMA Final 2026** – kam mit 3.x hinzu, indem das bestehende Setup verfeinert wurde, statt bei null zu beginnen. Die 2.8.x-Linie hinter den ersten vieren ist weiterhin verfügbar: siehe die FAQ, [Pfad 3](FAQ.de.md#four-paths-of-usage).

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
> Die KI ist ein Assistent, aber die Verantwortung liegt bei dir. Ein Tippfehler bei einer manuell eingegebenen Zahl kann einen Hochtöner zerstören. Prüfe Trennfrequenzen immer, bevor du die Stummschaltung aufhebst, und starte stets bei geringer Lautstärke.

## Was du für den Start brauchst

Die App lässt sich mit einem einzigen Befehl installieren. An Hardware und Abonnements benötigst du Folgendes:

1. **Messmikrofon** (z. B. UMIK-1, oder vorzugsweise ein XLR-Mikrofon mit Audio-Interface und physischem Loopback).
2. **Prozessor (DSP)** in deinem Auto.
3. **REW-Software (Room EQ Wizard)** — die **Beta-Version** ist erforderlich (der aktuelle Release-Build, V5.31.3 vom Juli 2024, bietet keinerlei API – prüfe vorab Help → About). Lade den Beta-Build von [roomeqwizard.com/beta.html](https://www.roomeqwizard.com/beta.html) herunter. Gehe nach dem Starten von REW zu *Preferences → API*, aktiviere **Start the API when REW starts** und klicke auf **Start server**.
4. **Kostenpflichtiges Claude-Abonnement (Pro oder Max)** — Claude übernimmt die Hauptarbeit; dies ist der unterstützte Weg, und die App ist dafür ausgelegt. Andere KIs können den Durchlauf über `omp` steuern (wird nur installiert, wenn du danach fragst) – auf eigenes Risiko.

*(Empfohlen: ein kostenloses GitHub-Konto, um deinen Tuning-Verlauf in einem privaten Repository zu sichern.)*

## Installation und Start

**Standardmäßig richtet der Installer Folgendes ein:** Claude Code, die Tuning-Methode samt den für ihre Werkzeuge benötigten Python-Bibliotheken, die Desktop-App **Autosound TCC** und den Gemini-Reviewer (`agy`). Das dauert beim ersten Mal auf einem Mac ohne die Entwicklertools 10–20 Minuten, ansonsten wenige Minuten. Je nach System bitten eventuell weitere Installationsprogramme zwischendurch um Erlaubnis – das ist normal (Details in der FAQ).

**macOS** — öffne das Terminal (⌘-Leertaste, „terminal“ eintippen, Enter) und füge Folgendes ein:
```sh
curl -fsSL https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/v3.1.2/install.sh | bash
```

**Windows** — öffne die PowerShell (Start, „powershell“ eintippen, Enter) und füge Folgendes ein:
```powershell
irm https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/v3.1.2/install.ps1 | iex
```
*(Die Version in der Adresse fixiert den Installer selbst; er installiert immer das neueste Release.)*

**Optionen:**

| Funktion | macOS | Windows |
|---|---|---|
| andere Modelle als Claude über `omp` | `--with-omp` | `-WithOmp` |
| Projekt-Backup auf GitHub (ein privates Repository; die Keys bleiben außen vor) | `--github` | `-GitHub` |
| die Methode ohne die App (nur Terminal) | `--terminal` | `-Terminal` |
| den Plan anzeigen und nichts ändern | `--dry-run` | `-DryRun` |

Mit Optionen – zum Beispiel `omp` und dem GitHub-Backup – unter macOS:
```sh
curl -fsSL https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/v3.1.2/install.sh | bash -s -- --with-omp --github
```
und unter Windows als zwei Zeilen:
```powershell
$i = irm https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/v3.1.2/install.ps1
& ([scriptblock]::Create($i)) -WithOmp -GitHub
```
**Wie es endete**, steht im Exit-Code des Installers: `0` bereit · `1` gestoppt — die Methode wurde nicht installiert oder geändert · `2` eine falsche Option für `install.sh` oder ein ungültiges `-Channel` oder `-Plugin` für `install.ps1` (PowerShell selbst lehnt eine Option, die sie nicht kennt, mit `1` ab) · `3` installiert, aber nicht bereit, seine letzten Zeilen nennen, was fehlt und was zu tun ist.

**Bereits in Claude Code unterwegs?** Die Methode lässt sich auch als Plugin installieren:
```sh
claude plugin marketplace add ayukhno/autosound-tuning-skill
claude plugin install autosound-tuning
```
Ein Plugin bringt nur die Dateien der Methode mit: Gib in der ersten Sitzung **`/autosound-tuning:setup`** ein – der Befehl gleicht das Plugin mit seinem signierten Release ab und installiert den Rest. Die TCC-Desktop-App ist auf diesem Weg nicht enthalten; füge sie mit `/autosound-tuning:setup app` (oder `/autosound-tuning:install-tcc`) hinzu.

**Nach der Installation:**
1. Der letzte Schritt des Installers meldet dich an: Claude, dann der Gemini-Reviewer (`agy`) und GitHub, falls du es ausgewählt hast.
2. Öffne die App **Autosound TCC** von deinem Schreibtisch aus.
3. Erstelle einen leeren Ordner für dein Auto (z. B. `MyCarTuning`) und wähle ihn in der App aus, mit **AI main: Claude Opus (SDK)** und **AI critic: Gemini Pro (High)** — oder **Gemini Flash (High)**, falls dir Pro nicht angeboten wird.
4. **Wichtig:** Belasse den Effort von Claude Opus bei `xhigh` oder höher (der Standardwert; `max` für schwierige Schritte).
5. Tippe im App-Chat: **"tune a new car from scratch"**. Die KI beginnt mit Fragen und nimmt dich an die Hand.

Möchtest du dich lieber im Terminal mit der KI unterhalten? Das geht ebenfalls, und viele finden es praktischer: Halte TCC daneben im **Control mode** geöffnet, wo du jeden Parameter siehst und steuerst, während die Sitzung läuft ([TCC-Anleitung](https://github.com/ayukhno/autosound-tcc/blob/main/docs/guide/REFERENCE.md#control-mode), [FAQ](FAQ.de.md#control-mode-die-session-im-terminal)).

▶ **Zielkurven:** Die Methode bringt eine eigene Kurve für Wettbewerbe mit: **SQ-Comp-Ref**. Der **[Target Curve Visualizer](https://ayukhno.github.io/autosound-tuning-skill/_curve-visualizer.html?lang=de)** analysiert und vergleicht Kurven nebeneinander – SQ-Comp-Ref, deine eigenen aus REW oder die Standardkurven aus dem [Nono Tuning Tool](https://nonotuningtool.com) – und speichert diejenige, die du auswählst. Wie du eine auswählst: der [Zielkurven-Leitfaden](skills/autosound-tuning/references/patterns/target-curves/target_curves_guide.md).

## So sieht der Tuning-Prozess aus

1. **Vorbereitung zu Hause:** Du informierst die KI über dein System (welche Lautsprecher, welcher Prozessor).
2. **Messungen im Auto (einmalig):** Mit Schutzfiltern auf dem DSP misst du jedes Chassis einzeln in einer einzigen Sitzung ein; die TCC-App leitet dich Schritt für Schritt an. Das Setup wird anschließend am Schreibtisch entworfen.
3. **Berechnungen am Schreibtisch:** Du sitzt an deinem Computer (ohne das Auto in der Nähe). Die KI analysiert die Messungen, bindet den Subwoofer an den Tiefmittelton an, gleicht die Bühne an und berechnet den EQ. Der Schreibtisch liefert nur die Vorhersage der Ergebnisse; im Auto werden sie anschließend überprüft.
4. **Zurück im Auto – überprüfen, korrigieren, feintunen:** Trage die Werte in den DSP ein, prüfe sie mit ein paar Kontrollmessungen sowie nach Gehör und korrigiere, was nicht passt. Danach folgt das Feintuning, das am besten direkt im Auto mit dem fähigsten Modell stattfindet (derzeit Claude Fable): Du beschreibst der KI, was du hörst, und je besser es klingen soll, desto mehr Runden sind nötig. Das Arbeiten am Schreibtisch ist ebenfalls möglich – Modell und Methode passen sich an.

## Feedback, Support und Datenschutz

**Datenschutz:** Der Skill lernt aus jedem Tuning und sendet – nur mit deiner ausdrücklichen Zustimmung – verallgemeinerte Erkenntnisse an eine gemeinsame Wissensdatenbank. Er erfasst niemals persönliche Daten und sendet niemals vollständige Messungen.

**Probleme und Fehler:**
- Wenn etwas mit der Tuning-Logik selbst nicht stimmt: [Öffne ein Issue auf GitHub (autosound-tuning-skill)](https://github.com/ayukhno/autosound-tuning-skill/issues/new/choose).
- Wenn das Problem die grafische Oberfläche (Autosound TCC) betrifft – schreibe an das [TCC-App-Repository](https://github.com/ayukhno/autosound-tcc/issues/new/choose).
- Kein GitHub-Konto? Frage in der Sitzung ("report a bug") oder nutze das Meldefenster von TCC: Dein Bericht geht stattdessen über ein Google Form an den Autor – rein als Text.

Dieses Tool ist **vollständig kostenlos**. Der Code und die Skripte stehen unter der **MIT**-Lizenz, die Dokumentation und die Methode selbst unter **CC BY-SA 4.0**. 

**Credits:** Ein Teil der DSP-Mathematik wurde aus [Resonalyze](https://github.com/DIMOSUS/Resonalyze) von DIMOSUS (MIT) portiert — [`LICENSES/NOTICE.md`](LICENSES/NOTICE.md).

Wenn dir das Tool wochenlange Tuning-Arbeit erspart hat und du dem Autor danken möchtest, kannst du das hier tun:
💜 **[GitHub Sponsors](https://github.com/sponsors/ayukhno)** · ☕ **[Monobank Jar (UA)](https://send.monobank.ua/jar/8wThVcodjm)**

**Guten Klang!**
