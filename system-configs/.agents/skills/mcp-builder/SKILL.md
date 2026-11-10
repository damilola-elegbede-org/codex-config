---
name: "mcp-builder"
description: "Design, implement, and evaluate MCP servers for external services using the current Python or TypeScript SDK."
license: "Complete terms in LICENSE.txt"
metadata: {"source-repository": "damilola-elegbede-org/claude-config", "source-commit": "06fcb1349e93860a779c14c5ac47b9bf0cbe2aa4", "source-path": "system-configs/.claude/skills/mcp-builder/SKILL.md"}
---

# mcp-builder

Read guide.md for design and reference/mcp_best_practices.md for interfaces; select reference/python_mcp_server.md or node_mcp_server.md for the chosen language. Verify current SDK/protocol documentation rather than trusting retained examples’ versions. Use typed schemas, pagination, actionable errors, structured output, and accurate read/write annotations. Tool descriptions should explain the precise behavior, when to use a sibling tool instead, accepted parameter formats and limits, the return shape, and caveats or failure modes. Give the model enough operational context to select and use the tool correctly. Preserve the service’s authentication and authorization boundaries. Test through MCP Inspector and realistic read-only queries. reference/evaluation.md describes XML test cases and the Codex CLI harness in scripts/evaluation.py; this port does not require Anthropic SDK credentials or route work to Claude.

Follow the host’s instructions and current authorization. Tool names, delegation, models, sandboxing, and question availability come from the running Codex session; this skill does not override them. Resolve helpers from this SKILL.md’s actual directory (SKILL_DIR in examples is a variable you set, not a Codex substitution).
