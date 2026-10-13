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
competes for the same queries). A run that fails either, ends in an error result (a model that is not there) or could
not start is void: it is named, the rest are cancelled, no score is printed, and the runner exits 1. `--settings` and
`--no-session-persistence` are handed to every `claude -p`; e.g. hide a synced skill with
`--settings '{"skillOverrides":{"rew-car-audio-tuning":"off"}}' --absent rew-car-audio-tuning` (#145).
`--selftest` runs the mechanics against a stand-in `claude` on PATH, offline.
"""
import argparse, json, os, select, subprocess, sys, time
from concurrent.futures import CancelledError, ProcessPoolExecutor, as_completed
from pathlib import Path


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


def run_one(query: str, skill_name: str, model: str, timeout: int, settings=None, no_persist=False,
            absent=()) -> dict:
    """{"triggered", "problem", "init"} for one query. A problem with the init skill list ends the run at once."""
    cmd = claude_argv(query, model, settings, no_persist)
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=env)
    buf = ""
    pending = False   # inside a Skill tool_use block
    acc = ""
    init = None       # what the init event's skill list held, once it is read
    start = time.time()

    def done(triggered: bool, problem=None) -> dict:
        if init is None and problem is None:             # what was seen without the list is not a result
            triggered, problem = False, "no init event from claude -p (it ended or timed out before one)"
        return {"triggered": triggered, "problem": problem, "init": init}

    try:
        while time.time() - start < timeout:
            if p.poll() is not None:
                rem = p.stdout.read()
                if rem:
                    buf += rem.decode("utf-8", "replace")
            r, _, _ = select.select([p.stdout], [], [], 1.0) if p.poll() is None else ([p.stdout], [], [])
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
            if p.poll() is not None and "\n" not in buf:
                break
        return done(False)
    finally:
        if p.poll() is None:
            p.kill(); p.wait()


# --------------------------------------------------------------------------------------------------- selftest
_FAKE = r'''#!{python}
"""A stand-in `claude -p`: writes its argv to $FAKE_CLAUDE_ARGV, then the stream $FAKE_CLAUDE_MODE names."""
import json, os, sys
with open(os.environ["FAKE_CLAUDE_ARGV"], "a", encoding="utf-8") as fh:
    fh.write(json.dumps(sys.argv[1:]) + "\n")
mode = os.environ["FAKE_CLAUDE_MODE"]
lists = {{"ok": ["autosound-tuning", "anthropic-skills:pdf"], "plugin": ["autosound-tuning:autosound-tuning"],
         "other": ["autosound-tuning", "anthropic-skills:rew-car-audio-tuning"], "ours-missing": ["anthropic-skills:pdf"]}}
def say(ev):
    print(json.dumps(ev), flush=True)
if mode != "no-init":
    say({{"type": "system", "subtype": "init", "skills": lists[mode.split("-", 1)[1] if mode.startswith(("fire-", "quiet-", "error-")) else mode]}})
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
    import shutil, tempfile
    tmp = tempfile.mkdtemp(prefix="trigger_eval_")
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

        for check in (_check_trigger_read_with_the_list_seen, _check_init_list_named,
                      _check_arguments_reach_claude, _check_a_void_run_exits_1, _check_a_void_run_has_no_score):
            try:
                check()
            except AssertionError as exc:
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
          "there) each void the run, by name; "
          "--settings and --no-session-persistence reach every claude -p; a void run exits 1 and prints no score, "
          "a query it cancelled is not counted, and a query that could not start voids it")
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
    ap.add_argument("--selftest", action="store_true", help="the mechanics, against a stand-in claude, offline")
    a = ap.parse_args()
    if a.selftest:
        return _selftest()
    if not a.eval_set:
        ap.error("--eval-set is required")

    items = json.loads(Path(a.eval_set).read_text(encoding="utf-8"))
    results, problems = {}, []
    started = time.time()
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        fut = {ex.submit(run_one, it["query"], a.skill_name, a.model, a.timeout, a.settings,
                         a.no_session_persistence, tuple(a.absent)): it for it in items}
        for f in as_completed(fut):
            it = fut[f]
            try:
                got = f.result()
            except CancelledError:
                continue                                 # the run was void before this query started
            except Exception as e:                       # a query that could not run is no "not triggered"
                got = {"triggered": False, "problem": f"the query could not run: {e!r}", "init": None}
            results[it["query"]] = (got, it["should_trigger"])
            if got["problem"] and not problems:
                for other in fut:
                    other.cancel()                       # the run is void: start no more queries
            if got["problem"]:
                problems.append(f"{it['query'][:60]!r}: {got['problem']}")
    duration = round(time.time() - started, 1)

    passed = 0
    for it in items:
        q = it["query"]
        if q not in results:
            continue
        got, should = results[q]
        ok = (got["triggered"] == should)
        passed += ok
        print(f"  [{'PASS' if ok else 'FAIL'}] triggered={got['triggered']!s:5} expected={should!s:5}  {q[:66]}",
              file=sys.stderr)
    absent = ", ".join(a.absent) or "no other skill checked"
    if problems:                                         # a void run has no score: what ran is not a sample
        print(f"\nthe run is void -- {len(problems)} quer(ies) could not be scored:", file=sys.stderr)
        for line in problems:
            print(f"  {line}", file=sys.stderr)
        print(f"no score: the run is void ({len(results)} of {len(items)} queries ran, {duration} s)",
              file=sys.stderr)
    else:
        print(f"\ninit skill list: {a.skill_name} in all {len(results)} runs, {absent} in none", file=sys.stderr)
        print(f"{passed}/{len(items)} passed in {duration} s", file=sys.stderr)
    print(json.dumps({"passed": None if problems else passed, "total": len(items), "void": bool(problems),
                      "model": a.model, "duration_s": duration,
                      "claude_argv": claude_argv("<query>", a.model, a.settings, a.no_session_persistence),
                      "init": {"skill": a.skill_name, "absent": a.absent, "problems": problems},
                      "results": [{"query": q, "triggered": g["triggered"], "should_trigger": s,
                                   "problem": g["problem"], "init": g["init"]}
                                  for q, (g, s) in results.items()]}, indent=2, ensure_ascii=False))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
