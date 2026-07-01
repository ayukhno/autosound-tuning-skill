"""Audiotec-Fischer (Helix) "Full EQ (30 bands)" bank — parse AND generate.

This is the tab-separated text block REW produces with Equaliser = "Audiotec
Fischer" and that you paste/import into Helix DSP PC-Tool. Format spec +
REW→Helix workflow: references/tooling/helix-eq-export.md. Validated against a REAL
export — testdata/atf_full_eq_sample.txt (run `python atf_eq.py --selftest`).

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
  python atf_eq.py <file>      parse a block and print its bands
  python atf_eq.py --selftest  round-trip the bundled real fixture
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


def format_atf_eq(bands) -> str:
    """Render bands as the 30-row ATF block ready to paste into Helix PC-Tool.

    Any band numbers you don't supply are emitted as empty (`None`) rows, so
    the output is always exactly 30 bands. Precision matches what Helix needs,
    not REW's byte-for-byte output (Helix parses by field, not by text).
    """
    by_num = {b.number: b for b in bands}
    out = [BANK_HEADER, COL_HEADER + "\t"]   # real export has a trailing tab here
    for n in range(1, N_BANDS + 1):
        b = by_num.get(n)
        if b is None or b.type == "None":
            out.append(f"{n}\tTrue\tAuto\tNone\t")
            continue
        en = "True" if b.enabled else "False"
        if b.type == "PK":
            out.append(f"{n}\t{en}\t{b.control}\tPK\t{_fmt(b.freq,1)}\t"
                       f"{_fmt(b.gain,1)}\t{_fmt(b.q,2)}\t{_fmt(b.bandwidth,2)}\t")
        elif b.type in _SHELVES:
            out.append(f"{n}\t{en}\t{b.control}\t{b.type}\t{_fmt(b.freq,1)}\t"
                       f"{_fmt(b.gain,1)}\t{_fmt(b.q,1)}")
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
