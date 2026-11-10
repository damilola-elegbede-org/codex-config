# Claude configuration migration

Source: [claude-config at 06fcb134](https://github.com/damilola-elegbede-org/claude-config/tree/06fcb1349e93860a779c14c5ac47b9bf0cbe2aa4/system-configs/.claude),
verified against upstream main on 2026-11-09. This refresh advances the previous
`cb257acb72ef568efc5d9dc2c25c365b179383b0` source snapshot.
The source contains 51 skills and 8 agents; this distribution contains 50 skill
entrypoints and 9 native agents. `codex-review` maps into `review` and the PR
workflow, while the bounded Codex `feature-agent` is intentionally retained from
the prior snapshot. `office-common` is shared support, not a skill. Repository-local `sync` is
already a Codex skill and is separate from this system configuration inventory.

## Native mappings and limits

- Skills use YAML `name` and `description` plus progressive reference files.
  Our frontmatter writes JSON scalars (valid YAML) to permit standard-library
  source validation. Installation uses [Codex’s user skill directory](https://learn.chatgpt.com/docs/build-skills),
  `~/.agents/skills`. Actual helper paths resolve from the loaded SKILL.md;
  `SKILL_DIR` is a variable the agent sets, not a Codex substitution.
- Agents use [native standalone TOML](https://learn.chatgpt.com/docs/agent-configuration/subagents)
  under `$CODEX_HOME/agents`, with name, description, and developer instructions.
  All inherit the parent permissions, model and reasoning settings. Read-only
  roles express that constraint in their instructions; `sandbox_mode` in a
  custom agent file does not enforce a separate shell sandbox and is rejected
  by this repository's validator. Roles cannot widen user authorization and
  are instructed to return orchestration needs to the parent.
- Claude model pins, frontmatter tool lists, permissionMode, memory, colors,
  and automatic skill preloading are not copied. These are not equivalent native
  settings. Developer instructions replace workflow intent, not persistent memory.
  Feature-agent explicitly reads feature-lifecycle when available. Missing named
  Claude specialists use available built-in agents with a domain brief.
- Questions use available Codex question tools under the active mode’s rules, or
  plain questions when permitted. Already-authorized work does not gain new
  approval requirements. Workflow/Task/Skill dispatchers, `/loop`, and Claude
  substitution syntax are removed. Independent-pass workflows report a limitation
  if delegation is unavailable or prohibited; they do not fake multiple reviewers.
- The Executive format now begins with conclusion, `You`, and `Unsure`. Portable
  Git safety, repository reuse, and prompt-authoring rules live in the global
  `AGENTS.md`; host-managed worktree paths and output protocols take precedence.
- `codex-review` maps to native independent review of the exact content being
  published, including new files. It does not launch a recursive Codex CLI or
  copy authentication. `land` checks current-head CI, reviews, threads, and
  mergeability with bounded repair/wait cycles. Merging still needs authorization.
- `goal-status` uses the available native goal-read tool, with no Claude
  transcript parser. `papercuts` requires an identified log and repository,
  counts deterministically, and treats attribution/fix status as claims to verify.
- `experiment` records a locked protocol, separates blind execution from scoring,
  and retains run evidence. Scratch directories and runner instructions are not
  an OS/network sandbox. No trial runs or model requests occur during sync.
- The eight Higgsfield skills are optional service-specific workflows adapted
  from the MIT-licensed v0.13.0 bundle. Each retains the vendor license and useful
  resources. Generic image and website requests follow the host's native tools.
  CLI/account setup, generation, uploads, and publication remain within the
  user's actual task authorization. Sync never installs or authenticates the CLI.
- Jev hooks are optional external Claude infrastructure, not bundled dependencies.
  ask-jev now uses a local filtered relevance ranker. Commit classification, review
  depth, Linear grouping, and DOM selection use direct evidence and agent judgment.
- MCP evaluations now use configured Codex CLI sessions, inherited model settings,
  exact XML answers, and observed successful target MCP calls. This uses model
  quota only when run explicitly. It does not require Anthropic authentication.
  Configure only approved read-only MCP tools: shell sandboxing cannot enforce
  remote API permissions. Linear needs an available authorized connector.
- The source docx/pdf/pptx/xlsx licenses expressly prohibit copying and derivatives.
  Their bundled implementations and OOXML support are not distributed here. These
  four skill names use fresh workflows based on documented libraries and a new
  standard-library ZIP/XML checker. This is not parity with the restricted schema,
  redlining, annotation, rendering, or recalculation helpers; unsupported advanced
  features require an available compatible editor. Browser, diagram, video, and
  MCP resources with permissive licenses retain their original terms and attribution.
  Video audio upload requires an explicitly requested/configured workflow.
- Tools and package versions in retained examples must be checked against current
  upstream documentation. External dependencies (LibreOffice, office JS packages,
  PDF libraries, Playwright, yt-dlp, ffmpeg, renderer, MCP SDK) are not installed by
  sync. Skill discovery is verified; every external service workflow is not run.

## Sync and verification

Every machine receives the complete owned configuration, global instructions,
skills, and agents by default, including unknown automatically detected hosts.
Station manifests retain explicit overrides: `skills: false`, `agents: false`,
and `agents_md: false` skip future updates without deleting installed files.
The Mini’s empty exceptions file inherits the full defaults. Station selection
does not restrict a rollout when no overrides exist. Shipped model, TUI, and
tmux policy are preserved; the response-style change is described above.
Sync validates all staged extensions before installing config, records ownership,
backs up changed owned files, publishes resources before skill entrypoints, and
uses atomic replacement per file. It checks hashes again before installation.
A sync is not a transaction across hundreds of files: partial failures report the
backup path. A later sync can safely adopt identical files. It does not delete
withdrawn extensions; retirement requires an explicit reviewed change.

Validation commands: `tests/test.sh`, `tests/run-mutations.sh`, Skill Creator's
`quick_validate.py` for every entrypoint, real Codex strict config parsing, and
app-server `skills/list` in an isolated workspace. Source validation checks
complete migration inventory, metadata, syntax, and agent settings. PR evidence
records the tested CLI version and results. External document/video/Higgsfield
workflows and paid generations are not claimed as tested.

## Skill inventory

Canonical: `docs/claude-migration.json` (reviewed 2026-11-09).

| Skill | Purpose |
| --- | --- |
| `ask` | Present a focused decision or request for missing information with a recommendation. Use when D asks to be consulted or a material decision remains unresolved. |
| `ask-jev` | Rank candidate source files locally before reading a large candidate set. Use for broad where-is-this-implemented questions; skips exact-symbol lookups. |
| `audit` | Audit Codex skill and agent definitions for schema, resource, and configuration integrity. Use for configuration ecosystem checks, with optional scoped repairs. |
| `branch` | Create a clearly named feature or fix branch from the verified upstream base. Use when branch creation is requested. |
| `bro` | Re-explain the previous assistant message in plain language. Use when D says bro, asks for a simpler explanation, or did not follow the response. |
| `changelog` | Explain changes in an installed or requested Codex CLI release using official release notes. Use when D asks what changed after an upgrade. |
| `colorwheel` | Stress-test an idea or artifact with Red, Blue, Yellow, Orange, Green, Purple, and White perspectives. Read-only; deep mode verifies findings independently. |
| `commit` | Commit the intended changes with a clear message and the repository’s authorized identity. Use when changes are ready to commit; supports safe amend. |
| `debug` | Investigate bugs, crashes, race conditions, memory leaks, or performance problems and verify a targeted fix when requested. |
| `deps` | Audit, update, or clean dependencies across detected package managers. Use when dependency health or safe upgrades are requested. |
| `docs` | Create, update, or audit project documentation against the current implementation. Use for README, API, architecture, or setup documentation. |
| `docx` | Create, read, or edit Word documents with formatting, tables, tracked changes, and validation. Use when the requested artifact is a DOCX file. |
| `excalidraw` | Create and visually validate themed Excalidraw diagrams for systems, flows, sequences, and state machines. |
| `experiment` | Test a falsifiable claim with a pre-registered protocol, bounded local trials, controls, and a reproducible verdict. Use when new empirical evidence is needed; use test or verify for existing project checks. |
| `feature-lifecycle` | Deliver an authorized feature, bug fix, or refactor from specification through implementation and PR. Supports bounded autonomous slices and merge only when authorized. |
| `fix-ci` | Diagnose and repair GitHub Actions failures from actual job logs. Use for a failing run or a requested investigation of CI. |
| `frontend-design` | Build or improve a distinctive frontend interface in the user’s chosen project and framework. Use for web components, pages, layouts, and visual styling. |
| `gauntlet-loop` | Build a deliverable against a concrete reference using independent builder/critic rounds and a blind final panel. Use only when a rigorous gauntlet is explicitly requested. |
| `goal-status` | Report the current persistent goal, measured budget use, progress, and remaining work without changing its state. |
| `higgsfield-brandkit` | Create or extend brand systems and brandbooks through Higgsfield when Higgsfield is explicitly requested or already selected for the project. |
| `higgsfield-generate` | Use Higgsfield models, workflows, Marketing Studio, or video analysis when the user explicitly requests Higgsfield or has selected that service; ordinary image requests use the host image tools. |
| `higgsfield-marketplace-cards` | Create marketplace listing image sets with the Higgsfield marketplace-cards service when Higgsfield is explicitly requested or already selected. |
| `higgsfield-product-photoshoot` | Create product photography and variations with Higgsfield product-photoshoot when Higgsfield is explicitly requested or already selected. |
| `higgsfield-soul-id` | Train and manage a Higgsfield Soul identity from supplied face photos when the user requests Higgsfield Soul training. |
| `higgsfield-video-explainer` | Create narrated, illustrated explainer videos with the Higgsfield block-and-assembly workflow when Higgsfield is explicitly requested or already selected. |
| `higgsfield-websites` | Build, edit, or deploy websites, apps, games, and their assets on the Higgsfield platform when Higgsfield is explicitly selected; ordinary website requests use the host website workflow. |
| `higgsfield-youtube-thumbnail` | Create truthful video thumbnails and covers through Higgsfield when Higgsfield is explicitly requested or already selected. |
| `implement` | Implement a markdown specification in dependency-ordered slices and verify its acceptance criteria. Supports preview-only and incremental modes. |
| `interview` | Settle a task’s requirements through an explicit interview, then execute the confirmed authorized scope to its completion criteria. |
| `land` | Follow an authorized pull request through CI and review remediation to a verified merge-ready state; supports a read-only status check. |
| `mcp-builder` | Design, implement, and evaluate MCP servers for external services using the current Python or TypeScript SDK. |
| `merge` | Merge a branch or authorized pull request while preserving work and resolving conflicts deliberately. Use when a merge is requested. |
| `papercuts` | Analyze an explicitly identified papercut log for recurring workflow friction, repository attribution, and evidence that a fix exists. |
| `pdf` | Read, create, combine, split, OCR, or fill PDF documents. Use when a PDF is the input or requested output. |
| `plan` | Turn a feature or project request into a grounded PRD and dependency-ordered implementation slices. Use for planning; supports simple, preview-only, and file-input modes. |
| `pptx` | Create, read, or edit PowerPoint presentations, including templates, notes, layouts, and visual review. Use when a slide deck is requested. |
| `pr` | Create or update a GitHub pull request with verified evidence and follow its checks and reviews to a bounded readiness result. |
| `prime` | Map a repository’s architecture, stack, entry points, and verification commands. Use for onboarding or focused codebase exploration. |
| `process-linear` | Triage D’s BareClaude Linear decision queue, separating genuine decisions from agent work and recording authorized outcomes without executing downstream actions. |
| `prompt` | Improve prompt text with the SCOPE framework while preserving intent. Use for prompt optimization; does not execute the prompt. |
| `push` | Publish verified commits to the intended remote branch through authorized identity tooling. Supports a read-only preview and explicitly requested history rewrites. |
| `rebase` | Update an owned feature branch onto its verified upstream base with conflict and stash preservation. Use when rebase, continue, or abort is requested. |
| `resolve-comments` | Validate and address PR review threads or local review findings, publish authorized fixes, and verify resolution. Supports analysis-only mode. |
| `review` | Review a branch, commit, working diff, or requested wider codebase for consequential defects. Deep mode adds security and accessibility perspectives. |
| `ship-it` | Run requested documentation, test, verification, review, commit, push, and PR stages in order. Use when shipping code is requested; supports a no-write preview. |
| `test` | Discover and run a project’s test suite, or create tests when requested. Reports failures without silently repairing them. |
| `verify` | Run the project’s real verification gates, repair authorized failures, and re-run with a three-attempt bound. Use to verify completed work or risky changes. |
| `watch` | Read, transcribe, summarize, or research a video from captions and optional frames. Use for a video URL or local recording; transcript-only is the default. |
| `webapp-testing` | Test local web applications with Playwright, screenshots, DOM inspection, console logs, and reproducible interaction steps. |
| `xlsx` | Create, read, clean, or edit spreadsheet files with formulas and formatting. Use when the primary deliverable is XLSX, XLSM, CSV, or TSV. |

## Agent inventory

| Agent | Scope |
| --- | --- |
| `architect` | Analyze system architecture, API contracts, infrastructure design, and cross-module tradeoffs; return a sourced design, not implementation. |
| `code-reviewer` | Independently review code changes for concrete correctness, security, performance, and regression risks. |
| `debugger` | Investigate crashes, intermittent failures, race conditions, memory leaks, and performance regressions; repair only when assigned. |
| `devops` | Implement and diagnose CI/CD, infrastructure as code, container, deployment, and reliability changes within assigned scope. |
| `experiment-runner` | Execute one authorized locked experiment from its blinded plan, or judge anonymized observations against a supplied rubric; report observations and anomalies. |
| `feature-agent` | Implement an assigned feature slice from its specification and acceptance criteria, returning verified changes or an authorized PR. |
| `frontend-engineer` | Implement frontend components, design systems, responsive layouts, accessibility, and client-side behavior within assigned files. |
| `security-auditor` | Review security boundaries, authentication/authorization, vulnerability scenarios, and threat models with evidence. |
| `test-engineer` | Create and run behavior-focused tests, diagnose coverage gaps or flakiness, and validate assigned acceptance criteria. |
