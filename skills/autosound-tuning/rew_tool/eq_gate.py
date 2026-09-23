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
5-6k etc.) stay manual in the car record.

Validation status (2026-07-23, first formal experiment suite — see the
research project `sound_AutoSci`, idea `excess-phase-extraction`, 5 blocks,
cross-model verified Claude+Gemini, verdict partially_supported):
  - STRONG as a BLOCK detector. On an analytic ground-truth family (minimum-
    vs non-minimum-phase combs at MATCHED magnitude, where any depth-only
    rule is at chance) this gate scores 90/90 at the z_warn=5.0 operating
    point. It never confidently BLOCKs a minimum-phase dip at any depth (a
    min-phase system has ~zero excess phase, so S stays near the noise floor);
    at the more conservative default z_warn=4.5, deep min-phase dips tip to
    WARN (→ mic-shift check) rather than ALLOW — an abstention, not a false
    block. On the VW-B8 build's real BLOCK anchors it catches 20/25 on its own.
  - NOT a certifier. ALLOW / absence-of-BLOCK means "no phase objection",
    never "safe to boost". The permissive side's real evidence is thin
    (n=4, one session). Treat ALLOW as counsel, keep the human in the loop.
  - The 5 real BLOCK anchors it misses on its own are shallow dips where
    single-point in-cabin excess phase is drift-floor-unstable (breathes by
    orders of magnitude take-to-take). Catching those needs a SPATIAL check
    (does the dip survive a same-session MMM) — a future enhancement, not a
    fix; it requires an MMM solo per channel captured in the SAME session as
    the sweep. Until then, WARN→mic-shift (§13) is the safety net for these.
  - Calibration remains PROVISIONAL / install-specific: the METHOD is general
    but Z_WARN/Z_BLOCK/DIP_DB and per-driver trust bands are tuned on one
    vehicle. Pending a second install (out-of-sample), prefer advising over
    hard-vetoing — see `as_boost_gate` note.

⚠️ Do NOT add a depth-based null-guard that abstains on deep dips regardless
of S. An experiment did exactly that and it demoted 90/90 to 54/90 by
overriding correct confident ALLOWs on deep MINIMUM-phase notches (their S
sits at the noise floor, as theory requires). If a guard is ever wanted,
condition it on S (abstain only when S is ALSO near threshold), never on
depth alone. The `--selftest` locks in the deep-min-phase-ALLOW case.

Excess phase source: REW's native "Excess phase version" (`rew_api.
excess_phase_version`) — the authoritative path, not a home-brew Hilbert.

Usage:
    gate = ExcessPhaseGate(freqs, mag_db, excess_phase_deg, trust=(150, 4000))
    verdict, metric, at = gate.check(f0=662, q=5.0)
    realize_driver(..., boost_gate=gate.as_boost_gate())

The question BEFORE the gate's -- "is the excess phase at this feature only the
delay?" -- is `min_phase_verdict(freqs, excess_phase_deg, f0)`: the bulk delay
taken out over a stated window, the residual judged against a stated
threshold, both named in the result (#56 item 3). Read the excess phase raw and
the delay's ramp reads as "not minimum-phase" at every frequency.

Selftest: `python3 eq_gate.py --selftest` — two synthetic reflection combs
with near-identical magnitude (r=0.95 minimum-phase vs r=1.05 non-minimum-
phase): depth can't tell them apart, the gate must. The verdict's own cases
(numpy only) run first, scipy or not.
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
        # KEPT, and not decoration: `analyze`'s grid deliberately runs half an octave BELOW
        # trust[0] and an octave above trust[1] (smoothing needs the margin), while the MAD
        # normaliser is computed on the trust band ALONE. So a query outside the band divides
        # by a scale that was never calibrated for it and comes back looking like any other
        # confident verdict. Field cost, 2026-08-21: three of five BLOCKs on this car were
        # out-of-band; re-run inside the band, two of them fell from S=4.2/4.7 to 1.3/1.2.
        self.trust = (float(trust[0]), float(trust[1]))
        self.z_warn, self.z_block, self.dip_db = z_warn, z_block, dip_db

    def in_scope(self, f0):
        """Is f0 inside the CALIBRATED band? Outside it this gate has no vote --
        neither a permission nor an objection."""
        return self.trust[0] <= float(f0) <= self.trust[1]

    def s_at(self, f0):
        """The phase-anomaly statistic S at f0 — the ALWAYS-comparable value.

        Use this, not `check()`'s `metric`, for any cross-case comparison or
        aggregation. `metric` is fine here (both branches return an S-family
        value), but a subclass that adds branches returning a different
        quantity (e.g. a dB dip depth) would make `metric` non-comparable and
        silently corrupt any aggregate — that exact trap produced a false
        "criterion inverts on deep dips" finding in the 2026-07-23 research
        suite. `s_at()` is immune to it.
        """
        i0 = int(np.argmin(np.abs(self.r["g"] - f0)))
        return float(self.r["s"][i0])

    def check(self, f0, q):
        """-> (verdict, metric, at_freq|None) for a PK boost at (f0, q).

        `verdict` is ALLOW / WARN / BLOCK / **OUT_OF_SCOPE**. The last one is not a
        weak ALLOW: it means the question was asked outside the band this gate was
        calibrated on, so it has no vote at all and whatever governs there (the flaw
        map\'s `no_boost` zones, §13\'s mic-shift) governs alone. Record it by that
        NAME, never as ALLOW -- "ALLOW 1.2 @ 145 Hz" reads as permission a month
        later, and on this car 145 Hz is a cabin null the map says never to boost.

        `metric` is the S statistic on the hot path and S*w on ALLOW — both
        S-family, so it is comparable AS LONG AS this class is not subclassed
        with branches returning a different quantity. For safety in any
        cross-case analysis use `s_at(f0)` instead (see its docstring).
        """
        if not self.in_scope(f0):
            return "OUT_OF_SCOPE", None, None
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
        # OUT_OF_SCOPE is deliberately NOT in `bad`: a gate with no vote must not veto.
        # Out there the boost is governed by the flaw map, not by silence from this object.
        bad = {"BLOCK", "WARN"} if block_on_warn else {"BLOCK"}

        def fn(kind, f0, q):
            if kind != "PK":
                return True
            return self.check(f0, q)[0] not in bad
        return fn


# ── Is the excess phase at a feature ONLY a delay? (#56 item 3) ──────────────
# The criterion is sourced; its numbers come from the measurement (docs/RESEARCH-2026-09-23-min-phase-verdict.md,
# the Arbiter 2026-09-23: "the skill exists to find these answers"). Sourced: a region is minimum-phase where the excess
# group delay is FLAT once the delay is removed (REW help, Minimum Phase; Neely & Allen, JASA 1979); at one point that is
# decisive only below the cabin's Schroeder frequency, and above it what a filter can hold is decided by stability across
# positions (Toole, JAES 2015; Radlovic et al., IEEE TSAP 2000; Mulcahy). No source publishes a threshold in degrees or
# milliseconds, so none is invented here: the threshold is the measurement's own repeat floor.
#
# The window: the feature's own, +-1/6 oct (1/3 oct wide -- the scale the method reads features on, `eq_propose`'s
# RES_WIDTH, and matches them across positions by). +-0.5 oct charged a minimum-phase peak with a non-minimum-phase notch
# 0.4 oct away (52 degrees rms where +-1/6 reads 0.6), and the Passat's w-L modal peak and door null sit 0.3-0.7 oct apart.
MIN_PHASE_HALF_OCT = 1.0 / 6.0
# A floor UNDER the floor, not a physical constant: below it, grid and unwrap artefacts on a 96-ppo read cannot be told
# from signal (r = 1.01 reads 5 degrees rms, see below). The working threshold is max(this, 3 x the repeat floor).
MIN_PHASE_RESID_DEG = 10.0
# ...and the rms alone is blind to the reflection that is only JUST louder than the direct sound. At r = 1.01 its -360
# degree step is ~2 Hz wide, narrower than the grid, so nearly all of it falls between two points and unwraps to
# nothing. What survives is the one or two points ON the step, 34-44 degrees. So the largest point is held to 3x the rms
# threshold: where Gaussian noise that passes the rms test reaches on ~100 points; a spike past it is not noise of that kind.
MIN_PHASE_MAX_RATIO = 3.0
MIN_PHASE_MAX_DEG = MIN_PHASE_RESID_DEG * MIN_PHASE_MAX_RATIO
# Below this a single point is stable, and a single-point verdict is THE evidence; above it the verdict corroborates
# and the ellipsoid decides whether the feature stays (a car's Schroeder frequency is ~150-200 Hz, DAGA 2010;
# `eq_propose.SCHROEDER_HZ`, the same number).
MIN_PHASE_SCHROEDER_HZ = 200.0
# The only reads a phase verdict is taken on: REW smooths phase with magnitude, and 1/24 already erased a real
# non-minimum-phase step (r = 1.05 read MIN_PHASE at 1/24, 1/12 and 1/6).
MIN_PHASE_READS = (None, "None", "none", "1/48")
# Fewer points than this in the window and a straight line through them says nothing.
MIN_PHASE_MIN_POINTS = 8
# The largest bulk delay the coarse search looks for. REW references a sweep's phase to its own
# time zero, and with a loopback reference that carries the whole arrival: a live capture's notes
# read `DELAY 22.6504 ms` (`rew_api.measurement_kind`). 100 ms is well clear of any car.
MAX_BULK_DELAY_S = 0.1
# How close to the window's edges the data must reach. A grid point is never exactly ON f0*2**0.5,
# so "covers the window" means "within 2 % (1/35 oct) of each edge", not "to the last hertz".
_EDGE_TOL = 1.02


def _coarse_delay(f, ph_rad, max_delay_s=MAX_BULK_DELAY_S):
    """The bulk delay, found WITHOUT unwrapping, so that unwrapping afterwards is safe.

    `np.unwrap` on a steep delay ramp aliases as soon as the ramp per grid step nears 180 degrees,
    and it does so silently -- it hands back a smooth-looking curve with the wrong slope, and the
    line through it leaves a residual that reads "not minimum-phase". On REW's 96-ppo grid a
    7.3 ms delay (#56) gets there above ~9.5 kHz, a 22.65 ms loopback-referenced one above
    ~3 kHz. So the delay is first found as the one that makes the phasors in the window most
    coherent -- |sum exp(j*(phase + 2*pi*f*tau))| is largest at the true tau whatever the grid --
    and only the small remainder is left to `np.unwrap` and the line.

    A grid fine enough to unwrap any delay up to twice `max_delay_s` (REW's linear read, an FFT
    of an impulse) skips the search: there it would cost the most and buy nothing.
    """
    steps = np.diff(f)
    if steps.size == 0 or float(steps.max()) <= 1.0 / (4.0 * max_delay_s):
        return 0.0
    span = float(f[-1] - f[0])
    dt = 1.0 / (8.0 * span)                 # the coherence peak is ~1/span wide: 8 steps across it
    taus = np.arange(-max_delay_s, max_delay_s + dt, dt)
    z = np.exp(1j * ph_rad)
    best, best_tau = -1.0, 0.0
    for i in range(0, taus.size, 256):      # in blocks: dense grid x long search is not one matrix
        t = taus[i:i + 256]
        coh = np.abs(np.exp(2j * np.pi * np.outer(t, f)) @ z)
        k = int(np.argmax(coh))
        if coh[k] > best:
            best, best_tau = float(coh[k]), float(t[k])
    return best_tau


def channel_delay_ms(freqs, phase_deg, band):
    """One bulk delay for a channel, from its excess phase over the band it plays: the coherence search, then a line.

    A verdict fitted with a free line in every window absorbs a LOCAL group-delay offset as "delay" -- which is exactly
    REW's "not flat". One propagation path has one delay, so it is found once and held fixed (#56: 7.3 ms on all four)."""
    f = np.asarray(freqs, dtype=float)
    p = np.deg2rad(np.asarray(phase_deg, dtype=float))
    m = np.isfinite(f) & np.isfinite(p) & (f >= band[0]) & (f <= band[1])
    fw, ph = f[m], p[m]
    if fw.size < MIN_PHASE_MIN_POINTS:
        raise ValueError(f"{fw.size} points in {band[0]:g}-{band[1]:g} Hz: too few to find a delay")
    tau0 = _coarse_delay(fw, ph)
    rot = np.unwrap(ph + 2 * np.pi * fw * tau0)
    b = np.polyfit(fw - fw.mean(), rot, 1)[0]
    return float((tau0 - b / (2 * np.pi)) * 1e3)


def min_phase_verdict(freqs, phase_deg, f0, half_oct=MIN_PHASE_HALF_OCT,
                      threshold_deg=MIN_PHASE_RESID_DEG, max_deg=None, floor_deg=None, delay_ms=None,
                      smoothing=None):
    """Is the excess phase around `f0` a delay and nothing else? -> a verdict that NAMES its window.

    Why this exists (#56 item 3): a session read REW's excess phase at a candidate frequency, found
    -122 degrees mean, and concluded "not minimum-phase, do not EQ". That was wrong. A delay is an
    all-pass, so REW's split (measured minus minimum phase) puts ALL of the bulk propagation delay
    on the excess side, where it is a ramp linear in frequency, -360*f*tau degrees -- and at any
    one frequency that ramp reads as a large number. A minimum-phase feature under it has no excess
    phase of its own. The question is what is LEFT once the ramp is gone: detrended over +-0.5 oct,
    the same four features read 1.2 / 0.0 / 0.4 / 2.3 degrees -- all minimum-phase -- with a
    consistent 7.3 ms removed. One function, because a number justified only by how somebody
    computed it that day gets computed differently the next (the `dsp_math._design` note).

    The method (docs/RESEARCH-2026-09-23-min-phase-verdict.md): take the points in f0 * 2**(+-half_oct)
    (+-1/6 oct, the feature's own); take out the delay -- the CHANNEL's, `delay_ms` from `channel_delay_ms`,
    held fixed, and then only the mean; without it, a line fitted in the window, and the result says so --
    (`_coarse_delay` first, so wrapped input is fine: REW serves +-180), on LINEAR frequency, because a delay
    is linear in f. What is left is the residual. MIN_PHASE needs its rms within the threshold AND its
    largest point within 3x that: the rms catches a residual spread over the window, the max one
    concentrated on a step.

    The threshold is the measurement's own: max(`threshold_deg`, 3 x `floor_deg`), where `floor_deg` is the
    repeat floor of the same read at one position (`min_phase_across` measures it from the centre returns).
    No source publishes a number; 10 degrees stays only as the floor under it. Without a floor the verdict is
    PROVISIONAL, and says so.

    Reading it:
      * `MIN_PHASE` -- inside this window the excess phase is a delay; the feature's phase is its
        magnitude's own, and EQ can undo it AT THIS POINT. Below Schroeder (`scope` "decisive") that is
        the evidence; above it (`scope` "corroborating") whether it holds at the head is the
        ellipsoid's question. It is not a boost licence: whether a boost may go HERE is
        `ExcessPhaseGate.check`'s question (dip, anomaly and delivered gain at once), and a dip
        still needs its mic-shift (diagnostic §13).
      * `NON_MIN_PHASE` -- something in the window is not a delay: a reflection louder than its
        direct sound, a cancellation. EQ cannot undo it. The verdict is the WINDOW's, so a
        non-minimum-phase neighbour inside it counts; `residual_at_f0_deg` says where it sits and
        `why` which test failed.
      * `delay_ms` should AGREE between the features of one channel -- it is one propagation path
        (7.3 ms on all four in #56). A feature whose delay stands apart has had something broad
        and all-pass bent into the line; compare them, never average them.
      * `OUT_OF_SCOPE` -- the data does not reach both edges of the window, or holds fewer than
        MIN_PHASE_MIN_POINTS inside it. The numbers are None, not a guess over a shorter window
        that would be quoted as this one (`references/core/estimator-scope.md` §1). Narrow
        `half_oct` and say so, or read wider data.

    The grid bounds what it can see. A step narrower than the grid spacing can fall wholly between
    two points and leave nothing: on REW's 96-ppo grid a reflection within ~0.5 % of its direct
    sound reads 2-3 degrees rms and 18-26 max, a pass. A linear grid a fraction of a hertz apart
    resolves it -- REW's `smoothing="None"` read; r = 1.01 on a 0.73 Hz grid reads 94 degrees rms
    -- so a deep, narrow dip is judged on that read, not on the log one.

    Returns a dict: `verdict`, `min_phase` (True / False / None), `delay_ms`,
    `residual_rms_deg`, `residual_max_deg`, `residual_at_f0_deg`, `threshold_deg`,
    `max_threshold_deg`, `judged_on`, `window` (e.g. "+-0.5 oct, 707-1414 Hz"), `window_hz`,
    `half_oct`, `n_points`, `why`, and `line` -- one sentence carrying the verdict WITH its window
    and thresholds, so the number cannot be quoted without them.

    Raises ValueError when there is no phase at all: an RTA carries none (`rew_api.get_fr` returns
    None for it) -- read the excess phase of a SWEEP, REW's `-EP` (`rew_api.excess_phase_version`).
    """
    if phase_deg is None:
        raise ValueError("no phase to judge: an RTA carries none -- read the excess phase of a "
                         "sweep (REW's -EP version, rew_api.excess_phase_version)")
    if smoothing not in MIN_PHASE_READS:
        raise ValueError(f"the -EP was read at {smoothing} smoothing: REW smooths phase with magnitude, and 1/24 "
                         "already erases a non-minimum-phase step -- read it at None or 1/48")
    f = np.asarray(freqs, dtype=float)
    p = np.asarray(phase_deg, dtype=float)
    if f.shape != p.shape:
        raise ValueError(f"freqs and phase differ in length ({f.size} vs {p.size})")
    keep = np.isfinite(f) & np.isfinite(p) & (f > 0)
    order = np.argsort(f[keep])
    f, p = f[keep][order], p[keep][order]
    f0 = float(f0)
    lo, hi = f0 * 2.0 ** -half_oct, f0 * 2.0 ** half_oct
    window = f"±{_oct_name(half_oct)} oct, {lo:.0f}–{hi:.0f} Hz"
    rms_limit = max(float(threshold_deg), 3.0 * float(floor_deg)) if floor_deg is not None else float(threshold_deg)
    max_limit = float(max_deg) if max_deg is not None else MIN_PHASE_MAX_RATIO * rms_limit
    floor_said = (f"max({threshold_deg:g}°, 3 x floor {floor_deg:.1f}°)" if floor_deg is not None
                  else f"{threshold_deg:g}° (floor not measured -- PROVISIONAL)")
    thresholds = f"threshold {rms_limit:g}° rms / {max_limit:g}° max = {floor_said}"
    scope = "decisive" if f0 < MIN_PHASE_SCHROEDER_HZ else "corroborating"
    scope_said = (f"below Schroeder ({MIN_PHASE_SCHROEDER_HZ:g} Hz): decisive" if scope == "decisive" else
                  f"above Schroeder ({MIN_PHASE_SCHROEDER_HZ:g} Hz): corroborating -- whether it holds at the head "
                  "is the ellipsoid's question")
    inside = (f >= lo) & (f <= hi)
    out = {"f0_hz": f0, "window": window, "window_hz": (lo, hi), "half_oct": float(half_oct),
           "n_points": int(inside.sum()), "threshold_deg": rms_limit,
           "max_threshold_deg": max_limit, "floor_deg": floor_deg, "provisional": floor_deg is None,
           "scope": scope, "smoothing": smoothing, "delay_source": "channel" if delay_ms is not None else "window",
           "judged_on": ("residual_rms_deg <= threshold_deg and "
                         "residual_max_deg <= max_threshold_deg"),
           "delay_ms": None, "residual_rms_deg": None, "residual_max_deg": None,
           "residual_at_f0_deg": None, "min_phase": None}

    covered = bool(f.size) and f[0] <= lo * _EDGE_TOL and f[-1] >= hi / _EDGE_TOL
    if not covered or out["n_points"] < MIN_PHASE_MIN_POINTS:
        have = f"{f[0]:.0f}–{f[-1]:.0f} Hz" if f.size else "no points"
        why = (f"the data ({have}) does not cover the window" if not covered else
               f"{out['n_points']} points in the window, fewer than {MIN_PHASE_MIN_POINTS}")
        out.update(verdict="OUT_OF_SCOPE", why=why,
                   line=f"OUT_OF_SCOPE at {f0:g} Hz over {window}: {why} -- no verdict")
        return out

    fw, ph = f[inside], np.deg2rad(p[inside])
    resid, window_delay_ms = _residual(fw, ph, f0, delay_ms)
    rms = float(np.sqrt(np.mean(resid ** 2)))
    peak = float(np.max(np.abs(resid)))
    at_f0 = float(resid[int(np.argmin(np.abs(fw - f0)))])
    failed = []
    if rms > rms_limit:
        failed.append(f"rms {rms:.1f}° > {rms_limit:g}°")
    if peak > max_limit:
        failed.append(f"max {peak:.1f}° > {max_limit:g}° (a step on a few points)")
    ok = not failed
    verdict = "MIN_PHASE" if ok else "NON_MIN_PHASE"
    removed = delay_ms if delay_ms is not None else window_delay_ms
    out.update(verdict=verdict, min_phase=ok, delay_ms=removed, window_delay_ms=window_delay_ms,
               residual_rms_deg=rms, residual_max_deg=peak, residual_at_f0_deg=at_f0,
               why="; ".join(failed) or "the excess phase in the window is the delay, nothing else")
    delay_said = (f"after the channel delay {removed:.2f} ms (the window's own line: {window_delay_ms:.2f} ms)"
                  if delay_ms is not None else f"after {removed:.2f} ms fitted in the window")
    out["line"] = (f"{verdict} at {f0:g} Hz: residual {rms:.1f}° rms, {peak:.1f}° max "
                   f"({at_f0:+.1f}° at f0) over {window} {delay_said}; {thresholds}; "
                   f"read at {smoothing or 'unstated'} smoothing; {scope_said}")
    return out


def _oct_name(half_oct):
    for n in (2, 3, 4, 6, 8, 12):
        if abs(half_oct - 1.0 / n) < 1e-9:
            return f"1/{n}"
    return f"{half_oct:g}"


def _residual(fw, ph, f0, delay_ms=None):
    """`(residual in degrees, the window's own line delay in ms)`. With `delay_ms` the channel's delay is taken out and
    only the mean after it; without it the window's line is taken out."""
    tau0 = _coarse_delay(fw, ph) if delay_ms is None else delay_ms * 1e-3
    rot = np.unwrap(ph + 2 * np.pi * fw * tau0)      # what is left of the ramp is small: safe
    b, a = np.polyfit(fw - f0, rot, 1)               # centred on f0: a well-conditioned fit
    window_delay_ms = float((tau0 - b / (2 * np.pi)) * 1e3)
    if delay_ms is None:
        return np.rad2deg(rot - (a + b * (fw - f0))), window_delay_ms
    return np.rad2deg(rot - rot.mean()), window_delay_ms


def min_phase_across(takes, f0, delay_ms=None, **kw):
    """The verdict over REPEAT takes at one position (the ellipsoid's centre returns): `(verdict, per_take, floor_deg)`.

    The floor is the rms of the residual difference between two takes, over sqrt 2 -- what the read varies by when
    nothing moved; each take is then judged against max(10°, 3 x floor). A verdict is the one at least 2 of every 3
    takes agree on; otherwise `UNSTABLE`, a verdict of its own -- and `UNSTABLE` too when the floor itself is above
    10°, since a threshold of 3 x that would pass a reflection louder than its direct sound. On shallow features this cabin's single-point excess
    phase breathed by orders of magnitude between takes (w-L 155 Hz: S = 3.3 ... 589), so one take is a sample.
    `takes` is `[(freqs, phase_deg)]` on one grid."""
    half_oct = kw.get("half_oct", MIN_PHASE_HALF_OCT)
    lo, hi = float(f0) * 2.0 ** -half_oct, float(f0) * 2.0 ** half_oct
    resids = []
    for freqs, phase in takes:
        f = np.asarray(freqs, dtype=float)
        m = (f >= lo) & (f <= hi) & np.isfinite(np.asarray(phase, dtype=float))
        if m.sum() >= MIN_PHASE_MIN_POINTS:
            resids.append(_residual(f[m], np.deg2rad(np.asarray(phase, dtype=float)[m]), float(f0), delay_ms)[0])
    floor = None
    if len(resids) >= 2 and len({r.size for r in resids}) == 1:
        diffs = [float(np.sqrt(np.mean((a - a.mean() - (b - b.mean())) ** 2)) / np.sqrt(2.0))
                 for i, a in enumerate(resids) for b in resids[i + 1:]]
        floor = float(np.mean(diffs))
    per_take = [min_phase_verdict(freqs, phase, f0, floor_deg=floor, delay_ms=delay_ms, **kw)
                for freqs, phase in takes]
    # A floor above the floor-under-it means the read moves between repeats by more than the test can separate: a
    # threshold of 3 x that would pass a reflection louder than its direct sound (r = 1.05 reads ~20° rms). No verdict.
    if floor is not None and floor > MIN_PHASE_RESID_DEG:
        return "UNSTABLE", per_take, floor
    judged = [v["verdict"] for v in per_take if v["verdict"] in ("MIN_PHASE", "NON_MIN_PHASE")]
    need = int(np.ceil(2.0 * len(per_take) / 3.0))
    verdict = next((v for v in ("MIN_PHASE", "NON_MIN_PHASE") if judged.count(v) >= need), "UNSTABLE")
    return verdict, per_take, floor


def _selftest_min_phase():
    """`min_phase_verdict` on synthetic data whose truth is known -- numpy only, so it runs where
    the gate's own selftest is skipped for want of scipy.

    The excess phase is made the way REW makes it: measured phase minus the minimum phase of the
    same magnitude, the minimum phase from the folded real cepstrum. Then it is served the way REW
    serves it: on a 96-ppo log grid, wrapped to +-180, the bulk delay on top.
    """
    fs, n = 48000.0, 2 ** 16
    fk = np.fft.fftfreq(n, 1 / fs)                   # the whole circle; the negative half is conj
    s = 2j * np.pi * fk
    grid = 20.0 * 2.0 ** (np.arange(int(np.log2(20000 / 20) * 96) + 1) / 96)   # 20 Hz .. 20 kHz
    rng = np.random.default_rng(56)

    def pk(fc, gain_db, q):                          # analog peaking EQ: zeros and poles in the LHP
        A, w0 = 10 ** (gain_db / 40), 2 * np.pi * fc
        return (s ** 2 + s * A * w0 / q + w0 ** 2) / (s ** 2 + s * w0 / (A * q) + w0 ** 2)

    def served(H, delay_s, noise_deg=0.0):
        c = np.fft.ifft(np.log(np.abs(H) + 1e-12)).real
        fold = np.zeros(n)
        fold[0], fold[n // 2] = c[0], c[n // 2]
        fold[1:n // 2] = 2 * c[1:n // 2]
        ep = np.unwrap(np.angle(H * np.exp(-1j * np.fft.fft(fold).imag)))[: n // 2]
        on_grid = np.interp(grid, fk[: n // 2], ep) - 2 * np.pi * grid * delay_s
        on_grid += np.deg2rad(rng.normal(0.0, noise_deg, grid.size))
        return np.rad2deg(np.angle(np.exp(1j * on_grid)))          # wrapped, as REW serves it

    # 1. #56 itself: a minimum-phase PEAK under 7.3 ms of delay. The raw reading at the peak is the
    #    ramp, a large number -- the one that read as "not minimum-phase" -- and the verdict is not.
    ep = served(pk(1000.0, 6.0, 4.0), 7.3e-3, noise_deg=0.3)
    raw = float(ep[int(np.argmin(np.abs(grid - 1000.0)))])
    assert abs(raw) > 90, f"the raw excess phase at the peak should look alarming, got {raw:.0f}"
    v = min_phase_verdict(grid, ep, 1000.0)
    assert v["verdict"] == "MIN_PHASE" and v["min_phase"] is True, v
    assert abs(v["delay_ms"] - 7.3) < 0.02, f"the delay is recovered: {v['delay_ms']:.3f} ms"
    assert v["residual_rms_deg"] < 1.5, v
    assert "±1/6 oct" in v["line"] and "threshold 10° rms / 30° max" in v["line"], v["line"]
    assert v["window"] == "±1/6 oct, 891–1122 Hz" and v["threshold_deg"] == 10.0, v
    assert v["provisional"] and "PROVISIONAL" in v["line"] and v["scope"] == "corroborating", v

    # 2. A minimum-phase DIP under a loopback-sized delay, high enough that np.unwrap alone aliases
    #    on this grid. Red first: the plain unwrap-and-line gets the delay wrong here, so this case
    #    really walks the coarse search.
    ep = served(pk(6000.0, -8.0, 5.0), 22.65e-3)
    v = min_phase_verdict(grid, ep, 6000.0)
    m = (grid >= 6000 / 2 ** (1 / 6)) & (grid <= 6000 * 2 ** (1 / 6))
    naive = -np.polyfit(grid[m], np.unwrap(np.deg2rad(ep[m])), 1)[0] / (2 * np.pi) * 1e3
    assert abs(naive - 22.65) > 1.0, f"the naive unwrap should alias here ({naive:.2f} ms)"
    assert v["verdict"] == "MIN_PHASE" and abs(v["delay_ms"] - 22.65) < 0.02, v

    # 3. Two reflection combs at MATCHED magnitude (the gate selftest's pair): r = 0.95 is minimum-
    #    phase, r = 1.05 -- the reflection louder than the direct sound -- is not. Depth cannot tell
    #    them apart; the residual must. Judged at a notch, 3 ms of bulk delay on both.
    T = 1.5e-3
    notch = 5 / (2 * T)                              # 1667 Hz, the gate selftest's f0
    v_min = min_phase_verdict(grid, served(1 + 0.95 * np.exp(-s * T), 3e-3), notch)
    v_non = min_phase_verdict(grid, served(1 + 1.05 * np.exp(-s * T), 3e-3), notch)
    assert v_min["verdict"] == "MIN_PHASE" and abs(v_min["delay_ms"] - 3.0) < 0.02, v_min
    assert v_non["verdict"] == "NON_MIN_PHASE" and v_non["min_phase"] is False, v_non
    assert v_non["residual_rms_deg"] > MIN_PHASE_RESID_DEG, "r = 1.05 fails on the rms alone"
    # ...and r = 1.01, the step narrower than the grid: under the rms line, caught by the max. Red
    # first -- the rms assertion is what makes this case prove the max test is needed.
    # The max test is exercised on the octave window, where the step's own points land; on the feature's +-1/6 the
    # same step reads 22° max on this grid, under the line -- the grid's blind spot the docstring names, and why a
    # deep narrow dip is judged on REW's linear read.
    v_edge = min_phase_verdict(grid, served(1 + 1.01 * np.exp(-s * T), 3e-3), notch, half_oct=0.5)
    assert v_edge["residual_rms_deg"] <= MIN_PHASE_RESID_DEG, v_edge
    assert v_edge["verdict"] == "NON_MIN_PHASE" and "max" in v_edge["why"], v_edge

    # 4. The window and the threshold asked for are the ones used, and named.
    v = min_phase_verdict(grid, served(pk(1000.0, 6.0, 4.0), 7.3e-3), 1000.0,
                          half_oct=1 / 3, threshold_deg=5.0, max_deg=15.0)
    assert (v["half_oct"], v["threshold_deg"], v["max_threshold_deg"]) == (1 / 3, 5.0, 15.0), v
    assert "±1/3 oct" in v["line"] and "threshold 5° rms / 15° max" in v["line"], v["line"]

    # 5. Out of scope: a window the data does not reach gets no numbers, but still names itself.
    v = min_phase_verdict(grid, ep, 21.0)
    assert v["verdict"] == "OUT_OF_SCOPE" and v["min_phase"] is None, v
    assert v["delay_ms"] is None and v["residual_rms_deg"] is None and "±1/6 oct" in v["line"], v

    # 6. The research note's probes (docs/RESEARCH-2026-09-23-min-phase-verdict.md), each red under the old defaults.
    #    a) A minimum-phase peak with a non-minimum-phase notch 0.4 oct away: the old +-0.5 oct charged the peak with
    #       its neighbour; the feature's own window does not.
    Tn = 1.0 / (2 * 1000.0 * 2 ** 0.4) * 5          # a comb whose notch lands 0.4 oct above 1 kHz
    both = served(pk(1000.0, 6.0, 4.0) * (1 + 1.05 * np.exp(-s * Tn)), 3e-3)
    assert min_phase_verdict(grid, both, 1000.0, half_oct=0.5)["verdict"] == "NON_MIN_PHASE"
    assert min_phase_verdict(grid, both, 1000.0)["verdict"] == "MIN_PHASE"
    #    b) The channel's delay, found once over its band and held fixed, reads the same peak MIN_PHASE and says so.
    ep7 = served(pk(1000.0, 6.0, 4.0), 7.3e-3, noise_deg=0.3)
    d = channel_delay_ms(grid, ep7, (300.0, 3000.0))
    assert abs(d - 7.3) < 0.05, d
    v = min_phase_verdict(grid, ep7, 1000.0, delay_ms=d, smoothing="None")
    assert v["verdict"] == "MIN_PHASE" and v["delay_source"] == "channel" and "channel delay" in v["line"], v
    #    c) A read smoothed coarser than 1/48 is refused: 1/24 already erased a real step.
    try:
        min_phase_verdict(grid, ep7, 1000.0, smoothing="1/24")
    except ValueError:
        pass
    else:
        raise AssertionError("a 1/24-smoothed -EP was judged")
    #    d) The floor comes from the repeats: three takes of a true min-phase peak with 6° of read noise each agree on
    #       MIN_PHASE against max(10°, 3 x floor), where one take against a fixed 10° could flip on the noise alone;
    #       a reflection louder than its direct sound stays NON on every take; a verdict the takes split on is UNSTABLE.
    takes = [(grid, served(pk(1000.0, 6.0, 4.0), 7.3e-3, noise_deg=6.0)) for _ in range(3)]
    verdict, per_take, floor = min_phase_across(takes, 1000.0)
    assert verdict == "MIN_PHASE" and floor is not None and 5.0 < floor < 8.0, (verdict, floor)
    assert all("3 x floor" in t["line"] and not t["provisional"] for t in per_take), per_take[0]["line"]
    non_takes = [(grid, served(1 + 1.2 * np.exp(-s * T), 3e-3, noise_deg=1.0)) for _ in range(3)]
    assert min_phase_across(non_takes, notch)[0] == "NON_MIN_PHASE"
    split = [(grid, served(pk(1000.0, 6.0, 4.0), 7.3e-3)), (grid, served(pk(1000.0, 6.0, 4.0), 7.3e-3)),
             (grid, both), (grid, served(1 + 1.2 * np.exp(-s * T), 3e-3))]
    assert min_phase_across(split, 1000.0, half_oct=0.5)[0] == "UNSTABLE"
    #    e) Below Schroeder the verdict is decisive.
    low = served(pk(110.0, 6.0, 4.0), 7.3e-3, noise_deg=0.3)
    v = min_phase_verdict(grid, low, 110.0)
    assert v["verdict"] == "MIN_PHASE" and v["scope"] == "decisive" and "decisive" in v["line"], v
    try:
        min_phase_verdict(grid, None, 1000.0)
    except ValueError:
        pass
    else:
        raise AssertionError("no phase (an RTA) must raise, not judge")

    return (f"min_phase_verdict OK -- the feature's own ±1/6 oct window keeps a neighbour's notch out; the channel "
            f"delay held fixed; a read coarser than 1/48 refused; the floor from repeat takes (6° of read noise -> "
            f"floor {floor:.1f}°, MIN on all three), takes that disagree UNSTABLE; decisive below Schroeder; "
            f"#56 peak: raw {raw:.0f}° reads MIN_PHASE after 7.30 ms; "
            f"22.65 ms dip at 6 kHz recovered where plain unwrap gives {naive:.2f} ms; "
            f"comb r=0.95 {v_min['residual_rms_deg']:.1f}° rms MIN_PHASE, "
            f"r=1.05 {v_non['residual_rms_deg']:.0f}° rms NON_MIN_PHASE, "
            f"r=1.01 {v_edge['residual_max_deg']:.0f}° max NON_MIN_PHASE")


def _selftest():
    print(_selftest_min_phase())
    # scipy here is TEST-ONLY (Hilbert builds the synthetic min-phase
    # reference); the gate itself is pure numpy and works without scipy
    try:
        from scipy.signal import hilbert
    except ImportError:
        print("selftest SKIPPED -- scipy not installed (needed only to "
              "synthesize the test combs; the gate itself is scipy-free)")
        return

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

    # DEEP minimum-phase notch must never be BLOCKED. A min-phase system has
    # ~zero excess phase at ANY depth, so the point-S sits at the noise floor;
    # measurement noise can push the region-max S into the WARN band (an
    # abstention that routes to the §13 mic-shift check — acceptable), but it
    # must NOT reach BLOCK. This locks out the depth-guard regression that
    # demoted 90/90 to 54/90 in the 2026-07-23 research suite by confidently
    # rejecting deep min-phase dips (docstring ⚠️ note).
    g_deep = comb_case(0.98)          # |1-r|=0.02 -> a very deep min-phase dip
    v_deep, _, _ = g_deep.check(f0, 5.0)
    s_deep = g_deep.s_at(f0)
    assert v_deep != "BLOCK", (
        f"deep min-phase notch BLOCKED: {v_deep} (point-S {s_deep:.2f} -- a "
        f"depth-guard regression; min-phase must never confidently block)")
    assert s_deep < g_deep.z_warn, (
        f"deep min-phase point-S not at floor: {s_deep:.2f}")

    # OUT_OF_SCOPE: a query outside the calibrated band gets no verdict at all -- and
    # crucially does NOT come back as a confident BLOCK, the way it did on 2026-08-21.
    lo, hi = g_non.trust
    for f_out in (lo * 0.7, hi * 1.5):
        v_out, m_out, at_out = g_non.check(f_out, 4.0)
        assert v_out == "OUT_OF_SCOPE" and m_out is None and at_out is None, \
            (f_out, v_out, m_out, at_out)
    assert g_non.check(lo, 4.0)[0] != "OUT_OF_SCOPE", "the band edge is INSIDE the band"
    # ...and an abstention must never act as a veto in the boolean adapter.
    assert g_non.as_boost_gate()("PK", lo * 0.7, 4.0) is True, \
        "a gate with no vote must not block"

    print(f"selftest OK -- min-phase comb r=0.95: {v_min} (S*w {m_min:.1f}); "
          f"non-min-phase r=1.05: {v_non} (S {m_non:.1f} @ {at:.0f} Hz); "
          f"between-notch ALLOW; shelf pass-through; "
          f"deep min-phase r=0.98: {v_deep} (point-S {s_deep:.2f}, not BLOCK)")


if __name__ == "__main__":
    import console                       # issue #21: a code page must not destroy a result
    console.install()
    if "--selftest" in sys.argv:
        _selftest()
