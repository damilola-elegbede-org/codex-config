#!/usr/bin/env python3
"""Run one command in its own process group with a time limit.

  supervise.py <timeout_s> <timeout-mark-file> -- <command> [args...]

The command gets this process's stdin, stdout and stderr. When it exits, or when the limit passes, every
process still in its group is killed (SIGTERM, then SIGKILL after 2 s). A child
that deliberately creates a separate session can escape this process-group
cleanup; it is not a security sandbox. On timeout a mark file is written
(run.py reads it to set timed_out) and the exit code is 124. Otherwise the exit code is the command's own;
a command killed by a signal exits 128 + the signal number.
"""

import os
import math
import signal
import subprocess
import sys
import time


def kill_group(pgid):
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(pgid, sig)
        except ProcessLookupError:
            return
        except PermissionError:
            return
        deadline = time.time() + 2
        while time.time() < deadline:
            try:
                os.killpg(pgid, 0)
            except (ProcessLookupError, PermissionError):
                return
            time.sleep(0.05)


def main(argv):
    if len(argv) < 5 or argv[3] != "--":
        print(__doc__.strip(), file=sys.stderr)
        return 64
    try:
        limit = float(argv[1])
        if not math.isfinite(limit) or limit <= 0:
            raise ValueError()
    except ValueError:
        print("timeout must be a positive finite number", file=sys.stderr)
        return 64
    mark = argv[2]
    def terminate(signum, _frame):
        raise SystemExit(128 + signum)
    signal.signal(signal.SIGTERM, terminate)
    proc = subprocess.Popen(argv[4:], start_new_session=True)
    timed_out = False
    try:
        try:
            code = proc.wait(timeout=limit)
        except subprocess.TimeoutExpired:
            timed_out = True
            code = None
    finally:
        kill_group(proc.pid)
        proc.wait()
    if timed_out:
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        with open(mark, "w", encoding="utf-8") as f:
            f.write("timeout\n")
        return 124
    return code if code >= 0 else 128 - code


if __name__ == "__main__":
    sys.exit(main(sys.argv))
