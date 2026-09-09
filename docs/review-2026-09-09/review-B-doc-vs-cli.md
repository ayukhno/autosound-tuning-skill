# Рецензія B — команди в доках проти CLI/argparse і MCP TCC

Скіл: `/Users/o.yukhno/dev/autosound/skill/skills/autosound-tuning` (далі `<skill>`), режим тільки-читання. Перевірено `--help` + код парсерів; частину команд прогнано на одноразовому проєкті в скретчпаді.

## Зведення

- Перевірено ~95 унікальних форм команд (модуль · підкоманда · прапорці) з SKILL.md, `references/core/*`, `references/phases/*`, `rew-tool-docs.md`, `setup-critic-channel.md`, `capabilities.md`, плюс 11 назв MCP-інструментів TCC і 4 поля `get_tcc_state`.
- Збігаються: ~86 форм + усі 11 MCP-назв + 4 поля.
- Не збігаються: **2 🔴** (команда з доків падає або бреше мовчки) і **7 🟠** (форма/шлях/формулювання, які коштують спроби).
- П'ять кроків процесу (версія методу · звірка стану · фаза+журнал · факти проєкту · закриття сесії) — усі мають робочу команду; 🔴 сидять у кроках «звірка стану» (`registry render` без кореня) і «журнал» (власний приклад `done` у project-intake.md).

## Розбіжності

### 🔴 `process.py <project>/process done -1.2 "get_tcc_state.reviewer.model=…" "reachable=true"` — тул відхиляє
- **Де в доках:** `references/core/project-intake.md:33-34`:
  `python3 rew_tool/state/process.py <project>/process done -1.2 \ "get_tcc_state.reviewer.model=gemini-2.5-pro" "reachable=true"` — подано як зразок «record what the state said and close it in the same breath».
- **Що в коді:** `rew_tool/state/process.py:718-725` (`finish_step`) — хоча б один доказ мусить РЕЗОЛВИТИСЬ; резолвер `process.py:409-436` приймає лише `v_NNN` з леджера, шлях до файлу, що існує (`_PATH_RE`, :344), або назву заміру з методом `(sw|rta)`. Прогін на одноразовому проєкті: `error: step '-1.2' has evidence, but none of it resolves: 'get_tcc_state.reviewer.model=gemini-2.5-pro'; 'reachable=true'`, exit 1. Сусідній приклад для `-1.1` (`:30-31`) проходить лише тому, що в рядку є `autosound_context.md`, який існує.
- **Наслідок:** модель копіює зразок, дістає exit 1, крок −1.2 лишається відкритим і наступна сесія знову питає про рецензента — рівно те, від чого абзац застерігає.
- **Виправлення:** док — додати до доказів файл, що існує (наприклад `autosound_context.md`, де записано вибір рецензента), або код — навчити `resolves()` форми `get_tcc_state.<поле>=<значення>`; вибір за власником.

### 🔴 `python3 rew_tool/state/state.py registry render` без `--root` — мовчки читає порожній корінь
- **Де в доках:** `SKILL.md:69` (Pre-Session крок 2, кожен старт): «multi-slot DSP → the active-slot banner first, `python3 rew_tool/state/state.py registry render`»; те саме без кореня: `references/core/happy-paths.md:25`, `references/core/naming-and-structure.md:112` (`state.py registry set-active <preset>`), `references/core/project-intake.md:183`.
- **Що в коді:** `rew_tool/state/state.py:1030` — `--root` за замовчуванням `os.environ.get("AUTOSOUND_STATE_ROOT", "state")`, тобто `state/` відносно cwd. За `SKILL.md:31-33` усі шляхи — відносно кореня скіла, отже команда читає `<skill>/state`. Прогін із кореня скіла: друкує «⚠️ NO ACTIVE SLOT SET … (no presets have a snapshot history yet)», **exit 0**. `set-active` у тій самій формі хоча б відмовляє (`state.py:841`, ValueError «has no snapshot history under 'state'»). `capabilities.md:141` пише правильно: `state.py --root <proj>/state …`.
- **Наслідок:** на старті сесії модель бачить «активний слот не задано» для проєкту, де він задано, і або пропонує `set-active`, або працює не проти того слота — саме та пастка (#5), яку банер мав закрити.
- **Виправлення:** док — у всіх чотирьох місцях `--root <project>/state` (або задати `AUTOSOUND_STATE_ROOT`); або код — дефолт від `$AUTOSOUND_PROJECT_DIR/state`, як у `predict.py`/`process.py`, і відмова, коли корінь не існує.

### 🟠 `contract.py check` не каже «predates a schema field», і радить `catch-up` лише для `symptom`
- **Де в доках:** `SKILL.md:69`: «If that report says the project predates a schema field, run `python3 rew_tool/project.py <project> catch-up`… legacy names, `tier` read off the ledger, and a marked `DRAFT:` symptom».
- **Що в коді:** `rew_tool/contract.py` — слова «predates» немає (grep по `rew_tool/*.py`: тільки в коментарях інших модулів). Підказка `python3 rew_tool/project.py <dir> catch-up` друкується в `contract.py:797-799`, і лише коли owner-facing рядок мапи не має `symptom`/`DRAFT`. `_ROW_FIELDS` (`contract.py:387-396`) аудитує тільки `acoustics.flaws[].evidence` та `.symptom` — legacy-імена (`sample_rate_hz`) і `tier` `check` не називає взагалі. Сам `catch_up` (`project.py:661-706`) робить усі три речі.
- **Наслідок:** модель шукає в звіті фразу, якої нема; для проєкту зі старими іменами/без `tier` підказки не буде, і `catch-up` не запуститься.
- **Виправлення:** док — «якщо у звіті є рядок `catch-up`» або просто «запускай `catch-up` при кожному відкритті — ідемпотентно» (так уже каже `capabilities.md:146`).

### 🟠 `python3 rew_tool.py analyze-batch …` — шлях не з кореня скіла
- **Де в доках:** `references/phases/phase_1_foundation.md:104`, `references/phases/phase_2_eq.md:29`, `:77` — `python3 rew_tool.py analyze-batch "_2 (rta)"` / `analyze-joints`; скорочено так само `capabilities.md:64,99`. Поруч інша форма: `phase_1_foundation.md:37` — `python3 rew_tool/rew_tool.py analyze-joints --process …`.
- **Що в коді:** файл — `<skill>/rew_tool/rew_tool.py`. З кореня скіла (`SKILL.md:31-33`): `python3: can't open file '<skill>/rew_tool.py'`. З `rew_tool/` (`rew-tool-docs.md:18`, `cd <skill-dir>/rew_tool && python3 rew_tool.py`) працює; `selftest` проходить з обох тек.
- **Наслідок:** одна спроба з помилкою «no such file» і пошук, звідки запускати.
- **Виправлення:** док — одна форма `python3 rew_tool/rew_tool.py …` у фазах; `rew-tool-docs.md:18` лишити як примітку.

### 🟠 `rew_tool.py analyze-joints --from-state --process DIR` без `--state-root`
- **Де в доках:** `references/core/capabilities.md:64`.
- **Що в коді:** `rew_tool/rew_tool.py:1038-1039` — `--state-root` за замовчуванням `AUTOSOUND_STATE_ROOT` або `state` (відносно cwd); з кореня скіла: «Помилка: active slot не задано в registry (state); вкажи --preset» (`rew_tool.py:497`).
- **Наслідок:** відмова з хибною порадою (`--preset`), хоч бракує кореня.
- **Виправлення:** док — `--state-root <project>/state` у рядку команди (той самий клас, що 🔴 вище).

### 🟠 `python3 rew_tool/dsp_profile.py` → `find_bundled(vendor, model)` / «answers `None`»
- **Де в доках:** `references/core/project-intake.md:172`.
- **Що в коді:** CLI-дієслово — `find-bundled <vendor> <model> [bundled_dir]` (`dsp_profile.py --help`); без збігу друкує `no exact match`, exit 0 — `None` повертає лише python-функція. `car_profile.py --find` теж друкує «no exact match — this body is not in the library», не `None`. `project-intake.md:181` пише дієслово правильно.
- **Наслідок:** `python3 rew_tool/dsp_profile.py find_bundled …` → argparse «invalid choice».
- **Виправлення:** док — `python3 rew_tool/dsp_profile.py find-bundled "<vendor>" "<model>"` і «друкує `no exact match`».

### 🟠 `python3 rew_tool/dsp_profile.py <new> …` — проєкт на першому місці
- **Де в доках:** `references/core/intake-from-prose.md:60`.
- **Що в коді:** `dsp_profile.py` — підкоманда йде ПЕРШОЮ: `start <project_dir> <vendor> <model>`, `set-field <project_dir> <path> <value>`, `finalize <project_dir>` (subparser help). `<new>` на першій позиції — «invalid choice».
- **Наслідок:** одна помилкова спроба; модель шукає порядок у `--help`.
- **Виправлення:** док — `python3 rew_tool/dsp_profile.py start <new> <vendor> <model>` → `set-field <new> …` → `finalize <new>` (як `project.py <new> …` рядком вище, де порядок правильний).

### 🟠 `scripts/run-selftests.sh`, `scripts/installer-consistency.py`, `scripts/tag-check.sh`, `scripts/encoding-check.py` — не в `scripts/` скіла
- **Де в доках:** `references/core/capabilities.md:173-174`; `references/core/data-contract-universal.md:24`.
- **Що в коді:** ці файли лежать у корені репо `/Users/o.yukhno/dev/autosound/skill/scripts/`; `<skill>/scripts/` їх не має (там `autosound_ai.py`, `*_critic.sh`, `*_advisor.sh`, `start_gemini_tuner.sh`, …). За `SKILL.md:31` база для `scripts/` — корінь скіла. Команди супроводу, не сесії.
- **Наслідок:** низький — модель у сесії їх не запускає.
- **Виправлення:** док — `<repo>/scripts/…` або примітка про базу.

### 🟠 `get_tcc_state.reviewer.model` / `.reachable` є лише коли рецензента обрано
- **Де в доках:** `references/core/project-intake.md:14-15`, `:63`.
- **Що в коді:** `/Users/o.yukhno/dev/autosound/tcc/src/autosound_tcc/core/mcp_server.py:137-141` — без вибору повертається `{"configured": false, "how": "ask the Arbiter to pick one…"}` без `model`/`reachable`; з вибором — `configured, model, substituted, label, reachable, how, decided_by` (`:153-172`).
- **Наслідок:** модель читає відсутній ключ як «unreachable» замість «не обрано».
- **Виправлення:** док — одне речення: спершу `reviewer.configured`; коли `false`, є тільки `how`.

## MCP-інструменти TCC vs доки

Джерело: `/Users/o.yukhno/dev/autosound/tcc/src/autosound_tcc/core/mcp_server.py` (`@tool()` = `mcp.tool`, :327-332; назва інструмента = назва функції). Кожен пише через `process_writer` → `python3 process.py <project>/process <verb>` під ексклюзивним локом (`core/process_writer.py:119-150`), тобто той самий журнал, що й CLI.

| назва в доках (SKILL.md:84, project-intake.md:184) | є в TCC? | назва/сигнатура в TCC |
|---|---|---|
| `get_tcc_state` | так | `get_tcc_state()` :361 → `project_dir, ui, language, current_phase, process_state_error, sessions, pending_signals, effort, reviewer{…}, _this_is_settled` |
| `enter_phase` | так | `enter_phase(phase)` :725 |
| `add_step` | так | `add_step(step_id, name, situational=False)` :733 |
| `start_step` | так | `start_step(step_id)` :740 |
| `finish_step` | так | `finish_step(step_id, evidence: list[str])` :746 — та сама вимога RESOLVE |
| `skip_step` | так | `skip_step(step_id, superseded_by="")` :757 |
| `block_step` | так | `block_step(step_id, reason)` :763 |
| `start_capture` | так | `start_capture(version, expected: list[str], step="")` :796 |
| `record_capture` | так | `record_capture(title)` :812 |
| `skip_capture` | так | `skip_capture(title, reason)` :819 |
| `close_capture` | так | `close_capture(reason="")` :825 |
| `record_decision` | так | `record_decision(question, answer, step="", invalidates="")` :769 |
| — (не названо в доках) | є | `check_captures(titles)` :783 — MCP-двійник `capture-check`; варто додати до переліку в SKILL.md:84 |
| `capture-protective`, `capture-knobs`, `reviewer`, `target`, `listening-verdict`, `session-start`, `session-close` | **нема** MCP-двійника | лише CLI `process.py …` навіть з підключеним TCC (у TCC їх пише GUI: `process_writer.set_protective` :224, `record_reviewer` :199, `record_listening_verdict` :256 — без `@tool()`). Доки це не суперечать, але SKILL.md:84 «THAT is the call» варто звузити до 11 названих |

Поля `get_tcc_state`, обіцяні `project-intake.md:12-15`:

| поле | повертається? | де |
|---|---|---|
| `language` | так | `mcp_server.py:376` ← `ui.ui_language` ← `main_window.py:3273` (`i18n.current_language()`) |
| `reviewer.model` | так, коли `configured` | `mcp_server.py:155` |
| `reviewer.reachable` | так, коли `configured` | `mcp_server.py:163` (`model_choices.critic_reaches`) |
| `reviewer.how` | так, завжди | `mcp_server.py:139`, `:164-165` («call the `call_critic` tool» / clipboard) |

Інші перевірені твердження про код (пункт 4 завдання):
- `deployment.py`: exit `0` один метод (`:175`), `3` різні чекаути (`:174`), `4` нема ідентичності або нема жодного розгортання (`:157`, `:161`); `main()` повертає код і при `--json` (`:318-326`); `2` — неправильні аргументи. Збігається з `SKILL.md:48,67`.
- `contract.py check`: `--gate` → exit 0 лише при `complete` (`:909-910`), `--phase0-gate` → `map_ready` (`:907-908`), без прапорця → `ok` (`:911`); фраза «predates» — ні, порада `catch-up` — так, тільки для `symptom` (див. 🟠 вище).
- `enter-phase 1` відмовляє без флоу-мапи (`process.py:193-194`), без target (`:1621`), без `dsp_processing_rate_hz`/`delay`/`crossover_filters` (`:274`); `enter-phase 2` — без `parametric_eq`/`eq` (`:275`). Збігається з `phase_0_baseline.md:17`, `phase_1_foundation.md:13`, `phase_2_eq.md:16`.
- `dsp_profile.py effects` exit 3, коли список не записано (`dsp_profile.py:1092-1099`) — як у `capture-session-sheet.md:14`, `virtual-first.md:78-80`.
- `verify_prediction.py --project DIR` exit 4 при `unrecorded`/`unmapped` ручках (`verify_prediction.py:745-748`) — як у `capabilities.md:120`, `virtual-first.md:152-155`.
- `session-close` звітує і виходить 1, поки щось відкрите (`process.py:1975-2007`) — як у `SKILL.md:73`.

## Команди, що збігаються

**`rew_tool/state/process.py <project>/process …`** (перший позиційний = тека `process/`, `Process.__init__` :542; `project_dir` = її батько :557): `show`, `plan [phase]`, `enter-phase <N>` (у т.ч. `-1`), `add-step <id> <name> [--project]`, `start <id>`, `done <id> <evidence…>`, `skip <id> [superseded-by]`, `block <id> <reason>`, `reviewer <vendor> <model> [step] [--review PATH] [--mode clipboard]` (:1936-1955; `--mode clipboard` — прапорець саме цієї команди, в `autosound_ai.py` прапорця `--mode` нема — там clipboard-режим автоматичний, :985), `target <preset> <curve>`, `decision <question> <answer> [step] [--invalidates X]`, `session-start <harness> <model> [resumed]`, `session-close`, `capture-start <version> [titles…] [--step ID]`, `capture-taken <title>`, `capture-skip <title> <reason>`, `capture-close [reason]`, `capture-check [titles] [--session]`, `capture-knobs NAME=POS…` (`SubRC=4/4 RealCenter=ON`), `capture-protective <ch> --hp 1000 LR 24 [--lp 4000 BW 36]` / `<ch> OFF`, `listening-verdict --pair t:c:ok|bad … --text … --ledger-version vN --route full [--note]`, `listening-verdicts [--track] [--characteristic] [--ledger-version] [--bank]`, `check`, `selftest`. Прогнано: `enter-phase -1`, `add-step`, `done` з файлом, `reviewer … -1.2`, `decision … --invalidates`, `capture-start … --step`, `capture-protective m-L --hp 1000 LR 24`, `capture-knobs SubRC=4/4`, `session-close` — усі OK.

**`rew_tool/project.py <project> …`** (:1153-1295): `show`, `open-questions`, `catch-up [--dry-run]`, `migrate-fields [--dry-run]`, `backfill-tiers [--dry-run]`, `set-channel <code> key=value… [--source S]` (`slot=C fs_hz=62`, JSON-значення для `driver={…}`), `rename-channel <old> <new>`, `set-hardware <name> <value>`, `set-route <VIRTUAL> <out,out>`, `set-control-mapping <name> <step_db> <ch,ch> [--source] [--zero-at]`, `record-change <process-dir> <file> <what>`, `flaw <f_hz> <level_db> <kind> <action> [--q|--bw-oct] [--channels] --why --evidence [--status] [--symptom]` і `flaw --t-ms <ms> <kind> <action>`, `flaws [--owner]`.

**`rew_tool/state/state.py`**: `--root ROOT`, `log <preset>`, `render <preset> [version]`, `diff <preset> va vb`, `revert <preset> [version]`, `registry show|set-active|render|describe [preset]`, `repair-encoding`.

**`rew_tool/contract.py`**: `check <dir> [--json] [--no-rew] [--gate] [--phase0-gate]`, `gaps [<dir>…] [--json] [--depth N]` (без шляху — батько `$AUTOSOUND_PROJECT_DIR` або cwd, :843-853), `repair-encoding <dir> [--from cp1251]`, `table`, `selftest`.

**`rew_tool/deployment.py [<project>] [--json] [--selftest]`**.

**`rew_tool/rew_tool.py`**: `analyze-batch "<pattern>" [--curves-dir] [--no-targets]`, `analyze-joints [--joint "lo,hi,fc[,pair]"]… [--from-state] [--preset] [--state-root] [--state-ver] [--ver N] [--band-oct] [--process DIR] [--baseline] [--apf ch,APF2,f0,Q]`, `selftest`.

**`rew_tool/naming.py <project> …`** (:548-570): `codes`, `name <code> <version> [method]` (`name w-L 49 sw`), `parse <title>`, `expect <phase> <ver>`, `check <phase> <ver>`, `selftest`.

**`rew_tool/car_profile.py`** (:210-241): `--find "<make>" "<model>" "<generation>" "<body>"` (і три частини), `--prior <ті ж чотири> <dir>…`, `--list`.

**`rew_tool/dsp_profile.py`**: `find-bundled <vendor> <model>`, `list-bundled`, `effects <profile.json>`, `open-questions <path>`, `validate <path>`, `refresh <project_dir> [--write]`, `start <project_dir> <vendor> <model>`, `set-field <project_dir> <path> <value>`, `reset-field`, `draft <project_dir>`, `finalize <project_dir>`, `checklist`, `diff`.

**`rew_tool/project_seed.py SOURCE [TARGET] [--findings] [--no-profile] [--note] [--json]`**, `--describe <dir>`.

**`rew_tool/predict.py`**: `--solos DIR | --rew --ver N`, `--channels`, `--process DIR` (дефолт `$AUTOSOUND_PROJECT_DIR/process`), `--baseline`, `--from-state VER`, `--project DIR`, `--route VFL=w-L,m-L,tw-L`, `--joint`, `--out DIR`, `--plot`, `--json`, `--align [--max-delay-ms] [--step-ms] [--apf]`, `--gate MS`, `--fdw CYCLES`, `--arrival A,B`, `--delta-vs VER`, `--ladder lo,hi`.

**`rew_tool/eq_propose.py --project P --solos DIR|--rew --ver N --house FILE [--ellipsoid DIR] [--route …] [--process] [--allow-boost] [--accept a,b] --out DIR`**.

**`rew_tool/verify_prediction.py --predicted JSON --rew --ver N | --measured DIR [--pair lo,hi=T] [--solo ch=T] [--all T] [--all-plus-c T] [--allow-rta] [--entry] [--project DIR] [--steady] [--out]`**.

**`rew_tool/ear_suspects.py --rew --title "ALL_2 (rta)" | --file TXT [--process DIR --round K] [--phon] [--top] [--lang]`**.

**`rew_tool/ellipsoid.py --solos DIR | --rew --ver N --channel m-L`**.

**`rew_tool/flaw_map.py --project P --solos DIR [--ellipsoid DIR] [--write] [--json]`**.

**`rew_tool/xover_candidates.py --solos DIR --project DIR --house FILE --channel <code> [--hp lo:hi:step] [--lp lo:hi:step] [--fs]`**, `--selftest`; **`rew_tool/crossover_checks.py --fc <Hz> [--fs] [--order n] [--gd f:ms,…] [--phon]`**, `--selftest`.

**`rew_tool/spot_check.py "A" "B" --at 160,2540 --peak 2000-3000 --claim 2543.8`**, `--selftest`; **`rew_tool/phase_rotation.py <deg> <ref_hz> [--fs]`**; **`rew_tool/verify.py <title>… [--json] [--band lo hi] [--session]`**; **`rew_tool/state/migrate.py <old> --into <new> [--dry-run]`**; **`rew_tool/capabilities.py --selftest`**; `--selftest` у `analysis.py`, `joint_analysis.py`, `xover_select.py`, `setup_import.py` (+ `--atf CODE=file`).

**Скрипти (`<skill>/scripts/`)**: `autosound_ai.py critic|advisor <package.md> [trace.csv]`, `autosound_ai.py doctor` (:737-759; пише `process/reviews/<ts>-<role>.md` і друкує `REVIEW_FILE:` :718-733, проєкт бере з `$AUTOSOUND_PROJECT_DIR` або cwd-що-схожий-на-проєкт :682-699); `gemini|claude|codex_critic.sh <package.md> [trace.csv]`, `*_advisor.sh …`, у всіх `--doctor`; `GEMINI_CRITIC_MODEL=… scripts/gemini_critic.sh pkg.md` (`gemini_critic.sh:39`); `start_gemini_tuner.sh [--refresh]` (:70).

**Python-API, названі в доках**: `apply.propose(history, delta, …)` (`rew_tool/state/apply.py:290`), `Project(...).set_channel(...)`, `project.fact(...)`, `process.open_work`, `state.current_target` — існують.
