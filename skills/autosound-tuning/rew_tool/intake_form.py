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
        fields.append({
            "id": f["id"], "group": f["group"], "ask": _ask(lab, f), "ask_en": f["ask"],
            "required": f["required"], "multi": f["multi"], "per": f["per"],
            "couple": f["ask_with"], "writes": f["writes"], "lands": f["lands"],
            "options": _options(lab, f), "state": st,
            "value": _value_of(f, data, project_dir), "probe": auto,
            "when": f["when"], "default": default, "suggest": _suggestions(lab, f),
            "derive": _derive(lab, f) if auto else None,
        })

    gate = intake.gate_requirements(project_dir)
    groups = []
    for gid, why in intake.GROUPS:
        rows = [f for f in fields if f["group"] == gid]
        groups.append({
            "id": gid, "title": lab["groups"].get(gid) or gid, "why": why,
            "count": len(rows),
            "gate": sum(1 for r in rows if r["state"] == GATE),
            "nice": sum(1 for r in rows if r["state"] == NICE),
            "have": sum(1 for r in rows if r["state"] == HAVE),
        })
    whens = [{"id": w, "what": what, "title": (lab.get("when") or {}).get(w) or what,
              "count": sum(1 for f in fields if f["when"] == w)}
             for w, what in intake.WHEN]
    asked_now = [f for f in fields if f["when"] == "now" and not f["probe"]]
    return {
        "project_dir": project_dir, "lang": lab.get("lang", lang), "ui": lab["ui"],
        "when": whens,
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
                   # What the page puts in front of the person now, and how much of it is a choice.
                   "now": len(asked_now),
                   "now_open": sum(1 for f in asked_now if f["state"] != HAVE),
                   "now_choice": sum(1 for f in asked_now if f["options"] or f["suggest"]),
                   "auto": sum(1 for f in fields if f["when"] == "now" and f["probe"]),
                   "later": sum(1 for f in fields if f["when"] != "now")},
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
    current = value if value not in (None, "") else ("" if f["default"] is None else str(f["default"]))
    if f["options"] and f["multi"]:
        chosen = value.split(",") if value else []
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
        # Prose: the session asks it. The choices it will offer are shown, so the question is
        # never a blank box — and the page still does not pretend to store the answer.
        choices = f["options"] or f["suggest"]
        return ((f'<div class="meta">{_esc(ui.get("choices", "choices"))}: '
                 + ", ".join(_esc(t) for _v, t in choices) + "</div>" if choices else "")
                + _default_hint(f, ui)
                + f'<div class="meta">{_esc(ui.get("prose_note", ""))}</div>')
    value = "" if f["value"] is None else str(f["value"])
    return (f'<div class="row">{_choice(f, value, ui)}'
            f'<button class="save" onclick="saveField(\'{_esc(f["id"])}\', this)">'
            f'{_esc(ui.get("save", "Save"))}</button></div>{_default_hint(f, ui)}<div class="err"></div>')


def _field_html(f, ui):
    mark = (f' <span class="meta">({_esc(ui.get("required", "required"))})</span>'
            if f["required"] and f["when"] == "now" and not f["probe"] else "")
    return (f'<div class="f s-{f["state"]}" id="f-{_esc(f["id"])}">'
            f'<div class="q"><span class="dot d-{f["state"]}"></span>{_esc(f["ask"])}{mark}</div>'
            f'<div class="meta"><code>{_esc(f["id"])}</code> · '
            f'<span class="en">{_esc(f["ask_en"])}</span></div>'
            f'{_control(f, ui)}</div>')


CAR_PARTS = (("make", "car.make"), ("model", "car.model"), ("generation", "car.generation"),
             ("body", "car.body"), ("year", "car.year"))


def _car_block(m, fields):
    """`car_identity` is the one couple with a writer of its own: four parts or nothing."""
    ui = m["ui"]
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
    return (f'<div class="couple"><div class="t">{_esc(couple.get("title", "car"))}</div>'
            + "".join(inputs)
            + f'<div class="row"><button class="save" '
              f'onclick="saveGroupOf(\'.car-part\', \'car\', this)">'
              f'{_esc(ui.get("save", "Save"))}</button></div><div class="err"></div></div>')


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
        # No rows yet: say which questions will be asked of each one, rather than an empty grid.
        return (f'<div class="note">{_esc(ui.get("rows_first", "fill in the channels first"))}<ul>'
                + "".join(f'<li id="f-{_esc(c["id"])}">{_esc(c["ask"])}'
                          + (f' — {_esc(", ".join(t for _v, t in (c["options"] or c["suggest"])))}'
                             if c["options"] or c["suggest"] else "") + "</li>" for c in cols)
                + "</ul></div>")
    return (f'<div style="overflow-x:auto"><table><tr><th></th>{head}<th></th></tr>'
            + "".join(body) + "</table></div>")


def _section(m, rows, ui, add_rows):
    """One step's questions, in the table's group order — couples kept whole, tables for rows.

    A couple is rendered where its FIRST member falls, with every member this step asks, even
    across groups: the seat and the drive side are one control although they live in two groups.
    Two fields that write the SAME key are one question and are shown once.
    """
    out, done, seen_writes, heading = [], set(), {}, None
    by_group = {gid: [f for f in rows if f["group"] == gid] for gid, _ in intake.GROUPS}
    titles = {g["id"]: g["title"] for g in m["groups"]}
    for gid, _why in intake.GROUPS:
        for f in by_group[gid]:
            if f["id"] in done:
                continue
            if heading != gid:
                out.append(f'<h3>{_esc(titles.get(gid, gid))}</h3>')
                heading = gid
            if f["id"] in dict(CAR_PARTS).values():
                out.append(_car_block(m, rows))
                done |= set(dict(CAR_PARTS).values())
                continue
            if f["per"] in ("channel", "amp"):
                cols = [c for c in rows if c["per"] == f["per"]]
                data = m["rows"]["channels" if f["per"] == "channel" else "amps"]
                key = "code" if f["per"] == "channel" else "model"
                out.append(_table(m, f["per"], data, f["per"], key, cols,
                                  add=add_rows or f["per"] == "amp"))
                done |= {c["id"] for c in cols}
                continue
            writes = f["writes"]
            if writes and writes in seen_writes:
                out.append(f'<div class="meta" id="f-{_esc(f["id"])}">↳ <code>{_esc(f["id"])}</code> = '
                           f'<code>{_esc(seen_writes[writes])}</code></div>')
                done.add(f["id"])
                continue
            mates, twins = [], []
            for x in rows:
                if not f["couple"] or x["couple"] != f["couple"] or x["id"] in done or x["per"]:
                    continue
                first = next((y for y in mates if x["writes"] and y["writes"] == x["writes"]), None)
                (twins if first else mates).append(x)
            if len(mates) >= 2:
                couple = m["couplings"].get(f["couple"], {})
                out.append(f'<div class="couple"><div class="t">{_esc(couple.get("title", ""))}</div>'
                           + "".join(_field_html(x, ui) for x in mates)
                           + "".join(f'<div class="meta" id="f-{_esc(x["id"])}">↳ <code>{_esc(x["id"])}'
                                     f'</code> = <code>{_esc(next(y["id"] for y in mates if y["writes"] == x["writes"]))}'
                                     f'</code></div>' for x in twins)
                           + "</div>")
                done |= {x["id"] for x in mates + twins}
                seen_writes.update({x["writes"]: x["id"] for x in mates if x["writes"]})
                continue
            out.append(_field_html(f, ui))
            done.add(f["id"])
            if writes:
                seen_writes[writes] = f["id"]
    return "".join(out)


def render(m):
    """One self-contained page: no CDN, no font, no network — it must open on a car's laptop.

    What starting to measure needs is open on the page; what a tool answers, and what a later
    step asks, is folded under a line that names that step — there to read, not in the way.
    """
    ui = m["ui"]
    t = m["totals"]
    chips = (f'<span class="chip"><span class="dot d-gate"></span>'
             f'{_esc(ui.get("legend_now", "to answer now"))} <b>{t["now_open"]}</b> / {t["now"]}</span>'
             f'<span class="chip"><span class="dot d-have"></span>'
             f'{_esc(ui.get("legend_green", "answered"))} <b>{t["have"]}</b></span>'
             f'<span class="chip"><span class="dot d-prose"></span>'
             f'{_esc(ui.get("legend_later", "asked later"))} <b>{t["later"]}</b></span>')
    gate = m["gate"]
    verdict = (f'<span class="gate-ok">{_esc(ui.get("gate_open", "gate open"))}</span>'
               if gate["open"] else
               f'<span class="gate-shut">{_esc(ui.get("gate_shut", "gate shut"))}</span>'
               + (f' — {_esc(ui.get("gate_missing", "missing"))}: '
                  f'{_esc(", ".join(gate["missing_files"]))}' if gate["missing_files"] else ""))

    fields = m["fields"]
    now = [f for f in fields if f["when"] == "now" and not f["probe"]]
    auto = [f for f in fields if f["when"] == "now" and f["probe"]]
    parts = [f'<section class="now"><h2>{_esc(ui.get("now_title", "Now"))}</h2>'
             f'<p class="why">{_esc(ui.get("now_why", ""))}</p>'
             + _section(m, now, ui, add_rows=True) + "</section>"]
    parts.append(f'<details><summary>{_esc(ui.get("auto_title", "the tool answers these"))}'
                 f' <span class="n">{len(auto)}</span></summary>'
                 + "".join(_field_html(f, ui) for f in auto) + "</details>")
    for w in m["when"]:
        if w["id"] == "now" or not w["count"]:
            continue
        rows = [f for f in fields if f["when"] == w["id"]]
        parts.append(f'<details id="w-{_esc(w["id"])}"><summary>'
                     f'{_esc(ui.get("later_prefix", "asked later"))} — {_esc(w["title"])}'
                     f' <span class="n">{len(rows)}</span></summary>'
                     + _section(m, rows, ui, add_rows=False) + "</details>")

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
        assert by_id["rew.mic_model"]["state"] == GATE, "a required, missing field is not red"
        assert by_id["car.year"]["state"] == NICE, "an optional, missing field is not yellow"
        assert by_id["goal.wishes"]["state"] == PROSE, "prose is not reported as prose"
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

        # ── short up front: only what measuring needs is open; the rest is folded, not gone ──
        assert 0 < t["now"] < t["all"] // 2, t
        now_html = page.split("</section>", 1)[0]
        for fid in ("rew.mic_model", "goal.reference_seat", "car.drive_side", "channel_map.code"):
            assert f"f-{fid}" in now_html, f"{fid} is needed to start measuring and is not up front"
        for fid in ("target_curve.tone", "channel_map.position", "amps.make", "rew.api_reachable"):
            assert f"f-{fid}" not in now_html and f"f-{fid}" in page, f"{fid} is up front, or gone"
        # The seat and the drive side are ONE control although they live in two groups.
        couple = now_html.split('id="f-car.drive_side"', 1)[1].split('<div class="couple">', 1)[0]
        assert 'id="f-goal.reference_seat"' in couple, "the seat couple was split"
        # A default is pre-selected, not written: the radio is checked, the project is untouched.
        assert 'name="r-car.drive_side" value="LHD" checked' in page, "the default is not pre-selected"
        assert by_id["car.drive_side"]["state"] != GATE, "a pre-selected default is not a red gap"
        assert "drive_side" not in (project.Project(root).load().get("car") or {}), \
            "a default was stored behind the person's back"
        assert 'name="r-project.language" value="uk" checked' in page, "the page language is the default"
        # One key written by two fields is ONE question on the page, not two.
        assert sum(f'class="meta" id="f-{x}"' in page
                   for x in ("dsp.measurement_input", "source.measurement_input")) == 1, \
            "a key written by two fields rendered as two questions"

        # ── writing back goes through the method's writers, refusals included ────────────────
        apply_save(root, {"field": "rew.loopback", "value": "physical"})
        assert project.Project(root).load()["measurement"]["loopback"] == "physical"
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
