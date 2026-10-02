# Codex Config

This public repository is the source of truth for the small, explicit portion
of a Codex home that it owns. It uses native Codex configuration and file-based
profiles; it does not ship a persona dispatcher or
`[profiles.*]` tables.

## Owned configuration

`system-configs/.codex/config.toml` owns these top-level scalar keys:

- `model`
- `model_reasoning_effort`
- `web_search`
- `approval_policy` (`"never"`)
- `sandbox_mode` (`"danger-full-access"`)

It also owns the top-level `[tui]` table, whose `status_line` shows the thread,
model/reasoning, Git branch, current directory, Codex version, context remaining,
weekly quota remaining, and five-hour quota remaining.
Codex uses its built-in **Monokai Extended Origin** theme
(`tui.theme = "monokai-extended-origin"`). No custom Executive theme is shipped.
This setting controls code/diff highlighting and native status-line colors;
Executive response formatting is configured separately in `AGENTS.md`.

The status line is **native Codex only**. This repository does not install or
modify tmux status rows. In Codex 0.159.2, native items cannot run a shell script
or render arbitrary custom fields. Context and both quota windows consistently show the percentage remaining.
Quota fields appear only when Codex receives the corresponding window; accounts
without a five-hour window will not display a fabricated value.
There is no native output-style label, burn index, or five-segment usage bar.

Sync backs up and retires unchanged files from the withdrawn tmux
companion and custom Executive theme. Customized files or saved preview state are preserved so an existing
preview can still be restored manually. Sync never changes tmux settings.

Native footer colors come from the syntax theme. Session colors vary by thread
ID; model, branch, path, usage, and version use theme scopes. Independent fixed
field colors, separately colored labels and values, and usage-pressure color
thresholds are not configurable in this release. Selecting Monokai Extended Origin uses its native footer palette.

The theme is a visual palette. Separately, `system-configs/.codex/AGENTS.md`
installs the Executive response style as global Codex instructions: tagged
openings (`FYI`, `DECISION`, `APPROVAL`, `INPUT`, `ACTION`), action metadata when
needed, concise sourced evidence, and a closing `Next` line. Required review
schemas, exact-output tasks, and automation protocols keep their prescribed format.
This style supplements Codex's coding instructions; it does not replace them.
It also owns the file profiles that it ships (`think.config.toml`,
`code.config.toml`, and `review.config.toml`). The profile values mirror the
fleet model policy and are checked by `tests/test-policy-agreement.sh` whenever
that policy checkout is available.

The checked-in Mac Mini manifest has an empty override set (`"sync": {}`),
so it inherits all repository-owned settings, profiles, and global instructions,
including the native status line and full-access defaults (`approval_policy =
"never"`, `sandbox_mode = "danger-full-access"`). These permission defaults
also apply to fleet processes that do not supply higher-priority overrides.

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
auto-detected host instead receives the restricted key set (`model`,
`model_reasoning_effort`, and `web_search`) without global `AGENTS.md`.
Recognized or explicitly selected stations install the shipped `AGENTS.md` by
default. A manifest's `agents_md: false` skips future instruction updates;
it does not remove an already installed `AGENTS.md` or disable its behavior.
The checked-in Mini manifest
has no exceptions: it inherits all repository-owned settings and profiles.

## Rollout

Preview the changes before applying, including on the Mini:

```sh
scripts/sync.sh --dry-run
```

On the Mini, run the fleet review smoke from the BareClaude checkout before
applying (replace the path with your current codex-config checkout):

```sh
infra/scripts/codex-review.sh --base origin/main --repo-root /path/to/codex-config
```

Review the diff and staged validation, then apply manually:

```sh
scripts/sync.sh
```

The Mini Codex home is a fleet surface. Executive formatting applies to
human-facing prose, including other processes using this home; it explicitly
defers to machine-readable and review output contracts. Hooks, rules, and user
skills remain outside this rollout. Global instructions load at session startup;
restart/resume existing sessions after sync to load them and the status-line order.

## Tests

```sh
tests/test.sh
```

The test suite is hermetic: it stubs `codex` on `PATH`. Run
`scripts/validate.sh` separately where a real Codex binary is available.
