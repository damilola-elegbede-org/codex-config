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
The explicit `statusline/` companion helpers and theme attribution files are
also staged and installed. Sync never activates or changes tmux sessions; use
`python3 -B ~/.codex/statusline/preview.py install --pane <pane-id>` for a live
preview, and the same command with `restore` to undo it.
The Mini manifest has no overrides, so it inherits
the complete default ownership list, including global `AGENTS.md` with the
Executive response style. Unknown auto-detected hosts do not receive global
instructions. What it never touches: `[projects.*]`,
`[notice.model_migrations]`, nested `[tui.*]` state, `auth.json`, `sessions/`,
`history.jsonl`, sqlite, `cache/`, `log/`, `plugins/`, `skills/.system`,
`rules/default.rules`, user skills. On a fleet node (Mac Mini) run
`--dry-run` first, then a `codex-review.sh` smoke, before a real sync.
