"""Per-band target curves: the one file name, the title that asks for one, and the reader.

A per-band target is a file per CODE -- `w-L_target.txt`, `c_target.txt` -- written by
`target_bands.write_targets` and read here, both through `target_file_name`. Which code a REW title
asks for is the grammar's answer (`naming.explain_name`) checked against the project glossary,
never a guess: a title the glossary does not know gets NO target and a reason, because a wrong
target reads as a driver that needs 8 dB of EQ (#56 items 4 and 5).

Run `python3 target_curves.py selftest`.
"""
import glob
import os

import naming

#: What follows the code in a per-band target's file name. Read it through `target_file_name`.
TARGET_SUFFIX = "_target.txt"


def load_target_curve(filepath):
    freqs, mags = [], []
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) >= 2:
                try:
                    freqs.append(float(parts[0]))
                    mags.append(float(parts[1]))
                except ValueError:
                    continue
    return freqs, mags


def target_file_name(code):
    """`<code>_target.txt` -- the ONE spelling of a per-band target's file name (#56 item 4).

    `target_bands.write_targets` names its files through this, and `find_target_curve` looks them
    up through it. Until 2026-09-23 each side had its own: the writer emitted `<name>_target.txt`
    and the reader globbed `*_<fragment>*_REW.txt`, the Nono Tuning Tool's export spelling. Both
    were reasonable alone; together no file the writer could produce matched the reader's pattern,
    and `analyze-batch "_51 (rta)"` reported "no per-band target" for all 19 measurements of a
    series. The writer's spelling was kept, so every file it has already written is read as it
    stands.

    The code must be one the grammar reads back as ITSELF. A file named for `w_L` would never be
    found -- no title can carry that code since S-042 -- and one named for `m-L p1` would be read
    as `m-L` at a position, so both are refused here, on the writer's side, before anything is on
    disk, with the grammar's own reason."""
    text = str(code or "").strip()
    if not text:
        raise ValueError("a per-band target is filed under a code, and this one is empty")
    parsed, why = naming.explain_name(naming.generate_name(text, 1, naming.METHOD_SWEEP))
    if parsed is None or parsed["code"] != text:
        why = why or f"a title with it reads back as `{parsed['code']}`"
        raise ValueError(f"`{text}` cannot name a per-band target, since no measurement title "
                         f"resolves to it: {why}")
    return text + TARGET_SUFFIX


def _glossary_codes(glossary):
    """Every code the project glossary holds today -- channels, pairs, combos, joints, sides."""
    if glossary is None:
        return set()
    return (set(glossary.channel_codes()) | set(glossary.pairs) | set(glossary.combos)
            | set(glossary.joints) | set(glossary.sides))


def explain_channel(measurement_title, glossary=None):
    """`(code, None)` -- the code a title's per-band target is filed under -- or `(None, reason)`.

    The title is read by the grammar's one reader (`naming.explain_name`) with the project glossary
    (`naming.Glossary.for_project`), and the code is the channel's name TODAY (`code_current`,
    SCR-039): a capture taken before a rename is scored against the channel it belongs to.

    This used to be a substring map from a legacy per-band name set (`w_60`, `m_250`, `tw`, `sw`),
    and it was wrong three times, each time without a word in any output:

      * REW titles every sweep `<ch>_<ver> (sw)`. A substring search over the whole title found
        `sw` inside `(sw)`, so EVERY swept measurement -- woofer, mid, tweeter -- was handed the
        SUBWOOFER's target curve.
      * `tw` contains `w`, and `w-` came first in the map, so a tweeter matched the woofer's key.
        (Both found 2026-09-07 while writing this module's first selftest, HUB-037.)
      * On a real project (#56 item 5): `w-L` and `w-R` both came out `w_60`, the side lost and
        with it the L/R gain difference `target_bands` bakes in; `c`, `L`, `R` and `ALL` found
        nothing; and the joint `L m+tw` came out `w_60` -- a mid+tweeter sum scored against a
        MIDBASS target.

    A map of fragments cannot know a project's codes; its glossary does. So there is no map. A code
    the glossary does not hold is refused rather than matched to the nearest fragment, and a joint,
    pair, side or combo is its OWN code: it has a target when one was written for exactly that
    code, and otherwise none. Without a glossary the code is the title's as typed -- `parse_name`'s
    own answer -- which can only ever find a file written for exactly that code."""
    parsed, why = naming.explain_name(measurement_title, glossary)
    if parsed is None:
        return None, f"not a measurement title: {why}"
    code = parsed.get("code_current") or parsed["code"]
    known = _glossary_codes(glossary)
    if known and code not in known:
        return None, (f"`{code}` is not a code in this project's glossary, and no target is "
                      f"guessed for a code nobody agreed")
    return code, None


def channel_of(measurement_title, glossary=None):
    """The code a title's per-band target is filed under, or None -- `explain_channel` says why."""
    return explain_channel(measurement_title, glossary)[0]


def explain_target_curve(measurement_title, curves_dir, glossary=None):
    """`(path, (freqs, mags), None)`, or `(None, None, reason)` saying why there is no target.

    The reason is for the places a person reads the verdict (`rew_tool.py analyze-batch`): a bare
    "no target" is how 19 measurements went unscored while the table looked like a project with no
    targets rather than a reader looking for the wrong file names (#56 item 4)."""
    code, why = explain_channel(measurement_title, glossary)
    if code is None:
        return None, None, why
    try:
        name = target_file_name(code)
    except ValueError as exc:            # a glossary code no title reads back: no file can be it
        return None, None, str(exc)
    path = os.path.join(curves_dir, name)
    if not os.path.isfile(path):
        why = f"no `{name}` in {curves_dir}"
        if glob.glob(os.path.join(glob.escape(curves_dir), "*_REW.txt")):
            # The retired spelling is still on disk in real projects (an NTT export directory is
            # the CLI's default). Saying so turns a table of blanks into one step to take.
            why += ("; its `*_REW.txt` files are in the retired spelling (`w_60`, `m_250`: no "
                    "side, their own crossovers) and are not read -- `target_bands.write_targets` "
                    "writes this project's")
        return None, None, why
    return path, load_target_curve(path), None


def find_target_curve(measurement_title, curves_dir, glossary=None):
    """`(path, (freqs, mags))`, or `(None, None)` -- `explain_target_curve` says why not."""
    path, data, _ = explain_target_curve(measurement_title, curves_dir, glossary)
    return path, data


def interpolate_target(target_freqs, target_mags, query_freqs):
    """Linear interpolation of target curve at query frequencies."""
    result = []
    for f in query_freqs:
        if f <= target_freqs[0]:
            result.append(target_mags[0])
            continue
        if f >= target_freqs[-1]:
            result.append(target_mags[-1])
            continue
        for i in range(len(target_freqs) - 1):
            if target_freqs[i] <= f <= target_freqs[i + 1]:
                t = (f - target_freqs[i]) / (target_freqs[i + 1] - target_freqs[i])
                result.append(target_mags[i] + t * (target_mags[i + 1] - target_mags[i]))
                break
    return result


def _selftest():
    """The mapping, the file name and the interpolation, offline. First written for HUB-037.

    It was written to close a coverage gap and found two live bugs on the first run -- both in
    `channel_of`, both invisible in the tool's output. The third shape of the same bug came from a
    real car (#56 item 5); every case below that used to be wrong says so."""
    import tempfile

    # The reporting car's own glossary (#56), as its project.json holds it.
    car = naming.Glossary({
        "channels": [{"code": c} for c in ("tw-L", "tw-R", "m-L", "m-R", "w-L", "w-R", "c", "sw",
                                           "r-L", "r-R")],
        "pairs": {"Ms": ["m-L", "m-R"], "TWs": ["tw-L", "tw-R"], "Ws": ["w-L", "w-R"]},
        "joints": {"L m+tw": ["m-L", "tw-L"], "L w+m": ["w-L", "m-L"], "R m+tw": ["m-R", "tw-R"],
                   "R w+m": ["w-R", "m-R"], "SW+Ws": ["sw", "w-L", "w-R"]},
        "sides": {"L": ["tw-L", "m-L", "w-L"], "R": ["tw-R", "m-R", "w-R"]},
        "combos": {"ALL": ["tw-L", "tw-R", "m-L", "m-R", "w-L", "w-R", "sw"],
                   "ALL+C": ["tw-L", "tw-R", "m-L", "m-R", "w-L", "w-R", "sw", "c"]},
    })

    # ── the two bugs this selftest was born finding (HUB-037) ────────────────────────────────
    # RED before 2026-09-07: every one of these returned "sw", because REW titles sweeps `(sw)`.
    for title, code in (("m-L_2 (sw)", "m-L"), ("w-L_2 (sw)", "w-L"), ("tw-L_2 (sw)", "tw-L"),
                        # RED before 2026-09-07: "w-" came first in the map and `tw` contains `w`.
                        ("tw-R_2 (rta)", "tw-R"),
                        # still right, and the reason the first bug survived: the sub agrees.
                        ("sw_1 (sw)", "sw")):
        assert channel_of(title, car) == code, (title, channel_of(title, car))
        assert channel_of(title) == code, (title, channel_of(title))   # no glossary: as typed

    # ── #56 item 5: the codes of a real project. Each was RED on the fragment map ─────────────
    # `w-L` and `w-R` both became `w_60`: the side, and its gain, lost.
    assert channel_of("w-L_51 (rta)", car) == "w-L" and channel_of("w-R_51 (rta)", car) == "w-R"
    # `c`, the sides and the combo found nothing, though each is a code the project agreed.
    for title, code in (("c_51 (rta)", "c"), ("L_51 (rta)", "L"), ("R_51 (rta)", "R"),
                        ("ALL_51 (rta)", "ALL"), ("ALL+C_51 (rta)", "ALL+C")):
        assert channel_of(title, car) == code, (title, channel_of(title, car))
    # The worst one: the joint `L m+tw` became `w_60`, a mid+tweeter sum against a MIDBASS target.
    assert channel_of("L m+tw_50 (sw)", car) == "L m+tw", channel_of("L m+tw_50 (sw)", car)
    # A modifier (`c FX`, the virtual centre ON) is still the channel; the modifier is not a code.
    assert channel_of("c FX_51 (rta)", car) == "c", channel_of("c FX_51 (rta)", car)
    # A code the glossary does not hold is refused with a reason -- no nearest fragment. The old
    # contained-match fallback turned `front-m-L` into a mid; the glossary has no such code.
    for title in ("xyz_1 (sw)", "front-m-L_2 (sw)"):
        code, why = explain_channel(title, car)
        assert code is None and "not a code in this project's glossary" in why, (title, why)
    # The grammar refuses `w_L` since S-042, and says the hyphen form; that is the reason here.
    code, why = explain_channel("w_L_1 (sw)", car)
    assert code is None and "`w-L`" in why, why
    assert channel_of("Room sim") is None
    # SCR-039: a capture taken under a retired name is scored against the channel it belongs to.
    renamed = naming.Glossary({"channels": [{"code": "w-L", "previous_names": ["m-L"]}]})
    assert channel_of("m-L_2 (sw)", renamed) == "w-L", channel_of("m-L_2 (sw)", renamed)

    # ── #56 item 4: one spelling, and a code the grammar would not read back is refused ───────
    assert target_file_name("w-L") == "w-L_target.txt"
    assert target_file_name("L m+tw") == "L m+tw_target.txt"
    for bad, words in (("w_L", "`w-L`"), ("m-L p1", "`m-L`"), ("", "empty")):
        try:
            target_file_name(bad)
        except ValueError as exc:
            assert words in str(exc), (bad, exc)
            continue
        raise AssertionError(f"target_file_name took {bad!r}")

    # ── the file reader: comments, blanks and junk rows are skipped, not crashed on ──────────
    with tempfile.TemporaryDirectory() as d:
        # Written by hand in the pre-2026-09-23 writer's spelling: a file already on disk is read.
        path = os.path.join(d, "m-L_target.txt")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("# a comment\n\n20 6.0\n1000 0.0\nnot a row\n20000 -3.0 extra-column\n")
        freqs, mags = load_target_curve(path)
        assert freqs == [20.0, 1000.0, 20000.0], freqs
        assert mags == [6.0, 0.0, -3.0], mags
        found, data = find_target_curve("m-L_2 (sw)", d, car)
        assert found == path and data == (freqs, mags), (found, data)

        # The same title once picked the SUBWOOFER's file; both exist here, so this asserts the
        # choice rather than the absence of an alternative. A retired-spelling export sits beside
        # them and is NOT read, for any title.
        for name in ("sw_target.txt", "house_m_250_REW.txt", "house_w_60_REW.txt"):
            with open(os.path.join(d, name), "w", encoding="utf-8") as fh:
                fh.write("20 10.0\n80 0.0\n")
        assert find_target_curve("m-L_2 (sw)", d, car)[0] == path
        assert find_target_curve("sw_2 (sw)", d, car)[0] == os.path.join(d, "sw_target.txt")
        # `w-L` has a `*_w_60*_REW.txt` next to it that the old reader took; now it has none, and
        # the reason names the retired files rather than leaving a blank to puzzle over.
        got, data, why = explain_target_curve("w-L_51 (rta)", d, car)
        assert got is None and data is None and "`w-L_target.txt`" in why and "retired" in why, why
        # The joint finds no target, and above all not the mid's that sits right there.
        got, _, why = explain_target_curve("L m+tw_50 (sw)", d, car)
        assert got is None and "`L m+tw_target.txt`" in why, why
        assert find_target_curve("xyz_1 (sw)", d, car) == (None, None)

    # ── interpolation: inside, on the knots, and clamped outside ─────────────────────────────
    tf, tm = [100.0, 200.0, 400.0], [0.0, 10.0, 0.0]
    got = interpolate_target(tf, tm, [50.0, 100.0, 150.0, 200.0, 300.0, 400.0, 800.0])
    assert got == [0.0, 0.0, 5.0, 10.0, 5.0, 0.0, 0.0], got

    print("selftest OK — a title resolves through the grammar and the glossary to its own code "
          "(a sweep is not 'sw', a tweeter not a woofer, w-L/w-R keep their side, c/L/R/ALL "
          "resolve, the joint L m+tw is not scored against a midbass target, an unknown code is "
          "refused with a reason); one file name <code>_target.txt for writer and reader, the "
          "retired *_REW.txt spelling named and not read; the reader skips comments, blanks and "
          "junk rows; interpolation is linear inside and clamped outside.")


if __name__ == "__main__":
    import sys
    import console                       # issue #21: a code page must not destroy a result
    console.install()
    if len(sys.argv) > 1 and sys.argv[1] in ("selftest", "--selftest"):
        _selftest()
    else:
        print(__doc__ or "target_curves.py — run `target_curves.py selftest`")
