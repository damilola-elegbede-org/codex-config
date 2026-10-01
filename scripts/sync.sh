#!/bin/sh
# Stage, strictly validate, then atomically install only repository-owned files.
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SOURCE_CODEX=${CODEX_CONFIG_SOURCE:-"$ROOT/system-configs/.codex"}
TARGET_CODEX=${CODEX_HOME:-"$HOME/.codex"}
DRY_RUN=false
CREATE_BACKUP=true
FORCE=false

usage() { echo "usage: $0 [--dry-run] [--no-backup] [--force]" >&2; }
while [ $# -gt 0 ]; do
    case "$1" in
        --dry-run) DRY_RUN=true ;;
        --no-backup) CREATE_BACKUP=false ;;
        --force) FORCE=true ;;
        *) usage; exit 1 ;;
    esac
    shift
done
die_preflight() { echo "pre-flight: $*" >&2; exit 1; }
if ! command -v codex >/dev/null 2>&1; then die_preflight "codex is required"; fi
if ! python3 -c 'import tomllib' >/dev/null 2>&1; then die_preflight "python3 with tomllib is required"; fi
if [ ! -f "$SOURCE_CODEX/config.toml" ]; then die_preflight "missing $SOURCE_CODEX/config.toml"; fi

if [ -n "${CODEX_CONFIG_STATION:-}" ]; then
    STATION=$CODEX_CONFIG_STATION
    EXPLICIT_STATION=true
else
    STATION=$(scutil --get LocalHostName 2>/dev/null || hostname -s)
    EXPLICIT_STATION=false
fi
MANIFEST="$ROOT/sync-manifests/$STATION.json"
if [ -f "$MANIFEST" ] && ! python3 -c 'import json,sys; json.load(open(sys.argv[1]))' "$MANIFEST" >/dev/null 2>&1; then
    die_preflight "invalid manifest: $MANIFEST"
fi
manifest_value() {
    key=$1 fallback=$2
    if [ ! -f "$MANIFEST" ]; then printf '%s\n' "$fallback"; return; fi
    python3 - "$MANIFEST" "$key" "$fallback" <<'PY'
import json, sys
value = json.load(open(sys.argv[1]))["sync"].get(sys.argv[2], sys.argv[3])
if isinstance(value, bool):
    print(str(value).lower())
elif isinstance(value, list):
    print(" ".join(value))
else:
    print(value)
PY
}
CONFIG_MODE=$(manifest_value config merge)
ALL_OWNED_KEYS="model model_reasoning_effort web_search approval_policy sandbox_mode tui"
SAFE_OWNED_KEYS="model model_reasoning_effort web_search"
if [ -f "$MANIFEST" ] || [ "$EXPLICIT_STATION" = true ]; then
    OWNED_KEYS=$(manifest_value config_owned_keys "$ALL_OWNED_KEYS")
    DEFAULT_AGENTS_MD=true
else
    OWNED_KEYS=$SAFE_OWNED_KEYS
    DEFAULT_AGENTS_MD=false
fi
PROFILES=$(manifest_value profiles true)
AGENTS_MD=$(manifest_value agents_md "$DEFAULT_AGENTS_MD")
RULES=$(manifest_value rules false)
HOOKS=$(manifest_value hooks false)
case "$CONFIG_MODE" in merge) ;; *) die_preflight "config mode must be merge" ;; esac
case " $OWNED_KEYS " in
    *" projects "*|*" notice.model_migrations "*|*" tui.model_availability_nux "*) die_preflight "manifest attempts to own a never-owned Codex table" ;;
esac

# Local-ref check only: it never fetches or invokes a network Git operation.
if [ "$FORCE" = false ] && git -C "$ROOT" rev-parse --verify -q origin/main >/dev/null; then
    behind=$(git -C "$ROOT" rev-list --count HEAD..origin/main)
    [ "$behind" -eq 0 ] || die_preflight "checkout is $behind commit(s) behind origin/main; use --force deliberately"
elif [ "$FORCE" = false ]; then
    echo "warning: origin/main is unavailable; freshness could not be checked" >&2
fi

STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT HUP INT TERM
mkdir -p "$STAGE"
if [ -f "$TARGET_CODEX/config.toml" ]; then cp "$TARGET_CODEX/config.toml" "$STAGE/config.toml"; else : > "$STAGE/config.toml"; fi
if ! CODEX_CONFIG_ALLOWED_KEYS="$ALL_OWNED_KEYS" python3 "$ROOT/scripts/merge-config.py" "$SOURCE_CODEX/config.toml" "$STAGE/config.toml" $OWNED_KEYS; then
    echo "staging validation failed; live configuration was not changed" >&2
    exit 2
fi
stage_file() {
    source=$1 relative=$2
    [ -f "$source" ] || return 0
    mkdir -p "$(dirname "$STAGE/$relative")"
    cp "$source" "$STAGE/$relative"
}
MANAGED_PROFILES_FILE="$TARGET_CODEX/.codex-config-managed-profiles"
STALE_LIST="$STAGE/.stale-profiles"
: > "$STALE_LIST"
if [ "$PROFILES" = true ]; then
    for source in "$SOURCE_CODEX"/*.config.toml; do [ -e "$source" ] && stage_file "$source" "$(basename "$source")"; done
    for staged in "$STAGE"/*.config.toml; do [ -e "$staged" ] && basename "$staged"; done > "$STAGE/.codex-config-managed-profiles"
    if [ -f "$MANAGED_PROFILES_FILE" ]; then
        while IFS= read -r managed; do
            [ -n "$managed" ] || continue
            [ -e "$STAGE/$managed" ] || printf '%s\n' "$managed" >> "$STALE_LIST"
        done < "$MANAGED_PROFILES_FILE"
    fi
fi
[ "$AGENTS_MD" = true ] && stage_file "$SOURCE_CODEX/AGENTS.md" AGENTS.md || true
[ "$HOOKS" = true ] && stage_file "$SOURCE_CODEX/hooks.json" hooks.json || true
[ "$RULES" = true ] && stage_file "$SOURCE_CODEX/rules/codex-config.rules" rules/codex-config.rules || true
# Ship only repository theme files; never replace the user's themes directory.
for source in "$SOURCE_CODEX"/themes/*.tmTheme; do
    [ -e "$source" ] || continue
    if ! python3 - "$source" <<'PY'
import plistlib, sys
try:
    with open(sys.argv[1], "rb") as source:
        theme = plistlib.load(source)
    if not isinstance(theme, dict) or not isinstance(theme.get("settings"), list) or not theme["settings"]:
        raise ValueError("theme must contain a nonempty settings array with global settings first")
    for rule in theme["settings"]:
        if not isinstance(rule, dict) or not isinstance(rule.get("settings"), dict):
            raise ValueError("theme rules must contain a settings dictionary")
    if "scope" in theme["settings"][0]:
        raise ValueError("first theme entry must define global settings, without a scope")
except Exception as error:
    print(f"{sys.argv[1]}: invalid theme: {error}", file=sys.stderr)
    raise SystemExit(1)
PY
    then
        echo "staging validation failed; live configuration was not changed" >&2
        exit 2
    fi
    stage_file "$source" "themes/$(basename "$source")"
done


# Retire only byte-identical copies of the withdrawn companion and theme. The planner
# preserves customized files and any saved preview needing manual restoration.
RETIRED_LIST="$STAGE/.retired-config"
python3 "$ROOT/scripts/retire-config.py" "$TARGET_CODEX" > "$RETIRED_LIST"

if ! "$ROOT/scripts/validate.sh" "$STAGE"; then
    echo "staging validation failed; live configuration was not changed" >&2
    exit 2
fi
print_diff() {
    echo "station: $STATION"
    echo "manifest: ${MANIFEST#$ROOT/}"
    echo "config: merge ($OWNED_KEYS)"
    diff -u "$TARGET_CODEX/config.toml" "$STAGE/config.toml" 2>/dev/null || true
    if [ -f "$STAGE/AGENTS.md" ]; then
        if [ -f "$TARGET_CODEX/AGENTS.md" ]; then
            diff -u "$TARGET_CODEX/AGENTS.md" "$STAGE/AGENTS.md" || true
        else
            diff -u /dev/null "$STAGE/AGENTS.md" || true
        fi
    fi
    for staged in "$STAGE"/*.config.toml; do
        [ -e "$staged" ] || continue
        name=$(basename "$staged")
        diff -u "$TARGET_CODEX/$name" "$staged" 2>/dev/null || true
    done
    for staged in "$STAGE"/themes/*.tmTheme; do
        [ -e "$staged" ] || continue
        name="themes/$(basename "$staged")"
        if [ -f "$TARGET_CODEX/$name" ]; then
            diff -u "$TARGET_CODEX/$name" "$staged" || true
        else
            echo "would install theme: $name"
        fi
    done
    if [ -s "$STALE_LIST" ]; then
        while IFS= read -r stale; do echo "would remove stale profile: $stale"; done < "$STALE_LIST"
    fi
    while IFS= read -r retired; do echo "would remove retired config: $retired"; done < "$RETIRED_LIST"
    echo "backup would be created: $HOME/.codex-config.backup.<timestamp>"
}
if [ "$DRY_RUN" = true ]; then
    print_diff
    echo "dry-run: validated staging; no files were written"
    exit 0
fi

BACKUP=
if [ "$CREATE_BACKUP" = true ]; then
    BACKUP="$HOME/.codex-config.backup.$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP"
    backup_file() {
        relative=$1
        [ -f "$TARGET_CODEX/$relative" ] || return 0
        mkdir -p "$(dirname "$BACKUP/$relative")"
        cp "$TARGET_CODEX/$relative" "$BACKUP/$relative"
    }
    backup_file config.toml
    while IFS= read -r retired; do backup_file "$retired"; done < "$RETIRED_LIST"
    for staged in "$STAGE"/themes/*.tmTheme; do
        [ -e "$staged" ] && backup_file "themes/$(basename "$staged")"
    done
    for staged in "$STAGE"/*.config.toml; do [ -e "$staged" ] && backup_file "$(basename "$staged")"; done
    if [ -s "$STALE_LIST" ]; then
        while IFS= read -r stale; do backup_file "$stale"; done < "$STALE_LIST"
    fi
    [ "$AGENTS_MD" = true ] && backup_file AGENTS.md || true
    [ "$HOOKS" = true ] && backup_file hooks.json || true
    [ "$RULES" = true ] && backup_file rules/codex-config.rules || true
fi
install_file() {
    relative=$1
    mkdir -p "$(dirname "$TARGET_CODEX/$relative")"
    temporary="$TARGET_CODEX/$relative.tmp.$$"
    cp "$STAGE/$relative" "$temporary"
    mv "$temporary" "$TARGET_CODEX/$relative"
}
install_checked() {
    file=$1
    if ! install_file "$file"; then
        echo "install failed for $file; backup: ${BACKUP:-none}" >&2
        exit 3
    fi
}
# Install the theme before publishing the config that selects it.
for staged in "$STAGE"/themes/*.tmTheme; do
    [ -e "$staged" ] || continue
    install_checked "themes/$(basename "$staged")"
done
install_checked config.toml
for staged in "$STAGE"/*.config.toml; do
    [ -e "$staged" ] || continue
    install_checked "$(basename "$staged")"
done
if [ "$AGENTS_MD" = true ] && [ -f "$STAGE/AGENTS.md" ]; then install_checked AGENTS.md; fi
if [ "$HOOKS" = true ] && [ -f "$STAGE/hooks.json" ]; then install_checked hooks.json; fi
if [ "$RULES" = true ] && [ -f "$STAGE/rules/codex-config.rules" ]; then install_checked rules/codex-config.rules; fi
if [ "$PROFILES" = true ]; then
    install_checked .codex-config-managed-profiles
    if [ -s "$STALE_LIST" ]; then
        while IFS= read -r stale; do rm -f "$TARGET_CODEX/$stale"; done < "$STALE_LIST"
    fi
fi
if ! "$ROOT/scripts/validate.sh" "$TARGET_CODEX"; then
    echo "post-install validation failed; backup: ${BACKUP:-none}" >&2
    exit 3
fi
# Recheck hashes and preview state before removal; a concurrent user edit wins.
if [ -s "$RETIRED_LIST" ]; then
    python3 "$ROOT/scripts/retire-config.py" "$TARGET_CODEX" --remove
fi
if [ -n "$BACKUP" ]; then
    find "$HOME" -maxdepth 1 -type d -name '.codex-config.backup.[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]_[0-9][0-9][0-9][0-9][0-9][0-9]' -print |
        sort -r | tail -n +6 | while IFS= read -r old; do
            case "$old" in "$HOME"/.codex-config.backup.[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]_[0-9][0-9][0-9][0-9][0-9][0-9]) rm -rf "$old" ;; esac
        done
fi
echo "synced Codex configuration; backup: ${BACKUP:-disabled}"
