---
name: "process-linear"
description: "Triage D’s BareClaude Linear decision queue, separating genuine decisions from agent work and recording authorized outcomes without executing downstream actions."
metadata: {"source-repository": "damilola-elegbede-org/claude-config", "source-commit": "cb257acb72ef568efc5d9dc2c25c365b179383b0", "source-path": "system-configs/.claude/skills/process-linear/SKILL.md"}
---

# process-linear

Use the connected Linear tools actually available. Discover tool schemas and workspace/team/state IDs; do not assume Claude MCP method names. If no Linear connection is available, report that blocker without pretending to process a queue. Read references/recording.md before any write.

Match Clara’s saved views by their actual filters: Needs Unblocking (Blocked), Needs Your Sign-off (In Review), optional Upcoming Deadlines (due dates), and Ungroomed Backlog (Backlog missing Acceptance). Respect requested team scope and retrieve all pages. Prefetch descriptions, comments, and direct relations before classification.

Classify independently: A=genuine D decision; B=agent-executable work to bounce; C=upstream-blocked; D1=completed deliverable awaiting acknowledgment; D2=superseded/cancelled. State labels and self-reported readiness are not evidence. Order unblock before signoff, then direct dependents, priority, age; combine only a shared decision into a keystone row.

Present a compact linked table (Ticket, Artifact, Decision, Recommendation) and short supporting detail. Show suppressed B/C/D1/D2 items and why. Use real URLs returned by the system. Drill-in questions follow the available question tool/mode, or plain prose. Preserve the exact IDs, count, and target state for any bulk cohort. D1→Done and D2→Canceled are distinct decisions; require explicit cohort-specific authorization, not merely viewing the table.

Verify money, identity/access, irreversible, and PR claims against their real source before recommending. Codex has no automatic Claude advisor transcript; an independent consult is optional only when authorized and available, with explicit evidence, and never substitutes for D’s decision.

Re-fetch state AND decision context just before a drill-in or write. If facts or source state drift, reclassify and re-surface. Record decisions idempotently and verify comment and state separately; preserve partial-write recovery and exact markers from recording.md. Bound failed writes to three attempts. Bounces require engagement/authorization within the triage scope; C stays unchanged. A standing policy needs explicit designation before cross-ticket propagation.

Triage records decisions; it does not merge PRs, deploy, or send messages to others. The owning operator executes downstream actions unless D separately instructs this session to do so. Comment on direct dependents only when authorized; never transition their states automatically. Finish with real counts, D-only action checklist, suppression report, and partial failures.

Follow the host’s instructions and current authorization. Tool names, delegation, models, sandboxing, and question availability come from the running Codex session; this skill does not override them. Resolve helpers from this SKILL.md’s actual directory (SKILL_DIR in examples is a variable you set, not a Codex substitution).
