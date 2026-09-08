"""Resonalyze Virtual DSP session (`resonalyze-virtual-crossover` v7..v10)  →  ledger rows.

The mirror of `resonalyze_ir.py`: that one writes REW measurements INTO Resonalyze, this one
reads a tune BACK OUT of it. The occasion was a Resonalyze Virtual DSP session another tuner
shares, computed over our own IRs; the point is that anybody's Virtual DSP session can be read as
a proposal against our own ledger, in one place both the terminal and a GUI call.

What comes out is `state/state.py` schema-v3 channel rows -- `{hp, lp, gain_db, ta_ms, polarity,
eq, status}` -- one per sourced leg, each with a machine-readable per-field verdict from the
project's DSP capability profile (`dsp_profile.py`). It stops there. Banking rows into a preset
is `state/apply.py`'s gated job and a tuning decision; this module only says what the session
asks for and whether the hardware can be made to do it.

Four things this file exists to get right, each of which a naive reader gets wrong:

  * **`crossoverKind` decides which edge is live, and the dormant edge still holds values.**
    A side with `crossoverKind: "LowPass"` carries a `highPassEdge` too, and in these sessions it
    is often the C# constructor's untouched default (`LinkwitzRiley 2000 Hz 24 dB/oct`, see
    `VirtualCrossoverChannelSettings`). The sub here reads `highPassEdge: BW 10 Hz 24 dB/oct`
    while its kind is `LowPass` -- i.e. his plan has NO subsonic filter. Import both edges and you
    have invented one. Dormant edges are kept out of the row and reported under `dormant`.

  * **The stereo scene fields are an AIM, not a stage.** `stereoSceneOffsetMs` and
    `stereoLevelDifferenceDb` are what Resonalyze's Auto delay / gain balance *targets* (its own
    comment: "the intentional level difference the Auto delay gain balance aims for"); the result
    is already sitting in the per-leg `gainDb`/`delayMs`. Adding them on top double-counts the
    scene. They travel in `scene` as provenance and touch no row.

  * **A capability the profile does not state is `unknown`, never `ok`.** Same rule as
    `references/core/estimator-scope.md` and the installer checker: a check whose input is missing
    must fail, not report "no objection". The live Helix profile declares a delay STEP and no
    delay MAX, so a delay is reported as "on the grid, ceiling not declared" -- not as fine.

  * **Nothing is rounded to fit.** A leg the target DSP cannot enter keeps the value the session
    asked for and is marked `enterable: false`. Silently rounding LR48 to the LR36 a Helix does
    have would put a filter nobody chose into a tune nobody could then explain.

`isTransparent` on a PEQ band is Resonalyze's DERIVED "contributes nothing" flag
(`EqualizationCurve.IsTransparent` = `GainDb == 0 || Q <= 0 || FrequencyHz <= 0`), not a user's
bypass switch -- it is recomputed here rather than trusted, and such bands are left out of `eq`
and counted in `dropped_eq_bands` instead of being mapped onto the ledger's `bypass`, which means
something else.

Q travels unchanged: Resonalyze holds a band's Q in the RBJ convention internally and only
restates it on EXPORT (`PeqQConvention`, `MeasurementSettingsFile.TargetDspQConvention`), and RBJ
is what Audiotec-Fischer (HELIX / MATCH / BRAX) reads -- DIMOSUS's own table says so. For a
target DSP on another convention the Q would need rescaling, and no profile field states a
convention today, so the report says which one it assumed rather than pretending the question
does not exist. Whoever adds that rescaling must skip SHELVES: a shelf's Q sets a knee, not a
bandwidth, so the conventions do not apply to it and Resonalyze's own `ToConvention` passes
shelves through untouched. Rescaling one silently widens it.

Format skew, seen in the wild and handled: in the v7 files the app writes, `enabled`/`bypass` sit
on the PAIR, while the fork checkout's `VirtualCrossoverChannelSettings` carries them on the SIDE.
Both are read, side first.

VERSIONS. The app's writer moved four times in three weeks -- v7 (22.08) → v8 (24.08, the per-side
all-pass stage became a band of the PEQ bank) → v9 (30.08, every block got a ZONE: front / rear /
center / sub) → v10 (05.09, the channel phase control, `phaseRotationDegrees`) -- and a reader
pinned to v7 refused every file the current app saves, correctly and uselessly (hub RES-008).
`migrate_session` now brings any v7..v10 document to v10 IN MEMORY by the app's own `Migrate`
steps, ported line for line (the header below pins them and `scripts/upstream-drift.py` compares
the format version on every run); the file on disk is never touched, and the report says which
steps ran and what each one guessed or dropped. A version above 10 is refused by its number.

What v9 and v10 add to a row: the block's `zone` travels on the leg (the ledger has no such field,
but it decides which crossover corner the phase control's angle is stated at), and a non-zero
`phaseRotationDegrees` becomes the row's `phase_deg`. The angle is stated AT the channel's
configured crossover -- the LP on a sub block, the HP on every other -- so when that edge is
dormant in the session (`crossoverKind` does not engage it) the row still carries it, with
`slope: "OFF"`: the ledger's own form of "configured, not active", which `predict._phase_reference`
reads and `predict._leg` keeps out of the chain. The check on that field names the one way this
goes wrong silently: the ledger picks the corner BY CHANNEL CODE (`sw…` reads the LP), the session
by zone, and a sub-zone leg bound to a code that is not a sub lands its angle on the wrong corner.

    resonalyze_vc.py <session.json> --project <dir>          # human report
    resonalyze_vc.py <session.json> --project <dir> --json    # the same as machine JSON
    resonalyze_vc.py --write-fixture                          # the synthetic v7 and v10 fixtures

Exit codes: 0 every check passed · 1 something the target DSP cannot enter · 2 nothing blocking
but something unverifiable (no profile, or a limit the profile does not declare).

stdlib only, py3.9+.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

# upstream: DIMOSUS/Resonalyze source/Tools/VirtualCrossover/VirtualCrossoverProjectFile.cs @ 319e873 (MIT) --
#   the session schema v7..v10 (`VirtualCrossoverChannelSettings`, `VirtualCrossoverChannelPairSettings`),
#   `Migrate` steps v7→v8 (the all-pass stage into the PEQ bank, `EqualizationCurve.MaxBandCount`),
#   v8→v9 (the zone) and v9→v10 (the phase control), `PhaseReferenceHz` (LP on a Sub block, HP
#   otherwise, AS CONFIGURED), `Validate()`'s ranges.
# format-version: 10 -- their `CurrentVersion`; `scripts/upstream-drift.py` reads it out of the
#   upstream file and names a mismatch as a drift of the FORMAT.
# deviation: reads and never writes -- the migration runs in memory and the file stays as it was;
#            their `LoadOrDefault` rewrites the project on the next save. See `migrate_session`.
# deviation: `IsTransparent` is recomputed here and a transparent band is DROPPED and listed,
#            where their chain carries it as a no-op -- see `_eq_bands`.
# deviation: a dormant reference edge under a non-zero angle is written into the row with
#            `slope: "OFF"` -- the ledger's form of "configured, not active"; theirs keeps both
#            edges on the side always. See `_leg` and `predict._phase_reference`.
# upstream: DIMOSUS/Resonalyze source/Tools/VirtualCrossover/VirtualCrossoverZone.cs @ f026276 (MIT) --
#   `VirtualCrossoverZones.GuessForLegacyPair` (the v9 step's zone guess) and the zone names.
CONVERTER = "autosound-tuning-skill rew_tool/resonalyze_vc.py"
CONVERTER_VERSION = "1.1 (2026-09-08, reads format v7..v10 as of Resonalyze 319e873, migrated in memory)"

FORMAT = "resonalyze-virtual-crossover"
SUPPORTED_VERSIONS = (7, 8, 9, 10)   #: what `validate_session` accepts; `migrate_session` brings all to
CURRENT_VERSION = 10                 #: ...this, their `CurrentVersion`
MAX_BAND_COUNT = 32                  #: `EqualizationCurve.MaxBandCount` -- the v7→v8 step's full-bank rule
ZONES = ("Front", "Rear", "Center", "Sub")   #: `VirtualCrossoverZone`, in their order
#: `PhaseRotationControl.MaximumDegrees`: 360 − 360/64. Range only, like their `Validate()`; the
#: 5.625° grid is the profile's business (`phase_control.step_deg`).
MAX_PHASE_DEG = 360.0 - 360.0 / 64.0

#: Resonalyze crossover family -> the ledger's short type code.
FAMILY_TO_TYPE = {
    "Butterworth": "BW",
    "LinkwitzRiley": "LR",
    "Bessel": "BE",
    "Chebyshev": "CHEBYSHEV",
}
#: Resonalyze PEQ band type -> `state.EQ_TYPES`. Since v8 the all-pass sections are bands of the
#: bank (`PeqBandType.AllPassFirstOrder` / `AllPassSecondOrder`); a first-order section takes no Q.
BAND_TO_EQ_TYPE = {"Peaking": "PK", "LowShelf": "LSH", "HighShelf": "HSH",
                   "AllPassFirstOrder": "APF1", "AllPassSecondOrder": "APF2"}
ALLPASS_BAND_TYPES = ("AllPassFirstOrder", "AllPassSecondOrder")
#: v7's per-side all-pass STAGE (`allPassType`) -> the v8 band type the migration writes.
ALLPASS_STAGE_TO_BAND = {"FirstOrder": "AllPassFirstOrder", "SecondOrder": "AllPassSecondOrder"}

CROSSOVER_KINDS = ("Off", "LowPass", "HighPass", "BandPass")

#: `StereoSceneOffsetMs` at or under this magnitude is the right-hand-drive zero marker, not an
#: offset -- Resonalyze writes 0.001 ms so a zero RHD scene still carries its layout in the sign
#: for builds older than the explicit flag (`VirtualCrossoverProjectFile.RhdZeroOffsetMarkerMs`).
RHD_ZERO_MARKER_MS = 0.001

OK, UNSUPPORTED, UNKNOWN = "ok", "unsupported", "unknown"


class SessionError(ValueError):
    """The file is not a Virtual DSP session this module can read."""


# ── reading the session ────────────────────────────────────────────────────────
def load_session(path):
    """Read and validate a session file. `SessionError` on anything unreadable."""
    try:
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
    except OSError as exc:
        raise SessionError(f"cannot read {path}: {exc}") from exc
    except ValueError as exc:
        raise SessionError(f"{path} is not JSON: {exc}") from exc
    return validate_session(doc, path)


def validate_session(doc, path="<session>"):
    """Refuse anything that is not a v7..v10 Virtual DSP session, loudly and by name.

    A v2-era file carries its channels in the legacy flat `channels` list rather than in `pairs`.
    That is refused rather than read as "a session with no legs": an empty result from a file that
    demonstrably describes a tune is the silent-zero failure this whole module is written against.
    """
    if not isinstance(doc, dict):
        raise SessionError(f"{path}: expected a JSON object, got {type(doc).__name__}")
    fmt = doc.get("format")
    if fmt != FORMAT:
        raise SessionError(f"{path}: format is {fmt!r}, expected {FORMAT!r}")
    version = doc.get("version")
    if version not in SUPPORTED_VERSIONS:
        raise SessionError(
            f"{path}: version {version!r}, this converter reads {list(SUPPORTED_VERSIONS)} "
            f"(Resonalyze 319e873 writes {CURRENT_VERSION}); a later number means the upstream "
            "writer moved -- `scripts/upstream-drift.py` names it")
    pairs = doc.get("pairs")
    if not isinstance(pairs, list):
        raise SessionError(f"{path}: 'pairs' must be a list, got {type(pairs).__name__}")
    if not pairs and doc.get("channels"):
        raise SessionError(
            f"{path}: no 'pairs', but the legacy flat 'channels' list has "
            f"{len(doc['channels'])} entr{'y' if len(doc['channels']) == 1 else 'ies'} -- this is "
            "a pre-pairs session and reading it as empty would lose the whole tune")
    return doc


def migrate_session(doc):
    """A validated v7..v10 document -> (a v10 COPY, the notes of what each step did).

    Their `Migrate`, ported step for step; the input is not touched. Every step is additive or a
    move, so a migrated session describes the same tune -- the two places that is not exactly
    true are said in the notes rather than left to be found: the v7→v8 step has to DROP a band
    when a full 32-band bank has no room for the all-pass stage (theirs drops the last
    gain-bearing band and tells the user; so does this), and the v8→v9 step GUESSES the zone
    from the mono flag and the filter (a stereo block is Front, a mono high-passed block is
    Center, any other mono block is Sub -- `VirtualCrossoverZones.GuessForLegacyPair`), which is
    right for most installs and wrong for a rear pair, and a wrong guess costs one combo box in
    their UI and one `zone` field here.
    """
    doc = json.loads(json.dumps(doc))
    notes = []
    version = doc.get("version")
    if version == 7:
        dropped = 0
        for index, pair in enumerate(doc.get("pairs") or []):
            for side_name in ("left", "right"):
                side = pair.get(side_name)
                if not isinstance(side, dict):
                    continue
                stage = ALLPASS_STAGE_TO_BAND.get(side.get("allPassType"))
                first = stage == "AllPassFirstOrder"
                f = _num(side.get("allPassFrequencyHz"), 0.0)
                q = 1.0 if first else _num(side.get("allPassQ"), 1.0)
                if stage and math.isfinite(f) and f > 0 and math.isfinite(q) and q > 0:
                    bands = side.setdefault("peqBands", [])
                    if not isinstance(bands, list):
                        bands = side["peqBands"] = []
                    if len(bands) >= MAX_BAND_COUNT:
                        last = max((i for i, b in enumerate(bands)
                                    if isinstance(b, dict) and b.get("type") not in ALLPASS_BAND_TYPES),
                                   default=-1)
                        if last >= 0:
                            gone = bands.pop(last)
                            dropped += 1
                            notes.append(
                                f"v7→v8 pair {index} {side_name}: the bank was full (32), so its "
                                f"last gain-bearing band ({_band_label(_band_from_raw(gone))}) was "
                                "dropped to make room for the all-pass stage -- a bell Auto Tune "
                                "can propose again, where an all-pass sits on a junction aligned by ear")
                    if len(bands) < MAX_BAND_COUNT:
                        bands.append({"frequencyHz": f, "q": q, "gainDb": 0.0, "type": stage,
                                      "isTransparent": False})
                elif side.get("allPassType") not in (None, "Off"):
                    notes.append(f"v7→v8 pair {index} {side_name}: all-pass stage "
                                 f"{side.get('allPassType')!r} at {f:g} Hz Q {q:g} is not a filter "
                                 "and was dropped, as their migration drops it")
                for key in ("allPassType", "allPassFrequencyHz", "allPassQ"):
                    side.pop(key, None)
        notes.insert(0, "v7→v8: each side's all-pass stage became a band of its PEQ bank"
                        + (f" ({dropped} full bank(s) lost a band for it)" if dropped else ""))
        doc["version"] = version = 8
    if version == 8:
        for index, pair in enumerate(doc.get("pairs") or []):
            if not isinstance(pair, dict):
                continue
            left = pair.get("left") if isinstance(pair.get("left"), dict) else {}
            pair["zone"] = guess_zone(bool(pair.get("mono")), left.get("crossoverKind", "Off"))
            notes.append(f"v8→v9 pair {index}: zone GUESSED as {pair['zone']} from "
                         f"mono={bool(pair.get('mono'))} and the left side's crossoverKind "
                         f"{left.get('crossoverKind', 'Off')!r} -- a rear pair reads as Front here")
        doc["version"] = version = 9
    if version == 9:
        notes.append("v9→v10: the channel phase control is absent, so every side opens with no "
                     "rotation (phase_deg 0)")
        doc["version"] = version = 10
    return doc, notes


def guess_zone(mono, mono_side_kind):
    """`VirtualCrossoverZones.GuessForLegacyPair`: a stereo block is Front; a mono block that
    plays UP the spectrum (high-passed) is a Center, any other mono block is the Sub."""
    if not mono:
        return "Front"
    return "Center" if mono_side_kind == "HighPass" else "Sub"


def scene_of(doc):
    """The session-wide context a row cannot carry: calibration, stereo scene, target, smoothing.

    `stereo_scene_offset_ms` is the layout-neutral MAGNITUDE and `stereo_right_hand_drive` the
    layout, reconciled exactly as Resonalyze does it: the sign on the wire IS the layout for
    builds older than the flag, and a zero RHD offset is written as a tiny negative marker that
    reads back as zero.
    """
    raw_offset = _num(doc.get("stereoSceneOffsetMs"), 0.0)
    magnitude = 0.0 if abs(raw_offset) <= RHD_ZERO_MARKER_MS else abs(raw_offset)
    rhd = bool(doc.get("stereoRightHandDrive")) or raw_offset < 0
    # The level difference's sign is a layout flag too, not physics. It is stored L-R, but the
    # sign is CHOSEN from the layout (LHD negative, RHD positive) while the UI edits a
    # non-negative near-side cut. Read as plain L-R it misreports every right-hand-drive session,
    # so both readings travel: the wire value, and the cut with the side it lands on named.
    raw_level = _num(doc.get("stereoLevelDifferenceDb"), 0.0)
    return {
        "calibration_id": doc.get("calibrationId"),
        "stereo_scene_offset_ms": magnitude,
        "stereo_right_hand_drive": rhd,
        "stereo_level_difference_db": raw_level,
        "stereo_near_side_cut_db": abs(raw_level),
        "stereo_near_side": "right" if rhd else "left",
        "target_level_db": _num(doc.get("targetLevelDb"), 0.0),
        "target": doc.get("target"),
        "smoothing_inverse_octaves": doc.get("smoothingInverseOctaves"),
        "psychoacoustic_smoothing": doc.get("psychoacousticSmoothing"),
        "saved_at_utc": doc.get("savedAtUtc"),
        "note": "the stereo scene offset and level difference are what Resonalyze's Auto delay "
                "and gain balance AIM for; the result is already in each leg's gain_db/ta_ms. "
                "Do not apply them a second time.",
    }


def legs_of(doc):
    """One entry per side that actually has a measurement behind it, in pair order.

    A side with `hasSource` false is not a channel at all -- the mono sub pair here has an empty
    right side -- and is skipped rather than emitted as a row of defaults.
    """
    if doc.get("version") != CURRENT_VERSION:
        doc, _ = migrate_session(doc)
    out = []
    for index, pair in enumerate(doc.get("pairs") or []):
        if not isinstance(pair, dict):
            continue
        mono = bool(pair.get("mono"))
        for side in ("left", "right"):
            raw = pair.get(side)
            if not isinstance(raw, dict) or not _has_source(raw):
                continue
            if mono and side == "right":
                # A mono pair computes from its left set on both sides (`SideFor`); a right side
                # carrying a source anyway would be a second row for one driver.
                continue
            out.append(_leg(index, side, mono, pair, raw))
    return out


def _has_source(side):
    """Resonalyze's own `HasSource`: a history id OR a non-blank file path."""
    if side.get("historyEntryId"):
        return True
    path = side.get("sourceFilePath")
    return isinstance(path, str) and path.strip() != ""


def _leg(pair_index, side, mono, pair, raw):
    """One side, split into what the ledger takes and what only travels alongside it."""
    kind = raw.get("crossoverKind", "Off")
    if kind not in CROSSOVER_KINDS:
        raise SessionError(
            f"pair {pair_index} {side}: crossoverKind {kind!r} is not one of {CROSSOVER_KINDS}")
    live_lp = kind in ("LowPass", "BandPass")
    live_hp = kind in ("HighPass", "BandPass")
    zone = pair.get("zone", "Front")
    if zone not in ZONES:
        raise SessionError(f"pair {pair_index}: zone {zone!r} is not one of {ZONES}")
    phase_deg = _num(raw.get("phaseRotationDegrees"), 0.0)
    if not math.isfinite(phase_deg) or phase_deg < 0 or phase_deg > MAX_PHASE_DEG:
        raise SessionError(f"pair {pair_index} {side}: phaseRotationDegrees {phase_deg!r} is "
                           f"outside 0..{MAX_PHASE_DEG:g} (their Validate() refuses it too)")

    eq, dropped = _eq_bands(raw)
    row = {
        "hp": _edge(raw.get("highPassEdge")) if live_hp else None,
        "lp": _edge(raw.get("lowPassEdge")) if live_lp else None,
        "gain_db": _num(raw.get("gainDb"), 0.0),
        "ta_ms": _num(raw.get("delayMs"), 0.0),
        "polarity": "INV" if raw.get("invertPolarity") else "NORM",
        "phase_deg": phase_deg,
        "eq": eq,
        "status": "proposed",
    }
    # What the file carries and the tune does NOT use. Reported so a reader can see that the
    # values exist and were left out on purpose, rather than wondering whether they were missed.
    dormant = {}
    if not live_hp and raw.get("highPassEdge"):
        dormant["hp"] = _edge(raw["highPassEdge"])
    if not live_lp and raw.get("lowPassEdge"):
        dormant["lp"] = _edge(raw["lowPassEdge"])
    # The phase control's angle is stated AT a crossover corner: the LP on a Sub block, the HP on
    # every other, AS CONFIGURED whatever the kind engages (`PhaseReferenceHz`; the Helix bench,
    # fact 6). A dormant reference is therefore still the reference, and the row has to carry
    # it or the angle is not a filter -- so it goes into the row with `slope: "OFF"`, the
    # ledger's form of "configured, not active", which `predict._phase_reference` reads and
    # `predict._leg` keeps out of the chain. Only under a non-zero angle: a dormant edge with
    # nothing stated at it stays out, as before.
    ref_kind = "lp" if zone == "Sub" else "hp"
    phase_reference = None
    if phase_deg:
        edge = _edge(raw.get("lowPassEdge" if ref_kind == "lp" else "highPassEdge"))
        phase_reference = {"kind": ref_kind, "hz": edge["f"], "dormant": row[ref_kind] is None}
        if row[ref_kind] is None:
            row[ref_kind] = dict(edge, slope="OFF")
            dormant.pop(ref_kind, None)

    display = raw.get("displayName") or ""
    return {
        "pair": pair_index,
        "side": side,
        "mono": mono,
        # v7 keeps enable/bypass on the PAIR, and only there. Schema v7 (upstream bcf6cc3,
        # 2026-08-22) moved them off the side, and its migration NULLS the side copies after
        # folding them, so in a v7 file the side simply has no such key. Reading the side first
        # and defaulting a missing key to "enabled" would turn every pair-level mute into a
        # playing channel -- a muted leg entering the ledger as live is the one direction of this
        # error a tuner cannot see coming. Version decides; there is no fallback chain.
        # (Folding for a v6 file, if this ever reads one, is not a plain AND: enabled is AND over
        # the loaded sides, bypass is OR -- the louder answer wins, because a mute lost in a
        # migration is invisible. `SUPPORTED_VERSIONS` gates that door shut for now.)
        "enabled": bool(pair.get("enabled", True)),
        "bypass": bool(pair.get("bypass", False)),
        "display_name": display,
        "source_relative_path": raw.get("sourceRelativePath"),
        "source_file_path": raw.get("sourceFilePath"),
        "peq_source_name": raw.get("peqSourceName"),
        "peq_preamp_db": _num(raw.get("peqPreampDb"), 0.0),
        "crossover_kind": kind,
        "zone": zone.lower(),
        "phase_reference": phase_reference,
        "channel_hint": channel_hint(display or raw.get("sourceRelativePath") or ""),
        "channel": None,
        "row": row,
        "dormant": dormant,
        "dropped_eq_bands": dropped,
    }


def _edge(raw):
    """One crossover edge as a ledger leg: `{f, type, slope}`, plus the family verbatim.

    `family` is kept beside the short code because the code is lossy in one direction that
    matters: a Chebyshev edge also has a `ripple_db` the ledger has no field for, and dropping the
    original name would make that invisible.
    """
    if not isinstance(raw, dict):
        raise SessionError(f"a crossover edge must be an object, got {raw!r}")
    family = raw.get("family")
    leg = {
        "f": _num(raw.get("frequencyHz"), None),
        "type": FAMILY_TO_TYPE.get(family, family),
        "slope": raw.get("slopeDbPerOctave"),
        "family": family,
    }
    if family == "Chebyshev":
        leg["ripple_db"] = _num(raw.get("rippleDb"), None)
    return leg


def _eq_bands(side):
    """PEQ bands plus the all-pass stage, as ledger `eq` entries.

    A band Resonalyze itself would skip (`IsTransparent`) is left out and listed separately: it
    changes no response, and carrying it would eat a hardware EQ slot to do nothing. The flag is
    RECOMPUTED from the numbers rather than read from the file -- it is a derived C# property that
    happens to serialize, so a stale one in a hand-edited file must not decide anything.
    """
    bands, dropped = [], []
    for i, raw in enumerate(side.get("peqBands") or []):
        if not isinstance(raw, dict):
            raise SessionError(f"peqBands[{i}] must be an object, got {raw!r}")
        entry = _band_from_raw(raw)
        entry["i"] = len(bands) + 1
        # Their `IsTransparent`: `Q <= 0 || FrequencyHz <= 0 || (GainDb == 0 && !Type.IsAllPass())`
        # -- an all-pass has no gain by construction and is anything but transparent.
        if entry["f"] <= 0 or entry["_q"] <= 0 or (entry["_gain"] == 0 and entry["type"] not in ("APF1", "APF2")):
            dropped.append(dict(_ledger_band(entry), reason="transparent: contributes nothing"))
            continue
        bands.append(_ledger_band(entry))
    return bands, dropped


def _band_from_raw(raw):
    """One `peqBands[]` entry as read, before the ledger's shape is decided."""
    kind = raw.get("type", "Peaking")
    return {"type": BAND_TO_EQ_TYPE.get(kind, kind), "f": _num(raw.get("frequencyHz"), 0.0),
            "_gain": _num(raw.get("gainDb"), 0.0), "_q": _num(raw.get("q"), 0.0)}


def _ledger_band(entry):
    """The ledger's band: a bell or shelf carries gain and Q; an all-pass carries neither gain
    nor -- for a first-order section, a single real pole -- a Q (the file stores the 1.0 the
    section ignores). The ledger's `q` is optional for exactly that case."""
    band = {"type": entry["type"], "f": entry["f"], "i": entry.get("i")}
    if entry["type"] == "APF1":
        return band
    if entry["type"] == "APF2":
        band["q"] = entry["_q"]
        return band
    band.update({"gain_db": entry["_gain"], "q": entry["_q"]})
    return band


def _num(value, default):
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) \
        else default


# ── binding legs to our channels ───────────────────────────────────────────────
def channel_hint(name):
    """The channel token inside a Resonalyze IR filename, or "" when there is none.

    `Resonalyze-IR-2026-08-20_12-35-42_w_L.json` -> `w_L`, which is exactly the `id` our
    `project.json` keeps beside the display code `w-L`. A trailing measurement tag survives
    (`..._m_L-ctl1.json` -> `m_L-ctl1`) because stripping it here would be this module guessing at
    naming; `bind_channels` resolves the longest matching prefix through `project.py` instead,
    which is the one place that knows a project's real names.
    """
    if not isinstance(name, str) or not name.strip():
        return ""
    base = os.path.basename(name.replace("\\", "/"))
    for suffix in (".json",):
        if base.lower().endswith(suffix):
            base = base[: -len(suffix)]
    # Resonalyze names a capture `Resonalyze-IR-<date>_<time>_<channel>`: the channel is whatever
    # follows the time field. Anything not shaped like that is handed back whole rather than
    # chopped on a guess.
    parts = base.split("_")
    if len(parts) >= 3 and parts[0].startswith("Resonalyze-IR"):
        return "_".join(parts[2:])
    return base


def bind_channels(legs, proj=None, mapping=None):
    """Give each leg the channel code it belongs to. Explicit mapping wins; nothing is guessed.

    Two sources, in order. An explicit `mapping` (hint or display name -> code) is taken as given
    -- that is the caller having asked a human. Otherwise the hint is resolved through
    `project.resolve_channel`, which already answers "which channel is this name?" through current
    `code`, then `id`, then `previous_names` (SCR-039) -- the same three lookups a ledger row key
    goes through, so a channel renamed after the measurement was taken still lands. A hint with a
    trailing measurement tag (`m_L-ctl1`) is retried on progressively shorter prefixes at the `-`
    boundaries, so the tag does not have to be known here.

    A leg nothing matches keeps `channel: None`. An unknown name is not this module's to invent --
    the caller either asks or refuses, and both are better than a row filed under a wrong driver.
    """
    mapping = mapping or {}
    for leg in legs:
        hint = leg.get("channel_hint") or ""
        explicit = mapping.get(hint) or mapping.get(leg.get("display_name"))
        if explicit:
            leg["channel"] = explicit
            leg["channel_bound_by"] = "mapping"
            continue
        if proj is None:
            continue
        for candidate in _hint_prefixes(hint):
            row = proj.resolve_channel(candidate)
            if row is not None:
                leg["channel"] = row.get("code")
                leg["channel_bound_by"] = f"project.json ({candidate})"
                break
    return legs


def _hint_prefixes(hint):
    """`m_L-ctl1` -> `m_L-ctl1`, `m_L`. Longest first, so a real channel named with a `-` wins."""
    if not hint:
        return []
    parts = hint.split("-")
    return ["-".join(parts[:n]) for n in range(len(parts), 0, -1)]


# ── what the target DSP can actually be told ───────────────────────────────────
def _verdict(channel, field, wanted, verdict, reason, verified=(), unverified=()):
    """One field's answer: can this DSP be told this, yes / no / could-not-establish.

    `verified` and `unverified` name the individual limits behind the verdict, because "unknown"
    on its own is not actionable. The live Helix profile states a crossover STEP and no crossover
    RANGE, so every corner in a session comes back unverifiable -- true, and useless unless the
    reader can see that the family and the slope WERE checked and it is only the range that is
    missing. It also says exactly which profile key would turn the answer green, which is the
    difference between a report and a shrug.
    """
    return {
        "channel": channel,
        "field": field,
        "wanted": wanted,
        "verdict": verdict,
        "enterable": {OK: True, UNSUPPORTED: False, UNKNOWN: None}[verdict],
        "reason": reason,
        "verified": list(verified),
        "unverified": list(unverified),
    }


def _on_grid(value, step):
    """Is `value` an exact multiple of `step`? Tolerant of binary float dust, not of real error."""
    if not step:
        return True
    ratio = value / step
    return abs(ratio - round(ratio)) <= 1e-6


def check_leg(leg, profile=None, group_id="physical_outputs"):
    """Every per-field verdict for one leg against a DSP capability profile.

    Profile-driven, not Helix-shaped: the limits come from `dsp_profile.py`'s declared structure
    (`groups[].crossover_filters`, `groups[].eq`, `parametric_eq`, `delay`, `polarity`), so the
    same code answers for a MUSWAY. Whatever the profile does not declare comes back `unknown`
    with the reason naming the missing key -- a limit nobody wrote down has not been checked, and
    saying so is the difference between this and a rubber stamp.
    """
    channel = leg.get("channel") or leg.get("channel_hint") or f"pair{leg['pair']}.{leg['side']}"
    out = []
    group = _group(profile, group_id)
    if group is None:
        why = ("no DSP profile given" if profile is None
               else f"profile declares no {group_id!r} group")
        for field in ("hp", "lp", "gain_db", "ta_ms", "polarity", "eq"):
            out.append(_verdict(channel, field, _wanted(leg, field), UNKNOWN, why,
                                unverified=[f"groups[{group_id}]"]))
        return out

    inner = _unwrap_profile(profile)
    out += _check_crossovers(leg, channel, group)
    out += _check_eq(leg, channel, group, inner)
    out += _check_delay(leg, channel, inner)
    out += _check_gain(leg, channel, inner)
    out += _check_polarity(leg, channel, inner)
    out += _check_phase(leg, channel, inner)
    out += _check_preamp(leg, channel)
    out += _check_state(leg, channel)
    return out


def _ledger_reads_lp(code):
    """Which corner the LEDGER states a `phase_deg` at: the LP on a channel whose code says sub,
    the HP on every other. The same one-line rule as `predict._is_sub` -- kept here rather than
    imported so this module stays stdlib-only; the selftest binds the two when numpy is about."""
    return str(code or "").lower().startswith(("sw", "sub"))


def _check_phase(leg, channel, inner):
    """A non-zero angle against `phase_control` -- range and step, like a delay -- and against
    the one thing a profile cannot know: WHICH corner the ledger will read it at.

    Resonalyze states the angle at the LP of a Sub block and the HP of any other (`zone`); the
    ledger, having no zone, picks the corner from the channel CODE (`predict._is_sub`). A sub
    block bound to `m-L`, or a front block bound to `sw`, lands the same number on the other
    corner -- a different filter, applied silently. Refused by name; an unbound leg cannot be
    checked and says so.
    """
    deg = leg["row"].get("phase_deg") or 0.0
    if not deg:
        return []
    ref = leg.get("phase_reference") or {}
    wanted = (f"{_g(deg)} deg @ {ref.get('kind', '?').upper()} {_g(ref.get('hz'))} Hz"
              + (" (that edge is dormant in the session; written with slope OFF)" if ref.get("dormant") else ""))
    out = []
    control = inner.get("phase_control") if isinstance(inner, dict) else None
    if not isinstance(control, dict):
        out.append(_verdict(channel, "phase_deg", wanted, UNKNOWN,
                            "profile has no 'phase_control' block", unverified=["phase_control"]))
    else:
        rng, step = control.get("range_deg"), control.get("step_deg")
        verified, unverified = [], []
        if isinstance(rng, list) and len(rng) == 2:
            if not (rng[0] <= deg <= rng[1]):
                return [_verdict(channel, "phase_deg", wanted, UNSUPPORTED,
                                 f"outside the DSP's {_g(rng[0])}..{_g(rng[1])} deg range")]
            verified.append(f"within {_g(rng[0])}..{_g(rng[1])} deg")
        else:
            unverified.append("phase_control.range_deg")
        if step is None:
            unverified.append("phase_control.step_deg")
        elif not _on_grid(deg, step):
            return [_verdict(channel, "phase_deg", wanted, UNSUPPORTED,
                             f"not a multiple of the DSP's {_g(step)} deg step", verified)]
        else:
            verified.append(f"on the {_g(step)} deg grid")
        if unverified:
            out.append(_verdict(channel, "phase_deg", wanted, UNKNOWN,
                                (("; ".join(verified) + " -- but ") if verified else "")
                                + "the profile states no "
                                + ", ".join(k.split(".")[-1] for k in unverified),
                                verified, unverified))
        else:
            out.append(_verdict(channel, "phase_deg", wanted, OK, "; ".join(verified), verified))
    # The corner: the session's zone against the ledger's code rule.
    code = leg.get("channel")
    session_lp = ref.get("kind") == "lp"
    if not code:
        out.append(_verdict(channel, "phase_deg.reference", wanted, UNKNOWN,
                            "no channel bound, so which corner the ledger reads the angle at "
                            "(the LP on a `sw…` code, the HP otherwise) is not decided yet",
                            unverified=["channel binding"]))
    elif _ledger_reads_lp(code) != session_lp:
        out.append(_verdict(channel, "phase_deg.reference", wanted, UNSUPPORTED,
                            f"the session states the angle at the {'LP' if session_lp else 'HP'} "
                            f"(zone {leg.get('zone')}), but the ledger reads phase_deg on "
                            f"{code!r} at the {'LP' if _ledger_reads_lp(code) else 'HP'} -- the same "
                            "number would become a different filter; rebind, or leave the angle out"))
    else:
        out.append(_verdict(channel, "phase_deg.reference", wanted, OK,
                            f"the ledger reads {code!r}'s angle at the same corner the session "
                            f"states it ({'LP' if session_lp else 'HP'})"))
    return out


def _check_crossovers(leg, channel, group):
    out = []
    xo = group.get("crossover_filters")
    for field in ("hp", "lp"):
        edge = leg["row"].get(field)
        if edge is None:
            continue
        wanted = f"{edge['type']}{edge['slope']} @ {_g(edge['f'])} Hz"
        if not isinstance(xo, dict):
            out.append(_verdict(channel, field, wanted, UNKNOWN,
                                "profile group declares no 'crossover_filters'",
                                unverified=["crossover_filters"]))
            continue
        types = xo.get("types")
        if not isinstance(types, dict):
            out.append(_verdict(channel, field, wanted, UNKNOWN,
                                "crossover_filters declares no 'types'",
                                unverified=["crossover_filters.types"]))
            continue
        spec = types.get(edge["type"])
        if spec is None:
            out.append(_verdict(channel, field, wanted, UNSUPPORTED,
                                f"this DSP has no {edge['type']} crossover "
                                f"(it offers {', '.join(sorted(types))})"))
            continue
        orders = (spec or {}).get("orders_db_per_oct")
        if not isinstance(orders, list):
            out.append(_verdict(channel, field, wanted, UNKNOWN,
                                f"profile states no orders_db_per_oct for {edge['type']}",
                                [f"{edge['type']} is offered"],
                                [f"crossover_filters.types.{edge['type']}.orders_db_per_oct"]))
        elif edge["slope"] not in orders:
            out.append(_verdict(
                channel, field, wanted, UNSUPPORTED,
                f"{edge['type']} is offered at {'/'.join(str(o) for o in orders)} dB/oct, "
                f"not {edge['slope']}", [f"{edge['type']} is offered"]))
        else:
            # A family whose own parameters are unstated is NOT determined by family and slope
            # alone. Chebyshev is the live case: the hardware offers it, and `ripple_db` is null
            # because an experiment was run and could not identify the maths (user, 2026-08-23) —
            # so we cannot say what this filter DOES, only that it can be entered. Reporting that
            # as `ok` would be the profile getting more agreeable where it is least understood.
            missing = [k for k, v in (spec or {}).items() if v is None]
            if missing:
                out.append(_verdict(
                    channel, field, wanted, UNKNOWN,
                    f"{edge['type']}{edge['slope']} can be ENTERED, but this family's "
                    f"{', '.join(missing)} is unstated, so what the filter does is not "
                    f"determined — it cannot be modelled, predicted or checked against a target",
                    [f"{edge['type']}{edge['slope']} is offered"],
                    [f"crossover_filters.types.{edge['type']}.{k}" for k in missing]))
                continue
            out.append(_check_corner(channel, field, wanted, edge, xo,
                                     [f"{edge['type']}{edge['slope']} is offered"]))
    return out


def _check_corner(channel, field, wanted, edge, xo, verified):
    """The family and slope are offered; is the corner frequency itself enterable?"""
    freq = edge.get("f")
    if freq is None:
        return _verdict(channel, field, wanted, UNSUPPORTED, "the edge carries no frequency",
                        verified)
    unverified = []
    rng = xo.get("corner_freq_range_hz")
    if isinstance(rng, list) and len(rng) == 2:
        if not (rng[0] <= freq <= rng[1]):
            return _verdict(channel, field, wanted, UNSUPPORTED,
                            f"corner outside the DSP's {_g(rng[0])}-{_g(rng[1])} Hz range",
                            verified)
        verified.append(f"corner within {_g(rng[0])}-{_g(rng[1])} Hz")
    else:
        unverified.append("crossover_filters.corner_freq_range_hz")

    step = xo.get("corner_freq_step_hz")
    if step is None:
        unverified.append("crossover_filters.corner_freq_step_hz")
    elif not _on_grid(freq, step):
        return _verdict(channel, field, wanted, UNSUPPORTED,
                        f"corner is not a multiple of the DSP's {_g(step)} Hz step", verified)
    else:
        verified.append(f"corner on the {_g(step)} Hz grid")

    if unverified:
        return _verdict(channel, field, wanted, UNKNOWN,
                        f"{'; '.join(verified)} -- but the profile states no "
                        f"{', '.join(k.split('.')[-1] for k in unverified)}",
                        verified, unverified)
    return _verdict(channel, field, wanted, OK, "; ".join(verified), verified)


def _check_eq(leg, channel, group, inner):
    bands = leg["row"].get("eq") or []
    out = []
    eq = group.get("eq")
    if not isinstance(eq, dict):
        return [_verdict(channel, "eq", f"{len(bands)} bands", UNKNOWN,
                         "profile group declares no 'eq'", unverified=["eq"])]
    limit = eq.get("bands_per_channel")
    if limit is None:
        out.append(_verdict(channel, "eq", f"{len(bands)} bands", UNKNOWN,
                            "profile states no bands_per_channel",
                            unverified=["eq.bands_per_channel"]))
    elif len(bands) > limit:
        out.append(_verdict(channel, "eq", f"{len(bands)} bands", UNSUPPORTED,
                            f"this DSP has {limit} bands per channel"))
    else:
        out.append(_verdict(channel, "eq", f"{len(bands)} bands", OK,
                            f"within the DSP's {limit} bands per channel"))

    allowed = eq.get("band_types")
    peq = inner.get("parametric_eq") if isinstance(inner, dict) else None
    for band in bands:
        field = f"eq[{band.get('i')}]"
        wanted = _band_label(band)
        if not isinstance(allowed, list):
            out.append(_verdict(channel, field, wanted, UNKNOWN,
                                "profile states no band_types",
                                unverified=["eq.band_types"]))
        elif band["type"] not in allowed:
            out.append(_verdict(channel, field, wanted, UNSUPPORTED,
                                f"this DSP has no {band['type']} band "
                                f"(it offers {', '.join(allowed)})"))
        else:
            out += _check_band_numbers(channel, field, wanted, band, peq)
    return out


def _check_band_numbers(channel, field, wanted, band, peq):
    """Frequency / gain / Q of one band against `parametric_eq`'s ranges and steps.

    Q can be bounded PER BAND TYPE. One range for every type is wrong on real hardware, and the
    bench of 2026-09-01 measured it: a Helix PC-Tool takes a bell's Q up to 50 and a SHELF's Q only
    within 0.3 .. 2 (hub #36 / RES-002). Checked against the single `q_range`, a legitimate shelf
    at Q 0.3 reads as out of range while a shelf at Q 30 -- which the processor will not accept --
    passes. So `parametric_eq.q_range_by_type` (keyed by the ledger's own type names, `PK` / `LSH` /
    `HSH` / `APF2`) overrides `q_range` for the types it names, and nothing changes for a profile
    that does not declare one.
    """
    if not isinstance(peq, dict):
        return [_verdict(channel, field, wanted, UNKNOWN,
                         "profile has no 'parametric_eq' block, so the band's numbers "
                         "cannot be checked", unverified=["parametric_eq"])]
    by_type = peq.get("q_range_by_type")
    q_override = by_type.get(band.get("type")) if isinstance(by_type, dict) else None
    problems, verified, unverified = [], [], []
    for key, value, rng_key, step_key, unit in (
        ("frequency", band.get("f"), "freq_range_hz", "freq_step_hz", "Hz"),
        ("gain", band.get("gain_db"), "gain_range_db", "gain_step_db", "dB"),
        ("Q", band.get("q"), "q_range", "q_step", ""),
    ):
        if value is None:                     # an APF1 has no Q and no gain -- not a gap
            continue
        rng, step = peq.get(rng_key), peq.get(step_key)
        if key == "Q" and isinstance(q_override, list) and len(q_override) == 2:
            rng = q_override
        if isinstance(rng, list) and len(rng) == 2:
            if not (rng[0] <= value <= rng[1]):
                problems.append(f"{key} {_g(value)}{unit} outside {_g(rng[0])}..{_g(rng[1])}")
                continue
            verified.append(f"{key} within {_g(rng[0])}..{_g(rng[1])}")
        else:
            unverified.append(f"parametric_eq.{rng_key}")
        if step is None:
            unverified.append(f"parametric_eq.{step_key}")
        elif not _on_grid(value, step):
            problems.append(f"{key} {_g(value)}{unit} off the {_g(step)}{unit} step")
        else:
            verified.append(f"{key} on the {_g(step)}{unit} step")
    if problems:
        return [_verdict(channel, field, wanted, UNSUPPORTED, "; ".join(problems), verified)]
    if unverified:
        return [_verdict(channel, field, wanted, UNKNOWN,
                         "within every stated limit, but the profile states no "
                         + ", ".join(sorted({k.split(".")[-1] for k in unverified})),
                         verified, unverified)]
    return [_verdict(channel, field, wanted, OK, "within the DSP's EQ ranges and steps",
                     verified)]


def _check_delay(leg, channel, inner):
    value = leg["row"].get("ta_ms")
    wanted = f"{_g(value)} ms"
    delay = inner.get("delay") if isinstance(inner, dict) else None
    if not isinstance(delay, dict):
        return [_verdict(channel, "ta_ms", wanted, UNKNOWN, "profile has no 'delay' block",
                         unverified=["delay"])]
    ceiling = delay.get("max_ms")
    step = delay.get("step_ms")
    verified, unverified = [], []
    if ceiling is None:
        unverified.append("delay.max_ms")
    elif value > ceiling:
        return [_verdict(channel, "ta_ms", wanted, UNSUPPORTED,
                         f"beyond the DSP's {_g(ceiling)} ms maximum")]
    else:
        verified.append(f"under {_g(ceiling)} ms")
    if step is None:
        unverified.append("delay.step_ms")
    elif not _on_grid(value, step):
        return [_verdict(channel, "ta_ms", wanted, UNSUPPORTED,
                         f"not a multiple of the DSP's {_g(step)} ms step", verified)]
    else:
        verified.append(f"on the {_g(step)} ms grid")
    if unverified:
        return [_verdict(channel, "ta_ms", wanted, UNKNOWN,
                         (("; ".join(verified) + " -- but ") if verified else "")
                         + "the profile states no "
                         + ", ".join(k.split(".")[-1] for k in unverified),
                         verified, unverified)]
    return [_verdict(channel, "ta_ms", wanted, OK, "; ".join(verified), verified)]


def _check_gain(leg, channel, inner):
    """Channel gain -- NOT the EQ's gain, which `parametric_eq` covers and this must not borrow."""
    value = leg["row"].get("gain_db")
    wanted = f"{value:+g} dB"
    gain = inner.get("channel_gain") if isinstance(inner, dict) else None
    if not isinstance(gain, dict):
        return [_verdict(channel, "gain_db", wanted, UNKNOWN,
                         "profile has no 'channel_gain' block; parametric_eq's gain range "
                         "describes EQ bands, not the channel trim, so it cannot stand in",
                         unverified=["channel_gain"])]
    # Range and step are checked SEPARATELY and reported separately. Lumping them meant a profile
    # that states the range and not the step reported BOTH as unverified -- naming a fact that is
    # in the file and was used, in the very list a consumer renders as "these were not checked".
    # An over-broad gap report is the same failure as an over-broad pass, one direction along.
    rng, step = gain.get("range_db"), gain.get("step_db")
    verified, unverified = [], []
    if isinstance(rng, list) and len(rng) == 2:
        if not (rng[0] <= value <= rng[1]):
            return [_verdict(channel, "gain_db", wanted, UNSUPPORTED,
                             f"outside the DSP's {_g(rng[0])}..{_g(rng[1])} dB range")]
        verified.append(f"within {_g(rng[0])}..{_g(rng[1])} dB")
    else:
        unverified.append("channel_gain.range_db")
    if step is None:
        unverified.append("channel_gain.step_db")
    elif not _on_grid(value, step):
        return [_verdict(channel, "gain_db", wanted, UNSUPPORTED,
                         f"not a multiple of the DSP's {_g(step)} dB step", verified)]
    else:
        verified.append(f"on the {_g(step)} dB step")
    if unverified:
        return [_verdict(channel, "gain_db", wanted, UNKNOWN,
                         (("; ".join(verified) + " -- but ") if verified else "")
                         + "the profile states no "
                         + ", ".join(k.split(".")[-1] for k in unverified),
                         verified, unverified)]
    return [_verdict(channel, "gain_db", wanted, OK, "; ".join(verified), verified)]


def _check_polarity(leg, channel, inner):
    wanted = leg["row"].get("polarity")
    if wanted == "NORM":
        return []
    if not isinstance(inner.get("polarity"), dict):
        return [_verdict(channel, "polarity", wanted, UNKNOWN,
                         "profile has no 'polarity' block", unverified=["polarity"])]
    return [_verdict(channel, "polarity", wanted, OK, "the DSP has per-channel polarity")]


def _check_preamp(leg, channel):
    """A non-zero PEQ preamp has no ledger field, and folding it into gain_db would lie.

    Resonalyze applies it inside the EQ block; the ledger's `gain_db` is the channel trim. Adding
    one to the other produces the same summed level and a row that misreports what was entered
    where -- and the row is what a settings sheet is generated from.
    """
    value = leg.get("peq_preamp_db") or 0.0
    if value == 0:
        return []
    return [_verdict(channel, "peq_preamp_db", f"{value:+g} dB", UNSUPPORTED,
                     "the ledger row has no PEQ-preamp field; folding it into gain_db would "
                     "misreport which control holds it")]


def _check_state(leg, channel):
    """A leg the session itself has switched off or put in bypass is not part of the tune."""
    out = []
    if not leg.get("enabled", True):
        out.append(_verdict(channel, "enabled", "disabled", UNSUPPORTED,
                            "the session has this leg disabled, so its row is not part of "
                            "the tune it describes"))
    if leg.get("bypass"):
        out.append(_verdict(channel, "bypass", "bypassed", UNSUPPORTED,
                            "the session bypasses this leg's whole DSP chain (raw signal); "
                            "the values below are what it would apply, not what it does"))
    return out


def _unwrap_profile(profile):
    if not isinstance(profile, dict):
        return {}
    return profile.get("dsp_profile", profile)


def _group(profile, group_id):
    inner = _unwrap_profile(profile)
    for group in inner.get("groups") or []:
        if isinstance(group, dict) and group.get("id") == group_id:
            return group
    return None


def _wanted(leg, field):
    value = leg["row"].get(field)
    if field in ("hp", "lp"):
        return None if value is None else f"{value['type']}{value['slope']} @ {_g(value['f'])} Hz"
    if field == "eq":
        return f"{len(value or [])} bands"
    return value


def _band_label(band):
    parts = [f"{band['type']} {_g(band.get('f'))} Hz"]
    if band.get("gain_db") is not None:
        parts.append(f"{band['gain_db']:+g} dB")
    if band.get("q") is not None:
        parts.append(f"Q{_g(band['q'])}")
    return " ".join(parts)


def _g(value):
    return f"{value:g}" if isinstance(value, (int, float)) else str(value)


# ── the whole conversion ───────────────────────────────────────────────────────
def convert(doc, *, profile=None, proj=None, mapping=None, group_id="physical_outputs",
            source_path=None):
    """Session document -> `{source, scene, legs, summary}`, checks included.

    The one call a CLI and a GUI both make, so neither can drift into its own reading of a file.
    """
    validate_session(doc, source_path or "<session>")
    read_version = doc.get("version")
    doc, migration = migrate_session(doc)
    legs = legs_of(doc)
    bind_channels(legs, proj, mapping)
    for leg in legs:
        leg["checks"] = check_leg(leg, profile, group_id)

    checks = [c for leg in legs for c in leg["checks"]]
    counts = {v: sum(1 for c in checks if c["verdict"] == v) for v in (OK, UNSUPPORTED, UNKNOWN)}
    inner = _unwrap_profile(profile)
    gaps = profile_gaps(legs)
    return {
        "converter": CONVERTER,
        "converter_version": CONVERTER_VERSION,
        "source": {
            "path": source_path,
            "format": doc.get("format"),
            "version": read_version,
            "read_as": CURRENT_VERSION,
            "migration": migration,
        },
        "scene": scene_of(doc),
        "profile": None if not inner else {
            "name": inner.get("name"), "vendor": inner.get("vendor"), "group": group_id,
        },
        "q_convention": {
            "session": "Rbj",
            "assumed_target": "Rbj",
            "note": "Resonalyze stores Q in the RBJ convention and only restates it on export; "
                    "Audiotec-Fischer (HELIX/MATCH/BRAX), Audison/Hertz, Mosconi and miniDSP read "
                    "Q the same way, so the numbers pass through unchanged. A DSP on the "
                    "Symmetric or Classic convention would need every Q rescaled -- no profile "
                    "field states a convention today, so this is an assumption, not a check.",
        },
        "legs": legs,
        "profile_gaps": gaps,
        "summary": {
            "legs": len(legs),
            "unbound": sum(1 for leg in legs if not leg.get("channel")),
            OK: counts[OK],
            UNSUPPORTED: counts[UNSUPPORTED],
            UNKNOWN: counts[UNKNOWN],
            "blocked": counts[UNSUPPORTED] > 0,
        },
    }


def profile_gaps(legs):
    """The unverifiable answers rolled up by the profile key that would settle them.

    Fifty-three per-band lines saying "no freq_range_hz" is the same one fact, and printed per
    band it buries the finding that actually blocks the tune. Grouping loses nothing -- every
    check still carries its own `unverified` list -- and turns the noise into a short, honest
    to-do list against the profile, which is where the missing facts belong anyway
    (`dsp_profile.open_questions`).
    """
    gaps = {}
    for leg in legs:
        for check in leg["checks"]:
            for key in check.get("unverified") or []:
                entry = gaps.setdefault(key, {"key": key, "checks": 0, "fields": set(),
                                              "channels": set()})
                entry["checks"] += 1
                entry["fields"].add(check["field"].split("[")[0])
                entry["channels"].add(check["channel"])
    out = []
    for g in sorted(gaps.values(), key=lambda g: -g["checks"]):
        out.append(dict(g, fields=sorted(g["fields"]), channels=sorted(g["channels"]),
                        **_grade(g["key"], sorted(g["fields"]), g["checks"])))
    return out


#: What a caller can do about each gap, graded by what it STOPS — `estimator-scope.md §1a`. The
#: grade is about the work, not about how interesting the fact is, and it is deliberately NOT
#: stored per profile key: the same missing step is SLOW while every value sits on a whole number
#: and a STOPPER the moment somebody enters a half-decibel trim. It is computed from what this
#: session actually asks for, every run.
def _grade(key, fields, count):
    leaf = key.split(".")[-1]
    who = "the Arbiter — it is read off the DSP's own screen, not derived from anything we hold"
    if leaf.endswith("_step_hz") or leaf.endswith("_step_db") or leaf.endswith("step_ms"):
        return {"grade": "DEGRADED", "ask": who,
                "cost": f"{count} value(s) on {', '.join(fields)} are within every stated range "
                        f"but cannot be checked against the entry grid — a value off the grid "
                        f"would be accepted here and refused by the DSP"}
    if leaf.endswith("_range_hz") or leaf.endswith("range_db") or leaf.endswith("max_ms"):
        return {"grade": "DEGRADED", "ask": who,
                "cost": f"{count} value(s) on {', '.join(fields)} pass every stated limit, but "
                        f"nothing bounds them — an out-of-range value would go unremarked"}
    return {"grade": "DEGRADED", "ask": who,
            "cost": f"{count} check(s) on {', '.join(fields)} could not run at all"}


def exit_code(result):
    """0 all clear · 1 something the DSP cannot enter · 2 something that could not be checked."""
    summary = result["summary"]
    if summary[UNSUPPORTED]:
        return 1
    if summary[UNKNOWN] or summary["unbound"]:
        return 2
    return 0


# ── report ─────────────────────────────────────────────────────────────────────
_MARK = {OK: "ok  ", UNSUPPORTED: "NO  ", UNKNOWN: "?   "}


def report(result):
    """The human rendering. Same facts as `--json`, in the order a tuner reads them."""
    lines = []
    scene = result["scene"]
    profile = result["profile"]
    lines.append(f"{result['source']['format']} v{result['source']['version']}"
                 + (f" (read as v{result['source']['read_as']})"
                    if result["source"].get("read_as") not in (None, result["source"]["version"]) else "")
                 + "  ->  ledger rows (status: proposed)")
    lines.append(f"  file        {result['source']['path']}")
    for note in result["source"].get("migration") or []:
        lines.append(f"  migrated    {note}")
    lines.append(f"  saved       {scene['saved_at_utc']}")
    lines.append(f"  calibration {scene['calibration_id']!r}"
                 + ("" if scene["calibration_id"] else "  (none -- IRs treated as uncalibrated)"))
    lines.append(f"  stereo      scene offset {_g(scene['stereo_scene_offset_ms'])} ms"
                 f" ({'RHD' if scene['stereo_right_hand_drive'] else 'LHD'}),"
                 f" {_g(scene['stereo_near_side_cut_db'])} dB cut on the"
                 f" {scene['stereo_near_side']} (near) side")
    lines.append("              ^ the AIM of Auto delay / gain balance, already inside the "
                 "per-leg numbers below")
    lines.append(f"  target      {_target_line(scene)}")
    named = profile["name"] if profile else "NONE GIVEN -- nothing below has been checked"
    lines.append(f"  profile     {named}")
    lines.append("")

    for leg in result["legs"]:
        head = leg["channel"] or f"?  ({leg['channel_hint']})"
        flags = [] if leg["enabled"] else ["DISABLED"]
        if leg["bypass"]:
            flags.append("BYPASSED")
        if leg["mono"]:
            flags.append("mono")
        lines.append(f"{head}   pair {leg['pair']} {leg['side']}   zone {leg.get('zone', '?')}"
                     + (f"   [{', '.join(flags)}]" if flags else ""))
        lines.append(f"    source  {leg['source_relative_path'] or leg['display_name']}")
        if not leg["channel"]:
            lines.append("    UNBOUND -- no channel in project.json answers to this name; "
                         "bind it with --map before using the row")
        row = leg["row"]
        lines.append(f"    HP {_leg_str(row['hp'])}    LP {_leg_str(row['lp'])}"
                     f"    gain {row['gain_db']:+g} dB    delay {_g(row['ta_ms'])} ms"
                     f"    {row['polarity']}")
        if row.get("phase_deg"):
            ref = leg.get("phase_reference") or {}
            lines.append(f"    phase {_g(row['phase_deg'])} deg @ {ref.get('kind', '?').upper()} "
                         f"{_g(ref.get('hz'))} Hz"
                         + ("  (that edge is dormant in the session -- carried with slope OFF so "
                            "the angle keeps its reference)" if ref.get("dormant") else ""))
        if row["eq"]:
            lines.append(f"    EQ  {len(row['eq'])} bands: "
                         + "; ".join(_band_label(b) for b in row["eq"]))
        for band in leg["dropped_eq_bands"]:
            lines.append(f"    EQ  dropped {_band_label(band)} -- {band['reason']}")
        for field, edge in sorted(leg["dormant"].items()):
            lines.append(f"    --  {field.upper()} {_leg_str(edge)} is in the file but NOT live "
                         f"(crossoverKind is {leg['crossover_kind']})")
        # Only the refusals are per-leg news. What the profile simply cannot answer is the same
        # sentence on every leg, and it is collected once at the foot instead.
        for check in leg["checks"]:
            if check["verdict"] != UNSUPPORTED:
                continue
            lines.append(f"    {_MARK[UNSUPPORTED]}{check['field']}: "
                         f"{check['wanted']} -- {check['reason']}")
        lines.append("")

    summary = result["summary"]
    gaps = result.get("profile_gaps") or []
    if gaps:
        lines.append(f"Not verifiable against this profile ({summary[UNKNOWN]} checks) -- these "
                     "are gaps in the profile, not faults in the session:")
        for gap in gaps:
            lines.append(f"  [{gap['grade']}] {gap['key']} not stated")
            lines.append(f"      cost: {gap['cost']}")
            lines.append(f"      ask : {gap['ask']}")
        lines.append("")

    lines.append(f"{summary['legs']} legs · {summary[OK]} enterable · "
                 f"{summary[UNSUPPORTED]} NOT enterable · {summary[UNKNOWN]} unverifiable"
                 + (f" · {summary['unbound']} unbound" if summary["unbound"] else ""))
    if summary["blocked"]:
        lines.append("BLOCKED: nothing was rounded to fit. Decide each 'NO' above by hand -- "
                     "a substitute filter is a tuning decision, not a conversion.")
    return "\n".join(lines)


def _target_line(scene):
    """The aiming curve as its NUMBERS, with the preset name demoted to a label.

    Resonalyze stores a flat numeric mirror beside the preset name on purpose: "presets are a
    starting point whose numbers can change between versions, while a session has to open aiming
    at exactly the curve it was tuned against". So a provenance line reading `CarBass` can come to
    mean a different curve after an upstream release, while the tilt and the shelf triples cannot.
    The blob itself is carried verbatim and never parsed into a row -- the target is a project-wide
    overlay the host owns, not a per-channel filter, and the ledger rightly has nowhere to put it.
    """
    target = scene.get("target") or {}
    level = f"{scene['target_level_db']:+g} dB"
    if not isinstance(target, dict) or not target:
        return f"none at {level}"
    parts = [f"tilt {_g(target.get('tiltDbPerOctave', 0))} dB/oct"]
    for label, prefix in (("bass", "bassShelf"), ("treble", "trebleShelf"),
                          ("presence", "presence")):
        gain = target.get(f"{prefix}GainDb")
        if gain is None:
            continue
        parts.append(f"{label} {gain:+g} dB @{_g(target.get(f'{prefix}FrequencyHz'))} Hz"
                     f"/{_g(target.get(f'{prefix}WidthOctaves'))} oct")
    label = target.get("preset")
    return (" · ".join(parts) + f" at {level}"
            + (f"   (preset label {label!r} -- the numbers above are what binds)"
               if label else ""))


def _leg_str(leg):
    if leg is None:
        return "OFF"
    return f"{_g(leg['f'])} {leg['type']}{leg['slope']}"


# ── CLI ────────────────────────────────────────────────────────────────────────
def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="resonalyze_vc.py",
        description="Read a Resonalyze Virtual DSP session as ledger rows, checked against the "
                    "project's DSP capability profile.")
    parser.add_argument("session", help="the resonalyze-virtual-crossover JSON to read")
    parser.add_argument("--project", help="project directory holding project.json and "
                                          "dsp_profile.json")
    parser.add_argument("--profile", help="a dsp_profile.json to check against, if not the "
                                          "project's own")
    parser.add_argument("--group", default="physical_outputs",
                        help="the profile group the legs belong to (default: physical_outputs)")
    parser.add_argument("--map", action="append", default=[], metavar="NAME=CODE",
                        help="bind a source name to a channel code; repeatable")
    parser.add_argument("--json", action="store_true", help="machine output instead of a report")
    args = parser.parse_args(argv)

    mapping = {}
    for item in args.map:
        if "=" not in item:
            parser.error(f"--map wants NAME=CODE, got {item!r}")
        name, code = item.split("=", 1)
        mapping[name.strip()] = code.strip()

    proj = None
    if args.project:
        import project as project_mod
        proj = project_mod.Project(args.project)

    profile = None
    profile_path = args.profile
    if profile_path is None and args.project:
        candidate = os.path.join(args.project, "dsp_profile.json")
        profile_path = candidate if os.path.exists(candidate) else None
    if profile_path:
        import dsp_profile
        profile = dsp_profile.load_profile(profile_path)

    try:
        doc = load_session(args.session)
        result = convert(doc, profile=profile, proj=proj, mapping=mapping,
                         group_id=args.group, source_path=args.session)
    except SessionError as exc:
        print(f"resonalyze_vc: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, ensure_ascii=False) if args.json else report(result))
    return exit_code(result)


# ── selftest ───────────────────────────────────────────────────────────────────
def _session(**over):
    """A two-pair session: a mono sub (low-pass, inverted) and a stereo woofer (band-pass)."""
    def side(name, **kw):
        base = {
            "displayName": name, "sourceFilePath": f"D:\\x\\{name}", "sourceRelativePath": name,
            "historyEntryId": None, "gainDb": 0.0, "delayMs": 0.0, "invertPolarity": False,
            "crossoverKind": "Off",
            "lowPassEdge": {"family": "LinkwitzRiley", "frequencyHz": 2000,
                            "slopeDbPerOctave": 24, "rippleDb": 0.1},
            "highPassEdge": {"family": "LinkwitzRiley", "frequencyHz": 2000,
                             "slopeDbPerOctave": 24, "rippleDb": 0.1},
            "allPassType": "Off", "allPassFrequencyHz": 2000, "allPassQ": 1.0,
            "peqPreampDb": 0.0, "peqBands": [], "peqSourceName": None, "hasSource": True,
        }
        base.update(kw)
        return base

    empty = {"displayName": "", "sourceFilePath": None, "sourceRelativePath": None,
             "historyEntryId": None, "hasSource": False, "crossoverKind": "Off"}
    doc = {
        "format": FORMAT, "version": 7, "savedAtUtc": "2026-08-22T21:20:19Z", "channels": [],
        "calibrationId": "90deg", "stereoSceneOffsetMs": 0.25, "stereoRightHandDrive": False,
        "stereoLevelDifferenceDb": -1.0, "targetLevelDb": -4.0,
        "target": {"preset": "CarBass", "tiltDbPerOctave": 0, "bassShelfGainDb": 9,
                   "bassShelfFrequencyHz": 100, "bassShelfWidthOctaves": 0.8,
                   "trebleShelfGainDb": -2, "trebleShelfFrequencyHz": 12000,
                   "trebleShelfWidthOctaves": 0.7, "toleranceDb": 3},
        "smoothingInverseOctaves": 6,
        "pairs": [
            {"mono": True, "enabled": True, "bypass": False,
             "left": side("Resonalyze-IR-2026-08-20_12-40-42_sw.json",
                          invertPolarity=True, crossoverKind="LowPass",
                          lowPassEdge={"family": "Butterworth", "frequencyHz": 65,
                                       "slopeDbPerOctave": 36, "rippleDb": 1},
                          highPassEdge={"family": "Butterworth", "frequencyHz": 10,
                                        "slopeDbPerOctave": 24, "rippleDb": 0.1},
                          peqBands=[{"frequencyHz": 38, "q": 7, "gainDb": -3,
                                     "type": "Peaking", "isTransparent": False},
                                    {"frequencyHz": 100, "q": 2, "gainDb": 0,
                                     "type": "Peaking", "isTransparent": True}]),
             "right": dict(empty)},
            {"mono": False, "enabled": True, "bypass": False,
             "left": side("Resonalyze-IR-2026-08-20_12-35-42_w_L.json",
                          delayMs=4.71, crossoverKind="BandPass",
                          highPassEdge={"family": "Butterworth", "frequencyHz": 65,
                                        "slopeDbPerOctave": 36, "rippleDb": 1},
                          lowPassEdge={"family": "LinkwitzRiley", "frequencyHz": 350,
                                       "slopeDbPerOctave": 48, "rippleDb": 0.1}),
             "right": side("Resonalyze-IR-2026-08-20_12-36-32_w_R.json",
                           delayMs=2.81, crossoverKind="BandPass",
                           highPassEdge={"family": "Butterworth", "frequencyHz": 65,
                                         "slopeDbPerOctave": 36, "rippleDb": 1},
                           lowPassEdge={"family": "LinkwitzRiley", "frequencyHz": 350,
                                        "slopeDbPerOctave": 24, "rippleDb": 0.1})},
            # A leg no project answers to. Every consumer's importer needs the MISS in its
            # fixture: binding is the easy path and the unbound leg is the one a dialog exists
            # for, so a fixture where everything resolves tests the half that never fails.
            {"mono": True, "enabled": True, "bypass": False,
             "left": side("Resonalyze-IR-2026-08-20_12-44-02_nosuch.json", crossoverKind="Off"),
             "right": dict(empty)},
        ],
    }
    doc.update(over)
    return doc


def _profile():
    """A Helix-shaped profile: LR stops at 36, 1 Hz corners, a delay step and NO delay ceiling."""
    return {"dsp_profile": {
        "name": "Test DSP", "vendor": "Test", "dsp_processing_rate_hz": 96000,
        "delay": {"step_ms": 0.01},
        "polarity": {"scope": ["per driver output"]},
        "parametric_eq": {"freq_range_hz": None, "freq_step_hz": 0.01,
                          "gain_range_db": [-30.0, 12.0], "gain_step_db": 0.1,
                          "q_range": [0.5, 15.0], "q_step": 0.1},
        "groups": [{
            "id": "physical_outputs", "label": "Outputs", "max_count": 12,
            "fields": ["hp", "lp", "gain_db", "ta_ms", "polarity", "eq"],
            "eq": {"band_types": ["PK", "LSH", "HSH", "APF1", "APF2"], "bands_per_channel": 30},
            "crossover_filters": {
                "corner_freq_range_hz": None, "corner_freq_step_hz": 1.0,
                "types": {"BW": {"orders_db_per_oct": [6, 12, 18, 24, 30, 36, 42]},
                          "BE": {"orders_db_per_oct": [6, 12, 18, 24, 30, 36, 42]},
                          "LR": {"orders_db_per_oct": [12, 24, 36]}},
            },
        }],
    }}


def _session_v10(**over):
    """The same two-pair session as `_session`, in the form the CURRENT Resonalyze writes (v10,
    319e873): no per-side all-pass keys (the stage is a band of the bank), a `zone` and a
    `collapsed` flag on every pair, `phaseRotationDegrees` on every side. The sub carries the
    v7 fixture's all-pass as an `AllPassSecondOrder` band; the woofer's left side asks for 90°
    of phase at its live HP; the orphan is a Center block with its HP DORMANT and 45° stated at
    it. SYNTHETIC, built from the upstream's own tests (VirtualCrossoverProjectFileTests) -- no
    file written by a v10 build is on disk today (hub RES-008); when one arrives it belongs
    beside this one, and the reader is checked on both."""
    doc = _session()
    doc["version"] = 10
    doc["synthetic"] = ("built by resonalyze_vc._session_v10() from the upstream's tests, not "
                        "written by Resonalyze -- the shape of a v10 session, not somebody's tune")
    doc["dspProcessorModelId"] = None
    doc["showPhaseView"] = True
    zones = ("Sub", "Front", "Center")
    for pair, zone in zip(doc["pairs"], zones):
        pair["zone"] = zone
        pair["collapsed"] = False
        for name in ("left", "right"):
            side = pair.get(name) or {}
            if not side.get("hasSource"):
                continue
            for key in ("allPassType", "allPassFrequencyHz", "allPassQ"):
                side.pop(key, None)
            side["phaseRotationDegrees"] = 0.0
    sub, woofer, orphan = doc["pairs"]
    sub["left"]["peqBands"].append({"frequencyHz": 120, "q": 2.5, "gainDb": 0, "type": "AllPassSecondOrder",
                                    "isTransparent": False})
    woofer["left"]["phaseRotationDegrees"] = 90.0
    orphan["left"]["crossoverKind"] = "LowPass"
    orphan["left"]["highPassEdge"] = {"family": "LinkwitzRiley", "frequencyHz": 300,
                                      "slopeDbPerOctave": 24, "rippleDb": 0.1}
    orphan["left"]["phaseRotationDegrees"] = 45.0
    doc.update(over)
    return doc


#: A synthetic v7 session on disk, for consumers who need a file rather than this module's
#: builder (autosound-tcc's importer tests). SYNTHETIC on purpose: a real session carries
#: somebody's tune and the absolute paths of their machine, and this repo is public.
FIXTURE = os.path.join(_HERE, "testdata", "virtual-dsp-session-v7.json")
#: ...and its v10 twin, the shape the current app writes (`_session_v10`).
FIXTURE_V10 = os.path.join(_HERE, "testdata", "virtual-dsp-session-v10.json")


def _fixture_text(builder=None):
    """The fixture's exact bytes, from the same builder the selftest runs on.

    One source, two consumers. A fixture hand-maintained beside a builder is two descriptions of
    one format that agree until the day they do not -- and the drift shows up as somebody else's
    test passing against a file this module no longer produces.
    """
    return json.dumps((builder or _session)(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _selftest():
    doc = _session()
    legs = legs_of(doc)

    # The mono pair's empty right side is not a channel, and a mono pair yields ONE row.
    assert len(legs) == 4, [f"{l['pair']}.{l['side']}" for l in legs]
    sub, w_l, w_r, orphan = legs

    # A dormant edge stays out of the row. The sub's file carries HP BW 10/24 while its kind is
    # LowPass -- importing it would invent a subsonic filter that is not in the tune.
    assert sub["row"]["hp"] is None, sub["row"]["hp"]
    assert sub["dormant"]["hp"]["f"] == 10, sub["dormant"]
    assert sub["row"]["lp"] == {"f": 65.0, "type": "BW", "slope": 36,
                                "family": "Butterworth"}, sub["row"]["lp"]
    assert sub["row"]["polarity"] == "INV", sub["row"]
    # ...and the mirror trap: a high-pass-only leg must withhold its dormant LOW-pass edge, which
    # in these files is the C# constructor's untouched default (LR 2000 Hz 24 dB/oct).
    hp_only = legs_of(_session(pairs=[{"mono": True, "left": dict(
        _session()["pairs"][1]["left"], crossoverKind="HighPass"),
        "right": {"hasSource": False}}]))[0]
    assert hp_only["row"]["lp"] is None and hp_only["dormant"]["lp"]["f"] == 350.0, hp_only

    # A transparent band (zero gain) is dropped, not carried into a hardware slot, and the
    # surviving bands are renumbered so `i` stays a usable slot index.
    assert [b["f"] for b in sub["row"]["eq"]] == [38.0], sub["row"]["eq"]
    assert len(sub["dropped_eq_bands"]) == 1, sub["dropped_eq_bands"]
    assert sub["row"]["eq"][0]["i"] == 1, sub["row"]["eq"]

    # The scene offset is the AIM, and it never reaches a row: both delays are the file's own.
    scene = scene_of(doc)
    assert scene["stereo_scene_offset_ms"] == 0.25 and not scene["stereo_right_hand_drive"]
    assert w_l["row"]["ta_ms"] == 4.71 and w_r["row"]["ta_ms"] == 2.81, (w_l["row"], w_r["row"])

    # A right-hand-drive session's layout survives whether it arrives as a flag or as the sign,
    # and the tiny zero-marker reads back as no offset at all.
    rhd = scene_of(_session(stereoSceneOffsetMs=-0.3, stereoRightHandDrive=False))
    assert rhd["stereo_right_hand_drive"] and rhd["stereo_scene_offset_ms"] == 0.3, rhd
    zero = scene_of(_session(stereoSceneOffsetMs=-0.001, stereoRightHandDrive=True))
    assert zero["stereo_right_hand_drive"] and zero["stereo_scene_offset_ms"] == 0.0, zero

    # The level difference's sign is the layout too. Both of these ask for the SAME thing -- 1 dB
    # off the near side -- and only the layout differs, so a reader that takes the wire value as
    # plain L-R has the cut on the wrong seat in exactly one of them.
    assert (scene["stereo_near_side_cut_db"], scene["stereo_near_side"]) == (1.0, "left"), scene
    rhd_level = scene_of(_session(stereoSceneOffsetMs=-0.25, stereoLevelDifferenceDb=1.0))
    assert (rhd_level["stereo_near_side_cut_db"],
            rhd_level["stereo_near_side"]) == (1.0, "right"), rhd_level

    # A pair-level mute must reach the row as a mute. v7 keeps enable/bypass on the PAIR only,
    # and a side-first read would default the missing side key to "enabled" and hand back a muted
    # leg as a playing one -- silently, and in the one direction nobody checks.
    muted = convert(_session(pairs=[{"mono": True, "enabled": False,
                                     "left": _session()["pairs"][1]["left"],
                                     "right": {"hasSource": False}}]))
    assert muted["legs"][0]["enabled"] is False, muted["legs"][0]
    # ...and a stale side-level `enabled: true` (what v6 wrote, which v7's migration nulls) must
    # NOT override the pair that says otherwise.
    stale = convert(_session(pairs=[{"mono": True, "enabled": False,
                                     "left": dict(_session()["pairs"][1]["left"], enabled=True),
                                     "right": {"hasSource": False}}]))
    assert stale["legs"][0]["enabled"] is False, stale["legs"][0]

    # The filename carries the channel id our project.json keeps beside the code.
    assert channel_hint("Resonalyze-IR-2026-08-20_12-35-42_w_L.json") == "w_L"
    assert channel_hint("Resonalyze-IR-2026-08-20_12-34-48_m_L-ctl1.json") == "m_L-ctl1"
    assert _hint_prefixes("m_L-ctl1") == ["m_L-ctl1", "m_L"], _hint_prefixes("m_L-ctl1")

    class _Proj:
        """Stands in for `project.Project`: code, then id, then previous_names."""
        rows = [{"code": "sw"}, {"code": "w-L", "id": "w_L"}, {"code": "w-R", "id": "w_R"},
                {"code": "m-L", "id": "m_L"}]

        def resolve_channel(self, name, data=None):
            for match in (lambda r: r.get("code") == name, lambda r: r.get("id") == name):
                row = next((r for r in self.rows if match(r)), None)
                if row is not None:
                    return row
            return None

    bind_channels(legs, _Proj())
    assert [leg["channel"] for leg in legs] == ["sw", "w-L", "w-R", None], legs
    assert orphan["channel_hint"] == "nosuch" and "channel_bound_by" not in orphan, orphan
    # A measurement tag falls away at the `-`, but only after the full name has been tried.
    tagged = [{"channel_hint": "m_L-ctl1", "display_name": ""}]
    bind_channels(tagged, _Proj())
    assert tagged[0]["channel"] == "m-L", tagged

    # ── the verdicts ──────────────────────────────────────────────────────────
    profile = _profile()
    result = convert(doc, profile=profile, proj=_Proj(), source_path="<selftest>")
    assert result["summary"]["unbound"] == 1, result["summary"]

    def verdicts(channel, field):
        return [c for leg in result["legs"] for c in leg["checks"]
                if c["channel"] == channel and c["field"] == field]

    # THE case this converter exists for: LR48 is a filter the target DSP does not have, and it
    # comes back refused -- not rounded to the LR36 the profile does offer.
    lp = verdicts("w-L", "lp")[0]
    assert lp["verdict"] == UNSUPPORTED and lp["enterable"] is False, lp
    assert "36" in lp["reason"] and "48" in lp["wanted"], lp
    assert result["legs"][1]["row"]["lp"]["slope"] == 48, "the wanted value must survive intact"
    assert result["summary"]["blocked"] and exit_code(result) == 1, result["summary"]

    # The same corner at a slope the DSP DOES have is NOT refused -- so the refusal is about the
    # slope, not about LR and not about 350 Hz. It is not `ok` either: this profile states no
    # `corner_freq_range_hz`, so the corner is unverifiable and the verdict says which half was
    # checked. An "unknown" that cannot name its own gap is the shrug this asserts against.
    lp_ok = verdicts("w-R", "lp")[0]
    assert lp_ok["verdict"] == UNKNOWN and lp_ok["enterable"] is None, lp_ok
    assert "LR24 is offered" in lp_ok["verified"], lp_ok
    assert lp_ok["unverified"] == ["crossover_filters.corner_freq_range_hz"], lp_ok
    # ...and once the profile states the range, the very same leg goes green. Without this the
    # test above would also pass on a checker that simply never returns `ok`.
    ranged = json.loads(json.dumps(profile))
    ranged["dsp_profile"]["groups"][0]["crossover_filters"]["corner_freq_range_hz"] = [10, 20000]
    green = convert(doc, profile=ranged, proj=_Proj())
    assert [c for leg in green["legs"] for c in leg["checks"]
            if c["channel"] == "w-R" and c["field"] == "lp"][0]["verdict"] == OK

    # A DORMANT edge is never validated, and the pair of assertions matters more than either.
    # The sub's dormant `highPassEdge` is 10 Hz, BELOW the Helix's 20 Hz corner floor. Checking it
    # would refuse a tune over a filter that is not applied — the mirror of silently rounding an
    # impossible value, and just as wrong. But if that same edge were LIVE, 10 Hz must be caught:
    # a converter that ignores dormant edges by never checking 10 Hz at all would pass both halves
    # of this test while being broken. Only the two together say "dormant, therefore unchecked"
    # rather than "unchecked, therefore fine".
    floored = json.loads(json.dumps(profile))
    floored["dsp_profile"]["groups"][0]["crossover_filters"]["corner_freq_range_hz"] = [20, 20480]
    quiet = convert(doc, profile=floored, proj=_Proj())
    assert quiet["legs"][0]["dormant"]["hp"]["f"] == 10.0, quiet["legs"][0]["dormant"]
    assert not [c for c in quiet["legs"][0]["checks"] if c["field"] == "hp"], \
        "a dormant edge must not be validated at all"
    live_10 = convert(_session(pairs=[{"mono": True, "left": dict(
        _session()["pairs"][0]["left"], crossoverKind="BandPass"),
        "right": {"hasSource": False}}]), profile=floored)
    hp_low = [c for c in live_10["legs"][0]["checks"] if c["field"] == "hp"][0]
    assert hp_low["verdict"] == UNSUPPORTED and "20-20480" in hp_low["reason"], hp_low

    # A family the hardware offers but whose parameters are unstated is ENTERABLE and not
    # MODELLABLE, and those are different answers. Chebyshev's ripple is null because an
    # experiment could not identify the maths -- so the honest verdict is "cannot be checked",
    # never a clean pass. Asked the other way: without this, a Chebyshev crossover would report
    # exactly like a Butterworth one, in the one family we understand least.
    cheby = json.loads(json.dumps(profile))
    cheby["dsp_profile"]["groups"][0]["crossover_filters"]["types"]["CHEBYSHEV"] = {
        "orders_db_per_oct": [6, 12, 18, 24, 30, 36, 42], "ripple_db": None}
    cheb = convert(_session(pairs=[{"mono": True, "left": dict(
        _session()["pairs"][1]["left"],
        highPassEdge={"family": "Chebyshev", "frequencyHz": 65, "slopeDbPerOctave": 36,
                      "rippleDb": 1}), "right": {"hasSource": False}}]), profile=cheby)
    ch = [c for c in cheb["legs"][0]["checks"] if c["field"] == "hp"][0]
    assert ch["verdict"] == UNKNOWN and ch["enterable"] is None, ch
    assert "ripple_db" in ch["reason"] and "cannot be modelled" in ch["reason"], ch
    assert ch["unverified"] == ["crossover_filters.types.CHEBYSHEV.ripple_db"], ch
    # ...and the same edge in a family whose parameters ARE stated still passes, so this is about
    # the missing parameter and not about refusing anything unfamiliar.
    assert [c for c in convert(_session(pairs=[{"mono": True, "left": dict(
        _session()["pairs"][1]["left"]), "right": {"hasSource": False}}]),
        profile=cheby)["legs"][0]["checks"] if c["field"] == "hp"][0]["verdict"] != UNSUPPORTED

    # BW36 at 65 Hz is a filter this DSP has, at a corner on its 1 Hz grid.
    hp_36 = verdicts("w-L", "hp")[0]
    assert hp_36["enterable"] is not False, hp_36
    assert "BW36 is offered" in hp_36["verified"], hp_36
    assert "corner on the 1 Hz grid" in hp_36["verified"], hp_36
    off_grid = convert(_session(pairs=[{"mono": True, "left": dict(
        _session()["pairs"][1]["left"],
        highPassEdge={"family": "Butterworth", "frequencyHz": 65.5, "slopeDbPerOctave": 36,
                      "rippleDb": 1}), "right": {"hasSource": False}}]), profile=profile)
    hp = [c for c in off_grid["legs"][0]["checks"] if c["field"] == "hp"][0]
    assert hp["verdict"] == UNSUPPORTED and "1 Hz step" in hp["reason"], hp

    # A limit the profile does not state is UNKNOWN, never ok. The profile has a delay step and
    # no ceiling, so a delay is reported as unverified rather than waved through.
    delay = verdicts("w-L", "ta_ms")[0]
    assert delay["verdict"] == UNKNOWN and delay["enterable"] is None, delay
    assert "max_ms" in delay["reason"], delay
    with_ceiling = dict(profile)
    with_ceiling["dsp_profile"] = dict(profile["dsp_profile"],
                                       delay={"step_ms": 0.01, "max_ms": 20.82})
    ok_delay = convert(doc, profile=with_ceiling, proj=_Proj())
    assert [c for leg in ok_delay["legs"] for c in leg["checks"]
            if c["field"] == "ta_ms"][1]["verdict"] == OK
    over = convert(_session(pairs=[{"mono": True, "left": dict(
        _session()["pairs"][1]["left"], delayMs=25.0), "right": {"hasSource": False}}]),
        profile=with_ceiling)
    assert [c for c in over["legs"][0]["checks"]
            if c["field"] == "ta_ms"][0]["verdict"] == UNSUPPORTED

    # Channel gain is NOT checked against parametric_eq's gain range: they are different controls,
    # and borrowing one for the other is a check that looks green while measuring nothing.
    gain = verdicts("w-L", "gain_db")[0]
    assert gain["verdict"] == UNKNOWN and "channel_gain" in gain["reason"], gain

    # A half-stated limit reports only the half that is missing. With the range declared and the
    # step absent, naming the RANGE as unverified would put a fact that is in the file — and was
    # used — into the list a consumer renders as "these were not checked". An over-broad gap
    # report is the same failure as an over-broad pass, one direction along. (TCC, 2026-08-23.)
    ranged_gain = json.loads(json.dumps(profile))
    ranged_gain["dsp_profile"]["channel_gain"] = {"range_db": [-30.0, 5.0]}
    half = [c for leg in convert(doc, profile=ranged_gain, proj=_Proj())["legs"]
            for c in leg["checks"] if c["field"] == "gain_db"][0]
    assert half["verdict"] == UNKNOWN, half
    assert half["unverified"] == ["channel_gain.step_db"], half
    assert "within -30..5 dB" in half["verified"], half
    # ...and with both stated it goes green; without that, the assertion above also passes on a
    # checker that can never say yes.
    ranged_gain["dsp_profile"]["channel_gain"]["step_db"] = 0.1
    full = [c for leg in convert(doc, profile=ranged_gain, proj=_Proj())["legs"]
            for c in leg["checks"] if c["field"] == "gain_db"][0]
    assert full["verdict"] == OK and not full["unverified"], full
    # A gain the hardware refuses is still refused, range-only profile or not.
    ranged_gain["dsp_profile"]["channel_gain"]["range_db"] = [-30.0, -5.0]
    over = [c for leg in convert(doc, profile=ranged_gain, proj=_Proj())["legs"]
            for c in leg["checks"] if c["field"] == "gain_db"][0]
    assert over["verdict"] == UNSUPPORTED, over

    # No profile at all means every field is unknown -- and specifically NOT ok.
    blind = convert(doc, profile=None, proj=_Proj())
    assert {c["verdict"] for leg in blind["legs"] for c in leg["checks"]} == {UNKNOWN}, blind
    assert not blind["summary"]["blocked"] and exit_code(blind) == 2, blind["summary"]

    # EVERY unknown names the profile key that would settle it, so every unknown reaches the
    # roll-up. Asked the other way -- what would still pass without this? -- a check that shrugs
    # without saying which fact is missing: it would count in the total, appear in no group, and
    # nobody would ever know which line of the profile to go and write.
    for case in (result, blind, convert(doc, profile=profile, proj=None)):
        loose = [(c["channel"], c["field"], c["reason"]) for leg in case["legs"]
                 for c in leg["checks"] if c["verdict"] == UNKNOWN and not c["unverified"]]
        assert not loose, f"unknowns naming no missing key: {loose}"
        assert sum(g["checks"] for g in case["profile_gaps"]) == case["summary"][UNKNOWN], \
            (case["profile_gaps"], case["summary"])
        # Every gap says what it COSTS and who to ask -- `estimator-scope.md §1a`. An abstention
        # that names no consequence gets filed rather than answered, which is the same fate as a
        # warning nobody reads.
        for gap in case["profile_gaps"]:
            assert gap["grade"] in ("STOPPER", "DEGRADED", "SLOW"), gap
            assert gap["cost"] and gap["ask"], gap
            assert str(gap["checks"]) in gap["cost"], \
                "the cost must be quantified, not adjectival"
            assert gap["channels"], "a gap names the channels it touches"
    # ...and a verdict that IS enterable claims nothing it did not check.
    for leg in green["legs"]:
        for check in leg["checks"]:
            assert not (check["verdict"] == OK and check["unverified"]), check

    # A PEQ preamp has nowhere honest to go, so it is refused rather than added to the trim.
    pre = convert(_session(pairs=[{"mono": True, "left": dict(
        _session()["pairs"][1]["left"], peqPreampDb=-3.0), "right": {"hasSource": False}}]),
        profile=profile)
    assert any(c["field"] == "peq_preamp_db" and c["verdict"] == UNSUPPORTED
               for c in pre["legs"][0]["checks"]), pre["legs"][0]["checks"]

    # An all-pass stage becomes the ledger band the profile declares; a first-order one has no Q.
    ap = legs_of(_session(pairs=[{"mono": True, "left": dict(
        _session()["pairs"][1]["left"], allPassType="SecondOrder", allPassFrequencyHz=1200,
        allPassQ=1.7), "right": {"hasSource": False}}]))[0]
    assert ap["row"]["eq"][-1] == {"type": "APF2", "f": 1200.0, "i": 1, "q": 1.7}, ap["row"]["eq"]
    ap1 = legs_of(_session(pairs=[{"mono": True, "left": dict(
        _session()["pairs"][1]["left"], allPassType="FirstOrder", allPassFrequencyHz=1200),
        "right": {"hasSource": False}}]))[0]
    assert "q" not in ap1["row"]["eq"][-1], ap1["row"]["eq"]

    # A leg the session switched off is reported as not part of the tune, so a caller cannot
    # bank it by accident.
    pair = {"mono": True, "enabled": False, "left": dict(_session()["pairs"][1]["left"]),
            "right": {"hasSource": False}}
    got = convert(_session(pairs=[pair]), profile=profile)
    assert any(c["field"] == "enabled" and c["verdict"] == UNSUPPORTED
               for c in got["legs"][0]["checks"]), got["legs"][0]["checks"]
    bypassed = convert(_session(pairs=[dict(pair, enabled=True, bypass=True)]), profile=profile)
    assert any(c["field"] == "bypass" and c["verdict"] == UNSUPPORTED
               for c in bypassed["legs"][0]["checks"]), bypassed["legs"][0]["checks"]

    # A pre-pairs file must fail, not come back as a tune with no channels.
    for bad, why in (
        ({"format": "resonalyze-impulse-response", "version": 7, "pairs": []}, "wrong format"),
        ({"format": FORMAT, "version": 6, "pairs": []}, "wrong version"),
        ({"format": FORMAT, "version": 7, "pairs": [], "channels": [{"gainDb": 0}]}, "legacy"),
    ):
        try:
            validate_session(bad)
        except SessionError:
            pass
        else:
            raise AssertionError(f"{why} was accepted")

    # An unbound leg is visible as unbound and never silently filed under a guess.
    loose = convert(doc, profile=profile, proj=None)
    assert loose["summary"]["unbound"] == 4, loose["summary"]
    assert all(leg["channel"] is None for leg in loose["legs"])
    assert "UNBOUND" in report(loose)

    text = report(result)
    assert "BLOCKED" in text and "LR48" in text and "NOT live" in text, text
    # The aiming curve is reported by its NUMBERS; the preset name is a label that can come to
    # mean a different curve after an upstream release.
    assert "tilt 0 dB/oct" in text and "bass +9 dB @100 Hz" in text, text
    assert "preset label 'CarBass' -- the numbers above are what binds" in text, text

    # The on-disk fixture other repos test against IS this builder's output. If someone edits
    # either one alone, this fails and names the command that reconciles them -- which is the only
    # reason a second copy of a format description is safe to keep at all.
    if os.path.exists(FIXTURE):
        with open(FIXTURE, encoding="utf-8") as f:
            on_disk = f.read()
        assert on_disk == _fixture_text(), (
            f"{FIXTURE} has drifted from _session(); regenerate:\n"
            f"    python3 {os.path.basename(__file__)} --write-fixture")
        assert convert(load_session(FIXTURE), profile=profile,
                       proj=_Proj())["summary"]["blocked"], "the fixture must still refuse LR48"
    else:
        raise AssertionError(f"missing fixture {FIXTURE} -- write it with --write-fixture")
    if os.path.exists(FIXTURE_V10):
        with open(FIXTURE_V10, encoding="utf-8") as f:
            assert f.read() == _fixture_text(_session_v10), (
                f"{FIXTURE_V10} has drifted from _session_v10(); regenerate:\n"
                f"    python3 {os.path.basename(__file__)} --write-fixture")
    else:
        raise AssertionError(f"missing fixture {FIXTURE_V10} -- write it with --write-fixture")

    # ── versions: v7..v10 read, migrated in memory by their own steps; v11 refused by name ──
    for v in (8, 9, 10):
        validate_session(_session(version=v))
    try:
        validate_session(_session(version=11))
    except SessionError as exc:
        assert "11" in str(exc) and "upstream-drift" in str(exc), exc
    else:
        raise AssertionError("a v11 session was read")
    # v7→v8: the all-pass stage becomes a band of the bank, per order (their test, pinned): a
    # second-order stage keeps its Q, a first-order one has none, a side without a stage gains
    # nothing, and the v7 document itself is not touched.
    v7 = _session()
    v7["pairs"][1]["left"].update(allPassType="SecondOrder", allPassFrequencyHz=120, allPassQ=2.5)
    v7["pairs"][1]["right"].update(allPassType="FirstOrder", allPassFrequencyHz=300, allPassQ=4.0)
    v10, notes = migrate_session(v7)
    assert v7["version"] == 7 and "allPassType" in v7["pairs"][1]["left"], "the input was mutated"
    assert v10["version"] == 10 and notes and notes[0].startswith("v7→v8"), notes
    wl, wr = v10["pairs"][1]["left"], v10["pairs"][1]["right"]
    assert "allPassType" not in wl and wl["peqBands"][-1] == {
        "frequencyHz": 120.0, "q": 2.5, "gainDb": 0.0, "type": "AllPassSecondOrder", "isTransparent": False}, wl
    assert wr["peqBands"][-1]["type"] == "AllPassFirstOrder" and wr["peqBands"][-1]["q"] == 1.0, wr
    assert v10["pairs"][0]["left"]["peqBands"][-1]["type"] == "Peaking", "a side with no stage gained a band"
    m_legs = legs_of(v10)
    assert [b["type"] for b in m_legs[1]["row"]["eq"]] == ["APF2"] and m_legs[1]["row"]["eq"][0]["q"] == 2.5
    assert m_legs[2]["row"]["eq"] == [{"type": "APF1", "f": 300.0, "i": 1}], m_legs[2]["row"]["eq"]
    # ...an all-pass band is NOT transparent though its gain is 0 (their IsTransparent excludes it),
    # and a bell at 0 dB still is.
    assert not m_legs[1]["dropped_eq_bands"] and m_legs[0]["dropped_eq_bands"], "transparency rule"
    # A full bank: the last gain-bearing band goes, the all-pass lands, and the note says what it cost.
    full = _session()
    full["pairs"][1]["left"]["peqBands"] = [{"frequencyHz": 100 + i, "q": 2, "gainDb": -1, "type": "Peaking"}
                                            for i in range(MAX_BAND_COUNT)]
    full["pairs"][1]["left"].update(allPassType="SecondOrder", allPassFrequencyHz=120, allPassQ=2.5)
    fm, fnotes = migrate_session(full)
    bank = fm["pairs"][1]["left"]["peqBands"]
    assert len(bank) == MAX_BAND_COUNT and bank[-1]["type"] == "AllPassSecondOrder", len(bank)
    assert not any(b["frequencyHz"] == 131 for b in bank), "the last bell (131 Hz) should be gone"
    assert any("bank was full" in n and "131 Hz" in n for n in fnotes), fnotes
    # Garbage and nonsense stages degrade to "no all-pass", and the rest of the file survives.
    junk = _session()
    junk["pairs"][1]["left"].update(allPassType="SomeGarbage", allPassFrequencyHz=120, allPassQ=2.5)
    junk["pairs"][1]["right"].update(allPassType="SecondOrder", allPassFrequencyHz=300, allPassQ=0)
    jm, jnotes = migrate_session(junk)
    assert all(b["type"] != "AllPassSecondOrder" for b in jm["pairs"][1]["left"]["peqBands"] + jm["pairs"][1]["right"]["peqBands"])
    assert sum("dropped" in n for n in jnotes) == 2, jnotes
    assert legs_of(jm)[1]["row"]["ta_ms"] == 4.71, "the rest of the side must survive"
    # v8→v9: the zone is GUESSED their way -- stereo Front, mono high-passed Center, mono else Sub.
    assert guess_zone(False, "HighPass") == "Front" and guess_zone(True, "HighPass") == "Center"
    assert guess_zone(True, "LowPass") == "Sub" and guess_zone(True, "Off") == "Sub"
    assert [leg["zone"] for leg in legs_of(_session())] == ["sub", "front", "front", "sub"]
    assert any("GUESSED" in n for n in notes), notes
    # v10 as the app writes it: the zone is READ, not guessed; the angle becomes the row's
    # phase_deg; the bank's all-pass is an APF2 band; an absent angle is 0.
    t = _session_v10()
    t_legs = legs_of(t)
    assert [leg["zone"] for leg in t_legs] == ["sub", "front", "front", "center"], [leg["zone"] for leg in t_legs]
    assert t_legs[0]["row"]["eq"][-1] == {"type": "APF2", "f": 120.0, "i": 2, "q": 2.5}, t_legs[0]["row"]["eq"]
    assert t_legs[1]["row"]["phase_deg"] == 90.0 and t_legs[2]["row"]["phase_deg"] == 0.0
    assert t_legs[1]["phase_reference"] == {"kind": "hp", "hz": 65.0, "dormant": False}, t_legs[1]["phase_reference"]
    # The Center block's HP is dormant (kind LowPass) and 45° is stated at it: the row carries
    # the HP with slope OFF -- configured, not active -- so the angle keeps its reference, and
    # the edge is no longer listed as merely dormant.
    orphan = t_legs[3]
    assert orphan["row"]["hp"] == {"f": 300.0, "type": "LR", "slope": "OFF", "family": "LinkwitzRiley"}, orphan["row"]["hp"]
    assert orphan["phase_reference"] == {"kind": "hp", "hz": 300.0, "dormant": True} and "hp" not in orphan["dormant"]
    assert orphan["row"]["lp"]["f"] == 2000.0, "the live LP (the C# default) is untouched"
    # A Sub block states its angle at the LP: the row's reference is the LP.
    sub10 = _session_v10()
    sub10["pairs"][0]["left"]["phaseRotationDegrees"] = 180.0
    assert legs_of(sub10)[0]["phase_reference"] == {"kind": "lp", "hz": 65.0, "dormant": False}
    # An angle outside their Validate() range is refused, not clamped.
    bad = _session_v10()
    bad["pairs"][1]["left"]["phaseRotationDegrees"] = 360.0
    try:
        legs_of(bad)
    except SessionError as exc:
        assert "phaseRotationDegrees" in str(exc), exc
    else:
        raise AssertionError("an angle of 360 was read")
    # ── the phase verdicts ─────────────────────────────────────────────────────
    phased = json.loads(json.dumps(profile))
    phased["dsp_profile"]["phase_control"] = {"range_deg": [0.0, 354.375], "step_deg": 5.625}
    pres = convert(t, profile=phased, proj=_Proj(), source_path="<v10>")
    assert pres["source"]["version"] == 10 and pres["source"]["read_as"] == 10 and pres["source"]["migration"] == []

    def pv(res, channel, field):
        return [c for leg in res["legs"] for c in leg["checks"] if c["channel"] == channel and c["field"] == field]
    # w-L, zone front, 90° at its HP: on the grid, in range, and the ledger reads `w-L` at the HP too.
    assert pv(pres, "w-L", "phase_deg")[0]["verdict"] == OK, pv(pres, "w-L", "phase_deg")
    assert pv(pres, "w-L", "phase_deg.reference")[0]["verdict"] == OK, pv(pres, "w-L", "phase_deg.reference")
    assert not pv(pres, "w-R", "phase_deg"), "an angle of 0 is nothing to enter"
    # The unbound Center block: the number checks, the corner cannot -- said, not guessed.
    assert pv(pres, "nosuch", "phase_deg.reference")[0]["verdict"] == UNKNOWN
    # A step the control does not have is refused; a profile without the block is unknown.
    off_grid = _session_v10()
    off_grid["pairs"][1]["left"]["phaseRotationDegrees"] = 91.0
    assert pv(convert(off_grid, profile=phased, proj=_Proj()), "w-L", "phase_deg")[0]["verdict"] == UNSUPPORTED
    assert pv(convert(t, profile=profile, proj=_Proj()), "w-L", "phase_deg")[0]["verdict"] == UNKNOWN
    # THE trap: a Sub block (angle at the LP) bound to a code the ledger reads at the HP. Same
    # number, different filter -- refused by name. Bound to `sw`, the corners agree.
    trap = _session_v10()
    trap["pairs"][0]["left"]["phaseRotationDegrees"] = 180.0
    wrong = convert(trap, profile=phased, proj=_Proj(), mapping={"sw": "m-L"})
    ref = pv(wrong, "m-L", "phase_deg.reference")[0]
    assert ref["verdict"] == UNSUPPORTED and "LP" in ref["reason"] and "HP" in ref["reason"], ref
    right = convert(trap, profile=phased, proj=_Proj())
    assert pv(right, "sw", "phase_deg.reference")[0]["verdict"] == OK
    # ...and the local corner rule IS predict's rule, on the codes that matter, when predict can load.
    try:
        import predict as _predict
    except ImportError:                      # stdlib-only environment: the rule is the same text
        pass
    else:
        for code in ("sw", "sw-f", "sub", "SW_R", "w-L", "m-R", "tw-L", "c", "s-L"):
            assert _ledger_reads_lp(code) == _predict._is_sub(code), code
    # The report says what was read, what migrated, and which corner an angle sits on.
    text10 = report(pres)
    assert "zone front" in text10 and "phase 90 deg @ HP 65 Hz" in text10, text10
    assert "phase 45 deg @ HP 300 Hz  (that edge is dormant" in text10, text10
    text7 = report(convert(_session(), profile=phased, proj=_Proj(), source_path="<v7>"))
    assert "v7 (read as v10)" in text7 and "migrated    v7→v8" in text7 and "GUESSED" in text7, text7

    # Q bounded per band type (hub #36 / RES-002): a Helix takes a bell to Q 50 and a SHELF only
    # to 2, so one range for every type both refuses legitimate shelves and passes impossible ones.
    peq_by_type = {"gain_range_db": [-30.0, 12.0], "gain_step_db": 0.1,
                   "freq_range_hz": [10.0, 40000.0], "freq_step_hz": 0.01,
                   "q_range": [0.5, 50.0], "q_step": 0.1,
                   "q_range_by_type": {"LSH": [0.3, 2.0], "HSH": [0.3, 2.0]}}
    shelf_low = {"i": 1, "type": "LSH", "f": 100.0, "gain_db": 3.0, "q": 0.3}
    shelf_high = {"i": 2, "type": "LSH", "f": 100.0, "gain_db": 3.0, "q": 30.0}
    bell_high = {"i": 3, "type": "PK", "f": 100.0, "gain_db": 3.0, "q": 30.0}
    ok_shelf = _check_band_numbers("A", "eq[1]", "LSH", shelf_low, peq_by_type)[0]
    bad_shelf = _check_band_numbers("A", "eq[2]", "LSH", shelf_high, peq_by_type)[0]
    ok_bell = _check_band_numbers("A", "eq[3]", "PK", bell_high, peq_by_type)[0]
    assert ok_shelf["verdict"] == OK, ok_shelf          # 0.3 is legal for a shelf, below q_range
    assert bad_shelf["verdict"] == UNSUPPORTED, bad_shelf   # 30 is legal for a bell, not a shelf
    assert ok_bell["verdict"] == OK, ok_bell
    # ...and a profile that declares no override behaves exactly as before.
    plain = dict(peq_by_type)
    plain.pop("q_range_by_type")
    assert _check_band_numbers("A", "eq[1]", "LSH", shelf_low, plain)[0]["verdict"] == UNSUPPORTED

    print(f"selftest OK -- {len(legs)} legs from {len(doc['pairs'])} pairs; LR48 refused (not rounded to LR36); "
          f"dormant HP 10 Hz withheld; delay unverifiable without max_ms; "
          f"Q bounded per band type (shelf 0.3 ok, shelf 30 refused, bell 30 ok); "
          f"no profile => {blind['summary'][UNKNOWN]} unknown, 0 ok; "
          f"v7..v10 read and migrated in memory (all-pass into the bank incl. a full one, zone guessed "
          f"their way, v11 refused); v10 zone read, phase_deg with its reference (a dormant edge kept "
          f"with slope OFF), a sub angle bound to a non-sub code refused")


if __name__ == "__main__":
    import console                       # issue #21: a code page must not destroy a result
    console.install()
    if "--selftest" in sys.argv:
        _selftest()
    elif "--write-fixture" in sys.argv:
        os.makedirs(os.path.dirname(FIXTURE), exist_ok=True)
        for _path, _builder in ((FIXTURE, _session), (FIXTURE_V10, _session_v10)):
            with open(_path, "w", encoding="utf-8") as _f:
                _f.write(_fixture_text(_builder))
            print(f"wrote {_path}")
    else:
        sys.exit(main())
