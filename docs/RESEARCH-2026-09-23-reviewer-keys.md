# Research 2026-09-23: where the reviewer's key should live

Owner's complaint, verbatim in effect: a `GEMINI_API_KEY` exported from `~/.zshrc` "is not seen"
by the method repeatedly, keeping it there worries him as a security practice, and an earlier pass
at this "probably got it wrong." He wants one correct, safe way to **enter**, **store**, and **use**
the reviewer's key, that works without refusals — and the signed-in-CLI (subscription) route must
stay a first-class path, not a thing the key path displaces.

Scope: reading only, plus web research. One file written (this one). No code changed.

## The problem

**What he saw and why it happens, with sources:**

1. **A GUI-launched app never sees a shell profile's `export`.** TCC (PySide6, launched from
   Finder/Start menu) starts its child tuning session as a launchd-spawned process on macOS; macOS
   GUI apps get their environment from `launchd`, not from any shell's rc file — the mechanism that
   once let a shell-style file feed the GUI environment (`~/.MacOSX/environment.plist`) stopped
   being read starting with OS X 10.8 (Mountain Lion), and its short-lived replacements
   (`~/.launchd.conf`) were dropped again by 10.10 (Yosemite). Today the only way to hand `launchd`
   a variable is `launchctl setenv`, run once per login — an `export` in `~/.zshrc` never reaches
   that path at all. [Launchd — Wikipedia](https://en.wikipedia.org/wiki/Launchd) ·
   [A launchd Tutorial](https://www.launchd.info/) ·
   [Script to manually apply your shell PATH to macOS GUI apps](https://gist.github.com/riaf/cf662d965ebd1b8b47453dd79cdd5578)

2. **Even from a terminal, an edited profile does not reach an already-running session.** A
   process's environment is a snapshot taken at start; editing `~/.zshrc` after a Claude Code
   session (or any shell) started changes nothing already running — the method's own docs say
   this today (`setup-critic-channel.md:120-123`, quoted below). The Windows analogue is the same
   fact with a different mechanism: every Windows process gets a **copy** of its parent's
   environment block at creation, with no live link to the registry; a value set with `set` in one
   terminal never reaches sibling or later processes started from Explorer unless it is written to
   the registry **and** broadcast with `WM_SETTINGCHANGE` — which only `setx`/the System Properties
   dialog/`[Environment]::SetEnvironmentVariable(...,"User")` do; anything already running (or a
   terminal opened before the change) keeps its stale copy.
   [WM_SETTINGCHANGE message — Microsoft Learn](https://learn.microsoft.com/en-au/windows/win32/winmsg/wm-settingchange) ·
   [Windows Environment Variables — env.dev](https://env.dev/guides/windows-environment-variables)

3. **The security concern is real, not theoretical.** An exported variable is inherited by
   *every* child process the shell starts from then on — every package script, every agent, every
   `env`/`ps e` — and on Linux any process owned by the same user can read another's environment
   straight out of `/proc/<pid>/environ`. It also survives in shell history if typed inline, in
   dotfile backups and dotfiles-repo syncs, and in accidental commits of a profile file. Security
   guidance is consistent on this: don't put secrets in a shell profile.
   [Stop Putting API Keys in Your Shell Config — kakkoyun.me](https://kakkoyun.me/posts/stop-putting-api-keys-in-shell-config/) ·
   [Security implications of /proc/self/environ — Security StackExchange](http://library.eshikshya.org/kiwix/content/security.stackexchange.com_en_all_2023-05/questions/107373/security-implications-of-the-contents-of-proc-self-environ-in-lfi-attacks)

So: the owner is not imagining a bug. He is describing the correct, expected behaviour of two
operating systems' process models colliding with a habit (`export` in a shell profile) that this
method's own docs already argue against — but argue against only in prose, with nothing that
detects or fixes an existing export, and nothing that offers a safer way to enter a key that is as
easy as typing `export`.

## What the method does now

The current design (`skills/autosound-tuning/scripts/autosound_ai.py`) is already better than a
bare `export` — it just stops short of a real secret store, and has no entry command.

- **One canonical machine-wide file, outside the project**, resolved once
  (`autosound_ai.py:45-53`, `machine_config_path`):
  > "The per-machine critic config — the place a SECRET belongs, outside any project. The project
  > folder is the one the README tells you to back up to a private GitHub, so a key kept there is
  > one `git push` from leaving... The one door since the shell wrappers were retired (skill #41),
  > so the one place the path is resolved."
  `~/.config/autosound/critic-env` (or `$XDG_CONFIG_HOME`), `%APPDATA%\autosound\critic-env` on
  Windows.

- **Read order**, machine file first (`autosound_ai.py:104-112`, `load_env_file`):
  > "Read every config that exists, machine file FIRST, project files after it... Both are read
  > rather than the first one winning: the machine file carries the key, and a project may still
  > pin non-secret things."
  Candidates: `machine_config_path()`, `<PROJECT_MIRROR>/.critic-env`, `<CWD>/.critic-env`,
  `<CWD>/scripts/.critic-env`.

- **A project-local file that could leak the key is refused, not just warned about**
  (`autosound_ai.py:74-96`, `_refuse_if_git_would_take`): if a non-machine config carries an
  `*_API_KEY` line and git would ever pick it up (tracked, or not `.gitignore`d), the script exits
  2 with the fix printed, rather than reading it.

- **The key is read only from the process environment** at the point of use
  (`autosound_ai.py:335-340`, `api_key_for`): it loops `_PROVIDERS[provider]["env"]` (e.g.
  `GEMINI_API_KEY`) and returns `os.environ.get(var)` — the config-file loader's only trick is that
  it writes into `os.environ` itself before this runs, so "read the file" and "read the shell
  export" are indistinguishable to every consumer downstream.

- **A blank line in the file can deliberately suppress an inherited key**
  (`autosound_ai.py:343-357`, `suppressed_key`), so a machine that wants the CLI route even with a
  key sitting in the shell can force it — but this is a workaround for the shell-export problem,
  not a fix for it.

- **`doctor` is diagnosis only — it never writes anything.** `run_doctor`
  (`autosound_ai.py:1253` onward) prints which files were found, `env_origin(var)` (file path, or
  `"зі змінної середовища: її бачить кожна програма, запущена з цього сеансу"` when the value came
  from the shell), and the key's shape (`gemini_key_shape`) — but there is no command that moves a
  value from the shell into the file, and no command that writes a key into the file at all. The
  only way to "enter" a key today is to hand-edit a text file, per
  `.critic-env.example:1-16` and `setup-critic-channel.md:94-104` (§3):
  > "`mkdir -p ~/.config/autosound … cp scripts/.critic-env.example ~/.config/autosound/critic-env …
  > chmod 600 …` And do not `export GEMINI_API_KEY` from your shell profile."
  That is correct advice with no mechanism behind it — which is exactly the gap `export` fills by
  habit.

- **The installers only print a notice, once, during install** — they do not act.
  `install.sh:1342-1347`:
  > "hub #187: a key in the shell profile is not the reviewer's sign-in, and it sends every review
  > to the API, where agy's model names (…-high) do not exist. ... To keep the key for the reviewer,
  > put it in ~/.config/autosound/critic-env and take it out of your shell profile."
  `install.ps1:1355-1360` says the same for `%APPDATA%\autosound\critic-env`. Neither offers to do
  the move; both only fire once, at install time, and only see the *current process's* environment
  — a key exported after install, or in a profile not yet re-sourced, is invisible to this check
  too.

- **`.gitignore` protection is real but scoped to the project file, not the key's entry path**
  (`rew_tool/project_seed.py:252-262`, HUB-025): a fresh project gets a written `.gitignore`
  covering `.critic-env`, explicitly as a second line of defence — "a key belongs outside the
  project entirely... because `.gitignore` stops none of `git add -f`, a copied folder, or a
  backup that is not git at all." This says nothing about how the key gets into
  `~/.config/autosound/critic-env` in the first place, which is still manual.

- **Hub #187 (2026-09-19/20) already chased one instance of exactly this owner complaint** and
  fixed the *routing* half (an `agy`-only model now goes to the CLI even with a key exported; the
  installer's "signs of being set up" check no longer treats a bare exported key as "done"). It
  did not add a way to store a key safely or to migrate one out of `~/.zshrc` — which is why the
  same complaint has resurfaced now.

## How it should be done

### macOS — Keychain

`security(1)` is already on every Mac, needs no install, and both directions work from a script:

```bash
security add-generic-password -a "$USER" -s autosound-reviewer-google -w "$KEY" -U   # store (update if exists)
security find-generic-password -a "$USER" -s autosound-reviewer-google -w            # read back
```
[Storing generic passwords in macOS' keychain — jpmens.net](https://jpmens.net/2021/04/18/storing-passwords-in-macos-keychain/) ·
[Get Password from Keychain in Shell Scripts — scriptingosx.com](https://scriptingosx.com/2021/04/get-password-from-keychain-in-shell-scripts/) ·
[Working with credentials managed by Keychain Access — gist](https://gist.github.com/tamakiii/9c3eadc493597ed819b9ff96cbcf61d4)

Trade-off: the value is briefly an argv element to `security`, so it can appear in `ps` output for
the instant the command runs (not in shell history if entered via a prompt rather than typed
inline); reading with `-T <path>` at creation time can pre-authorize one interpreter path so
`find-generic-password` doesn't prompt, but this project runs "wherever python3 is," so the exact
interpreter path is not fixed — occasional keychain access prompts are a realistic residual cost.

### Windows — no single obvious winner; pick by what a script actually needs

- **`cmdkey`** writes a Credential Manager entry but **cannot read it back** — "the major drawback
  to using cmdkey is that it doesn't have the ability to recover the password... much more limited
  for scripting." Fine for a human to inspect in the Control Panel; useless as this script's own
  store. [Managing Secrets In Windows — grahamwatts.co.uk](https://grahamwatts.co.uk/windows-secrets/) ·
  [Storing Credentials Securely on Windows — Red Gate](https://www.red-gate.com/hub/product-learning/flyway/storing-credentials-securely-on-a-windows-based-flyway-installation/)
- **PowerShell `SecretManagement` + `SecretStore`** gives a real get/set API, but neither module
  ships with Windows — both need `Install-Module ... -Scope CurrentUser` first, plus a vault to
  initialize. [Use the SecretStore in automation — Microsoft Learn](https://learn.microsoft.com/en-us/powershell/utility-modules/secretmanagement/how-to/using-secrets-in-automation?view=ps-modules)
- **DPAPI directly** (`CryptProtectData`/`CryptUnprotectData` in `crypt32.dll`) needs **no install
  at all** — it's callable from pure-stdlib Python via `ctypes.windll.crypt32`, ties the ciphertext
  to the logged-in user exactly like Credential Manager does under the hood, and supports both
  directions from one script.
  [CryptProtectData — Microsoft Learn](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata) ·
  [CryptUnprotectData — Microsoft Learn](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptunprotectdata) ·
  [Use Windows DPAPI with Python — dev.to](https://dev.to/samklingdev/use-windows-data-protection-api-with-python-for-handling-credentials-5d4j)
  Trade-off: a DPAPI-encrypted file does not show up in the Credential Manager UI the way a
  `cmdkey`/`CredWrite` entry would — it's an encrypted file under the user's profile, not a listed
  "Windows Credential," so there's nothing to inspect in Control Panel. Given this script's
  "standard library only, runs wherever `python3` does" constraint, DPAPI is the one Windows option
  that needs nothing extra and both reads and writes — the right fit here, at the cost of that
  visibility.

### Cross-platform `keyring` (PyPI) — attractive, but a dependency this script doesn't have

`keyring.set_password`/`get_password` cover macOS Keychain and Windows Credential Locker out of the
box; Linux needs Secret Service (`secretstorage`, itself needing a running desktop D-Bus session)
or KWallet (`dbus-python`, which "does not always install correctly when using pip"). Headless/CI
machines have no backend at all: recent versions raise `NoKeyringError`("No recommended backend was
available"), and the documented escape is to force the degenerate
`PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring`.
[keyring — PyPI](https://pypi.org/project/keyring/) ·
[NoKeyringError on headless Linux — GitHub issue](https://github.com/Kordevance/kordevance-agent/issues/2)
This is the natural cross-platform answer *if* the script accepted a pip dependency — but
`autosound_ai.py`'s header states it deliberately "Працює без сторонніх залежностей (standard
library only)." Calling the OS's own tools (`security`, DPAPI via `ctypes`) gets the same security
property without breaking that constraint; `keyring` is worth reconsidering only if that
zero-dependency rule is ever relaxed.

### The 0600 file — right as the fallback, not as the front door

A permission-restricted config file is portable, needs nothing, and is already built
(`~/.config/autosound/critic-env`, mode 600). Its ceiling: any process running as the same OS user
can read it (no OS-level access control beyond file permissions — weaker than Keychain/DPAPI, which
are tied to the logging-in principal via the OS's own crypto), and it does nothing to stop a user
from *also* exporting the same variable elsewhere, which is the exact failure mode in hub #187.

### What comparable tools do

| Tool | Primary store | Fallback | Subscription **and** key? |
|---|---|---|---|
| `gh` (GitHub CLI) | OS keyring (macOS Keychain / Windows Credential Manager / Linux Secret Service) since Feb 2023 | `~/.config/gh/hosts.yml` plaintext, opt-in via `--insecure-storage` | Login only (OAuth/PAT) |
| Gemini CLI / Antigravity (`agy`) | **Plaintext JSON**, `~/.gemini/oauth_creds.json` — no keychain at all | — | **Yes** — OAuth login *or* `GEMINI_API_KEY` |
| Claude Code | macOS Keychain (service "Claude Code-credentials") | `~/.claude/.credentials.json`, mode 0600 (Linux, or when Keychain is locked/unreachable, e.g. over SSH) | **Yes** — subscription login *or* `ANTHROPIC_API_KEY` |
| OpenAI Codex CLI | Plaintext `~/.codex/auth.json` by default | Configurable to OS credential store via `cli_auth_credentials_store` | **Yes** — ChatGPT login *or* API key |
| AWS CLI | Plaintext `~/.aws/credentials` by default | `credential_process` lets a helper (e.g. `aws-vault`) source from the OS keychain at call time instead | SSO cached tokens are the closest analog to "subscription" |
| `llm` (Simon Willison) | `keys.json` under the OS app-config dir (e.g. `~/Library/Application Support/io.datasette.llm/`), `llm keys set <provider>` masked prompt | `chmod 600` recommended | Key-only |
| 1Password `op run` | Vault; injects into the **child process's env at call time only** — never written to disk | — | N/A (a secrets broker, not an AI CLI) |
| direnv | Per-directory `.envrc`, plaintext, requires explicit `direnv allow` | — | N/A — a workflow convenience, not a credential store |

Sources: [gh CLI keyring migration — GitHub issue #7757](https://github.com/cli/cli/issues/7757) ·
[Gemini CLI authentication — geminicli.com](https://geminicli.com/docs/get-started/authentication/) ·
[Claude Code plugin credentials — dev.to](https://dev.to/rsdouglas/claude-code-plugin-credentials-what-the-new-keychain-storage-does-and-doesnt-do-cnf) ·
[Skipping the lock — Silverfort](https://www.silverfort.com/blog/skipping-the-lock-a-claude-code-cli-weakness-lets-any-macos-process-read-stored-credentials/) ·
[Codex CLI authentication — developers.openai.com](https://developers.openai.com/codex/auth.md) ·
[AWS CLI credential_process + aws-vault — Andreas Bergström](https://andreasbergstrom.dev/posts/aws-cli-profiles-keychain-sso) ·
[llm setup — Datasette docs](https://llm.datasette.io/en/stable/setup.html) ·
[Load secrets into the environment — 1Password Developer](https://developer.1password.com/docs/cli/secrets-environment-variables)

The pattern across every tool that supports both routes (Gemini CLI, Claude Code, Codex): **the
subscription login is the default and the key is a documented alternative**, never the reverse —
and the two nearest precedents to this project's own constraints point opposite ways worth naming
plainly: Google's own CLI, under the same "must run everywhere, no extra install" pressure, settled
for a plaintext file; Anthropic's, under a similar pressure but a security-conscious userbase, put
the Keychain first and kept the plaintext file only as its documented fallback. Claude Code's
shape — Keychain first, 0600 file second — is the closer match for what a careful "does the user's
own subscription CLI" tool should do, and it is the one recommended below.

### How a GUI-started child process should receive the secret

Read it at the moment of the call, inject it only into that one subprocess's environment dict, and
never let the GUI app's own long-lived process hold it. `op run` is the clean example of the
principle: "the target program receives environment variables in memory... but the secret values
never need to live in a local file," scoped to the one child, for the length of that one run.
[1Password: load secrets into the environment](https://developer.1password.com/docs/cli/secrets-environment-variables)
`autosound_ai.py` already has the right shape for this: `child_env()` builds the *one* dict a
reviewer CLI subprocess receives (`autosound_ai.py:509-517`), stripped of nested-session markers —
the same function is the natural place to resolve the key from the keystore right before the
`subprocess.run(...)` call, rather than TCC exporting it into its own environment where every
process TCC ever starts would inherit it (the exact `~/.zshrc` problem, one process up).

## Proposal for the method

**Primary store:** the OS's own secret store — macOS Keychain via `security` (no dependency);
Windows via DPAPI (`ctypes` + `crypt32.dll`, no dependency). **Fallback**, used automatically when
the primary store is unavailable (headless SSH, a locked keychain, an unsupported OS): the existing
0600 `~/.config/autosound/critic-env` / `%APPDATA%\autosound\critic-env` file — this mirrors Claude
Code's own precedent exactly, and needs no new file format.

**Entry — one command, never a shell profile, never a chat:**
```
python3 scripts/autosound_ai.py key set google      # prompts with getpass (no echo, no argv, no history)
python3 scripts/autosound_ai.py key status          # what's set, where from, never the value
python3 scripts/autosound_ai.py key rm google
```
`key set` tries the keystore first; on failure (no Keychain access, DPAPI error) it falls back to
writing the 0600 file and says so. This is the missing piece today — `export` is not a rejected
alternative to something easier, it is currently the *only* thing as easy as typing one line.

**Read order in `api_key_for`, most specific first, each one visible in `doctor`'s `env_origin`:**
1. an explicit process environment variable (kept — a deliberate one-shell override still works,
   e.g. CI or `--via api` testing);
2. the machine keystore (Keychain / DPAPI file);
3. the machine config file (`critic-env`);
4. the project-local config file.
`suppressed_key`'s "a blank line wins" trick stays, since it's orthogonal to where the key itself
lives.

**`doctor` reports the keystore exactly as it reports files today** — found/not found, key shape,
one live check — and never prints the value, same as now.

**TCC's child sessions:** unchanged in shape — TCC still calls `autosound_ai.py`, which still
builds one subprocess environment per call (`child_env()`); the keystore read happens inside that
function, immediately before the call, not in TCC's own process.

**Migrating an existing `~/.zshrc` export — detected, offered, never silent:** `doctor` (and the
installers' existing signal-5 check) already knows when a key's value came from "the shell" rather
than a file (`env_origin`); add a text search of `~/.zshrc` / `~/.bash_profile` / `~/.profile`
(Windows: the User environment variable in the registry) for a literal `export VAR=`/`setx VAR`
line for that same variable. When both are true, print the exact file and line, and offer — with
an explicit y/n, never automatic — to copy the value into the keystore and comment out that one
line (leaving a `.bak`). This turns the installers' current one-shot, inert notice
(`install.sh:1342-1347`, `install.ps1:1355-1360`) into an actual, repeatable action available from
`doctor` at any time, not only at install.

**Installers:** keep the CLI login (`agy`/`claude`/`codex`) as the offered default; when a key is
detected in the environment, run the migrate offer above instead of only printing where it should
go.

**The subscription route stays first-class, unconditionally:** nothing above changes
`resolve_model()`/`detect_cli()`/hub #187's routing fix — a signed-in CLI is still tried whenever
the picked model is a CLI-only slug or no key is configured at all; the keystore only ever feeds
`api_key_for()`, which is consulted for an API-shaped model, a forced `--via api`, or when no CLI is
present. A user who only ever runs `agy`/`claude`/`codex` after logging in never needs to run
`key set` at all.

**Must NOT happen — unchanged, and worth stating outright:**
- a key in the project folder (already refused: `_refuse_if_git_would_take`, `autosound_ai.py:74-96`);
- a key typed into a review package or the clipboard-mode payload — the package format carries the
  car's data and the contract, never a credential;
- a key in a log — `AUTOSOUND_REVIEW_RAW_DIR` records the prompt sent and the reply received, never
  the header/argv the key travelled in;
- a key in argv where it can be avoided — the HTTP calls already send it as a header, not a URL
  parameter (`call_gemini_api`'s own PAS-004 comment, `autosound_ai.py` around the Gemini call); the
  new `key set` entry path uses `getpass` (stdin), not a command-line argument.

## Risks and open points

- **Keychain access prompts are not fully eliminable.** Pre-authorizing one interpreter path at
  creation time (`security ... -T <path>`) only works if that path is stable, and this script is
  meant to run under whatever `python3` a machine has (Homebrew, uv, pyenv, system) — expect an
  occasional macOS prompt the first time a *different* interpreter reads the entry.
- **The DPAPI file is invisible in the Windows Credential Manager UI.** A real `CredWrite`-backed
  entry would show there; an open point is whether that visibility is worth the extra
  `ctypes`/`advapi32` surface, or whether "not listed in Control Panel" is an acceptable trade for
  zero dependencies.
- **Linux is left with the file only.** `keyring`'s Linux backends need a desktop D-Bus session
  (Secret Service) or an extra native dependency (`dbus-python` for KWallet) — neither fits
  "standard library only," so a Linux dev machine keeps today's 0600-file behaviour; this is a
  deliberate scope cut, not an oversight, unless the zero-dependency rule is revisited.
- **The exact `key set/status/rm` verb and surface are a design choice for whoever implements
  this**, not fixed by this research; `doctor --fix` was considered as an alternative shape and is
  worth weighing against a dedicated `key` subcommand.
- **TCC's own settings screen reads/writes `critic-env` independently** (`core/critic_env.py`, per
  hub #187's comments) — if the primary store moves to the keystore, TCC's screen needs the same
  read/write logic (or to shell out to `autosound_ai.py key set/get`) so the two don't drift; this
  is a coordination point for the implementer, not resolved here.
