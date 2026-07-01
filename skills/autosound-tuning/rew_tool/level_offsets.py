"""Preliminary per-channel LEVEL offsets from geometry (off-axis directivity + distance).

A physics-grounded STARTING level balance for Phase 1 — a hypothesis to verify by
RTA/ear, not a final answer. Ports the method Gemini used on the Passat B8, generalized:
inputs are PROJECT data (ask the user), nothing car-specific is baked in.

Model per channel:
  * off-axis loss  = band-averaged far-field piston directivity  D(f,θ) = 2·J1(kasinθ)/(kasinθ)
  * distance loss  = 10·n·log10(d)     (n=2 → inverse-square/free field; n<2 in a live cabin)
  * delivered      = −distance_loss − offaxis_loss   (louder = higher)
  * offset (apply) = min(delivered) − delivered      (≤ 0, CUT-ONLY; loudest driver cut most)

INPUTS (per driver, all PROJECT data — ask the user, store in autosound_context.md):
  d      — path distance driver→reference ear (m)
  theta  — off-axis angle between the driver's aim and the ear direction (deg)
  a      — effective piston radius (m) ≈ cone/dome radius (enclosure sets the LF band edge)
  band   — (f_min, f_max) the driver's working band (from the crossovers)
  n      — distance attenuation exponent (default 2.0; lower it if the cabin is reverberant)

stdlib-only. Self-test: `python level_offsets.py --selftest`.
"""
from __future__ import annotations
import math
import sys
from dataclasses import dataclass

C_AIR = 343.0  # m/s


def bessj1(x: float) -> float:
    """Bessel function of the first kind, order 1 (Numerical Recipes rational approx, ~1e-7)."""
    ax = abs(x)
    if ax < 8.0:
        y = x * x
        p1 = x * (72362614232.0 + y * (-7895059235.0 + y * (242396853.1 + y * (
            -2972611.439 + y * (15704.48260 + y * (-30.16036606))))))
        p2 = 144725228442.0 + y * (2300535178.0 + y * (18583304.74 + y * (
            99447.43394 + y * (376.9991397 + y * 1.0))))
        return p1 / p2
    z = 8.0 / ax
    y = z * z
    xx = ax - 2.356194491
    p1 = 1.0 + y * (0.183105e-2 + y * (-0.3516396496e-4 + y * (0.2457520174e-5 + y * (-0.240337019e-6))))
    p2 = 0.04687499995 + y * (-0.2002690873e-3 + y * (0.8449199096e-5 + y * (-0.88228987e-6 + y * 0.105787412e-6)))
    ans = math.sqrt(0.636619772 / ax) * (math.cos(xx) * p1 - z * math.sin(xx) * p2)
    return -ans if x < 0.0 else ans


def directivity(f: float, theta_deg: float, a: float, c: float = C_AIR) -> float:
    """Far-field circular-piston directivity magnitude D(f,θ) ∈ (0, 1]. On-axis (θ=0) → 1."""
    x = (2.0 * math.pi * f / c) * a * math.sin(math.radians(theta_deg))
    if abs(x) < 1e-9:
        return 1.0
    return abs(2.0 * bessj1(x) / x)


def band_offaxis_loss_db(f_min: float, f_max: float, theta_deg: float, a: float,
                         c: float = C_AIR, npts: int = 60) -> float:
    """Band-averaged off-axis loss (dB, ≥ 0). Log-spaced average over the driver's band."""
    if theta_deg == 0.0 or a == 0.0:
        return 0.0
    lo, hi = math.log10(f_min), math.log10(f_max)
    vals = []
    for i in range(npts):
        f = 10.0 ** (lo + (hi - lo) * i / (npts - 1))
        vals.append(20.0 * math.log10(directivity(f, theta_deg, a, c)))
    return -sum(vals) / len(vals)  # losses are negative dB → return positive loss


def distance_loss_db(d: float, n: float = 2.0) -> float:
    """Distance attenuation (dB, relative). n=2 → 20·log10(d) (6 dB/doubling)."""
    return 10.0 * n * math.log10(d)


@dataclass
class Driver:
    name: str
    d: float                 # distance to ear (m)
    theta: float             # off-axis angle (deg)
    a: float                 # piston radius (m)
    band: tuple[float, float]  # (f_min, f_max) Hz


def compute_offsets(drivers: list[Driver], n: float = 2.0, c: float = C_AIR) -> dict[str, float]:
    """Cut-only per-channel offsets (dB, ≤ 0), normalized so the quietest driver = 0."""
    delivered = {}
    for dr in drivers:
        oa = band_offaxis_loss_db(dr.band[0], dr.band[1], dr.theta, dr.a, c)
        delivered[dr.name] = -distance_loss_db(dr.d, n) - oa
    floor = min(delivered.values())
    return {name: round(floor - lvl, 1) for name, lvl in delivered.items()}


def _selftest() -> None:
    assert abs(bessj1(0.0)) < 1e-9, "J1(0)=0"
    assert abs(bessj1(1.0) - 0.4400505857) < 1e-6, f"J1(1)={bessj1(1.0)}"
    assert abs(directivity(1000, 0.0, 0.05) - 1.0) < 1e-9, "on-axis → 1"
    assert directivity(10000, 45.0, 0.05) < 1.0, "off-axis HF attenuates"
    # a nearer + more on-axis driver must be cut MORE (more negative) than a far/off-axis one
    drv = [
        Driver("near_onaxis", d=1.5, theta=10.0, a=0.03, band=(300, 3500)),
        Driver("far_offaxis", d=2.0, theta=40.0, a=0.03, band=(300, 3500)),
    ]
    off = compute_offsets(drv)
    assert off["near_onaxis"] <= off["far_offaxis"], off
    assert max(off.values()) == 0.0 and min(off.values()) <= 0.0, "cut-only, floor=0"
    print("selftest OK —",
          f"J1(1)={bessj1(1.0):.6f}; D(10k,45°,5cm)={directivity(10000,45,0.05):.3f}; offsets={off}")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        print(__doc__)
        print("Run with --selftest, or import compute_offsets(drivers, n).")
