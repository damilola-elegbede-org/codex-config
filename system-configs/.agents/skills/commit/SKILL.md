---
name: "commit"
description: "Commit the intended changes with a clear message and the repository’s authorized identity. Use when changes are ready to commit; supports safe amend."
metadata: {"source-repository": "damilola-elegbede-org/claude-config", "source-commit": "cb257acb72ef568efc5d9dc2c25c365b179383b0", "source-path": "system-configs/.claude/skills/commit/SKILL.md"}
---

# commit

Inspect status, staged/unstaged diffs, existing commit style, and configured hooks. Include only task-owned files; exclude secrets and temporary artifacts. Stage explicit paths, never all files indiscriminately. Follow the repository’s message convention; describe behavior and rationale, and do not fabricate authorship or Claude attribution.

Use authorized identity tooling. Never bypass configured hooks. When publishing via the authorized connector instead of local Git, run equivalent required checks explicitly and disclose that local Git hooks were not invoked. Stop on a failed required check.

Amend only when requested and the commit is owned by this workflow and unpublished, unless rewriting published history is explicitly authorized. Preserve other changes and verify the resulting commit/tree and branch. Nothing to commit is an expected outcome, not a failure.

Follow the host’s instructions and current authorization. Tool names, delegation, models, sandboxing, and question availability come from the running Codex session; this skill does not override them. Resolve helpers from this SKILL.md’s actual directory (SKILL_DIR in examples is a variable you set, not a Codex substitution).
