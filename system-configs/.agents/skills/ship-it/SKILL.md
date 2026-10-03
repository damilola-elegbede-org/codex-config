---
name: "ship-it"
description: "Run requested documentation, test, verification, review, commit, push, and PR stages in order. Use when shipping code is requested; supports a no-write preview."
metadata: {"source-repository": "damilola-elegbede-org/claude-config", "source-commit": "cb257acb72ef568efc5d9dc2c25c365b179383b0", "source-path": "system-configs/.claude/skills/ship-it/SKILL.md"}
---

# ship-it

Parse only current flags: d=docs, t=test, v=verify, r=review, c=commit, p=push, pr=PR. No flags selects docs → test → verify → review → commit → push → PR, within the user’s scope. Reject ambiguous partial combinations before writes; do not infer a merge or deployment stage.

Dry-run reports enabled stages and required authorizations without executing them. Otherwise read the sibling SKILL.md for each selected stage and perform it directly; Codex has no Claude Skill dispatcher or commit-commands plugin dependency.

Before any commit, push, or PR stage, run current required project gates in this invocation (report-only verify if v was not selected). Tests alone do not prove lint/typecheck/build. Halt on failed or unavailable required checks. If the project genuinely defines none, disclose that nothing was checked rather than inventing a green gate.

Use authorized identity tooling, preserve hooks or execute their required equivalents for connector publishing, and stop at the first failure. If review repairs change code, repeat affected gates before publishing. Preserve skipped-review acknowledgments when authorized. Return exact commit/branch/PR evidence, which stages ran, and what remains.

Follow the host’s instructions and current authorization. Tool names, delegation, models, sandboxing, and question availability come from the running Codex session; this skill does not override them. Resolve helpers from this SKILL.md’s actual directory (SKILL_DIR in examples is a variable you set, not a Codex substitution).
