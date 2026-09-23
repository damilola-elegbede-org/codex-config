#!/bin/sh
# validate_one() writes codex's stderr to a mktemp file and returns from four
# places; sh has no per-function trap. sync.sh runs validate.sh twice per run
# and validate.sh runs validate_one once per profile, so a leaked temp file
# compounds on every sync.
#
# macOS mktemp(1) ignores TMPDIR unless -t is given, so pinning TMPDIR proves
# nothing here (verified: the file still lands in /var/folders). Instead a
# mktemp shim on PATH routes every temp file into a directory we own and
# can count afterwards.
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT HUP INT TERM
mkdir -p "$WORK/bin" "$WORK/home" "$WORK/tmp"

printf '%s\n' '#!/bin/sh' \
  'echo "Model provider __nonexistent__ not found" >&2' \
  'exit 1' > "$WORK/bin/codex"
printf '%s\n' '#!/bin/sh' \
  'exec /usr/bin/mktemp "$LEAK_DIR/leak.XXXXXX"' > "$WORK/bin/mktemp"
chmod +x "$WORK/bin/codex" "$WORK/bin/mktemp"

# Base config plus two profiles: three validate_one calls, three temp files.
printf '%s\n' 'model = "test"' > "$WORK/home/config.toml"
printf '%s\n' 'model = "test"' > "$WORK/home/think.config.toml"
printf '%s\n' 'model = "test"' > "$WORK/home/code.config.toml"

LEAK_DIR="$WORK/tmp" PATH="$WORK/bin:$PATH" "$ROOT/scripts/validate.sh" "$WORK/home" >/dev/null

# Positive control: the shim must actually have been used, or an empty
# directory proves nothing. validate.sh calls mktemp once per validate_one,
# and each call leaves a file only if the script forgot to remove it -- so
# prove the shim by calling it once ourselves.
probe=$(LEAK_DIR="$WORK/tmp" PATH="$WORK/bin:$PATH" mktemp)
case "$probe" in
    "$WORK/tmp"/leak.*) rm -f "$probe" ;;
    *) echo "mktemp shim not on PATH (got $probe); test cannot see leaks" >&2; exit 1 ;;
esac

leaked=$(find "$WORK/tmp" -mindepth 1 | wc -l | tr -d ' ')
if [ "$leaked" -ne 0 ]; then
    echo "validate.sh leaked $leaked temp file(s):" >&2
    find "$WORK/tmp" -mindepth 1 >&2
    exit 1
fi
echo "PASS test-validate-leak"
