#!/usr/bin/env python3
"""Local relevance ranking. No external model, telemetry, or network access."""
import argparse
import json
import re
from pathlib import Path

EXCLUDED = {"node_modules", "vendor", "dist", "build", ".git", ".credentials", "credentials", "work", "visa"}


def rank(query, paths):
    terms = set(re.findall(r"[a-z0-9_]{2,}", query.lower()))
    found = []
    for name in paths:
        path = Path(name)
        parts = set(part.lower() for part in path.resolve().parts)
        if parts & EXCLUDED or re.search(r"(^\.env|secret|token|credential|auth\.json|\.(pem|key)$)", path.name, re.I):
            continue
        try:
            if path.is_symlink() or not path.is_file() or path.stat().st_size > 256_000:
                continue
            data = path.read_bytes()
            if b"\0" in data:
                continue
            content = data.decode("utf-8").lower()
        except (OSError, UnicodeError):
            continue
        score = sum(8 * (term in str(path).lower()) + min(content.count(term), 20) for term in terms)
        found.append({"path": str(path), "score": score})
    return sorted(found, key=lambda item: (-item["score"], item["path"]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--top", type=int, default=8)
    parser.add_argument("query")
    parser.add_argument("paths", nargs="+")
    args = parser.parse_args()
    if args.top < 1:
        parser.error("--top must be positive")
    results = rank(args.query, args.paths)[:args.top]
    print(json.dumps(results, indent=2))
    return 0 if results else 1


if __name__ == "__main__":
    raise SystemExit(main())
