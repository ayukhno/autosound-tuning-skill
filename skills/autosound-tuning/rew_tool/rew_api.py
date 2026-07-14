import urllib.request
import urllib.parse
import json
import base64
import struct

BASE_URL = "http://localhost:4735"


def _get(path):
    url = BASE_URL + path
    with urllib.request.urlopen(url) as r:
        return json.loads(r.read())


def _post(path, data):
    url = BASE_URL + path
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        raw = r.read()
        return json.loads(raw) if raw else {}


def _put(path, data):
    url = BASE_URL + path
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, method="PUT",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        raw = r.read()
        return json.loads(raw) if raw else {}


def decode_floats(b64_str):
    raw = base64.b64decode(b64_str)
    n = len(raw) // 4
    return list(struct.unpack(f">{n}f", raw))


def build_freqs(start_freq, ppo, n_points):
    return [start_freq * (2 ** (i / ppo)) for i in range(n_points)]


def freq_axis(data, n):
    """Build the frequency axis from a REW response payload.

    REW returns one of two spacings depending on the measurement type:
      • log-spaced (sweep): "ppo" (points-per-octave) + "startFreq"
      • linear-spaced (RTA / linear): "freqStep" + "startFreq"
    Handle both, or get a KeyError crash on RTA data (only "ppo" was handled).
    """
    if data.get("ppo"):
        return build_freqs(data["startFreq"], data["ppo"], n)
    if data.get("freqStep"):
        start = data.get("startFreq", 0.0)
        step = data["freqStep"]
        return [start + i * step for i in range(n)]
    # Fallback: assume a sane log axis rather than crashing.
    return build_freqs(data.get("startFreq", 20.0), data.get("ppo", 48), n)


def get_measurements():
    return _get("/measurements")


def get_measurement(mid):
    return _get(f"/measurements/{mid}")


def find_measurement_id(name, measurements=None, exact=True):
    """Resolve a measurement's CURRENT ordinal id by its title (name).

    REW keys get_measurements() by an ordinal ("1","15",...) that is NOT stable
    across calls — a reorder / sort / delete / new sweep reshuffles it. So never
    cache an index; resolve the title→id immediately before each pull. Raises on
    an AMBIGUOUS (>1) or MISSING (0) match, so a wrong-channel pull can't pass
    silently (the real m-L/m-R swap bug). See rew-api-quirks.md.
    """
    ms = measurements if measurements is not None else get_measurements()
    matches = []
    for mid, m in ms.items():
        title = (m or {}).get("title", "")
        if (title == name) if exact else (name.lower() in title.lower()):
            matches.append(mid)
    if not matches:
        titles = [(m or {}).get("title", "") for m in ms.values()]
        raise KeyError(f"No measurement titled {name!r} (have: {titles})")
    if len(matches) > 1:
        raise KeyError(f"Ambiguous: {len(matches)} measurements titled {name!r} "
                       f"→ {matches}; rename so titles are unique")
    return matches[0]


def get_measurement_by_name(name, exact=True):
    """(id, measurement_dict) resolved by title NOW — never via a cached index.

    Use this (or find_measurement_id) right before pulling FR/IR/etc., e.g.:
        mid, _ = get_measurement_by_name("m-L_07 (sw)"); freqs, mag, ph = get_fr(mid)
    """
    ms = get_measurements()
    mid = find_measurement_id(name, ms, exact=exact)
    return mid, ms[mid]


def get_fr(mid):
    data = _get(f"/measurements/{mid}/frequency-response")
    mag = decode_floats(data["magnitude"])
    # RTA measurements carry no phase (rew-api-quirks.md "Timing"); return None
    # so magnitude-only callers keep working instead of hitting a KeyError.
    phase = decode_floats(data["phase"]) if "phase" in data else None
    freqs = freq_axis(data, len(mag))
    return freqs, mag, phase


def get_group_delay(mid):
    data = _get(f"/measurements/{mid}/group-delay")
    # GD values come under key "magnitude" (verified); accept "groupDelay" too.
    gd = decode_floats(data.get("groupDelay") or data["magnitude"])
    freqs = freq_axis(data, len(gd))
    return freqs, gd


def get_impulse_response(mid):
    data = _get(f"/measurements/{mid}/impulse-response")
    # REW returns the samples under "data" (not "impulseResponse" — that key
    # doesn't exist on this endpoint; the old code KeyError'd here).
    ir = decode_floats(data.get("data") or data["impulseResponse"])
    # Timing comes straight from REW ("startTime"/"delay") — don't reconstruct
    # it from the array; that gave junk timing (see rew-api-quirks.md).
    start_time = data.get("startTime", data.get("delay", 0.0))
    sample_rate = data.get("sampleRate", 48000)
    dt = 1.0 / sample_rate
    times = [start_time + i * dt for i in range(len(ir))]
    return times, ir


def get_distortion(mid):
    try:
        return _get(f"/measurements/{mid}/distortion")
    except Exception:
        return None


def get_filters(mid):
    return _get(f"/measurements/{mid}/filters")


def set_filters(mid, filters):
    return _put(f"/measurements/{mid}/filters", filters)


def get_equaliser(mid):
    return _get(f"/measurements/{mid}/equaliser")


def set_equaliser(mid, equaliser_name):
    return _post(f"/measurements/{mid}/equaliser", {"name": equaliser_name})


def get_equalisers():
    return _get("/eq/equalisers")


def get_crossover_types():
    return _get("/eq/crossover-types")


def get_slopes():
    return _get("/eq/slopes")


def get_target_settings(mid):
    return _get(f"/measurements/{mid}/target-settings")


def get_target_response(mid):
    data = _get(f"/measurements/{mid}/target-response")
    mag = decode_floats(data["magnitude"])
    freqs = freq_axis(data, len(mag))
    return freqs, mag


# ── Measurement-processing commands (POST /measurements/{id}/command) ────────
# Distinct from the Pro-gated capture namespace (/measure/*): processing an
# EXISTING measurement is free. Verified live on REW 5.40 / API 0.9.5.

def measurement_command(mid, command, parameters=None):
    """Low-level `POST /measurements/{id}/command`. `parameters` is a dict
    (REW reports missing keys with a 400 listing them — build up from there)."""
    body = {"command": command}
    if parameters is not None:
        body["parameters"] = parameters
    return _post(f"/measurements/{mid}/command", body)


def minimum_phase_version(mid, append_lf_tail=False, append_hf_tail=False,
                          include_cal=False, replicate_data=False):
    """Create the **minimum-phase** version of a sweep (new measurement `<name>-MP`).
    Tails off by default (turning a tail on also needs its start/slope params —
    pass a raw dict via `measurement_command` for that). Returns 202 in-progress."""
    return measurement_command(mid, "Minimum phase version", {
        "append lf tail": append_lf_tail, "append hf tail": append_hf_tail,
        "include cal": include_cal, "replicate data": replicate_data})


def excess_phase_version(mid, append_lf_tail=False, append_hf_tail=False,
                         include_cal=False, replicate_data=False):
    """Create the **excess-phase** version of a sweep (new measurement `<name>-EP`).
    REW's own Hilbert-based excess phase = measured − minimum phase; read it back
    with `get_fr` (its phase channel IS the excess phase) to decide min- vs
    non-min-phase at a joint — the authoritative path, not a home-brew scan."""
    return measurement_command(mid, "Excess phase version", {
        "append lf tail": append_lf_tail, "append hf tail": append_hf_tail,
        "include cal": include_cal, "replicate data": replicate_data})


def set_smoothing(mid, smoothing="1/6"):
    """Apply REW's own smoothing to a measurement (`Smooth` command) so a later
    `get_fr` returns REW-smoothed data — avoids the home-brew perceptual_smooth
    drift. Values per `/measurements/frequency-response/smoothing-choices`
    (e.g. '1/1'…'1/48', 'Var', 'Psy', 'None')."""
    return measurement_command(mid, "Smooth", {"smoothing": smoothing})


def get_distortion(mid):
    """THD-vs-frequency table computed by REW from a normal log sweep
    (endpoint /measurements/{id}/distortion; verified live 2026-07-14).
    Returns (freqs, fundamental_db, thd_pct, rows) where rows keeps the raw
    per-harmonic columns. ⚠️ Rows below the channel's HPF are noise (a 71 %
    "THD" at 10 Hz on a 460 Hz-HPF mid is the noise floor, not the driver) —
    evaluate only in/near the intended passband. Use: the Phase-0 flaw map's
    distortion floors — a crossover corner needs LOW measured THD with
    margin, not just a datasheet Fs rule."""
    data = _get(f"/measurements/{mid}/distortion")
    hdr = data.get("columnHeaders", [])
    rows = data.get("data", [])

    def col(idx):
        out = []
        for r in rows:
            try:
                out.append(float(r[idx]))
            except (IndexError, TypeError, ValueError):
                out.append(float("nan"))
        return out
    i_thd = next((i for i, h in enumerate(hdr) if "THD" in h), 2)
    return col(0), col(1), col(i_thd), rows


def _selftest():
    """Exercise both branches of get_fr offline — phase-present (sweep) and
    phase-absent (RTA). The RTA branch used to KeyError on data["phase"]
    (rew-api-quirks.md "Timing"); it stayed hidden because no test drove it.
    Stubbing the HTTP layer keeps this regression caught even when no live
    measurement or production caller touches the phase-absent path."""
    global _get
    _orig = _get

    def _enc(vals):
        return base64.b64encode(struct.pack(f">{len(vals)}f", *vals)).decode()

    try:
        _get = lambda path: {                       # sweep: has "phase"
            "magnitude": _enc([80.0, 82.0, 84.0]),
            "phase": _enc([-10.0, -20.0, -30.0]),
            "startFreq": 100.0, "ppo": 48,
        }
        _f, _m, p = get_fr("stub")
        assert p is not None and len(p) == 3, "sweep: phase should decode"

        _get = lambda path: {                       # RTA: NO "phase" key
            "magnitude": _enc([70.0, 71.0, 72.0]),
            "startFreq": 20.0, "freqStep": 10.0,
        }
        f, m, p = get_fr("stub")
        assert p is None, "RTA: phase must be None, not a KeyError"
        assert len(m) == 3 and len(f) == 3, "RTA: magnitude/freqs still returned"
    finally:
        _get = _orig

    # command wrappers post the right path/body (mock _post — no live REW)
    global _post
    _origp = _post
    sent = {}
    try:
        _post = lambda path, data: (sent.update(path=path, data=data),
                                    {"message": "ok"})[1]
        excess_phase_version(7)
        assert sent["path"] == "/measurements/7/command", sent
        assert sent["data"]["command"] == "Excess phase version", sent
        assert sent["data"]["parameters"]["replicate data"] is False, sent
        minimum_phase_version(7)
        assert sent["data"]["command"] == "Minimum phase version", sent
        set_smoothing(7, "1/6")
        assert sent["data"] == {"command": "Smooth",
                                "parameters": {"smoothing": "1/6"}}, sent
    finally:
        _post = _origp

    print("rew_api selftest OK — get_fr handles sweep/RTA phase branch; "
          "excess/min-phase + smooth command wrappers post correct bodies")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        _selftest()
    else:
        print("usage: python rew_api.py --selftest")
