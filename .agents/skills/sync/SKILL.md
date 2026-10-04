---
name: sync
description: Install this repository's owned Codex configuration into ~/.codex — staged, validated, backed up, atomic. Use after pulling main; --dry-run on a fleet node.
---

# /sync

Run from a clone of this repository that is current with `origin/main` (the
script refuses a checkout behind its local `origin/main` ref):

```bash
scripts/sync.sh $ARGUMENTS
```

Flags: `--dry-run` (validate the staged result and print the diff, write
nothing), `--no-backup`, `--force`. Exit codes: 0 synced · 1 pre-flight ·
2 validation failed (live untouched) · 3 install or post-validate failed
(backup path printed).

What it owns: the repository-default or manifest-listed top-level keys of
`config.toml`
(`model`, `model_reasoning_effort`, `web_search`, `approval_policy`,
`sandbox_mode`, and the root `[tui]` table on the Mini) and the profile files
`think|code|review.config.toml`. This includes full-access permission defaults
and the native status line. Shipped `themes/*.tmTheme` files are also staged,
validated, backed up, and installed; unrelated user themes are preserved.
The configured theme is the built-in `monokai-extended-origin`. Sync retires
unchanged files from the withdrawn custom theme and companion, after backup.
The status line is native Codex only; sync does not modify tmux.
The Mini manifest has no overrides, so it inherits
the complete default ownership list, including global `AGENTS.md` with the
Executive response style. Unknown auto-detected hosts do not receive global
instructions. What it never touches: `[projects.*]`,
`[notice.model_migrations]`, nested `[tui.*]` state, `auth.json`, `sessions/`,
`history.jsonl`, sqlite, `cache/`, `log/`, `plugins/`, `skills/.system`,
`rules/default.rules`, unrelated user skills and agents. Shipped skills and shared
resources install into `~/.agents/skills`; native agent TOMLs install into
`$CODEX_HOME/agents`. Sync tracks owned file hashes, preserves unrelated files,
and stops before installation on customized or unmanaged conflicting shipped
paths. Recognized or explicitly selected stations install these by default;
manifest `skills: false` / `agents: false` skips future updates. Unknown
auto-detected hosts do not receive these extensions. Removed source extensions
are retained until explicit retirement. On a fleet node (Mac Mini) run
`--dry-run` first, then a `codex-review.sh` smoke, before a real sync.
