# Setting up the Critic / Advisor channel (out-of-the-box)

The reviewer channel is a CLI wrapper (`scripts/gemini_critic.sh` + `scripts/gemini_advisor.sh`) that sends your Generator package to a **second AI** acting as Critic/Advisor — the single biggest quality lever in this method (one-perspective tuning is noticeably worse). The **role is core; the specific CLI is not.** This file gets the default Gemini channel working on a fresh machine, then lists fallbacks.

> A real cold-start install hit five papercuts here (CLI missing, stale model names, headless trust block, wrong context loaded, broken path math). The wrappers + this doc now handle all five — but read it once so nothing surprises you.

## 1. Install a Gemini CLI

Two CLIs work; the wrappers **auto-detect** which you have (no config needed):

- **`@google/gemini-cli`** (official, npm — recommended for a fresh setup):
  ```bash
  npm i -g @google/gemini-cli
  gemini            # first run: sign in (free Google account / API key)
  ```
- **`agy`** (Antigravity) — the skill author's rig. If you already have it, the wrappers pick it automatically.

Detection order: `agy` if present, else `gemini`. Force one with `GEMINI_BIN` (see §3).
**Don't symlink `agy → gemini`** — that confuses model ids + flags. Just install `gemini` and let detection use it.

## 2. Models (the wrappers pick the right names per CLI)

| CLI | default model (Flash) | opt-in Pro (hard calls) |
|---|---|---|
| `@google/gemini-cli` | `gemini-2.5-flash` | `gemini-2.5-pro` |
| `agy` | `Gemini 3.5 Flash (Medium)` | `Gemini 3.1 Pro (High)` |

Defaults are **Flash** (free, snappy, strong critic). Opt into Pro per call:
```bash
GEMINI_CRITIC_MODEL=gemini-2.5-pro scripts/gemini_critic.sh pkg.md
```
Model names drift — list current ones with `gemini models` (or `agy models`). The wrapper auto-falls-back to Flash if the chosen model is exhausted/unavailable (429 / quota / `ModelNotFound`).

`--skip-trust` (gemini-cli refuses headless runs in an "untrusted" dir) is added **automatically** for the `gemini` flavor. Override all extra flags with `GEMINI_EXTRA_ARGS`.

## 3. Where the channel reads the project from (no cross-project leaks)

The wrappers inject two files into Gemini as system framing: the **Contract** (protocol) and your **project's `autosound_context.md`** (the car/DSP/state). They resolve **project-local FIRST**:

```
$PWD/rew_analitic/data-contract-template.md   ← preferred
$PWD/rew_analitic/autosound_context.md        ← preferred
   (fallback only: $AUTOSOUND_DIR, the author's iCloud canon)
```

So **launch Claude from the project directory** (CWD = the car you're tuning). `PROJECT_MIRROR` defaults to `$PWD/rew_analitic`.

> ⚠️ Why this matters: if the Critic loads a *different* project's context (e.g. the author's iCloud `_AI/Autosound/autosound_context.md`), it will confidently cite sessions and a car that aren't yours — and leak that car's install specifics (crossovers, driver geometry) as if they were facts about your build. Project-local-first prevents this. If you ever see the Critic reference a vehicle/history you don't recognise, your context path is wrong — fix it here, don't argue with the output.

## 4. Pin config once with `.critic-env` (optional)

Drop `rew_analitic/.critic-env` (gitignore it) to set anything once instead of per-call:
```bash
# rew_analitic/.critic-env  — sourced automatically by both wrappers
GEMINI_BIN=gemini
GEMINI_CRITIC_MODEL=gemini-2.5-flash
GEMINI_ADVISOR_MODEL=gemini-2.5-pro
# PROJECT_MIRROR=/abs/path/to/project/rew_analitic   # only if CWD differs
```

## 5. Smoke-test before you rely on it

After any install/CLI/model change, run one real micro-package — the channel can break silently (a flag rename once killed both wrappers; only the smoke test caught it):
```bash
printf '## Test\nChannel check: reply with one line "channel works".\n' > /tmp/smoke.md
scripts/gemini_critic.sh /tmp/smoke.md
```
Expect a one-line Gemini reply + a `— [critic: <model>]` tag (or `[advisor: …]` for the advisor variant). A `*: not found` / `context not found` / `no Gemini CLI` error tells you exactly which of §1–§3 to fix.

An **empty reply** (just the tag, no text) ≠ a crash — it usually means the CLI's **quota is exhausted** or it lost auth. `agy`'s Antigravity *Starter* tier shares a **weekly** quota per model group (Gemini Flash/Pro together); when it hits 0% it returns empty with no error text (and refreshes ~weekly — `agy` shows the countdown). The wrapper now prints a loud WARNING for this. Recover by switching to a model group that still has quota (`GEMINI_CRITIC_MODEL` / `GEMINI_ADVISOR_MODEL`), or pin the other CLI: `GEMINI_BIN=gemini` in `rew_analitic/.critic-env`.

## 6. No Gemini? Use the fallback ladder (the ROLE still happens)

The reviewer role is vendor-agnostic (`../review-loop/SKILL.md`). If there's no Gemini CLI:
1. **Any other AI** in a second window — paste the package, ask it to play Critic.
2. **Claude in a SEPARATE session** as reviewer (cross-session self-review; TWO-PASS anti-anchoring — see `review-loop`).
3. **The human** as reviewer.

Never skip the second perspective just because the `agy`/`gemini` channel isn't set up — set up a fallback instead.
