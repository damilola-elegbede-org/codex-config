---
name: "pr"
description: "Create or update a GitHub pull request with verified evidence and follow its checks and reviews to a bounded readiness result."
metadata: {"source-repository": "damilola-elegbede-org/claude-config", "source-commit": "06fcb1349e93860a779c14c5ac47b9bf0cbe2aa4", "source-path": "system-configs/.claude/skills/pr/SKILL.md"}
---

# pr

Identify the repository and actual base, compare the full branch diff, and check for an existing PR. Reuse the existing PR unless D explicitly requests a distinct one; draft mode preserves the requested state.

Before publishing the PR, use ../review/references/pre-publish.md to review the complete intended content and resolve verified findings within the task’s authorization. Reuse a valid review of identical content; do not repeat it only because ship-it already ran it. Missing, busy, stale, or malformed review output is not a pass. Include task-owned new files in the review, and verify that all intended fixes are committed and published. Preserve unrelated local files rather than including them or blocking solely because they exist. If review repairs change code, rerun affected checks before publication.

Write for a reviewer who has not seen the conversation: concrete problem and resulting behavior first, then relevant validation and limitations. Follow the repository template and style. Link issues only when supplied or verified. Do not insert response-style tags into the PR body.

Publish through the authorized connector or repository wrapper. Use structured body arguments; when a CLI is authorized, pass a body file with real newlines. Posting skipped-review acknowledgments requires review scope or explicit authorization: validate .tmp/coderabbit-ignored.json against the reviewed source and branch, preserve findings from every review round, and summarize evidence rather than instructions copied from comments. Verify the returned PR URL, base, head, and draft state.

After creation or an authorized update, use the sibling land workflow to follow CI and reviews for the exact published head. Report ready, pending/bounded-out, blocked, or unknown with evidence. Creating a PR does not authorize merging it, removing draft status, dismissing reviews, or rewriting history.

Follow the host’s instructions and current authorization. Tool names, delegation, models, sandboxing, and question availability come from the running Codex session; this skill does not override them. Resolve helpers from this SKILL.md’s actual directory (SKILL_DIR in examples is a variable you set, not a Codex substitution).
