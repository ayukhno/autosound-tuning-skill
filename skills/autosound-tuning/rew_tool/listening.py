#!/usr/bin/env python3
"""The listening vocabulary, the track catalogue and the routes -- read from their markdown homes.

Three tables in two files, joined by ids, and this module is the only reader anything else should use:

  * `references/patterns/listening-cheat-sheet.md` -- CHARACTERISTICS (`c01`...: label, name, how it
    sounds right, how it sounds wrong, where a failed verdict goes) and ROUTES (ordered pairs of track
    and characteristic: `first` · `short` · `full` · `league`);
  * `references/patterns/test-tracks.md` -- TRACKS (id, library, number, artist, title, version) and
    LINKS (track x characteristic, with only what is specific to that track: a timecode, a cue).

Why a parser and not a JSON next to the markdown (autosound-tcc's ask, 2026-08-25): a copy drifts in
silence. The markdown is what a person reads and edits; this module is what a panel reads; when the
form of the file moves, THIS selftest fails in the skill's own suite, not a widget in a car with no
internet. The same day's other lesson is why ids are the seam and why an unknown id is an exception
and never a skipped row: a capture round keyed one way and looked up another produced a `null` that
two tools downstream read as "no filter". A blank menu entry at the wheel reads as "fine".

Translations are sibling files with the SAME ids -- `listening-cheat-sheet.uk.md`, `test-tracks.uk.md`
-- and only the free text differs. `characteristics(lang="uk")` returns the phrase in that language
where the file has it and the English one, marked `translated: False`, where it does not: the panel
must never show an empty line because a translation arrived one commit later than an id.

    characteristics(lang=None) -> {id: {id, label, name, good, bad, route, translated}}
    tracks(lang=None)          -> {id: {id, library, number, artist, title, version, translated}}
    links(lang=None)           -> [{track, characteristic, timecode, cue, translated}]
    routes()                   -> {route: [{n, track, characteristic}]}
    check(lang=None)           -> [problems]   (empty = consistent, on the REAL files)

stdlib only, py3.9+.
"""
from __future__ import annotations

import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
PATTERNS = os.path.join(_HERE, "..", "references", "patterns")
CHEAT_SHEET = "listening-cheat-sheet"
TEST_TRACKS = "test-tracks"

CHAR_COLUMNS = ("id", "label", "name", "sounds right", "sounds wrong", "where a ✗ goes")
ROUTE_COLUMNS = ("route", "#", "track", "characteristic")
TRACK_COLUMNS = ("id", "library", "number", "artist", "title", "version")
LINK_COLUMNS = ("track", "characteristic", "timecode", "cue")

_CHAR_ID = re.compile(r"^c\d{2}$")
_TIMECODE = re.compile(r"^\d{1,2}:\d{2}$")


class ListeningError(ValueError):
    """The files do not say what a reader needs -- a missing id, a moved column, an orphan."""


# ---------------------------------------------------------------- markdown tables
def _file(base, lang=None, root=None):
    root = root or PATTERNS
    name = f"{base}.{lang}.md" if lang and lang != "en" else f"{base}.md"
    return os.path.join(root, name)


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _cells(line):
    # A row is `| a | b | c |`; a cell may hold a literal pipe only if escaped, which these files do
    # not do -- so a plain split is the honest parser, and a stray pipe shows up as a column-count
    # error rather than a silently shifted cell.
    inner = line.strip()
    if inner.startswith("|"):
        inner = inner[1:]
    if inner.endswith("|"):
        inner = inner[:-1]
    return [c.strip() for c in inner.split("|")]


def _is_rule(cells):
    return all(re.fullmatch(r":?-{3,}:?", c) for c in cells)


def parse_tables(text):
    """Every pipe table in `text` -> [(header_cells, [row_cells, ...])], in document order."""
    tables, lines = [], text.splitlines()
    i = 0
    while i < len(lines):
        if lines[i].strip().startswith("|") and i + 1 < len(lines) and \
                lines[i + 1].strip().startswith("|") and _is_rule(_cells(lines[i + 1])):
            header = _cells(lines[i])
            rows = []
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(_cells(lines[i]))
                i += 1
            tables.append((header, rows))
        else:
            i += 1
    return tables


def _table(text, columns, what):
    """The one table whose header IS `columns` (order and text), rows as dicts. Refuses a missing
    table and a row with the wrong width -- a moved column must be a failure here, not a shifted
    field in a panel."""
    for header, rows in parse_tables(text):
        if tuple(header) == tuple(columns):
            out = []
            for r in rows:
                if len(r) != len(columns):
                    raise ListeningError(f"{what}: row has {len(r)} cells, expected {len(columns)}: {r!r}")
                out.append(dict(zip(columns, r)))
            return out
    raise ListeningError(f"{what}: no table with header {list(columns)} -- the file's form moved")


def _dash(v):
    return None if v in ("", "—", "-") else v


# ---------------------------------------------------------------- the four readers
def characteristics(lang=None, root=None):
    """{id: {...}} from the cheat sheet. With `lang`, the translated file's text where it has the id,
    the English text (marked `translated: False`) where it does not."""
    base = _table(_read(_file(CHEAT_SHEET, None, root)), CHAR_COLUMNS, "characteristics")
    out = {}
    for r in base:
        cid = r["id"]
        if not _CHAR_ID.match(cid):
            raise ListeningError(f"characteristics: id {cid!r} is not of the form cNN")
        if cid in out:
            raise ListeningError(f"characteristics: id {cid!r} appears twice")
        out[cid] = {"id": cid, "label": r["label"], "name": r["name"], "good": r["sounds right"],
                    "bad": r["sounds wrong"], "route": r["where a ✗ goes"], "translated": True}
    if lang and lang != "en":
        path = _file(CHEAT_SHEET, lang, root)
        have = {}
        if os.path.exists(path):
            for r in _table(_read(path), CHAR_COLUMNS, f"characteristics[{lang}]"):
                have[r["id"]] = r
        for cid, entry in out.items():
            r = have.get(cid)
            if r is None:
                entry["translated"] = False
                continue
            entry.update({"label": r["label"], "name": r["name"], "good": r["sounds right"],
                          "bad": r["sounds wrong"], "route": r["where a ✗ goes"], "translated": True})
        for cid in have:
            if cid not in out:
                raise ListeningError(f"characteristics[{lang}]: id {cid!r} exists in the translation "
                                     f"and not in the English source")
    return out


TITLE_COLUMNS = ("id", "title")


def tracks(lang=None, root=None):
    """{id: {...}}. A track's `title` is normally a proper NAME and is NOT translated (Melody Gardot
    stays Melody Gardot). But a row with no artist (`own/*`, the EMMA position/focus/moving rows) has
    a DESCRIPTION in the title slot, and a description must translate or a `uk` panel shows one English
    line among Ukrainian ones (autosound-tcc, 2026-08-25). With `lang`, the descriptive titles listed
    in `test-tracks.<lang>.md`'s "Descriptive titles" table override the English by id; a proper name,
    which the translator leaves out of that table, stays English and is marked `translated: False`."""
    rows = _table(_read(_file(TEST_TRACKS, None, root)), TRACK_COLUMNS, "tracks")
    out = {}
    for r in rows:
        tid = r["id"]
        if tid in out:
            raise ListeningError(f"tracks: id {tid!r} appears twice")
        out[tid] = {"id": tid, "library": r["library"], "number": _dash(r["number"]),
                    "artist": _dash(r["artist"]), "title": r["title"], "version": r["version"],
                    "translated": True}
    if lang and lang != "en":
        path = _file(TEST_TRACKS, lang, root)
        have = {}
        if os.path.exists(path):
            text = _read(path)
            # the descriptive-titles table is optional in a translation
            for header, trows in parse_tables(text):
                if tuple(header) == TITLE_COLUMNS:
                    for tr in trows:
                        if len(tr) != 2:
                            raise ListeningError(f"tracks[{lang}] title row: {tr!r}")
                        have[tr[0]] = tr[1]
                    break
        for tid, entry in out.items():
            t = have.get(tid)
            if t is not None:
                entry["title"] = t
            elif entry["artist"] is None:
                # a description with no translation falls back to English and SAYS so
                entry["translated"] = False
        for tid in have:
            if tid not in out:
                raise ListeningError(f"tracks[{lang}]: descriptive title for {tid!r} which is not a track")
    return out


def links(lang=None, root=None):
    """[{track, characteristic, timecode, cue, translated}] in file order. The cue is translated
    like a characteristic; the timecode is not text and comes from the English file only."""
    base = _table(_read(_file(TEST_TRACKS, None, root)), LINK_COLUMNS, "links")
    out = []
    for r in base:
        tc = _dash(r["timecode"])
        if tc is not None and not _TIMECODE.match(tc):
            raise ListeningError(f"links: timecode {tc!r} for {r['track']} x {r['characteristic']} "
                                 f"is not mm:ss")
        out.append({"track": r["track"], "characteristic": r["characteristic"], "timecode": tc,
                    "cue": r["cue"], "translated": True})
    if lang and lang != "en":
        path = _file(TEST_TRACKS, lang, root)
        have = {}
        if os.path.exists(path):
            for r in _table(_read(path), LINK_COLUMNS, f"links[{lang}]"):
                have[(r["track"], r["characteristic"])] = r["cue"]
        keys = {(l["track"], l["characteristic"]) for l in out}
        for k in have:
            if k not in keys:
                raise ListeningError(f"links[{lang}]: {k[0]} x {k[1]} exists in the translation and "
                                     f"not in the English source")
        for l in out:
            cue = have.get((l["track"], l["characteristic"]))
            if cue is None:
                l["translated"] = False
            else:
                l["cue"] = cue
    return out


def routes(root=None):
    rows = _table(_read(_file(CHEAT_SHEET, None, root)), ROUTE_COLUMNS, "routes")
    out = {}
    for r in rows:
        try:
            n = int(r["#"])
        except ValueError:
            raise ListeningError(f"routes: step number {r['#']!r} in route {r['route']!r} is not an integer")
        out.setdefault(r["route"], []).append({"n": n, "track": r["track"],
                                               "characteristic": r["characteristic"]})
    for name, steps in out.items():
        got = [s["n"] for s in steps]
        if got != list(range(1, len(steps) + 1)):
            raise ListeningError(f"routes: route {name!r} steps are {got}, expected 1..{len(steps)} in order")
    return out


# ---------------------------------------------------------------- consistency
def check(lang=None, root=None):
    """Orphans in BOTH directions, on the real files. Empty list = consistent.

    Every id a link or a route names must exist; every characteristic must be exposed by at least one
    track; every track must expose at least one characteristic; every route pair must also be a link
    (a route step without a cue is a step nobody can be told where to listen)."""
    problems = []
    try:
        ch = characteristics(lang, root)
        tr = tracks(lang, root)
        ln = links(lang, root)
        rt = routes(root)
    except (ListeningError, OSError) as e:
        return [str(e)]
    pairs = set()
    for l in ln:
        if l["characteristic"] not in ch:
            problems.append(f"link {l['track']} x {l['characteristic']}: unknown characteristic")
        if l["track"] not in tr:
            problems.append(f"link {l['track']} x {l['characteristic']}: unknown track")
        key = (l["track"], l["characteristic"])
        if key in pairs:
            problems.append(f"link {key[0]} x {key[1]} appears twice")
        pairs.add(key)
    exposed = {c for _, c in pairs}
    for cid in ch:
        if cid not in exposed:
            problems.append(f"characteristic {cid} is exposed by no track")
    linked = {t for t, _ in pairs}
    for tid in tr:
        if tid not in linked:
            problems.append(f"track {tid} exposes no characteristic")
    for name, steps in rt.items():
        for s in steps:
            if s["track"] not in tr:
                problems.append(f"route {name} #{s['n']}: unknown track {s['track']}")
            if s["characteristic"] not in ch:
                problems.append(f"route {name} #{s['n']}: unknown characteristic {s['characteristic']}")
            elif (s["track"], s["characteristic"]) not in pairs:
                problems.append(f"route {name} #{s['n']}: {s['track']} x {s['characteristic']} has no link row")
    return problems


def languages(root=None):
    """The translation languages present on disk (files `listening-cheat-sheet.<lang>.md`)."""
    root = root or PATTERNS
    out = []
    for name in sorted(os.listdir(root)):
        m = re.fullmatch(re.escape(CHEAT_SHEET) + r"\.([a-z]{2})\.md", name)
        if m:
            out.append(m.group(1))
    return out


# ---------------------------------------------------------------- selftest
def _selftest():
    import tempfile
    # 1. On the REAL files: every reader answers, and nothing is an orphan, in English and in every
    #    translation on disk. This is the check that fails the suite when the two files part ways.
    ch, tr, ln, rt = characteristics(), tracks(), links(), routes()
    assert len(ch) >= 13 and "c01" in ch and ch["c01"]["good"] and ch["c01"]["bad"], ch.get("c01")
    assert ch["c01"]["good"] != ch["c01"]["bad"]
    assert "mono/merrill" in tr and tr["mono/merrill"]["artist"] == "Helen Merrill"
    # a descriptive (artist-less) title translates; a proper name does not (autosound-tcc, 2026-08-25)
    assert tr["own/favourite"]["artist"] is None, tr["own/favourite"]
    tr_uk = tracks("uk")
    if "own/favourite" in tr_uk and tr_uk["own/favourite"]["translated"]:
        assert tr_uk["own/favourite"]["title"] != tr["own/favourite"]["title"], "own title must translate in uk"
    assert tracks("uk")["mono/merrill"]["title"] == "You\u0027d Be So Nice to Come Home To", "a proper name is not translated"
    assert tr["CarMus#01"]["library"] == "CarMus" and tr["CarMus#01"]["number"] == "01"
    assert any(l["track"] == "CarMus#07" and l["timecode"] == "2:00" for l in ln), \
        "the whisper at 2:00 must be a timecode on the link, not prose on the track"
    assert set(rt) >= {"first", "short", "full"}, list(rt)
    assert rt["first"][0]["track"] == "own/favourite" and rt["first"][1]["characteristic"] == "c01"
    problems = check()
    assert not problems, "\n".join(problems)
    for lang in languages():
        problems = check(lang)
        assert not problems, f"[{lang}]\n" + "\n".join(problems)
        chl = characteristics(lang)
        assert all(chl[c]["good"] for c in chl), lang
    # No "sounds right / wrong" phrase may live in a link cue: the cheat sheet is the ONE home.
    bank = {ch[c]["good"].lower() for c in ch} | {ch[c]["bad"].lower() for c in ch}
    for l in ln:
        assert l["cue"].lower() not in bank, f"link {l['track']} x {l['characteristic']} repeats a phrase"

    # 2. On a fixture: the parser refuses what a panel must never receive quietly.
    with tempfile.TemporaryDirectory() as d:
        def write(name, body):
            with open(os.path.join(d, name), "w", encoding="utf-8") as fh:
                fh.write(body)
        cs = ("| id | label | name | sounds right | sounds wrong | where a ✗ goes |\n|---|---|---|---|---|---|\n"
              "| c01 | centre | Mono centre | tight | smeared | 1.3 |\n"
              "| c02 | depth | Depth | deep | flat | 1.3 |\n\n"
              "| route | # | track | characteristic |\n|---|---|---|---|\n"
              "| short | 1 | T1 | c01 |\n")
        tt = ("| id | library | number | artist | title | version |\n|---|---|---|---|---|---|\n"
              "| T1 | mono | — | A | B | v |\n| T2 | mono | — | A | C | v |\n\n"
              "| track | characteristic | timecode | cue |\n|---|---|---|---|\n"
              "| T1 | c01 | — | one point |\n| T2 | c02 | 1:05 | behind |\n")
        write("listening-cheat-sheet.md", cs)
        write("test-tracks.md", tt)
        assert check(root=d) == [], check(root=d)
        # a translation: one id translated, the other falls back to English and SAYS so
        write("listening-cheat-sheet.uk.md",
              "| id | label | name | sounds right | sounds wrong | where a ✗ goes |\n|---|---|---|---|---|---|\n"
              "| c01 | центр | Моно-центр | точка | розмазано | 1.3 |\n")
        uk = characteristics("uk", root=d)
        assert uk["c01"]["good"] == "точка" and uk["c01"]["translated"] is True
        assert uk["c02"]["good"] == "deep" and uk["c02"]["translated"] is False
        # descriptive titles: own-style rows translate by id; a proper name and an untranslated
        # description stay English, the latter flagged; an id not a track is refused.
        # T1 artist-less WITH a translation; T2 artist-less WITHOUT one; a named row is untouched.
        tt2 = (tt.replace("| T1 | mono | — | A | B | v |", "| T1 | mono | — | — | play your own favourite | v |")
                 .replace("| T2 | mono | — | A | C | v |", "| T2 | mono | — | — | a familiar album | v |"))
        write("test-tracks.md", tt2)
        write("test-tracks.uk.md",
              "| track | characteristic | timecode | cue |\n|---|---|---|---|\n| T1 | c01 | — | твоя точка |\n\n"
              "| id | title |\n|---|---|\n| T1 | грай свій улюблений |\n")
        t_uk = tracks("uk", root=d)
        assert t_uk["T1"]["title"] == "грай свій улюблений" and t_uk["T1"]["translated"] is True
        assert t_uk["T2"]["title"] == "a familiar album" and t_uk["T2"]["translated"] is False
        write("test-tracks.uk.md",
              "| id | title |\n|---|---|\n| T9 | привид |\n")
        try:
            tracks("uk", root=d)
            raise AssertionError("a descriptive title for a non-track was accepted")
        except ListeningError:
            pass
        os.remove(os.path.join(d, "test-tracks.uk.md"))
        write("test-tracks.md", tt)
        assert check("uk", root=d) == []
        # an id only in the translation is refused, not merged
        write("listening-cheat-sheet.uk.md",
              "| id | label | name | sounds right | sounds wrong | where a ✗ goes |\n|---|---|---|---|---|---|\n"
              "| c09 | x | X | a | b | 1.3 |\n")
        try:
            characteristics("uk", root=d)
            raise AssertionError("an id present only in a translation was accepted")
        except ListeningError:
            pass
        os.remove(os.path.join(d, "listening-cheat-sheet.uk.md"))
        # orphans in both directions are NAMED, not skipped
        write("test-tracks.md", tt.replace("| T2 | c02 | 1:05 | behind |", "| T2 | c07 | 1:05 | behind |"))
        p = check(root=d)
        assert any("unknown characteristic" in x for x in p) and any("c02 is exposed by no track" in x for x in p), p
        write("test-tracks.md", tt.replace("| T2 | c02 | 1:05 | behind |\n", ""))
        p = check(root=d)
        assert any("T2 exposes no characteristic" in x for x in p), p
        write("test-tracks.md", tt)
        write("listening-cheat-sheet.md", cs + "| short | 2 | T2 | c01 |\n")
        p = check(root=d)
        assert any("has no link row" in x for x in p), p
        # a moved column is a failure at the parser, not a shifted field
        write("listening-cheat-sheet.md", cs.replace("| id | label | name |", "| id | name | label |"))
        try:
            characteristics(root=d)
            raise AssertionError("a moved column was read as if nothing happened")
        except ListeningError:
            pass
        write("listening-cheat-sheet.md", cs)
        write("test-tracks.md", tt.replace("| 1:05 |", "| 1m05 |"))
        try:
            links(root=d)
            raise AssertionError("a timecode that is not mm:ss was accepted")
        except ListeningError:
            pass
    print(f"selftest[listening] OK -- {len(ch)} characteristics, {len(tr)} tracks, {len(ln)} links, "
          f"routes {sorted(rt)}, translations {languages() or 'none'}; no orphans either way; the "
          f"cheat sheet is the one home of every sounds-right/wrong phrase; a moved column, a bad "
          f"timecode and an id only in a translation are refused")
    return 0


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("what", nargs="?", choices=["characteristics", "tracks", "links", "routes", "check"],
                    default="check")
    ap.add_argument("--lang", default=None, help="translation to read (en = the source)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        return _selftest()
    if args.what == "check":
        problems = check(args.lang)
        for p in problems:
            print("  " + p)
        print("consistent" if not problems else f"{len(problems)} problem(s)")
        return 1 if problems else 0
    data = {"characteristics": lambda: characteristics(args.lang), "tracks": lambda: tracks(args.lang),
            "links": lambda: links(args.lang), "routes": routes}[args.what]()
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=1))
    elif isinstance(data, dict):
        for k, v in data.items():
            print(k, "->", v)
    else:
        for row in data:
            print(row)
    return 0


if __name__ == "__main__":
    sys.exit(main())
