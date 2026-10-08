#!/usr/bin/env python3
"""Check that the three installers still agree with each other.

`install.sh`, `install.ps1` and `install.cmd` carry the same decisions three times in three
languages. Nothing made them agree, and on 2026-08-22 the same class of drift was found three
times in one evening: a line-count comparison that never opened `install.cmd`; a tag glob counted
as living in two files when it lived in three; and a claim about the update path checked in the
bash half and wrong in both. Each was caught by a person reading carefully, which is exactly the
mechanism that fails on the day nobody does.

So this compares the constants that MUST match and fails when they drift. It is deliberately
narrow: it parses declarations, not logic, and it would rather check four things reliably than
ten things approximately.

    python3 scripts/installer-consistency.py     # OK, or the divergences, exit 1

What it does NOT check, so nobody reads a pass as more than it is: that the three files do the
same THING. Only that the values they were given are the same values. A rewritten update path in
one file alone still passes here — read all three.
"""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SH, PS1, CMD = ROOT / "install.sh", ROOT / "install.ps1", ROOT / "install.cmd"

# owner/repo as it appears in any github URL, however the URL is spelled
SLUG = re.compile(r"github(?:usercontent)?\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?(?=[/\s\"']|$)", re.M)


def read(p):
    if not p.exists():
        sys.exit(f"missing: {p.name} — this check expects all three installers")
    return p.read_text(encoding="utf-8", errors="replace")


def slug_of(url, where, problems):
    """owner/repo out of one URL, or a problem naming the URL that did not yield one."""
    m = SLUG.search(url)
    if not m:
        problems.append(f"{where}: not a github URL — {url}")
        return None
    return m.group(1).rstrip("/")


def one(pattern, text, what, where):
    """Exactly one match, or the check itself is broken and says so instead of guessing."""
    found = re.findall(pattern, text, re.M)
    if len(found) != 1:
        return None, f"{where}: expected exactly one {what}, found {len(found)}"
    return found[0], None


def home_path_sh(sh, name):
    """`NAME="${HOME}/<path>"` in install.sh -> `<path>`, or (None, why)."""
    return one(rf'^{name}="\$\{{HOME\}}/([^"]+)"', sh, name, "install.sh")


def checkout_paths(sh, ps1, sh_name, ps_name, problems):
    """One checkout path from each installer, relative to the home folder, slashes forward.

    install.sh spells it `"${HOME}/.claude/..."` and install.ps1 `Join-Path $HOME ".claude\\..."`,
    so both are read down to the part after the home folder: the comparison is about the place,
    not the punctuation. A path either file no longer spells that way is a problem, not a pass.
    """
    p_sh, err_a = home_path_sh(sh, sh_name)
    p_ps, err_b = one(rf'^\${ps_name}\s*=\s*Join-Path \$HOME "([^"]+)"', ps1, f"${ps_name}",
                      "install.ps1")
    problems.extend(e for e in (err_a, err_b) if e)
    return p_sh, (p_ps.replace("\\", "/") if p_ps else None)


#: The order the beta channel must produce (hub RELEASE-CHANNEL.md §11.2, HUB-060), as (tags
#: offered, the one to install): numeric where a number sits, a release above its own candidates, a
#: candidate for a newer version above an older release, and nothing of another shape.
CHANNEL_CASES = (
    (["v3.0.9", "v3.0.10", "v3.0.49"], "v3.0.49"),
    (["v3.0.49", "beta-v3.1.0-rc1"], "beta-v3.1.0-rc1"),
    (["beta-v3.1.0-rc10", "v3.0.49", "beta-v3.1.0-rc2"], "beta-v3.1.0-rc10"),
    (["beta-v3.1.0-rc2", "v3.1.0", "v3.0.49"], "v3.1.0"),
    (["v3.1.1-foo", "beta-v3.1.1", "beta-v3.2.0-rc", "v3.0.49"], "v3.0.49"),
    # skill #108: the STABLE pick goes through the same function, so a name that is not a release never wins.
    (["v3.0.49", "v3.x", "v3.9"], "v3.0.49"),
    (["v0.1.44", "v0.x", "v0.1.45"], "v0.1.45"),
    ([], ""),
)
#: What install.ps1's `Select-NewestOnChannel` must still carry. Read, not run: there is no
#: PowerShell on the author's Mac or in CI, so this half is shapes and sort key, not behaviour. The
#: two shapes are the release-tag rule's (T-45): ASCII digits, the whole name, case kept.
PS1_CHANNEL_SHAPES = ("-cmatch '^v([0-9]+)\\.([0-9]+)\\.([0-9]+)\\z'",
                      "-cmatch '^beta-v([0-9]+)\\.([0-9]+)\\.([0-9]+)-rc([0-9]+)\\z'", "Sort-Object X, Y, Z, R, N")

#: T-45 (#142): one rule for "is a release tag", answered alike by install.sh's `is_release_tag` (run), upkeep.py's
#: `is_release_tag` (imported) and install.ps1's `Test-ReleaseTag` (read, applied as .NET reads it). `١` is
#: ARABIC-INDIC DIGIT ONE, which `\d` takes in Python and .NET alike; the newline is one `$` lets through.
TAG_RULE_CASES = (("v3.1.2", True), ("beta-v3.1.3-rc1", True), ("v3.1.2-x", False), ("v3.1", False),
                  ("v3.1.2\n", False), ("v3.١.2", False), ("main", False), ("V3.1.2", False),
                  # ...and an -rc only with beta-, beta- only with an -rc: two shapes, as newest_on_channel's awk pair.
                  ("v3.1.2-rc1", False), ("beta-v3.1.3", False))

#: T-37 (#142): the tags a stand-in `ls-remote` offers the method's pick, and the one it must install on stable.
SELECTION_TAGS = ("v3.0.9", "v3.1.10", "v3.1.2", "beta-v3.1.3-rc1", "v3.1.2-x", "v03.1.1")
#: ...and the stand-in: a `git` with no network. `ls-remote` prints a ref line for each name in the file $STUB_TAGS
#: names (none when it is unset), or -- $STUB_RC not 0 -- git's own words for a remote it cannot reach, with that exit.
#: Any other subcommand is not this test's to answer. Bytes, so the script keeps its "\n" line ends on Windows.
NO_NETWORK_GIT = (b"#!/bin/sh\n"
                  b"[ \"$1\" = ls-remote ] || { echo \"stub git: $1 is not asked here\" >&2; exit 99; }\n"
                  b"if [ \"${STUB_RC:-0}\" != 0 ]; then\n"
                  b"  echo \"fatal: unable to access 'https://github.com/ayukhno/autosound-tuning-skill.git/': "
                  b"Could not resolve host: github.com\" >&2\n"
                  b"  exit \"$STUB_RC\"\n"
                  b"fi\n"
                  b"[ -n \"${STUB_TAGS:-}\" ] || exit 0\n"
                  b"while IFS= read -r t; do\n"
                  b"  printf '0123456789abcdef0123456789abcdef01234567\\trefs/tags/%s\\n' \"$t\"\n"
                  b"done < \"$STUB_TAGS\"\n")
#: T-45 (#142): a `git` whose `checkout` answers 0 and does nothing -- a checkout that did not land. Everything else is
#: the real git, which the script names in $REAL_GIT before this folder goes first on PATH.
NO_CHECKOUT_GIT = (b"#!/bin/sh\n"
                   b"for a in \"$@\"; do [ \"$a\" = checkout ] && exit 0; done\n"
                   b"exec \"$REAL_GIT\" \"$@\"\n")

#: The installers' exit table (#142, audit T-44, J6a item 4): 0 ready · 1 stopped -- the method not installed or not
#: changed (steps before it, Claude Code's, may have run) · 2 usage · 3 installed, NOT ready, the missing parts named.
#: The receipt's fields in the order both installers write them: today's seven, then how the run ended.
RECEIPT_FIELDS = ("installer", "installer_sha256", "method_ref", "mode", "at", "platform", "engine",
                  "installer_version", "status", "missing", "python")
#: The short names a part that is not ready goes by, in both installers. install.ps1 adds the python3 a new window
#: runs, which only Windows gets wrong (`python3 in a new window`).
MISSING_NAMES = ("numpy", "scipy", "the method", "the method (2.x line)", "the beta copy", "TCC", "Claude Code")
#: What ENGINE_DID can carry -- the engine's own last line: a quote, a backslash, a tab. The receipt is JSON whatever it
#: holds: python's builder keeps the tab, escaped; the shell's drops control characters.
HOSTILE_ENGINE = 'built or run failed: "C:\\dotnet\\sdk" said\tno'
#: The `python3` a run of `finish` sees: a `plugin-ready` call is written down in $PLUGIN_MARK, anything else goes to
#: the interpreter running this check -- so the receipt's JSON is built the same way on every platform.
FAKE_PYTHON3 = ('python3() {\n'
                '  case " $* " in *" plugin-ready "*) printf "%s\\n" "$*" >> "$PLUGIN_MARK"; return 0 ;; esac\n'
                '  "$PYTHON_FOR_TEST" "$@"\n'
                '}\n')


def cut_functions(sh, names):
    """`(text, missing)`: the named functions of install.sh, cut out as they stand -- one line (`say() { ...; }`), or
    from `name() {` to the first `}` alone at column 0 -- and the names not found. A copy here would be a second
    implementation, agreeing with this file while the installer drifted."""
    cut, missing = [], []
    for name in names:
        m = (re.search(rf"^{name}\(\)[ \t]*\{{[^\n]*;[ \t]*\}}[ \t]*\n", sh, re.M)
             or re.search(rf"^{name}\(\) \{{[^\n]*\n.*?^\}}\n", sh, re.M | re.S))
        if m:
            cut.append(m.group(0))
        else:
            missing.append(name)
    return "".join(cut), missing


def bash_literal(text):
    """`text` as a bash `$'...'` word, every byte that is not a plain letter, digit, `.` or `-` as `\\xHH`: a newline
    or a non-ASCII digit reaches the function exactly, through bash 3.2 too."""
    return "$'" + "".join(chr(b) if (chr(b).isalnum() and b < 128) or chr(b) in ".-" else f"\\x{b:02x}"
                          for b in text.encode("utf-8")) + "'"


def _is_wsl_launcher(path, environ=os.environ):
    """True for a `bash.exe` under the Windows system directory: WSL's launcher, not a shell."""
    sysroot = environ.get("SystemRoot") or environ.get("windir") or "C:\\Windows"
    p = os.path.normcase(os.path.abspath(path))
    return any(p.startswith(os.path.normcase(os.path.join(sysroot, d)) + os.sep)
               for d in ("System32", "Sysnative", "SysWOW64"))


def find_bash(windows=None, which=shutil.which, environ=os.environ):
    """`(path, None)` for a bash that can run install.sh's function, else `(None, why)`.

    On Windows the `bash` on PATH is often `C:\\Windows\\System32\\bash.exe`, WSL's launcher: with no
    Linux distribution installed it prints a UTF-16 notice instead of running anything, and v3.0.50's
    order check reported six false divergences on GitHub's windows-latest (hub TCC-010). So on
    Windows the bash is Git for Windows' own, found beside `git` or in its usual place, and the
    launcher is never taken for one.
    """
    windows = (os.name == "nt") if windows is None else windows
    if not windows:
        found = which("bash")
        return (found, None) if found else (None, "no bash on PATH")
    candidates = []
    git = which("git")
    if git:
        here = Path(git).resolve().parent                # ...\Git\cmd, ...\Git\mingw64\bin, ...
        for up in [here] + list(here.parents)[:3]:
            candidates += [up / "bin" / "bash.exe", up / "usr" / "bin" / "bash.exe"]
    for var in ("ProgramFiles", "ProgramW6432", "ProgramFiles(x86)", "LOCALAPPDATA"):
        if environ.get(var):
            base = Path(environ[var])
            candidates += [base / "Git" / "bin" / "bash.exe", base / "Programs" / "Git" / "bin" / "bash.exe"]
    on_path = which("bash")
    if on_path:
        candidates.append(Path(on_path))
    for c in candidates:
        if c.is_file() and not _is_wsl_launcher(str(c), environ):
            return str(c), None
    if on_path and _is_wsl_launcher(on_path, environ):
        return None, (f"no usable bash on Windows: the `bash` on PATH is WSL's launcher ({on_path}), "
                      "and no Git for Windows bash was found")
    return None, "no usable bash on Windows: none on PATH, and no Git for Windows bash was found"


def channel_order_problems(sh):
    """Run install.sh's own `newest_on_channel` on CHANNEL_CASES; [] when it gives every answer.

    The function is cut out of the installer's text and run as it stands -- a copy of it here would be
    a second implementation, agreeing with this file while the installer drifted.
    """
    m = re.search(r"^newest_on_channel\(\) \{\n.*?^\}\n", sh, re.M | re.S)
    if not m:
        return ["install.sh: no `newest_on_channel() { ... }` -- the beta channel's order cannot be checked"]
    bash, why = find_bash()
    if not bash:
        return [f"{why} -- install.sh's beta order cannot be run, and unrun is not agreed"]
    out = []
    for offered, want in CHANNEL_CASES:
        # The function and the names go in on stdin, as BYTES: an argument is re-quoted on Windows, and
        # a text pipe there turns "\n" into "\r\n", which bash reads as part of each command. /usr/bin
        # goes first so Git Bash's own sort and awk answer, not Windows' sort.exe.
        script = ('export PATH="/usr/bin:$PATH"\n' + m.group(0)
                  + "newest_on_channel <<'TAGS'\n" + "".join(t + "\n" for t in offered) + "TAGS\n")
        r = subprocess.run([bash, "-s"], input=script.encode("utf-8"), capture_output=True)
        got = r.stdout.decode("utf-8", "replace").strip()
        err = r.stderr.decode("utf-8", "replace").strip()
        if r.returncode != 0 or got != want:
            out.append(f"install.sh newest_on_channel via {bash}: {offered} gave {got[:60]!r}, want {want!r}"
                       + (f" (exit {r.returncode}: {err[:80]})" if r.returncode else ""))
    return out


UPKEEP = ROOT / "skills" / "autosound-tuning" / "scripts" / "upkeep.py"


#: The functions of install.sh's signature check, cut out and run together: the method's tag and the app's (#99, #101),
#: and the release-tag rule they ask (T-45).
SIGNING_FUNCTIONS = ("is_release_tag", "settled_by_name", "verify_tag", "check_tcc_tag", "tcc_tag_still_at")

#: T-35 (#142): what the person's own git configuration may hold, and a `git` that is not git. Each answers "Good" one
#: way or another; none of them is the author's signature. A fake `gpg.program` stands in for gpg: no real one runs,
#: and no keyring is touched. Bytes, so a script keeps its "\n" line ends on Windows.
SIGN_ONLY_HELPER = b"#!/bin/sh\necho 'helper: sign-only (try -Y sign)' >&2\nexit 1\n"
FAKE_GPG = (b"#!/bin/sh\n"
            b"cat >/dev/null\n"
            b"echo '[GNUPG:] NEWSIG'\n"
            b"echo '[GNUPG:] GOODSIG 0123456789ABCDEF Mallory <m@example.org>'\n"
            b"echo '[GNUPG:] VALIDSIG 0123456789ABCDEF0123456789ABCDEF01234567 2026-10-08 0 0 0 0 0 1 0 "
            b"0123456789ABCDEF0123456789ABCDEF01234567'\n"
            b"echo '[GNUPG:] TRUST_ULTIMATE 0 pgp'\n"
            b"echo 'gpg: Good signature from \"Mallory <m@example.org>\" [ultimate]' >&2\n"
            b"exit 0\n")
STUB_GIT = (b"#!/bin/sh\n"
            b"for a in \"$@\"; do\n"
            b"  if [ \"$a\" = verify-tag ]; then echo 'Good signature from \"anyone\"' >&2; exit 0; fi\n"
            b"done\n"
            b"exec /usr/bin/git \"$@\"\n")
#: An ssh-keygen older than OpenSSH 8.2, which has no -Y: git answers for it in a sentence of its own.
OLD_SSH_KEYGEN = (b"#!/bin/sh\n"
                  b"echo 'ssh-keygen: illegal option -- Y' >&2\n"
                  b"echo 'usage: ssh-keygen [-q] [-b bits] [-C comment] [-f output_keyfile]' >&2\n"
                  b"exit 1\n")
#: A tag message that ends in an OpenPGP block -- any base64 body: git hands it to `gpg.program` as it is.
PGP_SIGNED_MESSAGE = (b"v3.0.67\n\n-----BEGIN PGP SIGNATURE-----\n\n"
                      b"iQEzBAABCAAdFiEEASNFZ4mrze8BI0VniavN7wEjRWcFAmcFAAAACgkQASNFZ4mrze8AAA==\n=AAAA\n"
                      b"-----END PGP SIGNATURE-----\n")


def signing_problems(sh):
    """Run install.sh's own signature check against tags made here (skill #99, #101); [] when it answers each right.

    A temp repo gets a signed tag, a tag signed by another key, an unsigned one and one older than signing, for the
    method's line and for the app's; the functions are cut out of the installer and run with THIS test's key in the
    constants they read. The app's tags go through `check_tcc_tag` whole, with the temp repo standing in for
    TCC_REPO: the fetch into a bare repo, the check, the commit it hands on, and the "moved" check before uv. Made in
    a subprocess, not by a session's `git tag`, which the channel guard refuses.
    """
    import tempfile
    cut = []
    for name in SIGNING_FUNCTIONS:
        m = re.search(rf"^{name}\(\) \{{[^\n]*\n.*?^\}}\n", sh, re.M | re.S)
        if not m:
            return [f"install.sh: no `{name}() {{ ... }}` -- the signature check cannot be run"]
        cut.append(m.group(0))
    functions = "".join(cut)
    bash, why = find_bash()
    if not bash:
        return [f"{why} -- install.sh's signature check cannot be run, and unrun is not agreed"]
    tmp = tempfile.mkdtemp(prefix="autosound_sign_")
    # GNUPGHOME in this temp dir: no case may reach the person's own ~/.gnupg, whatever a case gets wrong.
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
               GIT_COMMITTER_EMAIL="t@t", GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1",
               GNUPGHOME=os.path.join(tmp, "gnupg"))
    env.pop("AUTOSOUND_SKIP_TAG_VERIFY", None)

    def sh_run(*cmd, cwd=None):
        r = subprocess.run(list(cmd), cwd=cwd, env=env, capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(f"{' '.join(cmd)}: {r.stderr.strip()[:200]}")
        return r.stdout
    try:
        os.makedirs(env["GNUPGHOME"], mode=0o700)
        keys = {}
        for who in ("author", "stranger"):
            sh_run("ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", who, "-f", os.path.join(tmp, who))
            keys[who] = " ".join(Path(tmp, who + ".pub").read_text().split()[:2])
        repo = os.path.join(tmp, "repo")
        sh_run("git", "init", "-q", repo)
        Path(repo, "a").write_text("a\n")
        sh_run("git", "-C", repo, "add", "a")
        sh_run("git", "-C", repo, "commit", "-q", "-m", "a")
        sh_run("git", "-C", repo, "tag", "-a", "v3.0.10", "-m", "before signing")
        signed = ("git", "-C", repo, "-c", "gpg.format=ssh")
        sh_run(*signed, "-c", f"user.signingkey={os.path.join(tmp, 'author')}.pub", "tag", "-s", "v3.0.64", "-m", "s")
        sh_run(*signed, "-c", f"user.signingkey={os.path.join(tmp, 'stranger')}.pub", "tag", "-s", "v3.0.65", "-m", "f")
        sh_run("git", "-C", repo, "tag", "-a", "v3.0.66", "-m", "unsigned")
        # The app's line (#101): v0.1.45 is TCC's first signed tag; v0.1.48 is lightweight -- no ^{} line to peel.
        sh_run("git", "-C", repo, "tag", "-a", "v0.1.44", "-m", "before signing")
        sh_run(*signed, "-c", f"user.signingkey={os.path.join(tmp, 'author')}.pub", "tag", "-s", "v0.1.45", "-m", "s")
        sh_run(*signed, "-c", f"user.signingkey={os.path.join(tmp, 'stranger')}.pub", "tag", "-s", "v0.1.46", "-m", "f")
        sh_run("git", "-C", repo, "tag", "-a", "v0.1.47", "-m", "unsigned")
        sh_run("git", "-C", repo, "tag", "v0.1.48")
        commit = sh_run("git", "-C", repo, "rev-parse", "HEAD").strip()
        # T-35 (#142): a tag whose message ends in an OpenPGP block, the scripts above, and the git configs that
        # name them -- each a file in this temp dir, its paths written with forward slashes for git on Windows.
        Path(tmp, "pgp-message").write_bytes(PGP_SIGNED_MESSAGE)
        sh_run("git", "-C", repo, "tag", "-a", "v3.0.67", "-F", os.path.join(tmp, "pgp-message"))
        stub_dir, old_dir = Path(tmp, "stub-git"), Path(tmp, "old-openssh")
        stub_dir.mkdir()
        old_dir.mkdir()
        for path, body in ((Path(tmp, "sign-only.sh"), SIGN_ONLY_HELPER), (Path(tmp, "fake-gpg.sh"), FAKE_GPG),
                           (stub_dir / "git", STUB_GIT), (old_dir / "ssh-keygen", OLD_SSH_KEYGEN)):
            path.write_bytes(body)
            path.chmod(0o755)
        hostile, pgp = Path(tmp, "hostile.gitconfig"), Path(tmp, "pgp.gitconfig")
        hostile.write_bytes(f'[gpg "ssh"]\n\tprogram = {Path(tmp, "sign-only.sh").as_posix()}\n'.encode("utf-8"))
        pgp.write_bytes(f'[gpg]\n\tprogram = {Path(tmp, "fake-gpg.sh").as_posix()}\n'.encode("utf-8"))
        ultimate = Path(tmp, "ultimate.gitconfig")
        ultimate.write_bytes(b"[gpg]\n\tminTrustLevel = ultimate\n")
    except (OSError, RuntimeError) as exc:
        return [f"the signature check's fixtures could not be made ({exc}) -- unrun is not agreed"]
    repo_posix = Path(repo).as_posix()

    def run(call, skip="", dry="0", config=os.devnull, first_on_path=None):
        # A folder put first on PATH goes in as bash spells it: `cd` takes a Windows path, `pwd` answers in Git Bash's
        # own form, which PATH's colons can carry.
        first = f'"$(cd "{first_on_path.as_posix()}" && pwd)":' if first_on_path else ""
        script = (f'export PATH={first}"/usr/bin:$PATH"\nsay() {{ printf "%s\\n" "$*"; }}\n'
                  f'warn() {{ printf "! %s\\n" "$*"; }}\n'
                  f'DRY_RUN={dry}\nAUTOSOUND_SKIP_TAG_VERIFY="{skip}"\nSKILL_SIGNING_PRINCIPAL=author\n'
                  f'SKILL_SIGNING_KEY="{keys["author"]}"\nSKILL_SIGNED_FROM=v3.0.64\nTCC_SIGNED_FROM=v0.1.45\n'
                  f'TCC_REPO="{repo_posix}"\n' + functions + call)
        r = subprocess.run([bash, "-s"], input=script.encode("utf-8"), capture_output=True,
                           env=dict(env, GIT_CONFIG_GLOBAL=str(config)))
        return r.returncode, r.stdout.decode("utf-8", "replace") + r.stderr.decode("utf-8", "replace")

    out = []
    # A name that is not a release is still installed when it is named -- and said UNSIGNED (T-37).
    cases = (("v3.0.64", "", 0, "signed by the skill's author"), ("v3.0.65", "", 1, "does not check out"),
             ("v3.0.66", "", 1, "does not check out"), ("v3.0.10", "", 0, "predates signed tags"),
             ("main", "", 0, "UNSIGNED"), ("v3.0.66", "1", 0, "NOT checked"))
    for ref, skip, want_rc, want_text in cases:
        rc, said = run(f'verify_tag "{repo_posix}" "{ref}" 2>&1\n', skip)
        if rc != want_rc or want_text not in said:
            out.append(f"install.sh verify_tag {ref}{' (skip)' if skip else ''}: exit {rc}, want {want_rc} "
                       f"and {want_text!r} -- said {said.strip()[-160:]!r}")
    # Only the rule's own "no" settles a name as unsigned: a rule that fails some other way (here it is not there at
    # all, exit 127) sends the name on to the signature, which refuses it -- it never installs unchecked (T-45).
    rc, said = run(f'unset -f is_release_tag\nverify_tag "{repo_posix}" main 2>&1\n')
    if rc != 1 or "UNSIGNED" in said or "does not check out" not in said:
        out.append(f"install.sh verify_tag main with no release-tag rule to ask: exit {rc}, want 1 and 'does not "
                   f"check out', never 'UNSIGNED' -- said {said.strip()[-160:]!r}")
    # T-35 (#142): a signature is the author's or nothing, whatever the person's git or GPG configuration says. A
    # sign-only helper as gpg.ssh.program (1Password's, for one) is not asked, so the good tag passes; an OpenPGP tag
    # the person's gpg calls good (git picks the verifier from the signature, not gpg.format) and a git that says
    # "Good" of any tag are refused, though each exits 0 with "Good". An ssh-keygen with no -Y is a machine that cannot
    # check, said as such: its refusal is not called a bad signature. Last, a person's `gpg.minTrustLevel=ultimate`:
    # git rates a key in allowed_signers `fully`, and refused every good release with the Good line printed.
    #   The stand-ins' own words are asked for too (T-35's review): a fake gpg that never ran, or an ssh-keygen Windows
    # could not spawn, is refused the same way -- and would pass unseen while the person's real gpg ran.
    t35_cases = ((hostile, None, "v3.0.64", 0, ("signed by the skill's author",), "a sign-only gpg.ssh.program"),
                 (pgp, None, "v3.0.67", 1, ("does not check out", 'Good signature from "Mallory'),
                  "a gpg.program that calls an OpenPGP tag good"),
                 (os.devnull, stub_dir, "v3.0.64", 1, ("does not check out",), "a git on PATH that says Good"),
                 (os.devnull, old_dir, "v3.0.64", 1, ("could not be checked here", "find-principals/verify"),
                  "an ssh-keygen with no -Y"),
                 (ultimate, None, "v3.0.64", 0, ("signed by the skill's author",), "gpg.minTrustLevel=ultimate"))
    for config, first_on_path, ref, want_rc, want_texts, what in t35_cases:
        rc, said = run(f'verify_tag "{repo_posix}" "{ref}" 2>&1\n', config=config, first_on_path=first_on_path)
        if rc != want_rc or any(text not in said for text in want_texts):
            out.append(f"install.sh verify_tag {ref} under {what}: exit {rc}, want {want_rc} and "
                       f"{' + '.join(repr(t) for t in want_texts)} -- said {said.strip()[-200:]!r}")
    # The app's tags, through check_tcc_tag: (ref, the switch, a dry run, exit, words, the commit it hands on).
    tcc_cases = (("v0.1.45", "", "0", 0, "v0.1.45 is signed by TCC's author", commit),
                 ("v0.1.46", "", "0", 1, "does not check out", ""),
                 ("v0.1.47", "", "0", 1, "a release of TCC is signed by its author", ""),
                 ("v0.1.44", "", "0", 0, "predates signed tags (they start at v0.1.45)", ""),
                 ("v0.1.47", "1", "0", 0, "NOT checked", ""),
                 ("v0.1.99", "", "0", 1, "could not fetch v0.1.99", ""),
                 ("v0.1.45", "", "1", 0, "would check the signature of v0.1.45", ""))
    for ref, skip, dry, want_rc, want_text, want_sha in tcc_cases:
        rc, said = run(f'check_tcc_tag "{ref}" 2>&1; rc=$?; printf "TCC_SHA=%s\\n" "$TCC_SHA"; exit $rc\n', skip, dry)
        if rc != want_rc or want_text not in said or f"TCC_SHA={want_sha}\n" not in said:
            out.append(f"install.sh check_tcc_tag {ref}{' (skip)' if skip else ''}{' (dry run)' if dry == '1' else ''}: "
                       f"exit {rc}, want {want_rc}, {want_text!r} and TCC_SHA={want_sha[:12]!r} -- said "
                       f"{said.strip()[-160:]!r}")
    # ...and the "moved" check before uv: the verified commit passes; another commit, or a tag with no ^{} line, not.
    for ref, sha, want_rc in (("v0.1.45", commit, 0), ("v0.1.45", "0" * 40, 1), ("v0.1.48", commit, 1)):
        rc, said = run(f'tcc_tag_still_at "{ref}" "{sha}"\n')
        if rc != want_rc:
            out.append(f"install.sh tcc_tag_still_at {ref} {sha[:12]}: exit {rc}, want {want_rc} -- said {said.strip()[-120:]!r}")
    shutil.rmtree(tmp, ignore_errors=True)
    return out


def ps1_stop_problems(ps1):
    """install.ps1 stops only through Stop-Installer; [] when it does.

    Under the README one-liner (`irm ... | iex`) there is no file, and a bare `exit` ends the user's
    own PowerShell -- the window closed over the line that said why (2026-09-13). The one `exit`
    that is right lives inside Stop-Installer, for a run as a file; every call is followed by
    `; return`, which is what ends the script when there is no file.
    """
    lines = ps1.splitlines()
    fn = re.search(r"^function Stop-Installer \{\n.*?^\}$", ps1, re.M | re.S)
    if not fn:
        return ["install.ps1: no `function Stop-Installer { ... }` -- the one-liner's stops cannot be checked"]
    first = ps1.count("\n", 0, fn.start()) + 1
    last = ps1.count("\n", 0, fn.end()) + 1
    out = []
    for n, line in enumerate(lines, 1):
        if line.lstrip().startswith("#") or first <= n <= last:
            continue
        if re.search(r"\bexit\b", line):
            out.append(f"install.ps1:{n}: a bare `exit` -- under the one-liner it closes the user's "
                       f"window; use `Stop-Installer N; return`")
        elif re.search(r"\bStop-Installer\b", line) and not re.match(r"^\s*Stop-Installer \d+; return\s*$", line):
            out.append(f"install.ps1:{n}: Stop-Installer without `; return` on its line -- without "
                       f"the return the one-liner runs on past the stop")
    return out


def tag_rule_problems(sh, ps1):
    """T-45 (#142): TAG_RULE_CASES answered alike by the three spellings of "is a release tag"; [] when they are.

    install.sh's `is_release_tag` is cut out and RUN; upkeep.py's is imported by path; install.ps1's `Test-ReleaseTag`
    is READ, and its patterns applied with Python's `re` the way .NET reads them -- which holds only while each pattern
    is the ASCII class `[0-9]` (never `\\d`, which takes any script's digits in both engines) and ends in `\\z` (`$`
    lets a trailing newline through in both): `\\z` becomes Python's `\\Z`, the same end of the string.
    """
    import importlib.util
    out, names = [], [name for name, _ in TAG_RULE_CASES]
    answers = {}
    functions, missing = cut_functions(sh, ("is_release_tag",))
    bash, why = find_bash()
    if missing:
        out.append("install.sh: no `is_release_tag() { ... }` -- the release-tag rule cannot be run")
    elif not bash:
        out.append(f"{why} -- install.sh's release-tag rule cannot be run, and unrun is not agreed")
    else:
        script = functions + "".join(f"if is_release_tag {bash_literal(name)}; then echo '{i} yes'; "
                                     f"else echo '{i} no'; fi\n" for i, name in enumerate(names))
        r = subprocess.run([bash, "-s"], input=script.encode("utf-8"), capture_output=True)
        got = dict(line.split() for line in r.stdout.decode("utf-8", "replace").splitlines() if " " in line)
        answers["install.sh"] = [got.get(str(i)) == "yes" if str(i) in got else None for i in range(len(names))]
    try:
        spec = importlib.util.spec_from_file_location("autosound_upkeep_rule", UPKEEP)
        upkeep = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(upkeep)
        answers["upkeep.py"] = [bool(upkeep.is_release_tag(name)) for name in names]
    except Exception as exc:  # noqa: BLE001 -- a module that cannot answer is the finding, said with its reason
        out.append(f"upkeep.py: no is_release_tag to ask ({type(exc).__name__}: {exc})")
    fn = re.search(r"^function Test-ReleaseTag \{.*?^\}", ps1, re.M | re.S)
    patterns = re.findall(r"-cmatch '([^']*)'", fn.group(0)) if fn else []
    shapes_bad = [p for p in patterns if "\\d" in p or "[0-9]" not in p or not p.startswith("^") or not p.endswith("\\z")]
    if not fn or not patterns:
        out.append("install.ps1: no `function Test-ReleaseTag` with its `-cmatch` patterns -- the rule cannot be read")
    elif shapes_bad or any(op != "cmatch" for op in re.findall(r"-(\w*match)\b", fn.group(0))):
        out.append("install.ps1 Test-ReleaseTag: every pattern must be `-cmatch` (case kept), start in `^`, use the "
                   "ASCII class [0-9] and end in \\z, or .NET does not read it as this check does -- "
                   + ", ".join(shapes_bad or ["a match that is not -cmatch"]))
    else:
        compiled = [re.compile(p[:-2] + "\\Z") for p in patterns]
        answers["install.ps1"] = [any(c.search(name) for c in compiled) for name in names]
    for i, (name, want) in enumerate(TAG_RULE_CASES):
        said = {where: got[i] for where, got in answers.items()}
        if any(v != want for v in said.values()):
            out.append(f"the release-tag rule answers {name!r} " + ", ".join(f"{k} {v}" for k, v in said.items())
                       + f" -- want {want} (T-45)")
    return out


def selection_problems(sh, ps1):
    """T-37 (#142): install.sh's `pick_method_ref` RUN with a `git` that has no network; [] when it answers right.

    No tag readable and none named is a stop, exit 1, with nothing on stdout -- an empty `ls-remote` installed an
    unchecked `main`, and moved a verified copy onto it on a re-run. A named branch goes on, said UNSIGNED; a named
    release needs no network to be picked; and with tags readable the newest stable release wins whatever else the
    remote offers. The ref is all that reaches stdout, since the caller takes it with $(...). The call sites in both
    installers, and install.ps1's mirror, are READ: no `main` to fall back on, no app spec without a tag.
    """
    import json
    import tempfile
    # The stop is `stop` (#142): it writes the receipt, here into a temp XDG_DATA_HOME, under the call's own `set -u`.
    functions, missing = cut_functions(sh, ("say", "warn", "have", "on_mac", "runs_ok", "usable", "json_str",
                                            "write_receipt", "stop", "is_release_tag", "newest_on_channel",
                                            "pick_method_ref"))
    if missing:
        return [f"install.sh: no `{name}() {{ ... }}` -- the method's tag pick cannot be run" for name in missing]
    bash, why = find_bash()
    if not bash:
        return [f"{why} -- install.sh's tag pick cannot be run, and unrun is not agreed"]
    out = []
    tmp = tempfile.mkdtemp(prefix="autosound_pick_")
    try:
        stub_dir, tags = Path(tmp, "stub-git"), Path(tmp, "tags")
        stub_dir.mkdir()
        (stub_dir / "git").write_bytes(NO_NETWORK_GIT)
        (stub_dir / "git").chmod(0o755)
        tags.write_bytes("".join(t + "\n" for t in SELECTION_TAGS).encode("utf-8"))
        cases = (("", None, 0, 1, None, ("could not read the method's release tags", "nothing was installed"), ()),
                 ("", None, 128, 1, None, ("could not read the method's release tags", "nothing was installed"), ()),
                 ("main", None, 0, 0, "main", ("UNSIGNED",), ()),
                 ("v3.0.33", None, 128, 0, "v3.0.33", (), ("UNSIGNED",)),
                 ("", tags, 0, 0, "v3.1.10", (), ("UNSIGNED",)))
        for i, (given, offered, stub_rc, want_rc, want_ref, words, not_words) in enumerate(cases):
            script = (f'set -euo pipefail\nexport PATH="$(cd "{stub_dir.as_posix()}" && pwd)":"/usr/bin:$PATH"\n'
                      'SKILL_REPO="https://github.com/ayukhno/autosound-tuning-skill.git"\nSKILL_TAG_GLOB="v3.*"\n'
                      + functions + f'ref="$(pick_method_ref "{given}")" || exit $?\nprintf "REF=[%s]\\n" "$ref"\n')
            data = Path(tmp, f"data-{i}")
            env = dict(os.environ, STUB_RC=str(stub_rc), STUB_TAGS=offered.as_posix() if offered else "",
                       HOME=tmp, XDG_DATA_HOME=str(data))
            r = subprocess.run([bash, "-s"], input=script.encode("utf-8"), capture_output=True, env=env)
            got_out = r.stdout.decode("utf-8", "replace")
            got_err = r.stderr.decode("utf-8", "replace")
            want_out = f"REF=[{want_ref}]\n" if want_ref is not None else ""
            receipt = data / "autosound" / "install-receipt.json"
            try:
                status = json.loads(receipt.read_text(encoding="utf-8-sig")).get("status") if receipt.exists() else None
            except ValueError as exc:
                status = f"unreadable ({exc})"
            want_status = "stopped" if want_rc == 1 else None
            if (r.returncode != want_rc or got_out != want_out or any(w not in got_err for w in words)
                    or any(w in got_err for w in not_words) or status != want_status):
                out.append(f"install.sh pick_method_ref {given or '(no --skill-ref)'}"
                           f"{' with ' + ' '.join(SELECTION_TAGS) if offered else ''}, ls-remote exit {stub_rc}: "
                           f"exit {r.returncode}, stdout {got_out.strip()!r}, receipt {status!r}, want {want_rc} and "
                           f"{want_out.strip()!r}"
                           + (f" saying {' + '.join(map(repr, words))}" if words else "")
                           + (f" and never {' + '.join(map(repr, not_words))}" if not_words else "")
                           + (f", a receipt saying {want_status!r} (#142)" if want_status else ", no receipt")
                           + f" -- stderr {got_err.strip()[-200:]!r} (T-37)")
    except OSError as exc:
        out.append(f"the tag pick's fixtures could not be made ({exc}) -- unrun is not agreed")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    stop_ps1 = ("could not read the method's release tags (no network?) -- nothing was installed or changed for the "
                "method; run again when GitHub answers, or name a tag with -SkillRef")
    read = (("install.sh", 'SKILL_REF="$(pick_method_ref "$SKILL_REF")" || stop $?', True),
            ("install.sh", 'SKILL_REF="main"', False),
            ("install.sh", "could not read the app's release tags (no network?)", True),
            ("install.ps1", "$SkillRef = Select-MethodRef $SkillRef", True),
            ("install.ps1", stop_ps1, True),
            ("install.ps1", '$SkillRef = "main"', False),
            ("install.ps1", "could not read the app's release tags (no network?)", True))
    texts = {"install.sh": sh, "install.ps1": ps1}
    wrong = [f"{where} {'lacks' if must else 'still has'} {needle!r}" for where, needle, must in read
             if (needle in texts[where]) != must]
    wrong += [f"{where}: the app's spec without a tag ({m.group(0)!r}) -- uv takes the default branch, unchecked"
              for where, pattern in (("install.sh", r"git\+\$\{TCC_REPO\}(?!@)"), ("install.ps1", r"git\+\$TccRepo(?!@)"))
              for m in re.finditer(pattern, texts[where])]
    # install.ps1's mirror is only read: it gives back a name it was given or read, or $null -- never one of its own.
    pick_ps1 = re.search(r"^function Select-MethodRef \{.*?^\}", ps1, re.M | re.S)
    if not pick_ps1 or not re.search(r"return \$null\s*\}\Z", pick_ps1.group(0)) or re.search(r"[\"']main[\"']",
                                                                                               pick_ps1.group(0)):
        wrong.append("install.ps1 Select-MethodRef does not end in `return $null`, or names `main` itself")
    if wrong:
        out.append("the installers still have a way to an unchecked `main` or default branch: " + "; ".join(wrong)
                   + " (T-37)")
    return out


def checkout_problems(sh, ps1):
    """T-45 (#142): install.sh's `checkout_method` RUN against a repository made here; [] when a copy is the tag it
    checked.

    The remote holds v3.0.64 signed by this test's author key, a branch of the same name on a later commit (`git clone
    --branch` took the branch, and the check then read the tag), v3.0.66 unsigned and v3.0.67 signed on that later
    commit, and `main`. A new copy is the tag's commit, detached, with `origin` set; an update lands on its tag; a tag
    that does not check out leaves nothing; a named branch is checked out, said UNSIGNED. A checkout that did not land
    (a `git` whose checkout does nothing) removes a new copy and puts an update back where it was, exit 3 either way.
    A folder already at the path that is not a checkout is left exactly as it is. An update that cannot be made -- its
    tag cannot be fetched, or the copy's local changes cannot be kept -- leaves the copy where it was and answers 1,
    which both installers' update paths stop on, as on a failed new copy (#142, R32). install.ps1's mirror is READ.
    """
    import tempfile
    functions, missing = cut_functions(sh, ("say", "warn", "pretty", "run", "is_release_tag", "settled_by_name",
                                            "verify_tag", "keep_local", "head_is", "checkout_method"))
    if missing:
        return [f"install.sh: no `{name}() {{ ... }}` -- the method's checkout cannot be run" for name in missing]
    bash, why = find_bash()
    if not bash:
        return [f"{why} -- install.sh's checkout cannot be run, and unrun is not agreed"]
    tmp = tempfile.mkdtemp(prefix="autosound_checkout_")
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
               GIT_COMMITTER_EMAIL="t@t", GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1",
               GNUPGHOME=os.path.join(tmp, "gnupg"))
    env.pop("AUTOSOUND_SKIP_TAG_VERIFY", None)

    def git(*args, check=True):
        r = subprocess.run(["git", *args], env=env, capture_output=True, text=True)
        if check and r.returncode:
            raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()[:200]}")
        return r.stdout.strip()
    out = []
    try:
        os.makedirs(env["GNUPGHOME"], mode=0o700)
        key = os.path.join(tmp, "author")
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "author", "-f", key], env=env,
                       capture_output=True, check=True)
        author = " ".join(Path(key + ".pub").read_text().split()[:2])
        origin = os.path.join(tmp, "origin")
        git("init", "-q", origin)
        Path(origin, "a").write_text("a\n")
        git("-C", origin, "add", "a")
        git("-C", origin, "commit", "-q", "-m", "a")
        signed = ("-C", origin, "-c", "gpg.format=ssh", "-c", f"user.signingkey={key}.pub", "tag", "-s")
        git(*signed, "v3.0.64", "-m", "signed")
        git("-C", origin, "tag", "-a", "v3.0.66", "-m", "unsigned")
        Path(origin, "a").write_text("a\nb\n")
        git("-C", origin, "commit", "-q", "-am", "b")
        git(*signed, "v3.0.67", "-m", "signed")
        first, later = git("-C", origin, "rev-parse", "v3.0.64^{commit}"), git("-C", origin, "rev-parse", "HEAD")
        git("-C", origin, "update-ref", "refs/heads/v3.0.64", later)
        git("-C", origin, "update-ref", "refs/heads/main", later)
        stub_dir = Path(tmp, "no-checkout")
        stub_dir.mkdir()
        (stub_dir / "git").write_bytes(NO_CHECKOUT_GIT)
        (stub_dir / "git").chmod(0o755)
        occupied = Path(tmp, "occupied")
        occupied.mkdir()
        (occupied / "mine.txt").write_text("somebody's\n")
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        shutil.rmtree(tmp, ignore_errors=True)
        return [f"the checkout's fixtures could not be made ({exc}) -- unrun is not agreed"]
    url = Path(origin).as_uri()

    def run(where, ref, stub=False):
        first_on_path = f'"$(cd "{stub_dir.as_posix()}" && pwd)":' if stub else ""
        script = ('REAL_GIT="$(command -v git)"; export REAL_GIT\n'
                  f'export PATH={first_on_path}"/usr/bin:$PATH"\n' + functions
                  + f'DRY_RUN=0\nAUTOSOUND_SKIP_TAG_VERIFY=""\nSKILL_SIGNING_PRINCIPAL=author\n'
                  f'SKILL_SIGNING_KEY="{author}"\nSKILL_SIGNED_FROM=v3.0.64\nSKILL_REPO="{url}"\n'
                  f'checkout_method "{Path(where).as_posix()}" "{ref}" "the method"\n')
        r = subprocess.run([bash, "-s"], input=script.encode("utf-8"), capture_output=True, env=env)
        return r.returncode, (r.stdout + r.stderr).decode("utf-8", "replace")

    def head(where):
        return git("-C", where, "rev-parse", "--verify", "--quiet", "HEAD", check=False) if os.path.isdir(where) else ""

    def the_tag(where, tag):
        """`where` is a copy detached on `tag`'s commit, the tag in its refs/tags, `origin` the method's remote. Asked of
        the refs, not of `describe`: fetch brings along any tag on the same commit (v3.0.66 here), and `describe`
        names whichever is newer."""
        at = git("-C", where, "rev-parse", "--verify", "--quiet", f"refs/tags/{tag}^{{commit}}", check=False)
        return (bool(at) and head(where) == at
                and not git("-C", where, "symbolic-ref", "--quiet", "HEAD", check=False)
                and git("-C", where, "remote", "get-url", "origin", check=False) == url)

    def where_is(where):
        if not os.path.isdir(os.path.join(where, ".git")):
            return "no copy"
        branch = git("-C", where, "symbolic-ref", "--quiet", "--short", "HEAD", check=False)
        return (f"HEAD {head(where)[:12]} ({git('-C', where, 'describe', '--tags', '--always', check=False)}"
                f"{', on branch ' + branch if branch else ', detached'}"
                f", origin {git('-C', where, 'remote', 'get-url', 'origin', check=False) or 'none'})")

    copy = os.path.join(tmp, "copy")
    steps = (
        ("a new copy of v3.0.64, a branch of that name on another commit", copy, "v3.0.64", False, 0,
         ("signed by the skill's author",), lambda: head(copy) == first and the_tag(copy, "v3.0.64")),
        ("that copy updated to v3.0.67", copy, "v3.0.67", False, 0, ("signed by the skill's author",),
         lambda: head(copy) == later and the_tag(copy, "v3.0.67")),
        ("that copy updated to v3.0.64 by a checkout that does not land", copy, "v3.0.64", True, 3,
         ("did not take",), lambda: head(copy) == later),
        ("a new copy of v3.0.66, unsigned", os.path.join(tmp, "unsigned"), "v3.0.66", False, 2,
         ("does not check out",), lambda: not os.path.exists(os.path.join(tmp, "unsigned"))),
        ("a new copy of the branch main, named", os.path.join(tmp, "branch"), "main", False, 0, ("UNSIGNED",),
         lambda: head(os.path.join(tmp, "branch")) == later),
        ("a new copy of v3.0.64 by a checkout that does not land", os.path.join(tmp, "stuck"), "v3.0.64", True, 3,
         ("removed",), lambda: not os.path.exists(os.path.join(tmp, "stuck"))),
        ("a new copy into a folder that is there and is not a checkout", str(occupied), "v3.0.64", False, 1, (),
         lambda: sorted(os.listdir(occupied)) == ["mine.txt"]),
        # R32 (#142): an update that cannot be made is a stop, the copy where it was -- it was a warning, and the run
        # ended "Installed." on the old version.
        ("that copy updated to v3.0.99, a tag its remote does not have", copy, "v3.0.99", False, 1,
         ("could not fetch v3.0.99", "nothing was changed"), lambda: head(copy) == later),
        ("that copy, changed by hand, updated to v3.0.64 when the change cannot be kept", copy, "v3.0.64", False, 1,
         ("cannot be kept automatically",),
         lambda: head(copy) == later and Path(copy, "a").read_text() == "a\nb\nmine\n",
         lambda: Path(copy, "a").write_text("a\nb\nmine\n")),
    )
    for what, where, ref, stub, want_rc, words, state_ok, *prepare in steps:
        for made in prepare:
            made()
        rc, said = run(where, ref, stub)
        if rc != want_rc or any(w not in said for w in words) or not state_ok():
            out.append(f"install.sh checkout_method, {what}: exit {rc}, {where_is(where)} -- want exit {want_rc}"
                       + (f", saying {' + '.join(map(repr, words))}" if words else "")
                       + f" -- said {said.strip()[-220:]!r} (T-45)")
    shutil.rmtree(tmp, ignore_errors=True)
    # install.ps1's mirror, READ: a new copy made the same way, HEAD held to the tag, and every failed copy a stop.
    sync = re.search(r"^function Sync-MethodCheckout \{.*?^\}", ps1, re.M | re.S)
    body = sync.group(0) if sync else ""
    lacking = [n for n in ("init --quiet $Dir", "remote add origin $SkillRepo", "fetch --quiet --depth 1 origin $spec",
                           "Test-HeadIs $Dir $want", "$script:NotTheTag = $true") if n not in body]
    lacking += [f"a stop after {what}" for what, pattern in (
        ("a failed new copy", r"elseif \(-not \$cloned\) \{[^{}]*Stop-Installer 1; return"),
        ("an update that did not land", r"if \(\$script:NotTheTag\) \{[^{}]*Stop-Installer 1; return"),
        ("an update that could not be made (R32)", r"if \(-not \$updated\) \{[^{}]*Stop-Installer 1; return"))
        if not re.search(pattern, ps1)]
    if 'if [ "$_co_rc" = 1 ]; then stop 1 "update failed -- see above"; fi' not in sh:
        lacking.append("install.sh: no stop after an update that could not be made (R32)")
    lacking += [f"{name} still clones by --branch" for name, text in (("install.sh", sh), ("install.ps1", ps1))
                if re.search(r"clone --quiet --branch", text)]
    if lacking:
        out.append("install.ps1's checkout is not the tag it checked -- " + "; ".join(lacking) + " (T-45)")
    return out


def exit_contract_problems(sh, ps1):
    """#142 (T-44, J6a item 4): the exit table and the receipt; [] when both installers keep them.

    install.sh's `finish` and `stop` are cut out and RUN, each into a temp XDG_DATA_HOME under `set -euo pipefail`, with
    `going_ahead`'s trap in place: nothing missing ends 0 with `Installed.`, a missing part 3 with `Installed, NOT
    ready: <names>` (a part named twice is named once), a stop 1 -- and every one of them writes a receipt that parses
    as JSON with RECEIPT_FIELDS in that order, `status` and `missing` as the run ended, even with a quote, a backslash
    and a tab in the engine's line: once with a python3 to build it, once with the shell's own builder. `plugin-ready`
    is asked for only on a ready install; a dry run writes nothing and ends 0. A declined "Go ahead?" (`consent`, no
    terminal and no --yes) is a stop, 1; a run that fails under `set -e` -- with 1, or with a 3 of its own -- or on an
    unbound variable (bash 3.2 hands the trap 0) ends 1, and one that ends where no trap sees it says `stopped`: an
    earlier run's `ready` never stands over it. install.ps1
    is READ: Stop-Installer writes `stopped`, a declined "Go ahead?" stops with 1 and the receipt says `stopped` right
    after it, the end writes its receipt and then stops with 3 under `-not $ok`, `plugin-ready` is called once, under
    `$ok`, Write-Receipt's fields are RECEIPT_FIELDS in order, Add-Missing names a part once. Every part that is not
    ready goes through `missing` / `Add-Missing`, every stop through `stop` -- no `exit 1` and no `ok=0` left in
    install.sh -- the beta channel's copy not on this run's candidate is missing in both (R38), and the installers'
    version is plugin.json's.
    """
    import hashlib
    import json
    import tempfile
    out = []
    version, err = one(r'^INSTALLER_VERSION="([^"]+)"', sh, "INSTALLER_VERSION", "install.sh")
    ps_version, err_ps = one(r'^\$InstallerVersion\s*=\s*"([^"]+)"', ps1, "$InstallerVersion", "install.ps1")
    out.extend(e for e in (err, err_ps) if e)
    try:
        manifest = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
    except (OSError, ValueError, KeyError) as exc:
        manifest = None
        out.append(f".claude-plugin/plugin.json: no version to hold the installers to ({exc})")
    if version and ps_version and manifest and len({version, ps_version, manifest}) != 1:
        out.append(f"the installers' version differs -- install.sh INSTALLER_VERSION {version!r}, install.ps1 "
                   f"$InstallerVersion {ps_version!r}, plugin.json {manifest!r}; the release's bookkeeping moves all "
                   f"three (#142)")

    # install.sh, READ: a stop is `stop`, a part not ready is `missing`, and `finish` is the last statement.
    lines = sh.splitlines()
    code = [(n, line) for n, line in enumerate(lines, 1) if line.strip() and not line.lstrip().startswith("#")]
    out.extend(f"install.sh:{n}: `exit 1` -- a stop goes through `stop 1 \"...\"`, which writes the receipt (#142)"
               for n, line in code if re.search(r"(?:^|[;&|{]|\bthen|\belse|\bdo)\s*exit 1\b", line))
    out.extend(f"install.sh:{n}: `{m.group(0)}` -- a part that is not ready goes through `missing <name>`, the one "
               f"record `finish` reads (#142)" for n, line in code for m in [re.search(r"\bok=[01]\b", line)] if m)
    if not code or code[-1][1].strip() != "finish":
        out.append(f"install.sh: the last statement is {code[-1][1].strip()[:60] if code else 'nothing'!r}, not "
                   f"`finish` -- the verdict, the receipt and the exit code are the run's last word (#142)")
    names_sh = [n for n in MISSING_NAMES if not re.search(r'\bmissing (?:"' + re.escape(n) + r'"|' + re.escape(n)
                                                           + r')\s*(?:;|$)', sh, re.M)]
    names_ps = [n for n in MISSING_NAMES if f'Add-Missing "{n}"' not in ps1]
    if names_sh or names_ps:
        out.append("a part that is not ready is not named the same in both installers -- "
                   + "; ".join([f"install.sh has no `missing {n}`" for n in names_sh]
                               + [f"install.ps1 has no `Add-Missing \"{n}\"`" for n in names_ps]) + " (#142)")
    # The consent, and the moment the run goes ahead (Task 8's review): `consent`, then `going_ahead`, one after the
    # other at the top level -- from there the receipt says `stopped` until the run's own end writes how it ended.
    top = [line.rstrip() for _, line in code if not line[:1].isspace()]
    if "consent" not in top or top.index("consent") + 1 >= len(top) or top[top.index("consent") + 1] != "going_ahead":
        out.append("install.sh: the top level does not run `consent` and then `going_ahead`, one after the other -- an "
                   "earlier run's receipt stands over a run that ends neither in `stop` nor in `finish` (#142)")
    # R38: the beta channel's copy, when it is not on this run's candidate -- the candidates unread, or the update refused
    # -- counts missing in its own block, in both installers; the checks count a copy that is not there at all.
    beta_sh = re.search(r'^if \[ "\$CHANNEL" = "beta" \]; then\n.*?^fi\n', sh, re.M | re.S)
    beta_ps = re.search(r'^if \(\$Channel -eq "beta"\) \{\n.*?^\}\n', ps1, re.M | re.S)
    if (not beta_sh or beta_sh.group(0).count('missing "the beta copy"') != 2
            or not beta_ps or beta_ps.group(0).count('Add-Missing "the beta copy"') != 2):
        out.append("the beta channel's copy is not counted missing in both installers' beta block when it is not on "
                   "this run's candidate -- the candidates unread, or its update refused; it ended 0 (R38, #142)")

    # install.ps1, READ.
    stop_fn = re.search(r"^function Stop-Installer \{\n.*?^\}$", ps1, re.M | re.S)
    write_fn = re.search(r"^function Write-Receipt \{\n.*?^\}$", ps1, re.M | re.S)
    block = re.search(r"\[ordered\]@\{(.*?)\}", write_fn.group(0), re.S) if write_fn else None
    keys = tuple(re.findall(r"(\w+)\s*=", block.group(1))) if block else ()
    stops = list(re.finditer(r"^\s*Stop-Installer (\d+); return\s*$", ps1, re.M))
    last = stops[-1] if stops else None
    after = [ln.strip() for ln in ps1[last.end():].splitlines() if ln.strip() and not ln.strip().startswith("#")] \
        if last else []
    receipts = [m.start() for m in re.finditer(r"^\s*Write-Receipt\b", ps1, re.M)]
    ps_wrong = []
    if not stop_fn or not re.search(r'if \(\$Code -eq 1\) \{ Write-Receipt "stopped" \}', stop_fn.group(0)):
        ps_wrong.append('Stop-Installer does not write `Write-Receipt "stopped"` for a stop (code 1)')
    if keys != RECEIPT_FIELDS:
        ps_wrong.append(f"Write-Receipt's [ordered] fields are {list(keys)}, not {list(RECEIPT_FIELDS)}")
    if not last or last.group(1) != "3" or not re.search(
            r"if \(-not \$ok\b[^\n{]*\)\s*\{\s*\n\s*Stop-Installer 3; return\s*\n\s*\}", ps1):
        ps_wrong.append("its end does not stop with `Stop-Installer 3; return` under `if (-not $ok ...)`")
    elif any(ln not in ("}", "if ($AutosoundTranscriptOn) { try { Stop-Transcript | Out-Null } catch { $null = $_ } }")
             for ln in after):
        ps_wrong.append(f"something runs after its `Stop-Installer 3`: {after[:3]}")
    if not last or not receipts or receipts[-1] > last.start():
        ps_wrong.append("its end does not write the receipt before its `Stop-Installer 3`")
    if not re.search(r"if \(\$ok\b[^\n{]*\)\s*\{[^}]*plugin-ready --root", ps1):
        ps_wrong.append("`plugin-ready` is not under `if ($ok ...)`")
    ready_calls = [ln for ln in ps1.splitlines() if "plugin-ready --root" in ln and not ln.lstrip().startswith("#")]
    if len(ready_calls) != 1:
        ps_wrong.append(f"`plugin-ready --root` is called {len(ready_calls)} times -- once, under `if ($ok ...)`")
    if re.search(r"\$ok\s*=\s*\$false", ps1):
        ps_wrong.append("`$ok = $false` is still set beside the list -- a part not ready goes through Add-Missing")
    # The consent (Task 8's review): declined -- or no terminal and no -Yes -- it is a stop, 1 (it ended 0, which a
    # script read as ready), and once given the receipt says `stopped` until the end writes how the run ended.
    if not re.search(r'Ask "Go ahead\?" "n"\)\) \{[^{}]*Stop-Installer 1; return', ps1):
        ps_wrong.append('a declined "Go ahead?" does not stop with `Stop-Installer 1; return`')
    asked, first_dir = ps1.find('Ask "Go ahead?"'), ps1.find("New-Item -ItemType Directory -Force -Path $LocalBin")
    if not any(asked < m.start() < first_dir for m in re.finditer(r'^Write-Receipt "stopped"\s*$', ps1, re.M)):
        ps_wrong.append('the receipt does not say `stopped` (`Write-Receipt "stopped"`, at the top level) between the '
                        'consent and the first install step -- an earlier run\'s receipt stands over one that dies')
    add_fn = re.search(r"^function Add-Missing \{\n.*?^\}$", ps1, re.M | re.S)
    if not add_fn or "-notcontains $Name" not in add_fn.group(0):
        ps_wrong.append("Add-Missing adds a name already listed -- a part is named once, as install.sh's `missing`")
    if ps_wrong:
        out.append("install.ps1's end is not the exit contract: " + "; ".join(ps_wrong) + " (#142)")

    # install.sh, RUN.
    functions, missing = cut_functions(sh, ("say", "warn", "have", "on_mac", "runs_ok", "usable", "pretty", "ask",
                                            "json_str", "write_receipt", "is_missing", "missing", "stop", "finish",
                                            "consent", "going_ahead", "unplanned_end"))
    if missing:
        return out + [f"install.sh: no `{name}() {{ ... }}` -- the exit contract cannot be run (#142)"
                      for name in missing]
    bash, why = find_bash()
    if not bash:
        return out + [f"{why} -- install.sh's exit contract cannot be run, and unrun is not agreed"]
    tmp = tempfile.mkdtemp(prefix="autosound_exit_")

    def run(case, body, builder, dry, plugin, before=None):
        home = Path(tmp, case)
        home.mkdir()
        data, mark = home / "data", home / "plugin-ready-calls"
        if before is not None:                          # an earlier run's receipt, there before this one
            (data / "autosound").mkdir(parents=True)
            (data / "autosound" / "install-receipt.json").write_text(json.dumps(before), encoding="utf-8")
        # A file, so $0 is one: the receipt's sha256 is this script's, as it is install.sh's when it runs as a file.
        # Under the installer's own `set -euo pipefail`; `tty_ok` answers "no terminal", so `ask` takes its default.
        text = ('set -euo pipefail\nexport PATH="/usr/bin:$PATH"\n' + functions + FAKE_PYTHON3
                + "tty_ok() { return 1; }\n" + ("usable() { return 1; }\n" if builder == "shell" else "")
                + f'DRY_RUN={dry}\nASSUME_YES=0\nMODE=terminal\nSKILL_REF=v3.1.2\nINSTALLER_VERSION="{version}"\n'
                + f"ENGINE_DID={bash_literal(HOSTILE_ENGINE)}\nMISSING=\"\"\nTCC_REFUSED=\"\"\n"
                + f'SKILL_HOME="{home.as_posix()}/skill"\nSKILL_BETA_SRC="{home.as_posix()}/beta"\n'
                + (f'PLUGIN_ROOT="{home.as_posix()}/plugin"\nPLUGIN_VERSION=3.1.2\n' if plugin else 'PLUGIN_ROOT=""\n')
                + body).encode("utf-8")
        script = home / "install.sh"
        script.write_bytes(text)
        env = dict(os.environ, HOME=str(home), XDG_DATA_HOME=str(data), PLUGIN_MARK=mark.as_posix(),
                   PYTHON_FOR_TEST=Path(sys.executable).as_posix(), MSYS2_ARG_CONV_EXCL="*", MSYS_NO_PATHCONV="1")
        r = subprocess.run([bash, script.as_posix()], capture_output=True, env=env)
        said = r.stdout.decode("utf-8", "replace") + r.stderr.decode("utf-8", "replace")
        path = data / "autosound" / "install-receipt.json"
        receipt, unreadable = None, ""
        if path.exists():
            try:
                receipt = json.loads(path.read_text(encoding="utf-8-sig"))
            except ValueError as exc:
                unreadable = f"not JSON ({exc}): {path.read_bytes()[:160]!r}"
        calls = mark.read_text(encoding="utf-8").count("plugin-ready") if mark.exists() else 0
        return r.returncode, said, receipt, unreadable, calls, hashlib.sha256(text).hexdigest()

    flat = "".join(ch for ch in HOSTILE_ENGINE if ord(ch) >= 32)
    # An earlier run's receipt: this run's end -- whatever it is -- must not leave it standing.
    earlier = {"installer": "install.sh", "status": "ready", "missing": [], "at": "2026-10-01T00:00:00Z"}
    # Every run goes ahead as install.sh's does -- `going_ahead` after the consent -- so its trap is there when `stop` and
    # `finish` end it; a dry run passes `consent` without a question.
    go = "going_ahead\n"
    # (case, body, builder, dry run, --plugin, exit, words, never, status (None: no receipt), missing, plugin-ready
    # [, the receipt there before])
    cases = (("ready", go + "finish\n", "python3", "0", True, 0, ("Installed.",), ("NOT ready",), "ready", [], 1),
             ("not-ready", go + "MISSING=numpy\nfinish\n", "python3", "0", True, 3, ("Installed, NOT ready: numpy",
              "set-up note comes back"), (), "not ready", ["numpy"], 0, earlier),
             ("two-parts", go + 'missing numpy\nmissing "Claude Code"\nfinish\n', "python3", "0", False, 3,
              ("Installed, NOT ready: numpy, Claude Code",), (), "not ready", ["numpy", "Claude Code"], 0),
             ("the-same-part-twice", go + 'missing "the beta copy"\nmissing "the beta copy"\nfinish\n', "python3", "0",
              False, 3, ("Installed, NOT ready: the beta copy\n",), ("the beta copy, the beta copy",), "not ready",
              ["the beta copy"], 0),
             ("a-stop", go + 'stop 1 "could not read the tags -- nothing was installed"\nsay "past the stop"\n',
              "python3", "0", False, 1, ("could not read the tags -- nothing was installed",),
              ("past the stop", "Installed", "stopped (exit"), "stopped", [], 0),
             ("ready-no-python3", go + "finish\n", "shell", "0", True, 0, ("Installed.",), ("NOT ready",), "ready", [],
              1),
             ("not-ready-no-python3", go + 'missing numpy\nmissing TCC\nfinish\n', "shell", "0", True, 3,
              ("Installed, NOT ready: numpy, TCC",), (), "not ready", ["numpy", "TCC"], 0),
             ("a-stop-no-python3", go + 'stop 1 "stopped: no tag"\n', "shell", "0", False, 1, ("stopped: no tag",), (),
              "stopped", [], 0),
             ("a-dry-run", "consent\n" + go + "MISSING=numpy\nfinish\n", "python3", "1", True, 0,
              ("Nothing was installed",), ("NOT ready", "Go ahead"), None, None, 0),
             ("a-stop-in-a-dry-run", "consent\n" + go + 'stop 1 "stopped: no tag"\n', "python3", "1", False, 1,
              ("stopped: no tag",), (), None, None, 0),
             # Task 8's review: a declined "Go ahead?" -- here no terminal and no --yes, which takes the default "n" --
             # is a stop, 1, nothing installed; it ended 0, which a script read as ready. Given, the run goes on.
             ("declined", "consent\n" + go + "finish\n", "python3", "0", False, 1,
              ("Nothing installed. Re-run when you want to.",), ("Installed",), "stopped", [], 0, earlier),
             ("consented", "ASSUME_YES=1\nconsent\n" + go + "finish\n", "python3", "0", False, 0, ("Installed.",),
              ("Nothing installed",), "ready", [], 0, earlier),
             # ...and a run that ends neither in `stop` nor in `finish`: a failure under `set -e` is a stop, 1 -- also
             # when the failing command's own code is the table's 3 -- and the receipt says `stopped`; where no trap
             # sees the end (Ctrl-C under bash 3.2, a kill; here `exec`), it says `stopped` from going ahead on.
             ("a-failure", go + "missing numpy\nfalse\nfinish\n", "python3", "0", False, 1,
              ("stopped (exit 1) -- the lines above say where",), ("Installed",), "stopped", ["numpy"], 0, earlier),
             ("a-failure-coded-3", go + "missing numpy\nsh -c 'exit 3'\nfinish\n", "python3", "0", False, 1,
              ("stopped (exit 3) -- the lines above say where",), ("Installed",), "stopped", ["numpy"], 0, earlier),
             ("an-end-no-trap-sees", go + "missing numpy\nexec false\n", "python3", "0", False, 1, (), ("Installed",),
              "stopped", [], 0, earlier),
             # An unbound variable under `set -u`: bash 3.2 (macOS's) hands the trap $? = 0, and a trap that trusted it
             # ended the run 0 -- ready.
             ("an-unbound-variable", go + 'missing numpy\n: "$NOT_SET_ANYWHERE"\nfinish\n', "python3", "0", False, 1,
              ("unbound variable", "stopped (exit"), ("Installed",), "stopped", ["numpy"], 0, earlier))
    try:
        for case, body, builder, dry, plugin, want_rc, words, never, status, missing_want, want_calls, *before in cases:
            rc, said, receipt, unreadable, calls, sha = run(case, body, builder, dry, plugin, *before)
            wrong = []
            if rc != want_rc:
                wrong.append(f"exit {rc}, want {want_rc}")
            wrong += [f"never says {w!r}" for w in words if w not in said]
            wrong += [f"says {w!r}" for w in never if w in said]
            if calls != want_calls:
                wrong.append(f"plugin-ready asked for {calls} time(s), want {want_calls}")
            if unreadable:
                wrong.append(f"the receipt is {unreadable}")
            elif status is None and receipt is not None:
                wrong.append("a receipt was written")
            elif status is not None and receipt is None:
                wrong.append("no receipt was written")
            elif status is not None:
                want = {"installer": "install.sh", "installer_sha256": sha, "method_ref": "v3.1.2", "mode": "terminal",
                        "engine": HOSTILE_ENGINE if builder == "python3" else flat, "installer_version": version,
                        "status": status, "missing": missing_want}
                if tuple(receipt) != RECEIPT_FIELDS:
                    wrong.append(f"the receipt's fields are {list(receipt)}, not {list(RECEIPT_FIELDS)}")
                wrong += [f"the receipt's {k} is {receipt.get(k)!r}, want {v!r}" for k, v in want.items()
                          if receipt.get(k) != v]
                if not receipt.get("python") or not isinstance(receipt.get("python"), str):
                    wrong.append(f"the receipt's python is {receipt.get('python')!r}, want '<path> <version>'")
            if wrong:
                out.append(f"install.sh's exit contract, {case} ({builder} builds the receipt"
                           f"{', a dry run' if dry == '1' else ''}): " + "; ".join(wrong)
                           + f" -- said {said.strip()[-240:]!r} (#142)")
    except OSError as exc:
        out.append(f"the exit contract's fixtures could not be made ({exc}) -- unrun is not agreed")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return out


def main():
    sh, ps1, cmd = read(SH), read(PS1), read(CMD)
    problems, checked = [], []

    # 1. the SKILL repo each file installs from. Not "the only repo each file mentions" — they
    # legitimately name others (autosound-tcc, cli/cli for gh), and a first draft of this check
    # flagged those as drift. A checker outside its scope is the defect it is here to prevent.
    slugs = {}
    sh_repo, err = one(r'^SKILL_REPO="(\S+?)"', sh, "SKILL_REPO", "install.sh")
    if err:
        problems.append(err)
    elif sh_repo:
        slugs["install.sh"] = slug_of(sh_repo, "install.sh", problems)
    ps_repo, err = one(r'^\$SkillRepo\s*=\s*"(\S+?)"', ps1, "$SkillRepo", "install.ps1")
    if err:
        problems.append(err)
    elif ps_repo:
        slugs["install.ps1"] = slug_of(ps_repo, "install.ps1", problems)
    if len(set(v for v in slugs.values() if v)) > 1:
        problems.append("the installers install the method from different repos — "
                        + ", ".join(f"{k} → {v}" for k, v in sorted(slugs.items())))
    elif slugs and all(slugs.values()):
        checked.append(f"skill repo agrees ({next(iter(slugs.values()))})")

    # the TCC repo travels with them and drifts the same way
    sh_tcc, _ = one(r'^TCC_REPO="(\S+?)"', sh, "TCC_REPO", "install.sh")
    ps_tcc, _ = one(r'^\$TccRepo\s*=\s*"(\S+?)"', ps1, "$TccRepo", "install.ps1")
    if sh_tcc and ps_tcc:
        a, b = slug_of(sh_tcc, "install.sh", problems), slug_of(ps_tcc, "install.ps1", problems)
        if a and b and a != b:
            problems.append(f"TCC repo differs — install.sh {a} vs install.ps1 {b}")
        elif a and b:
            checked.append(f"TCC repo agrees ({a})")

    # 2. the supported-line glob, which is the whole point of naming it (inbox 5.3)
    sh_glob, err = one(r'^SKILL_TAG_GLOB="([^"]+)"', sh, "SKILL_TAG_GLOB", "install.sh")
    if err:
        problems.append(err)
    ps_glob, err = one(r'^\$SkillTagGlob\s*=\s*"([^"]+)"', ps1, "$SkillTagGlob", "install.ps1")
    if err:
        problems.append(err)
    if sh_glob and ps_glob:
        if sh_glob != ps_glob:
            problems.append(f"tag glob differs — install.sh {sh_glob!r} vs install.ps1 {ps_glob!r}")
        else:
            checked.append(f"tag glob agrees ({sh_glob})")

    # 2b. the app's supported line, added with SCR-054. It is `v*` where the skill's is `v3.*`,
    # and that difference is intentional -- so this checks the two files agree, not that the two
    # globs match each other.
    sh_tglob, err = one(r'^TCC_TAG_GLOB="([^"]+)"', sh, "TCC_TAG_GLOB", "install.sh")
    if err:
        problems.append(err)
    ps_tglob, err = one(r'^\$TccTagGlob\s*=\s*"([^"]+)"', ps1, "$TccTagGlob", "install.ps1")
    if err:
        problems.append(err)
    if sh_tglob and ps_tglob:
        if sh_tglob != ps_tglob:
            problems.append(f"app tag glob differs — install.sh {sh_tglob!r} vs "
                            f"install.ps1 {ps_tglob!r}")
        else:
            checked.append(f"app tag glob agrees ({sh_tglob})")

    # 2c. the beta channel's globs (hub RELEASE-CHANNEL.md §11, HUB-060): the same in both files, and
    # each is `beta-` + its line's stable glob -- a candidate from ANOTHER line arriving on the beta
    # channel would be a line change nobody asked for.
    for what, sh_name, ps_name, stable in (("skill", "SKILL_BETA_GLOB", "SkillBetaGlob", sh_glob),
                                            ("app", "TCC_BETA_GLOB", "TccBetaGlob", sh_tglob)):
        b_sh, err_a = one(rf'^{sh_name}="([^"]+)"', sh, sh_name, "install.sh")
        b_ps, err_b = one(rf'^\${ps_name}\s*=\s*"([^"]+)"', ps1, f"${ps_name}", "install.ps1")
        if err_a or err_b:
            problems.extend(e for e in (err_a, err_b) if e)
        elif b_sh != b_ps:
            problems.append(f"{what} beta glob differs — install.sh {b_sh!r} vs install.ps1 {b_ps!r}")
        elif stable and b_sh != f"beta-{stable}":
            problems.append(f"{what} beta glob {b_sh!r} is not `beta-` + the stable glob {stable!r}")
        else:
            checked.append(f"{what} beta glob agrees ({b_sh})")

    # 2d. the beta channel's ORDER: install.sh's function RUN on fixed names; install.ps1's READ.
    order = channel_order_problems(sh)
    if order:
        problems.extend(order)
    else:
        checked.append(f"install.sh picks the newest beta tag right in {len(CHANNEL_CASES)} cases (run)")
    missing = [shape for shape in PS1_CHANNEL_SHAPES if shape not in ps1]
    if missing:
        problems.append("install.ps1 Select-NewestOnChannel no longer carries " + ", ".join(missing))
    else:
        checked.append("install.ps1 carries the same tag shapes and sort key (read, not run)")
    # 2d'. the STABLE pick keeps release-shaped tags only (skill #108): a `v3.x` sorted above every release and,
    # being "not a release tag", was installed with no signature check. install.ps1 filters through the one rule.
    raw_sh = [i + 1 for i, line in enumerate(sh.splitlines()) if "sort -V | tail -1" in line]
    raw_ps = [m.start() for m in re.finditer(r"Sort-Object \{ \[version\]", ps1)
              if "Where-Object { Test-ReleaseTag $_ }" not in ps1[max(0, m.start() - 160):m.start()]]
    if raw_sh or raw_ps:
        problems.append("a stable tag pick takes any name the glob matches: "
                        + (f"install.sh `sort -V | tail -1` at line(s) {raw_sh}" if raw_sh else "")
                        + ("; " if raw_sh and raw_ps else "")
                        + (f"install.ps1 {len(raw_ps)} `Sort-Object {{ [version] }}` with no release-shape filter"
                           if raw_ps else "") + " (skill #108)")
    else:
        checked.append("the stable tag picks keep release-shaped tags only, in both installers (skill #108)")
    # 2d''. one release-tag rule (T-45), and no tag readable is no install (T-37).
    rule = tag_rule_problems(sh, ps1)
    if rule:
        problems.extend(rule)
    else:
        checked.append(f"one release-tag rule: install.sh's is_release_tag (run), upkeep.py's (imported) and "
                       f"install.ps1's Test-ReleaseTag (read, as .NET reads it) answer {len(TAG_RULE_CASES)} names "
                       f"alike (T-45)")
    picked = selection_problems(sh, ps1)
    if picked:
        problems.extend(picked)
    else:
        checked.append("install.sh's pick_method_ref stops, exit 1, when no release tag can be read and none is named "
                       "-- network down or refused -- installs a named branch said UNSIGNED, and picks v3.1.10 from "
                       f"{len(SELECTION_TAGS)} offered names (run); neither installer has a `main` or an untagged app "
                       "to fall back on (read) (T-37)")

    # 2e. the method's two checkouts (autosound-hub #145): the terminal's and the beta channel's. A
    # consumer runs the beta one BY PATH, so the two installers putting it in different places would
    # leave one platform's app looking for a copy that is not there.
    for what, sh_name, ps_name in (("terminal", "SKILL_SRC", "SkillSrc"),
                                   ("beta", "SKILL_BETA_SRC", "SkillBetaSrc")):
        p_sh, p_ps = checkout_paths(sh, ps1, sh_name, ps_name, problems)
        if p_sh and p_ps:
            if p_sh != p_ps:
                problems.append(f"the {what} checkout differs — install.sh {p_sh!r} vs install.ps1 {p_ps!r}")
            else:
                checked.append(f"the {what} checkout agrees (~/{p_sh})")

    # 3. install.cmd hardcodes the URL it fetches install.ps1 from; it must be THIS repo's, on main
    ps1url, err = one(r'^set "PS1URL=(\S+)"', cmd, "PS1URL", "install.cmd")
    if err:
        problems.append(err)
    elif ps1url:
        # Compare against the skill repo the OTHER two named. If we could not establish it, say so
        # and fail — a check whose input is missing must not report "no objection". That silent
        # degradation is exactly what let a hijacked PS1URL pass a first draft of this file.
        want = next(iter({v for v in slugs.values() if v}), None) if len(set(slugs.values())) == 1 else None
        if not want:
            problems.append("install.cmd PS1URL cannot be checked — the skill repo could not be "
                            "established from install.sh/install.ps1")
        elif not ps1url.endswith("/install.ps1"):
            problems.append(f"install.cmd PS1URL does not end in /install.ps1 — {ps1url}")
        elif f"/{want}/" not in ps1url:
            problems.append(f"install.cmd PS1URL is not {want} — {ps1url}")
        elif "/main/" in ps1url:
            # A moving branch is the thing HUB-030 removed: a broken `main` reaches every new
            # user instantly, a broken tag reaches nobody until the next one is cut.
            problems.append(f"install.cmd PS1URL still points at main — {ps1url}")
        else:
            checked.append(f"install.cmd fetches install.ps1 from {want}, by tag")

    # 4. the version-pin EXAMPLE. It is documentation, not a constant -- and that is exactly why it
    # drifted unseen: `install.sh` said `v3.0.3`, `install.ps1` said `v3.0.4`, `install.cmd` said
    # nothing, and every FAQ page copied the pair out of that help text (found 2026-08-26). The
    # example teaches the reader which two versions belong together, so a mismatched pair here
    # teaches the opposite of the thing the pairing exists for. Same versions in every file that
    # shows the example, and the skill/app versions quoted as ONE pair.
    ex_sh = set(re.findall(r"--skill-ref\s+(v[0-9.]+)", sh)) , set(re.findall(r"--tcc-ref\s+(v[0-9.]+)", sh))
    ex_ps = set(re.findall(r"-SkillRef\s+(v[0-9.]+)", ps1)), set(re.findall(r"-TccRef\s+(v[0-9.]+)", ps1))
    ex_cmd = set(re.findall(r"-SkillRef\s+(v[0-9.]+)", cmd)), set(re.findall(r"-TccRef\s+(v[0-9.]+)", cmd))
    for what, a, b in (("skill", ex_sh[0], ex_ps[0]), ("app", ex_sh[1], ex_ps[1])):
        if not a or not b:
            problems.append(f"the {what} version example is missing from "
                            f"{'install.sh' if not a else 'install.ps1'} — the pin example is part "
                            f"of what the triplet must agree on")
        elif len(a) > 1 or len(b) > 1:
            problems.append(f"the {what} version example is not one value — install.sh {sorted(a)}, "
                            f"install.ps1 {sorted(b)}")
        elif a != b:
            problems.append(f"the {what} version example differs — install.sh {a.pop()} vs "
                            f"install.ps1 {b.pop()}")
        else:
            v = a.pop()
            # install.cmd passes every option through to install.ps1 and lists them, so its own
            # example must name the same pair -- it is the file a Windows user double-clicks.
            c = ex_cmd[0] if what == "skill" else ex_cmd[1]
            if c and c != {v}:
                problems.append(f"the {what} version example in install.cmd is {sorted(c)}, "
                                f"not {v} like the other two")
            elif not c:
                problems.append(f"install.cmd shows no {what} version example — it lists the "
                                f"options it forwards, so it must show the same pair")
            else:
                checked.append(f"{what} version example agrees in all three ({v})")

    # 4b. install.ps1 stops without closing a one-liner user's window (see ps1_stop_problems).
    stops = ps1_stop_problems(ps1)
    if stops:
        problems.extend(stops)
    else:
        calls = len(re.findall(r"^\s*Stop-Installer \d+; return\s*$", ps1, re.M))
        checked.append(f"install.ps1 stops through Stop-Installer ({calls} calls, each with return), no bare exit")

    # 5. the default mode. `--terminal` is the opt-out in both, so both must default to tcc.
    if not re.search(r'^MODE="tcc"', sh, re.M):
        problems.append('install.sh: default MODE is no longer "tcc"')
    elif not re.search(r'\{\s*"terminal"\s*\}\s*else\s*\{\s*"tcc"\s*\}', ps1):
        problems.append('install.ps1: $Mode no longer defaults to "tcc" the way install.sh does')
    else:
        checked.append("both default to mode tcc (--terminal / -Terminal is the opt-out)")

    # 5a. the optional extras come only when asked (the user, 2026-09-16/17, issue #25): omp with
    # --with-omp / -WithOmp, gh with --github / -GitHub. A default flipped in one installer and not
    # the other installs a different set of things on a Mac than on a PC.
    if not re.search(r'^WANT_OMP=0$', sh, re.M):
        problems.append("install.sh: omp is no longer off by default (WANT_OMP=0)")
    elif not re.search(r'^\$WantOmp\s*=\s*\[bool\]\$WithOmp\b', ps1, re.M):
        problems.append("install.ps1: $WantOmp no longer comes from -WithOmp alone, the way install.sh's does")
    elif not re.search(r'^WANT_GITHUB="auto"$', sh, re.M) or not re.search(r'else \{ "auto" \}', ps1):
        problems.append('gh\'s default differs: install.sh WANT_GITHUB="auto" and install.ps1 "auto" (gh only with the flag, or already here)')
    else:
        checked.append("both install omp only with --with-omp / -WithOmp, and gh only with --github / -GitHub or when already here")

    # 5b. the PINNED uv version. Pinning is only worth anything while both sides pin the SAME
    # thing: two installers on two versions of a third-party bootstrap is the drift this file
    # exists to catch, and it would show up as "works on my machine" (HUB-031).
    uv_sh, err_a = one(r'^UV_VERSION="([0-9][0-9.]*)"', sh, "UV_VERSION", "install.sh")
    uv_ps, err_b = one(r'^\$UvVersion\s*=\s*"([0-9][0-9.]*)"', ps1, "$UvVersion", "install.ps1")
    if err_a or err_b:
        problems.append(err_a or err_b)
    elif uv_sh and uv_ps and uv_sh != uv_ps:
        problems.append(f"the pinned uv version differs — install.sh {uv_sh} vs install.ps1 {uv_ps}")
    elif uv_sh:
        checked.append(f"both pin uv at {uv_sh}")

    # 5d. signed tags (skill #99): one trust anchor, spelled the same in both installers and in upkeep.py (the path
    # TCC calls), and install.sh's check run against real signed, foreign-signed, unsigned and older tags.
    up = UPKEEP.read_text(encoding="utf-8") if UPKEEP.exists() else ""
    for what, sh_name, ps_name, py_name in (("signing key", "SKILL_SIGNING_KEY", "SkillSigningKey", "SIGNING_KEY"),
                                            ("signing principal", "SKILL_SIGNING_PRINCIPAL", "SkillSigningPrincipal",
                                             "SIGNING_PRINCIPAL"),
                                            ("first signed tag", "SKILL_SIGNED_FROM", "SkillSignedFrom", "SIGNED_FROM")):
        v_sh, e1 = one(rf'^{sh_name}="([^"]+)"', sh, sh_name, "install.sh")
        v_ps, e2 = one(rf'^\${ps_name}\s*=\s*"([^"]+)"', ps1, f"${ps_name}", "install.ps1")
        v_py, e3 = one(rf'^{py_name} = "([^"]+)"', up, py_name, "upkeep.py")
        problems.extend(e for e in (e1, e2, e3) if e)
        if v_sh and v_ps and v_py:
            if len({v_sh, v_ps, v_py}) != 1:
                problems.append(f"the {what} differs -- install.sh {v_sh!r}, install.ps1 {v_ps!r}, upkeep.py {v_py!r}")
            else:
                checked.append(f"the {what} agrees in both installers and upkeep.py ({v_sh[:24]}…)")
    # The app's first signed tag (#101): the two installers only -- TCC's own copy is in its repository
    # (core/signed_tags.py TCC_SIGNED_FROM), out of reach of a check that runs offline in this one.
    t_sh, e1 = one(r'^TCC_SIGNED_FROM="([^"]+)"', sh, "TCC_SIGNED_FROM", "install.sh")
    t_ps, e2 = one(r'^\$TccSignedFrom\s*=\s*"([^"]+)"', ps1, "$TccSignedFrom", "install.ps1")
    problems.extend(e for e in (e1, e2) if e)
    if t_sh and t_ps:
        if t_sh != t_ps:
            problems.append(f"the app's first signed tag differs -- install.sh {t_sh!r}, install.ps1 {t_ps!r}")
        else:
            checked.append(f"the app's first signed tag agrees in both installers ({t_sh})")
    signers = ROOT / "allowed_signers"
    listed = [ln.split() for ln in (signers.read_text(encoding="utf-8").splitlines() if signers.exists() else [])
              if ln.strip() and not ln.startswith("#")]
    key_sh, _ = one(r'^SKILL_SIGNING_KEY="([^"]+)"', sh, "SKILL_SIGNING_KEY", "install.sh")
    if not listed or " ".join(listed[0][2:4]) != key_sh or listed[0][0] != (one(
            r'^SKILL_SIGNING_PRINCIPAL="([^"]+)"', sh, "SKILL_SIGNING_PRINCIPAL", "install.sh")[0]):
        problems.append("allowed_signers does not list the installers' signing key under their principal -- "
                        "tag-check.sh reads it to decide whether git would sign with that key")
    else:
        checked.append("allowed_signers lists the installers' signing key")
    p_sh, p_ps = checkout_paths(sh, ps1, "LOCAL_CHANGES", "LocalChanges", problems)
    if p_sh and p_ps:
        if p_sh != p_ps or f'"{p_sh.split("/")[-1]}"' not in up:
            problems.append(f"where local changes are kept differs -- install.sh {p_sh!r}, install.ps1 {p_ps!r}")
        else:
            checked.append(f"local changes are kept in the same place (~/{p_sh})")
    sig = signing_problems(sh)
    problems.extend(sig)
    if not sig:
        checked.append("install.sh's verify_tag passes a signed tag, refuses a foreign-signed and an unsigned one, "
                       "lets an older tag and a branch through, and says when the switch skips it")
        checked.append("install.sh's verify_tag takes only the author's SSH signature: a sign-only gpg.ssh.program "
                       "is not asked, an OpenPGP 'Good' and a git that says 'Good' are refused, an ssh-keygen "
                       "with no -Y is a machine that cannot check, and gpg.minTrustLevel=ultimate refuses nothing "
                       "-- each stand-in seen to run (T-35, run)")
        checked.append("install.sh's check_tcc_tag does the same for the app's tags from a bare fetch, hands on the "
                       "verified commit, refuses a tag it cannot fetch, and tcc_tag_still_at refuses a moved tag (run)")
    landed = checkout_problems(sh, ps1)
    if landed:
        problems.extend(landed)
    else:
        checked.append("install.sh's checkout_method makes a copy that is the tag it checked -- a branch of the same "
                       "name ignored, detached, origin set -- updates onto the tag, leaves nothing of a refused tag, "
                       "removes a new copy or puts back an update whose checkout did not land, and leaves a folder "
                       "that is not a checkout alone; an update it cannot fetch, or whose local changes it cannot "
                       "keep, answers 1 with the copy where it was (run); install.ps1 the same, and both update paths "
                       "stop on it (read) (T-45, R32)")
    # The exit contract (#142): what the run ended as, in its exit code and its receipt.
    contract = exit_contract_problems(sh, ps1)
    if contract:
        problems.extend(contract)
    else:
        checked.append("the exit contract: install.sh's finish ends 0 `Installed.` or 3 `Installed, NOT ready: "
                       "<names>`, and stop ends 1, each writing a receipt that parses with its eleven fields in "
                       "install.ps1's order -- with a quote, a backslash and a tab in the engine's line, built by "
                       "python3 and by the shell -- plugin-ready only when ready, and a dry run writes nothing; a "
                       "declined consent ends 1, and a run that dies after it -- set -e, an unbound variable, an exec "
                       "-- ends 1 with `stopped`, never an earlier `ready` (run, under set -euo pipefail); "
                       "install.ps1's Stop-Installer writes `stopped`, a declined consent stops with 1 and the receipt "
                       "says `stopped` after it, its end the receipt and then `Stop-Installer 3` under -not $ok, one "
                       "plugin-ready under $ok (read); no `exit 1` or `ok=0` left in install.sh, the parts not ready "
                       "named alike and once in both, and the beta copy off its candidate among them (#142, R38)")
        installer_version, _ = one(r'^INSTALLER_VERSION="([^"]+)"', sh, "INSTALLER_VERSION", "install.sh")
        checked.append(f"install.sh's INSTALLER_VERSION, install.ps1's $InstallerVersion and plugin.json's version "
                       f"agree ({installer_version})")
    if "Test-TagSignature" not in ps1 or "gpg.ssh.allowedSignersFile" not in ps1:
        problems.append("install.ps1: no Test-TagSignature with gpg.ssh.allowedSignersFile -- the Windows half of #99")
    else:
        # git says "Good" and every reason on stderr, and Windows PowerShell 5.1 drops a native program's stderr
        # records at SilentlyContinue before `2>&1` merges them: the VM refused a good signature, with no reason
        # printed, until the check ran under Continue (2026-09-29, beta-v3.0.64-rc1).
        fn = re.search(r"^function Test-TagSignature \{.*?^\}", ps1, re.M | re.S)
        if not fn or re.search(r'ErrorActionPreference\s*=\s*"SilentlyContinue"', fn.group(0)):
            problems.append("install.ps1: Test-TagSignature reads git's answer under SilentlyContinue -- PowerShell 5.1 "
                            "drops stderr there, so a good signature reads as refused")
        else:
            checked.append("install.ps1's Test-TagSignature reads git's stderr (not under SilentlyContinue)")
    # T-35 (#142): one verifier, pinned, and one sentence accepted, in all three checks. install.sh's is RUN above; the
    # other two are READ here -- no PowerShell on the author's Mac or in the Linux job, and upkeep's selftest runs its own.
    # upkeep's must also hand git its `env`: without it git reads the person's own config, and its selftest's OpenPGP
    # case would give a PGP block to their real gpg.
    pinned = ("gpg.ssh.program=ssh-keygen", "gpg.minTrustLevel=fully", 'Good "git" signature for ')
    read_halves = (("install.ps1", re.search(r"^function Test-TagSignature \{.*?^\}", ps1, re.M | re.S), pinned),
                   ("upkeep.py", re.search(r"^def verify_tag\(.*?(?=^\S)", up, re.M | re.S), pinned + ("env=env",)))
    t35_missing = [f"{where}: {needle}" for where, fn, needles in read_halves for needle in needles
                   if not fn or needle not in fn.group(0)]
    if t35_missing:
        problems.append("a signature check leaves the verifier to the person's git config or takes more than the "
                        "author's sentence -- missing " + "; ".join(t35_missing) + " (T-35)")
    else:
        checked.append('install.ps1 and upkeep.py pin gpg.ssh.program=ssh-keygen and gpg.minTrustLevel=fully and accept '
                       'only `Good "git" signature for <principal> with`, as install.sh does; upkeep.py hands git its '
                       'env (read, not run)')
    # ...and the app's tag, both installers (#101): checked before uv, held to its commit right before it. install.sh's
    # functions are RUN above; these are the calls that put them in the app's path, and install.ps1's half, READ.
    tcc_calls = (("install.sh", sh, ('check_tcc_tag "$TCC_REF"', 'tcc_tag_still_at "$TCC_REF" "$TCC_SHA"')),
                 ("install.ps1", ps1, ("Test-TccTag $TccRef", "Test-TccTagStillAt $TccRef $script:TccSha",
                                       "Test-TagSignature $repo $Ref $TccSignedFrom", "init --quiet --bare",
                                       "refs/tags/${Ref}^{}")))
    tcc_missing = [f"{where}: {needle}" for where, text, needles in tcc_calls for needle in needles
                   if needle not in text]
    if tcc_missing:
        problems.append("the app's tag is not checked the same way before uv -- missing " + "; ".join(tcc_missing))
    else:
        checked.append("both installers check the app's tag before uv and hold it to its commit (install.ps1 read, "
                       "not run)")

    # 5c. Phase 1's desk engine (TODO S-020, the user's decision 2026-09-18). Three things have to
    # be the same decision in all three files, or a Mac and a PC do not end up with the same
    # machine: WHEN it is fetched (only where no .NET SDK can build one), WHO computes the file's
    # name and checks its digest (the method, through its own `fetch-binary` -- an installer that
    # spelled the name itself would be a second copy of hub RELEASE-CHANNEL.md §12), and what exit
    # 4 means (this release carries none for this pin and platform: say so, carry on).
    engine = []
    if not re.search(r'^WANT_ENGINE="auto"$', sh, re.M):
        engine.append('install.sh: WANT_ENGINE is no longer "auto" — the engine would be fetched '
                      "on machines that can build one, or not at all")
    if not re.search(r'^\$WantEngine\s*=\s*if \(\$Engine\) \{ "1" \} elseif \(\$NoEngine\) \{ "0" \} '
                     r'else \{ "auto" \}', ps1, re.M):
        engine.append("install.ps1: $WantEngine no longer comes from -Engine / -NoEngine the way "
                      "install.sh's comes from --engine / --no-engine")
    for text, where, flag in ((sh, "install.sh", "--no-engine"), (ps1, "install.ps1", "-NoEngine"),
                              (cmd, "install.cmd", "-NoEngine")):
        if flag not in text:
            engine.append(f"{where}: {flag} is not offered — the fetch cannot be refused there")
    for text, where in ((sh, "install.sh"), (ps1, "install.ps1")):
        if "fetch-binary --tag" not in text:
            engine.append(f"{where}: no `fetch-binary --tag` — the archive's name and its digest are "
                          "the method's to compute, not an installer's")
    if not re.search(r'^\s*4\)', sh, re.M) or "$engineRc -eq 4" not in ps1:
        engine.append("the meaning of exit 4 is not carried by both — a release with no archive for "
                      "this platform must be said out loud, not read as a failure")
    if engine:
        problems.extend(engine)
    else:
        checked.append("all three agree on the desk engine: fetched only where there is no .NET SDK, "
                       "by the method's own fetch-binary, exit 4 = this release carries none")

    # 6. the TAG the world is told to paste. HUB-030 moved the one-liners off `main`, and a pinned
    # URL is only worth pinning while it is current: a stale one keeps handing new users a build
    # that is not the newest. Compared against the CHANGELOG's own top entry, which is what this
    # repo already treats as the released version -- and offline, because CI has no network.
    #   One release behind is accepted too (hub #245, the release train): the last candidate of a minor carries its
    # `## [vX.Y.Z]` before the tag exists, and the lines people paste from main's front page must not name a tag
    # that does not exist yet -- the train moves them in its publication commit, right after the tag. A patch keeps
    # them current itself, and `tag-check.sh vX.Y.Z` holds it to that before the tag.
    changelog = read(ROOT / "CHANGELOG.md")
    released = previous = None
    heads = re.findall(r"^## \[(v3\.[0-9.]+)\]", changelog, re.M)
    if heads:
        released = heads[0]
        previous = heads[1] if len(heads) > 1 else None
    else:
        problems.append("CHANGELOG.md: no `## [v3.x.y]` heading — the released version cannot be "
                        "established, so the install lines cannot be checked against it")

    readmes = {n: read(ROOT / n) for n in
               ("README.md", "README.uk.md", "README.de.md", "README.pl.md")}
    pasted = {}
    for name, text in readmes.items():
        tags = set(re.findall(r"autosound-tuning-skill/(v3\.[0-9.]+|main)/install\.", text))
        if not tags:
            problems.append(f"{name}: no install one-liner found — it is the line people paste")
        elif len(tags) > 1:
            problems.append(f"{name}: the two install lines disagree — {sorted(tags)}")
        else:
            pasted[name] = tags.pop()
    if pasted and "main" in pasted.values():
        problems.append("an install one-liner still points at main: "
                        + ", ".join(n for n, t in pasted.items() if t == "main"))
    elif pasted and len(set(pasted.values())) > 1:
        problems.append("the four READMEs paste different versions — "
                        + ", ".join(f"{n} {t}" for n, t in sorted(pasted.items())))
    elif pasted and previous and set(pasted.values()) == {previous}:
        checked.append(f"all four READMEs paste {previous}, the release before CHANGELOG's newest {released} -- "
                       f"not tagged yet; the release train's publication commit moves them")
    elif pasted and released and set(pasted.values()) != {released}:
        problems.append(f"the READMEs paste {pasted['README.md']} but CHANGELOG's newest is "
                        f"{released} — the pinned line is behind the release")
    elif pasted and released:
        checked.append(f"all four READMEs paste the same install line, at {released}")

    # ...and install.cmd's download path, which fetches install.ps1 BY TAG. It stayed on v3.0.46 for
    # three releases (found 2026-09-13), so a Windows user without a local install.ps1 was handed the
    # installer of three releases ago. Same rule as the READMEs: that tag is the released version.
    if ps1url and released:
        cmd_tag = re.search(r"autosound-tuning-skill/(v3\.[0-9.]+)/install\.ps1", ps1url)
        if not cmd_tag:
            problems.append(f"install.cmd PS1URL names no v3 tag — {ps1url}")
        elif cmd_tag.group(1) != released:
            problems.append(f"install.cmd fetches install.ps1 at {cmd_tag.group(1)} but CHANGELOG's newest is "
                            f"{released} — bump PS1URL with the release")
        else:
            checked.append(f"install.cmd fetches install.ps1 at the released tag ({released})")

    # The plugin route (W-6 #120): both installers take the flag, check the copy with `upkeep.py verify-copy` before
    # anything is installed, and write it down with `plugin-ready` at the end -- the hook reads what they write.
    plugin = {"install.sh": (sh, "--plugin)"), "install.ps1": (ps1, "[switch]$Plugin")}
    lacking = [f"{name}: {what}" for name, (text, flag) in plugin.items()
               for what in (flag, "verify-copy --root", "plugin-ready --root") if what not in text]
    if lacking:
        problems.append("the plugin route is not in both installers -- missing " + "; ".join(lacking))
    else:
        checked.append("both installers take the plugin flag, verify the copy first and write it down last")

    # And the app: `install-tcc.md` is the OTHER way into TCC, so it must pin too (SCR-054) -- the lines agree with each
    # other, and each asks uv for Python 3.12 as the installers do (T-45): without it uv takes whatever Python it finds,
    # and a 3.9 reads as a broken package. Which tag is newest is not checked here: that needs the network, and the
    # installers resolve it when they run.
    tcc_doc = read(ROOT / "commands" / "install-tcc.md")
    tcc_refs = set(re.findall(r"autosound-tcc(@v[0-9.]+)?'", tcc_doc))
    tcc_installs = re.findall(r"`(uv tool install [^`]*)`", tcc_doc)
    if not tcc_refs:
        problems.append("commands/install-tcc.md: no `uv tool install … autosound-tcc` line found")
    elif "" in tcc_refs:
        problems.append("commands/install-tcc.md: an install line has no @tag, so uv takes the "
                        "default branch — the two ways into TCC stop giving the same app")
    elif len(tcc_refs) > 1:
        problems.append(f"commands/install-tcc.md: the lines pin different app versions — "
                        f"{sorted(tcc_refs)}")
    elif not tcc_installs or any("--python 3.12" not in line for line in tcc_installs):
        problems.append("commands/install-tcc.md: an install line has no `--python 3.12` -- uv takes whatever "
                        "Python it finds, which the installers never let it do (T-45)")
    else:
        checked.append(f"commands/install-tcc.md pins the app at {tcc_refs.pop().lstrip('@')}, with --python 3.12 "
                       f"on all {len(tcc_installs)} lines")

    for line in checked:
        print(f"  ok   {line}")
    for line in problems:
        print(f"  FAIL {line}", file=sys.stderr)
    if problems:
        print(f"\ninstaller-consistency: {len(problems)} divergence(s) — the installers are a "
              f"TRIPLET, fix all three", file=sys.stderr)
        return 1
    print(f"\ninstaller-consistency OK -- {len(checked)} shared decisions agree across "
          f"install.sh / install.ps1 / install.cmd")
    return 0


#: ── A CONSUMER CONTRACT, not just a convenience ──────────────────────────────────────────────
#: TCC's test suite reads `--print`, parses `NAME=value` and compares four of its own constants
#: against ours (their F-030, closed 2026-08-26). So the NAMES (six then, two beta globs added for
#: HUB-060) and the `NAME=value` shape are an interface: renaming a value or changing the output format breaks their suite, and it breaks
#: it the way `name_key`'s tuple did — quietly, in a consumer we do not build. Add names freely;
#: change or remove one only after telling them. Values themselves are expected to change: that is
#: what the flag is for.
#:
#: One asymmetry they handle on their side, recorded so nobody "fixes" it here: our `SKILL_REPO`
#: ends in `.git` and theirs does not. Same remote, different punctuation; they strip the suffix on
#: both sides before comparing.
#:
#: The values a fourth copy may need to agree with, each read from the installer that owns it.
#: `--print NAME` writes one of them and nothing else, so a consumer parses a value rather than
#: grepping this script -- TCC keeps a fourth copy of the tag glob and asked for this (F-030); a
#: test written against our source instead of our output breaks silently when we refactor.
def values():
    sh = read(SH)
    out = {}
    v, _ = one(r'^SKILL_TAG_GLOB="([^"]+)"', sh, "SKILL_TAG_GLOB", "install.sh")
    if v: out["SKILL_TAG_GLOB"] = v
    v, _ = one(r'^TCC_TAG_GLOB="([^"]+)"', sh, "TCC_TAG_GLOB", "install.sh")
    if v: out["TCC_TAG_GLOB"] = v
    v, _ = one(r'^SKILL_BETA_GLOB="([^"]+)"', sh, "SKILL_BETA_GLOB", "install.sh")
    if v: out["SKILL_BETA_GLOB"] = v
    v, _ = one(r'^TCC_BETA_GLOB="([^"]+)"', sh, "TCC_BETA_GLOB", "install.sh")
    if v: out["TCC_BETA_GLOB"] = v
    # The method's two checkouts, relative to the home folder (autosound-hub #145): an app that runs
    # the beta channel's copy finds it by path, and reads the path here rather than copying it.
    for name in ("SKILL_SRC", "SKILL_BETA_SRC"):
        v, _ = home_path_sh(sh, name)
        if v: out[name] = v
    m = re.search(r"--skill-ref\s+(v[0-9.]+)", sh)
    if m: out["SKILL_REF_EXAMPLE"] = m.group(1)
    m = re.search(r"--tcc-ref\s+(v[0-9.]+)", sh)
    if m: out["TCC_REF_EXAMPLE"] = m.group(1)
    for name, pat in (("SKILL_REPO", r"SKILL_REPO=\"([^\"]+)\""), ("TCC_REPO", r"TCC_REPO=\"([^\"]+)\"")):
        m = re.search(pat, sh)
        if m: out[name] = m.group(1)
    return out


def print_value(name):
    """One value on stdout, or exit 2 naming what exists -- never a guess, never a partial match."""
    vals = values()
    if name == "--list" or name is None:
        for k, v in sorted(vals.items()):
            print(f"{k}={v}")
        return 0
    if name not in vals:
        print(f"unknown name {name!r}; available: {', '.join(sorted(vals))}", file=sys.stderr)
        return 2
    print(vals[name])
    return 0


if __name__ == "__main__":
    if "--print" in sys.argv:
        i = sys.argv.index("--print")
        sys.exit(print_value(sys.argv[i + 1] if len(sys.argv) > i + 1 else "--list"))
    sys.exit(main())
