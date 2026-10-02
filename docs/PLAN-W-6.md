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

### #118 — agy through ADC: the installers and the docs (hub #234 asks 4, 5) — built; Windows half for the VM

- **Ask 4.** `install.sh`: `adc_file`, `critic_env_path`, `adc_switch_on`, `critic_env_set_adc`; `agy_status` signal 0
  is ADC (switch on + file present). In the sign-in step, an ADC file and no agy sign-in → offer to write the line
  (`offer`: Enter writes, `s` goes to the account sign-in; `--yes` never writes — ADC can bill a project kept for
  other work). The account route ends with one line pointing to the FAQ's ADC section. `install.ps1`: the same with
  `Get-AdcFile`, `Get-CriticEnvPath`, `Test-AdcSwitch`, `Set-CriticEnvAdc` (UTF-8 without a BOM: the method reads
  the file as plain UTF-8, and a BOM would hide the first key). Checked: the sh helpers on a fake home (none / file
  only / file + switch; the line written once, after a last line with no newline, mode 600). The PowerShell half has
  not run (no PowerShell on the Mac): the candidate's VM run.
- **Ask 5.** FAQ section in four languages (English written here, uk/de/pl by the Advisor through agy/ADC — the first
  translations on the new connection; `i18n-check` OK, the literals checked); `setup-critic-channel.md` §1 bullet.
- The README's model recommendation (Pro `-high`, not offered under ADC) goes with the docs pass, #124.

### #124 — the documentation to the release's state (English) — hygiene done; the interactive pass with the Arbiter next

The Arbiter, 2026-10-02: «зроби базову гігієну в одній мові - далі я хотів попрацювати ітерактивно з реадмі та ФАК з
тобою (до перекладу на всі мови)». Hygiene, English only:
- README: 3.x is the release (no «beta»); 2.8.x is a pointer to the FAQ's path 3; the plugin block now leads to 3.x
  with `/autosound-tuning:setup`; the ADC sign-in at the installer's last step; the critic's Flash (High) for ADC.
- FAQ: path 1 without «beta»; path 2 names the plugin and the setup; path 3 and «stay on 2.x» use the catalog at its
  branch (`claude plugin marketplace add ayukhno/autosound-tuning-skill#2.x`, Claude Code's documented way to hold a
  version; the old local-clone recipe is gone); «which version» reads `claude plugin list`; the migrator inside the
  plugin; the models with the ADC line; updating names the signed tag and the plugin's update; the README anchor.
- The six translations carry `Translation lags the English original:` until #125, so `i18n-check` notes, not fails.
- Left for the release's bookkeeping (#123): `commands/install-tcc.md`'s app pin (v0.1.35 → the paired TCC v1.1.0),
  the install pins, the CHANGELOG doctrine's «the catalogue is pinned to 2.8.3».

### #124 (continued) — the README/FAQ pass with the Arbiter — done

- README, line by line with the Arbiter (English); the Advisor proofread it (four fixes).
- The roadmap: 3.1 is the release, one-command installer; next is what users ask for (the Arbiter: no further plans).
- FAQ: the Advisor compressed it by the README's rules, sections dropped and merged on the Arbiter's word; Fable read
  README + FAQ as a novice (no terminal, AI only as a browser chat) and listed where they get stuck. On the Arbiter's
  choice: a glossary, «Before you start», one path from installation to the car, Control mode, the naming rules kept;
  the terminal, other ways, versions and the reviewer by hand moved to `ADVANCED.md` (English only). README untouched
  except the terminal + Control mode line and its bar (quick guide); the FAQ bar carries the full guide and the roadmap.
- The capture sheet: the minimum set includes the hand-held RTA; only the nine sweeps are optional.

### #125 — the translations — done

README and FAQ in uk/de/pl, translated whole by the Advisor through agy/ADC; bars set per language, in-page anchors
remapped to the translated headings, two Ukrainian slips fixed. `i18n-check` OK; every anchor resolves.

### #126 — upkeep names the newest agy and native Claude Code (hub #237) — built

Joined W-6 on the Arbiter's word (2026-10-02: «додаємо і робимо»). `available_version`: agy `self` → the manifest
`…/manifests/<platform>.json` its installers read (`agy_platform`: darwin/windows/linux[_musl] × amd64/arm64); Claude
`self` → `registry.npmjs.org/-/package/@anthropic-ai/claude-code/dist-tags`, the tag of `claude_channel()`
(`autoUpdatesChannel`, `latest` by default). `_http_json` returns None on any failure → "". `tool_rows` takes `fetch`, so
the selftest stays offline. Live on the Mac: agy 1.2.15 → 1.2.15. **Tell tcc** with the tag.

## The candidate — `beta-v3.1.0-rc1` (2026-10-02)

PR #127 (CI green) fast-forwarded to `main`; `tag-check.sh --candidate v3.1.0` 5/5; signed tag on `4dbb969`. An export
of rc1 verifies against it by itself (279 files; `v3.1.0` does not exist yet, so `copy_tag` takes the candidate).
For the plugin route, branch `rc-catalog` holds a catalog (`autosound-rc`) that installs rc1 by its sha — for the run
only, deleted after it.

What the run covers (the Arbiter, the Mac and the Windows VM):
1. The installer at rc1 (`--skill-ref` / `-SkillRef beta-v3.1.0-rc1`): the signature line, the ADC offer where a
   Google Cloud ADC file exists, `doctor` — on Windows agy's tool-less reviewer agent for the first time.
2. The plugin route on a machine without the installer's copy: `claude plugin marketplace add
   ayukhno/autosound-tuning-skill#rc-catalog`, `claude plugin install autosound-tuning@autosound-rc`, the session's
   note, `/autosound-tuning:setup` («beta-v3.1.0-rc1 as its author signed it», the tools), no note in the next session.
3. S-090: `key move-shell` on the VM.

### #123 — the catalog: a protected surface (hub #239)

`main:.claude-plugin/marketplace.json`'s pin is protected surface №2 and the `Latest` release is №9
(`RELEASE-CHANNEL.md` §3): the release role's. Hub #239 (SKL-063) asks how they are done for v3.1.0, and for hub #220's
minor-pair rule before the tag; the skill touches neither surface before the answer. TCC is asked to re-pin to rc1 for
one joint run and to tag v1.1.0 on v3.1.0 the same day (hub #238, SKL-062).

### The candidate run — results so far

- **Windows VM (ARM64), installer at rc1, 2026-10-02:** «beta-v3.1.0-rc1 is signed by the skill's author»; libraries,
  the REW shortcut, TCC v0.1.46 (TCC's candidate not cut yet); agy «already set up», no ADC on the VM, so no ADC offer
  (as expected). No prebuilt engine for the candidate («no SHA256SUMS on beta-v3.1.0-rc1»): `engine-binaries` runs on
  `v3.*` tags only, so a candidate never carries one — the release will; the VM had one from an earlier install.
- **`doctor` on the VM:** «Вхід agy: обліковий запис agy (вхід є)» (#117), «CLI agy запускається без ключів API» (#119);
  with `--via cli --model gemini-3.8-flash-high`: «Шлях cli … ключ google для раунду не береться», **«Живий виклик (CLI
  agy): channel works», «АВТОМАТИЧНИЙ (відповів CLI agy)»** — agy's tool-less reviewer agent in its temporary folder
  answers on Windows (#117 ask 7).
- Pool for the next wave (cosmetic, `doctor`): with no model pinned it still prints «Режим роботи: АВТОМАТИЧНИЙ (через
  API google)» though a round would stop at the choice; on a CLI route it prints «Ключа API … немає» beside «ключ … не
  береться» while the key is in the store.
- **The plugin route on the VM, rc1:** the catalog `autosound-rc` added and the plugin installed; the SessionStart
  note reached the session word for word (both reasons, the offer of `/autosound-tuning:setup`); the setup showed the
  PowerShell line and ran it on the Arbiter's yes; **the check refused**: «1 not in the release: .in_use/4368». On
  Windows Claude Code's `.in_use` marker is a folder with a file per process; `copy_files` knew only the file form.
  Fixed (`_COPY_NOISE_DIRS` gains `.in_use`, `.orphaned_at`; selftest with a `.in_use/4368` folder) → **rc2**, which
  also carries S-096 (the Arbiter's word: it joins only if an rc2 is cut for another finding).
