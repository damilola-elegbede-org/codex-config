---
name: "push"
description: "Publish verified commits to the intended remote branch through authorized identity tooling. Supports a read-only preview and explicitly requested history rewrites."
metadata: {"source-repository": "damilola-elegbede-org/claude-config", "source-commit": "cb257acb72ef568efc5d9dc2c25c365b179383b0", "source-path": "system-configs/.claude/skills/push/SKILL.md"}
---

# push

Confirm the repository, remote branch, intended commits, current remote SHA, and required checks. Use the authorized wrapper or explicitly authorized connector. A dry-run inspects and reports what would change without updating a ref; do not claim hooks passed unless they ran.

Run configured pre-push checks and preserve hooks. With connector publishing, perform required checks explicitly because Git hooks do not run there. Update the branch without force by default and verify the published SHA. Do not publish unrelated changes or push directly to a protected base as a shortcut.

A history rewrite needs explicit authorization. Use a lease/expected-head guard, never an unconditional overwrite; reject if the remote moved. Do not force-update main or the live production checkout. Authentication failure is a blocker to report, not permission to switch identities or extract credentials.

Follow the host’s instructions and current authorization. Tool names, delegation, models, sandboxing, and question availability come from the running Codex session; this skill does not override them. Resolve helpers from this SKILL.md’s actual directory (SKILL_DIR in examples is a variable you set, not a Codex substitution).
