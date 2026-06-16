"""Read Nono Tuning Tool curve exports (the files behind the misnamed
`ATF_EQ_(Helix)_*` zips). These are NOT Helix EQ banks — they are target
curves exported by nonotuningtool.com, in two shapes:

  * Full target  (e.g. `..._0db_REW.txt`)  -> 2 cols:  freq  mag(dB)
  * Per-band     (e.g. `..._mid_..._SUM`)  -> 3 cols:  freq  mag(dB)  phase(deg)

The full curve is magnitude-only (no phase); the per-band components carry
the crossover phase (see `references/rew-api-quirks.md` Targets). Use this to
pull a downloaded Nono curve straight into analysis without a REW round-trip.

stdlib-only. CLI self-test: `python nono_curves.py <file-or-dir>`
"""
from __future__ import annotations
import os
import sys
from dataclasses import dataclass, field


@dataclass
class NonoCurve:
    path: str
    source: str | None          # e.g. "Generated from Nono Tuning Tool"
    version: str | None         # e.g. "3.1.1"
    freqs: list[float] = field(default_factory=list)
    mag: list[float] = field(default_factory=list)
    phase: list[float] | None = None   # None for a magnitude-only (full) target

    @property
    def has_phase(self) -> bool:
        return self.phase is not None

    @property
    def kind(self) -> str:
        return "per-band (mag+phase)" if self.has_phase else "full target (mag-only)"

    def __len__(self) -> int:
        return len(self.freqs)


def parse_nono_curve(path: str) -> NonoCurve:
    """Parse one Nono curve export. Auto-detects 2-col (mag) vs 3-col (mag+phase).

    Tolerant by design: comment lines (`#`) and blanks are skipped; a row's
    column count decides the shape from the first data row, and ragged/short
    rows are ignored rather than crashing (matches the 'pull must TOLERATE'
    rule for targets).
    """
    source = version = None
    freqs: list[float] = []
    mag: list[float] = []
    phase: list[float] = []
    has_phase: bool | None = None

    with open(path, encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            line = raw.strip()
            if not line:
                continue
            if line.startswith("#"):
                low = line.lstrip("# ").strip()
                if low.lower().startswith("version"):
                    version = low.split(None, 1)[1].strip() if " " in low else low
                else:
                    source = low
                continue
            parts = line.split()
            try:
                nums = [float(p) for p in parts]
            except ValueError:
                continue  # not a data row
            if len(nums) < 2:
                continue
            if has_phase is None:
                has_phase = len(nums) >= 3
            freqs.append(nums[0])
            mag.append(nums[1])
            if has_phase:
                phase.append(nums[2] if len(nums) >= 3 else float("nan"))

    return NonoCurve(
        path=path, source=source, version=version,
        freqs=freqs, mag=mag, phase=(phase if has_phase else None),
    )


def parse_nono_band_set(directory: str) -> dict[str, NonoCurve]:
    """Parse every `*.txt` Nono export in a directory, keyed by detected band.

    Band is guessed from the filename (sw / woofer / mid / tw); the full
    target (no band token) is keyed 'full'.
    """
    out: dict[str, NonoCurve] = {}
    for name in sorted(os.listdir(directory)):
        if not name.lower().endswith(".txt"):
            continue
        curve = parse_nono_curve(os.path.join(directory, name))
        low = name.lower()
        for tok in ("sw", "woofer", "mid", "tw"):
            if f"_{tok}_" in low or f"_{tok}(" in low or f"_{tok}-" in low:
                band = tok
                break
        else:
            band = "full"
        out[band] = curve
    return out


def _fmt(curve: NonoCurve) -> str:
    lo, hi = (curve.freqs[0], curve.freqs[-1]) if curve.freqs else (0, 0)
    return (f"{os.path.basename(curve.path):<48} "
            f"{curve.kind:<22} n={len(curve):<4} "
            f"{lo:.0f}-{hi:.0f}Hz  v{curve.version or '?'}")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    if os.path.isdir(target):
        for band, curve in parse_nono_band_set(target).items():
            print(f"[{band:>6}] {_fmt(curve)}")
    else:
        print(_fmt(parse_nono_curve(target)))
