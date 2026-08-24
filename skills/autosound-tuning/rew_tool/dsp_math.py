"""Vectorized DSP building blocks for the v3 acoustic-target pipeline.
All responses are complex numpy arrays over an arbitrary frequency vector,
digital-domain at FS=96000 (matches Helix DSP Ultra S).
"""
import numpy as np

FS = 96000.0


# ---------- crossover filters (same conventions as v2, minus Chebyshev) ----------
# scipy is needed ONLY here (Bessel/Butterworth design). Everything else in
# this module — PEQ/shelf/APF responses, alignment, APF search, robust
# metrics, greedy EQ fit — is pure numpy and must keep working without scipy
# (soft degradation: an install without scipy can still run eq_gate and all
# joint-phase analysis; only crossover REALIZATION needs the extra dep).

def _scipy_signal():
    try:
        from scipy import signal
        return signal
    except ImportError as e:
        raise RuntimeError(
            "dsp_math.xo_response needs scipy for crossover design "
            "(Bessel/Butterworth/LR). Install it: pip install scipy. "
            "PEQ/APF/joint-phase functions work without it.") from e


def _design(order_db_per_oct, wn, btype, ftype):
    """Second-order sections, never (b, a).

    The transfer-function form breaks down for a high-order filter at a low normalised frequency:
    the polynomial coefficients span many orders of magnitude and evaluating them loses the answer
    to floating point. Measured on this module's own grid before the fix (error at the filter's own
    corner, where every family has a defined value): BW42 at 80 Hz was off by -30.1 dB, BE42 at
    63 Hz by -28.0, BE36 at 40 Hz by +13.2. That band is where a sub/midbass joint lives and steep
    slopes are exactly what gets chosen there, so the worst errors sat on the most-used settings.
    Cascaded second-order sections are conditioned per section and give 0.000 dB across the whole
    grid. Found 2026-08-22 (see the selftest's corner anchor, which is what would have caught it)."""
    sig = _scipy_signal()
    n = max(1, round(order_db_per_oct / 6))
    if ftype == "BE":
        # norm="mag" (-3 dB at the corner) matches REW's BE shapes, verified
        # against REW predicted responses 2026-07-12 (norm="phase" gave up to
        # 27 dB transfer-function error on BE12/BE18 channels)
        return sig.bessel(n, wn, btype=btype, norm="mag", output="sos")
    return sig.butter(n, wn, btype=btype, output="sos")


def xo_response(freqs_hz, corner_hz, order_db_per_oct, kind, ftype):
    """Complex response of one HPF/LPF slot. kind: 'hp'|'lp'. ftype: 'BW'|'BE'|'LR'."""
    sosfreqz = _scipy_signal().sosfreqz
    wn = min(max(corner_hz / (FS / 2.0), 1e-4), 0.999)
    btype = "highpass" if kind == "hp" else "lowpass"
    w = 2 * np.pi * freqs_hz / FS
    if ftype == "LR":
        sos = _design(max(6, order_db_per_oct // 2), wn, btype, "BW")
        _, h = sosfreqz(sos, worN=w)
        return h * h
    sos = _design(order_db_per_oct, wn, btype, ftype)
    _, h = sosfreqz(sos, worN=w)
    return h


# ── enterable vs modellable: two questions, and they must not share one list ───────────────────
#
# **ENTERABLE** is a fact about a PROCESSOR — can the device be given this filter? It lives in the
# project's `dsp_profile.json` under `crossover_filters.types`, differs per model, and is the right
# question when VALIDATING something a person already chose.
#
# **MODELLABLE** is a fact about US — do we have a realisation we trust? It lives here, is the same
# for every DSP, and is the right question when PROPOSING. A search that offers a filter we cannot
# predict is worse than one that offers nothing: the tuner enters it and neither of us knows what
# it did.
#
# Conflating them is how a Chebyshev crossover would come to be recommended. The Helix offers the
# family; an experiment was run and could not identify its mathematics (user, 2026-08-23), so the
# ripple is unidentified and the filter is not DETERMINED. Enterable, not modellable. It is the
# same shape as the sub's 20-300 Hz UI range in mirror image -- there, one field answering two
# questions would have REFUSED something possible; here it would PROPOSE something unpredictable.

#: Families this module has a trusted realisation for. OURS, not any device's.
MODELLABLE_FAMILIES = ("LR", "BW", "BE")

#: Orders the Butterworth/Bessel realisations cover.
XO_BW_ORDERS = (6, 12, 18, 24, 30, 36, 42)

#: A DEFAULT search space, and it is the reference car's grid rather than a universal truth: LR at
#: 12/24/36 is what a Helix DSP Ultra S offers, not a property of Linkwitz-Riley. Prefer
#: `options_for(profile_types)` whenever a profile is in hand -- this constant is what to use when
#: none is, and it is deliberately the narrower of the two so that being wrong means proposing too
#: little.
XO_OPTIONS = (
    [("LR", o) for o in (12, 24, 36)]
    + [("BW", o) for o in XO_BW_ORDERS]
    + [("BE", o) for o in XO_BW_ORDERS]
)


def options_for(profile_types, families=MODELLABLE_FAMILIES):
    """The search space for THIS DSP: what it can be given AND what we can predict.

    `profile_types` is a `dsp_profile` group's `crossover_filters.types` -- `{"LR": {...}, ...}` --
    passed as a plain dict so this module stays free of the profile schema.

    A family the profile declares and we cannot realise is dropped, which is the point. A family
    we can realise and the profile does not declare is dropped too: proposing a filter the device
    will not accept wastes a tuner's trip to the car.

    A family whose own parameters are unstated (`ripple_db: null`) is NOT modellable regardless of
    the list -- the filter is not determined by family and order alone, so there is nothing to
    realise. That check is here rather than at the call site because forgetting it is silent.
    """
    out = []
    for family in families:
        spec = (profile_types or {}).get(family)
        if not isinstance(spec, dict):
            continue
        if any(value is None for key, value in spec.items() if key != "orders_db_per_oct"):
            continue
        for order in spec.get("orders_db_per_oct") or ():
            if isinstance(order, int):
                out.append((family, order))
    return out


# ---------- biquad EQ (RBJ cookbook, digital, matches Helix PEQ bank) ----------

def _biquad_h(freqs_hz, b0, b1, b2, a0, a1, a2):
    z1 = np.exp(-1j * 2 * np.pi * freqs_hz / FS)
    z2 = z1 * z1
    return (b0 + b1 * z1 + b2 * z2) / (a0 + a1 * z1 + a2 * z2)


#: The ledger spells the shelves `LSH`/`HSH` (`state.EQ_TYPES`); the fitter and the older callers
#: here say `LS`/`HS`. One table, so a band read straight out of a ledger renders as the filter it
#: names instead of falling through to the wrong branch.
_SHELF_KINDS = {"LS": "LS", "LSH": "LS", "HS": "HS", "HSH": "HS"}


def peq_response(freqs_hz, kind, f0, gain_db, q):
    """kind: 'PK' | 'LS'/'LSH' | 'HS'/'HSH'. Complex response.

    Anything else is refused. It used to fall through to the high shelf — `PK` was one branch,
    `LS` another, and *everything else* the third — so an `APF2` band handed in here came back as
    a shelf with no error anywhere (SCR-050, 2026-08-18). An all-pass has its own functions below;
    `eq_complex` is the one place that dispatches by kind.
    """
    if kind != "PK" and kind not in _SHELF_KINDS:
        raise ValueError(f"peq_response: unknown EQ kind {kind!r} (PK, LS/LSH, HS/HSH; "
                         f"an all-pass goes through apf1_response/apf2_response)")
    A = 10.0 ** (gain_db / 40.0)
    w0 = 2 * np.pi * f0 / FS
    cw, sw = np.cos(w0), np.sin(w0)
    if kind == "PK":
        alpha = sw / (2 * q)
        c = (1 + alpha * A, -2 * cw, 1 - alpha * A,
             1 + alpha / A, -2 * cw, 1 - alpha / A)
    else:
        # shelves with S=1 (RBJ), q arg ignored
        alpha = sw / 2.0 * np.sqrt(max((A + 1 / A) * (1 / 1.0 - 1) + 2, 0.0))
        tsa = 2 * np.sqrt(A) * alpha
        if _SHELF_KINDS[kind] == "LS":
            c = (A * ((A + 1) - (A - 1) * cw + tsa),
                 2 * A * ((A - 1) - (A + 1) * cw),
                 A * ((A + 1) - (A - 1) * cw - tsa),
                 (A + 1) + (A - 1) * cw + tsa,
                 -2 * ((A - 1) + (A + 1) * cw),
                 (A + 1) + (A - 1) * cw - tsa)
        else:
            c = (A * ((A + 1) + (A - 1) * cw + tsa),
                 -2 * A * ((A - 1) + (A + 1) * cw),
                 A * ((A + 1) + (A - 1) * cw - tsa),
                 (A + 1) - (A - 1) * cw + tsa,
                 2 * ((A - 1) - (A + 1) * cw),
                 (A + 1) - (A - 1) * cw - tsa)
    return _biquad_h(freqs_hz, *c)


def apf1_response(freqs_hz, f0):
    """1st-order allpass (APF1 in an EQ slot): unit magnitude, phase 0 → −180° through `f0`.

    −90° at `f0`, and that is the whole filter — one number to type. The same analog convention
    as `apf2_response` (phase lag, negative going), so the two stack and compare directly; where
    the second order turns a full 360°, this turns half of it, which is what makes it the right
    tool for a joint that needs a quarter turn and not a half (SCR-050 item 4, 2026-08-18).
    """
    x = np.asarray(freqs_hz, dtype=float) / f0
    phase = -2.0 * np.arctan(x)
    return np.exp(1j * phase)


def apf2_response(freqs_hz, f0, q):
    """2nd-order allpass (APF2 in the Helix PEQ bank): unit magnitude, phase only.

    0 → −360° through `f0`, −180° AT `f0`, and `q` sets how much of the turn happens near it."""
    x = np.asarray(freqs_hz, dtype=float) / f0
    phase = -2.0 * np.arctan2(x / q, 1.0 - x * x)
    return np.exp(1j * phase)


# ---------- deterministic inner solvers ----------

def align_delay_polarity(freqs_hz, A, B, band, max_delay_ms=3.0, step_ms=0.01,
                         polarities=(1, -1), tie_frac=0.005):
    """Delay tau (applied to B) and polarity maximizing sum energy in band.
    Vectorized over the full tau grid.
    Returns (pol, tau_ms, residual_null_db, polarity_margin_db).

    The near-tie rule spans BOTH polarities, which is the whole point: among
    candidates within `tie_frac` of the best sum, the smallest |tau| wins, and a
    flipped candidate half a period away is a lobe like any other. Applying the
    rule inside each polarity and then settling the two with a bare `>` — as this
    did until 2026-08-22 — let a 0.001 dB difference choose a polarity AND a lobe,
    the one place the function refused its own "fractions of a dB decide nothing".
    tau = 0 is the prior here because both branches come from one measurement on
    one time base; that is also why no "prefer non-inverted" margin is imported
    from tools that align raw arrivals — at an ODD-order Linkwitz-Riley joint the
    inverted connection is the correct one (LR36 wins by only 0.17 dB in the
    selftest), and such a margin would break it.

    `polarity_margin_db` is how much the chosen polarity beats the other one at
    its own best tau — the number that says whether summation decided the choice
    or merely reported it. It goes NEGATIVE when the near-tie rule deliberately
    takes the marginally weaker polarity because that one is more compact, which
    is the rule working, not a fault. `inf` when only one polarity was searched."""
    m = (freqs_hz >= band[0]) & (freqs_hz <= band[1])
    f, a, b = freqs_hz[m], A[m], B[m]
    taus = np.arange(-max_delay_ms, max_delay_ms + step_ms / 2, step_ms) / 1000.0
    rot = np.exp(-2j * np.pi * np.outer(taus, f))          # (n_tau, n_f)
    energies = np.array([np.sum(np.abs(a[None, :] + pol * b[None, :] * rot) ** 2, axis=1)
                         for pol in polarities])           # (n_pol, n_tau)
    ip, it = np.where(energies >= (1.0 - tie_frac) * energies.max())
    # Smallest |tau| among the near-ties. This is DOCTRINE, not a bias (re-litigated and kept
    # 2026-08-24): on a flat synthetic pair with tau = 0.37 ms it answers 0.33, because the
    # energy surface is flat to within 0.5 % for four steps either side and the rule takes the
    # most compact correction the measurement cannot tell from the optimum. The 0.04 ms is only
    # "wrong" because the fixture knows its own tau; in the car that difference is noise, and
    # buying it with delay is optimality with no failing case. A test that demands the exact
    # synthetic tau is therefore the wrong test (it was written, failed, and was withdrawn). An EXACT |tau| draw is a real coin flip -- a
    # Butterworth joint offers (+1, -tau) and (-1, +tau) with the same sum and the same
    # null -- so it is settled by a convention rather than by the 1e-15 that separates
    # them: keep the driver non-inverted. Nothing acoustic is lost, and the same set of
    # measurements stops producing a different polarity on different days.
    # |tau| is compared in whole grid steps: `arange` is not bit-symmetric about zero
    # (|-1.320| and |+1.320| can differ by 5e-16), and without quantising, that last bit
    # decides the draw before the convention below ever runs.
    steps = np.rint(np.abs(taus[it]) / (step_ms / 1000.0)).astype(int)
    inverted = np.array([0 if polarities[i] > 0 else 1 for i in ip])
    j = np.lexsort((-energies[ip, it], inverted, steps))[0]
    pol, tau = polarities[ip[j]], taus[it[j]]
    peak = energies.max(axis=1)
    margin_db = (float("inf") if len(polarities) < 2
                 else float(10 * np.log10(peak[ip[j]] / np.delete(peak, ip[j]).max())))
    s = a + pol * b * np.exp(-2j * np.pi * f * tau)
    ceil = np.abs(a) + np.abs(b)
    ok = ceil > 0
    null_db = float(np.min(20 * np.log10(np.abs(s[ok]) / ceil[ok] + 1e-12)))
    return pol, tau * 1000.0, null_db, margin_db


# Jitter set field-validated in the v4.x/vC1 loop: deep interference nulls
# are chaotic — even same-session sweep ratios breathe 4-6 dB RMS (1/12 oct),
# and razor-tuned APF optima did not survive ONE HOUR between snapshots.
# (delay_seconds, level_db) perturbations applied to one branch.
ROBUST_PERT = ((0.0, 0.0), (20e-6, 0.0), (-20e-6, 0.0), (0.0, 0.5),
               (0.0, -0.5), (15e-6, 0.35), (-15e-6, -0.35))


def robust_worst_null(freqs_hz, A, B, band, perturbations=ROBUST_PERT):
    """Worst energy-significant null of A+B over jitter perturbations of B.
    THE objective for joint-phase decisions (diagnostic-techniques §24):
    a solution must hold under small delay/level drift, not win at the
    razor point. Returns the worst null in dB (0 = perfectly coherent)."""
    m = (freqs_hz >= band[0]) & (freqs_hz <= band[1])
    f, a, b = freqs_hz[m], A[m], B[m]
    ceil0 = np.abs(a) + np.abs(b)
    sig = 20 * np.log10(ceil0 + 1e-12) >= np.max(20 * np.log10(ceil0 + 1e-12)) - 20.0
    worst = np.inf
    for tau, lv in perturbations:
        bb = b * np.exp(-2j * np.pi * f * tau) * 10 ** (lv / 20.0)
        c = np.abs(a) + np.abs(bb)
        n = float(np.min(20 * np.log10(np.abs((a + bb)[sig]) / (c[sig] + 1e-12) + 1e-12)))
        worst = min(worst, n)
    return worst


# ---------- sum loss: the junction metric ported from Resonalyze ----------
# upstream: DIMOSUS/Resonalyze dsp/VirtualCrossoverAnalysis.cs @ 5d24924 (MIT) --
# reviewed: 5d24924 (#117, 2026-08-24) adds per-frequency arrival coherence and only CALLS
#           DetailedLoss; the definition, the constants and SumLossCurve are untouched. The
#           port was made at 1da56dd and re-pinned after reading that diff.
# `DetailedLoss`, `SumLossCurve`, `DipExcessPenaltyWeight`, `MinBinAmplitudeRatio`,
# `SumLossLevelGateDb`. A port of the DEFINITION (formula and constants), written
# fresh in numpy; see LICENSES/NOTICE.md. Checked against our own earlier Python
# reading of the same metric (sound_AutoSci resonalyze-cross-check), which agreed
# with the C# to tenths of a dB on six real junctions.
# deviation: d(ln f) per bin instead of their bare 1/f weight -- see `_log_weights`
#            (their 1/f is a log-frequency average only on a uniform-Hz FFT grid).
# deviation: candidates tie-break by our own near-tie rule (smallest |tau| within
#            0.02 dB), not by their AlignmentSelection gates -- see `align_sum_loss`.
# A `# deviation:` line is where a drift checker must look before calling a
# difference from upstream a drift: an unlisted difference is one; a listed one is ours.
#
# Why a second junction metric next to `align_delay_polarity`'s energy maximum:
# the energy of |A+B|^2 is dominated by wherever the pair is LOUD, so a junction
# can score well while a genuine cancellation notch sits inside its band. Sum
# loss measures the gap between the complex sum and the phase-blind magnitude
# sum, bin by bin, in dB (<= 0): 0 dB is perfect in-phase addition everywhere,
# and the number is independent of level and of the drivers' own shape. The
# 1/f weight makes it an average over LOG frequency, so a wide top octave does
# not outvote the narrow bottom one; the dip reads the minimum of a 1/6-octave
# moving mean, so a single-bin modal notch cannot pose as the junction's dip
# while a real cancellation trough still reads at full depth.
SUM_LOSS_MIN_RATIO = 1e-3          # -60 dB floor on |A+B| / (|A|+|B|) per bin
SUM_LOSS_DIP_OCTAVES = 1.0 / 6.0   # width of the moving mean the dip reads
SUM_LOSS_DIP_WEIGHT = 0.5          # score = avg + 0.5 * (dip - avg): the EXCESS over the average
SUM_LOSS_LEVEL_GATE_DB = 25.0      # display/read-out gate: a point > 25 dB under its local peak is NaN
SUM_LOSS_LEVEL_GATE_OCTAVES = 1.0  # ... "local" = within +-1 octave


def _log_weights(freqs_hz):
    """Per-bin weight for a LOG-frequency average, whatever the grid: d(ln f) per bin.

    Resonalyze weights each FFT bin by 1/f -- which IS the log-frequency average, but only on
    its own uniform-Hz grid. On the geometric grids this module works on, a bare 1/f would
    count the bottom twice (the bins are already denser there per Hz) and the metric would
    change with the grid it was evaluated on. d(ln f) = df/f reduces to their 1/f on a linear
    grid and to a constant on a geometric one, so the number is a property of the pair, not of
    the ruler."""
    f = np.asarray(freqs_hz, dtype=float)
    if len(f) < 2:
        return np.ones(len(f))
    return np.gradient(np.log(f))


def sum_loss(freqs_hz, A, B, band, *, level_gate_db=None,
             dip_octaves=SUM_LOSS_DIP_OCTAVES, min_ratio=SUM_LOSS_MIN_RATIO):
    """Junction sum loss of two complex responses over `band`.

    Returns a dict: `avg_db` (the per-bin loss averaged over LOG frequency -- their 1/f
    weight on a linear FFT grid, made grid-independent here, see `_log_weights`), `dip_db` (minimum of the `dip_octaves` moving mean of the per-bin loss) and
    `dip_hz` (where it sits), `score_db` (`avg + 0.5 * (dip - avg)` -- the ranking figure
    Resonalyze's search uses, penalising the notch's EXCESS over the average so a uniformly
    lossy junction is not punished twice), `curve_db` per in-band bin (NaN where gated),
    `freqs_hz` of those bins, and `gated_bins`.

    `level_gate_db=None` is the SEARCH definition (every in-band bin counts, as in their
    `DetailedLoss`). `level_gate_db=25` is the READ-OUT definition (their `SumLossCurve`):
    a bin whose |A|+|B| sits more than 25 dB below the loudest |A|+|B| within +-1 octave is
    NaN and skipped -- there the "loss" is the phase arithmetic of two noise floors. Use the
    gate when reporting a curve, not when comparing candidates: a gate that moves with the
    candidate is a ruler that moves with the part.

    `A` and `B` are complex responses on `freqs_hz`, already carrying whatever delay,
    polarity and chain the caller wants judged. Level does not matter (a ratio); shape does
    not matter (a ratio per bin). Both responses zero at a bin -> that bin is skipped.
    """
    f = np.asarray(freqs_hz, dtype=float)
    A = np.asarray(A, dtype=complex)
    B = np.asarray(B, dtype=complex)
    m = (f >= band[0]) & (f <= band[1])
    f, a, b = f[m], A[m], B[m]
    mag_sum = np.abs(a) + np.abs(b)
    usable = mag_sum > 0
    if level_gate_db is not None:
        # The loudest |A|+|B| within +-gate_octaves of each bin, then the 25 dB floor under it.
        ratio = 2.0 ** SUM_LOSS_LEVEL_GATE_OCTAVES
        local_peak = np.array([mag_sum[(f >= fc / ratio) & (f <= fc * ratio)].max() for fc in f])
        usable &= mag_sum >= local_peak * 10.0 ** (-level_gate_db / 20.0)
    empty = {"avg_db": None, "dip_db": None, "dip_hz": None, "score_db": None,
             "curve_db": np.full(len(f), np.nan), "freqs_hz": f, "n_bins": 0,
             "gated_bins": int((~usable).sum())}
    if not usable.any():
        return empty
    fu, au, bu, su = f[usable], a[usable], b[usable], mag_sum[usable]
    loss = 20.0 * np.log10(np.maximum(np.abs(au + bu) / su, min_ratio))
    w = _log_weights(fu)
    avg = float(np.sum(w * loss) / np.sum(w))
    # Minimum of the moving mean over [fc / 2^(oct/2), fc * 2^(oct/2)]: unweighted, like theirs.
    half = 2.0 ** (dip_octaves / 2.0)
    dip, dip_hz = 0.0, None
    for k, fc in enumerate(fu):
        win = (fu >= fc / half) & (fu <= fc * half)
        v = float(loss[win].mean())
        if v < dip:
            dip, dip_hz = v, float(fc)
    curve = np.full(len(f), np.nan)
    curve[usable] = loss
    return {"avg_db": avg, "dip_db": float(dip), "dip_hz": dip_hz,
            "score_db": sum_loss_score(avg, dip),
            "curve_db": curve, "freqs_hz": f, "n_bins": int(usable.sum()),
            "gated_bins": int((~usable).sum())}


def sum_loss_score(avg_db, dip_db, weight=SUM_LOSS_DIP_WEIGHT):
    """The ranking figure: the average plus `weight` times the dip's EXCESS over it (<= avg).

    Penalising the excess rather than the dip itself leaves a uniformly lossy candidate
    unpunished twice; the average alone cannot tell a smooth -0.7 dB from a -0.7 dB average
    hiding a -5 dB cancellation notch. Higher (closer to 0) is better."""
    return float(avg_db + weight * (dip_db - avg_db))


def align_sum_loss(freqs_hz, A, B, band, max_delay_ms=3.0, step_ms=0.01,
                   polarities=(1, -1), tie_db=0.02):
    """Delay tau (applied to B) and polarity that maximise the sum-loss SCORE in `band`.

    The sum-loss twin of `align_delay_polarity`, returning the same first four values
    `(pol, tau_ms, dip_db, polarity_margin_db)` plus `avg_db` and `score_db` at the optimum,
    so a caller can print both metrics side by side -- the user's ruling (2026-08-24): sum
    loss sits NEXT TO the worst null, neither replaces the other.

    Same tie rule as its twin: among candidates within `tie_db` of the best score, the smallest
    |tau| wins across BOTH polarities, an exact |tau| draw keeps the driver non-inverted, and
    no "prefer non-inverted" margin is imported -- at an odd-order Linkwitz-Riley joint the
    inverted connection is the correct one. `polarity_margin_db` is by how much the chosen
    polarity's best score beats the other polarity's best; negative when the tie rule took the
    marginally weaker but more compact candidate on purpose.
    """
    f = np.asarray(freqs_hz, dtype=float)
    A = np.asarray(A, dtype=complex)
    B = np.asarray(B, dtype=complex)
    m = (f >= band[0]) & (f <= band[1])
    fb, ab, bb = f[m], A[m], B[m]
    taus = np.arange(-max_delay_ms, max_delay_ms + step_ms / 2, step_ms) / 1000.0
    rot = np.exp(-2j * np.pi * np.outer(taus, fb))                    # (n_tau, n_f)
    mag_sum = np.abs(ab) + np.abs(bb)
    usable = mag_sum > 0
    fu = fb[usable]
    w = _log_weights(fu)
    half = 2.0 ** (SUM_LOSS_DIP_OCTAVES / 2.0)
    windows = [(fu >= fc / half) & (fu <= fc * half) for fc in fu]
    scores = np.empty((len(polarities), len(taus)))
    avgs = np.empty_like(scores)
    dips = np.empty_like(scores)
    for ip, pol in enumerate(polarities):
        s = ab[None, :] + pol * bb[None, :] * rot                       # (n_tau, n_f)
        loss = 20.0 * np.log10(np.maximum(np.abs(s[:, usable]) / mag_sum[usable],
                                          SUM_LOSS_MIN_RATIO))
        avg = loss @ w / w.sum()
        # Moving 1/6-oct mean per tau, minimum over centres; 0 is the ceiling (loss <= 0).
        dip = np.zeros(len(taus))
        for win in windows:
            dip = np.minimum(dip, loss[:, win].mean(axis=1))
        avgs[ip], dips[ip] = avg, dip
        scores[ip] = avg + SUM_LOSS_DIP_WEIGHT * (dip - avg)
    # The twin's doctrine, verbatim: among every grid point within the tie of the best score,
    # the most compact correction wins -- a difference the score cannot resolve is not bought
    # with delay. `tie_db` 0.02 dB is the sum-loss reading of the twin's 0.5 % energy.
    ip_, it_ = np.where(scores >= scores.max() - tie_db)
    steps = np.rint(np.abs(taus[it_]) / (step_ms / 1000.0)).astype(int)
    inverted = np.array([0 if polarities[i] > 0 else 1 for i in ip_])
    j = np.lexsort((-scores[ip_, it_], inverted, steps))[0]
    ip, it = ip_[j], it_[j]
    peak = scores.max(axis=1)
    margin = (float("inf") if len(polarities) < 2
              else float(peak[ip] - np.delete(peak, ip).max()))
    return (polarities[ip], float(taus[it] * 1000.0), float(dips[ip, it]), margin,
            float(avgs[ip, it]), float(scores[ip, it]))


def apf_search(freqs_hz, A, B, band, apply_to="hi", n_f0=48,
               q_set=(0.5, 0.7, 1.0, 1.5, 2.0, 3.0, 4.0),
               robust=False, perturbations=ROBUST_PERT):
    """APF2 (f0,q) on one branch maximizing the WORST-case null in band
    (energy-significant bins only) without losing total energy.
    robust=True scores every candidate (and the baseline) by the worst null
    over the jitter perturbations instead of the clean single-point null —
    the field-validated objective (razor optima collapse under cm-scale
    drift; see ROBUST_PERT note). Default False preserves legacy behavior.
    Returns (f0, q, null_gain_db) or (None, None, 0.0) if no improvement."""
    m = (freqs_hz >= band[0]) & (freqs_hz <= band[1])
    f, a, b = freqs_hz[m], A[m], B[m]
    ceil = np.abs(a) + np.abs(b)
    ceil_db = 20 * np.log10(ceil + 1e-12)
    sig = ceil_db >= np.max(ceil_db) - 20.0

    pert = perturbations if robust else ((0.0, 0.0),)
    rots = [(np.exp(-2j * np.pi * f * tau), 10 ** (lv / 20.0)) for tau, lv in pert]

    def score(aa, bb):
        """Worst null over the active perturbation set (jitter on bb)."""
        worst = np.inf
        for rot, g in rots:
            bp = bb * rot * g
            c = np.abs(aa) + np.abs(bp)
            n = float(np.min(20 * np.log10(np.abs((aa + bp)[sig]) / (c[sig] + 1e-12)
                                           + 1e-12)))
            worst = min(worst, n)
        return worst

    base_null = score(a, b)
    base_energy = np.sum(np.abs(a + b) ** 2)
    # keep f0 a quarter-octave inside the band edges: an edge APF "fixing"
    # an edge bin is metric exploitation, not a crossover-region repair
    grid = np.geomspace(band[0] * 1.19, band[1] / 1.19, n_f0)
    best = (base_null, None, None)
    for f0 in grid:
        for q in q_set:
            ap = apf2_response(f, f0, q)
            aa, bb = (a * ap, b) if apply_to == "lo" else (a, b * ap)
            if np.sum(np.abs(aa + bb) ** 2) < 0.98 * base_energy:
                continue  # never trade broadband summation for the notch
            n = score(aa, bb)
            if n > best[0]:
                best = (n, f0, q)
    return best[1], best[2], float(best[0] - base_null)


def greedy_eq_fit(freqs_hz, resid_db, weight, n_bands=4,
                  gain_lo=-12.0, gain_hi=3.0, q_set=(0.7, 1.0, 1.4, 2.0, 3.0, 5.0, 8.0),
                  n_f0=28, band=None, allow_shelf=True, no_boost_zones=(),
                  boost_gate=None):
    """Greedy magnitude-domain EQ fit: minimize weighted RMS of resid_db.
    resid_db = acoustic_db - target_db (positive -> needs cut).
    boost_gate: optional callable (kind, f0, q) -> bool from
    eq_gate.ExcessPhaseGate.as_boost_gate() — measurement-driven veto of PK
    boosts into deep phase-anomalous notches (complements the static zones).
    Returns (bands, resid_after) where bands = [(kind, f0, gain, q), ...]."""
    resid = resid_db.copy()
    w = weight / (np.sum(weight) + 1e-12)
    lo = band[0] if band else freqs_hz[0]
    hi = band[1] if band else freqs_hz[-1]
    f0_grid = np.geomspace(lo, hi, n_f0)
    bands = []

    def wrms(r):
        return float(np.sqrt(np.sum(w * r * r)))

    for _ in range(n_bands):
        base = wrms(resid)
        best = (base, None, None)
        cands = [("PK", f0, q) for f0 in f0_grid for q in q_set]
        if allow_shelf:
            # q=0.71 is display/export metadata: our shelf math is fixed RBJ S=1,
            # which equals a variable-Q shelf at Q=1/sqrt(2) (Helix "LS Q"/"HS Q")
            cands += [("LS", f0, 0.71) for f0 in np.geomspace(lo, min(4 * lo, hi), 8)]
            cands += [("HS", f0, 0.71) for f0 in np.geomspace(max(hi / 4, lo), hi, 8)]
        for kind, f0, q in cands:
            # gain estimate: weighted local residual around f0 (about 2/3 octave)
            sel = (freqs_hz > f0 / 1.3) & (freqs_hz < f0 * 1.3)
            if kind == "LS":
                sel = freqs_hz < f0
            elif kind == "HS":
                sel = freqs_hz > f0
            if not np.any(sel):
                continue
            g0 = -float(np.sum(weight[sel] * resid[sel]) / (np.sum(weight[sel]) + 1e-12))
            for g in {np.clip(round(g0, 1), gain_lo, gain_hi),
                      np.clip(round(0.6 * g0, 1), gain_lo, gain_hi)}:
                if abs(g) < 0.3:
                    continue
                # boosts only in the true passband (weight==1); cuts anywhere
                if g > 0 and float(np.max(weight[sel])) < 0.99:
                    continue
                # known non-minimum-phase dips (interference/SBIR/diffraction):
                # a boost cannot fill them and only burns headroom. Block if f0
                # is inside a zone OR >1/3 of the band's working region overlaps
                # one (otherwise the fit just hugs the zone edge with a wide Q).
                if g > 0 and no_boost_zones:
                    lo_s = f0 / 1.3 if kind != "LS" else freqs_hz[0]
                    hi_s = f0 * 1.3 if kind != "HS" else freqs_hz[-1]
                    span = np.log(hi_s / lo_s)
                    blocked = False
                    for lo_z, hi_z in no_boost_zones:
                        if lo_z <= f0 <= hi_z:
                            blocked = True
                            break
                        ov = np.log(min(hi_s, hi_z) / max(lo_s, lo_z))
                        if ov > 0 and ov / span > 0.33:
                            blocked = True
                            break
                    if blocked:
                        continue
                if g > 0 and boost_gate is not None and not boost_gate(kind, f0, q):
                    continue
                # don't stack boosts within 1/3 octave of an existing boost
                # (a dip that "needs" that is likely cancellation, not EQ-able)
                if g > 0 and any(abs(np.log2(f0 / f2)) < 0.333 and g2 > 0
                                 for _k2, f2, g2, _ in bands):
                    continue
                # total boost budget per driver: headroom + EQ-ability caution
                if g > 0 and sum(max(g2, 0.0) for _, _, g2, _ in bands) + g > 4.5:
                    continue
                mag = 20 * np.log10(np.abs(peq_response(freqs_hz, kind, f0, g, q)) + 1e-12)
                r = wrms(resid + mag)
                if r < best[0]:
                    best = (r, (kind, float(f0), float(g), float(q)), mag)
        if best[1] is None or best[0] > base - max(0.05, 0.03 * base):
            break
        bands.append(best[1])
        resid = resid + best[2]
    return bands, resid


#: The all-pass kinds, spelled as the ledger spells them (`state.EQ_TYPES`).
APF_KINDS = ("APF1", "APF2")


def eq_complex(freqs_hz, bands):
    """Complex response of a whole EQ bank: `[(kind, f0, gain_db, q), ...]` multiplied out.

    Dispatches by kind, and refuses a kind it does not know. Until 2026-08-18 every band went
    through `peq_response`, whose fall-through branch is the high shelf — so a bank carrying an
    `APF1`/`APF2` band (both legitimate ledger types) rendered the all-pass as a shelf, silently.
    Reachable the moment anything hands a ledger's own bands to the simulator (SCR-050 item 5).
    For an all-pass the gain is ignored (it has none) and `q` is read only by the second order.
    """
    freqs_hz = np.asarray(freqs_hz, dtype=float)
    h = np.ones_like(freqs_hz, dtype=complex)
    for kind, f0, g, q in bands:
        if kind == "APF1":
            h = h * apf1_response(freqs_hz, f0)
        elif kind == "APF2":
            h = h * apf2_response(freqs_hz, f0, q)
        elif kind == "PK" or kind in _SHELF_KINDS:
            h = h * peq_response(freqs_hz, kind, f0, g, q)
        else:
            raise ValueError(f"eq_complex: unknown EQ kind {kind!r} in band "
                             f"{(kind, f0, g, q)!r}; known: PK, LS/LSH, HS/HSH, APF1, APF2")
    return h


# ---------- misc ----------

def complex_interp(freqs_target, freqs_src, mag_db, phase_deg=None):
    if phase_deg is not None:
        h = 10 ** (np.asarray(mag_db) / 20.0) * np.exp(1j * np.deg2rad(phase_deg))
    else:
        h = 10 ** (np.asarray(mag_db) / 20.0) + 0j
    re = np.interp(freqs_target, freqs_src, np.real(h))
    im = np.interp(freqs_target, freqs_src, np.imag(h))
    return re + 1j * im


def mag_db(h):
    return 20 * np.log10(np.abs(h) + 1e-12)


def load_ntt_txt(path):
    """NTT/REW txt: comment lines start with #/;/*, then 'freq mag' columns."""
    fr, mg = [], []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line or line[0] in "#;*":
                continue
            parts = line.split()
            if len(parts) >= 2:
                try:
                    fr.append(float(parts[0])); mg.append(float(parts[1]))
                except ValueError:
                    continue
    return np.array(fr), np.array(mg)


# ---------- selftest ----------

def _selftest():
    """The all-pass functions against the physics, and `eq_complex` against its own kinds.

    Every number below is a closed-form fact about the filter, not a value read off a previous
    run: a selftest that agrees with the implementation instead of checking it would have passed
    on the day `eq_complex` rendered an APF as a high shelf.
    """
    # ---- sum loss: anchored to the DEFINITION, never to a stored number ---------------------
    fs_ = np.geomspace(20.0, 20000.0, 3000)
    band = (100.0, 1000.0)
    flat = np.ones(len(fs_), dtype=complex)
    r = sum_loss(fs_, flat, flat, band)
    assert abs(r["avg_db"]) < 1e-9 and r["dip_db"] == 0.0 and r["score_db"] == 0.0, r
    # A ratio: scaling one side by 20 dB changes nothing, and so does scaling both.
    r2 = sum_loss(fs_, flat * 10.0, flat, band)
    assert abs(r2["avg_db"] - r["avg_db"]) < 1e-9 and r2["dip_db"] == r["dip_db"], r2
    # Inverted: every bin at the -60 dB floor (the ratio is exactly 0 before the floor).
    r3 = sum_loss(fs_, flat, -flat, band)
    assert abs(r3["avg_db"] + 60.0) < 1e-6 and abs(r3["dip_db"] + 60.0) < 1e-6, r3
    # A pure delay: the sum cancels where f*tau = 1/2, so the dip must sit at 1/(2 tau) --
    # a fact about waves, and the one place the metric's dip is nailed to a frequency.
    tau = 1.0e-3
    delayed = flat * np.exp(-2j * np.pi * fs_ * tau)
    r4 = sum_loss(fs_, flat, delayed, band)
    assert abs(r4["dip_hz"] - 1.0 / (2 * tau)) / (1.0 / (2 * tau)) < 0.03, r4["dip_hz"]
    assert -60.0 < r4["avg_db"] < 0.0 and r4["dip_db"] < r4["avg_db"], r4
    assert abs(r4["score_db"] - (r4["avg_db"] + 0.5 * (r4["dip_db"] - r4["avg_db"]))) < 1e-12
    # Grid independence: the same pair on a linear grid and on a geometric one must agree --
    # the metric is a property of the pair, not of the ruler it is read with.
    lin = np.arange(100.0, 1000.0 + 0.5, 1.0)
    d_lin = np.exp(-2j * np.pi * lin * tau)
    r4l = sum_loss(lin, np.ones(len(lin), dtype=complex), d_lin, band)
    assert abs(r4l["avg_db"] - r4["avg_db"]) < 0.15, (r4l["avg_db"], r4["avg_db"])
    # A one-bin notch cannot pose as the dip: the 1/6-octave mean dilutes it by the window's
    # bin count, so the dip reads a fraction of the notch and the average barely moves.
    notched = flat.copy()
    k = int(np.argmin(np.abs(fs_ - 300.0)))
    notched[k] = -flat[k] * (1 - 2e-3)          # |A+B|/(|A|+|B|) ~ 1e-3 at one bin: -60 dB
    r5 = sum_loss(fs_, flat, notched, band)
    n_win = int(((fs_ >= 300 / 2 ** (1 / 12)) & (fs_ <= 300 * 2 ** (1 / 12))).sum())
    assert -60.0 / n_win * 1.5 < r5["dip_db"] < -60.0 / n_win * 0.5, (r5["dip_db"], n_win)
    assert r5["avg_db"] > -0.5, r5["avg_db"]
    # The read-out gate: bins 25 dB under their local peak are NaN and do not vote. Build a
    # pair that is flat to 600 Hz and 40 dB down above it, with the loss made bad up there.
    # The quiet stretch (600-1000) sits inside ONE octave of the loud part, so every quiet bin
    # sees a loud neighbour and is gated; a quiet region wider than an octave would NOT be --
    # by design, a tilted response is judged region by region (first draft of this test got
    # exactly that wrong and blamed the code).
    quiet = flat.copy()
    quiet[fs_ > 600.0] *= 1e-2
    bad_hi = quiet.copy()
    bad_hi[fs_ > 600.0] *= -1.0                 # inverted only where it is 40 dB down
    r6 = sum_loss(fs_, quiet, bad_hi, band)                       # search definition: counts
    r7 = sum_loss(fs_, quiet, bad_hi, band, level_gate_db=25.0)   # read-out: gated
    assert r6["avg_db"] < -5.0 and r7["avg_db"] > -1e-6, (r6["avg_db"], r7["avg_db"])
    assert r7["gated_bins"] > 0 and np.isnan(r7["curve_db"]).sum() == r7["gated_bins"], r7["gated_bins"]
    # The search recovers a known delay and polarity from the score, and prints both metrics.
    tau_ms = 0.37
    B_ = -flat * np.exp(-2j * np.pi * fs_ * tau_ms / 1000.0)
    # The metric's optimum sits on the true delay (tie off), and the doctrine's answer sits
    # within the tie plateau of it -- the tie rule takes the most compact correction the score
    # cannot tell from the optimum, which on a flat pair is a few grid steps toward zero.
    pol0, tau0, *_ = align_sum_loss(fs_, flat, B_, band, tie_db=0.0)
    assert pol0 == -1 and abs(tau0 + tau_ms) < 0.011, (pol0, tau0)
    pol, tau_hat, dip_at, margin, avg_at, score_at = align_sum_loss(fs_, flat, B_, band)
    assert pol == -1 and 0.0 <= (tau_ms - abs(tau_hat)) < 0.06, (pol, tau_hat)
    assert avg_at > -0.05 and dip_at > -0.1 and margin > 0, (avg_at, dip_at, margin)
    # ...and agrees with the energy-max twin on a clean case, so the two rulers can be read together.
    pol_e, tau_e, _, _ = align_delay_polarity(fs_, flat, B_, band)
    assert pol_e == pol and abs(tau_e - tau_hat) < 0.06, (pol_e, tau_e, tau_hat)

    f = np.geomspace(2.0, 40000.0, 4000)
    deg = lambda h: np.degrees(np.unwrap(np.angle(h)))  # noqa: E731

    # APF1: unit magnitude, -90 deg exactly at f0, one half turn overall, phase lag only.
    f0 = 100.0
    h1 = apf1_response(f, f0)
    assert np.allclose(np.abs(h1), 1.0, atol=1e-12), "APF1 is not unit magnitude"
    at_f0 = np.degrees(np.angle(apf1_response(np.array([f0]), f0)))[0]
    assert abs(at_f0 + 90.0) < 1e-9, f"APF1 phase at f0 = {at_f0:.4f}, expected -90"
    p1 = deg(h1)
    assert p1[0] > -3.0 and p1[-1] < -177.0, f"APF1 span {p1[0]:.2f} .. {p1[-1]:.2f}, expected 0 .. -180"
    assert np.all(np.diff(p1) < 0), "APF1 phase must fall monotonically with frequency"
    # Far below f0 an APF1 is a pure delay of 1/(pi*f0): 3.18 ms at 100 Hz. That is the whole
    # reason the method aligns a joint with an APF and not with raw delay -- the delay is
    # confined to the band around and below f0 instead of moving the driver's every arrival.
    tau_s = 1.0 / (np.pi * f0)
    low = 2.0
    ph_low = np.degrees(np.angle(apf1_response(np.array([low]), f0)))[0]
    assert abs(ph_low - (-360.0 * low * tau_s)) < 1e-3, (ph_low, -360.0 * low * tau_s)

    # APF2: unit magnitude, -180 deg exactly at f0, one full turn overall, steeper for higher Q.
    for q in (0.5, 0.7, 1.0, 2.0, 4.0):
        h2 = apf2_response(f, f0, q)
        assert np.allclose(np.abs(h2), 1.0, atol=1e-12), f"APF2 q={q} is not unit magnitude"
        at2 = np.degrees(np.angle(apf2_response(np.array([f0]), f0, q)))[0]
        assert abs(abs(at2) - 180.0) < 1e-9, f"APF2 phase at f0 = {at2:.4f}, expected -180"
        p2 = deg(h2)
        # The two ends against the filter's own asymptotes: far below f0 the lag is 2x/q radians
        # (x = f/f0), far above it is a full turn short of 2/(xq). Low Q starts turning earlier --
        # at 2 Hz an APF2(100 Hz, Q 0.5) already lags 4.6 deg -- so a fixed "near zero" would be
        # wrong about the physics, not about the code.
        lo_asym = -np.degrees(2.0 * (f[0] / f0) / q)
        hi_asym = -360.0 + np.degrees(2.0 * (f0 / f[-1]) / q)
        assert abs(p2[0] - lo_asym) < 0.05, (q, p2[0], lo_asym)
        assert abs(p2[-1] - hi_asym) < 0.05, (q, p2[-1], hi_asym)
        assert np.all(np.diff(p2) < 0), f"APF2 q={q} phase must fall monotonically"
    just_above = np.array([f0 * 2 ** (1 / 6)])
    steep = np.degrees(np.unwrap(np.angle(apf2_response(np.array([f0, just_above[0]]), f0, 4.0))))
    gentle = np.degrees(np.unwrap(np.angle(apf2_response(np.array([f0, just_above[0]]), f0, 0.7))))
    assert steep[1] < gentle[1] < -180.0, ("higher Q turns faster near f0", steep, gentle)
    # Two first-order sections at one f0 ARE a second-order all-pass with Q = 0.5. If the two
    # functions did not share a convention this identity would break first.
    assert np.allclose(apf1_response(f, f0) ** 2, apf2_response(f, f0, 0.5), atol=1e-12), \
        "APF1^2 != APF2(Q=0.5): the two all-pass functions disagree about their convention"

    # eq_complex: an all-pass band renders as the all-pass, the ledger's shelf spellings render as
    # the shelves they name, and a kind nobody knows is refused rather than drawn as a shelf.
    assert np.allclose(eq_complex(f, [("APF2", f0, 0.0, 0.7)]), apf2_response(f, f0, 0.7))
    assert np.allclose(eq_complex(f, [("APF1", f0, 0.0, None)]), apf1_response(f, f0))
    ap_only = eq_complex(f, [("APF1", 80.0, 0.0, None), ("APF2", 300.0, 0.0, 1.0)])
    assert np.allclose(np.abs(ap_only), 1.0, atol=1e-12), "a bank of all-passes has unit magnitude"
    ls = peq_response(f, "LS", 200.0, 6.0, 0.71)
    hs = peq_response(f, "HS", 200.0, 6.0, 0.71)
    assert np.allclose(eq_complex(f, [("LSH", 200.0, 6.0, 0.71)]), ls), "LSH is the low shelf"
    assert np.allclose(eq_complex(f, [("HSH", 200.0, 6.0, 0.71)]), hs), "HSH is the high shelf"
    assert not np.allclose(ls, hs), "the two shelves are different filters (sanity)"
    for bad in ("APF3", "XX", "LSX", None):
        try:
            eq_complex(f, [(bad, 100.0, 0.0, 1.0)])
        except ValueError:
            pass
        else:
            raise AssertionError(f"eq_complex accepted unknown kind {bad!r}")
    try:
        peq_response(f, "APF2", 100.0, 0.0, 1.0)
    except ValueError:
        pass
    else:
        raise AssertionError("peq_response rendered an all-pass as a shelf again")
    # ...and the fitter's own vocabulary still works untouched.
    assert np.allclose(eq_complex(f, [("PK", 1000.0, -3.0, 2.0)]),
                       peq_response(f, "PK", 1000.0, -3.0, 2.0))
    # ---- align_delay_polarity: the physics decides the polarity, not a preference ----
    # An Nth-order Linkwitz-Riley joint is two cascaded Butterworth of order N/2, so the
    # branches differ by N/2 * 180 deg at fc: 12 and 36 dB/oct (2nd and 6th order) sum
    # only with one branch INVERTED, 24 dB/oct (4th) sums in phase. Closed-form, not a
    # value read off a run -- and the guard against ever importing a "prefer
    # non-inverted" margin from a tool that aligns raw arrivals instead of two branches
    # of one measurement. At 36 dB/oct the correct inverted answer leads by ~0.17 dB;
    # any such margin above that would silently invert this result.
    fx = np.geomspace(10.0, 24000.0, 20000)
    for fc in (200.0, 3000.0):
        for order, want in ((12, -1), (24, +1), (36, -1)):
            lo = xo_response(fx, fc, order, "lp", "LR")
            hi = xo_response(fx, fc, order, "hp", "LR")
            pol, tau, _null, margin = align_delay_polarity(fx, lo, hi, (fc / 4, fc * 4))
            assert pol == want, f"LR{order} at {fc:g} Hz chose polarity {pol:+d}, expected {want:+d}"
            assert abs(tau) < 0.02, f"LR{order} at {fc:g} Hz wants tau=0, got {tau:+.3f} ms"
            assert margin > 0, f"LR{order} at {fc:g} Hz: chosen polarity should lead, margin {margin:+.3f} dB"

    # An exact |tau| draw is settled by convention, and the convention costs nothing: a
    # Butterworth joint offers (+1, -tau) and (-1, +tau) with the SAME residual null, so
    # the assertion is that the mirror is equally good and that we return the plain one.
    for fc in (80.0, 300.0, 3000.0):
        for order in (6, 18, 30):
            lo = xo_response(fx, fc, order, "lp", "BW")
            hi = xo_response(fx, fc, order, "hp", "BW")
            band = (fc / 4, fc * 4)
            pol, tau, null, _m = align_delay_polarity(fx, lo, hi, band)
            assert pol == +1, f"BW{order} at {fc:g} Hz: an exact draw must stay non-inverted, got {pol:+d}"
            mirror = align_delay_polarity(fx, lo, hi, band, polarities=(-1,))
            # tolerances are the grid's own: half a search step, and a hundredth of a dB
            # -- `arange` is not bit-symmetric about zero, so the mirror lands a few last
            # bits away rather than exactly opposite.
            assert abs(mirror[2] - null) < 0.01, (
                f"BW{order} at {fc:g} Hz: the mirror should be equally good, "
                f"{mirror[2]:.4f} vs {null:.4f} dB")
            assert abs(abs(mirror[1]) - abs(tau)) < 0.005, (fc, order, mirror[1], tau)
            assert mirror[3] == float("inf"), "a single-polarity search has no margin to report"

    # The near-tie rule spans BOTH polarities: whatever comes back must be the smallest
    # |tau| among every candidate within tie_frac of the best sum -- the property that a
    # bare `>` between the two polarities used to break.
    for fc, order, ftype in ((200.0, 42, "BW"), (800.0, 42, "BW"), (3000.0, 24, "LR")):
        lo = xo_response(fx, fc, order, "lp", ftype)
        hi = xo_response(fx, fc, order, "hp", ftype)
        band = (fc / 4, fc * 4)
        pol, tau, _null, _m = align_delay_polarity(fx, lo, hi, band)
        m_ = (fx >= band[0]) & (fx <= band[1])
        ff, aa, bb = fx[m_], lo[m_], hi[m_]
        tg = np.arange(-3.0, 3.0 + 0.005, 0.01) / 1000.0
        rot = np.exp(-2j * np.pi * np.outer(tg, ff))
        en = np.array([np.sum(np.abs(aa[None, :] + q * bb[None, :] * rot) ** 2, axis=1)
                       for q in (1, -1)])
        ip, it = np.where(en >= 0.995 * en.max())
        want_tau = np.abs(tg[it]).min() * 1000.0
        assert abs(abs(tau) - want_tau) < 1e-9, (
            f"{ftype}{order} at {fc:g} Hz returned |tau|={abs(tau):.4f} ms, "
            f"but the near-tie set holds one at {want_tau:.4f} ms")

    # ---- the corner is where we SAY it is -------------------------------------------------
    # Everything above pins the joint's BEHAVIOUR (inversion, near-tie, compactness) and none of
    # it pins the corner to anything outside the module: shift `_design`'s cutoff by 50% and the
    # whole suite still passes, because `xover_select` scores a realization against a target
    # computed by the same broken function -- the ruler and the part are one object, so the fit
    # reads 0.00 dB at the wrong frequency. Found 2026-08-22 by injecting exactly that.
    #
    # The anchor is a definition, not a measurement: LR is BW squared, so it is -6.02 dB at its
    # own corner for EVERY order, while BW is -3.01 there. BE is -3.01 too, and that is not a
    # coincidence to be tolerated but the `norm="mag"` choice in `_design` -- made deliberately
    # because norm="phase" gave up to 27 dB of transfer-function error against REW's own BE
    # shapes (2026-07-12). So this line also stops that choice being reverted silently.
    for fc in (80.0, 500.0, 3000.0):
        at_fc = np.array([fc])
        for order in (12, 24, 36):
            for kind in ("hp", "lp"):
                for ftype, want in (("LR", -6.0206), ("BW", -3.0103), ("BE", -3.0103)):
                    got = 20 * np.log10(abs(xo_response(at_fc, fc, order, kind, ftype)[0]))
                    assert abs(got - want) < 0.05, (
                        f"{ftype}{order} {kind} at its own corner {fc:g} Hz reads {got:+.3f} dB, "
                        f"expected {want:+.3f} -- the corner is not where the caller asked for it "
                        f"(or BE's norm= changed)")

    # ---- and the SLOPE is the one that was asked for ---------------------------------------
    # The corner anchor above pins the family and the frequency but NOT the steepness: a
    # Butterworth is -3.01 dB at its own corner for EVERY order, so if the `n = round(order/6)`
    # mapping ever drifted, all 54 assertions above would stay green while every filter came out
    # the wrong order. Raised by a consumer reading the anchor (TCC, 2026-08-22) -- the right
    # reading of a new test is "what would still pass".
    #
    # Asymptotically a filter falls at its nominal order, so measure an octave of the stopband
    # well away from the corner. Tolerance 1.2 dB/oct: the measured spread is 0.71 at worst (BE
    # approaches its asymptote more slowly than BW), while drifting `n` by ONE step moves the
    # slope by 6 dB/oct -- five times the tolerance.
    # The measured octave must sit at 4x-8x the corner, not 2x-4x: a Bessel reaches its asymptote
    # more slowly than a Butterworth and reads ~7 dB/oct shallow in the nearer octave. And it must
    # stay far from Nyquist, where the bilinear transform warps the response STEEPER -- measuring
    # BW42's lp slope over 8-16 kHz reads 46.7 dB/oct, which is the test being wrong, not the
    # filter. Both edges found by writing the check badly first.
    nyq_safe = FS / 20.0
    for ftype, orders in (("LR", (12, 24, 36)), ("BW", XO_BW_ORDERS), ("BE", XO_BW_ORDERS)):
        for order in orders:
            for fc in (63.0, 500.0, 2000.0):
                bands = [("hp", fc / 8, fc / 4)]
                if fc * 8 <= nyq_safe:
                    bands.append(("lp", fc * 4, fc * 8))
                for kind, f1, f2 in bands:
                    g = lambda x: 20 * np.log10(abs(  # noqa: E731
                        xo_response(np.array([x]), fc, order, kind, ftype)[0]))
                    slope = abs(g(f2) - g(f1))
                    assert abs(slope - order) < 1.2, (
                        f"{ftype}{order} {kind} at {fc:g} Hz falls at {slope:.2f} dB/oct, "
                        f"expected {order} -- the order mapping drifted")

    # ---- and the PHASE at the corner cannot depend on WHERE the corner is ------------------
    # Both anchors above are magnitude-only, and magnitude was the smaller half of the damage: in
    # the broken module the response's PHASE drifted by thousands of degrees in-band while the
    # corner gain looked plausible. This one needs no per-family constant, which the obvious
    # alternatives all do -- BW's corner phase is -45 deg x n, LR's is -90 deg x the HALVED order
    # (its prototype is `max(6, order//2)`), and BE under norm="mag" has no closed form at all,
    # only stored numbers. The property instead: a digital filter's response scales with
    # frequency, so its phase AT its own corner is the same wherever that corner is put.
    #
    # Compared as a ratio, never as a difference of angles: at 24 dB/oct the corner phase is
    # +-180 deg and two identical answers land on opposite sides of the wrap, which a naive
    # max-min reads as 360 deg of drift in a module that is perfectly correct.
    for ftype, orders in (("LR", (12, 24, 36)), ("BW", XO_BW_ORDERS), ("BE", XO_BW_ORDERS)):
        for order in orders:
            for kind in ("hp", "lp"):
                units = [(lambda h: h / abs(h))(
                    xo_response(np.array([fc]), fc, order, kind, ftype)[0])
                    for fc in (40.0, 63.0, 125.0, 500.0, 2500.0)]
                drift = max(abs(np.degrees(np.angle(u / units[0]))) for u in units)
                assert drift < 0.5, (
                    f"{ftype}{order} {kind}: phase at its own corner moves {drift:.2f} deg "
                    f"across corner frequencies -- the response is not scaling with frequency")

    # ---- against an INDEPENDENT reference, not against ourselves ---------------------------
    # The three anchors above are definitions, which is what makes them honest, but they are also
    # all evaluated through the same code path they are checking. This one is not: it designs in
    # ZPK -- poles and zeros, which stay well conditioned where the polynomial form falls apart --
    # and evaluates by multiplying factors directly in the z plane. No polynomial anywhere in the
    # path, which is the whole point: `output="zpk"` buys nothing if the result is handed back to
    # `freqz(b, a)`.
    #
    # It is the strongest of the four. It confirms the SOS rewrite by a third route rather than
    # by SOS agreeing with itself, and it catches the 30 dB/oct orders that both the corner anchor
    # and the phase anchor are blind to (they read 4.5 dB and 0.2 deg of error there while the
    # in-band phase was drifting by tens of degrees). Measured: this module 0.000000 dB / 0.0000
    # deg against the reference; the pre-v3.0.14 form, 77.6 dB and a full half turn.
    sig = _scipy_signal()

    def _reference(freqs, fc, order, kind, ftype):
        btype = "highpass" if kind == "hp" else "lowpass"
        wn = min(max(fc / (FS / 2.0), 1e-4), 0.999)
        zz = np.exp(1j * 2 * np.pi * freqs / FS)

        def one(order_db):
            n = max(1, round(order_db / 6))
            if ftype == "BE":
                z, pl, k = sig.bessel(n, wn, btype=btype, norm="mag", output="zpk")
            else:
                z, pl, k = sig.butter(n, wn, btype=btype, output="zpk")
            return k * (np.prod(zz[:, None] - z, axis=1) / np.prod(zz[:, None] - pl, axis=1))

        if ftype == "LR":
            h = one(max(6, order // 2))
            return h * h
        return one(order)

    fx = np.geomspace(20.0, 20000.0, 800)
    for ftype, orders in (("LR", (12, 24, 36)), ("BW", XO_BW_ORDERS), ("BE", XO_BW_ORDERS)):
        for order in orders:
            for kind in ("hp", "lp"):
                for fc in (40.0, 125.0, 500.0, 2500.0):
                    want = _reference(fx, fc, order, kind, ftype)
                    got = xo_response(fx, fc, order, kind, ftype)
                    # Only where the filter passes something: 100 dB of disagreement deep in a
                    # stopband is arithmetic noise nobody hears or acts on.
                    band = 20 * np.log10(np.abs(want)) > -40.0
                    if not band.any():
                        continue
                    dmag = np.max(np.abs(20 * np.log10(np.abs(got[band]))
                                         - 20 * np.log10(np.abs(want[band]))))
                    dphase = np.max(np.abs(np.degrees(np.angle(got[band] / want[band]))))
                    assert dmag < 0.01 and dphase < 0.1, (
                        f"{ftype}{order} {kind} at {fc:g} Hz differs from a zpk reference by "
                        f"{dmag:.3f} dB / {dphase:.2f} deg -- the evaluation path is losing the "
                        f"answer, as the transfer-function form did before v3.0.14")

    # -- enterable vs modellable (2026-08-23) ---------------------------------
    # A search must offer only what the device accepts AND we can predict. Chebyshev is the live
    # case: the Helix offers it, an experiment could not identify its maths, so proposing one would
    # hand the tuner a filter neither of us can account for.
    helix = {"LR": {"orders_db_per_oct": [12, 24, 36]},
             "BW": {"orders_db_per_oct": [6, 12, 24, 42]},
             "CHEBYSHEV": {"orders_db_per_oct": [6, 12, 24], "ripple_db": None}}
    opts = options_for(helix)
    assert ("CHEBYSHEV", 12) not in opts, "an unmodellable family must never be proposed"
    assert ("LR", 36) in opts and ("BW", 42) in opts, opts
    assert ("LR", 48) not in opts, "a device that does not offer it must not be searched"
    assert ("BE", 12) not in opts, "a family the profile omits is not ours to add"
    # ...and the exclusion is about the UNSTATED PARAMETER, not about the name: the same family
    # with a ripple stated is modellable, so this does not quietly blacklist anything unfamiliar.
    stated = dict(helix, CHEBYSHEV={"orders_db_per_oct": [12], "ripple_db": 1.0})
    assert ("CHEBYSHEV", 12) in options_for(stated, families=("CHEBYSHEV",)), \
        "a determined filter is modellable once its parameters are stated"
    # The default constant stays the reference car's grid and must not silently widen.
    assert ("CHEBYSHEV", 12) not in XO_OPTIONS and ("LR", 48) not in XO_OPTIONS

    print("selftest[dsp_math] OK -- APF1 (-90 deg at f0, 0..-180, 1/(pi f0) delay far below f0), "
          "APF2 (-180 deg at f0, 0..-360, Q steepens), APF1^2 == APF2(Q=0.5), "
          "eq_complex renders APF/LSH/HSH as themselves and refuses an unknown kind, "
          "align_delay_polarity inverts at odd-order LR joints and breaks near-ties "
          "across both polarities by smallest |tau|, and every crossover sits at the corner it "
          "was asked for (LR -6.02 dB, BW/BE -3.01 dB, 54 combinations) and falls at the "
          "order it was asked for (+-1.2 dB/oct over an octave of stopband), and its phase at its own "
          "corner does not depend on where that corner is; and the whole grid matches an "
          "independent zpk reference to 0.000 dB / 0.00 deg.")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] in ("selftest", "--selftest"):
        _selftest()
    else:
        print("usage: python3 dsp_math.py selftest")
