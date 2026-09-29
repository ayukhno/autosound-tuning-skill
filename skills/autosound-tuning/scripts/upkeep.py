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

TCC runs this from its vendored skill (as new as TCC). The installers run the copy inside the tag they are about
to check out (`git show FETCH_HEAD:<this file>`), so a clone that predates this script is not in the way.

stdlib only, py3.9+. Exit codes: 0 done · 2 usage · 3 refused (a dirty clone, a signature, a failed step).
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

_TAG_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")


class Refused(Exception):
    """A step that must not go ahead, with the sentence that says why and what to do."""


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


def tag_key(tag):
    m = _TAG_RE.match(tag or "")
    return tuple(int(x) for x in m.groups()) if m else None


def newest_tag(repo=SKILL_REPO, glob=SKILL_TAG_GLOB):
    """The newest `v3.x.y` on the remote, or "" when it cannot be asked (the installers' ls-remote)."""
    rc, out, _ = run(["git", "ls-remote", "--tags", "--refs", repo, glob], timeout=60)
    tags = [line.rsplit("/", 1)[-1] for line in out.splitlines() if rc == 0 and "refs/tags/" in line]
    tags = [t for t in tags if tag_key(t)]
    return max(tags, key=tag_key) if tags else ""


def verify_tag(clone, tag, principal=None, key=None, signed_from=None, env=None):
    """`(ok, sentence)`. ok is True for a good signature, and for a tag that predates signing (the sentence says
    which); False for anything else at or after `signed_from`. The switch skips it, visibly."""
    env = os.environ if env is None else env
    principal, key = principal or SIGNING_PRINCIPAL, key or SIGNING_KEY
    signed_from = signed_from or SIGNED_FROM
    if env.get(SKIP_VERIFY_VAR) == "1":
        return True, f"signature NOT checked: {SKIP_VERIFY_VAR}=1 is set (a developer's switch)"
    if tag_key(tag) is None:
        return False, f"{tag!r} is not a release tag (vX.Y.Z), so there is no signature to check"
    if tag_key(tag) < tag_key(signed_from):
        return True, f"{tag} predates signed tags (they start at {signed_from}): installed without a signature check"
    with tempfile.TemporaryDirectory(prefix="autosound_signers_") as tmp:
        signers = os.path.join(tmp, "allowed_signers")
        with open(signers, "w", encoding="utf-8") as fh:
            fh.write(f'{principal} namespaces="git" {key}\n')
        rc, out, err = git(clone, "-c", "gpg.format=ssh", "-c", f"gpg.ssh.allowedSignersFile={signers}",
                           "verify-tag", tag)
    said = (err or out).strip()
    if rc == 0 and "Good" in said:
        return True, f"{tag}: signature good ({principal})"
    reason = said.splitlines()[-1].rstrip(".") if said else f"git verify-tag exit {rc}"
    return False, (f"{tag}: the signature does not check out -- {reason}. Not installed: a release tag of this "
                   f"skill is signed by its author, and this one is not, or not by that key")


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
    signature verified (#99), checked out. A clone with local changes is refused, naming `keep-local`."""
    files = changed_files(clone)
    if files:
        raise Refused(f"{clone} has local changes ({', '.join(files[:5])}{' …' if len(files) > 5 else ''}); "
                      f"`upkeep.py keep-local` keeps them as a patch and resets the clone, then run this again")
    was = describe(clone)
    tag = tag or newest_tag(repo or SKILL_REPO)
    if not tag:
        raise Refused("the newest release could not be asked for (no network?); nothing was changed")
    rc, _, err = git(clone, "fetch", "--quiet", "--depth", "1", repo or "origin", f"+refs/tags/{tag}:refs/tags/{tag}",
                     timeout=300)
    if rc != 0:
        raise Refused(f"could not fetch {tag}: {err.strip()}; nothing was changed")
    ok, said = verify_tag(clone, tag)
    if not ok:
        raise Refused(said + "; nothing was changed")
    rc, _, err = git(clone, "-c", "advice.detachedHead=false", "checkout", "--quiet", f"refs/tags/{tag}^{{commit}}")
    if rc != 0:
        raise Refused(f"could not check out {tag}: {err.strip()}")
    return {"clone": clone, "from": was, "to": describe(clone), "signature": said}


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


def available_version(name, path, how, package, runner=run):
    """What the tool's source offers now, or "" when it cannot say without installing (agy, a native Claude)."""
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


def tool_rows(env=None, runner=run, ask_available=True):
    rows = []
    for name in TOOLS:
        path = locate(name, env)
        if not path:
            continue                       # never installed here: nothing is added (#97 ask 1)
        how, package = how_installed(name, path)
        rows.append({"name": name, "path": path, "how": how, "package": package,
                     "installed": tool_version(path),
                     "available": available_version(name, path, how, package, runner) if ask_available else "",
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
        else:
            got = update_libs()
    except Refused as exc:
        if args.json:
            print(json.dumps({"ok": False, "refused": str(exc)}, ensure_ascii=False))
        else:
            print(f"refused: {exc}", file=sys.stderr)
        return 3
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
def _selftest():
    """Offline, in temporary repositories: a signed tag passes, an unsigned or foreign-signed one is refused, an
    old one predates signing; local changes become a patch that brings them back, and only then is the clone
    reset; the clone update lands the tag in refs/tags (describe names it) and refuses a dirty clone; tools are
    updated the way they were installed; pip is asked to upgrade."""
    tmp = tempfile.mkdtemp(prefix="autosound_upkeep_")
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
               GIT_COMMITTER_EMAIL="t@t", GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
    env.pop(SKIP_VERIFY_VAR, None)

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
        for bad in ("v3.0.65", "v3.0.66"):
            try:
                update_clone(clone, bad, repo="file://" + origin)
                raise AssertionError(f"{bad} must not be checked out")
            except Refused as exc:
                assert "does not check out" in str(exc) and describe(clone) == "v3.0.64", (exc, describe(clone))
    finally:
        SIGNING_PRINCIPAL, SIGNING_KEY = saved

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

    rows = tool_rows(env=fake_env, runner=fake)
    assert [r["name"] for r in rows] == ["omp", "agy"], "claude and gh are not here: not listed, not added"
    omp = rows[0]
    assert omp["installed"] == "17.2.9" and omp["available"] == "18.4.3" and omp["how"] == "self", omp
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
    print("selftest[upkeep] OK -- a signed tag passes, an unsigned or foreign-signed one is refused, one before "
          f"{SIGNED_FROM} predates signing, the developer's switch says so; local changes (new files too) become a "
          "patch that brings them back, sent only when asked, and only then is the clone reset; the update lands "
          "the tag in refs/tags and refuses a dirty clone or a bad signature; each tool is updated the way it was "
          "installed and a missing one is not added; pip is asked to upgrade with the installers' flags")
    return 0


if __name__ == "__main__":
    try:
        sys.path.insert(0, os.path.join(SKILL_DIR, "rew_tool"))
        import console
        console.install()
    except Exception:  # noqa: BLE001 -- the fallback is cosmetic; the run is not
        pass
    sys.exit(main())
