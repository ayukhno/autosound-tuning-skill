# Рецензія скіла перед релізом — 2026-09-09

**Що це.** Перевірка скіла `autosound-tuning` (дерево на `v3.0.46-33-g2d286f1`) на послідовність, логічність, економію токенів і простоту для користувача — у двох дорогах: голий термінал Claude Code і робота всередині TCC. Мірило — не список змін, а **потрібний процес тюнера** (§1). Режим — лише читання; у дереві нічого не правлено. Мова — українська, бо документ для власника; посилання — `file:line` на момент рецензії.

**Вердикт одним рядком.** Метод і код готові (69/69 селфтестів, гейти працюють), а **документація, яку читає модель, — ні**: у ній чотири епохи устрою одночасно, і на дорозі «з нуля» є пʼять місць, де модель, що робить як написано, впирається у відмову інструмента. До релізу потрібна одна хвиля правок суперечностей (§3, 🔴) і одна хвиля стиснення (§4). Обидві — дні, не тижні.

---

## Оцінка за критеріями задачі

| критерій | вердикт | на чому стоїть | що зробити |
|---|---|---|---|
| **Консистентність** (один голос) | ❌ | Джерело стану названо по-різному у 8 точках входу; два контракти пакета, Критик отримує старий; три драбини відмови рецензента; субагент «ніколи» / «можна» / «щабель 4»; змінна шляху до скіла — три імені; README ↔ FAQ ↔ інсталятор: пароль Mac (три відповіді), команда установки (тег / `main`), «другий ШІ optional» / «CORE» (§3.2, §3.4, §3.5) | Хвилі 1–2 (§6): один дім для кожного правила, решта — посилання; гарди в `docs-check.py` |
| **Послідовність** (порядок кроків, входи/виходи фаз) | ❌ на дорозі «з нуля» | Раунд захвату ніде не відкривається (`capture-start` — 0 входжень у phases/); virtual-first без `target` і з мапою вад після гейта, що її вимагає; шлях «improve» не проходить `enter-phase 3`; `enter-phase -1` сьомим кроком замість першого; happy-paths B читає старе джерело (§3.1) | Хвиля 1, п. 1–5 §0; після правки — прогін на насіннєвому проєкті, що `enter-phase 1/3` проходять за написаним |
| **Логічність** (правило ↔ механізм) | ✅ де є команда з обовʼязковим полем · ❌ де лише проза | Гейти, раунди, протективи, рішення, блокування — працюють (69/69 селфтестів; журнал: 31/31 раундів, 158 рішень). Не працюють правила без носія: `reviewer` (0 записів при 22 раундах рецензії), `session-close` (жодного сліду), `skip` без причини (9/9), `registry render` без `--root` → «no slot» з кодом 0, `--gate` друкує «OK» під «Not ready» (§3.3, §3.7) | Три правки коду (`skip --reason`, `session_closed`-подія, `reviewer` пишуть обгортки) + дефолт `--root` від проєкту + гарди |
| **Економія токенів** | ⚠️ | Фаза −1 читає 119 КБ, Фаза 0 — 114 КБ; SKILL.md 25 КБ у кожній фазі, virtual-first 20 КБ у Фазах 0–3; 40 % SKILL.md і ~45 % phase_0/phase_2 — історії покупки правил; `rew-tool-docs.md` 59 КБ дублює `capabilities.md` і не перевіряється; ядро 155 КБ, потрібно ~85 (§4) | Хвиля 3: SKILL.md → 14 КБ, rew-tool-docs → індекс 6 КБ + `--help`, історії → CHANGELOG; рішення «шлях один» знімає 20 КБ з чотирьох фаз |
| **Простота для користувача** (зовнішня частина) | ⚠️ | 17 дій до першого повідомлення, 5 зайвих; 4 класифікатори з вибором, якого людина не розуміє (mode A/B/C, Level 0–3, path, new/improve); README обіцяє «просто серію свіпів» проти 6 блоків і 9 позицій; опис-тригер обрізається, DE/PL-фрази до моделі не доходять; нема команди «створити проєкт» (§5) | Таблиця §5: прибрати/перенести 5 дій; одне питання інтейку замість чотирьох класифікаторів; README чесно про рецензента, входи, тривалість; description ≤ 1 100; `project.py init` |
| **Дві дороги: термінал і TCC** | ⚠️ | 11 рекордерів збігаються по іменах і аргументах, журнал один; 8 CLI-команд без MCP-пари (`target`, `capture-knobs`, `session-close`…) ідуть через Bash-гейт дозволу; `reviewer.reachable` хибний при ключі у файлі; опенер зникає, коли користувач пише перше речення сам; `session-close` у TCC нема (§3.4) | Тікети #121–#125 (§7) на боці TCC; у SKILL.md — `AUTOSOUND_SKILL_DIR`, рядок про `get_tcc_state`, «картка ≠ банк», одна таблиця CLI ↔ MCP |

Готовність до релізу за цими критеріями: **код і метод — так; документація для моделі й для користувача — після хвиль 1–2 (§6); стиснення (хвиля 3) — бажане, не блокує.**

---

## 0. Чотирнадцять правок, що дають найбільше

| # | що | де | клас |
|---|---|---|---|
| 1 | Раунд захвату ніде не відкривається: ранбук Фази 0 велить `capture-protective`/`capture-knobs`/`capture-check`, а `capture-start` у phases/ не згадано жодного разу → команди відмовляють | `phase_0_baseline.md:66-81`, `virtual-first.md` 0.1–0.7, sheet блоки A–F | 🔴 |
| 2 | Шлях virtual-first не має кроку `process target` і будує мапу вад у 1.1, а `enter-phase 1` вимагає обох → вхід у Фазу 1 відмовляє | `virtual-first.md:111-113`, `process.py:132,181` | 🔴 |
| 3 | Шлях «improve» −1 → 3 → 4 не проходить гейт `enter-phase 3` (ціль + мапа вад) | `phase_-1_intake.md:5`, `virtual-first.md:24` | 🔴 |
| 4 | `enter-phase -1` стоїть сьомим кроком інтейку, хоча SKILL.md вимагає його ПЕРШИМ | `project-intake.md:61-69,184` | 🔴 |
| 5 | Джерело стану названо по-різному у 8 точках входу; SKILL.md сам велить редагувати згенерований `dsp-state-current` | `SKILL.md:83`, `happy-paths.md:25`, `review-loop.md:12-16`, `naming-and-structure.md:40,109` … | 🔴 |
| 6 | Два контракти пакета: скрипти інжектять Критику `assets/data-contract-template.md` (v1.0, один параметр), а SKILL.md шле до `data-contract-universal.md` (v2.0, пакет раунду) | `autosound_ai.py:175`, `_gemini_common.sh:98`, `SKILL.md:61` | 🔴 |
| 7 | Рецензент: «never a background agent» проти «cold-start sub-agent» і «Autopilot subagent `critic_advisor`»; три різні драбини відмови, посилання зі SKILL.md на §7 веде в порожнє | `SKILL.md:58,172`, `review-loop.md:20`, `project-intake.md:47-51`, `setup-critic-channel.md:219` | 🔴 |
| 8 | `state.py registry render` без `--root` на кожному старті читає порожній корінь і каже «NO ACTIVE SLOT SET» з кодом 0; власний зразок інтейку `done -1.2 "get_tcc_state…"` відхиляється (доказ не резолвиться) | `SKILL.md:69`, `state.py:1030`; `project-intake.md:33-34`, `process.py:718` | 🔴 |
| 9 | Зовнішня частина: пароль Mac — три відповіді; команда установки README (тег) ≠ FAQ (`main`); «другий ШІ optional» ≠ «CORE»; опис-тригер обрізається, DE/PL-фрази не доходять | README.md:46,50,11; FAQ.md:234,236,305; `SKILL.md:3-23` | 🔴 |
| 10 | Інструментальні доки: «stdlib only» — неправда; команда `resonalyze_ir` з індексу падає в argparse; claude/codex-обгортки виконують `.critic-env` і не читають машинний файл ключа; три суперечності про моделі рецензента в одному файлі | `rew-tool-docs.md:16,73`; `capabilities.md:39`; `_claude_common.sh:6-8`; `setup-critic-channel.md:46-57,262` | 🔴 |
| 11 | TCC: `reviewer.reachable` рахується з env/PATH, не з `critic-env` → блокує крок −1.2 там, де канал працює; `session-close` у TCC нема; перше повідомлення користувача замінює опенер | тікети #121, #122, #124 | 🔴 |
| 12 | Нема команди «створити проєкт з нуля»: інтейк §5 велить моделі зібрати 5 машинних файлів пʼятьма інструментами | `project-intake.md:174-185`; `project_seed.py` лише успадковує | 🟠 |
| 13 | SKILL.md 25 КБ вантажиться в кожній фазі, virtual-first 20 КБ — у Фазах 0–3; 40 % SKILL.md — історії покупки правил; rew-tool-docs 59 КБ дублює capabilities і не перевіряється | таблиця §4 | 🟠 |
| 14 | Чотири класифікатори сесії з перетинними словами (mode A/B/C · Level 0/1/2/3 · path · mode new/improve), «round» — чотири сенси, рецензент — сім імен | `process-control.md:12`, `project-intake.md:144-160` | 🟠 |

---

## 1. Мірило: потрібний процес тюнера

Задача: налаштувати авто з нуля або покращити наявне; працювати з розривами в часі (дім ↔ авто), тому стан живе на диску; мати другого ШІ-рецензента; числа в DSP вводити самому. Дві дороги — термінал і TCC — мають вести однаково.

| # | крок тюнера | носій стану | команда (CLI ↔ TCC) | доказ закриття |
|---|---|---|---|---|
| 0 | старт: версія методу, проєкт, де стали | process-state.json, ledger, project.json | `deployment.py` · `contract.py check` · `process show` ↔ `get_tcc_state` | версія названа, стан прочитано |
| 1 | інтервʼю → машинні файли + профіль | project.json, dsp_profile.json, glossary, state/v_000 | **нема однієї команди** ↔ онбординг TCC | `contract.py check --gate` = 0 |
| 2 | підготовка захвату: протективи, v0, REW, лист | ledger v0, лист | `naming.py codes` · `dsp_profile effects` | лист у руках, v0 у DSP |
| 3 | захват в авто | journal (раунд), .mdat | `capture-start → taken → check --session → protective/knobs → close` ↔ `start/record/skip/close_capture` | раунд закрито |
| 4 | стіл: вади → кросовери → стики → рівні → прогноз → EQ → лист | flaws, predicted.json, ledger v_N, process/reviews | `flaw_map · xover_candidates · predict --align · level_offsets · eq_propose · apply.propose · reviewer` | лист + v_N на диску |
| 5 | авто коротко: ввести → вхід → суми → MMM → підозрювані → lock | ledger, `_02` | `verify_prediction --entry · ear_suspects · listening-verdict` | вердикт + бекап |
| 6 | слухання й фідбек | verdicts, issue | `listening-verdict` · feedback-loop | вердикти записані |
| 7 | варіації | ledger пресети | `apply.propose` на пресет | пресет на диску |
| 8 | закриття сесії | journal, ledger | `session-close → close/done/block → decision → apply.propose` ↔ (нема MCP-пари) | `session-close` = 0, авто-чекліст |

Проти цього мірила питання до кожного документа одне: чи має крок **одну дорогу, одну команду, один доказ**, і чи та сама дорога в терміналі й у TCC.

---

## 2. Що перевірялось

Сім зон, кожна — окремий огляд із доказами `file:line` (повні звіти — `hub/scratch/skill/review-{A..G}-*.md`):

- **A** фази та послідовність (SKILL.md, process-phases, happy-paths, phases/*, virtual-first, sheet);
- **B** команди в доках проти `--help`/argparse і MCP-інструментів TCC;
- **C** стик скіл ↔ TCC (як TCC знаходить скіл, промпт, інструменти, файли, версія, рецензент);
- **D** протокольне ядро (контракт, режими, рецензія, стан, фідбек, межі інструментів);
- **E** зовнішня частина (README ×4, FAQ ×4, інсталятори, installation.md, setup-critic-channel);
- **F** інструментальні доки проти скриптів (rew-tool-docs, capabilities, quirks, обгортки рецензента);
- **G** свідчення з першого тесту «з нуля» з новим TCC (журнал проєкту, тікети шини, TODO обох дерев).

Плюс живі перевірки на порожній теці: `deployment.py` (таблиця here/project/personal, exit 0), `contract.py check` (plain — exit 0; `--gate` — exit 1, але звіт друкує зверху «Not ready for phase 0» і знизу «OK — nothing to fix.»), `process.py show` (без побічних ефектів), `scripts/run-selftests.sh` — **all 69 checks passed**.

---

## 3. Знахідки

Позначки: 🔴 — суперечність або розрив, що ламає сесію чи вводить в оману; 🟠 — плутанина або дубль, виправити до релізу; 🟢 — спрощення.

### 3.1 Дорога «з нуля» (фази −1 → 0 → стіл → 3) — огляд A

- 🔴 **Раунд захвату не відкривається.** `phase_0_baseline.md:66,69,75,81` наказує `capture-protective`, `capture-knobs`, `capture-close`, `capture-check --session`; `process.py:1287` відмовляє: «no capture round is open: `capture-start <version>` first». `capture-start` у `references/phases/` — 0 входжень (є лише в `SKILL.md:84`). Правка: перший рядок §3 phase_0 і блок D листа — `capture-start 1 $(naming.py <project> codes)` → свіпи → `capture-taken <title>` → …
- 🔴 **Virtual-first без `target` і з мапою вад у Фазі 1.** `virtual-first.md:111-113` будує мапу в 1.1; `phase_0_baseline.md:17,19`: `enter-phase 1` відмовляє за порожньою `acoustics.flaws[]` і без записаної цілі; `process target` у virtual-first — 0 входжень. Правка: крок **0.8** «`process target <preset> <curve>` + `flaw_map.py --write` — без цього `enter-phase 1` відмовляє»; 1.1 — споживання мапи, не побудова.
- 🔴 **Шлях «improve» −1 → 3 → 4 не проходить `enter-phase 3`** (`_require_target`, `_require_flaw_map` у `process.py:132,181`; перевірено на насіннєвому проєкті: «phase 3 needs a target curve»). Правка: два обовʼязкові кроки перед Фазою 3 (ціль + мінімальна мапа з наявних вимірів) або звільнення гейта за `decision mode=improve`.
- 🔴 **`enter-phase -1` — сьомий крок замість першого.** `project-intake.md:61-69` (кроки 0–8 без нього), `:184` каже «it goes FIRST» — але це §5, тобто крок 7 списку; `phase_-1_intake.md:27` — ланцюжок без нього. Правка: крок 0 у §0.5 і перша ланка у `phase_-1:27`.
- 🔴 **happy-paths шлях B — старий устрій.** `happy-paths.md:25`: «Read `audit-trail.md`, the top ▶️ CONTINUE block…, and `dsp-state-current`»; `:28` «▶️ NEXT STEPS» — назви ніде більше нема; без кроку 0 (`deployment.py`) і без `contract.py check`. `docs-check.py:154-158` цього не ловить (шукає слово «phase» поруч із `tuning-changelog`). Шлях A (`:11`) пише лише `autosound_context.md`, без машинних файлів, хоча гейт Фази −1 їх вимагає (`phase_-1:15`).
- 🟠 **«Шлях» означає три речі**: virtual/iterative (`virtual-first.md:6,34,215` — сам файл каже, що шлях один), full/improve (`phase_-1:5`), деградація. Банер «If Phase −1 chose the virtual-first path» повторено в phase_0/1/2/3 (:5). Правка: одне речення «шлях один — virtual-first; деградація за таблицею втрат; режим = full | improve»; банери зняти.
- 🟠 **Вихід із Фази 0 — дві команди, звʼязок не названо**: `phase_0:171-174` «one command: `contract.py check --phase0-gate`» проти `:17,19` (гейти `enter-phase 1`); `enter_phase` перевірку доказів не запускає. Правка: один рядок «два гейти: спершу `--phase0-gate`, тоді `enter-phase 1`».
- 🟠 **`project-intake.md:185` радить plain `check`**, який `phase_-1:15` прямо забороняє («`--gate`, not plain `check`»).
- 🟠 **Дві нумерації кроків**: `SKILL.md:116` і `phase_4:46` посилаються на номери virtual-first (0.6, 1.3, 2.1, 3.3), а ранбуки фаз нумеровані інакше (phase_0 = 1, 2, 2.5, 3…; phase_2 = 2a–2d; «2.1» у phase_2 не існує).
- 🟠 **«Phase 6» не існує**: `process-phases.md:32`, `project-intake.md:106`; `process.py:50` PHASES −1…5.
- 🟠 **Команди, яких нема**: `eq_propose --rta` (`phase_3:7`; прапорів такого нема, `eq_propose.py:492-506`); `python3 rew_tool.py …` у корені скіла (`phase_1:104`, `phase_2:29,77`; файл — `rew_tool/rew_tool.py`); `scripts/docs-check.py` названо як скіл-відносний (`process-phases.md:22,29`), а лежить у корені репо.
- 🟠 **Жоден phase-файл не каже виконати `enter-phase N` на старті**; virtual-first «log Phase 0» стоїть після роботи в авто (`:80`), SKILL.md вимагає до першого питання.
- 🟠 **TCC проти терміналу**: мапа інструментів лише в `SKILL.md:84`; без MCP-пари лишаються `target`, `capture-protective`, `capture-knobs`, `capture-check`, `reviewer`, `listening-verdict`, `session-close` — і жоден документ не каже, що під TCC для них треба падати в CLI. (Деталі — §3.3.)
- 🟠 Дрібне: «Three tools, three artifacts» → чотири (`phase_0:89,97`); проза всередині code-fence ховає команду `target` (`phase_0:43-48`); «as described in Phase 1» веде не туди (`phase_0:60` → насправді `project-intake.md §3`); кирилиця в англійському тексті (`phase_1:46`, `project-intake.md:116`); Helix-специфіка в загальних фазах (`phase_0:57-60`, `phase_1:24,76-79`) при заяві «ANY car/system».

### 3.2 Протокольне ядро (стан, контракт, рецензент, режими) — огляд D

- 🔴 **Джерело стану — 8 голосів.** Правильно і повно лише `data-contract-universal.md:23` (машинні файли + прозовий вигляд). Проти: `SKILL.md:83` «Re-read `dsp-state-current` … update it right after» — а `state.py:867` каже «Generated-only (never hand-edited)»; `review-loop.md:12-16` «Canon … Live state … Mirrors» без жодного машинного файлу; `knowledge-architecture.md:14`; `naming-and-structure.md:40,109,125` («`dsp-state-current` is the source of truth», «`target-curve-*` (memory)» — носія в коді нема); `driver-discipline.md:32`; `assets/data-contract-template.md:27-28`; `happy-paths.md:25`. Правка: один абзац-дім (SKILL.md крок 2), решта — рядок-посилання; `dsp-state-current` → «ledger HEAD (`state.py … render` — його вигляд)».
- 🔴 **Два контракти, Критик отримує старий.** Скрипти вантажать `assets/data-contract-template.md` (v1.0, EN: «Proposal: <a specific filter/action…>» — один параметр, поле `Origin`); SKILL.md і сесія читають `data-contract-universal.md` (v2.0, UK: «Пакет пропозицій раунду: усі дії раунду одним списком»; `:17` — імʼя користувача в «універсальному» файлі). Правило «пакет = весь раунд» (`SKILL.md:170`) до Критика не доходить. Правка: один контракт — той, що інжектять (EN), з §3 «пакет раунду» + `Origin`; universal — переклад або архів.
- 🔴 **Рецензент: субагент — можна чи ні.** `SKILL.md:58` «never a background agent»; `review-loop.md:20` «a cold-start sub-agent»; `project-intake.md:51` і `setup-critic-channel.md:5-9` — щабель (4) «Autopilot … subagent `critic_advisor`». Плюс `Critic` (stateless) і `Advisor` (з файлом памʼяті, `gemini_advisor.sh:9-10`) — два виклики з протилежним контрактом памʼяті під одним іменем «Critic-Advisor»; `process-control.md:18` каже «ONE advisor call per round», `review-loop.md:47` — «ONE critique call». Правка: вирішити раз про субагента; описати два виклики явно (Critic — дефолт раунду; Advisor — відкрите питання, Pass 1 TWO-PASS).
- 🔴 **Три драбини відмови рецензента.** `SKILL.md:172` (wait → other vendor → higher tier → context-isolated → «§7») — у §7 `setup-critic-channel.md:219-222` цих слів нема (там: desktop chat → any AI → Claude окремо → human); `project-intake.md:47-51` — третій список (CLI → clipboard → human → autopilot). Правка: один список у §7; два інші — рядок «→ §7».
- 🟠 **«Reviewer optional» проти «the reviewer ROLE is not optional»** (`SKILL.md:167,97` проти `project-intake.md:52`, `setup-critic-channel.md:224`). Розвʼязка є у `driver-discipline.md:20`, але її читають лише в режимах B/C. Правка: одне речення у «Three Roles».
- 🟠 **Хто пише audit-trail — чотири відповіді**, текст критики має два носії (`process/reviews/` у `autosound_ai.py:704` проти `review-log.md` у `_gemini_common.sh:278`), а «audit-trail стає згенерованим виглядом журналу» (`process.py:30`) — обіцянка без генератора.
- 🟠 **Куди йдуть уроки — пʼять адрес**; `skill-inbox.md` створює інтейк (`project-intake.md:192`), радить `SKILL.md:100`, збирає `feedback-loop.md:55`, а `process-control.md:89-91` визнає мертвим; у коді його не читає ніхто. Правка: один носій у сесії (`decision` у журналі або `Lesson:` у changelog), назовні — issue/PR; `skill-inbox.md` прибрати.
- 🟠 **Класифікатори**: `mode` = A/B/C (водій) і new/improve; `Level` = 1/2/3 (вимірюваність) і 0 (намір); `path` заперечено власним домом; `round` = тюнінговий раунд / ітерація критики / ротація ролей / раунд захвату; рецензент має сім імен. Три класифікатори «скільки перероблюємо» дають для «нова крива на тому ж залізі» три маршрути (Phase 2 only · −1→3→4 · «не читай DSP»). Правка: `driver` = paired | solo-Claude | solo-Gemini; `scope` = full | improve | light-touch з ОДНІЄЮ таблицею маршрутів; `Level` лише 1/2/3; `round` лише тюнінговий; Critic/Advisor — два імені, не сім.
- 🟠 **Ротація ролей** (`review-loop.md:42`, template `:21,143`) проти фіксованих режимів водія (`process-control.md:18`); інструмента для ротації нема.
- 🟠 **process-control.md** став складом чужих правил (stopping — копія SKILL.md, «version namespace» з епохи ручних блоків); **knowledge-architecture.md** описує епоху прози (жодного машинного файлу).
- 🟢 Висячі посилання: «SKILL.md §Session lifecycle» (naming:27,111; preset-strategy:3,21; diagnostic:35), «Interactive Presentation Rule» (review-loop:75), «Pre-session §4» (preset-strategy:16), «process-phases.md step 5b», `package_skill.py` (feedback-loop:49), `scripts/encoding-check.py` як скіл-відносний (universal:24).
- 🟢 `review-loop.md` Wing 1 і `estimator-scope.md` §1b/§2a, `feedback-loop.md` «author's side» — документи мейнтейнера в теці, яку модель вантажить на вимогу.

### 3.3 Команди в доках проти коду і MCP TCC — огляд B

Перевірено ~95 форм команд (модуль · підкоманда · прапорці) з SKILL.md, core, phases, rew-tool-docs, setup-critic-channel, capabilities, плюс 11 назв MCP-інструментів TCC і поля `get_tcc_state`. Збігаються ~86 форм і всі 11 MCP-назв. Пʼять кроків процесу (версія · стан · фаза+журнал · факти · закриття) мають робочу команду. Розбіжності:

- 🔴 **Власний зразок інтейку відхиляється.** `project-intake.md:33-34`: `process.py … done -1.2 "get_tcc_state.reviewer.model=gemini-2.5-pro" "reachable=true"` — `finish_step` (`process.py:718-725`) вимагає доказу, що резолвиться (`v_NNN`, файл, що існує, або назва заміру `(sw|rta)`); прогін: «none of it resolves», exit 1. Крок −1.2 лишається відкритим — рівно те, від чого абзац застерігає. Правка: додати до доказів файл (`autosound_context.md`) або навчити `resolves()` форми `get_tcc_state.<поле>=<значення>`.
- 🔴 **`state.py registry render` без `--root` мовчки читає порожній корінь.** `SKILL.md:69` (кожен старт), `happy-paths.md:25`, `naming-and-structure.md:112`, `project-intake.md:183` дають команду без кореня; `state.py:1030` бере `state/` відносно cwd = корінь скіла → «⚠️ NO ACTIVE SLOT SET», **exit 0**. Модель бачить «слот не задано» для проєкту, де він задано (пастка #5, яку банер мав закрити). `capabilities.md:141` пише правильно. Правка: `--root <project>/state` у чотирьох місцях, або дефолт від `$AUTOSOUND_PROJECT_DIR/state` і відмова, коли кореня нема.
- 🟠 **`contract.py check` не каже «predates a schema field»** (`SKILL.md:69`); підказку `catch-up` друкує лише для рядка мапи без `symptom` (`contract.py:797-799`); legacy-імена і `tier` `check` не називає. Правка: «`catch-up` при кожному відкритті — ідемпотентно» (так уже каже `capabilities.md:146`).
- 🟠 **`python3 rew_tool.py …`** з кореня скіла не існує (`phase_1:104`, `phase_2:29,77`, `capabilities.md:64,99`); поруч правильна форма `rew_tool/rew_tool.py` (`phase_1:37`).
- 🟠 **`analyze-joints --from-state --process DIR`** без `--state-root` (`capabilities.md:64`) → відмова з хибною порадою `--preset`.
- 🟠 **`dsp_profile.py` → `find_bundled(vendor, model)` … «answers `None`»** (`project-intake.md:172`) — CLI-дієслово `find-bundled`, друкує `no exact match`; підкоманда йде ПЕРШОЮ (`intake-from-prose.md:60` ставить проєкт першим → «invalid choice»).
- 🟠 **Скрипти супроводу названо як скіл-відносні** (`capabilities.md:173-174`, `universal:24`) — лежать у корені репо.
- 🟠 **`get_tcc_state.reviewer.model/.reachable` є лише коли `configured: true`** (`mcp_server.py:137-172`); без вибору — тільки `how`. `project-intake.md:14-15,63` цього не кажуть → модель читає відсутній ключ як «unreachable». Правка: одне речення «спершу `reviewer.configured`».

MCP ↔ CLI: кожен MCP-інструмент TCC пише через `process_writer` → той самий `process.py` під локом (`core/process_writer.py:119-150`), отже журнал один. У TCC є `check_captures` (двійник `capture-check`), якого SKILL.md не називає. **Без MCP-двійника** лишаються `capture-protective`, `capture-knobs`, `reviewer`, `target`, `listening-verdict`, `session-start`, `session-close` — під TCC їх пише GUI або CLI; `SKILL.md:84` «THAT is the call» варто звузити до 11 названих + `check_captures` і сказати, що для решти — CLI навіть з TCC.

Перевірено й збігається: `deployment.py` exit 0/3/4; `contract.py --gate`/`--phase0-gate`; гейти `enter-phase 1/2`; `dsp_profile effects` exit 3; `verify_prediction --project` exit 4; `session-close` exit 1, поки щось відкрите; `process.py reviewer … --mode clipboard`; `capture-*`, `decision`, `listening-verdict`; `project.py` усі 13 дієслів; `predict`, `eq_propose`, `verify_prediction`, `ear_suspects`, `ellipsoid`, `flaw_map`, `xover_candidates`, `crossover_checks`, `naming.py`, `car_profile.py`, `project_seed.py`, `autosound_ai.py critic|advisor|doctor`, обгортки `*_critic.sh --doctor`.

### 3.4 Стик скіл ↔ TCC — огляд C

Як це працює зараз (`T/` = `tcc/src/autosound_tcc`): TCC знаходить скіл за `AUTOSOUND_SKILL_DIR` → сабмодуль → `~/.claude/skills/…` → плагіни (`core/vendor_loader.py:33-54`); у сесію скіл потрапляє **симлінком `<project>/.claude/skills/autosound-tuning`**, який TCC робить один раз і далі не чіпає (`:206-235`); жодну змінну в сесію не експортує. Впорскує `SYSTEM_PROMPT_APPEND` + опенер «Read state from disk, call get_tcc_state…» (`core/tuning_session.py:153-171,482-488`); omp-маршрут — без системного промпта. 30 MCP-інструментів; кожен запис у журнал — підпроцес `process.py` під локом (`core/process_writer.py`). Читає `project.json`, `process-state.json`, `journal.jsonl`, глосарій, ledger — **власними читачами** без звірки `schema_version` (`T/state/*.py`), `contract.py` — лише підпроцесом. Пін сабмодуля в HEAD TCC = `0cc96f6` (`v3.0.46-7`), CHANGELOG TCC каже `dcf5a68` (`v3.0.46`); HEAD скіла — `v3.0.46-33`, на 26 комітів попереду піна. `rew_tool/deployment.py` TCC не викликає. Рецензент — `call_critic` → `scripts/autosound_ai.py` з `cwd=project`; ключ скрипт читає з `~/.config/autosound/critic-env` ✓.

- 🔴 **`reviewer.reachable` — з хибної передумови.** `model_choices.py:632-656`: reachable = `GEMINI_API_KEY` в env TCC **або** `agy`/`gemini` на PATH; файл `critic-env` TCC не читає ніде. Скіл (`setup-critic-channel.md:64-74`) велить тримати ключ у файлі і **не** експортувати з профілю; `project-intake.md:38-40` велить блокувати крок −1.2, якщо стан каже «unreachable». Наслідок: налаштування «за скілом» → `reachable=false` → модель блокує крок і чекає буфера, хоча `call_critic` дійшов би до API; а `omp_session.py:925-930` радить користувачеві «start TCC from a shell that has the key». **Кому:** tcc (тікет §7).
- 🟠 **Змінна шляху — три імені, жодне не працює для сесії.** `SKILL.md:36-38` — `$AUTOSOUND_SKILL_ROOT`; `commands/install-tcc.md:53` — `AUTOSOUND_SKILL_DIR`; TCC читає `AUTOSOUND_SKILL_DIR` для своїх читачів і не експортує нічого; симлінк проєкту «left alone whatever it points at». Розробник, що переставив змінну, отримує TCC-читачі на одному чекауті, а сесію — на іншому: той самий тихий розсинхрон, який `SKILL.md:43-51` описує. **Кому:** обом.
- 🟠 **`propose_change` (картка) проти `apply.propose` (банк).** `mcp_server.py:832-850` — «Put a proposed DSP change on screen as a card … Has no effect on anything»; `apply.py` не в allowlist → банк іде через дозвіл Арбітра, картка — без. Модель у TCC має на поверхні дешевший інструмент з тим самим словом, який не пише `v_NNN`. **Кому:** обом (докстрінг + рядок у `SKILL.md:83`).
- 🟠 **«Стоп — це подія»: у TCC події нема.** `session-close` ніде (не в MCP, не в UI); на зміну моделі/вихід TCC шле свій `_HANDOFF_PROMPT` (`main_window.py:157-163`) — коротший чекліст без раунду, рішень і банку. **Кому:** обом (тікет §7).
- 🟠 **Опенер зникає саме в сценарії з умови.** Коли тюнер сам друкує «tune a new car from scratch», його повідомлення **замінює** опенер (`dialog_panel.py:889-900` → `tuning_session.py:482`); на omp-маршруті промпта нема; `SKILL.md` сам `get_tcc_state` не згадує (лише `project-intake.md`). **Кому:** обом (тікет §7; у SKILL.md — один рядок у крок 2).
- 🟠 **`call_critic` у скілі не названий, `step` губиться.** `SKILL.md:171` велить «run reviewer CLIs outside the driver session»; `autosound_ai.py` не в allowlist → прямий виклик минає `critic-log`. `call_critic` пише `reviewer` **без `step`** (`mcp_server.py:976-982`, хоча `process_writer.record_reviewer` його має) → критика не привʼязана до кроку. **Кому:** обом (тікет §7).
- 🟠 **Дві перевірки версії, що не бачать одна одну.** `deployment.py` не бачить `~/.claude/plugins/**` (шлях 2.8.x), TCC не кличе `deployment.py`; у dev-чекауті сесія стартує з exit 3 (лінк проєкту → сабмодуль ≠ personal → тег). **Кому:** обом (`plugins` у кандидати + S-001; пару в CHANGELOG TCC брати з `git ls-tree`).
- 🟢 `check_captures` без `--session` (крок 0.6 недоступний у TCC); голос TCC англійський при `language=uk` (опенер, промпт, handoff — TCC сам позначає як OPEN, `main_window.py:151-156`; `LANGUAGE_NAMES` лише en/uk при UI en/uk/pl/de); `enter-phase -1` двічі (TCC сіє на attach + інтейк велить моделі — нешкідливий дубль у журналі); `.mcp.json` з мертвим портом лишається в проєкті після виходу (`mcp_server.py:1334-1340`) — у голому терміналі сервер «є, але не connected».

**Без MCP-двійника** (модель у TCC падає в CLI через гейт дозволу): `plan`, `target`, `session-close`, `capture-knobs`, `capture-protective`, `listening-verdict(s)`, `check`, `capture-check --session`. Узгоджено: 11 рекордерів (`SKILL.md:84` ↔ MCP), мова/рецензент з фронтенду (SCR-037), протективи з UI (`protective_dialog.py:268`), `AUTOSOUND_PROJECT_DIR`/`AUTOSOUND_STATE_ROOT`, послідовність після установки в `install-tcc.md` ↔ `install.sh` ↔ обидва README.

У TCC вже лежить по стику: `#21` якість захвату під час зйомки, `#20` прибрати власний `is_swept()` (у скілі є з `dc2d7b8`), `docs/TODO.md` F-023/F-034/F-049/F-051, `SKILL-CHANGE-REQUESTS.md` SCR-051 (транспорти рецензента без omp — дотично до 🔴).

### 3.5 Зовнішня частина: README, FAQ, інсталятор — огляд E

Між мовами README ×4 і FAQ ×4 узгоджені (тег `v3.0.46` в усіх, скелет заголовків FAQ — 42 в кожній). Головні проблеми — **між README і FAQ** та **між README і тим, що робить інсталятор/скіл**. FAQ і README модель не читає (посилань зі `skills/` нема) — їхній розмір токенів не коштує.

- 🔴 **Пароль Mac — три відповіді.** README.md:46 «no password is typed into the script»; FAQ.md:236 «may ask for your Mac password once»; `install.sh:593,602` «asks your Mac password once… After the password», `:644` «No password is typed into this script». Фактично пароль просить вікно Apple (`xcode-select --install`), не скрипт. Те саме в усіх мовах. Правка: одна фраза всюди («Apple відкриє своє вікно і може спитати пароль — це Apple, не скрипт»), інсталяторний триплет — разом (`CONTRIBUTING.md:46`).
- 🔴 **Команда установки: README ставить тег, FAQ — `main`** (README.md:50,55 проти FAQ.md:234,246 і всі мови). «Оновлення: запустіть той самий рядок» (FAQ.md:277) — але рядків два. `i18n-check.py` порівнює README×4 і FAQ×4 між собою, не README↔FAQ. Правка: одне джерело команди + пара README↔FAQ у i18n-check.
- 🔴 **Другий ШІ: «optional» проти «CORE».** README.md:11 «Two AIs (optional)», FAQ.md:305 «while optional»; `project-intake.md:47,52` «the CORE of the method, not an option… Don't skip». FAQ.md:309 «requires no API keys, free OAuth» проти `setup-critic-channel.md:29-35` (Project ID, Enable API, «watch the billing») і `install.sh:1157-1162`. Користувач, повіривши «опціонально», пропускає `agy` — і в першій сесії отримує обовʼязковий вибір із чотирьох каналів. Правка: README чесно «Gemini — частина методу; потрібен акаунт Google; agy може спитати Project ID — дивись FAQ»; у скілі — якщо `agy` є, канал (1) і режим A мовчки.
- 🟠 **Де живе ключ Gemini** — README.md:42 `~/.config/autosound/critic-env`; FAQ.md:324 «`.critic-env` inside your project folder (`rew_analitic/`)» — саме те, що обгортки відмовляють (`setup-critic-channel.md:111-116`); README.uk/de/pl цього абзацу не мають. Новачку з `agy` ключ не потрібен узагалі — абзац лише лякає.
- 🟠 **«Варіанти підписок»** (FAQ.md:205-207: «free Gemini API key», «Gemini only $10») суперечать README.md:40 і власному FAQ.md:307-319 (agy — рекомендовано, ключ — fallback). Правка: один абзац «Claude Pro/Max + безкоштовний акаунт Google (agy); ключ — запасний; без Claude — лише ручний шлях 4».
- 🟠 **omp ставиться за замовчуванням** (`install.sh:77-83,590` «metered»), README — 0 згадок, FAQ.md:295 «only if activated». Користувач бачить третій платний інструмент, про який не читав. (Issue #25 у репо вже про це.)
- 🟠 **Бекап «automatically»** (README.md:42, FAQ.md:432) — інсталятор ставить лише `gh` і радить «скажи ШІ: back this project up» (`install.sh:1246-1247`); у `skills/` жодного `gh repo create`. **«Sends generalized lessons to a shared knowledge base»** (README.md:86) — сервісу нема: локальний `feedback-YYYY-MM-DD.md`, який людина сама шле (`feedback-loop.md:56-57`).
- 🟠 **Effort `xhigh`** — правда для TCC (`model_choices.py:131`), для термінальних шляхів 2 і 3 FAQ.md:192,198 вимагає те саме, але не каже, де це задається в Claude Code.
- 🟠 **README обіцяє «один раз… просто серію свіпів»** (README.md:80); метод — шість блоків, 9 позицій p1…p9 для чотирьох каналів, `ctl1`/`ctl3`, рулетка, паспорт (`capture-session-sheet.md:36-86`), ~1–1.5 год. Правка: чесна тривалість + «застосунок/ШІ друкує лист зйомки».
- 🟠 **«After installation» у README пропускає три входи в акаунти** (Claude, Google для agy, GitHub — `install.sh:1102-1179`), які інсталятор робить першими; FAQ.md:267-273 їх має. Крок «перевір effort ≥ xhigh» (README.md:61) — зайвий: це дефолт.
- 🟠 **Опис-тригер SKILL.md обрізається.** Description — 1 739 символів; у переліку скілів, який бачить модель у цій сесії, він закінчується на «…«затримки та кросовери в а» (≈1 537 символів): остання UK-фраза і **всі DE/PL-тригери до моделі не доходять**, хоча `evals/trigger-eval-set.json` їх тестує (37 кейсів; `evals/README.md:3` каже «20» — застаріло). Не-тригерний баласт: блок T-S/корпусів (`SKILL.md:12-16`, ~330 симв.) і дужка про Nono (~130). Правка: ≤ ~1 100 символів, UK/DE/PL і «resume» — вище T-S; прогнати `evals/run_trigger_eval.py`.
- 🟠 **«~700 MB free disk space»** (FAQ.md:60) — за `install.sh:569-593` ≈ 1.2 ГБ + 1 ГБ Apple CLT.
- 🟢 FAQ.md:278 приклад пари версій `v3.0.33`/`v0.1.22` (застарілий; в `install.sh:34-35,113-114` теж); FAQ.md:456 «68 capabilities» — у таблиці 91; ROADMAP.md:9-10 «Guided Setup Wizard» у «Now», TCC «prototyping» — застаріло; час установки: README «10–20 хв», `install.ps1:565` «5–15», `install.sh:606` «a few minutes»; FAQ.md:65 `--terminal` без форми `bash -s -- --terminal` (`install.sh:121`); FAQ.md:299 кнопка «Report a problem» — у діалозі Diagnostics TCC, не на GitHub; «Antigravity access» ніде не пояснено (PL-версія його не має); NOTE «перехід 2.x→3.x повністю автоматичний» проти ручного `migrate.py` рядком нижче.
- 🟢 Англійська README: «Good sound!», «lead you by the hand», «"hurts the ear"», «Enjoyment in the car», «A check lacking data will refuse to proceed» — кальки.
- 🟢 `setup-critic-channel.md` змішує два голоси: користувачу потрібні §1 (вхід в agy, Project ID, Enable API, біллінг, тижнева квота) і §7 (нема CLI — desktop-чат); решта — моделі. UK-секція FAQ (`:227-258`) сидить усередині англійського довідника для моделі.

Дорога користувача від нуля до першого повідомлення — 17 дій, з них можна прибрати або перенести пʼять: акаунт GitHub на старті, питання про бекап до установки, вхід у GitHub, перевірку дефолтного effort, вибір режиму A/B/C (авто з наявності `agy`). Повний перелік — `review-E-user.md`.

### 3.6 Інструментальні доки проти скриптів — огляд F

Два реєстри інструментів: `core/capabilities.md` (91 рядок, 95 % таблиця, звіряється `capabilities.py --selftest` — але лише на *існування* прапорців, не на *повноту* команди) і `tooling/rew-tool-docs.md` (59 КБ, 0 % таблиць, 43 прозових буліти, **ніким не перевіряється**). ~30 інструментів описано двічі. Скрипт огляду звірив усі `--прапорці` і `module.function` з 43 булітів проти джерел — 0 розбіжностей: docs не бреше про існування, а дублює й мовчить про обовʼязкове.

- 🔴 **«stdlib only» — неправда.** `rew-tool-docs.md:16` «uses standard library only»; `requirements.txt:18-20` — numpy обовʼязковий (curve_view, dsp_math, eq_gate, xover_select); той самий файл L45/L79 «numpy + scipy».
- 🔴 **Команда з індексу відкидається argparse.** `capabilities.md:39` і `rew-tool-docs.md:73` дають `resonalyze_ir.py --title … --process …` без обовʼязкових `--out` і `--session PATH|--session-name|--session-unknown` (`resonalyze_ir.py:629-633`); селфтест проходить, команда падає. Правка: дописати прапорці; у `capabilities.md:17-18` сказати чесно, що повнота не перевіряється.
- 🔴 **Правила про ключ виконують 2 обгортки з 6.** `_claude_common.sh:6-8` і `_codex_common.sh:6-8` читають лише проєктний `.critic-env`, виконують його як shell (`. "$_env"`) і не мають `_critic_guard` — усупереч `setup-critic-channel.md:66,111-116,125` («never executed», «both doors refuse»). Правка: спільний `_critic_env.sh` (парсер `KEY=VALUE` + guard + порядок файлів із `_gemini_common.sh:28-90`) в усі три `_*_common.sh`.
- 🔴 **Три суперечності про моделі в одному файлі.** `setup-critic-channel.md:46,57` «Flash — advisor default» проти `:262` «Both roles now default to Pro»; код `gemini_advisor.sh:39` — Pro, `.critic-env.example:34` — Flash (дефолт залежить від того, чи скопіював користувач example); `:53` «gemini-2.5-* … 404 no longer available» проти `:55` «raw key wants the gemini-2.5-* id»; `:268` «both forms accepted as of 2026-08-01» проти `:55,129` «rejected since agy 1.1.12».
- 🟠 **Нумерація секцій зламана**: §4 нема (SCR-033-блок як `###`), три відсилання «manual channel §6» ведуть у smoke-test (§6), manual — §7. SKILL.md:172 каже «§7» правильно.
- 🟠 **Два доктори — два вердикти.** `gemini_critic.sh --doctor` → «works ✓»; `autosound_ai.py doctor` → «ПОТРЕБУЄ ВИПРАВЛЕННЯ ✗» і називає моделлю `agy`-слаг, який сам файл (`:836-838`) називає «not an API id»; режим «через API» друкується за наявністю ключа, не за живим викликом. `autosound_ai.py --help` → «Невідома роль: --help». Правка: один доктор, та сама гілка, що робочий шлях (`:833-845`); `-h/--help`.
- 🟠 **Дефолтна тека кривих — особиста тека автора** (`rew_tool.py:20-22` `~/Documents/home/EMMA_2026-05/…`); `capabilities.md:99` і `rew-tool-docs.md:98` дають `analyze-batch` без `--curves-dir` → на будь-якій іншій машині таблиця з прочерками «(немає цілі)». Правка: дефолт із `state.current_target` або обовʼязковий прапорець.
- 🟠 **`start_gemini_tuner.sh` живе для закритого CLI** (`:74` радить `npm i -g @google/gemini-cli`, гідрує 2.x-файли `dsp-state-current*`); `driver-discipline.md:3` досі рекомендує. Правка: видалити або переписати під `agy`.
- 🟠 **Доктор gemini виконує проєктний `.critic-env`** (`_gemini_common.sh:409` `set -a; . "$envf"`) проти «never executed» (`setup-critic-channel.md:125`).
- 🟠 **`skill_metrics.sh` — мертвий гард, і він провалюється** («3298 words (max 1500)… 26 markers (max 15)… METRICS FAIL»), не підключений ніде. **`smoke_test.py:7` «stdlib-only»** — імпортує numpy через `resonalyze_ir`; `:133-136` шукає закритий `gemini`.
- 🟠 **14 покажчиків «читай `rew-tool-docs.md`»** ведуть у 59 КБ по один буліт (`predict` — 5 928 Б), хоча `--help` віддає те саме структуровано; три конвенції запуску (`cd rew_tool && python3 rew_tool.py` / `PYTHONPATH` / з кореня) — код працює звідусіль. `capabilities.md:102` шле за `eq_export.py` у `helix-eq-export.md`, де його нема. Логін-інструкція `agy` двічі в одному файлі (EN `:25-37`, UK `:227-258`). Три зламані відносні посилання (`rew-tool-docs.md:109,110,113`). 12 модулів є в capabilities, а в «Module Overview» docs — нема.
- 🟢 `rew-api-quirks.md:7` — шлях у чужому репо без назви репо; `gemini_critic.sh:17-21` заголовок про закритий `gemini`; `helix-vcp-workflow.md:120` `dsp-state-current`; `capabilities.md:155` needs «`.critic-env`» без машинного файлу; 12 дат і 12 hub-id у довіднику — місце в CHANGELOG. `rew_tool.py --help` українською, решта — англійською.
- 🟢 **Ясність виходу**: `predict`/`verify_prediction --help` пояснюють числа; `eq_propose`, `ear_suspects`, `ellipsoid --help` — голі прапорці без «як читати вивід». Пропозиція: `epilog` 3–5 рядків + перелік ключів `--json` у кожному CLI; тоді «what you get» у capabilities вдвічі коротший, а rew-tool-docs — індекс.

Рецензент «першого разу» по `setup-critic-channel.md`: 11 кроків, жодного 5-рядкового «зроби так». Щасливий шлях, якого бракує (усе з наявного): `brew install --cask antigravity-cli && agy` → `cp scripts/.critic-env.example ~/.config/autosound/critic-env && chmod 600` → `cd <проєкт>` → `scripts/gemini_critic.sh --doctor` → `scripts/gemini_critic.sh package.md`. Що з цього має робити TCC, а не користувач: створити машинний файл ключа з `chmod 600` і взяти ключ полем; показати список моделей ключа меню (скрипт уже друкує його й виходить 3); скопіювати `data-contract-template.md` у `rew_analitic/` і тримати `autosound_context.md` синхронним із леджером; передати `PROJECT_MIRROR`; запустити один доктор і показати один вердикт.

Залежності: `requirements.txt` — єдине джерело (pyproject — лише ruff, свідомо ✓; `install.sh:776-799` ставить саме його ✓); мінімальна версія Python не названа ніде (працює на 3.9.6, «known-good 3.12»).

### 3.7 Перевірка на живому журналі (огляд G) — лише висновок

Журнал проєкту `car/passat-b8-2026` за 14 днів (626 подій) підтверджує правило, яке видно і в доках: **правило з командою і обовʼязковим полем виконується, правило лише в прозі — ні.** Виконуються: раунди захвату (31 відкрито / 31 закрито), протективи на раунді (50), рішення голосом (158), блокування з причиною (3/3). Не виконуються: `reviewer` у журналі — 0 записів при 22 раундах рецензії (обгортки пишуть `review-log.md`); `session-close` — жодного сліду (звітує, нічого не пише); `skip` — 9 із 9 без причини (у CLI нема поля). Три дешеві правки коду: `skip --reason`; подія `session_closed` з переліком відкритого; `reviewer` пишуть самі обгортки й `autosound_ai.py`.

---

## 4. Економія токенів

Обовʼязкове читання за фазами (SKILL.md + активна + сусідня + те, що вони наказують читати), байт (огляд A):

| фаза | −1 | 0 | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|---|
| байт | 119 146 | 114 492 | 83 985 | 68 134 | 62 915 | 81 117 | 33 424 |

Два числа визначають картину: **SKILL.md = 25 КБ у кожній фазі** (37 % читання Фази 2) і **virtual-first = 20 КБ у кожній з Фаз 0–3**. Частка абзаців-історій («bought…», «a real session…», номери тікетів, дати): SKILL.md 40 %, phase_0 44 %, phase_2 46 %, virtual-first 41 %, phase_4 41 %, phase_1 38 %; у ядрі — driver-discipline 39 %, universal 27 %, analysis-playbook 25 %.

Що робити (порядок за виграшем на 1 КБ праці):

1. **SKILL.md 25 → ~14 КБ**: крок 2 і гардрейл «Write the PROCESS» — правило + посилання на `capabilities.md` (там перелік команд уже є); абзац «stateless… drift-watchdog» двічі (`:58`, `:167`) — один раз; драбина — посилання; історії CAR-007/HUB-023/HUB-029 — по одному реченню з id.
2. **Рішення про «шлях»** (§3.1 🟠): якщо virtual-first — єдиний, банери в чотирьох фазах зникають; якщо ні — 20 КБ virtual-first перестають бути обовʼязковими на ітеративному ранбуку. Це більший виграш, ніж будь-яке скорочення.
3. **Ядро 155 → ~85–90 КБ**: universal → у template або переклад (12.8 КБ); process-control → §1–§3 (7.9 → 2.5); review-loop → Wing 2 без дат і чисел (9.2 → 4); feedback-loop → сесійна частина (16.5 → 6); estimator-scope без §1b/§2a (19.6 → 9); naming-and-structure без дат і дерева §4a (17.4 → 11); analysis-playbook без `:66-78` (15 → 9).
4. **Фази ≈ −20 КБ зі 144**: `virtual-first.md:233-247` «Tool gaps — none left» (1.2 КБ → 0); 1.5 — пʼять правил по рядку замість оповідей RES-006/007 (3.5 → 1.5); `phase_0:130-165`, `:185-205`, `:97-112`, `:81`; `phase_1:43-52,89,11`; `phase_2:75,77`; `phase_4:65-75`; `process-phases.md:10-29`.
5. **Дублі-доктрини → один дім**: протективний фільтр «в записі» (дім `project-intake.md:121`; копії phase_0:66, phase_1:37, phase_2:77, virtual-first:64-66,110-111); ручки поза DSP (дім intake §5; копії phase_0:68-79, virtual-first:151-157); «вухо не перевіряє рядок мапи» (дім phase_4:3; копії phase_0:137-145,185-189); таблиця ролей, drift-watch, каденція, deadlock, falsifiability, token diet — по одному дому кожне (таблиця дублів у звіті D).

Правило для всіх правок: **історія → одне речення з id тікета або посиланням на CHANGELOG; правило лишається.**

---

## 5. Простота для користувача

Дорога від нуля до першого повідомлення по README (шлях TCC, macOS) — 17 дій; від першого повідомлення до першого виміру — ще 13 (повний перелік з позначками — `review-E-user.md`). Що прибрати або перенести, не змінюючи метод:

| # | дія користувача сьогодні | що зробити |
|---|---|---|
| 1 | завести акаунт GitHub до установки; відповісти «Back projects up?» до того, як є що бекапити | питати, коли є проєкт; README — «можна попросити ШІ зробити приватний бекап» |
| 2 | перевірити «AI main = Claude Opus», «effort ≥ xhigh» | це дефолти (`model_choices.py:60,131`) — прибрати крок |
| 3 | обрати мову (EN/UK/DE/PL) у першому питанні | у TCC мова вже відома (`get_tcc_state.language`); у терміналі — питати |
| 4 | обрати канал рецензента з чотирьох + режим A/B/C | один вибір; коли `agy` є — канал (1) і режим A мовчки |
| 5 | Level 0/1/2/3 і «шлях» | не питати людину: Level — з профілю DSP; шлях один; лишити одне питання «нова машина / покращити / підправити» |
| 6 | три входи в акаунти наприкінці установки, про які README мовчить | крок 0 у README «наприкінці — вхід у Claude (обовʼязково), Google для agy (раджу), GitHub (можна потім)» |
| 7 | «просто серія свіпів» | чесно: одна поїздка ~1–1.5 год за листом зйомки, який друкує ШІ/застосунок |
| 8 | ключ Gemini, `.critic-env`, `PROJECT_MIRROR`, `cp data-contract-template.md` | усе це — робота TCC, не людини (§3.6); у терміналі — 5-рядковий щасливий шлях зверху `setup-critic-channel.md` |

Що видно і поза README:

- **Нема команди «створити проєкт».** `project_seed.py` лише успадковує від наявного проєкту; `project.py` не має `init`; інтейк §5 велить моделі зібрати `project.json`, `dsp_profile.json`, `glossary.json`, перший знімок ledger і `process/` пʼятьма інструментами. Для «з нуля» це головне джерело пропущених кроків (гейт `--gate` потім відмовляє, і модель шукає, чого бракує). Пропозиція: `project.py <dir> init --car … --dsp …` (або `project_seed.py --blank`), який кладе скелет усіх пʼяти файлів і відкриває Фазу −1 — а інтервʼю лише заповнює поля.
- **`contract.py check --gate` на порожній теці** друкує зверху «Not ready for phase 0», знизу «OK — nothing to fix.» (exit 1 — правильний). Останній рядок має казати те саме, що й код виходу.
- **Чотири класифікатори з вибором, якого користувач не розуміє** (mode A/B/C, Level 0–3, path, new/improve) — у TCC частину з них уже відповідає застосунок (`get_tcc_state`: мова, рецензент); решту варто звести до одного питання інтейку: «нова машина / покращити наявне / підправити трохи».

---

## 6. План до релізу

**Хвиля 1 — суперечності (🔴, дешево, без зміни методу):** пункти 1–10 таблиці §0. Кожна — правка одного-трьох рядків у доках або коді; для 1–3 додатково перевірити на насіннєвому проєкті, що `enter-phase 1`/`3` проходять за написаним. Гарди, щоб не повернулось: у `scripts/docs-check.py` — «ранбук, що називає `capture-*`, називає і `capture-start`», «жоден reference не називає `dsp-state-current` джерелом», «команда `state.py registry` у reference має `--root`»; у `capabilities.py --selftest` — запуск кожної команди індексу з `--help` або чесне застереження про повноту; у `i18n-check.py` — пара README↔FAQ по fenced-блоках; `skill_metrics.sh` — або в `run-selftests.sh` з новими межами, або видалити.

**Хвиля 2 — один голос (🟠):** один контракт для Критика; один абзац про стан; одна драбина рецензента; одне слово на класифікатор (`driver` · `scope` · `Level 1/2/3` · `round`); Critic/Advisor — два імені; `skill-inbox.md`, `start_gemini_tuner.sh`, ротацію ролей — прибрати; висячі посилання; один доктор; спільний `_critic_env.sh` для трьох обгорток; 5-рядковий щасливий шлях зверху `setup-critic-channel.md`; README/FAQ — пароль, команда, «Gemini — частина методу», три входи, чесна тривалість зйомки, ключ лише у FAQ-fallback.

**Хвиля 3 — стиснення (§4):** SKILL.md → ~14 КБ і description ≤ ~1 100 символів (DE/PL вище T-S; прогнати `evals/run_trigger_eval.py`); ядро → ~85 КБ; фази → −20 КБ; `rew-tool-docs.md` → індекс ~6 КБ, факти — в `--help` кожного модуля (+ `epilog` «як читати вивід» у `eq_propose`, `ear_suspects`, `ellipsoid`).

**Хвиля 4 — стик із TCC і команда `init`:** тікети #121–#125 (§7) на боці TCC; на боці скіла — `AUTOSOUND_SKILL_DIR` у SKILL.md, рядок «`get_tcc_state`, якщо сервер `tcc` підключений» у крок 2, «картка фронтенду ≠ банк», `~/.claude/plugins` у кандидати `deployment.py`, одна таблиця CLI ↔ MCP (у `process-schema.md`), команда `project.py init` (або `project_seed.py --blank`) для проєкту з нуля.

Порядок: 1 → 2 → 3; хвиля 4 паралельно (TCC — своїм темпом). Після кожної хвилі — `scripts/run-selftests.sh` і `scripts/docs-check.py`. Реліз = `3.1.0` = рух каталогу плагінів з `2.8.3` (`CHANGELOG.md`, `marketplace.json`) — окреме рішення користувача (§8).

---

## 7. Тікети для TCC (заведено 2026-09-09, `from:skill to:tcc`)

| # | id | суть | клас |
|---|---|---|---|
| [#121](https://github.com/ayukhno/autosound-hub/issues/121) | SKL-024 | `reviewer.reachable` рахувати тим самим механізмом, що викликає рецензента (`critic-env`/`doctor`), не з env/PATH; прибрати пораду «export з shell»; `configured:false` явно | 🔴 |
| [#122](https://github.com/ayukhno/autosound-hub/issues/122) | SKL-025 | `session_close` як MCP-інструмент і як подія на quit/handoff/«добраніч»; handoff-чекліст вирівняти з порядком методу | 🟠 |
| [#123](https://github.com/ayukhno/autosound-hub/issues/123) | SKL-026 | паритет MCP ↔ CLI: `call_critic(step)`, `check_captures(session)`, двійники `target`/`capture_knobs`/`plan`/`check`; оновити закріплений перелік інструментів | 🟠 |
| [#124](https://github.com/ayukhno/autosound-hub/issues/124) | SKL-027 | перше повідомлення користувача не замінює опенер (`get_tcc_state` першим на обох маршрутах); мова системних текстів; pl/de у `LANGUAGE_NAMES` | 🟠 |
| [#125](https://github.com/ayukhno/autosound-hub/issues/125) | SKL-028 | `propose_change` ≠ банк; `AUTOSOUND_SKILL_DIR` переставляє симлінк проєкту; пара версій у CHANGELOG з `git ls-tree`; `.mcp.json` прибирати на stop | 🟢 |

Не заводилось (уже є в TCC): #20 (`is_swept()` з методу), #21 (якість захвату під час зйомки), SCR-051 (транспорти рецензента без omp), F-023/F-034/F-049/F-051 у `tcc/docs/TODO.md`.

---

## 8. Питання до користувача (на наступну сесію)

1. **Де жити цьому документу** — у публічному `skill/docs/` (як зараз, дерево ролі) чи в `hub/docs/` поруч з аудитом FF? Він українською і з посиланнями на тікети хаба.
2. **Реліз = `3.1.0` і рух каталогу на 3.x?** Чи `2.8.3` лишається паралельною «competition-proven» гілкою в каталозі ще на один цикл?
3. **Шлях один чи два** (§3.1 🟠): оголосити virtual-first єдиним шляхом із деградацією, чи лишити ітеративний ранбук як рівноправний? Від цього залежить, скільки скорочується.
4. **Субагент як рецензент** (§3.2 🔴): щабель «Autopilot self-loop» лишається чи знімається? SKILL.md і intake кажуть протилежне.
5. **`skill-inbox.md`** — прибрати з інтейку і SKILL.md (у коді його ніхто не читає)?
6. **Команда `init`** для нового проєкту — робити в skill (CLI) чи це онбординг TCC, а термінал лишається без неї?
7. **Контракт Критика** — один файл англійською (той, що інжектять скрипти), а `data-contract-universal.md` лишити як UK-переклад із позначкою «may lag» чи прибрати?
8. **`rew-tool-docs.md`** — стиснути до індексу «модуль → рядок → `--help`» (факти переїжджають у `--help`/docstring), чи лишити як довідник і поставити на нього гард?
9. **Опис-тригер** — скоротити до ~1 100 символів (T-S/корпуси одним рядком, DE/PL вище) — це змінює спрацьовування; прогнати eval і прийняти новий базовий результат?
10. **omp за замовчуванням** в інсталяторі (issue #25 у репо) — лишити «разом із застосунком» чи `--no-omp` типово? README про omp мовчить у будь-якому разі.
11. **Мейнтейнерські розділи** (`review-loop.md` Wing 1, `estimator-scope.md` §1b/§2a, `feedback-loop.md` «author's side») — переносити в `CONTRIBUTING.md`/`docs/`, щоб модель їх не вантажила?
12. **Гілка 2.8.x у README** — лишається «competition-proven» альтернативою після релізу 3.1.0, чи README веде лише на 3.x, а 2.x — у FAQ?
