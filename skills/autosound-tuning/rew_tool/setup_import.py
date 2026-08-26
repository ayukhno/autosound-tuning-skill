#!/usr/bin/env python3
"""setup_import -- read a DSP's CURRENT setup into the ledger, and say how it was read.

The "improve an existing tune" mode (`phases/virtual-first.md`) starts by reading what is in the
processor now. On a Helix there is nothing to read from: PC-Tool 6 has no text export of a setup,
so crossovers, delays, gains and polarity are transcribed from its screens -- and only the EQ has a
machine form, the ATF bank (`atf_eq.py`). A "reader" for that processor is therefore honest only
in this shape:

    screens  ->  a transcription file  ->  VALIDATED against the DSP profile  ->  the ledger,
                                                                                   with provenance

Three things this insists on, each bought elsewhere in this repo:

  * **Provenance travels with the version.** A setup typed from screens is a claim, not a file;
    the ledger version that carries it says `transcribed`, names the source and the date, and marks
    `verified_by_file: false` -- so a later reader does not mistake a transcription for a read-back
    (the same reason `name_key`'s docstring names its consequence, 2026-08-26).
  * **Validation refuses; it never rounds.** A delay off the DSP's grid, a gain outside its range,
    an EQ type the profile does not offer -- each is a refusal naming the value. The transcription
    is wrong or the profile is wrong; silently fixing either would hide which.
  * **The EQ comes from the ATF file when there is one.** Typing 30 bands from a screen is where
    transcription fails first (the user, 2026-08-25: "EQ is the worst"); the bank REW exports and
    PC-Tool imports is exact, so `--atf CODE=file.atf` takes it from there.

Transcription file (JSON), one object per channel, fields as the ledger spells them
(`state/schema.md`); a leg is `null`/"OFF" or {f, type, slope}; `eq` is a list of
{type, f, gain_db, q}:

    {"preset": "SQ", "source": "PC-Tool 6 screens", "read_on": "2026-08-26",
     "channels": {"m-L": {"hp": {"f": 300, "type": "LR", "slope": 24}, "lp": {...},
                          "gain_db": -3, "ta_ms": 2.35, "polarity": "NORM", "eq": []}, ...}}

    python3 rew_tool/setup_import.py <project> transcription.json [--atf m-L=m-L.atf ...] [--write]
    python3 rew_tool/setup_import.py --selftest

Without `--write` it validates and prints what WOULD be banked. With it: a project whose ledger is
empty gets this as its first version; one with a history gets it as a proposal through
`apply.propose`, so every refusal that gate has still applies.
"""
from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
for _d in (_HERE, os.path.join(_HERE, "state")):
    if _d not in sys.path:
        sys.path.insert(0, _d)

import atf_eq                                   # noqa: E402
import dsp_profile                              # noqa: E402
import state as _state                          # noqa: E402
import apply as _apply                          # noqa: E402

#: ATF band types -> the ledger's (`state.EQ_TYPES`). Anything else is refused by name.
ATF_TO_LEDGER = {"PK": "PK", "LS_Q": "LSH", "HS_Q": "HSH", "AP1": "APF1", "AP2": "APF2"}


class ImportRefusal(ValueError):
    """The transcription and the DSP profile disagree; nothing was written."""


def _on_grid(value, step, eps=1e-6):
    return abs(value / step - round(value / step)) < eps


def eq_from_atf(path_or_text):
    """The ledger's band list from an ATF bank: enabled, typed bands only, mapped by name."""
    out = []
    for b in atf_eq.parse_atf_eq(path_or_text):
        if not b.active or not b.enabled:
            continue
        if b.type not in ATF_TO_LEDGER:
            raise ImportRefusal(f"ATF band {b.number}: type {b.type!r} has no ledger equivalent")
        band = {"type": ATF_TO_LEDGER[b.type], "f": float(b.freq), "gain_db": float(b.gain)}
        if b.q is not None:
            band["q"] = float(b.q)
        out.append(band)
    return out


def validate_against_profile(channels, profile):
    """Every field of every channel against the profile's declared limits. Returns the refusals.

    A returned list is a list of REASONS, one per violation, each naming channel, field and value;
    an empty list means the profile has no objection to any value -- which is not the same as the
    values being right, only that the DSP could hold them.
    """
    p = dsp_profile._unwrap(profile)
    problems = []
    delay = p.get("delay") or {}
    gain = p.get("channel_gain") or {}
    peq = p.get("parametric_eq") or {}
    phys = next((g for g in p.get("groups", []) if g.get("id") == "physical_outputs"), {}) or {}
    eq_spec = phys.get("eq") or {}
    band_types = set(eq_spec.get("band_types") or _state.EQ_TYPES)
    max_bands = eq_spec.get("bands_per_channel")

    for code, ch in channels.items():
        if not isinstance(ch, dict):
            problems.append(f"{code}: not an object")
            continue
        unknown = [k for k in ch if k not in _state.CHANNEL_FIELDS]
        if unknown:
            problems.append(f"{code}: unknown field(s) {unknown} -- the ledger spells them "
                            f"{sorted(_state.CHANNEL_FIELDS)}")
        ta = ch.get("ta_ms")
        if ta is not None:
            if ta < 0:
                problems.append(f"{code}.ta_ms = {ta}: a delay cannot be negative")
            if delay.get("max_ms") is not None and ta > delay["max_ms"]:
                problems.append(f"{code}.ta_ms = {ta} exceeds the DSP's {delay['max_ms']} ms")
            if delay.get("step_ms") and not _on_grid(ta, delay["step_ms"]):
                problems.append(f"{code}.ta_ms = {ta} is off the DSP's {delay['step_ms']} ms grid "
                                f"-- PC-Tool cannot hold it; read the screen again")
        g = ch.get("gain_db")
        if g is not None:
            rng = gain.get("range_db")
            if rng and not (rng[0] <= g <= rng[1]):
                problems.append(f"{code}.gain_db = {g} outside the DSP's {rng} dB")
            if gain.get("step_db") and not _on_grid(g, gain["step_db"]):
                problems.append(f"{code}.gain_db = {g} is off the {gain['step_db']} dB grid")
        pol = ch.get("polarity")
        if pol is not None and pol not in _state.POLARITIES:
            problems.append(f"{code}.polarity = {pol!r}: must be one of {_state.POLARITIES}")
        for leg in ("hp", "lp"):
            v = ch.get(leg)
            if v is None or v == "OFF":
                continue
            if not isinstance(v, dict) or "f" not in v:
                problems.append(f"{code}.{leg} = {v!r}: expected null/'OFF' or {{f,type,slope}}")
            elif not (isinstance(v["f"], (int, float)) and v["f"] > 0):
                problems.append(f"{code}.{leg}.f = {v.get('f')!r}: must be a positive Hz")
        eq = ch.get("eq")
        if eq is not None:
            if not isinstance(eq, list):
                problems.append(f"{code}.eq: must be a list of bands")
                continue
            if max_bands is not None and len(eq) > max_bands:
                problems.append(f"{code}.eq has {len(eq)} bands; the DSP holds {max_bands}")
            for i, b in enumerate(eq):
                t = b.get("type")
                if t not in band_types:
                    problems.append(f"{code}.eq[{i}].type = {t!r}: this DSP offers {sorted(band_types)}")
                f = b.get("f")
                fr = peq.get("freq_range_hz")
                if fr and f is not None and not (fr[0] <= f <= fr[1]):
                    problems.append(f"{code}.eq[{i}].f = {f} outside {fr} Hz")
                gb = b.get("gain_db")
                gr = peq.get("gain_range_db")
                if gr and gb is not None and not (gr[0] <= gb <= gr[1]):
                    problems.append(f"{code}.eq[{i}].gain_db = {gb} outside {gr} dB")
                q = b.get("q")
                qr = peq.get("q_range")
                if qr and q is not None and not (qr[0] <= q <= qr[1]):
                    problems.append(f"{code}.eq[{i}].q = {q} outside {qr}")
    return problems


def load_transcription(path, atf=None):
    """The transcription file, with any `--atf CODE=file` banks merged in as that channel's `eq`."""
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    if "channels" not in doc or not isinstance(doc["channels"], dict) or not doc["channels"]:
        raise ImportRefusal(f"{path}: needs a non-empty `channels` object")
    atf_used = {}
    for code, apath in (atf or {}).items():
        if code not in doc["channels"]:
            raise ImportRefusal(f"--atf {code}: no such channel in the transcription")
        doc["channels"][code]["eq"] = eq_from_atf(apath)
        atf_used[code] = os.path.basename(apath)
    doc["_atf"] = atf_used
    return doc


def provenance_of(doc):
    """What travels with the version: how it was read, from what, when, and what was NOT verified."""
    return {"kind": "transcription",
            "source": doc.get("source") or "DSP screens",
            "read_on": doc.get("read_on"),
            "verified_by_file": False,
            "eq_from_atf": sorted(doc.get("_atf", {}).keys()),
            "note": "typed from the processor's screens; a transcription is a claim, not a read-back"}


def run(project_dir, transcription_path, atf=None, write=False, preset=None, note=None):
    """Validate, then (with `write`) seed or propose. Returns {refusals, would_bank|version, provenance}."""
    prof_path = dsp_profile.profile_path(project_dir)
    if not os.path.isfile(prof_path):
        raise ImportRefusal(f"{project_dir}: no dsp_profile.json -- without the DSP's limits nothing "
                            f"here can be checked, and an unchecked transcription is not a reading")
    profile = dsp_profile.load_profile(prof_path)
    doc = load_transcription(transcription_path, atf)
    preset = preset or doc.get("preset")
    if not preset:
        raise ImportRefusal("no preset: give `preset` in the file or --preset on the command line")
    refusals = validate_against_profile(doc["channels"], profile)
    prov = provenance_of(doc)
    result = {"refusals": refusals, "preset": preset, "provenance": prov,
              "channels": sorted(doc["channels"])}
    if refusals or not write:
        return result

    root = os.path.join(project_dir, "state")
    hist = _state.PresetHistory(root, preset, project_dir=project_dir)
    rate = dsp_profile.processing_rate_hz(profile)
    try:
        hist.load()
        has_history = True
    except FileNotFoundError:
        has_history = False
    if not has_history:
        rows = {}
        for code, ch in doc["channels"].items():
            row = {"hp": ch.get("hp", "OFF"), "lp": ch.get("lp", "OFF"),
                   "gain_db": ch.get("gain_db", 0.0), "ta_ms": ch.get("ta_ms", 0.0),
                   "polarity": ch.get("polarity", "NORM"), "eq": ch.get("eq", [])}
            for k in ("mute", "off", "phase_deg", "tag"):
                if k in ch:
                    row[k] = ch[k]
            rows[code] = row
        state = {"schema_version": _state.SCHEMA_VERSION, "preset": preset, "sample_rate": rate,
                 "channels": rows, "provenance": prov}
        version = hist.snapshot(state, note=note or f"read from the DSP: {prov['source']}")
        reg = _state.Registry(root)
        if reg.get_active() is None:
            reg.set_active(preset)
        result["version"] = version
        result["mode"] = "seeded"
    else:
        res = _apply.propose(hist, {"channels": doc["channels"]},
                             note=note or f"re-read from the DSP: {prov['source']}",
                             provenance=prov, registry=_state.Registry(root))
        result["version"] = res["version"]
        result["mode"] = "proposed"
        result["diff"] = res.get("diff")
    return result


def render(result):
    lines = []
    if result["refusals"]:
        lines.append(f"REFUSED -- {len(result['refusals'])} disagreement(s) between the transcription "
                     f"and the DSP profile; nothing written:")
        lines += [f"  - {r}" for r in result["refusals"]]
        return "\n".join(lines)
    p = result["provenance"]
    head = (f"{result.get('mode', 'would bank')} {result.get('version', '')}".strip()
            + f" -- preset {result['preset']}, {len(result['channels'])} channel(s)")
    lines.append(head)
    lines.append(f"  provenance: {p['kind']} from {p['source']}"
                 + (f" on {p['read_on']}" if p.get("read_on") else "")
                 + f"; verified_by_file={p['verified_by_file']}"
                 + (f"; EQ from ATF for {', '.join(p['eq_from_atf'])}" if p["eq_from_atf"] else
                    "; EQ typed from screens (the weakest part of a transcription)"))
    if "mode" not in result:
        lines.append("  (dry run -- add --write to bank it)")
    return "\n".join(lines)


def _selftest():
    import shutil
    import tempfile

    tmp = tempfile.mkdtemp(prefix="setup_import_")
    try:
        proj = os.path.join(tmp, "proj")
        os.makedirs(os.path.join(proj, "state"))
        bundled = dsp_profile.find_bundled("Audiotec-Fischer", "Helix DSP Ultra S")
        assert bundled, "the bundled Helix profile must exist -- the selftest validates against it"
        dsp_profile.save_profile(os.path.join(proj, "dsp_profile.json"), bundled)
        with open(os.path.join(proj, "project.json"), "w") as fh:
            json.dump({"schema_version": 3, "channels": [{"code": c, "role": r, "tier": "channels"}
                                                        for c, r in (("m-L", "mid"), ("m-R", "mid"))]}, fh)

        # an ATF bank: LS_Q maps to LSH, a disabled band is dropped, a None band is dropped
        atf = atf_eq.format_atf_eq([
            atf_eq.Band(1, "PK", True, "Manual", 1000.0, -3.0, 2.0),
            atf_eq.Band(2, "LS_Q", True, "Manual", 120.0, 2.0, 0.7),
            atf_eq.Band(3, "PK", False, "Manual", 3000.0, -6.0, 4.0),
        ])
        atf_path = os.path.join(tmp, "m-L.atf")
        with open(atf_path, "w") as fh:
            fh.write(atf)
        got = eq_from_atf(atf_path)
        assert [b["type"] for b in got] == ["PK", "LSH"], got
        assert got[0]["gain_db"] == -3.0 and got[1]["f"] == 120.0, got

        good = {"preset": "SQ", "source": "PC-Tool 6 screens", "read_on": "2026-08-26",
                "channels": {"m-L": {"hp": {"f": 300, "type": "LR", "slope": 24},
                                     "lp": {"f": 3000, "type": "LR", "slope": 24},
                                     "gain_db": -3.0, "ta_ms": 2.35, "polarity": "NORM", "eq": []},
                             "m-R": {"hp": {"f": 300, "type": "LR", "slope": 24},
                                     "lp": {"f": 3000, "type": "LR", "slope": 24},
                                     "gain_db": -2.0, "ta_ms": 2.11, "polarity": "NORM", "eq": []}}}
        gpath = os.path.join(tmp, "good.json")
        with open(gpath, "w") as fh:
            json.dump(good, fh)

        # every kind of disagreement is REFUSED BY NAME, and nothing is written
        bad = json.loads(json.dumps(good))
        bad["channels"]["m-L"]["ta_ms"] = 2.355            # off the 0.01 ms grid
        bad["channels"]["m-L"]["gain_db"] = 7.0            # above +5
        bad["channels"]["m-R"]["polarity"] = "FLIP"
        bad["channels"]["m-R"]["eq"] = [{"type": "NOTCH", "f": 1000, "gain_db": -3, "q": 2},
                                        {"type": "PK", "f": 1000, "gain_db": -40, "q": 2}]
        bpath = os.path.join(tmp, "bad.json")
        with open(bpath, "w") as fh:
            json.dump(bad, fh)
        r = run(proj, bpath, write=True)
        text = "\n".join(r["refusals"])
        for needle in ("2.355", "off the DSP's 0.01 ms grid", "gain_db = 7.0", "FLIP", "NOTCH", "-40"):
            assert needle in text, (needle, text)
        assert "version" not in r, "a refused import must not write"
        assert not os.listdir(os.path.join(proj, "state")), "nothing in state/ after a refusal"

        # dry run: validates, names what it would do, writes nothing
        r = run(proj, gpath, atf={"m-L": atf_path}, write=False)
        assert not r["refusals"] and "version" not in r
        assert r["provenance"]["verified_by_file"] is False
        assert r["provenance"]["eq_from_atf"] == ["m-L"]
        assert not os.listdir(os.path.join(proj, "state"))

        # first write seeds the ledger, with provenance ON the version
        r = run(proj, gpath, atf={"m-L": atf_path}, write=True)
        assert r["mode"] == "seeded", r
        hist = _state.PresetHistory(os.path.join(proj, "state"), "SQ", project_dir=proj)
        snap = hist.load()
        assert snap["channels"]["m-L"]["eq"][0]["type"] == "PK", snap["channels"]["m-L"]["eq"]
        assert snap["channels"]["m-L"]["eq"][1]["type"] == "LSH"
        assert snap["provenance"]["kind"] == "transcription" and snap["provenance"]["verified_by_file"] is False
        assert _state.Registry(os.path.join(proj, "state")).get_active() == "SQ"

        # second write goes through apply.propose -- a proposal, not a rewrite of history
        good["channels"]["m-R"]["gain_db"] = -4.0
        with open(gpath, "w") as fh:
            json.dump(good, fh)
        r2 = run(proj, gpath, write=True)
        assert r2["mode"] == "proposed" and r2["version"] != r["version"], r2
        assert hist.load()["channels"]["m-R"]["gain_db"] == -4.0

        # no profile => nothing can be checked => refusal, not a best effort
        bare = os.path.join(tmp, "bare")
        os.makedirs(os.path.join(bare, "state"))
        try:
            run(bare, gpath, write=True)
        except ImportRefusal as exc:
            assert "dsp_profile.json" in str(exc)
        else:
            raise AssertionError("an import without a profile must refuse")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("selftest OK -- off-grid delay, out-of-range gain, bad polarity, foreign EQ type and "
          "out-of-range EQ gain are each refused by name and nothing is written; ATF LS_Q->LSH with "
          "disabled bands dropped; the first write seeds with provenance (transcription, "
          "verified_by_file=false) and the second goes through apply.propose; no profile = refusal")
    return 0


def _main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="read a DSP's current setup into the ledger, with provenance")
    ap.add_argument("project")
    ap.add_argument("transcription", help="JSON typed from the DSP's screens (see the module doc)")
    ap.add_argument("--atf", action="append", default=[], metavar="CODE=FILE",
                    help="take this channel's EQ from an ATF bank instead of the transcription")
    ap.add_argument("--preset", help="ledger preset (default: the file's `preset`)")
    ap.add_argument("--note", help="version note")
    ap.add_argument("--write", action="store_true", help="bank it; without this only validate")
    args = ap.parse_args(argv)
    atf = {}
    for item in args.atf:
        if "=" not in item:
            ap.error(f"--atf expects CODE=FILE, got {item!r}")
        code, path = item.split("=", 1)
        atf[code] = path
    try:
        r = run(args.project, args.transcription, atf=atf, write=args.write,
                preset=args.preset, note=args.note)
    except (ImportRefusal, ValueError) as exc:
        print(f"REFUSED -- {exc}", file=sys.stderr)
        return 3
    print(render(r))
    return 3 if r["refusals"] else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    sys.exit(_main())
