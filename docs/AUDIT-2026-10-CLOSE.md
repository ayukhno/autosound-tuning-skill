# Closing the October audit — a joint proposal (skill → TCC → hub → the Arbiter)

**Status:** proposal, 2026-10-13. Written by the skill on the Arbiter's request («мені подобається твоя ідея, але її треба
синхронізувати з аудитом ТСС»). TCC agrees or corrects it and sends its answer to the hub; the Arbiter decides once for
both products. Nothing here is built before that.

Inputs: the skill's `docs/PLAN-AUDIT-2026-10.md` (§3 groups, §5 waves), TCC's `docs/PLAN-AUDIT-2026-10.md` at `7e8bff5`
(§2 groups G1–G14, §3 waves, §4 dependencies), and the cost of W-9 (hub #272, SKL-070).

## Where each product stands

- **Skill:** W-8 (v3.1.2) and W-9 (v3.1.3) released. Done of the joint list: J1a (contract 1), J2a + J2b (atomic writes,
  the lock), J3a (unreadable is not empty), J4a (REW in three states, the read-back), J6a (honest installs), J8 (what the
  model is told), S1, S2, S4a, S6, and J7's P3/P9/P10. Left in the plan: W-10 (J1b, J4b, S4b, S5, J5), W-11 (J1c, J3b,
  S3, J6b, J6c, J7's rest), W-12 (J6d).
- **TCC:** W-8 (v1.1.2) released; W-9 (v1.1.3: G5 S1+S2, G9 S1, G8 phase 0, G6 slice 1, G3, G4 part 1, G7 now, G10 S,
  G13 slice, the re-pin to the skill's W-8 tag) built and reviewed, waiting on the skill's v3.1.3, which is out. Left in
  its plan: W-10 (G5 S3, G7 with the skill, G6 slice 2, G11, G4 part 2a), W-11 (G8 phase 1, G9 S2, G6 slice 3), W-12+
  (G9 S3, G10 M, G12, G4 part 2b), G13/G14 every wave, J7 screens after a car walk.

## The rule proposed

Keep what protects a person's tune or data, what a person sees go wrong, and what the other product is blocked on.
Close the rest as «not doing», each with one line why. After this, findings come from use (collection) again; a closed
item that turns out to bite comes back as an ordinary finding.

## Joint items

| item | skill side | TCC side | proposal | why |
|---|---|---|---|---|
| J2 · one lock | done (W-9) | G8 phase 1: adopt the skill's lock, drop TCC's own around self-locking children | **keep** (TCC) | finishes the data-loss fix: today TCC's reads under its own lock do not exclude a bare CLI write (TCC's #267 answer) |
| J3/J4 · refusals and REW states on screen | done (W-8) | G7 with the skill | **keep** (TCC) | a person sees a named refusal instead of an empty plan or "missing — measure it" |
| J1 · contract handshake | done (J1a) | G5 S3 (contract 1) | **keep** (TCC) | small; completes what TCC's W-9 shipped |
| J1 · `sys.path` out of the closure | J1b (W-10), J1c (W-11) | conftest re-points `rew_api` (prerequisite) | **close**, unless TCC names a failure it sees | `siblings.py` (W-8) already loads one module object per file; what is left is hygiene |
| J8 · what the model is told | done (W-9) | G11 (S×6) | **keep** (TCC) | small; the three routes say the same rules |
| J6 · constraints from TCC's tag | J6d (W-12) | G4 part 2a (`constraints.txt` in every tag, the updater's `-c`) | **keep** | a dependency release can break a fresh install today; TCC first, the skill's installers follow |
| J6 · the interpreter | J6b (question 2) | — | **keep** (skill) | which Python runs the method decides whether an install works |
| J6 · signed `SHA256SUMS` | J6c | — | **close** | the engine archive is already checked against the sums of the same signed release |
| J5 · the seed preview | K-4 dry run | G9 S3 switches to it | **close**, unless TCC's G9 S1 (debounce and cache, built) leaves a measured problem | S1 already stops the seed-per-keystroke |
| §4.1 #6 · `Process.capture_history()` readers | not in the skill's plan | G6 slice 2 | **close** both | TCC keeps its own fold with parity tests, as its plan already allows |
| J7 · the car desk (P1, P2, P4, P5, P7, P8) | text after a car walk (question 6) | screens after the text | **move to the product pool** | product work for a collection, not an audit item |

## The skill's own items

| item | proposal | why |
|---|---|---|
| J4b · a per-call deadline over connect and read | **keep that part only** | a REW that hangs hangs the session; the rest of J4b (thread-local URL, the 12 callers narrowed, the stub's recorded shapes) **close** |
| S3 · one path, virtual-first split by phase | **keep**, after questions 3–5 | it is the method's own text — what a session reads while tuning |
| J3b · gate parity, `check_schema` for the glossary, migration hints, `strict=` everywhere | **close** | W-8's strict reads cover the cases that lost data; the rest is consistency |
| S4b · a smoke run per verb, golden key sets | **close** | tests for the tests; TCC's G12 holds the seams TCC reads |
| S5 · documents against the commands, dead references | **close as a wave**; fix when touched | `docs-check` already holds the rules that misled a session |

## TCC's own groups — the skill's outside view (TCC decides)

| group | outside view |
|---|---|
| G1 · boundaries say what happened (a hung turn, errors swallowed) | **keep** — a person sees a hang |
| G9 S2 · one helper, one FIFO lane | **only with G8 phase 1, and only if a measured problem stays** |
| G9 S3 · two-phase constructor, lazy `mcp` | **close**, unless start-up time is a complaint |
| G6 slice 3 · one reader per skill file | **close**, unless a mismatch bites |
| G10 M · `setData`, the crash protocol | **keep if the curve window still crashes** (TCC's protocol: 5/40 before); otherwise close |
| G12 · tests at the seams | **keep the wheel-install smoke job and `pytest-timeout`** (a broken wheel would ship unseen); close the rest |
| G13 · structure | **keep the ratchet** (the window may not grow); extract only when touching, no slice per wave |
| G4 part 2b · the scheduled fresh-resolve job | **close** |
| G14 · hygiene | as now: when nearby |

## How the remaining work is run

Both products by SKL-070 (hub #272) A and B: the full review loop only for risky code (data writes, locks, signatures,
installers, the seam between the products), one review for ordinary code, one final review per wave; models by role.
The re-pin order and N2 stay as they are: the skill tags first, TCC runs its suite on each skill candidate, TCC re-pins
in its next wave.

## What it saves

- **Skill:** five audit groups and the halves of two more close; four items stay (J4b's deadline, J6b, S3, J6d),
  each an ordinary task in a collection wave.
- **TCC:** by its own sizes, roughly G6 slices 2–3 (~14 h), G9 S2/S3 (~36 h, or only what a measurement asks for), most
  of G12 (~1.5 days), G4 part 2b, and the per-wave G13 slices.
- **The plugin catalog** need not wait on v3.1.1 for the audit's end: it moves when the Arbiter says.
