#!/usr/bin/env python3
"""Stage and install owned skills/agents without replacing local custom files.

No pruning: withdrawn extensions remain installed until explicitly retired.
The ownership index stores target roots and hashes, never credentials or content.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import stat
import sys
import tempfile
from pathlib import Path, PurePosixPath

INDEX = ".codex-config-managed-extensions.json"


def digest(path):
    if not path.exists():
        return None
    if not path.is_file():
        raise ValueError(f"not a regular file: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_path(root, relative):
    parts = PurePosixPath(relative).parts
    if not parts or relative != str(PurePosixPath(relative)) or any(p in ("..", ".") for p in parts) or relative.startswith("/"):
        raise ValueError(f"unsafe extension path: {relative}")
    path = Path(root) / relative
    for parent in (path, *path.parents):
        if parent.is_symlink():
            # macOS exposes these system directories through fixed /private aliases.
            if sys.platform == "darwin" and str(parent) in ("/tmp", "/var", "/etc") and parent.resolve() == Path("/private") / parent.name:
                continue
            raise ValueError(f"symlink in extension path: {parent}")
    return path


def atomic_write(path, content, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def load_index(path, roots):
    if not path.exists():
        return {"version": 1, "roots": roots, "files": {}}
    value = json.loads(path.read_text())
    if value.get("version") != 1 or value.get("roots") != roots or not isinstance(value.get("files"), dict):
        raise ValueError(f"invalid or mismatched ownership index: {path}")
    for key, checksum in value["files"].items():
        kind, separator, relative = key.partition("/")
        if kind not in roots or not separator or not isinstance(checksum, str) or len(checksum) != 64:
            raise ValueError(f"invalid ownership entry: {key}")
        safe_path(roots[kind], relative)
    return value


def stage(args):
    roots = {"skills": str(args.skills_target.absolute()), "agents": str(args.agents_target.absolute())}
    index_path = safe_path(args.agents_target.parent, INDEX)
    index = load_index(index_path, roots)
    files = []
    for kind, source, enabled in (("skills", args.skills_source, args.skills), ("agents", args.agents_source, args.agents)):
        if not enabled or not source.exists():
            continue
        for file in sorted(source.rglob("*")):
            if "__pycache__" in file.parts or file.suffix in (".pyc", ".pyo"):
                continue
            if file.is_symlink():
                raise ValueError(f"source symlink is not supported: {file}")
            if file.is_dir():
                continue
            relative = file.relative_to(source).as_posix()
            target = safe_path(roots[kind], relative)
            expected = digest(target)
            checksum = digest(file)
            key = f"{kind}/{relative}"
            if expected is not None and expected not in (checksum, index["files"].get(key)):
                raise ValueError(f"preserving customized or unmanaged extension; sync stopped: {target}")
            staged = safe_path(args.stage / kind, relative)
            staged.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(file, staged)
            files.append({"key": key, "relative": relative, "kind": kind, "expected": expected,
                          "sha256": checksum, "mode": stat.S_IMODE(file.stat().st_mode)})
    spec = importlib.util.spec_from_file_location("validator", Path(__file__).with_name("validate-extensions.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    counts = module.validate(args.stage / "skills", args.stage / "agents")
    plan = {"roots": roots, "files": files, "index": index, "index_expected": digest(index_path)}
    (args.stage / "plan.json").write_text(json.dumps(plan))
    print(f"extensions: {counts[0]} skills, {counts[1]} agents, {len(files)} resource files staged")
    for file in files:
        if file["expected"] != file["sha256"]:
            print(f"would install: {file['key']}")


def apply(args):
    plan = json.loads((args.stage / "plan.json").read_text())
    roots = plan["roots"]
    index_path = safe_path(Path(roots["agents"]).parent, INDEX)
    if digest(index_path) != plan["index_expected"]:
        raise ValueError("ownership index changed after staging")
    # Check all inputs and targets before changing anything. Check again per write.
    for file in plan["files"]:
        target = safe_path(roots[file["kind"]], file["relative"])
        source = safe_path(args.stage / file["kind"], file["relative"])
        if digest(target) != file["expected"] or digest(source) != file["sha256"]:
            raise ValueError(f"extension changed after staging: {target}")
    index = plan["index"]
    # Supporting resources precede discovery entrypoints.
    ordered = sorted(plan["files"], key=lambda item: (item["kind"] == "agents", item["relative"].endswith("SKILL.md"), item["key"]))
    for file in ordered:
        target = safe_path(roots[file["kind"]], file["relative"])
        if digest(target) != file["expected"]:
            raise ValueError(f"extension changed during installation: {target}")
        if file["expected"] != file["sha256"]:
            if args.backup and target.exists():
                backup = safe_path(args.backup / "extensions" / file["kind"], file["relative"])
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(target, backup)
            source = safe_path(args.stage / file["kind"], file["relative"])
            atomic_write(target, source.read_bytes(), file["mode"])
        index["files"][file["key"]] = file["sha256"]
    if not plan["files"]:
        return
    if args.backup and index_path.exists():
        backup = args.backup / INDEX
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(index_path, backup)
    atomic_write(index_path, (json.dumps(index, indent=2) + "\n").encode())
    print(f"installed {len(plan['files'])} managed extension files")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("stage", "apply"))
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--skills-source", type=Path)
    parser.add_argument("--agents-source", type=Path)
    parser.add_argument("--skills-target", type=Path)
    parser.add_argument("--agents-target", type=Path)
    parser.add_argument("--skills", action="store_true")
    parser.add_argument("--agents", action="store_true")
    parser.add_argument("--backup", type=Path)
    args = parser.parse_args()
    try:
        if args.mode == "stage" and any(value is None for value in (args.skills_source, args.agents_source, args.skills_target, args.agents_target)):
            parser.error("stage requires source and target roots")
        (stage if args.mode == "stage" else apply)(args)
    except (OSError, ValueError) as error:
        parser.exit(2, f"extension sync: {error}\n")


if __name__ == "__main__":
    main()
