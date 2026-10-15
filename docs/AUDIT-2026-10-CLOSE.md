# Closing the October audit — the minimum (skill → TCC → hub → the Arbiter)

**Status:** decided 2026-10-14 · TCC agreed (hub #276, TCC-056 §6) and the Arbiter took the minimum as agreed (#276's
receipt); the minimum is TCC's, in its wave after W-10; the skill has no audit item left, only S-105's check before
W-11 builds · was: proposal, 2026-10-13, on the Arbiter's word: «так, мінімум» — and «чи можна це відкласти на хвилю (зробити
через одну), а наступною закрити ті проблеми, що вже зібрались з використання в машині». TCC agrees or corrects it and
sends its answer to the hub (hub #273, SKL-071); the Arbiter decides once for both products. Nothing here is built
before that.

Inputs: the skill's `docs/PLAN-AUDIT-2026-10.md` (§3 groups, §5 waves), TCC's `docs/PLAN-AUDIT-2026-10.md` at `7e8bff5`
(§2 groups G1–G14, §3 waves, §4 dependencies), and the cost of W-9 (hub #272, SKL-070).

## Where each product stands

- **Skill:** W-8 (v3.1.2) and W-9 (v3.1.3) released — J1a, J2a + J2b (atomic writes, the lock), J3a, J4a, J6a, J8, S1,
  S2, S4a, S6, J7's P3/P9/P10.
- **TCC:** W-8 (v1.1.2) released; W-9 (v1.1.3) built and reviewed, its re-pin to the skill's W-8 tag included, waiting on
  the skill's v3.1.3, which is out. TCC releases it on its own schedule; that is not audit work in this proposal.

## The minimum: what stays

Only what makes the already-built halves work as intended. Both items are TCC's.

| item | why it cannot just be dropped | size (TCC's plan) |
|---|---|---|
| **G8 phase 1** — TCC takes the skill's lock and drops its own around children that lock themselves | the skill's lock is out; until TCC takes it, TCC's own reads under its own lock (the round re-read before a capture check or an import write) do not exclude a terminal's write (TCC's answer on hub #267) | M, ~1 day |
| **G7 with the skill** — the skill's refusals and REW states shown as such | until then a damaged project can read as an empty plan, and REW's three states as one | M, ~1 day |

## Everything else: closed as audit, moved to each product's pool

Each closed item comes back as an ordinary finding if it bites in use.

- **Skill:** J1b, J1c (`sys.path` hygiene — `siblings.py` already loads one module object per file), J3b, J4b (a
  per-call REW deadline — kept in the pool as a small task), J5 (TCC's G9 S1 already debounces the seed), J6b (the
  interpreter, question 2), J6c, J6d (`constraints.txt`), S3 (one path — waits for questions 3–5), S4b, S5, J7's rest
  (the car desk: P1, P2, P4, P5, P7, P8).
- **TCC (its call):** G1, G4 parts 2a and 2b, G5 S3, G6 slices 2–3, G9 S2–S3, G10 M, G11, G12, G13's per-wave slices (the
  ratchet stays), G14 as now.
- **Questions 2–6** of the skill's audit (§1) stop gating anything; each comes back with the pool item it belongs to.

## When

- **The next wave of both products:** collection from use in the car — the findings already gathered, then the rest.
  No audit item in it.
- **The wave after:** the minimum (G8 phase 1, G7), TCC's. Safe to wait one wave: the skill's lock already orders every
  write that goes through the method's CLI (TCC's race test now passes on v3.1.3), and until G7 TCC shows the skill's
  refusals word for word (TCC's plan §3, W-10 row).
- The skill has no audit item left. The plugin catalog need not wait on v3.1.1 for the audit's end: it moves when the
  Arbiter says.

## How the remaining work is run

By SKL-070 (hub #272), A and B: the full review loop only for risky code (data writes, locks, signatures, installers, the
seam between the products) — G8 phase 1 is such code; ordinary code gets its group's review and none per task; one final
review per wave; models by role (`hub:seam`, decided by the user 2026-10-14, hub #278). The re-pin order and N2 stay: the skill tags first, TCC runs its suite on each skill candidate, TCC re-pins in its
next wave.
