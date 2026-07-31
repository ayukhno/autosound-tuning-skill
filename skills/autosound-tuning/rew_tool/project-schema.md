# Project facts — schema & usage (SCR-001/011/014/015/016/017)

Machine-readable answer to "what is this car/install, objectively": equipment, per-channel driver
facts, the naming glossary, DSP-hardware controls, and the left-panel Project/System/Car-audio-
analysis sections. Code: `project.py` (stdlib only). Sibling of the ledger (`state/schema.md`) and
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
                                                             //   role/order/hidden -- the ledger carries
                                                             //   tuning state and joins here by `code`
    {"code": "w-L", "slot": "C", "descr": "Front L Woofer", "role": "woofer", "order": 1,
     "driver": {"make": "Audiofrog", "model": "GB25"},
     "fs_hz": {"value": 62, "source": "datasheet", "at": "…"},
     "impedance_ohm": 4, "hidden": false},
    {"code": "vrf", "slot": "F", "hidden": true}             // SCR-003: no physical driver assigned
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

  "param_sections": [                                        // SCR-015: left-panel extra sections
    {"id": "system", "label": "System params",
     "params": [["DSP", "Helix DSP Ultra S"], ["REW port", "4735"]]}
  ],
  "channel_summary": {                                       // SCR-016: project-scoped tier counts
    "virtual_channels": {"total": 8, "off": 1},
    "channels": {"total": 12, "off": 2}
  },

  "_open_questions": ["source.head_unit trim level"]
}
```

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
python project.py <project-dir> show
python project.py <project-dir> open-questions
python project.py <project-dir> set-channel <code> key=value [key=value ...]
python project.py <project-dir> set-hardware <name> <value> [--source user]
python project.py <project-dir> record-change <process-dir> <file> <what> [--why W] [--source S] [--impact I]
python project.py selftest
```

## Invariants

- **Lenient on missing facts, strict on shape** — an unfilled fact is `null`/absent (→
  `_open_questions`), never a validation error; a malformed collection (wrong type, duplicate
  channel `code`) IS refused, same "strict on silent/expensive errors" split as `state.py`.
- **`channels[]` here is per-channel HARDWARE facts (driver/Fs/impedance), not the naming
  glossary** — `glossary.channels` (codes + active flag, consumed by `naming.py`) is a distinct,
  smaller list keyed by the same `code`. Two different questions: "what can this channel be
  called in a measurement title" vs. "what driver is actually wired to it."
- **`hardware.controls` is DSP-level, never per-preset** — see SCR-017 above; the per-preset ledger
  keeps only what genuinely varies per preset (`mute`, `off`).
- **Writes are atomic** (write-temp-then-rename) — a torn write must not read back as an empty
  project, the same reasoning `process.py._write` documents.
