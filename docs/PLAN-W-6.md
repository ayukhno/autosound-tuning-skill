# W-6 · v3.1.0 — the plan

Collection opened 2026-10-02 (the Arbiter: «відкривай W-6») and closed the same day («збір закінчено»). Milestone
`W-6 · v3.1.0` (#6), ten issues #116–#125, `ok` on all ten (the Arbiter, 2026-10-02: «Усі 10»). **The wave's goal**:
when it ends, v3.1.0 is ready to ship (the Arbiter: «на кінці W-6 все повино бути готове для випуску релізу»). The
minor is cut with TCC v1.1.0 (hub #220); the catalog moves with the tag.

Branch `wave-2026-10-02`. Pool: `docs/TODO.md` S-093 (the wave), S-094 (the plugin route), S-095 (the documentation).

## Order

1. **#117** — agy through ADC, the code half. First: it brings the Critic and the Advisor back on this Mac, and the
   documentation goes through the Advisor (the Arbiter: «документацію робимо після того як запрацює Радник на новому
   конекті»).
2. **#116, #119, #122** — the small ones: the ledger join, the CLI route that never bills a key, the plugin folder.
3. **#120, #121** — the plugin route: the tools, the signature check.
4. **#118, #124, #125** — the installers' ADC half and the documentation, English then the translations.
5. **#123** — the catalog, at the tag.

**Needs the Arbiter:** a candidate `beta-v3.1.0-rc1` run on the Mac and the Windows VM — the installers, the plugin
route from the catalog, and agy's reviewer agent on Windows (a tool-less agent in a temporary folder, measured on the
Mac only).

## The tasks

### #117 — agy through ADC: the reviewer channel (hub #234 asks 1, 2, 3, 6, 7) — built

- **Ask 1.** `_NESTED_MARKERS` strips every `AGY_` name; `AGY_ADC_AUTH` is now an exception (`_NOT_MARKERS`,
  `_is_marker`) in `child_env` and `nested_session_marker`. The `GOOGLE_*` variables were never stripped.
- **Ask 2, the carrier: the machine's critic-env.** The method reads it itself (`load_env_file`), whatever started the
  run, so a TCC started from the Dock gets the switch; `~/.zshrc` works for shell runs. Checked live with a temporary
  critic-env (`XDG_CONFIG_HOME`) holding only the model and `AGY_ADC_AUTH=true`: ADC, channel works, automatic mode.
- **Ask 3.** `agy_sign_in` → `doctor`'s «Вхід agy» line: ADC (the file, gcloud's account and project from its own
  settings, where the switch came from), agy's account (the installers' four signals), or none with what to do. No
  credential file is opened.
- **Ask 6, the model under ADC: `gemini-3.8-flash-high`.** Under ADC agy lists Flash 3.6–3.8 in three tiers each, 3.5
  Flash, 3.1 Pro only at `low`, 3.1 Flash Lite and 3 Flash (`agy models`, 2026-10-02). The newest line at its top tier
  is the strongest offered; 3.1 Pro at low thinking is the old line held back. It answered every live check. The
  method keeps no default model (`resolve_model`): the name goes into the installers' and the docs' recommendation
  (#118, #124).
- **Ask 7, agy's persisted policies in headless runs.** agy's changelog: «headless (`-p` / `--print`) runs … now honor
  persisted `settings.json` policies, including `permissions`, file access, sandbox mode, auto-execution, and artifact
  review». On this Mac `toolPermission` is `always-proceed`, and a review prompt asking for `ls -d ~/dev` got the
  listing, with and without `--sandbox`. **Decided:** the reviewer does not depend on anyone's settings — each call runs
  `--agent autosound-reviewer` in a fresh temporary folder holding only that agent (`excludeDefaultComponents: true`,
  `tools: []`); the same prompt answered NO-TOOLS, and the doctor's live call through it answered. So the tip (#118)
  may describe Tool Permission for agy's own window freely, saying that the method's reviews are not affected.
- Selftests: the marker exception, the child's environment, the agent file, the four sign-in outcomes on a fake home.

### #116 — the DSP sheet joins a `w_L` channel to its `w-L` row (hub #233) — built

- **Ask 1.** `state.py` `project_channels` adds each key's `naming.canonical_code` form where the name as written is
  not already a key, and `render_state`'s `slot_of` falls back to the row key's canonical form. `naming` is loaded by
  path (`_canonical_code`): `state.py` is imported by consumers that put neither `state/` nor its parent on `sys.path`.
- **Ask 2, an `sw-f` row from v3.0.65: named, not read back.** `contract.py`'s ledger cross-check already lists it as
  foreign; it now says it is v3.0.65's spelling of the channel `sw_f` and that which row holds the live values is the
  Arbiter's call. Reading it back on its own could merge two rows of one channel.
- Selftests: `state.py` (both directions on the sheet; `sw_f` stays apart), `contract.py` (the sentence, only for that
  case).

### #119 — a CLI route never bills an API key (hub #236) — built

- **Ask 1.** `main` reads `AUTOSOUND_CRITIC_VIA` when no `--via` is given (validated against `VIA_ROUTES`, an unknown
  value refused, the route said on stderr); `doctor` takes the same `via` and, on `cli`/`clipboard`, checks the CLI.
- **Ask 2.** `child_env` drops `VENDOR_KEYS` for `SUBSCRIPTION_CLIS` (agy, `claude`, `codex`), so a key from the
  environment, a critic-env line or the store reaches none of them. The `gemini` CLI keeps its key (a key is how it
  signs in); omp keeps its environment (a door of its own, hub #216). `doctor` says the CLI runs without the keys.
- `setup-critic-channel.md` names the variable, the stripped keys and the ADC carrier (#117).
- Selftests: no vendor key in any subscription CLI's environment, omp untouched; the route variable's clipboard run,
  `--via` beating it, a bogus value refused.
- **Tell tcc** with the tag: the variable's name is `AUTOSOUND_CRITIC_VIA`.

### #122 — `deployment.py` knows the plugin install folder — built

- `plugin_installs(home)` reads `~/.claude/plugins/installed_plugins.json` for `autosound-tuning@<marketplace>`
  (install path, `gitCommitSha`, version, scope, project). `describe(path, plugins)` takes the recorded commit for a
  copy with no `.git` whose root is a recorded install; `candidates` adds every user-scope install and a project-scope
  one for that project as origin `plugin`. Verdicts unchanged: same sha agrees, another splits, no sha is unknown.
- Selftests on a fake home: the registry read, the plugin's identity, agreement, split, unknown, another project's.

### #121 — the plugin route's signature check — built

- **What Claude Code guarantees** (its plugin docs, 2026-10-02): a `url` source with `ref` and `sha` is checked out at
  the `sha` — git's content addressing holds the copy to the pin — and no signature is verified; `sha256` exists only
  for `archive` sources. So the pin is as trustworthy as whoever can edit the catalog.
- **Decided: the copy verifies itself against the signed tag.** `upkeep.py verify-copy --root <plugin root>`: the tag
  `v<plugin.json version>` into a throwaway bare repository, `verify_tag` with the constant key (the installers'),
  then every blob of the tag's tree against the copy (`blob_id`, computed in Python; CRLF accepted as the same file;
  `.in_use`, `.orphaned_at`, `.DS_Store`, `__pycache__`, `*.pyc` ignored). Changed, missing, added: refused by name.
  No reliance on `installed_plugins.json` (its `gitCommitSha` is undocumented). Live: an export of v3.0.66 verified,
  274 files, 2 s; one changed byte refused.
- `plugin-ready --root` writes `vX.Y.Z` into `~/.config/autosound/plugin-ready` (once), for the SessionStart hook.
  A version, not a path: the hook runs in Git Bash on Windows and the paths would not compare across shells.
- Selftests: a signed copy passes, CRLF passes, noise ignored, changed/added/missing refused, an unsigned release
  refused, the ready line written once.

### #120 — the plugin route reaches a working method — built; the real install is the candidate's run

- **What Claude Code offers** (plugin docs, 2026-10-02): no install-time script; a `SessionStart` hook in
  `hooks/hooks.json` (stdout goes into the session's context, default timeout 600 s, `${CLAUDE_PLUGIN_ROOT}`,
  `${CLAUDE_PLUGIN_DATA}`); plugin commands `commands/*.md` → `/autosound-tuning:<name>`; hooks run in Git Bash on
  Windows, PowerShell only when there is no Git Bash.
- **Decided: the installers do the work, in plugin mode; the hook only nudges.** Installing packages from a hook at
  every session start would open macOS's Command Line Tools dialog and wait on downloads, and a second installer
  would be a fourth copy of the triplet's decisions. `install.sh --plugin` / `install.ps1 -Plugin`: the plugin root
  from the script's own folder (no `.git`, a `plugin.json` with a version), `upkeep.py verify-copy` before anything,
  `SKILL_HOME` set to the plugin's skill folder so every later step reads it, `plugin-ready` at the end. The clone
  and the beta copy are skipped. `commands/setup.md` runs it with `--yes` on the person's word.
- **The hook** reads `~/.config/autosound/plugin-ready` for `v<version>`; absent, it prints four lines for the
  session to offer `/autosound-tuning:setup` first. Silent when set up and for a checkout. Version, not path: see #121.
- Checked: `install.sh --plugin --terminal --dry-run` from an exported copy (the plan line, the check, the
  requirements and engine from the copy); `--plugin` from the working tree and with `--skill-ref` refused; the hook on
  a fake copy (note / silent / silent); `claude plugin validate` passes; `installer-consistency.py` 33 OK.
- **Needs the Arbiter (the candidate run):** a real `/plugin install` from a catalog at the rc's commit on the Mac and
  the Windows VM, then `/autosound-tuning:setup` — the PowerShell half has never run (no PowerShell on the Mac), and
  the hook on Windows depends on Git Bash.
