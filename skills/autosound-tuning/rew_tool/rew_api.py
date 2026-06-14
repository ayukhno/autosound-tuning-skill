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


def get_measurements():
    return _get("/measurements")


def get_measurement(mid):
    return _get(f"/measurements/{mid}")


def get_fr(mid):
    data = _get(f"/measurements/{mid}/frequency-response")
    mag = decode_floats(data["magnitude"])
    phase = decode_floats(data["phase"])
    freqs = build_freqs(data["startFreq"], data["ppo"], len(mag))
    return freqs, mag, phase


def get_group_delay(mid):
    data = _get(f"/measurements/{mid}/group-delay")
    gd = decode_floats(data["groupDelay"])
    freqs = build_freqs(data["startFreq"], data["ppo"], len(gd))
    return freqs, gd


def get_impulse_response(mid):
    data = _get(f"/measurements/{mid}/impulse-response")
    ir = decode_floats(data["impulseResponse"])
    start_time = data.get("startTime", 0)
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
    freqs = build_freqs(data["startFreq"], data["ppo"], len(mag))
    return freqs, mag
