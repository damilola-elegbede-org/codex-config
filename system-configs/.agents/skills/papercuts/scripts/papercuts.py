#!/usr/bin/env python3
"""Read explicitly supplied papercut logs; report counts and attribution evidence."""
import argparse
import datetime as dt
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


def read_entries(path):
    entries = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        fields = line.split(" · ")
        if len(fields) < 5:
            continue
        try:
            date = dt.date.fromisoformat(fields[0])
        except ValueError:
            continue
        entries.append({"id": f"{path}:{number}", "date": date.isoformat(),
                        "source": fields[1], "symptom": fields[2],
                        "fix": " · ".join(fields[3:-1]), "project": fields[-1]})
    return entries


def attribute(entry, repo):
    roots = [repo / "system-configs/.agents/skills", repo / ".agents/skills"]
    names = [entry["source"]]
    names += re.findall(r"(?:^|\s)[/$]([a-z][a-z0-9-]+)\b", entry["symptom"])
    for name in names:
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
            continue
        for root in roots:
            path = root / name / "SKILL.md"
            if path.is_file():
                return "repo-skill-mentioned", f"{path.relative_to(repo)}:1"
    project = entry["project"].strip()
    if project == repo.name or project == str(repo) or project.startswith(str(repo) + "/"):
        return "repo-unverified", "project matches; causation not established"
    return "unattributed", "no shipped-skill evidence"


def report(log, repo, days, today, archive_dir=None):
    if days < 1:
        raise ValueError("--days must be positive")
    if not log.is_file():
        raise ValueError(f"log does not exist: {log}")
    if not repo.is_dir():
        raise ValueError(f"repository directory does not exist: {repo}")
    if archive_dir is not None and not archive_dir.is_dir():
        raise ValueError(f"archive directory does not exist: {archive_dir}")
    paths = sorted(archive_dir.glob("*.md")) if archive_dir else []
    paths.append(log)
    rows, seen = [], set()
    for path in paths:
        for entry in read_entries(path):
            key = tuple(entry[k] for k in ("date", "source", "symptom", "fix", "project"))
            if key not in seen:
                seen.add(key)
                rows.append(entry)
    if not rows:
        raise ValueError("no supported dated rows; expected YYYY-MM-DD · source · symptom · fix · project")
    since = today - dt.timedelta(days=days - 1)
    window = []
    repeats = defaultdict(list)
    for entry in rows:
        entry["owner"], entry["evidence"] = attribute(entry, repo)
        entry["in_window"] = since.isoformat() <= entry["date"] <= today.isoformat()
        if entry["in_window"]:
            window.append(entry)
        repeats[(entry["source"], " ".join(entry["symptom"].casefold().split()))].append(entry)
    repeated = [{"source": key[0], "symptom": hits[0]["symptom"], "count": len(hits),
                 "entries": [entry["id"] for entry in hits],
                 "in_window": sum(entry["in_window"] for entry in hits)}
                for key, hits in repeats.items() if len(hits) > 1 and any(e["in_window"] for e in hits)]
    repeated.sort(key=lambda item: (-item["in_window"], -item["count"], item["source"]))
    return {"window": {"since": since.isoformat(), "today": today.isoformat(), "days": days},
            "totals": {"log": len(rows), "window": len(window),
                       "by_owner": dict(Counter(e["owner"] for e in window))},
            "entries": window, "repeated_symptoms": repeated,
            "fix_status": "unverified; inspect the fixing change and subsequent evidence"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--archive-dir", type=Path)
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--today", type=dt.date.fromisoformat,
                        default=dt.datetime.now(dt.timezone.utc).date())
    args = parser.parse_args()
    try:
        result = report(args.log, args.repo, args.days, args.today, args.archive_dir)
    except (OSError, ValueError) as error:
        print(json.dumps({"error": str(error)}))
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
