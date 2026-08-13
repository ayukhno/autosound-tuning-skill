# Setting up the Critic-Advisor channel (out-of-the-box)

The reviewer channel is critical to prevent single-perspective bias. **The strongest setup is a second, different AI vendor** — Claude + Gemini — via the CLI wrappers (§1–§4) or a manual chat (§7). The Autopilot self-loop (§0) is a **fallback** for when no second AI is available.

## 0. Autopilot self-loop — FALLBACK (only when you have no second AI)
If no second AI is available, the Generator can run the loop by programmatically spawning an isolated subagent — **no external API keys or CLI logins required**. ⚠️ Same-model review shares the model's blind spots (**not** true cross-vendor anti-anchoring) and is the mode where long autonomous sessions have drifted (lost DSP state / phase). Prefer §1–§4 or §7 whenever a second vendor exists.
* **How to verify/smoke-test it:**
  Simply spawn a quick test subagent named `critic_advisor` with an isolated context and ask: *"Channel check: reply with one line 'Autopilot works'."*.
  If you get a reply, the fallback is ready. Only rely on it when a second vendor genuinely isn't available (§1–§7).

## 1. Install and Set up the CLI — `agy` (Antigravity)

> 🩺 **Stuck? Run the doctor FIRST:** `scripts/gemini_critic.sh --doctor`. It checks the CLI, macOS quarantine, `.critic-env` syntax, the Contract/Context paths, and runs a live 1-line smoke — printing the exact fix for each, so you diagnose all of §1–§3 in ONE command instead of serially. (A real cold-start hit ~6 papercuts here; the doctor surfaces them at once.)

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

| Role | `agy` default | `gemini` CLI default |
|---|---|---|
| **Critic** | `Gemini 3.1 Pro (High)` | `gemini-2.5-pro` |
| Advisor / routine | `Gemini 3.5 Flash (Medium)` | `gemini-2.5-flash` |
| Fallback (quota dry) | Flash | Flash |

> ℹ️ **`Gemini 3.5/3.1` are Antigravity's own display labels** (what `agy models` shows), NOT real Gemini versions — the direct-API path (`autosound_ai.py`, no CLI) maps them to `gemini-2.5-flash` / `gemini-2.5-pro`. Use the label your channel expects: the `agy` CLI wants the display name; a raw `GEMINI_API_KEY` call wants the `gemini-2.5-*` id.

**The Critic defaults to Pro** — a Flash critic praises and misses obvious problems (field-observed); "don't praise" prompt text doesn't fix a too-weak model. Flash remains the advisor/routine default and the automatic fallback (⚠️ agy Starter shares one weekly Flash+Pro quota — Pro burns it faster; when dry, pin Flash or use the manual channel §6). Names drift — list current ones with `agy models`. Override per call:
```bash
GEMINI_CRITIC_MODEL="Gemini 3.5 Flash (Medium)" scripts/gemini_critic.sh pkg.md  # force Flash
```

## 3. Pin config once with `.critic-env`

Copy the shipped template (it's gitignored) and edit:
```bash
cp scripts/.critic-env.example rew_analitic/.critic-env
```
⚠️ **Quote any model name with spaces/parens**, or the file won't parse (`--doctor` catches this):
```bash
GEMINI_BIN=agy
GEMINI_CRITIC_MODEL="Gemini 3.5 Flash (Medium)"     # quotes REQUIRED
GEMINI_ADVISOR_MODEL="Gemini 3.1 Pro (High)"
# PROJECT_MIRROR=/abs/path/to/project/rew_analitic   # only if CWD differs
```

### Any vendor, not only Gemini (SCR-033)

The reviewer's transport is a parameter now. `autosound_ai.py` reads the model name, works out
whose it is, and takes that vendor's API or CLI — so the Arbiter can pick a Claude or GPT
reviewer and still get an automated channel rather than the clipboard.

```bash
AUTOSOUND_CRITIC_MODEL=claude-opus-5      # or gemini-2.5-pro, gpt-5.2, …
AUTOSOUND_ADVISOR_MODEL=gemini-2.5-pro    # a DIFFERENT vendor from the Generator is the point
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

`GEMINI_CRITIC_MODEL` / `GEMINI_ADVISOR_MODEL` still work and mean "the reviewer's model",
whatever the vendor — every documented setup exports them and a front-end already sets them, so
renaming would have broken working installs to tidy a table. `AUTOSOUND_*` wins when both are set.

**There is no default model any more.** With neither variable set, the script asks an installed CLI
what it can run and uses the first answer; if nothing answers, it says so and goes to clipboard
mode. It used to fall back to a named model, which is a promise to keep updating a name — the old
default was two generations stale before anyone noticed, and a stale default fails as an opaque API
error instead of "nobody told me which model to use". Same reason the display-label→API-id table is
gone: **a table of model names is a maintenance commitment**, and this file could not keep it.

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
Expect a one-line reply + a `— [critic: <model>]` tag (or `[advisor: …]`). An **empty reply** (just the tag) ≠ a crash — it's almost always **quota exhausted** (agy's weekly tier) or lost auth; the wrapper prints a loud WARNING. Recover by switching the model group, re-logging-in `agy`, or pinning the gemini API-key path (§2).

## 7. No CLI — or the CLI is slow/dry? Use a manual channel (the ROLE still happens)

The reviewer role is vendor-agnostic (`review-loop.md`). When there's no CLI — **or `agy` is quota-dry / hanging on a big package** — go manual:
1. **Copy-paste into a desktop chat** *(field-proven; the go-to when the CLI chokes)* — `cat package.md | pbcopy`, paste into a **Gemini / Claude / ChatGPT desktop chat** where you have a subscription / tokens, then paste the reply back. No CLI, no quota juggling, no agentic stalls — ideal for a **bulk one-off** review (e.g. several long docs at once). Real use: a 4-language README review the agentic CLI couldn't finish.
2. **Any other AI** in a second window — same idea, ask it to play the Critic.
3. **Claude in a SEPARATE session** (cross-session self-review; TWO-PASS anti-anchoring — see `review-loop.md`).
4. **The human** as reviewer.

Never skip the second perspective just because the `agy`/`gemini` channel isn't set up or is slow — use a manual channel instead.

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

**Both roles now default to Pro.** The Critic already did; the Advisor was on Flash to save the shared weekly quota, and that turned out to be a false economy on any question about *method*.

Field case: the Advisor was asked to settle whether a per-position residual was a real spatial gradient or measurement noise. The Flash reply called it a genuine gradient in section 1 and explained the same residual as hand-trajectory instability in the Q&A of the same document — **both sides of the one question it existed to answer**, with no acknowledgement of the contradiction. Re-run on `gemini-3.1-pro-high` it settled the question, and additionally overturned the Generator's proposed lever on grounds neither party had raised. Cost of the weak round: one full package cycle.

Rule of thumb: **routine pings and "does this look sane" → Flash is fine; anything that decides whether a method, a metric, or an error bar is valid → Pro.** If quota forces a fallback, the wrapper now says so loudly — treat that round as advisory and re-run before banking anything resting on it.

⚠️ **Model names drift.** `agy models` has moved from display labels (`Gemini 3.1 Pro (High)`) to slug ids (`gemini-3.1-pro-high`); both forms were accepted as of 2026-08-01. List the current names before assuming a pinned name still resolves — an unresolvable name is one of the ways the channel returns an empty reply.

## A reviewer that contradicts itself is a result, not a failure

Read the reply as evidence about the review, not only about the subject. If two sections answer the same question differently, the round did **not** settle it — say so in the ledger and re-run, rather than quoting whichever half agrees with the plan. The same applies to a reviewer that endorses a proposal while missing that it re-opens a banked decision: that is a signal the package omitted context, and the fix is in the package (see the Generator's omission of the live HF split, 2026-08-01), not in the reviewer.
