# Autosound Tuning Skill

🇬🇧 [English](README.md) · 🇩🇪 **Deutsch** · 🇵🇱 [Polski](README.pl.md) · 🇺🇦 [Українська](README.uk.md) · [FAQ](FAQ.md)

**In einem Satz:** ein Claude-Skill, der dich zu **klarem, transparentem, ausgewogenem Klang** in *deinem* Auto führt — er bringt das ganze Handwerk auf dein konkretes Setup, liest deine REW-Messungen und hilft dir, jede Änderung zu wählen.

- 📊 **Arbeitet mit REW** über die API — holt Messungen, lädt EQ-Filter zurück
- 🎯 **Kennt das Handwerk** — Zielkurven, Abstimmpraktiken, ein Schritt-für-Schritt-Prozess
- 🎧 **Test-Tracks** — worauf zu achten ist und auf welchem Track (Beschreibungen, kein Audio)
- 🚗 **Lernt dein Setup** — sammelt Wissen über Auto & Geräte, nur mit deiner Zustimmung

## Erste Schritte

Dieser Skill läuft als Plugin für **Claude Code** (dem offiziellen Terminal-Agenten von Anthropic).

### 1. Schnelle Installation

Führe diese Befehle in deiner aktiven Claude-Code-Sitzung **nacheinander (einzeln)** aus (kopiere und füge sie nicht zusammen ein):

```bash
/plugin marketplace add ayukhno/autosound-tuning-skill
```

```bash
/plugin install autosound-tuning
```

```bash
/reload-plugins
```

*Dann starte das Tuning mit:* **"tune a new car from scratch"** (oder auf Deutsch: *"stimme ein neues Auto von Grund auf ab"*).

### 2. Umfassendes Setup & FAQ

Brauchst du Hilfe bei der Einrichtung von Claude Code, der Ausführung unter **Windows**, der Konfiguration des **Gemini Critic** oder der Auswahl des Mikrofons?

👉 Siehe direkt in unserem umfassenden **[FAQ.md](FAQ.md)** nach.

---

## Was hier drin ist

```
autosound-tuning-skill/        ein Claude-Code-Plugin
└── skills/autosound-tuning/    der Skill
    ├── SKILL.md        Einstiegspunkt — Prozessübersicht, Sitzungs-Lebenszyklus, Rollen
    ├── references/     Docs bei Bedarf (Phasen, Diagnostik, EQ, Filter, Bühne,
    │                   Test-Tracks, REW API, Helix, die Review-Methode, Intake …)
    ├── knowledge/      gesammelte Auto- & DSP-Profile (cars/, dsp/)
    └── scripts/        Beispiel-Tooling für den Kritiker-Kanal (optional)
```

Ein Skill — die unabhängige Review-Methode (Kritiker/Berater/Schiedsrichter, Anti-Anchoring) ist als `references/core/review-loop.md` gebündelt.

## Für wen & Warum

* **Für wen:** Für alle, die den Sound im Auto aufbauen und dieses Handwerk lernen. Es ist dein Exoskelett, das – angetrieben von deinem Gehör und deinen Handlungen dort, wo es keine direkten Software-Schnittstellen gibt – Wissen und Erfahrung verwaltet, um den Car-HiFi-Sound deiner Träume abzustimmen.
* **Warum:** Abstimmen ist eine Lawine — zu viele Methoden, Parameter und Faustregeln, um sie im Kopf zu behalten, und man verliert sich leicht in einem Detail und damit das Gesamtbild. Der Skill ist dein Navigator: Er hält das Wissen bereit, weist auf die wenigen Änderungen hin, die wirklich zählen, und behält den Kompromiss zwischen Bühnenabbildung und tonaler Balance im Blick. Dein Ohr ist der letzte Richter.

Er deckt eine komplette Abstimmung ab — von einem neuen Projekt über Frequenzweichen, Laufzeitkorrektur, Phase, kanalweisen und summierten EQ, die Bühnenabbildung bis hin zum Voicing nach Geschmack — gesteuert von einer **Generator-↔-Kritiker-↔-Schiedsrichter-Review-Schleife**.

## Deine Erfahrung beitragen

Der Skill lernt aus jeder Abstimmung — und sammelt dieses Feedback direkt im Terminal, während du arbeitest, nicht über ein Formular. Zum Abschluss (sobald du mit dem Klang zufrieden bist) fragt er, was geholfen hat, was nicht passte und welche DSP-/Auto-Eigenheit dir begegnet ist — dann bietet er, **mit deiner ausdrücklichen Zustimmung**, an, die *verallgemeinerbaren* Erkenntnisse zu teilen (um die gemeinsame Methode + die `knowledge/`-Bibliothek wachsen zu lassen).

Er erfasst **nur Methode + Geräteklassen** — Innenraumverhalten, DSP-/Geräteklasse, welche Techniken funktioniert haben. **Niemals persönliche Daten, niemals vollständige Messungen;** du siehst genau, was geteilt wird, und stimmst pro Punkt zu. Bestätigte Erkenntnisse werden mit Namensnennung eingearbeitet.

## Unterstützung

Der Skill ist **kostenlos und offen** (CC BY-SA) und bleibt es — nichts ist hinter einer Zahlung verschlossen. Wenn er geholfen hat und du Danke sagen möchtest, gibt es eine **freiwillige Spendenkasse**, ganz ohne Druck:

☕ **[Diesen Skill unterstützen — Monobank-Kasse](https://send.monobank.ua/jar/8wThVcodjm)** 🤝

Ein Tippen, kein Konto; die Seite akzeptiert auch ausländische Karten (Apple/Google Pay, Visa/Mastercard).

## Lizenz

[CC BY-SA 4.0](LICENSE) — nutze, passe an, teile; halte Ableitungen offen und nenne die Quelle. Es ist ein Methoden-/Wissenswerk, daher hält Share-Alike die gesammelte Erfahrung der Community offen.
