#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT HUP INT TERM
HOME="$WORK/home"
LIVE="$WORK/live"
SOURCE="$WORK/source/.codex"
mkdir -p "$HOME" "$LIVE" "$SOURCE" "$WORK/bin"

printf '%s\n' '#!/bin/sh' \
  'if grep -R "^bad_key" "$CODEX_HOME" >/dev/null 2>&1; then' \
  '  echo "unknown configuration field '\''bad_key'\''" >&2; exit 1' \
  'fi' \
  'echo "Model provider __nonexistent__ not found" >&2' \
  'exit 1' > "$WORK/bin/codex"
chmod +x "$WORK/bin/codex"
printf '%s\n' \
  'model = "new"' \
  'model_reasoning_effort = "high"' \
  'web_search = "live"' \
  'approval_policy = "never"' \
  'sandbox_mode = "danger-full-access"' \
  '' \
  '[tui]' \
  'status_line = ["thread-name", "model-with-reasoning", "current-dir", "context-used", "task-progress"]' > "$SOURCE/config.toml"
printf '%s\n' 'model = "profile-new"' > "$SOURCE/think.config.toml"
printf '%s\n' \
  'model = "old"' \
  'model_reasoning_effort = "low"' \
  'web_search = "cached"' \
  'approval_policy = "on-request"' \
  'sandbox_mode = "workspace-write"' \
  '' \
  '[projects."/private/project"]' \
  'trust_level = "trusted"' \
  '' \
  '[notice.model_migrations]' \
  'old = "new"' \
  '' \
  '[tui]' \
  'status_line = ["old-status"]' \
  '' \
  '[tui.model_availability_nux]' \
  'old = 1' > "$LIVE/config.toml"
printf '%s\n' 'model = "unknown"' > "$LIVE/custom.config.toml"
printf '%s\n' 'secret' > "$LIVE/auth.json"
mkdir -p "$LIVE/sessions"
printf '%s\n' 'state' > "$LIVE/sessions/x"

PATH="$WORK/bin:$PATH" HOME="$HOME" CODEX_HOME="$LIVE" CODEX_CONFIG_SOURCE="$SOURCE" \
  CODEX_CONFIG_STATION=test-no-manifest "$ROOT/scripts/sync.sh" --force >"$WORK/sync.out"
grep -q 'model = "new"' "$LIVE/config.toml"
grep -q 'approval_policy = "never"' "$LIVE/config.toml"
grep -q 'sandbox_mode = "danger-full-access"' "$LIVE/config.toml"
grep -q 'status_line = \["thread-name", "model-with-reasoning", "current-dir", "context-used", "task-progress"\]' "$LIVE/config.toml"
grep -q '\[projects."/private/project"\]' "$LIVE/config.toml"
grep -q '\[notice.model_migrations\]' "$LIVE/config.toml"
grep -q '\[tui.model_availability_nux\]' "$LIVE/config.toml"
python3 - "$LIVE/config.toml" <<'PY'
import sys
import tomllib

with open(sys.argv[1], "rb") as source:
    config = tomllib.load(source)
assert config["approval_policy"] == "never"
assert config["sandbox_mode"] == "danger-full-access"
assert config["tui"]["status_line"] == [
    "thread-name",
    "model-with-reasoning",
    "current-dir",
    "context-used",
    "task-progress",
]
assert config["tui"]["model_availability_nux"] == {"old": 1}
PY
grep -q 'model = "unknown"' "$LIVE/custom.config.toml"
backup=$(find "$HOME" -maxdepth 1 -type d -name '.codex-config.backup.*' -print | head -n 1)
[ -f "$backup/config.toml" ]
[ ! -e "$backup/auth.json" ]
[ ! -e "$backup/sessions" ]

before=$(cksum "$LIVE/config.toml")
PATH="$WORK/bin:$PATH" HOME="$HOME" CODEX_HOME="$LIVE" CODEX_CONFIG_SOURCE="$SOURCE" \
  CODEX_CONFIG_STATION=test-no-manifest "$ROOT/scripts/sync.sh" --force --dry-run >"$WORK/dry.out"
after=$(cksum "$LIVE/config.toml")
[ "$before" = "$after" ]
grep -q 'dry-run: validated staging; no files were written' "$WORK/dry.out"

printf '%s\n' 'model = "newer"' > "$SOURCE/config.toml"
PATH="$WORK/bin:$PATH" HOME="$HOME" CODEX_HOME="$LIVE" CODEX_CONFIG_SOURCE="$SOURCE" \
  CODEX_CONFIG_STATION=test-no-manifest "$ROOT/scripts/sync.sh" --force --no-backup >"$WORK/drop.out"
grep -q 'model = "newer"' "$LIVE/config.toml"
if grep -q '^web_search[[:space:]]*=' "$LIVE/config.toml"; then
    echo "dropped owned key survived" >&2
    exit 1
fi

printf '%s\n' 'bad_key = true' > "$SOURCE/config.toml"
before=$(cksum "$LIVE/config.toml")
if PATH="$WORK/bin:$PATH" HOME="$HOME" CODEX_HOME="$LIVE" CODEX_CONFIG_SOURCE="$SOURCE" \
  CODEX_CONFIG_STATION=test-no-manifest "$ROOT/scripts/sync.sh" --force >"$WORK/bad.out" 2>&1; then
    echo "invalid staged config unexpectedly installed" >&2
    exit 1
fi
[ "$(cksum "$LIVE/config.toml")" = "$before" ]
grep -q 'staging validation failed' "$WORK/bad.out"

printf '%s\n' \
  'model = "newer"' \
  'model_reasoning_effort = "high"' \
  'web_search = "live"' \
  'approval_policy = "never"' \
  'sandbox_mode = "danger-full-access"' \
  '' \
  '[tui]' \
  'status_line = ["thread-name", "model-with-reasoning", "current-dir", "context-used", "task-progress"]' > "$SOURCE/config.toml"
mkdir -p "$WORK/mini"
printf '%s\n' \
  'model = "old"' \
  'model_reasoning_effort = "low"' \
  'web_search = "cached"' \
  'approval_policy = "on-request"' \
  'sandbox_mode = "workspace-write"' \
  '' \
  '[tui]' \
  'status_line = ["mini-status"]' > "$WORK/mini/config.toml"
PATH="$WORK/bin:$PATH" HOME="$HOME" CODEX_HOME="$WORK/mini" CODEX_CONFIG_SOURCE="$SOURCE" \
  CODEX_CONFIG_STATION=damilola-mbm "$ROOT/scripts/sync.sh" --force --no-backup >"$WORK/mini.out"
grep -q 'model = "newer"' "$WORK/mini/config.toml"
grep -q 'approval_policy = "on-request"' "$WORK/mini/config.toml"
grep -q 'sandbox_mode = "workspace-write"' "$WORK/mini/config.toml"
grep -q 'status_line = \["mini-status"\]' "$WORK/mini/config.toml"

mkdir -p "$WORK/alternate-header"
printf '%s\n' \
  'model = "old"' \
  'model_reasoning_effort = "low"' \
  'web_search = "cached"' \
  'approval_policy = "on-request"' \
  'sandbox_mode = "workspace-write"' \
  '' \
  '[ tui ] # local status-line settings' \
  'status_line = ["old-status"]' \
  '' \
  '[tui.model_availability_nux]' \
  'old = 1' > "$WORK/alternate-header/config.toml"
PATH="$WORK/bin:$PATH" HOME="$HOME" CODEX_HOME="$WORK/alternate-header" CODEX_CONFIG_SOURCE="$SOURCE" \
  CODEX_CONFIG_STATION=test-no-manifest "$ROOT/scripts/sync.sh" --force --no-backup >"$WORK/alternate-header.out"
python3 - "$WORK/alternate-header/config.toml" <<'PY'
import sys
import tomllib

with open(sys.argv[1], "rb") as source:
    config = tomllib.load(source)
assert config["tui"]["status_line"] == [
    "thread-name",
    "model-with-reasoning",
    "current-dir",
    "context-used",
    "task-progress",
]
assert config["tui"]["model_availability_nux"] == {"old": 1}
PY

mkdir -p "$WORK/quoted-header"
printf '%s\n' \
  'model = "old"' \
  'model_reasoning_effort = "low"' \
  'web_search = "cached"' \
  'approval_policy = "on-request"' \
  'sandbox_mode = "workspace-write"' \
  '' \
  '["tui"] # local status-line settings' \
  'status_line = ["old-status"]' \
  '' \
  '[tui.model_availability_nux]' \
  'old = 1' > "$WORK/quoted-header/config.toml"
PATH="$WORK/bin:$PATH" HOME="$HOME" CODEX_HOME="$WORK/quoted-header" CODEX_CONFIG_SOURCE="$SOURCE" \
  CODEX_CONFIG_STATION=test-no-manifest "$ROOT/scripts/sync.sh" --force --no-backup >"$WORK/quoted-header.out"
python3 - "$WORK/quoted-header/config.toml" <<'PY'
import sys
import tomllib

with open(sys.argv[1], "rb") as source:
    config = tomllib.load(source)
assert config["tui"]["status_line"] == [
    "thread-name",
    "model-with-reasoning",
    "current-dir",
    "context-used",
    "task-progress",
]
assert config["tui"]["model_availability_nux"] == {"old": 1}
PY

mkdir -p "$WORK/dotted-tui"
printf '%s\n' \
  'model = "old"' \
  'tui.status_line = ["old-status"]' \
  'web_search = "cached"' > "$WORK/dotted-tui/config.toml"
PATH="$WORK/bin:$PATH" HOME="$HOME" CODEX_HOME="$WORK/dotted-tui" CODEX_CONFIG_SOURCE="$SOURCE" \
  CODEX_CONFIG_STATION=test-no-manifest "$ROOT/scripts/sync.sh" --force --no-backup >"$WORK/dotted-tui.out"
python3 - "$WORK/dotted-tui/config.toml" <<'PY'
import sys
import tomllib

with open(sys.argv[1], "rb") as source:
    config = tomllib.load(source)
assert config["tui"]["status_line"] == [
    "thread-name",
    "model-with-reasoning",
    "current-dir",
    "context-used",
    "task-progress",
]
assert config["web_search"] == "live"
PY

mkdir -p "$WORK/multiline-dotted-tui"
printf '%s\n' \
  'model = "old"' \
  'tui.status_line = [' \
  '  "old-status",' \
  '  ["nested-old"],' \
  ']' \
  'note = """keep' \
  'tui.status_line = ["literal assignment text"]' \
  '[tui]' \
  '"""' \
  'web_search = "cached"' > "$WORK/multiline-dotted-tui/config.toml"
PATH="$WORK/bin:$PATH" HOME="$HOME" CODEX_HOME="$WORK/multiline-dotted-tui" CODEX_CONFIG_SOURCE="$SOURCE" \
  CODEX_CONFIG_STATION=test-no-manifest "$ROOT/scripts/sync.sh" --force --no-backup >"$WORK/multiline-dotted-tui.out"
python3 -c 'import sys, tomllib; tomllib.load(open(sys.argv[1], "rb"))' \
  "$WORK/multiline-dotted-tui/config.toml"
python3 - "$WORK/multiline-dotted-tui/config.toml" <<'PY'
import sys
import tomllib

with open(sys.argv[1], "rb") as source:
    config = tomllib.load(source)
assert config["tui"]["status_line"] == [
    "thread-name",
    "model-with-reasoning",
    "current-dir",
    "context-used",
    "task-progress",
]
assert config["note"] == 'keep\ntui.status_line = ["literal assignment text"]\n[tui]\n'
assert config["web_search"] == "live"
PY
if grep -q '^  "old-status",$' "$WORK/multiline-dotted-tui/config.toml"; then
    echo "orphaned dotted-array continuation survived" >&2
    exit 1
fi

printf '%s\n' \
  'model = "newer"' \
  'model_reasoning_effort = "high"' > "$SOURCE/config.toml"
[ -f "$LIVE/think.config.toml" ] || { echo "expected think.config.toml before removal test" >&2; exit 1; }
rm -f "$SOURCE/think.config.toml"
PATH="$WORK/bin:$PATH" HOME="$HOME" CODEX_HOME="$LIVE" CODEX_CONFIG_SOURCE="$SOURCE" \
  CODEX_CONFIG_STATION=test-no-manifest "$ROOT/scripts/sync.sh" --force >"$WORK/remove.out"
if [ -e "$LIVE/think.config.toml" ]; then
    echo "stale profile think.config.toml was not removed after deletion from source" >&2
    exit 1
fi
grep -q 'model = "unknown"' "$LIVE/custom.config.toml"
found_backup=0
for b in "$HOME"/.codex-config.backup.*; do
    [ -d "$b" ] || continue
    [ -f "$b/think.config.toml" ] && found_backup=1
done
[ "$found_backup" -eq 1 ] || { echo "no backup captured the removed think.config.toml" >&2; exit 1; }
echo "PASS test-sync"
