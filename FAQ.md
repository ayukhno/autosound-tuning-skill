# FAQ

Real questions people asked while trying to set this up, answered once here instead of over and over in comments. English only for now — worth translating once there's enough on this page to justify it.

Have a question that isn't here? Open a [discussion or issue](../../issues) and we'll add it.

## Table of Contents

- [First-Time Setup (Claude Code)](#first-time-setup-windows-claude-code--antigravity)
  - [1. Quick Installation (macOS & Windows)](#1-quick-installation-claude-code)
  - [2. Authentication & Plugin Setup](#2-authentication--plugin-setup-cross-platform)
- [Setting up the Gemini/Antigravity Critic (Standalone)](#setting-up-the-geminiantigravity-critic-standalone-setup)
  - [macOS & Windows Setup (Antigravity CLI - Recommended)](#macos--windows-setup-using-antigravity-cli---recommended)
  - [Linux & Fallback Setup (Gemini CLI)](#linux--fallback-setup-using-gemini-cli--free-api-key)
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


## Measuring Phase & Time Alignment: UMIK-1 vs. XLR Microphones

There is a major difference in how USB and XLR microphones handle time-critical phase measurements:

* **XLR Microphones (Behringer ECM8000, Beyerdynamic MM1, etc.):** These plug into an analog audio interface (like the Focusrite Scarlett 2i2). This setup is ideal for phase measurements because it allows a **physical loopback cable** (routing a channel output back into an input) to establish a sample-accurate timing reference.
* **UMIK-1 / UMIK-2:** These are USB microphones that plug directly into your laptop, bypassing the audio interface. Because there is no physical loopback path, you cannot use a hardware timing reference.

#### Can I measure phase with a UMIK-1?
**Yes.** You can still get highly accurate phase and time-delay measurements with a USB microphone by using REW's **Acoustic Timing Reference**. Instead of a loopback cable, REW will play a short high-frequency "chirp" from a designated reference speaker (usually a tweeter) before each measurement sweep to calculate the timing offset.

For a complete step-by-step video guide on how to configure REW for accurate phase measurements with a USB microphone, watch this excellent tutorial by RAW-Cat:
👉 [RAW-Cat: Measuring Speaker Phase in REW](https://www.youtube.com/watch?v=El-kwZ5_nnU)
