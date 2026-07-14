"""Vectorized DSP building blocks for the v3 acoustic-target pipeline.
All responses are complex numpy arrays over an arbitrary frequency vector,
digital-domain at FS=96000 (matches Helix DSP Ultra S).
"""
import numpy as np
from scipy.signal import bessel, butter, freqz

FS = 96000.0


# ---------- crossover filters (same conventions as v2, minus Chebyshev) ----------

def _design(order_db_per_oct, wn, btype, ftype):
    n = max(1, round(order_db_per_oct / 6))
    if ftype == "BE":
        # norm="mag" (-3 dB at the corner) matches REW's BE shapes, verified
        # against REW predicted responses 2026-07-12 (norm="phase" gave up to
        # 27 dB transfer-function error on BE12/BE18 channels)
        return bessel(n, wn, btype=btype, norm="mag")
    return butter(n, wn, btype=btype)


def xo_response(freqs_hz, corner_hz, order_db_per_oct, kind, ftype):
    """Complex response of one HPF/LPF slot. kind: 'hp'|'lp'. ftype: 'BW'|'BE'|'LR'."""
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


def peq_response(freqs_hz, kind, f0, gain_db, q):
    """kind: 'PK' | 'LS' | 'HS'. Complex response."""
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
        if kind == "LS":
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


def apf2_response(freqs_hz, f0, q):
    """2nd-order allpass (APF2 in the Helix PEQ bank): unit magnitude, phase only."""
    x = freqs_hz / f0
    phase = -2.0 * np.arctan2(x / q, 1.0 - x * x)
    return np.exp(1j * phase)


# ---------- deterministic inner solvers ----------

def align_delay_polarity(freqs_hz, A, B, band, max_delay_ms=3.0, step_ms=0.01,
                         polarities=(1, -1)):
    """Delay tau (applied to B) and polarity maximizing sum energy in band.
    Vectorized over the full tau grid. Returns (pol, tau_ms, residual_null_db)."""
    m = (freqs_hz >= band[0]) & (freqs_hz <= band[1])
    f, a, b = freqs_hz[m], A[m], B[m]
    taus = np.arange(-max_delay_ms, max_delay_ms + step_ms / 2, step_ms) / 1000.0
    rot = np.exp(-2j * np.pi * np.outer(taus, f))          # (n_tau, n_f)
    best = None
    for pol in polarities:
        s = a[None, :] + pol * b[None, :] * rot
        e = np.sum(np.abs(s) ** 2, axis=1)
        # among near-ties (within 0.5% of max) prefer the smallest |tau|:
        # same summation with a more compact impulse
        near = np.where(e >= 0.995 * np.max(e))[0]
        k = near[np.argmin(np.abs(taus[near]))]
        if best is None or e[k] > best[0]:
            best = (e[k], pol, taus[k])
    _, pol, tau = best
    s = a + pol * b * np.exp(-2j * np.pi * f * tau)
    ceil = np.abs(a) + np.abs(b)
    ok = ceil > 0
    null_db = float(np.min(20 * np.log10(np.abs(s[ok]) / ceil[ok] + 1e-12)))
    return pol, tau * 1000.0, null_db


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


def eq_complex(freqs_hz, bands):
    h = np.ones_like(freqs_hz, dtype=complex)
    for kind, f0, g, q in bands:
        h *= peq_response(freqs_hz, kind, f0, g, q)
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
