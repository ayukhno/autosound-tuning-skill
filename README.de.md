# Autosound Tuning Skill

🇬🇧 [English](README.md) · 🇩🇪 **Deutsch** · 🇵🇱 [Polski](README.pl.md) · 🇺🇦 [Українська](README.uk.md) · ❓ [FAQ](FAQ.md) · <img src="assets/icons/roadmap.svg" width="14" height="14" valign="middle" alt="Roadmap" /> [Roadmap (EN, Entwurf)](ROADMAP.md)

**In einem Satz:** ein Claude-Skill, der dich zu klarem, transparentem, ausgewogenem Klang in *deinem* Auto führt. Er bringt das ganze Handwerk auf dein konkretes Setup, liest deine REW-Messungen und hilft dir, jede Änderung zu wählen.

- **Arbeitet mit REW**: holt Messungen über die API, schreibt berechnete EQ-Filter zurück in REW, von wo du sie in dein DSP exportierst
- **Diagnostiziert, bevor korrigiert wird**: ermittelt EQ-fähige Frequenzen, akustische Reflexionen (Phasenauslöschungen) und Verzerrungsgrenzen jedes Treibers aus deiner Grundmessung, bevor eine Weichen- oder EQ-Änderung vorgeschlagen wird
- **Kennt das Handwerk**: Zielkurven, Abstimmpraktiken, ein Schritt-für-Schritt-Prozess
- **Test-Tracks**: worauf zu achten ist und auf welchem Track (Beschreibungen, kein Audio)
- **Lernt dein Setup**: sammelt Wissen über Auto und Geräte, nur mit deiner Zustimmung

> [!CAUTION]
> KI kann sich bei Zahlen irren. Prüfe Trennfrequenzen, Flankensteilheiten und EQ-Werte in deinem DSP immer manuell nach, bevor du die Stummschaltung aufhebst, besonders bei Hochtönern, und starte bei niedriger Lautstärke.

## Inhalt

- [Für wen & Warum](#für-wen--warum)
- [Wie echte Arbeit und Synergie zwischen verschiedenen KIs aussieht](#wie-echte-arbeit-und-synergie-zwischen-verschiedenen-kis-aussieht)
- [Erste Schritte](#erste-schritte)
- [Empfohlene Modelle, Modi & meine Erfahrung](#empfohlene-modelle-modi--meine-erfahrung)
- [Vollständiges Setup & FAQ](#vollständiges-setup--faq)
- [Was hier drin ist](#was-hier-drin-ist)
- [Deine Erfahrung beitragen](#deine-erfahrung-beitragen)
- [Unterstützung](#unterstützung)
- [Lizenz](#lizenz)

## Für wen & Warum

* **Für wen:** Für alle, die den Sound im Auto aufbauen und dieses Handwerk lernen. Es ist dein Exoskelett: Es trägt das Wissen und die Erfahrung des Handwerks, du bringst die Ohren und die Hände am DSP mit.
* **Warum:** Abstimmen ist eine Lawine: zu viele Methoden, Parameter und Faustregeln, um sie im Kopf zu behalten, und man verliert sich leicht in einem Detail und damit das Gesamtbild. Der Skill ist dein Navigator: Er hält das Wissen bereit, weist auf die wenigen Änderungen hin, die wirklich zählen, und behält den Kompromiss zwischen Bühnenabbildung und tonaler Balance im Blick. Dein Ohr ist der letzte Richter.

Er deckt eine komplette Abstimmung ab: von einem neuen Projekt über Frequenzweichen, Laufzeitkorrektur, Phase, kanalgetrennten und summierten EQ und die Bühnenabbildung bis hin zum Voicing nach Geschmack — plus die optionalen räumlichen Ebenen (ein komplementäres **Center-Fill** und ein differenzielles **Rear-Fill**, beides feldvalidierte Rezepte). Jede Änderung durchläuft eine **Generator ↔ Kritiker ↔ Schiedsrichter**-Review-Schleife: eine KI schlägt vor, eine andere widerspricht, du entscheidest.

## Wie echte Arbeit und Synergie zwischen verschiedenen KIs aussieht

Drei Stimmen: **du** auf dem Hörplatz, **Claude**, der den Prozess führt, **Gemini**, das jeden Schritt hinterfragt.

> **Du (Schiedsrichter):** Der Kontrabass dröhnt ein bisschen. Und als ich die Delays nach Gehör verschoben habe, klang der Bass besser — sollen wir meine Werte eintragen?
>
> **Claude (Generator):** Erst gegen frische Messungen geprüft: deine Delays sind bereits optimal — dein Ohr mochte etwas anderes. Die wahren Übeltäter sind zwei schmale Türresonanzen und eine zu laute linke Seite. Ich schlage drei chirurgische Schnitte vor.
>
> **Gemini (Kritiker):** Einwand: einer dieser Schnitte liegt mitten im Übergangsbereich der Weiche — er kann die Summation dort stören.
>
> **Claude:** Auf den Messungen geprüft — dieser Übergang wird dadurch sogar *besser*. Aber dein Zweifel hat mich genauer hinschauen lassen, und du liegst richtig: es ist nicht nur der Tiefmitteltöner, der Mitteltöner ist dort auch zu laut. Überarbeiteter Plan: jeder Treiber bekommt seinen eigenen Schnitt.
>
> **Gemini:** Jetzt einverstanden.
>
> **Du:** Eingetragen. Das Dröhnen ist weg… aber der Subwoofer spielt jetzt von hinten!
>
> **Claude:** Mein Fehler — zwei meiner Filter überlappen sich und schneiden tiefer als beabsichtigt. Einer wird abgeschwächt.
>
> **Du:** Der Bass ist wieder vorn — aber er sitzt tief. Ich will ihn oben auf der Windschutzscheibe, wo er vorher war.
>
> **Claude:** Der alte Defekt war es, der das Bild oben gehalten hat. Wir bringen den Defekt nicht zurück — stattdessen eine sanfte, symmetrische EQ-Anhebung auf beiden Mitteltönern, damit die Höhe zurückkehrt, ohne die Schieflage.
>
> **Du:** …Der Bass sitzt auf der Motorhaube! So lassen.

Etwa vierzig Minuten von „es dröhnt" bis „der Bass sitzt auf der Motorhaube" — ein Problem, das sonst Wochen forumsgeleiteten Ausprobierens frisst. Jeder Teilnehmer erkannte etwas, das die anderen übersehen hatten, und die Schleife löste alles davon. Die vollständige technische Version, mit jeder Zahl: [die Fallstudie](case-study-mode-a-bass-2026-07-15.md).

**Die Mathematik dahinter** — eine Skript-Bibliothek, die riesige Datenmengen lokal verarbeitet und dabei keine Modell-Tokens verbrennt:

- **Eine Innenraum- und Einbau-Fehlerkarte, erstellt vor jedem Tuning** — Türresonanzen, Reflexionen und L/R-„Taschen", die kein Stereo-EQ füllen kann, werden aus den ersten Messungen kartiert — so plant der EQ *um den Innenraum herum*, statt gegen ihn zu kämpfen;
- **Mehrskaliges Kurvenlesen** — jede Kurve wird auf drei „Distanzen" gelesen (Trend → Form → Feinstruktur), und jeder Befund geht an das Werkzeug, dem er gehört: Voicing, Verifikation, ein chirurgischer Schnitt oder „lass es, das ist der Raum";
- **Jitter-robuste Phasensummation** — Korrekturen an Weichenübergängen werden unter kleinem Delay-/Pegel-Drift bewertet, damit sie die reale Welt überstehen, statt nur an einem Rasierklingen-Optimum zu gewinnen;
- **Hardware-verifizierte Filtermodelle** — jeder vorgeschlagene EQ/All-Pass wird an deinen *gemessenen* Antworten simuliert, bevor du ihn einträgst;
- **Ein Excess-Phase-„Boost-Fähigkeit"-Gate** — unterscheidet eine füllbare Senke von einer Interferenz-Auslöschung: kein Treiber muss je gegen die Physik kämpfen;
- **Vier-Schätzer-Ankunftstriangulation** — vier unabhängige Zeitmessungen müssen übereinstimmen, bevor ein Delay angefasst wird;
- **Grundton-bewusstes Verzerrungslesen** — THD-Spitzen werden gegen den Pegel des Grundtons geprüft, damit eine Rauminterferenz nie als defekter Treiber fehldiagnostiziert wird.

## Erste Schritte

Dieser Skill läuft als Plugin für **Claude Code** (den offiziellen Terminal-Agenten von Anthropic). Falls du ihn noch nicht hast, findest du unten in der FAQ Copy-paste-Installationsschritte für macOS/Windows; eine bezahlte Claude-Subscription ist erforderlich, die Kostenwege stehen in der FAQ. Dort steht auch, [warum eine volle Sitzung weniger Tokens braucht, als man erwarten würde](FAQ.md#why-a-full-session-uses-fewer-tokens-than-youd-expect).

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

**Start mit Gemini als Fahrer:** noch nicht ganz so schnell wie mit Claude Code, zumindest bisher. Es gibt keinen Plugin-Installer dafür, aber der schnellste Weg ist, eine agentische Gemini-Sitzung (Antigravity CLI oder ein beliebiges Gemini-Setup mit Datei- und Shell-Zugriff) direkt auf das Repository anzusetzen und zu bitten:

> Clone https://github.com/ayukhno/autosound-tuning-skill, read `skills/autosound-tuning/SKILL.md`, and follow that method as your operating instructions for this session.

Mehr dazu in der FAQ.

## Empfohlene Modelle, Modi & meine Erfahrung

Der Skill unterstützt zwei Arten, ihn zu betreiben, nach Zuverlässigkeit geordnet. Wähle danach, wie wichtig diese Abstimmung ist und wie viel Aufwand du in die Einrichtung stecken willst:

| Modus | Einrichtung | Zuverlässigkeit | Kompromiss |
| :--- | :--- | :--- | :--- |
| **A: Claude + Gemini** | Claude führt (Sonnet 5 / Fable 5), Gemini prüft (eine Pro-Stufe — aktuell 3.1 Pro — für schwierige akustische Entscheidungen, Flash für Routine) | Höchste | Zwei KIs einzurichten; fängt mehr ab, langsamer pro Entscheidung |
| **B: Solo-Betrieb (Claude oder Gemini)** | Ein Modell führt und prüft sich selbst; Eskalation auf eine stärkere Stufe bei schwierigen Frequenzweichen-Entscheidungen (Claude Opus 4.8 oder eine höhere Gemini-Stufe) | Niedriger, hängt vom gewählten Modell ab | Nur eine Perspektive; Gemini solo liefert mutige, unkonventionelle Vorschläge, deren Zahlen aber von Hand geprüft werden müssen |

**Meine eigene Erfahrung bisher** (das ist bisher nur meine eigene Erfahrung; sobald mehr Leute damit abgestimmt haben, soll das hier die Erfahrung der Community widerspiegeln, nicht nur meine):

* **Claude führt, Gemini prüft (Modus A):** stabil, bewegt sich aber in kleinen Schritten, was etwas langsam wirken kann. Du musst mindestens für Claude bezahlen. Kostenloses Gemini funktioniert auch, stößt aber manchmal an seine Grenzen. Noch etwas, das mir aufgefallen ist: Sonnet ist zuverlässig, aber vorsichtig, und hält oft an, um Dinge zu erfragen, die Opus meist selbst entscheidet, schneller. Dafür geht Sonnet sparsamer mit Tokens um, sodass man seltener an die Nutzungslimits stößt.
* **Gemini führt, mit Claude oder einem stärkeren Gemini-Modell als Prüfer:** deutlich schneller. Nach zwei vollständigen Messrunden hatte ich bereits eine erste funktionierende Version. Später in der Sitzung kann es aber anfangen zu halluzinieren oder frühere Entscheidungen zu vergessen, bis zu dem Punkt, an dem ich zurück zu Claude wechseln wollte. Ich habe das nicht mit kostenlosem Gemini probiert, wegen der Limits — um sie aufzuheben, brauchst du ein bezahltes Google-Cloud-Abrechnungskonto (die [Kostenwege in der FAQ](FAQ.md#subscription-options-quotas--budgets-as-of-july-2026) decken die aktuellen Einzahlungs-/Gratisguthaben-Details ab, die sich oft ändern). Wenn du ohnehin für API-Zugriff zahlst, kommt Modus A insgesamt günstiger.
* **Die manuelle Schritt-für-Schritt-Version (ohne lokale Skripte):** funktioniert, aber der Copy-paste-Prozess ist nervenaufreibend. Man muss aufpassen, dabei nichts zu verlieren. Nach einer vollen Sitzung mit echtem Gedächtnis zwischen den Nachrichten kostet es Überwindung, dahin zurückzukehren.
* **Welches Modell bisher am zuverlässigsten als Fahrer ist:** **Claude Opus** hat bisher die stabilsten Ergebnisse geliefert. **Sonnet 5** funktioniert, wirkt in dieser Rolle aber bisher weniger sicher — seine Entscheidungen sollte man vorerst genauer prüfen. **Fable 5** hat die besten Ergebnisse aller Modelle erzielt: Es hat den Skill auditiert und überarbeitet, während es eine vollständige Abstimmungssitzung durchführte (siehe [audit-fable-2026-07-11.md](audit-fable-2026-07-11.md)), und dann eine zweite volle Sitzung im Auto nach den vereinfachten Regeln gefahren — dieser Aufbau ist aktuell mein klanglich bestes Ergebnis. **Gemini** hat mit zunehmender Komplexität der Prozessregeln etwas an Leistungsfähigkeit eingebüßt; nachdem das Audit sie vereinfacht hat, hat sich Gemini 3.1 Pro in der Rolle des **Kritikers** erneut bewährt, während Gemini als *Fahrer* unter den neuen Regeln noch nicht verifiziert ist — Rückmeldungen aus der Community sind hier willkommen.

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

▶ **[Öffne den Zielkurven-Visualisierer online](https://ayukhno.github.io/autosound-tuning-skill/curve-visualizer.html?lang=de)** (oder öffne `skills/autosound-tuning/curves.html` lokal) — ziehe deine eigene Kurve hinein oder eine Standardkurve vom [Nono Tuning Tool](https://nonotuningtool.com), rechtsklicke auf einen Punkt im Diagramm für den Frequenzcharakter-Guide, und vergleiche Kurven direkt nebeneinander. Es ist eine einzige eigenständige Datei (funktioniert offline) — mit **Speichern unter** im Browser behältst du deine eigene Kopie; die integrierten Kurven und der Drag-and-drop-Import funktionieren weiterhin.

Die unabhängige Review-Methode (Kritiker/Berater/Schiedsrichter, Anti-Anchoring) ist als `references/core/review-loop.md` gebündelt; die [Fallstudie](case-study-mode-a-bass-2026-07-15.md) zeigt sie an einem echten, schwierigen Fall in Aktion.

Eine separate, zustandslose Web-Chat-Version der Methode, ganz ohne lokale Installation, liegt im Branch [manual_step-by-step](https://github.com/ayukhno/autosound-tuning-skill/tree/manual_step-by-step).

## Deine Erfahrung beitragen

Der Skill lernt aus jeder Abstimmung: Er sammelt dieses Feedback direkt im Terminal, während du arbeitest, nicht über ein Formular. Zum Abschluss, sobald du mit dem Klang zufrieden bist, fragt er, was geholfen hat, was nicht passte und welche DSP-/Auto-Eigenheit dir begegnet ist. Mit **deiner ausdrücklichen Zustimmung** bietet er dann an, die *verallgemeinerbaren* Erkenntnisse zu teilen, um die gemeinsame Methode und die `knowledge/`-Bibliothek wachsen zu lassen.

Er erfasst **nur Methode und Geräteklassen**: Innenraumverhalten, DSP-/Geräteklasse, welche Techniken funktioniert haben. **Niemals persönliche Daten, niemals vollständige Messungen;** du siehst genau, was geteilt wird, und stimmst pro Punkt zu. Bestätigte Erkenntnisse werden mit Namensnennung eingearbeitet.

## Unterstützung

Der Skill ist **kostenlos und offen** (CC BY-SA) — und bleibt es; nichts ist hinter einer Bezahlung versteckt. Wenn er geholfen hat und du Danke sagen möchtest, gibt es zwei freiwillige Kanäle:

💜 **[GitHub Sponsors](https://github.com/sponsors/ayukhno)** · ☕ **[Monobank-Spendenkasse](https://send.monobank.ua/jar/8wThVcodjm)** — ein Tippen, kein Konto; akzeptiert Apple Pay, Google Pay, Visa, Mastercard.

## Lizenz

[CC BY-SA 4.0](LICENSE): nutze, passe an, teile; halte Ableitungen offen und nenne die Quelle. Es ist ein Methoden-/Wissenswerk, daher hält Share-Alike die gesammelte Erfahrung der Community offen.

Code und Skripte (`rew_tool/`, `scripts/` und andere .py/.sh-Dateien) stehen unter der [MIT-Lizenz](LICENSE-CODE). Assets Dritter sind in [LICENSES/NOTICE.md](LICENSES/NOTICE.md) aufgeführt.
