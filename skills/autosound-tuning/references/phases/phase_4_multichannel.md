# Phase 4 — Center & Rear-Fill Integration (Optional)

This phase integrates the Center and Rear-Fill channels — an **optional, additive layer done LATE**.

> ⛔ **GATE: do NOT start center/rear until the FRONT genuinely SATISFIES** — technically locked (Phase 3) **and** subjectively OK to the user by ear (after the front's listening/fine-tuning in Phase 5 and any voicing in Phase 6). Center/rear on an unsatisfying front is **wasted work** — you'll redo it the moment the front changes. Finish the front first.

## 🎯 Goal-node

**Purpose:** integrate center + rear-fill **without dragging the front stage back** — an optional layer, only after the front is locked (Phase 3) **AND satisfies the user by ear** (post Phase 5/6). If the front isn't satisfying, go back and finish it first.

**Questions this phase answers:** does the center anchor focus without narrowing width? does rear-fill add envelopment without pulling the stage rearward?

**Required evidence:** measured center level/polarity/APF (verify, don't assume); summation at the LP for center polarity; the front-to-rear arrival difference for the Haas delay.

**✅ Quality gate → Phase 5:** front locked first; center bandwidth-limited + level/delay/polarity set by summation, anchors focus without narrowing; rear-fill differential L−R, band-limited, Haas-delayed, quiet (inaudible from the front but missed when muted); all logged to `dsp-state-current`.

**⚠️ Failure modes:** starting before the front is locked · center too loud/wideband (comb filtering, narrows the stage) · rear-fill audible / pulling the stage back · assuming params from logs instead of measuring.

**🧩 Refs:** center → [`diagnostic-techniques.md` §20](file:///skills/autosound-tuning/references/core/diagnostic-techniques.md); rear → [`voicing-by-ear.md` §Rear](file:///skills/autosound-tuning/references/patterns/voicing-by-ear.md).

---

## Core Guidelines & Safety Gate
* The center and rear-fill levels, polarities, and all-pass filters are part of the active **PROJECT state** (`dsp-state-current`).
* Prior to commencing work, **always verify these parameters via physical measurement**, rather than assuming values from past session logs.
* For comprehensive center setup rules, see [diagnostic-techniques.md §20](file:///skills/autosound-tuning/references/core/diagnostic-techniques.md).
* For comprehensive rear-fill tuning rules, see [voicing-by-ear.md §Rear](file:///skills/autosound-tuning/references/patterns/voicing-by-ear.md).

---

## 1. Center Channel Integration
Integrating a center channel introduces a third acoustic source, which can easily create comb filtering with the left/right midranges.

### Method A: Manual L+R Center
* **Narrow the Bandwidth:** Restrict the center channel to the core vocal range. Set a high-pass filter and a low-pass filter around **$1.0\text{ kHz}$ to $1.2\text{ kHz}$**.
* **Attenuate Levels:** Keep the center channel quiet. It is a subtle complement, not a primary source.
* **Determine Polarity/APF:** Match center polarity to the front mids by checking for maximum acoustic summation at the listening position.

### Method B: Algorithmic Center (e.g., Helix RealCenter)
* **Adjust Output Gain:** Dial in a level where the center anchors the phantom image focus without narrowing the horizontal soundstage width.
* **Dial in Delay:** Set center delay so its arrival does not precede the left/right front channels.
* **Resolve Phase Compression:** If the soundstage feels narrow, adjust the center channel's all-pass filters to manage phase overlap.
* **Center Tweeter (if present):** Set its high-pass filter high (**$6.0\text{ kHz}$ to $8.0\text{ kHz}$**) and keep the output gain very quiet (**$-6\text{ dB}$ to $-10\text{ dB}$**).

---

## 2. Rear-Fill Channel Integration
The objective of rear-fill is to provide a sense of acoustic **envelopment** without dragging the front soundstage backward.

### Standard Configuration
* **Differential L-R Matrix:** Utilize a differential routing matrix ($L-R$) to cancel mono vocal information from the rear speakers.
* **Bandwidth Limitation:** Restrict rear-fill frequencies to avoid aggravating door/cabin resonances. Set a high-pass filter above **$300\text{ Hz}$ to $315\text{ Hz}$** and a low-pass filter around **$4.0\text{ kHz}$ to $5.0\text{ kHz}$**.
* **Haas Delay:** Apply a time delay equal to the physical front-to-rear arrival difference **plus an extra $8\text{ ms}$ to $10\text{ ms}$** (the Haas precedence effect). This ensures the ear localizes all sound sources to the front while perceiving the rear channels as ambient spaciousness.
* **Attenuate Levels:** Set the rear-fill output gain quiet enough that the rear speakers are inaudible when sitting in the front seats, but their absence is immediately noticed as a loss of spaciousness when muted.

Log all finalized center and rear-fill parameters in the `dsp-state-current` register, then **re-check the full system by ear** (the center/rear must not have dragged the front back) and proceed to **Phase 7** (wrap-up).
