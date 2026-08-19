# FAQ

Real questions people asked while trying to set this up, answered once here instead of over and over in comments. English only for now — worth translating once there's enough on this page to justify it.

Have a question that isn't here? Open a [discussion or issue](../../issues) and we'll add it.

## Table of Contents

- [Philosophy & Structure: Why AI?](#philosophy--structure-why-ai)
  - [Our Mission & Vision](#our-mission--vision)
  - [Why We Need Specialized AI & Local State](#why-we-need-specialized-ai--local-state)
  - [The 5-Step Tuning Journey](#the-5-step-tuning-journey)
  - [Which models is this actually supported on?](#which-models-is-this-actually-supported-on-as-of-august-2026)
  - [Subscription Options, Quotas, & Budgets (As of July 2026)](#subscription-options-quotas--budgets-as-of-july-2026)
  - [Why a full session uses fewer tokens than you'd expect](#why-a-full-session-uses-fewer-tokens-than-youd-expect)
- [First-Time Setup (macOS & Windows)](#first-time-setup-macos--windows)
  - [The installer does the setup](#the-installer-does-the-setup)
  - [Signing in, and starting](#signing-in-and-starting)
- [Setting up the Gemini/Antigravity Critic (Standalone)](#setting-up-the-geminiantigravity-critic-standalone-setup)
  - [macOS & Windows Setup (Antigravity CLI - Recommended)](#macos--windows-setup-using-antigravity-cli---recommended)
  - [Fallback: Direct API Setup (No CLI/Node.js)](#fallback-direct-api-setup-no-cli-or-nodejs-required)
  - [Do you have a version running on Google AI Studio?](#do-you-have-a-version-running-on-google-ai-studio)
  - [Can I ask Gemini to install and run the skill itself?](#can-i-ask-gemini-to-install-and-run-the-skill-itself-without-claude-code)
- [Measuring Phase & Time Alignment: UMIK-1 vs. XLR](#measuring-phase--time-alignment-umik-1-vs-xlr-microphones)
  - [Can I measure phase with a UMIK-1?](#can-i-measure-phase-with-a-umik-1)
- [Target curves](#target-curves)
  - [Can I build my own target curve?](#can-i-build-my-own-target-curve)

---

## Philosophy & Structure: Why AI?

You absolutely *can* use a regular web-chat with free versions of Claude or Gemini! The core of this project is a **methodology**, not just software. However, there is a fundamental difference between a general chat and our structured AI-assisted approach. Here is how our philosophy and the entire tuning process are organized into four key aspects:

### Our Mission & Vision

We believe that professional-grade car audio tuning should be accessible to every enthusiast. Our goal is to showcase the power of modern AI not as a replacement for human judgment, but as a powerful **intellectual exoskeleton** for the tuner.

The human (the Arbiter) always remains the master who listens, feels the soundstage, and makes final decisions. The AI acts as the exoskeleton—instantly calculating complex cabin physics, analyzing phase alignments, automating tasks via the REW API, and offering bold, non-standard acoustic insights. We bridge the gap between rigorous science and human intuition to reveal the true emotional depth and pure joy of music in your car.

### Why We Need Specialized AI & Local State

To make AI-assisted tuning highly reliable, repeatable, and automated, we solve three major limitations of generic web chats:

* **The "Memory Drift" Problem (Why general chat eventually fails):**
  Tuning a car is a highly iterative process (measuring, adjusting crossovers, set delays, check phase, EQ). Over a long conversation, **general AI models suffer from "context drift"**—they start to forget or slightly alter the exact numbers decided at the beginning, leading to contradictory or dangerous suggestions.
  *The Solution:* We keep your active DSP configuration on disk (`dsp-state-current.md` and `tuning-changelog.md`). Every time you invoke the AI, it reads this "single source of truth" from disk, restoring 100% of its memory instantly.

* **What a Specialized "Skill" Actually Is:**
  A general AI model knows basic audio theory, but it doesn't know car cabins, specific driver behaviors, or safety boundaries. A **Skill** is like installing a custom "firmware" into the AI. It loads specialized acoustic patterns, safety checklists (to protect your tweeters), target curves (like ResoNix or Audiofrog), and calculation scripts. It turns a generic text generator into a professional car-audio calibration engineer that guides you by the hand.

* **Why We Use Local Scripts & APIs (Optional but Powerful):**
  Measuring a car generates massive amounts of data (phase curves, impulse responses, RTA sweeps). Copying and pasting thousands of rows of CSV data or taking dozens of screenshots is tedious and error-prone. Our Python scripts connect directly to **REW's local API**. They automatically pull the raw measurements, extract the acoustic essence (phase cancellations, cabin resonances, timing deltas), and feed them to the AI in milliseconds. It turns a 10-minute manual data entry job into a 2-second automated command.

### The 5-Step Tuning Journey

Regardless of whether you use our automated scripts (Level 2) or simply follow our guidebook in a free web-chat (Level 1), the process always follows this rigorous 5-step roadmap:

1. **System Audit & Target Selection (Baseline & Target)**
   We document your physical hardware (speaker placement, amps, DSP native sample rate) and agree on a target acoustic curve (e.g., flat monitor, warm bass, or competition-grade). We also run a flaw-analysis pass on that same baseline — which frequencies are EQ-able versus physically unfixable (phase cancellation, cabin interference), where L/R pairs decorrelate, and each driver's distortion floor — so later steps don't chase a fix that can't work.
2. **Building the Stage (Crossovers & Delays)**
   We **select and configure** the exact crossovers for each speaker so they play in alignment and within their optimal performance ranges. Then, we apply precise time-alignment delays so sound from every speaker arrives at your ears at the exact same microsecond, creating a razor-sharp, stable stereo image on your dashboard.
3. **Tonal Balance & Phase Matching (EQ & Phase Alignment)**
   We use the parametric EQ to tame major cabin resonances and smooth out vocals. **Our core philosophy here is Phase Alignment over surgical EQ: we focus on matching the acoustic phases of the speakers at their crossover points, consciously minimizing the number of EQ bands used.** This is a deliberate compromise with the "ideal" mathematical curve to preserve a live, dynamic, and natural soundstage rather than forcing a flat but lifeless response.
4. **Objective & Subjective Verification (Technical Lock & Listening)**
   We verify our work using specialized acoustic sweeps and then listen to critical test tracks **from specialized music-testing libraries, which you can buy, find on the internet, or stream on popular services**. We check for center focus, stage width/depth, and any harshness or boominess.
5. **Tailoring to Taste (Voicing & Variations)**
   We build subtle variations and presets tailored to your preferences (e.g., a high-energy rock preset, a highly detailed jazz preset, or a relaxed daily driving profile).

### Which models is this actually supported on? (As of August 2026)

**Generator: Claude Opus, at `xhigh` effort. Reviewer: Gemini Pro (High).**

Read the next section — the money one — with that in mind, because the cheaper paths below are real and they are also where this choice gets made.

**Any model can run the skill; that is the point of it being plain Markdown and Python.** But the method has been driven end to end with exactly one combination, and the others are experiments — a different model, a different vendor, or the same model asked to think less.

The thing to understand before you economise is that **a downgrade does not fail loudly. It agrees with you.** One documented run closed phases −1 through 3 in a single sitting and reported crossover points, delays to 0.1 ms, EQ "within ±0.5 dB", and a listening verdict — for a car nobody had sat in. There is no error message for that. It reads like a finished tune, and the only way to catch it is to already know what a real one costs in time and measurements.

Practical notes:

* **Effort is not a preference, it is half the recommendation.** `xhigh` on the Generator; set it where you set the model (`/model` inside Claude Code, or `claude --effort xhigh` at launch). Nothing raises effort on its own mid-session — a session started cheap stays cheap no matter how hard the work turns out to be.
* **For Gemini via `agy`, the effort tier *is* the model name.** `gemini-3.1-pro-high`, not `gemini-3.1-pro-low`. `(High)` is the whole instruction, and `(Low)` is a different reviewer rather than a discounted one. The Critic channel defaults to `xhigh` for the same reason — see [setup-critic-channel.md](skills/autosound-tuning/references/tooling/setup-critic-channel.md).
* **The Critic is the wrong place to save money.** A reviewer that never disagrees is not a cheap reviewer, it is an absent one, and it costs you the single check that catches the failure above.
* **A free Critic is still worth having.** Clipboard Mode into a free web chat is a genuine reviewer and far better than none — the warning here is about a *quiet, capable-sounding* downgrade, not about being on a budget.

**The date is part of the claim.** Model names move fast, and an undated recommendation goes stale without anyone noticing. If you are reading this well after August 2026, check what the current equivalents are rather than trusting these names.

### Subscription Options, Quotas, & Budgets (As of July 2026)

> [!WARNING]
> **Prices, quotas, free-credit offers, and model names below are a snapshot (July 2026) and go stale fast.** Treat the dollar figures and limits as illustrative of the *shape* of the choice (cheap-solo vs. reliable-dual), not as current fact — always verify the live pricing on the Anthropic / Google Cloud pages before committing.

In car audio, enthusiasts easily spend hundreds or thousands of dollars on physical hardware (where a single premium sound dampening sheet or a high-quality RCA cable costs $20–$50). When it comes to tuning your system with this AI tool, you have three flexible financial paths depending on your budget, tolerance for rate limits, and preference for automation:

* **Option 1 (Recommended Baseline): Claude ($20/mo) + Free Gemini as Advisor/Critic**
  You pay $20 for a 1-month Claude Pro subscription (using Claude as the strict, highly structured, and systematic "driver" of the tuning process) and connect Gemini as the Critic/Advisor for free (via Clipboard Mode or standard free API keys from Google AI Studio). This is the shape of the [supported pair](#which-models-is-this-actually-supported-on-as-of-august-2026) — spend the subscription on Opus at `xhigh` rather than on more messages from a cheaper tier. 
  * **Pros:** Highly precise, 100% protection against mathematical errors, costs just $20. You simply cancel the subscription once your car is tuned.
  * **Cons:** The free-tier Gemini API can occasionally hit Rate Limits (RPM/TPM quotas) during rapid, back-to-back testing.

* **Option 2 (Budget Compromise): Gemini Solo ($10 deposit)**
  You set up a paid billing account on [Google Cloud Console Billing](https://console.cloud.google.com/billing) and deposit $10 (the minimum required deposit to activate paid API tiers, which unlocks $300 in free credits for new accounts). You then run Gemini "solo" as your main tuner. 
  * **Pros:** Extremely cost-efficient ($10). **Indeed, having Gemini in the driver's seat yields the most amazing acoustic insights and non-standard tuning solutions.**
  * **Cons:** Due to the risk of "memory drift" under heavy contexts, you will need to manually double-check any variables or parameters the AI references (for example, when it suggests changing a crossover frequency from 200 Hz to 250 Hz when you actually have 230 Hz set, or no filter at all) and start every new tuning phase with a clean session using the `/clear + resume` command. This is also solo drive: one model proposing and approving its own work, with no second opinion to catch the failure described [just above](#which-models-is-this-actually-supported-on-as-of-august-2026).

* **Option 3 (Professional & Seamless): Both Paid (Claude Pro $20 + Paid Gemini Cloud API)**
  You keep a paid Claude Pro subscription ($20) for the main structured "driver" agent and use a funded [Google Cloud Console Billing](https://console.cloud.google.com/billing) account for the Gemini API Critic/Advisor.
  * **Pros:** This is the absolute peak of the dual-AI review loop. It eliminates all rate limits, prevents "API quota exhausted" errors, and allows you to tune continuously without pauses. This is highly recommended for professionals, people tuning multiple cars, or those running deep, back-to-back testing sessions.
  * **Cons:** Costs $20 plus pay-as-you-go API usage (which typically amounts to just a few cents or dollars per session drawn from your Google Cloud deposit).

### Why a full session uses fewer tokens than you'd expect

A real full in-car session (bass shaping, HF imaging, and a first-pass rear-fill — with measured verification of every step, on the most capable Claude model) consumed noticeably less quota than casual chat use would suggest. That's not luck; it's what the skill's "token-smart" design does, and it's worth knowing so you can keep it that way:

1. **Raw measurement data never enters the chat.** A REW sweep is thousands of data points, but they live inside local Python scripts; only digests come back to the conversation ("zone median +5.3 dB", a five-row joint table). Analysis costs tokens proportional to the *conclusion*, not to the *data*. This is the single biggest factor — and the main economic difference from the copy-paste manual method, where curves have to be described in text both ways.
2. **State lives on disk, not in the context.** The DSP ledger and changelog are re-read in slices when needed; the AI never re-narrates the project history to itself turn after turn. Session summaries are appended to files, not repeated in chat.
3. **The phase sliding window.** Only the active phase's reference doc (plus its neighbor) is loaded — never the whole knowledge corpus.
4. **Round-based review cadence.** One Critic call per round on the whole batch (not per-parameter), escalating to two passes only at phase gates — a handful of compact review packages per session instead of dozens.
5. **The Arbiter matters too.** Precise listening verdicts, measuring proactively, and a screenshot instead of a description save whole clarification round-trips — the cheapest tokens are the ones never spent.

Practical takeaway: a structured tuning session on a strong model is dominated by *decisions*, not *chatter* — so the strong model is affordable exactly where it counts. If your sessions feel token-hungry, check you're running with the local scripts (not the manual copy-paste path) and resuming from disk state (`/clear` + resume) rather than carrying one endless conversation.

---

## First-Time Setup (macOS & Windows)

To get started, you will need a laptop, a calibrated microphone setup, and a DSP.

> [!IMPORTANT]
> **Subscription:** You will need a paid **Claude Pro or Max** subscription because Claude Code (the CLI agent) requires access that isn't available on the free tier. ChatGPT Plus plans cannot be transferred.

#### The installer does the setup

One line installs Claude Code, Python, the tuning method, the desktop app, Google's `agy` for the Gemini reviewer and `omp` (which is what lets the app offer models other than Claude), on a clean machine. It shows what is already there, lists everything it will download, asks once, then runs on its own; the sign-ins come at the end, in your browser (Claude first — required; the reviewer and GitHub if you want them).

<details>
<summary><b>For macOS</b></summary>

1. **Open Terminal** (press **Cmd + Space**, type `Terminal`, and hit **Enter**).
2. **Paste this line:**
   ```bash
   curl -fsSL https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/main/install.sh | bash
   ```
3. On a Mac that has never been used for programming it asks for your **Mac password once**, right after the "Go ahead?" question, for Apple's Command Line Tools (git). Nothing else needs it. Then wait — ten to twenty minutes, nothing to press.
4. At the end it opens your browser for the Claude sign-in (a Pro or Max account), then offers the Gemini reviewer's sign-in and GitHub's — press **Enter** to do one now, **s** to leave it for later.

</details>

<details>
<summary><b>For Windows</b></summary>

1. **Open Windows PowerShell** (press **Win**, type `powershell`, and hit **Enter**).
2. **Paste this line:**
   ```powershell
   irm https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/main/install.ps1 | iex
   ```
3. If Git for Windows is not installed yet, Windows shows **one permission dialog** for it — click **Yes**. Nothing else needs administrator rights; everything else goes into your user profile. Then wait, five to fifteen minutes.
4. The sign-ins at the end are the same as on macOS. The reviewer's doctor script later runs in **Git Bash** (Start Menu → Git → Git Bash), which the installer brought.

To leave something out, run the one-liner in this form with the options you want: `& ([scriptblock]::Create((irm https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/main/install.ps1))) -Terminal` (no desktop app), `-NoReviewer`, `-NoGitHub`, `-NoOmp`. Prefer a double-click? [Download the repository ZIP](https://github.com/ayukhno/autosound-tuning-skill/archive/refs/heads/main.zip), *Extract All*, and double-click `install.cmd`.

</details>

Running the same line again **updates** everything. `--uninstall` (macOS, after `bash -s --`) / `-Uninstall` (Windows) removes what the installer put there and never a project folder.

---

#### Signing in, and starting

* **Claude:** the installer runs `claude auth login` for you at the end. If you skipped it, run that command in a terminal: a browser window opens, you sign in with your Claude account (Pro or Max) and click **Authorize**.
* **The reviewer (Gemini):** run `agy` once — see the next section — or press Enter when the installer offers it.
* **Start:** make one folder per car and open it either in the app (double-click **Autosound TCC** on your Desktop, *Browse…* to the folder, pick the models, *Open*) or in a terminal (`cd` into it, run `claude`), then say *"tune a new car from scratch"*.

> [!NOTE]
> **The 2.x plugin route** (`/plugin marketplace add ayukhno/autosound-tuning-skill` → `/plugin install autosound-tuning` → `/reload-plugins` inside Claude Code) still works and still gives you the 2.x line. The installer above gives you 3.x. One skill per machine — see the README's *Other ways in* for switching.

## Setting up the Gemini/Antigravity Critic (Standalone Setup)

The dual-agent **Generator ↔ Gemini (Critic)** loop is the strongest setup because it completely eliminates single-model bias. The critic runs in the background via lightweight scripts (`scripts/gemini_critic.sh`), so you don't have to manage a second AI window manually.

This standalone setup is highly recommended, even if you are not using Claude Code (for example, if you prefer a manual workflow or use other tools like Cursor, ChatGPT, or VS Code).

### macOS & Windows Setup (using Antigravity CLI - Recommended)

Google's official **Antigravity CLI (`agy`)** is the recommended default method because it uses a free, browser-based OAuth login and does not require creating or managing any API keys.

#### 1. Install the CLI:

**The installer from [First-Time Setup](#first-time-setup-macos--windows) already did this** unless you passed `--no-reviewer` / `-NoReviewer`. By hand, it is Google's own installer — no Homebrew, no package manager, no administrator rights; it puts `agy` in your user profile and clears macOS's quarantine flag itself:

* **For macOS:**
  ```bash
  curl -fsSL https://antigravity.google/cli/install.sh | bash
  ```
* **For Windows (PowerShell):**
  ```powershell
  irm https://antigravity.google/cli/install.ps1 | iex
  ```

Either way, open a **new** terminal window afterwards so it is on your PATH.

#### 2. Perform a one-time login:
In your standard terminal (Terminal.app on Mac, or PowerShell on Windows), simply run:
```bash
agy
```
* A browser window will open automatically. Sign in with the Google account that has Antigravity access.
* Once authorized, return to your terminal and type `/quit` to close the interactive session.

#### 3. Verify the installation:
Run this command to test the background channel:
```bash
agy -p "Hello, world!"
```

---

### Fallback: Direct API Setup (No CLI or Node.js required!)

If you are running **Linux**, if the Antigravity CLI is not available on your system, or if your weekly Antigravity free quota is exhausted, you can call Google's Gemini API directly using a free API key without installing Node.js, npm, or any external command-line utilities:

1. **Get a free API key** (no credit card required) at **[aistudio.google.com/apikey](https://aistudio.google.com/apikey)**.
2. **Add it to your config:** Create a file named `.critic-env` inside your project's `rew_analitic/` directory (or in CWD) and add your key:
   ```env
   GEMINI_API_KEY=AIzaSy...your_actual_key...
   ```
3. That's it! The Python script (`autosound_ai.py`) will automatically detect the key and make direct, lightweight HTTPS API calls to Gemini (using the robust and active `gemini-2.5-flash` model), bypassing any need for local CLI tools or npm shims.

> [!TIP]
> **Do I have to set this up?**
> No. If no local Gemini CLI or API key is found, the tuning skill will seamlessly fall back to **Autopilot self-loop** (spawning an isolated subagent inside Claude Code) or **Clipboard Mode** (allowing you to copy-paste proposals into any web-based AI of your choice, like ChatGPT or Gemini web).

---


## Do you have a version running on Google AI Studio?

**Yes.** We shipped a beta built specifically for this: a set of stateless prompt templates you run entirely inside **[Google AI Studio](https://aistudio.google.com/)** (or any web chat) with free Gemini, no local install and no API key required.

**[manual_step-by-step branch](https://github.com/ayukhno/autosound-tuning-skill/tree/manual_step-by-step)**

Each tuning step runs in a fresh chat with a short copy-paste prompt plus your REW exports. The passport file (your car's settings) gets regenerated in full at each step and saved as a new version, so nothing gets lost between steps the way long chat sessions tend to drift.

Being honest about where it stands: it works, but it's a step below the full local setup described above. There's no REW API pulling numbers automatically, no persistent state between messages, and no real back-and-forth review loop. Treat it as the fastest way to try the method for free, before deciding whether the full local setup is worth the time and the small subscription cost.

Still labeled experimental (it's new), and feedback from real tuning sessions is welcome.

---

## Can I ask Gemini to install and run the skill itself, without Claude Code?

**Yes, as a manual bootstrap, not a formal install.** There is no plugin system for Gemini the way Claude Code has one. But since the skill is plain Markdown and Python, nothing Claude-specific, you can point an agentic Gemini session (Antigravity CLI, or any Gemini setup with file and shell access) at the repo and ask it directly:

> Clone https://github.com/ayukhno/autosound-tuning-skill, read `skills/autosound-tuning/SKILL.md`, and follow that method as your operating instructions for this session.

One real caveat: Claude Code's own Skill system loads only the active phase on demand (see `SKILL.md`'s "Phase Sliding Window"), which keeps its context focused over a long session. A Gemini session that reads everything at once, instead of pulling files in on demand, may not hold that same discipline over a long session, on top of Gemini's already-documented tendency to drift on long sessions (see above).

The fully stateless, no-install alternative is the [manual_step-by-step](https://github.com/ayukhno/autosound-tuning-skill/tree/manual_step-by-step) pipeline described just above.

---


## Measuring Phase & Time Alignment: UMIK-1 vs. XLR Microphones

There is a major difference in how USB and XLR microphones handle time-critical phase measurements:

* **XLR Microphones (Behringer ECM8000, Beyerdynamic MM1, etc.):** These plug into an analog audio interface (like the Focusrite Scarlett 2i2). This setup is ideal for phase measurements because it allows a **physical loopback cable** (routing a channel output back into an input) to establish a sample-accurate timing reference.
* **UMIK-1 / UMIK-2:** These are USB microphones that plug directly into your laptop, bypassing the audio interface. Because there is no physical loopback path, you cannot use a hardware timing reference.

#### Can I measure phase with a UMIK-1?
**Yes.** You can still get highly accurate phase and time-delay measurements with a USB microphone by using REW's **Acoustic Timing Reference**. Instead of a loopback cable, REW will play a short high-frequency "chirp" from a designated reference speaker (usually a tweeter) before each measurement sweep to calculate the timing offset.

For a complete step-by-step video guide on how to configure REW for accurate phase measurements with a USB microphone, watch this excellent tutorial by RAW-Cat:
[RAW-Cat: Measuring Speaker Phase in REW](https://www.youtube.com/watch?v=El-kwZ5_nnU)

> [!WARNING]
> **CRITICAL RULE: Take all sweeps consecutively in one run!**
> Whether you are using a physical loopback (XLR) or an Acoustic Timing Reference (USB), **always measure all speakers consecutively in a single session.** Do not measure one speaker, take a 15-minute break (or turn on the AC/heater), and then measure the next one.
> * **Temperature Drift:** The speed of sound depends heavily on cabin air temperature. A shift of just 5°C alters the speed of sound enough to shift calculated arrival times by nearly 0.08 ms. While this is negligible for low-frequency bass/subwoofer alignment, it is completely fatal for midranges and tweeters (MF/HF) where wave periods are extremely short, easily destroying your crossover phase alignment and stage focus.
> * **Clock Drift:** If you are using a USB microphone (like the UMIK), the microphone and your output sound card run on separate hardware clocks. Because they are unsynchronized, their sample rates slowly drift over time. Waiting between measurements introduces artificial time offsets that do not physically exist.
> * **Rule of thumb:** If you adjust the microphone, change the cabin temperature (e.g., turn on/off AC), or pause the session for more than a few minutes, **re-measure all channels again** to guarantee your timing baseline remains 100% consistent.

---

## Target curves

#### Can I build my own target curve?

**Yes — and you often should.** A target ("house") curve is not a fixed standard; it's a
*per-project starting hypothesis* that you finalize by ear after the Phase-0 baseline. There is
no single "correct" curve — each car, install, and taste ends up with its own.

Two practical ways to build one:

**1. Ask the skill to design it.** Describe your taste and the skill will propose a shape, run it
through the Generator ↔ Critic ↔ Arbiter loop, and export it for REW/your DSP. The more concretely
you describe the *character* you want, the better the result. Useful things to tell it:
- Your genres and how you listen (low volume vs. loud, long drives).
- The direction vs. a reference: e.g. *"start from ResoNix Accurate but +2 dB more sub-bass and calmer highs"*, or *"like SQ-Comp-Ref but with a slightly deeper presence dip for more laid-back vocals"*.
- Any complaints about the current sound in the frequency-character language (*boomy, honky, thin, sibilant, no air*…).

Example prompts:
> *"Build me a custom target curve: warm, punchy bass for rock, vocals slightly forward, gentle highs — start from Half Whitledge and show me the shape."*
>
> *"Blend Audiofrog and Harman into one target with Audiofrog's timbre but a bit more deep bass, then compare it against both."*

The skill writes a 2-column `freq  dB` file (log-spaced, 20 Hz–20 kHz) into the project's
`rew_analitic/target-curves/<name>/`, and `rew_tool` then uses it as the house curve when it
designs EQ filters. You still confirm the final shape by ear with the measured baseline in hand.

> *Reality check: the AI will draw whatever curve you ask for, but your speakers have to physically support it — make sure your midbass and subwoofer have the power and excursion headroom before committing to an aggressive low-end boost.*

**2. Draw it yourself in the Nono Tuning Tool** ([nonotuningtool.com](https://nonotuningtool.com) →
*Custom Target Curve*), then export the `.txt` and drop it into the project's `curves/` folder or
onto the visualizer.

**Compare and sanity-check it** against the well-known reference curves — and see what each hump or
dip means for your instruments — in the interactive comparison tool:
**[open the curve visualizer online](https://ayukhno.github.io/autosound-tuning-skill/_curve-visualizer.html)**
(works offline too; drag your `.txt` in, compare it side by side against SQ-Comp-Ref / ResoNix /
Audiofrog / Harman / Jazzi / Whitledge, and right-click any point for a frequency-character guide).
