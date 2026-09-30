# Codex Config

This public repository is the source of truth for the small, explicit portion
of a Codex home that it owns. It uses native Codex configuration and file-based
profiles; it does not ship a persona dispatcher, custom prompts, or
`[profiles.*]` tables.

## Owned configuration

`system-configs/.codex/config.toml` owns these top-level scalar keys:

- `model`
- `model_reasoning_effort`
- `web_search`
- `approval_policy` (`"never"`)
- `sandbox_mode` (`"danger-full-access"`)

It also owns the top-level `[tui]` table, whose `status_line` shows the thread,
model/reasoning, Git branch, current directory, context usage, and task progress. The line
uses only Codex-native items; it does not execute the Claude shell script or
access Claude usage data.
It also owns the file profiles that it ships (`think.config.toml`,
`code.config.toml`, and `review.config.toml`). The profile values mirror the
fleet model policy and are checked by `tests/test-policy-agreement.sh` whenever
that policy checkout is available.

These approval, sandbox, and TUI defaults apply only when the laptop-default
ownership list is in use. The checked-in Mac Mini manifest remains scoped to
model settings and profiles, so it does not receive them.

## Never touched

Sync does not overwrite `[projects.*]`, `[notice.model_migrations]`, or nested
`[tui.*]` state such as `[tui.model_availability_nux]`. It atomically replaces
the owned root `[tui]` table. It does not back up `auth.json`, `sessions/`,
`history.jsonl`, `*.sqlite*`, `cache/`, `log/`, `tmp/`, `plugins/`,
`skills/.system`, or `rules/default.rules`. Unknown profile files also remain
in place. These are Codex state or machine-local configuration, not repository
configuration.

## Validate and sync

Validate a staged home without spending a token:

```sh
scripts/validate.sh "$CODEX_HOME"
```

The validator succeeds only after strict Codex parsing reaches a deliberately
missing model provider. It does not make a model request.

Preview a deployment:

```sh
scripts/sync.sh --dry-run
```

Apply a deployment from a current checkout:

```sh
scripts/sync.sh
```

Sync stages and validates first, makes an owned-only timestamped backup, then
atomically replaces each owned file and validates again. `--no-backup` disables
that backup; `--force` bypasses the local `origin/main` freshness comparison.
Station manifests scope fleet-sensitive surfaces. On a host without a manifest,
laptop-first defaults apply only when `CODEX_CONFIG_STATION` is explicitly set,
for example `CODEX_CONFIG_STATION=laptop scripts/sync.sh`. An unrecognized,
auto-detected host instead receives the restricted Mini-equivalent key set
(`model`, `model_reasoning_effort`, and `web_search`). The checked-in Mini
manifest intentionally enables only those model keys and profiles.

## Rollout

Roll out on a laptop first. On the Mini, preview only:

```sh
scripts/sync.sh --dry-run
```

After the resulting diff and staged validator are reviewed, schedule a normal
apply in a maintenance window and smoke the fleet gate:

```sh
infra/scripts/codex-review.sh
```

The Mini Codex home is a fleet surface. Do not use this repository to change
global instructions, hooks, rules, or user skills there until their impact
reviews explicitly enable them.

## Tests

```sh
tests/test.sh
```

The test suite is hermetic: it stubs `codex` on `PATH`. Run
`scripts/validate.sh` separately where a real Codex binary is available.
