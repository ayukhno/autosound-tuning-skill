# Рецензія E — зовнішня (користувацька) частина `autosound-tuning-skill` @ v3.0.46

Режим: тільки читання. Дата: 2026-09-09. Шляхи відносно `/Users/o.yukhno/dev/autosound/skill/`; `tcc/…` — сусіднє репо `/Users/o.yukhno/dev/autosound/tcc` (v0.1.35).

Коротко: команди установки в чотирьох README узгоджені (v3.0.46), скелет заголовків FAQ×4 однаковий. Головні проблеми — не між мовами, а **між README і FAQ** (`main` vs тег, пароль Mac, де живе ключ Gemini) та **між README і тим, що робить інсталятор/скіл** («другий ШІ опціональний» vs «ядро методу», три входи в акаунти, яких README не згадує, omp, бекап «автоматично»).

---

## Дорога користувача (як є)

**A. Від нуля до першого повідомлення (README, шлях TCC 3.x, macOS)**

1. Мати мікрофон, DSP, ноутбук — [ок]
2. Скачати REW **beta** з roomeqwizard.com/beta.html — [неясно] README мовчить, що завантаження лежать на форумі AV NIRVANA (це каже лише інсталятор, `install.sh:1198`)
3. У REW: Preferences → API → «Start the API when REW starts» → «Start server» — [ок] (на Windows інсталятор ставить ярлик «REW (API on)», `install.ps1:887-900`)
4. Купити Claude Pro/Max — [ок]
5. Завести акаунт GitHub — [зайве на старті] (README.md:42 радить; потрібен лише для бекапу, який і так робиться пізніше через ШІ)
6. Відкрити Terminal, вставити `curl … v3.0.46/install.sh | bash` — [ок]
7. Питання інсталятора «Back projects up to GitHub?» y/n (`install.sh:559`, типово n) — [неясно] README не попереджає; користувач не знає, що відповісти
8. «Go ahead?» — згода на список завантажень — [ок]
9. Вікно Apple Command Line Tools: Install → Agree, чекати (`install.sh:661-662`) — [неясно] README каже «один клік і без пароля», FAQ — «може попросити пароль», сам скрипт каже і те, і те (див. 🔴 1)
10. Чекати 10–20 хв — [ок]
11. Вхід 1: Claude — Enter → браузер → Authorize (`install.sh:1121-1125`) — [ок]
12. Вхід 2: Gemini reviewer — `agy`: «press Enter through its two setup screens», вхід Google, можливо **Project ID** з aistudio.google.com/app/apikey, `/quit` (`install.sh:1155-1158`); потім, можливо, «Enable» Agent Platform API (`:1161-1162`) — [неясно] README цього кроку не має взагалі; FAQ каже «без ключів, безкоштовний OAuth»
13. Вхід 3: GitHub `gh auth login --web` (якщо на кроці 7 сказав y) — [зайве на старті]
14. Відкрити «Autosound TCC» з робочого столу — [ок]
15. Створити порожню теку, Browse… — [ок]
16. Перевірити «AI main = Claude Opus», «AI critic = Gemini Pro (High)», effort ≥ xhigh (README.md:61, `install.sh:1215`) — [зайве] це вже дефолти (`tcc/src/autosound_tcc/core/model_choices.py:60,131`); README змушує перевіряти те, що й так стоїть
17. Написати «tune a new car from scratch» — [ок] (але фраза різна в README.md:62 / `install.sh:1218` / FAQ.uk.md:273 — див. таблицю)

**B. Від першого повідомлення до першого виміру (SKILL.md → `project-intake.md §0.5` → `capture-session-sheet.md`)**

18. Питання «English, or your native language? (EN·UK·DE·PL)» (`project-intake.md:42`) — [зайве в TCC] застосунок уже знає мову (`:61-62` `get_tcc_state.language`); [ок у терміналі]
19. Вибір каналу рецензента з 4 варіантів: CLI/API · Clipboard Mode · Human · Autopilot self-loop (`project-intake.md:47-52`) — [неясно] README сказав «опціонально», скіл каже «ядро методу, не пропускати»; користувач не розуміє різниці
20. Вибір режиму A/B/C (`SKILL.md:143`, `process-control.md:14-19`) — [неясно] жаргон; можна вирішити автоматично: є agy → A
21. Інтервʼю про обладнання: авто, динаміки по каналах (марка/модель/**Fs**), DSP, підсилювачі, мікрофон, джерело (`project-intake.md §1`) — [ок] (Fs для новачка важко; є fallback «з даташита»)
22. Чек-лист можливостей DSP → Level 0/1/2/3 (`project-intake.md:130-160`) — [неясно] рівні пояснені для моделі, не для людини; можна брати з `knowledge/dsp/<профіль>`
23. Інтервʼю про цілі: змагання/для себе, референсне місце, смак → зерно кривої (`§2`) — [ок]
24. Цільова крива: згенерувати ШІ / намалювати в Nono / принести свою (FAQ.md:409-412) — [ок]
25. Рig REW: кал-файли мікрофона, sample rate = нативна DSP, **фізичний loopback**, вхід не кліпує (`project-intake.md:66`) — [неясно] README.md:37 каже «UMIK-1 годиться», скіл — «без loopback фаза/тайминг ненадійні»
26. Узгодити коди каналів і назви замірів — гейт (`project-intake.md:67`) — [ок, автоматизовано `naming.py`]
27. Перевірка інсталяції: розводка, полярність, захисні HPF ≥1.1×Fs LR4, гейни, шум, обкатка, безпечний рівень свіпу (`§3`) — [ок] безпека
28. Генерація файлів проєкту (`§5`) — [ок, автоматично]
29. Підготовка зйомки (−1.4): бекап тюну; пресет `v0` (тільки захисні, гейни рівні, затримки 0, EQ порожній, ефекти off); налаштування REW (Sweep 512k, Repetitions 4, Timing loopback; RTA 1/48, FFT 64k, Forever, Hann); роздрукувати лист зйомки; паспорт; «сумка» (`capture-session-sheet.md:8-27`) — [неясно] README.md:80 обіцяє «просто записуєш серію свіпів»
30. В авто: блок A рівні (саб −5…−10 dBFS) → блок B RTA кожного каналу + **9 позицій p1…p9 для w-L/R, m-L/R** → блок C штатив, рулетка, drift-пара → блок D свіпи з `ctl1`/`ctl3` → блок E capture-check на місці → блок F закриття (`capture-session-sheet.md:36-86`) — [неясно] це ~1–1.5 год і десятки замірів, README каже «один раз … серія свіпів»

Що можна прибрати/автоматизувати: 5, 13 (перенести бекап на «коли є що бекапити»), 16 (дефолти), 18 (у TCC), 19+20 (один вибір замість двох, або автоматично з наявності agy), 22 (з профілю DSP), 7 (питати після установки, не до).

---

## Знахідки

### [🔴] Пароль Mac: README каже «ні», FAQ — «так», інсталятор — і те, і те
**Де:** README.md:46 «no password is typed into the script»; FAQ.md:236 «The script may ask for your Mac password once»; `install.sh:593` «Apple's Command Line Tools — git, about 1 GB … asks your Mac password once»; `install.sh:602` «After the password you can walk away»; `install.sh:644` «No password is typed into this script». Те саме в усіх мовах (README.uk:46 vs FAQ.uk:238; FAQ.de:238; FAQ.pl:238).
**Що не так:** для не-програміста «просити пароль» — сигнал безпеки; три тексти дають три відповіді. Фактично `xcode-select --install` (`install.sh:663`) відкриває вікно Apple, пароль просить Apple, не скрипт.
**Як виправити:** одна фраза всюди: «Apple відкриє своє вікно і може спитати пароль Mac — це Apple, не скрипт»; прибрати «asks your Mac password once»/«After the password» з `install.sh:593,602` (і дзеркала в ps1/cmd, `CONTRIBUTING.md:46` «Touched an installer? Touch all three»).

### [🔴] Команда установки: README ставить тег, FAQ — `main`
**Де:** README.md:50,55 «…/v3.0.46/install.sh»; FAQ.md:234,246 «…/main/install.sh» (так само FAQ.uk:236,248; FAQ.de:236,248; FAQ.pl:236,248).
**Що не так:** «Оновлення: запустіть той самий рядок» (FAQ.md:277) — але рядків два, і вони можуть тягнути різний скрипт. `scripts/i18n-check.py` порівнює README×4 і FAQ×4 між собою, але не README↔FAQ, тож розбіжність невидима.
**Як виправити:** FAQ бере рядок із README (тег) або README посилається на FAQ як на єдине джерело команди; додати пару README↔FAQ у i18n-check (fenced-блоки).

### [🔴] Другий ШІ: «optional» у README/FAQ — «CORE, not an option» у скілі
**Де:** README.md:11 «Two AIs (optional)»; FAQ.md:305 «While optional, this provides the greatest benefit»; `references/core/project-intake.md:47` «It's the CORE of the method, not an option», `:52` «Don't skip this step»; FAQ.md:309 «requires no API keys and uses a free OAuth login» vs `references/tooling/setup-critic-channel.md:29` «will prompt for your Google Cloud Project ID», `:31` «Enable the API in that project … the channel cannot work without it», `:35` «Watch the billing on that project»; `install.sh:1157-1162` (Project ID, «press Enable»).
**Що не так:** користувач, повіривши «опціонально», пропускає agy при установці — і в першій же сесії отримує обовʼязковий вибір із 4 каналів (крок 19). А той, хто ставить agy, стикається з Project ID / Enable API / billing, про які README і FAQ мовчать.
**Як виправити:** README чесно: «Другий ШІ (Gemini) — частина методу. Потрібен акаунт Google; при установці agy може спитати Project ID — де взяти, дивись FAQ». FAQ.md:309 — прибрати «no API keys / free», додати Project ID + Enable. У скілі — якщо agy є, вибирати канал (1) і режим A мовчки.

### [🟠] Де живе ключ Gemini — README і FAQ показують різні місця, три мови мовчать
**Де:** README.md:42 «it lives … in `~/.config/autosound/critic-env`»; FAQ.md:324 «Create a text file named `.critic-env` inside your **project folder** (inside `rew_analitic/`…)»; `scripts/.critic-env.example:3` «the API KEY -> ~/.config/autosound/critic-env»; README.uk:42 / de:42 / pl:42 речення про ключ немає.
**Що не так:** FAQ веде в теку проєкту — саме ту, яку README радить бекапити на GitHub, і саме той випадок, що обгортки відмовляють (`setup-critic-channel.md:111-116`). Новачку з agy ключ не потрібен узагалі — абзац у README лише лякає.
**Як виправити:** з README прибрати абзац про ключ; FAQ «Fallback: Direct Gemini API Key» — шлях до машинного файлу з `.critic-env.example:3`.

### [🟠] «Варіанти підписок» у FAQ суперечать і README, і власному FAQ
**Де:** FAQ.md:205-206 «Option 1 … free Gemini as Critic … Use a free Gemini API key generated in Google AI Studio»; FAQ.md:207 «Option 2 … Gemini Only ($10 prepay on Google Cloud)»; README.md:40 «Paid Claude subscription (Pro or Max)»; FAQ.md:307-309 рекомендований шлях — `agy`, а ключ — fallback (FAQ.md:319).
**Що не так:** три «варіанти» — про гроші, а не про те, що робити; «Gemini only» для новачка звучить як підтримуваний шлях, хоч це ручний запуск (FAQ.md:337).
**Як виправити:** один абзац: «Потрібно: Claude Pro/Max + безкоштовний акаунт Google (agy). Ключ Gemini — лише запасний варіант. Без Claude — тільки ручний шлях 4».

### [🟠] omp ставиться за замовчуванням, README про нього не знає, FAQ каже «лише якщо активовано»
**Де:** `install.sh:77-83` (WANT_OMP «auto» → разом із застосунком), `install.sh:590` «omp — offers TCC every non-Claude model (metered)»; FAQ.md:295 «available only if the `omp` system is activated (billed separately)»; README — 0 згадок.
**Що не так:** користувач бачить на екрані згоди третій платний («metered») інструмент, про який не читав.
**Як виправити:** один рядок у README «What You Need» або `--no-omp` за замовчуванням; FAQ.md:295 — «встановлюється разом із застосунком; платний лише при використанні».

### [🟠] Бекап «automatically» — інсталятор лише ставить `gh`
**Де:** README.md:42 «to automatically back up your tuning history in a private repository»; FAQ.md:432 «Our installer offers an option to set up automated … backups»; `install.sh:554-559` (питання + встановлення gh), `install.sh:1246-1247` «say to the AI: "back this project up to a private GitHub repository"»; у скілі жодного `gh repo create` (grep по `skills/` — лише коментарі в `project_seed.py:250,521`).
**Що не так:** «автоматично» ≠ «попроси ШІ, він щось зробить через gh». Механізму немає — є намір.
**Як виправити:** README: «можна попросити ШІ зробити приватний бекап на GitHub (потрібен gh — інсталятор поставить)»; або справді додати команду в `rew_tool`.

### [🟠] «Sends generalized lessons to a shared knowledge base» — такого сервісу немає
**Де:** README.md:86 (і uk/de/pl:86); `references/core/feedback-loop.md:56` «Delivery to the author (optional…) The user sends the file themselves via one of the channels below», `:57` файл `feedback-YYYY-MM-DD.md`.
**Що не так:** реальність — локальний markdown-файл, який людина сама шле автору (issue/e-mail). «Скіл вчиться з кожного тюна» — вчиться автор, коли вливає в репо.
**Як виправити:** «Наприкінці ШІ пропонує зібрати файл-відгук; надіслати його автору — окреме твоє рішення».

### [🟠] Effort `xhigh`: правда для TCC, для терміналу — ніде не сказано як
**Де:** README.md:61 «effort level for Claude Opus … `xhigh` (this is the default value) … changes apply only to the next session» — підтверджено `tcc/src/autosound_tcc/core/model_choices.py:131` `EFFORT_DEFAULT = "xhigh"`, `ui/tcc/i18n.py:579` «Effort applies to the next session»; FAQ.md:192,198 «Do not lower Claude's effort level below `xhigh`» — для всіх шляхів, але де це крутиться в Claude Code (шляхи 2 і 3) — жодного слова.
**Як виправити:** у FAQ один рядок для терміналу (як задати effort у Claude Code) або обмежити пораду TCC.

### [🟠] README обіцяє «один раз … просто серію свіпів»; метод вимагає 6 блоків і 9 позицій
**Де:** README.md:80 «just record a series of sweeps for each driver»; FAQ.md:395-399 (p1…p9, ctl); `references/phases/capture-session-sheet.md:36-86` (блоки A–F, «p1…p9 … for w-L w-R m-L m-R», `ctl1`/`ctl3`, рулетка, паспорт).
**Що не так:** очікування «15 хвилин» проти реальних ~1–1.5 год; людина без листа зйомки не знає, що «серія» — це десятки іменованих замірів.
**Як виправити:** README: «одна поїздка ~1–1.5 години; застосунок/ШІ друкує лист зйомки, ти йдеш по ньому».

### [🟠] «After installation» у README пропускає три входи в акаунти, які інсталятор робить першими
**Де:** README.md:58-62 (4 кроки: відкрити TCC, тека, effort, фраза); `install.sh:1102-1179` («Sign in — the part that is yours»: Claude, Gemini reviewer, GitHub); FAQ.md:267-273 має їх.
**Як виправити:** у README додати крок 0 «наприкінці установки — вхід у Claude (обовʼязково), Google для agy (раджу), GitHub (можна пропустити)».

### [🟠] Опис-тригер SKILL.md: 1739 символів; у переліку скілів цієї сесії обрізано на ~1537-му
**Де:** `skills/autosound-tuning/SKILL.md:3-23` (description 1 779 симв. з переносами / 1 739 нормалізованих / 1 977 байт). У переліку скілів, що бачить модель у цій сесії, опис закінчується «…«затримки та кросовери в а…» — тобто останні 202 символи (одна UK-фраза, усі DE- і PL-фрази) до моделі **не доходять**.
**Що не так:** DE/PL-тригери тестуються в `evals/trigger-eval-set.json` (37 кейсів: «kannst du mir helfen mein Car-HiFi einzumessen…», «pomóż mi ze strojeniem DSP w aucie…»), але в описі вони стоять останніми; `evals/README.md:3` каже «20 queries» — застаріло. Опис не дублює README (README — для людини), але роздутий: блок T-S/корпусів (`SKILL.md:12-16`, ~330 симв.) і ліцензійна дужка про Nono (`:10-11`, ~130 симв.) — не тригери.
**Як виправити:** скоротити до ≤ ~1 000–1 200 симв.: прибрати дужку про Nono, стиснути T-S до «driver impedance / Thiele-Small, box design, DVC wiring», підняти UK/DE/PL-фрази й «resume/продовжити тюн» вище T-S. Прогнати `evals/run_trigger_eval.py` після.

### [🟠] «~700 MB free disk space» — на чистому Mac ближче до 2 GB
**Де:** FAQ.md:60 «~700 MB free disk space»; `install.sh:569-593` (Claude 200 + TCC 700 + agy 100 + omp 150 + gh 50 + «Apple's Command Line Tools — git, about 1 GB»).
**Як виправити:** «≈2 GB (з них 1 GB — інструменти Apple)».

### [🟢] Застарілий приклад пари версій
**Де:** FAQ.md:278 «`--skill-ref v3.0.33` and `--tcc-ref v0.1.22`» (і `install.sh:34-35,113-114`); поточні v3.0.46 / v0.1.35 (`commands/install-tcc.md:20`, `tcc` тег v0.1.35).
**Як виправити:** «пара, яку інсталятор друкує наприкінці», без чисел.

### [🟢] «68 capabilities» — у таблиці 91 рядок
**Де:** FAQ.md:456 «all 68 capabilities»; `references/core/capabilities.md` — 91 рядок-можливість (без шапок).
**Як виправити:** прибрати число.

### [🟢] ROADMAP застарів відносно README
**Де:** ROADMAP.md:9 «Guided Setup Wizard — interactive onboarding instead of manual README steps» (у «Now»), :10 «TCC … Currently in prototyping stage»; README.md:44-46 — інсталятор є, TCC «beta», v0.1.35.
**Як виправити:** оновити або поставити дату «станом на».

### [🟢] Час установки — три числа
**Де:** README.md:46 «10–20 minutes» (обидві ОС); `install.ps1:565` «5 to 15 minutes»; `install.sh:606` «a few minutes» (коли CLT уже є).
**Як виправити:** «5–20 хв».

### [🟢] Дрібне у FAQ
- FAQ.md:65 «Set up via the installer with the `--terminal` flag» — не показано, як передати прапорець через `curl | bash` (є в `install.sh:121`: `| bash -s -- --terminal`).
- FAQ.md:97 `/plugin install …` (усередині Claude Code) vs README.md:73 `claude plugin install …` (у shell) — обидва працюють, але дві форми плутають.
- FAQ.md:299 «*Report a problem* button on TCC's GitHub page» — кнопка в діалозі Diagnostics самого TCC (`tcc/…/i18n.py:135`), не на GitHub.
- FAQ.md:270 «Google account that has Antigravity access» — термін ніде не пояснено; PL-версія (FAQ.pl.md:272) його просто не має.
- FAQ.md:261 «Tuning Method | `~/.claude/skills/.autosound-tuning-src`» — це checkout; сам скіл — симлінк `~/.claude/skills/autosound-tuning` (`install.sh:63,761`); шлях `migrate.py` у FAQ.md:132 правильний (файл є).

### [🟢] Англійська README — кальки
README.md:99 «**Good sound!**» (→ «Enjoy the music!» / «Happy listening!»); :62 «lead you by the hand» (→ «walk you through it»); :82 «"hurts the ear"» (→ «sounds harsh»), «"the stage is off"» (→ «the stage is off-center»); :82 «**Enjoyment in the car:**» (→ «Listening in the car»); :12 «A check lacking data will refuse to proceed» (→ «A check that lacks data refuses to run»).

---

## Таблиця розбіжностей між мовами

| твердження | EN | UK | DE | PL |
|---|---|---|---|---|
| Тег у команді установки (README:50,55) | v3.0.46 | v3.0.46 | v3.0.46 | v3.0.46 |
| Гілка у команді установки (FAQ) | `main` (:234,246) | `main` (:236,248) | `main` (:236,248) | `main` (:236,248) |
| Пароль Mac | README:46 «no password» / FAQ:236 «may ask» | README:46 «жодного пароля» / FAQ:238 «може попросити» | README:46 «kein Passwort» / FAQ:238 «fragt … Passwort» | README:46 «żadne hasło» / FAQ:238 «poprosić o hasło» |
| Абзац про ключ Gemini в `~/.config/autosound/critic-env` (README:42) | є | **нема** | **нема** | **нема** |
| Примітка «мідбас без LPF різкий на свіпі — норма» (README:80) | є | **нема** | є | є |
| Перша фраза в чат (README:62) | «tune a new car from scratch» | «налаштуймо авто з нуля» + EN | EN only | EN only |
| Перша фраза у FAQ «First launch» | «tune a new car from scratch» (:271) | «налаштуймо **нове** авто з нуля» (:273) | (рядок :273, текст DE) | «s…» (:273, текст PL) |
| Та сама фраза в інсталяторі | `install.sh:1218` «let's tune this car from scratch» | — | — | — |
| Рекомендація щодо 2.8.x (README:16) | «many choose to stick with» | «**варто обрати**» (сильніше) | «entscheiden sich daher viele» | «wiele osób wybiera» |
| Рядок навігації мов у FAQ | **нема** (FAQ.md:1-3) | є (:3, «Roadmap (EN, чернетка)») | є (:3) | є (:3) |
| «Antigravity access» у кроці входу agy | «has Antigravity access» (:270) | «має доступ до Antigravity» (:272) | «Zugang zu Antigravity hat» (:272) | **без Antigravity** — «zaloguj się na swoje konto Google» (:272) |
| Скелет заголовків FAQ | 42 заголовки | 42 | 42 | 42 — збігається |
| Розмір FAQ | 32 023 симв. | 32 301 симв. (53 KB — це UTF-8 кирилиці, не зміст) | 36 701 | 34 496 |

---

## Обіцянки vs код

| обіцянка (file:line) | де в коді | статус |
|---|---|---|
| README.md:42 «automatically back up … in a private repository»; FAQ.md:432 «installer offers an option to set up automated … backups» | `install.sh:554-559` (питання, ставить gh), `:1246-1247` («say to the AI: back this project up»); у `skills/` немає жодного `gh repo create` | **частково** — є gh + порада попросити ШІ, автоматики нема |
| README.md:86 «sends generalized lessons to a shared knowledge base» | `references/core/feedback-loop.md:56-57` — локальний `feedback-YYYY-MM-DD.md`, «The user sends the file themselves» | **нема** сервісу; є файл + ручне надсилання |
| FAQ.md:441 REW-EQ-CopyPaste-Assistant для інших DSP | `knowledge/dsp/_TEMPLATE.md:24`, `references/tooling/helix-eq-export.md:24`, `knowledge/dsp/profiles/musway-m6v4.json:182` | **є** (посилання на сторонній інструмент; «30+ platforms» — лише в `docs/changelog/archive…:1549`, у FAQ цього числа нема) |
| README.md:70 «2.8.x … works exclusively through the terminal» | `.claude-plugin/marketplace.json:14-18` — `ref: "2.x"`, sha v2.8.3; `install.sh:1039` «the skill … is the 2.x line — TCC cannot drive it» | **є** |
| README.md:59 «Autosound TCC app will appear on your desktop» | `install.sh:72-73` (`~/Applications/Autosound TCC.app` + симлінк на Desktop), `:878-900`; `install.ps1:127-128,860-870` (.lnk Desktop + Start Menu) | **є** (з попередженням-fallback «the command still works: autosound-tcc») |
| README.md:61 effort `xhigh` за замовчуванням; зміна — з наступної сесії | `tcc/src/autosound_tcc/core/model_choices.py:131`; `ui/tcc/i18n.py:579` | **є** для TCC; для терміналу — не описано |
| README.md:35 «installs with a single command» | `install.sh:559` (y/n GitHub), `:613-620` («Go ahead?»), `:661` (вікно Apple), `:1102-1179` (3 входи) | **частково** — одна команда + 2 питання + вікно + 3 входи |
| FAQ.md:269 «script will automatically run the `claude auth login`» | `install.sh:1121-1133` — лише інтерактивно, після Enter; інакше друкує команду | **є** (з умовою) |
| FAQ.md:277 «Updating: run the installation command again … latest tag v3.*» | `install.sh:49` `SKILL_TAG_GLOB="v3.*"`, `:700` `ls-remote --tags` | **є** (але FAQ дає рядок з `main`, README — з тегом) |
| FAQ.md:248 «REW (API on) shortcut on your Desktop» (Windows) | `install.ps1:887-900` | **є** (лише якщо REW знайдено) |
| FAQ.md:261 метод у `~/.claude/skills/.autosound-tuning-src` | `install.sh:63` (checkout), `:761` симлінк `~/.claude/skills/autosound-tuning` | **є** (симлінк не названо) |
| FAQ.md:132 шлях до `migrate.py` | `skills/autosound-tuning/rew_tool/state/migrate.py` існує | **є** |
| FAQ.md:331 fallback: self-loop / Clipboard Mode | `scripts/smoke_test.py:136-137`, `scripts/autosound_ai.py:926-938`, `setup-critic-channel.md §0, §7` | **є** |
| FAQ.md:99 «Diagnostics → Installation» у TCC | `tcc/…/i18n.py:304` «Diagnostics and updates…», `:133` «Installation» | **є** |
| FAQ.md:309 agy «requires no API keys … free OAuth login» | `setup-critic-channel.md:29-35` (Project ID, Enable API, «Watch the billing»), `install.sh:1157-1162` | **частково** — ключа нема, але є Project ID + Enable + біллінг |
| FAQ.md:456 «all 68 capabilities» | `references/core/capabilities.md` — 91 рядок | **неточно** |
| FAQ.md:60 «~700 MB free disk space» | `install.sh:569-593` ≈ 1.2 GB + 1 GB CLT | **неточно** |

---

## Розміри (п. 6)

FAQ не читає модель: у `SKILL.md` і `references/` посилань на `FAQ*.md` немає (grep по `skills/`: лише `scripts/issue_triage.py:98` — підказка для відповідей на issues, `rew_tool/capabilities.py:58` — назва i18n-check, `rew_tool/dsp_profile.py:473` — коментар). README теж не завантажується. Отже 32/53 KB — розмір **для людини**, токенів не коштує; 53 KB FAQ.uk — це 32 301 символ проти 32 023 в EN (кирилиця у UTF-8 по 2 байти), зміст того ж обсягу. Що модель **читає** завжди — `SKILL.md` (24.7 KB, 180 рядків), і саме там довгий description (див. 🟠 вище).

## Що з `setup-critic-channel.md` потрібно користувачу, а що — моделі

Користувачу (можна винести в FAQ): §1 вхід в `agy` (Project ID де взяти, Enable API, біллінг на проєкті Google Cloud — `:29-35`), §1 «Quota: WEEKLY … At 0% the channel returns empty for ~a week» (`:38`), §7 «немає CLI — копіюй у desktop-чат» (`:215-223`), укр. FAQ «Як увійти в agy» (`:227-258`). Решта — моделі: §0 self-loop, §2 slug-ids моделей, §3 `.critic-env`/secret-scan, §4 будь-який вендор, §5 `PROJECT_MIRROR`, §6 smoke, «reviewer that contradicts itself» (`:270`). Зараз файл змішує обидва голоси, і українська секція FAQ (`:227`) сидить усередині англійського довідника для моделі.
