# Hard-params state — schema & usage

Versioned single-source-of-truth for a preset's **hard params** (crossovers · gains · TA · polarity ·
EQ pointers), the anti-drift anchor and the experimentation engine. Code: `state.py` (stdlib only).

**Schema v3** (2026-07-31, the 3.0 format break). Two changes on top of v2:

- **Identity left this file.** `slot`, `descr`, `role`, `order`, `hidden` and `tag_value` now live
  in `project.json` — `channels[]` for the first five, `hardware.controls` for `tag_value`
  (SCR-001/017). A row here carries only what can differ between two snapshots of the same
  install; consumers join the two files on the channel `code`. `validate` **refuses** a row still
  carrying them rather than dropping them silently, so a half-migrated file is loud, not lossy.
- **A row's key is the channel's id, not its name** (SCR-039, 2026-08-07). The id defaults to the
  code, so nothing about an existing file changes and no migration runs — the two only diverge
  once a channel is renamed, and then this file keeps the key it was written with. That is what
  makes a snapshot immutable in practice: renaming `m-L` to `w-L` used to mean rewriting every
  historical snapshot or leaving them keyed by a name nobody uses. `project.json` carries the
  current name and a `previous_names` list; `project_channels` resolves a row key through all
  three, so a reader never sees an unknown channel it has full identity for.
- **Every snapshot stamps `project_rev`** (SCR-024) — the revision of `project.json` in force when
  the values were banked, so joining an old snapshot to today's facts is detectable instead of
  silently relabelling history when a driver is replaced.

One number for the whole project: every versioned machine file carries `schema_version: 3`
(`contract.py`'s `FORMAT_VERSION`). Nothing in 3.x reads a 2.x file — import its current state
into a NEW 3.0 project once, `python3 state/migrate.py <old-project-dir> --into <new-project-dir>`,
and move on: a folder that holds a project's ledger or `dsp_profile.json` is refused, nothing
written. The 2.x skill remains its own release for anyone staying there.

**Schema v2** (2026-07-29, autosound-tcc sync — see that repo's `docs/SKILL-SYNC-PLAN.md`): the
ledger became **tier-aware**, EQ bands became **structured objects**, and every snapshot carried
`schema_version`.

## Why it exists
- **Anti-drift:** one file per snapshot holds *all* hard params together, so nobody ever reads a
  partial picture (the split-artifact bug: gains in a screenshot, EQ in `.req` → "no gain change"
  mis-read). Write-after-every-change + read-before-edit make `/clear + resume` trustworthy.
- **Experimentation:** a snapshot is a `diff` / `revert` away → weird ideas are cheap to try. Same
  mechanism as anti-drift; stability and freedom are not opposed.

## Layout (data is PROJECT-local; code is in the skill)
```
<root>/versions/v_001.json …   immutable snapshots, numbered once per PROJECT   # <root> = <project>/state
<root>/slots.json              {"active", "slots": {preset: {version, since, label, note, dsp_preset,
                               loaded: {version, since, source},
                               history: [{version, since}]}}, "configs": {name: {version, slot,
                               purpose, saved, previous: {code, version} | null,
                               history: [{version, saved}]}}, "layout": "project-numbered"}
<root>/proposals/v_NNN.json    the change sheet beside each proposal (SCR-026)
<root>/legacy/<preset>/…       a per-preset ledger after `migrate-line`, as it was
<root>/legacy-map.json         {"<preset>/v_NNN": "v_MMM"} — every old citation resolves
```
A version carries `preset` (the slot it was banked FOR) and `parent` (the version it was made from);
a variant also carries `variant` (its name) and is banked without moving the slot (`place=False`).

**A candidate is a variant named `candidate`** (`propose`, a structural move with no evidence or no reviewer behind
it). While a slot's newest version is one and not in the slot, a `propose` that names no base is refused: `--on v_NNN`
builds on it, `--on HEAD` says the delta really is for the slot's version (#199). Built on a candidate, the result's
structural moves are measured from the candidate's own base, the first version up its `parent` line that is no
candidate, so nothing it has not earned goes through. It stays a candidate until evidence and a reviewer are there,
even with no move of its own; then its `candidate` rows become `proposed`, `variant` is cleared and it is placed, so
`attest` covers them. Until then `attest` refuses it, in the slot or not. A device read vouches only for the rows it
read: the others stay `candidate`, and the version stays one while any is left. `parent` is the true base
(`v_003 = v_002 + …`, also on the older layout), while the sheet is measured against the last placed version, because
that is what is in the DSP.

**A base other than HEAD answers to the slot** (`--on <older or named version>`): its structural moves are measured
against the last placed version as well, so a delta of `{}` on an older version is every move between the two, a row
only the slot holds counting as removed. Held until evidence and a reviewer are there, like any candidate.

**A configuration is a version SAVED into a DSP preset under a name** (the Arbiter, 2026-09-23). A
`v_NNN` is a full DSP state proposed at the desk and may never be kept; what the tuner saves into the
device he saves under a name of his own (`SQ-1`, `FULL-v1`, `SQ-2`, any name, any purpose).
`state.py config save <version> <name> [--slot S] [--dsp-preset N] [--purpose "…"]` records it in
`slots.json` `configs` and puts the version in the slot. Its `previous` is the nearest ancestor up the
`parent` chain that was saved under a name, found at save time: SQ-2 (v_006, made from v_003) has SQ-1
(v_003) as its previous, never v_005 banked in between for another preset. `--previous NAME` states it
when the ancestry does not. A name saved again keeps its `history`. `config compare <name>` diffs
against the previous configuration (`--with` another name or a version); `config list` lists them.
A front-end compares against `previous`, not against the number before.

**The older layout is still read** (W-2, hub #195): `<root>/<preset>/v_NNN.json` + `<root>/<preset>/HEAD`
+ `<root>/registry.json`, one number line per preset. `state.py --root <root> migrate-line` shows the
move and `--apply` makes it; the active slot keeps its numbers, and the others are numbered after it.
It is one-way and offered, never automatic. A root holding both layouts, or `versions/` without
`slots.json` (a move that stopped), is refused with the command that finishes it (`ledger_layout`).
An empty root starts on the per-project line.

## Snapshot JSON
```jsonc
{
  "schema_version": 3,                                        // stamped by snapshot(); one number per project
  "project_rev": 7,                                           // SCR-024: project.json revision these
                                                              //   values were banked against
  "preset": "SQ_Jazzi", "version": "v_002", "created": "…",   // version/created injected by snapshot()
  "sample_rate": 96000,                                       // samples DERIVED from this; ms is canonical
  "target": "Jazzi",
  "roles": {"artist": "Gemini", "producer": "Claude", "critic": null},   // roles-on-disk (AD-2)
  "provenance": {"decision": "clean-slate by-ear 2026-06-18"},
  "banked_ear_verdicts": [],
  "virtual_eq_ptr": null,
  "note": "sub INV test + w-L trim",                          // per-snapshot label, NOT diffed
  "channels": {                                                // the REQUIRED tier (physical outputs)
    "w-L": {                                                  // identity (slot/descr/role/order/hidden)
                                                                // is NOT here in v3 -- project.json owns it.
                                                                // This key is the channel's ID (SCR-039),
                                                                // which DEFAULTS to its code: it reads as
                                                                // the name, and stops moving if the channel
                                                                // is ever renamed
            "tag": null,                                      // optional: WHICH hardware control affects
                                                                // this row (its VALUE is in project.json's
                                                                // hardware.controls -- SCR-017)
            "mute": false, "off": false,                      // optional bools; absent = false/unknown
            "hp": {"f": 70, "type": "BW", "slope": 12},       // null / "OFF" when disabled
            "lp": {"f": 270, "type": "BW", "slope": 12},
            "gain_db": -7.8,
            "ta_ms": 5.38,                                    // CANONICAL; samples = round(ms*rate/1000)
            "polarity": "NORM",                               // NORM | INV
            "phase_deg": null,                                // optional: all-pass/phase angle
            "eq": [{"type": "PK", "f": 1000, "gain_db": -9, "q": 2, "bypass": false}],  // structured bands
            "eq_ptr": {"output": "exports/w-L.req", "virtual": null},
            "status": "applied"}                              // proposed | applied | measured  (AD-1)
  },
  "virtual_channels": {                                        // any OTHER tier the DSP profile declares
    "VFL": {"gain_db": 0.0, "ta_ms": 0.0, "polarity": "NORM"}                // no hp/lp -- not required here
  }
}
```

### Tiers (schema v2)

The ledger is **tier-aware**, not `channels`-only: a tier is any top-level key holding a dict of
row-dicts. `channels` is the one REQUIRED tier (physical outputs) and the only one with a strict
required-field list (`hp`, `lp`, `gain_db`, `ta_ms`, `polarity`). Any OTHER top-level dict-of-dicts
key (e.g. `virtual_channels`, or a MUSWAY-style `inputs`) is an additional tier — validated
leniently (only present fields are type-checked; nothing is required), matching a DSP profile's
declared groups (`dsp_profile.py`'s `groups[].id`, `physical_outputs` → `channels`, anything else
→ a same-named top-level key — the convention `autosound-tcc`'s `ProjectView.from_dict` already
reads by). `state.tier_names(snapshot)` returns every tier present. A tier must exist as a
(possibly empty) top-level key **before** `apply.propose` can address it by name — intake seeds
every profile-declared tier, even empty, at the first snapshot.

`tag`/`mute`/`off`/`phase_deg`/`eq` are all OPTIONAL on every tier's rows — only type-checked when
present (the booleans must be bool), matching how `eq_ptr`/`status` were already optional.
Leniency stops at identity: `slot`/`descr`/`role`/`order`/`hidden`/`tag_value` are **refused** on
every tier, including virtual ones — a virtual slot's name belongs in `project.json` exactly like a
physical one's.

### EQ bands (structured, schema v2)

`eq` is a list of **band objects**, not strings:
```jsonc
{"type": "PK", "f": 1000, "gain_db": -9, "q": 2, "bypass": false, "i": 1}
```
`type` ∈ `EQ_TYPES` = `PK | LSH | HSH | APF1 | APF2` (TCC-TZ.md §2's authoritative Helix
vocabulary); `f` is a positive Hz; `gain_db`/`q` are numeric and optional (an all-pass band has no
gain); `bypass` is an optional bool; `i` is an optional 1-based band-slot index (useful for a
30-slot Helix EQ / PC-Tool insert order). The old inline string form (`"PK 1000 -9 Q2"`) is now
**display-only**, generated on demand: `state.eq_str(bands)` / `state.eq_band_str(band)`. Parsing
the string form back (`state.eq_band_from_str`) exists ONLY for `migrate.py` — it also
normalizes the `LS`/`HS` shorthand the two hand-authored v1 ledgers actually used to the canonical
`LSH`/`HSH`.

**`eq` vs `eq_ptr`** — both, not either/or: `eq_ptr` says where the authoritative REW export
lives, `eq` carries the bands themselves so a reader needs no second file.

### Preset settings (`preset_settings`, #197, #200)

A preset's own settings, beside the tiers: a top-level object that is **not** a tier (`_NON_TIER_KEYS`; `preset` is
taken by the slot's name), checked on its own by `validate_preset_settings`. No migration: `SCHEMA_VERSION` stays 3, and
a version without the field is valid.
```jsonc
"preset_settings": {
  "input_gain_db": -0.3,                                       // the preset's main input gain, dB
  "sources": {"main": 0.0, "hec": -2.0, "digital": 0.0},       // source levels, dB
  "fx": {"realcenter": true, "dynamic_bass": false, "subxpander": false},   // the FX group, as the DSP shows it
  "rtc": {"on": true, "curve": {"gstart0": -3.0, "fstart0": 800}},          // curve: name -> number
  "bt": {"source": "AUX", "auto_switch": true},
  "conductor": {"sub_lamps": 7},                               // the sub knob position it was set up and judged at
  "status": "applied",                                         // its own, as a row's: proposed -> applied by attest
  "source_file": {"name": "…", "path": "…", "md5": "…",        // the saved preset this version was read from
                  "saved": "…", "pctool": "…", "device": "…",  // the save time, PC-Tool version, device it states
                  "read_at": "…", "compared": "no difference"}  // or a list of the differences
}
```
- **Every field is optional; a missing one reads as its default**, 0 dB or off. So it is no difference and nothing is
  printed. The exception is `dynamic_bass` and `subxpander`, which have no legacy alias: where a record does not state
  them they are **unknown, not off**. `bt.source`, `rtc.curve` and `conductor.sub_lamps` have no default: an unstated one
  is a dash. A field `validate` does not know is refused, as a channel field is.
- **Never asked for.** Not in the intake, not required to bank, not on a sheet while at its default (the tuner: «default
  0 dB, and don't ask until the user gets to needing it»).
- **Audiotec Fischer's** (the Arbiter, 2026-11-08), Helix and its kin. The fields beyond `input_gain_db` are filled only
  on a DSP whose profile names them (`effects_and_dynamics`, `dsp_profile.py`). This is the method's text: `validate` and
  the renderers get no profile. They are filled by the session or the person. When the skill can read a saved preset it
  checks them against it; until then the check is the screen (`screen-read-dsp.md`).
- **`FX` in anything older means RealCenter**: `fx.realcenter` (`references/core/naming-and-structure.md`).
- **A delta** carries it by name, `{"preset_settings": {"input_gain_db": -0.3}}`, alone or beside the rows. `apply_delta`
  takes it out before `_split_by_tier` and merges it two levels deep, so one `fx` switch leaves the others.
- **A change is an ordinary row**: no structural move, so no reviewer. `structural_moves` and `advisories` walk the
  tiers only. Held with a structural move that has not earned its proposal, it goes `candidate` and is promoted with it.
- **The diff** carries one key under `preset`: `preset_settings: [old, new]`, each only what it really sets. Its status
  and its source file are no change of the DSP, so neither reaches the diff. Readers: the sheet, `delta_rows` (`tier:
  preset_settings`, `channel: preset`, `param`, `field`, `was`, `value`, `was_raw`, `value_raw`), `render_state`,
  `render_diff` by name; `verification_set` asks for the whole-system sum; `levelbase.changed_ranges` reads it as
  every band changed; `predict.chains_from_snapshot(snap, trim=True)` adds the input gain once, on the physical tier,
  for the `predict` view, off by default for the engine.
- **`source_file` is `attest`'s**: `attest --source-file <file.json>` (`apply.attest(…, source_file=)`) records it, and
  `attest` keeps it. A delta cannot give it, and `propose` drops it, since a new version was not compared to that file.
  Not `provenance`: `propose`'s only door replaces the whole `provenance` and switches off the structural hold.
- **Not harmless to an older copy.** A 3.2 copy of the method reads the dict as a tier and refuses the number in it. It
  fails loud, only on a project a newer copy has written. A project bound to an older copy moves up before using the field.

## Invariants
- **ms is canonical, samples are a view.** Entering 96 kHz samples into a 48 kHz DSP doubles the
  delay — so the file commits to ms; `render` shows derived samples for the active rate.
- **status lifecycle (AD-1):** 🟡`proposed` → 🟢`applied` (Arbiter attests) → 📏`measured`. The file
  is the truth for **intent + attested-applied**, NOT a device mirror — **device-truth = the latest
  measurement.** It claims nothing more.
- **HEAD is the pointer; `loaded` is a dated claim; neither is a mirror (AD-1, #201).** HEAD
  (`slots[slot].version`) is the version the slot's line stands at, and it may be a proposal nobody has
  entered yet. `slots[slot].loaded = {version, since, source}` says this version went into the DSP's
  preset, when, and how that is known. It is written by `attest` (the newly banked version, which is
  HEAD; source `attest`), by `config save` (source `config save <name>`) and by `state.py loaded <slot>
  <version> --source "…"` for what no verb here saw: a preset loaded in the PC tool, a `.pct6` read
  back. A later move of HEAD leaves it where it is, so HEAD ahead of `loaded` reads plainly as «proposed,
  not in the DSP». No `loaded` means no claim: unknown, never HEAD. A preset changed by hand leaves both
  behind, so device-truth stays the latest measurement. `loaded` is on the per-project line only: a
  `slots.json` beside per-preset folders makes the ledger unreadable.
- **`render` is generated-only** — never hand-edit the Markdown sheet; edit the JSON and re-render.
  (The render is also the settings sheet the future `apply-change` gate hands the Arbiter at the
  PC-Tool screen — the artifact that makes the compliant path the easiest path.)
- **`snapshot` validates and refuses malformed state** (bad polarity, missing crossover, ms absent).
- **`revert` is forward-only** — it writes a new snapshot copying an old one; history is never destroyed.
- **Every tier is covered** — `validate`/`diff_states`/`render` all walk `tier_names(state)`, not
  just `channels`. A virtual-tier change used to be invisible to all three; that was the split-
  artifact bug this file exists to prevent, just happening to a whole tier instead of one field.

## API / CLI
```python
from state import PresetHistory
h = PresetHistory(root, "SQ_Jazzi")            # project_dir= if <root> isn't <project>/state
h.snapshot(state, note="…")   # -> "v_00N"   (validates, advances HEAD, stamps schema_version
                              #               + project_rev read from project.json)
h.diff("v_001", "v_002")      # -> structured deltas, one key per tier (only changed fields)
h.render("v_002")             # -> Markdown settings sheet (a section per non-`channels` tier)
h.revert("v_001")             # -> new snapshot == v_001 content
```
```
python3 state.py --root <dir> log|render|diff|revert <preset> [args]
python3 state.py --root <dir> config save <version> <name> [--slot S] [--dsp-preset N] [--purpose "…"]
python3 state.py --root <dir> config list | config compare <name> [--with <name or version>]
python3 state.py --root <dir> loaded <slot> <version> --source "<where this comes from>"
python3 state.py selftest
python3 state/migrate.py <old-project-dir> --into <new-project-dir> [--dry-run]   # 2.x -> 3.0, into a NEW project
```

## apply-change gate (`apply.py`)
The gate that turns a proposed delta into a banked snapshot + the human SETTINGS SHEET. The DSP is
entered by hand in Helix, so the gate can't touch the device — it earns its keep by being the ONLY
producer of the clean old→new sheet the Arbiter keys in (bypass = nothing usable → compliant = easiest).
```python
from state import PresetHistory
import apply
h = PresetHistory(root, "SQ_Jazzi")            # HEAD must exist (seed the first state via h.snapshot)
r = apply.propose(h, {"w-L": {"gain_db": -7.5, "ta_ms": 5.45}, "sub": {"polarity": "INV"},
                      "virtual_channels": {"VFL": {"gain_db": -1.0}}},
                  note="…")                     # -> banks 🟡 snapshot; r["sheet"] = the settings sheet
print(r["sheet"])                               # channel/param old→new, ms+derived samples, advisories
apply.attest(h)                                 # Arbiter entered it in Helix -> flip 🟡→🟢 applied (new snapshot)
                                                # source_file={...}: the saved preset it was read from (#200)
```
- **Tier-aware delta (schema v2):** a bare `{channel: {field: value}}` delta still means `channels`
  (unchanged); a delta is read as tier-keyed only when EVERY one of its top-level keys is already a
  tier the ledger has (`state.tier_names`), so an ordinary channel-name delta is never misread — see
  `apply._split_by_tier`. A tier the ledger doesn't have yet cannot be addressed this way; intake
  seeds every profile-declared tier, even empty, up front.
- **Deterministic refusals (hard):** unknown channel/field (typo), partial edit of a non-existent
  row, TA given as samples not `ta_ms`, or any result failing `validate` — a refused delta banks
  nothing.
- **Advisories (soft, waivable — the demoted noun-rails):** large gain jump, polarity flip, big
  delay/crossover move → printed ⚠️, never blocking; the ear + measurement rule the acoustic nouns.
- Lifecycle: `propose` 🟡 → `attest` 🟢 → 📏 after a control measurement confirms effect — across
  every tier a proposal touched, not just `channels`.
- Why it's kept simple: banking a change is genuinely useful (A/B, revert, resume after `/clear`, one
  honest audit trail), so it earns its place on merit — not as a mechanism to police the model.

## Multi-slot registry (`Registry` — issue #5)
A multi-preset DSP (e.g. a Helix's numbered slots) invites a degrading model to anchor on the **wrong slot's**
gains: the real incident was tuning `3.SQ-Comp-Ref` while the top of a flat state table still
showed `2.ResoNix` numbers, so proposed HF filters were computed off a baseline that belonged to
a different slot. Each preset's snapshots are **already** physically isolated under `<root>/<preset>/`;
the registry adds the one missing thing — an explicit, machine-checked pointer to the **live** slot.
```
<root>/slots.json         # per-project line: {"active": "<preset>", "slots": {"<preset>": {"version": "v_063", "label": "3.SQ-Comp-Ref", …}}}
<root>/registry.json      # per-preset layout: {"active": "<preset>", "slots": {"<preset>": {"label": "3.SQ-Comp-Ref", "note": "…"}}, "updated": "…"}
```
- **`set_active(preset)`** — deterministic guard: the preset must already have a snapshot history.
- **`render()`** — the generated multi-slot `dsp-state-current` view: a **LOUD active-slot banner**
  first (a top-down read can't drift to a neighbour), then one isolated summary row per slot.
- **Gate integration:** `apply.propose(h, delta, registry=reg)` **REFUSES** a change whose preset is
  not the active slot (unless `allow_nonactive=True`) and stamps the settings-sheet header
  `ACTIVE SLOT ✅` / `⚠️ NON-ACTIVE SLOT`. This is the *mechanized* MULTI-SLOT STATE INTEGRITY RULE —
  a gate that refuses, not prose that asks.
```python
from state import Registry
reg = Registry(root)
reg.set_active("SQ_Comp_Ref")                 # which slot is loaded in the DSP right now
reg.describe_slot("SQ_Comp_Ref", label="3.SQ-Comp-Ref")  # number.configuration, the slot rule
print(reg.render())                           # banner + per-slot table (generated dsp-state-current)
apply.propose(h, delta, registry=reg)         # refuses if h.preset != active slot
```
```
python3 state.py --root <dir> registry show|render
python3 state.py --root <dir> registry set-active <preset>
python3 state.py --root <dir> registry describe <preset> --label "3.SQ-Comp-Ref" --note "…"
python3 state.py --root <dir> variant new <preset> <name> [--from v_NNN] [--delta change.json]
python3 state.py --root <dir> variant list <preset>
python3 state.py --root <dir> variant switch <preset> <v_NNN>   # the slot's pointer moves; nothing is copied
python3 state.py --root <dir> migrate-line [--apply]             # per-preset → per-project line
```
