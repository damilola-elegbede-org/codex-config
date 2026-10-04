---
name: "interview"
description: "Interview D in structured rounds to settle a task’s requirements. Use when explicitly asked to interview, eliminate guesses, or confirm understanding."
metadata: {"source-repository": "damilola-elegbede-org/claude-config", "source-commit": "cb257acb72ef568efc5d9dc2c25c365b179383b0", "source-path": "system-configs/.claude/skills/interview/SKILL.md"}
---

# interview

Map the unanswered choices internally; ask only questions whose answers change the work and cannot be resolved from the conversation or files. Start with up to three related scoping questions, then targeted follow-ups. Keep unrelated decisions separate.

Use the available Codex question tool under its mode rules, or plain questions if no suitable tool exists. Include the context and recommendation in each question; read ../ask/SKILL.md when the question format needs detail.

When the remaining questions would not change the work, play back: goal, constraints, D’s decisions, exclusions, and any assumptions. Ask whether that understanding is confirmed or needs correction. Keep an explicitly requested interview open until D confirms. If D says to proceed or stop interviewing, state the remaining assumptions and follow that instruction. Do not re-open settled decisions during execution.

Follow the host’s instructions and current authorization. Tool names, delegation, models, sandboxing, and question availability come from the running Codex session; this skill does not override them. Resolve helpers from this SKILL.md’s actual directory (SKILL_DIR in examples is a variable you set, not a Codex substitution).
