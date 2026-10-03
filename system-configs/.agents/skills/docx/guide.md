# DOCX workflow

1. Read the supplied file and identify the requested changes. Keep an untouched copy.
2. Inspect with an available library or editor before choosing how to edit. python-docx preserves many document structures but does not support every Word feature; detect tracked changes, macros, signatures, content controls, comments, and fields before saving.
3. For a new document, define page size, margins, styles, heading levels, and table widths explicitly. Use real paragraph styles and lists rather than formatting everything as normal text. Use table headers and meaningful image descriptions where supported.
4. For supported edits, change the smallest affected structure. Retain relationships and embedded objects. Check the output's document structure and text against the requested change.
5. Run `python3 ../office-common/package-check.py output.docx` from this skill directory, then render with an available document engine for visual inspection. This checks ZIP/XML integrity only; it is not full Word schema or layout validation.

Current library API: https://python-docx.readthedocs.io/en/latest/user/quickstart.html

Minimal creation example, using an already available dependency:

```python
from docx import Document

document = Document()
document.add_heading("Report", level=0)
document.add_paragraph("Requested content")
document.save("output.docx")
```

Writing to a new output avoids overwriting the input, but does not by itself prove that editing an existing document preserved every feature. Report which visual and structural checks were performed.
