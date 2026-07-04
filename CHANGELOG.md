# Changelog

All notable changes to the autosound-tuning skill. The skill is co-developed with real tuning sessions: each refactor harvests confirmed lessons from the field and folds them in.

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
