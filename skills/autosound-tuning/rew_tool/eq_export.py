"""One channel's settings, rendered for the clipboard in whatever the target DSP takes.

The caller hands over a DSP profile and a ledger channel's rows, and gets back text to paste plus
the NAME of what it produced. One function, so a window never learns a format and the method never
learns a window:

    export_eq(profile, eq_rows, crossovers=...) -> Export(text, format_name, ...)

**Why the name comes back with the text.** A clipboard whose format nobody can identify is a trap:
the person pastes it, the DSP either rejects it or -- worse -- accepts part of it, and nothing on
screen ever said what was attempted. `format_name` is part of the contract, and a UI shows it.

**Nothing is ever dropped in silence** (`references/core/estimator-scope.md` 1a). A band the format
cannot carry, or that the DSP's own profile does not declare, comes back in `left_out` with a
reason. A tuner who pastes a bank believing it holds ten bands when it holds eight has been misled
by the tool, and finds out while listening.

## Crossovers: it depends on the format, and on the tier

* **Audiotec-Fischer: never.** That bank is EQ only -- on a Helix the crossovers are separate device
  fields, not bank rows. A crossover handed to this writer is REPORTED, never smuggled in.
* **REW Generic: yes, and the flavour follows from it.** `Generic` and `Extended` are the same 20
  slots and the same 14 columns; **Extended carries crossovers inline as numbered rows** and plain
  Generic keeps them in a trailing section. So the flavour is a consequence of the content: pick
  Extended always and the block advertises a section it never fills; pick Generic always and a
  crossover has nowhere to go.
* **A tier with no crossover of its own: never, whatever the format.** Read from the profile --
  `no_crossover`, or `hp`/`lp` absent from the group's fields -- so a virtual channel gets none
  because its own profile says it has none, not because "virtual" is special-cased here. That
  distinction survives the first DSP that puts a crossover upstream. `fields: null` means NOT
  ENUMERATED and does not count as saying so.

**Where there is no vendor format, it falls back to REW's own and says which one it used.** It does
not invent a plausible vendor syntax: a guessed import file looks right and fails quietly. The
user's instruction on new formats, 2026-08-23: a missing format comes from him, not from us. What
the fallback does say is that the block is REW's neutral one and not the processor's native import,
because "it pasted" and "it was understood" are different things and only the person at the DSP can
tell them apart.

stdlib only, py3.9+.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import atf_eq
import generic_eq

#: The ledger's band vocabulary (`state/state.py`'s `EQ_TYPES`) -> the wire spelling. Both formats
#: agree today; kept as two names so a future divergence is a one-line change, not a hunt.
LEDGER_TO_ATF = {"PK": "PK", "LSH": "LS_Q", "HSH": "HS_Q", "APF1": "AP1", "APF2": "AP2"}
LEDGER_TO_GENERIC = dict(LEDGER_TO_ATF)

ATF_VENDOR = "audiotec-fischer"


@dataclass
class Export:
    """What to paste, what it is, and what did not make it."""

    text: str
    format_name: str
    #: Bands written into the text.
    written: int = 0
    #: Crossover legs written. Always 0 for Audiotec-Fischer -- that bank has no room for them.
    crossovers: int = 0
    #: The block's fixed size. A fixed-size bank is a FORM: unused rows are emitted empty and
    #: overwrite whatever those slots held before.
    bank_size: "int | None" = None
    #: `{"item": ..., "why": ...}` for everything left out. Never silent.
    left_out: list = field(default_factory=list)
    #: Things the caller should say out loud.
    notes: list = field(default_factory=list)

    @property
    def complete(self) -> bool:
        return not self.left_out


def _group(profile, group_id):
    inner = profile.get("dsp_profile", profile) if isinstance(profile, dict) else {}
    for group in inner.get("groups") or []:
        if isinstance(group, dict) and group.get("id") == group_id:
            return inner, group
    return inner, {}


def tier_has_crossover(group):
    """Does this tier have a crossover at all? Asked of the PROFILE, never inferred from the name.

    On a Helix the crossovers sit on the output stage and the virtual tier has none, so exporting
    one to a virtual channel writes a setting with nowhere to land. Hardcoding "virtual channels
    are different" would be right here and wrong on the first processor that puts a crossover
    upstream. `fields: null` is "not enumerated", which is not a claim that there is none.
    """
    if group.get("no_crossover"):
        return False
    fields = group.get("fields")
    if fields is None:
        return True
    return "hp" in fields or "lp" in fields


def export_eq(profile, eq_rows, *, crossovers=None, group_id="physical_outputs", channel=None):
    """Render one channel for the clipboard.

    `eq_rows` is the ledger's own list -- `[{"type": "PK", "f": 2551, "gain_db": -14.1, "q": 1.5}]`
    -- in ledger order, which is the order the slots are numbered in. `crossovers` is the ledger's
    `{"hp": {...}, "lp": {...}}` for that channel, or None; `null`/`"OFF"` legs are ignored.

    Dispatch is on the profile's VENDOR, because a format belongs to the vendor: one Audiotec-
    Fischer writer serves Helix, MATCH and BRAX, and what differs between their models is the bank
    SIZE, read from `eq.bands_per_channel` rather than assumed.
    """
    inner, group = _group(profile, group_id)
    eq = group.get("eq") if isinstance(group.get("eq"), dict) else None
    vendor = str(inner.get("vendor") or "").strip().lower()
    rows = list(eq_rows or [])
    legs, dropped = _legs(crossovers, group, group_id)

    if vendor == ATF_VENDOR:
        size = (eq or {}).get("bands_per_channel")
        if isinstance(size, int) and size >= 1:
            return _export_atf(inner, eq, rows, legs, dropped, size)
        dropped.append({"item": "the whole bank", "why":
                        "an Audiotec-Fischer bank writes its own size into its header and the "
                        "profile does not state `eq.bands_per_channel` -- guessing it would "
                        "produce a file that looks valid and is the wrong shape for this model"})
        return _export_generic(inner, rows, legs, dropped,
                               why="this Audiotec-Fischer profile does not state its bank size")
    return _export_generic(inner, rows, legs, dropped,
                           why=f"no writer for vendor {inner.get('vendor')!r}")


def _legs(crossovers, group, group_id):
    """The live crossover legs, or none -- with the reason when a tier cannot have them."""
    live = [(name, leg) for name, leg in sorted((crossovers or {}).items())
            if isinstance(leg, dict) and leg.get("f")]
    if not live:
        return [], []
    if not tier_has_crossover(group):
        return [], [{"item": f"{len(live)} crossover leg(s)", "why":
                     f"the {group_id!r} tier has no crossover of its own in this DSP's profile"
                     f"{' (no_crossover)' if group.get('no_crossover') else ''} -- there is "
                     f"nowhere for them to land, so they are not exported"}]
    return live, []


def _export_atf(inner, eq, rows, legs, dropped, size):
    allowed = (eq or {}).get("band_types")
    bands = []
    for row in rows:
        kind = row.get("type")
        if isinstance(allowed, list) and kind not in allowed:
            dropped.append({"item": row, "why": f"this DSP's profile does not declare a {kind!r} "
                                                f"band ({', '.join(allowed)})"})
            continue
        mapped = LEDGER_TO_ATF.get(kind)
        if mapped is None:
            dropped.append({"item": row,
                            "why": f"no Audiotec-Fischer spelling for a {kind!r} band"})
            continue
        if len(bands) >= size:
            dropped.append({"item": row, "why": f"the bank holds {size} bands and this is number "
                                                f"{len(bands) + 1}"})
            continue
        bands.append(atf_eq.Band(number=len(bands) + 1, type=mapped,
                                 enabled=not row.get("bypass", False), control="Manual",
                                 freq=row.get("f"), gain=row.get("gain_db"), q=row.get("q")))

    # NEVER, and it is the format's own limit rather than a policy of ours: the bank is EQ, and on
    # this vendor the crossovers are separate device fields. Reported so a caller can say what did
    # not travel, instead of the tuner discovering it at the DSP.
    for name, leg in legs:
        dropped.append({"item": {name: leg}, "why":
                        "the Audiotec-Fischer bank is EQ only -- this vendor's crossovers are "
                        "separate device fields and no bank row can carry them. Enter by hand."})

    notes = []
    if len(bands) < size:
        notes.append(f"{size - len(bands)} of the {size} rows are emitted EMPTY. The bank is a "
                     f"form, not a list -- pasting it CLEARS those slots, so this replaces the "
                     f"channel's bank rather than adding to it.")
    return Export(text=atf_eq.format_atf_eq(bands, size),
                  format_name=f"Audiotec-Fischer - Full EQ ({size} bands)",
                  written=len(bands), crossovers=0, bank_size=size,
                  left_out=dropped, notes=notes)


def _export_generic(inner, rows, legs, dropped, why):
    """REW's own neutral block. **Extended when there is a crossover to carry, Generic when not.**"""
    size = generic_eq.N_BANDS
    bands = []
    for row in rows:
        kind = row.get("type")
        mapped = LEDGER_TO_GENERIC.get(kind)
        if mapped is None:
            dropped.append({"item": row, "why": f"no Generic spelling for a {kind!r} band"})
            continue
        if len(bands) >= size:
            dropped.append({"item": row, "why": f"the block holds {size} slots and this is "
                                                f"number {len(bands) + 1}"})
            continue
        bands.append(generic_eq.Band(
            number=len(bands) + 1, type=mapped, enabled=not row.get("bypass", False),
            control="Manual", freq=row.get("f"), gain=row.get("gain_db"), q=row.get("q")))

    written_legs = 0
    for name, leg in legs:
        if len(bands) >= size:
            dropped.append({"item": {name: leg}, "why": f"no slot left -- the block holds {size}"})
            continue
        shape = generic_eq.SHAPES.get(leg.get("type"))
        if shape is None:
            dropped.append({"item": {name: leg}, "why":
                            f"no Generic spelling for a {leg.get('type')!r} crossover "
                            f"({', '.join(sorted(generic_eq.SHAPES))})"})
            continue
        bands.append(generic_eq.Band(
            number=len(bands) + 1, control="Manual",
            type="High_pass" if name == "hp" else "Low_pass",
            freq=leg.get("f"), shape=shape, slope=leg.get("slope")))
        written_legs += 1

    flavour = generic_eq.EXTENDED if written_legs else generic_eq.GENERIC
    notes = [f"REW's own neutral format, used because {why}. It pastes, but it is not "
             f"{inner.get('name') or 'this DSP'}'s native import -- confirm the processor accepted "
             f"it rather than assuming, since a partial success looks like a success."]
    if len(bands) < size:
        notes.append(f"{size - len(bands)} of the {size} slots are emitted EMPTY, so pasting "
                     f"REPLACES the block rather than adding to it.")
    if written_legs:
        notes.append(f"{written_legs} crossover leg(s) are in this block as inline rows -- pasting "
                     f"it changes WHAT THE DRIVER PLAYS, not only its EQ.")
    return Export(text=generic_eq.format_generic(bands, size, flavour=flavour),
                  format_name=f"REW Generic - {flavour} ({size} slots)",
                  written=len(bands) - written_legs, crossovers=written_legs, bank_size=size,
                  left_out=dropped, notes=notes)


# -- selftest ------------------------------------------------------------------
def _profile(vendor="Audiotec-Fischer", size=30, types=None, name="Helix DSP Ultra S",
             fields="default", no_crossover=False):
    group = {"id": "physical_outputs", "label": "Outputs", "max_count": 12,
             "fields": ["hp", "lp", "gain_db", "ta_ms", "polarity", "eq"]
             if fields == "default" else fields,
             "eq": {"bands_per_channel": size,
                    "band_types": types if types is not None
                    else ["PK", "LSH", "HSH", "APF1", "APF2"]}}
    if no_crossover:
        group["no_crossover"] = True
    return {"dsp_profile": {"name": name, "vendor": vendor, "sample_rate_hz": 96000,
                            "groups": [group]}}


def _selftest():
    rows = [{"type": "PK", "f": 2551, "gain_db": -14.1, "q": 1.5},
            {"type": "LSH", "f": 60, "gain_db": 2.0, "q": 0.7},
            {"type": "APF2", "f": 1200, "q": 1.7}]
    xo = {"hp": {"f": 350, "type": "LR", "slope": 24},
          "lp": {"f": 4000, "type": "BW", "slope": 36}}

    atf = export_eq(_profile(), rows, channel="m-L")
    assert atf.format_name == "Audiotec-Fischer - Full EQ (30 bands)", atf.format_name
    assert atf.written == 3 and atf.complete, atf
    assert atf.text.split("\n")[0] == "Audiotec_Fischer_Full_EQ_(30_bands)"
    # The ledger's vocabulary is not the vendor's, and an all-pass IS a bank row here.
    assert "\tLS_Q\t" in atf.text and "\tAP2\t" in atf.text, atf.text
    assert atf.text.count("\tNone\t") == 27 and any("CLEARS" in n for n in atf.notes), atf
    back = atf_eq.active_bands(atf_eq.parse_atf_eq(atf.text))
    assert [b.type for b in back] == ["PK", "LS_Q", "AP2"], [b.type for b in back]

    # ATF NEVER carries a crossover -- the bank is EQ, and this vendor keeps crossovers as separate
    # device fields. Reported, so the caller can say what did not travel.
    atf_xo = export_eq(_profile(), rows, crossovers=xo)
    assert atf_xo.crossovers == 0 and "High_pass" not in atf_xo.text, atf_xo.text[:80]
    assert len(atf_xo.left_out) == 2, atf_xo.left_out
    assert all("EQ only" in lo["why"] for lo in atf_xo.left_out), atf_xo.left_out

    # Generic: the FLAVOUR follows the content. Nothing to carry -> Generic; a crossover ->
    # Extended, because only Extended has anywhere to put one.
    plain = export_eq(_profile(vendor="Musway", name="M6V4"), rows)
    assert plain.text.split("\n")[0] == "Generic", plain.text.split("\n")[0]
    assert plain.crossovers == 0 and "Generic (20 slots)" in plain.format_name, plain.format_name

    ext = export_eq(_profile(vendor="Musway", name="M6V4"), rows, crossovers=xo)
    assert ext.text.split("\n")[0] == "Extended", ext.text.split("\n")[0]
    assert ext.crossovers == 2 and ext.written == 3, ext
    assert "\tHigh_pass\t350.00\t" in ext.text and "\tLow_pass\t4000.00\t" in ext.text, ext.text
    # Our ledger says LR/BW; this block says L-R/BU.
    assert "\tL-R\t24\t" in ext.text and "\tBU\t36\t" in ext.text, ext.text
    assert any("WHAT THE DRIVER PLAYS" in n for n in ext.notes), ext.notes
    # ...and it round-trips through the format's own reader, not through our own intent.
    rb, _ = generic_eq.parse_generic(ext.text)
    xr = [b for b in generic_eq.active_bands(rb) if b.is_crossover]
    assert [(b.type, b.freq, b.shape, b.slope) for b in xr] == [
        ("High_pass", 350.0, "L-R", 24), ("Low_pass", 4000.0, "BU", 36)], xr

    # A tier with no crossover of its own gets none -- decided by the PROFILE, so it stays right on
    # a DSP that puts a crossover somewhere we have not seen.
    virt = export_eq(_profile(vendor="Musway", no_crossover=True,
                              fields=["gain_db", "ta_ms", "eq"]), rows, crossovers=xo)
    assert virt.crossovers == 0 and virt.text.split("\n")[0] == "Generic", virt.format_name
    assert len(virt.left_out) == 1 and "nowhere for them to land" in virt.left_out[0]["why"], virt
    # `fields: null` is NOT ENUMERATED, which is not a claim that the tier has no crossover.
    unknown_tier = export_eq(_profile(vendor="Musway", fields=None), rows, crossovers=xo)
    assert unknown_tier.crossovers == 2, "unknown fields must not read as 'no crossover'"

    # A band the DSP does not declare is refused BY NAME, never quietly missing.
    narrow = export_eq(_profile(types=["PK"]), rows)
    assert narrow.written == 1 and len(narrow.left_out) == 2 and not narrow.complete
    assert any("LSH" in lo["why"] for lo in narrow.left_out), narrow.left_out
    over = export_eq(_profile(size=2), rows)
    assert over.written == 2 and "holds 2 bands" in over.left_out[0]["why"], over.left_out

    # The bank size is the MODEL's: a writer hardcoding 30 emits a header that lies.
    small = export_eq(_profile(size=10), rows)
    assert small.text.startswith("Audiotec_Fischer_Full_EQ_(10_bands)\n"), small.text[:40]
    # ...and an ATF profile that does not state it falls back rather than assuming.
    sizeless = export_eq(_profile(size=None), rows)
    assert sizeless.format_name.startswith("REW Generic"), sizeless.format_name
    assert any("bands_per_channel" in lo["why"] for lo in sizeless.left_out), sizeless.left_out

    empty = export_eq(_profile(), [])
    assert empty.written == 0 and empty.text.count("\tNone\t") == 30

    print(f"selftest OK -- ATF '{atf.format_name}' never carries a crossover (2 reported, not "
          f"smuggled); Generic flavour follows content (Generic without, Extended with, LR->L-R "
          f"BW->BU); a tier whose profile says it has no crossover gets none, `fields: null` does "
          f"not count as saying so; undeclared and overflow bands refused by name")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        print(__doc__)
