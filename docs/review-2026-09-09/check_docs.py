#!/usr/bin/env python3
"""Check rew-tool-docs.md: every --flag and module.function named in a module's bullet exists in the module."""
import os, re, sys
SKILL = "/Users/o.yukhno/dev/autosound/skill/skills/autosound-tuning"
DOCS = os.path.join(SKILL, "references/tooling/rew-tool-docs.md")
DIRS = [os.path.join(SKILL, "rew_tool"), os.path.join(SKILL, "rew_tool/state"), os.path.join(SKILL, "rew_tool/gates"), os.path.join(SKILL, "scripts")]
def find(name):
    for d in DIRS:
        p = os.path.join(d, name)
        if os.path.isfile(p): return p
    return None
lines = open(DOCS, encoding="utf-8").read().splitlines()
# group top-level bullets: a bullet starts with "* **`rew_tool/X.py`" or "* **`rew_api.func"
bullets = []  # (lineno, module, text)
cur = None
for i, ln in enumerate(lines, 1):
    m = re.match(r"^\* \*\*`(?:rew_tool/)?([a-z_]+)(?:\.py)?[`.]", ln)
    if m:
        cur = [i, m.group(1) + ".py", ln]
        bullets.append(cur)
    elif cur and (ln.startswith("  ") or ln.startswith("\t")):
        cur[2] += "\n" + ln
    else:
        cur = None
FLAG = re.compile(r"`([^`]*--[a-z][\w-]*[^`]*)`")
FUNC = re.compile(r"`([a-z_][a-z0-9_]*)\.([a-zA-Z_][A-Za-z0-9_]*)(?:\(|`|\b)")
BARE = re.compile(r"`([a-z_][a-z0-9_]{3,})(?:\([^`]*\))?`")
probs = []
for ln, mod, text in bullets:
    path = find(mod)
    if not path:
        probs.append(f"L{ln}: bullet names {mod} which does not exist"); continue
    src = open(path, encoding="utf-8", errors="replace").read()
    # flags inside backticks in this bullet -> must be in THIS module (or in rew_tool.py for the rew_tool bullet)
    for tok in FLAG.findall(text):
        for fl in set(re.findall(r"--[a-z][\w-]*", tok)):
            if fl not in src:
                probs.append(f"L{ln}: {mod} has no flag {fl} (from `{tok[:60]}`)")
    # module.function tokens -> must be def/class in that module
    for m2, fn in FUNC.findall(text):
        p2 = find(m2 + ".py")
        if not p2 or fn in ("py","md","json","cs","sh"): continue
        s2 = open(p2, encoding="utf-8", errors="replace").read()
        if not re.search(rf"^\s*(def|class)\s+{re.escape(fn)}\b|^{re.escape(fn)}\s*=", s2, re.M):
            probs.append(f"L{ln}: {m2}.py has no `{fn}`")
    # bare backticked identifiers in this bullet that look like function names -> check in this module (report only if absent everywhere)
    for name in set(BARE.findall(text)):
        if name in ("selftest","stdlib","numpy","scipy","hypothesis","evidence","symptom","notes","title","uuid","status","proposed","enabled","bypass","zone","true","false","full","per_band","freq","mag","phase","gate","steady","raw","bare","unknown","none","virtual","generic","field","desk","check","yes","no","comparable","agree","sweep","rta","impedance","exists","valid","applicable","kind","issues","stats","name","first","short","league","routes","tracks","links","characteristics","delay","reference","offset_s","has_ir","ir_start_s","ir_peak_s","sample_rate","start_freq","end_freq","notes_offset_s","notes_agrees","rewSource","protectiveHighPass","protectiveState","protectiveSource","smoothing","window_spec","window","all_plus_c","lr_delta","shared_band","predicted","measured","polarity_margin_db","per_snapshot_db","robust","left_out","format_name","written","crossovers","bank_size","text","format","fields","hp","lp","virtual_routing","previous_names","enterable","profile_gaps","crossoverKind","stereoSceneOffsetMs","stereoLevelDifferenceDb","IsTransparent","timingReference","timingOffset","group","preset","version","project_rev","measurements_repo","sources","paths","channels","glossary","channel_summary","presets","car","source","dsp","amps","mic","hardware","acoustics","flaws","_open_questions","state","journal","tcc","phase_deg","gain_db","ta_ms","polarity","eq","slope","OFF","hpf","lpf","delay_ms","inverted","peq","current","ref","sha","realpath","path","expect","allow_shadow","fallback","candidates","bind","main","alignSPLOffsetdB","date","endFreq","groupID","groupName","groupNotes","rewVersion","splOffsetdB","startFreq","timeOfIRStartSeconds","written_by","skill_sha","translated","lang","json","macro","fine","input_smoothing","source","score_db","avg_db","dip_db","dip_hz","ripple_db","level_gate_db","pol","tau_ms","excess","process","apply","naming","verify","predict","protective","dsp_math","curve_view","ellipsoid","eq_gate","xover_select","joint_analysis","analysis","listening","timebase","windows","resonalyze_ir","resonalyze_vc","eq_export","generic_eq","atf_eq","target_bands","equal_loudness","phase_rotation","flaw_map","setup_import","crossover_checks","spot_check","level_offsets","dsp_profile","project_seed","rew_api","rew_stub","path_check","provenance","make_plot","ear_suspects","eq_propose","verify_prediction","xover_candidates","nono_curves","target_curves","deployment","contract","project","migrate","console","capabilities","car_profile","excess_gate","side_effect","presweep_safety","Extended","Generic","Compound_filters","High_pass","Low_pass","Manufacturer","APF1","APF2","PK","LS","HS","LSH","HSH","BU","BE","LR","L-R","PRE_MS","STATE_FLOOR_DB","GATE_MIN_CYCLES","ROBUST_PERT","FORMATS","DEFAULT_FORMAT","KIND_HEARD","BASE_URL","REW_API_URL","AUTOSOUND_PROJECT_DIR","PYTHONPATH","CurveViewError","Export","ExcessPhaseGate","Project","Seeded","Validate","ImpulseResponseFile","TimeAlignmentAnalysis","Migrate","PhaseRotationControl","MeasureJunctionSpectrum","UNBOUND","UNVERIFIED","BLOCK","ALLOW","WARN","TRUSTED","CHECK","DRAFT","ILL","MOVES","STAYS","REFUSE","CAUTION","OK"):
            continue
        if name.isupper() or "_" not in name: continue
        if not re.search(rf"\b{re.escape(name)}\b", src):
            # look elsewhere
            found = [os.path.basename(p) for d in DIRS for p in [os.path.join(d, f) for f in os.listdir(d) if f.endswith('.py')] if re.search(rf"\b{re.escape(name)}\b", open(p, encoding='utf-8', errors='replace').read())]
            probs.append(f"L{ln}: `{name}` not in {mod}" + (f" (found in {', '.join(found[:3])})" if found else " (found NOWHERE)"))
print(f"{len(bullets)} module bullets in rew-tool-docs.md")
for p in probs: print("  - " + p)
print(f"{len(probs)} problem(s)")
