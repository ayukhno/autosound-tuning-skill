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
(`contract.py`'s `FORMAT_VERSION`). Nothing in 3.x reads a 2.x file — run
`python3 state/migrate.py <project-dir>` once and move on. The 2.x skill remains its own release
for anyone staying there.

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
<root>/<preset>/v_001.json …   immutable snapshots     # <root> = e.g. project rew_analitic/state/
<root>/<preset>/HEAD           current version name     #         (env AUTOSOUND_STATE_ROOT)
```

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

## Invariants
- **ms is canonical, samples are a view.** Entering 96 kHz samples into a 48 kHz DSP doubles the
  delay — so the file commits to ms; `render` shows derived samples for the active rate.
- **status lifecycle (AD-1):** 🟡`proposed` → 🟢`applied` (Arbiter attests) → 📏`measured`. The file
  is the truth for **intent + attested-applied**, NOT a device mirror — **device-truth = the latest
  measurement.** It claims nothing more.
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
python3 state.py selftest
python3 state/migrate.py <project-dir> [--dry-run]   # one-shot 2.x -> 3.0, whole project
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
A multi-preset DSP (e.g. Helix Slot 1/2/3) invites a degrading model to anchor on the **wrong slot's**
gains: the real incident was tuning Slot 3 (SQ-Comp-Ref) while the top of a flat state table still
showed Slot 2 (ResoNix) numbers, so proposed HF filters were computed off a baseline that belonged to
a different slot. Each preset's snapshots are **already** physically isolated under `<root>/<preset>/`;
the registry adds the one missing thing — an explicit, machine-checked pointer to the **live** slot.
```
<root>/registry.json      # {"active": "<preset>", "slots": {"<preset>": {"label": "Slot 3", "note": "…"}}, "updated": "…"}
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
reg.describe_slot("SQ_Comp_Ref", label="Slot 3")
print(reg.render())                           # banner + per-slot table (generated dsp-state-current)
apply.propose(h, delta, registry=reg)         # refuses if h.preset != active slot
```
```
python3 state.py --root <dir> registry show|render
python3 state.py --root <dir> registry set-active <preset>
python3 state.py --root <dir> registry describe <preset> --label "Slot 3" --note "SQ-Comp-Ref"
```
