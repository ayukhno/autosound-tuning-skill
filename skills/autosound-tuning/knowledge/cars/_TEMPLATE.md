# <Car make/model/body> — a SINGLE-BUILD CASE STUDY (NOT a reference of facts)

> **Copy this file to `knowledge/cars/<body-slug>.md`** and record ONE real build, so the next build on the **same body** doesn't re-diagnose the body class from scratch — and as a structural template. The filled worked example is `vw-passat-b8-sedan.md`.
>
> **How to read / fill this file — two parts, treated differently:**
> - **PART A — body-class physics** → transfers as an *expectation* to any car of this exact body (confirm by measurement anyway, but you may reason from it).
> - **PART B — the record of THIS build** → ⛔ **VERIFY ONLY. Never cite as fact, never offer as a starting point.** Driver placement/orientation/coplanarity, enclosure, crossovers, gains, anomaly frequencies **vary build-to-build even on the same body** → write **every PART B item as a CHECK** ("the author's build showed X → measure whether yours does"), never as "your X = Y".
> - **A different body?** The scope is EXACTLY this body. Don't name this profile to the user, don't pull PART B numbers; at most the *generic* body-class tendency from PART A transfers. A platform sibling (same VAG/PSA/etc. platform) is **not** the same body — at most a private hypothesis to verify. Full rule → `SKILL.md → knowledge/cars`.

## PART A — body-class physics (expected on any <body>; confirm anyway)

- **Room gain** — sedan/hatch/wagon LF tendency (a sedan typically lifts the low end; a hatch/wagon leaks more). Budget for it, don't "flatten" it blindly.
- *(add body-class tendencies that hold across builds: a typical cabin-gain hump region, glass/dash geometry tendencies — physics of the SHELL, not of one install.)*

## PART B — the record of THIS build — ⛔ VERIFY ONLY (each line = a CHECK, not a fact)

**How the build is PUT TOGETHER — the install, and it is logic, not physics:**
The standing, physical arrangement the sound meets before anyone tunes: driver mounting angle and
aim, on/off axis, whether **passive filters** sit in the path, enclosure and placement. It changes
only when somebody rebuilds the car, so it is the one kind of per-build detail the knowledge base
is *for* (`references/core/knowledge-architecture.md`). Keep it here and **out of the anomaly
lines below**: an angle explains a dip, it is not the dip, and a row that carries both makes a
measured finding read as a configuration choice. Nothing DIALLED goes here either — crossovers,
delays, EQ and phase angles are the tune's state and live in the project, never in this file.
- □ *(driver positions / aim angles / coplanarity)* → these depend on YOUR install — **never assert coplanarity as fact** (the recurring leak); ask or measure.
- □ *(passive filters in the path — present, and where?)* → ask; a passive between amp and driver changes what every electrical setting downstream means. Enclosure is its own block below.

**Cabin response anomalies — the PHYSICS half: if present, LEAVE them (interference / non-min-phase), don't fill:**
- □ *(anomaly the author's build showed, e.g. a left-door dip ~X Hz)* → measure your own; don't assume the Hz or the side.
- □ *(SBIR notches)* → **never assert a notch frequency as fact**; it follows this build's geometry.
- □ *(cabin nulls / deep dips / room modes the author saw)* → check your own; don't EQ-boost a positional null.

**Drivers / enclosure — from the user's intake or the datasheet, NOT from here:**
- □ *(enclosure type/volume in the author's build)* → yours is whatever the user actually has; don't assume.

**Crossovers that won in the author's build — DATA, not your starting table:**
- *(values)* → ⚠️ derive a specific car's crossovers from baseline + summation (`process-phases` Phase 1); do **NOT** present these before measuring.

**Install polarity & TA — a SUMMATION result of THIS build, NOT a rule:**
- □ *(per-driver polarity / inter-channel timing)* → derive yours by summation (`diagnostic §9`) and the measured latest-arriver (`process-phases` Phase 1); never copy the pattern.

**Techniques (more transferable, still verify by ear/measurement):**
- *(e.g. heavy midbasses → align to the IR peak; LHD/RHD → which side is quieter/delayed for centering.)*

> **Source:** the project's `autosound_context.md`. De-identify before sharing (`feedback-loop.md`): the body class + method, no personal data / full `.mdat`.
