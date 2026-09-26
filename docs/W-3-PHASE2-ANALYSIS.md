# Phase 2's plan, as the Passat ran it: where it can be shorter without being worse

Skill #73, the Arbiter's ask (2026-09-24): «глянь на план — якийсь він завеликий заскладний … де коли ми щось
міряємо, щось рахуємо, скіл щось пише, але ми не йдемо вперед». This is the analysis he asked for first; nothing
in the method changes on it until he says which cuts to take. Written 2026-09-26 on `wave-2026-09-23`.

## What the plan was

Ten steps on the screen, in order (the issue's list, as the Generator wrote them):

| # | step, as planned | what it does | what he enters |
|---|---|---|---|
| 1 | read the current filters and the deviation matrix | analysis (`analyze-batch`) | — |
| 2 | packages through `eq_propose` | computation | — |
| 3 | the summed response of each package | computation | — |
| 4 | one review · the Arbiter's choice · `apply.propose` · the Helix export · ONE control series | review, decision, version, export, **a trip to the car** | **yes** |
| 5 | re-check the junctions where 2a's EQ reached | computation | — (a delay, if it moved) |
| 6 | group sums and L vs R | **measurement** (MMM in the car) | — |
| 7 | two scene presets by ear with the centre off | listening, in the car | a preset switch |
| 8 | final EQ to target on the virtual layer | computation → version | **yes** |
| 9 | a review of the full package | review | — |
| 10 | the centre's delay | computation → version | **yes** |

Three of ten put something in front of him to enter. The rest measure, compute, review or write. That is the shape
he called «товчемося на місці», and it is true: seven steps produce records, three produce a change.

## Where the steps come from, and which are the method's

The method describes Phase 2 twice, and the plan took from both:

- **`phase_2_eq.md`** is the iterative path: 2a (pairs and what the coarse pass left) → 2b (joint phase) → 2c
  (summed groups, with the scene presets between the two halves) → 2d (final EQ, centre, rear). It asks for **one**
  review on the round's full package (2d) and a second only when 2b's joints were reworked. Its 2a box says
  "batch the whole round … then take ONE comprehensive re-measurement pass" — that is where step 4's control series
  comes from.
- **`virtual-first.md`** is the desk path, which this project chose: 2.1 (the second part of EQ, as packages, in the
  order above, every package one version), 2.2 (predict again, `verify_prediction`), 2.3 (the sheet to disk), and
  **the car once, in Phase 3**. On this path Phase 2 has no measurement at all: 2c's group sums are `predict`'s
  sums, and the scene presets are the one thing that needs an ear — but they are listened to in the car, in
  Phase 3, on the preset switch, not in Phase 2.

So the plan mixed the two paths: it kept the desk's packages (steps 2, 3, 5, 8, 10) **and** the iterative path's
trips (step 4's control series, step 6's MMM group sums) **and** put the listening (step 7) in the desk phase. That
is the "measure, compute, write, no progress": the desk path's whole point is that Phase 2 ends with a sheet, and the
plan sent him to the car twice before the sheet existed.

## Step by step: keep, merge, or cut — with the reason from the sources

| # | verdict | why (source) |
|---|---|---|
| 1 | **merge into 2** | `eq_propose --part 2` reads the solos and the deviation itself; `analyze-batch` is the same read printed for a person. One tool, one step: "the packages, with the matrix they came from". (`phase_2_eq.md` 2a ⚡ box; `eq_propose` docstring) |
| 2 | **keep** — the step of Phase 2 | the packages are the decision unit (`phase_2_eq.md` 2a "as PACKAGES"; `virtual-first.md` 2.1) |
| 3 | **cut** | `eq_propose` already scores each package's summed curve per channel ("Score the package's SUMMED curve", 2a; `_score` in the tool). A separate step repeats the tool. |
| 4 | **split, and the trip goes** | the review, his choice and `apply.propose` are the end of step 2 (a package is accepted or refused whole, banked as one version — 2a). The Helix export is 2.3's sheet. The **control series is the iterative path's** (2a ⚡ "one re-measurement pass"); on the desk path the check is 2.2 (`verify_prediction`), at the desk, and the car comes once in Phase 3. |
| 5 | **keep, as part of 2** | the rule stands: a package that reached a junction's band re-checks that junction's delay (`virtual-first.md` 2.1: "a package says which junctions it reaches (`recheck_junctions`) before it is banked"). It is a line in the package, not a step. |
| 6 | **cut from Phase 2; it is Phase 3's** | on the desk path the group sums are predicted (2.2); the MMM sums are taken in the car in Phase 3 (`virtual-first.md` 3.x, `phase_2_eq.md` 2c "Verification Steps" belong to the iterative path). |
| 7 | **move to Phase 3** | the presets are built at the desk (`scene_presets.py`, a delta per rung — `virtual-first.md` 2.1) and listened to in the car; the listening needs the preset switch and the seat. Building them is a line in step 2; hearing them is a Phase-3 step. |
| 8 | **keep** — the last package of 2.1 | "everything together, the tone per pair toward the target" is the final EQ (`virtual-first.md` 2.1; `phase_2_eq.md` 2d). It is the last package, not a separate phase of work. |
| 9 | **keep, once** | "one critic checkpoint on the round's full package" is the gate (`phase_2_eq.md` quality gate). Step 4's review folds into it when the packages are reviewed together; two reviews only when 2b's joints were reworked. |
| 10 | **keep, as a package** | the centre under everything is the next-to-last package of 2.1 (`virtual-first.md` 2.1; `phase_2_eq.md` 2d "then the centre"). |

## What Phase 2 looks like after the cuts (the desk path)

Four steps, each ending in something he sees:

1. **2.1 the packages** — `eq_propose --part 2` with the ellipsoid; each package says what it reaches
   (`recheck_junctions`) and comes with its score; the scene presets' deltas built beside them. **Ends in:** the
   packages on the screen, each accepted or refused, each accepted one a yellow version (`apply.propose`).
2. **2.2 the check at the desk** — `verify_prediction` on the accepted set: joints and L/R through the same windows.
   **Ends in:** a verdict; a junction that moved sends its package back to 1.
3. **2.3 the review** — one critic round on the full package. **Ends in:** the review file; a refusal sends a package
   back to 1.
4. **2.4 the sheet** — `docs/sheets/<v_NNN>-<slot>.md` (skill #61) and the EQ file to import. **Ends in:** what he
   enters, in one place. Then Phase 3: the car, once — enter, control, MMM sums, the presets by ear, lock.

Ten steps become four; the two car trips inside Phase 2 become none; three steps that only restated a tool's rule
(Q ceiling, tolerance, cuts only) are gone because the tool holds the rule. Nothing measured is lost: the group
sums and the listening are still taken, in Phase 3, where the desk path always put them.

## What would change in the method, if he takes this

- `virtual-first.md` 2.1–2.3: no change of substance; the four steps above are its 2.1–2.3 with the review named as
  its own step (it is in `phase_2_eq.md`'s gate, and the plan lost it between the packages).
- `phase_2_eq.md`: the 2a ⚡ box "then take ONE comprehensive re-measurement pass" and 2c's "Verification Steps" get
  one line each: **iterative path only; on the desk path this is Phase 3**. Today a session reads both files and
  plans both trips.
- **How a session writes plan steps** (the rule that makes this stick): a Phase-2 step is named for what it ENDS IN
  — a version, a verdict, a review file, a sheet — never for a rule it follows. A step that ends in nothing he can
  see is not a step; it is a line inside one. This goes into `SKILL.md`'s process bullet, beside #72's "a step goes
  by its id".
- The plan template a session starts Phase 2 from: the four steps above, as `add-step` lines, so the next project
  does not rebuild the ten.

## What is NOT proposed

- Cutting the review (step 9): it is the phase's gate and the one place a second vendor sees the package.
- Cutting 2.2: `verify_prediction` is what the desk path has instead of the car; without it the sheet is unchecked.
- Changing the iterative path: a project that measures between packages still needs 2a's control series. The cuts
  are about not mixing the two paths in one plan, not about removing one of them.

**His call:** which of the four cuts (1→2, 3, 4's trip, 6 and 7 to Phase 3) to take, and whether the step-naming
rule goes into `SKILL.md`. The text changes follow his word.
