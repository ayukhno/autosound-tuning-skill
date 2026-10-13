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
#: names (none when it is unset), or -- $STUB_RC not 0 -- git's own words for a remote it cannot reach ($STUB_SAYS, or
#: a host that does not resolve), with that exit. `--version` answers, as `usable git` asks it; any other subcommand is
#: not this test's to answer. Every call is written down in $STUB_LOG when that is set. Bytes, so the script keeps its
#: "\n" line ends on Windows.
NO_NETWORK_GIT = (b"#!/bin/sh\n"
                  b"[ -z \"${STUB_LOG:-}\" ] || printf 'git %s\\n' \"$*\" >> \"$STUB_LOG\"\n"
                  b"[ \"$1\" = --version ] && { echo 'git version 2.99.0 (a stand-in)'; exit 0; }\n"
                  b"[ \"$1\" = ls-remote ] || { echo \"stub git: $1 is not asked here\" >&2; exit 99; }\n"
                  b"if [ \"${STUB_RC:-0}\" != 0 ]; then\n"
                  b"  echo \"${STUB_SAYS:-fatal: unable to access 'https://github.com/ayukhno/autosound-tuning-skill.git/': "
                  b"Could not resolve host: github.com}\" >&2\n"
                  b"  exit \"$STUB_RC\"\n"
                  b"fi\n"
                  b"[ -n \"${STUB_TAGS:-}\" ] || exit 0\n"
                  b"while IFS= read -r t; do\n"
                  b"  printf '0123456789abcdef0123456789abcdef01234567\\trefs/tags/%s\\n' \"$t\"\n"
                  b"done < \"$STUB_TAGS\"\n")
#: SFH's TLS-inspecting proxy (#142): git's own last line, which a stop over an unreadable tag list must carry -- it
#: said "no network?" over a network that answered with a certificate nobody trusts.
SSL_SAYS = ("fatal: unable to access 'https://github.com/ayukhno/autosound-tuning-skill.git/': SSL certificate problem: "
            "self-signed certificate in certificate chain")
#: #142 (SFH 1): a `git` whose `status` fails -- a copy with a broken submodule says "fatal: not a git repository" there
#: -- and which is the real git, named in $REAL_GIT, for everything else. A failed status read as a clean tree, and the
#: forced put-back then dropped a hand edit the update had refused to overwrite.
STATUS_FAILS_GIT = (b"#!/bin/sh\n"
                    b"for a in \"$@\"; do\n"
                    b"  if [ \"$a\" = status ]; then\n"
                    b"    echo 'fatal: not a git repository: vendor/Resonalyze/../../.git/modules/vendor/Resonalyze' >&2\n"
                    b"    exit 128\n"
                    b"  fi\n"
                    b"done\n"
                    b"exec \"$REAL_GIT\" \"$@\"\n")
#: The deferred T7 pair (#142): a checkout that breaks off half way -- a tracked file changed, HEAD where it was -- and
#: the put-back's `checkout --force`, which goes to the real git: what it promises, a copy back where it was and clean,
#: is then seen, where NO_CHECKOUT_GIT made the put-back a no-op as well.
BROKEN_CHECKOUT_GIT = (b"#!/bin/sh\n"
                       b"dir=''; prev=''; co=0; force=0\n"
                       b"for a in \"$@\"; do\n"
                       b"  [ \"$prev\" = -C ] && dir=\"$a\"\n"
                       b"  [ \"$a\" = checkout ] && co=1\n"
                       b"  [ \"$a\" = --force ] && force=1\n"
                       b"  prev=\"$a\"\n"
                       b"done\n"
                       b"if [ \"$co\" = 1 ] && [ \"$force\" = 0 ]; then printf 'half\\n' >> \"$dir/a\"; exit 0; fi\n"
                       b"exec \"$REAL_GIT\" \"$@\"\n")
#: T-45 (#142): a `git` whose `checkout` answers 0 and does nothing -- a checkout that did not land. Everything else is
#: the real git, which the script names in $REAL_GIT before this folder goes first on PATH.
NO_CHECKOUT_GIT = (b"#!/bin/sh\n"
                   b"for a in \"$@\"; do [ \"$a\" = checkout ] && exit 0; done\n"
                   b"exec \"$REAL_GIT\" \"$@\"\n")

#: The installers' exit table (#142, audit T-44, J6a item 4): 0 ready · 1 stopped before the end -- a refusal, an error
#: or an interruption; what was done before it stays, and a stop before the method's step leaves the method as it was ·
#: 2 usage · 3 installed, NOT ready, the missing parts named.
#: The receipt's fields in the order both installers write them: today's seven, then how the run ended.
RECEIPT_FIELDS = ("installer", "installer_sha256", "method_ref", "mode", "at", "platform", "engine",
                  "installer_version", "status", "missing", "python")
#: The short names a part that is not ready goes by, in both installers. install.ps1 adds the python3 a new window
#: runs, which only Windows gets wrong (`python3 in a new window`).
MISSING_NAMES = ("numpy", "scipy", "the method", "the method (2.x line)", "the beta copy", "TCC", "Claude Code")
#: What ENGINE_DID can carry -- the engine's own last line: a quote, a backslash, a tab. The receipt is JSON whatever it
#: holds: python's builder keeps the tab, escaped; the shell's drops control characters.
HOSTILE_ENGINE = 'built or run failed: "C:\\dotnet\\sdk" said\tno'
#: E-pair (#142): the version pair the installers' help shows -- a method and an app released together, the minor pair
#: the hub's tag ledger records (hub #239). Nine places: install.sh's header and usage each name the method's
#: (--skill-ref) and the app's (--tcc-ref), install.ps1's the same (-SkillRef, -TccRef), install.cmd's one line both.
EXAMPLE_PAIR = ("v3.1.0", "v1.1.0")
EXAMPLE_PLACES = {"install.sh": 2, "install.ps1": 2, "install.cmd": 1}
#: T-44 (#142): fetch-binary's answers, as the installers write them into the receipt's `engine` -- the same words in
#: both, `<tag>` the tag's variable in each. Any other code is "fetch-binary failed (code N)".
ENGINE_ANSWERS = {0: "installed for <tag> and checked against SHA256SUMS",
                  3: "does not match its SHA256SUMS -- nothing installed",
                  4: "carries no engine for this machine",
                  5: "the release could not be reached -- run the installer again later"}
#: E-time (#142): how long an install takes, said one way -- 10 to 20 minutes on a Mac without Apple's Command Line Tools
#: (Apple's ~1 GB, through their own window), 5 to 15 on Windows without Git (the fresh-VM runs of 2026-08-17, commit
#: 9b46f65 -- on a fresh PC that is the first install; R44), a few minutes otherwise: the installers' plan screen per
#: machine, and README.md and FAQ.md in this sentence. README and FAQ said 10-20 for everyone.
INSTALL_TIMES = {"install.sh": ["10 to 20 minutes", "a few minutes"],
                 "install.ps1": ["5 to 15 minutes", "a few minutes"]}
INSTALL_TIME_DOCS = ("10–20 minutes the first time on a Mac without the developer tools, 5–15 on Windows without Git, "
                     "a few minutes otherwise")
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


def fake_gpg(uid):
    """A `gpg.program` that calls any OpenPGP signature good, from a key whose user id is `uid` -- the signer's own
    words, which gpg prints after its `gpg: ` prefix. Runs no real gpg; bytes, so it keeps "\\n" on Windows."""
    return (b"#!/bin/sh\n"
            b"cat >/dev/null\n"
            b"echo '[GNUPG:] NEWSIG'\n"
            + f"echo '[GNUPG:] GOODSIG 0123456789ABCDEF {uid}'\n".encode("utf-8")
            + b"echo '[GNUPG:] VALIDSIG 0123456789ABCDEF0123456789ABCDEF01234567 2026-10-08 0 0 0 0 0 1 0 "
              b"0123456789ABCDEF0123456789ABCDEF01234567'\n"
              b"echo '[GNUPG:] TRUST_ULTIMATE 0 pgp'\n"
            + f"echo 'gpg: Good signature from \"{uid}\" [ultimate]' >&2\n".encode("utf-8")
            + b"exit 0\n")


FAKE_GPG = fake_gpg("Mallory <m@example.org>")
#: #142 (PTA 4): a user id that IS the author's sentence -- gpg prints it inside its own line, so only a test held to
#: the start of a line refuses it; one that searched anywhere installed a tag the author never signed.
FORGED_UID = 'Good "git" signature for author with ED25519 key SHA256:forged'
#: ...and one that is git's "cannot check" sentence (the deferred T6 item): searched anywhere, it made a forged tag read
#: as a machine that cannot check -- still refused, but worded "could not be checked". git's own lines start the line.
CANNOT_CHECK_UID = "error: cannot run ssh-keygen: No such file or directory"
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
                           (Path(tmp, "forged-gpg.sh"), fake_gpg(FORGED_UID)),
                           (Path(tmp, "cannot-check-gpg.sh"), fake_gpg(CANNOT_CHECK_UID)),
                           (stub_dir / "git", STUB_GIT), (old_dir / "ssh-keygen", OLD_SSH_KEYGEN)):
            path.write_bytes(body)
            path.chmod(0o755)
        hostile, pgp = Path(tmp, "hostile.gitconfig"), Path(tmp, "pgp.gitconfig")
        hostile.write_bytes(f'[gpg "ssh"]\n\tprogram = {Path(tmp, "sign-only.sh").as_posix()}\n'.encode("utf-8"))
        pgp.write_bytes(f'[gpg]\n\tprogram = {Path(tmp, "fake-gpg.sh").as_posix()}\n'.encode("utf-8"))
        forged, cannot = Path(tmp, "forged.gitconfig"), Path(tmp, "cannot-check.gitconfig")
        forged.write_bytes(f'[gpg]\n\tprogram = {Path(tmp, "forged-gpg.sh").as_posix()}\n'.encode("utf-8"))
        cannot.write_bytes(f'[gpg]\n\tprogram = {Path(tmp, "cannot-check-gpg.sh").as_posix()}\n'.encode("utf-8"))
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
                 (ultimate, None, "v3.0.64", 0, ("signed by the skill's author",), "gpg.minTrustLevel=ultimate"),
                 # #142 (PTA 4): the author's sentence as an OpenPGP user id, inside gpg's own line -- refused only by a
                 # test held to the start of a line; and git's "cannot run ssh-keygen" the same way (T6), which must
                 # not make a forged tag read as a machine that cannot check.
                 (forged, None, "v3.0.67", 1, ("does not check out", f'Good signature from "{FORGED_UID}'),
                  "a gpg.program whose user id is the author's sentence"),
                 (cannot, None, "v3.0.67", 1, ("does not check out", f'Good signature from "{CANNOT_CHECK_UID}'),
                  "a gpg.program whose user id is git's cannot-check sentence"))
    for config, first_on_path, ref, want_rc, want_texts, what in t35_cases:
        rc, said = run(f'verify_tag "{repo_posix}" "{ref}" 2>&1\n', config=config, first_on_path=first_on_path)
        never = ("could not be checked here",) if config is cannot else ()
        if rc != want_rc or any(text not in said for text in want_texts) or any(text in said for text in never):
            out.append(f"install.sh verify_tag {ref} under {what}: exit {rc}, want {want_rc} and "
                       f"{' + '.join(repr(t) for t in want_texts)}"
                       + (f", never {' + '.join(repr(t) for t in never)}" if never else "")
                       + f" -- said {said.strip()[-200:]!r}")
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


def utf8_locales():
    """The en_US UTF-8 locale this machine lists (`locale -a`; glibc spells it `en_US.utf8`), or () -- none, or no
    `locale` at all (Windows)."""
    try:
        listed = subprocess.run(["locale", "-a"], capture_output=True, text=True, timeout=20).stdout.split()
    except (OSError, subprocess.SubprocessError):
        return ()
    return tuple(name for name in ("en_US.UTF-8", "en_US.utf8") if name in listed)[:1]


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
        # ...and again in a UTF-8 locale where the machine has one (the deferred T7 item, #142): glibc reads a range such
        # as [0-9] by the locale's collation, which is what the rule's own `LC_ALL=C` is there for -- macOS reads code
        # points, and the selftests' Ubuntu runs C.UTF-8, so the guard was pinned nowhere a collation could differ.
        for where, env in (("install.sh", None),) + tuple(
                (f"install.sh under LC_ALL={loc}", dict(os.environ, LC_ALL=loc)) for loc in utf8_locales()):
            r = subprocess.run([bash, "-s"], input=script.encode("utf-8"), capture_output=True, env=env)
            got = dict(line.split() for line in r.stdout.decode("utf-8", "replace").splitlines() if " " in line)
            answers[where] = [got.get(str(i)) == "yes" if str(i) in got else None for i in range(len(names))]
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
    functions, missing = cut_functions(sh, ("say", "warn", "pretty", "have", "on_mac", "runs_ok", "usable",
                                            "json_str", "write_receipt", "stop", "is_release_tag",
                                            "newest_on_channel", "read_tags", "pick_method_ref"))
    if missing:
        return [f"install.sh: no `{name}() {{ ... }}` -- the method's tag pick cannot be run" for name in missing]
    bash, why = find_bash()
    if not bash:
        return [f"{why} -- install.sh's tag pick cannot be run, and unrun is not agreed"]
    out = []
    tmp = tempfile.mkdtemp(prefix="autosound_pick_")
    unreadable = ("could not read the method's release tags", "nothing was installed")
    try:
        stub_dir, tags = Path(tmp, "stub-git"), Path(tmp, "tags")
        stub_dir.mkdir()
        (stub_dir / "git").write_bytes(NO_NETWORK_GIT)
        (stub_dir / "git").chmod(0o755)
        tags.write_bytes("".join(t + "\n" for t in SELECTION_TAGS).encode("utf-8"))
        # (--skill-ref, offered tags, ls-remote's exit, what git says, a dry run, no git yet, exit, the ref, words,
        # never). #142 (SFH 5): git's own last line goes into the stop -- a proxy's certificate is not "no network?".
        # #142 (SFH 4): a dry run changes nothing, so an unreadable list stops nothing: it says what a real run would
        # install and why it cannot say which; with no git yet -- a Mac without Apple's tools, whose /usr/bin/git is a
        # shim that opens Apple's window -- no git is run at all (the stand-in writes down every call).
        cases = (("", None, 0, None, "0", False, 1, None, unreadable, ()),
                 ("", None, 128, None, "0", False, 1, None, unreadable + ("Could not resolve host: github.com",), ()),
                 ("", None, 128, SSL_SAYS, "0", False, 1, None, unreadable + ("SSL certificate problem: self-signed",),
                  ("no network?",)),
                 ("main", None, 0, None, "0", False, 0, "main", ("UNSIGNED",), ()),
                 ("v3.0.33", None, 128, None, "0", False, 0, "v3.0.33", (), ("UNSIGNED",)),
                 ("", tags, 0, None, "0", False, 0, "v3.1.10", (), ("UNSIGNED",)),
                 ("", None, 128, SSL_SAYS, "1", False, 0, "v3.*",
                  ("would install the newest v3.* release (not readable here: ", "SSL certificate problem"),
                  ("could not read the method's release tags",)),
                 ("", None, 0, None, "1", True, 0, "v3.*",
                  ("would install the newest v3.* release (not readable here: no git yet)",),
                  ("no network?", "could not read the method's release tags")))
        for i, (given, offered, stub_rc, says, dry, nogit, want_rc, want_ref, words, not_words) in enumerate(cases):
            script = (f'set -euo pipefail\nexport PATH="$(cd "{stub_dir.as_posix()}" && pwd)":"/usr/bin:$PATH"\n'
                      'SKILL_REPO="https://github.com/ayukhno/autosound-tuning-skill.git"\nSKILL_TAG_GLOB="v3.*"\n'
                      f'DRY_RUN={dry}\n' + functions + ("usable() { return 1; }\n" if nogit else "")
                      + f'ref="$(pick_method_ref "{given}")" || exit $?\nprintf "REF=[%s]\\n" "$ref"\n')
            data, calls = Path(tmp, f"data-{i}"), Path(tmp, f"git-calls-{i}")
            env = dict(os.environ, STUB_RC=str(stub_rc), STUB_TAGS=offered.as_posix() if offered else "",
                       HOME=tmp, XDG_DATA_HOME=str(data), STUB_LOG=calls.as_posix())
            env.pop("STUB_SAYS", None)
            if says:
                env["STUB_SAYS"] = says
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
            ran_git = calls.read_text(encoding="utf-8").strip() if calls.exists() else ""
            if (r.returncode != want_rc or got_out != want_out or any(w not in got_err for w in words)
                    or any(w in got_err for w in not_words) or status != want_status or (nogit and ran_git)):
                out.append(f"install.sh pick_method_ref {given or '(no --skill-ref)'}"
                           f"{' with ' + ' '.join(SELECTION_TAGS) if offered else ''}, ls-remote exit {stub_rc}"
                           f"{', a dry run' if dry == '1' else ''}{' with no git yet' if nogit else ''}: "
                           f"exit {r.returncode}, stdout {got_out.strip()!r}, receipt {status!r}, want {want_rc} and "
                           f"{want_out.strip()!r}"
                           + (f" saying {' + '.join(map(repr, words))}" if words else "")
                           + (f" and never {' + '.join(map(repr, not_words))}" if not_words else "")
                           + (f", a receipt saying {want_status!r} (#142)" if want_status else ", no receipt")
                           + (f", and no git run -- it ran {ran_git!r}" if nogit else "")
                           + f" -- stderr {got_err.strip()[-220:]!r} (T-37)")
    except OSError as exc:
        out.append(f"the tag pick's fixtures could not be made ({exc}) -- unrun is not agreed")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    stop_ps1 = ("could not read the method's release tags ($($script:TagsWhy)) -- nothing was installed or changed for "
                "the method; run again when GitHub answers, or name a tag with -SkillRef")
    read = (("install.sh", 'SKILL_REF="$(pick_method_ref "$SKILL_REF")" || stop $?', True),
            ("install.sh", 'SKILL_REF="main"', False),
            ("install.sh", "could not read the app's release tags ($TAGS_WHY)", True),
            ("install.sh", "could not read the method's candidates ($TAGS_WHY)", True),
            ("install.ps1", "$SkillRef = Select-MethodRef $SkillRef", True),
            ("install.ps1", stop_ps1, True),
            ("install.ps1", '$SkillRef = "main"', False),
            ("install.ps1", "could not read the app's release tags ($($script:TagsWhy))", True),
            ("install.ps1", "could not read the method's candidates ($($script:TagsWhy))", True))
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
    # #142 (SFH 4, 5): one reader of the tag lists in install.ps1, which keeps git's last line and says "no git yet"
    # without running a git that is not there; a dry run's unreadable list is said, not a stop.
    read_fn = re.search(r"^function Read-ReleaseTags \{.*?^\}", ps1, re.M | re.S)
    if not read_fn or '"no git yet"' not in read_fn.group(0) or "$script:TagsWhy" not in read_fn.group(0) \
            or "if (-not (Have git))" not in read_fn.group(0):
        wrong.append("install.ps1 has no Read-ReleaseTags that names git's own line, and \"no git yet\" without git")
    if not pick_ps1 or "would install the newest $SkillTagGlob release (not readable here: $($script:TagsWhy))" \
            not in pick_ps1.group(0) or "if ($DryRun)" not in pick_ps1.group(0):
        wrong.append("install.ps1 Select-MethodRef stops a dry run over a tag list it cannot read")
    if len(re.findall(r"& git ls-remote", ps1)) != 2:
        wrong.append(f"install.ps1 reads a tag list {len(re.findall(r'& git ls-remote', ps1))} ways -- one, "
                     f"Read-ReleaseTags, plus the app's moved check")
    sh_reads = [ln for ln in sh.splitlines() if "$(git ls-remote " in ln and not ln.lstrip().startswith("#")]
    if len(sh_reads) != 2:
        wrong.append(f"install.sh reads a tag list {len(sh_reads)} ways -- one, read_tags, plus the app's moved check")
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
    functions, missing = cut_functions(sh, ("say", "warn", "pretty", "run", "have", "on_mac", "runs_ok", "usable",
                                            "is_release_tag", "settled_by_name", "verify_tag", "keep_local", "head_is",
                                            "put_tag_back", "checkout_method"))
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
        # A sibling on the update's commit: git brings any tag on a fetched commit along unless told `--no-tags` (R48).
        git("-C", origin, "tag", "-a", "v3.0.71", "-m", "unsigned, beside v3.0.67")
        first, later = git("-C", origin, "rev-parse", "v3.0.64^{commit}"), git("-C", origin, "rev-parse", "HEAD")
        git("-C", origin, "update-ref", "refs/heads/v3.0.64", later)
        git("-C", origin, "update-ref", "refs/heads/main", later)
        # R48 (#142): two unsigned tags on a third commit, which no fetch of an earlier step can bring along.
        Path(origin, "a").write_text("a\nb\nc\n")
        git("-C", origin, "commit", "-q", "-am", "c")
        git("-C", origin, "tag", "-a", "v3.0.68", "-m", "unsigned")
        git("-C", origin, "tag", "-a", "v3.0.69", "-m", "unsigned")
        stubs = {}
        for name, body in (("no-checkout", NO_CHECKOUT_GIT), ("broken-checkout", BROKEN_CHECKOUT_GIT),
                           ("status-fails", STATUS_FAILS_GIT)):
            stubs[name] = Path(tmp, name)
            stubs[name].mkdir()
            (stubs[name] / "git").write_bytes(body)
            (stubs[name] / "git").chmod(0o755)
        occupied = Path(tmp, "occupied")
        occupied.mkdir()
        (occupied / "mine.txt").write_text("somebody's\n")
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        shutil.rmtree(tmp, ignore_errors=True)
        return [f"the checkout's fixtures could not be made ({exc}) -- unrun is not agreed"]
    url = Path(origin).as_uri()

    def run(where, ref, stub=None):
        first_on_path = f'"$(cd "{stubs[stub].as_posix()}" && pwd)":' if stub else ""
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
        the refs, not of `describe`, which picks among tags on one commit by tagger date."""
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

    def tag_at(where, tag):
        return git("-C", where, "rev-parse", "--verify", "--quiet", f"refs/tags/{tag}", check=False)

    def clean(where):
        return git("-C", where, "status", "--porcelain", "--untracked-files=all", check=False) == ""

    copy, own = os.path.join(tmp, "copy"), {}
    empty = os.path.join(tmp, "empty")
    steps = (
        # ...each fetch the one tag asked for: v3.0.66 shares v3.0.64's commit, v3.0.71 v3.0.67's (R48, `--no-tags`).
        ("a new copy of v3.0.64, a branch of that name on another commit", copy, "v3.0.64", None, 0,
         ("signed by the skill's author",),
         lambda: head(copy) == first and the_tag(copy, "v3.0.64") and tag_at(copy, "v3.0.66") == ""),
        ("that copy updated to v3.0.67", copy, "v3.0.67", None, 0, ("signed by the skill's author",),
         lambda: head(copy) == later and the_tag(copy, "v3.0.67") and tag_at(copy, "v3.0.71") == ""),
        ("that copy updated to v3.0.64 by a checkout that does not land", copy, "v3.0.64", "no-checkout", 3,
         ("did not take",), lambda: head(copy) == later),
        # The deferred T7 pair (#142): the put-back's `--force` reaches the real git, over a tracked file a checkout
        # that broke off left changed -- the copy is back where it was, and clean.
        ("that copy updated to v3.0.64 by a checkout that breaks off half way", copy, "v3.0.64", "broken-checkout", 3,
         ("did not take",), lambda: head(copy) == later and clean(copy)),
        # R48 (#142): a refused update leaves refs/tags as it found them -- the tag it fetched is deleted again, and a
        # local tag of that name, which the forced fetch overwrote, gets its own value back.
        ("that copy updated to v3.0.68, unsigned, a tag it did not have", copy, "v3.0.68", None, 2,
         ("does not check out",), lambda: head(copy) == later and tag_at(copy, "v3.0.68") == ""),
        ("that copy updated to v3.0.69, unsigned, over a v3.0.69 of its own", copy, "v3.0.69", None, 2,
         ("does not check out",), lambda: head(copy) == later and tag_at(copy, "v3.0.69") == own["v3.0.69"] != "",
         lambda: (git("-C", copy, "tag", "-f", "v3.0.69", first), own.update({"v3.0.69": tag_at(copy, "v3.0.69")}))),
        ("a new copy of v3.0.66, unsigned", os.path.join(tmp, "unsigned"), "v3.0.66", None, 2,
         ("does not check out",), lambda: not os.path.exists(os.path.join(tmp, "unsigned"))),
        ("a new copy of the branch main, named", os.path.join(tmp, "branch"), "main", None, 0, ("UNSIGNED",),
         lambda: head(os.path.join(tmp, "branch")) == later),
        ("a new copy of v3.0.64 by a checkout that does not land", os.path.join(tmp, "stuck"), "v3.0.64",
         "no-checkout", 3, ("removed",), lambda: not os.path.exists(os.path.join(tmp, "stuck"))),
        ("a new copy into a folder that is there and is not a checkout", str(occupied), "v3.0.64", None, 1, (),
         lambda: sorted(os.listdir(occupied)) == ["mine.txt"]),
        # The deferred T7 item (#142): a new copy whose fetch fails leaves no folder -- an empty one already at that
        # path included, which holds nothing to lose (the comment over it said "never a folder that was there").
        ("a new copy of v3.0.99, a tag its remote does not have", os.path.join(tmp, "nothing"), "v3.0.99", None, 1,
         (), lambda: not os.path.exists(os.path.join(tmp, "nothing"))),
        ("a new copy of v3.0.99 into an empty folder already there", empty, "v3.0.99", None, 1, (),
         lambda: not os.path.exists(empty), lambda: os.makedirs(empty)),
        # R32 (#142): an update that cannot be made is a stop, the copy where it was -- it was a warning, and the run
        # ended "Installed." on the old version.
        ("that copy updated to v3.0.99, a tag its remote does not have", copy, "v3.0.99", None, 1,
         ("could not fetch v3.0.99", "nothing was changed"), lambda: head(copy) == later),
        # #142 (SFH 1): a `git status` that fails is no clean tree. It read as one, the checkout refused to overwrite the
        # hand edit, and the forced put-back dropped it. Now a stop, 1, git's line said, the edit where it was.
        ("that copy, changed by hand, updated to v3.0.64 when git status fails", copy, "v3.0.64", "status-fails", 1,
         ("git status failed", "not a git repository", "nothing was changed"),
         lambda: head(copy) == later and Path(copy, "a").read_text() == "a\nb\nmine\n",
         lambda: Path(copy, "a").write_text("a\nb\nmine\n")),
        ("that copy, changed by hand, updated to v3.0.64 when the change cannot be kept", copy, "v3.0.64", None, 1,
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
    lacking = [n for n in ("init --quiet $Dir", "remote add origin $SkillRepo",
                           "fetch --quiet --no-tags --depth 1 origin $spec", "Test-HeadIs $Dir $want",
                           "$script:NotTheTag = $true", "if ($statusRc -ne 0) {", "checkout --quiet @force $was")
               if n not in body]
    # #142 (SFH 1, R48): a status read with its exit code, a put-back forced only over a tree seen clean, and refs/tags
    # put back on every way an update does not land -- refused, unreadable, not kept, not landed.
    if body.count("Restore-Tag $Dir $tagRef $had") != 4 or body.count("fetch --quiet --no-tags --depth 1") != 2:
        lacking.append(f"Restore-Tag on each of the four ways an update does not land, and --no-tags on both fetches "
                       f"(Restore-Tag {body.count('Restore-Tag $Dir $tagRef $had')} times)")
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


#: T-40 (#142): where the method's copy is, and whether the SDK can build the engine from it -- `method_is_checkout`'s
#: answer: the installer's clone (no --plugin), a plugin root that is a git checkout (a `.git` folder, or a `.git` file in
#: a submodule), and a plugin copy, which is none.
CHECKOUT_LAYOUTS = (("the installer's clone", None, 0), ("a plugin root with a .git folder", "folder", 0),
                    ("a plugin root with a .git file (a submodule)", "file", 0), ("a plugin copy, no .git", "none", 1))
#: The engine step's lines that must say the same in both installers: a plugin copy's 4 waits for an engine -- it has no
#: SDK route (T-40) -- and an engine that does not run names the repair: the same tag's engine is never fetched again
#: while it is there (T-44).
ENGINE_PLUGIN_WAITS = "a plugin copy cannot build one -- Phase 1's desk step waits for an engine"
ENGINE_REPAIR = "to fetch it again, remove"


def engine_gate_problems(sh, ps1):
    """T-40 (#142): install.sh's `method_is_checkout` RUN on CHECKOUT_LAYOUTS -- a constant answer passed a read of the
    branches that ask it -- and READ: both installers' two build branches ask it, the SDK line after a 4 is said only for
    a checkout (a plugin copy waits for an engine), and an engine that does not run names the repair. [] when all hold."""
    import tempfile
    out = []
    functions, missing = cut_functions(sh, ("method_is_checkout",))
    bash, why = find_bash()
    if missing:
        out.append("install.sh: no `method_is_checkout() { ... }` -- where the SDK can build the engine cannot be run "
                   "(T-40)")
    elif not bash:
        out.append(f"{why} -- install.sh's method_is_checkout cannot be run, and unrun is not agreed")
    else:
        tmp = tempfile.mkdtemp(prefix="autosound_checkout_gate_")
        try:
            for what, git, want in CHECKOUT_LAYOUTS:
                root = Path(tmp, what.replace(" ", "-").replace(",", "").replace("(", "").replace(")", ""))
                root.mkdir()
                if git == "folder":
                    (root / ".git").mkdir()
                elif git == "file":
                    (root / ".git").write_text("gitdir: ../.git/modules/skill\n", encoding="utf-8")
                plugin = "" if git is None else root.as_posix()
                script = f'set -euo pipefail\nPLUGIN_ROOT="{plugin}"\n' + functions + "method_is_checkout\n"
                r = subprocess.run([bash, "-s"], input=script.encode("utf-8"), capture_output=True)
                if r.returncode != want:
                    out.append(f"install.sh method_is_checkout, {what}: exit {r.returncode}, want {want} "
                               f"({'a checkout' if want == 0 else 'no checkout'}) -- "
                               f"{r.stderr.decode('utf-8', 'replace').strip()[-120:]!r} (T-40)")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    four_sh = re.search(r"^\s*4\) .*?;;", sh, re.M | re.S)
    four_ps = re.search(r"\$engineRc -eq 4\) \{.*?\n    \}", ps1, re.S)
    reads = (("install.sh: both build branches ask method_is_checkout",
              len(re.findall(r'"\$WANT_ENGINE" = "auto" \] && method_is_checkout && have_dotnet', sh)) == 2),
             ("install.ps1: both build branches ask $MethodIsCheckout",
              len(re.findall(r'\$WantEngine -eq "auto" -and \$MethodIsCheckout -and \$HaveDotnet', ps1)) == 2),
             ("install.ps1: $MethodIsCheckout is install.sh's method_is_checkout",
              '$MethodIsCheckout = -not ($PluginRoot -and -not (Test-Path (Join-Path $PluginRoot ".git")))' in ps1),
             ("install.sh: after a 4, the SDK line only for a checkout, and a plugin copy waits for an engine",
              bool(four_sh) and "if method_is_checkout; then" in four_sh.group(0)
              and ENGINE_PLUGIN_WAITS in four_sh.group(0)),
             ("install.ps1: after a 4, the SDK line only for a checkout, and a plugin copy waits for an engine",
              bool(four_ps) and "if ($MethodIsCheckout)" in four_ps.group(0) and ENGINE_PLUGIN_WAITS in four_ps.group(0)),
             ("both: an engine that does not run names the repair",
              f'"{ENGINE_REPAIR} $(pretty "$ENGINE_HOME")' in sh and f'"{ENGINE_REPAIR} $(Pretty $EngineHome)' in ps1))
    out += [f"{what} -- does not hold (T-40, T-44)" for what, holds in reads if not holds]
    return out


#: T-38 (#142): install.sh's link block run in a temp HOME -- (case, what is at the link's place before, DRY_RUN,
#: checkout_method's answer, exit, words, never, what is there after). `ours` is a link into the clone, `foreign` one to a
#: folder of somebody else's, `dangling` one to nothing; an update that cannot be made (1) or is refused (2) is a stop
#: that makes no link.
RELINK_CASES = (
    ("missing", None, "0", 0, 0, ("was missing — made again",), (), "ours"),
    ("ours", "ours", "0", 0, 0, (), ("made again", "would make"), "ours"),
    ("foreign", "foreign", "0", 0, 0, ("left exactly as it is",), ("made again",), "foreign"),
    ("dangling", "dangling", "0", 0, 0, ("left exactly as it is",), ("made again",), "dangling"),
    ("a real folder", "folder", "0", 0, 0, ("a real directory this script did not create",), ("made again",), "folder"),
    # #142 (SFH 7): a file there is neither ours nor a folder: left, as install.ps1 leaves it -- it was `rm -f`'d.
    ("a regular file", "file", "0", 0, 0, ("a file this script did not create", "left alone"), ("made again",), "file"),
    ("missing, a dry run", None, "1", 0, 0, ("would make the missing link",), ("made again",), "nothing"),
    ("missing, the update not made", None, "0", 1, 1, ("update failed",), ("made again",), "nothing"),
    ("missing, the update refused", None, "0", 2, 1, ("not a signed release",), ("made again",), "nothing"),
    # #142 (PTA 5): a checkout that did not land is a stop of its own, the copy put back.
    ("missing, the update did not land", None, "0", 3, 1, ("could not be put on",), ("made again",), "nothing"))
#: #142 (SFH 7): what the receipt's method_ref says when the method's step left the link's place as it was -- not a
#: tag this run never installed.
LEFT_AS_IT_WAS = "left as it was: "


def relink_problems(sh, ps1):
    """T-38 (#142): a re-run repairs the link; [] when both installers' update branch does.

    The branch that updates the method's copy already there made no `~/.claude/skills/autosound-tuning` when it was
    missing -- removed by hand, or by a tidy-up -- and every re-run said "updating" over a method Claude Code could not
    see. install.sh's link block (`ours=0` to the end of its if/elif chain) is cut out and RUN over RELINK_CASES with
    `checkout_method` stubbed: a missing link is made again, after the update's stops; ours is left as it is; a link
    that is not ours (dangling or not) and a real folder are warned about and left; a dry run makes nothing. On Windows
    -- where install.sh never runs, and Git Bash's `ln -s` copies -- and wherever `ln -s` makes no link, the block is
    read only, and said so. `(problems, ran)`.
    install.ps1 is READ: its update branch makes the junction again under `-not $linkExists`, after its stops, and the
    entry is looked at with `Get-Item -Force` -- `Test-Path` says False for a dangling junction, which then read as
    missing: "made again" over a New-Item that fails.
    """
    import tempfile
    out, ran = [], None
    branches = (
        ("install.sh", re.search(r'^elif \[ -d "\$SKILL_SRC/\.git" \]; then\n(.*?)^else\n', sh, re.M | re.S),
         r"\bstop 1\b", 'ln -s "$SKILL_SRC/skills/autosound-tuning" "$SKILL_HOME"', '[ ! -L "$SKILL_HOME" ]'),
        ("install.ps1", re.search(r'^    if \(Test-Path \(Join-Path \$SkillSrc "\.git"\)\) \{\n(.*?)^    \} else \{\n', ps1,
                                  re.M | re.S),
         r"Stop-Installer 1; return",
         'New-Item -ItemType Junction -Path $SkillHome -Target (Join-Path $SkillSrc "skills\\autosound-tuning")',
         "-not $linkExists"))
    for where, branch, stop_re, link, when_missing in branches:
        if not branch:
            out.append(f"{where}: no update branch to read -- the method's copy already there (T-38)")
            continue
        body = branch.group(1)
        last_stop = max((m.end() for m in re.finditer(stop_re, body)), default=0)
        tail = body[last_stop:]
        if link not in tail or when_missing not in tail or tail.find(when_missing) > tail.find(link):
            out.append(f"{where}: the update branch does not make a missing link again after its stops -- want "
                       f"`{link}` under `{when_missing}` (T-38)")
    if "$entry = Get-Item $SkillHome -Force -ErrorAction SilentlyContinue" not in ps1 or "$linkExists = [bool]$entry" \
            not in ps1:
        out.append("install.ps1: the link's place is looked at with Test-Path, which says False for a dangling junction "
                   "-- it read as missing, and the update said \"made again\" over a New-Item that fails; want "
                   "`$entry = Get-Item $SkillHome -Force -ErrorAction SilentlyContinue` and `$linkExists = [bool]$entry` "
                   "(T-38)")
    # install.sh's block, RUN.
    block = re.search(r"^ours=0\n.*?(?=^# The beta channel's copy \(autosound-hub #145\))", sh, re.M | re.S)
    bash, why = find_bash()
    if not block:
        return out + ["install.sh: no link block (`ours=0` up to the beta channel's copy) to run (T-38)"], False
    if not bash:
        return out + [f"{why} -- install.sh's link block cannot be run, and unrun is not agreed"], False
    tmp = tempfile.mkdtemp(prefix="autosound_relink_")
    try:
        probe = subprocess.run([bash, "-c", 'cd "$1" && mkdir t && ln -s t l && [ -L l ]', "_", Path(tmp).as_posix()],
                               capture_output=True)
        ran = os.name != "nt" and probe.returncode == 0
        # On POSIX a bash whose `ln -s` makes no link is a missing input, not a reason to read instead of run: the
        # block's cases would pass unrun (#142, the last re-review). Windows reads it, and says so.
        if os.name != "nt" and probe.returncode != 0:
            out.append(f"{bash}: `ln -s` made no link here ({probe.stderr.decode('utf-8', 'replace').strip()[-120:]!r})"
                       f" -- install.sh's link block cannot be run, and unrun is not agreed (T-38)")
        for case, before, dry, co_rc, want_rc, words, never, after in (RELINK_CASES if ran else ()):
            home = Path(tmp, case.replace(" ", "-").replace(",", ""))
            src = home / ".claude" / "skills" / ".autosound-tuning-src"
            (src / ".git").mkdir(parents=True)
            (src / "skills" / "autosound-tuning").mkdir(parents=True)
            (home / "elsewhere").mkdir()
            setup = {None: ":", "ours": 'ln -s "$SKILL_SRC/skills/autosound-tuning" "$SKILL_HOME"',
                     "foreign": 'ln -s "$HOME/elsewhere" "$SKILL_HOME"', "dangling": 'ln -s "$HOME/gone" "$SKILL_HOME"',
                     "folder": 'mkdir -p "$SKILL_HOME/mine"', "file": 'printf "mine\\n" > "$SKILL_HOME"'}[before]
            script = ('set -euo pipefail\nsay() { printf "%s\\n" "$*"; }\nwarn() { printf "  ! %s\\n" "$*"; }\n'
                      'stop() { _c="$1"; shift; printf "STOP %s\\n" "$*"; exit "$_c"; }\n'
                      f'checkout_method() {{ return {co_rc}; }}\n'
                      'SKILL_HOME="$HOME/.claude/skills/autosound-tuning"\n'
                      'SKILL_SRC="$HOME/.claude/skills/.autosound-tuning-src"\n'
                      f'SKILL_REF=v3.1.3\nDRY_RUN={dry}\nMETHOD_LEFT=""\n{setup}\n' + block.group(0)
                      + 'printf "METHOD_LEFT=[%s]\\n" "$METHOD_LEFT"\n')
            r = subprocess.run([bash, "-s"], input=script.encode("utf-8"), capture_output=True,
                               env=dict(os.environ, HOME=home.as_posix()))
            said = (r.stdout + r.stderr).decode("utf-8", "replace")
            place = home / ".claude" / "skills" / "autosound-tuning"
            if not os.path.lexists(place):
                state = "nothing"
            elif place.is_symlink():
                state = ("dangling" if not place.exists()
                         else "ours" if os.path.samefile(place, src / "skills" / "autosound-tuning")
                         else "foreign" if os.path.samefile(place, home / "elsewhere") else "something else")
            else:
                state = "folder" if place.is_dir() else "file" if place.is_file() else "something else"
            wrong = ([f"exit {r.returncode}, want {want_rc}"] if r.returncode != want_rc else [])
            wrong += [f"never says {w!r}" for w in words if w not in said]
            wrong += [f"says {w!r}" for w in never if w in said]
            if state != after:
                wrong.append(f"the link's place holds {state}, want {after}")
            if before == "folder" and not (place / "mine").is_dir():
                wrong.append("the real folder's content is gone")
            if before == "file" and state == "file" and place.read_text() != "mine\n":
                wrong.append("the file's content is changed")
            # The receipt's method_ref (#142, SFH 7): a place left as it was is said so, never as the tag picked.
            left = re.search(r"METHOD_LEFT=\[(.*)\]", said)
            left_at = left.group(1) if left else None
            if r.returncode == 0 and before in ("foreign", "dangling", "folder", "file") \
                    and not (left_at or "").startswith(LEFT_AS_IT_WAS):
                wrong.append(f"the receipt's method_ref would be the tag picked, not {LEFT_AS_IT_WAS!r}...: "
                             f"METHOD_LEFT is {left_at!r}")
            elif r.returncode == 0 and before not in ("foreign", "dangling", "folder", "file") and left_at:
                wrong.append(f"METHOD_LEFT is {left_at!r} for a place this run made or kept")
            if wrong:
                out.append(f"install.sh's link block, {case}: " + "; ".join(wrong)
                           + f" -- said {said.strip()[-200:]!r} (T-38)")
    except OSError as exc:
        out.append(f"the link block's fixtures could not be made ({exc}) -- unrun is not agreed")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return out, ran


#: #142 (SFH 2 = PTA 1, PTA 3): install.sh's app block and its line in the checks, RUN with stand-ins -- (case, the tags
#: ls-remote offers or None, ls-remote's exit, the tag signed, uv here, uv's install exit, an app here before, the parts
#: missing after, MODE after, words). A failed upgrade over an app from an earlier run ended 0, ready: the checks saw
#: the old app.
APP_CASES = (("installed now", ("v1.1.2",), 0, True, True, 0, False, "", "tcc", ("✓ installed",)),
             ("its signature refused", ("v1.1.2",), 0, False, True, 0, False, "TCC", "tcc",
              ("could not be shown to be a signed release of TCC",)),
             ("its tags unreadable behind a proxy", None, 128, True, True, 0, False, "TCC", "tcc",
              ("could not read the app's release tags (", "SSL certificate problem")),
             ("its upgrade failed, an app here from before", ("v1.1.2",), 0, True, True, 1, True, "TCC", "tcc",
              ("was here before and was not upgraded",)),
             ("its install failed, none here before", ("v1.1.2",), 0, True, True, 1, False, "TCC", "tcc",
              ("Autosound TCC was not installed",)),
             ("uv does not install", ("v1.1.2",), 0, True, False, 0, False, "TCC", "terminal",
              ("uv did not install",)),
             # A dry run with no git yet (the re-review): what a real run would install, as the method's step says it --
             # it said "could not read the app's release tags (no git yet) -- run again when GitHub answers".
             ("a dry run with no git yet", None, 0, True, True, 0, False, "", "tcc",
              ("would install the newest app release (not readable here: no git yet)",), True,
              ("run again when GitHub answers", "could not read the app's release tags", "the app is not installed")))
#: The stand-ins the app's block meets: a `uv` that lists the app, installs it into $LOCAL_BIN or fails as $STUB_UV_RC
#: says; and a `curl` that never reaches the network -- what it hands `sh` ends uv's own installer with 7.
STUB_UV = (b"#!/bin/sh\n"
           b"[ -z \"${STUB_LOG:-}\" ] || printf 'uv %s\\n' \"$*\" >> \"$STUB_LOG\"\n"
           b"case \"$1 ${2:-}\" in\n"
           b"  '--version '*) echo 'uv 0.12.10 (a stand-in)' ;;\n"
           b"  'tool list') echo 'autosound-tcc v1.1.2' ;;\n"
           b"  'tool install')\n"
           b"    if [ \"${STUB_UV_RC:-0}\" != 0 ]; then echo 'error: the build failed (a stand-in)' >&2; "
           b"exit \"$STUB_UV_RC\"; fi\n"
           b"    mkdir -p \"$LOCAL_BIN\" && printf '#!/bin/sh\\nexit 0\\n' > \"$LOCAL_BIN/autosound-tcc\" "
           b"&& chmod 755 \"$LOCAL_BIN/autosound-tcc\" ;;\n"
           b"esac\n")
STUB_CURL = (b"#!/bin/sh\n"
             b"[ -z \"${STUB_LOG:-}\" ] || printf 'curl %s\\n' \"$*\" >> \"$STUB_LOG\"\n"
             b"echo 'exit 7'\n")


def app_problems(sh, ps1):
    """#142 (SFH 2 = PTA 1, PTA 3, SFH 5): install.sh's app block -- `TCC_BIN=""` up to the reviewer's -- and the app's
    line in the checks, cut out and RUN over APP_CASES with stand-ins for git, uv, curl and the signature check; [] when
    each ends with the parts missing it should. Every site that leaves the app out counts it missing, by what it does,
    not by where `missing TCC` is spelled. install.ps1's half is READ: its four Add-Missing "TCC" and the arm for an app
    that was here before."""
    import tempfile
    out = []
    block = re.search(r'^TCC_BIN=""\n.*?(?=^# ── the reviewer)', sh, re.M | re.S)
    check = re.search(r'^if \[ "\$MODE" = "tcc" \] && \[ "\$DRY_RUN" = 0 \]; then\n.*?^fi\n', sh, re.M | re.S)
    functions, missing = cut_functions(sh, ("say", "warn", "have", "runs_ok", "usable", "run", "pretty", "in_local_bin",
                                            "find_bin", "manifest_add", "is_missing", "missing", "newest_on_channel",
                                            "read_tags"))
    if not block or not check or missing:
        return [f"install.sh: the app's block, its line in the checks, or {missing} -- the app cannot be run (#142)"]
    bash, why = find_bash()
    if not bash:
        return [f"{why} -- install.sh's app block cannot be run, and unrun is not agreed"]
    tmp = tempfile.mkdtemp(prefix="autosound_app_")
    try:
        for i, (case, offered, ls_rc, signed, have_uv, uv_rc, before, want_missing, want_mode, words, *dry_never) \
                in enumerate(APP_CASES):
            dry, never = dry_never if dry_never else (False, ())
            home = Path(tmp, f"case-{i}")
            stub = home / "stub"
            stub.mkdir(parents=True)
            for name, body, wanted in (("git", NO_NETWORK_GIT, True), ("uv", STUB_UV, have_uv), ("curl", STUB_CURL, True),
                                       ("autosound-tcc", b"#!/bin/sh\nexit 0\n", before)):
                if wanted:
                    (stub / name).write_bytes(body)
                    (stub / name).chmod(0o755)
            tags = home / "tags"
            tags.write_bytes("".join(t + "\n" for t in (offered or ())).encode("utf-8"))
            script = ('set -euo pipefail\n' + functions
                      + 'step() { printf "==> %s\\n" "$*"; }\non_mac() { return 1; }\n'
                      + ('check_tcc_tag() { TCC_SHA=""; return 0; }\n' if signed
                         else 'check_tcc_tag() { TCC_SHA=""; return 1; }\n')
                      + 'tcc_tag_still_at() { return 0; }\n'
                      + ('usable() { return 1; }\n' if dry else '')
                      + f'export PATH="$(cd "{stub.as_posix()}" && pwd):/usr/bin:/bin"\n'
                      + f'LOCAL_BIN="{(home / "bin").as_posix()}"; export LOCAL_BIN\n'
                      + f'MANIFEST="{(home / "manifest").as_posix()}"\nAPP="{(home / "no.app").as_posix()}"\n'
                      + f'DESKTOP_LINK="{(home / "no-link").as_posix()}"\n'
                      + f'MODE=tcc\nCHANNEL=stable\nTCC_REF=""\nDRY_RUN={1 if dry else 0}\nMISSING=""\nUV_VERSION=0.12.10\n'
                      + 'TCC_REPO="https://github.com/ayukhno/autosound-tcc"\nTCC_TAG_GLOB="v*"\nTCC_BETA_GLOB="beta-v*"\n'
                      + block.group(0) + check.group(0)
                      + 'printf "MISSING=[%s] MODE=[%s]\\n" "$MISSING" "$MODE"\n')
            env = dict(os.environ, HOME=home.as_posix(), STUB_TAGS=tags.as_posix() if offered else "",
                       STUB_RC=str(ls_rc), STUB_SAYS=SSL_SAYS, STUB_UV_RC=str(uv_rc),
                       STUB_LOG=(home / "calls").as_posix())
            env.pop("UV_TOOL_BIN_DIR", None)
            r = subprocess.run([bash, "-s"], input=script.encode("utf-8"), capture_output=True, env=env)
            said = (r.stdout + r.stderr).decode("utf-8", "replace")
            got = re.search(r"MISSING=\[(.*?)\] MODE=\[(.*?)\]", said)
            wrong = [] if r.returncode == 0 else [f"exit {r.returncode}"]
            if not got or got.group(1) != want_missing or got.group(2) != want_mode:
                wrong.append(f"ends with {got.group(0) if got else 'no MISSING line'}, want MISSING=[{want_missing}] "
                             f"MODE=[{want_mode}]")
            wrong += [f"never says {w!r}" for w in words if w not in said]
            wrong += [f"says {w!r}" for w in never if w in said]
            calls = (home / "calls").read_text(encoding="utf-8") if (home / "calls").exists() else ""
            if dry and "git " in calls:
                wrong.append(f"a dry run with no git yet ran git: {calls!r}")
            if "curl" in calls and "astral.sh" not in calls:
                wrong.append(f"curl was asked for something other than uv's installer: {calls!r}")
            if wrong:
                out.append(f"install.sh's app block, {case}: " + "; ".join(wrong) + f" -- said {said.strip()[-260:]!r}")
    except OSError as exc:
        out.append(f"the app block's fixtures could not be made ({exc}) -- unrun is not agreed")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    # install.ps1, READ: four ways to leave the app out, each counted -- no uv, refused or unreadable, not upgraded over
    # an app from before, not installed -- and the arm for an app that was here before.
    sh_sites = [ln for ln in sh.splitlines() if not ln.lstrip().startswith("#")
                and re.search(r"(?:^|;)\s*missing TCC\s*$", ln.strip())]
    reads = ((len(re.findall(r'Add-Missing "TCC"', ps1)) == 4, 'install.ps1 has four Add-Missing "TCC"'),
             ('elseif ($HaveTcc) { Warn "Autosound TCC was here before and was not upgraded this time (above) -- it is '
              'left as it was"; Add-Missing "TCC" }' in ps1, "install.ps1's arm for an app here before, not upgraded"),
             (len(sh_sites) == 3,
              f"install.sh has three `missing TCC` (no uv; refused, unreadable or not upgraded; not installed), "
              f"not {len(sh_sites)}"),
             ("TCC_REFUSED=\"its install did not finish -- uv's lines above say why\"" in sh,
              "install.sh records a failed install of the app as TCC_REFUSED"),
             # The re-review: a dry run that cannot read the app's tags says what a real run would install (install.ps1,
             # read; install.sh's is the dry-run case above), and the end knows an app from before stays (TCC_KEPT,
             # outside both blocks run here).
             ('Warn "would install the newest app release (not readable here: $($script:TagsWhy))"' in ps1,
              "install.ps1's app block says what a dry run would install when the app's tags cannot be read"),
             ('if [ "$DRY_RUN" = 0 ] && { [ -d "$APP" ] || find_bin autosound-tcc >/dev/null; }; then TCC_KEPT=1; fi'
              in sh, "install.sh notes an app from before (TCC_KEPT) for the end's line"))
    out += [f"{what} -- does not hold (#142)" for holds, what in reads if not holds]
    return out


#: #142 (SFH 11): each option that takes a value, given none -- it ended 1 with no line (`shift` under `set -e`).
OPTION_CASES = ((("--skill-ref",), 2, "--skill-ref needs a value"), (("--terminal", "--channel"), 2,
                                                                       "--channel needs a value"),
                (("--tcc-ref",), 2, "--tcc-ref needs a value"),
                (("--skill-ref", "v3.1.0", "--tcc-ref", "v1.1.0", "--channel", "beta"), 0,
                 "SKILL_REF=[v3.1.0] CHANNEL=[beta] TCC_REF=[v1.1.0]"))


def option_problems(sh):
    """#142 (SFH 11): install.sh's option loop, cut out and RUN under `set -euo pipefail` over OPTION_CASES; []."""
    loop = re.search(r"^while \[ \$# -gt 0 \]; do\n.*?^done\n", sh, re.M | re.S)
    bash, why = find_bash()
    if not loop:
        return ["install.sh: no option loop (`while [ $# -gt 0 ]; do ... done`) to run (#142)"]
    if not bash:
        return [f"{why} -- install.sh's option loop cannot be run, and unrun is not agreed"]
    out = []
    for args, want_rc, words in OPTION_CASES:
        script = ('set -euo pipefail\nusage() { echo usage; }\nMODE=tcc\nSKILL_REF=""\nCHANNEL=stable\nTCC_REF=""\n'
                  + "set -- " + " ".join(args) + "\n" + loop.group(0)
                  + 'printf "SKILL_REF=[%s] CHANNEL=[%s] TCC_REF=[%s]\\n" "$SKILL_REF" "$CHANNEL" "$TCC_REF"\n')
        r = subprocess.run([bash, "-s"], input=script.encode("utf-8"), capture_output=True)
        said = (r.stdout + r.stderr).decode("utf-8", "replace")
        if r.returncode != want_rc or words not in said:
            out.append(f"install.sh {' '.join(args)}: exit {r.returncode}, want {want_rc} and {words!r} -- said "
                       f"{said.strip()[-160:]!r} (#142)")
    return out


def engine_answer_problems(sh, ps1):
    """#142 (PTA 6): fetch-binary's answers, each in its own arm. install.sh's `case "$ENGINE_RC" in ... esac` is cut out
    and RUN for each code -- the receipt's words were searched anywhere in the file, so an arm that said another code's
    words passed; install.ps1's `$engineRc -eq N` arms are READ, each one's own `$EngineDid`. []."""
    out = []
    case = re.search(r'^  case "\$ENGINE_RC" in\n.*?^  esac\n', sh, re.M | re.S)
    functions, missing = cut_functions(sh, ("say", "warn", "pretty"))
    bash, why = find_bash()
    if not case or missing:
        out.append('install.sh: no `case "$ENGINE_RC" in ... esac` to run (#142)')
    elif not bash:
        out.append(f"{why} -- install.sh's engine answers cannot be run, and unrun is not agreed")
    else:
        for code, words in tuple(ENGINE_ANSWERS.items()) + ((7, "fetch-binary failed (code 7)"),):
            script = ('set -euo pipefail\n' + functions + 'python3() { echo "  ✓ it runs"; return 0; }\n'
                      'method_is_checkout() { return 0; }\nSKILL_REF=v3.1.2\nENGINE_PY=/x/resonalyze_engine.py\n'
                      f'ENGINE_HOME=/x/engines\nENGINE_DID=""\nENGINE_RC={code}\n' + case.group(0)
                      + 'printf "ENGINE_DID=[%s]\\n" "$ENGINE_DID"\n')
            r = subprocess.run([bash, "-s"], input=script.encode("utf-8"), capture_output=True)
            said = (r.stdout + r.stderr).decode("utf-8", "replace")
            did = re.search(r"ENGINE_DID=\[(.*)\]", said)
            want = words.replace("<tag>", "v3.1.2")
            others = [w.replace("<tag>", "v3.1.2") for c, w in ENGINE_ANSWERS.items() if c != code]
            if r.returncode or not did or want not in did.group(1) or any(o in did.group(1) for o in others):
                out.append(f"install.sh's engine arm for fetch-binary's {code}: the receipt's engine is "
                           f"{did.group(1) if did else None!r}, want {want!r} and no other code's words (#142)")
    for code, words in ENGINE_ANSWERS.items():
        arm = re.search(rf'\$engineRc -eq {code}\) \{{\s*\n\s*\$EngineDid = "([^"]*)"', ps1)
        if not arm or words.replace("<tag>", "$SkillRef") not in arm.group(1):
            out.append(f"install.ps1's `$engineRc -eq {code}` arm does not set $EngineDid to {words!r} first (#142)")
    return out


#: #142 (SFH 6): upkeep.py verify-copy's codes, as the installers' plugin block reads them: 3 the copy is not as its
#: author signed it, 4 it could not be checked here (no network, git failed) -- the two shared exit 3 and one sentence.
VERIFY_COPY_CASES = ((0, ()), (3, ("is not v3.1.2 as its author signed it",)),
                     (4, ("could not be checked against its signed release here",)))


def plugin_check_problems(sh, ps1):
    """#142 (SFH 6): install.sh's plugin block -- the check of a plugin copy -- cut out and RUN with a stand-in python3
    answering each of verify-copy's codes; install.ps1's READ. []."""
    out = []
    block = re.search(r'^if \[ -n "\$PLUGIN_ROOT" \]; then\n  # The plugin\'s copy is the method.*?(?=^else\n)', sh,
                      re.M | re.S)
    functions, missing = cut_functions(sh, ("say", "warn", "pretty"))
    bash, why = find_bash()
    if not block or missing:
        out.append("install.sh: no plugin block (`if [ -n \"$PLUGIN_ROOT\" ]; then ...`) to run (#142)")
    elif not bash:
        out.append(f"{why} -- install.sh's plugin check cannot be run, and unrun is not agreed")
    else:
        for code, words in VERIFY_COPY_CASES:
            script = ('set -euo pipefail\n' + functions
                      + 'stop() { _c="$1"; shift; printf "STOP %s\\n" "$*"; exit "$_c"; }\nusable() { return 0; }\n'
                      + f'python3() {{ return {code}; }}\nPLUGIN_ROOT=/x/plugin\nPLUGIN_VERSION=3.1.2\nDRY_RUN=0\n'
                      + block.group(0) + "fi\necho PAST\n")
            r = subprocess.run([bash, "-s"], input=script.encode("utf-8"), capture_output=True)
            said = (r.stdout + r.stderr).decode("utf-8", "replace")
            want_rc, others = (0, ()) if code == 0 else (1, [w for c, ws in VERIFY_COPY_CASES if c not in (0, code)
                                                             for w in ws])
            if r.returncode != want_rc or any(w not in said for w in words) or any(o in said for o in others) \
                    or (code == 0) != ("PAST" in said):
                out.append(f"install.sh's plugin check, verify-copy's {code}: exit {r.returncode}, want {want_rc}"
                           + (f" saying {words!r}" if words else " and going on") + f" -- said {said.strip()[-200:]!r}"
                           + " (#142)")
    reads = (("if ($LASTEXITCODE -eq 4) {" in ps1, "install.ps1 reads verify-copy's 4 apart from its 3"),
             ("could not be checked against its signed release here" in ps1, "install.ps1 says a copy it could not check"))
    out += [f"{what} -- does not hold (#142)" for holds, what in reads if not holds]
    return out


def ps1_native_problems(ps1):
    """#142 (SFH 3): install.ps1's Run and Test-Quiet count a native command that could not start as one that ran -- a
    command that is not there sets no exit code, and both read the 0 they had set beforehand. READ (no PowerShell here):
    each clears the code to $null first, answers $false from its catch, and counts only a code that was set and is 0.
    The same functions are RUN where PowerShell is (ps1_run_problems)."""
    want = ("$global:LASTEXITCODE = $null", "return ($null -ne $LASTEXITCODE -and $LASTEXITCODE -eq 0)")
    out = []
    for name in ("Run", "Test-Quiet"):
        fn = re.search(rf"^function {name} \{{\n.*?^\}}$", ps1, re.M | re.S)
        body = fn.group(0) if fn else ""
        lacking = [w for w in want if w not in body]
        if not re.search(r"catch \{[^}]*return \$false", body):
            lacking.append("catch { ... return $false }")
        if "$global:LASTEXITCODE = 0" in body:
            lacking.append("no `$global:LASTEXITCODE = 0` before the call")
        if lacking:
            out.append(f"install.ps1 {name}: a native command that could not start reads as one that ran -- want "
                       + "; ".join(lacking) + " (#142)")
    # ...and the git calls of the signature check and of a new copy (the re-review): a code that was set, never the 0
    # set beforehand -- a git that could not start read as one that said yes.
    for name in ("Test-TagSignature", "Test-TccTag", "Sync-MethodCheckout"):
        fn = re.search(rf"^function {name} \{{\n.*?^\}}$", ps1, re.M | re.S)
        if not fn or "$global:LASTEXITCODE = 0" in fn.group(0):
            out.append(f"install.ps1 {name}: sets $global:LASTEXITCODE = 0 before a git call -- a git that could not "
                       f"start then reads as one that answered 0; want $null (#142)")
    return out


def find_powershell(which=shutil.which):
    """Windows PowerShell 5.1 where it is (what install.cmd runs, and every Windows ships), else PowerShell 7, else
    None -- the author's Mac has neither; GitHub's Windows runners have both."""
    return which("powershell") or which("pwsh")


def powershell_env(environ=None):
    """The environment a PowerShell this check starts gets: this process's, without PSModulePath (R50, #142). A CI step
    runs under PowerShell 7, whose PSModulePath names its own modules; Windows PowerShell 5.1 started with it cannot
    load its own (`Get-FileHash` was "not recognized"), and builds the right one itself when the variable is not set.
    Compared without case: Windows' names are."""
    environ = os.environ if environ is None else environ
    return {k: v for k, v in environ.items() if k.upper() != "PSMODULEPATH"}


#: The functions of install.ps1 that its end and its probes need, cut out as they stand.
PS1_RUN_FUNCTIONS = ("Stop-Installer", "Write-Receipt", "Add-Missing", "Say", "Warn", "Pretty", "Run", "Test-Quiet")


def ps1_run_problems(ps1):
    """#142 (PTA 2's note, SFH 3): install.ps1's end and its two native-command probes, cut out and RUN under PowerShell
    -- where there is one: the Windows job's runner; `(problems, ran)`. Each case is a script file of its own (so
    Stop-Installer's `exit` is the process's code) in a temp folder that stands in for %LOCALAPPDATA%:
      * the end with nothing missing: exit 0, `Installed.`, the receipt `ready`;
      * the end with numpy missing: exit 3, `Installed, NOT ready: numpy`, the receipt `not ready` naming it;
      * Run and Test-Quiet over a command that is not there ($false), one that ends 0 ($true) and one that ends 3
        ($false) -- the interpreter running this check stands in for the native command.
    """
    import json
    import tempfile
    shell = find_powershell()
    if not shell:
        return [], False
    cut, lacking = [], []
    for name in PS1_RUN_FUNCTIONS:
        # One line (`function Say  { ... }`), or from `function Name {` to the first `}` alone at column 0.
        m = (re.search(rf"^function {re.escape(name)}\s+\{{[^\n]*\}}[ \t]*$", ps1, re.M)
             or re.search(rf"^function {re.escape(name)} \{{\n.*?^\}}", ps1, re.M | re.S))
        (cut.append(m.group(0)) if m else lacking.append(name))
    end_at = ps1.find("$ok = $script:Missing.Count -eq 0")
    if lacking or end_at < 0:
        return [f"install.ps1: no {lacking or 'end'} to run under PowerShell (#142)"], True
    py = Path(sys.executable).as_posix()
    tmp = tempfile.mkdtemp(prefix="autosound_ps1_")
    out = []

    def run_case(case, body):
        home = Path(tmp, case)
        home.mkdir()
        appdata = home / "appdata"
        script = home / "case.ps1"
        head = (f'$ErrorActionPreference = "Continue"\n$env:LOCALAPPDATA = "{appdata.as_posix()}"\n'
                f'$DryRun = $false\n$PluginRoot = ""\n$LocalBin = "{(home / "bin").as_posix()}"\n'
                f'$Py3 = "{(home / "bin" / "python3.exe").as_posix()}"\n$SkillHome = "{(home / "skill").as_posix()}"\n'
                f'$SkillBetaSrc = "{(home / "beta").as_posix()}"\n$SkillRef = "v3.1.2"\n$MethodLeft = ""\n'
                '$Mode = "terminal"\n$InstallerVersion = "3.1.2"\n$EngineDid = "not fetched: -NoEngine"\n'
                '$TccRefused = ""\n$AutosoundTranscriptOn = $false\n$AutosoundRunAsFile = [bool]$PSCommandPath\n'
                '$script:Missing = @()\n')
        script.write_bytes((head + "\n".join(cut) + "\n" + body).encode("utf-8"))
        r = subprocess.run([shell, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(script)],
                           capture_output=True, timeout=120, env=powershell_env())
        said = (r.stdout + r.stderr).decode("utf-8", "replace")
        receipt_path = appdata / "autosound" / "install-receipt.json"
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8-sig")) if receipt_path.is_file() else None
        except ValueError:
            receipt = "not JSON"
        return r.returncode, said, receipt

    end = ps1[end_at:]
    try:
        for case, missing, want_rc, word, status in (("ready", "", 0, "Installed.", "ready"),
                                                     ("not-ready", 'Add-Missing "numpy"\n', 3,
                                                      "Installed, NOT ready: numpy", "not ready")):
            rc, said, receipt = run_case(case, missing + end)
            want_missing = ["numpy"] if missing else []
            if rc != want_rc or word not in said or not isinstance(receipt, dict) or receipt.get("status") != status \
                    or receipt.get("missing") != want_missing:
                out.append(f"install.ps1's end under {Path(shell).name}, {case}: exit {rc}, receipt "
                           f"{receipt if not isinstance(receipt, dict) else {k: receipt.get(k) for k in ('status', 'missing')}}"
                           f" -- want {want_rc}, {word!r}, status {status!r}, missing {want_missing} -- said "
                           f"{said.strip()[-300:]!r} (#142)")
        nothere = Path(tmp, "not-there", "nothing.exe").as_posix()
        probes = (f'Write-Host "Q-absent=$(Test-Quiet {{ & \'{nothere}\' }})"\n'
                  f'Write-Host "Q-zero=$(Test-Quiet {{ & \'{py}\' -c \'import sys; sys.exit(0)\' }})"\n'
                  f'Write-Host "Q-three=$(Test-Quiet {{ & \'{py}\' -c \'import sys; sys.exit(3)\' }})"\n'
                  f'Write-Host "R-absent=$(Run {{ & \'{nothere}\' }} \'nothing\')"\n'
                  f'Write-Host "R-zero=$(Run {{ & \'{py}\' -c \'import sys; sys.exit(0)\' }} \'zero\')"\n'
                  f'Write-Host "R-three=$(Run {{ & \'{py}\' -c \'import sys; sys.exit(3)\' }} \'three\')"\n')
        rc, said, _ = run_case("probes", probes)
        want = {"Q-absent": "False", "Q-zero": "True", "Q-three": "False", "R-absent": "False", "R-zero": "True",
                "R-three": "False"}
        got = dict(re.findall(r"^([QR]-\w+)=(\w+)\s*$", said, re.M))
        if got != want:
            out.append(f"install.ps1's Run and Test-Quiet under {Path(shell).name}: {got}, want {want} -- a command "
                       f"that could not start must not read as one that ran; said {said.strip()[-300:]!r} (#142)")
    except (OSError, subprocess.SubprocessError) as exc:
        out.append(f"install.ps1 could not be run under {shell} ({exc}) -- unrun is not agreed (#142)")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return out, True


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
    # #142 (PTA 2): the verdict's one input, by position -- after the last Add-Missing, before the verdict is said. A
    # `$ok` set anywhere else, or `-gt`/`-le` in it, would end a NOT ready run 0 with nothing else to catch it.
    oks = [m.start() for m in re.finditer(r"^\$ok = \$script:Missing\.Count -eq 0$", ps1, re.M)]
    adds = [m.start() for m in re.finditer(r'\bAdd-Missing "', ps1)]
    verdict = ps1.find('elseif ($ok) { Write-Host "Installed." }')
    if len(oks) != 1 or not adds or verdict < 0 or not adds[-1] < oks[0] < verdict \
            or len(re.findall(r"^\$ok\s*=", ps1, re.M)) != 1:
        ps_wrong.append("`$ok = $script:Missing.Count -eq 0` is not the one `$ok`, after the last Add-Missing and before "
                        "the verdict")
    # #142 (SFH 8): Write-Receipt says, once, when it cannot write -- the file and why -- and stops nothing. Its
    # cmdlets stop on their error (-ErrorAction Stop), or Set-Content's non-terminating one passed the catch by.
    if not write_fn or write_fn.group(0).count("-ErrorAction Stop") < 2 \
            or 'Warn "the receipt was not written (' not in write_fn.group(0):
        ps_wrong.append("Write-Receipt keeps a receipt it could not write quiet -- want -ErrorAction Stop on New-Item and "
                        "Set-Content, and one Warn naming the file and the reason")
    # #142 (SFH 7): a method step that left the link's place says so in method_ref, as install.sh's METHOD_LEFT.
    if not write_fn or "$ref = if ($MethodLeft) { $MethodLeft } else { \"$SkillRef\" }" not in write_fn.group(0) \
            or "method_ref = $ref;" not in write_fn.group(0) or len(re.findall(r'\$MethodLeft = "left as it was: ', ps1)) != 2:
        ps_wrong.append("the receipt's method_ref is the tag picked even when the method's step left the link's place "
                        "as it was -- want $MethodLeft, set twice (a link not ours, anything else there)")
    if "which is not there, and this installer leaves a link it did not make -- remove that link" not in ps1:
        ps_wrong.append("the end does not name a dangling link not ours as the thing to remove")
    # R50 (#142): the installer's hash from .NET, under its own guard -- Get-FileHash comes from a script module that a
    # Windows PowerShell under PowerShell 7's PSModulePath cannot load, and its error cost the whole receipt (CI
    # 37866508892: the receipt never written, "The term 'Get-FileHash' is not recognized").
    write_code = "\n".join(ln for ln in (write_fn.group(0) if write_fn else "").splitlines()
                           if not ln.lstrip().startswith("#"))
    if not write_fn or "Get-FileHash" in write_code \
            or "$hasher = [System.Security.Cryptography.SHA256]::Create()" not in write_fn.group(0) \
            or '} catch { $sha = "" }' not in write_fn.group(0):
        ps_wrong.append("Write-Receipt's installer_sha256 is not .NET's SHA256 under its own guard -- a module that does "
                        "not load costs the whole receipt (R50)")
    # The end's line for the app (#142): one reason, and "not upgraded" when an app from before stays.
    if 'if ($HaveTcc -and -not $TccExe) { Warn "the app was not upgraded -- the one from before is left as it was: $why; ' \
            'the method is installed and works without it" }' not in ps1:
        ps_wrong.append("the end's line for the app glues two reasons, or says \"not installed\" over an app from before")
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
        if callable(before):                            # the receipt's place made unwritable (#142, SFH 8)
            before(data)
        elif before is not None:                        # an earlier run's receipt, there before this one
            (data / "autosound").mkdir(parents=True)
            (data / "autosound" / "install-receipt.json").write_text(json.dumps(before), encoding="utf-8")
        # A file, so $0 is one: the receipt's sha256 is this script's, as it is install.sh's when it runs as a file.
        # Under the installer's own `set -euo pipefail`; `tty_ok` answers "no terminal", so `ask` takes its default.
        text = ('set -euo pipefail\nexport PATH="/usr/bin:$PATH"\n' + functions + FAKE_PYTHON3
                + "tty_ok() { return 1; }\n" + ("usable() { return 1; }\n" if builder == "shell" else "")
                + f'DRY_RUN={dry}\nASSUME_YES=0\nMODE=terminal\nSKILL_REF=v3.1.2\nMETHOD_LEFT=""\n'
                + f'INSTALLER_VERSION="{version}"\n'
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
        if path.is_file():
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
              ("past the stop", "Installed", "the lines above say where"), "stopped", [], 0),
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
             # sees the end (a kill; here `exec`) it says `stopped` from going ahead on, and a signal -- which bash
             # 3.2's trap sees as 130 after a Ctrl-C stopped a child, as 0 when it was sent to the shell alone -- ends
             # by the signal with the receipt the same.
             ("a-failure", go + "missing numpy\nfalse\nfinish\n", "python3", "0", False, 1,
              ("stopped (exit 1) -- the lines above say where",), ("Installed",), "stopped", ["numpy"], 0, earlier),
             ("a-failure-coded-3", go + "missing numpy\nsh -c 'exit 3'\nfinish\n", "python3", "0", False, 1,
              ("stopped (exit 3) -- the lines above say where",), ("Installed",), "stopped", ["numpy"], 0, earlier),
             ("an-end-no-trap-sees", go + "missing numpy\nexec false\n", "python3", "0", False, 1, (), ("Installed",),
              "stopped", [], 0, earlier),
             # An unbound variable under `set -u`: bash 3.2 (macOS's) hands the trap $? = 0, and a trap that trusted it
             # ended the run 0 -- ready. Its line then names no code (bash 5's, 1): never "exit 0" for a run ending 1.
             ("an-unbound-variable", go + 'missing numpy\n: "$NOT_SET_ANYWHERE"\nfinish\n', "python3", "0", False, 1,
              ("unbound variable", "the lines above say where"), ("Installed", "(exit 0)"), "stopped", ["numpy"], 0,
              earlier),
             # #142 (SFH 7): the method's step left the link's place as it was -- its receipt says so, not the tag
             # picked; by either builder.
             ("left-as-it-was", go + f'METHOD_LEFT="{LEFT_AS_IT_WAS}a folder this installer did not make"\nfinish\n',
              "python3", "0", False, 0, ("Installed.",), (), "ready", [], 0),
             ("left-as-it-was-no-python3", go + f'METHOD_LEFT="{LEFT_AS_IT_WAS}a link to /x"\nmissing numpy\nfinish\n',
              "shell", "0", False, 3, ("Installed, NOT ready: numpy",), (), "not ready", ["numpy"], 0),
             # #142 (SFH 8): a receipt that cannot be written stops nothing, and is said once per write: the file, and
             # why. A file where its folder goes, and a folder where the file goes.
             ("an-unwritable-receipt-folder", go + "finish\n", "python3", "0", False, 0,
              ("Installed.", "the receipt was not written", "install-receipt.json")
              + (("File exists",) if os.name != "nt" else ()), (), None, None, 0,
              lambda data: (data.mkdir(parents=True), (data / "autosound").write_text("a file\n"))),
             ("an-unwritable-receipt", go + 'missing scipy\nfinish\n', "shell", "0", False, 3,
              ("Installed, NOT ready: scipy", "the receipt was not written", "install-receipt.json")
              + (("Is a directory",) if os.name != "nt" else ()), (), None, None, 0,
              lambda data: (data / "autosound" / "install-receipt.json").mkdir(parents=True)))
    # The end's line for the app (#142, the re-review): one reason -- the refusal's, or the block's -- and "not upgraded"
    # when an app from before stays; it glued "... uv's lines above say why -- the app's block above says why".
    failed = 'TCC_REFUSED="its install did not finish -- uv\'s lines above say why"\n'
    cases += (("the-app-not-upgraded", go + failed + "TCC_KEPT=1\nmissing TCC\nfinish\n", "python3", "0", False, 3,
               ("the app was not upgraded -- the one from before is left as it was: its install did not finish -- uv's "
                "lines above say why; the method is installed",), ("the app's block above says why",), "not ready",
               ["TCC"], 0),
              ("the-app-not-installed", go + failed + "missing TCC\nfinish\n", "python3", "0", False, 3,
               ("the app was not installed: its install did not finish -- uv's lines above say why; the method",),
               ("the app's block above says why", "not upgraded"), "not ready", ["TCC"], 0),
              ("the-app-left-out-unsaid", go + "missing TCC\nfinish\n", "python3", "0", False, 3,
               ("the app was not installed: the app's block above says why; the method",), (), "not ready", ["TCC"], 0))
    # #142 (SFH 7): a foreign link to nothing is what to remove -- "run this again" made it again, and again. A link,
    # so POSIX only: Git Bash's `ln -s` copies.
    if os.name != "nt":
        cases += (("a-dangling-foreign-link", go + 'ln -s "$HOME/gone" "$SKILL_HOME"\nmissing "the method"\nfinish\n',
                   "python3", "0", False, 3, ("is a link to", "which is not there", "remove that link"),
                   ("the method's step above says why",), "not ready", ["the method"], 0),)
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
                left = re.search(r'METHOD_LEFT="([^"]*)"', body)
                want = {"installer": "install.sh", "installer_sha256": sha,
                        "method_ref": left.group(1) if left else "v3.1.2", "mode": "terminal",
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
        locales = utf8_locales()
        checked.append(f"one release-tag rule: install.sh's is_release_tag (run"
                       f"{', also under LC_ALL=' + locales[0] if locales else ', no en_US UTF-8 locale here'}), "
                       f"upkeep.py's (imported) and install.ps1's Test-ReleaseTag (read, as .NET reads it) answer "
                       f"{len(TAG_RULE_CASES)} names alike (T-45)")
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
    # teaches the opposite of the thing the pairing exists for. One pair, released together (EXAMPLE_PAIR), in every
    # place that shows it -- install.cmd's too: it lists the options it forwards, and a Windows user double-clicks it.
    shown = {"install.sh": (re.findall(r"--skill-ref\s+(v[0-9.]+)", sh), re.findall(r"--tcc-ref\s+(v[0-9.]+)", sh)),
             "install.ps1": (re.findall(r"-SkillRef\s+(v[0-9.]+)", ps1), re.findall(r"-TccRef\s+(v[0-9.]+)", ps1)),
             "install.cmd": (re.findall(r"-SkillRef\s+(v[0-9.]+)\s+-TccRef\s+v[0-9.]+", cmd),
                             re.findall(r"-SkillRef\s+v[0-9.]+\s+-TccRef\s+(v[0-9.]+)", cmd))}
    off = []
    for where, (skill, app) in shown.items():
        if len(skill) != EXAMPLE_PLACES[where] or len(app) != EXAMPLE_PLACES[where]:
            off.append(f"{where} shows the method's version {len(skill)} time(s) and the app's {len(app)}, want "
                       f"{EXAMPLE_PLACES[where]} each{' on one line' if where == 'install.cmd' else ''}")
        off += [f"{where} names {got} for the {what}" for what, got_all, want in
                (("method", skill, EXAMPLE_PAIR[0]), ("app", app, EXAMPLE_PAIR[1])) for got in got_all if got != want]
    if off:
        problems.append(f"the version-pin example is not one pair in all nine places -- want the method's "
                        f"{EXAMPLE_PAIR[0]} with the app's {EXAMPLE_PAIR[1]}, the minor pair the hub's tag ledger "
                        f"records (hub #239): " + "; ".join(off))
    else:
        checked.append(f"the version-pin example is one pair in all nine places: the method's {EXAMPLE_PAIR[0]} "
                       f"with the app's {EXAMPLE_PAIR[1]} (install.sh and install.ps1 twice each, install.cmd once)")

    # 4c. how long an install takes, said one way (E-time): the installers' plan screen, and README.md and FAQ.md.
    times = {"install.sh": re.findall(r"Downloads \$_size; ([^.]+)\.", sh),
             "install.ps1": re.findall(r"Downloads \$size; ([^.]+)\.", ps1)}
    off = [f"{where}'s plan screen says {got}, want {INSTALL_TIMES[where]}" for where, got in times.items()
           if got != INSTALL_TIMES[where]]
    off += [f"{name} does not say {INSTALL_TIME_DOCS!r}" for name in ("README.md", "FAQ.md")
            if INSTALL_TIME_DOCS not in read(ROOT / name)]
    if off:
        problems.append("the install time is not said one way -- " + "; ".join(off) + " (E-time, #142)")
    else:
        checked.append("the install time is said one way: 10 to 20 minutes on a Mac without Apple's tools, 5 to 15 on "
                       "Windows without Git, a few minutes otherwise -- both installers' plan screen, README.md and FAQ.md")

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
    relinked, ran = relink_problems(sh, ps1)
    if relinked:
        problems.extend(relinked)
    elif ran:
        checked.append(f"install.sh's link block, run over {len(RELINK_CASES)} cases: a missing link made again after "
                       f"the update's stops, ours left, a foreign or dangling link and a real folder warned about and "
                       f"left, nothing made by a dry run or a stop; install.ps1 the same and its entry seen with "
                       f"Get-Item -Force (read) (T-38)")
    else:
        checked.append("both installers' update branch makes a missing ~/.claude/skills/autosound-tuning link again, "
                       "after its stops, and install.ps1 sees a dangling junction (read; install.sh's block is not run "
                       "here -- this is Windows, or this bash's ln -s makes no link) (T-38)")
    # The app (#142): every way the app is left out counts it missing -- a failed upgrade over an app from before too.
    app = app_problems(sh, ps1)
    if app:
        problems.extend(app)
    else:
        checked.append(f"install.sh's app block and its line in the checks, run over {len(APP_CASES)} cases: installed "
                       f"now is ready; refused, unreadable behind a proxy (git's own line said), an upgrade that failed "
                       f"over an app from before, an install that failed, and no uv each name TCC missing; install.ps1 "
                       f"counts the same four ways, its arm for an app from before read (#142)")
    for found, ok_line in ((option_problems(sh), f"install.sh's options that take a value say so and end 2 when given "
                                                 f"none, run over {len(OPTION_CASES)} command lines (#142)"),
                           (plugin_check_problems(sh, ps1), "the plugin's check tells a copy that is not as signed "
                                                            "(verify-copy's 3) from one that could not be checked (4): "
                                                            "install.sh's block run, install.ps1's read (#142)"),
                           (ps1_native_problems(ps1), "install.ps1's Run and Test-Quiet count only an exit code that "
                                                      "was set and is 0 -- a native command that could not start is "
                                                      "no success (read) (#142)")):
        if found:
            problems.extend(found)
        else:
            checked.append(ok_line)
    # install.ps1's end and its probes RUN under PowerShell, where there is one (#142): the Windows job's runner.
    ran_ps1, ps1_ran = ps1_run_problems(ps1)
    if ran_ps1:
        problems.extend(ran_ps1)
    elif ps1_ran:
        checked.append(f"install.ps1's end, run under {Path(find_powershell()).name}: nothing missing ends 0 with the "
                       f"receipt ready, numpy missing ends 3 with it not ready; Run and Test-Quiet say $false for a "
                       f"command that is not there or ends 3, $true for one that ends 0 (#142)")
    else:
        checked.append("install.ps1's end, Run and Test-Quiet are NOT run here -- no PowerShell on this machine; the "
                       "Windows job runs them (#142)")
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
    # #142 (PTA 4): the accepted sentence held to the start of a line -- install.ps1's two lines whole (the pattern with
    # `(?m)^`, the principal, the exit code and `-cmatch`), upkeep's `(?m)^` -- and git's "cannot check" sentences too
    # (T6): a signer's user id is printed inside gpg's own line, never at the start of one.
    ps1_whole = ("$good = '(?m)^Good \"git\" signature for ' + [regex]::Escape($SkillSigningPrincipal) + ' with '",
                 "if ($rc -eq 0 -and $said -cmatch $good) {", "if ($said -cmatch '(?m)^(?:")
    read_halves = (("install.ps1", re.search(r"^function Test-TagSignature \{.*?^\}", ps1, re.M | re.S),
                    pinned + ps1_whole),
                   ("upkeep.py", re.search(r"^def verify_tag\(.*?(?=^\S)", up, re.M | re.S),
                    pinned + ("env=env", "(?m)^Good \"git\" signature for ")),
                   ("install.sh", re.search(r"^verify_tag\(\) \{.*?^\}", sh, re.M | re.S),
                    ("grep -q \"^Good \\\"git\\\" signature for $SKILL_SIGNING_PRINCIPAL with \"", "grep -Eq '^(")))
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
    # T-44 (#142): each of fetch-binary's answers read by both installers and written into the receipt's engine in the
    # same words -- 4 (a release with no archive for this platform) is an answer said out loud, not a failure, and 5
    # (no answer at all) is not 4: a re-run later is what helps. Each code in its own arm (PTA 6): install.sh's case RUN
    # per code, install.ps1's arms read one by one.
    engine += engine_answer_problems(sh, ps1)
    engine += engine_gate_problems(sh, ps1)
    if engine:
        problems.extend(engine)
    else:
        checked.append("all three agree on the desk engine: fetched only where nothing can build it -- no .NET SDK, "
                       "or a plugin copy, which is no checkout (install.sh's method_is_checkout run on a clone, a .git "
                       "folder, a .git file and a plugin copy; T-40) -- by the method's own fetch-binary, whose 0, 3, 4 "
                       "and 5 both installers write into the receipt in the same words; a plugin copy's 4 waits for an "
                       "engine, and one that does not run names the repair (T-44)")

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
