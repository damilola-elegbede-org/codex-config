---
name: "deps"
description: "Audit, update, or clean dependencies across detected package managers. Use when dependency health or safe upgrades are requested."
metadata: {"source-repository": "damilola-elegbede-org/claude-config", "source-commit": "cb257acb72ef568efc5d9dc2c25c365b179383b0", "source-path": "system-configs/.claude/skills/deps/SKILL.md"}
---

# deps

Detect each manifest and lockfile. Default/quick mode runs the ecosystem’s own audit and outdated-package tooling and reports evidence without edits. Read references/ecosystems.md for commands and references/risk-matrix.md for severity and supply-chain indicators.

For authorized updates, inspect release notes and compatibility, preserve a rollback point, and update manifests with lockfiles. Apply compatible fixes within scope; identify the concrete breaking change before a major or behavior-changing upgrade. Do not blindly force an audit fix. Clean only dependencies proved unused.

Run the project’s appropriate tests after changes. On failure, restore only changes made by this workflow, preserving pre-existing work. Report advisories, package versions, real outcomes, and unresolved risk. Delegate independent ecosystems only when allowed; otherwise perform the same checks sequentially.

Follow the host’s instructions and current authorization. Tool names, delegation, models, sandboxing, and question availability come from the running Codex session; this skill does not override them. Resolve helpers from this SKILL.md’s actual directory (SKILL_DIR in examples is a variable you set, not a Codex substitution).
