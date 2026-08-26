#!/usr/bin/env python3
"""rew_stub -- the four REW API endpoints the method's tools read, served from files. No REW needed.

The commands that talk to REW -- `capture-check [--session]`, `predict --rew --ver N`,
`verify_prediction --rew` -- could until now only be exercised with a live REW and a car. This
serves what they ask for from impulse responses on disk (Resonalyze v7 files, or arrays handed to
`serve()` in-process), so the in-car half of the path runs in `path_check`, in CI, and at a desk
with an archived session. Point the tools at it with `REW_API_URL` (`rew_api.py` reads it).

    python3 rew_tool/rew_stub.py --from-v7 <dir> --ver 49            # serve <code>_49 (sw) titles
    REW_API_URL=http://127.0.0.1:47350 python3 rew_tool/state/process.py <proj>/process capture-check --session

What is served, and only that (`rew_api.py` is the list of what is read):

  GET /measurements                       {id: {title, uuid, date, timingReference, timingOffset,
                                                timeOfIRStartSeconds, timeOfIRPeakSeconds, sampleRate,
                                                startFreq, endFreq, notes}}
  GET /measurements/{id}                  the same record
  GET /measurements/{id}/frequency-response   {startFreq, ppo, magnitude, phase, smoothing: "None"}
                                          (an RTA record: freqStep instead of ppo, no phase)
  GET /measurements/{id}/impulse-response {startTime, sampleRate, data}

Floats travel as REW sends them -- base64 of big-endian float32 -- so `rew_api.decode_floats` is
the reader on both. Everything else answers 404 with a message, the way REW does: a tool that
asks for what the stub does not serve fails by name, never silently. GET only: REW may be
mid-session is the doctrine for the real thing; the stub simply has nothing to write.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import struct
import sys
import threading
import uuid as _uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

PPO = 48
F_LOW, F_HIGH = 20.0, 20000.0


def encode_floats(values):
    arr = np.asarray(values, dtype=">f4")
    return base64.b64encode(arr.tobytes()).decode("ascii")


class Measurement:
    """One served measurement: an impulse response with its time base, or an RTA curve."""

    def __init__(self, title, ir=None, sample_rate=96000, start_time_s=0.0, *, rta=None,
                 timing_reference="Loopback", timing_offset_s=0.0, notes="", uid=None):
        self.title = title
        self.ir = None if ir is None else np.asarray(ir, dtype=float)
        self.fs = int(sample_rate)
        self.start_time_s = float(start_time_s)
        self.rta = rta                      # (freqs, mag_db) for a moving-mic measurement
        self.timing_reference = timing_reference
        self.timing_offset_s = float(timing_offset_s)
        self.notes = notes
        self.uid = uid or str(_uuid.uuid4())
        self._fr = None

    def record(self, mid):
        rec = {"id": mid, "title": self.title, "uuid": self.uid, "date": "2026-01-01 00:00:00",
               "notes": self.notes, "sampleRate": self.fs, "startFreq": F_LOW, "endFreq": F_HIGH,
               "timingReference": self.timing_reference, "timingOffset": self.timing_offset_s}
        if self.ir is not None:
            k = int(np.argmax(np.abs(self.ir)))
            rec["timeOfIRStartSeconds"] = self.start_time_s
            rec["timeOfIRPeakSeconds"] = self.start_time_s + k / self.fs
            rec["delay"] = rec["timeOfIRPeakSeconds"]
        else:
            rec["timeOfIRStartSeconds"] = None
            rec["timeOfIRPeakSeconds"] = None
        return rec

    def frequency_response(self):
        if self.rta is not None:
            f, mag = self.rta
            f = np.asarray(f, float)
            step = float(f[1] - f[0]) if len(f) > 1 else 1.0
            return {"startFreq": float(f[0]), "freqStep": step, "magnitude": encode_floats(mag),
                    "smoothing": "None"}
        if self._fr is None:
            n = self.ir.size
            # Zero-padded 4x: the bins are then a quarter of the IR's own resolution, and the
            # log-magnitude interpolation below is exact to a few thousandths of a dB even at the
            # knee of a low-frequency roll-off (0.04 dB at 22 Hz without the padding).
            X = np.fft.rfft(self.ir, 4 * n)
            fb = np.fft.rfftfreq(4 * n, 1.0 / self.fs)
            npts = int(np.floor(np.log2(F_HIGH / F_LOW) * PPO)) + 1
            f = F_LOW * 2.0 ** (np.arange(npts) / PPO)
            # Magnitude and UNWRAPPED phase interpolated separately: a pure delay is then exactly
            # flat on the grid (interpolating real/imag between bins of a rotating phasor shaves the
            # magnitude by 1 - cos(half the phase step per bin) -- 0.003 dB on a 250-sample delay).
            mag_b = 20.0 * np.log10(np.maximum(np.abs(X), 1e-12))
            ph_b = np.unwrap(np.angle(X))
            mag = np.interp(f, fb, mag_b)
            ph = np.degrees(np.interp(f, fb, ph_b))
            ph = (ph + 180.0) % 360.0 - 180.0
            self._fr = {"startFreq": F_LOW, "ppo": PPO, "magnitude": encode_floats(mag),
                        "phase": encode_floats(ph), "smoothing": "None"}
        return self._fr

    def impulse_response(self):
        if self.ir is None:
            return None
        return {"startTime": self.start_time_s, "sampleRate": self.fs, "data": encode_floats(self.ir)}


class _Handler(BaseHTTPRequestHandler):
    measurements = []          # set by serve(): a list, ids are 1-based ordinals like REW's

    def log_message(self, *a):  # quiet
        pass

    def _json(self, code, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parts = [p for p in self.path.split("?")[0].split("/") if p]
        ms = self.measurements
        if parts == ["measurements"]:
            return self._json(200, {str(i + 1): m.record(str(i + 1)) for i, m in enumerate(ms)})
        if len(parts) >= 2 and parts[0] == "measurements":
            try:
                m = ms[int(parts[1]) - 1]
            except (ValueError, IndexError):
                return self._json(404, {"message": f"no measurement {parts[1]}"})
            if len(parts) == 2:
                return self._json(200, m.record(parts[1]))
            if parts[2] == "frequency-response":
                return self._json(200, m.frequency_response())
            if parts[2] == "impulse-response":
                ir = m.impulse_response()
                if ir is None:
                    return self._json(404, {"message": f"{m.title!r} has no impulse response (an RTA)"})
                return self._json(200, ir)
        return self._json(404, {"message": f"rew_stub does not serve {self.path}"})

    def do_POST(self):
        self._json(405, {"message": "rew_stub is read-only: it serves what REW would, and writes nothing"})

    do_PUT = do_DELETE = do_POST


def serve(measurements, host="127.0.0.1", port=0):
    """Start serving `measurements` (a list of `Measurement`) in a thread. Returns (url, server);
    stop with `server.shutdown()`. Port 0 picks a free one."""
    handler = type("Handler", (_Handler,), {"measurements": list(measurements)})
    server = ThreadingHTTPServer((host, port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return f"http://{host}:{server.server_address[1]}", server


def measurements_from_v7_dir(directory, ver):
    """Every v7 file in DIR as a served sweep titled `<code>_<ver> (sw)`; a control file
    `m_L-ctl1.json` becomes `m-L-ctl1_<ver> (sw)`."""
    out = []
    for name in sorted(os.listdir(directory)):
        if not name.endswith(".json") or name == "manifest.json":
            continue
        with open(os.path.join(directory, name), encoding="utf-8") as fh:
            doc = json.load(fh)
        if "transferRealSamples" not in doc:
            continue
        stem = name[:-5]
        code = stem.replace("-ctl", "|ctl").replace("_", "-").replace("|ctl", "-ctl")
        rs = doc.get("rewSource") or {}
        out.append(Measurement(f"{code}_{ver} (sw)", doc["transferRealSamples"], doc["sampleRate"],
                               0.0, notes=rs.get("rewNotes", ""), uid=rs.get("rewUuid")))
    if not out:
        raise SystemExit(f"{directory}: no v7 impulse-response files")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--from-v7", metavar="DIR", help="serve the v7 files in DIR")
    ap.add_argument("--ver", default="1", help="the `_N` the titles carry (default 1)")
    ap.add_argument("--port", type=int, default=47350)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        return _selftest()
    if not args.from_v7:
        ap.error("need --from-v7 DIR")
    url, server = serve(measurements_from_v7_dir(args.from_v7, args.ver), port=args.port)
    print(f"rew_stub serving {len(server.RequestHandlerClass.measurements)} measurements at {url} -- "
          f"REW_API_URL={url}   (Ctrl-C to stop)")
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        server.shutdown()
    return 0


def _selftest():
    """Through `rew_api` itself, with `BASE_URL` pointed at the stub: what the tools read comes back
    as REW would send it, and a pure delay reads as a pure delay."""
    import dsp_math
    import rew_api
    import verify as _verify
    fs, n, d = 96000, 1 << 15, 250
    # a driver-shaped impulse: a delay of d samples through a 40 Hz LR12 high-pass (the capture
    # gate calls a FLAT response "a loopback or a placeholder, not a driver in a car" -- rightly)
    fb = np.fft.rfftfreq(n, 1.0 / fs)
    shape = dsp_math.xo_response(fb, 40.0, 12, "hp", "LR")
    ir = np.fft.irfft(0.5 * shape * np.exp(-2j * np.pi * fb * d / fs), n=n)
    rta_f = np.arange(20.0, 20000.0, 10.0)
    ms = [Measurement("w-L_1 (sw)", ir, fs, 0.0),
          Measurement("w-L_1 (rta)", rta=(rta_f, np.full(rta_f.size, 70.0))),
          Measurement("odd_1 (sw)", ir, fs, -0.5, timing_offset_s=0.0077)]
    url, server = serve(ms)
    try:
        rew_api.BASE_URL = url
        listing = rew_api.get_measurements()
        assert set(listing) == {"1", "2", "3"} and listing["1"]["title"] == "w-L_1 (sw)", listing
        mid = rew_api.find_measurement_id("w-L_1 (sw)", listing, exact=True)
        t = rew_api.get_timing(mid)
        assert t["has_ir"] and t["reference"] == "Loopback" and t["offset_s"] == 0.0, t
        assert abs(t["ir_peak_s"] - d / fs) < 1e-9, t
        f, mag, phase = rew_api.get_fr(mid)
        assert len(f) == len(mag) == len(phase) and abs(f[0] - 20.0) < 1e-9 and f[-1] <= 20000.0
        want = 20 * np.log10(0.5 * np.abs(dsp_math.xo_response(np.asarray(f), 40.0, 12, "hp", "LR")))
        assert max(abs(m - w) for m, w in zip(mag, want)) < 0.01, "the served magnitude is the designed shape"
        times, ir_back = rew_api.get_impulse_response(mid)
        assert times[0] == 0.0 and abs(times[1] - 1.0 / fs) < 1e-12 and len(ir_back) == n
        assert abs(int(np.argmax(np.abs(ir_back))) - d) <= 1
        # the RTA: no impulse, no phase, a linear axis -- exactly what the tools branch on
        t2 = rew_api.get_timing(rew_api.find_measurement_id("w-L_1 (rta)", listing))
        assert t2["has_ir"] is False, t2
        f2, m2, p2 = rew_api.get_fr("2")
        assert p2 is None and abs(f2[1] - f2[0] - 10.0) < 1e-9 and abs(m2[0] - 70.0) < 1e-6
        try:
            rew_api.get_impulse_response("2")
            raise AssertionError("an RTA handed back an impulse response")
        except Exception as exc:  # noqa: BLE001 -- REW's 404 carries a message; so does ours
            assert "impulse" in str(exc), exc
        # the odd one: an offset the tools must refuse as a shared base
        t3 = rew_api.get_timing("3")
        assert abs(t3["offset_s"] - 0.0077) < 1e-12 and t3["ir_start_s"] == -0.5
        # and the capture gate reads a served sweep as a valid measurement
        v = _verify.verdict("w-L_1 (sw)", listing)
        assert v["exists"] and v["valid"] and v["stats"]["capture_rate_hz"] == fs, v
        assert abs(v["stats"]["peak_time_ms"] - d / fs * 1000) < 1e-3, v["stats"]   # sub-sample refined, 4 decimals
        # something not served fails by name
        try:
            rew_api._get("/measurements/1/filters")
            raise AssertionError("an unserved endpoint answered")
        except Exception as exc:  # noqa: BLE001
            assert "rew_stub" in str(exc) or "404" in str(exc), exc
    finally:
        server.shutdown()
    print("selftest[rew_stub] OK -- the four endpoints read back through rew_api: listing, timing "
          "(loopback / offset / no-IR), log-axis FR (the designed shape comes back), the impulse with its "
          "start time, a linear-axis RTA without phase or impulse, the capture gate's verdict on a "
          "served sweep, and a 404 by name for what is not served.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
