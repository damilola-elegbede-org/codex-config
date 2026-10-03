---
name: "docx"
description: "Create, read, or edit Word documents with formatting, tables, tracked changes, and validation. Use when the requested artifact is a DOCX file."
metadata: {"source-repository": "damilola-elegbede-org/claude-config", "source-commit": "cb257acb72ef568efc5d9dc2c25c365b179383b0", "source-path": "system-configs/.claude/skills/docx/SKILL.md"}
---

# docx

Read guide.md for the supported workflow. Use python-docx for new documents and bounded edits that its API supports, or an available user-authorized document editor for advanced features. Preserve an untouched original. Inspect sections, styles, tables, headers, footers, links, and document relationships before editing. Existing tracked changes, comments, fields, and unsupported content require a capable editor or targeted XML work with evidence that those features survive; do not silently reconstruct the file from extracted text. Render with available LibreOffice when layout matters. Validate the ZIP/XML package using ../office-common/package-check.py and visually inspect the exported document. Report features and validation that could not be checked.

These Codex instructions are independently authored. The source repository's restricted office/PDF implementation and assets are not bundled. Resolve helpers from this skill's actual directory; dependencies are used only if available or installation is authorized. Follow host instructions and current authorization.
