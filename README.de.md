# Autosound Tuning Skill

🇬🇧 [English](README.md) · 🇩🇪 **Deutsch** · 🇵🇱 [Polski](README.pl.md) · 🇺🇦 [Українська](README.uk.md) · [FAQ](FAQ.md)

**In einem Satz:** ein Claude-Skill, der dich zu klarem, transparentem, ausgewogenem Klang in *deinem* Auto führt. Er bringt das ganze Handwerk auf dein konkretes Setup, liest deine REW-Messungen und hilft dir, jede Änderung zu wählen.

- **Arbeitet mit REW**: holt Messungen über die API, schreibt berechnete EQ-Filter zurück in REW, von wo du sie in dein DSP exportierst
- **Diagnostiziert, bevor korrigiert wird**: ermittelt EQ-fähige Frequenzen, akustische Reflexionen (Phasenauslöschungen) und Verzerrungsgrenzen jedes Treibers aus deiner Grundmessung, bevor eine Weichen- oder EQ-Änderung vorgeschlagen wird
- **Kennt das Handwerk**: Zielkurven, Abstimmpraktiken, ein Schritt-für-Schritt-Prozess
- **Test-Tracks**: worauf zu achten ist und auf welchem Track (Beschreibungen, kein Audio)
- **Lernt dein Setup**: sammelt Wissen über Auto und Geräte, nur mit deiner Zustimmung

> [!CAUTION]
> KI kann sich bei Zahlen irren. Prüfe Trennfrequenzen, Flankensteilheiten und EQ-Werte in deinem DSP immer manuell nach, bevor du die Stummschaltung aufhebst, besonders bei Hochtönern, und starte bei niedriger Lautstärke.

## Für wen & Warum

* **Für wen:** Für alle, die den Sound im Auto aufbauen und dieses Handwerk lernen. Es ist dein Exoskelett (angetrieben von deinem Gehör und deinen Handlungen dort, wo es keine direkten Software-Schnittstellen gibt), das Wissen und Erfahrung verwaltet, damit du den Klang deines Autos abstimmen kannst.
* **Warum:** Abstimmen ist eine Lawine: zu viele Methoden, Parameter und Faustregeln, um sie im Kopf zu behalten, und man verliert sich leicht in einem Detail und damit das Gesamtbild. Der Skill ist dein Navigator: Er hält das Wissen bereit, weist auf die wenigen Änderungen hin, die wirklich zählen, und behält den Kompromiss zwischen Bühnenabbildung und tonaler Balance im Blick. Dein Ohr ist der letzte Richter.

Er deckt eine komplette Abstimmung ab, von einem neuen Projekt über Frequenzweichen, Laufzeitkorrektur, Phase, kanalweisen und summierten EQ, die Bühnenabbildung, bis hin zum Voicing nach Geschmack, gesteuert von einer **Generator ↔ Kritiker ↔ Schiedsrichter**-Review-Schleife.

## Erste Schritte

Dieser Skill läuft als Plugin für **Claude Code** (den offiziellen Terminal-Agenten von Anthropic). Falls du ihn noch nicht hast, findest du unten in der FAQ Copy-paste-Installationsschritte für macOS/Windows (eine bezahlte Claude-Subscription ist erforderlich; Kostenwege siehe FAQ).

Führe diese Befehle in deiner aktiven Claude-Code-Sitzung **nacheinander, einzeln** aus (kopiere und füge sie nicht zusammen ein):

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

> **Auslösen — nenne ein Car-Audio-Wort.** Der Skill reagiert auf das, *was du fragst*, ein bloßes `resume` allein weckt ihn also nicht (zu allgemein — könnte jedes Projekt meinen). Füge ein Domänenwort hinzu: **„Auto-DSP weiter einmessen"**, **„zurück zur Car-HiFi-Abstimmung"**, **„was ist mein aktueller DSP-/Trennfrequenz-Stand"**. Genauso beim Neustart: nenne Auto/Audio, nicht nur „hilf mir".

## Empfohlene Modelle, Modi & meine Erfahrung

Der Skill unterstützt zwei Arten, ihn zu betreiben, nach Zuverlässigkeit geordnet. Wähle danach, wie wichtig diese Abstimmung ist und wie viel Aufwand du in die Einrichtung stecken willst:

| Modus | Einrichtung | Zuverlässigkeit | Kompromiss |
| :--- | :--- | :--- | :--- |
| **A: Claude + Gemini** | Claude Sonnet 5 führt, Gemini prüft (2.5 Pro für schwierige akustische Entscheidungen, 2.5 Flash für Routine) | Höchste | Zwei KIs einzurichten; fängt mehr ab, langsamer pro Entscheidung |
| **B: Solo-Betrieb (Claude oder Gemini)** | Ein Modell führt und prüft sich selbst; Eskalation auf eine stärkere Stufe bei schwierigen Frequenzweichen-Entscheidungen (Claude Opus 4.8 oder eine höhere Gemini-Stufe) | Niedriger, hängt vom gewählten Modell ab | Nur eine Perspektive; Gemini solo liefert mutige, unkonventionelle Vorschläge, deren Zahlen aber von Hand geprüft werden müssen |

**Meine eigene Erfahrung bisher** (das ist bisher nur meine eigene Erfahrung; sobald mehr Leute damit abgestimmt haben, soll das hier die Erfahrung der Community widerspiegeln, nicht nur meine):

* **Claude führt, Gemini prüft (Modus A):** stabil, bewegt sich aber in kleinen Schritten, was etwas langsam wirken kann. Du musst mindestens für Claude bezahlen. Kostenloses Gemini funktioniert auch, stößt aber manchmal an seine Grenzen. Noch etwas, das mir aufgefallen ist: Sonnet ist zuverlässig, aber vorsichtig, und hält oft an, um Dinge zu erfragen, die Opus meist selbst entscheidet, schneller.
* **Gemini führt, mit Claude oder einem stärkeren Gemini-Modell als Prüfer:** deutlich schneller. Nach zwei vollständigen Messrunden hatte ich bereits eine erste funktionierende Version. Später in der Sitzung kann es aber anfangen zu halluzinieren oder frühere Entscheidungen zu vergessen, bis zu dem Punkt, an dem ich zurück zu Claude wechseln wollte. Ich habe das nicht mit kostenlosem Gemini probiert, wegen der Limits. Die kostenlose Gemini-Stufe hat harte Ratenlimits; um sie aufzuheben, brauchst du ein bezahltes Google-Cloud-Abrechnungskonto, für dessen Aktivierung eine Mindesteinzahlung von $10 nötig ist, und bei manchen Karten (z. B. ukrainischen) ist das eine echte Abbuchung, keine bloße Reservierung. Neue Konten erhalten dabei aktuell auch $300 Guthaben geschenkt, genug für eine ganze Abstimmung, aber dieses Guthaben verfällt nach 3 Monaten und ist eine aktuelle Aktion, keine dauerhaft garantierte Konditionen. Wenn du ohnehin für API-Zugriff zahlst, kommt Modus A insgesamt günstiger.
* **Die manuelle Schritt-für-Schritt-Version (ohne lokale Skripte):** funktioniert, aber der Copy-paste-Prozess ist nervenaufreibend. Man muss aufpassen, dabei nichts zu verlieren. Nach einer vollen Sitzung mit echtem Gedächtnis zwischen den Nachrichten kostet es Überwindung, dahin zurückzukehren.
* **Welches Modell bisher am zuverlässigsten als Fahrer ist:** **Claude Opus** hat bisher die stabilsten Ergebnisse geliefert. **Sonnet 5** funktioniert, wirkt in dieser Rolle aber bisher weniger sicher — seine Entscheidungen sollte man vorerst genauer prüfen. **Fable 5** hat bisher die besten Ergebnisse aller Modelle erzielt: In derselben Sitzung, in der es den Skill auditiert und überarbeitet hat (siehe [audit-fable-2026-07-11.md](audit-fable-2026-07-11.md)), hat es auch eine vollständige Abstimmungssitzung durchgeführt — und das ist bisher das klanglich beste Ergebnis. **Gemini** hat mit zunehmender Komplexität der Prozessregeln etwas an Leistungsfähigkeit eingebüßt; seitdem wurden ein Audit und eine Optimierung durchgeführt, die das beheben sollten, aber das ist in einer echten Sitzung noch nicht bestätigt — Rückmeldungen aus der Community sind hier willkommen.

**Start mit Gemini als Fahrer:** noch nicht ganz so schnell wie mit Claude Code, zumindest bisher. Es gibt keinen Plugin-Installer dafür, aber der schnellste Weg ist, eine agentische Gemini-Sitzung (Antigravity CLI oder ein beliebiges Gemini-Setup mit Datei- und Shell-Zugriff) direkt auf das Repository anzusetzen und zu bitten:

> Clone https://github.com/ayukhno/autosound-tuning-skill, read `skills/autosound-tuning/SKILL.md`, and follow that method as your operating instructions for this session.

Mehr dazu in der FAQ.

## Vollständiges Setup & FAQ

Brauchst du Hilfe bei der Einrichtung von Claude Code, der Ausführung unter **Windows**, der Konfiguration des **Gemini Critic** (einschließlich eines kostenlosen, browserbasierten Arbeitsbereichs über **Google AI Studio**) oder der Auswahl des Mikrofons?

Sieh dir unsere **[FAQ.md](FAQ.md)** an.

## Was hier drin ist

```
autosound-tuning-skill/        ein Claude-Code-Plugin
└── skills/autosound-tuning/    der Skill
    ├── SKILL.md        Einstiegspunkt — Prozessübersicht, Sitzungs-Lebenszyklus, Rollen
    ├── references/     Docs bei Bedarf (Phasen, Diagnostik, EQ, Filter, Bühne,
    │                   Test-Tracks, REW API, Helix, die Review-Methode, Intake …)
    ├── knowledge/      gesammelte Auto- und DSP-Profile (cars/, dsp/)
    ├── rew_tool/       Brücke zur REW API, Analyse, Zielkurven-Generierung, versionierter Zustand
    ├── scripts/        Kritiker/Berater-Kanal-Wrapper (Gemini, Claude, Codex)
    └── curves.html     Zielkurven-Visualisierer
```

Die unabhängige Review-Methode (Kritiker/Berater/Schiedsrichter, Anti-Anchoring) ist als `references/core/review-loop.md` gebündelt.

Eine separate, zustandslose Web-Chat-Version der Methode, ganz ohne lokale Installation, liegt im Branch [manual_step-by-step](https://github.com/ayukhno/autosound-tuning-skill/tree/manual_step-by-step).

## Deine Erfahrung beitragen

Der Skill lernt aus jeder Abstimmung: Er sammelt dieses Feedback direkt im Terminal, während du arbeitest, nicht über ein Formular. Zum Abschluss, sobald du mit dem Klang zufrieden bist, fragt er, was geholfen hat, was nicht passte und welche DSP-/Auto-Eigenheit dir begegnet ist. Mit **deiner ausdrücklichen Zustimmung** bietet er dann an, die *verallgemeinerbaren* Erkenntnisse zu teilen, um die gemeinsame Methode und die `knowledge/`-Bibliothek wachsen zu lassen.

Er erfasst **nur Methode und Geräteklassen**: Innenraumverhalten, DSP-/Geräteklasse, welche Techniken funktioniert haben. **Niemals persönliche Daten, niemals vollständige Messungen;** du siehst genau, was geteilt wird, und stimmst pro Punkt zu. Bestätigte Erkenntnisse werden mit Namensnennung eingearbeitet.

## Unterstützung

Der Skill ist **kostenlos und offen** (CC BY-SA). Wenn er geholfen hat und du Danke sagen möchtest, gibt es zwei freiwillige Kanäle:

💜 **[GitHub Sponsors](https://github.com/sponsors/ayukhno)** · ☕ **[Monobank-Spendenkasse](https://send.monobank.ua/jar/8wThVcodjm)** (Apple Pay, Google Pay, ...)

Ein Tippen, kein Konto; die Seite akzeptiert auch Karten — Apple Pay, Google Pay, Visa, Mastercard.

## Lizenz

[CC BY-SA 4.0](LICENSE): nutze, passe an, teile; halte Ableitungen offen und nenne die Quelle. Es ist ein Methoden-/Wissenswerk, daher hält Share-Alike die gesammelte Erfahrung der Community offen.
