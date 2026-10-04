---
name: "ask-jev"
description: "Rank candidate source files locally before reading a large candidate set. Use for broad where-is-this-implemented questions; skips exact-symbol lookups."
metadata: {"source-repository": "damilola-elegbede-org/claude-config", "source-commit": "cb257acb72ef568efc5d9dc2c25c365b179383b0", "source-path": "system-configs/.claude/skills/ask-jev/SKILL.md"}
---

# ask-jev

Resolve scripts/rank-files.py from this skill directory. Run python3 <skill-directory>/scripts/rank-files.py --root "<search-root>" --top 8 "<query>" <paths...>. The search root defaults to the current directory; exclusions apply only within that tree, and outside paths are excluded. It filters binary, oversized, secret-named, vendor/generated, and work/Visa paths, then ranks path and text keyword matches locally.

Read the best candidates first, widening the search if needed. Scores are heuristic relevance points, not model probabilities. No Jev hooks, external model call, API key, or egress is required. An empty shortlist is not proof the implementation is absent; fall back to rg and targeted reads. Exit 1 means no eligible file and exit 2 a usage error. Do not export excluded code to another provider to recover the original Jev behavior.

Follow the host’s instructions and current authorization. Tool names, delegation, models, sandboxing, and question availability come from the running Codex session; this skill does not override them. Resolve helpers from this SKILL.md’s actual directory (SKILL_DIR in examples is a variable you set, not a Codex substitution).
