"""variant_front -- Phase 1's variants as a TRADE-OFF FRONT, not a winner (skill #38, W-2 package V).

A tune is not a sum of locally optimal junctions. On the Passat the two sides wanted opposite
mid/tweeter corners (left best at 2800, right at 1800), the m/tw junction never did better than
-1.6 dB anywhere in its range, and the largest defect of the predicted sum -- an L-R imbalance of
+7.9 dB over 250-500 Hz -- was invisible to every junction metric. So each candidate configuration
is broken down by the SAME terms, and 2-3 are picked by DIFFERENT weightings of them:

    tonal      how far the predicted ALL sum is from the target curve (shape only, level removed)
    stage      L-R balance per band (the log-weighted mean of |L-R| over the bands `predict` reads)
    junctions  the mean sum loss after delay (level-normalised: phase agreement), with each
               junction's LEVEL STEP beside it (#50) -- the loss is blind to a 6 dB step
    ripple     the mean ripple of the junction sums (not normalised)

**It never hands over an argmax** (`predict.ladder_report`'s rule: a table ordered by the metric is
a proposal wearing a table's clothes). Each pick says which weighting it wins under, what it BUYS
and what it SPENDS against the others, and every output ends with what the objective cannot see.
The desk proposes; the tuner chooses (the Arbiter's В8).
"""

from __future__ import annotations

import math

TERMS = ("tonal", "stage", "junctions", "ripple")

#: Three weightings, one per thing a tuner may want first. The numbers only decide which candidate
#: wins under each; they are not shown as a score, and a tuner who wants other weights passes them.
WEIGHTINGS = {
    "tone first": {"tonal": 1.0, "stage": 0.3, "junctions": 0.3, "ripple": 0.3},
    "stage first": {"tonal": 0.3, "stage": 1.0, "junctions": 0.3, "ripple": 0.3},
    "junctions first": {"tonal": 0.3, "stage": 0.3, "junctions": 1.0, "ripple": 1.0},
}

#: A spread across the candidates smaller than this is a TIE on that term, not a trade: 0.03 dB of junction loss
#: read as "buys the best junctions" would be the precision of the arithmetic sold as a property of the car.
TIE_DB = {"tonal": 0.1, "stage": 0.2, "junctions": 0.05, "ripple": 0.1}

#: A junction whose sum loss is worse than this in EVERY candidate is not a choice any of them makes.
LIMITED_JUNCTION_DB = -1.5

CANNOT_SEE = ("The objective has no term for imaging, depth or fatigue at volume: an optimiser will "
              "buy 0.3 dB of junction with something it cannot measure. Phases 4 and 5 judge those, "
              "by ear.")

TONAL_BAND_HZ = (40.0, 16000.0)


def _log_weights(f):
    """Weights that give each octave the same say (a log-spaced grid already does; a linear one does not)."""
    out = []
    for i, x in enumerate(f):
        lo = f[i - 1] if i else x
        hi = f[i + 1] if i + 1 < len(f) else x
        out.append(max(math.log(hi / lo) if lo > 0 and hi > 0 else 0.0, 1e-9))
    return out


def tonal_distance_db(freqs, all_db, target):
    """RMS (dB) of the predicted ALL sum against the target over 40 Hz-16 kHz, the level removed.

    `target` is `[(hz, db), ...]`, interpolated on log frequency. The target is a SHAPE, not a level
    (`naming-and-structure.md` §6), so the mean difference is taken out before the RMS. None when
    the target or the band is missing -- a tonal term read from nothing would still rank."""
    if not target:
        return None
    pts = sorted((float(h), float(d)) for h, d in target if float(h) > 0)
    if len(pts) < 2:
        return None

    def at(hz):
        if hz <= pts[0][0]:
            return pts[0][1]
        if hz >= pts[-1][0]:
            return pts[-1][1]
        lo = max(i for i, (h, _) in enumerate(pts) if h <= hz)
        (h0, d0), (h1, d1) = pts[lo], pts[lo + 1]
        t = (math.log(hz) - math.log(h0)) / (math.log(h1) - math.log(h0))
        return d0 + t * (d1 - d0)

    band = [(f, d) for f, d in zip(freqs, all_db) if TONAL_BAND_HZ[0] <= f <= TONAL_BAND_HZ[1]]
    if len(band) < 3:
        return None
    fs = [f for f, _ in band]
    diff = [d - at(f) for f, d in band]
    w = _log_weights(fs)
    mean = sum(wi * di for wi, di in zip(w, diff)) / sum(w)
    return math.sqrt(sum(wi * (di - mean) ** 2 for wi, di in zip(w, diff)) / sum(w))


def _band_level(freqs, mag_db, lo, hi):
    """Energy-average level (dB) inside [lo, hi], or None."""
    pwr = [10.0 ** (d / 10.0) for f, d in zip(freqs, mag_db) if lo <= f <= hi]
    return 10.0 * math.log10(sum(pwr) / len(pwr)) if pwr else None


def level_step_db(freqs, lo_db, hi_db, fc):
    """The lower member's plateau minus the upper's, each read an octave into its own band (#50)."""
    a = _band_level(freqs, lo_db, fc / 4.0, fc / 1.5)
    b = _band_level(freqs, hi_db, fc * 1.5, fc * 4.0)
    return None if a is None or b is None else round(a - b, 2)


def terms(pred, target=None):
    """The four terms of ONE candidate, from `predict.to_json`'s shape (or `predict.predict`'s, converted).

    `pred` needs `freqs_hz`, `all_mag_db`, `lr_delta`, `junctions`, and `channels` (`{code: {mag_db}}`)
    for the level steps. A missing piece gives that term None, named, never a zero."""
    freqs = [float(x) for x in pred.get("freqs_hz") or []]
    out = {"tonal": tonal_distance_db(freqs, pred.get("all_mag_db") or [], target) if freqs else None}
    lr = pred.get("lr_delta") or []
    if lr:
        w = [math.log(b["band"][1] / b["band"][0]) for b in lr]
        out["stage"] = sum(wi * abs(b["delta_db"]) for wi, b in zip(w, lr)) / sum(w)
        worst = max(lr, key=lambda b: abs(b["delta_db"]))
        out["stage_worst"] = {"band_hz": worst["band"], "delta_db": round(worst["delta_db"], 1)}
    else:
        out["stage"] = None
    js = pred.get("junctions") or []
    losses = [j["sum_loss_avg_db"] for j in js if j.get("sum_loss_avg_db") is not None]
    ripples = [j["sum_ripple_db"] for j in js if j.get("sum_ripple_db") is not None]
    out["junctions"] = sum(losses) / len(losses) if losses else None
    out["ripple"] = sum(ripples) / len(ripples) if ripples else None
    chans = pred.get("channels") or {}
    per = []
    for j in js:
        lo, hi = chans.get(j.get("lo")) or {}, chans.get(j.get("hi")) or {}
        step = (level_step_db(freqs, lo["mag_db"], hi["mag_db"], j["fc"])
                if freqs and lo.get("mag_db") and hi.get("mag_db") and j.get("fc") else None)
        per.append({"lo": j.get("lo"), "hi": j.get("hi"), "fc": j.get("fc"),
                    "loss_db": j.get("sum_loss_avg_db"), "level_step_db": step})
    out["per_junction"] = per
    return out


def _cost(name, value):
    """Lower is better for every term: the loss is negative dB, so its cost is its size."""
    if value is None:
        return None
    return -value if name == "junctions" else value


def front(candidates, weightings=None):
    """`candidates`: `[{"name", "terms"}]`. Returns `{"picks": [...], "limited": [...], "missing": [...]}`.

    Each term is scaled across the candidates (0 = the best of them, 1 = the worst); a candidate's
    cost under a weighting is the weighted sum. Under each weighting the cheapest wins, and the
    winners, deduplicated, are the front (2-3 when the candidates differ; one when a single one wins
    everywhere, which is said). A term no candidate has is dropped and named."""
    weightings = weightings or WEIGHTINGS
    names = [c["name"] for c in candidates]
    usable = [t for t in TERMS if all(_cost(t, c["terms"].get(t)) is not None for c in candidates)]
    missing = [t for t in TERMS if t not in usable]
    scaled, ties = {}, []
    for t in usable:
        vals = [_cost(t, c["terms"][t]) for c in candidates]
        lo, hi = min(vals), max(vals)
        if hi - lo < TIE_DB[t]:
            ties.append(t)
            scaled[t] = [0.0] * len(vals)
        else:
            scaled[t] = [(v - lo) / (hi - lo) for v in vals]
    traded = [t for t in usable if t not in ties]
    wins = {}
    for label, w in weightings.items():
        cost = [sum(w.get(t, 0.0) * scaled[t][i] for t in usable) for i in range(len(candidates))]
        best = min(range(len(candidates)), key=lambda i: (cost[i], i))
        wins.setdefault(best, []).append(label)
    picks = []
    for i in sorted(wins):
        buys = [t for t in traded if scaled[t][i] == 0.0 and len(candidates) > 1]
        spends = [t for t in traded if scaled[t][i] == 1.0 and len(candidates) > 1]
        picks.append({"name": names[i], "wins_under": wins[i], "buys": buys, "spends": spends,
                      "terms": candidates[i]["terms"]})
    limited = []
    per = [c["terms"].get("per_junction") or [] for c in candidates]
    if per and per[0]:
        for k, j in enumerate(per[0]):
            losses = [p[k]["loss_db"] for p in per if k < len(p) and p[k].get("loss_db") is not None]
            if losses and len(losses) == len(per) and max(losses) < LIMITED_JUNCTION_DB:
                limited.append({"lo": j["lo"], "hi": j["hi"], "best_loss_db": round(max(losses), 2)})
    if not traded and len(picks) > 1:
        # Every term ties: the weightings chose by index, which is no choice at all. One pick, said so.
        picks = picks[:1]
        picks[0]["wins_under"] = list(weightings)
    return {"picks": picks, "limited": limited, "missing": missing, "ties": ties, "candidates": names}


def _fmt(v, spec="+.2f"):
    return "--" if v is None else format(v, spec)


def render(result):
    """The front as a table and three kinds of sentence: what each buys and spends, what no candidate
    repairs, and what the objective cannot see. In the candidates' own order, never sorted by a score."""
    lines = ["  VARIANTS AS A TRADE-OFF FRONT -- the same four terms for each, picked by different "
             "weightings (#38); no winner is chosen here",
             f"  {'variant':22}{'tonal rms':>10}{'stage |L-R|':>13}{'junction loss':>15}{'ripple':>8}  wins under"]
    for p in result["picks"]:
        t = p["terms"]
        lines.append(f"  {p['name'][:22]:22}{_fmt(t.get('tonal'), '.2f'):>10}{_fmt(t.get('stage'), '.2f'):>13}"
                     f"{_fmt(t.get('junctions')):>15}{_fmt(t.get('ripple'), '.2f'):>8}  {', '.join(p['wins_under'])}")
    lines.append("  (dB; tonal = RMS against the target, level removed, 40 Hz-16 kHz; stage = log-weighted mean "
                 "|L-R| over the bands; junction loss = mean sum loss after delay, level-normalised; "
                 "ripple = mean junction ripple)")
    if len(result["picks"]) == 1:
        lines.append(f"  one candidate wins under every weighting: {result['picks'][0]['name']}. "
                     "The others trade nothing it does not already have.")
    for p in result["picks"]:
        say = []
        if p["buys"]:
            say.append("buys the best " + ", ".join(p["buys"]))
        if p["spends"]:
            say.append("spends the worst " + ", ".join(p["spends"]))
        worst = p["terms"].get("stage_worst")
        if worst:
            say.append(f"its largest L-R is {worst['delta_db']:+.1f} dB at {worst['band_hz'][0]:g}-"
                       f"{worst['band_hz'][1]:g} Hz")
        steps = [f"{j['lo']}↔{j['hi']} {j['level_step_db']:+.1f}" for j in p["terms"].get("per_junction") or []
                 if j.get("level_step_db") is not None and abs(j["level_step_db"]) >= 1.0]
        if steps:
            say.append("level steps " + ", ".join(steps) + " dB")
        lines.append(f"  {p['name']}: " + ("; ".join(say) if say else "in the middle on every term"))
    for j in result["limited"]:
        lines.append(f"  none of these repairs {j['lo']} ↔ {j['hi']}: its sum loss stays at or below "
                     f"{j['best_loss_db']:+.2f} dB in every candidate -- the junction is the ceiling, not the choice")
    if result.get("ties"):
        lines.append("  a tie, not a trade, on " + ", ".join(result["ties"]) + ": the candidates differ by less than "
                     + ", ".join(f"{TIE_DB[t]:g} dB" for t in result["ties"]) + " there")
        if len(result["ties"]) == len([t for t in TERMS if t not in result["missing"]]):
            lines.append("  on these terms one candidate is as good as another: the difference, if any, is for the ear")
    if result["missing"]:
        lines.append("  not scored: " + ", ".join(result["missing"])
                     + (" (no target curve given)" if "tonal" in result["missing"] else ""))
    lines.append(f"  {CANNOT_SEE}")
    lines.append("  The tuner chooses; nothing is entered without the tuner's OK.")
    return "\n".join(lines)


def read_target(path):
    """A REW-style text curve: `hz db` per line, `*`/`#` comments skipped."""
    pts = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            parts = line.replace(",", " ").split()
            if len(parts) < 2 or parts[0].startswith(("*", "#")):
                continue
            try:
                pts.append((float(parts[0]), float(parts[1])))
            except ValueError:
                continue
    return pts


def _selftest():
    freqs = [20.0 * 2 ** (i / 12.0) for i in range(120)]
    target = [(20.0, 6.0), (100.0, 3.0), (1000.0, 0.0), (20000.0, -4.0)]

    def pred(tilt, lr_mid, loss_mt, step_db=0.0):
        all_db = [80.0 + (3.0 - 3.0 * math.log10(f / 20.0)) * tilt for f in freqs]
        chans = {"m-L": {"mag_db": [80.0 + step_db] * len(freqs)}, "tw-L": {"mag_db": [80.0] * len(freqs)}}
        return {"freqs_hz": freqs, "all_mag_db": all_db, "channels": chans,
                "lr_delta": [{"band": [60, 250], "delta_db": 0.5}, {"band": [250, 500], "delta_db": lr_mid},
                             {"band": [500, 1000], "delta_db": 1.0}],
                "junctions": [{"lo": "m-L", "hi": "tw-L", "fc": 2800.0, "sum_loss_avg_db": loss_mt,
                               "sum_ripple_db": 2.0}]}

    cands = [{"name": "A (the engine's best)", "terms": terms(pred(1.0, 7.9, -1.6, 6.0), target)},
             {"name": "B (1800 Hz)", "terms": terms(pred(1.0, 2.0, -2.1), target)},
             {"name": "C (flatter)", "terms": terms(pred(0.2, 5.0, -1.9), target)}]
    assert cands[0]["terms"]["per_junction"][0]["level_step_db"] == 6.0, cands[0]["terms"]["per_junction"]
    res = front(cands)
    names = [p["name"] for p in res["picks"]]
    assert names == [c["name"] for c in cands if c["name"] in names], "picks must keep the candidates' order"
    assert len(res["picks"]) >= 2, res
    assert any("stage first" in p["wins_under"] and p["name"].startswith("B") for p in res["picks"]), res
    assert res["limited"] == [{"lo": "m-L", "hi": "tw-L", "best_loss_db": -1.6}], res["limited"]
    shown = render(res)
    assert "none of these repairs m-L ↔ tw-L" in shown and CANNOT_SEE in shown and "level steps m-L↔tw-L +6.0" in shown
    no_target = front([{"name": c["name"], "terms": terms(pred(1.0, 2.0, -1.0), None)} for c in cands[:2]])
    assert no_target["missing"] == ["tonal"] and "no target curve given" in render(no_target), no_target
    print("selftest[variant_front] OK -- four terms per candidate (tonal against the target with the level removed, "
          "|L-R| per band, the level-normalised junction loss with each junction's level step, ripple); the front "
          "picks by three weightings in the candidates' own order, says what each buys and spends, names a junction "
          "no candidate repairs, drops a term nobody has and says so, and always ends with what it cannot see")
    return 0


if __name__ == "__main__":
    import sys
    import console                       # issue #21: a code page must not destroy a result
    console.install()
    if len(sys.argv) > 1 and sys.argv[1] in ("--selftest", "selftest"):
        raise SystemExit(_selftest())
    print(__doc__)
