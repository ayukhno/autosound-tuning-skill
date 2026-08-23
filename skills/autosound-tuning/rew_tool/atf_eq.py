"""Audiotec-Fischer (Helix) "Full EQ (30 bands)" bank — parse AND generate.

This is the tab-separated text block REW produces with Equaliser = "Audiotec
Fischer" and that you paste/import into Helix DSP PC-Tool. Format spec +
REW→Helix workflow: references/tooling/helix-eq-export.md. Validated against a REAL
export — testdata/atf_full_eq_sample.txt (run `python3 atf_eq.py --selftest`).

Two directions:
  parse_atf_eq(text_or_path) -> list[Band]
      recover a tune's EQ bank from a copied/exported block — the black-box
      case (read an existing Helix EQ from a file when the live DSP can't be
      read; references/core/diagnostic-techniques.md §22).
  format_atf_eq(bands)       -> str
      emit the 30-band block from computed PEQ, so the tool produces the Helix
      import file itself (skip the REW round-trip).

The bank holds EQ only — crossovers / delays / polarity / phase are SEPARATE
Helix fields, never in this file (helix-eq-export.md).

stdlib-only, py3.9+.
CLI:
  python3 atf_eq.py <file>      parse a block and print its bands
  python3 atf_eq.py --selftest  round-trip the bundled real fixture
"""
from __future__ import annotations
import os
import sys
from dataclasses import dataclass

BANK_HEADER = "Audiotec_Fischer_Full_EQ_(30_bands)"
COL_HEADER = ("Number\tEnabled\tControl\tType\tFrequency(Hz)\tGain(dB)\tQ\t"
              "Bandwidth(Hz)\tTargetT60(ms)")
N_BANDS = 30
_SHELVES = ("LS_Q", "HS_Q")
_FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "testdata", "atf_full_eq_sample.txt")


@dataclass
class Band:
    number: int
    type: str = "None"          # PK | LS_Q | HS_Q | AP1 | AP2 | None
    enabled: bool = True
    control: str = "Auto"       # Auto | Manual
    freq: float | None = None
    gain: float | None = None
    q: float | None = None
    bandwidth: float | None = None   # PK only (REW writes it next to Q)

    @property
    def active(self) -> bool:
        return self.type != "None"


def _num(s):
    s = (s or "").strip()
    return float(s) if s else None


def parse_atf_eq(text_or_path) -> "list[Band]":
    """Parse an ATF bank (a file path OR raw text) into its Band rows.

    Tolerant of the real export's quirks: a UTF-8 BOM, CRLF line ends, ragged
    rows (shelves omit Bandwidth/TargetT60), and trailing empty cells.
    """
    text = text_or_path
    if "\n" not in text_or_path and os.path.isfile(text_or_path):
        with open(text_or_path, encoding="utf-8-sig") as fh:   # tolerate BOM
            text = fh.read()
    lines = [ln for ln in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
             if ln.strip() != ""]
    if not lines or BANK_HEADER not in lines[0]:
        raise ValueError("not an Audiotec-Fischer Full EQ block (header missing)")

    bands: "list[Band]" = []
    for ln in lines[1:]:
        if ln.startswith("Number\t"):       # the column header
            continue
        f = ln.split("\t")
        g = lambda i: f[i] if i < len(f) else ""   # safe ragged index
        if not g(0).strip():
            continue
        typ = g(3).strip() or "None"
        b = Band(number=int(g(0)), type=typ,
                 enabled=g(1).strip() == "True", control=g(2).strip() or "Auto")
        if typ == "PK":
            b.freq, b.gain, b.q, b.bandwidth = _num(g(4)), _num(g(5)), _num(g(6)), _num(g(7))
        elif typ in _SHELVES:
            b.freq, b.gain, b.q = _num(g(4)), _num(g(5)), _num(g(6))
        elif typ == "AP2":                  # all-pass 2nd order: freq + Q (gain col empty)
            b.freq, b.q = _num(g(4)), _num(g(6))
        elif typ == "AP1":                  # all-pass 1st order: freq only
            b.freq = _num(g(4))
        bands.append(b)
    return bands


def active_bands(bands) -> "list[Band]":
    return [b for b in bands if b.active]


def _fmt(x, nd):
    return "" if x is None else f"{x:.{nd}f}"


def bank_header(n_bands=N_BANDS):
    """The bank's first line, which NAMES ITS OWN SIZE — `Audiotec_Fischer_Full_EQ_(30_bands)`.

    Parametrised because the vendor is Audiotec-Fischer and the models are Helix, MATCH and BRAX:
    the format is the vendor's, but the band count is the MODEL's, and it is written into the
    header and into the row count. So a processor with a different bank size needs a different
    first line, not the same file with fewer rows — which is why callers pass the count from the
    DSP profile (`eq.bands_per_channel`) rather than inheriting this default.
    """
    return f"Audiotec_Fischer_Full_EQ_({n_bands}_bands)"


def format_atf_eq(bands, n_bands=N_BANDS) -> str:
    """Render bands as the ATF block ready to paste into the vendor's PC-Tool.

    Any band numbers you don't supply are emitted as empty (`None`) rows, so the output is always
    exactly `n_bands` rows — the bank is a fixed-size form, not a list. Precision matches what the
    DSP needs, not REW's byte-for-byte output (it parses by field, not by text).
    """
    by_num = {b.number: b for b in bands}
    out = [bank_header(n_bands), COL_HEADER + "\t"]   # real export has a trailing tab here
    for n in range(1, n_bands + 1):
        b = by_num.get(n)
        if b is None or b.type == "None":
            out.append(f"{n}\tTrue\tAuto\tNone\t")
            continue
        en = "True" if b.enabled else "False"
        if b.type == "PK":
            out.append(f"{n}\t{en}\t{b.control}\tPK\t{_fmt(b.freq,1)}\t"
                       f"{_fmt(b.gain,1)}\t{_fmt(b.q,2)}\t{_fmt(b.bandwidth,2)}\t")
        elif b.type in _SHELVES:
            # Trailing tab, like every other row type. Two real REW exports disagree here: the
            # bundled fixture has no trailing tab on shelf rows, the user's 2026-08-23 sample does
            # — and his is the internally consistent one, since the header, the PK rows and the
            # empty rows all end with a tab. Either parses (the trailing tab is an empty final
            # field), so this is about matching what REW writes, not about correctness. Recorded
            # rather than silently chosen; if a future export settles it the other way, that is
            # one character here and a note.
            out.append(f"{n}\t{en}\t{b.control}\t{b.type}\t{_fmt(b.freq,1)}\t"
                       f"{_fmt(b.gain,1)}\t{_fmt(b.q,1)}\t")
        elif b.type == "AP2":
            out.append(f"{n}\t{en}\t{b.control}\tAP2\t{_fmt(b.freq,1)}\t\t{_fmt(b.q,2)}")
        elif b.type == "AP1":
            out.append(f"{n}\t{en}\t{b.control}\tAP1\t{_fmt(b.freq,1)}")
        else:
            out.append(f"{n}\t{en}\t{b.control}\t{b.type}")
    return "\n".join(out) + "\n"


def _selftest():
    bands = parse_atf_eq(_FIXTURE)
    act = active_bands(bands)
    assert len(act) == 20, f"expected 20 active bands in fixture, got {len(act)}"
    assert {b.type for b in act} == {"PK", "LS_Q", "HS_Q"}, "unexpected band types"
    # semantic round-trip: parse -> format -> parse -> identical band data
    rt = active_bands(parse_atf_eq(format_atf_eq(bands)))
    key = lambda b: (b.number, b.type, b.enabled, b.control, b.freq, b.gain, b.q, b.bandwidth)
    assert [key(b) for b in act] == [key(b) for b in rt], "round-trip mismatch"

    # BYTE-exact against a reference this module did not write. The semantic round-trip above
    # cannot see a text difference — it parses our own output with our own parser, so any
    # formatting drift round-trips perfectly and reports success. That is the implementation
    # marking its own homework, and it hid a missing trailing tab on shelf rows until the user
    # pasted a real REW export on 2026-08-23.
    reference = (
        "Audiotec_Fischer_Full_EQ_(30_bands)\n"
        "Number\tEnabled\tControl\tType\tFrequency(Hz)\tGain(dB)\tQ\tBandwidth(Hz)"
        "\tTargetT60(ms)\t\n"
        "1\tTrue\tAuto\tPK\t20.0\t1.0\t2.50\t8.00\t\n"
        "2\tTrue\tManual\tLS_Q\t25.0\t-3.3\t0.7\t\n"
        "3\tTrue\tManual\tHS_Q\t31.5\t-12.0\t2.0\t\n"
        + "".join(f"{n}\tTrue\tAuto\tNone\t\n" for n in range(4, 31))
    )
    emitted = format_atf_eq(parse_atf_eq(reference))
    assert emitted == reference, (
        "emitted text differs from a real REW export:\n"
        + "\n".join(f"  line {i+1}\n    REW:  {a!r}\n    ours: {b!r}"
                    for i, (a, b) in enumerate(zip(reference.split("\n"),
                                                   emitted.split("\n"))) if a != b))

    # A bank whose size is the MODEL's, not the format's — Audiotec-Fischer is the vendor behind
    # Helix, MATCH and BRAX, and the count is written into the header as well as the row count.
    small = format_atf_eq([Band(1, "PK", freq=100.0, gain=-3.0, q=2.0, bandwidth=50.0)], 10)
    assert small.startswith("Audiotec_Fischer_Full_EQ_(10_bands)\n"), small.split("\n")[0]
    assert len(small.rstrip("\n").split("\n")) == 12, "header + columns + 10 rows"
    print(f"selftest OK — parsed {len(bands)} rows, {len(act)} active, round-trip stable")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        _selftest()
    else:
        path = sys.argv[1] if len(sys.argv) > 1 else _FIXTURE
        bands = parse_atf_eq(path)
        act = active_bands(bands)
        print(f"parsed {len(bands)} rows, {len(act)} active from {path}:")
        for b in act:
            print(f"  #{b.number:>2} {b.type:<5} {b.control:<6} "
                  f"f={b.freq}Hz g={b.gain} Q={b.q} bw={b.bandwidth}")
