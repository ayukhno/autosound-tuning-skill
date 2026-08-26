# FAQ

Real questions people asked while setting this up and tuning with it, answered once here instead
of over and over in comments. The [README](README.md) is the short version; this page holds the
details. English only for now.

Have a question that isn't here? Open a [discussion or issue](https://github.com/ayukhno/autosound-tuning-skill/issues) and we'll add it.

## Table of contents

- [Choosing a path](#choosing-a-path)
  - [The four paths, and what each costs you](#the-four-paths-and-what-each-costs-you)
  - [Which one should I take?](#which-one-should-i-take)
  - [I already installed something — which is it?](#i-already-installed-something--which-is-it)
  - [Staying on 2.x](#staying-on-2x)
  - [Moving from 2.x to 3.x](#moving-from-2x-to-3x)
  - [What 3.x changed](#what-3x-changed)
- [Philosophy & structure: why AI?](#philosophy--structure-why-ai)
  - [Our mission & vision](#our-mission--vision)
  - [Why a specialised skill, and why state on disk](#why-a-specialised-skill-and-why-state-on-disk)
  - [The path: phases −1 to 5, and the desk-first way through them](#the-path-phases-1-to-5-and-the-desk-first-way-through-them)
  - [What the method refuses to do](#what-the-method-refuses-to-do)
  - [Which models is this actually supported on? (As of August 2026)](#which-models-is-this-actually-supported-on-as-of-august-2026)
  - [Subscription options, quotas & budgets (As of July 2026)](#subscription-options-quotas--budgets-as-of-july-2026)
  - [Why a full session uses fewer tokens than you'd expect](#why-a-full-session-uses-fewer-tokens-than-youd-expect)
- [First-time setup (macOS & Windows)](#first-time-setup-macos--windows)
  - [The installer does the setup](#the-installer-does-the-setup)
  - [What the installer puts where](#what-the-installer-puts-where)
  - [Signing in, and starting](#signing-in-and-starting)
  - [Updating, pinning a version, uninstalling](#updating-pinning-a-version-uninstalling)
- [TCC, the desktop app](#tcc-the-desktop-app)
  - [What it is, and whether you need it](#what-it-is-and-whether-you-need-it)
  - [One project, two windows](#one-project-two-windows)
  - [Which models the app offers](#which-models-the-app-offers)
  - [App updates, and reporting an app problem](#app-updates-and-reporting-an-app-problem)
- [Setting up the Gemini/Antigravity Critic (standalone)](#setting-up-the-geminiantigravity-critic-standalone-setup)
  - [macOS & Windows setup (Antigravity CLI — recommended)](#macos--windows-setup-using-antigravity-cli---recommended)
  - [Fallback: direct API setup (no CLI/Node.js)](#fallback-direct-api-setup-no-cli-or-nodejs-required)
  - [Do you have a version running on Google AI Studio?](#do-you-have-a-version-running-on-google-ai-studio)
  - [Can I ask Gemini to install and run the skill itself?](#can-i-ask-gemini-to-install-and-run-the-skill-itself-without-claude-code)
- [Measuring](#measuring)
  - [Measuring phase & time alignment: UMIK-1 vs. XLR microphones](#measuring-phase--time-alignment-umik-1-vs-xlr-microphones)
  - [Can I measure phase with a UMIK-1?](#can-i-measure-phase-with-a-umik-1)
  - [How do I name measurements in REW?](#how-do-i-name-measurements-in-rew)
  - [What is the capture session, and why protective filters only?](#what-is-the-capture-session-and-why-protective-filters-only)
  - [What are the p1…p9 positions and the ctl measurements for?](#what-are-the-p1p9-positions-and-the-ctl-measurements-for)
- [Target curves](#target-curves)
  - [Can I build my own target curve?](#can-i-build-my-own-target-curve)
- [The project on disk](#the-project-on-disk)
  - [What is in the project folder, and what is worth backing up?](#what-is-in-the-project-folder-and-what-is-worth-backing-up)
  - [Which DSPs, and how does the EQ get into mine?](#which-dsps-and-how-does-the-eq-get-into-mine)
  - [My tweeter and midrange share one DSP channel (a passive crossover) — does this work?](#my-tweeter-and-midrange-share-one-dsp-channel-a-passive-crossover--does-this-work)
  - [Where do I find what the method can do?](#where-do-i-find-what-the-method-can-do)

---

## Choosing a path

The same method reaches you four ways. The [README's table](README.md#choose-how-you-want-to-use-it)
is the short version; here is what each one actually asks of you and gives back.

### The four paths, and what each costs you

**1 · 3.x in a window — [TCC](#tcc-the-desktop-app).** The
[one-line installer](#first-time-setup-macos--windows) brings Claude Code, Python, the method, the
reviewer and the desktop app: the DSP tree, your measured curves, the plan and the AI in one window,
macOS and Windows, over the same project files the terminal uses. What you get with 3.x itself is
the project as data (a ledger you revert in one step), the desk-first path, EQ proposed as gated
packages, an entry control that confirms the car heard what the desk designed, tools that refuse
rather than report "no objection", and fixes that arrive as tags.
*Costs you:* a paid Claude plan, a REW beta with the API on, about 700 MB of disk — and the honesty
of a pre-release, with an app younger than the method it runs. Models other than Claude and Gemini
come through `omp` and are metered separately. *Take it if* you would rather see the tree and the
curves than read them.

**2 · 3.x in a terminal.** The same installer with `--terminal` / `-Terminal`: everything in path 1
except the window. The method writes the same files, so you can add the app later without moving
anything.
*Costs you:* the same subscription and REW, the same pre-release honesty, and everything happens in
text. *Take it if* you live in a terminal anyway, or the machine is thin on disk.

**3 · The 2.x line — the one that won.** A Claude Code plugin at
[`v2.8.3`](https://github.com/ayukhno/autosound-tuning-skill/releases/tag/v2.8.3) on branch
[`2.x`](https://github.com/ayukhno/autosound-tuning-skill/tree/2.x): the full iterative method,
REW read over its API, the analysis scripts, and the Generator ↔ Critic ↔ Arbiter loop. The four
2026 awards were tuned with it.
*Costs you:* a paid Claude plan, a REW beta with the API on, and a terminal — plus the ceiling of
what prose can hold: the project is written as text, so what is in force is re-read rather than
machine-checked, and the desk-first path, the ledger and the newer tools are not in it. It takes
fixes, not features. *Take it if* you want exactly what is proven, on the version that competed.

**4 · Web chat, nothing installed.** The
[manual_step-by-step](https://github.com/ayukhno/autosound-tuning-skill/tree/manual_step-by-step)
branch: each tuning step is a short prompt you paste into
[Google AI Studio](https://aistudio.google.com/) or any chat, together with your REW exports, and
the car's passport file comes back rewritten in full so nothing drifts between steps.
*Costs you:* nothing but your time — and all the work is manual. No REW API, no state on disk, no
review loop, none of the calculating tools. *Take it to* see whether the method suits you before
spending anything. Still labelled experimental.

### Which one should I take?

- **"I want the current method."** Path 1 if you would rather look at the tree and the curves,
  path 2 if you would rather type. Both update themselves to the newest 3.x tag.
- **"I want the tune that took the awards."** Path 3. The plugin entry names the 2.8.3 commit, so
  nothing moves you off it later.
- **"I don't want to install anything yet."** Path 4, then decide.
- **"I would rather drive with Gemini than with Claude."** That is a bootstrap rather than a path —
  [how, below](#can-i-ask-gemini-to-install-and-run-the-skill-itself-without-claude-code). On paths
  1–3 Gemini is the reviewer anyway, which is where it is strongest here.

You are not locked in: paths 1 and 2 are the same installation seen two ways, a project made in one
opens in the other, and 2.x → 3.x is [a documented move](#moving-from-2x-to-3x) that leaves the old
project untouched.

### I already installed something — which is it?

- **How it arrived.** `/plugin install autosound-tuning` inside Claude Code gave you 2.x. The
  `curl … | bash` / `irm … | iex` line, or the app, gave you 3.x.
- **What the project folder holds.** 2.x keeps `dsp-state-current.md` and `tuning-changelog.md`,
  prose. 3.x keeps `project.json`, a ledger of versions and `process-state.json`.
- **Ask the app.** In TCC, *Diagnostics → Installation* names the method version it runs with.

### Staying on 2.x

**You are already on it, and an update will not move you.** The marketplace entry names an exact
commit rather than a branch, so `/plugin marketplace update` cannot carry you across a major
version, and `/plugin update` brings you to the commit that entry names, which is 2.8.3.

To control it yourself — a local checkout of the `2.x` branch, which also takes 2.x fixes the
moment they land rather than when a pin moves — clone it once, in your terminal:

```bash
git clone -b 2.x https://github.com/ayukhno/autosound-tuning-skill.git ~/autosound-2x
```

Then, inside your Claude Code session, one command at a time:

```bash
/plugin marketplace add ~/autosound-2x
```

```bash
/plugin install autosound-tuning
```

A local path is **referenced, not copied** — that checkout *is* the plugin source. So
`git -C ~/autosound-2x pull` is how you take 2.x fixes, and nothing moves you onto a newer line
until you decide to; `git -C ~/autosound-2x checkout v2.8.3` pins you to that exact state. To
rejoin the normal channel later, remove the local marketplace and add `ayukhno/autosound-tuning-skill`
again. The 2.x documentation is [its own README](https://github.com/ayukhno/autosound-tuning-skill/blob/2.x/README.md).

### Moving from 2.x to 3.x

One skill per machine: two plugins shipping a skill of the same name both stay active, and which
one answers is anybody's guess. So remove the plugin first, inside Claude Code:

```
/plugin uninstall autosound-tuning
```

```
/plugin marketplace remove autosound-tuning-skill
```

Then run the install line from [First-time setup](#first-time-setup-macos--windows). Your 2.x
projects are not converted: 3.x imports the car's **current** state into a **new** project and
leaves the old one untouched:

```sh
python3 ~/.claude/skills/.autosound-tuning-src/skills/autosound-tuning/rew_tool/state/migrate.py <old-project> --into <new-project>
```

Channels and their output slots, crossovers, delays, gains, polarity, EQ and the DSP profile move
across. The journal and older snapshots stay behind, deliberately: 2.x never recorded which facts
were in force when, so carrying its history would mean inventing it.

### What 3.x changed

- **The project is data, not prose.** Facts in `project.json`, every crossover, delay, gain and
  filter in a ledger with the version it entered in, the process (which phase, which capture
  round, what was checked) in `process-state.json`. The AI reads the state instead of remembering
  it; the app reads the same files.
- **The desk-first path.** One capture session, the tune designed on predicted sums at the desk,
  one short verification in the car — see [the path](#the-path-phases-1-to-5-and-the-desk-first-way-through-them).
- **Tools that decide, with gates.** Alignment by the loss at each joint, EQ proposed as packages
  through gates, an entry control, session drift, the spread across positions, a ranked list of
  ear suspects. Each with its own selftest.
- **A method that refuses.** A check whose input is missing fails; it never reports "no
  objection" — [the list](#what-the-method-refuses-to-do).
- **An installer and an app.** One line brings everything; TCC runs the method in a window.
- **Patch tags reach you.** The installer and the app take the newest `v3.*` tag, so a fix is on
  your machine the next time either updates. The [CHANGELOG](CHANGELOG.md) carries an Upgrading
  note per tag.

---

## Philosophy & structure: why AI?

You absolutely *can* use a regular web chat with free versions of Claude or Gemini. The core of
this project is a **methodology**, not just software. But there is a fundamental difference
between a general chat and this structured, AI-assisted approach.

### Our mission & vision

Professional-grade car audio tuning should be accessible to every enthusiast. The goal is to show
modern AI not as a replacement for human judgement but as an **intellectual exoskeleton** for the
tuner.

The human (the Arbiter) remains the master who listens, feels the soundstage and makes the final
decisions. The AI is the exoskeleton: it computes the cabin's physics, reads phase and timing,
drives REW through its API, and offers bold, non-standard acoustic insight. Rigorous science and
human intuition together, to reveal the emotional depth and the pure joy of music in your car.

### Why a specialised skill, and why state on disk

- **The "memory drift" problem — why a general chat eventually fails.** A tune is iterative:
  measure, set crossovers, set delays, check phase, EQ, measure again. Over a long conversation a
  general model starts to forget or slightly alter the numbers decided at the beginning, and the
  suggestions turn contradictory or dangerous. *The solution:* the state lives on disk. In 3.x that
  is `project.json` (the facts: channels, DSP, microphone, target), the ledger (every crossover,
  delay, gain and filter, with the version it entered in), `process-state.json` (where the process
  stands) and `autosound_context.md` (the car's glossary and notes). Every time you invoke the AI it
  reads this single source of truth, and its memory is complete.
- **What a "skill" actually is.** A general model knows basic audio theory; it does not know car
  cabins, driver behaviour or safety boundaries. A skill is firmware for the AI: acoustic patterns,
  safety checklists (to protect your tweeters), target curves, a step-by-step process and the
  computing scripts. It turns a generic text generator into a calibration engineer that guides you
  by the hand.
- **Why local scripts and the REW API.** Measuring a car produces a lot of data — phase curves,
  impulse responses, RTA averages. Pasting rows of CSV or taking dozens of screenshots is tedious
  and error-prone. The Python scripts connect to REW's local API, pull the raw measurements,
  extract the acoustic essence (cancellations, resonances, timing) and hand the AI a digest in
  milliseconds. A ten-minute data-entry job becomes a two-second command — and a number the script
  computed is a number the model did not guess.

### The path: phases −1 to 5, and the desk-first way through them

The phases are the same on both lines; what 3.x adds is the desk in the middle. The car is visited
twice — once to capture, once to verify — and everything between is designed on the *predicted*
sum of your own measured drivers.

| Phase | Where | What happens | What comes out |
| :--- | :--- | :--- | :--- |
| **−1 Intake** | desk | The car, the drivers, the DSP and what it can do (its filters, its processing rate), the microphone, the target curve | `project.json`, the DSP profile, the checklist — nothing in the car is a surprise |
| **0 Capture** | car, once | Every driver alone, with *protective* filters only; sweeps and an MMM pass in one go; a few control positions around the head; the round checked before you leave | One usable capture round, drift and protective set on record |
| **1 Foundation** | desk | Crossovers, levels, delays and polarity chosen on the summed response predicted with the DSP's own filters; each joint scored by how little it loses; an alignment a whole cycle off is named | A ledger version with the foundation, and a predicted sum |
| **2 EQ** | desk | EQ as packages — a driver's own resonances (only where the peak stays put across positions and is minimum-phase), left/right shape, tone toward the target; cuts only by default; ≤ 6 bands per channel | One ledger version per accepted package; an export file for the DSP |
| **3 Verdict & lock** | car, short | You enter the sheet. An entry control confirms the car hears what the desk predicted, driver by driver (±1 dB at 1/6 octave, delay to 0.1 ms), or names the one that does not. Then fine EQ on the moving-mic average, and A/B by one band with the ear suspects — three rounds at most | The technical tune, locked |
| **4 Listening** | car | Test tracks, a cheat-sheet of what to listen for, the verdict written against the version that earned it | Listening verdicts in the journal |
| **5 Variations** | desk / car | Presets to taste on a virtual layer, the optional center-fill and rear-fill | Presets; the technical tune underneath stays intact |

When the desk and the car disagree — the entry control names a driver, a joint does not sum as
predicted — the path falls back to the iterative loop of 2.x for that step, and the ledger records
where. The full text is
[`references/phases/virtual-first.md`](skills/autosound-tuning/references/phases/virtual-first.md);
the phase files are listed in [`SKILL.md`](skills/autosound-tuning/SKILL.md).

### What the method refuses to do

A tool that answers "no objection" for want of data is worse than none, so these are refusals, not
warnings:

- **Write into your DSP.** It never has. Every change is yours to type or to import.
- **Set a delay from a single reading.** Four independent timing estimates must agree; when they
  don't, the disagreement is the finding.
- **Boost into a null.** An excess-phase test tells a fillable dip from an interference null; only
  the fillable one may be boosted, and boosts are off by default anyway.
- **Design on a capture round it cannot trust.** No protective set on record, drift between the
  first and last sweep, a driver missing — the round is refused and you are told what to remeasure.
- **A filter narrower than the seat allows.** The spread across the positions around the head sets
  the Q ceiling band by band; where no positions were measured the ceiling is 6, and the report says
  it is a default.
- **Chase the ear without end.** Three suspects per round, three rounds; then the answer is "leave
  it" or a new capture, not a fourth round.
- **Invent an import format.** A DSP without a writer of its own gets REW's Generic format or a
  format you supply, never a guessed syntax that fails quietly on import.

The table of what each tool refuses and why is
[`references/core/estimator-scope.md`](skills/autosound-tuning/references/core/estimator-scope.md).

### Which models is this actually supported on? (As of August 2026)

**Generator: Claude Opus, at `xhigh` effort. Reviewer: Gemini Pro (High).**

Read the next section — the money one — with that in mind, because the cheaper paths below are
real and they are also where this choice gets made.

**Any model can run the skill; that is the point of it being plain Markdown and Python.** But the
method has been driven end to end with exactly one combination, and the others are experiments —
a different model, a different vendor, or the same model asked to think less.

The thing to understand before you economise is that **a downgrade does not fail loudly. It
agrees with you.** One documented run closed phases −1 through 3 in a single sitting and reported
crossover points, delays to 0.1 ms, EQ "within ±0.5 dB", and a listening verdict — for a car
nobody had sat in. There is no error message for that. It reads like a finished tune, and the only
way to catch it is to already know what a real one costs in time and measurements.

Practical notes:

* **Effort is not a preference, it is half the recommendation.** `xhigh` on the Generator; set it
  where you set the model (`/model` inside Claude Code, or `claude --effort xhigh` at launch).
  Nothing raises effort on its own mid-session — a session started cheap stays cheap no matter
  how hard the work turns out to be.
* **For Gemini via `agy`, the effort tier *is* the model name.** `gemini-3.1-pro-high`, not
  `gemini-3.1-pro-low`. `(High)` is the whole instruction, and `(Low)` is a different reviewer
  rather than a discounted one. The Critic channel defaults to `xhigh` for the same reason — see
  [setup-critic-channel.md](skills/autosound-tuning/references/tooling/setup-critic-channel.md).
* **The Critic is the wrong place to save money.** A reviewer that never disagrees is not a cheap
  reviewer, it is an absent one, and it costs you the single check that catches the failure above.
* **A free Critic is still worth having.** Clipboard Mode into a free web chat is a genuine
  reviewer and far better than none — the warning here is about a *quiet, capable-sounding*
  downgrade, not about being on a budget.

**The date is part of the claim.** Model names move fast, and an undated recommendation goes stale
without anyone noticing. If you are reading this well after August 2026, check what the current
equivalents are rather than trusting these names.

### Subscription options, quotas & budgets (As of July 2026)

> [!WARNING]
> **Prices, quotas, free-credit offers and model names below are a snapshot (July 2026) and go
> stale fast.** Treat the dollar figures and limits as illustrative of the *shape* of the choice
> (cheap-solo vs. reliable-dual), not as current fact — verify the live pricing on the Anthropic
> and Google Cloud pages before committing.

In car audio, enthusiasts easily spend hundreds or thousands on hardware, where a single sheet of
sound deadening or a good RCA cable costs $20–50. For tuning with this tool there are three paths,
depending on your budget, your tolerance for rate limits and how much automation you want:

* **Option 1 (recommended baseline): Claude ($20/mo) + free Gemini as Advisor/Critic.**
  One month of Claude Pro for the strict, structured "driver" of the process, and Gemini as the
  Critic for free (Clipboard Mode, or a free API key from Google AI Studio). This is the shape of
  the [supported pair](#which-models-is-this-actually-supported-on-as-of-august-2026) — spend the
  subscription on Opus at `xhigh` rather than on more messages from a cheaper tier.
  * *Pros:* precise, the maths checked by the scripts, $20. Cancel the subscription once the car
    is tuned.
  * *Cons:* the free Gemini tier can hit rate limits during rapid back-to-back testing.

* **Option 2 (budget compromise): Gemini solo ($10 deposit).**
  A paid billing account on [Google Cloud](https://console.cloud.google.com/billing) with the
  minimum $10 deposit (which unlocks $300 in free credits for new accounts), and Gemini as the
  sole tuner.
  * *Pros:* very cheap; and Gemini in the driver's seat does produce striking acoustic insight and
    non-standard solutions.
  * *Cons:* memory drift under heavy context, so you double-check every parameter it quotes (a
    crossover it believes is at 200 Hz when you have 230, or none) and start every phase from a
    clean session (`/clear` + resume). And it is solo drive: one model proposing and approving its
    own work, with no second opinion to catch the failure described
    [above](#which-models-is-this-actually-supported-on-as-of-august-2026).

* **Option 3 (professional): both paid (Claude Pro $20 + Gemini Cloud API).**
  Claude Pro for the driver and a funded Google Cloud account for the Critic.
  * *Pros:* the full dual-AI review loop with no rate limits and no "quota exhausted" pauses; for
    professionals, people tuning several cars, or long back-to-back sessions.
  * *Cons:* $20 plus pay-as-you-go API usage, typically cents to a few dollars per session.

### Why a full session uses fewer tokens than you'd expect

A real full in-car session — bass shaping, HF imaging and a first-pass rear-fill, with measured
verification of every step, on the most capable Claude model — used noticeably less quota than
casual chat would suggest. That is by design:

1. **Raw measurement data never enters the chat.** A REW sweep is thousands of points; they stay
   inside the local scripts, and only digests come back ("zone median +5.3 dB", a five-row joint
   table). Analysis costs tokens in proportion to the *conclusion*, not the *data*. This is the
   biggest factor, and the main economic difference from the copy-paste manual method.
2. **State lives on disk, not in the context.** The ledger and the journal are re-read in slices
   when needed; the AI never re-narrates the project's history to itself turn after turn.
3. **The phase sliding window.** Only the active phase's reference (plus its neighbour) is loaded,
   never the whole corpus.
4. **Round-based review.** One Critic call per round on the whole batch, not per parameter, with a
   second pass only at phase gates.
5. **The Arbiter matters too.** Precise listening verdicts, measuring proactively and a screenshot
   instead of a description save whole round-trips; the cheapest tokens are the ones never spent.

Practical takeaway: a structured session on a strong model is dominated by *decisions*, not
*chatter*, so the strong model is affordable exactly where it counts. If your sessions feel
token-hungry, check that you are running with the local scripts, not the manual copy-paste path,
and resuming from the state on disk (`/clear` + resume) rather than carrying one endless
conversation.

---

## First-time setup (macOS & Windows)

You will need a laptop, a calibrated microphone and a DSP you can type into.

> [!IMPORTANT]
> **Subscription:** a paid **Claude Pro or Max** subscription, because Claude Code (the terminal
> agent) needs access that the free tier does not include. ChatGPT Plus plans cannot be
> transferred.

### The installer does the setup

One line installs Claude Code, Python, the tuning method, the desktop app, Google's `agy` for the
Gemini reviewer and `omp` (which is what lets the app offer models other than Claude), on a clean
machine. It shows what is already there, lists everything it will download, asks once, then runs
on its own; the sign-ins come at the end, in your browser (Claude first — required; the reviewer
and GitHub if you want them).

<details>
<summary><b>For macOS</b></summary>

1. **Open Terminal** (press **Cmd + Space**, type `Terminal`, and hit **Enter**).
2. **Paste this line:**
   ```bash
   curl -fsSL https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/main/install.sh | bash
   ```
3. On a Mac that has never been used for programming it asks for your **Mac password once**,
   right after the "Go ahead?" question, for Apple's Command Line Tools (git). Nothing else needs
   it. Then wait — ten to twenty minutes, nothing to press.
4. At the end it opens your browser for the Claude sign-in (a Pro or Max account), then offers
   the Gemini reviewer's sign-in and GitHub's — press **Enter** to do one now, **s** to leave it
   for later.

To leave something out: `--terminal` (no desktop app), `--no-reviewer`, `--no-github`, `--no-omp`,
after `bash -s --`.

</details>

<details>
<summary><b>For Windows</b></summary>

1. **Open Windows PowerShell** (press **Win**, type `powershell`, and hit **Enter**).
2. **Paste this line:**
   ```powershell
   irm https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/main/install.ps1 | iex
   ```
3. If Git for Windows is not installed yet, Windows shows **one permission dialog** for it —
   click **Yes**. Nothing else needs administrator rights; everything else goes into your user
   profile. Then wait, five to fifteen minutes.
4. The sign-ins at the end are the same as on macOS. The installer also puts a **REW (API on)**
   shortcut on your Desktop, which starts REW with its API switched on in one click.

To leave something out, run the one-liner in this form with the options you want:
`& ([scriptblock]::Create((irm https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/main/install.ps1))) -Terminal`
(no desktop app), `-NoReviewer`, `-NoGitHub`, `-NoOmp`. Prefer a double-click?
[Download the repository ZIP](https://github.com/ayukhno/autosound-tuning-skill/archive/refs/heads/main.zip),
*Extract All*, and double-click `install.cmd`.

</details>

### What the installer puts where

Everything goes into your user profile; nothing needs administrator rights except the two
one-time items named above.

| What | Where | Why |
| :--- | :--- | :--- |
| Claude Code | Anthropic's own installer | the AI that runs the method |
| The method (this repository, at its newest `v3.*` tag) | `~/.claude/skills/.autosound-tuning-src`, with `~/.claude/skills/autosound-tuning` pointing into it | where Claude Code looks for skills |
| **Autosound TCC** (the app, at its newest tag) with `uv` and a Python 3.12 of its own | `~/Applications/Autosound TCC.app` and a shortcut on your Desktop (macOS); your user profile and a Desktop shortcut (Windows) | the method in a window |
| `agy`, Google's Antigravity CLI | your user profile | Gemini as the reviewer |
| `gh`, GitHub's command *(only if you said yes)* | your user profile | the private project backup |
| `omp` | your user profile | lets the app offer models other than Claude (metered) |

### Signing in, and starting

* **Claude:** the installer runs `claude auth login` for you at the end. If you skipped it, run
  that command in a terminal: a browser window opens, you sign in with your Claude account (Pro or
  Max) and click **Authorize**.
* **The reviewer (Gemini):** run `agy` once — see [the Critic setup](#setting-up-the-geminiantigravity-critic-standalone-setup)
  — or press Enter when the installer offers it.
* **Start:** make one folder per car and open it either in the app (double-click **Autosound
  TCC** on your Desktop, *Browse…* to the folder, pick the models, *Open*) or in a terminal
  (`cd` into it, run `claude`), then say *"tune a new car from scratch"*. Open a *new* terminal
  window for that: the one you installed from cannot see what was just installed.

### Updating, pinning a version, uninstalling

* **Update:** run the same install line again. It takes the newest `v3.*` tag of the method and
  the newest tag of the app, and leaves your projects alone. The app also updates itself. What a
  tag changed, and anything to do after updating, is in the [CHANGELOG](CHANGELOG.md).
* **Pin a version:** `--skill-ref v3.0.32` and `--tcc-ref v0.1.12` (macOS, after `bash -s --`),
  `-SkillRef` and `-TccRef` on Windows.
* **Uninstall:** `--uninstall` (macOS, after `bash -s --`) / `-Uninstall` (Windows) removes what
  the installer put there and never a project folder. `--uninstall --all` / `-Uninstall -All` also
  removes `uv`, Claude Code and `~/.claude`, and `agy`/`gh`/`omp` when this installer brought them.

---

## TCC, the desktop app

### What it is, and whether you need it

[TCC](https://github.com/ayukhno/autosound-tcc) runs the 3.x method in a desktop window, on macOS
and Windows: the DSP tree on the left, the curves REW measured, the plan with its steps, the
ledger's versions, and the AI in a side panel. You do not need it: the method in a terminal is the
proven path, and everything the app shows is in the project's files. The app is for people who
would rather see the tree and the curves than read them, and it is early — say so to yourself when
it surprises you, and [report it](#app-updates-and-reporting-an-app-problem).

### One project, two windows

The app and the terminal are one project, not two. The method writes the project's files, the app
reads them, and a change made in either shows up in the other: a version banked in the terminal is
in the app's list, a step taken in the app is in the process state the terminal reads. Point both
at the same folder and switch as you like.

### Which models the app offers

The app talks to Claude through Anthropic's SDK, so your Claude subscription covers it — *AI main*
is Claude Opus (SDK) and *AI critic* is Gemini Pro (High), the [supported pair](#which-models-is-this-actually-supported-on-as-of-august-2026).
Gemini reaches it the same way it reaches the terminal: through `agy`, on your own Google sign-in.
Models beyond those two are what `omp` adds, and they are metered separately; leave `omp` out with
`--no-omp` / `-NoOmp` and the list is the supported pair.

### App updates, and reporting an app problem

The app updates itself and, with it, the method it carries — the same newest `v3.*` tag the
installer takes. *Diagnostics → Installation* shows which app version and which method version
you are on, and *Report a problem* there opens [the app's issue form](https://github.com/ayukhno/autosound-tcc/issues/new/choose)
half filled in. Problems with the *method* — wrong advice, a tool that refused when it should not
have — go to [this repository's issues](https://github.com/ayukhno/autosound-tuning-skill/issues/new/choose).

---

## Setting up the Gemini/Antigravity Critic (Standalone Setup)

The dual-agent **Generator ↔ Gemini (Critic)** loop is the strongest setup because it removes
single-model bias. The Critic runs in the background through a lightweight script
(`scripts/gemini_critic.sh`), so you do not manage a second AI window by hand.

This standalone setup is worth doing even if you are not using Claude Code — for a manual workflow,
or with other tools such as Cursor, ChatGPT or VS Code.

### macOS & Windows Setup (using Antigravity CLI - Recommended)

Google's official **Antigravity CLI (`agy`)** is the recommended default because it uses a free,
browser-based OAuth login and needs no API keys.

#### 1. Install the CLI

**The installer from [First-time setup](#first-time-setup-macos--windows) already did this** unless
you passed `--no-reviewer` / `-NoReviewer`. By hand, it is Google's own installer — no Homebrew, no
package manager, no administrator rights; it puts `agy` in your user profile and clears macOS's
quarantine flag itself:

* **macOS:**
  ```bash
  curl -fsSL https://antigravity.google/cli/install.sh | bash
  ```
* **Windows (PowerShell):**
  ```powershell
  irm https://antigravity.google/cli/install.ps1 | iex
  ```

Either way, open a **new** terminal window afterwards so it is on your PATH.

#### 2. Perform a one-time login

In your standard terminal (Terminal.app on Mac, PowerShell on Windows), run:
```bash
agy
```
* A browser window opens. Sign in with the Google account that has Antigravity access.
* Once authorised, return to the terminal and type `/quit`.

#### 3. Verify the installation

```bash
agy -p "Hello, world!"
```

---

### Fallback: Direct API Setup (No CLI or Node.js required!)

On **Linux**, where the Antigravity CLI is not available, or when your weekly Antigravity quota is
exhausted, the Critic can call Google's Gemini API directly with a free API key, with no Node.js,
npm or other command-line tools:

1. **Get a free API key** (no credit card) at **[aistudio.google.com/apikey](https://aistudio.google.com/apikey)**.
2. **Add it to your config:** create a file named `.critic-env` in your project's `rew_analitic/`
   folder (or in the folder you run from) with:
   ```env
   GEMINI_API_KEY=AIzaSy...your_actual_key...
   ```
3. That is it. The channel script (`autosound_ai.py`) detects the key and makes direct HTTPS calls
   to the Gemini API.

> [!TIP]
> **Do I have to set this up?**
> No. If no local Gemini CLI or API key is found, the skill falls back to an **Autopilot self-loop**
> (an isolated subagent inside Claude Code) or to **Clipboard Mode** (you paste proposals into any
> web AI of your choice, such as ChatGPT or Gemini web).

---

### Do you have a version running on Google AI Studio?

**Yes — that is [path 4](#the-four-paths-and-what-each-costs-you).** A set of stateless prompt
templates you run inside [Google AI Studio](https://aistudio.google.com/) or any web chat with free
Gemini, no local install and no API key:
**[manual_step-by-step branch](https://github.com/ayukhno/autosound-tuning-skill/tree/manual_step-by-step)**.
Each step is a fresh chat with a short copy-paste prompt plus your REW exports, and the car's
passport comes back rewritten in full, so nothing drifts between steps. What it does not have is
everything the local setup automates — the REW API, the state on disk, the review loop, the
calculating tools. Still labelled experimental; feedback from real sessions is welcome.

---

### Can I ask Gemini to install and run the skill itself, without Claude Code?

**Yes, as a manual bootstrap, not a formal install.** There is no plugin system for Gemini the way
Claude Code has one. But the skill is plain Markdown and Python, nothing Claude-specific, so you
can point an agentic Gemini session (Antigravity CLI, or any Gemini setup with file and shell
access) at the repository and ask it directly:

> Clone https://github.com/ayukhno/autosound-tuning-skill, read `skills/autosound-tuning/SKILL.md`,
> and follow that method as your operating instructions for this session.

One real caveat: Claude Code's skill system loads only the active phase on demand (the "phase
sliding window" in `SKILL.md`), which keeps the context focused over a long session. A Gemini
session that reads everything at once may not hold that discipline, on top of Gemini's documented
tendency to drift on long sessions.

The fully stateless, no-install alternative is the
[manual_step-by-step](https://github.com/ayukhno/autosound-tuning-skill/tree/manual_step-by-step)
pipeline described just above.

---

## Measuring

### Measuring Phase & Time Alignment: UMIK-1 vs. XLR Microphones

There is a major difference in how USB and XLR microphones handle time-critical phase measurements:

* **XLR microphones (Behringer ECM8000, Beyerdynamic MM1, …)** plug into an analog audio interface
  (a Focusrite Scarlett 2i2, say). This is ideal for phase because a **physical loopback cable** —
  one output routed back into an input — gives a sample-accurate timing reference.
* **UMIK-1 / UMIK-2** are USB microphones that plug straight into the laptop, bypassing the
  interface. With no physical loopback path there is no hardware timing reference.

### Can I measure phase with a UMIK-1?

**Yes.** You can still get accurate phase and delay with a USB microphone through REW's **Acoustic
Timing Reference**: instead of a loopback cable, REW plays a short high-frequency chirp from a
designated reference speaker (usually a tweeter) before each sweep to establish the timing offset.

For a step-by-step video on configuring REW for phase with a USB microphone, see RAW-Cat's
tutorial: [Measuring Speaker Phase in REW](https://www.youtube.com/watch?v=El-kwZ5_nnU).

> [!WARNING]
> **Take all sweeps in one run, and re-measure the first channel at the end.** Loopback or acoustic
> reference, **measure all the speakers in a single session** — not one now and the next after a
> fifteen-minute break with the heating on.
> * **Temperature is the one that moves things.** The speed of sound follows the cabin's air
>   temperature, so a few degrees change every arrival time — and with an acoustic timing reference
>   it moves the reference chirp's own path as well. Fractions of a millisecond: negligible against
>   a subwoofer's wavelengths, fatal for midranges and tweeters, where the same fraction is tens of
>   degrees of phase at the crossover and takes the focus with it.
> * **Sequential measurement has a floor, and it is per capture rather than per minute.** Measured
>   in this method's own control block: one speaker measured six times over eighteen minutes moved
>   its arrival by one sample (10 µs, about 3.6 mm of apparent path), and the movement tracked the
>   *captures*, not the idle time — seventeen idle minutes moved it 0.5 µs, while consecutive
>   captures moved it about 2.6 µs each. Over eight channels that accumulates to one or two samples:
>   below what matters for a woofer, not obviously below what matters for a tweeter.
> * **So measure it instead of assuming it.** Re-measure the first channel at the end of the round —
>   that control capture turns the floor from an assumption into a number. In 3.x the capture check
>   does the comparison for you, to a fraction of a sample, and a round that drifted is refused
>   rather than designed on.

### How do I name measurements in REW?

Names are the identity: the tools find a measurement by its title, so a title outside the grammar
is invisible to them. The grammar is small:

| Title | Meaning |
| :--- | :--- |
| `m-L_01 (sw)` | channel `m-L` (left midrange), capture round `01`, a sweep |
| `m-L_01 (rta)` | the same channel and round, the moving-mic average |
| `sw_01 (sw)` · `w-R_01 (sw)` · `tw-L_01 (sw)` | subwoofer, right midbass, left tweeter |
| `L_01 (rta)` · `ALL_01 (rta)` | the left side summed; everything summed |
| `m-L p5_01 (sw)` | the same driver measured at position `p5` (also written `m-L_01 (sw) p5`) |
| `m-L-ctl1_01 (sw)` · `m-L-ctl3_01 (sw)` | the *controls* that open and close a series (`m-L_01ctl` / `m-L_01rep`, as typed in the car, read the same) |
| `m-L_final (sw)` | the sweep of the locked tune |

Channel codes come from your project's glossary (`sw`, `w-L/R`, `m-L/R`, `tw-L/R` are the common
ones); the round number goes up every time you go back to the car with a change. The capture sheet
for one session, in the order to take them, is
[`references/phases/capture-session-sheet.md`](skills/autosound-tuning/references/phases/capture-session-sheet.md),
and `naming.py` in `rew_tool/` validates a title before you type it into REW. Keep REW's history
clean — rename or delete a mistyped measurement at once, because a stray title is either ignored
or, worse, mistaken for a real one.

### What is the capture session, and why protective filters only?

The capture session is the one visit to the car in which every driver is measured *alone*, sweeps
and MMM in one pass, with only **protective** filters in the DSP: a high-pass on the midranges and
tweeters so a full-range sweep cannot hurt them, and nothing else — no crossovers, no delays, no
EQ. The reason is what the recording is for. A measurement taken through a tune carries the tune,
and every later design step would be reasoning about the tune instead of the driver. A measurement
taken with protective filters carries the driver and the cabin; the protective set is recorded in
the ledger with the round, and the desk removes it from the curves before predicting anything, so
the design sees the bare driver and enters its own filters on top.

**Playing one driver at a time** is done in the DSP, not in REW: mute everything but the channel
being measured (the PC-Tool, Conductor, or whatever your processor's software is), and keep one REW
output level and one head-unit level for the whole session so the levels of different drivers stay
comparable. On Windows that usually means REW on the ASIO driver of your interface; on macOS, the
interface as REW's output device. The sheet you take into the car —
[`capture-session-sheet.md`](skills/autosound-tuning/references/phases/capture-session-sheet.md) —
carries the whole order, the REW settings and the levels to write down.

The round is checked before you leave the car: are all the drivers there, do the first and last
sweep agree in time, is the protective set on record. A round that fails is not designed on — it is
remeasured while the microphone is still on the stand.

### What are the p1…p9 positions and the ctl measurements for?

A curve is true at a certain width, and which width depends on where the microphone is. A resonance
of the driver stays put when the microphone moves a few centimetres; a reflection comb or a
seat-position dip moves with it. So a few extra sweeps of the same driver at positions around the
listener's head — `p1…p9`, with `p5` the centre and `p1/p5/p9` repeated as the centre's own
control — tell the desk the *spread* at every frequency, and with it:

- which features **stay** (the driver — EQ may correct them) and which **move** (the seat — EQ at
  the desk will not fix them, and it is told so);
- **how narrow a filter may be**, band by band: the Q ceiling. Where no positions were taken the
  ceiling is the borrowed default of 6, and the proposal says it is a default;
- whether the centre **drifted** between the first and last repeat — the usability of the set.

The `ctl` measurements are the controls that open and close a series of sweeps of one driver, so
that the drift within the series is measurable rather than assumed.

---

## Target curves

### Can I build my own target curve?

**Yes — and you often should.** A target ("house") curve is not a fixed standard; it is a
*per-project starting hypothesis* that you finalise by ear after the baseline. There is no single
correct curve: each car, install and taste ends up with its own.

Two practical ways to build one:

**1. Ask the skill to design it.** Describe your taste and the skill proposes a shape, runs it
through the Generator ↔ Critic ↔ Arbiter loop, and exports it for REW and your DSP. The more
concretely you describe the *character* you want, the better the result. Useful things to tell it:
- your genres and how you listen (low volume vs. loud, long drives);
- the direction against a reference: *"start from ResoNix Accurate but +2 dB more sub-bass and
  calmer highs"*, or *"like SQ-Comp-Ref with a slightly deeper presence dip for laid-back vocals"*;
- any complaints about the current sound in frequency-character language (*boomy, honky, thin,
  sibilant, no air*…).

Example prompts:
> *"Build me a custom target curve: warm, punchy bass for rock, vocals slightly forward, gentle highs — start from Half Whitledge and show me the shape."*
>
> *"Blend Audiofrog and Harman into one target with Audiofrog's timbre but a bit more deep bass, then compare it against both."*

The skill writes a two-column `freq dB` file (log-spaced, 20 Hz–20 kHz) into the project's
target-curve folder, records it as the active curve, and derives from it the per-driver targets
that the EQ proposals aim at. You still confirm the final shape by ear with the measured baseline
in hand.

> *Reality check: the AI will draw whatever curve you ask for, but your speakers have to support it
> physically — make sure your midbass and subwoofer have the power and excursion headroom before
> committing to an aggressive low-end boost.*

**2. Draw it yourself in the Nono Tuning Tool** ([nonotuningtool.com](https://nonotuningtool.com)
→ *Custom Target Curve*), export the `.txt`, and drop it into the project or onto the visualizer.

**Compare and sanity-check it** against the well-known reference curves, and see what each hump or
dip means for your instruments, in the interactive comparison tool:
**[open the curve visualizer online](https://ayukhno.github.io/autosound-tuning-skill/_curve-visualizer.html)**
(works offline too; drag your `.txt` in, compare it side by side against SQ-Comp-Ref / ResoNix /
Audiofrog / Harman / Jazzi / Whitledge, and right-click any point for a frequency-character guide).

---

## The project on disk

### What is in the project folder, and what is worth backing up?

One folder per car; copying the folder copies the whole tune. In 3.x it holds:

- **`project.json`** — the facts: channels and their output slots, the DSP profile, the
  microphone, the target;
- **the ledger** — every crossover, delay, gain, polarity and filter, with the version it entered
  in, and the snapshots (`registry.json`) you can return to in one step;
- **`process-state.json`** — where the process stands: the phase, the capture rounds and what was
  checked on each;
- **`autosound_context.md`** and the journal — the car's glossary, the notes, the listening
  verdicts;
- the target curves, the analysis notes, the DSP configuration backups and the export files.

What is worth backing up is exactly that list: small files, and no amount of re-measuring brings
them back. The raw sweeps are not on it: they run 16 to 112 MB apiece, they live in REW's own
`.mdat` files on your disk, and if you ever needed them again you would re-measure. The installer
offers a **private** GitHub repository for the backup and signs `gh` in; the backup itself happens
when you tell the AI to back the project up, and it knows what stays out.

### Which DSPs, and how does the EQ get into mine?

Any processor you can type into. The method never writes into a DSP; it writes a file:

- **Helix, MATCH, BRAX** (Audiotec Fischer): the Full EQ file the PC-Tool imports in one go.
- **Everything else:** REW's Generic format — twenty slots, neutral — or its Extended form when
  a crossover has to ride along with the EQ. Processors without file import, such as Musway, ESX
  and Zapco, take it through the
  [copy-paste helper](https://github.com/IvanBakhmutov/REW-EQ-CopyPaste-Assistant).
- **A format of your own:** a vendor format can be supplied during a session. What the method
  will not do is guess one: a guessed import syntax produces a file that looks right and fails
  quietly.

Whatever the format, the numbers are checked against what your DSP can do — its filter types, its
band count, its processing rate — before they are written, and a filter that will not fit is
reported rather than dropped.

### My tweeter and midrange share one DSP channel (a passive crossover) — does this work?

**Yes, with one thing it cannot do.** A passive pair on one amplifier channel is *one* channel to
the method: it is measured as one, it gets one target, one delay and one set of EQ bands, and the
ledger holds it as a single row. Everything the path does — the prediction, the joint to the
midbass or the sub, the entry control, the EQ packages — works on it unchanged.

What no software can do from outside is time-align the tweeter to the midrange *inside* that pair,
or move the passive crossover point: those live in the passive network, and the only inputs are the
network itself and the physical positions. So the method will say what the pair's summed response
does, including a suck-out at the passive crossover if there is one, and it will not pretend it can
correct one half of it. Splitting the pair into two DSP channels — an amplifier channel each — is
the change that removes the limit, and it is a hardware decision, not a tuning one.

### Where do I find what the method can do?

The board: [`references/core/capabilities.md`](skills/autosound-tuning/references/core/capabilities.md).
Sixty-seven capabilities in thirteen directions — talking to REW, naming and capture rounds,
protective filters, time and junctions, crossovers and levels, targets, EQ, prediction and
verification, listening, the project on disk, the review channel, safety and abstention, the
health of the install — each with the words you would say, what you get, the command, what it
needs and refuses without, the phase it belongs to, how mature it is, and where to read the
reasoning. It is written for a session that comes with its own process ("I have my measurements,
only align the sub-to-midbass joint") as much as for the AI; a checker in the test suite keeps it
honest against the code.
