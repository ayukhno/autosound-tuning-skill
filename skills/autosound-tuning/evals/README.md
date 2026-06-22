# Trigger eval set

`trigger-eval-set.json` — 20 queries (10 should-trigger incl. the impedance/T-S/box-design
capability + recall guards for existing triggers, 10 should-NOT near-misses) for validating
the SKILL.md `description` triggering via skill-creator:

```
python -m scripts.run_loop --eval-set <this>/trigger-eval-set.json \
  --skill-path <skill-dir> --model <session-model> --max-iterations 5 --verbose
```

⚠️ Known env caveat (2026-06-22 run): the skill-creator `claude -p` eval subprocess reported
0% recall on EVERYTHING — incl. slam-dunk existing triggers (EMMA, imaging, MMM sweep) — which
is not real (the live skill triggers on those). The skill was not being registered/detected in
the `claude -p` subprocess; the improve step then hit a token limit. So the impedance/T-S/box
trigger phrases in `description` were added MANUALLY (additive — cannot reduce existing recall).
Re-run this set on a machine where the eval harness actually registers the skill to get a valid
before/after.
