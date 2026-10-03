---
name: "implement"
description: "Implement a markdown specification in dependency-ordered slices and verify its acceptance criteria. Supports preview-only and incremental modes."
metadata: {"source-repository": "damilola-elegbede-org/claude-config", "source-commit": "cb257acb72ef568efc5d9dc2c25c365b179383b0", "source-path": "system-configs/.claude/skills/implement/SKILL.md"}
---

# implement

Parse tasks, dependencies, and Acceptance/Acceptance Criteria. Incremental mode selects incomplete tasks; dry-run reports the plan without edits. Identify domains and shared files, with exactly one owner per shared file.

Implement only required behavior. For behavior changes, use small public-interface red/green slices, mocking at system boundaries; scaffolding and documentation need appropriate validation rather than mirrored tests. Refactor only when it supports the slice.

When delegation is allowed and useful, hand disjoint frontend work to frontend-engineer, tests to test-engineer, and infrastructure to devops. Backend/data work uses the built-in worker with an explicit domain brief: no backend-engineer/data-engineer is shipped in the source. Keep dependencies sequential and independent ownership explicit. Otherwise implement directly.

Run relevant project checks and verify each acceptance item before checking a task done. Failed or unavailable validation is incomplete. Return files changed, actual results, and remaining blockers. Specification implementation alone does not authorize commit, push, PR, merge, or deployment.

Follow the host’s instructions and current authorization. Tool names, delegation, models, sandboxing, and question availability come from the running Codex session; this skill does not override them. Resolve helpers from this SKILL.md’s actual directory (SKILL_DIR in examples is a variable you set, not a Codex substitution).
