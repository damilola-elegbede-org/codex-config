---
name: "rebase"
description: "Update an owned feature branch onto its verified upstream base with conflict and stash preservation. Use when rebase, continue, or abort is requested."
metadata: {"source-repository": "damilola-elegbede-org/claude-config", "source-commit": "cb257acb72ef568efc5d9dc2c25c365b179383b0", "source-path": "system-configs/.claude/skills/rebase/SKILL.md"}
---

# rebase

Read references/workflow.md. Verify the target and current branch first. Never rebase the base branch onto itself or rewrite shared/published history without authorization. Use an isolated workspace when the checkout is live/shared.

Fetch/inspect the actual upstream and rebase only the intended branch. Preserve unrelated changes; record and restore only a stash created by this run, including untracked files when necessary. Capture conflicts under .tmp/rebase/ and resolve from verified intent rather than blindly taking a side. Continue/abort only the in-progress operation requested.

Report stash restoration failures as incomplete. Verify tests after content changes. A later push needs an expected-head/lease guard and authorization for the rewrite; rebasing alone does not authorize force-publishing.

Follow the host’s instructions and current authorization. Tool names, delegation, models, sandboxing, and question availability come from the running Codex session; this skill does not override them. Resolve helpers from this SKILL.md’s actual directory (SKILL_DIR in examples is a variable you set, not a Codex substitution).
