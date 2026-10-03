---
name: "changelog"
description: "Explain changes in an installed or requested Codex CLI release using official release notes. Use when D asks what changed after an upgrade."
metadata: {"source-repository": "damilola-elegbede-org/claude-config", "source-commit": "cb257acb72ef568efc5d9dc2c25c365b179383b0", "source-path": "system-configs/.claude/skills/changelog/SKILL.md"}
---

# changelog

Read codex --version for the installed version, or honor an explicitly requested version. Fetch the matching official OpenAI Codex release notes/release page through available browsing tools, using OpenAI sources. Summarize actual user-facing features, improvements, and fixes with direct links.

Do not claim an upgrade-from version or installation date unless an actual local record establishes it. Codex has no equivalent to the Claude upgrade hook’s cached slice in this migration. If offline or a matching source is missing, state the limit and use only a verified local cache supplied by the user. Full mode means a more complete sourced summary, not unrestricted verbatim reproduction. Do not write Claude caches or silently install an upgrade.

Follow the host’s instructions and current authorization. Tool names, delegation, models, sandboxing, and question availability come from the running Codex session; this skill does not override them. Resolve helpers from this SKILL.md’s actual directory (SKILL_DIR in examples is a variable you set, not a Codex substitution).
