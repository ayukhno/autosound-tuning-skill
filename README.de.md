# Autosound Tuning Skill

🇬🇧 [English](README.md) · 🇩🇪 **Deutsch** · 🇵🇱 [Polski](README.pl.md)

Ein **Skill** für [Claude](https://claude.com/claude-code) zum Abstimmen eines Car-Audio-DSP mit [REW](https://www.roomeqwizard.com/) — von einem brandneuen Projekt (Equipment- + Ziel-Interview, Wahl der Zielkurve, Installationsprüfung) über Weichen, Laufzeitkorrektur, Phase, kanalweises und summiertes EQ, Imaging/Bühne, bis zum Voicing nach Kundengeschmack. Er kodiert eine messbasierte **Methode** (Generator ↔ Kritiker ↔ Schiedsrichter Review-Schleife) plus eine wachsende Bibliothek hart erarbeiteter Diagnosetechniken.

Der Skill ist **Methode, nicht Maschine.** Keine Messungen oder DSP-Zustände eines konkreten Autos liegen hier — die bleiben im eigenen Projekt des Tuners. Dieses Repo liefert den wiederverwendbaren Prozess, der mit **jedem Auto / jedem DSP** funktioniert.

> Entwickelt und im Wettbewerb bewährt an einem VW Passat B8 / Helix DSP Ultra S (ein AYA-Wettbewerbssieg), aber die Auto-/DSP-Spezifika sind in ein Profil + eine `knowledge/`-Bibliothek ausgelagert, sodass ein neues Projekt nur „die Eingaben wählen“ bedeutet.

## Was ist hier drin

```
skills/
├── autosound-tuning/      der Haupt-Skill
│   ├── SKILL.md           Einstiegspunkt (Prozesskarte, Sitzungs-Lebenszyklus, Rollen)
│   ├── references/        Docs bei Bedarf: Phasen, Diagnostik, EQ-Muster, Filtertypen,
│   │                      Bühne/Tiefe, Wettbewerb, Test-Tracks, Voicing-nach-Gehör,
│   │                      REW-API, Helix-Spezifika, Intake, Feedback
│   ├── knowledge/         gesammelte Auto- & DSP-Profile (cars/, dsp/)
│   └── scripts/           Beispiel-Kritiker-Kanal (optionales Rig-Tooling)
└── review-loop/           Partner-Skill: unabhängige Review-Orchestrierung (anbieterneutral)
```

Die zwei Skills sind ein **Paar** — `autosound-tuning` referenziert `review-loop` für das Review-Protokoll. Installiere beide.

## Erste Schritte — neu bei Claude Code / im Terminal?

Dieser Skill läuft in **Claude Code**, einem Terminal-Werkzeug. Wenn du bisher nur Desktop-/Web-Chat genutzt hast, hier die einmalige Einrichtung.

**Warum Claude Code (nicht die Web-App / Cowork):** Abstimmen ist iterativ — messen → analysieren → ändern → erneut messen — über Text-/Zahlendaten (REW-CSV/Text-Exporte, DSP-Konfigs, Iterations-Logs). Ein Terminal + git geben dir Parsing, Skripting und eine vollständige Änderungshistorie. Cowork ist auf Dateioperationen in anderen Apps ausgerichtet — hier überflüssig.

**1. Claude Code installieren** (macOS / zsh; benötigt Node.js 18+ und einen kostenpflichtigen Claude-Plan — Pro / Max / Team / Enterprise; der kostenlose Plan reicht nicht):
```bash
node --version                                   # Node.js 18 oder neuer
mkdir -p ~/.npm-global && npm config set prefix '~/.npm-global'
echo 'export PATH="$HOME/.npm-global/bin:$PATH"' >> ~/.zshrc && source ~/.zshrc
npm install -g @anthropic-ai/claude-code
claude --version                                 # prüfen
```

**2. Projektordner erstellen und starten:**
```bash
mkdir ~/car-audio-setup && cd ~/car-audio-setup
claude                                            # erster Start öffnet den Browser zum Login
```

**3. Nicht überstrukturieren — halte die Struktur schlank.** Beginne mit einem leeren Ordner. Lege deinen ersten REW-Export (`.txt`/`.csv`) so ab, wie er ist, führe ein einziges Markdown-Notizlog (nur anhängen), und lass Ordner (`measurements/`, `configs/`, `eq-log/`) entstehen, wenn du sie wirklich brauchst.

**4. Deine erste Nachricht = „Schritt 0“: Die Initialisierung.** Beschreibe dein System in einer Nachricht: Auto + Lautsprecher-Layout (wie viele Wege, Sub?), DSP-Modell (Helix / Audison / anderes), Mess-Equipment (Mikrofon, Interface), und ob du schon Messungen hast oder von der Hardware startest. Der Skill macht weiter — und **fragt zuerst deine bevorzugte Arbeitssprache** (Englisch / deine Muttersprache, falls unterstützt: EN · UK · DE · PL), damit Gespräch und Projektdateien in ihr entstehen. Dann: Intake → Signalketten-Check → Mikrofon-Kalibrierung → erster Sweep → …

(Danach den Skill selbst installieren — nächster Abschnitt.)

## Voraussetzungen

- **Claude Code** (oder claude.ai mit Skills).
- **REW** mit aktiviertem API-Server (`localhost:4735`), ein kalibriertes Messmikrofon.
- Die **Software deines DSP** und ein Weg, EQ hineinzuladen (Datei-Import ideal; für 30+ DSPs ohne Import siehe [REW-EQ-CopyPaste-Assistant](https://github.com/IvanBakhmutov/REW-EQ-CopyPaste-Assistant)).
- **Optional:** ein zweites KI-Modell als „Kritiker“ (beliebiger Anbieter — die Rollen sind anbieterneutral). Ohne ihn übernimmt ein Mensch die Review-Rolle; der Prozess bleibt gültig.

## Installation

**Am einfachsten — lass Claude es installieren.** Öffne Claude Code und bitte einfach, z. B.:

> *„Installiere den Skill `autosound-tuning` und seinen Begleiter `review-loop` von https://github.com/ayukhno/autosound-tuning-skill in meinen benutzerweiten Skills-Ordner (`~/.claude/skills/`), damit er überall verfügbar ist.“*

Claude klont das Repo und legt **beide** Skills (sie sind ein Paar) dorthin, wo du wählst:

- **Benutzerweit — `~/.claude/skills/`** *(empfohlen)*: in **jedem** Ordner verfügbar, in dem du Claude Code öffnest. Wähle das, wenn du mehr als ein Auto abstimmst oder es immer griffbereit haben willst.
- **Projektweit — `<dein-projekt>/.claude/skills/`**: nur in diesem einen Projekt. Wähle das, um das Repo eines einzelnen Autos eigenständig zu halten.

**Oder manuell:**
```bash
git clone https://github.com/ayukhno/autosound-tuning-skill.git
# benutzerweit (überall verfügbar):
cp -R autosound-tuning-skill/skills/autosound-tuning ~/.claude/skills/
cp -R autosound-tuning-skill/skills/review-loop      ~/.claude/skills/
# …oder projektweit: dieselben zwei Ordner nach  dein-projekt/.claude/skills/
```

Dann Claude Code in deinem Projekt öffnen und z. B. sagen: *„stimme ein neues Auto von Grund auf ab“* / *"tune a new car from scratch"* — der Skill startet mit **Intake** (`references/project-intake.md`): Quickstart, Equipment- + Ziel-Interview, Wahl der Zielkurve (kein Default — mit dir gewählt), Installationsprüfung und Erzeugung der Projektdateien.

## Deine Erfahrung beitragen

Der Skill **lernt aus jeder Abstimmung — und sammelt dieses Feedback direkt im Terminal, während du arbeitest, nicht über ein auszufüllendes Formular.** Zum Abschluss (Phase 7) führt er ein kurzes Abschlussritual durch: fragt, was wirklich geholfen hat, was danebenlag, und welche DSP-/Auto-Eigenheit dir begegnet ist — und bietet dann, **mit deiner ausdrücklichen Zustimmung**, an, die *verallgemeinerbaren* Erkenntnisse zu teilen.

**Wozu die Abschlussumfrage dient und was sie erfasst:** um die gemeinsame Methode + die `knowledge/`-Bibliothek wachsen zu lassen. Erfasst werden **nur Methode + Geräteklassen** — das Verhalten von Karosserie/Innenraum, das DSP/der Prozessor und die Geräteklasse, und welche Techniken funktioniert haben. **Niemals persönliche Daten, niemals vollständige Messungen.** Du siehst genau, was geteilt würde, und stimmst pro Punkt zu (oder nicht).

Bestätigte Erkenntnisse werden in den Skill und die `knowledge/`-Auto-/DSP-Profile eingearbeitet (mit Namensnennung). Tipps, die bestehenden Erkenntnissen widersprechen, werden als *Varianten* behalten, nicht gelöscht — ein anderer Innenraum kann sie richtig machen.

*(Lieber GitHub? Du kannst weiterhin ein [Field-Feedback-Issue](../../issues/new?template=field-feedback.md) öffnen — gleiche Regel: nur Methode/Geräteklassen.)*

## Lizenz

[CC BY-SA 4.0](LICENSE) — nutze, passe an, teile; halte Ableitungen offen und nenne die Quelle. Es ist ein Methoden-/Wissenswerk, daher hält Share-Alike die gesammelte Erfahrung der Community offen. Die Lizenzbedingungen garantieren, dass methodisches Wissen der Community zugänglich bleibt.
