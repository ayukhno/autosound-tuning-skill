# Target-curve guide — choosing the character of the sound

A target ("house") curve is a **starting shape**, not a finish and not a level. You pick or
build one **per project**, then finalize it by ear after the raw baseline. This guide compares
the well-known reference curves and shows how to load one into NTT / REW.

> 🧩 A target curve is a **hypothesis**: a start, validated by measurement + ear. There is **no
> default**, and each project ends up with its own curve. See
> [`knowledge-architecture.md`](file:///skills/autosound-tuning/references/core/knowledge-architecture.md).

## Open the interactive comparison
`target_curves_visualizer.html` is **fully self-contained — it works OFFLINE** (Chart.js is inlined; no CDN / no internet needed — important when tuning in the car). Open it in a browser:
- **Quickest:** open **`curves.html`** — every project gets one **symlinked at its own root** during intake (`project-intake.md §5`), so it's right there without digging into the skill's folders. The skill root also has one (`skills/autosound-tuning/curves.html`) — same one-click launcher, either copy works.
- **macOS:** `open <skill-dir>/references/patterns/target-curves/target_curves_visualizer.html` (or double-click it in Finder → opens in your default browser).
- **Any OS:** double-click the file, or drag it onto a browser tab.

*(When an assistant is driving the session, it can launch it for the user by running `open` on the resolved path — the file's location is known once the skill is loaded.)*

## Standard reference curves (character)

| Curve | Focus | Sound & effect |
| :--- | :--- | :--- |
| **EMMA-Ref v3** (this project — **bundled**) | Juicy + SQ-accurate | Deep juicy sub-bass (+9 dB), ultra-smooth decline to 200 Hz (kills boom), a −2 dB stage dip at 2.5 kHz, natural HF decline (−0.5 dB/oct). The only curve that **ships with the skill** (`curves/`). |
| **Audiofrog** (Andy Wehmeyer) | Neutral / linear | Studio-accurate (+~4.5 dB bass, gentle decline to 100 Hz). Correct timbre; can feel "dry" in a moving car. |
| **Harman car curve** | Deep sub-bass / HF rolloff | Big, full character (+~10 dB deep bass, −1.2 dB/oct HF). In sedans can boom and mask the mids. |
| **Jazzi v2** (NTT-style) | Strong bass + deep dip | +~9 dB sub-bass, sharp −4.5 dB dip near 2 kHz. Big stage illusion; the deep cut can hollow the vocal. |
| **ResoNix Accurate** | Balanced SQ reference | A popular, natural competition start — even balance, honest timbre, no extreme moves. |
| **Half Whitledge** | Warm, half the bass rise | Whitledge warmth with the bass rise ~halved → closer to neutral, lighter and faster. |

Only **EMMA-Ref v3** ships with the skill (in [`curves/`](file:///skills/autosound-tuning/references/patterns/target-curves/curves)). The five community curves above are **downloaded from the Nono Tuning Tool** ([nonotuningtool.com](https://nonotuningtool.com)) — not redistributed here — then dropped into `curves/` or onto the visualizer.

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
