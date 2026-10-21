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
    # #171: the beta channel takes a candidate for a newer version over the release before it.
    (["v3.1.2", "beta-v3.1.3-rc1"], "beta-v3.1.3-rc1"),
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
#: The receipt's fields in the order both installers write them: today's seven, then how the run ended, then the
#: Codex link (#149).
RECEIPT_FIELDS = ("installer", "installer_sha256", "method_ref", "mode", "at", "platform", "engine",
                  "installer_version", "status", "missing", "python", "codex_link")
#: The short names a part that is not ready goes by, in both installers. install.ps1 adds the python3 a new window
#: runs, which only Windows gets wrong (`python3 in a new window`).
MISSING_NAMES = ("numpy", "scipy", "the method", "the method (2.x line)", "the beta copy", "TCC", "Claude Code",
                 "Codex link")
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
SIGNING_FUNCTIONS = ("is_release_tag", "release_at_least", "settled_by_name", "verify_tag", "check_tcc_tag",
                     "tcc_tag_still_at")
#: #179: what the app's tag carries from v1.1.4 (TCC's TCC_CONSTRAINTS, uv.lock's export for `[gui,claude]`), and the
#: release that first carries it (TCC's TCC_CONSTRAINTS_FROM). The bytes hold a CRLF and a Cyrillic letter: the copy
#: uv is handed is the signed commit's file as it is, never text a shell or PowerShell decoded and wrote again.
TCC_PINS_NAME = "constraints.txt"
TCC_PINS_BYTES = "# tested with these (a stand-in)\r\npyside6==6.11.2\n# ж\n".encode("utf-8")
TCC_PINS_FROM = "v1.1.4"
#: #179 (the task review): LF only, so a git that converts line ends -- core.autocrlf=true in the person's own
#: configuration -- would hand CRLF to anything that reads the tag through `git archive` without holding it.
TCC_PINS_LF = b"pyside6==6.11.2\nshiboken6==6.11.2\n"
#: ...and that configuration, as a global git config file.
AUTOCRLF_CONFIG = b"[core]\n\tautocrlf = true\n"
#: A `mktemp` that cannot make the copy's folder, and makes every other one (the task review): check_tcc_tag says so,
#: and writes nothing -- "" would have put the copy at /constraints.txt.
NO_PINS_MKTEMP = (b"#!/bin/sh\n"
                  b"case \"$*\" in *autosound-tcc-pins*) echo 'mktemp: cannot (a stand-in)' >&2; exit 1 ;; esac\n"
                  b"exec /usr/bin/mktemp \"$@\"\n")

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
        # #179: the app's tags from v1.1.4 carry `constraints.txt` -- each signed by the author, on a commit of its own:
        # v1.1.4 the file, v1.1.3 and v1.2.0 none, v1.2.1 a folder by that name, v1.2.2 a symbolic link (its index
        # entry written by hand: a Windows git with core.symlinks=false would add a plain file). After `commit` above,
        # which the older tags name.
        author_signed = (*signed, "-c", f"user.signingkey={os.path.join(tmp, 'author')}.pub", "tag", "-s")
        Path(repo, TCC_PINS_NAME).write_bytes(TCC_PINS_BYTES)
        sh_run("git", "-C", repo, "add", TCC_PINS_NAME)
        sh_run("git", "-C", repo, "commit", "-q", "-m", "pins")
        sh_run(*author_signed, "v1.1.4", "-m", "s")
        sh_run("git", "-C", repo, "rm", "-q", TCC_PINS_NAME)
        sh_run("git", "-C", repo, "commit", "-q", "-m", "no pins")
        sh_run(*author_signed, "v1.1.3", "-m", "s")
        sh_run(*author_signed, "v1.2.0", "-m", "s")
        Path(repo, TCC_PINS_NAME).mkdir()
        Path(repo, TCC_PINS_NAME, "x").write_bytes(b"x\n")
        sh_run("git", "-C", repo, "add", TCC_PINS_NAME)
        sh_run("git", "-C", repo, "commit", "-q", "-m", "a folder")
        sh_run(*author_signed, "v1.2.1", "-m", "s")
        sh_run("git", "-C", repo, "rm", "-q", "-r", TCC_PINS_NAME)
        Path(tmp, "link-target").write_bytes(b"elsewhere.txt")
        blob = sh_run("git", "-C", repo, "hash-object", "-w", os.path.join(tmp, "link-target")).strip()
        sh_run("git", "-C", repo, "update-index", "--add", "--cacheinfo", f"120000,{blob},{TCC_PINS_NAME}")
        sh_run("git", "-C", repo, "commit", "-q", "-m", "a link")
        sh_run(*author_signed, "v1.2.2", "-m", "s")
        # v1.3.0: LF only, read under a person's core.autocrlf=true (the task review). The link's index entry goes
        # first (CI 39595279381): under core.symlinks=false -- Windows' git -- a file added over a path the index
        # holds as a link keeps mode 120000, and v1.3.0 was a link too.
        sh_run("git", "-C", repo, "rm", "-q", "--cached", TCC_PINS_NAME)
        Path(repo, TCC_PINS_NAME).write_bytes(TCC_PINS_LF)
        sh_run("git", "-C", repo, "add", TCC_PINS_NAME)
        sh_run("git", "-C", repo, "commit", "-q", "-m", "LF pins")
        sh_run(*author_signed, "v1.3.0", "-m", "s")
        # A tag that is not what its case means is the fixture's failure, said as one -- not the installer's.
        for tag, mode in (("v1.1.4", "100644"), ("v1.2.2", "120000"), ("v1.3.0", "100644")):
            listed = sh_run("git", "-C", repo, "ls-tree", tag, "--", TCC_PINS_NAME).split()
            if not listed or listed[0] != mode:
                raise RuntimeError(f"the fixture's {tag} holds {TCC_PINS_NAME} as {listed[:1] or 'nothing'}, "
                                   f"want mode {mode} (#179)")
        autocrlf = Path(tmp, "autocrlf.gitconfig")
        autocrlf.write_bytes(AUTOCRLF_CONFIG)
        no_mktemp = Path(tmp, "no-mktemp")
        no_mktemp.mkdir()
        (no_mktemp / "mktemp").write_bytes(NO_PINS_MKTEMP)
        (no_mktemp / "mktemp").chmod(0o755)
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
    # #179: the tag's `constraints.txt`, copied out of the scratch repository before it goes -- only a file, byte for
    # byte -- with TMPDIR this case's own folder: when check_tcc_tag is done the copy is the one thing left there (the
    # scratch repository and the signers file gone), and nothing at all when there was no file. (ref, the switch, a dry
    # run, the case's own condition, the copy's bytes or None, words in TCC_PINS_WHY, TCC_FETCHED, a commit handed on.)
    # A tag settled by its name is not fetched, so it hands on neither a copy nor a reason: the app's block says that
    # one (app_problems). The developer's switch skips the signature, not the fetch (tcc #227): the pins come along,
    # no commit does, and a fetch that fails under it installs as the switch always did.
    pin_cases = (("v1.1.4", "", "0", "", TCC_PINS_BYTES, "", "1", True),
                 ("v1.1.3", "", "0", "", None, "v1.1.3 carries no constraints.txt", "1", True),
                 ("v1.2.0", "", "0", "", None, "v1.2.0 carries no constraints.txt", "1", True),
                 ("v1.2.1", "", "0", "", None, "a folder in the tag, not a file (git mode 040000)", "1", True),
                 ("v1.2.2", "", "0", "", None, "a symbolic link in the tag, not a file (git mode 120000)", "1", True),
                 ("v1.1.4", "1", "0", "", TCC_PINS_BYTES, "", "1", False),
                 ("v1.2.0", "1", "0", "", None, "v1.2.0 carries no constraints.txt", "1", False),
                 ("v1.9.9", "1", "0", "", None, "could not fetch v1.9.9", "1", False),
                 ("v1.1.4", "", "1", "", None, "", "", False),
                 ("v0.1.44", "", "0", "", None, "", "", False),
                 # No temporary folder for the copy: said, and nothing written at /constraints.txt.
                 ("v1.1.4", "", "0", "no-mktemp", None, "no temporary folder for the copy", "1", True),
                 # `git show` is the blob's bytes: a person's core.autocrlf=true converts nothing.
                 ("v1.3.0", "", "0", "autocrlf", TCC_PINS_LF, "", "1", True))
    for ref, skip, dry, cond, want_bytes, want_why, want_fetched, want_sha in pin_cases:
        what = f"{ref}{' (skip)' if skip else ''}{' (dry run)' if dry == '1' else ''}{f' ({cond})' if cond else ''}"
        own = Path(tmp, f"pins-tmp-{ref}-{skip or 0}-{dry}-{cond}")
        own.mkdir()
        rc, said = run(f'TMPDIR="{own.as_posix()}"; export TMPDIR\n'
                       'TCC_PINS=stale TCC_PINS_WHY=stale TCC_FETCHED=stale TCC_PINS_MADE=stale\n'
                       f'check_tcc_tag "{ref}" 2>&1; rc=$?\n'
                       'printf "TCC_PINS=[%s]\\nTCC_PINS_WHY=[%s]\\nTCC_FETCHED=[%s]\\nTCC_SHA=[%s]\\nTCC_PINS_MADE=[%s]\\n" '
                       '"${TCC_PINS-unset}" "${TCC_PINS_WHY-unset}" "${TCC_FETCHED-unset}" "${TCC_SHA-unset}" '
                       '"${TCC_PINS_MADE-unset}"\n'
                       'exit $rc\n', skip, dry, config=autocrlf if cond == "autocrlf" else os.devnull,
                       first_on_path=no_mktemp if cond == "no-mktemp" else None)
        got = dict(re.findall(r"^(TCC_PINS|TCC_PINS_WHY|TCC_FETCHED|TCC_SHA|TCC_PINS_MADE)=\[(.*)\]$", said, re.M))
        left = sorted(p.relative_to(own).as_posix() for p in own.rglob("*"))
        wrong = [] if rc == 0 else [f"exit {rc}, want 0"]
        if want_bytes is not None:
            folder = left[0] if left else ""
            copy = own / folder / TCC_PINS_NAME
            if left != [folder, f"{folder}/{TCC_PINS_NAME}"] or not copy.is_file() or copy.is_symlink():
                wrong.append(f"leaves {left} in its TMPDIR, want one folder holding one file {TCC_PINS_NAME}")
            elif copy.read_bytes() != want_bytes:
                wrong.append(f"its copy holds {copy.read_bytes()[:60]!r}, want the tag's bytes {want_bytes[:60]!r}")
            if not got.get("TCC_PINS", "").endswith(f"{folder}/{TCC_PINS_NAME}"):
                wrong.append(f"TCC_PINS is {got.get('TCC_PINS', 'not printed')!r}, want that copy's path")
            if not folder.startswith("autosound-tcc-pins.") \
                    or got.get("TCC_PINS_MADE", "") + f"/{TCC_PINS_NAME}" != got.get("TCC_PINS"):
                wrong.append(f"TCC_PINS_MADE is {got.get('TCC_PINS_MADE', 'not printed')!r}, want the folder it made, "
                             f"autosound-tcc-pins.* in TMPDIR")
        else:
            if left:
                wrong.append(f"leaves {left} in its TMPDIR, want nothing")
            if got.get("TCC_PINS") != "" or got.get("TCC_PINS_MADE") != "":
                wrong.append(f"TCC_PINS is {got.get('TCC_PINS', 'not printed')!r} and TCC_PINS_MADE "
                             f"{got.get('TCC_PINS_MADE', 'not printed')!r}, want both empty")
        why = got.get("TCC_PINS_WHY")
        if why is None or (want_why not in why if want_why else why):
            wrong.append(f"TCC_PINS_WHY is {why if why is not None else 'not printed'!r}, want "
                         + (f"one naming {want_why!r}" if want_why else "empty"))
        if got.get("TCC_FETCHED") != want_fetched:
            wrong.append(f"TCC_FETCHED is {got.get('TCC_FETCHED', 'not printed')!r}, want {want_fetched!r}")
        if bool(got.get("TCC_SHA")) != want_sha:
            wrong.append(f"TCC_SHA is {got.get('TCC_SHA', 'not printed')!r}, want "
                         + ("the verified commit" if want_sha else "empty: nothing was verified"))
        if wrong:
            out.append(f"install.sh check_tcc_tag {what}, the tag's {TCC_PINS_NAME} (#179): " + "; ".join(wrong)
                       + f" -- said {said.strip()[-200:]!r}")
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


def ps1_switch_name_problems(ps1):
    """No variable in install.ps1 takes a [switch] parameter's name; [] when none does.

    PowerShell's names are case-insensitive, so at script scope `$help = ""` IS the parameter `[switch]$Help`, and a
    string does not convert to a switch: the assignment throws. W-11's rc1 on the Windows VM: the TCC step's
    `$help = ""` (uv's --help) stopped the app's install, «Autosound TCC is not installed», while every check was green
    -- the Windows cases run that block outside the script's param(). A function's own variable would only shadow the
    parameter, but one rule for the whole file is the one a reader can hold.
    """
    block = re.search(r"^param\((.*?)^\)", ps1, re.M | re.S)
    if not block:
        return ["install.ps1: no `param( ... )` block -- the switch names cannot be checked"]
    switches = re.findall(r"\[switch\]\$(\w+)", block.group(1))
    first = ps1.count("\n", 0, block.end()) + 1
    out = []
    for n, line in enumerate(ps1.splitlines(), 1):
        if n <= first or line.lstrip().startswith("#"):
            continue
        for name in switches:
            if re.search(rf"\${name}\s*=(?!=)", line, re.I):
                out.append(f"install.ps1:{n}: `${name}` here is the parameter [switch]${name} (names are "
                           f"case-insensitive), and assigning it a value that is not a switch throws -- rename the "
                           f"variable")
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


#: json_str's input and what its output reads as (#172): with iconv a byte that is not UTF-8 is dropped and a UTF-8
#: letter kept; without iconv every byte outside printable ASCII is a `?`. Either way the text is JSON.
JSON_STR_CASES = ((b'a\xff"b', 'a"b', 'a?"b'), ("é".encode("utf-8"), "é", "??"), (b"v\xff", "v", "v?"),
                  ("Київ".encode("utf-8"), "Київ", "?" * 8), ("🎵".encode("utf-8"), "🎵", "????"),
                  # Above U+10FFFF: macOS's iconv -c passed these through as they were (the T5 review) -- a byte
                  # dropped or a `?`, either is JSON.
                  (b"v\xf4\x90\x80\x80", ("v", "v?"), "v????"), (b"v\xf7\xbf\xbf\xbf", ("v", "v?"), "v????"),
                  (b"v\xf8\x88\x80\x80\x80", ("v", "v?"), "v?????"))


def shell_text_problems(sh):
    """#157 and #172: Claude Code's installer piped to bash, and json_str's text JSON whatever bytes reach it.

    Claude's installer is a bash script: piped to `sh`, Ubuntu's dash stops it with `Syntax error: "(" unexpected`, and a
    fresh Ubuntu install ended NOT ready. READ: no `claude.ai/install.sh | sh` left in install.sh, and the command it
    runs and the one it hands the person are both `| bash`. RUN: json_str, cut out, over a byte that is not UTF-8 and
    over a UTF-8 letter -- with iconv and with iconv missing -- gives text `json.loads` reads (the shell's own receipt
    builder, when no python3 runs: a `--skill-ref $'v\\xff'` made a receipt that was not JSON)."""
    import json
    out = []
    if re.search(r"claude\.ai/install\.sh \| sh\b", sh):
        out.append("install.sh still pipes Claude Code's installer to `sh` -- dash cannot run it (#157)")
    # The group round: `run sh -c 'set -o pipefail; ... | bash'` passed the count above, and dash stops on `-o pipefail`
    # without a syntax error -- the wrapper is pinned, bash running the pipe under pipefail.
    step = ("""  if run "${BASH:-bash}" -c 'set -o pipefail; curl -fsSL https://claude.ai/install.sh | bash'; then""")
    if [ln for ln in sh.splitlines() if not ln.lstrip().startswith("#")].count(step) != 1:
        out.append(f"install.sh does not run Claude Code's installer as exactly `{step.strip()}` (#157)")
    if sh.count("curl -fsSL https://claude.ai/install.sh | bash") < 3:
        out.append("install.sh does not run and name Claude Code's installer as `curl -fsSL https://claude.ai/install.sh "
                   "| bash` (the step, its hint, the end's line) (#157)")
    functions, missing = cut_functions(sh, ("have", "json_str"))
    if missing:
        return out + [f"install.sh: no `{name}() {{ ... }}` -- json_str cannot be run (#172)" for name in missing]
    bash, why = find_bash()
    if not bash:
        return out + [f"{why} -- install.sh's json_str cannot be run, and unrun is not agreed (#172)"]
    # (the group round) an iconv that is there and fails -- exit 1, nothing out -- takes the no-iconv path: its empty
    # text made every field of the receipt "".
    for mode in ("iconv", "no iconv", "an iconv that fails"):
        iconv = mode == "iconv"
        if iconv and not shutil.which("iconv"):
            continue
        deny = {"iconv": "", "no iconv": 'have() { [ "$1" != iconv ] && command -v "$1" >/dev/null 2>&1; }\n',
                "an iconv that fails": "iconv() { return 1; }\n"}[mode]
        for raw, with_iconv, without in JSON_STR_CASES:
            word = "$'" + "".join(f"\\x{b:02x}" for b in raw) + "'"
            script = ("set -euo pipefail\n" + functions + deny + f"json_str {word}\n").encode("utf-8")
            r = subprocess.run([bash, "-s"], input=script, capture_output=True)
            try:
                got = json.loads(r.stdout.decode("utf-8"))
            except ValueError as exc:
                got = f"not JSON ({exc}): {r.stdout!r}"
            want = with_iconv if iconv else without
            if r.returncode != 0 or (got not in want if isinstance(want, tuple) else got != want):
                out.append(f"install.sh json_str {word}{'' if iconv else ' with ' + mode}: exit {r.returncode}, "
                           f"{got!r}, want 0 and {want!r} -- stderr {r.stderr.decode('utf-8', 'replace')[-160:]!r} (#172)")
    return out


#: An earlier run's receipt, there before a run that stops before changing anything (#160): it stays byte for byte.
SEEDED_RECEIPT = b'{"installer": "install.sh", "status": "ready", "missing": [], "engine": "fetched v0.1.0"}\n'


def selection_problems(sh, ps1):
    """T-37 (#142): install.sh's `pick_method_ref` RUN with a `git` that has no network; [] when it answers right.

    No tag readable and none named is a stop, exit 1, with nothing on stdout -- an empty `ls-remote` installed an
    unchecked `main`, and moved a verified copy onto it on a re-run. A named branch goes on, said UNSIGNED; a named
    release needs no network to be picked; and with tags readable the newest stable release wins whatever else the
    remote offers. The ref is all that reaches stdout, since the caller takes it with $(...). The call sites in both
    installers, and install.ps1's mirror, are READ: no `main` to fall back on, no app spec without a tag.
    """
    import tempfile
    # The stop is `stop` (#142): it writes the receipt, here into a temp XDG_DATA_HOME, under the call's own `set -u`.
    functions, missing = cut_functions(sh, ("say", "warn", "pretty", "have", "on_mac", "runs_ok", "usable",
                                            "json_str", "write_receipt", "stop", "is_release_tag",
                                            "newest_on_channel", "read_tags", "pick_method_ref", "settled_by_name"))
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
                 # #164: the pick names a branch and says nothing of it -- settled_by_name says it, below.
                 ("main", None, 0, None, "0", False, 0, "main", (), ("is not a release",)),
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
                      # #160: nothing has changed yet when the pick stops (Claude Code was there) -- an earlier
                      # run's receipt, seeded below, stays byte for byte; a stop after a change writes `stopped`
                      # (exit_contract_problems, a-stop).
                      f'DRY_RUN={dry}\n' + functions + ("usable() { return 1; }\n" if nogit else "")
                      + f'ref="$(pick_method_ref "{given}")" || exit $?\nprintf "REF=[%s]\\n" "$ref"\n')
            data, calls = Path(tmp, f"data-{i}"), Path(tmp, f"git-calls-{i}")
            (data / "autosound").mkdir(parents=True)
            (data / "autosound" / "install-receipt.json").write_bytes(SEEDED_RECEIPT)
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
            status = "kept" if receipt.is_file() and receipt.read_bytes() == SEEDED_RECEIPT else \
                f"not kept: {receipt.read_bytes()[:80] if receipt.is_file() else 'gone'!r}"
            want_status = "kept"
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
                           + ", the earlier receipt kept byte for byte (#160)"
                           + (f", and no git run -- it ran {ran_git!r}" if nogit else "")
                           + f" -- stderr {got_err.strip()[-220:]!r} (T-37)")
        # #164: the full path -- the pick, then the signature step every ref passes -- says a branch is not a release
        # exactly once; a dry run's placeholders (the tag globs, when no tag could be read) never, and keep "would".
        # #171: the stable pick takes `v` names only -- a candidate for a newer version stays out though the stand-in
        # git lists it whatever the glob; the beta channel's order takes it.
        pair = Path(tmp, "pair")
        pair.write_bytes(b"v3.1.2\nbeta-v3.1.3-rc1\n")
        beta_only = Path(tmp, "beta-only")
        beta_only.write_bytes(b"beta-v3.1.3-rc1\n")
        full = (("main", None, 128, "0", 'settled_by_name "$ref" v3.0.67', "main", 1, ()),
                ("", None, 128, "1", 'settled_by_name "$ref" v3.0.67; settled_by_name "v*" v0.1.45', "v3.*", 0,
                 ("would check the signature of v3.*", "would check the signature of v*")),
                ("", pair, 0, "0", ":", "v3.1.2", 0, ()),
                # ...and a list of candidates alone is no stable release (a dry run says so and goes on).
                ("", beta_only, 0, "1", ":", "v3.*", 0, ("the remote lists no v3.* release",)))
        for j, (given, offered, stub_rc, dry, then, want_ref, unsigned, words) in enumerate(full):
            script = (f'set -euo pipefail\nexport PATH="$(cd "{stub_dir.as_posix()}" && pwd)":"/usr/bin:$PATH"\n'
                      'SKILL_REPO="https://github.com/ayukhno/autosound-tuning-skill.git"\nSKILL_TAG_GLOB="v3.*"\n'
                      f'DRY_RUN={dry}\n' + functions
                      + f'ref="$(pick_method_ref "{given}")" || exit $?\nprintf "REF=[%s]\\n" "$ref"\n{then}\n')
            env = dict(os.environ, STUB_RC=str(stub_rc), STUB_TAGS=offered.as_posix() if offered else "",
                       HOME=tmp, XDG_DATA_HOME=str(Path(tmp, f"data-full-{j}")))
            env.pop("STUB_SAYS", None)
            env.pop("STUB_LOG", None)
            r = subprocess.run([bash, "-s"], input=script.encode("utf-8"), capture_output=True, env=env)
            said = r.stdout.decode("utf-8", "replace") + r.stderr.decode("utf-8", "replace")
            if (r.returncode != 0 or f"REF=[{want_ref}]" not in said or said.count("is not a release") != unsigned
                    or any(w not in said for w in words)):
                out.append(f"install.sh pick_method_ref {given or '(no --skill-ref)'}"
                           f"{' over ' + offered.read_text().replace(chr(10), ' ').strip() if offered else ''}"
                           f"{', a dry run' if dry == '1' else ''}, then `{then}`: exit {r.returncode}, want 0, "
                           f"REF=[{want_ref}], 'is not a release' {unsigned} time(s) (said {said.count('is not a release')})"
                           + (f" and {' + '.join(map(repr, words))}" if words else "")
                           + f" -- said {said.strip()[-260:]!r} (#164, #171)")
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
    out.extend(one_unsigned_line_problems(sh, ps1, pick_ps1.group(0) if pick_ps1 else ""))
    return out


def one_unsigned_line_problems(sh, ps1, pick_ps1):
    """#164 and #171, READ: the UNSIGNED line lives in settled_by_name / Test-SettledByName alone, said before a dry
    run's "would check" unless the ref is a glob (the dry run's placeholder); the stable picks keep `v` names only, by
    an explicit `^v` right after the tag list is read, and the beta channel's picks do not. install.sh's half is also
    RUN above; install.ps1's under PowerShell, where there is one (ps1_run_problems)."""
    wrong = []
    unsigned = "is not a release: it is installed UNSIGNED, unchecked"
    for where, text in (("install.sh", sh), ("install.ps1", ps1)):
        lines = [ln for ln in text.splitlines() if unsigned in ln and not ln.lstrip().startswith("#")]
        if len(lines) != 1:
            wrong.append(f"{where} says {unsigned!r} on {len(lines)} lines -- once, in its settled-by-name step")
    settled_sh = re.search(r"^settled_by_name\(\) \{.*?^\}", sh, re.M | re.S)
    settled_ps = re.search(r"^function Test-SettledByName \{.*?^\}", ps1, re.M | re.S)
    for where, body, glob, dry in (("install.sh settled_by_name", settled_sh, "*'*'*",
                                    '\n  if [ "$DRY_RUN" = 1 ]; then'),
                                   ("install.ps1 Test-SettledByName", settled_ps, "$Ref -match '[*?]'",
                                    "\n    if ($DryRun) {")):
        text = body.group(0) if body else ""
        at_glob, at_unsigned, at_dry = text.find(glob), text.find(unsigned), text.find(dry)
        if not (0 <= at_glob < at_unsigned < at_dry):
            wrong.append(f"{where} does not guard a glob ({glob}), then say a name is not a release, before a dry "
                         f"run's 'would check' -- a dry run's placeholder would be said UNSIGNED, or a branch's dry "
                         f"run not at all")
    def code_of(text):                                  # a commented `grep '^v'` filters nothing (the test seat)
        return "\n".join(ln for ln in text.splitlines() if not ln.lstrip().startswith("#"))
    pick_sh = re.search(r"^pick_method_ref\(\) \{.*?^\}", sh, re.M | re.S)
    if not pick_sh or """printf '%s\\n' "$TAGS_READ" | grep '^v' | newest_on_channel""" not in code_of(pick_sh.group(0)):
        wrong.append("install.sh pick_method_ref does not keep `v` names only (`grep '^v'`) before newest_on_channel")
    tcc_sh = re.search(r'^    else\n      # Release-shaped tags only, as the method.s \(skill #108\)[^\n]*\n(.*?)^    fi\n',
                       sh, re.M | re.S)
    if not tcc_sh or "grep '^v'" not in code_of(tcc_sh.group(1)):
        wrong.append("install.sh's stable app pick does not keep `v` names only (`grep '^v'`)")
    beta_sh = re.search(r'^  if read_tags "\$SKILL_REPO" "\$SKILL_TAG_GLOB" "\$SKILL_BETA_GLOB"; then\n(.*?)^  fi\n', sh,
                        re.M | re.S)
    if not beta_sh or "grep '^v'" in beta_sh.group(1) or "newest_on_channel" not in beta_sh.group(1):
        wrong.append("install.sh's beta pick of the method does not take candidates through newest_on_channel")
    if "Where-Object { $_ -cmatch '^v' }" not in pick_ps1:
        wrong.append("install.ps1 Select-MethodRef does not keep `v` names only (`Where-Object { $_ -cmatch '^v' }`)")
    if "$tccTags = @($names | Where-Object { $_ -cmatch '^v' } |" not in ps1:
        wrong.append("install.ps1's stable app pick does not keep `v` names only (`Where-Object { $_ -cmatch '^v' }`)")
    if "if ($Channel -eq \"beta\") { $TccRef = Select-NewestOnChannel $names }" not in ps1:
        wrong.append("install.ps1's beta pick of the app does not take candidates through Select-NewestOnChannel")
    # The T6 review: a branch's dry run said "would fetch main ..., check it, and check it out" over "installed
    # UNSIGNED, unchecked" -- the check is said for a release only, in both of each installer's dry-run lines.
    for where, text, name, var in (("install.sh", sh, r"^checkout_method\(\) \{.*?^\}", "$_co_does"),
                                   ("install.ps1", ps1, r"^function Sync-MethodCheckout \{.*?^\}", "$does")):
        fn = re.search(name, text, re.M | re.S)
        lines = [ln for ln in (fn.group(0) if fn else "").splitlines() if "would fetch " in ln]
        if len(lines) != 2 or any(var not in ln or "check it, and" in ln for ln in lines):
            wrong.append(f"{where}'s dry-run fetch lines do not take the check from {var} -- a branch's dry run says "
                         f"it is checked and UNSIGNED at once")
    return [f"the UNSIGNED line and the stable pick (#164, #171): {w}" for w in wrong]


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
                  # #160: where the copy is first changed -- the receipt is armed there, and never before a refusal.
                  "changing() { printf 'CHANGING THE COPY\\n'; }\n"
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
        # #160: a copy refused (2) or not reachable (1) was never changed, so the receipt is not armed: the last real
        # one stays. One that lands (0) or is put back after its checkout (3) was.
        armed = "CHANGING THE COPY" in said
        if rc != want_rc or any(w not in said for w in words) or not state_ok() or armed != (want_rc in (0, 3)):
            out.append(f"install.sh checkout_method, {what}: exit {rc}, {where_is(where)} -- want exit {want_rc}"
                       + (f", saying {' + '.join(map(repr, words))}" if words else "")
                       + f", the receipt {'armed' if want_rc in (0, 3) else 'not armed'} (it was "
                       f"{'armed' if armed else 'not'}, #160) -- said {said.strip()[-220:]!r} (T-45)")
    # #164 (the test seat): a dry run's two returns, which reach no signature step -- a branch is said not a release
    # once, and not "checked"; a release is "checked", and nothing is said UNSIGNED. A new folder, and a copy that is
    # there with no git yet. Nothing is made.
    for what, where, ref, nogit, words, never, unsigned in (
            ("main into a new folder", os.path.join(tmp, "dry-new"), "main", False,
             ("would fetch main into", "and check it out"), ("check it,",), 1),
            ("main over a copy, no git yet", copy, "main", True, ("would fetch main into", "and check it out (no git yet)"),
             ("check it,",), 1),
            ("v3.1.2 into a new folder", os.path.join(tmp, "dry-release"), "v3.1.2", False,
             ("would fetch v3.1.2 into", ", check it, and check it out"), ("UNSIGNED",), 0)):
        script = ('export PATH="/usr/bin:$PATH"\n' + functions
                  + f'DRY_RUN=1\nAUTOSOUND_SKIP_TAG_VERIFY=""\nSKILL_SIGNED_FROM=v3.0.64\nSKILL_REPO="{url}"\n'
                  + "changing() { :; }\n" + ("usable() { return 1; }\n" if nogit else "")
                  + f'checkout_method "{Path(where).as_posix()}" "{ref}" "the method"\n')
        r = subprocess.run([bash, "-s"], input=script.encode("utf-8"), capture_output=True, env=env)
        said = (r.stdout + r.stderr).decode("utf-8", "replace")
        made = not nogit and os.path.exists(where)
        if (r.returncode != 0 or any(w not in said for w in words) or any(w in said for w in never)
                or said.count("is not a release") != unsigned or made):
            out.append(f"install.sh checkout_method in a dry run, {what}: exit {r.returncode}, want 0, "
                       f"{' + '.join(map(repr, words))}, never {' + '.join(map(repr, never))}, 'is not a release' "
                       f"{unsigned} time(s) (said {said.count('is not a release')}){', and it made the folder' if made else ''}"
                       f" -- said {said.strip()[-220:]!r} (#164)")
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
#: #179 (hub #280): a fresh install is held to the tag's constraints.txt, as TCC's own updater is (tcc #194) -- (case,
#: the tag, what check_tcc_tag hands on: a copy of the "file", none ("absent"), a copy from a tag "fetched" under the
#: developer's switch (no commit verified), or nothing for a tag "settled" by its name; the uv: "" new, "old" without
#: `--constraints`, "silent" (its help elsewhere); uv's install exit; the parts missing after; uv given the
#: file; words; words never). One install in every case: a pinned install that fails is not tried again without the
#: file -- a dropped network is not an old uv (TCC's updates.py, the re-review of #194).
APP_PIN_CASES = (
    ("a tag with constraints.txt", "v1.2.0", "file", "", 0, "", True,
     ("held to the versions v1.2.0 was tested with", "✓ installed"), ("uv chooses",)),
    ("a v1.1.3 tag, from before the file", "v1.1.3", "absent", "", 0, "", False, ("✓ installed",),
     ("uv chooses", "could not be read", "held to")),
    ("a v1.2.0 tag without it", "v1.2.0", "absent", "", 0, "", False,
     ("the versions v1.2.0 was tested with could not be read, so uv chooses the versions",
      "v1.2.0 carries no constraints.txt", "✓ installed"), ("held to",)),
    # The version gate (the task review): a candidate counts as its release, and v1.1.10 is above v1.1.4.
    ("a beta-v1.1.4-rc1 tag without it", "beta-v1.1.4-rc1", "absent", "", 0, "", False,
     ("the versions beta-v1.1.4-rc1 was tested with could not be read", "✓ installed"), ("held to",)),
    ("a v1.1.10 tag without it", "v1.1.10", "absent", "", 0, "", False,
     ("the versions v1.1.10 was tested with could not be read", "✓ installed"), ("held to",)),
    ("an old uv", "v1.2.0", "file", "old", 0, "", False,
     ("this uv cannot hold the app to the versions it was tested with (that needs uv 0.5.6 or newer)", "uv 0.4.30",
      "✓ installed"), ("held to", "gave no answer")),
    # A uv whose --help says nothing on its output is not an old uv, and "0.5.6 or newer" would be a guess.
    ("a uv that gives --help no answer", "v1.2.0", "file", "silent", 0, "", False,
     ("uv gave no answer to `uv tool install --help`", "✓ installed"), ("held to", "0.5.6")),
    ("a pinned install that fails", "v1.2.0", "file", "", 1, "TCC", True,
     ("held to the versions v1.2.0 was tested with", "Autosound TCC was not installed"), ("uv chooses",)),
    # The developer's switch: fetched, nothing verified (no commit) -- held to the file all the same (tcc #227).
    ("a tag fetched under the developer's switch", "v1.2.0", "fetched", "", 0, "", True,
     ("held to the versions v1.2.0 was tested with", "✓ installed"), ("uv chooses", "not fetched")),
    ("a tag settled by its name", "v1.2.0", "settled", "", 0, "", False,
     ("v1.2.0 was not fetched, so the versions it was tested with are not read -- uv chooses them", "✓ installed"),
     ("held to",)),
    # ...and a release from before the file, settled by its name: none of those had it, so nothing is said.
    ("a v1.1.3 tag settled by its name", "v1.1.3", "settled", "", 0, "", False, ("✓ installed",),
     ("not fetched", "uv chooses", "held to")))
#: The stand-ins the app's block meets: a `uv` that lists the app, installs it into $LOCAL_BIN or fails as $STUB_UV_RC
#: says; and a `curl` that never reaches the network -- what it hands `sh` ends uv's own installer with 7.
#:   #179: its `tool install --help` names `-c, --constraints` (uv 0.5.6 and newer), or with STUB_UV_HELP=old does not
#: -- an old uv, whose --version says so -- and both name `--build-constraints`, which is not the option; with
#: STUB_UV_HELP=silent it says its help on stderr, and nothing on its output. Before, the
#: probe would have "installed". An install handed `--constraints <file>` copies the file's bytes to $STUB_LOG.pins and
#: its path to $STUB_LOG.pins-path: what uv was given, read while the install runs.
STUB_UV = (b"#!/bin/sh\n"
           b"[ -z \"${STUB_LOG:-}\" ] || printf 'uv %s\\n' \"$*\" >> \"$STUB_LOG\"\n"
           b"case \"$1 ${2:-}\" in\n"
           b"  '--version '*) if [ \"${STUB_UV_HELP:-}\" = old ]; then echo 'uv 0.4.30 (an old stand-in)'; "
           b"else echo 'uv 0.12.10 (a stand-in)'; fi ;;\n"
           b"  'tool list') echo 'autosound-tcc v1.1.2' ;;\n"
           b"  'tool install')\n"
           b"    for a in \"$@\"; do\n"
           b"      [ \"$a\" = --help ] || continue\n"
           b"      [ \"${STUB_UV_HELP:-}\" != silent ] || { echo 'help is elsewhere (a stand-in)' >&2; exit 0; }\n"
           b"      echo 'Usage: uv tool install [OPTIONS] <PACKAGE>'\n"
           b"      [ \"${STUB_UV_HELP:-}\" = old ] || echo '  -c, --constraints <CONSTRAINTS>  Constrain versions using "
           b"the given requirements files'\n"
           b"      echo '      --build-constraints <BUILD_CONSTRAINTS>  Constrain build dependencies'\n"
           b"      exit 0\n"
           b"    done\n"
           b"    held='' last=''\n"
           b"    for a in \"$@\"; do [ \"$last\" != --constraints ] || held=\"$a\"; last=\"$a\"; done\n"
           b"    if [ -n \"$held\" ] && [ -n \"${STUB_LOG:-}\" ]; then\n"
           b"      printf '%s\\n' \"$held\" > \"$STUB_LOG.pins-path\"\n"
           b"      cat \"$held\" > \"$STUB_LOG.pins\" 2>/dev/null || rm -f \"$STUB_LOG.pins\"\n"
           b"    fi\n"
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
    check_line = re.search(r'^if \[ "\$MODE" = "tcc" \] && \[ "\$DRY_RUN" = 0 \]; then\n.*?^fi\n', sh, re.M | re.S)
    functions, missing = cut_functions(sh, ("say", "warn", "have", "runs_ok", "usable", "run", "pretty", "in_local_bin",
                                            "find_bin", "manifest_add", "is_missing", "missing", "newest_on_channel",
                                            "is_release_tag", "release_at_least",
                                            "read_tags"))
    if not block or not check_line or missing:
        return [f"install.sh: the app's block, its line in the checks, or {missing} -- the app cannot be run (#142)"]
    bash, why = find_bash()
    if not bash:
        return [f"{why} -- install.sh's app block cannot be run, and unrun is not agreed"]
    tmp = tempfile.mkdtemp(prefix="autosound_app_")

    def run_block(i, offered, ls_rc, check, have_uv, uv_rc, before, dry, uv_help="", tcc_ref=""):
        """The app's block and its line in the checks, run once with `check` in check_tcc_tag's place: (said, the
        stand-ins' calls, the case's folder, the MISSING/MODE line, what is wrong with the run itself)."""
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
                  + check.replace("@HOME@", home.as_posix())
                  + 'tcc_tag_still_at() { return 0; }\n'
                  + ('usable() { return 1; }\n' if dry else '')
                  + f'export PATH="$(cd "{stub.as_posix()}" && pwd):/usr/bin:/bin"\n'
                  + f'LOCAL_BIN="{(home / "bin").as_posix()}"; export LOCAL_BIN\n'
                  + f'MANIFEST="{(home / "manifest").as_posix()}"\nAPP="{(home / "no.app").as_posix()}"\n'
                  + f'DESKTOP_LINK="{(home / "no-link").as_posix()}"\n'
                  + f'MODE=tcc\nCHANNEL=stable\nTCC_REF="{tcc_ref}"\nDRY_RUN={1 if dry else 0}\nMISSING=""\nUV_VERSION=0.12.10\n'
                  + f'TCC_CONSTRAINTS_FROM={TCC_PINS_FROM}\n'
                  # install.sh's early globals for the copy, cleared before the run goes ahead (#179, the re-review).
                  + 'TCC_PINS=""\nTCC_PINS_MADE=""\nTCC_PINS_WHY=""\nTCC_FETCHED=""\n'
                  + 'TCC_REPO="https://github.com/ayukhno/autosound-tcc"\nTCC_TAG_GLOB="v*"\nTCC_BETA_GLOB="beta-v*"\n'
                  + block.group(0) + check_line.group(0)
                  + 'printf "MISSING=[%s] MODE=[%s]\\n" "$MISSING" "$MODE"\n')
        env = dict(os.environ, HOME=home.as_posix(), STUB_TAGS=tags.as_posix() if offered else "",
                   STUB_RC=str(ls_rc), STUB_SAYS=SSL_SAYS, STUB_UV_RC=str(uv_rc), STUB_UV_HELP=uv_help,
                   STUB_LOG=(home / "calls").as_posix())
        env.pop("UV_TOOL_BIN_DIR", None)
        r = subprocess.run([bash, "-s"], input=script.encode("utf-8"), capture_output=True, env=env)
        said = (r.stdout + r.stderr).decode("utf-8", "replace")
        got = re.search(r"MISSING=\[(.*?)\] MODE=\[(.*?)\]", said)
        calls = (home / "calls").read_text(encoding="utf-8") if (home / "calls").exists() else ""
        wrong = [] if r.returncode == 0 else [f"exit {r.returncode}"]
        if "curl" in calls and "astral.sh" not in calls:
            wrong.append(f"curl was asked for something other than uv's installer: {calls!r}")
        return said, calls, home, got, wrong

    try:
        for i, (case, offered, ls_rc, signed, have_uv, uv_rc, before, want_missing, want_mode, words, *dry_never) \
                in enumerate(APP_CASES):
            dry, never = dry_never if dry_never else (False, ())
            said, calls, home, got, wrong = run_block(
                i, offered, ls_rc, 'check_tcc_tag() { TCC_SHA=""; return %d; }\n' % (0 if signed else 1), have_uv,
                uv_rc, before, dry)
            if not got or got.group(1) != want_missing or got.group(2) != want_mode:
                wrong.append(f"ends with {got.group(0) if got else 'no MISSING line'}, want MISSING=[{want_missing}] "
                             f"MODE=[{want_mode}]")
            wrong += [f"never says {w!r}" for w in words if w not in said]
            wrong += [f"says {w!r}" for w in never if w in said]
            if dry and "git " in calls:
                wrong.append(f"a dry run with no git yet ran git: {calls!r}")
            if wrong:
                out.append(f"install.sh's app block, {case}: " + "; ".join(wrong) + f" -- said {said.strip()[-260:]!r}")
        # #179: the tag's constraints.txt, as check_tcc_tag hands it on -- a copy (TCC_PINS), or why there is none
        # (TCC_PINS_WHY), or neither for a tag settled by its name (TCC_SHA "") -- and what the block does with it.
        for j, (case, ref, pins, uv_help, uv_rc, want_missing, want_held, words, never) in enumerate(APP_PIN_CASES):
            # A verified tag hands on its commit; one fetched under the switch none; one settled by its name nothing.
            sha = "0123456789abcdef0123456789abcdef01234567" if pins in ("file", "absent") else ""
            fetched = "" if pins == "settled" else "1"
            if pins in ("file", "fetched"):
                check = ('check_tcc_tag() { TCC_SHA="%s"; TCC_FETCHED=%s; mkdir -p "@HOME@/pins"; '
                         'cp "@HOME@/pins.src" "@HOME@/pins/%s"; TCC_PINS="@HOME@/pins/%s"; TCC_PINS_MADE="@HOME@/pins"; '
                         'TCC_PINS_WHY=""; }\n' % (sha, fetched, TCC_PINS_NAME, TCC_PINS_NAME))
            else:
                why = f"{ref} carries no {TCC_PINS_NAME}" if pins == "absent" else ""
                check = ('check_tcc_tag() { TCC_SHA="%s"; TCC_FETCHED="%s"; TCC_PINS=""; TCC_PINS_WHY="%s"; }\n'
                         % (sha, fetched, why))
            Path(tmp, f"case-pins-{j}").mkdir(parents=True)
            Path(tmp, f"case-pins-{j}", "pins.src").write_bytes(TCC_PINS_BYTES)
            said, calls, home, got, wrong = run_block(f"pins-{j}", None, 0, check, True, uv_rc, False, False, uv_help,
                                                      tcc_ref=ref)
            if not got or got.group(1) != want_missing or got.group(2) != "tcc":
                wrong.append(f"ends with {got.group(0) if got else 'no MISSING line'}, want MISSING=[{want_missing}] "
                             f"MODE=[tcc]")
            wrong += [f"never says {w!r}" for w in words if w not in said]
            wrong += [f"says {w!r}" for w in never if w in said]
            installs = [ln for ln in calls.splitlines() if ln.startswith("uv tool install ") and "--help" not in ln]
            probes = [ln for ln in calls.splitlines() if ln.startswith("uv tool install ") and "--help" in ln]
            if len(installs) != 1:
                wrong.append(f"{len(installs)} install(s), want exactly one -- never a retry: {installs!r}")
            held = [ln for ln in installs if " --constraints " in ln]
            if want_held and not held:
                wrong.append(f"uv was not given --constraints: {installs!r}")
            if not want_held and held:
                wrong.append(f"uv was given --constraints: {held!r}")
            if want_held:
                given = home / "calls.pins"
                if not given.is_file() or given.read_bytes() != TCC_PINS_BYTES:
                    wrong.append(f"uv read {given.read_bytes()[:60] if given.is_file() else 'no file'!r} from "
                                 f"--constraints, want the tag's bytes")
            if pins in ("file", "fetched") and len(probes) != 1:
                wrong.append(f"uv's --help was asked {len(probes)} time(s) before the install, want once")
            if pins not in ("file", "fetched") and probes:
                wrong.append(f"uv's --help was asked with no file to hold it to: {probes!r}")
            if (home / "pins").exists():
                wrong.append(f"the copy of {TCC_PINS_NAME} is left after the install: "
                             f"{sorted(p.name for p in (home / 'pins').iterdir())}")
            if wrong:
                out.append(f"install.sh's app block, {case} (#179): " + "; ".join(wrong)
                           + f" -- said {said.strip()[-300:]!r}")
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
              in sh, "install.sh notes an app from before (TCC_KEPT) for the end's line"),
             # #179: install.ps1's half of the tag's constraints.txt, READ (Test-TccTag's copy is RUN where PowerShell
             # is, ps1_tcc_pins_problems): uv's --help asked first, one install line that takes the file, and the three
             # ways of installing without it said as install.sh says them.
             ("@tccForce @tccHeld $TccSpec" in ps1 and len(re.findall(r"tool install --quiet --python 3\.12", ps1)) == 1,
              "install.ps1 has one app install line, and it hands uv @tccHeld (#179)"),
             ("tool install --help" in ps1 and '.Contains(" --constraints ")' in ps1,
              "install.ps1 asks uv's tool install --help for ' --constraints ' before the install (#179)"),
             # The re-review: the EXIT trap removes TCC_PINS_MADE's folder, so no value from the environment may reach
             # it -- the early globals clear it before the run goes ahead, with TCC_PINS beside it.
             (all(re.search(rf"^{v}=\"\"$", sh, re.M) and re.search(r"^going_ahead$", sh, re.M)
                  and re.search(rf"^{v}=\"\"$", sh, re.M).start() < re.search(r"^going_ahead$", sh, re.M).start()
                  for v in ("TCC_PINS", "TCC_PINS_MADE")),
              "install.sh clears TCC_PINS and TCC_PINS_MADE among its early globals, before going_ahead arms the "
              "EXIT trap that removes the copy (#179)"),
             (all(w in ps1 for w in ("this uv cannot hold the app to the versions it was tested with (that needs uv "
                                     "0.5.6 or newer)", "was tested with could not be read, so uv chooses the versions",
                                     "was not fetched, so the versions it was tested with are not read -- uv chooses "
                                     "them", "held to the versions $TccRef was tested with")),
              "install.ps1 says an old uv, a release without its constraints.txt and a tag not fetched as install.sh "
              "does (#179)"))
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


#: #149 (T17b): the user-level link Codex finds the method by -- OpenAI's docs (learn.chatgpt.com/docs/build-skills):
#: Codex scans `$HOME/.agents/skills` and follows a symlinked skill folder. Both installers make it when `codex` is on
#: PATH, or always with the option; on Windows a junction. The link is the installers' own when the installer-manifest
#: records its target (`codex-link <target>`, one line) and the target holds no `..`: that one is kept, or repointed when
#: the method moves -- whether or not codex is on PATH (a link made with the option for Codex's app stays looked after).
#: Anything else there is left as it is. With the option, a link not made is a missing part. The receipt's
#: `codex_link` says what the step did.
CODEX_OPTION = {"install.sh": "--codex", "install.ps1": "-Codex"}
CODEX_PATH = {"install.sh": 'CODEX_LINK_PATH="${HOME}/.agents/skills/autosound-tuning"',
              "install.ps1": '$CodexLink = Join-Path $HOME ".agents\\skills\\autosound-tuning"'}
#: The receipt's codex_link, in both installers: the first five the link step's, `not reached` a run that stopped
#: before it. `skipped: ` carries why.
CODEX_VALUES = ("made", "repointed", "kept", "skipped: ", "absent", "not reached")
#: The manifest line that records the link's target -- the installers' ownership of it.
CODEX_RECORD = "codex-link "
#: (case, codex on PATH, the option given, a dry run, what is at the link's place before, the target the manifest
#: records (None: no line), the target the step is given (None: the method is not this installer's), codex_link (a
#: prefix for `skipped: `), "Codex link" missing after, words, never, what is there after). Places: `clone` the method's
#: clone, `plugin` a plugin copy of it, `old` an older plugin copy (gone, so a link to it dangles), `foreign` somebody's
#: folder, `dotdot` the clone's path climbed out of with `..` to that folder; `folder` and `file` real ones at the link's
#: place, `locked` a ~/.agents nothing can be written in (POSIX only).
CODEX_CASES = (
    ("no-codex", False, False, False, None, None, "clone", "absent", False, ("no Codex on PATH", "<option>"),
     ("made the link",), "nothing"),
    ("codex-on-path", True, False, False, None, None, "clone", "made", False, ("made the link",), ("would",), "clone"),
    ("the-option-no-codex", False, True, False, None, None, "clone", "made", False, ("made the link",),
     ("no Codex on PATH",), "clone"),
    ("a-dry-run", True, False, True, None, None, "clone", "made", False, ("would make the link",), ("made the link",),
     "nothing"),
    ("a-dry-run-no-codex", False, False, True, None, None, "clone", "absent", False, ("no Codex on PATH", "<option>"),
     ("would make",), "nothing"),
    ("ours-already", True, False, False, "clone", "clone", "clone", "kept", False, ("already points at the method",),
     ("made the link", "repointed"), "clone"),
    ("ours-already-no-codex", False, False, False, "clone", "clone", "clone", "kept", False,
     ("already points at the method",), ("no Codex on PATH",), "clone"),
    ("ours-older", True, False, False, "old", "old", "plugin", "repointed", False, ("repointed the link",), (),
     "plugin"),
    # The Silent-failure seat's Important: made once with the option (Codex's app, nothing on PATH), the link is still
    # ours after a plugin update -- repointed, and the receipt does not say there is none.
    ("ours-older-no-codex", False, False, False, "old", "old", "plugin", "repointed", False, ("repointed the link",),
     ("no Codex on PATH",), "plugin"),
    ("ours-older-a-dry-run", True, False, True, "old", "old", "plugin", "repointed", False,
     ("would repoint the link",), ("repointed the link",), "old"),
    ("the-clone-link-a-plugin-target", True, False, False, "clone", "clone", "plugin", "repointed", False,
     ("repointed the link",), (), "plugin"),
    ("somebody-elses-link", True, False, False, "foreign", "clone", "clone", "skipped: ", False,
     ("not this installer's -- left as it is",), ("made the link", "repointed"), "foreign"),
    ("somebody-elses-link-the-option", False, True, False, "foreign", None, "clone", "skipped: ", True,
     ("not this installer's -- left as it is",), ("made the link", "repointed"), "foreign"),
    # Ownership is the manifest's, not a path's shape: a link into the plugins folder nobody recorded is somebody's.
    ("a-link-into-plugins-unrecorded", True, False, False, "old", None, "plugin", "skipped: ", False,
     ("not this installer's -- left as it is",), ("repointed",), "old"),
    ("a-dotdot-link-recorded", True, False, False, "dotdot", "dotdot", "clone", "skipped: ", False,
     ("not this installer's -- left as it is",), ("repointed",), "foreign"),
    ("a-dotdot-target", True, False, False, None, None, "dotdot", "skipped: ", False, ("holds a `..`",),
     ("made the link",), "nothing"),
    ("a-real-folder", True, True, False, "folder", None, "clone", "skipped: ", True,
     ("a folder this installer did not make -- left as it is",), ("made the link",), "folder"),
    ("a-plain-file", True, False, False, "file", None, "clone", "skipped: ", False,
     ("a file this installer did not make -- left as it is",), ("made the link",), "file"),
    ("an-unwritable-agents", True, True, False, "locked", None, "clone", "skipped: ", True, ("could not make",),
     ("made the link",), "nothing"),
    ("the-method-not-ours", True, False, False, None, None, None, "skipped: ", False,
     ("the method at ~/.claude/skills/autosound-tuning is not this installer's",), ("made the link",), "nothing"))
#: The tools install.sh's Codex functions run, and nothing else on their PATH.
CODEX_SH_TOOLS = ("mkdir", "ln", "readlink", "dirname", "grep", "mv", "rm", "ls", "rmdir")
#: What the method is not, said when the method's step left the link's place as it was.
CODEX_NOT_OURS = "the method at ~/.claude/skills/autosound-tuning is not this installer's"
#: The uninstall's Codex part: (case, what is at the link's place, the target the manifest records, a dry run, words,
#: never, what is there after, the manifest's codex-link target after (None: no line), a file put beside the link
#: (`skills` in ~/.agents/skills, `agents` in ~/.agents, None: none), the folders there after (`both`, `agents` alone,
#: `neither`)). #181: the link gone, ~/.agents/skills and then ~/.agents are removed when that leaves them empty --
#: never with anything in them (somebody's), never on a dry run, and only after this script's own link went.
CODEX_UNLINK_CASES = (
    ("ours", "clone", "clone", False, ("removing the Codex link",), ("left alone", "could not remove"), "nothing",
     None, None, "neither"),
    ("ours-a-dry-run", "clone", "clone", True, ("removing the Codex link", "would"), (), "clone", "clone", None,
     "both"),
    ("ours-a-sibling-in-skills", "clone", "clone", False, ("removing the Codex link",),
     ("left alone", "could not remove"), "nothing", None, "skills", "both"),
    ("ours-more-in-agents", "clone", "clone", False, ("removing the Codex link",), ("left alone", "could not remove"),
     "nothing", None, "agents", "agents"),
    ("somebody-elses-link", "foreign", "clone", False, ("not ours, left alone",), ("removing",), "foreign", "clone",
     None, "both"),
    ("ours-in-shape-unrecorded", "clone", None, False, ("not ours, left alone",), ("removing",), "clone", None, None,
     "both"),
    ("a-real-folder", "folder", None, False, ("not a link this script made",), ("removing",), "folder", None, None,
     "both"),
    ("nothing-there", None, "clone", False, (), ("removing", "left alone"), "nothing", "clone", None, "neither"),
    # The group seat: ~/.agents, or ~/.agents/skills, a link (a junction on Windows) to a folder of somebody's, which
    # the link's removal leaves empty -- the linked folder and its target stay, and nothing tries to remove them.
    ("ours-agents-a-linked-folder", "clone", "clone", False, ("removing the Codex link",),
     ("left alone", "could not remove"), "nothing", None, "agents-linked", "agents"),
    ("ours-skills-a-linked-folder", "clone", "clone", False, ("removing the Codex link",),
     ("left alone", "could not remove"), "nothing", None, "skills-linked", "both"))


def _codex_linked(home, beside, junction=False):
    """#181 (the group seat): before the case's link is made, ~/.agents (`agents-linked`) or ~/.agents/skills
    (`skills-linked`) as a link to a folder of somebody's, ~/theirs-agents -- a symbolic link, or a junction on Windows,
    as the person would make one. None for any other case."""
    if beside not in ("agents-linked", "skills-linked"):
        return None
    elsewhere = Path(home, "theirs-agents")
    elsewhere.mkdir(parents=True)
    at = Path(home, ".agents") if beside == "agents-linked" else Path(home, ".agents", "skills")
    at.parent.mkdir(parents=True, exist_ok=True)
    if junction:
        import _winapi
        _winapi.CreateJunction(str(elsewhere), str(at))
    else:
        os.symlink(elsewhere, at)
    return at


def _codex_linked_problems(at):
    """#181: the linked folder and its target are both still there after the uninstall."""
    if at is None:
        return []
    out = [] if os.path.lexists(at) and at.is_dir() else [f"the linked folder {at.name} is gone"]
    return out + ([] if Path(at.parent if at.name == ".agents" else at.parent.parent, "theirs-agents").is_dir()
                  else ["the linked folder's target is gone"])


def _codex_beside(link, beside):
    """#181: the case's file of somebody's beside the Codex link -- in ~/.agents/skills or in ~/.agents."""
    if beside in ("skills", "agents"):
        folder = link.parent if beside == "skills" else link.parent.parent
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "theirs").write_text("theirs\n")


def _codex_folders(link):
    """#181: which of ~/.agents/skills and ~/.agents are there: `both`, `agents` (alone), `neither`, or `skills alone`."""
    skills, agents = link.parent.is_dir(), link.parent.parent.is_dir()
    return "both" if skills and agents else "agents" if agents else "neither" if not skills else "skills alone"


def codex_read_problems(sh, ps1):
    """#149: what both installers must agree on, READ -- the option (parsed, in --help), the link's path, the receipt's
    `codex_link` and its values, the step called after the method's, the end's line, ownership by the manifest, a
    missing "Codex link" under the option, and the uninstall going through its run function. `[]` when they do."""
    out = []
    for where, text in (("install.sh", sh), ("install.ps1", ps1)):
        opt = CODEX_OPTION[where]
        if where == "install.sh":
            parsed = re.search(r"^\s*--codex\)\s+WANT_CODEX=1 ;;", sh, re.M)
            usage = re.search(r"^usage\(\) \{.*?^\}", sh, re.M | re.S)
            helped = usage and "install.sh --codex" in usage.group(0)
            values = [v for v in CODEX_VALUES if not re.search(r'CODEX_DID="' + re.escape(v), sh)]
            called = re.search(r'^changing\n(?:#[^\n]*\n)*if \[ -n "\$METHOD_LEFT" \]; then codex_link "" ', sh, re.M)
            said = "$CODEX_SAID" in (re.search(r'^step "Checking"\n.*?(?=^step ")', sh, re.M | re.S) or [""])[0]
            gone = re.search(r'^if \[ "\$UNINSTALL" = 1 \]; then\n.*?^fi\n', sh, re.M | re.S)
            unlinks = gone and re.search(r"^\s*codex_unlink\s*$", gone.group(0), re.M)
            ours = re.search(r"^codex_ours\(\) \{.*?^\}", sh, re.M | re.S)
            by_manifest = ours and 'grep -qxF "codex-link $1" "$MANIFEST"' in ours.group(0)
            asked = re.search(r'^\s*\[ "\$WANT_CODEX" != 1 \] \|\| missing "Codex link"\s*$', sh, re.M)
        else:
            parsed = re.search(r"^\s*\[switch\]\$Codex,", ps1, re.M)
            usage = re.search(r'^if \(\$Help\) \{\n.*?^\}', ps1, re.M | re.S)
            helped = usage and "install.ps1 -Codex" in usage.group(0)
            values = [v for v in CODEX_VALUES if not re.search(r'\$script:CodexDid = "' + re.escape(v), ps1)]
            called = re.search(r'^Enter-Change\n(?:#[^\n]*\n)*if \(\$MethodLeft\) \{ Set-CodexLink "" ', ps1, re.M)
            said = "$script:CodexSaid" in (re.search(r'^Step "Checking"\n.*?(?=^Step ")', ps1, re.M | re.S) or [""])[0]
            gone = re.search(r'^if \(\$Uninstall\) \{\n.*?^\}\n', ps1, re.M | re.S)
            unlinks = gone and re.search(r"^\s*Remove-CodexLink\s*$", gone.group(0), re.M)
            ours = re.search(r"^function Test-CodexOurs \{\n.*?^\}", ps1, re.M | re.S)
            by_manifest = ours and "@(Read-ManifestLines)" in ours.group(0) \
                and '"codex-link "' in ours.group(0)
            asked = re.search(r'^\s*if \(\$Codex\) \{ Add-Missing "Codex link" \}\s*$', ps1, re.M)
        wrong = []
        if CODEX_PATH[where] not in text:
            wrong.append(f"the link's path is not `{CODEX_PATH[where]}`")
        if not parsed:
            wrong.append(f"{opt} is not an option")
        if not helped:
            wrong.append(f"--help does not name {opt}")
        if values:
            wrong.append(f"codex_link never says {values}")
        if not called:
            wrong.append("the link step is not called right after the run's first change, after the method's step, "
                         "with no target when the method was left as it was")
        if not said:
            wrong.append("the end's Checking block does not say the link in its one line")
        if not unlinks:
            wrong.append("the uninstall does not take the link off through its run function")
        if not by_manifest:
            wrong.append("the link's ownership is not the installer-manifest's `codex-link <target>` line")
        if not asked:
            wrong.append(f"a link not made under {opt} is not a missing \"Codex link\"")
        if wrong:
            out.append(f"{where}, the Codex link (#149): " + "; ".join(wrong))
    if "codex_link" not in RECEIPT_FIELDS:
        out.append("the receipt's fields do not hold codex_link (#149)")
    if "New-Item -ItemType Junction -Path $tmp -Target $Target" not in ps1:
        out.append("install.ps1's Codex link is not a junction made under a temporary name (`New-Item -ItemType "
                   "Junction -Path $tmp -Target $Target`) -- a symlink needs Developer Mode or an elevated prompt, and "
                   "a repoint that removes first can leave no link (#149)")
    if 'ln -sfn "$_cx_to" "$CODEX_LINK_PATH"' not in sh:
        out.append("install.sh's Codex link is not replaced in one step (`ln -sfn`) -- a repoint that removes first can "
                   "leave no link (#149)")
    return out


def _codex_places(home, posix):
    """The places CODEX_CASES name, under <home>: `(spelled, paths)` -- the path strings as the installer under test
    spells them, and the Paths."""
    src = home / ".claude" / "skills" / ".autosound-tuning-src"
    cache = home / ".claude" / "plugins" / "cache" / "m" / "autosound-tuning"
    places = {"clone": src / "skills" / "autosound-tuning", "plugin": cache / "3.1.3" / "skills" / "autosound-tuning",
              "old": cache / "3.1.2" / "skills" / "autosound-tuning", "foreign": home / "elsewhere"}
    spell = (lambda p: p.as_posix()) if posix else str
    spelled = {k: spell(v) for k, v in places.items()}
    sep = "/" if posix else "\\"
    spelled["dotdot"] = spelled["clone"] + sep + sep.join([".."] * 5) + sep + "elsewhere"
    return spelled, places


def _codex_state(link, places):
    """What is at the Codex link's place: `nothing`, `folder` (a real one, its `mine` inside), `file`, the name in
    `places` a link or junction there points at -- read with os.readlink, which reads a junction too, dangling or not
    -- or `something else`."""
    if not os.path.lexists(link):
        return "nothing"
    try:
        to = os.readlink(link)
    except (OSError, ValueError):
        return "folder" if (Path(link) / "mine").is_dir() else "file" if Path(link).is_file() else "something else"
    for prefix in ("\\\\?\\", "\\??\\"):
        to = to[len(prefix):] if to.startswith(prefix) else to

    def norm(p):
        return os.path.normcase(os.path.abspath(str(p)))
    return next((name for name in ("clone", "plugin", "old", "foreign") if norm(to) == norm(places[name])),
                f"something else ({to})")


def _codex_manifest_problems(manifest, want_codex):
    """The manifest after a case: the other installer's line (`uv`) kept, and the codex-link lines exactly
    `want_codex` (a target, or None for none)."""
    lines = manifest.read_text(encoding="utf-8-sig").splitlines() if manifest.is_file() else []
    wrong = [] if "uv" in lines else [f"the manifest lost its other lines: {lines!r}"]
    got = [ln[len(CODEX_RECORD):] for ln in lines if ln.startswith(CODEX_RECORD)]
    want = [want_codex] if want_codex else []
    if [os.path.normcase(g) for g in got] != [os.path.normcase(w) for w in want]:
        wrong.append(f"the manifest records {got!r}, want {want!r}")
    return wrong


def _codex_case_problems(said, did, missing, words, never, option, state, after):
    """The verdict on one CODEX_CASES run, from what it printed."""
    got = re.search(r"^CODEX_DID=\[(.*)\]\s*$", said, re.M)
    line = re.search(r"^CODEX_SAID=\[(.*)\]\s*$", said, re.M)
    parts = re.search(r"^MISSING=\[(.*)\]\s*$", said, re.M)
    wrong = []
    if not got or not (got.group(1).startswith(did) if did.endswith(": ") else got.group(1) == did):
        wrong.append(f"codex_link is {got.group(1) if got else None!r}, want {did!r}")
    elif did.endswith(": ") and len(got.group(1)) <= len(did):
        wrong.append("codex_link says `skipped:` and not why")
    if not parts or ("Codex link" in parts.group(1)) != missing:
        wrong.append(f"the parts missing are {parts.group(1) if parts else None!r}, want "
                     f"{'Codex link' if missing else 'none'} ({'the option given' if option else 'no option'})")
    wrong += [f"never says {w!r}" for w in words
              if w not in said and w.replace("~/", "~\\").replace("/", "\\") not in said]
    wrong += [f"says {w!r}" for w in never if w in said]
    if not line or not line.group(1):
        wrong.append("no line for the end's Checking block")
    if state != after:
        wrong.append(f"the link's place holds {state}, want {after}")
    return wrong


def codex_link_problems(sh):
    """#149: install.sh's `codex_link` and `codex_unlink`, cut out and RUN over CODEX_CASES and CODEX_UNLINK_CASES in a
    scratch HOME -- a stand-in `codex` on a PATH of its own (or none), a manifest holding another line (`uv`) and the
    case's `codex-link`, under `set -euo pipefail`. `(problems, ran)`; Windows reads it (Git Bash's `ln -s` copies),
    and the Windows job runs install.ps1's own."""
    import tempfile
    functions, missing = cut_functions(sh, ("say", "warn", "have", "pretty", "run", "is_missing", "missing",
                                            "codex_safe", "codex_ours", "codex_record", "codex_skip", "codex_link",
                                            "codex_unlink"))
    if missing:
        return [f"install.sh: no `{name}() {{ ... }}` -- the Codex link cannot be run (#149)" for name in missing], False
    bash, why = find_bash()
    if not bash:
        return [f"{why} -- install.sh's Codex link cannot be run, and unrun is not agreed (#149)"], False
    if os.name == "nt":
        return [], False
    root = os.geteuid() == 0 if hasattr(os, "geteuid") else False
    out = []
    tmp = os.path.realpath(tempfile.mkdtemp(prefix="autosound_codex_"))
    locked = []
    # The functions' PATH is the stand-in's folder and one holding links to the few tools they run -- never the
    # machine's own /usr/bin or /usr/local/bin, where a CI image may carry a real `codex` and every "no codex" case
    # would pass or fail on the image, not on the installer.
    tools = Path(tmp, "tools")
    tools.mkdir()
    for tool in CODEX_SH_TOOLS:
        found = shutil.which(tool)
        if not found:
            shutil.rmtree(tmp, ignore_errors=True)
            return [f"no `{tool}` here -- install.sh's Codex link cannot be run, and unrun is not agreed (#149)"], False
        os.symlink(found, tools / tool)

    def fixture(case, on_path, before, recorded):
        home = Path(tmp, case)
        stub = home / "stub-bin"
        stub.mkdir(parents=True)
        if on_path:
            (stub / "codex").write_bytes(b"#!/bin/sh\nexit 0\n")
            (stub / "codex").chmod(0o755)
        spelled, places = _codex_places(home, posix=True)
        for name in ("clone", "plugin", "foreign"):
            places[name].mkdir(parents=True)
        link = home / ".agents" / "skills" / "autosound-tuning"
        if before in ("clone", "plugin", "old", "foreign", "dotdot"):
            link.parent.mkdir(parents=True, exist_ok=True)
            os.symlink(spelled[before], link)
        elif before == "folder":
            (link / "mine").mkdir(parents=True)
        elif before == "file":
            link.parent.mkdir(parents=True)
            link.write_text("mine\n")
        elif before == "locked":
            (home / ".agents").mkdir()
            (home / ".agents").chmod(0o555)
            locked.append(home / ".agents")
        manifest = home / ".local" / "share" / "autosound" / "installer-manifest"
        manifest.parent.mkdir(parents=True)
        manifest.write_text("uv\n" + (f"{CODEX_RECORD}{spelled[recorded]}\n" if recorded else ""))
        head = ('set -euo pipefail\n' + functions + 'CODEX_DID="not reached"\nCODEX_SAID=""\nMISSING=""\n'
                + 'CODEX_LINK_PATH="${HOME}/.agents/skills/autosound-tuning"\n'
                + 'MANIFEST="${HOME}/.local/share/autosound/installer-manifest"\n')
        return home, stub, spelled, places, link, manifest, head

    def run(home, stub, script):
        r = subprocess.run([bash, "-s"], input=script.encode("utf-8"), capture_output=True,
                           env=dict(os.environ, HOME=home.as_posix(), PATH=f"{stub.as_posix()}:{tools.as_posix()}"))
        return r.returncode, (r.stdout + r.stderr).decode("utf-8", "replace")

    try:
        for case, on_path, option, dry, before, recorded, target, did, want_missing, words, never, after in CODEX_CASES:
            if before == "locked" and root:
                continue                                # root writes through any mode: the case cannot be made
            home, stub, spelled, places, link, manifest, head = fixture(case, on_path, before, recorded)
            call = f'codex_link "{spelled[target]}"' if target else f'codex_link "" "{CODEX_NOT_OURS}"'
            rc, said = run(home, stub, head + f'DRY_RUN={int(dry)}\nWANT_CODEX={"1" if option else "auto"}\n' + call
                           + '\nprintf "CODEX_DID=[%s]\\nCODEX_SAID=[%s]\\nMISSING=[%s]\\n" "$CODEX_DID" "$CODEX_SAID" '
                             '"$MISSING"\n')
            for p in locked:
                p.chmod(0o755)
            wrong = [f"exit {rc}, want 0"] if rc else []
            wrong += _codex_case_problems(said, did, want_missing, [w.replace("<option>", "--codex") for w in words],
                                          never, option, _codex_state(link, places), after)
            if before == "folder" and not (link / "mine").is_dir():
                wrong.append("the real folder's content is gone")
            if before == "file" and link.is_file() and link.read_text() != "mine\n":
                wrong.append("the file's content is changed")
            made = did in ("made", "repointed", "kept") and not dry
            wrong += _codex_manifest_problems(manifest, spelled[target] if made else
                                              (spelled[recorded] if recorded else None))
            if wrong:
                out.append(f"install.sh's Codex link, {case}: " + "; ".join(wrong) + f" -- said {said.strip()[-240:]!r}"
                           " (#149)")
        for case, before, recorded, dry, words, never, after, codex_after, beside, folders in CODEX_UNLINK_CASES:
            linked = _codex_linked(Path(tmp, "unlink-" + case), beside)
            home, stub, spelled, places, link, manifest, head = fixture("unlink-" + case, False, before, recorded)
            _codex_beside(link, beside)
            rc, said = run(home, stub, head + f"DRY_RUN={int(dry)}\ncodex_unlink\n")
            linked_wrong = _codex_linked_problems(linked)
            wrong = [f"exit {rc}, want 0"] if rc else []
            wrong += [f"never says {w!r}" for w in words if w not in said]
            wrong += [f"says {w!r}" for w in never if w in said]
            state = _codex_state(link, places)
            if state != after:
                wrong.append(f"the link's place holds {state}, want {after}")
            if _codex_folders(link) != folders:
                wrong.append(f"~/.agents/skills and ~/.agents: {_codex_folders(link)} there, want {folders} (#181)")
            if before == "folder" and not (link / "mine").is_dir():
                wrong.append("the real folder's content is gone")
            wrong += _codex_manifest_problems(manifest, spelled[codex_after] if codex_after else None) + linked_wrong
            if wrong:
                out.append(f"install.sh's uninstall of the Codex link, {case}: " + "; ".join(wrong)
                           + f" -- said {said.strip()[-240:]!r} (#149)")
    except OSError as exc:
        out.append(f"the Codex link's fixtures could not be made ({exc}) -- unrun is not agreed (#149)")
    finally:
        for p in locked:
            try:
                p.chmod(0o755)
            except OSError:
                pass
        shutil.rmtree(tmp, ignore_errors=True)
    return out, True


def manifest_encoding_problems(ps1):
    """The final review's I2, READ (RUN on the Windows job, ps1_codex_link_problems): install.ps1 reads and writes its
    installer-manifest one way -- Read-ManifestLines / Write-ManifestLines, UTF-8 named on both sides through .NET.
    Set-Content -Encoding UTF8 writes no BOM under PowerShell 7, and 5.1's Get-Content with no -Encoding reads a
    BOM-less file in the ANSI code page: a `codex-link C:\\Users\\<Cyrillic>\\...` line written by one and read by the
    other made the installer's own junction "not this installer's"."""
    out = []
    enc = "(New-Object System.Text.UTF8Encoding $false)"
    read_fn = re.search(r"^function Read-ManifestLines \{.*?^\}", ps1, re.M | re.S)
    write_fn = re.search(r"^function Write-ManifestLines \{.*?^\}", ps1, re.M | re.S)
    if not read_fn or f"[System.IO.File]::ReadAllLines($Manifest, {enc})" not in read_fn.group(0) \
            or not write_fn or f"[System.IO.File]::WriteAllLines($Manifest, [string[]]$Lines, {enc})" \
            not in write_fn.group(0):
        out.append(f"install.ps1 has no Read-ManifestLines / Write-ManifestLines naming UTF-8 on both sides -- "
                   f"[System.IO.File]::ReadAllLines / WriteAllLines with {enc} (#149, I2)")
    code = [(n, ln) for n, ln in enumerate(ps1.splitlines(), 1) if not ln.lstrip().startswith("#")]
    out.extend(f"install.ps1:{n}: the manifest read or written by a cmdlet ({ln.strip()[:70]!r}) -- its encoding then "
               f"differs between PowerShell 5.1 and 7; Read-ManifestLines / Write-ManifestLines (#149, I2)"
               for n, ln in code if re.search(r"\b(?:Get|Set|Add)-Content\b[^|;]*\$Manifest\b", ln))
    return out


def ps1_codex_link_problems(ps1):
    """#149: install.ps1's Set-CodexLink and Remove-CodexLink, cut out and RUN under PowerShell over CODEX_CASES and
    CODEX_UNLINK_CASES -- where there is one: the Windows job's runner; `(problems, ran)`. The links are junctions made
    by the case's own script, as the installer makes them; a stand-in `codex.cmd` on a PATH of its own, or none; the
    `locked` case is POSIX's alone."""
    import tempfile
    shell = find_powershell()
    # Windows alone (CI 38543860362): GitHub's Ubuntu image ships pwsh, and a junction is Windows' -- these cases are
    # the installer's Windows half, not PowerShell's on any system.
    if not shell or os.name != "nt":
        return [], False
    cut, lacking = [], []
    for name in ("Say", "Warn", "Have", "Pretty", "Add-Missing", "Read-ManifestLines", "Write-ManifestLines",
                 "Add-ManifestEntry", "Test-ManifestEntry", "Test-CodexOurs", "Set-CodexRecord", "Set-CodexLink",
                 "Remove-CodexLink"):
        m = (re.search(rf"^function {re.escape(name)}\s+\{{[^\n]*\}}[ \t]*$", ps1, re.M)
             or re.search(rf"^function {re.escape(name)} \{{\n.*?^\}}", ps1, re.M | re.S))
        (cut.append(m.group(0)) if m else lacking.append(name))
    if lacking:
        return [f"install.ps1: no {lacking} to run under PowerShell (#149)"], True
    out = []
    # Long names (CI 38542204702): Windows' TEMP is an 8.3 short path (RUNNER~1), and a junction reads its target back
    # long -- every comparison then failed on the spelling, not on the link.
    tmp = os.path.realpath(tempfile.mkdtemp(prefix="autosound_ps1_codex_"))
    sysroot = os.environ.get("SystemRoot", "C:\\Windows")

    def fixture(case, on_path, before, recorded):
        home = Path(tmp, case)
        stub = home / "stub-bin"
        stub.mkdir(parents=True)
        if on_path:
            (stub / "codex.cmd").write_bytes(b"@exit /b 0\r\n")
        spelled, places = _codex_places(home, posix=False)
        for name in ("clone", "plugin", "old", "foreign"):
            places[name].mkdir(parents=True)
        link = home / ".agents" / "skills" / "autosound-tuning"
        make = ""
        if before in ("clone", "plugin", "old", "foreign", "dotdot"):
            make = (f"New-Item -ItemType Directory -Force -Path '{link.parent}' | Out-Null\n"
                    f"New-Item -ItemType Junction -Path '{link}' -Target '{spelled[before]}' | Out-Null\n")
        elif before == "folder":
            (link / "mine").mkdir(parents=True)
        elif before == "file":
            link.parent.mkdir(parents=True)
            link.write_text("mine\n")
        manifest = home / "manifest" / "installer-manifest"
        manifest.parent.mkdir(parents=True)
        manifest.write_text("uv\n" + (f"{CODEX_RECORD}{spelled[recorded]}\n" if recorded else ""))
        # The older plugin copy is gone: a junction to it dangles, as one left by an uninstalled plugin version.
        gone = f"Remove-Item -Recurse -Force '{places['old']}'\n"
        head = (f'$ErrorActionPreference = "Continue"\n$env:PATH = "{stub};{sysroot}\\System32"\n'
                f"$CodexLink = '{link}'\n$Manifest = '{manifest}'\n"
                '$script:CodexDid = "not reached"\n$script:CodexSaid = ""\n$script:Missing = @()\n'
                + "\n".join(cut) + "\n" + make + gone)
        return home, spelled, places, link, manifest, head

    def run(home, body):
        script = home / "case.ps1"
        script.write_bytes(body.encode("utf-8"))
        r = subprocess.run([shell, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File",
                            str(script)], capture_output=True, timeout=120, env=powershell_env())
        return r.returncode, (r.stdout + r.stderr).decode("utf-8", "replace")

    try:
        for case, on_path, option, dry, before, recorded, target, did, want_missing, words, never, after in CODEX_CASES:
            if before == "locked":
                continue
            home, spelled, places, link, manifest, head = fixture(case, on_path, before, recorded)
            call = f"Set-CodexLink '{spelled[target]}'" if target else f'Set-CodexLink "" "{CODEX_NOT_OURS}"'
            rc, said = run(home, head + f"$DryRun = ${str(dry).lower()}\n$Codex = ${str(option).lower()}\n" + call
                           + '\nWrite-Host "CODEX_DID=[$($script:CodexDid)]"\nWrite-Host "CODEX_SAID=[$($script:CodexSaid)]"'
                             '\nWrite-Host "MISSING=[$($script:Missing -join \', \')]"\n')
            wrong = [f"exit {rc}, want 0"] if rc else []
            wrong += _codex_case_problems(said, did, want_missing, [w.replace("<option>", "-Codex") for w in words],
                                          never, option, _codex_state(link, places), after)
            made = did in ("made", "repointed", "kept") and not dry
            wrong += _codex_manifest_problems(manifest, spelled[target] if made else
                                              (spelled[recorded] if recorded else None))
            if wrong:
                out.append(f"install.ps1's Codex link under {Path(shell).name}, {case}: " + "; ".join(wrong)
                           + f" -- said {said.strip()[-300:]!r} (#149)")
        for case, before, recorded, dry, words, never, after, codex_after, beside, folders in CODEX_UNLINK_CASES:
            linked = _codex_linked(Path(tmp, "unlink-" + case), beside, junction=True)
            home, spelled, places, link, manifest, head = fixture("unlink-" + case, False, before, recorded)
            _codex_beside(link, beside)
            rc, said = run(home, head + f"$DryRun = ${str(dry).lower()}\nRemove-CodexLink\n")
            wrong = [f"exit {rc}, want 0"] if rc else []
            wrong += [f"never says {w!r}" for w in words if w not in said]
            wrong += [f"says {w!r}" for w in never if w in said]
            state = _codex_state(link, places)
            if state != after:
                wrong.append(f"the link's place holds {state}, want {after}")
            if _codex_folders(link) != folders:
                wrong.append(f"~/.agents/skills and ~/.agents: {_codex_folders(link)} there, want {folders} (#181)")
            wrong += _codex_manifest_problems(manifest, spelled[codex_after] if codex_after else None)
            wrong += _codex_linked_problems(linked)
            if wrong:
                out.append(f"install.ps1's uninstall of the Codex link under {Path(shell).name}, {case}: "
                           + "; ".join(wrong) + f" -- said {said.strip()[-300:]!r} (#149)")
        # The final review's I2: a user folder in Cyrillic. A codex-link line written without a BOM, as PowerShell 7
        # wrote it, is this installer's own under 5.1; Set-CodexRecord and Add-ManifestEntry write UTF-8 that both
        # read back. The name is built from code points: this case's script has no BOM, and 5.1 reads it as ANSI.
        home, spelled, places, link, manifest, head = fixture("cyrillic-home", False, "none", None)
        body = (head + "$DryRun = $false\n$name = -join ([char]0x41E, [char]0x43B, [char]0x435, [char]0x433)\n"
                f"$t = '{home}\\' + $name + '\\clone'\n"
                "[System.IO.File]::WriteAllText($Manifest, \"uv`ncodex-link $t`n\", (New-Object System.Text.UTF8Encoding $false))\n"
                'Write-Host "OURS-AFTER-PWSH7=$(Test-CodexOurs $t)"\n'
                'Write-Host "RECORDED=$(Set-CodexRecord $t)"\nAdd-ManifestEntry "agy"\n'
                'Write-Host "OURS-AFTER-51=$(Test-CodexOurs $t) AGY=$(Test-ManifestEntry \'agy\') UV=$(Test-ManifestEntry \'uv\')"\n')
        rc, said = run(home, body)
        try:
            text = manifest.read_bytes().decode("utf-8-sig")
        except (OSError, UnicodeDecodeError) as exc:
            text = f"unreadable as UTF-8 ({exc})"
        want_line = "codex-link " + str(home) + "\\\u041e\u043b\u0435\u0433\\clone"
        if rc or "OURS-AFTER-PWSH7=True" not in said or "RECORDED=True" not in said \
                or "OURS-AFTER-51=True AGY=True UV=True" not in said or want_line not in text.splitlines():
            out.append(f"install.ps1's manifest under {Path(shell).name}, a Cyrillic user folder: exit {rc} -- want the "
                       f"BOM-less line read as ours, and the line written back as UTF-8 beside uv and agy; the file "
                       f"holds {text[:200]!r} -- said {said.strip()[-300:]!r} (#149, I2)")
    except (OSError, subprocess.SubprocessError) as exc:
        out.append(f"install.ps1's Codex link could not be run under {shell} ({exc}) -- unrun is not agreed (#149)")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return out, True


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


#: #161: a cmdlet, as install.ps1 spells one -- Verb-Noun, the verb one PowerShell approves of.
PS1_CMDLET = re.compile(r"(?<![\w$.-])(?:Add|Clear|Compress|ConvertFrom|ConvertTo|Copy|Disable|Enable|Expand|Format|"
                        r"ForEach|Get|Import|Invoke|Join|Measure|Move|New|Out|Pop|Push|Read|Register|Remove|Rename|"
                        r"Resolve|Restart|Resume|Select|Set|Sort|Split|Start|Stop|Suspend|Tee|Test|Unblock|Update|Wait|"
                        r"Where|Write)-[A-Z]\w*")


#: What the NEW tag's upkeep.py needs beside it to keep local changes (skill #91): the modules it imports, each falling
#: back when missing -- rew_tool/bounded_run.py since #167. Relative to skills/autosound-tuning.
KEEP_LOCAL_FILES = ("scripts/upkeep.py", "rew_tool/gates/side_effect.py", "rew_tool/console.py", "rew_tool/bounded_run.py")


def keep_local_problems(sh, ps1):
    """#167, READ: install.sh's keep_local and install.ps1's Save-LocalChanges copy the same files out of the new tag
    for its upkeep.py -- KEEP_LOCAL_FILES, rew_tool/bounded_run.py among them -- and install.ps1 archives only those
    the tag has: `git archive` refuses the whole list over one path an older tag lacks."""
    out = []
    fn_sh = re.search(r"^keep_local\(\) \{.*?^\}", sh, re.M | re.S)
    m_sh = re.search(r"for _kl_f in ([^;]*); do", fn_sh.group(0) if fn_sh else "")
    got_sh = tuple(m_sh.group(1).split()) if m_sh else ()
    fn_ps = re.search(r"^function Save-LocalChanges \{.*?^\}", ps1, re.M | re.S)
    m_ps = re.search(r"\$keep = @\(([^)]*)\)", fn_ps.group(0) if fn_ps else "")
    got_ps = tuple(p.removeprefix("skills/autosound-tuning/") for p in re.findall(r'"([^"]+)"', m_ps.group(1))) \
        if m_ps else ()
    for where, got in (("install.sh keep_local", got_sh), ("install.ps1 Save-LocalChanges", got_ps)):
        if set(got) != set(KEEP_LOCAL_FILES):
            out.append(f"{where} copies {list(got)} for the new upkeep.py, not {list(KEEP_LOCAL_FILES)} (#167)")
    body = fn_ps.group(0) if fn_ps else ""
    if "ls-tree --name-only FETCH_HEAD -- @keep" not in body or "FETCH_HEAD @have" not in body:
        out.append("install.ps1 Save-LocalChanges archives files the new tag may not have -- `git archive` then gives "
                   "nothing at all; want `ls-tree --name-only FETCH_HEAD -- @keep` and `FETCH_HEAD @have` (#167)")
    out.extend(keep_local_run_problems(sh, ps1))
    out.extend(claude_step_problems(sh))
    return out


#: A `git` for keep_local alone: `status` names one changed file, the new tag's upkeep.py is $UPKEEP_STUB, and any other
#: file of the tag is not there (an older tag, without bounded_run.py and the rest).
KEEP_LOCAL_GIT = (b"#!/bin/sh\n"
                  b'case "$*" in\n'
                  b'  *" status "*) echo " M a"; exit 0 ;;\n'
                  b'  *" show FETCH_HEAD:skills/autosound-tuning/scripts/upkeep.py") cat "$UPKEEP_STUB"; exit 0 ;;\n'
                  b'  *" show "*) echo "fatal: path not in FETCH_HEAD" >&2; exit 128 ;;\n'
                  b"esac\nexit 0\n")


#: The new tag's upkeep.py for keep_local's run: it names the files beside it that are there -- (#167) one the tag lacks
#: must be missing, never an empty file an import then loads -- says it ran, and fails (it reset the copy, then a locked
#: file stopped its clean).
KEEP_LOCAL_UPKEEP = (b"import os, sys\n"
                     b"root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))\n"
                     b"names = ('rew_tool/gates/side_effect.py', 'rew_tool/console.py', 'rew_tool/bounded_run.py')\n"
                     b"print('BESIDE', [n for n in names if os.path.exists(os.path.join(root, n))])\n"
                     b"print('UPKEEP RAN: reset, then a locked file')\n"
                     b"sys.exit(1)\n")


def claude_step_problems(sh):
    """#160 (the final review's M3), RUN: install.sh's Claude Code step, cut out as it stands, arms the receipt only when
    the installer ran or left its binary -- a download that failed and left nothing changed nothing, and a later stop
    then keeps the last receipt. `run` stands in for the installer; `changing` says it was called."""
    import tempfile
    block = re.search(r'^step "Claude Code"\n.*?^fi\n', sh, re.M | re.S)
    functions, missing = cut_functions(sh, ("in_local_bin",))
    if not block or missing:
        return ["install.sh: no Claude Code step (`step \"Claude Code\"` ... `fi`) or in_local_bin to run (#160)"]
    bash, why = find_bash()
    if not bash:
        return [f"{why} -- install.sh's Claude Code step cannot be run, and unrun is not agreed (#160)"]
    out = []
    # The stand-in binary carries a #! line: Git for Windows' bash (MSYS) takes a file with no extension as executable
    # by that line alone, so an empty one read as absent there (CI 38547555900).
    tmp = tempfile.mkdtemp(prefix="autosound_claude_step_")
    try:
        for case, run_body, want in (("the download fails, nothing left", "return 1", False),
                                     ("it fails, its binary left", "printf '#!/bin/sh\\n' > \"$LOCAL_BIN/claude\"; chmod +x \"$LOCAL_BIN/claude\"; return 1",
                                      True),
                                     ("it installs", "printf '#!/bin/sh\\n' > \"$LOCAL_BIN/claude\"; chmod +x \"$LOCAL_BIN/claude\"; return 0", True)):
            home = Path(tmp, str(len(os.listdir(tmp))))
            (home / "bin").mkdir(parents=True)
            script = ('set -euo pipefail\n' + functions + f'LOCAL_BIN="{(home / "bin").as_posix()}"\n'
                      'step() { :; }\nsay() { :; }\nwarn() { :; }\nmanifest_add() { :; }\n'
                      'find_bin() { in_local_bin "$1" && printf %s "$LOCAL_BIN/$1"; }\n'
                      "changing() { echo ARMED; }\n" + f"run() {{ {run_body}; }}\n" + block.group(0) + "echo END\n")
            r = subprocess.run([bash, "-s"], input=script.encode("utf-8"), capture_output=True)
            said = (r.stdout + r.stderr).decode("utf-8", "replace")
            if r.returncode or "END" not in said or ("ARMED" in said) != want:
                out.append(f"install.sh's Claude Code step, {case}: exit {r.returncode}, the receipt "
                           f"{'armed' if 'ARMED' in said else 'not armed'} -- want {'armed' if want else 'not armed'} "
                           f"-- said {said.strip()[-200:]!r} (#160)")
    except OSError as exc:
        out.append(f"the Claude Code step's fixtures could not be made ({exc}) -- unrun is not agreed (#160)")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return out


def keep_local_run_problems(sh, ps1):
    """#160 (the group round), RUN: keep_local arms the receipt (`changing`) before the new upkeep.py runs -- it writes
    the patch and resets the copy, and a locked file can stop it after the reset -- and a failure then is said as upkeep
    says it, never "nothing was reset". install.ps1's Save-LocalChanges is READ: Enter-Change before the upkeep call,
    the same words."""
    import tempfile
    out = []
    functions, missing = cut_functions(sh, ("say", "warn", "pretty", "keep_local"))
    if missing:
        return [f"install.sh: no `{name}() {{ ... }}` -- keep_local cannot be run (#160)" for name in missing]
    bash, why = find_bash()
    if not bash:
        return [f"{why} -- install.sh's keep_local cannot be run, and unrun is not agreed (#160)"]
    tmp = tempfile.mkdtemp(prefix="autosound_keep_")
    try:
        stub = Path(tmp, "stub")
        stub.mkdir()
        (stub / "git").write_bytes(KEEP_LOCAL_GIT)
        (stub / "git").chmod(0o755)
        Path(tmp, "upkeep.py").write_bytes(KEEP_LOCAL_UPKEEP)
        py_dir = Path(sys.executable).parent.as_posix()
        script = (f'export PATH="$(cd "{stub.as_posix()}" && pwd)":"{py_dir}":"/usr/bin:$PATH"\n' + functions
                  + f'DRY_RUN=0\nLOCAL_CHANGES="{Path(tmp, "patches").as_posix()}"\n'
                  + "offer() { return 1; }\nchanging() { echo 'ARMED BEFORE UPKEEP'; }\npython3() { "
                  + f'"{Path(sys.executable).as_posix()}" "$@"; }}\n'
                  + f'keep_local "{Path(tmp, "copy").as_posix()}" "the method"\n')
        r = subprocess.run([bash, "-s"], input=script.encode("utf-8"), capture_output=True,
                           env=dict(os.environ, UPKEEP_STUB=Path(tmp, "upkeep.py").as_posix()))
        said = (r.stdout + r.stderr).decode("utf-8", "replace")
        armed, ran = said.find("ARMED BEFORE UPKEEP"), said.find("UPKEEP RAN")
        if "BESIDE []" not in said:
            out.append(f"install.sh keep_local copies a file the new tag does not have as an EMPTY file -- the new upkeep.py "
                       f"then imports an empty module (#167) -- said {said.strip()[-200:]!r}")
        if r.returncode != 1 or not 0 <= armed < ran or "nothing was reset" in said \
                or "see above: upkeep says what it kept and reset" not in said:
            out.append(f"install.sh keep_local, the new upkeep.py failing after its reset: exit {r.returncode}, want 1, "
                       f"`changing` before upkeep runs and 'see above: upkeep says what it kept and reset', never "
                       f"'nothing was reset' -- said {said.strip()[-300:]!r} (#160)")
    except OSError as exc:
        out.append(f"keep_local's fixtures could not be made ({exc}) -- unrun is not agreed (#160)")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    fn = re.search(r"^function Save-LocalChanges \{.*?^\}", ps1, re.M | re.S)
    body = fn.group(0) if fn else ""
    at_arm, at_call = body.find("Enter-Change"), body.find("& $Py3 $tool --clone $Dir keep-local")
    if not 0 <= at_arm < at_call or "nothing was reset" in body or "see above: upkeep says what it kept and reset" not in body:
        out.append("install.ps1 Save-LocalChanges does not arm the receipt (Enter-Change) before the new upkeep.py runs, "
                   "or says 'nothing was reset' over a failure after its reset (#160)")
    return out


def windows_start_problems(ps1, cmd):
    """#161 and #162, READ (the Windows job RUNS both): install.ps1 under Windows PowerShell 5.1 resets PSModulePath to
    5.1's own -- the machine's and the user's values and $PSHOME\\Modules -- before its first cmdlet, and hands the same
    reset to the child PowerShell of every upstream installer; install.cmd tells a double click by Explorer's exact
    command line, not by `/c` and its own name, which PowerShell's `& .\\install.cmd` has too."""
    out = []
    code = "\n".join(ln for ln in ps1.splitlines() if not ln.lstrip().startswith("#"))
    param_end = re.search(r"^\[CmdletBinding\(\)\]\nparam\(\n.*?^\)\n", code, re.M | re.S)
    # The T9 review: only a path that holds PowerShell 7's own folders is reset -- under the README one-liner the
    # person's own window keeps its Documents\WindowsPowerShell\Modules and what its profile added -- and the user's
    # Documents folder (where 5.1 itself looks, OneDrive's when redirected) leads, no empty entry anywhere. The group
    # round (CI run 38537781090): `-match '\\PowerShell\\'` also took SQL Server's `...\Tools\PowerShell\Modules\`, a
    # 5.1 entry of the runner's machine value, so pwsh's folders are named exactly: the user's and the machine's
    # Documents\ / Program Files\PowerShell\Modules, and a Modules folder beside a pwsh.exe ($PSHOME's). Both lines are
    # RUN under PowerShell where there is one (ps1_run_problems: SQL Server's entry left as it is).
    folders_def = re.search(r"^\$Ps51PwshFolders = \{ [^\n]*\}$", code, re.M)
    reset_def = re.search(r"^\$Ps51ModulePath = \{ if \(\$PSVersionTable\.PSEdition -eq 'Desktop' -and "
                          r"@\(& \$Ps51PwshFolders\)\.Count -gt 0\) \{ [^\n]*\} \}$", code, re.M)
    reset_run = re.search(r"^\. \$Ps51ModulePath$", code, re.M)
    folders = folders_def.group(0) if folders_def else ""
    body = reset_def.group(0) if reset_def else ""
    lacking = [w for w in ("[Environment]::GetFolderPath('MyDocuments')", "'\\WindowsPowerShell\\Modules'",
                           "[Environment]::GetEnvironmentVariable('PSModulePath', 'Machine')",
                           "[Environment]::GetEnvironmentVariable('PSModulePath', 'User')", "($PSHOME + '\\Modules')",
                           "-split ';') -ne '')", "-join ';'") if w not in body]
    lacking += [w for w in ("'\\PowerShell\\Modules'", "$env:ProgramFiles", "'\\pwsh.exe'", "-contains")
                if w not in folders]
    if body and not body.find("GetFolderPath('MyDocuments')") < body.find("'PSModulePath', 'Machine'"):
        lacking.append("the Documents folder first")
    if re.search(r"-match '\\\\PowerShell\\\\'", code):
        lacking.append("no `-match '\\\\PowerShell\\\\'` -- it takes SQL Server's Tools\\PowerShell\\Modules for pwsh's")
    if (not param_end or not folders_def or not reset_def or not reset_run or lacking or '"' in body + folders
            or PS1_CMDLET.search(body + folders)):
        out.append("install.ps1 has no `$Ps51PwshFolders = { ... }` naming pwsh's own module folders and no "
                   "`$Ps51ModulePath = { if ($PSVersionTable.PSEdition -eq 'Desktop' -and @(& $Ps51PwshFolders).Count "
                   "-gt 0) { ... } }` run by `. $Ps51ModulePath` -- the Documents folder, the machine's and the user's "
                   "values and $PSHOME\\Modules, no cmdlet and no double quote in either"
                   + (f"; it lacks {lacking}" if lacking else "") + " (#161)")
    else:
        first = PS1_CMDLET.search(code, param_end.end())
        if not param_end.end() <= folders_def.start() < reset_def.start() < reset_run.start() \
                or (first and first.start() < reset_run.start()):
            out.append(f"install.ps1 runs `{first.group(0) if first else '?'}` before it resets PSModulePath -- under "
                       f"PowerShell 7's module path Windows PowerShell 5.1 cannot load its own cmdlets (#161)")
    upstream = re.search(r"^function Invoke-Upstream \{.*?^\}", ps1, re.M | re.S)
    if not upstream or '$cmd = "`$Ps51PwshFolders = {$Ps51PwshFolders}; $Ps51ModulePath; [Net.ServicePointManager]' \
            not in upstream.group(0):
        out.append("install.ps1 Invoke-Upstream's child PowerShell does not reset PSModulePath first -- "
                   "`$cmd = \"`$Ps51PwshFolders = {$Ps51PwshFolders}; $Ps51ModulePath; ...` (#161)")
    # #162: Explorer starts a .cmd as `cmd.exe /c ""<full path>" "`; PowerShell as `/c ""<path>" <args>"`.
    want = ('set "SELF=%~f0"', 'set "CMDLINE=!cmdcmdline!"', 'set "CMDTAIL=!CMDLINE:*/c =!"',
            'set "EXPLORER=""!SELF!" ""', 'set "RUNAS="!SELF!" "', 'if /i "!CMDTAIL!"=="!EXPLORER!" set "DOUBLECLICKED=1"',
            'if /i "!CMDTAIL!"=="!RUNAS!" set "DOUBLECLICKED=1"')
    lacking = [w for w in want if w not in cmd]
    # (the group round) a `!` in the path: SELF and PS1 are set before delayed expansion is on, and read as !PS1!.
    at_setlocal = cmd.find("setlocal EnableDelayedExpansion")
    for line in ('set "SELF=%~f0"', 'set "PS1=%~dp0install.ps1"'):
        if not 0 <= cmd.find(line) < at_setlocal:
            lacking.append(f"{line} before setlocal")
    if "%PS1%" in cmd:
        lacking.append("no %PS1% (a `!` in the path is eaten after it expands): !PS1!")
    if lacking or re.search(r'find /i "/c"', cmd, re.I):
        out.append(f"install.cmd does not tell a double click by Explorer's exact command line -- lacking {lacking}"
                   + ("; it still takes `/c` and its own name" if re.search(r'find /i "/c"', cmd, re.I) else "")
                   + " (#162)")
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
PS1_RUN_FUNCTIONS = ("Stop-Installer", "Write-Receipt", "Enter-Change", "Enter-TentativeChange",
                     "Undo-TentativeChange", "Get-PathStamps", "Test-PathsChanged", "Select-ToolReason",
                     "Invoke-Upstream", "Sync-MethodCheckout",
                     "Save-LocalChanges", "Add-Missing", "Say", "Warn", "Pretty", "Run", "Test-Quiet",
                     "Test-ReleaseTag", "Test-SettledByName", "Select-MethodRef", "Select-NewestOnChannel")
#: #164, #171: install.ps1's tag pick over a stand-in tag list -- Read-ReleaseTags answers $script:StubTags, or nothing
#: with $script:StubWhy -- then the signature step every ref passes. (case, body, the words, how many times "is not a
#: release" is said.)
PS1_PICK_HEAD = ('$SkillRepo = "https://example.invalid/skill.git"\n$SkillTagGlob = "v3.*"\n'
                 '$SkillSignedFrom = "v3.0.64"\n$script:TagsWhy = ""\n$script:StubTags = @()\n$script:StubWhy = ""\n'
                 'function Read-ReleaseTags { param([string]$Repo, [string[]]$Globs) $script:TagsWhy = $script:StubWhy; '
                 'return @($script:StubTags) }\n')
PS1_PICK_CASES = (
    ("pick-main", '$ref = Select-MethodRef "main"\nWrite-Host "REF=[$ref]"\n$null = Test-SettledByName $ref $SkillSignedFrom\n',
     ("REF=[main]", "main is not a release: it is installed UNSIGNED, unchecked"), 1),
    ("pick-placeholders-dry", '$DryRun = $true\n$script:StubWhy = "no git yet"\n$ref = Select-MethodRef ""\n'
     'Write-Host "REF=[$ref]"\n$null = Test-SettledByName $ref $SkillSignedFrom\n$null = Test-SettledByName "v*" "v0.1.45"\n',
     ("REF=[v3.*]", "would install the newest v3.* release (not readable here: no git yet)",
      "would check the signature of v3.*", "would check the signature of v*"), 0),
    # The test seat: Sort-Object swallows [version]'s throw on a `beta-` name, so the old code may pick v3.1.2 too --
    # $Error counts it. A list of candidates alone is no stable release.
    ("pick-stable", '$script:StubTags = @("v3.1.2", "beta-v3.1.3-rc1")\n$e0 = $Error.Count\n$s = Select-MethodRef \'\'\n'
     'Write-Host "STABLE=[$s] ERRORS=$($Error.Count - $e0)"\n'
     'Write-Host "BETA=[$(Select-NewestOnChannel @(\'v3.1.2\', \'beta-v3.1.3-rc1\'))]"\n',
     ("STABLE=[v3.1.2] ERRORS=0", "BETA=[beta-v3.1.3-rc1]"), 0),
    ("pick-candidates-only", '$DryRun = $true\n$script:StubTags = @("beta-v3.1.3-rc1")\n$e0 = $Error.Count\n'
     '$s = Select-MethodRef \'\'\nWrite-Host "STABLE=[$s] ERRORS=$($Error.Count - $e0)"\n',
     ("STABLE=[v3.*] ERRORS=0", "the remote lists no v3.* release"), 0))


#: #180: the stand-ins every tentative-step case runs over -- the step's own helpers that would reach the machine; the
#: profile and %APPDATA% in the case's folder.
PS1_ARM_AFTER_HEAD = ("New-Item -ItemType Directory -Force -Path $LocalBin | Out-Null\n"
                      '$env:USERPROFILE = Join-Path $env:LOCALAPPDATA "profile"\n'
                      '$env:APPDATA = Join-Path $env:LOCALAPPDATA "roaming"\n$UvVersion = "0.0.0"\n'
                      "function Step { param($m) }\nfunction Sync-ProcessPath { }\n"
                      "function Find-Bin { param($name) return $null }\n"
                      'function Add-ManifestEntry { param($n) Write-Host "MANIFEST $n ARMED=$($script:ReceiptArmed)" }\n')
#: Git's: winget and the official installer's download, signature and run, each a stand-in that may leave `git`.
PS1_ARM_AFTER_GIT = ('$HaveGit = $false\n$Scratch = Join-Path $env:LOCALAPPDATA "scratch"\n$Arch = "amd64"\n'
                     '$script:GitMarker = Join-Path $LocalBin "git-stand-in"\n$script:InstallerRc = 0\n'
                     '$script:StopInside = $false\n'
                     'function Have { param($n) if ($n -eq "winget") { return [bool]$script:Winget }; '
                     'if ($n -eq "git") { return (Test-Path $script:GitMarker) }; return $false }\n'
                     'function git { "git version 2.0 (a stand-in)" }\n'
                     # winget's chatter on its output: Run's answer is the step's, not the lines winget printed.
                     # Built from char codes: the case file is read in the ANSI code page by Windows PowerShell.
                     '$script:Bar = ([string][char]0x2588) * 12 + ([string][char]0x2592) * 8\n'
                     'function winget { Write-Output "Found Git [Git.Git] Version 2.0"; '
                     'Write-Output ("-`r\\`r|`r/"); Write-Output ("  " + $script:Bar + "  1.2 MB / 58.3 MB"); '
                     'Write-Output "  42%"; Write-Output ""; '
                     'if ($script:WingetRc -ne 0) { Write-Output "Installer failed with exit code: 1602" }; '
                     'if ($script:StopInside) { Stop-Installer 1; return }; '
                     'if ($script:Leaves) { Set-Content -Path $script:GitMarker -Value "" }; '
                     '$global:LASTEXITCODE = $script:WingetRc }\n'
                     'function Get-LatestAsset { [pscustomobject]@{ Name = "Git-2.0-64-bit.exe"; '
                     'Url = "https://example.invalid/Git-2.0-64-bit.exe" } }\n'
                     'function Invoke-WebRequest { param($Uri, $OutFile, [switch]$UseBasicParsing) '
                     'if ($script:DownloadFails) { throw "the network is down (a stand-in)" }; '
                     'Set-Content -Path $OutFile -Value "" }\n'
                     'function Unblock-File { }\n'
                     'function Get-AuthenticodeSignature { [pscustomobject]@{ Status = "Valid"; SignerCertificate = '
                     '[pscustomobject]@{ Subject = "CN=Johannes Schindelin, O=Johannes Schindelin" } } }\n'
                     'function Start-Process { Write-Host "INSTALLER RAN"; '
                     'if ($script:Leaves) { Set-Content -Path $script:GitMarker -Value "" }; '
                     '[pscustomobject]@{ ExitCode = [int]$script:InstallerRc } }\n')
#: Claude Code's and uv's Invoke-Upstream: fails, or succeeds, and leaves something or not.
PS1_UPSTREAM = ('function Invoke-Upstream {{ param([string]$Url, [string]$Label, [switch]$Capture) '
                '{leave}return ${ok} }}\n')
#: What claude.ai/install.ps1 writes before claude.exe is there, and claude.exe itself.
PS1_CLAUDE_EXE = 'Set-Content -Path (Join-Path $LocalBin "claude.exe") -Value ""; '
PS1_CLAUDE_DOWNLOADS = 'New-Item -ItemType Directory -Force -Path (Join-Path $env:USERPROFILE ".claude\\downloads") | Out-Null; '
PS1_CLAUDE_SHARE = 'New-Item -ItemType Directory -Force -Path (Join-Path $env:USERPROFILE ".local\\share\\claude") | Out-Null; '
PS1_UV_EXE = 'Set-Content -Path (Join-Path $LocalBin "uv.exe") -Value ""; '
#: A folder that was there before the call, a day old -- an earlier attempt's, or a toolchain uv already holds (#180).
PS1_AGED = ('function New-Aged {{ param($Path) New-Item -ItemType Directory -Force -Path $Path | Out-Null; '
            '(Get-Item -LiteralPath $Path).LastWriteTimeUtc = (Get-Date).ToUniversalTime().AddDays(-1) }}\n'
            'New-Aged {path}\n')
PS1_DOWNLOADS = '(Join-Path $env:USERPROFILE ".claude\\downloads")'
PS1_VERSIONS = '(Join-Path $env:USERPROFILE ".local\\share\\claude\\versions")'
PS1_TOOLCHAIN = '(Join-Path $env:APPDATA "uv\\python\\cpython-3.12.7-windows-x86_64-none")'
#: Python's: `& $Uv python install` reaches a stand-in uv; python3 is a .cmd outside ~\.local\bin, so the receipt's own
#: python3 probe does not run it.
PS1_ARM_AFTER_PY = ('$Py3 = Join-Path $env:LOCALAPPDATA "py\\python3.cmd"\n'
                    'New-Item -ItemType Directory -Force -Path (Split-Path $Py3) | Out-Null\n$Uv = "uv-stand-in"\n'
                    'function uv-stand-in {{ Write-Output "Installed Python 3.12"; {leave}'
                    '$global:LASTEXITCODE = {rc} }}\n')
PS1_PY3 = 'Set-Content -Path $Py3 -Value "@echo Python 3.12.0"; '
PS1_PY_TOOLCHAIN = ('New-Item -ItemType Directory -Force -Path (Join-Path $env:APPDATA '
                    '"uv\\python\\cpython-3.12.7-windows-x86_64-none") | Out-Null; ')
#: winget's "restart your PC to finish installation" (0x8A150109): Git is installed.
WINGET_REBOOT_TO_FINISH = -1978334967
#: (case, the blocks, its stand-ins, exit, the receipt, words it says). The receipt: "kept" -- the earlier one byte for
#: byte, disarmed; "armed" -- `stopped`, and still armed at the end when the case ends 0; "none" -- no earlier receipt,
#: none after, disarmed; "kept-armed" -- armed by an earlier step, which a failure here does not undo.
PS1_ARM_AFTER_CASES = (
    ("git-winget-fails-nothing-left", ("git",), "$script:Winget = $true\n$script:WingetRc = 1\n$script:Leaves = $false\n",
     1, "kept", ("winget ended 1 (0x00000001)", "winget: Found Git [Git.Git] Version 2.0",
                 "winget: Installer failed with exit code: 1602", "git is still not found")),
    ("git-winget-fails-git-left", ("git",), "$script:Winget = $true\n$script:WingetRc = 1\n$script:Leaves = $true\n",
     0, "armed", ("OK   git version",)),
    ("git-winget-says-0-no-git-yet", ("git",), "$script:Winget = $true\n$script:WingetRc = 0\n$script:Leaves = $false\n",
     1, "armed", ("git is still not found",)),
    ("git-winget-restart-to-finish", ("git",), f"$script:Winget = $true\n$script:WingetRc = {WINGET_REBOOT_TO_FINISH}\n"
     "$script:Leaves = $false\n", 1, "armed", ("git is still not found",)),
    ("git-winget-installs", ("git",), "$script:Winget = $true\n$script:WingetRc = 0\n$script:Leaves = $true\n",
     0, "armed", ("OK   git version",)),
    ("git-winget-already-armed-fails", ("git",), "$script:ReceiptArmed = $true\n$script:Winget = $true\n"
     f"$script:WingetRc = {WINGET_REBOOT_TO_FINISH + 2}\n$script:Leaves = $false\n", 1, "armed",
     ("winget ended -1978334965 (0x8A15010B)",)),
    ("git-stop-during-winget", ("git",), "$script:Winget = $true\n$script:WingetRc = 0\n$script:Leaves = $false\n"
     "$script:StopInside = $true\n", 1, "armed", ()),
    ("git-download-fails", ("git",), "$script:Winget = $false\n$script:DownloadFails = $true\n$script:Leaves = $false\n",
     1, "kept", ("the Git installer did not run", "git is still not found")),
    ("git-installer-ran-no-git", ("git",), "$script:Winget = $false\n$script:DownloadFails = $false\n"
     "$script:Leaves = $false\n", 1, "armed", ("INSTALLER RAN", "git is still not found")),
    ("git-installer-ends-1", ("git",), "$script:Winget = $false\n$script:DownloadFails = $false\n$script:Leaves = $true\n"
     "$script:InstallerRc = 1\n", 0, "armed", ("INSTALLER RAN", "the Git installer ended 1", "OK   git version")),
    ("git-installer-installs", ("git",), "$script:Winget = $false\n$script:DownloadFails = $false\n"
     "$script:Leaves = $true\n", 0, "armed", ("INSTALLER RAN", "OK   git version")),
    ("claude-fails-nothing-left", ("claude",), PS1_UPSTREAM.format(leave="", ok="false"), 0, "kept",
     ("Claude Code did not install",)),
    # The group seat: Git installs (its hold must be used up there), then Claude Code fails and leaves nothing -- the
    # pre-run receipt is NOT put back, Git is installed: #160's bug if it were.
    ("git-installs-then-claude-fails", ("git", "claude"), "$script:Winget = $true\n$script:WingetRc = 0\n"
     "$script:Leaves = $true\n" + PS1_UPSTREAM.format(leave="", ok="false"), 0, "armed",
     ("OK   git version", "Claude Code did not install")),
    ("claude-fails-no-earlier-receipt", ("claude",), PS1_UPSTREAM.format(leave="", ok="false"), 0, "none", ()),
    ("claude-fails-armed-before", ("claude",), "$script:ReceiptArmed = $true\n"
     + PS1_UPSTREAM.format(leave="", ok="false"), 0, "kept-armed", ()),
    ("claude-fails-binary-left", ("claude",), PS1_UPSTREAM.format(leave=PS1_CLAUDE_EXE, ok="false"), 0, "armed", ()),
    ("claude-fails-downloads-left", ("claude",), PS1_UPSTREAM.format(leave=PS1_CLAUDE_DOWNLOADS, ok="false"), 0,
     "armed", ()),
    ("claude-fails-share-left", ("claude",), PS1_UPSTREAM.format(leave=PS1_CLAUDE_SHARE, ok="false"), 0, "armed", ()),
    ("claude-fails-downloads-from-before", ("claude",), PS1_AGED.format(path=PS1_DOWNLOADS)
     + PS1_UPSTREAM.format(leave="", ok="false"), 0, "kept", ()),
    ("claude-fails-downloads-touched", ("claude",), PS1_AGED.format(path=PS1_DOWNLOADS) + PS1_UPSTREAM.format(
        leave=f'Set-Content -Path (Join-Path {PS1_DOWNLOADS} "claude.exe") -Value ""; ', ok="false"), 0, "armed", ()),
    ("claude-fails-versions-from-before", ("claude",), PS1_AGED.format(path=PS1_VERSIONS)
     + PS1_UPSTREAM.format(leave="", ok="false"), 0, "kept", ()),
    ("claude-fails-new-version", ("claude",), PS1_AGED.format(path=PS1_VERSIONS) + PS1_UPSTREAM.format(
        leave=f'New-Item -ItemType Directory -Force -Path (Join-Path {PS1_VERSIONS} "2.0.0") | Out-Null; ', ok="false"),
     0, "armed", ()),
    ("claude-installs", ("claude",), PS1_UPSTREAM.format(leave=PS1_CLAUDE_EXE, ok="true"), 0, "armed",
     ("MANIFEST claude ARMED=True",)),
    ("claude-stop-during", ("claude",), PS1_UPSTREAM.format(leave="Stop-Installer 1; ", ok="true"), 1, "armed", ()),
    # A terminating error, as Ctrl-C or a closed window is: nothing after it runs, and the receipt already says so.
    ("claude-throws-during", ("claude",), PS1_UPSTREAM.format(leave='throw "the window closed (a stand-in)"; ',
                                                               ok="true"), 1, "armed", ()),
    ("uv-fails-nothing-left", ("uv",), PS1_UPSTREAM.format(leave="", ok="false"), 0, "kept", ()),
    ("uv-fails-binary-left", ("uv",), PS1_UPSTREAM.format(leave=PS1_UV_EXE, ok="false"), 0, "armed", ()),
    ("uv-installs", ("uv",), PS1_UPSTREAM.format(leave=PS1_UV_EXE, ok="true"), 0, "armed", ("MANIFEST uv ARMED=True",)),
    ("python-fails-nothing-left", ("python",), PS1_ARM_AFTER_PY.format(leave="", rc=1), 0, "kept",
     ("python3.exe did not appear",)),
    ("python-fails-python3-left", ("python",), PS1_ARM_AFTER_PY.format(leave=PS1_PY3, rc=1), 0, "armed", ()),
    ("python-fails-toolchain-left", ("python",), PS1_ARM_AFTER_PY.format(leave=PS1_PY_TOOLCHAIN, rc=1), 0, "armed",
     ("python3.exe did not appear",)),
    # The common one: uv holds 3.12 already, ~\.local\bin\python3.exe is missing, and the link step fails.
    ("python-fails-toolchain-from-before", ("python",), PS1_AGED.format(path=PS1_TOOLCHAIN)
     + PS1_ARM_AFTER_PY.format(leave="", rc=1), 0, "kept", ("python3.exe did not appear",)),
    ("python-fails-toolchain-touched", ("python",), PS1_AGED.format(path=PS1_TOOLCHAIN) + PS1_ARM_AFTER_PY.format(
        leave=f'Set-Content -Path (Join-Path {PS1_TOOLCHAIN} "python.exe") -Value ""; ', rc=1), 0, "armed", ()),
    ("python-installs", ("python",), PS1_ARM_AFTER_PY.format(leave=PS1_PY3, rc=0), 0, "armed", ()),
    ("python-stop-during", ("python",), PS1_ARM_AFTER_PY.format(leave="Stop-Installer 1; return; ", rc=0), 1, "armed",
     ()),
    # A dry run over the four steps, as they stand -- the real Invoke-Upstream and Run: nothing written.
    ("dry-run-winget", ("git", "claude", "uv", "python"), "$DryRun = $true\n$script:Winget = $true\n"
     "$script:WingetRc = 1\n$script:Leaves = $false\n", 0, "kept-dry",
     ("would run: winget install --id Git.Git", "would run: irm https://claude.ai/install.ps1",
      "would run: irm https://astral.sh/uv/", "would run: uv python install 3.12")),
    ("dry-run-no-winget", ("git",), "$DryRun = $true\n$script:Winget = $false\n$script:Leaves = $false\n", 0, "kept-dry",
     ("would run: Git-2.0-64-bit.exe /VERYSILENT /NORESTART",)))


def ps1_arm_after_run_problems(ps1, run_case, earlier, tmp, shell_name):
    """#180, RUN (from ps1_run_problems, under PowerShell): install.ps1's Git, Claude Code, uv and Python steps, cut out
    as they stand and run over stand-ins with an earlier run's receipt there. Each arms the receipt before its call, so a
    stop or a terminating error during it leaves `stopped`; a call that failed and left nothing puts the earlier receipt
    back byte for byte (none, when there was none) and disarms -- a stop after it, as Git's, keeps it; one that ran
    (winget's 0 or its restart-to-finish code, the Git installer's run, whatever it ended) or left something (the
    binary; Claude Code's downloads or its share folder; uv's Python toolchain) stays armed: `stopped`. An earlier
    step's arm is not undone. A dry run writes nothing."""
    blocks = {"git": re.search(r'^if \(-not \$HaveGit\) \{\n    Step "Git for Windows"\n.*?^\}\n', ps1, re.M | re.S),
              "claude": re.search(r'^Step "Claude Code"\n.*?^\}\n', ps1, re.M | re.S),
              "uv": re.search(r'^Step "uv, and Python 3\.12"\n.*?^\}\n', ps1, re.M | re.S),
              "python": re.search(r'^if \(\$Uv\) \{\n    if \(Test-Path \$Py3\).*?^\}\n', ps1, re.M | re.S)}
    lacking = [k for k, m in blocks.items() if not m]
    if lacking:
        return [f"install.ps1: no {lacking} step to run under {shell_name} (#180)"]
    out = []
    never_by_case = {"git-winget-fails-nothing-left": ("1.2 MB / 58.3 MB", "42%", "winget: -", "winget: /"),
                     "git-winget-installs": ("winget:", "winget ended", "58.3 MB"),
                     "git-winget-fails-git-left": ("58.3 MB",)}
    plain = {"kept": "the earlier receipt put back byte for byte and unarmed",
             "kept-armed": "the earlier receipt untouched and still armed (an earlier step armed it)",
             "kept-dry": "the earlier receipt untouched (a dry run writes nothing)",
             "none": "no receipt after (there was none before) and unarmed",
             "armed": "the receipt `stopped`" }
    for case, keys, stand_ins, want_rc, want, words in PS1_ARM_AFTER_CASES:
        never = never_by_case.get(case, ())
        body = ("$script:ReceiptArmed = $false\n" + PS1_ARM_AFTER_HEAD + (PS1_ARM_AFTER_GIT if "git" in keys else "")
                + stand_ins + "".join(blocks[k].group(0) for k in keys)
                + 'Write-Host "ARMED=$($script:ReceiptArmed)"\nWrite-Host "END"\n')
        rc, said, receipt = run_case(f"arm-{case}", body, seed=None if want == "none" else earlier)
        there = Path(tmp, f"arm-{case}", "appdata", "autosound", "install-receipt.json")
        got = there.read_bytes() if there.is_file() else b""
        armed_at_end = re.search(r"^ARMED=(\w+)\s*$", said, re.M)
        file_ok = {"kept": got == earlier, "kept-armed": got == earlier, "kept-dry": got == earlier,
                   "none": not there.exists(),
                   "armed": isinstance(receipt, dict) and receipt.get("status") == "stopped"}[want]
        flag_ok = want_rc != 0 or want == "kept-dry" or (
            armed_at_end is not None and armed_at_end.group(1) == ("True" if want in ("armed", "kept-armed") else "False"))
        missing_words = [w for w in words if w not in said]
        said_never = [w for w in never if w in said]
        if rc != want_rc or (want_rc == 0 and "END" not in said) or missing_words or said_never or not file_ok \
                or not flag_ok:
            out.append(f"install.ps1's {' + '.join(keys)} step under {shell_name}, case {case}: want exit {want_rc} and "
                       f"{plain[want]}{' (armed at its end)' if want == 'armed' and want_rc == 0 else ''} -- got exit "
                       f"{rc}, receipt {got[:120]!r}, {armed_at_end.group(0).strip() if armed_at_end else 'no ARMED= line'}"
                       + (f"; did not say {missing_words}" if missing_words else "")
                       + (f"; said {said_never}, which it must not" if said_never else "")
                       + f" -- said {said.strip()[-300:]!r} (#180)")
    return out


def ps1_run_problems(ps1):
    """#142 (PTA 2's note, SFH 3): install.ps1's end and its two native-command probes, cut out and RUN under PowerShell
    -- where there is one: the Windows job's runner; `(problems, ran)`. Each case is a script file of its own (so
    Stop-Installer's `exit` is the process's code) in a temp folder that stands in for %LOCALAPPDATA%:
      * the end with nothing missing: exit 0, `Installed.`, the receipt `ready`;
      * the end with numpy missing: exit 3, `Installed, NOT ready: numpy`, the receipt `not ready` naming it;
      * Run and Test-Quiet over a command that is not there ($false), one that ends 0 ($true) and one that ends 3
        ($false) -- the interpreter running this check stands in for the native command;
      * Git's, Claude Code's, uv's and Python's steps over stand-ins (#180, ps1_arm_after_run_problems).
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

    def run_case(case, body, seed=None):
        home = Path(tmp, case)
        home.mkdir()
        appdata = home / "appdata"
        script = home / "case.ps1"
        if seed is not None:                            # an earlier run's receipt, there before this one (#160)
            (appdata / "autosound").mkdir(parents=True)
            (appdata / "autosound" / "install-receipt.json").write_bytes(seed)
        head = (f'$ErrorActionPreference = "Continue"\n$env:LOCALAPPDATA = "{appdata.as_posix()}"\n'
                f'$DryRun = $false\n$PluginRoot = ""\n$LocalBin = "{(home / "bin").as_posix()}"\n'
                f'$Py3 = "{(home / "bin" / "python3.exe").as_posix()}"\n$SkillHome = "{(home / "skill").as_posix()}"\n'
                f'$SkillBetaSrc = "{(home / "beta").as_posix()}"\n$SkillRef = "v3.1.2"\n$MethodLeft = ""\n'
                '$Mode = "terminal"\n$InstallerVersion = "3.1.2"\n$EngineDid = "not fetched: -NoEngine"\n'
                '$TccRefused = ""\n$AutosoundTranscriptOn = $false\n$AutosoundRunAsFile = [bool]$PSCommandPath\n'
                # The end runs after the run went ahead (#160); a case before it sets $false itself.
                '$script:Missing = @()\n$script:ReceiptArmed = $true\n')
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
        # (#160) a run that changed nothing still writes its end's verdict: the end with the receipt unarmed.
        for case, missing, want_rc, word, status in (("ready", "", 0, "Installed.", "ready"),
                                                     ("not-ready", 'Add-Missing "numpy"\n', 3,
                                                      "Installed, NOT ready: numpy", "not ready"),
                                                     ("ready-nothing-changed", "$script:ReceiptArmed = $false\n", 0,
                                                      "Installed.", "ready")):
            rc, said, receipt = run_case(case, missing + end)
            want_missing = ["numpy"] if "numpy" in missing else []
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
        for case, body, words, unsigned in PS1_PICK_CASES:
            rc, said, _ = run_case(case, PS1_PICK_HEAD + body)
            if rc != 0 or any(w not in said for w in words) or said.count("is not a release") != unsigned:
                out.append(f"install.ps1's tag pick under {Path(shell).name}, {case}: exit {rc}, want 0, "
                           f"{' + '.join(map(repr, words))} and 'is not a release' {unsigned} time(s) (said "
                           f"{said.count('is not a release')}) -- said {said.strip()[-300:]!r} (#164, #171)")
        # #164 (the test seat): Sync-MethodCheckout's two dry-run returns, which reach no signature step -- a branch
        # said not a release once and not "checked", a release "checked" and nothing UNSIGNED; a new folder, and a
        # copy that is there with no git yet (Have answers no).
        for case, ref, gitless, words, never, unsigned in (
                ("dry-new", "main", False, ("would fetch main into", "and check it out"), ("check it,",), 1),
                ("dry-no-git", "main", True, ("would fetch main into", "and check it out (no git yet)"), ("check it,",), 1),
                ("dry-release", "v3.1.2", False, ("would fetch v3.1.2 into", ", check it, and check it out"),
                 ("UNSIGNED",), 0)):
            where = Path(tmp, f"{case}-copy")
            if gitless:
                (where / ".git").mkdir(parents=True)
            body = (PS1_PICK_HEAD + "$DryRun = $true\n" + ("function Have { param($n) $false }\n" if gitless else "")
                    + f"$null = Sync-MethodCheckout '{where}' '{ref}' 'the method'\n")
            rc, said, _ = run_case(case, body)
            if rc != 0 or any(w not in said for w in words) or any(w in said for w in never) \
                    or said.count("is not a release") != unsigned:
                out.append(f"install.ps1 Sync-MethodCheckout under {Path(shell).name}, {case}: exit {rc}, want 0, "
                           f"{' + '.join(map(repr, words))}, never {' + '.join(map(repr, never))}, 'is not a release' "
                           f"{unsigned} time(s) -- said {said.strip()[-300:]!r} (#164)")
        # #167 (the test seat): Save-LocalChanges over a tag without bounded_run.py and the rest -- a repository made
        # here whose FETCH_HEAD holds only scripts/upkeep.py (KEEP_LOCAL_UPKEEP) and a changed file: `git archive`
        # takes what ls-tree found, the new upkeep.py runs with nothing beside it, and its failure is said as its own.
        repo = Path(tmp, "keep-repo")
        try:
            genv = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
                        GIT_COMMITTER_EMAIL="t@t", GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
            tool = repo / "skills" / "autosound-tuning" / "scripts" / "upkeep.py"
            tool.parent.mkdir(parents=True)
            tool.write_bytes(KEEP_LOCAL_UPKEEP)
            (repo / "a").write_text("a\n")
            for args in (("init", "-q"), ("add", "-A"), ("commit", "-q", "-m", "a"), ("fetch", "-q", ".", "HEAD")):
                subprocess.run(["git", "-C", str(repo), *args], env=genv, capture_output=True, check=True)
            (repo / "a").write_text("a\nmine\n")
            body = (f"$Py3 = '{Path(sys.executable)}'\n$LocalChanges = '{Path(tmp, 'patches')}'\n"
                    "function Offer { param($q) return $false }\n"
                    f"$kept = Save-LocalChanges '{repo}' 'the method'\nWrite-Host \"KEPT=$kept\"\n")
            rc, said, _ = run_case("keep-local-older-tag", body)
            if rc != 0 or "BESIDE []" not in said or "UPKEEP RAN" not in said or "KEPT=False" not in said \
                    or "cannot be kept automatically" in said or "see above: upkeep says what it kept and reset" not in said:
                out.append(f"install.ps1 Save-LocalChanges under {Path(shell).name}, a tag without bounded_run.py: exit "
                           f"{rc} -- want the new upkeep.py run with nothing beside it, its failure said as its own "
                           f"-- said {said.strip()[-300:]!r} (#167, #160)")
        except (OSError, subprocess.CalledProcessError) as exc:
            out.append(f"Save-LocalChanges' fixture repository could not be made ({exc}) -- unrun is not agreed (#167)")
        # #161 (the group round): install.ps1's two module-path lines, cut out as they stand. SQL Server's
        # Tools\PowerShell\Modules\ is an ordinary 5.1 entry and leaves the path as it was; pwsh's own folders are reset,
        # the Documents folder first, no empty entry; and Invoke-Upstream's child -- the lines as -Command text, started
        # from a parent whose path holds pwsh's folders -- runs a local script by a file:// URL that finds none of them
        # and runs Get-FileHash and Expand-Archive. Only under Windows PowerShell 5.1, where the reset applies.
        lines = re.findall(r"^\$Ps51(?:PwshFolders|ModulePath) = \{[^\n]*\}$", ps1, re.M)
        if len(lines) != 2:
            out.append(f"install.ps1: {len(lines)} module-path lines to run, want $Ps51PwshFolders and $Ps51ModulePath "
                       f"(#161)")
        else:
            reset = "\n".join(lines) + "\n"
            child_dir = Path(tmp, "upstream-child")
            child_dir.mkdir()
            import zipfile
            with zipfile.ZipFile(child_dir / "a.zip", "w") as zf:
                zf.writestr("a.txt", "a file to unzip\n")
            (child_dir / "child.ps1").write_bytes(
                b'$ErrorActionPreference = "Stop"\r\n'
                b'if (@(& $Ps51PwshFolders).Count -gt 0) { Write-Host "CHILD-PWSH-LEFT: $env:PSModulePath"; exit 5 }\r\n'
                b'$z = Join-Path $env:CHILD_DIR "a.zip"\r\n'
                b'$h = (Get-FileHash -Path $z -Algorithm SHA256).Hash\r\n'
                b'Expand-Archive -Path $z -DestinationPath (Join-Path $env:CHILD_DIR "out") -Force\r\n'
                b'Write-Host "CHILD-OK $h"\r\n')
            pwsh_path = ("$env:ProgramFiles + '\\PowerShell\\7\\Modules;' + $env:ProgramFiles + '\\PowerShell\\Modules;"
                         "C:\\Windows\\system32\\WindowsPowerShell\\v1.0\\Modules'")
            cases161 = (
                ("module-path-sql-server",
                 "$env:PSModulePath = 'C:\\Windows\\system32\\WindowsPowerShell\\v1.0\\Modules;C:\\Program Files (x86)\\"
                 "Microsoft SQL Server\\130\\Tools\\PowerShell\\Modules\\'\n$before = $env:PSModulePath\n" + reset
                 + ". $Ps51ModulePath\nWrite-Host \"SAME=$($env:PSModulePath -ceq $before)\"\n", ("SAME=True",)),
                ("module-path-pwsh", f"$env:PSModulePath = {pwsh_path}\n" + reset
                 + ". $Ps51ModulePath\nWrite-Host \"LEFT=$(@(& $Ps51PwshFolders).Count)\"\n"
                 "Write-Host \"EMPTY=$($env:PSModulePath -match ';;|^;|;$')\"\n"
                 # No Documents folder (a USERPROFILE set to a bare folder, as TCC's tests do): GetFolderPath says ''
                 # and the reset rightly leaves the entry out -- there is nothing to put first.
                 "$docs = [Environment]::GetFolderPath('MyDocuments')\n"
                 "Write-Host \"FIRST=$((-not $docs) -or $env:PSModulePath.StartsWith($docs + "
                 "'\\WindowsPowerShell\\Modules'))\"\n", ("LEFT=0", "EMPTY=False", "FIRST=True")),
                ("module-path-upstream-child", reset + f"$env:CHILD_DIR = '{child_dir}'\nSay 'the parent is ready'\n"
                 f"$env:PSModulePath = {pwsh_path} + ';' + $env:PSModulePath\n"
                 f"$ok = Invoke-Upstream '{(child_dir / 'child.ps1').as_uri()}' 'a local probe'\n"
                 "Write-Host \"UPSTREAM=$ok\"\n", ("CHILD-OK", "UPSTREAM=True")))
            for case, body, words in cases161:
                rc, said, _ = run_case(case, 'Write-Host "EDITION=$($PSVersionTable.PSEdition)"\n' + body)
                if "EDITION=Desktop" not in said:
                    continue                            # PowerShell 7: the reset does not apply
                if rc != 0 or any(w not in said for w in words):
                    out.append(f"install.ps1's module path under {Path(shell).name}, {case}: exit {rc}, want 0 and "
                               f"{' + '.join(map(repr, words))} -- said {said.strip()[-300:]!r} (#161)")
        # #160: a stop before the run's first change keeps the last real receipt byte for byte -- the consent declined
        # (its block cut out of install.ps1 and run with an Ask that says no), the consent given and a stop before any
        # change (the tag list, a signature), or a stop anywhere before; from Enter-Change on, it says `stopped`.
        consent = re.search(r'^if \(-not \$DryRun\) \{\n    if \(-not \(Ask "Go ahead\?" "n"\)\) \{\n.*?^\}\n', ps1,
                            re.M | re.S)
        earlier = b'{"installer":"install.ps1","status":"ready","missing":[],"at":"2026-10-01T00:00:00Z"}\r\n'
        if not consent:
            out.append('install.ps1: no consent block (`if (-not $DryRun) { if (-not (Ask "Go ahead?" "n")) {`) to run '
                       '(#160)')
        else:
            for case, body, want_rc, word, want in (
                    ("declined", "function Ask { param($q, $d) return $false }\n" + consent.group(0), 1,
                     "Nothing installed. Re-run when you want to.", "kept"),
                    ("a-stop-before-going-ahead", 'Warn "stopped: no git"\nStop-Installer 1; return\n', 1,
                     "stopped: no git", "kept"),
                    ("consented-then-a-stop", "function Ask { param($q, $d) return $true }\n" + consent.group(0)
                     + 'Warn "stopped: could not read the tags"\nStop-Installer 1; return\n', 1,
                     "stopped: could not read the tags", "kept"),
                    ("consented-then-a-change", "function Ask { param($q, $d) return $true }\n" + consent.group(0)
                     + "Enter-Change\nEnter-Change\n", 0, "", "stopped")):
                rc, said, receipt = run_case(f"receipt-{case}", "$script:ReceiptArmed = $false\n" + body, seed=earlier)
                there = Path(tmp, f"receipt-{case}", "appdata", "autosound", "install-receipt.json")
                got = there.read_bytes() if there.is_file() else b""
                kept_ok = got == earlier if want == "kept" else isinstance(receipt, dict) and receipt.get("status") == want
                if rc != want_rc or word not in said or not kept_ok:
                    out.append(f"install.ps1's receipt under {Path(shell).name}, {case}: exit {rc}, receipt "
                               f"{got[:120]!r} -- want {want_rc}, {word!r} and "
                               f"{'the earlier receipt byte for byte' if want == 'kept' else 'status ' + repr(want)} -- "
                               f"said {said.strip()[-300:]!r} (#160)")
        # #180: Windows alone, as ps1_tcc_pins_problems -- the cases stand in %APPDATA%, %USERPROFILE%, .exe and .cmd
        # files and winget; the Ubuntu job's pwsh runs the rest of this function as before.
        if os.name == "nt":
            out.extend(ps1_arm_after_run_problems(ps1, run_case, earlier, tmp, Path(shell).name))
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


#: #179 (the task review): the uv install.ps1's app block meets under PowerShell -- a native command, as uv is: a
#: `uv.cmd` that hands its arguments to this Python, which answers as STUB_UV does for install.sh (the same
#: STUB_UV_HELP: "" new, "old", "silent"), records each call in $STUB_LOG, and copies what `--constraints` names to
#: $STUB_LOG.pins while the install runs.
STUB_UV_PY = (b"import os, shutil, sys\n"
              b"a = sys.argv[1:]\n"
              b"log = os.environ.get('STUB_LOG', '')\n"
              b"help_mode = os.environ.get('STUB_UV_HELP', '')\n"
              b"if log:\n"
              b"    with open(log, 'a', encoding='utf-8') as f:\n"
              b"        f.write('uv ' + ' '.join(a) + '\\n')\n"
              b"if a[:1] == ['--version']:\n"
              b"    print('uv 0.4.30 (an old stand-in)' if help_mode == 'old' else 'uv 0.12.10 (a stand-in)')\n"
              b"    sys.exit(0)\n"
              b"if a[:2] == ['tool', 'list']:\n"
              b"    sys.exit(0)\n"
              b"if a[:2] == ['tool', 'install'] and '--help' in a:\n"
              b"    if help_mode == 'silent':\n"
              b"        print('help is elsewhere (a stand-in)', file=sys.stderr)\n"
              b"        sys.exit(0)\n"
              b"    print('Usage: uv tool install [OPTIONS] <PACKAGE>')\n"
              b"    if help_mode != 'old':\n"
              b"        print('  -c, --constraints <CONSTRAINTS>  Constrain versions using the given requirements files')\n"
              b"    print('      --build-constraints <BUILD_CONSTRAINTS>  Constrain build dependencies')\n"
              b"    sys.exit(0)\n"
              b"if a[:2] == ['tool', 'install']:\n"
              b"    if '--constraints' in a and log:\n"
              b"        held = a[a.index('--constraints') + 1]\n"
              b"        with open(log + '.pins-path', 'w', encoding='utf-8') as f:\n"
              b"            f.write(held)\n"
              b"        try:\n"
              b"            shutil.copyfile(held, log + '.pins')\n"
              b"        except OSError:\n"
              b"            pass\n"
              b"    rc = int(os.environ.get('STUB_UV_RC', '0') or 0)\n"
              b"    if rc:\n"
              b"        print('error: the build failed (a stand-in)', file=sys.stderr)\n"
              b"        sys.exit(rc)\n"
              b"    os.makedirs(os.environ['STUB_LOCAL_BIN'], exist_ok=True)\n"
              b"    open(os.path.join(os.environ['STUB_LOCAL_BIN'], 'autosound-tcc.exe'), 'wb').close()\n"
              b"sys.exit(0)\n")
#: The functions install.ps1's app block calls, cut out as they stand; the rest are stand-ins in the case's head.
PS1_APP_FUNCTIONS = ("Say", "Warn", "Step", "Add-Missing", "Pretty", "Run", "Test-ReleaseTag", "Select-NewestOnChannel")
#: What install.ps1's block says where install.sh's says another thing -- or where install.sh's words come from its
#: checks, which are not part of the block run here.
PS1_APP_WORDS = {"✓ installed": "OK   installed", "Autosound TCC was not installed": "the app did not install"}


def ps1_app_pins_problems(ps1):
    """#179 (the task review): install.ps1's app block -- `$TccExe = $null` up to the shortcuts -- RUN under
    PowerShell, where there is one (the Windows job), over APP_PIN_CASES as app_problems runs install.sh's: a stand-in
    Test-TccTag hands on what the real one would (a copy of the file, its absence, a tag fetched under the switch, or
    nothing for a tag settled by its name), and a native stand-in uv (STUB_UV_PY) takes or lacks `-c, --constraints`.
    Each case: exactly one install, given the file or not as it should be, the file's bytes read while uv ran, the
    probe asked once and only when there is a file, the copy gone after; `(problems, ran)`."""
    import tempfile
    shell = find_powershell()
    # Windows alone, as ps1_codex_link_problems (CI 38543860362): GitHub's Ubuntu image ships pwsh, and the stand-in uv
    # is a .cmd -- these cases are the installer's Windows half, not PowerShell's on any system.
    if not shell or os.name != "nt":
        return [], False
    block = re.search(r'^\$TccExe = \$null\n.*?(?=^if \(\$Mode -eq "tcc" -and \(\$TccExe -or \$DryRun\)\) \{)', ps1,
                      re.M | re.S)
    cut, lacking = [], []
    for name in PS1_APP_FUNCTIONS:
        m = (re.search(rf"^function {re.escape(name)}\s+\{{[^\n]*\}}[ \t]*$", ps1, re.M)
             or re.search(rf"^function {re.escape(name)} \{{\n.*?^\}}", ps1, re.M | re.S))
        (cut.append(m.group(0)) if m else lacking.append(name))
    if lacking or not block:
        return [f"install.ps1: no {lacking or 'app block'} to run under PowerShell (#179)"], True
    tmp = tempfile.mkdtemp(prefix="autosound_ps1_app_")
    out = []
    try:
        stub_py = Path(tmp, "stub_uv.py")
        stub_py.write_bytes(STUB_UV_PY)
        uv_cmd = Path(tmp, "uv.cmd")
        uv_cmd.write_bytes(f'@"{sys.executable}" "{stub_py}" %*\r\n@exit /b %errorlevel%\r\n'.encode("utf-8"))
        for j, (case, ref, pins, uv_help, uv_rc, _missing, want_held, words, never) in enumerate(APP_PIN_CASES):
            home = Path(tmp, f"case-{j}")
            home.mkdir()
            (home / "pins.src").write_bytes(TCC_PINS_BYTES)
            sha = "0123456789abcdef0123456789abcdef01234567" if pins in ("file", "absent") else ""
            fetched = "$false" if pins == "settled" else "$true"
            why = f"{ref} carries no {TCC_PINS_NAME}" if pins == "absent" else ""
            copy = ('$d = Join-Path $script:CaseHome "pins"; New-Item -ItemType Directory -Force -Path $d | Out-Null; '
                    '$script:TccPins = Join-Path $d "constraints.txt"; '
                    'Copy-Item -LiteralPath (Join-Path $script:CaseHome "pins.src") -Destination $script:TccPins; '
                    if pins in ("file", "fetched") else "")
            head = ('$ErrorActionPreference = "Continue"\n'
                    f"$script:CaseHome = '{home}'\n$Uv = '{uv_cmd}'\n$LocalBin = '{home / 'bin'}'\n"
                    '$DryRun = $false\n$Mode = "tcc"\n$Channel = "stable"\n'
                    f'$TccRef = "{ref}"\n$TccTagGlob = "v*"\n$TccBetaGlob = "beta-v*"\n'
                    '$TccRepo = "https://github.com/ayukhno/autosound-tcc"\n'
                    f'$TccConstraintsFrom = "{TCC_PINS_FROM}"\n$HaveTcc = $false\n$script:Missing = @()\n'
                    '$script:TagsWhy = ""\n' + "\n".join(cut) + "\n"
                    'function Sync-ProcessPath { }\n'
                    'function Read-ReleaseTags { param([string]$Repo, [string[]]$Globs) return @() }\n'
                    'function Test-TccTagStillAt { param([string]$Ref, [string]$Sha) return $true }\n'
                    'function Test-TccTag { param([string]$Ref) '
                    f'$script:TccSha = "{sha}"; $script:TccFetched = {fetched}; $script:TccPins = ""; '
                    f'$script:TccPinsWhy = "{why}"; ' + copy + 'return $true }\n')
            script = home / "case.ps1"
            script.write_bytes((head + block.group(0) + 'Write-Host "EXE=[$TccExe]"\n').encode("utf-8"))
            env = dict(powershell_env(), STUB_LOG=str(home / "calls"), STUB_UV_HELP=uv_help, STUB_UV_RC=str(uv_rc),
                       STUB_LOCAL_BIN=str(home / "bin"))
            r = subprocess.run([shell, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File",
                                str(script)], capture_output=True, timeout=120, env=env)
            said = (r.stdout + r.stderr).decode("utf-8", "replace")
            calls = (home / "calls").read_text(encoding="utf-8") if (home / "calls").exists() else ""
            wrong = [] if r.returncode == 0 and "EXE=[" in said else [f"exit {r.returncode}, no end line"]
            wrong += [f"never says {PS1_APP_WORDS.get(w, w)!r}" for w in words if PS1_APP_WORDS.get(w, w) not in said]
            wrong += [f"says {w!r}" for w in never if w in said]
            installs = [ln for ln in calls.splitlines() if ln.startswith("uv tool install ") and "--help" not in ln]
            probes = [ln for ln in calls.splitlines() if ln.startswith("uv tool install ") and "--help" in ln]
            held = [ln for ln in installs if " --constraints " in ln]
            if len(installs) != 1:
                wrong.append(f"{len(installs)} install(s), want exactly one -- never a retry: {installs!r}")
            if bool(held) != want_held:
                wrong.append(f"uv was {'not ' if want_held else ''}given --constraints: {installs!r}")
            given = home / "calls.pins"
            if want_held and (not given.is_file() or given.read_bytes() != TCC_PINS_BYTES):
                wrong.append(f"uv read {given.read_bytes()[:60] if given.is_file() else 'no file'!r} from "
                             f"--constraints, want the tag's bytes")
            if len(probes) != (1 if pins in ("file", "fetched") else 0):
                wrong.append(f"uv's --help was asked {len(probes)} time(s), want "
                             + ("once, before the install" if pins in ("file", "fetched") else "never: no file"))
            if (home / "pins").exists():
                wrong.append(f"the copy of {TCC_PINS_NAME} is left after the install")
            if wrong:
                out.append(f"install.ps1's app block under {Path(shell).name}, {case} (#179): " + "; ".join(wrong)
                           + f" -- said {said.strip()[-300:]!r}")
    except (OSError, subprocess.SubprocessError) as exc:
        out.append(f"install.ps1's app block could not be run under {shell} ({exc}) -- unrun is not agreed (#179)")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return out, True


#: #179: install.ps1's functions that Test-TccTag runs on, cut out as they stand; Test-TagSignature is a stand-in that
#: says yes (the signature is install.sh's run above, and the read checks of install.ps1's).
PS1_PINS_FUNCTIONS = ("Say", "Warn", "Test-ReleaseTag", "Test-SettledByName", "Test-TccTag")


def ps1_tcc_pins_problems(ps1):
    """#179: install.ps1's Test-TccTag RUN under PowerShell, where there is one, against tags made here -- v1.1.4 holds
    `constraints.txt`, v1.2.0 does not, v1.2.1 holds a folder by that name, v1.2.2 a symbolic link, v1.3.0 an LF-only
    file read under a person's core.autocrlf=true; `(problems, ran)`. Each fetch is the real one, into a bare
    repository under a $Scratch of the case's own, which holds a copy an earlier run left: when Test-TccTag is done the
    new copy is the one thing left there -- one folder, one file, the tag's bytes -- and nothing at all when the tag
    gave no file. The developer's switch fetches and reads the file, and verifies nothing (tcc #227); a dry run is not
    fetched and leaves nothing."""
    import tempfile
    import time
    shell = find_powershell()
    # Windows alone, as ps1_app_pins_problems: install.ps1 runs there, and $Scratch's paths are Windows'.
    if not shell or os.name != "nt":
        return [], False
    cut, lacking = [], []
    for name in PS1_PINS_FUNCTIONS:
        m = (re.search(rf"^function {re.escape(name)}\s+\{{[^\n]*\}}[ \t]*$", ps1, re.M)
             or re.search(rf"^function {re.escape(name)} \{{\n.*?^\}}", ps1, re.M | re.S))
        (cut.append(m.group(0)) if m else lacking.append(name))
    if lacking:
        return [f"install.ps1: no {lacking} to run under PowerShell (#179)"], True
    tmp = tempfile.mkdtemp(prefix="autosound_ps1_pins_")
    out = []
    try:
        repo = Path(tmp, "tcc")
        git_vars = dict(GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t",
                        GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
        genv = dict(os.environ, **git_vars)

        def git(*args):
            return subprocess.run(["git", "-C", str(repo), *args], env=genv, capture_output=True,
                                  check=True).stdout.decode("utf-8", "replace").strip()
        repo.mkdir()
        git("init", "-q")
        (repo / TCC_PINS_NAME).write_bytes(TCC_PINS_BYTES)
        for args in (("add", "-A"), ("commit", "-q", "-m", "pins"), ("tag", "-a", "v1.1.4", "-m", "t"),
                     ("rm", "-q", TCC_PINS_NAME), ("commit", "-q", "-m", "no pins"), ("tag", "-a", "v1.2.0", "-m", "t")):
            git(*args)
        (repo / TCC_PINS_NAME).mkdir()
        (repo / TCC_PINS_NAME / "x").write_bytes(b"x\n")
        for args in (("add", "-A"), ("commit", "-q", "-m", "a folder"), ("tag", "-a", "v1.2.1", "-m", "t"),
                     ("rm", "-q", "-r", TCC_PINS_NAME)):
            git(*args)
        # A symbolic link's index entry written by hand: a Windows git with core.symlinks=false would add a plain file.
        Path(tmp, "link-target").write_bytes(b"elsewhere.txt")
        blob = git("hash-object", "-w", str(Path(tmp, "link-target")))
        for args in (("update-index", "--add", "--cacheinfo", f"120000,{blob},{TCC_PINS_NAME}"),
                     ("commit", "-q", "-m", "a link"), ("tag", "-a", "v1.2.2", "-m", "t")):
            git(*args)
        # The link's index entry goes first (CI 39595279381): under core.symlinks=false -- Windows' git -- a file added
        # over a path the index holds as a link keeps mode 120000, and v1.3.0 was a link too.
        git("rm", "-q", "--cached", TCC_PINS_NAME)
        (repo / TCC_PINS_NAME).write_bytes(TCC_PINS_LF)
        for args in (("add", TCC_PINS_NAME), ("commit", "-q", "-m", "LF pins"), ("tag", "-a", "v1.3.0", "-m", "t")):
            git(*args)
        # A tag that is not what its case means is the fixture's failure, said as one -- not the installer's.
        for tag, mode in (("v1.1.4", "100644"), ("v1.2.2", "120000"), ("v1.3.0", "100644")):
            listed = git("ls-tree", tag, "--", TCC_PINS_NAME).split()
            if not listed or listed[0] != mode:
                raise OSError(f"the fixture's {tag} holds {TCC_PINS_NAME} as {listed[:1] or 'nothing'}, want mode "
                              f"{mode} (#179)")
        autocrlf = Path(tmp, "autocrlf.gitconfig")
        autocrlf.write_bytes(AUTOCRLF_CONFIG)
        # (ref, the switch, a dry run, a person's core.autocrlf=true, the copy's bytes or None, words in TccPinsWhy,
        # fetched, a commit handed on.)
        for ref, skip, dry, crlf, want_bytes, want_why, want_fetched, want_sha in (
                ("v1.1.4", "", False, False, TCC_PINS_BYTES, "", True, True),
                ("v1.2.0", "", False, False, None, "v1.2.0 carries no constraints.txt", True, True),
                ("v1.2.1", "", False, False, None, "a folder in the tag, not a file (git mode 040000)", True, True),
                ("v1.2.2", "", False, False, None, "a symbolic link in the tag, not a file (git mode 120000)", True,
                 True),
                ("v1.3.0", "", False, True, TCC_PINS_LF, "", True, True),
                ("v1.1.4", "1", False, False, TCC_PINS_BYTES, "", True, False),
                ("v1.9.9", "1", False, False, None, "could not fetch v1.9.9", True, False),
                ("v1.1.4", "", True, False, None, "", False, False)):
            case = f"{ref}{'-skip' if skip else ''}{'-dry' if dry else ''}{'-autocrlf' if crlf else ''}"
            scratch = Path(tmp, f"scratch-{case}")
            # A copy an earlier run left two days ago is swept; one another run is using now is not (the re-review:
            # nothing keeps two runs apart).
            (scratch / "tcc-pins-from-an-earlier-run").mkdir(parents=True)
            (scratch / "tcc-pins-from-an-earlier-run" / TCC_PINS_NAME).write_bytes(b"stale\n")
            aged = time.time() - 2 * 86400
            os.utime(scratch / "tcc-pins-from-an-earlier-run", (aged, aged))
            (scratch / "tcc-pins-another-run-now").mkdir()
            (scratch / "tcc-pins-another-run-now" / TCC_PINS_NAME).write_bytes(b"live\n")
            script = Path(tmp, f"{case}.ps1")
            body = ('$ErrorActionPreference = "Continue"\n'
                    f'$DryRun = ${"true" if dry else "false"}\n$TccSignedFrom = "v0.1.45"\n'
                    f"$TccRepo = '{repo.as_posix()}'\n$Scratch = '{scratch}'\n" + "\n".join(cut) + "\n"
                    'function Test-TagSignature { param([string]$Dir, [string]$Ref, [string]$SignedFrom, '
                    '[string]$Whose) Write-Host "SIGNATURE ASKED"; return $true }\n'
                    '$script:TccPins = "stale"; $script:TccPinsWhy = "stale"; $script:TccFetched = "stale"\n'
                    f'$ok = Test-TccTag "{ref}"\n'
                    'Write-Host "OK=[$ok]"\nWrite-Host "PINS=[$($script:TccPins)]"\n'
                    'Write-Host "WHY=[$($script:TccPinsWhy)]"\nWrite-Host "FETCHED=[$($script:TccFetched)]"\n'
                    'Write-Host "SHA=[$($script:TccSha)]"\n')
            script.write_bytes(body.encode("utf-8"))
            env = powershell_env()
            env.pop("AUTOSOUND_SKIP_TAG_VERIFY", None)
            if skip:
                env["AUTOSOUND_SKIP_TAG_VERIFY"] = skip
            env.update(git_vars)
            if crlf:
                env["GIT_CONFIG_GLOBAL"] = str(autocrlf)
            r = subprocess.run([shell, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File",
                                str(script)], capture_output=True, timeout=120, env=env)
            said = (r.stdout + r.stderr).decode("utf-8", "replace")
            got = dict(re.findall(r"^(OK|PINS|WHY|FETCHED|SHA)=\[(.*)\]\s*$", said, re.M))
            left = sorted(p.relative_to(scratch).as_posix() for p in scratch.rglob("*"))
            wrong = [] if r.returncode == 0 and got.get("OK") == "True" else [f"exit {r.returncode}, want OK=[True]"]
            other = ["tcc-pins-another-run-now", f"tcc-pins-another-run-now/{TCC_PINS_NAME}"]
            if any(o not in left for o in other):
                wrong.append("another run's copy, made now, was swept")
            left = [x for x in left if x not in other]
            if want_bytes is not None:
                folder = left[0] if left else ""
                copy = scratch / folder / TCC_PINS_NAME
                if left != [folder, f"{folder}/{TCC_PINS_NAME}"] or not folder.startswith("tcc-pins-") \
                        or folder == "tcc-pins-from-an-earlier-run" or not copy.is_file():
                    wrong.append(f"leaves {left} in its $Scratch, want the earlier run's copy gone and one new folder "
                                 f"holding one file {TCC_PINS_NAME}")
                elif copy.read_bytes() != want_bytes:
                    wrong.append(f"its copy holds {copy.read_bytes()[:60]!r}, want the tag's bytes {want_bytes[:60]!r}")
                if not got.get("PINS") or Path(got["PINS"]).resolve() != copy.resolve():
                    wrong.append(f"$script:TccPins is {got.get('PINS', 'not printed')!r}, want that copy")
            else:
                # A dry run fetches nothing and sweeps nothing: it changes nothing on disk.
                if left != ([] if not dry else ["tcc-pins-from-an-earlier-run",
                                                f"tcc-pins-from-an-earlier-run/{TCC_PINS_NAME}"]):
                    wrong.append(f"leaves {left} in its $Scratch, want "
                                 + ("the earlier run's copy only" if dry else "nothing"))
                if got.get("PINS") != "":
                    wrong.append(f"$script:TccPins is {got.get('PINS', 'not printed')!r}, want empty")
            why = got.get("WHY")
            if why is None or (want_why not in why if want_why else why):
                wrong.append(f"$script:TccPinsWhy is {why if why is not None else 'not printed'!r}, want "
                             + (f"one naming {want_why!r}" if want_why else "empty"))
            if got.get("FETCHED") != str(want_fetched):
                wrong.append(f"$script:TccFetched is {got.get('FETCHED', 'not printed')!r}, want {want_fetched}")
            if bool(got.get("SHA")) != want_sha or (skip and "SIGNATURE ASKED" in said):
                wrong.append(f"$script:TccSha is {got.get('SHA', 'not printed')!r}"
                             + (", the signature asked under the switch" if skip and "SIGNATURE ASKED" in said else "")
                             + f", want {'the verified commit' if want_sha else 'empty: nothing was verified'}")
            if wrong:
                out.append(f"install.ps1 Test-TccTag {case} under {Path(shell).name}, the tag's {TCC_PINS_NAME} "
                           f"(#179): " + "; ".join(wrong) + f" -- said {said.strip()[-300:]!r}")
    except (OSError, subprocess.SubprocessError) as exc:
        out.append(f"Test-TccTag's fixtures could not be made or run under {shell} ({exc}) -- unrun is not agreed "
                   f"(#179)")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return out, True


#: #180: install.ps1's steps whose call may fail with nothing changed -- (name, the step's first line, its calls in
#: order, the next step's first line). Each arms the receipt through Enter-TentativeChange before its first call, so a
#: stop during the call says `stopped`, and calls Undo-TentativeChange after its last, for a call that failed and left
#: nothing; no bare Enter-Change in it.
PS1_ARM_AFTER = (
    ("Git", 'Step "Git for Windows"', ("winget install --id Git.Git -e", "Start-Process -FilePath $tmp"), 'Step "Claude Code"'),
    ("Claude Code", 'Step "Claude Code"', ('Invoke-Upstream "https://claude.ai/install.ps1"',),
     'Step "uv, and Python 3.12"'),
    ("uv", 'Step "uv, and Python 3.12"', ('Invoke-Upstream "https://astral.sh/uv/',),
     '$Py3 = Join-Path $LocalBin "python3.exe"'),
    ("Python 3.12", '$Py3 = Join-Path $LocalBin "python3.exe"', ("& $Uv python install 3.12",),
     "# What a NEW window will run for `python3`"))


def ps1_arm_after_problems(ps1):
    """#180 (W-10's final review M3, half done in d4250f3), READ: install.ps1's Git, Claude Code, uv and Python steps arm
    the receipt through Enter-TentativeChange before their first call -- a stop, Ctrl-C or a closed window during the
    download then leaves `stopped` -- and call Undo-TentativeChange after their last, which puts the earlier receipt back
    when the call failed and left nothing: a bare Enter-Change before the call (the v3.1.3 form) wrote `stopped` over a
    good receipt, and one after it left the download unguarded. Enter-TentativeChange saves the receipt and then arms;
    Undo-TentativeChange restores it and disarms. Which outcome undoes is RUN in ps1_run_problems. A comment naming
    either is not a call."""
    out = []
    enter = re.search(r"^function Enter-TentativeChange \{\n.*?^\}$", ps1, re.M | re.S)
    undo = re.search(r"^function Undo-TentativeChange \{\n.*?^\}$", ps1, re.M | re.S)
    if not enter or "ReadAllBytes" not in enter.group(0) or not enter.group(0).rstrip("}\n ").endswith("Enter-Change") \
            or not undo or "WriteAllBytes" not in undo.group(0) or "$script:ReceiptArmed = $false" not in undo.group(0):
        out.append("install.ps1: no Enter-TentativeChange that saves the receipt's bytes and then calls Enter-Change, or "
                   "no Undo-TentativeChange that writes them back and sets `$script:ReceiptArmed = $false` (#180)")
    # Invoke-Upstream's answer is the one Undo-TentativeChange reads: as Run's (#142), a child that could not start sets
    # no exit code, and the 0 set beforehand read as an upstream installer that ran.
    upstream = re.search(r"^function Invoke-Upstream \{\n.*?^\}$", ps1, re.M | re.S)
    if not upstream or "$global:LASTEXITCODE = $null" not in upstream.group(0) \
            or "return ($null -ne $LASTEXITCODE -and $LASTEXITCODE -eq 0)" not in upstream.group(0):
        out.append("install.ps1 Invoke-Upstream: does not clear $global:LASTEXITCODE to $null and answer `$null -ne "
                   "$LASTEXITCODE -and $LASTEXITCODE -eq 0` -- a child that could not start reads as one that ran (#180)")
    # The re-review: a leftover that was there before the call is not this run's change -- Claude Code's, uv's and
    # Python's steps stamp what the call may leave before it (Get-PathStamps) and ask Test-PathsChanged after it.
    for name, call, undo_if in (("Claude Code", 'Invoke-Upstream "https://claude.ai/install.ps1"',
                                 "if (-not $claudeRan -and -not (Test-PathsChanged $claudeBefore $claudeLeaves))"),
                                ("uv", 'Invoke-Upstream "https://astral.sh/uv/',
                                 "if (-not $uvRan -and -not (Test-PathsChanged $uvBefore $uvLeaves))"),
                                ("Python 3.12", "& $Uv python install 3.12",
                                 "if (-not $pyRan -and -not (Test-PathsChanged $pyBefore $pyLeaves))")):
        at = ps1.find(call)
        var = undo_if.split("Test-PathsChanged ")[1].split()[0]
        stamp = ps1.rfind(f"{var} = Get-PathStamps ", 0, at) if at >= 0 else -1
        if at < 0 or stamp < 0 or at - stamp > 600 or not 0 < ps1.find(undo_if, at) - at < 900:
            out.append(f"install.ps1's {name} step does not stamp what its call may leave before it ({var} = "
                       f"Get-PathStamps ...) and undo only when `{undo_if}` -- a leftover from before then reads as "
                       f"this run's change (#180)")
    git_step = ps1[ps1.find('Step "Git for Windows"'):ps1.find('Step "Claude Code"')]
    winget_line = next((ln for ln in git_step.splitlines() if "winget install --id Git.Git -e" in ln), "")
    if "[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false" not in git_step \
            or not re.search(r"\} finally \{\s*\n\s*if \(\$encoding\) \{ try \{ \[Console\]::OutputEncoding = \$encoding",
                             git_step) or "Out-Host" in winget_line or "$script:WingetSaid = @(" not in winget_line \
            or "Select-ToolReason $script:WingetSaid" not in git_step \
            or """Warn ("winget ended $wingetRc ({0})" -f ('0x{0:X8}' -f $wingetRc))""" not in git_step:
        out.append("install.ps1's Git step: winget's output is not read back under UTF-8 ([Console]::OutputEncoding set "
                   "around the call and put back in a finally, the lines in $script:WingetSaid, none to Out-Host) and "
                   "said on a failure through Select-ToolReason after `winget ended <code> (0x<hex>)` -- Windows "
                   "PowerShell decodes it in the console's code page (#180)")
    if "$null -ne $p.ExitCode" not in git_step:
        out.append("install.ps1's Git step: the official installer's code is read without `$null -ne $p.ExitCode` (#180)")
    if not enter or 'Warn "the receipt (' not in enter.group(0):
        out.append("install.ps1 Enter-TentativeChange: a receipt that cannot be read is not said -- want a Warn naming "
                   "the file and that a stop now says `stopped` (#180)")
    for name, start, calls, end in PS1_ARM_AFTER:
        s = ps1.find(start)
        e = ps1.find(end, s + 1) if s >= 0 else -1
        at = [ps1.find(c, s) for c in calls] if s >= 0 else [-1]
        if s < 0 or e < 0 or any(a < 0 or a > e for a in at) or at != sorted(at):
            out.append(f"install.ps1: no {name} step ({start!r} ... {end!r}) holding {list(calls)} in that order (#180)")
            continue

        def code(word):
            return [s + m.start(1) for m in re.finditer(rf"^[^#\n]*?\b({word})\b", ps1[s:e], re.M)]
        tentative, undos, bare = code("Enter-TentativeChange"), code("Undo-TentativeChange"), code("Enter-Change")
        wrong = []
        if bare:
            wrong.append("calls a bare Enter-Change -- before the call it writes `stopped` over a good receipt when the "
                         "download fails, after it the download runs unguarded")
        if not any(x < at[0] for x in tentative):
            wrong.append(f"does not call Enter-TentativeChange before {calls[0]!r}")
        if not any(x > at[-1] for x in undos):
            wrong.append(f"does not call Undo-TentativeChange after {calls[-1]!r}, before the next step")
        if wrong:
            out.append(f"install.ps1's {name} step " + "; ".join(wrong) + " (#180)")
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
    # #160: install.sh arms the receipt (`changing`) where a step has changed something -- Apple's tools once they are
    # there, Claude Code's installer once it has run or left its binary (RUN: claude_step_problems), the method's
    # checkout (RUN: checkout_problems) -- and after the method's step; never before a step that may change nothing (the
    # final review's M3: a later stop wrote `stopped` over a good receipt). The git stops stand before the consent.
    sh_arms = [n for n, line in code if line.strip().startswith("changing")]
    clt = re.search(r'^  step "Apple\'s Command Line Tools \(git\)"\n.*?^fi\n', sh, re.M | re.S)
    clt_code = [ln.strip() for ln in (clt.group(0) if clt else "").splitlines() if not ln.lstrip().startswith("#")]
    clt_ok = ("changing" in clt_code and "done" in clt_code and "xcode-select --install >/dev/null 2>&1 || true" in clt_code
              and clt_code.index("xcode-select --install >/dev/null 2>&1 || true") < clt_code.index("done")
              < clt_code.index("changing"))
    after_method = [n for n, line in code if line.strip() == "fi   # not --plugin"]
    if not clt_ok or not after_method or after_method[0] + 2 not in sh_arms:
        out.append("install.sh does not call `changing` after Apple's tools are there (never before xcode-select, which "
                   "may change nothing) and after the method's step (#160)")
    consent_at = next((n for n, line in code if line.strip() == "consent"), None)
    git_stops = [n for n, line in code if "Install git with your package manager" in line or 'stop 1 "it said: ' in line]
    if not git_stops or consent_at is None or any(n > consent_at for n in git_stops):
        out.append("install.sh's no-git stops do not stand before `consent` -- a stop there writes no receipt only "
                   "while nothing ran (#160)")
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
    # #160: `stopped` is written from the run's first change on disk, never before -- a stop before it changed
    # nothing, and replaced the last real receipt. Enter-Change arms it, called before each step that may be the first
    # to change something and after the method's step; the flag starts $false at the top level, before the end can
    # write (a second run in the same window). RUN where PowerShell is (ps1_run_problems).
    asked = ps1.find('Ask "Go ahead?"')
    enter = re.search(r"^function Enter-Change \{\n.*?^\}$", ps1, re.M | re.S)
    unarmed = re.search(r"^\$script:ReceiptArmed = \$false\s*$", ps1, re.M)
    calls = [m.start() for m in re.finditer(r"^\s*Enter-Change\b", ps1, re.M)]
    # ...at the top level, none before the consent (a function's own call, as Set-LocalBinFirst's, runs when called).
    top_calls = [m.start() for m in re.finditer(r"^Enter-Change\b", ps1, re.M)]
    # Set-LocalBinFirst arms inside, right before its write: it changes nothing when ~\.local\bin leads already (M3).
    # Git's, Claude Code's, uv's and Python's steps arm AFTER their download, not above it (#180: ps1_arm_after_problems).
    befores = ('$key.SetValue("Path", ((@($LocalBin) + $rest) -join ";")',
               "-C $Dir checkout --quiet $want } \"git checkout", "@(& git -c advice.detachedHead=false -C $Dir checkout",
               "Step \"What the method's tools need")
    # Each change has an Enter-Change close above it (within a few lines).
    unguarded = [b for b in befores if (at := ps1.find(b)) < 0 or not any(0 < at - c < 400 for c in calls)]
    if not write_fn or 'if ($DryRun -or ($Status -eq "stopped" -and -not $script:ReceiptArmed)) { return }' \
            not in write_fn.group(0) or not enter or "if ($script:ReceiptArmed) { return }" not in enter.group(0) \
            or 'Write-Receipt "stopped"' not in enter.group(0) or not unarmed or unarmed.start() > write_fn.start() \
            or not calls or any(c < asked for c in top_calls) or unguarded \
            or re.search(r"Enter-Change\s*\n\s*if \(Set-LocalBinFirst\)", ps1):
        ps_wrong.append("`stopped` is not written from the run's first change on disk -- want Write-Receipt's guard on "
                        "`stopped` alone, Enter-Change arming once, `$script:ReceiptArmed = $false` before Write-Receipt, "
                        "and Enter-Change after the consent, before each first change"
                        + (f" (none close before: {unguarded})" if unguarded else "") + " (#160)")
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
    out.extend(ps1_arm_after_problems(ps1))

    # install.sh, RUN.
    functions, missing = cut_functions(sh, ("say", "warn", "have", "on_mac", "runs_ok", "usable", "pretty", "ask",
                                            "json_str", "write_receipt", "is_missing", "missing", "stop", "finish",
                                            "consent", "going_ahead", "changing", "unplanned_end"))
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
    go = "going_ahead\nchanging\n"
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
             # #160: a stop before going ahead changed nothing, and the last real receipt stays, byte for byte:
             # `kept`. After going ahead a stop still writes `stopped` (a-stop, a-failure).
             ("declined", "consent\n" + go + "finish\n", "python3", "0", False, 1,
              ("Nothing installed. Re-run when you want to.",), ("Installed",), "kept", [], 0, earlier),
             ("no-git", 'stop 1 "Install git with your package manager, then run this again."\n' + go + "finish\n",
              "python3", "0", False, 1, ("Install git with your package manager",), ("Installed",), "kept", [], 0,
              earlier),
             # ...and after going ahead, until the first change on disk (`changing`): a stop -- the tag list GitHub
             # did not give, a signature refused -- and a failure under set -e keep it too (the T7 review).
             ("a-stop-before-any-change", 'ASSUME_YES=1\nconsent\ngoing_ahead\nstop 1 "stopped: no tag"\n' + "finish\n",
              "python3", "0", False, 1, ("stopped: no tag",), ("Installed",), "kept", [], 0, earlier),
             ("a-failure-before-any-change", "going_ahead\nfalse\nchanging\nfinish\n", "python3", "0", False, 1,
              ("stopped (exit 1) -- the lines above say where",), ("Installed",), "kept", [], 0, earlier),
             ("the-end-with-no-change", "going_ahead\nfinish\n", "python3", "0", False, 0, ("Installed.",), (),
              "ready", [], 0, earlier),
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
             # #172: a ref with a byte that is not UTF-8, and no python3 to build the receipt -- the shell's builder
             # writes JSON all the same: the byte dropped (iconv) or a `?` (no iconv).
             ("a-bad-byte-ref-no-python3", go + "SKILL_REF=$'v\\xff'\nfinish\n", "shell", "0", False, 0,
              ("Installed.",), (), "ready", [], 0),
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
            if status == "kept":
                kept = json.dumps(before[0]).encode("utf-8") if before and isinstance(before[0], dict) else None
                there = Path(tmp, case, "data", "autosound", "install-receipt.json")
                got = there.read_bytes() if there.is_file() else None
                if kept is None or got != kept:
                    wrong.append(f"the receipt there before is not kept byte for byte -- it is "
                                 f"{(got or b'')[:160]!r} (#160)")
            elif unreadable:
                wrong.append(f"the receipt is {unreadable}")
            elif status is None and receipt is not None:
                wrong.append("a receipt was written")
            elif status is not None and receipt is None:
                wrong.append("no receipt was written")
            elif status is not None:
                left = re.search(r'METHOD_LEFT="([^"]*)"', body)
                ref = left.group(1) if left else ("v", "v?") if "SKILL_REF=$'v\\xff'" in body else "v3.1.2"
                want = {"installer": "install.sh", "installer_sha256": sha, "method_ref": ref, "mode": "terminal",
                        "engine": HOSTILE_ENGINE if builder == "python3" else flat, "installer_version": version,
                        "status": status, "missing": missing_want, "codex_link": "not reached"}
                if tuple(receipt) != RECEIPT_FIELDS:
                    wrong.append(f"the receipt's fields are {list(receipt)}, not {list(RECEIPT_FIELDS)}")
                wrong += [f"the receipt's {k} is {receipt.get(k)!r}, want {v!r}" for k, v in want.items()
                          if (receipt.get(k) not in v if isinstance(v, tuple) else receipt.get(k) != v)]
                if not receipt.get("python") or not isinstance(receipt.get("python"), str):
                    wrong.append(f"the receipt's python is {receipt.get('python')!r}, want '<path> <version>'")
            if wrong:
                out.append(f"install.sh's exit contract, {case} ({builder} builds the receipt"
                           f"{', a dry run' if dry == '1' else ''}): " + "; ".join(wrong)
                           + f" -- said {said.strip()[-240:]!r} (#142)")
        # #179 (the task review): the copy of the app's constraints.txt, live when the run ends some other way than
        # through the app's block -- a failure, a stop, a Ctrl-C during uv's long install -- goes with the run: the
        # EXIT trap removes the folder check_tcc_tag made (TCC_PINS_MADE, a TMPDIR/autosound-tcc-pins.* of its own).
        # And only that one (the re-review): a TCC_PINS and a TCC_PINS_MADE that name some other folder -- a value from
        # the environment the early globals did not clear -- leave it and its file where they are.
        live = ('TMPDIR="$HOME/tmp"\nmkdir -p "$TMPDIR/autosound-tcc-pins.abc123"\n'
                ': > "$TMPDIR/autosound-tcc-pins.abc123/constraints.txt"\n'
                'TCC_PINS_MADE="$TMPDIR/autosound-tcc-pins.abc123"\nTCC_PINS="$TCC_PINS_MADE/constraints.txt"\n')
        foreign = ('mkdir -p "$HOME/keep"\n: > "$HOME/keep/x"\nTCC_PINS="$HOME/keep/x"\nTCC_PINS_MADE="$HOME/keep"\n'
                   'TMPDIR="$HOME/tmp"\n')
        # The group seat: the prefix is right and a `/` after it climbs out -- the shape's second half refuses it.
        climbs = ('TMPDIR="$HOME/tmp"\nmkdir -p "$TMPDIR/autosound-tcc-pins.x" "$HOME/keep"\n: > "$HOME/keep/x"\n'
                  'TCC_PINS_MADE="$TMPDIR/autosound-tcc-pins.x/../../keep"\nTCC_PINS="$TCC_PINS_MADE/x"\n')
        # A signal on POSIX only: Git Bash's own `kill` of itself is not the terminal's Ctrl-C.
        for case, body, gone, kept in (
                ("the-pins-copy-and-a-failure", go + live + "false\nfinish\n", "tmp/autosound-tcc-pins.abc123", ""),
                ("the-pins-copy-and-a-stop", go + live + 'stop 1 "stopped: a stand-in"\n',
                 "tmp/autosound-tcc-pins.abc123", ""),
                *((("the-pins-copy-and-a-signal", go + live + "kill -TERM $$\nsleep 5\nfinish\n",
                    "tmp/autosound-tcc-pins.abc123", ""),) if os.name != "nt" else ()),
                ("a-foreign-pins-path-and-a-stop", go + foreign + 'stop 1 "stopped: a stand-in"\n', "", "keep/x"),
                ("a-foreign-pins-path-and-a-failure", go + foreign + "false\nfinish\n", "", "keep/x"),
                ("a-pins-path-climbing-out-and-a-stop", go + climbs + 'stop 1 "stopped: a stand-in"\n', "", "keep/x")):
            rc, said, *_ = run(case, body, "python3", "0", False)
            wrong = [] if rc != 0 else ["exit 0, want a stop"]
            if gone and Path(tmp, case, gone).exists():
                wrong.append(f"{gone} is left, want the copy gone")
            if kept and not Path(tmp, case, kept).is_file():
                wrong.append(f"{kept} is gone -- the trap removed a folder the installer did not make")
            if wrong:
                out.append(f"install.sh's exit contract, {case}: " + "; ".join(wrong) + f" (#179) -- said "
                           f"{said.strip()[-200:]!r}")
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
    shell_text = shell_text_problems(sh)
    if shell_text:
        problems.extend(shell_text)
    else:
        checked.append("install.sh pipes Claude Code's installer to bash, in the step and in both hints (read); its "
                       "json_str gives JSON over a byte that is not UTF-8 and over a UTF-8 letter, with iconv and "
                       "without (run) (#157, #172)")
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

    # 4a. No variable takes a [switch] parameter's name (see ps1_switch_name_problems).
    clashes = ps1_switch_name_problems(ps1)
    if clashes:
        problems.extend(clashes)
    else:
        checked.append("no variable in install.ps1 takes a [switch] parameter's name (a string there throws)")

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
    # #179: the first app release that carries constraints.txt -- TCC's TCC_CONSTRAINTS_FROM (1, 1, 4), whose own copy
    # is in its repository: from it on, a release that gives none is said, as TCC's updater says it (`nopins`).
    c_sh, e1 = one(r'^TCC_CONSTRAINTS_FROM="([^"]+)"', sh, "TCC_CONSTRAINTS_FROM", "install.sh")
    c_ps, e2 = one(r'^\$TccConstraintsFrom\s*=\s*"([^"]+)"', ps1, "$TccConstraintsFrom", "install.ps1")
    problems.extend(e for e in (e1, e2) if e)
    if c_sh and c_ps:
        if len({c_sh, c_ps, TCC_PINS_FROM}) != 1:
            problems.append(f"the app's first release with constraints.txt differs -- install.sh {c_sh!r}, install.ps1 "
                            f"{c_ps!r}, TCC's {TCC_PINS_FROM!r} (#179)")
        else:
            checked.append(f"the app's first release with constraints.txt agrees in both installers ({c_sh}) (#179)")
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
        checked.append("install.sh's check_tcc_tag copies a verified tag's constraints.txt out byte for byte before "
                       "its scratch repository goes, and only a file: none, a folder or a link by that name, and a tag "
                       "settled by its name leave nothing behind (run) (#179)")
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
                       f"counts the same four ways, its arm for an app from before read (#142); and over "
                       f"{len(APP_PIN_CASES)} more, a tag's constraints.txt handed to uv when it takes --constraints, "
                       f"and the plain install said for an old uv, a release without the file and a tag not fetched -- "
                       f"one install each, never a retry (#179)")
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
    manifest_enc = manifest_encoding_problems(ps1)
    if manifest_enc:
        problems.extend(manifest_enc)
    else:
        checked.append("install.ps1 reads and writes its installer-manifest one way, UTF-8 named on both sides "
                       "(read; run on the Windows job over a Cyrillic user folder) (#149)")
    kept = keep_local_problems(sh, ps1)
    if kept:
        problems.extend(kept)
    else:
        checked.append(f"both installers copy the new tag's {len(KEEP_LOCAL_FILES)} files its upkeep.py needs to keep "
                       f"local changes, rew_tool/bounded_run.py among them; install.ps1 archives those the tag has "
                       f"(read) (#167)")
    windows = windows_start_problems(ps1, cmd)
    if windows:
        problems.extend(windows)
    else:
        checked.append("install.ps1 under Windows PowerShell 5.1 resets PSModulePath to its own before its first cmdlet, "
                       "and hands the reset to the upstream installers' child PowerShell; install.cmd holds its window "
                       "open only for Explorer's exact command line (read; the Windows job runs both) (#161, #162)")
    # #149: the Codex link -- READ in both, install.sh's RUN here, install.ps1's RUN under PowerShell where there is one.
    codex = codex_read_problems(sh, ps1)
    codex_sh, codex_sh_ran = codex_link_problems(sh)
    codex_ps, codex_ps_ran = ps1_codex_link_problems(ps1)
    if codex or codex_sh or codex_ps:
        problems.extend(codex + codex_sh + codex_ps)
    else:
        checked.append(f"the Codex link (#149): both installers name --codex / -Codex in --help, make "
                       f"~/.agents/skills/autosound-tuning (a junction on Windows) and write the receipt's codex_link "
                       f"({', '.join(CODEX_VALUES)}), say it in the end's one line, own the link by the manifest's "
                       f"codex-link line and count it missing when the option asked for it (read); {len(CODEX_CASES)} "
                       f"cases -- codex on PATH or not, the option, a dry run, their own link kept or repointed with or "
                       f"without codex, somebody's link, a `..`, a real folder and a file left -- and "
                       f"{len(CODEX_UNLINK_CASES)} uninstall cases run for install.sh "
                       + ("here" if codex_sh_ran else "NOT here (Windows: Git Bash's ln -s copies)")
                       + " and for install.ps1 " + (f"under {Path(find_powershell()).name}" if codex_ps_ran
                                                    else "NOT here -- " + ("no PowerShell" if os.name == "nt" else "not Windows")
                                                    + "; the Windows job runs them"))
    # install.ps1's end and its probes RUN under PowerShell, where there is one (#142): the Windows job's runner.
    ran_ps1, ps1_ran = ps1_run_problems(ps1)
    if ran_ps1:
        problems.extend(ran_ps1)
    elif ps1_ran:
        checked.append(f"install.ps1 run under {Path(find_powershell()).name}: its end (ready, not ready, ready with "
                       f"nothing changed); Run and Test-Quiet (#142); the receipt kept before the first change and "
                       f"`stopped` after it (#160); "
                       + ("Git's, Claude Code's, uv's and Python's steps armed before their call, put back when it "
                          "failed and changed nothing, a dry run writing none (#180); " if os.name == "nt" else
                          "NOT the four steps' receipt (Windows alone, #180); ")
                       + "the tag pick, Sync-MethodCheckout's dry "
                       "runs and the UNSIGNED line "
                       "(#164, #171); the module path over SQL Server's entry and over pwsh's, and Invoke-Upstream's "
                       "child (#161)")
    else:
        checked.append("install.ps1's end, Run and Test-Quiet are NOT run here -- no PowerShell on this machine; the "
                       "Windows job runs them (#142)")
    app_ps1, app_ran = ps1_app_pins_problems(ps1)
    if app_ps1:
        problems.extend(app_ps1)
    elif app_ran:
        checked.append(f"install.ps1's app block run under {Path(find_powershell()).name} over {len(APP_PIN_CASES)} "
                       f"cases: a tag's constraints.txt handed to a uv that takes --constraints, the plain install said "
                       f"for an old uv, a silent one, a release without the file and a tag not fetched -- one install "
                       f"each, never a retry, the copy gone after (#179)")
    else:
        checked.append("install.ps1's app block is NOT run here -- "
                       + ("no PowerShell on this machine" if os.name == "nt" else "not Windows")
                       + "; the Windows job runs it (#179)")
    pins_ps1, pins_ran = ps1_tcc_pins_problems(ps1)
    if pins_ps1:
        problems.extend(pins_ps1)
    elif pins_ran:
        checked.append(f"install.ps1's Test-TccTag run under {Path(find_powershell()).name}: a tag's constraints.txt is "
                       f"copied out byte for byte before the scratch repository goes; none, a folder by that name, or a "
                       f"tag not fetched leaves nothing (#179)")
    else:
        checked.append("install.ps1's Test-TccTag is NOT run here -- "
                       + ("no PowerShell on this machine" if os.name == "nt" else "not Windows")
                       + "; the Windows job runs it (#179)")
    # The exit contract (#142): what the run ended as, in its exit code and its receipt.
    contract = exit_contract_problems(sh, ps1)
    if contract:
        problems.extend(contract)
    else:
        checked.append("the exit contract: install.sh's finish ends 0 `Installed.` or 3 `Installed, NOT ready: "
                       "<names>`, and stop ends 1, each writing a receipt that parses with its twelve fields in "
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
    # #179 (the group seat): the copy Test-TccTag makes is live from that call on -- through Test-TccTagStillAt's network
    # and uv's probes to the install -- so the `try` whose `finally` removes it opens before the call, not after them.
    app_at = ps1.find("if (-not (Test-TccTag $TccRef))")
    app_ref = ps1.rfind("if ($TccRef) {", 0, app_at) if app_at >= 0 else -1
    app_try = ps1.rfind("try {", 0, app_ref) if app_ref >= 0 else -1
    app_fin = ps1.find("if ($script:TccPins) { Remove-Item -LiteralPath (Split-Path -Parent $script:TccPins)", app_at)
    if app_at < 0 or app_ref < 0 or app_try < 0 or ps1[app_try + len("try {"):app_ref].strip() \
            or re.search(r"^\s*try \{\s*$", ps1[app_at:app_fin], re.M) or not 0 < app_fin - app_at < 9000:
        tcc_missing.append("install.ps1: the app block's try (its finally removes the constraints.txt copy) does not "
                           "open right before `if ($TccRef) {` -- a Ctrl-C between Test-TccTag and the install leaves the "
                           "copy for a day (#179)")
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

    # ...and install.ps1's header comment, the `irm … | iex` one-liner a PowerShell reader copies from its top (#163). It is
    # the same paste as the READMEs, so it holds to the same tag: the released one, or the one before it while the release
    # train has not yet moved the lines (the README rule above). A `main` there is a stale pin, as it was before this check.
    if released:
        header = re.search(r"^#\s+irm https://raw\.githubusercontent\.com/ayukhno/autosound-tuning-skill/(\S+?)/install\.ps1 \| iex",
                           ps1, re.M)
        if not header:
            problems.append("install.ps1's header comment names no `irm …/install.ps1 | iex` one-liner")
        elif header.group(1) not in {released, previous}:
            problems.append(f"install.ps1's header comment names {header.group(1)} for its one-liner, but CHANGELOG's newest "
                            f"is {released} -- the comment is a literal and moves with the release")
        else:
            checked.append(f"install.ps1's header comment names the released tag ({header.group(1)}) for its one-liner")

    # 6b. the one-liner in the installers' --help (#163): it names the release the installer belongs to, built from the
    # installer's OWN version variable, so there is no second literal to move. install.sh's help is printed by an echo
    # that expands ${INSTALLER_VERSION} (the rest of the usage text stays a quoted heredoc); install.ps1's help is a
    # double-quoted here-string, which expands $InstallerVersion. Each help body must name exactly that one ref, and
    # install.sh's help is RUN so the expanded line is what gets compared.
    help_problems = []
    usage_sh = re.search(r"^usage\(\) \{\n(.*?)^\}", sh, re.M | re.S)
    help_ps = re.search(r'if \(\$Help\) \{\s*@"\n(.*?)^"@', ps1, re.M | re.S)
    help_ref = r"autosound-tuning-skill/(\S+?)/install\.(?:sh|ps1)\b"
    if not usage_sh:
        help_problems.append("install.sh: no usage() function to read the --help text from")
    else:
        refs = re.findall(help_ref, usage_sh.group(1))
        if refs != ["v${INSTALLER_VERSION}"]:
            help_problems.append(f"install.sh's --help names {refs}, want exactly v${{INSTALLER_VERSION}}")
    if not help_ps:
        help_problems.append("install.ps1: the -Help text is no longer a double-quoted here-string, so $InstallerVersion "
                             "would not expand in it")
    else:
        refs = re.findall(help_ref, help_ps.group(1))
        if refs != ["v$InstallerVersion"]:
            help_problems.append(f"install.ps1's -Help names {refs}, want exactly v$InstallerVersion")
    sh_version, err_version = one(r'^INSTALLER_VERSION="([^"]+)"', sh, "INSTALLER_VERSION", "install.sh")
    if err_version:
        help_problems.append(err_version)
    bash, why = find_bash()
    if not bash:
        help_problems.append(f"{why} -- install.sh --help cannot be run, so the expanded line is not checked")
    elif sh_version:
        expanded = f"autosound-tuning-skill/v{sh_version}/install.sh | bash -s -- --terminal"
        try:
            r = subprocess.run([bash, SH.as_posix(), "--help"], capture_output=True, timeout=60)
        except subprocess.TimeoutExpired:
            help_problems.append("install.sh --help did not finish within 60 s, so the expanded line is not checked")
        else:
            out = r.stdout.decode("utf-8", errors="replace")
            tail = " | ".join(r.stderr.decode("utf-8", errors="replace").strip().splitlines()[-3:])
            if r.returncode != 0 or expanded not in out:
                help_problems.append(f"install.sh --help does not print {expanded!r} (exit {r.returncode}"
                                     + (f"; stderr: {tail}" if tail else "") + ")")
    if help_problems:
        problems.extend(help_problems)
    else:
        checked.append(f"both --help bodies name only the installer's own version (v{sh_version}, $InstallerVersion), "
                       "and install.sh --help prints the expanded line")

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
    elif any(not re.search(r"--constraints \S*/autosound-tcc/v[0-9.]+/constraints\.txt", line) for line in tcc_installs):
        # #179: the installers hold TCC's dependencies to the tag's own constraints.txt; the page does it by URL.
        problems.append("commands/install-tcc.md: an install line has no `--constraints …/autosound-tcc/<tag>/"
                        "constraints.txt` -- uv resolves TCC's dependencies afresh, which the installers no longer let "
                        "it do (#179)")
    elif {f"@{t}" for line in tcc_installs
          for t in re.findall(r"/autosound-tcc/(v[0-9.]+)/constraints\.txt", line)} != tcc_refs:
        # A bump that moves the app's tag and not the constraints' (or back) installs one tag under another's pins.
        problems.append(f"commands/install-tcc.md: the constraints file is not the pinned tag's -- the app at "
                        f"{sorted(tcc_refs)}, the constraints at {sorted(set(re.findall(r'/autosound-tcc/(v[0-9.]+)/', tcc_doc)))}")
    else:
        checked.append(f"commands/install-tcc.md pins the app at {next(iter(tcc_refs)).lstrip('@')}, with --python 3.12 "
                       f"and that tag's constraints on all {len(tcc_installs)} lines")

    for line in checked:
        print(f"  ok   {line}")
    # stdout first, whole: piped (the selftests runner, tag-check) it is block-buffered and stderr is not, so the FAIL
    # lines came out first and a caller's `tail` showed only `ok` lines (CI 38542204702).
    sys.stdout.flush()
    for line in problems:
        print(f"  FAIL {line}", file=sys.stderr)
    if problems:
        print(f"\ninstaller-consistency: {len(problems)} divergence(s) — the installers are a "
              f"TRIPLET, fix all three", file=sys.stderr)
        # ...and a recap, last, one short line each: a caller that shows the last dozen lines shows every FAIL.
        print("FAIL recap:", file=sys.stderr)
        for line in problems:
            print(f"  FAIL {line[:150]}{'...' if len(line) > 150 else ''}", file=sys.stderr)
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
