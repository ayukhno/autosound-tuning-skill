# helix_pct6 — read ATF PC-Tool 6 setup files (`.pct6`)

Read only. Python 3.9+, standard library only. Format documented by **amATFpct6**.

> **Warning, shown with every result:** reading `.pct6` has been checked on **HELIX DSP ULTRA S** and
> **HELIX NEXT V EIGHT DSP ULTIMATE** only. Any other model is read at your own risk. In every case, check the
> values against PC-Tool's own screens: PC-Tool versions change, and a new version may store a value differently.

## Use

```python
import helix_pct6 as hp

doc = hp.read_pct6("preset.pct6")        # or hp.read_pct6(file_bytes)
inv = hp.interpret(doc)                   # every value: raw + meaning, JSON-ready
diff = hp.differences(doc, hp.read_pct6("other.pct6"), ignore_save_metadata=True)
rows = hp.check(doc, [{"path": "/ATF/OC[@ON='16']/T[1]/@T", "expected": 4.63, "policy": "display_delay_ms"}])
```

```sh
python3 -m helix_pct6 read FILE --summary          # per-output table: gain, delay, polarity, mute, crossovers
python3 -m helix_pct6 read FILE                    # everything, JSON
python3 -m helix_pct6 diff LEFT RIGHT --ignore-save-metadata
python3 -m helix_pct6 check FILE expected.json
python3 -m helix_pct6 models
python3 -m helix_pct6 selftest                     # the package's tests (see Tests)
```

`-m` runs from `skills/autosound-tuning/rew_tool/`; `helix_pct6/__main__.py` also runs by its path, from any folder.

Exit codes: `0` done · `2` the file could not be read (`error (<kind>)` on stderr) · `3` an input changed while read.

## What it reads

| layer | what |
|---|---|
| container | XOR with `ATFV6` → 4-byte length → one zlib stream → XML. Bounded size, checksum, exact length, no trailing data, no DTD/entities. Errors carry a `kind`: `container` · `checksum` · `truncated` · `limit` · `xml` |
| raw inventory | every attribute with a stable path (`OC[@ON='16']`, `Fil[32]` 1-based), nothing dropped |
| channels | name (CHS), level dB, delay full and as PC-Tool shows it (half up to 0.01 ms), phase, phase mode, polarity, mute, every filter with its state |
| filters | EQ (Fine EQ, LSH, HSH, PK, APF1, APF2), crossovers (Butterworth, Linkwitz confirmed; Bessel, Chebyshev, Self-define documented), bypass |
| routing | each matrix: source → target, source level, links with dB, missing or extra coefficients reported |
| system | RealCenter, Dynamic Bass, SubXpander, RTC and its bands, BT auto-switch, BT/AUX, CONDUCTOR |

States are kept apart: `missing` (no value in the file), `not_saved` (a channel points at a filter the file does
not hold), `off` / `bypassed` / `neutral` (stored but doing nothing), `zero_amplitude` (never 0 dB), `unknown`.
An all-pass at G=0 is `configured`, never `neutral`.

Differences fall into `audio` · `system` · `naming` · `save_metadata` · `ui_state` (LG, PC-Tool's window) ·
`unknown` · `structure`. An unknown field never counts as a match.

## Models

| model | Dev | how far it is checked |
|---|---|---|
| HELIX DSP ULTRA S | 39 | 57 mapping rules (50 confirmed, 6 assumption, 1 unknown), 15 one-change experiments, files from PC-Tool 6.03.03 to 6.05.01 |
| HELIX NEXT V EIGHT DSP ULTIMATE | not yet pinned | checked by the user; recognised as checked once a sample file pins its Dev code |
| any other ATF model | any | read with the ULTRA S rules at the user's risk: delays at an assumed 96 kHz, no A–L channel labels |

Files of Dev 17, 32, 38, 50 and 53 open with the same container; their meaning is not checked.

## Never writes

There is no encoder and no write path: nothing here creates or changes a `.pct6`, and nothing is written next to
an input. The CLI prints to stdout only and re-hashes each input after reading. A test fails the package if its
source gains a write mode, `zlib.compress`, a rename or a delete. A generated file loaded into a processor could
damage it; changes reach the DSP only by hand, in PC-Tool.

## Tests

```sh
python3 skills/autosound-tuning/rew_tool/helix_pct6/__main__.py selftest     # from the repo root
cd skills/autosound-tuning/rew_tool && python3 -m helix_pct6 selftest        # the same, as a package
```

Fixtures are files saved by PC-Tool, never generated. `HELIX_PCT6_FIXTURES` names their folders (`os.pathsep`
between them); by default it is `rew_tool/testdata/helix-pct6/`, which holds the reference file only, so the tests
of the other files are skipped there, never passed. A fixture is looked up at its relative path (`experiments/…`,
`others/`, `versions/`) and, failing that, by its file name in the folder. Error cases build containers in memory.

## Limits

- Only the saved file: no live processor state, nothing about other preset slots.
- Fields in `rules.json` → `unknown` stay raw: root AV, VM, VCO, …, AOM 25, parts of DCM/ABP/MCV2/ATFCOND, OC DG/GD/EqBy/CE/Finit.
- Assumptions stay assumptions: LG as window state, FilBBR as a bypass copy, the CN name table, the ABP BF frequency formula, CONDUCTOR menu items.
- Input-channel MT is kept raw: no experiment calibrates it.

## Credit

Format documented by amATFpct6.
