---
name: "gauntlet-loop"
description: "Build a deliverable against a concrete reference using independent builder/critic rounds and a blind final panel. Use only when a rigorous gauntlet is explicitly requested."
metadata: {"source-repository": "damilola-elegbede-org/claude-config", "source-commit": "cb257acb72ef568efc5d9dc2c25c365b179383b0", "source-path": "system-configs/.claude/skills/gauntlet-loop/SKILL.md"}
---

# gauntlet-loop

Require a named concrete reference and access to it. Confirm modality: compare like artifacts; if not comparable, propose rubric-only mode and label that limitation. Establish the reference, iteration budget, immediate execution versus plan-only, rubric, aspect decomposition, and final playback with D. Preserve already-settled choices; ask only missing decisions. A final confirmed Task / Build Method / Bar to Hit and rubric is the execution contract.

Use available Codex delegation, not a Claude Workflow tool. If independent contexts are unavailable or prohibited, stop with that limitation. Record a finite agreed cap (default proposal: five revisions per aspect and three panel cycles); do not silently promise an unbounded run. Save the prompt and progress ledger under .tmp/plans/gauntlet/. Plan-only does not launch agents. No recurrence, scheduler, production write, publishing, sending, or purchase is authorized by this skill.

One persistent builder owns each disjoint aspect. Each revision returns artifact locations and addressed rubric IDs. One fresh harsh critic per aspect/round receives the artifact and rubric, without previous verdicts, and returns only located defects tagged by rubric ID. Empty defects is the pass. Close a previously open item only when the critic omits it AND the builder supplies matching current-round change evidence. Reappearing IDs are regressions. The same unresolved rubric ID for three consecutive rounds stalls that aspect; other independent work can finish.

A separate integrator reconciles aspects by rubric priority. Integration defects re-enter the appropriate aspect loop; unassigned defects become explicit cross-cutting work. Do not advance to judgment with unresolved stalls.

Use at least three fresh final panelists on distinct rubric slices covering the complete rubric. Randomize anonymized A/B order separately for each; do not reveal authorship or prior verdicts. Each slice returns clearly prefers build / prefers build / toss-up / prefers reference. Completion requires unanimous clearly prefers build. Rubric-only mode instead requires every slice to meet its written criteria and discloses that no blind artifact comparison occurred. Route dissent only to implicated aspects. Three repeated (aspect, rubric-ID) panel failures stall rather than endlessly cycling.

At any cap, stall, missing critic, or cancelled run, preserve the ledger and report incomplete. Deliver the actual final artifact only when its gate passes, with real agent-call counts, aspect rounds, panel verdicts, and limitations. Do not imply technical isolation solely because prompts restrict the agents.

Follow the host’s instructions and current authorization. Tool names, delegation, models, sandboxing, and question availability come from the running Codex session; this skill does not override them. Resolve helpers from this SKILL.md’s actual directory (SKILL_DIR in examples is a variable you set, not a Codex substitution).
