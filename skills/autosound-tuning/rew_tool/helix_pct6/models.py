"""Which ATF models this reader knows, and how sure it is about each.

Every model is read. What differs is how much of the reading has been checked: the container and the raw
inventory are the same for every file seen so far; the meaning of values (delay clock, channel layout, enum
codes) has been checked on the models in `VERIFIED_NAMES` only. Everything else is read at the user's own
risk and is marked so in the result.
"""

from dataclasses import dataclass
from typing import Optional

#: The models reading has been checked on (the user's word, 2026-11-20).
VERIFIED_NAMES = ("HELIX DSP ULTRA S", "HELIX NEXT V EIGHT DSP ULTIMATE")

#: Shown with every result, for every model, verified or not.
WARNING = (
    "Reading .pct6 has been checked on HELIX DSP ULTRA S and HELIX NEXT V EIGHT DSP ULTIMATE only. "
    "Any other model is read at your own risk. In every case, check the values against PC-Tool's own "
    "screens: PC-Tool versions change, and a new version may store a value differently."
)

#: PC-Tool versions whose files this package's tests read (a fact about the test set, not a limit).
PC_TOOL_VERSIONS_READ = ("6.03.03", "6.03.04", "6.04.01", "6.04.03", "6.05.01")


@dataclass(frozen=True)
class Model:
    dev: Optional[str]
    name: str
    verified: bool
    clock_hz: Optional[int]
    layout: Optional[str]
    note: str


MODELS = (
    Model("39", "HELIX DSP ULTRA S", True, 96000, "ultra-s",
          "57 mapping rules (50 confirmed, 6 assumption, 1 unknown), 15 one-change experiments, "
          "files from PC-Tool 6.03.03 to 6.05.01"),
    Model("44", "HELIX NEXT V EIGHT DSP ULTIMATE", True, None, "v-eight",
          "checked by the user (2026-11-20); Dev 44 and the channel layout pinned on his demo-mode save "
          "(testdata/helix-pct6/Helix-V8U.pct6, PC-Tool 6.05.01) against PC-Tool's screens: Virtual 1-14, "
          "Amp Out 1-8, Line Out 9-14; the file states no clock and none is checked, so delays are at an "
          "assumed 96 kHz"),
    Model("22", "HELIX DSP ULTRA", False, None, None,
          "named in the device list; no sample file"),
)


def lookup(dev: Optional[str]) -> Optional[Model]:
    for model in MODELS:
        if model.dev is not None and model.dev == dev:
            return model
    return None


def describe(dev: Optional[str]) -> dict:
    """The `device` block of a result: who the file says it is for, and how far that is checked."""
    model = lookup(dev)
    if model is None:
        return {"dev": dev, "name": None, "verified": False, "clock_hz": None, "clock_assumed_hz": 96000,
                "layout": None, "note": "this model is not checked: values are read with the HELIX DSP ULTRA S "
                                        "rules and may be wrong"}
    return {"dev": dev, "name": model.name, "verified": model.verified,
            "clock_hz": model.clock_hz, "clock_assumed_hz": None if model.clock_hz else 96000,
            "layout": model.layout, "note": model.note}
