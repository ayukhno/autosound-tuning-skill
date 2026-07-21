# Hard-params state — schema & usage

Versioned single-source-of-truth for a preset's **hard params** (crossovers · gains · TA · polarity ·
EQ pointers), the anti-drift anchor and the experimentation engine. Code: `state.py` (stdlib only).

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
  "preset": "SQ_Jazzi", "version": "v_002", "created": "…",   // version/created injected by snapshot()
  "sample_rate": 96000,                                       // samples DERIVED from this; ms is canonical
  "target": "Jazzi",
  "roles": {"artist": "Gemini", "producer": "Claude", "critic": null},   // roles-on-disk (AD-2)
  "provenance": {"decision": "clean-slate by-ear 2026-06-18"},
  "banked_ear_verdicts": [],
  "virtual_eq_ptr": null,
  "note": "sub INV test + w-L trim",                          // per-snapshot label, NOT diffed
  "channels": {
    "w-L": {"helix_ch": "C",
            "hp": {"f": 70, "type": "BW", "slope": 12},       // null / "OFF" when disabled
            "lp": {"f": 270, "type": "BW", "slope": 12},
            "gain_db": -7.8,
            "ta_ms": 5.38,                                    // CANONICAL; samples = round(ms*rate/1000)
            "polarity": "NORM",                               // NORM | INV
            "eq_ptr": {"output": "exports/w-L.req", "virtual": null},
            "status": "applied"}                              // proposed | applied | measured  (AD-1)
  }
}
```

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

## API / CLI
```python
from state import PresetHistory
h = PresetHistory(root, "SQ_Jazzi")
h.snapshot(state, note="…")   # -> "v_00N"   (validates, advances HEAD)
h.diff("v_001", "v_002")      # -> structured deltas (only changed fields)
h.render("v_002")             # -> Markdown settings sheet
h.revert("v_001")             # -> new snapshot == v_001 content
```
```
python state.py --root <dir> log|render|diff|revert <preset> [args]
python state.py selftest
```

## apply-change gate (`apply.py`)
The gate that turns a proposed delta into a banked snapshot + the human SETTINGS SHEET. The DSP is
entered by hand in Helix, so the gate can't touch the device — it earns its keep by being the ONLY
producer of the clean old→new sheet the Arbiter keys in (bypass = nothing usable → compliant = easiest).
```python
from state import PresetHistory
import apply
h = PresetHistory(root, "SQ_Jazzi")            # HEAD must exist (seed the first state via h.snapshot)
r = apply.propose(h, {"w-L": {"gain_db": -7.5, "ta_ms": 5.45}, "sub": {"polarity": "INV"}},
                  note="…")                     # -> banks 🟡 snapshot; r["sheet"] = the settings sheet
print(r["sheet"])                               # channel/param old→new, ms+derived samples, advisories
apply.attest(h)                                 # Arbiter entered it in Helix -> flip 🟡→🟢 applied (new snapshot)
```
- **Deterministic refusals (hard):** unknown channel/field (typo), partial edit of a non-existent
  channel, TA given as samples not `ta_ms`, or any result failing `validate` — a refused delta banks
  nothing.
- **Advisories (soft, waivable — the demoted noun-rails):** large gain jump, polarity flip, big
  delay/crossover move → printed ⚠️, never blocking; the ear + measurement rule the acoustic nouns.
- Lifecycle: `propose` 🟡 → `attest` 🟢 → 📏 after a control measurement confirms effect.
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
python state.py --root <dir> registry show|render
python state.py --root <dir> registry set-active <preset>
python state.py --root <dir> registry describe <preset> --label "Slot 3" --note "SQ-Comp-Ref"
```
