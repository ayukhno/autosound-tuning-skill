# community-inbox

Where community-contributed field experience lands before it's folded into the skill
(see `skills/autosound-tuning/references/core/feedback-loop.md` for the harvest → fold loop).

Three folders:

- **`setups/`** — per-vehicle setup + feedback packages: equipment, what worked, what
  didn't, generalizable know-how. One file per vehicle/session, named `<body>-<date>.md`
  (e.g. `passat-b8-2026-07-01.md`). Drop other people's setups here.
- **`case-studies/`** — narrative stories: a focused walk-through of one hard call and how
  it was solved (e.g. `case-study-mode-a-bass-2026-07-15.md`). Add other people's stories here.
- **`dsp-profiles/`** — machine-readable DSP capability profiles (`rew_tool/dsp_profile.py`
  schema), one file per model, named `<vendor>-<model>.json` (e.g. `musway-m6v4.json`). A DSP
  *model's* facts (what tiers/params it exposes), not one car's install — sent via
  `gates/side_effect.py::post_dsp_profile` right after an onboarding interview produces or
  extends a profile, not deferred to a satisfaction milestone like the other two folders (the
  facts are useful independent of whether that particular tuning project finishes).

Before sending, follow the **package safety rules** in `feedback-loop.md`: method + equipment
classes only — no names, locations, plate/VIN, photos, or raw `.mdat`; numbers decimated.
