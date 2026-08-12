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

> [!NOTE]
> **2.x ist die stabile Linie.** Sie ist funktional abgeschlossen und wird weiter unterstützt. Eine 3.x-Linie — mit GUI und Installer — ist in Entwicklung; ohne Termine.

> [!TIP]
> **Auszeichnungen & Erfolge**
> Dieser Ansatz ist nicht nur für den reinen Hörgenuss gedacht, sondern auch um zu gewinnen. Er hat seine Wirksamkeit in der Praxis bereits bewiesen und zwei Auszeichnungen eingebracht:
> * **1. Platz in der Klasse EINSTEIGER 5000 beim AYA-Wettbewerb (30.05.2026, Lemgo)**. Dieses Ergebnis wurde durch Diagrammanalysen und Ratschläge von Gemini erzielt.
> * **1. Platz in der Klasse AMATEUR 5000 beim AYA-Wettbewerb (25.07.2026, Horst)**. Ein Sieg in der nächsten Klasse, der mit Hilfe dieses Skills und dem eigenen Gehör errungen wurde.
> 
> <p align="left">
>   <img src="assets/awards/aya-may26-einsteiger5000.jpg" width="100" alt="AYA May 2026 Einsteiger 5000">
>   &nbsp;&nbsp;&nbsp;
>   <img src="assets/awards/aya-jul26-amateur5000.jpg" width="100" alt="AYA Jul 2026 Amateur 5000">
> </p>
> 
> *Hier könnte auch deine Auszeichnung stehen!*

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

Etwa vierzig Minuten von „es dröhnt" bis „der Bass sitzt auf der Motorhaube" — ein Problem, das sonst Wochen forumsgeleiteten Ausprobierens frisst. Jeder Teilnehmer erkannte etwas, das die anderen übersehen hatten, und die Schleife löste alles davon. Die vollständige technische Version, mit jeder Zahl: [die Fallstudie](community-inbox/case-studies/case-study-mode-a-bass-2026-07-15.md).

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

### Auf der 2.x-Linie bleiben

**Du bist bereits darauf, und ein Update verschiebt dich nicht.** Der Marketplace-Eintrag nennt einen exakten Commit statt eines Branches, deshalb kann `/plugin marketplace update` dich nicht über einen Hauptversionswechsel tragen; ein ausdrückliches `/plugin update` bringt dich zu dem Commit, den der Eintrag nennt — 2.8.1.

Der Weg unten ist für alle, die es selbst steuern wollen: ein lokaler Checkout des Branches `2.x`, der 2.x-Korrekturen außerdem sofort übernimmt.

Einmalig im Terminal klonen:

```bash
git clone -b 2.x https://github.com/ayukhno/autosound-tuning-skill.git ~/autosound-2x
```

Danach in der Claude-Code-Sitzung, ein Befehl nach dem anderen:

```bash
/plugin marketplace add ~/autosound-2x
```

```bash
/plugin install autosound-tuning
```

Ein lokaler Pfad wird **referenziert, nicht kopiert** — dieser Checkout *ist* die Plugin-Quelle. `git -C ~/autosound-2x pull` ist also der Weg, 2.x-Fixes zu übernehmen, und nichts hebt dich auf eine neuere Linie, bevor du es selbst entscheidest. Das letzte 2.x-Release trägt den Tag [`v2.8.1`](https://github.com/ayukhno/autosound-tuning-skill/releases/tag/v2.8.1); `git -C ~/autosound-2x checkout v2.8.1` fixiert genau diesen Stand.

Um später zum normalen Kanal zurückzukehren: den lokalen Marketplace entfernen und `ayukhno/autosound-tuning-skill` erneut hinzufügen.

## Empfohlene Modelle, Modi & meine Erfahrung

Zwei Betriebsarten:

| Modus | Aufbau | Verlässlichkeit |
| :--- | :--- | :--- |
| **A: Claude + Gemini** | Claude steuert, Gemini prüft (eine Pro-Stufe für die schwierigen akustischen Entscheidungen) | Am höchsten — zwei Perspektiven, dafür langsamer pro Entscheidung |
| **B: Solo** | Ein Modell steuert und prüft sich selbst | Geringer — eine Perspektive, und die Zahlen sollte man von Hand nachrechnen |

**Womit steuern** — bisher meine eigene Erfahrung; ich hätte gern, dass daraus Erfahrung der Community wird:

* **Opus — die Vorgabe fürs Einmessen.** Es hält eine lange Sitzung zusammen und entscheidet dort, wo ein schwächeres Modell nachfragt. In den kniffligen Kurven mit **Max effort** fahren.
* **Sonnet — nicht für ein komplexes Einmessen.** Vorsichtig, und es verliert den Faden, sobald Fakten über eine lange Sitzung hinweg zusammengeführt werden müssen. Für kurze, klar abgegrenzte Schritte in Ordnung.
* **Fable — für Forschungsaufgaben.** Wo ein neuer Ansatz gesucht und nicht ein bekannter angewandt wird, kamen hier die besten Ideen.
* **Gemini — als Kritiker**, auf einer Pro-Stufe. Als Steuermodell unter den aktuellen Regeln unerprobt; Rückmeldungen willkommen.

**Und das alles ändert sich schnell.** Modelle, Stufen und ihre Stärken verschieben sich von Monat zu Monat — nimm das Obige also als Ausgangspunkt, nicht als Urteil. Probiere selbst, experimentiere, und du wirst finden, was zu deinem Auto und deinem Gehör passt.

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

▶ **[Öffne den Zielkurven-Visualisierer online](https://ayukhno.github.io/autosound-tuning-skill/_curve-visualizer.html?lang=de)** (oder öffne `skills/autosound-tuning/curves.html` lokal) — ziehe deine eigene Kurve hinein oder eine Standardkurve vom [Nono Tuning Tool](https://nonotuningtool.com), rechtsklicke auf einen Punkt im Diagramm für den Frequenzcharakter-Guide, und vergleiche Kurven direkt nebeneinander. Es ist eine einzige eigenständige Datei (funktioniert offline) — mit **Speichern unter** im Browser behältst du deine eigene Kopie; die integrierten Kurven und der Drag-and-drop-Import funktionieren weiterhin.

Die unabhängige Review-Methode (Kritiker/Berater/Schiedsrichter, Anti-Anchoring) ist als `references/core/review-loop.md` gebündelt; die [Fallstudie](community-inbox/case-studies/case-study-mode-a-bass-2026-07-15.md) zeigt sie an einem echten, schwierigen Fall in Aktion.

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
