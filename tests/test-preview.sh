#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
if ! command -v tmux >/dev/null 2>&1; then
    echo 'SKIP: tmux integration (not installed)'
    exit 0
fi
TEMP=$(mktemp -d)
SERVER="codex-config-test-$$"
trap 'tmux -L "$SERVER" kill-server 2>/dev/null || true; rm -rf "$TEMP"' EXIT HUP INT TERM
tmux -L "$SERVER" -f /dev/null new-session -d -s preview 'sleep 120'
SOCKET=$(tmux -L "$SERVER" display-message -p '#{socket_path}')
export TMUX="$SOCKET,0,0" CODEX_HOME="$TEMP" PYTHONDONTWRITEBYTECODE=1
preview() { python3 -B "$ROOT/system-configs/.codex/statusline/preview.py" "$1" --pane %0; }
tmux show-options -t preview > "$TEMP/before"
before_row=$(tmux show-options -Av -t preview 'status-format[0]')
preview install
[ "$(tmux show-options -v -t preview status)" = 2 ]
[ "$(tmux show-options -v -t preview 'status-format[0]')" = "$before_row" ]
tmux show-options -v -t preview 'status-format[1]' | grep -q 'statusline.sh'
preview install
[ "$(tmux show-options -v -t preview status)" = 2 ]
preview restore
tmux show-options -t preview > "$TEMP/after"
diff -u "$TEMP/before" "$TEMP/after"
# A custom second row survives append+restore as well.
tmux set-option -t preview status 2
tmux set-option -t preview 'status-format[1]' 'my existing row'
tmux show-options -t preview > "$TEMP/before"
preview install
[ "$(tmux show-options -v -t preview status)" = 3 ]
preview restore
tmux show-options -t preview > "$TEMP/after"
diff -u "$TEMP/before" "$TEMP/after"
# A new server at the same socket must not reuse stale preview state.
preview install
tmux -L "$SERVER" kill-server
tmux -L "$SERVER" -f /dev/null new-session -d -s preview 'sleep 120'
preview install
[ "$(tmux show-options -v -t preview status)" = 2 ]
preview restore
echo 'PASS: tmux preview appends, restores options, and survives server restarts'
