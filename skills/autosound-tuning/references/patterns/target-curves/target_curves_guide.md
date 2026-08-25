# Target-curve guide — choosing the character of the sound

A target ("house") curve is a **starting shape**, not a finish and not a level. You pick or
build one **per project**, then finalize it by ear after the raw baseline. This guide compares
the well-known reference curves and shows how to load one into NTT / REW.

> 🧩 A target curve is a **hypothesis**: a start, validated by measurement + ear. There is **no
> default**, and each project ends up with its own curve. See
> [`knowledge-architecture.md`](references/core/knowledge-architecture.md).

## Open the interactive comparison
`target_curves_visualizer.html` is **fully self-contained — it works OFFLINE** (Chart.js is inlined; no CDN / no internet needed — important when tuning in the car). Open it in a browser:
- **Quickest:** open **`curves.html`** — every project gets one **symlinked at its own root** during intake (`project-intake.md §5`), so it's right there without digging into the skill's folders. The skill root also has one (`skills/autosound-tuning/curves.html`) — same one-click launcher, either copy works.
- **macOS:** `open <skill-dir>/references/patterns/target-curves/target_curves_visualizer.html` (or double-click it in Finder → opens in your default browser).
- **Any OS:** double-click the file, or drag it onto a browser tab.

*(When an assistant is driving the session, it can launch it for the user by running `open` on the resolved path — the file's location is known once the skill is loaded.)*

## Standard reference curves (character)

| Curve | Focus | Sound & effect |
| :--- | :--- | :--- |
| **SQ-Comp-Ref** (this project — **bundled**) | Deep, controlled + SQ-accurate | Deep sub-bass floor (+9 dB), ultra-smooth decline to 200 Hz (kills boom), a −2 dB stage dip at 2.5 kHz, natural HF decline (−0.5 dB/oct). The only curve that **ships with the skill** (`curves/`). |
| **Audiofrog** (Andy Wehmeyer) | Neutral / linear | Studio-accurate (+~4.5 dB bass, gentle decline to 100 Hz). Correct timbre; can feel "dry" in a moving car. |
| **Harman car curve** | Deep sub-bass / HF rolloff | Big, full character (+~10 dB deep bass, −1.2 dB/oct HF). In sedans can boom and mask the mids. |
| **Jazzi v2** (NTT-style) | Strong bass + deep dip | +~9 dB sub-bass, sharp −4.5 dB dip near 2 kHz. Big stage illusion; the deep cut can hollow the vocal. |
| **ResoNix Accurate** | Balanced SQ reference | A popular, natural competition start — even balance, honest timbre, no extreme moves. |
| **Half Whitledge** | Warm, half the bass rise | Whitledge warmth with the bass rise ~halved → closer to neutral, lighter and faster. |

Only **SQ-Comp-Ref** ships with the skill (in [`curves/`](references/patterns/target-curves/curves)). The five community curves above are **downloaded from the Nono Tuning Tool** ([nonotuningtool.com](https://nonotuningtool.com)) — not redistributed here — then dropped into `curves/` or onto the visualizer.

## Building your OWN target (per project)

Narrow by the user's genres/taste — the curve→character table in
[`voicing-by-ear.md`](references/patterns/voicing-by-ear.md) — to
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


## Loading a curve the page does not bundle (URL fragment)

The visualizer carries only the curves in `curves/`. To show one it does not bundle — a project's
target that lives elsewhere — open it with the curve in the URL **fragment** (a front-end like TCC
does this so a clicked target opens as itself, not silently as a bundled curve):

```
target_curves_visualizer.html#curve=<encodeURIComponent(name)>&data=<encodeURIComponent(REW text)>
```

The fragment never leaves the browser (it is not sent to any server), so the page stays static and
nothing is published. The curve loads at its own level (offset 0) — exactly the values in the text —
and the per-curve level buttons adjust it after. A `SQ-Comp-Ref`-sized curve is ~3 KB; comment lines
may be dropped and dB rounded to one decimal if a payload ever approaches the browser URL limit
(tens of KB). Added 2026-08-25 at autosound-tcc's request.
