"""Excess-phase EQ-boost-ability gate (canonical module).

Decides whether an EQ BOOST candidate targets a minimum-phase deficit
(fillable) or a non-minimum-phase notch (interference/SBIR/diffraction —
boost forbidden), from the measurement itself. Replaces / augments the
hand-maintained NO_BOOST_ZONES car-record lists.

The rule = the skill's peak-vs-null doctrine (diagnostic-techniques §2) made
quantitative. A boost is dangerous only where ALL THREE hold at once:
  dip(f)  >= DIP_DB — a deep LOCAL magnitude dip (±2/3-oct rolling median);
  S(f)    >= Z_WARN — phase-anomalous: S = sliding RMS (1/6 oct) of the
                      excess-group-delay z-score vs a ±1-oct rolling baseline
                      (bipolar S-swings zero-cross at the notch center, so
                      point |z| misses them; S integrates both lobes);
  w(f)    >= 0.5    — the filter actually delivers gain there (normalized
                      dB profile; skirt clips are free).
Cabin mids are phase-rough EVERYWHERE (30-50 % of band shows S>=4.5), so
phase alone over-blocks; depth alone can't tell cancellation from a fillable
shape deficit. The conjunction reproduced 7/7 of the VW-B8 build's real
boost history (3 known violations -> WARN/BLOCK, 4 boosts that worked ->
ALLOW); see excess_gate.py for the research/validation harness.

Verdicts: ALLOW < Z_WARN <= WARN (needs a mic-shift cross-check, diagnostic
§13) < Z_BLOCK <= BLOCK. Scope: phase-based only — taste zones (de-esser
5-6k etc.) stay manual in the car record. Calibration is PROVISIONAL:
validated on one build (2026-07-13).

Excess phase source: REW's native "Excess phase version" (`rew_api.
excess_phase_version`) — the authoritative path, not a home-brew Hilbert.

Usage:
    gate = ExcessPhaseGate(freqs, mag_db, excess_phase_deg, trust=(150, 4000))
    verdict, metric, at = gate.check(f0=662, q=5.0)
    realize_driver(..., boost_gate=gate.as_boost_gate())

Selftest: `python3 eq_gate.py --selftest` — two synthetic reflection combs
with near-identical magnitude (r=0.95 minimum-phase vs r=1.05 non-minimum-
phase): depth can't tell them apart, the gate must.
"""
import sys

import numpy as np

PPO = 96
SMOOTH_FRAC = 6            # 1/6-oct FWHM for excess-phase smoothing
BASE_HALF_OCT = 1.0        # rolling-median baseline half-window (octaves)
Z_WARN, Z_BLOCK = 4.5, 6.0
DIP_DB = 4.0
MAD_FLOOR_S = 1e-6         # numerical floor for the z normalization


def gauss_smooth(y, sigma_pts):
    n = int(max(3, round(sigma_pts * 8)) | 1)
    k = np.exp(-0.5 * ((np.arange(n) - n // 2) / sigma_pts) ** 2)
    k /= k.sum()
    return np.convolve(np.pad(y, n // 2, mode="edge"), k, mode="valid")


def analyze(freqs, mag_db, excess_phase_deg, trust):
    """Excess-GD anomaly fields on a log grid. Returns dict of arrays:
    g, tau (excess GD, s), z (deviation score), s (sliding-RMS of z),
    dip (local dip depth, dB), trust_mask."""
    g = np.geomspace(max(20, trust[0] * 0.5), min(20000, trust[1] * 2),
                     int(np.log2(20000 / 20) * PPO))
    e = np.exp(1j * np.deg2rad(np.interp(g, freqs, excess_phase_deg)))
    sig = PPO / SMOOTH_FRAC / 2.355
    es = gauss_smooth(e.real, sig) + 1j * gauss_smooth(e.imag, sig)
    phi = np.unwrap(np.angle(es))
    tau = -np.gradient(phi, g) / (2 * np.pi)
    half = int(BASE_HALF_OCT * PPO)
    base = np.array([np.median(tau[max(0, i - half):i + half + 1])
                     for i in range(len(tau))])
    dev = tau - base
    m = (g >= trust[0]) & (g <= trust[1])
    mad = max(float(np.median(np.abs(dev[m] - np.median(dev[m])))), MAD_FLOOR_S)
    z = dev / mad
    s = np.sqrt(gauss_smooth(z ** 2, PPO / SMOOTH_FRAC / 2.355))
    mag = np.interp(g, freqs, mag_db)
    hw = int(2 * PPO / 3)
    mag_base = np.array([np.median(mag[max(0, i - hw):i + hw + 1])
                         for i in range(len(mag))])
    return {"g": g, "tau": tau, "dev": dev, "cycles": dev * g, "z": z, "s": s,
            "dip": mag_base - mag, "mag": mag, "trust_mask": m}


class ExcessPhaseGate:
    def __init__(self, freqs, mag_db, excess_phase_deg, trust,
                 z_warn=Z_WARN, z_block=Z_BLOCK, dip_db=DIP_DB):
        self.r = analyze(freqs, mag_db, excess_phase_deg, trust)
        self.z_warn, self.z_block, self.dip_db = z_warn, z_block, dip_db

    def check(self, f0, q):
        """-> (verdict, metric, at_freq|None) for a PK boost at (f0, q)."""
        from dsp_math import peq_response
        r = self.r
        w = np.abs(20 * np.log10(np.abs(peq_response(r["g"], "PK", f0, 3.0, q))
                                 + 1e-12))
        w = w / max(w.max(), 1e-12)
        hot = (r["s"] >= self.z_warn) & (r["dip"] >= self.dip_db) & (w >= 0.5)
        if not hot.any():
            return "ALLOW", float(np.max(r["s"] * w)), None
        metric = float(r["s"][hot].max())
        i = int(np.argmax(np.where(hot, r["s"], -np.inf)))
        verdict = "BLOCK" if metric >= self.z_block else "WARN"
        return verdict, metric, float(r["g"][i])

    def as_boost_gate(self, block_on_warn=True):
        """Callable for dsp_math.greedy_eq_fit(boost_gate=...): PK boosts only
        (shelves keep the static-zone/budget rules); True = allowed."""
        bad = {"BLOCK", "WARN"} if block_on_warn else {"BLOCK"}

        def fn(kind, f0, q):
            if kind != "PK":
                return True
            return self.check(f0, q)[0] not in bad
        return fn


def _selftest():
    from scipy.signal import hilbert

    n = 2 ** 14
    f = np.linspace(1.0, 8000.0, n)
    tau = 1.5e-3
    rng = np.random.default_rng(7)

    def comb_case(r_coef):
        H = 1.0 + r_coef * np.exp(-2j * np.pi * f * tau)
        mag = np.abs(H)
        # excess phase = total - minimum phase (Hilbert of log-magnitude)
        logm = np.log(mag + 1e-9)
        pad = n // 4
        ext = np.pad(logm, pad, mode="reflect")
        mp = -np.imag(hilbert(ext))[pad:-pad]
        ep = np.rad2deg(np.unwrap(np.angle(H)) - mp)
        # small measurement-like GD noise so MAD is realistic, not ~0
        ep += np.cumsum(rng.normal(0, 0.02, n))
        return ExcessPhaseGate(f, 20 * np.log10(mag + 1e-9), ep,
                               trust=(200, 6000))

    notch = 1.0 / (2 * tau)  # first comb notch, 333.3 Hz -> use the 3rd @ 1667
    f0 = 5 * notch
    g_min = comb_case(0.95)   # |r|<1: minimum-phase comb -> EQ-able in theory
    g_non = comb_case(1.05)   # |r|>1: RHP zeros -> non-minimum-phase comb
    v_min, m_min, _ = g_min.check(f0, 5.0)
    v_non, m_non, at = g_non.check(f0, 5.0)
    assert v_min == "ALLOW", f"min-phase comb blocked: {v_min} ({m_min:.1f})"
    assert v_non in ("WARN", "BLOCK"), f"non-min-phase comb passed: {v_non}"
    # exactly between two notches (1667 and 2333), narrow enough to miss both
    ok_flat, _, _ = g_non.check(6 * notch, 8.0)
    assert ok_flat == "ALLOW", f"flat region blocked: {ok_flat}"
    assert g_non.as_boost_gate()("PK", f0, 5.0) is False
    assert g_non.as_boost_gate()("LS", f0, 0.71) is True
    print(f"selftest OK -- min-phase comb r=0.95: {v_min} (S*w {m_min:.1f}); "
          f"non-min-phase r=1.05: {v_non} (S {m_non:.1f} @ {at:.0f} Hz); "
          f"between-notch ALLOW; shelf pass-through")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
