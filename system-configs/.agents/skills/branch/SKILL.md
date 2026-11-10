---
name: "branch"
description: "Create a clearly named feature or fix branch from the verified upstream base. Use when branch creation is requested."
metadata: {"source-repository": "damilola-elegbede-org/claude-config", "source-commit": "06fcb1349e93860a779c14c5ac47b9bf0cbe2aa4", "source-path": "system-configs/.claude/skills/branch/SKILL.md"}
---

# branch

Inspect branch state, existing names, uncommitted changes, repository instructions, and the real default branch. Derive a concise lowercase name such as feature/<subject>, fix/<subject>, or the repository’s established convention. Validate it with git check-ref-format.

Create from the current verified upstream base in an isolated checkout/worktree when the existing checkout is live or shared. Do not switch, reset, or force-update a production checkout. Preserve unrelated work; do not automatically stash another session’s changes. If a stash is necessary and authorized, include task-owned untracked files, use a unique label, record the exact stash SHA, and restore only that stash with apply. The stash stack is shared across worktrees: never assume stash@{0} is yours, and retain the entry until restoration is confirmed. A conflict leaves the operation incomplete; report the preserved stash and paths.

Use the repository-authorized Git wrapper or explicitly authorized GitHub connector for writes. Do not recover a token, impersonate another agent, or bypass a disabled identity. If the name or branch purpose is genuinely missing, ask; do not add a confirmation for an already-specified routine choice. Report the branch, base SHA, and workspace location.

Follow the host’s instructions and current authorization. Tool names, delegation, models, sandboxing, and question availability come from the running Codex session; this skill does not override them. Resolve helpers from this SKILL.md’s actual directory (SKILL_DIR in examples is a variable you set, not a Codex substitution).
