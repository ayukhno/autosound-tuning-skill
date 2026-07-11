# Changelog

All notable changes to the autosound-tuning skill. The skill is co-developed with real tuning sessions: each refactor harvests confirmed lessons from the field and folds them in.

## [v2.3.1] — 2026-07-11

Docs-only follow-ups plus a funding-channel activation.

### Added
- **`project-intake.md §4` — Level 0, light-touch entry.** The DSP capability levels (1/2/3) answer "what CAN you do"; Level 0 answers "how much do you WANT to do this session" — a small fine-tune of an already-working system can start from just the current measurement + target, skipping a full DSP dump/reverse-engineer. Guards the one real risk (double-correcting blind to existing filters) by still requiring a per-channel filter read before editing that channel's EQ, and stays re-entrant into Level 1/2 if it starts fighting something unseen.
- **GitHub Sponsors activated** (`github.com/sponsors/ayukhno`, approved 2026-07-11) as a second funding channel alongside the Monobank jar — `.github/FUNDING.yml`, the session-close donation ritual (`feedback-loop.md` §D), and all four README locales updated.

### Changed
- **README (all four languages) now notes the trigger needs a domain word** — a bare `resume` won't wake the skill (too generic); include "car-audio"/"tune" or the local-language equivalent.

## [v2.3.0] — 2026-07-11

A speed audit of the measure→analyze→correct→measure cycle (mass measurement/analysis, not sacrificing precision) plus a from-real-incident bugfix and an always-loaded token diet.

### Added
- **`rew_tool.py analyze-batch "<pattern>"`** — mass analysis of every measurement matching a pattern in ONE consolidated deviation matrix (per-driver band means vs per-band target + `anchor` + `ripple`). One `get_measurements` + one FR-only `get_fr` per driver instead of the interactive REPL's 5-endpoint fan-out — ~5× fewer round-trips, one table instead of N dumps. Same `analysis.py`/`target_curves.py` math, only orchestration + rendering are new.
- **`rew_tool.py analyze-joints`** — mass joint analysis (Phase 2b): every adjacent joint in one pass (polarity · drift-immune delay via `align_by_summation` · residual null · APF f0/Q), reusing `joint_analysis.py` unchanged. Honest by construction — a computed delay/APF is emitted only when a measured `pair` reproduces the complex solos (`phase_trust_gate`); no pair → `UNVERIFIED`; gate trips → `BLOCK`, no delay, fall back to the magnitude power-sum verdict. `--from-state` auto-derives the whole joint map from the active slot's crossovers in `state/` (no hand-typed `lo,hi,fc`).
- **`rew_api.py` measurement-processing wrappers** — `excess_phase_version(mid)` / `minimum_phase_version(mid)` create REW's native `-EP`/`-MP` versions (read the excess phase back via `get_fr`) — the authoritative min- vs non-min-phase decision using REW's own Hilbert, not a home-brew scan. `set_smoothing(mid, '1/6')` applies REW's own smoothing before a pull instead of the `perceptual_smooth` approximation. `POST /measurements/{id}/command` (processing an existing measurement) is a different namespace from capture (`/measure/*`) and is **not** Pro-gated — verified live on REW 5.40 / API 0.9.5.

### Fixed
- **`target_bands.py` now warns when a channel's config matches the module's `_DEMO_CFG` exactly** (`UserWarning`). Real incident: a project's committed per-band target curves turned out to be generated from the demo's placeholder crossovers/gains (e.g. a tweeter HPF knee at ~3500 Hz instead of the project's actual 1000 Hz) — silently, because nothing warned. `phase_1_foundation.md` Step 5 now states explicitly that per-band targets are a DERIVED artifact of the current crossovers/gains, to be regenerated on every crossover/gain change, never left stale or generated from demo values.

### Changed
- **`SKILL.md` always-loaded surface trimmed ~21%** (7133 → 5610 tokens; 185 → 157 lines) without dropping any rule — rebalanced by scope (universal stays in SKILL.md; phase-specific moves to its phase file, loaded on-demand by the sliding-window protocol) and criticality (critical rules stay full; non-critical collapse to a pointer). Start-only guardrails (Verify Banked Decisions) moved into the Pre-Session/Resume steps; refactor-only ones (the 5-step Skill Maintenance Loop) moved to `feedback-loop.md`.

### Explored and consciously dropped
- **Automating measurement capture over the REW API.** Verified live that `POST /measure/command {"command":"SPL"}` does fire a sweep and `/measure/naming` does name it — but every capture/control POST requires a REW Pro license (free tier returns `401`), and more decisively, the mic is placed/held by hand (MMM = moving mic) regardless, so auto-triggering a sweep saves nothing. Analysis stays API-driven (GET); capture stays manual. Documented in `rew-api-quirks.md` so this isn't re-explored.

## [v2.1.1] — 2026-07-05

Curve-visualizer fixes, found live by a user dropping curves into `curves.html`.

### Fixed
- **Manual level-offset lost/doubled on reload.** The offset was tracked only in a closure-local JS variable that reset to 0 every page load, decoupled from what was actually baked into the persisted data/label — so the display lied ("0.0 dB" on an already-shifted curve) and nudging it again stacked on top of the old shift instead of replacing it. Offset now lives on the dataset object, is persisted explicitly, and old (already-broken) saved state self-heals via a label-suffix parse fallback.
- **No way to remove a dropped curve.** Added a delete (✕) button per loaded-curve card; card wiring switched from a captured array index to a live dataset reference so deleting one card can't desync another's toggle/offset handlers.
- **Delete button hidden behind the next card on long names.** An unbreakable underscored filename in the flex title row refused to shrink (no `min-width:0`), overflowing the row and pushing the button past the card's edge, where the next grid cell's own background painted over it — clicks landed on the neighboring card instead. Fixed with `min-width:0` + `overflow-wrap:anywhere` on the label and `flex-shrink:0` on the dot/button.
- **Drag-drop hint text overlapping the card grid.** `#dropZone` and the "клац на картку" hint lived inside `.chart-wrapper` (hard `height:500px` for the canvas), so they overflowed past the box into the same band where `.info-grid` starts. Moved both to be normal-flow siblings instead.
- **`curves.html` too hard to find.** New-project intake (`project-intake.md §5`) now symlinks it at the project root, not just the skill root.

## [v2.1.0] — 2026-07-04

State substrate + field-harvested phase/summation tools + license cleanup + dogfood-informed process control. (Authoritative version of a checkout is `plugin.json`; the unambiguous identity of a build is the commit hash.)

### Added
- **Versioned hard-params state** (`rew_tool/state/state.py`) — one JSON snapshot per change (crossovers / gains / TA / polarity + EQ pointers); `snapshot` / `diff` / `revert` / `render`. ms is canonical, samples derived at the DSP's rate. Anti-drift anchor + cheap A/B / revert / resume.
- **apply-change** (`rew_tool/state/apply.py`) — `propose` → banks a 🟡 snapshot + emits the human settings sheet (channel/param old→new, ms+samples); `attest` → 🟢 applied (proposed-vs-applied).
- **Side-effect gate** (`rew_tool/gates/side_effect.py`) — outbound actions run an exact command with the repo **hardcoded** + returned-URL verify (FAIL LOUD); kills the confabulated-repo failure. **Dedup guard:** an identical-title open feedback issue newer than 24 h → loud SKIP instead of a double-post (a real #3/#4 double-fire, 5 s apart).
- **Pre-sweep safety gate** (`rew_tool/gates/presweep_safety.py`) — refuses a sweep on an unprotected fragile driver (HPF ≥1.1×Fs @≥24 dB, level, clip).
- **`rew_tool/joint_analysis.py`** — within-session summation / TA / phase logic: `joint_summation_check` (measured pair vs incoherent power reference → phase cancellation vs tonal dip; never boost a null), `phase_trust_gate` (do the complex solos reproduce the pair? if not — block delay/APF/polarity), `flag_remeasure_candidates` (dirty-sweep detection: pre-echo vs the cleanest capture of the SAME driver; validated 5/5 on field ground truth), `timing_drift_audit` (REW label-drift vs a real TA change — ~0.13 ms drift measured even WITH loopback), `align_by_summation` (drift-immune polarity+delay from the coherent sum), `allpass_for_residual_null`, `shelf_vs_bell`, `impulse_polarity`, `perceptual_smooth`, `midband_level_anchor`.
- **`rew_tool/spot_check.py`** — independent verification of a model's cited numbers against live REW (levels at cited freqs, L−R deltas, actual band peak vs the claimed one, anchored deviation vs target). Field-proven double duty: confirmed honest numbers to the hundredth AND caught a filter aimed at 2450 Hz when the measured peak sat at 2202 Hz.
- **`references/core/process-control.md`** — the Arbiter's operating modes (**A** Claude+Gemini-Advisor with mandatory advisor nodes · **B** Claude solo · **C** Gemini solo with process risk consciously accepted) + the pull-based playbook (tool-emitted settings-sheets only; "done" costs a path; spot-check before applying; reviewer runs OUTSIDE the driver session).
- **Offline target-curve visualizer** (`curves.html`) + **`rew_tool/equal_loudness.py`** (ISO 226 sub-bass targeting); review-loop full-transcript logging. Visualizer: **localStorage persistence** (imported curves, show/hide selection and per-curve level survive refresh), **group imports share ONE common offset** (mono/stereo/per-band level relationships preserved), auto-matched curve descriptions.
- **`autosound_ai.py` hang protection** — a reviewer CLI spawned inside an agent session deadlocks (observed ~15/20 field sessions); calls now time out (`AUTOSOUND_CLI_TIMEOUT`, default 120 s), FAIL LOUD naming the cause, and fall back to Clipboard Mode. Troubleshooting section in `installation.md` (incl. Antigravity sandbox state-root note).

### Added — acoustic method
- **Judge deviations by audibility, not the trace** (`references/patterns/car-eq-patterns.md`): weight by *bandwidth* (a broad tilt vs the target beats a narrow notch of equal dB), catch it with a band-integrated deviation-vs-target scan (analysis playbook + Phase-3 verdict) + a long/fatigue listen (Phase 4); don't overcorrect narrow nulls / off-axis dips (kills transparency). Folded from field feedback (VW Passat B8 · Jazzi, issue #2).
- **Cross-time phase trust is band-gated** (folded into `joint_analysis` + method docs): LF phase survives between sessions; MF/HF phase does NOT (reference drift ~0.13 ms even with loopback; HF decorrelates ~110° rms) → TA/polarity only from back-to-back captures via summation/xcorr, never from cross-session HF phase.
- **[provisional] Off-axis tweeter idea-to-try** (`voicing-by-ear.md`): before keeping single-mic software HF cuts on the far/off-axis tweeter, A/B their bypass by ear — target-matching can choke decay/air (field case; geometry-dependent, NOT a rule).

### Removed
- **The 6 bundled third-party target curves** (Audiofrog, Harman, Jazzi, ResoNix Accurate, ResoNix Laid-Back, Half Whitledge) — they are other people's published curves and we don't redistribute them. Users download them from the **Nono Tuning Tool** (nonotuningtool.com) and drop them into `target-curves/curves/` or onto the visualizer (which keeps our own character descriptions and auto-matches them by name). The folder `NTT/` was renamed to **`curves/`**; the only bundled curve is now **EMMA-Ref v3** (developed within this project, materialized as `curves/EMMA-Ref_v3_0db_REW.txt`).

### Notes
- A token-handshake + `override` "control-plane" was built and then **removed by design** — the substrate stays simple; compliance is model-choice + human-in-the-loop, not scaffolding.
- **Dogfood verdict (solo-Gemini, ~20 sessions, transcript-audited):** deterministic *calculator* tools get used (library helpers ran 100+ times); pure *discipline* gates get **narrated, not run** (the change-gate: 70+ spoken mentions, 0 executions). Hence the reframe shipped here: the substrate is the **Arbiter's power-tool, pulled** (settings-sheets citing a `v_NNN` snapshot), not a Generator self-discipline ritual — and the honest operating-modes table in `process-control.md`. The tune itself was excellent and its numbers verified real — the method holds; the process spine belongs to the Arbiter.

## [v2.0.6] — 2026-07-02
Critic as drift-watchdog (recommends re-anchor / `/clear` on detected Generator drift).

## [v2.0.5] — 2026-07-02
Single-AI reviewer ladder (on-demand / stateless, tier-escalating, never solo).

## [v2.0.4] — 2026-07-02
Resume / continuation description triggers (anchored, validated).

## [v2.0.3] — 2026-07-02
L/R shape-match group-delay caution (Gemini v2.0 methodology review).

## [v2.0.2] — 2026-07-02
UK / DE / PL native-language description triggers (validated 7/7).

## [v2.0.1] — 2026-07-02
Restore casual-EN + create-curve description triggers (9/9); repaired trigger-eval runner.

## [v2.0.0] — 2026-07-01
Assisted method: Claude+Gemini default reviewer, 5-layer knowledge architecture, goal-node phases, anti-drift state-on-disk, Gemini gemini-optim tooling. **Major bump — the numbering moved from 1.x to 2.x here;** the CHANGELOG had lagged at v1.1.0 (reconciled 2026-07-04, which is why a stale read reported "v1.1.0").

## [v1.1.0] — 2026-06-26

Packaging + method-harvest release.

### Added
- **Distributed as a Claude Code plugin** — one-command install (`/plugin marketplace add ayukhno/autosound-tuning-skill` → `/plugin install autosound-tuning`); no more manual clone+copy or the `SKILL.md`-nesting "Unknown skill" trap.
- **`knowledge/approaches.md`** — a classifier of whole-system tuning/crossover schemes as variants tagged by setup context + success story + confidence (the format names a GOAL, not a slope recipe).
- **`knowledge/{cars,dsp}/_TEMPLATE.md`** — blank fill-in profiles so onboarding a new car/DSP is a form, not reverse-engineering the example.
- **`rew_tool` helpers** — `find_measurement_id` / `get_measurement_by_name` (resolve by name) + `first_arrival` (leading-edge) + `relative_delay_xcorr` (cross-correlation), `--selftest`-verified.
- Ukrainian README (`README.uk.md`); a **Support** section (a voluntary Monobank tip jar) in all four languages.

### Changed
- **Merged the `review-loop` sibling skill into `autosound-tuning`** as `references/review-loop.md` — one skill, simpler distribution; translated to English (the skill body is now fully EN-canon).
- **Crossover schemes decoupled from competition format** — the format names a goal; the slopes follow from the setup (body → install → ways → equipment), recorded as success stories, not laws.
- **Intake §2 restructured** as the user's goals journey + a new "who is the tune for?" (driver / passenger / all seats) question + an open catch-all for any other wish.
- **De-Helix'd the universal path** — the method reads DSP-agnostic; Helix stays the worked example.
- READMEs shortened ~21% and native-reviewed (EN/DE/PL/UK).

### Notes
- Built on a VW Passat B8 / Helix DSP Ultra S system (AYA competition win).

## [v1.0.0] — 2026-06-13

First public release. Portability + process refactor that turned a single-car skill into a distributable, any-car/any-DSP method.

### Added
- **Phase −1 — new-project intake** (`references/project-intake.md`): quickstart for new hands, equipment + goals interview, target-curve choice (no default — chosen with the user via the curve→character table), install verification (routing, electrical polarity, protective crossovers, gain staging, noise, break-in, safe sweep level), DSP-capability checklist (incl. non-Helix), project-file generation.
- **Phase 7 — project wrap-up / feedback loop** (`references/feedback-loop.md`): how the skill ships and how field experience flows back safely (package template, channels, safety rules, two-step "fix locally → deliver explicitly").
- **`knowledge/` library** of accumulated profiles: `cars/vw-passat-b8-sedan.md` (body vs install anomalies, winning crossovers — anonymized), `dsp/helix-dsp-ultra-s.md` (filled intake checklist + two EQ-transfer paths). Checked first at intake of a known body/DSP.
- **`nonotuningtool` step** (Phase 1, step 5b): per-channel target curves with summation coefficients → imported into REW.
- **Standard listening pass** (`references/test-tracks.md`): a fixed 10-step route with a binary checklist for milestone ear-verification.
- Documented **REW-EQ-CopyPaste-Assistant** as the EQ-transfer path for 30+ DSPs without file import.

### Changed
- Generalized the skill to any car/DSP: car-specifics moved out of `SKILL.md` into the project profile; `description` generalized; Helix references marked `[DSP-specific]`.
- **No default target curve** anywhere — the curve is chosen with the user.
- **Phase 2 restructured** into the correct order: hygiene-EQ → joint phase → summed-curve alignment (band pairs / sides / SW+Ws) → final EQ-to-target. (Listener taste stays in Phase 6, on the virtual layer.)
- Phase 4 (center/rear) rewritten to current findings; crossover starting-sets consolidated (several variants, not one "standard").

### Notes
- Built on a VW Passat B8 / Helix DSP Ultra S system (AYA competition win). The `review-loop` sibling skill ships alongside.
