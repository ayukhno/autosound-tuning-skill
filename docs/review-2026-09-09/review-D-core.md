# Рецензія D — протокольне ядро скіла `autosound-tuning`

Режим: лише читання. Корінь: `/Users/o.yukhno/dev/autosound/skill/skills/autosound-tuning`. Шляхи нижче — від кореня скіла; `file:line` — з `cat -n` станом на 2026-09-09.

**Підсумок одним абзацом.** Процес простий (модель веде тюнера · другий ШІ або людина рецензує · стан на диску · тюнер сам вводить числа), але 14 файлів описують його **чотирма голосами з різних епох**: епоха «памʼяті» (`dsp-state-current`, `target-curve-*`, `skill-inbox.md`), епоха «прози як істини» (`autosound_context.md` у контракті), епоха «леджера» (`state/<preset>/v_NNN.json`) і епоха «журналу процесу» (`process/journal.jsonl`). Джерело стану названо по-різному в 8 точках входу; контракт пакета існує у двох версіях, і Критик отримує стару; слово «mode» значить три речі, «round» — чотири, «Level» — дві. Із 13 довідкових файлів сесії щодня потрібні ~3 (контракт, каденція рецензії, вибір режиму — разом ≈ 8 КБ), ще 5 — за фазою/подією, 5 — це документи мейнтейнера, що лежать у теці, яку модель вантажить на вимогу.

---

## Таблиця класифікаторів сесії

| поняття | значення | файл-дім | перетинається з |
|---|---|---|---|
| **Mode A/B/C** (operating mode) | ХТО водій і чи є крос-вендорний рецензент | `process-control.md:12-20` | `SKILL.md:98,169`; `driver-discipline.md:3`; щабель (4) драбини (subagent = фактично mode B) |
| **Драбина рецензента** — три різні | ЯКИМ КАНАЛОМ іде рецензія, коли основний недоступний | `project-intake.md:47-51` (1 CLI → 2 clipboard → 3 human → 4 autopilot-subagent); `setup-critic-channel.md:219-222` §7 (1 desktop chat → 2 any AI → 3 Claude окрема сесія → 4 human); `SKILL.md:172` (wait → other vendor → higher tier → context-isolated) | mode B/C; «reviewer optional» |
| **Level 1/2/3** | що МОЖНА виміряти / прочитати з DSP | `project-intake.md:144-149` | `SKILL.md:96` («Level-2 black-box»); `diagnostic-techniques.md §22` |
| **Level 0** («light-touch») | скільки ХОЧЕТЬСЯ зробити цієї сесії — intent, «orthogonal to 1/2/3» | `project-intake.md:156-160` | mode new/improve; таблиця тригерів |
| **Path** virtual-first / iterative | як ПРОЄКТУЄТЬСЯ тюн | `project-intake.md:151-152` | `virtual-first.md:34`: «There is no separate "iterative path" to choose. The path is one» — класифікатор заперечено його ж домом |
| **Mode new / improve** | повний прохід (−1→0→desk→3→4) чи −1→3→4 | `project-intake.md:154`; `virtual-first.md:49,58,189` | Level 0 («small fine-tune»); тригери |
| **Тригер** new curve / component swap / new install | що з Phase 0–1 лишається дійсним | `naming-and-structure.md:19-25` | mode improve; Level 0 — три класифікатори дають різні маршрути для «нова крива» (Phase 2 only · −1→3→4 · «skip reading the DSP») |
| **Phase −1…5** (+ «desk») | де в процесі | `process-phases.md`; `SKILL.md:105-116` | «desk» у `project-intake.md:154` — не фаза, а щабель шляху |
| **Round** — 4 сенси | (a) тюнінговий раунд measure→batch→import→re-measure `SKILL.md:96`; (b) ітерація критики `[Iteration N/3]` `review-loop.md:72`, `data-contract-universal.md:92`, `assets/data-contract-template.md:105`; (c) раунд ротації ролей `template:143`; (d) capture round `SKILL.md:84`, `process-control.md:64` | — | «ONE reviewer call per round» (`SKILL.md:170`) читається і як (a), і як (b) |
| **Каденція** ONE call / TWO-PASS | скільки викликів на раунд | `review-loop.md:47-48,60-66` | `SKILL.md:170` (копія) |
| **Роль рецензента** — 7 імен | Reviewer AI · Critic-Advisor · Critic · Advisor · Second expert · Challenger · Cold-auditor | `SKILL.md:58`; `review-loop.md:38-40`; `template:18,82`; `data-contract-universal.md:16` | скрипти: `gemini_critic.sh` (stateless) і `gemini_advisor.sh` (з памʼяттю) — це ДВА виклики з протилежним контрактом памʼяті |
| **Клас моделі** Sonnet/Opus/Pro/Flash за задачею | яку модель на яку роль | `process-control.md:28-30`; `setup-critic-channel.md:260-268` | — |

**Що злити / перейменувати** (щоб «mode» = одне):

1. **`mode` — лише A/B/C**, і краще перейменувати у *driver*: `paired` / `solo-Claude` / `solo-Gemini`. Тоді «Modes B/C load driver-discipline» читається без словника.
2. **`new/improve` + Level 0 + таблиця тригерів → один класифікатор *scope*** із трьома значеннями (`full` / `improve` / `light-touch`) і **однією** таблицею маршрутів (яка фаза, які capture). Зараз три таблиці в двох файлах відповідають на одне питання по-різному.
3. **Path — прибрати як вибір.** `virtual-first.md:34` уже каже, що шлях один; лишити «degradation» (`virtual-first.md:215`) як подію, не як опцію інтейку.
4. **`Level` — лише 1/2/3** (вимірюваність); Level 0 іде в scope.
5. **`round` — лише тюнінговий раунд.** Критика — `iteration N/3`; захват — `capture block`; ротацію ролей прибрати (див. знахідку 9).
6. **Драбина — одна, в одному домі** (`setup-critic-channel.md §7`); `SKILL.md` і `project-intake.md` тримають один рядок «→ §7».
7. **Два імені рецензентських викликів, не сім**: *Critic* (stateless, форма §4, дефолт раунду) і *Advisor* (відкрите питання, файл памʼяті, Pass 1 TWO-PASS і staging). «Critic-Advisor» як назва ролі можна лишити, але кожне місце, де сказано «ONE call per round», має казати, **який** із двох.

---

## Знахідки

### 🔴 Джерело стану названо по-різному у 8 точках входу
**Де:**
- `SKILL.md:69` — «MACHINE FILES FIRST, prose second … if prose and the machine files disagree, **the machine files win**»
- `SKILL.md:83` — «Re-read `dsp-state-current` before proposing any DSP change; update it right after the user applies one» — але `rew_tool/state/state.py:867`: «Generated-only (never hand-edited)»
- `assets/data-contract-template.md:27-28` — «`autosound_context.md` … after every accepted change the "Current state" block is updated»
- `references/core/review-loop.md:12-16` — «Canon … Live state … Mirrors» — жодного машинного файлу; і :16 «written identically at every entry point»
- `references/core/knowledge-architecture.md:14` — «Project State | project · `dsp-state` · `tuning-changelog` · `audit-trail`»
- `references/core/naming-and-structure.md:109` — «The full state of the current `vN` always lives in `dsp-state-current` (memory)»; :40 «`dsp-state-current` is the source of truth»; :125 «Active curve → `target-curve-*`» (носія `target-curve-*` у `rew_tool` нема — grep порожній)
- `references/core/driver-discipline.md:32` — «prose state (`dsp-state-current`) stays faithful»
- `references/core/happy-paths.md:25` (поза зоною, але точка входу) — «Read `audit-trail.md`, the top ▶️ CONTINUE block …, and `dsp-state-current`»
- Правильно і повно — лише `data-contract-universal.md:23`: «одне джерело (машинні файли) + один читабельний вигляд (проза)».
**Що не так:** модель, що вантажить будь-який файл, крім universal, отримує стару модель істини; `SKILL.md:83` прямо велить редагувати згенерований файл.
**Як виправити:** один абзац-дім (SKILL.md крок 2 або universal §2), решта — «стан → див. X». У `SKILL.md:83` замінити `dsp-state-current` на «ledger HEAD (`state.py … render` — його вигляд)». Переписати рядок 5 у knowledge-architecture і «truth model» у review-loop через машинні файли.

### 🔴 Два контракти пакета; той, що реально отримує Критик, — старий і одноосібний
**Де:**
- `SKILL.md:61` — «Full protocol → `references/core/data-contract-universal.md`» (UK, «Версія 2.0»)
- `scripts/autosound_ai.py:175` `find_file("data-contract-template.md")`, `scripts/_gemini_common.sh:98` — інструменти вантажать **`assets/data-contract-template.md`** (EN, «Version 1.0»)
- `data-contract-universal.md:46-48` — «Пакет пропозицій раунду: <УСІ дії раунду одним списком … НЕ один параметр на ревʼю>»
- `assets/data-contract-template.md:60` — «Proposal: <a specific filter/action: type, frequency, Q, channel>» — один параметр; :61 поле `Origin` (SCR-050), якого в universal нема
- `data-contract-universal.md:17` — «**Користувач (Олександр)**» — імʼя в «універсальному» публічному контракті
- `assets/data-contract-template.md:6` — «copied to `rew_analitic/data-contract-template.md`» — копіювання ручне (`project-intake.md:196` `cp`), і файли Критика лишаються в `rew_analitic/` (`project-intake.md:194-196`), тоді як машинні файли — у корені проєкту (`naming-and-structure.md:76-88`)
**Що не так:** правило «пакет = весь раунд» (`SKILL.md:170`, `review-loop.md:48`) не доходить до Критика, бо шаблон, який йому інжектять, описує по-параметровий пакет.
**Як виправити:** один контракт — той, що вантажать скрипти (EN), з §3 «пакет раунду» + `Origin`; universal → або видалити, або лишити як UK-переклад §3–§5 з позначкою «translation may lag»; §2 universal (кодування, `contract.py gaps`) — у `rew-tool-docs.md`, тут один рядок-посилання.

### 🔴 Рецензент: «never a background agent» vs «cold-start sub-agent» vs Autopilot-subagent `critic_advisor`
**Де:**
- `SKILL.md:58` — «a **stateless on-demand call** that re-reads state from disk (never a background agent)»
- `references/core/review-loop.md:20` — «ideally **another model** (a cold-start sub-agent)»
- `references/core/project-intake.md:51` — «(4) Autopilot self-loop … spawns an isolated subagent `critic_advisor`»; `references/tooling/setup-critic-channel.md:5-9` — те саме, з тестом
- Пара «stateless» vs памʼять: `review-loop.md:69` — «A persistent file, injected into every call» (для Advisor); `scripts/gemini_advisor.sh:9-10` — «Adds SESSION MEMORY»; `process-control.md:18` — «**ONE advisor call per round**»; `review-loop.md:47` — «ONE **critique** call per round»
**Що не так:** три документи дозволяють те, що SKILL.md забороняє; «Critic-Advisor» як одна роль ховає два виклики з протилежним контрактом памʼяті, і тексти сперечаються, який із них є дефолтом раунду.
**Як виправити:** вирішити про субагента один раз (є щабель → `SKILL.md:58` це каже; нема → прибрати щабель (4) і §0). Описати два виклики явно: Critic = stateless, §4, дефолт раунду; Advisor = відкрите питання + файл памʼяті, Pass 1 TWO-PASS і staging. У `process-control.md:18` замінити «advisor» на «critic» або пояснити.

### 🔴 Три різні драбини відмови рецензента, і посилання з SKILL.md веде в порожнє
**Де:**
- `SKILL.md:172` — «Descend the ladder (wait → other vendor → same vendor higher tier → same model context-isolated) … → `setup-critic-channel.md` §7» — у §7 жодного з цих слів нема (grep `wait|higher tier|context-isolated|other vendor` → 0)
- `references/tooling/setup-critic-channel.md:219-222` — «1. Copy-paste into a desktop chat … 2. Any other AI … 3. Claude in a SEPARATE session … 4. The human»
- `references/core/project-intake.md:47-51` — «(1) Automated Scripts … (2) Clipboard Mode … (3) Human Reviewer. (4) Autopilot self-loop»
**Що не так:** три списки, різні щаблі, різний порядок; людина — 3-й або 4-й щабель залежно від файлу.
**Як виправити:** один список у `setup-critic-channel.md §7`; SKILL.md і project-intake — по рядку «→ §7».

### 🟠 «Reviewer optional» vs «the reviewer ROLE is not optional»
**Де:** `SKILL.md:167` — «but it works with a single AI too»; `SKILL.md:97` — «**offer** to start the reviewer channel»; `process-control.md:19` — mode B «Claude solo + self-control» як легітимний; vs `project-intake.md:52` — «(The CLI CHANNEL is optional; the reviewer ROLE is not.)»; `setup-critic-channel.md:224` — «Never skip the second perspective».
**Що не так:** розвʼязка є (`driver-discipline.md:20`: у соло-режимі роль = stateless виклик обгортки на власний пакет), але її читають лише в B/C.
**Як виправити:** одне речення у «Three Roles»: «роль обовʼязкова; канал варіюється (§7); у соло-режимах роль виконує виклик обгортки на власний пакет (`driver-discipline.md §2`)».

### 🟠 Хто пише audit-trail — чотири відповіді, дві теки для тексту критики
**Де:**
- `review-loop.md:42` — «the wrapper injects the contract + context and **logs the audit-trail**»; :78 — «canonical decision log, append-only: each round — a stamp»
- `assets/data-contract-template.md:136` §8 — «After each cycle — a short entry: Trace ID, the decision, the key objection…» (пише модель)
- `scripts/autosound_ai.py:885` — додає лише `date | role=model | package=`; текст критики → `process/reviews/<ts>-<role>.md` (:704); `scripts/_gemini_common.sh:278` — shell-обгортки пишуть текст у **`review-log.md`**; `driver-discipline.md:30` каже «check `review-log.md`», `SKILL.md:84` — «record that pointer» на `process/reviews/`
- `rew_tool/state/process.py:30` — «`tuning-changelog` and `audit-trail.md` become generated views over the journal» — генератора нема (grep `audit` у process.py — лише docstring)
**Що не так:** рішення (`decision` у журналі), штамп (audit-trail), текст критики (два носії) і «згенерований вигляд» (обіцянка) — чотири історії про один запис.
**Як виправити:** оголосити: рішення → журнал (`decision`); текст критики → `process/reviews/` (shell-обгортки теж, або назвати `review-log.md` legacy); `audit-trail.md` = людський вигляд/legacy. Зняти з моделі обовʼязок §8 шаблону і «wrapper logs the audit-trail».

### 🟠 Куди йдуть уроки — пʼять адрес, одна з них визнано мертва
**Де:** `SKILL.md:100` — «fix locally + `skill-inbox.md` note, or file an issue»; `feedback-loop.md:55` — «collects data from `skill-inbox.md` + the changelog (`Lesson:` lines)… writes `feedback-YYYY-MM-DD.md`»; :101 — «read `rew_analitic/skill-inbox.md`»; :87-89 — Issue / PR у `community-inbox/setups/` / месенджер; :56 — `post_feedback` через side-effect gate; `project-intake.md:192` — інтейк створює `skill-inbox.md`; `process-control.md:89-91` — «the inbox never received them … a harvest queue that is written to but never read from silently becomes a second ledger». У коді `skill-inbox` не читає й не пише ніхто (grep `rew_tool scripts` → 0).
**Що не так:** інтейк створює файл, який SKILL.md радить, feedback-loop збирає, а process-control визнає мертвим.
**Як виправити:** один носій уроку в сесії — рядок `Lesson:` у changelog або `decision` у журналі; назовні — лише `post_feedback` (issue) і PR у `community-inbox/`. `skill-inbox.md` прибрати з `project-intake.md §5`, `SKILL.md:100`, `feedback-loop.md:55,74,101`.

### 🟠 «Round» — чотири сенси в одних і тих самих абзацах
**Де:** `SKILL.md:96` — «Iterate by **round**, not by parameter: measure → compute … → one re-measure»; `SKILL.md:170` — «ONE reviewer call per round»; `review-loop.md:72` — «Max **3 rounds** per question»; `template:143` — «Round 1: Generator — AI-A, Critic — AI-B (rotate afterward)»; `process-control.md:64` — «an open capture round».
**Як виправити:** round = тюнінговий раунд; `iteration N/3` — критика; `capture block` — захват; ротацію прибрати.

### 🟠 Ротація ролей vs фіксовані режими водія
**Де:** `review-loop.md:42` — «Periodically **swap Generator ↔ Critic**»; `template:21` — «Role rotation: periodically swap»; `template:143` — «rotate afterward»; vs `process-control.md:18` — «**A** | Claude drives (Generator) + Gemini as Advisor»; `SKILL.md:167` — «default: Claude drives + Gemini reviews». Інструмента для ротації нема: `gemini_critic.sh` — лише Gemini-як-Критик.
**Як виправити:** видалити ротацію з template §0/«Role assignment» і review-loop:42, або переписати як «ротація = інший mode наступної сесії».

### 🟠 Path virtual-first/iterative заперечено власним домом
**Де:** `project-intake.md:151` — «### Path: virtual-first or iterative (an INTENT on top of the Level)»; `references/phases/virtual-first.md:34` — «There is no separate "iterative path" to choose. The path is one».
**Як виправити:** прибрати «Path» з інтейку; лишити «Degradation» (`virtual-first.md:215`) як подію.

### 🟠 Три класифікатори «скільки перероблюємо» дають різні маршрути
**Де:** `project-intake.md:157` — «Level 0 answers how much you WANT to do this session … skip reading/reversing the full DSP state»; `project-intake.md:154` — «improving an existing tune (−1 → 3 → 4, no new solos)»; `naming-and-structure.md:23` — «New target curve, same hardware | valid, reuse | same raw still valid | **Phase 2 only**».
**Що не так:** для «нова крива на тому ж залізі» три відповіді: Phase 2 only · −1→3→4 · «не читай DSP».
**Як виправити:** один *scope* з таблицею маршрутів у `project-intake.md §4`; `naming-and-structure.md §2` — посилання.

### 🟠 process-control.md перетворився на склад чужих правил, частина — з епохи прози
**Де:** `process-control.md:54-81` «Stopping is an event» — сам каже (:77) «The trigger words, the full order … live in `SKILL.md`»; :83-91 «hardware drift»; :93-99 «system state … in the measurement's own notes» (правило про заміри в файлі про режими; `analysis-playbook.md:76` на нього посилається); :101-103 — «Before writing a new `vN.N` block, grep the ledger for that label» — `v_NNN` виділяє `apply.propose` (`rew_tool/state/apply.py:290`), не рука.
**Як виправити:** лишити §1–§3 (≈2.5 КБ); правило про notes → `naming-and-structure.md §3`; версійний простір — видалити; stopping — один рядок-посилання.

### 🟠 Пʼятишарова архітектура знань описує епоху прози
**Де:** `knowledge-architecture.md:12` — «Engineering Profile | project · `autosound_context.md`»; :14 — «Project State | `dsp-state` · `tuning-changelog` · `audit-trail`». Ні `project.json`, ні `dsp_profile.json`, ні `state/`, ні `process/` (їх описує `naming-and-structure.md:76-88`).
**Як виправити:** у рядках 3 і 5 назвати машинні файли, прозу — як «view».

### 🟢 Висячі посилання (розділи/файли, яких нема)
- `naming-and-structure.md:27,111`; `preset-strategy.md:3,21`; `diagnostic-techniques.md:35` → «SKILL.md §Session lifecycle» — розділ знято в коміті `532dbb4` («rewrite SKILL.md into ultra-compact router»).
- `review-loop.md:75` → «**Interactive Presentation Rule** in `SKILL.md`» — тепер «Settings land in chat» (`SKILL.md:85`), знято тим самим комітом.
- `preset-strategy.md:16` → «Pre-session §4» — §4 тепер «STOPPING IS AN EVENT» (`SKILL.md:71`); перевірка входу — крок 1 (`SKILL.md:68`).
- `preset-strategy.md:21` → «`process-phases.md` step 5b» — 5b живе в `references/phases/phase_1_foundation.md:81`; у process-phases його нема.
- `feedback-loop.md:49` → `package_skill.py` — у репо нема.
- `data-contract-universal.md:24` → `scripts/encoding-check.py` — лежить у `scripts/` **кореня репо**, не скіла; за `SKILL.md:32` шляхи скіл-відносні → для моделі файл «відсутній».
- `naming-and-structure.md:118,125` → `target-curve-*` «project memory» — носія нема в коді; активна крива тепер `rew_analitic/target-curves/README.md` (`project-intake.md:189`).
- `critic_advisor` — живий у `project-intake.md:51`, `setup-critic-channel.md:8` (див. 🔴 №3). `verify_measurements.py`, `Phase 6` — не знайдено ніде (чисто).
- Відносні лінки `references/core/…` зсередини `references/core/` (`process-control.md:7,37`; `knowledge-architecture.md:55,62`; `preference-profile.md:6,29-33`) — для моделі ок за конвенцією `SKILL.md:32`, у будь-якому Markdown-рендері биті.

### 🟢 Мова
`data-contract-universal.md` — єдиний UK-файл ядра; шаблон, який інжектять скрипти, — EN. Або перекласти, або позначити як переклад (як зроблено для `listening-cheat-sheet.uk.md`, `SKILL.md:147`).

### 🟢 review-loop.md «Wing 1» — гігієна проєкту, не сесія
`review-loop.md:9-28` (truth model, cold audit, brief→fix→verify) — методика мейнтейнера; «Wing 2» (:32-78) — те, що потрібно сесії. Розділити: Wing 2 → у файл каденції (або прямо в `SKILL.md §Review Channel`, який уже є копією :47-48/:60-61), Wing 1 → `CONTRIBUTING.md`.

### 🟢 estimator-scope.md наполовину — документація розробника і підписане рішення
`estimator-scope.md:88-144` (§1b + «cached in the profile»: `dsp_profile.annotate_modellable`, selftest, CI) і :165-216 (§2a «Signed off: the user, 2026-09-01») — ≈9 КБ, які сесія тюнінгу не читає. Лишити §1, §1a, §2-таблицю, §3, §4; §1b → `rew-tool-docs.md`, §2a → CHANGELOG/рішення.

### 🟢 feedback-loop.md — ритуал сесії змішаний із боком автора
`feedback-loop.md:35-38` (донат-лінки, `FUNDING.yml`), :44-49 («Distributing the skill» — дублює `installation.md`), :109-123 («The author's side») — мейнтейнерське. Сесії потрібні A–C + шаблон пакета + правила безпеки (≈6 КБ). `feedback-loop.md:112-116` дослівно повторює `SKILL.md:86-94` (обидва цитують HUB-029).

### 🟢 SKILL.md сам собі дублікат
`SKILL.md:58` і `SKILL.md:167` — той самий абзац «stateless… drift-watchdog… /clear + resume» двічі; `SKILL.md:69` — 1.3 КБ одним кроком із двома анекдотами (CAR-007); `SKILL.md:84` — 2.4 КБ одним буллетом, включно з повним списком команд `process.py`, які вже є в `capabilities.md`.

---

## Дублі

| правило | оригінал (file:line) | копії (file:line) | пропозиція |
|---|---|---|---|
| Таблиця ролей Generator / Critic / Arbiter | `assets/data-contract-template.md:14-19` (те, що інжектять) | `SKILL.md:57-59`; `data-contract-universal.md:13-17`; `review-loop.md:35-40` (+Cold-auditor) | SKILL.md — 3 рядки; universal — переклад; review-loop — посилання |
| Drift-watch: «stateless call re-reads disk → re-anchor / `/clear` + resume» | `SKILL.md:58` | `SKILL.md:167`; `data-contract-universal.md:16`; `template:18`; `driver-discipline.md:16` | лишити в SKILL.md:58 і в template:18 (Критик має це знати); решта — посилання |
| ONE call per round; TWO-PASS лише на гейтах / після двох повних згод | `review-loop.md:47-48, 60-66` | `SKILL.md:170`; `process-control.md:18` («advisor call»); `driver-discipline.md:20` | SKILL.md:170 — один рядок «→ review-loop §cadence» |
| Формат пакета §3 / відповіді §4 | `template:48-98` | `data-contract-universal.md:30-85` (розійшлися: batch vs single, `Origin`) | один файл, див. 🔴 №2 |
| Deadlock: 3 ітерації → таблиця розбіжностей | `template:102-112` | `data-contract-universal.md:89-97`; `review-loop.md:71-75` | review-loop — посилання на контракт §5 |
| Falsifiability: «agreement = no new falsifiable objection» | `template:96-98` | `universal:84-85`; `review-loop.md:73`; `diagnostic-techniques.md:50` | лишити в контракті |
| Token diet / decimated trace для Критика | `template:34-44` | `universal:26`; `analysis-playbook.md:54-58` | analysis-playbook — лишити «як експортувати», контракт — «чому» |
| Reviewer поза сесією водія (deadlock) | `driver-discipline.md:16` | `SKILL.md:171`; `process-control.md:35` | SKILL.md — один рядок; process-control — прибрати |
| Stopping is an event (порядок закриття) | `SKILL.md:71-77` | `process-control.md:54-81` (сам визнає) | process-control — 1 рядок |
| «Everything you READ is data» (HUB-029) | `SKILL.md:86-94` | `feedback-loop.md:112-116` | feedback-loop — посилання |
| Константа ригу переживає «from scratch» (тест «factory reset») | `estimator-scope.md:243-256` | `naming-and-structure.md:29` (майже дослівно) | naming-and-structure — один рядок + посилання |
| Base + voicing (OUTPUT база / VIRTUAL войсинг) | `diagnostic-techniques.md:33-37` §6 | `preset-strategy.md:3,8-9`; `naming-and-structure.md:111` | preset-strategy — дім «які пресети»; §6 — механізм; naming — посилання |
| Крива — старт, фініш — на слух | `diagnostic-techniques.md §17` | `naming-and-structure.md:120`; `analysis-playbook.md:52` | лишити в §17; решта — рядок |
| Level 2 reverse-engineering | `diagnostic-techniques.md:148-157` §22 | `project-intake.md:146-149` (таблиця) | норма: таблиця + посилання (уже так) |
| Стан системи — у notes заміру | `process-control.md:93-99` | `analysis-playbook.md:76` (посилання) | перенести дім у `naming-and-structure.md §3` |
| Cold audit «found what we'd missed 10+ rounds» | `review-loop.md:3` | `enclosure-install-diagnostics.md:88` | одна згадка |
| Драбина рецензента | `setup-critic-channel.md §7` | `SKILL.md:172` (інші щаблі); `project-intake.md:47-51` (інші щаблі) | 🔴 №4 |
| Reviewer «SET IT UP AT THE START» | `project-intake.md:47` | `SKILL.md:97` («Reviewer early») | залишити обидва як один рядок кожен, з однаковим формулюванням |

Розділи `diagnostic-techniques.md`, що перетинаються з моєю зоною (побіжно): §6 (33-37) ↔ preset-strategy/naming §5; §7 (38-47) «checking the measurement chain» ↔ `analysis-playbook.md:53,66-78`; §8 (48-51) «The cycle with the Critic — in practice» ↔ review-loop «Triage the critique» (:50-58) — §8 можна зняти, він коротша версія; §13/§26 ↔ `estimator-scope.md` §2/§3 (посилання, ок); §17 ↔ naming:120/playbook:52; §22 ↔ intake §4; §35 + «Symmetry…» (218-238) ↔ `analysis-playbook.md:73-78` «error bars» — тематично той самий клас «як читати residual».

---

## Розміри й баласт

Метод: «історії» = рядки з датами `2026-..`, «bought/куплено», «real session/case/run», «field-validated/observed», номерами тікетів хаба/issue. Оцінка груба (рядок може містити й правило), тому «≈».

| файл | байт | ≈ частка «історій» | пропозиція «до → після» |
|---|---|---|---|
| `SKILL.md` | 25 258 | 11 % (CAR-007, HUB-023, HUB-029, «a real session lost minutes…») | 25 → ~14 КБ: крок 2 і guardrail «Write the PROCESS» стиснути до правила + `capabilities.md`; :58/:167 — один раз; драбина — посилання |
| `data-contract-universal.md` | 12 848 | 27 % (§2 — CAR-007, TCC-007, v3.0.45, cp1251) | 12.8 → 0 (злити в template) або ~4 КБ як UK-переклад §3–§5 |
| `process-control.md` | 7 867 | 15 % (HUB-023, «Three independent occurrences», v4.5) | 7.9 → ~2.5 КБ (§1–§3) |
| `review-loop.md` | 9 173 | 8 % (2026-06, 2026-07-15, 2026-07-19, «−2.08 → −1.78», «9.8° → 6.8°») | 9.2 → ~4 КБ: Wing 2 без дат і чисел; Wing 1 → CONTRIBUTING |
| `driver-discipline.md` | 4 767 | 39 % («~20 sessions», «70+ times, executed zero», «~15 of 20», «2450 vs 2202») | 4.8 → ~3 КБ: 4 правила + таблиця; польові числа → CHANGELOG одним рядком |
| `feedback-loop.md` | 16 455 | 12 % (issue #23, HUB-029, «approved 2026-07-11») | 16.5 → ~6 КБ сесійна частина; §D/«Distributing»/«author's side» → доки репо |
| `estimator-scope.md` | 19 583 | 7 % (але §1b-cache і §2a — ~9 КБ доку розробника/рішення) | 19.6 → ~9 КБ |
| `knowledge-architecture.md` | 4 447 | 3 % («Bought 2026-09-05 … helix-phase-allpass») | 4.4 → ~3 КБ + оновити рядки 3/5 таблиці |
| `naming-and-structure.md` | 17 438 | 18 % («2026-08-24, additive», «2026-08-26», SCR-039, issue #5, 2026-08-21) | 17.4 → ~11 КБ: дати → правила; дерево §4a → посилання на `project-schema.md`; зняти «(memory)», `target-curve-*` |
| `preference-profile.md` | 2 410 | 0 % | лишити |
| `preset-strategy.md` | 4 725 | 0 % | лишити; поправити 3 висячі посилання |
| `intake-from-prose.md` | 4 889 | 0 % | лишити — зразок того, як має виглядати файл «коли читати / що взяти» |
| `analysis-playbook.md` | 15 013 | 25 % (:66-78 — «+4.3…+5.7 dB», «18.4 ms», «0.25 ± 0.07») | 15 → ~9 КБ: таблиця + reading rules; :66-78 → diagnostic-techniques або CHANGELOG |
| `assets/data-contract-template.md` | 8 093 | 9 % (SCR-050) | 8.1 → ~7 КБ: зняти §7 «Transport» (macOS/VM — середовище, не протокол) і ротацію; додати batch-пакет |
| **разом** | **154 966** | — | **≈ 85–90 КБ** |

Скільки модель мусить читати реально: **завжди** — SKILL.md + контракт (той, що бачить Критик) + каденція рецензії (можна 15 рядків у SKILL.md) ≈ 8 КБ; **за подією** — driver-discipline (лише B/C), intake-from-prose (лише за `contract.py check`), preset-strategy/preference-profile (інтейк §2, Phase 5), naming §3/§5 (перше іменування захвату), analysis-playbook (читання графіків), estimator-scope §2/§3 (перед довірою числу); **майже ніколи в сесії** — knowledge-architecture, feedback-loop §автора, review-loop Wing 1, estimator-scope §1b/§2a, process-control §4.

---

## Ясність: чи кажуть перші 10 рядків «коли читати і що взяти»

| файл | перші 10 рядків | вердикт |
|---|---|---|
| `data-contract-universal.md` | «Призначення… Версія 2.0» — ні «коли», ні «що взяти»; мова UK | ❌ додати: «Loaded into the reviewer's prompt by scripts; a session reads §3 (package) and §5 (deadlock)» |
| `process-control.md` | :3-8 — що це і коли вантажити driver-discipline | 🟡 є «що», нема «коли читати цей файл» (відповідь: один раз, обираючи режим) |
| `review-loop.md` | :5 «Read this before the first review round of a session» | ✅ — але далі йде Wing 1, який до сесії не стосується |
| `driver-discipline.md` | :3 «**When to load:** …» | ✅ зразковий |
| `feedback-loop.md` | :3 мета; тригер у :7 | 🟡 «коли» є, «що взяти» — лише після 40 рядків |
| `estimator-scope.md` | :3-15 — чому існує; «коли» неявно | 🟡 додати рядок: «Read §2 before trusting any tool's number; §3 before turning a fit into a setting» |
| `knowledge-architecture.md` | :3-4 | 🟡 нема «коли» (відповідь: при fold у knowledge/, не в сесії) |
| `naming-and-structure.md` | :3 | ✅ |
| `preference-profile.md` | :3-6 | ✅ |
| `preset-strategy.md` | :3-5 | ✅ (три биті посилання в перших 20 рядках) |
| `intake-from-prose.md` | :3-5 | ✅ зразковий |
| `analysis-playbook.md` | :3 «A map: decision → data → REW API function» | ✅ |
| `assets/data-contract-template.md` | :3-8 | ✅ |
| `SKILL.md` | — | Reference Map (:120-161) каже «Read when» для кожного; але для review-loop/process-control/data-contract він каже «cadence… modes… protocol» — три файли на одну тему, і жоден рядок не каже, що контракт — це файл для Критика, а не для водія |

---

## Три кроки, що дають найбільше за найменше

1. **Один контракт** (EN, той, що вантажать скрипти) з пакетом-раундом і `Origin`; universal → переклад або в архів. Знімає 🔴 №2 і три рядки дублів.
2. **Один абзац про істину стану** + заміна `dsp-state-current`/`target-curve-*`/`skill-inbox.md` у 8 місцях на машинні носії. Знімає 🔴 №1, 🟠 «audit-trail», 🟠 «уроки».
3. **`session-protocol.md` ≈ 6 КБ** = process-control §1–§2 + review-loop Wing 2 без дат + одна драбина; SKILL.md «Review Channel» стає п'ятьма рядками з посиланням. Знімає 🔴 №3–4, 🟠 «optional», «round», «ротація».
