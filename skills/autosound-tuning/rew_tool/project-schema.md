# Project facts — schema & usage (SCR-001/011/014/015/016/017)

Machine-readable answer to "what is this car/install, objectively": equipment, per-channel driver
facts, the naming glossary, DSP-hardware controls, and the left-panel Project/System/Car-audio-
analysis panels. Code: `project.py` (stdlib only). Sibling of the ledger (`state/schema.md`) and
the process state (`state/process-schema.md`) — this is the third and last machine-config file
class (SKILL-SYNC-PLAN.md §0/§3): **config** (mutable, this file), **ledger** (immutable
snapshots), **process** (append-only journal + current slice).

## Why it exists

Before this, objective facts about the car/install — driver make/model/Fs per channel, the naming
glossary, which knob a DSP's RearRC/SubRC remote is dialled to — lived only in
`autosound_context.md` prose, or (worse) got hand-copied into every preset's ledger, where they
drifted out of sync (the RearRC bug caught 2026-07-28: a hardware-constant fact, duplicated
per-preset by hand, went briefly wrong in one of the two copies). A consumer UI had nothing
machine-readable to render for its Project/System/Car-audio-analysis panels either.

## Layout (data is PROJECT-local; code is in the skill)

```
<project>/project.json     the whole file below — mutable, git-tracked (config class, TCC-TZ §3)
```

## project.json

```jsonc
{
  "schema_version": 3,                                       // one number for every machine file
  "project_rev": 7,                                          // SCR-024: bumped on every write; a ledger
                                                             //   snapshot copies the value in force when
                                                             //   it was taken, so a consumer can tell
                                                             //   whose facts it is joining against
  "sources": ["user, confirmed at intake 2026-07-20", "datasheet: Audiofrog GB25 spec sheet"],
  "car": {"make": "VW", "model": "Passat B8", "year": 2019},
  "source": {"head_unit": "OEM"},
  "dsp": {"vendor": "Audiotec-Fischer", "model": "Helix DSP Ultra S"},   // links dsp_profile.json
  "amps": [{"role": "front", "make": "Helix", "model": "P Six DSP",
            "gain_db": {"value": -6.0, "source": "measured", "at": "2026-07-20T12:00:00+00:00"}}],
  "mic": {"model": "UMIK-1", "calibration_file": "umik1_cal.txt"},
  "paths": {"rew_project": null},                          // SCR-018 -- filled once intake records it
  "presets": ["FULL", "SQ"],

  "channels": [                                              // SCR-001: per-channel IDENTITY. As of v3
                                                             //   this is the ONLY home for slot/descr/
                                                             //   role/order/tier/hidden -- the ledger
                                                             //   carries tuning state, joins here by `code`
    {"code": "w-L", "slot": "C", "descr": "Front L Woofer", "role": "woofer", "order": 1,
     "tier": "channels",                                     // SCR-042: the LEDGER tier key, not the
                                                             //   profile's group id -- physical outputs
                                                             //   are "channels", never "physical_outputs"
     "id": "m-L", "previous_names": ["m-L"],                 // SCR-039: written only by a rename.
                                                             //   Absent = id is the code, which is
                                                             //   every project that never renamed
     "driver": {"make": "Audiofrog", "model": "GB25"},
     "fs_hz": {"value": 62, "source": "datasheet", "at": "…"},
     "impedance_ohm": 4, "hidden": false},
    {"code": "vrf", "slot": "F", "hidden": true,             // SCR-003: no physical driver assigned
     "role": "unused", "tier": "virtual_channels"}           // SCR-042: which tier it is spare OF.
                                                             //   Slot letters REPEAT across tiers (this
                                                             //   Helix: virtual A-H, outputs B-K), so
                                                             //   "F" alone is ambiguous and a guess
                                                             //   files a spare output among the
                                                             //   virtual channels. `role: "unused"` is
                                                             //   not a substitute -- it is what loses
                                                             //   the tier in the first place
  ],

  "hardware": {                                              // SCR-017: DSP-level, NOT per-preset
    "controls": {
      "RearRC": {"value": "3/4", "source": "user", "at": "…"},
      "RealCenter": {"value": "ON", "source": "user", "at": "…"}
    }
  },

  "glossary": {                                              // SCR-008 -- naming.Glossary.for_project
    "channels": [{"code": "w-L", "active": true}, {"code": "c", "active": false}],
    "pairs": {}, "combos": {}, "joints": {}, "sides": {}
  },

  "channel_summary": {                                       // SCR-016: project-scoped tier counts
    "virtual_channels": {"total": 8, "off": 1},
    "channels": {"total": 12, "off": 2}
  },

  "acoustics": {                                             // SCR-015: the phase-0 flaw map, as data
    "flaws": [
      {"f_hz": 73, "q": 3.5, "level_db": 9,                  // level_db = the FEATURE: + hump, - dip
       "kind": "driver_resonance", "action": "notch",        //   NOT the correction you would apply
       "channels": ["w-R"], "why": "right-woofer resonance",
       "evidence": ["w-R_1 (sw)"], "at": "…"},
      {"f_hz": 250, "level_db": -12, "kind": "cabin_null",   // a dip can NEVER be `notch`
       "action": "no_boost", "channels": ["w-R"],
       "why": "interference, not min-phase",
       "evidence": ["w-R_1 (sw)"], "at": "…"}
    ]
  },

  "_open_questions": ["source.head_unit trim level"]
}
```

### `acoustics.flaws[]` — what this cabin does, and what may be done about it (SCR-015)

The phase-0 Acoustic Flaw Map (`phase_0_baseline.md §3.5`) as machine data rather than prose, so a
front-end can render it and a later phase can consult it without re-reading a case study.

| field | notes |
|---|---|
| `f_hz` | centre frequency, required, positive |
| `q` / `bw_oct` | width, either form, optional |
| `level_db` | **the feature**, signed: `+` a hump, `−` a dip. Not the correction |
| `kind` | `room_gain` · `modal_peak` · `cabin_null` · `sbir` · `floor_bounce` · `driver_resonance` · `non_min_phase` · `thd_spike` · `pair_suckout` |
| `action` | `notch` · `leave` · `no_boost` · `geometry` · `delay` · `crossover` |
| `channels` | the codes it was measured on |
| `why` | one line — the next session reads the reason, not the number |
| `evidence` | the captures it was read off; a flaw with no measurement behind it is a rumour |

Both lists are closed: a consumer colours by `action`, and "what may NOT be done here" is the half
that has to survive the session that found it. **`level_db < 0` with `action: "notch"` is refused**
— a null is interference, not minimum-phase; cutting it changes nothing and boosting it burns
headroom against physics. That refusal is the map's whole reason for existing in code rather than
in a paragraph somebody may or may not re-read.

Re-measuring the same frequency on the same channels **replaces** its row. An install changes and
the map is redone; two contradictory rows for one peak would leave a reader picking between them.

### A channel's id is not its name (SCR-039)

`code` used to do three jobs: the ledger's row key, the join key between this file and a snapshot,
and the label a human reads — and types into every REW measurement title the project will ever
have. Renaming a channel for an ordinary reason (an `m-L` the install correction turns into a
woofer, a "rear" pair that is really a centre) then meant rewriting every historical snapshot or
leaving them keyed by a name nobody uses. Both were done by hand in this project's own dogfood data.

Now:

| field | notes |
|---|---|
| `id` | the stable identity. Never displayed. **Defaults to the code**, so it is absent from every project that has never renamed anything — no migration, no format break |
| `code` | the current name: what a person reads, what a generated REW title uses |
| `previous_names` | every name it has gone by before, oldest first |

`rename_channel(old, new)` is the whole operation: materialise the id, set the new code, append the
old name, and rename the glossary entry so tomorrow's titles use the new name. **Snapshots are not
touched** — their keys are ids, so they stay valid and immutable, which is the point. **REW titles
are not touched either**, because they cannot be: a title is typed by hand and the captures a
channel took under its old name are the only ones it has. `naming.Glossary.resolve_code` maps an
old name to the current one, so `m-L_2 (sw)` and `w-L_2 (sw)` are one measurement — same channel,
same DSP config version — and a checklist does not ask for work already sitting in REW.

Refused, because both make a capture's owner ambiguous: two channels with the same `id`, and a
`previous_names` entry that is another channel's live `code`.

A rename is a label being corrected, so its `config_change` impact is normally `none` — no
measurement is invalidated by it.

### A spare slot says which tier it is spare of (SCR-042)

Rows in a consumer's channel panel are built from the ledger, and **a slot with nothing wired to it
has no ledger row** — there is no tuning state to record for it. `project.json` does carry those
slots, correctly marked (`hidden: true`, `role: "unused"`), so the fix is not new data but a field
that says which tier each one belongs to.

| field | notes |
|---|---|
| `tier` | the **ledger tier key**: `channels` for a physical output, `virtual_channels` / `inputs` / whatever else that DSP's profile declares. Optional — a project written before this renders exactly as it did |

**It is the ledger key, not the profile's group id.** The profile calls the physical-output tier
`physical_outputs`; the ledger has always called it `channels`. `dsp_profile.ledger_tier()` is the
one place that conversion lives, and `validate()` refuses `tier: "physical_outputs"` outright —
it would match no tier, and the row would simply never render, without an error.

**Why it cannot be inferred:** slot letters repeat across tiers. On a Helix Ultra S the virtual tier
runs A–H and the outputs run B–K, so `slot: "F"` is a legal address in both, and guessing files a
spare output among the virtual channels — a wrong row in the one panel whose job is showing the rig
as it actually is. `role` is no help either: an unused virtual slot is written `role: "unused"`,
which is precisely what loses the tier.

The companion is **`max_count` per group in `dsp_profile.json`** — how many slots that tier
physically has. Without it a consumer can only count the rows it was given, so a 12-output Helix
with ten wired reads `10/10` instead of `10/12`. It is a DSP-model fact like the rest of that file,
null until confirmed, and it makes the spares visible as spares whether or not `tier` is filled in.

## Provenance (SCR-014)

Two granularities, deliberately not one:

- **File-scoped** — the top-level `sources` list (free text, the same convention
  `dsp_profile.json` already carries in the wild): "confirmed once, rarely revisited" facts (car
  make/model, mic model, DSP vendor) don't need per-field dating.
- **Fact-scoped** — `fact(value, source, at)` → `{"value": …, "source": "user|measured|datasheet",
  "at": "…"}`, for the specific facts that DO drift mid-project and that a `config_change` event
  needs to point back at: amp gain, driver `fs_hz`, a hardware control's dialled position.
  `fact_value(x)` unwraps either shape (wrapped or bare) — a reader never needs to know which
  fields are wrapped.

`open_questions(data)` walks the whole structure (mirrors `dsp_profile.py`'s walker exactly): a
bare `null` OR a `fact()` wrapper whose `value` is `null` is an open question; `_open_questions`
freeform notes are included as-is. Unknowns are recorded, never guessed.

## Hardware controls vs. the ledger (SCR-017)

A DSP hardware control (Helix's RearRC/SubRC remote-knob position, RealCenter on/off) is a fact
about the **device**, constant across every preset loaded on it — it does not belong in
`state/v_NNN.json` (which is per-preset). Recording it once in `project.json.hardware.controls`
(via `set_hardware_control`) is what stops the two copies drifting, which is exactly what happened
by hand during the M7 pass this schema replaces. **Optional and profile-declared** — a MUSWAY or
other vendor with no such remote simply has no `hardware.controls` entries; nothing assumes them.

## config_change events (SCR-014)

Every mid-project correction to ANY machine config file — this one, the ledger, `dsp_profile.json`
— is a journal event, so a resume can see WHAT changed and WHY, and a consumer UI can flag exactly
what the change invalidates:

```python
from state.process import Process   # via the lazy sys.path import project.py's CLI/selftest use
import project

proj = project.Project(project_dir)
proc = Process(f"{project_dir}/process")
proj.record_change(proc, "project.json", "swapped front woofer driver",
                    why="blown voice coil", source="user", impact="remeasure: [w-L, w-R]")
```

`impact` is the machine form of `naming-and-structure.md §2`'s "what raw data survives" table:
`"none"` · `"remeasure: [<codes>]"` · `"full_rebaseline"`. The event lands in the SAME project's
`process/journal.jsonl` (SCR-004) — `project.py` does not own a second log.

## API / CLI

```python
from project import Project, fact, fact_value, open_questions

proj = Project(project_dir)
proj.set_channel("w-L", driver={"make": "Audiofrog", "model": "GB25"},
                  fs_hz=fact(62, source="datasheet"))
proj.set_hardware_control("RearRC", "3/4", source="user")
data = proj.load()                 # -> the whole file (an empty skeleton if none exists yet)
open_questions(data)                # -> ["mic.calibration_file", "amps.0.gain_db", ...]
```
```
python3 project.py <project-dir> show
python3 project.py <project-dir> open-questions
python3 project.py <project-dir> set-channel <code> key=value [key=value ...]
python3 project.py <project-dir> rename-channel <old> <new>        # SCR-039
python3 project.py <project-dir> set-hardware <name> <value> [--source user]
python3 project.py <project-dir> record-change <process-dir> <file> <what> [--why W] [--source S] [--impact I]
python3 project.py selftest
```

## Invariants

- **Lenient on missing facts, strict on shape** — an unfilled fact is `null`/absent (→
  `_open_questions`), never a validation error; a malformed collection (wrong type, duplicate
  channel `code`) IS refused, same "strict on silent/expensive errors" split as `state.py`.
- **A channel is addressable by any name it has ever had** (SCR-039) — `resolve_channel` and
  `set_channel` both look up current code, then id, then `previous_names`, so a caller working from
  a stale context (as a language model regularly is) updates the right row instead of appending a
  second channel.
- **`channels[]` here is per-channel HARDWARE facts (driver/Fs/impedance), not the naming
  glossary** — `glossary.channels` (codes + active flag, consumed by `naming.py`) is a distinct,
  smaller list keyed by the same `code`. Two different questions: "what can this channel be
  called in a measurement title" vs. "what driver is actually wired to it."
- **`hardware.controls` is DSP-level, never per-preset** — see SCR-017 above; the per-preset ledger
  keeps only what genuinely varies per preset (`mute`, `off`).
- **Writes are atomic** (write-temp-then-rename) — a torn write must not read back as an empty
  project, the same reasoning `process.py._write` documents.
