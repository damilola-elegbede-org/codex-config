#!/bin/sh
# Exercise the detected Mini against the actual shipped configuration.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT HUP INT TERM
mkdir -p "$WORK/bin" "$WORK/live" "$WORK/home"
printf '%s\n' '#!/bin/sh' 'echo damilola-mbm' > "$WORK/bin/scutil"
printf '%s\n' '#!/bin/sh' 'echo "Model provider __nonexistent__ not found" >&2' 'exit 1' > "$WORK/bin/codex"
chmod +x "$WORK/bin/scutil" "$WORK/bin/codex"
printf '%s\n' '#!/bin/sh' 'if [ "$1" = --version ]; then echo v22.0.0; fi' > "$WORK/bin/node"
cat > "$WORK/bin/npm" <<'PY'
#!/usr/bin/env python3
import json
from pathlib import Path
root = Path.cwd()
version = json.loads((root / 'package.json').read_text())['dependencies']['ai']
(root / 'node_modules/ai').mkdir(parents=True)
(root / 'node_modules/ai/package.json').write_text(json.dumps({'version': version}))
PY
chmod +x "$WORK/bin/node" "$WORK/bin/npm"
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
PATH="$WORK/bin:$PATH" HOME="$WORK/home" CODEX_HOME="$WORK/live" CODEX_SKILLS_HOME="$WORK/home/.agents/skills" \
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
for theme in (source / "themes").glob("*.tmTheme"):
    assert (target / "themes" / theme.name).read_bytes() == theme.read_bytes(), theme.name
assert (target / "AGENTS.md").read_bytes() == (source / "AGENTS.md").read_bytes()
assert (target / "custom.config.toml").read_text() == 'model = "custom"\n'
assert (target / "auth.json").read_text() == 'test-auth-state\n'
assert (target / "hooks.json").read_bytes() == (source / "hooks.json").read_bytes()
assert (target / ".codex-config-managed-hooks.json").is_file()
print("PASS: detected Mini syncs all shipped settings and profiles, preserving local state")
PY
