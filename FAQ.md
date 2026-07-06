# FAQ

Real questions people asked while trying to set this up, answered once here instead of over and over in comments. English only for now — worth translating once there's enough on this page to justify it.

Have a question that isn't here? Open a [discussion or issue](../../issues) and we'll add it.

## Table of Contents

- [First-Time Setup (Claude Code)](#first-time-setup-windows-claude-code--antigravity)
  - [1. Quick Installation (macOS & Windows)](#1-quick-installation-claude-code)
  - [2. Authentication & Plugin Setup](#2-authentication--plugin-setup-cross-platform)
- [Setting up the Gemini/Antigravity Critic (Standalone)](#setting-up-the-geminiantigravity-critic-standalone-setup)
  - [macOS & Windows Setup (Antigravity CLI - Recommended)](#macos--windows-setup-using-antigravity-cli---recommended)
  - [Fallback: Direct API Setup (No CLI/Node.js)](#fallback-direct-api-setup-no-cli-or-nodejs-required)
  - [Do you have a version running on Google AI Studio?](#do-you-have-a-version-running-on-google-ai-studio)
- [Measuring Phase & Time Alignment: UMIK-1 vs. XLR](#measuring-phase--time-alignment-umik-1-vs-xlr-microphones)
  - [Can I measure phase with a UMIK-1?](#can-i-measure-phase-with-a-umik-1)

---

## First-Time Setup (Windows, Claude Code & Antigravity)

To get started, you will need a laptop, a calibrated microphone setup, and a DSP.

> [!IMPORTANT]
> **Subscription:** You will need a paid **Claude Pro** subscription ($20/mo) because Claude Code (the CLI agent) requires API access that isn't available on the free tier. ChatGPT Plus plans cannot be transferred.

#### 1. Quick Installation (Claude Code)

Choose the instructions for your operating system:

<details>
<summary><b>🍎 For macOS</b></summary>

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
<summary><b>🪟 For Windows</b></summary>

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

#### 2. Authentication & Plugin Setup (Cross-Platform)

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

* **🍎 For macOS:** Install via Homebrew:
  ```bash
  brew install --cask antigravity-cli
  ```
  *Bypass Gatekeeper Security (Required):* Run this command in Terminal to trust the utility and prevent *"cannot be opened because developer cannot be verified"* errors:
  ```bash
  xattr -dr com.apple.quarantine "$(command -v agy)"
  ```
* **🪟 For Windows (PowerShell):** Run this command in Windows PowerShell:
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

**Yes, absolutely!** You can run the entire Critic/Advisor workflow directly inside **[Google AI Studio](https://aistudio.google.com/)** completely for free. 

This is a fantastic alternative if you prefer a beautiful, visual, browser-based workspace, are on an iPad, mobile device, or tablet, do not want to install Python/Git locally, or want to completely bypass command-line quotas.

> [!NOTE]
> **Can I run the main Generator process in AI Studio too?**
> Technically yes, but it is highly impractical. The main Generator needs access to your local files (to read REW `.mdat`/`.csv` measurements, save the current DSP state, and log tuning steps) and needs to execute local Python scripts (`rew_tool`) to calculate phase offsets. AI Studio has no access to your filesystem or local execution environment. Therefore, AI Studio is best kept strictly for the **Critic** role, while the main Generator runs locally.
> 
> **How does the Critic interact with my local session?**
> Since AI Studio is a standard cloud website, it cannot talk to your local terminal directly. Instead, it works via **Clipboard Mode**. When you run a critic check locally, the system compiles the full prompt (including your system state, contract, and the new proposal) and automatically copies it to your clipboard. You simply paste it into your Google AI Studio chat, let Gemini generate the critique, and copy the response back to your local agent.

### How to set up a permanent "Car Audio Critic" in Google AI Studio:

1. **Go to Google AI Studio:** Open **[aistudio.google.com](https://aistudio.google.com/)** in your browser and sign in with your Google account.
2. **Create a New Chat Prompt:** Click the **"Create new prompt"** button (+ icon) on the left-hand panel and select **"Chat prompt"**.
3. **Configure System Instructions (The Critic's Brain):**
   * On the right-hand configuration panel, find the **System Instructions** text area.
   * Copy and paste this system instructions block there:
     ```
     SYSTEM ROLE — YOU ARE THE CRITIC (Challenger) in a two-model car-audio tuning loop.
     Task: find acoustic risks and false assumptions in the Generator's PROPOSAL.
     The car / DSP / system state is in the AUTOSOUND CONTEXT block below; rely only on it.
     Rules:
       • DON'T praise. Don't agree by default.
       • Objections must be FALSIFIABLE (testable by ear/measurement), not "a vibe".
       • Think in cabin physics + psychoacoustics, not the math of ideal filters.
       • Remember: an all-pass is flat in FR — any FR change comes through source SUMMATION.
     Respond STRICTLY in the "Critic → Generator" format from Contract §4, in the language of the AUTOSOUND CONTEXT.
     ```
4. **Anchor your Car Context & Contract (Baseline Knowledge):**
   * Open your local project's `rew_analitic/autosound_context.md` (containing your Passat B8 configuration) and paste its entire text into the chat.
   * Open `rew_analitic/data-contract-template.md` (containing the data contract protocol) and paste its entire text into the chat.
   * Press **Enter** or click **"Run"** to let Gemini ingest your system configuration.
5. **Save the Workspace:**
   * Click **Save** in the top-right corner of the web interface.
   * Name your workspace something like *«Car Audio Critic — Passat B8»*.
   * This workspace is now permanently saved in your Google Drive. You can reopen it at any time from your AI Studio dashboard!
6. **Start Tuning:**
   * Whenever you or your agent have a crossover, delay, or EQ proposal, simply run the Critic call to trigger **Clipboard Mode**, copy the compiled package, paste it into your saved Google AI Studio chat, and hit Enter.
   * Gemini will immediately reply with a professional, grounded, and physically accurate critique!

---


## Measuring Phase & Time Alignment: UMIK-1 vs. XLR Microphones

There is a major difference in how USB and XLR microphones handle time-critical phase measurements:

* **XLR Microphones (Behringer ECM8000, Beyerdynamic MM1, etc.):** These plug into an analog audio interface (like the Focusrite Scarlett 2i2). This setup is ideal for phase measurements because it allows a **physical loopback cable** (routing a channel output back into an input) to establish a sample-accurate timing reference.
* **UMIK-1 / UMIK-2:** These are USB microphones that plug directly into your laptop, bypassing the audio interface. Because there is no physical loopback path, you cannot use a hardware timing reference.

#### Can I measure phase with a UMIK-1?
**Yes.** You can still get highly accurate phase and time-delay measurements with a USB microphone by using REW's **Acoustic Timing Reference**. Instead of a loopback cable, REW will play a short high-frequency "chirp" from a designated reference speaker (usually a tweeter) before each measurement sweep to calculate the timing offset.

For a complete step-by-step video guide on how to configure REW for accurate phase measurements with a USB microphone, watch this excellent tutorial by RAW-Cat:
👉 [RAW-Cat: Measuring Speaker Phase in REW](https://www.youtube.com/watch?v=El-kwZ5_nnU)

> [!WARNING]
> **CRITICAL RULE: Take all sweeps consecutively in one run!**
> Whether you are using a physical loopback (XLR) or an Acoustic Timing Reference (USB), **always measure all speakers consecutively in a single session.** Do not measure one speaker, take a 15-minute break (or turn on the AC/heater), and then measure the next one.
> * **Temperature Drift:** The speed of sound depends heavily on cabin air temperature. A shift of just 5°C alters the speed of sound enough to shift calculated arrival times by nearly 0.08 ms (~8 samples @ 96 kHz). 
  * *Why it matters for Mid/Highs (MF/HF):* At midrange/tweeter crossovers (e.g., 4000 Hz, where the wave period is just 0.25 ms), this tiny 0.08 ms shift represents an **$110^\circ$ phase shift**, which will completely destroy your crossover summation and stage focus.
  * *Why it is negligible for Bass (LF/Sub):* At subwoofer-to-midbass handoffs (e.g., 60 Hz, where the wave period is a massive 16.6 ms), an 0.08 ms shift is less than **$2^\circ$ of phase shift**—meaning temperature drift has virtually zero audible impact on low-frequency alignment.
> * **Clock Drift:** If you are using a USB microphone (like the UMIK), the microphone and your output sound card run on separate hardware clocks. Because they are unsynchronized, their sample rates slowly drift over time. Waiting between measurements introduces artificial time offsets that do not physically exist.
> * **Rule of thumb:** If you adjust the microphone, change the cabin temperature (e.g., turn on/off AC), or pause the session for more than a few minutes, **re-measure all channels again** to guarantee your timing baseline remains 100% consistent.
