# Licenses & Notice

License map for this repository:

- Primary license at the root (`LICENSE`): Creative Commons Attribution-ShareAlike 4.0 International — applies to documentation, methods, case studies, .md and .html files, and any material not explicitly marked otherwise.

- Code and executable scripts: `LICENSE-CODE` (MIT License) — applies to source code and executable scripts (.py, .sh, and similar) in `skills/autosound-tuning/rew_tool/`, `skills/autosound-tuning/scripts/`, `skills/autosound-tuning/evals/`, and elsewhere in the repository, unless a specific file states otherwise.

## Third-party assets

Third-party resources (icons, external target curves, data) with their own licenses are listed here:

- `assets/icons/roadmap.svg` — the `route` icon from [Lucide](https://lucide.dev) (stroke color changed to `#888888`), used under the ISC License:

  > ISC License
  >
  > Copyright (c) 2026 Lucide Icons and Contributors
  >
  > Permission to use, copy, modify, and/or distribute this software for any purpose
  > with or without fee is hereby granted, provided that the above copyright notice
  > and this permission notice appear in all copies.
  >
  > THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
  > REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND
  > FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
  > INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS
  > OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER
  > TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF
  > THIS SOFTWARE.

- `skills/autosound-tuning/rew_tool/dsp_math.py` — the junction **sum-loss metric** (`sum_loss`,
  `sum_loss_score`, `align_sum_loss`) is a Python port of the *definition* in
  [Resonalyze](https://github.com/DIMOSUS/Resonalyze) by DIMOSUS, `dsp/VirtualCrossoverAnalysis.cs`
  at commit `1da56dd` (`DetailedLoss`, `SumLossCurve`, `DipExcessPenaltyWeight`,
  `MinBinAmplitudeRatio`, `SumLossLevelGateDb`): the formula and its constants, written fresh in
  numpy with one grid-independence change noted in the source. Resonalyze is used under the MIT
  License:

  > Copyright (c) 2023 dimosus
  >
  > Permission is hereby granted, free of charge, to any person obtaining a copy
  > of this software and associated documentation files (the "Software"), to deal
  > in the Software without restriction, including without limitation the rights
  > to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
  > copies of the Software, and to permit persons to whom the Software is
  > furnished to do so, subject to the following conditions:
  >
  > The above copyright notice and this permission notice shall be included in all
  > copies or substantial portions of the Software.
  >
  > THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
  > IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
  > FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
  > AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
  > LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
  > OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
  > SOFTWARE.

  Each such port names its upstream file and commit in a header line (`upstream: dsp/X.cs @ sha`)
  so drift against the upstream can be checked.

Notes:
- If you include third-party content in a contribution, state its source and license in the PR description.
- Derivative works of the documentation must remain under CC BY-SA 4.0 (ShareAlike).
