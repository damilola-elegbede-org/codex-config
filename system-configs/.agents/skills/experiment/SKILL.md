---
name: "experiment"
description: "Test a falsifiable claim with a pre-registered protocol, bounded local trials, controls, and a reproducible verdict. Use when new empirical evidence is needed; use test or verify for existing project checks."
metadata: {"source-repository": "damilola-elegbede-org/claude-config", "source-commit": "06fcb1349e93860a779c14c5ac47b9bf0cbe2aa4", "source-path": "system-configs/.claude/skills/experiment/SKILL.md"}
---

# experiment

Choose the smallest experiment that distinguishes the claim from its alternative. A code or documentation lookup may already settle it. Record the hypothesis, falsifying outcome, metric, pass rule, negative control, repetitions, seed, time budget, and whether the evidence is observed or simulated before running. A simulation supports claims about the simulation only.

Resolve helpers relative to this SKILL.md. `scripts/new.sh <slug>` creates `.tmp/experiments/<id>/`; fill its protocol and plan using [references/protocol.md](references/protocol.md), then `scripts/lock.sh <dir>` seals them. The lock detects subsequent edits; it is not a signature or protection against a writer who replaces the artifacts. Never re-lock after observations. Change the design in a new directory.

Read [references/execution.md](references/execution.md) before running commands. Inspect every command and observer against the user's existing authorization and host permissions. `python3 scripts/run.py <dir> --execute-local` runs only protocols classified `local`, in scratch directories with an isolated HOME and a bounded process group. These conventions are **not an operating-system or network sandbox**. The helper does not supply missing authorization or replace host approval. Calls to models or external services use available host tools under the existing authorization and budget, then `run.py <dir> --record ...` records their evidence. Do not extract credentials or copy them into experiment artifacts.

When independent delegation is available and permitted, give `experiment-runner` only the locked directory, helper location, and execution scope; keep the hypothesis and expected results out of its context. Otherwise run directly and disclose the lack of independent execution. One writer per directory; an interrupted run resumes recorded pairs without repeating them. If the runner refuses, correct the design or report the missing requirement, never execute the refused commands through another path.

Prefer mechanical observations. When judgment is necessary, freeze the rubric before locking and follow [references/judging.md](references/judging.md). A fresh permitted judge sees anonymized outputs and the rubric only; do not present your own repeated assessment as independent evidence.

`python3 scripts/score.py <dir>` applies the locked rule and writes `verdict.json` with protocol and observation hashes. Report SUPPORTED, REFUTED, or INCONCLUSIVE, the valid sample size, control behavior, interval, evidence kind, and artifact path. SUPPORTED describes these trials; it never means proved. Missing, invalid, or failed-control observations remain inconclusive. An observed effect does not authorize deployment, publication, or further spending. Sync installs these files and runs no experiments.

Follow the host's instructions and current authorization. Tools, models, delegation, sandboxing, and question availability come from the running Codex session.
