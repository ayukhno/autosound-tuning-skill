# Target curves (skill library)

Standard reference target curves + the comparison tool. A target curve is a **starting shape**,
not a finish and not a level — pick or build one **per project** (there is no default). Full
guide: [`target_curves_guide.md`](./target_curves_guide.md).

## Contents
- **`NTT/`** — standard reference curves at 0 dB (REW/NTT format): Audiofrog, Harman, Jazzi v2,
  ResoNix Accurate, Half Whitledge.
- **`target_curves_guide.md`** — character comparison, how to load into NTT/REW, and building your own.
- **`target_curves_visualizer.html`** — interactive comparison (open in a browser).

## Where per-project curves live
Your car's **chosen** curve and its **per-driver** targets (generated in Phase 1 after crossovers)
belong in the PROJECT's `rew_analitic/target-curves/<name>/`, **not** here. This skill folder holds
only the reusable standard references.
