#!/usr/bin/env python3
"""The Mosconi / Gladen filter model: the crossover and EQ responses these DSPs actually run.

Mosconi / Gladen filter model and the PICO 6/8-2 profile contributed by Widar1979
https://github.com/ayukhno/autosound-tuning-skill/issues/214

A crossover leg here is not the textbook alignment of its name: each leg is two biquad sections whose
order, Q and corner come from fixed tables (`SECTION_ORDERS`, `SECTION_Q`, `CORNER_K`), the corner
moved by one of three corner sets chosen once for the whole preset. A first-order low-pass puts its
pole at 2.7^-w0, not e^-w0. The coefficients the hardware runs are the designed ones divided by a0 and
cut to 8.24 fixed point (truncated toward zero), and every response here is computed from those.

The EQ bank: peak, shelves, notch, band-pass, first and second order all-pass, first and second order
HP/LP. A peak band has two modes, and which one is in force is a setting of the tuner's PC program,
not of the preset:

  * «REW-compatible peak»             -- the ordinary RBJ peak;
  * «gain-dependent bandwidth peak»   -- the same filter with its bandwidth set by the gain.

So the method ASKS the tuner which mode the program is set to and records it with the corner set in
the project: `project.py <dir> set-dsp-setting peak_mode rew|gain_dependent --source user` and
`... set-dsp-setting corner_set default|minus_3db|minus_6db --source user` (`project.json`
`dsp.settings`). Not recorded, a peak band or a crossover leg is refused with the question to ask; a
default is never guessed.

The desk reaches it through `dsp_math`'s response hook: `bind_for_project(dir)`, called by `predict`,
`eq_propose`, `joint_search`, `xover_candidates` and `version_bench`, binds this model when the
project's `dsp_profile.json` is this vendor's (`is_this_vendor`).

Verified against saved presets by the contributor: Butterworth 6/12/18/24, Linkwitz 12/18/24, Bessel 12,
the default corner set. The rest (Chebyshev, Bessel 6/18/24, Linkwitz 6, the two normalised sets) is
his model's arithmetic, not yet seen in a saved file.

Read only: this module has no write path of any kind -- it never creates or changes a preset file.

numpy; scipy only through `dsp_math`, which `bind` loads for the hook.

  python3 mosconi_gladen.py --selftest
"""
import math
import os
import sys

import numpy as np

FAMILIES = ("LR", "BE", "BW", "CH")
SLOPES = (6, 12, 18, 24)
_FAMILY_SPELLINGS = {"LR": "LR", "LINKWITZ": "LR", "BE": "BE", "BESSEL": "BE", "BW": "BW",
                     "BUTTERWORTH": "BW", "CH": "CH", "CHEBYSHEV": "CH"}

#: The corner sets, in the order a preset numbers them (0, 1, 2).
CORNER_SETS = {"default": "default corners", "minus_3db": "normalised to -3 dB", "minus_6db": "normalised to -6 dB"}
CORNER_SET_ORDER = ("default", "minus_3db", "minus_6db")

#: The two peak modes, by the key recorded in the project and the name said to the tuner.
PEAK_MODES = {"rew": "REW-compatible peak", "gain_dependent": "gain-dependent bandwidth peak"}

#: Per slope, the order of stage 1 and stage 2 (0 off, 1 first order, 2 second order).
SECTION_ORDERS = {6: (0, 1), 12: (0, 2), 18: (1, 2), 24: (2, 2)}

#: Q of each second-order stage, per family and slope (None: a first-order or unused stage).
SECTION_Q = {
    "LR": {12: (None, 0.5), 18: (None, 0.707), 24: (0.707, 0.707)},
    "BE": {12: (None, 0.58), 18: (None, 0.69), 24: (0.81, 0.52)},
    "BW": {12: (None, 0.707), 18: (None, 1.0), 24: (1.307, 0.541)},
    "CH": {12: (None, 1.0), 18: (None, 1.41), 24: (0.58, 1.618)},
}

#: Corner factor k of each stage: the stage sits at f*k (low-pass) or f/k (high-pass). Unlisted = 1.
CORNER_K = {
    "default": {"LR": {6: (1, 0.571)},
                "BE": {12: (1, 1.27), 18: (1.32, 1.45), 24: (1.6, 1.43)},
                "BW": {},
                "CH": {24: (1.015, 1.015)}},
    "minus_3db": {"LR": {12: (1, 1.563), 18: (1.351, 1.351), 24: (1.25, 1.25)},
                  "BE": {12: (1, 1.27), 18: (1.32, 1.45), 24: (1.6, 1.43)},
                  "BW": {},
                  "CH": {12: (1, 0.781), 18: (0.855, 0.855), 24: (0.897, 0.897)}},
    "minus_6db": {"LR": {6: (1, 0.571)},
                  "BE": {6: (1, 0.571), 12: (1, 0.876), 18: (0.964, 1.058), 24: (1.176, 1.051)},
                  "BW": {6: (1, 0.571), 12: (1, 0.763), 18: (0.833, 0.833), 24: (0.87, 0.87)},
                  "CH": {6: (1, 0.571), 12: (1, 0.667), 18: (0.758, 0.758), 24: (0.816, 0.816)}},
}

#: Where a stage's corner and Q are held.
SECTION_F_RANGE_HZ = (20.0, 20000.0)
SECTION_Q_RANGE = (0.5, 2.0)
#: The base of the first-order pole (not e).
POLE_BASE = 2.7
#: The EQ band kinds, in the ledger's spelling.
EQ_KINDS = ("PK", "LSH", "HSH", "NOTCH", "BP", "APF1", "APF2", "HP1", "LP1", "HP2", "LP2")
_EQ_SPELLINGS = {"LS": "LSH", "HS": "HSH", "AP1": "APF1", "AP2": "APF2"}


class NotRecorded(Exception):
    """A setting the response depends on that the project has not recorded: the peak mode or the corner set.

    `is_unmodelled` so `predict`'s `main` says it in one line, exit 1, as it says a family it has no model for."""
    is_unmodelled = True


def peak_mode_question():
    return ("which peak mode is the DSP program set to: «REW-compatible peak» or «gain-dependent bandwidth peak»? "
            "Record the tuner's answer: project.py <dir> set-dsp-setting peak_mode rew|gain_dependent --source user")


def corner_set_question():
    return ("which corner set is the preset's crossover correction on: default corners, normalised to -3 dB or "
            "normalised to -6 dB? Record the tuner's answer: project.py <dir> set-dsp-setting corner_set "
            "default|minus_3db|minus_6db --source user")


# ---------------------------------------------------------------------------------------- 8.24 fixed point
def q824_word(x):
    """`x` as the hardware stores it: x*2^24 truncated toward zero, a 32-bit two's complement word."""
    i = int(x * 2 ** 24)                 # int() truncates toward zero
    return ((i + 2 ** 31) % 2 ** 32) - 2 ** 31


def q824(x):
    """`x` after the hardware's 8.24 quantising, as a float."""
    return q824_word(x) / 2 ** 24


def q824_bytes(x):
    """The four bytes of `q824_word(x)`, big-endian."""
    w = q824_word(x) & 0xFFFFFFFF
    return [(w >> 24) & 255, (w >> 16) & 255, (w >> 8) & 255, w & 255]


# ---------------------------------------------------------------------------------------- sections
def _biquad(freqs_hz, c, fs, quantise=True):
    """Response of one normalised section `c = (b0, b1, b2, a1, a2)` at `fs`; quantised as the hardware runs it."""
    b0, b1, b2, a1, a2 = c
    if quantise:                        # b as stored; a stored negated, so -a is what is cut to 8.24
        b0, b1, b2, a1, a2 = q824(b0), q824(b1), q824(b2), -q824(-a1), -q824(-a2)
    z1 = np.exp(-1j * 2 * np.pi * np.asarray(freqs_hz, dtype=float) / fs)
    return (b0 + (b1 + b2 * z1) * z1) / (1.0 + (a1 + a2 * z1) * z1)


def _xo_section(order, kind, f, q, fs):
    """One crossover stage: `(b0, b1, b2, a1, a2)` and the three words it is stored as."""
    if order == 0:
        return (1.0, 0.0, 0.0, 0.0, 0.0), (0.0, 0.0, 1.0)
    w0 = 2 * math.pi * f / fs
    s, c = math.sin(w0), math.cos(w0)
    hp = kind == "hp"
    if order == 1:
        if hp:
            a0 = 1 + s / 2
            a1, b0 = -(1 - s / 2) / a0, 1 / a0
            return (b0, -b0, 0.0, a1, 0.0), (-a1, b0, 0.0)
        p = POLE_BASE ** -w0
        return (1 - p, 0.0, 0.0, -p, 0.0), (p, 1 - p, 0.0)
    q = min(max(q, SECTION_Q_RANGE[0]), SECTION_Q_RANGE[1])
    alpha = s / (2 * q)
    a0 = 1 + alpha
    a1, a2 = -2 * c / a0, (1 - alpha) / a0
    b0 = ((1 + c) if hp else (1 - c)) / 2 / a0
    return (b0, -2 * b0 if hp else 2 * b0, b0, a1, a2), (-a1, -a2, b0)


def crossover_sections(family, slope, corner_hz, kind, corner_set, fs):
    """The two stages of one leg: `[(order, section, stored words), (order, section, stored words)]`."""
    fam = _FAMILY_SPELLINGS.get(str(family).upper())
    if fam is None or slope not in SECTION_ORDERS or kind not in ("hp", "lp") or corner_set not in CORNER_K:
        raise ValueError(f"crossover {family}{slope} {kind} on corner set {corner_set!r}: families "
                         f"{'/'.join(FAMILIES)}, slopes {'/'.join(map(str, SLOPES))}, kind hp|lp, corner sets "
                         f"{'/'.join(CORNER_SET_ORDER)}")
    ks = CORNER_K[corner_set][fam].get(slope, (1, 1))
    qs = SECTION_Q[fam].get(slope, (None, None))
    out = []
    for order, k, q in zip(SECTION_ORDERS[slope], ks, qs):
        f = corner_hz / k if kind == "hp" else corner_hz * k
        f = min(max(f, SECTION_F_RANGE_HZ[0]), SECTION_F_RANGE_HZ[1])
        out.append((order,) + _xo_section(order, kind, f, q, fs))
    return out


def crossover_response(freqs_hz, corner_hz, slope, kind, family, corner_set, fs, quantise=True):
    """Complex response of one HP ('hp') or LP ('lp') leg at the DSP's rate `fs`."""
    h = np.ones(len(np.atleast_1d(freqs_hz)), dtype=complex)
    for _order, section, _stored in crossover_sections(family, slope, corner_hz, kind, corner_set, fs):
        h = h * _biquad(freqs_hz, section, fs, quantise)
    return h


def crossover_block(family, slope, corner_hz, kind, corner_set, fs):
    """The 26 bytes a leg's coefficients are stored as: per stage three 8.24 words and a check byte (sum & 255)."""
    out = []
    for _order, _section, stored in crossover_sections(family, slope, corner_hz, kind, corner_set, fs):
        words = [b for v in stored for b in q824_bytes(v)]
        out += words + [sum(words) & 255]
    return out


def eq_section(kind, f0, gain_db, q, fs, peak_mode=None):
    """One EQ band as a normalised section `(b0, b1, b2, a1, a2)`. A peak needs `peak_mode` (a `PEAK_MODES` key)."""
    kind = _EQ_SPELLINGS.get(str(kind).upper(), str(kind).upper())
    if kind in ("HP1", "LP1", "HP2", "LP2"):
        return _xo_section(int(kind[2]), kind[:2].lower(), f0, q if q is not None else 0.707, fs)[0]
    if kind not in EQ_KINDS:
        raise ValueError(f"EQ band {kind!r}: the kinds are {', '.join(EQ_KINDS)}")
    w0 = 2 * math.pi * f0 / fs
    s, c = math.sin(w0), math.cos(w0)
    A = 10 ** ((gain_db or 0.0) / 40)
    if kind == "APF1":
        p = POLE_BASE ** -w0
        return (-p, 1.0, 0.0, -p, 0.0)
    if q is None:
        raise ValueError(f"{kind} at {f0:g} Hz has no Q: this DSP's {kind} depends on it")
    alpha = s / (2 * q)
    if kind == "PK":
        if peak_mode not in PEAK_MODES:
            raise NotRecorded(f"peak at {f0:g} Hz on a Mosconi / Gladen DSP: the peak mode is "
                              f"{'not recorded' if peak_mode is None else repr(peak_mode)} -- ask the tuner "
                              f"{peak_mode_question()}")
        if peak_mode == "gain_dependent":   # the bandwidth follows the gain, in three branches
            width = 0.8 if gain_db >= 0 else (-gain_db / 4 if gain_db < -4 else 1.0)
            alpha = s / (width * A * q)
        b, a = (1 + alpha * A, -2 * c, 1 - alpha * A), (1 + alpha / A, -2 * c, 1 - alpha / A)
    elif kind in ("LSH", "HSH"):
        S = min(q, 3.0)
        alpha = s / 2 * math.sqrt((A + 1 / A) * (1 / S - 1) + 2)
        sa, sign = 2 * math.sqrt(A) * alpha, (1 if kind == "LSH" else -1)
        b = (A * ((A + 1) - sign * (A - 1) * c + sa), sign * 2 * A * ((A - 1) - sign * (A + 1) * c),
             A * ((A + 1) - sign * (A - 1) * c - sa))
        a = ((A + 1) + sign * (A - 1) * c + sa, -sign * 2 * ((A - 1) + sign * (A + 1) * c),
             (A + 1) + sign * (A - 1) * c - sa)
    elif kind == "NOTCH":
        b, a = (1.0, -2 * c, 1.0), (1 + alpha, -2 * c, 1 - alpha)
    elif kind == "BP":
        b, a = (alpha, 0.0, -alpha), (1 + alpha, -2 * c, 1 - alpha)
    else:                               # APF2
        b, a = (1 - alpha, -2 * c, 1 + alpha), (1 + alpha, -2 * c, 1 - alpha)
    return (b[0] / a[0], b[1] / a[0], b[2] / a[0], a[1] / a[0], a[2] / a[0])


def eq_response(freqs_hz, bands, fs, peak_mode=None, quantise=True):
    """Complex response of an EQ bank `[(kind, f0, gain_db, q), ...]`."""
    h = np.ones(len(np.atleast_1d(freqs_hz)), dtype=complex)
    for kind, f0, gain_db, q in bands:
        h = h * _biquad(freqs_hz, eq_section(kind, f0, gain_db, q, fs, peak_mode), fs, quantise)
    return h


# ---------------------------------------------------------------------------------------- the desk's hook
class Model:
    """What `dsp_math.bind_response_model` takes: `xo_response` and `eq_complex` with `dsp_math`'s signatures."""
    name = "mosconi_gladen"

    def __init__(self, corner_set=None, peak_mode=None):
        self.corner_set, self.peak_mode = corner_set, peak_mode

    def xo_response(self, freqs_hz, corner_hz, order_db_per_oct, kind, ftype, fs):
        if self.corner_set is None:
            raise NotRecorded(f"crossover {ftype}{order_db_per_oct} at {corner_hz:g} Hz on a Mosconi / Gladen DSP: "
                              f"the corner set is not recorded -- ask the tuner {corner_set_question()}")
        return crossover_response(freqs_hz, corner_hz, order_db_per_oct, kind, ftype, self.corner_set, fs)

    def eq_complex(self, freqs_hz, bands, fs):
        return eq_response(freqs_hz, bands, fs, self.peak_mode)


def is_this_vendor(profile):
    """True when a `dsp_profile` (on-disk or inner shape) names Mosconi or Gladen as its vendor."""
    inner = profile.get("dsp_profile", profile) if isinstance(profile, dict) else None
    vendor = str((inner or {}).get("vendor") or "").strip().lower()
    return any(word in vendor for word in ("mosconi", "gladen"))


class BadSetting(ValueError):
    """A `dsp.settings` value in `project.json` this model has no name for (one edited by hand): `is_unreadable`, so
    `predict`'s `main` says it in one line, exit 1, as it says a project file it cannot read."""
    is_unreadable = True


def settings_of(project_data):
    """`(corner_set, peak_mode)` recorded in `project.json` `dsp.settings`, each None when not recorded. A value the
    model has no name for raises `BadSetting`, naming the repair."""
    raw = (((project_data or {}).get("dsp") or {}).get("settings") or {})

    def value(key, allowed):
        x = raw.get(key)
        x = x.get("value") if isinstance(x, dict) else x
        if x is None:
            return None
        if x not in allowed:
            raise BadSetting(f"project.json dsp.settings.{key} is {x!r}: one of {', '.join(allowed)} -- record the "
                             f"tuner's answer again: project.py <dir> set-dsp-setting {key} {'|'.join(allowed)} "
                             f"--source user")
        return x
    return value("corner_set", CORNER_SET_ORDER), value("peak_mode", tuple(PEAK_MODES))


def model_for(profile, project_data):
    """This vendor's `Model` with the project's recorded settings, or None for any other vendor's profile."""
    if not is_this_vendor(profile):
        return None
    return Model(*settings_of(project_data))


def _siblings():
    """`rew_tool/siblings.py`, by its path: how this module reaches a sibling (skill #137).

    The same text in every module that loads a sibling -- only the `here` line differs with the file's folder;
    scripts/contract-guard.py holds the copies identical.
    """
    import hashlib
    import importlib.util
    here = os.path.dirname(os.path.realpath(__file__))
    name = "_autosound_" + hashlib.sha1(here.encode("utf-8")).hexdigest()[:8] + "_siblings"
    module = sys.modules.get(name)
    if module is None:
        spec = importlib.util.spec_from_file_location(name, os.path.join(here, "siblings.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # Published only once it has run: a thread racing this first call never gets a half-run siblings.py.
        module = sys.modules.setdefault(name, module)
    return module


def bind(profile, project_data):
    """Bind this model into `dsp_math` for a Mosconi / Gladen profile, or unbind it for any other. Returns a note.

    The hook is reset first, before anything here can raise: a setting refused (`BadSetting`) leaves the generic
    model, never the model of a project read before this one."""
    dsp_math = _siblings().load("dsp_math.py")
    dsp_math.reset_response_model()
    model = model_for(profile, project_data)
    if model is None:
        return None
    dsp_math.bind_response_model(model)
    missing = [q for q, v in ((corner_set_question(), model.corner_set), (peak_mode_question(), model.peak_mode))
               if v is None]
    return ("Mosconi / Gladen filter model bound (corner set "
            f"{CORNER_SETS.get(model.corner_set, 'not recorded')}, peak mode "
            f"{PEAK_MODES.get(model.peak_mode, 'not recorded')})"
            + ("".join(f"; to ask: {q}" for q in missing)))


def note_without_profile(project_data):
    """The note for a project `project.json` names as this vendor's that has no `dsp_profile.json`: its DSP is modelled
    by the generic model, said once. None for any other vendor's project."""
    vendor = str((((project_data or {}).get("dsp") or {}).get("vendor")) or "").strip()
    if not is_this_vendor({"vendor": vendor}):
        return None
    return f"{vendor} project, no dsp_profile.json: the generic model is used"


def bind_for_project(project_dir):
    """`bind` for a project folder: its `dsp_profile.json` and `project.json`, read only. With no profile, a project
    whose `project.json` names this vendor gets the generic model and one note saying so (`note_without_profile`)."""
    if not project_dir:
        return bind(None, None)
    _siblings().load("dsp_math.py").reset_response_model()     # before a read below can raise
    dsp_profile = _siblings().load("dsp_profile.py")
    project_io = _siblings().load("project_io.py")
    path = os.path.join(project_dir, "dsp_profile.json")
    pj = os.path.join(project_dir, "project.json")
    profile = dsp_profile.load_profile(path) if os.path.exists(path) else None
    if not is_this_vendor(profile):
        bind(None, None)
        if profile is None and os.path.exists(pj):
            try:
                data = project_io.read_json(pj)
            except Exception as exc:  # noqa: BLE001 -- a note only: the run's own read of project.json refuses it
                if not (isinstance(exc, (OSError, ValueError)) or getattr(type(exc), "is_unreadable", False)):
                    raise
                return None
            return note_without_profile(data)
        return None
    return bind(profile, project_io.read_json(pj) if os.path.exists(pj) else None)


# ---------------------------------------------------------------------------------------- selftest
#: The vector grid: 48 log-spaced points, 10 Hz to 24 kHz; the cases below read six (crossovers) or three (EQ).
def _grid(indices):
    return np.array([10.0 * 2400.0 ** (i / 47.0) for i in indices])


_XO_AT = (5, 14, 22, 32, 38, 44)          # 22.9, 101.6, 382.1, 2001.8, 5406.8, 14603.4 Hz
#: Transcribed from the contributor's vectors (#214): (family, slope, corner set, kind, Hz, magnitude dB, phase deg).
#: Stored to 4 decimals (dB) and 3 (deg): tolerance 0.001 dB, 0.01 deg. fs 96 kHz.
_XO_CASES = (
    ("LR", 6, "default", "hp", 2000, (-43.6199, -30.6779, -19.219, -6.0203, -1.473, -0.2041),
     (89.622, 88.324, 83.719, 59.999, 32.434, 12.373)),
    ("LR", 12, "minus_6db", "hp", 2000, (-77.6833, -51.8134, -29.0867, -6.0128, -1.0951, -0.138),
     (178.691, 174.192, 158.395, 89.948, 40.262, 14.425)),
    ("LR", 24, "minus_3db", "lp", 80, (-0.0962, -6.3598, -46.6774, -104.2208, -139.0569, -176.0028),
     (-37.69, 177.507, 43.34, 8.092, 2.967, 1.024)),
    ("BE", 12, "default", "hp", 2000, (-73.2732, -47.6343, -24.8692, -2.9743, -0.3658, -0.0421),
     (178.566, 173.632, 156.052, 74.271, 28.481, 9.839)),
    ("BE", 18, "minus_6db", "lp", 80, (-0.4429, -9.5, -40.363, -83.3371, -109.3405, -136.158),
     (-39.503, -157.0, 120.702, 99.449, 102.227, 118.103)),
    ("BW", 6, "minus_3db", "lp", 80, (-0.3462, -4.2074, -13.8251, -28.026, -36.6113, -44.953),
     (-16.025, -51.779, -77.538, -83.977, -79.029, -62.331)),
    ("BW", 18, "default", "lp", 80, (-0.0449, -7.2238, -40.8387, -84.0104, -110.0195, -136.8334),
     (-33.323, -167.517, 114.812, 98.312, 101.81, 117.959)),
    ("BW", 24, "minus_6db", "hp", 2000, (-160.2187, -108.4367, -62.4068, -6.0601, -0.0054, -0.0002),
     (-1.488, -6.607, -24.942, -151.427, 64.872, 21.856)),
    ("CH", 12, "minus_3db", "hp", 2000, (-81.7435, -56.0814, -32.9898, -3.1142, 0.8196, 0.1127),
     (179.489, 177.73, 171.343, 116.539, 31.082, 9.456)),
    ("CH", 24, "default", "lp", 80, (0.1447, -6.6632, -53.7601, -111.4638, -146.3041, -183.2519),
     (-38.532, 129.146, 28.821, 5.438, 1.994, 0.689)),
)
#: The stored blocks of three of those legs (the 8.24 words and check bytes), exact.
_XO_BLOCKS = (
    (("LR", 6, "default", "hp", 2000),
     (0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 203, 194, 215, 0, 229, 225, 107, 0, 0, 0, 0, 149)),
    (("BW", 24, "minus_6db", "hp", 2000),
     (1, 222, 195, 39, 255, 27, 196, 88, 0, 240, 191, 180, 98, 1, 188, 158, 252, 255, 62, 76, 99, 0, 223, 148, 166, 92)),
    (("CH", 24, "default", "lp", 80),
     (1, 253, 168, 100, 255, 2, 85, 196, 0, 0, 0, 117, 153, 1, 255, 39, 62, 255, 0, 214, 233, 0, 0, 0, 118, 153)),
)
_EQ_AT = (22, 28, 32)                     # 382.1, 1032.2, 2001.8 Hz
#: Peak 1 kHz, Q 2, fs 96 kHz: (mode, gain dB, quantised b0 b1 b2, quantised -a1 -a2, magnitude dB). Tolerance 0.001.
_EQ_CASES = (
    ("rew", 6.0, (1.0113887786865234, -1.972880780696869, 0.9657251834869385),
     (1.972880780696869, -0.9771139621734619), (0.3056, 5.8979, 0.6306)),
    ("rew", -9.5, (0.9817280769348145, -1.9408852458000183, 0.9633216857910156),
     (1.9408852458000183, -0.9450497627258301), (-0.5323, -9.3201, -1.0793)),
    ("gain_dependent", 6.0, (1.019980549812317, -1.9556523561477661, 0.9398679137229919),
     (1.9556523561477661, -0.9598485231399536), (0.853, 5.967, 1.5845)),
    ("gain_dependent", -3.0, (0.9871050119400024, -1.907601535320282, 0.9245895743370056),
     (1.907601535320282, -0.9116945862770081), (-0.6668, -2.9913, -1.1556)),
    ("gain_dependent", -9.5, (0.9737424254417419, -1.9169209003448486, 0.9472915530204773),
     (1.9169209003448486, -0.9210339784622192), (-1.0417, -9.4138, -1.9712)),
)


def _wrap_deg(d):
    return (d + 180.0) % 360.0 - 180.0


def _selftest():
    fs = 96000.0
    failures = []

    # the transcribed tables are there: a table cut to nothing would let every loop below pass on no case at all
    for name, table in (("_XO_CASES", _XO_CASES), ("_XO_BLOCKS", _XO_BLOCKS), ("_EQ_CASES", _EQ_CASES),
                        ("SECTION_Q", SECTION_Q), ("CORNER_K", CORNER_K), ("SECTION_ORDERS", SECTION_ORDERS)):
        if not table:
            failures.append(f"{name} is empty: the selftest checks nothing against it")
    for cset in CORNER_SET_ORDER:
        if not CORNER_K.get(cset):
            failures.append(f"CORNER_K holds no corners for the set {cset!r}")
    if {mode for mode, *_rest in _EQ_CASES} != set(PEAK_MODES) or {c[0] for c in _XO_CASES} != set(FAMILIES):
        failures.append("the vectors do not cover both peak modes and every family")

    # crossovers: magnitude and phase, every family and slope, all three corner sets, both kinds
    f = _grid(_XO_AT)
    for family, slope, cset, kind, hz, mag, ph in _XO_CASES:
        h = crossover_response(f, hz, slope, kind, family, cset, fs)
        dm = np.max(np.abs(20 * np.log10(np.abs(h)) - np.array(mag)))
        dp = np.max(np.abs(_wrap_deg(np.degrees(np.angle(h)) - np.array(ph))))
        if dm > 1e-3 or dp > 1e-2:
            failures.append(f"{family}{slope} {kind} {hz} Hz {cset}: off by {dm:.4f} dB / {dp:.3f} deg")

    # 8.24: the stored blocks, byte for byte, and the quantiser itself on a few words
    for (family, slope, cset, kind, hz), want in _XO_BLOCKS:
        got = tuple(crossover_block(family, slope, hz, kind, cset, fs))
        if got != want:
            failures.append(f"{family}{slope} {kind} {cset}: stored block {got} != {want}")
    for x, word in ((1.0, 0x01000000), (-1.0, -0x01000000), (0.5 + 2 ** -25, 0x00800000),
                    (-(0.5 + 2 ** -25), -0x00800000), (128.0, -2 ** 31)):
        if q824_word(x) != word:
            failures.append(f"q824_word({x!r}) = {q824_word(x)} != {word} (truncated toward zero, 32-bit wrap)")
    if q824_bytes(-1.0) != [255, 0, 0, 0]:
        failures.append(f"q824_bytes(-1.0) = {q824_bytes(-1.0)}")

    # peaks: both modes, the three gain branches of the gain-dependent one; coefficients and magnitude
    f = _grid(_EQ_AT)
    for mode, g, b, minus_a, mag in _EQ_CASES:
        c = eq_section("PK", 1000.0, g, 2.0, fs, peak_mode=mode)
        got_b, got_ma = tuple(q824(x) for x in c[:3]), (q824(-c[3]), q824(-c[4]))
        if got_b != b or got_ma != minus_a:
            failures.append(f"peak {mode} {g:+} dB: coefficients {got_b} {got_ma} != {b} {minus_a}")
        h = eq_response(f, [("PK", 1000.0, g, 2.0)], fs, peak_mode=mode)
        dm = np.max(np.abs(20 * np.log10(np.abs(h)) - np.array(mag)))
        if dm > 1e-3:
            failures.append(f"peak {mode} {g:+} dB: magnitude off by {dm:.4f} dB")

    # a peak band with no recorded mode is refused, naming the question; a peak-free bank needs none
    try:
        eq_response(f, [("PK", 1000.0, -3.0, 2.0)], fs, peak_mode=None)
        failures.append("a peak with no recorded mode was modelled")
    except NotRecorded as exc:
        if "«REW-compatible peak» or «gain-dependent bandwidth peak»" not in str(exc) \
                or "set-dsp-setting peak_mode" not in str(exc):
            failures.append(f"the peak refusal does not name the question: {exc}")
    eq_response(f, [("APF2", 1000.0, 0.0, 0.7), ("LSH", 80.0, 3.0, 0.7)], fs, peak_mode=None)

    # the hook: a Mosconi profile routes dsp_math to this model, any other profile does not
    dsp_math = _siblings().load("dsp_math.py")
    mosconi = {"dsp_profile": {"vendor": "Mosconi", "name": "PICO 6/8-2 DSP", "groups": []}}
    helix = {"dsp_profile": {"vendor": "Audiotec-Fischer", "name": "Helix DSP Ultra S", "groups": []}}
    project = {"dsp": {"settings": {"corner_set": {"value": "minus_6db", "source": "user", "at": None},
                                    "peak_mode": {"value": "gain_dependent", "source": "user", "at": None}}}}
    fx = _grid(_XO_AT)
    try:
        dsp_math.reset_response_model()
        generic = dsp_math.xo_response(fx, 2000.0, 24, "hp", "BW", fs=fs)
        bind(mosconi, project)
        routed = dsp_math.xo_response(fx, 2000.0, 24, "hp", "BW", fs=fs)
        if np.max(np.abs(routed - crossover_response(fx, 2000.0, 24, "hp", "BW", "minus_6db", fs))) > 1e-12:
            failures.append("a Mosconi profile did not route dsp_math.xo_response to this model")
        peq = dsp_math.eq_complex(f, [("PK", 1000.0, -3.0, 2.0)])
        if np.max(np.abs(20 * np.log10(np.abs(peq)) - np.array(_EQ_CASES[3][4]))) > 1e-3:
            failures.append("a Mosconi profile did not route dsp_math.eq_complex to this model's recorded mode")
        bind(helix, project)
        if np.max(np.abs(dsp_math.xo_response(fx, 2000.0, 24, "hp", "BW", fs=fs) - generic)) > 1e-12:
            failures.append("another vendor's profile was routed to this model")
        bind(mosconi, {"dsp": {}})
        try:
            dsp_math.eq_complex(f, [("PK", 1000.0, -3.0, 2.0)])
            failures.append("bound with no recorded peak mode, a peak was modelled")
        except NotRecorded:
            pass
        # a hand-edited setting the model has no name for: a refusal of one line (`is_unreadable`, as a project file
        # that cannot be read), and the project before it does not stay bound
        bind(mosconi, project)
        try:
            bind(mosconi, {"dsp": {"settings": {"peak_mode": {"value": "classic", "source": "user", "at": None}}}})
            failures.append("a peak mode 'classic' was bound")
        except Exception as exc:  # noqa: BLE001 -- read by its attributes
            if not getattr(type(exc), "is_unreadable", False) or "'classic'" not in str(exc) \
                    or "set-dsp-setting peak_mode" not in str(exc):
                failures.append(f"a peak mode 'classic' is not refused in one line naming the repair: {exc!r}")
        if dsp_math._MODEL["impl"] is not None:
            failures.append("a refused setting left the previous project's model bound")
        # a Mosconi project with no dsp_profile.json: one note that the generic model is used
        note = note_without_profile({"dsp": {"vendor": "Mosconi", "model": "PICO 6/8-2 DSP"}})
        if not note or "no dsp_profile.json" not in note or "generic model" not in note:
            failures.append(f"a Mosconi project with no profile says nothing of the generic model: {note!r}")
        if note_without_profile({"dsp": {"vendor": "Audiotec-Fischer"}}) is not None:
            failures.append("another vendor's project with no profile got the Mosconi note")
    finally:
        dsp_math.reset_response_model()

    # what project.py records is what this model reads
    recorded = _siblings().load("project.py").DSP_SETTINGS
    if recorded != {"peak_mode": tuple(PEAK_MODES), "corner_set": CORNER_SET_ORDER}:
        failures.append(f"project.py DSP_SETTINGS {recorded} is not this model's peak modes and corner sets")

    # no write path: the source opens nothing for writing and moves or removes no file
    with open(os.path.abspath(__file__), encoding="utf-8") as fh:
        src = fh.read()
    modes = [quote + m + quote for m in "w wb a x".split() for quote in "\"'"]
    for banned in modes + ["write_" + "bytes", "write_" + "text", "os." + "rename", "os." + "replace", "sh" + "util",
                           "os." + "remove", "un" + "link"]:
        if banned in src:
            failures.append(f"the module holds {banned}: it has no write path")

    if failures:
        for line in failures:
            print("FAIL", line)
        return 1
    print(f"mosconi_gladen selftest OK: {len(_XO_CASES)} crossover legs (LR/BE/BW/CH, 6/12/18/24, all three corner "
          f"sets, HP and LP) match the contributed vectors in magnitude and phase; {len(_XO_BLOCKS)} stored blocks "
          f"byte for byte and the 8.24 quantiser truncates and wraps; {len(_EQ_CASES)} peaks in both modes match "
          f"coefficients and magnitude; a peak with no recorded mode is refused naming the question; a Mosconi "
          f"profile routes dsp_math to this model and another profile does not; no write path.")
    return 0


if __name__ == "__main__":
    import console                       # issue #21: a code page must not destroy a result
    console.install()
    if len(sys.argv) > 1 and sys.argv[1] in ("selftest", "--selftest"):
        sys.exit(_selftest())
    print("usage: python3 mosconi_gladen.py --selftest")
