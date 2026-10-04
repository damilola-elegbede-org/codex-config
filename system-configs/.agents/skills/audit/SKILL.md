---
name: "audit"
description: "Audit Codex skill and agent definitions for schema, resource, and configuration integrity. Use for configuration ecosystem checks, with optional scoped repairs."
metadata: {"source-repository": "damilola-elegbede-org/claude-config", "source-commit": "cb257acb72ef568efc5d9dc2c25c365b179383b0", "source-path": "system-configs/.claude/skills/audit/SKILL.md"}
---

# audit

Find the repository-owned source or the explicitly requested installed directories. Count actual SKILL.md entrypoints and agent TOML files; do not hardcode ecosystem totals.

Validate skill YAML name/description, directory/name agreement, linked resources, script paths, and supported metadata. Validate agent TOML name, description, developer_instructions, read-only versus implementation boundaries, and inherited configuration. Inspect for obsolete Claude tool calls, unavailable hooks, hardcoded models, missing resources, and source drift.

In codex-config run scripts/validate-extensions.py on the source roots, then scripts/validate.sh on an isolated staged Codex home. In another repo, locate its validator or perform the checks directly; do not assume those scripts exist. Default mode is read-only. Fix mode repairs verified issues within scope and re-validates; never weaken a schema or quality gate to report success.

Follow the host’s instructions and current authorization. Tool names, delegation, models, sandboxing, and question availability come from the running Codex session; this skill does not override them. Resolve helpers from this SKILL.md’s actual directory (SKILL_DIR in examples is a variable you set, not a Codex substitution).
