#!/usr/bin/env python3
"""Execute reviewed local trials, or record observations made through host tools.

run.py DIR --execute-local
run.py DIR --record CONDITION REP JSON_VALUE --evidence RELATIVE_PATH

Scratch directories and a clean environment are not a security sandbox. The
caller reviews commands under the user's existing scope and host permissions.
No command executes without --execute-local; external trials are recorded only.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import time

from score import ExpError, check_lock, load_json, read_rows, validate


def timestamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def append(directory, row):
    with (directory / "runs.jsonl").open("a", encoding="utf-8") as out:
        out.write(json.dumps(row, allow_nan=False) + "\n")


def run_command(command, out, err, mark, limit, environment, cwd):
    with out.open("w", encoding="utf-8") as stdout, err.open("w", encoding="utf-8") as stderr:
        proc = subprocess.run(
            [sys.executable, str(Path(__file__).with_name("supervise.py")),
             str(limit), str(mark), "--", "bash", "--noprofile", "--norc", "-c", command],
            stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, cwd=cwd, env=environment,
            check=False,
        )
    return proc.returncode, mark.exists()


def execute(directory, plan, existing):
    start = time.monotonic()
    spent = sum(r.get("secs", 0) for r in read_rows(directory)
                if isinstance(r.get("secs", 0), (int, float)) and r.get("secs", 0) >= 0)
    work, home, outputs = (directory / name for name in ("work", "home", "runs"))
    for path in (work, home, outputs):
        if path.is_symlink():
            raise ExpError(f"refused linked working directory: {path}")
        path.mkdir(exist_ok=True)
    env = {key: os.environ[key] for key in ("PATH", "LANG", "LC_ALL", "TZ") if key in os.environ}
    env.update({"HOME": str(home), "TMPDIR": str(work), "EXPERIMENT_DIR": str(directory),
                "EXPERIMENT_WORK": str(work), "EXPERIMENT_HOME": str(home)})
    count = 0
    for rep in range(1, plan["reps"] + 1):
        conditions = list(plan["conditions"])
        random.Random(plan.get("seed", 1) * 1000003 + rep).shuffle(conditions)
        for condition in conditions:
            name = condition["name"]
            if (name, rep) in existing:
                continue
            remaining = plan["budget_s"] - spent - (time.monotonic() - start)
            if remaining <= 0:
                print(f"budget exhausted; wrote {count} rows; unrun trials remain missing")
                return 2
            check_lock(directory)
            environment = {**env, "EXPERIMENT_CONDITION": name, "EXPERIMENT_REP": str(rep)}
            out, err, mark = (outputs / f"{name}-{rep}.{suffix}" for suffix in ("out", "err", "timeout"))
            mark.unlink(missing_ok=True)
            began = time.monotonic()
            row = {"condition": name, "rep": rep, "started": timestamp(), "source": "run.py"}
            code, timed_out = run_command(condition["cmd"], out, err, mark,
                                          min(plan.get("timeout_s", 120), remaining), environment, work)
            observer = condition.get("observe")
            value, error = code == 0, None
            if observer == "judge":
                value = None
            elif observer is not None:
                remaining = plan["budget_s"] - spent - (time.monotonic() - start)
                obsout, obserr, obsmark = (outputs / f"{name}-{rep}.observe.{suffix}"
                                          for suffix in ("out", "err", "timeout"))
                obsmark.unlink(missing_ok=True)
                if remaining <= 0:
                    value, error = None, "budget exhausted before observation"
                else:
                    obsenv = {**environment, "RUN_OUT": str(out), "RUN_ERR": str(err), "RUN_EXIT": str(code)}
                    obs_code, obs_timed_out = run_command(observer, obsout, obserr, obsmark,
                                                          min(60, remaining), obsenv, work)
                    if obs_timed_out or obs_code != 0:
                        value = None
                        error = "observe timed out" if obs_timed_out else f"observe exited {obs_code}"
                    else:
                        observation = obsout.read_text(encoding="utf-8", errors="replace").strip()
                        if not observation:
                            value, error = None, "observe produced empty output"
                        else:
                            try:
                                value = json.loads(observation)
                                json.dumps(value, allow_nan=False)
                            except (ValueError, TypeError):
                                value = observation
            row.update({"exit": code, "timed_out": timed_out, "value": value,
                        "secs": round(time.monotonic() - began, 3),
                        "stdout": str(out.relative_to(directory)), "stderr": str(err.relative_to(directory)),
                        "stdout_sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
                        "stderr_sha256": hashlib.sha256(err.read_bytes()).hexdigest()})
            if error:
                row["error"] = error
            append(directory, row)
            count += 1
    print(f"ran {count}; skipped {len(existing)} recorded pairs; rows in {directory / 'runs.jsonl'}")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--execute-local", action="store_true")
    mode.add_argument("--record", nargs=3, metavar=("CONDITION", "REP", "JSON_VALUE"))
    parser.add_argument("--evidence", help="existing file inside the experiment recording the observed outcome")
    args = parser.parse_args()
    directory = args.directory.resolve()
    errors = validate(directory)
    if errors:
        raise ExpError("; ".join(errors))
    check_lock(directory)
    lockdir = directory / ".runner-lock"
    try:
        lockdir.mkdir()
    except FileExistsError:
        raise ExpError("another runner holds .runner-lock; verify it stopped before removing a stale lock")
    try:
        check_lock(directory)
        plan = load_json(directory / "plan.json")
        side = load_json(directory / "lock.json").get("side_effects")
        if side == "refuse":
            raise ExpError("protocol forbids execution and recording")
        rows = read_rows(directory)
        existing = {(r.get("condition"), r.get("rep")) for r in rows}
        if args.record:
            name, rep_text, raw = args.record
            try:
                rep = int(rep_text)
                value = json.loads(raw)
                json.dumps(value, allow_nan=False)
            except (ValueError, TypeError):
                raise ExpError("record requires an integer repetition and finite JSON value")
            if name not in {c["name"] for c in plan["conditions"]} or not 1 <= rep <= plan["reps"]:
                raise ExpError("condition and repetition must be in the locked plan")
            if (name, rep) in existing:
                raise ExpError("condition/repetition already recorded")
            if not args.evidence:
                raise ExpError("manual observations require --evidence pointing to their actual evidence")
            evidence = (directory / args.evidence).resolve()
            if not evidence.is_relative_to(directory) or not evidence.is_file():
                raise ExpError("evidence must be an existing file inside the experiment")
            append(directory, {"condition": name, "rep": rep, "value": value,
                               "started": timestamp(), "source": "manual",
                               "evidence": str(evidence.relative_to(directory)),
                               "evidence_sha256": hashlib.sha256(evidence.read_bytes()).hexdigest()})
            print(f"recorded {name} rep {rep}")
            return 0
        if side != "local":
            raise ExpError("external trials must use authorized host tools and --record; nothing executed")
        return execute(directory, plan, existing)
    finally:
        lockdir.rmdir()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ExpError, OSError) as error:
        print(f"refused: {error}", file=sys.stderr)
        sys.exit(3)
