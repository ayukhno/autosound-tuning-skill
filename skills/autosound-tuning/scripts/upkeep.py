#!/usr/bin/env python3
"""One path to keep what the skill runs on up to date -- the clone, its tools, its libraries.

Four W-4 tasks asked for the same thing from different sides (skill #91 #92 #97 #98, and the clone half of
#99): a machine that updates the skill should end up with the skill, its tools and its libraries at what was
released and tested, with nothing lost on the way. Three doors each did a part of it -- `install.sh`,
`install.ps1`, and TCC's updater running git itself -- so the part that is the same everywhere lives here,
once, and every door calls it:

    status [--json]              the clone, each tool (installed and available version, how it was installed),
                                 the libraries -- what TCC's update panel shows
    keep-local [--send]          the clone's local changes as one patch file, sent to the skill as an issue only
                                 with --send (the caller asked the person first), then the clone reset (#91)
    clone [--tag vX.Y.Z]         the tag fetched into refs/tags, its signature verified, checked out (#92, #99)
    tools [--only NAME]          every tool that is present, updated the way it was installed; old -> new (#97)
    libs                         numpy, scipy, matplotlib upgraded in the Python the method's tools run on (#98)
    verify-copy --root DIR       a copy with no .git (a plugin install) checked against its signed release tag,
                                 file by file (W-6 #121)
    plugin-ready --root DIR      record that this plugin version is verified and set up on the machine (#120)

TCC runs this from its vendored skill (as new as TCC). The installers run the copy inside the tag they are about
to check out (`git show FETCH_HEAD:<this file>`), so a clone that predates this script is not in the way.

stdlib only, py3.9+. Exit codes: 0 done · 2 usage · 3 refused (a dirty clone, a signature, a failed step; for
verify-copy, a copy that is not as its author signed it) · 4 verify-copy only: the copy could not be checked here (no
network, git failed) -- nothing was judged (#142).
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(HERE)
SKILL_REPO = "https://github.com/ayukhno/autosound-tuning-skill"
SKILL_TAG_GLOB = "v3.*"
CLONE = os.path.join(os.path.expanduser("~"), ".claude", "skills", ".autosound-tuning-src")
LOCAL_CHANGES = os.path.join(os.path.expanduser("~"), ".claude", "skills", "autosound-local-changes")
LOCAL_BIN = os.path.join(os.path.expanduser("~"), ".local", "bin")
REQUIREMENTS = os.path.join(SKILL_DIR, "requirements.txt")

# ── signed tags (#99, hub #82 HUB-031) ───────────────────────────────────────────────────────────
# The trust anchor is a CONSTANT here and in both installers (installer-consistency.py compares them), never a
# file read from the tag being verified: a tag's own `allowed_signers` would vouch for itself. Tags before the
# first signed one stay installable -- they are named as predating the signature, not refused.
SIGNING_PRINCIPAL = "ayukhno"
SIGNING_KEY = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHLm4x1yz9JbFfBlxdQA8vR8yYMupVktswes3CL7QE1y"
SIGNED_FROM = "v3.0.64"
SKIP_VERIFY_VAR = "AUTOSOUND_SKIP_TAG_VERIFY"

# A release tag's two shapes (T-45, #142), always matched whole (`fullmatch`): ASCII digits -- `\d` takes any script's
# -- and no trailing newline, which `$` lets through. `is_release_tag` below is the rule.
_TAG_RE = re.compile(r"v([0-9]+)\.([0-9]+)\.([0-9]+)")


class Refused(Exception):
    """A step that must not go ahead, with the sentence that says why and what to do. `exit_code` is the command line's
    answer -- read as an attribute, never matched by class (a caller may hold another copy of this module)."""
    exit_code = 3


class CannotCheck(Refused):
    """verify-copy could not check the copy at all -- no network, git failed -- so nothing was judged: exit 4, apart
    from 3, a copy that is not as its author signed it (#142). The two shared 3 and one sentence, and the installers
    sent a person who was offline to reinstall a good plugin."""
    exit_code = 4


def run(cmd, cwd=None, env=None, timeout=120, stdin=subprocess.DEVNULL):
    """`(returncode, stdout, stderr)`; a missing program or a timeout is a returncode, never an exception."""
    try:
        p = subprocess.run(cmd, cwd=cwd, env=env, timeout=timeout, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", stdin=stdin)
        return p.returncode, p.stdout, p.stderr
    except FileNotFoundError as exc:
        return 127, "", str(exc)
    except subprocess.TimeoutExpired:
        return 124, "", f"no answer in {timeout} s"


def git(clone, *args, env=None, timeout=120):
    return run(["git", "-C", clone, *args], env=env, timeout=timeout)


_CANDIDATE_RE = re.compile(r"beta-v([0-9]+)\.([0-9]+)\.([0-9]+)-rc([0-9]+)")


def is_release_tag(name):
    """True for a release tag -- `vX.Y.Z`, or a candidate's `beta-vX.Y.Z-rcN` -- and for nothing else. The one rule
    (T-45, #142), here as in install.sh's `is_release_tag` and install.ps1's `Test-ReleaseTag`;
    `installer-consistency.py` holds the three to one table of names."""
    return isinstance(name, str) and bool(_TAG_RE.fullmatch(name) or _CANDIDATE_RE.fullmatch(name))


def release_key(tag):
    """The release a tag names: `v3.1.0` and `beta-v3.1.0-rc2` both name (3, 1, 0); None for anything else. A
    candidate is signed like a release (the installers verify both), so the signature rules read this, not the name."""
    m = _TAG_RE.fullmatch(tag or "") or _CANDIDATE_RE.fullmatch(tag or "")
    return tuple(int(x) for x in m.groups()[:3]) if m else None


def tag_key(tag):
    m = _TAG_RE.fullmatch(tag or "")
    return tuple(int(x) for x in m.groups()) if m else None


def newest_tag(repo=SKILL_REPO, glob=SKILL_TAG_GLOB):
    """The newest `v3.x.y` on the remote, or "" when it cannot be asked (the installers' ls-remote)."""
    rc, out, _ = run(["git", "ls-remote", "--tags", "--refs", repo, glob], timeout=60)
    tags = [line.rsplit("/", 1)[-1] for line in out.splitlines() if rc == 0 and "refs/tags/" in line]
    tags = [t for t in tags if tag_key(t)]
    return max(tags, key=tag_key) if tags else ""


def verify_tag(clone, tag, principal=None, key=None, signed_from=None, env=None):
    """`(ok, sentence)`. ok is True for a good signature, and for a tag that predates signing (the sentence says
    which); False for anything else at or after `signed_from`. The switch skips it, visibly.

    A good signature is one answer only (T-35, #142): git's exit 0 and ssh-keygen's line `Good "git" signature for
    <principal> with ...`, whatever the person's git or GPG configuration says. ssh-keygen is named for the check, so
    a sign-only helper set as `gpg.ssh.program` (1Password's, for one) is not asked to verify; and git picks the
    verifier from the signature, not from `gpg.format`, so an OpenPGP tag that the person's own gpg calls good exits
    0 with "Good" too -- and is not the author's. `gpg.minTrustLevel` is held at `fully`, git's rating of a key in
    allowed_signers: a person's `ultimate` refused every good release. `env` is what git runs in."""
    env = os.environ if env is None else env
    principal, key = principal or SIGNING_PRINCIPAL, key or SIGNING_KEY
    signed_from = signed_from or SIGNED_FROM
    if env.get(SKIP_VERIFY_VAR) == "1":
        return True, f"signature NOT checked: {SKIP_VERIFY_VAR}=1 is set (a developer's switch)"
    if not is_release_tag(tag):
        return False, f"{tag!r} is not a release tag (vX.Y.Z or beta-vX.Y.Z-rcN), so there is no signature to check"
    if release_key(tag) < tag_key(signed_from):
        return True, f"{tag} predates signed tags (they start at {signed_from}): installed without a signature check"
    with tempfile.TemporaryDirectory(prefix="autosound_signers_") as tmp:
        signers = os.path.join(tmp, "allowed_signers")
        with open(signers, "w", encoding="utf-8") as fh:
            fh.write(f'{principal} namespaces="git" {key}\n')
        rc, out, err = git(clone, "-c", "gpg.format=ssh", "-c", "gpg.ssh.program=ssh-keygen", "-c",
                           "gpg.minTrustLevel=fully", "-c", f"gpg.ssh.allowedSignersFile={signers}", "verify-tag", tag,
                           env=env)
    said = (err or out).strip()
    if rc == 0 and re.search(rf'(?m)^Good "git" signature for {re.escape(principal)} with ', said):
        return True, f"{tag}: signature good ({principal})"
    reason = said.splitlines()[-1].rstrip(".") if said else f"git verify-tag exit {rc}"
    return False, (f"{tag}: the signature does not check out -- {reason}. Not installed: a release tag of this "
                   f"skill is signed by its author, and this one is not, or not by that key")


# ── a copy with no .git: the plugin install (W-6 #120, #121) ─────────────────────────────────────
def ready_file(env=None, nt=None):
    """Where a plugin version, once verified and set up, is written down -- one `vX.Y.Z` per line. The plugin's
    SessionStart hook (`hooks/session-start.sh`) reads `$HOME/.config/autosound/plugin-ready`, so this is the same
    file: on Windows the hook runs in Git Bash, whose $HOME is %HOME% when that is set and %USERPROFILE% otherwise,
    while Python's `~` there is %USERPROFILE% alone -- with a %HOME% of its own, the two named two files and the set-up
    note never went away (#142)."""
    env = os.environ if env is None else env
    nt = (os.name == "nt") if nt is None else nt
    home = (env.get("HOME") or env.get("USERPROFILE")) if nt else env.get("HOME")
    return os.path.join(home or os.path.expanduser("~"), ".config", "autosound", "plugin-ready")


#: The ready file for this process's environment, as it stood at import; `plugin_ready` asks `ready_file()` each call.
PLUGIN_READY = ready_file()
#: What is in a plugin copy that is not the release's: Claude Code's own markers, and what running the tools leaves.
_COPY_NOISE_FILES = (".in_use", ".orphaned_at", ".DS_Store")
#: `.in_use` is a FOLDER on Windows, one file per process holding the plugin (`.in_use/4368`, the W-6 candidate run on
#: the VM refused a fresh plugin install over it); a marker either way, never the release's.
_COPY_NOISE_DIRS = (".git", "__pycache__", ".in_use", ".orphaned_at")


def blob_id(data):
    """git's id of a file's bytes (`git hash-object`), computed here: no repository needed, no process per file."""
    import hashlib
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def copy_version(root):
    """The `version` in the copy's `.claude-plugin/plugin.json`, or "" -- the tag a copy says it is."""
    try:
        with open(os.path.join(root, ".claude-plugin", "plugin.json"), encoding="utf-8") as fh:
            got = json.load(fh).get("version", "")
    except (OSError, ValueError, AttributeError):
        return ""
    return got if isinstance(got, str) else ""


def copy_files(root):
    """`{relative posix path: absolute path}` of every file in the copy, the noise left out."""
    out = {}
    for here, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in _COPY_NOISE_DIRS]
        for name in files:
            if name in _COPY_NOISE_FILES or name.endswith(".pyc"):
                continue
            path = os.path.join(here, name)
            out[os.path.relpath(path, root).replace(os.sep, "/")] = path
    return out


def copy_tag(root, repo=None):
    """The tag a plugin copy is checked against: `v<version>` from its `plugin.json`, or -- before that release
    exists -- its newest candidate `beta-v<version>-rcN`, so a candidate can be installed and set up as a plugin too
    (the W-6 run of rc1). Asked of the remote, like the installers' ls-remote; "" when neither is there."""
    version = copy_version(os.path.abspath(root))
    if not version:
        return ""
    rc, out, _ = run(["git", "ls-remote", "--tags", "--refs", repo or SKILL_REPO, f"v{version}",
                      f"beta-v{version}-rc*"], timeout=60)
    names = [line.rsplit("/", 1)[-1] for line in out.splitlines() if rc == 0 and "refs/tags/" in line]
    if f"v{version}" in names:
        return f"v{version}"
    candidates = [n for n in names if _CANDIDATE_RE.fullmatch(n)]
    return max(candidates, key=lambda n: int(_CANDIDATE_RE.fullmatch(n).group(4))) if candidates else ""


def verify_copy(root, repo=None, tag=None):
    """A copy with no `.git` -- what `/plugin install` leaves -- checked against its signed release tag (W-6 #121).

    The catalog pins a commit, and Claude Code checks that commit out: git's content addressing holds the copy to the
    pin, but nothing holds the pin to the author -- whoever can change the catalog can change the sha, and Claude Code
    verifies no signature (2026-10-02, the plugin docs). So the copy is held to what the installers hold a clone to:
    the release tag named by its own `plugin.json` is fetched into a throwaway bare repository, its signature verified
    against the constant key, and every file of its tree compared, by blob id, with the copy. A file missing, changed
    or added is a refusal that names it. A line ending turned into CRLF by a Windows checkout is the same file.
    """
    root = os.path.abspath(root)
    version = copy_version(root)
    tag = tag or copy_tag(root, repo) or (f"v{version}" if version else "")
    if not is_release_tag(tag):
        raise Refused(f"{root}: no release version in .claude-plugin/plugin.json ({version!r}), so no tag to check "
                      f"this copy against")
    # Could not check (git, the network) is CannotCheck, exit 4; not as signed (a signature, a file) is Refused, 3.
    with tempfile.TemporaryDirectory(prefix="autosound_verify_") as bare:
        rc, _, err = run(["git", "init", "--quiet", "--bare", bare])
        if rc != 0:
            raise CannotCheck(f"git is needed to check this copy, and `git init` failed: {err.strip()}")
        rc, _, err = git(bare, "fetch", "--quiet", "--depth", "1", repo or SKILL_REPO,
                         f"+refs/tags/{tag}:refs/tags/{tag}", timeout=300)
        if rc != 0:
            raise CannotCheck(f"could not fetch {tag} to check this copy against (no network?): {err.strip()}")
        ok, said = verify_tag(bare, tag)
        if not ok:
            raise Refused(said)
        rc, out, err = git(bare, "ls-tree", "-r", "-z", "--full-tree", f"refs/tags/{tag}^{{commit}}")
        if rc != 0:
            raise CannotCheck(f"could not list {tag}: {err.strip()}")
    expected = {}
    for entry in out.split("\0"):
        if "\t" not in entry:
            continue
        meta, path = entry.split("\t", 1)
        mode, kind, oid = meta.split()
        if kind == "blob":
            expected[path] = oid
    local = copy_files(root)
    missing = sorted(set(expected) - set(local))
    added = sorted(set(local) - set(expected))
    changed = []
    for path in sorted(set(expected) & set(local)):
        with open(local[path], "rb") as fh:
            data = fh.read()
        if expected[path] not in (blob_id(data), blob_id(data.replace(b"\r\n", b"\n"))):
            changed.append(path)
    if missing or added or changed:
        def few(paths):
            return ", ".join(paths[:5]) + (f" (+{len(paths) - 5} more)" if len(paths) > 5 else "")
        parts = [f"{len(changed)} changed: {few(changed)}" if changed else "",
                 f"{len(missing)} missing: {few(missing)}" if missing else "",
                 f"{len(added)} not in the release: {few(added)}" if added else ""]
        raise Refused(f"{root} is not {tag} as its author signed it -- " + "; ".join(p for p in parts if p)
                      + ". Reinstall the plugin, or install with the installer (install.sh / install.ps1)")
    return {"root": root, "tag": tag, "signature": said, "files": len(expected)}


def plugin_ready(root, path=None):
    """Write down that the copy's version is verified and set up here (#120): one line, `vX.Y.Z`, kept once."""
    version = copy_version(os.path.abspath(root))
    if tag_key(f"v{version}") is None:
        raise Refused(f"{root}: no release version in .claude-plugin/plugin.json ({version!r})")
    path = path or ready_file()
    try:
        with open(path, encoding="utf-8") as fh:
            have = [line.strip() for line in fh if line.strip()]
    except OSError:
        have = []
    if f"v{version}" not in have:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        # "\n" on every platform (T-39, #142): the hook reads each line whole (`grep -x`), and Windows' text mode
        # wrote "\r\n" -- the set-up note never went away there.
        with open(path, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(f"v{version}\n")
    return {"root": os.path.abspath(root), "version": f"v{version}", "file": path}


# ── the clone and its local changes (#91, #92) ───────────────────────────────────────────────────
def changed_files(clone):
    """What `git status` names -- changed, deleted, new; ignored files are not the user's work on the skill."""
    rc, out, err = git(clone, "status", "--porcelain", "--untracked-files=all")
    if rc != 0:
        raise Refused(f"{clone}: git status failed -- {err.strip()}")
    return [line[3:].strip() for line in out.splitlines() if line.strip()]


def describe(clone):
    rc, out, _ = git(clone, "describe", "--tags", "--always")
    return out.strip() if rc == 0 else "unknown"


def make_patch(clone):
    """Every local change, new files included, as one binary patch against HEAD -- built in a temporary index,
    so the clone's own index is not touched."""
    with tempfile.TemporaryDirectory(prefix="autosound_index_") as tmp:
        env = dict(os.environ, GIT_INDEX_FILE=os.path.join(tmp, "index"))
        for args in (("read-tree", "HEAD"), ("add", "-A")):
            rc, _, err = git(clone, *args, env=env)
            if rc != 0:
                raise Refused(f"{clone}: could not collect the local changes ({' '.join(args)}): {err.strip()}")
        # Bytes, not text: a file checked out with CRLF (every .ps1 on Windows) carries them in its diff lines, and
        # reading the diff as text would turn them into LF -- a patch that no longer applies to what it came from.
        p = subprocess.run(["git", "-C", clone, "diff", "--cached", "--binary", "HEAD"], env=env,
                           capture_output=True, stdin=subprocess.DEVNULL)
        if p.returncode != 0:
            raise Refused(f"{clone}: could not write the local changes as a patch: "
                          f"{p.stderr.decode('utf-8', 'replace').strip()}")
        return p.stdout


def keep_local(clone=CLONE, send=False, out_dir=LOCAL_CHANGES, poster=None, now=None):
    """Keep the clone's local changes as a patch, send it to the skill when asked, reset the clone.

    The reset happens only after the patch is on disk AND reverse-applies to the clone as it is -- the check that
    the file holds exactly the changes about to be discarded. `send` is the person's OK, asked by the caller
    (TCC's dialog, the installer's prompt): an issue leaves the machine. Returns a dict for `--json`."""
    files = changed_files(clone)
    if not files:
        return {"clone": clone, "changed": [], "patch": None, "sent": None, "reset": False}
    version = describe(clone)
    patch = make_patch(clone)
    os.makedirs(out_dir, exist_ok=True)
    stamp = (now or datetime.datetime.now()).strftime("%Y%m%d-%H%M%S")
    path = os.path.join(out_dir, f"{stamp}-{re.sub(r'[^A-Za-z0-9._-]', '_', version)}.patch")
    with open(path, "wb") as fh:
        fh.write(patch)
    rc, _, err = git(clone, "apply", "--check", "-R", "--binary", path)
    if rc != 0:
        raise Refused(f"{path} does not hold the clone's changes exactly ({err.strip()}); nothing was reset -- "
                      f"the changes are still in {clone}")
    sent = None
    if send:
        sent = send_patch(path, version, files, poster=poster)
    for args in (("reset", "--hard", "-q", "HEAD"), ("clean", "-fdq")):
        rc, _, err = git(clone, *args)
        if rc != 0:
            raise Refused(f"{clone}: {' '.join(args)} failed -- {err.strip()}; the patch is kept at {path}")
    return {"clone": clone, "changed": files, "version": version, "patch": path, "sent": sent, "reset": True}


def patch_issue_body(path, version, files, limit=50000):
    with open(path, encoding="utf-8", errors="replace") as fh:
        diff = fh.read()
    cut = len(diff) > limit
    return "\n".join([
        f"# Local change in the installed skill ({version})",
        "",
        "Sent by the skill's update path (`scripts/upkeep.py keep-local --send`) with the person's OK, before the "
        "installed clone was reset and updated. The patch was also kept on that machine.",
        "",
        f"- **Version:** `{version}`",
        "- **Files:** " + ", ".join(f"`{f}`" for f in files),
        "",
        "```diff",
        diff[:limit].rstrip("\n"),
        "```",
        "" if not cut else f"(cut at {limit} characters; the whole patch is {len(diff)} characters)",
    ])


def send_patch(path, version, files, poster=None):
    """The issue, through the feedback gate (the repo is the gate's, never ours to name). A patch that cannot be
    sent is not a reason to stop: the answer says so and the patch stays on disk."""
    body = path + ".issue.md"
    with open(body, "w", encoding="utf-8") as fh:
        fh.write(patch_issue_body(path, version, files))
    if poster is None:
        sys.path.insert(0, os.path.join(SKILL_DIR, "rew_tool", "gates"))
        try:
            import side_effect
        except ImportError as exc:
            return {"sent": False, "why": f"the feedback gate is missing ({exc})"}

        def poster(body_file, title):
            if not side_effect.gh_ready():
                return {"sent": False, "why": "no GitHub here (`gh` missing or not signed in); the patch is kept"}
            got = side_effect.post_feedback(body_file, "installed skill", version, via="github", title=title)
            if got.get("skipped"):
                return {"sent": False, "why": f"already posted: {got.get('duplicate_url')}"}
            return {"sent": True, "url": (got.get("stdout") or "").strip()}
    try:
        return poster(body, f"Local change in the installed skill ({version}): " + ", ".join(files[:3])
                      + (f" and {len(files) - 3} more" if len(files) > 3 else ""))
    except Exception as exc:  # noqa: BLE001 -- a refused send keeps the patch and says why
        return {"sent": False, "why": str(exc).splitlines()[0] if str(exc) else type(exc).__name__}


def update_clone(clone=CLONE, tag=None, repo=None):
    """Move the clone to `tag` (default: the newest release): fetched into refs/tags so `describe` names it (#92),
    signature verified (#99), checked out. A clone with local changes is refused, naming `keep-local`.

    An update that does not land leaves refs/tags as it found them (R48, #142): the tag its fetch wrote is deleted
    again, or -- a local tag of that name was there before, and the fetch's `+` overwrote it -- given its old value back.
    A refused tag stayed, "nothing was changed" was not true of refs/tags, and `describe` could name it. `--no-tags`:
    the one tag asked for, not every tag git would bring along on the same commit -- a refused one's siblings."""
    files = changed_files(clone)
    if files:
        raise Refused(f"{clone} has local changes ({', '.join(files[:5])}{' …' if len(files) > 5 else ''}); "
                      f"`upkeep.py keep-local` keeps them as a patch and resets the clone, then run this again")
    was = describe(clone)
    tag = tag or newest_tag(repo or SKILL_REPO)
    if not tag:
        raise Refused("the newest release could not be asked for (no network?); nothing was changed")
    ref = f"refs/tags/{tag}"
    rc, had, _ = git(clone, "rev-parse", "--verify", "--quiet", ref)
    had = had.strip() if rc == 0 else ""
    rc, _, err = git(clone, "fetch", "--quiet", "--no-tags", "--depth", "1", repo or "origin", f"+{ref}:{ref}",
                     timeout=300)
    if rc != 0:
        raise Refused(f"could not fetch {tag}: {err.strip()}; nothing was changed")

    def put_back():
        rc, _, err = git(clone, "update-ref", ref, had) if had else git(clone, "update-ref", "-d", ref)
        return "" if rc == 0 else f" ({ref} could not be put back as it was: {err.strip()})"

    ok, said = verify_tag(clone, tag)
    if not ok:
        raise Refused(said + "; nothing was changed" + put_back())
    rc, _, err = git(clone, "-c", "advice.detachedHead=false", "checkout", "--quiet", f"{ref}^{{commit}}")
    if rc != 0:
        raise Refused(f"could not check out {tag}: {err.strip()}" + put_back())
    # The tag asked for, not `describe`: a release lands on its candidate's commit, so `beta-…-rc2` and the release
    # can name one commit, and `describe` picks between them by tagger date -- in the selftest's fixture, within one
    # second, by chance (W-5: the suite named v3.0.66 once).
    return {"clone": clone, "from": was, "to": tag, "signature": said}


# ── tools (#97, hub #219) ────────────────────────────────────────────────────────────────────────
TOOLS = ("claude", "omp", "agy", "gh")


def locate(name, env=None):
    """Where the tool is, the way the installers' `find_bin` looks: PATH, then the folders they install into."""
    env = os.environ if env is None else env
    exe = name + (".exe" if sys.platform == "win32" else "")
    found = shutil.which(name, path=env.get("PATH"))
    if found:
        return found
    extra = [LOCAL_BIN]
    if sys.platform == "win32":
        local = env.get("LOCALAPPDATA", "")
        extra += [os.path.join(local, "agy", "bin"), os.path.join(local, "omp")]
    for d in extra:
        p = os.path.join(d, exe)
        if os.path.isfile(p):
            return p
    return None


def how_installed(name, path):
    """`(how, package)`: brew · brew-cask · npm · self (its own `update`) · release (the installer's download) ·
    other. The answer follows where the binary really is, because updating a Homebrew omp with omp's own
    updater, or gh from a release over a Homebrew one, would leave two copies and a PATH that picks one."""
    real = os.path.realpath(path).replace("\\", "/")
    m = re.search(r"/Cellar/([^/]+)/", real)
    if m:
        return "brew", m.group(1)
    m = re.search(r"/Caskroom/([^/]+)/", real)
    if m:
        return "brew-cask", m.group(1)
    if name == "claude":
        return ("npm" if "/node_modules/" in real else "self"), "@anthropic-ai/claude-code"
    if name in ("omp", "agy"):
        return "self", name
    if name == "gh" and os.path.dirname(os.path.abspath(path)) == os.path.abspath(LOCAL_BIN):
        return "release", "cli/cli"
    return "other", name


_VERSION_RE = re.compile(r"(\d+\.\d+(?:\.\d+)?)")


def tool_version(path):
    rc, out, err = run([path, "--version"], timeout=30)
    m = _VERSION_RE.search(out or err or "")
    return m.group(1) if (rc == 0 and m) else ""


def _brew():
    return shutil.which("brew") or next((p for p in ("/opt/homebrew/bin/brew", "/usr/local/bin/brew")
                                         if os.path.isfile(p)), None)


#: Where a self-installed agy and a native Claude Code say what is newest, without installing (W-6 #126, hub #237).
#: agy's own installers read a manifest per platform from its update server (`antigravity.google/cli/install.sh`,
#: `install.ps1`, 2026-10-02); Claude Code's native updater follows a CHANNEL (`autoUpdatesChannel` in
#: `~/.claude/settings.json`, `latest` by default, or `stable`), whose newest is the npm registry's dist-tag of that name
#: -- read over HTTP, so no npm is needed. TCC's Updates row could only say «cannot be known» for these two before.
AGY_MANIFEST = "https://antigravity-cli-auto-updater-974169037036.us-central1.run.app/manifests/{platform}.json"
CLAUDE_DIST_TAGS = "https://registry.npmjs.org/-/package/@anthropic-ai/claude-code/dist-tags"


def _http_json(url, timeout=20):
    """The JSON at `url`, or None for any failure -- an unknown is "", never an exception in a status row."""
    import urllib.request
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"Accept": "application/json"}),
                                    timeout=timeout) as r:
            return json.load(r)
    except Exception:  # noqa: BLE001
        return None


def agy_platform(platform=None, machine=None):
    """agy's manifest name for this machine (`darwin_arm64`, `windows_amd64`, `linux_amd64[_musl]`), or "" when it
    builds for none of them. The same rule as agy's installers."""
    import platform as _platform
    system = (platform or sys.platform)
    machine = (machine or _platform.machine() or "").lower()
    arch = {"x86_64": "amd64", "amd64": "amd64", "arm64": "arm64", "aarch64": "arm64"}.get(machine)
    if not arch:
        return ""
    if system.startswith("darwin"):
        return f"darwin_{arch}"
    if system.startswith("win"):
        return f"windows_{arch}"
    if system.startswith("linux"):
        musl = any(os.path.exists(f) for f in ("/lib/libc.musl-x86_64.so.1", "/lib/libc.musl-aarch64.so.1"))
        return f"linux_{arch}" + ("_musl" if musl else "")
    return ""


def claude_channel(home=None):
    """The native Claude Code's update channel: `autoUpdatesChannel` from `~/.claude/settings.json`, `latest` when unset."""
    path = os.path.join(home or os.path.expanduser("~"), ".claude", "settings.json")
    try:
        with open(path, encoding="utf-8") as fh:
            got = (json.load(fh) or {}).get("autoUpdatesChannel")
    except (OSError, ValueError, AttributeError):
        got = None
    return got if got in ("latest", "stable") else "latest"


def available_version(name, path, how, package, runner=run, fetch=_http_json, home=None):
    """What the tool's source offers now, or "" when it cannot say without installing."""
    if how in ("brew", "brew-cask") and _brew():
        rc, out, _ = runner([_brew(), "info", "--json=v2", ("--cask" if how == "brew-cask" else "--formula"),
                             package], timeout=60)
        try:
            data = json.loads(out) if rc == 0 else {}
            if how == "brew":
                return data["formulae"][0]["versions"]["stable"]
            return str(data["casks"][0]["version"]).split(",")[0]
        except (ValueError, KeyError, IndexError):
            return ""
    if name == "omp" and how == "self":
        rc, out, err = runner([path, "update", "--check"], timeout=60)
        m = re.search(r"New version available:\s*v?(\S+)", out + err)
        if m:
            return m.group(1)
        m = re.search(r"Current version:\s*v?(\S+)", out + err)
        return m.group(1) if (rc == 0 and m) else ""
    if name == "claude" and how == "npm":
        rc, out, _ = runner(["npm", "view", package, "version"], timeout=60)
        return out.strip() if rc == 0 else ""
    if name == "claude" and how == "self":
        tags = fetch(CLAUDE_DIST_TAGS) or {}
        got = tags.get(claude_channel(home)) if isinstance(tags, dict) else None
        return got if isinstance(got, str) and _VERSION_RE.fullmatch(got) else ""
    if name == "agy" and how == "self":
        platform = agy_platform()
        manifest = fetch(AGY_MANIFEST.format(platform=platform)) if platform else None
        got = manifest.get("version") if isinstance(manifest, dict) else None
        return got if isinstance(got, str) and _VERSION_RE.fullmatch(got) else ""
    if how == "release":
        return _gh_latest()
    return ""


def _gh_latest():
    import urllib.request
    try:
        req = urllib.request.Request("https://api.github.com/repos/cli/cli/releases/latest",
                                     headers={"Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r).get("tag_name", "").lstrip("v")
    except Exception:  # noqa: BLE001 -- no answer is "", which the caller shows as unknown
        return ""


def update_command(name, path, how, package):
    """The command that updates this tool the way it was installed; None when it is not ours to update."""
    if how == "brew":
        return [_brew() or "brew", "upgrade", package]
    if how == "brew-cask":
        return [_brew() or "brew", "upgrade", "--cask", package]
    if how in ("self", "npm"):
        return [path, "update"]        # `claude update` handles an npm install itself; omp and agy update themselves
    if how == "release":
        return ["<release>", "cli/cli"]
    return None


def tool_rows(env=None, runner=run, ask_available=True, fetch=_http_json):
    rows = []
    for name in TOOLS:
        path = locate(name, env)
        if not path:
            continue                       # never installed here: nothing is added (#97 ask 1)
        how, package = how_installed(name, path)
        rows.append({"name": name, "path": path, "how": how, "package": package,
                     "installed": tool_version(path),
                     "available": available_version(name, path, how, package, runner, fetch) if ask_available else "",
                     "updatable": update_command(name, path, how, package) is not None})
    return rows


def update_gh_release(dest_dir=LOCAL_BIN):
    """gh from its newest GitHub release, checked against the checksums that release publishes -- the installers'
    path, so an installer-installed gh moves the way it came. The old binary is replaced only after the check."""
    import hashlib
    import tarfile
    import urllib.request
    import zipfile
    ver = _gh_latest()
    if not ver:
        raise Refused("gh: the newest release could not be asked for (no network?)")
    import platform
    arch = "arm64" if platform.machine().lower() in ("arm64", "aarch64") else "amd64"
    system = {"darwin": "macOS", "win32": "windows"}.get(sys.platform, "linux")
    asset = f"gh_{ver}_{system}_{arch}." + ("tar.gz" if system == "linux" else "zip")
    base = f"https://github.com/cli/cli/releases/download/v{ver}"
    with tempfile.TemporaryDirectory(prefix="autosound_gh_") as tmp:
        got = os.path.join(tmp, asset)
        urllib.request.urlretrieve(f"{base}/{asset}", got)
        sums = urllib.request.urlopen(f"{base}/gh_{ver}_checksums.txt", timeout=60).read().decode()
        want = next((line.split()[0] for line in sums.splitlines() if line.split()[-1:] == [asset]), "")
        with open(got, "rb") as fh:
            have = hashlib.sha256(fh.read()).hexdigest()
        if not want or want != have:
            raise Refused(f"gh: the download does not match the checksum its release publishes "
                          f"(expected {want or 'no line'}, got {have}); not installed")
        if asset.endswith(".zip"):
            with zipfile.ZipFile(got) as z:
                z.extractall(tmp)
        else:
            with tarfile.open(got) as t:
                t.extractall(tmp)
        exe = "gh.exe" if sys.platform == "win32" else "gh"
        built = next((os.path.join(d, exe) for d, _, names in os.walk(tmp) if exe in names and d.endswith("bin")), None)
        if not built:
            raise Refused(f"gh: no {exe} in {asset}")
        target = os.path.join(dest_dir, exe)
        staged = target + ".new"
        shutil.copy2(built, staged)
        os.chmod(staged, 0o755)
        os.replace(staged, target)
    return ver


def update_tools(only=None, env=None, runner=run, gh_updater=update_gh_release):
    """Every present tool (or `only`) updated the way it was installed; one row each with old -> new. A failed
    update leaves the tool as it was -- the package managers and the self-updaters swap atomically, and gh is
    replaced only after its checksum -- and says why."""
    out = []
    for row in tool_rows(env=env, runner=runner, ask_available=False):
        if only and row["name"] not in only:
            continue
        cmd = update_command(row["name"], row["path"], row["how"], row["package"])
        entry = {"name": row["name"], "how": row["how"], "old": row["installed"]}
        if cmd is None:
            entry.update(ok=False, why=f"installed some other way ({row['path']}); update it the way it was installed")
        elif cmd[0] == "<release>":
            try:
                gh_updater()
                entry.update(ok=True)
            except Exception as exc:  # noqa: BLE001
                entry.update(ok=False, why=str(exc))
        else:
            rc, so, se = runner(cmd, timeout=900)
            entry.update(ok=rc == 0, command=" ".join(cmd))
            if rc != 0:
                entry["why"] = ((se or so).strip().splitlines() or [f"exit {rc}"])[-1]
        entry["new"] = tool_version(row["path"]) if runner is run else entry["old"]
        out.append(entry)
    return out


# ── the libraries (#98) ──────────────────────────────────────────────────────────────────────────
LIBS = ("numpy", "scipy", "matplotlib")


def method_python(env=None):
    """The interpreter the method's tools run on: `python3` as the method calls it. On Windows the installer puts
    uv's real one in ~\\.local\\bin, ahead of the Store's alias."""
    env = os.environ if env is None else env
    if sys.platform == "win32":
        p = os.path.join(LOCAL_BIN, "python3.exe")
        if os.path.isfile(p):
            return p
    return shutil.which("python3", path=env.get("PATH"))


def pip_command(py, requirements=REQUIREMENTS, in_venv=False, platform=sys.platform):
    """The installers' command, with `--upgrade`: in a venv as it is; outside one `--user`, and on Windows
    `--break-system-packages` too (uv marks its Pythons externally managed)."""
    cmd = [py, "-m", "pip", "install", "--quiet", "--upgrade", "--no-warn-script-location",
           "--disable-pip-version-check"]
    if not in_venv:
        cmd.append("--user")
        if platform == "win32":
            cmd.append("--break-system-packages")
    return cmd + ["-r", requirements]


def lib_versions(py):
    code = ("import json, importlib.metadata as m\nout = {}\nfor n in %r:\n    try:\n        out[n] = m.version(n)\n"
            "    except Exception:\n        out[n] = ''\nprint(json.dumps(out))") % (LIBS,)
    rc, out, _ = run([py, "-c", code], timeout=60)
    try:
        return json.loads(out) if rc == 0 else {}
    except ValueError:
        return {}


def update_libs(py=None, requirements=REQUIREMENTS, runner=run):
    py = py or method_python()
    if not py:
        raise Refused("no python3 on this machine, so the method's tools have nothing to run on")
    rc, out, _ = runner([py, "-c", "import sys; print(sys.prefix != sys.base_prefix)"], timeout=30)
    before = lib_versions(py) if runner is run else {}
    cmd = pip_command(py, requirements, in_venv=out.strip() == "True")
    rc, so, se = runner(cmd, timeout=900)
    after = lib_versions(py) if runner is run else {}
    return {"python": py, "command": " ".join(cmd), "ok": rc == 0, "before": before, "after": after,
            "why": "" if rc == 0 else ((se or so).strip().splitlines() or [f"exit {rc}"])[-1]}


# ── status ───────────────────────────────────────────────────────────────────────────────────────
def status(clone=CLONE):
    info = {"clone": {"path": clone, "exists": os.path.isdir(os.path.join(clone, ".git"))}}
    if info["clone"]["exists"]:
        try:
            info["clone"].update(version=describe(clone), changed=changed_files(clone))
        except Refused as exc:
            info["clone"]["error"] = str(exc)
    info["tools"] = tool_rows()
    py = method_python()
    info["libs"] = {"python": py or "", "installed": lib_versions(py) if py else {}}
    return info


def _print_status(info):
    c = info["clone"]
    print(f"skill: {c.get('version', 'not installed')} at {c['path']}"
          + (f" -- local changes: {', '.join(c['changed'])}" if c.get("changed") else ""))
    for t in info["tools"]:
        avail = t["available"] or "?"
        mark = "  (update available)" if t["available"] and t["available"] != t["installed"] else ""
        print(f"  {t['name']:7} {t['installed'] or '?':>10} -> {avail:<10} via {t['how']}{mark}")
    libs = info["libs"]
    print(f"libraries in {libs['python'] or 'no python3'}: "
          + ", ".join(f"{k} {v or 'missing'}" for k, v in libs["installed"].items()))


def main(argv=None):
    p = argparse.ArgumentParser(prog="upkeep.py", description=__doc__.split("\n\n")[0])
    p.add_argument("--json", action="store_true", help="one JSON object on stdout")
    p.add_argument("--clone", default=CLONE, help=f"the installed clone (default {CLONE})")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("status")
    kp = sub.add_parser("keep-local")
    kp.add_argument("--send", action="store_true", help="send the patch to the skill as an issue -- only after the "
                                                        "person said yes: it leaves the machine")
    cp = sub.add_parser("clone")
    cp.add_argument("--tag", default=None, help="the release to move to (default: the newest)")
    tp = sub.add_parser("tools")
    tp.add_argument("--only", action="append", choices=TOOLS)
    sub.add_parser("libs")
    vp = sub.add_parser("verify-copy")
    vp.add_argument("--root", required=True, help="the copy's root: the folder holding .claude-plugin/")
    vp.add_argument("--tag", default=None, help="the release to check against (default: v<plugin.json version>)")
    rp = sub.add_parser("plugin-ready")
    rp.add_argument("--root", required=True, help="the plugin copy's root")
    sub.add_parser("selftest")
    args = p.parse_args(argv)
    if args.cmd == "selftest":
        return _selftest()
    if args.cmd is None:
        p.print_help()
        return 2
    try:
        if args.cmd == "status":
            got = status(args.clone)
        elif args.cmd == "keep-local":
            got = keep_local(args.clone, send=args.send)
        elif args.cmd == "clone":
            got = update_clone(args.clone, args.tag)
        elif args.cmd == "tools":
            got = update_tools(args.only)
        elif args.cmd == "verify-copy":
            got = verify_copy(args.root, tag=args.tag)
        elif args.cmd == "plugin-ready":
            got = plugin_ready(args.root)
        else:
            got = update_libs()
    except Refused as exc:
        # The code by the exception's own attribute (#142): 4 for a copy that could not be checked at all, 3 otherwise.
        code = getattr(exc, "exit_code", 3)
        word = "could not check" if code == 4 else "refused"
        if args.json:
            print(json.dumps({"ok": False, "refused": str(exc), "exit_code": code}, ensure_ascii=False))
        else:
            print(f"{word}: {exc}", file=sys.stderr)
        return code
    if args.json:
        print(json.dumps(got, ensure_ascii=False, indent=1))
        return 0 if _ok(args.cmd, got) else 3
    if args.cmd == "status":
        _print_status(got)
    elif args.cmd == "keep-local":
        if not got["changed"]:
            print(f"{got['clone']}: no local changes")
        else:
            print(f"kept {len(got['changed'])} changed file(s) of {got['version']} as {got['patch']}")
            sent = got["sent"]
            if sent:
                print(f"sent to the skill: {sent['url']}" if sent.get("sent") else f"not sent: {sent['why']}")
            print(f"{got['clone']} is reset to {got['version']}; `git apply {got['patch']}` there brings the changes back")
    elif args.cmd == "clone":
        print(f"skill {got['from']} -> {got['to']} ({got['signature']})")
    elif args.cmd == "verify-copy":
        print(f"✓ {got['root']} is {got['tag']} as its author signed it: {got['files']} files ({got['signature']})")
    elif args.cmd == "plugin-ready":
        print(f"{got['version']} is set up here ({got['file']})")
    elif args.cmd == "tools":
        for t in got:
            print(f"  {t['name']:7} {t['old'] or '?'} -> {t['new'] or '?'}" if t["ok"] else
                  f"  {t['name']:7} {t['old'] or '?'} -- not updated: {t['why']}")
        if not got:
            print("none of omp, agy, gh, Claude Code is installed here -- nothing to update")
    else:
        print(f"libraries in {got['python']}: " + (", ".join(
            f"{k} {got['before'].get(k) or 'missing'} -> {v or 'missing'}" for k, v in got["after"].items())
            if got["ok"] else f"not upgraded: {got['why']}"))
    return 0 if _ok(args.cmd, got) else 3


def _ok(cmd, got):
    if cmd == "tools":
        return all(t["ok"] for t in got)
    if cmd == "libs":
        return got["ok"]
    return True


# ── selftest ─────────────────────────────────────────────────────────────────────────────────────
#: T-35 (#142): what the person's own git configuration may hold, and a `git` that is not git. Each answers "Good" one
#: way or another; none of them is the author's signature. A fake `gpg.program` stands in for gpg: no real one runs,
#: and no keyring is touched. Bytes, so a script keeps its "\n" line ends on Windows.
_SIGN_ONLY_HELPER = b"#!/bin/sh\necho 'helper: sign-only (try -Y sign)' >&2\nexit 1\n"


def _fake_gpg(uid):
    """A `gpg.program` that calls any OpenPGP signature good, from a key whose user id is `uid` -- printed after gpg's
    own `gpg: ` prefix. Runs no real gpg."""
    return (b"#!/bin/sh\n"
            b"cat >/dev/null\n"
            b"echo '[GNUPG:] NEWSIG'\n"
            + f"echo '[GNUPG:] GOODSIG 0123456789ABCDEF {uid}'\n".encode("utf-8")
            + b"echo '[GNUPG:] VALIDSIG 0123456789ABCDEF0123456789ABCDEF01234567 2026-10-08 0 0 0 0 0 1 0 "
              b"0123456789ABCDEF0123456789ABCDEF01234567'\n"
              b"echo '[GNUPG:] TRUST_ULTIMATE 0 pgp'\n"
            + f"echo 'gpg: Good signature from \"{uid}\" [ultimate]' >&2\n".encode("utf-8")
            + b"exit 0\n")


_FAKE_GPG = _fake_gpg("Mallory <m@example.org>")
#: #142 (PTA 4): a user id that IS the author's sentence (the selftest's principal is `author`): only a test held to the
#: start of a line refuses it -- gpg prints it inside its own line.
_FORGED_UID = 'Good "git" signature for author with ED25519 key SHA256:forged'
_STUB_GIT = (b"#!/bin/sh\n"
             b"for a in \"$@\"; do\n"
             b"  if [ \"$a\" = verify-tag ]; then echo 'Good signature from \"anyone\"' >&2; exit 0; fi\n"
             b"done\n"
             b"exec /usr/bin/git \"$@\"\n")
#: A tag message that ends in an OpenPGP block -- any base64 body: git hands it to `gpg.program` as it is.
_PGP_SIGNED_MESSAGE = (b"v3.0.67\n\n-----BEGIN PGP SIGNATURE-----\n\n"
                       b"iQEzBAABCAAdFiEEASNFZ4mrze8BI0VniavN7wEjRWcFAmcFAAAACgkQASNFZ4mrze8AAA==\n=AAAA\n"
                       b"-----END PGP SIGNATURE-----\n")


def _signature_fixture(tmp, env, anchor, author_key):
    """The T-35 cases' ground, under `tmp/t35`: a repo with v3.0.64 signed by the key at `author_key` (git is given
    its `.pub`) and v3.0.67 whose message ends in an OpenPGP block; a sign-only helper named by `hostile.gitconfig`, a
    fake gpg named by `pgp.gitconfig`, `gpg.minTrustLevel=ultimate` in `ultimate.gitconfig`, and `stub-git/git`. Runs
    no real gpg."""
    base = os.path.join(tmp, "t35")
    repo, stub_dir = os.path.join(base, "repo"), os.path.join(base, "stub-git")
    os.makedirs(repo)
    os.makedirs(stub_dir)

    def sh(*cmd):
        rc, out, err = run(list(cmd), env=env)
        assert rc == 0, (cmd, out, err)

    sh("git", "init", "-q", repo)
    with open(os.path.join(repo, "a.txt"), "w", encoding="utf-8") as fh:
        fh.write("one\n")
    sh("git", "-C", repo, "add", "a.txt")
    sh("git", "-C", repo, "commit", "-q", "-m", "one")
    sh("git", "-C", repo, "-c", "gpg.format=ssh", "-c", f"user.signingkey={author_key}.pub", "tag", "-s", "v3.0.64",
       "-m", "signed")
    for name, body in (("pgp-message", _PGP_SIGNED_MESSAGE), ("sign-only.sh", _SIGN_ONLY_HELPER),
                       ("fake-gpg.sh", _FAKE_GPG), ("forged-gpg.sh", _fake_gpg(_FORGED_UID)),
                       (os.path.join("stub-git", "git"), _STUB_GIT)):
        with open(os.path.join(base, name), "wb") as fh:
            fh.write(body)
        os.chmod(os.path.join(base, name), 0o755)
    sh("git", "-C", repo, "tag", "-a", "v3.0.67", "-F", os.path.join(base, "pgp-message"))
    configs = {"hostile": ('[gpg "ssh"]', "sign-only.sh"), "pgp": ("[gpg]", "fake-gpg.sh"),
               "forged": ("[gpg]", "forged-gpg.sh")}
    for name, (section, program) in configs.items():
        program = os.path.join(base, program).replace(os.sep, "/")   # forward slashes: a config's "\" escapes
        with open(os.path.join(base, name + ".gitconfig"), "wb") as fh:
            fh.write(f"{section}\n\tprogram = {program}\n".encode("utf-8"))
    with open(os.path.join(base, "ultimate.gitconfig"), "wb") as fh:
        fh.write(b"[gpg]\n\tminTrustLevel = ultimate\n")
    return {"repo": repo, "env": env, "anchor": anchor, "stub_dir": stub_dir,
            "hostile": os.path.join(base, "hostile.gitconfig"), "pgp": os.path.join(base, "pgp.gitconfig"),
            "forged": os.path.join(base, "forged.gitconfig"), "ultimate": os.path.join(base, "ultimate.gitconfig")}


def _check_a_signing_helper_is_not_asked(fx):
    """A sign-only helper as the person's gpg.ssh.program (1Password's, for one) cannot verify: ssh-keygen does, and
    the author's tag passes."""
    ok, said = verify_tag(fx["repo"], "v3.0.64", env=dict(fx["env"], GIT_CONFIG_GLOBAL=fx["hostile"]), **fx["anchor"])
    assert ok and "signature good" in said, said


def _check_an_openpgp_good_is_not_the_authors(fx):
    """git picks the verifier from the signature, not from gpg.format: an OpenPGP tag that the person's own gpg calls
    good exits 0 with "Good" -- and is not the author's. The fake gpg's own words must be in the answer: a fake that
    never ran is refused the same way, and would pass unseen while the person's real gpg ran."""
    ok, said = verify_tag(fx["repo"], "v3.0.67", env=dict(fx["env"], GIT_CONFIG_GLOBAL=fx["pgp"]), **fx["anchor"])
    assert not ok and "does not check out" in said and "Mallory" in said, said
    # #142 (PTA 4): the author's own sentence as the key's user id -- inside gpg's line, never at the start of one.
    ok, said = verify_tag(fx["repo"], "v3.0.67", env=dict(fx["env"], GIT_CONFIG_GLOBAL=fx["forged"]), **fx["anchor"])
    assert not ok and "does not check out" in said and "SHA256:forged" in said, said


def _check_a_git_that_says_good_is_not_believed(fx):
    """A `git` first on PATH that says "Good signature from" of any tag, with exit 0, is not the author's sentence.
    POSIX only: on Windows a child is found on the parent's PATH, and a shell script is no program to it -- "skipped",
    which the OK line then says (#142)."""
    if os.name == "nt":
        return "skipped"
    path = fx["stub_dir"] + os.pathsep + fx["env"].get("PATH", os.defpath)
    ok, said = verify_tag(fx["repo"], "v3.0.64", env=dict(fx["env"], PATH=path), **fx["anchor"])
    assert not ok and "does not check out" in said, said


def _check_a_min_trust_level_is_not_the_persons(fx):
    """A person's `gpg.minTrustLevel=ultimate` made git refuse every good release with the Good line printed: git rates
    a key in allowed_signers `fully`. The level is pinned at that, and the author's tag passes."""
    ok, said = verify_tag(fx["repo"], "v3.0.64", env=dict(fx["env"], GIT_CONFIG_GLOBAL=fx["ultimate"]),
                          **fx["anchor"])
    assert ok and "signature good" in said, said


#: The plugin's SessionStart hook: at the root of a checkout or a plugin copy, two folders above this skill.
_HOOK = os.path.normpath(os.path.join(SKILL_DIR, "..", "..", "hooks", "session-start.sh"))


def _a_bash():
    """A bash that runs a script, or None. On Windows it is Git for Windows' own, found beside `git`: the `bash` a bare
    name reaches there is often WSL's launcher in System32, which runs nothing without a Linux installed."""
    if os.name != "nt":
        return shutil.which("bash")
    found = shutil.which("git")
    if not found:
        return None
    here = os.path.dirname(os.path.realpath(found))          # ...\Git\cmd, or ...\Git\mingw64\bin
    for up in (here, os.path.dirname(here), os.path.dirname(os.path.dirname(here))):
        for rel in (("bin", "bash.exe"), ("usr", "bin", "bash.exe")):
            if os.path.isfile(os.path.join(up, *rel)):
                return os.path.join(up, *rel)
    return None


def _plugin_root(folder, version):
    """A plugin copy as the hook and `plugin_ready` read one: `.claude-plugin/plugin.json` naming `version`, no .git."""
    os.makedirs(os.path.join(folder, ".claude-plugin"))
    with open(os.path.join(folder, ".claude-plugin", "plugin.json"), "w", encoding="utf-8") as fh:
        json.dump({"name": "autosound-tuning", "version": version}, fh)
    return folder


def _check_plugin_ready_writes_its_line_byte_for_byte(tmp):
    """T-39 (#142): the ready file holds `v3.1.2` and "\\n", byte for byte, once. The hook reads each line whole (`grep
    -x`), and on Windows a text-mode write ended it "\\r\\n": the set-up note never went away. Read in binary -- text
    mode turns a "\\r\\n" back into "\\n" and hides it."""
    root = _plugin_root(os.path.join(tmp, "ready-bytes"), "3.1.2")
    ready = os.path.join(tmp, "ready-bytes", "plugin-ready")
    for _ in range(2):
        plugin_ready(root, path=ready)
    with open(ready, "rb") as fh:
        got = fh.read()
    assert got == b"v3.1.2\n", f"the ready file holds {got!r}, want b'v3.1.2\\n'"


def _check_the_hook_is_silent_once_set_up(tmp, hook=None, repo_root=None):
    """The SessionStart hook reads what `plugin_ready` writes (T-39, #142): the note while this version is not set up,
    nothing once `plugin_ready` has written it down, and nothing for a checkout -- `.git` a file in a submodule (TCC
    vendors the skill as one, hub #238), a folder in a clone. Wherever a bash runs it, Git for Windows' on Windows: the
    platform whose line ending kept the note on is the one it was never run on. Skipped only for the skill folder alone,
    with no repository root around it (`.claude-plugin/plugin.json` two folders up): where that root is, a hook that is
    not there is a failure (#142) -- it was a skip, and the check could not fail."""
    hook = hook or _HOOK
    repo_root = repo_root or os.path.normpath(os.path.join(SKILL_DIR, "..", ".."))
    if not os.path.isfile(os.path.join(repo_root, ".claude-plugin", "plugin.json")):
        return                    # the skill folder alone, without the repository's root: the hook is not shipped here
    assert os.path.isfile(hook), f"the repository's root is here ({repo_root}) and its SessionStart hook is not: {hook}"
    bash = _a_bash()
    assert bash, "no bash to run the SessionStart hook with -- on Windows, Git for Windows' own, beside git"
    home = os.path.join(tmp, "hook-home")
    root = _plugin_root(os.path.join(tmp, "hook-plugin"), "3.1.2")

    def note():
        r = subprocess.run([bash, hook], env=dict(os.environ, HOME=home, CLAUDE_PLUGIN_ROOT=root),
                           capture_output=True, text=True, timeout=30)
        assert r.returncode == 0, f"the hook exited {r.returncode}: {r.stderr.strip()[-200:]}"
        return r.stdout

    assert "v3.1.2 is not set up" in note(), "a plugin copy not set up gets the note"
    plugin_ready(root, path=os.path.join(home, ".config", "autosound", "plugin-ready"))
    said = note()
    assert said == "", f"set up by plugin_ready, the hook still says: {said[:120]!r}"
    os.remove(os.path.join(home, ".config", "autosound", "plugin-ready"))
    with open(os.path.join(root, ".git"), "w", encoding="utf-8") as fh:
        fh.write("gitdir: ../.git/modules/skill\n")
    assert note() == "", "a submodule checkout is a checkout"
    os.remove(os.path.join(root, ".git"))
    os.makedirs(os.path.join(root, ".git"))
    assert note() == "", "a clone is a checkout"


def _check_a_missing_hook_fails_the_hook_check(tmp):
    """#142 (SFH 10): the hook check above, given a repository root without its hook, FAILS -- it returned, and a hook
    that went missing passed every run."""
    fake_root = os.path.join(tmp, "root-without-hook")
    _plugin_root(fake_root, "3.1.2")
    try:
        _check_the_hook_is_silent_once_set_up(tmp, hook=os.path.join(fake_root, "hooks", "session-start.sh"),
                                              repo_root=fake_root)
    except AssertionError as exc:
        assert "SessionStart hook is not" in str(exc), exc
        return
    raise AssertionError("a repository root whose hooks/session-start.sh is gone passed the hook check")


def _check_the_ready_file_is_where_the_hook_looks(tmp):
    """#142 (SFH 10): `plugin_ready` and the hook name one file. The hook reads `$HOME/.config/autosound/plugin-ready`,
    and on Windows Git Bash's $HOME is %HOME% when that is set -- Python's `~` there is %USERPROFILE% alone, so with a
    %HOME% of its own the two were two files. Asked of `ready_file` for Windows and POSIX, then live: a HOME that is not
    USERPROFILE, `plugin_ready` with no path, and the hook run with that HOME is silent."""
    on_nt = ready_file({"HOME": os.path.join("h", "home"), "USERPROFILE": os.path.join("u", "profile")}, nt=True)
    assert on_nt == os.path.join("h", "home", ".config", "autosound", "plugin-ready"), on_nt
    no_home = ready_file({"USERPROFILE": os.path.join("u", "profile")}, nt=True)
    assert no_home == os.path.join("u", "profile", ".config", "autosound", "plugin-ready"), no_home
    posix = ready_file({"HOME": os.path.join("h", "home")}, nt=False)
    assert posix == os.path.join("h", "home", ".config", "autosound", "plugin-ready"), posix
    bash = _a_bash()
    if not os.path.isfile(_HOOK) or not bash:
        return                    # no hook beside this skill, or no bash: the live half is the hook check's ground
    home, profile = os.path.join(tmp, "ready-home"), os.path.join(tmp, "ready-profile")
    root = _plugin_root(os.path.join(tmp, "ready-plugin"), "3.1.4")
    saved = {name: os.environ.get(name) for name in ("HOME", "USERPROFILE")}
    try:
        os.environ.update(HOME=home, USERPROFILE=profile)
        written = plugin_ready(root)["file"]
    finally:
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
    r = subprocess.run([bash, _HOOK], env=dict(os.environ, HOME=home, USERPROFILE=profile, CLAUDE_PLUGIN_ROOT=root),
                       capture_output=True, text=True, timeout=30)
    assert r.returncode == 0 and r.stdout == "", (f"plugin_ready wrote {written}, and the hook run with HOME={home} "
                                                  f"still says: {r.stdout[:120]!r}")


def _check_a_refused_update_leaves_the_tags_as_they_were(fx):
    """R48 (#142): an update refused for its signature leaves refs/tags as it found them -- the tag it fetched deleted
    again, and a local tag of that name, which the fetch's `+` overwrote, given its own value back -- and HEAD where it
    was. Asked of the refs and HEAD's commit, never of `describe`: v3.0.64, v3.0.65 and v3.0.66 name one commit, and
    `describe` picks between them by tagger date (the Windows CI flake, 37858572763)."""
    base = os.path.join(fx["tmp"], "r48")
    origin, clone = os.path.join(base, "origin"), os.path.join(base, "clone")
    os.makedirs(origin)
    env = fx["env"]

    def sh(*cmd):
        rc, out, err = run(list(cmd), env=env)
        assert rc == 0, (cmd, out, err)
        return out.strip()

    sh("git", "init", "-q", origin)
    with open(os.path.join(origin, "a.txt"), "w", encoding="utf-8") as fh:
        fh.write("one\n")
    sh("git", "-C", origin, "add", "a.txt")
    sh("git", "-C", origin, "commit", "-q", "-m", "one")
    sh("git", "-C", origin, "-c", "gpg.format=ssh", "-c", f"user.signingkey={fx['author_key']}.pub", "tag", "-s",
       "v3.0.64", "-m", "signed")
    for name in ("v3.0.65", "v3.0.66"):
        sh("git", "-C", origin, "tag", "-a", name, "-m", "unsigned, on the same commit")
    sh("git", "init", "-q", clone)
    sh("git", "-C", clone, "remote", "add", "origin", "file://" + origin)
    global SIGNING_PRINCIPAL, SIGNING_KEY
    saved = SIGNING_PRINCIPAL, SIGNING_KEY
    SIGNING_PRINCIPAL, SIGNING_KEY = fx["anchor"]["principal"], fx["anchor"]["key"]
    try:
        update_clone(clone, "v3.0.64", repo="file://" + origin)
        at = sh("git", "-C", clone, "rev-parse", "HEAD")

        def tag_at(name):
            return git(clone, "rev-parse", "--verify", "--quiet", f"refs/tags/{name}")[1].strip()

        assert tag_at("v3.0.65") == "", "the update to v3.0.64 brought v3.0.65 along: it fetches the tag asked for alone"
        try:
            update_clone(clone, "v3.0.65", repo="file://" + origin)
            raise AssertionError("v3.0.65, unsigned, was checked out")
        except Refused as exc:
            assert "does not check out" in str(exc), exc
        assert sh("git", "-C", clone, "rev-parse", "HEAD") == at and tag_at("v3.0.65") == "", \
            f"after the refusal HEAD is {sh('git', '-C', clone, 'rev-parse', 'HEAD')[:12]} and v3.0.65 is " \
            f"{tag_at('v3.0.65')[:12] or 'absent'} -- want HEAD {at[:12]} and no v3.0.65"
        sh("git", "-C", clone, "tag", "v3.0.66", at)               # a local v3.0.66 of its own, lightweight
        own = tag_at("v3.0.66")
        try:
            update_clone(clone, "v3.0.66", repo="file://" + origin)
            raise AssertionError("v3.0.66, unsigned, was checked out")
        except Refused as exc:
            assert "does not check out" in str(exc), exc
        assert tag_at("v3.0.66") == own and sh("git", "-C", clone, "rev-parse", "HEAD") == at, \
            f"after the refusal v3.0.66 is {tag_at('v3.0.66')[:12]}, want its own {own[:12]} back"
    finally:
        SIGNING_PRINCIPAL, SIGNING_KEY = saved


def _check_verify_copy_says_which_way_it_failed(fx):
    """#142 (SFH 6): `verify-copy` answers 4 for a copy it could not check -- the release did not answer -- and 3 for one
    that is not as its author signed it. The two shared 3, so the installers sent a person who was offline to
    reinstall a good plugin. Through `main`, its exit code, the release's repository the module's SKILL_REPO."""
    import contextlib
    import io
    good = fx["plugin_copy"]("v3.0.70")
    with open(os.path.join(good, "a.txt"), "a", encoding="utf-8") as fh:
        fh.write("changed\n")
    saved = SKILL_REPO
    said = io.StringIO()
    try:
        answers = {}
        for what, repo in (("offline", "file://" + os.path.join(fx["tmp"], "no-such-release")),
                           ("changed", "file://" + fx["origin"])):
            globals()["SKILL_REPO"] = repo
            with contextlib.redirect_stderr(said), contextlib.redirect_stdout(said):
                answers[what] = main(["verify-copy", "--root", good, "--tag", "v3.0.70"])
    finally:
        globals()["SKILL_REPO"] = saved
    assert answers == {"offline": 4, "changed": 3}, f"verify-copy answered {answers}, want offline 4 and changed 3 -- " \
                                                    f"said {said.getvalue()[-300:]!r}"
    assert "could not check: could not fetch v3.0.70" in said.getvalue(), said.getvalue()[-300:]


def _selftest():
    """Offline, in temporary repositories: a signed tag passes, an unsigned or foreign-signed one is refused, an
    old one predates signing; only the author's SSH signature is good, whatever the git configuration says (the
    `_check_*` functions above); local changes become a patch that brings them back, and only then is the clone
    reset; the clone update lands the tag in refs/tags (describe names it) and refuses a dirty clone; tools are
    updated the way they were installed; pip is asked to upgrade."""
    tmp = tempfile.mkdtemp(prefix="autosound_upkeep_")
    # GNUPGHOME in this temp dir for the whole process, not only in the `env` the checks hand git (#142): whatever runs
    # git with the process's own environment -- update_clone, keep_local, verify_copy, a verify_tag that lost its `env`
    # -- cannot reach the person's ~/.gnupg either. The stub-git check stops the rest when git is not given its `env`,
    # but only where a stand-in `git` can run: on Windows it returns at once. And no global or system git config there
    # either, as in that `env`: Git for Windows' own sets core.autocrlf, and a clone the checks make without it was
    # then reset and patched with it (R33: this selftest runs in the Windows CI job).
    isolated = {"GNUPGHOME": os.path.join(tmp, "gnupg"), "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
    saved = {name: os.environ.get(name) for name in isolated}
    os.environ.update(isolated)
    try:
        return _selftest_in(tmp)
    finally:
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def _selftest_in(tmp):
    """`_selftest`'s checks, in `tmp`, with the process's environment already pointed there."""
    # The `env` the checks hand git: no global or system config, and GNUPGHOME in this temp dir, as the process's.
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
               GIT_COMMITTER_EMAIL="t@t", GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1",
               GNUPGHOME=os.path.join(tmp, "gnupg"))
    env.pop(SKIP_VERIFY_VAR, None)
    os.makedirs(env["GNUPGHOME"], mode=0o700)

    def sh(*cmd, cwd=None):
        rc, out, err = run(list(cmd), cwd=cwd, env=env)
        assert rc == 0, (cmd, out, err)
        return out

    keys = {}
    for who in ("author", "stranger"):
        k = os.path.join(tmp, who)
        sh("ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", who, "-f", k)
        with open(k + ".pub", encoding="utf-8") as fh:
            keys[who] = " ".join(fh.read().split()[:2])
    origin = os.path.join(tmp, "origin")
    os.makedirs(origin)
    sh("git", "init", "-q", "-b", "main", origin)
    with open(os.path.join(origin, "a.txt"), "w", encoding="utf-8") as fh:
        fh.write("one\n")
    sh("git", "-C", origin, "add", "a.txt")
    sh("git", "-C", origin, "commit", "-q", "-m", "one")
    sh("git", "-C", origin, "tag", "-a", "v3.0.10", "-m", "old, before signing")
    with open(os.path.join(origin, "a.txt"), "a", encoding="utf-8") as fh:
        fh.write("two\n")
    sh("git", "-C", origin, "commit", "-q", "-am", "two")
    signed = ("git", "-C", origin, "-c", "gpg.format=ssh")
    sh(*signed, "-c", f"user.signingkey={os.path.join(tmp, 'author')}.pub", "tag", "-s", "v3.0.64", "-m", "signed")
    sh(*signed, "-c", f"user.signingkey={os.path.join(tmp, 'stranger')}.pub", "tag", "-s", "v3.0.65", "-m", "foreign")
    sh("git", "-C", origin, "tag", "-a", "v3.0.66", "-m", "unsigned")
    anchor = {"principal": "author", "key": keys["author"]}
    ok, said = verify_tag(origin, "v3.0.64", env=env, **anchor)
    assert ok and "signature good" in said, said
    for tag in ("v3.0.65", "v3.0.66"):
        ok, said = verify_tag(origin, tag, env=env, **anchor)
        assert not ok and "does not check out" in said, (tag, said)
    ok, said = verify_tag(origin, "v3.0.10", env=env, **anchor)
    assert ok and "predates signed tags" in said, said
    ok, said = verify_tag(origin, "v3.0.66", env=dict(env, **{SKIP_VERIFY_VAR: "1"}), **anchor)
    assert ok and "NOT checked" in said, said
    assert newest_tag(origin) == "v3.0.66", newest_tag(origin)
    # T-35 (#142): a signature is the author's or nothing, whatever the person's git or GPG configuration says. The
    # stub-git check runs first, and the rest only once it passed: it is the one that sees a verify_tag no longer
    # handing git its `env` -- and then the OpenPGP check would give a PGP block to the person's own gpg, which finds
    # only this process's temporary GNUPGHOME (above), on Windows too, where this check returns at once.
    fx = _signature_fixture(tmp, env, anchor, os.path.join(tmp, "author"))
    failures, skipped = [], []
    for check in (_check_a_git_that_says_good_is_not_believed, _check_a_signing_helper_is_not_asked,
                  _check_an_openpgp_good_is_not_the_authors, _check_a_min_trust_level_is_not_the_persons):
        try:
            if check(fx) == "skipped":
                skipped.append(check)
        except AssertionError as exc:
            failures.append(f"{check.__name__}: {exc}")
            if check is _check_a_git_that_says_good_is_not_believed:
                failures.append("the other signature checks were not run: git may not be getting their env, and the "
                                "OpenPGP one would then reach the person's own gpg")
                break
    assert not failures, "\n".join(failures)

    # The clone, as the installer makes it: shallow, at a tag.
    clone = os.path.join(tmp, "clone")
    sh("git", "-c", "advice.detachedHead=false", "clone", "-q", "--branch", "v3.0.10", "--depth", "1",
       "file://" + origin, clone)
    with open(os.path.join(clone, "a.txt"), "a", encoding="utf-8") as fh:
        fh.write("a session's patch\n")
    with open(os.path.join(clone, "new.py"), "w", encoding="utf-8") as fh:
        fh.write("print('added by hand')\n")
    global SIGNING_PRINCIPAL, SIGNING_KEY
    saved = SIGNING_PRINCIPAL, SIGNING_KEY
    SIGNING_PRINCIPAL, SIGNING_KEY = anchor["principal"], anchor["key"]
    os.environ.pop(SKIP_VERIFY_VAR, None)
    try:
        try:
            update_clone(clone, "v3.0.64", repo="file://" + origin)
            raise AssertionError("a clone with local changes must be refused, not updated over")
        except Refused as exc:
            assert "keep-local" in str(exc) and "a.txt" in str(exc), exc
        posted = []
        got = keep_local(clone, send=True, out_dir=os.path.join(tmp, "kept"),
                         poster=lambda body, title: (posted.append((body, title)), {"sent": True, "url": "u"})[1],
                         now=datetime.datetime(2026, 9, 29, 12, 0, 0))
        assert sorted(got["changed"]) == ["a.txt", "new.py"] and got["reset"], got
        assert changed_files(clone) == [] and not os.path.exists(os.path.join(clone, "new.py")), "reset"
        assert got["patch"].endswith("20260929-120000-v3.0.10.patch"), got["patch"]
        assert posted and "a.txt" in posted[0][1] and "v3.0.10" in posted[0][1], posted
        with open(posted[0][0], encoding="utf-8") as fh:
            body = fh.read()
        assert "a session's patch" in body and "`new.py`" in body, body
        sh("git", "-C", clone, "apply", got["patch"])
        assert sorted(changed_files(clone)) == ["a.txt", "new.py"], "the patch brings every change back"
        keep_local(clone, out_dir=os.path.join(tmp, "kept"))
        assert keep_local(clone, out_dir=os.path.join(tmp, "kept"))["changed"] == []
        # The update: the tag lands in refs/tags, so `describe` names it (#92); the signature is checked (#99).
        moved = update_clone(clone, "v3.0.64", repo="file://" + origin)
        assert moved["to"] == "v3.0.64" and "signature good" in moved["signature"], moved
        # A refused update leaves HEAD and refs/tags as they were (R48, #142) -- asked of HEAD's commit and the tag,
        # not of `describe`, which picks among v3.0.64/65/66 on one commit by tagger date (Windows CI 37858572763).
        landed = git(clone, "rev-parse", "HEAD")[1].strip()
        for bad in ("v3.0.65", "v3.0.66"):
            try:
                update_clone(clone, bad, repo="file://" + origin)
                raise AssertionError(f"{bad} must not be checked out")
            except Refused as exc:
                left = git(clone, "rev-parse", "--verify", "--quiet", f"refs/tags/{bad}")[1].strip()
                assert "does not check out" in str(exc) and git(clone, "rev-parse", "HEAD")[1].strip() == landed \
                    and not left, (exc, landed, left)

        # W-6 #121: a plugin copy (no .git) against its signed tag, file by file. Two more releases in the origin:
        # v3.0.70 signed by the author, v3.0.71 unsigned, each naming itself in .claude-plugin/plugin.json.
        os.makedirs(os.path.join(origin, ".claude-plugin"), exist_ok=True)
        for version, how in (("3.0.70", "signed"), ("3.0.71", "unsigned")):
            with open(os.path.join(origin, ".claude-plugin", "plugin.json"), "w", encoding="utf-8") as fh:
                json.dump({"name": "autosound-tuning", "version": version}, fh)
            sh("git", "-C", origin, "add", "-A")
            sh("git", "-C", origin, "commit", "-q", "-m", version)
            if how == "signed":
                sh(*signed, "-c", f"user.signingkey={os.path.join(tmp, 'author')}.pub", "tag", "-s", f"v{version}", "-m", version)
            else:
                sh("git", "-C", origin, "tag", "-a", f"v{version}", "-m", version)

        def plugin_copy(tag):
            dest = os.path.join(tmp, "plugin-" + tag)
            shutil.rmtree(dest, ignore_errors=True)
            os.makedirs(dest)
            tar = os.path.join(tmp, tag + ".tar")
            sh("git", "-C", origin, "archive", "-o", tar, tag)
            sh("tar", "-xf", tar, "-C", dest)
            return dest

        plug = plugin_copy("v3.0.70")
        got = verify_copy(plug, repo="file://" + origin)
        assert got["tag"] == "v3.0.70" and got["files"] == 2 and "signature good" in got["signature"], got
        os.makedirs(os.path.join(plug, "__pycache__"))
        for noise in (".in_use", os.path.join("__pycache__", "x.cpython-312.pyc")):
            open(os.path.join(plug, noise), "w").close()
        win = plugin_copy("v3.0.70")                         # Windows: `.in_use` is a folder with a file per process
        os.makedirs(os.path.join(win, ".in_use"))
        open(os.path.join(win, ".in_use", "4368"), "w").close()
        assert verify_copy(win, repo="file://" + origin)["files"] == 2, "the .in_use folder is a marker, not a file"
        with open(os.path.join(plug, "a.txt"), "wb") as fh:
            fh.write(b"one\r\ntwo\r\n")                      # a Windows checkout's line endings: the same file
        assert verify_copy(plug, repo="file://" + origin)["files"] == 2
        for harm, word in (("changed", "1 changed: a.txt"), ("added", "1 not in the release: evil.py"),
                           ("missing", "1 missing: a.txt")):
            plug = plugin_copy("v3.0.70")
            if harm == "changed":
                with open(os.path.join(plug, "a.txt"), "a", encoding="utf-8") as fh:
                    fh.write("injected\n")
            elif harm == "added":
                open(os.path.join(plug, "evil.py"), "w").close()
            else:
                os.remove(os.path.join(plug, "a.txt"))
            try:
                verify_copy(plug, repo="file://" + origin)
                raise AssertionError(f"a copy with a file {harm} passed")
            except Refused as exc:
                assert word in str(exc) and "Reinstall" in str(exc), (harm, exc)
        # A candidate before its release (W-6 rc1): the copy names 3.0.72, only beta-v3.0.72-rc1 exists, signed.
        with open(os.path.join(origin, ".claude-plugin", "plugin.json"), "w", encoding="utf-8") as fh:
            json.dump({"name": "autosound-tuning", "version": "3.0.72"}, fh)
        sh("git", "-C", origin, "commit", "-q", "-am", "3.0.72 rc1")
        sh(*signed, "-c", f"user.signingkey={os.path.join(tmp, 'author')}.pub", "tag", "-s", "beta-v3.0.72-rc1", "-m", "rc1")
        cand = plugin_copy("beta-v3.0.72-rc1")
        assert copy_tag(cand, repo="file://" + origin) == "beta-v3.0.72-rc1"
        got = verify_copy(cand, repo="file://" + origin)
        assert got["tag"] == "beta-v3.0.72-rc1" and "signature good" in got["signature"], got
        assert release_key("beta-v3.0.72-rc1") == (3, 0, 72) == release_key("v3.0.72") and release_key("v3.x") is None
        try:
            verify_copy(plugin_copy("v3.0.71"), repo="file://" + origin)
            raise AssertionError("an unsigned release passed")
        except Refused as exc:
            assert "does not check out" in str(exc), exc
        ready = os.path.join(tmp, "plugin-ready")
        for _ in range(2):
            assert plugin_ready(plugin_copy("v3.0.70"), path=ready)["version"] == "v3.0.70"
        assert open(ready, encoding="utf-8").read() == "v3.0.70\n", "one line per version, written once"
        # #142: verify-copy's two ways to fail, and a refused update's refs/tags (R48).
        fx2 = {"tmp": tmp, "env": env, "anchor": anchor, "author_key": os.path.join(tmp, "author"), "origin": origin,
               "plugin_copy": plugin_copy}
        failures = []
        for check in (_check_verify_copy_says_which_way_it_failed, _check_a_refused_update_leaves_the_tags_as_they_were):
            try:
                check(fx2)
            except AssertionError as exc:
                failures.append(f"{check.__name__}: {exc}")
        assert not failures, "\n".join(failures)
    finally:
        SIGNING_PRINCIPAL, SIGNING_KEY = saved
    # T-39 (#142): the ready file byte for byte, and the SessionStart hook that reads it -- on every platform a bash
    # runs, Windows' Git Bash included (the hook's checks, POSIX only until now, are in the second); a hook gone missing
    # fails that check, and the ready file is the one the hook reads, whatever HOME and USERPROFILE say.
    failures = []
    for check in (_check_plugin_ready_writes_its_line_byte_for_byte, _check_the_hook_is_silent_once_set_up,
                  _check_a_missing_hook_fails_the_hook_check, _check_the_ready_file_is_where_the_hook_looks):
        try:
            check(tmp)
        except AssertionError as exc:
            failures.append(f"{check.__name__}: {exc}")
    assert not failures, "\n".join(failures)

    # Tools: the way each was installed decides the command; a tool that is not here is not added.
    brew_omp = "/opt/homebrew/Cellar/omp/17.2.9/bin/omp"
    assert how_installed("omp", brew_omp) == ("brew", "omp")
    assert how_installed("agy", "/opt/homebrew/Caskroom/antigravity-cli/1.1.12/agy") == ("brew-cask", "antigravity-cli")
    assert how_installed("claude", "/opt/homebrew/lib/node_modules/@anthropic-ai/claude-code/bin/claude.exe")[0] == "npm"
    assert how_installed("agy", os.path.join(tmp, "agy")) == ("self", "agy")
    assert how_installed("gh", os.path.join(LOCAL_BIN, "gh")) == ("release", "cli/cli")
    assert how_installed("gh", "/usr/bin/gh") == ("other", "gh") and update_command("gh", "/usr/bin/gh", "other", "gh") is None
    assert update_command("omp", brew_omp, "brew", "omp")[1:] == ["upgrade", "omp"]
    assert update_command("agy", "/x/agy", "self", "agy") == ["/x/agy", "update"]
    bindir = os.path.join(tmp, "bin")
    os.makedirs(bindir)
    for name, ver in (("omp", "17.2.9"), ("agy", "1.2.12")):
        path = os.path.join(bindir, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(f"#!/bin/sh\necho '{name}/{ver}'\n")
        os.chmod(path, 0o755)
    fake_env = {"PATH": bindir}
    calls = []

    def fake(cmd, timeout=None, **kw):
        calls.append(cmd)
        if cmd[1:] == ["update", "--check"]:
            return 0, "Current version: 17.2.9\nNew version available: 18.4.3\n", ""
        return (0, "", "") if os.path.basename(cmd[0]) == "omp" else (1, "", "agy: update server unreachable\n")

    fetched = []

    def fake_fetch(url, timeout=20):
        fetched.append(url)
        if "/manifests/" in url:
            return {"version": "1.2.15", "url": "https://x/agy", "sha512": "0" * 128}
        if "dist-tags" in url:
            return {"stable": "2.1.285", "latest": "2.1.288", "next": "2.1.288"}
        return None

    # The fake tools are shell scripts, and `tool_version` starts each one: Windows cannot start a shell script, so this
    # part, and the update below, run on POSIX only -- said in a line there, and left out of the OK line.
    tools_here = os.name != "nt"
    if not tools_here:
        print("upkeep: the tools' rows and their update were not checked here -- the fake tools are shell scripts, "
              "which Windows cannot start")
    if tools_here:
        rows = tool_rows(env=fake_env, runner=fake, fetch=fake_fetch)
        assert [r["name"] for r in rows] == ["omp", "agy"], "claude and gh are not here: not listed, not added"
        omp = rows[0]
        assert omp["installed"] == "17.2.9" and omp["available"] == "18.4.3" and omp["how"] == "self", omp
        # W-6 #126 (hub #237): a self-installed agy reads its update server's manifest for this platform, a native
        # Claude Code the npm dist-tag of its own channel; no answer is "" as before, never an exception.
        assert rows[1]["available"] == "1.2.15" and fetched and "/manifests/" in fetched[0], (rows[1], fetched)
    assert agy_platform("darwin", "arm64") == "darwin_arm64" and agy_platform("win32", "AMD64") == "windows_amd64"
    assert agy_platform("linux", "aarch64").startswith("linux_arm64") and agy_platform("sunos5", "sparc") == ""
    with tempfile.TemporaryDirectory() as fake_home:
        assert available_version("claude", "/x/claude", "self", "@anthropic-ai/claude-code", fetch=fake_fetch,
                                 home=fake_home) == "2.1.288", "no settings: the latest channel"
        os.makedirs(os.path.join(fake_home, ".claude"))
        with open(os.path.join(fake_home, ".claude", "settings.json"), "w", encoding="utf-8") as fh:
            json.dump({"autoUpdatesChannel": "stable"}, fh)
        assert claude_channel(fake_home) == "stable"
        assert available_version("claude", "/x/claude", "self", "@anthropic-ai/claude-code", fetch=fake_fetch,
                                 home=fake_home) == "2.1.285", "the stable channel's newest"
    assert available_version("agy", "/x/agy", "self", "agy", fetch=lambda url, timeout=20: None) == ""
    assert available_version("claude", "/x/claude", "self", "c", fetch=lambda url, timeout=20: {"latest": "oops"}) == ""
    if tools_here:           # the fake tools again (above): shell scripts, which Windows cannot start
        calls.clear()
        done = update_tools(env=fake_env, runner=fake)
        assert [c[1:] for c in calls] == [["update"], ["update"]], calls
        assert done[0]["ok"] and not done[1]["ok"] and "unreachable" in done[1]["why"], done
        only = update_tools(only=["omp"], env=fake_env, runner=fake)
        assert [t["name"] for t in only] == ["omp"], only

    # Libraries: pip is asked to UPGRADE, with the installers' flags.
    assert pip_command("py", "r.txt", in_venv=True)[-3:] == ["--disable-pip-version-check", "-r", "r.txt"]
    assert "--upgrade" in pip_command("py", "r.txt") and "--user" in pip_command("py", "r.txt", platform="darwin")
    assert "--break-system-packages" in pip_command("py", "r.txt", platform="win32")
    assert "--break-system-packages" not in pip_command("py", "r.txt", platform="darwin")
    got = update_libs("py", "r.txt", runner=lambda cmd, timeout=None: (0, "False\n", ""))
    assert got["ok"] and "--upgrade" in got["command"] and "--user" in got["command"], got
    shutil.rmtree(tmp, ignore_errors=True)
    # The OK line names only what ran (#142): on Windows the stand-in git is a shell script no child can start.
    good_says = ("a git that says Good" if _check_a_git_that_says_good_is_not_believed not in skipped
                 else "a git that says Good: NOT checked here, Windows starts no shell script")
    print("selftest[upkeep] OK -- a signed tag passes, an unsigned or foreign-signed one is refused, one before "
          f"{SIGNED_FROM} predates signing, the developer's switch says so; only the author's SSH signature is good, "
          f"whatever the git config says (a signing helper, an OpenPGP Good, the author's sentence as an OpenPGP user "
          f"id, {good_says}, a minimum trust level); local changes "
          "(new files too) become a "
          "patch that brings them back, sent only when asked, and only then is the clone reset; the update lands "
          "the tag in refs/tags and refuses a dirty clone or a bad signature, leaving HEAD and refs/tags as they were; "
          "verify-copy answers 4 for a copy it could not check and 3 for one not as signed; the ready file is one "
          "line, \\n-ended, where the hook looks, and the SessionStart hook is silent once it is written; "
          + ("each tool is updated the way it was installed and a missing one is not added; " if tools_here else "")
          + "pip is asked to upgrade with the installers' flags")
    return 0


if __name__ == "__main__":
    try:
        sys.path.insert(0, os.path.join(SKILL_DIR, "rew_tool"))
        import console
        console.install()
    except Exception:  # noqa: BLE001 -- the fallback is cosmetic; the run is not
        pass
    sys.exit(main())
