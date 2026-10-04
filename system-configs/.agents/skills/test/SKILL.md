---
name: "test"
description: "Discover and run a project’s test suite, or create tests when requested. Reports failures without silently repairing them."
metadata: {"source-repository": "damilola-elegbede-org/claude-config", "source-commit": "cb257acb72ef568efc5d9dc2c25c365b179383b0", "source-path": "system-configs/.claude/skills/test/SKILL.md"}
---

# test

Discover the command from README/project instructions, package-manager scripts, framework configuration, then test files. Read references/discovery.md for the language table and coverage flags. An explicit framework or suite overrides discovery. If several materially different suites exist, use the requested/relevant suite or ask when the choice changes scope or cost.

Run the actual command and report its output, counts, exit status, and failing assertions with locations. Distinguish no tests, failed tests, and unavailable tooling. This skill runs and reports; do not silently change code or assertions to improve the grade.

Create mode is explicit permission to add meaningful behavioral tests, using test-engineer if delegation is allowed. Run the generated tests before claiming they work. Coverage mode uses the project’s configured measurement; do not impose an invented threshold.

Follow the host’s instructions and current authorization. Tool names, delegation, models, sandboxing, and question availability come from the running Codex session; this skill does not override them. Resolve helpers from this SKILL.md’s actual directory (SKILL_DIR in examples is a variable you set, not a Codex substitution).
