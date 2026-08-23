# Changelog

All notable changes to the autosound-tuning skill. The skill is co-developed with real tuning sessions: each refactor harvests confirmed lessons from the field and folds them in.

## What the version number means

**Major** — the product changes in principle. **Minor** — a version, which is to say **a release**:
the moment 3.x is handed to users rather than worked on. **Patch** — ongoing fixes between releases.

Two consequences worth stating, because both have already caused a question:

- Every `3.0.x` tag is **work, not a release — but say for whom.** There are two audiences and the
  tags reach them differently. The plugin catalogue (`.claude-plugin/marketplace.json`) is pinned by
  SHA to the last released line, **2.8.1**; it does not move when a tag is cut, and that pin is
  deliberate, not forgotten. The **installers and TCC's updater track tags**: both take the newest
  tag matching `SKILL_TAG_GLOB` (`install.sh`, `install.ps1`) or the same glob in TCC's updater, so
  a `3.0.x` tag is on somebody's machine as soon as it is pushed, with no intervening step. To a
  catalogue user a `3.0.x` tag is invisible; to an installer user it *is* the release. Cut one with
  that in mind — the Upgrading note is the only warning that audience gets. **3.1.0** is the moment
  the catalogue moves too, and that is what gives the method an installation path independent of any
  consumer.
- **A published tag is never moved. A forgotten note ships as the next patch.** Two costs, and it is
  worth being exact about which, because the obvious one does not apply here. **It is not that
  installed users get stuck:** both installers fetch the ref *by name* from the remote
  (`git fetch --depth 1 origin "$SKILL_REF"` → `checkout FETCH_HEAD`, and a first install is
  `clone --branch <tag> --depth 1`), so a moved tag is picked up correctly on the next update, and
  TCC's updater re-resolves from `ls-remote` the same way. What it actually costs: **(a)
  diagnosability** — two different sets of code wear one number, so the version can no longer tell
  you what is on somebody's disk, which is the entire job of a version; and **(b) local clones**,
  where it genuinely bites: a plain `git fetch` does not move an existing tag, so every developer
  checkout and every vendored copy keeps silently showing the old commit until someone runs
  `fetch --tags --force`. So a missing Upgrading note is not a reason to retag; it is a reason to cut
  `x.y.z+1` carrying it. The cost is one spent number, which is nothing against two builds sharing a
  name. **Write the Upgrading note before tagging, not after** — the cheaper half of the same rule.
  Learned by doing it wrong: `v3.0.12` was force-moved from `2e71dd2` to `addc9b9` on 2026-08-22, and
  a consumer's vendored checkout showed the stale commit within the hour.
- The number answers *"is this a release?"*, **not** *"how risky is the upgrade?"* When a patch
  changes a return contract — `eq_gate.check` gaining a fourth verdict, `arrival_triangulate`
  emptying fields — the warning belongs in this file's **Upgrading** note and in the release body,
  where a consumer will actually read it. Do not reach for a bigger number to signal danger; say the
  danger in words.

## [Unreleased]

- **An abstention is half an answer — a tool that cannot run must ASK, and say what it costs**
  (`references/core/estimator-scope.md §1a`, the user's rule). Saying "unknown" stops a tool being
  believed where it has no vote, and then quietly moves the work onto whoever reads the output:
  they must work out what is missing, who can supply it, and whether it matters. Left there,
  "unknown" becomes wallpaper. So an abstention for want of an INPUT now names the missing fact
  precisely, says what it costs, addresses the Arbiter when only they can supply it, and rolls
  repeats up. Graded by what it STOPS — stopper / degraded / slow — because that is what the
  Arbiter is deciding, and re-graded as the work changes: a missing gain STEP blocks nothing until
  somebody enters a half-decibel trim, and then it always was a stopper. `resonalyze_vc.py`'s gap
  roll-up carries the grade, the quantified cost and the ask.
- **A channel's EQ to the clipboard, in the DSP's own format** — `eq_export.export_eq(profile,
  eq_rows, crossovers=…)`, one call so a window never learns a format. Audiotec-Fischer (Helix /
  MATCH / BRAX) writes the vendor's `Full EQ (N bands)` bank, with N from the profile rather than a
  constant, because the size is in the header and a hardcoded 30 emits a header that lies. For
  anything else, REW's own **Generic / Extended** block — a real pasteable format, not a table to
  type from — and the flavour follows the content: Extended when there is a crossover to carry
  inline, Generic when there is not. **Crossovers never go into an Audiotec-Fischer bank** (it is
  EQ only; this vendor keeps them as separate device fields) and never go to a tier whose profile
  says it has none, which is how a virtual channel is excluded without special-casing the word.
  `format_name` comes back with the text, and nothing is dropped without a reason.
- **`atf_eq` and `generic_eq` are now byte-checked against real REW exports.** The ATF selftest was
  a semantic round-trip — parse, format, parse, compare values — which cannot see a formatting
  difference, because it re-reads our own output with our own parser and passes either way. Against
  a real export it was missing a trailing tab on shelf rows. The two formats also differ in
  precision (frequency 1 dp against 2, a PK's Q 2 dp against 3), which is exactly the class of
  thing that ruler could never have caught.
- **`in_scope: false` — a tier the DSP HAS and the method does not tune.** The Helix's input stage
  exists, but it is not a tuning tier: it forms the input signal from a factory head unit's
  speaker-level outputs, and on optical / Bluetooth / USB it is not in the path at all. Recovering
  a flat input by undoing what a head unit already did — its EQ, its delays, its all-passes — is a
  different problem, and this method does not solve it. Deleting the group would have asserted the
  hardware lacks the stage; leaving it in scope made `open-questions` ask forever about controls
  nobody will enumerate, and a list carrying permanent dead entries is one people stop reading —
  the failure §1a exists to prevent. So it is kept, declared, and skipped when counting what is
  unanswered. Expect no ledger rows for such a tier; their absence is not an incomplete project.
- **The PEQ mode pairing is OBSERVED, and the derived label is retired as SATISFIED.** The
  "Parametric EQ" panel was photographed in one state with every field visible together — Freq
  26.01 Hz, Gain 0.1 dB, Q 50 — which settles both halves at once: the frequency field ACCEPTS two
  decimals rather than merely displaying them, and Q reaches 50 in that same panel. So the union
  recorded earlier co-occurs in one mode and stops being an inference. Said as *satisfied* rather
  than dropped, because a requirement quietly abandoned looks identical afterwards to one that was
  met. The same shot corroborates the EQ band's 0.1 dB step, so the band gain and the channel trim
  are now measured as different in range, step and resolution rather than argued to be.
- **The ask-rule applied beyond the converter.** `dsp_profile.gaps()` turns each unanswered fact
  into `{key, what, governs, ask}` — and deliberately does NOT grade, because this module cannot
  see the work: `channel_gain.step_db` is nothing while every trim is a whole number and a stopper
  the moment somebody wants half a decibel. A library that guessed urgency would be inventing it.
  `timebase.compare()` DOES grade, because it can see the batch. And §1a now states the boundary:
  the rule is for a missing INPUT only — a tool silent because it is out of its domain has no
  answer for anybody to supply, and asking for one is worse than silence, since it reads as a real
  gap and gets a real answer invented for it.
- **`timebase`: silence is not disagreement.** Grouping captures by their stated terms treated an
  unstated offset as a DIFFERENT offset, so one silent capture manufactured a mismatch the batch
  had no evidence for — and the silence then graded itself unimportant on the grounds that the
  batch "already" mismatched, which was circular. Only captures that state their terms are
  grouped; the silent ones are reported as unknowns, and they are a STOPPER when others did state
  theirs, because that is the comparison somebody is about to make.
- **`channels[].tier` is for every channel, not only spares** — and `project.py backfill-tiers`
  fills it by READING the ledger's row keys, never by inferring. A channel's tier cannot change
  between snapshots, so by schema v3's own test it is identity and belongs in `project.json`;
  leaving it in ledger keys for working channels put one fact in two homes depending on a property
  of the channel. Found by `autosound-tcc` on a real **seeded** project: with no ledger yet, not
  one working channel could be placed and a fully described car drew an empty rig panel — 6 of 20
  placed on the reference car, all six of them spares. A channel with no ledger row and no `tier`
  stays unplaced rather than guessed: `role` would place most of them, and that inference is what
  the field exists to refuse, because slot letters repeat across tiers and a wrong placement is
  invisible once written. Seed order matters — backfill the source first and the tiers travel.

## [v3.0.19] — 2026-08-23 · reading somebody else's tune, and a library to check it against

Written before the tag and read back against `git log` before cutting it — which caught two
omissions, so the rule has two halves: write it early, and re-read it, because a note is not
a place things file themselves.

- **The method ships a DSP profile library** — `knowledge/dsp/profiles/`, with
  `dsp_profile.find_bundled(vendor, model)` defaulting to it. It took a directory argument since it
  was written while the method shipped none, so every consumer built a private library and one
  processor ended up described four times in three serialisations. First entry is the Helix DSP
  Ultra S, contributed by `autosound-tcc` and diffed field by field before landing.
- **`dsp_profile.py refresh <project> [--write]`** brings a project's `dsp_profile.json` back in
  line with the library — a command that can be re-run, not a paste that fixes today and diverges
  again next month. It refuses to approximate: no exact vendor+model match changes nothing.
  `list-bundled` enumerates the library.
- **`rew_api.get_timing(mid)` — one exported reader of a measurement's time base**, for the
  method and for `autosound-tcc` alike, instead of each consumer digging the fields out of a raw
  record. Two readings of REW's timing fields is how the two halves of a project come to disagree
  about when a sweep happened — and that disagreement would look like a driver that moved. The
  rules travel with the fields, so a caller cannot take the numbers without them: `offset_s` is
  authoritative and the prose in `notes` is only a cross-check; `reference` alone is not evidence
  of a shared time base; `ir_start_s` is the anchor and `ir_peak_s` is not; an RTA has no IR, which
  is not a disagreement. Its contract is pinned in `rew_api`'s selftest because it crosses a repo
  boundary.
- **`rew_tool/timebase.py` — were these measurements captured the same way?** A batch
  comparability gate, asked for because a project accumulates captures across sessions and nothing
  ever checked that the batches agree; a mismatch does not announce itself, it reads as a driver
  that moved. Compares timing reference AND offset as a pair, sample rate and sweep range.
  **`timingReference` is not evidence of a shared time base** — it says `"Loopback"` whether the
  offset is 0 or 7.7 ms. Verified against a live REW: three offset groups in one set, all claiming
  `Loopback`, plus a note deliberately edited to say 5 ms beside a field saying 4 — a test of what
  an export carries, since reverted, which establishes that the two CAN diverge and nothing about
  how often.
  It separates *comparable* from *agree* — a batch can be internally consistent and still have
  nothing stating what it agrees on, which is safe to compare within and not across days.
- **A DSP profile group's `fields` is null-until-confirmed.** It had to be a non-empty list, so
  the only way to make a profile validate was to name some controls — and because `missing_facts`
  derives its checklist FROM the declared tokens, under-declaring did not merely assert controls
  nobody had confirmed: it **deleted the questions** about the ones left out. A tier written as
  `["hp", "lp"]` to get past the validator reads to every consumer as "this DSP's outputs have
  crossover legs and no gain, no delay, no polarity and no EQ", and `open-questions` then says
  nothing about any of them. `fields: null` now means "this tier exists, its controls are not
  enumerated yet", and `open_questions` reports it. Absence of a GROUP remains a positive claim
  that the tier does not exist; the two must not be confused, because one answers a question and
  the other asks it. ⚠️ **Consumers iterating `group["fields"]` must read it as
  `(group.get("fields") or [])`** — a null will otherwise raise. Found by the AutoSci session
  trying to contribute an honest profile stub and being unable to.
- **`groups_enumerated` — the tier LIST gets the same tri-state.** `fields: null` fixed a tier's
  controls and left the identical defect one level up: `groups` must be non-empty, so an honest
  stub names the one tier it knows and thereby asserts every other tier does not exist. `true`
  means the list is complete and an absent group IS a claim that the DSP lacks it; `false` means
  there may be more; absent/null means nobody has said, and `open-questions` asks. Existing
  profiles will therefore report one new open question until somebody answers it — including our
  own Helix, which is correct: nobody has confirmed it has no per-input tier.
- **Second library entry: Musway M6V4**, contributed by the AutoSci session and deliberately almost
  empty — name, vendor, one tier, everything else `null`, and what was remembered kept in
  `_open_questions` where no consumer can execute it. It is the shape a low-confidence entry should
  take: the label goes per FACT, not per file.
- **`rew_api` no longer substitutes a different quantity for a missing IR time base.** It reads
  `startTime` or raises. `delay` is the ARRIVAL, one second of sweep pre-roll away from the buffer
  origin, and it is exactly `timeOfIRPeakSeconds` — so a reconstruction from it would inherit the
  peak instability that the same measurements warn about. The dimensionally correct formula is
  recorded in the docstring as deliberately unused, so nobody restores it as a helpful fix.
- **`rew-api-quirks.md` gains what a live REW actually does with time** (measured, 19 captures
  across two sessions): the timing offset is folded into `delay`; `timingReference` reads
  `"Loopback"` whether the offset is 0 or 7.7 ms, so it is not the guard it looks like; the IR peak
  is not a timing anchor (it moved 3.6 ns between two reads of one *stored* measurement); the text
  export quantises `Start time` to the sample grid and carries no offset at all; and the pre-roll
  is not a constant — 1.000000 s on twelve channels, 1.000003273 s on the sub.
- **A repeatability floor for sequential per-driver measurement**, which is a method fact rather
  than a code one: ~1 sample of drift across 6 captures over 18 minutes, per-capture rather than
  per-clock, present with no offset applied. Over eight channels that is 1–2 samples — below what
  matters for a woofer, not obviously below what matters for a tweeter. Hence the new rule:
  re-measure channel 1 at the end whenever inter-channel timing is load-bearing.

- **Two provenance corrections in the knowledge files, which change what the method CLAIMS rather
  than what it does.** The Helix EQ's "Q 0.5–50 with a 0.01 Hz step" pairing is now labelled as
  DERIVED from the user's full-range ruling rather than measured: each of the three numbers is
  separately user-verified, but nobody has yet seen them hold at once in one PC-Tool mode, and
  anything copied from that line into a machine-readable profile must carry the derived label —
  a plausible number becomes a measured fact simply by sitting in a field that only records
  measured facts. And `dsp_profile.py`'s opening paragraph no longer illustrates its design
  rationale with MUSWAY specifics that traced to one unverified recollection; the retraction had
  reached the paragraph making the argument and not the summary above it, where most readers stop.

### Upgrading

**`rew_api.get_impulse_response` can now raise `KeyError`** where it previously returned a
plausible-looking time base. That is the point — the old fallbacks placed sample 0 a second away
from the truth in one direction or the other — but a caller that never handled an exception there
should look. In practice REW supplies `startTime` on that endpoint, so the raise is a guard rather
than a behaviour change on any working rig.

Nothing else removed or renamed; two new modules and one new command, all additive.

## [v3.0.18] — 2026-08-23 · somebody else's tune, read back as ours — and refused where the hardware cannot follow

### A Virtual DSP session becomes ledger rows

**`rew_tool/resonalyze_vc.py`** — the return leg of `resonalyze_ir.py`. That one writes REW
measurements INTO [Resonalyze](https://github.com/DIMOSUS/Resonalyze); this reads a tune back out.
A `resonalyze-virtual-crossover` v7 session becomes schema-v3 ledger rows —
`{hp, lp, gain_db, ta_ms, polarity, eq, status: "proposed"}`, one per sourced leg — each with a
machine-readable per-field verdict against the project's own `dsp_profile.json`. The occasion was
Resonalyze's author sending his tune of the reference car over our measurements; the point is that
**anybody's** Virtual DSP session can be read as a proposal against our ledger, through one
function a terminal and a GUI both call.

**Nothing is rounded to fit.** His plan uses Linkwitz-Riley 48 dB/oct on eight edges; a Helix DSP
Ultra S offers LR at 12/24/36. Each of those comes back `enterable: false` with the value he asked
for intact. Substituting the LR36 the hardware does have would be a tuning decision wearing a
conversion's clothes — and the point was proved the same day, when the first human attempt at an
"obvious" substitution picked a slope Resonalyze itself cannot model.

**A capability the profile does not state is `unknown`, never `ok`** — `estimator-scope.md`'s rule
applied to a profile instead of an estimator. Every such verdict names the profile key that would
settle it, and they roll up into `profile_gaps`, so a long list of shrugs reads as a few missing
facts. That is what surfaced the four gaps in our own Helix profile, all of which are now closed.

Four traps it exists to get right, each of which a plain reading gets wrong: `crossoverKind`
decides which edge is live and the **dormant edge still holds values** (often the constructor
default, and on the sub a 10 Hz high-pass his tune does not apply); `stereoSceneOffsetMs` and
`stereoLevelDifferenceDb` are the **aim** of his auto-alignment, already inside each leg's numbers,
and the SIGN of both encodes the drive layout rather than a value; `IsTransparent` is derived, not
a bypass; and v7 keeps `enabled`/`bypass` on the **pair** only, so a side-first read hands back a
muted leg as playing.

### A new project starts from the car you already described

**`rew_tool/project_seed.py`** — system parameters travel from an existing project instead of being
retyped. Ported from `autosound-tcc` with its classification intact, and moved here because
`project-schema.md` and `project.py` are here: the code that WRITES `project.json` belongs where
the schema is, or the two drift and the copy outside the schema drifts silently. **The system**
travels; **the findings** (`acoustics.flaws`, `_open_questions`) are offered but off by default,
because their `evidence` names measurements that exist only in the source project; **the project's
own** stays behind. An allowlist, not a blocklist — whatever the schema grows next stays put until
somebody decides it travels. `Seeded.profile_open` counts what the inherited profile still does not
state, so a `null` cannot read as settled.

### The Helix profile, and a rule for every profile after it

Four capability facts, user-verified in PC-Tool: **channel level −30 … +5 dB** on both tiers —
deliberately *not* the EQ row's −30 … +12, which is band gain, and the asymmetry is why it had to
be measured rather than inferred; **EQ frequency 10–40000 Hz**; **crossover corner 20–20480 Hz**;
**delay ceiling 20.82 ms**.

And the rule they produced, which outlives them: **record the FULL range, because it can be entered
by hand.** The sub channel's UI offers 20–300 Hz and a higher corner types in fine, so 300 is not a
limit. Generalised, it dissolved what looked like a three-file contradiction over the PEQ's
frequency step — two coherent readings of two different UI *modes*, neither of them the hardware.
The trade-off is stated in the profile itself: a profile now answers "enterable on this hardware",
not "enterable in the mode you are in", and that is the recoverable direction. Refusing a setting
the hardware accepts means a valid tune is never tried and nobody learns why.

### Also in this tag

- **The crossover corner steps in 1 Hz**, not 0.01 — the 0.01 belongs to the parametric EQ's own
  frequency control. Not only documentation: `xover_select` searches corners on a caller-supplied
  `step_hz`, so a fractional step searched settings the hardware cannot be set to and then rounded
  the winner off the optimum it had just computed.
- **The Windows installer path ran end to end for the first time**, on a VM whose method was at
  3.0.4 and whose app had neither an update panel nor `--install-desktop`: the method resolved to
  3.0.16 and the app to 0.1.14 by tag, and both shortcuts were created — so "replace the app, then
  call it" worked on a machine where the installed app could not have made them when the run began.
- Repo conventions moved to `CLAUDE.md`, and the session process that is nobody's business but ours
  moved out of this public repository into an untracked file.

### Upgrading

**Two new modules; nothing removed, renamed, or changed in an existing return contract.** The
selftest suite goes 26 → 28 (`scripts/run-selftests.sh`, the same command CI runs).

Three things worth knowing before you rely on them:

- **`resonalyze_vc.py` emits rows and stops.** It does not write a ledger snapshot, and it should
  not: banking rows is `state/apply.py`'s gated job and a tuning decision. Gate your own writes on
  `summary["blocked"]`.
- **`enterable` is three-valued** — `true` / `false` / `null`. `null` is not a soft yes; it means
  the profile does not state that limit, so nothing was checked. Treat it as "ask", never as "pass".
- **A DSP profile now claims the hardware's full range, not the current UI mode's.** Under the
  full-range rule a checker can accept a value some UI mode will not offer — a Q of 30 that Fine EQ
  refuses, say. The tuner meets that at the PC-Tool screen and switches mode. If you were relying
  on a profile to describe one mode exactly, it never did, and now it says so.

## [v3.0.17] — 2026-08-22 · the field session's six open asks, and a check that does not measure with its own ruler

### The tools answer, or say they cannot

**`rew_api` errors now carry REW's own explanation.** An `HTTPError` *is* the response — the
server's body is sitting on it — and dropping it turned `The request is missing parameters: append
lf tail, append hf tail, include cal` into a bare 400 that named nothing. A session lost time
hand-probing for what had been arriving all along. All four verbs go through one opener now; the
raw body is also left on `.rew_body`.

**`delete_measurement(mid)`** — REW has supported it all along and a session had to hand-roll it
after an accidental duplicate. Its docstring carries the hazard that outweighs the call: a delete
**reshuffles every ordinal after it**, so resolve → delete → resolve. Never collect ids and loop.

**`duplicate_titles()`, and `contract.py check` runs it first and unconditionally.** The identity
model rests on a title being one measurement's stable name; REW does not enforce it; a live session
held two `m-L_0 (sw)-EP` and nothing said so. `find_measurement_id` would have raised on the
ambiguity only at the moment of use, if it ever came. Everything else in that check trusts titles,
so this is checked before them.

**The REW checklist reads the OPEN capture round, and abstains when there is none.** It used to
derive what it expected from ledger HEAD, so a project on a set-0 baseline reported
`0/16 captured — MISSING [...]` forever and a genuinely missing round would have been invisible in
that noise. The round already carries the list it asked for, which beats re-deriving one. With no
round open it now says so rather than answering: nothing was asked for, so nothing can be missing —
the same rule `references/core/estimator-scope.md` states for every other estimator here.

### The method says what it is silent about

**Phase-0's four artifacts are a LIST, not a sequence.** A session read the numbering as an order,
ran all four, and only afterwards learned that the EQ-ability map is silent below ~150 Hz — so it is
not on the critical path to the sub↔midbass joint, which is usually the first Phase-1 decision.
`phase_0_baseline.md` now gives each artifact its scope, **what it is silent about**, and which
Phase-1 decision consumes it, so the order is chosen by what is blocked.

**The flaw map has a row shape for time-domain install properties** — `energy_lag`, `ringing`,
`decay_asymmetry`, carrying `t_ms`, with `f_hz` optional. One door's energy lagging the other's by
~1.1 ms is a real measured property of an install with no frequency and no dB; for want of a row it
went into prose, which is exactly what SCR-015 exists to prevent.

### A check that does not measure with its own ruler

Two more anchors on `dsp_math`, after v3.0.14's corner check turned out to leave gaps that others
found by asking *what would still pass?*

- **Phase at the corner cannot depend on where the corner is** — the response scales with
  frequency. Needs no per-family constant, which every obvious alternative does. Compared as a
  ratio, never as a difference of angles: at 24 dB/oct the corner phase is ±180°, and two identical
  answers land either side of the wrap, which a naive max−min reads as 360° of drift in a module
  that is perfectly correct.
- **The whole grid is checked against an independent ZPK reference** — poles and zeros multiplied
  directly in the z plane, no polynomial anywhere in the path. This is the strongest of the four: it
  confirms the SOS rewrite by a third route instead of by SOS agreeing with itself, and it catches
  the 30 dB/oct orders that the corner and phase anchors are both blind to. This module: 0.000000 dB
  / 0.0000°. The pre-v3.0.14 form: 77.6 dB and a half turn.

**`scripts/windows-install-test.md`** writes down the Windows pass that has only ever been spoken,
including the upgrade case (a VM on an old build has no `--install-desktop` at all, so the run works
only because the app is replaced before the call — a sequence never executed) and one *wrong* worry,
recorded so nobody pays for it twice.

### Upgrading

**New API surface, nothing removed or renamed.** `rew_api.delete_measurement` and
`rew_api.duplicate_titles` are additions. Existing calls are unchanged.

Two things a consumer may notice:

- **`contract.py check`'s REW section reports differently.** Where it used to print
  `N/M captured — MISSING [...]` derived from ledger HEAD, it now prints the open capture round's
  verdict, or a note saying nothing is outstanding. A front-end that parsed the old line, or that
  treated its absence as an error, should read the new keys: `round`, and `duplicate_titles` when
  present.
- **Flaw rows are no longer guaranteed to have `f_hz` and `level_db`.** A row whose `kind` is one of
  `energy_lag` / `ringing` / `decay_asymmetry` carries `t_ms` instead. **Check the kind, not the
  field** — the first consumer to trip over this was `project.py` itself, whose deduplication keyed
  on `entry["f_hz"]` directly.

## [v3.0.16] — 2026-08-22 · a fresh install and the app's update button finally mean the same thing

Two consumer requests, landed together because they change the same two files and the same install
path.

**SCR-054 — the app is installed BY TAG, the way the method already was.** `git+URL` with no ref
means HEAD of the default branch, so a fresh install handed somebody whatever was on the app's
`main` at that moment, including unfinished work — while the app's own update button, since its
v0.1.12, pins the newest release tag. Two ways of getting the same app, disagreeing on one machine:
the installed build could be *newer* than every release, and the button then had nothing to offer.
Both installers now resolve the newest app tag and pin it, with `--tcc-ref` / `-TccRef` beside the
existing `--skill-ref` for anyone who wants an older one. No tags or no network is not a failure —
it installs from the default branch as before and says so.

**SCR-056 — the app makes its own shortcuts.** Two guesses across a repository boundary, replaced by
one call to `autosound-tcc --install-desktop`. The macOS bundle was built by a script in *this*
repo, located by path (`$SKILL_SRC/scripts/…`, falling back to `dirname $0` — which under
`curl … | bash` is whatever folder the person was standing in, and once failed to be found on a
clean M1). The Windows icon was worse: `install.ps1` ran the app's own interpreter to read
`autosound_tcc.app.APP_ICO` by name out of a private module, so a rename on their side would have
removed the icon here with no error on either side. The half that owns the bundle layout and the
icon now places them, and this script reads an exit code. `scripts/make-macos-app.sh` is kept and
marked superseded.

**The catalogue moved for the first time since 2.8.1** — to **v2.8.3**, which carries the crossover
fix backported from v3.0.14. Its pin had been `ref: "main"` / `sha b8d6347`, a commit from when
`main` *was* the 2.x line, and that commit carries the broken `xo_response`: every plugin install
was handing out the defect while the fix shipped on lines the catalogue does not serve. It moved for
a correctness fix, not a release — **3.x still becomes the catalogue's line at 3.1.0.**

Also: the app's tag glob is a named constant in both installers (`TCC_TAG_GLOB` / `$TccTagGlob`)
rather than a literal in a pipeline, and `installer-consistency.py` checks it — six shared decisions
now. The two globs deliberately DIFFER (`v*` for the app, `v3.*` for the method, because the two
version independently); the check compares the two files against each other, not the two globs.

### Upgrading

**The installer now requires the app at v0.1.13 or newer**, which is what its own tag resolution
installs — so a normal run is unaffected. The exception is a deliberate `--tcc-ref` / `-TccRef`
below v0.1.13: that build has no `--install-desktop`, so it installs and runs, but no shortcut or
app bundle is created. There is no fallback path; the only machines running older builds are the
author's own.

⚠️ **The Windows half of both changes is UNVERIFIED.** `install.ps1` was written as the mirror of
`install.sh` and has not been executed — there is no PowerShell on the machine that wrote it. The
macOS and Linux halves were run (`bash -n`, `--help`, and a dry run resolving both tags live). Treat
a Windows install from this version as the first test of it, and prefer `-DryRun` first.

## [v3.0.15] — 2026-08-22 · if you are on LR, v3.0.14 did not change your numbers

A correction to the previous release's Upgrading note, and two holes it left.

**LR is not affected at all — 0.0000 dB.** v3.0.14's note said "high-order filters below ~250 Hz"
and left readers to work out which. Measured properly, old module against new across the full
hardware grid (3 families × every order × hp/lp × 11 corners from 40 Hz to 2.5 kHz, comparing only
where the filter passes above −40 dB): **LR 0.0000 dB, BW up to 96.9, BE up to 104.1.** The reason
is structural: the LR path designs a *half-order* Butterworth prototype and squares it, so the order
handed to the designer is always low and the transfer-function form never breaks down. Since LR is
the default for joints, most builds were never affected — including, checked directly, a live
5-channel tune whose legs are all LR24. **What to re-derive: BW or BE at 36 dB/oct or steeper with a
corner below ~250 Hz.** Nothing else.

**The corner anchor did not pin steepness.** A Butterworth is −3.01 dB at its own corner for *every*
order, so if the `n = round(order/6)` mapping ever drifted, all 54 corner assertions would have
stayed green while every filter came out the wrong order. Raised by a consumer reading the new test
and asking what would still pass — the right question about any test. The selftest now also measures
an octave of stopband and requires the filter to fall at its nominal order (±1.2 dB/oct, against a
6 dB/oct step if `n` drifts). Verified by injecting a BE-only order drift, which the older polarity
assertion does not cover: caught.

Writing that check badly first taught two things worth keeping: measure the octave at **4×–8×** the
corner, because a Bessel approaches its asymptote more slowly than a Butterworth and reads ~7 dB/oct
shallow in the nearer octave; and keep the upper edge far from Nyquist, where the bilinear transform
warps the response *steeper* (BW42's lp slope over 8–16 kHz reads 46.7 dB/oct — the test being
wrong, not the filter).

**`run-selftests.sh` was globbing, not recursing**, so it silently skipped every module in
`rew_tool`'s subpackages: `state/{state,process,migrate,apply}` and `gates/{presweep_safety,
side_effect}`. All six have working selftests and all six pass. Found by the consumer that runs four
of them and none of the eleven this script was running — two partial sets, each believing it was the
whole. The count goes 20 → **26**.

**Hardware profile:** the Helix DSP Ultra S EQ limits are now recorded — Q 0.5–50, and in Fine EQ
mode Q 0.5–15 with a 1 Hz frequency step (user-verified in PC-Tool). Noted alongside it: that
ceiling is what the *hardware* allows, not what the method should use — §13's spatial-validity Q
ceiling is the binding one in a cabin.

### Upgrading

Nothing to do. No API and no numbers change: v3.0.14 fixed the arithmetic, this release corrects what
was said about who it affected and closes two gaps in the checks. If you deferred re-deriving
crossovers after v3.0.14, the list above is shorter than you were told — **LR joints need nothing.**

## [v3.0.14] — 2026-08-22 · every steep low crossover this module drew was wrong

`xo_response` designed its filters in transfer-function form and evaluated them with `freqz`. For a
high-order filter at a low normalised frequency that form breaks down: the polynomial coefficients
span many orders of magnitude and the answer is lost to floating point. Measured against the one
value every family has by definition — its gain at its own corner, −6.02 dB for LR (it is BW
squared), −3.01 dB for BW and for BE under the `norm="mag"` this module deliberately uses:

| | 40 Hz | 63 Hz | 80 Hz | 125 Hz | 250 Hz+ |
|---|---|---|---|---|---|
| BW36 hp | −17.2 | −0.7 | +0.5 | −0.1 | 0.00 |
| BW42 hp | +0.4 | −14.4 | **−30.1** | −7.0 | 0.00 |
| BE36 hp | **+13.2** | −7.5 | +1.4 | −0.1 | 0.00 |
| BE42 hp | −6.7 | **−28.0** | −27.9 | −5.1 | 0.00 |

Above 250 Hz the error is zero, which is why nothing noticed. Below it, the error sat on precisely
the settings a sub/midbass joint uses — that band is where steep slopes get chosen. Across an octave
either side of the corner the old curve differed from the true one by up to **75 dB** (BW42 at
80 Hz). Fixed by designing and evaluating as cascaded second-order sections (`output="sos"`,
`sosfreqz`), which is conditioned per section: **0.000 dB across the entire hardware grid.**

**Why the selftest suite passed anyway, and what now stops it.** Every existing check pinned the
joint's *behaviour* — inversion at odd-order LR joints, the near-tie rule, compactness — and none
tied the corner to anything outside the module. `xover_select` reports `fit=0.00 dB` while scoring a
realization against a target computed by the same broken function: the ruler and the part were one
object. The selftest now asserts the corner gain for all 54 combinations of family × order × hp/lp ×
corner, which is a definition rather than a stored number, and it fails on any future drift of
`_design` — including a silent revert of BE's `norm="mag"`, itself a choice verified against REW in
July.

Found by a reviewer injecting a 50 % corner shift into `_design` and observing that all 20 checks
still passed. The bug this exposed was not the injected one.

### Upgrading

**Numbers change.** No API moved — same call, same return type — but `xo_response`, and everything
downstream of it, returns *different values* for high-order filters below ~250 Hz. Affected:
`xover_select` (crossover choice and its reported fit), `align_joint` / `align_delay_polarity` where
the joint is a steep low one, and any predicted summation in that band.

- **A stored crossover recommendation from an earlier version, at a low steep joint, should be
  re-derived rather than trusted.** It was computed against a curve that did not describe the
  hardware.
- **Delays and polarities solved at such a joint deserve a re-check.** The inputs to that solution
  were wrong by tens of dB near the corner, so a previously "correct" answer there was correct about
  the wrong filter.
- Nothing above ~250 Hz changes, at any order. A build whose joints all sit higher is unaffected.

## [v3.0.13] — 2026-08-22 · four external rules, three attributions the draft got wrong, and the first CI

Four published findings folded into the reference set — and the useful part of the work turned out
to be checking them against the primary texts instead of the note that summarised them. Three
claims did not survive.

**§2 gains a fourth failure class: the directivity dip** (Wehmeyer, *"A Straightforward Stereo
Tuning Process"*, pp. 28-30). A crossover above the woofer's beaming limit leaves a hole in the
*reflected* field; the mic sums direct and reflected and shows a dip; filling it flattens the RTA
and makes the direct sound — where the image lives — bright. It is the only one of the four classes
where EQ actively makes things worse, and its treatment is the crossover frequency, not a filter.
§16's crossover rule (3) now carries the mechanism and his worked cases. His zone table is a figure
and is **cited, not reproduced** — inventing its boundaries would be the easiest lie in the file.

**A new §34, the mute-one-channel test** (same source, p. 52): a dip present on the sum and absent
from either channel alone is inter-channel phase, and his verdict is narrower than "fix it with
delay" — either it is a delay error or it cannot be fixed at all. With the >6 dB peak exception, the
"resist the urge to equalize with both playing" rule, and the deliberate-damage corollary.

**§13 gains the MMM boundary under its own author's name.** Jean-Luc Ohl: "missing the time and
phase information … not a tool to set up crossovers, time align speakers". Our doctrine already drew
that line; what was missing is that the method's own proponent draws it too.

**A Q ceiling on corrective filters, stated as ours.** The mechanism is Wehmeyer's — five mic
positions in a 7″ circle, 25+ dB apart above 1 kHz, and what fails to track the average after
smoothing is always *narrow*, so narrowness (not frequency) predicts "property of the position".
The rule we take from it: do not deploy a filter narrower than the features that survive spatial
averaging. Better than borrowing a number, §13 already captures six separated positions, so the
ceiling is **measurable per car** rather than assumed.

**§23: the peak is the starting estimate, phase agreement is the final criterion** — adopted
partially from DIMOSUS (Resonalyze #88). The arrival difference stays what we drive to zero; what
changes is the tie-break, where estimators disagree beyond placement scatter. This generalises §28's
existing rule from "the LF pair" to "any pair whose estimators disagree".

### Three corrections, all against the primary sources

- **"MMM is not for the cabin"** forbids more than *any* of the three sources do, and would outlaw
  the use we actually make of it. Narrowed to "not for timing/phase".
- **"rooms of 30 m³ or more" is not Ohl's number.** It is a conclusion of Critchley & Dunbavin (IOA
  Spring Conference, 2008) which he quotes. Attributed to them.
- **"Q ≤ 6 (Wehmeyer)" is not in either Wehmeyer text we hold.** It reached the draft through a
  paraphrase. The observation is his and stays under his name; the ceiling is ours; the number is
  ours to set. The sources' disagreement on smoothing (his article says 1/12, the paraphrase says
  1/6, Ohl recommends 1/6 for an unrelated reason) is recorded rather than averaged away.

### Tooling: the installers stop being three unchecked copies, and the repo gets CI

`scripts/installer-consistency.py` compares the five decisions `install.sh`, `install.ps1` and
`install.cmd` must share — skill repo, TCC repo, tag glob, `install.cmd`'s hardcoded `PS1URL`, and
the `tcc` default mode — and fails when they drift. In one evening the same class of drift was found
three times by hand; each time by someone reading carefully, which is the mechanism that fails on
the day nobody does.

`scripts/run-selftests.sh` runs that check plus **every** `rew_tool` module's own selftest — 20 in
all. `.github/workflows/checks.yml` runs that exact script on push and PR. The set is deliberately
small and offline so that **red means broken**: no REW, no network beyond `pip`, no downloaded
fixtures.

### Upgrading

**No code contracts changed in this release.** No function's return shape moved, nothing was renamed
or removed; a consumer pinned to v3.0.12 can take this without reading further.

Two things worth knowing anyway:

- **`scripts/run-selftests.sh` is now the single entry point for the skill's own checks**, and it
  runs all 19 `rew_tool` selftests, not a subset. A consumer wiring the skill's selftests into its
  own gate can call this one script instead of maintaining its own list — and will pick up modules
  that list did not have. It honours `PYTHON=…`, and it still needs `numpy` and `scipy` (unchanged
  since v3.0.12).
- **The Q ceiling and the phase tie-break are doctrine, not code.** They change what a session
  *recommends*, not what any function returns. A consumer that renders advice may notice narrower
  filters being declined and pairs accepted on phase agreement rather than on an arrival number.

## [v3.0.12] — 2026-08-22 · fractions of a dB were still allowed to choose a polarity

`align_delay_polarity` carried its own rule and then broke it. Among near-ties it preferred the
smallest `|tau|` — "the same summation with a more compact impulse" — but that rule ran *inside*
each polarity, and the two polarities were then settled by a bare `>` on band energy. A candidate
winning by 0.001 dB took both the polarity and the lobe. On a survey of 117 crossover
configurations, **18 were decided that way**: same `|tau|`, same residual null, the two answers
differing by 0.000 dB, the winner picked by floating-point noise.

The near-tie rule now spans both polarities, so a flipped candidate half a period away is treated
as the lobe it is. An exact `|tau|` draw — a Butterworth joint genuinely offers `(+1, -tau)` and
`(-1, +tau)` with the same sum and the same null — is settled by convention rather than by the
1e-15 separating them: **the driver stays non-inverted.** Nothing acoustic is lost, and one set of
measurements stops yielding a different polarity on different days.

### Why no "prefer non-inverted" margin

The obvious fix — the one an auto-alignment tool that works from raw arrivals uses, a 0.5 dB
preference for the plain connection — is wrong here and was measured to be wrong before it was
rejected. At an **odd-order Linkwitz-Riley joint the inverted connection is the correct one**, and
at 36 dB/oct it leads by only **0.17 dB**: any margin above that would silently invert a correct
result. That prior belongs to tools aligning two independent arrivals; here both branches come
from one measurement on one time base, so `tau = 0` is the prior and compactness already carries
it. The selftest now pins the physics — LR 12 and 36 dB/oct inverted, 24 dB/oct not — so the
margin cannot be reintroduced quietly.

### Added
- `polarity_margin_db`, on `align_joint` and `select_neighbor_pair` results: how far the chosen
  polarity beat the other at its own best delay. **Below a few tenths, summation did not decide
  the polarity** — it reported one. The value goes negative when the near-tie rule deliberately
  takes the marginally weaker polarity because it is more compact; that is the rule working.
- Selftest coverage for all of the above, written as closed-form facts about the filters rather
  than values read off a run.

### Fixed
- `|tau|` is compared in whole grid steps. `arange` is not bit-symmetric about zero, so `|-1.320|`
  and `|+1.320|` differed by 5e-16 — enough for the last bit to settle a draw before any stated
  rule ran.

### Upgrading

`dsp_math.align_delay_polarity` now returns **four** values, `(pol, tau_ms, null_db,
polarity_margin_db)`, where it returned three. Both in-repo callers are updated; any external
`pol, tau, null = align_delay_polarity(...)` must add the fourth name. The dict-returning
`align_joint` and `select_neighbor_pair` are additive — a new key, nothing renamed.

Polarity results may differ from v3.0.11 at joints where the two answers were equally good. In
every case observed the residual null is unchanged to the hundredth of a dB; what changes is which
of two identical solutions is reported, and it is now stable across runs.

**The `dsp_math` self-test now needs `scipy`, where it did not before.** It pins the physics by
*designing* crossovers rather than asserting on constants, and design is the one thing in this
module that requires scipy — `xo_response` appears six times in the self-test and appeared zero
times in v3.0.11. Nothing in the shipped code changed its dependencies: the crossover functions
always needed scipy, and everything else here (PEQ/APF responses, alignment, robust metrics,
greedy EQ fit) still runs without it. But a consumer that wires `python3 dsp_math.py selftest`
into a test gate will see that gate go red on upgrade, with a message about a dependency it never
chose. Declare `scipy` wherever that gate's dependencies live.

Stated as a rule for later notes: **a self-test moving into a subset that needs an optional
dependency is a consumer-visible change of the same class as a changed return contract**, because
self-tests are what consumers wire into their gates. Reported by TCC on the v3.0.11 → v3.0.12 bump
(1 failed / 1231 passed before declaring it, 1232 passed after).

## [v3.0.11] — 2026-08-22 · a tool that cannot say "not here" will be believed everywhere

Harvested from one working session in which a competent operator made six errors and **five were
the same error**: a tool returned a confident-looking number outside the conditions it is valid in,
and nothing in the returned value said so. Three of the five were already documented — in this very
reference set — and the prose did not fire at the moment the number was read. Prose warns the
reader; a value warns the user, and under load a session is a user, not a reader. So scope moved
out of the docstrings and into the return values.

### Added

- **`references/core/estimator-scope.md`** — the seam this release is about: the abstention
  convention; a table of **where each tool is SILENT**, so step order can be *derived* instead of
  asked (it was asked twice, by round trip); *a measurement is not a setting* (a best-fit τ is not
  a time alignment, a gate statistic is not a permission, a pocket measured before alignment is not
  a pocket); and what survives a "from scratch".
- **What a "from scratch" restart discards** — decisions, never instrument facts, with a
  one-question test: *would this number be the same after a factory reset of the DSP?* Latency,
  drift, mic calibration, Fs — yes. Corners, delays, gains, EQ — no. Added to
  `naming-and-structure.md §2`, where the restart trigger is defined; a real session nearly
  discarded a measured `electronicLatencyMs` that was sitting in its own capture manifest.

### Changed

- **`eq_gate.ExcessPhaseGate.check` returns `OUT_OF_SCOPE`** outside its calibrated band, with no
  metric attached. The grid deliberately runs half an octave below `trust[0]` while the MAD
  normaliser is computed on the trust band alone — so an out-of-band query divided by a scale never
  calibrated for it and came back indistinguishable from a valid verdict. Field cost: three of five
  BLOCKs on one car were out-of-band; re-run inside the band, two fell from S=4.2/4.7 to 1.3/1.2.
  `OUT_OF_SCOPE` is not a weak ALLOW and must be recorded by that name — *"ALLOW 1.2 @ 145 Hz"*
  reads as permission a month later, where the flaw map says never to boost. Nor is it a veto:
  `as_boost_gate` treats it as no objection, because a tool with no vote does not get one.
- **`analysis.arrival_triangulate` empties its estimators on ILL-POSED** instead of labelling them.
  A sub returned `edge30_ms = -8.16 ms` — nonsense, but nonsense shaped like milliseconds. The
  values move to `rejected` so reading one is deliberate; `spread_ms` stays, being the evidence for
  the verdict rather than an estimate of arrival.
- **`analysis.relative_delay_xcorr` states its precondition and detects the break.** The two IRs
  must already share a time base; the function cannot supply one. Fed per-measurement-centred data
  it returns a truthful `0.0000 ms` about untruthful input — which happened, and was diagnosed as
  the function lying. It now reports `basis: "shared" | "SUSPECT"`, flagging the same-peak-index
  signature of per-measurement centring. The old docstring's *"one time base → the relative delay
  is preserved"* described the shared crop and read as a promise the function never made.
- **Pair coherence / Δφ climb (§26) now carries its precondition: align the pair first.** The test
  asks what a delay cannot track, which is only a question once the delay is gone — and Phase 0
  captures solos with modifiers zeroed, so nothing is aligned by default and the pair's geometric
  offset (1.2–1.4 ms on the source build) sits inside the number as divergence. Measured cost of
  skipping it: a *"−18.96 dB pocket, deepest in the pair"* that was **−1.9 dB** once aligned, and
  would have pushed a crossover corner out of a healthy region. Stated in both `phase_0_baseline.md`
  and `diagnostic-techniques.md §26`.

## [v3.0.10] — 2026-08-21 · a stray file that could delete a channel, and the checker that never said so

### Fixed

- **A standalone `glossary.json` silently SHADOWS `project.json`'s `glossary` key, and the contract
  checker called it valid.** `naming.Glossary.for_project` returns the standalone file the moment it
  exists and never opens `project.json` — deliberate precedence (SCR-011), and unchanged here. What
  was missing was the alarm: `contract.check_glossary` inspected the *already-resolved* glossary, so
  it could not see that two sources existed and disagreed. Observed in the field on 2026-08-21, when
  a consumer's test fixture (seven channels) landed on a live project (eight) and the **centre
  channel ceased to exist** for every name check and every derived measurement checklist — while the
  one command whose job is integrity reported `present: true, valid: true`. The check now compares
  both sources and names the codes that the shadow hides. The **empty** standalone file is the worst
  form, not the absent one — everything vanishes and the old code would have answered "no glossary
  yet, go write one" to a project that already had a complete one; the shadow now decides validity
  and replaces that line. Locked in by `contract.py selftest`, both directions: a disagreeing
  standalone is invalid, an agreeing one is not an error.

## [v3.0.9] — 2026-08-20 · the noise floor of our own measurements, and where a dip stops meaning anything

### Added

- **A measured floor for the whole measurement history.** Hand-held repeats 25 s apart differ by
  **0.9–2.4 dB RMS** over 100 Hz–16 kHz with arrivals wandering **±2 samples** and drifting five over
  a quarter of an hour; on a tripod, **0.18–0.25 dB RMS** and **0.09 samples**. Every inter-channel
  delay taken hand-held carries that, invisibly — and any old single-point difference smaller than it
  was never evidence. With it: the gain set once, drift controls three times a block (cabin
  temperature moves an arrival by **0.43 samples per °C** on a 0.9 m path at 96 kHz), no ventilating
  between captures, and every A/B ratioed against the reference **nearest in time** (74 s apart:
  0.16 dB RMS; thirteen minutes apart: 0.95 dB). `diagnostic-techniques.md` §7.
- **The frequency below which a dip means something, and above which it does not.** A car's Schroeder
  frequency is **150–200 Hz** (Strauß/Treichel + Kessler, DAGA 2010; the bound itself is Geddes &
  Blind, AES 76 paper 2127, 1984). Above it sound pressure at a point is Rayleigh-distributed, so a
  measured value is **much more likely to be too low than too high** — a deep single-point dip up
  there is the expected outcome of where the microphone was. Never boost on that evidence, whatever
  the gate says; and the same statistics make a measured peak more trustworthy than a measured dip,
  which is a better argument for cut-first than headroom. `diagnostic-techniques.md` §13,
  `phase_2_eq.md`.
- **The mic-shift test, now with a number attached and a form that survives a hand.** Nine sweeps in
  97 s on one channel: the dip near 800 Hz sat at 800/818/800 Hz across three returns to the centre
  (**1.0 %**) and at 688…1080 Hz across six positions (**9–14 %**). It is the *anchors* that are
  mandatory, not the tripod — without repeats at one position there is no floor to judge the spread
  against. Six positions in the ear ellipsoid, kept separately rather than averaged, because
  averaging is what destroys the signal the test reads. `diagnostic-techniques.md` §13.
- **Near-field against in-car: the cheapest way to tell a driver from its cabin.** Two door woofers
  that measure as a matched pair in near-field (1.55 dB RMS apart) behave from the listening seat
  like different instruments — the near one +9.9 dB at 100 Hz and −8.9 at 160, the far one shelved
  down 9–19 dB from 250 up. Also the corollary that exonerated a pair of enclosures: soft-material
  treatments moved a mid's near-field by 0.23–0.27 dB RMS, i.e. nothing, while the grille and the
  A-pillar cover moved it by 4 and 7 dB. `enclosure-install-diagnostics.md` §4b.

## [v3.0.8] — 2026-08-19 · the reviewer was signed in all along

### Fixed

- **The Gemini sign-in was offered again on a machine that had done it** — still, after the first
  fix. That fix looked at the Antigravity **IDE**'s state file, `~/.gemini/antigravity/`. This
  installer installs the **CLI**, and on a machine that only ever had `agy` there is no
  `antigravity/` folder at all: the user's `~/.gemini` on Windows 11 held exactly `antigravity-cli`
  and `config` (screenshot, 2026-08-19). Two more signals, both read off disk and neither opening a
  credential file: the CLI's own `antigravity-cli/jetski_state.pbtxt`, which records the
  post-onboarding screens that were walked, and `config/projects/*.json`, which is written once a
  project has been chosen — something that only happens after signing in. Checked against four
  shapes of machine, including one that has never signed in, where the sign-in is still offered.

## [v3.0.7] — 2026-08-19 · which REW has the API

### Fixed

- **Nothing in this method measures without REW's API, and the version a web search gives you does
  not have one.** A tester installed REW on Windows from the first search result — the release
  build, V5.31.3, July 2024 — and found no API tab in its preferences at all. The API is in the
  **beta** builds (5.40), whose downloads live at AV NIRVANA, the REW forum. Both READMEs, all four
  languages, and both installers now name the beta and link
  [roomeqwizard.com/beta.html](https://www.roomeqwizard.com/beta.html): in the plan line before
  anything is downloaded, and again in the closing steps — including the case where REW is already
  installed, where the tell is "no API tab at all".
- **A correction to what we told Windows users.** We had been saying Windows REW has no "Start the
  API when REW starts" box and that the Desktop shortcut worked around it. That was never a
  platform difference — it was a version one: the machine we saw had the release build, which has
  no API tab whatsoever. On a beta the panel is identical on both platforms, checkbox included.
  The `REW (API on)` shortcut stays, described now as what it is: one click that cannot be
  forgotten.

## [v3.0.6] — 2026-08-19 · the reviewer can find its own contract

### Fixed

- **The Critic short-circuited with `not_ready` on every clean install, and would have done so
  for ever.** `autosound_ai.py` looked for `data-contract-template.md` in `<project>/rew_analitic`,
  the project root and `$AUTOSOUND_DIR` — and that file is in none of those on a fresh machine,
  because it is the METHOD's document and ships in the skill's own `assets/`. Nothing copies it
  into a project. So the preflight could never pass, whatever the project's state (user, on a
  fresh Windows install, 2026-08-19: the reviewer reported "not ready" on a project that had
  everything else). The skill's own copy is now the LAST place looked, so a project that keeps an
  edited contract still wins. TCC's own preflight was corrected the same way, in the same hour.

## [v3.0.5] — 2026-08-19 · the beta the first outside tester gets

The release that makes 3.x the way in: the front page, the FAQ and all three translations now
describe the one-line install instead of the 2.x plugin, and the installer behind that line has
been run from scratch on a second Mac and on Windows 11 (UTM) the same day, with everything those
two runs found fixed here. Still a beta, and the README says so in as many words: what it has not
had is a full tune driven end to end from the app.


### Fixed

- **A re-run asked what it already knew** (user, 2026-08-19, re-running to pick up the icon fix;
  fixed in `install.sh` first, then mirrored into `install.ps1` before the Windows test).
  The GitHub question came again although `gh` was installed — it is a question about a download,
  so with the command already on the machine there is nothing to decide, and it is skipped (the
  option line still names `--no-github`, so the choice stays visible). The Gemini reviewer offered
  its sign-in on every run, unlike Claude and GitHub either side of it, which check first: there
  is now an `agy_status`, read off disk (never by running `agy`, which is interactive and takes
  over the terminal) — so a signed-in reviewer reports it and the Google setup screens are not
  walked again. **Three signals, not one**: the first version looked only at
  `~/.gemini/oauth_creds.json` and still offered the sign-in on a Mac that had done it — that file
  is the shape Google's own `gemini` CLI writes, which `agy` is a fork of and shares a folder with,
  so a machine with only `agy` on it need not have one. Also read: `agy`'s own state file, which
  records that its setup screens were walked, and `GEMINI_API_KEY`/`GOOGLE_API_KEY`, which the
  reviewer runs on just as well. An account name prints as "signed in as …"; the weaker signals
  print as "already set up" with the command to check it, because claiming a sign-in the script
  cannot see would be worse than one extra line. No credential file is opened for its contents.
- **The Desktop shortcut kept the blank icon even after the bundle was fixed** — it took a Get
  Info to refresh. Finder caches an icon against the item that has it, so a link first drawn when
  the app had no icon keeps that tile. The installer now REPLACES its own shortcut instead of
  leaving it: a link made a moment ago is an item Finder has never drawn, so it asks Launch
  Services, which the builder has just told. Only a symlink pointing at our own app is ever
  removed; anything else on the Desktop under that name is somebody's file and stays.
- **The app on the Desktop had no icon — a blank white tile** (user, 2026-08-19, installing on a
  second Mac from the README's own one-liner). Two causes, both closed. **Launch Services was
  never told the bundle exists**: Finder does not read an `Info.plist` to draw an icon, it asks
  Launch Services, and a bundle a script created seconds ago is not in that database — so the app
  and every alias to it were drawn with the placeholder. `make-macos-app.sh` now registers the
  bundle it built (`lsregister -f`, one bundle, not the minutes-long full rebuild), and the
  installer touches the Desktop shortcut after making it. And **the icon lookup imported the app
  to find a data file**: `import autosound_tcc.app` runs that module's logging and config imports,
  so anything wrong in them lost the icon *silently* (the probe's errors went to `/dev/null`). It
  now uses `importlib.util.find_spec`, which locates the package without executing a line of it.
  The "no icon" note is a warning at last, not an aside in brackets that scrolls past unread.

### Changed

- **omp comes with the app now; `--no-omp` / `-NoOmp` leaves it out.** It was opt-in behind
  `--with-omp`, which is wrong in the one way an option cannot fix: the person who wants omp is
  the person who does not know the flag exists, and a clean install left them with TCC's model
  picker offering two vendors and no clue why (user, 2026-08-19). It follows the app rather than
  the method — `--terminal` never brings it, because a picker for TCC's models has nothing to pick
  for in a plain terminal — and it is named on the one screen that lists everything before
  anything downloads, so consent is still given once, in full. `--with-omp`/`-WithOmp` still work.

### Added

- **The 3.x line is the front page.** README, FAQ and the German, Polish and Ukrainian
  translations describe the one-line install and the desktop app instead of the 2.x plugin. The
  plugin route is kept as a clearly-labelled note that says which line it gives you, and the
  marketplace still pins 2.8.1, so nobody already on 2.x is moved. The translations were
  re-translated from the new English rather than patched — the section structure changed under
  them.

- **REW → Resonalyze: `rew_tool/resonalyze_ir.py` writes a REW loopback-referenced sweep as the
  impulse-response JSON (format v7) that [Resonalyze](https://github.com/DIMOSUS/Resonalyze) saves
  itself**, so a REW-with-loopback measurement set opens in its Virtual DSP / Auto delay / Auto
  crossover with nothing retyped — the file-level bridge offered in
  [DIMOSUS/Resonalyze#86](https://github.com/DIMOSUS/Resonalyze/issues/86) (item 6 — the "second
  cabin" dataset, published in this format as the first set of
  [autosound-measurements](https://github.com/ayukhno/autosound-measurements), the new public data
  repository: per-driver loopback IRs of real cabins, moving-mic RTA, DSP states, hardware facts; CC BY 4.0). Three things the file must get right, and where each was
  checked: the **level** — REW's IR endpoint peak-normalises every IR to ±1.0 by default, which
  silently destroys the level relation between channels (a sub's IR peak really sits ~18 dB under a
  woofer's); the module pulls `?normalised=false` and carries fractions of full scale, so relative
  levels are exact for a set measured at one gain; the **time base** — Resonalyze wants the loopback
  reference AT sample 0 of the transfer IR, while REW anchors its grid on the mic-IR peak (an integer
  sample) and lets t = 0 fall at a fractional index, so the transfer IR is rotated by the exact
  fraction with a linear-phase FFT shift (an integer case stays a bit-exact roll; rounding would
  cost up to 0.5 sample = 1.8 mm, and Resonalyze's arrival estimator resolves ~0.1 sample);
  and the **format** — every document is checked with a field-for-field port of the app's own
  `ImpulseResponseFile.Validate()`, and eight Passat B8 files were then loaded through Resonalyze's
  reader compiled verbatim (`ImpulseResponseFile.LoadAsync`, commit d11186e) and read back by its
  `TimeAlignmentAnalysis` to REW's own delays within ±0.01 ms (2026-08-19). Refuses anything not on
  the loopback base (`timingReference ≠ Loopback`, a timing offset). Each file carries a `rewSource`
  block (title, uuid, REW date and delay, peak dBFS, the shift, the protective high-pass in force)
  that their reader ignores; protective HPFs are NOT removed — Resonalyze compensates them at capture
  time, so a file-based consumer must de-embed, and the manifest says which channels need it.
  `--selftest` (offline, in the smoke test); the two REW facts (peak-normalised default, fractional
  t = 0) are in `rew-api-quirks.md` — the first one had already bitten the 2026-08-18 cross-check
  harness, which summed peak-normalised IRs.
- **A Windows installer that has run on Windows.** `install.ps1` is now the mirror of the
  rebuilt `install.sh` — the same two blocks, the same defaults, the same flags in PowerShell
  spelling (`-Terminal`, `-NoReviewer`, `-GitHub`, `-WithOmp`, `-DryRun`, `-Yes`, `-Uninstall
  -All`, plus `-Log <file>` for a transcript) — and it was run on Windows 11 (25H2, a Parallels
  VM) on 2026-08-17: a fresh unattended install and `-Uninstall -All`, twice over, then the
  interactive form with all three sign-ins (Claude in the browser, agy's TUI, gh's device code) —
  transcripts read line by line. What Windows needs that macOS does not: **Git for Windows** (git for the method,
  Git Bash for Claude Code's Bash tool), through winget or the official installer — the one
  permission (UAC) dialog, once, machine-wide; **a real `python3`**, because Windows ships only a
  Store shortcut by that name — uv installs Python 3.12 with `--default`, so `python3.exe` sits in
  `~\.local\bin` at the front of the user PATH; the method's packages into the user site with
  `--break-system-packages`, since uv marks its Pythons EXTERNALLY-MANAGED and pip refuses even
  `--user` without it; a junction instead of a symlink for the skill (no Developer Mode); Desktop
  and Start Menu shortcuts pointing at TCC's new windowed launcher, with TCC's `.ico`. The upstream
  one-liners (Claude Code, uv, agy, omp) run in a child PowerShell, so an `exit` in their code
  cannot end this script. `install.cmd` (double-click) is ASCII-only now and passes options through.
- **On Windows, a "REW (API on)" shortcut on the Desktop.** REW's Windows API tab has no
  "start the API when REW starts" box — only a Start-server button to press on every launch — and
  REW's own help names the alternative, `roomeqwizard.exe -api`. When REW is installed the
  installer makes that shortcut (its exe found at the default path or through the uninstall
  entry), the Start step points at it, and `-Uninstall` removes only a shortcut that is that
  (user's screenshot of the Windows panel, 2026-08-17). The macOS text keeps the checkbox, which
  exists there.
- What the transcripts caught and the script no longer does: stop to ask "Are you sure?" when
  removing the junction (`Remove-Item` on a junction under Windows PowerShell 5.1; now
  `Directory.Delete`, which removes the link and never the target); paint red
  `NativeCommandError` blocks for git's annotated-tag warning, for `gh auth status` when nobody is
  signed in, and for `import numpy` when it is missing; fail the `gh` download on a machine whose
  `%TEMP%` is an 8.3 short path PowerShell cannot resolve (downloads now go under
  `~\.cache\autosound-installer`).
- **`dsp_math.apf1_response(freqs, f0)` — the first-order all-pass** (SCR-050 item 4,
  2026-08-18). Unit magnitude, −90° exactly at `f0`, 0 → −180° overall; far below `f0` it is a
  pure delay of 1/(π·f0), which is the whole reason the method aligns a joint with an all-pass
  and not with raw delay. Same convention as `apf2_response` — the selftest holds them to
  `apf1² ≡ apf2(Q 0.5)`, the identity two cascaded first-order sections satisfy — so the two stack
  and compare directly. TCC's curve window applies both to a measured trace and draws the
  predicted sum live; the maths lives here and only here.
- **`dsp_math.py selftest`** — the module had none. It pins the all-pass functions to closed-form
  facts (the phase at `f0`, the asymptotes, monotonic lag, the delay far below `f0`) and
  `eq_complex` to its own kinds, so a wrong branch fails on numbers and not on somebody's memory.
- **`analyze-joints --apf "ch,APF2,f0,Q"` (or `ch,APF1,f0`) — a hand-dialled all-pass VERIFIED,
  not proposed** (SCR-050 items 1–2, 2026-08-19). TCC's curve window now lets the Arbiter put an
  `APF1`/`APF2` on a measured driver and watch the predicted sum move; until now that number had
  nowhere to go. Every joint touching the channel gets one more line under its row — the joint's
  worst null as it stands, with the candidate and nothing else changed (the reading TCC showed),
  and with the candidate plus the best further delay — under the same trust gate as the row: no
  measured pair → the candidate is UNVERIFIED too; gate tripped → nothing computed. The selftest
  holds it to a synthetic joint: the right APF2 on the right branch closes a −39 dB null with no
  delay change, the same APF2 on the other branch does not help, and an APF1 on an APF2-shaped
  joint MOVES the null to the top of the band instead of closing it — the exact "fixes it or
  moves the problem" a Critic is asked about. The data-contract package gained an `Origin:` line
  so a hand-dialled candidate enters the review as a candidate, never as something checked; the
  Helix phase ANGLE is deliberately not accepted (one vendor's control, `helix-phase-allpass.md`).

### Fixed

- **`eq_complex` rendered an all-pass band as a HIGH SHELF, silently** (SCR-050 item 5). Every
  band went through `peq_response`, whose kind handling was `PK` → peaking, `LS` → low shelf and
  *everything else* → high shelf, with no guard — so a bank carrying `APF1`/`APF2` (both
  legitimate `EQ_TYPES`) came back as a shelf with no error anywhere; the ledger's own `LSH`
  spelling took the same wrong turn. `eq_complex` now dispatches by kind (`PK`, `LS`/`LSH`,
  `HS`/`HSH`, `APF1`, `APF2`) and **raises on a kind it does not know**, and `peq_response`
  refuses anything but a peak or a shelf. Reachable the moment anything hands a ledger's bands to
  the simulator; found while scoping TCC's all-pass, not reported from the field.

## [v3.0.4] — 2026-08-17 · tagged, not yet the default install

The installer, rebuilt around the person installing rather than around the packages. The one-liner
executes `install.sh` from `main`, so that part is live for everyone the moment it is pushed; the
app-builder fix below travels with this tag, because the clone is the tag.

### Changed

- **`install.sh` asks everything at the start and does the sign-ins at the end — two blocks, nothing
  in between.** A real first install (2026-08-13) had twelve points where the person had to act,
  spread over the whole run: three questions, a RETURN and an admin password twelve minutes in
  (Homebrew), and seven "what to do next" steps. Now: one screen that names every download and
  asks once, the Mac password right after it (only when Apple's Command Line Tools are missing),
  and — after ten to twenty unattended minutes — a sign-in block that runs `claude auth login` in
  the browser for you and offers the reviewer's and GitHub's sign-ins on Enter. `--yes` prints the
  sign-ins as commands instead of running them.
- **Homebrew is gone from the install.** Google publishes `agy` through its own installer
  (`antigravity.google/cli/install.sh` → `~/.local/bin`, quarantine cleared), and `omp` through
  `omp.sh/install.sh`; neither needed a package manager, and Homebrew was the only reason the
  install stopped for a password, needed an administrator, or put a second directory on PATH.
  Every tool now lands in `~/.local/bin`, so one PATH line covers all of them.
- **Apple's Command Line Tools install without a dialog and without a second run.** On a Mac
  without them the old script exited with "run `xcode-select --install` and run this again". They
  are now installed the way Homebrew's installer does it — `softwareupdate` with the one password
  asked at the start, kept alive for the download — and the script continues. Non-administrators
  get Apple's own installer window and the script waits for it instead of exiting.
- **Everything is the default; opting out is a flag.** No "which size?" question: a first install
  gets the method, the TCC app and the Gemini reviewer, because that is the configuration the
  method is written for. `--terminal` leaves the app out, `--no-reviewer` the reviewer, and the
  consent screen says so before asking. `omp` is no longer installed by default (`--with-omp`): it
  is the metered route, offered as an experiment, and the recommended pair does not use it.
- **One optional question, up front: back projects up to GitHub?** (SCR-049 §2.) Yes installs
  GitHub's `gh` straight from its releases and offers `gh auth login --web` in the sign-in block;
  the closing advice is a how-to, not a claim that the method already scripts the backup.
- **Every message re-read as a first-time reader.** Paths print as `~/…`; the reviewer's installer
  is kept quiet unless it fails (its ordinary log lines all begin "ERROR: logging before
  google.Init"); the app installer prints one line instead of thirty-six package names; the
  "Start" screen says what to click and what to type, and the terminal path says to open a NEW
  window instead of explaining PATH.
- **`--uninstall` is manifest-driven.** The script records what it installed
  (`~/.local/share/autosound/installer-manifest`) and `--uninstall --all` removes exactly that —
  agy, gh, omp only when they were ours — plus Claude Code's whole native install
  (`~/.local/share/claude`, `~/.claude.json`), uv's cache, and TCC's own settings and log, which
  a "reset the test machine" run left behind before.

### Fixed

- **The app bundle lost its icon whenever uv wrote a `#!/bin/sh` trampoline instead of a python
  shebang** (long home paths, folders with spaces): `make-macos-app.sh` read the shebang alone,
  found `/bin/sh`, and gave up. It now reads the trampoline's `exec` line and, failing that, asks
  `uv tool dir`. This tag is what carries it to installs — the builder comes from the clone.

## [v3.0.3] — 2026-08-13 · tagged, not yet the default install

What the first from-scratch install on a second Mac found. Every item below was a defect nobody
could have seen on a machine that already had everything — which is what the author's laptop is.

### Fixed

- **Homebrew could never install through the documented one-liner, on any Mac.** The code piped
  `printf '\n'` into Homebrew's installer to answer its RETURN pause, which guaranteed the thing
  it was avoiding: with stdin a pipe, Homebrew announces "Running in non-interactive mode because
  `stdin` is not a TTY", skips the password prompt and dies on "Need sudo access on macOS" — on an
  account that IS an administrator. So the Gemini reviewer, which the installer itself calls
  "where most of the value is", was never installed for anyone who followed the instructions. It
  now gets `/dev/tty` and asks. **The install pauses there for a RETURN and your admin password.**
- **The summary argued with itself.** "autosound-tcc is installed but that folder is not on your
  PATH", and directly under it "your .zshrc already has it — not touching it". Both were true: the
  profile was correct and only the running shell was stale, which is the ordinary state right
  after an install and needs no alarm. It now answers the question a person actually has — will a
  new terminal find it — and says either "installed" or a warning, never both.
- **"What to do next" was a puzzle.** Two of its seven items were the same reviewer setup in
  different words; "open a new terminal" was number 2 while numbers 3 and 7 both needed it done
  first; required steps were mixed in with optional ones. The list is now sorted into "do these,
  in this order" and "when you have time", and the two reviewer paths can only queue one step.
- **`--dry-run` described the machine instead of the plan.** It ended with "Installed, with the
  warnings above" about an install that had not happened, reported a reviewer as "not installed"
  directly under "would run: <the Homebrew installer>", and skipped the list of everything it
  would download — which is the half of a dry run people want.
- **Not being signed in to Claude was reported as a warning**, so a completely successful install
  ended with "Installed, with the warnings above". Every first install on every machine is in that
  state, and the script says so itself two sections earlier.

### Added

- **`omp` is installed in the same Homebrew visit as the reviewer.** It is what fills TCC's model
  picker with anything that is not Claude; without it that dialog opens empty.
- **The summary ends with both repositories** and where to open an issue.
- **The macOS app bundle gets TCC's icon.** The artwork ships inside the TCC package, and the
  builder reads it from the installed package rather than keeping a second copy here.

## [v3.0.2] — 2026-08-13 · tagged, not yet the default install

Tagged without an entry at the time; written up here. Two threads: the installers became real,
and the reviewer channel learned to tell "configured" from "works".

### Added

- **Installers, and the one-liner that runs them.** `install.sh` for macOS/Linux, `install.ps1`
  mirrored from it for Windows — **not yet run on Windows, and it says so in its own header** —
  and `install.cmd` so a double-click or a `cmd` prompt works. `--uninstall` removes what the
  script installed and never a project; `--uninstall --all` also names Homebrew rather than
  removing a package manager it cannot prove it owns.
- **`gemini_critic.sh --doctor`** reports the channel and the project as two separate verdicts, so
  "the reviewer works" and "this folder has not been through intake" stop being one answer. The
  smoke test can now fail: it makes a live one-line call rather than declaring success because a
  binary exists.
- **The enable-the-API step in `setup-critic-channel.md`**, which had never been written down.

### Fixed

- **A project whose state is prose is told what it is**, instead of being sent to redo intake.
- **Reviewer model ids are slugs only.** A caption where an id belongs went to the API verbatim
  and fell back to the clipboard silently.
- **A long series of first-install defects** found by running the script on a clean M1: the PATH
  line written twice, the second directory never added at all, a question asked twice mid-scroll,
  an optional extra taking the whole install down with it, an off-PATH reviewer reported as a
  missing one, `--skill-ref` working on a first install and breaking on every update.

### Changed

- **The 3.x line is no longer described as "in development"**, in all four languages.
- **The catalogue's version number is dropped** — it described the wrong thing.

## [v3.0.1] — 2026-08-13 · tagged, not yet the default install

Everything v3.0.0 said, plus the defects a live audit of the marketplace found in it.

### Fixed

- **The phase 0 gate named a subcommand that does not exist.** `process.py … set-target` appears
  three times in `phase_0_baseline.md` and once in the refusal that sends you there; the command
  is `target`, and `set-target` exits 2 with a usage error. A refusal that instructs an invalid
  command teaches its reader that refusals are noise, which is the opposite of what a gate is for.
  **This is why v3.0.0 should not be installed — v3.0.1 replaces it.**
- **A post-sweep quality gate** (issue #9). `flag_remeasure_candidates` had sat unreachable since
  before 2.8: every capture is now compared against the cleanest capture of the SAME driver, and
  one that is `REMEASURE_MARGIN_DB` (15 dB) worse is flagged by `capture-check`. Relative, never
  absolute — an absolute pre-echo threshold was tried and condemned two good sweeps.
- **A stale reviewer-model label is recognised.** 2.x's own `.critic-env.example` shipped
  `GEMINI_CRITIC_MODEL="Gemini 3.5 Flash (Medium)"`; 3.0 removed the alias table that translated
  it, so the caption went to the API verbatim and the reviewer silently fell back to the
  clipboard. Recognised by shape rather than by a table of names.

### Changed

- **One entry in the marketplace again.** `autosound-tuning-next` is withdrawn: both entries
  shipped a skill with the same `name`, so installing both left two active with near-identical
  triggers and no warning. A machine runs one method. Trying 3.x is a local clone of the tag plus
  `marketplace add <path>` — the same mechanism already documented for staying on 2.x.
- **The installer** (`install.sh`) installs the skill's own Python dependencies up front, which is
  the reason `INSTALLER-TZ.md` §0 gives for having an installer at all.

## [v3.0.0] — 2026-08-12 · tagged, not yet the default install

> Tagged so it can be installed deliberately (`autosound-tuning-next` in the marketplace).
> The default entry still delivers 2.8.1 and will until the pin is moved, which happens
> after a full tuning session has been run on 3.0 end to end.

**A format break, and the line the GUI runs on.** 2.x is unaffected and stays supported: the
marketplace entry names an exact commit, so an update cannot carry an existing install across.
Moving to 3.0 is a decision somebody makes, not something that arrives.

### Added

- **`project.json`** — project-level facts as a machine file, with one home per fact: the car, the
  equipment, the channel roster and its identity, the glossary, hardware controls, and the
  acoustic flaw map (SCR-001/011/014/015/016/017). Channel identity moved here out of the ledger,
  so a rename keeps a channel's history instead of orphaning its captures (SCR-039).
- **`contract.py`** — one whole-project check: every machine file's existence, schema version and
  validity, plus the cross-file questions no single file can answer (a glossary that disagrees
  with a ledger, a profile missing a tier, a spare slot naming a tier that does not exist,
  SCR-042). `--gate` answers the narrower question of whether phase 0 may start.
- **A recorded process.** Capture rounds are written down rather than derived (SCR-034), the
  Arbiter's rulings are events (SCR-030/031), the change and the critique are files rather than
  text retyped into chat (SCR-026/027), and the journal can say a session happened at all.
- **`state/migrate.py`** — the one-way door, as an IMPORT: `migrate.py <old> --into <new>` builds a
  fresh 3.0 project from a 2.x one, carrying the car's current state (channels, their output
  slots, crossovers, delays, gains, polarity, EQ, and the DSP profile). The old project is not
  touched and still opens in 2.x.
- **A GUI**, in its own repository, reading these files: `autosound-tcc`.

### Changed

- **One format number for the whole project.** Every machine file carries `schema_version: 3`, so
  "which format is this project in" is one comparison rather than a matrix.
- **The ledger is tier-aware** and EQ is structured band objects rather than strings.
- **Phases have gates.** A phase does not start on facts nobody recorded: intake must have
  produced its files, phase 0 cannot be left without a recorded target curve (SCR-036) or an
  acoustic flaw map (SCR-044), and phase 1 asks the profile for the facts it is about to use
  (SCR-045). Evidence for a finished step has to RESOLVE — a ledger version that exists, a file
  that exists, a measurement the glossary knows — not merely describe (SCR-035). The reason is on
  the record: a cheap model closed phases −1 to 3 and reported a finished tune, with
  `dsp_profile.json` alone on disk and the Critic never called.
- **The DSP profile's field vocabulary is closed** and enforced. A token no consumer knows renders
  as nothing, so it is refused with the name it probably meant.
- **No default reviewer model, and no table of model names.** A hardcoded default is a model that
  retires; a table is a promise to keep updating it, and neither was kept. The reviewer is named
  or asked for.

### Fixed

- The migration carried six identity fields that no released 2.x version ever wrote, and did not
  carry `helix_ch` — the DSP output letter, the one identity field the released line did use. It
  reported success and left the Slot column empty. Its selftest passed throughout, because the
  fixture was a development shape rather than a released one.
- A 2.x project was reported as one intake had never touched, with advice to run intake — which
  would re-ask what the project already answered. It is recognised and told to import instead.
- The migration was not atomic: `project.json` was written before the snapshots were validated.
- `delay_ms`, the field token 2.x's own examples wrote, is renamed to `ta_ms` on import rather
  than left to fail validation forever.

### Upgrading

Existing 2.x installs are pinned and will not move. To try 3.0, install it deliberately; to bring
a car across, use `migrate.py <old> --into <new>` and keep the old project for its history.

## [v2.8.1] — 2026-08-12

A packaging fix, plus the field notes that landed on `main` after v2.8.0 was tagged.

### Fixed
- **Both plugin manifests now declare the version they actually ship.** `plugin.json` still said `2.6.3` and `marketplace.json` `2.1.2`, so anyone installing the plugin was handed 2.8.0 files while `/plugin list` showed a version two releases stale — and a version-comparing updater would have seen no reason to move.

### Added
- **The AYA competition disc is indexed**, with how to read a resolution track (`competition.md`).
- **The VW Passat B8 card records the signal chain** and what it binds.

### Changed
- The README's model-recommendation section is cut down to what a reader can act on (all four languages).
- Python bytecode caches are no longer tracked.

## [v2.8.0] — 2026-08-01

The last release of the 2.x line, and the biggest field harvest so far: two competition-season tuning arcs, one event, and eighteen sessions folded back in. Also ships the release that v2.7.1 documented but never tagged, and the TCC-integration groundwork that landed on `main` after v2.7.0.

Most of what follows was learned the expensive way — a wrong verdict, a missed gate, a whole arc measured in a configuration nobody listens to. The rules are written so the next build does not pay again.

### Added — measurement method (`analysis-playbook.md`)
- **The two-snapshot rule.** A convention that mutes the centre and disables effects protects series comparability *and* can mean the configuration people actually hear is never measured. On one build the centre's own contribution was +4.3…+5.7 dB and sat outside every tonal verdict of the arc. Each series now carries both the legacy invariant and the combat snapshot; **tonal verdicts come only from the combat snapshot.**
- **Attribute a summed excess before choosing where to cut.** A symmetric cut behaved exactly as modelled on the solo sides and moved the combat curve by nothing — the intermediate snapshot showed the centre alone was +8.0 dB there. For any multi-source excess, capture the middle member first.
- **Discrete test tones are read at the tone frequencies, never as band medians** — a band summarised as "on target, 1.9 dB spread" hid a +3.0 dB peak sitting on a scored tone.
- **Measured group delay ≠ filter group delay.** Modelling the banks before accepting a "consolidate the filters" argument saved five ear-attested wins: the side with half the filter count measured the larger GD, because the bulk was door-null acoustics.
- **Know your own error bars.** Measure the repeatability floor per rig (MMM capture-to-capture, static sweep, 2 cm and 5 cm mic shifts) and quote it whenever a difference is called real. Between-series scatter can run 3-7× the within-series σ when an unrecorded global — master volume, level-dependent tilt compensation — moved between them.
- **A set with no replicate can still have an error bar.** Above the fill channel's low-pass a full-system capture must equal the power sum of the solo sides at the same place; the residual of that identity is the set's internal inconsistency, free and requiring no extra capture.
- **Spread within an MMM traversal can be the signal.** MMM measures a volume, so not holding an exact point is the design. Decompose the residual instead of blaming the operator: narrow notch-like structure = undersampled comb (a real averaging failure), broad-shaped structure = a spatial gradient across the volume, i.e. directivity.

### Added — diagnostics (`diagnostic-techniques.md`)
- **An electrically symmetric move becomes acoustically asymmetric when one side has a non-EQ-able null in the band** — check the filter's skirt against the pair's asymmetry map, not just the target band.
- **Reinforcing a correct localisation cue can expose a defective one and split the image in two.** Read "the image split" as a cue-conflict signature.
- **A differentially-fed fill layer depends on level symmetry to stay silent on correlated content** — its acceptance gate must be re-run after any level change on either side, not only at first entry.
- **Don't accept a band as the mechanism until you've put the band back.** Restoring a suspected cause is cheaper than a new measurement and falsifies more decisively; on one build it killed a model that had been steering work for weeks.
- **A mono mic with no head cannot answer a binaural question.** Use it as a sniper scope to find a resonance frequency; the ear decides the balance.
- **Level asymmetry is the last lever, not the first** — path attenuation is already inside any curve measured at the listening position, and if centring needs more than ~0.5-1 dB of near-side cut the bug is in delays/phase.
- **Choosing the lever:** a broadband channel-gain change drags the crossover region and shifts joint *summation* (a flat gain is phase-neutral — what moves is null depth and joint median, not phase). A shelf placed above the joint reaches the same tonal band and leaves the crossover alone.

### Added — gates and tracks (`test-tracks.md`, `competition.md`)
- **A mono/centred gate cannot catch an L/R level overshoot; pan-extreme tests can.** One state passed band-passed mono pink and failed the pan test in the same session.
- **Gate a centre/fill level on an amplitude-panned track, not natural stereo** — a statically summed centre never goes silent on extreme pans, which is why choir-based attestation hid the defect for months.
- **A moving-source track beats a static one for asymmetry**, and when a source *jumps* rather than glides, separate the author's intent from the system's error by failure shape: all positions shifted one way = level; blurred or doubled = phase/time; position correlating with the source's pitch = narrowband.
- **Disc identity: the number is not the track.** Regional compilations borrow category names but carry different music, and numbering transfers neither between volumes nor to streaming. Always cite `LIBRARY #N + artist — title`; ask and log the user's actual tracks; verify the track↔criterion mapping from the original-language disc description (a translation turned `Höhe` into "pitch" and sent a whole session's height gates to the wrong tracks).
- **Competition process:** changes inside 72 hours of the start need same-day measured attestation or a revert · every listening verdict is recorded with the master position · check every ruleset the event runs, because a defect worth zero points on one card is scored on another · cross-validate the ledger's open risks against the judge's card afterwards — a free external test.

### Added — bookkeeping discipline (`process-control.md`)
- **The record and the hardware drift apart.** Three independent occurrences on one build — an output gain at −5 while the ledger attested +3, a centre gain recorded that existed in no preset, and five harvested lessons filed as "in the inbox" that never arrived. Read the current value off the DSP screen before computing any delta from it, and check a harvest destination actually received what a document says it did.
- **The system state belongs in the measurement, not in memory** — master, sub, effects, fill channel (plus sweep attenuation and mic position when non-standard) go into the measurement's own notes at capture time; titles stay protocol-clean for name-matching.
- **Version identifiers are a namespace** — grep the ledger before allocating one, or two unrelated states merge in every later reference.

### Changed — the reviewer channel
- **The Advisor role now defaults to Pro**, like the Critic. Asked to settle whether a residual was signal or noise, a Flash advisor answered "signal" in one section and "noise" in another of the same reply, endorsing both sides of the only question it existed to answer. Flash remains the automatic fallback when quota is dry, and the fallback now prints a loud warning explaining that a weak round reads like a strong one — treat it as advisory and re-run before banking anything resting on it.
- **A reviewer that contradicts itself is a result, not a failure** — record that the round did not settle the question rather than quoting the half that agrees with the plan. A reviewer that endorses a proposal which re-opens a banked decision is a signal the *package* omitted context.
- Documented that model names drift (`agy models` moved from display labels to slug ids; both accepted as of 2026-08-01) — an unresolvable name is one of the ways the channel returns an empty reply.

### Fixed / documented (`rew-api-quirks.md`)
- **`PUT /measurements/{id}` replaces the notes field**, destroying the capture information REW wrote there itself. Read → filter → append → write back; a state-stamping helper must round-trip and offer `--show` / `--clear`.

### Included from the untagged v2.7.1 and post-v2.7.0 `main`
- `eq_gate.py` provenance rewritten to its real validation and limits, plus `ExcessPhaseGate.s_at(f0)` and a selftest regression lock (documented as v2.7.1 on 2026-07-23; the tag was never cut).
- TCC-integration groundwork: machine-readable process state (`process-state.json` + `journal.jsonl`), measurement naming as code (`rew_tool/naming.py`, matching by parsed identity rather than raw title), `rew_api` timeouts and working write endpoints (`set_filters` fixed, `set_equaliser` takes manufacturer+model, `rename_measurement`), the DSP capability-profile mechanism (`dsp_profile.py`, `community-inbox/dsp-profiles`), and declared Python dependencies (`requirements.txt`).

### Note on the line
2.x is feature-complete and stays supported. The 3.x line — GUI and installer — is in development on a branch; no dates. The READMEs now say so in all four languages.

## [v2.7.1] — 2026-07-23

The excess-phase EQ-ability gate (`eq_gate.py`) got its first formal validation — a 5-block experiment suite in the research project, cross-model verified (Claude + Gemini), verdict `partially_supported`. No behaviour change to the shipping gate; the update is honest scoping plus a regression lock.

### Changed
- **`eq_gate.py` provenance rewritten** from the thin "validated on one build (2026-07-13)" to the real validation and its limits: STRONG as a BLOCK detector (90/90 on an analytic minimum- vs non-minimum-phase ground-truth family at matched magnitude, where any depth-only rule is at chance; 20/25 on the VW-B8 real BLOCK anchors on its own), but NOT a certifier (ALLOW means "no phase objection", not "safe to boost"; permissive-side evidence is n=4, one session). Calibration remains install-specific — prefer advising over hard-vetoing until a second install lands.

### Added
- **`ExcessPhaseGate.s_at(f0)`** — the always-comparable S accessor. `check()`'s `metric` is safe in this class but a subclass adding branches could return a different quantity; aggregating that across cases produced a false "criterion inverts on deep dips" finding in the research suite. Use `s_at()` for any cross-case analysis.
- **Selftest regression lock**: a deep minimum-phase notch (r=0.98) must never be BLOCKed (WARN → mic-shift is acceptable; a min-phase system has ~zero excess phase at any depth, so S stays near the noise floor). Guards against a depth-based null-guard being added later — an experiment did exactly that and demoted 90/90 to 54/90.

### Known limitation (documented, not fixed)
- The gate misses 5/25 real BLOCK anchors on its own — shallow dips where single-point in-cabin excess phase is drift-floor-unstable. Catching those needs a spatial check (does the dip survive a same-session MMM per channel), a future enhancement requiring the MMM to be captured in the SAME session as the sweep. Until then WARN→mic-shift (§13) is the safety net.

## [v2.7.0] — 2026-07-22

Curve-visualizer release: a deviation-analysis panel, and an audit that made its numbers reproducible.

### Added
- **Deviation analysis in the curve visualizer:** a new "Analyze" panel picks a Baseline (reference) and a Compare curve — same math for Measured-vs-Target or two ALL runs before/after a change — and computes an autonomous, no-AI band-by-band deviation report: broadband tilt (100 Hz–8 kHz fit), coverage %, Broad-tonal and Narrow-structure grades, and per-band PEAK/DIP/NULL features. Reuses the existing 10-band `FREQ_BANDS`/`BAND_TREND` grid and computes "instruments affected" live from `BAND_INSTRUMENTS`, ranked by octave-overlap share (fundamentals first, harmonics only backfilled when fewer than three fundamentals match). Level is aligned by default (median 300 Hz–3 kHz anchor + manual fine-tune, since gain is always re-optimized separately) so the report reads shape, not gain. A delta-bar strip renders under the main chart on a fixed ±10 dB scale, and the two analyzed curves are drawn with the same smoothing and level shift as the report, so chart and report always agree. No L/R comparison — without time-alignment there is nothing actionable in an L/R difference.
- **Boost advice gated on what an EQ can actually do.** Q = √(2^N)/(2^N−1), so a deficit tighter than Q 3 is never offered a boost, one deeper than 3 dB is capped at "about 3 dB at most, leave the rest", and only a low-Q deficit within 3 dB keeps "a gentle wide boost is fair". Cuts are unchanged — a cut is always physically safe. The Q a tuner would dial is printed on every feature row.
- **The panel states its own precision.** The report is re-derived at three further sub-bin grid offsets (nothing physical changes when the grid starts a fraction of a bin higher), and each Δ and the coverage figure carry the observed half-spread. Fully offline, ~29 ms.
- **Reference-track links in the band table:** a "?" badge next to an instrument opens the EMMA test-track references for it, but only where the instrument matched on fundamentals.
- **Rotating tips box** at the bottom of the page, and hover/click explanations on each verdict tile.
- **Instruments overlay:** a panel (grouped Vocal / Percussion / Strings / Winds / Keys & Other / EMMA 2024 / EMMA 2026) draws up to 5 instruments' ranges on the chart — fundamentals solid, harmonics lighter — with per-instrument EQ tips. Selection persists.
- Per-curve **color pickers** and a **"Clear" loaded-curves** button (see v2.6.3 visualizer).

### Fixed
Audited by re-running the same measurement under combinations of equally defensible arithmetic choices that change nothing physical, and measuring the spread. Every feature is now reported in every run (the largest deviation in the reference measurement, +8.1 dB at 40 Hz, was previously detected 8/8 and shown 4/8), and the arbitrary component of each printed dB figure fell 3–4×. Full method and findings in `deviation-analysis-audit.md`.

- Features are cut on an absolute significance floor instead of a top-8 cap, which silently dropped 1–2 real features per run.
- Severity rebalanced: mild width factor instead of a 4× swing, softer and symmetric low-frequency weighting, no blanket dip penalty — a wide shallow HF ripple can no longer outrank a deep hole.
- Prominence is true topographic prominence. The old fixed ±4-bin probe rejected any feature on a broad base however large: a +4.2 dB peak at 554 Hz measured 0.60 dB against a 1.0 dB gate and never reached the report, and its band was then skipped as "within tolerance" because the mean of a +4.2 / −4.1 swing is +0.07 dB.
- The smoothing window is sized by index, not by comparing frequencies — the float boundary made a 1/6-oct pass use 5 taps on some bins and 2 on others, injecting ripple into the signal the detector reads. Out-of-range taps use an odd extension (20 Hz edge bias +0.27 dB → 0.00).
- The level anchor is a median rather than a mean; the mean was dragged by the very notches being measured, and defensible estimators spread over 1.28 dB.
- Curves are resampled onto the analysis grid by bin-averaging, not point-sampling, which threw away every other point of a 1/48-oct export. This also normalises whatever resolution a file arrives at to the grid's own 1/24 oct.
- Smoothing is fixed at 1/6 oct and the dropdown is gone. Width grows with smoothing and width alone separated NULL ("never boost") from DIP ("a gentle boost is fair"), so a setting picked for how the graph looked flipped the advice on the same notch.
- The context test is gone — topographic prominence already rejects what it was added for, while it compared against absolute zero and so let a 1 dB level nudge add or remove real features, hiding a genuine −4.1 dB dip at 678 Hz.
- The detector's extremum window is clamped at the array ends instead of skipping them; a feature was previously impossible below 22.45 Hz and above 17.7 kHz.
- The "Resonance control" grade counted narrow peaks only — one feature decided it while two −6 dB nulls contributed nothing and it still read "Excellent". Now counts every narrow feature and is named "Narrow structure" for what it measures.
- Band rows with no feature must clear the same ±1.5 dB tolerance as everything else, so no row is printed without something to act on; the footer says "average within", which is what it actually tests.
- Rows within a band are ordered by frequency, matching the chart.
- Large exports are condensed onto a 1/96-oct grid above 3000 points (a 96k-point sweep cost ~2 MB of localStorage against a ~5 MB budget); `interpY` binary-searches instead of scanning, since it runs per dataset on every mouse move.

## [v2.6.3] — 2026-07-21

Curve-visualizer release: the target-curve visualizer became a standalone, shareable tool, and the bundled curve was renamed for trademark safety.

### Changed
- **Renamed the bundled target curve `EMMA-Ref v3` → `SQ-Comp-Ref`** (character tag `Tight-Sub Edition`). "EMMA" is a registered trademark of the European Mobile Media Association; the curve is our own, developed in-house, so the name is changed to avoid implying any affiliation. The file is now `curves/SQ-Comp-Ref_0db_REW.txt`; references and the visualizer's built-in curve, descriptions, and match token were updated across all languages. Curve data is unchanged. The description now states it's our own in-house curve and reframes "juicy" as a deep-but-controlled low end.

### Added
- **Standalone curve visualizer** (`_curve-visualizer.html` at the repo root, served via GitHub Pages): 4-language UI (EN/UA/DE/PL), light/dark and wide/narrow toggles, a Flat reference curve, an editable normalization offset on import, per-curve color pickers, a "Clear loaded" button, right-click frequency-character guide (boost/cut characters, per-band descriptions, example instruments, band + octave width), and a curve-comparison table that reads the difference between curves as a relative tonal trend (not an absolute defect). The hover tooltip lists every visible curve. All descriptions and translations were reviewed via the Gemini advisor.
- **`promotion/`** section with the launch post; **FAQ:** "Can I build my own target curve?"

Field-harvest release from three sessions (2026-07-16/17/19: center realign + Chebyshev O2 + tone-ladder vT1; gain structure vG1/vG1.1; stage/bass session v4.5 + pan/piano rounds vP1/vP2). Twenty-two confirmed lessons folded. No engine changes.

### Added
- **`diagnostic-techniques.md` §27–33:** the ghost-overshoot arbitration ladder (deltas vs a single baseline lie on steep interference structures; repeat → bank check → solo bypass protocol → baseline 1/12 structure); band-limited pair arrival is ill-defined (four estimators, four answers — decide by summation coherence); the consolidated drift-floor family (solo ratios unreadable near corners/skirts; HF gain work by pair-average); measurement-frame discipline (differential ops immune to constant setup errors; arithmetic over noisy medians; group-delta sanity vs the contributor's own level; anchor circularity); pan collapse as a frequency seesaw of solo sides; the amp gain-structure field kit (RCA-pull, XO-bypass noise locator, per-pair knob ceiling, global preset invalidation, relative aux gains); complementary-center corner re-solve after any overlapped-branch change + the guard-dip cap.
- **`staging-depth.md` §9:** a trunk sub localizes on SUSTAINED bass only, and only above its calibrated level (precedence vs steady-state energy); the ±6 dB bass-image stability window; road-masking as the owner-vs-judge divergence mechanism.
- **`review-loop.md` triage additions:** re-anchor the critic's claims against the ledger (hallucinated hardware params deep in a round); compute the NET differential filter stack, sign included, before accepting "asymmetric EQ ruins phantom phase" (a counter-sign cut UNWOUND net pair phase 9.8° → 6.8°).
- **`SKILL.md`:** settings sheets carry ABSOLUTE target values only (relative phrasing caused a 3 dB hardware/ledger fork); in-car session close = an explicit EXIT CHECKLIST (revert test values, knobs, backup).
- **Helix Ultra S profile:** RTC is global (presets don't switch it), Director/Conductor knobs are not stored in `.pct6`, RTC anchors vs applied values, the foolproof flat-point master config; RTC OFF on every measurement series.
- **B8 car card:** the coherent presence valley (EQ-liftable, with the measured escalation criterion), position-sensitive left cold lobes + the hot 990–1250 lob (piano wander / bass left-drift mechanism), bass-pan seesaw items — all verify-only.

## [v2.6.1] — 2026-07-15

Field-harvest release from a full in-car session (bass form → HF edges → rear-fill, driven by Fable 5 with Gemini 3.1 Pro as Critic): seven confirmed lessons folded into doctrine and device knowledge. No engine changes.

### Added
- **Rear-fill worked example in Phase-5 §6** — the doctrine recipe validated first-pass on a live build: differential ±50% feed on the DSP's virtual channels, HPF 315 / LPF 4000 LR24, per-side Haas delays from MEASURED arrivals (+~9 ms, sides differ when the rears sit asymmetrically), one PK flattening the rears' own hump. Plus the practical rules that made it work: **verify the matrix with correlated pink (rears must go SILENT; a positive test needs decorrelated material)** and **judge level by MUTE-CONTRAST, not by hearing the rear** — a correct differential rear is nearly inaudible as a source.
- **`staging-depth.md` §8 — bass-image height & sub forward-masking live in the front's upper-bass (130–500):** cutting 250–430 on the pillar-lit side steals the bass image's height (fix the L/R disease per-side, restore height with a small symmetric in-band PK on the mid PAIR — field result "sub on the hood"); over-cutting the front's 130–250 punch unmasks the trunk sub (it localizes rearward) — suspect the front anchor before touching the sub.
- **Phase-2 rule: score the package's SUMMED curve per channel** — overlapping PK skirts stack (live case: −5.1 dB delivered where −3.5 was intended, audible regression); compute the product of all new filters (`dsp_math.peq_response`) before issuing a settings sheet.
- **THD null-artifact disqualifier** (Phase-0 flaw-map item 4 + `rew-api-quirks.md`): in a deep null the fundamental collapses while harmonics radiate outside it → THD % explodes with a QUIET fundamental. Read the fundamental-dB column next to THD % — a spike counts as mechanical only at a healthy fundamental. Resolves the B8 card's "4.8 % @ 160 Hz" verify item: **mechanics cleared**.
- **`review-loop.md` — critique triage: verify NUMBERS by script, adopt PHYSICS as redesign.** Both live rounds: the critic's numeric predictions lost to a one-script check against measured data, while its physical-mechanism objections (direct/reflected balance; split the correction across both sides) reshaped the final package for the better.
- **`setup-critic-channel.md` — keep the mirror's context CURRENT:** a stale `autosound_context.md` copy made the Critic police ghosts ("context drift" flagged on a correct statement); reconcile the mirror with the live ledger (dated ADDENDUM) when assembling `PROJECT_MIRROR`.
- **Helix Ultra S profile:** delays up to **20.82 ms on BOTH output and virtual channels — they SUM** (enter in one layer only); virtual-mixer legs take **signed percentages** → true differential rear feed works; **RearRC** (Conductor) = live rear-level knob on the `[RearATT]` virtuals — a ready-made ear-ladder.
- **B8 car card:** near-side 250–430 excess carried by BOTH branches (w and m) — check both before assigning it to one; rear-fill worked config (verify-only).

## [v2.6.0] — 2026-07-14

"How we look" release — three of the tuner's seeing disciplines turned into tools and wired into the phase pipeline, all validated on live data the day they were built. Headed to AYA/EMMA with the source build.

### Added
- **IR-start triangulation + ETC/Step helpers** (`analysis.arrival_triangulate` / `etc_envelope` / `step_response`): the honest resolution of "REW never finds the right start" — for a band-limited driver a single start does NOT exist; the tool measures four estimators (peak, −20/−30 dB edges, ETC peak) and returns TRUSTED/ILL-POSED from their spread (measured: clean mids 0.06 ms; door midbass 2.8 ms; sub 13 ms). ILL-POSED routes to xcorr-for-pairs / summation-for-joints instead of any single onset. Step response documented as LF-character visual only (live data: step "polarity" disagreed between identically-polarized mids — §9 stands).
- **Distortion floors in the flaw map** (`rew_api.get_distortion`, endpoint verified live): THD-vs-frequency comes free with every sweep → Phase-0 flaw map item 4; Phase-1 crossover corners now require low MEASURED in-band THD with margin (replaces datasheet-only floors). Source-build payoff: mid-R 18 % @ 100 Hz → the 460 Hz HPF margin became a measured fact; a 4.8 % in-band spike at 160 Hz on one woofer surfaced only through this table.
- **Phase-0 §3.5 "Acoustic Flaw Map"** — the flaw-analysis math is now a prescribed EARLY step (mandatory for a new car; redo on a changed install), built from the SAME raw `_1` baseline with no extra measuring: per-channel EQ-ability map (excess-phase versions → `eq_gate`), per-pair coherence maps + the >1-rotation multipath test (§26), and `curve_view` three-distance reads. The map BINDS downstream: Phase-1 crossover corners avoid multipath pockets/non-min-phase zones (new bullet in §3), Phase-2 EQ passes the gate structurally (`boost_gate=` wired into the "Never Fill Nulls" rule), imaging work knows what is electrically unfixable before chasing it.
- **`rew_tool/curve_view.py` — multi-scale curve viewer with doctrine routing** (from the user's "look at curves from different distances" insight, 2026-07-14): band window → MACRO trend (1/3 oct, band-anchored) → FINE residual (1/24 − macro) with FWHM-measured features, each routed to the doctrine that owns it (broad → voicing §6; narrow-on-sweep → verify-first §13; medium peak → point-EQ cut §21/§2; medium dip → null-suspect §2/§13; `source='mmm'` skips the verify-first arm). Replaces a pattern that had been hand-rolled ~8 times in one project's ad-hoc scripts. Smoke-tested on real data: it independently rediscovered the mid-pair decorrelation pocket structure (657-dip/788-peak) from the ALL curve alone.

## [v2.5.1] — 2026-07-14

Field-harvest release: everything learned in the v4.x/vC1 arc after v2.5.0 — the robust joint-phase objective, the excess-phase boost gate, the validated center-fill remedy — plus scipy soft-degradation so the new modules never brick a lean install.

### Added
- **scipy soft-degradation in `rew_tool/dsp_math.py`**: scipy is imported lazily and ONLY by crossover design (`xo_response`); PEQ/shelf/APF responses, alignment, APF search, robust metrics, greedy EQ fit, and the whole `eq_gate` are pure numpy and keep working without scipy. A missing scipy now raises one clear actionable error at the crossover-realization call instead of an import-time crash of the module (verified by an import-blocked smoke test); the `eq_gate` selftest skips gracefully (scipy there was test-only).
- **Jitter-robust joint-phase objective in the API** (diagnostic §24 made executable): `dsp_math.robust_worst_null` + the field-validated `ROBUST_PERT` set (±20 µs / ±0.5 dB); `apf_search(robust=…)`; `repair_joint_apf` now **defaults to robust scoring** (`robust=False` kept only to reproduce legacy razor runs); new `repair_joint_apf_multi` selects an APF across several same-day snapshots by MIN of the robust score (razor optima measured collapsing −19→−35 dB across one hour) and reports `per_snapshot_db`. Selftest pins the API contract (jitter can never beat the clean point; robust repair ≥ razor repair under jitter) — the chaotic-collapse phenomenon itself is field-validated, not synthetically reproducible.
- **Center-fill validated as MEDICINE for measured pair decorrelation** (the diagnostic §26 remedy arm is no longer provisional): the complementary band-limited center — corners at the measured pockets, deep trough over the healthy zone, quiet level, alignment solved on the SHAPED response — measured +4.4/+2.3 dB pocket recovery, ≤1.8 dB comb, and passed listening gates (head-turn-stable center, no LC/RC pull-in, released width). The classic 400–1200 shape failed the same gates everywhere. B8 card carries the worked config as verify-only data.
- **`rew_tool/eq_gate.py` — excess-phase EQ-boost-ability gate** (the peak-vs-null doctrine made quantitative): `ExcessPhaseGate` built from a driver sweep + REW's native excess-phase version vetoes boosts only where a deep local dip ∧ phase anomaly ∧ real delivered gain coincide; three-state ALLOW/WARN(→ mic-shift cross-check)/BLOCK; plugs into `greedy_eq_fit(boost_gate=…)` / `realize_driver(boost_gate=…)` (both grew the parameter; `realize_driver` also gained `no_boost_zones`). Calibration provisional — reproduced 7/7 of the source build's real boost history (3 known violations caught, 4 working boosts passed); synthetic selftest: near-identical r=0.95 vs r=1.05 reflection combs (min-phase ALLOW / non-min-phase BLOCK). Design lessons in the module docstring: point |z| zero-crosses at a bipolar notch center (use sliding-RMS S); working-region max over-blocks wide filters whose skirt clips a bad zone; phase alone carpets 30-50 % of a cabin's band — the magnitude conjunction is essential. Rule 6 added to `filter-types-car-audio.md` §Acoustic-plan-first.

## [v2.5.0] — 2026-07-13

Harvest of the AutoSci "v3 acoustic-target" research arc (crossover realization → joint alignment → hardware attestation on the Passat B8 / Helix Ultra S) plus the same-day v4.x joint/imaging/voicing loop.

### Added
- **`rew_tool/xover_select.py` + `rew_tool/dsp_math.py`** — crossover-realization & joint-alignment API (realize_driver / select_neighbor_pair / align_joint / repair_joint_apf / lr_phase_tracking), REW-exact filter math, `--selftest` green. New dep: scipy.
- **`filter-types-car-audio.md` §Acoustic-plan-first** — the six validated "v3" selection rules (acoustic plan first; two measurement spaces; joint-aware pair selection; analytic delay/polarity; APF repair discipline; L/R symmetry reformulated as an ACOUSTIC requirement with a phase-tracking metric).
- **`diagnostic-techniques.md` §23–25** — per-pair imaging TA (never one constant side shift); session-local + jitter-ROBUST joint-phase solving (incl. the single-variable same-session A/B protocol for verifying DSP filter implementations, and the low-Q≈delay degeneracy trap); the delay+APF package rule (+ APF rotation reach ~f0/Q; post-repair energy bump belongs to virtual EQ). Plus §1: series-level level-comparability; §13: point-sweep spikes must survive MMM before EQ.
- **`staging-depth.md` §1** — provisional: a joint-coherence repair raises the stage (height/forwardness); rebalance the foundation, don't undo the repair.
- **`knowledge/approaches.md`** — the acoustic-plan-decomposition scheme (field-confirmed, one build).

### Changed
- **`knowledge/dsp/helix-dsp-ultra-s.md`** — a virtual SUB channel EXISTS (user-verified; the old "Front L/R, Center, Rear only" was wrong); AP2 hardware-verified ≡ textbook APF2; LS_Q/HS_Q(Q=0.71) ≡ RBJ S=1; REW modeling target = Generic Extended (20 slots).
- **`helix-phase-allpass.md`** — explicit AP1/AP2 EQ-bank section with the hardware-verification protocol and the high-Q-only verification caveat.
- **`rew-api-quirks.md`** — Generic Extended push schema (crossover shapes + slopedBPerOctave, shelves with q, "All pass" with q), the predicted-response smoothing leak, and the REW↔model filter-math equivalences (Bessel `norm="mag"`).
- **`knowledge/cars/vw-passat-b8-sedan.md`** — PART B: tri-pair 1.28 ms left-early arrival; mid-pair 117° phase divergence at identical settings; pair mono-sum suckouts (Ws 175 / Ms 501); tweeter non-min-phase 2100–2800 zone; the 2026-07 "v3" electrical set as a second crossover data point.

## [v2.4.1] — 2026-07-11

### Fixed
- **Trigger phrases for impedance/T-S/box-design restored in the skill `description`** — a false negative on "REW impedance jig / added-mass method" traced back to the 2026-06-27 ultra-compact router rewrite (`532dbb4`), which dropped phrases an earlier commit (`20ab543`) had added; the later `v2.0.1` restore covered casual-EN and create-curve phrasing but missed these. Additive-only restore (cannot reduce existing recall). Caught by `run_trigger_eval.py`.

### Changed
- **`--doctor` output now shows per-role models** — was one collapsed `model=` field; now shows `critic=` and `advisor=` separately, so the Pro-critic default (added in v2.4.0) is actually visible when diagnosing a solo-Gemini setup.

## [v2.4.0] — 2026-07-11

Simplification release, driven by a full external audit (`audit-fable-2026-07-11.md`) of a felt regression: sessions had become slow, over-cautious, and micro-stepping. Root cause: the always-loaded core had been optimized for the *worst* driver (solo-Gemini countermeasures) and thereby taxed the best one — SKILL.md had grown 1.1k→3.6k words with doubled defensive-tone density.

### Changed
- **SKILL.md cut to ~1.4k words (was ~2.6k after two earlier passes, peak 3.6k).** Guardrails compressed to 1–3 lines + links; reference-map descriptions shortened; Model Selection table folded into `process-control.md` §1. Frontmatter (triggers) untouched.
- **Review cadence: ONE reviewer call per round is the default.** Package the round's whole batch (crossovers+levels, or the full EQ plan) → one critique pass → Arbiter. TWO-PASS anti-anchoring is now an **escalation** — phase gates (Phase-1 strategy, Phase-3 verdict) or after the reviewer fully agrees twice in a row — not the per-decision default. 3 rounds = ceiling, expectation = 1 (`review-loop.md`, `process-control.md` mode A).
- **Phase-2 gate: one critic checkpoint on the round's full package** (a second, after 2b, only when joint alignment was reworked) — was two mandatory checkpoints.
- **Critic wrapper defaults to Pro** (`gemini-2.5-pro` / `Gemini 3.1 Pro (High)`): a Flash critic praises and misses obvious problems; "don't praise" prompt text doesn't fix a too-weak model. Flash remains the advisor/routine default and the quota fallback (`setup-critic-channel.md` §2).
- **Cadence contradiction fixed:** `happy-paths.md` path C rewritten round-based (was "propose one change"); data-contract §3 field is now «Пакет пропозицій раунду» — the package format no longer structurally enforces one-change-per-review.

### Added
- **`references/core/driver-discipline.md`** — the anti-confabulation ruleset (pull-based control, "done costs a path", behavior→countermeasure table, wrapper-only self-critique) split out of the always-loaded core. Loaded **only for solo drivers (modes B/C)**; a mode-A Claude driver no longer reads solo-Gemini policing every turn. `process-control.md` §2/§3 replaced by a pointer.
- **`scripts/start_gemini_tuner.sh`** — one-command solo-Gemini (mode C) launcher: writes a hydrated `GEMINI.md` (operating instructions + `driver-discipline` pointer + ▶️ CONTINUE block + `dsp-state-current` snapshot) that gemini-cli auto-loads; `--refresh` regenerates it after `/clear` or an applied change. Moves "re-read the state" discipline from model memory to infrastructure. (Adopted from Gemini's self-review, audit §8.)
- **Solo self-critique rule:** for round packages and phase gates, self-critique goes through a **stateless `gemini_critic.sh` call on the model's own package** (clean context + contract §4 format) — never in-context "now imagine you are a strict judge" (that shares every anchor and produces praise). In-prompt self-critique only for routine micro-decisions (`driver-discipline.md` §2).
- **`scripts/skill_metrics.sh`** — complexity guard for the always-loaded core: SKILL.md ≤1500 words, defensive markers ≤15, cadence invariants present, no driver-discipline leakage. Run before a release; fails → trim, don't ship.

## [v2.3.2] — 2026-07-11

### Fixed
- **`.github/FUNDING.yml` no longer lists the Monobank jar under `custom:`.** GitHub's `custom:` field has no label option — it always renders the raw URL as link text in the repo's "Sponsor this project" sidebar widget, unlike `github:`/other predefined platforms. With GitHub Sponsors now covering the native widget, dropped the unstyled raw-URL entry rather than live with it. The jar is unaffected as a channel — still offered with proper text in README and the session-close donation ritual (`feedback-loop.md` §D).

## [v2.3.1] — 2026-07-11

Docs-only follow-ups plus a funding-channel activation.

### Added
- **`project-intake.md §4` — Level 0, light-touch entry.** The DSP capability levels (1/2/3) answer "what CAN you do"; Level 0 answers "how much do you WANT to do this session" — a small fine-tune of an already-working system can start from just the current measurement + target, skipping a full DSP dump/reverse-engineer. Guards the one real risk (double-correcting blind to existing filters) by still requiring a per-channel filter read before editing that channel's EQ, and stays re-entrant into Level 1/2 if it starts fighting something unseen.
- **GitHub Sponsors activated** (`github.com/sponsors/ayukhno`, approved 2026-07-11) as a second funding channel alongside the Monobank jar — `.github/FUNDING.yml`, the session-close donation ritual (`feedback-loop.md` §D), and all four README locales updated.

### Changed
- **README (all four languages) now notes the trigger needs a domain word** — a bare `resume` won't wake the skill (too generic); include "car-audio"/"tune" or the local-language equivalent.

## [v2.3.0] — 2026-07-11

A speed audit of the measure→analyze→correct→measure cycle (mass measurement/analysis, not sacrificing precision) plus a from-real-incident bugfix and an always-loaded token diet.

### Added
- **`rew_tool.py analyze-batch "<pattern>"`** — mass analysis of every measurement matching a pattern in ONE consolidated deviation matrix (per-driver band means vs per-band target + `anchor` + `ripple`). One `get_measurements` + one FR-only `get_fr` per driver instead of the interactive REPL's 5-endpoint fan-out — ~5× fewer round-trips, one table instead of N dumps. Same `analysis.py`/`target_curves.py` math, only orchestration + rendering are new.
- **`rew_tool.py analyze-joints`** — mass joint analysis (Phase 2b): every adjacent joint in one pass (polarity · drift-immune delay via `align_by_summation` · residual null · APF f0/Q), reusing `joint_analysis.py` unchanged. Honest by construction — a computed delay/APF is emitted only when a measured `pair` reproduces the complex solos (`phase_trust_gate`); no pair → `UNVERIFIED`; gate trips → `BLOCK`, no delay, fall back to the magnitude power-sum verdict. `--from-state` auto-derives the whole joint map from the active slot's crossovers in `state/` (no hand-typed `lo,hi,fc`).
- **`rew_api.py` measurement-processing wrappers** — `excess_phase_version(mid)` / `minimum_phase_version(mid)` create REW's native `-EP`/`-MP` versions (read the excess phase back via `get_fr`) — the authoritative min- vs non-min-phase decision using REW's own Hilbert, not a home-brew scan. `set_smoothing(mid, '1/6')` applies REW's own smoothing before a pull instead of the `perceptual_smooth` approximation. `POST /measurements/{id}/command` (processing an existing measurement) is a different namespace from capture (`/measure/*`) and is **not** Pro-gated — verified live on REW 5.40 / API 0.9.5.

### Fixed
- **`target_bands.py` now warns when a channel's config matches the module's `_DEMO_CFG` exactly** (`UserWarning`). Real incident: a project's committed per-band target curves turned out to be generated from the demo's placeholder crossovers/gains (e.g. a tweeter HPF knee at ~3500 Hz instead of the project's actual 1000 Hz) — silently, because nothing warned. `phase_1_foundation.md` Step 5 now states explicitly that per-band targets are a DERIVED artifact of the current crossovers/gains, to be regenerated on every crossover/gain change, never left stale or generated from demo values.

### Changed
- **`SKILL.md` always-loaded surface trimmed ~21%** (7133 → 5610 tokens; 185 → 157 lines) without dropping any rule — rebalanced by scope (universal stays in SKILL.md; phase-specific moves to its phase file, loaded on-demand by the sliding-window protocol) and criticality (critical rules stay full; non-critical collapse to a pointer). Start-only guardrails (Verify Banked Decisions) moved into the Pre-Session/Resume steps; refactor-only ones (the 5-step Skill Maintenance Loop) moved to `feedback-loop.md`.

### Explored and consciously dropped
- **Automating measurement capture over the REW API.** Verified live that `POST /measure/command {"command":"SPL"}` does fire a sweep and `/measure/naming` does name it — but every capture/control POST requires a REW Pro license (free tier returns `401`), and more decisively, the mic is placed/held by hand (MMM = moving mic) regardless, so auto-triggering a sweep saves nothing. Analysis stays API-driven (GET); capture stays manual. Documented in `rew-api-quirks.md` so this isn't re-explored.

## [v2.1.1] — 2026-07-05

Curve-visualizer fixes, found live by a user dropping curves into `curves.html`.

### Fixed
- **Manual level-offset lost/doubled on reload.** The offset was tracked only in a closure-local JS variable that reset to 0 every page load, decoupled from what was actually baked into the persisted data/label — so the display lied ("0.0 dB" on an already-shifted curve) and nudging it again stacked on top of the old shift instead of replacing it. Offset now lives on the dataset object, is persisted explicitly, and old (already-broken) saved state self-heals via a label-suffix parse fallback.
- **No way to remove a dropped curve.** Added a delete (✕) button per loaded-curve card; card wiring switched from a captured array index to a live dataset reference so deleting one card can't desync another's toggle/offset handlers.
- **Delete button hidden behind the next card on long names.** An unbreakable underscored filename in the flex title row refused to shrink (no `min-width:0`), overflowing the row and pushing the button past the card's edge, where the next grid cell's own background painted over it — clicks landed on the neighboring card instead. Fixed with `min-width:0` + `overflow-wrap:anywhere` on the label and `flex-shrink:0` on the dot/button.
- **Drag-drop hint text overlapping the card grid.** `#dropZone` and the "клац на картку" hint lived inside `.chart-wrapper` (hard `height:500px` for the canvas), so they overflowed past the box into the same band where `.info-grid` starts. Moved both to be normal-flow siblings instead.
- **`curves.html` too hard to find.** New-project intake (`project-intake.md §5`) now symlinks it at the project root, not just the skill root.

## [v2.1.0] — 2026-07-04

State substrate + field-harvested phase/summation tools + license cleanup + dogfood-informed process control. (Authoritative version of a checkout is `plugin.json`; the unambiguous identity of a build is the commit hash.)

### Added
- **Versioned hard-params state** (`rew_tool/state/state.py`) — one JSON snapshot per change (crossovers / gains / TA / polarity + EQ pointers); `snapshot` / `diff` / `revert` / `render`. ms is canonical, samples derived at the DSP's rate. Anti-drift anchor + cheap A/B / revert / resume.
- **apply-change** (`rew_tool/state/apply.py`) — `propose` → banks a 🟡 snapshot + emits the human settings sheet (channel/param old→new, ms+samples); `attest` → 🟢 applied (proposed-vs-applied).
- **Side-effect gate** (`rew_tool/gates/side_effect.py`) — outbound actions run an exact command with the repo **hardcoded** + returned-URL verify (FAIL LOUD); kills the confabulated-repo failure. **Dedup guard:** an identical-title open feedback issue newer than 24 h → loud SKIP instead of a double-post (a real #3/#4 double-fire, 5 s apart).
- **Pre-sweep safety gate** (`rew_tool/gates/presweep_safety.py`) — refuses a sweep on an unprotected fragile driver (HPF ≥1.1×Fs @≥24 dB, level, clip).
- **`rew_tool/joint_analysis.py`** — within-session summation / TA / phase logic: `joint_summation_check` (measured pair vs incoherent power reference → phase cancellation vs tonal dip; never boost a null), `phase_trust_gate` (do the complex solos reproduce the pair? if not — block delay/APF/polarity), `flag_remeasure_candidates` (dirty-sweep detection: pre-echo vs the cleanest capture of the SAME driver; validated 5/5 on field ground truth), `timing_drift_audit` (REW label-drift vs a real TA change — ~0.13 ms drift measured even WITH loopback), `align_by_summation` (drift-immune polarity+delay from the coherent sum), `allpass_for_residual_null`, `shelf_vs_bell`, `impulse_polarity`, `perceptual_smooth`, `midband_level_anchor`.
- **`rew_tool/spot_check.py`** — independent verification of a model's cited numbers against live REW (levels at cited freqs, L−R deltas, actual band peak vs the claimed one, anchored deviation vs target). Field-proven double duty: confirmed honest numbers to the hundredth AND caught a filter aimed at 2450 Hz when the measured peak sat at 2202 Hz.
- **`references/core/process-control.md`** — the Arbiter's operating modes (**A** Claude+Gemini-Advisor with mandatory advisor nodes · **B** Claude solo · **C** Gemini solo with process risk consciously accepted) + the pull-based playbook (tool-emitted settings-sheets only; "done" costs a path; spot-check before applying; reviewer runs OUTSIDE the driver session).
- **Offline target-curve visualizer** (`curves.html`) + **`rew_tool/equal_loudness.py`** (ISO 226 sub-bass targeting); review-loop full-transcript logging. Visualizer: **localStorage persistence** (imported curves, show/hide selection and per-curve level survive refresh), **group imports share ONE common offset** (mono/stereo/per-band level relationships preserved), auto-matched curve descriptions.
- **`autosound_ai.py` hang protection** — a reviewer CLI spawned inside an agent session deadlocks (observed ~15/20 field sessions); calls now time out (`AUTOSOUND_CLI_TIMEOUT`, default 120 s), FAIL LOUD naming the cause, and fall back to Clipboard Mode. Troubleshooting section in `installation.md` (incl. Antigravity sandbox state-root note).

### Added — acoustic method
- **Judge deviations by audibility, not the trace** (`references/patterns/car-eq-patterns.md`): weight by *bandwidth* (a broad tilt vs the target beats a narrow notch of equal dB), catch it with a band-integrated deviation-vs-target scan (analysis playbook + Phase-3 verdict) + a long/fatigue listen (Phase 4); don't overcorrect narrow nulls / off-axis dips (kills transparency). Folded from field feedback (VW Passat B8 · Jazzi, issue #2).
- **Cross-time phase trust is band-gated** (folded into `joint_analysis` + method docs): LF phase survives between sessions; MF/HF phase does NOT (reference drift ~0.13 ms even with loopback; HF decorrelates ~110° rms) → TA/polarity only from back-to-back captures via summation/xcorr, never from cross-session HF phase.
- **[provisional] Off-axis tweeter idea-to-try** (`voicing-by-ear.md`): before keeping single-mic software HF cuts on the far/off-axis tweeter, A/B their bypass by ear — target-matching can choke decay/air (field case; geometry-dependent, NOT a rule).

### Removed
- **The 6 bundled third-party target curves** (Audiofrog, Harman, Jazzi, ResoNix Accurate, ResoNix Laid-Back, Half Whitledge) — they are other people's published curves and we don't redistribute them. Users download them from the **Nono Tuning Tool** (nonotuningtool.com) and drop them into `target-curves/curves/` or onto the visualizer (which keeps our own character descriptions and auto-matches them by name). The folder `NTT/` was renamed to **`curves/`**; the only bundled curve is now **SQ-Comp-Ref** (developed within this project, materialized as `curves/SQ-Comp-Ref_0db_REW.txt`).

### Notes
- A token-handshake + `override` "control-plane" was built and then **removed by design** — the substrate stays simple; compliance is model-choice + human-in-the-loop, not scaffolding.
- **Dogfood verdict (solo-Gemini, ~20 sessions, transcript-audited):** deterministic *calculator* tools get used (library helpers ran 100+ times); pure *discipline* gates get **narrated, not run** (the change-gate: 70+ spoken mentions, 0 executions). Hence the reframe shipped here: the substrate is the **Arbiter's power-tool, pulled** (settings-sheets citing a `v_NNN` snapshot), not a Generator self-discipline ritual — and the honest operating-modes table in `process-control.md`. The tune itself was excellent and its numbers verified real — the method holds; the process spine belongs to the Arbiter.

## [v2.0.6] — 2026-07-02
Critic as drift-watchdog (recommends re-anchor / `/clear` on detected Generator drift).

## [v2.0.5] — 2026-07-02
Single-AI reviewer ladder (on-demand / stateless, tier-escalating, never solo).

## [v2.0.4] — 2026-07-02
Resume / continuation description triggers (anchored, validated).

## [v2.0.3] — 2026-07-02
L/R shape-match group-delay caution (Gemini v2.0 methodology review).

## [v2.0.2] — 2026-07-02
UK / DE / PL native-language description triggers (validated 7/7).

## [v2.0.1] — 2026-07-02
Restore casual-EN + create-curve description triggers (9/9); repaired trigger-eval runner.

## [v2.0.0] — 2026-07-01
Assisted method: Claude+Gemini default reviewer, 5-layer knowledge architecture, goal-node phases, anti-drift state-on-disk, Gemini gemini-optim tooling. **Major bump — the numbering moved from 1.x to 2.x here;** the CHANGELOG had lagged at v1.1.0 (reconciled 2026-07-04, which is why a stale read reported "v1.1.0").

## [v1.1.0] — 2026-06-26

Packaging + method-harvest release.

### Added
- **Distributed as a Claude Code plugin** — one-command install (`/plugin marketplace add ayukhno/autosound-tuning-skill` → `/plugin install autosound-tuning`); no more manual clone+copy or the `SKILL.md`-nesting "Unknown skill" trap.
- **`knowledge/approaches.md`** — a classifier of whole-system tuning/crossover schemes as variants tagged by setup context + success story + confidence (the format names a GOAL, not a slope recipe).
- **`knowledge/{cars,dsp}/_TEMPLATE.md`** — blank fill-in profiles so onboarding a new car/DSP is a form, not reverse-engineering the example.
- **`rew_tool` helpers** — `find_measurement_id` / `get_measurement_by_name` (resolve by name) + `first_arrival` (leading-edge) + `relative_delay_xcorr` (cross-correlation), `--selftest`-verified.
- Ukrainian README (`README.uk.md`); a **Support** section (a voluntary Monobank tip jar) in all four languages.

### Changed
- **Merged the `review-loop` sibling skill into `autosound-tuning`** as `references/review-loop.md` — one skill, simpler distribution; translated to English (the skill body is now fully EN-canon).
- **Crossover schemes decoupled from competition format** — the format names a goal; the slopes follow from the setup (body → install → ways → equipment), recorded as success stories, not laws.
- **Intake §2 restructured** as the user's goals journey + a new "who is the tune for?" (driver / passenger / all seats) question + an open catch-all for any other wish.
- **De-Helix'd the universal path** — the method reads DSP-agnostic; Helix stays the worked example.
- READMEs shortened ~21% and native-reviewed (EN/DE/PL/UK).

### Notes
- Built on a VW Passat B8 / Helix DSP Ultra S system (AYA competition win).

## [v1.0.0] — 2026-06-13

First public release. Portability + process refactor that turned a single-car skill into a distributable, any-car/any-DSP method.

### Added
- **Phase −1 — new-project intake** (`references/project-intake.md`): quickstart for new hands, equipment + goals interview, target-curve choice (no default — chosen with the user via the curve→character table), install verification (routing, electrical polarity, protective crossovers, gain staging, noise, break-in, safe sweep level), DSP-capability checklist (incl. non-Helix), project-file generation.
- **Phase 7 — project wrap-up / feedback loop** (`references/feedback-loop.md`): how the skill ships and how field experience flows back safely (package template, channels, safety rules, two-step "fix locally → deliver explicitly").
- **`knowledge/` library** of accumulated profiles: `cars/vw-passat-b8-sedan.md` (body vs install anomalies, winning crossovers — anonymized), `dsp/helix-dsp-ultra-s.md` (filled intake checklist + two EQ-transfer paths). Checked first at intake of a known body/DSP.
- **`nonotuningtool` step** (Phase 1, step 5b): per-channel target curves with summation coefficients → imported into REW.
- **Standard listening pass** (`references/test-tracks.md`): a fixed 10-step route with a binary checklist for milestone ear-verification.
- Documented **REW-EQ-CopyPaste-Assistant** as the EQ-transfer path for 30+ DSPs without file import.

### Changed
- Generalized the skill to any car/DSP: car-specifics moved out of `SKILL.md` into the project profile; `description` generalized; Helix references marked `[DSP-specific]`.
- **No default target curve** anywhere — the curve is chosen with the user.
- **Phase 2 restructured** into the correct order: hygiene-EQ → joint phase → summed-curve alignment (band pairs / sides / SW+Ws) → final EQ-to-target. (Listener taste stays in Phase 6, on the virtual layer.)
- Phase 4 (center/rear) rewritten to current findings; crossover starting-sets consolidated (several variants, not one "standard").

### Notes
- Built on a VW Passat B8 / Helix DSP Ultra S system (AYA competition win). The `review-loop` sibling skill ships alongside.
