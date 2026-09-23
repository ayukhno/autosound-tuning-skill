# KI-Assistent für Car-HiFi (Autosound Tuning Skill)

🇬🇧 [English](README.md) · 🇩🇪 **Deutsch** · 🇵🇱 [Polski](README.pl.md) · 🇺🇦 [Українська](README.uk.md) · ❓ [FAQ](FAQ.de.md) · <img src="assets/icons/roadmap.svg" width="14" height="14" valign="middle" alt="Roadmap" /> [Roadmap (EN)](ROADMAP.md)

**In einfachen Worten:** Dies ist dein persönlicher KI-Meister für das Einstellen von Car-HiFi. Du willst eine perfekte Bühne und eine saubere tonale Balance, aber Graphen, Phasen und Laufzeiten erscheinen dir zu kompliziert? Dieser Assistent übernimmt den schwierigsten Teil. Er liest deine Mikrofonmessungen und führt dich Schritt für Schritt zum perfekten Sound.

- **Du misst — die KI rechnet:** Sie arbeitet mit der REW-Software zusammen, analysiert die Akustik deines Innenraums und schlägt genaue Einstellungen für EQ, Frequenzweichen und Laufzeitkorrektur vor.
- **Minimale Zeit im Auto:** Die Hauptberechnungen finden an deinem Schreibtisch zu Hause statt. Du machst nur die initialen Messungen im Auto und kommst dann mit fertigen Zahlen zurück, um dir das Ergebnis anzuhören und tiefer ins Tuning einzusteigen.
- **Schreibt nichts in deinen DSP — du lädst es:** Der Assistent greift niemals direkt in deinen Prozessor ein. Er zeigt dir Zahlen und Graphen und bereitet den EQ für den Import vor: Bei einem Helix wandert die gesamte Full-EQ-Bank über das DSP PC-Tool in einem Schritt hinein, und für Prozessoren ohne Datei-Import fügt der kostenlose [REW-EQ-CopyPaste-Assistant](https://github.com/IvanBakhmutov/REW-EQ-CopyPaste-Assistant) ihn ein. Du entscheidest, was hineinkommt.
- **Kein normaler Chat:** Der Projektstatus und alle Einstellungen werden als Dateien auf deiner Festplatte gespeichert, sodass zwischen den Sitzungen nichts „vergessen“ wird und du jederzeit einen Schritt zurückgehen kannst.
- **Zwei KIs — ein Reviewer gehört zur Methode:** Eine KI schlägt Einstellungen vor, eine zweite kritisiert und überprüft sie. Optional ist lediglich der *automatische Kanal* (ein lokales Skript, das Pakete zwischen ihnen übergibt); die *Rolle* des Reviewers ist es nicht — ohne zweite Meinung ist die Methode spürbar schlechter, und wo sich kein Kanal einrichten lässt, fügst du das Paket manuell in den Chat einer beliebigen anderen KI ein oder liest es selbst. Aber der letzte Richter ist dein Ohr: Du hörst zu und entscheidest, anstatt ihre Ideen einfach blind zu übernehmen.
- **Arbeitet mit Fakten:** Eine Überprüfung, der Daten fehlen, verweigert die Arbeit. Die KI rät keine Einstellungen — wenn die Messungen falsch gemacht wurden oder unzureichend sind, wird eine spezifische Prüfung die Berechnung einfach ablehnen und stoppen.

## Auf Wettbewerben bewährt

Mit der Version 2.x dieser Methode holte das Auto des Autors im Jahr 2026 vier Auszeichnungen bei **EMMA**- und **AYA**-Meisterschaften (die erste Auszeichnung wurde errungen, bevor die Methode zu einem Skill wurde, durch KI-Tipps anhand derselben Graphen, was die Idee für diesen Skill lieferte). Die neueste Version 3.x (mit grafischer Oberfläche) befindet sich derzeit in der Beta-Phase und hat ihre Wettbewerbserprobung gerade begonnen: Die fünfte Auszeichnung — der 3. Platz beim **Deutschen EMMA Finale 2026** — entstand durch die Nachabstimmung des bestehenden Setups mit 3.x, nicht durch ein Tuning von Grund auf. Für ein garantiertes Ergebnis entscheiden sich daher viele weiterhin für die bewährte Version 2.8.x.

<p align="left">
  <img src="assets/awards/aya-may26-einsteiger5000.jpg" height="120" alt="AYA Mai 2026, Einsteiger 5000, 1. Platz">
  &nbsp;&nbsp;&nbsp;
  <img src="assets/awards/aya-jul26-amateur5000.jpg" height="120" alt="AYA Juli 2026, Amateur 5000, 1. Platz">
  &nbsp;&nbsp;&nbsp;
  <img src="assets/awards/aya-aug26-amateur5000.jpg" height="120" alt="AYA August 2026, Amateur 5000, 2. Platz">
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
  <img src="assets/awards/emma-aug26-entry-unlimited.jpg" height="120" alt="EMMA Sound Off 2026, SQ Entry Unlimited, 3. Platz">
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
  <img src="assets/awards/emma-sep26-final-entry-unlimited.jpg" height="120" alt="Deutsches EMMA Finale 2026, Frankfurt, SQ Entry Unlimited, 3. Platz">
</p>

*Deine Anlage kann auch wie ein Champion klingen!*

> [!CAUTION]
> Die KI ist ein Assistent, aber die Verantwortung liegt bei dir. Eine manuell mit Tippfehler eingegebene Zahl kann einen Hochtöner durchbrennen lassen. Überprüfe immer die Trennfrequenzen, bevor du den Ton einschaltest, und beginne immer mit geringer Lautstärke.

## Was du für den Start brauchst

Du musst kein Programmierer sein — das Programm lässt sich mit einem einzigen Befehl installieren. Aber an Hardware und Abos brauchst du Folgendes:

1. **Messmikrofon** (z.B. UMIK-1, besser ein XLR-Mikrofon mit Soundkarte und physischem Loopback).
2. **Prozessor (DSP)** in deinem Auto.
3. **REW (Room EQ Wizard) Software** — **Beta-Version** ist erforderlich (der aktuelle Release-Build, V5.31.3 vom Juli 2024, hat überhaupt keine API — prüfe Help → About, bevor du beginnst). Hol dir den Beta-Build unter [roomeqwizard.com/beta.html](https://www.roomeqwizard.com/beta.html). Nach dem Start von REW gehe auf *Preferences → API*, aktiviere **Start the API when REW starts** und klicke auf **Start server**.
4. **Kostenpflichtiges Claude-Abo (Pro oder Max)** — diese KI erledigt die Hauptarbeit und löst komplexe mathematische Probleme. Dies ist der unterstützte Weg, und die grafische App ist dafür gebaut. Ein Durchlauf, der vollständig von einer anderen KI gesteuert wird, ist möglich, aber manuell, und du verzichtest auf die zweite Meinung, auf die sich die Methode stützt — siehe FAQ, „Kann ich die Methode komplett in Gemini ausführen?“. Ohne Internet am Auto funktioniert die Sitzung so oder so nicht.

*(Wir empfehlen außerdem ein kostenloses GitHub-Konto, um deinen Tuning-Verlauf in einem privaten Repository zu sichern — der Installer fügt GitHubs `gh` dafür hinzu, wenn du danach fragst: `--github`, oder `-GitHub` unter Windows. Dein Gemini-API-Key, falls du einen verwendest, wandert **nicht** mit diesem Backup: Er liegt außerhalb des Projekts in `~/.config/autosound/critic-env` — `%APPDATA%\autosound\critic-env` unter Windows — und ein neues Projekt wird mit einer `.gitignore` angelegt, die auch die projektlokale Konfiguration aus Git heraushält.)*

## Installation und Start (Version 3.x — Beta)

Wir haben einen Installer entwickelt, der alles Nötige herunterlädt und eine praktische **grafische Anwendung (Autosound TCC)** vorbereitet. Andere Modelle als Claude laufen über **`omp`**, was der Installer **nur auf Wunsch** hinzufügt (Optionen unten). Diese Modelle werden **nach Nutzung abgerechnet**, und nichts läuft über `omp`, es sei denn, du wählst eines davon aus; die reine Terminal-Installation bringt es nie mit. Der Vorgang dauert 10–20 Minuten (unter macOS öffnet sich einmalig Apples eigenes Installationsfenster für die Entwicklerwerkzeuge — ein Klick, und kein Passwort wird in das Skript eingegeben; unter Windows erscheint ein Git-Berechtigungsdialog).

**macOS** — öffne das Terminal (⌘-Space drücken, "terminal" tippen, Enter) und füge ein:
```sh
curl -fsSL https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/v3.0.61/install.sh | bash
```

**Windows** — öffne PowerShell (Start drücken, "powershell" tippen, Enter) und füge ein:
```powershell
irm https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/v3.0.61/install.ps1 | iex
```

**Optionen:** `--with-omp` (andere Modelle als Claude), `--github` (das Backup), `--terminal` (die Methode ohne die App), `--dry-run` (zeigt den Plan, ändert nichts). Unter macOS kommen sie hinter `bash -s --`:
```sh
curl -fsSL https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/v3.0.61/install.sh | bash -s -- --github
```
Unter Windows lauten sie `-WithOmp`, `-GitHub`, `-Terminal`, `-DryRun`, in dieser Form:
```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/v3.0.61/install.ps1))) -GitHub
```

**Nach der Installation:**
1. Der letzte Schritt des Installers meldet dich an: Claude im Browser, dann der Gemini-Reviewer über Googles `agy` (Enter meldet an, `s` überspringt) und GitHub, falls `gh` vorhanden ist.
2. Auf dem Desktop erscheint die App **Autosound TCC**. Öffne sie.
3. Erstelle einen neuen leeren Ordner für dein Auto (z.B. `MyCarTuning`) und wähle ihn im Programm aus, mit **AI main: Claude Opus (SDK)** und **AI critic: Gemini Pro (High)**.
4. **WICHTIG:** Stelle vor deiner ersten Nachricht sicher, dass das Anstrengungsniveau (Effort) für **Claude Opus** mindestens auf `xhigh` steht (dies ist der Standardwert). Für sehr komplexe Schritte verwende `max`. Das ist entscheidend: Eine schwächere Modellstufe hält bei einem Fehler nicht an; sie stimmt dir einfach zu, was zu „stillen Fehlern“ beim Tuning führt. *Hinweis: Änderungen am Effort-Level gelten erst für die nächste Sitzung.*
5. Schreibe in den App-Chat: **"tune a new car from scratch"**. Die KI fängt an, Fragen zu stellen und nimmt dich an die Hand.

▶ **[Öffne den Target Curve Visualizer online](https://ayukhno.github.io/autosound-tuning-skill/_curve-visualizer.html?lang=de)** — ziehe deine Kurve oder eine Standardkurve aus dem [Nono Tuning Tool](https://nonotuningtool.com) hinein, vergleiche Graphen und speichere sie.

---

**Wettbewerbserprobte Version 2.8.x** — [Weg 3 im FAQ](FAQ.de.md#vier-optionen-zur-nutzung)

Wenn du genau die **2.8.x** Version nutzen möchtest, mit der die Wettbewerbe gewonnen wurden: Diese funktioniert ausschließlich über das Terminal. Anstelle der obigen Skripte führe in einem Terminal mit bereits installiertem `claude` (Claude Code) zwei Befehle aus:
```sh
claude plugin marketplace add ayukhno/autosound-tuning-skill
claude plugin install autosound-tuning
```
*(Falls `claude` noch nicht installiert ist, kannst du es mit dem offiziellen Skript hinzufügen: `curl -fsSL https://claude.ai/install.sh | sh`, oder alternativ über npm).*

## Wie der Tuning-Prozess abläuft

1. **Vorbereitung zu Hause:** Du erzählst der KI von deinem System (welche Lautsprecher, welcher Prozessor).
2. **Messungen im Auto (einmalig):** eine disziplinierte Sitzung, und die Abstimmung wird anschließend am Schreibtisch entworfen. Du aktivierst die grundlegenden Schutzfilter an deinem DSP und nimmst jeden Treiber einzeln auf — zuerst ein handgeführter Durchgang, dann derselbe Satz mit einem **Mikrofon auf einem Stativ, das bis zum Schluss nicht bewegt wird**, eingerahmt von je einem Kontroll-Sweep zu Beginn und am Ende, damit jede Drift sichtbar wird. Plane **~25 Minuten für den Pflichtteil** (den Stativ-Block) ein und bis zu etwa einer Stunde, wenn du auch den handgeführten Neun-Positionen-Satz aufnimmst, der Innenraum-Eigenschaften von punktuellen Effekten unterscheidet. Das genaue Ablaufblatt befindet sich in der Methode (`capture-session-sheet.md`); die App führt dich Block für Block hindurch. *Hinweis: Ein Tiefmitteltöner ohne Tiefpassfilter (LPF) klingt obenrum beim Sweep schrill — das ist normal (Membranaufbruch), brich die Messungen nicht ab.*
3. **Mathematik am Schreibtisch:** Du sitzt am Computer (ohne das Auto in der Nähe). Die KI analysiert die Messungen, koppelt den Subwoofer an den Tiefmitteltöner, richtet die Bühne aus und berechnet den Equalizer. Der Schreibtisch prognostiziert nur die Ergebnisse; das Auto verifiziert sie anschließend. Wenn die Prognosen des Schreibtischs bei der Überprüfung nicht mit der Realität übereinstimmen, macht das System die Schritte rückgängig.
4. **Genuss im Auto:** Du gehst zurück zum Auto, gibst die fertigen Zahlen in den DSP ein, spielst Test- und Lieblingslieder ab und genießt. Wenn etwas leicht brummt, „in den Ohren wehtut“ oder „die Bühne verschoben ist“ — sagst du es der KI, und ihr korrigiert das Problem gezielt.

## Feedback, Support und Datenschutz

**Datenschutz:** Der Skill lernt aus jedem Tuning und sendet, nur mit deiner ausdrücklichen Zustimmung, verallgemeinerte Lektionen an eine gemeinsame Wissensdatenbank. Er sammelt niemals persönliche Daten und versendet keine vollständigen Messungen.

**Probleme und Bugs:**
- Wenn mit der Tuning-Logik selbst etwas nicht stimmt: [Öffne ein Issue auf GitHub (autosound-tuning-skill)](https://github.com/ayukhno/autosound-tuning-skill/issues/new/choose).
- Wenn das Problem die grafische Oberfläche (Autosound TCC) betrifft — schreibe ins [Repository der TCC-App](https://github.com/ayukhno/autosound-tcc/issues/new/choose).

Dieses Tool ist **komplett kostenlos**. Der Code und die Skripte stehen unter der **MIT**-Lizenz, die Dokumentation und die Methode selbst unter **CC BY-SA 4.0**.

**Danksagung:** Ein Teil der DSP-Mathematik folgt der Logik des Projekts [Resonalyze](https://github.com/DIMOSUS/Resonalyze) von DIMOSUS (MIT) — die Summenverlust-Metrik an der Trennstelle und die HELIX-Kanal-Phasensteuerung sind Portierungen daraus, damit ein Tuner, der zwischen beiden Werkzeugen wechselt, pro Filter eine Antwort erhält und nicht zwei. Details in [`LICENSES/NOTICE.md`](LICENSES/NOTICE.md).

Wenn es dir Wochen an Tuning-Zeit gespart hat und du dem Autor danken möchtest, kannst du das hier tun:
💜 **[GitHub Sponsors](https://github.com/sponsors/ayukhno)** · ☕ **[Monobank Jar (UA)](https://send.monobank.ua/jar/8wThVcodjm)**

**Guten Sound!**
