#!/usr/bin/env python3
"""Validate repository-authored skill metadata and native standalone agents.

Skills use JSON scalars in YAML frontmatter so validation needs only stdlib.
This intentionally validates our source contract, not arbitrary third-party YAML.
"""
import argparse
import json
import re
import tomllib
from pathlib import Path


def validate(skills: Path, agents: Path) -> tuple[int, int]:
    skill_count = agent_count = 0
    if skills.exists():
        for entry in skills.iterdir():
            if entry.name == "README.md" and entry.is_file():
                continue
            if not entry.is_dir():
                raise ValueError(f"unexpected skill-root file: {entry}")
            path = entry / "SKILL.md"
            if not path.exists():
                if entry.name == "office-common":
                    continue
                raise ValueError(f"missing SKILL.md: {entry}")
            parts = path.read_text(encoding="utf-8").split("---\n", 2)
            if len(parts) != 3 or parts[0]:
                raise ValueError(f"invalid frontmatter: {path}")
            fields = {}
            for line in parts[1].splitlines():
                key, separator, value = line.partition(": ")
                if not separator or key in fields:
                    raise ValueError(f"frontmatter must use unique JSON scalars: {path}")
                fields[key] = json.loads(value)
            if fields.get("name") != entry.name or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", entry.name):
                raise ValueError(f"invalid skill name: {path}")
            if not isinstance(fields.get("description"), str) or not fields["description"].strip():
                raise ValueError(f"missing description: {path}")
            if set(fields) - {"name", "description", "license", "metadata"}:
                raise ValueError(f"unsupported frontmatter: {path}")
            if not parts[2].strip():
                raise ValueError(f"empty skill instructions: {path}")
            skill_count += 1
    if agents.exists():
        for path in agents.iterdir():
            if path.suffix != ".toml" or not path.is_file():
                raise ValueError(f"unexpected agent entry: {path}")
            agent = tomllib.loads(path.read_text(encoding="utf-8"))
            for key in ("name", "description", "developer_instructions"):
                if not isinstance(agent.get(key), str) or not agent[key].strip():
                    raise ValueError(f"missing {key}: {path}")
            if agent["name"] != path.stem:
                raise ValueError(f"agent name must match filename: {path}")
            if set(agent) - {"name", "description", "developer_instructions", "sandbox_mode"}:
                raise ValueError(f"unsupported repository agent setting: {path}")
            if "sandbox_mode" in agent and agent["sandbox_mode"] != "read-only":
                raise ValueError(f"agent must inherit permissions or restrict to read-only: {path}")
            agent_count += 1
    return skill_count, agent_count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skills", type=Path)
    parser.add_argument("agents", type=Path)
    args = parser.parse_args()
    try:
        counts = validate(args.skills, args.agents)
        print(f"validated {counts[0]} skills and {counts[1]} agents")
    except (ValueError, OSError) as error:
        parser.exit(1, f"extension validation: {error}\n")
