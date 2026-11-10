---
name: "ask-jev"
description: "Use Jev to rank candidate source files before reading a large set, with a local keyword fallback. Use for broad where-is-this-implemented questions; skips exact-symbol lookups."
metadata: {"source-repository": "damilola-elegbede-org/claude-config", "source-commit": "e1c3210b3938d4ac0a6452baf85b9089e9267371", "source-path": "system-configs/.claude/skills/ask-jev/SKILL.md"}
---

# ask-jev

Before invoking the helper, exclude paths under peer installed skill directories from <paths...>. Do not enumerate or read peer skill directories to build the candidate list; use source files within the requested project instead.

Resolve `scripts/rank-files.py` from this skill directory. Run:

```sh
python3 <skill-directory>/scripts/rank-files.py --root "<search-root>" --top 8 "<query>" <project-paths...>
```

The helper filters binaries, oversized and secret-named files, generated/vendor trees, symlinks, installed peer skills, and work/Visa directories within the search tree. Candidates outside the root are excluded. It prefilters by keywords, then sends at most 60 candidates in batches of 20 to the native client at `${CODEX_HOME:-~/.codex}/hooks/jev/jev-ask`: paths and the first 40 lines, capped at 240 characters per line. The client also enforces configured work/Visa exclusions for the request root and targets and redacts known credentials before sending. Do not bypass exclusions or send excluded code to another provider.

Read the best candidates first, widening if needed. Output is JSON: `score` is the local keyword score; `probability` is Jev's relevance probability when `source` is `jev`. If the service, credentials, dependency, or rule is unavailable, `source` is `local` and `probability` is `null`; stderr identifies the fallback. A local score is not a model probability. An empty shortlist is not proof the implementation is absent: fall back to `rg` and targeted reads. Exit 1 means no eligible file and exit 2 a usage error.

The synced client uses Node 22+, its pinned SDK cache, and existing AI Gateway credentials. `jev-ask --check` checks local prerequisites without a model request. `JEV_DIR` can select an isolated client directory. Rule `ask-jev-rank` in the client's `jev-rules.json` controls bounded batches and timeouts; `off` selects local fallback. A regular `${CODEX_HOME:-~/.codex}/jev.off` file disables calls. Decision logs contain outcome/count metadata, not queries or file content. Running this skill uses the configured Jev service; do not imply that hook installation itself ran a model request.

Follow the host’s instructions and current authorization. Tool names, delegation, models, sandboxing, and question availability come from the running Codex session; this skill does not override them. Resolve helpers from this SKILL.md’s actual directory (SKILL_DIR in examples is a variable you set, not a Codex substitution).
