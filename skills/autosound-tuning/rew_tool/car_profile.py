#!/usr/bin/env python3
"""Has this CABIN been described before? — the car-side twin of `dsp_profile.find_bundled`.

`project-intake.md:172` asks one question about two libraries: "first check whether there's already
a profile in `knowledge/dsp/` (and `knowledge/cars/` for this body)". Only half of it was backed by
code. For the processor there is a tool, it returns a clean "no" (`bundled_exact_match: null`), and
a consumer can put the answer in front of the person. For the body there was prose, so the check
happened when a session remembered to go looking — and on a real intake it did, then decided
silently what to do with what it found, and the material went unused for two days until the person
asked directly whether any existed (reported as `ayukhno/autosound-tuning-skill#19`).

**The point is not automation.** It is that "there is prior material for this cabin, here is how
much, do you want it carried as hypotheses?" becomes a question the person is ASKED, instead of a
judgement an agent makes quietly.

⛔ **EXACT match or nothing, and a near miss is never named.** A platform sibling is a different
car: the same shell can carry different doors, different glass and a different floor, and its
numbers do not transfer. The scope rule is `SKILL.md → knowledge/cars`, and the failure it guards
against is not a wrong file being read but a wrong file being *mentioned* — "we have something for
the Passat B7, want it?" is already the damage, because the answer is going to be yes. So this
module offers no suggestions, no fuzzy fallback and no "did you mean": `list_bundled` exists for a
person browsing the library, not for softening a `None`.

The library is markdown on purpose — `knowledge/cars/<body-slug>.md` is read by a person and by a
session, not parsed for numbers, and PART B of one is a checklist of things to VERIFY rather than
facts to cite. So this returns where the file is and what it calls itself, not its contents.

    car_profile.py --find "VW" "Passat" "B8 sedan"
    car_profile.py --list

stdlib only, py3.9+.
"""
from __future__ import annotations

import glob
import os
import re
import sys

#: The method's own cabin library. Absolute, resolved from this module rather than from the
#: caller's cwd -- the same reason `dsp_profile.bundled_dir()` is.
BUNDLED_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "knowledge", "cars")

#: Not a body. The template is the thing you copy to describe a new one, and a lookup that returns
#: it has answered "yes, we know this car" about a file full of placeholders.
NOT_A_BODY = ("_TEMPLATE",)


def bundled_dir():
    """The library's absolute path."""
    return os.path.normpath(BUNDLED_DIR)


def body_slug(make, model, body=""):
    """`("VW", "Passat", "B8 sedan")` -> `vw-passat-b8-sedan`.

    Built rather than searched for, which is the naming rule's whole purpose (`SKILL.md:108`: the
    path comes from the answer, never from a `find`). That also makes the refusals fall out of the
    arithmetic instead of needing rules of their own: a wagon slugs differently from a sedan and so
    does not match it, and a body nobody named slugs short and matches nothing.
    """
    joined = " ".join(str(p or "").strip() for p in (make, model, body))
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", joined.lower())).strip("-")


def title_of(path):
    """The file's own first heading, so a consumer shows what the LIBRARY calls this car.

    Read from the file rather than composed from the caller's three strings: the answer to "is this
    the same car?" must come from the thing being matched, not from the question.
    """
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.startswith("# "):
                    return line[2:].strip()
    except OSError:
        pass
    return ""


def find_bundled_car(make, model, body="", dir_=None):
    """The library's entry for EXACTLY this body, or `None` — which is itself the answer.

    `None` means "nobody has described this cabin here", and that is what a session needs to hear
    before it starts an intake from scratch. It never means "close enough exists": see the module
    docstring for why a near miss is not reported at all.

    Returns `{"slug", "path", "title"}`.
    """
    slug = body_slug(make, model, body)
    if not slug or slug.upper() in NOT_A_BODY:
        return None
    path = os.path.join(dir_ or bundled_dir(), f"{slug}.md")
    if not os.path.isfile(path):
        return None
    return {"slug": slug, "path": path, "title": title_of(path)}


def list_bundled(dir_=None):
    """Every cabin the library describes, as `(slug, path, title)`, slug-sorted.

    For a person browsing, and for a selftest. NOT for turning a `None` from `find_bundled_car`
    into a suggestion -- naming a sibling is the mistake this library's scope rule exists to stop.
    """
    out = []
    for path in sorted(glob.glob(os.path.join(dir_ or bundled_dir(), "*.md"))):
        slug = os.path.splitext(os.path.basename(path))[0]
        if slug.upper() in NOT_A_BODY:
            continue
        out.append((slug, path, title_of(path)))
    return out


def _main(argv):
    if len(argv) > 1 and argv[1] == "--list":
        for slug, path, title in list_bundled():
            print(f"{slug:<28} {title}")
        return 0
    if len(argv) > 2 and argv[1] == "--find":
        found = find_bundled_car(*argv[2:5])
        if found is None:
            print("no exact match — this body is not in the library")
            return 0
        print(f"{found['slug']}\n{found['title']}\n{found['path']}")
        return 0
    print(__doc__.strip().splitlines()[-4].strip(), file=sys.stderr)
    return 2


def _selftest():
    import tempfile

    lib = tempfile.mkdtemp(prefix="autosound_cars_")
    with open(os.path.join(lib, "vw-passat-b8-sedan.md"), "w", encoding="utf-8") as f:
        f.write("# VW Passat B8 sedan — a SINGLE-BUILD CASE STUDY\n\nbody\n")
    with open(os.path.join(lib, "_TEMPLATE.md"), "w", encoding="utf-8") as f:
        f.write("# <Make> <Model> <body>\n")

    assert body_slug("VW", "Passat", "B8 sedan") == "vw-passat-b8-sedan"
    assert body_slug(" vw ", "PASSAT", "b8   sedan") == "vw-passat-b8-sedan", "case and spacing"

    hit = find_bundled_car("VW", "Passat", "B8 sedan", dir_=lib)
    assert hit and hit["slug"] == "vw-passat-b8-sedan", hit
    assert hit["title"].startswith("VW Passat B8 sedan"), hit
    # The title comes off the FILE. Composing it from the caller's own three strings would make
    # the answer to "is this the same car?" a restatement of the question.
    assert "CASE STUDY" in hit["title"], hit

    # -- everything that is NOT this body must come back None, and come back SILENTLY ------------
    # A wagon is not a sedan, a B7 is not a B8, and an unnamed body is not a body. None of these
    # may be softened into a suggestion: naming a sibling is the damage, because the answer to
    # "we have something for the Passat B7, want it?" is going to be yes.
    for miss in (("VW", "Passat", "B8 wagon"),      # different body on the same platform
                 ("VW", "Passat", "B7 sedan"),      # different generation
                 ("VW", "Passat", ""),              # body not named at all
                 ("VW", "Passat", "B8"),            # generation without the body
                 ("", "", ""),                      # nothing asked
                 ("Skoda", "Superb", "B8 sedan")):  # same platform, different car
        assert find_bundled_car(*miss, dir_=lib) is None, miss

    # The template is not a car. A lookup that returns it has answered "yes, we know this cabin"
    # about a file of placeholders -- and it is reachable, because `_TEMPLATE` slugs to `template`
    # only if something strips the underscore, so the guard is on the NAME, not on the slug.
    assert find_bundled_car("", "", "_TEMPLATE", dir_=lib) is None
    assert [s for s, _, _ in list_bundled(dir_=lib)] == ["vw-passat-b8-sedan"], list_bundled(lib)

    # -- and the shipped library answers for the one body it describes --------------------------
    # `dsp_profile`'s own history is the reason this assertion is here: `find_bundled` took a
    # directory argument for months while no library shipped, so every consumer built a private
    # one and the same processor ended up described four times. A lookup with nothing to look in
    # passes its tests and fails its users.
    assert os.path.isdir(bundled_dir()), bundled_dir()
    assert find_bundled_car("VW", "Passat", "B8 sedan") is not None, "the shipped library moved"

    print(f"selftest OK -- exact body matched off the shipped library and off a fixture; six near "
          f"misses (wagon, B7, unnamed body, generation-only, empty, platform sibling) all None "
          f"and unsuggested; the template is not a car. library={bundled_dir()}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "selftest":
        raise SystemExit(_selftest())
    raise SystemExit(_main(sys.argv))
