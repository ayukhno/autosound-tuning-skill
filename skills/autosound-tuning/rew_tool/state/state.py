"""Versioned hard-params DSP state — the anti-drift anchor AND the experimentation engine.

The single source of truth is one JSON per snapshot (`v_NNN.json`) under `<root>/<preset>/`.
A human-readable Markdown settings sheet is GENERATED from that JSON (`render`); it is never
hand-edited. Editing a rendered view instead of the source is the split-artifact trap
(gains-lived-in-a-screenshot while EQ-lived-in-.req → a careful reader mis-concluded "no gain
change") that this module exists to kill: one file per snapshot holds crossovers + gains + TA +
polarity + EQ pointers together, so nobody ever reads a partial picture.

Why versioned: the same file that stops drift (write-after-every-change, read-before-edit) is what
makes weird ideas cheap to try — a snapshot is a diff/A-B/revert away, so experimentation costs
one command. Stability and freedom are the same mechanism, not opposites.

Layout
    <root>/<preset>/v_001.json, v_002.json, ...   immutable snapshots
    <root>/<preset>/HEAD                           text file: the current version name

Design invariants
    * ms is the CANONICAL delay unit; samples are DERIVED from the preset's sample_rate at render
      time and never stored. Entering 96 kHz samples into a 48 kHz DSP doubles the physical delay
      and ruins alignment — so the file commits to ms, and samples are a view.
    * status lifecycle (AD-1): proposed -> applied -> measured. The file is the source of truth for
      INTENT + ATTESTED-APPLIED, NOT a guaranteed device mirror; device-truth is the latest
      measurement. The design claims nothing more.
    * snapshot() VALIDATES before writing and refuses on malformed state — a deterministic gate in
      embryo (a confabulated/garbage state can't be silently banked).
    * revert() is forward-only: it writes a NEW snapshot copying an old one, never destroys history.
"""

import argparse
import copy
import datetime
import json
import os
import re

# ── schema ──────────────────────────────────────────────────────────────────
POLARITIES = ("NORM", "INV")
STATUSES = ("proposed", "applied", "measured")
CHANNEL_FIELDS = ("helix_ch", "hp", "lp", "gain_db", "ta_ms", "polarity", "eq_ptr", "status")
TOP_REQUIRED = ("preset", "sample_rate", "channels")
_VER_RE = re.compile(r"^v_(\d{3,})$")


def _validate_filter(name, ch_name, f):
    """A crossover leg is null / "OFF" (disabled) or {f, type, slope}."""
    if f is None or f == "OFF":
        return
    if not isinstance(f, dict) or "f" not in f:
        raise ValueError(f"{ch_name}.{name}: expected null/'OFF' or {{f,type,slope}}, got {f!r}")
    if not isinstance(f["f"], (int, float)) or f["f"] <= 0:
        raise ValueError(f"{ch_name}.{name}.f must be a positive Hz, got {f.get('f')!r}")


def validate(state):
    """Raise ValueError on malformed state; return the state unchanged if OK.

    This is intentionally strict on the things that cause silent, expensive errors (bad polarity,
    a missing crossover, ms not present) and lenient on free-text (note, provenance)."""
    for k in TOP_REQUIRED:
        if k not in state:
            raise ValueError(f"state missing required key {k!r}")
    if not isinstance(state["sample_rate"], (int, float)) or state["sample_rate"] <= 0:
        raise ValueError(f"sample_rate must be a positive Hz, got {state['sample_rate']!r}")
    chans = state["channels"]
    if not isinstance(chans, dict) or not chans:
        raise ValueError("channels must be a non-empty object")
    for ch_name, ch in chans.items():
        missing = [f for f in ("hp", "lp", "gain_db", "ta_ms", "polarity") if f not in ch]
        if missing:
            raise ValueError(f"channel {ch_name!r} missing {missing}")
        _validate_filter("hp", ch_name, ch["hp"])
        _validate_filter("lp", ch_name, ch["lp"])
        if not isinstance(ch["gain_db"], (int, float)):
            raise ValueError(f"{ch_name}.gain_db must be a number, got {ch['gain_db']!r}")
        if not isinstance(ch["ta_ms"], (int, float)):
            raise ValueError(f"{ch_name}.ta_ms must be a number (ms is canonical), got {ch['ta_ms']!r}")
        if ch["polarity"] not in POLARITIES:
            raise ValueError(f"{ch_name}.polarity must be one of {POLARITIES}, got {ch['polarity']!r}")
        st = ch.get("status", "proposed")
        if st not in STATUSES:
            raise ValueError(f"{ch_name}.status must be one of {STATUSES}, got {st!r}")
    return state


def samples_for(ms, sample_rate):
    """Derive DSP samples from canonical ms at the preset's native rate (never stored)."""
    return int(round(ms * sample_rate / 1000.0))


# ── store ─────────────────────────────────────────────────────────────────────
class PresetHistory:
    """Versioned snapshot history for one preset under a project-local root.

    The CODE lives in the skill; the DATA (snapshots) lives in the project — pass `root`
    (e.g. the project's `rew_analitic/state/`) so the same tooling serves any car/project.
    """

    def __init__(self, root, preset):
        self.preset = preset
        self.dir = os.path.join(root, preset)
        os.makedirs(self.dir, exist_ok=True)

    # -- versions --
    def versions(self):
        out = []
        for fn in os.listdir(self.dir):
            m = _VER_RE.match(fn[:-5]) if fn.endswith(".json") else None
            if m:
                out.append(fn[:-5])
        return sorted(out, key=lambda v: int(_VER_RE.match(v).group(1)))

    def _next_version(self):
        vs = self.versions()
        n = (int(_VER_RE.match(vs[-1]).group(1)) + 1) if vs else 1
        return f"v_{n:03d}"

    def _path(self, version):
        return os.path.join(self.dir, version + ".json")

    def _head_path(self):
        return os.path.join(self.dir, "HEAD")

    def head(self):
        hp = self._head_path()
        if os.path.exists(hp):
            with open(hp) as f:
                v = f.read().strip()
            if v in self.versions():
                return v
        vs = self.versions()
        return vs[-1] if vs else None

    def _set_head(self, version):
        with open(self._head_path(), "w") as f:
            f.write(version + "\n")

    # -- read/write --
    def load(self, version=None):
        version = version or self.head()
        if version is None:
            raise FileNotFoundError(f"no snapshots yet for preset {self.preset!r}")
        with open(self._path(version)) as f:
            return json.load(f)

    def snapshot(self, state, note=None):
        """Validate, assign the next version, write it, advance HEAD. Returns the version name."""
        state = copy.deepcopy(state)
        state["preset"] = self.preset
        if note is not None:
            state["note"] = note
        validate(state)
        version = self._next_version()
        state["version"] = version
        state["created"] = datetime.datetime.now().isoformat(timespec="seconds")
        with open(self._path(version), "w") as f:
            json.dump(state, f, indent=2, sort_keys=True, ensure_ascii=False)
        self._set_head(version)
        return version

    def revert(self, version, note=None):
        """Forward-only revert: write a NEW snapshot copying `version`. History is never destroyed."""
        old = self.load(version)
        old.pop("version", None)
        old.pop("created", None)
        note = note or f"revert to {version}"
        return self.snapshot(old, note=note)

    # -- diff --
    def diff(self, va, vb):
        """Structured deltas va -> vb. Returns {'preset': {...}, 'channels': {ch: {field: [old,new]}}}."""
        a, b = self.load(va), self.load(vb)
        return diff_states(a, b)

    def render(self, version=None):
        return render_state(self.load(version))


def _diff_scalar(a, b):
    return None if a == b else [a, b]


def diff_states(a, b):
    """Deltas between two state dicts (pure — no I/O). Only changed fields appear."""
    # `note`/`version`/`created` are per-snapshot labels, not comparable STATE — excluded on purpose.
    out = {"from": a.get("version"), "to": b.get("version"), "preset": {}, "channels": {}}
    for k in ("sample_rate", "target", "roles", "provenance", "virtual_eq_ptr"):
        d = _diff_scalar(a.get(k), b.get(k))
        if d is not None:
            out["preset"][k] = d
    ach, bch = a.get("channels", {}), b.get("channels", {})
    for ch in sorted(set(ach) | set(bch)):
        if ch not in ach:
            out["channels"][ch] = {"__added__": True}
            continue
        if ch not in bch:
            out["channels"][ch] = {"__removed__": True}
            continue
        fields = {}
        for fld in CHANNEL_FIELDS:
            d = _diff_scalar(ach[ch].get(fld), bch[ch].get(fld))
            if d is not None:
                fields[fld] = d
        if fields:
            out["channels"][ch] = fields
    return out


# ── render (generated-only settings sheet) ───────────────────────────────────
def _fmt_filter(f):
    if f is None or f == "OFF":
        return "OFF"
    return f"{f['f']:g} {f.get('type', '?')} {f.get('slope', '?')}"


_STATUS_ICON = {"proposed": "🟡", "applied": "🟢", "measured": "📏"}


def render_state(state):
    """The human-applicable settings sheet, GENERATED from the source of truth.

    Never hand-edit this — edit the JSON and re-render. This is also the artifact the future
    `apply-change` gate hands the Arbiter to read at the PC-Tool screen (channel/param/old→new),
    which is what makes the compliant path the easiest path.
    """
    rate = state["sample_rate"]
    roles = state.get("roles") or {}
    lines = []
    lines.append(f"# DSP settings sheet — {state.get('preset', '?')} · {state.get('version', '(unsaved)')}")
    lines.append("")
    meta = [
        f"target: {state.get('target', '—')}",
        f"sample_rate: {rate:g} Hz (samples derived; ms is canonical)",
        f"roles: artist={roles.get('artist', '—')} · producer={roles.get('producer', '—')} · critic={roles.get('critic', '—')}",
    ]
    prov = state.get("provenance") or {}
    if prov:
        meta.append(f"provenance: {prov.get('decision', prov.get('round', '—'))}")
    if state.get("note"):
        meta.append(f"note: {state['note']}")
    if state.get("created"):
        meta.append(f"created: {state['created']}")
    lines += ["- " + m for m in meta]
    lines.append("")
    lines.append("| Channel | Helix | HP | LP | Pol | TA ms | TA smp | Gain dB | Status | EQ (out / virt) |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for ch_name, ch in state["channels"].items():
        eq = ch.get("eq_ptr") or {}
        eq_s = f"{eq.get('output', '—')} / {eq.get('virtual', '—')}"
        st = ch.get("status", "proposed")
        lines.append(
            f"| {ch_name} | {ch.get('helix_ch', '—')} | {_fmt_filter(ch['hp'])} | {_fmt_filter(ch['lp'])} "
            f"| {ch['polarity']} | {ch['ta_ms']:g} | {samples_for(ch['ta_ms'], rate)} | {ch['gain_db']:g} "
            f"| {_STATUS_ICON.get(st, '?')} {st} | {eq_s} |"
        )
    verdicts = state.get("banked_ear_verdicts") or []
    if verdicts:
        lines += ["", "**Banked ear verdicts:**"] + [f"- {v}" for v in verdicts]
    lines.append("")
    return "\n".join(lines)


def render_diff(d):
    """Compact human view of diff_states() output."""
    lines = [f"# diff {d.get('from')} → {d.get('to')}", ""]
    if d["preset"]:
        lines.append("**Preset-level:**")
        for k, (o, n) in d["preset"].items():
            lines.append(f"- {k}: {o!r} → {n!r}")
        lines.append("")
    if d["channels"]:
        lines.append("**Channels:**")
        for ch, fields in d["channels"].items():
            if fields.get("__added__"):
                lines.append(f"- {ch}: ➕ added")
            elif fields.get("__removed__"):
                lines.append(f"- {ch}: ➖ removed")
            else:
                parts = [f"{fld} {o!r}→{n!r}" for fld, (o, n) in fields.items()]
                lines.append(f"- {ch}: " + " · ".join(parts))
    if not d["preset"] and not d["channels"]:
        lines.append("_(no changes)_")
    return "\n".join(lines) + "\n"


# ── multi-slot registry (issue #5: active-slot integrity) ─────────────────────
class Registry:
    """Which preset (slot) is ACTIVE in the physical DSP right now — the anti-cross-slot-anchoring
    pointer.

    A multi-preset processor (e.g. Helix Slot 1/2/3) invites a degrading model to anchor on the
    WRONG slot's gains: the real incident (issue #5) was tuning Slot 3 (SQ-Comp-Ref) while the top
    of a flat state table showed Slot 2 (ResoNix) numbers, so proposed HF filters were computed off
    a −8.0 dB baseline that belonged to a different slot. Each preset's snapshots already live
    physically isolated under `<root>/<preset>/` (PresetHistory); this registry adds the one missing
    thing — an explicit, machine-checked pointer to the live slot — and `render()` emits a LOUD
    banner so a top-down read hits the active slot first and can't drift to a neighbour's table.
    The apply gate (`apply.py propose`) reads this to REFUSE a change aimed at a non-active slot.
    """

    def __init__(self, root):
        self.root = root
        os.makedirs(root, exist_ok=True)

    def _path(self):
        return os.path.join(self.root, "registry.json")

    def list_presets(self):
        """Preset names that actually have a snapshot history under root (dirs holding v_NNN.json)."""
        out = []
        if os.path.isdir(self.root):
            for name in sorted(os.listdir(self.root)):
                d = os.path.join(self.root, name)
                if os.path.isdir(d) and any(
                        fn.endswith(".json") and _VER_RE.match(fn[:-5]) for fn in os.listdir(d)):
                    out.append(name)
        return out

    def load(self):
        p = self._path()
        if os.path.exists(p):
            with open(p) as f:
                return json.load(f)
        return {"active": None, "slots": {}}

    def _write(self, reg):
        reg["updated"] = datetime.datetime.now().isoformat(timespec="seconds")
        with open(self._path(), "w") as f:
            json.dump(reg, f, indent=2, sort_keys=True, ensure_ascii=False)

    def get_active(self):
        return self.load().get("active")

    def set_active(self, preset):
        """Point the active slot at `preset`. Deterministic guard: it must already have a history."""
        presets = self.list_presets()
        if preset not in presets:
            raise ValueError(f"preset {preset!r} has no snapshot history under {self.root!r} "
                             f"(known: {presets or 'none'}) — seed it (history.snapshot) before "
                             f"making it the active slot")
        reg = self.load()
        reg["active"] = preset
        reg.setdefault("slots", {})
        self._write(reg)
        return preset

    def describe_slot(self, preset, label=None, note=None):
        """Attach an optional human label/desc to a slot (e.g. label='Slot 3', note='SQ-Comp-Ref')."""
        reg = self.load()
        entry = reg.setdefault("slots", {}).setdefault(preset, {})
        if label is not None:
            entry["label"] = label
        if note is not None:
            entry["note"] = note
        self._write(reg)
        return entry

    def render(self):
        return render_registry(self.root, self.load(), self.list_presets())


def render_registry(root, reg, presets):
    """LOUD active-slot banner + one isolated summary row per preset — the generated multi-slot
    `dsp-state-current` view. Generated-only (never hand-edited): a top-down read hits the ACTIVE
    banner first, so it cannot anchor on a neighbour slot's gains (issue #5)."""
    active = reg.get("active")
    slots = reg.get("slots") or {}
    lines = ["# DSP state — multi-slot registry", ""]
    if active:
        lbl = (slots.get(active) or {}).get("label")
        lines.append(f"> ⚠️ **ACTIVE SLOT IN THE DSP:** `{active}`" + (f" — {lbl}" if lbl else ""))
        lines.append("> Read and propose ONLY against this preset's section. The apply gate refuses "
                     "changes aimed at any other slot.")
    else:
        lines.append("> ⚠️ **NO ACTIVE SLOT SET** — run `state.py registry set-active <preset>` "
                     "before proposing any change.")
    lines.append("")
    if not presets:
        return "\n".join(lines + ["_(no presets have a snapshot history yet)_", ""])
    lines += ["| Slot (preset) | Active | HEAD | Target | Key gains (dB) |",
              "|---|---|---|---|---|"]
    for preset in presets:
        h = PresetHistory(root, preset)
        head = h.head()
        s = h.load(head) if head else {}
        chans = s.get("channels", {}) or {}
        gains = " · ".join(f"{c}={chans[c].get('gain_db')}" for c in list(chans)[:4]) if chans else "—"
        lbl = (slots.get(preset) or {}).get("label")
        name = preset + (f" — {lbl}" if lbl else "")
        mark = "✅" if preset == active else ""
        lines.append(f"| {name} | {mark} | {head or '—'} | {s.get('target', '—')} | {gains} |")
    lines.append("")
    return "\n".join(lines)


# ── CLI ───────────────────────────────────────────────────────────────────────
def _main(argv=None):
    p = argparse.ArgumentParser(description="Versioned hard-params DSP state")
    p.add_argument("--root", default=os.environ.get("AUTOSOUND_STATE_ROOT", "state"),
                   help="directory holding <preset>/ snapshots (project-local; env AUTOSOUND_STATE_ROOT)")
    sub = p.add_subparsers(dest="cmd")
    for name in ("log", "render", "revert"):
        sp = sub.add_parser(name)
        sp.add_argument("preset")
        if name in ("render", "revert"):
            sp.add_argument("version", nargs="?", default=None)
    sp = sub.add_parser("diff")
    sp.add_argument("preset")
    sp.add_argument("va")
    sp.add_argument("vb")
    rp = sub.add_parser("registry", help="multi-slot active-slot pointer (issue #5)")
    rp.add_argument("action", choices=["show", "set-active", "render", "describe"])
    rp.add_argument("preset", nargs="?", default=None)
    rp.add_argument("--label", default=None)
    rp.add_argument("--note", default=None)
    sub.add_parser("selftest")
    args = p.parse_args(argv)

    if args.cmd == "selftest" or args.cmd is None:
        return _selftest()
    if args.cmd == "registry":
        reg = Registry(args.root)
        if args.action == "set-active":
            print("active →", reg.set_active(args.preset))
        elif args.action == "describe":
            print(reg.describe_slot(args.preset, label=args.label, note=args.note))
        elif args.action == "render":
            print(reg.render())
        else:  # show
            print(json.dumps(reg.load(), indent=2, ensure_ascii=False))
        return 0
    h = PresetHistory(args.root, args.preset)
    if args.cmd == "log":
        for v in h.versions():
            s = h.load(v)
            head = " (HEAD)" if v == h.head() else ""
            print(f"{v}{head}  {s.get('created', '')}  {s.get('note', '')}")
    elif args.cmd == "render":
        print(h.render(args.version))
    elif args.cmd == "diff":
        print(render_diff(h.diff(args.va, args.vb)))
    elif args.cmd == "revert":
        print("wrote", h.revert(args.version))


# ── self-test ─────────────────────────────────────────────────────────────────
def _sample_state():
    """A minimal Passat-shaped state (grounded in dsp-state-current clean-slate)."""
    return {
        "sample_rate": 96000,
        "target": "Jazzi",
        "roles": {"artist": "Gemini", "producer": "Claude", "critic": None},
        "provenance": {"decision": "clean-slate by-ear 2026-06-18"},
        "banked_ear_verdicts": [],
        "virtual_eq_ptr": None,
        "channels": {
            "sub":  {"helix_ch": "K", "hp": {"f": 20, "type": "BE", "slope": 12},
                     "lp": {"f": 45, "type": "BW", "slope": 12}, "gain_db": -6.0,
                     "ta_ms": 5.0, "polarity": "NORM", "eq_ptr": {}, "status": "applied"},
            "w-L":  {"helix_ch": "C", "hp": {"f": 70, "type": "BW", "slope": 12},
                     "lp": {"f": 270, "type": "BW", "slope": 12}, "gain_db": -7.8,
                     "ta_ms": 5.38, "polarity": "NORM", "eq_ptr": {}, "status": "applied"},
            "tw-R": {"helix_ch": "H", "hp": {"f": 5000, "type": "BE", "slope": 12},
                     "lp": "OFF", "gain_db": -6.0, "ta_ms": 4.09, "polarity": "NORM",
                     "eq_ptr": {}, "status": "applied"},
        },
    }


def _selftest():
    import tempfile
    root = tempfile.mkdtemp(prefix="autosound_state_")
    h = PresetHistory(root, "SQ_Jazzi")

    v1 = h.snapshot(_sample_state(), note="baseline clean-slate")
    assert v1 == "v_001", v1
    assert h.head() == "v_001"

    # ms is canonical; samples derive from 96 kHz (5.38 ms → 516 smp).
    assert samples_for(5.38, 96000) == 516, samples_for(5.38, 96000)
    # the SAME ms on a 48 kHz DSP is half the samples — the hazard the design guards.
    assert samples_for(5.38, 48000) == 258

    # change three things: sub polarity, w-L gain, w-L TA.
    s2 = h.load()
    s2["channels"]["sub"]["polarity"] = "INV"
    s2["channels"]["w-L"]["gain_db"] = -7.5
    s2["channels"]["w-L"]["ta_ms"] = 5.45
    v2 = h.snapshot(s2, note="sub INV test + w-L trim")
    assert v2 == "v_002" and h.head() == "v_002"

    d = h.diff("v_001", "v_002")
    assert d["channels"]["sub"]["polarity"] == ["NORM", "INV"], d
    assert d["channels"]["w-L"]["gain_db"] == [-7.8, -7.5], d
    assert d["channels"]["w-L"]["ta_ms"] == [5.38, 5.45], d
    assert "tw-R" not in d["channels"], "unchanged channel must not appear in the diff"
    assert d["preset"] == {}, d

    # render is generated + carries derived samples and the status icon.
    r = h.render("v_001")
    assert "516" in r and "5.38" in r, r          # derived samples present
    assert "🟢 applied" in r, r
    assert "samples derived; ms is canonical" in r

    # revert is forward-only: v_003 == v_001 content, history intact.
    v3 = h.revert("v_001", note="back to baseline")
    assert v3 == "v_003" and h.head() == "v_003"
    assert h.load("v_003")["channels"]["sub"]["polarity"] == "NORM"
    assert h.versions() == ["v_001", "v_002", "v_003"], h.versions()

    # validation refuses garbage (the gate-in-embryo).
    bad = _sample_state()
    bad["channels"]["w-L"]["polarity"] = "sideways"
    try:
        h.snapshot(bad)
        raise AssertionError("snapshot accepted an invalid polarity")
    except ValueError:
        pass

    # ── multi-slot registry (issue #5): active-slot pointer + LOUD banner ──
    h2 = PresetHistory(root, "ResoNix")
    h2.snapshot(_sample_state(), note="resonix baseline")     # a second slot to disambiguate
    reg = Registry(root)
    assert set(reg.list_presets()) == {"SQ_Jazzi", "ResoNix"}, reg.list_presets()
    try:
        reg.set_active("SQ_Comp_Ref")                          # no history → deterministic refusal
        raise AssertionError("set_active accepted a preset with no history")
    except ValueError:
        pass
    reg.set_active("SQ_Jazzi")
    assert reg.get_active() == "SQ_Jazzi"
    banner = reg.render()
    assert "ACTIVE SLOT IN THE DSP:** `SQ_Jazzi`" in banner, banner
    assert "ResoNix" in banner, "every slot must still be listed (isolated rows)"
    active_row = [ln for ln in banner.splitlines() if ln.startswith("| SQ_Jazzi")][0]
    assert "✅" in active_row, active_row

    print(f"selftest OK — 3 snapshots, diff caught exactly the 3 changes, 5.38 ms → 516 smp @96k "
          f"(258 @48k), revert forward-only (v_001→v_003), validation rejected bad polarity; "
          f"registry: 2 slots isolated, active=SQ_Jazzi loud-bannered, set-active refused a "
          f"history-less slot. root={root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
