#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
python3 - "$ROOT/system-configs/.codex/config.toml" <<'PY'
import sys
import tomllib

with open(sys.argv[1], "rb") as source:
    config = tomllib.load(source)

# Keep identity fields and the version immediately before the remaining-context and quota fields.
assert config["tui"]["status_line"] == [
    "thread-name", "model-with-reasoning", "git-branch", "current-dir",
    "codex-version", "context-remaining", "weekly-limit", "five-hour-limit",
]
assert config["tui"]["status_line_use_colors"] is True
assert config["tui"]["theme"] == "monokai-extended-origin"
assert config["model"] == "gpt-6.1-sol"
assert config["model_reasoning_effort"] == "medium"
print("PASS: native status fields, order, colors, and default model")
PY
