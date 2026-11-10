#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
command -v node >/dev/null 2>&1 || { echo "node is required for verification-runner tests" >&2; exit 1; }
mkdir -p "$ROOT/.tmp"
VERIFY_TEST_ROOT="$ROOT" python3 - <<'PY'
import json
import os
from pathlib import Path
import subprocess
import tempfile

root = Path(os.environ["VERIFY_TEST_ROOT"])
runner = root / "system-configs/.agents/skills/verify/scripts/run-checks.mjs"
with tempfile.TemporaryDirectory(prefix="verify-gates-", dir=root / ".tmp") as temporary:
    work = Path(temporary)

    def project(name, scripts=None, config=False, lock=None):
        path = work / name
        path.mkdir()
        if scripts is not None:
            (path / "package.json").write_text(json.dumps({"scripts": scripts}))
        if config:
            (path / ".markdownlint.json").write_text("{}")
        if lock:
            (path / lock).touch()
        return path

    def gates(path):
        result = subprocess.run(
            ["node", str(runner), "--list", "--json", "--dir", str(path)],
            check=True, capture_output=True, text=True,
        )
        return json.loads(result.stdout)["checks"]

    preferred = project("preferred", {"lint:markdown": "custom-scoped-lint", "lint:md": "alternate"}, config=True)
    [gate] = gates(preferred)
    assert gate["id"] == "markdownlint"
    assert [gate["cmd"], *gate["args"]] == ["npm", "run", "lint:markdown"], gate

    for manager, lock in [("pnpm", "pnpm-lock.yaml"), ("yarn", "yarn.lock")]:
        path = project(manager, {"lint:md": "custom-scoped-lint"}, lock=lock)
        [gate] = gates(path)
        assert [gate["cmd"], *gate["args"]] == [manager, "run", "lint:md"], gate

    fallback = project("config-only", config=True)
    [gate] = gates(fallback)
    assert gate["cmd"] == "npx", gate
    for excluded in ("#**/node_modules", "#.claude/worktrees", "#.tmp"):
        assert excluded in gate["args"], gate
    assert gates(project("no-markdown")) == []

    # Exercise the selected command and its exit status without running npm or
    # fetching a linter. A configured lint failure must remain a failed gate.
    binary = work / "bin"
    binary.mkdir()
    shim = binary / "npm"
    shim.write_text('#!/bin/sh\n[ "$1" = run ] && [ "$2" = lint:markdown ] || exit 91\nprintf "scoped lint ran\\n"\nexit "${FIXTURE_LINT_EXIT:-0}"\n')
    shim.chmod(0o700)
    env = {**os.environ, "PATH": str(binary) + os.pathsep + os.environ["PATH"]}
    for code, verdict in [("0", "pass"), ("7", "fail")]:
        result = subprocess.run(
            ["node", str(runner), "--json", "--only", "markdownlint", "--dir", str(preferred)],
            capture_output=True, text=True, env={**env, "FIXTURE_LINT_EXIT": code},
        )
        report = json.loads(result.stdout)
        assert report["verdict"] == verdict, report
        assert report["checks"][0]["exitCode"] == int(code), report
        assert "scoped lint ran" in report["checks"][0]["output"], report
        assert result.returncode == (0 if code == "0" else 1), result

print("PASS: verification uses scoped Markdown commands, fallback exclusions, and real exit status")
PY
