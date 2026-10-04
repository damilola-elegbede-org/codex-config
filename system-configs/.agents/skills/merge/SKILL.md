---
name: "merge"
description: "Merge a branch or authorized pull request while preserving work and resolving conflicts deliberately. Use when a merge is requested."
metadata: {"source-repository": "damilola-elegbede-org/claude-config", "source-commit": "cb257acb72ef568efc5d9dc2c25c365b179383b0", "source-path": "system-configs/.claude/skills/merge/SKILL.md"}
---

# merge

Determine whether the request concerns integrating a branch locally or merging a GitHub PR. Inspect the repository contract, current state, upstream SHA, and merge policy. Read references/workflow.md for preservation and conflict handling.

For a PR, verify the exact head, required checks, review state, unresolved threads, and authorization; use the authorized connector with expected-head protection or approved wrapper. Do not bypass protection, dismiss reviews to force completion, or infer approval from zero review data.

For local integration, work in the authorized isolated checkout. Preserve pre-existing modifications and track only stashes created by this run. Resolve conflicting content from requirements and both sides’ changes; ours/theirs choices discard content and require that intent. A failed stash restoration is incomplete and must be reported. Verify the final commit or PR merged state. Branch deletion is separate and requires scope/authorization.

Follow the host’s instructions and current authorization. Tool names, delegation, models, sandboxing, and question availability come from the running Codex session; this skill does not override them. Resolve helpers from this SKILL.md’s actual directory (SKILL_DIR in examples is a variable you set, not a Codex substitution).
