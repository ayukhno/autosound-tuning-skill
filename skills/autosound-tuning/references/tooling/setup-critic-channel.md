# Setting up the Critic-Advisor channel (out-of-the-box)

The reviewer channel is critical to prevent single-perspective bias. **The strongest setup is a second, different AI vendor** — Claude + Gemini — via the CLI wrappers (§1–§4) or a manual chat (§7). **§7 holds THE ladder** — which channel to reach for, in order, both when setting one up and when the one you have stops answering. Every other file points here rather than keeping its own list.

## 0. The whole thing in five lines

```bash
brew install --cask antigravity-cli            # the CLI (macOS; Windows → §1)
agy login                                      # or put a key in the machine file below
printf 'GEMINI_CRITIC_MODEL=gemini-pro-latest\n' > ~/.config/autosound/critic-env
scripts/gemini_critic.sh --doctor              # one command, diagnoses everything in §1–§3
scripts/gemini_critic.sh package.md            # a real review
```

**Where the key lives, and why there:** `~/.config/autosound/critic-env` — **outside every
repository**. A project-local `.critic-env` is still read (for models, paths, `GEMINI_BIN`), but if
it carries a key AND git would take it — tracked, or not in `.gitignore` — the wrapper **refuses to
run** and says how to fix it. `.gitignore` alone was never enough: it does not stop `git add -f`, a
folder copy, or a backup that is not git at all. The key never needs to leave this machine, and
nothing here prints it — the doctor reports its SHAPE (`current` / `OLD` / `unrecognised, N chars`).

**Which doctor.** The one for the channel you actually use: `scripts/{gemini,claude,codex}_critic.sh
--doctor` checks that vendor's CLI, its auth, the paths and a live one-line smoke.
`python3 scripts/autosound_ai.py doctor` is the one for the **direct-API** path (a key, no CLI) and
checks the contract and context files it would send. They answer different questions; running the
one for your channel is the answer to "why is the reviewer unreachable".

---

## 1. Install and Set up the CLI — `agy` (Antigravity)

> 🩺 **Stuck? Run the doctor FIRST:** `scripts/gemini_critic.sh --doctor`. It checks the CLI, macOS quarantine, `.critic-env` syntax, the Contract/Context paths, the API key's shape and liveness (one free `GET /v1beta/models`), and runs a live 1-line smoke — printing the exact fix for each, so you diagnose all of §1–§3 in ONE command instead of serially. (A real cold-start hit ~6 papercuts here; the doctor surfaces them at once.) It recognises the **closed `gemini` CLI sign-in** (§2) by Google's own words and says "use agy" instead of a generic error.

Google's official CLI is **Antigravity (`agy`)**. It is fully cross-platform (macOS and Windows) and is the sole, unified way to invoke the Gemini Critic-Advisor channel.

**macOS — install the REAL `agy`:**
```bash
brew install --cask antigravity-cli      # the REAL agy — NOT a symlink to gemini
```
- **Gatekeeper:** first launch may pop *"…can't be opened"* with a **Move to Trash** button — click **Done** (it's quarantine, not malware), then clear it:
  ```bash
  xattr -dr com.apple.quarantine "$(command -v agy)"
  ```
- **One-time login (Claude or Terminal):** You can execute `agy`'s interactive login flow directly through Claude Code's interactive terminal or in standard shells (Terminal.app / iTerm). Run:
  ```bash
  agy
  ```
  The CLI will prompt for your **Google Cloud Project ID** and then provide a verification link with an OAuth code.
  - **Google Cloud Project ID:** Retrieve the exact **Project ID** from your [Google AI Studio (Projects)](https://aistudio.google.com/app/apikey) details modal (not the project name or number).
  - **Enable the API in that project — a missing step until 2026-08-13, and the channel cannot work without it.** A fresh account logs in fine, `agy models` lists models, and the first real call comes back:
    > `Error: Agent Platform API has not been used in project <id> before or it is disabled.`

    Open `https://console.developers.google.com/apis/api/aiplatform.googleapis.com/overview?project=<YOUR_PROJECT_ID>`, press **Enable**, and give it a few minutes to propagate. The error carries that link already, with your project filled in.
  - **Watch the billing on that project.** The calls run through *your* Google Cloud project, not past it, whatever the free-tier wording elsewhere suggests. If you keep separate balances in AI Studio and Cloud, this is the Cloud one.
  - **OAuth Verification Code:** Open the generated URL in a browser, log in with your Google account, copy the code, and paste it back into your terminal.
  The authorization token will be saved and persist across sessions. (Do not smoke-test `agy --version`/`-p` before completing this login, as they will hang/re-trigger OAuth).
- **Quota:** Antigravity's free *Starter* tier is a **WEEKLY** Flash+Pro group limit. At 0% the channel returns empty for ~a week (`agy` shows the countdown) — fall back to manual channel (§6) when it's dry.
- ⚠️ **Agentic — slow / hangs on BIG inputs.** `agy` is an *agentic* CLI; on a large `-p` package (tens of KB — e.g. several long docs at once) it can think for minutes or hang outright (seen: a 34 KB review timed out at 5 min, no output). Keep packages **lean** (decimated numbers, one focus — `analysis-playbook.md`). For a genuine bulk one-off review, skip the CLI and use the **copy-paste desktop channel (§6)** — faster and more reliable.

## 2. Models

**One reviewer, one model — and no default.** The Critic and the Advisor are one role (the
Arbiter's ruling, 2026-09-11; hub SKL-032, skill#27): one model variable, one call path —
`*_advisor.sh` and `autosound_ai.py advisor` are second doors to the critic's. Nothing in the
scripts names a model: with `GEMINI_CRITIC_MODEL` unset the wrapper prints `agy models` and
stops (exit 3) for you to pick. A fallback model runs only if you name one
(`GEMINI_FALLBACK_MODEL`); without it, a dry quota is reported, not papered over with a weaker model.

| What | Where it comes from |
|---|---|
| **The reviewer's model** | `GEMINI_CRITIC_MODEL` (`AUTOSOUND_CRITIC_MODEL` for any vendor) — an id from `agy models`, left column; a Pro `-high` tier |
| Fallback (quota dry) | `GEMINI_FALLBACK_MODEL` — only if set |

> ⛔ **The `gemini` CLI path (`@google/gemini-cli`, `GEMINI_BIN=gemini`) is CLOSED for its own sign-in — 2026-09-08, gemini-cli 0.50.0, both models.** A session in a car followed an older revision of this page, tried it first, and lost ~10 minutes to this, verbatim:
>
> `Error authenticating: IneligibleTierError: This client is no longer supported for Gemini Code Assist for individuals. To continue using Gemini, please migrate to the Antigravity suite of products: https://antigravity.google`
>
> Google shut the free OAuth tier the CLI signed in with; `agy` (§1) is what replaced it. **A key does not reopen it as installed:** with a fresh `AQ.`-shaped `GEMINI_API_KEY` in the environment the same CLI still went to its sign-in and printed the text above (probed 2026-09-08 — its stored auth mode decides, not the variable). Treat the `gemini` CLI as closed; the wrappers keep detecting it only to NAME the closed path: "шлях gemini CLI закрито Google, використовуй agy", and they stop rather than fall back to the other model, which fails at the same sign-in. A `GEMINI_API_KEY` still matters for the **direct API** (`autosound_ai.py`, §3) — and there the model ids come from the key, not from this page: the `gemini-2.5-pro` / `gemini-2.5-flash` ids this page used to list answered `404 … no longer available to new users` under a working key on 2026-09-08, while `gemini-3.6-flash` and Google's own pointers `gemini-pro-latest` / `gemini-flash-latest` answered. **When the pinned model is gone, or none is named, the script prints the key's list and stops (exit 3) — the choice is the Arbiter's**, not a fall-through to a CLI or the clipboard with the same stale name.

> ℹ️ **`Gemini 3.5/3.1` are Antigravity's own display labels** (what `agy models` shows beside the slug ids), NOT real Gemini versions. Use the name your channel expects: the `agy` CLI wants its slug id (`gemini-3.1-pro-high`; the display label is rejected since agy 1.1.12); a raw `GEMINI_API_KEY` call wants the `gemini-2.5-*` id.

**Name a Pro tier** — a Flash reviewer praises and misses obvious problems, and asked to settle a question it endorsed both sides of it (field-observed — «Which model for which role» below); "don't praise" prompt text doesn't fix a too-weak model. ⚠️ agy Starter shares one weekly Flash+Pro quota — Pro burns it faster; when dry, name a fallback or use the manual channel §6. Names drift — which is exactly why none is kept here: `agy models` is the list, and `--doctor` smokes **the model you named** and prints that list beside it when agy does not know the name. Override per call:
```bash
GEMINI_CRITIC_MODEL=gemini-3.1-pro-high scripts/gemini_critic.sh pkg.md  # slug id — agy ≥ 1.1.12 rejects the display label
```

## 3. Pin config once — the KEY outside the project, the rest in it

**The API key does not go in the project folder.** That folder is the one the README suggests
backing up to a private GitHub, so a key kept there is one `git push` from leaving. It lives
per-machine instead, and both the shell wrappers and `autosound_ai.py` read it from there first:

```bash
mkdir -p ~/.config/autosound                       # Windows: %APPDATA%\autosound\
cp scripts/.critic-env.example ~/.config/autosound/critic-env
chmod 600 ~/.config/autosound/critic-env
```

**And do not `export GEMINI_API_KEY` from your shell profile.** A file is read by whoever knows
its path; an exported variable is handed to **every** process you start — every npm package, every
agent, every `env` and `ps e`. The wrappers export it themselves for the length of their own run,
which is as long as it needs to exist. If you call `gemini`/`agy` by hand, export it in that one
shell rather than in `~/.zshrc`.

**Check the key itself, not only its presence** — the doctor does, and by hand it is one free call:
```bash
curl -s -o /dev/null -w '%{http_code}\n' "https://generativelanguage.googleapis.com/v1beta/models?key=$GEMINI_API_KEY"
# 200 → live · 400 with API_KEY_INVALID in the body → not this key
```
Two facts cost a session its time on 2026-09-08, and both are about the KEY, not the channel:
- **AI Studio issues keys in a new shape — `AQ.` + 53 characters.** The old shape, `AIza` + 39
  characters, is what every earlier note here showed. An old-shape key answers `API_KEY_INVALID`
  once a new one has been issued for the project; the doctor prints which shape it sees.
- **A session's environment does not follow `~/.zshrc`.** A key changed in the profile after the
  session started is not what that session holds: the old export stays in `env`, the wrappers
  export it over the file's value for their own run, and a key that is perfectly valid in the
  profile reads as invalid from inside the session. Which is one more reason the key belongs in
  the file (§3 above) and not in an export: the file is read fresh on every call. The doctor says
  when the key it sees came from the shell rather than from a file.

Everything non-secret — models, `GEMINI_BIN`, `PROJECT_MIRROR` — can still sit in the project,
where it belongs with the car it describes:

```bash
cp scripts/.critic-env.example rew_analitic/.critic-env   # then delete the key line from it
```

Both files are read, the machine one first, so an existing project-local setup keeps working.
A project's `.gitignore` now really does cover `.critic-env` — `project_seed.py` writes it when
the project is created (before, this page said "it's gitignored" and nothing wrote one). That is
the second line, not the first: `.gitignore` stops none of `git add -f`, a copied folder, or a
backup that is not git.

**A file that can carry a key MUST be ignored — and that is checked, not promised** (the user's
rule, 2026-09-08, after the "it's gitignored" months). Three carriers:
- **Both doors refuse the dangerous case.** A project-local `.critic-env` that carries an
  `*_API_KEY` line inside a git repository and that git would take — tracked, or not in
  `.gitignore` — stops the wrappers (`gemini_critic.sh` and its advisor door) and `autosound_ai.py` with the fix
  printed (add the line, or move the key to the machine file; a TRACKED one also says *rotate*,
  because the history already has it). A file with no key line, or outside any repository, is
  read as before. `--doctor` reports which side of the rule a project file is on.
- **`scripts/secret-scan.py`** scans a repository for a tracked/unignored key file and for
  key-shaped strings in tracked text (Google `AIza…`/`AQ.…`, Anthropic, OpenAI, or a real value
  under a `*_API_KEY=` name) — naming the file and line, never the value. `scripts/run-selftests.sh`
  runs it on this tree, so CI fails before a tag can carry a key.
- **`scripts/secret-scan.py --install-hook <repo>`** writes a pre-commit hook that runs the same
  scan on the staged change; a foreign hook is never overwritten. Install it in every repository a
  project lives in — the skill's own and the car's.

**The file is read as `KEY=VALUE`, never executed.** A line containing `$(`, a backtick or `;` is
dropped with a message — before, this file was `source`d, so a project someone else wrote ran
arbitrary shell the moment you started the reviewer.

⚠️ **Use the slug ids `agy models` prints in its left column** — the display labels in the right
column (`Gemini 3.1 Pro (High)`) are rejected by agy ≥ 1.1.12 (`invalid model selection`), and a
quoted label is what this block used to show. Quotes are harmless either way (`--doctor` catches a
malformed line):
```bash
GEMINI_BIN=agy
GEMINI_CRITIC_MODEL=gemini-3.1-pro-high              # THE reviewer model (one role) — an id from `agy models`
# GEMINI_FALLBACK_MODEL=<id>                         # only if you want one when the quota is dry
# PROJECT_MIRROR=/abs/path/to/project/rew_analitic   # only if CWD differs
```

### Any vendor, not only Gemini (SCR-033)

The reviewer's transport is a parameter now. `autosound_ai.py` reads the model name, works out
whose it is, and takes that vendor's API or CLI — so the Arbiter can pick a Claude or GPT
reviewer and still get an automated channel rather than the clipboard.

```bash
AUTOSOUND_CRITIC_MODEL=gemini-pro-latest # the reviewer, any vendor — a DIFFERENT one from the Generator is the point
# AUTOSOUND_CRITIC_PROVIDER=anthropic     # only when the name does not give the vendor away
# AUTOSOUND_CRITIC_BIN=claude             # force one binary, whatever is on PATH
# AUTOSOUND_CRITIC_EFFORT=xhigh           # how hard the reviewer thinks; default xhigh
```

**Effort defaults to `xhigh`, not to each CLI's own default.** A Critic that rubber-stamps is worse
than no Critic, and the failure this channel exists to catch — a model that closed four phases in
one sitting and reported a finished tune on a car nobody had sat in — is exactly what a cheap
reviewer looks like: it never disagrees. It is not `max`: a review is a one-shot call on a package
that is already written, and on a metered key the difference is the Arbiter's money.

**Google is the exception, deliberately.** `agy` publishes each effort tier as its own model
(`gemini-3.1-pro-high` vs `gemini-3.1-pro-low`) instead of taking a flag, so for that vendor the
effort IS the model name — pick the `(High)` variant. Nothing is passed on the command line there;
a flag would be rejected and the channel would break for one vendor only, quietly.

| Vendor | API key | Local CLI | Model names that resolve to it |
|---|---|---|---|
| `google` | `GEMINI_API_KEY` | `agy`, `gemini` | anything with `gemini`/`google` — **and anything unrecognised** |
| `anthropic` | `ANTHROPIC_API_KEY` | `claude` | `claude`, `opus`, `sonnet`, `haiku`, `fable` |
| `openai` | `OPENAI_API_KEY` | `codex` | `gpt`, `o1`, `o3`, `codex` |

`GEMINI_CRITIC_MODEL` still works and means "the reviewer's model", whatever the vendor — every
documented setup exports it and a front-end already sets it, so renaming would have broken working
installs to tidy a table. `AUTOSOUND_CRITIC_MODEL` wins when both are set. The second slot's names
(`GEMINI_ADVISOR_MODEL`, `AUTOSOUND_ADVISOR_MODEL`, `CLAUDE_/CODEX_ADVISOR_MODEL`) are **no longer
read** — one reviewer, one model — and a value left in one is named on stderr rather than obeyed.

**There is no default model any more.** With neither variable set and a Google key present, the
script asks the key what it can call, **prints that list and stops (exit 3) for you to choose** —
it does not take the first name (an `agy` slug such as `gemini-3.8-flash-high` is not an API id and
answered 404 there, 2026-09-08). With no key it asks an installed CLI what it can run and **prints
that list and stops the same way** — it used to take the first answer, which was choosing for the
Arbiter; if nothing answers, it says so and goes to clipboard mode. It used to fall back to a
named model, which is a promise to keep updating a name — the old default was two generations stale
before anyone noticed, and a stale default fails as an opaque API error instead of "nobody told me
which model to use". Same reason the display-label→API-id table is gone: **a table of model names
is a maintenance commitment**, and this file could not keep it. The same rule applies when a pinned
model retires under you: the 404 becomes the list, and the run stops on it. `gemini-pro-latest` /
`gemini-flash-latest` are Google's own pointers to the current Pro / Flash, so a pin on them
follows the models; a dated id stays put until Google retires it.

`scripts/autosound_ai.py doctor` answers the question that actually matters: which vendor the
chosen reviewer belongs to, and whether THAT vendor's key or CLI is present. A `claude` on PATH
does nothing for a Gemini reviewer.

## 5. Where the channel reads the project from (no cross-project leaks)

The wrappers inject the **Contract** (protocol) + your **project's `autosound_context.md`** as system framing, resolved **project-local FIRST**:
```
$PWD/rew_analitic/data-contract-template.md   ← preferred
$PWD/rew_analitic/autosound_context.md        ← preferred
   (fallback only: $AUTOSOUND_DIR — an OPTIONAL cross-project canon dir you set yourself; unset by default)
```
So **launch Claude from the project directory** (CWD = the car you're tuning). `PROJECT_MIRROR` defaults to `$PWD/rew_analitic`.

> ⚠️ If the Critic ever cites a vehicle/history you don't recognise, it loaded a *different* project's context — fix the path here (or `PROJECT_MIRROR`), don't argue with the output.

> ⚠️ **Keep the mirror's `autosound_context.md` CURRENT — the Critic grades you against it.** Field case (2026-07-15): a mirror assembled from a stale copy (predating the build's center channel) made the Critic flag the Generator's *correct* statement as "context drift — re-read the config". When you assemble/copy a `PROJECT_MIRROR` for the wrappers, reconcile the context file with the live ledger/state first (append a dated ADDENDUM with the current channel map and active preset if the original is user-owned). A critic on stale context spends its round policing ghosts.

## 6. Smoke-test before you rely on it

`--doctor` (top of file) already runs a live smoke. Or by hand after any CLI/model change:
```bash
printf '## Test\nChannel check: reply with one line "channel works".\n' > /tmp/smoke.md
scripts/gemini_critic.sh /tmp/smoke.md
```
Expect a one-line reply + a `— [critic: <model>]` tag (the advisor door answers with the same tag — it is the same reviewer). An **empty reply** (just the tag) ≠ a crash — it's almost always **quota exhausted** (agy's weekly tier) or lost auth; the wrapper prints a loud WARNING. Recover by switching the model group, re-logging-in `agy`, or going to the direct API with a key through `autosound_ai.py` (§3; the `gemini` CLI is closed, §2).

## 7. THE LADDER — which reviewer to reach for, in order

**One list, two uses:** it is the order to set a channel up in (Phase −1), and the order to descend
when the channel you have stops answering mid-session. Every other file points here instead of
keeping a list of its own — three lists that disagreed is what this section replaced (2026-09-09).

0. **Wait / retry — mid-session only.** An empty reply is usually an exhausted quota or lost auth,
   not a crash (§6); a minute or a model-group switch often costs less than changing channel.
1. **A CLI wrapper on ANOTHER vendor than the one driving** — `scripts/{gemini,claude,codex}_critic.sh`
   (or `autosound_ai.py` with an API key, §3). This is the recommended default: Generator one vendor,
   reviewer the other, which is what cross-vendor anti-anchoring means. Verify with `--doctor`.
2. **Clipboard mode — a desktop or web chat of any vendor** *(field-proven; the go-to when the CLI
   chokes)*. `cat package.md | pbcopy`, paste into a **Gemini / Claude / ChatGPT** chat where you have
   a subscription, paste the reply back. No CLI, no quota juggling, no agentic stalls — and the best
   answer for a **bulk one-off** (a real case: a 4-language README review the agentic CLI could not
   finish). `autosound_ai.py --mode clipboard` writes the package to `process/reviews/` so a review
   answered by hand does not look like no review at all.
3. **The same vendor at a higher tier**, when no second vendor is available at all — weaker, because
   the blind spots are shared, and it must be said out loud in the round's record.
4. **Claude in a SEPARATE session** — cross-session, TWO-PASS anti-anchoring (`review-loop.md`).
   A separate session a human opens; **not** a spawned background agent (see the note below).
5. **The human** as reviewer.

> ⛔ **What is NOT on this ladder: a background sub-agent as the reviewer.** Spawning an isolated
> same-model agent to critique your own proposal was a tier here until 2026-09-09 and is gone by the
> user's ruling. Two reasons, both paid for: the blind spots are the model's own, so the critique
> agrees with the proposal for the same wrong reason; and spawning a reviewer CLI inside an agent
> session deadlocks (~15 of 20 field sessions). If no channel on this ladder is reachable, the round
> is **blocked and says so** — `process.py <project>/process block <step> "<reason>"` — rather than
> passing a self-review off as a second perspective.

Never skip the second perspective just because the `agy`/`gemini` channel isn't set up or is slow —
descend the ladder instead.

---

## FAQ / Часті Питання (Agy Login Flow)

### Q: Як правильно увійти в Antigravity CLI (`agy`) через Claude або термінал?

**A:** Для успішного входу в `agy` виконайте такі кроки:

1. **Запустіть процес входу:**
   Ви можете запустити `agy` безпосередньо в інтерактивному середовищі Claude Code або у вашому стандартному терміналі (Terminal / iTerm / PowerShell):
   ```bash
   agy
   ```

2. **Введіть Google Cloud Project ID (Критично важливий крок!):**
   При першому запуску `agy` привітає вас і запитає:
   `Enter Google Cloud Project ID:`
   
   > [!IMPORTANT]
   > Не вводьте назву проекту або його числовий номер. Вам потрібен саме унікальний текстовий **Project ID**.
   > Його можна знайти там, де ви створювали свій API-ключ:
   > 1. Перейдіть до [Google AI Studio (Projects)](https://aistudio.google.com/app/apikey) або клікніть посилання прямо у вікні.
   > 2. У списку проектів відкрийте деталі вашого поточного проекту (Project details).
   > 3. Знайдіть поле **Project id** та скопіюйте його текстове значення (наприклад: `gen-lang-client-0354681673`).

3. **Введіть код авторизації зі сторінки (OAuth Verification Code):**
   - Після введення правильного Project ID утиліта `agy` згенерує унікальне посилання для верифікації та покаже код авторизації.
   - Відкрийте це посилання у браузері, увійдіть під вашим Google-акаунтом (на якому активовано Antigravity) та дозвольте доступ.
   - Скопіюйте отриманий код та вставте його назад у термінал Claude / звичайний термінал, де запущено `agy`.

4. **Завершіть авторизацію:**
   Після вставки коду та натискання `Enter` ви успішно увійдете в систему. Напишіть `/quit`, щоб вийти з інтерактивного режиму `agy`. 
   
   Токен збережеться локально, і тепер виклики Радника/Критика через скрипти (наприклад, `scripts/gemini_critic.sh`) працюватимуть автоматично і безперешкодно!

## Which model for which role (updated 2026-08-01)

**Both roles now default to Pro.** The Critic already did; the Advisor was on Flash to save the shared weekly quota, and that turned out to be a false economy on any question about *method*. *(2026-09-11: there are no longer two roles or any default — one reviewer, the model you name. The case below is why that name should be a Pro tier.)*

Field case: the Advisor was asked to settle whether a per-position residual was a real spatial gradient or measurement noise. The Flash reply called it a genuine gradient in section 1 and explained the same residual as hand-trajectory instability in the Q&A of the same document — **both sides of the one question it existed to answer**, with no acknowledgement of the contradiction. Re-run on `gemini-3.1-pro-high` it settled the question, and additionally overturned the Generator's proposed lever on grounds neither party had raised. Cost of the weak round: one full package cycle.

Rule of thumb: **routine pings and "does this look sane" → Flash is fine; anything that decides whether a method, a metric, or an error bar is valid → Pro.** If quota forces a fallback, the wrapper now says so loudly — treat that round as advisory and re-run before banking anything resting on it.

⚠️ **Model names drift.** `agy models` has moved from display labels (`Gemini 3.1 Pro (High)`) to slug ids (`gemini-3.1-pro-high`); both forms were accepted as of 2026-08-01. List the current names before assuming a pinned name still resolves — an unresolvable name is one of the ways the channel returns an empty reply.

## A reviewer that contradicts itself is a result, not a failure

Read the reply as evidence about the review, not only about the subject. If two sections answer the same question differently, the round did **not** settle it — say so in the ledger and re-run, rather than quoting whichever half agrees with the plan. The same applies to a reviewer that endorses a proposal while missing that it re-opens a banked decision: that is a signal the package omitted context, and the fix is in the package (see the Generator's omission of the live HF split, 2026-08-01), not in the reviewer.
