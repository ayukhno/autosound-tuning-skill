#!/usr/bin/env python3
"""Every command a document prints is RUN, and an argparse refusal is a documentation bug.

WHY. `capabilities.py` already checks that a documented flag or verb exists in the module's source.
That is a string search, and it passes for a command that can never run: the capability board
printed `resonalyze_ir.py --title "w-L_49 (sw)" --process <proj>/process` for months — every token
real — and the tool answers `error: --out and at least one --title/--id are required`. A reader who
copies a documented command and gets a usage error learns that this project's documents are
approximate, which is the expensive lesson to teach.

HOW. Each command is run with its placeholders pointed at a directory that does not exist, in a
temporary working directory. Only ARGPARSE's own refusals count as findings — "unrecognized
arguments", "the following arguments are required", "argument X: ...", or a `usage:` block with
"required" in it. Everything else is expected and ignored: no such project, REW not running,
connection refused. The command never gets to do real work, because the paths it is given are not
there.

WHAT IS SKIPPED, and why that is honest rather than convenient: anything whose verb writes
(`--write`, `apply`, `set-`, `repair`, `close`, `--fix`, `install`) is not run at all. A guard that
could damage a project to check a document is a bad trade, and those commands are the ones a
reviewer reads most carefully anyway.

  doc-commands-check.py            # fast: the parser, on fixtures (what the suite runs)
  doc-commands-check.py --run      # actually execute every documented command
  doc-commands-check.py --selftest

stdlib only.
"""
import argparse
import os
import re
import shlex
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SKILL = os.path.join(REPO, "skills", "autosound-tuning")
DOCS = [os.path.join(SKILL, "references", "core", "capabilities.md"),
        os.path.join(SKILL, "references", "tooling", "rew-tool-docs.md")]

BACKTICK = re.compile(r"`([^`]+)`")
# A command line is a `.py`/`.sh` — written with a path or by bare name — optionally prefixed by
# `python3`, and followed by at least one argument. Documents write the same tool both ways
# (`python3 rew_tool/state/process.py …` and `process.py <proj>/process show`), so the name is
# resolved against the directories modules actually live in, exactly as the capability board does.
CMD = re.compile(r"^(?:python3(?:\.\d+)?\s+)?([\w./-]+\.(?:py|sh))\b(.*)$")
MODULE_DIRS = [os.path.join(SKILL, "rew_tool"), os.path.join(SKILL, "rew_tool", "state"),
               os.path.join(SKILL, "rew_tool", "gates"), os.path.join(SKILL, "scripts"),
               os.path.join(REPO, "scripts")]


def find_module(name):
    """The module a document names, wherever it lives; None when there is no such file."""
    if os.path.isabs(name):
        return name if os.path.isfile(name) else None
    direct = os.path.join(SKILL, name)
    if os.path.isfile(direct):
        return direct
    base = os.path.basename(name)
    for d in MODULE_DIRS:
        cand = os.path.join(d, base)
        if os.path.isfile(cand):
            return cand
    return None
# Verbs that change something on disk are read, never run.
DESTRUCTIVE = ("--write", "--fix", "apply", "set-", "repair", "close", "install", "propose",
               "--refresh", "migrate", "seed")
ARGPARSE_REFUSAL = re.compile(
    r"error: (unrecognized arguments|the following arguments are required|argument )"
    r"|usage:.*\n.*required", re.I | re.S)
PLACEHOLDER = re.compile(r"<[^>]+>")


def commands(paths=DOCS):
    """[(doc, line_no, command)] — every backticked command line in the documents."""
    out = []
    for path in paths:
        if not os.path.isfile(path):
            continue
        for n, line in enumerate(open(path, encoding="utf-8").read().splitlines(), 1):
            for token in BACKTICK.findall(line):
                token = token.replace("\\|", "|").strip()
                m = CMD.match(token)
                # A bare module name is a HEADING ("* **`rew_tool/flaw_map.py`** — the flaw map"),
                # not a command. Running one and reading argparse's usage back would report every
                # module in the index as broken, which is how a guard teaches people to ignore it.
                if m and m.group(2).strip():
                    out.append((os.path.relpath(path, REPO), n, token))
    return out


# `predict.py … --fdw 6` and `state.py … log | render` are REFERENCES, not lines to copy: the
# ellipsis means "the arguments above" and the pipe enumerates alternatives. Running one literally
# reports a required argument missing, which is true of the fragment and false of the document.
PARTIAL = ("…", "...", "|")
# A bare capitalised word IS a placeholder, written without the angle brackets: `--solos DIR`,
# `--ver N`, `--title SUBSTR`. Substituting a path for `N` and letting argparse refuse "invalid int
# value: 'N'" would report the document's own shorthand as a bug.
BARE_PLACEHOLDER = re.compile(r"^[A-Z][A-Z_]*$")
# `--rew` talks to the REW instance running on this machine. A guard that reaches into the
# instrument to check a document has overstepped, even read-only — these are read, never run.
LIVE = ("--rew",)


def is_partial(cmd):
    if any(mark in cmd for mark in PARTIAL) or any(w in cmd.split() for w in LIVE):
        return True
    body = re.sub(r"\[[^\]]*\]", " ", cmd)                  # optional groups are documentation
    args = [a for a in body.split()[1:] if not a.startswith("-")]
    if any(BARE_PLACEHOLDER.match(a) for a in args):
        return True
    # prose naming a subcommand ("`process.py capture-knobs`") gives no path and no placeholder
    return not any("<" in a or "/" in a or '"' in a for a in body.split()[1:])


def is_destructive(cmd):
    low = cmd.lower()
    return any(word in low for word in DESTRUCTIVE)


def as_argv(cmd, nowhere):
    """The command as a list, with every `<placeholder>` pointed at a path that does not exist."""
    body = re.sub(r"\[[^\]]*\]", " ", re.sub(r"^python3(?:\.\d+)?\s+", "", cmd))
    try:
        parts = shlex.split(body)          # `--title "w-L_49 (sw)"` is ONE argument, not three
    except ValueError:
        parts = body.split()
    path = find_module(parts[0]) or os.path.join(SKILL, parts[0])
    argv = [sys.executable if parts[0].endswith(".py") else "bash", path]
    for part in parts[1:]:
        argv.append(PLACEHOLDER.sub(nowhere, part))
    return argv


def run_one(cmd, nowhere, sandbox, timeout=20):
    """(ok, detail) — ok is False only when ARGPARSE refused the documented form."""
    argv = as_argv(cmd, nowhere)
    if not os.path.exists(argv[1]):
        return False, f"no such module: {os.path.relpath(argv[1], SKILL)}"
    try:
        # cwd is a TEMPORARY directory, never the skill: the first full run wrote a plot and a
        # `…/` folder into `rew_tool/` — a command that got far enough to do real work. A guard
        # that leaves artefacts in the tree it checks is a guard someone will delete.
        # The modules import each other FLAT (`from analysis import …`), so running from anywhere
        # else needs their directories on the path — without it every command dies on ImportError,
        # which is not an argparse refusal and would make this guard pass everything in silence.
        env = dict(os.environ, PYTHONPATH=os.pathsep.join(MODULE_DIRS + [SKILL]))
        p = subprocess.run(argv, cwd=sandbox, env=env, capture_output=True, text=True,
                           timeout=timeout)
    except subprocess.TimeoutExpired:
        return True, "timed out (not an argparse refusal — ignored)"
    except OSError as exc:
        return True, f"could not start ({exc})"
    blob = (p.stderr or "") + (p.stdout or "")
    if ARGPARSE_REFUSAL.search(blob):
        first = next((l for l in blob.splitlines() if l.lower().startswith(("usage:", "error:"))
                      or " error: " in l.lower()), blob.strip().splitlines()[-1:] or [""])
        return False, (first if isinstance(first, str) else first[0]).strip()
    return True, ""


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run", action="store_true", help="execute the commands (default: parse only)")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    found = commands()
    if not args.run:
        print(f"{len(found)} documented command line(s) found in "
              f"{len(DOCS)} document(s); --run executes them")
        return 0
    tmp = tempfile.mkdtemp(prefix="doc_cmd_")
    nowhere = os.path.join(tmp, "no-such-project")
    sandbox = os.path.join(tmp, "cwd")
    os.makedirs(sandbox, exist_ok=True)
    bad, ran, skipped = [], 0, 0
    for doc, line, cmd in found:
        if is_destructive(cmd) or is_partial(cmd):
            skipped += 1
            continue
        ran += 1
        ok, detail = run_one(cmd, nowhere, sandbox)
        if not ok:
            bad.append(f"{doc}:{line}: `{cmd}` → {detail}")
    for b in bad:
        print(b)
    print(f"\n{ran} run, {skipped} skipped (writing, or a partial reference), "
          f"{len(bad)} refused by argparse")
    return 1 if bad else 0


def selftest():
    found = commands()
    assert found, "no commands parsed out of the documents — the regex or the paths moved"
    # the parser puts a real module path together and drops the documentation brackets
    argv = as_argv("python3 rew_tool/naming.py <project> codes [--json]", "/nowhere")
    assert argv[1].endswith("rew_tool/naming.py"), argv
    # the same tool written by bare name resolves to the same file
    assert as_argv("naming.py <project> codes", "/nowhere")[1] == argv[1]
    assert find_module("process.py").endswith("state/process.py"), find_module("process.py")
    assert find_module("no_such_module.py") is None
    assert argv[2] == "/nowhere" and argv[-1] == "codes", argv
    assert is_destructive("state/apply.py propose") and not is_destructive("naming.py codes")
    assert is_partial("predict.py … --fdw 6") and is_partial("state.py log | render")
    assert is_partial("level_offsets.py --solos DIR --ver N"), "a bare DIR/N is a placeholder"
    assert is_partial("ear_suspects.py --rew --title x"), "--rew reaches into the live instrument"
    assert is_partial("process.py capture-knobs"), "prose naming a subcommand is not a command"
    assert not is_partial("naming.py <project> codes")
    # and it recognises argparse's refusal, not a domain error
    assert ARGPARSE_REFUSAL.search("error: the following arguments are required: --out")
    assert ARGPARSE_REFUSAL.search("error: unrecognized arguments: --nope")
    assert not ARGPARSE_REFUSAL.search("error: no such project '/nowhere'")
    assert not ARGPARSE_REFUSAL.search("ConnectionRefusedError: [Errno 61]")
    print(f"selftest OK — {len(found)} documented command lines parsed; placeholders point at a "
          f"path that does not exist, writing verbs are skipped, and only argparse's own refusal "
          f"counts as a finding (a missing project or a silent REW does not)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
