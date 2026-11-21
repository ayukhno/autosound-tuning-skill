"""One version of the journal against a saved `.pct6` (#218 T2) or a Mosconi `.PR15` (#219 T7, `_compare_pr` below):
`apply.py <project-dir> compare-file <version> FILE`.

Read only, everywhere: the file is opened for reading, hashed before it is read and after, and nothing is written --
not beside the file, not into the project, not into the journal. The contract is `rew_tool/CONTRACT.md` item 13.

What is compared and how:

* the file is read by `helix_pct6` (`read_pct6`, `interpret`); every value is compared by `helix_pct6.check`, one
  call for the whole version -- this module only says which path holds which of the version's values, and in what
  unit (`_PLAN` below);
* a channel row of the version reaches the file through `project.json`: its `slot` and the row's tier name the output
  the reader labels with that letter or number (tier `channels`: `Output <slot>`, on the V EIGHT `Amp Out` / `Line
  Out <slot>`) or `Virtual <slot>` (tier `virtual_channels`, only a channel PC-Tool shows). A row with no such output
  is `unknown`, and so is every visible output no row reaches;
* a value one side holds and the other does not record or decode is a row too, `unknown` with its reason, never a
  match and never dropped. A value the version leaves unstated is not read as its default: the version did not say
  it. `check`'s `missing` (the file holds no value at the path) is passed on as `unknown` with that reason;
* an EQ band is paired with the file's band in the slot its `i` names; a band with no `i` with the first band of the
  same type at the same frequency. A band of the version the file does not hold, and an active band of the file the
  version does not hold, differ: the file's EQ is decoded in full. A file band that is bypassed or neutral does
  nothing and is not reported unless the version names it.

Rows are `{parameter, channel, journal, file, result, category, reason, path}`, `result` in match / differs /
unknown, every audio row first. Format documented by amATFpct6.
"""

import hashlib
import importlib.util
import math
import os
import re
import sys

#: The shape's name and version, the value of the JSON's `contract` key (CONTRACT.md item 13).
CONTRACT = "compare-file.v1"
RESULTS = ("match", "differs", "unknown")
#: Audio first; the rest in the order `helix_pct6.compare` lists its categories.
CATEGORY_ORDER = ("audio", "system", "naming", "ui_state", "save_metadata", "structure", "unknown")
EXIT_COMPARED, EXIT_JOURNAL, EXIT_UNREADABLE, EXIT_CHANGED = 0, 1, 2, 3
#: A row's fields that are the journal's own bookkeeping, no setting of the DSP: not compared, said in item 13.
BOOKKEEPING = ("status", "eq_ptr", "tag")
_TIER_LABEL = {"channels": "Output", "virtual_channels": "Virtual"}
#: A delay of a model whose clock is not checked, the file stating none: its steps are not read as ms at an assumed rate.
CLOCK_ASSUMED = "the file states no clock and this model's is not checked: its delay steps are not read as ms at an " \
                "assumed 96 kHz"
_POLARITY = {"NORM": "0", "INV": "1"}
_POLARITY_BACK = {"0": "NORM", "1": "INV"}
#: The journal's EQ band types -> the file's codes (`helix_pct6.inventory.EQ_TYPES`).
_EQ_CODES = {"PK": 17, "LSH": 3, "HSH": 4, "APF1": 19, "APF2": 20}
_EQ_NAMES = {1: "Fine EQ", 3: "LSH", 4: "HSH", 17: "PK", 19: "APF1", 20: "APF2"}
_EQ_WITH_GAIN = ("PK", "LSH", "HSH")
#: The journal's crossover families -> the reader's family names (`helix_pct6.inventory.CROSSOVER_TYPES`).
_XO_FAMILY = {"LR": "Linkwitz", "BW": "Butterworth", "BE": "Bessel", "CH": "Chebyshev", "CHEBYSHEV": "Chebyshev",
              "SD": "Self-define", "SELF_DEFINED": "Self-define"}
#: Written as the profiles and the Mosconi reader spell the two (S-136.3); `_XO_FAMILY` above reads both spellings.
_XO_SHORT = {"Linkwitz": "LR", "Butterworth": "BW", "Bessel": "BE", "Chebyshev": "CHEBYSHEV", "Self-define": "SELF_DEFINED"}
#: Tolerances: exact to what PC-Tool shows, a Q to 0.005 (a shelf's 0.71 in the journal is the file's 0.707).
_TOL_DB, _TOL_HZ, _TOL_Q, _TOL_DEG = 0.005, 0.005, 0.005, 0.001
_RTC_KEY = re.compile(r"^([GVF])(START|STOP)([01])$")


def _siblings():
    """`rew_tool/siblings.py`, by its path: how this module reaches a sibling (skill #137).

    The same text in every module that loads a sibling -- only the `here` line differs with the file's folder;
    scripts/contract-guard.py holds the copies identical.
    """
    import hashlib
    import importlib.util
    here = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    name = "_autosound_" + hashlib.sha1(here.encode("utf-8")).hexdigest()[:8] + "_siblings"
    module = sys.modules.get(name)
    if module is None:
        spec = importlib.util.spec_from_file_location(name, os.path.join(here, "siblings.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # Published only once it has run: a thread racing this first call never gets a half-run siblings.py.
        module = sys.modules.setdefault(name, module)
    return module


def _state():
    """`state/state.py`: the journal, one module object with the one `apply.py` imports."""
    return _siblings().load("state/state.py")


def _helix():
    """The `helix_pct6` package of this copy of the method, by its path: one package object per process. A copy already
    imported (`import helix_pct6`, its `__main__`) is adopted; otherwise it is loaded under a name tied to this copy,
    so its relative imports resolve inside it."""
    sib = _siblings()
    init = sib.path_of("helix_pct6/__init__.py")
    with sib._LOCK:
        found = sib.find_loaded(init)
        if found is not None:
            return found
        name = sib.module_name("helix_pct6")
        spec = importlib.util.spec_from_file_location(name, init, submodule_search_locations=[os.path.dirname(init)])
        if spec is None or spec.loader is None:
            raise ImportError(f"compare_file: {init} cannot be loaded")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        try:
            spec.loader.exec_module(module)
        except BaseException:
            for key in [k for k in sys.modules if k == name or k.startswith(name + ".")]:
                sys.modules.pop(key, None)
            raise
        return module


def _sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


# ---------------------------------------------------------------------------------------------------- the journal

def load_version(project_dir, version, preset=None):
    """`(version, snapshot)` of the project's journal, read only. `version` is `v_NNN` or `HEAD` (the slot's version:
    `preset`, else the active slot). Raises `ValueError` (a `SnapshotError` among them) for a version not there."""
    st = _state()
    root = os.path.join(project_dir, "state")
    layout = st.ledger_layout(root)
    if preset is None:
        preset = st.Registry(root).get_active()
    if not preset and (layout == "preset" or str(version).upper() == "HEAD"):
        raise ValueError(f"no active slot in {root} -- pass --preset")
    history = st.PresetHistory(root, preset or "", project_dir=project_dir)
    name = history.head() if str(version).upper() == "HEAD" else version
    if not name:
        raise ValueError(f"the slot {preset!r} holds no version in {root}")
    try:
        return name, history.load(name)
    except FileNotFoundError as exc:
        raise ValueError(f"no version {name!r} in {root}") from exc


# ---------------------------------------------------------------------------------------------------- the plan
# A planned row is a dict: parameter, channel, journal, and either `expect` ({path, expected, policy, tolerance}) with
# `show` (the file's raw value -> the journal's unit) -- compared by `helix_pct6.check` -- or a ready `result`, `file`,
# `reason`, `category`, `path` for a row nothing in the file can be compared with.

def _compared(parameter, channel, journal, path, expected, policy, show=None, tolerance=None, confirm=None):
    expect = {"path": path, "expected": expected, "policy": policy}
    if tolerance is not None:
        expect["tolerance"] = tolerance
    return {"parameter": parameter, "channel": channel, "journal": journal, "expect": expect, "show": show,
            "confirm": confirm}


def _said(parameter, channel, journal, file, result, reason, category=None, path=None):
    """A row built without `compare.check`. Its category is the one `check` would give its path; a row with no path
    is `audio`, except a preset setting other than a source level or the input gain, which is `system` (item 13)."""
    if category is None:
        if path is not None:
            category = _helix().compare.category(path)
        elif channel == "preset" and not (parameter.startswith("sources.") or parameter == "input_gain_db"):
            category = "system"
        else:
            category = "audio"
    return {"parameter": parameter, "channel": channel, "journal": journal, "file": file, "result": result,
            "reason": reason, "category": category, "path": path}


def _number(raw):
    try:
        return float(raw)
    except (TypeError, ValueError):
        return raw


def _leg_text(leg):
    """A crossover leg of the reader, as the file holds it."""
    if not leg or "position" not in leg:
        return None
    family = _XO_SHORT.get(leg.get("family"), "code %s" % leg.get("type_code"))
    if leg.get("state") == "off":
        return "OFF (stored: %s at %g Hz)" % (family, leg.get("frequency_hz") or 0)
    gain = _number(leg["raw"].get("G"))
    slope = (-gain + 0.0) if isinstance(gain, float) else gain
    text = "%s %s dB/oct at %g Hz" % (family, "%g" % slope if isinstance(slope, float) else slope,
                                     leg.get("frequency_hz") or 0)
    return text + " (bypassed)" if leg.get("state") == "bypassed" else text


def _band_text(band):
    """An EQ band of the reader, as the file holds it."""
    text = "%s %g Hz" % (_EQ_NAMES.get(band.get("type_code"), "code %s" % band.get("type_code")),
                         band.get("frequency_hz") or 0)
    if band.get("gain_db") is not None:
        text += " %+g dB" % band["gain_db"]
    if band.get("q_applies") and band.get("q") is not None:
        text += " Q%g" % band["q"]
    return text + (" (bypassed)" if band.get("bypass") else "")


def _channel_rows(code, tier, row, ch, base):
    """The planned rows of one channel row of the version against the reader's channel `ch` (its OC at `base`)."""
    out = []
    timing = ch["timing"][0] if ch.get("timing") else {}
    not_recorded = "the version does not record it"
    for field in sorted(row):
        if field in BOOKKEEPING or field in ("gain_db", "ta_ms", "polarity", "phase_deg", "mute", "off", "eq",
                                             "eq_bypass", "hp", "lp"):
            continue
        out.append(_said(field, code, row[field], None, "unknown", "a field this comparison does not know"))
    # level, delay, polarity
    if row.get("gain_db") is not None:
        out.append(_compared("gain_db", code, row["gain_db"], base + "/Vol[1]/@L", row["gain_db"], "db",
                             tolerance=_TOL_DB))
    else:
        out.append(_said("gain_db", code, None, ch["level"]["value"], "unknown", not_recorded, path=base + "/Vol[1]/@L"))
    delay = timing.get("delay") or {}
    if delay.get("clock_assumed"):
        out.append(_said("ta_ms", code, row.get("ta_ms"), None, "unknown", CLOCK_ASSUMED, path=base + "/T[1]/@T"))
    elif row.get("ta_ms") is not None:
        out.append(_compared("ta_ms", code, row["ta_ms"], base + "/T[1]/@T", row["ta_ms"], "display_delay_ms"))
    else:
        out.append(_said("ta_ms", code, None, delay.get("display_ms"), "unknown", not_recorded, path=base + "/T[1]/@T"))
    if row.get("polarity") in _POLARITY:
        out.append(_compared("polarity", code, row["polarity"], base + "/@CINV", _POLARITY[row["polarity"]], "raw",
                             show=_POLARITY_BACK.get))
    else:
        out.append(_said("polarity", code, row.get("polarity"), ch.get("polarity"), "unknown", not_recorded,
                         path=base + "/@CINV"))
    # phase: a value only where the version states one or the file's channel has the phase control
    if row.get("phase_deg") is not None:
        out.append(_compared("phase_deg", code, row["phase_deg"], base + "/T[1]/@P", row["phase_deg"], "number",
                             show=_number, tolerance=_TOL_DEG))
    elif timing.get("phase_mode") == "phase_adjustable":
        out.append(_said("phase_deg", code, None, timing.get("phase_degrees"), "unknown", not_recorded,
                         path=base + "/T[1]/@P"))
    # mute, and the switches the file does not decode or does not establish
    if row.get("mute") is not None:
        out.append(_compared("mute", code, row["mute"], base + "/@MT", "0" if row["mute"] else "1", "raw",
                             show={"0": True, "1": False}.get))
    else:
        out.append(_said("mute", code, None, ch.get("mute_on"), "unknown", not_recorded, path=base + "/@MT"))
    if row.get("off") is not None:
        out.append(_said("off", code, row["off"], None, "unknown", "the file decodes no such switch"))
    if row.get("eq_bypass") is not None:
        out.append(_compared("eq_bypass", code, row["eq_bypass"], base + "/@EqBy", "1" if row["eq_bypass"] else "0",
                             "raw", show={"0": False, "1": True}.get))
    # crossovers
    for leg in ("hp", "lp"):
        if leg not in row:
            continue
        side = "high_pass" if leg == "hp" else "low_pass"
        out += _leg_rows(code, leg, row[leg], ch.get(side), base, tier)
    out += _eq_rows(code, row, ch, base)
    return out


def _leg_rows(code, leg, want, have, base, tier):
    if tier != "channels" and want in (None, "OFF"):
        return []
    if not have or "position" not in have:
        file_side = "the file holds no %s filter for this channel" % ("high-pass" if leg == "hp" else "low-pass")
        return [_said(leg, code, want, None, "unknown", file_side, path=base)]
    path = base + "/Fil[%d]" % have["position"]
    if want in (None, "OFF"):
        return [_compared(leg + ".slope", code, "OFF", path + "/@G", 0, "number", tolerance=0.0,
                          show=lambda _raw, have=have: _leg_text(have))]
    direction = "HP" if leg == "hp" else "LP"
    family = _XO_FAMILY.get(str(want.get("type", "")).upper())
    codes = {(f, d): (c, conf) for c, (f, d, conf) in _CROSSOVER_TYPES().items()}
    found = codes.get((family, direction))
    rows = []
    if found is None:
        rows.append(_said(leg + ".type", code, want.get("type"), _XO_SHORT.get(have.get("family"), have.get("family")),
                          "unknown", "the file has no code for the type %r" % want.get("type"), path=path + "/@T"))
    else:
        type_code, confidence = found
        confirm = None if confidence == "confirmed" else (
            "the file's code for %s is documented, not confirmed on a saved file" % family)
        rows.append(_compared(leg + ".type", code, want.get("type"), path + "/@T", str(type_code), "raw",
                              show=lambda raw: _XO_SHORT.get(_CROSSOVER_TYPES().get(int(raw), (None,))[0], "code " + raw)
                              if str(raw).isdigit() else raw, confirm=confirm))
    if want.get("f") is not None:
        rows.append(_compared(leg + ".f", code, want["f"], path + "/@F", want["f"], "number", show=_number,
                              tolerance=_TOL_HZ))
    if _configured_off(want):
        # off with its corner kept: the type and the frequency above, and off is G = 0, as for an OFF leg
        rows.append(_compared(leg + ".slope", code, "OFF", path + "/@G", 0, "number", tolerance=0.0,
                              show=lambda _raw, have=have: _leg_text(have)))
    elif want.get("slope") is not None:
        rows.append(_compared(leg + ".slope", code, want["slope"], path + "/@G", -want["slope"], "number",
                              show=lambda raw: -_number(raw) if isinstance(_number(raw), float) else raw, tolerance=0.0))
    else:
        # PC-Tool keeps a leg's type and frequency when it is OFF: with no slope, the rows above say nothing of on/off
        rows.append(_said(leg + ".slope", code, None, _leg_text(have), "unknown", "the version records no slope",
                          path=path + "/@G"))
    rows.append(_compared(leg + ".bypass", code, False, path + "/@FilBy", "0", "raw", show={"0": False, "1": True}.get))
    return rows


def _CROSSOVER_TYPES():
    return _helix().inventory.CROSSOVER_TYPES


def _eq_rows(code, row, ch, base):
    slots = [f for f in ch.get("filters") or [] if f.get("role") == "eq"]
    by_position = {f["position"]: f for f in slots}
    # A band that does something, or may: configured, or of a type code the reader does not decode (state unknown).
    active = [f for f in slots if f.get("state") not in ("neutral", "bypassed")]
    if row.get("eq") is None:
        if not active:
            return []
        return [_said("eq", code, None, [_band_text(f) for f in active], "unknown",
                      "the version does not record this channel's EQ", path=base + "/Fil")]
    out, claimed, pairs = [], set(), []
    for band in row["eq"]:
        if band.get("i") is None:
            continue
        found = by_position.get(band["i"])
        if found is None:
            out.append(_said("eq[%s]" % band["i"], code, band, None, "unknown",
                             "the file holds no EQ band in slot %s" % band["i"], path=base + "/Fil"))
            continue
        claimed.add(band["i"])
        pairs.append((band, found))
    for band in row["eq"]:
        if band.get("i") is not None:
            continue
        want_code, bypass = _EQ_CODES.get(band.get("type")), bool(band.get("bypass"))
        candidates = [f for f in slots if f["position"] not in claimed and f.get("type_code") == want_code
                      and f.get("state") != "neutral" and f.get("frequency_hz") is not None
                      and abs(f["frequency_hz"] - float(band["f"])) <= _TOL_HZ]
        pick = next((f for f in candidates if f.get("bypass") == bypass), candidates[0] if candidates else None)
        if pick is None:
            out.append(_said("eq %s %g Hz" % (band.get("type"), band["f"]), code, band, None, "differs",
                             "the file holds no %s band at %g Hz" % (band.get("type"), band["f"])))
            continue
        claimed.add(pick["position"])
        pairs.append((band, pick))
    for band, found in sorted(pairs, key=lambda p: p[1]["position"]):
        name, path = "eq[%d]" % found["position"], base + "/Fil[%d]" % found["position"]
        btype = band.get("type")
        if btype in _EQ_CODES:
            out.append(_compared(name + ".type", code, btype, path + "/@T", str(_EQ_CODES[btype]), "raw",
                                 show=lambda raw: _EQ_NAMES.get(int(raw), "code " + raw) if str(raw).isdigit() else raw))
        else:
            out.append(_said(name + ".type", code, btype, _EQ_NAMES.get(found.get("type_code")), "unknown",
                             "the file has no code for the type %r" % btype, path=path + "/@T"))
        if found.get("type_code") not in _EQ_NAMES:
            # A type the reader does not decode: its frequency, gain and Q mean nothing known -- never a match.
            why = ("the file's band in slot %d is of type code %s, which this reader does not decode: its values are "
                   "not read" % (found["position"], found["raw"].get("T", "(none)")))
            for field, have, at in (("f", found.get("frequency_hz"), "/@F"), ("gain_db", found.get("gain_db"), "/@G"),
                                    ("q", found.get("q"), "/@Q")):
                if field == "f" or (field == "gain_db" and btype in _EQ_WITH_GAIN) or (field == "q" and btype != "APF1"):
                    out.append(_said("%s.%s" % (name, field), code, band.get(field), have, "unknown", why,
                                     path=path + at))
            out.append(_compared(name + ".bypass", code, bool(band.get("bypass")), path + "/@FilBy",
                                 "1" if band.get("bypass") else "0", "raw", show={"0": False, "1": True}.get))
            continue
        out.append(_compared(name + ".f", code, band["f"], path + "/@F", band["f"], "number", show=_number,
                             tolerance=_TOL_HZ))
        if btype in _EQ_WITH_GAIN:
            if band.get("gain_db") is not None:
                out.append(_compared(name + ".gain_db", code, band["gain_db"], path + "/@G", band["gain_db"], "number",
                                     show=_number, tolerance=_TOL_DB))
            else:
                out.append(_said(name + ".gain_db", code, None, found.get("gain_db"), "unknown",
                                 "the version records no gain for this band", path=path + "/@G"))
        if btype != "APF1":
            if band.get("q") is not None:
                out.append(_compared(name + ".q", code, band["q"], path + "/@Q", band["q"], "number", show=_number,
                                     tolerance=_TOL_Q))
            else:
                out.append(_said(name + ".q", code, None, _number(found["raw"].get("Q")), "unknown",
                                 "the version records no Q for this band", path=path + "/@Q"))
        out.append(_compared(name + ".bypass", code, bool(band.get("bypass")), path + "/@FilBy",
                             "1" if band.get("bypass") else "0", "raw", show={"0": False, "1": True}.get))
        if found.get("invert"):
            out.append(_said(name + ".invert", code, None, True, "unknown",
                             "the version cannot record an all-pass invert; the file's band is inverted",
                             path=path + "/@I"))
    for found in active:
        if found["position"] in claimed:
            continue
        path = base + "/Fil[%d]" % found["position"]
        text = _band_text(found)
        if found.get("state") != "configured":
            out.append(_said("eq[%d]" % found["position"], code, None, text, "unknown",
                             "the file holds a band of type code %s this reader does not decode"
                             % found["raw"].get("T", "(none)"), path=path + "/@T"))
            continue
        if found.get("type_code") in (19, 20):        # an all-pass turns phase at any gain: only a bypass stops it
            expect = (path + "/@FilBy", "1", "raw", None)
        else:
            expect = (path + "/@G", 0, "number", 0.0)
        planned = _compared("eq[%d]" % found["position"], code, None, expect[0], expect[1], expect[2],
                            show=lambda _raw, text=text: text, tolerance=expect[3])
        planned["note"] = "the version holds no such band"
        out.append(planned)
    return out


def _preset_rows(settings, values, root, stated_any):
    """The planned rows of the version's `preset_settings` against the file's system values (`values`: its flat
    paths). A field the version does not state is not read as its default: it is `unknown` where the file holds one."""
    st = _state()
    out = []
    not_stated = "the version does not state it (the journal reads it as %s)"

    def leaf(path):
        return st._preset_leaf(settings, path) if isinstance(settings, dict) else None

    def unstated(path, file_value, at, category="system"):
        default = st._PRESET_FIELDS[path][1]
        reason = not_stated % ("unknown" if default is None else repr(default))
        if not stated_any:
            reason = "the version records no preset settings"
        out.append(_said(path, "preset", None, file_value, "unknown", reason, category=category, path=at))

    def raw_at(path):
        return values.get(path)

    # input gain and the knob position: no value in the file to compare with
    if leaf("input_gain_db") is not None:
        out.append(_said("input_gain_db", "preset", leaf("input_gain_db"), None, "unknown",
                         "the file decodes no input gain"))
    if leaf("conductor.sub_lamps") is not None:
        out.append(_said("conductor.sub_lamps", "preset", leaf("conductor.sub_lamps"), None, "unknown",
                         "a knob's position is not stored in the file", category="system"))
    # source levels: the routing's OFFS per source (Main, HEC/AUX, Digital)
    route = root.find("Route")
    position = {}
    if route is not None:
        k = 0
        for child in route:
            if child.tag == "R":
                k += 1
                position.setdefault(child.get("AOM"), k)
    for source, aom in (("main", "1"), ("hec", "5"), ("digital", "9")):
        path = "sources." + source
        at = "/ATF/Route[1]/R[%d]/@OFFS" % position[aom] if aom in position else None
        if leaf(path) is not None:
            if at is None:
                out.append(_said(path, "preset", leaf(path), None, "unknown", "the file holds no route for this source"))
            else:
                out.append(_compared(path, "preset", leaf(path), at, leaf(path), "db", tolerance=_TOL_DB))
        elif at is not None and raw_at(at) is not None:
            linear = _number(raw_at(at))
            shown = None
            if isinstance(linear, float) and linear > 0:
                shown = round(20 * math.log10(linear), 4)
            unstated(path, shown, at, category="audio")
    # switches: (field, path, the raw value for ON, for OFF)
    switches = (("fx.realcenter", "/ATF/STX[1]/@CMOD", "1", "0"),
                ("fx.dynamic_bass", "/ATF/ABP[1]/@SWBP", "0", "1"),
                ("fx.subxpander", "/ATF/ABP[1]/@SWS", "0", "1"),
                ("rtc.on", "/ATF/MCV2[1]/@RTC_EN", "1", "0"))
    for path, at, on, off in switches:
        show = {on: True, off: False}.get
        if leaf(path) is not None:
            out.append(_compared(path, "preset", leaf(path), at, on if leaf(path) else off, "raw", show=show))
        elif raw_at(at) is not None:
            unstated(path, show(raw_at(at)), at)
    # the RTC curve: G/V in tenths of a dB, F in Hz
    curve = leaf("rtc.curve")
    stored = sorted(k for k in values if k.startswith("/ATF/MCV2[1]/@RTC_") and _RTC_KEY.match(k.rsplit("_", 1)[1]))
    if isinstance(curve, dict):
        for name, value in sorted(curve.items()):
            m = _RTC_KEY.match(str(name).upper())
            if not m:
                out.append(_said("rtc.curve." + name, "preset", value, None, "unknown",
                                 "the file holds no RTC value of this name"))
                continue
            at = "/ATF/MCV2[1]/@RTC_" + str(name).upper()
            tenths = m.group(1) != "F"
            out.append(_compared("rtc.curve." + name, "preset", value, at, value * 10 if tenths else value, "number",
                                 tolerance=0.5 if tenths else _TOL_HZ,
                                 show=(lambda raw: _number(raw) / 10 if isinstance(_number(raw), float) else raw)
                                 if tenths else _number))
    elif stored:
        unstated("rtc.curve", {k.rsplit("@RTC_", 1)[1].lower(): _number(values[k]) for k in stored}, "/ATF/MCV2[1]")
    # BT: the selector and the auto-switch bit of the input mask
    selector = next((k[:-len("/@i")] for k, v in values.items()
                     if k.startswith("/ATF/DCM") and k.endswith("/@i") and v == "0"
                     and re.search(r"/SW\[\d+\]/@i$", k)), None)
    at = selector + "/@A" if selector else None
    source = leaf("bt.source")
    if source is not None:
        raw = {"BT": "1", "AUX": "0"}.get(str(source).upper())
        if raw is None or at is None:
            out.append(_said("bt.source", "preset", source, None, "unknown",
                             "the file holds no BT/AUX selector" if at is None else "BT or AUX is all the file holds"))
        else:
            out.append(_compared("bt.source", "preset", source, at, raw, "raw", show={"1": "BT", "0": "AUX"}.get))
    elif at is not None and raw_at(at) is not None:
        unstated("bt.source", {"1": "BT", "0": "AUX"}.get(raw_at(at)), at)
    mask_at = "/ATF/MCV2[1]/@IMASK"
    mask = raw_at(mask_at)
    auto = leaf("bt.auto_switch")
    on = bool(int(mask) & 0x04) if mask is not None and mask.isdigit() else None
    if auto is not None:
        if mask is None or not mask.isdigit():
            out.append(_said("bt.auto_switch", "preset", auto, None, "unknown", "the file holds no input mask",
                             path=mask_at))
        else:
            # only the auto-switch bit is the version's; the mask's other bits stay as the file has them
            want = str((int(mask) & ~0x04) | (0x04 if auto else 0))
            out.append(_compared("bt.auto_switch", "preset", auto, mask_at, want, "raw",
                                 show=lambda raw: bool(int(raw) & 0x04) if str(raw).isdigit() else raw))
    elif on is not None:
        unstated("bt.auto_switch", on, mask_at)
    return out


def _shown_virtual(outputs):
    """The virtual channels PC-Tool shows, in index order."""
    return sorted((c for c in outputs if c.get("group") == "virtual" and c.get("visible_in_pc_tool")),
                  key=lambda c: c["index"])


def _slot_of(label):
    """The slot a reader's label names: its last word (`Output C` -> C, `Line Out 9` -> 9, `Virtual K` -> K)."""
    return str(label).rsplit(" ", 1)[-1]


def _physical_by_slot(outputs):
    """{slot: channel} for the physical outputs, the slot being the reader's own label's letter or number: Output A..L
    on the HELIX DSP ULTRA S, Amp Out 1-8 and Line Out 9-14 on the HELIX NEXT V EIGHT DSP ULTIMATE. The one place this
    rule lives."""
    return {_slot_of(c["label"]): c for c in outputs if c.get("group") == "physical" and c.get("label")}


def _physical_miss(outputs, slot):
    """Why a physical slot reaches no output, in the model's own words."""
    if all(str(c["label"]).startswith("Output ") for c in _physical_by_slot(outputs).values()):
        return "no channel PC-Tool shows is Output %s on this model" % slot
    return "no output PC-Tool shows is numbered %s on this model" % slot


def _virtual_by_letter(outputs):
    """{PC-Tool's letter: channel} for the virtual channels PC-Tool shows. The letter is the reader's own label,
    `Virtual <letter>`, the index's letter: on the HELIX DSP ULTRA S PC-Tool shows Virtual A..F, K, L, indexes 0-5, 10,
    11 (the owner's PC-Tool screen, 2026-11-21: Virtual K is the sub, the file's index 10). v3.3.2 lettered them by
    their ordinal, A..H, which put the sub at G; a project lettered so keeps its slots, and `_virtual_miss` names
    PC-Tool's letter for its G and H. The one place this rule lives."""
    return {c["label"][len("Virtual "):]: c for c in _shown_virtual(outputs)
            if str(c.get("label") or "").startswith("Virtual ")}       # the V EIGHT's numbers alike: Virtual 9 -> "9"


def _virtual_miss(outputs, slot):
    """Why a virtual slot reaches no channel: none PC-Tool shows has that letter. A single letter at whose ordinal
    PC-Tool shows a channel (a tier lettered A..H in order, v3.3.2's rule) is told that channel's letter, so the tuner
    can re-slot it."""
    why = "no channel PC-Tool shows is Virtual %s on this model" % slot
    shown = _shown_virtual(outputs)
    n = ord(slot) - ord("A") if len(slot) == 1 and "A" <= slot <= "Z" else -1
    if 0 <= n < len(shown) and shown[n].get("label"):
        nth = "%d%s" % (n + 1, {1: "st", 2: "nd", 3: "rd"}.get(n + 1, "th"))
        own = "number" if _slot_of(shown[n]["label"]).isdigit() else "letter"
        why += "; the %s virtual channel PC-Tool shows is %s: a tier lettered in order (A..H) holds it at %s, " \
               "re-slot it to its own %s" % (nth, shown[n]["label"], slot, own)
    return why


def _plan(hx, doc, inv, snap, identity):
    """Every planned row of the version against the file, in the version's order: channels by tier and slot, the
    outputs no row reaches, then the preset."""
    out, reached = [], set()
    outputs = [c for c in inv["channels"] if c["kind"] == "output"]
    physical = _physical_by_slot(outputs)
    virtual = _virtual_by_letter(outputs)
    letter_of = {c["index"]: "Virtual " + letter for letter, c in virtual.items()}
    tiers = [t for t in _state().tier_names(snap) if isinstance(snap.get(t), dict)]
    planned = []
    for tier in tiers:
        for key, row in snap[tier].items():
            entry = identity.get(key) or {}
            slot = str(entry.get("slot") or "").strip().upper()
            planned.append((tiers.index(tier), slot or "~", key, tier, row, entry, slot))
    for _order, _slot, key, tier, row, entry, slot in sorted(planned, key=lambda p: (p[0], p[1], p[2])):
        code = entry.get("code") or key
        why = None
        ch = None
        if tier not in _TIER_LABEL:
            why = "the file's channels are not mapped for the tier %r" % tier
        elif not slot:
            why = "project.json gives this channel no slot"
        elif not inv["device"].get("layout"):
            why = "this model's channel layout is not checked: no output is named by a slot"
        else:
            ch = (physical if tier == "channels" else virtual).get(slot)
            if ch is None:
                why = _physical_miss(outputs, slot) if tier == "channels" else _virtual_miss(outputs, slot)
        if ch is None:
            for field in sorted(f for f in row if f not in BOOKKEEPING):
                out.append(_said(field, code, row[field], None, "unknown", why))
            continue
        reached.add(ch["index"])
        out += _channel_rows(code, tier, row, ch, "/ATF/OC[@ON='%d']" % ch["index"])
    for ch in outputs:
        visible = ch.get("group") == "physical" or ch.get("visible_in_pc_tool")
        if not visible or ch["index"] in reached:
            continue
        state = "muted" if ch.get("mute_on") else "on"
        out.append(_said("channel", letter_of.get(ch["index"], ch["label"]), None, "%s, %s" % (ch.get("name") or "no name", state), "unknown",
                         "no row of this version is on this output", path="/ATF/OC[@ON='%d']" % ch["index"]))
    settings = snap.get(_state().PRESET_SETTINGS)
    stated = isinstance(settings, dict) and any(k not in ("status", "source_file") for k in settings)
    out += _preset_rows(settings if isinstance(settings, dict) else {}, hx.inventory.flatten(doc.root), doc.root, stated)
    return out


def _finish(hx, doc, plan):
    """The rows: every planned comparison through ONE `helix_pct6.check` call, the verdicts read back into the shape."""
    expected = [p["expect"] for p in plan if "expect" in p]
    verdicts = iter(hx.check(doc, expected))
    rows = []
    for p in plan:
        if "expect" not in p:
            rows.append({k: p[k] for k in ("parameter", "channel", "journal", "file", "result", "category", "reason",
                                           "path")})
            continue
        v = next(verdicts)
        result, reason = v["result"], v.get("reason")
        file_value = None
        if result == "missing":
            result, reason = "unknown", "the file holds no value at this path"
        else:
            raw = v.get("actual_raw")
            file_value = p["show"](raw) if p.get("show") else v.get("actual", raw)
            if isinstance(file_value, float):
                file_value = round(file_value, 4)
            if result == "unknown" and not reason:
                reason = "the meaning of this field in the file is not established"
            if result == "match" and p.get("confirm"):
                result, reason = "unknown", p["confirm"]
            if result != "unknown" and p.get("note"):
                reason = p["note"]
        if result not in RESULTS:
            result, reason = "unknown", reason or "the comparison gave %r" % v["result"]
        rows.append({"parameter": p["parameter"], "channel": p["channel"], "journal": p["journal"], "file": file_value,
                     "result": result, "category": v["category"], "reason": reason, "path": v["path"]})
    rank = {c: i for i, c in enumerate(CATEGORY_ORDER)}
    rows.sort(key=lambda r: rank.get(r["category"], len(rank)))          # stable: the version's order within one
    return rows


def _counts(rows):
    by_result = {r: 0 for r in RESULTS}
    by_category = {}
    for row in rows:
        by_result[row["result"]] += 1
        by_category.setdefault(row["category"], {r: 0 for r in RESULTS})[row["result"]] += 1
    return {"result": by_result, "category": by_category}


def _file_block(name, md5=None, saved=None, pctool=None):
    return {"name": name, "md5": md5, "saved": saved, "pctool": pctool}


def warning_uk(warning):
    """The reader's `warning` in Ukrainian (`warning_uk`, CONTRACT.md item 13): the text TCC shows in Ukrainian. Every
    warning a reader ships has one; a warning without one is a bug in this module, said, never answered in English."""
    texts = {_helix().WARNING: _helix().WARNING_UK, _mosconi().WARNING: _mosconi().WARNING_UK}
    if warning not in texts:
        raise ValueError("no Ukrainian text for the reader's warning %r" % warning[:60])
    return texts[warning]


def refusal(warning, name, kind, message, md5=None):
    """The JSON of a comparison not made: exit 1 (`journal`), 2 (the file's kind) or 3 (`changed`)."""
    return {"contract": CONTRACT, "warning": warning, "warning_uk": warning_uk(warning), "file": _file_block(name, md5),
            "error": {"kind": kind, "message": message}}


def load_journal(project_dir, version, preset=None):
    """`(snapshot, identity, dsp_settings)`: the version, `project.json`'s channels by every name a row may use, and its
    `dsp.settings` (the tuner's answers a file is compared with: a `.PR15`'s corner set, S-136.2). The journal's side,
    and the only one that raises: `ValueError` (a `SnapshotError` among them) or `OSError` -- exit 1. A caller that
    builds the journal itself may pass the pair alone: no setting is then recorded."""
    _name, snap = load_version(project_dir, version, preset)
    _check_kinds(snap)
    st = _state()
    settings = (st._project_json(project_dir).get("dsp") or {}).get("settings")
    return snap, st.project_channels(project_dir), settings if isinstance(settings, dict) else {}


def _check_kinds(snap):
    """The two fields the ledger's validators leave untyped and this comparison does arithmetic on: a leg's `slope`
    and a row's `phase_deg` must be numbers, or the version is refused here -- a journal fault, exit 1, never blamed
    on the file (exit 2 `interpret`)."""
    def number(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    for tier, rows in snap.items():
        if not isinstance(rows, dict):
            continue
        for code, row in rows.items():
            if not isinstance(row, dict):
                continue
            if row.get("phase_deg") is not None and not number(row["phase_deg"]):
                raise ValueError("%s %s: phase_deg is %r, not a number" % (tier, code, row["phase_deg"]))
            for leg in ("hp", "lp"):
                spec = row.get(leg)
                if isinstance(spec, dict) and spec.get("slope") is not None and not number(spec["slope"]) \
                        and not _configured_off(spec):
                    raise ValueError("%s %s: %s.slope is %r, not a number" % (tier, code, leg, spec["slope"]))


def _configured_off(spec):
    """A leg `{f, type, slope: "OFF"}`: the method's form for a crossover switched off with its corner still configured
    (the phase control's reference, `predict._phase_reference`)."""
    return isinstance(spec, dict) and isinstance(spec.get("slope"), str) and spec["slope"].upper() == "OFF"


def compare(project_dir, version, file_path, preset=None):
    """`(exit code, JSON object)`: the version against the file, or the refusal. Writes nothing, anywhere. A version
    that is not there raises (`load_journal`), before the file is opened; past that, see `compare_journal`."""
    return compare_journal(load_journal(project_dir, version, preset), file_path)


def compare_journal(journal, file_path):
    """`(exit code, JSON object)` for a journal `load_journal` read: the file's side, which never raises for the file.

    0 compared, whatever the rows say; 2 the file cannot be read (`error.kind`: the reader's kind -- container,
    checksum, truncated, limit, xml --, `io`, or `interpret`: it decoded and then could not be interpreted or
    compared); 3 the file changed while it was read (`changed`), which wins over a failed read: what failed was
    another file. A `.PR<n>` file goes to the Mosconi reader (`_compare_pr`), the same shape. A version this comparison
    cannot read raises `JournalFault` (a `ValueError`): the journal's, exit 1, never said as the file's."""
    if _mosconi().is_preset_path(file_path):
        return _compare_pr(journal, file_path)
    code, doc = read_doc(file_path)
    if code != EXIT_COMPARED:
        return code, doc
    return compare_doc(journal, doc, os.path.basename(file_path))


def read_doc(file_path):
    """`(0, doc)`: the `.pct6` read by `helix_pct6.read_pct6`, hashed before the read and after -- or `(2, refusal)` the
    file cannot be read, `(3, refusal)` it changed while it was read. The one read `compare-file` and `--from-file`
    share."""
    hx = _helix()
    name = os.path.basename(file_path)
    try:
        before = _sha256(file_path)
    except OSError as exc:
        return EXIT_UNREADABLE, refusal(hx.WARNING, name, "io", "the file cannot be opened: %s" % exc)

    def changed():
        try:
            return _sha256(file_path) != before
        except OSError:
            return True

    said = "the file changed while it was read: nothing was compared or taken from it -- read it again once nothing " \
           "is saving it"
    try:
        doc = hx.read_pct6(file_path)
    except (hx.Pct6Error, OSError) as exc:
        if changed():
            return EXIT_CHANGED, refusal(hx.WARNING, name, "changed", said)
        if isinstance(exc, hx.Pct6Error):
            return EXIT_UNREADABLE, refusal(hx.WARNING, name, exc.kind, str(exc))
        return EXIT_UNREADABLE, refusal(hx.WARNING, name, "io", "the file cannot be read: %s" % exc)
    if doc.input_sha256 != before or changed():
        return EXIT_CHANGED, refusal(hx.WARNING, name, "changed", said, md5=doc.input_md5)
    return EXIT_COMPARED, doc


class JournalFault(ValueError):
    """The version holds a value this comparison cannot read: the journal's fault, exit 1 -- never the file's."""


#: The policies `helix_pct6.check` does arithmetic on: the version's value handed to it must be a finite number.
_NUMBER_POLICIES = ("number", "db", "display_delay_ms")


def _check_plan(plan):
    """Every value of the version a planned row hands `helix_pct6.check` is of the kind its policy reads -- a finite
    number, or the raw text -- or `JournalFault`. Past this, a failure inside `check` is the file's value, not the
    version's."""
    for p in plan:
        expect = p.get("expect")
        if not expect:
            continue
        value = expect["expected"]
        if expect["policy"] in _NUMBER_POLICIES:
            ok = isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
        else:
            ok = isinstance(value, str)
        if not ok:
            raise JournalFault("%s %s: the version holds %r, which this comparison cannot read"
                               % (p["channel"], p["parameter"], p["journal"]))


def compare_doc(journal, doc, name, inv=None):
    """`(exit code, JSON object)`: a version (`load_journal`'s pair) against a file `read_doc` read -- `inv` its
    `helix_pct6.interpret` when the caller has it. Only the file's side is caught: its interpretation (exit 2
    `interpret`), and a value of the file `check` cannot read at a compared path once the version's own values are
    known to be of their kind (`_check_plan`). The version's side raises `JournalFault`: exit 1."""
    hx = _helix()
    snap, identity = journal[:2]

    def uninterpretable(exc):
        # The file decoded and a value in it is not what the reader takes (a delay `abc`: decimal.InvalidOperation,
        # an ArithmeticError and no ValueError; `NaN`: a ValueError): said as the file's, never as the journal's.
        return EXIT_UNREADABLE, refusal(hx.WARNING, name, "interpret", "the file decoded and could not be interpreted "
                                        "or compared (%s: %s)" % (type(exc).__name__, exc), md5=doc.input_md5)
    try:
        if inv is None:
            inv = hx.interpret(doc)
        device = hx.models.describe(doc.dev)
    except Exception as exc:  # noqa: BLE001 -- any failure of the file's interpretation is the file's, its type named
        return uninterpretable(exc)
    try:
        plan = _plan(hx, doc, inv, snap, identity)
        _check_plan(plan)
    except JournalFault:
        raise
    except (TypeError, ValueError, KeyError, AttributeError) as exc:
        raise JournalFault("the version cannot be compared (%s: %s)" % (type(exc).__name__, exc)) from exc
    try:
        rows = _finish(hx, doc, plan)
    except Exception as exc:  # noqa: BLE001 -- the version's values are checked: what fails here is the file's value
        return uninterpretable(exc)
    return EXIT_COMPARED, {
        "contract": CONTRACT, "warning": hx.WARNING, "warning_uk": hx.WARNING_UK, "device": device, "checked_model": bool(device["verified"]),
        "file": _file_block(name, doc.input_md5, inv["device"].get("saved"), doc.pc_tool_version),
        "counts": _counts(rows), "rows": rows}


# ---------------------------------------------------------------------------------------------------- a .PR15 (#219 T7)
# The Mosconi PICO 6/8-2's preset, read by `rew_tool/mosconi_pr.py`: the same rows and top level as a `.pct6`. The
# file is a byte a line, so a row's `path` is the 0-based line of the value looked at (`offset 1281`). No
# `helix_pct6.check` here: the values are compared below, with the tolerances named.

#: The journal's crossover families -> the reader's (the profile's `types`).
_PR_FAMILY = {"LR": "LR", "BW": "BW", "BE": "BE", "CH": "CHEBYSHEV", "CHEBYSHEV": "CHEBYSHEV"}
_PR_WITH_GAIN = ("PK", "LSH", "HSH")
#: A delay to half of 0.01 ms (the journal's usual precision; the file's step is 1/384 ms at 96 kHz).
_PR_TOL_MS = 0.005


def _mosconi():
    """`rew_tool/mosconi_pr.py`, the `.PR15` reader."""
    return _siblings().load("mosconi_pr.py")


def warning_for(path):
    """The warning of the reader that reads `path`: the Mosconi one for a `.PR<n>`, else `helix_pct6`'s."""
    return _mosconi().WARNING if _mosconi().is_preset_path(path) else _helix().WARNING


def _pr_profile(skipped=None):
    """The bundled profile of the model the reader reads, unwrapped, or None. `skipped`, a list, gets each library
    file that could not be read, as `(path, why)`: the profile looked for may be one of them."""
    dp = _siblings().load("dsp_profile.py")
    device = _mosconi().DEVICE
    data = dp.find_bundled(device["vendor"], device["name"], skipped=skipped)
    return dp._unwrap(data) if data else None


def _pr_numbering(profile, outputs):
    """`({project.json slot: output}, None)`, or `(None, why)` when the profile does not settle which slot is which
    output. The profile's output tier is numbered (no letter style), "1"..."N" as intake names it (`slot_names`), and
    the file's outputs are the program's channels 1-8: slot "n" is channel n, and nothing else is guessed."""
    group = next((g for g in (profile or {}).get("groups") or []
                  if isinstance(g, dict) and g.get("id") == "physical_outputs"), None)
    if group is None:
        return None, "no bundled profile of this model says how its outputs are named"
    if group.get("row_id_style") == "letter":
        return None, "the profile letters the outputs and the file numbers them: no rule says which is which"
    if group.get("max_count") != len(outputs):
        return None, "the profile counts %s outputs and the file %d" % (group.get("max_count"), len(outputs))
    return {str(o["channel"]): o for o in outputs}, None


def _pr_at(offset):
    return "offset %d" % offset


def _pr_number(parameter, code, want, have, tolerance, path):
    """A number of the version against the file's, within `tolerance`."""
    try:
        diff = abs(float(want) - float(have))
    except (TypeError, ValueError):
        return _said(parameter, code, want, have, "unknown", "not a number on both sides", category="audio", path=path)
    result = "match" if diff <= tolerance + 1e-9 else "differs"
    return _said(parameter, code, want, have, result, None, category="audio", path=path)


def _pr_equal(parameter, code, want, have, path):
    return _said(parameter, code, want, have, "match" if want == have else "differs", None, category="audio", path=path)


def _pr_leg_text(leg):
    if leg["state"] == "off":
        return "OFF (stored: %s at %d Hz)" % (leg["family"], leg["frequency_hz"])
    if leg["state"] == "undecoded":
        return "%s, slope code %d (not decoded), at %d Hz" % (leg["family"], leg["slope_code"], leg["frequency_hz"])
    return "%s %d dB/oct at %d Hz" % (leg["family"], leg["slope_db_oct"], leg["frequency_hz"])


def _pr_band_text(band):
    text = "%s %d Hz" % (band["type"] or "code %d" % band["type_code"], band["frequency_hz"])
    return text + " %+g dB Q%g" % (band["gain_db"], round(band["q"], 2))


def _pr_leg_rows(code, leg, want, have):
    path = _pr_at(have["offset"])
    undecoded = None
    if have["state"] == "undecoded":
        undecoded = "the file holds a slope code %d this reader does not decode" % have["slope_code"]
    if want in (None, "OFF") and undecoded:
        return [_said(leg + ".slope", code, "OFF", _pr_leg_text(have), "unknown", undecoded, category="audio",
                      path=path)]
    if want in (None, "OFF"):
        return [_said(leg + ".slope", code, "OFF", _pr_leg_text(have), "match" if have["state"] == "off" else "differs",
                      None, category="audio", path=path)]
    if not isinstance(want, dict):
        return [_said(leg, code, want, _pr_leg_text(have), "unknown", "the version's leg is not a filter this "
                      "comparison reads", category="audio", path=path)]
    rows = []
    family = _PR_FAMILY.get(str(want.get("type", "")).upper())
    if family is None:
        rows.append(_said(leg + ".type", code, want.get("type"), have["family"], "unknown",
                          "the file has no code for the type %r" % want.get("type"), category="audio", path=path))
    else:
        rows.append(_said(leg + ".type", code, want.get("type"), have["family"],
                          "match" if family == have["family"] else "differs", None, category="audio", path=path))
    if want.get("f") is not None:
        rows.append(_pr_number(leg + ".f", code, want["f"], have["frequency_hz"], _TOL_HZ, path))
    if undecoded:
        rows.append(_said(leg + ".slope", code, want.get("slope"), _pr_leg_text(have), "unknown", undecoded,
                          category="audio", path=path))
    elif _configured_off(want):
        rows.append(_said(leg + ".slope", code, "OFF", _pr_leg_text(have), "match" if have["state"] == "off" else "differs",
                          None, category="audio", path=path))
    elif want.get("slope") is not None:
        rows.append(_pr_equal(leg + ".slope", code, want["slope"], have["slope_db_oct"], path))
    else:
        rows.append(_said(leg + ".slope", code, None, _pr_leg_text(have), "unknown", "the version records no slope",
                          category="audio", path=path))
    return rows


def _pr_eq_rows(code, row, output):
    bands = output["eq"]
    by_band = {b["band"]: b for b in bands}
    active = [b for b in bands if b["state"] != "neutral"]
    if row.get("eq") is None:
        if not active:
            return []
        return [_said("eq", code, None, [_pr_band_text(b) for b in active], "unknown",
                      "the version does not record this channel's EQ", category="audio", path=_pr_at(bands[0]["offset"]))]
    out, claimed, pairs = [], set(), []
    for band in row["eq"]:
        if band.get("i") is None:
            continue
        found = by_band.get(band["i"])
        if found is None:
            out.append(_said("eq[%s]" % band["i"], code, band, None, "unknown",
                             "the file holds no EQ band in slot %s" % band["i"], category="audio"))
            continue
        claimed.add(band["i"])
        pairs.append((band, found))
    for band in row["eq"]:
        if band.get("i") is not None:
            continue
        pick = next((b for b in bands if b["band"] not in claimed and b["state"] == "configured"
                     and b["type"] == band.get("type") and abs(b["frequency_hz"] - float(band["f"])) <= _TOL_HZ), None)
        if pick is None:
            out.append(_said("eq %s %g Hz" % (band.get("type"), band["f"]), code, band, None, "differs",
                             "the file holds no %s band at %g Hz" % (band.get("type"), band["f"]), category="audio"))
            continue
        claimed.add(pick["band"])
        pairs.append((band, pick))
    for band, found in sorted(pairs, key=lambda p: p[1]["band"]):
        name, path = "eq[%d]" % found["band"], _pr_at(found["offset"])
        btype = band.get("type")
        if btype in _PR_WITH_GAIN:
            out.append(_pr_equal(name + ".type", code, btype, found["type"] or "code %d" % found["type_code"], path))
        else:
            out.append(_said(name + ".type", code, btype, found["type"] or "code %d" % found["type_code"], "unknown",
                             "the file's code for the type %r is not known" % btype, category="audio", path=path))
        if found["type"] is None:
            # A type the reader does not decode: the record's frequency, gain and Q mean nothing known -- never a match.
            why = ("the file's band is of type code %d, which this reader does not decode: its values are not read"
                   % found["type_code"])
            for field, have in (("f", found["frequency_hz"]), ("gain_db", found["gain_db"]), ("q", found["q"])):
                if field != "gain_db" or btype in _PR_WITH_GAIN:
                    out.append(_said("%s.%s" % (name, field), code, band.get(field), have, "unknown", why,
                                     category="audio", path=path))
            if band.get("bypass"):
                out.append(_said(name + ".bypass", code, True, None, "unknown", "the file decodes no bypass for a band",
                                 category="audio", path=path))
            continue
        out.append(_pr_number(name + ".f", code, band.get("f"), found["frequency_hz"], _TOL_HZ, path))
        if btype in _PR_WITH_GAIN:
            if band.get("gain_db") is not None:
                out.append(_pr_number(name + ".gain_db", code, band["gain_db"], found["gain_db"], _TOL_DB, path))
            else:
                out.append(_said(name + ".gain_db", code, None, found["gain_db"], "unknown",
                                 "the version records no gain for this band", category="audio", path=path))
        if band.get("q") is not None:
            out.append(_pr_number(name + ".q", code, band["q"], found["q"], _TOL_Q, path))
        else:
            out.append(_said(name + ".q", code, None, found["q"], "unknown", "the version records no Q for this band",
                             category="audio", path=path))
        if band.get("bypass"):
            out.append(_said(name + ".bypass", code, True, None, "unknown", "the file decodes no bypass for a band",
                             category="audio", path=path))
    for found in active:
        if found["band"] in claimed:
            continue
        path = _pr_at(found["offset"])
        if found["state"] != "configured":
            out.append(_said("eq[%d]" % found["band"], code, None, _pr_band_text(found), "unknown",
                             "the file holds a band of type code %d this reader does not decode" % found["type_code"],
                             category="audio", path=path))
        else:
            out.append(_said("eq[%d]" % found["band"], code, None, _pr_band_text(found), "differs",
                             "the version holds no such band", category="audio", path=path))
    return out


def _pr_channel_rows(code, row, o, reading_rate=None):
    """The rows of one channel row of the version against the reader's output `o`; `reading_rate` the reader's `rate`
    (a delay is read at it)."""
    out = []
    not_recorded = "the version does not record it"
    for field in sorted(row):
        if field in BOOKKEEPING or field in ("gain_db", "ta_ms", "polarity", "phase_deg", "mute", "off", "eq",
                                             "eq_bypass", "hp", "lp"):
            continue
        out.append(_said(field, code, row[field], None, "unknown", "a field this comparison does not know",
                         category="audio"))
    slot = o["slot"]
    # a muted output keeps its set level at the second offset
    level_at = _pr_at((1292 if o["muted"] else 1280) + slot - 1)
    level_byte = o["level_while_muted_byte"] if o["muted"] else o["level_byte"]
    if row.get("gain_db") is not None and o["level_db"] is None:
        out.append(_said("gain_db", code, row["gain_db"], None, "unknown", "the file's level byte %d is not decoded"
                         % level_byte, category="audio", path=level_at))
    elif row.get("gain_db") is not None:
        out.append(_pr_number("gain_db", code, row["gain_db"], o["level_db"], _TOL_DB, level_at))
    else:
        out.append(_said("gain_db", code, None, o["level_db"], "unknown", not_recorded, category="audio", path=level_at))
    delay_at = _pr_at(1408 + 2 * (slot - 1))
    rate = reading_rate or {}
    if rate.get("assumed"):
        # The steps are read as ms at the rate: one not stored is no rate to compare a delay at.
        said = ("the rate is not stored in the file; %d kHz assumed" % (_mosconi().DEVICE["rate_hz"] // 1000)
                if rate.get("byte") is None else "the file's rate byte %s is not one this reader knows; %d kHz assumed"
                % (rate["byte"], _mosconi().DEVICE["rate_hz"] // 1000))
        out.append(_said("ta_ms", code, row.get("ta_ms"), round(o["delay_ms"], 4), "unknown", said, category="audio",
                         path=delay_at))
    elif row.get("ta_ms") is not None:
        out.append(_pr_number("ta_ms", code, row["ta_ms"], round(o["delay_ms"], 4), _PR_TOL_MS, delay_at))
    else:
        out.append(_said("ta_ms", code, None, round(o["delay_ms"], 4), "unknown", not_recorded, category="audio",
                         path=delay_at))
    polarity_at = _pr_at(1392 if slot <= 8 else 1393)
    if row.get("polarity") in _POLARITY:
        out.append(_pr_equal("polarity", code, row["polarity"], o["polarity"], polarity_at))
    else:
        out.append(_said("polarity", code, row.get("polarity"), o["polarity"], "unknown", not_recorded,
                         category="audio", path=polarity_at))
    if row.get("phase_deg") is not None:
        out.append(_said("phase_deg", code, row["phase_deg"], None, "unknown",
                         "this model has no phase control, only a polarity switch", category="audio"))
    mute_at = _pr_at(1280 + slot - 1)
    if row.get("mute") is not None:
        out.append(_pr_equal("mute", code, bool(row["mute"]), o["muted"], mute_at))
    else:
        out.append(_said("mute", code, None, o["muted"], "unknown", not_recorded, category="audio", path=mute_at))
    for field in ("off", "eq_bypass"):
        if row.get(field) is not None:
            out.append(_said(field, code, row[field], None, "unknown", "the file decodes no such switch",
                             category="audio"))
    for leg in ("hp", "lp"):
        if leg in row:
            out += _pr_leg_rows(code, leg, row[leg], o["high_pass" if leg == "hp" else "low_pass"])
    out += _pr_eq_rows(code, row, o)
    return out


#: `project.json` `dsp.settings.corner_set` (`project.DSP_SETTINGS`) in the `.PR15` reader's words
#: (`mosconi_pr.CORNER_SETS`); the selftest holds the two tables to these keys and names.
PR_CORNER_SETS = {"default": "default", "minus_3db": "normalized to -3 dB", "minus_6db": "normalized to -6 dB"}


def _pr_preset_rows(snap, reading, dsp_settings=None):
    """The version's `preset_settings` against the file: the input gain (one per input in the file) and the corner set
    (the file's only one; the journal records none, `project.json` `dsp.settings.corner_set` does, S-136.2). Any other
    stated setting: the file decodes no such setting."""
    st = _state()
    settings = snap.get(st.PRESET_SETTINGS)
    settings = settings if isinstance(settings, dict) else {}
    stated = any(k not in ("status", "source_file") for k in settings)
    out = []
    gains = [g["attenuation_db"] for g in reading["input_gain"]]
    for path in st._PRESET_FIELDS:
        value = st._preset_leaf(settings, path)
        category = "audio" if path.startswith("sources.") or path == "input_gain_db" else "system"
        if path == "input_gain_db":
            reason = ("the file holds an attenuation per input (inputs 1-%d); one value of the version names none of "
                      "them" % len(gains)) if value is not None else (
                "the version does not state it" if stated else "the version records no preset settings")
            out.append(_said(path, "preset", value, {"attenuation_db": gains}, "unknown", reason, category=category,
                             path=_pr_at(1344)))
        elif value is not None:
            out.append(_said(path, "preset", value, None, "unknown", "the file decodes no such setting",
                             category=category))
    out.append(_pr_corner_set_row(reading["corner_set"], dsp_settings))
    return out


def _pr_corner_set_row(corner, dsp_settings):
    """`crossover.corner_set`: the file's code against `project.json`'s recorded answer -- `match` or `differs` in the
    reader's words; `unknown` when the project has not recorded it, records a value that is no corner set, or the file
    holds a code outside the reader's table."""
    raw = (dsp_settings or {}).get("corner_set")
    recorded = raw.get("value") if isinstance(raw, dict) else raw
    have = corner.get("name")
    if recorded is None:
        return _said("crossover.corner_set", "preset", None, have, "unknown",
                     "the journal records no corner set: the program's corner correction is asked, not recorded",
                     category="system", path=_pr_at(2307))
    want = PR_CORNER_SETS.get(recorded)
    if want is None:
        return _said("crossover.corner_set", "preset", recorded, have, "unknown",
                     "project.json dsp.settings.corner_set is %r, no corner set (%s)"
                     % (recorded, ", ".join(PR_CORNER_SETS)), category="system", path=_pr_at(2307))
    if have is None:
        return _said("crossover.corner_set", "preset", want, "code %s" % corner.get("code"), "unknown",
                     "the file's corner set code %s is outside the reader's table" % corner.get("code"),
                     category="system", path=_pr_at(2307))
    return _said("crossover.corner_set", "preset", want, have, "match" if want == have else "differs", None,
                 category="system", path=_pr_at(2307))


def _pr_plan(reading, snap, identity, dsp_settings=None):
    out, reached = [], set()
    outputs = reading["outputs"]
    skipped = []
    profile = _pr_profile(skipped)
    by_slot, why_not = _pr_numbering(profile, outputs)
    if profile is None and skipped:
        why_not = "no bundled profile of this model could be read: %s -- no rule says how its outputs are named" % (
            "; ".join("%s cannot be read (%s)" % (os.path.basename(path), why) for path, why in skipped))
    tiers = [t for t in _state().tier_names(snap) if isinstance(snap.get(t), dict)]
    planned = []
    for tier in tiers:
        for key, row in snap[tier].items():
            entry = identity.get(key) or {}
            slot = str(entry.get("slot") or "").strip().upper()
            planned.append((tiers.index(tier), slot or "~", key, tier, row, entry, slot))
    for _order, _slot, key, tier, row, entry, slot in sorted(planned, key=lambda p: (p[0], p[1], p[2])):
        code = entry.get("code") or key
        why, o = None, None
        if tier != "channels":
            why = "the file's outputs are not mapped for the tier %r" % tier
        elif not slot:
            why = "project.json gives this channel no slot"
        elif by_slot is None:
            why = why_not
        else:
            o = by_slot.get(slot)
            if o is None:
                why = "this model has no output %s (outputs 1-%d)" % (slot, len(outputs))
        if o is None:
            for field in sorted(f for f in row if f not in BOOKKEEPING):
                out.append(_said(field, code, row[field], None, "unknown", why, category="audio"))
            continue
        reached.add(o["channel"])
        out += _pr_channel_rows(code, row, o, reading.get("rate"))
    for o in outputs:
        if o["channel"] in reached:
            continue
        out.append(_said("channel", "Output %d" % o["channel"], None, "muted" if o["muted"] else "on", "unknown",
                         "no row of this version is on this output", category="audio",
                         path=_pr_at(1280 + o["slot"] - 1)))
    out += _pr_preset_rows(snap, reading, dsp_settings)
    rank = {c: i for i, c in enumerate(CATEGORY_ORDER)}
    out.sort(key=lambda r: rank.get(r["category"], len(rank)))
    return out


def _pr_device(reading):
    d, fw, rate = reading["device"], reading["firmware"], reading["rate"]
    note = ("read on one sample preset only; outputs 1-8 are the file's memory slots %s; firmware %s; rate byte %s"
            % (", ".join(str(s) for s in _mosconi().CHANNEL_SLOTS), fw["version"] if fw else "not stored",
               rate["byte"]))
    return {"dev": d["dev"], "name": "%s %s" % (d["vendor"], d["name"]), "verified": False,
            "clock_hz": rate["hz"], "clock_assumed_hz": None if rate["hz"] else d["rate_hz"], "layout": "pico-6-8-2",
            "note": note}


def _compare_pr(journal, file_path):
    """`compare_journal` for a `.PR<n>`: exit 0 compared, 2 unreadable (`io`, `model`, `format`, `truncated`,
    `interpret`), 3 changed while read. The reader hashes the file before it reads it and after."""
    mp = _mosconi()
    snap, identity = journal[:2]
    dsp_settings = journal[2] if len(journal) > 2 and isinstance(journal[2], dict) else {}
    name = os.path.basename(file_path)
    try:
        reading = mp.read_pr(file_path)
    except mp.PrError as exc:
        code = EXIT_CHANGED if exc.kind == "changed" else EXIT_UNREADABLE
        return code, refusal(mp.WARNING, name, exc.kind, str(exc))
    try:
        rows = _pr_plan(reading, snap, identity, dsp_settings)
        device = _pr_device(reading)
    except Exception as exc:  # noqa: BLE001 -- past the read, a failure is the file's, its type named
        return EXIT_UNREADABLE, refusal(mp.WARNING, name, "interpret", "the file was read and could not be compared "
                                        "(%s: %s)" % (type(exc).__name__, exc), md5=reading["file"]["md5"])
    return EXIT_COMPARED, {
        "contract": CONTRACT, "warning": mp.WARNING, "warning_uk": mp.WARNING_UK, "device": device, "checked_model": False,
        "file": _file_block(name, reading["file"]["md5"]), "counts": _counts(rows), "rows": rows}


def _cell(value):
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "on" if value else "off"
    if isinstance(value, float):
        return "%g" % value
    if isinstance(value, dict):
        return " ".join("%s=%s" % (k, _cell(v)) for k, v in sorted(value.items()))
    if isinstance(value, list):
        return "; ".join(_cell(v) for v in value)
    return str(value)


def render(result, version):
    """The table a person reads: the warning, the file and the model, the counts, then one row a line."""
    f, d = result["file"], result["device"]
    lines = [result["warning"], "",
             "version %s against %s (md5 %s, saved %s%s)" % (version, f["name"], f["md5"], f["saved"],
                                                              ", PC-Tool %s" % f["pctool"] if f["pctool"] else ""),
             "model: %s (Dev %s) -- %s" % (d.get("name") or "unknown", d.get("dev"),
                                          "checked" if result["checked_model"] else "NOT CHECKED: read at your own risk"),
             "rows: " + ", ".join("%d %s" % (n, r) for r, n in result["counts"]["result"].items()), ""]
    head = ("result", "category", "channel", "parameter", "journal", "file")
    table = [head] + [(r["result"], r["category"], r["channel"], r["parameter"], _cell(r["journal"]), _cell(r["file"]))
                      for r in result["rows"]]
    widths = [min(max(len(str(row[i])) for row in table), 40) for i in range(len(head))]
    for row in table:
        lines.append("  ".join(str(c)[:40].ljust(w) for c, w in zip(row, widths)).rstrip())
    reasons = [r for r in result["rows"] if r["result"] == "unknown"]
    if reasons:
        lines += ["", "unknown, and why:"]
        lines += ["  %s %s: %s" % (r["channel"], r["parameter"], r["reason"]) for r in reasons]
    return "\n".join(lines)
