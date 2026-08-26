# autosound-tuning-skill — conventions this repo has paid for

Each of these was bought with real damage. Working arrangements specific to the author's own
sessions live in `CLAUDE.local.md`, which is not tracked: this repo is public, and internal process
is noise to anyone reading the code.

## Releasing

- **A patch tag is a publication.** `install.sh`, `install.ps1` and the TCC updater all install the
  newest tag matching `v3.*`, so a `3.0.x` tag is on somebody's machine as soon as it is pushed. The
  plugin catalogue is separate and pinned by SHA — it does not move when a tag is cut. To a
  catalogue user a `3.0.x` tag is invisible; to an installer user it *is* the release.
- **Write the Upgrading note BEFORE tagging, and never move a published tag** — a forgotten note
  ships as the next patch. Moving one makes a single version number name two builds, and local
  clones keep showing the old commit, because a plain `git fetch` does not move a tag. The full
  reasoning is in the CHANGELOG's own doctrine section.
- **A tag takes the whole tree**, so its note must describe everything standing in front of it, not
  only the change that prompted it.

## The installers are a TRIPLET

`install.sh`, `install.ps1` and `install.cmd` carry the same decisions three times in three
languages. **A claim checked in one file is not checked.** Run
`python3 scripts/installer-consistency.py`, which compares the constants that must match.

There is no PowerShell on the author's Mac, so the Windows half of any installer change is verified
only when it is RUN — the author does that on Windows VMs (Parallels and UTM) with the one-liner
`irm https://raw.githubusercontent.com/ayukhno/autosound-tuning-skill/main/install.ps1 | iex`
(last confirmed 2026-08-26; the protocol is `scripts/windows-install-test.md`). Until a change has
had that run, say so in the release note.

## Ported maths carries its upstream in the header

A port of somebody else's DSP (Resonalyze's sum-loss metric is the first) starts with a block
`# upstream: OWNER/REPO path @ <sha> (LICENCE) -- <symbols>` and one `# deviation: … -- see …` line
per thing we do differently, in that block, not in a docstring a screen below. `scripts/upstream-drift.py`
lists the upstream commits that touched the file since the sha; **a difference listed as a deviation is
ours, an unlisted one is a drift** — and a deviation recorded anywhere the checker does not look is the
one somebody will "fix back". The licence text goes verbatim into `LICENSES/NOTICE.md`.

## Tests
## Tests

- **`scripts/run-selftests.sh` is the single entry point** — the installer check plus every
  `rew_tool` module's own selftest, 26 in all. It needs `numpy` and `scipy`, and CI runs this exact
  script, so a green run locally is a green run there.
- **A test that shares the implementation's ruler proves nothing.** `xover_select` reported
  `fit=0.00 dB` for a long time while scoring a realization against a target computed by the same
  broken function — the ruler and the part were one object, and a 30 dB error at 80 Hz survived.
  Anchor to a **definition** (a Linkwitz-Riley is −6.02 dB at its own corner because it is
  Butterworth squared) or to an **independent path** (design in ZPK, evaluate in the z plane).
- **Ask of every new test: what would still pass?** The corner anchor pinned family and frequency
  but not steepness, because Butterworth is −3.01 dB at its corner for *every* order. That question
  is what found the two anchors after it.
- **A check whose input is missing must FAIL, not report "no objection."** A first draft of the
  installer checker let a hijacked URL through in exactly that way. It is the same rule the tools
  themselves follow — `references/core/estimator-scope.md`.
