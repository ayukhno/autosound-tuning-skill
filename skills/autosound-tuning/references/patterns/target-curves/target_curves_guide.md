# Target-curve guide — choosing the character of the sound

A target ("house") curve is a **starting shape**, not a finish and not a level. You pick or
build one **per project**, then finalize it by ear after the raw baseline. This guide compares
the well-known reference curves and shows how to load one into NTT / REW.

> 🧩 A target curve is a **hypothesis**: a start, validated by measurement + ear. There is **no
> default**, and each project ends up with its own curve. See
> [`knowledge-architecture.md`](file:///skills/autosound-tuning/references/core/knowledge-architecture.md).

## Open the interactive comparison
Double-click to open in a browser (Chrome/Safari — VS Code's Restricted Mode blocks embedded SVG):
[target_curves_visualizer.html](file:///skills/autosound-tuning/references/patterns/target-curves/target_curves_visualizer.html)

## Standard reference curves (character)

| Curve | Focus | Sound & effect |
| :--- | :--- | :--- |
| **Audiofrog** (Andy Wehmeyer) | Neutral / linear | Studio-accurate (+~4.5 dB bass, gentle decline to 100 Hz). Correct timbre; can feel "dry" in a moving car. |
| **Harman car curve** | Deep sub-bass / HF rolloff | Big, full character (+~10 dB deep bass, −1.2 dB/oct HF). In sedans can boom and mask the mids. |
| **Jazzi v2** (NTT-style) | Strong bass + deep dip | +~9 dB sub-bass, sharp −4.5 dB dip near 2 kHz. Big stage illusion; the deep cut can hollow the vocal. |
| **ResoNix Accurate** | Balanced SQ reference | A popular, natural competition start — even balance, honest timbre, no extreme moves. |
| **Half Whitledge** | Warm, half the bass rise | Whitledge warmth with the bass rise ~halved → closer to neutral, lighter and faster. |

Curve files live in [`NTT/`](file:///skills/autosound-tuning/references/patterns/target-curves/NTT).

## Building your OWN target (per project)

Narrow by the user's genres/taste — the curve→character table in
[`voicing-by-ear.md`](file:///skills/autosound-tuning/references/patterns/voicing-by-ear.md) — to
2–3 candidates, then audition by ear (finalized **after** the Phase-0 baseline, with measured reality
in hand). A competition-oriented curve is often a moderate, collected bass + a gentle HF decline +
a soft presence pocket (to push the stage behind the glass) — but the exact shape is yours to build
and confirm by measurement. Export a 2-column `freq  dB` file (log-spaced, 20 Hz–20 kHz) into this
project's `rew_analitic/target-curves/<name>/`.

## Loading a curve

**NTT (nonotuningtool.com):** *Custom Target Curve* → import your `.txt` → it pulls the shape (and,
with the per-band/stereo config, generates the per-driver targets — see Phase 1 §5).

**REW:** *Preferences → House Curve → Browse* your `.txt`; in the EQ window enable
*Add room curve to target* so REW designs filters to your curve.
