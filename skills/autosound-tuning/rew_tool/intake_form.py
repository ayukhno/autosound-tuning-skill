#!/usr/bin/env python3
"""The intake as a FORM the skill serves itself — one page generated from `intake.FIELDS` (S-033).

`intake.py` made Phase −1 readable as data (SCR-059); this module is the other half — the page that
renders it and the small local server that writes the answers back through the method's own writers.
It lives in the skill, not in a front-end, for one reason: the questions must exist ONCE. A window
that carries its own copy of them drifts from the method the first time a field is added, which is
the failure the car package already cost us (hub `#185`), and a terminal session has no window at
all — so `serve` gives it one.

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
  python3 rew_tool/intake_form.py render <project-dir> [--lang uk] [--out page.html]
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
.note { background:#fff; border:1px dashed var(--line); border-radius:8px; padding:9px 12px;
        color:#555; font-size:13px; margin:0 0 10px; }
.ok { color:var(--have); font-size:12px; }
.err { color:var(--gate); font-size:12.5px; white-space:pre-wrap; }
[hidden] { display:none !important; }
section { margin:0 0 22px; }
section.goal, section.new-dsp { border-top:1px solid var(--line); padding-top:14px; }
li { margin:3px 0; font-size:13.5px; }
"""

_JS = """
async function send(payload, el) {
  const box = el.closest('.f, .couple, tr') || document.body;
  const err = box.querySelector('.err');
  if (err) err.textContent = '';
  el.disabled = true;
  try {
    const r = await fetch('/save', {method:'POST', headers:{'Content-Type':'application/json'},
                                    body: JSON.stringify(payload)});
    const out = await r.json();
    if (!r.ok) throw new Error(out.error || r.statusText);
    location.reload();
  } catch (e) {
    el.disabled = false;
    if (err) err.textContent = String(e.message || e);
    else alert(e.message || e);
  }
}
function valueOf(box) {
  const multi = box.querySelectorAll('input[type=checkbox]');
  if (multi.length) return [...multi].filter(c => c.checked).map(c => c.value);
  const radios = box.querySelectorAll('input[type=radio]');
  if (radios.length) { const on = [...radios].find(r => r.checked); return on ? on.value : null; }
  const one = box.querySelector('select, input[type=text]');
  return one ? one.value : null;
}
function saveField(id, el) { send({field:id, value: valueOf(el.closest('.f'))}, el); }
function saveGroupOf(sel, kind, el) {
  const out = {};
  document.querySelectorAll(sel).forEach(i => { if (i.value !== '') out[i.dataset.k] = i.value; });
  send({[kind]: out}, el);
}
let pickedCar = null;
function pickCar(sel) {
  const o = sel.selectedOptions[0];
  pickedCar = o && o.value !== '' ? {make:o.dataset.make, model:o.dataset.model,
                                      generation:o.dataset.generation, body:o.dataset.body} : null;
  if (pickedCar) document.querySelectorAll('.car-part').forEach(i => {
    if (i.dataset.k in pickedCar) i.value = pickedCar[i.dataset.k]; });
  carEdited();
}
function carEdited() {
  const hint = document.getElementById('car-new');
  if (!hint) return;
  const differs = pickedCar && [...document.querySelectorAll('.car-part')].some(
    i => i.dataset.k in pickedCar && i.value !== pickedCar[i.dataset.k]);
  hint.hidden = !differs;
}
function showNewDsp(on) {
  const sec = document.getElementById('new-dsp'); if (sec && on) sec.hidden = false;
  const h = document.getElementById('dsp-new-hint'); if (h) h.hidden = !on;
}
function pickVendor(sel) {
  const other = sel.value === '__other__';
  document.getElementById('dsp-vendor-free').hidden = !other;
  const model = document.getElementById('dsp-model');
  [...model.options].forEach(o => { if (o.dataset.vendor) o.hidden = o.dataset.vendor !== sel.value; });
  model.value = other ? '__other__' : '';
  pickModel(model);
}
function pickModel(sel) {
  const other = sel.value === '__other__';
  document.getElementById('dsp-model-free').hidden = !other;
  showNewDsp(other);
}
function saveDsp(el) {
  const v = document.getElementById('dsp-vendor'), m = document.getElementById('dsp-model');
  const vendor = v.value === '__other__' ? document.getElementById('dsp-vendor-free').value : v.value;
  const model = m.value === '__other__' ? document.getElementById('dsp-model-free').value : m.value;
  send({dsp: {vendor, model}}, el);
}
function saveGoal(el) {
  const choices = [...document.querySelectorAll('.goal-pick')].filter(c => c.checked).map(c => c.value);
  send({goal: {choices, text: document.getElementById('goal-text').value}}, el);
}
function saveTiers(el) { send({dsp_tiers: valueOf(el.closest('.f'))}, el); }
window.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.car-part').forEach(i => i.addEventListener('input', carEdited));
});
function saveRow(kind, tr, el) {
  const out = {};
  tr.querySelectorAll('input, select').forEach(i => { if (i.dataset.k && i.value !== '') out[i.dataset.k] = i.value; });
  send({[kind]: out}, el);
}
"""


def _esc(text):
    return html.escape("" if text is None else str(text), quote=True)


#: Up to this many choices are shown as radio buttons — all of them visible at once; more is a list.
RADIO_MAX = 6


def _choice(f, value, ui, cls="", key=""):
    """The control for one answer: radios, a list, checkboxes, or a text box with suggestions.

    A default is PRE-SELECTED when nothing is on disk yet, and says so — the person changes it only
    if theirs differs. It is not written until he presses the button: a shown default is a question
    already answered for him, a silently stored one would be an answer he never gave.
    """
    data = f' data-k="{_esc(key)}"' if key else ""
    klass = f' class="{cls}"' if cls else ""
    if isinstance(value, (list, tuple)):
        chosen = [str(v) for v in value]
        value = ",".join(chosen)
    else:
        chosen = str(value).split(",") if value not in (None, "") else []
    current = value if value not in (None, "") else ("" if f["default"] is None else str(f["default"]))
    if f["options"] and f["multi"]:
        return "<div>" + "".join(
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
    listed = ""
    if f["suggest"]:
        dl = f'dl-{f["id"]}'
        listed = (f' list="{_esc(dl)}" placeholder="{_esc(ui.get("pick_or_type", "pick or type"))}"'
                  f'><datalist id="{_esc(dl)}">'
                  + "".join(f'<option value="{_esc(v)}">{_esc(t)}</option>' if t != v
                            else f'<option value="{_esc(v)}">' for v, t in f["suggest"])
                  + "</datalist")
    return f'<input type="text"{klass}{data} value="{_esc(value or "")}"{listed}>'


def _default_hint(f, ui):
    if f["default"] is None or f["value"] not in (None, ""):
        return ""
    shown = dict(f["options"]).get(str(f["default"]), str(f["default"]))
    return (f'<div class="meta hint">{_esc(ui.get("default_hint", "pre-selected"))}: '
            f'<b>{_esc(shown)}</b></div>')


def _control(f, ui):
    """The input for one field — or the honest note that this form does not write it."""
    if f["id"] == "dsp.tiers":            # the one profile question the page writes (new DSP only)
        return (f'<div class="row">{_choice(f, _draft_tiers(f), ui)}'
                f'<button class="save" onclick="saveTiers(this)">{_esc(ui.get("save", "Save"))}</button>'
                f'</div><div class="err"></div>')
    if f["probe"]:
        return (f'<div class="meta">🔎 {_esc(ui.get("probe", "probed, not asked"))}'
                + (f' — {_esc(f["derive"])}' if f["derive"] else "") + "</div>")
    writes = f["writes"] or ""
    if writes.startswith("dsp_profile.draft:"):
        return (f'<div class="meta">{_esc(ui.get("dsp_profile_note", ""))} — '
                f'<code>{_esc(writes.split(":", 1)[1])}</code></div>')
    if writes.startswith("glossary:"):
        return f'<div class="meta">{_esc(ui.get("glossary_note", ""))}</div>'
    if f["per"]:
        key = "per_" + f["per"]
        return f'<div class="meta">↳ {_esc(ui.get(key, f["per"]))}</div>'
    if not writes:
        choices = f["options"] or f["suggest"]
        return ((f'<div class="meta">{_esc(ui.get("choices", "choices"))}: '
                 + ", ".join(_esc(t) for _v, t in choices) + "</div>" if choices else "")
                + f'<div class="meta">{_esc(ui.get("prose_note", ""))}</div>')
    return (f'<div class="row">{_choice(f, f["value"], ui)}'
            f'<button class="save" onclick="saveField(\'{_esc(f["id"])}\', this)">'
            f'{_esc(ui.get("save", "Save"))}</button></div>{_default_hint(f, ui)}<div class="err"></div>')


def _draft_tiers(f):
    return f.get("draft_tiers") or []


def _field_html(f, ui):
    mark = (f' <span class="meta">({_esc(ui.get("required", "required"))})</span>'
            if f["required"] and f["place"] == "now" else "")
    return (f'<div class="f s-{f["state"]}" id="f-{_esc(f["id"])}">'
            f'<div class="q"><span class="dot d-{f["state"]}"></span>{_esc(f["ask"])}{mark}</div>'
            f'<div class="meta"><code>{_esc(f["id"])}</code> · '
            f'<span class="en">{_esc(f["ask_en"])}</span></div>'
            f'{_control(f, ui)}</div>')


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
            f'data-generation="{_esc(c["generation"])}" data-body="{_esc(c["body"])}">'
            f'{_esc(c["label"])} · {_esc(src_label.get(c["source"]) or c["source"].replace("project:", ui.get("car_src_project", "project") + " "))}'
            f'</option>' for i, c in enumerate(m["cars"]))
        pick = (f'<div class="f" id="car-pick-box"><div class="q">{_esc(ui.get("car_pick", "Pick a known car"))}</div>'
                f'<div class="row"><select id="car-pick" onchange="pickCar(this)">'
                f'<option value="">{_esc(ui.get("car_pick_none", "— type it below —"))}</option>{opts}</select></div>'
                f'<div class="meta">{_esc(ui.get("car_pick_src", ""))}</div>'
                f'<div class="meta hint" id="car-new" hidden>{_esc(ui.get("car_edited", "edited: this is a new car"))}</div></div>')
    inputs = []
    for key, fid in CAR_PARTS:
        f = next((x for x in fields if x["id"] == fid), None)
        if not f:
            continue
        value = "" if f["value"] is None else str(f["value"])
        inputs.append(f'<div class="f s-{f["state"]}" id="f-{_esc(fid)}"><div class="q">'
                      f'<span class="dot d-{f["state"]}"></span>{_esc(f["ask"])}</div>'
                      f'<div class="row">{_choice(f, value, ui, cls="car-part", key=key)}</div></div>')
    couple = m["couplings"].get("car_identity", {})
    return (f'<div class="couple"><div class="t">{_esc(couple.get("title", "car"))}</div>{pick}'
            + "".join(inputs)
            + f'<div class="row"><button class="save" '
              f'onclick="saveGroupOf(\'.car-part\', \'car\', this)">'
              f'{_esc(ui.get("save", "Save"))}</button></div><div class="err"></div></div>')


def _dsp_block(m, fields):
    """Vendor, then model — the models offered are ONLY that vendor's (the Arbiter, 2026-09-22).

    The list is the skill's own DSP library (`intake.known_dsps`). "Another" opens two text boxes,
    and a processor the library does not describe is a NEW processor: its base questions are asked
    once, in their own step, and only then.
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
                     f'{"" if d["vendor"] == v_sel else " hidden"}>{_esc(d["model"])}</option>'
                     for d in m["dsps"])
    free_v = "" if v_sel != other else dsp["vendor"]
    free_m = "" if m_sel != other else dsp["model"]
    ids = "".join(f'<span id="f-{fid}"></span>' for fid in ("dsp.vendor", "dsp.model"))
    state = "have" if dsp["vendor"] and dsp["model"] else "gate"
    return (f'<div class="couple" id="dsp-box">{ids}<div class="t">{_esc(m["couplings"]["dsp_identity"]["title"])}</div>'
            f'<div class="f s-{state}"><div class="q"><span class="dot d-{state}"></span>'
            f'{_esc(next(f["ask"] for f in fields if f["id"] == "dsp.vendor"))} '
            f'<span class="meta">({_esc(ui.get("required", "required"))})</span></div>'
            f'<div class="row"><select id="dsp-vendor" onchange="pickVendor(this)"><option value="">—</option>{v_opts}'
            f'<option value="{other}"{" selected" if v_sel == other else ""}>{_esc(ui.get("dsp_other_vendor", "another vendor"))}</option></select>'
            f'<input type="text" id="dsp-vendor-free" value="{_esc(free_v)}"{"" if v_sel == other else " hidden"}></div></div>'
            f'<div class="f s-{state}"><div class="q"><span class="dot d-{state}"></span>'
            f'{_esc(next(f["ask"] for f in fields if f["id"] == "dsp.model"))}</div>'
            f'<div class="row"><select id="dsp-model" onchange="pickModel(this)"><option value="">—</option>{m_opts}'
            f'<option value="{other}"{" selected" if m_sel == other else ""}>{_esc(ui.get("dsp_other_model", "another model"))}</option></select>'
            f'<input type="text" id="dsp-model-free" value="{_esc(free_m)}"{"" if m_sel == other else " hidden"}></div></div>'
            f'<div class="meta hint" id="dsp-new-hint"{"" if dsp["new"] else " hidden"}>{_esc(ui.get("dsp_new_hint", "a new processor"))}</div>'
            f'<div class="row"><button class="save" onclick="saveDsp(this)">{_esc(ui.get("save", "Save"))}</button></div>'
            f'<div class="err"></div></div>')


def _goal_block(m, fields):
    """What the tune is for — ONE optional control: EMMA / AYA / for yourself / other + words.

    The Arbiter's shape (2026-09-22). The ticks map onto the method's keys on the way in:
    EMMA/AYA are `goal.formats`, a format means competition, "for yourself" is enjoyment, both is
    both; the words go to `goal.wishes`.
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
    return (f'<div class="f s-{state}" id="goal-box">{ids}<div class="q"><span class="dot d-{state}"></span>'
            f'{_esc(ui.get("goal_ask", "What is the tune for?"))}</div>'
            f'<div>{boxes}</div><div class="row"><input type="text" id="goal-text" value="{_esc(wishes)}" '
            f'placeholder="{_esc(ui.get("goal_text", "in your own words"))}"></div>'
            f'<div class="row"><button class="save" onclick="saveGoal(this)">{_esc(ui.get("save", "Save"))}</button></div>'
            f'<div class="err"></div></div>')


def _cell(c, raw, ui):
    """One table cell: a list for a closed set, a text box with suggestions for an open one."""
    leaf = c["id"].split(".", 1)[1]
    value = "" if raw is None else str(raw)
    if isinstance(raw, bool):
        value = "yes" if raw else "no"
    return f'<td>{_choice(c, value, ui, key=leaf)}</td>'


def _table(m, per, rows, kind, key_field, cols, add=True):
    """The per-entity half: questions per channel are a table, never 12 × N controls.

    `cols` are the columns THIS section asks; a later section shows the same rows with its own
    columns and carries the key in a hidden input, so a row is always saved against its code.
    """
    ui = m["ui"]
    head = "".join(f'<th title="{_esc(c["ask_en"])}" id="f-{_esc(c["id"])}">{_esc(c["ask"])}<br>'
                   f'<code style="font-size:10px">{_esc(c["id"].split(".", 1)[1])}</code></th>'
                   for c in cols)
    keyed = any(c["id"].split(".", 1)[1] == key_field for c in cols)
    body = []
    for row in rows + ([{}] if add else []):
        cells = []
        for c in cols:
            leaf = c["id"].split(".", 1)[1]
            raw = row.get(leaf)
            if isinstance(raw, dict) and "make" not in leaf:
                raw = project.fact_value(raw) if project.is_fact(raw) else ""
            if leaf in ("driver_make", "driver_model"):
                raw = ((row.get("driver") or {}) or {}).get(leaf.split("_", 1)[1], "")
            cells.append(_cell(c, raw, ui))
        hidden = ("" if keyed or not row.get(key_field) else
                  f'<input type="hidden" data-k="{_esc(key_field)}" value="{_esc(row.get(key_field))}">')
        label = _esc(row.get(key_field) or ui.get("add_row", "+"))
        body.append(f'<tr><th>{label}{hidden}</th>{"".join(cells)}'
                    f'<td><button class="save" onclick="saveRow(\'{kind}\', this.closest(\'tr\'), this)">'
                    f'{_esc(ui.get("save", "Save"))}</button><div class="err"></div></td></tr>')
    if not body:
        return (f'<div class="note">{_esc(ui.get("rows_first", "fill in the channels first"))}<ul>'
                + "".join(f'<li id="f-{_esc(c["id"])}">{_esc(c["ask"])}</li>' for c in cols)
                + "</ul></div>")
    return (f'<div style="overflow-x:auto"><table><tr><th></th>{head}<th></th></tr>'
            + "".join(body) + "</table></div>")


def _section(m, rows, ui, add_rows):
    """One place's questions, in the table's group order — couples kept whole, tables for rows."""
    out, done, heading = [], set(), None
    titles = {g["id"]: g["title"] for g in m["groups"]}
    specials = {"car": _car_block, "dsp_identity": _dsp_block, "purpose": _goal_block}
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
            if f["couple"] in ("dsp_identity", "purpose"):
                out.append(specials[f["couple"]](m, m["fields"]))
                done |= {x["id"] for x in rows if x["couple"] == f["couple"]} | (
                    {"goal.wishes"} if f["couple"] == "purpose" else set())
                continue
            if f["per"] in ("channel", "amp"):
                cols = [c for c in rows if c["per"] == f["per"]]
                data = m["rows"]["channels" if f["per"] == "channel" else "amps"]
                key = "code" if f["per"] == "channel" else "model"
                out.append(_table(m, f["per"], data, f["per"], key, cols, add=add_rows))
                done |= {c["id"] for c in cols}
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


def _memo(m, rows, ui):
    """What the page does NOT ask — a cheat-sheet, grouped by who answers it and when."""
    whens = {w["id"]: w["title"] for w in m["when"]}
    auto = [f for f in rows if f["probe"]]
    later = [f for f in rows if not f["probe"]]
    out = [f'<h3>{_esc(ui.get("memo_auto", "a tool or the profile answers these"))}</h3><ul>']
    out += [f'<li id="f-{_esc(f["id"])}">{_esc(f["ask"])} — <span class="meta">{_esc(f["derive"])}</span></li>'
            for f in auto]
    out.append(f'</ul><h3>{_esc(ui.get("memo_later", "the session asks when the step comes"))}</h3><ul>')
    out += [f'<li id="f-{_esc(f["id"])}">{_esc(f["ask"])} — <span class="meta">{_esc(whens.get(f["when"], f["when"]))}</span></li>'
            for f in later]
    return "".join(out) + "</ul>"


def render(m):
    """One self-contained page: no CDN, no font, no network — it must open on a car's laptop.

    Open on the page: what starting to measure needs, and the optional goal. A new processor's base
    questions appear only for a new processor; the drivers and other hardware are an optional fold;
    everything else is a memo, not a question.
    """
    ui = m["ui"]
    t = m["totals"]
    fields = m["fields"]
    for f in fields:
        if f["id"] == "dsp.tiers" and m["dsp"]["source"] == "draft":
            f["draft_tiers"] = m["dsp"]["tiers"]
    chips = (f'<span class="chip"><span class="dot d-gate"></span>'
             f'{_esc(ui.get("legend_now", "to answer now"))} <b>{t["now_open"]}</b> / {t["now"]}</span>'
             f'<span class="chip"><span class="dot d-have"></span>'
             f'{_esc(ui.get("legend_green", "answered"))} <b>{t["have"]}</b></span>'
             f'<span class="chip"><span class="dot d-prose"></span>'
             f'{_esc(ui.get("legend_memo", "not asked"))} <b>{t["memo"]}</b></span>')
    gate = m["gate"]
    verdict = (f'<span class="gate-ok">{_esc(ui.get("gate_open", "gate open"))}</span>'
               if gate["open"] else
               f'<span class="gate-shut">{_esc(ui.get("gate_shut", "gate shut"))}</span>'
               + (f' — {_esc(ui.get("gate_missing", "missing"))}: '
                  f'{_esc(", ".join(gate["missing_files"]))}' if gate["missing_files"] else ""))

    def place(p):
        return [f for f in fields if f["place"] == p]

    parts = [f'<section class="now"><h2>{_esc(ui.get("now_title", "Now"))}</h2>'
             f'<p class="why">{_esc(ui.get("now_why", ""))}</p>'
             + _section(m, place("now"), ui, add_rows=True) + "</section>"]
    parts.append(f'<section class="goal"><h2>{_esc(ui.get("goal_title", "Goal and music"))}</h2>'
                 f'<p class="why">{_esc(ui.get("goal_why", ""))}</p>'
                 + _section(m, place("goal"), ui, add_rows=False) + "</section>")
    parts.append(f'<section class="new-dsp" id="new-dsp"{"" if m["dsp"]["new"] else " hidden"}>'
                 f'<h2>{_esc(ui.get("new_dsp_title", "New processor"))}</h2>'
                 f'<p class="why">{_esc(ui.get("new_dsp_why", ""))}</p>'
                 # Here nothing is derived: the library has no profile of THIS processor, so the
                 # base questions are put to the person, once.
                 + "".join(_field_html(dict(f, probe=False), ui) for f in place("new_dsp"))
                 + "</section>")
    equipment = place("equipment")
    table_cols = [f for f in equipment if f["per"] == "channel"]
    body = (_table(m, "channel", m["rows"]["channels"], "channel", "code", table_cols, add=False)
            + "".join(_field_html(f, ui) for f in equipment if f["per"] != "channel"))
    parts.append(f'<details id="equipment"><summary>{_esc(ui.get("equipment_title", "Other equipment"))}'
                 f' <span class="n">{len(equipment)}</span></summary>'
                 f'<p class="why">{_esc(ui.get("equipment_why", ""))}</p>{body}</details>')
    parts.append(f'<details id="memo"><summary>{_esc(ui.get("memo_title", "Memo"))}'
                 f' <span class="n">{t["memo"]}</span></summary>{_memo(m, place("memo"), ui)}</details>')

    return (
        "<!doctype html><html lang=\"" + _esc(m["lang"]) + "\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        f"<title>{_esc(ui.get('title', 'Intake'))}</title><style>{_CSS}</style></head><body>"
        f"<header><h1>{_esc(ui.get('title', 'Intake'))}</h1>"
        f"<div class=\"sub\">{_esc(ui.get('subtitle', ''))}</div>"
        f"<div class=\"dir\">{_esc(m['project_dir'])}</div>"
        f"<div class=\"chips\">{chips}<span class=\"chip\">{verdict}</span>"
        f"<span class=\"chip\"><code>{_esc(gate['command'])}</code></span></div></header>"
        f"<main>{''.join(parts)}</main>"
        f"<script>{_JS}</script></body></html>"
    )


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
    if "field" in payload:
        value = payload.get("value")
        if isinstance(value, list):
            if not value:
                raise intake.IntakeError("nothing chosen — nothing was written")
        elif value in (None, ""):
            raise intake.IntakeError("порожнє значення — нічого не записано")
        return {"field": payload["field"],
                "value": intake.save(project_dir, payload["field"], _coerce(payload["field"], value))}

    if "dsp" in payload:
        # Vendor and model are ONE identity: both or nothing, written together.
        row = payload["dsp"]
        vendor, model_ = (row.get("vendor") or "").strip(), (row.get("model") or "").strip()
        if not (vendor and model_):
            raise intake.IntakeError("the DSP is a vendor AND a model — nothing was written")
        intake.save(project_dir, "dsp.vendor", vendor)
        intake.save(project_dir, "dsp.model", model_)
        return {"dsp": intake.dsp_state(project_dir)}

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

    if "dsp_tiers" in payload:
        # A NEW processor's tiers go into the interview draft through the profile's own writer;
        # a group the draft already has keeps what was answered about it.
        chosen = [t for t in (payload["dsp_tiers"] or []) if t]
        if not chosen:
            raise intake.IntakeError("nothing chosen — nothing was written")
        dsp = intake.dsp_state(project_dir)
        if not dsp["new"]:
            raise intake.IntakeError("the tiers are read off the processor's profile; they are asked "
                                     "only for a new processor — nothing was written")
        data = dsp_profile.start_draft(project_dir, dsp["vendor"], dsp["model"])
        have = {g.get("id"): g for g in dsp_profile._unwrap(data).get("groups") or []}
        names = {"channels": "Output channels", "virtual_channels": "Virtual channels", "inputs": "Inputs"}
        groups = []
        for t in chosen:
            gid = "physical_outputs" if t == "channels" else t
            groups.append(have.get(gid) or {"id": gid, "label": names.get(t, t), "fields": None,
                                            "max_count": None})
        dsp_profile.set_field(project_dir, "groups", groups)
        return {"dsp_tiers": chosen}

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
        driver = {k: row.pop(f"driver_{k}") for k in ("make", "model") if f"driver_{k}" in row}
        if driver:
            row["driver"] = driver
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

        # ── the page: every field on it, no network, and the couples kept whole ──────────────
        page = render(m)
        for fid in ids:
            assert f"f-{fid}" in page or fid in page, f"{fid} is not on the page"
        external = re.findall(r"""(?:src|href)=["']https?://""", page)
        assert not external, f"the page reaches the network: {external[:3]}"
        assert "Якою мовою відповідати" in page, "the Ukrainian labels did not reach the page"
        assert m["couplings"]["seat"]["fields"] == ["car.drive_side", "goal.reference_seat"], \
            m["couplings"]["seat"]

        # ── the Arbiter's review, 2026-09-22 ─────────────────────────────────────────────────
        now_html = page.split("</section>", 1)[0]
        for fid in ("goal.reference_seat", "car.drive_side", "channel_map.code", "rew.loopback",
                    "dsp.vendor", "dsp.tiers_used"):
            assert f"f-{fid}" in now_html, f"{fid} is needed to start measuring and is not up front"
        # Not asked at all: the solo question, the mic, the signal chain, the clip check.
        memo = page.split('id="memo"', 1)[1]
        for fid in ("dsp.per_channel_measurable", "rew.mic_model", "rew.mic_cal_0", "source.kind",
                    "source.listening_input", "dsp.measurement_input", "rew.input_clip_checked",
                    "amps.make", "target_curve.tone"):
            assert f"f-{fid}" not in now_html and f'<li id="f-{fid}"' in memo, f"{fid} is asked"
        # The seat and the drive side are ONE control although they live in two groups.
        couple = now_html.split('id="f-car.drive_side"', 1)[1].split('<div class="couple">', 1)[0]
        assert 'id="f-goal.reference_seat"' in couple, "the seat couple was split"
        # A default is pre-selected, not written.
        assert 'name="r-car.drive_side" value="LHD" checked' in page, "the default is not pre-selected"
        assert "drive_side" not in (project.Project(root).load().get("car") or {}), \
            "a default was stored behind the person's back"
        # The car list is what the skill has seen, and a known car fills the four parts.
        assert 'data-make="VW" data-model="Passat" data-generation="B8" data-body="sedan"' in page
        # The DSP: a model is offered under ITS vendor only, so Musway + Helix cannot be picked.
        for d in intake.known_dsps():
            assert f'value="{_esc(d["model"])}" data-vendor="{_esc(d["vendor"])}"' in page, d
        # No processor chosen: the new-processor step exists but is not shown.
        assert '<section class="new-dsp" id="new-dsp" hidden>' in page
        # The goal is one optional control; the curve question is the Arbiter's words.
        assert 'class="goal-pick" value="EMMA"' in page and "Яка цільова крива?" in page
        assert 'value="chesky"' in page and 'value="jazz"' in page, "libraries/genres are not checkboxes"

        apply_save(root, {"dsp": {"vendor": "Audiotec-Fischer", "model": "Helix DSP Ultra S"}})
        m2 = model(root, "uk")
        tiers = next(f for f in m2["fields"] if f["id"] == "channel_map.tier")["options"]
        assert [v for v, _ in tiers] == ["virtual_channels", "channels", "inputs"], tiers
        assert '<section class="new-dsp" id="new-dsp" hidden>' in render(m2), "a known DSP is not new"
        apply_save(root, {"field": "dsp.tiers_used", "value": ["channels"]})
        tiers = next(f for f in model(root, "uk")["fields"] if f["id"] == "channel_map.tier")["options"]
        assert [v for v, _ in tiers] == ["channels"], "the tiers in use do not narrow the row's choice"
        try:
            apply_save(root, {"dsp_tiers": ["channels"]})
            raise AssertionError("a known processor's tiers were overwritten from the form")
        except intake.IntakeError as exc:
            assert "new processor" in str(exc), exc
        apply_save(root, {"dsp": {"vendor": "Acme", "model": "X8"}})
        m3 = model(root, "uk")
        assert m3["dsp"]["new"] is True and '<section class="new-dsp" id="new-dsp">' in render(m3)
        apply_save(root, {"dsp_tiers": ["channels", "virtual_channels"]})
        assert intake.dsp_state(root)["tiers"] == ["channels", "virtual_channels"], intake.dsp_state(root)
        tiers = next(f for f in model(root, "uk")["fields"] if f["id"] == "channel_map.tier")["options"]
        assert [v for v, _ in tiers] == ["channels"], tiers   # still narrowed by what is in use
        # The goal ticks map onto the method's keys.
        apply_save(root, {"goal": {"choices": ["EMMA", "enjoyment", "other"], "text": "clear nav"}})
        goal = project.Project(root).load()["goal"]
        assert goal == {"formats": ["EMMA"], "purpose": "both", "wishes": "clear nav"}, goal

        # ── writing back goes through the method's writers, refusals included ────────────────
        apply_save(root, {"field": "rew.loopback", "value": "acoustic"})
        assert project.Project(root).load()["measurement"]["loopback"] == "acoustic"
        # An enumerated rate posted as TEXT must land as the number the table holds.
        apply_save(root, {"field": "rew.capture_rate_hz", "value": "96000"})
        assert project.Project(root).load()["measurement"]["sample_rate_hz"] == 96000
        apply_save(root, {"channel": {"code": "w-L", "slot": "C", "tier": "channels",
                                      "driver_make": "GZ", "driver_model": "GZUW", "fs_hz": "52.4"}})
        row = next(c for c in project.Project(root).load()["channels"] if c["code"] == "w-L")
        assert row["driver"] == {"make": "GZ", "model": "GZUW"}, row
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

        # ── a missing translation is a fallback, never a crash ──────────────────────────────
        page_en = render(model(root, "xx"))
        assert intake.FIELDS[0]["ask"] in page_en, "the English fallback did not render"

    print(f"selftest OK (intake_form) — {len(ids)} fields render from one table, uk.json covers "
          f"every one of them, the page carries no network reference, and every write goes through "
          f"intake's own writers")
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
        page = render(model(project_dir, lang))
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
