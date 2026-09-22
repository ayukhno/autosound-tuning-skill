"""Generate per-driver (per-band) target curves from a house curve + crossovers + levels.

Replaces the manual NTT-web round-trip: change a crossover and regenerate the per-driver
targets locally in one shot. Ports the method Gemini used, generalized — the house curve and
the per-channel config are INPUTS; nothing car-specific is baked in. (nonotuningtool.com stays
a fine manual alternative to mention to the user.)

Per channel:
  target(f) = house(f)
              − summation_offset(f)          [stereo pairs only]
              + asymmetric_compensation(f)   [stereo, when the L/R levels differ]
              + crossover_loss(f)            [HPF/LPF: the DSP's own family and slope]
              + channel_gain                 [per-channel level — e.g. from level_offsets.py]

Two matched speakers sum, so each side targets LOWER (by ~6 dB where the LF sum is coherent,
tapering to ~3 dB at HF) so the acoustic SUM lands on the house curve. asymmetric_compensation
corrects that when L/R gains differ, so the ASYMMETRIC sum still reconstructs the house curve.

A crossover type is written as the ledger and the DSP write it, family and slope in dB/oct --
`LR24`, `BE12`, `BW18` -- and its shape comes from `dsp_math.xo_response`, the model the rest of the
method predicts with, for every family and order that module can build. The two spellings this
module started with, `lr4` (LR24) and `bw2` (BW12), still read, and keep their closed forms as the
fallback for an install without numpy/scipy. A type that cannot be modelled is REFUSED by name,
never replaced by the nearest one that can (#56 item 6).

Files: `write_targets` names each one `target_curves.target_file_name(code)` -- the name
`target_curves.find_target_curve` looks up (#56 item 4).

stdlib-only for `lr4`/`bw2`; every other type needs numpy + scipy (through `dsp_math`).
Self-test: `python3 target_bands.py --selftest`.  Demo: `python3 target_bands.py --demo`.
"""
from __future__ import annotations
import math
import os
import re
import sys
import warnings
from bisect import bisect_left

import target_curves


# ---- crossover shapes (target follows the roll-off so hygiene EQ doesn't fight the filter) ----
# The closed forms of the two types this module started with. Since #56 item 6 they are the
# FALLBACK, used only where numpy/scipy are missing; `crossover_db` below is the entry point.
def hpf_lr4(f: float, fc: float | None) -> float:
    return 0.0 if not fc else -20.0 * math.log10(1.0 + (fc / f) ** 4)


def lpf_lr4(f: float, fc: float | None) -> float:
    return 0.0 if not fc else -20.0 * math.log10(1.0 + (f / fc) ** 4)


def hpf_bw2(f: float, fc: float | None) -> float:
    return 0.0 if not fc else -10.0 * math.log10(1.0 + (fc / f) ** 4)


_HPF = {"lr4": hpf_lr4, "bw2": hpf_bw2}
_LPF = {"lr4": lpf_lr4}

# ---- which crossover a type names, and whether we can model it (#56 item 6) ----
#
# The two tables above were ALL this module could express, and three of the four junctions of the
# car that reported it are Bessel (w HP 65 BE12, m LP 2800 BE24, tw HP 2800 BE24). None of them was
# representable, and an unknown type silently became `lr4` -- the wrong-knee failure
# `phase_1_foundation.md` §5 is written against: a BE24 high-pass is still -1.86 dB at 1.25 x fc,
# where an LR24 is -2.97, and at the corner the two are -3.01 and -6.02. A target with the wrong
# knee asks the hygiene EQ to fill in, or cut away, a filter that is doing exactly its job.
#
# `dsp_math.xo_response` already models LR/BW/BE at any order it designs, prewarped at the
# processing rate and bench-verified against the Helix -- so the shape comes from there, and the
# tables are what is left when numpy/scipy are not installed.

#: What the two original spellings MEAN in the ledger's terms. They count POLES (`lr4` is a
#: fourth-order Linkwitz-Riley, 24 dB/oct); every other type here is written in dB/oct, as the
#: ledger and the DSP write it -- so `BE4` in prose is `BE24` here.
_LEGACY = {"lr4": ("LR", 24), "bw2": ("BW", 12)}
_LEGACY_KEY = {v: k for k, v in _LEGACY.items()}
_TYPE_RE = re.compile(r"^([A-Za-z]+)(\d+)$")


def crossover_type(spec) -> tuple[str, int]:
    """`(family, slope in dB/oct)` of a cfg type: `"BE12"` -> `("BE", 12)`, `"lr4"` -> `("LR", 24)`.

    Parses; does not judge whether the filter can be modelled (`crossover_db` does). A type that is
    not a family and a slope is refused here, since guessing what it meant is the substitution
    this module used to make."""
    text = str(spec or "").strip()
    if text.lower() in _LEGACY:
        return _LEGACY[text.lower()]
    m = _TYPE_RE.match(text)
    if not m:
        raise ValueError(f"crossover type {spec!r} is not a family and a slope in dB/oct "
                         f"(`LR24`, `BE12`, `BW18`), nor `lr4`/`bw2`")
    return m.group(1).upper(), int(m.group(2))


def _dsp_math():
    """`dsp_math` when it can design a crossover here (numpy AND scipy), else None."""
    try:
        import dsp_math
        import scipy.signal  # noqa: F401 -- `xo_response` designs with it
    except ImportError:
        return None
    return dsp_math


def _modellable(dm, family: str, slope: int) -> bool:
    """Whether `dm.xo_response` builds exactly this filter -- not a neighbour it rounds to.

    `_design` takes `round(slope / 6)` sections, so a slope off the 6 dB grid (BW20) would come out
    as another order under the asked-for name. An LR is built as a Butterworth of HALF the slope,
    squared, so its half must itself be an order on the grid: LR18 would be designed as two
    sections squared, which is an LR24."""
    if family not in dm.MODELLABLE_FAMILIES:
        return False
    if family == "LR":
        return slope % 12 == 0 and slope // 2 in dm.XO_BW_ORDERS
    return slope in dm.XO_BW_ORDERS


def crossover_db(freqs: list[float], fc: float | None, spec, kind: str,
                 fs: float | None = None, where: str = "") -> list[float]:
    """One crossover leg's magnitude, in dB, on `freqs`; zeros when the leg has no corner.

    `kind` is `"hp"` or `"lp"`. `fs` is the DSP's processing rate; omitted, `dsp_math`'s bound one
    (`processing_rate()`, whose source says when it is only assumed). `where` names the channel and
    leg in a refusal, so the refusal says which line of the config to fix."""
    if not fc:
        return [0.0] * len(freqs)
    prefix = f"{where}: " if where else ""
    try:
        family, slope = crossover_type(spec)
    except ValueError as exc:
        raise ValueError(prefix + str(exc)) from None
    canon = f"{family}{slope}"
    label = f"{prefix}`{spec}`" + ("" if str(spec).strip() == canon else f" ({canon})")
    dm = _dsp_math()
    if dm is not None:
        if not _modellable(dm, family, slope):
            families = ", ".join(dm.MODELLABLE_FAMILIES)
            orders = ", ".join(map(str, dm.XO_BW_ORDERS))
            why = (f"{label} is not a filter dsp_math can model ({families}; BW/BE at {orders} "
                   f"dB/oct, LR at twice a BW order)")
            if slope <= 8 and _modellable(dm, family, slope * 6):
                why += (f"; the slope is in dB/oct here, so a {slope}-pole {family} is "
                        f"`{family}{slope * 6}`")
            raise ValueError(why + " -- no target is given with another filter's knee in its place")
        import numpy as np
        h = dm.xo_response(np.asarray(freqs, dtype=float), float(fc), slope, kind, family, fs=fs)
        return [float(v) for v in 20.0 * np.log10(np.abs(h) + 1e-15)]
    fn = (_HPF if kind == "hp" else _LPF).get(_LEGACY_KEY.get((family, slope)))
    if fn is None:
        raise ValueError(
            f"{label} needs numpy + scipy (dsp_math.xo_response): without them only the closed "
            f"forms of LR24 and BW12 high-pass and LR24 low-pass are here -- no target is given "
            f"with another filter's knee in its place")
    return [fn(f, fc) for f in freqs]


def summation_offset(f: float, lo_db: float = 6.0, hi_db: float = 3.0,
                     f_lo: float = 80.0, f_hi: float = 1000.0) -> float:
    """Two-speaker acoustic-sum offset: lo_db at/below f_lo, hi_db at/above f_hi, log-interp between."""
    if f <= f_lo:
        return lo_db
    if f >= f_hi:
        return hi_db
    t = (math.log10(f) - math.log10(f_lo)) / (math.log10(f_hi) - math.log10(f_lo))
    return lo_db - (lo_db - hi_db) * t


def asymmetric_compensation(f: float, gain_l: float, gain_r: float, **kw) -> float:
    """Correction so an ASYMMETRIC L/R sum (gains differ) still reconstructs the house curve.
    Zero when gains are equal."""
    s = summation_offset(f, **kw)
    if s == 0.0 or gain_l == gain_r:
        return 0.0
    p = s / math.log10(2)
    sum_val = 10 ** (gain_l / p) + 10 ** (gain_r / p)
    return s - p * math.log10(sum_val)


class HouseCurve:
    """A house/target curve; linear interpolation in log-frequency, clamped at the ends."""

    def __init__(self, freqs: list[float], mags: list[float]):
        pairs = sorted(zip(freqs, mags))
        self.f = [math.log10(p[0]) for p in pairs]
        self.m = [p[1] for p in pairs]

    @classmethod
    def from_file(cls, path: str) -> "HouseCurve":
        fr, mg = [], []
        with open(path, encoding="utf-8", errors="replace") as fh:
            for raw in fh:
                s = raw.strip()
                if not s or s.startswith("#"):
                    continue
                parts = s.split()
                try:
                    fr.append(float(parts[0]))
                    mg.append(float(parts[1]))
                except (ValueError, IndexError):
                    continue
        return cls(fr, mg)

    def at(self, freq: float) -> float:
        x = math.log10(freq)
        if x <= self.f[0]:
            return self.m[0]
        if x >= self.f[-1]:
            return self.m[-1]
        i = bisect_left(self.f, x)
        x0, x1 = self.f[i - 1], self.f[i]
        y0, y1 = self.m[i - 1], self.m[i]
        return y0 + (y1 - y0) * (x - x0) / (x1 - x0)


def _partner_gain(name: str, cfg: dict[str, dict], own_gain: float) -> float:
    """The L/R partner's gain (for asymmetric compensation). Falls back to own (symmetric)."""
    for a, b in (("-L", "-R"), ("-R", "-L"), ("_L", "_R"), ("_R", "_L")):
        if name.endswith(a):
            partner = name[: -len(a)] + b
            if partner in cfg:
                return cfg[partner].get("gain", 0.0)
    return own_gain


def _level_db(freq: float, house: HouseCurve, name: str, ch: dict,
              cfg: dict[str, dict], summ_kw: dict) -> float:
    """Everything in a channel's target but its crossover legs."""
    db = house.at(freq)
    if ch.get("is_stereo"):
        db -= summation_offset(freq, **summ_kw)
        gain_l = ch.get("gain", 0.0)
        gain_r = _partner_gain(name, cfg, gain_l)
        db += asymmetric_compensation(freq, gain_l, gain_r, **summ_kw)
    return db + ch.get("gain", 0.0)


def band_targets(freqs: list[float], house: HouseCurve, name: str, ch: dict,
                 cfg: dict[str, dict], summ_kw: dict, fs: float | None = None) -> list[float]:
    """The channel's target on `freqs`. The crossover legs are computed once for the whole grid:
    a filter designed per point is ~0.7 ms, ~2 s for a seven-channel car at 200 points."""
    hp = crossover_db(freqs, ch.get("hpf"), ch.get("hpf_type", "lr4"), "hp", fs, f"{name} hpf")
    lp = crossover_db(freqs, ch.get("lpf"), ch.get("lpf_type", "lr4"), "lp", fs, f"{name} lpf")
    return [_level_db(f, house, name, ch, cfg, summ_kw) + h + low
            for f, h, low in zip(freqs, hp, lp)]


def band_target(freq: float, house: HouseCurve, name: str, ch: dict,
                cfg: dict[str, dict], summ_kw: dict, fs: float | None = None) -> float:
    return band_targets([freq], house, name, ch, cfg, summ_kw, fs)[0]


def _warn_if_demo_config(cfg: dict[str, dict]) -> None:
    """Catch the real incident this guards against: per-band targets committed
    for an actual project while `cfg` was still (partly) the module's demo
    placeholders — wrong crossover knees + flat/symmetric-looking gains,
    silently, because nothing ever complained. Last-resort net; the real fix is
    feeding `generate()` the project's actual v1/vN crossovers + level_offsets.py
    gains, never `_DEMO_CFG` itself (see phase_1_foundation.md Step 5)."""
    for name, ch in cfg.items():
        demo = _DEMO_CFG.get(name)
        if demo and all(ch.get(k) == v for k, v in demo.items() if k != "gain"):
            warnings.warn(
                f"target_bands: channel {name!r} config matches _DEMO_CFG's crossover "
                f"exactly (hpf/lpf/type) — if this is a real project, you're generating "
                f"per-band targets from PLACEHOLDER values, not this project's actual "
                f"crossovers. Feed generate() the real v1/vN config.", UserWarning)


def generate(house: HouseCurve, cfg: dict[str, dict], npts: int = 200,
             f_min: float = 20.0, f_max: float = 20000.0,
             summ_kw: dict | None = None,
             fs: float | None = None) -> dict[str, list[tuple[float, float]]]:
    """Per-channel targets. `cfg[code]["hpf_type"]`/`["lpf_type"]` name the DSP's filter (`BE12`,
    `LR24`; `lr4` when absent, as always); `fs` is the processing rate the crossover is modelled at
    (omitted: `dsp_math.processing_rate()`). A type that cannot be modelled raises, naming the
    channel and the leg."""
    _warn_if_demo_config(cfg)
    summ_kw = summ_kw or {}
    lo, hi = math.log10(f_min), math.log10(f_max)
    freqs = [10 ** (lo + (hi - lo) * i / (npts - 1)) for i in range(npts)]
    out: dict[str, list[tuple[float, float]]] = {}
    for name, ch in cfg.items():
        out[name] = list(zip(freqs, band_targets(freqs, house, name, ch, cfg, summ_kw, fs)))
    return out


def write_targets(targets: dict[str, list[tuple[float, float]]], out_dir: str) -> None:
    """One file per channel, named `target_curves.target_file_name(code)` -- the name the reader
    looks up, through the same function (#56 item 4). Every name is made before any file is
    written, so a code the grammar would never read back (`w_L`) leaves nothing half-written."""
    names = {name: target_curves.target_file_name(name) for name in targets}
    os.makedirs(out_dir, exist_ok=True)
    for name, rows in targets.items():
        with open(os.path.join(out_dir, names[name]), "w", encoding="utf-8") as fh:
            fh.write(f"# Per-band target for {name}\n# Frequency(Hz) Magnitude(dB)\n")
            fh.write("\n".join(f"{f:.2f} {db:.2f}" for f, db in rows) + "\n")


# ---------------------------------------------------------------------------
_DEMO_CFG = {
    "tw-L": {"hpf": 3500, "hpf_type": "lr4", "gain": -1.5, "is_stereo": True},
    "tw-R": {"hpf": 3500, "hpf_type": "lr4", "gain": 0.0, "is_stereo": True},
    "m-L": {"hpf": 300, "lpf": 3500, "gain": -2.0, "is_stereo": True},
    "m-R": {"hpf": 300, "lpf": 3500, "gain": 0.0, "is_stereo": True},
    "w-L": {"hpf": 60, "lpf": 300, "gain": -1.5, "is_stereo": True},
    "w-R": {"hpf": 60, "lpf": 300, "gain": 0.0, "is_stereo": True},
    "sw": {"hpf": 20, "hpf_type": "bw2", "lpf": 60, "gain": 0.0, "is_stereo": False},
}


def _selftest() -> None:
    house = HouseCurve([20, 100, 1000, 20000], [8.0, 4.0, 0.0, -3.0])
    assert abs(house.at(1000) - 0.0) < 1e-6
    assert abs(house.at(10) - 8.0) < 1e-6  # clamps below range
    assert abs(summation_offset(80) - 6.0) < 1e-9 and abs(summation_offset(1000) - 3.0) < 1e-9
    assert abs(asymmetric_compensation(500, -2.0, -2.0)) < 1e-9, "symmetric → 0"
    assert asymmetric_compensation(500, -2.0, 0.0) > 0.0, "asymmetric raises target"
    # symmetric config → stereo passband target ≈ house − summation_offset (comp = 0)
    sym = {"m-L": {"hpf": 300, "lpf": 3500, "gain": 0.0, "is_stereo": True},
           "m-R": {"hpf": 300, "lpf": 3500, "gain": 0.0, "is_stereo": True}}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)  # sym reuses demo-shaped hpf/lpf on purpose
        ms = next(db for f, db in generate(house, sym, npts=200)["m-R"] if abs(f - 1000) < 30)
    assert abs(ms - (house.at(1000) - summation_offset(1000))) < 0.3, f"symmetric mid ≈ house − S, got {ms}"
    # asymmetric demo → the cut side sits exactly (gain difference) below the uncut side.
    # _DEMO_CFG legitimately triggers the demo-config guard here — expected, silence it.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        t = generate(house, _DEMO_CFG, npts=200)
    assert set(t) == set(_DEMO_CFG)

    def val(name, ft):
        return next(db for f, db in t[name] if abs(f - ft) < 30)

    assert abs((val("m-L", 1000) - val("m-R", 1000)) - (-2.0)) < 1e-6, "L/R gain difference flows through"
    # mono sub (no summation offset): below house by its narrow-band crossover roll-off only
    sub40 = next(db for f, db in t["sw"] if abs(f - 40) < 5)
    assert house.at(40) - 4.0 < sub40 < house.at(40), f"sub follows house minus xo, got {sub40}"
    # The demo-config guard: real incident (RN-A project) had per-band targets
    # committed with _DEMO_CFG's tw HPF 3500 instead of the project's actual
    # 1000 Hz — silently, because nothing warned. Confirm the net catches it.
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        generate(house, {"tw-L": dict(_DEMO_CFG["tw-L"])}, npts=20)
        assert any("PLACEHOLDER" in str(x.message) for x in caught), \
            "demo-shaped config must warn"
    with warnings.catch_warnings(record=True) as caught2:
        warnings.simplefilter("always")
        generate(house, {"tw-L": {"hpf": 1000, "hpf_type": "lr4", "gain": -1.2,
                                  "is_stereo": True}}, npts=20)
        assert not caught2, "a real (non-demo) config must NOT warn"

    # ── #56 item 6: Bessel is expressible, and its knee is not an LR's ───────────────────────
    # The reporting car's three Bessel junctions: w HP 65 BE12, m LP 2800 BE24, tw HP 2800 BE24.
    # Each raised nothing here only by becoming an LR24; now each is itself.
    flat = HouseCurve([20, 20000], [0.0, 0.0])
    fc = 2800.0

    def leg(typ, kind, f):
        key = "hpf" if kind == "hp" else "lpf"
        return band_target(f, flat, "tw-L", {key: fc, key + "_type": typ}, {}, {})

    # Anchored to DEFINITIONS, not to the module under test: every Bessel here is -3 dB at its
    # corner (norm="mag", the Helix's own, dsp_math bench fact 9) and a Linkwitz-Riley is -6.02,
    # being a Butterworth squared.
    for typ, at_fc in (("BE24", -3.01), ("LR24", -6.02), ("BE12", -3.01)):
        for kind in ("hp", "lp"):
            got = leg(typ, kind, fc)
            assert abs(got - at_fc) < 0.02, (typ, kind, got)
    # The number #56 quotes: a BE24 is still about -1.8 dB at 1.25 x fc on its passband side,
    # where an LR24 is -2.97 -- the ~1.1 dB a target built on the wrong family misplaces there, and
    # 3 dB at the corner itself. The same on the low-pass, mirrored.
    be_hp, lr_hp = leg("BE24", "hp", 1.25 * fc), leg("LR24", "hp", 1.25 * fc)
    be_lp, lr_lp = leg("BE24", "lp", fc / 1.25), leg("LR24", "lp", fc / 1.25)
    assert -1.95 < be_hp < -1.75 and -1.95 < be_lp < -1.75, (be_hp, be_lp)
    assert abs(lr_hp - -2.97) < 0.05 and abs(lr_lp - -2.97) < 0.05, (lr_hp, lr_lp)
    assert 1.0 < be_hp - lr_hp < 1.25 and 1.0 < be_lp - lr_lp < 1.25, (be_hp - lr_hp, be_lp - lr_lp)
    car = {"w-L": {"hpf": 65, "hpf_type": "BE12", "lpf": 400, "lpf_type": "LR24", "gain": -1.0,
                   "is_stereo": True},
           "m-L": {"hpf": 400, "hpf_type": "LR24", "lpf": 2800, "lpf_type": "BE24", "gain": -2.0,
                   "is_stereo": True},
           "tw-L": {"hpf": 2800, "hpf_type": "BE24", "gain": -4.0, "is_stereo": True}}
    t_car = generate(house, car, npts=60)
    assert set(t_car) == set(car)
    w_knee = band_target(1.25 * 65, flat, "w-L", {"hpf": 65, "hpf_type": "BE12"}, {}, {})
    assert -2.0 < w_knee < -1.8, w_knee
    # The two original spellings mean what they always meant, in any case.
    assert crossover_type("lr4") == crossover_type("LR4") == crossover_type("LR24") == ("LR", 24)
    assert crossover_type("bw2") == crossover_type("BW12") == ("BW", 12)
    # A type that cannot be modelled is REFUSED by name -- channel, leg, and what was asked.
    unmodelled = "not a filter dsp_math can model"
    for typ, words in (("CH24", unmodelled),      # enterable on a Helix, and not modellable
                       ("LR18", unmodelled),      # would be built as an LR24
                       ("BW20", unmodelled),      # off the 6 dB grid
                       ("BE48", unmodelled),
                       ("BE4", "`BE24`"),         # poles, not dB/oct: and it says so
                       ("Bessel", "not a family and a slope")):
        try:
            generate(house, {"m-R": {"hpf": 400, "lpf": 2800, "lpf_type": typ}}, npts=10)
        except ValueError as exc:
            assert words in str(exc) and "m-R lpf" in str(exc), (typ, exc)
            continue
        raise AssertionError(f"{typ} was not refused")

    # ── the no-scipy fallback: the two closed forms, and nothing substituted beyond them ───────
    # The closed form is the analogue DEFINITION; dsp_math designs digitally at 96 kHz, prewarped
    # AT the corner. Two independent paths, one filter: they agree at the corner exactly, and the
    # warping they differ by grows away from it -- 0.09 dB two octaves down, 48 dB into the stop.
    grid = [700.0, 1400.0, 2800.0, 5600.0, 11200.0]
    by_model = crossover_db(grid, fc, "LR24", "hp")
    real = globals()["_dsp_math"]
    globals()["_dsp_math"] = lambda: None
    try:
        closed = crossover_db(grid, fc, "lr4", "hp")
        assert closed == [hpf_lr4(f, fc) for f in grid]
        assert max(abs(a - b) for a, b in zip(by_model, closed)) < 0.1, (by_model, closed)
        assert abs(by_model[2] - closed[2]) < 1e-9, (by_model[2], closed[2])
        assert abs(closed[2] - -6.02) < 0.01, closed
        assert crossover_db(grid, fc, "BW12", "hp") == [hpf_bw2(f, fc) for f in grid]
        for typ, kind in (("BE24", "hp"), ("bw2", "lp")):
            try:
                crossover_db(grid, fc, typ, kind, where="tw-L")
            except ValueError as exc:
                assert "needs numpy + scipy" in str(exc) and "tw-L" in str(exc), exc
                continue
            raise AssertionError(f"{typ} {kind} was substituted without scipy")
    finally:
        globals()["_dsp_math"] = real

    # ── #56 item 4: what the writer writes, the reader finds -- through the car's own titles ────
    import tempfile
    import naming
    gloss = naming.Glossary({"channels": [{"code": c} for c in car]})
    with tempfile.TemporaryDirectory() as d:
        write_targets(t_car, d)
        for code, rows in t_car.items():
            path, data = target_curves.find_target_curve(f"{code}_51 (rta)", d, gloss)
            assert path == os.path.join(d, target_curves.target_file_name(code)), (code, path)
            assert len(data[0]) == len(rows) and abs(data[1][0] - round(rows[0][1], 2)) < 1e-9
        # A key no title can carry is refused before a single file is written.
        try:
            write_targets({"tw-R": t_car["tw-L"], "w_L": t_car["w-L"]}, os.path.join(d, "bad"))
        except ValueError as exc:
            assert "`w-L`" in str(exc), exc
        else:
            raise AssertionError("write_targets wrote a file no reader can find")
        assert not os.path.exists(os.path.join(d, "bad"))

    print("selftest OK — sym m-R@1k=%.2f (house−S=%.2f); asym m-L−m-R=%.2f dB; sub@40=%.2f (house=%.2f); "
          "demo-config guard fires on placeholder cfg, silent on a real one; "
          "BE24 @1.25fc %.2f dB vs LR24 %.2f (Bessel from dsp_math, -3.01/-6.02 at the corner), "
          "unmodellable types refused by name, lr4/bw2 closed forms without scipy agree with the "
          "model at the corner and to 0.1 dB over two octaves; the writer's files are found by "
          "the reader's titles"
          % (ms, house.at(1000) - summation_offset(1000), val("m-L", 1000) - val("m-R", 1000),
             sub40, house.at(40), be_hp, lr_hp))


if __name__ == "__main__":
    import console                       # issue #21: a code page must not destroy a result
    console.install()
    if "--selftest" in sys.argv:
        _selftest()
    elif "--demo" in sys.argv:
        house = HouseCurve([20, 100, 1000, 20000], [8.0, 4.0, 0.0, -3.0])
        out = "/tmp/target_bands_demo"
        write_targets(generate(house, _DEMO_CFG), out)
        print("demo targets written to", out)
    else:
        print(__doc__)
        print("Import generate(house, cfg) / write_targets(...). Run --selftest or --demo.")
