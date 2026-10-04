#!/usr/bin/env python3
"""Check basic ZIP/XML integrity of a DOCX, PPTX, or XLSX without extraction.

This is not OOXML schema, formula, visual, or application compatibility validation.
"""
import argparse
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath

CORE = {".docx": "word/document.xml", ".pptx": "ppt/presentation.xml", ".xlsx": "xl/workbook.xml"}


def check(path):
    if path.suffix.lower() not in CORE:
        raise ValueError("expected .docx, .pptx, or .xlsx")
    with zipfile.ZipFile(path) as package:
        entries = package.infolist()
        names = [entry.filename for entry in entries]
        if len(names) != len(set(names)):
            raise ValueError("duplicate ZIP entries")
        required = {"[Content_Types].xml", "_rels/.rels", CORE[path.suffix.lower()]}
        if not required.issubset(names):
            raise ValueError(f"missing core package entries: {sorted(required - set(names))}")
        if sum(entry.file_size for entry in entries) > 256_000_000:
            raise ValueError("package exceeds 256 MB uncompressed check limit")
        for entry in entries:
            if ".." in PurePosixPath(entry.filename).parts or entry.filename.startswith(("/", "\\")):
                raise ValueError("unsafe package entry name")
            if entry.filename.endswith((".xml", ".rels")):
                data = package.read(entry)
                if b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
                    raise ValueError("DTD/entity definitions are not supported")
                ET.fromstring(data)
        bad = package.testzip()
        if bad:
            raise ValueError(f"CRC failure: {bad}")
    return len(entries)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    args = parser.parse_args()
    try:
        count = check(args.file)
        print(f"ZIP/XML integrity checked: {count} entries; application/layout checks still required")
    except (OSError, ValueError, zipfile.BadZipFile, ET.ParseError, RuntimeError) as error:
        parser.exit(1, f"package check: {error}\n")


if __name__ == "__main__":
    main()
