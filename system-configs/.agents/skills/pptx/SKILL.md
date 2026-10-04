---
name: "pptx"
description: "Create, read, or edit PowerPoint presentations, including templates, notes, layouts, and visual review. Use when a slide deck is requested."
metadata: {"source-repository": "damilola-elegbede-org/claude-config", "source-commit": "cb257acb72ef568efc5d9dc2c25c365b179383b0", "source-path": "system-configs/.claude/skills/pptx/SKILL.md"}
---

# pptx

Read guide.md. Use python-pptx for new slides and edits its API supports, or an available presentation tool for unsupported animation, complex charts, and other advanced content. Start from the supplied template when present. Preserve slide dimensions, masters, theme, fonts, notes, and user content. Plan hierarchy and a grid before adding shapes; use editable text and meaningful charts. Validate the ZIP/XML package using ../office-common/package-check.py, render with an available presentation engine, inspect every slide for clipping, overlap, contrast, and reading order, then fix and re-render. Report unrendered or unsupported content.

These Codex instructions are independently authored. The source repository's restricted office/PDF implementation and assets are not bundled. Resolve helpers from this skill's actual directory; dependencies are used only if available or installation is authorized. Follow host instructions and current authorization.
