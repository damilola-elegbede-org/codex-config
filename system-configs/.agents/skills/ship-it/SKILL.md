---
name: "ship-it"
description: "Run requested documentation, test, verification, review, commit, push, and PR stages in order. Use when shipping code is requested; supports a no-write preview."
metadata: {"source-repository": "damilola-elegbede-org/claude-config", "source-commit": "06fcb1349e93860a779c14c5ac47b9bf0cbe2aa4", "source-path": "system-configs/.claude/skills/ship-it/SKILL.md"}
---

# ship-it

Parse only current flags: d=docs, t=test, v=verify, r=review, x=pre-publish review, c=commit, p=push, pr=PR. No flags selects docs → test → verify → review → commit → push → PR, within the user’s scope. The x stage and the review required by pr use Codex’s native review workflow; they do not spawn a recursive CLI or require a second login. Reject ambiguous partial combinations before writes; do not infer a merge or deployment stage.

Dry-run reports enabled stages and required authorizations without executing them. Otherwise read the sibling SKILL.md for each selected stage and perform it directly; Codex has no Claude Skill dispatcher or commit-commands plugin dependency.

Before any commit, push, or PR stage, run current required project gates in this invocation (report-only verify if v was not selected). Tests alone do not prove lint/typecheck/build. Halt on failed or unavailable required checks. If the project genuinely defines none, disclose that nothing was checked rather than inventing a green gate.

For x or any PR path, use ../review/references/pre-publish.md. A single valid result for the same base and content satisfies both r and x; a duplicate invocation is not another independent review. In the PR-only path, pr owns that review and verifies the actual publication state. A cached review never exempts checking that intended fixes are committed and pushed. With p or pr selected but c absent, uncommitted task-owned fixes must be committed within existing authorization or reported as incomplete; never publish a partial fix set. Review-only x does not require a commit.

Use authorized identity tooling and preserve hooks or execute their required equivalents for connector publishing. If repairs change code, repeat affected gates before publishing. Preserve authorized skipped-review acknowledgments across rounds. The pr stage follows the exact head through the sibling land workflow and reports its bounded outcome; a PR URL alone is not evidence of readiness. Return exact commit/branch/PR evidence, which stages ran, and what remains.

Follow the host’s instructions and current authorization. Tool names, delegation, models, sandboxing, and question availability come from the running Codex session; this skill does not override them. Resolve helpers from this SKILL.md’s actual directory (SKILL_DIR in examples is a variable you set, not a Codex substitution).
