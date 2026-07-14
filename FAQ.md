# FAQ

Real questions people asked while trying to set this up, answered once here instead of over and over in comments. English only for now — worth translating once there's enough on this page to justify it.

Have a question that isn't here? Open a [discussion or issue](../../issues) and we'll add it.

## Table of Contents

- [Philosophy & Structure: Why AI?](#philosophy--structure-why-ai)
  - [Our Mission & Vision](#our-mission--vision)
  - [Why We Need Specialized AI & Local State](#why-we-need-specialized-ai--local-state)
  - [The 5-Step Tuning Journey](#the-5-step-tuning-journey)
  - [Subscription Options, Quotas, & Budgets (As of July 2026)](#subscription-options-quotas--budgets-as-of-july-2026)
- [First-Time Setup (Claude Code)](#first-time-setup-windows-claude-code--antigravity)
  - [Quick Installation (macOS & Windows)](#quick-installation-claude-code)
  - [Authentication & Plugin Setup](#authentication--plugin-setup-cross-platform)
- [Setting up the Gemini/Antigravity Critic (Standalone)](#setting-up-the-geminiantigravity-critic-standalone-setup)
  - [macOS & Windows Setup (Antigravity CLI - Recommended)](#macos--windows-setup-using-antigravity-cli---recommended)
  - [Fallback: Direct API Setup (No CLI/Node.js)](#fallback-direct-api-setup-no-cli-or-nodejs-required)
  - [Do you have a version running on Google AI Studio?](#do-you-have-a-version-running-on-google-ai-studio)
  - [Can I ask Gemini to install and run the skill itself?](#can-i-ask-gemini-to-install-and-run-the-skill-itself-without-claude-code)
- [Measuring Phase & Time Alignment: UMIK-1 vs. XLR](#measuring-phase--time-alignment-umik-1-vs-xlr-microphones)
  - [Can I measure phase with a UMIK-1?](#can-i-measure-phase-with-a-umik-1)

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

### Subscription Options, Quotas, & Budgets (As of July 2026)

> [!WARNING]
> **Prices, quotas, free-credit offers, and model names below are a snapshot (July 2026) and go stale fast.** Treat the dollar figures and limits as illustrative of the *shape* of the choice (cheap-solo vs. reliable-dual), not as current fact — always verify the live pricing on the Anthropic / Google Cloud pages before committing.

In car audio, enthusiasts easily spend hundreds or thousands of dollars on physical hardware (where a single premium sound dampening sheet or a high-quality RCA cable costs $20–$50). When it comes to tuning your system with this AI tool, you have three flexible financial paths depending on your budget, tolerance for rate limits, and preference for automation:

* **Option 1 (Recommended Baseline): Claude ($20/mo) + Free Gemini as Advisor/Critic**
  You pay $20 for a 1-month Claude Pro subscription (using Claude as the strict, highly structured, and systematic "driver" of the tuning process) and connect Gemini as the Critic/Advisor for free (via Clipboard Mode or standard free API keys from Google AI Studio). 
  * **Pros:** Highly precise, 100% protection against mathematical errors, costs just $20. You simply cancel the subscription once your car is tuned.
  * **Cons:** The free-tier Gemini API can occasionally hit Rate Limits (RPM/TPM quotas) during rapid, back-to-back testing.

* **Option 2 (Budget Compromise): Gemini Solo ($10 deposit)**
  You set up a paid billing account on [Google Cloud Console Billing](https://console.cloud.google.com/billing) and deposit $10 (the minimum required deposit to activate paid API tiers, which unlocks $300 in free credits for new accounts). You then run Gemini "solo" as your main tuner. 
  * **Pros:** Extremely cost-efficient ($10). **Indeed, having Gemini in the driver's seat yields the most amazing acoustic insights and non-standard tuning solutions.**
  * **Cons:** Due to the risk of "memory drift" under heavy contexts, you will need to manually double-check any variables or parameters the AI references (for example, when it suggests changing a crossover frequency from 200 Hz to 250 Hz when you actually have 230 Hz set, or no filter at all) and start every new tuning phase with a clean session using the `/clear + resume` command.

* **Option 3 (Professional & Seamless): Both Paid (Claude Pro $20 + Paid Gemini Cloud API)**
  You keep a paid Claude Pro subscription ($20) for the main structured "driver" agent and use a funded [Google Cloud Console Billing](https://console.cloud.google.com/billing) account for the Gemini API Critic/Advisor.
  * **Pros:** This is the absolute peak of the dual-AI review loop. It eliminates all rate limits, prevents "API quota exhausted" errors, and allows you to tune continuously without pauses. This is highly recommended for professionals, people tuning multiple cars, or those running deep, back-to-back testing sessions.
  * **Cons:** Costs $20 plus pay-as-you-go API usage (which typically amounts to just a few cents or dollars per session drawn from your Google Cloud deposit).

---

## First-Time Setup (Windows, Claude Code & Antigravity)

To get started, you will need a laptop, a calibrated microphone setup, and a DSP.

> [!IMPORTANT]
> **Subscription:** You will need a paid **Claude Pro** subscription ($20/mo) because Claude Code (the CLI agent) requires API access that isn't available on the free tier. ChatGPT Plus plans cannot be transferred.

#### Quick Installation (Claude Code)

Choose the instructions for your operating system:

<details>
<summary><b>For macOS</b></summary>

1. **Open Terminal** (press **Cmd + Space**, type `Terminal`, and hit **Enter**).
2. **Install Claude Code** by running this command:
   ```bash
   curl -fsSL https://claude.ai/install.sh | sh
   ```
3. **Verify Git (Required for plugins)**. macOS usually comes with Git pre-installed. Verify it by running:
   ```bash
   git --version
   ```
   *(If prompted to install Xcode Command Line Tools, click "Install" to let macOS set up Git automatically).*
4. **Create a project folder and launch Claude:**
   ```bash
   mkdir car-audio-tuning && cd car-audio-tuning && claude
   ```

</details>

<details>
<summary><b>For Windows</b></summary>

1. **Open Windows PowerShell** (press **Win + R**, type `powershell`, and hit **Enter**). If you are already in a standard Command Prompt (CMD), type `powershell` first to switch to the PowerShell environment.
2. **Install Claude Code** by running this command:
   ```powershell
   irm https://claude.ai/install.ps1 | iex
   ```
3. **Add Claude to PATH (Required for Windows)**. If PowerShell says `claude` is not recognized, run these two short commands in PowerShell. We split them so they are short, easy to copy-paste without terminal formatting/line-wrap issues, and they work instantly without restarting your window:
   * **Step A** (Enables it for the current window instantly):
     ```powershell
     $env:Path += ";$HOME\.local\bin"
     ```
   * **Step B** (Saves it permanently for future sessions and reboots):
     ```powershell
     [Environment]::SetEnvironmentVariable("Path", $env:Path, "User")
     ```
4. **Verify Git (Required for plugins)**. Run this command in PowerShell to make sure Git is installed and recognized:
   ```powershell
   git --version
   ```
   * **If it is NOT recognized** (or you don't have Git installed), run this command in PowerShell to install it instantly using the built-in Windows Package Manager (`winget`):
     ```powershell
     winget install Git.Git --silent --accept-source-agreements --accept-package-agreements
     ```
     *Once installation completes, update your path in the active window by running:*
     ```powershell
     $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
     ```
   * **If Git is installed but you see an "unsafe location/directory" error** when trying to install plugins later, run this command in PowerShell to trust your local directories:
     ```powershell
     git config --global --add safe.directory *
     ```
5. **Install Python (Required for Windows scripts):**
   Windows does not come with Python pre-installed. Run this command in PowerShell to install it instantly:
   ```powershell
   winget install Python.Python.3.11
   ```
   *Once installation completes, completely restart your PowerShell window or editor to apply the new PATH changes.*
6. **Create a project folder and launch Claude:**
   Run these commands in PowerShell:
   ```powershell
   mkdir car-audio-tuning; cd car-audio-tuning; claude
   ```

</details>

---

#### Authentication & Plugin Setup (Cross-Platform)

Once you run the `claude` command in your terminal:

* **Select login method:** When prompted, select **`1. Claude account with subscription · Pro, Max, Team, or Enterprise`**.
* **Authenticate:** A browser window will open automatically. Log in with your Claude credentials, **copy the temporary authorization code** from the website, and paste it back into your terminal to complete the login. *(Note: You must have already created an account and purchased at least a **Claude Pro** subscription on [claude.ai](https://claude.ai) beforehand).*
* **Install the tuning skill** by running these commands **one by one** inside your active Claude Code session (do not copy and paste them together):
  ```
  /plugin marketplace add ayukhno/autosound-tuning-skill
  ```
  ```
  /plugin install autosound-tuning
  ```
  ```
  /reload-plugins
  ```
* Start the session by typing this inside Claude Code: *"tune a new car from scratch."*

## Setting up the Gemini/Antigravity Critic (Standalone Setup)

The dual-agent **Generator ↔ Gemini (Critic)** loop is the strongest setup because it completely eliminates single-model bias. The critic runs in the background via lightweight scripts (`scripts/gemini_critic.sh`), so you don't have to manage a second AI window manually.

This standalone setup is highly recommended, even if you are not using Claude Code (for example, if you prefer a manual workflow or use other tools like Cursor, ChatGPT, or VS Code).

### macOS & Windows Setup (using Antigravity CLI - Recommended)

Google's official **Antigravity CLI (`agy`)** is the recommended default method because it uses a free, browser-based OAuth login and does not require creating or managing any API keys.

#### 1. Install the CLI:

* **For macOS:** Install via Homebrew:
  ```bash
  brew install --cask antigravity-cli
  ```
  *Bypass Gatekeeper Security (Required):* Run this command in Terminal to trust the utility and prevent *"cannot be opened because developer cannot be verified"* errors:
  ```bash
  xattr -dr com.apple.quarantine "$(command -v agy)"
  ```
* **For Windows (PowerShell):** Run this command in Windows PowerShell:
  ```powershell
  irm https://antigravity.google/cli/install.ps1 | iex
  ```
  *Once installation completes, update your path in the active window by running:*
  ```powershell
  $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
  ```
  *(Or simply close your current PowerShell window and open a new one to apply the changes).*

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
