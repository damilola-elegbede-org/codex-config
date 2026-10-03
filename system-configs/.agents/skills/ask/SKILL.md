---
name: "ask"
description: "Present a focused decision or request for missing information with a recommendation. Use when D asks to be consulted or a material decision remains unresolved."
metadata: {"source-repository": "damilola-elegbede-org/claude-config", "source-commit": "cb257acb72ef568efc5d9dc2c25c365b179383b0", "source-path": "system-configs/.claude/skills/ask/SKILL.md"}
---

# ask

Ask one decision at a time. For a cold topic, put the headline, plain context, dated latest fact, consequence, and question together so the dialog is self-contained. For a warm topic, ask directly.

Use the question tool actually available in the session and permitted in its current mode. Prefer 2–3 concrete choices, with exactly one recommended choice and a reason. Do not invent a Claude question tool, multiselect, preview fields, or tool parameters. If no suitable question tool is available, ask plainly. Permission questions must follow the host's permission rules.

Do not ask again for already-authorized work or facts you can inspect. Optional questions may proceed under a stated assumption if host instructions permit; required answers and approvals remain pending until D responds. Act on the answer and record it in the requested artifact when appropriate. A correction to the premise is the answer, not a reason to repeat the question.

Follow the host’s instructions and current authorization. Tool names, delegation, models, sandboxing, and question availability come from the running Codex session; this skill does not override them. Resolve helpers from this SKILL.md’s actual directory (SKILL_DIR in examples is a variable you set, not a Codex substitution).
