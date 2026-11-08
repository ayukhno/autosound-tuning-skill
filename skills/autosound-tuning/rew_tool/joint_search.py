#!/usr/bin/env python3
"""joint_search -- the search behind the joint-by-joint approach (#210): the joints from the roles, the bass joint.

One raw capture, then the joints from the bottom up, each joint a search over the filter space that scores and ranks
the variants. This module holds the engine and, in this build, the BASS joint: sub low-pass x next role's high-pass x
sub level x polarity x sub/front delay, the front's L-R offset held. The joints above the bass come later, on the same
engine (`docs/PLAN-W-12.md`, T14).

The joints come from `xover_wishes.ROLE_ORDER` over the channels present, each adjacent pair one joint: 3-way + sub, 2-way +
sub, a front sub are the same code. Everything searched comes from the project: the families (`dsp_math.options_for`),
corners (the profile's range and step), gain and delay limits, Fs. The grid is the joint's, not the hardware's: corner bounds
from a role table, 1/6-oct steps. Its size is printed before the run and over a ceiling it refuses without a flag.

    python3 rew_tool/joint_search.py --project DIR --house FILE --solos DIR [--json] [--out DIR] [--front-lp FAM ORD HZ]
                                     [--no-leak] [--no-dip] [--no-lr-offset]
    python3 rew_tool/joint_search.py --project DIR --house FILE --rew --ver N
    python3 rew_tool/joint_search.py --selftest

Read-only: it prints a table, `--json`, `--out DIR`. The table is what a person keys in: each channel's filter, gain and
delay, inside the DSP's ranges and on its steps. It never banks and never picks; the last line says so. Each refusal is one
line, `refusing: <why>`, exit 3; a search that finds nothing says so in words with the reasons counted, exit 0.
"""
from __future__ import annotations

import json
import math
import os
import sys
from dataclasses import dataclass, field

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import crossover_checks as _cc                   # noqa: E402
import dsp_math                                  # noqa: E402
import dsp_profile as _dp                        # noqa: E402
import naming                                    # noqa: E402
import predict as P                              # noqa: E402
import project as _pj                            # noqa: E402
import project_io                                # noqa: E402
import target_bands                              # noqa: E402
import windows                                   # noqa: E402
import xover_wishes as _xw                       # noqa: E402


class JointSearchError(ValueError):
    """A refusal of this tool: one line, `refusing: <why>`, exit 3."""

    is_refusal = True


# ---------------------------------------------------------------- method constants, each with its source
#: The ±30° band through the acoustic crossing: the Arbiter's metric (18.10), `swws_xo.py:124`.
PHASE_WINDOW_DEG = 30.0
#: The sum against the target may not fall below this in the joint's band (a peak is EQ's to cut; a dip is not):
#: `swws_search2.py:7,56`.
DIP_LIMIT_DB = -3.5
#: The sub's leak above the joint, sub minus front, relative to the row's crossing. `swws_search2.py:6,44` read it at 100 Hz and
#: over 125-200 Hz, which belong to one car's crossing near 65 Hz: 100 Hz is 1.5x that crossing, 125-200 Hz is 2-3x it.
LEAK_NEAR_RATIO = 1.5
LEAK_NEAR_DB = -24.0
LEAK_FAR_RATIOS = (2.0, 3.0)
LEAK_FAR_DB = -30.0
#: The floor of a high-pass, times the driver's installed Fs. Mid: the run's value (#210); tweeter: `fs_margin`'s convention.
#: A woofer is not on this list (`xover_wishes.FRAGILE_ROLES`): its margin is shown per row, not filtered on.
HP_FS_FLOOR = {"midrange": 1.45, "tweeter": _cc.FS_MARGIN_DEFAULT}
#: (delay L - delay R) = -(raw arrival L - raw arrival R) within this: `stage_lock.py:7-12`.
LR_OFFSET_TOLERANCE_MS = 0.10
#: A sub may stay at one point while its crossing is under this: lambda > 3.4 m, `swws_xo.py:69`.
SUB_ONE_POINT_MAX_HZ = 100.0
#: A person's decision to run on one point, in these words: `process.py <dir> decision "<these words>" "<the person's words>"`.
#: Both halves are checked: that the nine points were skipped, and that the joints run on one point (`_single_point_decided`).
SINGLE_POINT_SKIP_WORDS = "nine points skipped"
SINGLE_POINT_ONE_WORDS = "joints run on one point"
SINGLE_POINT_DECISION = f"{SINGLE_POINT_SKIP_WORDS}; the {SINGLE_POINT_ONE_WORDS}"
#: A recorded answer starting with one of these is the person saying no to the question that carried the words.
_NO_WORDS = ("no", "nope", "ні", "нi", "нет")
#: The grid: 1/6-oct corners over the joint's bounds, then +-1/12 oct around the shortlist (PLAN-W-12, the grid).
CORNER_STEP_OCT = 1.0 / 6.0
CORNER_REFINE_OCT = 1.0 / 12.0
#: About twice the design's ~29,000 filter pairs a joint: over it the run refuses without `--allow-large-grid`. The count is
#: filter pairs times L-R offsets (`--no-lr-offset` is 25 offsets): the combinations the scan really walks.
GRID_CEILING_PAIRS = 60000
#: Rows held at once per crossing band while the grid is walked. The reference-point scan yields many rows per pair; only the
#: best per band can reach the shortlist, so anything past this is settled and the rest dropped, counted (`past_shortlist`).
#: The memory of a run stays one filter-response bank (about 24 kB per filter option) plus this, whatever the grid's size.
ROW_BUFFER_PER_BAND = 2000
#: Delay of the front against the sub: coarse over +-`delay.max_ms`, then fine around the best (`swws_xo.py:194,218`).
DELAY_COARSE_STEP_MS = 0.2
DELAY_FINE_SPAN_MS = 1.0
DELAY_FINE_STEP_MS = 0.05
#: Candidates per crossing band carried from the reference point to every point (`swws_xo.py:221`).
SHORTLIST_PER_BAND = 40
#: A free L-R offset, only with the stage condition off, around the raw offset (a free per-side search moved it by up to
#: 1 ms, #210 §4; the bass joint tolerates more before the front's L+R sum turns, so the window is wider than that).
FREE_OFFSET_SPAN_MS = 3.0
FREE_OFFSET_STEP_MS = 0.25
#: Sub level relative to the front: a wide default around unity, the project's range limits it (`--gain` replaces it).
GAIN_GRID_DB = (-6.0, 12.0, 2.0)
#: Reading under 1 kHz: IR 5 ms before to 500 ms after its peak, a 10 % cosine tail, 1/6-oct vector average (`swws_xo.py:45-56`).
WINDOW_BEFORE_MS = 5.0
WINDOW_AFTER_MS = 500.0
WINDOW_TAIL_FRACTION = 0.1
SMOOTH_OCT = 1.0 / 6.0
#: Points per octave of the search grid.
GRID_PPO = 96
#: The band each role's raw arrival is read in (`windows.arrival_between`) and its gate.
ARRIVAL_READ = {"sub": ((30.0, 100.0), 30.0), "woofer": ((200.0, 800.0), 5.0), "midrange": ((1000.0, 4000.0), 5.0),
                "tweeter": ((1000.0, 4000.0), 5.0)}
#: Rows per crossing band in the table.
TOP_DEFAULT = 10
#: The width of the crossing bands the results are listed by, in octaves.
BAND_WIDTH_OCT = 0.25
POSITIONS = tuple(f"p{i}" for i in range(1, 10))
CENTRE_POINTS = ("p1", "p5", "p9")


@dataclass(frozen=True)
class JointClass:
    """The bounds and bands of one kind of joint. The table below grows with the joints above the bass."""
    name: str
    lp_bounds: tuple
    hp_bounds: tuple
    crossing_window: tuple
    grid_hz: tuple
    dip_band: tuple
    dip_fit_band: tuple


#: Bounds per joint (PLAN-W-12: "bass 40-125 Hz"), overridable by `--lp-bounds` / `--hp-bounds`; the crossing window, the dip
#: band and its offset-fit band are `swws_xo.py:102` and `swws_search2.py:21-22`.
JOINT_CLASSES = {
    # the grid reaches 3x the top of the crossing window: the far leak band of a crossing at 200 Hz is 400-600 Hz
    "bass": JointClass("bass", (40.0, 125.0), (40.0, 125.0), (35.0, 200.0), (20.0, 630.0), (45.0, 110.0), (100.0, 250.0)),
}


# ---------------------------------------------------------------- the stack of joints
@dataclass(frozen=True)
class Branch:
    """One side of a joint: one channel, or a real L/R pair summed with its offset held."""
    role: str
    codes: tuple

    @property
    def single(self):
        return len(self.codes) == 1

    @property
    def left(self):
        return self.codes[0]

    @property
    def right(self):
        return self.codes[1] if not self.single else None


@dataclass(frozen=True)
class Joint:
    lower: Branch
    upper: Branch

    @property
    def name(self):
        return f"{self.lower.role}-{self.upper.role}"

    @property
    def cls(self):
        return "bass" if self.lower.role == "sub" else self.name


def _branch(role, codes):
    codes = sorted(codes)
    if len(codes) == 1:
        return Branch(role, (codes[0],))
    left = [c for c in codes if c.endswith("-L")]
    right = [c for c in codes if c.endswith("-R")]
    if len(codes) == 2 and len(left) == 1 and len(right) == 1:
        return Branch(role, (left[0], right[0]))
    raise JointSearchError(f"role {role} has {len(codes)} channels ({', '.join(codes)}), neither one nor an L/R pair: "
                           f"this tool cannot tell which of them to sum")


def _stack(channels):
    """`[(role, codes)]` of `xover_wishes.ROLE_ORDER` over the channels present, low to high."""
    stack = []
    for role in _xw.ROLE_ORDER:
        codes = [c for c, row in channels.items() if (row or {}).get("role") == role]
        if codes:
            stack.append((role, codes))
    return stack


def stack_names(channels):
    """The joints of the stack by name, low to high: nothing is built, so a role with four channels is no refusal here."""
    return [f"{a[0]}-{b[0]}" for a, b in zip(_stack(channels), _stack(channels)[1:])]


def joints_of(channels, *, cls=None):
    """The joints of the stack, low to high: only those of class `cls` when given, so a 4-channel tweeter role does not block a
    bass joint it has no part in (M2). `channels`: {code: project row}."""
    stack = _stack(channels)
    out = []
    for (low, low_codes), (high, high_codes) in zip(stack, stack[1:]):
        if cls is None or ("bass" if low == "sub" else f"{low}-{high}") == cls:
            out.append(Joint(_branch(low, low_codes), _branch(high, high_codes)))
    return out


# ---------------------------------------------------------------- the stage conditions
def check_stage(*, rule_ms=None, lr_delay_ms=None):
    """What a candidate breaks of the L-R rule, as a list of words (empty = holds): (delay L - delay R) must equal the signed
    rule -(raw arrival L - raw arrival R) within `LR_OFFSET_TOLERANCE_MS`. Asked for every real L/R pair of a row, on the delays
    the DSP takes (`scan_bass`'s `accept`), so a delay step too coarse to hold the rule shows here. A bass joint gives one polarity
    and one filter to a whole side, so those two conditions have nothing to check until the joints above it are built."""
    why = []
    if rule_ms is not None and lr_delay_ms is not None \
            and abs(float(lr_delay_ms) - float(rule_ms)) > LR_OFFSET_TOLERANCE_MS + 1e-9:
        why.append(f"delay L-R {float(lr_delay_ms):+.2f} ms breaks the rule {float(rule_ms):+.2f} "
                   f"+-{LR_OFFSET_TOLERANCE_MS:g} ms")
    return why


# ---------------------------------------------------------------- the space from the project
def profile_xo(project_dir):
    """The physical outputs' crossover facts, or None: `xover_wishes._profile_xo` (the group), then the profile's top level for
    what the group does not state. A Musway-shaped profile keeps the corner range and step at the top (`musway-m6v4.json:24,28`),
    and without them corners came out off the device's step."""
    xo = _xw._profile_xo(project_dir)
    if xo is None:
        return None
    path = _dp.profile_path(project_dir)
    top = _dp._unwrap(_dp.load_profile(path)).get("crossover_filters") if os.path.isfile(path) else None
    top = top if isinstance(top, dict) else {}
    return {"types": xo.get("types") or top.get("types") or {},
            "range": xo.get("range") if xo.get("range") is not None else top.get("corner_freq_range_hz"),
            "step": xo.get("step") if xo.get("step") is not None else top.get("corner_freq_step_hz")}


@dataclass
class Space:
    """What the project allows: `xo` is `xover_wishes._profile_xo`'s dict."""
    families: list
    xo: dict
    gain_range: tuple
    delay_max_ms: float
    delay_step_ms: float
    rate_note: str = None
    #: What the profile offers and the search left out, named: `["LR6", "LR18", ...]` (`dsp_math` builds other filters for them).
    dropped: list = field(default_factory=list)
    gain_step_db: float = None


@dataclass
class BassInput:
    freqs: np.ndarray
    points: list
    lower: np.ndarray
    upper_l: np.ndarray
    upper_r: np.ndarray
    ref_lower: np.ndarray
    ref_l: np.ndarray
    ref_r: np.ndarray
    lp_options: list
    hp_options: list
    gains_db: tuple
    max_ms: float
    gain_range: tuple
    target_db: np.ndarray = None
    lr_rule_ms: float = 0.0
    free_lr_offset: bool = False
    #: A stereo sub's offset as the DSP holds it (on the delay step), and the raw rule it must stay within: None for one sub.
    lower_offset_ms: float = None
    lower_rule_ms: float = None
    delay_step_ms: float = None
    gain_step_db: float = None
    sub_one_point: bool = False
    hp_floor_hz: float = 0.0
    fs_upper_hz: float = None
    leak_on: bool = True
    dip_on: bool = True
    marks: tuple = ()
    joint: JointClass = JOINT_CLASSES["bass"]
    xo: dict = None
    notes: list = field(default_factory=list)


def space_of(project_dir):
    """The search space from the project's profile, or a refusal. Binds the response model to the DSP's rate."""
    path = _dp.profile_path(project_dir)
    try:
        prof = _dp.load_profile(path)
    except FileNotFoundError:
        raise JointSearchError(f"{path} not found: the search space comes from the project's DSP profile") from None
    try:
        gain_range = _dp.gain_range_db(prof)
    except ValueError as exc:
        raise JointSearchError(f"{path}: {exc} -- correct it in the profile") from None
    if gain_range is None:
        raise JointSearchError(f"{path} states no channel_gain.range_db: the sub level cannot be bounded")
    _rate, rate_note = _dp.bind_model_rate(prof, path=path)
    xo = profile_xo(project_dir)
    if not xo or not xo.get("types"):
        raise JointSearchError(f"{path} lists no crossover families for the physical outputs")
    # Only what `xo_response` builds exactly: an order it would round to another filter is left out, by `target_bands`' own test.
    offered = dsp_math.options_for(xo["types"])
    families = [(fam, order) for fam, order in offered if target_bands._modellable(dsp_math, fam, order)]
    if not families:
        raise JointSearchError(f"{path}: none of its crossover families is one the method can model")
    _rate2, max_ms = P._profile_limits(project_dir)
    if not max_ms:
        raise JointSearchError(f"{path} states no delay.max_ms: the delay search cannot be bounded")
    data = _dp._unwrap(prof)
    step = (data.get("delay") or {}).get("step_ms") if isinstance(data.get("delay"), dict) else None
    gain = data.get("channel_gain") if isinstance(data.get("channel_gain"), dict) else {}
    options = gain.get("step_options_db")
    gain_step = gain.get("step_db") or (min(options) if isinstance(options, list) and options else None)
    return Space(families=families, xo=xo, gain_range=gain_range, delay_max_ms=float(max_ms),
                 delay_step_ms=float(step) if step else None, rate_note=rate_note, dropped=_dropped_options(xo["types"], families),
                 gain_step_db=float(gain_step) if gain_step else None)


def _dropped_options(types, kept):
    """What the profile offers that the search left out, named `LR18`, `BW48`, a family with no orders by its word."""
    names = []
    for fam, spec in (types or {}).items():
        orders = (spec or {}).get("orders_db_per_oct") if isinstance(spec, dict) else None
        if not orders:
            names.append(str(fam))
            continue
        names += [f"{fam}{order}" for order in orders if (fam, order) not in kept]
    return names


def corner_grid(bounds, xo, step_oct=CORNER_STEP_OCT):
    """Corners over `bounds` in `step_oct` steps, snapped to the profile's step and range, ascending, once each."""
    lo, hi = float(bounds[0]), float(bounds[1])
    n = int(math.floor(math.log2(hi / lo) / step_oct + 1e-9))
    corners = {_xw._snap(lo * 2.0 ** (k * step_oct), xo)[0] for k in range(n + 1)}
    return sorted(float(c) for c in corners if lo <= c <= hi)


def filter_options(families, corners, *, floor_hz=0.0):
    """Every (family, order, corner) a side of the joint may take, as lists: the row's form."""
    return [(fam, int(order), float(c)) for fam, order in families for c in corners if c >= floor_hz]


# ---------------------------------------------------------------- the scan: reference point, shortlist, every point
class _Bank:
    """One filter side's responses on the grid, once each."""

    def __init__(self, freqs, kind):
        self._f, self._kind, self._c = freqs, kind, {}

    def get(self, opt):
        key = tuple(opt)
        if key not in self._c:
            h = dsp_math.xo_response(self._f, float(opt[2]), int(opt[1]), self._kind, opt[0])
            self._c[key] = (h, _db(h).astype(np.float32), np.degrees(np.angle(h)).astype(np.float32))
        return self._c[key]


def _db(h):
    return 20.0 * np.log10(np.maximum(np.abs(h), 1e-12))


def _front_sum(left, right, freqs, offset_ms):
    """The summed L+R with L delayed by the held offset; a single channel as it is."""
    if right is None:
        return left
    return left * np.exp(-2j * np.pi * freqs * offset_ms * 1e-3) + right


def _widths(ok, c, step):
    """Per row of `ok` (D, N): the in-tolerance run through column `c`, in octaves (0 if `c` itself fails)."""
    left = ok[:, :c + 1][:, ::-1]
    right = ok[:, c:]
    lc = np.where(left.all(1), left.shape[1], np.argmin(left, 1))
    rc = np.where(right.all(1), right.shape[1], np.argmin(right, 1))
    return np.where(ok[:, c], np.maximum(lc + rc - 2, 0) * step, 0.0)


def _plateau_centre(values):
    """The middle index of the maximum of `values`: on a tie the centre of the plateau, not its first edge."""
    best = np.flatnonzero(values >= values.max() - 1e-9)
    return int(best[len(best) // 2])


def _on_step(value, step):
    return not step or abs(value / step - round(value / step)) < 1e-6


def _gain_split(rel_db, gain_range, step_db=None):
    """(sub dB, front dB) realising a relative sub level inside the channel-gain range and on its step, or None."""
    lo, hi = gain_range
    if rel_db >= 0:
        sub = min(hi, rel_db)
        front = sub - rel_db
    else:
        sub = rel_db
        front = 0.0
    if not (lo <= sub <= hi and lo <= front <= hi) or not (_on_step(sub, step_db) and _on_step(front, step_db)):
        return None
    return float(sub), float(front)


def _snap_ms(value, step):
    """`value` on the DSP's delay step, in floats that compare clean; `None` is no step."""
    return float(value) if not step else round(round(float(value) / step) * step, 6)


def _delay_split(delay_ms, offset_ms, max_ms, single_upper, *, lower_offset_ms=None, step_ms=None):
    """The delays the DSP takes for `delay_ms` (+ front later, - sub later), with the front's and a stereo sub's held L-R offsets
    (delay L - delay R), on the delay step: every value at or above zero with the lowest at zero, or None past the ceiling. A
    single sub is `sub` only; a pair `sub_left` and `sub_right`."""
    delay = _snap_ms(delay_ms, step_ms)
    upper_off = 0.0 if single_upper else _snap_ms(offset_ms, step_ms)
    sub, base = max(0.0, -delay), max(0.0, delay)
    lower_off = 0.0 if lower_offset_ms is None else _snap_ms(lower_offset_ms, step_ms)
    values = {"sub_left": sub + lower_off, "sub_right": sub, "upper_left": base + upper_off, "upper_right": base}
    lowest = min(values.values())
    values = {k: v - lowest for k, v in values.items()}
    if max(values.values()) > max_ms + 1e-9:
        return None
    single_lower = lower_offset_ms is None
    return {"sub": round(values["sub_right"], 6) if single_lower else None,
            "sub_left": None if single_lower else round(values["sub_left"], 6),
            "sub_right": None if single_lower else round(values["sub_right"], 6),
            "upper_left": round(values["upper_left"], 6), "upper_right": None if single_upper else round(values["upper_right"], 6)}


def _who_delays(tas):
    """The side whose lowest channel is above zero takes the delay, the rest hold it at zero: follows `_delay_split`, not the sign
    of the delay (+0.5 ms with a -1.5 ms L-R offset floors L at zero and leaves the sub delayed)."""
    sub = min(v for v in (tas["sub"], tas["sub_left"], tas["sub_right"]) if v is not None)
    upper = min(v for v in (tas["upper_left"], tas["upper_right"]) if v is not None)
    return "sub" if sub > 1e-9 else ("front" if upper > 1e-9 else "none")


def _dip_db(freqs, s, w, target_db, cls):
    """The worst dip of the sum against the target, the offset fitted over the band above the joint."""
    db = _db(s + w)
    fit = (freqs >= cls.dip_fit_band[0]) & (freqs <= cls.dip_fit_band[1])
    band = (freqs >= cls.dip_band[0]) & (freqs <= cls.dip_band[1])
    dev = db - np.mean(db[fit] - target_db[fit]) - target_db
    return float(dev[band].min())


def _band_edges(cls):
    lo, hi = cls.crossing_window
    n = max(1, int(math.ceil(math.log2(hi / lo) / BAND_WIDTH_OCT)))
    return [lo * 2.0 ** (k * BAND_WIDTH_OCT) for k in range(n)] + [hi]


def _band_label(edges, fx):
    for a, b in zip(edges, edges[1:]):
        if a <= fx < b:
            return f"{a:.0f}-{b:.0f} Hz"
    return None


def _crossing(diff_db, m, m0):
    """The first falling zero of the level difference inside the crossing window (index into the grid), or None."""
    d = diff_db[m] > 0
    falls = d[:-1] & ~d[1:]
    if not falls.any():
        return None
    return int(m0 + np.argmax(falls))


def _crossings(diff_db, m, m0, gains):
    """As `_crossing`, for each gain at once: (found mask, indexes)."""
    d = (diff_db[m][None, :] + gains[:, None]) > 0
    falls = d[:, :-1] & ~d[:, 1:]
    return falls.any(1), m0 + falls.argmax(1)


def _round_corner(f, xo):
    if xo is None:
        return float(round(f))
    return float(_xw._snap(f, xo)[0])


def _neighbours(opt, cls_bounds, xo):
    """A filter's corners one refine step either side, snapped, within the joint's bounds (the filter itself included)."""
    lo, hi = cls_bounds
    out = set()
    for k in (-1.0, 0.0, 1.0):
        c = _round_corner(opt[2] * 2.0 ** (k * CORNER_REFINE_OCT), xo)
        if lo <= c <= hi:
            out.add((opt[0], opt[1], c))
    return sorted(out)


def _offsets_of(single_upper, free, rule_ms, step_ms):
    """The front's L-R offsets the scan walks, each on the DSP's delay step, once each: the source of the ceiling's count too."""
    if single_upper:
        return [0.0]
    if not free:
        return [_snap_ms(rule_ms, step_ms)]
    n_off = int(round(FREE_OFFSET_SPAN_MS / FREE_OFFSET_STEP_MS))
    return list(dict.fromkeys(_snap_ms(rule_ms + k * FREE_OFFSET_STEP_MS, step_ms) for k in range(-n_off, n_off + 1)))


def scan_bass(inp):
    """The bass joint: all pairs on the reference point, vectorised over delay, then the best per crossing band on every point.

    Returns `{"rows": [...], "bands": {label: [...]}, "rejected": {...}, "grid": {...}}`: `rows` best first over all bands."""
    f = np.asarray(inp.freqs, float)
    step = float(np.log2(f[1] / f[0]))
    cls = inp.joint
    n = int(math.floor(inp.max_ms / DELAY_COARSE_STEP_MS))
    delays = np.arange(-n, n + 1) * DELAY_COARSE_STEP_MS
    rot_deg = (360.0 * f[None, :] * delays[:, None] * 1e-3).astype(np.float32)
    gains = np.asarray(inp.gains_db, float)
    single_upper = inp.upper_r is None
    offsets = _offsets_of(single_upper, inp.free_lr_offset, inp.lr_rule_ms, inp.delay_step_ms)
    lp_bank, hp_bank = _Bank(f, "lp"), _Bank(f, "hp")
    sub_db0 = _db(inp.ref_lower).astype(np.float32)
    sub_ph0 = np.degrees(np.angle(inp.ref_lower)).astype(np.float32)
    # the leak bands, in grid steps above each row's own crossing (the grid is log-spaced, so one offset fits every crossing)
    n_near = int(round(math.log2(LEAK_NEAR_RATIO) / step))
    n_far = (int(round(math.log2(LEAK_FAR_RATIOS[0]) / step)), int(round(math.log2(LEAK_FAR_RATIOS[1]) / step)))
    last = len(f) - 1
    cw = np.flatnonzero((f >= cls.crossing_window[0]) & (f <= cls.crossing_window[1]))
    cw_mask, m0 = np.zeros(len(f), bool), int(cw[0])
    cw_mask[cw] = True
    edges = _band_edges(cls)
    rejected = {"leak": 0, "no_crossing": 0, "sub_one_point": 0, "phase": 0, "gain": 0, "delay": 0, "stage": 0, "dip": 0,
                "past_shortlist": 0}
    label_at = {}
    bands, peak = {}, [0]                     # {label: {"kept": sorted rows, "wait": rows not yet looked at}}, the peak held

    def scan(pairs, oi):
        """Rows for the filter pairs at the reference point, one L-R offset, offered to the buffers as they come."""
        offset = offsets[oi]
        front = _front_sum(inp.ref_l, inp.ref_r, f, offset)
        front_db, front_ph = _db(front).astype(np.float32), np.degrees(np.angle(front)).astype(np.float32)
        for lp, hp in pairs:
            _, lp_db, lp_ph = lp_bank.get(lp)
            _, hp_db, hp_ph = hp_bank.get(hp)
            ls, lw = sub_db0 + lp_db, front_db + hp_db
            gap = ls - lw
            has, cross = _crossings(gap, cw_mask, m0, gains)
            g_cross = has.copy()
            rejected["no_crossing"] += int((~has).sum())
            if not g_cross.any():
                continue
            # the leak, relative to each gain's own crossing (`LEAK_*`): the same two levels whether the test is on or off
            near_db, far_db = np.zeros(len(gains)), np.zeros(len(gains))
            for c in np.unique(cross[g_cross]):
                a, b = int(c) + n_far[0], int(c) + n_far[1]
                near = float(gap[min(int(c) + n_near, last)])
                far = float(gap[min(a, last):min(b, last) + 1].max())
                at_c = cross == c
                near_db[at_c], far_db[at_c] = near + gains[at_c], far + gains[at_c]
            if inp.leak_on:
                leak_ok = (near_db <= LEAK_NEAR_DB) & (far_db <= LEAK_FAR_DB)
                rejected["leak"] += int((g_cross & ~leak_ok).sum())
                g_cross = g_cross & leak_ok
                if not g_cross.any():
                    continue
            if inp.sub_one_point:
                high = f[cross] >= SUB_ONE_POINT_MAX_HZ
                rejected["sub_one_point"] += int((g_cross & high).sum())
                g_cross = g_cross & ~high
                if not g_cross.any():
                    continue
            base = (sub_ph0 + lp_ph) - (front_ph + hp_ph)
            x = base[None, :] + rot_deg
            a = np.abs(((x + 180.0) % 360.0) - 180.0)
            for pol, ok in (("NORM", a <= PHASE_WINDOW_DEG), ("INV", a >= 180.0 - PHASE_WINDOW_DEG)):
                for c in np.unique(cross[g_cross]):
                    w = _widths(ok, int(c), step)
                    k = _plateau_centre(w)
                    at_c = np.flatnonzero(g_cross & (cross == c))
                    if w[k] <= 0:
                        rejected["phase"] += int(at_c.size)
                        continue
                    for gi in at_c:
                        offer((float(w[k]), lp, hp, float(gains[gi]), pol, float(delays[k]), int(c), oi,
                               float(near_db[gi]), float(far_db[gi])))

    def split_of(row):
        """The row's delays as the DSP takes them, each real L-R pair on its offset, or None past the ceiling."""
        return _delay_split(row[5], offsets[row[7]], inp.max_ms, single_upper, lower_offset_ms=inp.lower_offset_ms,
                            step_ms=inp.delay_step_ms)

    def accept(row):
        """The hard limits and the dip, walked only for rows the sort reaches: (split gain, split delay) or None. Each row is
        looked at once (`compact` takes it out of the buffer), so each drop is counted once."""
        width, lp, hp, g, pol, d, c, oi, _near, _far = row
        gain = _gain_split(g, inp.gain_range, inp.gain_step_db)
        if gain is None:
            rejected["gain"] += 1
            return None
        tas = split_of(row)
        if tas is None:
            rejected["delay"] += 1
            return None
        if not inp.free_lr_offset and not single_upper \
                and check_stage(rule_ms=inp.lr_rule_ms, lr_delay_ms=tas["upper_left"] - tas["upper_right"]):
            rejected["stage"] += 1
            return None
        if inp.lower_rule_ms is not None \
                and check_stage(rule_ms=inp.lower_rule_ms, lr_delay_ms=tas["sub_left"] - tas["sub_right"]):
            rejected["stage"] += 1
            return None
        if inp.dip_on and inp.target_db is not None:
            s = (-1.0 if pol == "INV" else 1.0) * 10.0 ** (g / 20.0) * inp.ref_lower * lp_bank.get(lp)[0]
            w = _front_sum(inp.ref_l, inp.ref_r, f, offsets[oi]) * hp_bank.get(hp)[0] \
                * np.exp(-2j * np.pi * f * d * 1e-3)
            if _dip_db(f, s, w, inp.target_db, cls) < DIP_LIMIT_DB:
                rejected["dip"] += 1
                return None
        return gain, tas

    def offer(row):
        """A row from the scan goes to its band's buffer, or out at once when it cannot reach the shortlist."""
        c = row[6]
        if c not in label_at:
            label_at[c] = _band_label(edges, float(f[c]))
        label = label_at[c]
        if label is None:
            rejected["no_crossing"] += 1
            return
        stats["rows"] += 1
        band = bands.setdefault(label, {"kept": [], "wait": []})
        if len(band["kept"]) >= SHORTLIST_PER_BAND and row[0] <= band["kept"][-1][0]:
            rejected["past_shortlist"] += 1
            return
        band["wait"].append(row)
        peak[0] = max(peak[0], sum(len(b["kept"]) + len(b["wait"]) for b in bands.values()))
        if len(band["wait"]) >= ROW_BUFFER_PER_BAND:
            compact(band)

    def compact(band):
        """Settle a band's waiting rows, widest first: accept keeps the top of the shortlist, the rest are out, counted. A stable
        sort over the arrival order, so a tie goes to the row that came first, as a full sort of all rows would."""
        band["wait"].sort(key=lambda r: -r[0])
        kept = band["kept"]
        for i, row in enumerate(band["wait"]):
            if len(kept) >= SHORTLIST_PER_BAND and row[0] <= kept[-1][0]:
                rejected["past_shortlist"] += len(band["wait"]) - i
                break
            if accept(row) is None:
                continue
            kept.append(row)
            kept.sort(key=lambda r: -r[0])
            if len(kept) > SHORTLIST_PER_BAND:
                kept.pop()
                rejected["past_shortlist"] += 1
        band["wait"] = []

    def settle():
        for band in bands.values():
            compact(band)
        return {label: list(band["kept"]) for label, band in bands.items() if band["kept"]}

    stats = {"rows": 0}
    n_pairs = len(inp.lp_options) * len(inp.hp_options)
    for oi in range(len(offsets)):           # a generator per offset: the pairs of a large grid are not held in memory
        scan(((tuple(lp), tuple(hp)) for lp in inp.lp_options for hp in inp.hp_options), oi)
    short = settle()

    # +-1/12 oct around the shortlist: the coarse grid found the place, the neighbours refine the corners.
    coarse_lp, coarse_hp = {tuple(o) for o in inp.lp_options}, {tuple(o) for o in inp.hp_options}
    fresh = set()
    for members in short.values():
        for row in members:
            for lp in _neighbours(row[1], cls.lp_bounds, inp.xo):
                for hp in _neighbours(row[2], cls.hp_bounds, inp.xo):
                    if hp[2] >= inp.hp_floor_hz and not (tuple(lp) in coarse_lp and tuple(hp) in coarse_hp):
                        fresh.add(((tuple(lp), tuple(hp)), row[7]))
    for oi in range(len(offsets)):
        scan([p for p, o in fresh if o == oi], oi)
    short = settle()

    rows = []
    for label, members in short.items():
        band_rows = [_score_points(inp, row, label, offsets, lp_bank, hp_bank, step, cls, m0, cw_mask, single_upper, rejected)
                     for row in members]
        rows += [r for r in band_rows if r is not None]
    rows.sort(key=_row_key, reverse=True)
    bands = {}
    for r in rows:
        bands.setdefault(r["band"], []).append(r)
    return {"rows": rows, "bands": bands, "rejected": rejected,
            "grid": {"pairs": n_pairs, "lp_options": [list(o) for o in inp.lp_options],
                     "hp_options": [list(o) for o in inp.hp_options], "lr_offsets": len(offsets),
                     "gains": len(gains), "delays": len(delays), "scored_rows": stats["rows"], "peak_rows": peak[0]}}


def _row_key(r):
    """The ranking: worst point's band, median's band, the summation loss; among ties the sum nearest the target."""
    return (r["width_worst_oct"], r["width_median_oct"], -99.0 if r["loss_median_db"] is None else r["loss_median_db"],
            -99.0 if r["dip_median_db"] is None else -abs(r["dip_median_db"]))


def _public(row):
    """The row as a reader gets it: numbers rounded for reading (the ranking used the unrounded values)."""
    out = dict(row)
    for key, n in (("width_worst_oct", 2), ("width_median_oct", 2), ("loss_median_db", 2), ("dip_median_db", 2),
                   ("leak_near_db", 1), ("leak_far_db", 1), ("crossing_hz", 1)):
        out[key] = _round(out[key], n)
    return out


def _round(v, n=2):
    return None if v is None else round(float(v), n)


def _score_points(inp, row, label, offsets, lp_bank, hp_bank, step, cls, m0, cw_mask, single_upper, rejected):
    """Every point, the delay refined there: worst then median of the ±30 degree band, then the summation loss. A row that falls
    here (past a limit at its final delay, the one-point limit at another point's crossing) is counted in `rejected`."""
    f = np.asarray(inp.freqs, float)
    _coarse_w, lp, hp, g, pol, d, _c, oi, leak_near, leak_far = row
    xs, xw = lp_bank.get(lp)[0], hp_bank.get(hp)[0]
    sign = -1.0 if pol == "INV" else 1.0
    s = sign * 10.0 ** (g / 20.0) * inp.lower * xs
    w = _front_sum(inp.upper_l, inp.upper_r, f, offsets[oi]) * xw
    gap = _db(s) - _db(w)
    base = np.degrees(np.angle(s)) - np.degrees(np.angle(w))
    fine = d + np.arange(-int(round(DELAY_FINE_SPAN_MS / DELAY_FINE_STEP_MS)),
                         int(round(DELAY_FINE_SPAN_MS / DELAY_FINE_STEP_MS)) + 1) * DELAY_FINE_STEP_MS
    if inp.delay_step_ms:
        fine = np.unique(np.round(fine / inp.delay_step_ms) * inp.delay_step_ms)
    fine = fine[np.abs(fine) <= inp.max_ms + 1e-9]
    if fine.size == 0:
        rejected["delay"] += 1
        return None
    rot = 360.0 * f[None, :] * fine[:, None] * 1e-3
    widths = np.zeros((len(inp.points), len(fine)))
    crossings = [None] * len(inp.points)
    for p in range(len(inp.points)):
        c = _crossing(gap[p], cw_mask, m0)
        crossings[p] = c
        if c is None:
            continue
        if inp.sub_one_point and f[c] >= SUB_ONE_POINT_MAX_HZ:     # one curve for the sub holds under 100 Hz, at every point
            rejected["sub_one_point"] += 1
            return None
        a = np.abs(((base[p][None, :] + rot + 180.0) % 360.0) - 180.0)
        widths[p] = _widths(a <= PHASE_WINDOW_DEG, c, step)
    worst = widths.min(0)
    median = np.median(widths, axis=0)
    # worst first, then the median; the plateau's centre on a tie
    top = worst >= worst.max() - 1e-9
    k = int(np.flatnonzero(top)[_plateau_centre(median[top])])
    d_best = _snap_ms(float(fine[k]), inp.delay_step_ms)
    tas = _delay_split(d_best, offsets[oi], inp.max_ms, single_upper, lower_offset_ms=inp.lower_offset_ms, step_ms=inp.delay_step_ms)
    if tas is None:
        rejected["delay"] += 1
        return None
    gain = _gain_split(g, inp.gain_range, inp.gain_step_db)
    if gain is None:
        rejected["gain"] += 1
        return None
    rot_c = np.exp(-2j * np.pi * f * d_best * 1e-3)
    losses, dips, fxs = [], [], []
    for p in range(len(inp.points)):
        c = crossings[p]
        if c is None:
            continue
        fx = float(f[c])
        fxs.append(fx)
        loss = dsp_math.sum_loss(f, s[p], w[p] * rot_c, (fx / math.sqrt(2.0), fx * math.sqrt(2.0)))["avg_db"]
        if loss is not None:
            losses.append(loss)
        if inp.target_db is not None:
            dips.append(_dip_db(f, s[p], w[p] * rot_c, inp.target_db, cls))
    if not fxs:
        rejected["no_crossing"] += 1
        return None
    fs_margin = None
    if inp.fs_upper_hz:
        fs_margin = _cc.fs_margin(hp[2], inp.fs_upper_hz, order=max(hp[1] // 6, 1))["verdict"]
    return {"lp": list(lp), "hp": list(hp), "sub_rel_db": g, "sub_gain_db": gain[0], "front_gain_db": gain[1],
            "polarity": pol, "delay_ms": round(d_best, 3), "who_delays": _who_delays(tas),
            "ta_ms": tas, "lr_offset_ms": 0.0 if single_upper else round(float(offsets[oi]), 3),
            "sub_lr_offset_ms": None if inp.lower_offset_ms is None else round(float(inp.lower_offset_ms), 3),
            "crossing_hz": float(np.median(fxs)), "width_worst_oct": float(worst[k]), "width_median_oct": float(median[k]),
            "loss_median_db": float(np.median(losses)) if losses else None,
            "dip_median_db": float(np.median(dips)) if dips else None, "leak_near_db": float(leak_near),
            "leak_far_db": float(leak_far), "fs_margin": fs_margin, "band": label, "marks": list(inp.marks)}


# ---------------------------------------------------------------- the input
def read_window(ir_info, freqs):
    """The bass reading of one kept IR: 5 ms before to 500 ms after its peak, a cosine tail, 1/6-oct vector average, on `freqs`.

    The bulk delay comes out before the average and goes back after, so the average does not smear the phase and the absolute
    time base stays (`t0_s` is sample 0's time, as `predict` keeps it)."""
    x = np.asarray(ir_info["ir"], float)
    fs = float(ir_info["sample_rate"])
    t0 = float(ir_info.get("t0_s") or 0.0) - float(ir_info.get("drift_samples") or 0.0) / fs
    f_grid = np.asarray(freqs, float)
    pk = int(np.argmax(np.abs(x)))
    a = max(0, pk - int(WINDOW_BEFORE_MS * 1e-3 * fs))
    b = min(x.size, pk + int(WINDOW_AFTER_MS * 1e-3 * fs))
    seg = x[a:b].copy()
    tail = int(WINDOW_TAIL_FRACTION * seg.size)
    if tail:
        seg[-tail:] *= 0.5 * (1.0 + np.cos(np.linspace(0.0, np.pi, tail)))
    nfft = 1 << int(math.ceil(math.log2(max(seg.size * 4, 8))))
    bins = np.fft.rfftfreq(nfft, 1.0 / fs)
    tau0 = (pk - a) / fs
    H = np.fft.rfft(seg, nfft) * np.exp(2j * np.pi * bins * tau0)
    k = 2.0 ** (SMOOTH_OCT / 2.0)
    keep = bins <= f_grid[-1] * k * 1.01
    b_cut, H_cut = bins[keep], H[keep]
    cum = np.concatenate(([0.0 + 0j], np.cumsum(H_cut)))
    lo_i = np.searchsorted(b_cut, f_grid / k, side="left")
    hi_i = np.searchsorted(b_cut, f_grid * k, side="right")
    n = np.maximum(hi_i - lo_i, 1)
    hi_i = np.minimum(lo_i + n, b_cut.size)
    avg = (cum[hi_i] - cum[lo_i]) / np.maximum(hi_i - lo_i, 1)
    return avg * np.exp(-2j * np.pi * f_grid * (tau0 + t0 + a / fs))


def load_channels(codes, freqs, *, solos=None, ver=None, api=None, record=None):
    """Every channel's curves, tripod and points, each windowed, keeping `info` (IR, timing, protection), the protective
    filter taken out once (`predict.de_embed_solos`, its refusal passed on as it stands).

    Returns `({code: {"tripod": H or None, "points": {pos: H}, "info": {key: info}}}, notes)`; `solos` is a folder of v7 files
    (`m_L.json`, `m_L-p1.json`), else REW at series `ver` (`naming.generate_name`)."""
    groups, out = {}, {code: {"tripod": None, "points": {}, "info": {}} for code in codes}
    have = None
    if solos is None:
        if api is None:
            import rew_api as api  # noqa: F811
        have = {(m or {}).get("title") for m in api.get_measurements().values()}
    for code in codes:
        for pos in (None,) + POSITIONS:
            key = pos or "tripod"
            if solos is not None:
                stem = code.replace("-", "_") + (f"-{pos}" if pos else "")
                path = os.path.join(solos, f"{stem}.json")
                if not os.path.isfile(path):
                    continue
                try:
                    _h, info = P.load_solo_v7(path, freqs, keep_ir=True)
                except (TypeError, KeyError, AttributeError, ValueError) as exc:
                    if getattr(type(exc), "is_refusal", False):
                        raise
                    raise JointSearchError(f"{path}: its protective record or its content cannot be read: {exc}") from None
            else:
                title = naming.generate_name(code, ver, "sw", position=pos)
                if title not in have:
                    continue
                _h, info = P.load_solo_rew(title, freqs, api=api, keep_ir=True)
            groups.setdefault(key, {})[code] = (read_window(info["ir"], freqs), info)
    notes = []
    for key, loaded in groups.items():
        try:
            corrected, these, refused = P.de_embed_solos(loaded, freqs, record=record, baseline=True)
        except (TypeError, KeyError, AttributeError, ValueError) as exc:
            if getattr(type(exc), "is_refusal", False):
                raise
            raise JointSearchError(f"the protective record of {key} is malformed: {exc}") from None
        for line in these:
            if refused and "REFUSED" in line:
                raise JointSearchError(line)
            if line not in notes:
                notes.append(line)
        for code, H in corrected.items():
            if key == "tripod":
                out[code]["tripod"] = H
            else:
                out[code]["points"][key] = H
            out[code]["info"][key] = loaded[code][1]
    return out, notes


def lr_rule_ms(left, right, role, *, positions):
    """The signed rule's value at the centre points: -(raw arrival L - raw arrival R), or a refusal in words."""
    band, gate = ARRIVAL_READ[role]
    values = []
    for key in positions:
        a, b = (left["info"].get(key) or {}).get("ir"), (right["info"].get(key) or {}).get("ir")
        if a is None or b is None:
            continue
        ms, info = windows.arrival_between(a["ir"], b["ir"], float(a["sample_rate"]), band=band, gate_ms=gate,
                                           t0_a=float(a["t0_s"]), t0_b=float(b["t0_s"]))
        if ms is None:
            raise JointSearchError(f"the L-R arrival of the {role} cannot be read at {key}: {info.get('refused')}")
        values.append(ms)
    if not values:
        raise JointSearchError(f"the L-R arrival of the {role} needs both channels at the same point (tripod or a centre point)")
    return -float(np.mean(values))


def _level_step_db(sub_session, main, upper, freqs, band):
    """How much louder the main session is than the sub's: the front's centre points against its tripod in the sub's
    session, over the control band, averaged (`swws_xo.py:71-73`)."""
    m = (freqs >= band[0]) & (freqs <= band[1])

    def level(h):
        return 10.0 * np.log10(np.mean(np.abs(h[m]) ** 2))

    steps = []
    for code in upper.codes:
        tripod = sub_session[code]["tripod"]
        if tripod is None:
            raise JointSearchError(f"--level-step needs {code}'s tripod solo in the sub's session")
        for pos in CENTRE_POINTS:
            h = main[code]["points"].get(pos)
            if h is not None:
                steps.append(level(h) - level(tripod))
    if not steps:
        raise JointSearchError("--level-step needs the front's centre points")
    return float(np.mean(steps))


def _rule_positions(left, right, single_point):
    """Where the L-R rule is read: the centre points, or with one point only where `_ref_curve` would take the curve from."""
    if not single_point:
        return CENTRE_POINTS
    for key in ("tripod", "p5", "p1", "p9"):
        if key in left["info"] and key in right["info"]:
            return (key,)
    return ()


def _ref_curve(chan, code):
    if chan["tripod"] is not None:
        return chan["tripod"]
    for pos in ("p5", "p1", "p9"):
        if pos in chan["points"]:
            return chan["points"][pos]
    raise JointSearchError(f"{code}: neither a tripod solo nor a centre point (p1/p5/p9)")


def _build_bass_input(joint, *, curves, lower_curves, freqs, single_point, lp_options, hp_options, gains, max_ms, gain_range,
                      target_db, free_offset, hp_floor_hz, fs_upper_hz, xo, cls, marks, delay_step_ms=None, gain_step_db=None,
                      leak_on=True, dip_on=True, front_lp=None):
    upper = joint.upper
    lower = joint.lower
    if single_point:
        points = ["centre"]
    else:
        points = list(POSITIONS)
        for code in upper.codes:
            missing = [p for p in POSITIONS if p not in curves[code]["points"]]
            if missing:
                raise JointSearchError(f"{code}: the nine points are needed and {', '.join(missing)} are missing -- capture "
                                       "them, or decide for --single-point and record that decision")
    chan_u = [curves[c] for c in upper.codes]
    chan_l = [lower_curves[c] for c in lower.codes]
    sub_one_point = single_point or not any(ch["points"] for ch in chan_l)
    if single_point:
        low_stack = [np.array([_ref_curve(ch, c)]) for ch, c in zip(chan_l, lower.codes)]
        up_stack = [np.array([_ref_curve(ch, c)]) for ch, c in zip(chan_u, upper.codes)]
    else:
        if sub_one_point:
            low_stack = [np.tile(_ref_curve(ch, c), (len(points), 1)) for ch, c in zip(chan_l, lower.codes)]
        else:
            for ch, c in zip(chan_l, lower.codes):
                missing = [p for p in POSITIONS if p not in ch["points"]]
                if missing:
                    raise JointSearchError(f"{c}: {', '.join(missing)} of its points are missing; measure the sub at all nine "
                                           "points or at one")
            low_stack = [np.array([ch["points"][p] for p in points]) for ch in chan_l]
        up_stack = [np.array([ch["points"][p] for p in points]) for ch in chan_u]
    # a lower branch that is a real pair is summed here, once, its own L-R offset held; a sub measured once reads the rule
    # where the curve came from
    rule_ms, notes, lower_rule, lower_offset = 0.0, [], None, None
    if not lower.single:
        lower_rule = lr_rule_ms(chan_l[0], chan_l[1], lower.role, positions=_rule_positions(chan_l[0], chan_l[1], sub_one_point))
        lower_offset = _snap_ms(lower_rule, delay_step_ms)
        sum_low = _front_sum(low_stack[0], low_stack[1], freqs, lower_offset)
        ref_low = _front_sum(_ref_curve(chan_l[0], lower.codes[0]), _ref_curve(chan_l[1], lower.codes[1]), freqs, lower_offset)
    else:
        sum_low = low_stack[0]
        ref_low = _ref_curve(chan_l[0], lower.codes[0])
    if not upper.single:
        try:
            rule_ms = lr_rule_ms(chan_u[0], chan_u[1], upper.role, positions=_rule_positions(chan_u[0], chan_u[1], single_point))
        except JointSearchError as exc:
            if not free_offset:
                raise
            notes.append(f"the free L-R offset is searched around 0, not the raw offset: {exc}")
    if sub_one_point:
        notes.append("the sub is one curve for every point: no drift is applied between the points")
    # the woofer's low-pass, in the model when `--front-lp` names it: it adds its phase to the front's arrival at the crossing
    lp_h = None if front_lp is None else dsp_math.xo_response(freqs, front_lp[2], front_lp[1], "lp", front_lp[0])
    with_lp = (lambda h: h) if lp_h is None else (lambda h: h * lp_h)
    return BassInput(freqs=freqs, points=points, lower=sum_low, upper_l=with_lp(up_stack[0]),
                     upper_r=None if upper.single else with_lp(up_stack[1]), ref_lower=ref_low,
                     ref_l=with_lp(_ref_curve(chan_u[0], upper.codes[0])),
                     ref_r=None if upper.single else with_lp(_ref_curve(chan_u[1], upper.codes[1])),
                     lp_options=lp_options, hp_options=hp_options, gains_db=gains, max_ms=max_ms, gain_range=gain_range,
                     target_db=target_db, lr_rule_ms=rule_ms, free_lr_offset=free_offset, sub_one_point=sub_one_point,
                     hp_floor_hz=hp_floor_hz, fs_upper_hz=fs_upper_hz, marks=marks, joint=cls, xo=xo, notes=notes,
                     lower_offset_ms=lower_offset, lower_rule_ms=lower_rule, delay_step_ms=delay_step_ms, gain_step_db=gain_step_db,
                     leak_on=leak_on, dip_on=dip_on)


# ---------------------------------------------------------------- the report
def _filter_name(opt):
    return f"{opt[0]}{opt[1]}@{opt[2]:g}"


#: Each drop's words in the report; the key is `scan_bass`'s `rejected`.
_REJECT_WORDS = {"leak": "leak limit", "no_crossing": "no crossing in the window", "sub_one_point": "the sub's one-point limit",
                 "phase": "no in-phase band through the crossing", "gain": "gain range or step", "delay": "past the delay ceiling",
                 "stage": "the L-R rule off the delay step", "dip": "dip under the target", "past_shortlist": "not looked at, past the shortlist"}


def _reasons(rejected):
    """The reasons rows fell, in words and counted."""
    return ", ".join(f"{_REJECT_WORDS.get(k, k)} {v}" for k, v in rejected.items() if v)


def render(doc):
    joint, cond = doc["joint"], doc["conditions"]
    head = f"Joint {joint} ({doc['joint_class']}): {doc['grid']['pairs']} filter pairs. Stack: {' / '.join(doc['joints_in_stack'])}."
    if cond["upper_single"]:
        head += " The upper side is one channel: no L-R offset."
    elif cond["lr_offset_held"]:
        head += f" L-R offset held at {cond['lr_offset_ms']:+.2f} ms (delay L - delay R)."
    else:
        head += f" L-R offset free, searched +-{FREE_OFFSET_SPAN_MS:g} ms around {cond['lr_offset_ms']:+.2f} ms: each row shows its own."
    if cond["lower_lr_offset_ms"] is not None:
        head += f" Sub L-R offset held at {cond['lower_lr_offset_ms']:+.2f} ms (delay L - delay R)."
    if cond.get("front_lp"):
        head += f" The front's low-pass ({_filter_name(cond['front_lp'])}) is in the model."
    lines = [head]
    free_shown = not cond["lr_offset_held"] and not cond["upper_single"]
    codes = list(doc["channels"]["lower"]) + list(doc["channels"]["upper"])
    delay_heads = " ".join(f"{c:>8}" for c in codes)
    for label, rows in doc["bands"].items():
        lines.append(f"\nCrossing {label}:")
        lines.append(f"  {'LP':>12} {'HP':>12} {'sub dB':>7} {'front dB':>9} {'sub pol':>7} "
                     + (f"{'L-R ms':>7} " if free_shown else "")
                     + f"{delay_heads} {'delay on':>9} {'worst oct':>9} "
                     f"{'med oct':>7} {'loss dB':>7} {'dip dB':>6} {'leak 1.5x':>9} {'Fs':>7}")
        for r in rows:
            lines.append(f"  {_filter_name(r['lp']):>12} {_filter_name(r['hp']):>12} {r['sub_gain_db']:>+7.1f} {r['front_gain_db']:>+9.1f} "
                         f"{r['polarity']:>7} "
                         + (f"{r['lr_offset_ms']:>+7.2f} " if free_shown else "")
                         + " ".join(f"{r['delays_ms'][c]:>8.3f}" for c in codes)
                         + f" {r['who_delays']:>9} {r['width_worst_oct']:>9.2f} {r['width_median_oct']:>7.2f} "
                         f"{r['loss_median_db'] if r['loss_median_db'] is not None else float('nan'):>7.2f} "
                         f"{r['dip_median_db'] if r['dip_median_db'] is not None else float('nan'):>6.1f} "
                         f"{r['leak_near_db']:>9.1f} {r['fs_margin'] or '':>7}"
                         + (f"  [{', '.join(r['marks'])}]" if r["marks"] else ""))
    lines.append("")
    if doc["notes"]:
        lines.append("Notes:")
        lines.extend(f"  - {n}" for n in doc["notes"])
        lines.append("")
    if doc["rows"]:
        lines.append("Rejected: " + (_reasons(doc["rejected"]) or "nothing"))
    else:
        lines.append("No variant came through the limits. Reasons, counted: " + (_reasons(doc["rejected"]) or "none recorded"))
    lines.append("\nThis describes; the choice is the tuner's.")
    return "\n".join(lines)


def _bounds(spec, label):
    try:
        lo, hi = (float(x) for x in spec.split(":"))
        if not 0 < lo < hi:
            raise ValueError
    except ValueError:
        raise JointSearchError(f"{label} takes LO:HI in Hz, got {spec!r}") from None
    return lo, hi


def _cli(argv=None):
    """`_main`'s work; its refusals are `_main`'s to say."""
    import argparse
    ap = argparse.ArgumentParser(description="the joint-by-joint search: the bass joint, described, not chosen")
    ap.add_argument("--project", required=True, metavar="DIR")
    ap.add_argument("--house", required=True, metavar="FILE", help="the target curve (REW text)")
    ap.add_argument("--solos", metavar="DIR", help="v7 impulse files, `m_L.json` and `m_L-p1.json`")
    ap.add_argument("--rew", action="store_true", help="read live REW: `--ver N` is the series")
    ap.add_argument("--ver", help="series number for --rew")
    ap.add_argument("--sub-solos", metavar="DIR", help="the sub from another capture session (needs --level-step)")
    ap.add_argument("--sub-ver", help="the sub's series in REW when it differs (needs --level-step)")
    ap.add_argument("--level-step", metavar="LO:HI", help="the control band two capture sessions are levelled over")
    ap.add_argument("--single-point", action="store_true", help="run on the centre point; needs the person's recorded decision")
    ap.add_argument("--joint", default="bass", help="which joint (this build: bass)")
    ap.add_argument("--lp-bounds", metavar="LO:HI", help="the lower driver's LP corners, Hz")
    ap.add_argument("--hp-bounds", metavar="LO:HI", help="the upper driver's HP corners, Hz")
    ap.add_argument("--gain", metavar="LO:HI:STEP", help="sub level relative to the front, dB")
    ap.add_argument("--no-lr-offset", action="store_true", help="stage condition off: search the front's L-R offset freely")
    ap.add_argument("--no-leak", action="store_true", help="condition off: do not reject the sub's leak above the crossing")
    ap.add_argument("--no-dip", action="store_true", help="condition off: do not reject a dip under the target")
    ap.add_argument("--front-lp", nargs=3, metavar=("FAMILY", "ORDER", "HZ"),
                    help="the woofer's low-pass, in the model of the bass joint (its phase moves the delay)")
    ap.add_argument("--allow-large-grid", action="store_true",
                    help=f"over {GRID_CEILING_PAIRS} filter pairs x L-R offsets, run anyway: time grows with the combinations, "
                         "memory with the filter options (about 24 kB each), the row buffer stays bounded")
    ap.add_argument("--top", type=int, default=TOP_DEFAULT, help="rows per crossing band")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out", metavar="DIR", help="write the table and the JSON here")
    args = ap.parse_args(argv)
    if bool(args.solos) == bool(args.rew):
        raise JointSearchError("give exactly one of --solos DIR or --rew --ver N")
    if args.rew and not args.ver:
        raise JointSearchError("--rew needs --ver N")
    if args.sub_ver and args.solos:
        raise JointSearchError("--sub-ver names the sub's REW series; with --solos it has nothing to read (--sub-solos DIR instead)")
    if args.rew:
        for label, ver in (("--ver", args.ver), ("--sub-ver", args.sub_ver)):
            try:
                if ver is not None:
                    naming.generate_name("x", ver, "sw")
            except ValueError as exc:
                raise JointSearchError(f"{label} {ver!r}: {exc}") from None
    project_dir = args.project
    space = space_of(project_dir)
    if space.rate_note:
        print(f"  ⚠ {space.rate_note}", file=sys.stderr)
    channels = _xw._channels(project_dir)
    stack = stack_names(channels)
    if args.joint != "bass":
        raise JointSearchError(f"joint {args.joint!r}: this build searches the bass joint only (--joint bass)")
    bass = joints_of(channels, cls="bass")
    if not bass:
        raise JointSearchError(f"no bass joint in this stack ({' / '.join(stack) or 'no joints'}): the channels "
                               "hold no sub with a role above it")
    joint = bass[0]
    upper = joint.upper
    # Fs: the floor of the upper driver's high-pass, and what its margin is judged against.
    fs_values = []
    for code in upper.codes:
        fs, why = _xw._fs_of(channels[code])
        if fs is None:
            raise JointSearchError(f"{code}: {why}")
        fs_values.append(fs)
    fs_upper = max(fs_values)
    floor = HP_FS_FLOOR.get(upper.role, 0.0) * fs_upper
    cls = JOINT_CLASSES[joint.cls]
    lp_bounds = _bounds(args.lp_bounds, "--lp-bounds") if args.lp_bounds else cls.lp_bounds
    hp_bounds = _bounds(args.hp_bounds, "--hp-bounds") if args.hp_bounds else cls.hp_bounds
    cls = JointClass(cls.name, lp_bounds, hp_bounds, cls.crossing_window, cls.grid_hz, cls.dip_band, cls.dip_fit_band)
    lp_corners = corner_grid(lp_bounds, space.xo)
    hp_corners = corner_grid(hp_bounds, space.xo)
    lp_options = filter_options(space.families, lp_corners)
    hp_options = filter_options(space.families, hp_corners, floor_hz=floor)
    if not lp_options or not hp_options:
        raise JointSearchError(f"no filter pair left: LP corners {lp_bounds} Hz, HP corners {hp_bounds} Hz above the floor {floor:g} Hz")
    if args.gain:
        try:
            g_lo, g_hi, g_step = (float(x) for x in args.gain.split(":"))
            if g_step <= 0 or g_hi < g_lo:
                raise ValueError
        except ValueError:
            raise JointSearchError(f"--gain takes LO:HI:STEP in dB, got {args.gain!r}") from None
    else:
        g_lo, g_hi, g_step = GAIN_GRID_DB
    gains = [float(g) for g in np.arange(g_lo, g_hi + g_step / 2.0, g_step)
             if _gain_split(float(g), space.gain_range, space.gain_step_db) is not None]
    if not gains:
        raise JointSearchError(f"no sub level in {g_lo:g}..{g_hi:g} dB fits the channel gain range {space.gain_range}"
                               + (f" and its step {space.gain_step_db:g} dB" if space.gain_step_db else ""))
    free = args.no_lr_offset
    n_off = len(_offsets_of(upper.single, free, 0.0, space.delay_step_ms))
    pairs = len(lp_options) * len(hp_options)
    combos = pairs * n_off
    print(f"grid: {len(lp_corners)} LP corners x {len(space.families)} families x {len(hp_corners)} HP corners x "
          f"{len(space.families)} families = {pairs} filter pairs x {n_off} L-R offsets (ceiling {GRID_CEILING_PAIRS}); "
          f"x {len(gains)} sub levels x 2 polarities x {2 * int(math.floor(space.delay_max_ms / DELAY_COARSE_STEP_MS)) + 1} "
          f"delays per pair on the reference point", file=sys.stderr)
    if combos > GRID_CEILING_PAIRS and not args.allow_large_grid:
        raise JointSearchError(f"{pairs} filter pairs x {n_off} L-R offsets = {combos} combinations is over the ceiling "
                               f"{GRID_CEILING_PAIRS}: narrow --lp-bounds / --hp-bounds or pass --allow-large-grid")
    front_lp = _front_lp_spec(args.front_lp, space) if args.front_lp else None
    # the capture
    state_dir = os.path.join(_HERE, "state")
    if state_dir not in sys.path:
        sys.path.insert(0, state_dir)
    import process as _process
    if args.single_point and not _single_point_decided(_process, project_dir):
        raise JointSearchError("--single-point needs the person's recorded decision: the session says the limits, the person "
                               f"decides, and it is recorded in these words: `process.py {project_dir} decision "
                               f"\"{SINGLE_POINT_DECISION}\" \"<the person's words>\"`")
    freqs = P.grid(cls.grid_hz[0], cls.grid_hz[1], GRID_PPO)
    if args.level_step:
        band = _bounds(args.level_step, "--level-step")
        if band[0] < freqs[0] or band[1] > freqs[-1] or np.count_nonzero((freqs >= band[0]) & (freqs <= band[1])) < 2:
            raise JointSearchError(f"--level-step {args.level_step} is outside the search grid {freqs[0]:.0f}-{freqs[-1]:.0f} Hz: "
                                   "the control band is levelled over the points it can read")
    two_sessions = (args.sub_solos and args.sub_solos != args.solos) or (args.sub_ver and args.sub_ver != args.ver)
    if two_sessions and not args.level_step:
        raise JointSearchError("the sub comes from another capture session: its level would read as the driver's imbalance; "
                               "--level-step LO:HI names the control band the sessions are levelled over")
    record = None
    if args.rew:
        try:
            record = _process.Process(os.path.join(project_dir, "process")).protective_record_for(args.ver)
        except _process.ProcessError as exc:
            raise JointSearchError(f"the capture record of series {args.ver}: {exc}") from None
    upper_codes, lower_codes = list(upper.codes), list(joint.lower.codes)
    sources = {"solos": args.solos, "ver": args.ver, "api": None, "record": record}
    main, notes = load_channels(upper_codes + ([] if two_sessions else lower_codes), freqs, **sources)
    lower_curves = main
    if two_sessions:
        sub_record = None
        if args.rew and args.sub_ver:
            try:
                sub_record = _process.Process(os.path.join(project_dir, "process")).protective_record_for(args.sub_ver)
            except _process.ProcessError as exc:
                raise JointSearchError(f"the capture record of series {args.sub_ver}: {exc}") from None
        sub_side, more = load_channels(upper_codes + lower_codes, freqs, solos=args.sub_solos or args.solos,
                                       ver=args.sub_ver or args.ver, api=None, record=sub_record)
        notes += [n for n in more if n not in notes]
        step = _level_step_db(sub_side, main, upper, freqs, _bounds(args.level_step, "--level-step"))
        factor = 10.0 ** (step / 20.0)
        lower_curves = {c: {"tripod": None if sub_side[c]["tripod"] is None else sub_side[c]["tripod"] * factor,
                            "points": {p: h * factor for p, h in sub_side[c]["points"].items()},
                            "info": sub_side[c]["info"]} for c in lower_codes}
        notes.append(f"the sub's session levelled by {step:+.1f} dB over {args.level_step} Hz")
    for code in upper_codes + lower_codes:
        have = lower_curves[code] if code in lower_codes else main[code]
        if have["tripod"] is None and not have["points"]:
            raise JointSearchError(f"{code}: no solo found")
    if not os.path.isfile(args.house):
        raise JointSearchError(f"{args.house}: the target curve file is not there")
    try:
        house = target_bands.HouseCurve.from_file(args.house)
    except (OSError, ValueError) as exc:
        raise JointSearchError(f"{args.house}: the target curve cannot be read: {exc}") from None
    if not house.f:
        raise JointSearchError(f"{args.house}: no parseable line (frequency and level) in the target curve file")
    target = np.array([house.at(float(x)) for x in freqs])
    if not np.isfinite(target).all():
        raise JointSearchError(f"{args.house}: the target curve holds a number that is not finite")
    marks = ("single-point",) if args.single_point else ()
    inp = _build_bass_input(joint, curves=main, lower_curves=lower_curves, freqs=freqs, single_point=args.single_point,
                            lp_options=lp_options, hp_options=hp_options, gains=tuple(gains), max_ms=space.delay_max_ms,
                            gain_range=space.gain_range, target_db=target, free_offset=free, hp_floor_hz=floor,
                            fs_upper_hz=fs_upper, xo=space.xo, cls=cls, marks=marks, delay_step_ms=space.delay_step_ms,
                            gain_step_db=space.gain_step_db, leak_on=not args.no_leak, dip_on=not args.no_dip, front_lp=front_lp)
    if space.dropped:
        notes.append(f"the profile also offers {', '.join(space.dropped)}: the model does not build those exactly, so they were left "
                     "out of the search")
    if len(stack) > 1 and front_lp is None:
        notes.append("the woofer's low-pass is not in this model yet (the joint above it has no result): the delay will shift once the "
                     "woofer gets it, and it is re-scored by the next joint (--front-lp FAMILY ORDER HZ to model it now)")
    res = scan_bass(inp)
    top = max(1, int(args.top))

    def published(row):
        pub = _public(row)
        pub["delays_ms"] = _channel_delays(pub["ta_ms"], joint.lower, upper)
        return pub
    bands = {k: [published(r) for r in v[:top]] for k, v in res["bands"].items()}
    grid = dict(res["grid"], ceiling=GRID_CEILING_PAIRS)
    doc = {"joint": joint.name, "joint_class": joint.cls, "joints_in_stack": stack,
           "channels": {"lower": lower_codes, "upper": upper_codes},
           "grid": grid, "rows": [published(r) for r in res["rows"]], "bands": bands, "rejected": res["rejected"],
           "dropped_options": list(space.dropped),
           "conditions": {"lr_offset_ms": 0.0 if upper.single else round(inp.lr_rule_ms, 3),
                          "lr_offset_tolerance_ms": LR_OFFSET_TOLERANCE_MS,
                          "lr_offset_held": (not free) and (not upper.single),
                          "lr_offset_free": bool(free) and not upper.single,
                          "upper_single": upper.single,
                          "lower_lr_offset_ms": None if inp.lower_offset_ms is None else round(inp.lower_rule_ms, 3),
                          "front_lp": list(front_lp) if front_lp else None,
                          "sub_one_point": inp.sub_one_point, "hp_floor_hz": round(floor, 1)},
           "notes": notes + inp.notes, "note": "This never picks: the table describes and the choice is the tuner's."}
    if not res["rows"]:
        doc["empty"] = {"said": "no variant came through the limits", "reasons": _reasons(res["rejected"])}
    text = render(doc)
    if args.out:
        project_io.atomic_write_json(os.path.join(args.out, f"joint-{joint.name}.json"), doc, makedirs=True)
        project_io.atomic_write_text(os.path.join(args.out, f"joint-{joint.name}.txt"), text + "\n", makedirs=True)
    print(json.dumps(doc, indent=2, ensure_ascii=False) if args.json else text)
    return 0


def _channel_delays(tas, lower, upper):
    """A row's delays by the channel codes the table prints."""
    out = {}
    if lower.single:
        out[lower.codes[0]] = tas["sub"]
    else:
        out[lower.left], out[lower.right] = tas["sub_left"], tas["sub_right"]
    out[upper.left] = tas["upper_left"]
    if not upper.single:
        out[upper.right] = tas["upper_right"]
    return out


def _front_lp_spec(values, space):
    """`--front-lp FAMILY ORDER HZ` as `(family, order, Hz)`, a filter the profile offers and the model builds, or a refusal."""
    family, order, hz = values
    try:
        fam, ord_, hz_ = family.upper(), int(order), float(hz)
    except ValueError:
        raise JointSearchError(f"--front-lp takes FAMILY ORDER HZ (LR 24 280), got {' '.join(values)!r}") from None
    if (fam, ord_) not in space.families:
        raise JointSearchError(f"--front-lp {fam}{ord_}: not a filter this profile offers and the model builds "
                               f"({', '.join(f'{f}{o}' for f, o in space.families)})")
    if hz_ <= 0 or _xw._snap(hz_, space.xo)[0] != hz_:
        raise JointSearchError(f"--front-lp {hz_:g} Hz: not a corner the DSP holds (range {space.xo.get('range')}, step "
                               f"{space.xo.get('step')})")
    return fam, ord_, hz_


def _single_point_decided(process_mod, project_dir):
    """Has the person decided to run on one point? A `user_decision` whose question or answer says both that the nine points
    were skipped and that the joints run on one point (`SINGLE_POINT_*`), the answer not a bare no to the question that carried
    them. Asked for the positions, the bare word "position": neither is that decision (`process._positions_asked` is another gate)."""
    try:
        events = process_mod.Process(os.path.join(project_dir, "process"))._events(kinds=(process_mod.EV_USER_DECISION,))
    except process_mod.ProcessError as exc:
        raise JointSearchError(f"the project's decisions cannot be read: {exc}") from None
    for event in events:
        question = " ".join(str(event.get("question", "")).lower().split())
        answer = " ".join(str(event.get("answer", "")).lower().split())
        said = f"{question} {answer}"
        if SINGLE_POINT_SKIP_WORDS not in said or SINGLE_POINT_ONE_WORDS not in said:
            continue
        if SINGLE_POINT_SKIP_WORDS not in answer and (answer.split() or [""])[0].rstrip(".,!") in _NO_WORDS:
            continue
        return True
    return False


def _main(argv=None):
    """The command line. Every refusal is one line, `refusing: <why>`, exit 3: this tool's, predict's, REW's own (down, a title
    held twice, an answer it cannot read: `rew_state` on the class) and an unreadable profile's."""
    try:
        return _cli(argv)
    except Exception as exc:  # noqa: BLE001 -- matched by its attribute; anything else still raises
        if getattr(type(exc), "rew_state", None) is not None:
            print(f"refusing: REW: {_rew_words(exc)}", file=sys.stderr)
            return 3
        if not (getattr(type(exc), "is_refusal", False) or getattr(type(exc), "is_unreadable", False)):
            raise
        print(f"refusing: {exc}", file=sys.stderr)
        return 3


def _rew_words(exc):
    """A `rew_api` exception in its own words (a `KeyError` subclass's `str` is a quoted repr)."""
    return exc.args[0] if exc.args else str(exc)


# ---------------------------------------------------------------- selftests
def _plant(lp, hp, *, gain_db=2.0, pol=-1, delay_ms=2.4, n_points=3, offset_ms=0.0, single_upper=False):
    """Curves whose best variant is known by construction: flat drivers whose phase only `lp` and `hp` with these settings
    cancel. Sub after (pol, gain, lp) and the front after (hp, delay) come out as |lp| and |hp|, in phase everywhere."""
    f = P.grid(20.0, 400.0, GRID_PPO)
    xs = dsp_math.xo_response(f, lp[2], lp[1], "lp", lp[0])
    xw = dsp_math.xo_response(f, hp[2], hp[1], "hp", hp[0])
    sub = pol * 10.0 ** (-gain_db / 20.0) * np.exp(-1j * np.angle(xs))
    front = np.exp(-1j * np.angle(xw)) * np.exp(2j * np.pi * f * delay_ms * 1e-3)
    n = len(f)
    lower = np.tile(sub, (n_points, 1))
    if single_upper:
        up_l, up_r = np.tile(front, (n_points, 1)), None
    else:
        left = 0.5 * front * np.exp(2j * np.pi * f * offset_ms * 1e-3)
        right = 0.5 * front
        up_l, up_r = np.tile(left, (n_points, 1)), np.tile(right, (n_points, 1))
    target = 20.0 * np.log10(np.abs(xs) + np.abs(xw) + 1e-12)
    return f, lower, up_l, up_r, target


def _options(fams, corners):
    return [(fam, order, float(c)) for fam, order in fams for c in corners]


_PLANT_FAMS = [("LR", 24), ("LR", 36), ("BW", 24), ("BE", 24)]
_PLANT_LP = ("LR", 36, 56.0)
_PLANT_HP = ("LR", 36, 90.0)


def _planted_input(*, lp=_PLANT_LP, hp=_PLANT_HP, fams=None, lp_corners=(40, 56, 80, 113), hp_corners=(50, 71, 90, 125),
                   **kw):
    lr_rule = kw.pop("lr_rule_ms", 0.0)
    free = kw.pop("free_lr_offset", False)
    delay_ms = kw.pop("delay_ms", 2.4)
    max_ms = kw.pop("max_ms", 8.0)
    leak_on = kw.pop("leak_on", True)
    dip_on = kw.pop("dip_on", True)
    sub_one = kw.pop("sub_one_point", False)
    f, lower, up_l, up_r, target = _plant(lp, hp, delay_ms=delay_ms, **kw)
    return BassInput(freqs=f, points=[f"p{i + 1}" for i in range(lower.shape[0])], lower=lower, upper_l=up_l, upper_r=up_r,
                     ref_lower=lower[0], ref_l=up_l[0], ref_r=None if up_r is None else up_r[0],
                     lp_options=_options(fams or _PLANT_FAMS, lp_corners),
                     hp_options=_options(fams or _PLANT_FAMS, hp_corners),
                     gains_db=tuple(float(g) for g in np.arange(-4.0, 8.1, 2.0)), max_ms=max_ms,
                     gain_range=(-30.0, 5.0), target_db=target, lr_rule_ms=lr_rule, free_lr_offset=free,
                     sub_one_point=sub_one, leak_on=leak_on, dip_on=dip_on)


def _is_planted(row, lp=_PLANT_LP, hp=_PLANT_HP):
    return (row["lp"] == list(lp) and row["hp"] == list(hp))


def _check_planted_delay_polarity_corners():
    """A planted delay, polarity and corner pair are found, on either side of the delay, by a margin: flat drivers with phase
    only the planted pair cancels. A front sub (arriving early) and a rear one are the same search: only which side takes the
    delay differs."""
    for delay, who in ((2.4, "front"), (-3.0, "sub")):
        res = scan_bass(_planted_input(delay_ms=delay))
        rows = res["rows"]
        assert rows, f"delay {delay}: no rows came back"
        best = rows[0]
        assert _is_planted(best), (delay, best["lp"], best["hp"])
        assert best["polarity"] == "INV", best["polarity"]
        assert abs(best["delay_ms"] - delay) <= 0.1, (best["delay_ms"], delay)
        assert best["who_delays"] == who, (best["who_delays"], who)
        assert abs(best["sub_rel_db"] - 2.0) < 1e-9, best["sub_rel_db"]
        # Flat drivers tie the band: every pair whose phase tracks the planted one's within the window scores 4.32 oct (a named
        # equivalence set, the rows above the sum loss line). The summation loss is what ranks the planted pair first.
        others = [r for r in rows if not _is_planted(r) and not _is_near(r)]
        assert others, "the grid has only the planted pair"
        assert best["loss_median_db"] - others[0]["loss_median_db"] >= 1e-3, (best["loss_median_db"], others[0]["loss_median_db"])


def _is_near(row, lp=_PLANT_LP, hp=_PLANT_HP):
    """Within one refine step (1/12 oct) of the planted pair, in the same families: indistinguishable on flat drivers."""
    return (row["lp"][:2] == list(lp[:2]) and row["hp"][:2] == list(hp[:2])
            and abs(math.log2(row["lp"][2] / lp[2])) <= CORNER_REFINE_OCT + 1e-3
            and abs(math.log2(row["hp"][2] / hp[2])) <= CORNER_REFINE_OCT + 1e-3)


def _check_family_outside_profile_never_returned():
    """The planted best is a Bessel; the project offers only LR and BW: no row names a family outside the profile."""
    fams = [("LR", 24), ("LR", 36), ("BW", 24)]
    res = scan_bass(_planted_input(hp=("BE", 24, 90.0), fams=fams, delay_ms=2.4))
    assert res["rows"], "no rows came back"
    seen = {tuple(r["hp"][:2]) for r in res["rows"]} | {tuple(r["lp"][:2]) for r in res["rows"]}
    assert seen <= set(fams), seen


def _check_lr_offset_condition():
    """The held L-R offset rejects the planted best when it breaks the rule: the planted L-R is 0 ms and the rule says +2.5
    ms, which puts the L+R sum's phase flip inside the band. With the condition on no row carries the planted offset and the
    band is narrower; off, the planted pair comes back near 0, wider by a margin. And the condition's own arithmetic: the
    signed rule within +-0.10 ms, the same polarity, the same family."""
    held = scan_bass(_planted_input(lr_rule_ms=2.5))
    assert held["rows"], "no rows with the condition on"
    assert all(abs(r["lr_offset_ms"] - 2.5) < 1e-6 for r in held["rows"]), held["rows"][0]["lr_offset_ms"]
    free = scan_bass(_planted_input(lr_rule_ms=2.5, free_lr_offset=True))
    assert free["rows"], "no rows with the condition off"
    assert abs(free["rows"][0]["lr_offset_ms"]) <= FREE_OFFSET_STEP_MS, free["rows"][0]["lr_offset_ms"]
    assert _is_planted(free["rows"][0]) or _is_near(free["rows"][0]), free["rows"][0]["lp"]
    assert free["rows"][0]["width_worst_oct"] >= held["rows"][0]["width_worst_oct"] + 0.3, \
        (free["rows"][0]["width_worst_oct"], held["rows"][0]["width_worst_oct"])
    assert not check_stage(rule_ms=-1.37, lr_delay_ms=-1.30), "a delay L-R 0.07 ms from the rule should pass"
    assert check_stage(rule_ms=-1.37, lr_delay_ms=-1.20), "a delay L-R 0.17 ms from the rule should be rejected"


def _check_joints_from_roles():
    """The joints are the adjacent roles of the stack: 3-way + sub, 2-way + sub, 2-way alone, a front sub (a `sub` role wherever
    it sits), a single sub with no L/R rule, a stereo sub as a pair."""
    def ch(**roles):
        return {code: {"code": code, "role": role} for code, role in roles.items()}
    three = dict(ch(sw="sub"), **{"w-L": {"role": "woofer"}, "w-R": {"role": "woofer"}, "m-L": {"role": "midrange"},
                                  "m-R": {"role": "midrange"}, "tw-L": {"role": "tweeter"}, "tw-R": {"role": "tweeter"},
                                  "c": {"role": "center"}})
    assert [j.name for j in joints_of(three)] == ["sub-woofer", "woofer-midrange", "midrange-tweeter"]
    two_sub = {k: v for k, v in three.items() if k not in ("m-L", "m-R", "c")}
    joints = joints_of(two_sub)
    assert [j.name for j in joints] == ["sub-woofer", "woofer-tweeter"], [j.name for j in joints]
    assert joints[0].lower.single and joints[0].cls == "bass" and joints[0].upper.codes == ("w-L", "w-R"), joints[0]
    two = {k: v for k, v in two_sub.items() if k != "sw"}
    assert [j.name for j in joints_of(two)] == ["woofer-tweeter"]
    sub_mid = {k: v for k, v in three.items() if k not in ("w-L", "w-R", "tw-L", "tw-R", "c")}
    assert [j.name for j in joints_of(sub_mid)] == ["sub-midrange"]
    stereo = dict({k: v for k, v in three.items() if k != "sw"}, **{"sw-L": {"role": "sub"}, "sw-R": {"role": "sub"}})
    j0 = joints_of(stereo)[0]
    assert not j0.lower.single and j0.lower.codes == ("sw-L", "sw-R") and j0.cls == "bass", j0


def _check_leak_and_dip_conditions():
    """Bass conditions: a sub leaking 24 dB above the joint and a sum dropping under the dip limit are rejected; the same
    grid without the conditions has them."""
    leaky = ("LR", 24, 80.0)
    res = scan_bass(_planted_input(lp=leaky, hp=_PLANT_HP, lp_corners=(56, 80), hp_corners=(90,)))
    assert all(r["lp"] != list(leaky) for r in res["rows"]), [r["lp"] for r in res["rows"]][:4]
    assert res["rejected"].get("leak", 0) > 0, res["rejected"]
    off = scan_bass(_planted_input(lp=leaky, hp=_PLANT_HP, lp_corners=(56, 80), hp_corners=(90,), leak_on=False))
    assert any(r["lp"] == list(leaky) for r in off["rows"]), [r["lp"] for r in off["rows"]][:4]
    # a target asking 10 dB more over the dip band than any candidate has: every row falls on the dip, none without the condition
    base = _planted_input()
    hole = base.target_db.copy()
    band = (base.freqs >= 45.0) & (base.freqs <= 110.0)
    hole[band] += 10.0
    base.target_db = hole
    dipped = scan_bass(base)
    assert not dipped["rows"] and dipped["rejected"].get("dip", 0) > 0, (len(dipped["rows"]), dipped["rejected"])
    base2 = _planted_input(dip_on=False)
    base2.target_db = hole
    assert scan_bass(base2)["rows"], "with the dip condition off the same grid must hold rows"


def _check_sub_one_point_limit():
    """A sub measured at one point: a crossing at or over 100 Hz needs its points and is rejected; with the points it stands."""
    lp, hp = ("LR", 36, 113.0), ("LR", 36, 113.0)
    kw = dict(lp=lp, hp=hp, lp_corners=(113,), hp_corners=(113,), leak_on=False, dip_on=False, delay_ms=1.0)
    one = scan_bass(_planted_input(sub_one_point=True, **kw))
    assert one["rejected"].get("sub_one_point", 0) > 0, one["rejected"]
    assert all(r["crossing_hz"] < SUB_ONE_POINT_MAX_HZ for r in one["rows"]), [r["crossing_hz"] for r in one["rows"]][:4]
    points = scan_bass(_planted_input(sub_one_point=False, **kw))
    assert any(r["crossing_hz"] >= SUB_ONE_POINT_MAX_HZ for r in points["rows"]), [r["crossing_hz"] for r in points["rows"]][:4]


def _check_hp_floor():
    """The floor of the high-pass (Fs times the role's multiple) holds, refine steps included: nothing under it comes back."""
    inp = _planted_input(hp_corners=(71, 90, 125))
    inp.hp_options = [o for o in inp.hp_options if o[2] >= 90.0]
    inp.hp_floor_hz = 90.0
    res = scan_bass(inp)
    assert res["rows"], "no rows came back"
    assert all(r["hp"][2] >= 90.0 for r in res["rows"]), sorted({r["hp"][2] for r in res["rows"]})[:4]


def _fixture(top, *, fs=True, profile=None, roles=None):
    """A project: roles, a profile (LR/BW only, narrow), a flat target."""
    proj = os.path.join(top, "project")
    os.makedirs(proj)
    pj = _pj.Project(proj)
    data = pj.load()
    roles = roles or {"sw": "sub", "w-L": "woofer", "w-R": "woofer"}
    data["channels"] = [{"code": c, "role": r, "fs_hz": 50.0 if fs else None} for c, r in roles.items()]
    pj.save(data)
    prof = profile or {
        "dsp_profile": {"name": "X", "dsp_processing_rate_hz": 96000, "delay": {"max_ms": 20.0, "step_ms": 0.01},
                        "channel_gain": {"range_db": [-30.0, 5.0]},
                        "groups": [{"id": "physical_outputs", "crossover_filters": {
                            "corner_freq_range_hz": [20.0, 20480.0], "corner_freq_step_hz": 1.0,
                            "types": {"LR": {"orders_db_per_oct": [24, 36]}, "BW": {"orders_db_per_oct": [24]}}}}]}}
    with open(os.path.join(proj, "dsp_profile.json"), "w", encoding="utf-8") as fh:
        json.dump(prof, fh)
    house = os.path.join(top, "house.txt")
    with open(house, "w", encoding="utf-8") as fh:
        fh.write("20 0\n20000 0\n")
    return proj, house


def _write_ir(path, at, *, rew_source=None, level=0.5):
    import resonalyze_ir as ri
    x = np.zeros(1 << 13)
    x[at] = level
    doc = ri.build_v7(x, 96000, 0.0, low_hz=20.0, high_hz=20000.0, rew_source=rew_source)
    ri.write_v7(doc[0] if isinstance(doc, tuple) else doc, path)


def _write_solos(solos, codes, *, points=None, at=None, rew_source=None):
    os.makedirs(solos, exist_ok=True)
    at = at or {}
    for code in codes:
        stem = code.replace("-", "_")
        _write_ir(os.path.join(solos, f"{stem}.json"), at.get(code, 96), rew_source=rew_source)
        for pos in (points or {}).get(code, ()):
            _write_ir(os.path.join(solos, f"{stem}-{pos}.json"), at.get(code, 96), rew_source=rew_source)


def _run(argv):
    """`(rc, stdout, stderr)` of `_main`; a traceback is rc "raised <type>: <message>"."""
    import contextlib
    import io as _io
    out, err = _io.StringIO(), _io.StringIO()
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = _main(argv)
    except BaseException as exc:  # noqa: BLE001 -- a traceback is the failure under test
        rc = f"raised {type(exc).__name__}: {exc}"
    return rc, out.getvalue(), err.getvalue()


_TINY = ["--lp-bounds", "56:71", "--hp-bounds", "56:80", "--gain", "2:8:2"]
_FRONT_POINTS = {"w-L": POSITIONS, "w-R": POSITIONS}


def _check_refusals_are_one_line():
    """Each refusal is one line, exit 3, nothing on stdout: a missing Fs (and an inherited one), an unreadable profile, a front
    driver without its nine points, `--single-point` with no decision on record, curves from two sessions, a grid over the
    ceiling. Each is said in words."""
    import shutil
    import tempfile
    failures = []
    def case(label, build, said):
        top = tempfile.mkdtemp(prefix="autosound_jointsearch_")
        try:
            argv = build(top)
            rc, out, err = _run(argv)
            lines = err.strip().splitlines()
            refusal = [ln for ln in lines if ln.startswith("refusing:")]
            if rc != 3 or out.strip() or len(refusal) != 1 or said not in refusal[0]:
                failures.append(f"{label}: rc {rc!r}, out {out[:120]!r}, err {err[-300:]!r}")
        finally:
            shutil.rmtree(top, ignore_errors=True)

    def base(top, **kw):
        proj, house = _fixture(top, **kw)
        solos = os.path.join(top, "solos")
        _write_solos(solos, ("sw", "w-L", "w-R"), points=_FRONT_POINTS, at={"w-L": 200, "w-R": 100})
        return ["--project", proj, "--house", house, "--solos", solos] + _TINY, proj, solos, house

    case("a missing Fs", lambda t: base(t, fs=False)[0], "no Fs on record")

    def inherited(t):
        argv, proj, _, _ = base(t)
        pj = _pj.Project(proj)
        data = pj.load()
        for row in data["channels"]:
            if row["role"] == "woofer":
                row["fs_hz"] = {"value": 50.0, "origin": "inherited", "inherited_from": "/x"}
        pj.save(data)
        return argv
    case("an inherited Fs", inherited, "carried in from")

    def bad_profile(t):
        argv, proj, _, _ = base(t)
        with open(os.path.join(proj, "dsp_profile.json"), "wb") as fh:
            fh.write(b'{"dsp_profile": {"nam')
        return argv
    case("an unreadable profile", bad_profile, "dsp_profile.json")

    def no_profile(t):
        argv, proj, _, _ = base(t)
        os.remove(os.path.join(proj, "dsp_profile.json"))
        return argv
    case("no profile at all", no_profile, "dsp_profile.json")

    def no_points(t):
        proj, house = _fixture(t)
        solos = os.path.join(t, "solos")
        _write_solos(solos, ("sw", "w-L", "w-R"))
        return ["--project", proj, "--house", house, "--solos", solos] + _TINY
    case("a front driver without its nine points", no_points, "nine points")

    def single_without_record(t):
        argv = no_points(t)
        return argv + ["--single-point"]
    case("--single-point with no decision on record", single_without_record, "decision")

    def two_sessions(t):
        argv, _, solos, _ = base(t)
        other = os.path.join(t, "subsolos")
        _write_solos(other, ("sw",))
        return argv + ["--sub-solos", other]
    case("curves from two sessions", two_sessions, "--level-step")

    def over_ceiling(t):
        big = {"dsp_profile": {"name": "X", "dsp_processing_rate_hz": 96000, "delay": {"max_ms": 20.0, "step_ms": 0.01},
                               "channel_gain": {"range_db": [-30.0, 5.0]},
                               "groups": [{"id": "physical_outputs", "crossover_filters": {
                                   "corner_freq_range_hz": [20.0, 20480.0], "corner_freq_step_hz": 1.0,
                                   "types": {"LR": {"orders_db_per_oct": [12, 24, 36]},
                                             "BW": {"orders_db_per_oct": [6, 12, 18, 24, 30, 36, 42]},
                                             "BE": {"orders_db_per_oct": [6, 12, 18, 24, 30, 36, 42]}}}}]}}
        proj, house = _fixture(t, profile=big)
        solos = os.path.join(t, "solos")
        os.makedirs(solos)
        return ["--project", proj, "--house", house, "--solos", solos, "--lp-bounds", "20:20000", "--hp-bounds", "20:20000",
                "--gain", "0:4:2"]
    case("a grid over the ceiling", over_ceiling, "--allow-large-grid")

    def missing_joint(t):
        argv, _, _, _ = base(t, roles={"w-L": "woofer", "w-R": "woofer", "tw-L": "tweeter", "tw-R": "tweeter"})
        return argv
    case("a stack with no bass joint", missing_joint, "bass joint")

    assert not failures, "\n  ".join(["refusals not in the one form:"] + failures)


def _check_protective_refusal_passed_on():
    """A protective filter the method cannot take out (a Chebyshev) is refused at the de-embedding and the refusal is passed on as it stands."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_jointsearch_")
    try:
        proj, house = _fixture(top)
        solos = os.path.join(top, "solos")
        src = {"protectiveHighPass": {"hz": 100, "family": "CH", "slopeDbPerOct": 24}, "protectiveState": "raw"}
        _write_solos(solos, ("sw", "w-L", "w-R"), points=_FRONT_POINTS, at={"w-L": 200, "w-R": 100}, rew_source=src)
        rc, out, err = _run(["--project", proj, "--house", house, "--solos", solos] + _TINY)
        last = (err.strip().splitlines() or [""])[-1]
        assert rc == 3 and not out.strip() and last.startswith("refusing:") \
            and "protective HP 100 Hz CH24 cannot be taken out" in last, (rc, out[:120], err[-400:])
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_cli_end_to_end():
    """The command line on a small project: the count printed before the run, the table, the held offset read from the arrivals
    (L later by 1.04 ms -> DSP L-R -1.04), `--json`, `--out`, and no pick. `--single-point` with the decision marks every row."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_jointsearch_")
    try:
        proj, house = _fixture(top)
        solos = os.path.join(top, "solos")
        _write_solos(solos, ("sw", "w-L", "w-R"), points=_FRONT_POINTS, at={"w-L": 200, "w-R": 100})
        out_dir = os.path.join(top, "out")
        rc, out, err = _run(["--project", proj, "--house", house, "--solos", solos, "--json", "--out", out_dir] + _TINY)
        assert rc == 0, (rc, err[-600:])
        assert "filter pairs" in err, err[:400]
        doc = json.loads(out)
        assert doc["rows"] and abs(doc["rows"][0]["lr_offset_ms"] - (-100.0 / 96.0)) < 0.03, doc["rows"][0]["lr_offset_ms"]
        assert doc["joint"] == "sub-woofer" and doc["joints_in_stack"] == ["sub-woofer"], doc["joints_in_stack"]
        assert doc["grid"]["pairs"] == len(doc["grid"]["lp_options"]) * len(doc["grid"]["hp_options"]), doc["grid"]
        assert os.path.isfile(os.path.join(out_dir, "joint-sub-woofer.json"))
        assert "never picks" in doc["note"], doc["note"]
        rc, out, err = _run(["--project", proj, "--house", house, "--solos", solos] + _TINY)
        assert rc == 0 and "the choice is the tuner's" in out and "sub-woofer" in out, (rc, out[-300:], err[-300:])
        state_dir = os.path.join(_HERE, "state")
        if state_dir not in sys.path:
            sys.path.insert(0, state_dir)
        import process as _process
        _process.Process(os.path.join(proj, "process")).record_decision("the ellipsoid capture?", _DECISION_WORDS)
        solos2 = os.path.join(top, "solos2")
        _write_solos(solos2, ("sw", "w-L", "w-R"), at={"w-L": 200, "w-R": 100})
        rc, out, err = _run(["--project", proj, "--house", house, "--solos", solos2, "--single-point", "--json"] + _TINY)
        assert rc == 0, (rc, err[-400:])
        doc = json.loads(out)
        assert doc["rows"] and all("single-point" in r["marks"] for r in doc["rows"]), doc["rows"][:1]
    finally:
        shutil.rmtree(top, ignore_errors=True)


# -------- the fix round's tests (#210, review of 3d1d11b): each pins one finding; drivers with their own phase where the band decides
#: One filter pair on the planted grid: for the checks about what comes out of a row, not about which row ranks first.
_ONE_PAIR = {"fams": [("LR", 36)], "lp_corners": (56,), "hp_corners": (90,)}


def _tmp():
    """A throwaway folder for one check: `(path, remove)`."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_jointsearch_")
    return top, (lambda: shutil.rmtree(top, ignore_errors=True))


def _doc(argv):
    rc, out, err = _run(argv + ["--json"])
    assert rc == 0, (rc, err[-600:])
    return json.loads(out)


def _solo_project(top, roles=None, profile=None, at=None, points=_FRONT_POINTS, fs=True):
    """A small project on disk and the common part of its command line."""
    proj, house = _fixture(top, fs=fs, profile=profile, roles=roles)
    solos = os.path.join(top, "solos")
    codes = tuple((roles or {"sw": "sub", "w-L": "woofer", "w-R": "woofer"}))
    _write_solos(solos, codes, points=points, at=at or {"w-L": 200, "w-R": 100})
    return ["--project", proj, "--house", house, "--solos", solos], proj, house, solos


def _band_width(f, diff_deg, centre_hz):
    """The in-tolerance run through `centre_hz`, in octaves, walked plainly: the scan's `_widths`, written another way."""
    i = int(np.argmin(np.abs(f - centre_hz)))
    assert abs(diff_deg[i]) <= PHASE_WINDOW_DEG, (centre_hz, diff_deg[i])
    lo = hi = i
    while lo > 0 and abs(diff_deg[lo - 1]) <= PHASE_WINDOW_DEG:
        lo -= 1
    while hi < len(f) - 1 and abs(diff_deg[hi + 1]) <= PHASE_WINDOW_DEG:
        hi += 1
    return math.log2(f[hi] / f[lo])


def _row_phase(inp, row, p=0):
    """The sub minus front phase of a row at point `p`, degrees, from its own settings: an independent reading of the row."""
    f = np.asarray(inp.freqs, float)
    lp = dsp_math.xo_response(f, row["lp"][2], row["lp"][1], "lp", row["lp"][0])
    hp = dsp_math.xo_response(f, row["hp"][2], row["hp"][1], "hp", row["hp"][0])
    sub = (-1.0 if row["polarity"] == "INV" else 1.0) * inp.lower[p] * lp
    front = _front_sum(inp.upper_l[p], None if inp.upper_r is None else inp.upper_r[p], f, row["lr_offset_ms"]) * hp \
        * np.exp(-2j * np.pi * f * row["delay_ms"] * 1e-3)
    return np.degrees(np.angle(sub * np.conj(front)))


def _own_phase_input(band=(55.0, 140.0), tilt=25.0, off=90.0, n_points=1, **kw):
    """Drivers with their own phase: inside `band` the sub leads the planted pair's sum by `tilt` degrees, outside by `off`,
    so the ±30 degree band is a known run and the sum inside it is not a perfect one."""
    inp = _planted_input(n_points=n_points, leak_on=False, dip_on=False, single_upper=True, **kw)
    f = inp.freqs
    inp.lower = inp.lower * np.exp(1j * np.radians(np.where((f >= band[0]) & (f <= band[1]), tilt, off)))
    inp.ref_lower = inp.lower[0]
    return inp


def _check_band_decides_the_rank():
    """T1: drivers with their own phase, and the ±30 degree band itself ranks the rows. Rows with a better summation loss stay
    below the widest band, and the band each row reports is the band its own settings have, read independently of the scan."""
    inp = _own_phase_input()
    rows = scan_bass(inp)["rows"]
    assert len(rows) > 2, len(rows)
    top = rows[0]
    better_loss = [r for r in rows if r["loss_median_db"] > top["loss_median_db"] + 0.05]
    assert better_loss, "no row with a better loss: the plant does not separate the band from the loss"
    assert all(r["width_worst_oct"] <= top["width_worst_oct"] for r in rows), top["width_worst_oct"]
    assert all(r["width_worst_oct"] < top["width_worst_oct"] for r in better_loss), \
        [(r["width_worst_oct"], top["width_worst_oct"]) for r in better_loss][:3]
    step = math.log2(inp.freqs[1] / inp.freqs[0])
    for row in [top] + better_loss[:5]:
        read = _band_width(inp.freqs, _row_phase(inp, row), row["crossing_hz"])
        assert abs(read - row["width_worst_oct"]) <= 1.01 * step, (read, row["width_worst_oct"], row["lp"], row["hp"])
    assert top["width_worst_oct"] > 1.2, top["width_worst_oct"]


def _check_worst_and_median_of_points():
    """T2: three points whose bands differ by construction. Each has the planted pair in phase over its own known run, so the
    worst, the median and the ranking are read off the plan: not the same number three times."""
    edges = ((50.0, 170.0), (55.0, 150.0), (62.0, 120.0))
    inp = _planted_input(lp=_PLANT_LP, hp=_PLANT_HP, fams=[("LR", 36)], lp_corners=(56,), hp_corners=(90,), n_points=3,
                         leak_on=False, dip_on=False, single_upper=True)
    for p, (lo, hi) in enumerate(edges):
        inp.lower[p] = inp.lower[p] * np.exp(1j * np.radians(np.where((inp.freqs >= lo) & (inp.freqs <= hi), 0.0, 90.0)))
    inp.ref_lower = inp.lower[0]
    best = scan_bass(inp)["rows"][0]
    want = sorted(math.log2(hi / lo) for lo, hi in edges)
    step = math.log2(inp.freqs[1] / inp.freqs[0])
    assert abs(best["width_worst_oct"] - want[0]) <= 2 * step, (best["width_worst_oct"], want)
    assert abs(best["width_median_oct"] - want[1]) <= 2 * step, (best["width_median_oct"], want)
    assert best["width_worst_oct"] < best["width_median_oct"] - 0.3, (best["width_worst_oct"], best["width_median_oct"])


def _musway_profile():
    with open(os.path.join(_HERE, "..", "knowledge", "dsp", "profiles", "musway-m6v4.json"), encoding="utf-8") as fh:
        return json.load(fh)


def _check_space_and_rows_against_a_profile():
    """T3, B2, M1: `space_of` on the real Musway profile (odd LRs in its menu, corner step and range at the top level, delay step
    0.021 ms, attenuation only): the families the model builds and none it does not, the dropped ones named; every row of the
    command line inside the profile, on its delay step, gains in its range; the corners on its step."""
    top, done = _tmp()
    try:
        argv, proj, _, _ = _solo_project(top, profile=_musway_profile())
        space = space_of(proj)
        assert ("LR", 24) in space.families and ("LR", 48) in space.families, space.families
        for gone in (("LR", 6), ("LR", 18), ("LR", 30), ("LR", 42), ("BW", 48), ("BE", 48)):
            assert gone not in space.families, (gone, space.families)
        assert {"LR6", "LR18", "LR30", "LR42", "BW48", "BE48"} <= set(space.dropped), space.dropped
        doc = _doc(argv + ["--lp-bounds", "56:63", "--hp-bounds", "71:80", "--gain", "4:8:2"])
        assert doc["rows"], doc["rejected"]
        said = " ".join(doc["notes"])
        assert all(name in said for name in ("LR6", "LR18", "LR30", "LR42")), said
        for row in doc["rows"]:
            for side in ("lp", "hp"):
                assert tuple(row[side][:2]) in space.families, row[side]
                assert row[side][2] == round(row[side][2]) and 20 <= row[side][2] <= 20000, row[side]
            assert -59.9 <= row["sub_gain_db"] <= 0.0 and -59.9 <= row["front_gain_db"] <= 0.0, row
            for code, ms in row["delays_ms"].items():
                assert 0.0 <= ms <= 17.0, (code, ms)
                assert abs(ms / 0.021 - round(ms / 0.021)) < 1e-3, (code, ms)
    finally:
        done()


def _check_corners_from_the_top_level():
    """I7: a corner step and range stated at the profile's top level (Musway's shape) bind the grid, with the types in the group."""
    prof = {"dsp_profile": {"name": "X", "dsp_processing_rate_hz": 96000, "delay": {"max_ms": 20.0, "step_ms": 0.01},
                            "channel_gain": {"range_db": [-30.0, 5.0]},
                            "crossover_filters": {"corner_freq_range_hz": [20.0, 20000.0], "corner_freq_step_hz": 5.0},
                            "groups": [{"id": "physical_outputs", "crossover_filters": {
                                "types": {"LR": {"orders_db_per_oct": [24, 36]}}}}]}}
    top, done = _tmp()
    try:
        argv, proj, _, _ = _solo_project(top, profile=prof)
        xo = profile_xo(proj)
        assert xo["step"] == 5.0 and xo["range"] == [20.0, 20000.0], xo
        assert all(c % 5 == 0 for c in corner_grid((50.0, 100.0), xo)), corner_grid((50.0, 100.0), xo)
        doc = _doc(argv + _TINY)
        assert doc["rows"], doc["rejected"]
        assert all(r["lp"][2] % 5 == 0 and r["hp"][2] % 5 == 0 for r in doc["rows"]), doc["rows"][0]
    finally:
        done()


def _check_stereo_sub_delays():
    """B1: two subs as an L/R pair. The search sums them with the rule's offset and the table gets each sub's own delay through
    the same floor and ceiling as the front's: the pair's offset is on the output and in the conditions, nothing goes negative,
    and a pair past the ceiling is rejected."""
    # at the unit: a held sub L-R offset comes out as sub L and sub R, floored at zero
    inp = _planted_input(delay_ms=-3.0, single_upper=True, max_ms=8.0, **_ONE_PAIR)
    inp.lower_offset_ms = 1.0
    best = scan_bass(inp)["rows"][0]
    tas = best["ta_ms"]
    assert tas.get("sub_left") is not None and abs(tas["sub_left"] - tas["sub_right"] - 1.0) < 1e-6, tas
    assert min(tas["sub_left"], tas["sub_right"], tas["upper_left"]) >= 0.0, tas
    inp = _planted_input(delay_ms=-0.4, single_upper=True, max_ms=8.0, **_ONE_PAIR)
    inp.lower_offset_ms = -1.0
    tas = scan_bass(inp)["rows"][0]["ta_ms"]
    assert tas.get("sub_left") is not None and abs(tas["sub_left"] - tas["sub_right"] + 1.0) < 1e-6, tas
    assert min(tas["sub_left"], tas["sub_right"], tas["upper_left"]) == 0.0, tas
    # past the ceiling: the sub's delay plus its offset does not fit under 3.2 ms
    inp = _planted_input(delay_ms=-3.0, single_upper=True, max_ms=3.2, **_ONE_PAIR)
    inp.lower_offset_ms = 1.0
    res = scan_bass(inp)
    assert res["rejected"].get("delay", 0) > 0, res["rejected"]
    assert all(max(r["ta_ms"]["sub_left"], r["ta_ms"]["sub_right"]) <= 3.2 + 1e-9 for r in res["rows"]), res["rows"][:1]
    # the command line: the rule from the arrivals, both subs in the table
    top, done = _tmp()
    try:
        roles = {"sw-L": "sub", "sw-R": "sub", "w-L": "woofer", "w-R": "woofer"}
        argv, _, _, _ = _solo_project(top, roles=roles, at={"sw-L": 192, "sw-R": 96, "w-L": 200, "w-R": 100},
                                      points={"w-L": POSITIONS, "w-R": POSITIONS})
        doc = _doc(argv + _TINY)
        rule = doc["conditions"]["lower_lr_offset_ms"]
        assert doc["rows"] and rule < -0.1, (rule, doc["rejected"])
        for row in doc["rows"]:
            ms = row["delays_ms"]
            assert abs(ms["sw-L"] - ms["sw-R"] - rule) <= 0.011, (ms, rule)
            assert min(ms.values()) == 0.0 and max(ms.values()) <= 20.0, ms
        rc, text, _err = _run(argv + _TINY)
        assert rc == 0 and "sw-L" in text and "sw-R" in text, text[:400]
    finally:
        done()


def _check_table_enterable():
    """I1: the default table carries what a person keys in: the sub's gain, the front's gain, each channel's delay; and `who_delays`
    follows the split, not the sign of the delay: +0.5 ms with a -1.5 ms L-R offset puts the zero on L and the delay on the sub."""
    inp = _planted_input(delay_ms=0.5, lr_rule_ms=-1.5, offset_ms=-1.5, **_ONE_PAIR)
    best = scan_bass(inp)["rows"][0]
    assert best["delay_ms"] > 0 and best["who_delays"] == "sub", (best["delay_ms"], best["who_delays"], best["ta_ms"])
    top, done = _tmp()
    try:
        argv, _, _, _ = _solo_project(top)
        doc = _doc(argv + _TINY)
        row = doc["rows"][0]
        assert set(row["delays_ms"]) == {"sw", "w-L", "w-R"} and "sub_gain_db" in row and "front_gain_db" in row, row
        rc, text, _err = _run(argv + _TINY)
        assert rc == 0, _err
        head = next(ln for ln in text.splitlines() if "LP" in ln and "HP" in ln)
        for name in ("sub dB", "front dB", "sw", "w-L", "w-R"):
            assert name in head, (name, head)
        line = next(ln for ln in text.splitlines() if ln.strip().startswith(_filter_name(row["lp"]))
                    and _filter_name(row["hp"]) in ln)
        fields = line.split()
        for value in (f"{row['sub_gain_db']:+.1f}", f"{row['front_gain_db']:+.1f}", f"{row['delays_ms']['sw']:.3f}",
                      f"{row['delays_ms']['w-L']:.3f}", f"{row['delays_ms']['w-R']:.3f}"):
            assert value in fields, (value, line)
    finally:
        done()


def _check_free_offset_is_said():
    """I2: under `--no-lr-offset` the header says the offset is free, every row shows its own."""
    top, done = _tmp()
    try:
        argv, _, _, _ = _solo_project(top)
        tiny = ["--lp-bounds", "56:63", "--hp-bounds", "71:80", "--gain", "6:8:2", "--no-lr-offset"]
        rc, text, _err = _run(argv + tiny)
        assert rc == 0, _err[-400:]
        head = text.splitlines()[0]
        assert "free" in head and "held" not in head, head
        doc = _doc(argv + tiny)
        assert doc["conditions"]["lr_offset_held"] is False, doc["conditions"]
        offsets = {r["lr_offset_ms"] for r in doc["rows"]}
        assert doc["rows"] and any(f"{off:+.2f}" in text for off in offsets), (offsets, text[:300])
        table = [ln for ln in text.splitlines() if "L-R" in ln and "LP" in ln]
        assert table, text[:400]
    finally:
        done()


def _check_notes_printed():
    """I3: `render` prints the notes, in the text and in `--out`'s `.txt`."""
    top, done = _tmp()
    try:
        argv, _, _, _ = _solo_project(top)
        out_dir = os.path.join(top, "out")
        rc, text, err = _run(argv + _TINY + ["--out", out_dir])
        assert rc == 0, err[-400:]
        with open(os.path.join(out_dir, "joint-sub-woofer.json"), encoding="utf-8") as fh:
            notes = json.load(fh)["notes"]
        assert notes, "the plain run has notes (the solo-used lines)"
        for line in notes:
            assert line in text, (line, text[:400])
        with open(os.path.join(out_dir, "joint-sub-woofer.txt"), encoding="utf-8") as fh:
            txt = fh.read()
        assert all(line in txt for line in notes), txt[:400]
    finally:
        done()


def _check_leak_relative_to_the_crossing():
    """I4: a crossing near 120 Hz with a sub that falls away fast above it is no leak: 100 and 125-200 Hz were one car's. The same
    pair with a gentle low-pass, which still sits under -24 dB at 100 Hz of its own crossing band, is rejected at 1.5x."""
    lp, hp = ("LR", 48, 113.0), ("LR", 36, 113.0)
    good = scan_bass(_planted_input(lp=lp, hp=hp, fams=[("LR", 48), ("LR", 36)], lp_corners=(113,), hp_corners=(113,), delay_ms=1.0,
                                    dip_on=False))
    assert any(r["lp"] == list(lp) and r["crossing_hz"] > 100.0 for r in good["rows"]), (good["rejected"], good["rows"][:1])
    for r in good["rows"]:
        assert r["leak_near_db"] <= -24.0 and r["leak_far_db"] <= -30.0, r
    gentle = scan_bass(_planted_input(lp=("LR", 12, 113.0), hp=("LR", 12, 113.0), fams=[("LR", 12)], lp_corners=(113,), hp_corners=(113,),
                                      delay_ms=1.0, dip_on=False))
    assert not gentle["rows"] and gentle["rejected"].get("leak", 0) > 0, gentle["rejected"]


def _check_no_leak_and_empty_words():
    """I4: `--no-leak` and `--no-dip` lift their conditions; an empty result says so in words with the reasons counted, exit 0."""
    top, done = _tmp()
    try:
        argv, _, house, _ = _solo_project(top)
        with open(house, "w", encoding="utf-8") as fh:
            fh.write("20 0\n44 0\n46 18\n110 18\n112 0\n20000 0\n")
        rc, text, err = _run(argv + _TINY)
        assert rc == 0, (rc, err[-400:])
        assert "No variant" in text and "dip" in text and any(ch.isdigit() for ch in text.split("No variant", 1)[1]), text[-500:]
        doc = _doc(argv + _TINY)
        assert not doc["rows"] and doc["rejected"].get("dip", 0) > 0, doc["rejected"]
        nodip = _doc(argv + _TINY + ["--no-dip"])
        assert nodip["rows"], nodip["rejected"]
        noleak = _doc(argv + _TINY + ["--no-dip", "--no-leak"])
        assert noleak["rows"] and noleak["rejected"].get("leak", 0) == 0, noleak["rejected"]
    finally:
        done()


def _check_front_lp_moves_the_delay():
    """I5: `--front-lp` puts the woofer's low-pass in the model and the search answers with another delay; without it a stack with
    a joint above the bass says the delay will shift; a stack with nothing above it, or the flag given, stays silent."""
    top, done = _tmp()
    try:
        roles = {"sw": "sub", "w-L": "woofer", "w-R": "woofer", "tw-L": "tweeter", "tw-R": "tweeter"}
        argv, _, _, _ = _solo_project(top, roles=roles, at={"sw": 96, "w-L": 200, "w-R": 100, "tw-L": 100, "tw-R": 100}, points=_FRONT_POINTS)
        plain = _doc(argv + _TINY)
        assert any("low-pass" in n and "re-scored" in n for n in plain["notes"]), plain["notes"]
        lp = _doc(argv + _TINY + ["--front-lp", "LR", "24", "280"])
        assert not any("re-scored" in n for n in lp["notes"]), lp["notes"]
        assert lp["conditions"]["front_lp"] == ["LR", 24, 280.0], lp["conditions"]
        d_plain = {(tuple(r["lp"]), tuple(r["hp"]), r["sub_rel_db"], r["polarity"]): r["delay_ms"] for r in plain["rows"]}
        d_lp = {(tuple(r["lp"]), tuple(r["hp"]), r["sub_rel_db"], r["polarity"]): r["delay_ms"] for r in lp["rows"]}
        common = set(d_plain) & set(d_lp)
        assert common and any(abs(d_plain[k] - d_lp[k]) >= 0.05 for k in common), (len(common), sorted(common)[:2])
        bad = _run(argv + _TINY + ["--front-lp", "XX", "24", "280"])
        assert bad[0] == 3 and "refusing:" in bad[2], bad[0]
    finally:
        done()
    top, done = _tmp()
    try:
        argv, _, _, _ = _solo_project(top)
        assert not any("re-scored" in n for n in _doc(argv + _TINY)["notes"])
    finally:
        done()


_DECISION_WORDS = "nine points skipped; the joints run on one point"


def _process_module():
    state_dir = os.path.join(_HERE, "state")
    if state_dir not in sys.path:
        sys.path.insert(0, state_dir)
    import process
    return process


def _check_single_point_needs_the_decision():
    """I6: the decision is on record in its words. A round that merely asked for positions, the bare word "position" in a ruling, a
    question put and refused: none of them passes. The refusal says the exact words to record."""
    proc = _process_module()
    top, done = _tmp()
    try:
        argv, proj, _, solos = _solo_project(top, points=None)
        cmd = argv + _TINY + ["--single-point"]
        p = proc.Process(os.path.join(proj, "process"))
        p.record_decision("the ellipsoid capture?", "no positions, one point only")
        rc, out, err = _run(cmd)
        assert rc == 3 and _DECISION_WORDS in err, (rc, err[-300:])
        p.record_decision("position", "the bare word")
        assert _run(cmd)[0] == 3, "the bare word passed"
        p.record_decision(_DECISION_WORDS, "ні")
        assert _run(cmd)[0] == 3, "a question refused by the person passed"
        p.record_decision(_DECISION_WORDS, "так, так і зробимо")
        rc, out, err = _run(cmd)
        assert rc == 0, (rc, err[-300:])
    finally:
        done()
    assert SINGLE_POINT_DECISION == _DECISION_WORDS, SINGLE_POINT_DECISION
    top, done = _tmp()
    try:
        # the words in the answer stand as well
        argv, proj, _, _ = _solo_project(top, points=None)
        proc.Process(os.path.join(proj, "process")).record_decision("can we do without the positions?", _DECISION_WORDS)
        rc, _out, err = _run(argv + _TINY + ["--single-point"])
        assert rc == 0, err[-300:]
    finally:
        done()


def _check_single_point_rule_on_any_reference():
    """M3: the single-point rule takes what `_ref_curve` takes: a stereo front with only p5 at the rule and no tripod runs, where
    it read the tripod alone and refused."""
    proc = _process_module()
    top, done = _tmp()
    try:
        roles = {"sw": "sub", "w-L": "woofer", "w-R": "woofer"}
        proj, house = _fixture(top, roles=roles)
        solos = os.path.join(top, "solos")
        os.makedirs(solos)
        _write_ir(os.path.join(solos, "sw.json"), 96)
        _write_ir(os.path.join(solos, "w_L-p5.json"), 200)
        _write_ir(os.path.join(solos, "w_R-p5.json"), 100)
        proc.Process(os.path.join(proj, "process")).record_decision("the ellipsoid?", _DECISION_WORDS)
        doc = _doc(["--project", proj, "--house", house, "--solos", solos] + _TINY + ["--single-point"])
        assert doc["rows"] and abs(doc["conditions"]["lr_offset_ms"] - (-100.0 / 96.0)) < 0.03, doc["conditions"]
    finally:
        done()


def _check_only_the_joints_roles_are_built():
    """M2: four tweeter channels (a bank of them) leave the bass joint alone; a role the joint touches still refuses."""
    channels = {"sw": {"role": "sub"}, "w-L": {"role": "woofer"}, "w-R": {"role": "woofer"},
                "tw-L": {"role": "tweeter"}, "tw-R": {"role": "tweeter"}, "tw-L2": {"role": "tweeter"}, "tw-R2": {"role": "tweeter"}}
    joints = joints_of(channels, cls="bass")
    assert [j.name for j in joints] == ["sub-woofer"], joints
    assert stack_names(channels) == ["sub-woofer", "woofer-tweeter"], stack_names(channels)
    top, done = _tmp()
    try:
        roles = {"sw": "sub", "w-L": "woofer", "w-R": "woofer", "tw-L": "tweeter", "tw-R": "tweeter", "tw-L2": "tweeter", "tw-R2": "tweeter"}
        at = {c: 100 for c in roles}
        at["w-L"] = 200
        argv, _, _, _ = _solo_project(top, roles=roles, at=at, points=_FRONT_POINTS)
        rc, _out, err = _run(argv + _TINY)
        assert rc == 0, (rc, err[-400:])
    finally:
        done()


def _check_level_step_and_sub_ver_refused():
    """M4: a `--level-step` band off the search grid refuses in words; so does `--sub-ver` with `--solos`."""
    top, done = _tmp()
    try:
        argv, _, _, solos = _solo_project(top)
        for bad in ("5:15", "10:30", "300:900"):
            rc, _out, err = _run(argv + _TINY + ["--sub-solos", solos, "--level-step", bad])
            assert rc == 3 and "--level-step" in err and "grid" in err, (bad, rc, err[-300:])
        rc, _out, err = _run(argv + _TINY + ["--sub-ver", "3"])
        assert rc == 3 and "--sub-ver" in err, (rc, err[-300:])
    finally:
        done()


def _check_failures_are_refusals():
    """M5: REW down, a bad `--ver`, an ambiguous title, a target file with no line in it, a malformed protective record: each is
    `refusing: <why>`, exit 3, not a traceback."""
    import rew_api as ra
    keep = ra.get_measurements
    failures = []

    def expect(label, argv, said):
        rc, out, err = _run(argv)
        lines = [ln for ln in err.strip().splitlines() if ln.startswith("refusing:")]
        if rc != 3 or out.strip() or not lines or said not in lines[-1]:
            failures.append(f"{label}: rc {rc!r}, err {err[-300:]!r}")

    top, done = _tmp()
    try:
        argv, proj, house, solos = _solo_project(top)
        rew = ["--project", proj, "--house", house, "--rew"] + _TINY

        def down():
            raise ra.RewUnavailable("REW does not answer on its port")
        ra.get_measurements = down
        expect("REW down", rew + ["--ver", "1"], "REW")
        ra.get_measurements = lambda: {"1": {"title": "sw_1 (sw)"}, "2": {"title": "sw_1 (sw)"}}
        expect("an ambiguous title", rew + ["--ver", "1"], "Ambiguous")
        ra.get_measurements = keep
        expect("a bad --ver", rew + ["--ver", "abc"], "--ver")
        no_line = os.path.join(top, "noline.txt")
        with open(no_line, "w", encoding="utf-8") as fh:
            fh.write("not a curve at all\n")
        expect("a target with no line", ["--project", proj, "--house", no_line, "--solos", solos] + _TINY, "no parseable")
        src = {"protectiveHighPass": {"hz": "abc", "family": "LR", "slopeDbPerOct": 24}, "protectiveState": "raw"}
        solos2 = os.path.join(top, "solos2")
        _write_solos(solos2, ("sw", "w-L", "w-R"), points=_FRONT_POINTS, at={"w-L": 200, "w-R": 100}, rew_source=src)
        expect("a malformed protective record", ["--project", proj, "--house", house, "--solos", solos2] + _TINY, "protective")
    finally:
        ra.get_measurements = keep
        done()
    assert not failures, "\n  ".join(["not a one-line refusal:"] + failures)


def _check_rejected_counts_every_drop_once():
    """M6: each row is counted once however many times the shortlist runs, and every drop has a count: with the refine pass on,
    rows out + rows on the list add up to the rows scored. The double walk of the shortlist counted its drops twice and the
    rows past the shortlist not at all."""
    inp = _planted_input(lp_corners=(40, 45, 50, 56, 63, 71, 80, 90), hp_corners=(50, 71, 90, 113))
    hole = inp.target_db.copy()
    band = (inp.freqs >= 45.0) & (inp.freqs <= 62.0)
    hole[band] += 5.0
    inp.target_db = hole
    res = scan_bass(inp)
    rej = res["rejected"]
    assert rej.get("dip", 0) > 0 and res["rows"], rej
    row_drops = rej.get("dip", 0) + rej.get("gain", 0) + rej.get("delay", 0) + rej.get("stage", 0) + rej.get("past_shortlist", 0)
    assert row_drops + len(res["rows"]) == res["grid"]["scored_rows"], (rej, len(res["rows"]), res["grid"]["scored_rows"])


def _check_grid_ceiling_and_row_buffer():
    """M7: the ceiling counts filter pairs times offsets under `--no-lr-offset` (a grid under it held, over it free), and the
    rows held in memory stay bounded however large the grid: the buffer's own limit, the same answer as a large buffer."""
    prof = {"dsp_profile": {"name": "X", "dsp_processing_rate_hz": 96000, "delay": {"max_ms": 20.0, "step_ms": 0.01},
                            "channel_gain": {"range_db": [-30.0, 5.0]},
                            "groups": [{"id": "physical_outputs", "crossover_filters": {
                                "corner_freq_range_hz": [20.0, 20480.0], "corner_freq_step_hz": 1.0,
                                "types": {"LR": {"orders_db_per_oct": [12, 24, 36]}, "BW": {"orders_db_per_oct": [6, 12, 18, 24, 30, 36, 42]},
                                          "BE": {"orders_db_per_oct": [6, 12, 18, 24, 30, 36, 42]}}}}]}}
    top, done = _tmp()
    try:
        proj, house = _fixture(top, profile=prof)
        solos = os.path.join(top, "solos")
        os.makedirs(solos)
        base = ["--project", proj, "--house", house, "--solos", solos, "--lp-bounds", "40:125", "--hp-bounds", "40:125", "--gain", "0:4:2"]
        rc, _out, err = _run(base)
        assert rc == 3 and "no solo" in err, (rc, err[-300:])
        rc, _out, err = _run(base + ["--no-lr-offset"])
        assert rc == 3 and "--allow-large-grid" in err and "offsets" in err, (rc, err[-300:])
    finally:
        done()
    inp = _planted_input()
    global ROW_BUFFER_PER_BAND
    keep = ROW_BUFFER_PER_BAND if "ROW_BUFFER_PER_BAND" in globals() else None
    try:
        ROW_BUFFER_PER_BAND = 16
        small = scan_bass(inp)
        assert small["grid"].get("peak_rows", 10 ** 9) <= 16 * len(_band_edges(inp.joint)) + 40 * len(_band_edges(inp.joint)) \
            and small["grid"]["peak_rows"] > 0, small["grid"].get("peak_rows")
    finally:
        if keep is None:
            del ROW_BUFFER_PER_BAND
        else:
            ROW_BUFFER_PER_BAND = keep
    large = scan_bass(inp)
    a = [(r["lp"], r["hp"], r["sub_rel_db"], r["polarity"], r["delay_ms"]) for r in small["rows"][:5]]
    b = [(r["lp"], r["hp"], r["sub_rel_db"], r["polarity"], r["delay_ms"]) for r in large["rows"][:5]]
    assert a == b, (a, b)


def _check_sub_limit_at_every_point():
    """M8: a sub at one point crossing under 100 Hz at the reference but over it at another point is out; it stands if the sub
    has its points. The note says no drift is applied."""
    lp, hp = ("LR", 36, 71.0), ("LR", 36, 71.0)
    kw = dict(lp=lp, hp=hp, fams=[("LR", 36)], lp_corners=(71,), hp_corners=(71,), leak_on=False, dip_on=False, delay_ms=1.0, n_points=3)
    inp = _planted_input(sub_one_point=True, **kw)
    inp.gains_db = (0.0,)
    # the front is 24 dB down at the last point: the crossing there moves far above the reference's
    inp.upper_l[2] = inp.upper_l[2] * 10.0 ** (-24.0 / 20.0)
    inp.upper_r[2] = inp.upper_r[2] * 10.0 ** (-24.0 / 20.0)
    res = scan_bass(inp)
    assert not res["rows"] and res["rejected"].get("sub_one_point", 0) > 0, (res["rejected"], res["rows"][:1])
    pts = _planted_input(sub_one_point=False, **kw)
    pts.gains_db = (0.0,)
    pts.upper_l[2], pts.upper_r[2] = inp.upper_l[2].copy(), inp.upper_r[2].copy()
    assert scan_bass(pts)["rows"], "with the sub's points the same case stands"
    top, done = _tmp()
    try:
        argv, _, _, _ = _solo_project(top)
        notes = " ".join(_doc(argv + _TINY)["notes"])
        assert "no drift" in notes, notes
    finally:
        done()


def _check_one_point_limit_with_leak_on():
    """T5: the one-point limit under the leak condition as it is on: a pair that passes the leak test (a steep low-pass, a
    crossing over 100 Hz) comes back with the sub's points and is rejected at one point."""
    lp, hp = ("LR", 48, 113.0), ("LR", 36, 113.0)
    kw = dict(lp=lp, hp=hp, fams=[("LR", 48), ("LR", 36)], lp_corners=(113,), hp_corners=(113,), dip_on=False, delay_ms=1.0)
    with_points = scan_bass(_planted_input(sub_one_point=False, **kw))
    assert any(r["crossing_hz"] >= SUB_ONE_POINT_MAX_HZ for r in with_points["rows"]), (with_points["rejected"], len(with_points["rows"]))
    one = scan_bass(_planted_input(sub_one_point=True, **kw))
    assert one["rejected"].get("sub_one_point", 0) > 0, one["rejected"]
    assert all(r["crossing_hz"] < SUB_ONE_POINT_MAX_HZ for r in one["rows"]), [r["crossing_hz"] for r in one["rows"]][:3]


def _check_stage_rule_on_a_coarse_step():
    """T4: the stage rule runs in the scan: a DSP whose delay step cannot hold the L-R rule within 0.10 ms has no rows, each
    counted under `stage`; a step that holds it has them."""
    inp = _planted_input(lr_rule_ms=0.75, **_ONE_PAIR)
    inp.delay_step_ms = 0.5
    res = scan_bass(inp)
    assert not res["rows"] and res["rejected"].get("stage", 0) > 0, (len(res["rows"]), res["rejected"])
    inp = _planted_input(lr_rule_ms=0.75, offset_ms=0.75, **_ONE_PAIR)
    inp.delay_step_ms = 0.05
    assert scan_bass(inp)["rows"], "a step that holds the rule has rows"


def _check_delay_step_and_gain_step():
    """M1: a delay step of 0.25 ms: every row lands on it, on the sub and on each front channel; a gain step of 1.5 dB rejects a
    sub level off it."""
    inp = _planted_input(lr_rule_ms=0.5, offset_ms=0.5, **_ONE_PAIR)
    inp.delay_step_ms = 0.25
    rows = scan_bass(inp)["rows"]
    assert rows, "no rows on the delay step"
    for row in rows:
        for value in row["ta_ms"].values():
            if value is not None:
                assert abs(value / 0.25 - round(value / 0.25)) < 1e-6, row["ta_ms"]
        assert abs(row["delay_ms"] / 0.25 - round(row["delay_ms"] / 0.25)) < 1e-6, row["delay_ms"]
    inp = _planted_input(**_ONE_PAIR)
    inp.gain_step_db = 1.5
    res = scan_bass(inp)
    assert res["rejected"].get("gain", 0) > 0, res["rejected"]
    assert all(abs(r["sub_gain_db"] / 1.5 - round(r["sub_gain_db"] / 1.5)) < 1e-6 for r in res["rows"]), res["rows"][:1]


def _check_delay_ceiling_and_gain_range():
    """T6: a delay past the ceiling is rejected (the L-R offset takes the front over it); a gain out of the channel range too."""
    assert _delay_split(2.9, 1.0, 3.0, False) is None, "2.9 + 1.0 over a 3.0 ms ceiling"
    inp = _planted_input(delay_ms=2.7, lr_rule_ms=1.0, offset_ms=1.0, max_ms=3.0, **_ONE_PAIR)
    res = scan_bass(inp)
    assert res["rejected"].get("delay", 0) > 0, res["rejected"]
    assert all(r["ta_ms"]["upper_left"] <= 3.0 + 1e-9 for r in res["rows"]), res["rows"][:1]
    assert _gain_split(-40.0, (-30.0, 5.0)) is None and _gain_split(8.0, (-30.0, 5.0)) == (5.0, -3.0)
    inp = _planted_input(**_ONE_PAIR)
    inp.gains_db = (-40.0, 2.0)
    res = scan_bass(inp)
    assert res["rejected"].get("gain", 0) > 0, res["rejected"]
    assert res["rows"] and all(r["sub_rel_db"] == 2.0 for r in res["rows"]), res["rows"][:1]


def _check_corners_snap():
    """T6: corners land on the profile's step, once each, inside its range; the refine neighbours too."""
    xo = {"types": {}, "range": [40.0, 200.0], "step": 5.0}
    corners = corner_grid((40.0, 125.0), xo)
    assert all(c % 5 == 0 and 40.0 <= c <= 125.0 for c in corners) and corners == sorted(set(corners)), corners
    for c in _neighbours(("LR", 24, 73.0), (40.0, 125.0), xo):
        assert c[2] % 5 == 0, c


def _check_time_base():
    """T6: `read_window`'s phase is on the absolute time base (`t0_s`, then the sample offset); `lr_rule_ms` reads it too."""
    fs, f = 96000, P.grid(20.0, 400.0, GRID_PPO)
    x = np.zeros(1 << 13)
    x[480] = 1.0
    base = read_window({"ir": x, "sample_rate": fs, "t0_s": 0.0}, f)
    moved = read_window({"ir": x, "sample_rate": fs, "t0_s": 0.002}, f)
    assert np.max(np.abs(moved - base * np.exp(-2j * np.pi * f * 0.002))) < 1e-6, "t0 is the absolute time of sample 0"
    assert np.max(np.abs(base - np.exp(-2j * np.pi * f * (480.0 / fs)))) < 0.02, "a spike at 5 ms is a 5 ms delay"
    y = np.zeros(1 << 13)
    y[2400] = 1.0
    chan = lambda ir, t0: {"info": {"p1": {"ir": {"ir": ir, "sample_rate": fs, "t0_s": t0}}}}
    rule = lr_rule_ms(chan(y, 0.0), chan(y, 0.002), "woofer", positions=("p1",))
    assert abs(rule - 2.0) < 0.1 and rule > 1.0, rule


def _check_level_step_succeeds():
    """T6: two sessions levelled over a control band: the step is applied to the sub (the sub session 6 dB down reads 6 dB up), the
    note says so. And the two sessions without a level step refuse (`_check_refusals_are_one_line` has that)."""
    top, done = _tmp()
    try:
        argv, proj, house, solos = _solo_project(top)
        other = os.path.join(top, "subsession")
        os.makedirs(other)
        # the sub's session: the front's tripods 6 dB quieter than the main session's points, the sub with them
        for stem, level in (("w_L", 0.25), ("w_R", 0.25), ("sw", 0.25)):
            _write_ir(os.path.join(other, f"{stem}.json"), 96, level=level)
        doc = _doc(argv + _TINY + ["--sub-solos", other, "--level-step", "100:300"])
        assert doc["rows"], doc["rejected"]
        said = [n for n in doc["notes"] if "levelled" in n]
        assert said and "+6.0" in said[0], (said, doc["notes"])
    finally:
        done()


def _check_partial_sub_points():
    """T6: a sub with some of its points is told which, and that it needs them all or one."""
    top, done = _tmp()
    try:
        argv, _, _, _ = _solo_project(top, points=dict(_FRONT_POINTS, sw=("p1", "p2")))
        rc, _out, err = _run(argv + _TINY)
        assert rc == 3 and "p3" in err and "at all nine" in err, (rc, err[-300:])
    finally:
        done()


def _check_fs_floor_through_the_options():
    """T6: the high-pass floor (the role's multiple of Fs) binds `filter_options` and the command line: a midrange with Fs 60 Hz
    on no corner under 87 Hz."""
    fams = [("LR", 24)]
    assert [o[2] for o in filter_options(fams, (50.0, 80.0, 90.0), floor_hz=87.0)] == [90.0]
    top, done = _tmp()
    try:
        roles = {"sw": "sub", "m-L": "midrange", "m-R": "midrange"}
        proj, house = _fixture(top, roles=roles)
        pj = _pj.Project(proj)
        data = pj.load()
        for row in data["channels"]:
            row["fs_hz"] = 60.0
        pj.save(data)
        solos = os.path.join(top, "solos")
        _write_solos(solos, tuple(roles), points={"m-L": POSITIONS, "m-R": POSITIONS}, at={"m-L": 200, "m-R": 100})
        doc = _doc(["--project", proj, "--house", house, "--solos", solos, "--lp-bounds", "63:80", "--hp-bounds", "71:125", "--gain", "2:8:2"])
        assert doc["conditions"]["hp_floor_hz"] == 87.0, doc["conditions"]
        assert all(o[2] >= 87.0 for o in doc["grid"]["hp_options"]) and doc["rows"], doc["grid"]["hp_options"][:4]
        assert all(r["hp"][2] >= 87.0 for r in doc["rows"]), doc["rows"][0]["hp"]
    finally:
        done()


def _selftest():
    failures = []
    for check in (_check_joints_from_roles, _check_planted_delay_polarity_corners, _check_family_outside_profile_never_returned,
                  _check_lr_offset_condition, _check_leak_and_dip_conditions, _check_sub_one_point_limit, _check_hp_floor,
                  _check_refusals_are_one_line, _check_protective_refusal_passed_on, _check_cli_end_to_end,
                  _check_band_decides_the_rank, _check_worst_and_median_of_points, _check_space_and_rows_against_a_profile,
                  _check_corners_from_the_top_level, _check_stereo_sub_delays, _check_table_enterable, _check_free_offset_is_said,
                  _check_notes_printed, _check_leak_relative_to_the_crossing, _check_no_leak_and_empty_words,
                  _check_front_lp_moves_the_delay, _check_single_point_needs_the_decision, _check_single_point_rule_on_any_reference,
                  _check_only_the_joints_roles_are_built, _check_level_step_and_sub_ver_refused, _check_failures_are_refusals,
                  _check_rejected_counts_every_drop_once, _check_grid_ceiling_and_row_buffer, _check_sub_limit_at_every_point,
                  _check_one_point_limit_with_leak_on, _check_stage_rule_on_a_coarse_step, _check_delay_step_and_gain_step,
                  _check_delay_ceiling_and_gain_range, _check_corners_snap, _check_time_base, _check_level_step_succeeds,
                  _check_partial_sub_points, _check_fs_floor_through_the_options):
        try:
            check()
        except AssertionError as exc:
            failures.append(f"{check.__name__}: {exc}")
    assert not failures, "\n".join(failures)
    print("selftest OK -- the joints come from the roles; a planted delay, polarity and corner pair are found by a margin, "
          "on either side of the delay; a family outside the profile never comes back; the ±30 degree band ranks, worst and median "
          "of the points apart; the table is what a person keys in, stereo sub included; the L-R rule holds on the DSP's step; leak "
          "is relative to the crossing; every refusal is one line, exit 3; every drop is counted once; nothing is picked")
    return 0


if __name__ == "__main__":
    import console                       # issue #21: a code page must not destroy a result
    console.install()
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    sys.exit(_main())
