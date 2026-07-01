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
"""
import argparse, json, os, select, subprocess, sys, time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path


def run_one(query: str, skill_name: str, model: str, timeout: int) -> bool:
    cmd = ["claude", "-p", query, "--output-format", "stream-json",
           "--verbose", "--include-partial-messages", "--model", model]
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=env)
    buf = ""
    pending = False   # inside a Skill tool_use block
    acc = ""
    start = time.time()
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
                if t == "stream_event":
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
                                return True
                    elif st in ("content_block_stop", "message_stop"):
                        pending = False
                elif t == "assistant":
                    for ci in ev.get("message", {}).get("content", []):
                        if ci.get("type") == "tool_use" and ci.get("name") == "Skill":
                            if skill_name in json.dumps(ci.get("input", {})):
                                return True
                elif t == "result":
                    return False
            if p.poll() is not None and "\n" not in buf:
                break
        return False
    finally:
        if p.poll() is None:
            p.kill(); p.wait()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval-set", required=True)
    ap.add_argument("--skill-name", default="autosound-tuning")
    ap.add_argument("--model", default="claude-sonnet-4-6")
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()

    items = json.loads(Path(a.eval_set).read_text())
    results = {}
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        fut = {ex.submit(run_one, it["query"], a.skill_name, a.model, a.timeout): it for it in items}
        for f in as_completed(fut):
            it = fut[f]
            try:
                results[it["query"]] = (f.result(), it["should_trigger"])
            except Exception as e:
                print(f"warn: {e}", file=sys.stderr)
                results[it["query"]] = (False, it["should_trigger"])

    passed = 0
    for it in items:
        q = it["query"]
        trig, should = results[q]
        ok = (trig == should)
        passed += ok
        print(f"  [{'PASS' if ok else 'FAIL'}] triggered={trig!s:5} expected={should!s:5}  {q[:66]}", file=sys.stderr)
    print(f"\n{passed}/{len(items)} passed", file=sys.stderr)
    print(json.dumps({"passed": passed, "total": len(items),
                      "results": [{"query": q, "triggered": t, "should_trigger": s} for q, (t, s) in results.items()]}, indent=2))


if __name__ == "__main__":
    main()
