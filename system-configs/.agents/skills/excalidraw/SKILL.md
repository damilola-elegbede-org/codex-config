---
name: "excalidraw"
description: "Create and visually validate themed Excalidraw diagrams for systems, flows, sequences, and state machines."
metadata: {"source-repository": "damilola-elegbede-org/claude-config", "source-commit": "cb257acb72ef568efc5d9dc2c25c365b179383b0", "source-path": "system-configs/.claude/skills/excalidraw/SKILL.md"}
---

# excalidraw

Read guide.md and the relevant references/ for layout, schema, binding, and palettes. Resolve scripts/render.mjs and scripts/check-theme.mjs from this skill directory. Choose the requested palette, or Tokyo Night by default; GitHub Light suits print. Plan tiers/lanes before emitting elements. Bind labels bidirectionally to containers, leave arrow bindings null with explicit points, and do not invert a baked dark palette with appState.theme. Render, inspect with the available image-viewing tool, fix overlaps/clipping/contrast, and re-render; run the theme validator. Report exact files and what was visually checked. Use diagrams generated from a schema for database models rather than a manually drifting ER drawing.

Follow the host’s instructions and current authorization. Tool names, delegation, models, sandboxing, and question availability come from the running Codex session; this skill does not override them. Resolve helpers from this SKILL.md’s actual directory (SKILL_DIR in examples is a variable you set, not a Codex substitution).
