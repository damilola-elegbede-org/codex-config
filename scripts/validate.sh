#!/bin/sh
# Validate a staged CODEX_HOME without contacting a model provider.
set -eu

CODEX_HOME=${1:-${CODEX_HOME:-}}
if [ -z "$CODEX_HOME" ] || [ ! -d "$CODEX_HOME" ]; then
    echo "usage: $0 <CODEX_HOME>" >&2
    exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 is required for TOML validation" >&2
    exit 1
fi
if ! command -v codex >/dev/null 2>&1; then
    echo "codex is required for strict configuration validation" >&2
    exit 1
fi

files="$CODEX_HOME/config.toml"
for profile in "$CODEX_HOME"/*.config.toml; do
    [ -e "$profile" ] || continue
    files="$files
$profile"
done

# tomllib gives deterministic file:line diagnostics for malformed TOML before
# asking Codex to reject unknown fields.
if ! VALIDATE_FILES="$files" python3 - <<'PY'
import os
import tomllib

for path in os.environ["VALIDATE_FILES"].splitlines():
    if not os.path.exists(path):
        continue
    try:
        with open(path, "rb") as source:
            tomllib.load(source)
    except tomllib.TOMLDecodeError as error:
        print(f"{path}:{error.lineno}: {error}")
        raise SystemExit(1)
PY
then
    exit 1
fi

validate_one() {
    profile=$1
    error_file=$(mktemp)
    if [ -n "$profile" ]; then
        CODEX_HOME="$CODEX_HOME" codex exec --strict-config --skip-git-repo-check -s read-only \
            -c 'model_provider="__nonexistent__"' -p "$profile" x </dev/null >/dev/null 2>"$error_file" || rc=$?
    else
        CODEX_HOME="$CODEX_HOME" codex exec --strict-config --skip-git-repo-check -s read-only \
            -c 'model_provider="__nonexistent__"' x </dev/null >/dev/null 2>"$error_file" || rc=$?
    fi
    rc=${rc:-0}
    error=$(cat "$error_file")
    # Read once, then drop it: the function returns from four places below
    # and sh has no per-function trap, so removing it here is the only spot
    # that covers every exit. sync.sh calls validate.sh twice per run and
    # validate.sh calls this once per profile, so a leak compounds fast.
    rm -f "$error_file"

    # The fake provider is intentionally invalid: reaching it proves strict
    # parsing completed without a token request.
    if printf '%s\n' "$error" | grep -Eq 'Model provider .* not found'; then
        return 0
    fi

    field=$(printf '%s\n' "$error" | sed -n "s/.*unknown configuration field ['\`\"]\([^'\`\"]*\).*/\1/p" | head -n 1)
    if [ -n "$field" ]; then
        old_ifs=$IFS
        IFS='
'
        for file in $files; do
            IFS=$old_ifs
            line=$(grep -n "^[[:space:]]*$field[[:space:]]*=" "$file" 2>/dev/null | head -n 1 || true)
            if [ -n "$line" ]; then
                printf '%s:%s: %s\n' "$file" "${line%%:*}" "$error" >&2
                return 1
            fi
        done
        IFS=$old_ifs
    fi
    if [ -n "$profile" ]; then
        printf '%s/%s.config.toml:1: %s\n' "$CODEX_HOME" "$profile" "$error" >&2
    else
        printf '%s/config.toml:1: %s\n' "$CODEX_HOME" "$error" >&2
    fi
    return 1
}

validate_one ""
for profile_path in "$CODEX_HOME"/*.config.toml; do
    [ -e "$profile_path" ] || continue
    profile=$(basename "$profile_path" .config.toml)
    validate_one "$profile"
done

echo "validated $CODEX_HOME"
