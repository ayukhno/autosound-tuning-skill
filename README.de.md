# Autosound Tuning Skill

🇬🇧 [English](README.md) · 🇩🇪 **Deutsch** · 🇵🇱 [Polski](README.pl.md) · 🇺🇦 [Українська](README.uk.md)

**In einem Satz:** ein Claude-Skill, der dir hilft, Car-Audio abzustimmen — er liest deine REW-Messungen, analysiert sie, empfiehlt Einstellungen und kann EQ zurück in REW laden.

- 📊 **Arbeitet mit REW** über die API — holt Messungen, lädt EQ-Filter zurück
- 🎯 **Kennt das Handwerk** — Zielkurven, Abstimmpraktiken, ein Schritt-für-Schritt-Prozess
- 🎧 **Test-Tracks** — worauf zu achten ist und auf welchem Track (Beschreibungen, kein Audio)
- 🚗 **Lernt dein Setup** — sammelt Wissen über Auto & Geräte, nur mit deiner Zustimmung

Er deckt eine komplette Abstimmung ab — von einem neuen Projekt (Interview zu Equipment + Zielen, Wahl der Zielkurve, Einbau-Checks) über Frequenzweichen, Laufzeitkorrektur, Phase, kanalweisen und summierten EQ und die Bühnenabbildung, bis hin zum Voicing nach Geschmack — gesteuert von einer Generator-↔-Kritiker-↔-Schiedsrichter-Review-Schleife. Es ist **Methode, keine Maschine**: keine Messungen eines Autos oder DSP-Zustände liegen hier (die bleiben in deinem Projekt), also funktioniert es mit **jedem Auto / jedem DSP**.

> Gebaut und praxiserprobt an einem VW Passat B8 / Helix DSP Ultra S (ein AYA-Wettbewerbssieg); die Auto-/DSP-Spezifika sind in ein Profil + eine `knowledge/`-Bibliothek ausgelagert, sodass ein neues Projekt nur „die Eingaben wählen“ heißt.

## Was hier drin ist

```
skills/
├── autosound-tuning/   der Haupt-Skill
│   ├── SKILL.md        Einstiegspunkt — Prozessübersicht, Sitzungs-Lebenszyklus, Rollen
│   ├── references/     Docs bei Bedarf (Phasen, Diagnostik, EQ, Filter, Bühne,
│   │                   Test-Tracks, REW API, Helix, Intake, Feedback …)
│   ├── knowledge/      gesammelte Auto- & DSP-Profile (cars/, dsp/)
│   └── scripts/        Beispiel-Tooling für den Kritiker-Kanal (optional)
└── review-loop/        Schwester-Skill: Orchestrierung unabhängiger Reviews
```

Die beiden sind ein **Paar** — `autosound-tuning` nutzt `review-loop` für das Review-Protokoll. Installiere beide.

## Erste Schritte — neu bei Claude Code?

Dieser Skill läuft in **Claude Code**, einem Terminal-Tool. Abstimmen ist iterativ (messen → analysieren → ändern → neu messen) über Text-/Zahlendaten, daher passen ein Terminal + git — Parsing, Skripting, vollständige Änderungshistorie — weit besser als die Web-App.

**1. Claude Code installieren** (macOS / zsh; benötigt Node.js 18+ und einen kostenpflichtigen Claude-Plan — Pro / Max / Team / Enterprise):
```bash
node --version                                   # Node.js 18 oder neuer
mkdir -p ~/.npm-global && npm config set prefix '~/.npm-global'
echo 'export PATH="$HOME/.npm-global/bin:$PATH"' >> ~/.zshrc && source ~/.zshrc
npm install -g @anthropic-ai/claude-code
claude --version                                 # prüfen
```

**2. Projektordner anlegen und starten:**
```bash
mkdir ~/car-audio-setup && cd ~/car-audio-setup
claude                                            # der erste Start öffnet den Browser zum Anmelden
```

**3. Halte es einfach.** Ein leerer Ordner, dein erster REW-Export unverändert hineingelegt, ein anhängender Notiz-Log — lass Unterordner entstehen, wenn du sie wirklich brauchst.

**4. Deine erste Nachricht = „Schritt 0“.** Beschreibe dein System: Auto + Lautsprecher-Layout (Wege, Sub?), DSP-Modell, Messtechnik, und ob du schon Messungen hast. Den Rest übernimmt der Skill — und **fragt zuerst nach deiner bevorzugten Arbeitssprache** (EN · UK · DE · PL), damit Gespräch und Projektdateien in ihr entstehen.

## Voraussetzungen

- **Claude Code** (oder claude.ai mit Skills).
- **REW** mit aktiviertem API-Server (`localhost:4735`) und ein kalibriertes Mikrofon.
- Die **Software deines DSP** + eine Möglichkeit, EQ zu laden (Datei-Import ideal; für 30+ DSPs ohne Import siehe [REW-EQ-CopyPaste-Assistant](https://github.com/IvanBakhmutov/REW-EQ-CopyPaste-Assistant)).
- **Optional:** ein zweites KI-Modell als „Kritiker“ (beliebiger Anbieter). Ohne es übernimmt ein Mensch das Review; der Prozess hält trotzdem.

## Installation

**Am einfachsten — lass Claude es erledigen.** Öffne Claude Code und sag:

> *„Klone https://github.com/ayukhno/autosound-tuning-skill in einen temporären Ordner, kopiere dann die zwei **inneren** Ordner `skills/autosound-tuning` und `skills/review-loop` nach `~/.claude/skills/`, sodass jede `SKILL.md` direkt unter `~/.claude/skills/<name>/SKILL.md` landet. Klone nicht das ganze Repo in den Skills-Ordner.“*

Installiere **beide** (sie sind ein Paar) auf **Benutzerebene — `~/.claude/skills/`** (überall verfügbar, empfohlen) oder **Projektebene — `<projekt>/.claude/skills/`** (hält das Repo eines Autos eigenständig).

> ⚠️ **Der eine zu vermeidende Fehler:** klone das Repo nicht *in* `~/.claude/skills/autosound-tuning/`. Das verschachtelt `SKILL.md` eine Ebene zu tief, und Claude meldet **`Unknown skill`**. Kopiere immer die **inneren** `skills/*`-Ordner, sodass `SKILL.md` *direkt* unter dem Skill-Ordner liegt.

**Manuell:**
```bash
git clone https://github.com/ayukhno/autosound-tuning-skill.git
cp -R autosound-tuning-skill/skills/autosound-tuning ~/.claude/skills/
cp -R autosound-tuning-skill/skills/review-loop      ~/.claude/skills/
# prüfen — jede Zeile muss den Pfad ausgeben (SKILL.md direkt unter dem Skill-Ordner):
ls ~/.claude/skills/autosound-tuning/SKILL.md
ls ~/.claude/skills/review-loop/SKILL.md
```

**Dann starte eine frische Claude-Code-Sitzung** (Skills laden beim Start) und sag z. B. *„stimme ein neues Auto von Grund auf ab“* — der Skill beginnt mit dem **Intake**: Schnellstart, Interview zu Equipment + Zielen, Wahl der Zielkurve (mit dir gewählt), Einbau-Checks, Erzeugung der Projektdateien. *(Bei `Unknown skill` oder wenn er nie auslöst — fast immer die obige Verschachtelung; kopiere die inneren `skills/*`-Ordner neu und starte neu.)*

## Deine Erfahrung beitragen

Der Skill **lernt aus jeder Abstimmung — und sammelt dieses Feedback direkt im Terminal, während du arbeitest, nicht über ein Formular.** Zum Abschluss (Phase 7) fragt er, was geholfen hat, was nicht passte und welche DSP-/Auto-Eigenheit dir begegnet ist — dann bietet er, **mit deiner ausdrücklichen Zustimmung**, an, die *verallgemeinerbaren* Erkenntnisse zu teilen (um die gemeinsame Methode + die `knowledge/`-Bibliothek wachsen zu lassen).

Er erfasst **nur Methode + Geräteklassen** — Innenraumverhalten, DSP-/Geräteklasse, welche Techniken funktioniert haben. **Niemals persönliche Daten, niemals vollständige Messungen;** du siehst genau, was geteilt wird, und stimmst pro Punkt zu. Bestätigte Erkenntnisse werden mit Namensnennung eingearbeitet; widersprechende Tipps werden als *Varianten* behalten, nicht gelöscht. *(Lieber GitHub? Öffne ein [Field-Feedback-Issue](../../issues/new?template=field-feedback.md) — gleiche Regel.)*

## Unterstützung

Der Skill ist **kostenlos und offen** (CC BY-SA) und bleibt es — nichts ist hinter einer Zahlung verschlossen. Wenn er geholfen hat und du Danke sagen möchtest, gibt es eine **freiwillige Spendenkasse**, ganz ohne Druck:

☕ **[Diesen Skill unterstützen — Monobank-Kasse](https://send.monobank.ua/jar/8wThVcodjm)** 🤝

Ein Tippen, kein Konto; die Seite akzeptiert auch ausländische Karten (Apple/Google Pay, Visa/Mastercard).

## Lizenz

[CC BY-SA 4.0](LICENSE) — nutze, passe an, teile; halte Ableitungen offen und nenne die Quelle. Es ist ein Methoden-/Wissenswerk, daher hält Share-Alike die gesammelte Erfahrung der Community offen.
