---
name: "docs"
description: "Create, update, or audit project documentation against the current implementation. Use for README, API, architecture, or setup documentation."
metadata: {"source-repository": "damilola-elegbede-org/claude-config", "source-commit": "cb257acb72ef568efc5d9dc2c25c365b179383b0", "source-path": "system-configs/.claude/skills/docs/SKILL.md"}
---

# docs

Compare the branch with its actual base and include staged and unstaged changes. Cross-check existing documentation against source, CLI help, and real commands. Default mode updates affected docs; audit mode reports gaps without edits; full mode scans the requested wider scope; a focused request always examines that scope.

Do not edit AGENTS.md, AGENTS.override.md, or CLAUDE.md as ordinary documentation: they are behavior contracts and require an explicit request. Keep reusable docs in the project’s documented location; temporary analysis belongs in .tmp/. Move existing files only when cleanup is requested and their consumers are understood.

Handle simple updates directly. For larger work, delegate only if allowed; use a general worker with a writing brief rather than assuming a nonexistent tech-writer agent. Verify examples and links, reconcile cross-references, and report the changed files and validation. Skip only when the source and docs are demonstrably unchanged or already aligned.

Follow the host’s instructions and current authorization. Tool names, delegation, models, sandboxing, and question availability come from the running Codex session; this skill does not override them. Resolve helpers from this SKILL.md’s actual directory (SKILL_DIR in examples is a variable you set, not a Codex substitution).
