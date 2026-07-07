# Autosound Tuning Skill

🇬🇧 [English](README.md) · 🇩🇪 [Deutsch](README.de.md) · 🇵🇱 **Polski** · 🇺🇦 [Українська](README.uk.md) · [FAQ](FAQ.md)

**W jednym zdaniu:** skill dla Claude, który prowadzi cię do **czystego, przejrzystego, zrównoważonego brzmienia** w *twoim* aucie — wnosi całe rzemiosło do twojego konkretnego zestawu, czyta twoje pomiary z REW i pomaga wybrać każdą zmianę.

- 📊 **Współpracuje z REW** przez API — pobiera pomiary, wgrywa filtry EQ z powrotem
- 🎯 **Zna rzemiosło** — krzywe docelowe, praktyki strojenia, proces krok po kroku
- 🎧 **Ścieżki testowe** — czego słuchać i na której ścieżce (opisy, nie audio)
- 🚗 **Uczy się twojego zestawu** — gromadzi wiedzę o aucie i sprzęcie, tylko za twoją zgodą

## Pierwsze kroki

Ten skill działa jako wtyczka do **Claude Code** (oficjalnego agenta terminalowego od Anthropic).

### 1. Szybka instalacja

Uruchom poniższe polecenia w aktywnej sesji Claude Code **jedno po drugim** (nie kopiuj i nie wklejaj ich razem):

```bash
/plugin marketplace add ayukhno/autosound-tuning-skill
```

```bash
/plugin install autosound-tuning
```

```bash
/reload-plugins
```

*Następnie rozpocznij strojenie, mówiąc:* **"tune a new car from scratch"** (lub po polsku: *"nastrój nowe auto od zera"*).

### 2. Kompleksowa konfiguracja i FAQ

Potrzebujesz pomocy w konfiguracji Claude Code, uruchomieniu na systemie **Windows**, konfiguracji **Gemini Critic** lub wyborze mikrofonu pomiarowego?

👉 Zajrzyj bezpośrednio do naszego wyczerpującego **[FAQ.md](FAQ.md)**.

---

## Co tu jest

```
autosound-tuning-skill/        wtyczka Claude Code
└── skills/autosound-tuning/    skill
    ├── SKILL.md        punkt wejścia — mapa procesu, cykl życia sesji, role
    ├── references/     dokumenty na żądanie (fazy, diagnostyka, EQ, filtry, scena,
    │                   ścieżki testowe, REW API, Helix, metoda recenzji, intake …)
    ├── knowledge/      zgromadzone profile aut i DSP (cars/, dsp/)
    └── scripts/        przykładowe narzędzia kanału Krytyka (opcjonalne)
```

Jeden skill — niezależna metoda recenzji (Krytyk/Doradca/Arbiter, anti-anchoring) jest dołączona jako `references/core/review-loop.md`.

## Dla kogo i Dlaczego

* **Dla kogo:** Dla tych, którzy budują dźwięk w samochodzie i uczą się tego rzemiosła. To twój egzoszkielet, który za pomocą twojego słuchu i działań (tam, gdzie nie ma bezpośrednich interfejsów oprogramowania) zarządza wiedzą i doświadczeniem, strojąc car audio twoich marzeń.
* **Dlaczego:** Strojenie to lawina — zbyt wiele metod, parametrów i reguł, by utrzymać je w głowie, i łatwo zanurzyć się w jednym szczególe i zgubić cały obraz. Skill jest twoim nawigatorem: trzyma wiedzę, wskazuje te kilka zmian, które naprawdę się liczą, i utrzymuje w polu widzenia kompromis między sceną a balansem tonalnym. Twoje ucho jest ostatecznym sędzią.

Obejmuje pełne strojenie — od nowego projektu przez zwrotnice, korekcję czasową, fazę, EQ kanałowy i sumaryczny, budowę sceny aż po voicing pod własny gust — sterowane pętlą recenzji **Generator ↔ Krytyk ↔ Arbiter**.

## Dzielenie się doświadczeniem

Skill uczy się z każdego strojenia — i zbiera ten feedback wprost w terminalu, gdy pracujesz, a nie przez formularz. Na zakończenie (gdy jesteś zadowolony z brzmienia) pyta, co pomogło, co było nie tak, i o każdą osobliwość DSP/auta, na którą trafiłeś — następnie, **za twoją wyraźną zgodą**, proponuje podzielić się *uogólnialnymi* wnioskami (aby rozwijać wspólną metodę + bibliotekę `knowledge/`).

Zbiera **tylko metodę + klasy sprzętu** — zachowanie kabiny, klasę DSP/sprzętu, które techniki zadziałały. **Nigdy danych osobowych, nigdy pełnych pomiarów;** widzisz dokładnie, co jest udostępniane, i decydujesz pozycja po pozycji. Potwierdzone wnioski trafiają do skilla z atrybucją.

## Wsparcie

Skill jest **darmowy i otwarty** (CC BY-SA) i taki pozostanie — nic nie jest zablokowane za płatnością. Jeśli pomógł i chcesz podziękować, jest **dobrowolna skarbonka**, bez żadnej presji:

☕ **[Wesprzyj ten skill — skarbonka Monobank](https://send.monobank.ua/jar/8wThVcodjm)** 🤝

Jedno dotknięcie, bez konta; strona przyjmuje też karty zagraniczne (Apple/Google Pay, Visa/Mastercard).

## Licencja

[CC BY-SA 4.0](LICENSE) — używaj, adaptuj, udostępniaj; zachowaj pochodne otwarte i podaj autorstwo. To dzieło metodyczne/wiedzowe, więc share-alike utrzymuje zgromadzone doświadczenie społeczności otwartym.
