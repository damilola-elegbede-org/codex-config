#!/usr/bin/env python3
"""Stage owned native hooks and prepare pinned dependencies before publication.

Existing hook files must match their recorded hash or the incoming source. This
installer never updates native hook trust, prunes withdrawn files, or runs a hook.
"""
import argparse
import ast
from contextlib import contextmanager
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time

_spec = importlib.util.spec_from_file_location("extensions", Path(__file__).with_name("sync-extensions.py"))
_extensions = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_extensions)
safe_path = _extensions.safe_path
atomic_write = _extensions.atomic_write
digest = _extensions.digest
INDEX = ".codex-config-managed-hooks.json"
EVENTS = {"SessionStart", "SessionEnd", "UserPromptSubmit", "PreToolUse", "PostToolUse", "PermissionRequest",
          "PreCompact", "PostCompact", "SubagentStart", "SubagentStop", "Stop", "Interrupt"}


def checked_directory(path):
    safe_path(path.parent, path.name)
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    safe_path(path.parent, path.name)
    if not path.is_dir():
        raise ValueError(f"not a directory: {path}")


@contextmanager
def exclusive_lock(path):
    checked_directory(path.parent)
    safe_path(path.parent, path.name)
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError(f"not a regular lock file: {path}")
        deadline = time.monotonic() + 360
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise ValueError(f"timed out waiting for hook installation lock: {path}")
                time.sleep(0.05)
        yield
    finally:
        os.close(fd)


def validate_hooks(source):
    path = safe_path(source, "hooks.json")
    if not path.is_file() or not safe_path(source, "hooks").is_dir():
        raise ValueError("enabled hooks require hooks.json and hooks/ in the source")
    data = json.loads(path.read_text())
    if not isinstance(data, dict) or set(data) - {"description", "hooks"}:
        raise ValueError("hooks.json must contain native hooks and optional description")
    events = data.get("hooks")
    if not isinstance(events, dict) or not events or set(events) - EVENTS:
        raise ValueError("hooks.json contains no events or unsupported native events")
    for event, groups in events.items():
        if not isinstance(groups, list) or not groups:
            raise ValueError(f"invalid matcher groups for {event}")
        for group in groups:
            if not isinstance(group, dict) or set(group) - {"matcher", "hooks"}:
                raise ValueError(f"invalid matcher group for {event}")
            if "matcher" in group:
                if not isinstance(group["matcher"], str):
                    raise ValueError("hook matcher must be a string")
                if group["matcher"] not in ("", "*"):
                    re.compile(group["matcher"])
            handlers = group.get("hooks")
            if not isinstance(handlers, list) or not handlers:
                raise ValueError(f"missing hook handlers for {event}")
            for handler in handlers:
                allowed = {"type", "command", "timeout", "async", "statusMessage", "additionalContextLimit"}
                if not isinstance(handler, dict) or set(handler) - allowed or handler.get("type") != "command":
                    raise ValueError("only native command hook handlers are shipped")
                if not isinstance(handler.get("command"), str) or not handler["command"].strip():
                    raise ValueError("hook command must be a nonempty string")
                timeout = handler.get("timeout", 600)
                if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 0 < timeout <= 600:
                    raise ValueError("hook timeout must be a positive number up to 600 seconds")
                if event in ("SessionEnd", "Interrupt") and timeout > 3:
                    raise ValueError(f"{event} hook timeout exceeds native three-second limit")
                if "async" in handler and not isinstance(handler["async"], bool):
                    raise ValueError("hook async must be a boolean")
                if "statusMessage" in handler and not isinstance(handler["statusMessage"], str):
                    raise ValueError("hook statusMessage must be a string")
                limit = handler.get("additionalContextLimit", 0)
                if isinstance(limit, bool) or not isinstance(limit, int) or limit < 0:
                    raise ValueError("hook additionalContextLimit must be a nonnegative integer")
                for resource in re.findall(r"/hooks/([A-Za-z0-9_.\-/]+)", handler["command"]):
                    if not safe_path(source / "hooks", resource).is_file():
                        raise ValueError(f"missing referenced hook resource: hooks/{resource}")
                result = subprocess.run(["sh", "-n"], input=handler["command"], text=True, capture_output=True)
                if result.returncode:
                    raise ValueError(f"invalid shell syntax in {event} hook command")
    return len(events)


def node_prerequisite():
    if not shutil.which("node") or not shutil.which("npm"):
        raise ValueError("enabled Jev hooks require Node >=22 and npm")
    result = subprocess.run(["node", "--version"], text=True, capture_output=True, timeout=10)
    match = re.fullmatch(r"v?(\d+)\.\d+\.\d+[^\s]*", result.stdout.strip())
    if result.returncode or not match or int(match[1]) < 22:
        raise ValueError("enabled Jev hooks require Node >=22")


def dependency_plan(staged, target):
    package_path = staged / "hooks/jev/package.json"
    lock_path = staged / "hooks/jev/package-lock.json"
    if not package_path.exists() and not lock_path.exists():
        return None
    package = json.loads(package_path.read_text())
    lock = json.loads(lock_path.read_text())
    version = package.get("dependencies", {}).get("ai")
    if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("Jev must pin an exact ai dependency version")
    entries = lock.get("packages", {})
    if lock.get("lockfileVersion") != 3 or entries.get("", {}).get("dependencies") != package.get("dependencies"):
        raise ValueError("Jev package and lock dependencies do not agree")
    if entries.get("node_modules/ai", {}).get("version") != version:
        raise ValueError("Jev ai lock version does not match package.json")
    for name, entry in entries.items():
        if not name:
            continue
        if (not isinstance(entry, dict) or entry.get("link") or
                not str(entry.get("resolved", "")).startswith("https://registry.npmjs.org/") or
                not str(entry.get("integrity", "")).startswith("sha512-")):
            raise ValueError("Jev lock contains a non-registry or unpinned dependency")
    lock_hash = digest(lock_path)
    cache = safe_path(target, f".codex-config-deps/jev/{lock_hash}")
    node_prerequisite()
    return {"lock_sha256": lock_hash, "package_sha256": digest(package_path), "ai_version": version, "cache": str(cache)}


def stage(args):
    source, target = args.source.absolute(), args.target.absolute()
    events = validate_hooks(source)
    index_path = safe_path(target, INDEX)
    if index_path.exists():
        index = json.loads(index_path.read_text())
        if index.get("version") != 1 or index.get("root") != str(target) or not isinstance(index.get("files"), dict):
            raise ValueError("invalid or mismatched hook ownership index")
    else:
        index = {"version": 1, "root": str(target), "files": {}}
    for name, checksum in index["files"].items():
        if name != "hooks.json" and not name.startswith("hooks/"):
            raise ValueError(f"invalid hook ownership entry: {name}")
        safe_path(target, name)
        if not isinstance(checksum, str) or not re.fullmatch(r"[0-9a-f]{64}", checksum):
            raise ValueError(f"invalid hook ownership hash: {name}")
    args.stage.mkdir(parents=True, exist_ok=True)
    files = []
    for file in [source / "hooks.json", *sorted((source / "hooks").rglob("*"))]:
        relative = file.relative_to(source).as_posix()
        if "__pycache__" in file.parts or "node_modules" in file.parts or file.suffix in (".pyc", ".pyo"):
            continue
        safe_path(source, relative)
        if file.is_dir():
            continue
        checksum = digest(file)
        if checksum is None:
            raise ValueError(f"missing source hook file: {file}")
        destination = safe_path(target, relative)
        expected = digest(destination)
        if expected is not None and expected not in (checksum, index["files"].get(relative)):
            raise ValueError(f"preserving customized or unmanaged hook; sync stopped: {destination}")
        staged = safe_path(args.stage / "files", relative)
        staged.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(file, staged)
        if file.suffix == ".py":
            ast.parse(staged.read_text(), filename=str(file))
        if file.suffix == ".json":
            json.loads(staged.read_text())
        files.append({"relative": relative, "sha256": checksum, "expected": expected,
                      "expected_mode": stat.S_IMODE(destination.stat().st_mode) if expected is not None else None,
                      "mode": stat.S_IMODE(file.stat().st_mode)})
    dependencies = dependency_plan(args.stage / "files", target)
    for file in files:
        source_file = args.stage / "files" / file["relative"]
        if source_file.suffix == ".mjs":
            if not shutil.which("node"):
                raise ValueError("node is required to validate hook JavaScript")
            result = subprocess.run(["node", "--check", str(source_file)], capture_output=True, timeout=10)
            if result.returncode:
                raise ValueError(f"invalid JavaScript hook: {file['relative']}")
        elif source_file.read_bytes().startswith(b"#!/bin/bash"):
            result = subprocess.run(["bash", "-n", str(source_file)], capture_output=True, timeout=10)
            if result.returncode:
                raise ValueError(f"invalid shell hook: {file['relative']}")
    plan = {"root": str(target), "index": index, "index_expected": digest(index_path), "files": files, "dependencies": dependencies}
    (args.stage / "plan.json").write_text(json.dumps(plan))
    print(f"hooks: {events} events, {len(files)} managed files staged; native trust is unchanged")
    if dependencies:
        print(f"Jev dependency cache: {dependencies['cache']} (prepared only on apply)")
    for item in files:
        if item["expected"] != item["sha256"]:
            print(f"would install: {item['relative']}")


def read_plan(args):
    plan = json.loads((args.stage / "plan.json").read_text())
    target = Path(plan["root"])
    if digest(safe_path(target, INDEX)) != plan["index_expected"]:
        raise ValueError("hook ownership index changed after staging")
    for item in plan["files"]:
        relative = item["relative"]
        if digest(safe_path(target, relative)) != item["expected"]:
            raise ValueError(f"hook changed after staging: {relative}")
        if item["expected"] is not None and stat.S_IMODE((target / relative).stat().st_mode) != item["expected_mode"]:
            raise ValueError(f"hook permissions changed after staging: {relative}")
        if digest(safe_path(args.stage / "files", relative)) != item["sha256"]:
            raise ValueError(f"staged hook changed: {relative}")
    return plan


def valid_cache(dependency):
    cache = Path(dependency["cache"])
    safe_path(cache.parent, cache.name)
    if not cache.exists():
        return False
    marker = safe_path(cache, ".complete.json")
    package = safe_path(cache, "package.json")
    lock = safe_path(cache, "package-lock.json")
    installed = safe_path(cache, "node_modules/ai/package.json")
    try:
        data = json.loads(marker.read_text())
        return (data == {"lock_sha256": dependency["lock_sha256"], "ai_version": dependency["ai_version"]}
                and digest(package) == dependency["package_sha256"] and digest(lock) == dependency["lock_sha256"]
                and json.loads(installed.read_text()).get("version") == dependency["ai_version"])
    except (OSError, ValueError):
        return False


def prepare(args):
    plan = read_plan(args)
    dependency = plan["dependencies"]
    if not dependency:
        return
    node_prerequisite()
    cache = Path(dependency["cache"])
    with exclusive_lock(cache.parent / ".install.lock"):
        if valid_cache(dependency):
            print("Jev dependencies: existing pinned cache verified")
            return
        if cache.exists():
            raise ValueError(f"Jev dependency cache is incomplete or modified; preserving it: {cache}")
        temporary = Path(tempfile.mkdtemp(prefix=".install.", dir=cache.parent))
        try:
            for name in ("package.json", "package-lock.json"):
                shutil.copyfile(args.stage / "files/hooks/jev" / name, temporary / name)
            npm_cache = safe_path(cache.parent, ".npm-cache")
            checked_directory(npm_cache)
            userconfig = temporary / ".npmrc"
            userconfig.write_text("")
            env = {**os.environ, "npm_config_cache": str(npm_cache), "npm_config_userconfig": str(userconfig)}
            result = subprocess.run(["npm", "ci", "--omit=dev", "--ignore-scripts", "--no-audit", "--no-fund",
                                     "--registry=https://registry.npmjs.org"],
                                    cwd=temporary, env=env, capture_output=True, timeout=300)
            if result.returncode:
                raise ValueError(f"Jev dependency installation failed (npm exit {result.returncode}); hooks were not published")
            installed = safe_path(temporary, "node_modules/ai/package.json")
            if json.loads(installed.read_text()).get("version") != dependency["ai_version"]:
                raise ValueError("npm did not install the pinned ai version")
            if (digest(temporary / "package.json") != dependency["package_sha256"] or
                    digest(temporary / "package-lock.json") != dependency["lock_sha256"]):
                raise ValueError("Jev package definitions changed during installation")
            marker = {"lock_sha256": dependency["lock_sha256"], "ai_version": dependency["ai_version"]}
            atomic_write(temporary / ".complete.json", json.dumps(marker).encode())
            safe_path(cache.parent, cache.name)
            os.rename(temporary, cache)
            print("Jev dependencies: installed pinned cache with package scripts disabled")
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)


def apply(args):
    plan = read_plan(args)
    target = Path(plan["root"])
    with exclusive_lock(target / ".codex-config-hooks.lock"):
        plan = read_plan(args)
        if plan["dependencies"] and not valid_cache(plan["dependencies"]):
            raise ValueError("Jev dependencies are not prepared; hooks were not published")
        index_path = safe_path(target, INDEX)
        index = plan["index"]
        for item in sorted(plan["files"], key=lambda item: (item["relative"] == "hooks.json", item["relative"])):
            relative = item["relative"]
            destination = safe_path(target, relative)
            if digest(destination) != item["expected"]:
                raise ValueError(f"hook changed during installation: {relative}")
            expected_mode = item["expected_mode"]
            if expected_mode is not None and stat.S_IMODE(destination.stat().st_mode) != expected_mode:
                raise ValueError(f"hook permissions changed during installation: {relative}")
            installed_mode = 0o700 if item["mode"] & stat.S_IXUSR else 0o600
            if item["expected"] != item["sha256"] or expected_mode != installed_mode:
                if args.backup and destination.exists():
                    backup = safe_path(args.backup, relative)
                    atomic_write(backup, destination.read_bytes(), destination.stat().st_mode)
                content = safe_path(args.stage / "files", relative).read_bytes()
                if hashlib.sha256(content).hexdigest() != item["sha256"]:
                    raise ValueError(f"staged hook changed during installation: {relative}")
                atomic_write(destination, content, item["mode"])
            index["files"][relative] = item["sha256"]
        if args.backup and index_path.exists():
            atomic_write(safe_path(args.backup, INDEX), index_path.read_bytes())
        atomic_write(index_path, (json.dumps(index, indent=2) + "\n").encode())
        print(f"installed {len(plan['files'])} managed hook files; new or changed hooks require native trust review")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("stage", "prepare", "apply", "check"))
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--target", type=Path)
    parser.add_argument("--backup", type=Path)
    args = parser.parse_args()
    if args.action == "stage" and (not args.source or not args.target):
        parser.error("stage requires --source and --target")
    try:
        {"stage": stage, "prepare": prepare, "apply": apply, "check": read_plan}[args.action](args)
    except (OSError, ValueError, SyntaxError, TypeError, subprocess.TimeoutExpired) as error:
        parser.exit(2, f"hook sync: {error}\n")


if __name__ == "__main__":
    main()
