# Рецензія C — стик скіл `autosound-tuning` ↔ TCC (2026-09-09, тільки читання)

Скорочення шляхів: `S/` = `/Users/o.yukhno/dev/autosound/skill/skills/autosound-tuning` (SKILL.md, references/, rew_tool/, scripts/); `S-repo/` = `/Users/o.yukhno/dev/autosound/skill`; `T/` = `/Users/o.yukhno/dev/autosound/tcc/src/autosound_tcc`; `T-repo/` = `/Users/o.yukhno/dev/autosound/tcc`.

## Як це працює зараз

1. **Як TCC знаходить скіл.** Змінна — `AUTOSOUND_SKILL_DIR` (`T/core/vendor_loader.py:33`), порядок: env → сабмодуль `vendor/autosound-tuning-skill/skills/autosound-tuning` → `~/.claude/skills/autosound-tuning` → `~/.claude/plugins/*/skills/…` (`vendor_loader.py:36-54`); «це 3.x-скіл» = є `rew_api.py`+`project.py`+`contract.py` (`:63`). Пін сабмодуля в HEAD TCC = `0cc96f6` = `v3.0.46-7` (`git ls-tree HEAD vendor/…`, коміт `a7733ec`), тоді як `T-repo/CHANGELOG.md:10-12` каже, що v0.1.35 «paired with dcf5a68 … v3.0.46»; HEAD скіла — `v3.0.46-33`, на 26 комітів попереду піна (серед них `capture-knobs`, новий `autosound_ai.py`, `contract.py`/`project.py` +186/+149 рядків). У сесію скіл потрапляє НЕ плагіном і не `--add-dir`, а **симлінком `<project>/.claude/skills/autosound-tuning` → `skill_dir().resolve()`**, який TCC робить один раз і далі не чіпає (`vendor_loader.py:206-235`, виклик `T/core/tuning_session.py:477`), + `setting_sources=["project"], skills=["autosound-tuning"]` (`tuning_session.py:453-454`); для omp — оверлей `skills.includeSkills` (`T/core/omp_session.py:291-301`). Жодну змінну середовища в сесію TCC не експортує (`child_env` дає лише `PYTHON*`, `vendor_loader.py:238-263`; SDK-опції без `env`, `tuning_session.py:441-469`).
2. **Що впорскується.** Claude-маршрут: `system_prompt={"preset":"claude_code","append":SYSTEM_PROMPT_APPEND}` (`tuning_session.py:449`, текст `:153-171`) + опенер «Start a tuning session … Read state from disk, call get_tcc_state, then tell me where we are» (`:482-488`); omp-маршрут — той самий опенер (`omp_session.py:904-911`) і **без** системного промпта (`T/core/mcp_server.py:396-397, 533`). Якщо тюнер сам друкує перше повідомлення («tune a new car from scratch»), воно **замінює** опенер (`T/ui/tcc/dialog_panel.py:887-900` → `main_window.py:3413-3419` → `tuning_session.py:482 opener = prompt or …`). Дозволи: `mcp__tcc*`/`TodoWrite` без питань, `Read/Grep/Glob` у проєкті+скілі, `Bash` лише read-only allowlist (`:57, :78-135, :393-416`); `apply.py` і `state/process.py` — через дозвіл Арбітра.
3. **MCP.** Сервер `tcc` (`mcp_server.py:82`), 30 інструментів (перелік закріплено тестом `T-repo/tests/test_mcp_server.py:135-177`). `get_tcc_state` віддає `project_dir`, `language` (=мова UI, `main_window.py:3273`, коди en/uk/pl/de `T/ui/tcc/i18n.py:31-36`), `current_phase` (з `process-state.json`, не «phase»), `reviewer{configured, model, substituted, label, reachable, how, decided_by}`, `ui`, `sessions`, `pending_signals`, `effort`, `_this_is_settled` (`mcp_server.py:360-412`, `:125-167`). Записи в журнал — лише через `python3 rew_tool/state/process.py` як підпроцес під file-lock (`T/core/process_writer.py:1-24, 119-150`). Таблиця — внизу.
4. **Що читає.** Через імпорт файлів скіла під синтетичними іменами (`vendor_loader.py:139-187`): `rew_api`, `state/state.py`, `state/process.py`, `naming`, `dsp_profile`, `project`, `dsp_math`, `resonalyze_vc`, `project_seed`, `eq_export`, `protective`, `listening`, `gates/side_effect`, `car_profile`; `contract.py` — тільки підпроцесом `--json` (`T/core/contract_check.py:1-20`). **Власні читачі поверх файлів:** `T/state/project_view.py:1-4` і `acoustics_view.py:173` (`project.json`), `process_view.py:63-94` (`process/process-state.json`, `journal.jsonl`), `measurement_view.py:37-48` (`glossary.json`/`project.json.glossary`), `dsp_state.py:22-26,281-289` (ledger `state/<preset>/v_NNN.json` + `project.json.channels/hardware.controls`), `core/target_curve.py:38-41` (`rew_analitic/target-curves`, `references/patterns/target-curves/curves`), `core/critic.py:86-113` (`rew_analitic/`, `autosound_context.md`, `data-contract-template.md`), `core/config.py:120-132` (`autosound_context.md`, `.tcc`, `dsp_profile.json`, `rew_analitic`). `schema_version` ці читачі не звіряють (жодного згадування в `T/state/*.py`); звірка — лише панеллю діагностики через `contract.py`. Ціна дубля вже куплена: F-050 (`plain`→`symptom`) знайшли тільки підняттям піна (`CHANGELOG.md` v0.1.35).
5. **Версія методу.** Заголовок вікна `TCC x · skill <plugin.json.version>` (`main_window.py:3198-3210`, `T/core/install_report.py:141-158` через `skill_repo_root` `vendor_loader.py:95-117`); sha — лише у звіті встановлення (`install_report.py:161-187`); «є новіший тег?» — за sha (`T/core/updates.py:246-280`); «пін відстав від тега» — `T/core/self_check.py:164-227`. **`rew_tool/deployment.py` TCC не викликає** (grep по `T/` — 0). Два репо ставлять два різні питання: TCC — «чи мій скіл найновіший», скіл — «чи всі копії на машині збігаються» (`S/rew_tool/deployment.py:131-175`: кандидати here/project/personal, плагіни не бачить).
6. **Рецензент.** `call_critic` → `T/core/critic.py:151-231` запускає `S/scripts/autosound_ai.py <role> <pkg>` з `cwd=project`, env + `PROJECT_MIRROR` + `GEMINI_CRITIC_MODEL` (модель — з футера, `mcp_server.py:963-968`); ключ TCC не тримає — скрипт сам читає `~/.config/autosound/critic-env` (`autosound_ai.py:53-56, 89-137`) ✓ узгоджено з `S/references/tooling/setup-critic-channel.md:62-71`; шлях критики з stderr `>> REVIEW_FILE:` іде в журнал (`critic.py:43`, `mcp_server.py:974-984`) ✓ SCR-027. Але `reviewer.reachable` рахується з `os.environ`/PATH (`T/core/model_choices.py:598-656`), файл `critic-env` TCC не читає (grep — 0). Пакети TCC пише в `.tcc/packages/` (`critic.py:132-147`).
7. **Установка.** `S-repo/install.sh`: скіл — `git clone --branch <найновіший v*> --depth 1` у `~/.claude/skills/.autosound-tuning-src` + симлінк `~/.claude/skills/autosound-tuning` (`:53-63, :700-704, :752-761`); TCC — `uv tool install 'autosound-tcc[gui,claude] @ git+…@<найновіший v*>'` (`:843-856`), далі `--install-desktop`. `S-repo/commands/install-tcc.md:20-22` пінить `@v0.1.35` = найновіший тег TCC ✓. Після установки всі три (`S-repo/README.md:58-62`, `install.sh:1207-1224`, `T-repo/README.md:204-246`) кажуть одне: відкрити TCC → тека авто → «tune a new car from scratch»; термінальний шлях `cd <project> && claude` — теж в обох.
8. **Старт проєкту в TCC.** На attach TCC сам пише `session-start` і, якщо `process/` порожній, `enter-phase -1` (`main_window.py:3629-3637`); далі фазу рухає лише модель. `.mcp.json` з сервером `tcc` пишеться в проєкт (`mcp_server.py:1107-1130`) і при `stop()` не прибирається (`:1334-1340`).

## Розбіжності скіл ↔ TCC

### 🔴 `reviewer.reachable` — «вирішено» з хибної передумови, і протилежні поради про ключ
**Скіл каже:** `setup-critic-channel.md:64-66, 74` — ключ живе в `~/.config/autosound/critic-env`, «do not `export GEMINI_API_KEY` from your shell profile»; `project-intake.md:38-40` — «A reviewer the state reports as unreachable is not done: block that step (`block -1.2 "clipboard-only until …"`)»; `:15-17` — стан читати як **answered**.
**TCC робить:** `model_choices.py:632-656` — `reachable` = є `GEMINI_API_KEY` в env TCC **або** `agy`/`gemini` на PATH; `critic-env` не читає ніде; `mcp_server.py:160-162` віддає «how: call `call_critic`; it will hand you a clipboard package»; `omp_session.py:925-930` радить «Start TCC from a shell that has the key».
**Наслідок:** налаштування «за скілом» (ключ у файлі, без `agy`) → `reachable=false` → модель блокує крок −1.2 і чекає буфера, хоча `call_critic` дійшов би до API (скрипт файл читає); а користувачеві TCC каже експортувати те, що скіл велить не експортувати.
**Кому правити:** tcc (+ skill SCR-051 для omp-транспортів).
**Пропозиція:** `critic_reaches` — питати те, що вже загорнуто: `autosound_ai.py doctor` (`critic.py:282-302`) або читати той самий `critic-env`; попередження omp — про профіль `omp auth`, не про shell-export.

### 🟠 Змінна шляху до скіла — три імені, жодне не працює для сесії
**Скіл каже:** `SKILL.md:36-38` — «else `$AUTOSOUND_SKILL_ROOT` if a front-end set it»; `S-repo/commands/install-tcc.md:53` — «the variable is `AUTOSOUND_SKILL_DIR`».
**TCC робить:** читає `AUTOSOUND_SKILL_DIR` для **своїх** читачів (`vendor_loader.py:33, 44-46`), у сесію не експортує нічого (`child_env` `:238-263`; SDK-опції `tuning_session.py:441-469`); симлінк проєкту «left alone whatever it points at» (`vendor_loader.py:217-219`).
**Наслідок:** у SKILL.md мертвий пункт із чужим іменем; розробник, що переставив `AUTOSOUND_SKILL_DIR`, отримує TCC-читачі на одному чекауті, а SKILL.md сесії — на іншому (старий симлінк) — саме той «тихий» розсинхрон, який `SKILL.md:43-51` описує.
**Кому правити:** обом.
**Пропозиція:** SKILL.md назвати `AUTOSOUND_SKILL_DIR` і сказати, що TCC його не експортує; TCC при заданій змінній переставляти симлінк проєкту (або хоча б попереджати, що він вказує деінде).

### 🟠 `propose_change` (картка) проти `apply.propose` (банк) — однакове слово, різна дія
**Скіл каже:** `SKILL.md:83` — «Bank every agreed change via `apply.propose` — it writes the `v_NNN` versioned snapshot AND emits the settings sheet».
**TCC робить:** `mcp_server.py:832-850` `propose_change(channel, param, from, to, rationale)` — «Put a proposed DSP change on screen as a card … Has no effect on anything»; про ledger/`apply.propose` докстрінг мовчить; `apply.py` не в read-only allowlist (`tuning_session.py:110-135`) → банк іде через дозвіл Арбітра, картка — без.
**Наслідок:** модель у TCC має на поверхні інструмент, чиє ім'я збігається з тим, що скіл велить робити, і дешевший шлях не пише `v_NNN` — розвилка ledger/hardware, про яку `SKILL.md:75`.
**Кому правити:** обом.
**Пропозиція:** у докстрінгу `propose_change` — «показує; банк лишається `apply.propose`», у `SKILL.md:83` — рядок у стилі `:84`: «картка фронтенду ≠ банк».

### 🟠 «Стоп — це подія»: у TCC події нема
**Скіл каже:** `SKILL.md:71-77` — на «добраніч» спершу `session-close` (називає відкритий раунд і кроки), потім `capture-skip/close`, `done/block`, `decision`, 🟡→`apply.propose`, лог; далі нового не починати.
**TCC робить:** `session-close` ніде (grep по `T/` — 0; не в MCP `test_mcp_server.py:140-177`, не у UI); при зміні моделі/виході шле свій `_HANDOFF_PROMPT` (`main_window.py:157-163`): finish/block/add_step, `report_phase` ≡ файлу, `autosound_context.md` — без раунду, рішень, банку.
**Наслідок:** у вікні «добраніч» закривається або через Bash-виклик `process.py` (гейт → діалог дозволу), або ніяк; вихід із TCC пише інший, коротший чекліст, ніж скіл.
**Кому правити:** обом.
**Пропозиція:** TCC — на quit/handoff запускати `session-close` і показувати його вихід (це вже є в `process_writer`-стилі); скіл — у `SKILL.md:73` назвати, що фронтенд без такого інструмента = CLI.

### 🟠 Три «перші кроки», і опенер TCC зникає саме в сценарії з умови
**Скіл каже:** `SKILL.md:67` крок 0 — `deployment.py <project>`, «named to the user before step 1»; `project-intake.md:11-12, 61` крок 0 — «Before the first question … call `get_tcc_state`»; `SKILL.md` сам `get_tcc_state` не згадує (grep — лише `project-intake.md`).
**TCC робить:** опенер «Read state from disk, call get_tcc_state…» (`tuning_session.py:482-488`, `omp_session.py:904-911`), але при власному першому повідомленні тюнера він **замінюється** тим повідомленням (`dialog_panel.py:889-900`, `tuning_session.py:482`); `SYSTEM_PROMPT_APPEND:156-163` додає ще `get_pending_signals` на початку кожного ходу і `report_phase` «as soon as they change»; omp-маршрут промпта не має (`mcp_server.py:533`).
**Наслідок:** при «tune a new car from scratch» на Gemini-маршруті єдине місце, що каже «спершу `get_tcc_state`», — §0 intake, який завантажується вже після того, як модель сама вирішила, що це фаза −1; для resume таку вказівку скіл не дає взагалі.
**Кому правити:** обом.
**Пропозиція:** TCC — префіксувати набране повідомлення канонічним рядком (або віддавати його першим `get_pending_signals`); скіл — у `SKILL.md` Pre-Session крок 2 один рядок «`get_tcc_state`, якщо сервер `tcc` підключений» (як `:84` для рекордерів).

### 🟠 Рецензент: `call_critic` у скілі не названий, `[step]` губиться
**Скіл каже:** `SKILL.md:84` — «every reviewer call → `reviewer <vendor> <model> [step] --review <path>`»; `:171` — «wrappers … `autosound_ai.py` … ⚠️ Run reviewer CLIs outside the driver session (inside = deadlock)».
**TCC робить:** `call_critic` (`mcp_server.py:942-1010`) сам пише `reviewer` **без `step`** (`:976-982`, `process_writer.record_reviewer` має параметр `step`, він не передається); `autosound_ai.py` — не в allowlist (`tuning_session.py:110-135`) → прямий виклик через Bash іде на дозвіл і минає `critic-log`/футер (`critic.py:238-262`, `main_window.py:3402-3411`).
**Наслідок:** модель у TCC читає «запусти CLI зовні сесії» і може оминути `call_critic`; коли ж користується ним — критика в журналі не прив'язана до кроку, і гейт кроку її не бачить.
**Кому правити:** обом.
**Пропозиція:** `SKILL.md:165-173` — «фронтенд із `call_critic` → це і є виклик» (той самий шаблон, що `:84`); TCC — аргумент `step` у `call_critic` → `record_reviewer`.

### 🟠 Дві перевірки версії, що не бачать одна одну; пін і реліз-нотатка розходяться
**Скіл каже:** `deployment.py:131-145` — кандидати `here`/`project`/`personal`; `SKILL.md:43-51, 67` — розбіжність (exit 3) називати перед кроком 1.
**TCC робить:** шукає ще й `~/.claude/plugins/**` (`vendor_loader.py:50-54`), `deployment.py` не викликає; у чекауті сабмодуль (`0cc96f6`, v3.0.46-7) стоїть **перед** `~/.claude/skills` (`:47-49`), а `install.sh:700-704, 752` ставить туди тег `v3.0.46` (`dcf5a68`); `CHANGELOG.md:10-12` v0.1.35 = `dcf5a68`, а `git ls-tree HEAD` = `0cc96f6`.
**Наслідок:** у dev-чекауті TCC кожна сесія стартує з «2 different checkouts» (exit 3), бо project-лінк→сабмодуль ≠ personal→тег; копія в `~/.claude/plugins` (шлях 2.8.x у `S-repo/README.md:68-74`) для `deployment.py` невидима; «з чим спарений v0.1.35» — два різні sha.
**Кому правити:** обом.
**Пропозиція:** скіл — додати `plugins` у кандидати `deployment.py` + `S-repo/docs/TODO.md` S-001 (оголошений пін); TCC — рядок пари в CHANGELOG брати з `git ls-tree`, не руками.

### 🟢 `capture-check --session` у TCC недоступний
**Скіл каже:** `SKILL.md:116`, `references/phases/virtual-first.md:98` — крок 0.6 `capture-check --session`.
**TCC робить:** `check_captures(titles)` без `--session` (`mcp_server.py:783-793`, `process_writer.py:358-371`).
**Наслідок:** модель у TCC мусить іти в CLI (writer → гейт). **Кому правити:** tcc. **Пропозиція:** прапорець `session: bool`.

### 🟢 Мова: факт узгоджений, а голос TCC — англійський
**Скіл каже:** `project-intake.md:42` — «the whole dialogue AND all generated project files — in the chosen language»; `:62` — брати з `get_tcc_state.language`.
**TCC робить:** `language` = код UI (`main_window.py:3273`) ✓, але опенер, `SYSTEM_PROMPT_APPEND`, handoff — англійські, і TCC сам позначає це як OPEN (`main_window.py:151-156`); правило мови є лише в інтерв'ю профілю (`agent_session.py:142-144`), де `LANGUAGE_NAMES` = en/uk (`:159`) при UI en/uk/pl/de.
**Наслідок:** другий голос у розмові; для pl/de інтерв'ю профілю назви мови нема. **Кому правити:** tcc. **Пропозиція:** одне рішення (мова сесії або «системні команди завжди EN») і дописати pl/de у `LANGUAGE_NAMES`.

### 🟢 `enter-phase -1` двічі і `.mcp.json` після виходу
`main_window.py:3636-3637` сіє `enter-phase -1`, `project-intake.md:184` велить моделі те саме; `process.py:610-636` при `previous == phase` статус не міняє, але подію `phase_entered` дописує (`:635`) — дубль у журналі, нешкідливий. `.mcp.json` з мертвим портом лишається в проєкті після `stop()` (`mcp_server.py:1334-1340`) — у голому терміналі (`T-repo/README.md:233-243`) сервер «є, але не connected»; за `project-intake.md:11` це коректно читається як «немає фронтенду», але з шумом невдалого підключення. **Кому правити:** tcc. **Пропозиція:** прибирати запис `tcc` на stop або документувати.

### 🟢 Узгоджено (для повноти)
Рекордери процесу: `SKILL.md:84` ↔ MCP `enter_phase…record_decision` — імена й аргументи збігаються, гейт evidence — на боці скіла (`mcp_server.py:745-754`, SCR-031/035 done). Мова/рецензент з фронтенду — SCR-037 done (`project-intake.md:11-40`, `mcp_server.py:398-402`). Захисні фільтри: `project-intake.md:123` «a front-end that marks protection writes the same record» ↔ `T/ui/tcc/protective_dialog.py:268`, `measurement_panel.py:254` → `capture-protective`. `AUTOSOUND_PROJECT_DIR`/`AUTOSOUND_STATE_ROOT` — одна конвенція (`config.py:8-18` ↔ `S/rew_tool/rew_tool.py:1038`, `contract.py:850`, `predict.py:1774`). Установка: `install-tcc.md` ↔ `install.sh` ↔ обидва README — одна послідовність дій.

## Що в TCC уже в TODO/issues по стику

- `#21` — показувати якість захвату, поки мікрофон у руках, і що перезняти (рендер вердикту `check_captures`).
- `#20` — прибрати власний `is_swept()`, коли метод дасть свій (у скілі вже є з `dc2d7b8`, за піном — після наступного підняття).
- `#19` — Windows: падіння набору (не стик).
- `docs/TODO.md` F-023 — per-round identity захвату всередині TCC (пара до SCR-053, withdrawn).
- `docs/TODO.md` F-034 — «гіпотеза» і «транскрипція» виглядають як підтверджене (походження фактів `project.json`).
- `docs/TODO.md` F-049 — `check` тепер про походження запису protective (TCC-005, у методі з v3.0.46).
- `docs/TODO.md` F-051 — Resonalyze: чотири ролі, видно дві (віддано в скіл, hub#75 / TCC-008).
- `docs/SKILL-CHANGE-REQUESTS.md` SCR-051 — транспорти рецензента без omp → бейдж «clipboard only» (proposed; дотично до 🔴).
- Скіл-бік, дотично: `S-repo/docs/TODO.md` S-001 — `deployment.py` не відрізняє оголошений пін від розколу.

## Таблиця MCP ↔ CLI

CLI = `S/rew_tool/state/process.py` (`_USAGE` `:1503-1555`, диспетчер `:1911-2160`); MCP = `T/core/mcp_server.py` (перелік `tests/test_mcp_server.py:140-177`); обгортки = `T/core/process_writer.py`.

| CLI підкоманда | MCP інструмент | збіг полів? |
|---|---|---|
| `show` | `report_phase` (`:1012-1048`) / `get_tcc_state.current_phase` | частково: лише `active_phase`; план/кроки — ні |
| `plan [phase]` | — (`process_writer.plan` `:403-408` є, ніхто не кличе) | нема; модель читає файл або CLI |
| `enter-phase <N>` | `enter_phase(phase)` `:724-730` | так |
| `add-step <id> <name> [--project]` | `add_step(step_id, name, situational)` `:732-737` | так |
| `start <id>` | `start_step(step_id)` `:739-743` | так |
| `done <id> <evidence…>` | `finish_step(step_id, evidence[])` `:745-754` | так; гейт — у скілі |
| `skip <id> [superseded-by]` | `skip_step(step_id, superseded_by)` `:756-760` | так |
| `block <id> <reason>` | `block_step(step_id, reason)` `:762-766` | так |
| `reviewer <vendor> <model> [step] [--review] [--mode]` | лише всередині `call_critic` `:942-1010` | частково: `step` не передається (`:976-982`); vendor виводиться з імені моделі |
| `target <preset> <curve>` | — (`process_writer.set_target` `:305-307` без викликів) | нема → CLI |
| `session-start <harness> <model> [resumed]` | — TCC пише сам на attach (`main_window.py:3629-3631`) | так, за задумом не інструмент моделі |
| `session-close` | — (нема ні в MCP, ні в UI, ні в handoff) | нема → CLI |
| `decision <q> <a> [step] [--invalidates]` | `record_decision(question, answer, step, invalidates)` `:768-780` | так |
| `capture-start <ver> [titles] [--step]` | `start_capture(version, expected, step)` `:795-809` | так |
| `capture-check [titles] [--session]` | `check_captures(titles)` `:782-793` | частково: без `--session` |
| `capture-taken <title>` | `record_capture(title)` `:811-816` | так |
| `capture-knobs NAME=POS…` | — (у піні `0cc96f6` команди ще нема — новіша за пін) | нема → CLI |
| `capture-protective <ch> OFF\|--hp…` | — у MCP; UI-діалог (`protective_dialog.py:268`, `measurement_panel.py:254`) | нема для моделі → CLI |
| `listening-verdict(s)` | — у MCP; UI (`listening_dialog.py:299`) | Арбітрів інструмент; для моделі — CLI |
| `capture-skip <title> <reason>` | `skip_capture(title, reason)` `:818-822` | так |
| `capture-close [reason]` | `close_capture(reason)` `:824-828` | так |
| `check` | — (`process_writer.check` `:398-400` без викликів) | нема → CLI |
| — | `get_tcc_state`, `get_pending_signals`, `ack_signals`, `wait_for_signal` | тільки TCC (сигнали UI) |
| — (`state.py registry render` / `v_NNN.json`) | `get_ledger(preset, version)` `:510` | читання ledger |
| — (`apply.propose`, бібліотека) | `propose_change` `:832-850` | **не банк** — лише картка (див. 🟠) |
| — (`rew_api.set_filters`) | `write_rew_filters` `:852-883` (з підтвердженням) | REW, не DSP |
| — (`helix-eq-export`) | `copy_helix_eq` `:885-903` (з підтвердженням) | буфер обміну |
| — | `show_curves` `:905-940` | тільки TCC |
| — (`scripts/autosound_ai.py`) | `call_critic(package, trace_path, model)` `:942-1010` | так, + запис `reviewer` без `step` |
| — (`dsp_profile.py`, `project.py set-car`) | `get_capability_checklist`, `check_existing_profile`, `check_existing_car`, `save_car`, `save_profile_field`, `reset_profile_field`, `finalize_profile` `:541-703` | інтейк-письмо через писарі скіла |

Що в CLI є, а в MCP нема (модель у TCC падає на CLI через гейт дозволу): `plan`, `target`, `session-close`, `capture-knobs`, `capture-protective`, `listening-verdict(s)`, `check`, `capture-check --session`. `SKILL.md:84` каже про fallback лише для рекордерів зі свого списку — про `session-close`/`target`/`check` як «CLI-only у TCC» не каже, а `call_critic`/`check_captures`/`get_tcc_state` у тому списку відсутні.
