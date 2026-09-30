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


def dotted_assignment_path(line):
    stripped = line.strip()
    if "=" not in stripped or stripped.startswith("#"):
        return None
    key = stripped.split("=", 1)[0].strip()
    if "." not in key:
        return None
    try:
        value = tomllib.loads(f"{key} = 0")
    except tomllib.TOMLDecodeError:
        return None
    path = []
    while isinstance(value, dict) and len(value) == 1:
        key, value = next(iter(value.items()))
        path.append(key)
    return tuple(path) if path else None


def assignment_value_span(lines, index):
    """Physical line count of the value at lines[index] (`key = value...`).

    Trial-parses progressively longer joins to find where a multi-line array
    or multi-line string closes, so callers can remove or pass through the
    whole value instead of only its opening line.
    """
    first = lines[index]
    tail = first[first.index("=") + 1 :]
    end = index
    while True:
        try:
            tomllib.loads(f"v = {tail}")
            return end - index + 1
        except tomllib.TOMLDecodeError:
            if end + 1 >= len(lines):
                return 1
            end += 1
            tail = f"{tail}\n{lines[end]}"


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

def continuation_line_indices(lines):
    """Indices of lines that are the 2nd+ physical line of a top-level
    multi-line value (array or string), so a naive line scan never mistakes
    a value's body text for a real table header or assignment."""
    skip = set()
    in_table = False
    index = 0
    while index < len(lines):
        line = lines[index]
        if index in skip:
            index += 1
            continue
        if table_name(line) is not None or line.strip().startswith("["):
            in_table = True
            index += 1
            continue
        stripped = line.strip()
        if not in_table and "=" in stripped and not stripped.startswith("#"):
            span = assignment_value_span(lines, index)
            skip.update(range(index + 1, index + span))
            index += span
            continue
        index += 1
    return skip


lines = destination.read_text().splitlines() if destination.exists() else []
value_continuation_lines = continuation_line_indices(lines)
destination_tables = {
    name
    for i, line in enumerate(lines)
    if i not in value_continuation_lines and (name := table_name(line)) is not None
}
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


index = 0
while index < len(lines):
    line = lines[index]
    dotted_path = dotted_assignment_path(line)
    if not in_table and dotted_path is not None and dotted_path[0] in owned:
        if len(dotted_path) == 2:
            index += assignment_value_span(lines, index)
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
            index += 1
            continue
        result.append(line)
        index += 1
        continue
    if line.strip().startswith("["):
        if not inserted_missing:
            insert_missing()
            inserted_missing = True
        in_table = True
        skipping_owned_table = False
        result.append(line)
        index += 1
        continue
    if skipping_owned_table:
        index += 1
        continue
    stripped = line.strip()
    if not in_table and "=" in stripped and not stripped.startswith("#"):
        key = stripped.split("=", 1)[0].strip()
        span = assignment_value_span(lines, index)
        if key in owned:
            seen_scalars.add(key)
            if key in assignments:
                result.append(assignments[key])
        else:
            result.extend(lines[index : index + span])
        index += span
        continue
    result.append(line)
    index += 1
if not inserted_missing:
    insert_missing()

destination.write_text("\n".join(result) + ("\n" if result else ""))
