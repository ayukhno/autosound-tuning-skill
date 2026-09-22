# Phase -1 — New Project & Setup Intake

This phase bootstraps a brand-new tuning project or a fresh system installation.

> 🗺️ **One way in.** The method builds a tune **from scratch** — −1 → 0 → desk → 3 → 4 — reading whatever the DSP currently holds into the ledger first. *Improving somebody else's existing tune is not a route laid out here* (user's ruling 2026-09-09): the tools serve it, the order of work is the tuner's own. Say so plainly rather than improvising a shortened phase order. The virtual-first happy path, the gear loss table, the degradation rule and the day-before preparation (−1.4) live in [`virtual-first.md`](references/phases/virtual-first.md) and [`capture-session-sheet.md`](references/phases/capture-session-sheet.md).

## 🎯 Goal-node

**Purpose:** bootstrap a brand-new project — workspace + language, equipment/goals interview, install verification, target-curve seed — so measurement can start safely on a known system.

**Questions this phase answers:** what's the car/drivers/DSP/mic rig? what are the goals (competition/enjoyment, reference seat, taste)? is the install safe and correct to measure?

**Required evidence:** the user interview (no guessing); driver `Fs` (datasheet/ask); routing · electrical polarity · gain · noise checks.

**✅ Quality gate → Phase 0:** language set; `autosound_context.md` (Engineering Profile) created — `preference-profile.md` may start as a stub, since taste is asked in Phase 0 after the baseline and applied in Phase 5; **the machine files exist and validate** — `project.json`, `dsp_profile.json`, the glossary, and a first ledger snapshot with every profile-declared tier populated (`python3 rew_tool/contract.py check <project> --gate` exits 0 — **`--gate`, not plain `check`**: plain `check` answers "is anything here wrong", which an EMPTY project satisfies, and this gate is asking whether everything it needs exists) — a prose-only intake is not a complete one, since a consumer front-end has nothing to render without them; install verified + protective HPFs set for fragile drivers. The target curve is **not** a Phase −1 item any more (2026-09-22, `docs/DESIGN-2026-09-22-intake-simplified.md`): nothing in the baseline capture reads it, it is chosen in Phase 0 with the baseline in hand (never defaulted), and `enter-phase 1` refuses without it.

**⚠️ Failure modes:** skipping install verification (costs a session) · filing reference seat / competition format as a "preference" (they're engineering) · enforcing a default curve.

**🧩 Patterns / refs:** the runbook is below; the doctrine it stands on → [`project-intake.md`](references/core/project-intake.md) (§0 the briefing and the reviewer, §3 install verification and its safety minima, §4 the DSP's capability level); curve→character → [`voicing-by-ear.md`](references/patterns/voicing-by-ear.md).

---

## Step-by-Step Runbook

The procedure of Phase −1, moved here from `core/project-intake.md` on 2026-09-16 (the user's decision: core
keeps doctrine, a phase file keeps its procedure). The section numbers are the ones it had there, so a
pointer that says §0.5, §1, §2 or §5 finds the same text; §0, §3 and §4 stay in `project-intake.md`.

**When you come here:** Resume finds no project files · a new car/system · a new or reworked install · the skill was handed to new hands · "tune from scratch". This is the **project's first session**: interview + verification first, only then the first measurement (Phase 0).

> **"The same car, but from scratch":** the profile (`autosound_context.md`) already exists — do NOT recreate it. Go through only §2 (goals/curve — they may have changed) + `project-intake.md` §3 (verification: the install may have drifted), archive the old history (changelog/dsp-state) with a marker, start a new one. Classifying the trigger "what raw data is still valid" → `naming-and-structure.md §2`.

### 0.5 — First-start guided flow (run IN ORDER; clear each gate before the next)

A new project's first contact has a fixed order, but the detail is spread across this runbook, `project-intake.md` and `process-phases.md` Phase 0 — and fresh sessions keep **skipping** a step (the glossary before measuring, the loopback, the reviewer). So run it as ONE sequence; the detail of each step is in the section noted — **this is the order + the gates:**

⛔ **Entry condition, before step 0 — open the phase.** `enter_phase("-1")` if the front-end offers the tool, otherwise `python3 rew_tool/state/process.py <project>/process enter-phase -1`. It is **not** a step in this list and **not** part of the write-up at §5: it happens BEFORE the first question. A model that asked its questions first dropped it without ever disobeying a sentence, and the phase went unrecorded for a whole session.

0. **Read the front-end** (`project-intake.md` §0) — `get_tcc_state` if a `tcc` server is connected. What it reports is settled; steps 1 and 2 are then a note, not a question.
1. **Language** (`project-intake.md` §0) — the REPLY language, and it is **read before it is asked**: the front-end's report wins (`get_tcc_state.language`), else `project.json`'s `language.reply` (`python3 rew_tool/project.py <project> language`), else ask EN/UK/DE/PL. The dialogue AND every project file follow it. **Write the answer** — `intake.save(<project>, "project.language", "<code>")` — so a session after a `/clear` reads it instead of coming back in English (S-045); the step is then **closed with `project.json` as its evidence**, an answered question left open being a question asked again next session. The INTERFACE language is the front-end's, and the language the person TYPES changes neither.
2. **Reviewer channel** (`project-intake.md` §0) — offer it and set it up NOW (the method's core, not an afterthought; `setup-critic-channel.md`). **If the front-end reports one, it is chosen** — record it and check `reviewer.reachable`; only an unreachable one is worth raising, and then as "this reviewer is clipboard-only", not as "which reviewer?".
3. **Interview — only what the first measurement needs** (`python3 rew_tool/intake.py fields --now`): the car (four parts + LHD/RHD), **the reference seat** (it decides where the mic stands), the DSP's vendor and model (the bundled profile answers its checklist on an exact match), whether each output can be soloed, the channel codes, the mic → write `autosound_context.md`. **The rest of §1–§2 is asked by the step that needs it**, not up front: drivers, amps and Fs at install verification (step 6); the source chain and inputs at Phase 0's pre-session checklist; purpose, genres and the curve seed in Phase 0 after the baseline; positions, enclosures, routing and constraints in Phase 1; stage priorities and test tracks in Phase 4; the taste axes in Phase 5. Each field names its step (`intake.WHEN`); ask it then, and do not re-ask what a tool or the bundled profile answers. A pre-selected default (LHD, 48 kHz, no loopback, a new tune) is confirmed, not asked; the seat has none, because it is written once.
4. **REW rig ready** — the mic + its cal files loaded; the sample rate = the DSP's native rate where possible; a **physical loopback** wired (without it, phase/timing reads are unreliable → lean on summation/ear); the right input/output devices selected; the measurement input **doesn't clip** (`project-intake.md` §3.8); the API answers at `localhost:4735`.
5. **Naming + glossary — AGREE BEFORE ANY MEASUREMENT.** ⛔ **Gate:** don't measure until the channel codes (`sw / w-L/R / m-L/R / tw-L/R / c / r`; two subwoofers → `sw-f` + `sw-r`, pair `SWs`, joint `SWs+Ws` — `naming-and-structure.md`) AND the title grammar are set with the user (`naming-and-structure.md §3`). The recurring slip is running off to measure with un-agreed names → an unusable history. **Write it, don't just agree it** — `glossary.json`/`project.json` (§5), the machine copy `naming.py` and a measurement checklist actually read.
6. **Install verification** (`project-intake.md` §3) — routing · electrical polarity · protective crossovers (fragile drivers only, above each Fs) · gain staging · noise · break-in of new drivers · a safe sweep level. ⛔ **Gate:** don't tune before this.
7. **Generate the project files** (§5).
8. **First baseline** (Phase 0) — **each driver solo**, the agreed names: `<ch>_1 (sw)` + `<ch>_1 (rta)` per driver, a RAW current-state capture on the clean `v0` (no TA/EQ) → this per-driver set feeds Phase 1 (which does not re-collect it).

> Steps 1–3 are the interview; 4–5 ready the rig and the language of the data; 6 protects the hardware; 7–8 produce the first real measurements. The two ⛔ gates — **measure only after naming, tune only after verification** — are where fresh sessions most often slip.

---

### 0.6 — A front-end MAY collect this intake up front. What it still owes the session

The questions below are a fixed set with fixed answers, and since SCR-059 they are also **data**:

```bash
python3 rew_tool/intake.py fields --json        # every field: id, group, the question, required, its enumeration, where it lands
python3 rew_tool/intake.py couplings            # the fields that are ONE question -- render each as one control
python3 rew_tool/intake.py gate <project>       # the files and keys the phase-0 gate decides on, before anything is opened
python3 rew_tool/intake.py missing <project>    # answered / missing / not machine-readable, right now
```

So a window may put §1–§2 on one form and hand the session the answers. **That is a supported way
in, not a shortcut around the phase order** — it was asked for after two intakes on the Arbiter's
own machine, where the car half was not asked by any window and arrived in free text only after the
Phase-0 gate refused, with the project already open.

**And the skill serves a form of its own** (`intake_form.py`, S-033), so "a window" is not only
TCC's: `python3 rew_tool/intake_form.py serve <project>` puts on one local page only what starting
to measure needs — about twenty answers, most of them a choice with the usual answer pre-selected —
and folds the rest under a line naming the step that asks it ("asked later — Phase 1 …"), so
nothing is hidden and nothing is in the way. Each couple is ONE control, the channel and amplifier
halves are tables, and every field is coloured by what is owed (red: needed now and missing; yellow:
optional, defaulted, or later; green: answered; grey: lands in prose). A terminal session hands a
person that URL instead of asking the questions in chat; a front-end opens the same page rather
than writing the questions a second time.
The page decides nothing — it writes through the same writers below and prints the gate's own
verdict. Labels are data (`intake_i18n/<lang>.json`); Ukrainian is the one that exists today.

**What a front-end may do:** ask the fields, in its own words and its own language (the tables carry
KEYS; the labels are the consumer's), and write what the person CONFIRMED —
`intake.py set-car | set-channel | set-amp | set <field> <value>` for the car, the channel map, the
measurement chain and the rig; `dsp_profile.py set-field` for the processor's half.

**What it still owes, unchanged:**

* **The phase is opened first** — `enter_phase("-1")` is the entry condition above, not a step, and
  collecting answers earlier does not move it.
* **Every ruling is still RECORDED** (`process.py <project>/process decision …`), and an answer that
  arrived on a form is an answered step — closed with what it said, never re-asked in conversation.
* **The gates do not move:** names agreed and written before any measurement (step 5), install
  verified before any tuning (step 6), the curve **seeded with the person** and never defaulted (§2.6).
* **The prose is still written** (§5): `autosound_context.md` and `preference-profile.md` are what
  the human and the Critic read, and a form's answers do not replace them.
* **What the form could not ask stays a question**, not a blank: `intake.py missing` says which
  required fields are still open, and the goals, taste and curve seed come back as *not
  machine-readable* — they live in prose and in recorded decisions, so a session asks them.

---

### 1. Interview: equipment and system → the project profile

Ask in blocks, record the answers right away in `autosound_context.md` (structure — §5 below). **Before the first measurement ask only what `intake.py fields --now` lists** (the car, the DSP identity, the channel codes, the mic); the other items below are asked by the step that first needs them (§0.5 step 3). Don't assume — ask; "I don't know" is also an answer (then we measure / look in the DSP software).

> ⚠️ **Take install/gear specifics ONLY from here (from the user) or from measurement — NOT from a `knowledge/cars`|`dsp` profile.** Driver placement/orientation/coplanarity, the gain-staging level (e.g. Output −6 dB), crossover numbers, anomaly frequencies — all of these depend on the SPECIFIC install/amps and **vary even on the same body/DSP**. A profile = a checklist to "verify", not facts to cite. Never "your X = Y" without the user's words or a measurement.

1. **Car:** make / model / **generation** / **body** — four parts, and all four get RECORDED in `project.json.car` (`project-schema.md` SCR-043). `Passat` is the model, `B8` the generation, `sedan` the body. The generation **is** the band of years over which the acoustics count as the same, so the **year classifies nothing** — record it as a detail of this car, never ask it to decide whether two cabins match. Body matters more than any of it (sedan vs hatch/wagon → room gain and low-frequency behavior), and a body left unrecorded means a later session cannot tell this cabin from a wagon's. Plus LHD/RHD (the listener's side → the direction of the L/R asymmetry).
2. **Sound source(s):** HU/streamer/phone; **how the signal enters the DSP** (optical/coax/RCA/BT/USB); **which input is for listening, and which is for the measurement signal** (this goes into the Pre-session checklist #4).
3. **DSP:** model → the full capability checklist in **`project-intake.md` §4** (it determines which of the skill's tools are available). *(Just a small fine-tune of an already-working system? You can enter **light-touch = Level 0** — `project-intake.md` §4 — and skip the full DSP dump, working from the measurement + target.)*
4. **Amplifiers:** model/channels/input sensitivity (for gain staging), what's on which channel.
5. **Drivers:** model, size, **the position and orientation of EACH** (door / A-pillar / kick / dash / deck; where it points), enclosure (pod/sealed/free-air volume), mass/character (a heavy midbass → align to the IR peak, `car-eq-patterns.md`), **new or broken-in** (new → break-in, `project-intake.md` §3.6). Record make/model/`Fs` **per channel** into `project.json` as you go (§5) — not only into this file's prose — so a consumer UI's per-channel tooltip has something to read; datasheet `Fs` is fine, mark it `source: datasheet` (a later impedance measurement can upgrade it to `measured`).
6. **Sub:** enclosure (sealed/ported), volume, location, how it's driven.
7. **Center / rear:** present or not, how they're driven (an FX algorithm / manual L+R / separate channels) — this determines the Phase-4 method.
8. **Mic rig:** mic + cal files (0°/90°), interface, **whether a physical loopback is possible** (without it, phase-critical measurements are unreliable → more weight to summation/the ear), sample rate (where possible = the DSP's native rate).
9. **Project paths:** where the context/audit/measurements will live (local project parameters, NOT skill constants; typically — the project's git repo, structure in §5).

### 2. Interview: goals and taste → the curve seed and Phase 5

Ask it the way the user thinks of it — a few **branching** questions, in this order. **Only #2 (the
reference seat) is asked before the first measurement**; the rest is asked in Phase 0 after the
baseline (purpose, music, the curve) and later (stage priorities and test tracks in Phase 4, taste
in Phase 5) — each field's `when` in `intake.py` names the step:

> 📂 **Route each answer into the right layer** (see [`preference-profile.md`](references/core/preference-profile.md)): answers that **shape the engineering** → **Engineering Profile** (`autosound_context.md`): purpose/competition format (#1), reference seat (#2), stage priorities & physical ceilings (#4), hard constraints (#7). **Pure taste** → **Preference Profile** (`preference-profile.md`), applied only in Phase 5: music & loudness (#3), taste axes (#5), curve character (#6).

1. **Purpose (the first fork):**
   - **Competition** → which format(s): **EMMA / AYA / CARMusic — one, several, or all.** ⚠️ Formats judge differently and some techniques are **mutually exclusive** (e.g. crossfeed stabilises an EMMA stage but is never used for AYA) → "several/all" = **separate presets**, not one tune (`competition.md`, `preset-strategy.md`). A format names a **GOAL**, not a slope recipe (`knowledge/approaches.md`).
   - **For yourself (daily enjoyment)** → fan out into #3 (music · loudness · taste).
   - **Both** → competition preset(s) + an enjoyment preset; base+voicing makes the second cheap.
2. **Who is the tune FOR — and this is WHAT THE PROJECT IS, not a setting inside it** (ask explicitly, and write it: `project.py <dir> project-type <type>`, or `intake.save(<dir>, "goal.reference_seat", "<type>")`). One of six: **`driver`** · **`passenger`** · **`both`** · **`all`** · **`rear_left`** · **`rear_right`**. ⛔ **Written once.** Tuning the stage for another seat means taking every raw curve again and walking the whole process, so the other seat is ANOTHER project — started from this one's description and none of its measurements (the Arbiter's ruling 2026-09-20, S-032). Not the presets: SQ and FULL live in one project on one measurement base, and FULL is the rears and surround, not a seat. (The car's **LHD/RHD** from §1 sets the *direction* of the L/R asymmetry.) ⚠️ This decides what the tune **optimises**: a **single seat** can be fully centred and imaged — one listening point is THE reference; **all seats** is a deliberate **compromise** — no perfect phantom centre for anyone, you trade per-seat perfection for an even spread. Settle it up front — it changes the centering/TA strategy (`diagnostic-techniques.md §16`), not just a level.
3. **Music & how you listen (the "for-yourself" branch):** genres + **what you love most** (bass · vocals · winds & strings · acoustic · electronica) → seeds the curve character; 3–5 favourite reference tracks; **how loud** (loud vs moderate → equal-loudness, `staging-depth.md §3`); long/short trips; **which test-track library** you have (a loaded compilation — CarMus / Chesky / EMMA-AYA disc — or a streaming service) → Phase 4 proposes only from what you can play (`test-tracks.md`).
4. **What stage we're building** (priorities — you can't maximize everything at once): width / depth-layering / height / a tight center focus; rear envelopment or front-only. State the physical ceilings honestly: depth is limited by the mid's geometry (`staging-depth.md §4`), envelopment needs a rear.
5. **Taste axes:** warm↔bright · bass-heavy↔neutral · forward↔laid-back · accuracy↔fun.
6. **Choosing the target curve — TOGETHER with the user, there is NO default.** Walk through the **curve→character** table (`voicing-by-ear.md`), narrow it by genres/taste to 2–3 candidates, finalize via the curve-audition method (same place) or take a candidate as the session's start and validate by ear in Phase 4/5. **A curve = a start and a shape, not a finish and not a level** (`naming-and-structure.md §6`). ⚠️ The curve is only **SEEDED** here — it's finalised AFTER the raw baseline (Phase 0), with the measured reality in hand. In a report that is «криву обираємо попередньо, остаточно — після замірів Фази 0»: the same rule as the ledger snapshot above, a metaphor the reader does not share is not a word to hand him (`naming-and-structure.md` §1a).
7. **Anything else you want from this system?** ⚠️ **The branches above are the COMMON ones, not a closed list — always leave room for the user's OWN wishes.** Capture any wish **in the user's own words**, then **map it to where it lands in the tune** rather than forcing it into a predefined box: the curve character · a Phase-6 voicing move (`voicing-by-ear.md`) · a separate preset (`preset-strategy.md`) · a hard constraint or an honest ceiling (state it) · an install/gear note. If a wish doesn't fit any box, **record it as an explicit project goal** and address it on its own terms. Examples a user might raise: "match how this one track sounds", "no harsh top when it's loud", "keep the nav prompts clear over music", "I don't want to cut into the doors", "make it sound like the demo car I heard". A free-form wish is always welcome — it's what makes the tune fit THIS person, not a generic target.

> **The order the user pictures (and the skill follows):** goals (this §2) → **equipment analysis** (§1 + the DSP capability `project-intake.md` §4) → **raw baseline measurement** (Phase 0) → **finalise the target curve** → tuning. The curve is chosen *with* the measurement, not before it.

### 3. Install verification — BEFORE the first measurement

The checklist and its safety minima — the protective high-pass at ≥ 1.1 × Fs and ≥ 24 dB/oct, and what
a protective filter does to the recording — are doctrine every later phase cites, so they stay in
[`project-intake.md` §3](references/core/project-intake.md). ⛔ Don't tune before it is cleared.

### 4. DSP capability checklist → which toolset is available

The capability levels (0–3), the checklist and the profile lookup: [`project-intake.md` §4](references/core/project-intake.md).

### 5. Generate the project files

In the new project's root (a git repo; layout and the "what's in git, what isn't" rule → `naming-and-structure.md §4a`). **Two families, not one** — prose for the human/Critic, and the MACHINE files a consumer front-end (or your own resume) reads. Both are this phase's deliverable; neither substitutes for the other.

**Machine files (write these — a front-end has nothing to render without them):**
- **`project.json`** — car/source/DSP/amps/mic/paths/presets, per-channel driver facts (make/model/`fs_hz`), the naming glossary, DSP-hardware controls (RearRC/SubRC/RealCenter-type knobs — constant across presets, so recorded ONCE here, never per-preset). Build it as you go through §1–§2, don't defer it to a write-up pass at the end: `python3 rew_tool/project.py <project> set-channel <code> slot=C fs_hz=62` for flat fields via the CLI, `Project(project_dir).set_channel(code, driver={"make": …, "model": …}, fs_hz=project.fact(62, source="datasheet"))` for the nested `driver`/provenance-wrapped facts. Unconfirmed facts stay `null`, surfaced by `open-questions`, never guessed. Full shape → `rew_tool/project-schema.md`.
  - **Give every channel a `tier`, and write a row for the EMPTY slots too (SCR-042).** `tier` is the ledger key — `channels` for a physical output, `virtual_channels`/`inputs`/… for the rest — **not** the profile's group id (`physical_outputs` is refused; `dsp_profile.ledger_tier()` converts). A slot with nothing wired to it never gets a ledger row, so this entry is the only record that it exists: `set-channel off-out-L slot=L hidden=true role=unused tier=channels`. And it must be told, not inferred — **slot letters repeat across tiers** (a Helix's virtual tier is A–H, its outputs B–K), so `slot: "F"` is a legal address in both and a guess puts a spare output among the virtual channels.
- **`dsp_profile.json`** — the DSP capability profile from `project-intake.md` §4's checklist (groups/tiers, per-group fields, EQ band types/count). Use the bundled reference under `data/dsp_profiles/` on an exact vendor+model match (`dsp_profile.py find-bundled`); otherwise build it from the answers here. Fill **`max_count` per group** — how many slots that tier *physically* has, counted from the processor's spec, not from what this car wired up. Left null, a 12-output Helix with ten in use reads `10/10` instead of `10/12` and its two spare slots are invisible.
- **The naming glossary agreed in §0.5 step 5** — write it, don't just agree it in conversation: `glossary.json` (or `project.json`'s `glossary` key) with `channels`/`pairs`/`combos`/`joints`/`sides`. `python3 rew_tool/naming.py <project> codes` reads it back; this is what lets the measurement checklist be derived instead of hard-coded (`naming-and-structure.md §3`).
- **The first ledger snapshot** (`rew_tool/state/`) — **in a report: «записую перший знімок реєстру (`v_001`)», never «сію»** (`naming-and-structure.md` §1a: the method's English is not the reader's, and this word cost a stop mid-wave) — seed it with **every tier the DSP profile declares populated**, not just physical outputs: a Helix project's first `v_001` needs both `channels` AND `virtual_channels` rows from the start (empty/placeholder is fine for a slot with no driver yet — mark it `"hidden": true`, SCR-003 — but the tier key itself must exist, since `apply.propose` can only address a tier that's already there). **A project COPIED from another car has none** — TCC's Copy car carries `project.json` and the DSP profile and deliberately not `state/` — and until the first snapshot is banked, `apply.propose` cannot produce a settings sheet and a `v_NNN` capture round is refused (TCC-022). Measuring is still open: a Phase-0 baseline opens at its series number (`capture-start 1 …`) and needs no ledger. **Multiple presets in physical DSP slots** → also set the live one (`state.py --root <project>/state registry set-active <preset>`); `state.py --root <project>/state registry render` generates the multi-slot `dsp-state-current` (active-slot banner + isolated per-slot rows) so the model can't anchor on the wrong slot (issue #5).
- **`process/`** — the phase itself was opened at the **entry condition of §0.5**, before the first question; if you reached here without it, that is the slip, not a step you owe now. Then `add-step`/`done` for its own checklist items as you clear them (§0.5's gates are natural step boundaries). This is what makes THIS phase itself resumable, not only the ones after it.
- **Verify the whole set before moving on:** `python3 rew_tool/contract.py check <project>` — should report every machine file present and valid before the Phase-0 gate clears. **To the user that verification is one word** — *checks: done* — and only a file it REFUSES is spoken in sentences, with what to do about it (SKILL.md `✍️ Output Style`).

**Prose (still needed — for the human and the Critic):**
- **`curves.html`** — a symlink to the skill's target-curve visualizer, right at the project root, so the tool is one click away instead of buried in the skill's folders: `ln -s <skill-dir>/curves.html curves.html`. **`.gitignore` it** — an absolute-path symlink is machine-specific (same pattern as `.agents/skills/`); re-link it with the command above on a new machine.
- **`autosound_context.md`** — the profile: §1 equipment · §2 channels/routing · §3 measurement rig · §4 targets/curve/crossovers (the active curve → `rew_analitic/target-curves/<name>/`) · §5 **channel glossary** narrative (the machine copy is `glossary.json`/`project.json` above — keep this section as the readable explanation, not a second disagreeing source) · §6 the experience/anomaly log (empty — the sessions will fill it). Template — the Passat B8 profile.
- **`preference-profile.md`** — the **Preference Profile** (layer 4): pure voicing preferences (taste axes, loudness habit, favourite tracks, curve character), kept separate from the Engineering Profile above and applied only in Phase 5. See `references/core/preference-profile.md`.
- **`tuning-changelog`** (with a ▶️ CONTINUE block at the top) — human-readable narrative alongside `process/process-state.json`, not instead of it; if the two ever disagree, the machine file is what resume trusts.
- **`audit-trail.md`** (the decision log a human reads — the machine record of how we got here is `process/journal.jsonl`, and where the two disagree the journal wins) + **`skill-inbox.md`** (empty, with a rules header).
- **`rew_analitic/`**: `dsp-config/` + a `README.md` map · `exports/` · **`target-curves/`** (house/target curves; **a subfolder per curve** = the full curve + per-band components with crossovers in the names; a `README.md` map: which is the **ACTIVE** one + curve↔preset — there can be several) · `.gitignore` with `*.mdat` (+ `.critic-env`) — **written by `project_seed.py` at creation**, so this is a check, not a chore; add `*.mdat` to it if the seed predates that rule.
- **The Critic channel's files — in `rew_analitic/` (where the channel reads them, project-local).** Create/place:
  - **`rew_analitic/autosound_context.md`** — this is the profile above (the channel reads `$PWD/rew_analitic/autosound_context.md`; keep it here, not only in the root).
  - **`rew_analitic/data-contract-template.md`** — copy the bundled template from the skill: `cp <skill>/assets/data-contract-template.md rew_analitic/`, then fill in the `<DSP>` placeholders. (Don't copy someone else's contract — its other car/DSP specifics would leak into the Critic.)
  - **What sits OUTSIDE the DSP is an input, not an assumption.** A remote knob (Helix `SubRC`/`RearRC`,
    a bass control, a fader), a switch, an amplifier's own gain: nothing in a measurement records them,
    the ledger is per-preset and cannot, and `project.json.hardware.controls` holds where they stand
    today — not where they stood for a given capture. So they are recorded **on the capture round**
    (`process.py <project>/process capture-knobs SubRC=4/4`, once Phase 0 has opened the round with `capture-start <N>` — it refuses with no round open) and what a step of one is WORTH is a
    separate fact with its own provenance (`project.py <dir> set-control-mapping SubRC 2 sw --source
    user`) — the vendor's claim or the tuner's word until somebody measures it. Two facts, because
    the position is read off the device and the mapping is somebody's opinion, and a report that
    mixes them cannot be argued with. Without the mapping, a comparison across positions is REFUSED
    rather than folded into a calibration offset (hub `RES-007`).
  - **The DSP's routing matrix is a fact of the project, recorded once** (`project.py <dir> set-route
    VFL w-L,m-L,tw-L`): which physical outputs each virtual channel feeds. A fact that has to be
    retyped on every run is one session away from being wrong, and it is never inferable from names —
    `VFL` looking like "virtual front left" is a convention, not a wiring diagram.
  - If the channel = `@google/gemini-cli` (closed since 2026-09-08 — a key did not reopen it, `setup-critic-channel.md` §2; use `agy`) or the CWD ≠ the project root — add **`rew_analitic/.critic-env`** (`GEMINI_BIN=…`, and `PROJECT_MIRROR=…` if needed). Detail → `references/tooling/setup-critic-channel.md`.
- The first changelog entry: "project created; intake done; candidate target: X; preset targets: …".

Next → **Phase 0** (`process-phases.md`).
