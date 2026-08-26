#!/usr/bin/env python3
"""ear_suspects -- what "cuts the ear" and what "booms", found on the curve and settled by A/B.

A listener who cannot say how a system SHOULD sound can still say which of two sounds better.
This turns that into a procedure with a small number of decisions (the author's rule: not ten
rounds -- three suspects, three rounds at most):

  1. measure (MMM `L/R/ALL_N (rta)` in the car; a sweep at the desk), and the tool names the top
     THREE suspects in plain words -- "cuts: +4.5 dB at 3.2 kHz", "booms: +6 dB at 63 Hz";
  2. each gets ONE conservative correction (a cut of half its prominence, the widest Q that
     covers it, no narrower than the ceiling) into the B slot, the tune as it was in A;
  3. A/B one band at a time with the cheat-sheet phrase for that suspect (`listening.py`), and
     the answer is one of three -- better / same / worse. Better: keep (a second half next
     round); same: the band is not needed; worse: drop it and remember. Recorded through the one
     writer (`process.py listening-verdict --text "suspect:<id>=better"`), read back by `--round`.

What a suspect IS, on the curve: a peak above the local trend (a median over +-1 octave) of
at least 3 dB (4 dB in the bass), between 1/12 and 1 octave wide -- narrower is the position,
broader is tone (a shelf, not a band). Where it sits says what the ear calls it:

    cuts / harsh      2-5 kHz      the ear's most sensitive region (ISO 226)      listen: c08, c07
    sibilant          5-9 kHz      "s" and "sh"                                   c07
    nasal / pressing  0.8-2 kHz                                                   c08
    boxy              150-300 Hz                                                  c14
    booms             40-120 Hz    a cabin mode; a sweep shows it RINGING          c14, c06, c05

and the ranking weighs prominence by the ear's sensitivity at the listening level
(`equal_loudness.iso226_spl`), so a +4 dB peak at 3 kHz outranks a +4 dB hump at 60 Hz.

Taste corrections live in a separate preset (or on the virtual layer), never in the per-driver
EQ: the technical tune stays whole and "how I like it" is one action to undo (Phase 5). Not a
competition tool: for a judged tune the same loop runs with "closer to the target" and the judges'
characteristics instead of "better".

    python3 rew_tool/ear_suspects.py --rew --title "ALL_2 (rta)" [--phon 70] [--process DIR --round 2]
    python3 rew_tool/ear_suspects.py --file curve.txt
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
_STATE = os.path.join(_HERE, "state")
if _STATE not in sys.path:
    sys.path.insert(0, _STATE)

import curve_view  # noqa: E402
import equal_loudness  # noqa: E402

TREND_HALF_OCT = 1.0              # the local trend: a median over +-1 octave (a +-1/2-oct median
                                  # swallows half of a Q 3 bump -- and a Q 3 bump is what "cuts")
MIN_PROMINENCE_DB = 3.0           # what the ear notices as "sticks out"
MIN_PROMINENCE_BASS_DB = 4.0      # ...and in the bass, where the ear is less sensitive
WIDTH_OCT = (1.0 / 12.0, 1.0)     # narrower = the position; broader = tone (a shelf)
TOP_N = 3
MAX_ROUNDS = 3
Q_CEILING = 6.0
CUT_FRACTION = 0.5                # the first correction is half the prominence
PHON_DEFAULT = 70.0               # the listening level the ear-weighting is read at
CLASSES = (
    # id,        lo,    hi,     label (en),         label (uk),    listen
    ("boom",     40.0,  120.0,  "booms",            "гудить",      ["c14", "c06", "c05"]),
    ("boxy",    120.0,  300.0,  "boxy / thick",     "коробка",     ["c14"]),
    ("nasal",   800.0, 2000.0,  "nasal / pressing", "гнусавить",   ["c08"]),
    ("harsh",  2000.0, 5000.0,  "cuts / harsh",     "ріже",        ["c08", "c07"]),
    ("sibilant", 5000.0, 9000.0, "sibilant",        "сичить",      ["c07"]),
)


class SuspectError(ValueError):
    pass


# ---------------------------------------------------------------- the detector
def _grid_view(freqs, mag_db):
    view = curve_view.multiscale(np.asarray(freqs, float), np.asarray(mag_db, float),
                                 (max(20.0, float(np.min(freqs))), min(20000.0, float(np.max(freqs)))),
                                 macro_frac=3, fine_frac=12)
    return view["grid"], view["fine"]


def local_trend(g, y, half_oct=TREND_HALF_OCT):
    """A median over +-half_oct around each point: the trend a peak sticks out of."""
    out = np.empty_like(y)
    for i, fc in enumerate(g):
        m = (g >= fc / 2 ** half_oct) & (g <= fc * 2 ** half_oct)
        out[i] = np.median(y[m])
    return out


def ear_weight(f, phon=PHON_DEFAULT):
    """The ear's relative sensitivity at `f` against 1 kHz, from the ISO 226 contour at `phon`:
    a lower contour value means less SPL is needed for the same loudness -> more sensitive."""
    try:
        ref = equal_loudness.iso226_spl(phon, 1000.0)
        here = equal_loudness.iso226_spl(phon, float(np.clip(f, 20.0, 12500.0)))
    except Exception:  # noqa: BLE001 -- outside the table: no weighting rather than a crash
        return 1.0
    return float(np.clip(10.0 ** ((ref - here) / 20.0), 0.5, 1.5))


def classify(f):
    for cid, lo, hi, en, uk, listen in CLASSES:
        if lo <= f < hi:
            return {"class": cid, "label": en, "label_uk": uk, "listen": listen}
    return None


def find_suspects(freqs, mag_db, phon=PHON_DEFAULT, top=TOP_N, q_ceiling=Q_CEILING, exclude=()):
    """The top suspects on a curve: peaks above the local trend, classified, ear-weighted."""
    g, y = _grid_view(freqs, mag_db)
    trend = local_trend(g, y)
    r = y - trend
    out = []
    i = 0
    n = len(g)
    while i < n:
        if r[i] < MIN_PROMINENCE_DB:
            i += 1
            continue
        j = i
        while j + 1 < n and r[j + 1] >= MIN_PROMINENCE_DB:
            j += 1
        k = i + int(np.argmax(r[i:j + 1]))
        prom = float(r[k])
        half = prom / 2.0
        wl, wr = k, k
        while wl > 0 and r[wl - 1] >= half:
            wl -= 1
        while wr < n - 1 and r[wr + 1] >= half:
            wr += 1
        width = float(np.log2(g[wr] / g[wl]))
        fc = float(g[k])
        cls = classify(fc)
        i = j + 1
        if cls is None:
            continue
        if fc < 120.0 and prom < MIN_PROMINENCE_BASS_DB:
            continue
        if not (WIDTH_OCT[0] <= width <= WIDTH_OCT[1]):
            continue
        sid = f"{cls['class']}@{fc:.0f}"
        if sid in exclude:
            continue
        w_ear = ear_weight(fc, phon)
        q_feat = 1.0 / (2.0 ** (max(width, 1 / 24) / 2.0) - 2.0 ** (-max(width, 1 / 24) / 2.0))
        q = round(min(q_feat, q_ceiling), 2)
        out.append({"id": sid, "f_hz": round(fc, 1), "prominence_db": round(prom, 2),
                    "width_oct": round(width, 3), "ear_weight": round(w_ear, 2),
                    "score": round(prom * w_ear, 2), "band": [round(float(g[wl]), 1), round(float(g[wr]), 1)],
                    "correction": {"type": "PK", "f": round(fc, 1), "gain_db": round(-CUT_FRACTION * prom, 1), "q": q},
                    **cls})
    out.sort(key=lambda s: -s["score"])
    return out[:top]


def ringdown_ms(ir, fs, f0, band_oct=1.0 / 3.0, drop_db=20.0):
    """How long the band around f0 keeps ringing after its peak: the time the band-limited
    envelope (`analysis.etc_envelope`) takes to fall `drop_db` below its maximum. A mode rings."""
    import analysis
    x = np.asarray(ir, float)
    n = x.size
    X = np.fft.rfft(x)
    fb = np.fft.rfftfreq(n, 1.0 / fs)
    m = (fb >= f0 / 2 ** (band_oct / 2)) & (fb <= f0 * 2 ** (band_oct / 2))
    y = np.fft.irfft(np.where(m, X, 0.0), n=n)
    env = np.asarray(analysis.etc_envelope(y.tolist()), float)
    k = int(np.argmax(env))
    below = np.where(env[k:] <= env[k] * 10 ** (-drop_db / 20.0))[0]
    return float(below[0] / fs * 1000.0) if below.size else float(n - k) / fs * 1000.0


# ---------------------------------------------------------------- the loop's memory
_VERDICT_RE = re.compile(r"suspect:([a-z]+@\d+)\s*=\s*(better|same|worse)", re.I)


def verdicts_from_journal(process_dir):
    """{suspect id: latest verdict} from the listening-verdict texts (`suspect:<id>=better|same|worse`)."""
    from process import Process
    out = {}
    for e in Process(process_dir).listening_verdicts():
        for sid, v in _VERDICT_RE.findall(str(e.get("text") or "")):
            out[sid] = v.lower()
    return out


def phrases(lang=None):
    """{cid: (label, good, bad)} from the cheat sheet, in `lang` (English when missing)."""
    import listening
    try:
        c = listening.characteristics(lang)
    except Exception:  # noqa: BLE001
        c = listening.characteristics(None)
    return {cid: (v.get("label"), v.get("good"), v.get("bad")) for cid, v in c.items()}


def render(suspects, round_no=1, lang=None, verdicts=None, rings=None):
    ph = phrases(lang)
    lines = [f"  Ear suspects -- round {round_no} of {MAX_ROUNDS}: the top {len(suspects)}, one correction each, "
             f"A/B one at a time (A = as it was, B = with the band)", ""]
    if not suspects:
        lines.append("  nothing sticks out above the local trend by the ear's measure -- stop here, or listen "
                     "and say what you hear")
    for s in suspects:
        c = s["correction"]
        ring = f", rings {rings[s['id']]:.0f} ms" if rings and s["id"] in rings else ""
        lines.append(f"  [{s['id']}]  {s['label']} / {s['label_uk']}: +{s['prominence_db']:.1f} dB at {s['f_hz']:.0f} Hz "
                     f"({s['width_oct']:.2f} oct{ring}; ear weight x{s['ear_weight']:.2f})")
        lines.append(f"      try: PK {c['f']:.0f} Hz {c['gain_db']:+.1f} dB Q {c['q']:g}   (half the prominence; the widest Q that covers it)")
        for cid in s["listen"]:
            lab, good, bad = ph.get(cid, (cid, "", ""))
            lines.append(f"      listen {cid} {lab}: better = {good}  |  worse = {bad}")
        lines.append(f"      record: process.py <process-dir> listening-verdict --pair <track>:{s['listen'][0]}:ok|bad "
                     f"--text \"suspect:{s['id']}=better|same|worse\"")
        lines.append("")
    if verdicts:
        lines.append("  earlier rounds: " + ", ".join(f"{k}={v}" for k, v in sorted(verdicts.items())))
    return "\n".join(lines)


# ---------------------------------------------------------------- CLI
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--rew", action="store_true", help="read --title from REW (an MMM `(rta)` or a sweep)")
    src.add_argument("--file", metavar="TXT", help="a REW text export (freq  dB)")
    ap.add_argument("--title", default=None)
    ap.add_argument("--phon", type=float, default=PHON_DEFAULT, help="listening level for the ear weighting")
    ap.add_argument("--top", type=int, default=TOP_N)
    ap.add_argument("--q-ceiling", type=float, default=Q_CEILING)
    ap.add_argument("--process", metavar="DIR", default=None, help="the project's process dir (verdicts of earlier rounds)")
    ap.add_argument("--round", type=int, default=1)
    ap.add_argument("--lang", default=None)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        return _selftest()
    if args.round > MAX_ROUNDS:
        print(f"round {args.round}: three rounds is the limit -- keep what was better, drop the rest, and "
              f"stop; more rounds is how a tune gets over-fitted to one afternoon", file=sys.stderr)
        return 3
    if not (args.rew or args.file):
        ap.error("need --rew --title T or --file TXT")
    rings = {}
    if args.rew:
        import rew_api as api
        if not args.title:
            ap.error("--rew needs --title")
        mid = api.find_measurement_id(args.title)
        f, mag, phase = api.get_fr(mid)
        f, mag = np.asarray(f, float), np.asarray(mag, float)
        try:
            times, ir = api.get_impulse_response(mid)
        except Exception:  # noqa: BLE001 -- an RTA has none
            times, ir = None, None
    else:
        import target_curves
        f, mag = target_curves.load_target_curve(args.file)
        f, mag = np.asarray(f, float), np.asarray(mag, float)
        times, ir = None, None
    verdicts = verdicts_from_journal(args.process) if args.process else {}
    exclude = {sid for sid, v in verdicts.items() if v in ("same", "worse")}
    suspects = find_suspects(f, mag, phon=args.phon, top=args.top, q_ceiling=args.q_ceiling, exclude=exclude)
    if ir is not None and times is not None and len(times) > 1:
        fs = 1.0 / (times[1] - times[0])
        for s in suspects:
            if s["class"] in ("boom", "boxy"):
                rings[s["id"]] = ringdown_ms(ir, fs, s["f_hz"])
    if args.json:
        print(json.dumps({"round": args.round, "suspects": suspects, "rings": rings, "verdicts": verdicts}, indent=1))
    else:
        print(render(suspects, args.round, args.lang, verdicts, rings))
    return 0


# ---------------------------------------------------------------- selftest
def _selftest():
    """Anchored to construction: a curve with a boom hump at 63 Hz and a harsh peak at 3.2 kHz
    names both, classes them, cuts half, ranks the ear's region first; a narrow spike is not a
    suspect; a shelf is tone, not a suspect; earlier verdicts exclude a band; rounds are capped."""
    import dsp_math
    f = 20.0 * 2.0 ** (np.arange(int(np.log2(1000) * 48) + 1) / 48.0)
    base = -1.0 * np.log2(f / 1000.0)                               # a gentle tilt (a house curve's shape)
    H = (dsp_math.peq_response(f, "PK", 63.0, 6.0, 5.0)              # a cabin mode: booms
         * dsp_math.peq_response(f, "PK", 3200.0, 4.5, 3.0)          # cuts the ear
         * dsp_math.peq_response(f, "PK", 8000.0, 5.0, 40.0))        # a one-bin spike: the position
    mag = base + 20 * np.log10(np.abs(H))
    s = find_suspects(f, mag)
    ids = [x["id"] for x in s]
    assert any(x["class"] == "boom" and abs(x["f_hz"] - 63) < 6 for x in s), s
    assert any(x["class"] == "harsh" and abs(x["f_hz"] - 3200) < 200 for x in s), s
    assert not any(abs(x["f_hz"] - 8000) < 400 for x in s), ("a one-bin spike is not a suspect", ids)
    harsh = next(x for x in s if x["class"] == "harsh")
    boom = next(x for x in s if x["class"] == "boom")
    assert s[0]["class"] == "harsh", ("the ear's region ranks first at equal-ish prominence", ids)
    assert abs(harsh["correction"]["gain_db"] + 0.5 * harsh["prominence_db"]) < 0.15, harsh["correction"]
    assert harsh["correction"]["q"] <= Q_CEILING and boom["correction"]["q"] <= Q_CEILING
    assert harsh["listen"][0] == "c08" and boom["listen"][0] == "c14"
    # a shelf (tone) is not a suspect; nothing to do on a clean tilt
    shelf = base + 20 * np.log10(np.abs(dsp_math.peq_response(f, "HS", 2000.0, 3.0, 0.71)))
    assert not find_suspects(f, shelf), find_suspects(f, shelf)
    assert not find_suspects(f, base)
    # an earlier round said "same" to the harsh band: it is excluded and the boom leads
    s2 = find_suspects(f, mag, exclude={harsh["id"]})
    assert s2 and s2[0]["class"] == "boom" and harsh["id"] not in [x["id"] for x in s2], s2
    # ear weight: more sensitive at 3 kHz than at 63 Hz
    assert ear_weight(3000.0) > 1.0 > ear_weight(63.0), (ear_weight(3000.0), ear_weight(63.0))
    # ring-down: a mode rings longer than a broad hump of the same height
    fs, n = 48000, 1 << 15
    fb = np.fft.rfftfreq(n, 1.0 / fs)
    ir_mode = np.fft.irfft(dsp_math.peq_response(fb, "PK", 63.0, 6.0, 12.0) * np.exp(-2j * np.pi * fb * 0.01), n=n)
    ir_broad = np.fft.irfft(dsp_math.peq_response(fb, "PK", 63.0, 6.0, 1.0) * np.exp(-2j * np.pi * fb * 0.01), n=n)
    assert ringdown_ms(ir_mode, fs, 63.0) > ringdown_ms(ir_broad, fs, 63.0), \
        (ringdown_ms(ir_mode, fs, 63.0), ringdown_ms(ir_broad, fs, 63.0))
    # the journal convention parses, latest wins
    assert _VERDICT_RE.findall("A/B: suspect:harsh@3210=better, suspect:boom@63=same") == \
        [("harsh@3210", "better"), ("boom@63", "same")]
    txt = render(s, 1, "uk")
    assert "гудить" in txt and "ріже" in txt and "listening-verdict" in txt and "c14" in txt, txt
    print("selftest[ear_suspects] OK -- a 63 Hz mode and a 3.2 kHz peak are named, classed (booms / cuts), "
          "the ear's region ranks first, each gets half its prominence at a capped Q with its cheat-sheet "
          "phrase; a one-bin spike and a shelf are not suspects; an earlier 'same' excludes a band; a mode "
          "rings longer than a hump; the journal convention parses.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
