#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
mkdir -p "$ROOT/.tmp"
HIGGSFIELD_TEST_ROOT="$ROOT" python3 - <<'PY'
"""Exercise packaged helpers with local fixtures; no auth, network, or paid jobs."""
import ast
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

root = Path(os.environ["HIGGSFIELD_TEST_ROOT"])
skills = root / "system-configs/.agents/skills"
bundles = sorted(skills.glob("higgsfield-*"))
assert len(bundles) == 8
for bundle in bundles:
    license_text = (bundle / "LICENSE.txt").read_text()
    assert "Copyright (c) 2026 Higgsfield AI" in license_text
    assert "THE SOFTWARE IS PROVIDED \"AS IS\"" in license_text
    for helper in bundle.rglob("*.py"):
        ast.parse(helper.read_text(), filename=str(helper))

brandkit = skills / "higgsfield-brandkit/scripts/brandkit.py"
inspector = skills / "higgsfield-websites/scripts/glb_inspect.py"
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("brandkit_helpers", brandkit)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
with tempfile.TemporaryDirectory(prefix="higgsfield-local-", dir=root / ".tmp") as tmp:
    work = Path(tmp)
    state = work / "state.json"

    # A logo touching all four viewBox edges is not necessarily a background.
    for path_data in (
        "M0 50 L50 0 L100 50 L50 100 Z",  # diamond
        "M0 0 L100 100 L100 0 L0 100 Z",  # crossing diagonals
        "M0 0 H100 V100 H0 Z M25 25 H75 V75 H25 Z",  # compound path
    ):
        svg = f'<svg viewBox="0 0 100 100"><path d="{path_data}" fill="#123456"/></svg>'
        assert helper.strip_full_canvas_background(svg) == (svg, False), path_data
    for shape in (
        '<path d="M0 0 H100 V100 H0 Z" fill="#123456"/>',
        '<path d="m0 0 h100 v100 h-100 z" fill="#123456"/>',
        '<rect width="100" height="100" fill="#123456"/>',
    ):
        stripped, removed = helper.strip_full_canvas_background(f'<svg viewBox="0 0 100 100">{shape}</svg>')
        assert removed and 'fill="none"' in stripped, shape

    # Stylesheet paints must fail before any variant files/directories appear.
    styled_svg = '<svg viewBox="0 0 100 100"><style>.mark{fill:#123456}</style><path class="mark" d="M10 50 L50 10 L90 50 L50 90 Z"/></svg>'
    try:
        helper.monochrome_svg(styled_svg, "#ffffff")
    except RuntimeError as error:
        assert "stylesheet" in str(error).lower(), error
    else:
        raise AssertionError("Stylesheet recoloring was silently accepted")
    for index, options in enumerate((
        {"include_monochrome": True},
        {"single_color": "#ffffff"},
        {"replacements": [{"from": "#123456", "to": "#ffffff"}]},
    )):
        logo_input = work / f"stylesheet-{index}.json"
        logo_input.write_text(json.dumps({"logo_svg": styled_svg, **options}))
        export_dir = work / f"stylesheet-export-{index}"
        result = subprocess.run([sys.executable, str(brandkit), "logo-export", "--input", str(logo_input), "--output-dir", str(export_dir)], text=True, capture_output=True)
        assert result.returncode != 0 and "stylesheet" in result.stderr.lower(), result.stderr
        assert not export_dir.exists(), "Rejected SVG wrote partial export artifacts"
    inline_svg = '<svg viewBox="0 0 100 100"><path d="M10 50 L50 10 L90 50 Z" style="fill:#123456;stroke:#654321"/></svg>'
    mono, changed = helper.monochrome_svg(inline_svg, "#ffffff")
    assert changed == 2 and "#123456" not in mono and "#654321" not in mono

    # Embedding a selected SVG must retain inherited root presentation.
    inherited_svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" fill="#123456" stroke="#654321" stroke-width="2"><path d="M10 50 L50 10 L90 50 Z"/></svg>'
    embedded = ET.fromstring(helper.logo_markup(inherited_svg))
    for name, value in (("fill", "#123456"), ("stroke", "#654321"), ("stroke-width", "2")):
        assert embedded.attrib[name] == value, embedded.attrib

    # Preview CSS must request and render the selected style/weight, not defaults.
    local_font = work / "fixture-font.woff2"
    local_font.write_bytes(b"fixture; CSS routing only, not font-render validation")
    display_font = {"family": "Example Serif", "source": "https://example.test/italic.woff2", "weight": 300, "style": "italic"}
    for source in (display_font["source"], str(local_font)):
        css, _ = helper.font_css({**display_font, "source": source}, "Arial")
        assert "font-style:italic" in css and "font-weight:300" in css, css
    google_css, _ = helper.font_css({**display_font, "source": "google:Example Serif"}, "Arial")
    assert ":ital,wght@1,300" in google_css, google_css
    review_html = helper.build_review_html({
        "stage": "typography", "name": "Selected pair", "premise": "Actual selected styles",
        "background_color": "#ffffff", "text_color": "#111111",
        "display_font": display_font,
        "body_font": {"family": "Example Sans", "source": str(local_font), "weight": 500, "style": "normal"},
        "headline": "Headline", "body": "Body specimen",
    })
    assert 'font:italic 300 52px/1.05 "Example Serif"' in review_html
    assert 'font:normal 500 18px/1.4 "Example Sans"' in review_html
    for invalid in ({"style": "oblique"}, {"weight": 1000}):
        try:
            helper.font_css({**display_font, **invalid}, "Arial")
        except RuntimeError:
            pass
        else:
            raise AssertionError(f"Unsupported preview font accepted: {invalid}")

    def state_action(action, payload=None, expect_success=True):
        command = [sys.executable, str(brandkit), "state", "--state-file", str(state), "--action", action]
        if payload is not None:
            source = work / "input.json"
            source.write_text(json.dumps(payload))
            command.extend(["--input", str(source)])
        result = subprocess.run(command, text=True, capture_output=True, cwd=work)
        if expect_success:
            assert result.returncode == 0, result.stderr
            return json.loads(result.stdout)
        assert result.returncode != 0, result.stdout
        return result

    # A read of an empty project must not create approval state.
    state_action("get_status")
    assert not state.exists()
    palette = {
        "approval_summary": "Fixture user approved this palette.",
        "palette": {"colors": [
            {"hex": "#102030", "name": "Ink"},
            {"hex": "#f0f0f0", "name": "Paper"},
        ]},
    }
    saved = state_action("approve_palette", palette)
    assert saved["revision"] == 1
    state_action("approve_brandbook_element", {
        "approval_summary": "Fixture user approved the palette board.",
        "required_slots": ["palette"],
        "brandbook_element": {
            "key": "palette-board", "kind": "board", "name": "Palette board",
            "asset": {"path": str(work / "board.html")},
        },
    })
    palette["palette"]["colors"][0]["hex"] = "#203040"
    changed = state_action("approve_palette", palette)
    assert changed["revision"] == 2
    assert changed["invalidated_brandbook_elements"] == ["palette-board"]
    assert state_action("list_brandbook_elements")["elements"] == []
    before = state.read_bytes()
    state_action("approve_palette", {"palette": {"colors": []}}, expect_success=False)
    assert state.read_bytes() == before, "Rejected input mutated approval state"

    # Verify the GLB inspector detects a broken root-scale animation without
    # needing Blender, a GPU, model downloads, or a Higgsfield workspace.
    fixture = {
        "asset": {"version": "2.0"},
        "nodes": [{"name": "Hips"}],
        "skins": [{"joints": [0]}],
        "accessors": [{"min": [1, 1, 1], "max": [1, 1, 1]}],
        "animations": [{"name": "Walk", "samplers": [{"output": 0}],
                        "channels": [{"sampler": 0, "target": {"node": 0, "path": "scale"}}]}],
    }

    def inspect():
        payload = json.dumps(fixture).encode()
        payload += b" " * (-len(payload) % 4)
        model = work / "fixture.glb"
        model.write_bytes(struct.pack("<III", 0x46546C67, 2, 20 + len(payload))
                          + struct.pack("<II", len(payload), 0x4E4F534A) + payload)
        return subprocess.run([sys.executable, str(inspector), str(model)], text=True, capture_output=True)

    valid = inspect()
    assert valid.returncode == 0, valid.stderr
    fixture["accessors"][0]["max"] = [1.176, 1.176, 1.176]
    broken = inspect()
    assert broken.returncode == 2, broken.stdout
    assert "Meshy baked-scale bug" in broken.stdout

print("Higgsfield ports: 8 bundles and 14 Python helpers checked; local state, SVG, font CSS, and GLB behavior passed.")
PY
