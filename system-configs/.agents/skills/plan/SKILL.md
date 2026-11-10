---
name: "plan"
description: "Turn a feature or project request into a grounded PRD and dependency-ordered implementation slices. Use for planning; supports simple, preview-only, and file-input modes."
metadata: {"source-repository": "damilola-elegbede-org/claude-config", "source-commit": "06fcb1349e93860a779c14c5ac47b9bf0cbe2aa4", "source-path": "system-configs/.claude/skills/plan/SKILL.md"}
---

# plan

Read repository instructions, README, architecture, existing modules, and test conventions. Verify factual claims before choosing a design. Use the request or supplied file; ask for the goal only if absent.

Walk the relevant decisions: actors, happy path, edge cases, data, module boundaries, API contracts, testing, security, observability, dependencies, and exclusions. In simple mode, focus on actors, flow, edges, tests, and exclusions. Keep the decision walk in the main conversation so D can correct choices as they are made. State material choices and their reasons while working, grounded in code and open to D’s correction; follow the active response format. Use existing conventions and avoid speculative work.

Write .tmp/plans/<repo>/<feature>/prd.md plus PR-sized phase_<n>_pr_<m>_<slug>.md files, unless preview-only/no-execute was requested. Each slice has a Tasks checkbox list with dependencies and an Acceptance or Acceptance Criteria checklist. Put stable goals and decisions in the PRD; current implementation paths belong in task files. Report the paths and first ready slice. Planning alone does not authorize implementation or remote writes.

Follow the host’s instructions and current authorization. Tool names, delegation, models, sandboxing, and question availability come from the running Codex session; this skill does not override them. Resolve helpers from this SKILL.md’s actual directory (SKILL_DIR in examples is a variable you set, not a Codex substitution).
