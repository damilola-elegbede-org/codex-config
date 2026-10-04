---
name: "plan"
description: "Turn a feature or project request into a grounded PRD and dependency-ordered implementation slices. Use for planning; supports simple, preview-only, and file-input modes."
metadata: {"source-repository": "damilola-elegbede-org/claude-config", "source-commit": "cb257acb72ef568efc5d9dc2c25c365b179383b0", "source-path": "system-configs/.claude/skills/plan/SKILL.md"}
---

# plan

Read repository instructions, README, architecture, existing modules, and test conventions. Verify factual claims before choosing a design. Use the request or supplied file; ask for the goal only if absent.

Walk the relevant decisions: actors, happy path, edge cases, data, module boundaries, API contracts, testing, security, observability, dependencies, and exclusions. In simple mode, focus on actors, flow, edges, tests, and exclusions. State material choices as Q / A / Why while working, grounded in code and open to D’s correction. Use existing conventions and avoid speculative work.

Write .tmp/plans/<repo>/<feature>/prd.md plus PR-sized phase_<n>_pr_<m>_<slug>.md files, unless preview-only/no-execute was requested. Each slice has a Tasks checkbox list with dependencies and an Acceptance or Acceptance Criteria checklist. Put stable goals and decisions in the PRD; current implementation paths belong in task files. Report the paths and first ready slice. Planning alone does not authorize implementation or remote writes.

Follow the host’s instructions and current authorization. Tool names, delegation, models, sandboxing, and question availability come from the running Codex session; this skill does not override them. Resolve helpers from this SKILL.md’s actual directory (SKILL_DIR in examples is a variable you set, not a Codex substitution).
