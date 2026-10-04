---
name: "review"
description: "Review a branch, commit, working diff, or requested wider codebase for consequential defects. Deep mode adds security and accessibility perspectives."
metadata: {"source-repository": "damilola-elegbede-org/claude-config", "source-commit": "cb257acb72ef568efc5d9dc2c25c365b179383b0", "source-path": "system-configs/.claude/skills/review/SKILL.md"}
---

# review

Identify the explicit scope; otherwise compare the branch to its verified base and include staged and unstaged changes. Full mode examines the requested tracked codebase. No diff is no changed code to review, not proof of quality.

Default review is independent and read-only. Use code-reviewer if delegation is permitted; otherwise inspect directly. Deep mode adds security-auditor and a separate accessibility brief, respecting concurrency limits. Use the corresponding prompts in references/; do not pin Claude models or assume missing custom agent types.

Find concrete failure scenarios, supported by file/line evidence, and prioritize repository-specific risks over mechanical nits already covered by CI. Deduplicate matching findings without dropping disagreement. Write .tmp/review-local.json with schema_version 1.0, branch, issues, and walkthrough as described in ../resolve-comments/references/schemas.md. Invalid or missing reviewer output is an incomplete review, never a clean pass.

In deep mode, keep .tmp/review-code.json, .tmp/review-security.json, and .tmp/review-accessibility.json independent. After all three finish, validate their schema, branch, and source_sha and aggregate their issues and walkthrough entries into .tmp/review-local.json using the shared schema. Qualify issue IDs by producer, preserve each finding’s source and original_id, and retain disagreements. The combined file is the input to file-mode resolution. Missing or invalid output makes the review incomplete; never substitute an empty pass.

Review alone does not authorize repairs or publishing. When fixes are requested, use resolve-comments to validate and act on them. Preserve the host’s exact code-review output schema when one is required.

Follow the host’s instructions and current authorization. Tool names, delegation, models, sandboxing, and question availability come from the running Codex session; this skill does not override them. Resolve helpers from this SKILL.md’s actual directory (SKILL_DIR in examples is a variable you set, not a Codex substitution).
