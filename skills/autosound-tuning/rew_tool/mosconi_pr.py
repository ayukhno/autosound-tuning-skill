"""Read a Mosconi PICO 6/8-2 preset (`.PR15`): what each output is set to. Read only.

Mosconi / Gladen filter model and the PICO 6/8-2 profile contributed by Widar1979 (https://github.com/Widar1979),
https://github.com/ayukhno/autosound-tuning-skill/issues/214

    python3 mosconi_pr.py read FILE.PR15 [--json]   the outputs, their crossovers and EQ, the warning first
    python3 mosconi_pr.py --selftest                 the checks on the shipped sample; last line OK on a pass

Exit codes: 0 read, 2 the file cannot be read (its kind on stderr), 3 it changed while it was read.

What the file is: plain text, one byte (0-255) in decimal a line, 16384 lines -- one preset. An empty line is a 0.
The model is known from the extension only (`.PR15` is the PICO 6/8-2); nothing inside the file names it, and no
format or software version is stored. Offsets below are 0-based line numbers.

What is read, per output (the program's channels 1-8 sit in the file's memory slots 1, 2, 3, 4, 7, 8, 11, 12):

* level (`1280 + slot - 1`: 12 dB minus half the byte; 255 = muted) and the level kept while muted (`1292 + ...`),
  read as the file holds it, even where it disagrees with the level;
* delay (`1408 + 2 (slot - 1)`, two bytes big-endian, in steps of 250/fs ms: 1/384 ms at 96 kHz);
* polarity (`1392` low byte, `1393` high byte: bit `slot - 1` set = inverted);
* the crossover legs (`2304 + 5 n`, n 0-23, even = high-pass, odd = low-pass): family, slope, frequency, and the
  corner set, one for all legs (`2307`, bits 0-1);
* the 10 output EQ records (`9280 + 32 n`, n = 10 (slot - 1) + 1 ... + 10): type, frequency, Q, gain -- read from the
  settings the record stores, not from its coefficients, so the peak mode is not needed to read them.

And for the whole preset: the input gain of the 5 inputs (`1344 + input - 1`, attenuation in half dB), the firmware
bytes (`68`-`70`, empty when the preset was saved with no unit connected) and the sample-rate byte (`72`).

Out of scope: the mixer (its routing is not fully understood -- the contributor says so), the input EQ and the group
EQ (a second EQ layer shared by the outputs of a group; the next wave). Their bytes are not read.

Nothing here writes anything, anywhere: there is no encoder, and the file is opened only for reading. It is hashed
before it is read and after; a file that changed in between is refused (`changed`, exit 3), not read.
"""

import hashlib
import json
import os
import sys

#: Shown with every result: the reading is checked on one sample only.
WARNING = (
    "Reading .PR15 has been checked on one sample preset of one model, the Mosconi PICO 6/8-2. Treat every value "
    "as unconfirmed: check it against the screens of the vendor's own program before relying on it."
)
#: The same warning in Ukrainian, for a front end that shows Ukrainian (compare-file's `warning_uk`).
WARNING_UK = (
    "Зчитування .PR15 перевірено лише на одному зразку пресету однієї моделі — Mosconi PICO 6/8-2. Вважайте кожне "
    "значення непідтвердженим: перш ніж покладатися на нього, звірте його з екранами власної програми виробника."
)
#: Shown with every result, in the text and in `--json`: whose work the model and the profile are.
CREDIT = ("Mosconi / Gladen filter model and the PICO 6/8-2 profile contributed by Widar1979 "
          "(https://github.com/Widar1979) -- https://github.com/ayukhno/autosound-tuning-skill/issues/214")

LINES = 16384
DEVICE = {"dev": "15", "vendor": "Mosconi", "name": "PICO 6/8-2 DSP", "extension": ".PR15", "outputs": 8,
          "rate_hz": 96000}
#: The program's output channel 1-8 -> the file's memory slot.
CHANNEL_SLOTS = (1, 2, 3, 4, 7, 8, 11, 12)
INPUTS = 5
EQ_BANDS = 10

_LEVEL, _LEVEL_MUTED, _INPUT_GAIN, _POLARITY, _DELAY = 1280, 1292, 1344, 1392, 1408
_XOVER, _XOVER_LEN, _EQ, _EQ_LEN = 2304, 5, 9280, 32
_FIRMWARE, _RATE = (68, 69, 70), 72
_MUTED = 255
_RATES = {1: 48000, 2: 96000}
#: The family bits of a crossover control byte, in the journal's short names (the profile's `types`).
FAMILIES = ("LR", "BE", "BW", "CHEBYSHEV")
SLOPES = (0, 6, 12, 18, 24)
CORNER_SETS = ("default", "normalized to -3 dB", "normalized to -6 dB")
#: The EQ record's type byte, as far as the sample shows it: peak, low shelf, high shelf. Any other code is read as
#: a code, its settings beside it, and named undecoded.
EQ_TYPES = {134: "PK", 133: "LSH", 132: "HSH"}


class PrError(ValueError):
    """A file this reader does not read. `kind` says why in one word: io, model, format, truncated, changed."""

    def __init__(self, kind, message):
        super().__init__(message)
        self.kind = kind


def is_preset_path(path):
    """True for a name with a `.PR<number>` extension: a preset of this vendor's family (only 15 is read)."""
    ext = os.path.splitext(str(path))[1].upper()
    return ext.startswith(".PR") and ext[3:].isdigit()


def _sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _read_bytes(path):
    with open(path, "rb") as fh:
        return fh.read()


def _values(data):
    """The file's bytes -> (values, empty line offsets). Raises `PrError` for anything but one byte a line."""
    try:
        text = data.decode("ascii")
    except UnicodeDecodeError:
        raise PrError("format", "not a preset: the file is not plain text") from None
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()                                   # the line break after the last line
    values, empty = [], set()
    for n, line in enumerate(lines):
        line = line.rstrip("\r").strip()
        if not line:
            values.append(0)
            empty.add(n)
            continue
        if not line.isdigit() or int(line) > 255:
            raise PrError("format", "not a preset: line %d holds %r, not a byte" % (n + 1, line[:20]))
        values.append(int(line))
    if len(lines) < LINES:
        raise PrError("truncated", "a preset has %d lines; this file has %d" % (LINES, len(lines)))
    if len(lines) > LINES:
        raise PrError("format", "a preset has %d lines; this file has %d (a whole setup is not read)"
                      % (LINES, len(lines)))
    return values, empty


def _level(byte):
    """A level byte -> dB, or None for a byte past -100 dB that is not the mute code."""
    return 12 - byte / 2 if byte <= 224 else None


def _leg(values, n):
    """One crossover leg. A slope code past the five this reader knows (5-7) is `undecoded`, its slope None: never
    read as off."""
    control = values[_XOVER + _XOVER_LEN * n:_XOVER + _XOVER_LEN * n + _XOVER_LEN]
    code = (control[0] >> 2) & 7
    not_set = bool(control[0] & 64)
    if not_set:
        slope, state = 0, "off"
    elif code < len(SLOPES):
        slope = SLOPES[code]
        state = "on" if slope else "off"
    else:
        slope, state = None, "undecoded"
    return {"side": "high_pass" if n % 2 == 0 else "low_pass", "family": FAMILIES[control[0] & 3],
            "slope_db_oct": slope, "slope_code": code, "state": state, "frequency_hz": control[1] * 256 + control[2],
            "locked": bool(control[0] & 32), "not_initialised": not_set, "offset": _XOVER + _XOVER_LEN * n,
            "control": control}


def _gain(b27, b28):
    """The stored gain: quarters of a dB in byte 27 and the fraction in 255ths in byte 28, both 255 - x below 0."""
    if b27 >= 128:
        return -round(((255 - b27) + (255 - b28) / 255) / 4, 2) + 0.0
    return round((b27 + b28 / 255) / 4, 2)


def _band(values, slot, k):
    n = (slot - 1) * EQ_BANDS + k
    at = _EQ + _EQ_LEN * n
    r = values[at:at + _EQ_LEN]
    name = EQ_TYPES.get(r[20])
    gain = _gain(r[27], r[28])
    if name is None:
        state = "undecoded"
    else:
        state = "neutral" if gain == 0 else "configured"
    return {"band": k, "type": name, "type_code": r[20], "frequency_hz": r[23] * 256 + r[24],
            "q": round((r[25] * 256 + r[26]) / 1024, 4), "gain_db": gain, "state": state,
            "checksum_ok": r[29] == sum(r[:20]) & 255, "offset": at}


def decode(values, empty=frozenset()):
    """A preset's values (one byte per line) -> what it holds. `empty`: offsets of empty lines (saved offline)."""
    rate_byte = values[_RATE]
    rate_hz = _RATES.get(rate_byte)
    steps_per_ms = (rate_hz or DEVICE["rate_hz"]) / 250
    mask = values[_POLARITY] | (values[_POLARITY + 1] << 8)
    outputs = []
    for channel, slot in enumerate(CHANNEL_SLOTS, start=1):
        byte, kept = values[_LEVEL + slot - 1], values[_LEVEL_MUTED + slot - 1]
        muted = byte == _MUTED
        steps = values[_DELAY + 2 * (slot - 1)] * 256 + values[_DELAY + 2 * (slot - 1) + 1]
        legs = [i for i in range(24) if (i // 4) * 2 + ((i >> 1) & 1) + 1 == slot]
        outputs.append({
            "channel": channel, "slot": slot, "muted": muted,
            "level_db": _level(kept if muted else byte), "level_byte": byte,
            "level_while_muted_db": _level(kept), "level_while_muted_byte": kept,
            "delay_steps": steps, "delay_ms": round(steps / steps_per_ms, 6),
            "polarity": "INV" if mask >> (slot - 1) & 1 else "NORM",
            "high_pass": _leg(values, legs[0]), "low_pass": _leg(values, legs[1]),
            "eq": [_band(values, slot, k) for k in range(1, EQ_BANDS + 1)],
        })
    corner = values[_XOVER + 3] & 3
    firmware = [values[i] for i in _FIRMWARE]
    return {
        "device": dict(DEVICE),
        "firmware": None if any(i in empty for i in _FIRMWARE) else {
            "bytes": firmware, "version": "%.2f" % (firmware[0] + firmware[1] / 10 + firmware[2] / 100)},
        "rate": {"byte": None if _RATE in empty else rate_byte, "hz": rate_hz,
                 "delay_steps_per_ms": steps_per_ms, "assumed": rate_hz is None},
        "corner_set": {"code": corner, "name": CORNER_SETS[corner] if corner < len(CORNER_SETS) else None},
        "input_gain": [{"input": i, "attenuation_db": values[_INPUT_GAIN + i - 1] / 2} for i in range(1, INPUTS + 1)],
        "outputs": outputs,
        "not_read": ["the mixer", "the input EQ", "the group EQ"],
    }


def read_pr(path):
    """Everything this reader takes from the preset at `path`, with the warning and the file's hashes.

    Raises `PrError`: `io` (not there, not to be opened), `model` (another `.PR` model than 15), `format` (not one byte
    a line), `truncated` (fewer lines than a preset), `changed` (the file changed while it was read)."""
    name = os.path.basename(path)
    if os.path.splitext(name)[1].upper() != DEVICE["extension"]:
        raise PrError("model", "only %s (the %s) is read; %s is another model"
                      % (DEVICE["extension"], DEVICE["name"], name))
    try:
        before = _sha256(path)
        data = _read_bytes(path)
        after = _sha256(path)
    except OSError as exc:
        raise PrError("io", "the file cannot be read: %s" % exc) from None
    if hashlib.sha256(data).hexdigest() != before or after != before:
        raise PrError("changed", "the file changed while it was read: read it again once nothing is saving it")
    values, empty = _values(data)
    out = decode(values, empty)
    out["warning"] = WARNING
    out["credit"] = CREDIT
    out["file"] = {"name": name, "md5": hashlib.md5(data).hexdigest(), "sha256": before, "lines": LINES}
    return out


def _leg_text(leg):
    if leg["state"] == "off":
        return "off"
    if leg["state"] == "undecoded":
        return "%s at %d Hz, slope code %d not decoded" % (leg["family"], leg["frequency_hz"], leg["slope_code"])
    return "%s %d at %d Hz" % (leg["family"], leg["slope_db_oct"], leg["frequency_hz"])


def _level_text(o):
    """An output's level as a person reads it; a byte past -100 dB that is not the mute code is said as not decoded."""
    if o["muted"]:
        if o["level_db"] is None:
            return "muted (level not decoded (byte %d))" % o["level_while_muted_byte"]
        return "muted (level %s dB)" % o["level_db"]
    if o["level_db"] is None:
        return "level not decoded (byte %d)" % o["level_byte"]
    return "%+g dB" % o["level_db"]


def summary(reading):
    """The text a person reads: the warning first, then one block an output."""
    rate = reading["rate"]
    fw = reading["firmware"]
    lines = [reading["warning"], "",
             "%s %s, file %s (md5 %s)" % (reading["device"]["vendor"], reading["device"]["name"],
                                         reading["file"]["name"], reading["file"]["md5"]),
             "firmware %s, rate byte %s (%s Hz%s), corner set %s" % (
                 fw["version"] if fw else "not stored", rate["byte"], rate["hz"] or reading["device"]["rate_hz"],
                 ", assumed" if rate["assumed"] else "", reading["corner_set"]["name"]),
             "input attenuation dB: " + ", ".join("%g" % g["attenuation_db"] for g in reading["input_gain"]),
             "not read: " + ", ".join(reading["not_read"]), ""]
    for o in reading["outputs"]:
        lines.append("output %d (slot %d): %s, delay %.3f ms, %s, HP %s, LP %s" % (
            o["channel"], o["slot"], _level_text(o), o["delay_ms"], o["polarity"], _leg_text(o["high_pass"]),
            _leg_text(o["low_pass"])))
        for b in o["eq"]:
            if b["state"] != "neutral":
                lines.append("    EQ %d: %s %d Hz Q %.2f %+.2f dB" % (
                    b["band"], b["type"] or "code %d" % b["type_code"], b["frequency_hz"], b["q"], b["gain_db"]))
    lines += ["", reading["credit"]]
    return "\n".join(lines)


def main(argv):
    if argv[:1] != ["read"] or len([a for a in argv[1:] if a != "--json"]) != 1:
        print(__doc__.split("\n\n")[1], file=sys.stderr)
        return 2
    path = next(a for a in argv[1:] if a != "--json")
    try:
        reading = read_pr(path)
    except PrError as exc:
        print("error: %s: %s: %s" % (os.path.basename(path), exc.kind, exc), file=sys.stderr)
        return 3 if exc.kind == "changed" else 2
    print(json.dumps(reading, indent=2) if "--json" in argv else summary(reading))
    return 0


# ---- selftest: below this line the module's own checks; the never-writes scan reads the source above it ----

SAMPLE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "testdata", "mosconi-pr", "example_pico682.PR15")
SAMPLE_SHA256 = "dffbfd2991b0f0a4f5fcddd0a7e25f5ed4c63b905efa1afa49c91828266f540e"
_MARK = "# ---- selftest: below this line"

#: The sample's settings, from the contributor's list of what is set in it; each checked by hand against the file.
#: (channel, slot, level dB, muted, polarity, delay steps, delay ms to 3 places, level-while-muted byte)
EXPECTED_OUTPUTS = (
    (1, 1, 0.0, False, "INV", 2611, 6.799, 22),     # the kept byte reads 22 (+1 dB) while the level is 24 (0 dB)
    (2, 2, 3.0, False, "INV", 1647, 4.289, 18),
    (3, 3, 0.0, True, "NORM", 0, 0.0, 24),
    (4, 4, 0.0, True, "NORM", 0, 0.0, 24),
    (5, 7, -1.5, False, "NORM", 1992, 5.188, 27),
    (6, 8, 0.0, False, "NORM", 1582, 4.120, 24),
    (7, 11, 0.0, False, "INV", 0, 0.0, 24),
    (8, 12, 0.0, True, "NORM", 0, 0.0, 24),
)
#: channel -> (high-pass, low-pass), each (family, slope, Hz) or None for off.
EXPECTED_LEGS = {
    1: (("LR", 18, 2000), None), 2: (("LR", 18, 2000), None), 3: (None, ("BW", 18, 80)),
    4: (("BW", 6, 80), ("BW", 12, 2000)), 5: (("BE", 12, 70), ("LR", 12, 2400)), 6: (("BW", 6, 80), ("BW", 12, 2000)),
    7: (None, ("LR", 24, 80)), 8: (None, ("LR", 24, 80)),
}
_CH3 = ((1, "LSH", 60, 1.00, -0.4), (2, "PK", 81, 3.57, 1.1), (3, "PK", 185, 2.71, -5.2), (4, "PK", 358, 1.14, -7.8),
        (5, "PK", 499, 2.22, 6.6), (6, "PK", 886, 2.05, -9.2), (7, "PK", 1513, 2.50, 1.9), (8, "HSH", 4000, 1.00, -5.6))
_CH4 = ((1, "LSH", 60, 1.00, -5.2), (2, "PK", 96, 5.00, -7.7), (3, "PK", 102, 3.19, 3.4), (4, "PK", 926, 2.96, -9.7),
        (5, "PK", 1638, 2.83, 5.0), (6, "PK", 2130, 1.18, -5.7), (7, "PK", 3486, 3.04, -5.6), (8, "PK", 3910, 2.57, 4.3),
        (9, "HSH", 4000, 1.00, -4.9))
#: channel -> the bands that do something: (band, type, Hz, Q to 2 places, dB). Every other band is a 0 dB peak.
EXPECTED_EQ = {
    1: ((1, "PK", 570, 4.42, 4.0), (2, "PK", 849, 1.00, -1.2), (3, "LSH", 900, 1.00, -9.0), (4, "PK", 1245, 2.87, 4.2),
        (5, "PK", 1933, 1.00, -3.6), (6, "PK", 2083, 3.59, -2.3), (7, "PK", 6000, 4.00, 3.0),
        (8, "PK", 9968, 2.03, -1.8), (9, "HSH", 12000, 1.00, 3.5)),
    2: ((1, "PK", 649, 3.66, 0.6), (2, "LSH", 989, 1.00, -8.9), (3, "PK", 1055, 4.90, -2.4), (4, "PK", 1550, 1.27, 2.7),
        (5, "PK", 2452, 2.36, -4.9), (6, "PK", 7026, 4.85, -2.4), (7, "HSH", 12500, 1.00, 3.2),
        (8, "PK", 4504, 3.00, -0.9)),
    3: _CH3, 4: _CH4, 5: _CH3, 6: _CH4, 7: (), 8: (),
}


def _check_sample_is_the_shipped_one():
    assert _sha256(SAMPLE) == SAMPLE_SHA256, "the shipped sample is not the contributor's file byte for byte"


def _check_values_on_the_sample():
    """Every value this reader takes, against the sample's settings list."""
    r = read_pr(SAMPLE)
    assert r["warning"] == WARNING and r["device"]["name"] == "PICO 6/8-2 DSP", r["device"]
    assert r["credit"] == CREDIT and summary(r).endswith("\n" + CREDIT), r["credit"]
    assert "https://github.com/Widar1979" in CREDIT and "/issues/214" in CREDIT, CREDIT
    assert r["firmware"] == {"bytes": [5, 2, 5], "version": "5.25"}, r["firmware"]
    assert (r["rate"]["byte"], r["rate"]["hz"], r["rate"]["assumed"]) == (2, 96000, False), r["rate"]
    assert r["corner_set"] == {"code": 0, "name": "default"}, r["corner_set"]
    assert [g["attenuation_db"] for g in r["input_gain"]] == [0.0] * INPUTS, r["input_gain"]
    assert len(r["outputs"]) == 8
    for (channel, slot, level, muted, pol, steps, ms, kept), o in zip(EXPECTED_OUTPUTS, r["outputs"]):
        got = (o["channel"], o["slot"], o["level_db"], o["muted"], o["polarity"], o["delay_steps"],
               o["level_while_muted_byte"])
        assert got == (channel, slot, level, muted, pol, steps, kept), (got, channel)
        assert abs(o["delay_ms"] - ms) <= 0.0005 + 1e-9, (o["delay_ms"], ms, channel)   # the list shows 3 places
        for leg, want in zip(("high_pass", "low_pass"), EXPECTED_LEGS[channel]):
            have = o[leg]
            assert (have["state"] == "off") == (want is None), (channel, leg, have)
            if want is not None:
                assert (have["family"], have["slope_db_oct"], have["frequency_hz"]) == want, (channel, leg, have)
        active = tuple((b["band"], b["type"], b["frequency_hz"], round(b["q"], 2), b["gain_db"])
                       for b in o["eq"] if b["state"] != "neutral")
        assert active == EXPECTED_EQ[channel], (channel, active)
        assert len(o["eq"]) == EQ_BANDS and all(b["checksum_ok"] for b in o["eq"]), channel


def _check_never_writes():
    """The reader's source holds no write call: the scan reads the code above the selftest mark, and fails if that is
    nothing."""
    with open(os.path.abspath(__file__), encoding="utf-8") as fh:
        src = fh.read()
    assert src.count(_MARK) == 2, "the selftest mark is not where the scan expects it"   # here and at its line
    code = src[:src.index("\n" + _MARK)]
    assert len(code) > 4000 and "def read_pr(" in code and "def decode(" in code, "the scan read no reader"
    quote = chr(34)
    banned = [quote + m + quote for m in ("w", "wb", "x", "xb", "a", "ab", "w+", "r+", "rb+")]
    banned += [chr(39) + m + chr(39) for m in ("w", "wb", "x", "xb", "a", "ab")]
    banned += ["write_bytes", "write_text", ".write(", "os.rename", "os.replace", "shutil", "os.remove", "unlink",
               "tempfile", "os.makedirs", "os.mkdir"]
    found = [b for b in banned if b in code]
    assert not found, "the reader holds %s" % found


def _check_a_change_while_read_is_refused():
    """The file is hashed before it is read and after: a file that changes in between is `changed` (exit 3)."""
    import shutil
    import tempfile
    global _read_bytes
    real = _read_bytes
    top = tempfile.mkdtemp(prefix="selftest_mosconi_pr_")
    try:
        path = os.path.join(top, "changing.PR15")
        shutil.copyfile(SAMPLE, path)

        def changing(p):
            data = real(p)
            with open(p, "ab") as fh:
                fh.write(b"0\r\n")
            return data
        _read_bytes = changing
        try:
            read_pr(path)
        except PrError as exc:
            assert exc.kind == "changed", exc.kind
        else:
            raise AssertionError("a file that changed while read was read")
        assert main(["read", path]) == 3
    finally:
        _read_bytes = real
        shutil.rmtree(top, ignore_errors=True)


def _check_unreadable_files_are_named():
    """Not there, another model, not a preset, cut short, one line too many, a byte over 255: refused with the kind,
    exit 2."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="selftest_mosconi_pr_")
    try:
        with open(SAMPLE, "rb") as fh:
            data = fh.read()
        lines = data.split(b"\n")
        big = b"\n".join(lines[:100] + [b"256\r"] + lines[101:])
        cases = {"none.PR15": None, "other.PR16": data, "garbage.PR15": b"\x00\x01 not a preset\r\n" * 9,
                 "cut.PR15": data[:len(data) // 2], "extra.PR15": data + b"0\r\n", "big.PR15": big}
        for name, body in cases.items():
            path = os.path.join(top, name)
            if body is not None:
                with open(path, "wb") as fh:
                    fh.write(body)
            want = {"none.PR15": "io", "other.PR16": "model", "garbage.PR15": "format", "cut.PR15": "truncated",
                    "extra.PR15": "format", "big.PR15": "format"}[name]
            try:
                read_pr(path)
            except PrError as exc:
                assert exc.kind == want, (name, exc.kind, str(exc))
            else:
                raise AssertionError("%s was read" % name)
            assert main(["read", path]) == 2, name
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_reading_leaves_the_file_as_it_was():
    before = _sha256(SAMPLE)
    listing = sorted(os.listdir(os.path.dirname(SAMPLE)))
    read_pr(SAMPLE)
    summary(read_pr(SAMPLE))
    assert _sha256(SAMPLE) == before and sorted(os.listdir(os.path.dirname(SAMPLE))) == listing


def _sample_with(top, name, lines):
    """A copy of the sample in `top` with `lines` ({0-based line: text}) changed: this selftest's own file only."""
    with open(SAMPLE, "rb") as fh:
        rows = fh.read().split(b"\n")
    for n, text in lines.items():
        rows[n] = text.encode("ascii") + (b"\r" if rows[n].endswith(b"\r") else b"")
    path = os.path.join(top, name)
    with open(path, "wb") as fh:
        fh.write(b"\n".join(rows))
    return path


def _check_an_undecoded_slope_code_is_not_off():
    """A crossover leg whose slope code this reader does not decode (5-7) is `undecoded` with no slope -- never read
    as OFF -- and the summary says the code."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="selftest_mosconi_pr_")
    try:
        with open(SAMPLE, "rb") as fh:
            byte = int(fh.read().split(b"\n")[_XOVER + _XOVER_LEN].strip() or b"0")
        path = _sample_with(top, "slope.PR15", {_XOVER + _XOVER_LEN: str((byte & ~(7 << 2) & ~64) | (5 << 2))})
        r = read_pr(path)
        leg = r["outputs"][0]["low_pass"]
        assert (leg["state"], leg["slope_db_oct"], leg["slope_code"]) == ("undecoded", None, 5), leg
        assert "slope code 5" in summary(r), summary(r)
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_a_level_byte_it_does_not_decode_is_said():
    """A level byte past -100 dB that is not the mute code (225-254) is read as no level, and `read` says it: "level
    not decoded (byte N)" -- not a crash."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="selftest_mosconi_pr_")
    try:
        r = read_pr(_sample_with(top, "level.PR15", {_LEVEL: "230"}))
        assert r["outputs"][0]["level_db"] is None, r["outputs"][0]
        assert "level not decoded (byte 230)" in summary(r), summary(r)
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _selftest():
    import contextlib
    import io
    checks = (_check_sample_is_the_shipped_one, _check_values_on_the_sample, _check_never_writes,
              _check_a_change_while_read_is_refused, _check_unreadable_files_are_named,
              _check_reading_leaves_the_file_as_it_was, _check_an_undecoded_slope_code_is_not_off,
              _check_a_level_byte_it_does_not_decode_is_said)
    failures = []
    for check in checks:
        try:
            with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
                check()
        except Exception as exc:  # noqa: BLE001 -- every failure is reported, none stops the others
            failures.append("%s: %s: %s" % (check.__name__, type(exc).__name__, exc))
    for line in failures:
        print("FAIL " + line)
    if failures:
        print("mosconi_pr selftest: %d of %d checks failed" % (len(failures), len(checks)))
        return 1
    print("mosconi_pr selftest OK -- %d checks on %s" % (len(checks), os.path.basename(SAMPLE)))
    return 0


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import console                       # issue #21: a code page must not destroy a result
    console.install()
    if "--selftest" in sys.argv[1:]:
        sys.exit(_selftest())
    sys.exit(main(sys.argv[1:]))
