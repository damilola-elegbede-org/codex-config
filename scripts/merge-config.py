#!/usr/bin/env python3
"""Replace owned top-level TOML scalar assignments and tables."""
import json
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
    """Return the decoded name of a root table header, if present."""
    match = header_pattern.match(line.strip())
    if match is None:
        return None
    key = match.group("key")
    if key[0] in "\"'":
        return tomllib.loads(f"key = {key}")["key"]
    return key


def assignment_parts(line):
    """Split at the assignment delimiter, not an equals sign in a quoted key."""
    quote = None
    escaped = False
    for index, char in enumerate(line):
        if escaped:
            escaped = False
        elif quote == '"' and char == "\\":
            escaped = True
        elif quote:
            if char == quote:
                quote = None
        elif char in "\"'":
            quote = char
        elif char == "=":
            return line[:index].strip(), line[index + 1:]
    return None


def dotted_assignment_path(line):
    """Decode the path of a TOML assignment, including quoted keys."""
    stripped = line.strip()
    if "=" not in stripped or stripped.startswith("#"):
        return None
    parts = assignment_parts(stripped)
    if parts is None:
        return None
    key = parts[0]
    try:
        value = tomllib.loads(f"{key} = 0")
    except tomllib.TOMLDecodeError:
        return None
    path = []
    while isinstance(value, dict) and len(value) == 1:
        key, value = next(iter(value.items()))
        path.append(key)
    return tuple(path) if path else None


def statements(lines):
    """Group complete TOML assignments so multiline values stay intact."""
    pending = []
    for line in lines:
        if pending:
            pending.append(line)
        elif "=" in line and not line.lstrip().startswith(("#", "[")):
            pending.append(line)
        else:
            yield line
            continue
        statement = "\n".join(pending)
        try:
            tomllib.loads(statement)
        except tomllib.TOMLDecodeError:
            continue
        yield statement
        pending = []
    if pending:
        raise SystemExit("incomplete or invalid TOML assignment")


assignments = {}
tables = {}
current_table = None
in_source_table = False
for number, line in enumerate(statements(source.read_text().splitlines()), start=1):
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
        key = dotted_assignment_path(line)[0]
        if key not in allowed:
            raise SystemExit(f"{source}:{number}: unowned top-level key {key}")
        if key in owned:
            assignments[key] = line

lines = list(statements(destination.read_text().splitlines())) if destination.exists() else []
destination_tables = {name for line in lines if (name := table_name(line)) is not None}
root_nested = {}
at_root = True
for line in lines:
    if line.lstrip().startswith("["):
        at_root = False
    path = dotted_assignment_path(line) if at_root else None
    if path and len(path) >= 2 and path[0] in tables:
        value = tomllib.loads(line)
        for part in path:
            value = value[part]
        if len(path) == 2 and not isinstance(value, dict):
            continue
        relative_key = ".".join(json.dumps(part, ensure_ascii=False) for part in path[1:])
        root_nested.setdefault(path[0], []).append(
            relative_key + " =" + assignment_parts(line)[1]
        )
for name, nested in root_nested.items():
    tables[name].extend(nested)
result = []
seen_scalars = set()
seen_tables = set()
in_table = False
skipping_owned_table = False
inserted_missing = False


def insert_missing():
    """Insert absent owned entries before destination table declarations."""
    for key in owned:
        if key not in seen_scalars and key in assignments:
            result.append(assignments[key])
    for key in owned:
        if key not in seen_tables and key not in destination_tables and key in tables:
            result.extend(tables[key])


for line in lines:
    dotted_path = dotted_assignment_path(line)
    if not in_table and dotted_path is not None and dotted_path[0] in owned:
        if len(dotted_path) == 2 or dotted_path[0] in root_nested:
            continue
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
        key = dotted_path[0] if dotted_path and len(dotted_path) == 1 else stripped.split("=", 1)[0].strip()
        if key in owned:
            seen_scalars.add(key)
            if key in assignments:
                result.append(assignments[key])
            continue
    result.append(line)
if not inserted_missing:
    insert_missing()

destination.write_text("\n".join(result) + ("\n" if result else ""))
