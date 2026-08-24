#!/usr/bin/env python3
"""Predicted against measured, on the same terms -- the model-trust metric of the virtual-first path.

(Not `verify.py`: that module is the post-sweep capture gate, `capture-check`. This one verifies a
PREDICTION, and the two questions must not share a name.)

`predict.py` says what the microphone would hear; this asks whether it did. The delta between the
two is the number the whole path rests on: while it stays inside its criterion the desk design is
believed, and where it does not, the report names the junction or the channel so the tuner knows
what to look at -- it never adjusts anything to make the delta smaller.

Three comparisons, each chosen so that what is compared does not depend on things nobody knows:

  * **The interference term at each junction** -- the measured PAIR (`sw+w-L_N (sw)`) minus the
    phase-blind power sum of the two measured solos, against the same term predicted. Level
    cancels out of it: SPL calibration, the sub knob, a mic-gain difference all move solos and
    pair together. What is left is delay, polarity and crossover phase -- the part a desk design
    actually decides. This is stage 0's "heart" (2026-08-21: 0.3-0.45 dB in band means), and the
    criterion is its: **|mean delta| <= 1 dB in every junction band**.
  * **Each channel's processed shape** -- the measured solo with the tune loaded against the
    predicted (solo x chain), after ONE level offset per channel. The offset itself is reported:
    it is a calibration fact (SPL reference, knob position), not an error.
  * **The whole front** -- `ALL_N` against the predicted ALL, after one offset, as a shape.

⚠️ **Same base or no comparison.** The prediction is a POINT -- the tripod position the solos were
taken from. A moving-microphone (MMM/RTA) measurement fills the interference nulls a point shows
(set-02: +27 dB at 165 Hz on w-L, exactly the null the point predicts), so an RTA cannot verify a
point prediction and is refused as a pair unless `--allow-rta` is given, and then every row built
on it says `rta` in its base column. Verification sums are point sweeps from the tripod.

Reports, never repairs. A junction outside its criterion is a finding about the model -- a wrong
chain fact, a moved driver, a protective filter nobody recorded -- and which of those is the
tuner's to find.
"""
import argparse
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dsp_math  # noqa: E402

CRITERION_DB = 1.0            # |mean delta| in a junction band, stage 0's pass mark
JUNCTION_THIRDS = 3           # each junction band is read in this many log-spaced sub-bands


class VerifyError(ValueError):
    pass


def _db(h):
    return 20.0 * np.log10(np.maximum(np.abs(h), 1e-12))


def _psum_db(a_db, b_db):
    return 10.0 * np.log10(10 ** (np.asarray(a_db) / 10.0) + 10 ** (np.asarray(b_db) / 10.0))


def _complex(mag_db, phase_deg):
    return 10 ** (np.asarray(mag_db, float) / 20.0) * np.exp(1j * np.radians(np.asarray(phase_deg, float)))


def _band_mean(f, y, lo, hi):
    m = (f >= lo) & (f <= hi) & np.isfinite(y)
    if not m.any():
        return None, None
    w = dsp_math._log_weights(f[m])
    mean = float(np.sum(w * y[m]) / np.sum(w))
    rms = float(math.sqrt(np.sum(w * (y[m] - mean) ** 2) / np.sum(w)))
    return mean, rms


def _sub_bands(lo, hi, n=JUNCTION_THIRDS):
    edges = np.geomspace(lo, hi, n + 1)
    return [(float(edges[i]), float(edges[i + 1])) for i in range(n)]


def _on_grid(f_src, y_src, f):
    return np.interp(f, np.asarray(f_src, float), np.asarray(y_src, float))


# ---------------------------------------------------------------- measured sources
def measured_from_rew(titles, api=None, allow_rta=False):
    """{title: (freqs, mag_db, base)} from a live REW. `base` is 'sw' for a sweep on the loopback
    base with no offset, 'rta' for a moving-mic measurement (refused unless allowed), or says the
    offset otherwise."""
    if api is None:
        import rew_api as api  # noqa: F811
    out = {}
    for title in titles:
        mid = api.find_measurement_id(title)
        timing = api.get_timing(mid)
        f, mag, phase = api.get_fr(mid)
        if not timing.get("has_ir", True) or phase is None:
            if not allow_rta:
                raise VerifyError(
                    f"{title!r} is not a sweep (no impulse response) -- an RTA fills the nulls a "
                    f"point prediction shows and cannot verify it; take point sweeps from the "
                    f"tripod, or pass --allow-rta to compare anyway and have it said in the table")
            base = "rta"
        else:
            ref = (timing.get("reference") or "").lower()
            off = float(timing.get("offset_s") or 0.0)
            base = "sw" if ("loopback" in ref and abs(off) < 1e-9) else f"sw(offset {off * 1e3:.3f} ms)"
        out[title] = (np.asarray(f, float), np.asarray(mag, float), base)
    return out


def measured_from_v7_dir(directory):
    """{name: (freqs, mag_db, 'sw')} from Resonalyze v7 files -- the magnitude of each record."""
    out = {}
    for name in sorted(os.listdir(directory)):
        if not name.endswith(".json") or name == "manifest.json":
            continue
        with open(os.path.join(directory, name), encoding="utf-8") as fh:
            doc = json.load(fh)
        if "transferRealSamples" not in doc:
            continue
        x = np.asarray(doc["transferRealSamples"], float)
        fs = int(doc["sampleRate"])
        X = np.fft.rfft(x)
        fb = np.fft.rfftfreq(len(x), 1.0 / fs)
        out[name[:-5]] = (fb[1:], _db(X[1:]), "sw")
    return out


# ---------------------------------------------------------------- the comparison
def verify(predicted, measured, *, pair_names=None, solo_names=None, all_name=None,
           criterion_db=CRITERION_DB):
    """`predicted`: the dict `predict.to_json` wrote. `measured`: {name: (freqs, mag_db, base)}.

    `pair_names`: {(lo, hi): measured name of the pair}; `solo_names`: {code: measured name of
    the channel's solo WITH the tune loaded}; `all_name`: the measured whole-front name.
    """
    f = np.asarray(predicted["freqs_hz"], float)
    chans = predicted["channels"]
    pred_c = {c: _complex(v["mag_db"], v["phase_deg"]) for c, v in chans.items()}
    pair_names = pair_names or {}
    solo_names = solo_names or {}
    report = {"criterion_db": criterion_db, "junctions": [], "channels": [], "all": None,
              "verdict": None, "bases": sorted({b for _, _, b in measured.values()})}

    # 1. Junction interference: predicted vs measured, level-free.
    worst = 0.0
    for j in predicted["junctions"]:
        lo, hi = j["lo"], j["hi"]
        wanted = {f"{lo} solo": solo_names.get(lo), f"{hi} solo": solo_names.get(hi),
                  f"{lo}+{hi} pair": pair_names.get((lo, hi))}
        missing = [what for what, name in wanted.items() if not name or name not in measured]
        if missing:
            report["junctions"].append({"lo": lo, "hi": hi, "fc": j["fc"],
                                        "status": "not measured", "missing": missing})
            continue
        (fa, ma, ba), (fb, mb, bb), (fp, mp, bp) = (measured[wanted[k]] for k in wanted)
        A, B = pred_c[lo], pred_c[hi]
        d_pred = _db(A + B) - _psum_db(_db(A), _db(B))
        d_meas = _on_grid(fp, mp, f) - _psum_db(_on_grid(fa, ma, f), _on_grid(fb, mb, f))
        delta = d_pred - d_meas
        bands = []
        j_worst = 0.0
        for lo_f, hi_f in _sub_bands(j["band"][0], j["band"][1]):
            mean, rms = _band_mean(f, delta, lo_f, hi_f)
            if mean is None:
                continue
            p_mean, _ = _band_mean(f, d_pred, lo_f, hi_f)
            m_mean, _ = _band_mean(f, d_meas, lo_f, hi_f)
            bands.append({"band": [round(lo_f, 1), round(hi_f, 1)], "pred_db": round(p_mean, 2),
                          "meas_db": round(m_mean, 2), "delta_db": round(mean, 2),
                          "rms_db": round(rms, 2), "ok": abs(mean) <= criterion_db})
            j_worst = max(j_worst, abs(mean))
        worst = max(worst, j_worst)
        base = "sw" if all(b == "sw" for b in (ba, bb, bp)) else "/".join(sorted({ba, bb, bp}))
        report["junctions"].append({
            "lo": lo, "hi": hi, "fc": j["fc"], "base": base, "bands": bands,
            "worst_abs_delta_db": round(j_worst, 2),
            "status": "trusted" if j_worst <= criterion_db else "NOT trusted",
        })

    # 2. Channel shape after one offset, plus the offset itself (a calibration fact).
    for code, name in solo_names.items():
        if code not in pred_c or name not in measured:
            continue
        fm, mm, base = measured[name]
        meas = _on_grid(fm, mm, f)
        pred = _db(pred_c[code])
        live = pred >= pred.max() - 20.0            # where the channel actually plays
        offset = float(np.median((meas - pred)[live]))
        resid = np.where(live, meas - pred - offset, np.nan)
        _, rms = _band_mean(f, resid, f[live].min(), f[live].max())
        report["channels"].append({"channel": code, "measured": name, "base": base,
                                   "offset_db": round(offset, 2), "shape_rms_db": round(rms, 2),
                                   "band": [round(float(f[live].min()), 1),
                                            round(float(f[live].max()), 1)]})

    # 3. The whole front as a shape.
    if all_name and all_name in measured:
        fm, mm, base = measured[all_name]
        meas = _on_grid(fm, mm, f)
        pred = np.asarray(predicted["all_mag_db"], float)
        live = pred >= pred.max() - 30.0
        offset = float(np.median((meas - pred)[live]))
        resid = np.where(live, meas - pred - offset, np.nan)
        _, rms = _band_mean(f, resid, f[live].min(), f[live].max())
        report["all"] = {"measured": all_name, "base": base, "offset_db": round(offset, 2),
                         "shape_rms_db": round(rms, 2)}

    judged = [j for j in report["junctions"] if j.get("status") in ("trusted", "NOT trusted")]
    if not judged:
        report["verdict"] = "UNVERIFIED -- no junction had its pair and both solos measured"
    elif all(j["status"] == "trusted" for j in judged):
        report["verdict"] = (f"TRUSTED -- every measured junction within {criterion_db:g} dB "
                             f"(worst {worst:.2f})")
    else:
        bad = [f"{j['lo']}↔{j['hi']}" for j in judged if j["status"] != "trusted"]
        report["verdict"] = (f"NOT trusted at {', '.join(bad)} -- the model disagrees with the car "
                             f"there; a chain fact, a moved driver or an unrecorded protective "
                             f"filter, and which one is the tuner's to find")
    if any(b != "sw" for b in report["bases"]):
        report["verdict"] += "  ⚠️ some rows are not on the point-sweep base (see `base`)"
    return report


def render(report):
    lines = [f"  Verify: predicted vs measured  (criterion |mean Δ| ≤ {report['criterion_db']:g} dB "
             f"per junction band; Δ = predicted − measured interference)", ""]
    lines.append(f"  {'junction':14}{'fc':>6} {'base':<6}{'band':>12}{'pred':>7}{'meas':>7}"
                 f"{'Δ':>7}{'rms':>6}  ")
    lines.append("  " + "-" * 70)
    for j in report["junctions"]:
        name = f"{j['lo']}↔{j['hi']}"
        if j.get("status") == "not measured":
            lines.append(f"  {name:14}{j['fc']:>6.0f}  — not measured: {', '.join(j['missing'])}")
            continue
        for k, b in enumerate(j["bands"]):
            band_s = "%.0f-%.0f" % (b["band"][0], b["band"][1])
            fc_s = f"{j['fc']:.0f}" if k == 0 else ""
            lines.append(f"  {name if k == 0 else '':14}{fc_s:>6}"
                         f" {j['base'] if k == 0 else '':<6}{band_s:>12}{b['pred_db']:>+7.2f}"
                         f"{b['meas_db']:>+7.2f}{b['delta_db']:>+7.2f}{b['rms_db']:>6.2f}"
                         f"  {'ok' if b['ok'] else '✗'}")
        lines.append(f"  {'':14}{'':>6} {'':<6}{'→ ' + j['status']:>12}  worst |Δ| "
                     f"{j['worst_abs_delta_db']:.2f}")
    if report["channels"]:
        lines.append("")
        lines.append("  channel shapes (one offset each; the offset is a calibration fact):")
        for c in report["channels"]:
            lines.append(f"    {c['channel']:6} {c['base']:<4} offset {c['offset_db']:+6.1f} dB   "
                         f"shape rms {c['shape_rms_db']:.2f} dB over {c['band'][0]:.0f}-{c['band'][1]:.0f}")
    if report["all"]:
        a = report["all"]
        lines.append(f"  ALL {a['base']:<4} offset {a['offset_db']:+.1f} dB  shape rms {a['shape_rms_db']:.2f} dB")
    lines.append("")
    lines.append("  " + report["verdict"])
    return "\n".join(lines)


# ---------------------------------------------------------------- CLI
def _default_names(predicted, ver):
    pairs = {(j["lo"], j["hi"]): f"{j['lo']}+{j['hi']}_{ver} (sw)" for j in predicted["junctions"]}
    solos = {c: f"{c}_{ver} (sw)" for c in predicted["channels"]}
    return pairs, solos, f"ALL_{ver} (sw)"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--predicted", required=False, metavar="JSON", help="predict.py's predicted.json")
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--rew", action="store_true", help="read the verification set from a live REW")
    src.add_argument("--measured", metavar="DIR", help="directory of Resonalyze v7 files")
    ap.add_argument("--ver", default="2", help="measurement version of the verification set")
    ap.add_argument("--pair", action="append", default=[], metavar="lo,hi=TITLE",
                    help="measured pair title for a junction (default '<lo>+<hi>_<ver> (sw)')")
    ap.add_argument("--solo", action="append", default=[], metavar="ch=TITLE",
                    help="measured solo title (default '<ch>_<ver> (sw)')")
    ap.add_argument("--all", default=None, metavar="TITLE", help="whole-front title (default 'ALL_<ver> (sw)')")
    ap.add_argument("--allow-rta", action="store_true",
                    help="compare against RTA/MMM rows too -- said in the table; not a verification")
    ap.add_argument("--criterion", type=float, default=CRITERION_DB)
    ap.add_argument("--out", metavar="DIR", default=None, help="write verified.json here")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        return _selftest()
    if not args.predicted or not (args.rew or args.measured):
        ap.error("need --predicted JSON and a measured source (--rew | --measured DIR)")
    with open(args.predicted, encoding="utf-8") as fh:
        predicted = json.load(fh)
    pairs, solos, all_name = _default_names(predicted, args.ver)
    for spec in args.pair:
        key, _, title = spec.partition("=")
        lo, hi = [p.strip() for p in key.split(",")]
        pairs[(lo, hi)] = title
    for spec in args.solo:
        code, _, title = spec.partition("=")
        solos[code.strip()] = title
    if args.all:
        all_name = args.all
    wanted = set(pairs.values()) | set(solos.values()) | {all_name}
    if args.rew:
        import rew_api as api
        ms = api.get_measurements()
        have = {v.get("title") for v in ms.values()}
        titles = sorted(t for t in wanted if t in have)
        missing = sorted(wanted - have)
        if missing:
            print("  not in REW: " + ", ".join(missing), file=sys.stderr)
        measured = measured_from_rew(titles, api=api, allow_rta=args.allow_rta)
    else:
        measured = measured_from_v7_dir(args.measured)
    report = verify(predicted, measured, pair_names=pairs, solo_names=solos, all_name=all_name,
                    criterion_db=args.criterion)
    if args.json:
        print(json.dumps(report, indent=1))
    else:
        print(render(report))
    if args.out:
        os.makedirs(args.out, exist_ok=True)
        with open(os.path.join(args.out, "verified.json"), "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=1)
    return 0 if report["verdict"].startswith("TRUSTED") else 1


# ---------------------------------------------------------------- selftest
def _selftest():
    """Anchored on construction: a measurement built from the prediction verifies to zero, a level
    change verifies to zero (it cancels), and a delay the car did not have does not."""
    import predict as P
    f = P.grid(20, 20000, 48)
    w = np.exp(-2j * np.pi * f * 1.0e-3)
    m = np.exp(-2j * np.pi * f * 1.5e-3)
    chains = {"w-L": P.chain_from_row({"hp": "OFF", "lp": {"f": 300, "type": "LR", "slope": 24},
                                       "gain_db": 0, "ta_ms": 0.5, "polarity": "NORM"}),
              "m-L": P.chain_from_row({"hp": {"f": 300, "type": "LR", "slope": 24}, "lp": "OFF",
                                       "gain_db": 0, "ta_ms": 0.0, "polarity": "NORM"})}
    pred = P.to_json(P.predict(f, {"w-L": w, "m-L": m}, chains))
    A = _complex(pred["channels"]["w-L"]["mag_db"], pred["channels"]["w-L"]["phase_deg"])
    B = _complex(pred["channels"]["m-L"]["mag_db"], pred["channels"]["m-L"]["phase_deg"])

    def meas(A_, B_, gain_db=0.0, base="sw"):
        g = 10 ** (gain_db / 20)
        return {"w-L_2 (sw)": (f, _db(A_ * g), base), "m-L_2 (sw)": (f, _db(B_ * g), base),
                "w-L+m-L_2 (sw)": (f, _db((A_ + B_) * g), base),
                "ALL_2 (sw)": (f, _db((A_ + B_) * g), base)}
    names = dict(pair_names={("w-L", "m-L"): "w-L+m-L_2 (sw)"},
                 solo_names={"w-L": "w-L_2 (sw)", "m-L": "m-L_2 (sw)"}, all_name="ALL_2 (sw)")

    # 1. The car agrees with the model exactly: every delta 0, verdict TRUSTED, offsets 0.
    r = verify(pred, meas(A, B), **names)
    assert r["verdict"].startswith("TRUSTED"), r["verdict"]
    assert all(abs(b["delta_db"]) < 1e-6 for j in r["junctions"] for b in j["bands"]), r
    assert all(abs(c["offset_db"]) < 1e-6 and c["shape_rms_db"] < 1e-6 for c in r["channels"]), r["channels"]
    # 2. Everything 7.3 dB louder (a different mic gain): the interference term does not move,
    #    the offsets report the 7.3 as a fact, and the verdict stands.
    r2 = verify(pred, meas(A, B, gain_db=7.3), **names)
    assert r2["verdict"].startswith("TRUSTED"), r2["verdict"]
    assert all(abs(c["offset_db"] - 7.3) < 0.01 for c in r2["channels"]), r2["channels"]
    assert abs(r2["all"]["offset_db"] - 7.3) < 0.01, r2["all"]
    # 3. The car has 0.6 ms the model does not (a moved driver, a wrong delay fact): the 300 Hz
    #    junction's interference disagrees by more than the criterion -> NOT trusted, and named.
    B_wrong = B * np.exp(-2j * np.pi * f * 0.6e-3)
    r3 = verify(pred, meas(A, B_wrong), **names)
    assert r3["verdict"].startswith("NOT trusted at w-L↔m-L"), r3["verdict"]
    assert r3["junctions"][0]["worst_abs_delta_db"] > CRITERION_DB, r3["junctions"][0]
    # 4. A missing pair is 'not measured', never a pass; an RTA base is said in the verdict.
    r4 = verify(pred, {k: v for k, v in meas(A, B).items() if "+" not in k}, **names)
    assert r4["junctions"][0]["status"] == "not measured" and r4["verdict"].startswith("UNVERIFIED"), r4
    r5 = verify(pred, meas(A, B, base="rta"), **names)
    assert "not on the point-sweep base" in r5["verdict"] and r5["bases"] == ["rta"], r5["verdict"]
    assert "w-L↔m-L" in render(r3) and "✗" in render(r3)
    print("selftest[verify_prediction] OK -- exact car → TRUSTED with zero deltas; +7.3 dB → still "
          "TRUSTED and the offsets say 7.3; an extra 0.6 ms → NOT trusted at the named junction; "
          "missing pair → UNVERIFIED; an RTA base is said in the verdict.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
