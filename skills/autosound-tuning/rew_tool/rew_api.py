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
    phase = decode_floats(data["phase"])
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
