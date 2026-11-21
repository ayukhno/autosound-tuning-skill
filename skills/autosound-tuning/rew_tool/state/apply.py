"""apply-change — the gate that turns a proposed hard-params delta into (a) a banked snapshot and
(b) the human-applicable SETTINGS SHEET the Arbiter keys into the PC-Tool screen.

Why this exists (the unlock both v3 reviews pointed at): the DSP is written by the Arbiter's HAND in
Helix — no script can interpose on that. So the gate does not "apply" to the device; it earns its
keep by being the ONLY producer of an artifact the human actually needs — the clean channel/param
old→new sheet (with samples derived for the active rate). Bypass the gate and you get nothing usable,
so the compliant path is also the easiest path. That inversion is what makes v3 hold where v2's
"you must" prose did not.

Lifecycle (AD-1): `propose` banks a 🟡 snapshot with the changed channels marked `proposed` and hands
back the settings sheet → the Arbiter enters it in Helix by HAND → `attest` banks a 🟢 snapshot
flipping those channels to `applied`. `measured` follows when a control measurement confirms effect.
The state file is truth for INTENT + ATTESTED-APPLIED, never a guaranteed device mirror.

Gate policy (per AD-2):
  * DETERMINISTIC REFUSALS (hard — correctness/process, not acoustic taste): unknown channel/field
    (typo protection), partial delta onto a non-existent channel, TA given as samples instead of the
    canonical ms, and any resulting state that fails `state.validate`.
  * ADVISORIES (soft — the old "rails on nouns" demoted to voice-with-waiver): a large gain jump, a
    polarity flip, a big delay or crossover move. Printed as ⚠️, never blocking — the Arbiter's ear
    and measurement are the authority on the acoustic nouns.

Tier-aware (schema v2, 2026-07-29): a delta may address any tier the ledger already has (any top-
level key `state.tier_names()` recognizes), not just `channels` — e.g.
`{"virtual_channels": {"VFL": {"gain_db": -1.0}}, "channels": {"w-L": {"ta_ms": 5.45}}}`. The old
FLAT form (`{channel: {field: value}}`) still means `channels`, unchanged — a delta is read as
tier-keyed only when every one of its top-level keys is already a known tier name, so an ordinary
channel-name delta is never misread. A tier a project's ledger doesn't have YET cannot be addressed
this way — intake seeds every profile-declared tier, even empty, at the first snapshot.
"""

import contextlib
import copy
import datetime
import json
import os
import sys

import state as _state


def _write_lock():
    """`rew_tool/write_lock.py`, through the ledger's own loader: one module object, so a hold taken here is the one
    `PresetHistory.snapshot` re-enters (#141)."""
    return _state._siblings().load("write_lock.py")


def _held(history):
    """The project's writer lock over one bank -- the snapshot, its delta and its sheet (#141, J2b) -- held on the
    history's own project, `history.project_dir`: the folder its snapshot holds, spelled the same, so that hold
    re-enters this one instead of waiting for it on its own thread. A history that names no project holds nothing
    here, and its snapshot holds its own."""
    project_dir = getattr(history, "project_dir", None)
    return _write_lock().hold(project_dir) if project_dir else contextlib.nullcontext()

# ── evidence-gated banking (#57 P2, #58 P7/P11) ─────────────────────────────────────────────────
# `finish_step` refused prose-only evidence while `propose` accepted anything: it banked a polarity flip
# whose only support was a single-point sweep the tool itself had marked UNVERIFIED, and a centre
# crossover derived from a filtered measurement -- both reverted the next day. So a STRUCTURAL move
# (polarity, a delay, a crossover edge, a gain step at or above the threshold) banks as a PROPOSAL only
# with evidence that resolves and one reviewer call behind it; without them it banks as a 🟠 CANDIDATE:
# a version on the line, visible, never placed in the slot and never attested (#58 P11: a candidate is
# fast, a banked version is proven). EQ inside a channel's own band stays as it was -- never the problem.
#: A polarity and a crossover edge always count. A delay counts from half a millisecond (a junction's alignment,
#: not a desk's fine trim) and a gain from the advisory threshold below (#57 P2: "above an advisory threshold").
STRUCTURAL_GAIN_DB = 6.0
STRUCTURAL_TA_MS = 0.5
_REFUSED_VERDICTS = ("UNVERIFIED", "BLOCK", "BLOCKED", "REFUSED")


def structural_moves(current, proposed):
    """`["w-L polarity", "tw-L hp", "sub-2 removed", ...]` -- the moves that need evidence to bank as a proposal. A row
    `current` has and `proposed` does not is one: the sheet tells the person to mute or remove that driver (#199)."""
    out = []
    for tier in _state.tier_names(proposed):
        for ch, row in (proposed.get(tier) or {}).items():
            was = (current.get(tier) or {}).get(ch) or {}
            if (row or {}).get("polarity") != was.get("polarity") and "polarity" in (row or {}):
                out.append(f"{ch} polarity")
            for leg in ("hp", "lp"):
                if leg in (row or {}) and row.get(leg) != was.get(leg):
                    out.append(f"{ch} {leg}")
            ta, ta0 = (row or {}).get("ta_ms"), was.get("ta_ms")
            if isinstance(ta, (int, float)) and (not isinstance(ta0, (int, float)) or abs(ta - ta0) >= STRUCTURAL_TA_MS):
                if ta != ta0:
                    out.append(f"{ch} delay")
            g, g0 = (row or {}).get("gain_db"), was.get("gain_db")
            if isinstance(g, (int, float)) and isinstance(g0, (int, float)) and abs(g - g0) >= STRUCTURAL_GAIN_DB:
                out.append(f"{ch} gain")
    for tier in _state.tier_names(current):
        out += [f"{ch} removed" for ch in (current.get(tier) or {}) if ch not in (proposed.get(tier) or {})]
    return out


def evidence_problems(evidence, project_dir):
    """`[]` when every item resolves, else what does not: a measurement title in the grammar, or a file (a tool's
    verdict) that exists and does not say UNVERIFIED/BLOCK. Prose resolves to nothing, as in `finish_step`.

    **A DESK result is evidence** (the Arbiter, 2026-09-23: «у нас є математика своя і Resonalyze … я хочу щоб
    підходи до машини були мінімальні на перших етапах»): `predict --out …/predicted.json`, `resonalyze_engine run
    --out …/variants.json`, an `--align` proposal. The car is for VERIFYING, once for several changes
    (`state.py … verification-set <last verified> <now>`), not a trip per change."""
    items = [evidence] if isinstance(evidence, str) else list(evidence or [])
    if not items:
        return ["no evidence: a desk result (the file `predict --out` or `resonalyze_engine run --out` wrote) or "
                "a measurement title -- no car trip is needed for the first"]
    import naming as _naming
    bad = []
    for item in items:
        text = str(item).strip()
        path = text if os.path.isabs(text) else os.path.join(project_dir or "", text)
        if os.path.isfile(path):
            try:
                with open(path, encoding="utf-8") as fh:
                    doc = json.load(fh)
            except (OSError, ValueError):
                doc = None
            said = str((doc or {}).get("verdict") or (doc or {}).get("status") or "").upper() if isinstance(doc, dict) else ""
            if any(s in said for s in _REFUSED_VERDICTS):
                bad.append(f"{text}: the tool itself says {said} -- that is not evidence to bank on")
            continue
        if _naming.parse_name(text):
            continue
        bad.append(f"{text!r}: neither a measurement title in the grammar nor a file")
    return bad


# advisory thresholds — voice, not veto
_GAIN_JUMP_DB = 6.0
_TA_JUMP_MS = 2.0
_XOVER_FACTOR = 1.5

_MERGEABLE = set(_state.CHANNEL_FIELDS)


def _split_by_tier(current, delta):
    """Classify `delta` as flat (`{channel: {field: value}}`, meaning `channels`) or tier-keyed
    (`{tier: {channel: {field: value}}}`) and return it normalized to `{tier: {channel: fields}}`.

    Deterministic, not guessed: tier-keyed ONLY when every top-level key of `delta` is already a
    tier `current` has (`state.tier_names`) — a delta naming an ordinary channel can never collide
    with this, since channel names are never also tier names.
    """
    if delta and set(delta) <= set(_state.tier_names(current)):
        return delta
    return {"channels": delta}


def _merge_preset_settings(proposed, settings):
    """Merge a delta's `preset_settings` into `proposed`, two levels deep: one `fx` switch leaves the others (#197,
    #200). It is no tier, so it is taken out before `_split_by_tier`, which would wrap it as a channel. A delta cannot
    give a `source_file`: that is `attest --source-file`, the claim that a version was compared to a file."""
    if not isinstance(settings, dict):
        raise ValueError(f"{_state.PRESET_SETTINGS} in a delta must be an object, got {settings!r}")
    if "source_file" in settings:
        raise ValueError(f"{_state.PRESET_SETTINGS}.source_file is not given by a delta: a new version was not compared "
                         f"to that file -- it goes through `attest --source-file`")
    merged = proposed.get(_state.PRESET_SETTINGS)
    merged = copy.deepcopy(merged) if isinstance(merged, dict) else {}
    for key, value in settings.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key].update(value)
        else:
            merged[key] = value
    merged["status"] = "proposed"
    _state.validate_preset_settings(merged)
    proposed[_state.PRESET_SETTINGS] = merged


def _drop_source_file(proposed):
    """A new version was not compared to the file the one before it was read from: its `source_file` is not carried
    over (#200). A field left with nothing but its status goes with it."""
    settings = proposed.get(_state.PRESET_SETTINGS)
    if isinstance(settings, dict) and "source_file" in settings:
        del settings["source_file"]
        if not set(settings) - {"status"}:
            del proposed[_state.PRESET_SETTINGS]


def _row_key(rows, name, identity):
    """The row a delta means, given the name it was addressed to — SCR-039.

    A ledger row's key is the channel's ID, which defaults to its code; the two only differ once a
    channel has been renamed. A caller then addresses it by the name it goes by now, and the row is
    sitting under the old one. Without this the delta would look like a brand-new channel: refused
    if partial (confusing but safe), and silently banked as a SECOND row for the same driver if the
    caller happened to give a full definition. `identity` is `state.project_channels()`, which maps
    the id, the current code and every previous name onto one entry.

    Falls through to the name, in the hyphen notation, whenever there is nothing to resolve — no project file, an
    unknown channel, or a project that has never renamed anything (i.e. almost always).

    Both notations are one name (S-079, the Arbiter 2026-10-01): when nothing matches as typed, the
    identity map and the row keys are compared in the one notation (`naming.canonical_code`), so a
    delta for `w_L` lands on the row `w-L` and the other way round. Two rows that are one name that
    way are refused, not merged: which one the delta meant is not guessed.
    """
    def aliases(entry):
        if not isinstance(entry, dict):
            return []
        return [str(a) for a in [entry.get("id"), entry.get("code"), *(entry.get("previous_names") or [])] if a]

    import naming as _naming
    one = _naming.canonical_code
    key = one(str(name))
    # A ledger that already holds the name in BOTH notations (an old `w_L` row beside the live `w-L`): an exact
    # match would update whichever was typed, silently -- refused like any other two rows of one name.
    twins = [k for k in rows if one(str(k)) == key]
    if len(twins) > 1:
        raise ValueError(f"{name!r} is the rows {', '.join(map(repr, twins))} once `_` is read as `-` (S-079): "
                         f"two rows of one name, and which one this delta means is not guessed")
    if name in rows:
        return name
    entry = (identity or {}).get(name)
    for alias in aliases(entry):
        if alias in rows:
            return alias
    if not isinstance(entry, dict):
        # no channel under the name as typed: the one under it in the one notation, if exactly one is
        found = {id(e): e for k, e in (identity or {}).items() if isinstance(e, dict) and one(str(k)) == key}
        entry = next(iter(found.values())) if len(found) == 1 else None
    wanted = {key} | {one(a) for a in aliases(entry)}
    hits = [k for k in rows if one(str(k)) in wanted]
    if len(hits) > 1:
        raise ValueError(f"{name!r} is the rows {', '.join(map(repr, hits))} once `_` is read as `-` (S-079): "
                         f"two rows of one name, and which one this delta means is not guessed")
    # A channel with no row yet gets one under the hyphen: the notation that is written (the Arbiter, 2026-10-01).
    return hits[0] if hits else key


def apply_delta(current, delta, identity=None):
    """Merge a delta onto `current`, marking every touched row `proposed`.

    Crossover legs (hp/lp) are replaced wholesale. Raises ValueError on the deterministic-refusal
    cases (typos, phantom channels, samples-not-ms) — see `_split_by_tier` for the flat-vs-tier-
    keyed delta shapes this accepts.

    `identity` (optional, `state.project_channels()`) lets a delta address a renamed channel by its
    current name and still land on the row the ledger has always kept it under — `propose` passes
    it; a direct caller with no project on disk simply doesn't.

    `preset_settings`, beside the tiers (#197, #200), is merged on its own: `_merge_preset_settings`.
    """
    proposed = copy.deepcopy(current)
    if _state.PRESET_SETTINGS in delta:
        delta = dict(delta)
        _merge_preset_settings(proposed, delta.pop(_state.PRESET_SETTINGS))
    _drop_source_file(proposed)
    tier_delta = _split_by_tier(current, delta)
    for tier, rows in tier_delta.items():
        chans = proposed.setdefault(tier, {})
        for ch_name, fields in rows.items():
            if not isinstance(fields, dict):
                raise ValueError(f"delta[{tier}][{ch_name!r}] must be an object of field→value")
            unknown = [f for f in fields if f not in _MERGEABLE]
            if unknown:
                if "ta_samples" in unknown or "ta_smp" in unknown:
                    raise ValueError(f"{tier}.{ch_name}: TA must be given as canonical `ta_ms`, not "
                                     f"samples (samples are derived at render for the active rate)")
                raise ValueError(f"{tier}.{ch_name}: unknown field(s) {unknown} — "
                                 f"valid: {sorted(_MERGEABLE)}")
            key = _row_key(chans, ch_name, identity)
            if key not in chans:
                # Only `channels` (physical outputs) has required fields, so only there does a
                # brand-new row need a full definition; any other tier may start from a partial one.
                if tier == "channels":
                    missing = [f for f in ("hp", "lp", "gain_db", "ta_ms", "polarity") if f not in fields]
                    if missing:
                        raise ValueError(f"{ch_name} is not in the current state — to add a channel "
                                         f"give a full definition (missing {missing}); a partial "
                                         f"edit needs an existing channel (typo?)")
                chans[key] = {}
            chans[key].update(fields)
            chans[key]["status"] = "proposed"
    return proposed


def advisories(current, proposed):
    """Soft ⚠️ notes on the acoustic nouns — voice, waivable, never blocking. Walks every tier."""
    out = []
    for tier in sorted(set(_state.tier_names(current)) | set(_state.tier_names(proposed))):
        cch, pch = current.get(tier) or {}, proposed.get(tier) or {}
        for ch in sorted(set(cch) & set(pch)):
            a, b = cch[ch], pch[ch]
            label = ch if tier == "channels" else f"{tier}:{ch}"
            if isinstance(a.get("gain_db"), (int, float)) and isinstance(b.get("gain_db"), (int, float)):
                if abs(b["gain_db"] - a["gain_db"]) >= _GAIN_JUMP_DB:
                    out.append(f"{label}: gain jump {a['gain_db']:g}→{b['gain_db']:g} dB "
                               f"(≥{_GAIN_JUMP_DB:g}) — double-check it's intended.")
            if a.get("polarity") != b.get("polarity"):
                out.append(f"{label}: polarity {a.get('polarity')}→{b.get('polarity')} — verify by "
                           f"SUMMATION, not by eye (a flip that helps one joint can wreck another).")
            if isinstance(a.get("ta_ms"), (int, float)) and isinstance(b.get("ta_ms"), (int, float)):
                if abs(b["ta_ms"] - a["ta_ms"]) >= _TA_JUMP_MS:
                    out.append(f"{label}: TA jump {a['ta_ms']:g}→{b['ta_ms']:g} ms "
                               f"(≥{_TA_JUMP_MS:g}) — big move.")
            for leg in ("hp", "lp"):
                fa, fb = a.get(leg), b.get(leg)
                if isinstance(fa, dict) and isinstance(fb, dict) and fa.get("f") and fb.get("f"):
                    hi, lo = max(fa["f"], fb["f"]), min(fa["f"], fb["f"])
                    if lo and hi / lo >= _XOVER_FACTOR:
                        out.append(f"{label}: {leg.upper()} {fa['f']:g}→{fb['f']:g} Hz — large "
                                   f"crossover move; re-check the joint phase/summation.")
                # #58 P6: a value that DEPENDS on a changed one is flagged when it was carried over. Delays were
                # carried across 2800 BE24 → 3500 LR24 without a word: the delay at a junction was set for its
                # old edge, and a new edge (a new corner or a new family) moves where the members sum.
                if (fa != fb and isinstance(fb, dict) and fb.get("f") and "ta_ms" in b
                        and a.get("ta_ms") == b.get("ta_ms")):
                    out.append(f"{label}: {leg.upper()} changed and its delay {b.get('ta_ms'):g} ms did not — "
                               f"the delay was set for the old edge; re-read the junction before trusting it.")
    return out


def gain_grid_advisories(project_dir, current, proposed):
    """What a proposed channel trim meets on THIS machine's gain grid (skill #52), as advisories.

    The step is a PC-Tool setting (Channel Gain Resolution: 1.00 / 0.50 / 0.25 / 0.10 dB), not the device's. A sheet
    was once rounded to whole dB on a step recorded as a constant, and the mirror error is not caught anywhere: a sheet
    at 0.1 dB handed to a machine set to 1.00 is rounded by whoever types it, and what they typed is never recorded.
    With the project's `channel_gain.step_db` known, a trim off it is named; with it unknown, a trim with decimals
    is named with the question to ask. Advice, not a refusal: the number is right, the machine may simply be set
    coarser, and that is the tuner's switch.

    The profile is read through `load_profile` (#134, H 16): one that is there and cannot be read, or that a newer
    method wrote, is said -- the file, its repair, and that the step is not checked against the trims that moved. It
    was read as absent, and said nothing over a profile that may record a 1.00 dB step. No profile is no advisory."""
    moved = []
    for tier in _state.tier_names(proposed):
        for ch, row in (proposed.get(tier) or {}).items():
            g = (row or {}).get("gain_db")
            was = ((current.get(tier) or {}).get(ch) or {}).get("gain_db")
            if isinstance(g, (int, float)) and g != was:
                moved.append((ch, float(g)))
    if not moved:
        return []
    dsp_profile = _state._siblings().load("dsp_profile.py")
    path = os.path.join(project_dir or "", "dsp_profile.json")
    try:
        prof = dsp_profile._unwrap(dsp_profile.load_profile(path))
    except FileNotFoundError:
        return []
    except Exception as exc:  # noqa: BLE001 -- matched by its attribute; anything else still raises
        if not getattr(type(exc), "is_unreadable", False):
            raise
        return [f"{exc}; so the machine's gain step is not checked against "
                + ", ".join(f"{ch} {g:+g}" for ch, g in moved) + " (#52)"]
    gain = (prof.get("channel_gain") if isinstance(prof, dict) else None) or {}
    step = gain.get("step_db")
    if step:
        off = [(ch, g) for ch, g in moved if abs(g / step - round(g / step)) > 1e-6]
        if off:
            return [f"this machine is set to {step:g} dB gain steps (PC-Tool: Channel Gain Resolution): "
                    + ", ".join(f"{ch} {g:+g}" for ch, g in off) + " will be rounded when typed (#52)"]
        return []
    fine = [(ch, g) for ch, g in moved if abs(g - round(g)) > 1e-6]
    if fine:
        options = "/".join(f"{o:g}" for o in gain.get("step_options_db") or []) or "1/0.5/0.25/0.1"
        return ["the machine's gain step is not recorded; it is a PC-Tool setting (Channel Gain Resolution: "
                f"{options} dB). Ask it before " + ", ".join(f"{ch} {g:+g}" for ch, g in fine)
                + " is typed, and record it as `channel_gain.step_db` (#52)"]
    return []


def _fmt_val(field, val, rate):
    if field in _state.PRESET_FIELD_LABELS:
        return _state.fmt_preset_value(field, val)   # the preset's settings (#197, #200): dB, on/off, unknown
    if field == "ta_ms" and isinstance(val, (int, float)):
        # No rate -- a profile nobody could read (#147, item 2) -- is no samples: `—`, never the snapshot's guess.
        return f"{val:g} ms ({_state.samples_for(val, rate) if rate else '—'} smp)"
    if field in ("hp", "lp"):
        return _state._fmt_filter(val)
    if field == "gain_db" and isinstance(val, (int, float)):
        return f"{val:g} dB"
    if field == "eq" and isinstance(val, (list, tuple)):
        # Bands are structured objects (schema v2) -- render them the way the human keys them
        # into the EQ screen, not a Python list/dict repr. Empty = say so explicitly rather than
        # render "[]", since "no bands" is a real, enterable state.
        bands = _state.eq_str(val)
        return " · ".join(bands) if bands else "(no bands)"
    return str(val)


# Identity fields are absent on purpose (schema v3): they cannot appear in a ledger diff any
# more, so a label for them would describe a row this sheet can never contain.
_FIELD_LABEL = {"hp": "HP", "lp": "LP", "gain_db": "Gain", "ta_ms": "TA",
                "polarity": "Polarity", "eq": "EQ bands", "eq_ptr": "EQ export",
                "status": "status", "tag": "Tag",
                "mute": "Mute", "off": "Off", **_state.PRESET_FIELD_LABELS}


_DIFF_RESERVED_KEYS = ("from", "to", "preset")


def _preset_changes(diff):
    """The preset settings a diff carries (`[old, new]` under `preset`), as `[(path, label, was, now)]`."""
    pair = (diff.get("preset") or {}).get(_state.PRESET_SETTINGS)
    return _state.preset_settings_changes(pair) if pair else []


def _row_label(tier, ch):
    """`channels` rows stay bare (unchanged sheet format); any other tier is prefixed so a mixed
    proposal never reads as if two tiers shared one channel namespace."""
    return ch if tier == "channels" else f"{tier}:{ch}"


def settings_sheet(diff, rate, preset, version, slot_note=None, rate_said=None, base=None):
    """The compact 'APPLY THIS at the PC-Tool screen' table — only the changed fields, old→new,
    across EVERY tier the diff touched (schema v2 — a virtual-tier change used to be invisible here).

    This is the artifact the Arbiter keys in; ms is the source of truth, samples shown for the rate.
    Generated-only — it is a view of the diff, never edited by hand. `slot_note` (issue #5) stamps
    the header with the preset's active-slot status so the human never keys a change into the wrong slot.
    `rate_said` (`sheet_rate`'s line) says which rate the samples are for, under the header (#147, item 2).
    `base` (#199) is the version this one was built on, named in the header so a wrong base shows on paper; the rows
    are measured from `diff["from"]`, and when that is another version the line says so.
    """
    header = f"## APPLY THIS in Helix PC-Tool — {preset} · {version} (proposed)"
    if slot_note:
        header += f" · {slot_note}"
    lines = [header]
    if base:
        measured = diff.get("from")
        lines.append(f"{version} = {base} + this change."
                     + ("" if measured in (None, base) else
                        f" Old → New is against {measured}, the last version placed in the slot: these rows are "
                        f"everything that differs from it, not only this change."))
    lines.append("Enter only these. ms is the source of truth; samples shown for the active rate.")
    if rate_said:
        lines.append(rate_said)
    lines += ["", "| Channel | Param | Old → New |", "|---|---|---|"]
    any_row = False
    for path, label, was, now in _preset_changes(diff):
        lines.append(f"| Preset | {label} | {_fmt_val(path, was, rate)} → {_fmt_val(path, now, rate)} |")
        any_row = True
    for tier in sorted(k for k in diff if k not in _DIFF_RESERVED_KEYS):
        for ch, fields in diff[tier].items():
            label = _row_label(tier, ch)
            if fields.get("__added__"):
                lines.append(f"| {label} | — | ➕ NEW row — enable & set all params (see full sheet) |")
                any_row = True
                continue
            if fields.get("__removed__"):
                lines.append(f"| {label} | — | ➖ mute/remove row |")
                any_row = True
                continue
            for fld, (o, n) in fields.items():
                if fld == "status":
                    continue
                lines.append(f"| {label} | {_FIELD_LABEL.get(fld, fld)} | "
                             f"{_fmt_val(fld, o, rate)} → {_fmt_val(fld, n, rate)} |")
                any_row = True
    if not any_row:
        lines.append("| — | — | _(no hard-param changes)_ |")
    return "\n".join(lines)



def delta_rows(diff, rate):
    """The change, as rows, in the SAME words the settings sheet prints (SCR-026).

    The sheet is built from these; so is the front-end's card. Two renderers over one structure,
    rather than a front-end diffing two snapshots and guessing at intent -- a `gain_db` that moved
    could be a level-match trim or a banked decision, and the snapshots do not say which.
    """
    rows = [{"tier": _state.PRESET_SETTINGS, "channel": "preset", "param": label, "field": path,
             "was": _fmt_val(path, was, rate), "value": _fmt_val(path, now, rate), "was_raw": was, "value_raw": now}
            for path, label, was, now in _preset_changes(diff)]
    for tier in sorted(k for k in diff if k not in _DIFF_RESERVED_KEYS):
        for ch, fields in diff[tier].items():
            if fields.get("__added__"):
                rows.append({"tier": tier, "channel": ch, "param": None,
                             "was": None, "value": None, "added": True})
                continue
            if fields.get("__removed__"):
                rows.append({"tier": tier, "channel": ch, "param": None,
                             "was": None, "value": None, "removed": True})
                continue
            for fld, (o, n) in fields.items():
                if fld == "status":
                    continue
                rows.append({
                    "tier": tier, "channel": ch,
                    "param": _FIELD_LABEL.get(fld, fld), "field": fld,
                    # Rendered, not raw: these are the values the Arbiter keys in, and the sheet's
                    # own formatter is what turns 620.0 into "620 Hz LR36" and ms into samples.
                    "was": _fmt_val(fld, o, rate), "value": _fmt_val(fld, n, rate),
                    "was_raw": o, "value_raw": n,
                })
    return rows


def sheet_rate(project_dir, snapshot_rate):
    """`(rate, said)`: the rate the settings sheet derives its samples from, and the line that says which (#147, item
    2). The PROFILE's processing rate when the project's profile states one -- the Arbiter's ruling of 2026-08-25
    (`state.processing_rate`): the sheet is what he types into the DSP, and the DSP runs at the profile's rate --
    else the snapshot's, said as the snapshot's. A profile that is there and cannot be read (`is_unreadable`) is
    `(None, ...)`: no samples are derived, and the line says the file, why and its repair, as `PresetHistory.render`
    says it. The delta rows took the snapshot's rate whatever the profile said."""
    if project_dir:
        try:
            rate = _state.processing_rate(project_dir)
        except Exception as exc:  # noqa: BLE001 -- matched by its attribute; anything else still raises
            if not getattr(type(exc), "is_unreadable", False):
                raise
            return None, (f"processing rate: NOT READ — {exc} — so no samples are derived (ms is canonical; the "
                          f"snapshot recorded {snapshot_rate:g}, and the sheet follows the profile's rate)")
        if rate:
            return rate, (f"processing rate: {rate:g} Hz, the profile's (samples derived; ms is canonical)"
                          + (f" — the snapshot recorded {snapshot_rate:g}; samples follow the PROFILE rate"
                             if rate != snapshot_rate else ""))
        # The cause said as it is (group fix 1, item 12): no profile at all is not a profile that states none.
        why = ("the project's profile states none" if os.path.lexists(os.path.join(project_dir, "dsp_profile.json"))
               else "the project has no dsp_profile.json")
    else:
        why = "no project given"
    return snapshot_rate, (f"processing rate: {snapshot_rate:g} Hz, the snapshot's -- {why} (samples derived; ms is "
                           f"canonical)")


def write_delta(history, diff, rate, version, note=None, advisories=(), rate_said=None, unwritten=None):
    """Bank the change beside the snapshot: `proposals/<v_NNN>.json` (SCR-026), under the preset
    on the old layout and under `state/` on the per-project line (W-2 R).

    The ledger stores the state AFTER a change; the Arbiter's sheet is about the change itself, and
    the skill computed it, printed it and threw it away. Retyping numbers into chat is a
    transcription surface with no gate on it -- the same argument as `dsp-state-current` being
    generated rather than hand-written, applied to the sheet.

    Best effort by design: a proposal that is banked but whose delta file could not be written must
    not fail the proposal. The snapshot is the source of truth; this is a view. `rate` and `rate_said` are
    `sheet_rate`'s: the rate the rows' samples are for, None when none was read, and the line that says which.
    `unwritten`, a list, gets the line that says a file that could not be written, and why (group fix 1, item 6):
    `propose` puts it on the sheet -- TCC reads this file, and it went missing with nothing said.
    """
    out = {
        "schema_version": _state.SCHEMA_VERSION,
        "version": version,
        "from": diff.get("from"),
        "preset": history.preset,
        "at": datetime.datetime.now().isoformat(timespec="seconds"),
        "note": note,
        "preset_changes": diff.get("preset") or {},
        "settings": delta_rows(diff, rate),
        # Which rate the samples in `settings` are for (#147, item 2): the profile's, the snapshot's, or none read.
        "processing_rate_hz": rate,
        "processing_rate": rate_said,
        "advisories": list(advisories or ()),
    }
    path = os.path.join(getattr(history, "proposals_dir", os.path.join(history.dir, "proposals")),
                        f"{version}.json")
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
    except OSError as exc:
        if unwritten is not None:
            repair = _state._project_io().repair_for(exc, writing=True)
            unwritten.append(f"⚠️ {path} was not written ({exc.strerror or exc}) -- the version is banked; the change "
                             f"file beside it is not: {repair}")
        return None
    return path


def propose(history, delta, note=None, provenance=None, registry=None, allow_nonactive=False,
            evidence=None, reviewed=None, on=None):
    """Gate: validate the delta against its base, bank a 🟡 proposed snapshot, return the sheet.

    Returns {version, sheet, full_render, diff, advisories}. Raises ValueError on a deterministic
    refusal (the state is NOT banked on refusal — a garbage change can't slip through).

    Multi-slot integrity (issue #5): if `registry` is given and an active slot is set, REFUSE a
    proposal aimed at a different preset (the cross-slot anchoring trap — tuning Slot 3 off Slot 2's
    baseline), unless `allow_nonactive=True`. The settings sheet is stamped with the slot status.

    The base (#199) is HEAD unless `on` names another: `on=<version>` builds on that version of this slot and
    `on="HEAD"` confirms HEAD. With no `on`, a slot whose newest version is a candidate not in the slot is REFUSED: the
    delta would land on HEAD, without the candidate it was written against. Built on a candidate, the structural moves
    are measured from the candidate's own base, so what it has not earned stays held; with evidence and a reviewer its
    rows become `proposed` and it stops being a candidate. A candidate `variant switch` put in the slot is built on the
    same way, with no `on`, and promotion needs evidence and a reviewer even with no move of its own. A device read
    (`provenance`) vouches only for the rows it read: the others stay `candidate` and the version keeps its mark. A base
    that is not HEAD answers to the slot as well: its structural moves are also measured from the last placed version.
    The sheet is always measured against that version, every row it lists is `proposed`, and a version built on another
    base or on a candidate is no variant once it goes in the slot; a plain propose on a named variant keeps the name.

    One writer's step under the project's writer lock (#141, J2b): what it reads -- the active slot, HEAD, the
    channels, the profile -- and what it writes -- the version, its delta, its sheet -- are one hold (`_held`)."""
    with _held(history):
        return _propose(history, delta, note, provenance, registry, allow_nonactive, evidence, reviewed, on)


def _candidate_base(history, snap):
    """The state a candidate was made from (#199): up its `parent` line to the first version that is no candidate. A
    candidate banked before `parent` was kept on the old layout, or a line that loops, reads as the slot's HEAD; if that
    is a candidate too, as the previous version by number that is none. None when the slot has no such version: there
    is nothing to measure the candidate's moves from, and the caller holds the change."""
    seen = set()
    while snap.get("variant") == "candidate":
        parent = snap.get("parent")
        if not parent or parent in seen:
            snap = history.load()
            break
        seen.add(parent)
        snap = history.load(parent)
    if snap.get("variant") != "candidate":
        return snap
    versions = history.versions()
    own = snap.get("version")
    for earlier in reversed(versions[:versions.index(own)] if own in versions else versions):
        found = history.load(earlier)
        if found.get("variant") != "candidate":
            return found
    return None


def _mark_what_differs(proposed, in_dsp):
    """Every row the sheet will list is `proposed` (#199): measured from the last placed version, a row taken from the
    base can differ from it with no delta touching it, and `attest` flips only what is `proposed`. A status is no
    difference, and neither is a row or a setting that is gone (there is nothing left to mark)."""
    changed = _state.diff_states(in_dsp, proposed)
    for tier in _state.tier_names(proposed):
        for ch, fields in (changed.get(tier) or {}).items():
            if set(fields) - {"status", "__removed__"}:
                proposed[tier][ch]["status"] = "proposed"
    settings = proposed.get(_state.PRESET_SETTINGS)
    if isinstance(settings, dict) and _state.PRESET_SETTINGS in changed["preset"]:
        settings["status"] = "proposed"


def _has_candidate_rows(state):
    """Whether a row of any tier, or the preset's settings, is still marked `candidate`."""
    rows = [row for tier in _state.tier_names(state) for row in (state.get(tier) or {}).values()]
    rows.append(state.get(_state.PRESET_SETTINGS))
    return any(isinstance(row, dict) and row.get("status") == "candidate" for row in rows)


def _propose(history, delta, note, provenance, registry, allow_nonactive, evidence, reviewed, on=None):
    """`propose`'s work, with the project's lock held."""
    slot_note = None
    if registry is not None:
        active = registry.get_active()
        if active is not None:
            if history.preset != active and not allow_nonactive:
                raise ValueError(
                    f"⛔ SLOT MISMATCH — proposing to preset {history.preset!r} but the ACTIVE slot "
                    f"in the DSP is {active!r}. This is the issue-#5 cross-slot anchoring trap. Either "
                    f"`registry set-active {history.preset}` (if you really switched slots) or pass "
                    f"allow_nonactive=True for a deliberate off-slot edit.")
            slot_note = ("ACTIVE SLOT ✅" if history.preset == active
                         else f"⚠️ NON-ACTIVE SLOT (active={active})")
    head, versions = history.head(), history.versions()
    if on is None:
        newest = versions[-1] if versions else None
        if newest and newest != head and history.load(newest).get("variant") == "candidate":
            raise ValueError(f"the newest version {newest} is a candidate not in the slot; this delta would land on "
                             f"HEAD {head} — pass --on {newest} to build on the candidate, or --on HEAD")
    elif on != "HEAD" and on not in versions:
        raise ValueError(f"--on {on}: no such version in slot {history.preset!r} (it has {', '.join(versions) or 'none'})")
    base = head if on in (None, "HEAD") else on
    current = history.load(base)  # read-before-edit (raises if no baseline — seed via history.snapshot first)
    # What the sheet is measured from: what is in the DSP (#199). «Enter only these» on candidate → fix would leave out
    # the candidate's own changes if it were the candidate. What a structural move is measured from is its own base:
    # the candidate's moves have earned nothing by being built on. A candidate `variant switch` put in the slot is the
    # same case with no `on`: its moves earned nothing by being placed either.
    in_dsp = current if head in (None, base) else history.load(head)
    on_candidate = current.get("variant") == "candidate"
    # Channel identity (SCR-039), so a delta addressed to a renamed channel's CURRENT name reaches
    # the row the ledger keeps under its id instead of banking a second row for the same driver.
    identity = _state.project_channels(getattr(history, "project_dir", None) or "")
    proposed = apply_delta(current, delta, identity)   # deterministic refusals fire here
    if provenance is not None:
        proposed["provenance"] = provenance
    _mark_what_differs(proposed, in_dsp)
    d = _state.diff_states(in_dsp, proposed)        # note current has no version yet in-memory
    project_dir = getattr(history, "project_dir", None)
    adv = advisories(in_dsp, proposed) + gain_grid_advisories(project_dir, in_dsp, proposed)
    # #57 P2 / #58 P7: a structural move banks as a proposal only on evidence that resolves and one review. An
    # import of what the device already holds (`provenance`) is its own evidence and needs no review.
    # A base that is not HEAD answers to the slot too (#199): against the DSP's own state, `{}` on an older version is
    # every move between the two, and a named variant carries its moves in with it.
    measured_from = _candidate_base(history, current) if on_candidate else current
    moves = [] if measured_from is None else structural_moves(measured_from, proposed)
    if base != head:
        moves = list(dict.fromkeys(moves + structural_moves(in_dsp, proposed)))
    held = []
    if provenance is None:
        if measured_from is None:
            held.append(f"no version on slot {history.preset!r} that is not a candidate, so its structural moves cannot "
                        f"be measured from anything")
        # A candidate is promoted only on evidence and a review, moves or none (#199): one held by the slot check and
        # then switched in has no move against its own base.
        if moves or on_candidate:
            held += evidence_problems(evidence, project_dir)
            if not reviewed:
                held.append("no reviewer call behind it -- a structural change banks after one "
                            "(`scripts/autosound_ai.py critic <package> --record`, then `reviewed=<the review file>`)")
            elif not os.path.isfile(reviewed if os.path.isabs(str(reviewed))
                                    else os.path.join(project_dir or "", str(reviewed))):
                held.append(f"reviewed={reviewed!r}: no such review file")
    candidate = bool(held)
    if candidate:
        for tier in _state.tier_names(proposed):
            for ch, row in (proposed.get(tier) or {}).items():
                if (row or {}).get("status") == "proposed" and row != ((current.get(tier) or {}).get(ch)):
                    row["status"] = "candidate"
        settings = proposed.get(_state.PRESET_SETTINGS)
        if isinstance(settings, dict) and settings.get("status") == "proposed" \
                and settings != current.get(_state.PRESET_SETTINGS):
            settings["status"] = "candidate"
        proposed["variant"] = "candidate"
    elif on_candidate and provenance is None:
        # Evidence and a reviewer are there (#199): the candidate's rows are a proposal now, so `attest` covers them.
        # A device read is neither: it vouches for the rows it read, which `apply_delta` already made `proposed`.
        for tier in _state.tier_names(proposed):
            for row in (proposed.get(tier) or {}).values():
                if (row or {}).get("status") == "candidate":
                    row["status"] = "proposed"
        settings = proposed.get(_state.PRESET_SETTINGS)
        if isinstance(settings, dict) and settings.get("status") == "candidate":
            settings["status"] = "proposed"
    # Built on another base or on a candidate, what goes in the slot is a version on the line (#199). A plain propose on
    # a named variant is still that variant; a row left `candidate` keeps the mark, so `attest` still refuses it.
    if not candidate and (base != head or on_candidate) and not _has_candidate_rows(proposed):
        proposed.pop("variant", None)
    # The samples follow the profile's rate, said which (#147, item 2) -- not the snapshot's recorded one. Read before
    # the bank, so nothing it raises can leave a version banked with no sheet.
    rate, rate_said = sheet_rate(project_dir, proposed["sample_rate"])
    version = history.snapshot(proposed, note=note or ("candidate" if candidate else "proposed change"),
                               place=not candidate, parent=base)   # validates again + versions
    sheet = settings_sheet({**d, "to": version}, rate, history.preset, version, slot_note=slot_note,
                           rate_said=rate_said, base=base)
    unwritten = []
    write_delta(history, {**d, "to": version}, rate, version, note=note, advisories=adv, rate_said=rate_said,
                unwritten=unwritten)
    if unwritten:
        sheet += "\n\n" + "\n".join(unwritten)
    if adv:
        sheet += "\n\n⚠️ **Advisories (double-check, not blocking):**\n" + "\n".join("- " + a for a in adv)
    if candidate:
        sheet = (f"🟠 CANDIDATE {version} -- banked on the line, not in the slot yet. "
                 f"Structural: {', '.join(moves) or ('not measured' if measured_from is None else 'none against its base')}. "
                 f"What it waits for: " + "; ".join(held)
                 + f". Compute it at the desk (`predict`, `resonalyze_engine run`), then propose on it, `on={version}` "
                   "(`--on` on the command line) with the fix or an empty delta, `evidence=<that file>` and "
                   "`reviewed=` -- no car trip is needed for that.\n\n"
                 + sheet)
    else:
        sheet += (f"\n\nAfter entering these in Helix, run `attest {version}` to bank it 🟢 applied, "
                  f"then take a control measurement (→ 📏 measured).")
    sheet_path = write_sheet(project_dir, history.preset, version, sheet)
    return {"version": version, "sheet": sheet, "full_render": history.render(version),
            "diff": d, "advisories": adv, "candidate": candidate, "waits_for": held, "structural": moves,
            "sheet_path": sheet_path}


def write_sheet(project_dir, preset, version, sheet):
    """The settings sheet as a file the person can find: `<project>/docs/sheets/<v_NNN>-<slot>.md` (skill #61, the
    Arbiter: every document meant for him goes into the project's `docs/`). Best effort, like `write_delta`: the
    snapshot is the record; this is where he reads it. Returns the path written, or None."""
    if not project_dir:
        return None
    folder = os.path.join(project_dir, "docs", "sheets")
    path = os.path.join(folder, f"{version}-{preset}.md")
    try:
        os.makedirs(folder, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(f"# {preset} · {version} — the settings sheet\n\n{sheet.strip()}\n")
    except OSError:
        return None
    return path


def attest(history, version=None, note=None, source_file=None, door="--source-file"):
    """Arbiter confirms the proposed change was entered in Helix → flip its rows 🟡→🟢 applied,
    across EVERY tier (schema v2 — a virtual-tier row left 🟡 forever was the bug before this).

    Banks a new snapshot (immutable audit trail: proposed at v_N, applied at v_N+1). Attested =
    INTENT, not a device mirror — device-truth remains the latest measurement. HEAD is read and the snapshot banked
    under one hold of the project's writer lock (#141).

    `preset_settings` flips with the rows (#197, #200; it is no tier, so their walk does not reach it). `source_file`
    (#200) is the record of the saved preset this version was read from and what the comparison said. For a `.pct6`
    the method fills it itself (`attest_from_file`, #218); for any other DSP's file the session or the person does.

    The slot records what the DSP holds now (#201, `slots[slot].loaded`): the newly banked version, which is HEAD, under
    this same hold. The per-project line only; on the older layout no `slots.json` may appear.

    A candidate is refused (#199): it has earned no place in the DSP, and `propose --on` is how it earns one. `door` is
    the option the record came through (`--source-file`, `--from-file`), named in the refusal.
    """
    with _held(history):
        version = version or history.head()
        s = history.load(version)
        if s.get("variant") == "candidate":
            # Unearned, in the slot or not: an attest would bank it as entered, still marked candidate (#199, #201).
            raise ValueError(f"{version} is a candidate, not a proposal: it is not attested. Earn it first: "
                             f"`propose --on {version}` with evidence and a reviewer, then attest the version that makes")
        flipped = []
        for tier in _state.tier_names(s):
            for ch, c in (s.get(tier) or {}).items():
                if c.get("status") == "proposed":
                    c["status"] = "applied"
                    flipped.append(ch if tier == "channels" else f"{tier}:{ch}")
        settings = s.get(_state.PRESET_SETTINGS)
        if isinstance(settings, dict) and settings.get("status") == "proposed":
            settings["status"] = "applied"
            flipped.append(_state.PRESET_SETTINGS)
        if source_file is not None:
            held = s.get(_state.PRESET_SETTINGS) or {}
            if not set(held) - {"status", "source_file"}:
                # `preset_settings` would hold only the file: a dict of dicts, which a 3.2 copy reads as a tier instead
                # of refusing the field by name as it does a number. The ledger stays as it is, and the file is not lost.
                raise ValueError(f"{door}: {version} has no preset setting, and a {_state.PRESET_SETTINGS}.source_file "
                                 f"alone is misread by a 3.2 copy of the method as a tier of its own. Attest without "
                                 f"{door}, or bank a preset setting first (`propose` with `preset_settings`)")
            s.setdefault(_state.PRESET_SETTINGS, {})["source_file"] = source_file
        v = history.snapshot(s, note=note or f"attested applied ({', '.join(flipped) or 'no proposed rows'})")
        if history._project():
            history.record_loaded(v, "attest")
    return {"version": v, "applied_channels": flipped}


# ── --from-file (#218 T3): a saved .pct6, read only, through attest and propose ──────────────────────────────────────
def _from_file():
    """`state/from_file.py`, through the ledger's own loader: one module object."""
    return _state._siblings().load("state/from_file.py")


def _not_a_pct6(file_path):
    """`(2, refusal)` for a `.PR<n>` given to `--from-file`, else None: `--from-file` reads a `.pct6` (CONTRACT.md item
    14); a Mosconi preset is compared with `compare-file`, and nothing is banked from it."""
    cf = _compare_file()
    mp = cf._mosconi()
    if not mp.is_preset_path(file_path):
        return None
    return cf.EXIT_UNREADABLE, cf.refusal(mp.WARNING, os.path.basename(file_path), "model", (
        "--from-file reads a .pct6; a %s preset is compared with compare-file (apply.py <project-dir> compare-file "
        "<version> FILE), and nothing is banked from it" % os.path.splitext(file_path)[1]))


def attest_from_file(history, file_path, version=None, note=None):
    """`attest` with the `source_file` filled from the `.pct6` itself (#218 T3, S-119): the file read by `helix_pct6`,
    the version compared with it by compare-file (`compare_file.compare_journal`), and the record -- name, path, md5,
    saved, PC-Tool, device, when read, `compared` -- banked by `attest`, whose refusals hold as for `--source-file`.

    `(exit code, result)`: 0 and `attest`'s result with `source_file`, `device`, `warning`; else compare-file's refusal
    -- 2 the file cannot be read or interpreted, or is a `.PR<n>` (`model`), 3 it changed while it was read -- and
    nothing banked. A refusal of the journal's raises `ValueError`, as `attest` does -- a version whose leg slope or
    phase is no number among them (`compare_file._check_kinds`, as compare-file checks it). One hold of the writer lock
    over the read of the version, the file's and the bank: what is compared is what is attested."""
    refused = _not_a_pct6(file_path)
    if refused:
        return refused
    cf, ff = _compare_file(), _from_file()
    with _held(history):
        version = version or history.head()
        if not version:
            raise ValueError(f"the slot {history.preset!r} holds no version to attest")
        snap = history.load(version)
        cf._check_kinds(snap)
        identity = _state.project_channels(getattr(history, "project_dir", None) or "")
        code, result = cf.compare_journal((snap, identity), file_path)
        if code != cf.EXIT_COMPARED:
            return code, result
        source = ff.source_file(result, file_path)
        got = attest(history, version, note=note or f"attested, read back from {source['name']}", source_file=source,
                     door="--from-file")
    got.update(source_file=source, device=result["device"], warning=result["warning"],
               counts=result["counts"]["result"])
    return code, got


def propose_from_file(history, file_path, note=None, registry=None, allow_nonactive=False, on=None):
    """A NEW version from a `.pct6`'s values (#218 T3): `from_file.build` turns what the file gives every row the slot
    rules map -- level, delay, polarity, mute, phase, the legs, the EQ bands -- and the preset's settings into an
    ordinary delta, and `propose` banks it, the one door: no version is rewritten. What the file does not give stays as
    the base had it and is named (`kept`, `not_taken`, `notes`), in the result and in the version's `provenance`.

    The base is compared with the file first, on the same read (`compare_file.compare_doc`): a file compare-file
    refuses -- a value it cannot interpret at a path the base reaches, a delay `abc` -- is refused here too, exit 2,
    and a base it cannot compare is the journal's refusal. The read is a device read (`provenance`), as
    `setup_import`'s: its own evidence, and about the slot -- built on HEAD unless `on` names another version.
    `(exit code, result)` as `attest_from_file`: 0 and `propose`'s result with `kept`, `not_taken`, `notes`, `device`,
    `warning`; 2 or 3 and the refusal, nothing banked."""
    refused = _not_a_pct6(file_path)
    if refused:
        return refused
    cf, ff = _compare_file(), _from_file()
    with _held(history):
        code, read = ff.read_file(file_path)
        if code:
            return code, read
        base = history.head() if on in (None, "HEAD") else on
        if not base:
            raise ValueError(f"the slot {history.preset!r} holds no version to build on")
        snap = history.load(base)
        cf._check_kinds(snap)
        identity = _state.project_channels(getattr(history, "project_dir", None) or "")
        code, compared = cf.compare_doc((snap, identity), read["doc"], read["name"], inv=read["inv"])
        if code:
            return code, compared
        built = ff.build(snap, identity, read)
        got = propose(history, built["delta"], note=note or f"read from {read['name']}",
                      provenance=ff.provenance(read, built), registry=registry, allow_nonactive=allow_nonactive,
                      on=on or "HEAD")
    got.update(kept=built["kept"], not_taken=built["not_taken"], notes=built["notes"], base=base,
               device=read["device"], warning=read["warning"], file=read["name"])
    return 0, got


# ── self-test ─────────────────────────────────────────────────────────────────
def _check_cli_refuses_unreadable():
    """`propose` beside a `seals.json` that cannot be read exits 1 naming it and its repair, and banks nothing (#136):
    the snapshot refuses such a file now -- read as "no seals", the bank rewrote it holding its own seal alone -- and
    the refusal, neither an `OSError` nor a `ValueError`, ended here in a traceback."""
    import contextlib
    import io
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_apply_unreadable_")
    try:
        root = os.path.join(top, "state")
        _state.PresetHistory(root, "SQ", project_dir=top).snapshot(_state._sample_state(), note="baseline")
        _state.Registry(root).set_active("SQ")
        with open(os.path.join(top, "eq-delta.json"), "w", encoding="utf-8") as fh:
            json.dump({"w-L": {"gain_db": -1.0}}, fh)
        seals = os.path.join(root, _state.SEALS_FILE)
        damaged = b'{"v_001": "ab'
        with open(seals, "wb") as fh:
            fh.write(damaged)
        out, err = io.StringIO(), io.StringIO()
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = _main(["apply.py", top, "propose", "eq-delta.json", "--evidence", "w-L_2 (sw)"])
        except Exception as exc:  # noqa: BLE001 -- the failure under test is the traceback itself
            raise AssertionError(f"propose raised {type(exc).__name__}: {exc}") from None
        assert rc == 1 and err.getvalue().startswith(f"error: {seals} "), (rc, err.getvalue()[-300:])
        assert "checkout HEAD -- seals.json" in err.getvalue() and not out.getvalue(), out.getvalue()
        assert _state.project_versions(root) == ["v_001"], _state.project_versions(root)
        with open(seals, "rb") as fh:
            assert fh.read() == damaged, "seals.json changed"
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_gain_grid_says_an_unreadable_profile():
    """`gain_grid_advisories` reads the profile through `load_profile` (#134, H 16): one that is there and cannot be
    read, or that a newer method wrote, is said -- one advisory naming the file, its repair, and that the machine's
    gain step is not checked against the trims that moved. It was read as absent and gave no advisory at all, over
    a profile that may record a 1.00 dB step. No profile, and no trim moved, are still no advisory."""
    import shutil
    import tempfile
    d = tempfile.mkdtemp(prefix="autosound_gaingrid_unreadable_")
    try:
        path = os.path.join(d, "dsp_profile.json")
        base, moved = {"channels": {"w-L": {"gain_db": -7.0}}}, {"channels": {"w-L": {"gain_db": -1.2}}}
        newer = _state._siblings().load("dsp_profile.py").SCHEMA_VERSION + 1
        for label, raw, said in (
                ("cut off", b'{"dsp_profile": {"channel_gain": {"step_db": 1.0, "ste', "checkout HEAD -- dsp_profile.json"),
                ("a newer method's", json.dumps({"schema_version": newer, "dsp_profile": {
                    "channel_gain": {"step_db": 1.0}}}).encode("utf-8"), f"is schema v{newer}")):
            with open(path, "wb") as fh:
                fh.write(raw)
            got = gain_grid_advisories(d, base, moved)
            assert len(got) == 1 and got[0].startswith(f"{path} ") and said in got[0] \
                and "gain step is not checked" in got[0] and "w-L -1.2" in got[0], (label, got)
            assert gain_grid_advisories(d, base, base) == [], (label, "no trim moved: nothing to check")
        os.remove(path)
        assert gain_grid_advisories(d, base, moved) == [], "no profile is still no advisory"
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _check_a_held_lock_answers_75():
    """Another writer holding the project's lock makes `propose` and `attest` wait AUTOSOUND_LOCK_TIMEOUT_S and exit 75
    (#141, J2b): one `busy:` line, no traceback, and no version claimed, no delta, no sheet -- the ledger,
    `proposals/` and `docs/sheets/` as they were. Let go, the same `propose` lands."""
    import shutil
    import tempfile
    pj = _state._siblings().load("project.py")
    top = tempfile.mkdtemp(prefix="autosound_apply_busy_")
    failures = []
    try:
        proj = os.path.join(top, "car")
        root = os.path.join(proj, "state")
        _state.PresetHistory(root, "SQ", project_dir=proj).snapshot(_state._sample_state(), note="baseline")
        _state.Registry(root).set_active("SQ")
        with open(os.path.join(proj, "eq-delta.json"), "w", encoding="utf-8") as fh:
            json.dump({"w-L": {"gain_db": -7.5}}, fh)
        before = pj._files_in(proj)
        with pj._held_elsewhere(proj):
            for argv in (["apply.py", proj, "propose", "eq-delta.json", "--evidence", "w-L_2 (sw)"],
                         ["apply.py", proj, "attest"], ["apply.py", proj, "attest", "--from-file", _AYA_PCT6],
                         ["apply.py", proj, "propose", "--from-file", _AYA_PCT6]):
                rc, out, err = pj._run_cli(_main, argv, AUTOSOUND_LOCK_TIMEOUT_S="0.2")
                what = " ".join(argv[2:4])
                why = pj._said_busy(rc, err, proj)
                if why:
                    failures.append(f"{what}: {why}")
                if pj._files_in(proj) != before:
                    failures.append(f"{what}: wrote under another writer's lock: "
                                    f"{sorted(set(pj._files_in(proj)) ^ set(before))}")
                    before = pj._files_in(proj)
        rc, out, err = pj._run_cli(_main, ["apply.py", proj, "propose", "eq-delta.json", "--evidence", "w-L_2 (sw)"],
                                   AUTOSOUND_LOCK_TIMEOUT_S="0.2")
        if rc != 0 or _state.project_versions(root) != ["v_001", "v_002"]:
            failures.append(f"let go, propose did not land: rc {rc}, versions {_state.project_versions(root)}, "
                            f"said {err.strip()[-200:]!r}")
    finally:
        shutil.rmtree(top, ignore_errors=True)
    assert not failures, f"{len(failures)} run(s) under a held lock:\n  " + "\n  ".join(failures)


def _check_one_hold_over_the_bank():
    """`propose` and `attest` hold the project's lock once over the snapshot, its delta and its sheet (#141, J2b): the
    snapshot's own hold re-enters it, because both name the history's project -- also with the ledger outside the
    project, where `AUTOSOUND_STATE_ROOT` can put it, and a hold on the root's parent would be another folder's. So the
    history is read and the delta and the sheet are written with the project's lock held, the lock is
    `<project>/.autosound/write.lock` -- none is made beside the ledger -- and a wait of 0.3 s is never met: a hold
    waiting on its own thread would have answered busy."""
    import shutil
    import tempfile
    pj = _state._siblings().load("project.py")
    lock = _state._siblings().load("write_lock.py")
    top = tempfile.mkdtemp(prefix="autosound_apply_one_hold_")
    real = {"write_delta": write_delta, "write_sheet": write_sheet}
    seen, loads = [], []

    def watched(name):
        def call(*args, **kwargs):
            seen.append((name, lock.held_here(proj)))
            return real[name](*args, **kwargs)
        return call
    try:
        proj = os.path.join(top, "car")
        ledger = os.path.join(top, "elsewhere", "state")
        os.makedirs(proj)
        h = _state.PresetHistory(ledger, "SQ", project_dir=proj)
        h.snapshot(_state._sample_state(), note="baseline")
        read = h.load

        def load(*args, **kwargs):
            loads.append(lock.held_here(proj))
            return read(*args, **kwargs)
        h.load = load
        globals().update(write_delta=watched("write_delta"), write_sheet=watched("write_sheet"))
        with pj._env(AUTOSOUND_LOCK_TIMEOUT_S="0.3"):
            r = propose(h, {"w-L": {"gain_db": -7.5}}, note="a trim")
            proposed = list(loads)
            a = attest(h, r["version"])
        assert seen == [("write_delta", True), ("write_sheet", True)], f"written with the lock held: {seen}"
        assert proposed and all(proposed), f"propose read the history with the lock free: {proposed}"
        assert len(loads) > len(proposed) and all(loads), f"attest read the history with the lock free: {loads}"
        assert (r["version"], a["version"]) == ("v_002", "v_003"), (r["version"], a["version"])
        assert r["sheet_path"] and os.path.isfile(r["sheet_path"]), r["sheet_path"]
        assert os.path.isfile(lock.lock_path(proj)), "no lock in the project"
        assert not os.path.exists(os.path.join(top, "elsewhere", ".autosound")), "a lock made beside the ledger"
        assert not lock.held_here(proj), "the lock was kept"
    finally:
        globals().update(real)
        shutil.rmtree(top, ignore_errors=True)


def _check_a_bad_timeout_is_a_usage_error():
    """An AUTOSOUND_LOCK_TIMEOUT_S that is no number of seconds makes `propose` and `attest` a usage error (#141, R25):
    exit 2, one line naming the variable, no traceback, and nothing written or made -- no version, no delta, no sheet,
    and the lock's `.autosound/` not made. The command line catches `ValueError` and `OSError` by class first (exit
    1); `BadTimeout` is neither, so it reaches the lock's own answer."""
    import shutil
    import tempfile
    pj = _state._siblings().load("project.py")
    top = tempfile.mkdtemp(prefix="autosound_apply_bad_wait_")
    failures = []
    said = "error: AUTOSOUND_LOCK_TIMEOUT_S=soon is not a number of seconds (0 or more) -- unset it for the default 10"
    try:
        proj = os.path.join(top, "car")
        root = os.path.join(proj, "state")
        _state.PresetHistory(root, "SQ", project_dir=proj).snapshot(_state._sample_state(), note="baseline")
        _state.Registry(root).set_active("SQ")
        with open(os.path.join(proj, "eq-delta.json"), "w", encoding="utf-8") as fh:
            json.dump({"w-L": {"gain_db": -1.0}}, fh)
        shutil.rmtree(os.path.join(proj, ".autosound"), ignore_errors=True)
        before = pj._files_in(proj)
        for argv in (["propose", "eq-delta.json", "--evidence", "w-L_2 (sw)"], ["attest"]):
            rc, out, err = pj._run_cli(_main, ["apply.py", proj, *argv], AUTOSOUND_LOCK_TIMEOUT_S="soon")
            if rc != 2 or err.strip().splitlines() != [said] or out.strip():
                failures.append(f"{argv[0]}: rc {rc}, said {(err or out).strip()[-200:]!r}")
            if pj._files_in(proj) != before or os.path.exists(os.path.join(proj, ".autosound")):
                failures.append(f"{argv[0]}: wrote or made something")
    finally:
        shutil.rmtree(top, ignore_errors=True)
    assert not failures, "\n  ".join(["a bad AUTOSOUND_LOCK_TIMEOUT_S:"] + failures)


def _check_a_missing_project_makes_nothing():
    """`attest --preset SQ` on a project folder that is not there makes nothing (#141, R23): exit 1, its one line, no
    folder and no `.autosound/` -- the lock made `<typo>/.autosound/` before the refusal."""
    import shutil
    import tempfile
    pj = _state._siblings().load("project.py")
    top = tempfile.mkdtemp(prefix="autosound_apply_gone_")
    try:
        gone = os.path.join(top, "gone")
        rc, out, err = pj._run_cli(_main, ["apply.py", gone, "attest", "--preset", "SQ"])
        said = (out + err).strip().splitlines()
        assert rc == 1 and said == ["error: no snapshots yet for preset 'SQ'"], (rc, said)
        assert not os.path.lexists(gone), f"made {sorted(os.listdir(gone)) if os.path.isdir(gone) else gone}"
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_sheet_samples_follow_the_profile():
    """The "APPLY THIS" rows and `proposals/<v>.json` derive their samples from the PROFILE's processing rate, the
    Arbiter's ruling of 2026-08-25 (`state.processing_rate`), and say which rate they took (#147, item 2): they took
    the snapshot's, so a snapshot recorded at 96 kHz on a DSP its profile says runs at 48 kHz put 523 samples where
    the DSP needs 262 -- while the full sheet (`PresetHistory.render`) said 262. No profile keeps the snapshot's rate,
    said as the snapshot's; a profile that cannot be read leaves the samples empty and says why, with its repair."""
    import shutil
    import tempfile
    failures = []
    for label, profile, row, said in (
            ("a profile at 48 kHz", {"dsp_profile": {"dsp_processing_rate_hz": 48000}},
             "5.38 ms (258 smp) → 5.45 ms (262 smp)", "processing rate: 48000 Hz, the profile's"),
            ("no profile", None, "5.38 ms (516 smp) → 5.45 ms (523 smp)", "processing rate: 96000 Hz, the snapshot's"),
            ("a profile cut off", b'{"dsp_profile": {"dsp_processing_rate_hz": 480',
             "5.38 ms (— smp) → 5.45 ms (— smp)", "checkout HEAD -- dsp_profile.json")):
        top = tempfile.mkdtemp(prefix="autosound_apply_rate_")
        try:
            h = _state.PresetHistory(os.path.join(top, "state"), "SQ", project_dir=top)
            h.snapshot(_state._sample_state(), note="baseline")          # recorded at 96000 Hz
            if profile is not None:
                with open(os.path.join(top, "dsp_profile.json"), "wb") as fh:
                    fh.write(profile if isinstance(profile, bytes) else json.dumps(profile).encode("utf-8"))
            r = propose(h, {"w-L": {"ta_ms": 5.45}}, note="w-L delay")
            sheet = r["sheet"]
            if f"| w-L | TA | {row} |" not in sheet or said not in sheet:
                failures.append(f"{label}: the sheet said {sheet[:600]!r}")
            path = os.path.join(getattr(h, "proposals_dir", os.path.join(h.dir, "proposals")), f"{r['version']}.json")
            with open(path, encoding="utf-8") as fh:
                delta = json.load(fh)
            ta = [s for s in delta.get("settings") or [] if s.get("field") == "ta_ms"]
            if not ta or f"{ta[0]['was']} → {ta[0]['value']}" != row or said not in str(delta.get("processing_rate")):
                failures.append(f"{label}: {os.path.basename(path)} holds {ta!r}, rate "
                                f"{delta.get('processing_rate_hz')!r} {delta.get('processing_rate')!r}")
        finally:
            shutil.rmtree(top, ignore_errors=True)
    assert not failures, "\n  ".join(["the sheet's samples:"] + failures)


def _check_an_unwritten_delta_is_said():
    """A `proposals/<v>.json` that could not be written is said on the sheet, the file and why (group fix 1, item 6):
    `write_delta` answered None and `propose` dropped it, so the file TCC reads -- with `processing_rate_hz` in it now
    -- could be missing with nothing said. The version is banked either way: the snapshot is the record. A file stands
    where the proposals' folder belongs, which no `makedirs` can make a folder of."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_apply_unwritten_delta_")
    try:
        h = _state.PresetHistory(os.path.join(top, "state"), "SQ", project_dir=top)
        h.snapshot(_state._sample_state(), note="baseline")
        folder = getattr(h, "proposals_dir", os.path.join(h.dir, "proposals"))
        os.makedirs(os.path.dirname(folder), exist_ok=True)
        with open(folder, "w", encoding="utf-8") as fh:
            fh.write("a file where the folder belongs\n")
        r = propose(h, {"w-L": {"gain_db": -7.5}}, note="a trim")
        path = os.path.join(folder, f"{r['version']}.json")
        said = [line for line in r["sheet"].splitlines() if path in line]
        assert r["version"] == "v_002" and h.head() == "v_002", (r["version"], h.head())
        assert len(said) == 1 and "was not written (" in said[0], r["sheet"][-600:]
        with open(r["sheet_path"], encoding="utf-8") as fh:
            assert path in fh.read(), "the sheet's file does not say it"
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_the_sheet_rate_is_read_first_and_said_by_cause():
    """`sheet_rate` is read before the bank (`a42c473`), and says the cause of the snapshot's rate (group fix 1, item
    12). A rate read that fails with what is no refusal of the profile's -- a stand-in `processing_rate` raising
    `RuntimeError` -- raises out of `propose`, and the version list is as it was: nothing banked with no sheet. A
    profile that states no rate says so; no `dsp_profile.json` at all says there is none -- it said "the project's
    profile states none", a profile nobody wrote."""
    import shutil
    import tempfile
    failures = []
    real = _state.processing_rate
    top = tempfile.mkdtemp(prefix="autosound_apply_rate_first_")
    try:
        h = _state.PresetHistory(os.path.join(top, "state"), "SQ", project_dir=top)
        h.snapshot(_state._sample_state(), note="baseline")
        before = h.versions()

        def broken(project_dir):
            raise RuntimeError("a rate read that broke")
        _state.processing_rate = broken
        try:
            propose(h, {"w-L": {"ta_ms": 5.45}}, note="w-L delay")
            failures.append("a broken rate read banked")
        except RuntimeError:
            pass
        finally:
            _state.processing_rate = real
        if h.versions() != before:
            failures.append(f"versions {before} became {h.versions()}")
        r = propose(h, {"w-L": {"ta_ms": 5.45}}, note="no profile")
        if "processing rate: 96000 Hz, the snapshot's -- the project has no dsp_profile.json" not in r["sheet"]:
            failures.append(f"no profile: the sheet said {r['sheet'][:400]!r}")
        with open(os.path.join(top, "dsp_profile.json"), "w", encoding="utf-8") as fh:
            json.dump({"dsp_profile": {}}, fh)
        r = propose(h, {"w-L": {"ta_ms": 5.5}}, note="a profile with no rate")
        if "processing rate: 96000 Hz, the snapshot's -- the project's profile states none" not in r["sheet"]:
            failures.append(f"a profile with no rate: the sheet said {r['sheet'][:400]!r}")
    finally:
        _state.processing_rate = real
        shutil.rmtree(top, ignore_errors=True)
    assert not failures, "\n  ".join(["the sheet's rate:"] + failures)


def _check_no_load_and_save_outside_update():
    """No function here loads `project.json` and saves it itself (#141, J2b): a writer of the project's facts goes
    through `Project.update`, which holds the lock across the read and the write (`project._load_and_save_paths`)."""
    with open(os.path.realpath(__file__), encoding="utf-8") as fh:
        found = _state._siblings().load("project.py")._load_and_save_paths(fh.read())
    assert not found, f"load-and-save outside Project.update: {found}"


_FLIP, _FIX = {"sub": {"polarity": "INV"}}, {"w-L": {"gain_db": -8.8}}     # a structural move, a small trim (#199)


def _ledger_with_a_baseline(top, layout):
    """A slot holding one applied `v_001`, on the per-project line or on the older per-preset layout (#199)."""
    root = os.path.join(top, "state")
    h = _state.PresetHistory(root, "SQ", project_dir=top)
    if layout == "project":
        h.snapshot(_state._sample_state(), note="baseline")
    else:
        os.makedirs(h.dir)
        seed = _state._sample_state()
        seed.update(preset="SQ", version="v_001", created="2026-08-01T00:00:00",
                    schema_version=_state.SCHEMA_VERSION, project_rev=1)
        with open(os.path.join(h.dir, "v_001.json"), "w", encoding="utf-8") as fh:
            json.dump(seed, fh)
        with open(os.path.join(h.dir, "HEAD"), "w", encoding="utf-8") as fh:
            fh.write("v_001\n")
    assert _state.ledger_layout(root) == layout, _state.ledger_layout(root)
    with open(os.path.join(top, "review.md"), "w", encoding="utf-8") as fh:
        fh.write("reviewed")
    return h


def _check_a_delta_after_a_candidate_is_refused():
    """A `propose` naming no base, while the slot's newest version is a candidate not in the slot, is refused (#199):
    `_propose` read HEAD whatever the newest version was, so «v_002 + one fix» banked as v_001 + the fix, with every move
    of v_002 gone and nothing said. Nothing is banked; the command line says it as `error: …`, exit 1. A candidate in
    the slot, or a newest version that is no candidate, is an ordinary propose."""
    import contextlib
    import io
    import shutil
    import tempfile
    for layout in ("project", "preset"):
        top = tempfile.mkdtemp(prefix="autosound_apply_on_refused_")
        try:
            h = _ledger_with_a_baseline(top, layout)
            cand = propose(h, _FLIP, note="a flip")
            assert cand["candidate"] and (cand["version"], h.head()) == ("v_002", "v_001"), (layout, cand)
            try:
                got = propose(h, _FIX, note="the fix")
            except ValueError as exc:
                said = str(exc)
            else:
                raise AssertionError(f"{layout}: {got['version']} banked on HEAD past the candidate v_002")
            assert all(w in said for w in ("newest version v_002 is a candidate", "land on HEAD v_001",
                                           "--on v_002", "--on HEAD")), (layout, said)
            assert h.versions() == ["v_001", "v_002"] and h.head() == "v_001", (layout, h.versions())
            placed = propose(h, _FIX, note="confirmed on the slot's version", on="HEAD")
            assert placed["version"] == "v_003" and propose(h, _FIX, note="an ordinary next one")["version"] == "v_004"
        finally:
            shutil.rmtree(top, ignore_errors=True)
    top = tempfile.mkdtemp(prefix="autosound_apply_on_cli_")
    try:
        h = _ledger_with_a_baseline(top, "project")
        _state.Registry(h.root).set_active("SQ")
        propose(h, _FLIP, note="a flip")
        with open(os.path.join(top, "fix.json"), "w", encoding="utf-8") as fh:
            json.dump(_FIX, fh)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = _main(["apply.py", top, "propose", "fix.json"])
        assert rc == 1 and err.getvalue().startswith("error: ") and "--on v_002" in err.getvalue() \
            and not out.getvalue(), (rc, out.getvalue(), err.getvalue())
        assert h.versions() == ["v_001", "v_002"], h.versions()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            assert _main(["apply.py", top, "propose", "fix.json", "--on", "v_002"]) == 0
        assert "🟠 candidate v_003 on SQ" in out.getvalue(), out.getvalue()
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_a_fix_on_a_candidate_stays_held():
    """`on=<candidate>` builds on it, and what the candidate has not earned stays held (#199): its structural moves are
    measured from its own base, HEAD at its making, not from the candidate (the fix alone is no structural move). Until
    evidence AND a reviewer are there the result is a candidate too, its rows `candidate`, the slot unmoved. The sheet
    is measured against what is in the DSP, the last placed version -- «Enter only these» on candidate → fix would
    leave out the candidate's changes -- and its header names the base; `parent` is that base, on both layouts."""
    import shutil
    import tempfile
    for layout in ("project", "preset"):
        top = tempfile.mkdtemp(prefix="autosound_apply_on_held_")
        try:
            h = _ledger_with_a_baseline(top, layout)
            propose(h, _FLIP, note="a flip")
            r = propose(h, _FIX, note="the fix", on="v_002")
            assert r["candidate"] and r["version"] == "v_003" and h.head() == "v_001", (layout, r)
            assert r["structural"] == ["sub polarity"], (layout, r["structural"])
            s = h.load("v_003")
            assert s["parent"] == "v_002" and s["variant"] == "candidate", (layout, s.get("parent"), s.get("variant"))
            assert s["channels"]["sub"]["polarity"] == "INV" and s["channels"]["w-L"]["gain_db"] == -8.8, layout
            assert {s["channels"][c]["status"] for c in ("sub", "w-L")} == {"candidate"}, layout
            for row in ("| sub | Polarity | NORM → INV |", "| w-L | Gain | -7.8 dB → -8.8 dB |"):
                assert row in r["sheet"], (layout, row, r["sheet"])
            assert "v_003 = v_002 + this change" in r["sheet"] and "against v_001" in r["sheet"], (layout, r["sheet"])
            for half in ({"evidence": ["sub+w-L_2 (sw)"]}, {"reviewed": "review.md"}):
                one = propose(h, _FIX, note="half of what it needs", on="v_002", **half)
                assert one["candidate"] and h.load(one["version"])["variant"] == "candidate", (layout, half, one)
                assert h.head() == "v_001", (layout, half, h.head())
        finally:
            shutil.rmtree(top, ignore_errors=True)


def _check_a_candidate_is_promoted_with_evidence_and_a_reviewer():
    """With evidence and a reviewer, a version made on a candidate is the proposal it could not be (#199): every row
    `candidate` becomes `proposed`, `variant` is cleared, it goes in the slot, and `attest` covers those rows too -- no
    branch cleared them, so they would stay 🟠 past the attest. Two candidates in a row are walked to the first base
    that is none; an empty delta promotes the candidate as it stands. `on="HEAD"` measures against the slot's version
    alone, and a version the slot does not have is refused, nothing banked."""
    import shutil
    import tempfile
    for layout in ("project", "preset"):
        top = tempfile.mkdtemp(prefix="autosound_apply_on_promoted_")
        try:
            h = _ledger_with_a_baseline(top, layout)
            propose(h, _FLIP, note="a flip")
            propose(h, _FIX, note="the fix, not reviewed yet", on="v_002")           # v_003 on the candidate v_002
            before = h.versions()
            for bad in ("v_099", "v_1"):
                try:
                    propose(h, _FIX, on=bad)
                except ValueError as exc:
                    assert bad in str(exc), exc
                else:
                    raise AssertionError(f"{layout}: on={bad} banked")
            assert h.versions() == before, (layout, h.versions())
            r = propose(h, {"w-L": {"gain_db": -9.0}}, note="reviewed now", on="v_003",
                        evidence=["sub+w-L_2 (sw)"], reviewed="review.md")
            assert not r["candidate"] and r["version"] == "v_004" and h.head() == "v_004", (layout, r)
            assert r["structural"] == ["sub polarity"], (layout, r["structural"])
            s = h.load("v_004")
            assert "variant" not in s and s["parent"] == "v_003", (layout, s.get("variant"), s.get("parent"))
            assert {s["channels"][c]["status"] for c in ("sub", "w-L")} == {"proposed"}, layout
            assert "candidate" not in {c.get("status") for c in s["channels"].values()}, layout
            assert s["channels"]["tw-R"]["status"] == "applied", (layout, "an untouched row")
            for row in ("| sub | Polarity | NORM → INV |", "| w-L | Gain | -7.8 dB → -9 dB |"):
                assert row in r["sheet"], (layout, row, r["sheet"])
            assert "v_004 = v_003 + this change" in r["sheet"] and "🟠" not in r["sheet"], (layout, r["sheet"])
            a = attest(h, "v_004")
            assert {"sub", "w-L"} <= set(a["applied_channels"]), (layout, a)
            done = h.load(a["version"])
            assert {c["status"] for c in done["channels"].values()} == {"applied"}, (layout, done["channels"])
            assert done["parent"] == "v_004", (layout, "attest's parent", done["parent"])
        finally:
            shutil.rmtree(top, ignore_errors=True)
        top = tempfile.mkdtemp(prefix="autosound_apply_on_empty_")
        try:
            h = _ledger_with_a_baseline(top, layout)
            propose(h, _FLIP, note="a flip")
            r = propose(h, {}, note="the candidate as it stands", on="v_002",
                        evidence=["sub+w-L_2 (sw)"], reviewed="review.md")
            s = h.load(r["version"])
            assert not r["candidate"] and h.head() == r["version"] and s["channels"]["sub"]["status"] == "proposed" \
                and "variant" not in s, (layout, r)
            assert "| sub | Polarity | NORM → INV |" in r["sheet"], (layout, r["sheet"])
        finally:
            shutil.rmtree(top, ignore_errors=True)
        top = tempfile.mkdtemp(prefix="autosound_apply_on_head_")
        try:
            h = _ledger_with_a_baseline(top, layout)
            propose(h, _FLIP, note="a flip")
            r = propose(h, _FIX, note="on the slot's version", on="HEAD")
            s = h.load(r["version"])
            assert not r["candidate"] and h.head() == r["version"] and s["parent"] == "v_001", (layout, r)
            assert s["channels"]["sub"]["polarity"] == "NORM" and "variant" not in s, (layout, s.get("variant"))
            assert "Polarity" not in r["sheet"] and "v_003 = v_001 + this change" in r["sheet"] \
                and "against v_0" not in r["sheet"], (layout, r["sheet"])
        finally:
            shutil.rmtree(top, ignore_errors=True)
    top = tempfile.mkdtemp(prefix="autosound_apply_on_other_slot_")
    try:
        h = _ledger_with_a_baseline(top, "project")
        other = _state.PresetHistory(h.root, "FULL", project_dir=top).snapshot(_state._sample_state(), note="another slot")
        try:
            propose(h, _FIX, on=other)
        except ValueError as exc:
            assert other in str(exc), exc
        else:
            raise AssertionError(f"on={other}: a version of another slot was built on")
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _proposed(h, delta, **kw):
    """`propose`, with a refusal said as a failed check: on the code before #197 a preset setting is a channel delta."""
    try:
        return propose(h, delta, **kw)
    except ValueError as exc:
        raise AssertionError(f"propose refused {delta!r}: {exc}") from None


def _check_a_trim_is_a_row_with_no_reviewer():
    """The preset's input gain (#197, #200) goes through `propose` as a settings row: no structural move whatever its
    size, no reviewer, no channel touched. Its own `status`, proposed to applied by `attest`, which the rows' walk does
    not reach. Trim-only and mixed deltas, on both layouts; a missing value is 0, a value back to 0 is a row."""
    import shutil
    import tempfile
    for layout in ("project", "preset"):
        top = tempfile.mkdtemp(prefix="autosound_apply_trim_")
        try:
            h = _ledger_with_a_baseline(top, layout)
            r = _proposed(h, {"preset_settings": {"input_gain_db": -0.3}}, note="a trim for the A/B")
            assert not r["candidate"] and r["version"] == "v_002" and h.head() == "v_002", (layout, r)
            assert r["structural"] == [] and r["waits_for"] == [], (layout, r)
            assert "| Preset | Input gain | 0 dB → -0.3 dB |" in r["sheet"], (layout, r["sheet"])
            assert "_(no hard-param changes)_" not in r["sheet"], (layout, r["sheet"])
            s = h.load("v_002")
            assert s["preset_settings"] == {"input_gain_db": -0.3, "status": "proposed"}, (layout, s["preset_settings"])
            assert {c["status"] for c in s["channels"].values()} == {"applied"}, (layout, "a channel was touched")
            # What the card and the sheet print: the settings rows, in the same words.
            rows = [x for x in delta_rows(r["diff"], 96000) if x["tier"] == "preset_settings"]
            assert rows == [{"tier": "preset_settings", "channel": "preset", "param": "Input gain",
                             "field": "input_gain_db", "was": "0 dB", "value": "-0.3 dB", "was_raw": 0.0,
                             "value_raw": -0.3}], (layout, rows)
            with open(os.path.join(h.proposals_dir, "v_002.json"), encoding="utf-8") as fh:
                banked = json.load(fh)
            assert banked["settings"] == rows, (layout, banked["settings"])
            assert banked["preset_changes"]["preset_settings"] == [{}, {"input_gain_db": -0.3}], (layout, banked)
            a = attest(h, "v_002")
            assert a["applied_channels"] == ["preset_settings"], (layout, a)
            done = h.load(a["version"])
            assert done["preset_settings"]["status"] == "applied", (layout, done["preset_settings"])
            assert "preset_settings" not in _state.diff_states(s, done)["preset"], (layout, "a status flip is no change")
            # Back to 0: a row. Then a missing value against a 0: none.
            r0 = _proposed(h, {"preset_settings": {"input_gain_db": 0.0}}, note="trim off")
            assert "| Preset | Input gain | -0.3 dB → 0 dB |" in r0["sheet"], (layout, r0["sheet"])
            r1 = _proposed(h, {"w-L": {"gain_db": -7.0}}, note="no trim named")
            assert "Input gain" not in r1["sheet"], (layout, r1["sheet"])
            # A large trim is still a level trim; a mixed delta lands on both.
            big = _proposed(h, {"preset_settings": {"input_gain_db": -12.0}}, note="a big trim")
            assert not big["candidate"] and big["advisories"] == [], (layout, big)
            mixed = _proposed(h, {"preset_settings": {"sources": {"hec": -2.0}}, "w-L": {"gain_db": -7.5}}, note="both")
            s = h.load(mixed["version"])
            assert s["channels"]["w-L"]["gain_db"] == -7.5 and s["preset_settings"]["sources"] == {"hec": -2.0}, layout
            assert s["preset_settings"]["input_gain_db"] == -12.0, (layout, s["preset_settings"])
            assert "| w-L | Gain | -7 dB → -7.5 dB |" in mixed["sheet"], (layout, mixed["sheet"])
            assert "| Preset | HEC level | 0 dB → -2 dB |" in mixed["sheet"], (layout, mixed["sheet"])
            tiered = _proposed(h, {"preset_settings": {"conductor": {"sub_lamps": 7}},
                                   "virtual_channels": {"VFL": {"gain_db": -1.0}}}, note="both, tier-keyed")
            s = h.load(tiered["version"])
            assert s["virtual_channels"]["VFL"]["gain_db"] == -1.0 and s["preset_settings"]["conductor"]["sub_lamps"] == 7
            assert "| Preset | Conductor sub lamps | — → 7 |" in tiered["sheet"], (layout, tiered["sheet"])
        finally:
            shutil.rmtree(top, ignore_errors=True)


def _check_preset_settings_merge_and_refusals():
    """A delta merges two levels deep (one FX switch does not wipe the others), and what `validate` refuses is refused
    with nothing banked: a field it does not know, a value of the wrong kind, a `source_file` given by a delta."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_apply_merge_")
    try:
        h = _ledger_with_a_baseline(top, "project")
        _proposed(h, {"preset_settings": {"fx": {"realcenter": True}, "sources": {"main": -1.0}}}, note="one")
        r = _proposed(h, {"preset_settings": {"fx": {"dynamic_bass": False}}}, note="the other")
        s = h.load(r["version"])
        assert s["preset_settings"]["fx"] == {"realcenter": True, "dynamic_bass": False}, s["preset_settings"]
        assert s["preset_settings"]["sources"] == {"main": -1.0}, s["preset_settings"]
        assert "| Preset | Dynamic Bass | unknown → off |" in r["sheet"], r["sheet"]
        assert "RealCenter" not in r["sheet"], r["sheet"]
        before = h.versions()
        for bad in ({"preset_settings": {"inputgain": 1.0}}, {"preset_settings": {"fx": {"centre": True}}},
                    {"preset_settings": {"input_gain_db": "x"}}, {"preset_settings": 3.0},
                    {"preset_settings": {"source_file": {"name": "5S.preset"}}}):
            try:
                propose(h, bad, note="refused")
            except ValueError as exc:
                assert "preset_settings" in str(exc), (bad, exc)
            else:
                raise AssertionError(f"banked {bad!r}")
        assert h.versions() == before, h.versions()
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_source_file_needs_a_preset_setting():
    """`--source-file` on a version with no preset setting refuses and banks nothing: `preset_settings` would hold only the
    file, and a 3.2 copy reads that dict of dicts as a tier instead of refusing it by name, as it refuses a number."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_apply_source_alone_")
    try:
        h = _ledger_with_a_baseline(top, "project")
        r = _proposed(h, {"w-L": {"gain_db": -7.0}}, note="no settings")
        before = h.versions()
        try:
            attest(h, r["version"], source_file={"name": "5S.preset"})
        except ValueError as exc:
            assert "source_file" in str(exc) and "preset setting" in str(exc), str(exc)
        else:
            raise AssertionError("a source file on a version with no preset setting was banked")
        assert h.versions() == before, h.versions()
        said = attest(h, r["version"])
        assert "preset_settings" not in h.load(said["version"]), h.load(said["version"])
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_preset_settings_candidate_and_source_file():
    """Held with a structural move that has not earned its proposal, the settings are held with it and promoted with
    it. The source file is `attest`'s (`--source-file`): kept by it, dropped by the next `propose`, which is a new
    state nobody compared to that file -- and a drop is no row and no difference."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_apply_source_")
    source = {"name": "5S.preset", "path": "/presets/5S.preset", "md5": "46f99511aa", "saved": "291020261232",
              "pctool": "6.04.03", "device": "DSP.3", "read_at": "2026-11-08T20:00:00", "compared": "no difference"}
    try:
        h = _ledger_with_a_baseline(top, "project")
        c = _proposed(h, {"preset_settings": {"input_gain_db": -0.5}, "sub": {"polarity": "INV"}}, note="held")
        assert c["candidate"] and h.load(c["version"])["preset_settings"]["status"] == "candidate", c
        r = _proposed(h, {}, note="reviewed", on=c["version"], evidence=["sub+w-L_2 (sw)"], reviewed="review.md")
        s = h.load(r["version"])
        assert not r["candidate"] and s["preset_settings"]["status"] == "proposed", (r, s["preset_settings"])
        a = attest(h, r["version"], source_file=source)
        done = h.load(a["version"])
        assert done["preset_settings"]["status"] == "applied" and done["preset_settings"]["source_file"] == source, done
        assert "preset_settings" not in _state.diff_states(s, done)["preset"], "the file is no change of the DSP"
        assert "5S.preset (md5 46f99511)" in h.render(a["version"]), h.render(a["version"])
        # The next proposal is a new state, compared to no file.
        n = _proposed(h, {"w-L": {"gain_db": -7.0}}, note="a new state")
        dropped = h.load(n["version"])
        assert "source_file" not in dropped["preset_settings"], dropped["preset_settings"]
        assert "Input gain" not in n["sheet"] and "5S.preset" not in n["sheet"], n["sheet"]
        kept = attest(h, n["version"], source_file=dict(source, compared=["w-L gain differs"]))
        assert h.load(kept["version"])["preset_settings"]["source_file"]["compared"] == ["w-L gain differs"]
    finally:
        shutil.rmtree(top, ignore_errors=True)
    top = tempfile.mkdtemp(prefix="autosound_apply_source_cli_")
    try:
        h = _ledger_with_a_baseline(top, "project")
        _state.Registry(h.root).set_active("SQ")
        _proposed(h, {"preset_settings": {"input_gain_db": -0.5}}, note="the file's setting")
        with open(os.path.join(top, "read.json"), "w", encoding="utf-8") as fh:
            json.dump(source, fh)
        import contextlib
        import io
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = _main(["apply.py", top, "attest", "--source-file", "read.json"])
        assert rc == 0, (rc, err.getvalue())
        assert h.load(h.head())["preset_settings"]["source_file"] == source, h.load(h.head())
        # A field that held only the file (banked before `attest` refused that) goes with it: a state with no settings is one with no field.
        h.snapshot(dict(h.load(h.head()), preset_settings={"source_file": source}), note="an older ledger")
        n = _proposed(h, {"w-L": {"gain_db": -7.0}}, note="a new state")
        assert "preset_settings" not in h.load(n["version"]), h.load(n["version"])
        _proposed(h, {"preset_settings": {"input_gain_db": -0.4}}, note="a setting to attest against")
        before = h.versions()
        with open(os.path.join(top, "bad.json"), "w", encoding="utf-8") as fh:
            json.dump({"sha": "x"}, fh)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rc = _main(["apply.py", top, "attest", "--source-file", "bad.json"])
        assert rc == 1 and err.getvalue().startswith("error: ") and "preset_settings" in err.getvalue(), err.getvalue()
        assert h.versions() == before, h.versions()
    finally:
        shutil.rmtree(top, ignore_errors=True)


_EARNED = {"evidence": ["sub+w-L_2 (sw)"], "reviewed": "review.md"}


def _on_the_command_line(h, *argv):
    """`state.py <argv>`, the commands a person runs, with what they print kept out of the selftest's own output."""
    import contextlib
    import io
    with contextlib.redirect_stdout(io.StringIO()):
        assert _state._main(["--root", h.root, *argv]) == 0, argv


def _a_named_variant(top, h, name, delta):
    """`variant new <name> --delta`: a version on the line with its own name, not in the slot. Returns the version."""
    path = os.path.join(top, f"{name}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(delta, fh)
    _on_the_command_line(h, "variant", "new", h.preset, name, "--delta", path)
    return h.versions()[-1]


def _check_a_candidate_switched_into_the_slot_is_held_then_promoted():
    """A candidate `variant switch` put in the slot goes through the same hold and promotion as `--on` (#199), with a
    plain `propose`: it was built on with its moves measured from itself, so it banked placed with no evidence, its rows
    `candidate` for good, past the attest too."""
    import shutil
    import tempfile
    for layout in ("project", "preset"):
        top = tempfile.mkdtemp(prefix="autosound_apply_switched_")
        try:
            h = _ledger_with_a_baseline(top, layout)
            propose(h, _FLIP, note="a flip")
            _on_the_command_line(h, "variant", "switch", "SQ", "v_002")
            r = propose(h, _FIX, note="a fix with nothing behind it")
            assert r["candidate"] and r["structural"] == ["sub polarity"] and h.head() == "v_002", (layout, r)
            s = h.load(r["version"])
            assert s["variant"] == "candidate" and s["channels"]["sub"]["status"] == "candidate", (layout, s["channels"])
        finally:
            shutil.rmtree(top, ignore_errors=True)
        top = tempfile.mkdtemp(prefix="autosound_apply_switched_")
        try:
            h = _ledger_with_a_baseline(top, layout)
            propose(h, _FLIP, note="a flip")
            _on_the_command_line(h, "variant", "switch", "SQ", "v_002")
            r = propose(h, _FIX, note="reviewed now", **_EARNED)
            s = h.load(r["version"])
            assert not r["candidate"] and h.head() == r["version"] and "variant" not in s, (layout, r, s.get("variant"))
            assert {s["channels"][c]["status"] for c in ("sub", "w-L")} == {"proposed"}, (layout, s["channels"])
            a = attest(h, r["version"])
            done = h.load(a["version"])
            assert "sub" in a["applied_channels"], (layout, a)
            assert {c["status"] for c in done["channels"].values()} == {"applied"}, (layout, done["channels"])
        finally:
            shutil.rmtree(top, ignore_errors=True)


def _check_attest_refuses_a_candidate():
    """`attest` on a candidate is refused, naming `propose --on` (#199, #201): it banked a placed copy still marked
    candidate and recorded it as in the DSP. Unplaced or switched into the slot, by version or as HEAD, nothing is
    banked and the slot records nothing; the command line says it as `error: …`, exit 1."""
    import contextlib
    import io
    import shutil
    import tempfile
    for layout in ("project", "preset"):
        top = tempfile.mkdtemp(prefix="autosound_apply_attest_candidate_")
        try:
            h = _ledger_with_a_baseline(top, layout)
            propose(h, _FLIP, note="a flip")
            before = h.versions()

            def refused(*args):
                try:
                    got = attest(h, *args)
                except ValueError as exc:
                    assert "propose --on v_002" in str(exc), (layout, str(exc))
                else:
                    raise AssertionError(f"{layout}: attest{args} banked {got['version']}")
                assert h.versions() == before, (layout, h.versions())
            refused("v_002")
            assert h.head() == "v_001", (layout, h.head())
            _on_the_command_line(h, "variant", "switch", "SQ", "v_002")
            refused()
            assert h.head() == "v_002", (layout, h.head())
            if layout == "project":
                assert "loaded" not in _state.Registry(h.root).load()["slots"]["SQ"], layout
                _state.Registry(h.root).set_active("SQ")
                err = io.StringIO()
                with contextlib.redirect_stderr(err):
                    rc = _main(["apply.py", top, "attest", "v_002"])
                assert rc == 1 and err.getvalue().startswith("error: ") and "propose --on v_002" in err.getvalue(), \
                    (rc, err.getvalue())
        finally:
            shutil.rmtree(top, ignore_errors=True)


def _check_a_base_that_is_not_head_answers_to_the_slot():
    """`on=` a version that is neither HEAD nor a candidate measures its moves against what is in the slot as well
    (#199): `propose {} --on v_001` under a reviewed `sub INV` placed `INV → NORM` with no evidence, and a named variant
    carrying a flip placed the flip, keeping its `variant`. Held until evidence and a reviewer; a result that goes in
    the slot is no variant any more."""
    import shutil
    import tempfile
    for layout in ("project", "preset"):
        top = tempfile.mkdtemp(prefix="autosound_apply_on_older_")
        try:
            h = _ledger_with_a_baseline(top, layout)
            flip = propose(h, _FLIP, note="a reviewed flip", **_EARNED)
            head = attest(h, flip["version"])["version"]
            r = propose(h, {}, note="back to the old polarity", on="v_001")
            assert r["candidate"] and r["structural"] == ["sub polarity"] and h.head() == head, (layout, r)
            s = h.load(r["version"])
            assert s["variant"] == "candidate" and s["channels"]["sub"]["status"] == "candidate", (layout, s["channels"])
            assert "| sub | Polarity | INV → NORM |" in r["sheet"], (layout, r["sheet"])
            r = propose(h, {}, note="reviewed now", on="v_001", **_EARNED)
            s = h.load(r["version"])
            assert not r["candidate"] and h.head() == r["version"] and "variant" not in s, (layout, r)
            assert "sub" in attest(h, r["version"])["applied_channels"], layout
        finally:
            shutil.rmtree(top, ignore_errors=True)
        top = tempfile.mkdtemp(prefix="autosound_apply_on_named_")
        try:
            h = _ledger_with_a_baseline(top, layout)
            named = _a_named_variant(top, h, "B", _FLIP)
            trim = {"preset_settings": {"input_gain_db": -0.3}}
            r = propose(h, trim, note="a trim on the variant", on=named)
            assert r["candidate"] and r["structural"] == ["sub polarity"] and h.head() == "v_001", (layout, r)
            assert h.load(r["version"])["variant"] == "candidate", layout
            r = propose(h, trim, note="reviewed now", on=named, **_EARNED)
            s = h.load(r["version"])
            assert not r["candidate"] and h.head() == r["version"], (layout, r)
            assert "variant" not in s, (layout, "a placed version keeps its variant", s.get("variant"))
        finally:
            shutil.rmtree(top, ignore_errors=True)
        top = tempfile.mkdtemp(prefix="autosound_apply_on_named_plain_")
        try:
            h = _ledger_with_a_baseline(top, layout)
            named = _a_named_variant(top, h, "C", _FIX)
            r = propose(h, {}, note="a variant with no structural move", on=named)
            s = h.load(r["version"])
            assert not r["candidate"] and h.head() == r["version"] and "variant" not in s, (layout, r, s.get("variant"))
        finally:
            shutil.rmtree(top, ignore_errors=True)


def _check_rows_the_sheet_lists_are_proposed():
    """Every row that differs from the last placed version is `proposed` (#199): rows taken from an older base, or from
    a candidate after HEAD moved, kept `applied` while the sheet listed them to enter, so `attest` never covered them.
    The preset's settings the same; a row that is what the DSP holds stays as it was."""
    import shutil
    import tempfile
    for layout in ("project", "preset"):
        top = tempfile.mkdtemp(prefix="autosound_apply_rows_older_")
        try:
            h = _ledger_with_a_baseline(top, layout)
            attest(h, propose(h, _FIX, note="a trim")["version"])
            r = propose(h, {}, note="the older trim again", on="v_001")
            s = h.load(r["version"])
            assert not r["candidate"] and "| w-L | Gain | -8.8 dB → -7.8 dB |" in r["sheet"], (layout, r)
            assert s["channels"]["w-L"]["status"] == "proposed", (layout, s["channels"]["w-L"])
            assert s["channels"]["tw-R"]["status"] == "applied", (layout, "a row the DSP already holds")
            assert "w-L" in attest(h, r["version"])["applied_channels"], layout
        finally:
            shutil.rmtree(top, ignore_errors=True)
        top = tempfile.mkdtemp(prefix="autosound_apply_rows_moved_")
        try:
            h = _ledger_with_a_baseline(top, layout)
            propose(h, _FLIP, note="a flip")                                      # the candidate v_002 on v_001
            attest(h, propose(h, _FIX, note="HEAD moves on", on="HEAD")["version"])
            r = propose(h, {}, note="the candidate, reviewed", on="v_002", **_EARNED)
            s = h.load(r["version"])
            assert not r["candidate"] and "| w-L | Gain | -8.8 dB → -7.8 dB |" in r["sheet"], (layout, r)
            assert s["channels"]["w-L"]["status"] == "proposed", (layout, s["channels"]["w-L"])
            assert {"sub", "w-L"} <= set(attest(h, r["version"])["applied_channels"]), layout
        finally:
            shutil.rmtree(top, ignore_errors=True)
        top = tempfile.mkdtemp(prefix="autosound_apply_rows_settings_")
        try:
            h = _ledger_with_a_baseline(top, layout)
            older = attest(h, propose(h, {"preset_settings": {"input_gain_db": -0.3}}, note="one")["version"])["version"]
            attest(h, propose(h, {"preset_settings": {"input_gain_db": -1.0}}, note="another")["version"])
            r = propose(h, {}, note="the older trim", on=older)
            assert "| Preset | Input gain | -1 dB → -0.3 dB |" in r["sheet"], (layout, r["sheet"])
            assert h.load(r["version"])["preset_settings"]["status"] == "proposed", layout
            assert "preset_settings" in attest(h, r["version"])["applied_channels"], layout
        finally:
            shutil.rmtree(top, ignore_errors=True)


def _write_version(h, version, **fields):
    """`version` on the older layout's folder as a copy of `v_001` plus `fields` -- what no writer here makes any more: a
    candidate with no `parent`, or a line that loops."""
    seed = h.load("v_001")
    seed.pop("parent", None)
    seed.update(version=version, **fields)
    seed["channels"]["sub"].update(polarity="INV", status="candidate")
    with open(os.path.join(h.dir, f"{version}.json"), "w", encoding="utf-8") as fh:
        json.dump(seed, fh)


def _check_a_candidate_base_is_no_candidate():
    """`_candidate_base` never answers with a candidate (#199): with no `parent`, or a line that loops, it read as HEAD,
    which could be that same candidate, and the candidate promoted itself unreviewed. It walks to the previous version
    by number that is none; a slot with no such version holds the change, evidence and a reviewer or not."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_apply_base_")
    try:
        h = _ledger_with_a_baseline(top, "preset")
        _write_version(h, "v_002", variant="candidate")
        h.place("v_002")
        assert _candidate_base(h, h.load("v_002"))["version"] == "v_001", "no parent, in the slot"
        r = propose(h, {}, note="nothing behind it", on="HEAD")
        assert r["candidate"] and r["structural"] == ["sub polarity"] and h.head() == "v_002", r
    finally:
        shutil.rmtree(top, ignore_errors=True)
    top = tempfile.mkdtemp(prefix="autosound_apply_base_loop_")
    try:
        h = _ledger_with_a_baseline(top, "preset")
        _write_version(h, "v_002", variant="candidate", parent="v_003")
        _write_version(h, "v_003", variant="candidate", parent="v_002")
        h.place("v_003")
        assert _candidate_base(h, h.load("v_003"))["version"] == "v_001", "a line that loops"
    finally:
        shutil.rmtree(top, ignore_errors=True)
    top = tempfile.mkdtemp(prefix="autosound_apply_base_none_")
    try:
        h = _ledger_with_a_baseline(top, "preset")
        _write_version(h, "v_001", variant="candidate")
        assert _candidate_base(h, h.load("v_001")) is None, "no version on the slot is free of the candidate mark"
        r = propose(h, {}, note="evidence, and nothing to measure from", on="HEAD", **_EARNED)
        assert r["candidate"] and h.head() == "v_001" and r["version"] == "v_002", r
        assert any("no version" in w for w in r["waits_for"]), r["waits_for"]
        assert h.load("v_002")["variant"] == "candidate", h.load("v_002").get("variant")
    finally:
        shutil.rmtree(top, ignore_errors=True)


_READING = {"kind": "transcription", "source": "PC-Tool 6 screens", "read_on": "2026-11-08"}


def _attest_is_refused(h, version, layout):
    """`attest` of a candidate is said as a refusal and banks nothing."""
    before = h.versions()
    try:
        got = attest(h, version)
    except ValueError as exc:
        assert "is a candidate" in str(exc), (layout, str(exc))
    else:
        raise AssertionError(f"{layout}: attest {version} banked {got['version']}")
    assert h.versions() == before, (layout, h.versions())


def _check_a_device_read_vouches_only_for_the_rows_it_read():
    """A device read is evidence for the rows it read and for no others (#199): on a candidate `variant switch` put in
    the slot, a reading of some channels (`setup_import --write`, `provenance`, `on="HEAD"`) turned the unread `sub` from
    `candidate` to `proposed` and cleared `variant`, so `attest` could apply a flip nobody reviewed. The version keeps
    its candidate mark while any row, or the settings, is left `candidate`; a reading of them all clears it."""
    import shutil
    import tempfile
    for layout in ("project", "preset"):
        top = tempfile.mkdtemp(prefix="autosound_apply_read_partial_")
        try:
            h = _ledger_with_a_baseline(top, layout)
            propose(h, _FLIP, note="a flip")
            _on_the_command_line(h, "variant", "switch", "SQ", "v_002")
            r = propose(h, {"channels": _FIX}, note="some channels read", provenance=_READING, on="HEAD")
            s = h.load(r["version"])
            assert not r["candidate"] and h.head() == r["version"] and s["provenance"] == _READING, (layout, r)
            assert s["channels"]["w-L"]["status"] == "proposed", (layout, s["channels"]["w-L"])
            assert s["channels"]["sub"]["status"] == "candidate", (layout, "the unread row", s["channels"]["sub"])
            assert s["variant"] == "candidate", (layout, s.get("variant"))
            _attest_is_refused(h, r["version"], layout)
            e = propose(h, {}, note="reviewed now", **_EARNED)
            assert not e["candidate"] and e["structural"] == ["sub polarity"], (layout, e)
            assert "sub" in attest(h, e["version"])["applied_channels"], layout
        finally:
            shutil.rmtree(top, ignore_errors=True)
        top = tempfile.mkdtemp(prefix="autosound_apply_read_all_")
        try:
            h = _ledger_with_a_baseline(top, layout)
            propose(h, _FLIP, note="a flip")
            _on_the_command_line(h, "variant", "switch", "SQ", "v_002")
            every = {c: {k: row[k] for k in ("gain_db", "polarity") if k in row}
                     for c, row in h.load("v_002")["channels"].items()}
            r = propose(h, {"channels": every}, note="every channel read", provenance=_READING, on="HEAD")
            s = h.load(r["version"])
            assert "variant" not in s and {c["status"] for c in s["channels"].values()} == {"proposed"}, (layout, s)
            assert "sub" in attest(h, r["version"])["applied_channels"], layout
        finally:
            shutil.rmtree(top, ignore_errors=True)
        top = tempfile.mkdtemp(prefix="autosound_apply_read_settings_")
        try:
            h = _ledger_with_a_baseline(top, layout)
            propose(h, {"preset_settings": {"input_gain_db": -0.5}, "sub": {"polarity": "INV"}}, note="held")
            _on_the_command_line(h, "variant", "switch", "SQ", "v_002")
            every = {c: {} for c in h.load("v_002")["channels"]}
            r = propose(h, {"channels": every}, note="the channels read, not the settings", provenance=_READING, on="HEAD")
            s = h.load(r["version"])
            assert s["preset_settings"]["status"] == "candidate" and s["variant"] == "candidate", (layout, s.get("variant"))
        finally:
            shutil.rmtree(top, ignore_errors=True)


def _check_a_candidate_with_no_moves_of_its_own_is_still_held():
    """Promotion always needs evidence and a reviewer (#199): `propose {} --on v_001` held by the slot check and then
    switched in has no move against its own base, so a plain `propose {}` found nothing to hold and placed it, with
    `INV → NORM` no one reviewed. It stays a candidate, and the sheet does not call that `not measured`."""
    import shutil
    import tempfile
    for layout in ("project", "preset"):
        top = tempfile.mkdtemp(prefix="autosound_apply_held_switched_")
        try:
            h = _ledger_with_a_baseline(top, layout)
            attest(h, propose(h, _FLIP, note="a reviewed flip", **_EARNED)["version"])
            held = propose(h, {}, note="back to the old polarity", on="v_001")
            assert held["candidate"], (layout, held)
            _on_the_command_line(h, "variant", "switch", "SQ", held["version"])
            r = propose(h, {}, note="nothing behind it")
            s = h.load(r["version"])
            assert r["candidate"] and r["structural"] == [] and h.head() == held["version"], (layout, r)
            assert s["variant"] == "candidate" and s["channels"]["sub"]["status"] == "candidate", (layout, s["channels"])
            assert any("no evidence" in w for w in r["waits_for"]) and any("reviewer" in w for w in r["waits_for"]), r
            assert "Structural: none against its base" in r["sheet"], (layout, r["sheet"][:200])
            _attest_is_refused(h, r["version"], layout)
            e = propose(h, {}, note="reviewed now", on=r["version"], **_EARNED)
            done = h.load(e["version"])
            assert not e["candidate"] and h.head() == e["version"] and "variant" not in done, (layout, e)
            assert "sub" in attest(h, e["version"])["applied_channels"], layout
        finally:
            shutil.rmtree(top, ignore_errors=True)


_NEW_ROW = {"sub-2": {"hp": "OFF", "lp": "OFF", "gain_db": -6.0, "ta_ms": 0.0, "polarity": "NORM"}}


def _check_a_row_gone_is_a_structural_move():
    """A row in the state measured from and absent from the result is a structural move (#199): `structural_moves`
    walked only the result, so with HEAD holding a channel the older base lacks, `propose {} --on <older>` showed no
    move and placed a sheet telling the person to mute or remove that driver. A tier gone whole counts; a plain propose
    removes nothing."""
    import shutil
    import tempfile
    row = {"polarity": "NORM"}
    was = {"channels": {"a": row, "b": row}, "virtual_channels": {"v": row}}
    assert structural_moves(was, {"channels": {"a": row}}) == ["b removed", "v removed"], "a row and a whole tier"
    assert structural_moves({"channels": {"a": row}}, was) == ["b polarity", "v polarity"], "a row added is as it was"
    for layout in ("project", "preset"):
        top = tempfile.mkdtemp(prefix="autosound_apply_row_gone_")
        try:
            h = _ledger_with_a_baseline(top, layout)
            attest(h, propose(h, _NEW_ROW, note="a channel added", **_EARNED)["version"])
            plain = propose(h, _FIX, note="an ordinary trim")
            assert not plain["candidate"] and plain["structural"] == [], (layout, plain)
            r = propose(h, {}, note="the older state", on="v_001")
            assert r["candidate"] and r["structural"] == ["sub-2 removed"] and h.head() == plain["version"], (layout, r)
            assert h.load(r["version"])["variant"] == "candidate", layout
            e = propose(h, {}, note="reviewed now", on="v_001", **_EARNED)
            assert not e["candidate"] and h.head() == e["version"], (layout, e)
        finally:
            shutil.rmtree(top, ignore_errors=True)


def _check_a_plain_propose_keeps_the_slots_named_variant():
    """A plain `propose`, or `on="HEAD"`, on a slot holding a named variant carries the name onto the new version: that
    work is still that variant. Only a version built on another base, or on a candidate, stops being one (#199)."""
    import shutil
    import tempfile
    for layout in ("project", "preset"):
        top = tempfile.mkdtemp(prefix="autosound_apply_named_kept_")
        try:
            h = _ledger_with_a_baseline(top, layout)
            named = _a_named_variant(top, h, "B", _FIX)
            _on_the_command_line(h, "variant", "switch", "SQ", named)
            for on in (None, "HEAD"):
                r = propose(h, {"w-L": {"gain_db": -9.0}}, note="a trim on the variant", on=on)
                assert not r["candidate"] and h.head() == r["version"], (layout, on, r)
                assert h.load(r["version"]).get("variant") == "B", (layout, on, h.load(r["version"]).get("variant"))
        finally:
            shutil.rmtree(top, ignore_errors=True)


# ── compare-file (#218 T2): a version of the journal against a saved `.pct6`, read only ────────────────────────────
_AYA_PCT6 = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "testdata", "helix-pct6",
                         "AYA.pct6")


def _compare_file():
    """`state/compare_file.py`, through the ledger's own loader: one module object."""
    return _state._siblings().load("state/compare_file.py")


def _aya_project(top, edit_state=None, edit_xml=None, more_channels=()):
    """A project in `top/project` whose one version, v_001, holds values read off the shipped AYA.pct6 for four outputs
    and two virtual channels -- with a gain, a polarity, a band and a switch made to differ, and fields left out or
    not decoded on purpose -- and a copy of the file in `top/files`, outside the project. Returns (project, file).
    `edit_state(state)` changes the version before it is banked, `more_channels` adds `project.json` channels, and
    `edit_xml(root)` builds the file from AYA's decoded XML changed in place (`_test_container`)."""
    import shutil
    project, files = os.path.join(top, "project"), os.path.join(top, "files")
    os.makedirs(project)
    os.makedirs(files)
    channels = [{"code": "w-L", "tier": "channels", "slot": "C"}, {"code": "m-L", "tier": "channels", "slot": "E"},
                {"code": "tw-L", "tier": "channels", "slot": "G"}, {"code": "sw", "tier": "channels", "slot": "K"},
                {"code": "VFL", "tier": "virtual_channels", "slot": "A"},
                {"code": "VSW", "tier": "virtual_channels", "slot": "K"}] + list(more_channels)
    with open(os.path.join(project, "project.json"), "w", encoding="utf-8") as fh:
        json.dump({"schema_version": _state.SCHEMA_VERSION, "project_rev": 1, "channels": channels}, fh)
    state = {
        "preset": "AYA", "sample_rate": 96000, "project_rev": 1,
        "channels": {
            # every value as the file holds it: all match
            "w-L": {"gain_db": -0.3, "ta_ms": 4.63, "polarity": "NORM", "mute": False,
                    "hp": {"f": 92, "type": "LR", "slope": 24}, "lp": {"f": 280, "type": "LR", "slope": 24},
                    "eq": [{"type": "PK", "f": 241, "gain_db": -3.0, "q": 5.0, "i": 1},
                           {"type": "PK", "f": 188, "gain_db": -2.5, "q": 7.0, "i": 2},
                           {"type": "PK", "f": 300, "gain_db": -2.5, "q": 2.0, "i": 3},
                           {"type": "PK", "f": 102, "gain_db": -3.0, "q": 3.5, "i": 4}]},
            # the file says -3.5 dB; no `eq`, no `mute`, no `phase_deg` on a phase channel: unknown, never a match
            "m-L": {"gain_db": -3.0, "ta_ms": 4.73, "polarity": "NORM",
                    "hp": {"f": 280, "type": "LR", "slope": 24}, "lp": {"f": 2500, "type": "LR", "slope": 24}},
            # the file says NORM; its low-pass is off (slope 0), as the version's
            "tw-L": {"gain_db": -5.8, "ta_ms": 4.73, "polarity": "INV", "phase_deg": 0.0,
                     "hp": {"f": 3000, "type": "BW", "slope": 24}, "lp": None},
            # bands with no slot index: paired by type and frequency; PK 1000 is not in the file, and the file's other
            # active bands are not in the version; `off` is a switch the file does not decode
            "sw": {"gain_db": -6.5, "ta_ms": 0.0, "polarity": "NORM", "off": False,
                   "hp": None, "lp": {"f": 80, "type": "LR", "slope": 24},
                   "eq": [{"type": "PK", "f": 55, "gain_db": 1.9, "q": 5.0},
                          {"type": "PK", "f": 1000, "gain_db": -3.0, "q": 2.0}]},
        },
        "virtual_channels": {
            # a shelf's Q written 0.71 where the file holds 0.707; `eq_bypass` is a field whose meaning in the file is
            # not established
            "VFL": {"gain_db": 0.0, "ta_ms": 0.0, "polarity": "NORM", "eq_bypass": False,
                    "eq": [{"type": "LSH", "f": 150, "gain_db": 2.5, "q": 0.71, "bypass": True, "i": 1}]},
            # slot K of the virtual tier: PC-Tool's Virtual K [SubRC], the file's index 10
            "VSW": {"gain_db": 0.0, "ta_ms": 0.0, "polarity": "NORM"},
        },
        # RealCenter and BT as the file; SubXpander on where the file has it off; the knob position is not in a file
        "preset_settings": {"fx": {"realcenter": True, "subxpander": True}, "bt": {"source": "BT"},
                            "sources": {"main": 0.0}, "conductor": {"sub_lamps": 7}},
    }
    if edit_state:
        edit_state(state)
    _state.PresetHistory(os.path.join(project, "state"), "AYA", project_dir=project).snapshot(state, note="AYA")
    pct6 = os.path.join(files, "AYA.pct6")
    if edit_xml is None:
        shutil.copyfile(_AYA_PCT6, pct6)
    else:
        import xml.etree.ElementTree as ET
        root = ET.fromstring(_compare_file()._helix().read_pct6(_AYA_PCT6).xml)
        edit_xml(root)
        with open(pct6, "wb") as fh:
            fh.write(_test_container(ET.tostring(root)))
    return project, pct6


def _test_container(xml):
    """The bytes of a `.pct6` around given XML, for this selftest's own cases only, written in its own temp folder and
    never next to a fixture -- as the helix_pct6 tests build their error containers. The method has no encoder."""
    import struct
    import zlib
    body = struct.pack(">I", len(xml)) + zlib.compress(xml)
    return bytes(b ^ b"ATFV6"[i % 5] for i, b in enumerate(body))


def _oc(root, index):
    return next(e for e in root.findall("OC") if e.get("ON") == str(index))


def _compare_cli(*argv):
    """(exit code, stdout, stderr) of `apply.py <argv>`."""
    import contextlib
    import io
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = _main(["apply.py"] + list(argv))
    return code, out.getvalue(), err.getvalue()


def _compared(project, pct6, version="v_001"):
    code, out, err = _compare_cli(project, "compare-file", version, pct6, "--json")
    assert code == 0, (code, out, err)
    return json.loads(out)


def _row(result, channel, parameter):
    found = [r for r in result["rows"] if r["channel"] == channel and r["parameter"] == parameter]
    assert len(found) == 1, (channel, parameter, found, sorted({(r["channel"], r["parameter"]) for r in result["rows"]}))
    return found[0]


def _pinned_compare_keys():
    """{object: [keys]} from the key table under CONTRACT.md's compare-file heading: the shape pinned in the contract."""
    import re
    contract = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "CONTRACT.md")
    with open(contract, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    inside, table = False, {}
    for line in lines:
        if line.startswith("## "):
            inside = "compare-file" in line
            continue
        m = re.match(r"^\| (?P<object>[^|]+?) \| (?P<keys>`[^|]+) \|$", line) if inside else None
        if m:
            table[m.group("object").strip("` ")] = re.findall(r"`([^`]+)`", m.group("keys"))
    assert table, "CONTRACT.md has no compare-file heading with a key table"
    return table


def _check_compare_file_keys_are_the_pinned_ones():
    """The JSON compare-file prints holds exactly the keys CONTRACT.md pins: top level, `file`, `counts`, `device`, a
    row, a refusal and its `error`. A key added, removed or renamed on either side fails here."""
    import shutil
    import tempfile
    pinned = _pinned_compare_keys()
    for name in ("top level", "file", "counts", "device", "row", "refusal", "error"):
        assert name in pinned, f"CONTRACT.md pins no keys for {name!r}: {sorted(pinned)}"
    for build, bad_name in ((_aya_project, "not-a-preset.pct6"), (_pico_project, "not-a-preset.PR15")):
        top = tempfile.mkdtemp(prefix="autosound_compare_keys_")
        try:
            project, preset_file = build(top)
            got = _compared(project, preset_file)
            assert sorted(got) == sorted(pinned["top level"]), (sorted(got), pinned["top level"])
            assert sorted(got["file"]) == sorted(pinned["file"]), (sorted(got["file"]), pinned["file"])
            assert sorted(got["counts"]) == sorted(pinned["counts"]), (sorted(got["counts"]), pinned["counts"])
            assert sorted(got["device"]) == sorted(pinned["device"]), (sorted(got["device"]), pinned["device"])
            assert got["rows"], "no rows"
            for row in got["rows"]:
                assert sorted(row) == sorted(pinned["row"]), (sorted(row), pinned["row"])
            bad = os.path.join(top, "files", bad_name)
            with open(bad, "wb") as fh:
                fh.write(b"this is not a PC-Tool file")
            code, out, _err = _compare_cli(project, "compare-file", "v_001", bad, "--json")
            refused = json.loads(out)
            assert code == 2 and sorted(refused) == sorted(pinned["refusal"]), (code, sorted(refused), pinned["refusal"])
            assert sorted(refused["error"]) == sorted(pinned["error"]), (sorted(refused["error"]), pinned["error"])
            assert sorted(refused["file"]) == sorted(pinned["file"]), (sorted(refused["file"]), pinned["file"])
        finally:
            shutil.rmtree(top, ignore_errors=True)


def _check_compare_file_matches_and_differs_on_aya():
    """On the shipped AYA.pct6: what the version holds as the file does is a match, what it holds otherwise differs --
    a gain, a polarity, a band missing on either side, a switch -- and the top level names the file and the model."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_compare_aya_")
    try:
        project, pct6 = _aya_project(top)
        got = _compared(project, pct6)
        hx = _compare_file()._helix()
        assert got["contract"] == _compare_file().CONTRACT and got["warning"] == hx.WARNING, got["warning"]
        assert got["device"]["name"] == "HELIX DSP ULTRA S" and got["checked_model"] is True, got["device"]
        assert got["file"] == {"name": "AYA.pct6", "md5": "708ccc26583f90e7dfb84fd9345f670c",
                               "saved": "16.10.2026 18:55", "pctool": "6.04.03"}, got["file"]
        for channel, parameter in (("w-L", "gain_db"), ("w-L", "ta_ms"), ("w-L", "polarity"), ("w-L", "mute"),
                                   ("w-L", "hp.type"), ("w-L", "hp.f"), ("w-L", "hp.slope"), ("w-L", "lp.f"),
                                   ("w-L", "eq[1].gain_db"), ("w-L", "eq[4].q"), ("w-L", "eq[2].f"),
                                   ("tw-L", "lp.slope"), ("tw-L", "hp.type"), ("tw-L", "phase_deg"),
                                   ("sw", "hp.slope"), ("sw", "eq[1].gain_db"), ("sw", "eq[1].q"),
                                   ("VFL", "gain_db"), ("VFL", "eq[1].q"), ("VFL", "eq[1].bypass"),
                                   ("preset", "fx.realcenter"), ("preset", "bt.source"), ("preset", "sources.main")):
            row = _row(got, channel, parameter)
            assert row["result"] == "match", row
        gain = _row(got, "m-L", "gain_db")
        assert gain["result"] == "differs" and gain["journal"] == -3.0 and abs(gain["file"] + 3.5) < 0.01, gain
        assert gain["category"] == "audio" and gain["path"] == "/ATF/OC[@ON='18']/Vol[1]/@L", gain
        pol = _row(got, "tw-L", "polarity")
        assert pol["result"] == "differs" and (pol["journal"], pol["file"]) == ("INV", "NORM"), pol
        assert _row(got, "preset", "fx.subxpander")["result"] == "differs"
        assert _row(got, "preset", "fx.subxpander")["category"] == "system"
        only_journal = [r for r in got["rows"] if r["channel"] == "sw" and r["file"] is None and r["result"] == "differs"]
        assert len(only_journal) == 1 and only_journal[0]["journal"]["f"] == 1000, only_journal
        only_file = [r for r in got["rows"] if r["channel"] == "sw" and r["journal"] is None and r["result"] == "differs"]
        assert {r["parameter"] for r in only_file} == {"eq[3]", "eq[5]", "eq[6]", "eq[7]", "eq[8]", "eq[9]"}, only_file
        assert got["counts"]["result"]["differs"] == sum(r["result"] == "differs" for r in got["rows"]), got["counts"]
        assert got["counts"]["category"]["audio"]["match"] == sum(
            r["result"] == "match" and r["category"] == "audio" for r in got["rows"]), got["counts"]
        # The table a person reads: the same rows, one a line, and the same exit.
        code, out, _err = _compare_cli(project, "compare-file", "v_001", pct6)
        assert code == 0 and hx.WARNING in out and "m-L" in out and "differs" in out, out
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_compare_file_unknown_is_never_a_match():
    """What one side holds and the other does not decode or record is a row, `unknown` with its reason, and never a
    match: a field left out of the version, one the file does not decode, a channel no output carries, a field whose
    meaning in the file is not established, a knob position. `check`'s `missing` is never passed on."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_compare_unknown_")
    try:
        project, pct6 = _aya_project(top)
        got = _compared(project, pct6)
        for channel, parameter in (("m-L", "eq"), ("m-L", "mute"), ("m-L", "phase_deg"), ("sw", "off"),
                                   ("VFL", "eq_bypass"), ("Output A", "channel"),
                                   ("preset", "conductor.sub_lamps"), ("preset", "fx.dynamic_bass")):
            row = _row(got, channel, parameter)
            assert row["result"] == "unknown" and row["reason"], row
        assert _row(got, "VFL", "eq_bypass")["category"] == "unknown"
        assert {r["result"] for r in got["rows"]} <= {"match", "differs", "unknown"}, {r["result"] for r in got["rows"]}
        assert not [r for r in got["rows"] if r["category"] == "unknown" and r["result"] == "match"]
        assert not [r for r in got["rows"] if r["result"] == "unknown" and not r["reason"]]
        counts = got["counts"]["result"]
        assert counts == {res: sum(r["result"] == res for r in got["rows"]) for res in ("match", "differs", "unknown")}, counts
        assert sum(counts.values()) == len(got["rows"]), counts
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_compare_file_audio_first():
    """Every audio row comes before every other row, whatever order the version and the file hold them in."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_compare_order_")
    try:
        project, pct6 = _aya_project(top)
        cats = [r["category"] for r in _compared(project, pct6)["rows"]]
        assert "audio" in cats and "system" in cats, sorted(set(cats))
        last_audio = max(i for i, c in enumerate(cats) if c == "audio")
        first_other = min(i for i, c in enumerate(cats) if c != "audio")
        assert last_audio < first_other, (last_audio, first_other, cats)
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_compare_file_unreadable_is_exit_2():
    """A file that is not a `.pct6`, one cut short, and one that is not there: exit 2, the JSON naming the kind of
    failure, no rows -- nothing compared."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_compare_unreadable_")
    try:
        project, pct6 = _aya_project(top)
        garbage, cut = os.path.join(top, "files", "garbage.pct6"), os.path.join(top, "files", "cut.pct6")
        with open(garbage, "wb") as fh:
            fh.write(b"\x00\x01 not a PC-Tool setup file \x02" * 8)
        with open(pct6, "rb") as fh:
            data = fh.read()
        with open(cut, "wb") as fh:
            fh.write(data[:len(data) // 2])
        for path, kind in ((garbage, "container"), (cut, "truncated"), (os.path.join(top, "files", "none.pct6"), "io")):
            code, out, err = _compare_cli(project, "compare-file", "v_001", path, "--json")
            assert code == 2, (path, code, out, err)
            refused = json.loads(out)
            assert refused["error"]["kind"] == kind and refused["error"]["message"], (path, refused)
            assert "rows" not in refused, refused
            code, out, err = _compare_cli(project, "compare-file", "v_001", path)
            assert code == 2 and kind in err, (path, code, out, err)
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_compare_file_input_changed_is_exit_3():
    """The input is hashed before it is read and after: a file that changed in between -- the reader made to change it,
    once after its read and once before -- is exit 3, a refusal with no rows, not a result."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_compare_changed_")
    hx = real = None
    try:
        hx = _compare_file()._helix()
        real = hx.read_pct6
        project, pct6 = _aya_project(top)

        def touch(path):
            with open(path, "ab") as fh:
                fh.write(b"\0")

        def changed_after(source, *args, **kwargs):
            doc = real(source, *args, **kwargs)
            touch(source)
            return doc

        def changed_before(source, *args, **kwargs):
            touch(source)
            return real(source, *args, **kwargs)

        for reader in (changed_after, changed_before):
            shutil.copyfile(_AYA_PCT6, pct6)
            hx.read_pct6 = reader
            try:
                code, out, err = _compare_cli(project, "compare-file", "v_001", pct6, "--json")
            finally:
                hx.read_pct6 = real
            assert code == 3, (reader.__name__, code, out, err)
            refused = json.loads(out)
            assert refused["error"]["kind"] == "changed" and "rows" not in refused, (reader.__name__, refused)
    finally:
        if hx is not None:
            hx.read_pct6 = real
        shutil.rmtree(top, ignore_errors=True)


def _check_compare_file_delay_rounds_half_up_on_both_sides():
    """A delay is compared as PC-Tool shows it, half up to 0.01 ms -- the version's ms too, not half to even: 4.625 ms
    is 444 samples at 96 kHz and shows 4.63; 0.045 ms shows 0.05, and 4 samples (0.0417) show 0.04."""
    import shutil
    import tempfile
    hx = _compare_file()._helix()
    path = "/ATF/OC[@ON='16']/T[1]/@T"
    doc = hx.read_pct6(_AYA_PCT6)
    assert doc.root.find("OC[@ON='16']/T").get("T") == "444"
    assert hx.check(doc, [{"path": path, "expected": 4.625, "policy": "display_delay_ms"}])[0]["result"] == "match"
    top = tempfile.mkdtemp(prefix="autosound_compare_delay_")
    try:
        def four_samples(root):
            _oc(root, 16).find("T").set("T", "4")

        def the_version(state):
            state["channels"]["w-L"]["ta_ms"] = 0.045

        project, pct6 = _aya_project(top, edit_state=the_version, edit_xml=four_samples)
        row = _row(_compared(project, pct6), "w-L", "ta_ms")
        assert row["result"] == "differs" and (row["journal"], row["file"]) == (0.045, 0.04), row
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_compare_file_a_leg_with_no_slope_is_unknown():
    """A crossover leg the version holds with no `slope` (valid: only `f` is required) against a leg the file has OFF
    -- PC-Tool keeps its type and frequency -- is never a match: `<leg>.slope` is unknown, the file's leg beside it."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_compare_noslope_")
    try:
        def no_slope(state):
            state["channels"]["spare-A"] = {"gain_db": 0.0, "ta_ms": 0.0, "polarity": "NORM",
                                            "hp": {"f": 100, "type": "BW"}, "lp": None}

        project, pct6 = _aya_project(top, edit_state=no_slope,
                                     more_channels=[{"code": "spare-A", "tier": "channels", "slot": "A"}])
        got = _compared(project, pct6)
        row = _row(got, "spare-A", "hp.slope")
        assert row["result"] == "unknown" and "no slope" in row["reason"] and "OFF" in str(row["file"]), row
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_compare_file_a_preset_row_without_its_value_is_system():
    """A preset setting the file does not hold is a `system` row like the rest of the preset: `bt.auto_switch` against a
    file with no input mask is unknown, category system, and after every audio row."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_compare_category_")
    try:
        def auto(state):
            state["preset_settings"]["bt"]["auto_switch"] = True

        def no_mask(root):
            for e in root.iter("MCV2"):
                e.attrib.pop("IMASK", None)

        project, pct6 = _aya_project(top, edit_state=auto, edit_xml=no_mask)
        got = _compared(project, pct6)
        row = _row(got, "preset", "bt.auto_switch")
        assert row["result"] == "unknown" and row["category"] == "system", row
        cats = [r["category"] for r in got["rows"]]
        assert "audio" not in cats[cats.index("system"):], cats
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_compare_file_a_journal_fault_is_the_journals():
    """A version whose leg `slope` or `phase_deg` is not a number is refused as the journal's fault, exit 1 `journal`,
    never blamed on the file as exit 2 `interpret`."""
    import shutil
    import tempfile
    for field, edit in (("slope", lambda st: st["channels"]["w-L"]["hp"].update(slope="24")),
                        ("phase_deg", lambda st: st["channels"]["tw-L"].update(phase_deg="0"))):
        top = tempfile.mkdtemp(prefix="autosound_compare_kinds_")
        try:
            try:
                project, pct6 = _aya_project(top, edit_state=edit)
            except ValueError:
                continue            # the ledger refuses it itself: then it never reaches compare-file
            code, out, err = _compare_cli(project, "compare-file", "v_001", pct6, "--json")
            assert code == 1, (field, code, out, err)
            assert json.loads(out)["error"]["kind"] == "journal", (field, out)
        finally:
            shutil.rmtree(top, ignore_errors=True)


def _check_compare_file_bands_it_cannot_decode_and_an_inverted_all_pass():
    """A file band of a type code the reader does not decode is a row, unknown, whether the version holds EQ for the
    channel or not; an all-pass the file holds inverted is unknown, the version having no way to record an invert."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_compare_bands_")
    try:
        def bands(root):
            wl = _oc(root, 16).findall("Fil")
            wl[4].attrib.update({"T": "2", "F": "500.00", "G": "-3", "FilBy": "0", "FilBBR": "0"})
            wl[5].attrib.update({"T": "20", "F": "80.00", "G": "0", "Q": "0.7", "I": "1", "FilBy": "0", "FilBBR": "0"})
            spare = _oc(root, 25).findall("Fil")                # Output L: no active band, then one it cannot decode
            spare[0].attrib.update({"T": "2", "F": "700.00", "G": "-2", "FilBy": "0", "FilBBR": "0"})

        def the_version(state):
            state["channels"]["w-L"]["eq"].append({"type": "APF2", "f": 80, "q": 0.7, "i": 6})
            state["channels"]["spare-L"] = {"gain_db": 0.0, "ta_ms": 0.0, "polarity": "NORM", "hp": None, "lp": None}

        project, pct6 = _aya_project(top, edit_state=the_version, edit_xml=bands,
                                     more_channels=[{"code": "spare-L", "tier": "channels", "slot": "L"}])
        got = _compared(project, pct6)
        odd = _row(got, "w-L", "eq[5]")
        assert odd["result"] == "unknown" and "type code 2" in odd["reason"], odd
        inverted = _row(got, "w-L", "eq[6].invert")
        assert inverted["result"] == "unknown" and "invert" in inverted["reason"] and inverted["file"] is True, inverted
        assert _row(got, "w-L", "eq[6].f")["result"] == "match"
        none_recorded = _row(got, "spare-L", "eq")
        assert none_recorded["result"] == "unknown" and none_recorded["file"], none_recorded
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_compare_file_virtual_letters_are_pc_tools():
    """A virtual slot letter is PC-Tool's, which is the reader's own label: on the HELIX DSP ULTRA S, PC-Tool shows
    Virtual A..F, K, L (indexes 0-5, 10, 11). K reaches index 10, L index 11; G (index 6, not shown) and I reach
    nothing."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_compare_virtual_")
    try:
        def three_more(state):
            for code in ("VL", "VG", "VI"):
                state["virtual_channels"][code] = {"gain_db": 0.0, "ta_ms": 0.0, "polarity": "NORM"}

        project, pct6 = _aya_project(top, edit_state=three_more,
                                     more_channels=[{"code": "VL", "tier": "virtual_channels", "slot": "L"},
                                                    {"code": "VG", "tier": "virtual_channels", "slot": "G"},
                                                    {"code": "VI", "tier": "virtual_channels", "slot": "I"}])
        got = _compared(project, pct6)
        k, l_ = _row(got, "VSW", "gain_db"), _row(got, "VL", "gain_db")
        assert k["result"] == "match" and k["path"] == "/ATF/OC[@ON='10']/Vol[1]/@L", k
        assert l_["result"] == "match" and l_["path"] == "/ATF/OC[@ON='11']/Vol[1]/@L", l_
        assert _row(got, "VFL", "gain_db")["path"] == "/ATF/OC[@ON='0']/Vol[1]/@L"
        g, i = _row(got, "VG", "gain_db"), _row(got, "VI", "gain_db")
        assert g["result"] == "unknown" and g["path"] is None, g
        assert g["reason"].startswith("no channel PC-Tool shows is Virtual G on this model"), g
        assert i["result"] == "unknown" and i["reason"] == "no channel PC-Tool shows is Virtual I on this model", i
        unreached = {r["channel"] for r in got["rows"] if r["parameter"] == "channel"}
        assert "Virtual K" not in unreached and "Virtual L" not in unreached, unreached
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_compare_file_an_ordinal_lettered_project_keeps_its_slots():
    """A project whose virtual tier was lettered A..H in order (v3.3.2's rule, the car's journals) keeps its slots:
    A..F still reach indexes 0-5; its G and H reach no channel and come out `unknown`, the reason naming the letter
    PC-Tool gives that ordinal (Virtual K, Virtual L), so the tuner can re-slot. `propose --from-file` keeps them with
    the same reason."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_compare_ordinal_")
    try:
        def one_more(state):
            state["virtual_channels"]["VH"] = {"gain_db": 0.0, "ta_ms": 0.0, "polarity": "NORM"}

        project, pct6 = _aya_project(top, edit_state=one_more,
                                     more_channels=[{"code": "VH", "tier": "virtual_channels", "slot": "H"}])
        with open(os.path.join(project, "project.json"), encoding="utf-8") as fh:
            pj = json.load(fh)
        next(c for c in pj["channels"] if c["code"] == "VSW")["slot"] = "G"
        with open(os.path.join(project, "project.json"), "w", encoding="utf-8") as fh:
            json.dump(pj, fh)
        got = _compared(project, pct6)
        assert _row(got, "VFL", "gain_db")["result"] == "match", _row(got, "VFL", "gain_db")
        for code, slot, ordinal, letter in (("VSW", "G", "7th", "K"), ("VH", "H", "8th", "L")):
            row = _row(got, code, "gain_db")
            assert row["result"] == "unknown" and row["path"] is None, row
            assert row["reason"].startswith("no channel PC-Tool shows is Virtual %s on this model" % slot), row
            assert "the %s virtual channel PC-Tool shows is Virtual %s" % (ordinal, letter) in row["reason"], row
        unreached = {r["channel"] for r in got["rows"] if r["parameter"] == "channel"}
        assert {"Virtual K", "Virtual L"} <= unreached, unreached
        code, out, err = _compare_cli(project, "propose", "--preset", "AYA", "--from-file", pct6)
        assert code == 0, (code, out[-600:], err)
        kept = [line for line in out.splitlines() if line.startswith("  - VSW: ")]
        assert kept and "the 7th virtual channel PC-Tool shows is Virtual K" in kept[0], (kept, out[-1200:])
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_compare_file_a_file_it_cannot_interpret_is_exit_2():
    """A file that decodes and then cannot be interpreted or compared -- a delay `abc`, a delay `NaN` -- is exit 2,
    `kind` interpret, the JSON refusal: the file's failure, never the journal's exit 1, never a traceback."""
    import shutil
    import tempfile
    for bad in ("abc", "NaN"):
        top = tempfile.mkdtemp(prefix="autosound_compare_interpret_")
        try:
            def odd_delay(root, bad=bad):
                _oc(root, 16).find("T").set("T", bad)

            project, pct6 = _aya_project(top, edit_xml=odd_delay)
            try:
                code, out, err = _compare_cli(project, "compare-file", "v_001", pct6, "--json")
            except Exception as exc:          # noqa: BLE001 -- what this check is about
                raise AssertionError(f"T={bad}: {type(exc).__name__}: {exc}") from exc
            assert code == 2, (bad, code, out[:300], err)
            refused = json.loads(out)
            assert refused["error"]["kind"] == "interpret" and "rows" not in refused, (bad, refused)
        finally:
            shutil.rmtree(top, ignore_errors=True)


def _tree_digest(top):
    """{relative path: sha256 or "<dir>"} of everything under `top`: a file made, changed or removed shows."""
    import hashlib
    out = {}
    for here, dirs, files in os.walk(top):
        for d in dirs:
            out[os.path.relpath(os.path.join(here, d), top)] = "<dir>"
        for f in files:
            with open(os.path.join(here, f), "rb") as fh:
                out[os.path.relpath(os.path.join(here, f), top)] = hashlib.sha256(fh.read()).hexdigest()
    return out


def _check_compare_file_writes_nothing():
    """compare-file writes nothing anywhere: the project tree (its journal among it) and the file's own folder hash the
    same before and after a comparison, its table, and a refusal."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_compare_nowrite_")
    try:
        project, pct6 = _aya_project(top)
        before = _tree_digest(top)
        assert any(k.endswith("v_001.json") for k in before) and "files/AYA.pct6".replace("/", os.sep) in before
        for argv, exit_code in ((("v_001", pct6, "--json"), 0), (("v_001", pct6), 0),
                                (("v_001", os.path.join(top, "files", "none.pct6")), 2)):
            code, out, err = _compare_cli(project, "compare-file", *argv)
            assert code == exit_code, (argv, code, out, err)     # it ran: a refusal at the door proves nothing
        assert _tree_digest(top) == before, sorted(set(_tree_digest(top).items()) ^ set(before.items()))
    finally:
        shutil.rmtree(top, ignore_errors=True)


# ── compare-file on a Mosconi `.PR15` (#219 T7): the same shape, its own reader ────────────────────────────────────
_PICO_PR15 = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "testdata", "mosconi-pr",
                          "example_pico682.PR15")


def _pico_project(top, edit_state=None):
    """A project in `top/project` whose v_001 holds values of the shipped sample preset for four outputs (numbered as
    the PICO 6/8-2's profile numbers them, "1"..."8"), with a gain and a band made to differ and fields left out on
    purpose, and one channel on a slot the model does not have; a copy of the file in `top/files`. (project, file)."""
    import shutil
    project, files = os.path.join(top, "project"), os.path.join(top, "files")
    os.makedirs(project)
    os.makedirs(files)
    channels = [{"code": "tw-L", "tier": "channels", "slot": "1"}, {"code": "tw-R", "tier": "channels", "slot": "2"},
                {"code": "w-L", "tier": "channels", "slot": "5"}, {"code": "sub", "tier": "channels", "slot": "7"},
                {"code": "x-9", "tier": "channels", "slot": "9"}]
    with open(os.path.join(project, "project.json"), "w", encoding="utf-8") as fh:
        json.dump({"schema_version": _state.SCHEMA_VERSION, "project_rev": 1, "channels": channels}, fh)
    state = {
        "preset": "PICO", "sample_rate": 96000, "project_rev": 1,
        "channels": {
            # as the file holds it; two of its nine active bands named, by slot, the rest only in the file
            "tw-L": {"gain_db": 0.0, "ta_ms": 6.8, "polarity": "INV", "mute": False,
                     "hp": {"f": 2000, "type": "LR", "slope": 18}, "lp": None,
                     "eq": [{"type": "PK", "f": 570, "gain_db": 4.0, "q": 4.42, "i": 1},
                            {"type": "LSH", "f": 900, "gain_db": -9.0, "q": 1.0, "i": 3}]},
            # the file says +3 dB; no mute, no EQ recorded: unknown, never a match
            "tw-R": {"gain_db": 2.5, "ta_ms": 4.29, "polarity": "INV",
                     "hp": {"f": 2000, "type": "LR", "slope": 18}, "lp": None},
            # a band paired by type and frequency; a peak at 1000 Hz the file does not hold; a phase it has no control for
            "w-L": {"gain_db": -1.5, "ta_ms": 5.19, "polarity": "NORM", "mute": False, "phase_deg": 0.0,
                    "hp": {"f": 70, "type": "BE", "slope": 12}, "lp": {"f": 2400, "type": "LR", "slope": 12},
                    "eq": [{"type": "PK", "f": 81, "gain_db": 1.1, "q": 3.57},
                           {"type": "PK", "f": 1000, "gain_db": -3.0, "q": 2.0}]},
            "sub": {"gain_db": 0.0, "ta_ms": 0.0, "polarity": "INV", "mute": False, "hp": None,
                    "lp": {"f": 80, "type": "LR", "slope": 24}},
            "x-9": {"gain_db": 0.0, "ta_ms": 0.0, "polarity": "NORM", "hp": None, "lp": None},
        },
    }
    if edit_state:
        edit_state(state)
    _state.PresetHistory(os.path.join(project, "state"), "PICO", project_dir=project).snapshot(state, note="PICO")
    pr15 = os.path.join(files, "example_pico682.PR15")
    shutil.copyfile(_PICO_PR15, pr15)
    return project, pr15


def _check_compare_file_pr15_matches_differs_and_unknown():
    """On the shipped `.PR15`: the same shape as a `.pct6`, its own warning, the model unchecked; what the version
    holds as the file does matches, what it holds otherwise differs, what one side does not hold or decode is unknown
    and never a match; audio first; nothing written anywhere."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_compare_pr15_")
    try:
        project, pr15 = _pico_project(top)
        before = _tree_digest(top)
        got = _compared(project, pr15)
        cf = _compare_file()
        assert got["contract"] == cf.CONTRACT and got["warning"] == cf._mosconi().WARNING, got["warning"]
        assert got["checked_model"] is False and got["device"]["verified"] is False, got["device"]
        assert (got["device"]["dev"], got["device"]["name"]) == ("15", "Mosconi PICO 6/8-2 DSP"), got["device"]
        assert got["file"]["name"] == "example_pico682.PR15" and got["file"]["md5"], got["file"]
        for channel, parameter in (("tw-L", "gain_db"), ("tw-L", "ta_ms"), ("tw-L", "polarity"), ("tw-L", "mute"),
                                   ("tw-L", "hp.type"), ("tw-L", "hp.f"), ("tw-L", "hp.slope"), ("tw-L", "lp.slope"),
                                   ("tw-L", "eq[1].type"), ("tw-L", "eq[1].f"), ("tw-L", "eq[1].gain_db"),
                                   ("tw-L", "eq[1].q"), ("tw-L", "eq[3].type"), ("tw-L", "eq[3].gain_db"),
                                   ("w-L", "lp.type"), ("w-L", "lp.f"), ("w-L", "hp.type"), ("w-L", "hp.slope"),
                                   ("w-L", "eq[2].gain_db"), ("w-L", "eq[2].q"), ("w-L", "ta_ms"),
                                   ("sub", "polarity"), ("sub", "lp.slope"), ("sub", "hp.slope")):
            assert _row(got, channel, parameter)["result"] == "match", _row(got, channel, parameter)
        gain = _row(got, "tw-R", "gain_db")
        assert gain["result"] == "differs" and (gain["journal"], gain["file"]) == (2.5, 3.0), gain
        assert gain["category"] == "audio" and gain["path"] == "offset 1281", gain
        missing = [r for r in got["rows"] if r["channel"] == "w-L" and r["file"] is None and r["result"] == "differs"]
        assert len(missing) == 1 and missing[0]["journal"]["f"] == 1000, missing
        only_file = {r["parameter"] for r in got["rows"]
                     if r["channel"] == "tw-L" and r["journal"] is None and r["result"] == "differs"}
        assert only_file == {"eq[2]", "eq[4]", "eq[5]", "eq[6]", "eq[7]", "eq[8]", "eq[9]"}, only_file
        for channel, parameter in (("tw-R", "mute"), ("tw-R", "eq"), ("w-L", "phase_deg"), ("x-9", "gain_db"),
                                   ("Output 3", "channel"), ("Output 8", "channel"), ("preset", "input_gain_db"),
                                   ("preset", "crossover.corner_set")):
            row = _row(got, channel, parameter)
            assert row["result"] == "unknown" and row["reason"], row
        assert "9" in _row(got, "x-9", "gain_db")["reason"], _row(got, "x-9", "gain_db")
        assert {r["result"] for r in got["rows"]} <= set(cf.RESULTS)
        assert not [r for r in got["rows"] if r["result"] == "unknown" and not r["reason"]]
        counts = got["counts"]["result"]
        assert counts == {res: sum(r["result"] == res for r in got["rows"]) for res in cf.RESULTS}, counts
        cats = [r["category"] for r in got["rows"]]
        assert "system" in cats and max(i for i, c in enumerate(cats) if c == "audio") < min(
            i for i, c in enumerate(cats) if c != "audio"), cats
        code, out, _err = _compare_cli(project, "compare-file", "v_001", pr15)
        assert code == 0 and cf._mosconi().WARNING in out and "tw-R" in out and "differs" in out, out
        assert _tree_digest(top) == before, sorted(set(_tree_digest(top).items()) ^ set(before.items()))
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_compare_file_pr15_corner_set_against_the_project():
    """S-136.2: `crossover.corner_set` sets the file's corner set against `project.json` `dsp.settings.corner_set` --
    `match` where the tuner's recorded answer is the file's, `differs` where it is another, `unknown` with its reason
    where none is recorded. It was `unknown` always. The table between the project's keys and the reader's names is
    the two modules' own."""
    import shutil
    import tempfile
    cf = _compare_file()
    project_mod = _state._siblings().load("project.py")
    assert tuple(cf.PR_CORNER_SETS) == project_mod.DSP_SETTINGS["corner_set"], cf.PR_CORNER_SETS
    assert tuple(cf.PR_CORNER_SETS.values()) == cf._mosconi().CORNER_SETS, cf.PR_CORNER_SETS
    top = tempfile.mkdtemp(prefix="autosound_compare_pr15_corners_")
    try:
        project, pr15 = _pico_project(top)
        row = _row(_compared(project, pr15), "preset", "crossover.corner_set")
        assert row["result"] == "unknown" and "records no corner set" in row["reason"], row
        pj = os.path.join(project, "project.json")
        with open(pj, encoding="utf-8") as fh:
            data = json.load(fh)
        for recorded, result, journal in (("default", "match", "default"),
                                          ("minus_6db", "differs", "normalized to -6 dB")):
            data["dsp"] = {"settings": {"corner_set": {"value": recorded, "source": "user"}}}
            with open(pj, "w", encoding="utf-8") as fh:
                json.dump(data, fh)
            row = _row(_compared(project, pr15), "preset", "crossover.corner_set")
            assert (row["result"], row["journal"], row["file"]) == (result, journal, "default"), (recorded, row)
            assert row["category"] == "system" and row["path"] == "offset 2307", row
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_compare_file_pr15_numbering_not_settled_is_unknown():
    """Outputs reach a version's rows only by the profile's numbering: a profile that letters them (or none at all)
    leaves every row unknown with its reason -- never a guessed match."""
    import shutil
    import tempfile
    cf = _compare_file()
    real = cf._pr_profile
    top = tempfile.mkdtemp(prefix="autosound_compare_pr15_slots_")
    try:
        project, pr15 = _pico_project(top)
        for profile in ({"groups": [{"id": "physical_outputs", "max_count": 8, "row_id_style": "letter"}]}, None):
            cf._pr_profile = lambda *_args, profile=profile, **_kwargs: profile
            got = _compared(project, pr15)
            rows = [r for r in got["rows"] if r["channel"] in ("tw-L", "tw-R", "w-L", "sub")]
            assert rows and all(r["result"] == "unknown" and r["reason"] for r in rows), rows
            assert not [r for r in got["rows"] if r["result"] != "unknown"], profile
    finally:
        cf._pr_profile = real
        shutil.rmtree(top, ignore_errors=True)


def _check_compare_file_pr15_unreadable_is_exit_2_and_changed_is_exit_3():
    """A `.PR15` that is not a preset, cut short, not there, or another `.PR` model: exit 2 with its kind, no rows. One
    that changes while it is read: exit 3, `changed`. Each refusal carries the Mosconi reader's warning."""
    import shutil
    import tempfile
    cf = _compare_file()
    mp = cf._mosconi()
    real = mp._read_bytes
    top = tempfile.mkdtemp(prefix="autosound_compare_pr15_bad_")
    try:
        project, pr15 = _pico_project(top)
        with open(pr15, "rb") as fh:
            data = fh.read()
        cases = (("garbage.PR15", b"not a preset\r\n" * 3, "format"), ("cut.PR15", data[:len(data) // 2], "truncated"),
                 ("other.PR16", data, "model"), ("none.PR15", None, "io"))
        for name, body, kind in cases:
            path = os.path.join(top, "files", name)
            if body is not None:
                with open(path, "wb") as fh:
                    fh.write(body)
            code, out, err = _compare_cli(project, "compare-file", "v_001", path, "--json")
            refused = json.loads(out)
            assert code == 2 and refused["error"]["kind"] == kind and "rows" not in refused, (name, code, refused)
            assert refused["warning"] == mp.WARNING, refused["warning"]

        def changing(p):
            got = real(p)
            with open(p, "ab") as fh:
                fh.write(b"0\r\n")
            return got
        mp._read_bytes = changing
        try:
            code, out, err = _compare_cli(project, "compare-file", "v_001", pr15, "--json")
        finally:
            mp._read_bytes = real
        refused = json.loads(out)
        assert code == 3 and refused["error"]["kind"] == "changed" and "rows" not in refused, (code, refused)
        code, out, err = _compare_cli(project, "compare-file", "v_009", pr15, "--json")
        assert code == 1 and json.loads(out)["warning"] == mp.WARNING, (code, out)
    finally:
        mp._read_bytes = real
        shutil.rmtree(top, ignore_errors=True)


# ── --from-file (#218 T3): attest records the file and the comparison, propose banks the file's values ─────────────
def _a_versions_file(project, version):
    """The bytes of `version`'s file in the project's ledger, wherever its layout keeps it."""
    for here, _dirs, files in os.walk(os.path.join(project, "state")):
        if version + ".json" in files:
            with open(os.path.join(here, version + ".json"), "rb") as fh:
                return fh.read()
    raise AssertionError(f"no {version}.json under {project}")


def _aya_history(project):
    return _state.PresetHistory(os.path.join(project, "state"), "AYA", project_dir=project)


def _check_attest_from_file_fills_the_source_file():
    """`attest --from-file` reads the file and records it itself: every one of S-119's eight fields, the hash the reader
    took, the save time and PC-Tool version the file states, the model, when it was read -- and `compared` from
    compare-file's own rows of that version against that file: its counts first, then every row that differs and every
    unknown one. The warning is printed, verbatim, before the result."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_attest_from_file_")
    try:
        project, pct6 = _aya_project(top)
        expected = _compared(project, pct6)
        code, out, err = _compare_cli(project, "attest", "--preset", "AYA", "--from-file", pct6)
        assert code == 0, (code, out, err)
        hx = _compare_file()._helix()
        assert out.startswith(hx.WARNING), out[:400]
        assert out.index(hx.WARNING) < out.index("🟢"), out[:600]
        h = _aya_history(project)
        assert h.versions() == ["v_001", "v_002"], h.versions()
        source = h.load("v_002")["preset_settings"]["source_file"]
        assert sorted(source) == sorted(_state._SOURCE_FILE_FIELDS), sorted(source)
        assert all(source[k] for k in _state._SOURCE_FILE_FIELDS), source
        assert source["name"] == "AYA.pct6" and source["path"] == os.path.abspath(pct6), source
        assert source["md5"] == "708ccc26583f90e7dfb84fd9345f670c", source
        assert (source["saved"], source["pctool"]) == ("16.10.2026 18:55", "6.04.03"), source
        assert "HELIX DSP ULTRA S" in source["device"], source
        datetime.datetime.fromisoformat(source["read_at"])
        compared = source["compared"]
        counts = expected["counts"]["result"]
        assert counts["differs"] and isinstance(compared, list), compared
        assert compared[0] == "%s: %d match, %d differs, %d unknown" % (
            expected["contract"], counts["match"], counts["differs"], counts["unknown"]), compared[0]
        for row in expected["rows"]:
            if row["result"] == "match":
                continue
            said = "%s %s %s" % (row["channel"], row["parameter"], row["result"])
            assert any(c.startswith(said + ":") for c in compared), (said, compared)
        assert len(compared) == 1 + counts["differs"] + counts["unknown"], (len(compared), counts)
        assert any(c.startswith("m-L gain_db differs: journal -3, file -3.5") for c in compared), compared
        assert "AYA.pct6 (md5 708ccc26)" in h.render("v_002"), h.render("v_002")
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_from_file_and_source_file_together_are_a_usage_error():
    """`--from-file` with `--source-file` -- two records of one file --, `propose --from-file` with a delta file, and
    either verb with `--evidence` or `--reviewed` beside `--from-file` (a device read is its own evidence) are usage
    errors: exit 2, the usage on stderr, nothing banked."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_from_file_usage_")
    try:
        project, pct6 = _aya_project(top)
        with open(os.path.join(project, "read.json"), "w", encoding="utf-8") as fh:
            json.dump({"name": "AYA.pct6"}, fh)
        with open(os.path.join(project, "delta.json"), "w", encoding="utf-8") as fh:
            json.dump({"w-L": {"gain_db": -1.0}}, fh)
        h = _aya_history(project)
        for argv in (("attest", "--preset", "AYA", "--from-file", pct6, "--source-file", "read.json"),
                     ("attest", "--preset", "AYA", "--source-file", "read.json", "--from-file", pct6),
                     ("propose", "delta.json", "--preset", "AYA", "--from-file", pct6),
                     ("propose", "--preset", "AYA", "--from-file", pct6, "--evidence", "w-L_2 (sw)"),
                     ("attest", "--preset", "AYA", "--from-file", pct6, "--evidence", "w-L_2 (sw)"),
                     ("propose", "--preset", "AYA", "--from-file", pct6, "--reviewed", "read.json"),
                     ("attest", "--preset", "AYA", "--reviewed", "read.json", "--from-file", pct6)):
            code, out, err = _compare_cli(project, *argv)
            assert code == 2 and "usage:" in err and "--from-file" in err and not out, (argv, code, out, err)
            assert h.versions() == ["v_001"], (argv, h.versions())
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_attest_from_file_needs_a_preset_setting():
    """The refusal `--source-file` has: on a version with no preset setting the file would stand alone in
    `preset_settings`, so `attest --from-file` refuses, exit 1, and banks nothing."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_attest_from_file_alone_")
    try:
        project, pct6 = _aya_project(top, edit_state=lambda state: state.pop("preset_settings"))
        code, out, err = _compare_cli(project, "attest", "--preset", "AYA", "--from-file", pct6)
        assert code == 1 and err.startswith("error: ") and "preset setting" in err, (code, out, err)
        assert "--from-file" in err and "--source-file" not in err, err           # the door the person used
        assert _aya_history(project).versions() == ["v_001"], _aya_history(project).versions()
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_from_file_input_changed_is_exit_3():
    """Both verbs hash the file before it is read and after: a file that changed in between -- the reader made to
    change it, once after its read and once before -- is exit 3, and nothing is banked."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_from_file_changed_")
    hx = real = None
    try:
        hx = _compare_file()._helix()
        real = hx.read_pct6
        project, pct6 = _aya_project(top)

        def touch(path):
            with open(path, "ab") as fh:
                fh.write(b"\0")

        def changed_after(source, *args, **kwargs):
            doc = real(source, *args, **kwargs)
            touch(source)
            return doc

        def changed_before(source, *args, **kwargs):
            touch(source)
            return real(source, *args, **kwargs)

        for verb in ("attest", "propose"):
            for reader in (changed_after, changed_before):
                shutil.copyfile(_AYA_PCT6, pct6)
                hx.read_pct6 = reader
                try:
                    code, out, err = _compare_cli(project, verb, "--preset", "AYA", "--from-file", pct6)
                finally:
                    hx.read_pct6 = real
                assert code == 3 and "changed" in err, (verb, reader.__name__, code, out, err)
                assert _aya_history(project).versions() == ["v_001"], (verb, reader.__name__)
    finally:
        if hx is not None:
            hx.read_pct6 = real
        shutil.rmtree(top, ignore_errors=True)


def _expected_from_the_reader(ch):
    """What `propose --from-file` is to take from the reader's channel `ch`, read off `helix_pct6.interpret` itself: the
    level, the delay as PC-Tool shows it, polarity, mute, the legs, and every band that does something or is bypassed."""
    timing = ch["timing"][0]
    want = {"gain_db": round(ch["level"]["value"], 2), "ta_ms": timing["delay"]["display_ms"],
            "polarity": ch["polarity"], "mute": ch["mute_on"]}
    for leg, side in (("hp", "high_pass"), ("lp", "low_pass")):
        have = ch.get(side)
        if have and have.get("state") == "configured":
            short = {"Linkwitz": "LR", "Butterworth": "BW"}[have["family"]]
            want[leg] = {"f": have["frequency_hz"], "type": short, "slope": have["slope_db_oct"]}
        elif have and have.get("state") == "off":
            # a channel with the phase control keeps the OFF leg's corner, its phase reference
            short = {"Linkwitz": "LR", "Butterworth": "BW"}.get(have.get("family"))
            want[leg] = ({"f": have["frequency_hz"], "type": short, "slope": "OFF"}
                         if timing.get("phase_mode") == "phase_adjustable" and short else None)
    bands = []
    for f in ch["filters"]:
        if f["role"] != "eq" or f.get("type") is None:
            continue
        bypassed = f["state"] == "bypassed" and (f["type"] in ("APF1", "APF2") or f.get("gain_db"))
        if f["state"] != "configured" and not bypassed:
            continue
        band = {"type": f["type"], "f": f["frequency_hz"], "i": f["position"]}
        if bypassed:
            band["bypass"] = True
        if f["type"] in ("PK", "LSH", "HSH"):
            band["gain_db"] = f["gain_db"]
        if f["type"] != "APF1":
            band["q"] = f["q"]
        bands.append(band)
    want["eq"] = bands
    return want


def _check_propose_from_file_banks_the_files_values():
    """`propose --from-file` banks a NEW version holding the file's values for every row the slot rules map -- level,
    delay, polarity, mute, both crossover legs, every EQ band, the preset's settings -- and leaves the version before
    it byte for byte. What it does not take is named, every field and channel: a switch the file does not decode, a
    field whose meaning in the file is not established, a setting the file does not store, a row with no slot, and an
    output of the file no row is on. The warning is printed, verbatim, before the result."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_propose_from_file_")
    try:
        def a_row_with_no_slot(state):
            state["channels"]["spare-N"] = {"gain_db": -1.0, "ta_ms": 0.0, "polarity": "NORM", "hp": None, "lp": None}

        project, pct6 = _aya_project(top, edit_state=a_row_with_no_slot,
                                     more_channels=[{"code": "spare-N", "tier": "channels"}])
        before = _a_versions_file(project, "v_001")
        code, out, err = _compare_cli(project, "propose", "--preset", "AYA", "--from-file", pct6)
        assert code == 0, (code, out, err)
        hx = _compare_file()._helix()
        assert out.startswith(hx.WARNING) and out.index(hx.WARNING) < out.index("proposed v_002"), out[:600]
        h = _aya_history(project)
        assert h.versions() == ["v_001", "v_002"], h.versions()
        assert _a_versions_file(project, "v_001") == before, "v_001 was rewritten"
        old, new = h.load("v_001"), h.load("v_002")
        inv = hx.interpret(hx.read_pct6(pct6))
        by_index = {c["index"]: c for c in inv["channels"] if c["kind"] == "output"}
        for code_, index in (("w-L", 16), ("m-L", 18), ("tw-L", 20), ("sw", 24)):
            want, row = _expected_from_the_reader(by_index[index]), new["channels"][code_]
            for field, value in want.items():
                assert row.get(field) == value, (code_, field, row.get(field), value)
        for code_, index in (("VFL", 0), ("VSW", 10)):
            want, row = _expected_from_the_reader(by_index[index]), new["virtual_channels"][code_]
            for field in ("gain_db", "ta_ms", "polarity", "mute", "eq"):
                # a channel with no band working in the file and no `eq` in the version gets none: no empty list
                got = row.get(field, [] if field == "eq" else None)
                assert got == want[field], (code_, field, got, want[field])
        assert new["channels"]["m-L"]["gain_db"] == -3.5 and new["channels"]["tw-L"]["polarity"] == "NORM"
        assert 1000 not in [b["f"] for b in new["channels"]["sw"]["eq"]], new["channels"]["sw"]["eq"]
        settings = new["preset_settings"]
        assert settings["fx"]["subxpander"] is False and settings["fx"]["realcenter"] is True, settings
        assert settings["bt"]["source"] == "BT" and settings["conductor"] == {"sub_lamps": 7}, settings
        # kept as v_001 had them, and named
        assert new["channels"]["sw"]["off"] is False and new["virtual_channels"]["VFL"]["eq_bypass"] is False
        assert new["channels"]["spare-N"] == old["channels"]["spare-N"], new["channels"]["spare-N"]
        kept = out[out.index("Kept as v_001 has them"):]
        for named in ("sw off:", "VFL eq_bypass:", "preset conductor.sub_lamps:", "spare-N:", "Output A",
                      "project.json gives this channel no slot"):
            assert named in kept, (named, kept)
        assert new["provenance"]["kind"] == "pct6" and new["provenance"]["md5"] == "708ccc26583f90e7dfb84fd9345f670c"
        assert "sw off" in " ".join(new["provenance"]["kept"]), new["provenance"]
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_from_file_a_leg_switched_off_keeps_its_corner():
    """A leg written `{f, type, slope: "OFF"}` -- the method's form for a crossover switched off with its corner kept,
    the phase control's reference -- is compared, never refused as a journal fault: its type and frequency against the
    file's stored ones, off against G = 0. propose --from-file takes an OFF leg of a channel with the phase control in
    that form, the file's stored corner kept, so the phase it takes has its reference."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_from_file_off_corner_")
    try:
        def configured_off(state):
            state["channels"]["tw-L"]["lp"] = {"f": 1000, "type": "LR", "slope": "OFF"}

        project, pct6 = _aya_project(top, edit_state=configured_off)
        got = _compared(project, pct6)
        for parameter in ("lp.type", "lp.f", "lp.slope"):
            assert _row(got, "tw-L", parameter)["result"] == "match", (parameter, _row(got, "tw-L", parameter))
        code, out, err = _compare_cli(project, "propose", "--preset", "AYA", "--from-file", pct6)
        assert code == 0, (code, out, err)
        lp = _aya_history(project).load("v_002")["channels"]["tw-L"]["lp"]
        assert lp == {"f": 1000, "type": "LR", "slope": "OFF"}, lp
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_propose_from_file_round_trips_through_compare_file():
    """propose --from-file, then compare-file of the new version against the same file: no row differs -- every value
    propose took from the file matches it -- and the rows v_001 had made to differ are matches now. Every row still
    unknown is one propose named (kept, not taken, taken short), in what it printed and in `provenance`; every row
    v_001 left unknown only because it did not state the value matches now, the phase of m-L (a channel with the phase
    control) among them. A high-pass of a family whose file code is documented and not confirmed (12, Bessel) is
    taken and named, not passed on silently."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_from_file_round_trip_")
    try:
        project, pct6 = _aya_project(top, edit_xml=lambda root: _fils(root, 16)[31].set("T", "12"))
        first = _compared(project, pct6)
        assert first["counts"]["result"]["differs"], "the fixture differs nowhere"
        code, out, err = _compare_cli(project, "propose", "--preset", "AYA", "--from-file", pct6)
        assert code == 0, (code, out, err)
        got = _compared(project, pct6, version="v_002")
        differs = [(r["channel"], r["parameter"], r["journal"], r["file"]) for r in got["rows"] if r["result"] == "differs"]
        assert not differs, differs
        for channel, parameter in (("m-L", "gain_db"), ("tw-L", "polarity"), ("preset", "fx.subxpander"),
                                   ("m-L", "mute"), ("sw", "eq[1].gain_db"), ("VFL", "eq[1].q"), ("m-L", "phase_deg")):
            assert _row(got, channel, parameter)["result"] == "match", (channel, parameter)
        prov = _aya_history(project).load("v_002")["provenance"]
        for where, labels in (("stdout", _named_lines(out)),
                              ("provenance", [line.split(": ", 1)[0] for section in ("kept", "not_taken", "taken_short")
                                              for line in prov.get(section) or []])):
            unnamed = [(r["channel"], r["parameter"], r["reason"]) for r in got["rows"]
                       if r["result"] == "unknown" and not _is_named(labels, r["channel"], r["parameter"])]
            assert not unnamed, (where, unnamed)
            assert "w-L hp.type" in labels, (where, labels)
        unstated = ("the version does not record", "the version does not state", "the version records no")
        now = {(r["channel"], r["parameter"]): r for r in got["rows"]}
        for row in first["rows"]:
            if row["result"] != "unknown" or not str(row["reason"]).startswith(unstated):
                continue
            channel, parameter = row["channel"], row["parameter"]
            after = [r for (c, p), r in now.items() if c == channel and (
                p == parameter or p.startswith(parameter + ".") or p.startswith(parameter + "["))]
            assert after and all(r["result"] == "match" for r in after), (channel, parameter, row["reason"], after)
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_propose_from_file_writes_the_full_family_names():
    """S-136.3: a leg the file holds as Chebyshev is banked by `propose --from-file` as `CHEBYSHEV`, the profiles' and
    the Mosconi reader's spelling, and Self-define as `SELF_DEFINED` -- not `CH` and `SD`. Both spellings are still
    read."""
    import shutil
    import tempfile
    ff = _from_file()
    assert ff.XO_SHORT["Self-define"] == "SELF_DEFINED", ff.XO_SHORT
    assert all(ff.XO_FAMILY[short] == ff.XO_FAMILY[name] for short, name in (("CH", "CHEBYSHEV"),
                                                                            ("SD", "SELF_DEFINED"))), ff.XO_FAMILY
    top = tempfile.mkdtemp(prefix="autosound_from_file_family_names_")
    try:
        project, pct6 = _aya_project(top, edit_xml=lambda root: _fils(root, 16)[31].set("T", "14"))   # Chebyshev HP
        code, out, err = _compare_cli(project, "propose", "--preset", "AYA", "--from-file", pct6)
        assert code == 0, (code, out, err)
        hp = _aya_history(project).load("v_002")["channels"]["w-L"]["hp"]
        assert hp["type"] == "CHEBYSHEV", hp
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_propose_from_file_on_an_unchecked_model_maps_nothing():
    """A model the reader has not checked has no channel layout: no output is named by a slot, so every row stays as the
    version had it and is named, and the model's not-checked line comes with the warning, before the result."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_from_file_unchecked_")
    try:
        project, pct6 = _aya_project(top, edit_xml=lambda root: root.set("Dev", "77"))
        code, out, err = _compare_cli(project, "propose", "--preset", "AYA", "--from-file", pct6)
        assert code == 0, (code, out, err)
        hx = _compare_file()._helix()
        assert out.startswith(hx.WARNING) and out.index("NOT CHECKED") < out.index("proposed v_002"), out[:800]
        h = _aya_history(project)
        old, new = h.load("v_001"), h.load("v_002")
        for tier in ("channels", "virtual_channels"):
            for key, row in old[tier].items():
                assert {k: v for k, v in new[tier][key].items() if k != "status"} == row, (tier, key)
        kept = out[out.index("Kept as v_001 has them"):]
        for named in ("w-L:", "m-L:", "tw-L:", "sw:", "VFL:", "VSW:", "layout is not checked"):
            assert named in kept, (named, kept)
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_from_file_tables_are_compare_files():
    """The codes between the journal and the file are one table for both directions: `from_file.py`'s, which
    compare-file reads its own copy of until it is moved onto it. Until then the two are held equal here."""
    cf, ff = _compare_file(), _from_file()
    assert ff.POLARITY == cf._POLARITY and ff.POLARITY_BACK == cf._POLARITY_BACK, (ff.POLARITY, cf._POLARITY)
    assert ff.EQ_CODES == cf._EQ_CODES and ff.EQ_WITH_GAIN == cf._EQ_WITH_GAIN, (ff.EQ_CODES, cf._EQ_CODES)
    assert ff.XO_FAMILY == cf._XO_FAMILY and ff.XO_SHORT == cf._XO_SHORT, (ff.XO_FAMILY, cf._XO_FAMILY)
    hx = cf._helix()
    outputs = [c for c in hx.interpret(hx.read_pct6(_AYA_PCT6))["channels"] if c["kind"] == "output"]
    assert ff.virtual_by_letter(outputs) == cf._virtual_by_letter(outputs), "the slot rule lives in one place"
    real = cf._virtual_by_letter
    try:                                    # compare-file's rule changed is from_file's rule changed: no second copy
        cf._virtual_by_letter = lambda outputs: {"Z": "compare-file's rule"}
        assert ff.virtual_by_letter(outputs) == {"Z": "compare-file's rule"}, "a second slot rule"
    finally:
        cf._virtual_by_letter = real
    assert ff.virtual_miss(outputs, "G") == cf._virtual_miss(outputs, "G") and "Virtual K" in ff.virtual_miss(outputs, "G")


# ── the fix round of the DSP file readers (W-13): what the review seats found, each held by a check ────────────────
def _strict_json(data):
    """`data` (bytes) read as JSON that a strict reader takes: no NaN, no Infinity."""
    def refuse(name):
        raise AssertionError(f"a version holds {name}, which no strict JSON reader takes")
    return json.loads(data.decode("utf-8"), parse_constant=refuse)


def _named_lines(out):
    """The labels `propose --from-file` names under its three headings: `Kept as`, `Not taken`, `Taken short`."""
    labels = []
    for line in out.splitlines():
        if line.startswith("  - "):
            labels.append(line[4:].split(": ", 1)[0])
    return labels


def _is_named(labels, channel, parameter):
    """True when a compare-file row (`channel`, `parameter`) is one of the names: the row's own name, its channel or
    output alone, or a name the row's sits under (`w-L eq[1]` names `w-L eq[1].f`, `VSW eq` names `VSW eq[1]`)."""
    full = f"{channel} {parameter}"
    for label in labels:
        if label == channel or label == full:
            return True
        if full.startswith(label) and full[len(label)] in ".[ ":
            return True
    return False


def _fils(root, index):
    return _oc(root, index).findall("Fil")


def _check_propose_from_file_keeps_the_bands_it_does_not_decode():
    """A file band in a slot the version holds a band in, and that the file does not decode -- a type code the reader
    does not know, Fine EQ, no frequency, a gain that is no finite number, a frequency of 0 the journal refuses -- is
    not dropped: the version's band in that slot stays, named under `Kept as`, and the file's band under `Not taken`.
    A version whose bands carry no slot keeps its whole EQ and names it. The new version is JSON a strict reader takes."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_from_file_bands_kept_")
    try:
        def odd(root):
            wl = _fils(root, 16)
            wl[0].set("T", "2")                                 # i 1: a type code the reader does not decode
            wl[1].set("T", "1")                                 # i 2: Fine EQ, no band type of the journal's
            del wl[2].attrib["F"]                               # i 3: no frequency
            wl[3].set("G", "inf")                               # i 4: a gain that is no finite number
            _fils(root, 0)[0].set("F", "0")                     # VFL i 1: a frequency the journal refuses
            sw = _fils(root, 24)
            sw[9].attrib.update({"T": "2", "F": "500.00", "G": "-3", "FilBy": "0"})   # sw: bands with no slot

        project, pct6 = _aya_project(top, edit_xml=odd)
        code, out, err = _compare_cli(project, "propose", "--preset", "AYA", "--from-file", pct6)
        assert code == 0, (code, out[-600:], err)
        h = _aya_history(project)
        old, new = h.load("v_001"), h.load("v_002")
        _strict_json(_a_versions_file(project, "v_002"))
        assert new["channels"]["w-L"]["eq"] == old["channels"]["w-L"]["eq"], new["channels"]["w-L"]["eq"]
        vfl = [b for b in new["virtual_channels"]["VFL"]["eq"] if b.get("i") == 1]
        assert vfl == old["virtual_channels"]["VFL"]["eq"], new["virtual_channels"]["VFL"]["eq"]
        assert new["channels"]["sw"]["eq"] == old["channels"]["sw"]["eq"], new["channels"]["sw"]["eq"]
        kept = out[out.index("Kept as v_001 has them"):out.index("Not taken from the file")]
        not_taken = out[out.index("Not taken from the file"):]
        prov_kept, prov_not = " | ".join(new["provenance"]["kept"]), " | ".join(new["provenance"]["not_taken"])
        for name in ("w-L eq[1]", "w-L eq[2]", "w-L eq[3]", "w-L eq[4]", "VFL eq[1]", "sw eq"):
            assert f"  - {name}: " in kept and name + ": " in prov_kept, (name, kept, prov_kept)
        for name in ("w-L eq[1]", "w-L eq[2]", "w-L eq[3]", "w-L eq[4]", "VFL eq[1]", "sw eq[10]"):
            assert f"  - {name}: " in not_taken and name + ": " in prov_not, (name, not_taken)
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_propose_from_file_keeps_values_that_are_not_finite():
    """A level, a leg frequency or a phase that is no finite number, a leg at 0 Hz, an RTC point `NaN`: none is
    banked -- the version's value stays and is named, or, where the version holds none, the file's is named as not
    taken. The new version is JSON a strict reader takes."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_from_file_finite_")
    try:
        def odd(root):
            _oc(root, 18).find("Vol").set("L", "NaN")           # m-L level
            _oc(root, 18).find("T").set("P", "inf")             # m-L phase: the version holds none
            _fils(root, 20)[31].set("F", "inf")                 # tw-L high-pass frequency
            _fils(root, 16)[30].set("F", "0")                   # w-L low-pass at 0 Hz
            root.find("MCV2").set("RTC_GSTART0", "NaN")

        project, pct6 = _aya_project(top, edit_xml=odd)
        code, out, err = _compare_cli(project, "propose", "--preset", "AYA", "--from-file", pct6)
        assert code == 0, (code, out[-600:], err)
        h = _aya_history(project)
        old, new = h.load("v_001"), h.load("v_002")
        _strict_json(_a_versions_file(project, "v_002"))
        assert new["channels"]["m-L"]["gain_db"] == -3.0, new["channels"]["m-L"]
        assert "phase_deg" not in new["channels"]["m-L"], new["channels"]["m-L"]
        assert new["channels"]["tw-L"]["hp"] == old["channels"]["tw-L"]["hp"], new["channels"]["tw-L"]
        assert new["channels"]["w-L"]["lp"] == old["channels"]["w-L"]["lp"], new["channels"]["w-L"]
        assert "gstart0" not in new["preset_settings"]["rtc"]["curve"], new["preset_settings"]["rtc"]
        labels = _named_lines(out)
        for name in ("m-L gain_db", "m-L phase_deg", "tw-L hp", "w-L lp", "preset rtc.curve.gstart0"):
            assert name in labels, (name, labels)
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_propose_from_file_merges_the_rtc_curve_key_by_key():
    """The RTC curve is taken point by point onto the one the version holds: a point the file does not hold, or holds
    as no number, stays as the version had it and is named; the file's other points are taken."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_from_file_rtc_")
    try:
        def held(state):
            state["preset_settings"]["rtc"] = {"curve": {"gstart0": 11, "gstart1": 7, "gstop0": -1}}

        def odd(root):
            mcv = root.find("MCV2")
            del mcv.attrib["RTC_GSTART1"]
            mcv.set("RTC_GSTOP0", "x")

        project, pct6 = _aya_project(top, edit_state=held, edit_xml=odd)
        code, out, err = _compare_cli(project, "propose", "--preset", "AYA", "--from-file", pct6)
        assert code == 0, (code, out[-600:], err)
        curve = _aya_history(project).load("v_002")["preset_settings"]["rtc"]["curve"]
        assert (curve.get("gstart0"), curve.get("gstart1"), curve.get("gstop0")) == (12, 7, -1), curve
        assert curve.get("gstop1") == -2 and curve.get("fstart1") == 10000 and len(curve) == 12, curve
        labels = _named_lines(out)
        for name in ("preset rtc.curve.gstart1", "preset rtc.curve.gstop0"):
            assert name in labels, (name, labels)
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_from_file_refuses_a_pr15():
    """`--from-file` reads a `.pct6` (CONTRACT.md item 14): a `.PR15` given to either verb is exit 2, kind `model`,
    saying compare-file is how a `.PR15` is compared -- nothing banked, nothing written beside the file."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_from_file_pr15_")
    try:
        project, pr15 = _pico_project(top)
        files = _tree_digest(os.path.dirname(pr15))
        for verb in ("attest", "propose"):
            code, out, err = _compare_cli(project, verb, "--preset", "PICO", "--from-file", pr15)
            assert code == 2 and ": model: " in err and "compare-file" in err and ".pct6" in err, (verb, code, out, err)
            assert "Traceback" not in err and _state.PresetHistory(
                os.path.join(project, "state"), "PICO", project_dir=project).versions() == ["v_001"], verb
        assert _tree_digest(os.path.dirname(pr15)) == files
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_compare_file_a_band_of_an_undecoded_type_paired_by_slot_is_unknown():
    """A version's band paired by its slot with a file band whose type the reader does not decode: the type row says
    what the file holds, and the band's frequency, gain and Q are unknown -- the file's values there are not read, so
    they never match. On a `.pct6` and on a `.PR15` alike."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_compare_undecoded_pair_")
    try:
        project, pct6 = _aya_project(top, edit_xml=lambda root: _fils(root, 16)[0].set("T", "2"))
        got = _compared(project, pct6)
        for parameter in ("eq[1].f", "eq[1].gain_db", "eq[1].q"):
            row = _row(got, "w-L", parameter)
            assert row["result"] == "unknown" and "type code 2" in row["reason"], row
    finally:
        shutil.rmtree(top, ignore_errors=True)
    top = tempfile.mkdtemp(prefix="autosound_compare_undecoded_pair_pr_")
    try:
        project, pr15 = _pico_project(top)
        _pr15_edit(pr15, {9280 + 32 * 1 + 20: "130"})            # output 1, band 1: a type byte outside 132-134
        got = _compared(project, pr15)
        for parameter in ("eq[1].f", "eq[1].gain_db", "eq[1].q"):
            row = _row(got, "tw-L", parameter)
            assert row["result"] == "unknown" and "130" in row["reason"], row
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _pr15_edit(path, lines=None, extra=()):
    """The `.PR15` copy at `path` rewritten with `lines` ({0-based line: text}) and `extra` lines appended -- this
    selftest's own copies in its own temp folder only; the method has no encoder."""
    with open(path, "rb") as fh:
        data = fh.read()
    rows = data.split(b"\n")
    tail = rows.pop() if rows and rows[-1] == b"" else None
    for n, text in (lines or {}).items():
        rows[n] = text.encode("ascii") + (b"\r" if rows[n].endswith(b"\r") else b"")
    rows += [t.encode("ascii") + b"\r" for t in extra]
    with open(path, "wb") as fh:
        fh.write(b"\n".join(rows) + (b"\n" if tail is not None else b""))


def _pr15_byte(path, line):
    with open(path, "rb") as fh:
        text = fh.read().split(b"\n")[line].strip()
    return int(text) if text else 0


def _check_compare_file_pr15_an_undecoded_slope_code_is_unknown():
    """A leg's slope code the reader does not decode (5-7) is no OFF: against an OFF leg of the version and against a
    filter of it, the slope is unknown, naming the code -- never a match."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_compare_pr15_slope_")
    try:
        project, pr15 = _pico_project(top)
        edits = {}
        for n, code in ((0, 6), (1, 5)):                         # output 1: its high-pass (a filter), its low-pass (OFF)
            byte = _pr15_byte(pr15, 2304 + 5 * n)
            edits[2304 + 5 * n] = str((byte & ~(7 << 2) & ~64) | (code << 2))
        _pr15_edit(pr15, edits)
        got = _compared(project, pr15)
        for parameter, code in (("hp.slope", 6), ("lp.slope", 5)):
            row = _row(got, "tw-L", parameter)
            assert row["result"] == "unknown" and "slope code %d" % code in row["reason"], row
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_compare_file_pr15_an_assumed_rate_leaves_the_delay_unknown():
    """With no rate byte in the file the delay steps are not read as ms at an assumed 96 kHz and compared: every delay
    is unknown, saying so."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_compare_pr15_rate_")
    try:
        project, pr15 = _pico_project(top)
        _pr15_edit(pr15, {72: ""})
        got = _compared(project, pr15)
        for channel in ("tw-L", "tw-R", "w-L", "sub"):
            row = _row(got, channel, "ta_ms")
            assert row["result"] == "unknown" and "96 kHz assumed" in row["reason"], row
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_compare_file_pr15_names_an_unreadable_bundled_profile():
    """A bundled profile of the model that cannot be read is named, file and why, in the reason every row gives --
    not said as "no bundled profile says how its outputs are named"."""
    import shutil
    import tempfile
    dp = _state._siblings().load("dsp_profile.py")
    real = dp.bundled_dir
    top = tempfile.mkdtemp(prefix="autosound_compare_pr15_profile_")
    try:
        project, pr15 = _pico_project(top)
        shelf = os.path.join(top, "shelf")
        os.makedirs(shelf)
        with open(os.path.join(shelf, "mosconi-pico-6-8-2.json"), "wb") as fh:
            fh.write(b'{"dsp_profile": {"vendor": "Mosconi", "na')
        dp.bundled_dir = lambda: shelf
        got = _compared(project, pr15)
        row = _row(got, "tw-L", "gain_db")
        assert row["result"] == "unknown" and "mosconi-pico-6-8-2.json" in row["reason"], row
        assert "cannot be read" in row["reason"], row
    finally:
        dp.bundled_dir = real
        shutil.rmtree(top, ignore_errors=True)


def _check_compare_file_pr15_rows_it_cannot_decode_are_unknown():
    """On a `.PR15`, each of these is unknown with its reason, never a match: `off`, `eq_bypass`, a band's `bypass`, a
    row field the comparison does not know, a row of the virtual tier, a stated preset setting other than the input
    gain, a band of a type byte outside 132-134. A file that is well formed and damaged -- one line too many, a byte
    over 255 -- is exit 2, `format`."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_compare_pr15_unknowns_")
    try:
        def more(state):
            row = state["channels"]["tw-L"]
            row.update(off=False, eq_bypass=False, weird=1)
            row["eq"][0]["bypass"] = True
            state["virtual_channels"] = {"VX": {"gain_db": 0.0, "ta_ms": 0.0, "polarity": "NORM"}}
            state["preset_settings"] = {"fx": {"realcenter": True}}

        project, pr15 = _pico_project(top, edit_state=more)
        with open(os.path.join(project, "project.json"), encoding="utf-8") as fh:
            pj = json.load(fh)
        pj["channels"].append({"code": "VX", "tier": "virtual_channels", "slot": "1"})
        with open(os.path.join(project, "project.json"), "w", encoding="utf-8") as fh:
            json.dump(pj, fh)
        _pr15_edit(pr15, {9280 + 32 * 10 + 20: "140"})          # output 1, band 10: a type byte outside 132-134
        got = _compared(project, pr15)
        for channel, parameter, said in (("tw-L", "off", "no such switch"), ("tw-L", "eq_bypass", "no such switch"),
                                         ("tw-L", "eq[1].bypass", "bypass"), ("tw-L", "weird", "does not know"),
                                         ("VX", "gain_db", "virtual_channels"), ("preset", "fx.realcenter", "no such"),
                                         ("tw-L", "eq[10]", "type code 140")):
            row = _row(got, channel, parameter)
            assert row["result"] == "unknown" and said in row["reason"], (channel, parameter, row)
        project2, _ = project, None
        files = os.path.dirname(pr15)
        for name, edit, extra in (("extra.PR15", None, ("0",)), ("big.PR15", {100: "256"}, ())):
            path = os.path.join(files, name)
            shutil.copyfile(_PICO_PR15, path)
            _pr15_edit(path, edit, extra)
            code, out, err = _compare_cli(project2, "compare-file", "v_001", path, "--json")
            refused = json.loads(out)
            assert code == 2 and refused["error"]["kind"] == "format" and "rows" not in refused, (name, code, out)
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_attest_from_file_after_propose_names_every_unknown():
    """`propose --from-file`, then `attest --from-file` of the new version against the same file: nothing differs and
    something is still unknown (a switch the file does not decode, an output no row is on), so `compared` is never
    "no difference" -- a list whose first line counts the unknowns and which names every unknown row compare-file gives."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_from_file_attest_after_")
    try:
        project, pct6 = _aya_project(top)
        code, out, err = _compare_cli(project, "propose", "--preset", "AYA", "--from-file", pct6)
        assert code == 0, (code, out[-400:], err)
        expected = _compared(project, pct6, version="v_002")
        counts = expected["counts"]["result"]
        assert counts["differs"] == 0 and counts["unknown"] > 0, counts
        code, out, err = _compare_cli(project, "attest", "v_002", "--preset", "AYA", "--from-file", pct6)
        assert code == 0, (code, out[-400:], err)
        compared = _aya_history(project).load("v_003")["preset_settings"]["source_file"]["compared"]
        assert isinstance(compared, list) and compared[0].endswith("0 differs, %d unknown" % counts["unknown"]), compared
        for row in expected["rows"]:
            if row["result"] == "unknown":
                assert "%s %s unknown: %s" % (row["channel"], row["parameter"], row["reason"]) in compared, row
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_from_file_writes_nothing_beside_the_file():
    """Neither `--from-file` verb writes anything into the file's own folder: not on success, not when the file cannot
    be read (exit 2), not when it changed while it was read (exit 3)."""
    import shutil
    import tempfile
    cf, ff = _compare_file(), _from_file()
    real = {m: m._sha256 for m in (cf, ff) if hasattr(m, "_sha256")}
    top = tempfile.mkdtemp(prefix="autosound_from_file_nowrite_")
    try:
        project, pct6 = _aya_project(top)
        files = os.path.dirname(pct6)
        bad = os.path.join(files, "garbage.pct6")
        with open(bad, "wb") as fh:
            fh.write(b"\x00\x01 not a PC-Tool setup file \x02" * 8)
        before = _tree_digest(files)
        for verb in ("propose", "attest"):
            for path, want in ((pct6, 0), (bad, 2)):
                code, out, err = _compare_cli(project, verb, "--preset", "AYA", "--from-file", path)
                assert code == want, (verb, path, code, out[-300:], err)
                assert _tree_digest(files) == before, (verb, path)
            calls = []

            def moving(path, calls=calls):
                calls.append(path)
                return real[cf](path) if len(calls) == 1 else "0" * 64     # the file reads as another after its read
            for m in real:
                m._sha256 = moving
            try:
                code, out, err = _compare_cli(project, verb, "--preset", "AYA", "--from-file", pct6)
            finally:
                for m, fn in real.items():
                    m._sha256 = fn
            assert code == 3 and "changed" in err, (verb, code, out[-300:], err)
            assert _tree_digest(files) == before, (verb, "exit 3")
    finally:
        for m, fn in real.items():
            m._sha256 = fn
        shutil.rmtree(top, ignore_errors=True)


def _check_from_file_preset_values_are_the_readers():
    """What `propose --from-file` takes for the preset is what the reader itself interprets from the file -- each
    switch, the BT source and auto-switch, every source level, the RTC curve -- read off `helix_pct6.interpret`'s own
    `system` and `routing`, so a code wrong in both of the method's tables still fails here."""
    ff = _from_file()
    hx = _compare_file()._helix()
    doc = hx.read_pct6(_AYA_PCT6)
    inv = hx.interpret(doc)
    got = ff._preset_values(doc, hx)
    fx = inv["system"]["effects"]
    want = {"fx.realcenter": fx["realcenter_on"], "fx.dynamic_bass": fx["dynamic_bass_enhancement_on"],
            "fx.subxpander": fx["subxpander_on"], "rtc.on": fx["remote_tone_control_on"],
            "bt.source": inv["system"]["bt_aux_selector"]["value"],
            "bt.auto_switch": inv["system"]["input_mask"]["bt_auto_switch_on"]}
    for name, aom in (("main", 1), ("hec", 5), ("digital", 9)):
        route = next(r for r in inv["routing"] if r["aom"] == aom)
        want["sources." + name] = round(route["source_level"]["value"], 2)
    want["rtc.curve"] = {key[len("RTC_"):].lower(): value["value"] for band in inv["system"]["rtc_bands"]
                         for key, value in band["configured"].items()}
    assert {k: got.get(k) for k in want} == want, ({k: got.get(k) for k in want}, want)


def _check_from_file_unreadable_is_exit_2_for_both_verbs():
    """A file that is no `.pct6`, one cut short, one not there, and one that decodes and holds a delay `abc`: both
    `--from-file` verbs answer exit 2 with the kind compare-file gives, one line, no traceback, nothing banked."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_from_file_unreadable_")
    try:
        project, pct6 = _aya_project(top)
        files = os.path.dirname(pct6)
        with open(pct6, "rb") as fh:
            data = fh.read()
        cases = {"garbage.pct6": b"\x00\x01 not a PC-Tool setup file \x02" * 8, "cut.pct6": data[:len(data) // 2],
                 "none.pct6": None}
        for name, body in cases.items():
            if body is not None:
                with open(os.path.join(files, name), "wb") as fh:
                    fh.write(body)
        import xml.etree.ElementTree as ET
        root = ET.fromstring(_compare_file()._helix().read_pct6(_AYA_PCT6).xml)
        _oc(root, 16).find("T").set("T", "abc")
        with open(os.path.join(files, "abc.pct6"), "wb") as fh:
            fh.write(_test_container(ET.tostring(root)))
        for name in list(cases) + ["abc.pct6"]:
            path = os.path.join(files, name)
            code, out, _err = _compare_cli(project, "compare-file", "v_001", path, "--json")
            kind = json.loads(out)["error"]["kind"]
            assert code == 2, (name, code)
            for verb in ("attest", "propose"):
                code, out, err = _compare_cli(project, verb, "--preset", "AYA", "--from-file", path)
                assert code == 2 and f": {kind}: " in err and "Traceback" not in err, (verb, name, code, out[-300:], err)
                assert len(err.strip().splitlines()) == 1, (verb, name, err)
                assert _aya_history(project).versions() == ["v_001"], (verb, name)
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_propose_from_file_names_everything_it_does_not_take():
    """One file and one version that hold every kind of thing `propose --from-file` does not take, each named in what
    it prints and in the version's `provenance`: kept -- `tag`, `eq_ptr`, a phase the file does not hold, a level and a
    delay it does not hold, a leg it holds bypassed, a leg of a type code it does not decode, EQ on a channel the file
    has none for, the preset's input gain, a row of another tier, a row whose slot names no channel; not taken -- a
    Fine EQ band, a band of an undecoded type, a band with no frequency; taken short -- an all-pass the file inverts."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_from_file_names_")
    try:
        def the_version(state):
            ch = state["channels"]
            ch["w-L"].update(tag="front", eq_ptr={"w-L": "v_001"})
            ch["m-L"]["phase_deg"] = 10.0
            ch["x-Z"] = {"gain_db": 0.0, "ta_ms": 0.0, "polarity": "NORM", "hp": None, "lp": None}
            state["virtual_channels"]["VSW"]["eq"] = [{"type": "PK", "f": 100, "gain_db": -1.0, "q": 1.0, "i": 1}]
            state["amp_channels"] = {"amp1": {"gain_db": 0.0, "ta_ms": 0.0, "polarity": "NORM"}}
            state["preset_settings"]["input_gain_db"] = 0.5

        def the_file(root):
            del _oc(root, 18).find("T").attrib["P"]                      # m-L: no phase
            del _oc(root, 20).find("Vol").attrib["L"]                    # tw-L: no level
            del _oc(root, 20).find("T").attrib["T"]                      # tw-L: no delay
            _fils(root, 24)[30].set("FilBy", "1")                        # sw: its low-pass bypassed
            _fils(root, 16)[31].set("T", "99")                           # w-L: a high-pass of type code 99
            vsw = _oc(root, 10)
            for f in vsw.findall("Fil"):                                 # VSW: no EQ in the file
                vsw.remove(f)
            ml = _fils(root, 18)
            ml[0].attrib.update({"T": "1", "F": "300.00", "G": "-2", "FilBy": "0"})     # a Fine EQ band
            ml[1].attrib.update({"T": "2", "F": "400.00", "G": "-2", "FilBy": "0"})     # an undecoded band
            ml[2].attrib.update({"T": "17", "G": "-2", "FilBy": "0"})
            del ml[2].attrib["F"]                                                         # a band with no frequency
            _fils(root, 16)[5].attrib.update({"T": "20", "F": "80.00", "G": "0", "Q": "0.7", "I": "1", "FilBy": "0"})

        project, pct6 = _aya_project(top, edit_state=the_version, edit_xml=the_file,
                                     more_channels=[{"code": "x-Z", "tier": "channels", "slot": "Z"},
                                                    {"code": "amp1", "tier": "amp_channels", "slot": "A"}])
        code, out, err = _compare_cli(project, "propose", "--preset", "AYA", "--from-file", pct6)
        assert code == 0, (code, out[-600:], err)
        prov = _aya_history(project).load("v_002")["provenance"]
        sections = {"kept": out[out.index("Kept as v_001"):out.index("Not taken from the file")],
                    "not_taken": out[out.index("Not taken from the file"):out.index("Taken short")],
                    "taken_short": out[out.index("Taken short"):]}
        want = {"kept": ("w-L tag", "w-L eq_ptr", "m-L phase_deg", "tw-L gain_db", "tw-L ta_ms", "sw lp", "w-L hp",
                         "VSW eq", "preset input_gain_db", "amp1", "x-Z"),
                "not_taken": ("m-L eq[1]", "m-L eq[2]", "m-L eq[3]"),
                "taken_short": ("w-L eq[6].invert",)}
        for section, names in want.items():
            for name in names:
                assert f"  - {name}: " in sections[section], (section, name, sections[section])
                assert any(line.startswith(name + ": ") for line in prov.get(section) or []), (section, name, prov)
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_compare_file_head_and_argument_count():
    """`HEAD` is the active slot's version once `set-active` names it; with no slot active and none named it is the
    journal's refusal, exit 1. A wrong number of arguments is usage: exit 2, the usage on stderr, nothing on stdout."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_compare_head_")
    try:
        project, pct6 = _aya_project(top)
        code, out, err = _compare_cli(project, "compare-file", "HEAD", pct6, "--json")
        assert code == 1 and json.loads(out)["error"]["kind"] == "journal", (code, out, err)
        code, out, err = _compare_cli(project, "propose", "--preset", "AYA", "--from-file", pct6)
        assert code == 0, (code, err)
        _state.Registry(os.path.join(project, "state")).set_active("AYA")
        assert _compared(project, pct6, version="HEAD") == _compared(project, pct6, version="v_002")
        assert _compared(project, pct6, version="HEAD") != _compared(project, pct6, version="v_001")
        for argv in (("v_001",), ("v_001", pct6, "extra"), ("v_001", "--json"), ()):
            code, out, err = _compare_cli(project, "compare-file", *argv)
            assert code == 2 and out == "" and "usage:" in err, (argv, code, out, err)
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_from_file_a_journal_fault_is_the_journals():
    """A version whose leg `slope` or `phase_deg` is not a number is the journal's fault for `--from-file` too: both
    verbs exit 1, nothing banked, never exit 2 `interpret`. And past the version's check, compare-file's own catch
    covers only the file: a version it cannot compare raises the journal's error, it is not answered as the file's."""
    import shutil
    import tempfile
    cf = _compare_file()
    for field, edit in (("slope", lambda st: st["channels"]["w-L"]["hp"].update(slope="24")),
                        ("phase_deg", lambda st: st["channels"]["tw-L"].update(phase_deg="0"))):
        top = tempfile.mkdtemp(prefix="autosound_from_file_kinds_")
        try:
            project, pct6 = _aya_project(top, edit_state=edit)
            for verb in ("attest", "propose"):
                code, out, err = _compare_cli(project, verb, "--preset", "AYA", "--from-file", pct6)
                assert code == 1 and err.startswith("error: ") and "not a number" in err, (field, verb, code, err)
                assert _aya_history(project).versions() == ["v_001"], (field, verb)
            snap = _aya_history(project).load("v_001")
            try:
                code, got = cf.compare_journal((snap, _state.project_channels(project)), pct6)
            except ValueError:
                pass
            else:
                raise AssertionError(f"{field}: a version it cannot compare was answered {code} {got.get('error')}")
        finally:
            shutil.rmtree(top, ignore_errors=True)


def _own_tempdir(selftest):
    """`selftest` run with tempfile's folder -- and TMPDIR, for the children it starts -- set to one folder of its own,
    removed with everything in it when the selftest ends, passed or failed, both put back (#148): a check that forgets
    a folder it made leaves it in no shared temp folder (scripts/run-selftests.sh fails a selftest that does)."""
    import functools

    @functools.wraps(selftest)
    def run(*args, **kwargs):
        import os
        import shutil
        import tempfile
        saved = tempfile.tempdir, os.environ.get("TMPDIR")
        own = tempfile.mkdtemp(prefix="selftest_" + os.path.splitext(os.path.basename(__file__))[0] + "_")
        tempfile.tempdir = own
        os.environ["TMPDIR"] = own
        try:
            return selftest(*args, **kwargs)
        finally:
            tempfile.tempdir = saved[0]
            if saved[1] is None:
                os.environ.pop("TMPDIR", None)
            else:
                os.environ["TMPDIR"] = saved[1]
            shutil.rmtree(own, ignore_errors=True)
    return run


@_own_tempdir
def _selftest():
    import shutil
    import tempfile
    failures = []
    for check in (_check_cli_refuses_unreadable, _check_gain_grid_says_an_unreadable_profile,
                  _check_a_held_lock_answers_75, _check_one_hold_over_the_bank,
                  _check_a_missing_project_makes_nothing, _check_a_bad_timeout_is_a_usage_error,
                  _check_no_load_and_save_outside_update, _check_sheet_samples_follow_the_profile,
                  _check_an_unwritten_delta_is_said, _check_the_sheet_rate_is_read_first_and_said_by_cause,
                  _check_a_delta_after_a_candidate_is_refused, _check_a_fix_on_a_candidate_stays_held,
                  _check_a_candidate_is_promoted_with_evidence_and_a_reviewer,
                  _check_a_trim_is_a_row_with_no_reviewer, _check_preset_settings_merge_and_refusals,
                  _check_preset_settings_candidate_and_source_file, _check_source_file_needs_a_preset_setting,
                  _check_a_candidate_switched_into_the_slot_is_held_then_promoted, _check_attest_refuses_a_candidate,
                  _check_a_base_that_is_not_head_answers_to_the_slot, _check_rows_the_sheet_lists_are_proposed,
                  _check_a_candidate_base_is_no_candidate, _check_a_device_read_vouches_only_for_the_rows_it_read,
                  _check_a_candidate_with_no_moves_of_its_own_is_still_held, _check_a_row_gone_is_a_structural_move,
                  _check_a_plain_propose_keeps_the_slots_named_variant,
                  _check_compare_file_keys_are_the_pinned_ones, _check_compare_file_matches_and_differs_on_aya,
                  _check_compare_file_unknown_is_never_a_match, _check_compare_file_audio_first,
                  _check_compare_file_unreadable_is_exit_2, _check_compare_file_input_changed_is_exit_3,
                  _check_compare_file_writes_nothing, _check_compare_file_delay_rounds_half_up_on_both_sides,
                  _check_compare_file_a_leg_with_no_slope_is_unknown,
                  _check_compare_file_a_preset_row_without_its_value_is_system,
                  _check_compare_file_a_journal_fault_is_the_journals,
                  _check_from_file_a_leg_switched_off_keeps_its_corner,
                  _check_compare_file_bands_it_cannot_decode_and_an_inverted_all_pass,
                  _check_compare_file_virtual_letters_are_pc_tools,
                  _check_compare_file_an_ordinal_lettered_project_keeps_its_slots,
                  _check_compare_file_a_file_it_cannot_interpret_is_exit_2,
                  _check_compare_file_pr15_matches_differs_and_unknown,
                  _check_compare_file_pr15_numbering_not_settled_is_unknown,
                  _check_compare_file_pr15_corner_set_against_the_project,
                  _check_compare_file_pr15_unreadable_is_exit_2_and_changed_is_exit_3,
                  _check_attest_from_file_fills_the_source_file,
                  _check_from_file_and_source_file_together_are_a_usage_error,
                  _check_attest_from_file_needs_a_preset_setting, _check_from_file_input_changed_is_exit_3,
                  _check_propose_from_file_banks_the_files_values,
                  _check_propose_from_file_round_trips_through_compare_file,
                  _check_propose_from_file_on_an_unchecked_model_maps_nothing,
                  _check_from_file_tables_are_compare_files, _check_propose_from_file_writes_the_full_family_names,
                  _check_propose_from_file_keeps_the_bands_it_does_not_decode,
                  _check_propose_from_file_keeps_values_that_are_not_finite,
                  _check_propose_from_file_merges_the_rtc_curve_key_by_key, _check_from_file_refuses_a_pr15,
                  _check_compare_file_a_band_of_an_undecoded_type_paired_by_slot_is_unknown,
                  _check_compare_file_pr15_an_undecoded_slope_code_is_unknown,
                  _check_compare_file_pr15_an_assumed_rate_leaves_the_delay_unknown,
                  _check_compare_file_pr15_names_an_unreadable_bundled_profile,
                  _check_compare_file_pr15_rows_it_cannot_decode_are_unknown,
                  _check_attest_from_file_after_propose_names_every_unknown,
                  _check_from_file_writes_nothing_beside_the_file, _check_from_file_preset_values_are_the_readers,
                  _check_from_file_unreadable_is_exit_2_for_both_verbs,
                  _check_propose_from_file_names_everything_it_does_not_take,
                  _check_compare_file_head_and_argument_count, _check_from_file_a_journal_fault_is_the_journals):
        try:
            check()
        except AssertionError as exc:
            failures.append(f"{check.__name__}: {exc}")
    assert not failures, "\n".join(failures)

    # The chain's project is a folder of its own, removed at the end -- never $TMPDIR itself (the final review's m-8): the
    # ledger's `project_dir` is its root's parent, and the evidence files, the review and `docs/sheets/` below were
    # written straight into the shared temp root, where a bank also read `project.json` strictly.
    parent = tempfile.mkdtemp(prefix="autosound_apply_")
    root = os.path.join(parent, "state")
    h = _state.PresetHistory(root, "SQ_Jazzi")
    h.snapshot(_state._sample_state(), note="baseline")   # seed HEAD (all applied)

    # propose a delta: w-L gain + TA, sub polarity flip.
    delta = {"w-L": {"gain_db": -7.5, "ta_ms": 5.45}, "sub": {"polarity": "INV"}}
    # #57 P2: a polarity flip is structural. With no evidence and no review it banks as a 🟠 CANDIDATE -- on the
    # line, not in the slot, never to be entered -- and says what it waits for.
    cand = propose(h, delta, note="sub INV test + w-L trim")
    assert cand["candidate"] and cand["version"] == "v_002" and h.head() == "v_001", cand
    assert cand["structural"] == ["sub polarity"] and "🟠 CANDIDATE" in cand["sheet"], cand
    assert h.load("v_002")["channels"]["sub"]["status"] == "candidate"
    assert any("reviewer" in w for w in cand["waits_for"]) and any("no evidence" in w for w in cand["waits_for"])
    # A verdict the tool marked UNVERIFIED is not evidence (the reverted polarity flip of #57 P2).
    unv = os.path.join(h.project_dir, "joint-verdict.json")
    with open(unv, "w", encoding="utf-8") as fh:
        json.dump({"verdict": "apply UNVERIFIED"}, fh)
    assert evidence_problems(["joint-verdict.json"], h.project_dir), "an UNVERIFIED verdict passed as evidence"
    assert evidence_problems(["sub+w-L_2 (sw)"], h.project_dir) == [], "a measurement title is evidence"
    # A DESK result is evidence too: the car is for verifying, once for several changes (the Arbiter, 2026-09-23).
    desk = os.path.join(h.project_dir, "predicted.json")
    with open(desk, "w", encoding="utf-8") as fh:
        json.dump({"junctions": [{"lo": "sub", "hi": "w-L", "sum_loss_avg_db": -0.2}]}, fh)
    assert evidence_problems(["predicted.json"], h.project_dir) == [], "a desk result is evidence"
    review = os.path.join(h.project_dir, "review-sub-inv.md")
    with open(review, "w", encoding="utf-8") as fh:
        fh.write("reviewed")
    r = propose(h, delta, note="sub INV test + w-L trim", evidence=["sub+w-L_2 (sw)"], reviewed=review, on="v_002")
    assert not r["candidate"] and r["version"] == "v_003" and h.head() == "v_003", r
    # settings sheet carries old→new with derived samples and the polarity flip.
    assert "5.38 ms (516 smp) → 5.45 ms (523 smp)" in r["sheet"], r["sheet"]
    assert "-7.8 dB → -7.5 dB" in r["sheet"]
    assert "NORM → INV" in r["sheet"]
    # polarity flip raised a (non-blocking) advisory.
    assert any("polarity" in a for a in r["advisories"]), r["advisories"]
    # the banked snapshot marks exactly the touched channels proposed; others stay applied.
    s2 = h.load("v_003")
    assert s2["channels"]["w-L"]["status"] == "proposed"
    assert s2["channels"]["sub"]["status"] == "proposed"
    assert s2["channels"]["tw-R"]["status"] == "applied", "untouched channel must stay applied"

    # attest → flips proposed→applied in a new snapshot.
    a = attest(h, "v_003")
    assert a["version"] == "v_004" and set(a["applied_channels"]) == {"w-L", "sub"}, a
    s3 = h.load("v_004")
    assert all(s3["channels"][c]["status"] == "applied" for c in ("w-L", "sub", "tw-R"))

    # ── virtual tier (schema v2): a TIER-KEYED delta addresses a tier other than `channels` ──
    # this is the thing the gate literally could not do before schema v2 -- a virtual-channel
    # change had nowhere to be proposed, so it could never be banked or attested.
    r_v = propose(h, {"virtual_channels": {"VFL": {"gain_db": -1.0}}}, note="VFL trim")
    assert h.load(r_v["version"])["virtual_channels"]["VFL"]["status"] == "proposed"
    assert "virtual_channels:VFL" in r_v["sheet"], r_v["sheet"]
    assert "0 dB → -1 dB" in r_v["sheet"], r_v["sheet"]
    a_v = attest(h, r_v["version"])
    assert "virtual_channels:VFL" in a_v["applied_channels"], a_v
    assert h.load(a_v["version"])["virtual_channels"]["VFL"]["status"] == "applied"

    # DETERMINISTIC REFUSALS — and none of them bank a snapshot.
    n_before = len(h.versions())
    for bad, why in [
        ({"w-L": {"gaindb": -7}}, "unknown field (typo gaindb)"),
        ({"w-L": {"ta_samples": 520}}, "TA as samples not ms"),
        ({"c": {"gain_db": -9}}, "partial edit of a non-existent channel"),
        ({"virtual_channels": {"VFL": {"gaindb": -1}}}, "unknown field, non-`channels` tier"),
    ]:
        try:
            propose(h, bad)
            raise AssertionError(f"gate accepted bad delta: {why}")
        except ValueError:
            pass
    assert len(h.versions()) == n_before, "a refused delta must NOT bank a snapshot"

    # adding a NEW full channel is allowed (enabling center).
    full_c = {"c": {"hp": {"f": 400, "type": "LR", "slope": 24},
                    "lp": {"f": 1200, "type": "LR", "slope": 24}, "gain_db": -9.0,
                    "ta_ms": 6.0, "polarity": "NORM", "eq_ptr": {}}}
    rc = propose(h, full_c, note="enable center", evidence=["c_2 (sw)"], reviewed=review)   # new edges: structural
    assert h.load(rc["version"])["channels"]["c"]["status"] == "proposed"
    assert "NEW row" in rc["sheet"]

    # ── identity is NOT proposable through the ledger any more (schema v3, SCR-001) ──
    # A driver's name/slot/role is a project fact; routing it through a tuning delta would bank it
    # into a snapshot, which is the two-homes-for-one-fact problem v3 removes. `project.py
    # set-channel` is where these go now.
    try:
        propose(h, {"c": {"role": "center", "descr": "Front Center Full"}}, note="identity")
        raise AssertionError("propose accepted identity fields")
    except ValueError as exc:
        assert "unknown field" in str(exc), exc

    # tuning fields on the same row still merge fine, including structured EQ bands.
    ann = propose(h, {"c": {"eq": [{"type": "PK", "f": 1000, "gain_db": -9, "q": 2},
                                   {"type": "PK", "f": 1450, "gain_db": -9, "q": 2}]}},
                  note="center EQ")
    c_after = h.load(ann["version"])["channels"]["c"]
    assert c_after["eq"][0]["type"] == "PK" and c_after["eq"][0]["f"] == 1000, c_after
    # the sheet is what the human keys in, so EQ bands must read as bands -- not a Python dict/list repr.
    assert "PK 1000 -9 Q2 · PK 1450 -9 Q2" in ann["sheet"], ann["sheet"]
    assert "{'type'" not in ann["sheet"], ann["sheet"]

    # ── multi-slot slot-guard (issue #5): propose to a NON-active slot is refused, banks nothing ──
    reg = _state.Registry(root)
    h2 = _state.PresetHistory(root, "ResoNix")
    h2.snapshot(_state._sample_state(), note="resonix baseline")
    reg.set_active("ResoNix")                              # active slot = ResoNix; h is SQ_Jazzi
    n0 = len(h.versions())
    try:
        propose(h, {"w-L": {"gain_db": -7.0}}, registry=reg)
        raise AssertionError("gate accepted a proposal aimed at a non-active slot")
    except ValueError as e:
        assert "SLOT MISMATCH" in str(e), e
    assert len(h.versions()) == n0, "a slot-mismatch refusal must NOT bank a snapshot"
    # deliberate override banks + stamps NON-ACTIVE; on the active slot the sheet stamps ACTIVE.
    r_over = propose(h, {"w-L": {"gain_db": -7.0}}, registry=reg, allow_nonactive=True)
    assert "NON-ACTIVE SLOT" in r_over["sheet"], r_over["sheet"]
    reg.set_active("SQ_Jazzi")
    r_act = propose(h, {"w-L": {"gain_db": -7.1}}, registry=reg)
    assert "ACTIVE SLOT ✅" in r_act["sheet"], r_act["sheet"]

    # ── SCR-039: a renamed channel is addressed by its CURRENT name and lands on the row the
    # ledger has always kept under its id. Its own project dir, since this needs a project.json.
    ren_root = tempfile.mkdtemp(prefix="autosound_apply_rename_")
    with open(os.path.join(ren_root, "project.json"), "w", encoding="utf-8") as f:
        json.dump({"schema_version": _state.SCHEMA_VERSION, "project_rev": 2,
                   "channels": [{"code": "w-L", "id": "m-L", "previous_names": ["m-L"],
                                 "slot": "C"}]}, f)
    h3 = _state.PresetHistory(os.path.join(ren_root, "state"), "SQ_Jazzi", project_dir=ren_root)
    seed = _state._sample_state()
    seed["channels"] = {"m-L": dict(seed["channels"]["w-L"])}      # the ledger key is the id
    h3.snapshot(seed, note="baseline written before the rename")
    r_ren = propose(h3, {"w-L": {"gain_db": -3.5}}, note="addressed by the current name")
    after = h3.load(r_ren["version"])["channels"]
    assert set(after) == {"m-L"}, f"a rename must not fork the row: {sorted(after)}"
    assert after["m-L"]["gain_db"] == -3.5, after
    # a full definition for a genuinely new channel is still an ADD, not a resolution.
    full = dict(seed["channels"]["m-L"], gain_db=-1.0)
    r_new = propose(h3, {"tw-L": full}, note="a real new channel")
    assert set(h3.load(r_new["version"])["channels"]) == {"m-L", "tw-L"}

    # ── S-079 (the Arbiter, 2026-10-01): both notations are one name. The Passat's shape -- code `w-L`, id `w_L`,
    # ledger rows keyed either way -- and a delta addressed either way lands on the row that is there.
    passat = {"w-L": {"code": "w-L", "id": "w_L", "previous_names": ["w_L"]}}
    passat["w_L"] = passat["w-L"]
    for rows, name, row in (({"w-L": {}}, "w_L", "w-L"), ({"w_L": {}}, "w-L", "w_L"), ({"w-L": {}}, "w-L", "w-L"),
                            ({"tw_L": {}}, "tw-L", "tw_L"), ({"tw-L": {}}, "tw_L", "tw-L")):
        assert _row_key(rows, name, passat) == row, (rows, name, _row_key(rows, name, passat))
        assert _row_key(rows, name, None) == row, "no project file: still one name"
    assert _row_key({"m-L": {}}, "w-L", passat) == "w-L", "a different channel is not reached by the notation"
    landed = apply_delta({"channels": {"w-L": {"gain_db": -7.0}}}, {"w_L": {"gain_db": -3.0}}, passat)
    assert set(landed["channels"]) == {"w-L"} and landed["channels"]["w-L"]["gain_db"] == -3.0, landed
    # Two rows of one name are refused, never merged: which one the delta meant is not guessed.
    try:
        apply_delta({"channels": {"w_L+tw-L": {"gain_db": 0.0}, "w-L+tw_L": {"gain_db": 0.0}}},
                    {"w-L+tw-L": {"gain_db": -1.0}})
    except ValueError as exc:
        assert "S-079" in str(exc) and "not guessed" in str(exc), exc
    else:
        raise AssertionError("apply_delta merged two rows of one name")
    # The Fable review of W-5 #103: a ledger holding BOTH spellings is refused even when one matches as typed (the
    # exact match would update the stale row silently), and a channel with no row yet gets it under the hyphen.
    try:
        _row_key({"w_L": {}, "w-L": {}}, "w-L", passat)
    except ValueError as exc:
        assert "not guessed" in str(exc), exc
    else:
        raise AssertionError("an exact match hid a twin row")
    assert _row_key({"m-L": {}}, "tw_L", None) == "tw-L", "a new row is written in the hyphen notation"

    # #52: the gain step is the machine's setting. Known: a trim off it is named; unknown: a trim with decimals asks.
    gproj = tempfile.mkdtemp(prefix="autosound_gaingrid_")
    base = {"channels": {"w-L": {"gain_db": -7.0}}}
    with open(os.path.join(gproj, "dsp_profile.json"), "w", encoding="utf-8") as fh:
        json.dump({"dsp_profile": {"channel_gain": {"step_options_db": [1.0, 0.5, 0.25, 0.1]}}}, fh)
    said = gain_grid_advisories(gproj, base, {"channels": {"w-L": {"gain_db": -1.2}}})
    assert said and "not recorded" in said[0] and "w-L -1.2" in said[0], said
    assert gain_grid_advisories(gproj, base, {"channels": {"w-L": {"gain_db": -2.0}}}) == []
    with open(os.path.join(gproj, "dsp_profile.json"), "w", encoding="utf-8") as fh:
        json.dump({"dsp_profile": {"channel_gain": {"step_db": 1.0}}}, fh)
    said = gain_grid_advisories(gproj, base, {"channels": {"w-L": {"gain_db": -1.2}}})
    assert said and "set to 1 dB" in said[0] and "rounded" in said[0], said
    assert gain_grid_advisories(os.path.join(gproj, "nowhere"), base, {"channels": {"w-L": {"gain_db": -1.2}}}) == []
    # #58 P6: an edge that moved while its delay stayed is named -- the delay was set for the old edge.
    cur_ = {"channels": {"tw-L": {"hp": {"f": 2800, "type": "BE", "slope": 24}, "ta_ms": 2.6}}}
    new_ = {"channels": {"tw-L": {"hp": {"f": 3500, "type": "LR", "slope": 24}, "ta_ms": 2.6}}}
    assert any("set for the old edge" in a for a in advisories(cur_, new_)), advisories(cur_, new_)
    # skill #74: from a terminal, one line banks a delta file as the yellow version and prints the sheet -- the step
    # that puts a proposal in front of the Arbiter used to need Python typed by hand, and was skipped.
    import io, contextlib
    cli_root = tempfile.mkdtemp(prefix="autosound_apply_cli_")
    cli_h = _state.PresetHistory(os.path.join(cli_root, "state"), "SQ", project_dir=cli_root)
    cli_h.snapshot(_state._sample_state(), note="baseline")
    _state.Registry(os.path.join(cli_root, "state")).set_active("SQ")
    with open(os.path.join(cli_root, "eq-delta.json"), "w", encoding="utf-8") as fh:
        json.dump({"w-L": {"gain_db": -1.0}}, fh)
    with open(os.path.join(cli_root, "review.md"), "w", encoding="utf-8") as fh:
        fh.write("reviewed")
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        assert _main(["apply.py", cli_root, "propose", "eq-delta.json", "--note", "trim",
                      "--evidence", "w-L_2 (sw)", "--reviewed", "review.md"]) == 0
    assert "🟡 proposed v_002 on SQ" in out.getvalue() and "w-L" in out.getvalue(), out.getvalue()
    assert cli_h.load("v_002")["channels"]["w-L"]["status"] == "proposed"
    # skill #61: the sheet is a file in the project's docs/sheets/, by version and slot.
    sheet_file = os.path.join(cli_root, "docs", "sheets", "v_002-SQ.md")
    assert os.path.isfile(sheet_file) and "APPLY THIS" in open(sheet_file, encoding="utf-8").read(), sheet_file
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        assert _main(["apply.py", cli_root, "attest"]) == 0
    assert "🟢 v_003" in out.getvalue() and cli_h.load("v_003")["channels"]["w-L"]["status"] == "applied", out.getvalue()
    assert _main(["apply.py", cli_root, "propose", "no-such.json"]) == 1
    shutil.rmtree(parent, ignore_errors=True)

    print(f"selftest OK — propose banked 🟡 + settings-sheet (old→new, 5.45 ms=523 smp@96k), "
          f"advisory on polarity flip, attest flipped 🟡→🟢 (w-L,sub); tier-keyed delta proposed+"
          f"attested a VIRTUAL-tier row (schema v2 — impossible before this), structured EQ bands "
          f"read as bands not a dict repr; 4 deterministic refusals banked nothing, new-channel add "
          f"allowed; a renamed channel's delta landed on its id row rather than forking it "
          f"(SCR-039); slot-guard refused a non-active-slot propose (banked nothing) + stamped "
          f"ACTIVE/NON-ACTIVE; propose beside a seals.json that cannot be read exits 1 naming it, banking "
          f"nothing (#136); under another writer's lock propose and attest exit 75 with one busy line, no "
          f"version, delta or sheet, and one hold covers the snapshot, its delta and its sheet, the snapshot "
          f"re-entering it with the ledger outside the project; attest on a project folder that is not there makes "
          f"nothing, and a bad AUTOSOUND_LOCK_TIMEOUT_S is exit 2 with its one line, nothing made (#141); a delta "
          f"past an unplaced candidate is refused, on=<candidate> stays held until evidence and a reviewer, then "
          f"promotes, the sheet measured from the DSP, `parent` the true base on both layouts (#199). "
          f"root={root}")
    return 0


_USAGE = """usage: apply.py <project-dir> propose <delta.json> [--preset P] [--note TEXT] [--evidence E ...] [--reviewed FILE] [--on v_NNN|HEAD]
       apply.py <project-dir> propose --from-file FILE.pct6 [--preset P] [--note TEXT] [--on v_NNN|HEAD]
       apply.py <project-dir> attest [v_NNN] [--preset P] [--note TEXT] [--source-file FILE.json | --from-file FILE.pct6]
       apply.py <project-dir> compare-file <v_NNN|HEAD> FILE.pct6 [--json] [--preset P]
       apply.py --selftest

  propose   bank the delta as a YELLOW version and print the settings sheet the Arbiter enters (skill #74: a
            proposal is a version on his screen, never files on disk; `eq_propose --accept` writes the delta).
            --on names the base: a version of this slot, or HEAD; past a candidate not in the slot it is required (#199)
  attest    the Arbiter entered it: flip the proposed rows to green, as a new version.
            --source-file: a JSON object, the saved preset this version was read from (state/schema.md, #200);
            refused on a version with no preset setting (it would stand alone in `preset_settings`)
            --from-file: the method fills that record from a saved .pct6 itself, with compare-file's comparison of the
            version against it; not with --source-file (#218)
  propose --from-file  a NEW version from a saved .pct6's values -- channels, crossovers, EQ, the preset's settings --
            for every row the slot rules map; what the file does not give stays as the base had it, and is named.
            Both --from-file verbs print the reader's warning first; exit 2 the file cannot be read, 3 it changed
            while it was read, nothing banked. FILE is taken as given (a relative path is the current folder's)
  compare-file  a version of the journal against a saved .pct6, row by row (match / differs / unknown, audio first);
            read only, writes nothing anywhere. --json: the shape CONTRACT.md item 13 pins. Exit 0 compared,
            1 the version is not there, 2 the file cannot be read, 3 the file changed while it was read (#218)
"""


def _compare_file_main(project_dir, args):
    """`compare-file <version> FILE [--json] [--preset P]` (#218 T2): exit 0 compared, 1 the journal refused, 2 the
    file unreadable (or usage), 3 the file changed while it was read. Writes nothing."""
    as_json, preset, rest = False, None, []
    i = 0
    while i < len(args):
        if args[i] == "--json":
            as_json = True
            i += 1
        elif args[i] == "--preset" and i + 1 < len(args):
            preset = args[i + 1]
            i += 2
        else:
            rest.append(args[i])
            i += 1
    if len(rest) != 2 or any(a.startswith("--") for a in rest):
        print(_USAGE, file=sys.stderr)
        return 2
    version, path = rest[0], os.path.abspath(rest[1])
    cf = _compare_file()
    try:                            # the journal's errors only: the file's are answered, exit 2 or 3, never raised
        journal = cf.load_journal(project_dir, version, preset=preset)
        code, result = cf.compare_journal(journal, path)
    except (ValueError, OSError) as exc:
        if as_json:
            print(json.dumps(cf.refusal(cf.warning_for(path), os.path.basename(path), "journal", str(exc)),
                             ensure_ascii=False, indent=2))
        print(f"error: {exc}", file=sys.stderr)
        return cf.EXIT_JOURNAL
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif code == cf.EXIT_COMPARED:
        print(cf.render(result, version))
    if code != cf.EXIT_COMPARED:
        print(f"error: {result['file']['name']}: {result['error']['kind']}: {result['error']['message']}",
              file=sys.stderr)
    return code


def _from_file_main(history, cmd, path, rest, opts, registry, preset):
    """`attest [v] --from-file FILE` and `propose --from-file FILE` (#218 T3): the warning first, verbatim -- and the
    model's not-checked line beside it -- then the result. Exit 0 banked, 2 the file cannot be read, 3 it changed
    while it was read (nothing banked on either); the journal's refusals raise to `_main`, exit 1."""
    if cmd == "attest":
        code, got = attest_from_file(history, path, rest[0] if rest else None, note=opts["--note"])
    else:
        code, got = propose_from_file(history, path, note=opts["--note"], registry=registry, on=opts["--on"])
    if code:
        print(f"error: {got['file']['name']}: {got['error']['kind']}: {got['error']['message']}", file=sys.stderr)
        return code
    ff = _from_file()
    print(got["warning"])
    print(ff.model_line(got["device"]))
    print()
    if cmd == "attest":
        source, counts = got["source_file"], got["counts"]
        print(f"🟢 {got['version']} on {preset}: applied {', '.join(got['applied_channels']) or 'nothing proposed'}")
        print(f"source file: {source['name']} (md5 {source['md5']}, saved {source['saved']}, PC-Tool {source['pctool']}),"
              f" read {source['read_at']}")
        print(f"compared: {counts['match']} match, {counts['differs']} differs, {counts['unknown']} unknown"
              + ("" if isinstance(source["compared"], str) else " -- `compare-file` lists every row"))
        for line in source["compared"][1:] if isinstance(source["compared"], list) else ():
            if " differs: " in line:
                print(f"  - {line}")
        return 0
    print(f"{'🟠 candidate' if got['candidate'] else '🟡 proposed'} {got['version']} on {preset}, read from {got['file']}")
    print(got["sheet"])
    print("\n".join(ff.render_names(got, got["base"])))
    return 0


def _main(argv):
    if "--selftest" in argv:
        return _selftest()
    if len(argv) < 3:
        print(_USAGE, file=sys.stderr)
        return 2
    project_dir, cmd, args = argv[1], argv[2], list(argv[3:])
    if cmd == "compare-file":       # read only: no slot to be active, no lock, nothing banked (#218)
        return _compare_file_main(project_dir, args)
    opts ={"--preset": None, "--note": None, "--reviewed": None, "--on": None, "--source-file": None,
           "--from-file": None}
    evidence = []
    rest = []
    i = 0
    while i < len(args):
        if args[i] in opts and i + 1 < len(args):
            opts[args[i]] = args[i + 1]
            i += 2
        elif args[i] == "--evidence" and i + 1 < len(args):
            evidence.append(args[i + 1])
            i += 2
        else:
            rest.append(args[i])
            i += 1
    root = os.path.join(project_dir, "state")
    registry = _state.Registry(root)
    preset = opts["--preset"] or registry.get_active()
    if not preset:
        print(f"error: no active slot in {root}/registry -- pass --preset", file=sys.stderr)
        return 2
    history = _state.PresetHistory(root, preset, project_dir=project_dir)
    if opts["--from-file"]:
        # One record of one file: the file read, or a JSON of it, or a delta -- never two (#218 T3). A device read is
        # its own evidence, so a reviewer or evidence beside it would be taken for nothing.
        beside = [name for name, given in (("--source-file", cmd == "attest" and opts["--source-file"]),
                                           ("a delta file", cmd == "propose" and rest),
                                           ("--evidence", evidence), ("--reviewed", opts["--reviewed"])) if given]
        if beside:
            print(f"error: --from-file takes no {', '.join(beside)} beside it\n" + _USAGE, file=sys.stderr)
            return 2
    try:
        if opts["--from-file"] and cmd in ("propose", "attest"):
            return _from_file_main(history, cmd, os.path.abspath(opts["--from-file"]), rest, opts, registry, preset)
        if cmd == "propose":
            if not rest:
                print(_USAGE, file=sys.stderr)
                return 2
            delta_path = rest[0] if os.path.isabs(rest[0]) else os.path.join(project_dir, rest[0])
            with open(delta_path, encoding="utf-8") as fh:
                delta = json.load(fh)
            got = propose(history, delta, note=opts["--note"] or f"proposed from {os.path.basename(rest[0])}",
                          registry=registry, evidence=evidence or None, reviewed=opts["--reviewed"], on=opts["--on"])
            print(f"{'🟠 candidate' if got['candidate'] else '🟡 proposed'} {got['version']} on {preset}")
            print(got["sheet"])
            return 0
        if cmd == "attest":
            source_file = None
            if opts["--source-file"]:
                source_path = (opts["--source-file"] if os.path.isabs(opts["--source-file"])
                               else os.path.join(project_dir, opts["--source-file"]))
                with open(source_path, encoding="utf-8-sig") as fh:   # an editor's or PowerShell's BOM is no fault
                    source_file = json.load(fh)
            got = attest(history, rest[0] if rest else None, note=opts["--note"], source_file=source_file)
            print(f"🟢 {got['version']} on {preset}: applied {', '.join(got['applied_channels']) or 'nothing proposed'}")
            return 0
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001 -- matched by its attribute; anything else still raises
        # The project's writer lock first (#141, `write_lock.py`): another writer held it past the wait -- 75, its one
        # `busy:` line, nothing written, safe to retry -- or the wait, AUTOSOUND_LOCK_TIMEOUT_S, is no number of
        # seconds: a usage error, said before anything was taken.
        if getattr(type(exc), "is_busy", False):
            return _write_lock().busy_exit(exc)
        if getattr(type(exc), "exit_code", None) == 2:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        # The snapshot refuses a `seals.json` or a `project.json` that is there and cannot be read (#136), and the lock
        # a project folder it cannot be made in (#141, `write_lock.Unwritable`).
        if not getattr(exc, "is_unreadable", False):
            raise
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(_USAGE, file=sys.stderr)
    return 2


if __name__ == "__main__":
    # issue #21: a code page must not destroy a result. Run from a subdirectory, so the sibling
    # modules' own directory has to go on the path before `console` can be found at all.
    import os as _os, sys as _sys
    _sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
    import console
    console.install()
    raise SystemExit(_main(sys.argv))
