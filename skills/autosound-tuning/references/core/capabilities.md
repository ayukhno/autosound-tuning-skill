# Capabilities — find the tool by what you want, not by the path

The phase path (−1…5, `process-phases.md`, `virtual-first.md`) is for a tune run from start to
finish. Many sessions come with their own process — "I have my measurements, only align the
sub↔midbass joint", "the tune is done, tell me what cuts", "read my friend's Virtual DSP session
into a ledger" — and need to find what the method can do for THAT. This board is the index for
them: one line per capability, by intent, pointing at the command and the doctrine. It is an index,
not documentation — the facts live where the pointer says (`tooling/rew-tool-docs.md` for the
modules, the phase and core files for the reasoning).

Columns: **what you want** (with the words a user says, EN / UK) · **what you get** · **command or
call** · **needs · refuses without** (a check whose input is missing FAILS, it never reports
"no objection" — `estimator-scope.md`) · **phase** where it normally sits · **maturity** — `field`
(has decided something in a car), `desk` (run on live data at the desk, no car verdict yet),
`selftest` (synthetic data only) · **read**.

`rew_tool/capabilities.py --selftest` keeps this board honest: every command, flag and function
named here must exist, and every module with a command line must be on the board.

## A · Talking to REW

| what you want | what you get | command / call | needs · refuses without | phase | maturity | read |
|---|---|---|---|---|---|---|
| is this crossover corner allowed at all — Fs, group delay, where the ear is least forgiving / чи можна ставити цей зріз | three verdicts (OK / CAUTION / REFUSE) with the source of each named: Fs margin against the INSTALLED Fs (floor 1.1× is doctrine, the working margin is convention), the group-delay budget against Blauert & Laws, the junction cost from ISO 226 | `crossover_checks.py --fc 2500 --fs 900 --order 2 [--gd f:ms,…]` · `crossover_checks.fs_margin / gd_budget / junction_cost` | needs the installed Fs from an impedance sweep · without `--fs` it SAYS the one refusing check was skipped | 1 | selftest | `core/impedance-ts.md`, `core/filter-types-car-audio.md` |
| read what is in the DSP NOW into the ledger — a Helix has no file to read, only screens / зчитати чинні налаштування процесора | a transcription validated against the DSP profile (delay grid and ceiling, gain range and step, EQ types/bands/ranges), banked as the first version or as a proposal, with provenance `transcription · verified_by_file=false`; EQ from an ATF bank where there is one | `setup_import.py <project> transcription.json [--atf m-L=m-L.atf] [--write]` | needs `dsp_profile.json` · refuses (exit 3) on any value the DSP cannot hold, naming it, and without a profile | −1 (improve mode) | selftest | `phases/virtual-first.md` (two modes), `tooling/helix-eq-export.md` |
| a second opinion on channel levels, from the measurement / рівні з виміру, а не з геометрії | each channel's energy-averaged level in its own band, and the cut-only offsets that balance them | `level_offsets.py --solos DIR --ver N --levels-fixed [--project DIR]` (geometry estimate: `level_offsets.compute_offsets`) | needs one REW output level for the whole round · refuses (exit 3) without `--levels-fixed`, because no file records the knob | 1 | desk | `phases/capture-session-sheet.md` |
| what must be OFF in the DSP before a capture / що вимкнути перед зйомкою | the vendor's own names for effects and dynamic processing, from the profile | `dsp_profile.py effects <profile.json>` | needs the list in the profile · refuses (exit 3) when nobody recorded it — "none" is an empty list | −1.4 / 0 | field | `phases/capture-session-sheet.md` |
| talk to a REW that is NOT on this machine / REW на іншій машині або на іншому порту | every tool reads that address instead of `localhost:4735` — one variable, no flags | `REW_API_URL=http://studio-pc:4740` in the environment (`rew_api.BASE_URL` reads it at import) | needs the API on at that address · refuses nothing — an unreachable address fails per call | any | field | `tooling/rew-api-quirks.md` |
| list what REW holds, find a measurement by its title / знайти замір за назвою | the id, FRESH (ids reshuffle on any reorder) | `rew_api.get_measurements()`, `rew_api.find_measurement_id(name)` | REW running at `REW_API_URL` (default `localhost:4735`) · an ambiguous title raises, never picks | any | field | `tooling/rew-api-quirks.md` |
| pull a frequency response, impulse, group delay, distortion / зняти АЧХ, імпульс, ГЗ, спотворення | arrays on REW's own axis (log or linear), big-endian float32 decoded | `rew_api.get_fr(mid)`, `get_impulse_response(mid)`, `get_group_delay(mid)`, `get_distortion(mid)` | an RTA has no phase and no impulse — said, not guessed | any | field | `tooling/rew-api-quirks.md` |
| know a measurement's TIME BASE (reference, offset, start, sample rate) / на якій базі знято | one dict, the same reader for the skill and TCC | `rew_api.get_timing(mid)`; batch: `timebase.py --title _49 \| --all` | `startTime` present — `delay` is the ARRIVAL, never a substitute | 0, 3 | field | `tooling/rew-tool-docs.md` (`timebase`) |
| what smoothing REW already applied / яке згладжування вже стоїть | the payload's own `smoothing` | `rew_api.fr_smoothing(mid)`; `set_smoothing(mid, "None")` before fine analysis | fine analysis on a pre-smoothed curve is REFUSED by `curve_view` | 0–3 | field | `tooling/rew-tool-docs.md` |
| the excess-phase / minimum-phase twin of a sweep / надлишкова фаза | REW creates `<name>-EP` / `-MP`; read with `get_fr` | `rew_api.excess_phase_version(mid)`, `minimum_phase_version(mid)` | a sweep (loopback) | 0, 2a | field | `core/analysis-playbook.md` |
| read or write a channel's filters / equaliser in REW | the filter set, the equaliser model | `rew_api.get_filters`, `set_filters`, `get_equaliser`, `set_equaliser`, `get_crossover_types`, `get_slopes` | REW may be mid-session: read, and put back what you change | 2 | field | `tooling/rew-api-quirks.md` |
| work with NO REW — an archived session, CI, a desk / без REW | the four endpoints the tools read, served from v7 files | `rew_stub.py --from-v7 DIR --ver 49`, then `REW_API_URL=http://127.0.0.1:47350` | v7 files (`resonalyze_ir.py` exports them) | any | selftest | `tooling/rew-tool-docs.md` (`rew_stub`) |
| export a sweep to a Resonalyze v7 impulse file / експорт у v7 | one JSON per title, loopback base, protective mark from the round | `resonalyze_ir.py --title "w-L_49 (sw)" --process <proj>/process` | loopback reference with zero offset — otherwise refused | 0 | field | `tooling/resonalyze-virtual-dsp.md` |

## B · Naming, capture rounds, is a capture usable

| what you want | what you get | command / call | needs · refuses without | phase | maturity | read |
|---|---|---|---|---|---|---|
| the right title for a measurement / як назвати замір | `w-L_49 (sw)`, positions `m-L p1_49 (sw)`, controls `m-L-ctl1_49 (sw)` | `naming.py <proj> name w-L 49 sw`, `parse <title>`, `expect <phase> <ver>`, `check <phase> <ver>` | the project's glossary | 0–3 | field | `core/naming-and-structure.md` §3 |
| open a capture round and record what came back / раунд зйому | the round on the process state, unplanned captures flagged | `process.py <proj>/process capture-start <ver> [titles] · capture-taken <title> · capture-skip · capture-close` | — | 0, 3 | field | `phases/phase_0_baseline.md` |
| mark what was in the chain while measuring / протективи на раунді | the round's protective record, read by every later phase decision | `process.py … capture-protective m-L --hp 100 LR 24` / `… OFF` | run it for every channel: not running it means "as configured" | 0 | field | `core/project-intake.md` §3 |
| is this capture there and usable / чи придатний замір | a verdict per title (exists, valid, issues, stats: level, IR peak, pre-ringing, capture rate) | `verify.py "<title>" …`; on the round: `process.py … capture-check` | REW; a flat curve is a loopback, not a driver | 0, 3 | field | `phases/phase_0_baseline.md` |
| the whole SESSION at a glance and the drift record / проба сесії, дрейф | levels side by side, loudest/quietest, ctl1→ctl3 drift by cross-correlation (held / moved) | `process.py … capture-check --session` / `verify.py --session …` | control titles `<x>-ctl1` and `-ctl3` (or `_Nctl`/`_Nrep`) | 0.6 | selftest | `phases/virtual-first.md` 0.6 |
| were these captures taken the same way / та сама база? | reference · offset · rate · range compared across a batch | `timebase.py --title _49` | — | 0, 3 | field | `tooling/rew-tool-docs.md` (`timebase`) |
| which sweep to re-take / що перезняти | pre-echo of each capture against the CLEANEST of the same driver | inside `capture-check`; `joint_analysis.flag_remeasure_candidates` | two captures of one driver — with one there is nothing to be an outlier of | 0 | field | `core/diagnostic-techniques.md` §13 |

## C · Protective filters — in the recording, not in the tune

| what you want | what you get | command / call | needs · refuses without | phase | maturity | read |
|---|---|---|---|---|---|---|
| take the protective filter OUT before reading phase / зняти протектив | the solo as the driver would read bare (correction capped, and the cap said) | automatic in `predict`, `analyze-joints --process`, `eq_propose`; library: `protective.de_embed` | the round's record (or the v7 mark) — a baseline solo nobody marked is REFUSED with `--baseline` | 1–2 | field | `core/project-intake.md` §3, `core/estimator-scope.md` §2 |

## D · Time, junctions, polarity, all-pass

| what you want | what you get | command / call | needs · refuses without | phase | maturity | read |
|---|---|---|---|---|---|---|
| all the joints of a measured system in one table / усі стики | polarity · delay · APF per adjacent pair, both rulers (sum loss, worst null) | `rew_tool.py analyze-joints --from-state --process DIR` | protective record for a baseline round | 2b | field | `phases/phase_2_eq.md` 2b |
| the joints at the DESK, from solos, before anything is entered / стики за столом | delay × polarity per junction bottom-up on the DSP's grid, aliases said by name, `aligned-delta.json` | `predict.py --solos DIR --project P --baseline --align [--apf] --out DIR` | solos on one time base; the profile's processing rate | 1.3 | desk | `phases/virtual-first.md` 1.3 |
| the delay of one pair by summation (drift-immune) / затримка пари | polarity + relative delay maximising the coherent sum | `joint_analysis.align_by_summation`, `xover_select.align_joint` | two solos on one base | 2b | field | `core/diagnostic-techniques.md` §9/§10 |
| an all-pass that repairs a remaining null / APF на стику | APF2 (f0, Q) and on which branch | `xover_select.repair_joint_apf`; `analyze-joints --apf ch,KIND,f0[,Q]` to VERIFY one dialled by hand | the joint aligned first | 2b | field | `tooling/helix-phase-allpass.md` |
| where does a driver's sound ARRIVE / прихід | onset, edges, ETC peak and a TRUSTED / ILL-POSED verdict | `analysis.arrival_triangulate`; L↔R: `analysis.relative_delay_xcorr` | clean, band-limited drivers — a sub is ILL-POSED and says so | 1 | field | `core/estimator-scope.md` |
| the L−R difference per band / різниця лівого і правого | per-band deltas of the predicted sides | `predict.py` (the `lr_delta` table) | — | 1.5, 2.2 | desk | `phases/virtual-first.md` |

## E · Crossovers and levels

| what you want | what you get | command / call | needs · refuses without | phase | maturity | read |
|---|---|---|---|---|---|---|
| a starting crossover for a driver / з чого почати кросовер | families, slopes, starting corners per driver class | (doctrine) | — | 1 | field | `core/filter-types-car-audio.md` |
| realise an acoustic target as an electrical crossover + trim + EQ / реалізація цілі | top candidates scored on fit, boost-budgeted | `xover_select.realize_driver`, `select_neighbor_pair` | an acoustic target and the driver's RTA | 1 | field | `tooling/rew-tool-docs.md` (`xover_select`) |
| a first LEVEL balance from geometry / рівні з геометрії | cut-only offsets from distance and off-axis angle | `level_offsets.compute_offsets` | distances, angles, piston radius (project data) | 1.4 | field | `phases/phase_1_foundation.md` |
| the Helix filter model against the hardware / модель фільтрів | (doctrine: verified textbook AP2; family scale BW/LR ±10°) | — | — | — | field | `tooling/helix-phase-allpass.md` |

## F · Targets and curves

| what you want | what you get | command / call | needs · refuses without | phase | maturity | read |
|---|---|---|---|---|---|---|
| choose, compare, build a house curve / цільова крива | the guide, the bundled curves, the visualizer | `patterns/target-curves/curves/*.txt`; `target_curves.load_target_curve` | — | −1, 0 | field | `patterns/target-curves/target_curves_guide.md` |
| set the preset's CURRENT target / поточна ціль | one pointer every reader uses (sheet, gate, TCC) | `process.py … target <preset> <curve>`; read: `state.current_target` | — | 0 | field | `core/naming-and-structure.md` |
| per-driver targets from the house curve / цілі по драйверах | house − summation offset + crossover shape + gain | `target_bands.generate(house, cfg)`; inside `eq_propose` | the ledger's crossovers and gains, never the demo config | 1.5 | field | `phases/phase_1_foundation.md` §5 |
| a sub target by equal loudness / саб за рівною гучністю | the ISO 226 contour through your anchor, and cuts to reach it | `equal_loudness.py --anchor 27.4 108.2 --measure …` | one measured anchor | 2, 5 | field | `tooling/rew-tool-docs.md` (`equal_loudness`) |
| read a Nono Tuning Tool export / крива з NTT | freq/mag(/phase) | `nono_curves.parse_nono_curve` | — | 1 | field | `tooling/rew-tool-docs.md` |

## G · EQ — what may be corrected, and how

| what you want | what you get | command / call | needs · refuses without | phase | maturity | read |
|---|---|---|---|---|---|---|
| what STAYS and what MOVES around the head; how narrow a filter may be / стоїть чи їде, стеля Q | σ(f), stays/moves per feature, the Q ceiling per band, the centre drift | `ellipsoid.py --solos DIR \| --rew --ver N --channel m-L` | 9 hand-held positions `p1…p9` (2 is the minimum, and says so) | 0.3 → 1.1 | desk | `core/diagnostic-techniques.md` §13 |
| EQ as PACKAGES, gated, with why / EQ пакетами | resonances per driver group, L/R shape per pair, tone per pair — each with why, a listening id, a score, an `apply.propose` delta | `eq_propose.py --project P --solos DIR --house curve.txt [--ellipsoid DIR] [--route VFL=w-L,m-L,tw-L] --out DIR [--accept a,b]` | the ledger, the house curve; cuts only unless `--allow-boost` and the gate | 2.1, 3.3 | desk | `phases/phase_2_eq.md` 2a |
| may this dip be BOOSTED / чи можна бустити яму | ALLOW / WARN / BLOCK / OUT_OF_SCOPE from the excess phase | `eq_gate.ExcessPhaseGate(...).check(f0, q)`; from an impulse: `eq_propose.gate_from_ir` | the calibrated band (150–4000 Hz) — outside it, no vote | 2a | field | `core/estimator-scope.md` |
| read a curve at three distances — tone, features, spikes / три дистанції | macro summary, features routed by width (voicing / point-EQ / verify-first / null-suspect) | `curve_view.report(freqs, mag_db, band)` | an UNSMOOTHED input for the fine scale — refused otherwise | 2 | field | `core/diagnostic-techniques.md` §6/§21 |
| the deviation of every `_N` measurement from its target in one table / масова таблиця відхилень | band means, anchor, ripple, per title | `rew_tool.py analyze-batch "_2 (rta)"` | target curves per channel | 2a, 2d | field | `phases/phase_2_eq.md` |
| what CUTS the ear, what BOOMS — and settle it by A/B / ріже, гудить | the top three suspects, classed, one correction each, the phrase to listen for, the verdict line | `ear_suspects.py --rew --title "ALL_2 (rta)" [--process DIR --round 2]` | an MMM or a sweep; three rounds at most | 3.3, 5 | selftest | `phases/virtual-first.md` 3.3 |
| fit EQ bands to a residual, with the gates / фіт смуг | bands and the residual after | `dsp_math.greedy_eq_fit(freqs, resid, weight, boost_gate=…)` | `weight` from the target's passband | 2 | field | `tooling/rew-tool-docs.md` (`dsp_math`) |
| the channel's EQ in the DSP's format / EQ-файл для DSP | ATF 30-band bank or REW Generic, with what was LEFT OUT | `eq_export.py <proj> tw-L --out tw-L.atf`; library both ways: `eq_export.export_eq`, `import_eq` | the project's DSP profile | 2.3 | field | `tooling/helix-eq-export.md` |
| read an existing Helix bank, emit only what you decided / прочитати банк ATF | parsed bands; a formatted bank | `atf_eq.parse_atf_eq`, `format_atf_eq` | — | 2 | field | `tooling/helix-eq-export.md` |
| verify a MODEL's cited numbers against live REW / перевірити цитовані числа | levels at cited frequencies, the real peak vs the claimed one | `spot_check.py "L_09 (rta)" "R_09 (rta)" --at 160,2540 --peak 2000-3000 --claim 2543.8` | REW | any | field | `core/driver-discipline.md` |

## H · Prediction and verification (virtual-first)

| what you want | what you get | command / call | needs · refuses without | phase | maturity | read |
|---|---|---|---|---|---|---|
| what the mic WOULD hear from the solos and the ledger / прогноз суми | channels, L/R/ALL sums, junction loss, L−R per band; JSON + plot | `predict.py --solos DIR \| --rew --ver N --project P [--baseline] --out DIR --plot` | solos on one time base; rows it cannot model are LEFT OUT and said | 1.5, 2.2 | field | `phases/virtual-first.md` |
| put the VIRTUAL tier into the prediction / віртуальний ярус | its EQ/gain/delay in the chain of the outputs it feeds | `predict.py … --route VFL=w-L,m-L,tw-L` | the routing as the DSP's matrix reads — never guessed from names | 1 | desk | `tooling/rew-tool-docs.md` (`predict`) |
| was the preset ENTERED as designed / контроль введення | per channel: shape after one offset, arrival error, CHECK with the nearest chain feature named | `verify_prediction.py --predicted predicted.json --rew --ver 2 --entry` (or `--measured DIR`) | 1–2 point sweeps from the tripod; an RTA cannot verify | 3.1 | selftest | `phases/virtual-first.md` 3.1 |
| do the measured sums TRUST the model / чи вірити прогнозу | junction interference predicted vs measured, ≤ 1 dB per sub-band → TRUSTED / NOT trusted at <junction> | `verify_prediction.py --predicted … --rew --ver 2` | pair sums and both solos on the same base | 3.2 | field | `phases/virtual-first.md` 3.2 |
| read a Virtual DSP session as ledger rows / сесія Resonalyze у леджер | rows checked against the DSP profile; what the DSP cannot enter is refused by name | `resonalyze_vc.py session.json --project P` | the project's `dsp_profile.json` | 1 | field | `tooling/resonalyze-virtual-dsp.md` |
| the whole path, end to end, on synthetic drivers / наскрізна перевірка | every seam of −1…4 walked through the real commands | `path_check.py --selftest` | nothing — it makes its own project | — | selftest | `tooling/rew-tool-docs.md` (`path_check`) |

## I · Listening

| what you want | what you get | command / call | needs · refuses without | phase | maturity | read |
|---|---|---|---|---|---|---|
| what to listen for, on which track, in which order / що слухати | characteristics c01–c16 with *sounds right / wrong*, the tracks, the routes first / short / full / league | `listening.py characteristics --lang uk`, `tracks`, `links`, `routes`, `check` | the two markdown homes; an orphan id fails the suite | 4 | field | `patterns/listening-cheat-sheet.md`, `patterns/test-tracks.md` |
| record what the Arbiter heard / записати вердикт | one journal entry: ticked pairs + own words, stamped with the ledger version | `process.py … listening-verdict --pair <track>:<char>:ok\|bad --text "…" --ledger-version vN` | ids validated against the vocabulary | 4 | field | `phases/phase_4_listening.md` |
| look back at what was heard when / що чули на v_003 | the verdicts filtered by track / characteristic / version; the lines a lock banks | `process.py … listening-verdicts [--track] [--characteristic] [--bank]` | — | 3, 4 | field | `phases/phase_4_listening.md` |
| taste EQ by A/B for someone who cannot name the target / «як подобається більше» | three suspects × three rounds, each settled better / same / worse | `ear_suspects.py …` → `listening-verdict --text "suspect:<id>=…"` → `--round 2` | a separate preset for taste (Phase 5) | 3.3, 5 | selftest | `phases/virtual-first.md` 3.3 |

## J · The project on disk — facts, ledger, process

| what you want | what you get | command / call | needs · refuses without | phase | maturity | read |
|---|---|---|---|---|---|---|
| start a project from prose, or from another project / новий проект | `project.json` + `dsp_profile.json` skeletons; system parameters inherited | `project.py <dir> show`; `project_seed.py SOURCE TARGET [--findings]` | — | −1 | field | `core/intake-from-prose.md`, `core/project-intake.md` |
| the car's facts, one channel at a time / факти про машину | channels, hardware controls, flaws, open questions | `project.py <dir> set-channel w-L role=woofer …`, `rename-channel`, `set-hardware`, `flaw …`, `flaws`, `open-questions`, `backfill-tiers`, `record-change` | — | −1…2 | field | `rew_tool/project-schema.md` |
| what the DSP CAN do / профіль DSP | the capability profile: rate, delay step, crossover families, Q convention, tiers | `dsp_profile.py list-bundled`, `find-bundled`, `refresh`, `validate`, `open-questions`; interview: `start`, `set-field`, `draft`, `finalize`, `checklist` | a new DSP: the interview, never a sibling's profile | −1.2 | field | `core/project-intake.md` §4 |
| the DSP settings as VERSIONS, and the sheet to type in / леджер, аркуш | v_NNN snapshots, HEAD, diff, the old→new sheet with samples at the processing rate | `state.py --root <proj>/state log \| render <preset> [vN] \| diff \| revert \| registry` | — | 1–3 | field | `rew_tool/state/schema.md` |
| bank a proposed change (the ONLY way a sheet is produced) / банк зміни | a 🟡 snapshot + the settings sheet; then 🟢 on attest | `apply.propose(history, delta, note=…, registry=…)`, `apply.attest(history, version)` (library — from a session, TCC, or `eq_propose`'s deltas) | the delta's channels must exist; a slot mismatch is refused | 1–3 | field | `core/driver-discipline.md` |
| the plan, the phase, the steps and their evidence / план і кроки | phase, steps with evidence that must RESOLVE on disk, decisions, reviewer calls | `process.py <proj>/process plan \| enter-phase \| add-step \| start \| done <id> <evidence> \| skip \| block \| decision \| reviewer \| session-start \| check \| show` | evidence that exists — a done step with none is caught by `check` | any | field | `rew_tool/state/process-schema.md` |
| is the whole project consistent / чи цілісний проект | every machine file: exists, schema, valid, cross-file checks, open questions | `contract.py check <dir> [--json] [--no-rew]` | — | any | field | `core/data-contract-universal.md` |
| move a 2.x project to 3.0; rename legacy fields / міграція | a new 3.0 project beside the old; `dsp.sample_rate_hz → dsp_processing_rate_hz` in `project.json` | `state/migrate.py <old> --into <new>`; `project.py <dir> migrate-fields [--dry-run]` | the source is never touched; two different rates are refused | −1 | field | `core/intake-from-prose.md` |

## K · The Advisor / Critic channel and the community

| what you want | what you get | command / call | needs · refuses without | phase | maturity | read |
|---|---|---|---|---|---|---|
| a second AI's independent review of a package / Критик, Радник | the review text, via a CLI, an API, or a clipboard block for any web chat | `scripts/autosound_ai.py critic <package.md> [trace.csv]`, `advisor …`, `doctor` | `.critic-env` (or clipboard mode); `doctor` says what is missing | review points of every phase | field | `tooling/setup-critic-channel.md`, `core/review-loop.md` |
| the review cadence, deadlocks, audits / як рецензувати | TWO-PASS, when the Arbiter breaks a tie | (doctrine) | — | any | field | `core/review-loop.md` |
| send experience back (a DSP profile, feedback) / зворотний звʼязок | a GitHub Issue, deduplicated, never a confabulated "posted" | `gates/side_effect.py` (dry-run first); `scripts/issue_triage.py` | `gh` and consent | 4 | field | `core/feedback-loop.md` |

## L · Safety and abstention

| what you want | what you get | command / call | needs · refuses without | phase | maturity | read |
|---|---|---|---|---|---|---|
| is it SAFE to sweep this driver at this level / чи безпечний свіп | a pass or a named refusal (no HPF, too-low corner, hot level) | `gates/presweep_safety.require_safe(...)` | the driver's fragility and its protective filter | 0 | field | `phases/phase_0_baseline.md` |
| where does each tool have NO vote / де інструмент мовчить | the abstention table: what governs instead, and the ordering it implies | (doctrine) | — | any | field | `core/estimator-scope.md` |

## M · Health of the installation

| what you want | what you get | command / call | needs · refuses without | phase | maturity | read |
|---|---|---|---|---|---|---|
| does the tooling work here / чи працює інсталяція | the deterministic core, offline | `scripts/smoke_test.py` | python3, numpy, scipy | — | field | `tooling/installation.md` |
| every module's own checks / усі селфтести | one entry point, what CI runs | `scripts/run-selftests.sh` | — | — | field | `CLAUDE.md` of the repo |
| the installers agree; a tag is safe to cut / інсталятори, тег | the shared constants compared; the eight pre-tag checks | `scripts/installer-consistency.py`, `scripts/tag-check.sh vX.Y.Z` | — | — | field | `CHANGELOG.md` (doctrine section) |
