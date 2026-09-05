# TODO — maintainer's backlog

Work that is understood but not yet due. Not the roadmap: `ROADMAP.md` is product direction for
people who use the method, this is engineering debt for whoever maintains it. An item here carries
**what would make it due**, because an item whose trigger is "when someone remembers" is the kind
that gets found again three months later as a surprise.

---

## S-001 · `deployment.py` cannot tell a DECLARED pin from a split

**Due when:** the first tuning project is pinned to a version and still being worked on. Not before.

**State today.** `rew_tool/deployment.py` refuses (exit 3) whenever two reachable deployments are
different commits. That is right for a split nobody chose, and wrong for a pin somebody chose on
purpose: a run held at `v3.0.33` for reproducibility will be refused every session, on the thing it
is doing correctly. A check that cries wolf on a deliberate arrangement teaches people to skip it —
and this module's own `verdict()` already carries that argument, in the paragraph explaining why
the grouping key is the sha and not the path. The same reasoning applies one level up, and this
item is where it lands.

**The form is already decided**, and it is the one shape on this machine that never drifted:
`autosound-tcc` carries the skill as a submodule, so the CONSUMER records the sha it expects and
git compares the record against what is checked out. Generalise that:

* the project records the version it is pinned to — a field beside the other project facts
  (`rew_tool/project.py`, `project.json`), not a new file and not a second place;
* a reachable deployment matching the record reads as **agreement**, not disagreement;
* a deployment that does NOT match the record is a harder failure than today's exit 3 — the run
  says which version its numbers were computed on, and something else is on the path;
* a project with no record behaves exactly as now. Absent is not the same as satisfied, and a
  silent default would put this module back where it started.

**What must not happen:** the pin becoming declarable in a file nobody compares against. That is
the failure this module was written for — the 2026-08-13 rule about the personal symlink lived in
a memory file, was contradicted by `install.sh:774`, and nothing noticed for thirteen days. A
declaration is only worth having where a check reads it.

**Trigger is live, not written down:** `deployment.py` already names this gap in its refusal when
one of the disagreeing checkouts is held (`DETACHED`), and points here. It arrives with the case.

**Raised** 2026-08-29, out of autosound-hub HUB-006, by the person whose run was pinned.

---

## S-002 · A proposed delay is printed in ms the device cannot hold

**Due when:** the first alignment sheet is entered by hand and the verdict is read at a tweeter
joint — or when the delay quantiser's direction (below) is measured, whichever comes first.

**State today.** The Helix quantises a typed delay to a **whole sample** at the processing rate
(10.4167 µs at 96 kHz; bench 2026-09-02, fact 3): 0.05 ms lands on 5 samples = 0.0521 ms. The
settings sheet (`state/apply.py`) keeps ms as the source of truth and derives samples for the rate,
so the samples column IS what the device holds — but `predict --align` searches on a 1000/rate grid
and reports `tau_ms` to four decimals, and `setup_import` checks a transcription against the
profile's `step_ms` (0.01), which is the UI's entry step and not the grid the device keeps. Worst
case half a sample per channel, 5.2 µs — 1.8 mm, or 19° at 10 kHz. Small, real, and unstated.

**The form:** snap a proposal to `round(ms × rate / 1000)` samples before it is printed, print the
ms the device will actually hold beside the ms that was asked for, and make `setup_import`'s grid
check use the sample grid when the profile says `delay.sample_quantised`. **Not before** the
direction is known: the two fractions measured (4.800 and 30.720 samples) both sat above the
half-sample, so rounding and truncation upward are not separated (`_open_questions` in the Helix
profile) — a snap in the wrong direction is a whole sample off, worse than no snap.

**Raised** 2026-09-05 from the Resonalyze-fork bench handoff (fact 3).

## S-003 · `apf1_response` models the typed corner; the Helix places a lower one

**Due when:** an AP1 band is prescribed on this hardware above ~2 kHz, or a second processor is
measured and the deviation turns out to be Helix-specific.

**State today.** Four points, one rig: typed 250 / 1000 / 4000 / 8000 Hz land at 248.8 / 993.2 /
3936 / 7611.6 (−0.5 / −0.7 / −1.6 / −4.9 %); AP2 in the same session within 0.05 %. The shape is a
clean first-order all-pass, so it is the frequency and not the form, and no simple law fits — not a
constant percentage, not an offset, not the un-prewarped substitution (7824 at 8 kHz). Cost of
modelling the typed value: 0.4° at 1 kHz, 0.9° at 4 kHz, 3.0° at 8 kHz. The method already prefers
AP2 (REW cannot mirror AP1 either), so today this is a documented deviation
(`helix-phase-allpass.md` §3, the `apf1_response` docstring), not a wrong number in a tune.

**The form, if it becomes due:** a per-profile correction table (typed → placed) read by
`eq_complex` for `APF1` on a profile that carries it — not a law, since none fits, and not a global
change, since it is one processor's. Four points are too few to interpolate honestly between; the
bench would need the octaves in between first.

**Raised** 2026-09-05 from the same handoff (fact 1).

## S-004 · The phase control's ceiling is known at one rate

**Due when:** a 48 kHz Audiotec-Fischer unit (a MATCH, or an older HELIX) is on a bench.

**State today.** `phase_rotation.MAX_CORNER_FRACTION = 3/16` — 18 kHz at 96 kHz. Three
recoveries at two references gave 18007–18010 Hz, which is 3/16 of the rate AND an absolute 18 kHz
within the spread; one rate cannot separate them. The rate-relative reading is taken (as Resonalyze
does); on a 48 kHz unit it predicts a 9 kHz ceiling where the absolute reading predicts 18 kHz, and
every setting at a reference above ~500 Hz would differ between the two. **One measurement decides
it**: any capped setting at a high reference on a 48 kHz device — the fitted corner is either 9 kHz
or 18 kHz. The constant is the one line to correct; the selftest's 48 kHz case (9 kHz, 7674 Hz for
90° at 5 kHz) is the assertion that would flip with it.

**Raised** 2026-09-05 from the same handoff (§1).
