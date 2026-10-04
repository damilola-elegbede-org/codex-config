# PowerPoint workflow

Use an available presentation engine when a template or advanced feature needs fidelity. python-pptx supports common shape/text operations but not every PowerPoint feature; inspect the input before choosing it. Keep original media, themes, and masters unless the user requested changes.

For new slides, define audience, slide dimensions, narrative, hierarchy, palette, and a consistent grid. Use editable text, semantic charts, and actual data. Check font availability and contrast. Speaker notes and source attribution belong in an appropriate user-facing artifact when useful.

Current API: https://python-pptx.readthedocs.io/en/latest/user/quickstart.html

Minimal creation with an available dependency:

```python
from pptx import Presentation
presentation = Presentation()
slide = presentation.slides.add_slide(presentation.slide_layouts[0])
slide.shapes.title.text = "Report"
slide.placeholders[1].text = "Requested content"
presentation.save("output.pptx")
```

Run `python3 ../office-common/package-check.py output.pptx` from this skill directory. Then render through an available presentation engine and inspect every slide. The ZIP/XML check is not a renderer and cannot prove layout, accessibility, chart correctness, or animation fidelity. Record missing checks instead of reporting a pass.
