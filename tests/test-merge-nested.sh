#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
python3 - "$ROOT" <<'PY'
import pathlib
import subprocess
import sys
import tempfile
import tomllib

root = pathlib.Path(sys.argv[1])
with tempfile.TemporaryDirectory() as directory:
    work = pathlib.Path(directory)
    source = work / "source.toml"
    source.write_text('[tui]\nstatus_line = ["context-used"]\n')
    for key in ['"foo=bar"', "'foo=bar'", '"foo\\\"=bar"']:
        destination = work / "destination.toml"
        destination.write_text(
            f'tui.{key}.old = "value=kept"\n'
            'tui.model_availability_nux = { old = 1, nested = { yes = true } }\n'
            'tui.status_line = ["old"]\n'
            '[profiles.custom]\ntui.status_line = ["local"]\n'
        )
        before = tomllib.loads(destination.read_text())
        subprocess.run([sys.executable, str(root / "scripts/merge-config.py"),
                        str(source), str(destination), "tui"], check=True)
        after = tomllib.loads(destination.read_text())
        assert after["tui"]["status_line"] == ["context-used"]
        for name, value in before["tui"].items():
            if name != "status_line":
                assert after["tui"][name] == value
        assert after["profiles"] == before["profiles"]
print("PASS: quoted equals keys and nested inline TUI tables survive merge")
PY
