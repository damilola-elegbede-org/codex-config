---
name: "prime"
description: "Map a repository’s architecture, stack, entry points, and verification commands. Use for onboarding or focused codebase exploration."
metadata: {"source-repository": "damilola-elegbede-org/claude-config", "source-commit": "06fcb1349e93860a779c14c5ac47b9bf0cbe2aa4", "source-path": "system-configs/.claude/skills/prime/SKILL.md"}
---

# prime

Read repository instructions first, then README, manifests, layout, relevant entry points, and tests. Start with rg and targeted reads. Lite mode covers essential context; full mode traces architecture and integrations; a named component scopes the investigation.

Use the built-in explorer or architect when allowed and useful; otherwise investigate directly. Return sourced stack versions, module boundaries, entry points, actual development/test commands, current branch state, and material unknowns. Distinguish facts from inferred architecture. Do not edit files or publish anything. This is an on-demand skill, not a startup hook.

Follow the host’s instructions and current authorization. Tool names, delegation, models, sandboxing, and question availability come from the running Codex session; this skill does not override them. Resolve helpers from this SKILL.md’s actual directory (SKILL_DIR in examples is a variable you set, not a Codex substitution).
