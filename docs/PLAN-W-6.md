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
