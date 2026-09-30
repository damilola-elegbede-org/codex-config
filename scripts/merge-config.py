#!/usr/bin/env python3
"""Replace owned top-level TOML scalar assignments and tables."""
import os
import pathlib
import re
import sys
import tomllib

source = pathlib.Path(sys.argv[1])
destination = pathlib.Path(sys.argv[2])
owned = sys.argv[3:]
allowed = set(os.environ.get("CODEX_CONFIG_ALLOWED_KEYS", " ".join(owned)).split())
header_pattern = re.compile(
    r"^\[\s*(?P<key>\"(?:[^\"\\\\]|\\\\.)*\"|'(?:[^']|'')*'|[A-Za-z0-9_-]+)\s*\]\s*(?:#.*)?$"
)
with source.open("rb") as handle:
    tomllib.load(handle)
for key in owned:
    if "." in key:
        raise SystemExit(f"owned key must be top-level: {key}")

def table_name(line):
    match = header_pattern.match(line.strip())
    if match is None:
        return None
    key = match.group("key")
    if key[0] in "\"'":
        return tomllib.loads(f"key = {key}")["key"]
    return key


assignments = {}
tables = {}
current_table = None
in_source_table = False
for number, line in enumerate(source.read_text().splitlines(), start=1):
    name = table_name(line)
    if name is not None:
        if name not in allowed:
            raise SystemExit(f"{source}:{number}: unowned top-level table {name}")
        current_table = name if name in owned else None
        in_source_table = True
        if current_table is not None:
            tables[current_table] = [line]
        continue
    if line.strip().startswith("["):
        current_table = None
        in_source_table = True
        continue
    if current_table is not None:
        tables[current_table].append(line)
        continue
    if in_source_table:
        continue
    stripped = line.strip()
    if "=" in stripped and not stripped.startswith("#"):
        key = stripped.split("=", 1)[0].strip()
        if key not in allowed:
            raise SystemExit(f"{source}:{number}: unowned top-level key {key}")
        if key in owned:
            assignments[key] = line

lines = destination.read_text().splitlines() if destination.exists() else []
destination_tables = {name for line in lines if (name := table_name(line)) is not None}
result = []
seen_scalars = set()
seen_tables = set()
in_table = False
skipping_owned_table = False
inserted_missing = False


def insert_missing():
    for key in owned:
        if key not in seen_scalars and key in assignments:
            result.append(assignments[key])
    for key in owned:
        if key not in seen_tables and key not in destination_tables and key in tables:
            result.extend(tables[key])


for line in lines:
    name = table_name(line)
    if name is not None:
        if not inserted_missing:
            insert_missing()
            inserted_missing = True
        in_table = True
        skipping_owned_table = name in owned
        if skipping_owned_table:
            seen_tables.add(name)
            if name in tables:
                result.extend(tables[name])
            continue
        result.append(line)
        continue
    if line.strip().startswith("["):
        if not inserted_missing:
            insert_missing()
            inserted_missing = True
        in_table = True
        skipping_owned_table = False
        result.append(line)
        continue
    if skipping_owned_table:
        continue
    stripped = line.strip()
    if not in_table and "=" in stripped and not stripped.startswith("#"):
        key = stripped.split("=", 1)[0].strip()
        if key in owned:
            seen_scalars.add(key)
            if key in assignments:
                result.append(assignments[key])
            continue
    result.append(line)
if not inserted_missing:
    insert_missing()

destination.write_text("\n".join(result) + ("\n" if result else ""))
