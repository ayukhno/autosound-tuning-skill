#!/usr/bin/env python3
"""resonalyze_engine -- Phase 1's proposals from Resonalyze's engines, on the project's own terms.

Auto crossover and Auto delay are Resonalyze's, CALLED through the C# wrapper in `engines/resonalyze/` against the
fork pinned as the submodule `vendor/Resonalyze` (docs/DESIGN-2026-09-17-phase1-variants.md §3; the fork session's
brief and goldens, PAS-008, hub #159). This module is the skill's side of the call:

  * **the input, from the project** -- one block per driver position: the zone by role (sub → Sub; woofer, midrange,
    tweeter → Front; center → Center; rear → Rear), the L/R pair from the codes, and the DRIVER TYPE from the role,
    never the engine's suggestion (on the Passat the suggestion read the mid as a midbass and the centre as a tweeter,
    which put the centre's high-pass on a tweeter's Fs floor). The solos come from a `resonalyze_ir.py` set; each
    file's protective high-pass is read from the set's manifest and divided out in memory, as Resonalyze's own capture
    does -- left in, the Passat's mids and tweeters flip polarity. No distortion curve from REW-converted files (the
    harmonic positions in REW's buffer are a guess). The processing rate and the DELAY RANGE are the project's device
    profile: Resonalyze's catalog has no range for the Helix and falls back to 50 ms, the Helix holds 20.82;
  * **the run** -- `dotnet` on PATH, else `~/.dotnet/dotnet`; the wrapper is built on demand and the submodule fetched
    on demand (`update = none` keeps it out of recursive clones of the skill);
  * **the limits** -- every proposed edge goes through `xover_wishes.check_setting` (the device's families, slopes,
    corner range and step; the fragile driver's Fs floor), a delay the device cannot hold comes back with the rear
    fill that would fit, and a Low-confidence placement is shown as that;
  * **the acceptance** -- the Passat's `ir-v7_49` against the goldens in `engines/resonalyze/golden/`, with the
    cross-OS tolerance of the brief §3: kinds, families, slopes, corners and polarity identical, delays ±0.01 ms,
    gains ±0.1 dB. The goldens are headless -- the engines through a copy of the window's code -- until the user's
    run in the window on Windows confirms them.

The engine proposes; the tuner decides. Nothing here writes the ledger or the DSP.

    python3 rew_tool/resonalyze_engine.py build
    python3 rew_tool/resonalyze_engine.py run PROJECT SET --out DIR [--include-hidden] [--type CODE=Type]
                                          [--file CODE=STEM] [--scene-offset MS] [--rear-fill MS] [--gains]
                                          [--near-side-cut DB] [--json]
    python3 rew_tool/resonalyze_engine.py layout PROJECT SET [--window-defaults] [--include-hidden] [--out FILE]
    python3 rew_tool/resonalyze_engine.py acceptance [--set DIR] [--project DIR]
    python3 rew_tool/resonalyze_engine.py smoke
    python3 rew_tool/resonalyze_engine.py --selftest

`acceptance` needs the Passat's data beside the skill (`../car/passat-b8-2026`), and says "skipped" without it;
`smoke` builds a synthetic set and runs it end to end (CI). `--selftest` is offline and needs no .NET.

Deps: numpy + scipy (the smoke set, and the selftest's check that the PEQ Q convention is the skill's); the layout,
the run and the checks are stdlib.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import dsp_profile as _dp  # noqa: E402
import naming  # noqa: E402
import project as _pj  # noqa: E402
import xover_wishes as _xw  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))
ENGINE_DIR = os.path.join(REPO, "engines", "resonalyze")
SUBMODULE = os.path.join(REPO, "vendor", "Resonalyze")
CSPROJ = os.path.join(ENGINE_DIR, "ResonalyzeEngine.csproj")
DLL = os.path.join(ENGINE_DIR, "bin", "Release", "net10.0", "ResonalyzeEngine.dll")
GOLDEN_DIR = os.path.join(ENGINE_DIR, "golden")

LAYOUT_CONTRACT = "autosound.resonalyze-layout.v1"
RESULT_CONTRACT = "autosound.resonalyze-result.v1"
GOLDEN_CONTRACT = "autosound.resonalyze-golden.v1"
EXIT_REFUSED = 3
#: AutoAlignmentEngine.DefaultMaxDelayMs -- what the window uses when its catalog names no range (the Helix's case).
ENGINE_DEFAULT_MAX_DELAY_MS = 50.0
#: The brief's cross-OS tolerance (PAS-008 §3): one machine is byte-identical, two are not measured.
DELAY_TOL_MS, GAIN_TOL_DB = 0.01, 0.1

BLOCK_ROLES = ("sub", "woofer", "midrange", "tweeter", "center", "rear")
ROLE_ZONE = {"sub": "Sub", "woofer": "Front", "midrange": "Front", "tweeter": "Front", "center": "Center", "rear": "Rear"}
ROLE_LABEL = {"sub": "Sub", "woofer": "Woofer", "midrange": "Mid", "tweeter": "Tweeter", "center": "Centre", "rear": "Rear"}
DRIVER_TYPES = ("Subwoofer", "Woofer", "Midbass", "Midrange", "Tweeter")
FAMILY_CODE = {"Butterworth": "BW", "LinkwitzRiley": "LR", "Bessel": "BE", "Chebyshev": "CHEBYSHEV"}
PROTECTIVE_KIND = {"LR": "LinkwitzRiley", "BW": "Butterworth"}
#: The ledger's EQ kinds (`state.EQ_TYPES`) as Resonalyze's PeqBandType. Both sides use RBJ's Q (the selftest checks).
PEQ_TYPE = {"PK": "Peaking", "LSH": "LowShelf", "HSH": "HighShelf", "APF1": "AllPassFirstOrder", "APF2": "AllPassSecondOrder"}


def driver_type(role, has_sub):
    """Resonalyze's driver class for a skill role.

    The engine's classes are sensible bands (`CrossoverAutoSetup.SensibleRange`): Woofer 40-250 Hz, Midbass 80-500 Hz.
    A door woofer beside a sub plays the midbass's band; without a sub, the woofer's. A centre is a midrange (the
    Passat's is, and the engine's other reading -- a tweeter -- puts its high-pass on a tweeter's Fs floor); a rear fill
    plays a woofer's band. `--type CODE=Type` overrides any of these.
    """
    return {"sub": "Subwoofer", "woofer": "Midbass" if has_sub else "Woofer", "midrange": "Midrange",
            "tweeter": "Tweeter", "center": "Midrange", "rear": "Woofer"}[role]


# ---------------------------------------------------------------- .NET, the submodule, the build

def find_dotnet():
    """`dotnet` on PATH, else the user-level SDK in ~/.dotnet (the design's choice: nothing installed system-wide)."""
    found = shutil.which("dotnet")
    if found:
        return found
    for name in ("dotnet", "dotnet.exe"):
        cand = os.path.join(os.path.expanduser("~"), ".dotnet", name)
        if os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    return None


def pin():
    """The fork commit the skill records for `vendor/Resonalyze`, and the one checked out there (None when absent)."""
    r = subprocess.run(["git", "-C", REPO, "ls-tree", "HEAD", "vendor/Resonalyze"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    recorded = r.stdout.split()[2] if r.returncode == 0 and len(r.stdout.split()) >= 3 else None
    checked = None
    # An uninitialised submodule is an empty folder, and `git -C` there answers for the SKILL's repository.
    if os.path.exists(os.path.join(SUBMODULE, ".git")):
        r = subprocess.run(["git", "-C", SUBMODULE, "rev-parse", "HEAD"], capture_output=True, text=True, encoding="utf-8", errors="replace")
        checked = r.stdout.strip() if r.returncode == 0 else None
    return {"recorded": recorded, "checked_out": checked}


def build(fetch=True, dotnet=None):
    """(True, dll) or (False, what is missing). Fetches the submodule when it is not checked out and `fetch` allows."""
    dotnet = dotnet or find_dotnet()
    if not dotnet:
        return False, ("no .NET SDK: `dotnet` is not on PATH and ~/.dotnet/dotnet is absent -- install the SDK the "
                       "wrapper's global.json names for your user only (dotnet-install.sh --install-dir ~/.dotnet)")
    if not os.path.isfile(os.path.join(SUBMODULE, "dsp", "Resonalyze.Dsp.csproj")):
        if not fetch:
            return False, "vendor/Resonalyze is not checked out -- git submodule update --init --checkout vendor/Resonalyze"
        r = subprocess.run(["git", "-C", REPO, "submodule", "update", "--init", "--checkout", "vendor/Resonalyze"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            return False, f"fetching vendor/Resonalyze failed: {r.stderr.strip()[-400:]}"
    r = subprocess.run([dotnet, "build", "-c", "Release", "-nologo", "-v", "q", CSPROJ], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        return False, "dotnet build failed:\n" + "\n".join((r.stdout + r.stderr).strip().splitlines()[-15:])
    return True, DLL


def run_engine(layout, out_dir, dotnet=None):
    """Write the layout, run the wrapper, read the result. Returns (exit code, result or None, stderr)."""
    dotnet = dotnet or find_dotnet()
    if not os.path.isfile(DLL):
        ok, msg = build(dotnet=dotnet)
        if not ok:
            return 2, None, msg
    os.makedirs(out_dir, exist_ok=True)
    layout_path = os.path.join(out_dir, "layout.json")
    result_path = os.path.join(out_dir, "result.json")
    with open(layout_path, "w", encoding="utf-8") as fh:
        json.dump(layout, fh, indent=1, ensure_ascii=False)
    if os.path.exists(result_path):
        os.remove(result_path)
    r = subprocess.run([dotnet, DLL, layout_path, result_path, "--log", os.path.join(out_dir, "engine.log")],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    result = None
    if os.path.isfile(result_path):
        with open(result_path, encoding="utf-8") as fh:
            result = json.load(fh)
        result["pin"] = pin()
        with open(result_path, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=1, ensure_ascii=False)
    return r.returncode, result, r.stderr


# ---------------------------------------------------------------- the input

def read_set(set_dir, pick=None):
    """The solo of each channel in a `resonalyze_ir.py` set: `({code: {file, protective, title}}, rew_converted, problems)`.

    A control take (`_49ctl`, `_49rep`) or a clarified one is not the solo. Two solos for one code are a question, not a
    guess: `pick` (`{code: stem}`) answers it. The protective high-pass comes from the manifest's record of the capture
    (`protectiveHighPass`: hz, family, slopeDbPerOct), as `Kind:Hz:Slope`.
    """
    with open(os.path.join(set_dir, "manifest.json"), encoding="utf-8") as fh:
        manifest = json.load(fh)
    cands, problems, out = {}, [], {}
    for stem, rec in (manifest.get("files") or {}).items():
        parts = naming.parse_name(rec.get("rewTitle") or "")
        if not parts or parts.get("control") or parts.get("modifier"):
            continue
        cands.setdefault(parts["code"], []).append((stem, rec))
    for code, items in sorted(cands.items()):
        chosen = None
        if pick and code in pick:
            chosen = next((it for it in items if it[0] == pick[code]), None)
            if chosen is None:
                problems.append(f"{code}: no solo named {pick[code]!r} in the set ({', '.join(s for s, _ in items)})")
        elif len(items) == 1:
            chosen = items[0]
        else:
            exact = [it for it in items if it[0].replace("_", "-") == code]
            if len(exact) == 1:
                chosen = exact[0]
            else:
                problems.append(f"{code}: {len(items)} solos in the set ({', '.join(s for s, _ in items)}) -- "
                                f"name one with --file {code}=<stem>")
        if chosen is None:
            continue
        stem, rec = chosen
        protective, hp = None, rec.get("protectiveHighPass")
        if hp:
            kind = PROTECTIVE_KIND.get(str(hp.get("family", "")).upper())
            if kind is None:
                problems.append(f"{code}: the protective filter's family {hp.get('family')!r} is neither LR nor BW -- "
                                "Resonalyze divides out only those")
            else:
                protective = f"{kind}:{float(hp['hz']):g}:{int(hp['slopeDbPerOct'])}"
        out[code] = {"file": stem + ".json", "protective": protective, "title": rec.get("rewTitle")}
    rew_converted = "resonalyze_ir" in str(manifest.get("converter", ""))
    return out, rew_converted, problems


def layout_from(rows, car, dsp, profile, solos, rew_converted, set_dir, *, include_hidden=False, window_defaults=False,
                types=None, scene_offset_ms=None, rear_fill_ms=None, adjust_gains=False, near_side_cut_db=None):
    """The wrapper's input from the project's facts. Returns `(layout, notes, problems)`; a layout with problems is not run.

    `rows`: project.json `channels`; `car`/`dsp`: project.json's blocks; `profile`: the unwrapped device profile;
    `solos`: `read_set()`'s map. `window_defaults` builds what the window does untouched -- the engine's own type
    readings, the distortion curve from the file, its 50 ms delay range -- which is what the goldens record.
    """
    notes, problems = [], []
    by_role = {}
    for row in rows:
        role, code = row.get("role"), row.get("code")
        if role not in ROLE_ZONE:
            continue
        if code not in solos:
            notes.append(f"{code}: no solo in the set -- left out")
            continue
        if row.get("hidden") and not include_hidden:
            notes.append(f"{code}: hidden in the project -- left out (--include-hidden takes it)")
            continue
        by_role.setdefault(role, []).append(code)
    has_sub = bool(by_role.get("sub"))
    types = types or {}
    blocks = []
    for role in BLOCK_ROLES:
        sided, mono = {}, []
        for code in by_role.get(role, []):
            m = re.match(r"^(.*)-([LR])$", code)
            if m:
                sided.setdefault(m.group(1), {})[m.group(2)] = code
            else:
                mono.append(code)
        for base, pair in [(b, p) for b, p in sided.items()] + [(c, None) for c in mono]:
            name = f"{chr(ord('A') + len(blocks))} {ROLE_LABEL[role]}"
            left, right = (base, None) if pair is None else (pair.get("L"), pair.get("R"))
            if left is None:
                problems.append(f"{name}: {right} has no left partner -- the stereo plan reads the left side first")
                continue
            block = {"name": name, "zone": ROLE_ZONE[role], "mono": pair is None, "left": solos[left]["file"],
                     "role": role, "channels": {"left": left}}
            if right:
                block["right"] = solos[right]["file"]
                block["channels"]["right"] = right
            protective = {solos[c]["protective"] for c in (left, right) if c}
            if len(protective) > 1:
                problems.append(f"{name}: L and R were measured behind different protective filters "
                                f"({', '.join(sorted(str(p) for p in protective))}) -- one block carries one")
            elif protective and next(iter(protective)):
                block["protective"] = next(iter(protective))
            wanted = types.get(left) or (types.get(right) if right else None) or types.get(role)
            if wanted and wanted not in DRIVER_TYPES:
                problems.append(f"{name}: {wanted!r} is not a driver type ({', '.join(DRIVER_TYPES)})")
            elif wanted or not window_defaults:
                block["type"] = wanted or driver_type(role, has_sub)
            blocks.append(block)
    if len(blocks) < 2:
        problems.append(f"{len(blocks)} block(s) with a solo -- Auto crossover needs two")

    rate = (dsp or {}).get("dsp_processing_rate_hz") or (profile or {}).get("dsp_processing_rate_hz")
    if not rate:
        problems.append("no processing rate on record -- project.json dsp.dsp_processing_rate_hz")
    max_ms = ENGINE_DEFAULT_MAX_DELAY_MS if window_defaults else ((profile or {}).get("delay") or {}).get("max_ms")
    if max_ms is None:
        problems.append("no delay range on record -- the device profile's delay.max_ms (Resonalyze's catalog is no "
                        "substitute: without a range it assumes 50 ms)")
    layout = {
        "contract": LAYOUT_CONTRACT,
        "note": ("the window's defaults (the engine's own type readings, its 50 ms range)" if window_defaults
                 else "the skill's layout: types from the channel map, the device profile's delay range"),
        "dataDir": os.path.abspath(set_dir),
        "processor": {"model": " ".join(x for x in ((dsp or {}).get("vendor"), (dsp or {}).get("model")) if x) or None,
                      "sampleRateHz": int(rate or 0), "maxDelayMs": float(max_ms if max_ms is not None else 0)},
        "distortion": "file" if (window_defaults or not rew_converted) else "none",
        "blocks": blocks,
        "autoCrossover": {"run": True},
        "autoDelay": {
            "run": True,
            "sceneOffsetMs": 0.25 if scene_offset_ms is None else float(scene_offset_ms),
            "rightHandDrive": str((car or {}).get("wheel", "")).upper() == "RHD",
            "adjustGains": bool(adjust_gains),
            "nearSideCutDb": 1.0 if near_side_cut_db is None else float(near_side_cut_db),
            "rearFillOffsetMs": 15.0 if rear_fill_ms is None else float(rear_fill_ms),
        },
    }
    return layout, notes, problems


def _project_facts(project_dir):
    data = _pj.Project(project_dir).load()
    profile = None
    path = os.path.join(project_dir, (data.get("dsp") or {}).get("profile") or "dsp_profile.json")
    if os.path.isfile(path):
        profile = _dp._unwrap(_dp.load_profile(path))
    channels = {r["code"]: r for r in data.get("channels") or [] if r.get("code")}
    return data, profile, channels


def build_layout(project_dir, set_dir, pick=None, **kw):
    """`layout_from` on a project folder and a set folder. Returns `(layout, notes, problems, channels, xo)`."""
    data, profile, channels = _project_facts(project_dir)
    solos, rew_converted, problems = read_set(set_dir, pick)
    layout, notes, more = layout_from(data.get("channels") or [], data.get("car"), data.get("dsp"), profile, solos,
                                      rew_converted, set_dir, **kw)
    return layout, notes, problems + more, channels, _xw._profile_xo(project_dir)


# ---------------------------------------------------------------- the limits

def check_result(result, layout, channels, xo):
    """Every edge the engine proposed, held to the skill's limits: `[{block, edge, setting, verdict, allowed, why}]`."""
    rows = []
    blocks = {b["name"]: b for b in layout.get("blocks") or []}
    for prop in (result.get("autoCrossover") or {}).get("result") or []:
        codes = [c for c in ((blocks.get(prop["block"]) or {}).get("channels") or {}).values() if c in channels]
        for key, label in (("highPass", "high-pass"), ("lowPass", "low-pass")):
            edge = prop.get(key)
            if not edge:
                continue
            family = FAMILY_CODE.get(edge["family"], edge["family"])
            members = {c: (None, c) for c in codes} if key == "highPass" else {}
            res = _xw.check_setting(members, family, int(edge["slopeDbPerOctave"]), float(edge["frequencyHz"]),
                                    channels, xo)
            rows.append({"block": prop["block"], "edge": label,
                         "setting": f"{family}{edge['slopeDbPerOctave']} {float(edge['frequencyHz']):g} Hz", **res})
    return rows


def fill_that_fits(over):
    """The largest rear fill, in 0.5 ms steps, that brings the widest channel inside the device's range -- or None when
    the widest channel carries no fill (then the fill is not what is too long)."""
    if not over or not over.get("widestCarriesFill"):
        return None
    fill = float(over["rearFillMs"]) - (float(over["neededMs"]) - float(over["limitMs"]))
    fill = math.floor(fill * 2.0 + 1e-9) / 2.0
    return fill if fill >= 0 else None


def notes_on(result):
    """What a reader of the proposal must know before trusting a number."""
    out = []
    ac = result.get("autoCrossover") or {}
    for ch in ac.get("channels") or []:
        if ch.get("typeSource") == "layout" and ch.get("suggestedType") != ch.get("typeUsed"):
            out.append(f"{ch['block']}: {ch['typeUsed']} from the channel map; the engine alone would have read "
                       f"{ch['suggestedType']}")
    if ac.get("error"):
        out.append(f"Auto crossover refused: {ac['error']}")
    ad = result.get("autoDelay") or {}
    for row in ad.get("result") or []:
        d = row.get("decision") or {}
        if d.get("confidence") == "Low":
            out.append(f"{row['channel']}: {row['delayMs']:.2f} ms at LOW confidence -- show it, do not enter it blind")
    if ad.get("error"):
        over = ad.get("overRange")
        fill = fill_that_fits(over)
        out.append(f"Auto delay refused: {ad['error']}" + (
            f" A rear fill of {fill:g} ms should fit: rerun with --rear-fill {fill:g}." if fill is not None else ""))
    return out


# ---------------------------------------------------------------- the goldens

def _edge_label(edge):
    return f"{edge['family']} {edge['slopeDbPerOctave']} dB/oct {edge['frequencyHz']:g} Hz" if edge else "none"


def compare(result, golden):
    """Differences beyond the brief's tolerance between a result and a golden's `expect`; [] when it holds."""
    diffs = []
    ga, ra = golden.get("autoCrossover") or {}, result.get("autoCrossover") or {}
    if ga.get("blockOrderAfterReorder") != ra.get("blockOrderAfterReorder"):
        diffs.append(f"block order {ra.get('blockOrderAfterReorder')} vs golden {ga.get('blockOrderAfterReorder')}")
    gt = {c["block"]: c["typeUsed"] for c in ga.get("channels") or []}
    rt = {c["block"]: c["typeUsed"] for c in ra.get("channels") or []}
    if gt != rt:
        diffs.append(f"types {rt} vs golden {gt}")
    gp = {p["block"]: p for p in ga.get("result") or []}
    rp = {p["block"]: p for p in ra.get("result") or []}
    if set(gp) != set(rp):
        diffs.append(f"crossover blocks {sorted(rp)} vs golden {sorted(gp)}")
    for name in sorted(set(gp) & set(rp)):
        g, r = gp[name], rp[name]
        if g["kind"] != r["kind"]:
            diffs.append(f"{name}: {r['kind']} vs golden {g['kind']}")
        for key in ("highPass", "lowPass"):
            ge, re_ = g.get(key), r.get(key)
            same = (ge is None and re_ is None) or (ge is not None and re_ is not None and
                                                  (ge["family"], ge["slopeDbPerOctave"], ge["frequencyHz"]) ==
                                                  (re_["family"], re_["slopeDbPerOctave"], re_["frequencyHz"]))
            if not same:
                diffs.append(f"{name} {key}: {_edge_label(re_)} vs golden {_edge_label(ge)}")
        if abs(float(g["gainDb"]) - float(r["gainDb"])) > GAIN_TOL_DB + 1e-9:
            diffs.append(f"{name} gain: {r['gainDb']} vs golden {g['gainDb']} dB")
    gd, rd = golden.get("autoDelay") or {}, result.get("autoDelay") or {}
    if bool(gd.get("error")) != bool(rd.get("error")):
        diffs.append(f"Auto delay {'refused' if rd.get('error') else 'ran'}: {rd.get('error') or ''} "
                     f"-- golden {'refused' if gd.get('error') else 'ran'}")
    if gd.get("overRange") or rd.get("overRange"):
        go, ro = gd.get("overRange") or {}, rd.get("overRange") or {}
        if go.get("channel") != ro.get("channel") or abs(float(go.get("neededMs", 0)) - float(ro.get("neededMs", 0))) \
                > DELAY_TOL_MS + 1e-9:
            diffs.append(f"over range {ro} vs golden {go}")
    for key in ("left", "right"):
        if (gd.get("bridge") or {}).get(key) != (rd.get("bridge") or {}).get(key):
            diffs.append(f"bridge {key}: {(rd.get('bridge') or {}).get(key)} vs golden {(gd.get('bridge') or {}).get(key)}")
    gr = {x["channel"]: x for x in gd.get("result") or []}
    rr = {x["channel"]: x for x in rd.get("result") or []}
    if set(gr) != set(rr):
        diffs.append(f"delay channels {sorted(rr)} vs golden {sorted(gr)}")
    for ch in sorted(set(gr) & set(rr)):
        g, r = gr[ch], rr[ch]
        if abs(float(g["delayMs"]) - float(r["delayMs"])) > DELAY_TOL_MS + 1e-9:
            diffs.append(f"{ch}: {r['delayMs']:.2f} ms vs golden {g['delayMs']:.2f}")
        if bool(g["invertPolarity"]) != bool(r["invertPolarity"]):
            diffs.append(f"{ch}: polarity {'inverted' if r['invertPolarity'] else 'normal'} vs golden "
                         f"{'inverted' if g['invertPolarity'] else 'normal'}")
        if abs(float(g["gainDb"]) - float(r["gainDb"])) > GAIN_TOL_DB + 1e-9:
            diffs.append(f"{ch}: gain {r['gainDb']} vs golden {g['gainDb']} dB")
        gk, rk = g.get("decision") or {}, r.get("decision") or {}
        if (gk.get("kind"), gk.get("confidence")) != (rk.get("kind"), rk.get("confidence")):
            diffs.append(f"{ch}: decision {rk.get('kind')}/{rk.get('confidence')} vs golden "
                         f"{gk.get('kind')}/{gk.get('confidence')}")
    return diffs


def expect_of(result):
    """The part of a result a golden pins."""
    ac, ad = result.get("autoCrossover") or {}, result.get("autoDelay") or {}
    return {
        "autoCrossover": {
            "channels": [{k: c[k] for k in ("block", "suggestedType", "typeUsed")} for c in ac.get("channels") or []],
            "result": ac.get("result"),
            "blockOrderAfterReorder": ac.get("blockOrderAfterReorder"),
        },
        "autoDelay": {k: ad[k] for k in ("request", "bridge", "result", "error", "overRange") if k in ad},
    }


def _md5(path):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _default_data():
    car = os.path.join(os.path.dirname(REPO), "car", "passat-b8-2026")
    return (os.environ.get("AUTOSOUND_PASSAT_IR_SET") or os.path.join(car, "data", "ir-v7_49"),
            os.environ.get("AUTOSOUND_PASSAT_PROJECT") or car)


def acceptance(set_dir=None, project_dir=None, dotnet=None, keep=None, echo=print):
    """Every golden in `engines/resonalyze/golden/` against a fresh run. 0 = all hold (or skipped), 1 = a difference."""
    d_set, d_project = _default_data()
    set_dir, project_dir = set_dir or d_set, project_dir or d_project
    goldens = sorted(glob.glob(os.path.join(GOLDEN_DIR, "*.json")))
    if not os.path.isfile(os.path.join(set_dir, "manifest.json")) or not os.path.isfile(
            os.path.join(project_dir, "project.json")):
        echo(f"  skipped: the Passat's data is not here ({set_dir}) -- the goldens need the set they were made on")
        return 0
    failed = 0
    md5_cache = {}
    for path in goldens:
        with open(path, encoding="utf-8") as fh:
            golden = json.load(fh)
        name = os.path.basename(path)
        wrong = []
        for fname, want in (golden.get("set") or {}).get("md5", {}).items():
            fp = os.path.join(set_dir, fname)
            got = md5_cache.setdefault(fp, _md5(fp) if os.path.isfile(fp) else None)
            if got != want:
                wrong.append(f"{fname} ({got or 'missing'})")
        if wrong:
            echo(f"  FAIL {name}: not the set the golden was made on -- {', '.join(wrong)}")
            failed += 1
            continue
        how = golden["layout"]
        layout, _, problems, _, _ = build_layout(
            project_dir, set_dir, include_hidden=how.get("includeHidden", False),
            window_defaults=how.get("mode") == "window-defaults", adjust_gains=how.get("adjustGains", False))
        for key in ("maxDelayMs",):
            if key in how:
                layout["processor"][key] = how[key]
        if "distortion" in how:
            layout["distortion"] = how["distortion"]
        if problems:
            echo(f"  FAIL {name}: the layout has problems: {'; '.join(problems)}")
            failed += 1
            continue
        out_dir = os.path.join(keep, name[:-5]) if keep else tempfile.mkdtemp(prefix="resonalyze-acceptance-")
        rc, result, err = run_engine(layout, out_dir, dotnet)
        if result is None:
            echo(f"  FAIL {name}: the wrapper wrote nothing (exit {rc}): {err.strip()[-300:]}")
            failed += 1
            continue
        diffs = compare(result, golden["expect"])
        if diffs:
            failed += 1
            echo(f"  FAIL {name}: {len(diffs)} difference(s) beyond the tolerance")
            for d in diffs:
                echo(f"         {d}")
        else:
            echo(f"  ok   {name}: {golden.get('what', '')}")
        if not keep:
            shutil.rmtree(out_dir, ignore_errors=True)
    echo(f"  {len(goldens) - failed} of {len(goldens)} golden(s) hold -- kinds, families, slopes, corners and polarity "
         f"identical, delays ±{DELAY_TOL_MS} ms, gains ±{GAIN_TOL_DB} dB")
    return 1 if failed else 0


# ---------------------------------------------------------------- the report

def render(layout, result, checks, notes):
    lines = [f"  Resonalyze engines on {len(layout['blocks'])} block(s) -- {layout['note']}"]
    p = (result or {}).get("pin") or {}
    if p.get("recorded") and p.get("recorded") == p.get("checked_out"):
        lines.append(f"  fork pin {p['recorded'][:9]}")
    elif p.get("recorded"):
        lines.append(f"  fork pin {p['recorded'][:9]} -- checked out {str(p.get('checked_out'))[:9]}, NOT the pin")
    elif p.get("checked_out"):
        lines.append(f"  fork checked out {p['checked_out'][:9]} (no pin recorded in this checkout's git)")
    ac = (result or {}).get("autoCrossover") or {}
    if ac.get("result"):
        lines += ["", f"  {'block':12}{'type':11}{'high-pass':24}{'low-pass':24}{'gain':>6}"]
        types = {c["block"]: c["typeUsed"] for c in ac.get("channels") or []}
        for prop in ac["result"]:
            hp, lp = prop.get("highPass"), prop.get("lowPass")
            show = (lambda e: f"{FAMILY_CODE.get(e['family'], e['family'])}{e['slopeDbPerOctave']} {e['frequencyHz']:g} Hz"
                    if e else "--")
            lines.append(f"  {prop['block']:12}{types.get(prop['block'], ''):11}{show(hp):24}{show(lp):24}"
                         f"{prop['gainDb']:>+6.1f}")
        if ac.get("subElevationDb") is not None or (ac.get("options") or {}).get("subElevationDb") is not None:
            lines.append(f"  sub elevation {(ac.get('options') or {}).get('subElevationDb')} dB")
    flagged = [c for c in checks if c["verdict"] != "OK"]
    if checks:
        lines.append("")
        lines.append(f"  limits: {len(checks) - len(flagged)} of {len(checks)} edge(s) OK")
        for c in flagged:
            lines.append(f"    {c['block']} {c['edge']} {c['setting']} -- {c['verdict']}")
            for w in c["why"]:
                lines.append(f"        · {w}")
    ad = (result or {}).get("autoDelay") or {}
    if ad.get("result"):
        b = ad.get("bridge") or {}
        lines += ["", f"  delays (scene offset {ad['request']['sceneOffsetMs']:g} ms, rear fill "
                      f"{ad['request']['rearFillOffsetMs']:g} ms; bridge {b.get('left')} → {b.get('right')})",
                  f"  {'channel':22}{'ms':>7}  {'polarity':9}decision"]
        for row in ad["result"]:
            d = row.get("decision") or {}
            lines.append(f"  {row['channel']:22}{row['delayMs']:>7.2f}  {'inverted' if row['invertPolarity'] else 'normal':9}"
                         f"{d.get('kind', '')}{', ' + d['confidence'] if d.get('confidence') else ''}"
                         + (f"   gain {row['gainDb']:+.1f}" if row.get("gainAdjusted") else ""))
    if notes:
        lines.append("")
        lines += [f"  ! {n}" for n in notes]
    lines += ["", "  The engine proposes; nothing is entered without the tuner's OK."]
    return "\n".join(lines)


# ---------------------------------------------------------------- smoke: a synthetic set end to end

def smoke(dotnet=None, echo=print):
    """A synthetic sub + three-way front through the wrapper: it builds, runs, and returns a sane proposal."""
    import numpy as np
    from scipy import signal

    import resonalyze_ir as _ri
    fs, n, pre = 96000, 1 << 16, 1 << 14
    rng = np.random.default_rng(7)
    drivers = {  # code: (role, arrival ms, high-pass Hz or None, low-pass Hz or None)
        "sw": ("sub", 5.0, 25.0, 120.0),
        "w-L": ("woofer", 3.0, 45.0, 1500.0), "w-R": ("woofer", 3.4, 45.0, 1500.0),
        "m-L": ("midrange", 2.8, 250.0, 9000.0), "m-R": ("midrange", 3.2, 250.0, 9000.0),
        "tw-L": ("tweeter", 2.6, 1800.0, None), "tw-R": ("tweeter", 3.0, 1800.0, None),
    }
    with tempfile.TemporaryDirectory() as tmp:
        set_dir = os.path.join(tmp, "set")
        os.makedirs(set_dir)
        files = {}
        for code, (role, arrival, hp, lp) in drivers.items():
            x = np.zeros(n)
            x[pre + int(round(arrival * 1e-3 * fs))] = 0.3
            if hp:
                x = signal.sosfilt(signal.butter(2, hp, "highpass", fs=fs, output="sos"), x)
            if lp:
                x = signal.sosfilt(signal.butter(2, lp, "lowpass", fs=fs, output="sos"), x)
            x = x + 1e-6 * rng.standard_normal(n)
            doc, _ = _ri.build_v7(x, fs, -pre / fs, low_hz=20.0, high_hz=20000.0)
            stem = code.replace("-", "_")
            _ri.write_v7(doc, os.path.join(set_dir, stem + ".json"))
            files[stem] = {"rewTitle": f"{code}_1 (sw)"}
        with open(os.path.join(set_dir, "manifest.json"), "w", encoding="utf-8") as fh:
            json.dump({"converter": "autosound-tuning-skill rew_tool/resonalyze_ir.py", "files": files}, fh)
        rows = [{"code": c, "role": r} for c, (r, *_rest) in drivers.items()]
        solos, rew, problems = read_set(set_dir)
        layout, notes, more = layout_from(rows, {"wheel": "LHD"}, {"dsp_processing_rate_hz": 96000},
                                          {"delay": {"max_ms": 20.0}}, solos, rew, set_dir)
        assert not problems and not more, (problems, more)
        rc, result, err = run_engine(layout, os.path.join(tmp, "out"), dotnet)
        assert result is not None, f"the wrapper wrote nothing (exit {rc}): {err[-600:]}"
        assert rc == 0, f"exit {rc}: {json.dumps(result.get('autoDelay'))[:600]} {err[-400:]}"
        assert result["contract"] == RESULT_CONTRACT
        props = {p["block"]: p for p in result["autoCrossover"]["result"]}
        assert set(props) == {"A Sub", "B Woofer", "C Mid", "D Tweeter"}, props
        assert props["A Sub"]["lowPass"] and props["D Tweeter"]["highPass"], props
        delays = {r["channel"]: r["delayMs"] for r in result["autoDelay"]["result"]}
        assert len(delays) == 7 and all(0.0 <= v <= 20.0 for v in delays.values()), delays
        # the tweeter arrives 0.4 ms before the woofer on its side, and a woofer's low-pass only adds lag: it waits
        assert delays["D Tweeter L"] > delays["B Woofer L"], delays
        echo(render(layout, result, check_result(result, layout, {c: {"code": c, "role": r} for c, (r, *_x) in
                                                                  drivers.items()}, None), notes_on(result)))
    echo("smoke[resonalyze_engine] OK -- a synthetic sub + three-way front built, ran through both engines, and came "
         "back with a proposal per block and seven delays inside the range, the early tweeter held back")
    return 0


# ---------------------------------------------------------------- selftest (offline, no .NET)

def _selftest():
    assert driver_type("woofer", True) == "Midbass" and driver_type("woofer", False) == "Woofer"
    assert driver_type("center", True) == "Midrange" and driver_type("rear", True) == "Woofer"

    rows = [{"code": "sw", "role": "sub"}, {"code": "w-L", "role": "woofer"}, {"code": "w-R", "role": "woofer"},
            {"code": "m-L", "role": "midrange", "fs_hz": {"value": 194.8}},
            {"code": "m-R", "role": "midrange", "fs_hz": {"value": 196.7}},
            {"code": "tw-L", "role": "tweeter", "fs_hz": {"value": 939.7}},
            {"code": "tw-R", "role": "tweeter", "fs_hz": {"value": 948.9}},
            {"code": "c", "role": "center"}, {"code": "VC", "role": "virtual"},
            {"code": "r-L", "role": "rear", "hidden": True}, {"code": "r-R", "role": "rear", "hidden": True}]
    with tempfile.TemporaryDirectory() as tmp:
        lr = {"hz": 100.0, "family": "LR", "slopeDbPerOct": 24}
        files = {"sw": {"rewTitle": "sw_49 (sw) x0"},
                 "w_L": {"rewTitle": "w-L_49 (sw) x0"}, "w_R": {"rewTitle": "w-R_49 (sw) x0"},
                 "m_L": {"rewTitle": "m-L_49 (sw) x0", "protectiveHighPass": lr},
                 "m_R": {"rewTitle": "m-R_49 (sw) x0", "protectiveHighPass": lr},
                 "tw_L": {"rewTitle": "tw-L_49 (sw) x0", "protectiveHighPass": dict(lr, hz=1000.0)},
                 "tw_R": {"rewTitle": "tw-R_49 (sw) x0", "protectiveHighPass": dict(lr, hz=1000.0)},
                 "c": {"rewTitle": "c_49 (sw) x0", "protectiveHighPass": lr},
                 "r_L": {"rewTitle": "r-L_49 (sw) x0", "protectiveHighPass": lr},
                 "r_R": {"rewTitle": "r-R_49 (sw) x0", "protectiveHighPass": lr},
                 "m_L-ctl1": {"rewTitle": "m-L_49ctl (sw) x0", "protectiveHighPass": lr}}
        with open(os.path.join(tmp, "manifest.json"), "w", encoding="utf-8") as fh:
            json.dump({"converter": "autosound-tuning-skill rew_tool/resonalyze_ir.py", "files": files}, fh)
        solos, rew, problems = read_set(tmp)
        # the control take is not the solo; each protective filter comes from the capture's record
        assert not problems and rew and solos["m-L"]["file"] == "m_L.json", (problems, solos["m-L"])
        assert solos["tw-R"]["protective"] == "LinkwitzRiley:1000:24" and solos["w-L"]["protective"] is None

        car, dsp, profile = {"wheel": "LHD"}, {"dsp_processing_rate_hz": 96000, "vendor": "Audiotec-Fischer",
                                               "model": "Helix DSP Ultra S"}, {"delay": {"max_ms": 20.82}}
        layout, notes, more = layout_from(rows, car, dsp, profile, solos, rew, tmp)
        assert not more, more
        names = [b["name"] for b in layout["blocks"]]
        assert names == ["A Sub", "B Woofer", "C Mid", "D Tweeter", "E Centre"], names     # the rear is hidden
        assert any("r-L: hidden" in n for n in notes), notes
        by = {b["name"]: b for b in layout["blocks"]}
        assert by["A Sub"]["mono"] and by["A Sub"]["type"] == "Subwoofer" and "protective" not in by["A Sub"]
        assert by["B Woofer"]["type"] == "Midbass" and by["C Mid"]["type"] == "Midrange" and by["E Centre"]["type"] == "Midrange"
        assert by["D Tweeter"]["protective"] == "LinkwitzRiley:1000:24" and by["D Tweeter"]["right"] == "tw_R.json"
        assert layout["processor"]["maxDelayMs"] == 20.82 and layout["distortion"] == "none", layout["processor"]

        # the window's defaults: no types, the file's distortion, the engine's 50 ms; the rear taken when asked
        wd, _, more = layout_from(rows, car, dsp, profile, solos, rew, tmp, window_defaults=True, include_hidden=True)
        assert not more and all("type" not in b for b in wd["blocks"]), wd["blocks"]
        assert [b["name"] for b in wd["blocks"]][-1] == "F Rear" and wd["processor"]["maxDelayMs"] == 50.0
        assert wd["distortion"] == "file"
        # a type the tuner names wins, by code or by role; a word that is no type is a problem, not a guess
        tl, _, more = layout_from(rows, car, dsp, profile, solos, rew, tmp, types={"c": "Tweeter", "woofer": "Woofer"})
        tb = {b["name"]: b for b in tl["blocks"]}
        assert not more and tb["E Centre"]["type"] == "Tweeter" and tb["B Woofer"]["type"] == "Woofer"
        _, _, more = layout_from(rows, car, dsp, profile, solos, rew, tmp, types={"c": "Horn"})
        assert more and "not a driver type" in more[0], more
        # no delay range on record is a refusal, never Resonalyze's 50 ms by default
        _, _, more = layout_from(rows, car, dsp, {}, solos, rew, tmp)
        assert any("delay range" in m for m in more), more

        # two solos for one code: a question with the way to answer it
        files2 = dict(files, **{"m_L-again": {"rewTitle": "m-L_49 (sw) x1"}})
        files2.pop("m_L")
        files2["m_L_old"] = {"rewTitle": "m-L_49 (sw) x0"}
        with open(os.path.join(tmp, "manifest.json"), "w", encoding="utf-8") as fh:
            json.dump({"files": files2}, fh)
        _, _, problems = read_set(tmp)
        assert problems and "--file m-L=" in problems[0], problems
        picked, _, problems = read_set(tmp, pick={"m-L": "m_L_old"})
        assert not problems and picked["m-L"]["file"] == "m_L_old.json"

    # the limits on an engine's proposal: the device's slope ladder and the tweeter's Fs floor
    channels = {r["code"]: r for r in rows}
    xo = {"types": {"BE": {"orders_db_per_oct": [6, 12, 18, 24, 30, 36, 42]}, "BW": {"orders_db_per_oct": [6, 12, 18, 24]},
                    "LR": {"orders_db_per_oct": [12, 24, 36]}}, "range": [20.0, 20480.0], "step": 1.0}
    lay = {"blocks": [{"name": "C Mid", "channels": {"left": "m-L", "right": "m-R"}},
                      {"name": "D Tweeter", "channels": {"left": "tw-L", "right": "tw-R"}},
                      {"name": "A Sub", "channels": {"left": "sw"}}]}
    edge = lambda fam, slope, f: {"family": fam, "slopeDbPerOctave": slope, "frequencyHz": f}  # noqa: E731
    res = {"autoCrossover": {"result": [
        {"block": "C Mid", "kind": "BandPass", "highPass": edge("Bessel", 18, 500.0), "lowPass": edge("LinkwitzRiley", 24, 2300.0), "gainDb": 0},
        {"block": "D Tweeter", "kind": "HighPass", "highPass": edge("LinkwitzRiley", 24, 900.0), "lowPass": None, "gainDb": -0.1},
        {"block": "A Sub", "kind": "LowPass", "highPass": None, "lowPass": edge("LinkwitzRiley", 48, 80.0), "gainDb": -0.1}]}}
    checks = {(c["block"], c["edge"]): c for c in check_result(res, lay, channels, xo)}
    assert checks[("C Mid", "high-pass")]["verdict"] == "OK" and checks[("C Mid", "low-pass")]["verdict"] == "OK"
    tw = checks[("D Tweeter", "high-pass")]
    assert tw["verdict"] == "REFUSED" and tw["allowed"]["f_hz"] == 1044.0, tw           # the stricter side, tw-R
    assert checks[("A Sub", "low-pass")]["verdict"] == "ADJUSTED" and checks[("A Sub", "low-pass")]["allowed"]["order_db"] == 36

    # the over-range refusal names the fill that fits -- the Passat's window-default rear on the Helix's 20.82 ms
    over = {"channel": "F Rear L", "neededMs": 23.67, "limitMs": 20.82, "rearFillMs": 15.0, "widestCarriesFill": True}
    assert fill_that_fits(over) == 12.0 and fill_that_fits(dict(over, widestCarriesFill=False)) is None
    msg = notes_on({"autoDelay": {"error": "does not fit", "overRange": over}})
    assert any("--rear-fill 12" in m for m in msg), msg
    low = notes_on({"autoCrossover": {"channels": [{"block": "E Centre", "typeSource": "layout", "suggestedType": "Tweeter",
                                                    "typeUsed": "Midrange"}]},
                    "autoDelay": {"result": [{"channel": "F Rear L", "delayMs": 23.67, "decision": {"confidence": "Low"}}]}})
    assert any("engine alone would have read Tweeter" in m for m in low) and any("LOW confidence" in m for m in low), low

    # the tolerance: 0.01 ms and 0.1 dB pass, a corner or a polarity never does
    gold = {"autoCrossover": {"blockOrderAfterReorder": ["A Sub", "C Mid"], "channels": [{"block": "C Mid", "typeUsed": "Midrange"}],
                              "result": [dict(res["autoCrossover"]["result"][0])]},
            "autoDelay": {"bridge": {"left": "D Tweeter L", "right": "D Tweeter R"},
                          "result": [{"channel": "C Mid L", "delayMs": 5.88, "invertPolarity": False, "gainDb": 0.0,
                                      "decision": {"kind": "Search", "confidence": "Low"}}]}}
    same = json.loads(json.dumps(gold))
    same["autoDelay"]["result"][0]["delayMs"] = 5.89
    same["autoCrossover"]["result"][0]["gainDb"] = 0.1
    assert compare(same, gold) == [], compare(same, gold)
    moved = json.loads(json.dumps(gold))
    moved["autoDelay"]["result"][0]["delayMs"] = 5.90
    moved["autoDelay"]["result"][0]["invertPolarity"] = True
    moved["autoCrossover"]["result"][0]["highPass"]["frequencyHz"] = 501.0
    diffs = compare(moved, gold)
    assert len(diffs) == 3 and any("polarity" in d for d in diffs) and any("501" in d for d in diffs), diffs

    # the PEQ bands travel as RBJ's Q on both sides: Resonalyze's analog magnitude (EqualizationCurve.cs) against the
    # skill's biquad, well below Nyquist where the two must agree
    import numpy as np

    import dsp_math

    def resonalyze_db(kind, f0, gain, q, f):
        a, x = 10.0 ** (gain / 40.0), f / f0
        if kind == "PK":
            base = (1 - x * x) ** 2
            return 10 * np.log10((base + (a * x / q) ** 2) / (base + (x / (a * q)) ** 2))
        t2 = (np.sqrt(a) * x / q) ** 2
        lifted, flat = a - x * x, 1 - a * x * x
        num, den = (lifted, flat) if kind == "LSH" else (flat, lifted)
        return 20 * np.log10(a) + 10 * np.log10((num * num + t2) / (den * den + t2))
    f = np.geomspace(40.0, 4000.0, 60)
    for kind, gain, q in (("PK", -6.0, 2.0), ("PK", 4.0, 0.7), ("LSH", 5.0, 0.71), ("HSH", -4.0, 1.2)):
        ours = 20 * np.log10(np.abs(dsp_math.peq_response(f, kind, 400.0, gain, q, fs=96000)))
        assert np.max(np.abs(ours - resonalyze_db(kind, 400.0, gain, q, f))) < 0.05, (kind, gain, q)
    assert set(PEQ_TYPE) >= {"PK", "LSH", "HSH"}

    print("selftest[resonalyze_engine] OK -- blocks from the channel map (the sub mono, the pairs by -L/-R, the "
          "hidden rear left out and taken when asked), types from the roles (a woofer beside a sub is a midbass, a "
          "centre a midrange), the protective filters from the set's manifest, the device's delay range or a refusal; "
          "the window-default layout; a tweeter corner under its Fs floor refused with 1044 Hz named; the rear fill "
          "that fits the Helix (12 ms); the cross-OS tolerance; and the PEQ Q the same on both sides")
    return 0


# ---------------------------------------------------------------- CLI

def _pairs(items, what):
    out = {}
    for it in items or []:
        if "=" not in it:
            raise SystemExit(f"{what} wants CODE=VALUE, not {it!r}")
        k, v = it.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    if argv[:1] == ["--selftest"]:
        return _selftest()
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build", help="fetch the submodule when needed and build the wrapper")
    for name in ("run", "layout"):
        p = sub.add_parser(name)
        p.add_argument("project")
        p.add_argument("set", help="a resonalyze_ir.py set: the solos and manifest.json")
        p.add_argument("--out", help="run: the folder for layout/result/log; layout: the file")
        p.add_argument("--include-hidden", action="store_true")
        p.add_argument("--window-defaults", action="store_true", help="what the window does untouched (the goldens)")
        p.add_argument("--type", action="append", metavar="CODE=Type", help="a driver type by channel code or role")
        p.add_argument("--file", action="append", metavar="CODE=STEM", help="which solo, when the set has two")
        p.add_argument("--scene-offset", type=float, metavar="MS")
        p.add_argument("--rear-fill", type=float, metavar="MS")
        p.add_argument("--near-side-cut", type=float, metavar="DB")
        p.add_argument("--gains", action="store_true", help="balance the channel gains after the delays")
        p.add_argument("--json", action="store_true")
    p = sub.add_parser("acceptance")
    p.add_argument("--set")
    p.add_argument("--project")
    p.add_argument("--keep", metavar="DIR", help="keep each run's layout, result and log here")
    sub.add_parser("smoke")
    a = ap.parse_args(argv)

    if a.cmd == "build":
        ok, msg = build()
        print(f"  {'built' if ok else 'not built'}: {msg}")
        return 0 if ok else 1
    if a.cmd == "acceptance":
        return acceptance(a.set, a.project, keep=a.keep)
    if a.cmd == "smoke":
        return smoke()

    layout, notes, problems, channels, xo = build_layout(
        a.project, a.set, pick=_pairs(a.file, "--file"), include_hidden=a.include_hidden,
        window_defaults=a.window_defaults, types=_pairs(a.type, "--type"), scene_offset_ms=a.scene_offset,
        rear_fill_ms=a.rear_fill, adjust_gains=a.gains, near_side_cut_db=a.near_side_cut)
    for n in notes:
        print(f"  · {n}", file=sys.stderr)
    if problems:
        for pr in problems:
            print(f"  ✗ {pr}", file=sys.stderr)
        return 2
    if a.cmd == "layout":
        text = json.dumps(layout, indent=1, ensure_ascii=False)
        if a.out:
            with open(a.out, "w", encoding="utf-8") as fh:
                fh.write(text + "\n")
            print(f"  wrote {a.out}")
        else:
            print(text)
        return 0
    out_dir = a.out or tempfile.mkdtemp(prefix="resonalyze-run-")
    rc, result, err = run_engine(layout, out_dir)
    if result is None:
        print(f"  the wrapper wrote nothing (exit {rc}): {err.strip()[-600:]}", file=sys.stderr)
        return 1
    checks = check_result(result, layout, channels, xo)
    notes_after = notes_on(result)
    with open(os.path.join(out_dir, "checks.json"), "w", encoding="utf-8") as fh:
        json.dump({"checks": checks, "notes": notes_after}, fh, indent=1, ensure_ascii=False)
    if a.json:
        print(json.dumps({"result": result, "checks": checks, "notes": notes_after}, indent=1, ensure_ascii=False))
    else:
        print(render(layout, result, checks, notes_after))
        print(f"\n  wrote {out_dir}/layout.json, result.json, engine.log, checks.json")
    return 0 if rc == 0 else EXIT_REFUSED


if __name__ == "__main__":
    import console                       # issue #21: a code page must not destroy a result
    console.install()
    sys.exit(main())
