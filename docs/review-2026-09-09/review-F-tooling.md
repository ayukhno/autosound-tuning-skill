# Рецензія F — інструментальна документація скіла (режим: тільки читання)

Корінь: `skills/autosound-tuning/`. Дата: 2026-09-09. Рядки — з `cat -n` на момент огляду.

## Зведення (5 рядків)

1. **Два реєстри інструментів.** `core/capabilities.md` — 91 рядок, 95 % таблиця, звіряється кодом (`python3 rew_tool/capabilities.py --selftest` → «OK — 91 board rows», у наборі через `scripts/run-selftests.sh` L85-93). `tooling/rew-tool-docs.md` — 59 КБ, 0 % таблиць, 43 прозових буліти, **ніким не перевіряється**. `capabilities.py` НЕ генерує — лише звіряє (docstring L2-8), тож ~30 інструментів описано двічі, а `rew-tool-docs.md` не має жодного гарда.
2. **Застаріле/хибне у зоні:** `rew-tool-docs.md` L16 «stdlib only» (numpy обов'язковий, `requirements.txt` L18-20); три зламані відносні посилання L109/L110/L113; особиста тека автора як дефолт кривих `rew_tool.py` L20-22; команда `resonalyze_ir.py` в обох реєстрах без обов'язкових `--out`/`--session…` — argparse її відкидає; `start_gemini_tuner.sh` запускає лише закритий `gemini` і радить `npm i -g @google/gemini-cli` (L74).
3. **Рецензент:** `setup-critic-channel.md` — 24 КБ есе без 5-рядкового «щасливого шляху»; §4 відсутній, «manual channel (§6)» тричі веде у smoke-test (§6), а manual — §7; три внутрішні суперечності про моделі; два доктори дають різні вердикти (`gemini_critic.sh --doctor` → «works ✓», `autosound_ai.py doctor` → «ПОТРЕБУЄ ВИПРАВЛЕННЯ ✗» і обіцяє API-режим із `agy`-слагом, який сам же `critic` відмовиться слати); `autosound_ai.py --help` → «Невідома роль».
4. **Обіцянки про ключ у доці виконують 2 з 6 обгорток:** `_claude_common.sh`/`_codex_common.sh` читають лише проєктний `.critic-env`, `source`-ять його і не мають guard'а — усупереч §3 L66/L111-116/L125.
5. **Вивід і залежності:** `--help` у `predict`/`verify_prediction` пояснює, що означає число; `eq_propose`/`ear_suspects`/`ellipsoid` — голі прапорці без «як читати». `requirements.txt` — єдине джерело залежностей (`pyproject.toml` — тільки ruff, свідомо; `install.sh` L776-799 ставить `-r requirements.txt` у той `python3`, що на PATH — тут 3.9.6, «known-good 3.12» L15-16). Мінімальна версія Python не названа ніде.

## Знахідки

### 🔴 «stdlib only» у реєстрі інструментів — неправда
**Де:** `references/tooling/rew-tool-docs.md:16` — «uses standard library only — no external dependencies»; проти `requirements.txt:18-20` — «Required. Imported at module scope by curve_view, dsp_math, eq_gate, make_plot and xover_select … numpy>=1.24»; і проти самого файлу L45 «deps: numpy + **scipy**», L79 «numpy + scipy».
**Що не так:** перше речення розділу «Tool Directory Layout» суперечить власним булітам і інсталятору; модель, що читає «на вимогу», повірить першому.
**Як виправити:** замінити на один рядок: «numpy обов'язковий; scipy/matplotlib — ліниво, `requirements.txt`».

### 🔴 Команда з індексу відкидається argparse — індекс «перевірений», але не запускається
**Де:** `references/core/capabilities.md:39` — «`resonalyze_ir.py --title "w-L_49 (sw)" --process <proj>/process`»; `rew-tool-docs.md:73` — «`--title … --out DIR [--hpf …] [--process …] …`»; код `rew_tool/resonalyze_ir.py:629` — «`--out and at least one --title/--id are required`», L632-633 — «exactly one of --session PATH / --session-name NAME / --session-unknown is required»; `rew-api-quirks.md:8` це каже прямо.
**Що не так:** `capabilities.py` звіряє, що прапорець *існує* в джерелі (L153-155), а не що рядок *запускається*: рядок L39 без `--out` і без `--session…` проходить селфтест і падає в argparse. Обидва реєстри мовчать про обов'язковий `--session…`.
**Як виправити:** у L39 і L73 дописати `--out DIR --session-unknown|--session PATH`; у `capabilities.md:17-18` сказати чесно: «названі прапорці існують; що команда повна — не перевіряється».

### 🔴 Правила про ключ у доці не виконують claude/codex-обгортки
**Де:** `scripts/_claude_common.sh:6-8` — «for _env in "$PWD/rew_analitic/.critic-env" "$PWD/.critic-env"; do … set -a; . "$_env"»; те саме `scripts/_codex_common.sh:6-8`. Проти `setup-critic-channel.md:66` — «both the shell wrappers and `autosound_ai.py` read it from there first» (машинний файл), L125 — «The file is read as `KEY=VALUE`, never executed», L111-113 — «Both doors refuse the dangerous case».
**Що не так:** 4 із 6 обгорток (claude_*, codex_*) не читають `~/.config/autosound/critic-env`, виконують проєктний файл як shell і не мають `_critic_guard`. Доку написано про gemini-двері; SKILL.md L171 подає всі три вендори як рівні.
**Як виправити:** винести парсер `KEY=VALUE` + `_critic_guard` + порядок файлів із `_gemini_common.sh` L28-90 у спільний `_critic_env.sh`, підключити в усі три `_*_common.sh`.

### 🔴 Три суперечності про моделі всередині `setup-critic-channel.md`
**Де:** (а) L46 — «Advisor / routine | `gemini-3.5-flash-medium`», L57 — «Flash remains the advisor/routine default» проти L262 — «**Both roles now default to Pro.**»; код: `scripts/gemini_advisor.sh:39` — «`PRIMARY_MODEL="${GEMINI_ADVISOR_MODEL:-$(gemini_default_critic_model)}"`» (Pro), а `scripts/.critic-env.example:34` — «`GEMINI_ADVISOR_MODEL=gemini-3.5-flash-medium`» (Flash). (б) L53 — «`gemini-2.5-pro` / `gemini-2.5-flash` … answered `404 … no longer available`» проти L55 — «a raw `GEMINI_API_KEY` call wants the `gemini-2.5-*` id». (в) L268 — «both forms were accepted as of 2026-08-01» проти L55/L129 — display label «rejected since agy 1.1.12».
**Що не так:** дефолт радника залежить від того, чи скопіював користувач example-файл; L55 радить id, який L53 назвав мертвим; L260-268 — застарілий блок від 2026-08-01, не знятий після правок 09-08.
**Як виправити:** один дефолт (у коді й у example однаковий), L55 → «`gemini-pro-latest`/`gemini-flash-latest`», блок L260-268 видалити (його висновок уже в L57).

### 🟠 Нумерація секцій рецензентської доки зламана
**Де:** заголовки — L5 «## 0.», L11 «## 1.», L41 «## 2.», L62 «## 3.», L140 «### Any vendor…», L192 «## 5.», L206 «## 6. Smoke-test», L215 «## 7. No CLI … manual channel». Посилання: L3 «(§1–§4)», L6 «§1–§4 or §7», L38 «fall back to manual channel (§6)», L39 «copy-paste desktop channel (§6)», L57 «manual channel §6».
**Що не так:** §4 нема (SCR-033-блок L140 — «###»); три відсилання на «manual §6» ведуть у smoke-test. SKILL.md L172 правильно каже «§7».
**Як виправити:** L140 → «## 4.», три «§6» → «§7».

### 🟠 Два доктори — два вердикти, і `autosound_ai.py doctor` обіцяє те, чого `critic` не зробить
**Де:** живий запуск: `scripts/gemini_critic.sh --doctor` → «== The reviewer channel works ✓»; `scripts/autosound_ai.py doctor` → «▶ Рецензент: gemini-3.8-flash-high → провайдер google / ▶ Режим роботи: АВТОМАТИЧНИЙ (через API google) / ПОТРЕБУЄ ВИПРАВЛЕННЯ ✗». Код: `autosound_ai.py:603` — «model = resolve_model("critic")» → L461-476 `_first_cli_model()` бере перший слаг `agy models`; L640-641 — «if api_provider: print("▶ Режим роботи: АВТОМАТИЧНИЙ (через API …")» за *наявністю* ключа; але робочий шлях L833-845 з ключем і без названої моделі друкує список і «sys.exit(3)».
**Що не так:** доктор називає моделлю `agy`-слаг, який сам файл (L836-838) називає «not an API id … 404», і режим «через API» при ключі, що відповів HTTP 400. Модель у першому запуску отримує два протилежні висновки.
**Як виправити:** у доктора та ж гілка, що в L833-845: «модель не названа → список → вибери»; «АВТОМАТИЧНИЙ» друкувати лише після живого `list_gemini_models`. Один доктор, на який посилаються обидві доки.

### 🟠 `autosound_ai.py --help` — помилка замість usage
**Де:** живий запуск — «Невідома роль: --help. Підтримуються: critic, advisor, doctor»; код `scripts/autosound_ai.py:738-751` — usage лише при `len(sys.argv) < 2`.
**Як виправити:** `-h/--help` → надрукувати L14-16 docstring і вийти 0.

### 🟠 Три зламані посилання в `rew-tool-docs.md`
**Де:** L109 «[analysis-playbook.md](references/core/analysis-playbook.md)», L110 «(references/core/diagnostic-techniques.md)», L113 «(references/tooling/rew-api-quirks.md)» — відносно `references/tooling/` жоден не існує (перевірено `test -f`).
**Як виправити:** `../core/…`, `rew-api-quirks.md`.

### 🟠 Дефолтна тека цільових кривих — особиста тека автора
**Де:** `rew_tool/rew_tool.py:20-22` — «DEFAULT_CURVES_DIR = os.path.expanduser("~/Documents/home/EMMA_2026-05/7. HelixDSP v4 ResoNix_ACС/…")»; `capabilities.md:99` — «`rew_tool.py analyze-batch "_2 (rta)"`» (needs: «target curves per channel», без `--curves-dir`); `rew-tool-docs.md:98` — теж без прапорця; наслідок у коді L239 «Цілі з: …» і L256-260 «(немає цілі)» у кожному рядку.
**Що не так:** на будь-якій іншій машині команда з індексу мовчки дає таблицю з прочерками. Проєктні криві живуть у `rew_analitic/target-curves/<name>/` (`project-intake.md:193`), а поточна ціль — `state.current_target` (`capabilities.md:86`).
**Як виправити:** дефолт → з проєкту (`state.current_target`) або обов'язковий `--curves-dir`; у L99/L98 показати прапорець.

### 🟠 `start_gemini_tuner.sh` живе для закритого CLI
**Де:** `scripts/start_gemini_tuner.sh:74` — «die "no Gemini CLI on PATH — npm i -g @google/gemini-cli, then re-run"»; L76-79 — запуск лише для `case … gemini)`, для `agy` (L80-82) — «start it yourself and paste»; L34-35 гідрує 2.x-файли `dsp-state-current*`/`tuning-changelog*`. `rew_tool/capabilities.py:100` — «"start_gemini_tuner.sh": "a launcher for one vendor's CLI (setup-critic-channel.md)"» — у тій доці 0 згадок; `core/driver-discipline.md:3` досі: «Solo-Gemini sessions start best via `scripts/start_gemini_tuner.sh`».
**Як виправити:** видалити скрипт і рядок у driver-discipline.md, або переписати під `agy` (без авто-`GEMINI.md`) і вказати справжню доку в `NOT_ON_BOARD`.

### 🟠 Доктор gemini виконує проєктний `.critic-env`
**Де:** `scripts/_gemini_common.sh:409` — «if ( set -a; . "$envf" ) 2>/tmp/_ce_err; then echo "✓ .critic-env: $envf parses"»; проти `setup-critic-channel.md:125` — «never executed».
**Як виправити:** синтаксис перевіряти тим самим `KEY=VALUE`-парсером L28-40.

### 🟠 `capabilities.md` шле за `eq_export.py` у доку, де його нема
**Де:** `capabilities.md:102` — «`eq_export.py <proj> tw-L --out tw-L.atf` … read: `tooling/helix-eq-export.md`»; `helix-eq-export.md` — 0 входжень `eq_export`; її шлях — REW-буфер + `atf_eq.py` (L23-31).
**Як виправити:** у `helix-eq-export.md` додати 8-10 рядків «з леджера: `eq_export.py … --fmt generic|atf`», або в L102 «read» → `rew-tool-docs.md` (`eq_export`).

### 🟠 14 покажчиків «читай `rew-tool-docs.md`» ведуть у 59 КБ по один буліт
**Де:** колонка read у `capabilities.md`: «`tooling/rew-tool-docs.md`» ×3 без якоря, «(`predict`)» ×2, «(`windows`)» ×2, «(`timebase`)» ×2, `dsp_math`/`equal_loudness`/`path_check`/`rew_stub`/`xover_select` ×1; L8-9 — «the facts live where the pointer says (`tooling/rew-tool-docs.md` for the modules)».
**Що не так:** щоб дізнатись прапорці `predict`, модель читає 59 КБ (буліт `predict` L80 — 5 928 Б), хоча `python3 rew_tool/predict.py --help` віддає те саме структуровано.
**Як виправити:** read → «`--help`» для модулів із CLI; `rew-tool-docs.md` — лише для бібліотек без CLI.

### 🟠 Три конвенції запуску
**Де:** `rew-tool-docs.md:18` — «cd <skill-dir>/rew_tool && python3 rew_tool.py …», L20 — «add … to your `PYTHONPATH`»; `capabilities.md:17` — «`rew_tool/capabilities.py --selftest`» (з кореня), рядки L24-L122 — голі «`predict.py …`», а L157/L170 — «`gates/side_effect.py`», «`rew_tool/deployment.py`». Код працює звідусіль (`rew_tool.py:13` sys.path.insert; перевірено `python3 rew_tool/predict.py --help` з кореня).
**Як виправити:** одна форма всюди: `python3 <skill>/rew_tool/X.py …`; прибрати пораду про PYTHONPATH.

### 🟠 Логін-інструкція `agy` двічі в одному файлі
**Де:** `setup-critic-channel.md:25-37` (EN) і L227-258 «## FAQ / Часті Питання (Agy Login Flow)» (UK) — той самий сценарій Project ID → OAuth → `/quit`, ~2,5 КБ.
**Як виправити:** лишити один (UK-версія точніша про Project ID), інший — посиланням.

### 🟠 `skill_metrics.sh` — мертвий гард, і він провалюється
**Де:** `scripts/skill_metrics.sh:10-11` — «SKILL.md words ≤ 1500 … defensive markers ≤ 15»; живий запуск — «3298 (max 1500) … 26 (max 15) … METRICS FAIL»; підключений ніде (grep по репо — лише власний заголовок; `run-selftests.sh` його не кличе).
**Як виправити:** або підняти межі й додати в `run-selftests.sh`, або видалити.

### 🟠 `smoke_test.py` — «stdlib-only», але імпортує numpy; згадує закритий `gemini`
**Де:** `scripts/smoke_test.py:7` — «Offline + stdlib-only»; L107 «import resonalyze_ir» → `rew_tool/resonalyze_ir.py:101` — «import numpy as np»; `capabilities.md:172` — needs «python3, numpy, scipy». L133 — «shutil.which("agy") or shutil.which("gemini")», L136 — «none (agy/gemini not on PATH → Clipboard Mode)».
**Як виправити:** L7 → «numpy потрібен»; L133-136 — тільки `agy`.

### 🟢 Дрібне
- `rew-api-quirks.md:7` — «in `research`'s `experiments/code/resonalyze-cross-check/pull_irs.py`» — шлях не існує в цьому репо (`ls`: No such file); без назви репо не резолвиться.
- `rew-tool-docs.md:5-10` «API Connectivity» дублює `rew-api-quirks.md:1-6` і `capabilities.md:31` (`REW_API_URL`).
- `scripts/gemini_critic.sh:17-21` — заголовок досі описує `gemini`-флейвор: «gemini gemini-2.5-pro», «--skip-trust for @google/gemini-cli».
- `helix-vcp-workflow.md:120` — «this car's current choice → `dsp-state-current`» (2.x-носій; так само `SKILL.md:83`); у 3.x стан — «`state.py --root <proj>/state … render`» (`capabilities.md:141`). Два носії «поточного стану» в доках.
- `capabilities.md:155` — needs «`.critic-env` (or clipboard mode)» — машинний файл `~/.config/autosound/critic-env` (setup L69-71) не названий.
- `rew-tool-docs.md` — 12 дат, 12 hub-id, 36 «measured/verified/field»: історія змін у довіднику (напр. L80 «until 2026-09-08 the live path was peak-normalised … hub RES-005»). Місце — CHANGELOG.
- `setup-critic-channel.md:167` — «Local CLI: `agy`, `gemini`» для google — `gemini` закритий (той самий файл L49).
- `rew-tool-docs.md` не має 12 модулів, які є в `capabilities.md`: `car_profile`, `contract`, `deployment`, `naming`, `project`, `state/{state,process,apply,migrate}`, `gates/{presweep_safety,side_effect}`, `console` — «Module Overview» (L22) неповний, і це ніхто не ловить.
- `verify_measurements.py` — лише в `rew_tool/verify.py:4` як історія («This replaced …»); застарілих посилань нема. ✓
- `capabilities.py:21-24` чесно каже, що глибина не перевіряється; але `capabilities.md:17-18` обіцяє «keeps this board honest» без цього застереження.

## Рецензент як «перший раз» (п. 3 завдання)
Шлях по `setup-critic-channel.md`: §0 (fallback) → §1 install+Gatekeeper+login+Project ID+enable API+billing (L17-39) → §2 моделі з ⛔-абзацом на 8 рядків (L49-53) → §3 ключ/файл/curl/дві історії (L62-138) → «Any vendor» (L140-190) → §5 CWD (L192-204) → §6 smoke (L206-213) → §7 manual (L215-223) → FAQ → два застарілі блоки. **11 кроків, жодного 5-рядкового «зроби так»**; узгодженість із `--doctor` — часткова (доктор gemini покриває §1-§3+§5+§6; `autosound_ai.py doctor` — інше, див. 🟠 вище).

Щасливий шлях, якого бракує (5 рядків, усе з наявного):
```
brew install --cask antigravity-cli && agy                                   # логін один раз (OAuth, Project ID)
mkdir -p ~/.config/autosound && cp scripts/.critic-env.example ~/.config/autosound/critic-env && chmod 600 ~/.config/autosound/critic-env
cd <проєкт>            # rew_analitic/autosound_context.md + data-contract-template.md мають бути (їх пише intake)
scripts/gemini_critic.sh --doctor                                            # один вердикт
scripts/gemini_critic.sh package.md [trace.csv]                              # → «— [critic: <model>]»
```

Що з цього має робити застосунок TCC, а не користувач: (1) створити машинний файл ключа з `chmod 600` і взяти ключ полем, а не `cp`/`chmod` руками (L69-71); (2) показати список моделей ключа меню — `autosound_ai.py` уже друкує його й виходить 3 (L175-177), лишилось показати; (3) скопіювати `data-contract-template.md` у `rew_analitic/` і тримати `autosound_context.md` синхронним із леджером — зараз це ручний `cp` (`project-intake.md:196`) і попередження «stale context» (setup L204); (4) передати `PROJECT_MIRROR`, бо TCC знає теку проєкту — правило «launch from the project directory» (L200) зникає; (5) запустити один доктор і показати один вердикт. Користувачеві лишаються OAuth-логін `agy` і вибір моделі.

## Дублі capabilities.md ↔ rew-tool-docs.md

| інструмент | capabilities.md (рядок) | rew-tool-docs.md (рядок) | різниця |
|---|---|---|---|
| `resonalyze_ir.py` | L39 `--title … --process …` | L73 `--title … --out DIR [--hpf] [--process] [--play-channel] [--sweep-seconds]` | caps без `--out`; обидва без обов'язкового `--session…` |
| `predict.py` | 8 рядків: L65, L70, L110, L111, L115-119, L121 | L80 (один буліт 5 928 Б) | одні прапорці втретє у `--help` — він найкращий із трьох |
| `verify_prediction.py` | L112, L113, L119, L120 | L81 | однакові; `--help` повніший (`--entry-criterion`, `--entry-delay`, `--steady`) |
| `eq_propose.py` | L96 `… --out DIR [--accept a,b]` | L91 `… --solos DIR\|--rew --ver N …` | caps має `--accept`, docs — `--rew`; в обох нема `--process`, `--preset` |
| `ear_suspects.py` | L100 `--rew --title … [--process DIR --round 2]` | L92 `--rew --title` / `--file curve.txt` | caps без `--file`; обидва без `--phon/--top/--q-ceiling` |
| `ellipsoid.py` | L95 | L90 | однакові |
| `level_offsets.py` | L28 | L65-66 | тотожні речення |
| `spot_check.py` | L104 | L57 | дослівно та сама команда |
| `timebase.py` | L34, L51 `--title _49 \| --all` | L83 `--all \| --title SUBSTR \| --id N [--json]` + коди виходу | caps без `--id`, `--json`, exit-кодів |
| `rew_stub.py` | L38 | L93 | тотожні |
| `eq_export.py` | L102 `<proj> tw-L --out tw-L.atf` | L77 `<project> <channel> [--preset] [--version] [--fmt] [--out FILE]` | caps без `--fmt/--preset/--version` |
| `setup_import.py` | L27 `… [--atf m-L=m-L.atf] [--write]` | L48 `--atf code=file` | те саме, інша форма |
| `equal_loudness.py` | L88 | L70 | однакові |
| `phase_rotation.py` | L68 `180 500 [--fs Hz]` | L52 | однакові |
| `xover_candidates.py` | L25 повна команда | L47 проза без CLI | caps повніший |
| `crossover_checks.py` | L26 повна команда | L49 без CLI | caps повніший |
| `flaw_map.py` | L24 повна команда | L46 без CLI | caps повніший |
| `dsp_profile.py` | L30 `effects`, L140 `list-bundled … checklist` | L74 лише `list-bundled`, `refresh` | docs відстає (нема `effects`, `validate`, інтерв'ю) |
| `resonalyze_vc.py` | L114 `session.json --project P` | L85 `… [--profile] [--group] [--map] [--json]` | caps коротший |
| `verify.py` | L49-50 | L87 | однакові; docs має `--band`, `--json` |
| `listening.py` | L128 | L84 | однакові |
| `rew_tool.py` batch/joints | L64, L99 | L95-100 (3 715 Б) | обидва без `--curves-dir`, `--state-root` |
| `path_check.py` | L122 | L94 | однакові |
| `project_seed.py` | L137, L139 | L75 | однакові прапорці |
| лише в caps | `car_profile`, `contract`, `deployment`, `naming`, `project`, `state/*`, `gates/*`, `scripts/*` | — | 12 модулів, яких «Module Overview» не має |
| лише в docs | — | L35 `analysis.first_arrival`; L38-41 `joint_analysis.timing_drift_audit/phase_trust_gate/shelf_vs_bell…`; L50 нутрощі `dsp_math` | бібліотечні, без CLI — єдине, що виправдовує docs |

Перевірка: мій скрипт (`scratchpad/check_docs.py`) звірив усі `--прапорці` та `module.function` з 43 булітів `rew-tool-docs.md` проти джерел — 0 розбіжностей. Тобто docs не бреше про *існування*, а дублює й мовчить про *обов'язкове*.

## Розміри й пропозиції

| файл | байт | пропозиція «до → після» |
|---|---|---|
| `tooling/rew-tool-docs.md` | 59 195 | 59 → ~6 КБ: індекс «модуль → одне речення → `--help`» (43 рядки ≈ 3 КБ); «API Connectivity» L5-10 → у quirks; історію (12 дат / 12 hub-id) → CHANGELOG; бібліотеки без CLI (`dsp_math`, `joint_analysis`, `xover_select`, `analysis`, `curve_view`, `protective`, `windows`) — по 2-3 рядки або в docstring |
| `core/capabilities.md` | 38 736 | 38 → ~28 КБ: лишити (95 % таблиця, звіряється); 5 найдовших рядків (L139 781 Б, L25 756, L27 727, L24 710, L26 705) — до ≤ 300 Б; 14 покажчиків на rew-tool-docs → `--help`; дописати обов'язкові прапорці (L39) |
| `tooling/setup-critic-channel.md` | 24 090 | 24 → ~10 КБ: 5-рядковий шлях зверху; §-нумерація; прибрати FAQ-дубль L227-258 і застарілий L260-268; таблицю вендорів L165-169 лишити |
| `tooling/rew-api-quirks.md` | 31 733 | без змін розміру; прибрати дубль «API connectivity» і чужий шлях L7 |
| `tooling/helix-phase-allpass.md` | 15 974 | без змін (узгоджений із кодом: L123, L148) |
| `tooling/resonalyze-virtual-dsp.md` | 17 545 | без змін |
| `tooling/helix-vcp-workflow.md` | 6 234 | без змін; L120 `dsp-state-current` → `state.py … render` |
| `tooling/helix-eq-export.md` | 5 507 | +10 рядків про `eq_export.py` (леджер → ATF/Generic) |
| `tooling/screen-read-dsp.md` | 5 138 | без змін |
| `scripts/autosound_ai.py` | 55 731 | додати `-h/--help`; доктор — та сама гілка, що робочий шлях L833-845 |
| `scripts/_gemini_common.sh` | 30 478 | парсер `.critic-env` + guard → спільний `_critic_env.sh`; L409 без `source` |
| `scripts/_claude_common.sh` / `_codex_common.sh` | 4 511 / 4 687 | підключити спільний парсер + guard; читати машинний файл |
| `scripts/start_gemini_tuner.sh` | 4 045 | видалити або переписати під `agy` |
| `scripts/skill_metrics.sh` | 2 253 | підключити в `run-selftests.sh` з новими межами або видалити |
| `scripts/smoke_test.py` | 6 294 | L7 «numpy потрібен»; L133-136 без `gemini` |
| `scripts/gemini_critic.sh` | 3 499 | заголовок L17-21 без `gemini`-дефолтів |
| `requirements.txt` | 1 507 | назвати мінімальний Python (працює на 3.9.6; «known-good 3.12»); `pyproject.toml` — лише ruff, свідомо (L1-3) ✓; `install.sh` L776-799 ставить саме цей файл ✓ |

## Ясність виходу (п. 5)
- `predict.py --help` — пояснює прапорці й межі («Every number says which», «ILL-POSED said out loud»), але «як читати таблицю» — тільки в `rew-tool-docs.md:80`.
- `verify_prediction.py --help` — є семантика `--entry`/`--steady`/`--project`; поріг «≤ 1 dB → TRUSTED» — лише в docs L81 і caps L113.
- `eq_propose.py --help`, `ear_suspects.py --help` (`--title TITLE`, `--phon PHON`, `--top TOP` без тексту), `ellipsoid.py --help` — голі прапорці, нуль про вивід.
- Пропозиція: `epilog` на 3-5 рядків «як читати цей вивід» + перелік ключів `--json` у кожному CLI; тоді колонка «what you get» у `capabilities.md` може стати вдвічі коротшою, а `rew-tool-docs.md` — індексом.
