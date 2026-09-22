# W-2 · v3.0.60 — what the session decided while the Arbiter was away

Why this file exists: `docs/PLAN-W-2.md`, *Run without the Arbiter*. Each line gives what was decided,
where (commit or file), and why. A decision that turns out to be wrong is reverted by his word, and
the line gets a note saying so. Nothing here was irreversible: the merge and the tag wait for him.

| # | package | decision | why | where |
|---|---|---|---|---|
| 1 | R | **The layout of the per-project version line.** `state/versions/v_NNN.json`, plus `state/slots.json` (it replaces `registry.json` and every `<preset>/HEAD`), plus `state/legacy/<preset>/` and `state/legacy-map.json`. A version keeps `preset` (the slot it was banked for) and gains `parent` | one line of numbers, and one file saying what each slot holds, which is the Arbiter's model (a preset is the slot a version is fixed in). No new field for what `preset` already says | hub `#195`, the reader-contract comment |
| 2 | R | **At migration the active slot keeps its numbers**, and the other presets are numbered after it | the Passat's journal cites `v_0NN` with no preset, and they are almost all SQ's (the active one); keeping SQ's numbers keeps those citations true without rewriting history. `legacy-map.json` records every move | same |
| 3 | R | **Both layouts are read. The migration is offered with the user's OK, never automatic. A half-migrated project is refused** | "one-way and refusing" (`#195` ask 3) without breaking anything that exists. So it is not `### Breaking`, and the wave stays a patch (the Arbiter: no minor is cut, `WAVES.md` §3.1). The schema number stays 3, because the content of a version did not change | same |
