---
name: "pdf"
description: "Read, create, combine, split, OCR, or fill PDF documents. Use when a PDF is the input or requested output."
metadata: {"source-repository": "damilola-elegbede-org/claude-config", "source-commit": "cb257acb72ef568efc5d9dc2c25c365b179383b0", "source-path": "system-configs/.claude/skills/pdf/SKILL.md"}
---

# pdf

Read guide.md. Choose pypdf for text/metadata, splitting, merging, and supported forms; PyMuPDF for rendering; or ReportLab for a new PDF. Scans need OCR through an available authorized tool. Extracted text alone does not prove visual fidelity. For forms, inspect actual field names, types, page geometry, and permission constraints before filling; retain the original and check the completed values and render. Never label a drawing overlay as securely redacted. For redaction use a verified tool that removes the underlying content, then test extraction and appearance. Do not invent a bundled PDF annotation or form helper; use supported library APIs and verify their current documentation.

These Codex instructions are independently authored. The source repository's restricted office/PDF implementation and assets are not bundled. Resolve helpers from this skill's actual directory; dependencies are used only if available or installation is authorized. Follow host instructions and current authorization.
