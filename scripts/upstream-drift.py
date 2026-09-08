#!/usr/bin/env python3
"""Has the upstream a port was taken from moved since the port was made?

Every port of somebody else's maths into `rew_tool` carries a header block (the user's ruling,
2026-08-24: "портуємо і будемо слідкувати за змінами"):

    # upstream: OWNER/REPO path/in/their/tree.cs @ <sha> (MIT) -- <symbols ported>
    # format-version: <N> -- <why>          (only on a port of a FILE FORMAT; optional)
    # deviation: <what we did differently> -- see <where in our code>

This script reads those headers and answers, per port, whether `path` has changed in the upstream
since `<sha>`. It says WHICH commits touched the file, so the reader can go and look — it does not
say whether the change matters, because that needs a person who understands both sides.

**A port of a file format pins the format's version as a number, and that number is checked, not
the commit list.** `# format-version: N` says which `CurrentVersion` the reader was written for;
the checker reads `const int CurrentVersion = M` out of the upstream file at `ref` and names
`M != N` as a drift of the FORMAT — whatever the commit list says, and however many commits
merely touched the file for other reasons. Four session versions in three weeks (v7 → v10,
2026-08-22 .. 09-05) is the pace that made this a mechanism rather than a note in a reference
(hub RES-008): a reader pinned to v7 refused every file the current app wrote, correctly, and
nothing named the gap until somebody read the upstream by hand.

**A `# deviation:` line is where the checker looks before calling a difference a drift.** An
unlisted difference between our port and the upstream is a drift (theirs moved, or ours did); a
listed one is ours, on purpose, and the line says why. Recording a deviation somewhere other than
the header — a docstring a screen below, say — is a deviation this script cannot see, and one that
the next person will "fix back" (the cockpit's catch, the day the header format was set).

Two ways to reach the upstream, tried in this order:

  * a local clone (`--fork DIR`, or `$AUTOSOUND_UPSTREAM_CLONE`): `git log <sha>..origin/main --
    <path>`, after `git fetch` when `--fetch` is given — the clone is usually a fork, and a fork's
    `main` is not the upstream's until fetched;
  * the GitHub compare API through `gh` (`repos/OWNER/REPO/compare/<sha>...HEAD`) — no clone
    needed, sixty anonymous calls an hour.

Exit 0 when every port is current, **2 when any has drifted** (a distinct code, so a CI step can
warn without failing), 1 when a header cannot be read or the upstream cannot be reached.
`--selftest` builds a throwaway git repository and needs no network.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
PORT_ROOTS = [os.path.join(REPO, "skills", "autosound-tuning", "rew_tool")]

UPSTREAM_RE = re.compile(
    r"^#\s*upstream:\s*(?P<repo>[\w.-]+/[\w.-]+)\s+(?P<path>\S+)\s+@\s+(?P<sha>[0-9a-fA-F]{7,40})")
DEVIATION_RE = re.compile(r"^#\s*deviation:\s*(?P<text>.+)$")
FORMAT_VERSION_RE = re.compile(r"^#\s*format-version:\s*(?P<n>\d+)")
CONTINUATION_RE = re.compile(r"^#\s{4,}(?P<text>\S.*)$")
# What the upstream's file says its writer produces. C# today; a second language gets a second
# pattern here, not a second script.
CURRENT_VERSION_RE = re.compile(r"\bconst\s+int\s+CurrentVersion\s*=\s*(?P<n>\d+)\s*;")


def find_headers(roots):
    """Every `# upstream:` block under `roots`: [{file, line, repo, path, sha, deviations}]."""
    out = []
    for root in roots:
        for dirpath, _, names in os.walk(root):
            for name in sorted(names):
                if not name.endswith(".py"):
                    continue
                fp = os.path.join(dirpath, name)
                with open(fp, encoding="utf-8") as fh:
                    lines = fh.read().splitlines()
                i = 0
                while i < len(lines):
                    m = UPSTREAM_RE.match(lines[i])
                    if not m:
                        i += 1
                        continue
                    entry = {"file": os.path.relpath(fp, REPO), "line": i + 1,
                             "repo": m["repo"], "path": m["path"], "sha": m["sha"].lower(),
                             "deviations": [], "format_version": None}
                    # The block runs while the lines are comments; deviations may wrap onto
                    # indented continuation lines.
                    j = i + 1
                    # ...and stops at the next `# upstream:` line: two ports declared back to back
                    # with no code between them are two blocks, not one with a swallowed header.
                    while j < len(lines) and lines[j].startswith("#") and not UPSTREAM_RE.match(lines[j]):
                        d = DEVIATION_RE.match(lines[j])
                        v = FORMAT_VERSION_RE.match(lines[j])
                        c = CONTINUATION_RE.match(lines[j])
                        if d:
                            entry["deviations"].append(d["text"].strip())
                        elif v:
                            entry["format_version"] = int(v["n"])
                        elif c and entry["deviations"]:
                            entry["deviations"][-1] += " " + c["text"].strip()
                        j += 1
                    out.append(entry)
                    i = j
    return out


def _git(clone, *args):
    r = subprocess.run(["git", "-C", clone, *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or f"git {' '.join(args)} failed")
    return r.stdout


def drift_via_clone(entry, clone, ref="origin/main"):
    """Commits on `ref` since `sha` that touch `path`, from a local clone."""
    try:
        _git(clone, "cat-file", "-e", f"{entry['sha']}^{{commit}}")
    except RuntimeError:
        return {"error": f"{entry['sha']} is not in the clone {clone} (fetch it, or the sha is wrong)"}
    log = _git(clone, "log", "--oneline", f"{entry['sha']}..{ref}", "--", entry["path"]).strip()
    commits = [l for l in log.splitlines() if l.strip()]
    head = _git(clone, "rev-parse", "--short", ref).strip()
    out = {"via": f"clone {clone} @ {ref} ({head})", "commits": commits}
    if entry.get("format_version") is not None:
        try:
            text = _git(clone, "show", f"{ref}:{entry['path']}")
        except RuntimeError as exc:
            return {"error": f"cannot read {entry['path']} at {ref}: {exc}"}
        out.update(_format_check(entry, text))
    return out


def _format_check(entry, upstream_text):
    """The upstream writer's version against the header's pin. A file that carries a pin but
    whose upstream states no `CurrentVersion` is an error, not a pass: the pin would be checked
    against nothing, which is the shape of check this whole script exists to refuse."""
    m = CURRENT_VERSION_RE.search(upstream_text)
    if not m:
        return {"error": f"format-version pinned at {entry['format_version']}, but "
                         f"{entry['path']} states no `const int CurrentVersion`"}
    theirs = int(m["n"])
    return {"upstream_format_version": theirs,
            "format_drift": theirs != entry["format_version"]}


def drift_via_api(entry):
    """Commits since `sha` that touch `path`, through `gh api …/compare/<sha>...HEAD`."""
    r = subprocess.run(["gh", "api", f"repos/{entry['repo']}/compare/{entry['sha']}...HEAD"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return {"error": f"gh api failed: {r.stderr.strip()[:160]}"}
    data = json.loads(r.stdout)
    touched = any(f.get("filename") == entry["path"] for f in data.get("files", []))
    commits = []
    if touched:
        # The compare payload lists commits but not per-commit files; ask per commit only when
        # the file is touched at all, so a clean port costs one call.
        for c in data.get("commits", []):
            sha = c["sha"]
            rr = subprocess.run(["gh", "api", f"repos/{entry['repo']}/commits/{sha}"],
                                capture_output=True, text=True)
            if rr.returncode == 0:
                cd = json.loads(rr.stdout)
                if any(f.get("filename") == entry["path"] for f in cd.get("files", [])):
                    commits.append(f"{sha[:7]} {cd['commit']['message'].splitlines()[0][:70]}")
    out = {"via": f"GitHub API, {data.get('ahead_by', '?')} commits ahead of {entry['sha']}",
           "commits": commits}
    if entry.get("format_version") is not None:
        rr = subprocess.run(["gh", "api", f"repos/{entry['repo']}/contents/{entry['path']}"],
                            capture_output=True, text=True)
        if rr.returncode != 0:
            return {"error": f"gh api contents failed: {rr.stderr.strip()[:160]}"}
        import base64
        text = base64.b64decode(json.loads(rr.stdout).get("content", "")).decode("utf-8", "replace")
        out.update(_format_check(entry, text))
    return out


def check(entries, clone=None, ref="origin/main", fetch=False):
    if clone and fetch:
        _git(clone, "fetch", "-q", ref.split("/")[0] if "/" in ref else "origin")
    results = []
    for e in entries:
        res = drift_via_clone(e, clone, ref) if clone else drift_via_api(e)
        results.append(dict(e, **res))
    return results


def render(results):
    lines = []
    for r in results:
        where = f"{r['file']}:{r['line']}"
        if "error" in r:
            lines.append(f"  ?    {where}  {r['repo']} {r['path']} @ {r['sha']}: {r['error']}")
        elif r.get("format_drift"):
            lines.append(f"  FORMAT {where}  {r['repo']} {r['path']}: the upstream writer is at "
                         f"version {r['upstream_format_version']}, this reader is pinned at "
                         f"{r['format_version']} ({r['via']}) -- files it writes now will be "
                         f"refused by their number until the reader is taught")
            for c in r["commits"]:
                lines.append(f"           {c}")
        elif r["commits"]:
            lines.append(f"  DRIFT {where}  {r['repo']} {r['path']} has moved since {r['sha']} "
                         f"({len(r['commits'])} commit(s), {r['via']}):")
            for c in r["commits"]:
                lines.append(f"           {c}")
        else:
            lines.append(f"  ok   {where}  {r['repo']} {r['path']} unchanged since {r['sha']} ({r['via']})")
        if r.get("format_version") is not None and not r.get("format_drift") and "error" not in r:
            lines.append(f"         format-version {r['format_version']} = the upstream writer's "
                         f"CurrentVersion")
        for d in r["deviations"]:
            lines.append(f"         deviation (ours, declared): {d}")
        if not r["deviations"]:
            lines.append("         no deviations declared -- any difference from upstream is a drift")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--fork", default=os.environ.get("AUTOSOUND_UPSTREAM_CLONE"),
                    help="local clone of the upstream (default $AUTOSOUND_UPSTREAM_CLONE); "
                         "without one the GitHub API is used through gh")
    ap.add_argument("--ref", default="origin/main", help="the upstream ref in the clone")
    ap.add_argument("--fetch", action="store_true", help="git fetch the clone first")
    ap.add_argument("--root", action="append", default=None, help="directories to scan for ports")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        return _selftest()
    entries = find_headers(args.root or PORT_ROOTS)
    if not entries:
        print("  no `# upstream:` headers found -- nothing is declared as a port")
        return 0
    results = check(entries, clone=args.fork, ref=args.ref, fetch=args.fetch)
    if args.json:
        print(json.dumps(results, indent=1))
    else:
        print(render(results))
    if any("error" in r for r in results):
        return 1
    return 2 if any(r["commits"] or r.get("format_drift") for r in results) else 0


def _selftest():
    """A throwaway upstream: one file, two commits. A port pinned to the first sha must read as
    drifted by exactly that one commit; pinned to the second, as current. Deviations are parsed
    with their continuation lines; a header with no deviation says so."""
    with tempfile.TemporaryDirectory() as tmp:
        up = os.path.join(tmp, "upstream")
        os.makedirs(os.path.join(up, "dsp"))
        subprocess.run(["git", "init", "-q", "-b", "main", up], check=True)
        env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
                   GIT_COMMITTER_EMAIL="t@t")

        def commit(msg):
            subprocess.run(["git", "-C", up, "add", "-A"], check=True, env=env)
            subprocess.run(["git", "-C", up, "commit", "-q", "-m", msg], check=True, env=env)
            return subprocess.run(["git", "-C", up, "rev-parse", "--short", "HEAD"],
                                  capture_output=True, text=True, check=True).stdout.strip()
        with open(os.path.join(up, "dsp", "Metric.cs"), "w") as fh:
            fh.write("v1\n")
        with open(os.path.join(up, "dsp", "Other.cs"), "w") as fh:
            fh.write("o1\n")
        sha1 = commit("first")
        with open(os.path.join(up, "dsp", "Metric.cs"), "w") as fh:
            fh.write("v2\n")
        sha2 = commit("the metric changed")
        with open(os.path.join(up, "dsp", "Other.cs"), "w") as fh:
            fh.write("o2\n")
        commit("something else moved")
        with open(os.path.join(up, "dsp", "Fmt.cs"), "w") as fh:
            fh.write("public const int CurrentVersion = 7;\n")
        sha_fmt7 = commit("a file format at version 7")
        # A clone with the upstream as origin/main, the way a fork checkout looks.
        clone = os.path.join(tmp, "clone")
        subprocess.run(["git", "clone", "-q", up, clone], check=True, env=env)

        ports = os.path.join(tmp, "ports")
        os.makedirs(ports)
        with open(os.path.join(ports, "a.py"), "w") as fh:
            fh.write("x = 1\n"
                     f"# upstream: who/what dsp/Metric.cs @ {sha1} (MIT) -- Metric\n"
                     "# deviation: log weights, not 1/f -- see _w\n"
                     "#            (their 1/f is a log average only on a linear grid).\n"
                     "# deviation: our tie rule -- see align\n"
                     "def f(): pass\n"
                     f"# upstream: who/what dsp/Metric.cs @ {sha2} -- Metric again\n"
                     "y = 2\n"
                     f"# upstream: who/what dsp/Other.cs @ {sha2}\n"
                     f"# upstream: who/what dsp/Fmt.cs @ {sha_fmt7} -- a reader of the format\n"
                     "# format-version: 7 -- their CurrentVersion\n"
                     f"# upstream: who/what dsp/Other.cs @ {sha_fmt7} -- pinned as if a format\n"
                     "# format-version: 1\n")
        entries = find_headers([ports])
        assert [e["sha"] for e in entries] == [sha1, sha2, sha2, sha_fmt7, sha_fmt7], entries
        assert [e["format_version"] for e in entries] == [None, None, None, 7, 1], entries
        assert entries[0]["deviations"] == [
            "log weights, not 1/f -- see _w (their 1/f is a log average only on a linear grid).",
            "our tie rule -- see align"], entries[0]["deviations"]
        assert entries[1]["deviations"] == [] and entries[2]["deviations"] == []
        results = check(entries[:4], clone=clone)
        assert len(results[0]["commits"]) == 1 and "the metric changed" in results[0]["commits"][0], results[0]
        assert results[1]["commits"] == [], results[1]           # pinned to the change itself: current
        assert len(results[2]["commits"]) == 1 and "something else" in results[2]["commits"][0], results[2]
        # The format pin: 7 against a writer at 7 is current and SAYS the number was compared.
        assert results[3]["commits"] == [] and results[3]["format_drift"] is False, results[3]
        assert results[3]["upstream_format_version"] == 7, results[3]
        text = render(results)
        assert "DRIFT" in text and "ok   " in text and "no deviations declared" in text
        assert "format-version 7 = the upstream writer's CurrentVersion" in text, text
        # A pin against a file that states no CurrentVersion is an error, never a pass.
        fmt_on_other = check([entries[4]], clone=clone)
        assert "error" in fmt_on_other[0] and "states no" in fmt_on_other[0]["error"], fmt_on_other
        # The writer moves to 8 and the reader pinned at 7 is named as a FORMAT drift -- even a
        # reader re-pinned to the very commit of the bump, whose commit list is empty.
        with open(os.path.join(up, "dsp", "Fmt.cs"), "w") as fh:
            fh.write("// bumped\npublic const int CurrentVersion = 8;\n")
        sha_fmt8 = commit("the format moved to 8")
        subprocess.run(["git", "-C", clone, "fetch", "-q"], check=True, env=env)
        moved = check([entries[3], dict(entries[3], sha=sha_fmt8)], clone=clone)
        assert moved[0]["format_drift"] and moved[0]["upstream_format_version"] == 8, moved[0]
        assert moved[1]["commits"] == [] and moved[1]["format_drift"], moved[1]
        assert "FORMAT" in render(moved) and "version 8" in render(moved), render(moved)
        assert (2 if any(r["commits"] or r.get("format_drift") for r in moved) else 0) == 2
        # A sha the clone has never seen is an error, not a clean bill.
        bad = check([dict(entries[0], sha="deadbeef")], clone=clone)
        assert "error" in bad[0], bad[0]
        # The exit code is what a CI step reads: 2 = drifted, distinct from 1 = broken.
        rc_drift = 2 if any(r["commits"] for r in results) else 0
        assert rc_drift == 2
    print("selftest[upstream-drift] OK -- headers parsed with wrapped deviations, drift = exactly the "
          "commits that touched the ported file since the pinned sha, a pin at the change reads as "
          "current, an unknown sha is an error, exit 2 on drift; a format-version pin is compared "
          "with the upstream's CurrentVersion (7 = 7 current and said so; 7 vs 8 is a FORMAT drift "
          "even with an empty commit list; a pin on a file with no version is an error).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
