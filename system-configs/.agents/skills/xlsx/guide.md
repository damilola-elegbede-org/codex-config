# Spreadsheet workflow

Inventory sheet names, dimensions, formulas, styles, merged cells, named ranges, external links, and macros. Preserve the input. Choose a compatible editor for unsupported features; do not silently strip them.

Current API and preservation limits: https://openpyxl.readthedocs.io/en/stable/tutorial.html

For supported bounded edits with an available dependency:

```python
from openpyxl import load_workbook
workbook = load_workbook("input.xlsx", data_only=False)
sheet = workbook["Sheet1"]
sheet["B2"] = "=SUM(B3:B8)"
workbook.save("output.xlsx")
```

Keep formulas as formulas. Align inputs, units, dates, currencies, and percentages with existing conventions. Use consistent styles, clear headers, and human-readable column widths. Verify ranges and relative/absolute references after inserting rows or sheets. Do not replace unknown formulas with guessed values.

openpyxl and XlsxWriter do not calculate formulas. An available spreadsheet engine such as LibreOffice can recalculate an exported copy; verify cached results afterwards with data_only=True. When recalculation is unavailable, say so. Check formula errors including #REF!, #DIV/0!, #VALUE!, #NAME?, and #N/A in the relevant cells. A stale cache is not evidence of a correct formula.

Run `python3 ../office-common/package-check.py output.xlsx` from this skill directory. This validates ZIP/XML integrity, not business logic, formula calculation, macro behavior, or visual layout. Inspect relevant sheets with an available renderer/editor when formatting matters.
