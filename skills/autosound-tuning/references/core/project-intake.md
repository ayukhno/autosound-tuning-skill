# Project intake — the doctrine Phase −1 stands on

**The runbook moved** (the user's decision, 2026-09-16): what a session DOES in Phase −1 — the first-start
flow, the two interviews and generating the project files (§0.5, §1, §2, §5) — lives in
[`phases/phase_-1_intake.md`](references/phases/phase_-1_intake.md) under the same numbers. This file keeps
what holds beyond that session and what later phases cite: §0 the briefing (language, the reviewer as
the method's core), §3 install verification with its safety minima, §4 the DSP's capability level. Their
numbers did not change, so a `project-intake.md §3` or `§4` pointer still lands on its text.

---
## 0. Quickstart — what you need to have (a briefing for new hands)

> 🖥️ **Before the first question: ask the front-end, not the user.** If a `tcc` MCP server is
> connected, call `get_tcc_state` and read it as **answered**, not as a suggestion. It reports the
> project folder, the current phase, the **language** the Arbiter is working in (`language`, e.g.
> `"uk"`), and the reviewer they chose in the GUI's own controls (`reviewer.model`,
> `reviewer.reachable`, `reviewer.how`). Everything it reports was set by the user in the app
> before this conversation started — **do not ask them to confirm it.** Ask only about what the
> state leaves blank or what contradicts the disk.
>
> **And it may have asked more than those two.** The intake's fields, their enumerations and
> the couples that must be asked as ONE control are data since SCR-059 (`rew_tool/intake.py`),
> so a window may collect §1–§2 on a form and hand the answers over — up front only the fields whose `when` is `now`; each other field names the later step that asks it (2026-09-22). What that changes and what
> it does NOT — the phase still opened first, the rulings still recorded, the gates unmoved —
> is `phases/phase_-1_intake.md` §0.6.
>
> This changes which of the questions below you actually put: with a front-end, the language is the
> one the app is already speaking and the reviewer channel is already picked, so steps 1 and 2 of
> the sequence collapse into "note what the state says and move on". With no front-end, ask them
> exactly as written — this is an "if you are told, do not ask" rule, not a removal.
>
> **An answered step is a closed step.** Not asking is only half of it: leave the plan's language /
> reviewer step open and the panel shows an unfinished intake for the rest of the project, and the
> next session re-opens the question the app answered before the first one. Record what the state
> said and close it in the same breath:
>
> ```bash
> # The RULING is recorded the moment it is made, so nobody asks again; the STEP closes
> # against the artefact that carries it (`autosound_context.md`, written in `phase_-1_intake.md` §5).
> python3 rew_tool/state/process.py <project>/process decision "dialogue language" "uk" -1.1
>
> # The reviewer channel is closed by an ANSWER, not by a setting. One live check, recorded:
> python3 scripts/autosound_ai.py doctor | tee <project>/rew_analitic/reviewer-check.md
> python3 rew_tool/state/process.py <project>/process reviewer <vendor> <the model you named> -1.2 \
>   --review rew_analitic/reviewer-check.md
> python3 rew_tool/state/process.py <project>/process done -1.2 "rew_analitic/reviewer-check.md"
> ```
>
> ⚠️ **Why a live check and not "configured".** Evidence must RESOLVE — a file, a ledger version, a
> measurement name — and `"reviewer.model=…"`, `"reachable=true"` resolve to nothing, so the step
> this file used to demonstrate was refused by the gate when run exactly as printed. A channel that
> was configured and never answered is the one that fails in Phase 1, when a round is waiting on it.
> The doctor runs a live one-line smoke through the channel; `tee` leaves what it said in the
> project, and that file is what closes the step (user's ruling 2026-09-09).
>
> The evidence names where the answer came from AND where it now lives on disk — a state read is
> not by itself a fact a later session can check. A reviewer the state reports as **unreachable**
> is not done: block that step with the reason (`block -1.2 "clipboard-only until ..."`), because
> a channel that cannot be called is a channel the method does not have.

> 🌍 **First of all — the project's REPLY language, and it is READ before it is asked.** Three
> languages live in one session (S-045, his evidence 2026-09-20) and only the first is the method's:
>
> | | what it is | who owns it |
> |---|---|---|
> | **reply** | what the session writes in — the dialogue AND every generated project file (`autosound_context`, `tuning-changelog`, `dsp-state-current`, `audit-trail`, `skill-inbox`) | the method: `project.json` `language.reply`, written by `intake.save(<project>, "project.language", "<code>")` |
> | **interface** | what a front-end shows | the front-end. The method never invents it and never stores it as its own |
> | **input** | whatever the person happened to type | nobody — and it changes NEITHER of the other two |
>
> **Order:** a front-end's report (`get_tcc_state.language`) wins, because the app is where he set
> it; else the stored `language.reply` (`python3 rew_tool/project.py <project> language`, and
> `contract.py check` prints it above everything else); else ASK — *"English, or your native
> language? (supported: **EN · UK · DE · PL**)"* — and record the answer, so the next clean session
> reads it instead of asking again.
>
> **The input language is the trap.** On a Windows VM with no Ukrainian keyboard he typed English
> while the interface and the reply were Ukrainian; a session that takes its language from the last
> message flips the whole tune on one sentence forced by a missing layout. And reading the value
> without acting on it is the same failure as not reading it — one session named the mismatch out
> loud, answered in English anyway, and advised him to go fix it in the app. A read value that
> changes nothing is not a setting, it is trivia.
>
> The skill body stays English — it is the method skeleton. Claude will manage other languages too;
> EN/UK/DE/PL are the officially checked ones.

- **REW** with the API server enabled (Preferences → API; check: `localhost:4735` responds). A measurement mic **with calibration files** + a way to position it stably at the listening point (LP).
- **Your DSP's software** and a way to load EQ into it (ideally a file import; we'll find out in §4).
- The review protocol lives in **`references/core/review-loop.md`** (roles, TWO-PASS anti-anchoring, the loop rules) — read it before the first review round.
- **🔑 The reviewer (Critic-Advisor) — SET IT UP AT THE START. It's the CORE of the method, not an option** — the synergy of a second expert is a colossal quality gain (single-perspective tuning is noticeably worse). **Offer it to the user** and pick what's available (the fallback ladder):
  **The order to try is THE ladder — one list, and it lives in [`setup-critic-channel.md` §7](references/tooling/setup-critic-channel.md):** wait / retry → another vendor through `scripts/autosound_ai.py` (the recommended default — Generator one vendor, reviewer the other; verify with `python3 scripts/autosound_ai.py doctor`) → clipboard into any desktop chat → the same vendor at a higher tier, said out loud → a separate Claude session → the human. **A background sub-agent is not on it** (removed 2026-09-09): same-model review shares the model's blind spots, and a reviewer CLI spawned inside an agent session deadlocks. With nothing reachable, the round is blocked and says so.
  ⚠️ **Don't skip this step.** (The CLI CHANNEL is optional; the reviewer ROLE is not.)
- **What a working session looks like:** Pre-session checklist (hardware) → Resume (state) → work by phases (`process-phases.md`) → **Session close** (stopping is an event with a fixed order — `process.py … session-close` names what is still open; `SKILL.md` Pre-Session & Resume item 4, `process-control.md`) → Session log (handoff to the next session). A new project's first session = this whole file + Phase 0.

---

## 3. Install verification — BEFORE the first measurement

A new/unfamiliar/long-unmeasured install. Each item is cheap; a skipped one costs a session.

1. **Routing:** a quiet test signal to each DSP output in turn → exactly that driver plays. Also a "DSP channel → speaker" map into the profile.
2. **Polarity — electrically** (markings/a polarity tester/a battery test; NOT "by ear on the pair's center" — the classic trap, `diagnostic-techniques.md §16`). Later, at the joints — control by summation (§9).
3. **Protective crossovers BEFORE the first sweep — PROTECTION OF FRAGILE drivers ONLY, NOT the final crossovers:**
   * **Steep slope — a SAFETY MINIMUM (not a soft pattern):** Use a steep **24 dB/oct (LR4 or BW4)** slope for protective crossovers. This is a **hard safety floor**: gentler slopes (e.g. 12 dB/oct) do **not** protect fragile voice coils from low-frequency energy during sweeps → risk of exceeding $X_{max}$ and physically destroying the driver. You may go **more** conservative (steeper / higher), **never** less. *(Only the FINAL musical crossovers — designed in Phase 1 — are a tuning choice; this protective step and its minimums are hard safety, not hypotheses.)*
   * **Dynamic Fs-bound frequency — a SAFETY MINIMUM:** Bind the protective HPF to the *specific driver's* actual resonant frequency ($F_s$). Set it at **$1.1 \times F_s$ (never lower) to $1.5 \times F_s$** (rounded up). For example, for a tweeter with $F_s = 900$ Hz (like Hertz ML 280.3), set the protective HPF to **1000 Hz @ 24 dB/oct** (or higher for a wider safety margin at low sweep volumes). For midranges, do the same based on their $F_s$. An $F_s$ that `contract.py check` lists as **carried in from another project** is not this build's $F_s$ until the Arbiter confirms it (`project.py <dir> set-channel <code> fs_hz=<Hz> --source user`) or it is measured here (an impedance sweep, `<code> (imp)`) — skill #36.
   * **The Overlap Exposure Rule (Правило розкриття стику):** If we set the protective HPF too high, we blind ourselves to the expected crossover/overlap region, making it impossible to design the target acoustic slope or match phases. The protective HPF should be set **at least 1 octave below the anticipated crossover point** where possible, but **never below $1.1 \times F_s$**. To make this low crossover safe, the sweep measurement **must be run at a safe, moderate volume** (e.g., −20 dB FS, comfortable to the ear). For example: Tweeter $F_s = 900$ Hz, expected crossover = 3000 Hz. Setting the protective HPF to 3500 Hz ruins the measurement. Setting it to **1000 Hz @ 24 dB/oct** and running a **quiet sweep** completely protects the voice coil while fully exposing the tweeter's roll-off and phase down to 1000 Hz!
   * **No Silently Assumed State:** Since we cannot automatically program the DSP, you **must** output an explicit, high-visibility **"⚠️ ACTION REQUIRED: MANUAL DSP PROTECTION SETUP"** block. Command the user to open their Helix/DSP software and manually configure these protective crossovers in the physical hardware *before* taking any measurements.
   * **Other Drivers:** Midbass and sub HPF don't need protective crossovers for sweeps (they are built for LF); a subsonic HPF is only needed for a ported sub (sealed enclosures limit cone excursion naturally).
   * **No Anchoring:** The final crossover points and types are designed in **Phase 1**, after measurements are taken. Do not announce final crossover proposals at this stage to avoid anchoring.
   * **And AFTER the sweep — the other half of this rule (doctrine, 2026-08-24):** a protective filter is **in the recording**. It rotates phase far past its corner — an `LR4 @100` still leaves ~52° at 320 Hz, an `LR4 @1k` ~48° at 3.5 kHz — and nothing downstream can tell, because a protective `LR4 @100` and a designed one are the same filter. On the reference car the same junction read **−49° with the protection in and +3° with it out**. So: **a joint-phase decision read through a protective filter that has not been taken back out is invalid.** Two obligations follow. (1) **Record what was in the chain, on the capture round, in the same breath as the sweep** — `python3 rew_tool/state/process.py <project>/process capture-protective <ch> --hp 1000 LR 24` per protected driver, `… capture-protective <ch> OFF` for one swept bare; a front-end that marks protection writes the same record. **There are two answers and `OFF` is the default** (user's ruling 2026-09-06, hub TCC-005): `OFF` means *leave this capture alone* — the chain was bare, or it carried a working crossover that is part of the tune and is read as it is — and a recorded filter is the one case the maths removes before analysis. A front-end writes one of those two for **every** channel it captures, so a channel with no record at all did not come from it: MCP, a hand-typed call, a round older than that ruling, or a front-end that failed to write what it thought it wrote. (2) **Let the tools take it out** — `rew_tool.py analyze-joints --process <project>/process` de-embeds a solo marked raw before any delay / polarity / APF, and answers `check` for a baseline solo nobody recorded rather than guessing — which is now a question about where the record came from, not a state a person can click into; `resonalyze_ir.py --process` carries the same record into the v7 manifest, so the fact has one home. Never de-embed when verifying a finished tune — there the filter *is* the tune. The Overlap Exposure Rule above is what makes this possible at all: the region below the joint has to be in the recording to be recoverable. Code: `rew_tool/protective.py`; scope: `estimator-scope.md §2`.
4. **Gain staging:** minimum amp gain + maximum DSP level = better SNR; gain up to the first THD jump → back off ~10% (the RTA/THD procedure is in `helix-vcp-workflow.md`, the principle is generic for any DSP).
5. **Noise:** silence on a pause, engine off and running: alternator whine / ground loop / hiss → cure it (grounding, isolation, gains) **before** the tune — EQ won't fix it.
6. **Break-in of new drivers** (Hashimoto): a rough start-tune → break-in with music → a precise tune. New components "fall apart" one by one if you do a precise alignment without break-in.
7. **A safe sweep level:** start quiet, watch the THD / cone excursion; don't push an unknown driver to its limit.
8. **A clip check of the chain:** the DSP input doesn't clip on the measurement signal (ISA/RTA THD).

## 4. DSP capability checklist → which toolset is available

> **Before you ask any of this: the answers may already be shipped.** `knowledge/dsp/<vendor>-<model>.md`
> holds a filled-in, hardware-verified version of this checklist for processors the skill knows.
> Build the path from what the user just told you — "Helix DSP Ultra S" → `knowledge/dsp/helix-dsp-ultra-s.md`
> — and read it. Present what it says and ask only what it leaves open. If the file is not there,
> `ls knowledge/dsp/` once and move on to the interview; do **not** `find` for it (the skill is
> installed as a symlink, so a plain `find` returns nothing and costs minutes).

> **Two standing facts, so the table below is read for what it is.** (1) **No DSP hands us its
> settings.** Reading one means the owner transcribing or exporting its screens; writing back means
> a separate tool or the DSP's own EQ import. (2) **The REW API reads freely, but firing a sweep
> needs a Pro licence** (a control POST answers `401` without one) — so a human runs the measurement
> session either way, and the method is written for that.
>
> **🔑 The hinge of applicability = whether you can MEASURE PER-CHANNEL, NOT "whether the DSP is readable".** Two questions decide the method branch:
> 1. **Is the DSP state readable?** (a dump / screen-read `screen-read-dsp.md` / a file export) — you can see the current crossovers/TA/EQ/gains.
> 2. **Can you measure PER-CHANNEL?** (solo each output — §3.1, a sweep on each driver separately).
>
> | Level | DSP readable | Per-channel measurement | Mode |
> |---|:---:|:---:|---|
> | **1 — full** | ✅ | ✅ | the whole method as is (verify the state in the DSP, not from memory) |
> | **2 — black-box / reverse** | ❌ | ✅ | the current tune isn't visible → **reverse-engineer it from per-channel measurements** (read crossovers/TA/polarity/EQ from FR/phase/IR — `diagnostic-techniques §22`), then the normal flow. ⚠️ no read-back → **confirm every change ONLY by re-measurement** (change one at a time, re-measure after each — higher drift risk). ⚠️ **This one-at-a-time caution is Level-2-specific** (it exists only because there's no other way to confirm state) — **do NOT carry it into Level 1**, where multi-band EQ batches normally in one export/import round (`phase_2_eq.md` 2a.4). |
> | **3 — sum only** | ❌/✅ | ❌ (channels don't isolate) | crossover/phase/TA surgery is **impossible** → fall back to **the whole system's tonal balance to the target + imaging/staging BY EAR** (test tracks `test-tracks.md`, EMMA positions `emma-2024-test-track`); record the ceiling honestly ("no per-channel access — only tone+imaging, not joints") |
>
> ⚠️ "The DSP isn't readable" ≠ a dead end: almost always this is **Level 2** (solo outputs measure, the tune reverses from REW). Level 3 — only when channels physically can't be isolated.
>
> ### Path: virtual-first or iterative (an INTENT on top of the Level)
> The Level says what you CAN measure; the **path** says how the tune is DESIGNED. **Virtual-first** (one capture session → design at the desk against a predicted sum → verify → lock, [`virtual-first.md`](references/phases/virtual-first.md)) needs all three of: a **loopback rig on one clock** (a USB mic on acoustic loopback does NOT qualify — the base is through the air), a **hardware-verified DSP filter model** (Helix today), and the **capture discipline** of Phase 0. It also needs Level 1 (readable + per-channel) to enter the current setup and to trust the joint work. Miss one and the DESK half degrades to the iterative content of Phases 1–3 — but **run the Phase-0 capture session the same way regardless**; degrade only the desk and the verification, never the capture. The loss table and the degradation rule are in `virtual-first.md`.
>
> **Also pick the MODE here:** a **new tune** (full: −1 → 0 → desk → 3 → 4) or **improving an existing tune** (−1 → 3 → 4, no new solos — Phase 3 already holds a sum measurement, MMM, fine EQ and a verdict). Both READ the current DSP settings into the ledger first; on a Helix that is a one-time transcription from the PC-Tool screens (no reader for PC-Tool 6), and the EQ is the slowest part — say that cost now.
>
> ### Level 0 — light-touch entry (an INTENT, orthogonal to 1/2/3)
> Levels 1–3 answer *what you CAN do*; **Level 0 answers how much you WANT to do this session.** For a **small fine-tune of an already-working system** — nudge the tone, chase one symptom, or swap the target curve — you can **skip reading/reversing the full DSP state** and work only from **the current measurement + the target + basic car/equipment info**. The measurement is the acoustic truth regardless of which DSP params produced it, so a correction *toward the target from measured reality* needs no full state dump. This is the low-friction door for "I just want it a bit better", not a from-scratch build (that's the full Phase −1→5).
> - **Do:** measure the current result → compare to target → propose the correction from what's measured; don't first reconstruct the whole old DSP state.
> - **⚠️ The one real risk — double-correction, blind to existing filters.** Not seeing the current EQ, you can fight it: cut a dip the old EQ already boosted into, or stack a notch on an existing one. Guards: (1) **still read THAT channel's current filters before editing its EQ** (`get_filters`/`get_equaliser` — a cheap per-channel read, not a full dump; this is already the always-loaded anti-drift rule, and it's exactly what keeps Level 0 honest); (2) prefer **broad moves on a fresh voicing/virtual layer** over surgical output-EQ edits; (3) if a change doesn't behave as predicted on re-measure, suspect a hidden filter interaction → read more state.
> - **Escalate freely:** the phase gates are re-entrant (`process-phases.md`). If light-touch keeps fighting something invisible, promote to Level 1/2 (read/reverse the DSP). Level 0 is the fast entry, **not a ceiling.**

| Question | What it determines in the skill |
|---|---|
| Is there a **virtual/group layer** above the per-channel one? | The base+voicing architecture (`diagnostic §6`). None → voicing = linked L=R on the output EQ; careful with joint phase, voicing presets cost more |
| **How many slots does each tier physically have** (`max_count` per group)? | Whether a spare slot can be seen as spare. Count the processor's own slots, not the ones this car uses — the difference is exactly what's being asked for. ⚠️ Slot letters commonly **repeat across tiers** (Helix: virtual A–H, outputs A–L), so record which tier each spare belongs to (`tier`, SCR-042) rather than trusting the letter |
| **EQ:** bands/channel, types (PK/shelf/all-pass), **file import + format** | The canonical REW→DSP path (for Helix → `helix-eq-export.md`); no file import → **REW-EQ-CopyPaste-Assistant** (clipboard→keystrokes into the DSP software's window, 30+ platforms: Musway, ESX, Zapco… — `knowledge/dsp/helix-dsp-ultra-s.md` §EQ transfer) or tables by hand |
| **Crossovers:** types (LR/BW/BE), orders, independent HP/LP | Which sets from `filter-types-car-audio.md` are realizable |
| **Delays:** step and limits; **polarity** per-channel; **a phase control (all-pass)** | TA accuracy; the phase method (for Helix → `helix-phase-allpass.md`) |
| **Presets:** how many; **what resets on a switch (the input!)** | The "a preset silently reset the input" trap (Pre-session #4, `competition.md`) |
| **Input routing:** a separate input for the measurement signal? | Pre-session checklist #4 for this car |

**For non-Helix DSPs:** first check whether there's already a profile in `knowledge/dsp/` (and `knowledge/cars/` for this body — a library of community experience, `feedback-loop.md`). **Both halves are commands, not a reminder:** `python3 rew_tool/dsp_profile.py` → `find_bundled(vendor, model)` for the processor, and `python3 rew_tool/car_profile.py --find "<make>" "<model>" "<generation>" "<body>"` for the cabin (four parts; the older three-part form `"<make>" "<model>" "<generation+body>"` still works and slugs the same). Each answers `None` when there is no exact match, and **that is the answer** — it is what tells you to interview from scratch instead of going looking. **Ask about a previous PROJECT on the same body too**, which is a second place entirely — and it is a COMMAND now, not a reminder: `python3 rew_tool/car_profile.py --prior "<make>" "<model>" "<generation>" "<body>" <dir> [<dir>...]` returns the previous builds on exactly this cabin, how many measured flaw rows each offers and which captures its evidence names (`project_seed.py --describe <dir>` still answers for one directory you already know). ⚠️ It reports a project that never recorded its body as **unknown**, not as "no" — a sedan and a wagon cannot be told apart without it, and silence read as an answer is what this whole check exists to stop. Put that number to the person — "there are 18 rows from a previous build of this cabin, carry them as hypotheses?" is a question they answer, not a judgement you make quietly. ⚠️ **The match must be EXACT** (the same body / the same DSP) — another car's profile, even a platform sibling's, **must not be applied as fact and must not be named in the answer** (the full scope rule → `SKILL.md` → `knowledge/cars`). No exact match → **copy `knowledge/dsp/_TEMPLATE.md` → `knowledge/dsp/<dsp-slug>.md` and fill the capability profile** from the answers here (the filled worked example is `helix-dsp-ultra-s.md`). Only for **heavy** use of that DSP also create `references/<dsp>-workflow.md` — the equivalent of the trio `helix-vcp-workflow` / `helix-eq-export` / `helix-phase-allpass` (layer architecture, gain staging, the EQ exchange format, quirks). The Helix files = a structural template; the rest of the skill is DSP-agnostic. Same for a new BODY: copy `knowledge/cars/_TEMPLATE.md` → `knowledge/cars/<body-slug>.md` (PART A body-physics / PART B verify-only).

