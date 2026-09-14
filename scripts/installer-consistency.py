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
    ([], ""),
)
#: What install.ps1's `Select-NewestOnChannel` must still carry. Read, not run: there is no
#: PowerShell on the author's Mac or in CI, so this half is shapes and sort key, not behaviour.
PS1_CHANNEL_SHAPES = ("'^v(\\d+)\\.(\\d+)\\.(\\d+)$'", "'^beta-v(\\d+)\\.(\\d+)\\.(\\d+)-rc(\\d+)$'",
                      "Sort-Object X, Y, Z, R, N")


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

    # 6. the TAG the world is told to paste. HUB-030 moved the one-liners off `main`, and a pinned
    # URL is only worth pinning while it is current: a stale one keeps handing new users a build
    # that is not the newest. Compared against the CHANGELOG's own top entry, which is what this
    # repo already treats as the released version -- and offline, because CI has no network.
    changelog = read(ROOT / "CHANGELOG.md")
    released = None
    m = re.search(r"^## \[(v3\.[0-9.]+)\]", changelog, re.M)
    if m:
        released = m.group(1)
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

    # And the app: `install-tcc.md` is the OTHER way into TCC, so it must pin too (SCR-054).
    tcc_doc = read(ROOT / "commands" / "install-tcc.md")
    tcc_refs = set(re.findall(r"autosound-tcc(@v[0-9.]+)?'", tcc_doc))
    if not tcc_refs:
        problems.append("commands/install-tcc.md: no `uv tool install … autosound-tcc` line found")
    elif "" in tcc_refs:
        problems.append("commands/install-tcc.md: an install line has no @tag, so uv takes the "
                        "default branch — the two ways into TCC stop giving the same app")
    elif len(tcc_refs) > 1:
        problems.append(f"commands/install-tcc.md: the lines pin different app versions — "
                        f"{sorted(tcc_refs)}")
    else:
        checked.append(f"commands/install-tcc.md pins the app at {tcc_refs.pop().lstrip('@')}")

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
