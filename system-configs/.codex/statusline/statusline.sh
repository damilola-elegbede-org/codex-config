#!/bin/sh
# A companion footer: Codex itself does not execute status-line scripts.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
# tmux servers may have an old PATH. Prefer the macOS package-manager Python.
if [ -x /opt/homebrew/bin/python3 ]; then
    exec /opt/homebrew/bin/python3 -B "$ROOT/statusline.py" "$@"
fi
exec python3 -B "$ROOT/statusline.py" "$@"
