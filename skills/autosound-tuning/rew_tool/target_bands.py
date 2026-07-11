"""Generate per-driver (per-band) target curves from a house curve + crossovers + levels.

Replaces the manual NTT-web round-trip: change a crossover and regenerate the per-driver
targets locally in one shot. Ports the method Gemini used, generalized — the house curve and
the per-channel config are INPUTS; nothing car-specific is baked in. (nonotuningtool.com stays
a fine manual alternative to mention to the user.)

Per channel:
  target(f) = house(f)
              − summation_offset(f)          [stereo pairs only]
              + asymmetric_compensation(f)   [stereo, when the L/R levels differ]
              + crossover_loss(f)            [HPF/LPF electrical+acoustic shape]
              + channel_gain                 [per-channel level — e.g. from level_offsets.py]

Two matched speakers sum, so each side targets LOWER (by ~6 dB where the LF sum is coherent,
tapering to ~3 dB at HF) so the acoustic SUM lands on the house curve. asymmetric_compensation
corrects that when L/R gains differ, so the ASYMMETRIC sum still reconstructs the house curve.

stdlib-only. Self-test: `python target_bands.py --selftest`.  Demo: `python target_bands.py --demo`.
"""
from __future__ import annotations
import math
import os
import sys
import warnings
from bisect import bisect_left


# ---- crossover shapes (target follows the roll-off so hygiene EQ doesn't fight the filter) ----
def hpf_lr4(f: float, fc: float | None) -> float:
    return 0.0 if not fc else -20.0 * math.log10(1.0 + (fc / f) ** 4)


def lpf_lr4(f: float, fc: float | None) -> float:
    return 0.0 if not fc else -20.0 * math.log10(1.0 + (f / fc) ** 4)


def hpf_bw2(f: float, fc: float | None) -> float:
    return 0.0 if not fc else -10.0 * math.log10(1.0 + (fc / f) ** 4)


_HPF = {"lr4": hpf_lr4, "bw2": hpf_bw2}
_LPF = {"lr4": lpf_lr4}


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


def band_target(freq: float, house: HouseCurve, name: str, ch: dict,
                cfg: dict[str, dict], summ_kw: dict) -> float:
    db = house.at(freq)
    if ch.get("is_stereo"):
        db -= summation_offset(freq, **summ_kw)
        gain_l = ch.get("gain", 0.0)
        gain_r = _partner_gain(name, cfg, gain_l)
        db += asymmetric_compensation(freq, gain_l, gain_r, **summ_kw)
    db += _HPF.get(ch.get("hpf_type", "lr4"), hpf_lr4)(freq, ch.get("hpf"))
    db += _LPF.get(ch.get("lpf_type", "lr4"), lpf_lr4)(freq, ch.get("lpf"))
    db += ch.get("gain", 0.0)
    return db


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
             summ_kw: dict | None = None) -> dict[str, list[tuple[float, float]]]:
    _warn_if_demo_config(cfg)
    summ_kw = summ_kw or {}
    lo, hi = math.log10(f_min), math.log10(f_max)
    out: dict[str, list[tuple[float, float]]] = {}
    for name, ch in cfg.items():
        rows = []
        for i in range(npts):
            f = 10 ** (lo + (hi - lo) * i / (npts - 1))
            rows.append((f, band_target(f, house, name, ch, cfg, summ_kw)))
        out[name] = rows
    return out


def write_targets(targets: dict[str, list[tuple[float, float]]], out_dir: str) -> None:
    os.makedirs(out_dir, exist_ok=True)
    for name, rows in targets.items():
        with open(os.path.join(out_dir, f"{name}_target.txt"), "w", encoding="utf-8") as fh:
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

    print("selftest OK — sym m-R@1k=%.2f (house−S=%.2f); asym m-L−m-R=%.2f dB; sub@40=%.2f (house=%.2f); "
          "demo-config guard fires on placeholder cfg, silent on a real one"
          % (ms, house.at(1000) - summation_offset(1000), val("m-L", 1000) - val("m-R", 1000), sub40, house.at(40)))


if __name__ == "__main__":
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
