# What the skill reads from REW, and whether a session finds it (hub #306 PRM-001)

2026-10-25, role `skill`, at `20b2307` (v3.2.0). Asked by `promo` for its public text. The user's question
behind the ticket: if a session reading the entry points cannot see a tool, a tuning session in a project may
not offer it either.

## 1. The list: REW quantity → how it is read → what the method does with it

Every read goes through `rew_tool/rew_api.py` (REW's REST API, `localhost:4735`). The TCC column is filled
in §3.

| quantity | read with | what the method does with it | tools | reference |
|---|---|---|---|---|
| frequency response (magnitude) | `get_fr(mid, smoothing)` | the deviation from target, crossover choice, EQ packages, what cuts or booms, the flaw map, the spread over head positions, prediction and its check | `rew_tool.py analyze-batch`, `xover_candidates.py`, `eq_propose.py`, `ear_suspects.py`, `flaw_map.py`, `ellipsoid.py`, `predict.py`, `verify_prediction.py` | `core/analysis-playbook.md` |
| phase | `get_fr` (it returns phase beside magnitude) | the delay and polarity of each junction by summation, all-pass at the junction | `rew_tool.py analyze-joints`, `joint_analysis.align_by_summation`, `xover_select.align_joint` | `core/diagnostic-techniques.md` §9/§10 |
| impulse response | `get_impulse_response(mid)` | where each driver's sound arrives (four estimators and a TRUSTED / ILL-POSED verdict), the junction read through a 6-cycle window, export to Resonalyze v7 | `analysis.first_arrival`, `analysis.arrival_triangulate`, `windows.py`, `predict.py`, `resonalyze_ir.py` | `tooling/rew-api-quirks.md`, `core/diagnostic-techniques.md` |
| step response, ETC | computed from the impulse inside the skill, not read from REW | step: the low-frequency character, a visual only (polarity is never read from it); ETC: one of the four arrival estimators | `analysis.step_response`, `analysis.etc_envelope` | `core/analysis-playbook.md` |
| group delay | REW's `get_group_delay(mid)` (the cabin in it) **and** the skill's own through a 6-cycle window (the direct sound) | per band in the single-measurement report; the crossover's group-delay budget against Blauert & Laws; the junction's GD swing in the desk prediction | `rew_tool.py` (interactive), `crossover_checks.py --gd`, `predict.py`, `windows.windowed_group_delay` | `core/analysis-playbook.md`, `core/filter-types-car-audio.md` |
| distortion (THD + harmonics) | `get_distortion(mid)` (comes free with every sweep) | Phase 0's distortion floor per driver: ~1 % caution, ~3 % avoid; how low a driver may be crossed; a `thd_spike` row in the project's flaw ledger; a THD spike in a deep null is the room, not the driver | `rew_tool.py` (interactive, top 8 peaks), `project.py` (`thd_spike`) | `phases/phase_0_baseline.md` step 4 |
| excess phase / minimum phase | REW's own command → `-EP` / `-MP` curves → `get_fr` | is a dip fixable with EQ (minimum-phase or not); one bulk delay per channel from its excess phase | `rew_api.excess_phase_version`, `eq_gate.py` | `core/analysis-playbook.md` |
| impedance | an impedance sweep titled `… (imp)`, recognised by `measurement_kind`, read with `get_fr` | Thiele-Small parameters, box volume and box check, L/R match, the INSTALLED Fs for the crossover check and the pre-sweep safety gate | doctrine (no fitting tool); `crossover_checks.py --fs`, `gates/presweep_safety.py` | `core/impedance-ts.md` |
| RTA (MMM) | `(rta)` captures, read with `get_fr` | the in-car tone: deviation tables, what cuts or booms, levels | `rew_tool.py analyze-batch "_N (rta)"`, `ear_suspects.py`, `level_offsets.py` | `core/analysis-playbook.md` |
| timing / time base | `get_timing(mid)` | the loopback offset as applied; drift through a capture session | `timebase.py`, `verify.py --session`, `capture-check --session` | `tooling/rew-api-quirks.md` |
| filters, EQ, target | `get_filters` / `set_filters`, `get_equaliser`, `get_target_settings` / `get_target_response`, `get_crossover_types`, `get_slopes` | REW's EQ window as a staging area: read what is set, write what the desk designed | `eq_export.py`, `generic_eq.py` | `tooling/rew-api-quirks.md` |
| ring-down (decay of one peak) | computed from the impulse inside the skill | for a boom (40–120 Hz) or boxy (150–300 Hz) peak above its ±1-oct trend: the time a 1/3-oct band takes to fall 20 dB; only the top three suspects, only where such a peak exists | `ear_suspects.py --rew` (`ringdown_ms`) | `tooling/rew-tool-docs.md` |
| waterfall / CSD, spectrogram, RT60 | **not read by any tool** | the playbook sends door ringing to REW's own CSD/waterfall view; enclosure A/B names CSD beside FR; the ledger has `ringing` and `decay_asymmetry` flaw kinds, written by the session, no tool computes them | — (REW's UI) | `core/analysis-playbook.md`, `core/enclosure-install-diagnostics.md` |
| coherence | **not read** | the word in the code is the skill's own arrival search (`eq_gate.py`), not REW's coherence trace | — | — |

**For public text:** the honest scope is frequency response and phase, impulse (with step and ETC derived
from it), group delay, distortion, excess/minimum phase, impedance, RTA, timing, and REW's filters/EQ/targets.
Waterfall, spectrogram, RT60 and REW's coherence are not analysed by the method.

## 2. Why the entry points do not show it

- **SKILL.md points to two maps, but by role, not by quantity.** Line 41: «Find a tool before improvising one:
  `capabilities.py find "<what you want>"`»; router row 147 (`core/capabilities.md`) and row 148
  (`core/analysis-playbook.md`, «Which REW graph for which decision.»). Neither line names a quantity, so a
  grep over SKILL.md finds nothing: the list is one hop away. The playbook's table (question → graph → API
  function) is the list promo was looking for.
- **The board's `find` misses words the board does not carry.** «group delay», «distortion», «impulse»,
  «step response», «excess phase», «impedance», «RTA» each return a row. «THD», «waterfall», «decay»,
  «RT60», «coherence» return «no row of the board matches»: the distortion row says «distortion», not
  «THD»; and nothing says «waterfall — REW's UI, no tool», so a session gets silence instead of a direction.
- **The single-measurement report has no row on the board.** `rew_tool.py` with no arguments is an
  interactive deep dive on one measurement: FR + phase, REW's group delay and the 6-cycle one, impulse, the
  THD table, the deviation from target, cut suggestions. It is documented in `tooling/rew-tool-docs.md`,
  but the board names only `analyze-batch` and `analyze-joints`. `capabilities.py`'s reverse check counts
  the module as present, so the missing mode passes in silence — the limit its docstring names («the DEPTH
  of each tool's coverage is not machine-checked»). It also waits on `input()`, which an AI session drives
  awkwardly.
- **README.md** is the user's page; it names no quantities. That is a promo matter, not a tuning one.

## 3. TCC's window

Read from TCC's code at `98ebbd60` (v1.2.0) by a Sonnet agent; the key claims checked by hand (the curve window's
`KINDS`, the bridge's unused readers, the flaw labels).

**TCC plots three REW quantities, in one window — the curve window («Where exactly?»): frequency response, phase
and impulse** (`ui/tcc/curve_dialog.py` `KINDS`). An MMM `(rta)` capture draws as a frequency response only (REW
has no phase or impulse for it). On top of them TCC computes, itself, the arrival (a draggable marker and the
proposed delay) and the predicted sum Σ of the drivers together. TCC's guide says the same: «frequency response,
impulse, phase» (`docs/guide/QUICK-GUIDE.md`, `REFERENCE.md`).

The rest reaches the person as text, through the method's files or the terminal:

| quantity | in TCC |
|---|---|
| distortion | a flaw-map row «THD 2.6 %» in «Car audio analysis», from the skill's `project.json`; no plot. TCC's own words: «Noise and distortion stay REW's to report» (`CHANGELOG.md`, `core/capture_import.py`) |
| group delay, step, ETC, excess/minimum phase | not shown; the skill's terminal report and verdicts (a `non_min_phase` flaw row) |
| impedance | the `(imp)` capture is listed by title on the capture card; the driver's Fs in the DSP tree's tooltip, from `project.json`; no curve |
| ringing / decay | a flaw-map row when the skill wrote one (`ringing · +3.2 ms`); no waterfall |
| capture usability | the import's verdict and its reasons, from the method's `verify` (reads FR and impulse) |
| REW's filters/EQ | written by the model's `write_rew_filters` (behind a confirm bar), not displayed |
| waterfall/CSD, spectrogram, RT60, coherence | nowhere |

**For public text:** «TCC draws frequency response, phase and impulse from REW, and predicts the sum of the
drivers on them; group delay, distortion, excess phase and impedance are read by the method and come back as
findings and verdicts».

Two things in TCC's zone, named for its owner, not acted on here: the flaw kinds `ringing`, `energy_lag`,
`decay_asymmetry` have no `flawKind_*` label in `ui/tcc/i18n.py`, so a row without its own text shows the raw key in
its hover; `core/rew_bridge.py`'s docstring advertises «curves (FR, group delay, impulse response, distortion)»,
while `group_delay`, `distortion`, `filters`, `equaliser` have no caller (`docs/audit/unreachable.md` lists five
others, not these four).

## 4. Does a tuning session find it? A blind probe

A Sonnet agent got only SKILL.md's path and the user's words: «I have a sweep of my left midbass, `w-L_1 (sw)`.
Can you check its group delay and its distortion (THD)? And is there ringing around 150 Hz from the door — a
waterfall?» It could run read-only commands SKILL.md names.

| ask | found from SKILL.md alone | path | dead ends |
|---|---|---|---|
| group delay | yes | line 41 → `find "group delay"` → `get_group_delay`; the reading (cabin vs direct sound) via row 148 → the playbook | the `find` row's `read:` names `rew-api-quirks.md`, which holds the encoding, not the reading |
| distortion / THD | yes | line 41 → `find "distortion THD"` → `get_distortion` → `rew-api-quirks.md` § Distortion (the null caveat with a worked example) | — |
| waterfall / ringing at 150 Hz | partly | row 148 → the playbook's «Resonances / ringing → CSD / waterfall → REW UI» | `find` returned no row five times (waterfall, decay, spectrogram, cumulative spectral decay); «ringing» landed on `verify.py`'s impulse pre-ringing — a false friend. `ear_suspects.py`'s ring-down and `enclosure-install-diagnostics.md`'s CSD notes were reached only by grep |

So the user's worry holds in one place, not across the board: the core quantities are found in two steps; the
time-domain «ringing» question is where a session goes wrong or gets silence, and the nearest computed answer
(the ring-down figure) is invisible from the entry points.

## 5. Findings for W-12

Recorded as `docs/TODO.md` S-111. The fix is text (the board, the router, the playbook) except item 2's
non-interactive form, which is a feature and under the freeze waits for the Arbiter's word.

1. **The board's words.** The distortion row carries «THD, harmonics, спотворення»; a new row for «ringing,
   decay, waterfall, CSD, дзвін, затухання» → `ear_suspects.py` ring-down where a peak exists, REW's
   waterfall view otherwise, `core/enclosure-install-diagnostics.md`; the group-delay row's `read:` adds the
   playbook. A seam check in `capabilities.py --selftest`: every quantity of §1 returns a row from `find`, so
   the next gap fails a test instead of a session.
2. **The single-measurement report on the board.** `rew_tool.py` with no arguments (FR, two group delays,
   impulse, THD, deviation, cuts) has no row; it also waits on `input()`. The row is text; a
   non-interactive `rew_tool.py report "<title>"` would be a feature.
3. **The router names quantities.** SKILL.md row 148 says «Which REW graph for which decision»; naming the
   quantities (FR, phase, impulse, group delay, THD, excess phase, impedance, CSD) makes a scan or grep of
   SKILL.md hit. The playbook's ringing row links `ear_suspects` and `enclosure-install-diagnostics.md`.
