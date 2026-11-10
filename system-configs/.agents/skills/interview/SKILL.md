---
name: "interview"
description: "Settle a task’s requirements through an explicit interview, then execute the confirmed authorized scope to its completion criteria."
metadata: {"source-repository": "damilola-elegbede-org/claude-config", "source-commit": "06fcb1349e93860a779c14c5ac47b9bf0cbe2aa4", "source-path": "system-configs/.claude/skills/interview/SKILL.md"}
---

# interview

Map unanswered choices internally; ask only questions whose answers change the work and cannot be resolved from the conversation or files. Include access, naming, execution scope, and the evidence required for completion. Read enough to ground the questions; settle the explicit interview before implementation. Start with up to three related scoping questions, then targeted follow-ups. Keep unrelated decisions separate.

Use the available Codex question tool under its mode rules, or plain questions if no suitable tool exists. Include the context and recommendation in each question; read ../ask/SKILL.md when the question format needs detail.

When the remaining questions would not change the work, play back: goal, constraints, D’s decisions, exclusions, assumptions, authorized actions, and checkable Done when criteria. Ask whether that understanding is confirmed or needs correction. Keep an explicitly requested interview open until D confirms. If D says to proceed or stop interviewing, state remaining assumptions and follow that instruction.

After confirmation, execute the authorized task until the Done when criteria are met. Do not re-ask settled decisions or introduce routine approval pauses. For an uncovered reversible implementation choice within scope, use judgment, note the choice, and continue. Ask only for material missing intent, an action only D can perform, or authorization genuinely required by the host for spending, irreversible actions, or other restricted operations. Confirmation records task scope; it does not create tool permissions, permission leases, or a Claude stop-hook contract.

Finish with evidence for completed criteria, or the exact blocker and remaining work. Do not claim completion merely because the interview ended.

Follow the host’s instructions and current authorization. Tool names, delegation, models, sandboxing, and question availability come from the running Codex session; this skill does not override them. Resolve helpers from this SKILL.md’s actual directory (SKILL_DIR in examples is a variable you set, not a Codex substitution).
