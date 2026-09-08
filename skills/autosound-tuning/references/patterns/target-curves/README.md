# Target curves (skill library)

> 🗺️ **Not on SKILL.md's Reference Map — by design:** this file is the folder's own index, for a person browsing
> `references/patterns/target-curves/`. A session is sent to
> [`target_curves_guide.md`](./target_curves_guide.md) instead — two doors to the same room
> would be two doors to keep in step (autosound-hub `HUB-039`).

The comparison tool + this project's reference curve. A target curve is a **starting shape**,
not a finish and not a level — pick or build one **per project** (the bundled default is
SQ-Comp-Ref). Full guide: [`target_curves_guide.md`](./target_curves_guide.md).

## Contents
- **`curves/`** — loadable target curves (`freq  dB` text, REW/NTT format). Ships with
  **`SQ-Comp-Ref_0db_REW.txt`**, a reference curve **developed within this project**. Every `.txt`
  dropped here is auto-read by the tools — add your own, or ones you download (below).
- **`target_curves_guide.md`** — character comparison, how to load a curve, and building your own.
- **`deviation-analysis-audit.md`** — how far the Analyze panel's printed numbers can be trusted
  (audit against a real measurement, 2026-07-22). Read it when changing that math.
- **`target_curves_visualizer.html`** — interactive comparison (open in a browser; drag any `.txt` onto it).

## Community reference curves (Harman, Audiofrog, ResoNix, Jazzi, Whitledge …)
**Not bundled** — these are other people's published curves, so we don't redistribute them. Get them
from the **Nono Tuning Tool** ([nonotuningtool.com](https://nonotuningtool.com)) — it ships them as
built-in presets — then drop the exported `.txt` into `curves/` or straight onto the visualizer.

## Where per-project curves live
Your car's **chosen** curve and its **per-driver** targets (generated in Phase 1 after crossovers)
belong in the PROJECT's `rew_analitic/target-curves/<name>/`, **not** here. This skill folder holds
only the reusable standard references.
