# PDF workflow

Decide whether the request concerns reading, generating, editing, forms, or redaction. Keep the input intact and write a separate output. Encrypted PDFs require authorized access; do not bypass permissions.

For text, pypdf's PdfReader can extract text page by page:

```python
from pypdf import PdfReader
reader = PdfReader("input.pdf")
for number, page in enumerate(reader.pages, start=1):
    print(number, page.extract_text() or "")
```

Current extraction API and limits: https://pypdf.readthedocs.io/en/stable/user/extract-text.html

Text extraction cannot recover text from an image scan; OCR is a separate step. Layout, tables, reading order, and unusual fonts may need rendering and visual inspection. Do not invent missing content.

For splitting or merging, copy actual page objects with a supported writer and check output page count and ordering. For forms, inspect get_fields() output, validate requested field values, use the supported field-update API, and inspect appearances in a rendered output; some forms require a capable desktop editor. For annotations, use documented page coordinates and verify them visually.

For new documents use an available PDF creation library such as ReportLab. Set page geometry, fonts, and wrapping deliberately. Render pages with an available PDF engine and inspect clipping, legibility, glyphs, and pagination.

A visible rectangle does not remove text. True redaction must remove the underlying objects and metadata where relevant; verify by text extraction and inspection after applying a supported redaction operation. Never promise this from an overlay.
