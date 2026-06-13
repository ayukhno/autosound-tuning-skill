# Helix DSP Ultra S — заповнений DSP-чеклист (intake §4)

Готові відповіді на capability-чеклист `project-intake.md §4`. Деталі — у трійці референсів: `helix-vcp-workflow.md` (архітектура/gain/AKM) · `helix-eq-export.md` (обмін EQ) · `helix-phase-allpass.md` (фаза).

| Питання | Helix DSP Ultra S |
|---|---|
| Шари обробки | **2: VIRTUAL (групи Front L/R, Center, Rear; Link L+R) + OUTPUT** (пер-канальний) → архітектура base+voicing працює повністю; RealCenter тягне сигнал з virtual |
| EQ | **30 смуг/канал**, типи PK / LS_Q / HS_Q + **AP1/AP2** (all-pass, кілька дозволено). **Імпорт файлом ✓** — формат Audiotec-Fischer (REW Equaliser = «Audiotec-Fischer») → ніколи не вводити руками (банк не видно весь одразу) |
| Кросовери | BE2-8 / BW1-8 / LR2-8; HP/LP незалежні per channel; точність до 0.01 Гц |
| Затримки / полярність / фаза | Delay per channel (мс, дрібний крок); Polarity NORM/INV per channel; **Phase 0–360°** = all-pass 2-го порядку на частоті кросовера (для саба — від LPF), у EQ-банку не видно; **не застосовується до мідбаса** (опора); порядок зведення: мідбас → саб → СЧ → ВЧ |
| Пресети | Кілька; ⚠️ **перемикання може тихо скинути ВХІД на іншу карту** — перевіряти вхід після кожного перемикання (Pre-session №4) |
| Входи | RCA/LineIN · оптика S/PDIF · BT HD (модуль) · USB-карти розширення; **ISA** (Input Signal Analyzer) = кліп-чек у реальному часі |
| Gain staging | Виходи до **8V** → типово всі Output на **−6 dB** (≈4V під більшість підсилювачів); принцип «мін. гейн підсилювача + макс. рівень DSP» |
| Native rate | **96 кГц** — основний мік-риг міряти на ньому |
| Конфіг-файл | `.pct6` — бінарний/шифрований, RESTORE-only (не парситься) → бекап-мапа обов'язкова (`naming-and-structure.md §4a`); версія PC-Tool файлу ≠ наш `vN` |
| Софт | PC-Tool **Windows-only** (на Mac → Parallels; кур'єрський крок = EQ-експорт через спільну папку) |
| Інше | DAC-фільтр AKM (SQ-реко: Short Delay Slow Roll Off); FX/Virtual X впливає на замір (суфікс `FX` у назвах) |

## Перенос EQ — два шляхи

1. **Канонічний (Helix): файл-імпорт** Audiotec-Fischer → `helix-eq-export.md`. Перевага: у REW одразу видно вплив фільтрів на криву.
2. **Альтернатива (і шлях для DSP без імпорту): REW-EQ-CopyPaste-Assistant** (github.com/IvanBakhmutov/REW-EQ-CopyPaste-Assistant) — Windows/PowerShell-помічник: «Copy» у EQ-секції REW → тулза конвертує кліпборд у keystroke-послідовності і сама вбиває смуги у вікно DSP-софта (клік на першу смугу → авто-ввід). **30+ платформ**: Musway TUNEST_PC (перевірено автором скіла), ESX, Zapco, Goldhorn, Ground Zero, Nakamichi-K тощо. Claude може готувати фільтр-пакет для копіювання так само, як готує Audiotec-Fischer файл (через REW або `rew_tool`).
