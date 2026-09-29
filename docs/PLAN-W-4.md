# W-4 · v3.0.64 — the plan

Opened 2026-09-27 as collection (the Arbiter: «відкрий віху»). `ok` on all thirteen tasks the same day (the
Arbiter: «можеш на всі поставити ок, але ще не робимо - збираємо»). **The collection was closed on 2026-09-29** (the
Arbiter's answer to «з чого починати?»: «Збір W-4 закрито — будувати»). The branch is `wave-2026-09-29`, and the
milestone is `W-4 · v3.0.64`. After W-4 comes `v3.1.0` with TCC `v1.1.0` (hub #220, `docs/RELEASE-PLAN-3.1.0.md`).

**Every row below carries `ok`.** "How" was decided from the code on 2026-09-29.

## One update path (#91, #97, #98, and the clone half of #92 and #99)

Four tasks ask for the same thing from different sides: a machine that updates the skill should end up with the
skill, its tools and its libraries at what was released and tested, with nothing lost on the way. Today three doors
each do a part: `install.sh`, `install.ps1` and TCC's `core/updates.py` (which runs git itself). So the part that is
the same everywhere becomes one stdlib-only script in the skill, `scripts/upkeep.py`, and every door calls it:

| subcommand | what it does | who calls it |
|---|---|---|
| `status --json` | the clone (path, tag, changed files), each tool (path, installed version, available version or `""`, how it was installed), the libraries (installed version each) | TCC's update panel |
| `keep-local [--send]` | the clone's local changes (tracked and new files) → one patch file in `~/.claude/skills/autosound-local-changes/`, checked to reverse-apply before anything is reset; `--send` (only after the person's OK) posts it to the skill as an issue through `gates/side_effect.py` with the version, the files and the diff; then the clone is reset | the installers (when the clone has changes), TCC (in place of the grey button, hub #217) |
| `clone --tag <vX.Y.Z>` | fetch the tag into `refs/tags` (the refspec the installers use, so `describe` works: #92), verify its signature (#99), check it out | TCC's «Оновити Скіл» |
| `tools [--yes]` | every tool the installer installs that is **present** — omp, agy, gh, Claude Code — to its current version, the way it was installed: Homebrew → `brew upgrade`, Claude Code → `claude update`, omp → `omp update`, agy → `agy update`, gh from the installer's own release download → the newest release with its SHA256 checked; old → new said per tool; a tool installed some other way is named and left alone | the installers on a re-run, TCC (hub #219) |
| `libs` | `pip install --upgrade -r requirements.txt` with the Python the method's tools run on (`python3` on PATH; on Windows uv's `~\.local\bin\python3.exe`), the flags the installers use | the installers, TCC |

TCC runs it from its **vendored** skill (always as new as TCC), the installers run the copy in the tag they are about
to check out (`git show FETCH_HEAD:…/upkeep.py`), so the clone at v3.0.63, which has no such script, is not in the
way. Its name and JSON go onto hub #217 and #219 before TCC builds against them.

- **#91** (S-064): `keep-local` above. The installers: a clone with changes no longer fails the checkout with
  "check the network"; they name the files, keep the patch, ask whether to send it (Enter = send, `s` = keep only;
  `--yes` keeps and does not send: sending needs a person), reset, update. The other half — what reached
  `render_report` as a non-dict — was found while building: the round's verdict carries its own `foreign` (a list of
  titles the naming grammar cannot read) and was merged into the same dict as REW's other-file measurements, so with a
  round open the list overwrote the dict. The dict is now `other_file`.
- **#97** (hub #219 TCC-035): `tools` above; the installers call it on a re-run, after one question listing the tools
  and their versions.
- **#98** (S-072): `--upgrade` in both installers' `pip install`, `libs` for TCC, and matplotlib in CI beside numpy and
  scipy. No exact pins: `requirements.txt`'s own note (pins fight other projects in a shared site) still holds on the
  Mac, where the tools run on the machine's `python3`.
- **#92** (S-065): TCC's updater stops running git itself and calls `upkeep.py clone`. One ticket to tcc with #94.

## Signed tags (#99, hub #82 HUB-031)

- The trust anchor is **not** read from the tag being verified (a tag's own `allowed_signers` would vouch for itself):
  the Arbiter's public key is a constant in `install.sh`, `install.ps1` and `upkeep.py` (compared by
  `installer-consistency.py`), and `allowed_signers` in the repo and the fingerprint in `SECURITY.md` are for people.
- `git -c gpg.format=ssh -c gpg.ssh.allowedSignersFile=<temp file from the constant> verify-tag <tag>` after the
  fetch, in both installers and in `upkeep.py clone`. A tag at or after the first signed one (`v3.0.64`) must verify;
  an older one (`--skill-ref v3.0.50`) installs with a line saying it predates signing. A failure stops the install.
  `AUTOSOUND_SKIP_TAG_VERIFY=1` skips it with a visible line (a developer's switch).
- `scripts/tag-check.sh`: red when `gpg.format` is not `ssh` or `user.signingkey` is not the key in `allowed_signers`;
  its ready line says `git tag -s`.
- Tests: a selftest makes a key and signed / unsigned / foreign-signed tags in a temp repo (a subprocess, not a
  session's `git tag`), and runs the installers' verify function against them.
- **Needs the Arbiter:** the signing key in git's config on this Mac (`gpg.format ssh`, `user.signingkey`), and runs of
  the installers on the Windows VM and the Mac before the tag.

## The rest

| item | what | how (decided) |
|---|---|---|
| **#93** (S-066) | omp's refusal cut before its reason | **Built** (`755dd20`): `failure_reason()` shows the `error:` line and what continues it, not bun's source dump; used by the omp route, the CLI rung and `doctor` |
| **#90** (S-062) | progress lines as red mojibake in PowerShell 5 | **Built** (`7eebe2b`): on Windows a piped stderr with no `PYTHONIOENCODING` is ASCII, folded by `console.py`; stdout (the answer) stays UTF-8. The red wrapper under `2>&1` is PowerShell's own; one line in the FAQ's Windows part with #71. Needs one run on the VM |
| **#89** (hub #213) | a file whose `version` names another version | **Built** (`68cba27`): `load()` refuses it with the repair; `state.py repair-version`; `ledger_identity` in `contract.py check` and `state.py verify` (mismatch, duplicate, gap, a slot with no file); no copy path in the skill |
| **#96** (S-071) | installer output slips | **Built** (`cceba5d`): the source said once, one colon per prompt, the heading "What is here, and what will be installed:". Needs the VM run |
| **#94** (S-068) | TCC's update window prints the whole command | a ticket to tcc, with #92 |
| **#95** (S-070) | README's install section | one sentence under the install line (the tag in the URL pins the installer; it installs the newest release), the options as a table (what it does · macOS · Windows, each cell a whole line to paste) and one example with two options; four languages through the Advisor. The pin itself stays (HUB-030) |
| **#71** | README/FAQ name Gemini Pro (High) | README and FAQ say what to pick when agy refuses the model in your region, and the installers' closing line stops naming one model as the critic; four languages through the Advisor |
| **#70** (S-057) | a five-line verdict block on top of six tools | a shared `rew_tool/verdict.py` (at most five lines: the verdict, two or three numbers each with its quantity and source, what to do next); each tool decides its verdict: `predict`, `rew_tool.py analyze-joints`, `eq_propose`, `resonalyze_engine run`, `contract.py check` (after the reply-language line, which stays first, SKILL.md), `verify_prediction` (its bottom verdict moves up). Details below; `--verbose` where a tool truncates. TCC reads only `contract.py --json`; its one change is #91's `other_file` |

## Built on `wave-2026-09-29`, 2026-09-29

Each with its selftest red first where a test could be red: #93 `755dd20` · #90 `7eebe2b` · #89 `68cba27` · #96
`cceba5d` · `upkeep.py` `f1a12f5` · the installers (#91 #97 #98 #99) `25fdcae` · #99's `allowed_signers`,
`SECURITY.md`, `tag-check.sh` `4422b08` · #91's crash (two meanings under `rew["foreign"]`: REW's other-file dict
and the round's list of unreadable titles; the second overwrote the first when a round was open) `1c3a167` · #70
`85f5423` `8688df8` `eb67c91` `78b66c1` · #95 #71 `2542d6e`. Tickets: the `upkeep.py` contract on hub #219 and
#217; hub #221 (SKL-059) to tcc for #92, #94 and the libraries.

Decided while building: #71's FAQ half was already done in W-3's FAQ rework, so #71 is README and the installers'
last screen. #95's options table carries the flags, with one full two-option example per system; whole lines in
the cells would be as wide as the line GitHub cut. #90's FAQ line was dropped: the red wrapper appears only for a
person piping the script by hand in PowerShell 5, and the CHANGELOG says what it is.

**Waiting on the Arbiter:** his signing key in git's config on this Mac; runs of the installers on the Windows VM
and the Mac (#90, #96, #99, #91's installer path) before the tag.

## Order

#93 #90 #89 #96 (built) → `upkeep.py` and the installers (#91 #97 #98 #99) → the tickets to tcc and the answers on
hub #217 / #219 → #70 → #95 #71 through the Advisor → version bump, CHANGELOG, the full suite once, PR, the Arbiter's
runs on the VM and the Mac, the signed tag.
