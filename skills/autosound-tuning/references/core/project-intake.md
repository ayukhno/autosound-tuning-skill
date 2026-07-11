# New project — briefing, interview, install verification, files (Phase −1)

**When you come here:** Resume finds no project files · a new car/system · a new or reworked install · the skill was handed to new hands · "tune from scratch". This is the **project's first session**: interview + verification first, only then the first measurement (Phase 0).

> **"The same car, but from scratch":** the profile (`autosound_context.md`) already exists — do NOT recreate it. Go through only §2 (goals/curve — they may have changed) + §3 (verification: the install may have drifted), archive the old history (changelog/dsp-state) with a marker, start a new one. Classifying the trigger "what raw data is still valid" → `naming-and-structure.md §2`.

---

## 0. Quickstart — what you need to have (a briefing for new hands)

> 🌍 **First of all — the local project's language.** Ask the user: *"English, or your native language? (supported: **EN · UK · DE · PL**)"*. From then on, **the whole dialogue AND all generated project files** (`autosound_context`, `tuning-changelog`, `dsp-state-current`, `audit-trail`, `skill-inbox`) — **in the chosen language**. The skill body is English (it's just the method skeleton) — the conversation and artifacts follow the user's language; Claude will manage other languages too, but EN/UK/DE/PL are the officially checked ones.

- **REW** with the API server enabled (Preferences → API; check: `localhost:4735` responds). A measurement mic **with calibration files** + a way to position it stably at the listening point (LP).
- **Your DSP's software** and a way to load EQ into it (ideally a file import; we'll find out in §4).
- The review protocol lives in **`references/core/review-loop.md`** (roles, TWO-PASS anti-anchoring, the loop rules) — read it before the first review round.
- **🔑 The reviewer (Critic-Advisor) — SET IT UP AT THE START. It's the CORE of the method, not an option** — the synergy of a second expert is a colossal quality gain (single-perspective tuning is noticeably worse). **Offer it to the user** and pick what's available (the fallback ladder):
  - **(1) Automated Scripts (CLI/API) — RECOMMENDED DEFAULT (a second, different AI vendor).** Runs the per-vendor wrappers `scripts/{gemini,claude,codex}_*.sh` (auto-detects the CLI — `agy` / `@google/gemini-cli` — or `autosound_ai.py` via an API key). **Pair Claude + Gemini** (Generator one vendor, reviewer the other) for true cross-vendor anti-anchoring. Verify with `scripts/gemini_critic.sh --doctor`. See `references/tooling/setup-critic-channel.md`.
  - **(2) Clipboard Mode (Manual Web-Chat) — robust, no CLI.** Copy-paste packages into a second AI's desktop/web chat (ChatGPT, Claude, Gemini Advanced) and paste the reply back. No CLI/key needed.
  - **(3) Human Reviewer.**
  - **(4) Autopilot self-loop — FALLBACK (only when no second AI is available).** The Generator spawns an isolated subagent `critic_advisor` in the same terminal — zero-config, no second-model setup. ⚠️ Same-model review shares the model's blind spots (not true cross-vendor anti-anchoring) and is where long autonomous sessions drifted (lost DSP state/phase). Use only if options 1–3 aren't available.
  ⚠️ **Don't skip this step.** (The CLI CHANNEL is optional; the reviewer ROLE is not.)
- **What a working session looks like:** Pre-session checklist (hardware) → Resume (state) → work by phases (`process-phases.md`) → Session log (handoff to the next session). A new project's first session = this whole file + Phase 0.

---

## 0.5 — First-start guided flow (run IN ORDER; clear each gate before the next)

A new project's first contact has a fixed order, but the detail is spread across this file + `process-phases.md` Phase 0 — and fresh sessions keep **skipping** a step (the glossary before measuring, the loopback, the reviewer). So run it as ONE sequence; the detail of each step is in the section noted — **this is the order + the gates:**

1. **Language** (§0) — ask EN/UK/DE/PL; the dialogue AND every project file follow it.
2. **Reviewer channel** (§0) — offer it and set it up NOW (the method's core, not an afterthought; `setup-critic-channel.md`).
3. **Interview** (§1–§2) — equipment (§1) + goals (§2: competition vs for-yourself vs both · **the reference seat — driver / passenger / all** · music & taste) + the curve seed → write `autosound_context.md`.
4. **REW rig ready** — the mic + its cal files loaded; the sample rate = the DSP's native rate where possible; a **physical loopback** wired (without it, phase/timing reads are unreliable → lean on summation/ear); the right input/output devices selected; the measurement input **doesn't clip** (§3.8); the API answers at `localhost:4735`.
5. **Naming + glossary — AGREE BEFORE ANY MEASUREMENT.** ⛔ **Gate:** don't measure until the channel codes (`sw / w-L/R / m-L/R / tw-L/R / c / r`) AND the convention `<ch>_<vN> (sw|rta)` are set with the user (`naming-and-structure.md §3`). The recurring slip is running off to measure with un-agreed names → an unusable history.
6. **Install verification** (§3) — routing · electrical polarity · protective crossovers (fragile drivers only, above each Fs) · gain staging · noise · break-in of new drivers · a safe sweep level. ⛔ **Gate:** don't tune before this.
7. **Generate the project files** (§5).
8. **First baseline** (Phase 0) — **each driver solo**, the agreed names: `<ch>_1 (sw)` + `<ch>_1 (rta)` per driver, a RAW current-state capture on the clean `v0` (no TA/EQ) → this per-driver set feeds Phase 1 (which does not re-collect it).

> Steps 1–3 are the interview; 4–5 ready the rig and the language of the data; 6 protects the hardware; 7–8 produce the first real measurements. The two ⛔ gates — **measure only after naming, tune only after verification** — are where fresh sessions most often slip.

---

## 1. Interview: equipment and system → the project profile

Ask in blocks, record the answers right away in `autosound_context.md` (structure — §5 below). Don't assume — ask; "I don't know" is also an answer (then we measure / look in the DSP software).

> ⚠️ **Take install/gear specifics ONLY from here (from the user) or from measurement — NOT from a `knowledge/cars`|`dsp` profile.** Driver placement/orientation/coplanarity, the gain-staging level (e.g. Output −6 dB), crossover numbers, anomaly frequencies — all of these depend on the SPECIFIC install/amps and **vary even on the same body/DSP**. A profile = a checklist to "verify", not facts to cite. Never "your X = Y" without the user's words or a measurement.

1. **Car:** make/model/body (sedan vs hatch/wagon → room gain and low-frequency behavior), LHD/RHD (the listener's side → the direction of the L/R asymmetry).
2. **Sound source(s):** HU/streamer/phone; **how the signal enters the DSP** (optical/coax/RCA/BT/USB); **which input is for listening, and which is for the measurement signal** (this goes into the Pre-session checklist #4).
3. **DSP:** model → the full capability checklist in **§4** (it determines which of the skill's tools are available). *(Just a small fine-tune of an already-working system? You can enter **light-touch = Level 0** — §4 — and skip the full DSP dump, working from the measurement + target.)*
4. **Amplifiers:** model/channels/input sensitivity (for gain staging), what's on which channel.
5. **Drivers:** model, size, **the position and orientation of EACH** (door / A-pillar / kick / dash / deck; where it points), enclosure (pod/sealed/free-air volume), mass/character (a heavy midbass → align to the IR peak, `car-eq-patterns.md`), **new or broken-in** (new → break-in, §3.6).
6. **Sub:** enclosure (sealed/ported), volume, location, how it's driven.
7. **Center / rear:** present or not, how they're driven (an FX algorithm / manual L+R / separate channels) — this determines the Phase-4 method.
8. **Mic rig:** mic + cal files (0°/90°), interface, **whether a physical loopback is possible** (without it, phase-critical measurements are unreliable → more weight to summation/the ear), sample rate (where possible = the DSP's native rate).
9. **Project paths:** where the context/audit/measurements will live (local project parameters, NOT skill constants; typically — the project's git repo, structure in §5).

## 2. Interview: goals and taste → the curve seed and Phase 5

Ask it the way the user thinks of it — a few **branching** questions, in this order:

> 📂 **Route each answer into the right layer** (see [`preference-profile.md`](file:///skills/autosound-tuning/references/core/preference-profile.md)): answers that **shape the engineering** → **Engineering Profile** (`autosound_context.md`): purpose/competition format (#1), reference seat (#2), stage priorities & physical ceilings (#4), hard constraints (#7). **Pure taste** → **Preference Profile** (`preference-profile.md`), applied only in Phase 5: music & loudness (#3), taste axes (#5), curve character (#6).

1. **Purpose (the first fork):**
   - **Competition** → which format(s): **EMMA / AYA / CARMusic — one, several, or all.** ⚠️ Formats judge differently and some techniques are **mutually exclusive** (e.g. crossfeed stabilises an EMMA stage but is never used for AYA) → "several/all" = **separate presets**, not one tune (`competition.md`, `preset-strategy.md`). A format names a **GOAL**, not a slope recipe (`knowledge/approaches.md`).
   - **For yourself (daily enjoyment)** → fan out into #3 (music · loudness · taste).
   - **Both** → competition preset(s) + an enjoyment preset; base+voicing makes the second cheap.
2. **Who is the tune FOR — the reference seat(s)** (ask explicitly; it's a GOAL, not a detail): the **driver only** / the **front passenger too** / **all seats**. (The car's **LHD/RHD** from §1 sets the *direction* of the L/R asymmetry.) ⚠️ This decides what the tune **optimises**: a **single seat** can be fully centred and imaged — one listening point is THE reference; **all seats** is a deliberate **compromise** — no perfect phantom centre for anyone, you trade per-seat perfection for an even spread. Settle it up front — it changes the centering/TA strategy (`diagnostic-techniques.md §16`), not just a level.
3. **Music & how you listen (the "for-yourself" branch):** genres + **what you love most** (bass · vocals · winds & strings · acoustic · electronica) → seeds the curve character; 3–5 favourite reference tracks; **how loud** (loud vs moderate → equal-loudness, `staging-depth.md §3`); long/short trips; **which test-track library** you have (a loaded compilation — CarMus / Chesky / EMMA-AYA disc — or a streaming service) → Phase 4 proposes only from what you can play (`test-tracks.md`).
4. **What stage we're building** (priorities — you can't maximize everything at once): width / depth-layering / height / a tight center focus; rear envelopment or front-only. State the physical ceilings honestly: depth is limited by the mid's geometry (`staging-depth.md §4`), envelopment needs a rear.
5. **Taste axes:** warm↔bright · bass-heavy↔neutral · forward↔laid-back · accuracy↔fun.
6. **Choosing the target curve — TOGETHER with the user, there is NO default.** Walk through the **curve→character** table (`voicing-by-ear.md`), narrow it by genres/taste to 2–3 candidates, finalize via the curve-audition method (same place) or take a candidate as the session's start and validate by ear in Phase 4/5. **A curve = a start and a shape, not a finish and not a level** (`naming-and-structure.md §6`). ⚠️ The curve is only **SEEDED** here — it's finalised AFTER the raw baseline (Phase 0), with the measured reality in hand.
7. **Anything else you want from this system?** ⚠️ **The branches above are the COMMON ones, not a closed list — always leave room for the user's OWN wishes.** Capture any wish **in the user's own words**, then **map it to where it lands in the tune** rather than forcing it into a predefined box: the curve character · a Phase-6 voicing move (`voicing-by-ear.md`) · a separate preset (`preset-strategy.md`) · a hard constraint or an honest ceiling (state it) · an install/gear note. If a wish doesn't fit any box, **record it as an explicit project goal** and address it on its own terms. Examples a user might raise: "match how this one track sounds", "no harsh top when it's loud", "keep the nav prompts clear over music", "I don't want to cut into the doors", "make it sound like the demo car I heard". A free-form wish is always welcome — it's what makes the tune fit THIS person, not a generic target.

> **The order the user pictures (and the skill follows):** goals (this §2) → **equipment analysis** (§1 + the DSP capability §4) → **raw baseline measurement** (Phase 0) → **finalise the target curve** → tuning. The curve is chosen *with* the measurement, not before it.

## 3. Install verification — BEFORE the first measurement

A new/unfamiliar/long-unmeasured install. Each item is cheap; a skipped one costs a session.

1. **Routing:** a quiet test signal to each DSP output in turn → exactly that driver plays. Also a "DSP channel → speaker" map into the profile.
2. **Polarity — electrically** (markings/a polarity tester/a battery test; NOT "by ear on the pair's center" — the classic trap, `diagnostic-techniques.md §16`). Later, at the joints — control by summation (§9).
3. **Protective crossovers BEFORE the first sweep — PROTECTION OF FRAGILE drivers ONLY, NOT the final crossovers:**
   * **Steep slope — a SAFETY MINIMUM (not a soft pattern):** Use a steep **24 dB/oct (LR4 or BW4)** slope for protective crossovers. This is a **hard safety floor**: gentler slopes (e.g. 12 dB/oct) do **not** protect fragile voice coils from low-frequency energy during sweeps → risk of exceeding $X_{max}$ and physically destroying the driver. You may go **more** conservative (steeper / higher), **never** less. *(Only the FINAL musical crossovers — designed in Phase 1 — are a tuning choice; this protective step and its minimums are hard safety, not hypotheses.)*
   * **Dynamic Fs-bound frequency — a SAFETY MINIMUM:** Bind the protective HPF to the *specific driver's* actual resonant frequency ($F_s$). Set it at **$1.1 \times F_s$ (never lower) to $1.5 \times F_s$** (rounded up). For example, for a tweeter with $F_s = 900$ Hz (like Hertz ML 280.3), set the protective HPF to **1000 Hz @ 24 dB/oct** (or higher for a wider safety margin at low sweep volumes). For midranges, do the same based on their $F_s$.
   * **The Overlap Exposure Rule (Правило розкриття стику):** If we set the protective HPF too high, we blind ourselves to the expected crossover/overlap region, making it impossible to design the target acoustic slope or match phases. The protective HPF should be set **at least 1 octave below the anticipated crossover point** where possible, but **never below $1.1 \times F_s$**. To make this low crossover safe, the sweep measurement **must be run at a safe, moderate volume** (e.g., −20 dB FS, comfortable to the ear). For example: Tweeter $F_s = 900$ Hz, expected crossover = 3000 Hz. Setting the protective HPF to 3500 Hz ruins the measurement. Setting it to **1000 Hz @ 24 dB/oct** and running a **quiet sweep** completely protects the voice coil while fully exposing the tweeter's roll-off and phase down to 1000 Hz!
   * **No Silently Assumed State:** Since we cannot automatically program the DSP, you **must** output an explicit, high-visibility **"⚠️ ACTION REQUIRED: MANUAL DSP PROTECTION SETUP"** block. Command the user to open their Helix/DSP software and manually configure these protective crossovers in the physical hardware *before* taking any measurements.
   * **Other Drivers:** Midbass and sub HPF don't need protective crossovers for sweeps (they are built for LF); a subsonic HPF is only needed for a ported sub (sealed enclosures limit cone excursion naturally).
   * **No Anchoring:** The final crossover points and types are designed in **Phase 1**, after measurements are taken. Do not announce final crossover proposals at this stage to avoid anchoring.
4. **Gain staging:** minimum amp gain + maximum DSP level = better SNR; gain up to the first THD jump → back off ~10% (the RTA/THD procedure is in `helix-vcp-workflow.md`, the principle is generic for any DSP).
5. **Noise:** silence on a pause, engine off and running: alternator whine / ground loop / hiss → cure it (grounding, isolation, gains) **before** the tune — EQ won't fix it.
6. **Break-in of new drivers** (Hashimoto): a rough start-tune → break-in with music → a precise tune. New components "fall apart" one by one if you do a precise alignment without break-in.
7. **A safe sweep level:** start quiet, watch the THD / cone excursion; don't push an unknown driver to its limit.
8. **A clip check of the chain:** the DSP input doesn't clip on the measurement signal (ISA/RTA THD).

## 4. DSP capability checklist → which toolset is available

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
> ### Level 0 — light-touch entry (an INTENT, orthogonal to 1/2/3)
> Levels 1–3 answer *what you CAN do*; **Level 0 answers how much you WANT to do this session.** For a **small fine-tune of an already-working system** — nudge the tone, chase one symptom, or swap the target curve — you can **skip reading/reversing the full DSP state** and work only from **the current measurement + the target + basic car/equipment info**. The measurement is the acoustic truth regardless of which DSP params produced it, so a correction *toward the target from measured reality* needs no full state dump. This is the low-friction door for "I just want it a bit better", not a from-scratch build (that's the full Phase −1→5).
> - **Do:** measure the current result → compare to target → propose the correction from what's measured; don't first reconstruct the whole old DSP state.
> - **⚠️ The one real risk — double-correction, blind to existing filters.** Not seeing the current EQ, you can fight it: cut a dip the old EQ already boosted into, or stack a notch on an existing one. Guards: (1) **still read THAT channel's current filters before editing its EQ** (`get_filters`/`get_equaliser` — a cheap per-channel read, not a full dump; this is already the always-loaded anti-drift rule, and it's exactly what keeps Level 0 honest); (2) prefer **broad moves on a fresh voicing/virtual layer** over surgical output-EQ edits; (3) if a change doesn't behave as predicted on re-measure, suspect a hidden filter interaction → read more state.
> - **Escalate freely:** the phase gates are re-entrant (`process-phases.md`). If light-touch keeps fighting something invisible, promote to Level 1/2 (read/reverse the DSP). Level 0 is the fast entry, **not a ceiling.**

| Question | What it determines in the skill |
|---|---|
| Is there a **virtual/group layer** above the per-channel one? | The base+voicing architecture (`diagnostic §6`). None → voicing = linked L=R on the output EQ; careful with joint phase, voicing presets cost more |
| **EQ:** bands/channel, types (PK/shelf/all-pass), **file import + format** | The canonical REW→DSP path (for Helix → `helix-eq-export.md`); no file import → **REW-EQ-CopyPaste-Assistant** (clipboard→keystrokes into the DSP software's window, 30+ platforms: Musway, ESX, Zapco… — `knowledge/dsp/helix-dsp-ultra-s.md` §EQ transfer) or tables by hand |
| **Crossovers:** types (LR/BW/BE), orders, independent HP/LP | Which sets from `filter-types-car-audio.md` are realizable |
| **Delays:** step and limits; **polarity** per-channel; **a phase control (all-pass)** | TA accuracy; the phase method (for Helix → `helix-phase-allpass.md`) |
| **Presets:** how many; **what resets on a switch (the input!)** | The "a preset silently reset the input" trap (Pre-session #4, `competition.md`) |
| **Input routing:** a separate input for the measurement signal? | Pre-session checklist #4 for this car |

**For non-Helix DSPs:** first check whether there's already a profile in `knowledge/dsp/` (and `knowledge/cars/` for this body — a library of community experience, `feedback-loop.md`). ⚠️ **The match must be EXACT** (the same body / the same DSP) — another car's profile, even a platform sibling's, **must not be applied as fact and must not be named in the answer** (the full scope rule → `SKILL.md` → `knowledge/cars`). No exact match → **copy `knowledge/dsp/_TEMPLATE.md` → `knowledge/dsp/<dsp-slug>.md` and fill the capability profile** from the answers here (the filled worked example is `helix-dsp-ultra-s.md`). Only for **heavy** use of that DSP also create `references/<dsp>-workflow.md` — the equivalent of the trio `helix-vcp-workflow` / `helix-eq-export` / `helix-phase-allpass` (layer architecture, gain staging, the EQ exchange format, quirks). The Helix files = a structural template; the rest of the skill is DSP-agnostic. Same for a new BODY: copy `knowledge/cars/_TEMPLATE.md` → `knowledge/cars/<body-slug>.md` (PART A body-physics / PART B verify-only).

## 5. Generate the project files

In the new project's root (a git repo; layout and the "what's in git, what isn't" rule → `naming-and-structure.md §4a`):

- **`curves.html`** — a symlink to the skill's target-curve visualizer, right at the project root, so the tool is one click away instead of buried in the skill's folders: `ln -s <skill-dir>/curves.html curves.html`. **`.gitignore` it** — an absolute-path symlink is machine-specific (same pattern as `.agents/skills/`); re-link it with the command above on a new machine.
- **`autosound_context.md`** — the profile: §1 equipment · §2 channels/routing · §3 measurement rig · §4 targets/curve/crossovers (the active curve → `rew_analitic/target-curves/<name>/`) · §5 **channel glossary** (agree the codes with the user; grammar `sw / w-L/R / m-L/R / tw-L/R / r-L/R / c-*`, pairs/combos/joints — `naming-and-structure.md §3`) · §6 the experience/anomaly log (empty — the sessions will fill it). Template — the Passat B8 profile.
- **`preference-profile.md`** — the **Preference Profile** (layer 4): pure voicing preferences (taste axes, loudness habit, favourite tracks, curve character), kept separate from the Engineering Profile above and applied only in Phase 5. See `references/core/preference-profile.md`.
- **`dsp-state-current`** + **`tuning-changelog`** (with a ▶️ CONTINUE block at the top) — project memory. **If the system will run several presets in physical DSP slots**, seed the versioned state per preset (`rew_tool/state/`) and set the live one (`state.py registry set-active <preset>`); `registry render` then *generates* the multi-slot `dsp-state-current` (active-slot banner + isolated per-slot rows) so the model can't anchor on the wrong slot (issue #5).
- **`audit-trail.md`** (the canonical decision log) + **`skill-inbox.md`** (empty, with a rules header).
- **`rew_analitic/`**: `dsp-config/` + a `README.md` map · `exports/` · **`target-curves/`** (house/target curves; **a subfolder per curve** = the full curve + per-band components with crossovers in the names; a `README.md` map: which is the **ACTIVE** one + curve↔preset — there can be several) · `.gitignore` with `*.mdat` (+ `.critic-env`).
- **The Critic channel's files — in `rew_analitic/` (where the channel reads them, project-local).** Create/place:
  - **`rew_analitic/autosound_context.md`** — this is the profile above (the channel reads `$PWD/rew_analitic/autosound_context.md`; keep it here, not only in the root).
  - **`rew_analitic/data-contract-template.md`** — copy the bundled template from the skill: `cp <skill>/assets/data-contract-template.md rew_analitic/`, then fill in the `<DSP>` placeholders. (Don't copy someone else's contract — its other car/DSP specifics would leak into the Critic.)
  - If the channel = `@google/gemini-cli` or the CWD ≠ the project root — add **`rew_analitic/.critic-env`** (`GEMINI_BIN=…`, and `PROJECT_MIRROR=…` if needed). Detail → `references/tooling/setup-critic-channel.md`.
- The first changelog entry: "project created; intake done; candidate target: X; preset targets: …".

Next → **Phase 0** (`process-phases.md`).
