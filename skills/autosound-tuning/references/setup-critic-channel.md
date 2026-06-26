# Setting up the Critic / Advisor channel (out-of-the-box)

The reviewer channel is a CLI wrapper (`scripts/gemini_critic.sh` + `scripts/gemini_advisor.sh`) that sends your Generator package to a **second AI** acting as Critic/Advisor — the single biggest quality lever in this method (one-perspective tuning is noticeably worse). The **role is core; the specific CLI is not.** This file gets the default channel working on a fresh machine, then lists fallbacks.

> 🩺 **Stuck? Run the doctor FIRST:** `scripts/gemini_critic.sh --doctor`. It checks the CLI, a fake-`agy` symlink, macOS quarantine, `.critic-env` syntax, the Contract/Context paths, and runs a live 1-line smoke — printing the exact fix for each, so you diagnose all of §1–§4 in ONE command instead of serially. (A real cold-start hit ~6 papercuts here; the doctor surfaces them at once.)

## 1. Install the CLI — `agy` (Antigravity) is the default

Google is steering free interactive access into **Antigravity (`agy`)**; `@google/gemini-cli`'s free OAuth sign-in is now **deprecated** (`IneligibleTierError`). So `agy` is the recommended default; gemini-cli-via-API-key is the cross-platform fallback (§2).

**macOS — install the REAL `agy`:**
```bash
brew install --cask antigravity-cli      # the REAL agy — NOT a symlink to gemini
```
- **Gatekeeper:** first launch may pop *"…can't be opened"* with a **Move to Trash** button — click **Done** (it's quarantine, not malware), then clear it:
  ```bash
  xattr -dr com.apple.quarantine "$(command -v agy)"
  ```
- **One-time login — in a REAL terminal:** `agy`'s login is an interactive browser OAuth and needs a TTY, so it **cannot** run inside Claude Code's `!` shell (`could not open TTY`). In **Terminal.app / iTerm**:
  ```bash
  agy        # opens a browser → sign in with the Google account that has Antigravity → then /quit
  ```
  The token persists; the wrappers' `-p` mode then works. (Don't smoke-test with `agy --version`/`-p` *before* this login — they hang / re-trigger OAuth.)
- **Quota:** Antigravity's free *Starter* tier is a **WEEKLY** Flash+Pro group limit. At 0% the channel returns empty for ~a week (`agy` shows the countdown) — fall back to §2 when it's dry.
- ⚠️ **Agentic — slow / hangs on BIG inputs.** `agy` is an *agentic* CLI; on a large `-p` package (tens of KB — e.g. several long docs at once) it can think for minutes or hang outright (seen: a 34 KB review timed out at 5 min, no output). Keep packages **lean** (decimated numbers, one focus — `analysis-playbook.md`). For a genuine bulk one-off review, skip the CLI and use the **copy-paste desktop channel (§7)** — faster and more reliable.

⚠️ **A FAKE `agy`** = a leftover symlink `agy → gemini`. The wrapper now **detects it**, warns, and runs the gemini flavor automatically (right model ids + `--skip-trust`) — but it isn't real Antigravity. Install the real one (above) or just use §2. `--doctor` flags this.

## 2. Fallback CLI — `@google/gemini-cli` via a FREE API key (cross-platform)

Use this when `agy` isn't available (Linux/Windows) or its weekly quota is dry. The **free OAuth tier is fully retired** — bare `gemini -p` (no key) now **hard-fails** with `IneligibleTierError: no longer supported … migrate to Antigravity` (confirmed 2026-06). So the **free API key is now mandatory** for the gemini flavor — authenticate with one (no card):
```bash
npm i -g @google/gemini-cli
# get a free key at https://aistudio.google.com/apikey , then in .critic-env (§4):
#   GEMINI_BIN=gemini
#   GEMINI_API_KEY=AIza...
```
The key is exported to gemini-cli automatically (the wrapper sources `.critic-env` with `set -a`). `--skip-trust` (gemini-cli refuses headless runs in an "untrusted" dir) is added automatically for the gemini flavor.

## 3. Models (the wrappers pick the right names per CLI)

| CLI | default (Flash) | opt-in Pro (hard calls) |
|---|---|---|
| `agy` | `Gemini 3.5 Flash (Medium)` | `Gemini 3.1 Pro (High)` |
| `@google/gemini-cli` | `gemini-2.5-flash` | `gemini-2.5-pro` |

Defaults are **Flash** (free, snappy, strong critic). Names drift — list current ones with `agy models` / `gemini models`. The wrapper auto-falls-back to the fallback model on quota/unavailable (429 / exhausted / `ModelNotFound`). Override per call:
```bash
GEMINI_CRITIC_MODEL="Gemini 3.1 Pro (High)" scripts/gemini_critic.sh pkg.md
```

## 4. Pin config once with `.critic-env`

Copy the shipped template (it's gitignored) and edit:
```bash
cp scripts/.critic-env.example rew_analitic/.critic-env
```
⚠️ **Quote any model name with spaces/parens**, or the file won't parse (`--doctor` catches this):
```bash
GEMINI_BIN=agy
GEMINI_CRITIC_MODEL="Gemini 3.5 Flash (Medium)"     # quotes REQUIRED
GEMINI_ADVISOR_MODEL="Gemini 3.1 Pro (High)"
# gemini fallback:
# GEMINI_BIN=gemini ; GEMINI_API_KEY=AIza… ; GEMINI_CRITIC_MODEL=gemini-2.5-flash
# PROJECT_MIRROR=/abs/path/to/project/rew_analitic   # only if CWD differs
```

## 5. Where the channel reads the project from (no cross-project leaks)

The wrappers inject the **Contract** (protocol) + your **project's `autosound_context.md`** as system framing, resolved **project-local FIRST**:
```
$PWD/rew_analitic/data-contract-template.md   ← preferred
$PWD/rew_analitic/autosound_context.md        ← preferred
   (fallback only: $AUTOSOUND_DIR, the author's iCloud canon)
```
So **launch Claude from the project directory** (CWD = the car you're tuning). `PROJECT_MIRROR` defaults to `$PWD/rew_analitic`.

> ⚠️ If the Critic ever cites a vehicle/history you don't recognise, it loaded a *different* project's context — fix the path here (or `PROJECT_MIRROR`), don't argue with the output.

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
