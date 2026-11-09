# Joint by joint — one way of doing the desk (Phases 1–2)

> 🗺️ **One order of phases, two ways of doing the desk.** The order of work stays
> [`virtual-first.md`](references/phases/virtual-first.md)'s: −1, 0, desk, 3, 4. This page replaces the desk steps of Phases
> 1–2 only, when `goal.desk_approach` is `joint_by_joint` or `both` ([`project-intake.md`](references/core/project-intake.md)
> §4); Phases 0, 3 and 4 stay as they are, and so does every gate of `phase_1_foundation.md` and `phase_2_eq.md`.

> 📏 **Reading cost.** This page is read when the way is chosen and is outside `scripts/reading-cost.py`'s `ORDERED`, so the
> reading-cost budget does not count it.

> **Each car has its own solution** (the Arbiter, 2026-11-08). This page gives rules, approaches and variants, with what each
> is for and where it fails. It is not a recipe. `joint_search.py` and `version_bench.py` are a **library**, and every threshold
> below is a **default**, named, changed by a flag and shown with its effect. Where no tool fits a car, the session writes its
> own analysis and keeps the same evidence: the table of what was searched, the metric, the variants compared, the choice with
> its reason. **Only two things are hard:** what the hardware cannot do (the DSP's families, ranges and steps, the delay
> ceilings) and driver safety (the Fs floors). Everything else on this page can be argued with.

**Evidence, as it is:** one car (VW Passat B8 sedan, Helix DSP Ultra S, 3-way front + centre + sub), nine days (26.10–03.11.2026),
one listener. The method held there; nothing here has run on a second car yet. The numbers below are that car's, as examples.

## 🎯 Goal-node

**Purpose:** build the tune upward one joint at a time, each joint a search over what the DSP can do, scored by explicit
metrics, the best few compared and one chosen, then whole configurations compared at matched loudness and blended.

**Questions this page answers:**
- At each joint, which filters, delay and polarity keep the two drivers together across the head's positions?
- What must each joint hold for the joints below and above it?
- Which whole configuration wins by the model and then by ear, and what does each lose against the others?

**Required evidence:** one raw capture (Phase 0): every channel's tripod solo on the loopback base, and the nine points for every
front driver and the centre; the target on the record; a way to read a saved preset back; the DSP's profile.

**✅ Quality gate → Phase 3:** each joint's table kept (`--out`), one row chosen for each with the reason and the tuner's OK; the
chosen configurations banked as ledger versions; `version_bench.py table` run on them; every A/B at matched loudness and against a
saved preset read back and matched to the ledger; the winner's sheet ready (`virtual-first.md` 2.4). Phase 1's gates stay.

**⚠️ Failure modes:** treating the table's first row as the answer → the tool describes, the ear decides · a joint chosen on one
point → the nine points are what show it survives a moving head · a filter that does not exist on this DSP → the search only offers
what the profile has · a cut placed on a joint and not re-checked → fusion breaks (lesson 1 below) · an A/B at different
loudness → the louder one wins · an A/B against a preset nobody read back → an entry error is judged as a tune.

**🧩 Refs:** [`capture-session-sheet.md`](references/phases/capture-session-sheet.md) (the capture) ·
[`rew-tool-docs.md`](references/tooling/rew-tool-docs.md) (`joint_search`, `version_bench`, every flag) ·
[`screen-read-dsp.md`](references/tooling/screen-read-dsp.md) (reading a preset back) ·
[`virtual-first.md`](references/phases/virtual-first.md) (the desk steps this replaces, the sheet, Phase 3) · issue #210.

---

## 1. What this way needs and what it gives

| | |
|---|---|
| **Needs** | several DSP memories (each compared configuration is a slot) · the raw capture with the nine points · a way to read a saved preset back · time for A/B listening at the reference seat |
| **Gives** | a ranked set of variants with the reasons behind each, and a choice the tuner made and can defend; not one answer |
| **Does not need** | the Resonalyze engine. With `goal.desk_approach: both`, its best configuration is one more contestant (§7) |
| **Is not offered** | to a light touch (`goal.mode: light_touch`): it has no capture session |

Out of this path's tools, and said rather than worked around: a tool for the RTA discriminator (§10 is a step without a tool), the
centre's delay (the existing steps run after the joints: `virtual-first.md` 1.5), a reader for a saved preset file (read it back from the
screens, `screen-read-dsp.md`), a tool for the blend (§9 is a re-run of the search).

**The steps, for the plan** (`add-step`, source `skill`, Phase 1; TCC renders an unknown step id):

```
add-step 1.J1 "the bass joint: the variants table and the chosen row"
add-step 1.J2 "the woofer-mid joint: the variants table and the chosen row"
add-step 1.J3 "the mid-tweeter joint: the variants table and the chosen row"
add-step 1.J4 "the configurations banked and compared side by side"
add-step 1.J5 "the A/B verdict at matched loudness"
```

(A 2-way has no 1.J2: its second joint is the woofer-tweeter, named so in 1.J3.)

## 2. The capture

The capture does not depend on the desk approach: **one full raw capture for every project**, whichever way the desk goes, and the desk approach
can still be changed after the capture. Block B of [`capture-session-sheet.md`](references/phases/capture-session-sheet.md)
is the recipe: the nine points for every front driver and the centre, on the fixed path in front of the nose; the tripod solos of
every channel; the raw `v0` state. Everything below is computed on these curves. No re-measuring between desk variants: the same
capture served more than ten of them on the reference car.

Nine points refused: the session says the limits in words before the capture and the decision is recorded (the sheet, after block
B); `joint_search.py --single-point` then runs on the centre point, every row marked, and refuses without that record.

## 3. The order of joints: bottom up

Sub ↔ woofers, then woofer ↔ mid, then mid ↔ tweeter. A 2-way + sub has sub ↔ woofer and woofer ↔ tweeter; a front sub is the
same code; the stack is `xover_wishes.ROLE_ORDER` over the channels present, each adjacent pair one joint.

**Why bottom up:** the bass joint is fixed by the cabin and has the least to give; once it is chosen it is a condition for everything
above it. A joint above can be searched against what is already held, and it can move the group above it as one, so the stage and the
joints below stay. Choose from the top down and every joint below pulls the top apart again. Where a car argues otherwise, argue it.

## 4. Before the crossover: align-then-cross and cross-first are variants

**Align-then-cross** (`--align`): each driver alone is put on the target first (gain up ≤ 6 dB, ≤ 4 cuts of ≤ 6 dB), then the crossover
is searched on the flattened chain. **Cross-first:** the crossover is searched as the drivers are, and the same EQ budget is spent on
the sum after. Neither is the method. On the reference car they gave different things: the flatten-first variant had the better microdynamics
(it kept 250–400 Hz off the door woofers that ring long there), the symmetric variant (the same filters L and R, with the L−R offset held: §6) the steadier stage. `--align` runs both
variants unless `--no-cross-first` is given. Compare them at this joint and in §7, not in principle.

Where it fails: a flatten eats phase margin near a joint; cuts on the overlap can break fusion (§11). A flatten that cannot stay inside the
DSP's gain range brings every channel down alike, not one side (`global_trim_db`).

## 5. Each joint: what is searched and which metric answers what

The commands run on the whole raw capture; `--out` keeps the table and JSON for the record. Read the flags in `rew-tool-docs.md`.

| joint | command | searched |
|---|---|---|
| bass | `python3 rew_tool/joint_search.py --project <p> --house <curve> --solos <dir> --joint bass --out <dir>` | sub LP × woofer HP × sub level × polarity × sub/front delay; the woofer L−R offset held |
| woofer ↔ mid | `python3 rew_tool/joint_search.py --project <p> --house <curve> --solos <dir> --joint woofer-midrange --fixed <bass.json>@<N> --align --out <dir>` | every w LP × m HP pair over the DSP's families and corners, m HP ≥ the mids' Fs floor, every delay shift, both polarities |
| mid ↔ tweeter | `python3 rew_tool/joint_search.py --project <p> --house <curve> --solos <dir> --joint midrange-tweeter --fixed <wm.json>@<N> --out <dir>` | every m LP × tw HP pair, tw HP above the tweeter's Fs floor (the craft margin of `crossover_checks.fs_margin`), every delay shift, both polarities |

`--rew --ver <N>` reads live REW instead of `--solos`. The table is what a person keys in: every row names filters, delays and gains on the DSP's own steps. It never picks.

On the reference car the defaults at the woofer ↔ mid joint (the same filters L and R, the 1/6-oct corners) gave only weak rows; the pairs the run banked had different filters on the two sides or corners off that grid. `--corners-per-side --no-same-family` admits them, at the price of the stage conditions they relax. When a table is thin, widen it and say what you loosened.

**Which metric answers what.** A metric is a question; pick by what the joint can answer at that frequency.

- **Under 1 kHz: the ±30° band.** The width, in octaves, of the band around the acoustic crossing where the two drivers' phases stay
  within ±30°, at the worst and the median of the nine points. It answers "do they stay together as the head moves". The competition
  tune and the user's own try scored 0 oct at the worst point on the reference car, the best candidates 1.6–1.76.
- **Summation loss** |a+b| against |a|+|b| over ±½ oct: how much the pair loses when summed. A number beside the band, not instead of it.
- **From 1 kHz: the power sum and the ear groups.** Above 1 kHz the mid-tweeter time difference spreads by about ±0.4 ms over the nine points, so
  a ±30° band means nothing. The answer changes: the nine-point power sum `10 log10(|m+tw|² / (|m|²+|tw|²))`, then the worst of the left-ear, right-ear and
  centre groups must not cancel, then the flattest response to the target. p1/p5/p9 are the centre, p2–p4 left, p6–p8 right: the ear
  groups come from the order of the points (the sheet) and the arrivals check it.
- **A joint whose bounds straddle 1 kHz** gets two lists, one per class: their scores do not compare.
- **The margin over a delay tolerance.** A delay is not known better than a head moves or a DSP step allows, so a row is ranked by what survives a small shift of
  the delay: the narrowest band within ±0.10 ms under 1 kHz (about 3.4 cm of head movement), or within ±0.02 ms from 1 kHz up. Why: on the reference car's bass joint
  **every width peak was one delay step wide**; a peak one step wide is suspect, because a head a few centimetres away or the DSP's next step is off it. The table
  ranks by the margin and shows it beside the peak.
- **And the ear may still choose such a peak.** On the reference car the chosen bass tune was one: widths 0.58 / 0.98 / 0.57 oct at the three neighbouring delays,
  ranked 108 of 238 by the margin, and the Arbiter heard it as the right one. The table describes; the ear decides. A peak the ear chooses is banked with that said.
- **Dip against the target, decay, the L/R phase** sit beside these. The decay (`ear_suspects.ringdown_ms`, in the woofer-mid table) is reported, not ranked: the
  reference car's door woofers rang 26–40 ms at 200–400 Hz against the mids' 10–24 ms, so a variant that hands 250–400 Hz to the woofers booms whatever the EQ does.

Where each fails: the ±30° band is meaningless once the drivers' arrivals spread over more than the band's phase tolerance; the power sum says nothing about
one narrow listening point; a margin at ±0.10 ms is a guess about how far a head moves.

## 6. Conditions carried upward, and which to loosen when

Each joint carries the ones below it as a condition. Defaults, each with a flag:

| condition | default | loosen when |
|---|---|---|
| the bass joint below (`--fixed`, `--bass-drop`) | may lose ≤ 0.1 oct, re-scored under each candidate | the joint above gains more than the bass loses, and the ear agrees |
| the mid/tweeter L−R arrival offset held at the raw centre-point difference, ±0.10 ms (`--no-lr-offset`, `--lr-tolerance`) | on; a free per-side search moved the offset by up to 1 ms on the reference car and pulled the image aside | the seat is off-centre by design, or the stage is judged by ear to want it |
| same absolute polarity L and R (`--no-same-polarity`) | on | a measured reason on this car |
| same family and order L and R, corners alike (`--no-same-family`, `--corners-per-side`) | on (L-vs-R phase 250–800 Hz at the head centre went 48° → 21–23° with it) | a side's install really differs |
| leak: each driver under the other an octave out (`--no-leak`, `--leak-*`) | −24 dB; bass −24 at 100 Hz, −30 over 125–200 Hz | the search comes back empty and the table says why |
| dip against the target (`--no-dip`, `--dip-limit`) | −3.5 dB | a dip that EQ will take care of after the joint |

A condition off is said in the table and in the record. A hard limit (Fs floors, families, ranges, delay ceilings) has no flag to loosen.

## 7. Whole configurations compete

Each complete variant is a ledger preset and a DSP memory: flatten-first, cross-first, symmetric, the blend (§9), the current tune on a car that is already tuned
(`virtual-first.md`, "Two ways in"), and, **when the person chose both**, the Resonalyze engine's best from `resonalyze_engine.py run` (with `--current` on an improved car). They go
side by side first by the model, then by ear:

```
python3 rew_tool/version_bench.py table --project <p> --solos <dir> --house <curve> <version> <version> <version>
```

The table gives the front's picks on its four terms, with the joint widths, ear sums, decay and L/R phase beside them and not part of the picks; it never takes an argmax.
`round-check` compares each tripod sum against the complex sum of its solos, `lr-phase` shows L against R. Versions on different point coverage refuse rather than compare.
Whichever path built them, the comparison is the same; both paths in one table need nothing more.

**From a chosen row to a version.** A row is not a delta: the table's `delay_ms` is the ledger's `ta_ms`, and `propose` refuses it under the old name. Every row of `joint-<name>.json` carries `delta`, the row in the ledger's own fields, so `rows[N-1].delta` (N the row's `#N`) is what goes in. The top joint's row carries the channels below it. Write it to a file:

```
python3 rew_tool/state/apply.py <p> propose <delta.json> --on HEAD --note "<the variant>"
```

A variant that moves a corner, a polarity or a delay by 0.5 ms or more is structural: **without evidence and a reviewer it banks as a candidate**, on the line and not in the slot, which `version_bench.py table` reads by its version. The next `propose` on that slot is refused without `--on` while the newest version is a candidate, and `--on HEAD` builds the next variant from HEAD, not on the candidate before it.

**Each variant earns its place on its own:** evidence (the joint's kept JSON is a desk result; no car trip is needed) and a reviewer, once per variant:

```
python3 rew_tool/state/apply.py <p> propose <{}.json> --on <the candidate> --evidence <joint-<name>.json> --reviewed <the review file>
```

(`{}.json` is an empty delta; a relative path in `--evidence` and `--reviewed` is read from the project folder; the reviewer's file is what `scripts/autosound_ai.py critic <package> --record` wrote.) `propose` prints the settings sheet the person keys in. **`attest` comes after the keying in**, on the version that `propose` just made, not on the candidate, which `attest` refuses:

```
python3 rew_tool/state/apply.py <p> attest <v_NNN>
```

## 8. A/B only at matched loudness, and only against a preset read back

Before any A/B: the loudness matched (`version_bench.py loudness`: Zwicker ISO 532-1 through `mosqito` where installed, otherwise ISO 226 at 80 phon, labelled as less exact when versions differ in
the bass; confirmed on an RTA within 0.05 dB on the reference car). And the saved preset read back and matched to the ledger (entry errors caught every time they happened there): no reader
for a preset file in this path, so read the screens (`screen-read-dsp.md`).

## 9. The blend

The Arbiter heard one variant's stage as steadier and another's microdynamics as better; the analysis traced the difference to the woofer-mid joint (decay, filter group delay). The next variant took
the symmetry of one and the joint of the other, re-running the search with the first as `--fixed` and moving the group that was free to move (`--move lower` moves the woofer, `--move upper` the mid and the group above, which keeps its relative delay and flips with it). **The blend is a re-run with `--fixed` and `--move`**, not a tool of its own: choose what to hold, choose who moves, read the table again, bank.

```
python3 rew_tool/joint_search.py --project <p> --house <curve> --solos <dir> --joint woofer-midrange --fixed <row.json>@<N> --move lower --out <dir>
```

## 10. A cheap discriminator before a full series (a step, no tool)

A full series of a configuration is expensive. Before taking one, an RTA of a handful of sums per configuration (the reference car used five, by MMM) shows tonality against the target, L−R per band, the centre's share and the loudness, and the configuration that can win on them stands out. It is
described here and has no tool: the session reads the sums with what `verify_prediction.py` and the RTA overlays offer and writes its own comparison. The reference car's final one read rms 1.66 dB from the target 80 Hz–10 kHz against 1.90 for the competition tune it started from, L−R at 160–1250 Hz within ±0.1 dB. Then the full series for the winner confirmed the model, and the ear finished it with one-parameter ladders.

## 11. Lessons from the ear (#210)

1. **A cut placed on a joint can break the fusion of the two drivers** (a voice split vertically on one side, fixed by 3 samples of tweeter delay). Re-check fusion after any cut on a crossover overlap.
2. **Harshness only at +10 dB** is a different question from harshness at listening level: RTA and THD at both levels first. On the reference car it was the ear, and the treble corner of the remote tone control (6.3 kHz) solved it, not a static EQ.
3. **A verdict counts only from the reference seat.**
