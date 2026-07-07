"""Side-effect class rule — any action that LEAVES THE MACHINE ships as an EXACT command plus a
post-verification, never model-resolved.

Real incident (issue #23): asked to "post the feedback file", a weak generator invented a plausible
target repo via "automatic search" and claimed «успішно опублікував… Issue #21» with a fabricated
URL — while the real feedback belonged elsewhere. Two failures: (a) hallucinated target, (b)
confabulated success. Prose ("post to the right repo") is not a rail; a script that hardcodes the
target and FAILS LOUD on a mismatch is.

The primitive: `guarded_run(argv, verify)` runs an exact argv (a list — never a shell string, never
a model-resolved target), then hands the real output to `verify`. If verify rejects, it raises
`SideEffectRefused` (FAIL LOUD). Generalize this to ANY outbound action: network post, git push,
delete. The concrete `post_feedback` wires it for the GitHub feedback issue with the repo HARDCODED.
"""

import shutil
import subprocess
import urllib.parse

# The feedback destination is HARDCODED here — it is NEVER resolved by a model, a search, or an arg.
FEEDBACK_REPO = "ayukhno/autosound-tuning-skill"
_EXPECTED_PREFIX = f"https://github.com/{FEEDBACK_REPO}/"


class SideEffectRefused(RuntimeError):
    """Raised (FAIL LOUD) when an outbound command's output fails post-verification."""


def _subprocess_runner(argv):
    proc = subprocess.run(argv, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def guarded_run(argv, verify, runner=_subprocess_runner, dry_run=False):
    """Run an EXACT command, then post-verify its output. FAIL LOUD if verify rejects.

    argv    : list of strings — never a shell string, never a model-resolved target.
    verify  : (returncode, stdout, stderr) -> (ok: bool, detail: str).
    runner  : injectable for tests (default = subprocess).
    dry_run : print the exact command and skip execution (returns the argv, does not verify).
    """
    if not isinstance(argv, (list, tuple)) or not all(isinstance(a, str) for a in argv):
        raise ValueError("argv must be a list of strings (no shell string, no interpolation)")
    if dry_run:
        print("DRY-RUN — exact command that WOULD run:\n  " + " ".join(_shq(a) for a in argv))
        return {"dry_run": True, "argv": list(argv)}
    rc, out, err = runner(argv)
    ok, detail = verify(rc, out, err)
    if not ok:
        raise SideEffectRefused(
            "⛔ SIDE-EFFECT REFUSED — output failed post-verification.\n"
            f"  command : {' '.join(_shq(a) for a in argv)}\n"
            f"  reason  : {detail}\n"
            f"  stdout  : {out.strip()[:400]}\n"
            f"  stderr  : {err.strip()[:400]}")
    return {"dry_run": False, "argv": list(argv), "returncode": rc, "stdout": out, "stderr": err,
            "detail": detail}


def _shq(s):
    return s if s and all(c.isalnum() or c in "-_./:=@" for c in s) else "'" + s.replace("'", "'\\''") + "'"


def _extract_url(text):
    """First http(s) URL in gh's output (it prints the created issue URL on success)."""
    for tok in text.split():
        if tok.startswith("http://") or tok.startswith("https://"):
            return tok.strip().rstrip(".,)")
    return None


def verify_feedback_url(rc, out, err):
    """Post-verify: gh succeeded AND the returned URL is on the HARDCODED feedback repo."""
    if rc != 0:
        return False, f"gh exited {rc}"
    url = _extract_url(out) or _extract_url(err)
    if not url:
        return False, "no issue URL in gh output (did it actually post?)"
    # normalize + host/path check — reject a look-alike host or a different repo.
    p = urllib.parse.urlparse(url)
    if p.scheme != "https" or p.netloc != "github.com":
        return False, f"URL host is {p.netloc!r}, expected github.com — refusing ({url})"
    if not url.startswith(_EXPECTED_PREFIX):
        return False, f"URL {url} is NOT on {FEEDBACK_REPO} — refusing (wrong-repo guard)"
    return True, f"verified on {FEEDBACK_REPO}: {url}"


_DEDUP_HOURS = 24.0


def _recent_duplicate(title, runner, hours=_DEDUP_HOURS):
    """URL of an open issue with the EXACT same title created within `hours`, else None.

    A real double-post happened (issues #3/#4, 5 s apart). A list failure returns None —
    never block feedback because the dedup check itself couldn't run.
    """
    import json
    from datetime import datetime, timezone, timedelta
    argv = ["gh", "issue", "list", "--repo", FEEDBACK_REPO, "--state", "open",
            "--search", f'in:title "{title}"',
            "--json", "title,url,createdAt", "--limit", "20"]
    try:
        rc, out, err = runner(argv)
        items = json.loads(out) if rc == 0 and out else []
    except Exception:
        return None
    if not isinstance(items, list):
        return None
    now = datetime.now(timezone.utc)
    for it in items:
        if not isinstance(it, dict) or it.get("title") != title:
            continue
        try:
            created = datetime.fromisoformat(str(it.get("createdAt", "")).replace("Z", "+00:00"))
        except ValueError:
            continue
        if now - created <= timedelta(hours=hours):
            return it.get("url") or f"https://github.com/{FEEDBACK_REPO}/issues"
    return None


def post_feedback(body_file, car, dsp, runner=_subprocess_runner, dry_run=False):
    """Post the de-identified feedback issue with the repo HARDCODED + returned-URL verified.

    Never let a model fill in the repo — that's the whole point. `car`/`dsp` only shape the title.
    Dedup guard: if an identical-title open issue exists newer than 24 h, SKIP loudly instead of
    double-posting (returns {"skipped": True, "duplicate_url": …}).
    """
    import os
    import sys
    if not os.path.isfile(body_file):
        raise ValueError(f"body-file not found: {body_file!r} (write the feedback file first)")
    # Only require the real `gh` binary when we're about to actually shell out to it — an injected
    # runner (tests, smoke_test.py) never touches the filesystem's `gh`, so it must stay installable-
    # and-runnable on a box with no `gh` on PATH (the whole point of dependency injection here).
    if runner is _subprocess_runner and shutil.which("gh") is None and not dry_run:
        raise EnvironmentError("`gh` CLI not found — install/auth it, or use the copy-paste block.")
    title = f"Feedback: {car} · {dsp}"
    if not dry_run:
        dup = _recent_duplicate(title, runner)
        if dup:
            print(f"⛔ SKIP — identical feedback issue already posted (<{_DEDUP_HOURS:.0f}h): {dup}",
                  file=sys.stderr)
            return {"skipped": True, "duplicate_url": dup, "title": title}
    argv = ["gh", "issue", "create", "--repo", FEEDBACK_REPO,
            "--title", title, "--body-file", body_file]
    return guarded_run(argv, verify_feedback_url, runner=runner, dry_run=dry_run)


# ── self-test (no network — the runner is faked) ──────────────────────────────
def _selftest():
    import os, tempfile
    body = os.path.join(tempfile.mkdtemp(), "feedback.md")
    with open(body, "w") as f:
        f.write("# Feedback\nbody\n")

    good = lambda argv: (0, f"https://github.com/{FEEDBACK_REPO}/issues/2\n", "")
    r = post_feedback(body, "VW Passat B8", "Helix DSP Ultra S", runner=good)
    assert r["detail"].startswith("verified on"), r
    # the repo in the actual command is the hardcoded one, not anything a model passed.
    assert r["argv"][:5] == ["gh", "issue", "create", "--repo", FEEDBACK_REPO], r["argv"]

    # dedup guard: identical-title open issue newer than 24 h → SKIP loudly, nothing posted.
    import json as _json
    from datetime import datetime, timezone, timedelta
    def _lister(created_at, then=good):
        def run(argv):
            if argv[1:3] == ["issue", "list"]:
                return (0, _json.dumps([{"title": "Feedback: car · dsp",
                                         "url": f"https://github.com/{FEEDBACK_REPO}/issues/3",
                                         "createdAt": created_at}]), "")
            return then(argv)
        return run
    fresh = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    d1 = post_feedback(body, "car", "dsp", runner=_lister(fresh))
    assert d1.get("skipped") and d1["duplicate_url"].endswith("/issues/3"), d1
    stale = (datetime.now(timezone.utc) - timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M:%SZ")
    d2 = post_feedback(body, "car", "dsp", runner=_lister(stale))
    assert not d2.get("skipped") and d2["detail"].startswith("verified on"), d2
    # a failing list must NOT block the post.
    def _list_broken(argv):
        return (1, "", "boom") if argv[1:3] == ["issue", "list"] else good(argv)
    d3 = post_feedback(body, "car", "dsp", runner=_list_broken)
    assert not d3.get("skipped") and d3["detail"].startswith("verified on"), d3

    # wrong repo (the #23 confabulation) → FAIL LOUD, even though gh "succeeded".
    wrong = lambda argv: (0, "https://github.com/IvanBakhmutov/REW-EQ-CopyPaste-Assistant/issues/21\n", "")
    for bad, why in [
        (wrong, "wrong repo"),
        (lambda a: (0, "Issue created successfully!\n", ""), "confabulated success, no URL"),
        (lambda a: (1, "", "HTTP 404\n"), "gh failed"),
        (lambda a: (0, "https://github.evil.com/ayukhno/autosound-tuning-skill/issues/1\n", ""), "look-alike host"),
    ]:
        try:
            post_feedback(body, "car", "dsp", runner=bad)
            raise AssertionError(f"accepted bad output: {why}")
        except SideEffectRefused:
            pass

    # missing body-file → deterministic refusal before any command runs.
    try:
        post_feedback("/no/such/file.md", "car", "dsp", runner=good)
        raise AssertionError("accepted a missing body-file")
    except ValueError:
        pass

    # dry-run shows the exact command and runs nothing.
    d = post_feedback(body, "car", "dsp", dry_run=True)
    assert d["dry_run"] and d["argv"][4] == FEEDBACK_REPO

    # argv must be a list, never a shell string.
    try:
        guarded_run("gh issue create", verify_feedback_url, runner=good)
        raise AssertionError("accepted a shell string")
    except ValueError:
        pass

    print("selftest OK — verified good post; dedup guard skips a <24h duplicate (stale + broken "
          "list still post); FAIL LOUD on wrong-repo / confabulated-success / gh-failure / "
          "look-alike host; refused missing body-file + shell-string argv; dry-run safe.")
    return 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
