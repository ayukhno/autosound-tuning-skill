#!/usr/bin/env python3
"""Valid trigger-eval for an INSTALLED/symlinked skill.

Unlike skill-creator's run_eval (which injects the candidate description as a
temp slash-command and only matches that uuid — it never matches a REAL
`Skill(<name>)` invocation, so it reports false 0% here), this runner tests the
actually-loaded skill: it runs `claude -p <query>` and detects a real
`Skill(<skill-name>)` tool_use in the stream, killing the subprocess the moment
a trigger is seen (so we don't pay for the whole skill run).

Requires the skill to be discoverable by `claude -p` (e.g. ~/.claude/skills/<name>
symlink or installed plugin). Tests the LIVE description.

Every run checks the skill list in `claude -p`'s init event: `--skill-name` must be in it (a run that cannot see the
skill measures nothing -- the old false 0%), and each `--absent` skill must not be (another skill on the same subject
competes for the same queries). A run that fails either, ends in an error result (a model that is not there), ends --
or is cut off at `--timeout` -- without a result event (the problem carries the last lines `claude -p` wrote to
stderr), or could not start is void: it is named, the rest are cancelled, no score is printed, and the runner exits
1. `--settings` and `--no-session-persistence` are handed to every `claude -p`; e.g. hide a synced skill with
`--settings '{"skillOverrides":{"rew-car-audio-tuning":"off"}}' --absent rew-car-audio-tuning` (#145).
Every `claude -p` starts in a folder that names nothing (#170): a fresh one under the system temp folder, or `--cwd`.
A folder inside a git repository, or whose path names `autosound`, `hub` or `skill`, is refused: the model reads the
path, and in a folder named for the hub it took "file an issue" for a GitHub task there. A query whose `"context"` is
`"project"` runs in a seeded tuning project instead (`--project-fixture`): the `CLAUDE.md` that
`rew_tool/project_seed.py` writes, `autosound_context.md`, `process/` and `state/`. Without the flag those queries
are not run, and the run says how many.
`--selftest` runs the mechanics against a stand-in `claude` on PATH, offline.
"""
import argparse, json, os, select, shutil, subprocess, sys, tempfile, time
from concurrent.futures import CancelledError, ProcessPoolExecutor, as_completed
from pathlib import Path

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_GUESS = str(Path(_HERE).parents[2])               # the checkout this runner lives in

#: The folder a query runs in: an empty one, or a seeded tuning project.
CONTEXTS = ("neutral", "project")
#: Words a run folder's path must not hold: the model reads the path as a hint of what the request is about.
NAMED_WORDS = ("autosound", "hub", "skill")


def cwd_problem(folder: str):
    """Why `folder` cannot be a run folder, or None: it must exist, sit outside every git repository, and its path
    must not name `autosound`, `hub` or `skill` (in any case)."""
    real = os.path.realpath(folder)
    if not os.path.isdir(real):
        return f"{folder} is not a folder"
    words = [w for w in NAMED_WORDS if w in real.lower()]
    if words:
        return f"its path names {', '.join(repr(w) for w in words)}, which the model reads as what the request is about"
    probe = real
    while True:
        if os.path.exists(os.path.join(probe, ".git")):
            return f"it is inside the git repository {probe}, which the model would read as the project"
        parent = os.path.dirname(probe)
        if parent == probe:
            return None
        probe = parent


def fresh_folder(prefix: str) -> str:
    """A new empty folder under the system temp folder that `cwd_problem` passes; its random name is drawn again if
    it happens to spell a refused word. Raises RuntimeError when the temp folder itself is refused."""
    for _ in range(5):
        folder = tempfile.mkdtemp(prefix=prefix)
        problem = cwd_problem(folder)
        if problem is None:
            return folder
        os.rmdir(folder)
    raise RuntimeError(f"no usable folder under the system temp folder {tempfile.gettempdir()}: {problem}; "
                       f"point TMPDIR elsewhere or pass --cwd")


#: The fixture's stand-ins. What loads the skill in a project is its CLAUDE.md, which is the seed's own.
_FIXTURE_FILES = {
    "autosound_context.md": "# Autosound context\n\nCar: a hatchback. DSP: an 8-channel processor. Front 3-way active, "
                            "a sub in the boot.\n\n## 5. Channel codes\n\n`sw`, `w-L/R`, `m-L/R`, `tw-L/R`\n",
    os.path.join("process", "process-state.json"): '{"phase": "time_alignment", "step": "delay pass 2"}\n',
    os.path.join("state", "dsp-state.md"): "# DSP state\n\nCrossovers set; delays: pass 1 done, pass 2 next.\n",
}


def seed_project(folder: str) -> str:
    """Make `folder` a tuning project as a person's looks on day one of a tune; returns it."""
    sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "rew_tool"))
    try:
        import project_seed
    finally:
        sys.path.pop(0)
    if not project_seed.write_claude_md(folder):
        raise RuntimeError(f"{folder} already holds a CLAUDE.md")
    for rel, text in _FIXTURE_FILES.items():
        path = os.path.join(folder, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
    return folder


def load_items(path: str) -> list:
    """The eval set, each item with its `context` ("neutral" when not given). Raises ValueError on a context that is
    neither, naming the query."""
    items = json.loads(Path(path).read_text(encoding="utf-8"))
    for it in items:
        it.setdefault("context", "neutral")
        if it["context"] not in CONTEXTS:
            raise ValueError(f"query {it['query'][:60]!r} has context {it['context']!r}: it is one of "
                             f"{', '.join(CONTEXTS)}")
    return items


def claude_argv(query: str, model: str, settings=None, no_persist=False) -> list:
    """The command line of one run."""
    cmd = ["claude", "-p", query, "--output-format", "stream-json",
           "--verbose", "--include-partial-messages", "--model", model]
    if settings is not None:
        cmd += ["--settings", settings]
    if no_persist:
        cmd.append("--no-session-persistence")
    return cmd


def _named(name: str, skill: str) -> bool:
    """`name` in an init skill list is `skill`: the skill itself, or a plugin's or a synced copy's `<prefix>:<skill>`."""
    return name == skill or name.endswith(":" + skill)


def init_check(event: dict, skill_name: str, absent=()) -> tuple:
    """(problem or None, what the list held) for one init event: `skill_name` must be in its skill list, and no skill
    of `absent`. An event without a list fails as one without the skill: what cannot be read is not passed."""
    names = []
    for entry in event.get("skills") or []:
        name = entry.get("name") if isinstance(entry, dict) else entry
        if isinstance(name, str):
            names.append(name)
    found = [n for n in names if _named(n, skill_name)]
    seen = [n for skill in absent for n in names if _named(n, skill)]
    problems = []
    if not found:
        problems.append(f"{skill_name} is not in the run's init skill list ({len(names)} skills): it cannot trigger")
    if seen:
        problems.append(f"{', '.join(seen)} is in the run's init skill list, where it was to be hidden")
    return ("; ".join(problems) or None), {"skills": len(names), "found": found, "absent_seen": seen,
                                           "model": event.get("model")}


#: How many of the last lines `claude -p` wrote to stderr a problem carries.
STDERR_LINES = 5


def run_one(query: str, skill_name: str, model: str, timeout: int, settings=None, no_persist=False,
            absent=(), cwd=None) -> dict:
    """{"triggered", "problem", "init"} for one query, its `claude -p` started in `cwd`. A problem with the init skill list ends the run at once. A run
    that ends -- or that `timeout` cuts off -- without a result event measured nothing: a problem too, carrying the
    last lines `claude -p` wrote to stderr, never a "not triggered" (#148)."""
    cmd = claude_argv(query, model, settings, no_persist)
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    err = tempfile.TemporaryFile()                       # its stderr: a file, so no pipe fills while it runs
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=err, env=env, cwd=cwd)
    buf = ""
    pending = False   # inside a Skill tool_use block
    acc = ""
    init = None       # what the init event's skill list held, once it is read
    start = time.time()

    def said() -> str:
        """`; its stderr: <its last lines>` -- what claude -p said of why it stopped -- or that it said nothing."""
        try:
            err.seek(0)
            lines = [ln.strip() for ln in err.read().decode("utf-8", "replace").splitlines() if ln.strip()]
        except OSError as exc:
            return f"; its stderr could not be read ({exc})"
        return f"; its stderr: {' | '.join(lines[-STDERR_LINES:])[-600:]}" if lines else "; it wrote nothing to stderr"

    def done(triggered: bool, problem=None) -> dict:
        if init is None and problem is None:             # what was seen without the list is not a result
            triggered, problem = False, "no init event from claude -p (it ended or timed out before one)" + said()
        return {"triggered": triggered, "problem": problem, "init": init}

    try:
        ended = False     # it has exited, and everything it wrote is in `buf`
        while time.time() - start < timeout:
            if p.poll() is not None:
                rem = p.stdout.read()                    # to the end: nothing it wrote is left in the pipe
                if rem:
                    buf += rem.decode("utf-8", "replace")
                if buf and not buf.endswith("\n"):
                    buf += "\n"                          # its last line, with no line end after it, is read too
                ended = True
            r, _, _ = select.select([p.stdout], [], [], 1.0) if not ended else ([], [], [])
            if r:
                chunk = os.read(p.stdout.fileno(), 8192)
                if chunk:
                    buf += chunk.decode("utf-8", "replace")
            while "\n" in buf:
                line, buf = buf.split("\n", 1)
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except json.JSONDecodeError:
                    continue
                t = ev.get("type")
                if t == "system" and ev.get("subtype") == "init":
                    problem, init = init_check(ev, skill_name, absent)
                    if problem:
                        return done(False, problem)
                elif t == "stream_event":
                    se = ev.get("event", {})
                    st = se.get("type", "")
                    if st == "content_block_start":
                        cb = se.get("content_block", {})
                        if cb.get("type") == "tool_use" and cb.get("name") == "Skill":
                            pending, acc = True, ""
                    elif st == "content_block_delta" and pending:
                        d = se.get("delta", {})
                        if d.get("type") == "input_json_delta":
                            acc += d.get("partial_json", "")
                            if skill_name in acc:
                                return done(True)
                    elif st in ("content_block_stop", "message_stop"):
                        pending = False
                elif t == "assistant":
                    for ci in ev.get("message", {}).get("content", []):
                        if ci.get("type") == "tool_use" and ci.get("name") == "Skill":
                            if skill_name in json.dumps(ci.get("input", {})):
                                return done(True)
                elif t == "result":
                    if ev.get("is_error"):                # no model, no access: an error, never a "not triggered"
                        return done(False, f"claude -p ended in an error: {str(ev.get('result'))[:300]}")
                    return done(False)
            if ended:                                    # read to its end, and no result in it
                if init is None:
                    return done(False)
                return done(False, f"claude -p ended (exit {p.returncode}) after its init without a result event: "
                                   f"a run cut short measured nothing" + said())
        if init is None:
            return done(False, f"no init event from claude -p within {timeout} s" + said())
        return done(False, f"claude -p gave no result within {timeout} s after its init, and was stopped: a run cut "
                           f"short measured nothing" + said())
    finally:
        if p.poll() is None:
            p.kill(); p.wait()
        err.close()


# --------------------------------------------------------------------------------------------------- selftest
_FAKE = r'''#!{python}
"""A stand-in `claude -p`: writes its argv to $FAKE_CLAUDE_ARGV, then the stream $FAKE_CLAUDE_MODE names."""
import json, os, sys
with open(os.environ["FAKE_CLAUDE_ARGV"], "a", encoding="utf-8") as fh:
    fh.write(json.dumps(sys.argv[1:]) + "\n")
if os.environ.get("FAKE_CLAUDE_CWD"):           # where it was started, and the query it was given
    with open(os.environ["FAKE_CLAUDE_CWD"], "a", encoding="utf-8") as fh:
        fh.write(json.dumps({{"cwd": os.getcwd(), "query": sys.argv[2]}}) + "\n")
mode = os.environ["FAKE_CLAUDE_MODE"]
lists = {{"ok": ["autosound-tuning", "anthropic-skills:pdf"], "plugin": ["autosound-tuning:autosound-tuning"],
         "other": ["autosound-tuning", "anthropic-skills:rew-car-audio-tuning"], "ours-missing": ["anthropic-skills:pdf"]}}
def say(ev):
    print(json.dumps(ev), flush=True)
key = mode.split("-", 1)[1] if mode.startswith(("fire-", "quiet-", "error-", "die-", "hang-", "tail-")) else mode
if mode != "no-init":
    say({{"type": "system", "subtype": "init", "skills": lists[key]}})
if mode.startswith("die-"):                     # its init, then dead: no result event
    sys.stderr.write("Error: the session ended unexpectedly\nAPI connection lost after 3 retries\n")
    sys.exit(3)
if mode.startswith("hang-"):                    # its init, then nothing until the timeout
    sys.stderr.write("waiting for the API...\n")
    sys.stderr.flush()
    import time
    time.sleep(30)
if mode.startswith("tail-"):                    # a result as the last line, with no line end after it
    sys.stdout.write(json.dumps({{"type": "result", "subtype": "success"}}))
    sys.stdout.flush()
    sys.exit(0)
if mode.startswith("fire-") or mode in ("other", "ours-missing"):
    say({{"type": "stream_event", "event": {{"type": "content_block_start",
                                         "content_block": {{"type": "tool_use", "name": "Skill"}}}}}})
    say({{"type": "stream_event", "event": {{"type": "content_block_delta",
                                         "delta": {{"type": "input_json_delta", "partial_json": "{{\"skill\": \"autosound-tuning\"}}"}}}}}})
if mode == "error-ok":
    say({{"type": "result", "subtype": "success", "is_error": True,
          "result": "API Error: 404 model: claude-sonnet-4-6 not found"}})
else:
    say({{"type": "result", "subtype": "success"}})
'''


def _selftest() -> int:
    tmp = fresh_folder("trigger_eval_")
    saved = {k: os.environ.get(k) for k in ("PATH", "FAKE_CLAUDE_ARGV", "FAKE_CLAUDE_MODE")}
    try:
        fake = os.path.join(tmp, "claude")
        with open(fake, "w", encoding="utf-8") as fh:
            fh.write(_FAKE.format(python=sys.executable))
        os.chmod(fake, 0o755)
        os.environ["PATH"] = tmp + os.pathsep + os.environ.get("PATH", "")
        argv_log = os.path.join(tmp, "argv.jsonl")
        os.environ["FAKE_CLAUDE_ARGV"] = argv_log
        hide = '{"skillOverrides":{"rew-car-audio-tuning":"off"}}'

        def one(mode: str, **kw) -> dict:
            os.environ["FAKE_CLAUDE_MODE"] = mode
            return run_one("q", "autosound-tuning", "m", 20, absent=("rew-car-audio-tuning",), **kw)

        failures = []

        def _check_trigger_read_with_the_list_seen():
            got = one("fire-ok")
            assert got["triggered"] is True and got["problem"] is None, got
            assert got["init"] == {"skills": 2, "found": ["autosound-tuning"], "absent_seen": [], "model": None}, got
            got = one("quiet-ok")
            assert got["triggered"] is False and got["problem"] is None, got
            got = one("fire-plugin")                    # a plugin's copy is the skill too
            assert got["triggered"] is True and got["init"]["found"] == ["autosound-tuning:autosound-tuning"], got

        def _check_init_list_named():
            got = one("other")                          # it would fire: the list is read first, and the run is void
            assert got["triggered"] is False and "anthropic-skills:rew-car-audio-tuning" in got["problem"], got
            got = one("ours-missing")
            assert got["triggered"] is False and "autosound-tuning is not in" in got["problem"], got
            got = one("no-init")
            assert got["triggered"] is False and "no init event" in got["problem"], got
            got = one("error-ok")                       # a model that is not there is no "not triggered"
            assert got["triggered"] is False and "404 model: claude-sonnet-4-6 not found" in got["problem"], got
            assert one("quiet-ok")["init"]["model"] is None, "the init's model is recorded as it says it"

        def _check_a_run_cut_short_is_a_problem():
            # A claude -p that prints its init and dies without a result, and one its timeout cuts off, measured
            # nothing: each is a problem, with the last lines it wrote to stderr -- they read as "not triggered", no
            # problem recorded, stderr thrown away (#148). A result with no line end after it is still read.
            got = one("die-ok")
            assert got["triggered"] is False and got["problem"] and got["init"] is not None, got
            assert "without a result" in got["problem"] and "exit 3" in got["problem"], got
            assert "the session ended unexpectedly" in got["problem"] and "lost after 3 retries" in got["problem"], got
            os.environ["FAKE_CLAUDE_MODE"] = "hang-ok"
            started = time.time()
            got = run_one("q", "autosound-tuning", "m", 2, absent=("rew-car-audio-tuning",))
            assert time.time() - started < 15, "the timeout did not stop it"
            assert got["triggered"] is False and got["problem"] and got["init"] is not None, got
            assert "no result within 2 s" in got["problem"] and "waiting for the API" in got["problem"], got
            got = one("tail-ok")
            assert got["triggered"] is False and got["problem"] is None, got

        def _check_a_run_cut_short_voids_the_run():
            sets = os.path.join(tmp, "set3.json")
            with open(sets, "w", encoding="utf-8") as fh:
                json.dump([{"query": f"q{i}", "should_trigger": False} for i in range(3)], fh)
            env = dict(os.environ, FAKE_CLAUDE_MODE="die-ok")
            done = subprocess.run([sys.executable, os.path.abspath(__file__), "--eval-set", sets, "--model", "m",
                                   "--workers", "1"], capture_output=True, text=True, encoding="utf-8", timeout=120,
                                  env=env)
            assert done.returncode == 1, (done.returncode, done.stderr[-800:])
            out = json.loads(done.stdout)
            assert out.get("void") is True and out["passed"] is None, out
            assert "no score" in done.stderr and "the session ended unexpectedly" in done.stderr, done.stderr

        def _check_arguments_reach_claude():
            open(argv_log, "w").close()
            one("quiet-ok", settings=hide, no_persist=True)
            one("quiet-ok")
            with open(argv_log, encoding="utf-8") as fh:
                runs = [json.loads(line) for line in fh]
            assert runs[0][-3:] == ["--settings", hide, "--no-session-persistence"], runs[0]
            assert "--settings" not in runs[1] and "--no-session-persistence" not in runs[1], runs[1]

        def _check_a_void_run_exits_1():
            sets = os.path.join(tmp, "set.json")
            with open(sets, "w", encoding="utf-8") as fh:
                json.dump([{"query": f"q{i}", "should_trigger": True} for i in range(3)], fh)
            base = ["--eval-set", sets, "--model", "m", "--workers", "1", "--absent", "rew-car-audio-tuning",
                    "--settings", hide, "--no-session-persistence"]
            for mode, rc_want in (("fire-ok", 0), ("other", 1)):
                os.environ["FAKE_CLAUDE_MODE"] = mode
                done = subprocess.run([sys.executable, os.path.abspath(__file__)] + base, capture_output=True,
                                      text=True, encoding="utf-8", timeout=120)
                assert done.returncode == rc_want, (mode, done.returncode, done.stderr[-800:])
                out = json.loads(done.stdout)
                assert out["claude_argv"][-3:] == ["--settings", hide, "--no-session-persistence"], out
                assert isinstance(out["duration_s"], (int, float)), out
                if rc_want:
                    assert out["init"]["problems"] and "rew-car-audio-tuning" in done.stderr, done.stderr
                    assert "void" in done.stderr, done.stderr
                else:
                    assert out["passed"] == 3 and out.get("void") is False and out["init"]["problems"] == [], out
                    assert "init skill list: autosound-tuning in all 3 runs, rew-car-audio-tuning in none" \
                        in done.stderr, done.stderr

        def _check_a_void_run_has_no_score():
            # A void run prints no score; a query it cancelled is not counted as "not triggered", and a query that
            # could not start (no claude on PATH -- an empty PATH, so the real one is never reached) voids the run.
            sets = os.path.join(tmp, "set6.json")
            with open(sets, "w", encoding="utf-8") as fh:
                json.dump([{"query": f"q{i}", "should_trigger": True} for i in range(6)], fh)
            empty = os.path.join(tmp, "empty")
            os.makedirs(empty, exist_ok=True)
            base = [sys.executable, os.path.abspath(__file__), "--eval-set", sets, "--model", "m", "--workers", "1",
                    "--absent", "rew-car-audio-tuning"]
            for mode, path, said in (("other", os.environ["PATH"], "rew-car-audio-tuning"),
                                     ("quiet-ok", empty, "could not run")):
                env = dict(os.environ, FAKE_CLAUDE_MODE=mode, PATH=path)
                done = subprocess.run(base, capture_output=True, text=True, encoding="utf-8", timeout=120, env=env)
                assert done.returncode == 1, (mode, done.returncode, done.stderr[-800:])
                out = json.loads(done.stdout)
                assert out.get("void") is True and out["passed"] is None, (mode, out)
                assert " passed in " not in done.stderr and "no score" in done.stderr, (mode, done.stderr)
                assert said in done.stderr, (mode, done.stderr)
                assert all(r["problem"] for r in out["results"]), (mode, out["results"])
                if mode == "other":
                    assert len(out["results"]) < 6, "every query ran: none was cancelled"


        def _check_it_runs_in_a_temp_folder():
            # #170: every claude -p started in the runner's own folder, whose path named the hub -- and the model
            # took "file an issue" for a GitHub task there. Now a neutral query runs in a fresh folder under the
            # system temp folder, and a project query in a seeded tuning project; neither is the repository.
            sets = os.path.join(tmp, "set-ctx.json")
            with open(sets, "w", encoding="utf-8") as fh:
                json.dump([{"query": "n0", "should_trigger": False},
                           {"query": "p0", "should_trigger": True, "context": "project"},
                           {"query": "n1", "should_trigger": False, "context": "neutral"}], fh)
            cwd_log = os.path.join(tmp, "cwd.jsonl")
            open(cwd_log, "w").close()
            env = dict(os.environ, FAKE_CLAUDE_MODE="quiet-ok", FAKE_CLAUDE_CWD=cwd_log)
            done = subprocess.run([sys.executable, os.path.abspath(__file__), "--eval-set", sets, "--model", "m",
                                   "--workers", "1", "--project-fixture", "--keep-folders"], capture_output=True,
                                  text=True, encoding="utf-8", timeout=120, env=env, cwd=_HERE)
            assert done.returncode == 0, (done.returncode, done.stderr[-800:])
            out = json.loads(done.stdout)
            with open(cwd_log, encoding="utf-8") as fh:
                seen = {r["query"]: os.path.realpath(r["cwd"]) for r in map(json.loads, fh)}
            neutral, project = os.path.realpath(out["cwd"]), os.path.realpath(out["project_cwd"])
            system_tmp = os.path.realpath(tempfile.gettempdir())
            try:
                assert seen == {"n0": neutral, "n1": neutral, "p0": project}, (seen, out["cwd"], out["project_cwd"])
                for folder in (neutral, project):
                    assert folder.startswith(system_tmp + os.sep), (folder, system_tmp)
                    assert not folder.startswith(os.path.realpath(_REPO_GUESS)), folder
                    assert cwd_problem(folder) is None, (folder, cwd_problem(folder))
                assert neutral != project and not os.listdir(neutral), (neutral, os.listdir(neutral))
                with open(os.path.join(project, "CLAUDE.md"), encoding="utf-8") as fh:
                    assert "Load the `autosound-tuning` skill" in fh.read(), "the fixture's CLAUDE.md is not the seed's"
                for name in ("autosound_context.md", "process", "state"):
                    assert os.path.exists(os.path.join(project, name)), name
                assert f"cwd: {out['cwd']}" in done.stderr and f"project cwd: {out['project_cwd']}" in done.stderr, \
                    done.stderr
                assert [r["context"] for r in out["results"]] == ["neutral", "project", "neutral"], out["results"]
            finally:
                shutil.rmtree(neutral, ignore_errors=True)
                shutil.rmtree(project, ignore_errors=True)
            # without --project-fixture a project query is not run, and the run says so; its folders are removed
            open(cwd_log, "w").close()
            done = subprocess.run([sys.executable, os.path.abspath(__file__), "--eval-set", sets, "--model", "m",
                                   "--workers", "1"], capture_output=True, text=True, encoding="utf-8", timeout=120,
                                  env=env)
            assert done.returncode == 0, (done.returncode, done.stderr[-800:])
            out = json.loads(done.stdout)
            assert out["total"] == 2 and out["passed"] == 2 and out["skipped_project"] == 1, out
            assert out["project_cwd"] is None and "--project-fixture" in done.stderr, done.stderr
            assert not os.path.exists(out["cwd"]), "the runner's own folder was left behind"
            with open(cwd_log, encoding="utf-8") as fh:
                assert sorted(json.loads(r)["query"] for r in fh) == ["n0", "n1"]

        def _check_a_named_or_repo_cwd_is_refused():
            sets = os.path.join(tmp, "set1.json")
            with open(sets, "w", encoding="utf-8") as fh:
                json.dump([{"query": "q", "should_trigger": False}], fh)
            named = os.path.join(tmp, "my-autosound-runs")
            repo = os.path.join(tmp, "plain", "inner")
            os.makedirs(named, exist_ok=True)
            os.makedirs(os.path.join(tmp, "plain", ".git"), exist_ok=True)
            os.makedirs(repo, exist_ok=True)
            env = dict(os.environ, FAKE_CLAUDE_MODE="quiet-ok")
            for folder, why in ((named, "autosound"), (repo, "git repository"), (os.path.join(tmp, "Hub"), "hub"),
                                (os.path.join(tmp, "skills-x"), "skill")):
                os.makedirs(folder, exist_ok=True)
                done = subprocess.run([sys.executable, os.path.abspath(__file__), "--eval-set", sets, "--model", "m",
                                       "--cwd", folder], capture_output=True, text=True, encoding="utf-8",
                                      timeout=60, env=env)
                assert done.returncode == 2 and not done.stdout, (folder, done.returncode, done.stdout[-300:])
                lines = done.stderr.strip().splitlines()
                assert len(lines) == 1 and why in lines[0] and "refused" in lines[0], (folder, done.stderr)
            assert cwd_problem(os.path.join(tmp, "plain")) and "git" in cwd_problem(repo)

        def _check_every_context_is_valid():
            with open(os.path.join(_HERE, "trigger-eval-set.json"), encoding="utf-8") as fh:
                items = json.load(fh)
            bad = [it["query"][:50] for it in items if it.get("context", "neutral") not in CONTEXTS]
            assert not bad, bad
            load_items(os.path.join(_HERE, "trigger-eval-set.json"))       # the loader takes the real set
            project = [it["query"] for it in items if it.get("context") == "project"]
            assert any(q.startswith("resume my car-audio tune") for q in project), project
            assert any(q.startswith("I'm in my car's tuning project folder") for q in project), project
            pairs = {}
            for it in items:
                pairs.setdefault(it["query"], set()).add(it.get("context", "neutral"))
            assert {"neutral", "project"} <= pairs.get("file an issue", set()), "a bare 'file an issue' in both"
            assert {"neutral", "project"} <= pairs.get("continue", set()), "a bare 'continue' in both"
            sets = os.path.join(tmp, "set-bad.json")
            with open(sets, "w", encoding="utf-8") as fh:
                json.dump([{"query": "q", "should_trigger": False, "context": "car"}], fh)
            try:
                load_items(sets)
            except ValueError as exc:
                assert "'car'" in str(exc) and "neutral" in str(exc), exc
            else:
                raise AssertionError("a context that is neither neutral nor project was taken")

        for check in (_check_trigger_read_with_the_list_seen, _check_init_list_named,
                      _check_a_run_cut_short_is_a_problem, _check_a_run_cut_short_voids_the_run,
                      _check_arguments_reach_claude, _check_a_void_run_exits_1, _check_a_void_run_has_no_score,
                      _check_it_runs_in_a_temp_folder, _check_a_named_or_repo_cwd_is_refused,
                      _check_every_context_is_valid):
            try:
                check()
            except (AssertionError, NameError, KeyError, ValueError, OSError) as exc:
                failures.append(f"{check.__name__}: {exc}")
        assert not failures, "\n".join(failures)
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(tmp, ignore_errors=True)
    print("selftest OK -- a trigger is read with the skill seen in the init list (a plugin's copy too); an init list "
          "holding the hidden skill, one without this skill, no init event and an error result (a model that is not "
          "there) each void the run, by name, and so do a run that dies after its init without a result and one its "
          "timeout cuts off, with the last lines claude -p wrote to stderr (a last line with no line end is still "
          "read); "
          "--settings and --no-session-persistence reach every claude -p; a void run exits 1 and prints no score, "
          "a query it cancelled is not counted, and a query that could not start voids it; every claude -p runs in "
          "a fresh folder under the system temp folder, a project query in a seeded tuning project with the seed's "
          "CLAUDE.md (not run without --project-fixture), and the runner's folders are removed after; a --cwd inside "
          "a git repository or naming autosound, hub or skill is refused in one line; every query's context is "
          "neutral or project")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval-set")
    ap.add_argument("--skill-name", default="autosound-tuning")
    ap.add_argument("--model", default="claude-sonnet-4-6")
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--settings", help="handed to every `claude -p` as --settings (a JSON string or a file)")
    ap.add_argument("--no-session-persistence", action="store_true",
                    help="handed to every `claude -p`: no run is saved to disk")
    ap.add_argument("--absent", action="append", default=[], metavar="SKILL",
                    help="a skill that must not be in any run's init skill list (repeatable)")
    ap.add_argument("--cwd", metavar="DIR",
                    help="the folder the neutral queries run in (default: a fresh one under the system temp folder); "
                         "one inside a git repository, or whose path names autosound, hub or skill, is refused")
    ap.add_argument("--project-fixture", action="store_true",
                    help='run the queries whose "context" is "project" in a seeded tuning project (a fresh folder '
                         "under the system temp folder); without it they are not run")
    ap.add_argument("--keep-folders", action="store_true",
                    help="keep the folders the runner made (they are removed after the run); --cwd is never removed")
    ap.add_argument("--selftest", action="store_true", help="the mechanics, against a stand-in claude, offline")
    a = ap.parse_args()
    if a.selftest:
        return _selftest()
    if not a.eval_set:
        ap.error("--eval-set is required")
    try:
        items = load_items(a.eval_set)
    except ValueError as exc:
        print(f"run_trigger_eval: the eval set is refused: {exc}", file=sys.stderr)
        return 2
    if a.cwd is not None:
        problem = cwd_problem(a.cwd)
        if problem:
            print(f"run_trigger_eval: --cwd {a.cwd} is refused: {problem}", file=sys.stderr)
            return 2

    made = []                                            # the folders this run made, removed at its end
    try:
        try:
            cwd = a.cwd if a.cwd is not None else fresh_folder("trigger_eval_")
            if a.cwd is None:
                made.append(cwd)
            project_cwd = None
            if a.project_fixture:
                project_cwd = fresh_folder("trigger_eval_project_")
                made.append(project_cwd)
                seed_project(project_cwd)
        except RuntimeError as exc:
            print(f"run_trigger_eval: {exc}", file=sys.stderr)
            return 2
        return _run(a, items, cwd, project_cwd)
    finally:
        if not a.keep_folders:
            for folder in made:
                shutil.rmtree(folder, ignore_errors=True)


def _run(a, items: list, cwd: str, project_cwd) -> int:
    """Score `items` -- the neutral ones in `cwd`, the project ones in `project_cwd` (not run when it is None)."""
    run_items = [(i, it) for i, it in enumerate(items) if it["context"] == "neutral" or project_cwd is not None]
    skipped = len(items) - len(run_items)
    print(f"cwd: {cwd}", file=sys.stderr)
    print(f"project cwd: {project_cwd}" if project_cwd else
          f"project cwd: none -- {skipped} project quer(ies) not run (pass --project-fixture)", file=sys.stderr)
    results, problems = {}, []                           # by the item's index: one query may stand in both contexts
    started = time.time()
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        fut = {ex.submit(run_one, it["query"], a.skill_name, a.model, a.timeout, a.settings,
                         a.no_session_persistence, tuple(a.absent),
                         project_cwd if it["context"] == "project" else cwd): (i, it) for i, it in run_items}
        for f in as_completed(fut):
            i, it = fut[f]
            try:
                got = f.result()
            except CancelledError:
                continue                                 # the run was void before this query started
            except Exception as e:                       # a query that could not run is no "not triggered"
                got = {"triggered": False, "problem": f"the query could not run: {e!r}", "init": None}
            results[i] = got
            if got["problem"] and not problems:
                for other in fut:
                    other.cancel()                       # the run is void: start no more queries
            if got["problem"]:
                problems.append(f"{it['query'][:60]!r} ({it['context']}): {got['problem']}")
    duration = round(time.time() - started, 1)

    passed = 0
    for i, it in run_items:
        if i not in results:
            continue
        got = results[i]
        ok = (got["triggered"] == it["should_trigger"])
        passed += ok
        print(f"  [{'PASS' if ok else 'FAIL'}] triggered={got['triggered']!s:5} expected={it['should_trigger']!s:5} "
              f"{it['context']:7}  {it['query'][:60]}", file=sys.stderr)
    absent = ", ".join(a.absent) or "no other skill checked"
    if problems:                                         # a void run has no score: what ran is not a sample
        print(f"\nthe run is void -- {len(problems)} quer(ies) could not be scored:", file=sys.stderr)
        for line in problems:
            print(f"  {line}", file=sys.stderr)
        print(f"no score: the run is void ({len(results)} of {len(run_items)} queries ran, {duration} s)",
              file=sys.stderr)
    else:
        print(f"\ninit skill list: {a.skill_name} in all {len(results)} runs, {absent} in none", file=sys.stderr)
        print(f"{passed}/{len(run_items)} passed in {duration} s (cwd {cwd}"
              f"{', project cwd ' + project_cwd if project_cwd else ''})", file=sys.stderr)
    print(json.dumps({"passed": None if problems else passed, "total": len(run_items), "void": bool(problems),
                      "skipped_project": skipped, "cwd": cwd, "project_cwd": project_cwd,
                      "model": a.model, "duration_s": duration,
                      "claude_argv": claude_argv("<query>", a.model, a.settings, a.no_session_persistence),
                      "init": {"skill": a.skill_name, "absent": a.absent, "problems": problems},
                      "results": [{"query": it["query"], "context": it["context"], "triggered": results[i]["triggered"],
                                   "should_trigger": it["should_trigger"], "problem": results[i]["problem"],
                                   "init": results[i]["init"]}
                                  for i, it in run_items if i in results]}, indent=2, ensure_ascii=False))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
