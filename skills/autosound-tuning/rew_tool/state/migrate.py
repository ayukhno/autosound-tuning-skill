"""One-shot 2.x -> 3.0 project migration — the bridge an existing tune crosses once.

3.0 is a format break, not an evolution: the 2.x skill stays usable as its own release for anyone
who wants it (no GUI, no TCC), and nothing in 3.x reads a 2.x file. This script is the only thing
that reads both, and it is deliberately a separate script rather than a compatibility layer inside
the readers — a shim never gets removed, a migration finishes.

What it does, per project:

1. **EQ strings -> band objects** (the old v1 -> v2 step, still needed: a 2.x project may hold
   ledgers older than its own writer). `"PK 1000 -9 Q2"` -> `{"type": "PK", "f": 1000, ...}`,
   including the `LS`/`HS` shorthand the hand-authored files actually use.
2. **Identity out of the ledger, into `project.json`** (SCR-001). `slot`/`descr`/`role`/`order`/
   `hidden` become `channels[]` entries keyed by `code`; `tag_value` becomes
   `hardware.controls[<tag>]`. The newest snapshot carrying a field wins, and a value already in
   `project.json` is never overwritten — that file is the owner, and a human who has already
   answered intake outranks whatever a year-old snapshot said.
3. **`project_rev` stamped on every snapshot** (SCR-024). All history gets the SAME revision — the
   one this migration produces — because 2.x recorded nothing about which facts were in force
   when, and inventing a per-snapshot revision would be fabricating provenance. What that costs is
   stated plainly rather than hidden: after migrating, a pre-migration snapshot cannot tell you
   that its driver was replaced halfway through. Snapshots taken from here on can.
4. **Every machine file's `schema_version` -> 3**, the one number that now answers "which format
   is this project in" (`contract.py`'s `FORMAT_VERSION`).

Into a new project, never over one: `--into` a folder that holds a project's ledger (`state/`
with a version, `slots.json`) or `dsp_profile.json` is refused before anything is written, naming
each -- a ledger version once written is never written over, so a re-run into the project an
import made is refused too (#134). A `project.json` there alone is merged into, no value in it
overwritten. And it refuses to write any file that does not validate afterwards — a migration
that produces an invalid project is worse than one that stops.

Usage:
    python3 migrate.py <old-project-dir> --into <new-project-dir>             import its current state
    python3 migrate.py <old-project-dir> --into <new-project-dir> --dry-run   say what would move, write nothing
    python3 migrate.py selftest

In place (`migrate.py <project-dir>` alone) is not offered: `_main` refuses it, exit 2, and names
the import.
"""
from __future__ import annotations

import copy
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
_PARENT = os.path.dirname(_HERE)
if _PARENT not in sys.path:
    sys.path.insert(0, _PARENT)

import state as _state  # noqa: E402

import dsp_profile as _dsp_profile  # noqa: E402
import project as _project  # noqa: E402


def _siblings():
    """`rew_tool/siblings.py`, by its path: how this module reaches a sibling (skill #137).

    The same text in every module that loads a sibling -- only the `here` line differs with the file's folder;
    scripts/contract-guard.py holds the copies identical.
    """
    import hashlib
    import importlib.util
    here = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    name = "_autosound_" + hashlib.sha1(here.encode("utf-8")).hexdigest()[:8] + "_siblings"
    module = sys.modules.get(name)
    if module is None:
        spec = importlib.util.spec_from_file_location(name, os.path.join(here, "siblings.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # Published only once it has run: a thread racing this first call never gets a half-run siblings.py.
        module = sys.modules.setdefault(name, module)
    return module


def _project_io():
    """`rew_tool/project_io.py`: how this module writes the files it owns (skill #135)."""
    return _siblings().load("project_io.py")


#: 2.x row field -> the `project.json` field it becomes, where the NAME changed too.
#: `MOVED_TO_PROJECT_JSON` covers the fields that kept their name; this covers the one that did
#: not — and it is the one the released 2.x line actually used. `helix_ch` holds the DSP output
#: letter; `slot` is the same fact under the vendor-neutral name 3.0 gave it (a MUSWAY has slots
#: too, and calling the column "Helix" was always wrong for anything else).
RENAMED_TO_PROJECT_JSON = {"helix_ch": "slot"}


def migrate_snapshot(raw):
    """Pure transform: one 2.x snapshot -> 3.0, returned with the identity it gave up.

    Returns `(snapshot, identity)` — `identity` is `{code: {field: value}}` for whatever this
    snapshot was carrying, so the caller can fold it into `project.json`. The snapshot itself comes
    back without those fields, with structured EQ, and at the current schema version.
    """
    out = copy.deepcopy(raw)
    out["schema_version"] = _state.SCHEMA_VERSION
    identity = {}
    for tier in _state.tier_names(out):
        for code, row in (out.get(tier) or {}).items():
            eq = row.get("eq")
            if isinstance(eq, list) and eq and isinstance(eq[0], str):
                try:
                    row["eq"] = [_state.eq_band_from_str(s) for s in eq]
                except ValueError as exc:
                    # A band string 2.x wrote that names no frequency is the version's refusal, naming its row (#134,
                    # batch 4's re-review M2); `import_current_state` puts the file in front. A bare `ValueError`
                    # named no file, and the command line takes no `ValueError` for a refusal.
                    raise _state.SnapshotError(f"{tier}.{code}.eq: {exc} -- give the band its frequency in Hz (e.g. "
                                               f"`PK 1000 -3 Q2`) or remove it from that version, then run the import "
                                               f"again") from exc
            renamed = {}
            for field in _state.MOVED_TO_PROJECT_JSON:
                if field not in row:
                    continue
                value = row.pop(field)
                if value is None:
                    continue
                target = RENAMED_TO_PROJECT_JSON.get(field)
                if target is None:
                    identity.setdefault(code, {})[field] = value
                else:
                    renamed[target] = value
            # Renamed fields fill gaps only. A row carrying BOTH `helix_ch` and `slot` keeps
            # `slot`: whatever wrote the newer name did so deliberately, and the old one beside it
            # is leftover.
            for target, value in renamed.items():
                identity.setdefault(code, {}).setdefault(target, value)
            # `tag` stays on the row (it is structural: WHICH control affects this channel), but a
            # `tag_value` that travelled with it needs the tag name to find its new home.
            if "tag_value" in identity.get(code, {}) and row.get("tag"):
                identity[code]["_tag"] = row["tag"]
    return out, identity


def fold_identity(data, identity):
    """Merge collected identity into a `project.json` dict. Existing values are never overwritten.

    Returns the number of fields actually added, so a caller can tell "nothing to do" from "done".
    """
    added = 0
    rows = data.setdefault("channels", [])
    by_code = {r.get("code"): r for r in rows if isinstance(r, dict)}
    controls = data.setdefault("hardware", {}).setdefault("controls", {})
    for code, fields in identity.items():
        fields = dict(fields)
        tag = fields.pop("_tag", None)
        tag_value = fields.pop("tag_value", None)
        if tag and tag_value is not None and tag not in controls:
            controls[tag] = _project.fact(tag_value, source="user")
            added += 1
        if not fields:
            continue
        row = by_code.get(code)
        if row is None:
            row = {"code": code}
            rows.append(row)
            by_code[code] = row
        for field, value in fields.items():
            if row.get(field) in (None, ""):
                row[field] = value
                added += 1
    return added


def _looks_like_project_json(data):
    """A `project.json` has `channels`/`car`/`dsp` blocks and no `groups`; a profile is the reverse."""
    if not isinstance(data, dict) or "dsp_profile" in data or "groups" in data:
        return False
    return "channels" in data or ("dsp" in data and "car" in data)


def rename_profile_fields(profile):
    """Rewrite field tokens 2.x wrote to the names 3.0's vocabulary knows. Returns what changed.

    3.0 closed `FIELD_VOCABULARY`, and the token it refuses most often is `delay_ms` — which is
    what 2.x's OWN examples wrote (its `dsp_profile.py` selftest fixture and MUSWAY stub both use
    it). So a profile written exactly as the released skill demonstrated is invalid at 3.0, and
    the migration used to leave it that way with a warning: the run reported success and
    `contract.py check` called the profile broken from then on, forever, until somebody hand-edited
    a file they had no reason to suspect (2026-08-12).

    Only the near-miss table is applied — the same mapping the validator already uses to say "did
    you mean". Renaming on a guess would be worse than refusing: a token nobody recognises may be
    a real capability this profile is the only record of.
    """
    # The file is `{"dsp_profile": {...}}`; a hand-written one is sometimes the body alone. Both
    # shapes exist in the wild and `validate_profile` accepts either, so this has to as well —
    # reading only the top level found no groups and silently renamed nothing.
    if _looks_like_project_json(profile):
        # Handed `project.json` instead of a profile, this used to return [] — a silent no-op that
        # reads as "nothing to rename" while `dsp.sample_rate_hz` stays on the old name forever
        # (measured on a live project's copy, 2026-08-26). An empty result must not stand in for
        # "I did not look here": refuse by name and point at the tool that does look.
        raise ValueError(
            "rename_profile_fields was handed a project.json, not a DSP profile: it renames profile "
            "fields only and would have reported nothing while `dsp.sample_rate_hz` stayed. For the "
            "project file run `project.py <project-dir> migrate-fields`.")
    body = profile.get("dsp_profile") if isinstance(profile.get("dsp_profile"), dict) else profile
    renames = []
    # Top-level: `sample_rate_hz` -> `dsp_processing_rate_hz` (2026-08-25). The old name never said
    # WHICH rate it is and got confused with the capture rate; readers accept both, and migration is
    # where the file itself moves to the canonical name.
    if "sample_rate_hz" in body and _dsp_profile.PROCESSING_RATE_KEY not in body:
        body[_dsp_profile.PROCESSING_RATE_KEY] = body.pop("sample_rate_hz")
        renames.append(f"sample_rate_hz -> {_dsp_profile.PROCESSING_RATE_KEY}")
    for index, group in enumerate(body.get("groups") or []):
        fields = group.get("fields")
        if not isinstance(fields, list):
            continue
        for at, token in enumerate(fields):
            better = _dsp_profile.FIELD_NEAR_MISSES.get(token)
            if better and token not in _dsp_profile.FIELD_VOCABULARY:
                fields[at] = better
                renames.append(f"groups.{index}.fields: {token} -> {better}")
    return renames


def channel_summary(snapshots):
    """`{tier: {"total": n, "off": n}}` derived from the snapshots being migrated (SCR-016).

    Derived, not invented: the codes are the ones this migration just read, and `off` is a real
    ledger field. Without this a migrated project opens with an empty "Project params" panel —
    found by running the real thing, not by a test — even though the count was sitting in the very
    files being rewritten.

    Newest snapshot wins for a code's `off` flag; the code set is the union across snapshots, so a
    channel that exists in one preset and not another is still counted once.
    """
    seen = {}
    for snap in snapshots:  # oldest first, so later writes overwrite earlier ones
        for tier in _state.tier_names(snap):
            rows = snap.get(tier) or {}
            for code, row in rows.items():
                seen.setdefault(tier, {})[code] = bool(row.get("off"))
    return {
        tier: {"total": len(codes), "off": sum(1 for is_off in codes.values() if is_off)}
        for tier, codes in seen.items()
        if codes
    }


def snapshot_paths(project_dir):
    """Every `v_NNN.json` under `<project>/state/`, oldest first per preset.

    Ordered because "the newest snapshot carrying a field wins" is only meaningful in order.
    Dot-directories are skipped for the same reason `contract.py` skips them — a consumer app's
    scratch directory is not a preset.
    """
    root = os.path.join(project_dir, "state")
    if not os.path.isdir(root):
        return []
    out = []
    for preset in sorted(n for n in os.listdir(root)
                         if not n.startswith(".") and os.path.isdir(os.path.join(root, n))):
        d = os.path.join(root, preset)
        versions = sorted(fn for fn in os.listdir(d)
                          if fn.endswith(".json") and _state._VER_RE.match(fn[:-5]))
        out.extend(os.path.join(d, fn) for fn in versions)
    return out


def _read_json(path):
    # Through the ledger's own door, so a 2.x project whose snapshots were written on a machine
    # with a non-UTF-8 default says which file and what to run (TCC-007) instead of ending the
    # migration with a `UnicodeDecodeError` from inside `json`. This is the likeliest place to meet
    # one: an old project is by definition one written before the encoding was named.
    return _state._read_snapshot_json(path)


def _write_json(path, data):
    _project_io().atomic_write_json(path, data, indent=2, sort_keys=True, ensure_ascii=False)


class IntoRefused(Exception):
    """`--into` names a folder the import cannot make a new project in: it holds a project's ledger or DSP profile
    already (#134, batch 4's re-review, the probe of `--into`). Neither an `OSError` nor a `ValueError`: the command
    line matches `is_into_refused` on its class."""
    is_into_refused = True


def project_there(new_dir):
    """What `new_dir` holds of a project that the import would write over, each named: `["state/SQ/ (2 versions)",
    "state/slots.json", "dsp_profile.json", ...]`, empty when it holds none (#134, batch 4's re-review, the probe of
    `--into`).

    The ledger is any line of it: a folder under `state/` holding a version (the per-preset layout, the one the import
    writes), the per-project `state/versions/` and `state/slots.json`; a version's name is read in any letter case. A
    `dsp_profile.json` -- a file, a folder or a link -- is the project's profile. A `project.json` alone is not here:
    the import merges into it and never overwrites a value (`fold_identity`)."""
    found = []
    root = os.path.join(new_dir, "state")
    if os.path.isdir(root):
        for name in sorted(os.listdir(root)):
            path = os.path.join(root, name)
            if name.startswith("."):
                continue                        # a front end's scratch folder is no line, as `snapshot_paths` reads
            if name == _state.SLOTS_FILE:
                found.append(f"state/{name}")
            elif os.path.isdir(path):
                n = sum(1 for fn in os.listdir(path)
                        if fn.lower().endswith(".json") and _state._VER_RE.match(fn[:-5].lower()))
                if n or name == _state.VERSIONS_DIR:
                    found.append(f"state/{name}/ ({n} version{'' if n == 1 else 's'})")
    if os.path.lexists(os.path.join(new_dir, "dsp_profile.json")):
        found.append("dsp_profile.json")
    return found


def _into_refused(new_dir, held, landed=None):
    """The refusal of `--into` over a project that is there, naming what it holds and the way on; `landed` says what this
    run wrote before a version's name turned out taken (the exclusive claim's backstop), where nothing else was."""
    apply_py = os.path.join(_HERE, "apply.py")
    wrote = f"{landed}, and no ledger version or profile was written over" if landed else "nothing was written"
    return IntoRefused(
        f"--into {new_dir} holds a project already: {', '.join(held)} -- the import makes a NEW project, and a ledger "
        f"version or a profile once written is never written over; {wrote}. Import into a new, empty folder (--into "
        f"<new folder>), or, to bring the 2.x values into this 3.0 project, bank them there with the method's own "
        f"bank: python3 {apply_py} {new_dir} propose <delta.json>")


def import_current_state(old_dir, new_dir, dry_run=False):
    """Carry a 2.x project's CURRENT state into a fresh 3.0 project. History stays behind.

    The supported way across, chosen over an in-place migration (user, 2026-08-12). What moves is
    what a car actually is right now: which channel is on which output, its crossovers, delay,
    gain, polarity and EQ, plus the DSP profile. What does not move is the journal, the process
    state and every snapshot but the newest.

    That asymmetry is the point, and it is not a shortcut:

    - **It removes a lie the in-place migration had to tell.** 2.x recorded nothing about which
      facts were in force when, so migrating history meant stamping every old snapshot with one
      invented revision — provenance that reads as real and is not.
    - **The new project is a NEW project**, so it goes through phase −1 and 0 in 3.0 like any
      other. Intake is a review rather than an interrogation, because the answers are already
      filled in — and the flaw map and target curve, which 2.x never collected, get recorded
      properly instead of being waived.
    - **The old project is untouched.** It still opens in 2.x, which is where its history is
      readable. Nothing here can lose it, because nothing here writes to it.
    - **The new project is new.** A folder that holds a project's ledger or DSP profile already is refused before
      anything is read or written (`IntoRefused`, naming each; #134, batch 4's re-review): the import wrote its
      `v_001.json` and `HEAD` over a ledger line the project had banked on, and its profile over the project's, and
      said "imported". A re-run into the project an import made is refused the same way. A `project.json` alone is
      merged into, never a value overwritten. The version is claimed by creating its file (`create_exclusive`); a
      name taken by then is the same refusal, saying what this run had written.
    """
    held = project_there(new_dir)
    if held:
        raise _into_refused(new_dir, held)
    report = {"project_dir": new_dir, "source": old_dir, "snapshots": [], "identity_fields": 0,
              "channel_summary": {}, "files": [], "warnings": [], "imported_from": old_dir}
    paths = snapshot_paths(old_dir)
    if not paths:
        # Two very different projects land here, and telling them apart is the difference between
        # a useful sentence and a dead end. A project with prose state HAS a tune — it just never
        # had a ledger, because it predates one. Sending its owner away with "nothing to import"
        # reads as "your work does not count" (found on a competition-winning project, 2026-08-13).
        prose = [name for name in ("autosound_context.md", "audit-trail.md",
                                   "tuning-changelog.md", "tuning-changelog.txt")
                 for base in (old_dir, os.path.join(old_dir, "rew_analitic"))
                 if os.path.isfile(os.path.join(base, name))]
        if prose:
            raise SystemExit(
                f"{old_dir} keeps its state in prose ({', '.join(sorted(set(prose)))}), not in a "
                f"ledger — so there is nothing for this script to read, and nothing wrong.\n\n"
                f"Bringing it across is a READING job, not a conversion: open the project in a "
                f"3.x session and follow `references/core/intake-from-prose.md`. The channel map "
                f"becomes project.json, the DSP settings become the first snapshot, the naming "
                f"convention becomes the glossary, the cabin anomalies become the flaw map — each "
                f"confirmed before it is written, and the prose left exactly as it is."
            )
        raise SystemExit(f"no ledger snapshots under {os.path.join(old_dir, 'state')} — "
                         f"nothing to import. A 2.x project keeps them in `state/<preset>/v_NNN.json`.")

    # Identity is accumulated across ALL snapshots (a `descr` may only appear in an old one), but
    # only the NEWEST snapshot per preset becomes a ledger in the new project.
    identity, newest = {}, {}
    for path in paths:
        raw = _read_json(path)
        try:
            snap, found = migrate_snapshot(raw)
        except Exception as exc:  # noqa: BLE001 -- matched by its attribute below; anything else still raises
            # The version's own refusal -- an EQ band with no frequency, its way on with it -- names the version (#134,
            # batch 4's re-review M2); a bug in the transform is raised as it is.
            if not getattr(type(exc), "is_snapshot_error", False):
                raise
            raise _state.SnapshotError(f"{path}: {exc}; nothing was imported") from exc
        for code, fields in found.items():
            identity.setdefault(code, {}).update(fields)
        newest[os.path.basename(os.path.dirname(path))] = (path, snap)

    # The import's refusals first, each on a read that holds nothing (#141, R27): the folder `--into` names may be no
    # project at all -- a mistaken target -- and a hold taken before them left the lock's `.autosound/` there under every
    # refusal. The reads of the new folder's `project.json` here decide only whether to refuse: a newer method's file,
    # the versions, the old profile, and the facts the import would write -- that file with the import merged in,
    # checked as `Project.save` checks them (a channel code twice), which `save` decided under the hold and a dry run
    # never asked. A dry run only reads, and takes no lock: its report is that merge.
    proj = _project.Project(new_dir)
    io_ = _project_io()
    _facts_to_merge_into(proj, io_)
    _check_versions(old_dir, newest, report)
    profile = _old_profile(old_dir, report, io_)
    _project.validate(dict(_merged(proj, io_, identity, newest, old_dir, report), project_rev=0))
    if not dry_run:
        # Then the new project's writer lock, from a fresh read of its `project.json` to the import's last write (#141,
        # R14, R23): the import's facts are merged into that file as it stands under the hold, so a change another
        # writer made since the reads above is not written over. Of the import's refusals two can come under the hold,
        # no other: such a change -- a `project.json` another writer made a newer method's, unreadable, or one the merge
        # leaves `save` refusing -- refused before anything is written; and a version's name another writer took since
        # the look, refused once `project.json` has landed, saying so (`_into_refused`). The lock's own -- busy, a lock
        # or a folder that cannot be made -- come at the hold and at the first write. Nothing slow runs under it --
        # files read, merged and written. A profile's stamp asks git, so that is asked first, with the lock still free,
        # and the wait read: a bad one is exit 2 before anything.
        if profile is not None:
            _dsp_profile._ready_to_hold()
        with _project._hold(new_dir):
            _write_import(proj, new_dir, _merged(proj, io_, identity, newest, old_dir, report), newest, profile, io_)
    report["project_rev"] = proj.load()["project_rev"] if not dry_run else 1
    report["files"].append("project.json")
    if profile is not None:
        report["files"].append("dsp_profile.json")

    report["warnings"].append(
        "History stayed behind on purpose: the journal, the process state and older snapshots are "
        "still in the old project, which still opens in 2.x. This project starts at phase −1.")
    return report


def _facts_to_merge_into(proj, io_):
    """The new folder's `project.json` as it stands -- the empty project where there is none -- refused when a newer
    method wrote it, before this copy's version is stamped over it, in `Project.save`'s words (#136, audit T-21):
    stamped first, `save` saw v3 and wrote the newer file down."""
    data = proj.load()
    newer = io_.newer_schema(data, _project.SCHEMA_VERSION)
    if newer is not None:
        raise _project.ProjectError(f"{proj.path}: the facts to write are schema v{newer} and this method writes "
                                    f"v{_project.SCHEMA_VERSION} -- writing them would write them down, so nothing "
                                    f"was written; {io_.UPDATE_THE_METHOD}")
    return data


def _merged(proj, io_, identity, newest, old_dir, report):
    """The new folder's `project.json`, read again -- under the new project's lock, for a real import -- and refused
    if a newer method wrote it since the first read, with the import's facts merged in: the identity the versions
    carried, the channel summary, where it came from."""
    data = _facts_to_merge_into(proj, io_)
    data["schema_version"] = _project.SCHEMA_VERSION
    report["identity_fields"] = fold_identity(data, identity)
    if not data.get("channel_summary"):
        data["channel_summary"] = channel_summary([snap for _p, snap in newest.values()])
    report["channel_summary"] = data.get("channel_summary") or {}
    # Where this came from, on the record. Not a flag anything BEHAVES on — the new project is a
    # new project — just the provenance a later reader will want.
    data.setdefault("imported_from", os.path.abspath(old_dir))
    return data


def _check_versions(old_dir, newest, report):
    """Each version the import carries, stamped `v_001` and checked as this method checks a version, before a single
    byte is written."""
    for preset, (path, snap) in sorted(newest.items()):
        snap["version"] = "v_001"
        snap["project_rev"] = 1
        snap["note"] = (f"imported from {os.path.relpath(path, old_dir)} in {old_dir} — "
                        f"the state this car was in when it moved to 3.0")
        try:
            _state.validate(snap)  # before a single byte is written
        except ValueError as exc:
            # A version this method's check refuses is the import's refusal, naming its file (#134, batch 4's re-review
            # N2): a bare `ValueError` named no file, and the command line takes no other `ValueError` for a refusal.
            raise _state.SnapshotError(f"{path}: {exc} -- it does not pass this method's check as it stands, so "
                                       f"nothing was imported") from exc
        report["snapshots"].append(f"{preset}/v_001.json (was {os.path.basename(path)})")


def _old_profile(old_dir, report, io_):
    """The old project's DSP profile, read and checked before the first write: the profile to carry, or None (#134,
    batch 4's re-review, Out of Scope 4). Read after the new `project.json` and the ledger were written, a profile
    refused -- cut off, a newer method's, one holding a `project.json` -- left the new project half made, and its line
    did not say what had landed. It is read as the profile's own reader reads it (`load_profile`): a file there and
    unreadable is refused, a folder in its place too; no file is no profile, and one that does not validate is a
    warning, not carried."""
    old_profile = os.path.join(old_dir, "dsp_profile.json")
    try:
        profile = _dsp_profile.load_profile(old_profile)
    except FileNotFoundError:
        profile = None
    if profile is not None:
        if _looks_like_project_json(profile):
            # `rename_profile_fields`' refusal, with its file and the way on (M2): a bare `ValueError` was a traceback.
            raise io_.Unreadable(old_profile, "holds a project.json, not a DSP profile",
                                 "put the DSP's profile there, or move that file aside (the import then carries no "
                                 "profile, and intake asks for one), then run the import again")
        renames = rename_profile_fields(profile)
        if renames:
            report["field_renames"] = renames
        try:
            _dsp_profile.validate_profile(profile)
        except ValueError as exc:
            report["warnings"].append(
                f"dsp_profile.json NOT imported — it does not validate: {exc}")
            profile = None
    return profile


def _write_import(proj, new_dir, data, newest, profile, io_):
    """Every write of the import, under the caller's one hold of the new project's writer lock (#141, R14) --
    `project.json` (`data`, merged under that hold), the ledger written here, the profile -- each writer re-entering it.
    A busy lock is met at that hold, before the fresh read and before any write, so its "nothing was written" is true.
    A `project.json` another writer changed since the look, so that the merge leaves `save` refusing it, is refused
    before anything is written too. A version's name taken since the look is refused once `project.json` has landed,
    and says so (`_into_refused`)."""
    proj.save(data)
    written = ["project.json"]
    for preset, (_path, snap) in sorted(newest.items()):
        preset_dir = os.path.join(new_dir, "state", preset)
        os.makedirs(preset_dir, exist_ok=True)
        snap["project_rev"] = proj.load()["project_rev"]
        # Claimed by creating its file, never by writing over one, as a bank claims its number (CONTRACT.md item
        # 8): `project_there` found no ledger, and a name taken since is the same refusal, saying what this run
        # wrote. The text is the one `_write_json` wrote; `HEAD` is replaced whole, as a bank replaces it.
        try:
            io_.create_exclusive(os.path.join(preset_dir, "v_001.json"),
                                 json.dumps(snap, indent=2, sort_keys=True, ensure_ascii=False))
        except FileExistsError:
            landed = (written[0] if len(written) == 1 else ", ".join(written[:-1]) + " and " + written[-1])
            raise _into_refused(new_dir, [f"state/{preset}/v_001.json"],
                                landed=f"{landed} {'is' if len(written) == 1 else 'are'} written") from None
        io_.atomic_write_text(os.path.join(preset_dir, "HEAD"), "v_001\n")
        written += [f"state/{preset}/v_001.json", f"state/{preset}/HEAD"]
    if profile is not None:
        _dsp_profile.save_profile(os.path.join(new_dir, "dsp_profile.json"), profile)


def render_report(report, dry_run=False):
    what = "would import" if dry_run else "imported"
    lines = [f"# 2.x → 3.0 import — {report['project_dir']}", ""]
    if report.get("source"):
        lines.append(f"- from: {report['source']} (untouched — it still opens in 2.x)")
    lines.append(f"- project_rev now: **{report['project_rev']}** (stamped onto every snapshot)")
    lines.append(f"- identity fields moved into project.json: {report['identity_fields']}")
    for rename in report.get("field_renames") or []:
        lines.append(f"  - dsp_profile.json field renamed: {rename}")
    for tier, counts in (report.get("channel_summary") or {}).items():
        lines.append(f"  - {tier}: {counts['total']} ({counts['off']} off)")
    lines.append(f"- snapshots {what}: {len(report['snapshots'])}")
    for rel in report["snapshots"]:
        lines.append(f"  - {rel}")
    lines.append(f"- files {what}: {', '.join(report['files'])}")
    for warning in report["warnings"]:
        lines.append(f"- ⚠️ {warning}")
    lines.append("")
    lines.append("Confirm with: `python3 rew_tool/contract.py check <project>`")
    return "\n".join(lines)


def _main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if not argv or argv[0] == "selftest":
        return _selftest()
    project_dir = argv[0]
    if not os.path.isdir(project_dir):
        print(f"no such project directory: {project_dir}", file=sys.stderr)
        return 2
    dry_run = "--dry-run" in argv
    if "--into" not in argv:
        # In-place migration is deliberately NOT offered. It had to invent provenance (one made-up
        # revision stamped across a history that recorded none), it left the project owing every
        # 3.0 gate a fact 2.x never collected, and it wrote into the only copy of a tune somebody
        # was in the middle of. Importing the current state into a new project costs a review of
        # intake and risks nothing (user, 2026-08-12).
        print(
            "in-place migration is not supported. Import this project's CURRENT state into a new "
            "3.0 project instead — the old one stays untouched and still opens in 2.x:\n\n"
            f"    python3 {os.path.abspath(__file__)} {project_dir} --into <new-project-dir>\n\n"
            "Add --dry-run to see what would move. What moves: channels and their output letters, "
            "crossovers, delays, gains, polarity, EQ, and the DSP profile. What stays behind: the "
            "journal, the process state, and every snapshot but the newest.",
            file=sys.stderr,
        )
        return 2
    at = argv.index("--into")
    if at + 1 >= len(argv):
        print("--into needs a directory for the new project", file=sys.stderr)
        return 2
    new_dir = argv[at + 1]
    if os.path.abspath(new_dir) == os.path.abspath(project_dir):
        print("--into must name a DIFFERENT directory: the point is that the old one is left "
              "alone", file=sys.stderr)
        return 2
    # The new folder is made by the import's first write, once everything it needs is read (#134, batch 4's
    # re-review, Out of Scope 4): made here, a refused import left an empty folder behind.
    try:
        report = import_current_state(project_dir, new_dir, dry_run=dry_run)
    except Exception as exc:  # noqa: BLE001 -- matched below; anything else still raises
        # A refusal of the import -- `--into` over a `project.json` a newer method wrote (`Project.save`'s words), one
        # that cannot be read, a ledger version that cannot be read or does not pass this method's check, an EQ band in
        # one that names no frequency, an old profile that cannot be read or holds a `project.json` -- is said in one
        # line, exit 1 (#134, H 23, T m10; batch 4's re-review M2). It ended in a traceback: nothing here caught it.
        # Those kinds alone (batch 4's re-review N2), and `--into` a folder that holds a project's ledger or profile
        # (`IntoRefused`, the re-review's probe of `--into`): any other `ValueError` -- a `float()` on a malformed
        # field, say -- is a bug, and raises with its traceback, where it was printed `error: could not convert ...`
        # with no file named. Every refusal comes before the first write (Out of Scope 4), so nothing was written --
        # but a version's name taken after the look, which says what this run had written -- and every one the import
        # makes from its reads comes before the new project's lock too (R27), so it makes nothing at all.
        # The new project's writer lock first (#141, R14, `write_lock.py`): another writer held it past the wait -- 75,
        # its one `busy:` line, nothing written (one hold covers every write), safe to retry -- or the wait,
        # AUTOSOUND_LOCK_TIMEOUT_S, is no number of seconds: a usage error, said before anything was taken. A folder
        # the lock cannot be made in (`write_lock.Unwritable`, `is_unreadable`) is one line, exit 1, below.
        if getattr(type(exc), "is_busy", False):
            return _project._write_lock().busy_exit(exc)
        if getattr(type(exc), "exit_code", None) == 2:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        if not (isinstance(exc, _project.ProjectError) or getattr(type(exc), "is_unreadable", False)
                or getattr(type(exc), "is_snapshot_error", False) or getattr(type(exc), "is_into_refused", False)):
            raise
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(render_report(report, dry_run=dry_run))
    return 0


# ── self-test ─────────────────────────────────────────────────────────────────
def _check_import_refuses_newer_project():
    """An import into a folder whose `project.json` a newer method wrote is refused before anything is stamped or
    written, in `Project.save`'s own words (#136, audit T-21): the import stamped v3 onto the loaded facts first, so
    `save` saw v3 and wrote the newer file down. A dry run refuses it too, and the file keeps its bytes -- the folder
    holds that file alone, no lock's `.autosound/` either: the refusal is made before the new project's lock is taken
    (#141, R27)."""
    import shutil
    import tempfile
    old = tempfile.mkdtemp(prefix="autosound_migrate_newer_old_")
    new = tempfile.mkdtemp(prefix="autosound_migrate_newer_new_")
    try:
        os.makedirs(os.path.join(old, "state", "SQ"))
        _write_json(os.path.join(old, "state", "SQ", "v_001.json"), {
            "preset": "SQ", "version": "v_001", "sample_rate": 96000,
            "channels": {"w-L": {"helix_ch": "C", "hp": {"f": 70, "type": "BW", "slope": 12},
                                 "lp": {"f": 270, "type": "BW", "slope": 12}, "gain_db": -7.8, "ta_ms": 5.38,
                                 "polarity": "NORM"}}})
        newer = _project.SCHEMA_VERSION + 1
        path = os.path.join(new, "project.json")
        _write_json(path, {"schema_version": newer, "project_rev": 7, "channels": []})
        with open(path, "rb") as fh:
            raw = fh.read()
        try:
            _project.Project(new).save({"schema_version": newer})
        except _project.ProjectError as exc:
            words = str(exc)
        else:
            raise AssertionError("Project.save wrote down facts a newer method wrote")
        for dry_run in (True, False):
            try:
                import_current_state(old, new, dry_run=dry_run)
            except _project.ProjectError as exc:
                assert str(exc) == words, (dry_run, str(exc), words)
            else:
                raise AssertionError(f"dry_run={dry_run}: the import took a v{newer} project.json")
            with open(path, "rb") as fh:
                assert fh.read() == raw, f"dry_run={dry_run}: project.json changed"
            assert sorted(os.listdir(new)) == ["project.json"], (dry_run, sorted(os.listdir(new)))
        # The command line says it in those words, one line, exit 1 (#134, H 23, T m10): `_main` caught nothing, and
        # the refusal ended in a `ProjectError` traceback.
        import contextlib
        import io
        for extra in ([], ["--dry-run"]):
            out, err = io.StringIO(), io.StringIO()
            try:
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    rc = _main([old, "--into", new] + extra)
            except Exception as exc:  # noqa: BLE001 -- a traceback is the failure under test
                rc = f"raised {type(exc).__name__}: {exc}"
            assert rc == 1 and err.getvalue().strip() == f"error: {words}" and not out.getvalue(), \
                (extra, rc, err.getvalue()[-300:])
            with open(path, "rb") as fh:
                assert fh.read() == raw and sorted(os.listdir(new)) == ["project.json"], (extra, "written")
    finally:
        shutil.rmtree(old, ignore_errors=True)
        shutil.rmtree(new, ignore_errors=True)


def _check_main_refuses_only_refusals():
    """`migrate --into` says the import's refusals in one line -- a `ProjectError`, a version the ledger cannot read
    (`is_snapshot_error`), a file that cannot be read (`is_unreadable`) -- and nothing else (#134, batch 4's re-review
    N2): every `ValueError` was taken for one, so a bug's (a `float()` on a malformed field, say) was printed
    `error: could not convert ...`, exit 1, no traceback and no file named. A 2.x version that does not pass this
    method's check is a refusal of its own, and names its file."""
    import contextlib
    import io
    import shutil
    import tempfile
    global migrate_snapshot
    real = migrate_snapshot
    old = tempfile.mkdtemp(prefix="autosound_migrate_refusals_old_")
    new = tempfile.mkdtemp(prefix="autosound_migrate_refusals_new_")
    try:
        os.makedirs(os.path.join(old, "state", "SQ"))
        version = os.path.join(old, "state", "SQ", "v_001.json")
        row = {"helix_ch": "C", "hp": {"f": 70, "type": "BW", "slope": 12}, "lp": {"f": 270, "type": "BW", "slope": 12},
               "gain_db": -7.8, "ta_ms": 5.38, "polarity": "NORM"}
        failures = []

        def run():
            out, err = io.StringIO(), io.StringIO()
            try:
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    rc = _main([old, "--into", new, "--dry-run"])
            except Exception as exc:  # noqa: BLE001 -- what reaches the command line is what is under test
                rc = f"raised {type(exc).__name__}: {exc}"
            return rc, out.getvalue(), err.getvalue().strip()
        _write_json(version, {"preset": "SQ", "version": "v_001", "sample_rate": 96000,
                              "channels": {"w-L": dict(row, gain_db="loud")}})
        rc, out, err = run()
        if rc != 1 or out or "\n" in err or not err.startswith(f"error: {version}: ") or "gain_db" not in err:
            failures.append(f"a version this method's check refuses: rc {rc!r}, said {err[-300:]!r}")

        def bug(raw):
            raise ValueError("could not convert string to float: 'x'")
        migrate_snapshot = bug
        _write_json(version, {"preset": "SQ", "version": "v_001", "sample_rate": 96000, "channels": {"w-L": row}})
        rc, out, err = run()
        if rc != "raised ValueError: could not convert string to float: 'x'":
            failures.append(f"a bug's ValueError: rc {rc!r}, said {err[-300:]!r}")
        assert not failures, "\n  ".join(["migrate's command line:"] + failures)
    finally:
        migrate_snapshot = real
        shutil.rmtree(old, ignore_errors=True)
        shutil.rmtree(new, ignore_errors=True)


def _check_import_refusals_in_one_line():
    """The import's two other deliberate refusals are one line, exit 1, each naming its file and the way on (#134, batch
    4's re-review M2): an EQ band a 2.x version wrote that names no frequency (`state.eq_band_from_str`'s refusal,
    reached through `migrate_snapshot`), and an old `dsp_profile.json` that holds a `project.json`
    (`rename_profile_fields`' refusal). Once the command line took only the import's own refusals, both were bare
    `ValueError`s, and both ended in a traceback naming no file. A bug's `ValueError` stays one
    (`_check_main_refuses_only_refusals`)."""
    import contextlib
    import io
    import shutil
    import tempfile
    old = tempfile.mkdtemp(prefix="autosound_migrate_m2_old_")
    new = tempfile.mkdtemp(prefix="autosound_migrate_m2_new_")
    try:
        os.makedirs(os.path.join(old, "state", "SQ"))
        version = os.path.join(old, "state", "SQ", "v_001.json")
        row = {"helix_ch": "C", "hp": {"f": 70, "type": "BW", "slope": 12}, "lp": {"f": 270, "type": "BW", "slope": 12},
               "gain_db": -7.8, "ta_ms": 5.38, "polarity": "NORM"}
        profile = os.path.join(old, "dsp_profile.json")
        failures = []
        for label, eq, held, said in (
                ("an EQ band with no frequency", ["PK"], None,
                 f"error: {version}: channels.w-L.eq: could not parse a frequency from EQ band 'PK' -- give the band "
                 f"its frequency in Hz (e.g. `PK 1000 -3 Q2`) or remove it from that version, then run the import "
                 f"again; nothing was imported"),
                ("a dsp_profile.json that holds a project.json", [], {"schema_version": 3, "channels": [], "car": {}},
                 f"error: {profile} holds a project.json, not a DSP profile -- put the DSP's profile there, or move "
                 f"that file aside (the import then carries no profile, and intake asks for one), then run the import "
                 f"again")):
            _write_json(version, {"preset": "SQ", "version": "v_001", "sample_rate": 96000,
                                  "channels": {"w-L": dict(row, eq=eq)}})
            if held is None:
                if os.path.exists(profile):
                    os.remove(profile)
            else:
                _write_json(profile, held)
            for extra in (["--dry-run"], []):
                out, err = io.StringIO(), io.StringIO()
                try:
                    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                        rc = _main([old, "--into", new] + extra)
                except Exception as exc:  # noqa: BLE001 -- a traceback is the failure under test
                    rc = f"raised {type(exc).__name__}: {exc}"
                if (rc, out.getvalue(), err.getvalue()) != (1, "", said + "\n"):
                    failures.append(f"{label} {extra}: rc {rc!r}, said {err.getvalue()[-400:]!r}")
        assert not failures, "\n  ".join(["an import refusal:"] + failures)
    finally:
        shutil.rmtree(old, ignore_errors=True)
        shutil.rmtree(new, ignore_errors=True)


def _check_import_reads_before_it_writes():
    """`migrate --into` writes nothing before everything it needs is read (#134, batch 4's re-review, Out of Scope 4):
    it wrote the new `project.json` and the ledger, and read the old `dsp_profile.json` after them, so a profile it
    refused -- cut off, a newer method's, one that holds a `project.json` -- left a project half made, and the refusal
    did not say what had landed. Now each refuses with the new folder as it was: not even made, when it was not
    there. A profile that reads is carried in, as before. A new folder under a parent this user may not write is
    refused as a lock that cannot be made is (#141): one line, exit 1, nothing made."""
    import contextlib
    import io
    import json
    import shutil
    import tempfile
    old = tempfile.mkdtemp(prefix="autosound_migrate_order_old_")
    top = tempfile.mkdtemp(prefix="autosound_migrate_order_new_")
    try:
        os.makedirs(os.path.join(old, "state", "SQ"))
        _write_json(os.path.join(old, "state", "SQ", "v_001.json"), {
            "preset": "SQ", "version": "v_001", "sample_rate": 96000,
            "channels": {"w-L": {"helix_ch": "C", "hp": {"f": 70, "type": "BW", "slope": 12},
                                 "lp": {"f": 270, "type": "BW", "slope": 12}, "gain_db": -7.8, "ta_ms": 5.38,
                                 "polarity": "NORM"}}})
        profile = os.path.join(old, "dsp_profile.json")
        good = {"dsp_profile": {"name": "Fixture", "vendor": "Fixture", "dsp_processing_rate_hz": 96000,
                                "delay": {"step_ms": 0.01}, "polarity": {"scope": []},
                                "groups": [{"id": "physical_outputs", "label": "Outputs", "max_count": 2,
                                            "fields": ["hp", "lp", "gain_db", "ta_ms", "polarity"],
                                            "crossover_filters": {"types": {"LR": {"orders_db_per_oct": [24]}}}}]}}
        failures = []
        for label, raw in (
                ("cut off", json.dumps(good).encode()[:40]),
                ("a newer method's", json.dumps(dict(good, schema_version=_dsp_profile.SCHEMA_VERSION + 1)).encode()),
                ("a project.json", json.dumps({"schema_version": 3, "channels": [], "car": {}}).encode())):
            with open(profile, "wb") as fh:
                fh.write(raw)
            new = os.path.join(top, label.replace(" ", "-").replace("'", ""))
            out, err = io.StringIO(), io.StringIO()
            try:
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    rc = _main([old, "--into", new])
            except Exception as exc:  # noqa: BLE001 -- a traceback is a failure under test
                rc = f"raised {type(exc).__name__}: {exc}"
            if rc != 1 or not err.getvalue().startswith(f"error: {profile} ") or os.path.exists(new):
                failures.append(f"{label}: rc {rc!r}, said {err.getvalue()[-300:]!r}, new folder "
                                f"{sorted(os.listdir(new)) if os.path.isdir(new) else 'not made'}")
        with open(profile, "w", encoding="utf-8") as fh:
            json.dump(good, fh)
        new = os.path.join(top, "whole")
        with contextlib.redirect_stdout(io.StringIO()):
            rc = _main([old, "--into", new])
        # The writers' lock folder (#141, `.autosound/`, git-ignored) is the writes' own, not something imported.
        made = sorted(n for n in os.listdir(new) if n != ".autosound")
        if rc != 0 or made != ["dsp_profile.json", "project.json", "state"]:
            failures.append(f"a profile that reads: rc {rc!r}, new folder {sorted(os.listdir(new))}")
        # The new folder under a parent this user may not write: refused as the lock refuses (`write_lock.make_folder`),
        # one line, exit 1, nothing made. It was a raw PermissionError's traceback.
        if _project._mode_refuses("--into under a parent this user may not write", "migrate"):
            with _project._under_a_read_only_parent(top) as new:
                out, err = io.StringIO(), io.StringIO()
                try:
                    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                        rc = _main([old, "--into", new])
                except Exception as exc:  # noqa: BLE001 -- a traceback is a failure under test
                    rc = f"raised {type(exc).__name__}: {exc}"
                made = sorted(os.listdir(os.path.dirname(new)))
            if rc != 1 or err.getvalue() != f"error: {_project._cannot_be_made(new)}\n" or out.getvalue() or made:
                failures.append(f"under a parent this user may not write: rc {rc!r}, said {err.getvalue()[-300:]!r}, "
                                f"made {made}")
        assert not failures, "\n  ".join(["an import refused after it wrote:"] + failures)
    finally:
        shutil.rmtree(old, ignore_errors=True)
        shutil.rmtree(top, ignore_errors=True)


def _two_x(old, preset="SQ", gain=-7.8):
    """A 2.x project at `old`: one version of `preset` (EQ as a string, `helix_ch`) and a 2.x profile (`TwoX`, the
    legacy rate key) -- what the re-review's probe of `--into` imports."""
    os.makedirs(os.path.join(old, "state", preset))
    _write_json(os.path.join(old, "state", preset, "v_001.json"), {
        "preset": preset, "version": "v_001", "sample_rate": 96000,
        "channels": {"w-L": {"helix_ch": "C", "hp": {"f": 70, "type": "BW", "slope": 12},
                             "lp": {"f": 270, "type": "BW", "slope": 12}, "gain_db": gain, "ta_ms": 5.38,
                             "polarity": "NORM", "eq": ["PK 1000 -3 Q2"]}}})
    _write_json(os.path.join(old, "dsp_profile.json"), {"dsp_profile": {
        "name": "TwoX", "vendor": "TwoX", "sample_rate_hz": 48000, "delay": {"step_ms": 0.01},
        "polarity": {"scope": []}, "groups": [{"id": "physical_outputs", "label": "Outputs", "max_count": 2,
                                               "fields": ["hp", "lp", "gain_db", "ta_ms", "polarity"],
                                               "crossover_filters": {"types": {"BW": {"orders_db_per_oct": [12]}}}}]}})


def _bytes_under(top):
    """`{relative path: bytes}` of every file under `top` -- nothing written is every byte of it the same. A link is
    its target, `-> <target>`, read without following it: one to nothing has no bytes to read. Not the top
    `.autosound/`: the writer lock's bookkeeping (write_lock.py), not the project's content."""
    out = {}
    for folder, dirs, names in os.walk(top):
        if folder == top and ".autosound" in dirs:
            dirs.remove(".autosound")
        for name in names:
            path = os.path.join(folder, name)
            if os.path.islink(path):
                out[os.path.relpath(path, top).replace(os.sep, "/")] = ("-> " + os.readlink(path)).encode("utf-8")
                continue
            with open(path, "rb") as fh:
                out[os.path.relpath(path, top).replace(os.sep, "/")] = fh.read()
    return out


def _check_bytes_under_leaves_the_lock_out():
    """`.autosound/` at the top is the writer lock's bookkeeping (write_lock.py, #141), made by whichever writer takes
    the lock: `_bytes_under` leaves it out, so taking the lock never reads as a change to the folder. Only the top
    one: a `.autosound/` deeper down is the project's like any other folder."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_migrate_bytes_")
    try:
        for rel in ("project.json", ".autosound/write.lock", ".autosound/.gitignore", "state/.autosound/x"):
            path = os.path.join(top, *rel.split("/"))
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("x")
        got = sorted(_bytes_under(top))
        assert got == ["project.json", "state/.autosound/x"], f"the walk read {got}"
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_into_waits_for_the_lock():
    """`--into` writes the new project -- its `project.json`, its ledger, its profile -- under the new project's writer
    lock, one hold over every write (#141, R14): under another writer's lock it waits AUTOSOUND_LOCK_TIMEOUT_S and exits
    75 with one `busy:` line, no traceback, and nothing written. An AUTOSOUND_LOCK_TIMEOUT_S that is no number of
    seconds is a usage error, exit 2, the new folder not even made. Let go, the import lands -- its profile stamped
    with git asked before the hold."""
    import shutil
    import tempfile
    old = tempfile.mkdtemp(prefix="autosound_migrate_busy_old_")
    top = tempfile.mkdtemp(prefix="autosound_migrate_busy_new_")
    failures = []
    try:
        _two_x(old)
        new = os.path.join(top, "new")
        # The folder first: the lock never makes a project folder (#141, R23), so another process holding a missing one
        # holds its own thread lock alone, and no other process would meet it.
        os.makedirs(new)
        with _project._held_elsewhere(new):
            rc, out, err = _project._run_cli(_main, [old, "--into", new], AUTOSOUND_LOCK_TIMEOUT_S="0.2")
            why = _project._said_busy(rc, err, new)
            if why or len([ln for ln in err.splitlines() if ln.startswith("busy: ")]) != 1:
                failures.append(f"under a held lock: {why or err.strip()[-200:]!r}")
            if _bytes_under(new):
                failures.append(f"written under another writer's lock: {sorted(_bytes_under(new))}")
        fresh = os.path.join(top, "fresh")
        rc, out, err = _project._run_cli(_main, [old, "--into", fresh], AUTOSOUND_LOCK_TIMEOUT_S="soon")
        lines = err.strip().splitlines()
        if rc != 2 or len(lines) != 1 or "AUTOSOUND_LOCK_TIMEOUT_S=soon" not in lines[0] or os.path.exists(fresh):
            failures.append(f"a bad wait: rc {rc}, said {err.strip()[-200:]!r}, made {os.path.exists(fresh)}")
        # Let go, the import lands -- `project.json` and the profile each reached with the lock held already: one hold
        # over every write, the ledger written between them included.
        lock, seen = _project._write_lock(), []
        real_save, real_profile = _project.Project.save, _dsp_profile.save_profile

        def save(self, data):
            seen.append(("project.json", lock.held_here(new)))
            return real_save(self, data)

        def save_profile(path, data):
            seen.append(("dsp_profile.json", lock.held_here(new)))
            return real_profile(path, data)
        _project.Project.save, _dsp_profile.save_profile = save, save_profile
        try:
            rc, out, err = _project._run_cli(_main, [old, "--into", new], AUTOSOUND_LOCK_TIMEOUT_S="0.2")
        finally:
            _project.Project.save, _dsp_profile.save_profile = real_save, real_profile
        if rc != 0 or sorted(_bytes_under(new)) != ["dsp_profile.json", "project.json", "state/SQ/HEAD",
                                                    "state/SQ/v_001.json"]:
            failures.append(f"let go, the import did not land: rc {rc}, wrote {sorted(_bytes_under(new))}, "
                            f"said {err.strip()[-200:]!r}")
        if [name for name, _held in seen] != ["project.json", "dsp_profile.json"] or not all(h for _n, h in seen):
            failures.append(f"written with the lock free: {seen}")
    finally:
        shutil.rmtree(old, ignore_errors=True)
        shutil.rmtree(top, ignore_errors=True)
    assert not failures, "\n  ".join(["--into and the lock:"] + failures)


def _check_into_an_existing_folder_refused_makes_nothing():
    """`--into` a folder that is there, refused, makes nothing there -- not even the lock's `.autosound/` (#141, R27).
    The folder may be no project at all, a mistaken target: the import's refusals are made on reads that hold nothing,
    and the new project's lock is taken only once the import will write. The hold came before the read, and every
    refusal under it left the lock's folder behind. Each refusal of a real import, over an empty folder and over one
    holding a `project.json`: a `project.json` a newer method wrote, a version this method's check refuses, an old
    profile cut off, an old profile that holds a `project.json`."""
    import contextlib
    import io
    import shutil
    import tempfile
    old = tempfile.mkdtemp(prefix="autosound_migrate_existing_old_")
    top = tempfile.mkdtemp(prefix="autosound_migrate_existing_new_")
    failures = []
    try:
        version = os.path.join(old, "state", "SQ", "v_001.json")
        profile = os.path.join(old, "dsp_profile.json")
        os.makedirs(os.path.dirname(version))
        row = {"helix_ch": "C", "hp": {"f": 70, "type": "BW", "slope": 12}, "lp": {"f": 270, "type": "BW", "slope": 12},
               "gain_db": -7.8, "ta_ms": 5.38, "polarity": "NORM"}
        cases = (("a project.json a newer method wrote", {}, None),
                 ("a version this method's check refuses", {"gain_db": "loud"}, None),
                 ("an old profile cut off", {}, b'{"dsp_profile": {"name": "Fixture", "gro'),
                 ("an old profile that holds a project.json", {}, json.dumps(
                     {"schema_version": 3, "channels": [], "car": {}}).encode("utf-8")))
        n = 0
        for label, change, profile_bytes in cases:
            _write_json(version, {"preset": "SQ", "version": "v_001", "sample_rate": 96000,
                                  "channels": {"w-L": dict(row, **change)}})
            if os.path.exists(profile):
                os.remove(profile)
            if profile_bytes is not None:
                with open(profile, "wb") as fh:
                    fh.write(profile_bytes)
            newer = label.startswith("a project.json a newer")
            for holding in ((("project.json",),) if newer else ((), ("project.json",))):
                n += 1
                new = os.path.join(top, f"target-{n}")
                os.makedirs(new)
                if holding:
                    _write_json(os.path.join(new, "project.json"),
                                {"schema_version": _project.SCHEMA_VERSION + (1 if newer else 0), "project_rev": 7,
                                 "channels": []})
                listed, before = sorted(os.listdir(new)), _bytes_under(new)
                out, err = io.StringIO(), io.StringIO()
                try:
                    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                        rc = _main([old, "--into", new])
                except Exception as exc:  # noqa: BLE001 -- a traceback is a failure under test
                    rc = f"raised {type(exc).__name__}: {exc}"
                where = f"{label}, into a folder holding {list(holding) or 'nothing'}"
                if rc != 1 or not err.getvalue().startswith("error: "):
                    failures.append(f"{where}: rc {rc!r}, said {err.getvalue()[-200:]!r}")
                if sorted(os.listdir(new)) != listed or _bytes_under(new) != before:
                    failures.append(f"{where}: the folder holds {sorted(os.listdir(new))}, was {listed}")
        assert not failures, "\n  ".join(["--into a folder that is there, refused:"] + failures)
    finally:
        shutil.rmtree(old, ignore_errors=True)
        shutil.rmtree(top, ignore_errors=True)


def _check_into_refuses_the_merged_facts_first():
    """The facts the import would write -- the new folder's `project.json` with the import merged in -- are checked as
    `Project.save` checks them on the reads that hold nothing too (#141, R27): a `project.json` that holds one channel
    code twice is refused before the new project's lock is taken, so the refusal makes nothing in the folder, not the
    lock's `.autosound/` either, and `--dry-run` says that refusal. `save` decided it under the hold, leaving the lock's
    folder in a folder that may be no project at all, and the dry run said "would import", exit 0."""
    import contextlib
    import io
    import shutil
    import tempfile
    old = tempfile.mkdtemp(prefix="autosound_migrate_merged_old_")
    top = tempfile.mkdtemp(prefix="autosound_migrate_merged_new_")
    failures = []
    try:
        _two_x(old)
        for extra in ([], ["--dry-run"]):
            new = os.path.join(top, "dry" if extra else "real")
            os.makedirs(new)
            _write_json(os.path.join(new, "project.json"), {"schema_version": _project.SCHEMA_VERSION, "project_rev": 4,
                                                            "channels": [{"code": "x"}, {"code": "x"}]})
            listed, before = sorted(os.listdir(new)), _bytes_under(new)
            out, err = io.StringIO(), io.StringIO()
            try:
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    rc = _main([old, "--into", new] + extra)
            except Exception as exc:  # noqa: BLE001 -- a traceback is a failure under test
                rc = f"raised {type(exc).__name__}: {exc}"
            label = " ".join(["--into"] + extra)
            if (rc, out.getvalue(), err.getvalue()) != (1, "", "error: duplicate channel code 'x'\n"):
                failures.append(f"{label}: rc {rc!r}, said {(err.getvalue() or out.getvalue())[-200:]!r}")
            if sorted(os.listdir(new)) != listed or _bytes_under(new) != before:
                failures.append(f"{label}: the folder holds {sorted(os.listdir(new))}, was {listed}")
    finally:
        shutil.rmtree(old, ignore_errors=True)
        shutil.rmtree(top, ignore_errors=True)
    assert not failures, "\n  ".join(["merged facts this method's check refuses:"] + failures)


def _check_into_holds_from_its_read():
    """`--into` a folder holding a `project.json` merges into it as it stands under the new project's lock, and holds the
    lock to its last write (#141, R23, R27): a change another writer made to that `project.json` once the import's
    refusals were read and its merge checked -- before the hold -- stays, and another writer -- a thread, through the
    real lock -- that changes it while the import works under the hold waits until the import has written, and its
    change stays too. The import read the file before its hold, and saved what it had read over the change. Its
    refusals are still read first, holding nothing: a refusal makes nothing
    (`_check_into_an_existing_folder_refused_makes_nothing`, `_check_into_refuses_the_merged_facts_first`). The hooks
    tell the two by the lock: the merge checked before the hold reads `project.json` too, and starts no writer."""
    import shutil
    import tempfile
    import threading
    old = tempfile.mkdtemp(prefix="autosound_migrate_read_old_")
    top = tempfile.mkdtemp(prefix="autosound_migrate_read_new_")
    real_fold, real_ready, got, threads, wrote_before = fold_identity, _dsp_profile._ready_to_hold, [], [], []
    lock = _project._write_lock()

    def before_the_hold():          # the reads are done, the merge checked, git asked next: another writer writes
        if not lock.held_here(new):                     # not `save_profile`'s own ask, under the import's hold
            _project.Project(new).update(lambda d: d.update(before_hold=True))
            wrote_before.append(True)
        return real_ready()

    def meanwhile():
        try:
            _project.Project(new).update(lambda d: d.update(meanwhile=True))
        except Exception as exc:  # noqa: BLE001 -- carried to the check, which names it
            got.append(exc)
        else:
            got.append(None)

    def folding(data, identity):            # the import has read project.json under its hold: another writer writes
        if lock.held_here(new):
            t = threading.Thread(target=meanwhile, daemon=True)
            t.start()
            t.join(0.5)
            threads.append(t)
        return real_fold(data, identity)
    try:
        _two_x(old)
        new = os.path.join(top, "new")
        os.makedirs(new)
        _project.Project(new).save({"schema_version": _project.SCHEMA_VERSION, "channels": []})
        globals().update(fold_identity=folding)
        _dsp_profile._ready_to_hold = before_the_hold
        try:
            # The other writer waits up to 60 s for the import, whatever wait the shell running the check has set (as
            # project.py's two writers do, R25): a short one there made it busy, and the check red for no fault.
            rc, out, err = _project._run_cli(_main, [old, "--into", new], AUTOSOUND_LOCK_TIMEOUT_S="60")
        finally:
            globals().update(fold_identity=real_fold)
            _dsp_profile._ready_to_hold = real_ready
        for t in threads:
            t.join(30)
        data = _project.Project(new).load()
        assert rc == 0, f"the import: rc {rc}, said {err.strip()[-200:]!r}"
        # The writer before the hold runs where the import asks `_ready_to_hold` with the lock free, which it does only
        # for an import that carries a profile (`_two_x`'s does): without it the check below would blame the merge.
        assert wrote_before, "the writer before the hold never ran: the import never asked " \
                             "_dsp_profile._ready_to_hold with its lock free -- it carries no profile, or no longer " \
                             "asks -- so its merge under the hold was not tested"
        assert data.get("before_hold") is True, \
            "the import merged into a read made before its hold, over a change made since"
        assert got == [None], f"the other writer: {got}"
        assert data.get("meanwhile") is True, "the import wrote over another writer's change to project.json"
        assert data.get("imported_from") == os.path.abspath(old), f"the import did not land: {sorted(data)}"
    finally:
        globals().update(fold_identity=real_fold)
        _dsp_profile._ready_to_hold = real_ready
        shutil.rmtree(old, ignore_errors=True)
        shutil.rmtree(top, ignore_errors=True)


def _check_into_a_project_refused():
    """`migrate --into` a folder that holds a project's ledger or DSP profile is refused before anything is written,
    in one line naming each and the way on, exit 1, with `--dry-run` too; every byte of the folder stays as it was
    (#134, batch 4's re-review, the probe of `--into`, cases A-D). It wrote its `state/<preset>/v_001.json` and `HEAD`
    there -- over the version an earlier import banked (sealed or not), with the slot moved off the version banked
    after it -- and the 2.x profile over the project's, beside a per-project line nothing can read with them, and said
    "imported", exit 0. A folder with a `project.json` alone, or empty, still imports, as before. So do the look's three
    edges (batch 4's N4-M4): an empty `state/versions/` and a `dsp_profile.json` link to nothing are refused -- each
    went untested, and read as nothing an import would have gone in beside a half-moved line, or replaced the link --
    and a front end's `state/.tcc/` imports, left as it was."""
    import contextlib
    import io
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="autosound_migrate_into_")

    def three(gain):
        return {"preset": "SQ", "sample_rate": 96000, "channels": {"w-L": {
            "hp": {"f": 80, "type": "LR", "slope": 24}, "lp": {"f": 300, "type": "LR", "slope": 24}, "gain_db": gain,
            "ta_ms": 1.25, "polarity": "NORM", "eq": []}}}

    def run(old, new, extra=()):
        out, err = io.StringIO(), io.StringIO()
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = _main([old, "--into", new] + list(extra))
        except Exception as exc:  # noqa: BLE001 -- a traceback is a failure under test
            rc = f"raised {type(exc).__name__}: {exc}"
        return rc, out.getvalue(), err.getvalue()

    def native(tgt, banks, profile):
        pj = _project.Project(tgt)
        pj.save(pj.load())
        h = _state.PresetHistory(os.path.join(tgt, "state"), "SQ", project_dir=tgt)
        for gain in banks:
            h.snapshot(three(gain), note="a 3.0 bank")
        if profile:
            _dsp_profile.save_profile(os.path.join(tgt, "dsp_profile.json"), {"dsp_profile": {
                "name": "Target3", "vendor": "Target3", "dsp_processing_rate_hz": 96000, "groups": [
                    {"id": "physical_outputs", "label": "Outputs", "fields": ["hp", "lp", "gain_db"]}]}})

    def imported(tgt, old, seal=False):
        assert run(old, tgt)[0] == 0, "the first import into a new folder"
        if seal:
            _state.seal_all(os.path.join(tgt, "state"))
        else:
            _state.PresetHistory(os.path.join(tgt, "state"), "SQ", project_dir=tgt).snapshot(three(-4.5), note="3.0")

    def other_case(tgt):
        pj = _project.Project(tgt)
        pj.save(pj.load())
        os.makedirs(os.path.join(tgt, "state", "SQ"))
        with open(os.path.join(tgt, "state", "SQ", "V_001.JSON"), "w", encoding="utf-8") as fh:
            json.dump(three(-2.0), fh)

    def profile_link_to_nothing(tgt):          # a link where the profile belongs, its target gone (batch 4's N4-M4)
        os.makedirs(tgt)
        os.symlink(os.path.join(tgt, "shared", "dsp_profile.json"), os.path.join(tgt, "dsp_profile.json"))

    probe = os.path.join(top, "can-link")
    try:
        os.symlink(probe + "-target", probe)
        links = True
    except (OSError, NotImplementedError):
        links = False
        print("  (no symbolic links on this system: a dsp_profile.json link to nothing was not made)")
    try:
        failures = []
        old = os.path.join(top, "old")
        _two_x(old)
        old_versions = os.path.join(top, "old-versions")
        _two_x(old_versions, preset="versions")
        # Three of the look's branches no case held (batch 4's N4-M4): an empty `state/versions/` -- the half-moved line
        # `state.py` refuses -- and a profile that is a link to nothing are refused; a front end's dot-folder imports.
        more = [("an empty state/versions/", old, lambda t: os.makedirs(os.path.join(t, "state", "versions")),
                 ["state/versions/ (0 versions)"])]
        if links:
            more.append(("a dsp_profile.json link to nothing", old, profile_link_to_nothing, ["dsp_profile.json"]))
        for label, source, make, named in [
                ("A: a per-project line and a profile", old, lambda t: native(t, (-3.0, -4.5), True),
                 ["state/slots.json", "state/versions/ (2 versions)", "dsp_profile.json"]),
                ("B: the line an import made, a version banked on it", old, lambda t: imported(t, old),
                 ["state/SQ/ (2 versions)", "dsp_profile.json"]),
                ("C: the line an import made, sealed", old, lambda t: imported(t, old, seal=True),
                 ["state/SQ/ (1 version)", "dsp_profile.json"]),
                ("D: a per-project line, the 2.x preset named versions", old_versions,
                 lambda t: native(t, (-3.0,), False), ["state/slots.json", "state/versions/ (1 version)"]),
                ("a profile alone", old, lambda t: native(t, (), True), ["dsp_profile.json"]),
                ("a version named in another letter case", old, other_case, ["state/SQ/ (1 version)"])] + more:
            tgt = os.path.join(top, label.split(":")[0].replace(" ", "-"))
            make(tgt)
            before = _bytes_under(tgt)
            for extra in (["--dry-run"], []):
                rc, out, err = run(source, tgt, extra)
                line = err.strip()
                want = f"error: --into {tgt} holds a project already: {', '.join(named)} -- "
                if (rc, out) != (1, "") or "\n" in line or not line.startswith(want) \
                        or "nothing was written" not in line or "new, empty folder" not in line \
                        or f"{os.path.join(_HERE, 'apply.py')} {tgt} propose" not in line:
                    failures.append(f"{label} {extra}: rc {rc!r}, stdout {len(out)} chars, said {line[-500:]!r}")
                after = _bytes_under(tgt)
                if after != before:
                    failures.append(f"{label} {extra}: changed "
                                    f"{sorted(k for k in set(after) | set(before) if after.get(k) != before.get(k))}")
        for label, make in (("a project.json alone", lambda t: _project.Project(t).save(_project.Project(t).load())),
                            ("an empty folder", os.makedirs)):
            tgt = os.path.join(top, label.replace(" ", "-").replace(".", "-"))
            make(tgt)
            rc, out, err = run(old, tgt)
            head = os.path.join(tgt, "state", "SQ", "HEAD")
            if rc != 0 or "imported: 1" not in out or sorted(_bytes_under(tgt)) != [
                    "dsp_profile.json", "project.json", "state/SQ/HEAD", "state/SQ/v_001.json"] \
                    or open(head, encoding="utf-8").read() != "v_001\n":
                failures.append(f"{label}: rc {rc!r}, said {(out + err)[-300:]!r}, files {sorted(_bytes_under(tgt))}")
        # A front end's own folder under state/ -- TCC's `.tcc/`, holding what reads like a version -- is no ledger
        # line: the import goes in beside it, and leaves it byte for byte.
        tgt = os.path.join(top, "a-front-end-s-dot-folder")
        os.makedirs(os.path.join(tgt, "state", ".tcc"))
        with open(os.path.join(tgt, "state", ".tcc", "v_001.json"), "w", encoding="utf-8") as fh:
            json.dump({"tcc": "a front end's scratch"}, fh)
        kept = _bytes_under(tgt)
        rc, out, err = run(old, tgt)
        after = _bytes_under(tgt)
        if rc != 0 or "imported: 1" not in out or sorted(after) != [
                "dsp_profile.json", "project.json", "state/.tcc/v_001.json", "state/SQ/HEAD", "state/SQ/v_001.json"] \
                or after["state/.tcc/v_001.json"] != kept["state/.tcc/v_001.json"]:
            failures.append(f"a front end's state/.tcc/: rc {rc!r}, said {(out + err)[-300:]!r}, files {sorted(after)}")
        assert not failures, "\n  ".join(["--into a folder that holds a project:"] + failures)
    finally:
        shutil.rmtree(top, ignore_errors=True)


def _check_version_claimed_exclusively():
    """The import claims each `v_001.json` by creating it (`project_io.create_exclusive`), as a bank claims its number,
    and replaces `HEAD` whole (#134, batch 4's re-review, the probe of `--into`): both were written over whatever stood
    at that name, the version through an atomic replace that never asked, `HEAD` in place. A name taken after
    `project_there` looked -- a writer in between -- is the same refusal, one line, exit 1, naming the file and what
    this run had written; the version there keeps every byte, and nothing after it is written. A `HEAD` whose write
    fails leaves no `HEAD` and no temp beside it. The version's bytes are the ones `_write_json` wrote."""
    import contextlib
    import io
    import shutil
    import tempfile
    global project_there
    real_look, io_ = project_there, _project_io()
    real_replace = io_._replace
    top = tempfile.mkdtemp(prefix="autosound_migrate_claim_")
    try:
        old = os.path.join(top, "old")
        _two_x(old)
        failures = []
        # A writer between the look and the claim: the look is made to see nothing, and the name is taken.
        tgt = os.path.join(top, "raced")
        os.makedirs(os.path.join(tgt, "state", "SQ"))
        version = os.path.join(tgt, "state", "SQ", "v_001.json")
        with open(version, "wb") as fh:
            fh.write(b'{"banked": "by another writer"}')
        project_there = lambda new_dir: []  # noqa: E731 -- the look that missed it
        out, err = io.StringIO(), io.StringIO()
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = _main([old, "--into", tgt])
        except Exception as exc:  # noqa: BLE001 -- a traceback is a failure under test
            rc = f"raised {type(exc).__name__}: {exc}"
        finally:
            project_there = real_look
        line = err.getvalue().strip()
        want = (f"error: --into {tgt} holds a project already: state/SQ/v_001.json -- the import makes a NEW project, "
                f"and a ledger version or a profile once written is never written over; project.json is written, and "
                f"no ledger version or profile was written over. Import into a new, empty folder")
        if rc != 1 or out.getvalue() or "\n" in line or not line.startswith(want):
            failures.append(f"a name taken after the look: rc {rc!r}, said {line[-400:]!r}")
        if sorted(_bytes_under(tgt)) != ["project.json", "state/SQ/v_001.json"] \
                or _bytes_under(tgt)["state/SQ/v_001.json"] != b'{"banked": "by another writer"}':
            failures.append(f"a name taken after the look: the folder holds {sorted(_bytes_under(tgt))}")
        # A HEAD whose replace fails: none is left, and no temp beside the version.
        tgt = os.path.join(top, "head-refused")

        def replace(src, dst):
            if os.path.basename(dst) == "HEAD":
                raise OSError(5, "Input/output error (made to fail)")
            return real_replace(src, dst)
        io_._replace = replace
        try:
            import_current_state(old, tgt)
        except OSError:
            pass
        else:
            failures.append("a HEAD whose replace fails: the import went on")
        finally:
            io_._replace = real_replace
        if sorted(os.listdir(os.path.join(tgt, "state", "SQ"))) != ["v_001.json"]:
            failures.append(f"a HEAD whose replace fails: state/SQ/ holds {sorted(os.listdir(os.path.join(tgt, 'state', 'SQ')))}")
        # The version's bytes are `_write_json`'s.
        tgt = os.path.join(top, "fresh")
        with contextlib.redirect_stdout(io.StringIO()):
            assert _main([old, "--into", tgt]) == 0, "a fresh import"
        version = os.path.join(tgt, "state", "SQ", "v_001.json")
        with open(version, "rb") as fh:
            claimed = fh.read()
        again = os.path.join(top, "again.json")
        _write_json(again, json.loads(claimed.decode("utf-8")))
        with open(again, "rb") as fh:
            if fh.read() != claimed:
                failures.append("the claimed version's bytes are not the ones _write_json writes")
        assert not failures, "\n  ".join(["the import's claim of a version:"] + failures)
    finally:
        project_there = real_look
        io_._replace = real_replace
        shutil.rmtree(top, ignore_errors=True)


def _selftest():
    import tempfile

    failures = []
    for check in (_check_import_refuses_newer_project, _check_main_refuses_only_refusals,
                  _check_import_refusals_in_one_line, _check_import_reads_before_it_writes,
                  _check_into_a_project_refused, _check_version_claimed_exclusively,
                  _check_bytes_under_leaves_the_lock_out, _check_into_waits_for_the_lock,
                  _check_into_holds_from_its_read, _check_into_an_existing_folder_refused_makes_nothing,
                  _check_into_refuses_the_merged_facts_first):
        try:
            check()
        except AssertionError as exc:
            failures.append(f"{check.__name__}: {exc}")
    assert not failures, "\n".join(failures)

    root = tempfile.mkdtemp(prefix="autosound_migrate_")
    preset_dir = os.path.join(root, "state", "SQ_Jazzi")
    os.makedirs(preset_dir)

    # A 2.x project as it actually looks in the wild. Two shapes on purpose, because two exist:
    #
    #   `w-L` and `sub` carry `helix_ch` — the ONLY identity field the RELEASED 2.x line ever
    #   wrote (`CHANNEL_FIELDS` at v2.8.1). This fixture used to use `slot` throughout, which no
    #   released version produced: the migration was being tested against a development state and
    #   passed while a real v2.8.1 project migrated to an empty Slot column (2026-08-12).
    #
    #   `VFL` carries `slot`/`descr`/`hidden`, the shape the development states between releases
    #   wrote. Some projects are in it, so it stays covered.
    #
    # Also 2.x-authentic: no schema_version, EQ as strings (incl. the LS shorthand), `tag_value`
    # beside its `tag`.
    v1 = {
        "preset": "SQ_Jazzi", "version": "v_001", "sample_rate": 96000,
        "channels": {
            "w-L": {"helix_ch": "C", "descr": "Front L Woofer", "role": "woofer", "order": 1,
                    "hp": {"f": 70, "type": "BW", "slope": 12},
                    "lp": {"f": 270, "type": "BW", "slope": 12},
                    "gain_db": -7.8, "ta_ms": 5.38, "polarity": "NORM",
                    "eq": ["PK 1000 -9 Q2", "LS 150 +2.5 Q0.71"]},
            "sub": {"helix_ch": "K", "tag": "SubRC", "tag_value": "-4dB",
                    "hp": {"f": 20, "type": "BE", "slope": 12},
                    "lp": {"f": 45, "type": "BW", "slope": 12},
                    "gain_db": -6.0, "ta_ms": 5.0, "polarity": "NORM"},
            # Both names at once — a project half-touched by a development build. The newer name
            # wins; the leftover must not overwrite it.
            "w-R": {"helix_ch": "OLD", "slot": "D",
                    "hp": {"f": 70, "type": "BW", "slope": 12},
                    "lp": {"f": 270, "type": "BW", "slope": 12},
                    "gain_db": -7.8, "ta_ms": 5.30, "polarity": "NORM"},
        },
        "virtual_channels": {
            "VFL": {"slot": "A", "descr": "Front L Full", "hidden": False,
                    "gain_db": 0.0, "ta_ms": 0.0, "polarity": "NORM",
                    "eq": ["APF2 2177 Q1.5"]},
        },
    }
    _write_json(os.path.join(preset_dir, "v_001.json"), v1)
    # a NEWER snapshot with a corrected description -- the newest value must win.
    v2 = copy.deepcopy(v1)
    v2["version"] = "v_002"
    v2["channels"]["w-L"]["descr"] = "Front L Woofer (corrected)"
    _write_json(os.path.join(preset_dir, "v_002.json"), v2)
    with open(os.path.join(preset_dir, "HEAD"), "w", encoding="utf-8") as f:
        f.write("v_002\n")

    # A DSP profile written exactly as the RELEASED 2.x skill demonstrated it — its own MUSWAY
    # stub used `delay_ms`, which 3.0's closed vocabulary refuses. Migration must fix the token,
    # not warn about it and move on.
    _write_json(os.path.join(root, "dsp_profile.json"), {
        "dsp_profile": {
            "name": "M6V4", "vendor": "Musway", "sample_rate_hz": 96000,  # legacy on purpose: rename_profile_fields must move it
            "groups": [
                {"id": "physical_outputs", "label": "Output channels",
                 "fields": ["hp", "lp", "gain_db", "delay_ms", "polarity"]},
                {"id": "inputs", "label": "Inputs", "no_crossover": True,
                 "fields": ["gain_db", "eq", "delay_ms"]},
            ],
        }
    })

    # The NEW project, where the car lands. A fact somebody already answered there must not be
    # clobbered by an old snapshot.
    new_root = tempfile.mkdtemp(prefix="autosound_import_new_")
    proj = _project.Project(new_root)
    seeded = proj.load()
    seeded["channels"] = [{"code": "sub", "descr": "Subwoofer (from intake)"}]
    proj.save(seeded)
    rev_before = proj.load()["project_rev"]

    # --dry-run writes nothing, into either project.
    before = _read_json(os.path.join(preset_dir, "v_001.json"))
    import_current_state(root, new_root, dry_run=True)
    assert _read_json(os.path.join(preset_dir, "v_001.json")) == before, "dry run wrote something"
    assert not os.path.exists(os.path.join(new_root, "state")), "dry run created a ledger"

    report = import_current_state(root, new_root)

    # The OLD project is untouched — that is the whole reason this is an import and not an
    # in-place migration: it cannot lose a tune somebody is in the middle of.
    assert _read_json(os.path.join(preset_dir, "v_001.json")) == before, "the source was modified"
    assert "helix_ch" in before["channels"]["w-L"], before["channels"]["w-L"]

    # identity landed in the new project.json, newest snapshot winning, intake's answer untouched.
    data = _project.Project(new_root).load()
    by_code = {r["code"]: r for r in data["channels"]}
    assert by_code["w-L"]["descr"] == "Front L Woofer (corrected)", by_code["w-L"]
    # `helix_ch` -> `slot`: the DSP output letter, the one thing on a 2.x row the Arbiter types
    # into the processor. It used to be carried nowhere at all — the migration reported success
    # and left the Slot column empty (2026-08-12).
    assert by_code["w-L"]["slot"] == "C" and by_code["w-L"]["order"] == 1, by_code["w-L"]
    assert by_code["sub"]["slot"] == "K", by_code["sub"]
    assert by_code["sub"]["descr"] == "Subwoofer (from intake)", by_code["sub"]
    # both names on one row: the newer one wins, the leftover does not overwrite it.
    assert by_code["w-R"]["slot"] == "D", by_code["w-R"]
    assert by_code["VFL"]["slot"] == "A", by_code  # a virtual row's identity moves too
    assert _project.fact_value(data["hardware"]["controls"]["SubRC"]) == "-4dB", data["hardware"]
    # SCR-016: the tier counts a consumer's Project-params panel renders, derived from the very
    # snapshots being migrated rather than left for a human to re-enter.
    assert data["channel_summary"] == {"channels": {"total": 3, "off": 0},
                                        "virtual_channels": {"total": 1, "off": 0}}, data
    assert data["project_rev"] > rev_before, data["project_rev"]

    # the profile's 2.x token was renamed, the file now validates, and the run said so.
    assert report.get("field_renames"), report
    profile = _read_json(os.path.join(new_root, "dsp_profile.json"))
    fields = [f for g in profile["dsp_profile"]["groups"] for f in g["fields"]]
    assert "delay_ms" not in fields and fields.count("ta_ms") == 2, fields
    # ...and the SOURCE profile still says what it always said.
    old_fields = [f for g in _read_json(os.path.join(root, "dsp_profile.json"))["dsp_profile"]
                  ["groups"] for f in g["fields"]]
    assert old_fields.count("delay_ms") == 2, old_fields
    _dsp_profile.validate_profile(profile)  # raises if the migration left it broken
    assert "dsp_profile.json" in report["files"], report

    # the imported ledger is 3.0: no identity, structured EQ, one snapshot — the newest.
    hist = _state.PresetHistory(os.path.join(new_root, "state"), "SQ_Jazzi", project_dir=new_root)
    assert hist.load("v_001")["note"].startswith("imported from"), hist.load("v_001")["note"]
    assert not os.path.exists(os.path.join(new_root, "state", "SQ_Jazzi", "v_002.json")), \
        "history must stay behind: only the current state is imported"
    for version in ("v_001",):
        snap = hist.load(version)
        _state.validate(snap)
        assert snap["schema_version"] == _state.SCHEMA_VERSION, snap
        assert snap["project_rev"] == report["project_rev"], snap
        for tier in _state.tier_names(snap):
            for row in (snap.get(tier) or {}).values():
                assert not any(f in row for f in _state.MOVED_TO_PROJECT_JSON), row
        assert snap["channels"]["w-L"]["eq"][0] == {
            "type": "PK", "f": 1000.0, "gain_db": -9.0, "q": 2.0}, snap
        assert snap["channels"]["w-L"]["eq"][1]["type"] == "LSH", snap  # LS shorthand normalized
        assert snap["virtual_channels"]["VFL"]["eq"][0]["type"] == "APF2", snap
        assert snap["channels"]["sub"]["tag"] == "SubRC", snap  # `tag` is structural, it stays

    # the settings sheet still prints slots -- they now come from project.json.
    sheet = hist.render("v_001")
    assert "| w-L | C |" in sheet, sheet

    # Re-running into the SAME new project is refused before anything is written (#134, batch 4's
    # re-review): it wrote the import's v_001.json and HEAD over the line again -- a version
    # banked on it since went out of the slot -- and the old profile over the project's, and said
    # "imported". Every byte of the project stays as it was.
    kept = _bytes_under(new_root)
    try:
        import_current_state(root, new_root)
    except Exception as exc:  # noqa: BLE001 -- the kind is what is under test
        assert getattr(type(exc), "is_into_refused", False), repr(exc)
        assert "state/SQ_Jazzi/ (1 version), dsp_profile.json -- " in str(exc), str(exc)
    else:
        raise AssertionError("a re-run into the project an import made was not refused")
    assert _bytes_under(new_root) == kept, "the refused re-run wrote something"

    # ...and importing into the source itself is refused: the point is that the old one is left
    # alone, and a caller who conflates them has misunderstood the whole shape.
    assert _main([root]) == 2, "in-place must not be silently accepted"

    # Handed a project.json, the renamer must REFUSE, not return [] (a live project's copy showed
    # the silent no-op, 2026-08-26) -- and must leave the dict exactly as it found it.
    project_like = {"schema_version": 3, "car": {"make": "X"}, "channels": [],
                    "dsp": {"vendor": "V", "sample_rate_hz": 96000},
                    "measurement": {"sample_rate_hz": 48000}}
    before = copy.deepcopy(project_like)
    try:
        rename_profile_fields(project_like)
        raise AssertionError("rename_profile_fields accepted a project.json and returned")
    except ValueError as exc:
        assert "migrate-fields" in str(exc), exc
    assert project_like == before, project_like

    print(f"selftest OK — a 2.x project (string EQ incl. LS shorthand, `helix_ch` as the released "
          f"2.x line wrote it, identity on ledger rows, "
          f"tag_value beside its tag) IMPORTED into a new 3.0 project, source untouched: identity "
          f"moved into project.json with the "
          f"newest snapshot winning and intake's own answer left intact, tag_value became a "
          f"hardware control, the current state landed as v_001 at project_rev={report['project_rev']} and "
          f"validated, the settings sheet kept its Slot column, --dry-run wrote nothing, a re-run "
          f"into the project it made was refused with every byte kept; --into under another writer's lock "
          f"exits 75 with one busy line and nothing written, a bad AUTOSOUND_LOCK_TIMEOUT_S is exit 2 with the "
          f"folder not made; its refusals are read holding nothing -- the merged facts checked as save checks them "
          f"among them, a dry run saying the same -- and make nothing in a folder that is there, not the lock's "
          f".autosound/ either, nor under a parent this user may not write; then one hold covers a fresh read of the "
          f"new project.json and every write, another writer's change to it kept (#141, R14, R23, R27). root={root}")
    return 0


if __name__ == "__main__":
    # issue #21: a code page must not destroy a result. Run from a subdirectory, so the sibling
    # modules' own directory has to go on the path before `console` can be found at all.
    import os as _os, sys as _sys
    _sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
    import console
    console.install()
    raise SystemExit(_main())
