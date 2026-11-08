#!/usr/bin/env python3
"""joint_search -- the search behind the joint-by-joint approach (#210): the joints from the roles, the bass and the woofer-mid joint.

One raw capture, then the joints from the bottom up, each joint a search over the filter space that scores and ranks
the variants: a candidate's delay and rank come from the margin, the narrowest band within the delay tolerance of it, not the peak (the
replay of #210). This module holds the engine, the BASS joint (sub low-pass x next role's high-pass x sub level x polarity x
sub/front delay, the front's L-R offset held) and the WOOFER-MID joint: every pair that passes the leak on both sides, scored on all the
points per side, the sides paired under the stage conditions, the bass joint below held by `--fixed` and re-scored (`docs/PLAN-W-12.md`,
T14; above 1 kHz comes next, on the same engine).

A library, not the method (the Arbiter, 2026-11-08): only the DSP's families, ranges and steps and the driver's Fs floor refuse; every other
threshold (±30 degrees, the leak, the dip, the delay tolerance, the shortlist, the bands, the rank, the stage conditions) is a named default
(`Limits`), changed by a flag, and a changed limit is shown with the same grid on the defaults beside it.

The joints come from `xover_wishes.ROLE_ORDER` over the channels present, each adjacent pair one joint: 3-way + sub, 2-way +
sub, a front sub are the same code. Everything searched comes from the project: the families (`dsp_math.options_for`),
corners (the profile's range and step), gain and delay limits, Fs. The grid is the joint's, not the hardware's: corner bounds
from a role table, 1/6-oct steps. Its size is printed before the run and over a ceiling it refuses without a flag.

    python3 rew_tool/joint_search.py --project DIR --house FILE --solos DIR [--joint bass|woofer-midrange] [--json] [--out DIR]
                                     [--front-lp FAM ORD HZ] [--no-leak] [--no-dip] [--no-lr-offset]
                                     [--fixed FILE[@N]] [--move upper|lower] [--align] (the flags of each limit: --help)
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
from dataclasses import dataclass, field, replace as _dc_replace

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
#: The sub's leak above the joint, sub minus front: -24 dB at 100 Hz and -30 dB over 125-200 Hz, the limits the method was validated
#: with (`swws_search2.py:6,44`). Those frequencies belong to that run's crossing near 65 Hz: a crossing at or below this is judged
#: exactly as the run was, a higher one has them moved up by crossing / `LEAK_ANCHOR_CROSSING_HZ`.
LEAK_ANCHOR_CROSSING_HZ = 65.0
LEAK_NEAR_HZ = 100.0
LEAK_NEAR_DB = -24.0
LEAK_FAR_HZ = (125.0, 200.0)
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
_NO_WORDS = ("no", "nope", "not", "don't", "don’t", "ні", "нi", "не", "нет")
#: The grid: 1/6-oct corners over the joint's bounds, then +-1/12 oct around the shortlist (PLAN-W-12, the grid).
CORNER_STEP_OCT = 1.0 / 6.0
CORNER_REFINE_OCT = 1.0 / 12.0
#: About twice the design's ~29,000 filter pairs a joint: over it the run refuses without `--allow-large-grid`. The count is
#: filter pairs times L-R offsets (`--no-lr-offset` is 25 offsets): the combinations the scan really walks.
GRID_CEILING_PAIRS = 60000
#: Rows held at once per crossing band while the grid is walked. The reference-point scan yields many rows per pair; only the
#: best per band can reach the shortlist, so anything past this is settled and the rest dropped, counted (`past_shortlist`).
#: The memory of a run stays one filter-response bank (about 11 kB per filter option: 24 bytes a point on the bass grid) plus this,
#: whatever the grid's size.
ROW_BUFFER_PER_BAND = 2000
#: Delay of the front against the sub: coarse over +-`delay.max_ms`, then fine around the best (`swws_xo.py:194,218`).
DELAY_COARSE_STEP_MS = 0.2
DELAY_FINE_SPAN_MS = 1.0
DELAY_FINE_STEP_MS = 0.05
#: A head moving about 3.4 cm (0.10 ms in air). The worst-of-nine band can peak within one delay step (#210, the replay: 0.58 / 0.98 /
#: 0.57 oct at 10.65 / 10.70 / 10.75 ms), and a peak that narrow does not survive a head moving a centimetre. A delay's margin is the
#: narrowest worst-of-nine band within this either side of it: the candidate takes the delay with the best margin and ranks on it.
DELAY_TOLERANCE_MS = 0.10
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
#: The joints above the bass: an octave out each driver at least this far under the other, both ways (`wm_search.py:107`).
LEAK_OCTAVE_DB = -24.0
#: L and R acoustic crossings within this: `stage_lock.py:217`.
LR_CROSSING_OCT = 1.0 / 3.0
#: The bass joint may lose no more than this, worst and median, under a candidate's low-pass: the run's criterion, `wm_search.py:19`.
BASS_RESCORE_DROP_OCT = 0.1
#: The sub's delay searched to bring a fallen bass joint back: every step of the delay range (`wm_search.py:194`).
BASS_RECOVER_STEP_MS = 0.1
#: Candidates per crossing band and side carried to the pairing of the sides (`stage_sym.py:88-96`, the design's 200).
SHORTLIST_COUPLED_PER_BAND = 200
#: Finished rows per crossing band of a coupled joint: dips, the ceiling and the bass re-score walk the candidates down to this.
ROWS_PER_BAND = 40
#: The upper driver's delay against the lower, searched around their raw arrival difference: `wm_search.py:42`.
SHIFT_SPAN_MS = 4.0
SHIFT_STEP_MS = 0.05
#: Filter pairs handled at once in a coupled scan (float32 curves, one family pair at a time, so the memory stays this many pairs).
COUPLED_CHUNK_PAIRS = 32
#: A lower driver ringing this many times longer than the upper is the case the decay report names (#210, `stage_v6.py`).
RING_RATIO = 1.5
#: The flatten of `--align`: gain up, cuts and their depth (`wm_flat.py:9`).
ALIGN_GAIN_MAX_DB = 6.0
ALIGN_CUTS = 4
ALIGN_CUT_MAX_DB = 6.0
#: The band each role is flattened over and the band whose level it keeps, overridable by `--align-band` (PLAN-W-12).
ALIGN_BANDS = {"sub": ((25.0, 130.0), (25.0, 130.0)), "woofer": ((100.0, 560.0), (100.0, 200.0)),
               "midrange": ((200.0, 1250.0), (700.0, 1500.0)), "midrange-upper": ((1250.0, 5000.0), (700.0, 1500.0)),
               "tweeter": ((1600.0, 10000.0), (5000.0, 10000.0))}
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
    band_width_oct: float = BAND_WIDTH_OCT
    #: The joints above the bass: the band the ±30 degree run walks, the band of the rms to the target, the leak's floor and ceiling.
    width_band: tuple = None
    rms_band: tuple = None
    leak_floor_hz: float = None
    leak_ceil_hz: float = None
    ring_band: tuple = None


@dataclass(frozen=True)
class Limits:
    """Every threshold of the method, a default until a flag changes it (the Arbiter, 2026-11-08: "a library, not the method"). The
    module constants are the defaults; hard limits (the DSP's families, ranges and steps, the Fs floors) are not here."""
    phase_window_deg: float = PHASE_WINDOW_DEG
    leak_near_db: float = LEAK_NEAR_DB
    leak_far_db: float = LEAK_FAR_DB
    leak_octave_db: float = LEAK_OCTAVE_DB
    dip_limit_db: float = DIP_LIMIT_DB
    delay_tolerance_ms: float = DELAY_TOLERANCE_MS
    lr_tolerance_ms: float = LR_OFFSET_TOLERANCE_MS
    lr_crossing_oct: float = LR_CROSSING_OCT
    shortlist: int = 0
    band_width_oct: float = 0.0
    corner_step_oct: float = CORNER_STEP_OCT
    rank: str = "margin"
    sub_one_point_max_hz: float = SUB_ONE_POINT_MAX_HZ
    shift_span_ms: float = SHIFT_SPAN_MS
    bass_drop_oct: float = BASS_RESCORE_DROP_OCT
    ring_ratio: float = RING_RATIO
    align_gain_max_db: float = ALIGN_GAIN_MAX_DB
    align_cuts: int = ALIGN_CUTS
    align_cut_max_db: float = ALIGN_CUT_MAX_DB
    crossing_window: tuple = None
    dip_band: tuple = None


#: Bounds per joint (PLAN-W-12: "bass 40-125 Hz"), overridable by `--lp-bounds` / `--hp-bounds`; the crossing window, the dip
#: band and its offset-fit band are `swws_xo.py:102` and `swws_search2.py:21-22`.
JOINT_CLASSES = {
    # the grid reaches past the far leak band of a crossing at 200 Hz: 200/65 x 125-200 Hz is 385-615 Hz
    "bass": JointClass("bass", (40.0, 125.0), (40.0, 125.0), (35.0, 200.0), (20.0, 630.0), (45.0, 110.0), (100.0, 250.0)),
    # the woofer-mid numbers are the run's (`wm_search.py:16,34,90,105,117,120`, `wm_flat.py:32`): the leak's floor 90 Hz and ceiling 1.6 kHz;
    # the grid starts at 20 Hz because the bass joint below is re-scored on it
    "woofer-midrange": JointClass("woofer-midrange", (150.0, 600.0), (150.0, 600.0), (150.0, 800.0), (20.0, 1600.0), (180.0, 600.0),
                                  (700.0, 1500.0), band_width_oct=0.5, width_band=(100.0, 1600.0), rms_band=(150.0, 600.0),
                                  leak_floor_hz=90.0, leak_ceil_hz=1600.0, ring_band=(150.0, 630.0)),
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
def check_stage(*, rule_ms=None, lr_delay_ms=None, tolerance_ms=LR_OFFSET_TOLERANCE_MS):
    """What a candidate breaks of the L-R rule, as a list of words (empty = holds): (delay L - delay R) must equal the signed
    rule -(raw arrival L - raw arrival R) within `LR_OFFSET_TOLERANCE_MS`. Asked for every real L/R pair of a row, on the delays
    the DSP takes (`scan_bass`'s `accept`), so a delay step too coarse to hold the rule shows here. A bass joint gives one polarity
    and one filter to a whole side, so those two conditions have nothing to check until the joints above it are built."""
    why = []
    if rule_ms is not None and lr_delay_ms is not None \
            and abs(float(lr_delay_ms) - float(rule_ms)) > tolerance_ms + 1e-9:
        why.append(f"delay L-R {float(lr_delay_ms):+.2f} ms breaks the rule {float(rule_ms):+.2f} "
                   f"+-{tolerance_ms:g} ms")
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
    th: Limits = Limits()
    #: The upper role's low-pass in the model (`--front-lp`), kept on each row so a `--fixed` row re-scores against its own baseline.
    front_lp: tuple = None


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


def _band_edges(cls, th=None):
    """The crossing-band set: the crossing window in steps of the band width, `--band-width` over the joint's own."""
    lo, hi = cls.crossing_window
    width = (th.band_width_oct if th is not None and th.band_width_oct else 0.0) or cls.band_width_oct
    n = max(1, int(math.ceil(math.log2(hi / lo) / width)))
    return [lo * 2.0 ** (k * width) for k in range(n)] + [hi]


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


def _leak_bins(f, crossing_hz):
    """The grid points of the leak limit for a crossing: (near index, far band's first and last index). At or below
    `LEAK_ANCHOR_CROSSING_HZ` the run's own frequencies, above it moved up with the crossing; a far band past the top of the grid
    reads the grid's last point, as far as it reaches."""
    scale = max(1.0, float(crossing_hz) / LEAK_ANCHOR_CROSSING_HZ)
    near = int(np.argmin(np.abs(f - LEAK_NEAR_HZ * scale)))
    last = len(f) - 1
    lo = min(int(np.searchsorted(f, LEAK_FAR_HZ[0] * scale, side="left")), last)
    hi = max(int(np.searchsorted(f, LEAK_FAR_HZ[1] * scale, side="right")) - 1, lo)
    return near, lo, hi


def _delay_margins(probes, worst, at, tolerance_ms=DELAY_TOLERANCE_MS):
    """Per fine delay (`at`: its index in `probes`, ascending ms): the narrowest worst-of-points band within `tolerance_ms`
    of it (`--delay-tolerance`). A candidate's band at one delay only is no band to a head that moves."""
    out = np.empty(len(at))
    for j, i in enumerate(at):
        out[j] = worst[np.abs(probes - probes[i]) <= tolerance_ms + 1e-9].min()
    return out


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
    cw = np.flatnonzero((f >= cls.crossing_window[0]) & (f <= cls.crossing_window[1]))
    cw_mask, m0 = np.zeros(len(f), bool), int(cw[0])
    cw_mask[cw] = True
    th = inp.th
    edges = _band_edges(cls, th)
    keep_n = _shortlist(th, SHORTLIST_PER_BAND)
    rejected = {"leak": 0, "no_crossing": 0, "sub_one_point": 0, "phase": 0, "gain": 0, "delay": 0, "stage": 0, "dip": 0,
                "past_shortlist": 0}
    label_at, leak_at = {}, {}
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
            # the leak, at each gain's own crossing (`LEAK_*`): the same two levels whether the test is on or off
            near_db, far_db = np.zeros(len(gains)), np.zeros(len(gains))
            for c in np.unique(cross[g_cross]):
                if int(c) not in leak_at:
                    leak_at[int(c)] = _leak_bins(f, float(f[c]))
                i_near, far_lo, far_hi = leak_at[int(c)]
                near = float(gap[i_near])
                far = float(gap[far_lo:far_hi + 1].max())
                at_c = cross == c
                near_db[at_c], far_db[at_c] = near + gains[at_c], far + gains[at_c]
            if inp.leak_on:
                leak_ok = (near_db <= th.leak_near_db) & (far_db <= th.leak_far_db)
                rejected["leak"] += int((g_cross & ~leak_ok).sum())
                g_cross = g_cross & leak_ok
                if not g_cross.any():
                    continue
            if inp.sub_one_point:
                high = f[cross] >= th.sub_one_point_max_hz
                rejected["sub_one_point"] += int((g_cross & high).sum())
                g_cross = g_cross & ~high
                if not g_cross.any():
                    continue
            base = (sub_ph0 + lp_ph) - (front_ph + hp_ph)
            x = base[None, :] + rot_deg
            a = np.abs(((x + 180.0) % 360.0) - 180.0)
            for pol, ok in (("NORM", a <= th.phase_window_deg), ("INV", a >= 180.0 - th.phase_window_deg)):
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
                and check_stage(rule_ms=inp.lr_rule_ms, lr_delay_ms=tas["upper_left"] - tas["upper_right"], tolerance_ms=th.lr_tolerance_ms):
            rejected["stage"] += 1
            return None
        if inp.lower_rule_ms is not None \
                and check_stage(rule_ms=inp.lower_rule_ms, lr_delay_ms=tas["sub_left"] - tas["sub_right"], tolerance_ms=th.lr_tolerance_ms):
            rejected["stage"] += 1
            return None
        if inp.dip_on and inp.target_db is not None:
            s = (-1.0 if pol == "INV" else 1.0) * 10.0 ** (g / 20.0) * inp.ref_lower * lp_bank.get(lp)[0]
            w = _front_sum(inp.ref_l, inp.ref_r, f, offsets[oi]) * hp_bank.get(hp)[0] \
                * np.exp(-2j * np.pi * f * d * 1e-3)
            if _dip_db(f, s, w, inp.target_db, cls) < th.dip_limit_db:
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
        if len(band["kept"]) >= keep_n and row[0] <= band["kept"][-1][0]:
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
            if len(kept) >= keep_n and row[0] <= kept[-1][0]:
                rejected["past_shortlist"] += len(band["wait"]) - i
                break
            if accept(row) is None:
                continue
            kept.append(row)
            kept.sort(key=lambda r: -r[0])
            if len(kept) > keep_n:
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
    rows.sort(key=lambda r: _row_key(r, th.rank), reverse=True)
    bands = {}
    for r in rows:
        bands.setdefault(r["band"], []).append(r)
    return {"rows": rows, "bands": bands, "rejected": rejected,
            "grid": {"pairs": n_pairs, "lp_options": [list(o) for o in inp.lp_options],
                     "hp_options": [list(o) for o in inp.hp_options], "lr_offsets": len(offsets),
                     "gains": len(gains), "delays": len(delays), "scored_rows": stats["rows"], "peak_rows": peak[0]}}


def _shortlist(th, default):
    """The shortlist's size: `--shortlist` over the joint's own."""
    return int(th.shortlist) if th.shortlist else default


def _row_key(r, rank="margin"):
    """The ranking: the margin (the worst point's band that survives a head moving), the worst point's band at the row's delay, the
    median's, the summation loss; among ties the sum nearest the target. `--rank worst|median|loss` puts that field first."""
    margin, worst, median = r["margin_oct"], r["width_worst_oct"], r["width_median_oct"]
    loss = -99.0 if r["loss_median_db"] is None else r["loss_median_db"]
    dip = r.get("dip_median_db", r.get("dip_db"))
    dip = -99.0 if dip is None else -abs(dip)
    if rank == "worst":
        return (worst, margin, median, loss, dip)
    if rank == "median":
        return (median, worst, margin, loss, dip)
    if rank == "loss":
        return (loss, margin, worst, median, dip)
    return (margin, worst, median, loss, dip)


def _public(row):
    """The row as a reader gets it: numbers rounded for reading (the ranking used the unrounded values)."""
    out = dict(row)
    for key, n in (("margin_oct", 2), ("width_worst_oct", 2), ("width_median_oct", 2), ("loss_median_db", 2), ("dip_median_db", 2),
                   ("leak_near_db", 1), ("leak_far_db", 1), ("crossing_hz", 1)):
        out[key] = _round(out[key], n)
    return out


def _round(v, n=2):
    return None if v is None else round(float(v), n)


def _score_points(inp, row, label, offsets, lp_bank, hp_bank, step, cls, m0, cw_mask, single_upper, rejected):
    """Every point, the delay refined there: the margin of the worst point's ±30 degree band over the delay tolerance
    (`_delay_margins`) picks the delay, then that delay's worst and median, then the summation loss. A row that falls here (past a limit at its final delay, the one-point limit at another point's crossing) is counted in `rejected`."""
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
    # the margin looks at a head moving, whatever delays the DSP can take: probes at the fine step around each settable delay, up
    # to the tolerance either side, a probe past the delay ceiling included (it is an arrival, not a setting)
    th = inp.th
    n_tol = int(round(th.delay_tolerance_ms / DELAY_FINE_STEP_MS))
    fine_at = np.round(fine, 6)
    probes = np.unique(np.round((fine_at[None, :] + np.arange(-n_tol, n_tol + 1)[:, None] * DELAY_FINE_STEP_MS).ravel(), 6))
    at = np.searchsorted(probes, fine_at)
    rot = 360.0 * f[None, :] * probes[:, None] * 1e-3
    widths = np.zeros((len(inp.points), len(probes)))
    crossings = [None] * len(inp.points)
    for p in range(len(inp.points)):
        c = _crossing(gap[p], cw_mask, m0)
        crossings[p] = c
        if c is None:
            continue
        if inp.sub_one_point and f[c] >= th.sub_one_point_max_hz:     # one curve for the sub holds under 100 Hz, at every point
            rejected["sub_one_point"] += 1
            return None
        a = np.abs(((base[p][None, :] + rot + 180.0) % 360.0) - 180.0)
        widths[p] = _widths(a <= th.phase_window_deg, c, step)
    worst = widths.min(0)
    median = np.median(widths, axis=0)
    margins = _delay_margins(probes, worst, at, th.delay_tolerance_ms)
    # the margin first, then that delay's worst, then its median; the plateau's centre on a tie
    top = np.flatnonzero(margins >= margins.max() - 1e-9)
    top = top[worst[at[top]] >= worst[at[top]].max() - 1e-9]
    k = int(top[_plateau_centre(median[at[top]])])
    i_best = int(at[k])
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
            "crossing_hz": float(np.median(fxs)), "margin_oct": float(margins[k]), "width_worst_oct": float(worst[i_best]),
            "width_median_oct": float(median[i_best]),
            "loss_median_db": float(np.median(losses)) if losses else None,
            "dip_median_db": float(np.median(dips)) if dips else None, "leak_near_db": float(leak_near),
            "leak_far_db": float(leak_far), "fs_margin": fs_margin, "band": label, "marks": list(inp.marks),
            "front_lp": list(inp.front_lp) if inp.front_lp else None}


# ---------------------------------------------------------------- the joints above the bass, one scan per L/R pair of sides
@dataclass
class CoupledSide:
    """One side of a coupled joint: `lower` and `upper` over (points, grid), each channel's own chain except the two filters searched."""
    name: str
    lower_code: str
    upper_code: str
    lower: np.ndarray
    upper: np.ndarray
    arrival_ms: float = 0.0


@dataclass
class BassHold:
    """The bass joint below, held from its row: the sub (its gain and low-pass in, polarity and delay apart), each woofer's chain without
    the low-pass the search brings. Re-scored with each candidate's low-pass (`_bass_judge`)."""
    freqs: np.ndarray
    sub: np.ndarray
    woofers: dict
    sub_delay_ms: float
    sub_polarity: str
    base_delays: dict
    base_lps: dict
    max_ms: float
    delay_step_ms: float = None
    #: {sub code: delay in the row}: how the row's table is rewritten when the sub moves (a stereo sub moves by the same step).
    sub_codes: dict = field(default_factory=dict)
    cls: JointClass = JOINT_CLASSES["bass"]
    lp_bank: dict = field(default_factory=dict)
    cache: dict = field(default_factory=dict)

    def __post_init__(self):
        self.lp_bank = _Bank(np.asarray(self.freqs, float), "lp")

    def baseline(self, th):
        key = (th.phase_window_deg, th.delay_tolerance_ms)
        if key not in self.cache:
            self.cache[key] = _bass_score(self, self.base_lps, self.base_delays, -1.0 if self.sub_polarity == "INV" else 1.0, self.sub_delay_ms, th)
        return self.cache[key]


@dataclass
class CoupledInput:
    freqs: np.ndarray
    points: list
    sides: list
    lp_options: list
    hp_options: list
    target_db: np.ndarray
    max_ms: float
    th: Limits = Limits()
    #: The upper role's rule: (delay L - delay R) = this within the tolerance; None for a single side.
    lr_rule_ms: float = None
    free_lr: bool = False
    same_polarity: bool = True
    same_family: bool = True
    per_side_corners: bool = False
    leak_on: bool = True
    dip_on: bool = True
    move: str = "upper"
    held_lower: dict = None
    held_upper: dict = None
    upper_polarity: dict = None
    above: dict = None
    bass: BassHold = None
    decay: dict = None
    delay_step_ms: float = None
    #: The lower role's L-R rule when nothing holds it: the woofers' raw offset, `move upper`'s starting point.
    lower_rule_ms: float = 0.0
    joint: JointClass = JOINT_CLASSES["woofer-midrange"]
    fs_upper_hz: float = None
    hp_floor_hz: float = 0.0
    marks: tuple = ()
    notes: list = field(default_factory=list)


def _third_oct(f):
    """The 1/3-octave averaging of a power curve, a row per grid point (`wm_search.py:44-46`)."""
    k = 2.0 ** (1.0 / 6.0)
    kernel = np.zeros((len(f), len(f)), np.float32)
    for i, x in enumerate(f):
        kernel[i, (f >= x / k) & (f <= x * k)] = 1.0
    return kernel / kernel.sum(1, keepdims=True)


def _power_db(p):
    return 10.0 * np.log10(np.maximum(p, 1e-30))


def _shift_grid(inp):
    """The upper's delay against the lower, the raw arrival differences' span and `shift_span_ms` around them, on the DSP's step."""
    arrivals = [float(s.arrival_ms) for s in inp.sides]
    lo = min(arrivals) - inp.th.shift_span_ms
    hi = max(arrivals) + inp.th.shift_span_ms
    n = int(math.floor((hi - lo) / SHIFT_STEP_MS + 1e-9))
    raw = lo + np.arange(n + 1) * SHIFT_STEP_MS
    if inp.delay_step_ms:
        raw = np.unique(np.round(raw / inp.delay_step_ms) * inp.delay_step_ms)
    return np.round(raw, 6)


def _coupled_crossing(dd, win, f, near):
    """The falling zero of the level difference inside the window nearest the corners' geometric mean: (index, Hz) or None."""
    cross = np.flatnonzero(np.diff(np.sign(dd[win])) < 0)
    if not cross.size:
        return None
    c = int(win[cross[np.argmin(np.abs(np.log(f[win[cross]] / near)))]])
    return c, float(f[c])


def _leak_pairs(inp, side, lp_bank, hp_bank, kernel, rejected):
    """Every filter pair with a crossing, and on one side the leak test, both ways, on the points' 1/3-octave power mean (`wm_search.py:87-108`).
    Returns `{(lp, hp): (crossing index, Hz, up dB, down dB)}`."""
    f, cls, th = np.asarray(inp.freqs, float), inp.joint, inp.th
    power_lo, power_up = np.mean(np.abs(side.lower) ** 2, 0), np.mean(np.abs(side.upper) ** 2, 0)
    lows = {tuple(o): _power_db(kernel @ (power_lo * np.abs(lp_bank.get(o)[0]) ** 2)).astype(np.float32) for o in inp.lp_options}
    highs = {tuple(o): _power_db(kernel @ (power_up * np.abs(hp_bank.get(o)[0]) ** 2)).astype(np.float32) for o in inp.hp_options}
    win = np.flatnonzero((f >= cls.crossing_window[0]) & (f <= cls.crossing_window[1]))
    third = 2.0 ** (1.0 / 6.0)
    out = {}
    for lp, lw in lows.items():
        for hp, lm in highs.items():
            found = _coupled_crossing(lw - lm, win, f, math.sqrt(lp[2] * hp[2]))
            if found is None:
                rejected["no_crossing"] += 1
                continue
            c, fx = found
            up = (f >= 2.0 * fx) & (f <= min(4.0 * fx, cls.leak_ceil_hz))
            dn = (f >= min(max(fx / 4.0, cls.leak_floor_hz), fx / 2.0 / third)) & (f <= fx / 2.0)
            up_db = float((lw - lm)[up].max()) if up.any() else None
            dn_db = float((lm - lw)[dn].max()) if dn.any() else None
            if inp.leak_on and ((up_db is not None and up_db > th.leak_octave_db) or (dn_db is not None and dn_db > th.leak_octave_db)):
                rejected["leak"] += 1
                continue
            out[(lp, hp)] = (c, fx, up_db, dn_db)
    return out


def _tol_windows(shifts, tolerance_ms):
    """Per shift, the index range of the shifts within the delay tolerance: `(lo, hi)`, the same for every candidate."""
    lo = np.searchsorted(shifts, shifts - tolerance_ms - 1e-9, side="left")
    hi = np.searchsorted(shifts, shifts + tolerance_ms + 1e-9, side="right")
    return lo, hi


def _rank_key(margin, worst, median, rank):
    """One number per shift for pairing: the rank's field first, then the others (a `loss` rank pairs on the margin, the loss comes last)."""
    if rank == "worst":
        return worst + 1e-3 * margin + 1e-6 * median
    if rank == "median":
        return median + 1e-3 * worst + 1e-6 * margin
    return margin + 1e-3 * worst + 1e-6 * median


def _side_curves(inp, side, pairs, shifts, lp_bank, hp_bank, step, rejected):
    """The delay curves of one side: every pair that passed the leak on both sides, on all its points, both polarities, chunked by family pair;
    `pairs` is `{(lp, hp): (c, fx, up, down)}` (`stage_lock.py:157-159`, `stage_sym.py:88-96`). Returns the candidates, top per crossing band."""
    f, th = np.asarray(inp.freqs, float), inp.th
    cls = inp.joint
    mask = (f >= cls.width_band[0]) & (f <= cls.width_band[1])
    off = int(np.flatnonzero(mask)[0])
    fb = f[mask]
    rot = (360.0 * fb[None, :] * shifts[:, None] * 1e-3).astype(np.float32)
    lo_ph, up_ph = (np.degrees(np.angle(side.lower))[:, mask].astype(np.float32),
                    np.degrees(np.angle(side.upper))[:, mask].astype(np.float32))
    windows = _tol_windows(shifts, th.delay_tolerance_ms)
    edges = _band_edges(cls, th)
    groups = {}
    for (lp, hp), info in pairs.items():
        groups.setdefault((lp[:2], hp[:2]), []).append((lp, hp, info))
    keep_n = _shortlist(th, SHORTLIST_COUPLED_PER_BAND)
    window_deg = th.phase_window_deg
    kept = {}
    n_points = side.lower.shape[0]
    for key in sorted(groups):
        items = groups[key]
        for first in range(0, len(items), COUPLED_CHUNK_PAIRS):
            chunk = items[first:first + COUPLED_CHUNK_PAIRS]
            cs = np.array([it[2][0] - off for it in chunk])
            filt = np.array([lp_bank.get(it[0])[2][mask] - hp_bank.get(it[1])[2][mask] for it in chunk], np.float32)
            widths = {"NORM": np.zeros((len(chunk), n_points, len(shifts)), np.float32),
                      "INV": np.zeros((len(chunk), n_points, len(shifts)), np.float32)}
            for p in range(n_points):
                x = (filt[:, None, :] + (lo_ph[p] - up_ph[p])[None, None, :] + rot[None, :, :])
                a = np.abs(((x + 180.0) % 360.0) - 180.0)
                near_in = a <= window_deg
                near_out = a >= 180.0 - window_deg
                for c in np.unique(cs):
                    sel = np.flatnonzero(cs == c)
                    for pol, ok in (("NORM", near_in), ("INV", near_out)):
                        block = ok[sel].reshape(-1, ok.shape[2])
                        widths[pol][sel, p, :] = _widths(block, int(c), step).reshape(len(sel), len(shifts))
            for pol, w in widths.items():
                worst = w.min(1)
                median = np.median(w, axis=1).astype(np.float32)
                margin = np.empty_like(worst)
                for i in range(len(shifts)):
                    margin[:, i] = worst[:, windows[0][i]:windows[1][i]].min(1)
                keys = _rank_key(margin, worst, median, th.rank).astype(np.float64)
                for n, (lp, hp, info) in enumerate(chunk):
                    label = _band_label(edges, info[1])
                    if label is None:
                        rejected["no_crossing"] += 1
                        continue
                    if worst[n].max() <= 0.0:
                        rejected["phase"] += 1
                        continue
                    kept.setdefault(label, []).append(
                        {"lp": lp, "hp": hp, "pol": pol, "c": info[0], "fx": info[1], "up_db": info[2], "dn_db": info[3],
                         "worst": worst[n].copy(), "median": median[n].copy(), "margin": margin[n].copy(), "key": keys[n].copy()})
                for label, rows in kept.items():
                    if len(rows) > 2 * keep_n:
                        rows.sort(key=lambda r: -r["key"].max())
                        rejected["past_shortlist"] += len(rows) - keep_n
                        del rows[keep_n:]
    out = []
    for label, rows in kept.items():
        rows.sort(key=lambda r: -r["key"].max())
        if len(rows) > keep_n:
            rejected["past_shortlist"] += len(rows) - keep_n
        out += rows[:keep_n]
    return out


def _pair_group_key(cand, inp):
    """What the stage conditions require to match L to R: family and order, the corners (unless per side), the polarity."""
    key = []
    if inp.same_family:
        key += [cand["lp"][:2], cand["hp"][:2]]
    if not inp.per_side_corners:
        key += [cand["lp"][2], cand["hp"][2]]
    if inp.same_polarity:
        key.append(cand["pol"])
    return tuple(key)


def _lower_offset(inp):
    """(lower L delay - lower R delay) as a candidate starts from: held by a row, or the lower role's raw rule."""
    sides = inp.sides
    if inp.held_lower:
        return float(inp.held_lower[sides[0].lower_code]) - float(inp.held_lower[sides[1].lower_code])
    return float(inp.lower_rule_ms or 0.0)


def _pair_sides(inp, rows_by_side, shifts, rejected):
    """The L/R pairs under the stage conditions, each with its pair of delays: the L-R rule on the upper delays couples them when the group
    above moves (`stage_lock.wm_pairs`); with the lower group moving each side aligns alone. Returns `[(key, a, b, i, j)]`, best first."""
    th = inp.th
    if len(rows_by_side) == 1:
        pairs = []
        for a in rows_by_side[0]:
            i = int(np.argmax(a["key"]))
            pairs.append((float(a["key"][i]), a, None, i, None))
        pairs.sort(key=lambda p: -p[0])
        return pairs
    A, B = rows_by_side
    if not A or not B:
        return []
    groups = {}
    for j, b in enumerate(B):
        groups.setdefault(_pair_group_key(b, inp), []).append(j)
    b_key = np.array([b["key"] for b in B], np.float64)
    b_peak = b_key.max(1)
    b_fx = np.array([b["fx"] for b in B])
    constrained = inp.lr_rule_ms is not None and not inp.free_lr and inp.move == "upper"
    lo, hi = None, None
    if constrained:
        offset = float(inp.lr_rule_ms) - _lower_offset(inp)
        tol = th.lr_tolerance_ms
        lo = np.searchsorted(shifts, shifts - offset - tol - 1e-9, side="left")
        hi = np.searchsorted(shifts, shifts - offset + tol + 1e-9, side="right")
    top_n = max(200, 3 * _shortlist(th, SHORTLIST_COUPLED_PER_BAND))
    pairs = []
    for a in A:
        idx = groups.get(_pair_group_key(a, inp))
        if not idx:
            continue
        idx = np.array(idx)
        near = np.abs(np.log2(a["fx"] / b_fx[idx])) <= th.lr_crossing_oct + 1e-9
        rejected["lr_crossing"] += int((~near).sum())
        idx = idx[near]
        if not idx.size:
            continue
        if constrained:
            sub = b_key[idx]
            best_j = np.full(sub.shape, -np.inf)
            for i in range(len(shifts)):
                if hi[i] > lo[i]:
                    best_j[:, i] = sub[:, lo[i]:hi[i]].max(1)
            combo = np.minimum(a["key"][None, :], best_j)
            i_star = combo.argmax(1)
            vals = combo[np.arange(len(idx)), i_star]
            ok = np.isfinite(vals)
            rejected["stage"] += int((~ok).sum())
            order = np.argsort(-vals)[:top_n]
            for n in order:
                if not ok[n]:
                    continue
                i = int(i_star[n])
                j = int(lo[i] + np.argmax(sub[n, lo[i]:hi[i]]))
                pairs.append((float(vals[n]), a, B[int(idx[n])], i, j))
        else:
            i = int(np.argmax(a["key"]))
            vals = np.minimum(a["key"][i], b_peak[idx])
            for n in np.argsort(-vals)[:top_n]:
                j = int(np.argmax(b_key[idx[n]]))
                pairs.append((float(vals[n]), a, B[int(idx[n])], i, j))
    pairs.sort(key=lambda p: -p[0])
    return pairs


def _place_coupled(inp, shifts, polarities):
    """Each channel's delay for one candidate, by which group moves, and the group above carried along with the mid: `(placed, None)` or
    `(None, why)`, why being "delay" (outside 0...max_ms) or "stage" (the L-R rule off the DSP's step)."""
    step = inp.delay_step_ms
    sides = inp.sides
    two = len(sides) == 2
    max_ms = float(inp.max_ms)
    delays, floating = {}, False
    if inp.move == "upper":
        if inp.held_lower:
            for side in sides:
                base = float(inp.held_lower[side.lower_code])
                delays[side.lower_code] = base
                delays[side.upper_code] = base + shifts[side.name]
        else:
            floating = True
            lower_off = _snap_ms(inp.lower_rule_ms or 0.0, step) if two else 0.0
            for k, side in enumerate(sides):
                base = lower_off if (two and k == 0) else 0.0
                delays[side.lower_code] = base
                delays[side.upper_code] = base + shifts[side.name]
    else:  # the woofer moves: the upper group stands
        if inp.held_upper:
            for side in sides:
                base = float(inp.held_upper[side.upper_code])
                delays[side.upper_code] = base
                delays[side.lower_code] = base - shifts[side.name]
        elif inp.held_lower:
            upper_off = _snap_ms(inp.lr_rule_ms or 0.0, step) if two else 0.0
            sum_side = sum(float(inp.held_lower[s.lower_code]) + shifts[s.name] for s in sides) - upper_off * (1 if two else 0)
            base = _snap_ms(sum_side / len(sides), step)
            for k, side in enumerate(sides):
                value = base + (upper_off if (two and k == 0) else 0.0)
                delays[side.upper_code] = value
                delays[side.lower_code] = value - shifts[side.name]
        else:
            floating = True
            upper_off = _snap_ms(inp.lr_rule_ms or 0.0, step) if two else 0.0
            for k, side in enumerate(sides):
                value = upper_off if (two and k == 0) else 0.0
                delays[side.upper_code] = value
                delays[side.lower_code] = value - shifts[side.name]
    above_out, moved = {}, {}
    for code, spec in (inp.above or {}).items():
        mid = spec["follows"]
        held = (inp.held_upper or {}).get(mid, delays[mid])
        delta = delays[mid] - float(held)
        moved[mid] = delta
        flip = (inp.upper_polarity or {}).get(mid, polarities[_side_of_upper(inp, mid)]) != polarities[_side_of_upper(inp, mid)]
        delays[code] = float(spec["delay_ms"]) + delta
        pol = spec["polarity"]
        above_out[code] = {"delay_ms": None, "polarity": ("NORM" if pol == "INV" else "INV") if flip else pol, "moved_ms": round(delta, 6), "flipped": flip}
    if floating:
        lowest = min(delays.values())
        delays = {k: v - lowest for k, v in delays.items()}
    delays = {k: round(_snap_ms(v, step), 6) for k, v in delays.items()}
    if any(v < -1e-9 or v > max_ms + 1e-9 for v in delays.values()):
        return None, "delay"
    if two and inp.lr_rule_ms is not None and not inp.free_lr:
        offset = delays[sides[0].upper_code] - delays[sides[1].upper_code]
        if check_stage(rule_ms=inp.lr_rule_ms, lr_delay_ms=offset, tolerance_ms=inp.th.lr_tolerance_ms):
            return None, "stage"
    for code in above_out:
        above_out[code]["delay_ms"] = delays[code]
    return {"delays": delays, "above": above_out, "moved": {k: round(v, 6) for k, v in moved.items()}}, None


def _side_of_upper(inp, code):
    return next(s.name for s in inp.sides if s.upper_code == code)


def _wrap_ok(base_deg, rot_deg, window_deg):
    """Per probe (rows of `rot_deg`), where the phase stays within the window: a sign-free helper of the two scans' test."""
    a = np.abs(((base_deg[None, :] + rot_deg + 180.0) % 360.0) - 180.0)
    return a <= window_deg


def _bass_curves(hold, lps, delays, sign, probes, th):
    """The bass joint's width per sub delay, at every point: `(worst, median, crossings)` over `probes` (ms), or None if no point has a crossing."""
    f = np.asarray(hold.freqs, float)
    step = float(np.log2(f[1] / f[0]))
    probes = np.asarray(probes, float)
    cw = (f >= hold.cls.crossing_window[0]) & (f <= hold.cls.crossing_window[1])
    m0 = int(np.flatnonzero(cw)[0])
    front = None
    for name, woofer in hold.woofers.items():
        h = woofer if lps.get(name) is None else woofer * hold.lp_bank.get(lps[name])[0]
        h = h * np.exp(-2j * np.pi * f * float(delays[name]) * 1e-3)
        front = h if front is None else front + h
    s = sign * hold.sub
    gap = _db(s) - _db(front)
    base = (np.degrees(np.angle(s)) - np.degrees(np.angle(front))).astype(np.float32)
    rot = (-360.0 * f[None, :] * probes[:, None] * 1e-3).astype(np.float32)
    widths = np.zeros((s.shape[0], len(probes)))
    crossings = []
    any_point = False
    for p in range(s.shape[0]):
        c = _crossing(gap[p], cw, m0)
        if c is None:
            continue
        any_point = True
        crossings.append(float(f[c]))
        widths[p] = _widths(_wrap_ok(base[p], rot, th.phase_window_deg), c, step)
    if not any_point:
        return None
    return widths.min(0), np.median(widths, axis=0), crossings


def _bass_score(hold, lps, delays, sign, sub_delay_ms, th):
    """The bass joint at one sub delay: margin (the worst point's band over the delay tolerance), the worst and median at that delay, the
    median crossing. None: no crossing at any point."""
    n_tol = int(round(th.delay_tolerance_ms / DELAY_FINE_STEP_MS))
    probes = np.round(sub_delay_ms + np.arange(-n_tol, n_tol + 1) * DELAY_FINE_STEP_MS, 6)
    done = _bass_curves(hold, lps, delays, sign, probes, th)
    if done is None:
        return None
    worst, median, crossings = done
    at = int(np.argmin(np.abs(probes - sub_delay_ms)))
    return {"margin_oct": float(worst.min()), "width_worst_oct": float(worst[at]), "width_median_oct": float(median[at]),
            "crossing_hz": float(np.median(crossings))}


def _bass_holds(score, base, th):
    return score is not None and score["width_worst_oct"] >= base["width_worst_oct"] - th.bass_drop_oct - 1e-9 \
        and score["width_median_oct"] >= base["width_median_oct"] - th.bass_drop_oct - 1e-9


def _bass_judge(hold, lps, delays, th):
    """Is the bass joint still there under this candidate? Kept when it falls no further than the limit; else the sub's own delay and polarity,
    the knob that leaves everything else in place, try to bring it back (`wm_search.py:189-198`). `recovered` says the sub moved; `kept` False
    means no delay and polarity holds it, and the candidate goes (`rejected["bass"]`)."""
    base = hold.baseline(th)
    sign = -1.0 if hold.sub_polarity == "INV" else 1.0
    held = _bass_score(hold, lps, delays, sign, hold.sub_delay_ms, th)
    out = dict(held or {"margin_oct": 0.0, "width_worst_oct": 0.0, "width_median_oct": 0.0, "crossing_hz": None})
    out.update({"baseline_worst_oct": None if base is None else base["width_worst_oct"],
                "baseline_median_oct": None if base is None else base["width_median_oct"],
                "kept": True, "recovered": False, "sub_delay_ms": float(hold.sub_delay_ms), "sub_polarity": hold.sub_polarity})
    if base is None or _bass_holds(held, base, th):
        out["kept"] = base is not None
        return out
    n = int(math.floor(float(hold.max_ms) / BASS_RECOVER_STEP_MS + 1e-9))
    grid = np.arange(n + 1) * BASS_RECOVER_STEP_MS
    if hold.delay_step_ms:
        grid = np.unique(np.round(grid / hold.delay_step_ms) * hold.delay_step_ms)
    grid = grid[(grid >= 0.0) & (grid <= float(hold.max_ms) + 1e-9)]
    best = None
    for pol, s in (("NORM", 1.0), ("INV", -1.0)):
        done = _bass_curves(hold, lps, delays, s, grid, th)
        if done is None:
            continue
        worst, median, _cross = done
        margins = _delay_margins(grid, worst, np.arange(len(grid)), th.delay_tolerance_ms)
        top = np.flatnonzero(margins >= margins.max() - 1e-9)
        top = top[worst[top] >= worst[top].max() - 1e-9]
        k = int(top[_plateau_centre(median[top])])
        key = (float(margins[k]), float(worst[k]), float(median[k]))
        if best is None or key > best[0]:
            best = (key, pol, float(grid[k]), s)
    if best is None:
        out["kept"] = False
        return out
    _key, pol, delay, s = best
    score = _bass_score(hold, lps, delays, s, delay, th)
    if not _bass_holds(score, base, th):
        out["kept"] = False
        return out
    out.update(score)
    out.update({"kept": True, "recovered": True, "sub_delay_ms": round(delay, 6), "sub_polarity": pol})
    return out


def _gd_ms(opt, kind, f_hz, cache={}):  # noqa: B006 -- a cache over the option's fixed filter
    """The filter's group delay at `f_hz`, ms (`stage_v6.py:68-71`)."""
    key = (tuple(opt), kind, round(float(f_hz), 3))
    if key not in cache:
        fq = np.geomspace(20.0, 5000.0, 4000)
        h = dsp_math.xo_response(fq, float(opt[2]), int(opt[1]), kind, opt[0])
        gd = -np.gradient(np.unwrap(np.angle(h)), 2.0 * np.pi * fq) * 1e3
        cache[key] = float(gd[int(np.argmin(np.abs(fq - f_hz)))])
    return cache[key]


def _side_numbers(inp, side, cand, shift_ms, lp_bank, hp_bank, kernel):
    """A side's filters on its curves at its delay: the sum's dip and rms against the target, the summation loss, the lower driver's share."""
    f, cls = np.asarray(inp.freqs, float), inp.joint
    xl, xh = lp_bank.get(cand["lp"])[0], hp_bank.get(cand["hp"])[0]
    sign = -1.0 if cand["pol"] == "INV" else 1.0
    lower = side.lower * xl
    upper = sign * side.upper * xh * np.exp(-2j * np.pi * f * shift_ms * 1e-3)
    level = _power_db(kernel @ np.mean(np.abs(lower + upper) ** 2, 0))
    fit = (f >= cls.dip_fit_band[0]) & (f <= cls.dip_fit_band[1])
    dip = (f >= cls.dip_band[0]) & (f <= cls.dip_band[1])
    rms = (f >= cls.rms_band[0]) & (f <= cls.rms_band[1])
    target = inp.target_db
    dev = level - float(np.mean((level - target)[fit])) - target
    fx = float(cand["fx"])
    band = (fx / math.sqrt(2.0), fx * math.sqrt(2.0))
    losses = []
    for p in range(lower.shape[0]):
        loss = dsp_math.sum_loss(f, lower[p], upper[p], band)["avg_db"]
        if loss is not None:
            losses.append(loss)
    return {"dip_db": float(dev[dip].min()), "dip_at_hz": float(f[dip][int(np.argmin(dev[dip]))]),
            "target_rms_db": float(np.sqrt(np.mean(dev[rms] ** 2))),
            "loss_median_db": float(np.median(losses)) if losses else None,
            "share": lambda band: _lower_share(f, lower, upper, band)}


def _lower_share(f, lower, upper, band):
    """dB of the lower driver against both over `band`, power over the points (`stage_v6.woofer_share`)."""
    m = (f >= band[0]) & (f <= band[1])
    pw = np.mean(np.abs(lower) ** 2, 0)[m].sum()
    pm = np.mean(np.abs(upper) ** 2, 0)[m].sum()
    return float(10.0 * np.log10(max(pw / max(pw + pm, 1e-30), 1e-30)))


def scan_coupled(inp):
    """A joint above the bass: every pair that passes the leak on both sides, each scored on all its points with its delay curve kept, the sides
    paired under the stage conditions, the bass joint below held and re-scored. Returns `{"rows", "bands", "rejected", "grid"}`, rows best first."""
    f = np.asarray(inp.freqs, float)
    step = float(np.log2(f[1] / f[0]))
    th, cls = inp.th, inp.joint
    rejected = {"leak": 0, "no_crossing": 0, "phase": 0, "lr_crossing": 0, "stage": 0, "dip": 0, "delay": 0, "bass": 0, "past_shortlist": 0}
    lp_bank, hp_bank = _Bank(f, "lp"), _Bank(f, "hp")
    kernel = _third_oct(f)
    n_pairs = len(inp.lp_options) * len(inp.hp_options)
    leak_sides = [_leak_pairs(inp, side, lp_bank, hp_bank, kernel, rejected) for side in inp.sides]
    common = sorted(set.intersection(*(set(d) for d in leak_sides))) if leak_sides else []
    shifts = _shift_grid(inp)
    rows_by_side = [_side_curves(inp, side, {k: leak_sides[n][k] for k in common}, shifts, lp_bank, hp_bank, step, rejected)
                    for n, side in enumerate(inp.sides)]
    pairs = _pair_sides(inp, rows_by_side, shifts, rejected)
    edges = _band_edges(cls, th)
    by_band = {}
    for pair in pairs:
        fx = pair[1]["fx"] if pair[2] is None else math.sqrt(pair[1]["fx"] * pair[2]["fx"])
        label = _band_label(edges, fx)
        if label is None:
            rejected["no_crossing"] += 1
            continue
        by_band.setdefault(label, []).append(pair)
    rows = []
    for label, members in by_band.items():
        done = 0
        for k, pair in enumerate(members):
            if done >= ROWS_PER_BAND:
                rejected["past_shortlist"] += len(members) - k
                break
            row = _finish_pair(inp, pair, label, shifts, lp_bank, hp_bank, kernel, rejected)
            if row is not None:
                rows.append(row)
                done += 1
    rows.sort(key=lambda r: _row_key(r, th.rank), reverse=True)
    bands = {}
    for r in rows:
        bands.setdefault(r["band"], []).append(r)
    return {"rows": rows, "bands": bands, "rejected": rejected,
            "grid": {"pairs": n_pairs, "lp_options": [list(o) for o in inp.lp_options], "hp_options": [list(o) for o in inp.hp_options],
                     "shifts": len(shifts), "shift_range_ms": [float(shifts[0]), float(shifts[-1])], "passing_leak": len(common),
                     "candidates_per_side": [len(r) for r in rows_by_side], "pairs_considered": len(pairs)}}


def _finish_pair(inp, pair, label, shifts, lp_bank, hp_bank, kernel, rejected):
    """One L/R pair of candidates finished: the ceiling, the dip, the bass joint below, the numbers of the row; None with the drop counted."""
    f, th, cls = np.asarray(inp.freqs, float), inp.th, inp.joint
    _key, a, b, i, j = pair
    items = [(inp.sides[0], a, i)] + ([(inp.sides[1], b, j)] if b is not None else [])
    placed, why = _place_coupled(inp, {s.name: float(shifts[k]) for s, _c, k in items}, {s.name: c["pol"] for s, c, _k in items})
    if placed is None:
        rejected[why] += 1
        return None
    numbers = [(s, c, k, _side_numbers(inp, s, c, float(shifts[k]), lp_bank, hp_bank, kernel)) for s, c, k in items]
    if inp.dip_on and min(n[3]["dip_db"] for n in numbers) < th.dip_limit_db:
        rejected["dip"] += 1
        return None
    bass = None
    if inp.bass is not None:
        lps = {s.name: tuple(c["lp"]) for s, c, _k, _n in numbers}
        woofers_at = {s.name: placed["delays"][s.lower_code] for s, _c, _k, _n in numbers}
        bass = _bass_judge(inp.bass, lps, woofers_at, th)
        if not bass["kept"]:
            rejected["bass"] += 1
            return None
    sides_out = {}
    for s, c, k, n in numbers:
        side = {"lp": list(c["lp"]), "hp": list(c["hp"]), "polarity": c["pol"], "shift_ms": round(float(shifts[k]), 6), "crossing_hz": float(c["fx"]),
                "margin_oct": float(c["margin"][k]), "width_worst_oct": float(c["worst"][k]), "width_median_oct": float(c["median"][k]),
                "loss_median_db": n["loss_median_db"], "dip_db": n["dip_db"], "dip_at_hz": n["dip_at_hz"], "target_rms_db": n["target_rms_db"],
                "leak_up_db": c["up_db"], "leak_down_db": c["dn_db"], "lower_share_db": None, "lp_gd_ms": None,
                "fs_margin": None if not inp.fs_upper_hz else _cc.fs_margin(c["hp"][2], inp.fs_upper_hz, order=max(c["hp"][1] // 6, 1))["verdict"]}
        decay = (inp.decay or {}).get(s.name)
        if decay and decay.get("band"):
            side["lower_share_db"] = n["share"](decay["band"])
            side["lp_gd_ms"] = _gd_ms(c["lp"], "lp", decay["gd_at_hz"])
        sides_out[s.name] = side
    worst = min(s["width_worst_oct"] for s in sides_out.values())
    median = min(s["width_median_oct"] for s in sides_out.values())
    margin = min(s["margin_oct"] for s in sides_out.values())
    losses = [s["loss_median_db"] for s in sides_out.values() if s["loss_median_db"] is not None]
    delays = dict(placed["delays"])
    if bass is not None and inp.bass.sub_codes:
        delta = bass["sub_delay_ms"] - float(inp.bass.sub_delay_ms)
        delays.update({code: round(float(v) + delta, 6) for code, v in inp.bass.sub_codes.items()})
    return {"joint": cls.name, "sides": sides_out, "band": label, "move": inp.move, "margin_oct": margin, "width_worst_oct": worst,
            "width_median_oct": median, "loss_median_db": min(losses) if losses else None,
            "dip_db": min(s["dip_db"] for s in sides_out.values()), "target_rms_db": max(s["target_rms_db"] for s in sides_out.values()),
            "delays_ms": delays, "above": placed["above"], "moved_ms": placed["moved"], "bass": bass, "marks": list(inp.marks)}


# ---------------------------------------------------------------- flatten first (`--align`)
def _fit_flat(level_db, target_db, f, band, anchor, *, gain_max, cuts, cut_max):
    """Gain up and PK cuts so that `level_db` stands on the target over `band`, the target placed by the median over `anchor`: the run's rule,
    which replaces its three copies (`wm_flat.py:35-64`). Returns (gain up dB, bands)."""
    m, a = (f >= band[0]) & (f <= band[1]), (f >= anchor[0]) & (f <= anchor[1])
    off = float(np.median(level_db[a] - target_db[a]))
    best = None
    for g in np.arange(0.0, gain_max + 0.01, 1.0):
        e = level_db + g - target_db - off
        bands = []
        for _ in range(int(cuts)):
            em = np.where(m, e, -99.0)
            i = int(np.argmax(em))
            if em[i] < 1.0:
                break
            h = min(float(em[i]), cut_max)
            lo = i
            while lo > 0 and m[lo - 1] and e[lo - 1] > h / 2.0:
                lo -= 1
            hi = i
            while hi < len(f) - 1 and m[hi + 1] and e[hi + 1] > h / 2.0:
                hi += 1
            bw = max(math.log2(f[hi] / f[lo]), 0.1)
            q = float(np.clip(math.sqrt(2.0 ** bw) / (2.0 ** bw - 1.0), 0.7, 8.0))
            band_row = {"type": "PK", "f": round(float(f[i]), 1), "gain_db": round(-h, 1), "q": round(q, 2)}
            bands.append(band_row)
            e = e + 20.0 * np.log10(np.abs(dsp_math.peq_response(f, "PK", band_row["f"], band_row["gain_db"], band_row["q"])))
        res = e[m]
        cost = float(np.sqrt(np.mean(np.minimum(res, 0.0) ** 2)) + np.sqrt(np.mean(np.maximum(res, 0.0) ** 2))) + 0.15 * len(bands)
        if best is None or cost < best[0]:
            best = (cost, float(g), bands)
    return best[1], best[2]


def _eq_response(f, bands, gain_db):
    """The channel's PK cuts and gain, complex."""
    h = np.ones_like(f, dtype=complex) * 10.0 ** (gain_db / 20.0)
    for band in bands:
        h = h * dsp_math.peq_response(f, "PK", band["f"], band["gain_db"], band["q"])
    return h


def _passband_db(h_points, f, band):
    """The power level over `band`, the points' power mean: the level `--align` keeps a channel at."""
    m = (f >= band[0]) & (f <= band[1])
    return float(10.0 * np.log10(np.mean(np.mean(np.abs(h_points) ** 2, 0)[m])))


def _flatten_channel(h_points, target_db, f, band, anchor, th, gain_step=None):
    """One channel put on the target: gain up and PK cuts over `band`, the level over `anchor` restored so only the shape changes
    (`wm_flat.py:83-90`), the net gain on the DSP's gain step. Returns (complex EQ, info for the row)."""
    level = _power_db(_third_oct(f) @ np.mean(np.abs(h_points) ** 2, 0))
    gain_up, bands = _fit_flat(level, target_db, f, band, anchor, gain_max=th.align_gain_max_db, cuts=th.align_cuts, cut_max=th.align_cut_max_db)
    raw = _eq_response(f, bands, gain_up)
    net = gain_up + _passband_db(h_points, f, anchor) - _passband_db(h_points * raw, f, anchor)
    if gain_step:
        net = round(round(net / gain_step) * gain_step, 6)
    eq = _eq_response(f, bands, net)
    return eq, {"gain_up_db": round(gain_up, 1), "bands": bands, "net_gain_db": round(net, 2),
                "passband_error_db": round(_passband_db(h_points * eq, f, anchor) - _passband_db(h_points, f, anchor), 3)}


def _common_trim(after, gain_range, step):
    """A channel past the gain range brings every channel alike, by the excess on the gain step (`wm_flat.py:184`), not a cap on that channel,
    which took one side to 0 oct. `after` is {code: channel gain}; None: no common shift fits the range at both ends."""
    lo, hi = gain_range
    values = list(after.values())
    over = max(values) - hi
    under = lo - min(values)

    def to_step(x):
        return x if not step else math.ceil(x / step - 1e-9) * step
    if over > 1e-9:
        trim = -to_step(over)
    elif under > 1e-9:
        trim = to_step(under)
    else:
        return 0.0
    if max(values) + trim > hi + 1e-9 or min(values) + trim < lo - 1e-9:
        return None
    return round(trim, 6)


# ---------------------------------------------------------------- the decay: read once per raw driver, reported and never ranked
def decay_table(curves, codes, freqs_hz):
    """The ring time of each raw driver in 1/3-octave bands (`ear_suspects.ringdown_ms`: -20 dB, from the impulse): tripod, else a centre point."""
    import ear_suspects
    table = {"freqs_hz": [float(x) for x in freqs_hz], "ms": {}, "ir_from": {}}
    for code in codes:
        info = curves[code]["info"]
        key = next((k for k in ("tripod", "p5", "p1", "p9") if k in info), next(iter(info), None))
        if key is None or info[key].get("ir") is None:
            table["ms"][code] = [None] * len(table["freqs_hz"])
            table["ir_from"][code] = None
            continue
        ir = info[key]["ir"]
        table["ms"][code] = [ear_suspects.ringdown_ms(np.asarray(ir["ir"], float), float(ir["sample_rate"]), f0) for f0 in table["freqs_hz"]]
        table["ir_from"][code] = key
    return table


def ring_band(lower_ms, upper_ms, freqs_hz, ratio):
    """Where the lower driver rings at least `ratio` times longer: `{freqs_hz, band: (lo, hi)}` or None."""
    flagged = [f for f, lo, up in zip(freqs_hz, lower_ms, upper_ms) if lo is not None and up is not None and up > 0 and lo >= ratio * up]
    if not flagged:
        return None
    third = 2.0 ** (1.0 / 6.0)
    return {"freqs_hz": flagged, "band": (min(flagged) / third, max(flagged) * third), "gd_at_hz": min(flagged)}


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
        notes.append(f"the stereo sub's L-R offset ({lower_offset:+.2f} ms) is low-confidence: read in {ARRIVAL_READ[lower.role][0][0]:g}-"
                     f"{ARRIVAL_READ[lower.role][0][1]:g} Hz, where a planted 1 ms read as about 0.4 ms -- check it by a measurement of its own "
                     "before keying it in")
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
    # the upper role's low-pass, in the model when `--front-lp` names it: it adds its phase to the front's arrival at the crossing
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
    if doc.get("default_line"):
        lines.append(doc["default_line"])
    free_shown = not cond["lr_offset_held"] and not cond["upper_single"]
    codes = list(doc["channels"]["lower"]) + list(doc["channels"]["upper"])
    delay_heads = " ".join(f"{c:>8}" for c in codes)
    for label, rows in doc["bands"].items():
        lines.append(f"\nCrossing {label}:")
        lines.append(f"  {'LP':>12} {'HP':>12} {'sub dB':>7} {'front dB':>9} {'sub pol':>7} "
                     + (f"{'L-R ms':>7} " if free_shown else "")
                     + f"{delay_heads} {'delay on':>9} {'margin':>7} {'worst oct':>9} "
                     f"{'med oct':>7} {'loss dB':>7} {'dip dB':>6} {'leak near':>9} {'Fs':>7}")
        for r in rows:
            lines.append(f"  {_filter_name(r['lp']):>12} {_filter_name(r['hp']):>12} {r['sub_gain_db']:>+7.2f} {r['front_gain_db']:>+9.2f} "
                         f"{r['polarity']:>7} "
                         + (f"{r['lr_offset_ms']:>+7.2f} " if free_shown else "")
                         + " ".join(f"{r['delays_ms'][c]:>8.3f}" for c in codes)
                         + f" {r['who_delays']:>9} {r['margin_oct']:>7.2f} {r['width_worst_oct']:>9.2f} {r['width_median_oct']:>7.2f} "
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
    lines.append("\nThis describes and never picks: the ear decides, the choice is the tuner's.")
    return "\n".join(lines)


def _bounds(spec, label):
    try:
        lo, hi = (float(x) for x in spec.split(":"))
        if not 0 < lo < hi:
            raise ValueError
    except ValueError:
        raise JointSearchError(f"{label} takes LO:HI in Hz, got {spec!r}") from None
    return lo, hi


# ---------------------------------------------------------------- the limits: each a flag, its effect shown
#: `Limits` fields and their flags, in the order the output prints them (`--leak-near`/`--leak-far` are the bass joint's, `--leak-octave` the joints' above it).
_LIMIT_FLAGS = (("phase_window_deg", "--phase-window"), ("leak_near_db", "--leak-near"), ("leak_far_db", "--leak-far"), ("leak_octave_db", "--leak-octave"),
                ("dip_limit_db", "--dip-limit"), ("delay_tolerance_ms", "--delay-tolerance"), ("lr_tolerance_ms", "--lr-tolerance"),
                ("lr_crossing_oct", "--lr-crossing-oct"), ("shortlist", "--shortlist"), ("band_width_oct", "--band-width"), ("corner_step_oct", "--corner-step"),
                ("rank", "--rank"), ("sub_one_point_max_hz", "--sub-one-point-max"), ("shift_span_ms", "--shift-span"), ("bass_drop_oct", "--bass-drop"),
                ("ring_ratio", "--ring-ratio"), ("align_gain_max_db", "--align-gain-max"), ("align_cuts", "--align-cuts"), ("align_cut_max_db", "--align-cut-max"),
                ("crossing_window", "--crossing-window"), ("dip_band", "--dip-band"))


def _limits_of(args):
    """`Limits` from the command line; a value that cannot mean anything refuses in one line."""
    def need(cond, words):
        if not cond:
            raise JointSearchError(words)
    values = {}
    for name, flag in _LIMIT_FLAGS:
        v = getattr(args, name)
        if v is None:
            continue
        values[name] = v
    if "phase_window_deg" in values:
        need(0.0 < values["phase_window_deg"] < 180.0, f"--phase-window takes a value above 0 and under 180 degrees (the phase window), got {values['phase_window_deg']:g}")
    if "shortlist" in values:
        need(values["shortlist"] >= 1, f"--shortlist takes 1 or more, got {values['shortlist']}")
    if "band_width_oct" in values:
        need(values["band_width_oct"] > 0.0, f"--band-width takes octaves above 0, got {values['band_width_oct']:g}")
    if "corner_step_oct" in values:
        need(values["corner_step_oct"] > 0.0, f"--corner-step takes octaves above 0, got {values['corner_step_oct']:g}")
    if "delay_tolerance_ms" in values:
        need(values["delay_tolerance_ms"] >= 0.0, f"--delay-tolerance takes 0 or more ms, got {values['delay_tolerance_ms']:g}")
    if "lr_tolerance_ms" in values:
        need(values["lr_tolerance_ms"] >= 0.0, f"--lr-tolerance takes 0 or more ms, got {values['lr_tolerance_ms']:g}")
    if "shift_span_ms" in values:
        need(values["shift_span_ms"] > 0.0, f"--shift-span takes ms above 0, got {values['shift_span_ms']:g}")
    if "ring_ratio" in values:
        need(values["ring_ratio"] > 0.0, f"--ring-ratio takes a ratio above 0, got {values['ring_ratio']:g}")
    if "align_cuts" in values:
        need(values["align_cuts"] >= 0, f"--align-cuts takes 0 or more, got {values['align_cuts']}")
    if "crossing_window" in values:
        values["crossing_window"] = _bounds(values["crossing_window"], "--crossing-window")
    if "dip_band" in values:
        values["dip_band"] = _bounds(values["dip_band"], "--dip-band")
    return Limits(**values)


def _limits_report(th):
    """Each limit, its value, its default and whether it was changed, as the output prints them."""
    defaults = Limits()
    out = {}
    for name, flag in _LIMIT_FLAGS:
        value, default = getattr(th, name), getattr(defaults, name)
        out[name] = {"value": list(value) if isinstance(value, tuple) else value, "default": list(default) if isinstance(default, tuple) else default,
                     "changed": value != default, "flag": flag}
    return out


def _changed_words(report, extra=()):
    words = [f"{v['flag']} {v['value']} (default {v['default']})" for v in report.values() if v["changed"]]
    return words + list(extra)


def _default_run(scan, changed_inp, default_inp, changed_words, summarise):
    """The same grid on the defaults, when anything was changed: what the change bought, in rows and in the best row."""
    if not changed_words:
        return None
    result = scan(default_inp)
    return {"changed": list(changed_words), "rows": len(result["rows"]), "best": summarise(result["rows"][0]) if result["rows"] else None,
            "rejected": result["rejected"]}


def _best_summary_bass(row):
    return {"lp": row["lp"], "hp": row["hp"], "margin_oct": _round(row["margin_oct"]), "width_worst_oct": _round(row["width_worst_oct"])}


def _best_summary_coupled(row):
    side = next(iter(row["sides"]))
    return {"lp": row["sides"][side]["lp"], "hp": row["sides"][side]["hp"], "margin_oct": _round(row["margin_oct"]), "width_worst_oct": _round(row["width_worst_oct"])}


def _default_line(default_run, here_rows, here_best):
    """The sentence the table prints about the changed limits."""
    words = "; ".join(default_run["changed"])
    best = default_run["best"]
    theirs = f"{default_run['rows']} rows" + (f", best margin {best['margin_oct']:.2f} oct" if best else "")
    mine = f"{here_rows} rows" + (f", best margin {here_best['margin_oct']:.2f} oct" if here_best else "")
    return f"Changed from the defaults: {words}. On the defaults the same grid gives {theirs}; these settings give {mine}."


# ---------------------------------------------------------------- `--fixed`
def _load_fixed(specs):
    """`--fixed FILE[@N]`, repeated: each a row of a joint's output (a row file, or a document with the row named `@N`, 1-based: this tool does not
    pick). Returns the rows; each carries `joint` and `channels`, or the refusal says what is missing."""
    rows = []
    for spec in specs or []:
        path, _sep, which = spec.partition("@")
        if not os.path.isfile(path):
            raise JointSearchError(f"--fixed {path}: no such file")
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError) as exc:
            raise JointSearchError(f"--fixed {path}: not readable as JSON: {exc}") from None
        if isinstance(data, dict) and isinstance(data.get("rows"), list):
            if not which:
                raise JointSearchError(f"--fixed {path} holds {len(data['rows'])} rows: name the one you chose as {path}@N, N from 1 (this tool never picks)")
            try:
                row = data["rows"][int(which) - 1]
            except (ValueError, IndexError):
                raise JointSearchError(f"--fixed {spec}: row {which!r} is not one of its {len(data['rows'])} rows") from None
        else:
            row = data
        if not isinstance(row, dict) or "joint" not in row or "channels" not in row or "delays_ms" not in row:
            raise JointSearchError(f"--fixed {spec}: not a joint's row (it needs `joint`, `channels` and `delays_ms`; take a row of this tool's --json or --out file)")
        rows.append(row)
    return rows


# ---------------------------------------------------------------- a row in a table or a file
def _channel_row(pub_row, lower, upper):
    """What a person keys in, channel by channel (the `channels` of a bass row): also what `--fixed` reads back."""
    tas = pub_row["ta_ms"]
    out = {}
    if lower.single:
        out[lower.codes[0]] = {"lp": pub_row["lp"], "polarity": pub_row["polarity"], "gain_db": pub_row["sub_gain_db"], "delay_ms": tas["sub"]}
    else:
        for code, key in zip(lower.codes, ("sub_left", "sub_right")):
            out[code] = {"lp": pub_row["lp"], "polarity": pub_row["polarity"], "gain_db": pub_row["sub_gain_db"], "delay_ms": tas[key]}
    for code, key in zip(upper.codes, ("upper_left", "upper_right")):
        out[code] = {"hp": pub_row["hp"], "lp": pub_row.get("front_lp"), "gain_db": pub_row["front_gain_db"], "polarity": "NORM", "delay_ms": tas[key]}
    return out


def _public_coupled(row, ctx):
    """A coupled row as a reader gets it: rounded, each channel's settings in `channels` for the table and for a later `--fixed`."""
    out = dict(row)
    for key, n in (("margin_oct", 2), ("width_worst_oct", 2), ("width_median_oct", 2), ("loss_median_db", 2), ("dip_db", 2), ("target_rms_db", 2)):
        out[key] = _round(out[key], n)
    sides = {}
    for name, side in row["sides"].items():
        s = dict(side)
        for key, n in (("margin_oct", 2), ("width_worst_oct", 2), ("width_median_oct", 2), ("loss_median_db", 2), ("dip_db", 2), ("dip_at_hz", 1),
                       ("target_rms_db", 2), ("leak_up_db", 1), ("leak_down_db", 1), ("crossing_hz", 1), ("lower_share_db", 1), ("lp_gd_ms", 2)):
            s[key] = _round(s[key], n)
        sides[name] = s
    out["sides"] = sides
    if row.get("bass"):
        b = dict(row["bass"])
        for key in ("margin_oct", "width_worst_oct", "width_median_oct", "baseline_worst_oct", "baseline_median_oct", "crossing_hz"):
            b[key] = _round(b.get(key), 2)
        out["bass"] = b
    channels = {}
    for name, side in sides.items():
        low_code, up_code = ctx["sides"][name]
        channels[low_code] = {"lp": side["lp"], "hp": ctx["held_filters"].get(low_code, {}).get("hp"), "polarity": "NORM", "gain_db": ctx["gains"].get(low_code),
                              "delay_ms": row["delays_ms"][low_code], "eq": ctx["eq"].get(low_code, [])}
        channels[up_code] = {"hp": side["hp"], "lp": ctx["held_filters"].get(up_code, {}).get("lp"), "polarity": side["polarity"], "gain_db": ctx["gains"].get(up_code),
                             "delay_ms": row["delays_ms"][up_code], "eq": ctx["eq"].get(up_code, [])}
    for code, spec in (row.get("above") or {}).items():
        channels[code] = {"delay_ms": spec["delay_ms"], "polarity": spec["polarity"]}
    for code in row["delays_ms"]:
        if code not in channels:
            sub = ctx["held_filters"].get(code, {})
            bass = row.get("bass") or {}
            channels[code] = {"lp": sub.get("lp"), "polarity": bass.get("sub_polarity", sub.get("polarity")), "gain_db": ctx["gains"].get(code), "delay_ms": row["delays_ms"][code]}
    out["channels"] = channels
    return out


def _render_coupled(doc):
    """The table of a coupled joint: two lines to a row, L and R, what a person keys in and the numbers it was ranked on."""
    joint, cond = doc["joint"], doc["conditions"]
    lines = [f"Joint {joint}: {doc['grid']['pairs']} filter pairs, {doc['grid']['passing_leak']} pass the leak on both sides, each scored over "
             f"{doc['grid']['shifts']} delay steps at every point. Stack: {' / '.join(doc['joints_in_stack'])}."]
    if doc.get("default_line"):
        lines.append(doc["default_line"])
    lines.append(f"Delay moves on the {cond['move']} group. L-R offset of the upper role: {cond['lr_words']}. Same polarity L/R: {cond['same_polarity']}; "
                 f"same family/order L/R: {cond['same_family']}; corners {'per side' if cond['per_side_corners'] else 'alike L/R'}.")
    for label, rows in doc["bands"].items():
        lines.append(f"\nCrossing {label}:")
        for r in rows:
            sides = list(r["sides"].items())
            for k, (name, s) in enumerate(sides):
                lead = f"{name or 'mono':>4}" + ("" if k else "")
                d = r["delays_ms"]
                low_code, up_code = _codes_of_side(doc, name)
                lines.append(f"  {lead} LP {_filter_name(s['lp']):>14}  HP {_filter_name(s['hp']):>14}  {s['polarity']:>4}  {low_code} {d[low_code]:>6.2f} ms  {up_code} {d[up_code]:>6.2f} ms"
                             f"  margin {s['margin_oct']:.2f}  worst {s['width_worst_oct']:.2f}  med {s['width_median_oct']:.2f}  loss {s['loss_median_db'] if s['loss_median_db'] is not None else float('nan'):+.2f}"
                             f"  dip {s['dip_db']:+.1f}  rms {s['target_rms_db']:.2f}  leak {s['leak_up_db'] if s['leak_up_db'] is not None else float('nan'):+.0f}/{s['leak_down_db'] if s['leak_down_db'] is not None else float('nan'):+.0f}"
                             + (f"  share {s['lower_share_db']:+.1f} dB" if s["lower_share_db"] is not None else "")
                             + (f"  LP GD {s['lp_gd_ms']:.2f} ms" if s["lp_gd_ms"] is not None else "")
                             + (f"  [{', '.join(r['marks'])}]" if r["marks"] and k == 0 else ""))
            head = f"       pair margin {r['margin_oct']:.2f}, worst {r['width_worst_oct']:.2f}, median {r['width_median_oct']:.2f}"
            if r.get("bass"):
                b = r["bass"]
                head += (f"; bass joint held {b['width_worst_oct']:.2f}/{b['width_median_oct']:.2f} oct (was {b['baseline_worst_oct']:.2f}/{b['baseline_median_oct']:.2f})"
                         + (f", sub moved to {b['sub_delay_ms']:.2f} ms {b['sub_polarity']}" if b["recovered"] else ""))
            for code, spec in (r.get("above") or {}).items():
                head += f"; {code} {spec['delay_ms']:.2f} ms {spec['polarity']}" + (" (flipped)" if spec["flipped"] else "")
            lines.append(head)
    lines.append("")
    if doc.get("decay"):
        lines.append("Decay (reported, not ranked): " + _decay_words(doc["decay"]))
    if doc.get("align"):
        lines.append(_align_words(doc["align"]))
    if doc.get("cross_first"):
        lines.append(_cross_first_words(doc["cross_first"]))
    if doc["notes"]:
        lines.append("Notes:")
        lines.extend(f"  - {n}" for n in doc["notes"])
        lines.append("")
    if doc["rows"]:
        lines.append("Rejected: " + (_reasons_coupled(doc["rejected"]) or "nothing"))
    else:
        lines.append("No variant came through the limits. Reasons, counted: " + (_reasons_coupled(doc["rejected"]) or "none recorded"))
    lines.append("\nThis describes and never picks: the ear decides, the choice is the tuner's.")
    return "\n".join(lines)


def _codes_of_side(doc, name):
    side = doc["sides"][name]
    return side["lower"], side["upper"]


def _reasons_coupled(rejected):
    return ", ".join(f"{_REJECT_WORDS_COUPLED.get(k, k)} {v}" for k, v in rejected.items() if v)


def _decay_words(decay):
    parts = []
    for name, band in decay["bands"].items():
        if band:
            parts.append(f"{name or 'mono'}: the lower driver rings {decay['ring_ratio']:g}x longer at {', '.join(f'{f:g}' for f in band['freqs_hz'])} Hz")
        else:
            parts.append(f"{name or 'mono'}: no band where the lower driver rings {decay['ring_ratio']:g}x longer")
    ms = "; ".join(f"{code} {['%.0f' % x if x is not None else '-' for x in values]}" for code, values in decay["table"]["ms"].items())
    return f"{'; '.join(parts)}. Ring ms at {', '.join(f'{f:g}' for f in decay['table']['freqs_hz'])} Hz: {ms}."


def _align_words(align):
    parts = [f"{code}: gain up {info['gain_up_db']:+.1f}, {len(info['bands'])} cuts, net {info['net_gain_db']:+.2f} dB" for code, info in align["channels"].items()]
    return "Aligned first: " + "; ".join(parts) + f". Common trim {align['global_trim_db']:+.2f} dB (every channel alike)."


def _cross_first_words(cross):
    if cross["rows"] is None:
        return "Cross first: no comparison (no row without the align)."
    return (f"Cross first (same filters and delays searched on the raw drivers, the same EQ budget on each side's sum): "
            + "; ".join(f"{r['band']}: rms {r['no_eq_rms_db']:.2f} -> {r['with_eq_rms_db']:.2f} dB, dip {r['no_eq_dip_db']:+.1f} -> {r['with_eq_dip_db']:+.1f} dB, "
                        f"{r['cuts']} cuts on the sum" for r in cross["rows"]))


_REJECT_WORDS_COUPLED = dict(_REJECT_WORDS, leak="leak limit (either side)", phase="no in-phase band on any delay",
                             lr_crossing="L and R crossings too far apart", bass="the bass joint below could not be held", stage="L-R rule off the delay step",
                             delay="delay outside 0..max_ms", past_shortlist="not looked at, past the shortlist")


# ---------------------------------------------------------------- the joints above the bass, on the command line
def _points_of(chan, code, points, single, label):
    """A channel's curves at the points, a (points, grid) array; a missing point refuses as the bass joint does."""
    if single:
        return np.array([_ref_curve(chan, code)])
    missing = [p for p in points if p not in chan["points"]]
    if missing:
        raise JointSearchError(f"{code}: the nine points are needed and {', '.join(missing)} are missing -- capture them, or decide for --single-point and record that decision"
                               if label == "front" else f"{code}: {', '.join(missing)} of its points are missing; measure at all nine points or at one")
    return np.array([chan["points"][p] for p in points])


def _sub_points(chan, code, points, single, one_point):
    if single or one_point:
        return np.tile(_ref_curve(chan, code), (len(points), 1))
    return _points_of(chan, code, points, single, "sub")


def _arrival_centre(a, b, side_name):
    """Where the shift search centres: minus the raw arrival of the upper against the lower at the centre points, or 0 and a note."""
    values, reasons = [], []
    band, gate = ARRIVAL_READ["woofer"]
    for key in ("tripod",) + CENTRE_POINTS:
        ia, ib = (a["info"].get(key) or {}).get("ir"), (b["info"].get(key) or {}).get("ir")
        if ia is None or ib is None:
            continue
        ms, info = windows.arrival_between(ia["ir"], ib["ir"], float(ia["sample_rate"]), band=band, gate_ms=gate,
                                           t0_a=float(ia["t0_s"]), t0_b=float(ib["t0_s"]))
        if ms is None:
            reasons.append(f"{key}: {info.get('refused')}")
        else:
            values.append(ms)
    if values:
        return -float(np.mean(values)), None
    return 0.0, f"side {side_name or 'mono'}: the raw arrival of upper against lower could not be read ({'; '.join(reasons) or 'no shared point'}): the shift search centres on 0"


def _align_band_table(specs):
    """`--align-band ROLE=FITLO:FITHI/ANCHLO:ANCHHI`, repeated, over `ALIGN_BANDS`."""
    table = dict(ALIGN_BANDS)
    for spec in specs or []:
        role, _eq, rest = spec.partition("=")
        if role not in table:
            raise JointSearchError(f"--align-band {spec!r}: no such role (one of {', '.join(table)})")
        fit, _slash, anchor = rest.partition("/")
        table[role] = (_bounds(fit, "--align-band"), _bounds(anchor, "--align-band"))
    return table


def _run_coupled(args, space, channels, stack, th, process_mod):
    """The woofer-mid joint from the command line; the bass path's helpers, the coupled scan, one table."""
    project_dir = args.project
    found = joints_of(channels, cls=args.joint)
    if not found:
        raise JointSearchError(f"no {args.joint} joint in this stack ({' / '.join(stack) or 'no joints'})")
    joint = found[0]
    lower, upper = joint.lower, joint.upper
    if lower.single != upper.single:
        raise JointSearchError(f"{joint.name}: one side has an L/R pair and the other one channel: this tool cannot pair them")
    fixed_rows = _load_fixed(args.fixed)
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
    cls = _dc_replace(cls, lp_bounds=lp_bounds, hp_bounds=hp_bounds, crossing_window=th.crossing_window or cls.crossing_window, dip_band=th.dip_band or cls.dip_band)
    default_cls = _dc_replace(JOINT_CLASSES[joint.cls], lp_bounds=lp_bounds, hp_bounds=hp_bounds)
    lp_corners = corner_grid(lp_bounds, space.xo, th.corner_step_oct)
    hp_corners = corner_grid(hp_bounds, space.xo, th.corner_step_oct)
    lp_options = filter_options(space.families, lp_corners)
    hp_options = filter_options(space.families, hp_corners, floor_hz=floor)
    if not lp_options or not hp_options:
        raise JointSearchError(f"no filter pair left: LP corners {lp_bounds} Hz, HP corners {hp_bounds} Hz above the floor {floor:g} Hz")
    pairs = len(lp_options) * len(hp_options)
    print(f"grid: {len(lp_corners)} LP corners x {len(space.families)} families x {len(hp_corners)} HP corners x {len(space.families)} families = {pairs} filter pairs "
          f"(ceiling {GRID_CEILING_PAIRS}); each that passes the leak scored per side over the delays and both polarities", file=sys.stderr)
    if pairs > GRID_CEILING_PAIRS and not args.allow_large_grid:
        raise JointSearchError(f"{pairs} filter pairs is over the ceiling {GRID_CEILING_PAIRS}: narrow --lp-bounds / --hp-bounds or pass --allow-large-grid")
    front_lp = _front_lp_spec(args.front_lp, space) if args.front_lp else None
    if args.single_point and not _single_point_decided(process_mod, project_dir):
        raise JointSearchError("--single-point needs the person's recorded decision: the session says the limits, the person "
                               f"decides, and it is recorded in these words: `process.py {project_dir} decision "
                               f"\"{SINGLE_POINT_DECISION}\" \"<the person's words>\"`")
    freqs = P.grid(cls.grid_hz[0], cls.grid_hz[1], GRID_PPO)
    target = _read_target(args.house, freqs)
    # what is held: the joint below, and any row naming this joint's upper channels
    fixed_bass = next((r for r in fixed_rows if r["joint"].startswith("sub-")), None)
    fixed_upper = next((r for r in fixed_rows if any(c in r["channels"] for c in upper.codes) and not r["joint"].startswith("sub-")), None)
    if args.sub_solos and fixed_bass is None:
        raise JointSearchError("--sub-solos without a --fixed bass row: the sub is read only to re-score the joint below")
    bass_joints = joints_of(channels, cls="bass") if fixed_bass is not None else []
    if fixed_bass is not None and not bass_joints:
        raise JointSearchError("--fixed names a bass row, and this stack has no bass joint")
    sub_codes = list(bass_joints[0].lower.codes) if bass_joints else []
    upper_codes = list(lower.codes) + list(upper.codes)
    main, lower_curves, notes = _load_capture(args, project_dir, upper_codes, sub_codes, freqs, Branch("woofer", lower.codes), process_mod)
    points = ["centre"] if args.single_point else list(POSITIONS)
    chains, held_filters, gains = {}, {}, {}
    for code in upper_codes:
        chains[code] = _points_of(main[code], code, points, args.single_point, "front")
    if front_lp:
        lp_h = dsp_math.xo_response(freqs, front_lp[2], front_lp[1], "lp", front_lp[0])
        for code in upper.codes:
            chains[code] = chains[code] * lp_h
            held_filters.setdefault(code, {})["lp"] = list(front_lp)
    held_lower, held_upper, upper_pol, above = None, None, None, None
    if fixed_bass is not None:
        held_lower = {}
        for code in lower.codes:
            spec = fixed_bass["channels"].get(code)
            if spec is None:
                raise JointSearchError(f"--fixed bass row has no channel {code}")
            held_lower[code] = float(spec["delay_ms"])
            gains[code] = float(spec.get("gain_db") or 0.0)
            hp = spec.get("hp")
            if hp:
                chains[code] = chains[code] * dsp_math.xo_response(freqs, hp[2], hp[1], "hp", hp[0])
                held_filters.setdefault(code, {})["hp"] = list(hp)
            chains[code] = chains[code] * 10.0 ** (gains[code] / 20.0)
    if fixed_upper is not None:
        held_upper, upper_pol = {}, {}
        for code in upper.codes:
            spec = fixed_upper["channels"].get(code)
            if spec is None:
                raise JointSearchError(f"--fixed row of {fixed_upper['joint']} has no channel {code}")
            held_upper[code] = float(spec["delay_ms"])
            upper_pol[code] = spec.get("polarity") or "NORM"
            lp = spec.get("lp")
            if lp and not front_lp and fixed_upper["joint"] != joint.name:
                chains[code] = chains[code] * dsp_math.xo_response(freqs, lp[2], lp[1], "lp", lp[0])
                held_filters.setdefault(code, {})["lp"] = list(lp)
        for code, spec in fixed_upper["channels"].items():
            if code in upper.codes or code in lower.codes:
                continue
            follow = next((c for c in upper.codes if c.split("-")[-1] == code.split("-")[-1] and len(upper.codes) > 1), upper.codes[0])
            above = above or {}
            above[code] = {"delay_ms": float(spec["delay_ms"]), "polarity": spec.get("polarity") or "NORM", "follows": follow}
    # flatten first
    eq_bands, align_doc = {}, None
    if args.align:
        table = _align_band_table(args.align_band)
        align_doc = {"channels": {}, "bands": {}}
        for code in upper_codes:
            role = lower.role if code in lower.codes else upper.role
            fit, anchor = table[role]
            fs_here = _xw._fs_of(channels[code])[0]
            if role in _xw.FRAGILE_ROLES and fs_here:
                fit = (max(fit[0], float(fs_here)), fit[1])
            eq, info = _flatten_channel(chains[code], target, freqs, fit, anchor, th, gain_step=space.gain_step_db)
            chains[code] = chains[code] * eq
            eq_bands[code] = info["bands"]
            gains[code] = gains.get(code, 0.0) + info["net_gain_db"]
            align_doc["channels"][code] = info
            align_doc["bands"][code] = {"fit": list(fit), "anchor": list(anchor)}
    # the bass joint below
    hold = None
    if fixed_bass is not None:
        bass_joint = bass_joints[0]
        sub_row = fixed_bass["channels"]
        sub_delays = {c: float(sub_row[c]["delay_ms"]) for c in bass_joint.lower.codes}
        if not all(c in sub_row for c in bass_joint.lower.codes):
            raise JointSearchError(f"--fixed bass row has no channel {bass_joint.lower.codes}")
        one = len(bass_joint.lower.codes) == 1
        ref_code = bass_joint.lower.codes[0]
        lp = sub_row[ref_code].get("lp") or fixed_bass.get("lp")
        if not lp:
            raise JointSearchError(f"--fixed bass row: {ref_code} has no low-pass")
        low_h = dsp_math.xo_response(freqs, lp[2], lp[1], "lp", lp[0])
        gain = 10.0 ** (float(sub_row[ref_code].get("gain_db") or 0.0) / 20.0)
        sub_one = not any(lower_curves[c]["points"] for c in bass_joint.lower.codes)
        stacks = [_sub_points(lower_curves[c], c, points, args.single_point, sub_one) for c in bass_joint.lower.codes]
        base_delay = sub_delays[ref_code]
        sub = stacks[0] * np.exp(-2j * np.pi * freqs * (sub_delays[ref_code] - base_delay) * 1e-3)
        if not one:
            sub = sub + stacks[1] * np.exp(-2j * np.pi * freqs * (sub_delays[bass_joint.lower.codes[1]] - base_delay) * 1e-3)
        sub = sub * low_h * gain
        woofers, delays_below, base_lps = {}, {}, {}
        row_front_lp = fixed_bass.get("front_lp")
        sides_lower = (("L", lower.left), ("R", lower.right)) if not lower.single else (("", lower.codes[0]),)
        for name, code in sides_lower:
            woofers[name], delays_below[name], base_lps[name] = chains[code].copy(), held_lower[code], (tuple(row_front_lp) if row_front_lp else None)
        hold = BassHold(freqs=freqs, sub=sub, woofers=woofers, sub_delay_ms=base_delay, sub_polarity=sub_row[ref_code].get("polarity") or "NORM", base_delays=delays_below,
                        base_lps=base_lps, max_ms=space.delay_max_ms, delay_step_ms=space.delay_step_ms, sub_codes=sub_delays)
        gains.update({c: float(sub_row[c].get("gain_db") or 0.0) for c in bass_joint.lower.codes})
        held_filters.update({c: {"lp": list(lp), "polarity": sub_row[c].get("polarity")} for c in bass_joint.lower.codes})
        notes.append("the bass joint below is held from its row and re-scored with each candidate's low-pass (recovered by the sub's own delay and polarity when it falls)")
    else:
        notes.append("no --fixed bass row: the bass joint is not in this model and is not re-scored")
    if args.align:
        trim = _common_trim({c: gains.get(c, 0.0) for c in upper_codes + sub_codes}, space.gain_range, space.gain_step_db)
        if trim is None:
            raise JointSearchError(f"after the align the channel gains span past the DSP's range {space.gain_range} at both ends: no common trim fits")
        align_doc["global_trim_db"] = trim
        for code in gains:
            gains[code] = round(gains[code] + trim, 6)
        if trim:
            notes.append(f"a channel left the gain range after the align: every channel moves by {trim:+g} dB alike, the sub and the channels not in this joint included")
    # the sides
    decay_ranges = _ring_freqs(cls.ring_band)
    decay_doc, decay_input = None, None
    sides, sides_doc, side_names = [], {}, []
    pairs_of_sides = (("L", lower.left, upper.left), ("R", lower.right, upper.right)) if not lower.single else (("", lower.codes[0], upper.codes[0]),)
    for name, low_code, up_code in pairs_of_sides:
        centre, why = _arrival_centre(main[up_code], main[low_code], name)
        if why:
            notes.append(why)
        sides.append(CoupledSide(name, low_code, up_code, chains[low_code], chains[up_code], arrival_ms=centre))
        sides_doc[name] = {"lower": low_code, "upper": up_code}
        side_names.append(name)
    table = decay_table(main, upper_codes, decay_ranges)
    bands_of_ring = {}
    decay_input = {}
    for name, low_code, up_code in pairs_of_sides:
        band = ring_band(table["ms"][low_code], table["ms"][up_code], table["freqs_hz"], th.ring_ratio)
        bands_of_ring[name] = band
        decay_input[name] = None if band is None else {"band": band["band"], "gd_at_hz": band["gd_at_hz"]}
    decay_doc = {"table": table, "ring_ratio": th.ring_ratio, "bands": bands_of_ring}
    rule_ms, lower_rule = None, 0.0
    if not lower.single:
        lower_rule = lr_rule_ms(main[lower.left], main[lower.right], lower.role, positions=_rule_positions(main[lower.left], main[lower.right], args.single_point))
        try:
            rule_ms = lr_rule_ms(main[upper.left], main[upper.right], upper.role, positions=_rule_positions(main[upper.left], main[upper.right], args.single_point))
        except JointSearchError as exc:
            if not args.no_lr_offset:
                raise
            notes.append(f"the upper role's L-R rule could not be read: {exc}")
    marks = ("single-point",) if args.single_point else ()
    base_inp = CoupledInput(freqs=freqs, points=points, sides=sides, lp_options=lp_options, hp_options=hp_options, target_db=target, max_ms=space.delay_max_ms, th=th,
                            lr_rule_ms=rule_ms, free_lr=args.no_lr_offset, same_polarity=not args.no_same_polarity, same_family=not args.no_same_family,
                            per_side_corners=args.corners_per_side, leak_on=not args.no_leak, dip_on=not args.no_dip, move=args.move, held_lower=held_lower, held_upper=held_upper,
                            upper_polarity=upper_pol, above=above, bass=hold, decay=decay_input, delay_step_ms=space.delay_step_ms, lower_rule_ms=lower_rule, joint=cls,
                            fs_upper_hz=fs_upper, hp_floor_hz=floor, marks=marks)
    res = scan_coupled(base_inp)
    words_extra = []
    if args.no_lr_offset:
        words_extra.append("--no-lr-offset")
    if args.no_same_polarity:
        words_extra.append("--no-same-polarity")
    if args.no_same_family:
        words_extra.append("--no-same-family")
    if args.corners_per_side:
        words_extra.append("--corners-per-side")
    if args.no_leak:
        words_extra.append("--no-leak")
    if args.no_dip:
        words_extra.append("--no-dip")
    report = _limits_report(th)
    changed = _changed_words(report, words_extra)
    default_inp = _dc_replace(base_inp, th=Limits(), joint=default_cls, free_lr=False, same_polarity=True, same_family=True, per_side_corners=False, leak_on=True, dip_on=True)
    default_run = None if args.no_default_run or not changed else _default_run(scan_coupled, base_inp, default_inp, changed, _best_summary_coupled)
    # cross first: the same search on the raw curves, the same EQ budget on each side's sum
    cross_first = None
    if args.align and not args.no_cross_first:
        cross_first = _cross_first_block(_dc_replace(base_inp, sides=_raw_sides(sides, main, points, args.single_point, held_filters, freqs), bass=None, decay=None), th)
    ctx = {"sides": {name: (low, up) for name, low, up in pairs_of_sides}, "gains": gains, "eq": eq_bands, "held_filters": held_filters}
    top = max(1, int(args.top))
    pub = [_public_coupled(r, ctx) for r in res["rows"]]
    bands = {}
    for r in pub:
        bands.setdefault(r["band"], [])
        if len(bands[r["band"]]) < top:
            bands[r["band"]].append(r)
    conditions = {"move": args.move, "same_polarity": not args.no_same_polarity, "same_family": not args.no_same_family, "per_side_corners": bool(args.corners_per_side),
                  "lr_offset_free": bool(args.no_lr_offset) or rule_ms is None, "lr_rule_ms": None if rule_ms is None else round(rule_ms, 3),
                  "lr_words": ("free (--no-lr-offset)" if args.no_lr_offset else (f"{rule_ms:+.2f} ms within +-{th.lr_tolerance_ms:g} ms" if rule_ms is not None else "one channel per side")),
                  "lower_lr_rule_ms": None if lower.single else round(lower_rule, 3), "hp_floor_hz": round(floor, 1), "front_lp": list(front_lp) if front_lp else None,
                  "shift_range_ms": res["grid"]["shift_range_ms"], "single_point": bool(args.single_point)}
    doc = {"joint": joint.name, "joint_class": joint.cls, "joints_in_stack": stack, "channels": {"lower": list(lower.codes), "upper": list(upper.codes)},
           "sides": sides_doc, "grid": dict(res["grid"], ceiling=GRID_CEILING_PAIRS), "rows": pub, "bands": bands, "rejected": res["rejected"],
           "dropped_options": list(space.dropped), "conditions": conditions, "limits": report, "default_run": default_run, "align": align_doc, "cross_first": cross_first,
           "decay": decay_doc, "fixed": [r["joint"] for r in fixed_rows], "notes": notes + base_inp.notes,
           "note": "This never picks: the table describes, the margin ranks on what survives a head moving, the ear decides and the choice is the tuner's."}
    if default_run:
        best = pub[0] if pub else None
        doc["default_line"] = _default_line(default_run, len(pub), {"margin_oct": best["margin_oct"]} if best else None)
    if space.dropped:
        doc["notes"].append(f"the profile also offers {', '.join(space.dropped)}: the model does not build those exactly, so they were left out of the search")
    if not res["rows"]:
        doc["empty"] = {"said": "no variant came through the limits", "reasons": _reasons_coupled(res["rejected"])}
    text = _render_coupled(doc)
    print(json.dumps(doc, indent=2, ensure_ascii=False) if args.json else text)
    if args.out:
        try:
            project_io.atomic_write_json(os.path.join(args.out, f"joint-{joint.name}.json"), doc, makedirs=True)
            project_io.atomic_write_text(os.path.join(args.out, f"joint-{joint.name}.txt"), text + "\n", makedirs=True)
        except OSError as exc:
            raise JointSearchError(f"--out {args.out}: the table above was not written: {exc}") from None
    return 0


def _ring_freqs(band):
    """1/3-octave centres inside `band`, Hz: the bands the decay report reads."""
    lo, hi = band
    n = int(math.floor(math.log2(hi / lo) * 3.0 + 1e-9))
    return tuple(round(lo * 2.0 ** (k / 3.0), 1) for k in range(n + 1))


def _raw_sides(sides, curves, points, single, held_filters, freqs):
    """The sides without `--align`: the raw curves and the held filters only."""
    out = []
    for side in sides:
        lower = _points_of(curves[side.lower_code], side.lower_code, points, single, "front")
        upper = _points_of(curves[side.upper_code], side.upper_code, points, single, "front")
        hp = held_filters.get(side.lower_code, {}).get("hp")
        if hp:
            lower = lower * dsp_math.xo_response(freqs, hp[2], hp[1], "hp", hp[0])
        out.append(CoupledSide(side.name, side.lower_code, side.upper_code, lower, upper, arrival_ms=side.arrival_ms))
    return out


def _cross_first_block(inp, th):
    """The same search on the raw drivers, the best row per crossing band, and the same EQ budget on each side's sum (cuts only, the level kept
    above the joint: `wm_flat.py:115-130`). What it reports next to the aligned rows: rms and dip before and after."""
    res = scan_coupled(_dc_replace(inp, th=_dc_replace(th, rank=th.rank)))
    if not res["rows"]:
        return {"rows": None}
    f = np.asarray(inp.freqs, float)
    cls = inp.joint
    kernel = _third_oct(f)
    out = []
    seen = set()
    for row in res["rows"]:
        if row["band"] in seen:
            continue
        seen.add(row["band"])
        rms_before, rms_after, dip_before, dip_after, cuts = [], [], [], [], 0
        for side in inp.sides:
            s = row["sides"][side.name]
            h = dsp_math.xo_response(f, s["lp"][2], s["lp"][1], "lp", s["lp"][0]) * side.lower \
                + (-1.0 if s["polarity"] == "INV" else 1.0) * dsp_math.xo_response(f, s["hp"][2], s["hp"][1], "hp", s["hp"][0]) * side.upper * np.exp(-2j * np.pi * f * s["shift_ms"] * 1e-3)
            level = _power_db(kernel @ np.mean(np.abs(h) ** 2, 0))
            gain, bands = _fit_flat(level, inp.target_db, f, cls.rms_band, cls.dip_fit_band, gain_max=0.0, cuts=th.align_cuts, cut_max=th.align_cut_max_db)
            eq = _eq_response(f, bands, gain)
            trim = _passband_db(h, f, cls.dip_fit_band) - _passband_db(h * eq, f, cls.dip_fit_band)
            eq = eq * 10.0 ** (trim / 20.0)
            cuts = max(cuts, len(bands))
            for label, curve in (("before", h), ("after", h * eq)):
                lvl = _power_db(kernel @ np.mean(np.abs(curve) ** 2, 0))
                dev = lvl - float(np.mean((lvl - inp.target_db)[(f >= cls.dip_fit_band[0]) & (f <= cls.dip_fit_band[1])])) - inp.target_db
                rms_val = float(np.sqrt(np.mean(dev[(f >= cls.rms_band[0]) & (f <= cls.rms_band[1])] ** 2)))
                dip_val = float(dev[(f >= cls.dip_band[0]) & (f <= cls.dip_band[1])].min())
                if label == "before":
                    rms_before.append(rms_val), dip_before.append(dip_val)
                else:
                    rms_after.append(rms_val), dip_after.append(dip_val)
        out.append({"band": row["band"], "lp": row["sides"][inp.sides[0].name]["lp"], "hp": row["sides"][inp.sides[0].name]["hp"],
                    "no_eq_rms_db": round(max(rms_before), 2), "with_eq_rms_db": round(max(rms_after), 2),
                    "no_eq_dip_db": round(min(dip_before), 2), "with_eq_dip_db": round(min(dip_after), 2), "cuts": cuts})
    return {"rows": out}


def _read_target(path, freqs):
    """The target curve on the grid, or a refusal in words."""
    if not os.path.isfile(path):
        raise JointSearchError(f"{path}: the target curve file is not there")
    try:
        house = target_bands.HouseCurve.from_file(path)
    except (OSError, ValueError) as exc:
        raise JointSearchError(f"{path}: the target curve cannot be read: {exc}") from None
    if not house.f:
        raise JointSearchError(f"{path}: no parseable line (frequency and level) in the target curve file")
    target = np.array([house.at(float(x)) for x in freqs])
    if not np.isfinite(target).all():
        raise JointSearchError(f"{path}: the target curve holds a number that is not finite")
    return target


def _load_capture(args, project_dir, codes, lower_codes, freqs, level_branch, process_mod):
    """The capture: `(main curves, lower curves, notes)`. `lower_codes` may come from another session (`--sub-solos`, `--sub-ver`), levelled
    over `--level-step`."""
    if args.level_step:
        band = _bounds(args.level_step, "--level-step")
        if band[0] < freqs[0] or band[1] > freqs[-1] or np.count_nonzero((freqs >= band[0]) & (freqs <= band[1])) < 2:
            raise JointSearchError(f"--level-step {args.level_step} is outside the search grid {freqs[0]:.0f}-{freqs[-1]:.0f} Hz: "
                                   "the control band is levelled over the points it can read")
    two_sessions = bool((args.sub_solos and args.sub_solos != args.solos) or (args.sub_ver and args.sub_ver != args.ver))
    if two_sessions and not args.level_step:
        raise JointSearchError("the sub comes from another capture session: its level would read as the driver's imbalance; "
                               "--level-step LO:HI names the control band the sessions are levelled over")
    record = None
    if args.rew:
        try:
            record = process_mod.Process(os.path.join(project_dir, "process")).protective_record_for(args.ver)
        except process_mod.ProcessError as exc:
            raise JointSearchError(f"the capture record of series {args.ver}: {exc}") from None
    sources = {"solos": args.solos, "ver": args.ver, "api": None, "record": record}
    main, notes = load_channels(list(codes) + ([] if two_sessions else list(lower_codes)), freqs, **sources)
    lower_curves = main
    if two_sessions:
        sub_record = None
        if args.rew and args.sub_ver:
            try:
                sub_record = process_mod.Process(os.path.join(project_dir, "process")).protective_record_for(args.sub_ver)
            except process_mod.ProcessError as exc:
                raise JointSearchError(f"the capture record of series {args.sub_ver}: {exc}") from None
        sub_side, more = load_channels(list(codes) + list(lower_codes), freqs, solos=args.sub_solos or args.solos,
                                       ver=args.sub_ver or args.ver, api=None, record=sub_record)
        notes += [n for n in more if n not in notes]
        step = _level_step_db(sub_side, main, level_branch, freqs, _bounds(args.level_step, "--level-step"))
        factor = 10.0 ** (step / 20.0)
        lower_curves = {c: {"tripod": None if sub_side[c]["tripod"] is None else sub_side[c]["tripod"] * factor,
                            "points": {p: h * factor for p, h in sub_side[c]["points"].items()},
                            "info": sub_side[c]["info"]} for c in lower_codes}
        notes.append(f"the sub's session levelled by {step:+.1f} dB over {args.level_step} Hz")
    for code in list(codes) + list(lower_codes):
        have = lower_curves[code] if code in lower_codes else main[code]
        if have["tripod"] is None and not have["points"]:
            raise JointSearchError(f"{code}: no solo found")
    return main, lower_curves, notes


def _cli(argv=None):
    """`_main`'s work; its refusals are `_main`'s to say."""
    import argparse
    ap = argparse.ArgumentParser(description="the joint-by-joint search: the bass joint and the woofer-mid joint, described, not chosen")
    ap.add_argument("--project", required=True, metavar="DIR")
    ap.add_argument("--house", required=True, metavar="FILE", help="the target curve (REW text)")
    ap.add_argument("--solos", metavar="DIR", help="v7 impulse files, `m_L.json` and `m_L-p1.json`")
    ap.add_argument("--rew", action="store_true", help="read live REW: `--ver N` is the series")
    ap.add_argument("--ver", help="series number for --rew")
    ap.add_argument("--sub-solos", metavar="DIR", help="the sub from another capture session (needs --level-step)")
    ap.add_argument("--sub-ver", help="the sub's series in REW when it differs (needs --level-step)")
    ap.add_argument("--level-step", metavar="LO:HI", help="the control band two capture sessions are levelled over")
    ap.add_argument("--single-point", action="store_true", help="run on the centre point; needs the person's recorded decision")
    ap.add_argument("--joint", default="bass", help="which joint: bass, woofer-midrange (the build's joints)")
    ap.add_argument("--lp-bounds", metavar="LO:HI", help="the lower driver's LP corners, Hz")
    ap.add_argument("--hp-bounds", metavar="LO:HI", help="the upper driver's HP corners, Hz")
    ap.add_argument("--gain", metavar="LO:HI:STEP", help="sub level relative to the front, dB (the bass joint)")
    ap.add_argument("--no-lr-offset", action="store_true", help="stage condition off: search the L-R offset of the upper role freely")
    ap.add_argument("--no-leak", action="store_true", help="condition off: do not reject the leak")
    ap.add_argument("--no-dip", action="store_true", help="condition off: do not reject a dip under the target")
    ap.add_argument("--no-same-polarity", action="store_true", help="stage condition off: L and R of the upper role may differ in polarity")
    ap.add_argument("--no-same-family", action="store_true", help="stage condition off: L and R may differ in filter family and order")
    ap.add_argument("--corners-per-side", action="store_true", help="L and R may have different corners (same family and order unless --no-same-family)")
    ap.add_argument("--front-lp", nargs=3, metavar=("FAMILY", "ORDER", "HZ"),
                    help="the upper role's low-pass, in the model (its phase moves the delay)")
    ap.add_argument("--allow-large-grid", action="store_true",
                    help=f"over {GRID_CEILING_PAIRS} filter pairs x L-R offsets, run anyway: time grows with the combinations, "
                         "memory with the filter options (about 11 kB each), the row buffer stays bounded")
    ap.add_argument("--top", type=int, default=TOP_DEFAULT, help="rows per crossing band")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out", metavar="DIR", help="write the table and the JSON here")
    # every method threshold, a default until changed: only what the hardware cannot do and driver safety refuse
    ap.add_argument("--phase-window", dest="phase_window_deg", type=float, metavar="DEG", help=f"the ±band of the in-phase run (default {PHASE_WINDOW_DEG:g})")
    ap.add_argument("--leak-near", dest="leak_near_db", type=float, metavar="DB", help=f"bass: the sub's leak at the near frequency (default {LEAK_NEAR_DB:g})")
    ap.add_argument("--leak-far", dest="leak_far_db", type=float, metavar="DB", help=f"bass: the sub's leak over the far band (default {LEAK_FAR_DB:g})")
    ap.add_argument("--leak-octave", dest="leak_octave_db", type=float, metavar="DB", help=f"above the bass: each driver under the other an octave out (default {LEAK_OCTAVE_DB:g})")
    ap.add_argument("--dip-limit", dest="dip_limit_db", type=float, metavar="DB", help=f"reject a sum under the target by more than this (default {DIP_LIMIT_DB:g})")
    ap.add_argument("--delay-tolerance", dest="delay_tolerance_ms", type=float, metavar="MS", help=f"the margin's reach, a head moving (default {DELAY_TOLERANCE_MS:g})")
    ap.add_argument("--lr-tolerance", dest="lr_tolerance_ms", type=float, metavar="MS", help=f"the L-R rule's tolerance (default {LR_OFFSET_TOLERANCE_MS:g})")
    ap.add_argument("--lr-crossing-oct", dest="lr_crossing_oct", type=float, metavar="OCT", help=f"L and R acoustic crossings within this (default {LR_CROSSING_OCT:.2f})")
    ap.add_argument("--shortlist", dest="shortlist", type=int, metavar="N", help=f"per crossing band (bass default {SHORTLIST_PER_BAND}, per side above it {SHORTLIST_COUPLED_PER_BAND})")
    ap.add_argument("--band-width", dest="band_width_oct", type=float, metavar="OCT", help="the crossing-band width (bass default 0.25, above it 0.5)")
    ap.add_argument("--corner-step", dest="corner_step_oct", type=float, metavar="OCT", help=f"the corner grid (default {CORNER_STEP_OCT:.3f})")
    ap.add_argument("--rank", dest="rank", choices=("margin", "worst", "median", "loss"), help="the first ranking key (default margin, the width that survives a moving head)")
    ap.add_argument("--sub-one-point-max", dest="sub_one_point_max_hz", type=float, metavar="HZ", help=f"a sub measured once is scored only below this crossing (default {SUB_ONE_POINT_MAX_HZ:g})")
    ap.add_argument("--shift-span", dest="shift_span_ms", type=float, metavar="MS", help=f"the upper's delay search, each way around the raw arrival (default {SHIFT_SPAN_MS:g})")
    ap.add_argument("--bass-drop", dest="bass_drop_oct", type=float, metavar="OCT", help=f"the most the bass joint below may lose, worst and median (default {BASS_RESCORE_DROP_OCT:g})")
    ap.add_argument("--ring-ratio", dest="ring_ratio", type=float, metavar="X", help=f"the lower driver ringing this many times longer is named in the decay report (default {RING_RATIO:g})")
    ap.add_argument("--crossing-window", dest="crossing_window", metavar="LO:HI", help="where the acoustic crossing is looked for and which bands are listed (default the joint's)")
    ap.add_argument("--dip-band", dest="dip_band", metavar="LO:HI", help="the band the dip is read in (default the joint's)")
    ap.add_argument("--no-default-run", action="store_true", help="do not rerun the same grid on the defaults to show what the changed limits did")
    # above the bass
    ap.add_argument("--fixed", action="append", metavar="FILE[@N]", help="a row held from an earlier joint's output (repeatable); a document's row is named @N, from 1")
    ap.add_argument("--move", choices=("upper", "lower"), default="upper", help="which group's delay moves: upper (default, the mid and everything above it) or lower (the woofer)")
    ap.add_argument("--align", action="store_true", help="flatten first: gain up, cuts, the channel back to its passband level")
    ap.add_argument("--align-band", action="append", metavar="ROLE=FITLO:FITHI/ANCHLO:ANCHHI", help="the fit and anchor bands of a role, over the table")
    ap.add_argument("--align-gain-max", dest="align_gain_max_db", type=float, metavar="DB", help=f"--align gain up (default {ALIGN_GAIN_MAX_DB:g})")
    ap.add_argument("--align-cuts", dest="align_cuts", type=int, metavar="N", help=f"--align cuts per channel (default {ALIGN_CUTS})")
    ap.add_argument("--align-cut-max", dest="align_cut_max_db", type=float, metavar="DB", help=f"--align depth of each cut (default {ALIGN_CUT_MAX_DB:g})")
    ap.add_argument("--no-cross-first", action="store_true", help="--align: skip the raw-drivers comparison")
    args = ap.parse_args(argv)
    th = _limits_of(args)
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
    state_dir = os.path.join(_HERE, "state")
    if state_dir not in sys.path:
        sys.path.insert(0, state_dir)
    import process as _process
    if args.joint == "woofer-midrange":
        if args.gain:
            raise JointSearchError("--gain is the sub level of the bass joint; the woofer-mid joint searches no level (use --align to flatten)")
        return _run_coupled(args, space, channels, stack, th, _process)
    if args.joint != "bass":
        raise JointSearchError(f"joint {args.joint!r}: this build searches the bass and woofer-midrange joints (--joint bass or --joint woofer-midrange)")
    for flag, value in (("--fixed", args.fixed), ("--align", args.align), ("--align-band", args.align_band), ("--no-cross-first", args.no_cross_first),
                        ("--no-same-polarity", args.no_same_polarity), ("--no-same-family", args.no_same_family), ("--corners-per-side", args.corners_per_side)):
        if value:
            raise JointSearchError(f"{flag} belongs to the joints above the bass (--joint woofer-midrange)")
    if args.move != "upper":
        raise JointSearchError("--move belongs to the joints above the bass (--joint woofer-midrange)")
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
    default_cls = _dc_replace(cls, lp_bounds=lp_bounds, hp_bounds=hp_bounds)
    cls = _dc_replace(cls, lp_bounds=lp_bounds, hp_bounds=hp_bounds, crossing_window=th.crossing_window or cls.crossing_window, dip_band=th.dip_band or cls.dip_band)
    lp_corners = corner_grid(lp_bounds, space.xo, th.corner_step_oct)
    hp_corners = corner_grid(hp_bounds, space.xo, th.corner_step_oct)
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
    if args.single_point and not _single_point_decided(_process, project_dir):
        raise JointSearchError("--single-point needs the person's recorded decision: the session says the limits, the person "
                               f"decides, and it is recorded in these words: `process.py {project_dir} decision "
                               f"\"{SINGLE_POINT_DECISION}\" \"<the person's words>\"`")
    freqs = P.grid(cls.grid_hz[0], cls.grid_hz[1], GRID_PPO)
    target = None
    upper_codes, lower_codes = list(upper.codes), list(joint.lower.codes)
    main, lower_curves, notes = _load_capture(args, project_dir, upper_codes, lower_codes, freqs, upper, _process)
    target = _read_target(args.house, freqs)
    marks = ("single-point",) if args.single_point else ()
    inp = _build_bass_input(joint, curves=main, lower_curves=lower_curves, freqs=freqs, single_point=args.single_point,
                            lp_options=lp_options, hp_options=hp_options, gains=tuple(gains), max_ms=space.delay_max_ms,
                            gain_range=space.gain_range, target_db=target, free_offset=free, hp_floor_hz=floor,
                            fs_upper_hz=fs_upper, xo=space.xo, cls=cls, marks=marks, delay_step_ms=space.delay_step_ms,
                            gain_step_db=space.gain_step_db, leak_on=not args.no_leak, dip_on=not args.no_dip, front_lp=front_lp)
    inp.th, inp.front_lp = th, front_lp
    if space.dropped:
        notes.append(f"the profile also offers {', '.join(space.dropped)}: the model does not build those exactly, so they were left "
                     "out of the search")
    if len(stack) > 1 and front_lp is None:
        notes.append(f"the {upper.role}'s low-pass is not in this model yet (the joint above it has no result): the delay will shift once "
                     f"the {upper.role} gets it, and it is re-scored by the next joint (--front-lp FAMILY ORDER HZ to model it now)")
    res = scan_bass(inp)
    report = _limits_report(th)
    changed = _changed_words(report, [flag for flag, on in (("--no-lr-offset", args.no_lr_offset), ("--no-leak", args.no_leak), ("--no-dip", args.no_dip)) if on])
    default_inp = _dc_replace(inp, th=Limits(), joint=default_cls, free_lr_offset=False, leak_on=True, dip_on=True)
    default_run = None if args.no_default_run or not changed else _default_run(scan_bass, inp, default_inp, changed, _best_summary_bass)
    top = max(1, int(args.top))

    def published(row):
        pub = _public(row)
        pub["delays_ms"] = _channel_delays(pub["ta_ms"], joint.lower, upper)
        pub["joint"] = joint.name
        pub["channels"] = _channel_row(pub, joint.lower, upper)
        return pub
    bands = {k: [published(r) for r in v[:top]] for k, v in res["bands"].items()}
    grid = dict(res["grid"], ceiling=GRID_CEILING_PAIRS)
    doc = {"joint": joint.name, "joint_class": joint.cls, "joints_in_stack": stack,
           "channels": {"lower": lower_codes, "upper": upper_codes},
           "grid": grid, "rows": [published(r) for r in res["rows"]], "bands": bands, "rejected": res["rejected"],
           "dropped_options": list(space.dropped),
           "conditions": {"lr_offset_ms": 0.0 if upper.single else round(_snap_ms(inp.lr_rule_ms, inp.delay_step_ms), 3),
                          "lr_rule_ms": 0.0 if upper.single else round(inp.lr_rule_ms, 3),
                          "lr_offset_tolerance_ms": th.lr_tolerance_ms, "delay_tolerance_ms": th.delay_tolerance_ms,
                          "lr_offset_held": (not free) and (not upper.single),
                          "lr_offset_free": bool(free) and not upper.single,
                          "upper_single": upper.single,
                          "lower_lr_offset_ms": None if inp.lower_offset_ms is None else round(inp.lower_offset_ms, 3),
                          "lower_lr_rule_ms": None if inp.lower_rule_ms is None else round(inp.lower_rule_ms, 3),
                          "front_lp": list(front_lp) if front_lp else None,
                          "sub_one_point": inp.sub_one_point, "hp_floor_hz": round(floor, 1)},
           "limits": report, "default_run": default_run,
           "notes": notes + inp.notes, "note": "This never picks: the table describes, the margin ranks on what survives a head moving, the ear decides and the choice "
                   "is the tuner's."}
    if default_run:
        doc["default_line"] = _default_line(default_run, len(res["rows"]), _best_summary_bass(res["rows"][0]) if res["rows"] else None)
    if not res["rows"]:
        doc["empty"] = {"said": "no variant came through the limits", "reasons": _reasons(res["rejected"])}
    text = render(doc)
    print(json.dumps(doc, indent=2, ensure_ascii=False) if args.json else text)
    if args.out:
        try:
            project_io.atomic_write_json(os.path.join(args.out, f"joint-{joint.name}.json"), doc, makedirs=True)
            project_io.atomic_write_text(os.path.join(args.out, f"joint-{joint.name}.txt"), text + "\n", makedirs=True)
        except OSError as exc:
            raise JointSearchError(f"--out {args.out}: the table above was not written: {exc}") from None
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
    """Has the person decided to run on one point? The latest `user_decision` whose question or answer says both that the nine points
    were skipped and that the joints run on one point (`SINGLE_POINT_*`) decides: its answer is not a bare no to the question that
    carried them. Asked for the positions, the bare word "position": neither is that decision (`process._positions_asked` is another gate)."""
    try:
        events = process_mod.Process(os.path.join(project_dir, "process"))._events(kinds=(process_mod.EV_USER_DECISION,))
    except process_mod.ProcessError as exc:
        raise JointSearchError(f"the project's decisions cannot be read: {exc}") from None
    for event in reversed(events):
        question = " ".join(str(event.get("question", "")).lower().split())
        answer = " ".join(str(event.get("answer", "")).lower().split())
        said = f"{question} {answer}"
        if SINGLE_POINT_SKIP_WORDS not in said or SINGLE_POINT_ONE_WORDS not in said:
            continue
        return SINGLE_POINT_SKIP_WORDS in answer or (answer.split() or [""])[0].rstrip(".,!") not in _NO_WORDS
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
    assert all(r["margin_oct"] <= top["margin_oct"] for r in rows), top["margin_oct"]
    assert all(_row_key(r) < _row_key(top) for r in better_loss), [(r["margin_oct"], top["margin_oct"]) for r in better_loss][:3]
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
        for value in (f"{row['sub_gain_db']:+.2f}", f"{row['front_gain_db']:+.2f}", f"{row['delays_ms']['sw']:.3f}",
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


def _check_leak_moves_with_the_crossing():
    """I4: a crossing near 120 Hz with a sub that falls away fast above it is no leak: the 100 and 125-200 Hz were one car's, and the
    limit moves up with the crossing. The same pair with a gentle low-pass is rejected at the frequencies moved up."""
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


# -------- the replay's round (#210): the leak as the run validated it, the ranking on a delay a head survives, the review's small findings
def _run_shape(lo, hi):
    """A sub's phase against its pair's filters: in phase over a known run, 90 degrees out everywhere else."""
    return lambda f: np.where((f >= lo) & (f <= hi), 0.0, 90.0)


def _knife_shape(lo, split, hi):
    """In tolerance by a hair over `lo`..`hi`: +29.9 degrees below `split`, -29.9 above it, 90 out. Moving the delay either way
    takes one side past the 30 degrees, so the worst point is widest at one delay only."""
    return lambda f: np.where((f >= lo) & (f < split), 29.9, np.where((f >= split) & (f <= hi), -29.9, 90.0))


def _two_pair_input(shapes):
    """Two filter pairs, A = LR36 at 56 Hz and B = LR36 at 125 Hz, each with its own phase plan per point: flat drivers, the sub's
    phase below 100 Hz cancels A's filters and adds `shapes["A"][p]`, above it B's and `shapes["B"][p]`. Each pair's numbers are read
    off its plan; a mixed pair (a corner of each) is in the grid and takes no part in what the checks ask."""
    a, b = ("LR", 36, 56.0), ("LR", 36, 125.0)
    n = len(shapes["A"])
    inp = _planted_input(lp=a, hp=a, fams=[("LR", 36)], lp_corners=(56, 125), hp_corners=(56, 125), n_points=n, leak_on=False,
                         dip_on=False, single_upper=True)
    inp.gains_db = (2.0,)
    f = inp.freqs

    def own(pair):
        return np.degrees(np.angle(dsp_math.xo_response(f, pair[2], pair[1], "hp", pair[0]))
                          - np.angle(dsp_math.xo_response(f, pair[2], pair[1], "lp", pair[0])))

    inp.upper_l = np.ones((n, len(f)), complex)
    inp.ref_l = inp.upper_l[0]
    for p in range(n):
        phase = np.where(f < 100.0, own(a) + shapes["A"][p](f), own(b) + shapes["B"][p](f))
        inp.lower[p] = 10.0 ** (-2.0 / 20.0) * np.exp(1j * np.radians(phase))
    inp.ref_lower = inp.lower[0]
    return inp, a, b


def _row_of(rows, pair):
    return next(r for r in rows if tuple(r["lp"]) == tuple(pair) and tuple(r["hp"]) == tuple(pair))


def _check_leak_from_the_validated_limits():
    """The leak limit is the run's own: -24 dB at 100 Hz and -30 dB over 125-200 Hz, judged there for a crossing at or below 65 Hz,
    moved up by crossing/65 above it. LR36 at 56 Hz is -21 dB at 1.5x its crossing and -30 dB at 100 Hz: the validated limit passes
    it, the relative one dropped it. Each row's two readings are the gap at those frequencies, read independently."""
    def read(inp, row):
        f = inp.freqs
        lp = dsp_math.xo_response(f, row["lp"][2], row["lp"][1], "lp", row["lp"][0])
        hp = dsp_math.xo_response(f, row["hp"][2], row["hp"][1], "hp", row["hp"][0])
        gap = _db(inp.ref_lower * lp * 10.0 ** (row["sub_rel_db"] / 20.0)) - _db(_front_sum(inp.ref_l, inp.ref_r, f, row["lr_offset_ms"]) * hp)
        scale = max(1.0, row["crossing_hz"] / 65.0)
        return float(gap[int(np.argmin(np.abs(f - 100.0 * scale)))]), float(gap[(f >= 125.0 * scale) & (f <= 200.0 * scale)].max())

    low = ("LR", 36, 56.0)
    inp = _planted_input(lp=low, hp=low, fams=[("LR", 36)], lp_corners=(56,), hp_corners=(56,), dip_on=False)
    rows = [r for r in scan_bass(inp)["rows"] if r["sub_rel_db"] == 2.0]
    assert rows and rows[0]["crossing_hz"] <= 65.0, "LR36 at 56 Hz passes the run's limit and came back with no row"
    high = ("LR", 48, 113.0)
    moved = _planted_input(lp=high, hp=high, fams=[("LR", 48)], lp_corners=(113,), hp_corners=(113,), dip_on=False, delay_ms=1.0)
    rows_high = [r for r in scan_bass(moved)["rows"] if r["crossing_hz"] > 65.0]
    assert rows_high, "no row with a crossing above 65 Hz"
    for source, row in [(inp, r) for r in rows] + [(moved, r) for r in rows_high]:
        near, far = read(source, row)
        assert abs(row["leak_near_db"] - near) < 1e-3 and abs(row["leak_far_db"] - far) < 1e-3, \
            (row["crossing_hz"], row["leak_near_db"], near, row["leak_far_db"], far)
    gentle = ("LR", 24, 56.0)                  # -20 dB at 100 Hz, over the limit at the run's own frequency
    res = scan_bass(_planted_input(lp=gentle, hp=gentle, fams=[("LR", 24)], lp_corners=(56,), hp_corners=(56,), dip_on=False))
    assert not [r for r in res["rows"] if r["sub_rel_db"] == 2.0] and res["rejected"].get("leak", 0) > 0, res["rejected"]


def _check_margin_ranks_past_a_knife_edge():
    """A band that holds at one delay only does not survive a head moving: pair A is 1.66 oct wide at one delay and 0.87 oct either
    side of it; pair B is 1.04 oct at every delay near. By the peak A leads; by the margin B does, and A's delay moves off the knife."""
    shape_a = _knife_shape(30.0, 52.0, 95.0)
    inp, a, b = _two_pair_input({"A": [shape_a] * 3, "B": [_run_shape(102.0, 210.0)] * 3})
    rows = scan_bass(inp)["rows"]
    knife, broad = _row_of(rows, a), _row_of(rows, b)
    step = math.log2(inp.freqs[1] / inp.freqs[0])
    assert abs(broad["margin_oct"] - math.log2(210.0 / 102.0)) <= 3 * step, broad["margin_oct"]
    assert abs(knife["margin_oct"] - math.log2(95.0 / 52.0)) <= 3 * step, knife["margin_oct"]
    assert knife["margin_oct"] < broad["margin_oct"], (knife["margin_oct"], broad["margin_oct"])
    assert rows.index(broad) < rows.index(knife), "the pair with the better margin ranks first"
    assert knife["delay_ms"] >= DELAY_TOLERANCE_MS - 1e-9, knife["delay_ms"]
    # the replay's two readings, by the arithmetic of the margin: the delays within the tolerance of the middle one
    for widths, want in (((0.58, 0.98, 0.57), 0.57), ((0.86, 1.17, 0.95), 0.86)):
        grid = np.array([10.65, 10.70, 10.75])
        assert abs(float(_delay_margins(grid, np.array(widths), np.array([1]))[0]) - want) < 1e-9, (widths, want)


def _check_margin_tolerance_reaches_past_a_coarse_step():
    """The tolerance is a head moving, not the DSP's step: on a 0.25 ms delay step the margin still looks at +-0.10 ms, not at the
    delay alone, and the delay it gives stays on the step."""
    inp, a, _b = _two_pair_input({"A": [_knife_shape(30.0, 52.0, 95.0)] * 3, "B": [_run_shape(102.0, 210.0)] * 3})
    inp.delay_step_ms = 0.25
    knife = _row_of(scan_bass(inp)["rows"], a)
    step = math.log2(inp.freqs[1] / inp.freqs[0])
    assert knife["margin_oct"] <= math.log2(95.0 / 52.0) + 3 * step, knife["margin_oct"]
    assert abs(knife["delay_ms"] / 0.25 - round(knife["delay_ms"] / 0.25)) < 1e-6, knife["delay_ms"]


def _check_worst_ranks_before_median():
    """Two pairs: A has the wider median and the narrower worst, B the reverse. Worst comes first, so B leads."""
    wide_median = [_run_shape(45.0, 70.0), _run_shape(35.0, 90.0), _run_shape(30.0, 95.0)]
    even = [_run_shape(102.0, 180.0)] * 3
    inp, a, b = _two_pair_input({"A": wide_median, "B": even})
    rows = scan_bass(inp)["rows"]
    first, second = _row_of(rows, b), _row_of(rows, a)
    assert second["width_median_oct"] > first["width_median_oct"] + 0.3, (second["width_median_oct"], first["width_median_oct"])
    assert second["width_worst_oct"] < first["width_worst_oct"] - 0.1, (second["width_worst_oct"], first["width_worst_oct"])
    assert rows.index(first) < rows.index(second), "worst before median"
    # the tie-breaks: margin, then the worst at that delay, then the median
    def row(margin, worst, median):
        return {"margin_oct": margin, "width_worst_oct": worst, "width_median_oct": median, "loss_median_db": -1.0, "dip_median_db": -1.0}
    ranked = sorted((row(0.8, 0.9, 1.0), row(0.8, 1.1, 0.7), row(0.9, 0.9, 0.5)), key=_row_key, reverse=True)
    assert [(r["margin_oct"], r["width_worst_oct"]) for r in ranked] == [(0.9, 0.9), (0.8, 1.1), (0.8, 0.9)], ranked


#: The smallest grid that still has rows: for the checks about what is said, not what ranks.
_SMALL = ["--lp-bounds", "56:63", "--hp-bounds", "71:80", "--gain", "6:8:2"]


_STEP_0_1 = {"dsp_profile": {"name": "X", "dsp_processing_rate_hz": 96000, "delay": {"max_ms": 20.0, "step_ms": 0.1},
                             "channel_gain": {"range_db": [-30.0, 5.0]},
                             "groups": [{"id": "physical_outputs", "crossover_filters": {
                                 "corner_freq_range_hz": [20.0, 20480.0], "corner_freq_step_hz": 1.0,
                                 "types": {"LR": {"orders_db_per_oct": [24, 36]}, "BW": {"orders_db_per_oct": [24]}}}}]}}


def _check_header_prints_the_scored_offset():
    """The header and `lr_offset_ms` carry the offset the search scored, on the DSP's step; the raw rule is a field of its own. L
    later by 1.04 ms on a 0.1 ms step scores -1.00, not -1.04. A stereo sub the same."""
    top, done = _tmp()
    try:
        roles = {"sw-L": "sub", "sw-R": "sub", "w-L": "woofer", "w-R": "woofer"}
        argv, _, _, _ = _solo_project(top, roles=roles, profile=_STEP_0_1, at={"sw-L": 192, "sw-R": 96, "w-L": 200, "w-R": 100},
                                      points={"w-L": POSITIONS, "w-R": POSITIONS})
        cond = _doc(argv + _SMALL)["conditions"]
        assert cond["lr_offset_ms"] == -1.0 and abs(cond["lr_rule_ms"] - (-100.0 / 96.0)) < 0.03, cond
        assert abs(cond["lower_lr_offset_ms"] / 0.1 - round(cond["lower_lr_offset_ms"] / 0.1)) < 1e-6, cond
        assert cond["lower_lr_rule_ms"] != cond["lower_lr_offset_ms"], cond
        rc, text, err = _run(argv + _SMALL)
        assert rc == 0, err[-300:]
        head = text.splitlines()[0]
        assert "L-R offset held at -1.00 ms" in head and f"{_doc(argv + _SMALL)['conditions']['lr_rule_ms']:+.2f} ms" not in head, head
    finally:
        done()


def _check_single_point_latest_decision_decides():
    """The person's latest matching decision stands, and "не", "not", "don't" read as a no, as "ні" does."""
    proc = _process_module()
    top, done = _tmp()
    try:
        argv, proj, _, _ = _solo_project(top, points=None)
        cmd = argv + _SMALL + ["--single-point"]
        p = proc.Process(os.path.join(proj, "process"))
        for answer, want in (("так, на одній", 0), ("ні, передумав", 3), ("так", 0), ("не треба", 3), ("так", 0), ("not this time", 3),
                             ("так", 0), ("don't", 3), ("так", 0), ("Don’t do it", 3), ("так", 0)):
            p.record_decision(_DECISION_WORDS, answer)
            rc, _out, err = _run(cmd)
            assert rc == want, (answer, rc, want, err[-200:])
    finally:
        done()


def _check_bad_out_is_a_refusal_after_the_table():
    """A `--out` that cannot be written: the table is printed first and the failure is the one line, exit 3, not a traceback."""
    top, done = _tmp()
    try:
        argv, _, _, _ = _solo_project(top)
        blocked = os.path.join(top, "afile")
        with open(blocked, "w", encoding="utf-8") as fh:
            fh.write("in the way\n")
        rc, out, err = _run(argv + _SMALL + ["--out", os.path.join(blocked, "out")])
        refusal = [ln for ln in err.strip().splitlines() if ln.startswith("refusing:")]
        assert rc == 3 and "the choice is the tuner's" in out and len(refusal) == 1 and "--out" in refusal[0], (rc, out[-200:], err[-300:])
    finally:
        done()


def _check_gains_print_on_a_quarter_step():
    """A 0.25 dB gain step: the table prints the quarter, .2f, and a gain that fits it is keyable as printed."""
    prof = json.loads(json.dumps(_STEP_0_1))
    prof["dsp_profile"]["channel_gain"]["step_db"] = 0.25
    top, done = _tmp()
    try:
        argv, _, _, _ = _solo_project(top, profile=prof)
        tiny = ["--lp-bounds", "56:71", "--hp-bounds", "56:80", "--gain", "2.25:6.25:2"]
        doc = _doc(argv + tiny)
        assert doc["rows"], doc["rejected"]
        rc, text, err = _run(argv + tiny)
        assert rc == 0, err[-300:]
        row = doc["rows"][0]
        line = next(ln for ln in text.splitlines() if ln.strip().startswith(_filter_name(row["lp"])) and _filter_name(row["hp"]) in ln)
        fields = line.split()
        for value in (f"{row['sub_gain_db']:+.2f}", f"{row['front_gain_db']:+.2f}"):
            assert value in fields, (value, line)
    finally:
        done()


def _check_front_lp_note_names_the_role():
    """The note about the next joint's low-pass names the role the stack has: a midrange above the sub is not called a woofer."""
    top, done = _tmp()
    try:
        roles = {"sw": "sub", "m-L": "midrange", "m-R": "midrange", "tw-L": "tweeter", "tw-R": "tweeter"}
        argv, _, _, _ = _solo_project(top, roles=roles, at={"sw": 96, "m-L": 200, "m-R": 100, "tw-L": 100, "tw-R": 100},
                                      points={"m-L": POSITIONS, "m-R": POSITIONS})
        doc = _doc(argv + ["--lp-bounds", "56:71", "--hp-bounds", "80:100", "--gain", "2:8:2"])
        said = [n for n in doc["notes"] if "re-scored" in n]
        assert said and "midrange's low-pass" in said[0] and "woofer" not in said[0], doc["notes"]
    finally:
        done()


def _check_stereo_sub_offset_is_low_confidence():
    """A stereo sub's L-R offset is read at 30-100 Hz, which read a planted 1 ms as about 0.4 ms: every run with a stereo sub says it
    is low-confidence and must be checked; a run with a single sub says nothing."""
    top, done = _tmp()
    try:
        roles = {"sw-L": "sub", "sw-R": "sub", "w-L": "woofer", "w-R": "woofer"}
        argv, _, _, _ = _solo_project(top, roles=roles, at={"sw-L": 192, "sw-R": 96, "w-L": 200, "w-R": 100},
                                      points={"w-L": POSITIONS, "w-R": POSITIONS})
        said = [n for n in _doc(argv + _SMALL)["notes"] if "low-confidence" in n]
        assert said and "check" in said[0], said
    finally:
        done()
    top, done = _tmp()
    try:
        argv, _, _, _ = _solo_project(top)
        assert not any("low-confidence" in n for n in _doc(argv + _SMALL)["notes"])
    finally:
        done()


def _check_margin_in_table_and_json():
    """`margin` and the peak worst/median are columns of the table and fields of the JSON; the note says the table never picks and
    the ear decides."""
    top, done = _tmp()
    try:
        argv, _, _, _ = _solo_project(top)
        doc = _doc(argv + _SMALL)
        assert doc["rows"], doc["rejected"]
        for row in doc["rows"]:
            assert row["margin_oct"] <= row["width_worst_oct"] + 1e-9, row
        assert doc["conditions"]["delay_tolerance_ms"] == DELAY_TOLERANCE_MS, doc["conditions"]
        assert "never picks" in doc["note"] and "ear" in doc["note"], doc["note"]
        rc, text, err = _run(argv + _SMALL)
        assert rc == 0, err[-300:]
        head = next(ln for ln in text.splitlines() if "LP" in ln and "HP" in ln)
        assert "margin" in head and "worst oct" in head and "med oct" in head, head
        assert "the ear decides" in text and "never picks" in text, text[-200:]
    finally:
        done()


# -------- slice 2 (#210): the woofer-mid joint, coupled per side; synthetic curves whose best is known, points that differ
_C_FAMS = [("LR", 36), ("BW", 36), ("BE", 36)]
_C_LP = ("LR", 36, 250.0)
_C_HP = ("BW", 36, 315.0)


def _c_grid():
    return P.grid(20.0, 1600.0, 48)


def _c_driver(f, lp, hp, delay_ms, sign=1.0):
    """(lower, upper) of flat magnitude, in phase only through `lp`, `hp` and `delay_ms` on the upper."""
    xl = dsp_math.xo_response(f, lp[2], lp[1], "lp", lp[0])
    xh = dsp_math.xo_response(f, hp[2], hp[1], "hp", hp[0])
    lower = np.exp(-1j * np.angle(xl))
    upper = sign * np.exp(-1j * np.angle(xh)) * np.exp(2j * np.pi * f * delay_ms * 1e-3)
    return lower, upper


def _c_points(curve, f, n, jitter_ms=0.03):
    """`n` curves differing by a small arrival, the points differing as a head moving makes them."""
    jitter = np.linspace(-jitter_ms, jitter_ms, n) if n > 1 else np.array([0.0])
    return np.array([curve * np.exp(-2j * np.pi * f * j * 1e-3) for j in jitter])


def _c_input(spec, *, lp_corners=(200, 250, 315), hp_corners=(250, 315, 400), fams=None, n=3, rule=None, **kw):
    """Sides from `(name, lp, hp, delay, sign)`; options over `lp_corners`/`hp_corners` in `fams`."""
    f = _c_grid()
    sides = []
    for name, lp, hp, delay, sign in spec:
        lower, upper = _c_driver(f, lp, hp, delay, sign)
        sides.append(CoupledSide(name, f"w-{name}", f"m-{name}", np.tile(lower, (n, 1)), _c_points(upper, f, n), arrival_ms=0.0))
    first = spec[0]
    xl = dsp_math.xo_response(f, first[1][2], first[1][1], "lp", first[1][0])
    xh = dsp_math.xo_response(f, first[2][2], first[2][1], "hp", first[2][0])
    target = 20.0 * np.log10(np.abs(xl) + np.abs(xh))
    fams = fams or _C_FAMS
    args = dict(freqs=f, points=[f"p{i + 1}" for i in range(n)], sides=sides,
                lp_options=_options(fams, lp_corners), hp_options=_options(fams, hp_corners), target_db=target, max_ms=20.0,
                lr_rule_ms=rule)
    args.update(kw)
    return CoupledInput(**args)


def _c_row(rows, lp, hp):
    """The first row whose sides are all this pair, or None."""
    for r in rows:
        if all(r["sides"][s]["lp"] == list(lp) and r["sides"][s]["hp"] == list(hp) for s in r["sides"]):
            return r
    return None


def _check_coupled_finds_the_planted_pair():
    """A pair, polarity and per-side delay planted on L and R, the rule's offset consistent with them: the search returns them, by a
    margin over a pair at another corner, on points that differ. Inverted on both sides it comes back as INV on both."""
    spec = [("L", _C_LP, _C_HP, 1.25, 1.0), ("R", _C_LP, _C_HP, 0.45, 1.0)]
    res = scan_coupled(_c_input(spec, rule=0.8))
    assert res["rows"], res["rejected"]
    best = res["rows"][0]
    for side, want in (("L", 1.25), ("R", 0.45)):
        row = best["sides"][side]
        assert row["lp"] == list(_C_LP) and row["hp"] == list(_C_HP), row
        assert row["polarity"] == "NORM", row["polarity"]
        assert abs(row["shift_ms"] - want) <= 0.06, (side, row["shift_ms"], want)
    others = [r for r in res["rows"] if _c_row([r], _C_LP, _C_HP) is None]
    assert others and best["margin_oct"] - others[0]["margin_oct"] >= 0.05, (best["margin_oct"], others[0]["margin_oct"] if others else None)
    assert abs((best["delays_ms"]["m-L"] - best["delays_ms"]["m-R"]) - 0.8) <= LR_OFFSET_TOLERANCE_MS + 1e-9, best["delays_ms"]
    inv = [("L", _C_LP, _C_HP, 1.25, -1.0), ("R", _C_LP, _C_HP, 0.45, -1.0)]
    back = scan_coupled(_c_input(inv, rule=0.8))["rows"][0]
    assert all(back["sides"][s]["polarity"] == "INV" for s in ("L", "R")), back["sides"]


def _check_coupled_rule_and_conditions():
    """The L-R conditions couple the sides. The rule held at 2.0 ms where the planted delays give 0.8: no row keeps both planted
    shifts, and every row holds the rule. Lifted (`free_lr`), the planted pair comes back near its own shifts. The same polarity: L NORM,
    R INV planted returns no row with different polarities unless `same_polarity` is off."""
    spec = [("L", _C_LP, _C_HP, 1.25, 1.0), ("R", _C_LP, _C_HP, 0.45, 1.0)]
    held = scan_coupled(_c_input(spec, rule=2.0))
    assert all(abs(r["delays_ms"]["m-L"] - r["delays_ms"]["m-R"] - 2.0) <= 0.1 + 1e-9 for r in held["rows"]), held["rows"][:1]
    assert not any(abs(r["sides"]["L"]["shift_ms"] - 1.25) < 0.03 and abs(r["sides"]["R"]["shift_ms"] - 0.45) < 0.03 for r in held["rows"])
    free = scan_coupled(_c_input(spec, rule=2.0, free_lr=True))
    top = _c_row(free["rows"], _C_LP, _C_HP)
    assert top is not None and abs(top["sides"]["L"]["shift_ms"] - 1.25) <= 0.06 and abs(top["sides"]["R"]["shift_ms"] - 0.45) <= 0.06, top
    assert free["rows"][0]["margin_oct"] >= (held["rows"][0]["margin_oct"] if held["rows"] else 0.0) + 0.2
    mixed = [("L", _C_LP, _C_HP, 1.25, 1.0), ("R", _C_LP, _C_HP, 0.45, -1.0)]
    same = scan_coupled(_c_input(mixed, rule=0.8))
    assert all(r["sides"]["L"]["polarity"] == r["sides"]["R"]["polarity"] for r in same["rows"])
    apart = scan_coupled(_c_input(mixed, rule=0.8, same_polarity=False))
    assert any(r["sides"]["L"]["polarity"] != r["sides"]["R"]["polarity"] for r in apart["rows"]), [r["sides"]["L"]["polarity"] for r in apart["rows"]][:3]
    # the same family and order L/R, by default; the per-side corners only with the flag
    other = ("BE", 36, 250.0)
    two = [("L", _C_LP, _C_HP, 1.25, 1.0), ("R", other, _C_HP, 0.45, 1.0)]
    alike = scan_coupled(_c_input(two, rule=0.8))
    assert all(r["sides"]["L"]["lp"][:2] == r["sides"]["R"]["lp"][:2] for r in alike["rows"]), alike["rows"][:1]
    corners = [("L", _C_LP, _C_HP, 1.25, 1.0), ("R", ("LR", 36, 315.0), ("BW", 36, 400.0), 0.45, 1.0)]
    sym = scan_coupled(_c_input(corners, rule=0.8))
    assert all(r["sides"]["L"]["lp"] == r["sides"]["R"]["lp"] for r in sym["rows"])
    per = scan_coupled(_c_input(corners, rule=0.8, per_side_corners=True))
    assert any(r["sides"]["L"]["lp"] != r["sides"]["R"]["lp"] for r in per["rows"]), [(r["sides"]["L"]["lp"], r["sides"]["R"]["lp"]) for r in per["rows"]][:3]
    # the L/R crossings within a third of an octave by default; a tolerance of nearly none rejects the different corners, counted
    near = scan_coupled(_c_input(corners, rule=0.8, per_side_corners=True, th=Limits(lr_crossing_oct=0.001)))
    assert near["rejected"]["lr_crossing"] > 0, near["rejected"]
    assert all(abs(math.log2(r["sides"]["L"]["crossing_hz"] / r["sides"]["R"]["crossing_hz"])) <= 0.001 + 1e-9 for r in near["rows"]), near["rows"][:1]


def _ref_peak_width(inp, side, lp, hp):
    """The widest ±30 degree band of one pair over the shifts at point 0, what a one-point shortlist would rank on."""
    f = inp.freqs
    step = float(np.log2(f[1] / f[0]))
    xl = dsp_math.xo_response(f, lp[2], lp[1], "lp", lp[0])
    xh = dsp_math.xo_response(f, hp[2], hp[1], "hp", hp[0])
    phase = np.degrees(np.angle(side.lower[0] * xl)) - np.degrees(np.angle(side.upper[0] * xh))
    shifts = np.arange(-4.0, 4.0001, 0.05)
    a = np.abs(((phase[None, :] + 360.0 * f[None, :] * shifts[:, None] * 1e-3 + 180.0) % 360.0) - 180.0)
    c = int(np.argmin(np.abs(f - math.sqrt(lp[2] * hp[2]))))
    return float(_widths(a <= PHASE_WINDOW_DEG, c, step).max())


def _check_coupled_keeps_what_one_point_would_lose():
    """Two filter pairs. At the reference point the first is exact, and a one-point shortlist of one keeps only it. On the other points
    its error is 1.6 times the second's: over every point the second wins, by a margin, and comes back first."""
    f = _c_grid()
    p1 = (("LR", 24, 250.0), ("BE", 24, 280.0))
    p2 = (("BE", 24, 315.0), ("LR", 24, 355.0))
    def phase(pair):
        return np.angle(dsp_math.xo_response(f, pair[0][2], pair[0][1], "lp", pair[0][0])) \
            - np.angle(dsp_math.xo_response(f, pair[1][2], pair[1][1], "hp", pair[1][0]))
    i0 = int(np.argmin(np.abs(f - 300.0)))
    d = np.unwrap(phase(p1) - phase(p2))
    d -= 2.0 * np.pi * round(d[i0] / (2.0 * np.pi))
    at_ref = np.exp(-1j * phase(p1))
    elsewhere = np.exp(-1j * (phase(p2) - 0.6 * d))
    lower = np.array([at_ref, elsewhere, elsewhere * np.exp(-2j * np.pi * f * 0.02e-3), elsewhere * np.exp(2j * np.pi * f * 0.02e-3)])
    upper = np.ones_like(lower)
    side = CoupledSide("", "w", "m", lower, upper, arrival_ms=0.0)
    inp = CoupledInput(freqs=f, points=["p1", "p2", "p3", "p4"], sides=[side], lp_options=[p1[0], p2[0]], hp_options=[p1[1], p2[1]],
                       target_db=np.zeros_like(f), max_ms=20.0, leak_on=False, dip_on=False)
    refs = {(lp, hp): _ref_peak_width(inp, side, lp, hp) for lp in inp.lp_options for hp in inp.hp_options}
    one_point = max(refs, key=refs.get)
    assert one_point == (p1[0], p1[1]) and refs[one_point] >= sorted(refs.values())[-2] + 0.2, refs
    rows = scan_coupled(inp)["rows"]
    assert rows, "no rows"
    best = rows[0]["sides"][""]
    chosen = (tuple(best["lp"]), tuple(best["hp"]))
    assert chosen != (p1[0], p1[1]) and refs[chosen] <= refs[one_point] - 0.2, (chosen, refs)
    loser = next((r for r in rows if r["sides"][""]["lp"] == list(p1[0]) and r["sides"][""]["hp"] == list(p1[1])), None)
    assert loser is None or rows[0]["width_worst_oct"] - loser["width_worst_oct"] >= 0.15, (rows[0]["width_worst_oct"], loser and loser["width_worst_oct"])


def _hold(f, *, drop=None, n=3):
    """A bass joint below: sub and woofer flat and in phase but for a slow bowl: the band runs nearly four octaves, a width only a nearly linear phase can keep."""
    bowl = np.exp(1j * np.radians(8.0 * np.log2(f / 100.0) ** 2))
    gaps = np.linspace(-0.03, 0.03, n)
    sub = np.array([bowl * np.exp(-2j * np.pi * f * g * 1e-3) for g in gaps])
    low = np.where(f < 100.0, 1.0, (100.0 / f) ** 6)
    high = np.where(f > 100.0, 1.0, (f / 100.0) ** 6)
    wf = {"L": 0.5 * np.array([high for _ in gaps]).astype(complex), "R": 0.5 * np.array([high for _ in gaps]).astype(complex)}
    th = Limits(bass_drop_oct=drop) if drop is not None else Limits()
    return BassHold(freqs=f, sub=(sub * low), woofers=wf, sub_delay_ms=3.0, sub_polarity="NORM", base_delays={"L": 3.0, "R": 3.0},
                    base_lps={"L": None, "R": None}, max_ms=20.0, delay_step_ms=None), th


def _check_a_fallen_bass_joint_is_recovered_or_rejected():
    """The bass joint below is held and re-scored with the candidate's woofer low-pass. A gentle low-pass makes it fall past the limit,
    and the sub's own delay brings it back (the delay moved, the woofers untouched). A steep one cannot be brought back and the candidate
    is rejected. The planted baseline width is known by construction; both comparisons by a margin."""
    f = _c_grid()
    hold, th = _hold(f)
    base = hold.baseline(th)
    assert 3.2 <= base["width_worst_oct"] <= 4.2, base
    gentle = ("BW", 12, 600.0)
    held = _bass_score(hold, {"L": gentle, "R": gentle}, hold.base_delays, 1.0, hold.sub_delay_ms, th)
    assert held["width_worst_oct"] <= base["width_worst_oct"] - 0.2, (held, base)
    judged = _bass_judge(hold, {"L": gentle, "R": gentle}, hold.base_delays, th)
    assert judged["kept"] and judged["recovered"], judged
    assert judged["width_worst_oct"] >= base["width_worst_oct"] - th.bass_drop_oct, (judged, base)
    assert abs(judged["sub_delay_ms"] - hold.sub_delay_ms) >= 0.05, judged
    steep = ("LR", 36, 180.0)
    lost = _bass_judge(hold, {"L": steep, "R": steep}, hold.base_delays, th)
    assert not lost["kept"], lost
    # through the scan: the gentle candidate carries the recovery in its row, the steep one is counted out
    spec = [("L", gentle, _C_HP, 0.5, 1.0), ("R", gentle, _C_HP, 0.5, 1.0)]
    inp = _c_input(spec, rule=0.0, lp_corners=(), hp_corners=(), leak_on=False, dip_on=False, bass=hold, held_lower={"w-L": 3.0, "w-R": 3.0})
    inp.lp_options, inp.hp_options = [gentle, steep], [_C_HP]
    res = scan_coupled(inp)
    kept = _c_row(res["rows"], gentle, _C_HP)
    assert kept is not None and kept["bass"]["recovered"] and kept["bass"]["kept"], (kept and kept["bass"], res["rejected"])
    assert _c_row(res["rows"], steep, _C_HP) is None and res["rejected"].get("bass", 0) > 0, res["rejected"]
    unfallen = _bass_judge(hold, {"L": None, "R": None}, hold.base_delays, th)
    assert unfallen["kept"] and not unfallen["recovered"], unfallen
    # the bass limit is a flag: at a drop of 6 oct the steep low-pass is no fall at all, kept without moving the sub
    lenient = Limits(bass_drop_oct=6.0)
    assert _bass_judge(hold, {"L": steep, "R": steep}, hold.base_delays, lenient)["kept"], "a limit of 6 oct must keep the steep low-pass"


def _check_upper_group_survives_move():
    """`--move upper`: the mid takes the shift, the tweeter follows by the same amount and flips with the mid's polarity; a row past
    the ceiling for the tweeter is rejected. `--move lower`: the woofer takes the shift, the mids and tweeters stand, and only the woofer
    is checked against 0...max_ms."""
    spec = [("L", _C_LP, _C_HP, 1.25, -1.0), ("R", _C_LP, _C_HP, 0.45, -1.0)]
    above = {"tw-L": {"delay_ms": 4.0, "polarity": "NORM", "follows": "m-L"}, "tw-R": {"delay_ms": 3.2, "polarity": "NORM", "follows": "m-R"}}
    inp = _c_input(spec, rule=0.8, held_lower={"w-L": 2.0, "w-R": 2.0}, held_upper={"m-L": 2.5, "m-R": 1.7},
                   upper_polarity={"m-L": "NORM", "m-R": "NORM"}, above=above)
    res = scan_coupled(inp)
    best = res["rows"][0]
    assert all(best["sides"][s]["polarity"] == "INV" for s in ("L", "R")), best["sides"]
    d = best["delays_ms"]
    for side, tw0, m0 in (("L", 4.0, 2.5), ("R", 3.2, 1.7)):
        moved = d[f"m-{side}"] - m0
        assert abs(moved - (best["sides"][side]["shift_ms"] + 2.0 - m0)) < 1e-6, (d, best["sides"][side])
        assert abs(d[f"tw-{side}"] - (tw0 + moved)) < 1e-6, (d, tw0, moved)
    assert best["above"]["tw-L"]["polarity"] == "INV" and best["above"]["tw-R"]["polarity"] == "INV", best["above"]
    # a tweeter pushed past the ceiling rejects, the mid alone would have fitted
    high = {"tw-L": {"delay_ms": 19.9, "polarity": "NORM", "follows": "m-L"}, "tw-R": {"delay_ms": 19.1, "polarity": "NORM", "follows": "m-R"}}
    over = scan_coupled(_c_input(spec, rule=0.8, held_lower={"w-L": 2.0, "w-R": 2.0}, held_upper={"m-L": 2.5, "m-R": 1.7},
                                 upper_polarity={"m-L": "NORM", "m-R": "NORM"}, above=high))
    assert over["rejected"]["delay"] > 0 and not any(
        all(abs(r["delays_ms"][c] - 0.0) >= 0 for c in r["delays_ms"]) and max(r["delays_ms"].values()) > 20.0 for r in over["rows"]), over["rejected"]
    # `--move lower`: the mids hold, woofers move by -shift
    low = scan_coupled(_c_input(spec, rule=0.8, move="lower", held_lower={"w-L": 2.0, "w-R": 2.0}, held_upper={"m-L": 2.5, "m-R": 1.7},
                                upper_polarity={"m-L": "INV", "m-R": "INV"}))
    top = low["rows"][0]
    assert abs(top["delays_ms"]["m-L"] - 2.5) < 1e-9 and abs(top["delays_ms"]["m-R"] - 1.7) < 1e-9, top["delays_ms"]
    assert abs(top["delays_ms"]["w-L"] - (2.5 - top["sides"]["L"]["shift_ms"])) < 1e-9, top["delays_ms"]


def _check_a_delay_past_the_ceiling_rejects():
    """A held woofer at 19.9 ms with the planted shift +1.25 ms puts the mid past 20: the planted pair is out, the reason counted; with
    the ceiling higher it stands. Negative delays reject too (a held woofer at 0.2 with a shift of -1)."""
    spec = [("L", _C_LP, _C_HP, 1.25, 1.0), ("R", _C_LP, _C_HP, 1.25, 1.0)]
    held = {"w-L": 19.9, "w-R": 19.9}
    tight = scan_coupled(_c_input(spec, rule=0.0, held_lower=held))
    planted = [r for r in tight["rows"] if abs(r["sides"]["L"]["shift_ms"] - 1.25) < 0.05]
    assert not planted and tight["rejected"]["delay"] > 0, (planted[:1], tight["rejected"])
    assert all(max(r["delays_ms"].values()) <= 20.0 + 1e-9 for r in tight["rows"]), tight["rows"][:1]
    wide = scan_coupled(_c_input(spec, rule=0.0, held_lower=held, max_ms=22.0))
    assert _c_row(wide["rows"], _C_LP, _C_HP) is not None, wide["rejected"]
    early = [("L", _C_LP, _C_HP, -1.25, 1.0), ("R", _C_LP, _C_HP, -1.25, 1.0)]
    low = scan_coupled(_c_input(early, rule=0.0, held_lower={"w-L": 0.2, "w-R": 0.2}))
    assert low["rejected"]["delay"] > 0 and all(min(r["delays_ms"].values()) >= -1e-9 for r in low["rows"]), low["rejected"]


def _check_align_passband_and_trim():
    """`--align`: a hump above the target is cut (no more cuts and depth than the budget), the gain up raises a sagging band, and the
    channel lands back on its own passband level, so only the shape moved. A channel past the gain range brings every channel down
    alike, by the excess on the step; below the range brings them up alike, within limits; both ends past at once refuse."""
    f = P.grid(50.0, 1600.0, 48)
    target = np.zeros_like(f)
    hump = dsp_math.peq_response(f, "PK", 400.0, 8.0, 3.0)
    h = np.tile(hump, (3, 1))
    th = Limits()
    keep = (100.0, 200.0)
    level = lambda arr: 10.0 * np.log10(np.mean(np.mean(np.abs(arr) ** 2, 0)[(f >= keep[0]) & (f <= keep[1])]))
    E, info = _flatten_channel(h, target, f, (100.0, 560.0), keep, th)
    assert len(info["bands"]) <= ALIGN_CUTS and all(b["gain_db"] >= -ALIGN_CUT_MAX_DB - 1e-9 for b in info["bands"]), info
    assert any(abs(b["f"] - 400.0) <= 60 for b in info["bands"]), info["bands"]
    assert abs(level(h * E) - level(h)) < 0.05, (level(h * E), level(h))
    # the shape moved: against the channel's own passband level the hump is lower by at least 4 dB
    i = int(np.argmin(np.abs(f - 400.0)))
    db_of = lambda x: 20.0 * np.log10(np.abs(x))
    a = (f >= keep[0]) & (f <= keep[1])
    before = db_of(h[0] * np.ones_like(f))[i] - np.mean(db_of(h[0])[a])
    after = db_of(h[0] * E)[i] - np.mean(db_of(h[0] * E)[a])
    assert before - after >= 4.0, (before, after, info)
    # a smaller budget changes the fit
    E2, info2 = _flatten_channel(h, target, f, (100.0, 560.0), keep, Limits(align_cuts=1, align_cut_max_db=3.0))
    assert len(info2["bands"]) <= 1 and all(b["gain_db"] >= -3.0 - 1e-9 for b in info2["bands"]), info2
    # the channel gains' common trim: one over the range, below the range, and both
    assert _common_trim({"a": 7.0, "b": 0.0}, (-30.0, 5.0), 1.0) == -2.0
    assert _common_trim({"a": -31.5, "b": -10.0}, (-30.0, 5.0), 1.0) == 2.0
    assert _common_trim({"a": 7.0, "b": -29.5}, (-30.0, 5.0), 1.0) is None
    assert _common_trim({"a": 0.0, "b": -3.0}, (-30.0, 5.0), 1.0) == 0.0
    assert _common_trim({"a": 5.4}, (-30.0, 5.0), None) == -0.4


def _check_decay_and_share():
    """Decay: the ring of each raw driver from its impulse, once per driver; the lower driver rings about 3x longer around 250 Hz:
    the band is named, the row carries the lower driver's share there and its low-pass group delay. A changed ratio names no band."""
    fs = 48000.0
    n = int(fs * 0.3)
    t = np.arange(n) / fs
    def ring(f0, tau):
        x = np.exp(-t / tau) * np.sin(2.0 * np.pi * f0 * t)
        x[0] = 1.0
        return x
    curves = {"w-L": {"info": {"tripod": {"ir": {"ir": ring(250.0, 0.016), "sample_rate": fs}}}},
              "m-L": {"info": {"tripod": {"ir": {"ir": ring(250.0, 0.005), "sample_rate": fs}}}}}
    table = decay_table(curves, ("w-L", "m-L"), (200.0, 250.0, 315.0))
    w_ms = dict(zip(table["freqs_hz"], table["ms"]["w-L"]))[250.0]
    m_ms = dict(zip(table["freqs_hz"], table["ms"]["m-L"]))[250.0]
    assert w_ms >= 1.5 * m_ms and 20.0 <= w_ms <= 90.0, (w_ms, m_ms)
    assert table["ir_from"]["w-L"] == "tripod", table["ir_from"]
    band = ring_band(table["ms"]["w-L"], table["ms"]["m-L"], table["freqs_hz"], 1.5)
    assert band and band["freqs_hz"] and 250.0 in band["freqs_hz"], band
    assert ring_band(table["ms"]["w-L"], table["ms"]["m-L"], table["freqs_hz"], 50.0) is None
    # the share of the lower driver over the band, the low-pass group delay beside it: a steeper low-pass gives a lower share at 250-400
    hp = ("LR", 36, 315.0)
    spec = [("", _C_LP, hp, 0.0, 1.0)]
    inp = _c_input(spec, rule=None, decay={"": {"band": (250.0, 400.0), "gd_at_hz": 250.0}}, lp_corners=(250,), hp_corners=(315,), fams=[("LR", 36)])
    row = scan_coupled(inp)["rows"][0]["sides"][""]
    pl = np.abs(dsp_math.xo_response(inp.freqs, 250.0, 36, "lp", "LR")) ** 2
    ph = np.abs(dsp_math.xo_response(inp.freqs, 315.0, 36, "hp", "LR")) ** 2
    m = (inp.freqs >= 250.0) & (inp.freqs <= 400.0)
    want = 10.0 * np.log10(pl[m].sum() / (pl[m].sum() + ph[m].sum()))
    assert row["lower_share_db"] is not None and abs(row["lower_share_db"] - want) < 0.2, (row["lower_share_db"], want)
    gd = -np.gradient(np.unwrap(np.angle(dsp_math.xo_response(np.geomspace(20, 5000, 4000), 250.0, 36, "lp", "LR"))), 2 * np.pi * np.geomspace(20, 5000, 4000)) * 1e3
    assert abs(row["lp_gd_ms"] - gd[np.argmin(np.abs(np.geomspace(20, 5000, 4000) - 250.0))]) < 0.1, row["lp_gd_ms"]


def _check_each_threshold_changes_the_answer():
    """Every named limit has an effect, the flag only sets it: for each, the same planted input read with the default and with the
    changed value gives a different answer, seen in rows or their numbers."""
    spec = [("L", _C_LP, _C_HP, 1.25, 1.0), ("R", _C_LP, _C_HP, 0.45, 1.0)]
    base = scan_coupled(_c_input(spec, rule=0.8))
    base_top = base["rows"][0]
    # a phase window of 5 degrees: the jittered points' band is narrower by a margin
    narrow = scan_coupled(_c_input(spec, rule=0.8, th=Limits(phase_window_deg=5.0)))
    top = _c_row(narrow["rows"], _C_LP, _C_HP)
    assert top is None or top["width_worst_oct"] <= base_top["width_worst_oct"] - 0.2, (top and top["width_worst_oct"], base_top["width_worst_oct"])
    # an impossible leak limit rejects every pair, and the rejected count says why
    strict = scan_coupled(_c_input(spec, rule=0.8, th=Limits(leak_octave_db=-200.0)))
    assert not strict["rows"] and strict["rejected"]["leak"] > 0, strict["rejected"]
    # the dip limit at +50 rejects by the dip; lifted to -60 keeps
    dip = scan_coupled(_c_input(spec, rule=0.8, th=Limits(dip_limit_db=50.0)))
    assert not dip["rows"] and dip["rejected"]["dip"] > 0, dip["rejected"]
    # tolerance zero: the margin is the point's own width, no neighbour narrower
    zero = scan_coupled(_c_input(spec, rule=0.8, th=Limits(delay_tolerance_ms=0.0)))
    top0 = _c_row(zero["rows"], _C_LP, _C_HP)
    assert top0 is not None and top0["margin_oct"] >= base_top["margin_oct"] - 1e-9, (top0["margin_oct"], base_top["margin_oct"])
    assert abs(top0["margin_oct"] - top0["width_worst_oct"]) < 1e-9, top0
    # the L-R tolerance: the rule 0.2 from the planted offset rejects the planted pair at 0.1, holds it at 0.3
    apart = scan_coupled(_c_input(spec, rule=1.0, th=Limits(lr_tolerance_ms=0.1)))
    assert not any(abs(r["sides"]["L"]["shift_ms"] - 1.25) < 0.03 and abs(r["sides"]["R"]["shift_ms"] - 0.45) < 0.03 for r in apart["rows"]), apart["rows"][:1]
    wider = scan_coupled(_c_input(spec, rule=1.0, th=Limits(lr_tolerance_ms=0.3)))
    assert any(abs(r["sides"]["L"]["shift_ms"] - 1.25) < 0.03 and abs(r["sides"]["R"]["shift_ms"] - 0.45) < 0.03 for r in wider["rows"]), wider["rejected"]
    # the shortlist: only one per band and side comes through
    one = scan_coupled(_c_input(spec, rule=0.8, th=Limits(shortlist=1)))
    assert one["rejected"]["past_shortlist"] > 0 and len(one["rows"]) <= len(base["rows"]), one["rejected"]
    # the crossing bands: a width of 0.1 oct gives more, narrower labels
    fine = scan_coupled(_c_input(spec, rule=0.8, th=Limits(band_width_oct=0.1)))
    assert len({r["band"] for r in fine["rows"]}) > len({r["band"] for r in base["rows"]}), ({r["band"] for r in fine["rows"]}, {r["band"] for r in base["rows"]})
    # the shift span: a span of 0.5 ms cannot reach the planted 1.25 on the L
    short = scan_coupled(_c_input(spec, rule=0.8, th=Limits(shift_span_ms=0.5)))
    assert not any(abs(r["sides"]["L"]["shift_ms"] - 1.25) < 0.06 for r in short["rows"]), short["rows"][:1]
    # the ranking: by default the margin decides, `--rank worst` the worst point's band at the row's delay
    first = {"margin_oct": 0.9, "width_worst_oct": 0.5, "width_median_oct": 0.6, "loss_median_db": 0.0, "dip_db": -1.0}
    second = {"margin_oct": 0.8, "width_worst_oct": 0.9, "width_median_oct": 0.6, "loss_median_db": 0.0, "dip_db": -1.0}
    assert sorted([second, first], key=_row_key, reverse=True)[0] is first
    assert sorted([first, second], key=lambda r: _row_key(r, "worst"), reverse=True)[0] is second
    assert sorted([first, second], key=lambda r: _row_key(r, "median"), reverse=True)[0] is second or _row_key(first, "median") == _row_key(second, "median")
    ranked = scan_coupled(_c_input(spec, rule=0.8, th=Limits(rank="worst")))["rows"]
    assert ranked and all(_row_key(a, "worst") >= _row_key(b, "worst") for a, b in zip(ranked, ranked[1:]))


def _check_bass_flags_reach_the_scan():
    """Slice 1's limits are flags too: the ±30 degree window, the leak levels, the dip limit, the delay tolerance, the shortlist,
    the crossing-band width and the rank, each read by `scan_bass` through `Limits`."""
    inp = _planted_input()
    base = scan_bass(inp)
    top = base["rows"][0]
    wider = _planted_input()
    wider.th = Limits(phase_window_deg=60.0)
    wide_top = scan_bass(wider)["rows"]
    assert wide_top and wide_top[0]["width_worst_oct"] >= top["width_worst_oct"] - 1e-9, (wide_top[0]["width_worst_oct"], top["width_worst_oct"])
    # the leak: limits strict enough drop every row; `rejected["leak"]` says it
    strict = _planted_input()
    strict.th = Limits(leak_near_db=-100.0, leak_far_db=-100.0)
    res = scan_bass(strict)
    assert not res["rows"] and res["rejected"]["leak"] > 0, res["rejected"]
    # the dip limit: above any sum rejects all
    dipped = _planted_input()
    dipped.th = Limits(dip_limit_db=20.0)
    res = scan_bass(dipped)
    assert not res["rows"] and res["rejected"]["dip"] > 0, res["rejected"]
    # the shortlist: 1 per band
    short = _planted_input()
    short.th = Limits(shortlist=1)
    res = scan_bass(short)
    per_band = {}
    for r in res["rows"]:
        per_band[r["band"]] = per_band.get(r["band"], 0) + 1
    assert per_band and max(per_band.values()) == 1, per_band
    # the crossing bands: width 1 oct, one or two labels
    wide = _planted_input()
    wide.th = Limits(band_width_oct=1.0)
    assert len({r["band"] for r in scan_bass(wide)["rows"]}) <= 3
    # the delay tolerance: zero makes the margin the width at the delay
    zero = _planted_input()
    zero.th = Limits(delay_tolerance_ms=0.0)
    row = scan_bass(zero)["rows"][0]
    assert abs(row["margin_oct"] - row["width_worst_oct"]) < 1e-9, (row["margin_oct"], row["width_worst_oct"])
    # the rank: worst first
    ranked = _planted_input()
    ranked.th = Limits(rank="worst")
    rows = scan_bass(ranked)["rows"]
    assert all(_row_key(a, "worst") >= _row_key(b, "worst") for a, b in zip(rows, rows[1:]))
    # the one-point limit moves: a crossing at 113 Hz passes with the limit at 150
    kw = dict(lp=("LR", 36, 113.0), hp=("LR", 36, 113.0), fams=[("LR", 36)], lp_corners=(113,), hp_corners=(113,), leak_on=False, dip_on=False, delay_ms=1.0)
    moved = _planted_input(sub_one_point=True, **kw)
    moved.th = Limits(sub_one_point_max_hz=150.0)
    assert any(r["crossing_hz"] >= SUB_ONE_POINT_MAX_HZ for r in scan_bass(moved)["rows"]), "the one-point limit did not move"
    # the rule's tolerance
    assert check_stage(rule_ms=0.0, lr_delay_ms=0.3, tolerance_ms=0.2) and not check_stage(rule_ms=0.0, lr_delay_ms=0.15, tolerance_ms=0.2)


def _cli_3way(top, *, tw=False, at=None):
    """A project with a sub, woofers and mids (tweeters optional): the same impulses at every point, for the command line."""
    roles = {"sw": "sub", "w-L": "woofer", "w-R": "woofer", "m-L": "midrange", "m-R": "midrange"}
    if tw:
        roles.update({"tw-L": "tweeter", "tw-R": "tweeter"})
    points = {c: POSITIONS for c in roles if c != "sw"}
    argv, proj, house, solos = _solo_project(top, roles=roles, at=at or {"w-L": 200, "w-R": 100, "m-L": 150, "m-R": 96}, points=points)
    return argv, proj, house, solos


_WM_TINY = ["--joint", "woofer-midrange", "--lp-bounds", "224:315", "--hp-bounds", "224:315", "--shift-span", "2"]


def _check_cli_woofer_mid_end_to_end():
    """The command line on a small 3-way project: the grid line, the table with its columns, `--json` carrying per-side rows and each
    channel's delay; the bass joint's row goes in through `--fixed` and the woofers' delays are held from it, the re-score named in the
    table and JSON; `--no-same-family` and the other flags recorded in `limits`, their effect shown; `--align` prints the EQ and the
    common trim; `--fixed` on a broken row refuses."""
    top, done = _tmp()
    try:
        argv, proj, house, solos = _cli_3way(top)
        rc, out, err = _run(argv + _WM_TINY + ["--no-leak"])
        assert rc == 0, (rc, err[-800:])
        assert "filter pairs" in err and "Crossing" in out and "margin" in out, (err[:300], out[:400])
        doc = _doc(argv + _WM_TINY + ["--no-leak"])
        assert doc["joint"] == "woofer-midrange", doc["joint"]
        assert doc["rows"] and {"L", "R"} == set(doc["rows"][0]["sides"]), doc["rows"][:1]
        row = doc["rows"][0]
        assert all(c in row["delays_ms"] for c in ("w-L", "w-R", "m-L", "m-R")), row["delays_ms"]
        assert row["channels"]["m-L"]["hp"] and row["channels"]["w-L"]["lp"], row["channels"]
        bass_doc = _doc(argv + _TINY)
        bass_file = os.path.join(top, "bass.json")
        with open(bass_file, "w", encoding="utf-8") as fh:
            json.dump(bass_doc, fh)
        # the row number is the person's: a doc with rows and no @N refuses
        rc, _o, err = _run(argv + _WM_TINY + ["--no-leak", "--fixed", bass_file])
        assert rc == 3 and "@N" in err, (rc, err[-300:])
        doc = _doc(argv + _WM_TINY + ["--no-leak", "--bass-drop", "6", "--fixed", f"{bass_file}@1"])
        assert doc["rows"], doc["rejected"]
        row = doc["rows"][0]
        held = bass_doc["rows"][0]["delays_ms"]
        assert abs(row["delays_ms"]["w-L"] - held["w-L"]) < 1e-6 and abs(row["delays_ms"]["w-R"] - held["w-R"]) < 1e-6, (row["delays_ms"], held)
        assert "bass" in row and "width_worst_oct" in row["bass"] and row["bass"]["baseline_worst_oct"] is not None, row.get("bass")
        assert any("re-scored" in n or "held" in n for n in doc["notes"]), doc["notes"]
        with open(os.path.join(top, "broken.json"), "w", encoding="utf-8") as fh:
            fh.write('{"joint": "sub-woofer"}')
        rc, _o, err = _run(argv + _WM_TINY + ["--fixed", os.path.join(top, "broken.json")])
        assert rc == 3 and "channels" in err, (rc, err[-300:])
        # a limit changed from its default is shown with its effect on the same grid
        doc = _doc(argv + _WM_TINY + ["--no-leak", "--phase-window", "40", "--dip-limit", "-6", "--delay-tolerance", "0.05",
                                      "--shortlist", "50", "--band-width", "0.25", "--rank", "worst", "--no-same-polarity",
                                      "--no-same-family", "--corners-per-side", "--lr-tolerance", "0.2", "--lr-crossing-oct", "0.5"])
        limits = doc["limits"]
        for key, value in (("phase_window_deg", 40.0), ("dip_limit_db", -6.0), ("delay_tolerance_ms", 0.05), ("shortlist", 50), ("band_width_oct", 0.25),
                           ("rank", "worst"), ("lr_tolerance_ms", 0.2), ("lr_crossing_oct", 0.5)):
            assert limits[key]["value"] == value and limits[key]["changed"], (key, limits[key])
        assert doc["conditions"]["same_polarity"] is False and doc["conditions"]["same_family"] is False and doc["conditions"]["per_side_corners"] is True, doc["conditions"]
        assert doc["default_run"]["rows"] is not None and doc["default_run"]["best"] is not None, doc["default_run"]
        rc, out, _e = _run(argv + _WM_TINY + ["--no-leak", "--phase-window", "40"])
        assert "default" in out.lower() and "40" in out, out[-500:]
        # no default run on request; a coarser corner grid is fewer pairs; the crossing window and the dip band are read
        doc = _doc(argv + _WM_TINY + ["--no-leak", "--phase-window", "40", "--no-default-run", "--corner-step", "0.5", "--crossing-window", "200:500", "--dip-band", "200:300"])
        assert doc["default_run"] is None and doc["limits"]["phase_window_deg"]["changed"], doc["default_run"]
        assert doc["grid"]["pairs"] < _doc(argv + _WM_TINY + ["--no-leak"])["grid"]["pairs"], doc["grid"]["pairs"]
        assert all(200.0 <= float(r["band"].split("-")[0]) and float(r["band"].split("-")[1].split(" ")[0]) <= 500.0 for r in doc["rows"]), [r["band"] for r in doc["rows"]][:5]
        assert doc["limits"]["dip_band"]["changed"] and doc["limits"]["crossing_window"]["value"] == [200.0, 500.0], doc["limits"]["dip_band"]
        # --align: the fit and the trim are in the output; both sides flattened
        doc = _doc(argv + _WM_TINY + ["--no-leak", "--align", "--align-cuts", "2", "--align-gain-max", "3"])
        assert doc["align"]["channels"]["w-L"]["net_gain_db"] is not None and doc["align"]["global_trim_db"] == 0.0, doc["align"]
        assert doc["limits"]["align_cuts"]["value"] == 2 and doc["cross_first"]["rows"] is not None, doc.get("cross_first")
        # hard limits keep their refusals: an out-of-profile fixed row does not widen them
        rc, _o, err = _run(argv + _WM_TINY + ["--phase-window", "0"])
        assert rc == 3 and "phase" in err, (rc, err[-300:])
    finally:
        done()


def _check_only_the_woofer_mid_row_table():
    """A joint the build does not search refuses in one line, and the flags that belong to other joints refuse here."""
    top, done = _tmp()
    try:
        argv, _proj, _house, _solos = _cli_3way(top, tw=True)
        rc, _o, err = _run(argv + ["--joint", "midrange-tweeter"])
        assert rc == 3 and "midrange-tweeter" in err, (rc, err[-300:])
        rc, _o, err = _run(argv + _TINY + ["--align"])
        assert rc == 3 and "--align" in err, (rc, err[-300:])
        rc, _o, err = _run(argv + _WM_TINY + ["--gain", "0:2:1"])
        assert rc == 3 and "--gain" in err, (rc, err[-300:])
    finally:
        done()


def _selftest():
    failures = []
    for check in (_check_joints_from_roles, _check_planted_delay_polarity_corners, _check_family_outside_profile_never_returned,
                  _check_lr_offset_condition, _check_leak_and_dip_conditions, _check_sub_one_point_limit, _check_hp_floor,
                  _check_refusals_are_one_line, _check_protective_refusal_passed_on, _check_cli_end_to_end,
                  _check_band_decides_the_rank, _check_worst_and_median_of_points, _check_space_and_rows_against_a_profile,
                  _check_corners_from_the_top_level, _check_stereo_sub_delays, _check_table_enterable, _check_free_offset_is_said,
                  _check_notes_printed, _check_leak_moves_with_the_crossing, _check_no_leak_and_empty_words,
                  _check_front_lp_moves_the_delay, _check_single_point_needs_the_decision, _check_single_point_rule_on_any_reference,
                  _check_only_the_joints_roles_are_built, _check_level_step_and_sub_ver_refused, _check_failures_are_refusals,
                  _check_rejected_counts_every_drop_once, _check_grid_ceiling_and_row_buffer, _check_sub_limit_at_every_point,
                  _check_one_point_limit_with_leak_on, _check_stage_rule_on_a_coarse_step, _check_delay_step_and_gain_step,
                  _check_delay_ceiling_and_gain_range, _check_corners_snap, _check_time_base, _check_level_step_succeeds,
                  _check_partial_sub_points, _check_fs_floor_through_the_options, _check_leak_from_the_validated_limits,
                  _check_margin_ranks_past_a_knife_edge, _check_margin_tolerance_reaches_past_a_coarse_step, _check_worst_ranks_before_median,
                  _check_header_prints_the_scored_offset, _check_single_point_latest_decision_decides,
                  _check_bad_out_is_a_refusal_after_the_table, _check_gains_print_on_a_quarter_step, _check_front_lp_note_names_the_role,
                  _check_stereo_sub_offset_is_low_confidence, _check_margin_in_table_and_json,
                  _check_coupled_finds_the_planted_pair, _check_coupled_rule_and_conditions, _check_coupled_keeps_what_one_point_would_lose,
                  _check_a_fallen_bass_joint_is_recovered_or_rejected, _check_upper_group_survives_move, _check_a_delay_past_the_ceiling_rejects,
                  _check_align_passband_and_trim, _check_decay_and_share, _check_each_threshold_changes_the_answer, _check_bass_flags_reach_the_scan,
                  _check_cli_woofer_mid_end_to_end, _check_only_the_woofer_mid_row_table):
        try:
            check()
        except AssertionError as exc:
            failures.append(f"{check.__name__}: {exc}")
    assert not failures, "\n".join(failures)
    print("selftest OK -- the joints come from the roles; a planted delay, polarity and corner pair are found by a margin, "
          "on either side of the delay; a family outside the profile never comes back; the ±30 degree band ranks, worst and median "
          "of the points apart, ranked on the margin a moving head leaves; the table is what a person keys in, stereo sub included; the L-R "
          "rule holds on the DSP's step; the leak limit is the run's own, moved up with the crossing; every refusal is one line, exit 3; every drop is counted once; the woofer-mid joint holds a pair a one-point shortlist would lose, carries the bass joint below (recovered or rejected) and the group above; every limit is a flag and shows what changed; nothing is picked")
    return 0


if __name__ == "__main__":
    import console                       # issue #21: a code page must not destroy a result
    console.install()
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    sys.exit(_main())
