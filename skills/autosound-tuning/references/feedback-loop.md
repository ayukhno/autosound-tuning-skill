# Feedback loop — distributing the skill and collecting experience (Phase 7)

Goal: the skill learns from **every** project, not just the author's — it accumulates successful decisions, know-how, experience with cars and gear (DSP, amps, drivers). Principles: **simple** (markdown, no infrastructure) · **convenient** (the skill builds the package) · **transparent** (the user sees everything they send) · **safe** (zero personal data, explicit consent).

## The session's closing ritual — FOUR distinct streams (don't mix them)

> ⚠️ **Phase 7 is NOT terminal — it's a REPEATABLE checkpoint that fires at every SATISFACTION milestone.** The richest feedback is captured the first time the tune is "**mostly there / sounds great**", not only at the very end of a project (a real package was built exactly at that first-satisfaction point and carried the freshest lessons). So **propose the closing ritual whenever the user signals satisfaction** — after a milestone, before a break, at a preset's completion — and **run it again** at later milestones; each pass accumulates more into the skill. Don't gate it behind "the project is finished".

When the tune is ready at this stage (after the listening work — Phase 5/6, or at any earlier satisfaction milestone), Claude runs short **interactive** steps. All optional, nothing blocks. The key: these are **different things for different recipients** — first the result (A), feedback on the skill (B), consent to contribute (C) → **submit**; and **only AFTER submit** — thanks and (on a positive) a quiet donation link (D). ⚠️ **The donation is never among questions A–C and isn't mentioned in any word before submit** — so that a request for money doesn't pressure the feedback.

> **INTERACTIVELY, not a wall of text.** Ask **closed questions with ready options** (choice buttons in Claude Code/claude.ai). **The ability to write freely is ALWAYS present as an OPTION** (in AskUserQuestion that's the "Other" field) — because free feedback is the basis of openness, and the author **reads it**. But **never mandatory**: open questions are treacherous (they force phrasing, deter people, give vague answers) → offer the channel, don't oblige filling it. At most 3–4 questions per stream; **for A+B combined — ~5–6 "taps", no more** (fatigue kills answer quality — better fewer but on point).

**A. Feedback on the PROJECT (for the installer/client).** Whether the tune's goal was met + the car's backlog:
- **Did the preset meet the goal?** → `Yes, fully` / `Mostly` / `Partly` / `Not yet`
- **Overall impression?** → `🙂 great` / `😐 ok` / `🙁 not there yet`
- **What to fine-tune first?** *(several)* → center/depth · rear · bass/sub · tone · stage-imaging
→ into the session log + the project backlog. ⚠️ This is about the CAR — "fine-tuning" goes here, **don't confuse it with the skill (B)**.

**B. Feedback on the SKILL (for the skill's author).** What in the skill **worked**, what **wasn't great** — from THIS project's practice:
- ⚠️ **Ask ONLY about what was actually used.** Check against the changelog/context which phases/techniques/references were engaged (intake? nono targets? joint phase? imaging? depth? competition? presets?) — and ask only about those. Asking about the unused = irritating with the irrelevant.
- e.g.: "What in the skill helped most?" *(a choice from what was used)* · "What was inconvenient / threw you off / was missing?" *(a choice + an optional comment)*.
→ material to improve the skill.

**C. Consent to share the work with the COMMUNITY — a separate, motivating step.**
Claude **collects the SPECIFIC work from this project**, **grouped by 3 experience categories** (they fold into DIFFERENT places, so group them up front):
- **① Method-skill** — techniques / phases / diagnostics, universal → SKILL.md + references;
- **② Car** — anomalies and solutions of a specific body/cabin → `knowledge/cars/<body>.md`;
- **③ Equipment** — quirks and capabilities of the DSP / amps / drivers → `knowledge/dsp/<dsp>.md`. ⚠️ Hardware experience can **OPEN new capabilities/presets** (e.g. a Goldhorn with a surround DSP → a surround preset — `preset-strategy.md`).

Presents it as **a list where EACH item is already PRE-SELECTED (☑)**. The user **unchecks** what they don't want to share (**opt-out, not opt-in** — less friction, more contribution), and presses **"I agree to send it for the community's benefit!"**.
- **Give a sense of value:** real experience from a specific car/DSP is rare and makes the skill smarter **for all tuners** — it's a contribution, not a chore. Emphasize the importance of the user's experience.
- **Implementing opt-out in Claude Code** (AskUserQuestion has no pre-checked boxes → emulate it): show a numbered list of the work in the text (all = "will be included"), then one question: `☑ Yes, all — I agree to send it for the community's benefit!` / `I'll pick what to exclude` / `Not now`. If "exclude" → a second multiSelect question: what to REMOVE; the rest goes into the package.
- **Safety is unchanged:** only the method + equipment classes, no personal data/full measurements (§"Collecting experience"). Consent to collect ≠ auto-send — **a human still confirms the publication** (themselves or, on request, via `gh` showing the final text).

**D. Thanks — and only AFTER submit a quiet donation link (NOT a form item).** The donation is **never among questions/lists A–C**, and **not a word about it before submit** (while the user is answering and confirming the contribution). Only **after completion** (the survey + consent C are sent): a short thanks, and **only if A showed a positive** — one link for a quick donation.
> "Thanks for the feedback 🙏 Glad it worked out. If the skill was useful — here's a quick tip jar to support the author: [jar link]. No pressure 🤝"
- **Never** on dissatisfaction (then — just thanks, no donation); **once**, don't repeat; **don't lock anything** behind a donation (CC BY-SA, works without payment); the tone — gratitude, not a request.
- **The link = the Monobank jar** — `https://send.monobank.ua/jar/8wThVcodjm` (also the repo's Sponsor button, set as `custom` in `.github/FUNDING.yml`): a voluntary tip jar, one tap, no account, foreign cards OK via the web page. ⚠️ **Post the LINK only — never the card number.** (GitHub Sponsors can be added later as an extra FUNDING line; if ever NO channel is active, **skip** the step silently — no dead link.)

> ⏳ The A–D stream structure is **settled**; **the exact wording/scales** of A–B are polished from REAL runs (they give better questions than armchair editing). Keep them closed + optionally-open, within a ~5–6 tap budget. A has two axes (goal met vs subjective impression) — don't confuse them, don't merge them.

---

## Distributing the skill

- **The canon = the skill's git repository** (autosound-tuning + the sibling `review-loop` together — they're a pair), **without project data**: the method is separated from the car (the `autosound_context.md` profile, measurements, dsp-state — live locally in the user's project and never enter the skill).
- **Versions:** git tags `vN` + `CHANGELOG.md` (a line per refactor; the source — the "Last refactor" entries from the author's skill-inbox).
- **Installing for new hands:** clone → a copy/symlink into the tuner's project `.claude/skills/` → the first session starts from `project-intake.md`. Updates = `git pull` (the user's own files — the profile, the inbox — live in their project, so a pull doesn't touch them).
- Optionally: `package_skill.py` (skill-creator) → a `.skill` file for installing into claude.ai.

## Collecting experience — the feedback package

**Trigger (proactive):** at **any satisfaction milestone** (the tune is "mostly there / sounds great"), the end of a project, or a significant session — and **repeatably** at later milestones — Claude **proposes itself** "build a feedback package for the skill's author?" — without waiting to be asked (it also fires on "build feedback"). The proactivity is only on the *proposing and preparing* side; **a human always does the sending** (see step 2 — the safety principle). **The mechanics — two separate stages:**

1. **Building and recording (locally).** The skill collects data from `skill-inbox.md` + the changelog (`Lesson:` lines) + the profile and writes **`feedback-YYYY-MM-DD.md`** in the project per the template. The user reads it, edits, says "OK" → the file is **recorded in the project**. At this stage **nothing has been sent anywhere** — but there's value already: the recorded packages sit nearby and can be handed over together/later.
2. **Delivery to the author (optional, a separate explicit decision).** The user sends the file themselves via one of the channels below — or asks Claude to do it for them (e.g. `gh issue create`, if the GitHub CLI is set up), and then Claude **shows the final text and waits for explicit confirmation** before sending. The "OK" from stage 1 ≠ consent to send.

### The package template

```markdown
# Feedback: <car/body> · <DSP> · <date> · skill <version>
## Setup (equipment classes, no personal data)
car/body · DSP · amps · drivers + positions · sub/enclosure · mic rig
## What worked
crossover sets · techniques · successful symptom→fix · track markers
## What did NOT work / where the skill erred or was silent
## New techniques / know-how (skill-inbox format: 📚 one line + why/evidence)
## DSP/hardware quirks (→ knowledge/dsp/)
## This body's cabin anomalies (→ knowledge/cars/)
```

### Sending channels (by increasing formality)

1. **A GitHub Issue** in the skill's repo per the issue template — the default: transparent, threaded, the history visible to all.
2. **A PR**: the package in `community-inbox/<body>-<date>.md`.
3. Without git: the file to the author by messenger/email.

### Package safety rules

- **Only the method + equipment classes.** WITHOUT: names, locations, plate/VIN numbers, photos, full measurements (`.mdat` are large and identify the system) — numbers only decimated, as for the critic (`analysis-playbook.md`).
- The package — plain markdown, read by the user BEFORE sending. A doubtful line → drop it.

## The author's side — how experience flows into the skill

- `community-inbox/` is processed by **the same maintenance loop** (harvest → correlate → fold, SKILL.md): each item is checked against the skill; the origin tag `[source: <body>/<author>]` is kept.
- **Contradicts our conclusions → a VARIANT, not a deletion** (maintenance loop rule §2: a different geometry/cabin can make the tip right).
- **Hardware experience accumulates into the skill's profile library** (each new entry = **copy the blank `_TEMPLATE.md` and fill it**, so the structure/discipline is consistent):
  - `knowledge/cars/<body>.md` — the cabin map: PART A body-physics / PART B verify-only anomalies, winning crossover sets, quirks (template `knowledge/cars/_TEMPLATE.md`; worked example — the Passat B8, de-identified);
  - `knowledge/dsp/<dsp>.md` — the capability profile (layers, EQ-exchange format, presets, quirks) (template `knowledge/dsp/_TEMPLATE.md`; worked example — `helix-dsp-ultra-s.md`).
  - `knowledge/approaches.md` — the **classifier of whole-system schemes** (crossover/slope approaches as variants tagged by setup context + success story + confidence + any competition result). Each finished tune **appends** the scheme it used; this is the seed of a public, community-rated classifier. ⚠️ A scheme is bound to ITS setup — never a format→slope recipe.
  At a new car's intake the skill **checks first** whether a profile of this body/DSP already exists (`project-intake.md §4`), and `knowledge/approaches.md` for schemes that worked on a similar setup (a shortlist of hypotheses, not facts).
- Thanks: a contributor line in the CHANGELOG.
