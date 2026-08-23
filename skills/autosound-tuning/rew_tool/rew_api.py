import urllib.request
import urllib.error
import urllib.parse
import json
import base64
import struct

BASE_URL = "http://localhost:4735"
# No timeout on urlopen() meant a REW-unreachable call (REW not running, port filtered rather than
# actively refused, ...) could hang a caller forever -- fatal when that caller is a Qt QThread: the
# app hangs, gets force-quit, and Qt aborts with "QThread: Destroyed while thread is still running"
# (hit live via TCC's Read/rename buttons, 2026-07-27). 5s is generous for REW's local API.
_TIMEOUT_S = 5


def _open(req_or_url):
    """urlopen, but a 4xx/5xx carries REW's OWN explanation instead of just its number.

    `HTTPError` is a response object: the server's body is sitting on it, and reading it is the
    difference between "HTTP Error 400: Bad Request" and REW telling you exactly what it wanted.
    A live case: `excess_phase_version` failed with a bare 400, and only a hand-rolled probe
    revealed the body -- "The request is missing parameters: append lf tail, append hf tail,
    include cal" -- which named the fix outright. That body had been arriving all along and being
    dropped on the floor (field session 2026-08-21, inbox 3.7).

    The body is read ONCE here, because HTTPError's stream cannot be read twice; callers that
    catch the error get it from the message and from `.rew_body`.
    """
    try:
        return urllib.request.urlopen(req_or_url, timeout=_TIMEOUT_S)
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", "replace").strip()
        except Exception:                      # a body that cannot be read is not the real error
            body = ""
        e.rew_body = body
        if body:
            # REW answers errors as JSON with a "message"; fall back to the raw text if not.
            try:
                said = json.loads(body).get("message") or body
            except ValueError:
                said = body
            e.msg = f"{e.msg} -- REW said: {said}"
        raise


def _get(path):
    url = BASE_URL + path
    with _open(url) as r:
        return json.loads(r.read())


def _body_request(path, data, method):
    url = BASE_URL + path
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, method=method,
                                 headers={"Content-Type": "application/json"})
    with _open(req) as r:
        raw = r.read()
        return json.loads(raw) if raw else {}


def _post(path, data):
    return _body_request(path, data, "POST")


def _put(path, data):
    return _body_request(path, data, "PUT")


def _delete(path):
    req = urllib.request.Request(BASE_URL + path, method="DELETE")
    with _open(req) as r:
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


def rename_measurement(mid, title):
    """Rename a measurement in place (its ordinal id is unchanged; only the title changes).

    `PUT /measurements/{id}` with a `title` body -- the REST-conventional shape, consistent with
    this API's other resource endpoints (e.g. `set_filters`'s `PUT /measurements/{id}/filters`).
    No REW doc describes a rename endpoint, so this was written from that convention and then
    **verified against a live REW instance** (renamed a measurement, confirmed the new title in
    REW's own UI, 2026-07-28). Added for TCC's capture-order auto-naming feature.

    If a future REW release breaks it, the fallback to try next is
    `POST /measurements/{id}/command` (see `measurement_command`) with a "Rename"-style command
    discovered via `GET /measurements/{id}/commands`."""
    return _put(f"/measurements/{mid}", {"title": title})


def delete_measurement(mid):
    """Remove a measurement from the live REW session. `DELETE /measurements/{id}`.

    Verified live (REW answered `{"message": "Measurement 75 deleted"}`, 2026-08-21). Written
    because a session had to hand-roll it after an accidental duplicate `-EP` version, which is
    the usual reason to need it at all.

    ⚠️ **Ordinal ids are not stable** -- a delete RESHUFFLES every id after it, which is the same
    hazard `find_measurement_id` exists for, made sharper: resolve the title to an id immediately
    before deleting, delete ONE, and resolve again before the next. Never collect a list of ids
    and then delete them in a loop; after the first, the rest point at other measurements.

    There is no undo. The caller decides whether a thing should go -- this only carries it out.
    """
    return _delete(f"/measurements/{mid}")


def duplicate_titles(measurements=None):
    """Titles held by more than one measurement in the live session: `{title: [ids]}`.

    The whole identity model rests on a title being one measurement's stable name
    (`naming-and-structure.md` section 3a) -- and REW does not enforce it. A session ended up with
    two measurements both called `m-L_0 (sw)-EP`, and `find_measurement_id` would have raised on
    the ambiguity only at the moment of use, if it was ever used: silent until then, and the
    invariant everything else rests on was already broken (inbox 3.5).

    Cheap enough to run before any capture round is declared closed. Empty dict = the invariant
    holds right now.
    """
    if measurements is None:
        measurements = get_measurements()
    seen = {}
    for mid, m in measurements.items():
        title = (m or {}).get("title")
        if title is None:
            continue
        seen.setdefault(title, []).append(mid)
    return {t: ids for t, ids in seen.items() if len(ids) > 1}


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


def _ir_start_time(data):
    """The time of sample 0, from REW's own fields — never reconstructed from the array.

    `startTime` is the answer whenever REW gives it. The interesting part is what happens when it
    does not, because the old fallback chain (`startTime` -> `delay` -> `0.0`) substituted two
    quantities that are NOT the same thing and said nothing:

    * **`delay` has the timing offset folded in.** Measured against a live REW on six captures
      (2026-08-23): `physical arrival = delay + timingOffset`, exact to the last digit on
      integer-sample offsets — 4 ms = 384.0 samples at 96 kHz. So `delay` alone is displaced by
      whatever offset the rig carries, and the displacement looks like a plausible delay rather
      than like an error. Worse, `timingReference` reads `"Loopback"` whether the offset is 0 or
      7.7 ms, so the field that looks like the guard is not one.
    * **`0.0` claims the IR starts at t = 0**, which for a REW sweep is about a second wrong — it
      carries ~1 s of pre-roll holding the Farina harmonic images.

    A check whose input is missing must FAIL rather than report no objection
    (`references/core/estimator-scope.md`), and that applies to a time base most of all: every
    arrival, every alignment and every crossover decision downstream inherits this number. So the
    offset is ADDED when the fallback is used, and a document carrying neither field raises
    instead of quietly starting the clock at zero.
    """
    if "startTime" in data:
        return float(data["startTime"])
    if "delay" in data:
        return float(data["delay"]) + float(data.get("timingOffset") or 0.0)
    raise KeyError(
        "impulse response carries neither 'startTime' nor 'delay': there is no time base to read, "
        "and assuming 0.0 would place sample 0 about a second early on a REW sweep")


def get_impulse_response(mid):
    data = _get(f"/measurements/{mid}/impulse-response")
    # REW returns the samples under "data" (not "impulseResponse" — that key
    # doesn't exist on this endpoint; the old code KeyError'd here).
    ir = decode_floats(data.get("data") or data["impulseResponse"])
    start_time = _ir_start_time(data)
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
    """Replace a measurement's whole filter set. `filters` is a list of FilterSetting dicts.

    POST with a `{"filters": [...]}` envelope, verified against a live REW (returns
    `{"message": "Filters set"}`). The previous shape here -- PUT with a bare array -- could never
    have worked: REW rejects it at the JSON layer with
    `IllegalStateException: Expected BEGIN_OBJECT but was BEGIN_ARRAY`, because PUT on this path
    takes a *single* FilterSetting (see `set_filter`), not a collection.

    Each entry needs at least `index` (1-based, matching the slot numbering `get_filters` returns)
    and `type`; omit `isAuto`, which REW reports but does not accept back. Clear a slot with
    `{"index": N, "type": "None", "enabled": True}`.

    ⚠️ The gain key is **`gaindB`**, not `gain`. An entry using `gain` is accepted with a 200 and
    the filter is created at **0 dB** -- silently flat. Verified live: sending `gain: -3.0` stores
    `gaindB: 0.0`, sending `gaindB: -3.0` stores `gaindB: -3.0`. A proposed EQ cut written the
    wrong way therefore does nothing at all while reporting success, which is the worst failure
    mode this API has. A working PK entry:
    `{"index": 1, "type": "PK", "enabled": True, "frequency": 1000.0, "gaindB": -3.0, "q": 2.0}`.
    """
    return _post(f"/measurements/{mid}/filters", {"filters": filters})


def set_filter(mid, filt):
    """Set ONE filter slot, addressed by the `index` inside `filt`.

    PUT on the same path as `set_filters`; REW answers `{"message": "Filter set"}` (singular).
    Useful for touching a single band without resending the other thirty slots.
    """
    return _put(f"/measurements/{mid}/filters", filt)


def get_equaliser(mid):
    return _get(f"/measurements/{mid}/equaliser")


def set_equaliser(mid, manufacturer, model):
    """Select the equaliser REW models this measurement's filters against.

    An equaliser is identified by the `{manufacturer, model}` pair `get_equalisers()` returns --
    the old single-`name` payload here was rejected with `400 "No manufacturer in the request"`,
    which is why `rew-api-quirks.md` §Writing filters documents the two-field form.

    The choice is load-bearing, not cosmetic: it sets the available filter types and the slot
    count. "Generic"/"Extended" gives 20 slots and includes crossover and all-pass types, so a
    whole channel can be modelled; "Generic"/"Configurable PEQ" gives 31 PEQ-only slots;
    "Audiotec Fischer"/"Full EQ (30 bands)" constrains REW to what a Helix can actually store.
    """
    return _post(
        f"/measurements/{mid}/equaliser", {"manufacturer": manufacturer, "model": model}
    )


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

    # ── the IR time base (2026-08-23) ─────────────────────────────────────────
    # Measured on a live REW: `physical arrival = delay + timingOffset`, and `timingReference`
    # says "Loopback" whether the offset is 0 or 7.7 ms — so the field that looks like the guard
    # is not one. The old chain startTime -> delay -> 0.0 silently swapped in two different
    # quantities, and every arrival downstream inherits whichever it got.
    assert _ir_start_time({"startTime": -1.0021, "delay": 0.5}) == -1.0021, "startTime wins"
    # 4 ms at 96 kHz: delay alone would be displaced by exactly the offset.
    got = _ir_start_time({"delay": -1.0, "timingOffset": 0.004})
    assert abs(got - (-0.996)) < 1e-12, got
    assert _ir_start_time({"delay": -1.0}) == -1.0, "no offset stated is offset zero"
    assert _ir_start_time({"delay": -1.0, "timingOffset": None}) == -1.0, "null offset is zero"
    try:
        _ir_start_time({"sampleRate": 96000})
    except KeyError:
        pass
    else:
        raise AssertionError("a document with no time base must raise, not start the clock at 0")

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

    # duplicate_titles: the invariant everything else rests on (inbox 3.5)
    ms = {"1": {"title": "m-L_0 (sw)"}, "7": {"title": "m-L_0 (sw)-EP"},
          "9": {"title": "m-L_0 (sw)-EP"}, "4": {"title": None}, "5": {}}
    dups = duplicate_titles(ms)
    assert dups == {"m-L_0 (sw)-EP": ["7", "9"]}, dups
    assert duplicate_titles({"1": {"title": "a"}, "2": {"title": "b"}}) == {}, "clean must be empty"

    # _open: an HTTP error must arrive carrying REW's own explanation, not just its number
    # (inbox 3.7 -- the body was always there and was being dropped).
    class _FakeError(urllib.error.HTTPError):
        def __init__(self, body):
            self._body = body.encode()
            super().__init__("http://x", 400, "Bad Request", {}, None)

        def read(self):
            return self._body

    _orig_open = urllib.request.urlopen
    try:
        said = "The request is missing parameters: append lf tail, append hf tail, include cal"
        urllib.request.urlopen = lambda *a, **k: (_ for _ in ()).throw(
            _FakeError(json.dumps({"message": said})))
        try:
            _get("/anything")
        except urllib.error.HTTPError as e:
            assert said in str(e), f"REW's explanation was dropped: {e}"
            assert getattr(e, "rew_body", None), "rew_body should carry the raw body"
        else:
            raise AssertionError("the error was swallowed entirely")

        # A body that is not JSON is still better than nothing, and must not raise on the way out.
        urllib.request.urlopen = lambda *a, **k: (_ for _ in ()).throw(_FakeError("plain text"))
        try:
            _get("/anything")
        except urllib.error.HTTPError as e:
            assert "plain text" in str(e), e
    finally:
        urllib.request.urlopen = _orig_open

    print("rew_api selftest OK — get_fr handles sweep/RTA phase branch; "
          "excess/min-phase + smooth command wrappers post correct bodies; "
          "duplicate titles are found; an HTTP error carries REW's own explanation")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        _selftest()
    else:
        print("usage: python3 rew_api.py --selftest")
