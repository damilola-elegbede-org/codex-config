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
model/reasoning, Git branch, current directory, Codex version, and context used.
The `executive` theme is an unmodified copy of the exact **Monokai Extended
Origin** bundled with Codex 0.159.2. Its provenance and license are shipped in
`themes/`. This controls code and diff highlighting; select `/theme` → `executive`
in an existing client or restart/resume to reload it.

The separate Claude-style companion footer supplies fields the native footer
cannot: fixed session colors, independently colored labels and numbers, weekly
**used**, Executive style, five-segment bars, and a weekly burn index. It appears
as an additional **tmux status row**, not a native Codex callback. Codex 0.159.2
has no custom-script field; its native footer remains available outside tmux.

After sync, activate or restore the preview in a chosen tmux session:

```sh
python3 -B ~/.codex/statusline/preview.py install --pane "$TMUX_PANE"
python3 -B ~/.codex/statusline/preview.py restore --pane "$TMUX_PANE"
```

Use the pane ID from `tmux list-panes -a` when invoking from an agent process:
its inherited `TMUX_PANE` may refer to another terminal. Installation preserves
existing status rows, affects only that tmux session, and is idempotent. Sync
updates the renderer without automatically changing other terminal sessions.
No tmux configuration file or shell profile is modified. Dependencies: Python
3.11+, Git, and tmux (tested with 3.6a). The wrapper supports Homebrew Python.

The companion order is session (pastel purple), model (red), branch (orange),
folder (pale blue), Executive (yellow), running version (bright terminal green),
Context and weekly Usage (gray labels, green numbers), then Burn. Context and
usage remain green as requested; burn changes blue/green/yellow/orange/red.
Bars appear at pane widths of at least 175 columns. Very narrow terminals may
clip the rightmost fields. A detached Git HEAD displays its short commit;
non-repositories display `no-git`.

Telemetry comes from the selected conversation's local `session_index.jsonl`
and incremental reads of its rollout, never credentials or a network scraper.
The latest turn supplies model/cwd; context uses Codex's 12,000-token baseline
and latest-turn tokens, not cumulative session tokens. Weekly usage selects
Codex's reported 10,080-minute window from either primary or secondary limits.
The version is read from the native footer, since resumed-session metadata may
name a different client. Unavailable or ambiguous values show `--`.

Burn = quota fraction used / fraction of the reported week elapsed. It calculates as soon as elapsed time is positive (no borrowed Claude warmup),
shows the uncapped ratio, rounds to one decimal before assigning color, and uses boundaries 0.5 / 1.1 / 1.3 / 1.5. A value of 1.0x
means consumption matches the week's elapsed fraction. Quota snapshots older
than 15 minutes show their age and suppress burn; snapshots past reset show
`--` rather than invented new-week usage. Quota values update when Codex emits
telemetry, so they are last observed values, not continuous account polling.
Claude-only credit budgets, Fable quotas, and fabricated token-to-dollar costs
are not displayed. There is no version-upgrade sparkle yet.

Source reference: Claude `statusline.sh` at commit
`c24b5f03e621732e35fc2a8a3758c7925a919833`. The renderer copies its progress bars,
quota pacing, rounding, and thresholds, with D's fixed field colors.

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
