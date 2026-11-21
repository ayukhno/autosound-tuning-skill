"""What a decoded `.pct6` says, in Hz, dB, ms, degrees and named states. Read only.

`interpret(document)` keeps every raw value and adds a meaning next to it. Conversions are written out here as
code; the mapping rules (`rules.json`) are provenance and confidence, never evaluated.

Four things are kept apart and must stay apart for a consumer:

* `missing` -- the file holds no such value; never read as zero or OFF;
* `not_saved` -- a channel points at a filter (HPi/LPi) that the file does not hold;
* `off` / `bypassed` / `neutral` -- a filter that is stored but does nothing, for three different reasons;
* `unknown` -- a value whose meaning is not established; never counted as a match.
"""

import json
import math
import os
import re
from collections import Counter
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from . import models
from .container import Document

_RULES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rules.json")

EQ_TYPES = {1: "Fine EQ", 3: "LSH", 4: "HSH", 17: "PK", 19: "APF1", 20: "APF2"}
EQ_NEUTRAL_AT_ZERO = {1, 3, 4, 17}
APF_TYPES = {19, 20}
#: Crossover type codes: (family, direction, confidence). BW and LR are confirmed by experiment; the other
#: families come from the documented type list without a calibration file of their own.
CROSSOVER_TYPES = {
    9: ("Butterworth", "LP", "confirmed"), 10: ("Butterworth", "HP", "confirmed"),
    15: ("Linkwitz", "LP", "confirmed"), 16: ("Linkwitz", "HP", "confirmed"),
    11: ("Bessel", "LP", "documented"), 12: ("Bessel", "HP", "documented"),
    13: ("Chebyshev", "LP", "documented"), 14: ("Chebyshev", "HP", "documented"),
    7: ("Self-define", "LP", "documented"), 8: ("Self-define", "HP", "documented"),
}
ROUTES = {1: ("Main", "Virtual"), 5: ("HEC/AUX", "Virtual"), 9: ("Digital", "Virtual"), 31: ("Virtual", "Output")}
SAVE_METADATA = frozenset({"/ATF/@D", "/ATF/@FN", "/ATF/ATFCOND[1]/@D"})
CHS_SH = {"0": "Pass Through", "1": "Line In", "2": "Line Out", "3": "Digital In", "4": "USB"}
CHS_LONG = {"0": "Front", "1": "Surround", "2": "Rear"}
CHS_LATERAL = {"0": "Left", "1": "Center", "2": "Right"}
CHS_PB = {"0": "Subwoofer", "1": "Low", "2": "Mid", "3": "High"}


def load_rules() -> dict:
    with open(_RULES_PATH, encoding="utf-8") as handle:
        return json.load(handle)


# ---------------------------------------------------------------- conversions

def amplitude_db(raw: Optional[str]) -> dict:
    """`Vol/@L` and `R/@OFFS`: linear amplitude -> dB. Zero amplitude and a missing value are states, not 0 dB."""
    if raw is None:
        return {"raw": None, "value": None, "unit": "dB", "state": "missing"}
    try:
        linear = float(raw)
    except ValueError:
        return {"raw": raw, "value": None, "unit": "dB", "state": "unknown"}
    if linear <= 0:
        return {"raw": raw, "value": None, "unit": "dB", "state": "zero_amplitude"}
    return {"raw": raw, "value": round(20 * math.log10(linear), 6), "unit": "dB", "state": "present"}


def delay(raw: Optional[str], clock_hz: int) -> dict:
    """`T/@T` samples -> ms, full and as PC-Tool shows it (half up to 0.01 ms: 444/96 = 4.625 -> 4.63)."""
    if raw is None:
        return {"raw": None, "ms": None, "display_ms": None, "state": "missing"}
    try:
        samples = Decimal(raw)
    except ArithmeticError:
        return {"raw": raw, "ms": None, "display_ms": None, "state": "unknown"}
    full = samples * 1000 / Decimal(clock_hz)
    shown = full.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return {"raw": raw, "samples": int(samples), "ms": float(full), "display_ms": float(shown), "state": "present"}


def _float(raw: Optional[str]) -> Optional[float]:
    try:
        return float(raw) if raw is not None else None
    except ValueError:
        return None


# ---------------------------------------------------------------- raw inventory

def parameters(root) -> list:
    """Every saved value with a stable path: OC/IC by their ON/IN index, other repeats by 1-based position."""
    rows = []

    def walk(element, path):
        for key, value in element.attrib.items():
            rows.append({"path": path + "/@" + key, "tag": element.tag, "key": key, "raw": value})
        if element.text and element.text.strip():
            rows.append({"path": path + "/#text", "tag": element.tag, "key": "#text", "raw": element.text})
        counts = Counter()
        for child in element:
            counts[child.tag] += 1
            ident = "ON" if child.tag == "OC" else "IN" if child.tag == "IC" else None
            if ident and child.get(ident) is not None:
                suffix = "[@%s=%r]" % (ident, child.get(ident))
            else:
                suffix = "[%d]" % counts[child.tag]
            walk(child, path + "/" + child.tag + suffix)

    walk(root, "/" + root.tag)
    return rows


def flatten(root) -> dict:
    """`{path: raw}` over `parameters`, plus one `#element` entry per element so a node that appears or goes is seen."""
    out = {}

    def walk(element, path):
        out[path + "/#element"] = element.tag
        for key, value in element.attrib.items():
            out[path + "/@" + key] = value
        if element.text and element.text.strip():
            out[path + "/#text"] = element.text.strip()
        counts = Counter()
        for child in element:
            counts[child.tag] += 1
            ident = "ON" if child.tag == "OC" else "IN" if child.tag == "IC" else None
            suffix = "[@%s=%r]" % (ident, child.get(ident)) if ident and child.get(ident) is not None \
                else "[%d]" % counts[child.tag]
            walk(child, path + "/" + child.tag + suffix)

    walk(root, "/" + root.tag)
    return out


# ---------------------------------------------------------------- channels and filters

def channel_name(element) -> Optional[str]:
    """The channel's name from `CHS` (which wins over the legacy CN code)."""
    chs = element.find("CHS")
    if chs is None:
        return None
    a = chs.attrib
    if not a:
        return ""
    if "UNAME" in a:
        return a["UNAME"]
    parts = []
    for key, table in (("SH", CHS_SH), ("LONG", CHS_LONG), ("LATERAL", CHS_LATERAL), ("PB", CHS_PB)):
        if key in a:
            parts.append(table.get(a[key], "%s=%s" % (key, a[key])))
    if "IDX" in a:
        parts.append(a["IDX"])
    return " ".join(parts)


def _layout(kind: str, index: int, layout: Optional[str]) -> dict:
    """Where a channel sits on the model. Known only for the HELIX DSP ULTRA S layout."""
    if layout != "ultra-s" or kind != "output":
        return {"group": None, "label": None, "visible_in_pc_tool": None}
    if 14 <= index <= 25:
        return {"group": "physical", "label": "Output " + chr(65 + index - 14), "visible_in_pc_tool": True}
    if 0 <= index <= 11:
        visible = index in (0, 1, 2, 3, 4, 5, 10, 11)
        return {"group": "virtual" if visible else "internal", "label": "Virtual " + chr(65 + index),
                "visible_in_pc_tool": visible}
    return {"group": "internal", "label": None, "visible_in_pc_tool": False}


def _filter(index: int, raw: dict, role: str) -> dict:
    try:
        code = int(raw.get("T", ""))
    except ValueError:
        code = None
    gain = _float(raw.get("G"))
    bypass = raw.get("FilBy") == "1"
    out = {"index": index, "position": index + 1, "role": role, "raw": dict(raw), "type_code": code,
           "frequency_hz": _float(raw.get("F")), "bypass": bypass}
    if "FilBBR" in raw and raw.get("FilBBR") != raw.get("FilBy"):
        out["bypass_copy_differs"] = True          # FilBBR = FilBy is an assumption; report, never fix
    if role in ("high_pass", "low_pass"):
        family, direction, confidence = CROSSOVER_TYPES.get(code, (None, None, "unknown"))
        off = gain == 0
        out.update({"family": family, "direction": direction, "type_confidence": confidence,
                    "slope_db_oct": None if off or gain is None else -gain,
                    "state": "bypassed" if bypass else "off" if off else "configured" if family else "unknown"})
        return out
    name = EQ_TYPES.get(code)
    if bypass:
        state = "bypassed"
    elif code in APF_TYPES:
        state = "configured"                        # an all-pass at G=0 still turns phase: never neutral
    elif code in EQ_NEUTRAL_AT_ZERO:
        state = "neutral" if gain == 0 else "configured"
    else:
        state = "unknown"
    out.update({"type": name, "state": state,
                "gain_db": gain if code in EQ_NEUTRAL_AT_ZERO else None,
                "q": _float(raw.get("Q")) if code != 19 else None, "q_applies": code != 19})
    if code in APF_TYPES:
        out["invert"] = raw.get("I") == "1"
    elif raw.get("I") == "1":
        out["inert_invert_flag"] = True             # I=1 on a non-APF band is a leftover, not an inverted APF
    return out


def _crossover_ref(element, attribute: str, filters: list) -> Optional[dict]:
    if attribute not in element.attrib:
        return None
    try:
        index = int(element.get(attribute))
    except ValueError:
        return {"index": element.get(attribute), "state": "unknown"}
    if not 0 <= index < len(filters):
        return {"index": index, "state": "not_saved"}
    return {"index": index, "state": "saved"}


def _channel(element, kind: str, device: dict) -> dict:
    ident = "ON" if kind == "output" else "IN"
    try:
        index = int(element.get(ident))
    except (TypeError, ValueError):
        index = None
    clock = device["clock_hz"] or device["clock_assumed_hz"]
    raw_filters = [dict(f.attrib) for f in element.findall("Fil")]
    hp = _crossover_ref(element, "HPi", raw_filters)
    lp = _crossover_ref(element, "LPi", raw_filters)
    roles = {}
    if hp and hp["state"] == "saved":
        roles[hp["index"]] = "high_pass"
    if lp and lp["state"] == "saved":
        roles[lp["index"]] = "low_pass"
    filters = [_filter(i, f, roles.get(i, "eq")) for i, f in enumerate(raw_filters)]
    level = element.find("Vol")
    timing = []
    for t in element.findall("T"):
        a = t.attrib
        entry = {"raw": dict(a), "delay": delay(a.get("T"), clock)}
        if device["clock_hz"] is None:
            entry["delay"]["clock_assumed"] = True
        if "P" in a:
            entry["phase_degrees"] = _float(a.get("P"))
        entry["phase_mode"] = {"1": "polarity_only", "2": "phase_adjustable"}.get(a.get("PM"), None if "PM" not in a else "unknown")
        if a.get("PM") == "2":
            entry["phase_step_degrees"] = 5.625
        timing.append(entry)
    out = {"kind": kind, "index": index, **_layout(kind, index if index is not None else -1, device["layout"]),
           "name": channel_name(element), "raw": dict(element.attrib),
           "level": amplitude_db(level.get("L") if level is not None else None),
           "polarity": {"0": "NORM", "1": "INV"}.get(element.get("CINV")),
           "timing": timing, "high_pass": hp, "low_pass": lp, "filters": filters}
    if kind == "output":
        out["mute_on"] = {"0": True, "1": False}.get(element.get("MT"))
    else:
        out["mute_raw"] = element.get("MT")            # input MT is not calibrated by an experiment
    for name, ref in (("high_pass", hp), ("low_pass", lp)):
        if ref and ref["state"] == "saved":
            out[name] = {**ref, **{k: v for k, v in filters[ref["index"]].items() if k != "index"}}
    return out


# ---------------------------------------------------------------- routing

def _routing(root, layout: Optional[str]) -> list:
    out = []
    for position, r in enumerate(root.findall("Route/R"), 1):
        a = r.attrib
        diagnostics = []
        try:
            ins, outs, aom = int(a.get("INS")), int(a.get("OUTS")), int(a.get("AOM"))
        except (TypeError, ValueError):
            out.append({"position": position, "raw": dict(a), "state": "unknown",
                        "diagnostics": ["INS/OUTS/AOM missing or not a number"]})
            continue
        coeff = {}
        for key, value in a.items():
            m = re.fullmatch(r"G(\d+)", key)
            if m:
                coeff[int(m.group(1))] = value
        expected = set(range(ins * outs))
        missing = sorted(expected - set(coeff))
        extra = sorted(set(coeff) - expected)
        if missing:
            diagnostics.append("missing coefficients: %s" % ", ".join("G%d" % n for n in missing))
        if extra:
            diagnostics.append("coefficients outside INS*OUTS: %s" % ", ".join("G%d" % n for n in extra))
        source, target = ROUTES.get(aom, (None, None))
        links = []
        for n in sorted(coeff):
            if n not in expected:
                continue
            value = _float(coeff[n])
            if not value:
                continue
            i, o = n % ins, n // ins
            links.append({"key": "G%d" % n, "input": i, "output": o, "linear": coeff[n],
                          "db": amplitude_db(coeff[n])["value"],
                          "input_label": _route_label(source, i, layout),
                          "output_label": _route_label(target, o, layout)})
        out.append({"position": position, "aom": aom, "name": "%s -> %s" % (source, target) if source else None,
                    "state": "known" if source else "unknown", "inputs": ins, "outputs": outs,
                    "source_level": amplitude_db(a.get("OFFS")), "links": links, "diagnostics": diagnostics})
    return out


def _route_label(kind: Optional[str], index: int, layout: Optional[str]) -> Optional[str]:
    if layout != "ultra-s" or kind is None:
        return None
    if kind in ("Virtual", "Output"):
        return "%s %s" % (kind, chr(65 + index)) if index < 12 else "%s index %d" % (kind, index)
    return "%s %d" % (kind, index + 1)


# ---------------------------------------------------------------- system, FX, CONDUCTOR

def _first(root, path: str) -> dict:
    element = root.find(path)
    return dict(element.attrib) if element is not None else {}


def _flag(raw: Optional[str], on: str) -> Optional[bool]:
    if raw is None:
        return None
    return raw == on if raw in ("0", "1") else None


def _system(root) -> dict:
    stx, abp, mcv = _first(root, "STX"), _first(root, "ABP"), _first(root, "MCV2")
    out = {"effects": {
        "realcenter_on": _flag(stx.get("CMOD"), "1"),
        "dynamic_bass_enhancement_on": _flag(abp.get("SWBP"), "0"),     # 1 = disabled
        "subxpander_on": _flag(abp.get("SWS"), "0"),                    # 1 = disabled
        "remote_tone_control_on": _flag(mcv.get("RTC_EN"), "1"),
    }, "rtc_bands": [], "assumptions": {}}
    for band, label in (("0", "LF"), ("1", "HF")):
        values = {}
        for kind in ("GSTART", "GSTOP", "VSTART", "VSTOP", "FSTART", "FSTOP"):
            key = "RTC_%s%s" % (kind, band)
            if key in mcv:
                number = _float(mcv[key])
                hz = kind.startswith("F")
                values[key] = {"raw": mcv[key], "value": number if hz or number is None else number / 10,
                               "unit": "Hz" if hz else "dB"}
        if values:
            out["rtc_bands"].append({"band": label, "configured": values})     # stored even when RTC is off
    if "IMASK" in mcv:
        try:
            mask = int(mcv["IMASK"])
            out["input_mask"] = {"raw": mcv["IMASK"], "bt_auto_switch_on": bool(mask & 0x04),
                                 "unknown_bits": mask & ~0x04}
        except ValueError:
            out["input_mask"] = {"raw": mcv["IMASK"], "state": "unknown"}
    dcm = root.find("DCM")
    if dcm is not None:
        for sw in dcm.iter("SW"):
            if sw.get("i") == "0":
                out["bt_aux_selector"] = {"raw": sw.get("A"), "value": {"1": "BT", "0": "AUX"}.get(sw.get("A"))}
                break
    for key in ("BF1", "BF2"):
        if key in abp and _float(abp[key]) is not None:
            out["assumptions"][key] = {"raw": abp[key], "frequency_hz": _float(abp[key]) * 96000 / (2 * math.pi),
                                       "confidence": "assumption"}
    out["conductor"] = _conductor(root)
    return out


def _conductor(root) -> Optional[dict]:
    cond = root.find("ATFCOND")
    if cond is None:
        return None
    glb = _first(cond, "GLB")
    mb, mto = _float(glb.get("MB")), _float(glb.get("MTO"))
    out = {"protocol_version": cond.get("CV"),
           "tone_menu_on": _flag(glb.get("TCEN"), "1"),
           "led_brightness_percent": None if mb is None else mb * 100 / 255,
           "led_dimming_percent": _float(glb.get("DB")),
           "menu_return_s": None if mto is None else mto / 1000,
           "controls": [], "tone_frequencies": []}
    for vol in cond.findall("VOL"):
        a = vol.attrib
        rng, stp = _float(a.get("RNG")), _float(a.get("STP"))
        number = int(a["VN"]) + 1 if a.get("VN", "").isdigit() else None
        out["controls"].append({
            "number": number, "raw": dict(a),
            "assignment": {"0": "Master", "1": "Sub", "5": "Rear Att.", "255": "none"}.get(a.get("SEL"), "unknown"),
            "rgb": [int(a[k]) for k in ("R", "G", "B")] if all(a.get(k, "").isdigit() for k in ("R", "G", "B")) else None,
            "range_db": None if rng is None else rng / 10,
            "step_db": None if rng is None or not stp else rng / stp / 10,
            "start_raw": a.get("BV"), "start_state": "unknown"})
    for tc in cond.findall("TC"):
        a = tc.attrib
        out["tone_frequencies"].append({"band": {"0": "LF", "1": "HF"}.get(a.get("TCN")),
                                        "frequency_hz": _float(a.get("TCF")), "raw": dict(a)})
    return out


# ---------------------------------------------------------------- the whole result

def _saved(raw: Optional[str]) -> Optional[str]:
    """`ATF/@D` is ddMMyyyyhhmm with no time zone; returned as `dd.MM.yyyy hh:mm`."""
    if not raw or not re.fullmatch(r"\d{12}", raw):
        return None
    return "%s.%s.%s %s:%s" % (raw[0:2], raw[2:4], raw[4:8], raw[8:10], raw[10:12])


def interpret(doc: Document) -> dict:
    """Everything the file says, raw and interpreted, as one JSON-ready dict. Every model is read; see `device`."""
    root = doc.root
    device = models.describe(doc.dev)
    device.update({"pc_tool_version": doc.pc_tool_version, "saved": _saved(root.get("D")),
                   "saved_raw": root.get("D"), "file_name_inside": root.get("FN")})
    rules = load_rules()
    rows = parameters(root)
    notes = []
    if not device["verified"]:
        notes.append("Dev=%s is not a checked model: delays use an assumed %d Hz clock, channels carry no "
                     "A-L labels, and every value needs checking against PC-Tool." % (doc.dev, device["clock_assumed_hz"]))
    elif device["clock_hz"] is None:
        notes.append("delays use an assumed 96000 Hz clock")
    channels = [_channel(e, "output", device) for e in root.findall("OC")] + \
               [_channel(e, "input", device) for e in root.findall("IC")]
    return {
        "format": "helix-pct6.inventory.v1",
        "warning": models.WARNING,
        "notes": notes + list(doc.diagnostics),
        "file": {"source_name": os.path.basename(doc.source) if doc.source else None,
                 "input_bytes": doc.input_bytes, "input_md5": doc.input_md5, "input_sha256": doc.input_sha256,
                 "xml_bytes": len(doc.xml), "xml_sha256": doc.xml_sha256,
                 "container_mode": doc.mode, "container_mode_confirmed": doc.mode_confirmed},
        "device": device,
        "counts": {"attributes": sum(len(e.attrib) for e in root.iter()), "records": len(rows),
                   "elements": dict(Counter(e.tag for e in root.iter()))},
        "channels": channels,
        "routing": _routing(root, device["layout"]),
        "system": _system(root),
        "unknown_fields": rules["unknown"],
        "rules": {"format": rules["format"], "scope": rules["scope"], "provenance_sha256": rules["provenance_sha256"],
                  "confidence": dict(Counter(r["confidence"] for r in rules["rules"]))},
        "parameters": rows,
    }
