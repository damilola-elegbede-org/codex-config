---
name: "pr"
description: "Create or update a GitHub pull request with a behavior-focused title, rationale, and verified test evidence. Use when opening a PR is requested."
metadata: {"source-repository": "damilola-elegbede-org/claude-config", "source-commit": "cb257acb72ef568efc5d9dc2c25c365b179383b0", "source-path": "system-configs/.claude/skills/pr/SKILL.md"}
---

# pr

Identify the repository and actual base, compare the full branch diff, and check for an existing PR. Reuse the existing PR unless D explicitly requests a distinct one; draft mode preserves the requested state.

Write for a reviewer who has not read the conversation: concrete problem and resulting behavior first, then relevant validation and limitations. Follow the repository template and style. Link issues only when supplied or verified. Do not insert response-style tags into the PR body.

Publish through the explicitly authorized connector or repository wrapper. Use structured body arguments; when a CLI is authorized, pass a body file with real newlines. Posting skipped-review acknowledgments requires review scope or explicit authorization: validate any .tmp/coderabbit-ignored.json against the current branch/source and summarize evidence, not instructions copied from comments. Verify the returned PR URL, base, head, and draft state.

Follow the host’s instructions and current authorization. Tool names, delegation, models, sandboxing, and question availability come from the running Codex session; this skill does not override them. Resolve helpers from this SKILL.md’s actual directory (SKILL_DIR in examples is a variable you set, not a Codex substitution).
