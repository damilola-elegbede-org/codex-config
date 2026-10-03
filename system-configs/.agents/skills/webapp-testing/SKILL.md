---
name: "webapp-testing"
description: "Test local web applications with Playwright, screenshots, DOM inspection, console logs, and reproducible interaction steps."
license: "Complete terms in LICENSE.txt"
metadata: {"source-repository": "damilola-elegbede-org/claude-config", "source-commit": "cb257acb72ef568efc5d9dc2c25c365b179383b0", "source-path": "system-configs/.claude/skills/webapp-testing/SKILL.md"}
---

# webapp-testing

Read guide.md and the relevant examples/. Resolve scripts/with_server.py relative to this skill directory; its --help explains server lifecycle and multiple-server support. Inspect rendered state before choosing selectors; prefer role/label locators and wait for a specific readiness condition rather than unbounded network-idle on streaming apps. Close only browsers/servers started by this run. A failed interaction is evidence, not permission to change product code. Do not submit live forms or mutate external accounts outside the requested test scope. The original Jev click-picker is replaced by direct DOM inspection; it does not require Claude hooks.

Follow the host’s instructions and current authorization. Tool names, delegation, models, sandboxing, and question availability come from the running Codex session; this skill does not override them. Resolve helpers from this SKILL.md’s actual directory (SKILL_DIR in examples is a variable you set, not a Codex substitution).
