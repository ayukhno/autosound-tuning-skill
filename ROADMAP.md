# Roadmap

> **Draft.** This describes direction, not commitments or dates. Things here can change or drop as research plays out.

**Why:** lower the barrier to entry for non-expert users (terminal, dual-AI setup, manual DSP work, the tuning-decision role) — without changing the existing expert workflow.

## Now

- **Guided Setup Wizard** — interactive onboarding instead of manual README steps
- **Tuning Command Center (TCC)** — shows current tuning state, what to do manually vs. what happens automatically

## Next

*Research — these gate any automation work below, not the other way around.*

- Can DSP software GUIs be read and controlled reliably and safely? Under investigation.
- Hard safety limits on volume/EQ changes — this must be solved **before** any automated write to a real system, not after.
- Where a DSP brand supports direct control without a GUI, prefer that over automation.

## Later

*Depends on Next passing.*

- DSP GUI automation, once safety and reliability are proven
- A decision-support layer for tuning choices, with a trust level you control — from fully manual to, eventually, bounded automatic within limits you set yourself
- Expert track unchanged — same tools, plus the ability to build and share DSP maps for new hardware
