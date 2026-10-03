---
name: "verify"
description: "Run the project’s real verification gates, repair authorized failures, and re-run with a three-attempt bound. Use to verify completed work or risky changes."
metadata: {"source-repository": "damilola-elegbede-org/claude-config", "source-commit": "cb257acb72ef568efc5d9dc2c25c365b179383b0", "source-path": "system-configs/.claude/skills/verify/SKILL.md"}
---

# verify

Resolve scripts/run-checks.mjs relative to this SKILL.md’s directory, not the target repository. Use node <skill-directory>/scripts/run-checks.mjs --list to discover gates, then --json to run them. List mode executes nothing; only/skip modes scope gate IDs; report-only changes nothing.

No gates detected means nothing was checked. Unavailable tools are not passes. Report failures first with command, exit status, output, and file/line. Separate environment failures and flakiness from product defects; a flaky diagnosis can justify one unchanged rerun within the retry budget.

When repair is authorized, fix the cause without weakening tests, thresholds, or lint rules. Re-run a failing gate at most three repair attempts; stop with evidence if it remains red or the gate itself is wrong. Once individual gates pass after repairs, run all selected gates once to catch interactions. Do not broaden or repeat successful checks without a new reason. This skill may repair; test only runs and reports.

Follow the host’s instructions and current authorization. Tool names, delegation, models, sandboxing, and question availability come from the running Codex session; this skill does not override them. Resolve helpers from this SKILL.md’s actual directory (SKILL_DIR in examples is a variable you set, not a Codex substitution).
