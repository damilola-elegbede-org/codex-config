# Claude configuration migration

Source: [claude-config at cb257ac](https://github.com/damilola-elegbede-org/claude-config/tree/cb257acb72ef568efc5d9dc2c25c365b179383b0/system-configs/.claude).
The checked-in migration contains every skill and agent in that source snapshot:
38 skill entrypoints and 8 standalone native Codex agent definitions.
`office-common` is shared support, not a 39th skill. Repository-local `sync` is
already a Codex skill and is separate from this system configuration inventory.

## Native mappings and limits

- Skills use YAML `name` and `description` plus progressive reference files.
  Our frontmatter writes JSON scalars (valid YAML) to permit standard-library
  source validation. Installation uses [Codex’s user skill directory](https://learn.chatgpt.com/docs/build-skills),
  `~/.agents/skills`. Actual helper paths resolve from the loaded SKILL.md;
  `SKILL_DIR` is a variable the agent sets, not a Codex substitution.
- Agents use [native standalone TOML](https://learn.chatgpt.com/docs/agent-configuration/subagents)
  under `$CODEX_HOME/agents`, with name, description, and developer instructions.
  Architect, code-reviewer, and security-auditor restrict shell access to read-only;
  other roles inherit the parent permissions. All inherit model and reasoning
  settings. Roles cannot widen user authorization or spawn children themselves.
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

`skills` and `agents` follow the global-instructions station boundary. The Mini’s
empty exceptions file inherits all three. Unknown automatically detected hosts
receive none. Existing model, response style, TUI, and tmux policy are unchanged.
Sync validates all staged extensions before installing config, records ownership,
backs up changed owned files, publishes resources before skill entrypoints, and
uses atomic replacement per file. It checks hashes again before installation.
A sync is not a transaction across hundreds of files: partial failures report the
backup path. A later sync can safely adopt identical files. It does not delete
withdrawn extensions; retirement requires an explicit reviewed change.

Validation: `tests/test.sh`, `tests/run-mutations.sh`, Skill Creator’s
`quick_validate.py` for all 38 entrypoints, real Codex strict config parsing, and
Codex 0.160.0 app-server `skills/list` in an isolated home (38 discovered, no skill
errors). Agent TOMLs pass required-field/permission checks; actual agent execution
and external document/video/service dependencies are not claimed as tested.

## Skill inventory

> Canonical: docs/claude-migration.json (generated 2026-10-03)

| Skill | Purpose |
| --- | --- |
| `ask` | Present a focused decision or request for missing information with a recommendation |
| `ask-jev` | Rank candidate source files locally before reading a large candidate set |
| `audit` | Audit Codex skill and agent definitions for schema, resource, and configuration integrity |
| `branch` | Create a clearly named feature or fix branch from the verified upstream base |
| `bro` | Re-explain the previous assistant message in plain language |
| `changelog` | Explain changes in an installed or requested Codex CLI release using official release notes |
| `colorwheel` | Stress-test an idea or artifact with Red, Blue, Yellow, Orange, Green, Purple, and White perspectives |
| `commit` | Commit the intended changes with a clear message and the repository’s authorized identity |
| `debug` | Investigate bugs, crashes, race conditions, memory leaks, or performance problems and verify a targeted fix when requested |
| `deps` | Audit, update, or clean dependencies across detected package managers |
| `docs` | Create, update, or audit project documentation against the current implementation |
| `docx` | Create, read, or edit Word documents with formatting, tables, tracked changes, and validation |
| `excalidraw` | Create and visually validate themed Excalidraw diagrams for systems, flows, sequences, and state machines |
| `feature-lifecycle` | Deliver an authorized feature, bug fix, or refactor from specification through implementation and PR |
| `fix-ci` | Diagnose and repair GitHub Actions failures from actual job logs |
| `frontend-design` | Build or improve a distinctive frontend interface in the user’s chosen project and framework |
| `gauntlet-loop` | Build a deliverable against a concrete reference using independent builder/critic rounds and a blind final panel |
| `implement` | Implement a markdown specification in dependency-ordered slices and verify its acceptance criteria |
| `interview` | Interview D in structured rounds to settle a task’s requirements |
| `mcp-builder` | Design, implement, and evaluate MCP servers for external services using the current Python or TypeScript SDK |
| `merge` | Merge a branch or authorized pull request while preserving work and resolving conflicts deliberately |
| `pdf` | Read, create, combine, split, OCR, or fill PDF documents |
| `plan` | Turn a feature or project request into a grounded PRD and dependency-ordered implementation slices |
| `pptx` | Create, read, or edit PowerPoint presentations, including templates, notes, layouts, and visual review |
| `pr` | Create or update a GitHub pull request with a behavior-focused title, rationale, and verified test evidence |
| `prime` | Map a repository’s architecture, stack, entry points, and verification commands |
| `process-linear` | Triage D’s BareClaude Linear decision queue, separating genuine decisions from agent work and recording authorized outcomes without executing downstream actions |
| `prompt` | Improve prompt text with the SCOPE framework while preserving intent |
| `push` | Publish verified commits to the intended remote branch through authorized identity tooling |
| `rebase` | Update an owned feature branch onto its verified upstream base with conflict and stash preservation |
| `resolve-comments` | Validate and address PR review threads or local review findings, publish authorized fixes, and verify resolution |
| `review` | Review a branch, commit, working diff, or requested wider codebase for consequential defects |
| `ship-it` | Run requested documentation, test, verification, review, commit, push, and PR stages in order |
| `test` | Discover and run a project’s test suite, or create tests when requested |
| `verify` | Run the project’s real verification gates, repair authorized failures, and re-run with a three-attempt bound |
| `watch` | Read, transcribe, summarize, or research a video from captions and optional frames |
| `webapp-testing` | Test local web applications with Playwright, screenshots, DOM inspection, console logs, and reproducible interaction steps |
| `xlsx` | Create, read, clean, or edit spreadsheet files with formulas and formatting |

## Agent inventory

| Agent | Scope |
| --- | --- |
| `architect` | Analyze system architecture, API contracts, infrastructure design, and cross-module tradeoffs; return a sourced design, not implementation. |
| `code-reviewer` | Independently review code changes for concrete correctness, security, performance, and regression risks. |
| `debugger` | Investigate crashes, intermittent failures, race conditions, memory leaks, and performance regressions; repair only when assigned. |
| `devops` | Implement and diagnose CI/CD, infrastructure as code, container, deployment, and reliability changes within assigned scope. |
| `feature-agent` | Implement an assigned feature slice from its specification and acceptance criteria, returning verified changes or an authorized PR. |
| `frontend-engineer` | Implement frontend components, design systems, responsive layouts, accessibility, and client-side behavior within assigned files. |
| `security-auditor` | Review security boundaries, authentication/authorization, vulnerability scenarios, and threat models with evidence. |
| `test-engineer` | Create and run behavior-focused tests, diagnose coverage gaps or flakiness, and validate assigned acceptance criteria. |
