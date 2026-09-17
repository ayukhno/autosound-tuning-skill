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

import platform
import shutil
import subprocess
import urllib.error
import urllib.parse
import urllib.request

# The feedback destinations are HARDCODED here — NEVER resolved by a model, a search, or an arg.
# A caller names a CHANNEL from this closed set; the repo behind the name is not the caller's.
# Two, because a finding has two owners: the method (the skill) and the front-end (TCC). With one
# route, a TCC finding had nowhere to go — the model refused, correctly, and the report landed on
# the skill instead (skill#27, 2026-09-11).
CHANNELS = {
    "skill": "ayukhno/autosound-tuning-skill",
    "tcc": "ayukhno/autosound-tcc",
}
FEEDBACK_REPO = CHANNELS["skill"]
_EXPECTED_PREFIX = f"https://github.com/{FEEDBACK_REPO}/"

#: Images ride on an ORPHAN branch of that same hardcoded repo, never on `main`: an issue body
#: needs a URL that resolves, and a screenshot is not source. The branch is part of the rail,
#: not an argument -- a caller that could choose the branch could choose a repo (`skill#17`).
ASSET_BRANCH = "issue-assets"

#: Raw content comes back from a DIFFERENT host than the issue does, so `verify_feedback_url`
#: cannot be reused here: it rejects everything that is not `github.com`, and that is correct
#: for what it guards. Two hosts, two verifiers, one hardcoded repo.
_ASSET_PREFIX = f"https://raw.githubusercontent.com/{FEEDBACK_REPO}/{ASSET_BRANCH}/"


#: The route WITHOUT GitHub: the Arbiter's own Google Form (hub TCC-017, his decision 2026-09-17). A tester who
#: installed without `gh` -- the ordinary case since the installers stopped installing it unless asked -- had
#: nowhere to send a finding. Text only: a file question would make Google demand a sign-in for the whole form.
#: The address, the question ids and the choice words are the form's as published, fixed here like the repos
#: above -- a destination a model can fill in is what this module exists to refuse. The same form, the same
#: answers, as TCC's window sends (`autosound-tcc` `core/form_report.py`).
FORM_POST_URL = ("https://docs.google.com/forms/d/e/"
                 "1FAIpQLSdMzITv6Rzh8PWITy5QWc3xQMcAn9aDl1k0QbpZykHEQd6A4g/formResponse")
FORM_FIELD_SENDER = "entry.240346646"      # «Від кого», required: a name and a contact, so the Arbiter can answer
FORM_FIELD_KIND = "entry.2096497360"       # «Тип», required
FORM_FIELD_IMPACT = "entry.42935929"       # «Наскільки заважає налаштуванню», asked of a problem
FORM_FIELD_MESSAGE = "entry.970390217"     # «Повідомлення», required; Markdown travels as typed
FORM_FIELD_VERSIONS = "entry.1476583291"   # «Версії»
#: The form's own words: a choice it does not list is not an answer it takes.
FORM_KINDS = {"problem": "Проблема", "wish": "Побажання", "feedback": "Відгук", "test": "Тест"}
#: What a PERSON's report is. `test` is for a probe of the channel: its row is marked, so nothing needs cleaning.
FORM_PERSON_KINDS = ("problem", "wish", "feedback")
FORM_IMPACTS = {"stops": "Зупиняє: далі налаштовувати не можу",
                "workaround": "Заважає, але можна обійти",
                "none": "Не заважає"}
#: Only the confirmation page carries it (the "submit another response" link); a form that did not take the answer
#: replies 200 with its own page, which does not. Measured 2026-09-17 by TCC with entries that reached the sheet.
FORM_ACCEPTED_MARKER = "usp=form_confirm"
FORM_TIMEOUT_S = 20


class SideEffectRefused(RuntimeError):
    """Raised (FAIL LOUD) when an outbound command's output fails post-verification -- or when the
    action was never allowed to run at all (an upload nobody consented to)."""


def _subprocess_runner(argv):
    proc = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", errors="replace")
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


def channel_repo(channel):
    """The hardcoded repo behind a channel name. Anything outside `CHANNELS` is refused — a repo
    spelled out by the caller (`owner/name`) included, because that is exactly the #23 path."""
    if channel not in CHANNELS:
        raise ValueError(f"unknown feedback channel {channel!r} — one of {sorted(CHANNELS)}; "
                         "the repo is never the caller's to name")
    return CHANNELS[channel]


def _verify_issue_on(repo):
    """Post-verify: gh succeeded AND the returned URL is on `repo` (one of the hardcoded ones)."""
    prefix = f"https://github.com/{repo}/"

    def _verify(rc, out, err):
        if rc != 0:
            return False, f"gh exited {rc}"
        url = _extract_url(out) or _extract_url(err)
        if not url:
            return False, "no issue URL in gh output (did it actually post?)"
        # normalize + host/path check — reject a look-alike host or a different repo.
        p = urllib.parse.urlparse(url)
        if p.scheme != "https" or p.netloc != "github.com":
            return False, f"URL host is {p.netloc!r}, expected github.com — refusing ({url})"
        if not url.startswith(prefix):
            return False, f"URL {url} is NOT on {repo} — refusing (wrong-repo guard)"
        return True, f"verified on {repo}: {url}"

    return _verify


def verify_feedback_url(rc, out, err):
    """Post-verify: gh succeeded AND the returned URL is on the HARDCODED skill repo."""
    return _verify_issue_on(FEEDBACK_REPO)(rc, out, err)


_DEDUP_HOURS = 24.0


def _recent_duplicate(title, runner, hours=_DEDUP_HOURS, repo=FEEDBACK_REPO):
    """URL of an open issue with the EXACT same title created within `hours`, else None.

    A real double-post happened (issues #3/#4, 5 s apart). A list failure returns None —
    never block feedback because the dedup check itself couldn't run.
    """
    import json
    from datetime import datetime, timezone, timedelta
    argv = ["gh", "issue", "list", "--repo", repo, "--state", "open",
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
            return it.get("url") or f"https://github.com/{repo}/issues"
    return None


def _issue_number(url):
    import re
    m = re.search(r"/issues/(\d+)", url or "")
    return m.group(1) if m else None


def _verify_dsp_profile_update(prior_url):
    """Like verify_feedback_url, plus: the comment must land on the SAME issue as prior_url —
    otherwise a `gh issue comment` call that silently resolved to the wrong thread would pass."""
    prior_n = _issue_number(prior_url)

    def _verify(rc, out, err):
        ok, detail = verify_feedback_url(rc, out, err)
        if not ok:
            return ok, detail
        url = _extract_url(out) or _extract_url(err)
        n = _issue_number(url)
        if prior_n and n != prior_n:
            return False, f"comment landed on issue #{n}, expected #{prior_n} ({prior_url})"
        return True, detail

    return _verify


def post_dsp_profile(profile_file, vendor, model, mode="new", prior_url=None,
                      runner=_subprocess_runner, dry_run=False):
    """Contribute a DSP capability profile to the community.

    Deliberately divergent from `post_feedback`'s timing: a profile is offered for contribution
    RIGHT AFTER an onboarding interview produces or extends it, not deferred to a satisfaction
    milestone — the facts are valuable independent of whether the tuning project itself succeeds,
    and waiting risks losing them on an abandoned project.

    mode="new"    -> opens a new Issue "DSP profile: <vendor> · <model>" (same
                     guarded_run/verify_feedback_url/dedup discipline as post_feedback).
    mode="update" -> COMMENTS on `prior_url` instead of opening a disconnected duplicate — one
                     thread per DSP model. Requires `prior_url` (the caller reads it back from the
                     project's own `_contributed` bookkeeping, never re-resolved by a model).
    """
    import os
    import sys
    if mode not in ("new", "update"):
        raise ValueError(f"mode must be 'new' or 'update', got {mode!r}")
    if not os.path.isfile(profile_file):
        raise ValueError(f"profile-file not found: {profile_file!r}")
    if mode == "update" and not prior_url:
        raise ValueError("mode='update' requires prior_url (the issue thread to comment on)")
    if runner is _subprocess_runner and shutil.which("gh") is None and not dry_run:
        raise EnvironmentError("`gh` CLI not found — install/auth it, or use the copy-paste block.")

    if mode == "new":
        title = f"DSP profile: {vendor} · {model}"
        if not dry_run:
            dup = _recent_duplicate(title, runner)
            if dup:
                print(f"⛔ SKIP — identical DSP-profile issue already posted "
                      f"(<{_DEDUP_HOURS:.0f}h): {dup}", file=sys.stderr)
                return {"skipped": True, "duplicate_url": dup, "title": title}
        argv = ["gh", "issue", "create", "--repo", FEEDBACK_REPO,
                "--title", title, "--body-file", profile_file]
        return guarded_run(argv, verify_feedback_url, runner=runner, dry_run=dry_run)

    argv = ["gh", "issue", "comment", prior_url, "--body-file", profile_file]
    return guarded_run(argv, _verify_dsp_profile_update(prior_url), runner=runner, dry_run=dry_run)


def form_answers(sender, kind, message, impact="", versions=""):
    """The form's question ids with their answers. Raises `ValueError` for what the form would not take."""
    if not str(sender or "").strip():
        raise ValueError("the form asks who is writing -- a name and a contact the Arbiter can answer; ask the person")
    if not str(message or "").strip():
        raise ValueError("a report without words is not a report")
    if kind not in FORM_KINDS:
        raise ValueError(f"the kind is one of {', '.join(FORM_KINDS)}, not {kind!r}")
    if impact and impact not in FORM_IMPACTS:
        raise ValueError(f"how far it stops the tuning is one of {', '.join(FORM_IMPACTS)}, not {impact!r}")
    answers = {FORM_FIELD_SENDER: str(sender).strip(), FORM_FIELD_KIND: FORM_KINDS[kind],
               FORM_FIELD_MESSAGE: str(message).strip()}
    if impact:
        answers[FORM_FIELD_IMPACT] = FORM_IMPACTS[impact]
    if str(versions or "").strip():
        answers[FORM_FIELD_VERSIONS] = str(versions).strip()
    return answers


def method_version():
    """The method's version as a person quotes it: the tag this checkout is at, `v3.0.55-12-ga61d9f4` past it, or
    `unknown` -- never guessed. A signature for a person, nothing is decided by comparing it."""
    import os
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))))
    try:
        proc = subprocess.run(["git", "-C", root, "describe", "--tags", "--always"], capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=10)
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return "unknown"


def versions_line(lang, channel="skill", version=None, system=None):
    """`method v3.0.55 · Darwin 25.6.0 · lang=uk · about=skill` -- what the report ran on, and whose finding it is."""
    channel_repo(channel)
    system = system if system is not None else f"{platform.system()} {platform.release()}".strip()
    return f"method {version or method_version()} · {system or 'unknown'} · lang={lang} · about={channel}"


def _form_context():
    import ssl
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:  # noqa: BLE001 -- no certifi: the system's store is what there is
        return ssl.create_default_context()


def _form_post(url, data, timeout):
    request = urllib.request.Request(url, data=data,
                                     headers={"Content-Type": "application/x-www-form-urlencoded; charset=utf-8"})
    with urllib.request.urlopen(request, timeout=timeout, context=_form_context()) as response:
        return response.status, response.read().decode("utf-8", "replace")


def verify_form_reply(status, body):
    """Post-verify a form send: 200 AND the confirmation page's marker. A 200 without it is the form refusing."""
    if status != 200:
        return False, f"the form answered HTTP {status}"
    if FORM_ACCEPTED_MARKER not in (body or ""):
        return False, ("the form did not confirm (no confirmation page) -- closed, changed, or a required answer "
                       "missing; nothing was received")
    return True, "confirmed by the form"


def post_form(sender, kind, message, *, lang, channel="skill", impact="", consented=False, post=_form_post,
              dry_run=False, versions=None):
    """Send ONE report to the Arbiter's form. "Sent" is what the form CONFIRMS; anything else raises.

    `consented` is the same rail as for an upload: the person has seen the final text -- who, the kind, how far it
    stops the tuning, the message and the versions line -- and said yes. `channel` says whose finding it is and goes
    into the versions line; the destination is not the caller's.
    """
    versions = versions if versions is not None else versions_line(lang, channel)
    answers = form_answers(sender, kind, message, impact, versions)
    if not consented:
        raise SideEffectRefused(
            "⛔ SIDE-EFFECT REFUSED — no consent recorded for sending to the Arbiter's form.\n"
            "  reason : show the person the final text -- who is writing, the kind, for a problem how far it stops "
            "the tuning, the message and the versions line -- wait for a yes, and pass consented=True.")
    if dry_run:
        print("DRY-RUN — would send to the Arbiter's form:\n  " + FORM_POST_URL + "\n" +
              "\n".join(f"  {k} = {v[:80]}" for k, v in answers.items()))
        return {"dry_run": True, "via": "form", "answers": answers}
    data = urllib.parse.urlencode(answers).encode("utf-8")
    try:
        status, body = post(FORM_POST_URL, data, FORM_TIMEOUT_S)
    except urllib.error.HTTPError as exc:
        status, body = exc.code, ""
    except (urllib.error.URLError, OSError) as exc:
        raise SideEffectRefused(f"⛔ SIDE-EFFECT REFUSED — the form could not be reached: "
                                f"{getattr(exc, 'reason', None) or exc}") from exc
    ok, detail = verify_form_reply(status, body)
    if not ok:
        raise SideEffectRefused("⛔ SIDE-EFFECT REFUSED — output failed post-verification.\n"
                                f"  sent to : {FORM_POST_URL}\n  reason  : {detail}")
    return {"dry_run": False, "via": "form", "answers": answers, "detail": detail}


def gh_ready(runner=_subprocess_runner):
    """Can this machine post an issue: `gh` present AND signed in. Nothing leaves the machine to find out."""
    if runner is _subprocess_runner and shutil.which("gh") is None:
        return False
    try:
        rc, _out, _err = runner(["gh", "auth", "status"])
    except OSError:
        return False
    return rc == 0


def post_feedback(body_file, car, dsp, runner=_subprocess_runner, dry_run=False, channel="skill", via="auto",
                  sender=None, kind="feedback", impact="", lang="en", consented=False, post=_form_post,
                  gh_is_ready=None):
    """Post the de-identified feedback issue with the repo HARDCODED + returned-URL verified.

    Never let a model fill in the repo — that's the whole point. `car`/`dsp` only shape the title.
    `channel` picks WHOSE finding it is — "skill" (the method, its scripts, its documents) or "tcc"
    (the front-end window) — and the repo comes from `CHANNELS`, never from the argument itself.
    Dedup guard: if an identical-title open issue exists newer than 24 h, SKIP loudly instead of
    double-posting (returns {"skipped": True, "duplicate_url": …}).

    `via`: "github" (an issue), "form" (the Arbiter's form, `post_form`), or "auto" -- the issue when `gh` is
    present and signed in, the form otherwise. The form asks who is writing (`sender`), the kind, for a problem how
    far it stops the tuning (`impact`), in the person's own language (`lang`), and takes the body file's text as the
    message; it has no read-back, so there is no duplicate guard -- send once. Whether GitHub is at hand is asked of
    this machine's `gh` only when the real runner is in use: an injected runner (TCC's tests, `smoke_test.py`) is
    taken as GitHub, as it always was, unless `gh_is_ready` says otherwise.
    """
    import os
    import sys
    repo = channel_repo(channel)
    if via not in ("auto", "github", "form"):
        raise ValueError(f"via is 'auto', 'github' or 'form', not {via!r}")
    if not os.path.isfile(body_file):
        raise ValueError(f"body-file not found: {body_file!r} (write the feedback file first)")
    if gh_is_ready is None:
        gh_is_ready = (lambda: gh_ready(runner)) if runner is _subprocess_runner else (lambda: True)
    if via == "form" or (via == "auto" and not dry_run and not gh_is_ready()):
        if not str(sender or "").strip():
            raise EnvironmentError(
                "no GitHub here (`gh` missing or not signed in) -- the route is the Arbiter's form: ask the person "
                "who is writing (a name and a contact), the kind (problem / wish / feedback) and, for a problem, how "
                "far it stops the tuning; show the final text; then post_feedback(..., via='form', sender=…, "
                "kind=…, impact=…, lang=…, consented=True). Pictures do not go through the form.")
        with open(body_file, encoding="utf-8") as fh:
            message = fh.read()
        return post_form(sender, kind, message, lang=lang, channel=channel, impact=impact, consented=consented,
                         post=post, dry_run=dry_run)
    title = f"Feedback: {car} · {dsp}"
    if not dry_run:
        dup = _recent_duplicate(title, runner, repo=repo)
        if dup:
            print(f"⛔ SKIP — identical feedback issue already posted (<{_DEDUP_HOURS:.0f}h): {dup}",
                  file=sys.stderr)
            return {"skipped": True, "duplicate_url": dup, "title": title}
    argv = ["gh", "issue", "create", "--repo", repo,
            "--title", title, "--body-file", body_file]
    return guarded_run(argv, _verify_issue_on(repo), runner=runner, dry_run=dry_run)


def verify_asset_url(rc, out, err):
    """Post-verify an upload: gh succeeded AND the raw URL is on the hardcoded repo AND branch."""
    if rc != 0:
        return False, f"gh exited {rc}"
    url = _extract_url(out) or _extract_url(err)
    if not url:
        return False, "no raw URL in gh output (did the upload actually happen?)"
    p = urllib.parse.urlparse(url)
    if p.scheme != "https" or p.netloc != "raw.githubusercontent.com":
        return False, f"URL host is {p.netloc!r}, expected raw.githubusercontent.com — refusing ({url})"
    if not url.startswith(_ASSET_PREFIX):
        return False, (f"URL {url} is NOT on {FEEDBACK_REPO}@{ASSET_BRANCH} — refusing "
                       "(wrong-repo/branch guard)")
    return True, f"verified on {FEEDBACK_REPO}@{ASSET_BRANCH}: {url}"


def upload_issue_asset(image_path, dest_name, *, consented=False, message=None,
                       runner=_subprocess_runner, dry_run=False):
    """Publish ONE image to the hardcoded repo's asset branch; the verified raw URL is `["url"]`.

    Returns `guarded_run`'s dict — the same shape `post_feedback` returns — with one key added:
    **`url`**, the raw URL after `verify_asset_url` accepted it. The docstring used to say it
    returned the URL itself while it returned the dict, and a caller who believed it and parsed a
    string would have got `None` and shipped an issue body with no picture in it. Caught by `tcc`
    on the first real wiring (hub `SKL-019`, 2026-09-03), who read both forms defensively rather
    than trusting either — the key exists so nobody has to.

    For a bug report whose evidence is a picture: a UI bug arrives without its screenshot today,
    and `gh issue create` has no attach flag (public `skill#17`).

    `consented` is not a courtesy argument. **A public upload cannot be meaningfully un-published**,
    and a screenshot carries more than the bug — a DSP window shows file paths with a person's name,
    a vehicle, an installer's branding (`feedback-loop.md`, package safety). So the default is to
    refuse, and the caller has to have ASKED and been told yes; a window that shows the person each
    image and lets them drop any of them is the shape that answer comes from. Prose asking a caller
    to be careful is not a rail — the same lesson as the hardcoded repo two functions up.

    The repo and the branch are hardcoded for the same reason the feedback repo is: a caller that
    could name them could be talked into naming others. Only the file and its destination NAME are
    the caller's, and the name is placed under a fixed prefix rather than used as a path.
    """
    import base64
    import os
    import posixpath
    import tempfile

    if not consented:
        raise SideEffectRefused(
            "⛔ SIDE-EFFECT REFUSED — no consent recorded for a PUBLIC upload.\n"
            f"  file             : {image_path}\n"
            f"  would publish to : {_ASSET_PREFIX}\n"
            "  reason           : an image on a public repository cannot be meaningfully "
            "un-published, and a screenshot can carry a name, a vehicle or an installer's "
            "branding. Show the person what is about to be published, let them drop any of it, "
            "and pass consented=True.")
    if not os.path.isfile(image_path):
        raise ValueError(f"image not found: {image_path!r}")
    name = posixpath.basename(str(dest_name))
    if not name or name.startswith("."):
        raise ValueError(f"destination name is not usable: {dest_name!r}")

    with open(image_path, "rb") as fh:
        encoded = base64.b64encode(fh.read()).decode("ascii")
    # `gh api` reads a field's value from a file with `@path`. The base64 of a screenshot is far
    # past any comfortable argv length, so it travels in a file rather than on the command line.
    tmp = tempfile.NamedTemporaryFile("w", suffix=".b64", delete=False)
    try:
        tmp.write(encoded)
        tmp.close()
        argv = ["gh", "api", "-X", "PUT",
                f"repos/{FEEDBACK_REPO}/contents/issues/{name}",
                "-f", f"branch={ASSET_BRANCH}",
                "-f", f"message={message or 'issue asset: ' + name}",
                "-F", f"content=@{tmp.name}",
                "--jq", ".content.download_url"]
        done = guarded_run(argv, verify_asset_url, runner=runner, dry_run=dry_run)
        # `verify_asset_url` already resolved and checked it; re-deriving it from `detail` would
        # make every caller parse a sentence written for a human.
        if not done.get("dry_run"):
            done["url"] = _extract_url(done.get("stdout", "")) or _extract_url(done.get("stderr", ""))
        return done
    finally:
        os.unlink(tmp.name)


# ── self-test (no network — the runner is faked) ──────────────────────────────
def _selftest():
    import os, tempfile
    body = os.path.join(tempfile.mkdtemp(), "feedback.md")
    with open(body, "w", encoding="utf-8") as f:
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

    # ── the route without GitHub: the Arbiter's form (hub TCC-017) -- the network is faked ──
    ans = form_answers("Олена, t.me/x", "problem", "**зламалось** на кроці 2", "workaround", "method v3 · lang=uk")
    assert ans == {FORM_FIELD_SENDER: "Олена, t.me/x", FORM_FIELD_KIND: "Проблема", FORM_FIELD_MESSAGE: "**зламалось** на кроці 2",
                   FORM_FIELD_IMPACT: "Заважає, але можна обійти", FORM_FIELD_VERSIONS: "method v3 · lang=uk"}, ans
    assert FORM_FIELD_IMPACT not in form_answers("a", "wish", "b")
    for bad in (("", "wish", "b"), ("a", "wish", " "), ("a", "bug", "b"), ("a", "problem", "b", "blocks")):
        try:
            form_answers(*bad)
            raise AssertionError(f"the form's answers took {bad!r}")
        except ValueError:
            pass
    assert "test" in FORM_KINDS and "test" not in FORM_PERSON_KINDS
    line = versions_line("uk", "tcc", version="v3.0.55", system="Windows 11")
    assert line == "method v3.0.55 · Windows 11 · lang=uk · about=tcc", line
    sent = []
    def _confirming(url, data, timeout):
        sent.append((url, urllib.parse.parse_qs(data.decode("utf-8"))))
        return 200, '<a href="https://docs.google.com/forms/d/e/x/viewform?usp=form_confirm">'
    try:
        post_form("a", "feedback", "b", lang="en", post=_confirming)
        raise AssertionError("the form took a send nobody consented to")
    except SideEffectRefused:
        pass
    assert not sent, "a refused send must not reach the network"
    done = post_form("Олена", "feedback", "текст", lang="uk", consented=True, post=_confirming, versions="v")
    assert done["detail"] == "confirmed by the form" and sent[0][0] == FORM_POST_URL, done
    assert sent[0][1][FORM_FIELD_KIND] == ["Відгук"] and sent[0][1][FORM_FIELD_SENDER] == ["Олена"], sent[0]
    for reply, why in (((200, "<html>the form page</html>"), "a 200 without the confirmation page"),
                       ((500, "?usp=form_confirm"), "an error status")):
        try:
            post_form("a", "wish", "b", lang="en", consented=True, post=lambda u, d, t, r=reply: r, versions="v")
            raise AssertionError(f"the form's reply was accepted: {why}")
        except SideEffectRefused:
            pass
    def _down(url, data, timeout):
        raise urllib.error.URLError("no route")
    try:
        post_form("a", "wish", "b", lang="en", consented=True, post=_down, versions="v")
        raise AssertionError("an unreachable form was reported as sent")
    except SideEffectRefused:
        pass
    # auto: signed in → the issue, as before; not signed in → the form, which first needs who is writing
    no_auth = lambda argv: (1, "", "not logged in") if argv[:3] == ["gh", "auth", "status"] else good(argv)
    assert gh_ready(good) and not gh_ready(no_auth)
    try:
        post_feedback(body, "car", "dsp", runner=no_auth, gh_is_ready=lambda: gh_ready(no_auth))
        raise AssertionError("no GitHub and no sender, yet something was sent")
    except EnvironmentError as e:
        assert "Arbiter's form" in str(e) and "Pictures do not go" in str(e), e
    sent.clear()
    via_form = post_feedback(body, "car", "dsp", runner=no_auth, channel="tcc", sender="Олена", kind="problem",
                             impact="stops", lang="uk", consented=True, post=_confirming,
                             gh_is_ready=lambda: gh_ready(no_auth))
    assert via_form["via"] == "form" and sent[0][1][FORM_FIELD_MESSAGE] == ["# Feedback\nbody"], sent
    assert sent[0][1][FORM_FIELD_VERSIONS][0].endswith("lang=uk · about=tcc"), sent[0][1]
    assert sent[0][1][FORM_FIELD_IMPACT] == ["Зупиняє: далі налаштовувати не можу"]
    # the person may pick the form even with GitHub at hand
    assert post_feedback(body, "car", "dsp", runner=good, via="form", sender="a", consented=True,
                         post=_confirming)["via"] == "form"

    # ── the second channel: a TCC finding goes to TCC's repo, still hardcoded (skill#27) ──
    tcc_repo = CHANNELS["tcc"]
    tcc_good = lambda argv: (0, f"https://github.com/{tcc_repo}/issues/28\n", "")
    t = post_feedback(body, "car", "dsp", runner=tcc_good, channel="tcc")
    assert t["argv"][:5] == ["gh", "issue", "create", "--repo", tcc_repo], t["argv"]
    assert t["detail"] == f"verified on {tcc_repo}: https://github.com/{tcc_repo}/issues/28", t
    # dedup looks in the channel's own repo, not in the skill's.
    seen = []
    def _tcc_lister(argv):
        seen.append(argv)
        return (0, "[]", "") if argv[1:3] == ["issue", "list"] else tcc_good(argv)
    post_feedback(body, "car", "dsp", runner=_tcc_lister, channel="tcc")
    assert seen[0][seen[0].index("--repo") + 1] == tcc_repo, seen[0]
    # each channel verifies against ITS repo: a TCC post that comes back on the skill's repo is
    # the wrong-repo case, not a success, and the same the other way round.
    for ch, lands_on in (("tcc", FEEDBACK_REPO), ("skill", tcc_repo)):
        try:
            post_feedback(body, "car", "dsp", channel=ch,
                          runner=lambda argv, r=lands_on: (0, f"https://github.com/{r}/issues/1\n", ""))
            raise AssertionError(f"channel {ch!r} accepted a post that landed on {lands_on}")
        except SideEffectRefused:
            pass
    # the channel is a NAME from a closed set; a repo spelled out by the caller is refused before
    # anything runs — that is the #23 path with a new door.
    for bad_channel in ("ayukhno/autosound-tcc", "TCC", "hub", "", None):
        try:
            post_feedback(body, "car", "dsp", runner=good, channel=bad_channel)
            raise AssertionError(f"accepted channel {bad_channel!r}")
        except ValueError:
            pass
    assert post_feedback(body, "car", "dsp", dry_run=True, channel="tcc")["argv"][4] == tcc_repo

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

    # ── uploading a screenshot (skill#17): consent is a rail, not a courtesy ──────────────
    import os as _os, tempfile as _tf
    shot = _os.path.join(_tf.mkdtemp(), "shot.png")
    with open(shot, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + b"x" * 64)

    # Default is REFUSAL: a public upload cannot be un-published, and nobody was asked.
    try:
        upload_issue_asset(shot, "shot.png", runner=lambda argv: (0, "", ""))
        raise AssertionError("an upload nobody consented to must be refused")
    except SideEffectRefused as exc:
        assert "no consent recorded" in str(exc) and _ASSET_PREFIX in str(exc), exc

    raw = _ASSET_PREFIX + "shot.png"
    up = upload_issue_asset(shot, "shot.png", consented=True,
                            runner=lambda argv: (0, raw + "\n", ""))
    assert up["detail"].startswith("verified on"), up
    # The URL is a KEY, not a sentence to parse. The docstring once promised the URL and returned
    # the dict; a caller who believed it got None and posted an issue with no picture in it.
    assert up["url"] == raw, up
    assert upload_issue_asset(shot, "shot.png", consented=True, dry_run=True).get("url") is None
    # The repo AND the branch are in the command as constants, not as anything a caller passed.
    assert up["argv"][:4] == ["gh", "api", "-X", "PUT"], up["argv"]
    assert up["argv"][4] == f"repos/{FEEDBACK_REPO}/contents/issues/shot.png", up["argv"]
    assert f"branch={ASSET_BRANCH}" in up["argv"], up["argv"]
    # A destination "name" that tries to be a path is reduced to its basename, so neither a
    # traversal nor a second directory can be smuggled in through it.
    esc = upload_issue_asset(shot, "../../evil.png", consented=True,
                             runner=lambda argv: (0, _ASSET_PREFIX + "evil.png\n", ""))
    assert esc["argv"][4].endswith("/contents/issues/evil.png"), esc["argv"]

    # FAIL LOUD on the ways an upload can look successful and not be: the right host but the
    # wrong repo, a look-alike host, and gh exiting non-zero with a URL still on stdout.
    for bad, why in (
        ("https://raw.githubusercontent.com/someone/else/issue-assets/shot.png", "wrong repo"),
        (f"https://raw.githubusercontent.com.evil.test/{FEEDBACK_REPO}/{ASSET_BRANCH}/s.png",
         "look-alike host"),
        (f"https://github.com/{FEEDBACK_REPO}/blob/{ASSET_BRANCH}/shot.png", "not the raw host"),
    ):
        try:
            upload_issue_asset(shot, "shot.png", consented=True,
                               runner=lambda argv, u=bad: (0, u + "\n", ""))
            raise AssertionError(f"must refuse: {why}")
        except SideEffectRefused:
            pass
    try:
        upload_issue_asset(shot, "shot.png", consented=True,
                           runner=lambda argv: (1, raw + "\n", "boom"))
        raise AssertionError("must refuse: gh exited non-zero")
    except SideEffectRefused:
        pass
    # An upload of a file that is not there is a caller error, not a refusal to publish.
    try:
        upload_issue_asset(shot + ".missing", "shot.png", consented=True)
        raise AssertionError("must refuse a missing file")
    except ValueError:
        pass
    # Dry-run prints the exact command and publishes nothing.
    assert upload_issue_asset(shot, "shot.png", consented=True, dry_run=True)["dry_run"]

    print("selftest OK — verified good post; dedup guard skips a <24h duplicate (stale + broken "
          "list still post); FAIL LOUD on wrong-repo / confabulated-success / gh-failure / "
          "look-alike host; refused missing body-file + shell-string argv; dry-run safe. "
          "Channels: tcc posts to its hardcoded repo and dedups there, each channel refuses a post "
          "that lands on the other's repo, a caller-spelled repo or unknown name is refused. "
          "Upload: refused without consent, repo+branch hardcoded, name reduced to a basename, "
          "loud on wrong repo / look-alike host / non-raw host / gh failure, verified URL "
          "returned under ['url'].")
    return 0


def _selftest_dsp_profile():
    import os, tempfile
    profile = os.path.join(tempfile.mkdtemp(), "profile.json")
    with open(profile, "w", encoding="utf-8") as f:
        f.write('{"dsp_profile": {"name": "M6V4", "vendor": "Musway"}}\n')

    good_new = lambda argv: (0, f"https://github.com/{FEEDBACK_REPO}/issues/9\n", "")
    r = post_dsp_profile(profile, "Musway", "M6V4", mode="new", runner=good_new)
    assert r["detail"].startswith("verified on"), r
    assert r["argv"][:3] == ["gh", "issue", "create"], r["argv"]
    assert r["argv"][r["argv"].index("--title") + 1] == "DSP profile: Musway · M6V4", r["argv"]

    # update mode comments on the prior issue instead of opening a new one.
    prior = f"https://github.com/{FEEDBACK_REPO}/issues/9"
    good_comment = lambda argv: (0, f"{prior}#issuecomment-123\n", "")
    r2 = post_dsp_profile(profile, "Musway", "M6V4", mode="update", prior_url=prior,
                           runner=good_comment)
    assert r2["detail"].startswith("verified on"), r2
    assert r2["argv"] == ["gh", "issue", "comment", prior, "--body-file", profile], r2["argv"]

    # a comment that lands on a DIFFERENT issue than prior_url must be refused, not accepted.
    wrong_issue = lambda argv: (0, f"https://github.com/{FEEDBACK_REPO}/issues/12#issuecomment-1\n", "")
    try:
        post_dsp_profile(profile, "Musway", "M6V4", mode="update", prior_url=prior,
                          runner=wrong_issue)
        raise AssertionError("accepted a comment that landed on the wrong issue")
    except SideEffectRefused:
        pass

    # mode='update' without prior_url is a deterministic refusal, no command runs.
    try:
        post_dsp_profile(profile, "Musway", "M6V4", mode="update", runner=good_comment)
        raise AssertionError("accepted mode='update' with no prior_url")
    except ValueError:
        pass

    # same wrong-repo confabulation guard applies to profile posts.
    wrong_repo = lambda argv: (0, "https://github.com/someone-else/skill/issues/1\n", "")
    try:
        post_dsp_profile(profile, "Musway", "M6V4", mode="new", runner=wrong_repo)
        raise AssertionError("accepted a profile post landing on the wrong repo")
    except SideEffectRefused:
        pass

    print("selftest OK (dsp-profile) — new-mode posts a titled Issue; update-mode comments on "
          "prior_url instead of duplicating; refused a comment that landed on the wrong issue, "
          "a missing prior_url, and the wrong-repo confabulation.")
    return 0


if __name__ == "__main__":
    # issue #21: a code page must not destroy a result. Run from a subdirectory, so the sibling
    # modules' own directory has to go on the path before `console` can be found at all.
    import os as _os, sys as _sys
    _sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
    import console
    console.install()
    raise SystemExit(_selftest() or _selftest_dsp_profile())
