"""Resonalyze Virtual DSP session (`resonalyze-virtual-crossover` v7)  →  ledger rows.

The mirror of `resonalyze_ir.py`: that one writes REW measurements INTO Resonalyze, this one
reads a tune BACK OUT of it. The occasion was DIMOSUS sending his own tune of the Passat as two
Virtual DSP sessions over our block-A IRs (2026-08-23); the point is that anybody's Virtual DSP
session can be read as a proposal against our own ledger, in one place both the terminal and a
GUI call.

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

Format skew, seen in the wild and handled: in the v7 files DIMOSUS writes, `enabled`/`bypass` sit
on the PAIR, while the fork checkout's `VirtualCrossoverChannelSettings` carries them on the SIDE.
Both are read, side first.

    resonalyze_vc.py <session.json> --project <dir>          # human report
    resonalyze_vc.py <session.json> --project <dir> --json    # the same as machine JSON

Exit codes: 0 every check passed · 1 something the target DSP cannot enter · 2 nothing blocking
but something unverifiable (no profile, or a limit the profile does not declare).

stdlib only, py3.9+.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

CONVERTER = "autosound-tuning-skill rew_tool/resonalyze_vc.py"
CONVERTER_VERSION = "1.0 (2026-08-23, format v7 as of Resonalyze VirtualCrossoverProjectFile.cs)"

FORMAT = "resonalyze-virtual-crossover"
SUPPORTED_VERSIONS = (7,)

#: Resonalyze crossover family -> the ledger's short type code.
FAMILY_TO_TYPE = {
    "Butterworth": "BW",
    "LinkwitzRiley": "LR",
    "Bessel": "BE",
    "Chebyshev": "CHEBYSHEV",
}
#: Resonalyze PEQ band type -> `state.EQ_TYPES`.
BAND_TO_EQ_TYPE = {"Peaking": "PK", "LowShelf": "LSH", "HighShelf": "HSH"}
#: Resonalyze all-pass stage -> `state.EQ_TYPES`. A first-order section takes no Q.
ALLPASS_TO_EQ_TYPE = {"FirstOrder": "APF1", "SecondOrder": "APF2"}

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
        with open(path) as f:
            doc = json.load(f)
    except OSError as exc:
        raise SessionError(f"cannot read {path}: {exc}") from exc
    except ValueError as exc:
        raise SessionError(f"{path} is not JSON: {exc}") from exc
    return validate_session(doc, path)


def validate_session(doc, path="<session>"):
    """Refuse anything that is not a v7 Virtual DSP session, loudly and by name.

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
            f"{path}: version {version!r}, this converter reads {list(SUPPORTED_VERSIONS)}")
    pairs = doc.get("pairs")
    if not isinstance(pairs, list):
        raise SessionError(f"{path}: 'pairs' must be a list, got {type(pairs).__name__}")
    if not pairs and doc.get("channels"):
        raise SessionError(
            f"{path}: no 'pairs', but the legacy flat 'channels' list has "
            f"{len(doc['channels'])} entr{'y' if len(doc['channels']) == 1 else 'ies'} -- this is "
            "a pre-pairs session and reading it as empty would lose the whole tune")
    return doc


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

    eq, dropped = _eq_bands(raw)
    row = {
        "hp": _edge(raw.get("highPassEdge")) if live_hp else None,
        "lp": _edge(raw.get("lowPassEdge")) if live_lp else None,
        "gain_db": _num(raw.get("gainDb"), 0.0),
        "ta_ms": _num(raw.get("delayMs"), 0.0),
        "polarity": "INV" if raw.get("invertPolarity") else "NORM",
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
        freq = _num(raw.get("frequencyHz"), 0.0)
        q = _num(raw.get("q"), 0.0)
        gain = _num(raw.get("gainDb"), 0.0)
        kind = raw.get("type", "Peaking")
        entry = {
            "type": BAND_TO_EQ_TYPE.get(kind, kind),
            "f": freq,
            "gain_db": gain,
            "q": q,
            "i": len(bands) + 1,
        }
        if gain == 0 or q <= 0 or freq <= 0:
            dropped.append(dict(entry, reason="transparent: contributes nothing"))
            continue
        bands.append(entry)

    all_pass = side.get("allPassType", "Off")
    if all_pass and all_pass != "Off":
        eq_type = ALLPASS_TO_EQ_TYPE.get(all_pass)
        if eq_type is None:
            raise SessionError(f"allPassType {all_pass!r} is not one of {list(ALLPASS_TO_EQ_TYPE)}")
        band = {"type": eq_type, "f": _num(side.get("allPassFrequencyHz"), 0.0),
                "i": len(bands) + 1}
        # A first-order section is a single real pole and has no Q at all; the ledger's `q` is
        # optional for exactly this case.
        if eq_type == "APF2":
            band["q"] = _num(side.get("allPassQ"), 0.0)
        bands.append(band)
    return bands, dropped


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
    out += _check_preamp(leg, channel)
    out += _check_state(leg, channel)
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
    """Frequency / gain / Q of one band against `parametric_eq`'s ranges and steps."""
    if not isinstance(peq, dict):
        return [_verdict(channel, field, wanted, UNKNOWN,
                         "profile has no 'parametric_eq' block, so the band's numbers "
                         "cannot be checked", unverified=["parametric_eq"])]
    problems, verified, unverified = [], [], []
    for key, value, rng_key, step_key, unit in (
        ("frequency", band.get("f"), "freq_range_hz", "freq_step_hz", "Hz"),
        ("gain", band.get("gain_db"), "gain_range_db", "gain_step_db", "dB"),
        ("Q", band.get("q"), "q_range", "q_step", ""),
    ):
        if value is None:                     # an APF1 has no Q and no gain -- not a gap
            continue
        rng, step = peq.get(rng_key), peq.get(step_key)
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
    rng, step = gain.get("range_db"), gain.get("step_db")
    if isinstance(rng, list) and len(rng) == 2 and not (rng[0] <= value <= rng[1]):
        return [_verdict(channel, "gain_db", wanted, UNSUPPORTED,
                         f"outside the DSP's {_g(rng[0])}..{_g(rng[1])} dB range")]
    if step is not None and not _on_grid(value, step):
        return [_verdict(channel, "gain_db", wanted, UNSUPPORTED,
                         f"not a multiple of the DSP's {_g(step)} dB step")]
    if not isinstance(rng, list) or step is None:
        return [_verdict(channel, "gain_db", wanted, UNKNOWN,
                         "channel_gain states no complete range_db + step_db",
                         unverified=["channel_gain.range_db", "channel_gain.step_db"])]
    return [_verdict(channel, "gain_db", wanted, OK, "within the DSP's channel-gain range")]


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
            "version": doc.get("version"),
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
                entry = gaps.setdefault(key, {"key": key, "checks": 0, "fields": set()})
                entry["checks"] += 1
                entry["fields"].add(check["field"].split("[")[0])
    return [dict(g, fields=sorted(g["fields"]))
            for g in sorted(gaps.values(), key=lambda g: -g["checks"])]


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
                 f"  ->  ledger rows (status: proposed)")
    lines.append(f"  file        {result['source']['path']}")
    lines.append(f"  saved       {scene['saved_at_utc']}")
    lines.append(f"  calibration {scene['calibration_id']!r}"
                 + ("" if scene["calibration_id"] else "  (none -- IRs treated as uncalibrated)"))
    lines.append(f"  stereo      scene offset {_g(scene['stereo_scene_offset_ms'])} ms"
                 f" ({'RHD' if scene['stereo_right_hand_drive'] else 'LHD'}),"
                 f" {_g(scene['stereo_near_side_cut_db'])} dB cut on the"
                 f" {scene['stereo_near_side']} (near) side")
    lines.append("              ^ the AIM of Auto delay / gain balance, already inside the "
                 "per-leg numbers below")
    target = scene.get("target") or {}
    lines.append(f"  target      {target.get('preset')} at {scene['target_level_db']:+g} dB")
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
        lines.append(f"{head}   pair {leg['pair']} {leg['side']}"
                     + (f"   [{', '.join(flags)}]" if flags else ""))
        lines.append(f"    source  {leg['source_relative_path'] or leg['display_name']}")
        if not leg["channel"]:
            lines.append("    UNBOUND -- no channel in project.json answers to this name; "
                         "bind it with --map before using the row")
        row = leg["row"]
        lines.append(f"    HP {_leg_str(row['hp'])}    LP {_leg_str(row['lp'])}"
                     f"    gain {row['gain_db']:+g} dB    delay {_g(row['ta_ms'])} ms"
                     f"    {row['polarity']}")
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
            lines.append(f"  {gap['key']} not stated"
                         f"  ->  {gap['checks']} checks on {', '.join(gap['fields'])}")
        lines.append("")

    lines.append(f"{summary['legs']} legs · {summary[OK]} enterable · "
                 f"{summary[UNSUPPORTED]} NOT enterable · {summary[UNKNOWN]} unverifiable"
                 + (f" · {summary['unbound']} unbound" if summary["unbound"] else ""))
    if summary["blocked"]:
        lines.append("BLOCKED: nothing was rounded to fit. Decide each 'NO' above by hand -- "
                     "a substitute filter is a tuning decision, not a conversion.")
    return "\n".join(lines)


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
        "target": {"preset": "CarBass"}, "smoothingInverseOctaves": 6,
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
        ],
    }
    doc.update(over)
    return doc


def _profile():
    """A Helix-shaped profile: LR stops at 36, 1 Hz corners, a delay step and NO delay ceiling."""
    return {"dsp_profile": {
        "name": "Test DSP", "vendor": "Test", "sample_rate_hz": 96000,
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


def _selftest():
    doc = _session()
    legs = legs_of(doc)

    # The mono pair's empty right side is not a channel, and a mono pair yields ONE row.
    assert len(legs) == 3, [f"{l['pair']}.{l['side']}" for l in legs]
    sub, w_l, w_r = legs

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
    assert [leg["channel"] for leg in legs] == ["sw", "w-L", "w-R"], legs
    # A measurement tag falls away at the `-`, but only after the full name has been tried.
    tagged = [{"channel_hint": "m_L-ctl1", "display_name": ""}]
    bind_channels(tagged, _Proj())
    assert tagged[0]["channel"] == "m-L", tagged

    # ── the verdicts ──────────────────────────────────────────────────────────
    profile = _profile()
    result = convert(doc, profile=profile, proj=_Proj(), source_path="<selftest>")

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
    assert loose["summary"]["unbound"] == 3, loose["summary"]
    assert all(leg["channel"] is None for leg in loose["legs"])
    assert "UNBOUND" in report(loose)

    text = report(result)
    assert "BLOCKED" in text and "LR48" in text and "NOT live" in text, text

    print(f"selftest OK -- {len(legs)} legs from 2 pairs; LR48 refused (not rounded to LR36); "
          f"dormant HP 10 Hz withheld; delay unverifiable without max_ms; "
          f"no profile => {blind['summary'][UNKNOWN]} unknown, 0 ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        sys.exit(main())
