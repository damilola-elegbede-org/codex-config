---
name: "goal-status"
description: "Report the current persistent goal, measured budget use, progress, and remaining work without changing its state."
metadata: {"source-repository": "damilola-elegbede-org/claude-config", "source-commit": "06fcb1349e93860a779c14c5ac47b9bf0cbe2aa4", "source-path": "system-configs/.claude/skills/goal-status/SKILL.md"}
---

# Goal status

Use the session's available goal-read tool (such as `get_goal`) to retrieve the
current goal. Report its actual objective, state, measured token/time usage,
remaining budget, and any limits the tool returns. Keep planned work separate
from completed work backed by tool results, commits, or acceptance checks.

If no persistent goal exists, say so and summarize the current task only when
the conversation establishes one. If the tool is unavailable, report that
measured goal state cannot be read; do not infer a budget or inspect another
agent's private database/transcript as a substitute.

Name the next unfinished acceptance item or the evidenced blocker. Do not
invent a completion percentage, past check history, or ETA. This is a read-only
report: it does not create a goal, change its budget, pause it, or mark it complete.
