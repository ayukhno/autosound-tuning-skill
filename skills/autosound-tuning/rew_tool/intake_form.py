#!/usr/bin/env python3
"""The intake as a FORM the skill serves itself — one page generated from `intake.FIELDS` (S-033).

`intake.py` made Phase −1 readable as data (SCR-059); this module is the other half — the page that
renders it and the small local server that writes the answers back through the method's own writers.
It lives in the skill, not in a front-end, for one reason: the questions must exist ONCE. A window
that carries its own copy of them drifts from the method the first time a field is added, which is
the failure the car package already cost us (hub `#185`), and a terminal session has no window at
all — so `serve` gives it one.

**Round 4 (2026-09-22):** ONE «Зберегти» per page, sending only what changed as one batch; a
a processor change that replaces a saved channel map asks first (round 6: the seat no longer asks;
once written it is shown FIXED, with why, and another seat is a copy of the project); the channel map is drawn by the page's JS from the data it
carries, so it follows a processor change before anything is saved; a NEW processor's base is its
own page (`/new-dsp`); the memo is not rendered.

**What the page is, and is not.** It puts up front only what starting to measure needs
(`intake.WHEN` = `now`), each as a choice where one exists and with the default pre-selected; what a
tool answers and what a later phase asks are folded under a line naming that step — on the page,
not in the way (2026-09-22, `docs/DESIGN-2026-09-22-intake-simplified.md`). It writes the fields
that have a machine home. It does NOT decide the gate: that is `contract.py check --gate`,
and the page prints its verdict. It does not ask what the tool can answer itself — `rew.api_reachable`,
`rew.input_clip_checked` and `dsp.readable` are probes, and a form that asks them asks the person to
do the tool's job (S-030's AUX input is the same class: a check, not a question).

**Colours** are computed, never bookkept: green = answered on disk, red = required and missing,
yellow = optional and missing, grey = the answer lands in prose and a recorded decision, so the form
says so instead of pretending to read it (`intake.missing()`'s third bucket).

**Language.** A session translates the method's English questions as it speaks; a static page cannot,
so the labels ship as DATA — `intake_i18n/<lang>.json`, keyed by field id, falling back to the
English in `FIELDS` for anything a translation has not reached yet. The Arbiter's decision
2026-09-19: Ukrainian first because he proofreads it, the other languages before the release.

Usage:
  python3 rew_tool/intake_form.py serve  <project-dir> [--port N] [--lang uk] [--open]
                                        (routes: / the intake, /new-dsp a new processor's base)

`--lang` is the INTERFACE language, an input: TCC or the skill passes it at start, and both routes
show it. It is also the AI's language, always -- Save writes it to `project.json` `language.reply`,
and the page never asks it (the Arbiter, 2026-09-22). The USER's own language is a separate,
optional field (`language.user`) that switches nothing.
  python3 rew_tool/intake_form.py render <project-dir> [--lang uk] [--page new-dsp] [--out page.html]
  python3 rew_tool/intake_form.py state  <project-dir> [--lang uk] [--json]
  python3 rew_tool/intake_form.py --selftest
"""
from __future__ import annotations

import html
import json
import os
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import dsp_profile  # noqa: E402
import intake  # noqa: E402  -- the question list itself, never a copy of it
import project  # noqa: E402

I18N_DIR = os.path.join(_HERE, "intake_i18n")
DEFAULT_LANG = "uk"

#: What the tool answers instead of asking. Kept here rather than in `intake.FIELDS`, because the
#: field table describes the METHOD's questions; which of them a front-end may probe is the form's
#: business (and the probe itself is not written yet — the page marks them and stays honest).
PROBES = ("rew.api_reachable", "rew.input_clip_checked", "dsp.readable")

#: The four states a field can be in on the page. `prose` is not a gap.
HAVE, GATE, NICE, PROSE = "have", "gate", "nice", "prose"


# ── labels ────────────────────────────────────────────────────────────────────
def labels(lang=DEFAULT_LANG):
    """The translation file for `lang`, or an empty shell when there is none.

    A missing translation is not an error: English is the source and it is always complete, so the
    page falls back field by field and the reader sees which lines are not translated yet.
    """
    path = os.path.join(I18N_DIR, f"{lang}.json")
    if not os.path.isfile(path):
        return {"lang": "en", "ui": {}, "groups": {}, "couplings": {}, "fields": {}}
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    for key in ("ui", "groups", "couplings", "fields"):
        data.setdefault(key, {})
    return data


def _ask(lab, field):
    row = lab["fields"].get(field["id"]) or {}
    return row.get("ask") or field["ask"]


def _options(lab, field):
    """`(value, label)` pairs. A numeric choice is its own label — 96000 needs no translation."""
    row = (lab["fields"].get(field["id"]) or {}).get("enum") or {}
    return [(str(v), row.get(str(v)) or str(v)) for v in (field["enum"] or ())]


def _suggestions(lab, field):
    """`(value, label)` pairs for an OPEN set — offered, never enforced (`intake._f`'s `suggest`)."""
    row = (lab["fields"].get(field["id"]) or {}).get("suggest") or {}
    return [(str(v), row.get(str(v)) or str(v)) for v in (field["suggest"] or ())]


def _derive(lab, field):
    row = lab["fields"].get(field["id"]) or {}
    return row.get("derive") or field["derive"]


def _ui(lab, key, fallback=""):
    return lab["ui"].get(key) or fallback


# ── the model ─────────────────────────────────────────────────────────────────
def _value_of(field, data, project_dir):
    """The answer as it stands on disk, for a field with a single machine home."""
    writes = field["writes"] or ""
    if not writes.startswith("project:") or data is None or "[]" in writes:
        return None
    node = data
    for part in writes.split(":", 1)[1].split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return project.fact_value(node) if project.is_fact(node) else node


def _tier_options(lab, tiers):
    labels_ = (lab["fields"].get("channel_map.tier") or {}).get("suggest") or {}
    return [(t, labels_.get(t) or t) for t in tiers]


def model(project_dir, lang=DEFAULT_LANG):
    """Everything the page renders: fields with their state and current value, tables, the gate."""
    lab = labels(lang)
    buckets = intake.missing(project_dir)
    state = {}
    for row in buckets["answered"]:
        state[row["id"]] = HAVE
    for row in buckets["missing"]:
        state[row["id"]] = GATE if row["required"] else NICE
    for row in buckets["not_machine_readable"]:
        state[row["id"]] = PROSE
    try:
        data = project.Project(project_dir).load()
    except (project.ProjectError, OSError):
        data = None

    # The processor decides which tiers a channel row may name (the Arbiter, 2026-09-22): the
    # tiers it has, narrowed to the ones this car uses once that is answered; every tier for a
    # processor nobody has described yet.
    dsp = intake.dsp_state(project_dir)
    has = dsp["tiers"] or list(intake.SUGGESTED_TIERS)
    used = [t for t in ((data or {}).get("dsp") or {}).get("tiers_used") or [] if t in has]

    fields = []
    for f in intake.FIELDS:
        st = state.get(f["id"], PROSE)
        auto = f["id"] in PROBES or f["derive"] is not None
        # Red means "the next step cannot start without YOU". A default the form pre-selects, a
        # tool's answer, or a step that comes later is owed, but not by the person, and not now.
        if st == GATE and (auto or f["default"] is not None or f["when"] != "now"):
            st = NICE
        default = f["default"]
        if f["id"] == "project.language" and lab.get("lang") in intake.LANGUAGES:
            default = lab["lang"]              # the page's own language is the obvious answer
        options, suggest = _options(lab, f), _suggestions(lab, f)
        if f["id"] == "dsp.tiers_used":
            options = _tier_options(lab, has)
        if f["id"] == "channel_map.tier":
            options, suggest = _tier_options(lab, used or has), []
            default = "channels" if "channels" in (used or has) else None
        if f["id"] == "dsp.tiers":
            options, suggest = _tier_options(lab, intake.SUGGESTED_TIERS), []
        fields.append({
            "id": f["id"], "group": f["group"], "ask": _ask(lab, f), "ask_en": f["ask"],
            "required": f["required"], "multi": f["multi"], "per": f["per"],
            "couple": f["ask_with"], "writes": f["writes"], "lands": f["lands"],
            "options": options, "state": st,
            "value": _value_of(f, data, project_dir), "probe": auto,
            "when": f["when"], "place": f["place"], "default": default, "suggest": suggest,
            "derive": _derive(lab, f) if auto else None,
        })

    gate = intake.gate_requirements(project_dir)
    groups = [{"id": gid, "title": lab["groups"].get(gid) or gid, "why": why}
              for gid, why in intake.GROUPS]
    whens = [{"id": w, "what": what, "title": (lab.get("when") or {}).get(w) or what}
             for w, what in intake.WHEN]
    asked = [f for f in fields if f["place"] in ("now", "goal")]
    now = [f for f in fields if f["place"] == "now"]
    return {
        "project_dir": project_dir, "lang": lab.get("lang", lang), "ui": lab["ui"],
        "when": whens, "dsp": dsp, "dsps": intake.known_dsps(),
        "map": intake.channel_map(project_dir),
        "tiers_used": [t for t in ((data or {}).get("dsp") or {}).get("tiers_used") or []],
        "controls": {k: str(project.fact_value(v)) for k, v in
                     (((data or {}).get("hardware") or {}).get("controls") or {}).items()},
        "car": {**{k: str(v) for k, v in ((data or {}).get("car") or {}).items()
                   if k in ("make", "model", "generation", "body") and v},
                "drive": ((data or {}).get("car") or {}).get("drive_side")},
        "lang_saved": (((data or {}).get("language") or {}).get("reply")),
        "new_dsp": intake.new_dsp_answers(project_dir),
        "cars": intake.known_cars(project_dir),
        "couplings": {c["id"]: {"fields": c["fields"], "why": c["why"],
                                "title": lab["couplings"].get(c["id"]) or c["id"]}
                      for c in intake.couplings()},
        "groups": groups, "fields": fields,
        "rows": {"channels": (data or {}).get("channels") or [],
                 "amps": (data or {}).get("amps") or []},
        "gate": {"open": gate.get("gate_open"), "missing_files": gate.get("missing_files") or [],
                 "command": gate["command"]},
        "totals": {"gate": sum(1 for f in fields if f["state"] == GATE),
                   "nice": sum(1 for f in fields if f["state"] == NICE),
                   "have": sum(1 for f in fields if f["state"] == HAVE),
                   "prose": sum(1 for f in fields if f["state"] == PROSE),
                   "all": len(fields),
                   # What the page puts in front of the person, and how much of it is a choice.
                   "now": len(now),
                   "now_open": sum(1 for f in now if f["state"] != HAVE),
                   "goal": sum(1 for f in fields if f["place"] == "goal"),
                   "asked": len(asked),
                   "asked_choice": sum(1 for f in asked if f["options"] or f["suggest"]),
                   "new_dsp": sum(1 for f in fields if f["place"] == "new_dsp"),
                   "equipment": sum(1 for f in fields if f["place"] == "equipment"),
                   "memo": sum(1 for f in fields if f["place"] == "memo")},
    }


# ── the page ──────────────────────────────────────────────────────────────────
_CSS = """
:root { --have:#1a7f37; --gate:#c0392b; --nice:#b7791f; --prose:#6b7280; --line:#e5e7eb; }
* { box-sizing: border-box; }
body { margin:0; font:15px/1.5 -apple-system, "Segoe UI", system-ui, sans-serif; color:#111;
       background:#fafafa; }
header { padding:18px 24px 10px; background:#fff; border-bottom:1px solid var(--line); }
h1 { margin:0 0 4px; font-size:19px; }
.sub { color:#555; font-size:13px; }
.dir { font-family: ui-monospace, Menlo, monospace; font-size:12px; color:#444; }
.chips { margin:10px 0 0; display:flex; gap:8px; flex-wrap:wrap; align-items:center; }
.chip { border:1px solid var(--line); border-radius:999px; padding:3px 10px; font-size:12px;
        background:#fff; }
.chip b { font-weight:600; }
.dot { display:inline-block; width:9px; height:9px; border-radius:50%; margin-right:6px; }
.d-have{background:var(--have)} .d-gate{background:var(--gate)} .d-nice{background:var(--nice)}
.d-prose{background:var(--prose)}
.gate-ok { color:var(--have); font-weight:600; } .gate-shut { color:var(--gate); font-weight:600; }
main { padding:18px 24px 60px; max-width:1100px; }
h2 { font-size:17px; margin:4px 0 4px; }
h3 { font-size:13px; text-transform:uppercase; letter-spacing:.04em; color:#475569; margin:18px 0 8px; }
details { background:#fff; border:1px solid var(--line); border-radius:10px; padding:8px 14px;
          margin:12px 0 0; }
details > summary { cursor:pointer; color:#374151; font-size:14px; padding:4px 0; }
details[open] > summary { margin-bottom:6px; }
.n { font-size:11px; color:#6b7280; margin-left:5px; border:1px solid var(--line); border-radius:999px;
     padding:0 7px; }
label.opt { display:inline-flex; align-items:center; gap:5px; margin:2px 14px 2px 0; cursor:pointer; }
.hint { color:#1f5fa8; }
.why { color:#555; font-size:13px; margin:0 0 14px; }
.f { background:#fff; border:1px solid var(--line); border-left-width:4px; border-radius:8px;
     padding:11px 13px; margin:0 0 9px; }
.f.s-have{border-left-color:var(--have)} .f.s-gate{border-left-color:var(--gate)}
.f.s-nice{border-left-color:var(--nice)} .f.s-prose{border-left-color:var(--prose)}
.q { font-weight:500; }
.meta { font-size:11.5px; color:#666; margin-top:3px; }
.meta code { font-family: ui-monospace, Menlo, monospace; }
.en { color:#888; font-style:italic; }
.row { display:flex; gap:8px; margin-top:8px; align-items:center; flex-wrap:wrap; }
input[type=text], select { font:inherit; padding:5px 8px; border:1px solid var(--line);
                           border-radius:6px; min-width:230px; background:#fff; }
button.save { font:inherit; font-size:13px; padding:5px 12px; border-radius:6px; border:1px solid #111;
              background:#111; color:#fff; cursor:pointer; }
button.save[disabled] { background:#eee; color:#888; border-color:var(--line); cursor:default; }
.couple { border:1px dashed #cbd5e1; border-radius:10px; padding:10px 12px 4px; margin:0 0 10px;
          background:#fff; }
.couple > .t { font-size:12px; text-transform:uppercase; letter-spacing:.04em; color:#475569;
               margin-bottom:8px; }
.couple .f { border-left-width:4px; box-shadow:none; }
table { border-collapse:collapse; width:100%; background:#fff; font-size:13px; }
th, td { border:1px solid var(--line); padding:5px 7px; text-align:left; vertical-align:top; }
th { background:#f6f6f6; font-weight:600; font-size:12px; }
td input, td select { min-width:90px; width:100%; }
table.drivers th { white-space:normal; min-width:110px; } table.drivers td select { min-width:130px; }
table.drivers td input.wide { min-width:180px; }
.note { background:#fff; border:1px dashed var(--line); border-radius:8px; padding:9px 12px;
        color:#555; font-size:13px; margin:0 0 10px; }
.ok { color:var(--have); font-size:12px; }
.err { color:var(--gate); font-size:12.5px; white-space:pre-wrap; }
[hidden] { display:none !important; }
section { margin:0 0 22px; }
section.goal, section.new-dsp { border-top:1px solid var(--line); padding-top:14px; }
li { margin:3px 0; font-size:13.5px; }
.chanmap details.tier { margin:8px 0 0; padding:4px 10px; }
.chanmap details.tier > summary { text-transform:uppercase; letter-spacing:.05em; color:#475569; font-size:13px; }
.slot { display:flex; align-items:center; gap:8px; padding:4px 0; border-bottom:1px solid #f1f1f1; flex-wrap:wrap; }
.slot .sl { width:26px; color:#555; } .slot .sc { min-width:90px; }
.slot-off .sc { color:#9ca3af; }
.slot input.code, .slot input.slotname { min-width:120px; width:140px; }
button.tog { font:inherit; font-size:12px; font-weight:600; text-transform:uppercase; padding:3px 10px;
             border-radius:6px; background:#fff; cursor:pointer; margin-left:auto; }
.tog-on { color:var(--have); border:1px solid var(--have); } .tog-off { color:#9ca3af; border:1px solid #d1d5db; }
.curve-grid { display:grid; grid-template-columns:repeat(auto-fill, minmax(170px, 1fr)); gap:2px 10px; margin:6px 0; }
.curve-ours { margin:6px 0; font-weight:500; }
textarea { font:inherit; width:100%; max-width:760px; padding:7px 9px; border:1px solid var(--line); border-radius:6px; }
input.num { min-width:70px; width:80px; }
.tier-row { border-top:1px solid #f1f1f1; padding:8px 0; }
.savebar { position:sticky; bottom:0; background:#fff; border-top:1px solid var(--line); padding:10px 24px;
           display:flex; gap:14px; align-items:center; z-index:5; }
button.save.big { font-size:15px; padding:8px 22px; }
.status { font-size:13px; color:#555; white-space:pre-wrap; } .status.err { color:var(--gate); }
section.equipment { border-top:1px solid var(--line); padding-top:14px; }
.knob { display:flex; align-items:center; gap:8px; padding:3px 0; }
.knob .kn { min-width:90px; font-weight:500; } .knob input { min-width:120px; width:160px; }
button.add { font:inherit; font-size:13px; margin-top:6px; padding:3px 10px; border:1px dashed #9ca3af;
             border-radius:6px; background:#fff; cursor:pointer; }
.drive-auto a { color:#1f5fa8; }
.locked .lock { font-size:12px; color:#666; } .locked b { font-weight:600; }
.bad { outline:2px solid var(--gate); outline-offset:2px; border-radius:6px; background:#fff5f5; }
.badmsg { color:var(--gate); font-size:12.5px; margin-top:4px; width:100%; }
"""

#: One JS for both pages. Round 4 (the Arbiter, 2026-09-22): ONE «Зберегти» per page instead of a
#: button on every question. It sends only what CHANGED, in dependency order (the processor before
#: the tiers it offers, the tiers before the slots), through `/save` as one batch. Round 5: a
#: pre-filled value is an ordinary value -- what is on the page is what Save writes. Only a
#: processor change that would replace a saved channel map asks; the write-once seat is shown fixed
#: once written (round 6), so there is nothing to confirm. The reply language is not asked: the page's language is written on Save. The channel map is drawn HERE, from data
#: the page carries, so it follows a processor change live, before anything is saved.
_JS = r"""
const D = JSON.parse(document.getElementById('intake-data').textContent);
const T = D.t || {};
function norm(v) {
  if (Array.isArray(v)) return v.length ? v.slice().sort() : null;
  return v === undefined || v === null || String(v).trim() === '' ? null : String(v).trim();
}
function same(a, b) { return JSON.stringify(a) === JSON.stringify(b); }
function valueOf(box) {
  const multi = box.querySelectorAll('input[type=checkbox]');
  if (multi.length) return [...multi].filter(c => c.checked).map(c => c.value);
  const radios = box.querySelectorAll('input[type=radio]');
  if (radios.length) { const on = [...radios].find(r => r.checked); return on ? on.value : null; }
  const one = box.querySelector('select, input[type=text], textarea');
  return one ? one.value : null;
}
function dirty(unit, now) {
  return !same(now, JSON.parse(unit.dataset.orig || 'null'));
}
function esc(s) {
  return String(s === undefined || s === null ? '' : s).replace(/[&<>"']/g,
    c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

// ── the car picker ──────────────────────────────────────────────────────────
let pickedCar = null;
function pickCar(sel) {
  const o = sel.selectedOptions[0];
  pickedCar = o && o.value !== '' ? {make:o.dataset.make, model:o.dataset.model,
                                      generation:o.dataset.generation, body:o.dataset.body,
                                      drive: o.dataset.drive || null} : null;
  if (pickedCar) document.querySelectorAll('.car-part').forEach(i => {
    if (i.dataset.k in pickedCar) i.value = pickedCar[i.dataset.k]; });
  carEdited();
}
function partsMatch(car) {
  return !!car && [...document.querySelectorAll('.car-part')].every(
    i => !(i.dataset.k in car) || i.dataset.k === 'drive' || (i.value || '').trim() === (car[i.dataset.k] || ''));
}
function carEdited() {
  const hint = document.getElementById('car-new');
  if (hint) hint.hidden = !(pickedCar && !partsMatch(pickedCar));
  syncDrive();
}
// The drive side comes WITH the car (round 5): a picked car that says which side, or the saved car
// the project already records, fills it and the question folds into one line. A new or edited car
// is asked -- with LHD pre-filled, as before.
function syncDrive() {
  const unit = document.querySelector('.unit[data-id="car.drive_side"]');
  if (!unit) return;
  const known = pickedCar && pickedCar.drive && partsMatch(pickedCar) ? pickedCar.drive
              : D.car && D.car.drive && partsMatch(D.car) ? D.car.drive : null;
  const q = unit.querySelector('.drive-q'), auto = unit.querySelector('.drive-auto');
  if (known) {
    const r = unit.querySelector('input[type=radio][value="' + known + '"]');
    if (r) r.checked = true;
    auto.querySelector('b').textContent = r ? r.parentNode.textContent.trim() : known;
  }
  q.hidden = !!known;
  auto.hidden = !known;
}
function askDrive() {
  const unit = document.querySelector('.unit[data-id="car.drive_side"]');
  unit.querySelector('.drive-q').hidden = false;
  unit.querySelector('.drive-auto').hidden = true;
}
function carValue() {
  const out = {};
  document.querySelectorAll('.car-part').forEach(i => { out[i.dataset.k] = norm(i.value); });
  return out;
}

// ── the processor: vendor, then only that vendor's models ───────────────────
// Models are REMOVED and re-added, never hidden: Safari ignores `hidden` on an <option>.
let allModels = null;
function filterModels(vendor) {
  const model = document.getElementById('dsp-model');
  if (!model) return;
  if (allModels === null) allModels = [...model.querySelectorAll('option[data-vendor]')];
  const keep = model.value;
  allModels.forEach(o => o.remove());
  const other = model.querySelector('option[value=__other__]');
  allModels.filter(o => o.dataset.vendor === vendor).forEach(o => model.insertBefore(o, other));
  model.value = [...model.options].some(o => o.value === keep) ? keep : '';
}
function dspIdentity() {
  const v = document.getElementById('dsp-vendor'), m = document.getElementById('dsp-model');
  if (!v || !m) return {vendor: D.saved.vendor || '', model: D.saved.model || ''};
  const vendor = v.value === '__other__' ? document.getElementById('dsp-vendor-free').value : v.value;
  const model = m.value === '__other__' ? document.getElementById('dsp-model-free').value : m.value;
  return {vendor: (vendor || '').trim(), model: (model || '').trim()};
}
function pickVendor(sel) {
  const other = sel.value === '__other__';
  document.getElementById('dsp-vendor-free').hidden = !other;
  filterModels(sel.value);
  const model = document.getElementById('dsp-model');
  model.value = other ? '__other__' : '';
  pickModel(model);
}
function pickModel(sel) {
  document.getElementById('dsp-model-free').hidden = sel.value !== '__other__';
  redraw();
}
function sameDsp(a, b) {
  return a.vendor.toLowerCase() === (b.vendor || '').toLowerCase()
      && a.model.toLowerCase() === (b.model || '').toLowerCase();
}
// What the map is drawn from: the SAVED processor's tiers and rows, or -- once another one is
// picked -- THAT processor's tiers and no rows. Slots are never carried across processors.
function mapSource() {
  const id = dspIdentity();
  if (!id.vendor || !id.model) return {state: 'none'};
  if (sameDsp(id, D.saved)) {
    if (D.saved.groups.length) return {state: 'ok', groups: D.saved.groups, chans: D.saved.channels, same: true};
    return {state: D.saved.new ? 'new' : 'none'};
  }
  const e = D.dsps.find(d => sameDsp(id, d));
  if (e) return {state: 'ok', groups: e.groups, chans: [], same: false};
  return {state: 'new-unsaved'};
}

// ── tiers in use, redrawn for the processor on the page ─────────────────────
let lastKey = null;
function redrawTiers(src) {
  const unit = document.getElementById('tiers-unit');
  if (!unit) return;
  const key = JSON.stringify(dspIdentity());
  if (key === lastKey) return;
  const first = lastKey === null;
  lastKey = key;
  edits = {};
  if (first) return;                       // the server drew the saved processor's tiers
  const groups = src.state === 'ok' ? src.groups : [];
  const keep = src.same ? D.saved.tiers_used : [];
  unit.querySelector('.choices').innerHTML = groups.map(g =>
      '<label class="opt"><input type="checkbox" value="' + esc(g.tier) + '"'
      + (keep.includes(g.tier) ? ' checked' : '') + ' onchange="redrawMap()"> '
      + esc((T.tier_names || {})[g.tier] || g.label) + '</label>').join('');
}

// ── the channel map (TCC's table): one fold per tier, used/total, a row per slot ──
let edits = {};
function offCode(tier, slot) { return (D.off_prefix[tier] || ('off-' + tier)) + '-' + slot; }
function tiersChecked() {
  const unit = document.getElementById('tiers-unit');
  return unit ? [...unit.querySelectorAll('.choices input[type=checkbox]')].filter(c => c.checked).map(c => c.value) : [];
}
function redrawMap() {
  const body = document.getElementById('chanmap-body');
  if (!body) return;
  const src = mapSource();
  const note = document.getElementById('chanmap-note');
  const link = document.getElementById('newdsp-link');
  if (link) link.hidden = !((src.state === 'new' || src.state === 'ok') && src.same !== false && D.saved.new);
  const pending = document.getElementById('newdsp-pending');
  if (pending) pending.hidden = src.state !== 'new-unsaved';
  if (src.state !== 'ok') {
    body.innerHTML = '';
    note.textContent = src.state === 'new' ? T.map_new : src.state === 'new-unsaved' ? T.map_new_unsaved : T.map_first;
    note.hidden = false;
    return;
  }
  const replacing = !src.same && D.saved.slotted > 0;
  note.hidden = !replacing;
  if (replacing) note.textContent = T.map_replaced.replace('{old}', D.saved.vendor + ' ' + D.saved.model)
                                                  .replace('{n}', D.saved.slotted);
  const used = tiersChecked();
  const groups = src.groups.filter(g => used.length ? used.includes(g.tier) : g.in_scope);
  body.innerHTML = groups.map(g => {
    const mine = src.chans.filter(c => c.tier === g.tier);
    const slots = g.slots.length ? g.slots : mine.map(c => c.slot);
    const rows = slots.map(slot => {
      const c = mine.find(x => String(x.slot) === String(slot)) || {};
      const origOn = !!c.code && !c.hidden && c.role !== 'unused';
      const e = edits[g.tier + '|' + slot] || {};
      const on = 'on' in e ? e.on : origOn;
      const code = 'code' in e ? e.code : (origOn ? c.code : '');
      return '<div class="slot' + (on ? '' : ' slot-off') + '" data-tier="' + esc(g.tier) + '" data-slot="' + esc(slot)
        + '" data-orig-on="' + (origOn ? 1 : 0) + '" data-orig-code="' + esc(origOn ? c.code : '') + '" data-on="' + (on ? 1 : 0) + '">'
        + '<span class="sl">' + esc(slot) + ' ·</span><span class="sc">' + esc(on ? code : (c.code || offCode(g.tier, slot))) + '</span>'
        + '<input type="text" class="code" list="codes-' + esc(g.tier) + '" value="' + esc(code)
        + '" placeholder="' + esc(T.code_pick) + '" oninput="codeEdited(this)">'
        + '<button type="button" class="tog ' + (on ? 'tog-off' : 'tog-on') + '" onclick="toggleSlot(this)">'
        + esc(on ? T.chan_off : T.chan_on) + '</button></div>';
    }).join('');
    return '<details class="tier" open><summary>' + esc((T.tier_names || {})[g.tier] || g.label)
      + ' <b class="usedtotal"></b></summary>' + rows + '</details>';
  }).join('');
  recount();
}
function recount() {
  document.querySelectorAll('#chanmap-body details.tier').forEach(d => {
    const rows = [...d.querySelectorAll('.slot')];
    d.querySelector('.usedtotal').textContent = rows.filter(r => r.dataset.on === '1').length + '/' + rows.length;
  });
}
function codeEdited(input) {
  const row = input.closest('.slot');
  const key = row.dataset.tier + '|' + row.dataset.slot;
  const code = input.value.trim();
  edits[key] = Object.assign(edits[key] || {}, {code});
  // A code typed into a switched-off slot means the slot is used: switch it on. Without this a
  // typed code stayed off, Save found nothing changed, and "Зберегти" looked broken (22.09).
  if (code && row.dataset.on !== '1') { toggleSlot(row.querySelector('button.tog')); return; }
  if (row.dataset.on === '1') row.querySelector('.sc').textContent = code;
}
function toggleSlot(btn) {
  const row = btn.closest('.slot');
  const input = row.querySelector('input.code');
  const on = row.dataset.on !== '1';
  if (on && !input.value.trim()) { input.focus(); input.placeholder = T.code_needed; return; }
  const key = row.dataset.tier + '|' + row.dataset.slot;
  edits[key] = Object.assign(edits[key] || {}, {on, code: input.value.trim()});
  row.dataset.on = on ? '1' : '0';
  row.classList.toggle('slot-off', !on);
  row.querySelector('.sc').textContent = on ? input.value.trim() : offCode(row.dataset.tier, row.dataset.slot);
  btn.textContent = on ? T.chan_off : T.chan_on;
  btn.className = 'tog ' + (on ? 'tog-off' : 'tog-on');
  recount();
}
// ── knobs outside the DSP: the chosen processor's own remote knobs, plus any added by name ──
function redrawKnobs() {
  const box = document.getElementById('knob-rows');
  if (!box) return;
  const id = dspIdentity();
  const entry = sameDsp(id, D.saved) ? {knobs: D.saved.knobs} : (D.dsps.find(d => sameDsp(id, d)) || {knobs: []});
  // A processor's own knobs follow the processor; a row the person ADDED (a head unit's bass
  // knob) is not the processor's, so it survives the change, typed values and all.
  const typed = {}, custom = [...box.querySelectorAll('.knob')].filter(r => r.querySelector('input.kname'));
  [...box.querySelectorAll('.knob')].filter(r => !r.querySelector('input.kname')).forEach(r => {
    typed[r.dataset.name] = r.querySelector('input.kpos').value; });
  const names = [...new Set([...(entry.knobs || []), ...Object.keys(D.controls)])];
  box.innerHTML = names.map(n => knobRow(n, n in typed ? typed[n] : (D.controls[n] || ''), D.controls[n] || '')).join('');
  custom.forEach(r => box.appendChild(r));
}
function knobRow(name, pos, orig) {
  return '<div class="knob" data-name="' + esc(name) + '" data-orig="' + esc(orig) + '"><span class="kn">' + esc(name)
    + '</span> — <input type="text" class="kpos" value="' + esc(pos) + '" placeholder="' + esc(T.knob_pos) + '"></div>';
}
function addKnob() {
  const box = document.getElementById('knob-rows');
  const row = document.createElement('div');
  row.className = 'knob';
  row.innerHTML = '<input type="text" class="kname" placeholder="' + esc(T.knob_name) + '"> — '
    + '<input type="text" class="kpos" placeholder="' + esc(T.knob_pos) + '">';
  box.appendChild(row);
  row.querySelector('input.kname').focus();
}
function redraw() { const src = mapSource(); redrawTiers(src); redrawMap(); redrawKnobs(); }

// ── one Save: collect what changed, in the order the writers need it ────────
// Each item remembers the element it came from (non-enumerable, so it is not sent): a refusal is
// shown AT that element, not in a line under the button.
function at(item, el) { Object.defineProperty(item, '_el', {value: el || null}); return item; }
function slotItems(dspId) {
  // Offs first (they free codes), then MOVES (the same code off in one slot and on in another: the
  // wire moved, one write keeps the channel's history), then the rest.
  const offs = [], ons = [];
  document.querySelectorAll('#chanmap-body .slot').forEach(r => {
    const on = r.dataset.on === '1', code = r.querySelector('input.code').value.trim();
    if (on === (r.dataset.origOn === '1') && (!on || code === r.dataset.origCode)) return;
    const item = at({slot: {tier: r.dataset.tier, slot: r.dataset.slot, code, on, dsp: dspId}}, r);
    (on ? ons : offs).push(item);
  });
  const moves = [];
  ons.slice().forEach(o => {
    const s = o.slot;
    const k = offs.findIndex(f => f.slot.tier === s.tier && f._el.dataset.origCode === s.code);
    if (k < 0) return;
    const [left] = offs.splice(k, 1);
    ons.splice(ons.indexOf(o), 1);
    moves.push(at({slot: Object.assign({}, s, {move_from: left.slot.slot})}, o._el));
  });
  return [...offs, ...moves, ...ons];
}
function collect() {
  const out = [], asks = [], late = [];
  // The AI's language IS the interface language (the Arbiter, 2026-09-22): the page's own
  // `--lang`, written on Save from either page, never asked.
  if (D.lang && D.lang !== D.lang_saved) out.push(at({field: 'project.language', value: D.lang}));
  const ul = document.querySelector('.unit[data-kind=userlang]');
  if (ul) {
    const sel = ul.querySelector('select').value;
    const v = norm(sel === '__other__' ? ul.querySelector('input').value : sel);
    if (v !== null && dirty(ul, v)) out.push(at({field: 'project.user_language', value: v}, ul));
  }
  const car = document.querySelector('.unit[data-kind=car]');
  if (car && dirty(car, carValue()) && Object.values(carValue()).some(v => v)) out.push(at({car: carValue()}, car));
  document.querySelectorAll('.unit[data-kind=field]').forEach(u => {
    const v = norm(valueOf(u));
    if (v === null || !dirty(u, v)) return;
    (u.dataset.id === 'dsp.tiers_used' ? late : out).push(at({field: u.dataset.id, value: v}, u));
  });
  const id = dspIdentity();
  const dspBox = document.querySelector('.unit[data-kind=dsp]');
  if (dspBox && id.vendor && id.model && !sameDsp(id, D.saved)) {
    const replace = D.saved.slotted > 0 && !!(D.saved.vendor || D.saved.model);
    if (replace) asks.push({kind: 'dsp', from: D.saved.vendor + ' ' + D.saved.model, to: id.vendor + ' ' + id.model});
    out.push(at({dsp: {vendor: id.vendor, model: id.model, replace_map: replace}}, dspBox));
  }
  out.push(...late);
  out.push(...slotItems([id.vendor, id.model]));
  const goal = document.querySelector('.unit[data-kind=goal]');
  if (goal) {
    const v = {choices: [...goal.querySelectorAll('.goal-pick')].filter(c => c.checked).map(c => c.value).sort(),
               text: norm(document.getElementById('goal-text').value)};
    if (dirty(goal, v)) out.push(at({goal: v}, goal));
  }
  const curve = document.querySelector('.unit[data-kind=curve]');
  if (curve) {
    const on = [...curve.querySelectorAll('input[name=curve]')].find(r => r.checked);
    const own = document.getElementById('curve-own').value.trim();
    const v = norm(!on ? '' : on.value === '__own__' ? own : on.value);
    if (v !== null && dirty(curve, v)) out.push(at({field: 'target_curve.candidate', value: v}, curve));
  }
  document.querySelectorAll('tr.unit[data-kind=chanrow]').forEach(tr => {
    const v = {};
    tr.querySelectorAll('input, select').forEach(i => { if (i.dataset.k) v[i.dataset.k] = norm(i.value); });
    if (!dirty(tr, v)) return;
    const row = {};
    Object.entries(v).forEach(([k, x]) => { if (x !== null) row[k] = x; });
    out.push(at({channel: row}, tr));
  });
  const knobs = {};
  document.querySelectorAll('#knobs .knob').forEach(r => {
    const nameIn = r.querySelector('input.kname');
    const name = nameIn ? nameIn.value.trim() : r.dataset.name;
    const pos = r.querySelector('input.kpos').value.trim();
    if (name && pos && pos !== (r.dataset.orig || '')) knobs[name] = pos;
  });
  if (Object.keys(knobs).length) out.push(at({controls: knobs}, document.getElementById('knobs')));
  const nd = document.getElementById('newdsp-form');
  if (nd) out.push(at({new_dsp: newDspValue(nd)}, nd));
  return {out, asks};
}

// ── what is wrong is shown AT the field, in red, and the page scrolls to the first one ─────────
function clearBad() {
  document.querySelectorAll('.bad').forEach(e => e.classList.remove('bad'));
  document.querySelectorAll('.badmsg').forEach(e => e.remove());
}
function markBad(el, text) {
  if (!el) return null;
  el.classList.add('bad');
  if (text) {
    const m = document.createElement('div');
    m.className = 'badmsg';
    m.textContent = text;
    el.appendChild(m);
  }
  return el;
}
function showFirst(els) {
  const first = els.find(Boolean);
  if (!first) return;
  const d = first.closest('details');
  if (d) d.open = true;
  first.scrollIntoView({behavior: 'smooth', block: 'center'});
  const f = first.querySelector('input:not([type=hidden]), select, textarea');
  if (f) setTimeout(() => f.focus({preventScroll: true}), 350);
}
function invalid() {
  // Values the writers would refuse, caught before anything is sent: a switched-on slot with no
  // code, and one code on two slots ("one code, one channel").
  const bad = [], seen = {};
  document.querySelectorAll('#chanmap-body .slot').forEach(r => {
    if (r.dataset.on !== '1') return;
    const code = r.querySelector('input.code').value.trim();
    if (!code) { bad.push(markBad(r, T.err_no_code)); return; }
    if (seen[code]) {
      bad.push(markBad(r, T.err_dup_code.replace('{code}', code).replace('{slot}', seen[code].dataset.slot)));
      if (!seen[code].classList.contains('bad')) markBad(seen[code]);
    } else seen[code] = r;
  });
  return bad;
}
function missingRequired() {
  const out = [];
  document.querySelectorAll('.unit[data-required="1"]').forEach(u => {
    const v = u.dataset.kind === 'dsp' ? (dspIdentity().vendor && dspIdentity().model ? 'x' : null) : norm(valueOf(u));
    if (v === null) out.push(markBad(u, T.err_required));
  });
  return out;
}
function newDspValue(form) {
  const num = n => { const i = form.querySelector('[name="' + n + '"]'); return i ? norm(i.value) : null; };
  const ticks = n => [...form.querySelectorAll('input[name="' + n + '"]:checked')].map(c => c.value);
  const pick = n => { const r = form.querySelector('input[name="' + n + '"]:checked'); return r ? r.value : null; };
  const yn = n => { const v = pick(n); return v === 'yes' ? true : v === 'no' ? false : null; };
  const tiers = {};
  form.querySelectorAll('.tier-row').forEach(r => {
    const t = r.dataset.tier;
    if (!r.querySelector('input.has').checked) return;
    tiers[t] = {count: num('count-' + t), letters: pick('style-' + t) !== 'number', fields: ticks('fields-' + t)};
  });
  return {tiers, rate: num('rate'),
          eq: {bands: num('eq-bands'), types: ticks('eq-types'), file_import: yn('eq-file')},
          crossover: {types: ticks('xo-types'), slopes: ticks('xo-slopes').map(Number), independent: yn('xo-indep')},
          delay: {step_ms: num('delay-step'), max_ms: num('delay-max')},
          presets: {count: num('presets-count'), input_switches: yn('presets-input')}};
}
async function saveAll(btn) {
  const status = document.getElementById('save-status');
  status.className = 'status'; status.textContent = '';
  clearBad();
  const wrong = invalid();
  if (wrong.length) {
    status.className = 'status err';
    status.textContent = T.err_fix_first;
    showFirst(wrong);
    return;
  }
  const {out, asks} = collect();
  if (!out.length) {
    const gaps = missingRequired();
    status.textContent = gaps.length ? T.err_still_missing.replace('{n}', gaps.length) : T.nothing_changed;
    showFirst(gaps);
    return;
  }
  for (const a of asks) {
    const text = T.dsp_confirm.replace('{old}', a.from).replace('{new}', a.to).replace('{n}', D.saved.slotted);
    if (!confirm(text)) { status.textContent = T.save_cancelled; return; }
  }
  btn.disabled = true;
  try {
    const r = await fetch('save', {method: 'POST', headers: {'Content-Type': 'application/json'},
                                   body: JSON.stringify({batch: out})});
    const res = await r.json();
    if (!r.ok) throw new Error(res.error || r.statusText);
    if (res.errors && res.errors.length) {
      // What was refused is shown at its own field; what went through is on disk already.
      const els = res.errors.map(e => markBad((out[e.index] || {})._el, T.err_refused + ' ' + e.error));
      const loose = res.errors.filter((e, i) => !els[i]).map(e => e.error);
      status.className = 'status err';
      status.textContent = T.err_some_refused.replace('{n}', res.errors.length)
        + (loose.length ? '\n' + loose.join('\n') : '');
      btn.disabled = false;
      showFirst(els);
      return;
    }
    // Reload to show what is on disk; `#saved` asks the reloaded page to point at what is still owed.
    if (btn.dataset.after) location.href = btn.dataset.after;
    else { location.hash = 'saved'; location.reload(); }
  } catch (e) {
    status.className = 'status err';
    status.textContent = String(e.message || e);
    btn.disabled = false;
  }
}
window.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.car-part').forEach(i => i.addEventListener('input', carEdited));
  const own = document.getElementById('curve-own');
  if (own) own.addEventListener('input', () => {
    const r = document.querySelector('input[name=curve][value=__own__]'); if (r) r.checked = true; });
  const v = document.getElementById('dsp-vendor'); if (v) filterModels(v.value);
  const tiers = document.getElementById('tiers-unit');
  if (tiers) tiers.querySelectorAll('.choices input[type=checkbox]').forEach(c => c.addEventListener('change', redrawMap));
  redraw();
  syncDrive();
  // A field fixed by hand stops being red at once.
  document.addEventListener('input', e => {
    const b = e.target.closest('.bad');
    if (b) { b.classList.remove('bad'); b.querySelectorAll('.badmsg').forEach(m => m.remove()); }
  });
  if (location.hash === '#saved') {
    history.replaceState(null, '', location.pathname + location.search);
    const status = document.getElementById('save-status');
    const gaps = missingRequired();
    if (status) status.textContent = gaps.length ? T.saved_missing.replace('{n}', gaps.length) : T.saved_ok;
    showFirst(gaps);
  }
});
"""


def _esc(text):
    return html.escape("" if text is None else str(text), quote=True)


#: Up to this many choices are shown as radio buttons — all of them visible at once; more is a list.
RADIO_MAX = 6


def _orig(value):
    """The value a unit started with, in the shape the page's `norm()` produces — so "changed" is
    a comparison of like with like (a list sorted, a blank as null, a number as text)."""
    if isinstance(value, (list, tuple)):
        return json.dumps(sorted(str(v) for v in value) or None)
    if value is None or str(value).strip() == "":
        return "null"
    return json.dumps(str(value).strip())


def _choice(f, value, ui, cls="", key=""):
    """The control for one answer: radios, a list, checkboxes, a text box with suggestions."""
    data = f' data-k="{_esc(key)}"' if key else ""
    klass = f' class="{cls}"' if cls else ""
    if isinstance(value, (list, tuple)):
        chosen = [str(v) for v in value]
        value = ",".join(chosen)
    else:
        chosen = str(value).split(",") if value not in (None, "") else []
    current = value if value not in (None, "") else ("" if f["default"] is None else str(f["default"]))
    if f["options"] and f["multi"]:
        return '<div class="choices">' + "".join(
            f'<label class="opt"><input type="checkbox" value="{_esc(v)}"'
            f'{" checked" if v in chosen else ""}> {_esc(t)}</label>' for v, t in f["options"]) + "</div>"
    if f["options"] and len(f["options"]) <= RADIO_MAX and not key:
        name = f'r-{f["id"]}'
        return "<div>" + "".join(
            f'<label class="opt"><input type="radio" name="{_esc(name)}" value="{_esc(v)}"{klass}{data}'
            f'{" checked" if current == v else ""}> {_esc(t)}</label>' for v, t in f["options"]) + "</div>"
    if f["options"]:
        opts = "".join(f'<option value="{_esc(v)}"{" selected" if current == v else ""}>{_esc(t)}</option>'
                       for v, t in f["options"])
        return f'<select{klass}{data}><option value="">—</option>{opts}</select>'
    if f["id"] == "hardware.description":
        return (f'<textarea rows="5"{klass}{data} placeholder="{_esc(ui.get("equipment_ph", ""))}">'
                f'{_esc(value or "")}</textarea>')
    listed = ""
    if f["suggest"]:
        dl = f'dl-{f["id"]}'
        listed = (f' list="{_esc(dl)}" placeholder="{_esc(ui.get("pick_or_type", "pick or type"))}"'
                  f'><datalist id="{_esc(dl)}">'
                  + "".join(f'<option value="{_esc(v)}">{_esc(t)}</option>' if t != v
                            else f'<option value="{_esc(v)}">' for v, t in f["suggest"])
                  + "</datalist")
    return f'<input type="text"{klass}{data} value="{_esc(value or "")}"{listed}>'


#: Fields that are written ONCE and then fixed, each with the ui key that says why and what to do
#: instead. The seat is what the project IS (S-032): another seat is a copy of the project, where
#: the seat is chosen again (`project_seed.py --seat`).
LOCKED_ONCE_SET = {"goal.reference_seat": "seat_locked"}


def _field_html(f, ui):
    """One question as a UNIT the page's single Save reads: its control, and what it started as."""
    mark = (f' <span class="meta">({_esc(ui.get("required", "required"))})</span>'
            if f["required"] and f["place"] == "now" else "")
    writes = f["writes"] or ""
    if writes.startswith("glossary:") or writes.startswith("dsp_profile.draft:") or f["per"] or not writes:
        note = ui.get("glossary_note", "") if writes.startswith("glossary:") else ""
        return (f'<div class="f s-{f["state"]}" id="f-{_esc(f["id"])}">'
                f'<div class="q"><span class="dot d-{f["state"]}"></span>{_esc(f["ask"])}{mark}</div>'
                f'<div class="meta">{_esc(note)}</div></div>')
    if f["id"] in LOCKED_ONCE_SET and f["value"] not in (None, ""):
        # Fixed once written (the Arbiter, 2026-09-22): not offered as a control at all, and the
        # page says why and what to do instead -- rather than letting a Save be refused.
        label = dict(f["options"] or []).get(f["value"], f["value"])
        return (f'<div class="f s-have locked" id="f-{_esc(f["id"])}">'
                f'<div class="q"><span class="dot d-have"></span>{_esc(f["ask"])}</div>'
                f'<div class="row"><b>{_esc(label)}</b> <span class="lock">· {_esc(ui.get("fixed", "fixed"))}</span></div>'
                f'<div class="meta">{_esc(ui.get(LOCKED_ONCE_SET[f["id"]], ""))}</div></div>')
    # `data-orig` is what is ON DISK, not what is shown: a pre-filled value that is not stored yet
    # is a change like any other, and Save writes it (round 5 -- no confirm ticks).
    unit_id = ' id="tiers-unit"' if f["id"] == "dsp.tiers_used" else ""
    control = f'<div class="row">{_choice(f, f["value"], ui)}</div>'
    if f["id"] == "car.drive_side":
        # Filled from the car when the car says it; asked only for a new or edited car.
        control = (f'<div class="drive-q">{control}</div>'
                   f'<div class="drive-auto meta hint" hidden>{_esc(ui.get("drive_from_car", "from the car"))}: '
                   f'<b></b> · <a href="#" onclick="askDrive(); return false">{_esc(ui.get("change", "change"))}</a></div>')
    req = ' data-required="1"' if mark else ""
    if f["id"] in LOCKED_ONCE_SET:
        control += f'<div class="meta">{_esc(ui.get("seat_once", ""))}</div>'
    return (f'<div class="f unit s-{f["state"]}" data-kind="field" data-id="{_esc(f["id"])}"{req} '
            f"data-orig='{_esc(_orig(f['value']))}'{unit_id}>"
            f'<span id="f-{_esc(f["id"])}"></span>'
            f'<div class="q"><span class="dot d-{f["state"]}"></span>{_esc(f["ask"])}{mark}</div>'
            f'{control}</div>')


#: The page's own refusals (round 6), in English for a language whose file lacks them.
_ERR_EN = {
    "err_no_code": "a switched-on slot needs its code",
    "err_dup_code": "the code {code} is already on slot {slot} — one code, one channel",
    "err_required": "required",
    "err_fix_first": "Nothing was saved: fix what is marked red.",
    "err_still_missing": "Nothing new to save. Still to fill in: {n} — marked red.",
    "err_refused": "Not saved:",
    "err_some_refused": "Saved, except {n} — marked red.",
    "saved_ok": "Saved.",
    "saved_missing": "Saved. Still to fill in: {n} — marked red.",
}


CAR_PARTS = (("make", "car.make"), ("model", "car.model"), ("generation", "car.generation"),
             ("body", "car.body"), ("year", "car.year"))


def _car_block(m, fields):
    """The car: pick a known one to fill the four parts, or type them. Four parts or nothing.

    The list is what the skill has SEEN — its cabin library and the projects next to this one
    (`intake.known_cars`); there is no catalogue beyond that and none is invented. A picked car can
    still be edited, and an edited car is a NEW car: the page says so the moment a part differs.
    """
    ui = m["ui"]
    src_label = {"library": ui.get("car_src_library", "skill library")}
    pick = ""
    if m["cars"]:
        opts = "".join(
            f'<option value="{i}" data-make="{_esc(c["make"])}" data-model="{_esc(c["model"])}" '
            f'data-generation="{_esc(c["generation"])}" data-body="{_esc(c["body"])}" '
            f'data-drive="{_esc(c.get("drive_side") or "")}">'
            f'{_esc(c["label"])} · {_esc(src_label.get(c["source"]) or c["source"].replace("project:", ui.get("car_src_project", "project") + " "))}'
            f'</option>' for i, c in enumerate(m["cars"]))
        pick = (f'<div class="f" id="car-pick-box"><div class="q">{_esc(ui.get("car_pick", "Pick a known car"))}</div>'
                f'<div class="row"><select id="car-pick" onchange="pickCar(this)">'
                f'<option value="">{_esc(ui.get("car_pick_none", "— type it below —"))}</option>{opts}</select></div>'
                f'<div class="meta">{_esc(ui.get("car_pick_src", ""))}</div>'
                f'<div class="meta hint" id="car-new" hidden>{_esc(ui.get("car_edited", "edited: this is a new car"))}</div></div>')
    inputs, orig = [], {}
    for key, fid in CAR_PARTS:
        f = next((x for x in fields if x["id"] == fid), None)
        if not f:
            continue
        value = "" if f["value"] is None else str(f["value"])
        orig[key] = value.strip() or None
        inputs.append(f'<div class="f s-{f["state"]}" id="f-{_esc(fid)}"><div class="q">'
                      f'<span class="dot d-{f["state"]}"></span>{_esc(f["ask"])}</div>'
                      f'<div class="row">{_choice(f, value, ui, cls="car-part", key=key)}</div></div>')
    couple = m["couplings"].get("car_identity", {})
    return (f"<div class=\"couple unit\" data-kind=\"car\" data-orig='{_esc(json.dumps(orig))}'>"
            f'<div class="t">{_esc(couple.get("title", "car"))}</div>{pick}' + "".join(inputs) + "</div>")


def _dsp_block(m, fields):
    """Vendor, then model — the models offered are ONLY that vendor's (round 2).

    Picking another processor redraws the channel map below at once, from that processor's own
    tiers and slot counts (round 4). A processor the library does not describe is NEW: its base is
    asked on its own page (`/new-dsp`), and the map appears once that base exists.
    """
    ui = m["ui"]
    dsp = m["dsp"]
    vendors = sorted({d["vendor"] for d in m["dsps"]})
    other = "__other__"
    known_pair = any(d["vendor"] == dsp["vendor"] and d["model"] == dsp["model"] for d in m["dsps"])
    v_sel = dsp["vendor"] if dsp["vendor"] in vendors else (other if dsp["vendor"] else "")
    m_sel = dsp["model"] if known_pair else (other if dsp["model"] else "")
    v_opts = "".join(f'<option value="{_esc(v)}"{" selected" if v == v_sel else ""}>{_esc(v)}</option>'
                     for v in vendors)
    m_opts = "".join(f'<option value="{_esc(d["model"])}" data-vendor="{_esc(d["vendor"])}"'
                     f'{" selected" if d["model"] == m_sel and d["vendor"] == v_sel else ""}'
                     f'>{_esc(d["model"])}</option>' for d in m["dsps"])
    free_v = "" if v_sel != other else dsp["vendor"]
    free_m = "" if m_sel != other else dsp["model"]
    ids = "".join(f'<span id="f-{fid}"></span>' for fid in ("dsp.vendor", "dsp.model"))
    state = "have" if dsp["vendor"] and dsp["model"] else "gate"
    ask = {f["id"]: f["ask"] for f in fields}
    return (f'<div class="couple unit" data-kind="dsp" data-required="1" id="dsp-box">{ids}'
            f'<div class="t">{_esc(m["couplings"]["dsp_identity"]["title"])}</div>'
            f'<div class="f s-{state}"><div class="q"><span class="dot d-{state}"></span>'
            f'{_esc(ask["dsp.vendor"])} <span class="meta">({_esc(ui.get("required", "required"))})</span></div>'
            f'<div class="row"><select id="dsp-vendor" onchange="pickVendor(this)"><option value="">—</option>{v_opts}'
            f'<option value="{other}"{" selected" if v_sel == other else ""}>{_esc(ui.get("dsp_other_vendor", "another vendor"))}</option></select>'
            f'<input type="text" id="dsp-vendor-free" value="{_esc(free_v)}" oninput="redraw()"{"" if v_sel == other else " hidden"}></div></div>'
            f'<div class="f s-{state}"><div class="q"><span class="dot d-{state}"></span>{_esc(ask["dsp.model"])}</div>'
            f'<div class="row"><select id="dsp-model" onchange="pickModel(this)"><option value="">—</option>{m_opts}'
            f'<option value="{other}"{" selected" if m_sel == other else ""}>{_esc(ui.get("dsp_other_model", "another model"))}</option></select>'
            f'<input type="text" id="dsp-model-free" value="{_esc(free_m)}" oninput="redraw()"{"" if m_sel == other else " hidden"}></div></div>'
            f'<div class="note" id="newdsp-link"{"" if dsp["new"] else " hidden"}>{_esc(ui.get("dsp_new_hint", ""))} '
            f'<a href="new-dsp">{_esc(ui.get("new_dsp_link", "New processor — fill in separately"))}</a></div>'
            f'<div class="note" id="newdsp-pending" hidden>{_esc(ui.get("dsp_new_unsaved", ""))}</div></div>')


def _goal_block(m, fields):
    """What the tune is for — ONE optional control: EMMA / AYA / for yourself / other + words.

    The ticks map onto the method's keys on the way in: EMMA/AYA are `goal.formats`, a format means
    competition, "for yourself" is enjoyment, both is both; the words go to `goal.wishes`.
    """
    ui = m["ui"]
    by = {f["id"]: f for f in fields}
    formats = by["goal.formats"]["value"] or []
    purpose = by["goal.purpose"]["value"] or ""
    wishes = by["goal.wishes"]["value"] or ""
    ticked = set(formats) | ({"enjoyment"} if purpose in ("enjoyment", "both") else set()) \
        | ({"other"} if wishes else set())
    choices = [("EMMA", "EMMA"), ("AYA", "AYA"),
               ("enjoyment", ui.get("goal_enjoyment", "for yourself")), ("other", ui.get("goal_other", "other"))]
    boxes = "".join(f'<label class="opt"><input type="checkbox" class="goal-pick" value="{v}"'
                    f'{" checked" if v in ticked else ""}> {_esc(t)}</label>' for v, t in choices)
    state = "have" if (formats or purpose or wishes) else "nice"
    ids = "".join(f'<span id="f-{fid}"></span>' for fid in ("goal.purpose", "goal.formats", "goal.wishes"))
    orig = {"choices": sorted(ticked), "text": wishes.strip() or None}
    return (f"<div class=\"f unit s-{state}\" data-kind=\"goal\" data-orig='{_esc(json.dumps(orig))}' id=\"goal-box\">"
            f'{ids}<div class="q"><span class="dot d-{state}"></span>{_esc(ui.get("goal_ask", "What is the tune for?"))}</div>'
            f'<div>{boxes}</div><div class="row"><input type="text" id="goal-text" value="{_esc(wishes)}" '
            f'placeholder="{_esc(ui.get("goal_text", "in your own words"))}"></div></div>')


def _channel_map_block(m, ui):
    """The processor's channel map as TCC draws it — one fold per tier, `used/total`, a row per
    slot with ON/OFF — drawn by the page's JS from the data it carries, so it is redrawn for a
    newly picked processor before anything is saved (round 4). Writes: `intake.save_slot`."""
    codes = {"virtual_channels": intake.SUGGESTED_VIRTUAL_CODES}
    tiers = dict.fromkeys(list(intake.SUGGESTED_TIERS) + [g["tier"] for d in m["dsps"] for g in d["groups"]]
                          + list(m["dsp"]["tiers"]))
    lists = "".join(f'<datalist id="codes-{_esc(t)}">'
                    + "".join(f'<option value="{_esc(c)}">' for c in codes.get(t, intake.SUGGESTED_CHANNEL_CODES))
                    + "</datalist>" for t in tiers)
    ids = "".join(f'<span id="f-{fid}"></span>' for fid in
                  ("channel_map.code", "channel_map.slot", "channel_map.tier", "channel_map.hidden"))
    return (f'<div class="f chanmap" id="chanmap">{ids}<div class="q">{_esc(ui.get("map_title", "Channel map"))}</div>'
            f'<div class="meta">{_esc(ui.get("map_why", ""))}</div>{lists}'
            f'<div class="note" id="chanmap-note">{_esc(ui.get("map_first", ""))}</div>'
            f'<div id="chanmap-body"></div></div>')


def _curve_block(m, fields):
    """The target curve: ONE choice (round 3) — ours, NTT's presets, or one's own."""
    ui = m["ui"]
    f = next(x for x in fields if x["id"] == "target_curve.candidate")
    value = f["value"] or ""
    known = (intake.BUNDLED_CURVE,) + intake.NTT_CURVE_PRESETS
    own = value if value and value not in known else ""

    def radio(v, label):
        return (f'<label class="opt"><input type="radio" name="curve" value="{_esc(v)}"'
                f'{" checked" if value == v or (v == "__own__" and own) else ""}> {_esc(label)}</label>')

    state = "have" if value else "nice"
    return (f"<div class=\"f unit s-{state}\" data-kind=\"curve\" data-orig='{_esc(_orig(value))}' "
            f'id="f-target_curve.candidate"><div class="q">'
            f'<span class="dot d-{state}"></span>{_esc(f["ask"])}</div>'
            f'<div class="curve-ours">{radio(intake.BUNDLED_CURVE, ui.get("curve_ours", "SQ-Comp-Ref — ours"))}</div>'
            f'<div class="meta">{_esc(ui.get("curve_ntt", "Nono Tuning Tool presets"))} — '
            f'<a href="{_esc(intake.NTT_URL)}" target="_blank" rel="noopener">nonotuningtool.com</a>. '
            f'{_esc(ui.get("curve_ntt_note", ""))}</div>'
            f'<div class="curve-grid">' + "".join(radio(c, c) for c in intake.NTT_CURVE_PRESETS) + "</div>"
            f'<div>{radio("__own__", ui.get("curve_own", "own / other"))}'
            f'<input type="text" id="curve-own" value="{_esc(own)}" '
            f'placeholder="{_esc(ui.get("curve_own_hint", "its name or file"))}"></div></div>')


def _driver_table(m, cols, ui):
    """The optional structured half of «Інше обладнання»: one row per live channel. None → nothing."""
    rows = [r for r in m["rows"]["channels"] if not r.get("hidden") and r.get("role") != "unused"]
    if not rows:
        return ""
    head = "".join(f'<th id="f-{_esc(c["id"])}">{_esc(c["ask"])}</th>' for c in cols)
    body = []
    for row in rows:
        cells, orig = [], {"code": row.get("code")}
        for c in cols:
            leaf = c["id"].split(".", 1)[1]
            raw = row.get(leaf)
            if leaf == "driver":
                drv = row.get("driver") or {}
                raw = drv.get("name") or " ".join(x for x in (drv.get("make"), drv.get("model")) if x)
            elif project.is_fact(raw):
                raw = project.fact_value(raw)
            value = "" if raw is None else str(raw)
            orig[leaf] = value.strip() or None
            # No pre-selected default in this optional table: a cell the person did not touch is
            # not an answer, and there is no tick here to confirm one.
            cells.append(f'<td>{_choice(dict(c, default=None), value, ui, key=leaf)}</td>')
        body.append(f"<tr class=\"unit\" data-kind=\"chanrow\" data-orig='{_esc(json.dumps(orig))}'>"
                    f'<th>{_esc(row.get("code"))}<input type="hidden" data-k="code" value="{_esc(row.get("code"))}"></th>'
                    + "".join(cells) + "</tr>")
    return (f'<div class="meta">{_esc(ui.get("drivers_title", ""))}</div>'
            f'<div style="overflow-x:auto"><table class="drivers"><tr><th></th>{head}</tr>' + "".join(body) + "</table></div>")


def _section(m, rows, ui):
    """One place's questions, in the table's group order — couples kept whole."""
    out, done, heading = [], set(), None
    titles = {g["id"]: g["title"] for g in m["groups"]}
    for gid, _why in intake.GROUPS:
        for f in [x for x in rows if x["group"] == gid]:
            if f["id"] in done:
                continue
            if heading != gid:
                out.append(f'<h3>{_esc(titles.get(gid, gid))}</h3>')
                heading = gid
            if f["id"] in dict(CAR_PARTS).values():
                out.append(_car_block(m, rows))
                done |= set(dict(CAR_PARTS).values())
                continue
            if f["couple"] == "dsp_identity":
                out.append(_dsp_block(m, m["fields"]))
                done |= {x["id"] for x in rows if x["couple"] == "dsp_identity"}
                continue
            if f["couple"] == "purpose":
                out.append(_goal_block(m, m["fields"]))
                done |= {x["id"] for x in rows if x["couple"] == "purpose"} | {"goal.wishes"}
                continue
            if f["per"] == "channel" and f["place"] == "now":
                out.append(_channel_map_block(m, ui))
                done |= {c["id"] for c in rows if c["per"] == "channel"}
                continue
            if f["id"] == "target_curve.candidate":
                out.append(_curve_block(m, m["fields"]))
                done.add(f["id"])
                continue
            if f["id"] == "project.user_language":
                out.append(_user_lang_block(f, ui))
                done.add(f["id"])
                continue
            mates = [x for x in rows if f["couple"] and x["couple"] == f["couple"]
                     and x["id"] not in done and not x["per"]]
            if len(mates) >= 2:
                couple = m["couplings"].get(f["couple"], {})
                out.append(f'<div class="couple"><div class="t">{_esc(couple.get("title", ""))}</div>'
                           + "".join(_field_html(x, ui) for x in mates) + "</div>")
                done |= {x["id"] for x in mates}
                continue
            out.append(_field_html(f, ui))
            done.add(f["id"])
    return "".join(out)


def _user_lang_block(f, ui):
    """The USER's own language — optional, empty by default, and it switches nothing: the AI's
    language is the interface language, always (the Arbiter, 2026-09-22)."""
    value = f["value"] or ""
    codes = [v for v, _t in f["suggest"]]
    other = bool(value) and value not in codes
    opts = "".join(f'<option value="{_esc(v)}"{" selected" if value == v else ""}>{_esc(t)}</option>'
                   for v, t in f["suggest"])
    return (f"<div class=\"f unit s-{f['state']}\" data-kind=\"userlang\" data-orig='{_esc(_orig(value))}'>"
            f'<span id="f-{_esc(f["id"])}"></span><div class="q"><span class="dot d-{f["state"]}"></span>'
            f'{_esc(f["ask"])}</div><div class="row"><select onchange="this.nextElementSibling.hidden = '
            f'this.value !== \'__other__\'"><option value="">—</option>{opts}'
            f'<option value="__other__"{" selected" if other else ""}>{_esc(ui.get("user_lang_other", "other"))}</option>'
            f'</select><input type="text" value="{_esc(value if other else "")}" '
            f'placeholder="{_esc(ui.get("user_lang_other_ph", ""))}"{"" if other else " hidden"}></div></div>')


def _knobs_block(f, ui):
    """Knobs outside the DSP as a LIST of `name — position` rows (round 5): the processor's own
    remote knobs pre-seeded (`intake.dsp_knobs`), any other added by name. The rows are drawn by the
    page's JS so they follow a processor change. Writes: `intake.save_controls` -> `hardware.controls`."""
    return (f'<div class="f" id="f-{_esc(f["id"])}"><div class="q">{_esc(f["ask"])}</div>'
            f'<div class="meta">{_esc(ui.get("knobs_why", ""))}</div>'
            f'<div id="knobs"><div id="knob-rows"></div>'
            f'<button type="button" class="add" onclick="addKnob()">+ {_esc(ui.get("knob_add", "add your own"))}</button>'
            f'</div></div>')


def _page_data(m):
    """What the page's JS draws the channel map from — embedded, so it works before any save."""
    chans = [{"tier": c.get("tier"), "slot": str(c.get("slot")), "code": c.get("code"),
              "hidden": bool(c.get("hidden")), "role": c.get("role")}
             for c in m["rows"]["channels"] if c.get("tier") and c.get("slot")]
    ui = m["ui"]
    t = {k: ui.get(k, "") for k in ("chan_on", "chan_off", "code_pick", "code_needed", "map_first",
                                    "map_new", "map_new_unsaved", "map_replaced",
                                    "dsp_confirm", "nothing_changed", "save_cancelled",
                                    "knob_pos", "knob_name")}
    # Round 6: what is wrong is said AT the field. English fallbacks for a language without them.
    t.update({k: ui.get(k) or en for k, en in _ERR_EN.items()})
    t["tier_names"] = ui.get("tier_names") if isinstance(ui.get("tier_names"), dict) else {}
    data = {"dsps": [{"vendor": d["vendor"], "model": d["model"], "groups": d["groups"],
                      "knobs": d.get("knobs") or []} for d in m["dsps"]],
            "saved": {"vendor": m["dsp"]["vendor"], "model": m["dsp"]["model"], "new": bool(m["dsp"]["new"]),
                      "groups": m["dsp"]["groups"], "channels": chans, "slotted": len(chans),
                      "tiers_used": m["tiers_used"], "knobs": m["dsp"].get("knobs") or []},
            "controls": m["controls"], "car": m["car"],
            "lang": m["lang"] if m["lang"] in intake.LANGUAGES else None, "lang_saved": m["lang_saved"],
            "off_prefix": intake.OFF_PREFIX, "t": t}
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


def _shell(m, title, parts, button_after=""):
    ui = m["ui"]
    after = f' data-after="{_esc(button_after)}"' if button_after else ""
    return (
        "<!doctype html><html lang=\"" + _esc(m["lang"]) + "\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        f"<title>{_esc(title)}</title><style>{_CSS}</style></head><body>"
        f"<header><h1>{_esc(title)}</h1>" + parts[0] + "</header>"
        f"<main>{''.join(parts[1:])}</main>"
        f'<div class="savebar"><button type="button" class="save big" onclick="saveAll(this)"{after}>'
        f'{_esc(ui.get("save", "Save"))}</button><div id="save-status" class="status"></div></div>'
        f'<script type="application/json" id="intake-data">{_page_data(m)}</script>'
        f"<script>{_JS}</script></body></html>"
    )


def render(m):
    """The intake page: one self-contained file, no CDN, no font — it must open on a car's laptop.

    Open: what starting to measure needs, then the optional goal and the optional «Інше
    обладнання» (a free-text description first). Not rendered at all: the memo (round 4) — those
    fields stay in `intake.FIELDS` for the session. A new processor's base is its OWN page.
    """
    ui = m["ui"]
    t = m["totals"]
    fields = m["fields"]
    chips = (f'<span class="chip"><span class="dot d-gate"></span>'
             f'{_esc(ui.get("legend_now", "to answer now"))} <b>{t["now_open"]}</b> / {t["now"]}</span>'
             f'<span class="chip"><span class="dot d-have"></span>'
             f'{_esc(ui.get("legend_green", "answered"))} <b>{t["have"]}</b></span>')
    gate = m["gate"]
    verdict = (f'<span class="gate-ok">{_esc(ui.get("gate_open", "gate open"))}</span>'
               if gate["open"] else
               f'<span class="gate-shut">{_esc(ui.get("gate_shut", "gate shut"))}</span>'
               + (f' — {_esc(ui.get("gate_missing", "missing"))}: '
                  f'{_esc(", ".join(gate["missing_files"]))}' if gate["missing_files"] else ""))
    head = (f"<div class=\"sub\">{_esc(ui.get('subtitle', ''))}</div>"
            f"<div class=\"dir\">{_esc(m['project_dir'])}</div>"
            f"<div class=\"chips\">{chips}<span class=\"chip\">{verdict}</span>"
            f"<span class=\"chip\"><code>{_esc(gate['command'])}</code></span></div>")

    def place(p):
        return [f for f in fields if f["place"] == p]

    parts = [head,
             f'<section class="now"><h2>{_esc(ui.get("now_title", "Now"))}</h2>'
             f'<p class="why">{_esc(ui.get("now_why", ""))}</p>' + _section(m, place("now"), ui) + "</section>",
             f'<section class="goal"><h2>{_esc(ui.get("goal_title", "Goal and music"))}</h2>'
             f'<p class="why">{_esc(ui.get("goal_why", ""))}</p>' + _section(m, place("goal"), ui) + "</section>"]
    equipment = place("equipment")
    desc = [f for f in equipment if f["id"] == "hardware.description"]
    cols = [f for f in equipment if f["per"] == "channel"]
    table = _driver_table(m, cols, ui)
    ids = "" if table else "".join(f'<span id="f-{_esc(f["id"])}"></span>' for f in cols)
    knobs = next(f for f in equipment if f["id"] == "channel_map.hardware_controls")
    rest = [f for f in equipment if f["per"] != "channel"
            and f["id"] not in ("hardware.description", "channel_map.hardware_controls")]
    parts.append(f'<section class="equipment" id="equipment"><h2>{_esc(ui.get("equipment_title", "Other equipment"))}</h2>'
                 f'<p class="why">{_esc(ui.get("equipment_why", ""))}</p>'
                 + "".join(_field_html(f, ui) for f in desc) + _knobs_block(knobs, ui) + table + ids
                 + "".join(_field_html(f, ui) for f in rest) + "</section>")
    return _shell(m, ui.get("title", "Intake"), parts)


def render_new_dsp(m):
    """The NEW processor's own form (round 4): its tiers, how many slots each has and how they are
    labelled, its controls, and the capability answers — written once, into the interview draft
    (`intake.save_new_dsp`). The main page's channel map is built from what this records."""
    ui = m["ui"]
    dsp = m["dsp"]
    title = " — ".join(x for x in (ui.get("new_dsp_title", "New processor"),
                                    f'{dsp["vendor"]} {dsp["model"]}'.strip()) if x)
    back = f'<div class="sub"><a href="./">{_esc(ui.get("back_to_intake", "back to the intake"))}</a></div>'
    if not dsp["new"]:
        return _shell(m, title, [back, f'<div class="note">{_esc(ui.get("new_dsp_not_new", ""))}</div>'])
    a = m["new_dsp"]
    fields = {f["id"]: f for f in m["fields"]}
    controls = ui.get("controls") if isinstance(ui.get("controls"), dict) else {}
    tier_names = ui.get("tier_names") if isinstance(ui.get("tier_names"), dict) else {}

    def checks(name, values, chosen, labels=None):
        chosen = [str(c) for c in chosen or []]
        return "".join(f'<label class="opt"><input type="checkbox" name="{_esc(name)}" value="{_esc(v)}"'
                       f'{" checked" if str(v) in chosen else ""}> {_esc((labels or {}).get(v, v))}</label>'
                       for v in values)

    def yesno(name, value):
        opts = (("yes", ui.get("yes", "yes")), ("no", ui.get("no", "no")), ("", ui.get("dont_know", "don't know")))
        cur = "yes" if value is True else "no" if value is False else ""
        return "".join(f'<label class="opt"><input type="radio" name="{_esc(name)}" value="{v}"'
                       f'{" checked" if v == cur else ""}> {_esc(t)}</label>' for v, t in opts)

    def num(name, value):
        return (f'<input type="text" inputmode="decimal" class="num" name="{_esc(name)}" '
                f'value="{_esc("" if value is None else value)}">')

    rows = []
    for tier in intake.SUGGESTED_TIERS:
        have = a["tiers"].get(tier)
        row = have or {"count": None, "letters": True, "fields": []}
        rows.append(
            f'<div class="tier-row" data-tier="{_esc(tier)}"><label class="opt"><input type="checkbox" class="has"'
            f'{" checked" if have else ""}> <b>{_esc(tier_names.get(tier, tier))}</b></label>'
            f'<div class="row">{_esc(ui.get("slots_count", "slots"))} {num("count-" + tier, row["count"])} '
            f'<label class="opt"><input type="radio" name="style-{_esc(tier)}" value="letter"'
            f'{" checked" if row["letters"] else ""}> A, B, C…</label>'
            f'<label class="opt"><input type="radio" name="style-{_esc(tier)}" value="number"'
            f'{"" if row["letters"] else " checked"}> 1, 2, 3…</label></div>'
            f'<div class="row">{_esc(ui.get("tier_controls", "controls"))}: '
            f'{checks("fields-" + tier, list(dsp_profile.FIELD_VOCABULARY), row["fields"], controls)}</div></div>')

    def q(fid):
        return _esc(fields[fid]["ask"])

    rate_opts = "".join(f'<option value="{r}"{" selected" if a["rate"] == r else ""}>{r}</option>'
                        for r in intake.PLAUSIBLE_RATES_HZ)
    body = (
        f'<form id="newdsp-form" onsubmit="return false">'
        f'<p class="why">{_esc(ui.get("new_dsp_why", ""))}</p>'
        f'<div class="f" id="f-dsp.tiers"><div class="q">{q("dsp.tiers")}</div>'
        f'<span id="f-dsp.max_count"></span><div class="meta">{q("dsp.max_count")}</div>{"".join(rows)}</div>'
        f'<div class="f" id="f-dsp.processing_rate_hz"><div class="q">{q("dsp.processing_rate_hz")}</div>'
        f'<div class="row"><select name="rate"><option value="">—</option>{rate_opts}</select></div></div>'
        f'<div class="f" id="f-dsp.eq"><div class="q">{q("dsp.eq")}</div>'
        f'<div class="row">{_esc(ui.get("eq_bands", "bands per channel"))} {num("eq-bands", a["eq"].get("bands"))}</div>'
        f'<div class="row">{checks("eq-types", intake.EQ_BAND_TYPES, a["eq"].get("types"))}</div>'
        f'<div class="row">{_esc(ui.get("eq_file", "EQ file import"))}: {yesno("eq-file", a["eq"].get("file_import"))}</div></div>'
        f'<div class="f" id="f-dsp.crossovers"><div class="q">{q("dsp.crossovers")}</div>'
        f'<div class="row">{checks("xo-types", intake.XO_FAMILIES, a["crossover"].get("types"))}</div>'
        f'<div class="row">{_esc(ui.get("xo_slopes", "slopes, dB/oct"))}: '
        f'{checks("xo-slopes", intake.XO_SLOPES, a["crossover"].get("slopes"))}</div>'
        f'<div class="row">{_esc(ui.get("xo_indep", "independent HP and LP"))}: {yesno("xo-indep", a["crossover"].get("independent"))}</div></div>'
        f'<div class="f" id="f-dsp.delays"><div class="q">{q("dsp.delays")}</div>'
        f'<div class="row">{_esc(ui.get("delay_step", "step, ms"))} {num("delay-step", a["delay"].get("step_ms"))} '
        f'{_esc(ui.get("delay_max", "maximum, ms"))} {num("delay-max", a["delay"].get("max_ms"))}</div></div>'
        f'<div class="f" id="f-dsp.presets"><div class="q">{q("dsp.presets")}</div>'
        f'<div class="row">{_esc(ui.get("presets_count", "how many"))} {num("presets-count", a["presets"].get("count"))}</div>'
        f'<div class="row">{_esc(ui.get("presets_input", "the input switches with the preset"))}: '
        f'{yesno("presets-input", a["presets"].get("input_switches"))}</div></div></form>')
    return _shell(m, title, [back, body], button_after="./")


# ── writing back ──────────────────────────────────────────────────────────────
def _coerce(field_id, value):
    """A form posts strings; the table's enumerations are typed. `96000` must not arrive as text.

    Only the field's OWN enumeration decides — no general "looks like a number" guess, which would
    turn a channel code of `12` into an int and a slot letter into nothing.
    """
    f = intake.field(field_id)
    if isinstance(value, str) and f["enum"]:
        for choice in f["enum"]:
            if str(choice) == value:
                return choice
    return value


def apply_save(project_dir, payload):
    """One posted answer → the method's own writer. Returns what was written.

    Every refusal comes from `intake`/`project` and is handed back verbatim: the page must say the
    method's words ("a slot needs its tier in the same breath"), not a paraphrase of them.
    """
    if "batch" in payload:
        # ONE Save sends every changed answer at once (round 4). Each goes through its own writer,
        # in the order the page sent them (the processor before its tiers, the tiers before the
        # slots); a refusal is reported for that answer and does not stop the ones after it —
        # every writer is atomic, so what was written is whole and what was refused is untouched.
        results, errors = [], []
        for i, item in enumerate(payload["batch"] or []):
            try:
                results.append(apply_save(project_dir, item))
            except (intake.IntakeError, project.ProjectError, ValueError) as exc:
                errors.append({"index": i, "error": str(exc)})
        return {"results": results, "errors": errors}

    if "field" in payload:
        value = payload.get("value")
        if isinstance(value, list):
            if not value:
                raise intake.IntakeError("nothing chosen — nothing was written")
        elif value in (None, ""):
            raise intake.IntakeError("порожнє значення — нічого не записано")
        return {"field": payload["field"],
                "value": intake.save(project_dir, payload["field"], _coerce(payload["field"], value))}

    if "slot" in payload:
        row = payload["slot"]
        # A slot belongs to the processor the map was drawn for; if that processor was not saved
        # (a refused change, a cancelled one), the slot is refused rather than filed on another unit.
        drawn = row.get("dsp")
        if drawn:
            saved = intake.dsp_state(project_dir)
            if [str(x).strip().lower() for x in drawn] != [saved["vendor"].lower(), saved["model"].lower()]:
                raise intake.IntakeError(f"slot {row.get('slot')}: the map was drawn for {' '.join(drawn)}, "
                                         f"and the project's processor is {saved['vendor']} {saved['model']} "
                                         "— save the processor first. Nothing was written")
        if row.get("move_from"):
            # The same code switched off in one slot and on in another in one Save: the wire moved.
            return {"slot": intake.move_slot(project_dir, row.get("tier"), row.get("code"),
                                             row.get("slot"))}
        return {"slot": intake.save_slot(project_dir, row.get("tier"), row.get("slot"),
                                         code=row.get("code"), on=bool(row.get("on")))}

    if "dsp" in payload:
        # Vendor and model are ONE identity: both or nothing, written together.
        row = payload["dsp"]
        return {"dsp": intake.change_dsp(project_dir, row.get("vendor"), row.get("model"),
                                         replace_map=bool(row.get("replace_map")))}

    if "controls" in payload:
        return {"controls": intake.save_controls(project_dir, payload["controls"] or {})}

    if "new_dsp" in payload:
        return {"new_dsp": intake.save_new_dsp(project_dir, payload["new_dsp"] or {})}

    if "goal" in payload:
        # EMMA / AYA / for yourself / other -> the method's own keys (`_goal_block`).
        row = payload["goal"]
        choices = set(row.get("choices") or [])
        formats = [f for f in intake.FORMATS if f in choices]
        enjoy = "enjoyment" in choices
        purpose = ("both" if formats and enjoy else "competition" if formats
                   else "enjoyment" if enjoy else None)
        written = {"formats": intake.save(project_dir, "goal.formats", formats)}
        if purpose:
            written["purpose"] = intake.save(project_dir, "goal.purpose", purpose)
        text = (row.get("text") or "").strip()
        if text:
            written["wishes"] = intake.save(project_dir, "goal.wishes", text)
        return {"goal": written}

    if "car" in payload:
        row = payload["car"]
        return {"car": intake.save_car(project_dir, row.get("make"), row.get("model"),
                                       row.get("generation"), row.get("body"),
                                       year=row.get("year") or None)}

    if "channel" in payload:
        row = dict(payload["channel"])
        code = (row.pop("code", "") or "").strip()
        if not code:
            raise intake.IntakeError("a channel row needs its code — nothing was written")
        if "driver" in row:
            row["driver"] = {"name": row.pop("driver")}
        if "fs_hz" in row:
            row["fs_hz"] = float(row["fs_hz"])
        return {"channel": intake.save_channel(project_dir, code, source="user", **row)}

    if "amp" in payload:
        row = dict(payload["amp"])
        index = row.pop("index", None)
        return {"amp": intake.save_amp(project_dir, index=int(index) if index not in (None, "") else None,
                                       **row)}

    raise intake.IntakeError(f"nothing to save in {sorted(payload)}")


# ── the local server ──────────────────────────────────────────────────────────
class _Handler(BaseHTTPRequestHandler):
    project_dir = None
    lang = DEFAULT_LANG

    def _send(self, code, body, kind="application/json; charset=utf-8"):
        raw = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):  # noqa: N802 — http.server's own spelling
        path = self.path.split("?", 1)[0]
        if path == "/":
            page = render(model(self.project_dir, self.lang))
            return self._send(200, page, "text/html; charset=utf-8")
        if path == "/new-dsp":
            page = render_new_dsp(model(self.project_dir, self.lang))
            return self._send(200, page, "text/html; charset=utf-8")
        if path == "/state":
            return self._send(200, json.dumps(model(self.project_dir, self.lang),
                                              ensure_ascii=False, indent=2))
        self._send(404, json.dumps({"error": "no such page"}))

    def do_POST(self):  # noqa: N802
        if self.path.split("?", 1)[0] != "/save":
            return self._send(404, json.dumps({"error": "no such page"}))
        length = int(self.headers.get("Content-Length") or 0)
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
            written = apply_save(self.project_dir, payload)
        except (intake.IntakeError, project.ProjectError, ValueError) as exc:
            return self._send(400, json.dumps({"error": str(exc)}, ensure_ascii=False))
        if "batch" in payload:
            # The page reads `errors` at the top: one Save, one report of what was refused.
            return self._send(200, json.dumps(dict(written, ok=not written["errors"]),
                                              ensure_ascii=False, default=str))
        self._send(200, json.dumps({"ok": True, "written": written}, ensure_ascii=False,
                                   default=str))

    def log_message(self, fmt, *args):  # keep the terminal for the session, not for hits
        pass


def serve(project_dir, port=0, lang=DEFAULT_LANG, open_browser=False):
    """Serve the form on the loopback only. Port 0 = let the OS pick, and print what it picked.

    A directory that is not there is refused before the socket is opened: a form for a project that
    does not exist would answer every question into nothing, and a server nobody can use still
    holds a port (and would hang the documented-command check, which runs every command a document
    prints against paths that are deliberately absent).
    """
    if not os.path.isdir(project_dir):
        raise intake.IntakeError(f"no such project directory: {project_dir}")
    handler = type("_Bound", (_Handler,), {"project_dir": os.path.abspath(project_dir),
                                           "lang": lang})
    httpd = ThreadingHTTPServer(("127.0.0.1", port), handler)
    url = f"http://127.0.0.1:{httpd.server_address[1]}/"
    print(f"  інтейк-форма: {url}\n  проєкт: {os.path.abspath(project_dir)}\n"
          f"  мова: {lang} · Ctrl-C щоб зупинити")
    if open_browser:
        webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  зупинено")
    finally:
        httpd.server_close()
    return url


# ── selftest ──────────────────────────────────────────────────────────────────
def _selftest():
    import re
    import tempfile

    # ── the translation covers the table, and covers it by ID ────────────────────────────────
    # A label file that has drifted from FIELDS is worse than none: the page would silently fall
    # back to English for the fields somebody actually renamed, and nobody would see it.
    lab = labels("uk")
    ids = {f["id"] for f in intake.FIELDS}
    assert set(lab["fields"]) == ids, (
        f"uk.json misses {sorted(ids - set(lab['fields']))}, invents {sorted(set(lab['fields']) - ids)}")
    for f in intake.FIELDS:
        row = lab["fields"][f["id"]]
        assert row.get("ask", "").strip(), f"{f['id']}: no Ukrainian question"
        for choice in f["enum"] or ():
            # A numeric choice is its own label -- 96000 is 96000 in every language.
            if not str(choice).isdigit():
                assert str(choice) in (row.get("enum") or {}), f"{f['id']}: {choice} not translated"
    assert set(lab["groups"]) >= {g for g, _ in intake.GROUPS}, lab["groups"]

    with tempfile.TemporaryDirectory() as root:
        intake.save_car(root, "VW", "Passat", "B8", "sedan")
        intake.save(root, "source.connection", "optical")
        m = model(root, "uk")

        # ── the model says what is owed, and the four buckets are the whole table ────────────
        t = m["totals"]
        assert t["gate"] + t["nice"] + t["have"] + t["prose"] == len(intake.FIELDS) == t["all"], t
        by_id = {f["id"]: f for f in m["fields"]}
        assert by_id["car.body"]["state"] == HAVE, by_id["car.body"]
        assert by_id["car.body"]["value"] == "sedan", by_id["car.body"]
        assert by_id["source.connection"]["state"] == HAVE
        assert by_id["dsp.vendor"]["state"] == GATE, "a required, missing field is not red"
        assert by_id["car.year"]["state"] == NICE, "an optional, missing field is not yellow"
        assert by_id["target_curve.loves_most"]["state"] == PROSE, "prose is not reported as prose"
        # The probes are marked, so the page does not ask a person to do the tool's job.
        for pid in PROBES:
            assert by_id[pid]["probe"], pid

        # ── the page: what it shows, and — round 4 — what it does NOT ─────────────────────────
        page = render(m)

        def carried_lang(html_):
            raw = re.search(r'<script type="application/json" id="intake-data">(.*?)</script>',
                            html_, re.S).group(1)
            d = json.loads(raw.replace("<\\/", "</"))
            return d["lang"], d["lang_saved"]
        for f in intake.FIELDS:
            if f["place"] in ("now", "goal", "equipment"):
                assert f'f-{f["id"]}' in page, f"{f['id']} is not on the page"
            if f["place"] in ("memo", "new_dsp"):
                # The memo stays in the data for the session and is not rendered; the new
                # processor's base is its OWN page.
                assert f'id="f-{f["id"]}"' not in page, f"{f['id']} ({f['place']}) is on the main page"
        assert 'id="memo"' not in page and 'id="new-dsp"' not in page
        # Nothing is LOADED from the network (no CDN, no font): it must open on a car's laptop. One
        # thing may point out, and only as a link the person clicks: NTT, where the curve files are
        # downloaded (round 3, 2026-09-22). Any other outbound reference still fails here.
        external = re.findall(r"""(?:src|href)=["']https?://""", page)
        links = re.findall(r"""<a href=["'](https?://[^"']+)""", page)
        assert len(external) == len(links) and set(links) <= {intake.NTT_URL}, \
            f"the page reaches the network: {external[:3]} / links {links}"
        assert not re.findall(r"""src=["']https?://|<link[^>]+href=["']https?://""", page), \
            "the page loads something from the network"
        assert "Для кого цей проєкт" in page, "the Ukrainian labels did not reach the page"
        # Round 5: the reply language is NOT a question -- the page's own language rides along and
        # is written on Save.
        assert 'data-id="project.language"' not in page and "Якою мовою відповідати" not in page
        # The USER's language is optional, empty, pre-fills nothing, and is stored apart.
        ul = page.split('data-kind="userlang"', 1)[1].split("</div></div>", 1)[0]
        assert "data-orig='null'" in page.split('data-kind="userlang"', 1)[1][:30] and " selected" not in ul
        assert carried_lang(page) == ("uk", None), carried_lang(page)
        # ONE «Зберегти» for the page, not a button on every question.
        assert len(re.findall(r'<button[^>]*class="save', page)) == 1 and ">Зберегти<" in page \
            and "Записати" not in page, "more than one Save, or the old label"
        assert m["couplings"]["seat"]["fields"] == ["car.drive_side", "goal.reference_seat"]

        now_html = page.split("</section>", 1)[0]
        for fid in ("goal.reference_seat", "car.drive_side", "channel_map.code", "rew.loopback",
                    "dsp.vendor", "dsp.tiers_used"):
            assert f"f-{fid}" in now_html, f"{fid} is needed to start measuring and is not up front"
        couple = now_html.split('id="f-car.drive_side"', 1)[1].split('<div class="couple">', 1)[0]
        assert 'id="f-goal.reference_seat"' in couple, "the seat couple was split"
        # Round 5: no confirm ticks. A pre-filled value is an ordinary one -- its unit starts from
        # what is ON DISK (null here), so Save writes what the page shows.
        assert "default-ok" not in page, "a confirm tick is back"
        side = now_html.split('data-id="car.drive_side"', 1)[1].split('data-kind=', 1)[0]
        assert 'value="LHD" checked' in side and "data-orig='null'" in now_html.split(
            'data-id="car.drive_side"', 1)[1][:40], "the pre-filled drive side is not a change"
        assert 'class="drive-auto' in side, "the drive side cannot fold into the car"
        seat = now_html.split('data-id="goal.reference_seat"', 1)[1].split("</div></div>", 1)[0]
        assert " checked" not in seat, "the write-once seat is pre-selected"
        assert "seat_confirm" not in page and "asks.push({kind: 'seat'" not in page, "the seat asks again"
        # Round 6: once written, the seat is FIXED on the page -- no control, and the reason given.
        locked = tempfile.mkdtemp(prefix="intake_form_seat_")
        intake.save(locked, "goal.reference_seat", "passenger")
        lpage = render(model(locked, lang="uk"))
        lseat = lpage.split('id="f-goal.reference_seat"', 1)[0].rsplit("<div", 1)[1]
        assert "locked" in lseat and 'data-id="goal.reference_seat"' not in lpage, "a fixed seat is editable"
        assert labels("uk")["ui"]["seat_locked"] in lpage, "a fixed seat does not say why"
        # The drive side comes with a car that says it: the library's Passat names LHD.
        assert 'data-body="sedan" data-drive="LHD"' in page, "the picked car carries no drive side"
        assert 'data-make="VW" data-model="Passat" data-generation="B8" data-body="sedan"' in page
        for d in intake.known_dsps():
            assert f'value="{_esc(d["model"])}" data-vendor="{_esc(d["vendor"])}"' in page, d
        # The map is drawn by the page from the data it CARRIES — every bundled processor's tiers
        # and slots — so another processor's map appears the moment it is picked (round 4).
        def carried(html_):
            raw = re.search(r'<script type="application/json" id="intake-data">(.*?)</script>',
                            html_, re.S).group(1)
            return json.loads(raw.replace("<\\/", "</"))
        data = carried(page)
        helix = next(d for d in data["dsps"] if d["model"] == "Helix DSP Ultra S")
        assert [(g["tier"], len(g["slots"]), g["slots"][0]) for g in helix["groups"][:2]] == \
            [("virtual_channels", 8, "A"), ("channels", 12, "A")], helix["groups"]
        musway = next(d for d in data["dsps"] if d["vendor"] == "Musway")
        assert musway["groups"][0]["slots"] == [str(i) for i in range(1, 9)], musway
        assert data["saved"]["slotted"] == 0 and 'id="chanmap-body"' in page
        assert 'class="goal-pick" value="EMMA"' in page and "Яка цільова крива?" in page
        assert 'value="chesky"' in page and 'value="jazz"' in page, "libraries/genres are not checkboxes"
        assert 'value="SQ-Comp-Ref"' in page and "завантажувати не треба" in page
        for name in intake.NTT_CURVE_PRESETS:
            assert f'name="curve" value="{_esc(name)}"' in page, name
        # «Інше обладнання»: the free-text description is the way in; no channels, no table.
        equip = page.split('id="equipment"', 1)[1]
        assert "<textarea" in equip and 'data-id="hardware.description"' in equip and "<table" not in equip

        # ── one Save = one batch, in order: the processor, its tiers, its slots ───────────────
        helix_id = ["Audiotec-Fischer", "Helix DSP Ultra S"]
        res = apply_save(root, {"batch": [
            {"dsp": {"vendor": helix_id[0], "model": helix_id[1]}},
            {"field": "dsp.tiers_used", "value": ["virtual_channels", "channels"]},
            {"slot": {"tier": "virtual_channels", "slot": "A", "code": "VFL", "on": True, "dsp": helix_id}},
            {"slot": {"tier": "virtual_channels", "slot": "F", "code": "", "on": False, "dsp": helix_id}},
            {"slot": {"tier": "channels", "slot": "A", "code": "w-L", "on": True, "dsp": ["Musway", "M6V4 (no 512K)"]}},
            {"slot": {"tier": "virtual_channels", "slot": "B", "code": "VFL", "on": True, "dsp": helix_id}},
            {"field": "rew.loopback", "value": "acoustic"},
            {"field": "hardware.description", "value": "Audison AV 6.5, JL 12W3"}]})
        assert [e["index"] for e in res["errors"]] == [4, 5], res["errors"]
        assert "save the processor first" in res["errors"][0]["error"], res["errors"]
        assert "one code, one channel" in res["errors"][1]["error"], res["errors"]
        loaded = project.Project(root).load()
        assert loaded["hardware"]["description"] == "Audison AV 6.5, JL 12W3", loaded["hardware"]
        assert loaded["measurement"]["loopback"] == "acoustic", "a refusal stopped the rest of the batch"
        m2 = model(root, "uk")
        assert [(g["tier"], g["used"], g["total"]) for g in m2["map"]] == \
            [("virtual_channels", 1, 8), ("channels", 0, 12)], m2["map"]
        # ── round 5: knobs outside the DSP -- the processor's own pre-seeded, others by name ─
        d2 = carried(render(m2))
        assert d2["saved"]["knobs"] == ["SubRC", "RearRC"], d2["saved"]["knobs"]
        assert next(d for d in d2["dsps"] if d["vendor"] == "Musway")["knobs"] == []
        assert 'id="knob-rows"' in render(m2) and "непорівнянними" in render(m2)
        res = apply_save(root, {"batch": [{"controls": {"SubRC": "4/4", "бас на магнітолі": "7",
                                                        "RearRC": ""}}]})
        assert not res["errors"], res
        hw = project.Project(root).load()["hardware"]["controls"]
        assert project.fact_value(hw["SubRC"]) == "4/4" and hw["SubRC"]["source"] == "user", hw
        assert project.fact_value(hw["бас на магнітолі"]) == "7" and "RearRC" not in hw, hw
        assert carried(render(model(root, "uk")))["controls"]["SubRC"] == "4/4"
        # The language is written on Save when it differs from what is stored, and then rides as saved.
        apply_save(root, {"field": "project.language", "value": "uk"})
        assert carried_lang(render(model(root, "uk"))) == ("uk", "uk")
        apply_save(root, {"field": "project.user_language", "value": "ru"})
        lang = project.Project(root).load()["language"]
        assert lang == {"reply": "uk", "user": "ru"}, lang
        assert project.reply_language(project.Project(root).load())["lang"] == "uk", \
            "the user's language switched the AI's"
        # Both routes honour the interface language they are started with.
        assert carried_lang(render_new_dsp(model(root, "uk")))[0] == "uk"
        assert carried(render(m2))["saved"]["slotted"] == 2, "the saved map is not carried"

        # ── a processor change: the saved map is REPLACED, never merged — and only when confirmed
        res = apply_save(root, {"batch": [{"dsp": {"vendor": "Musway", "model": "M6V4 (no 512K)"}}]})
        assert res["errors"] and "REPLACED" in res["errors"][0]["error"], res
        assert project.Project(root).load()["dsp"]["model"] == "Helix DSP Ultra S", "written unconfirmed"
        res = apply_save(root, {"batch": [{"dsp": {"vendor": "Musway", "model": "M6V4 (no 512K)",
                                                   "replace_map": True}}]})
        assert not res["errors"], res
        loaded = project.Project(root).load()
        assert loaded["dsp"]["previous_maps"][0]["model"] == "Helix DSP Ultra S", loaded["dsp"]
        assert not [c for c in loaded["channels"] if c.get("slot")], "a slot crossed processors"
        assert [c["code"] for c in loaded["channels"]] == ["VFL"], "the car's channel was lost"
        m2 = model(root, "uk")
        assert [(g["tier"], g["used"], g["total"]) for g in m2["map"]] == [("channels", 0, 8)], m2["map"]

        # ── a NEW processor: its own page, and the map from what that page records ───────────
        apply_save(root, {"dsp": {"vendor": "Acme", "model": "X8"}})
        m3 = model(root, "uk")
        page3 = render(m3)
        assert m3["dsp"]["new"] is True and '<div class="note" id="newdsp-link">' in page3
        assert 'href="new-dsp"' in page3 and not m3["map"], "a new processor has a map before its base"
        nd = render_new_dsp(m3)
        for f in intake.FIELDS:
            if f["place"] == "new_dsp":
                assert f'f-{f["id"]}' in nd, f"{f['id']} is not on the new-processor page"
        assert 'id="newdsp-form"' in nd and len(re.findall(r'<button[^>]*class="save', nd)) == 1
        res = apply_save(root, {"batch": [{"new_dsp": {
            "tiers": {"channels": {"count": "6", "letters": False,
                                   "fields": ["hp", "lp", "gain_db", "ta_ms", "polarity", "eq"]}},
            "rate": "48000", "eq": {"bands": "10", "types": ["PK"], "file_import": False},
            "crossover": {"types": ["LR"], "slopes": [24], "independent": True},
            "delay": {"step_ms": "0.02", "max_ms": "15"}, "presets": {"count": "4", "input_switches": True}}}]})
        assert not res["errors"], res
        m3 = model(root, "uk")
        assert [(g["tier"], g["total"], g["rows"][0]["slot"]) for g in m3["map"]] == [("channels", 6, "1")], m3["map"]
        assert 'name="count-channels" value="6"' in render_new_dsp(m3), "the form does not come back filled"
        apply_save(root, {"dsp": {"vendor": helix_id[0], "model": helix_id[1]}})
        assert 'id="newdsp-form"' not in render_new_dsp(model(root, "uk")), "a known DSP got the base form"

        apply_save(root, {"field": "target_curve.candidate", "value": "my_house_v3.txt"})
        page4 = render(model(root, "uk"))
        assert 'value="__own__" checked' in page4 and 'value="my_house_v3.txt"' in page4
        apply_save(root, {"goal": {"choices": ["EMMA", "enjoyment", "other"], "text": "clear nav"}})
        goal = project.Project(root).load()["goal"]
        assert goal == {"formats": ["EMMA"], "purpose": "both", "wishes": "clear nav",
                        "target_curve": "my_house_v3.txt"}, goal

        # ── writing back goes through the method's writers, refusals included ────────────────
        # An enumerated rate posted as TEXT must land as the number the table holds.
        apply_save(root, {"field": "rew.capture_rate_hz", "value": "96000"})
        assert project.Project(root).load()["measurement"]["sample_rate_hz"] == 96000
        apply_save(root, {"channel": {"code": "w-L", "slot": "C", "tier": "channels",
                                      "driver": "GZ GZUW", "amp": "GZPA 4SQ, ch 3", "fs_hz": "52.4"}})
        row = next(c for c in project.Project(root).load()["channels"] if c["code"] == "w-L")
        assert row["driver"] == {"name": "GZ GZUW"} and row["amp"] == "GZPA 4SQ, ch 3", row
        assert project.fact_value(row["fs_hz"]) == 52.4 and row["fs_hz"]["source"] == "user", row
        try:
            apply_save(root, {"channel": {"code": "m-L", "slot": "D"}})
            raise AssertionError("a slot went in without its tier")
        except intake.IntakeError as exc:
            assert "tier" in str(exc), exc
        try:
            apply_save(root, {"field": "car.body", "value": "saloon"})
            raise AssertionError("a value outside the enumeration went in")
        except intake.IntakeError as exc:
            assert "sedan" in str(exc), exc
        apply_save(root, {"amp": {"make": "Ground Zero", "model": "GZPA 4SQ",
                                  "channels": "m-L/m-R"}})
        assert project.Project(root).load()["amps"][0]["model"] == "GZPA 4SQ"

        # ── the served page: both routes, and ONE Save's report where the page reads it ──────
        import threading
        import urllib.request
        handler = type("_Bound", (_Handler,), {"project_dir": root, "lang": "uk"})
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        try:
            base = f"http://127.0.0.1:{httpd.server_address[1]}/"
            assert "intake-data" in urllib.request.urlopen(base).read().decode()
            assert urllib.request.urlopen(base + "new-dsp").status == 200
            req = urllib.request.Request(base + "save", headers={"Content-Type": "application/json"},
                                         data=json.dumps({"batch": [{"field": "car.body", "value": "saloon"},
                                                                    {"field": "rew.loopback", "value": "physical"}]}).encode())
            out = json.loads(urllib.request.urlopen(req).read())
            assert out["ok"] is False and [e["index"] for e in out["errors"]] == [0], out
            assert project.Project(root).load()["measurement"]["loopback"] == "physical"
        finally:
            httpd.shutdown()
            httpd.server_close()

        # ── a missing translation is a fallback, never a crash ──────────────────────────────
        page_en = render(model(root, "xx"))
        assert intake.field("goal.reference_seat")["ask"] in page_en, "the English fallback did not render"

    print(f"selftest OK (intake_form) — {len(ids)} fields in one table and uk.json covers every one; "
          "the page shows the now/goal/equipment ones and NOT the memo, has ONE Save, a pre-filled "
          "value is an ordinary one (no ticks), a written seat is shown fixed with why, the reply language is the "
          "interface's and never asked, knobs are rows the processor pre-seeds, a processor change REPLACES a saved map only when "
          "confirmed, a new processor gets its own page and its map from it, the page loads nothing "
          "from the network (one link out: NTT), and every write goes through intake's own writers")
    return 0


def _main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if argv[0] in ("selftest", "--selftest"):
        return _selftest()
    cmd, rest = argv[0], argv[1:]
    project_dir = next((a for a in rest if not a.startswith("-")), None)
    lang = intake._flag(rest, "--lang", DEFAULT_LANG)
    if cmd in ("serve", "render", "state") and not project_dir:
        print(__doc__, file=sys.stderr)
        return 2
    if cmd == "serve":
        if not os.path.isdir(project_dir):
            print(f"  нема такої теки проєкту: {project_dir}", file=sys.stderr)
            return 2
        serve(project_dir, port=int(intake._flag(rest, "--port", 0)), lang=lang,
              open_browser="--open" in rest)
        return 0
    if cmd == "render":
        m = model(project_dir, lang)
        page = render_new_dsp(m) if intake._flag(rest, "--page") == "new-dsp" else render(m)
        out = intake._flag(rest, "--out")
        if out:
            with open(out, "w", encoding="utf-8") as fh:
                fh.write(page)
            print(f"  {out} — {len(page)} bytes")
        else:
            print(page)
        return 0
    if cmd == "state":
        print(json.dumps(model(project_dir, lang), ensure_ascii=False, indent=2))
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    import console                       # issue #21: a code page must not destroy a result
    console.install()
    sys.exit(_main(sys.argv[1:]))
