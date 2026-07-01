#!/usr/bin/env python3
"""Synthetic-but-realistic REW-style FR plot to test whether Gemini analyzes
an IMAGE of a curve better than the raw numbers. L/R measured + target."""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import LogLocator, FuncFormatter

f = np.logspace(np.log10(20), np.log10(20000), 600)

def tilt(f):  # house target: +6 dB @20 Hz down to -3 dB @20 kHz
    return np.interp(np.log10(f), [np.log10(20), np.log10(1000), np.log10(20000)], [6, 0, -3])

target = tilt(f)

def bump(f, fc, q, g):
    return g * np.exp(-((np.log10(f) - np.log10(fc)) ** 2) / (2 * (1.0 / q) ** 2))

# Measured LEFT: target + real-world warts
meas_L = (target
          + bump(f, 70, 1.2, 4.5)     # midbass hump
          - bump(f, 230, 1.0, 5.0)    # SBIR-style suckout 150-300
          + bump(f, 3000, 1.3, 3.5)   # presence/harshness peak
          - bump(f, 9000, 0.8, 2.5))  # slight upper dip
meas_L[f > 12000] -= (np.log10(f[f > 12000]) - np.log10(12000)) * 18  # HF rolloff

# Measured RIGHT: similar but hotter 1-4k (image pulls right) + less midbass
meas_R = (target
          + bump(f, 70, 1.2, 2.5)
          - bump(f, 230, 1.0, 4.2)
          + bump(f, 2800, 1.1, 5.5)   # hotter presence -> imaging skew
          - bump(f, 9000, 0.8, 2.0))
meas_R[f > 12000] -= (np.log10(f[f > 12000]) - np.log10(12000)) * 18

# light 1/6-oct-ish smoothing
def smooth(y, n=9):
    k = np.ones(n) / n
    return np.convolve(y, k, mode="same")
meas_L, meas_R = smooth(meas_L), smooth(meas_R)

fig, ax = plt.subplots(figsize=(11, 5.5), dpi=130)
ax.semilogx(f, target, color="#888", lw=2, ls="--", label="Target (house curve)")
ax.semilogx(f, meas_L, color="#1f77b4", lw=2, label="Measured L")
ax.semilogx(f, meas_R, color="#d62728", lw=2, label="Measured R")

ax.set_xlim(20, 20000)
ax.set_ylim(-12, 14)
ax.set_xlabel("Frequency (Hz)")
ax.set_ylabel("SPL (dB)")
ax.set_title("Front stage — L/R vs target (1/6 oct), MMM RTA")
ax.grid(True, which="both", ls=":", alpha=0.4)
ax.xaxis.set_major_locator(LogLocator(base=10, subs=[1, 2, 5]))
ax.xaxis.set_major_formatter(FuncFormatter(
    lambda x, _: f"{x/1000:.0f}k" if x >= 1000 else f"{x:.0f}"))
ax.legend(loc="upper right")
fig.tight_layout()
out = __file__.rsplit("/", 1)[0] + "/fr_L_R_vs_target.png"
fig.savefig(out)
print("wrote", out)
