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

#: The formats this library can WRITE, as a caller-visible list. A GUI or an agent picks one by
#: name; `None` means "decide from the profile's vendor", which is the normal case.
#:
#: Deliberately a registry rather than a chain of `if vendor ==`: a format we do not have is not a
#: gap to be filled by guessing at a vendor's syntax, it is one the tuner will hand us
#: (user, 2026-08-23) -- and when he does, it lands here beside the others instead of inside the
#: dispatch. `register_format` is how it gets added mid-session without editing this file.
FORMATS = {
    "atf": "Audiotec-Fischer Full EQ (Helix / MATCH / BRAX) -- EQ only, size from the profile",
    "generic": "REW Generic -- 20 slots, neutral, crossovers in a separate section (not written)",
    "extended": "REW Generic/Extended -- 20 slots, crossovers INLINE, whole channel in one paste",
}

#: The DEFAULT when a DSP has no writer of its own (user, 2026-08-23: "беремо Generic"). Extended
#: is used in its place only when there is a crossover to carry, because plain Generic has nowhere
#: to put one -- and the swap is reported in `notes` rather than done quietly.
DEFAULT_FORMAT = "generic"

_EXTRA_WRITERS = {}


def register_format(name, writer, description=""):
    """Add a format at runtime -- for one the tuner supplies during a session.

    `writer(inner, rows, legs, dropped, why) -> Export`. Registering is how a real vendor format
    reaches us: this module will not invent one, because a guessed import syntax produces a file
    that looks right and fails quietly.
    """
    _EXTRA_WRITERS[name] = writer
    FORMATS[name] = description or f"supplied at runtime ({name})"
    return name


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


def export_eq(profile, eq_rows, *, crossovers=None, fmt=None, group_id="physical_outputs",
              channel=None):
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

    # An explicit `fmt` wins over the vendor. A person who picked a format in a dropdown has said
    # something the profile cannot contradict -- they may be pasting into something else entirely.
    if fmt is not None:
        if fmt in _EXTRA_WRITERS:
            return _EXTRA_WRITERS[fmt](inner, rows, legs, dropped, f"caller asked for {fmt!r}")
        if fmt == "atf":
            size = (eq or {}).get("bands_per_channel") or atf_eq.N_BANDS
            return _export_atf(inner, eq, rows, legs, dropped, size)
        if fmt in ("generic", "extended"):
            return _export_generic(inner, rows, legs, dropped, why=f"caller asked for {fmt!r}",
                                   flavour=(generic_eq.EXTENDED if fmt == "extended"
                                            else generic_eq.GENERIC))
        raise ValueError(f"unknown format {fmt!r} -- have {', '.join(sorted(FORMATS))}. A format "
                         f"we do not hold is one to be supplied (`register_format`), never guessed")

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


def _export_generic(inner, rows, legs, dropped, why, flavour=None):
    """REW's own neutral block.

    The default is plain **Generic**. Extended is substituted only when there is a crossover to
    carry, because Generic has literally nowhere to put one -- and the substitution is reported,
    not done quietly. An explicit `flavour` from the caller wins over both.
    """
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

    swapped = flavour is None and written_legs
    if flavour is None:
        flavour = generic_eq.EXTENDED if written_legs else generic_eq.GENERIC
    if flavour == generic_eq.GENERIC and written_legs:
        # Asked for plain Generic with crossovers in hand: they cannot go inline, and this writer
        # does not emit the trailing section, so they do not travel. Said out loud.
        for b in [b for b in bands if b.is_crossover]:
            dropped.append({"item": {"crossover": b.type, "f": b.freq}, "why":
                            "plain Generic keeps crossovers in a Compound_filters section this "
                            "writer does not emit -- ask for 'extended' to carry them inline"})
        bands = [b for b in bands if not b.is_crossover]
        written_legs = 0
    notes = [f"REW's own neutral format, used because {why}. It pastes, but it is not "
             f"{inner.get('name') or 'this DSP'}'s native import -- confirm the processor accepted "
             f"it rather than assuming, since a partial success looks like a success."]
    if len(bands) < size:
        notes.append(f"{size - len(bands)} of the {size} slots are emitted EMPTY, so pasting "
                     f"REPLACES the block rather than adding to it.")
    if swapped:
        notes.append(f"Flavour switched from the default {generic_eq.GENERIC} to "
                     f"{generic_eq.EXTENDED}: plain Generic has nowhere to put a crossover.")
    if written_legs:
        notes.append(f"{written_legs} crossover leg(s) are in this block as inline rows -- pasting "
                     f"it changes WHAT THE DRIVER PLAYS, not only its EQ.")
    return Export(text=generic_eq.format_generic(bands, size, flavour=flavour),
                  format_name=f"REW Generic - {flavour} ({size} slots)",
                  written=len(bands) - written_legs, crossovers=written_legs, bank_size=size,
                  left_out=dropped, notes=notes)


# -- import: the other direction ------------------------------------------------
#: Wire spelling -> the ledger's vocabulary. The inverse of `LEDGER_TO_ATF`, written out rather
#: than inverted at import time so an asymmetry (a wire type we read but never write, or the
#: reverse) is visible here instead of implied.
WIRE_TO_LEDGER = {"PK": "PK", "LS_Q": "LSH", "HS_Q": "HSH", "AP1": "APF1", "AP2": "APF2"}
#: Crossover family, wire -> ledger. `BU` is Butterworth, `L-R` Linkwitz-Riley.
WIRE_TO_XO = {v: k for k, v in generic_eq.SHAPES.items()}


@dataclass
class Imported:
    """What a pasted block turned out to hold."""

    #: Ledger-shaped EQ rows, ready for a channel's `eq`.
    eq: list = field(default_factory=list)
    #: Ledger-shaped `{"hp": {...}, "lp": {...}}`, only for legs the block actually carried.
    crossovers: dict = field(default_factory=dict)
    format_name: str = ""
    #: `{"item": ..., "why": ...}` -- rows understood but NOT returned, e.g. crossovers for a tier
    #: that has none. Never silent.
    ignored: list = field(default_factory=list)
    notes: list = field(default_factory=list)


def sniff(text):
    """Which format a pasted block is, from its first line. `None` when nothing recognises it."""
    first = (text or "").lstrip().split("\n", 1)[0].strip()
    if first.startswith("Audiotec_Fischer_Full_EQ_"):
        return "atf"
    if first == generic_eq.EXTENDED:
        return "extended"
    if first == generic_eq.GENERIC:
        return "generic"
    return None


def import_eq(text, profile=None, *, fmt=None, group_id="physical_outputs"):
    """Read a pasted block into ledger rows. The mirror of `export_eq`, and a separate call.

    Two directions rather than one function with a flag, because they answer different questions
    and fail differently: an export asks "what does this DSP take?", an import asks "what is this
    text?" — and the second has to cope with a block somebody pasted from anywhere.

    `fmt` forces the reader; by default the block's own first line decides (`sniff`). `profile` is
    optional and used for one thing only: deciding whether crossovers in the block belong to this
    tier at all. Without it they are returned, because refusing to hand back something the text
    plainly contains would be the tool overruling the person who pasted it.
    """
    kind = fmt or sniff(text)
    if kind is None:
        raise ValueError(
            "unrecognised block: the first line is neither an Audiotec-Fischer bank header nor "
            f"{generic_eq.GENERIC!r}/{generic_eq.EXTENDED!r}. Pass `fmt=` if you know what it is; "
            "guessing at a layout would read numbers out of the wrong columns")

    ignored, notes = [], []
    if kind == "atf":
        bands = atf_eq.active_bands(atf_eq.parse_atf_eq(text))
        raw_xo = []
        name = "Audiotec-Fischer Full EQ"
    else:
        parsed, compounds = generic_eq.parse_generic(text)
        bands = [b for b in generic_eq.active_bands(parsed) if not b.is_crossover]
        raw_xo = [(b.type, b.freq, b.shape, b.slope)
                  for b in generic_eq.active_bands(parsed) if b.is_crossover]
        raw_xo += [(c.kind, c.freq, c.shape, c.slope) for c in compounds]
        name = f"REW Generic/{generic_eq.EXTENDED if kind == 'extended' else generic_eq.GENERIC}"

    eq = []
    for b in bands:
        mapped = WIRE_TO_LEDGER.get(b.type)
        if mapped is None:
            ignored.append({"item": b, "why": f"no ledger band type for {b.type!r}"})
            continue
        row = {"type": mapped, "f": b.freq, "i": b.number}
        if b.gain is not None:
            row["gain_db"] = b.gain
        if b.q is not None:
            row["q"] = b.q
        if not b.enabled:
            row["bypass"] = True
        eq.append(row)

    crossovers = {}
    if raw_xo:
        group = _group(profile, group_id)[1] if profile is not None else None
        if group is not None and not tier_has_crossover(group):
            ignored.append({"item": f"{len(raw_xo)} crossover leg(s)", "why":
                            f"the {group_id!r} tier has no crossover in this DSP's profile — "
                            f"read from the block, but there is nowhere to put them"})
        else:
            for kind_, freq, shape, slope in raw_xo:
                leg = "hp" if kind_ == "High_pass" else "lp"
                mapped = WIRE_TO_XO.get(shape)
                if mapped is None:
                    ignored.append({"item": {leg: (freq, shape, slope)}, "why":
                                    f"no ledger crossover type for shape {shape!r}"})
                    continue
                crossovers[leg] = {"f": freq, "type": mapped, "slope": slope}
            if crossovers:
                notes.append("This block sets crossovers as well as EQ. Applying it changes WHAT "
                             "THE DRIVER PLAYS — confirm before writing it to the channel.")
    return Imported(eq=eq, crossovers=crossovers, format_name=name, ignored=ignored, notes=notes)


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
    return {"dsp_profile": {"name": name, "vendor": vendor, "dsp_processing_rate_hz": 96000,
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

    # -- the format is a PARAMETER, and the default is Generic ------------------
    forced = export_eq(_profile(), rows, fmt="extended", crossovers=xo)
    assert forced.text.split("\n")[0] == "Extended" and forced.crossovers == 2, forced.format_name
    # Plain Generic asked for WITH crossovers in hand does not smuggle them in and does not
    # silently upgrade: it drops them and names the flavour that would carry them.
    forced_plain = export_eq(_profile(vendor="Musway"), rows, fmt="generic", crossovers=xo)
    assert forced_plain.text.split("\n")[0] == "Generic" and forced_plain.crossovers == 0
    assert any("'extended'" in lo["why"] for lo in forced_plain.left_out), forced_plain.left_out
    try:
        export_eq(_profile(), rows, fmt="nosuch")
    except ValueError as exc:
        assert "never guessed" in str(exc), exc
    else:
        raise AssertionError("an unknown format must be refused")
    register_format("dummy", lambda inner, r, l, d, why: Export("X", "dummy"), "test")
    assert export_eq(_profile(), rows, fmt="dummy").text == "X" and "dummy" in FORMATS

    # -- import: the mirror, and a real round-trip ------------------------------
    assert sniff(atf.text) == "atf" and sniff(ext.text) == "extended"
    assert sniff(plain.text) == "generic" and sniff("nonsense") is None
    try:
        import_eq("nonsense")
    except ValueError as exc:
        assert "guessing at a layout" in str(exc), exc
    else:
        raise AssertionError("an unrecognised block must be refused, not guessed at")

    # What went out must come back: ledger -> wire -> ledger, through the format's own reader.
    trip = import_eq(ext.text)
    assert [(r["type"], r["f"], r.get("gain_db"), r.get("q")) for r in trip.eq] == [
        ("PK", 2551.0, -14.1, 1.5), ("LSH", 60.0, 2.0, 0.7), ("APF2", 1200.0, None, 1.7)], trip.eq
    assert trip.crossovers == {"hp": {"f": 350.0, "type": "LR", "slope": 24},
                               "lp": {"f": 4000.0, "type": "BW", "slope": 36}}, trip.crossovers
    assert any("WHAT THE DRIVER PLAYS" in n for n in trip.notes), trip.notes
    atf_trip = import_eq(atf.text)
    assert [r["type"] for r in atf_trip.eq] == ["PK", "LSH", "APF2"], atf_trip.eq
    assert not atf_trip.crossovers, "an ATF bank has none to give"

    byp = export_eq(_profile(), [{"type": "PK", "f": 100, "gain_db": -3, "q": 2, "bypass": True}])
    assert import_eq(byp.text).eq[0]["bypass"] is True, import_eq(byp.text).eq

    # On import, a tier with no crossover of its own has the block's legs READ and then set aside
    # -- reported, not returned into a field that does not exist.
    novirt = import_eq(ext.text, _profile(vendor="Musway", no_crossover=True,
                                          fields=["gain_db", "eq"]))
    assert not novirt.crossovers and len(novirt.ignored) == 1, novirt
    assert "nowhere to put them" in novirt.ignored[0]["why"], novirt.ignored

    print(f"selftest OK -- import and export both ways, round-trip exact; ATF '{atf.format_name}' never carries a crossover (2 reported, not "
          f"smuggled); Generic flavour follows content (Generic without, Extended with, LR->L-R "
          f"BW->BU); a tier whose profile says it has no crossover gets none, `fields: null` does "
          f"not count as saying so; undeclared and overflow bands refused by name")


_USAGE = """usage: eq_export.py <project-dir> <channel> [--preset P] [--version v_NNN] [--fmt NAME] [--out FILE]

  One channel's EQ (and crossover legs where the format carries them) from the project's ledger,
  rendered in the format the project's DSP profile takes -- what Phase 2.3 hands the tuner to
  import. Prints the text, then the format's name and everything LEFT OUT, on stderr; --out writes
  the text to a file. Default preset: the registry's active slot; default version: HEAD.
"""


def _main(argv):
    args = list(argv[1:])
    if len(args) < 2 or args[0] in ("-h", "--help"):
        print(_USAGE, file=sys.stderr)
        return 2

    def _flag(name):
        if name in args:
            i = args.index(name)
            v = args[i + 1]
            del args[i:i + 2]
            return v
        return None
    preset, version, fmt, out_path = _flag("--preset"), _flag("--version"), _flag("--fmt"), _flag("--out")
    project_dir, channel = args[0], args[1]
    state_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state")
    if state_dir not in sys.path:
        sys.path.insert(0, state_dir)
    import dsp_profile as _dp
    import state as _st
    profile = _dp.load_profile(os.path.join(project_dir, "dsp_profile.json"))
    root = os.path.join(project_dir, "state")
    if preset is None:
        preset = _st.Registry(root).get_active()
        if not preset:
            print(f"no active slot in {root}/registry; pass --preset", file=sys.stderr)
            return 1
    snap = _st.PresetHistory(root, preset, project_dir=project_dir).load(version)
    row = (snap.get("channels") or {}).get(channel)
    if row is None:
        print(f"{channel!r} is not a row of {preset} {snap.get('version') or 'HEAD'} -- rows: "
              + ", ".join(sorted(snap.get("channels") or {})), file=sys.stderr)
        return 1
    ex = export_eq(profile, row.get("eq") or [], crossovers={"hp": row.get("hp"), "lp": row.get("lp")},
                   fmt=fmt, channel=channel)
    if out_path:
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(ex.text)
        print(f"wrote {out_path}", file=sys.stderr)
    else:
        print(ex.text)
    print(f"format: {ex.format_name} -- {ex.written} band(s)"
          + (f", {ex.crossovers} crossover leg(s)" if ex.crossovers else "")
          + (f", bank of {ex.bank_size}" if ex.bank_size else "")
          + f"; {preset} {snap.get('version') or 'HEAD'} {channel}", file=sys.stderr)
    for item in ex.left_out:
        print(f"LEFT OUT: {item.get('item')} -- {item.get('why')}", file=sys.stderr)
    for note in ex.notes:
        print(f"note: {note}", file=sys.stderr)
    return 0 if ex.complete else 3


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        sys.exit(_main(sys.argv))
