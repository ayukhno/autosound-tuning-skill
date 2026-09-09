# Рецензія A — послідовність і логіка фаз (тільки читання)

Корінь: `/Users/o.yukhno/dev/autosound/skill/skills/autosound-tuning/` — шляхи нижче відносно нього
(`phases/…` = `references/phases/…`, `core/…` = `references/core/…`). Механізм звірено з
`rew_tool/state/process.py` (гейти `enter-phase`) на порожньому проєкті в скретчпаді, не в репо.

## Знахідки

### [🔴] Шлях «improve» −1 → 3 → 4 не проходить гейт `enter-phase 3`
**Де:** `phases/phase_-1_intake.md:5` «improve an existing tune (−1 → 3 → 4)»; `phases/virtual-first.md:24` «−1 → 3 → 4, with no new solos»; `rew_tool/state/process.py:133` `_require_target` (going ≥ 1, came_from < going → відмова), `:181` `_require_flaw_map` те саме.
**Що не так:** перевірено на насіннєвому проєкті: `enter_phase("-1")` → `enter_phase("3")` = «phase 3 needs a target curve»; далі відмовить порожній `acoustics.flaws[]`, якого шлях «без нових соло» не виробляє. Задокументований шлях механізм не пропускає.
**Як виправити:** у virtual-first «Improve» дописати два обовʼязкові кроки перед `enter-phase 3` — `process target` і мінімальна мапа вад (з наявних вимірів або `hypothesis`-рядки), або звільнити гейт за записаним `decision mode=improve`.

### [🔴] Virtual-first: мапа вад у 1.1 і жодного `process target` — `enter-phase 1` відмовить
**Де:** `phases/virtual-first.md:111-113` «**1.1** … the **flaw map** (Phase 0 §3.5)»; `SKILL.md:116` «`ellipsoid` (0.3 → 1.1)»; `phases/phase_0_baseline.md:17` «`enter-phase 1` refuses while `acoustics.flaws[]` is empty», `:19` «refuses while no target has been recorded». У `virtual-first.md` команда `target` не зустрічається (рядки 137/166/191/200 — лише «the target» як крива).
**Що не так:** на шляху virtual-first мапа будується вже «за столом» у Фазі 1, а вхід у Фазу 1 вимагає її і записаної цілі; крок запису цілі на цьому шляху відсутній узагалі.
**Як виправити:** додати у virtual-first крок **0.8**: `process target <preset> <curve>` + `flaw_map.py --write` / `project.py flaw …` — «без цього `enter-phase 1` відмовляє»; 1.1 переформулювати як *споживання* мапи, не побудову.

### [🔴] Раунд захвату ніде не відкривається — команди Фази 0 падають
**Де:** `phases/phase_0_baseline.md:66` `capture-protective`, `:69` `capture-knobs`, `:81` `capture-check --session`, `:75` `capture-close`; `rew_tool/state/process.py:1287` «no capture round is open: `capture-start <version> [expected ...]` first» (`set_knobs`, `set_protective` — `:877/:918` через `_require_capture`). `capture-start` у `phases/*` не згадується жодного разу (grep), лише `SKILL.md:84`.
**Що не так:** ранбук Фази 0 (і virtual-first 0.1–0.7, і блоки A–F sheet) наказує писати на раунд, який ніхто не відкрив; перевірено — `set_knobs` без раунду відмовляє.
**Як виправити:** перший рядок §3 phase_0: «`capture-start 1 $(naming.py <project> codes)` → свіпи → `capture-taken <title>` → …»; у capture-session-sheet блок D починати з `[capture-start]`.

### [🔴] §0.5 ставить `enter-phase -1` сьомим кроком, хоча він має бути першим
**Де:** `core/project-intake.md:61-69` кроки 0–8 без `enter-phase`; `:184` «`enter_phase("-1")` … it goes FIRST, before the first question, not somewhere in this list» — але це §5, тобто крок 7 списку; `phases/phase_-1_intake.md:27` ланцюжок теж без нього; `SKILL.md:84` «`enter-phase <N>` happens BEFORE you ask the user anything».
**Що не так:** модель, що йде «IN ORDER», доходить до відкриття фази після інтервʼю — саме та поломка, яку `:184` описує.
**Як виправити:** зробити його кроком 0 у §0.5 (`enter_phase("-1")` / CLI) і першою ланкою в `phase_-1:27`.

### [🔴] happy-paths шлях B читає стан зі старого джерела і з неіснуючого блоку
**Де:** `core/happy-paths.md:25` «Read `audit-trail.md`, the top ▶️ CONTINUE block of `tuning-changelog`, and `dsp-state-current`»; `:28` «continue from the ▶️ NEXT STEPS list» (назва більше ніде не визначена — єдине входження); vs `SKILL.md:69` «`process/process-state.json` … **not** `tuning-changelog`'s ▶️ CONTINUE block». У B немає кроку 0 (`deployment.py`, `SKILL.md:67`) і `contract.py check`.
**Що не так:** docs-check не ловить: `scripts/docs-check.py:154-158` спрацьовує лише на рядок із `tuning-changelog` **і** «active/current phase» — тут немає другого; `docs-check.py` зараз дає «docs OK».
**Як виправити:** B.1 переписати: `contract.py check` → `process.py … show` → ledger HEAD (`registry render`) → проза як перехресна перевірка; «NEXT STEPS» → план з `process.py … plan`.

### [🟠] «Шлях» означає три різні речі
**Де:** `phases/virtual-first.md:34-35` «There is no separate "iterative path" to choose. The path is one»; там же `:6-7` «The older iterative path … is the fallback», `:215` «Degradation — when the path falls back to iterative»; `core/process-phases.md:48` «Phase −1 picks it (or the iterative fallback)»; `phases/phase_0_baseline.md:5` (і phase_1/2/3:5) «**If** Phase −1 chose the virtual-first path»; `phases/phase_-1_intake.md:5` «picks the path: full … or improve».
**Що не так:** сесія не знає, чи `virtual-first.md` (20 КБ) читати завжди, чи лише «якщо обрано»; «шлях» = virtual/iterative, або full/improve, або деградація.
**Як виправити:** одне речення в phase_-1 і process-phases: «шлях один — virtual-first; деградація за таблицею втрат; режим = full | improve»; з чотирьох банерів прибрати «If … chose».

### [🟠] Вихід із Фази 0 — дві команди, звʼязок не названо
**Де:** `phases/phase_0_baseline.md:17,19` «`enter-phase 1` refuses…» vs `:171-174` «The boundary out of phase 0 — **one command**, not a memory: `contract.py check --phase0-gate`». У `process.py` «phase0» не зустрічається — `enter_phase` перевірку доказів не запускає.
**Що не так:** «одна команда» — неправда: `enter-phase 1` пропустить рядки без evidence.
**Як виправити:** один рядок: «два гейти: спершу `--phase0-gate` (докази), тоді `enter-phase 1` (ціль + непорожня мапа + факти профілю); другий перший не викликає».

### [🟠] §5 радить слабшу перевірку, яку phase_-1 прямо забороняє
**Де:** `core/project-intake.md:185` «`python3 rew_tool/contract.py check <project>` — should report every machine file present» vs `phases/phase_-1_intake.md:15` «**`--gate`, not plain `check`** … which an EMPTY project satisfies».
**Як виправити:** `--gate` у `:185`.

### [🟠] Дві нумерації кроків для тих самих фаз
**Де:** `SKILL.md:116` «(0.6) · (0.3 → 1.1) · (1.3) · (2.1 / 3.3) · (3.1) · (3.3)» і `phases/phase_4_listening.md:46` «the joints (1.3), the levels (1.4), the coarse EQ (2.1) or the fine EQ over MMM (3.3) … re-swept (3.2)» — це номери `virtual-first.md`; ранбуки фаз нумеровані інакше: phase_0 = 1, 2, 2.5, 3, 3.5, 4; phase_1 = 1–6 + 3.5; phase_2 = 2a–2d; phase_3 = 1, 2, 2.5, 3.
**Що не так:** «2.1» у phase_2 не існує; читач ітеративного ранбука не знайде кроків, на які його відсилає phase_4.
**Як виправити:** у SKILL.md:116 і phase_4:46 дописати «(virtual-first §…)», або перенумерувати ранбук phase_0 у 0.1…0.7 під sheet.

### [🟠] «Phase 6» не існує (фаз −1…5)
**Де:** `core/process-phases.md:32` «a failed Phase-5/6 ear check»; `core/project-intake.md:106` «a Phase-6 voicing move»; `rew_tool/state/process.py:50` `PHASES = ("-1", …, "5")`.
**Як виправити:** «Phase-4/5» і «Phase-5».

### [🟠] `eq_propose --rta` — такого прапора немає
**Де:** `phases/phase_3_control.md:7` «MMM fine EQ (`eq_propose --rta`…)»; прапори `rew_tool/eq_propose.py:492-506`: `--project --solos --rew --ver --process --house --ellipsoid --route --preset --allow-boost --accept --out --json`.
**Як виправити:** назвати реальну команду кроку 3.3 (або прибрати прапор).

### [🟠] `python3 rew_tool.py …` — файла в корені скіла немає
**Де:** `phases/phase_1_foundation.md:104`, `phases/phase_2_eq.md:29`, `:77` «`python3 rew_tool.py analyze-batch/analyze-joints`» vs `phase_1_foundation.md:37` «`python3 rew_tool/rew_tool.py analyze-joints`»; `SKILL.md:32` «every path … is relative to the skill root»; `rew_tool.py` у корені відсутній.
**Як виправити:** `rew_tool/rew_tool.py` у трьох місцях.

### [🟠] `scripts/docs-check.py` лежить не там, куди відсилає текст
**Де:** `core/process-phases.md:22,29` «checked by `scripts/docs-check.py`»; файл — `skill/scripts/docs-check.py` (корінь репо), у `skills/autosound-tuning/scripts/` його нема; за `SKILL.md:32` читач шукає під коренем скіла.
**Як виправити:** «(repo-level `scripts/docs-check.py`)» або прибрати згадку разом з історією.

### [🟠] «Three tools, three artifacts» — а їх чотири
**Де:** `phases/phase_0_baseline.md:89` «Three tools, three artifacts:» → пункти 1–4; `:97` «These four are a LIST».
**Як виправити:** «Four».

### [🟠] Проза всередині code-fence — команда `target` похована
**Де:** `phases/phase_0_baseline.md:43-48`: fence відкрито в `:43`, цитата «> **Two facts wear the name "target"…» у `:45` стоїть усередині, команда в `:46`.
**Як виправити:** винести `:45` під fence.

### [🟠] Захисні фільтри «as described in Phase 1» — у Фазі 1 їх не описано
**Де:** `phases/phase_0_baseline.md:60` «protective crossovers applied to ВЧ/СЧ as described in Phase 1»; насправді — `core/project-intake.md:113-121` (§3) і `phases/phase_-1_intake.md:27`. Там же кирилиця в англійському тексті (`phase_1:46` «фіксована логіка», `project-intake.md:116` «Правило розкриття стику»).
**Як виправити:** «→ project-intake.md §3», tw/m замість ВЧ/СЧ.

### [🟠] Жоден phase-файл не каже виконати `enter-phase N` на старті; virtual-first «log Phase» — після роботи в авто
**Де:** grep `enter-phase` у `phases/*`: лише як текст гейтів (`phase_0:17,19`, `phase_1:13`, `phase_2:16`); phase_-1/3/4/5 — нуль; єдиний наказ — `SKILL.md:84`. `phases/virtual-first.md:58` «log Phase −1», `:80` «Then the seat, then log Phase 0» (після 0.1 «v0 into the DSP») vs `SKILL.md:84` «entry condition … BEFORE you ask the user anything».
**Як виправити:** перший рядок кожного ранбука: «`enter-phase N` (TCC: `enter_phase`) — перш за все»; «log Phase» замінити командою і поставити перед 0.1.

### [🟠] TCC vs термінал: мапа інструментів є лише в SKILL.md, і половина CLI-команд без пари
**Де:** `SKILL.md:84` називає TCC-інструменти `enter_phase / add_step / start_step / finish_step / skip_step / block_step / start_capture / record_capture / skip_capture / close_capture / record_decision`. Без TCC-пари лишаються: `target` (`phase_0:17,46`), `capture-protective` / `capture-knobs` / `capture-check` (`phase_0:66,69,81`), `reviewer` (`SKILL.md:84`), `listening-verdict` (`phase_4:56`), `session-close` (`SKILL.md:73`). Обидві дороги дано лише в `core/project-intake.md:184` (`enter_phase("-1")` або CLI) і `§0.5:61` (`get_tcc_state`); `phase_4:53` згадує «a TCC panel», але дає тільки CLI; `rew_tool/state/process-schema.md:140` про TCC — лише «reads both files».
**Що не так:** у сесії з TCC модель не знає, чи для `target`/`capture-knobs`/`listening-verdict` є інструмент, чи треба падати в CLI.
**Як виправити:** одна таблиця «CLI ↔ TCC tool ↔ (нема → CLI і під TCC)» у SKILL.md або process-schema.md; у фазах — «(TCC: …)» лише там, де інструмент є; у `phase_-1:27` додати крок 0 «`get_tcc_state`».

### [🟠] happy-paths шлях A суперечить гейту Фази −1
**Де:** `core/happy-paths.md:11` «Write the answers into the project's `autosound_context.md`» — без машинних файлів, `enter-phase -1`, `contract.py check --gate`; vs `phases/phase_-1_intake.md:15` «a prose-only intake is not a complete one».
**Як виправити:** A.1: «+ `project.json`/`dsp_profile.json`/glossary/перший знімок ledger; `contract.py check --gate` = 0».

### [🟢] Вхід у Фазу 5 названо трьома способами
**Де:** `phases/phase_3_control.md:67` «Proceed to Phase 4 + any Phase 5 voicing» vs `phases/phase_5_variations.md:3` «locked front (Phases 1–3, verified in Phase 4)» vs `:13` «Center/rear only after the front satisfies».
**Як виправити:** одне речення в phase_3:67: «voicing — після lock; center/rear — після задоволення у Фазі 4».

### [🟢] Стиль посилань змішаний
**Де:** `core/process-phases.md:40-46` і `phases/*` — від кореня (`references/…`); `phases/virtual-first.md:67`, `phases/capture-session-sheet.md:3` — сусідні (`capture-session-sheet.md`).
**Як виправити:** один стиль (від кореня, за `SKILL.md:32`).

### [🟢] Helix-специфіка в загальних фазах
**Де:** `phases/phase_0_baseline.md:57-60` «Helix PC-Tool», `phases/phase_1_foundation.md:24` «`<prefix>_v1_foundation.pct6`», `:76-79`; SKILL.md заявляє «ANY car/system».
**Як виправити:** «як увести в DSP» → `knowledge/dsp/<vendor>.md`, у фазі — один рядок-посилання.

## Таблиця токенів по фазах

Обовʼязкове = SKILL.md + активна + сусідня + те, що вони наказують читати («Read … alongside», «Follow», «read them», «Run … §0.5», вхідна умова). У дужках — часто потрібне, але не наказане.

| фаза | файли, що читаються | байт разом |
|---|---|---|
| −1 | SKILL (25 258) + phase_-1 (2 993) + phase_0 (22 121) + project-intake.md весь (41 565; `:25` «Run … §0.5» → §0–§5) + virtual-first (20 280; `:5` −1.1…−1.4) + capture-session-sheet (6 929; −1.4) | **119 146** |
| 0 | SKILL + phase_0 + phase_1 (16 185) + virtual-first (`:5` «Read alongside») + capture-session-sheet (`:7`) + naming-and-structure (17 438; `:38` «Follow») + project-intake §3 (6 281; `:66`) | **114 492** |
| 1 | SKILL + phase_1 + phase_2 (15 981) + virtual-first + project-intake §3 (вхідна умова `:11`) (+ filter-types 16 748 «refer to») | **83 985** |
| 2 | SKILL + phase_2 + phase_3 (6 615) + virtual-first (+ diagnostic-techniques 67 522 — §13/§3/§9/§50 «see») | **68 134** |
| 3 | SKILL + phase_3 + phase_4 (10 762) + virtual-first (+ analysis-playbook 15 013 «method in», review-loop 9 173) | **62 915** |
| 4 | SKILL + phase_4 + phase_5 (8 166) + listening-cheat-sheet (12 192) + test-tracks (24 739) — `:39` «Do not restate them here — read them» (+ feedback-loop 16 455 при закритті) | **81 117** |
| 5 | SKILL + phase_5 (+ voicing-by-ear 11 067, preference-profile 2 410, preset-strategy 4 725 «refer to»; + phase_4 для закриття `:81`) | **33 424** |

Два числа, що визначають картину: **SKILL.md = 25 КБ у кожній фазі** (37 % читання Фази 2) і **virtual-first.md = 20 КБ у кожній з Фаз 0–3** (через «Read alongside» + знахідку про «шлях»).

Частка абзаців з історією («bought», «a real session/run», «Until 2026-…», `SCR-/CAR-/RES-/HUB-`, «skill #», дати) від обсягу файла: SKILL.md **40 %** (10 031 Б), phase_0 **44 %** (9 848), phase_2 **46 %** (7 397), virtual-first **41 %** (8 301), phase_4 **41 %** (4 380), phase_1 **38 %** (6 071), process-phases **26 %**; phase_-1, phase_3, phase_5 (крім прикладу), capture-session-sheet, happy-paths — 0 %. (Абзац рахується цілком, тож це верхня межа; чисту історію оцінено нижче по секціях.)

## Що можна злити/скоротити

Скорочення до одного речення + id (hub `RES-…`/`SCR-…`/skill `#N`) або посилання на CHANGELOG:

| файл : рядки | що там | до → після (Б) |
|---|---|---|
| `virtual-first.md:233-247` | «Tool gaps still open — None left open» — чиста історія | 1 204 → 0 |
| `virtual-first.md:125-161` | підпункти 1.5: RES-006/RES-007 оповіді; лишити 5 правил по рядку (predict-only, `--from-state`, два вікна, knobs-відмова, `--delta-vs`/`--ladder`) | 3 482 → ~1 500 |
| `virtual-first.md:3-10` | заголовок з датами валідації | 759 → ~300 |
| `phase_0:130-165` | `--why`/`--symptom`/`KIND_HEARD`/`DRAFT` + CAR-007 + skill #22 | 3 336 → ~1 000 |
| `phase_0:185-205` | історія гейта до 2026-09-08 + `gaps`; лишити команди + 1 речення | 1 440 → ~400 |
| `phase_0:68-79` | knobs (RES-007 втретє; оригінал — `project-intake.md` §5 «What sits OUTSIDE the DSP») | 1 108 → ~350 |
| `phase_0:97-112` | «LIST, not a sequence»: лишити таблицю, прибрати оповідь (inbox 3.6) | 1 713 → ~900 |
| `phase_0:81` | `capture-check` (SCR-040): команда + 2 речення | 2 190 → ~700 |
| `phase_0:5`, `phase_1:5`, `phase_2:5`, `phase_3:5` | один і той самий банер ×4 (по 381 Б); лишити другий, специфічний банер (`:7`) | 1 524 → ~480 |
| `phase_1:43-52` | «CRITICAL RULE … (Lesson 2026-06-27)»: правило = onset вручну, відняти активні затримки DSP, найпізніший = 0 ms | 1 713 → ~700 |
| `phase_1:89` | інцидент `_DEMO_CFG` | 827 → ~250 |
| `phase_1:11` | вхідна умова з поясненням «because a real run…» | 1 410 → ~600 |
| `phase_2:75`, `:77` | «tripped twice», analyze-joints з обґрунтуванням | 2 630 → ~1 350 |
| `phase_4:65-75` | фініш: форма фідбеку + вилка; текст про Sponsors → `feedback-loop.md` | 2 917 → ~1 500 |
| `SKILL.md:84` | гардрейл «Write the PROCESS»: лишити перелік команд + по одному «чому» | 2 990 → ~1 500 |
| `SKILL.md:69` | крок 2 з історією CAR-007 | 1 464 → ~800 |
| `SKILL.md:43-51` | «more than one candidate… not rare» | 872 → ~400 |
| `SKILL.md:107` | «(This line used to say the opposite of step 2, twenty-three lines apart.)» | 80 → 0 |
| `process-phases.md:10-29` | історія HUB-035 і назви чужого інструмента; лишити цитату + 2 рядки | 1 630 → ~450 |
| `phase_5:71-75` | польовий приклад rear-fill — не різати, **перенести** в `knowledge/cars/` | 1 432 → посилання |

Дублі-доктрини (де оригінал → де копії; копію замінити рядком-посиланням):
- **Захисний фільтр «в записі» / `OFF` за замовчуванням (2026-08-24, 2026-09-06):** оригінал `project-intake.md:121` («One home for the rule») → копії `phase_0:66`, `phase_1:37`, `phase_2:77`, `virtual-first.md:64-66,110-111`.
- **Ручки поза DSP (RES-007):** оригінал `project-intake.md` §5 → `phase_0:68-79`, `virtual-first.md:151-157`.
- **«Вухо не перевіряє рядок мапи» (skill #22):** оригінал `phase_4:3` → `phase_0:137-145`, `phase_0:185-189`, `phase_4:22`.
- **Джерело фази = process-state.json:** оригінал `SKILL.md:69,107` → `process-phases.md:10-15` (цитата — гаразд, її перевіряє docs-check), але `happy-paths.md:25,28` — протилежне (🔴 вище).
- **Re-entrancy гейтів:** `process-phases.md:32` → `happy-paths.md:41`, `phase_3:57` — норма, по одному реченню.

Разом реальних скорочень ≈ **20 КБ із 144 КБ** зони (≈14 %); читання Фази 0 падає зі 114 до ~100 КБ. Більший виграш дає не скорочення, а рішення 🟠 «шлях»: якщо virtual-first — єдиний шлях, банери в 4 фазах і «If … chose» зникають, а якщо ні — 20 КБ virtual-first перестають бути обовʼязковими на ітеративному ранбуку.
