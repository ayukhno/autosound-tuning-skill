"""REW's **Generic** equaliser block — the format to reach for when a DSP has no format of its own.

REW writes this with Equaliser = Manufacturer "Generic", Model "Generic". It is a real, pasteable
block rather than a listing to type from, which is what makes it the right default: a processor we
have no vendor writer for still gets something a person can move in one action.

Sibling of `atf_eq.py`, and the differences from that bank are the whole reason this is a separate
module rather than a flag:

  * **The header is one word, `Generic`** — no size in it, unlike
    `Audiotec_Fischer_Full_EQ_(30_bands)`.
  * **Twenty bands**, and the count lives nowhere in the text.
  * **More columns**: `Shape`, `Slope_dB/oct`, `Frequency2(Hz)`, `_Q2_`, `Slope2_dB/oct` follow
    `TargetT60(ms)`. They are what lets this block carry crossovers as well as EQ.
  * **Different precision, and it is not cosmetic** — REW writes frequency to 2 decimals here
    against 1 in the ATF bank, and a PK's Q to 3 against 2. A block emitted with the other
    module's precision parses fine and is not what REW produces, which is exactly the class of
    difference a value-level round-trip cannot see (see `atf_eq`'s byte-exact check for why that
    matters).

**Crossovers.** Both flavours can carry a high-pass and a low-pass; they differ in WHERE. Generic
puts them in a trailing `Compound_filters` section, Extended puts them inline as numbered rows:

    4	True	Manual	High_pass	50.00					BU	36
    5	True	Manual	Low_pass	250.00					L-R	12

`BU` is Butterworth, `L-R` Linkwitz-Riley, and the slope is in dB/oct. Inline rows are read AND
written (an Extended block is then a whole channel in one paste); the separate `Compound_filters`
section is read but not written, because Extended is the flavour to emit when crossovers are in
play and two ways to write the same fact is how they come to disagree.

⚠️ **Reading a crossover is not applying one.** A pasted EQ bank is what somebody asked for; a
crossover arriving with it CHANGES WHAT THE DRIVER PLAYS, and a tuner who did not notice the two
extra rows has had their acoustic design edited by a clipboard. `eq_export.crossover_disposition`
holds that decision — for a physical driver it ASKS, and for a tier whose profile says it has no
crossovers at all it ignores them and says so.

stdlib only, py3.9+.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass

#: The two flavours REW offers under Manufacturer "Generic". Same 14 columns, same 20 slots — they
#: differ in ONE structural way, and it is the one that matters here: **Extended puts crossovers
#: inline as numbered band rows, Generic puts them in a separate `Compound_filters` section.** So
#: an Extended block is a whole channel in one paste, which is why it is the one the author reaches
#: for by hand (2026-08-23) and the better default for us.
GENERIC, EXTENDED = "Generic", "Extended"
HEADER = GENERIC
COL_HEADER = ("Number\tEnabled\tControl\tType\tFrequency(Hz)\tGain(dB)\tQ\tBandwidth(Hz)\t"
              "TargetT60(ms)\tShape\tSlope_dB/oct\tFrequency2(Hz)\t_Q2_\tSlope2_dB/oct")
COMPOUND_HEADER = "Compound_filters"
N_BANDS = 20
_SHELVES = ("LS_Q", "HS_Q")

#: Crossover family as this block spells it. `atf_eq` has no equivalent: the Audiotec-Fischer bank
#: is EQ-only and its crossovers are separate device fields.
SHAPES = {"BW": "BU", "LR": "L-R", "BE": "BE"}


#: Row types that are a CROSSOVER rather than an EQ band. In Extended they sit in the numbered
#: list beside the PKs; in Generic they live in the trailing section instead.
CROSSOVER_TYPES = ("High_pass", "Low_pass")


@dataclass
class Band:
    number: int
    type: str = "None"          # PK | LS_Q | HS_Q | AP1 | AP2 | High_pass | Low_pass | None
    enabled: bool = True
    control: str = "Auto"       # Auto | Manual
    freq: "float | None" = None
    gain: "float | None" = None
    q: "float | None" = None
    bandwidth: "float | None" = None
    #: Crossover rows only: `BU` / `L-R` / `BE`, and the slope in dB per octave.
    shape: "str | None" = None
    slope: "int | None" = None

    @property
    def active(self) -> bool:
        return self.type != "None"

    @property
    def is_crossover(self) -> bool:
        return self.type in CROSSOVER_TYPES


@dataclass
class Compound:
    """One high-pass or low-pass row from the `Compound_filters` section."""

    number: int
    kind: str                    # High_pass | Low_pass
    freq: "float | None" = None
    shape: "str | None" = None   # BU | L-R | BE
    slope: "int | None" = None
    enabled: bool = True
    control: str = "Manual"


def _num(s):
    s = (s or "").strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def parse_generic(text_or_path):
    """Read a Generic block into `(bands, compounds)`.

    Both halves come back because a caller reading somebody's exported settings must not silently
    receive half of them: a block whose crossovers vanished on import looks like a tune that never
    had any.
    """
    text = text_or_path
    if "\n" not in text_or_path and len(text_or_path) < 4096:
        try:
            with open(text_or_path, encoding="utf-8") as f:
                text = f.read()
        except OSError:
            pass

    bands, compounds, in_compound = [], [], False
    for line in text.split("\n"):
        if not line.strip():
            continue
        if line.strip() == COMPOUND_HEADER:
            in_compound = True
            continue
        if line.startswith(HEADER) or line.startswith("Number\t"):
            continue
        cells = line.split("\t")
        if len(cells) < 4:
            continue
        try:
            number = int(cells[0].strip())
        except ValueError:
            continue
        enabled = cells[1].strip().lower() == "true"
        control = cells[2].strip()
        kind = cells[3].strip()
        if in_compound:
            compounds.append(Compound(
                number=number, kind=kind, freq=_num(_at(cells, 4)),
                shape=(_at(cells, 9) or "").strip() or None,
                slope=int(float(_at(cells, 10))) if _num(_at(cells, 10)) is not None else None,
                enabled=enabled, control=control))
        else:
            slope = _num(_at(cells, 10))
            bands.append(Band(number=number, type=kind or "None", enabled=enabled,
                              control=control, freq=_num(_at(cells, 4)),
                              gain=_num(_at(cells, 5)), q=_num(_at(cells, 6)),
                              bandwidth=_num(_at(cells, 7)),
                              shape=(_at(cells, 9) or "").strip() or None,
                              slope=int(slope) if slope is not None else None))
    return bands, compounds


def _at(cells, i):
    return cells[i] if i < len(cells) else ""


def active_bands(bands):
    return [b for b in bands if b.active]


def _fmt(x, nd):
    return "" if x is None else f"{x:.{nd}f}"


def format_generic(bands, n_bands=N_BANDS, flavour=GENERIC) -> str:
    """Render the Generic block: header, columns, then exactly `n_bands` rows.

    Precision is REW's own for THIS block and differs from the ATF bank's — frequency to 2
    decimals, a PK's Q to 3, a shelf's Q to 2. Checked byte for byte against a real export in the
    selftest, because a value-level round-trip cannot see a formatting difference: it re-reads our
    own output with our own parser and reports success either way.

    The `Compound_filters` section is not written — see the module docstring.
    """
    by_num = {b.number: b for b in bands}
    out = [flavour, COL_HEADER + "\t"]
    for n in range(1, n_bands + 1):
        b = by_num.get(n)
        if b is None or b.type == "None":
            out.append(f"{n}\tTrue\tAuto\tNone\t")
            continue
        en = "True" if b.enabled else "False"
        if b.type == "PK":
            out.append(f"{n}\t{en}\t{b.control}\tPK\t{_fmt(b.freq,2)}\t"
                       f"{_fmt(b.gain,1)}\t{_fmt(b.q,3)}\t{_fmt(b.bandwidth,2)}\t")
        elif b.type in _SHELVES:
            out.append(f"{n}\t{en}\t{b.control}\t{b.type}\t{_fmt(b.freq,2)}\t"
                       f"{_fmt(b.gain,1)}\t{_fmt(b.q,2)}\t")
        elif b.type == "AP2":
            out.append(f"{n}\t{en}\t{b.control}\tAP2\t{_fmt(b.freq,2)}\t\t{_fmt(b.q,3)}\t")
        elif b.type == "AP1":
            out.append(f"{n}\t{en}\t{b.control}\tAP1\t{_fmt(b.freq,2)}\t")
        elif b.is_crossover:
            # Gain / Q / Bandwidth / TargetT60 stay EMPTY and their tabs are still written: the
            # columns are positional, so Shape must land in the tenth field or it reads as a Q.
            out.append(f"{n}\t{en}\t{b.control}\t{b.type}\t{_fmt(b.freq,2)}\t\t\t\t\t"
                       f"{b.shape or ''}\t{'' if b.slope is None else int(b.slope)}\t")
        else:
            out.append(f"{n}\t{en}\t{b.control}\t{b.type}\t")
    return "\n".join(out) + "\n"


# ── selftest ───────────────────────────────────────────────────────────────────
#: A real REW Generic export, supplied by the user 2026-08-23. The reference this module is
#: checked against — not a fixture this module wrote for itself.
_REFERENCE = (
    "Generic\n"
    "Number\tEnabled\tControl\tType\tFrequency(Hz)\tGain(dB)\tQ\tBandwidth(Hz)\tTargetT60(ms)\t"
    "Shape\tSlope_dB/oct\tFrequency2(Hz)\t_Q2_\tSlope2_dB/oct\t\n"
    "1\tTrue\tAuto\tPK\t20.00\t1.0\t2.500\t8.00\t\n"
    "2\tTrue\tManual\tLS_Q\t25.00\t-3.3\t0.71\t\n"
    "3\tTrue\tManual\tHS_Q\t31.50\t-12.0\t2.00\t\n"
    + "".join(f"{n}\tTrue\tAuto\tNone\t\n" for n in range(4, 21))
)
_REFERENCE_COMPOUND = (
    "Compound_filters\n"
    "1\tTrue\tManual\tHigh_pass\t50.00\t\t\t\t\tBU\t36\t\n"
    "2\tTrue\tManual\tLow_pass\t250.00\t\t\t\t\tL-R\t12\n"
)


def _selftest():
    bands, compounds = parse_generic(_REFERENCE)
    assert len(bands) == 20, len(bands)
    act = active_bands(bands)
    assert [b.type for b in act] == ["PK", "LS_Q", "HS_Q"], [b.type for b in act]
    assert (act[0].freq, act[0].gain, act[0].q, act[0].bandwidth) == (20.0, 1.0, 2.5, 8.0), act[0]
    assert (act[1].freq, act[1].gain, act[1].q) == (25.0, -3.3, 0.71), act[1]
    assert not compounds, "the reference bank has no compound section"

    # BYTE-exact against REW's own output. The precision here is NOT the ATF bank's, and this is
    # the assertion that knows it: 20.00 not 20.0, 2.500 not 2.50, 0.71 not 0.7.
    emitted = format_generic(bands)
    assert emitted == _REFERENCE, (
        "emitted text differs from the real REW export:\n"
        + "\n".join(f"  line {i+1}\n    REW:  {a!r}\n    ours: {b!r}"
                    for i, (a, b) in enumerate(zip(_REFERENCE.split("\n"),
                                                   emitted.split("\n"))) if a != b))
    # ...and the ATF precision would NOT pass, which is why the two modules exist separately.
    assert "\t20.0\t" not in emitted and "\t2.50\t" not in emitted, emitted.split("\n")[2]

    # The crossover section is READ, so importing somebody's block does not silently lose half of
    # it — a tune whose crossovers vanished on import looks like a tune that never had any.
    _b, comp = parse_generic(_REFERENCE + _REFERENCE_COMPOUND)
    assert [(c.kind, c.freq, c.shape, c.slope) for c in comp] == [
        ("High_pass", 50.0, "BU", 36), ("Low_pass", 250.0, "L-R", 12)], comp
    # Writing it is a pending decision of the user's, so it must NOT appear on output yet.
    assert COMPOUND_HEADER not in format_generic(_b), "compound filters are not written yet"

    # The families as this block spells them -- `BU`/`L-R`, not our ledger's `BW`/`LR`.
    assert SHAPES["BW"] == "BU" and SHAPES["LR"] == "L-R", SHAPES

    # Extended, byte-exact against the user's own export: same columns, different header, and the
    # crossovers INLINE among the numbered rows rather than in a trailing section.
    ext = ("Extended\n" + COL_HEADER + "\t\n"
           "1\tTrue\tAuto\tPK\t20.00\t1.0\t2.500\t8.00\t\n"
           "2\tTrue\tManual\tLS_Q\t25.00\t-3.3\t0.71\t\n"
           "3\tTrue\tManual\tHS_Q\t31.50\t-12.0\t2.00\t\n"
           "4\tTrue\tManual\tHigh_pass\t50.00\t\t\t\t\tBU\t36\t\n"
           "5\tTrue\tManual\tLow_pass\t250.00\t\t\t\t\tL-R\t12\t\n"
           + "".join(f"{n}\tTrue\tAuto\tNone\t\n" for n in range(6, 21)))
    eb, ec = parse_generic(ext)
    assert not ec, "in Extended the crossovers are BANDS, not a separate section"
    xr = [b for b in active_bands(eb) if b.is_crossover]
    assert [(b.number, b.type, b.freq, b.shape, b.slope) for b in xr] == [
        (4, "High_pass", 50.0, "BU", 36), (5, "Low_pass", 250.0, "L-R", 12)], xr
    assert format_generic(eb, flavour=EXTENDED) == ext, "Extended must round-trip byte-exactly"
    # The same bands under the Generic header must NOT silently keep the inline crossovers'
    # header: the flavour is the first line and a caller choosing wrong should see it.
    assert format_generic(eb, flavour=GENERIC).split("\n")[0] == GENERIC

    print(f"selftest OK -- byte-exact against REW's own Generic export ({len(act)} active of "
          f"{len(bands)}); precision is 2/1/3 dp here, NOT the ATF bank's 1/1/2; Compound_filters "
          f"parsed (High_pass 50 BU36, Low_pass 250 L-R12) and deliberately not written")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        print(__doc__)
