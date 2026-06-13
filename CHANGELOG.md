# Changelog

All notable changes to the autosound-tuning skill. The skill is co-developed with real tuning sessions: each refactor harvests confirmed lessons from the field and folds them in.

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
