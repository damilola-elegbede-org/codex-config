#!/bin/sh
# Exercise the detected Mini against the actual shipped configuration.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT HUP INT TERM
mkdir -p "$WORK/bin" "$WORK/live"
printf '%s\n' '#!/bin/sh' 'echo damilola-mbm' > "$WORK/bin/scutil"
printf '%s\n' '#!/bin/sh' 'echo "Model provider __nonexistent__ not found" >&2' 'exit 1' > "$WORK/bin/codex"
chmod +x "$WORK/bin/scutil" "$WORK/bin/codex"
cat > "$WORK/live/config.toml" <<'TOML'
model = "old"
approval_policy = "on-request"
sandbox_mode = "workspace-write"
[projects."/private/project"]
trust_level = "trusted"
[notice.model_migrations]
old = "new"
[tui]
status_line = ["old-status"]
[tui.model_availability_nux]
old = 1
TOML
printf '%s\n' 'model = "custom"' > "$WORK/live/custom.config.toml"
printf '%s\n' 'test-auth-state' > "$WORK/live/auth.json"
unset CODEX_CONFIG_STATION CODEX_CONFIG_SOURCE
PATH="$WORK/bin:$PATH" CODEX_HOME="$WORK/live" \
  "$ROOT/scripts/sync.sh" --force --no-backup > "$WORK/sync.out"
python3 - "$ROOT/system-configs/.codex" "$WORK/live" <<'PY'
import pathlib
import sys
import tomllib

source, target = map(pathlib.Path, sys.argv[1:])
expected = tomllib.loads((source / "config.toml").read_text())
actual = tomllib.loads((target / "config.toml").read_text())
for key, value in expected.items():
    if key == "tui":
        for name, setting in value.items():
            assert actual["tui"].get(name) == setting, name
    else:
        assert actual.get(key) == value, key
assert actual["projects"] == {"/private/project": {"trust_level": "trusted"}}
assert actual["notice"]["model_migrations"] == {"old": "new"}
assert actual["tui"]["model_availability_nux"] == {"old": 1}
for profile in source.glob("*.config.toml"):
    assert (target / profile.name).read_bytes() == profile.read_bytes(), profile.name
assert (target / "custom.config.toml").read_text() == 'model = "custom"\n'
assert (target / "auth.json").read_text() == 'test-auth-state\n'
print("PASS: detected Mini syncs all shipped settings and profiles, preserving local state")
PY
