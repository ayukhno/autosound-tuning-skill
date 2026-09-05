# Helix DSP Ultra S — bench curves the selftests run against

Ten measured curves and one table of fitted cases, copied **verbatim** from
[`ayukhno/autosound-measurements`](https://github.com/ayukhno/autosound-measurements),
`hardware/helix/dsp-ultra-s/` at commit `5254c16` (2026-09-05), **CC BY 4.0** (`LICENSES/NOTICE.md`).
The facts they decided are in that repo's `FACTS.md`; the method's reading of them is in
`knowledge/dsp/helix-dsp-ultra-s.md` and `references/tooling/helix-phase-allpass.md`.

Why they are here: every other anchor in `dsp_math`'s selftest is a *definition* (LR is −6.02 dB
at its corner because it is Butterworth squared) or an *independent evaluation path* (design in
ZPK, evaluate in the z plane). None of those can say that the **processor** builds these filters.
These files can, and a check that runs on every push cannot depend on a network fetch.

## The files

All are `frequency_Hz<TAB>dB<TAB>phase_deg`, **1/96 octave anchored at 20 Hz, 957 points,
20 – 19897 Hz, unsmoothed**, exported from REW's raw linear spectrum by complex averaging into
each cell with the measurement's own delay removed before averaging and restored after. Lines
starting with `*` are the file's own header. **Electrical**: processor output straight into the
interface, no microphone, no cabin — the right shape when the question is the DSP's arithmetic.

| set | files | reference | decides |
|---|---|---|---|
| BW24 at 460 Hz, 2026-09-04 (`bw24-manifest.json`) | `bw24-460-hp` (the filter under test), `lr24-460-hp` (the control), `bw24-460-bypass-ctl` (the reference again, last) | `bw24-460-bypass` | the even-order Butterworth against `xo_response`, read as a **difference to a control** taken in the same 54-second pass (hub `#32` / `#64`) |
| BE36 at 1 kHz, 2026-09-01 | `fact9-be36-1k-lp`, `fact9-be36-1k-hp` | `fact9-be36-1k-bypass` | the Bessel normalisation: `norm="mag"` (−3 dB at the corner), not delay-normalised |
| LR36 at 8 kHz, 2026-08-31 | `fact8-xover-lr36-8k-lp`, `fact8-xover-lr36-8k-hp` | `fact8-xover-lr36-8k-bypass` | the filter is a bilinear-transformed digital biquad chain at the **processor's rate** — at 8 kHz on 96 kHz the analogue model and the digital one separate; at 1 kHz they do not |
| the phase control, 2026-09-02 (`bench3-manifest.json`) | `phase-control-vectors.json` — 32 cases | (each case is the ratio of its own file to its group's `ph0` capture; the curves themselves are not copied) | `phase_rotation`: the model side is Resonalyze's compiled `PhaseRotationControl` (`bc957c8`), the bench side the free fit of the published curve; **four cases are flagged `free_fit_trustworthy: false`** because the capped corner sits above the band their active crossover left usable — the residual is evidence there, the fitted corner is not. Do not remove the flag: the selftest proves it is load-bearing |

**The one rule for using them:** every set carries its own reference capture and **only ratios
within a set mean anything**. Levels are REW's electrical dB and are not comparable across sets.

## How the selftest reads them

`dsp_math._selftest` (the "against the HARDWARE" block) takes each filter file over its set's
reference as a complex ratio, computes `xo_response` **at 96 kHz** on the file's own grid, and
compares over a **stated band**, above a **stated mask** (bins where the measured leg is deeper
than the mask are stopband noise, not evidence), with the best-fit **delay and offset removed**
from the phase and the median removed from the magnitude. The band, mask and grid are part of
every number, because an rms is a weighted number and the grid is the weight: the same BW24
residual reads **0.443° on this grid and 0.220° on REW's raw linear bins** — nothing about the
filter differs (`diagnostic-techniques.md` §35). Where a control exists the assertion is on the
**difference** to it, which held to 0.11° across every mask from −40 to −10 dB while the absolute
number moved twenty-fold.

Re-derive any number here with `python3 rew_tool/dsp_math.py selftest`; the block prints what it
measured. The upstream numbers to compare with are in `FACTS.md` (facts 6, 8 and 9) and, for the
phase control, in `phase-control-vectors.json` itself.
