---
name: "xlsx"
description: "Create, read, clean, or edit spreadsheet files with formulas and formatting. Use when the primary deliverable is XLSX, XLSM, CSV, or TSV."
metadata: {"source-repository": "damilola-elegbede-org/claude-config", "source-commit": "cb257acb72ef568efc5d9dc2c25c365b179383b0", "source-path": "system-configs/.claude/skills/xlsx/SKILL.md"}
---

# xlsx

Read guide.md. Use openpyxl for existing spreadsheets and formulas or XlsxWriter for new workbooks, matching the user's existing conventions. Preserve formulas, number formats, sheet order, references, and user inputs. Load with data_only=False for editing; data_only=True exposes only cached values and does not calculate formulas. Use an available authorized spreadsheet engine for recalculation; report when none is available. VBA, external links, complex drawings, and other unsupported content require a compatible tool and preservation checks. For XLSX only, validate ZIP/XML integrity using ../office-common/package-check.py. For XLSM, use a macro-capable editor with VBA preservation checks and a compatible package validator; do not send it to the XLSX-only checker. For CSV/TSV, parse the correct delimiter and encoding, verify row/column counts and values, and round-trip through an appropriate reader. For every supported format, inspect relevant sheets and formula errors, and distinguish values you recalculated from stale caches.

These Codex instructions are independently authored. The source repository's restricted office/PDF implementation and assets are not bundled. Resolve helpers from this skill's actual directory; dependencies are used only if available or installation is authorized. Follow host instructions and current authorization.
