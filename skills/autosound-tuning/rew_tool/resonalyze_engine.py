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
    profile: Resonalyze's catalog has no range for the Helix and falls back to 50 ms; the Helix holds 20.82 ms on an
    output and 20.82 on the virtual channel feeding it, and the two add (`delay_tiers`);
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
#: The fork commit the wrapper is built against -- the submodule's record; the selftest holds the two together. A prebuilt
#: engine is installed per pin and platform, so a binary built against another pin is never picked up.
ENGINE_PIN = "b0ce9fb"
#: An engine executable named by the person, ahead of everything else.
ENGINE_ENV = "AUTOSOUND_RESONALYZE_ENGINE"
#: Where a tag's release keeps the prebuilt engines. The file NAME is computable -- that is what hub `RELEASE-CHANNEL.md`
#: §12 requires it for -- so nothing here lists a release or picks an asset: pin and platform say which file, and
#: `SHA256SUMS` beside it says whether what arrived is that file.
RELEASE_DOWNLOAD = "https://github.com/ayukhno/autosound-tuning-skill/releases/download"
SUMS_NAME = "SHA256SUMS"
#: ~30 MB over whatever line the person has, so not the 20 s a form gets.
FETCH_TIMEOUT_S = 180

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


def rid():
    """.NET's runtime identifier for this machine: win-x64, osx-arm64, linux-x64 ..."""
    import platform
    arch = "arm64" if platform.machine().lower() in ("arm64", "aarch64") else "x64"
    system = "win" if sys.platform.startswith("win") else "osx" if sys.platform == "darwin" else "linux"
    return f"{system}-{arch}"


def installed_dir():
    """Where a prebuilt engine for this pin and platform lives: %LOCALAPPDATA% on Windows, ~/.local/share elsewhere."""
    base = os.environ.get("LOCALAPPDATA") if sys.platform.startswith("win") else None
    base = base or os.path.join(os.path.expanduser("~"), ".local", "share")
    return os.path.join(base, "autosound", "engines", "resonalyze", ENGINE_PIN, rid())


def _exe_name():
    return "ResonalyzeEngine.exe" if sys.platform.startswith("win") else "ResonalyzeEngine"


def engine_command(dotnet=None):
    """How to start the engine: `(argv prefix, how)`, or `(None, what is missing)`.

    1. `AUTOSOUND_RESONALYZE_ENGINE` -- an executable a person named;
    2. a prebuilt self-contained engine installed for this pin and platform (`install-binary`) -- no .NET needed;
    3. the .NET SDK and this checkout's wrapper, built on demand -- a developer's machine and CI.
    """
    named = os.environ.get(ENGINE_ENV)
    if named:
        if os.path.isfile(named) and os.access(named, os.X_OK):
            return [named], f"{ENGINE_ENV}={named}"
        return None, f"{ENGINE_ENV} names {named}, which is not an executable file"
    prebuilt = os.path.join(installed_dir(), _exe_name())
    if os.path.isfile(prebuilt) and os.access(prebuilt, os.X_OK):
        return [prebuilt], f"the prebuilt engine {prebuilt}"
    dotnet = dotnet or find_dotnet()
    if dotnet:
        if not os.path.isfile(DLL):
            ok, msg = build(dotnet=dotnet)
            if not ok:
                return None, msg
        return [dotnet, DLL], f"the wrapper built here ({DLL})"
    return None, (f"no engine: no prebuilt one in {installed_dir()} (install-binary --from <zip>), and no .NET SDK to "
                  "build one (dotnet on PATH or ~/.dotnet/dotnet)")


def install_binary(source):
    """Put a prebuilt engine (a folder or a .zip holding `ResonalyzeEngine[.exe]`) where `engine_command` finds it."""
    import zipfile
    target = installed_dir()
    os.makedirs(target, exist_ok=True)
    if os.path.isdir(source):
        for name in os.listdir(source):
            shutil.copy2(os.path.join(source, name), os.path.join(target, name))
    elif zipfile.is_zipfile(source):
        with zipfile.ZipFile(source) as z:
            z.extractall(target)
    else:
        raise SystemExit(f"{source}: neither a folder nor a zip")
    exe = os.path.join(target, _exe_name())
    if not os.path.isfile(exe):
        raise SystemExit(f"{source}: holds no {_exe_name()} -- a build for another platform? this machine is {rid()}")
    os.chmod(exe, 0o755)
    return exe


def archive_name(engine_pin=None, runtime_id=None):
    """`resonalyze-engine-<pin>-<rid>.zip` -- the name hub `RELEASE-CHANNEL.md` §12 holds the release job to."""
    return f"resonalyze-engine-{engine_pin or ENGINE_PIN}-{runtime_id or rid()}.zip"


def _http_get(url, timeout=FETCH_TIMEOUT_S):
    """`(bytes, None)` or `(None, why)`. A 404 is a WHY, not an exception: a tag whose run attached nothing, and a
    platform nobody builds for, are both ordinary -- the caller then says which way it went and builds from the SDK."""
    import ssl
    import urllib.error
    import urllib.request
    try:
        import certifi
        context = ssl.create_default_context(cafile=certifi.where())
    except Exception:  # noqa: BLE001 -- no certifi: the system's store is what there is
        context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(url, timeout=timeout, context=context) as response:
            return response.read(), None
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}"
    except Exception as e:  # noqa: BLE001 -- a name that does not resolve, a proxy, a timeout: all "not reachable"
        return None, str(e) or e.__class__.__name__


def _sum_for(sums_text, name):
    """The digest `SHA256SUMS` records for `name`, or None. The job writes `sha256sum ./*.zip`, so the path is `./name`."""
    for line in (sums_text or "").splitlines():
        parts = line.split()
        if len(parts) == 2 and os.path.basename(parts[1]) == name:
            return parts[0].lower()
    return None


def fetch_binary(tag, get=_http_get):
    """Fetch THIS pin and platform's prebuilt engine from `tag`'s release, check it, install it.

    `{"status": ..., "detail": ...}`, and the status is the whole point:

    * `installed` -- the digest matched `SHA256SUMS` and the engine is where `engine_command` looks;
    * `absent` -- that release carries no archive for this pin and platform. Ordinary, not an error: the engine pin
      moves with the submodule rather than with the tag, and only three platforms are built. The SDK is the way then,
      and a caller must SAY which way it went rather than fall through in silence;
    * `unreachable` -- nothing answered.

    A file that ARRIVES and whose digest disagrees is REFUSED (`SystemExit`), never installed: the one outcome worse
    than no engine is a binary nobody can account for.
    """
    name = archive_name()
    base = f"{RELEASE_DOWNLOAD}/{tag}"
    sums, why = get(f"{base}/{SUMS_NAME}")
    if sums is None:
        status = "absent" if str(why).startswith("HTTP 404") else "unreachable"
        return {"status": status, "name": name, "tag": tag,
                "detail": f"no {SUMS_NAME} on {tag} ({why})" if status == "absent"
                          else f"{SUMS_NAME} on {tag} did not answer ({why})"}
    want = _sum_for(sums.decode("utf-8", "replace"), name)
    if not want:
        return {"status": "absent", "name": name, "tag": tag,
                "detail": f"{tag} carries no {name} (this machine is {rid()}, the engine pin {ENGINE_PIN})"}
    blob, why = get(f"{base}/{name}")
    if blob is None:
        status = "absent" if str(why).startswith("HTTP 404") else "unreachable"
        return {"status": status, "name": name, "tag": tag,
                "detail": f"{name} is listed in {SUMS_NAME} but did not download ({why})"}
    got = hashlib.sha256(blob).hexdigest()
    if got != want:
        raise SystemExit(f"{name} from {tag} does not match {SUMS_NAME}: {got} != {want} -- nothing was installed")
    with tempfile.TemporaryDirectory() as tmp:
        zip_path = os.path.join(tmp, name)
        with open(zip_path, "wb") as fh:
            fh.write(blob)
        exe = install_binary(zip_path)
    return {"status": "installed", "name": name, "tag": tag, "sha256": got, "exe": exe,
            "detail": f"{name} from {tag}, sha256 checked, in {installed_dir()}"}


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
    command, how = engine_command(dotnet)
    if command is None:
        return 2, None, how
    os.makedirs(out_dir, exist_ok=True)
    layout_path = os.path.join(out_dir, "layout.json")
    result_path = os.path.join(out_dir, "result.json")
    with open(layout_path, "w", encoding="utf-8") as fh:
        json.dump(layout, fh, indent=1, ensure_ascii=False)
    if os.path.exists(result_path):
        os.remove(result_path)
    r = subprocess.run([*command, layout_path, result_path, "--log", os.path.join(out_dir, "engine.log")],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    result = None
    if os.path.isfile(result_path):
        with open(result_path, encoding="utf-8") as fh:
            result = json.load(fh)
        result["pin"] = dict(pin(), engine=how)
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


def delay_tiers(profile, rows):
    """`(ceiling per tier in ms, how many tiers add up)` for the device.

    A Helix holds 20.82 ms on a driver output AND 20.82 ms on the virtual channel that feeds it, and the two add (the
    profile's `delay.scope`; the user, 2026-09-17: "they can be summed, on the rear for sure"). So an output fed by a
    virtual channel can be delayed up to the sum. Two tiers are counted only when the profile scopes the ceiling to a
    virtual channel too AND the project has virtual channels; otherwise one.
    """
    delay = (profile or {}).get("delay") or {}
    tier = delay.get("max_ms")
    scope = " ".join(str(x).lower() for x in delay.get("scope") or [])
    virtual = "virtual" in scope and any((r or {}).get("role") == "virtual" for r in rows or [])
    return (float(tier) if tier is not None else None), (2 if virtual else 1)


def split_notes(delay_result, layout):
    """A delay longer than one tier holds, split as the device takes it: the tier's ceiling on the output, the rest on
    the virtual channel that feeds it -- free only where that virtual channel feeds this output alone."""
    proc = (layout or {}).get("processor") or {}
    tier, tiers = proc.get("delayPerTierMs"), proc.get("delayTiers") or 1
    out = []
    if not tier or tiers < 2:
        return out
    for row in (delay_result or {}).get("result") or []:
        d = float(row["delayMs"])
        if d > tier + 0.005:
            out.append(f"{row['channel']}: {d:.2f} ms is more than one tier holds ({tier:g} ms) -- enter {tier:g} on the "
                       f"output and {d - tier:.2f} on the virtual channel that feeds it; free only when that virtual "
                       "channel feeds this output alone (the rear's does), otherwise every output it feeds moves too")
    return out


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
    tier_ms, tiers = delay_tiers(profile, rows)
    max_ms = ENGINE_DEFAULT_MAX_DELAY_MS if window_defaults else (tier_ms * tiers if tier_ms is not None else None)
    if max_ms is None:
        problems.append("no delay range on record -- the device profile's delay.max_ms (Resonalyze's catalog is no "
                        "substitute: without a range it assumes 50 ms)")
    layout = {
        "contract": LAYOUT_CONTRACT,
        "note": ("the window's defaults (the engine's own type readings, its 50 ms range)" if window_defaults
                 else "the skill's layout: types from the channel map, the device profile's delay range"),
        "dataDir": os.path.abspath(set_dir),
        "processor": {"model": " ".join(x for x in ((dsp or {}).get("vendor"), (dsp or {}).get("model")) if x) or None,
                      "sampleRateHz": int(rate or 0), "maxDelayMs": float(max_ms if max_ms is not None else 0),
                      "delayPerTierMs": tier_ms, "delayTiers": tiers},
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


# ---------------------------------------------------------------- the variants: the best within the limits, the wishes

#: The families the window's Auto crossover searches (Chebyshev is not among them), by the profile's code.
ENGINE_FAMILY = {"BW": "Butterworth", "LR": "LinkwitzRiley", "BE": "Bessel"}


def lattice(f):
    """`CrossoverAutoSetup.RoundToLattice`: 5 Hz steps under 100 Hz, 10 under 1 kHz, 50 above."""
    step = 5.0 if f < 100 else 10.0 if f < 1000 else 50.0
    return max(20.0, round(f / step) * step)


def floor_hz(codes, channels, xo):
    """The protective floor (1.1 x installed Fs, on the device's step) of the strictest fragile driver among `codes`,
    or None when none is fragile or no Fs is on record -- a floor nobody measured is not guessed."""
    worst = None
    for code in codes:
        row = channels.get(code) or {}
        if row.get("role") not in _xw.FRAGILE_ROLES:
            continue
        fs, _ = _xw._fs_of(row)
        if fs is not None and (worst is None or fs > worst):
            worst = fs
    if worst is None:
        return None
    f, _ = _xw._snap(math.ceil(round(_xw._cc.FS_FLOOR * worst, 6)), xo)
    return float(f)


def _engine_families(xo):
    names = [ENGINE_FAMILY[c] for c in ("BW", "LR", "BE") if xo is None or c in (xo.get("types") or {})]
    return names or list(ENGINE_FAMILY.values())


def _device_slopes(xo, families):
    if xo is None:
        return None
    code_of = {v: k for k, v in ENGINE_FAMILY.items()}
    slopes = set()
    for fam in families:
        for order in ((xo.get("types") or {}).get(code_of[fam]) or {}).get("orders_db_per_oct") or []:
            if order >= 12:
                slopes.add(int(order))
    return sorted(slopes) or None


def chain_pairs(result):
    """The front chain's junctions, low to high, as Auto crossover ordered the primary group: [(lower, upper)]."""
    for group in (result.get("autoCrossover") or {}).get("groups") or []:
        if group.get("primary"):
            order = group.get("chainOrder") or []
            return list(zip(order, order[1:]))
    return []


def _corner(prop_lower, prop_upper):
    lp, hp = (prop_lower or {}).get("lowPass"), (prop_upper or {}).get("highPass")
    return float((lp or hp or {}).get("frequencyHz") or 632.0)


#: The grid the pool's filter pairs are read on: 48 points per octave, 20 Hz to 20 kHz (`predict.grid`'s density).
_RERANK_GRID = None


def _rerank_grid():
    global _RERANK_GRID
    if _RERANK_GRID is None:
        import numpy as np
        _RERANK_GRID = np.geomspace(20.0, 20000.0, 480)
    return _RERANK_GRID


def rerank_pool(result, weight=None):
    """Resonalyze's ranked pool, re-ranked with the junction group-delay penalty (hub RES-014) -- TWO leaders.

    The harness exports the top 5 of `CrossoverAutoSetup.ProposeRanked`'s pool (`primaryRankedTop5`: whole-chain
    proposals with the engine's own `totalScore`, dB, lower is better). Each is read here junction by junction on the
    front chain: the two facing edges as filters alone (no drivers -- the term is about what the crossover does to
    timing), aligned as the filters themselves sum best (the pool carries no delays yet), and `dsp_math.
    junction_gd_swing` gives the swing against the Blauert & Laws threshold. `experimental_score = totalScore +
    the penalties, summed over the junctions`. Returns None without a pool; else `{engine_leader, experimental_leader,
    changed, rows, note}` -- the ENGINE's leader stays what the run continues with, the experimental one is shown
    beside it (the user, 2026-09-17: after the candidates are computed, show Resonalyze's leader AND the alternative
    leader by our own, still experimental, logic). A junction on a family the skill cannot model is not scored and
    the row says so.
    """
    import numpy as np
    import dsp_math
    ac = result.get("autoCrossover") or {}
    pool, pairs = ac.get("primaryRankedTop5") or [], chain_pairs(result)
    if not pool or not pairs:
        return None
    f = _rerank_grid()
    weight = dsp_math.GD_PENALTY_DB_PER_MS if weight is None else weight
    rows = []
    for rank, cand in enumerate(pool, start=1):
        props = {p["block"]: p for p in cand.get("proposals") or []}
        junctions, unread, penalty = [], [], 0.0
        for lower, upper in pairs:
            lp, hp = (props.get(lower) or {}).get("lowPass"), (props.get(upper) or {}).get("highPass")
            if not lp or not hp:
                continue                                   # no facing pair of edges: nothing the crossover does here
            fam_lo, fam_hi = FAMILY_CODE.get(lp["family"], lp["family"]), FAMILY_CODE.get(hp["family"], hp["family"])
            if fam_lo not in ENGINE_FAMILY or fam_hi not in ENGINE_FAMILY:
                unread.append(f"{lower} ↔ {upper}: {lp['family']}/{hp['family']} is not modelled here")
                continue
            fc = math.sqrt(float(lp["frequencyHz"]) * float(hp["frequencyHz"]))
            band = (fc / 2.0, fc * 2.0)
            h_lo = dsp_math.xo_response(f, float(lp["frequencyHz"]), int(lp["slopeDbPerOctave"]), "lp", fam_lo)
            h_hi = dsp_math.xo_response(f, float(hp["frequencyHz"]), int(hp["slopeDbPerOctave"]), "hp", fam_hi)
            pol, tau = dsp_math.align_sum_loss(f, h_lo, h_hi, band, max_delay_ms=3.0, step_ms=0.01)[:2]
            gd = dsp_math.junction_gd_swing(f, h_lo + pol * h_hi * np.exp(-2j * np.pi * f * tau / 1000.0), band,
                                            fc_hz=fc, weight=weight)
            junctions.append({"lower": lower, "upper": upper, "fc_hz": round(fc, 1), "lowPass": lp, "highPass": hp,
                              "swing_ms": gd["swing_ms"], "threshold_ms": gd["threshold_ms"], "over_ms": gd["over_ms"],
                              "penalty_db": gd["penalty_db"], "clamped": gd["clamped"]})
            penalty += gd["penalty_db"] or 0.0
        total = float(cand.get("totalScore") or 0.0)
        rows.append({"rank_engine": rank, "total_score_db": total, "magnitude_score_db": cand.get("magnitudeScore"),
                     "is_conventional_24": bool(cand.get("isConventional24")), "gd_penalty_db": round(penalty, 3),
                     "experimental_score_db": round(total + penalty, 4), "junctions": junctions, "unread": unread,
                     "proposals": cand.get("proposals") or []})
    leader = min(rows, key=lambda r: (r["experimental_score_db"], r["rank_engine"]))
    return {"engine_leader": rows[0], "experimental_leader": leader, "changed": leader is not rows[0], "rows": rows,
            "note": (f"the engine's pool as its harness exports it: the top {len(rows)} of ProposeRanked by its own "
                     f"score; the penalty is {weight:g} dB per ms of group-delay swing over the Blauert & Laws "
                     "threshold at each front-chain junction (clamped to 3.2 ms below 500 Hz), read on the filters "
                     "alone, aligned as they sum best. Experimental (hub RES-014): shown beside the engine's leader, "
                     "not applied -- the run continues with the engine's")}


def plan_repairs(result, layout, checks, channels, xo):
    """What must change before the engine's best can be shown: `(repairs, fixes, notes)`.

    A junction of the front chain whose edge broke a limit (REFUSED: under the fragile driver's floor; ADJUSTED: a
    family or slope the device does not have) is searched again by the junction tuner inside the limits -- the
    device's families and slopes, the corner window from the floor up -- and its best is written back (`repairs`).
    A lone block's edge (a centre, a rear fill) is set to the nearest allowed setting (`fixes`). An edge nobody can
    check is left as it is and said to be unchecked.
    """
    by = {(c["block"], c["edge"]): c for c in checks}
    props = {p["block"]: p for p in (result.get("autoCrossover") or {}).get("result") or []}
    blocks = {b["name"]: b for b in layout.get("blocks") or []}
    families = _engine_families(xo)
    slopes = _device_slopes(xo, families)
    repairs, fixes, notes, in_chain = [], {}, [], set()
    for lower, upper in chain_pairs(result):
        in_chain.update((lower, upper))
        hp, lp = by.get((upper, "high-pass")), by.get((lower, "low-pass"))
        broken = [c for c in (hp, lp) if c and c["verdict"] in ("REFUSED", "ADJUSTED")]
        if not broken:
            continue
        current = _corner(props.get(lower), props.get(upper))
        floor = floor_hz(((blocks.get(upper) or {}).get("channels") or {}).values(), channels, xo)
        lo, hi = lattice(current / math.sqrt(2)), lattice(current * math.sqrt(2))
        low = max(lo, floor) if floor else lo
        high = max(hi, lattice(low * math.sqrt(2)))
        repairs.append({"lower": lower, "upper": upper,
                        "purpose": "; ".join(f"{c['block']} {c['edge']} {c['setting']} {c['verdict']}" for c in broken),
                        "tune": {"families": families, "slopes": slopes, "minHz": float(low), "maxHz": float(high)}})
    for c in checks:
        if c["block"] in in_chain or c["verdict"] not in ("REFUSED", "ADJUSTED"):
            continue
        a = c.get("allowed") or {}
        fam = ENGINE_FAMILY.get(a.get("family"))
        if not (fam and a.get("order_db") and a.get("f_hz")):
            notes.append(f"{c['block']} {c['edge']} {c['setting']}: {c['verdict']} and no setting the engines can hold "
                         "is named -- left for the tuner")
            continue
        key = "highPass" if c["edge"] == "high-pass" else "lowPass"
        fixes.setdefault(c["block"], {})[key] = {"family": fam, "frequencyHz": float(a["f_hz"]),
                                                 "slopeDbPerOctave": int(a["order_db"])}
    return repairs, fixes, notes


def _block_of_role(layout, role, chain):
    names = [b["name"] for b in layout.get("blocks") or [] if b.get("role") == role]
    inside = [n for n in names if n in chain]
    return (inside or names or [None])[0]


def wish_items(rows, layout, result, channels, xo):
    """The tuner's checked wishes as junction items: `(items, not_computed)`.

    A wish with a corner is a PROBE -- the setting read against the best on one band, each after its own delay. A wish
    with a family or slope and no corner (or a range) is a TUNE -- the best that family and slope can do at that
    junction. A wish that broke a limit, that nobody can check, or that names no junction of this chain is not
    computed, and says why.
    """
    chain = [x for pair in chain_pairs(result) for x in pair]
    order = list(dict.fromkeys(chain))
    items, skipped = [], []
    for row in rows:
        said = row.get("clause", "").strip()
        if row["verdict"] in ("REFUSED", "UNKNOWN", "UNSURE", "UNCHECKED"):
            skipped.append((said, row["verdict"], "; ".join(row.get("why") or [])))
            continue
        roles = row.get("junction") or []
        if len(roles) == 1:
            upper = _block_of_role(layout, roles[0], order)
            lower = order[order.index(upper) - 1] if upper in order and order.index(upper) > 0 else None
            only_high = True
        else:
            lower, upper = _block_of_role(layout, roles[0], order), _block_of_role(layout, roles[-1], order)
            only_high = False
        if not lower or not upper or (lower, upper) not in chain_pairs(result):
            skipped.append((said, row["verdict"], f"{' ↔ '.join(roles)} is not a junction of the front chain "
                                                  f"({' → '.join(order) or 'none'})"))
            continue
        allowed = row.get("allowed") or {}
        fam = ENGINE_FAMILY.get(allowed.get("family")) if allowed.get("family") else None
        if allowed.get("family") and not fam:
            skipped.append((said, row["verdict"], f"{allowed['family']} is not a family the engines search (BW, LR, BE)"))
            continue
        order_db, f = allowed.get("order_db"), allowed.get("f_hz")
        f_range = (row.get("wish") or {}).get("f_range_hz")
        item = {"lower": lower, "upper": upper, "purpose": f"wish: {said}", "verdict": row["verdict"]}
        if f is not None and not f_range and fam and order_db:
            edge = {"family": fam, "frequencyHz": float(f), "slopeDbPerOctave": int(order_db)}
            item["probe"] = [{"label": said, "highPass": edge, **({} if only_high else {"lowPass": edge})}]
        else:
            floor = floor_hz(((next((b for b in layout["blocks"] if b["name"] == upper), {})).get("channels") or {}).values(),
                             channels, xo)
            tune = {"families": [fam] if fam else _engine_families(xo),
                    "slopes": [int(order_db)] if order_db else _device_slopes(xo, [fam] if fam else _engine_families(xo))}
            if f_range:
                tune["minHz"], tune["maxHz"] = float(f_range[0]), float(f_range[1])
            if floor:
                tune["minHz"] = max(float(tune.get("minHz") or 0.0), floor)
            item["tune"] = tune
        items.append(item)
    return items, skipped


def final_proposals(result):
    """The settings every block ends with, in `autoCrossover.result`'s shape, from `settingsFinal` (the left side:
    a crossover is one filter for both)."""
    out = []
    for row in result.get("settingsFinal") or []:
        left = row.get("left") or {}
        out.append({"block": row["block"], "kind": left.get("crossover"), "highPass": left.get("highPass"),
                    "lowPass": left.get("lowPass"), "gainDb": left.get("gainDb")})
    return out


def _on_edge(edge, window):
    """A best at the end of its search window: the window may be what stopped it."""
    if not edge or not window:
        return False
    f = float(edge["frequencyHz"])
    return any(abs(f - float(w)) <= (5.0 if w < 100 else 10.0 if w < 1000 else 50.0) for w in window)


def wish_costs(result, layout=None, channels=None, xo=None):
    """Per junction item: what the wish costs against what stands, in dB of the tuner's score (lower is better).
    A tune's best is held to the same limits as any proposal (`check_setting` on its high-pass), and a best found at
    the end of its search window is marked so."""
    blocks = {b["name"]: b for b in (layout or {}).get("blocks") or []}
    out = []
    for j in result.get("junctions") or []:
        entry = {"purpose": j.get("purpose"), "lower": j["lower"], "upper": j["upper"], "error": j.get("error")}
        probe = j.get("probe")
        if probe:
            base, *rest = probe["entries"]
            for e in rest:
                shared = {s["side"]: s["scoreDb"] for s in e["sharedBandSides"]}
                base_shared = {s["side"]: s["scoreDb"] for s in base["sharedBandSides"]}
                after = {a["side"]: a["lossDb"] for a in e["afterDelay"]}
                base_after = {a["side"]: a["lossDb"] for a in base["afterDelay"]}
                entry.setdefault("probes", []).append({
                    "label": e["label"], "unavailable": e.get("unavailable"),
                    "scoreDeltaDb": {k: round(shared[k] - base_shared[k], 2) for k in shared if k in base_shared},
                    "afterDelayLossDb": {k: (after.get(k), base_after.get(k)) for k in after}})
        tune = j.get("tune")
        if tune:
            best_high = tune["best"].get("highPass")
            limit = None
            if best_high and channels is not None:
                codes = [c for c in ((blocks.get(j["upper"]) or {}).get("channels") or {}).values() if c in channels]
                fam = FAMILY_CODE.get(best_high["family"], best_high["family"])
                limit = _xw.check_setting({c: (None, c) for c in codes}, fam, int(best_high["slopeDbPerOctave"]),
                                          float(best_high["frequencyHz"]), channels, xo)
            entry["tune"] = {"best": (tune["best"].get("lowPass") or best_high),
                             "limit": limit, "atWindowEdge": _on_edge(best_high or tune["best"].get("lowPass"),
                                                                     tune.get("windowHz")),
                             "scoreDeltaDb": round(tune["best"]["rankingScoreDb"] - tune["current"]["rankingScoreDb"], 2)
                             if tune["best"].get("rankingScoreDb") is not None and tune["current"].get("rankingScoreDb") is not None
                             else None,
                             "windowHz": tune.get("windowHz")}
        out.append(entry)
    return out


def variants(project_dir, set_dir, wishes=None, dotnet=None, out_dir=None, **kw):
    """Phase 1's crossover step at the desk: the engine's best, held to the limits and repaired inside them, with its
    delays; then each wish read against it. Two runs of the wrapper: Auto crossover alone (fast), then the repairs,
    Auto delay and the wishes on the crossovers it proposed. Returns a dict for `render_variants` and the JSON."""
    layout, notes, problems, channels, xo = build_layout(project_dir, set_dir, **kw)
    return variants_from(layout, channels, xo, wishes, notes, problems, dotnet, out_dir,
                         fill_given=kw.get("rear_fill_ms") is not None)


def variants_from(layout, channels, xo, wishes=None, notes=(), problems=(), dotnet=None, out_dir=None, fill_given=False):
    """`variants` on a layout already built -- the project's facts passed in rather than read from a folder.

    When Auto delay cannot fit the device and the rear fill is the default rather than the tuner's, the run is repeated
    once with the largest fill that fits, and says so; a fill the tuner gave is not changed -- the fill that would fit
    is named instead."""
    out = {"layout": layout, "notes": list(notes), "problems": list(problems)}
    if problems:
        return out
    out_dir = out_dir or tempfile.mkdtemp(prefix="resonalyze-variants-")
    first = json.loads(json.dumps(layout))
    first["autoDelay"]["run"] = False
    rc, result_a, err = run_engine(first, os.path.join(out_dir, "1-crossover"), dotnet)
    out.update(rc_crossover=rc, crossover=result_a)
    if result_a is None or (result_a.get("autoCrossover") or {}).get("error"):
        out["problems"] = [f"Auto crossover did not run (exit {rc}): "
                           f"{((result_a or {}).get('autoCrossover') or {}).get('error') or err.strip()[-300:]}"]
        return out
    checks_a = check_result(result_a, layout, channels, xo)
    out["rerank"] = rerank_pool(result_a)
    repairs, fixes, repair_notes = plan_repairs(result_a, layout, checks_a, channels, xo)
    rows = _xw.check_wishes(wishes, channels, xo) if wishes else []
    items, skipped = wish_items(rows, layout, result_a, channels, xo)
    out.update(checks_crossover=checks_a, repairs_planned=repairs, fixes=fixes, wishes=rows, wishes_skipped=skipped)
    out["notes"] += repair_notes

    second = json.loads(json.dumps(layout))
    props = {p["block"]: p for p in result_a["autoCrossover"]["result"]}
    order = result_a["autoCrossover"].get("blockOrderAfterReorder") or [b["name"] for b in second["blocks"]]
    second["blocks"].sort(key=lambda b: order.index(b["name"]) if b["name"] in order else len(order))
    for b in second["blocks"]:
        p = props[b["name"]]
        crossover = {"kind": p["kind"], "highPass": p.get("highPass"), "lowPass": p.get("lowPass")}
        for key, edge in (fixes.get(b["name"]) or {}).items():
            crossover[key] = edge
        b["crossover"], b["gainDb"] = crossover, p["gainDb"]
    second["autoCrossover"] = {"run": False}
    second["repairs"], second["junctions"] = repairs, items
    rc, result_b, err = run_engine(second, os.path.join(out_dir, "2-delays-and-wishes"), dotnet)
    first_fill, needed = second["autoDelay"]["rearFillOffsetMs"], None
    for _ in range(3):     # a repair moves the delays, so the fill that fits is read again after each run
        if result_b is None or rc != EXIT_REFUSED or fill_given:
            break
        refused = result_b.get("autoDelayAfterRepairs") or result_b.get("autoDelay") or {}
        fill = fill_that_fits(refused.get("overRange"))
        if fill is None or fill >= second["autoDelay"]["rearFillOffsetMs"]:
            break
        needed = refused["overRange"]
        second["autoDelay"]["rearFillOffsetMs"] = fill
        rc, result_b, err = run_engine(second, os.path.join(out_dir, "2-delays-and-wishes"), dotnet)
    if needed is not None:
        out["notes"].append(f"rear fill {first_fill:g} → {second['autoDelay']['rearFillOffsetMs']:g} ms: with "
                            f"{first_fill:g} the rear did not fit the device's {needed['limitMs']:g} ms -- the fill was "
                            "the default, so the desk took the largest that fits; the tuner may set another")
    out.update(rc_delays=rc, delays=result_b, out_dir=out_dir)
    if result_b is None:
        out["problems"] = [f"the second run wrote nothing (exit {rc}): {err.strip()[-300:]}"]
        return out
    if rc != 0:
        unread = [what for what, planned, key in (("the repairs", repairs, "repairs"), ("the wishes", items, "junctions"))
                  if planned and result_b.get(key) is None]
        if unread:
            out["notes"].append(f"{' and '.join(unread)} were not read: Auto delay refused, and a junction read at "
                                "delays that were never computed would mislead")
    out["checks_final"] = check_result({"autoCrossover": {"result": final_proposals(result_b)}}, second, channels, xo)
    out["costs"] = wish_costs(result_b, second, channels, xo)
    final_delay = result_b.get("autoDelayAfterRepairs") or result_b.get("autoDelay")
    out["notes"] += notes_on({"autoCrossover": result_a.get("autoCrossover"), "autoDelay": final_delay})
    out["notes"] += split_notes(final_delay, second)
    return out


def _edge_short(e):
    return f"{FAMILY_CODE.get(e['family'], e['family'])}{e['slopeDbPerOctave']} {float(e['frequencyHz']):g} Hz" if e else "--"


def _junction_short(candidate):
    """One junction's two facing edges: one label when they are the same filter, both when they differ."""
    lp, hp = candidate.get("lowPass"), candidate.get("highPass")
    return _edge_short(lp or hp) if (lp == hp or not lp or not hp) else f"{_edge_short(lp)} | {_edge_short(hp)}"


def render_variants(v):
    lines = []
    if v.get("problems"):
        return "\n".join(f"  ✗ {p}" for p in v["problems"])
    b = v.get("delays") or {}
    delay = b.get("autoDelayAfterRepairs") or b.get("autoDelay") or {}
    lines.append("  THE BEST WITHIN THE LIMITS -- Resonalyze's Auto crossover, every edge held to this car's limits"
                 + (", repaired where it broke one" if v.get("repairs_planned") or v.get("fixes") else ""))
    lines.append(f"  {'block':12}{'high-pass':20}{'low-pass':20}{'gain':>6}")
    for p in final_proposals(b):
        lines.append(f"  {p['block']:12}{_edge_short(p.get('highPass')):20}{_edge_short(p.get('lowPass')):20}"
                     f"{float(p.get('gainDb') or 0):>+6.1f}")
    for r in b.get("repairs") or []:
        t = r.get("tune") or {}
        if r.get("error") or not t:
            lines.append(f"  ! repair {r['lower']} ↔ {r['upper']} did not run: {r.get('error')}")
            continue
        cur, best = t["current"], t["best"]
        delta = (best.get("rankingScoreDb") or 0) - (cur.get("rankingScoreDb") or 0)
        lines.append(f"  repaired {r['lower']} ↔ {r['upper']}: {_junction_short(cur)} → {_junction_short(best)} "
                     f"({r.get('purpose')}); the score {delta:+.2f} dB")
    for block, edges in (v.get("fixes") or {}).items():
        lines.append(f"  set {block}: " + ", ".join(f"{k} {_edge_short(e)}" for k, e in edges.items()) + " (the nearest allowed)")
    flagged = [c for c in v.get("checks_final") or [] if c["verdict"] not in ("OK",)]
    if flagged:
        lines.append("  still to settle:")
        lines += [f"    {c['block']} {c['edge']} {c['setting']} -- {c['verdict']}: {'; '.join(c['why'])}" for c in flagged]
    if delay.get("result"):
        lines.append("")
        lines.append(f"  delays ({'after the repairs' if b.get('autoDelayAfterRepairs') else 'Auto delay'}; scene offset "
                     f"{delay['request']['sceneOffsetMs']:g} ms, rear fill {delay['request']['rearFillOffsetMs']:g} ms)")
        for row in delay["result"]:
            d = row.get("decision") or {}
            lines.append(f"  {row['channel']:22}{row['delayMs']:>7.2f} ms  {'inverted' if row['invertPolarity'] else 'normal':9}"
                         f"{d.get('kind', '')}{', ' + d['confidence'] if d.get('confidence') else ''}")
    elif delay.get("error"):
        lines.append(f"  Auto delay refused: {delay['error']}")
    rr = v.get("rerank")
    if rr:
        lines += ["", "  TWO LEADERS -- the engine's, and the alternative by our EXPERIMENTAL ranking (hub RES-014: the crossover "
                      "pair's group-delay swing against the Blauert & Laws threshold, 1 dB per ms over it; lower score is better)"]
        lines.append(f"  {'':3}{'engine rank':>12}{'engine dB':>11}{'gd penalty':>12}{'experimental':>14}  junctions: swing/threshold ms")
        for r in rr["rows"]:
            tag = ("E" if r is rr["engine_leader"] else " ") + ("X" if r is rr["experimental_leader"] else " ")
            js = "; ".join(f"{j['lower'].split(' ', 1)[-1]}↔{j['upper'].split(' ', 1)[-1]} {j['swing_ms']:.1f}/{j['threshold_ms']:.1f}"
                           + ("!" if j["over_ms"] else "") + ("c" if j["clamped"] else "")
                           for j in r["junctions"] if j["swing_ms"] is not None) or "--"
            lines.append(f"  {tag:3}{r['rank_engine']:>12}{r['total_score_db']:>11.2f}{r['gd_penalty_db']:>12.2f}"
                         f"{r['experimental_score_db']:>14.2f}  {js}" + (f"  ({'; '.join(r['unread'])})" if r["unread"] else ""))
        if rr["changed"]:
            x = rr["experimental_leader"]
            lines.append(f"  the experimental leader is the engine's #{x['rank_engine']} -- its edges, for the tuner to take instead:")
            for p in x["proposals"]:
                lines.append(f"    {p['block']:12}{_edge_short(p.get('highPass')):20}{_edge_short(p.get('lowPass')):20}")
        else:
            lines.append("  both rankings agree on the leader")
        lines.append(f"  E = the engine's leader (what this run continues with) · X = the experimental leader · ! = over the "
                     f"threshold · c = the below-500 Hz clamp. {rr['note'].split('. ', 1)[0]}.")
    if v.get("costs") or v.get("wishes_skipped"):
        lines += ["", "  THE WISHES, against the best (dB of the junction score; lower is better)"]
    for c in v.get("costs") or []:
        head = f"  {c['purpose']} -- {c['lower']} ↔ {c['upper']}"
        if c.get("error"):
            lines.append(f"{head}: not read ({c['error']})")
            continue
        for pr in c.get("probes") or []:
            per_side = ", ".join(f"{k} {d:+.2f}" for k, d in pr["scoreDeltaDb"].items())
            after = ", ".join(f"{k} {w:+.2f} vs {b_:+.2f}" for k, (w, b_) in pr["afterDelayLossDb"].items()
                              if w is not None and b_ is not None)
            lines.append(f"{head}: {per_side} on the shared band; the sum loss after its own delay {after}")
        if c.get("tune"):
            t = c["tune"]
            delta = "n/a" if t["scoreDeltaDb"] is None else f"{t['scoreDeltaDb']:+.2f} dB"
            lines.append(f"{head}: the best of that wish is {_edge_short(t['best'])}, {delta} against what stands "
                         f"(searched {t['windowHz'][0]:g}-{t['windowHz'][1]:g} Hz"
                         + (", found at the window's edge" if t.get("atWindowEdge") else "") + ")")
            lim = t.get("limit")
            if lim and lim["verdict"] != "OK":
                lines.append(f"      {lim['verdict']}: {'; '.join(lim['why'])}")
    for said, verdict, why in v.get("wishes_skipped") or []:
        lines.append(f"  {said or '(a clause)'} -- {verdict}, not computed: {why}")
    if v.get("notes"):
        lines.append("")
        lines += [f"  ! {n}" for n in v["notes"]]
    lines += ["", "  The engine proposes; nothing is entered without the tuner's OK."]
    return "\n".join(lines)


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
    """A synthetic sub + three-way front through both passes: Auto crossover, the repairs inside the limits, Auto delay,
    and a wish read against the best. It builds, runs, and comes back sane."""
    import numpy as np
    from scipy import signal

    import resonalyze_ir as _ri
    fs, n, pre = 96000, 1 << 16, 1 << 14
    rng = np.random.default_rng(7)
    drivers = {  # code: (role, installed Fs, arrival ms, high-pass Hz or None, low-pass Hz or None)
        "sw": ("sub", 30.0, 5.0, 25.0, 120.0),
        "w-L": ("woofer", 45.0, 3.0, 45.0, 1500.0), "w-R": ("woofer", 45.0, 3.4, 45.0, 1500.0),
        "m-L": ("midrange", 150.0, 2.8, 250.0, 9000.0), "m-R": ("midrange", 150.0, 3.2, 250.0, 9000.0),
        "tw-L": ("tweeter", 1600.0, 2.6, 1800.0, None), "tw-R": ("tweeter", 1600.0, 3.0, 1800.0, None),
    }
    xo = {"types": {"BE": {"orders_db_per_oct": [6, 12, 18, 24, 30, 36, 42]},
                    "BW": {"orders_db_per_oct": [6, 12, 18, 24, 30, 36, 42]},
                    "LR": {"orders_db_per_oct": [12, 24, 36]}}, "range": [20.0, 20480.0], "step": 1.0}
    with tempfile.TemporaryDirectory() as tmp:
        set_dir = os.path.join(tmp, "set")
        os.makedirs(set_dir)
        files = {}
        for code, (role, _fs, arrival, hp, lp) in drivers.items():
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
        rows = [{"code": c, "role": r, "fs_hz": {"value": f}} for c, (r, f, *_rest) in drivers.items()]
        channels = {r["code"]: r for r in rows}
        solos, rew, problems = read_set(set_dir)
        layout, notes, more = layout_from(rows, {"wheel": "LHD"}, {"dsp_processing_rate_hz": 96000},
                                          {"delay": {"max_ms": 20.0}}, solos, rew, set_dir)
        assert not problems and not more, (problems, more)
        v = variants_from(layout, channels, xo, wishes="BE4 між мідом і твітером на 2400", notes=notes,
                          dotnet=dotnet, out_dir=os.path.join(tmp, "out"))
        assert not v["problems"], v["problems"]
        b = v["delays"]
        assert v["rc_delays"] == 0 and b["contract"] == RESULT_CONTRACT, (v["rc_delays"], json.dumps(b)[:600])
        assert {p["block"] for p in v["crossover"]["autoCrossover"]["result"]} == {"A Sub", "B Woofer", "C Mid", "D Tweeter"}
        for r in b.get("repairs") or []:
            assert not r.get("error") and r["tune"]["applied"], r
        assert not [c for c in v["checks_final"] if c["verdict"] == "REFUSED"], v["checks_final"]
        delay = b.get("autoDelayAfterRepairs") or b["autoDelay"]
        delays = {r["channel"]: r["delayMs"] for r in delay["result"]}
        assert len(delays) == 7 and all(0.0 <= d <= 20.0 for d in delays.values()), delays
        # the tweeter arrives 0.4 ms before the woofer on its side, and a woofer's low-pass only adds lag: it waits
        assert delays["D Tweeter L"] > delays["B Woofer L"], delays
        probes = [pr for c in v["costs"] for pr in c.get("probes") or []]
        assert probes and set(probes[0]["scoreDeltaDb"]) == {"left", "right"}, v["costs"]
        echo(render_variants(v))
        echo(f"  repairs planned: {len(v['repairs_planned'])}, fixes: {len(v['fixes'])}")
    echo("smoke[resonalyze_engine] OK -- a synthetic sub + three-way front through both passes: a proposal per block, "
         "every repair applied and nothing left under a floor, seven delays inside the range with the early tweeter "
         "held back, and the wish read on both sides against the best")
    return 0


# ---------------------------------------------------------------- selftest (offline, no .NET)

def _selftest():
    assert driver_type("woofer", True) == "Midbass" and driver_type("woofer", False) == "Woofer"
    recorded = pin()["recorded"]
    assert recorded is None or recorded.startswith(ENGINE_PIN), (recorded, ENGINE_PIN)   # the constant follows the submodule
    assert rid().split("-")[0] in ("win", "osx", "linux") and installed_dir().endswith(os.path.join(ENGINE_PIN, rid()))
    saved = os.environ.get(ENGINE_ENV)
    try:
        os.environ[ENGINE_ENV] = os.path.join(tempfile.gettempdir(), "no-such-engine")
        command, how = engine_command()
        assert command is None and "not an executable" in how, how
    finally:
        if saved is None:
            os.environ.pop(ENGINE_ENV, None)
        else:
            os.environ[ENGINE_ENV] = saved
    assert driver_type("center", True) == "Midrange" and driver_type("rear", True) == "Woofer"

    # ── fetching the prebuilt engine from a tag's release (TODO S-020; hub `RELEASE-CHANNEL.md` §12) ──
    # The network is faked. What is held here: the NAME is computed from the pin and this machine, a
    # file that does not match `SHA256SUMS` is refused rather than installed, and "this release has
    # none for you" is an ANSWER -- the installers print it and build from the SDK instead.
    import io as _io
    import zipfile as _zipfile
    _buf = _io.BytesIO()
    with _zipfile.ZipFile(_buf, "w") as _z:
        _z.writestr(_exe_name(), "#!/bin/sh\nexit 0\n")
        _z.writestr("License.md", "the fork's licence rides inside the archive")
    _archive = _buf.getvalue()
    _name = archive_name()
    assert _name == f"resonalyze-engine-{ENGINE_PIN}-{rid()}.zip", _name
    _digest = hashlib.sha256(_archive).hexdigest()
    # `sha256sum ./*.zip` writes the path as `./<name>`, and the release carries the other platforms too.
    _sums = (f"{_digest}  ./{_name}\n"
             f"{'0' * 64}  ./resonalyze-engine-{ENGINE_PIN}-somewhere-else.zip\n").encode("utf-8")

    def _server(sums_reply, zip_reply):
        def get(url, timeout=None):
            if url.endswith(SUMS_NAME):
                return sums_reply
            return zip_reply if url.endswith(_name) else (None, "HTTP 404")
        return get

    def _with_temp_home(fn):
        real = globals()["installed_dir"]
        with tempfile.TemporaryDirectory() as home:
            globals()["installed_dir"] = lambda: os.path.join(home, "engines", ENGINE_PIN, rid())
            try:
                return fn(), home
            finally:
                globals()["installed_dir"] = real

    def _installing():                     # the checks live inside: the temporary home is gone on the way out
        got = fetch_binary("v9.9.9", get=_server((_sums, None), (_archive, None)))
        return dict(got, exe_there=os.path.isfile(got["exe"]), exe_name=os.path.basename(got["exe"]),
                    licence_there=os.path.isfile(os.path.join(installed_dir(), "License.md")))
    got, _ = _with_temp_home(_installing)
    assert got["status"] == "installed" and got["sha256"] == _digest and got["name"] == _name, got
    assert got["exe_there"] and got["exe_name"] == _exe_name() and got["licence_there"], got

    # A file that ARRIVES and does not match is the one case that must not degrade quietly.
    def _mismatched():
        try:
            fetch_binary("v9.9.9", get=_server((_sums, None), (b"another build entirely", None)))
        except SystemExit as e:
            return str(e), glob.glob(os.path.join(installed_dir(), "*"))
        raise AssertionError("a zip that does not match SHA256SUMS was accepted")
    (said, left), _ = _with_temp_home(_mismatched)
    assert SUMS_NAME in said and "nothing was installed" in said, said
    assert not left, left
    # A tag whose run attached nothing, a pin no archive was built for, a platform nobody builds:
    # one answer, and it names this machine so the line a person reads says why.
    absent, _ = _with_temp_home(lambda: fetch_binary("v3.0.56", get=_server((None, "HTTP 404"), (None, "HTTP 404"))))
    assert absent["status"] == "absent" and SUMS_NAME in absent["detail"], absent
    unlisted, _ = _with_temp_home(lambda: fetch_binary("v9.9.9", get=_server((b"%s  ./nothing-of-ours.zip\n" % (b"0" * 64), None), (None, "HTTP 404"))))
    assert unlisted["status"] == "absent" and rid() in unlisted["detail"] and ENGINE_PIN in unlisted["detail"], unlisted
    down, _ = _with_temp_home(lambda: fetch_binary("v9.9.9", get=_server((None, "<urlopen error [Errno 8]>"), (None, "x"))))
    assert down["status"] == "unreachable", down
    # Listed, but the file itself does not come down: still not an error to stop an install over.
    half, _ = _with_temp_home(lambda: fetch_binary("v9.9.9", get=_server((_sums, None), (None, "HTTP 404"))))
    assert half["status"] == "absent" and _name in half["detail"], half

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
        # two delay tiers add: an output and the virtual channel feeding it (the Helix: 20.82 + 20.82)
        helix = {"delay": {"max_ms": 20.82, "scope": ["per driver output", "per virtual channel"]}}
        assert delay_tiers(helix, rows) == (20.82, 2) and delay_tiers(helix, [r for r in rows if r["role"] != "virtual"]) == (20.82, 1)
        tl2, _, _ = layout_from(rows, car, dsp, helix, solos, rew, tmp, include_hidden=True)
        assert tl2["processor"]["maxDelayMs"] == 41.64 and tl2["processor"]["delayTiers"] == 2, tl2["processor"]
        split = split_notes({"result": [{"channel": "F Rear L", "delayMs": 23.67}, {"channel": "C Mid L", "delayMs": 6.1}]}, tl2)
        assert len(split) == 1 and "enter 20.82 on the output and 2.85 on the virtual channel" in split[0], split
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

    # the repairs: a front-chain corner under a floor is searched again from the floor up, on the device's families
    # and slopes; a lone centre's corner under its floor is set to the nearest allowed; the corner lattice is the engine's
    assert lattice(212.0) == 210.0 and lattice(97.0) == 95.0 and lattice(1760.0) == 1750.0 and lattice(12.0) == 20.0
    ch2 = dict(channels, c={"code": "c", "role": "center", "fs_hz": {"value": 900.0}})
    assert floor_hz(["m-L", "m-R"], ch2, xo) == 217.0 and floor_hz(["w-L"], ch2, xo) is None
    assert _device_slopes(xo, ["Butterworth", "LinkwitzRiley", "Bessel"]) == [12, 18, 24, 30, 36, 42]
    lay2 = {"blocks": [{"name": "A Sub", "role": "sub", "channels": {"left": "sw"}},
                       {"name": "B Woofer", "role": "woofer", "channels": {"left": "w-L", "right": "w-R"}},
                       {"name": "C Mid", "role": "midrange", "channels": {"left": "m-L", "right": "m-R"}},
                       {"name": "D Tweeter", "role": "tweeter", "channels": {"left": "tw-L", "right": "tw-R"}},
                       {"name": "E Centre", "role": "center", "channels": {"left": "c"}}]}
    res_a = {"autoCrossover": {
        "groups": [{"group": "FrontChain", "primary": True, "chainOrder": ["A Sub", "B Woofer", "C Mid", "D Tweeter"]},
                   {"group": "Center", "primary": False, "chainOrder": ["E Centre"]}],
        "result": [{"block": "A Sub", "kind": "LowPass", "lowPass": edge("LinkwitzRiley", 24, 80.0), "highPass": None, "gainDb": 0},
                   {"block": "B Woofer", "kind": "BandPass", "highPass": edge("LinkwitzRiley", 24, 80.0),
                    "lowPass": edge("LinkwitzRiley", 24, 200.0), "gainDb": -2.2},
                   {"block": "C Mid", "kind": "BandPass", "highPass": edge("LinkwitzRiley", 24, 200.0),
                    "lowPass": edge("LinkwitzRiley", 24, 2300.0), "gainDb": -3.5},
                   {"block": "D Tweeter", "kind": "HighPass", "highPass": edge("LinkwitzRiley", 24, 2300.0), "lowPass": None, "gainDb": 0},
                   {"block": "E Centre", "kind": "HighPass", "highPass": edge("LinkwitzRiley", 24, 900.0), "lowPass": None, "gainDb": 0}]}}
    assert chain_pairs(res_a) == [("A Sub", "B Woofer"), ("B Woofer", "C Mid"), ("C Mid", "D Tweeter")]
    repairs, fixes, _ = plan_repairs(res_a, lay2, check_result(res_a, lay2, ch2, xo), ch2, xo)
    assert [(r["lower"], r["upper"]) for r in repairs] == [("B Woofer", "C Mid")], repairs
    assert repairs[0]["tune"]["minHz"] == 217.0 and repairs[0]["tune"]["maxHz"] == 310.0, repairs[0]["tune"]
    assert repairs[0]["tune"]["families"] == ["Butterworth", "LinkwitzRiley", "Bessel"]
    assert fixes == {"E Centre": {"highPass": {"family": "LinkwitzRiley", "frequencyHz": 990.0, "slopeDbPerOctave": 24}}}, fixes

    # RES-014: the pool re-ranked with the group-delay penalty -- two leaders. A steep pair at the low junction swings
    # past the (clamped) threshold and pays; the gentler pair does not; above 2 kHz the term is silent.
    def cand(total, lp_fam, lp_slope, hp_fam, hp_slope, fc=320.0, conventional=False):
        return {"totalScore": total, "magnitudeScore": total, "achievabilityPenaltyDb": None, "isConventional24": conventional,
                "proposals": [{"block": "A Sub", "kind": "LowPass", "lowPass": edge("LinkwitzRiley", 24, 80.0), "highPass": None},
                              {"block": "B Woofer", "kind": "BandPass", "highPass": edge("LinkwitzRiley", 24, 80.0),
                               "lowPass": edge(lp_fam, lp_slope, fc)},
                              {"block": "C Mid", "kind": "BandPass", "highPass": edge(hp_fam, hp_slope, fc),
                               "lowPass": edge("LinkwitzRiley", 24, 2300.0)},
                              {"block": "D Tweeter", "kind": "HighPass", "highPass": edge("LinkwitzRiley", 24, 2300.0), "lowPass": None}]}
    steep, gentle = (cand(1.00, "LinkwitzRiley", 48, "LinkwitzRiley", 48, fc=200.0),
                     cand(1.30, "LinkwitzRiley", 24, "LinkwitzRiley", 24, fc=200.0))
    res_pool = {"autoCrossover": dict(res_a["autoCrossover"], primaryRankedTop5=[steep, gentle])}
    rr = rerank_pool(res_pool)
    j_steep = {j["upper"]: j for j in rr["rows"][0]["junctions"]}
    j_gentle = {j["upper"]: j for j in rr["rows"][1]["junctions"]}
    assert j_steep["C Mid"]["swing_ms"] > j_gentle["C Mid"]["swing_ms"] and j_steep["C Mid"]["clamped"], (j_steep, j_gentle)
    assert j_steep["D Tweeter"]["penalty_db"] == 0.0 and j_gentle["D Tweeter"]["penalty_db"] == 0.0, "silent above 2 kHz"
    assert rr["engine_leader"] is rr["rows"][0] and rr["rows"][0]["rank_engine"] == 1
    want = min(rr["rows"], key=lambda r: r["total_score_db"] + r["gd_penalty_db"])
    assert rr["experimental_leader"] is want and rr["changed"] == (want is not rr["rows"][0]), rr
    assert j_steep["C Mid"]["penalty_db"] > 0.3, ("the steep pair must pay for the test to mean anything", j_steep["C Mid"])
    assert rr["changed"], "1.3 - 1.0 = 0.3 dB of engine score against a larger penalty: the leader flips"
    assert rerank_pool({"autoCrossover": dict(res_a["autoCrossover"])}) is None, "no pool, no re-rank"
    txt_rr = render_variants({"delays": {}, "rerank": rr, "checks_final": [], "notes": []})
    assert "TWO LEADERS" in txt_rr and "  E " in txt_rr and "   X" in txt_rr, txt_rr
    assert "experimental leader is the engine's #2" in txt_rr, txt_rr

    # the wishes: a corner is a probe, a family without a corner a tune, a broken or unsure wish is not computed,
    # and a pair that is no junction of this chain says so
    rows_w = _xw.check_wishes("BE4 між мідом і твітером на 2300, BW2 між сабом і мідбасом, не знаю між мідбасом і "
                              "мідом, BW2 для твітера від 900, LR4 між сабом і твітером", ch2, xo)
    items, skipped = wish_items(rows_w, lay2, res_a, ch2, xo)
    assert [(i["lower"], i["upper"], "probe" in i, "tune" in i) for i in items] == [
        ("C Mid", "D Tweeter", True, False), ("A Sub", "B Woofer", False, True)], items
    assert items[0]["probe"][0]["lowPass"] == edge("Bessel", 24, 2300.0) == items[0]["probe"][0]["highPass"]
    assert items[1]["tune"] == {"families": ["Butterworth"], "slopes": [12]}, items[1]
    assert [v for _, v, _ in skipped] == ["UNSURE", "REFUSED", "OK"] and "not a junction" in skipped[2][2], skipped

    # the costs: a probe per side against what stands; a tune's best held to the limits and marked at the window's edge
    res_b = {"junctions": [
        {"lower": "C Mid", "upper": "D Tweeter", "purpose": "wish: X", "probe": {"entries": [
            {"label": "as it stands", "sharedBandSides": [{"side": "left", "scoreDb": 9.0}, {"side": "right", "scoreDb": 11.5}],
             "afterDelay": [{"side": "left", "lossDb": -1.1}, {"side": "right", "lossDb": -1.7}]},
            {"label": "X", "sharedBandSides": [{"side": "left", "scoreDb": 14.0}, {"side": "right", "scoreDb": 11.2}],
             "afterDelay": [{"side": "left", "lossDb": -1.0}, {"side": "right", "lossDb": -2.1}], "unavailable": None}]}},
        {"lower": "C Mid", "upper": "D Tweeter", "purpose": "wish: Y", "tune": {
            "windowHz": [1044.0, 3250.0], "current": {"rankingScoreDb": 9.78},
            "best": {"rankingScoreDb": 8.53, "lowPass": edge("Bessel", 24, 1050.0), "highPass": edge("Bessel", 24, 1050.0)}}}],
        "settingsFinal": [{"block": "C Mid", "left": {"crossover": "BandPass", "highPass": edge("LinkwitzRiley", 24, 250.0),
                                                      "lowPass": edge("LinkwitzRiley", 24, 2300.0), "gainDb": -3.5}}]}
    costs = wish_costs(res_b, lay2, ch2, xo)
    assert costs[0]["probes"][0]["scoreDeltaDb"] == {"left": 5.0, "right": -0.3}, costs[0]
    assert costs[1]["tune"]["scoreDeltaDb"] == -1.25 and costs[1]["tune"]["atWindowEdge"], costs[1]
    assert costs[1]["tune"]["limit"]["verdict"] == "CAUTION", costs[1]["tune"]["limit"]
    assert final_proposals(res_b)[0]["highPass"]["frequencyHz"] == 250.0
    shown = render_variants({"delays": res_b, "costs": costs, "repairs_planned": repairs, "fixes": fixes,
                             "wishes_skipped": skipped, "checks_final": [], "notes": []})
    assert "THE BEST WITHIN THE LIMITS" in shown and "found at the window's edge" in shown and "not computed" in shown, shown

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
          "that fits the Helix (12 ms); a mid corner under its floor re-searched from 217 Hz and a centre's set to "
          "990 Hz; wishes as probes and tunes, the broken and the unsure not computed; a tune's best at the window's "
          "edge and in CAUTION said so; the cross-OS tolerance; the PEQ Q the same on both sides; and the prebuilt "
          "engine fetched by its computed name with the digest checked -- a mismatch refused with nothing installed, "
          "a release that carries none answered rather than failed")
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
    p = sub.add_parser("install-binary", help="install a prebuilt engine for this pin and platform")
    p.add_argument("--from", dest="source", required=True, metavar="ZIP|DIR")
    p = sub.add_parser("fetch-binary", help="fetch this pin and platform's prebuilt engine from a tag's release")
    p.add_argument("--tag", required=True, metavar="vX.Y.Z", help="the tag whose release carries the archives")
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
        p.add_argument("--wishes", metavar="TEXT", help="run: the tuner's crossover wishes in free words (xover_wishes)")
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
    if a.cmd == "install-binary":
        print(f"  installed: {install_binary(a.source)}")
        return 0
    if a.cmd == "fetch-binary":
        got = fetch_binary(a.tag)
        print(f"  {got['status']}: {got['detail']}")
        # 0 installed · 4 nothing to install, and the caller says which way it went · 3 refused (above, loudly).
        return 0 if got["status"] == "installed" else 4
    if a.cmd == "acceptance":
        return acceptance(a.set, a.project, keep=a.keep)
    if a.cmd == "smoke":
        return smoke()

    if a.cmd == "layout":
        layout, notes, problems, _, _ = build_layout(
            a.project, a.set, pick=_pairs(a.file, "--file"), include_hidden=a.include_hidden,
            window_defaults=a.window_defaults, types=_pairs(a.type, "--type"), scene_offset_ms=a.scene_offset,
            rear_fill_ms=a.rear_fill, adjust_gains=a.gains, near_side_cut_db=a.near_side_cut)
        for n in notes:
            print(f"  · {n}", file=sys.stderr)
        if problems:
            for pr in problems:
                print(f"  ✗ {pr}", file=sys.stderr)
            return 2
        text = json.dumps(layout, indent=1, ensure_ascii=False)
        if a.out:
            with open(a.out, "w", encoding="utf-8") as fh:
                fh.write(text + "\n")
            print(f"  wrote {a.out}")
        else:
            print(text)
        return 0
    v = variants(a.project, a.set, wishes=a.wishes, out_dir=a.out, pick=_pairs(a.file, "--file"),
                 include_hidden=a.include_hidden, window_defaults=a.window_defaults, types=_pairs(a.type, "--type"),
                 scene_offset_ms=a.scene_offset, rear_fill_ms=a.rear_fill, adjust_gains=a.gains,
                 near_side_cut_db=a.near_side_cut)
    if v.get("out_dir"):
        with open(os.path.join(v["out_dir"], "variants.json"), "w", encoding="utf-8") as fh:
            json.dump({k: v[k] for k in v if k not in ("crossover", "delays")}, fh, indent=1, ensure_ascii=False)
    if a.json:
        print(json.dumps(v, indent=1, ensure_ascii=False))
    else:
        print(render_variants(v))
        if v.get("out_dir"):
            print(f"\n  wrote {v['out_dir']}/1-crossover, 2-delays-and-wishes, variants.json")
    if v.get("problems"):
        return 1
    return 0 if v.get("rc_delays") == 0 else EXIT_REFUSED


if __name__ == "__main__":
    import console                       # issue #21: a code page must not destroy a result
    console.install()
    sys.exit(main())
