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

    python3 rew_tool/joint_search.py --project DIR --house FILE --solos DIR [--json] [--out DIR]
    python3 rew_tool/joint_search.py --project DIR --house FILE --rew --ver N
    python3 rew_tool/joint_search.py --selftest

Read-only: it prints a table, `--json`, `--out DIR`. It never banks and never picks; the last line says so. Each refusal is
one line, `refusing: <why>`, exit 3.
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
#: The sub's leak above the joint, sub minus front: `swws_search2.py:6,44`.
BASS_LEAK_100_DB = -24.0
BASS_LEAK_HI_DB = -30.0
BASS_LEAK_HI_BAND = (125.0, 200.0)
#: The floor of a high-pass, times the driver's installed Fs. Mid: the run's value (#210); tweeter: `fs_margin`'s convention.
#: A woofer is not on this list (`xover_wishes.FRAGILE_ROLES`): its margin is shown per row, not filtered on.
HP_FS_FLOOR = {"midrange": 1.45, "tweeter": _cc.FS_MARGIN_DEFAULT}
#: (delay L - delay R) = -(raw arrival L - raw arrival R) within this: `stage_lock.py:7-12`.
LR_OFFSET_TOLERANCE_MS = 0.10
#: A sub may stay at one point while its crossing is under this: lambda > 3.4 m, `swws_xo.py:69`.
SUB_ONE_POINT_MAX_HZ = 100.0
#: The grid: 1/6-oct corners over the joint's bounds, then +-1/12 oct around the shortlist (PLAN-W-12, the grid).
CORNER_STEP_OCT = 1.0 / 6.0
CORNER_REFINE_OCT = 1.0 / 12.0
#: About twice the design's ~29,000 filter pairs a joint: over it the run refuses without `--allow-large-grid`.
GRID_CEILING_PAIRS = 60000
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
    "bass": JointClass("bass", (40.0, 125.0), (40.0, 125.0), (35.0, 200.0), (20.0, 400.0), (45.0, 110.0), (100.0, 250.0)),
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


def joints_of(channels):
    """The adjacent roles of `xover_wishes.ROLE_ORDER` over the channels present, low to high. `channels`: {code: project row}."""
    stack = []
    for role in _xw.ROLE_ORDER:
        codes = [c for c, row in channels.items() if (row or {}).get("role") == role]
        if codes:
            stack.append(_branch(role, codes))
    return [Joint(a, b) for a, b in zip(stack, stack[1:])]


# ---------------------------------------------------------------- the stage conditions
def check_stage(*, rule_ms=None, lr_delay_ms=None, polarities=None, families=None):
    """What a candidate breaks of the stage conditions, as a list of words (empty = holds).

    `rule_ms`: the signed rule, (delay L - delay R) = -(raw arrival L - raw arrival R), within `LR_OFFSET_TOLERANCE_MS`.
    `polarities`, `families`: L and R, one value each. Only real L/R pairs are ever asked: a single sub has no L/R rule."""
    why = []
    if rule_ms is not None and lr_delay_ms is not None \
            and abs(float(lr_delay_ms) - float(rule_ms)) > LR_OFFSET_TOLERANCE_MS + 1e-9:
        why.append(f"delay L-R {float(lr_delay_ms):+.2f} ms breaks the rule {float(rule_ms):+.2f} "
                   f"+-{LR_OFFSET_TOLERANCE_MS:g} ms")
    if polarities is not None and polarities[0] != polarities[1]:
        why.append(f"polarity differs L/R: {polarities[0]} / {polarities[1]}")
    if families is not None and tuple(families[0]) != tuple(families[1]):
        why.append(f"filter family differs L/R: {families[0]} / {families[1]}")
    return why


# ---------------------------------------------------------------- the space from the project
def profile_xo(project_dir):
    """The public face of `xover_wishes._profile_xo`: the physical outputs' crossover facts, or None."""
    return _xw._profile_xo(project_dir)


@dataclass
class Space:
    """What the project allows: `xo` is `xover_wishes._profile_xo`'s dict."""
    families: list
    xo: dict
    gain_range: tuple
    delay_max_ms: float
    delay_step_ms: float
    rate_note: str = None


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
    families = dsp_math.options_for(xo["types"])
    if not families:
        raise JointSearchError(f"{path}: none of its crossover families is one the method can model")
    _rate2, max_ms = P._profile_limits(project_dir)
    if not max_ms:
        raise JointSearchError(f"{path} states no delay.max_ms: the delay search cannot be bounded")
    data = _dp._unwrap(prof)
    step = (data.get("delay") or {}).get("step_ms") if isinstance(data.get("delay"), dict) else None
    return Space(families=families, xo=xo, gain_range=gain_range, delay_max_ms=float(max_ms),
                 delay_step_ms=float(step) if step else None, rate_note=rate_note)


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


def _gain_split(rel_db, gain_range):
    """(sub dB, front dB) realising a relative sub level inside the channel-gain range, or None."""
    lo, hi = gain_range
    if rel_db >= 0:
        sub = min(hi, rel_db)
        front = sub - rel_db
    else:
        sub = rel_db
        front = 0.0
    if not (lo <= sub <= hi and lo <= front <= hi):
        return None
    return float(sub), float(front)


def _delay_split(delay_ms, offset_ms, max_ms, single_upper):
    """The delays the DSP takes for `delay_ms` (+ front later, - sub later) and the front's held L-R offset, or None past the ceiling."""
    sub, base = max(0.0, -float(delay_ms)), max(0.0, float(delay_ms))
    left = base + (0.0 if single_upper else float(offset_ms))
    right = base
    lowest = min(sub, left, right)
    if lowest < 0:
        sub, left, right = sub - lowest, left - lowest, right - lowest
    if max(sub, left, right) > max_ms + 1e-9:
        return None
    return {"sub": round(sub, 3), "upper_left": round(left, 3), "upper_right": None if single_upper else round(right, 3)}


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
    if single_upper:
        offsets = [0.0]
    elif inp.free_lr_offset:
        n_off = int(round(FREE_OFFSET_SPAN_MS / FREE_OFFSET_STEP_MS))
        offsets = [inp.lr_rule_ms + k * FREE_OFFSET_STEP_MS for k in range(-n_off, n_off + 1)]
    else:
        offsets = [float(inp.lr_rule_ms)]
    lp_bank, hp_bank = _Bank(f, "lp"), _Bank(f, "hp")
    sub_db0 = _db(inp.ref_lower).astype(np.float32)
    sub_ph0 = np.degrees(np.angle(inp.ref_lower)).astype(np.float32)
    i100 = int(np.argmin(np.abs(f - 100.0)))
    hi_mask = (f >= BASS_LEAK_HI_BAND[0]) & (f <= BASS_LEAK_HI_BAND[1])
    cw = np.flatnonzero((f >= cls.crossing_window[0]) & (f <= cls.crossing_window[1]))
    cw_mask, m0 = np.zeros(len(f), bool), int(cw[0])
    cw_mask[cw] = True
    edges = _band_edges(cls)
    rejected = {"leak": 0, "no_crossing": 0, "sub_one_point": 0, "gain": 0, "delay": 0, "dip": 0}

    def scan(pairs, oi, seen=None):
        """Rows for the filter pairs at the reference point, one L-R offset. `seen`: filter pairs already scanned."""
        offset = offsets[oi]
        front = _front_sum(inp.ref_l, inp.ref_r, f, offset)
        front_db, front_ph = _db(front).astype(np.float32), np.degrees(np.angle(front)).astype(np.float32)
        rows = []
        for lp, hp in pairs:
            if seen is not None:
                key = (lp, hp, oi)
                if key in seen:
                    continue
                seen.add(key)
            _, lp_db, lp_ph = lp_bank.get(lp)
            _, hp_db, hp_ph = hp_bank.get(hp)
            ls, lw = sub_db0 + lp_db, front_db + hp_db
            gap = ls - lw
            leak100, leak_hi = float(gap[i100]), float(gap[hi_mask].max())
            if inp.leak_on:
                g_ok = (leak100 + gains <= BASS_LEAK_100_DB) & (leak_hi + gains <= BASS_LEAK_HI_DB)
                rejected["leak"] += int((~g_ok).sum())
                if not g_ok.any():
                    continue
            else:
                g_ok = np.ones(len(gains), bool)
            has, cross = _crossings(gap, cw_mask, m0, gains)
            g_cross = g_ok & has
            rejected["no_crossing"] += int((g_ok & ~has).sum())
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
                    if w[k] <= 0:
                        continue
                    for gi in np.flatnonzero(g_cross & (cross == c)):
                        rows.append((float(w[k]), lp, hp, float(gains[gi]), pol, float(delays[k]), int(c), oi,
                                     leak100 + float(gains[gi]), leak_hi + float(gains[gi])))
        return rows

    def accept(row):
        """The hard limits and the dip, walked only for rows the sort reaches: (split gain, split delay) or None."""
        width, lp, hp, g, pol, d, c, oi, _l100, _lhi = row
        gain = _gain_split(g, inp.gain_range)
        if gain is None:
            rejected["gain"] += 1
            return None
        tas = _delay_split(d, offsets[oi], inp.max_ms, single_upper)
        if tas is None:
            rejected["delay"] += 1
            return None
        if inp.dip_on and inp.target_db is not None:
            s = (-1.0 if pol == "INV" else 1.0) * 10.0 ** (g / 20.0) * inp.ref_lower * lp_bank.get(lp)[0]
            w = _front_sum(inp.ref_l, inp.ref_r, f, offsets[oi]) * hp_bank.get(hp)[0] \
                * np.exp(-2j * np.pi * f * d * 1e-3)
            if _dip_db(f, s, w, inp.target_db, cls) < DIP_LIMIT_DB:
                rejected["dip"] += 1
                return None
        return gain, tas

    def shortlist(rows):
        by_band = {}
        for row in rows:
            label = _band_label(edges, float(f[row[6]]))
            if label:
                by_band.setdefault(label, []).append(row)
        kept = {}
        for label, members in by_band.items():
            members.sort(key=lambda r: -r[0])
            out = []
            for row in members:
                if accept(row) is not None:
                    out.append(row)
                    if len(out) >= SHORTLIST_PER_BAND:
                        break
            if out:
                kept[label] = out
        return kept

    pairs = [(tuple(lp), tuple(hp)) for lp in inp.lp_options for hp in inp.hp_options]
    all_rows, seen = [], set()
    for oi in range(len(offsets)):
        all_rows += scan(pairs, oi, seen)
    short = shortlist(all_rows)

    # +-1/12 oct around the shortlist: the coarse grid found the place, the neighbours refine the corners.
    fresh = set()
    for members in short.values():
        for row in members:
            for lp in _neighbours(row[1], cls.lp_bounds, inp.xo):
                for hp in _neighbours(row[2], cls.hp_bounds, inp.xo):
                    if hp[2] >= inp.hp_floor_hz:
                        fresh.add(((tuple(lp), tuple(hp)), row[7]))
    extra = []
    for oi in range(len(offsets)):
        extra += scan([p for p, o in fresh if o == oi], oi, seen)
    if extra:
        all_rows += extra
        short = shortlist(all_rows)

    rows = []
    for label, members in short.items():
        band_rows = [_score_points(inp, row, label, offsets, lp_bank, hp_bank, step, cls, m0, cw_mask, single_upper)
                     for row in members]
        rows += [r for r in band_rows if r is not None]
    rows.sort(key=_row_key, reverse=True)
    bands = {}
    for r in rows:
        bands.setdefault(r["band"], []).append(r)
    return {"rows": rows, "bands": bands, "rejected": rejected,
            "grid": {"pairs": len(pairs), "lp_options": [list(o) for o in inp.lp_options],
                     "hp_options": [list(o) for o in inp.hp_options], "lr_offsets": len(offsets),
                     "gains": len(gains), "delays": len(delays), "scored_rows": len(all_rows)}}


def _row_key(r):
    """The ranking: worst point's band, median's band, the summation loss; among ties the sum nearest the target."""
    return (r["width_worst_oct"], r["width_median_oct"], -99.0 if r["loss_median_db"] is None else r["loss_median_db"],
            -99.0 if r["dip_median_db"] is None else -abs(r["dip_median_db"]))


def _public(row):
    """The row as a reader gets it: numbers rounded for reading (the ranking used the unrounded values)."""
    out = dict(row)
    for key, n in (("width_worst_oct", 2), ("width_median_oct", 2), ("loss_median_db", 2), ("dip_median_db", 2),
                   ("leak100_db", 1), ("leak_hi_db", 1), ("crossing_hz", 1)):
        out[key] = _round(out[key], n)
    return out


def _round(v, n=2):
    return None if v is None else round(float(v), n)


def _score_points(inp, row, label, offsets, lp_bank, hp_bank, step, cls, m0, cw_mask, single_upper):
    """Every point, the delay refined there: worst then median of the ±30 degree band, then the summation loss."""
    f = np.asarray(inp.freqs, float)
    _coarse_w, lp, hp, g, pol, d, _c, oi, leak100, leak_hi = row
    xs, xw = lp_bank.get(lp)[0], hp_bank.get(hp)[0]
    sign = -1.0 if pol == "INV" else 1.0
    s = sign * 10.0 ** (g / 20.0) * inp.lower * xs
    w = _front_sum(inp.upper_l, inp.upper_r, f, offsets[oi]) * xw
    gap = _db(s) - _db(w)
    base = np.degrees(np.angle(s)) - np.degrees(np.angle(w))
    fine = d + np.arange(-int(round(DELAY_FINE_SPAN_MS / DELAY_FINE_STEP_MS)),
                         int(round(DELAY_FINE_SPAN_MS / DELAY_FINE_STEP_MS)) + 1) * DELAY_FINE_STEP_MS
    fine = fine[np.abs(fine) <= inp.max_ms + 1e-9]
    if fine.size == 0:
        return None
    rot = 360.0 * f[None, :] * fine[:, None] * 1e-3
    widths = np.zeros((len(inp.points), len(fine)))
    crossings = [None] * len(inp.points)
    for p in range(len(inp.points)):
        c = _crossing(gap[p], cw_mask, m0)
        crossings[p] = c
        if c is None:
            continue
        a = np.abs(((base[p][None, :] + rot + 180.0) % 360.0) - 180.0)
        widths[p] = _widths(a <= PHASE_WINDOW_DEG, c, step)
    worst = widths.min(0)
    median = np.median(widths, axis=0)
    # worst first, then the median; the plateau's centre on a tie
    top = worst >= worst.max() - 1e-9
    k = int(np.flatnonzero(top)[_plateau_centre(median[top])])
    d_best = float(fine[k])
    tas = _delay_split(d_best, offsets[oi], inp.max_ms, single_upper)
    if tas is None:
        return None
    gain = _gain_split(g, inp.gain_range)
    if gain is None:
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
        return None
    fs_margin = None
    if inp.fs_upper_hz:
        fs_margin = _cc.fs_margin(hp[2], inp.fs_upper_hz, order=max(hp[1] // 6, 1))["verdict"]
    return {"lp": list(lp), "hp": list(hp), "sub_rel_db": g, "sub_gain_db": gain[0], "front_gain_db": gain[1],
            "polarity": pol, "delay_ms": round(d_best, 3), "who_delays": "none" if abs(d_best) < 1e-6 else ("front" if d_best > 0 else "sub"),
            "ta_ms": tas, "lr_offset_ms": 0.0 if single_upper else round(float(offsets[oi]), 3),
            "crossing_hz": float(np.median(fxs)), "width_worst_oct": float(worst[k]), "width_median_oct": float(median[k]),
            "loss_median_db": float(np.median(losses)) if losses else None,
            "dip_median_db": float(np.median(dips)) if dips else None, "leak100_db": float(leak100),
            "leak_hi_db": float(leak_hi), "fs_margin": fs_margin, "band": label, "marks": list(inp.marks)}


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
                _h, info = P.load_solo_v7(path, freqs, keep_ir=True)
            else:
                title = naming.generate_name(code, ver, "sw", position=pos)
                if title not in have:
                    continue
                _h, info = P.load_solo_rew(title, freqs, api=api, keep_ir=True)
            groups.setdefault(key, {})[code] = (read_window(info["ir"], freqs), info)
    notes = []
    for key, loaded in groups.items():
        corrected, these, refused = P.de_embed_solos(loaded, freqs, record=record, baseline=True)
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
        raise JointSearchError(f"the L-R arrival of the {role} needs both channels at the centre points")
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


def _ref_curve(chan, code):
    if chan["tripod"] is not None:
        return chan["tripod"]
    for pos in ("p5", "p1", "p9"):
        if pos in chan["points"]:
            return chan["points"][pos]
    raise JointSearchError(f"{code}: neither a tripod solo nor a centre point (p1/p5/p9)")


def _build_bass_input(joint, *, curves, lower_curves, freqs, single_point, lp_options, hp_options, gains, max_ms, gain_range,
                      target_db, free_offset, hp_floor_hz, fs_upper_hz, xo, cls, marks):
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
    # a lower branch that is a real pair is summed here, once, its own L-R offset held
    if not lower.single:
        positions = ("tripod",) if single_point else CENTRE_POINTS
        rule = lr_rule_ms(chan_l[0], chan_l[1], lower.role, positions=positions)
        sum_low = _front_sum(low_stack[0], low_stack[1], freqs, rule)
        ref_low = _front_sum(_ref_curve(chan_l[0], lower.codes[0]), _ref_curve(chan_l[1], lower.codes[1]), freqs, rule)
    else:
        sum_low = low_stack[0]
        ref_low = _ref_curve(chan_l[0], lower.codes[0])
    rule_ms, notes = 0.0, []
    if not upper.single:
        positions = ("tripod",) if single_point else CENTRE_POINTS
        try:
            rule_ms = lr_rule_ms(chan_u[0], chan_u[1], upper.role, positions=positions)
        except JointSearchError as exc:
            if not free_offset:
                raise
            notes.append(f"the free L-R offset is searched around 0, not the raw offset: {exc}")
    return BassInput(freqs=freqs, points=points, lower=sum_low, upper_l=up_stack[0],
                     upper_r=None if upper.single else up_stack[1], ref_lower=ref_low,
                     ref_l=_ref_curve(chan_u[0], upper.codes[0]),
                     ref_r=None if upper.single else _ref_curve(chan_u[1], upper.codes[1]),
                     lp_options=lp_options, hp_options=hp_options, gains_db=gains, max_ms=max_ms, gain_range=gain_range,
                     target_db=target_db, lr_rule_ms=rule_ms, free_lr_offset=free_offset, sub_one_point=sub_one_point,
                     hp_floor_hz=hp_floor_hz, fs_upper_hz=fs_upper_hz, marks=marks, joint=cls, xo=xo, notes=notes)


# ---------------------------------------------------------------- the report
def _filter_name(opt):
    return f"{opt[0]}{opt[1]}@{opt[2]:g}"


def render(doc):
    joint = doc["joint"]
    lines = [f"Joint {joint} ({doc['joint_class']}): {doc['grid']['pairs']} filter pairs. "
             f"Stack: {' / '.join(doc['joints_in_stack'])}. L-R offset held at {doc['conditions']['lr_offset_ms']:+.2f} ms."]
    for label, rows in doc["bands"].items():
        lines.append(f"\nCrossing {label}:")
        lines.append(f"  {'LP':>12} {'HP':>12} {'sub dB':>7} {'pol':>5} {'delay':>7} {'delay on':>9} {'worst oct':>9} "
                     f"{'med oct':>7} {'loss dB':>7} {'dip dB':>6} {'leak100':>7} {'Fs':>7}")
        for r in rows:
            lines.append(f"  {_filter_name(r['lp']):>12} {_filter_name(r['hp']):>12} {r['sub_rel_db']:>+7.1f} {r['polarity']:>5} "
                         f"{r['delay_ms']:>+7.2f} {r['who_delays']:>9} {r['width_worst_oct']:>9.2f} {r['width_median_oct']:>7.2f} "
                         f"{r['loss_median_db'] if r['loss_median_db'] is not None else float('nan'):>7.2f} "
                         f"{r['dip_median_db'] if r['dip_median_db'] is not None else float('nan'):>6.1f} "
                         f"{r['leak100_db']:>7.1f} {r['fs_margin'] or '':>7}"
                         + (f"  [{', '.join(r['marks'])}]" if r["marks"] else ""))
    lines.append("")
    rej = {k: v for k, v in doc["rejected"].items() if v}
    lines.append("Rejected: " + (", ".join(f"{k} {v}" for k, v in rej.items()) if rej else "nothing"))
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
    ap.add_argument("--allow-large-grid", action="store_true", help=f"over {GRID_CEILING_PAIRS} filter pairs, run anyway")
    ap.add_argument("--top", type=int, default=TOP_DEFAULT, help="rows per crossing band")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out", metavar="DIR", help="write the table and the JSON here")
    args = ap.parse_args(argv)
    if bool(args.solos) == bool(args.rew):
        raise JointSearchError("give exactly one of --solos DIR or --rew --ver N")
    if args.rew and not args.ver:
        raise JointSearchError("--rew needs --ver N")
    project_dir = args.project
    space = space_of(project_dir)
    if space.rate_note:
        print(f"  ⚠ {space.rate_note}", file=sys.stderr)
    channels = _xw._channels(project_dir)
    joints = joints_of(channels)
    if args.joint != "bass":
        raise JointSearchError(f"joint {args.joint!r}: this build searches the bass joint only (--joint bass)")
    bass = [j for j in joints if j.cls == "bass"]
    if not bass:
        raise JointSearchError(f"no bass joint in this stack ({' / '.join(j.name for j in joints) or 'no joints'}): the channels "
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
    gains = [float(g) for g in np.arange(g_lo, g_hi + g_step / 2.0, g_step) if _gain_split(float(g), space.gain_range) is not None]
    if not gains:
        raise JointSearchError(f"no sub level in {g_lo:g}..{g_hi:g} dB fits the channel gain range {space.gain_range}")
    free = args.no_lr_offset
    if upper.single:
        n_off = 1
    elif free:
        n_off = 2 * int(round(FREE_OFFSET_SPAN_MS / FREE_OFFSET_STEP_MS)) + 1
    else:
        n_off = 1
    pairs = len(lp_options) * len(hp_options)
    combos = pairs * n_off
    print(f"grid: {len(lp_corners)} LP corners x {len(space.families)} families x {len(hp_corners)} HP corners x "
          f"{len(space.families)} families = {pairs} filter pairs x {n_off} L-R offsets (ceiling {GRID_CEILING_PAIRS}); "
          f"x {len(gains)} sub levels x 2 polarities x {2 * int(math.floor(space.delay_max_ms / DELAY_COARSE_STEP_MS)) + 1} "
          f"delays per pair on the reference point", file=sys.stderr)
    if combos > GRID_CEILING_PAIRS and not args.allow_large_grid:
        raise JointSearchError(f"{combos} filter pairs is over the ceiling {GRID_CEILING_PAIRS}: narrow --lp-bounds / --hp-bounds "
                               "or pass --allow-large-grid")
    # the capture
    if args.single_point:
        state_dir = os.path.join(_HERE, "state")
        if state_dir not in sys.path:
            sys.path.insert(0, state_dir)
        import process as _process
        if not _process._positions_asked(project_dir):
            raise JointSearchError("--single-point needs the person's recorded decision to skip the nine points "
                                   "(`process.py <dir> decision ...`): the session says the limits, the person decides")
    freqs = P.grid(cls.grid_hz[0], cls.grid_hz[1], GRID_PPO)
    two_sessions = (args.sub_solos and args.sub_solos != args.solos) or (args.sub_ver and args.sub_ver != args.ver)
    if two_sessions and not args.level_step:
        raise JointSearchError("the sub comes from another capture session: its level would read as the driver's imbalance; "
                               "--level-step LO:HI names the control band the sessions are levelled over")
    record = None
    if args.rew:
        state_dir = os.path.join(_HERE, "state")
        if state_dir not in sys.path:
            sys.path.insert(0, state_dir)
        import process as _process
        record = _process.Process(os.path.join(project_dir, "process")).protective_record_for(args.ver)
    upper_codes, lower_codes = list(upper.codes), list(joint.lower.codes)
    sources = {"solos": args.solos, "ver": args.ver, "api": None, "record": record}
    main, notes = load_channels(upper_codes + ([] if two_sessions else lower_codes), freqs, **sources)
    lower_curves = main
    if two_sessions:
        sub_record = None
        if args.rew and args.sub_ver:
            sub_record = _process.Process(os.path.join(project_dir, "process")).protective_record_for(args.sub_ver)
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
    house = target_bands.HouseCurve.from_file(args.house)
    target = np.array([house.at(float(x)) for x in freqs])
    marks = ("single-point",) if args.single_point else ()
    inp = _build_bass_input(joint, curves=main, lower_curves=lower_curves, freqs=freqs, single_point=args.single_point,
                            lp_options=lp_options, hp_options=hp_options, gains=tuple(gains), max_ms=space.delay_max_ms,
                            gain_range=space.gain_range, target_db=target, free_offset=free, hp_floor_hz=floor,
                            fs_upper_hz=fs_upper, xo=space.xo, cls=cls, marks=marks)
    res = scan_bass(inp)
    top = max(1, int(args.top))
    bands = {k: [_public(r) for r in v[:top]] for k, v in res["bands"].items()}
    grid = dict(res["grid"], ceiling=GRID_CEILING_PAIRS)
    doc = {"joint": joint.name, "joint_class": joint.cls, "joints_in_stack": [j.name for j in joints],
           "grid": grid, "rows": [_public(r) for r in res["rows"]], "bands": bands, "rejected": res["rejected"],
           "conditions": {"lr_offset_ms": 0.0 if upper.single else round(inp.lr_rule_ms, 3),
                          "lr_offset_tolerance_ms": LR_OFFSET_TOLERANCE_MS,
                          "lr_offset_held": (not free) and (not upper.single),
                          "sub_one_point": inp.sub_one_point, "hp_floor_hz": round(floor, 1)},
           "notes": notes + inp.notes, "note": "This never picks: the table describes and the choice is the tuner's."}
    text = render(doc)
    if args.out:
        project_io.atomic_write_json(os.path.join(args.out, f"joint-{joint.name}.json"), doc, makedirs=True)
        project_io.atomic_write_text(os.path.join(args.out, f"joint-{joint.name}.txt"), text + "\n", makedirs=True)
    print(json.dumps(doc, indent=2, ensure_ascii=False) if args.json else text)
    return 0


def _main(argv=None):
    """The command line. Every refusal is one line, `refusing: <why>`, exit 3: this tool's, predict's and an unreadable profile's."""
    try:
        return _cli(argv)
    except Exception as exc:  # noqa: BLE001 -- matched by its attribute; anything else still raises
        if not (getattr(type(exc), "is_refusal", False) or getattr(type(exc), "is_unreadable", False)):
            raise
        print(f"refusing: {exc}", file=sys.stderr)
        return 3


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
    assert check_stage(polarities=("NORM", "INV")), "L and R of opposite polarity should be rejected"
    assert check_stage(families=(("LR", 24), ("BW", 24))), "L and R of different families should be rejected"
    assert not check_stage(polarities=("INV", "INV"), families=(("BE", 24), ("BE", 24)))


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


def _write_ir(path, at, *, rew_source=None):
    import resonalyze_ir as ri
    x = np.zeros(1 << 13)
    x[at] = 0.5
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


_TINY = ["--lp-bounds", "50:71", "--hp-bounds", "71:100", "--gain", "0:4:2"]
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
        _process.Process(os.path.join(proj, "process")).record_decision("the ellipsoid capture?", "no positions, one point only")
        solos2 = os.path.join(top, "solos2")
        _write_solos(solos2, ("sw", "w-L", "w-R"), at={"w-L": 200, "w-R": 100})
        rc, out, err = _run(["--project", proj, "--house", house, "--solos", solos2, "--single-point", "--json"] + _TINY)
        assert rc == 0, (rc, err[-400:])
        doc = json.loads(out)
        assert doc["rows"] and all("single-point" in r["marks"] for r in doc["rows"]), doc["rows"][:1]
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _selftest():
    failures = []
    for check in (_check_joints_from_roles, _check_planted_delay_polarity_corners, _check_family_outside_profile_never_returned,
                  _check_lr_offset_condition, _check_leak_and_dip_conditions, _check_sub_one_point_limit, _check_hp_floor,
                  _check_refusals_are_one_line, _check_protective_refusal_passed_on, _check_cli_end_to_end):
        try:
            check()
        except AssertionError as exc:
            failures.append(f"{check.__name__}: {exc}")
    assert not failures, "\n".join(failures)
    print("selftest OK -- the joints come from the roles; a planted delay, polarity and corner pair are found by a margin, "
          "on either side of the delay; a family outside the profile never comes back; the L-R offset condition holds; "
          "leak and dip reject; every refusal is one line, exit 3; nothing is picked")
    return 0


if __name__ == "__main__":
    import console                       # issue #21: a code page must not destroy a result
    console.install()
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    sys.exit(_main())
