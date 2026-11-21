"""A version's values from a saved `.pct6` (#218 T3): what `apply.py attest --from-file` records and what
`apply.py propose --from-file` proposes. The contract is `rew_tool/CONTRACT.md` item 14.

Read only, like compare-file: the file is opened for reading and hashed before it is read and after; this module
writes nothing. What it hands back -- a `source_file` record, a delta, the names of what it did not take -- is banked by
`apply.py` through `attest` and `propose`, the ledger's only doors.

**The codes between the journal and the file live here** (`POLARITY`, `EQ_CODES`, `XO_FAMILY`, ...): the one table both
directions are to read. compare-file (`compare_file.py`) still holds its own copies, written before this module;
`apply.py`'s selftest holds the two equal until compare-file reads them from here. The slot rule -- which output a row
reaches -- is compare-file's `_virtual_by_letter`, taken as it is (`virtual_by_letter`), and its reasons are its words.

**What the file gives a row** (`build`), in the journal's units: the level (dB, to 0.01), the delay as PC-Tool shows it
(ms, to 0.01), the polarity, the mute, the phase where the channel has the phase control or the version states one,
both crossover legs (family, Hz, dB/oct; an OFF leg is null), and every EQ band that does something or is bypassed
(type, Hz, gain, Q, the slot as `i`, the bypass). The preset's settings: the source levels, RealCenter, Dynamic Bass,
SubXpander, RTC and its curve, the BT selector and its auto-switch. Everything else stays as the version had it and is
named with its reason: a field the file does not decode, a leg it holds bypassed, a band of a type the journal has no
name for, a row no output is mapped to, an output no row is on. Format documented by amATFpct6.
"""

import datetime
import hashlib
import importlib.util
import math
import os
import re
import sys

#: The journal's polarity -> the file's `CINV`.
POLARITY = {"NORM": "0", "INV": "1"}
POLARITY_BACK = {v: k for k, v in POLARITY.items()}
#: The journal's `mute` -> the file's `MT` on an output (`MT` 1 is sounding).
MUTE = {True: "0", False: "1"}
MUTE_BACK = {v: k for k, v in MUTE.items()}
#: The journal's EQ band types -> the file's codes (`helix_pct6.inventory.EQ_TYPES`).
EQ_CODES = {"PK": 17, "LSH": 3, "HSH": 4, "APF1": 19, "APF2": 20}
EQ_TYPES_BACK = {code: name for name, code in EQ_CODES.items()}
EQ_WITH_GAIN = ("PK", "LSH", "HSH")
#: The journal's crossover families -> the reader's family names (`helix_pct6.inventory.CROSSOVER_TYPES`), and back.
XO_FAMILY = {"LR": "Linkwitz", "BW": "Butterworth", "BE": "Bessel", "CH": "Chebyshev", "CHEBYSHEV": "Chebyshev",
             "SD": "Self-define", "SELF_DEFINED": "Self-define"}
XO_SHORT = {"Linkwitz": "LR", "Butterworth": "BW", "Bessel": "BE", "Chebyshev": "CH", "Self-define": "SD"}
#: `preset_settings.sources.<name>` -> the `AOM` of its route, whose `OFFS` is its level.
SOURCES = (("main", "1"), ("hec", "5"), ("digital", "9"))
#: A preset switch: (its path in `preset_settings`, the file's value, the raw value for ON, for OFF).
SWITCHES = (("fx.realcenter", "/ATF/STX[1]/@CMOD", "1", "0"),
            ("fx.dynamic_bass", "/ATF/ABP[1]/@SWBP", "0", "1"),
            ("fx.subxpander", "/ATF/ABP[1]/@SWS", "0", "1"),
            ("rtc.on", "/ATF/MCV2[1]/@RTC_EN", "1", "0"))
BT_SOURCE = {"BT": "1", "AUX": "0"}
BT_SOURCE_BACK = {v: k for k, v in BT_SOURCE.items()}
BT_AUTO_SWITCH_BIT = 0x04
IMASK = "/ATF/MCV2[1]/@IMASK"
_RTC_KEY = re.compile(r"^([GVF])(START|STOP)([01])$")
#: The journal's row fields that are its own bookkeeping: kept as they are, said as such.
BOOKKEEPING = ("tag", "eq_ptr")
#: Why a field of the version is not taken from the file, where the field says it.
_WHY_KEPT = {
    "off": "the file decodes no such switch",
    "eq_bypass": "the meaning of this field in the file is not established",
    "tag": "the journal's bookkeeping, not in the file",
    "eq_ptr": "the journal's bookkeeping, not in the file -- it may point at bands the file has replaced",
}
_NOT_DECODED = "the file does not give it"


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


def _compare_file():
    """`state/compare_file.py`: the comparison and the slot rule, one module object."""
    return _siblings().load("state/compare_file.py")


def virtual_by_letter(outputs):
    """compare-file's slot rule for the virtual tier, as it is: one place for it."""
    return _compare_file()._virtual_by_letter(outputs)


def _sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


# ---------------------------------------------------------------------------------------------------- the file

def read_file(file_path):
    """`(exit code, read)`: the file read and interpreted, or compare-file's refusal (CONTRACT.md item 13) -- 2 the file
    cannot be read or interpreted (`error.kind`), 3 it changed while it was read. `read` is `{name, path, doc, inv,
    device, warning}` on 0. Hashed before the read, by the reader, and after, as compare-file hashes it."""
    cf = _compare_file()
    hx = cf._helix()
    name = os.path.basename(file_path)
    try:
        before = _sha256(file_path)
    except OSError as exc:
        return cf.EXIT_UNREADABLE, cf.refusal(hx.WARNING, name, "io", "the file cannot be opened: %s" % exc)

    def changed():
        try:
            return _sha256(file_path) != before
        except OSError:
            return True

    said = "the file changed while it was read: nothing was taken from it -- read it again once nothing is saving it"
    try:
        doc = hx.read_pct6(file_path)
    except (hx.Pct6Error, OSError) as exc:
        if changed():
            return cf.EXIT_CHANGED, cf.refusal(hx.WARNING, name, "changed", said)
        if isinstance(exc, hx.Pct6Error):
            return cf.EXIT_UNREADABLE, cf.refusal(hx.WARNING, name, exc.kind, str(exc))
        return cf.EXIT_UNREADABLE, cf.refusal(hx.WARNING, name, "io", "the file cannot be read: %s" % exc)
    if doc.input_sha256 != before or changed():
        return cf.EXIT_CHANGED, cf.refusal(hx.WARNING, name, "changed", said, md5=doc.input_md5)
    try:
        inv = hx.interpret(doc)
        device = hx.models.describe(doc.dev)
    except Exception as exc:  # noqa: BLE001 -- any failure past the decode is the file's, as in compare-file
        return cf.EXIT_UNREADABLE, cf.refusal(hx.WARNING, name, "interpret", "the file decoded and could not be "
                                              "interpreted (%s: %s)" % (type(exc).__name__, exc), md5=doc.input_md5)
    return cf.EXIT_COMPARED, {"name": name, "path": os.path.abspath(file_path), "doc": doc, "inv": inv,
                              "device": device, "warning": hx.WARNING}


def device_text(device):
    """The model a file names, in one line: its name and Dev code, or the Dev code of a model the reader does not know."""
    if device.get("name"):
        return "%s (Dev %s)" % (device["name"], device.get("dev"))
    return "Dev %s, a model the reader does not know" % device.get("dev")


def model_line(device):
    """What the person reads beside the warning: the model, and whether reading it has been checked."""
    return "model: %s -- %s" % (device_text(device), "checked" if device.get("verified")
                                else "NOT CHECKED: read at your own risk, every value to be checked in PC-Tool")


def now():
    """When a file was read: local time, to the second, as S-119's examples have it."""
    return datetime.datetime.now().isoformat(timespec="seconds")


# ---------------------------------------------------------------------------------------------------- attest

def compared(result):
    """`source_file.compared` from compare-file's JSON (CONTRACT.md item 13), in the form S-119 gave it: "no
    difference" when every row matches, else a list of strings -- the counts first, then each row that differs and each
    one that is unknown, with its values or its reason. An unknown is never written as no difference."""
    cf = _compare_file()
    counts = result["counts"]["result"]
    if not counts["differs"] and not counts["unknown"]:
        return "no difference"
    out = ["%s: %d match, %d differs, %d unknown" % (result["contract"], counts["match"], counts["differs"],
                                                   counts["unknown"])]
    for row in result["rows"]:
        if row["result"] == "differs":
            out.append("%s %s differs: journal %s, file %s" % (row["channel"], row["parameter"], cf._cell(row["journal"]),
                                                               cf._cell(row["file"])))
    for row in result["rows"]:
        if row["result"] == "unknown":
            out.append("%s %s unknown: %s" % (row["channel"], row["parameter"], row["reason"]))
    return out


def source_file(result, file_path, read_at=None):
    """S-119's `source_file` record of a comparison compare-file made: the file's name and full path, the md5 the reader
    took, the save time and PC-Tool version the file states, the model, when it was read, and `compared`. The eight
    keys `state.validate_preset_settings` knows, no other: an older copy of the method refuses a key it does not know."""
    f = result["file"]
    return {"name": f["name"], "path": os.path.abspath(file_path), "md5": f["md5"], "saved": f["saved"],
            "pctool": f["pctool"], "device": device_text(result["device"]), "read_at": read_at or now(),
            "compared": compared(result)}


# ---------------------------------------------------------------------------------------------------- propose

def _plain(value):
    """A number as the journal writes one: 92.0 -> 92, -2.5 stays."""
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def reach(inv, snap, identity):
    """`(rows, unreached)`: every row of the version with the reader's channel its slot names -- `(tier, key, code, row,
    channel or None, why not)` -- by compare-file's rules (CONTRACT.md item 13, "What reaches what"), and the outputs
    PC-Tool shows that no row is on, as `(label, text)`."""
    st = _state()
    outputs = [c for c in inv["channels"] if c["kind"] == "output"]
    physical = {c["label"][len("Output "):]: c for c in outputs if c.get("group") == "physical" and c.get("label")}
    virtual = virtual_by_letter(outputs)
    letter_of = {c["index"]: "Virtual " + letter for letter, c in virtual.items()}
    rows, reached = [], set()
    for tier in [t for t in st.tier_names(snap) if isinstance(snap.get(t), dict)]:
        for key, row in snap[tier].items():
            entry = identity.get(key) or {}
            code = entry.get("code") or key
            slot = str(entry.get("slot") or "").strip().upper()
            ch, why = None, None
            if tier not in ("channels", "virtual_channels"):
                why = "the file's channels are not mapped for the tier %r" % tier
            elif not slot:
                why = "project.json gives this channel no slot"
            elif not inv["device"].get("layout"):
                why = "this model's channel layout is not checked: no output is named by a slot"
            else:
                ch = (physical if tier == "channels" else virtual).get(slot)
                if ch is None:
                    why = "no channel PC-Tool shows is %s %s on this model" % (
                        "Output" if tier == "channels" else "Virtual", slot)
            if ch is not None:
                reached.add(ch["index"])
            rows.append((tier, key, code, row, ch, why))
    unreached = []
    for ch in outputs:
        if not (ch.get("group") == "physical" or ch.get("visible_in_pc_tool")) or ch["index"] in reached:
            continue
        unreached.append((letter_of.get(ch["index"], ch.get("label") or "output %s" % ch["index"]),
                          "%s, %s" % (ch.get("name") or "no name", "muted" if ch.get("mute_on") else "on")))
    return rows, unreached


def _leg(have, side):
    """`(value, None)` for a crossover leg the file gives -- `{f, type, slope}`, or None for OFF -- or `(None, why)`."""
    what = "high-pass" if side == "hp" else "low-pass"
    if not have or "position" not in have:
        return None, "the file holds no %s filter for this channel" % what
    state = have.get("state")
    if state == "off":
        return None, None
    if state == "bypassed":
        return None, "the file holds this %s bypassed, which the journal cannot record" % what
    family = XO_SHORT.get(have.get("family"))
    if state != "configured" or family is None or have.get("frequency_hz") is None or have.get("slope_db_oct") is None:
        return None, "the file holds a %s of type code %s this reader does not decode" % (what, have.get("type_code"))
    return {"f": _plain(have["frequency_hz"]), "type": family, "slope": _plain(have["slope_db_oct"])}, None


def _bands(ch, code):
    """`(bands, not taken, notes)`: the channel's EQ as the journal holds it -- every band that does something, and
    every bypassed one that would -- in slot order; the bands the journal has no name for; and what is taken short."""
    bands, skipped, notes = [], [], []
    for f in ch.get("filters") or []:
        if f.get("role") != "eq" or f.get("state") == "neutral":
            continue
        name = EQ_TYPES_BACK.get(f.get("type_code"))
        label = "%s eq[%d]" % (code, f["position"])
        if f.get("state") not in ("configured", "bypassed"):
            skipped.append((label, "the file holds a band of type code %s this reader does not decode"
                            % f["raw"].get("T", "(none)")))
            continue
        if name is None:
            skipped.append((label, "the journal has no band type for the file's %s" % (f.get("type") or f.get("type_code"))))
            continue
        if f.get("state") == "bypassed" and name in EQ_WITH_GAIN and not f.get("gain_db"):
            continue                      # bypassed and flat: does nothing either way
        if f.get("frequency_hz") is None:
            skipped.append((label, "the file holds no frequency for this band"))
            continue
        band = {"type": name, "f": _plain(f["frequency_hz"])}
        if name in EQ_WITH_GAIN:
            band["gain_db"] = f.get("gain_db")
        if name != "APF1":
            band["q"] = f.get("q")
        band["i"] = f["position"]
        if f.get("state") == "bypassed":          # a band with no `bypass` is one that is on, as the journal writes it
            band["bypass"] = True
        if any(band.get(k) is None for k in ("gain_db", "q") if k in band):
            skipped.append((label, "the file holds no %s for this band" % " or ".join(
                k for k in ("gain_db", "q") if k in band and band[k] is None)))
            continue
        if f.get("invert"):
            notes.append((label + ".invert", "the file's all-pass is inverted; the journal cannot record an invert"))
        bands.append(band)
    return bands, skipped, notes


def _channel_values(ch, row):
    """`(fields, why not)`: what the file gives one row, in the journal's units, and why each field it does not give
    is not taken -- `{field: reason}` for the fields the file holds no value for."""
    fields, why = {}, {}
    level = ch.get("level") or {}
    if level.get("state") == "present" and isinstance(level.get("value"), (int, float)):
        fields["gain_db"] = round(level["value"], 2)
    else:
        why["gain_db"] = "the file's level is %s" % (level.get("state") or "missing")
    timing = ch["timing"][0] if ch.get("timing") else {}
    delay = timing.get("delay") or {}
    if delay.get("state") == "present" and isinstance(delay.get("display_ms"), (int, float)):
        fields["ta_ms"] = delay["display_ms"]
    else:
        why["ta_ms"] = "the file's delay is %s" % (delay.get("state") or "missing")
    raw = ch.get("raw") or {}
    if raw.get("CINV") in POLARITY_BACK:
        fields["polarity"] = POLARITY_BACK[raw["CINV"]]
    else:
        why["polarity"] = "the file holds no polarity the journal can name (%r)" % raw.get("CINV")
    if raw.get("MT") in MUTE_BACK:
        fields["mute"] = MUTE_BACK[raw["MT"]]
    else:
        why["mute"] = "the file holds no mute it can name (%r)" % raw.get("MT")
    phase = timing.get("phase_degrees")
    if timing.get("phase_mode") == "phase_adjustable" or "phase_deg" in row:
        if isinstance(phase, (int, float)) and not math.isnan(phase):
            fields["phase_deg"] = phase
        else:
            why["phase_deg"] = "the file holds no phase for this channel"
    for leg, side in (("hp", "high_pass"), ("lp", "low_pass")):
        value, reason = _leg(ch.get(side), leg)
        if reason is None:
            fields[leg] = value
        else:
            why[leg] = reason
    return fields, why


def _preset_values(doc, hx):
    """`{path: value}` of the preset's settings the file stores, in `preset_settings`' paths and units."""
    values = hx.inventory.flatten(doc.root)
    out = {}
    route = doc.root.find("Route")
    position = {}
    if route is not None:
        k = 0
        for child in route:
            if child.tag == "R":
                k += 1
                position.setdefault(child.get("AOM"), k)
    for source, aom in SOURCES:
        raw = values.get("/ATF/Route[1]/R[%d]/@OFFS" % position[aom]) if aom in position else None
        try:
            linear = float(raw) if raw is not None else None
        except ValueError:
            linear = None
        if linear is not None and linear > 0 and not math.isinf(linear):
            out["sources." + source] = round(20 * math.log10(linear), 2)
    for path, at, on, off in SWITCHES:
        if values.get(at) in (on, off):
            out[path] = values[at] == on
    curve = {}
    for key, raw in values.items():
        if not key.startswith("/ATF/MCV2[1]/@RTC_"):
            continue
        name = key.rsplit("_", 1)[1]
        m = _RTC_KEY.match(name)
        try:
            number = float(raw)
        except (TypeError, ValueError):
            continue
        if m and not math.isnan(number):
            curve[name.lower()] = _plain(number / 10 if m.group(1) != "F" else number)
    if curve:
        out["rtc.curve"] = curve
    selector = next((k[:-len("/@i")] for k, v in values.items()
                     if k.startswith("/ATF/DCM") and k.endswith("/@i") and v == "0"
                     and re.search(r"/SW\[\d+\]/@i$", k)), None)
    if selector and values.get(selector + "/@A") in BT_SOURCE_BACK:
        out["bt.source"] = BT_SOURCE_BACK[values[selector + "/@A"]]
    mask = values.get(IMASK)
    if mask is not None and mask.isdigit():
        out["bt.auto_switch"] = bool(int(mask) & BT_AUTO_SWITCH_BIT)
    return out


def build(snap, identity, read):
    """What `propose --from-file` banks, from a version and a file `read_file` read: `{delta, kept, not_taken, notes}`.

    `delta` is an ordinary tier-keyed delta (`apply.apply_delta`) -- each mapped row's fields the file gives, and
    `preset_settings` -- so `propose` banks it as any other: a new version, the one before it untouched. `kept` names
    every field and row that stays as the version had it, with why; `not_taken` every output of the file no row is on
    and every band the journal has no name for; `notes` what is taken short (an all-pass invert). Each is a list of
    `(what, why)`."""
    st = _state()
    inv, doc = read["inv"], read["doc"]
    hx = _compare_file()._helix()
    delta, kept, not_taken, notes = {}, [], [], []
    rows, unreached = reach(inv, snap, identity)
    for tier, key, code, row, ch, why_not in rows:
        if ch is None:
            kept.append((code, why_not + " (every field kept)"))
            continue
        fields, why = _channel_values(ch, row)
        slots = [f for f in ch.get("filters") or [] if f.get("role") == "eq"]
        if slots:
            bands, skipped, band_notes = _bands(ch, code)
            if bands or "eq" in row:
                fields["eq"] = bands
            not_taken += skipped
            notes += band_notes
        elif row.get("eq"):
            why["eq"] = "the file holds no EQ for this channel"
        for leg in ("hp", "lp"):
            if leg in fields and fields[leg] is None and row.get(leg, "absent") in (None, "OFF"):
                fields[leg] = row[leg]            # OFF either way: the base's spelling of it, no change on the sheet
        if tier != "channels":
            for leg in ("hp", "lp"):
                # A virtual channel with no leg in the version and none working in the file: nothing to take, and
                # nothing kept -- compare-file does not compare an OFF leg there either.
                if leg not in row and fields.get(leg, "absent") is None:
                    del fields[leg]
                if leg in why and not row.get(leg) and "holds no" in why[leg]:
                    del why[leg]
        delta.setdefault(tier, {})[key] = fields
        for field in sorted(f for f in row if f not in fields and f != "status"):
            kept.append(("%s %s" % (code, field), why.get(field) or _WHY_KEPT.get(field, _NOT_DECODED)))
    not_taken = [(label, text + ": no row of this version is on this output") for label, text in unreached] + not_taken
    stated = _preset_values(doc, hx)
    settings = {}
    for path, value in stated.items():
        head, _, leaf = path.partition(".")
        settings.setdefault(head, {})[leaf] = value
    if settings:
        delta[st.PRESET_SETTINGS] = settings
    held = snap.get(st.PRESET_SETTINGS) if isinstance(snap.get(st.PRESET_SETTINGS), dict) else {}
    for path in st._PRESET_FIELDS:
        if path not in stated and st._preset_leaf(held, path) is not None:
            reason = {"input_gain_db": "the file decodes no input gain",
                      "conductor.sub_lamps": "a knob's position is not stored in the file"}.get(path, _NOT_DECODED)
            kept.append(("preset %s" % path, reason))
    return {"delta": delta, "kept": kept, "not_taken": not_taken, "notes": notes}


def provenance(read, built, read_at=None):
    """The version's `provenance`: a read of a saved file, what it was and when, and what it did not take. `propose`
    takes a `provenance` as a device read, which is its own evidence (`apply.propose`)."""
    inv = read["inv"]
    return {"kind": "pct6", "source": read["name"], "path": read["path"], "md5": read["doc"].input_md5,
            "saved": inv["device"].get("saved"), "pctool": read["doc"].pc_tool_version,
            "device": device_text(read["device"]), "read_at": read_at or now(),
            "kept": ["%s: %s" % pair for pair in built["kept"]],
            "not_taken": ["%s: %s" % pair for pair in built["not_taken"]],
            "note": "read from a saved PC-Tool file: what was saved, not proof the DSP holds it now"}


def render_names(built, base):
    """The lines that name what was not taken: every field and row kept, every output and band not taken, and what was
    taken short. Nothing is left out silently."""
    lines = []
    if built["kept"]:
        lines += ["", "Kept as %s has them -- the file does not give them (%d):" % (base, len(built["kept"]))]
        lines += ["  - %s: %s" % pair for pair in built["kept"]]
    if built["not_taken"]:
        lines += ["", "Not taken from the file (%d):" % len(built["not_taken"])]
        lines += ["  - %s: %s" % pair for pair in built["not_taken"]]
    if built["notes"]:
        lines += ["", "Taken short (%d):" % len(built["notes"])]
        lines += ["  - %s: %s" % pair for pair in built["notes"]]
    return lines
