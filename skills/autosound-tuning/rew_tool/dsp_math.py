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
    sig = _scipy_signal()
    n = max(1, round(order_db_per_oct / 6))
    if ftype == "BE":
        # norm="mag" (-3 dB at the corner) matches REW's BE shapes, verified
        # against REW predicted responses 2026-07-12 (norm="phase" gave up to
        # 27 dB transfer-function error on BE12/BE18 channels)
        return sig.bessel(n, wn, btype=btype, norm="mag")
    return sig.butter(n, wn, btype=btype)


def xo_response(freqs_hz, corner_hz, order_db_per_oct, kind, ftype):
    """Complex response of one HPF/LPF slot. kind: 'hp'|'lp'. ftype: 'BW'|'BE'|'LR'."""
    freqz = _scipy_signal().freqz
    wn = min(max(corner_hz / (FS / 2.0), 1e-4), 0.999)
    btype = "highpass" if kind == "hp" else "lowpass"
    w = 2 * np.pi * freqs_hz / FS
    if ftype == "LR":
        b, a = _design(max(6, order_db_per_oct // 2), wn, btype, "BW")
        _, h = freqz(b, a, worN=w)
        return h * h
    b, a = _design(order_db_per_oct, wn, btype, ftype)
    _, h = freqz(b, a, worN=w)
    return h


# hardware grid (helix-dsp-ultra-s.yaml), CHEBYSHEV excluded: ripple unconfirmed
XO_OPTIONS = (
    [("LR", o) for o in (12, 24, 36)]
    + [("BW", o) for o in (6, 12, 18, 24, 30, 36, 42)]
    + [("BE", o) for o in (6, 12, 18, 24, 30, 36, 42)]
)


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
    # Smallest |tau| among the near-ties. An EXACT |tau| draw is a real coin flip -- a
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

    print("selftest[dsp_math] OK -- APF1 (-90 deg at f0, 0..-180, 1/(pi f0) delay far below f0), "
          "APF2 (-180 deg at f0, 0..-360, Q steepens), APF1^2 == APF2(Q=0.5), "
          "eq_complex renders APF/LSH/HSH as themselves and refuses an unknown kind, "
          "align_delay_polarity inverts at odd-order LR joints and breaks near-ties "
          "across both polarities by smallest |tau|.")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] in ("selftest", "--selftest"):
        _selftest()
    else:
        print("usage: python3 dsp_math.py selftest")
