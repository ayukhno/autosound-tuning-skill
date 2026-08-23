"""Protective filters: what was in the chain while measuring, and taking it back out.

A driver is often swept with a protective filter in the signal path — a high-pass so a sweep does
not throw a mid or a tweeter past its excursion limit. That filter is **in the recording**. It is
not part of the tune, and nothing downstream can tell by looking, because a protective `LR4 @100`
and a designed `LR4 @100` are the same filter.

**Why it is a phase problem and not a level problem.** A crossover slope does not only cut level
near its corner; it rotates phase far past it, and the rotation decays slowly. Measured with this
module's own maths on the reference car's actual protective set:

    HPF LR4 @100 Hz   at 320 Hz  (3.2x above)   ~52 deg still unwound
    LPF LR4 @500 Hz   at 160 Hz  (3.1x below)   ~53.5 deg

So a junction three-ish times away from a protective corner carries about 50 degrees that belongs
to the measuring rig rather than to the car. On the same data, the same junction read **-49 deg**
with the protective filter left in and **+3 deg** with it removed (cross-check runs 3/4,
2026-08-18) — the difference between "badly out of phase, fix it" and "leave it alone".

**Low-pass filters count too, and symmetrically.** An HPF rotates phase above its corner, an LPF
below its own; the numbers above are within 1.5 degrees of each other at the same ratio. A tool
that de-embedded only high-passes would clean half the problem and look like it had cleaned all of
it, which is worse than cleaning nothing.

## What gets recorded, and why the DEFAULT is "working"

**Any capture is a working capture unless somebody says otherwise** (the user, 2026-08-23). It
measures the system as configured, whatever filters are in it are part of the tune, and nothing is
de-embedded. Raw captures — a driver behind protection, before its crossover exists — are the
exception and there are usually one or two of them, so they are the ones that carry a flag.

That is the right way round: the common case costs no clicks, and a record only exists where it
says something. The record is per capture series, per channel, in the ledger's own crossover
vocabulary (`{f, type, slope}` / `"OFF"`), so there is no second dialect to keep in step.

⚠️ **The hole this leaves, named rather than papered over.** With "working" as the default, an
absent record means two different things: *this measured the tune* (intended) and *this was raw
and nobody pressed the button* (a mistake). The second is silent, and it is expensive — every
phase decision at a nearby junction is then out by ~50 degrees with nothing complaining.

It cannot be caught by looking at the filter, because a protective `LR4 @100` and a designed one
are identical. It CAN be caught by when the capture happened: a **baseline** sweep is taken before
any crossover has been designed, so a baseline capture with crossovers in force is protection
almost by definition. `should_de_embed(..., baseline=True)` returns `"check"` for exactly that
case — the one place a forgotten button is recoverable.

The flag belongs to the CAPTURE, not to the filter. The same 1 kHz high-pass can be protection
today and part of the finished crossover next week; what makes it protective is that it was not
part of the design when this sweep was taken.

⚠️ **Do not de-embed when verifying a finished tune.** There the filter is supposed to be there,
and removing it measures something nobody configured. De-embedding belongs to reading a driver's
own behaviour, not to checking a result.

stdlib + numpy/scipy (via `dsp_math`).
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import numpy as np

import dsp_math

#: How much the correction may lift any single bin. Below a protective corner the filter's response
#: goes to zero, so dividing by it is division by almost nothing: the noise floor comes up with the
#: signal and a 60 dB "recovery" is 60 dB of hiss shaped like a driver. Resonalyze caps at the same
#: 40 dB. The cap is not a detail — it is what stops the correction inventing a measurement.
MAX_BOOST_DB = 40.0

#: There is deliberately NO "far enough to ignore" RATIO here, because I guessed one and the maths
#: disagreed: 8x looked safe and an LR4 still leaves 20 deg there. Measured decay, this module's
#: own numbers, residual degrees at a distance from the corner:
#:
#:      ratio      2x    3x    4x    6x    8x   12x   16x   24x   32x
#:      LR2 (12)        36.9              14.2         7.1         3.6
#:      LR4 (24)  86.6  55.9  41.3  27.3  20.4  13.5  10.1   6.7   5.0
#:      LR6 (36)        78.0              28.7        14.3         7.1
#:
#: It falls roughly as 1/ratio, not off a cliff, and it scales with the slope — so a steep
#: protective filter is still worth ~14 deg sixteen times out. A caller decides against DEGREES
#: with `matters_at`, never against a distance: the same ratio means different things per slope,
#: and a ratio threshold would have quietly waved through the LR6 case.
FAR_DEGREES = 10.0


class ProtectiveError(ValueError):
    """The protective record cannot answer what was asked of it."""


def legs_of(record, channel):
    """The `{hp, lp}` in force for one channel, or `None` when NOBODY SAID.

    `None` and `{"hp": "OFF", "lp": "OFF"}` are different answers and the caller must treat them
    differently: the first is an unanswered question, the second is a measured fact that there was
    nothing in the chain. Collapsing them is how a tool comes to report "corrected" over data it
    never corrected.
    """
    channels = (record or {}).get("channels")
    if not isinstance(channels, dict) or channel not in channels:
        return None
    entry = channels[channel]
    if entry in ("OFF", "none", None):
        return {"hp": "OFF", "lp": "OFF"}
    if not isinstance(entry, dict):
        raise ProtectiveError(
            f"{channel!r}: expected {{hp, lp}} or \"OFF\", got {entry!r}")
    return {"hp": entry.get("hp", "OFF"), "lp": entry.get("lp", "OFF")}


def should_de_embed(record, channel, *, baseline=None):
    """Decide what to do with one channel's capture. `(action, detail)`.

    * `("no", reason)` — a working capture: it measured the system as configured, so whatever
      filters were in it belong there. This is the DEFAULT and it is an answer, not a shrug.
    * `("yes", legs)` — marked raw, and here is what to take out.
    * `("check", reason)` — it looks raw and is not marked. See below.

    `baseline` is the caller's answer to "was this taken before any crossover was designed?" — from
    the capture phase or the measurement's own `_N` version, which this module deliberately does
    not go looking for. Pass `True` for a phase-0 style capture.

    **Why `"check"` exists.** With "working" as the sensible default, a forgotten flag is silent
    and costs ~50 degrees at a nearby junction. Nothing in the data can reveal it — a protective
    `LR4 @100` and a designed one are the same filter. But a baseline sweep happens BEFORE a
    crossover exists, so filters in force during one are protection almost by definition. That is
    the single place the omission is recoverable, and it is worth a question rather than a guess:
    the answer is a person's, since only they know whether the button was missed.
    """
    legs = legs_of(record, channel)
    if legs is not None and any(_live(legs.get(k)) for k in ("hp", "lp")):
        return "yes", legs
    if legs is not None:
        return "no", ("marked raw, and the record says nothing was in the chain — measured "
                      "unfiltered, so there is nothing to remove")
    if baseline:
        return "check", (
            f"{channel!r} was captured at baseline — before any crossover was designed — and is "
            f"not marked raw. If a protective filter was in the chain it is unrecorded, and every "
            f"phase decision near it will be out by tens of degrees with nothing to show for it. "
            f"Was protection in force? If it was, record it; if it was not, say so explicitly.")
    return "no", ("not marked raw, so this measured the system as configured — whatever filters "
                  "are in it are part of the tune and must NOT be removed")


def _live(leg):
    """A leg that actually filters, or None. `"OFF"`/null/missing all mean no filter."""
    if not isinstance(leg, dict) or leg.get("f") in (None, 0):
        return None
    return leg


def response(freqs_hz, legs):
    """The complex response of the protective chain — the thing that is IN the recording."""
    h = np.ones(len(freqs_hz), dtype=complex)
    for kind in ("hp", "lp"):
        leg = _live((legs or {}).get(kind))
        if leg is None:
            continue
        h = h * dsp_math.xo_response(np.asarray(freqs_hz, float), float(leg["f"]),
                                     int(leg["slope"]), kind, leg.get("type", "LR"))
    return h


def matters_at(legs, freq_hz):
    """How much protective phase is still unwound at one frequency, in degrees.

    The number a gate should look at, and the reason the threshold is in DEGREES rather than in
    distance: ~50 deg at three times the corner reversed a real junction decision, and eight times
    out is still 20 deg for an LR4 and 29 for an LR6. See `FAR_DEGREES` for the measured decay —
    it falls as roughly 1/ratio, so "far enough" is not a property of distance alone.
    """
    h = response([freq_hz], legs)[0]
    if h == 0:
        return 180.0
    return float(abs(np.degrees(np.angle(h))))


def de_embed(freqs_hz, measured, legs, *, max_boost_db=MAX_BOOST_DB):
    """Take the protective chain back out of a measured complex response.

    `measured` is what REW gave: driver x protective. Returns
    `(corrected, info)` where `info` reports what was actually done — the boost cap is not a detail
    to hide, since inside the capped region the correction is deliberately incomplete and the phase
    there is not to be trusted.

    Raises rather than guessing when `legs` is `None`: that means nobody recorded what was in the
    chain, and a correction applied to an unknown chain is worse than none, because the result
    looks corrected.
    """
    if legs is None:
        raise ProtectiveError(
            "no protective record for this capture. Under the working-by-default rule that means "
            "it measured the system AS CONFIGURED, so there is nothing to take out and this "
            "function should not have been called — ask `should_de_embed` first. If the capture "
            "really was raw, the flag was missed, and correcting an unknown chain would produce "
            "data that merely LOOKS corrected")
    freqs = np.asarray(freqs_hz, float)
    measured = np.asarray(measured, dtype=complex)
    prot = response(freqs, legs)

    live = [k for k in ("hp", "lp") if _live(legs.get(k))]
    if not live:
        return measured.copy(), {"applied": [], "capped_below_hz": None, "capped_above_hz": None,
                                 "capped_bins": 0,
                                 "note": "the record says nothing was in the chain — returned "
                                         "unchanged, which is a measured fact and not a no-op"}

    mag = np.abs(prot)
    floor = 10.0 ** (-max_boost_db / 20.0)
    capped = mag < floor
    safe = np.where(capped, prot / np.maximum(mag, 1e-300) * floor, prot)
    corrected = measured / safe

    lo = hi = None
    if capped.any():
        idx = np.flatnonzero(capped)
        # Which SIDE the capping is on: below a high-pass corner, above a low-pass one.
        below = idx[freqs[idx] < np.median(freqs)]
        above = idx[freqs[idx] >= np.median(freqs)]
        lo = float(freqs[below].max()) if below.size else None
        hi = float(freqs[above].min()) if above.size else None
    return corrected, {
        "applied": live,
        "capped_bins": int(capped.sum()),
        "capped_below_hz": lo,
        "capped_above_hz": hi,
        "note": (f"correction limited to {max_boost_db:g} dB where the protective filter has "
                 f"almost no output; inside that region the phase is NOT recovered and must not "
                 f"be read as the driver's" if capped.any() else
                 "no bin needed more than the boost cap"),
    }


# ── selftest ───────────────────────────────────────────────────────────────────
def _selftest():
    freqs = np.geomspace(20, 20000, 800)

    # The numbers that forced this work, from this module's own maths rather than a report.
    hp = {"hp": {"f": 100, "type": "LR", "slope": 24}}
    lp = {"lp": {"f": 500, "type": "LR", "slope": 24}}
    at_320 = matters_at(hp, 320.0)
    at_160 = matters_at(lp, 160.0)
    assert 50 <= at_320 <= 55, at_320          # cross-check reported ~52
    assert 50 <= at_160 <= 56, at_160          # ~53.5, and the point is that it MATCHES
    # A low-pass rotates as hard as a high-pass at the same ratio from its corner. A tool that
    # de-embedded only high-passes would clean half the problem and look finished.
    assert abs(at_320 - at_160) < 3.0, (at_320, at_160)
    # ...and it decays SLOWLY, which is the part I got wrong by intuition: at eight times the
    # corner an LR4 still carries 20 deg, and a steeper one carries more. Pinned so nobody
    # reintroduces a "far enough" ratio -- it takes about 16x to reach FAR_DEGREES for LR4.
    assert 18 < matters_at(hp, 800.0) < 23, matters_at(hp, 800.0)
    steep = {"hp": {"f": 100, "type": "LR", "slope": 36}}
    assert matters_at(steep, 800.0) > matters_at(hp, 800.0), "a steeper filter reaches further"
    assert matters_at(hp, 1600.0) <= FAR_DEGREES + 0.5, matters_at(hp, 1600.0)
    assert matters_at(steep, 1600.0) > FAR_DEGREES, \
        "the same distance is NOT the same residual across slopes -- which is why the threshold " \
        "is in degrees and not in ratio"

    # Round trip: a known driver, measured through protection, comes back.
    driver = dsp_math.xo_response(freqs, 3000.0, 12, "lp", "BW")   # stands in for a real response
    legs = {"hp": {"f": 100, "type": "LR", "slope": 24}, "lp": "OFF"}
    measured = driver * response(freqs, legs)
    back, info = de_embed(freqs, measured, legs)
    band = freqs >= 150                        # above the cap region
    err_db = np.abs(20 * np.log10(np.abs(back[band]) / np.abs(driver[band])))
    err_deg = np.abs(np.degrees(np.angle(back[band] / driver[band])))
    assert err_db.max() < 0.01, err_db.max()
    assert err_deg.max() < 0.01, err_deg.max()
    assert info["applied"] == ["hp"], info

    # The cap engages below the corner and SAYS SO. Without it the correction would lift the noise
    # floor by 60 dB and hand back hiss shaped like a driver.
    assert info["capped_bins"] > 0 and info["capped_below_hz"] is not None, info
    assert "NOT recovered" in info["note"], info
    boost = np.abs(1.0 / response(freqs, legs))
    assert boost.max() > 10 ** (MAX_BOOST_DB / 20), "the uncapped boost really is that large"
    deep = freqs < 30
    lifted = np.abs(back[deep]) / np.abs(driver[deep])
    assert lifted.max() < 10 ** ((MAX_BOOST_DB + 0.1) / 20), "the cap must actually bind"

    # "Nobody said" is NOT "there was nothing". The first refuses; the second is a fact and a no-op.
    try:
        de_embed(freqs, measured, None)
    except ProtectiveError as exc:
        assert "should not have been called" in str(exc), exc
    else:
        raise AssertionError("an unrecorded chain must be refused, not silently uncorrected")

    # -- working by default, raw by exception (the user, 2026-08-23) ------------
    # The common case costs no clicks and is an ANSWER: a capture nobody marked measured the
    # system as configured, so its filters belong to the tune and must not be removed.
    act, why = should_de_embed({"channels": {}}, "m-L")
    assert act == "no" and "part of the tune" in why, (act, why)
    # A marked one carries what to take out.
    marked = {"channels": {"m-L": {"hp": {"f": 100, "type": "LR", "slope": 24}}}}
    act, got = should_de_embed(marked, "m-L")
    assert act == "yes" and got["hp"]["f"] == 100, (act, got)
    # Marked and explicitly empty is also an answer -- measured unfiltered, nothing to remove.
    act, why = should_de_embed({"channels": {"w-L": "OFF"}}, "w-L")
    assert act == "no" and "nothing was in the chain" in why, (act, why)

    # THE HOLE, and the one place it is recoverable. A default of "working" makes a forgotten flag
    # silent, and it costs ~50 deg. Nothing in the data can reveal it -- a protective LR4@100 and a
    # designed one are identical. But a BASELINE sweep predates any crossover, so filters in force
    # during one are protection almost by definition.
    act, why = should_de_embed({"channels": {}}, "m-L", baseline=True)
    assert act == "check" and "not marked raw" in why, (act, why)
    assert "Was protection in force?" in why, "the check must ASK, not decide"
    # ...and a baseline capture that IS marked needs no question -- otherwise the guard would fire
    # on every correctly-recorded baseline and be trained away within a week.
    assert should_de_embed(marked, "m-L", baseline=True)[0] == "yes"
    assert should_de_embed({"channels": {"w-L": "OFF"}}, "w-L", baseline=True)[0] == "no"
    same, info_off = de_embed(freqs, measured, {"hp": "OFF", "lp": "OFF"})
    assert np.allclose(same, measured) and info_off["applied"] == [], info_off
    assert "measured fact and not a no-op" in info_off["note"], info_off

    # The record's own vocabulary: absent channel = unasked, explicit OFF = answered.
    rec = {"series": "3", "channels": {
        "m-L": {"hp": {"f": 100, "type": "LR", "slope": 24}},
        "w-L": "OFF"}}
    assert legs_of(rec, "m-L")["hp"]["f"] == 100, legs_of(rec, "m-L")
    assert legs_of(rec, "m-L")["lp"] == "OFF", "a leg not named is not in force"
    assert legs_of(rec, "w-L") == {"hp": "OFF", "lp": "OFF"}, legs_of(rec, "w-L")
    assert legs_of(rec, "tw-L") is None, "a channel nobody answered for is None, not OFF"
    assert legs_of({}, "m-L") is None

    print(f"selftest OK -- HPF LR4@100 leaves {at_320:.1f} deg at 320 Hz and LPF LR4@500 leaves "
          f"{at_160:.1f} deg at 160 Hz (same ratio, so low-passes count too); round trip recovers "
          f"the driver to {err_db.max():.4f} dB / {err_deg.max():.4f} deg above the cap; the "
          f"{MAX_BOOST_DB:g} dB cap binds and is reported; unrecorded refuses, explicit OFF is a "
          f"fact")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        print(__doc__)
