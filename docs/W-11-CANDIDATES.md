# W-11 candidates — the collection's pool, ranked

**Status:** a ranking for the Arbiter's review, 2026-10-15, on his word «сформуй список кандидатів на W-11». Collection
is still open (S-106): a finding that arrives joins this list; the milestone `W-11 · v3.1.5` opens on his «збір
закінчено», each item then becomes an issue with the four lines, and nothing is built before his `ok` on it. Items are
taken from the records named in «source»; each is checked unfixed when its issue is opened.

Sources: the bus queue `to:skill` (hub #280 #281 #285; deferred #113), this repo's issues (none open; deferred #169 #26),
`docs/TODO.md` (S-104 W-10's review pool, S-103, S-106, S-105), `docs/RESEARCH-2026-10-14-eq-boost-path.md` (#173).
The audit leaves nothing to the skill: TCC's answer on SKL-076 (hub #288).

**The order** (as W-10's): 1) what breaks work in the car now; 2) small and unblocking; 3) found in real use; 4) the
installers; 5) edges and silent failures; 6) text and features; 7) research and rulings. `Risk: high` is data writes,
locks, signatures, installers and the method/TCC seam; it sets the process weight (`hub:seam`). Complexity: XS < 1 h ·
S ~1–2 h · M ~half a day · L a day or more.

## To build — ranked

| # | item | source | class | risk | complexity | model | group |
|---|---|---|---|---|---|---|---|
| 1 | Rounds on one level base: each capture shifted by its `splOffsetdB` from the base round wherever rounds stand side by side (verify, predict/verify, session_report), the shift said; a round's control capture checked outside the changed bands; `capture-check` names an `splOffsetdB` change in a field TCC reads. Mirrors the bench's `levelbase.py` and the playbook's rule, not invented | hub #285 TCC-060 (tcc #198, PAS-015); S-104, the Arbiter «У W-11» | feature (method math) | high (verdicts, the seam) | L | opus · high | Rounds and levels |
| 2 | tcc #199's method part: TCC v1.1.4 passes `under` and `level` through `start_capture`; what the method still owes for unplanned takes' verdict is not named — name it or close it | S-104 (hub #260, PAS-013) | question → defect | high (the seam) | XS to name; S if any | opus · high | Rounds and levels |
| 3 | `failure_reason` finds only a lower-case `error:`; Codex prints `ERROR: …` last, so TCC shows Codex's start banner instead of its refusal (tcc #182) | hub #281 TCC-059 | defect | ordinary | XS–S | opus · medium | Reviewer |
| 4 | The installers resolve TCC's dependencies afresh (PySide6 6.12.0 against the lock's 6.11.2 on the VM); from v1.1.4 TCC's tag carries `constraints.txt` — pass it to `uv tool install`, never fail the install over it | hub #280 TCC-058 (TCC finding 158) | defect | high (installer) | S–M | opus · high | Installers |
| 5 | `install.ps1` still arms the receipt before winget's Git, Claude's `Invoke-Upstream` and uv's: a failed download writes `stopped` over a good receipt with nothing changed (W-10's final review M3, half done in `d4250f3`) | S-104 | defect | high (installer) | S | opus · high | Installers |
| 6 | Uninstall leaves the empty `~/.agents/skills` folders it made | S-104 | defect | high (installer) | XS | opus · medium | Installers |
| 7 | An AMBIGUOUS capture's stored issue names both spellings but not the fix («keep one: rename or delete the other in REW»); TCC's card shows the stored issue, never stdout | S-104 | defect | high (the seam) | XS | opus · high | Captures |
| 8 | A window between `capture-check`'s two REW reads can judge an old take (a stale check, not a wrong record) | S-104 | defect | high (gate verdict) | S–M | opus · high | Captures |
| 9 | `verify`'s summary calls every not-applicable sweep «not checked (not a sweep)» — wrong for a sweep outside the band | S-104 | defect | ordinary (TCC reads it) | S | opus · medium | Captures |
| 10 | `project.py`'s selftest `_check_two_writers_lose_nothing` starved once on Windows CI (a writer waited 60 s, got `Busy`); a red CI by chance, not a user's case | S-104 (CI run 38558929626) | infra | ordinary (test only) | S | opus · medium | CI |
| 11 | `bounded_run` starts the reviewer CLIs with stdin closed (said in v3.1.4's Upgrading) — check that no reviewer needs it | S-104 | check | ordinary | XS | sonnet · medium (trial) | Reviewer |
| 12 | In a folder that names nothing, the description fires on 10 of 26 car-audio queries (resume, de/pl, EMMA, TCC bug reports): the description's recall | S-104 (#170's neutral run, 2026-10-14) | docs (description) + eval | ordinary | M | opus · high | Agent start |

**Groups** (one theme, one review per group, `hub:seam`): **Rounds and levels** 1–2 — `Risk: high`, the full loop and a
Fable seat; **Installers** 4–6 — `Risk: high`; **Captures** 7–9; **Reviewer** 3, 11; **CI** 10; **Agent start** 12.

**Advice for the cut:** take 1–11. Item 1 is what the car hits now (a calibration reset read as a +16.65 dB change)
and what TCC's #198 half waits on; 3–6 are small and found in real use; 7–11 are W-10's own leftovers at the seam.
Rough machine time: Rounds and levels ~1 day, the rest ~half a day together. Item 12 is a measurement first (the eval
on a neutral folder), the description change after; it can wait a wave.

## For the Arbiter's ruling, not to build now

- **The boost path** (#173, research done 2026-10-14): advice option B — a narrow, opt-in `fill` for one dip class
  (minimum phase, narrow, below Schroeder, the gate's PASS, stable across the ellipsoid), capped, with a headroom check;
  the default stays cuts-only until the Passat check has run. Code only after his ruling and that check; until then
  `FAQ.md:133` («the method's EQ only cuts») stays true.

## Closed as audit — back only on his word

The audit's J7 P1 line (S-103, W-10's «Left out as audit»): README and FAQ say «two visits make the tune» with no
condition, while the method owes a further trip in some cases; the de/pl word for row 2 of
`naming-and-structure.md` §1a («Variante»/«wariant») collides with the intake's Phase 5 word (an Advisor round); the
FAQ's dips sentence (`FAQ.md:133`) — a method question, the same as the boost ruling. All text, XS–S each.

## Not to build — waiting for a run or deferred

- **S-017** existing-tune analysis: waits for the Arbiter's walk on the Passat after AYA 17.10.
- **S-021** Phase 1's variants end to end on a fresh system: deferred until after the 3.1.x line.
- **S-055** the min-phase verdict on real data: waits for the next ellipsoid round in the car.
- **S-059** TCC's upgrade path, third case on the VM: waits for the Arbiter's test.
- **S-001** a declared pin vs a split: returns with the first `frozen` run.
- **#169 / hub #113** «learn to listen», **#26** workflow orchestration: deferred, back only on his word.
