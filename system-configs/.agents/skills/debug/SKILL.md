---
name: "debug"
description: "Investigate bugs, crashes, race conditions, memory leaks, or performance problems and verify a targeted fix when requested."
metadata: {"source-repository": "damilola-elegbede-org/claude-config", "source-commit": "cb257acb72ef568efc5d9dc2c25c365b179383b0", "source-path": "system-configs/.claude/skills/debug/SKILL.md"}
---

# debug

Separate investigation, repair, and verification. Reproduce the failure or document why it cannot be reproduced. Gather logs, traces, timings, and the actual execution path; test hypotheses rather than treating correlation as the root cause.

Use the debugger agent if delegation is allowed and useful; otherwise investigate directly. Return evidence and confidence separately. Apply the smallest fix within the authorized scope, then run the relevant regression check. For performance work, compare measurements under the same workload. Do not claim production recovery from a local test.

An issue-reporting request authorizes an issue with reproduction, root cause, fix, and prevention evidence through the authorized GitHub interface. Investigation by itself does not authorize publishing an issue or deploying a fix.

Follow the host’s instructions and current authorization. Tool names, delegation, models, sandboxing, and question availability come from the running Codex session; this skill does not override them. Resolve helpers from this SKILL.md’s actual directory (SKILL_DIR in examples is a variable you set, not a Codex substitution).
