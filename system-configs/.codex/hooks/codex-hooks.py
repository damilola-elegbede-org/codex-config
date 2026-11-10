#!/usr/bin/env python3
"""Native Codex hooks. Policy checks are deterministic; Jev supplies advice only.

No transcript parsing, shell eval, output replacement, permission inference, or
Stop continuation. Installed scripts are reviewed through Codex's hook trust UI.
"""
import contextlib
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shlex
import stat
import subprocess
import sys
import tempfile
import time

EVENTS = {"SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse", "Stop", "PostCompact"}
INPUT_LIMIT = 1024 * 1024
HERE = Path(__file__).resolve().parent
SECRET = re.compile(r"\b(?:AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{36}|sk-(?:proj-)?[A-Za-z0-9_-]{32,}|xox[bp]-[0-9]{10,}-[A-Za-z0-9-]+|glpat-[A-Za-z0-9_-]{20,})\b")
FAILURE_ADVICE = {
    "dependency_missing": "check declared dependencies and the execution environment; an import error may also be a code defect",
    "configuration_error": "inspect the relevant configuration and reproduce the exact failing command",
    "test_failure": "inspect the failing assertion, type check, or lint rule and repair the cause",
    "transient_failure": "look for evidence of a transient service or timing failure before considering one unchanged retry",
}
# Automatic Jev calls receive only this finite vocabulary, never arbitrary user
# text or tool output whose file/message provenance the hook cannot establish.
SKILL_TOPICS = {
    "ask-jev": "find files implementation locate source relevance",
    "audit": "audit skills agents configuration integrity",
    "branch": "branch branching git feature",
    "commit": "commit git changes staged",
    "debug": "debug bug crash failure errors performance slow",
    "deps": "dependencies dependency packages upgrade audit",
    "docs": "docs documentation readme architecture",
    "excalidraw": "diagram excalidraw architecture flow",
    "experiment": "experiment hypothesis evidence trials control",
    "feature-lifecycle": "feature implement implementation bugfix specification",
    "fix-ci": "ci github actions pipeline workflow failed",
    "frontend-design": "frontend interface layout styling component website",
    "gauntlet-loop": "gauntlet critique reference",
    "goal-status": "goal status budget progress",
    "implement": "implement implementation specification tasks",
    "interview": "interview requirements clarify",
    "land": "land pull request ci reviews merge readiness",
    "mcp-builder": "mcp server tools integration",
    "merge": "merge git branch pull request",
    "papercuts": "papercuts recurring friction log",
    "plan": "plan planning requirements specification",
    "pr": "pr pull request publish github",
    "prime": "prime repository onboarding architecture",
    "process-linear": "linear triage decision queue",
    "prompt": "prompt prompting optimize rewrite",
    "push": "push git publish commits",
    "rebase": "rebase git branch conflicts",
    "resolve-comments": "review comments feedback resolve fixes",
    "review": "review code defects correctness",
    "security-audit": "security vulnerability authentication authorization audit",
    "ship-it": "ship publish commit push pull request",
    "test": "test tests suite coverage",
    "verify": "verify verification checks failures validation",
    "watch": "watch video captions transcribe research",
    "webapp-testing": "browser playwright webapp test screenshots",
    "docx": "docx word document formatting",
    "pdf": "pdf document extraction ocr",
    "pptx": "pptx powerpoint slides presentation",
    "xlsx": "xlsx spreadsheet csv workbook formulas",
    "higgsfield-brandkit": "higgsfield brand brandkit brandbook",
    "higgsfield-generate": "higgsfield generate image video marketing",
    "higgsfield-marketplace-cards": "higgsfield marketplace cards listing",
    "higgsfield-product-photoshoot": "higgsfield product photoshoot photography",
    "higgsfield-soul-id": "higgsfield soul identity training",
    "higgsfield-video-explainer": "higgsfield explainer narrated video",
    "higgsfield-websites": "higgsfield website app game deploy",
    "higgsfield-youtube-thumbnail": "higgsfield youtube thumbnail cover",
}
INTENT_WORDS = set(" ".join(SKILL_TOPICS.values()).split())
DIAGNOSTIC_PATTERNS = {
    "assertion": r"\bAssertionError\b|\bassertion failed\b",
    "test_summary": r"\b(?:tests? failed|failed tests?|FAILURES)\b",
    "typecheck": r"\berror TS\d{3,5}\b",
    "syntax": r"\bSyntaxError\b|\bsyntax error\b",
    "lint": r"\bESLint\b|\blint error\b",
    "command_missing": r"\bcommand not found\b|\bexecutable file not found\b",
    "module_resolution": r"\bModuleNotFoundError\b|\bCannot find module\b",
    "permission": r"\bPermission denied\b|\bEACCES\b",
    "network": r"\bECONNRESET\b|\bENOTFOUND\b|\bCould not resolve host\b",
    "rate_limit": r"\brate limit exceeded\b|\btoo many requests\b",
    "disk_full": r"\bNo space left on device\b",
}


def home():
    return Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex").absolute()


def checksum(value):
    return hashlib.sha256(value.encode()).hexdigest()


def context(event, message):
    return {"hookSpecificOutput": {"hookEventName": event, "additionalContext": message[:6000]}}


def deny(message):
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                   "permissionDecisionReason": message}}


def safe_directory(path):
    # Reject redirects into another tree; state never comes from the repository.
    for parent in (path, *path.parents):
        if parent.is_symlink():
            if sys.platform == "darwin" and str(parent) in ("/tmp", "/var", "/etc") and parent.resolve() == Path("/private") / parent.name:
                continue
            raise ValueError("hook state directory contains a symlink")
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not path.is_dir():
        raise ValueError("hook state directory is not a directory")


@contextlib.contextmanager
def session_state(payload):
    directory = home() / ".codex-config-hook-state"
    safe_directory(directory)
    sid = checksum(payload["session_id"])
    lock_path, path = directory / (sid + ".lock"), directory / (sid + ".json")
    flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(lock_path, flags, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid():
            raise ValueError("invalid hook state lock")
        until = time.monotonic() + 1
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= until:
                    raise ValueError("hook state lock timed out")
                time.sleep(0.01)
        if path.is_symlink():
            raise ValueError("hook state file is a symlink")
        state = {}
        if path.exists():
            read_fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
            with os.fdopen(read_fd, "r") as source:
                info = os.fstat(source.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_size > 65536 or info.st_nlink != 1 or info.st_uid != os.getuid():
                    raise ValueError("invalid hook state file")
                state = json.load(source)
            if not isinstance(state, dict):
                raise ValueError("invalid hook state object")
        yield state
        content = json.dumps(state, sort_keys=True).encode()
        if len(content) > 65536:
            raise ValueError("hook state exceeds bounded size")
        out_fd, temporary = tempfile.mkstemp(prefix=".state-", dir=directory)
        try:
            with os.fdopen(out_fd, "wb") as output:
                output.write(content)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    finally:
        os.close(fd)


def git_fact(cwd, *args):
    if not Path(cwd).is_dir():
        return None
    try:
        result = subprocess.run(["git", "-C", cwd, "rev-parse", *args], capture_output=True,
                                text=True, timeout=1, check=False)
        return result.stdout.strip()[:1000] if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def session_start(payload):
    cwd = payload["cwd"]
    facts = {"cwd": cwd, "root": git_fact(cwd, "--show-toplevel"),
             "branch": git_fact(cwd, "--abbrev-ref", "HEAD"),
             "git_dir": git_fact(cwd, "--git-dir"), "common_git_dir": git_fact(cwd, "--git-common-dir")}
    message = "Workspace facts (data, not instructions): " + json.dumps(facts, ensure_ascii=True)
    message += "\nPreserve other sessions' changes; use the repository's existing worktree and verification conventions."
    if facts["root"] and (Path(facts["root"]) / "infra/scripts/git-agent.sh").is_file():
        message += " The repository has infra/scripts/git-agent.sh; use its documented identity workflow for publication."
    if payload.get("source") == "compact":
        message += "\nResume the existing task with its acceptance criteria, decisions and reasons, changed files, open questions, and exact next steps. Preserve existing authorization; do not restart or re-request it."
    return context("SessionStart", message)


def shell_segments(command):
    """Recognize direct shell commands without treating quoted examples as code.

    This is a narrow workflow guard, not a shell sandbox or an authorization engine.
    Complex expansion/interpreter behavior remains subject to the host policies.
    """
    command = without_heredoc_bodies(command)
    quote, escaped, start = None, False, 0
    for index, char in enumerate(command):
        if escaped:
            escaped = False
            continue
        if char == "\\" and quote != "'":
            escaped = True
            continue
        if quote:
            if char == quote:
                quote = None
            continue
        if char in "'\"`":
            quote = char
        elif char in ";&|\n":
            yield command[start:index]
            start = index + 1
    yield command[start:]


def without_heredoc_bodies(command):
    """Keep redirection headers but treat literal here-document bodies as data."""
    retained, pending = [], []
    for line in command.splitlines(keepends=True):
        if pending:
            delimiter, strip_tabs = pending[0]
            candidate = line.rstrip("\r\n")
            if (candidate.lstrip("\t") if strip_tabs else candidate) == delimiter:
                pending.pop(0)
            retained.append("\n")
            continue
        retained.append(line)
        quote, escaped, index = None, False, 0
        while index < len(line):
            char = line[index]
            if escaped:
                escaped = False
            elif char == "\\" and quote != "'":
                escaped = True
            elif quote:
                if char == quote:
                    quote = None
            elif char in "'\"`":
                quote = char
            elif char == "#" and (index == 0 or line[index - 1].isspace()):
                break
            elif line.startswith("<<", index) and not line.startswith("<<<", index) and (index == 0 or line[index - 1] != "<"):
                match = re.match(r'''<<(-?)\s*(?:'([^'\n]+)'|"([^"\n]+)"|([A-Za-z0-9_]+))''', line[index:])
                if match:
                    pending.append((next(item for item in match.groups()[1:] if item is not None), bool(match[1])))
                    index += match.end() - 1
            index += 1
    return "".join(retained)


def commands(command, depth=0):
    if depth > 3:
        return
    for segment in shell_segments(command):
        try:
            tokens = shlex.split(segment, comments=True)
        except ValueError:
            continue
        while tokens and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", tokens[0]):
            tokens.pop(0)
        if tokens and Path(tokens[0]).name == "env":
            tokens.pop(0)
            while tokens and (tokens[0] in ("-i", "--ignore-environment", "--") or re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", tokens[0])):
                tokens.pop(0)
        while tokens and tokens[0] in ("command", "exec", "builtin", "--"):
            tokens.pop(0)
        if not tokens:
            continue
        if Path(tokens[0]).name in ("sh", "bash", "zsh") and len(tokens) >= 3 and tokens[1] in ("-c", "-lc"):
            yield from commands(tokens[2], depth + 1)
        else:
            yield tokens


def git_args(tokens):
    if not tokens or Path(tokens[0]).name != "git":
        return None
    args = tokens[1:]
    while args and args[0].startswith("-"):
        option = args.pop(0)
        if option in ("-C", "-c", "--git-dir", "--work-tree", "--namespace") and args:
            value = args.pop(0)
            if option == "-c" and value.lower() in ("core.hookspath=/dev/null", "core.hookspath=nul", "core.hookspath="):
                return ["__hooks_disabled__"]
        elif option.lower() in ("-ccore.hookspath=/dev/null", "-ccore.hookspath=nul", "-ccore.hookspath="):
            return ["__hooks_disabled__"]
    return args


def standalone_flags(args):
    # Message/author/path values can legitimately contain an option-looking word.
    values = {"-m", "--message", "-F", "--file", "--author", "--date", "--grep", "--pathspec-from-file"}
    skip = False
    for arg in args:
        if skip:
            skip = False
        elif arg in values:
            skip = True
        elif arg == "--":
            break
        else:
            yield arg


def git_guard(command):
    advice = []
    for tokens in commands(command):
        args = git_args(tokens)
        if not args:
            continue
        op, flags = args[0], list(standalone_flags(args[1:]))
        short_bypass = False
        if op == "commit":
            for flag in flags:
                if not flag.startswith("-") or flag.startswith("--"):
                    continue
                for character in flag[1:]:
                    if character in "mFcC":
                        break  # The rest is a message/file/commit argument.
                    if character == "n":
                        short_bypass = True
        # Git accepts unambiguous long-option prefixes. Conservatively recognize
        # --no-v through --no-verify while preserving distinct --no-verbose.
        long_bypass = any(len(flag) >= len("--no-v") and "--no-verify".startswith(flag) for flag in flags)
        if op == "__hooks_disabled__" or (op in {"commit", "push", "merge", "rebase", "cherry-pick", "revert", "am"} and long_bypass) or short_bypass:
            return deny("Preserve Git hooks. Remove the hook-bypass option and resolve the failing hook before retrying.")
        destructive = (op == "reset" and "--hard" in flags or
                       op == "clean" and any(x.startswith("-") and not x.startswith("--") and "f" in x and "n" not in x for x in flags) or
                       op == "branch" and "-D" in flags or
                       op == "checkout" and "." in args[1:] or
                       op == "push" and any(x in ("-f", "--force", "--mirror") or x.startswith("+") for x in flags))
        if destructive:
            advice.append("This Git command can discard or rewrite work. Check existing explicit authorization and preserve other sessions' work; a history rewrite needs a lease or expected-head guard.")
        if op == "add" and any(x in (".", "-A", "--all") for x in flags):
            advice.append("Stage explicit intended paths within the existing authorization; preserve unrelated changes.")
    return context("PreToolUse", "\n".join(dict.fromkeys(advice))) if advice else {}


def patch_guard(patch):
    current, added_file, texts, new_files = None, False, [], []
    for line in patch.splitlines():
        match = re.match(r"^\*\*\* (Add|Update|Delete) File: (.+)$", line)
        if match:
            current, added_file = match[2], match[1] == "Add"
            if added_file:
                new_files.append(current)
        elif current and line.startswith("+"):
            path = Path(current)
            fixture = (any(part in ("test", "tests", "__tests__") for part in path.parts) or
                       re.search(r"(?:^test_|[._](?:test|spec)[._]|_test\.)", path.name) or
                       path.suffix.lower() in (".md", ".txt", ".svg", ".lock") or path.name == ".env.example")
            if not fixture and SECRET.search(line[1:]):
                return deny("A newly added production line resembles a credential. Use the existing secret store or an environment reference; do not commit the credential.")
    for filename in new_files:
        path = Path(filename)
        if ".tmp" not in path.parts and len(path.parts) == 1 and re.search(r"(?:analysis|report|draft|scratch|temp|plan)", path.stem, re.I):
            texts.append("Temporary analysis, plans, reports, and drafts belong under .tmp/. Keep an explicitly requested deliverable in its authorized location.")
    return context("PreToolUse", "\n".join(dict.fromkeys(texts))) if texts else {}


def pre_tool(payload):
    value = payload.get("tool_input")
    if not isinstance(value, dict):
        return {}
    command = value.get("command")
    if not isinstance(command, str):
        return {}
    if payload.get("tool_name") == "Bash":
        return git_guard(command)
    if payload.get("tool_name") in ("apply_patch", "Edit", "Write"):
        return patch_guard(command)
    return {}


def jev(payload, rule, questions, state, untrusted):
    executable = Path(os.environ.get("CODEX_HOOKS_JEV") or HERE / "jev/jev-ask")
    request = {"rule": rule, "cwd": payload["cwd"], "timeout_ms": 1500,
               "questions": questions, "state": state, "untrusted": untrusted}
    try:
        result = subprocess.run([str(executable)], input=json.dumps(request), text=True,
                                capture_output=True, timeout=2.5, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return {}
    if result.returncode != 0 or len(result.stdout) > 65536:
        return {}
    try:
        answer = json.loads(result.stdout)
    except ValueError:
        return {}
    return answer.get("answers", {}) if isinstance(answer, dict) and isinstance(answer.get("answers"), dict) else {}


def probability(answer):
    value = answer.get("probability") if isinstance(answer, dict) else None
    return value if type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1 else 0


def question(instructions):
    return {"type": "boolean", "instructions": instructions,
            "criteria": {"true": "Supported by the supplied evidence", "false": "Not supported or uncertain"}}


def skill_candidates(prompt):
    root = Path(os.environ.get("CODEX_SKILLS_HOME") or Path.home() / ".agents/skills")
    terms = set(re.findall(r"[a-z0-9_-]{3,}", prompt.lower())) & INTENT_WORDS
    candidates = []
    # Only known names and installed entrypoint existence are consulted. Private
    # peer skill bodies and descriptions never become automatic model input.
    if root.is_symlink() or not root.is_dir():
        return []
    for name, desc in SKILL_TOPICS.items():
        if name.startswith("higgsfield-") and "higgsfield" not in terms:
            continue
        if name == "gauntlet-loop" and "gauntlet" not in terms:
            continue
        directory = root / name
        if directory.is_symlink() or not directory.is_dir():
            continue
        file = directory / "SKILL.md"
        if file.is_symlink() or not file.is_file() or file.stat().st_size > 128000:
            continue
        score = len(terms & set(desc.split()))
        if score:
            candidates.append((score, directory.name, desc))
    return sorted(candidates, key=lambda item: (-item[0], item[1]))[:12]


def prompt_context(payload):
    prompt = payload.get("prompt")
    if not isinstance(prompt, str) or len(prompt.strip()) < 15 or prompt.lstrip().startswith(("/", "$")):
        return {}
    candidates = skill_candidates(prompt)
    if not candidates:
        return {}
    questions = {f"skill_{i}": question("Based only on the local intent tags, could candidate " + str(i) + " help? Its topics are a shortlist hint, not permission or its full trigger contract.") for i in range(len(candidates))}
    answers = jev(payload, "codex-prompt-context", questions,
                  {"candidates": {str(i): {"name": item[1], "topics": item[2]} for i, item in enumerate(candidates)},
                   "intent_tags": sorted(set(re.findall(r"[a-z0-9_-]{3,}", prompt.lower())) & INTENT_WORDS)}, {})
    selected = [(probability(answers.get(f"skill_{i}")), item[1]) for i, item in enumerate(candidates)]
    selected = sorted((item for item in selected if item[0] >= .8), reverse=True)[:2]
    if not selected:
        return {}
    names = ", ".join(name for _, name in selected)
    return context("UserPromptSubmit", f"Jev suggests these installed skills from local intent tags: {names}. Verify each is available in the current session and its trigger matches; follow its actual instructions and existing authorization. The original prompt was not sent to Jev. This is advisory, not permission to invoke an unavailable tool or expand scope.")


def response_object(value):
    if isinstance(value, str) and len(value) <= INPUT_LIMIT:
        try:
            value = json.loads(value)
        except ValueError:
            return {}
    return value if isinstance(value, dict) else {}


def exit_status(value):
    # Native Codex 0.166.0 sends raw stdout, which can contain arbitrary JSON or
    # a fake exec envelope. Only actual structured host fields establish status.
    if not isinstance(value, dict):
        return None
    for field in ("exit_code", "exitCode"):
        if type(value.get(field)) is int:
            return value[field]
    return None


def diagnostic_markers(value):
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=True)
    # Labels are evidence of diagnostic text, not proof the command failed.
    return [name for name, pattern in DIAGNOSTIC_PATTERNS.items() if re.search(pattern, text[-16000:], re.I)]


def failure_hint(payload, status, markers):
    if not markers:
        return ""
    answers = jev(payload, "codex-failure-classify", {key: question("Do the fixed diagnostic markers provide evidence for " + key.replace("_", " ") + "? Missing exit status does not establish command failure.") for key in FAILURE_ADVICE},
                  {"exit_status": status, "diagnostic_markers": markers}, {})
    picks = sorted(((probability(answers.get(key)), key) for key in FAILURE_ADVICE), reverse=True)
    if picks and picks[0][0] >= .8:
        return " Jev suggests: " + FAILURE_ADVICE[picks[0][1]] + "; confirm the classification from evidence before acting."
    return ""


def publication(command):
    for tokens in commands(command):
        args = git_args(tokens)
        if args and args[0] == "push":
            return True
        if len(tokens) >= 3 and Path(tokens[0]).name == "gh" and tokens[1:3] == ["pr", "create"]:
            return True
    return False


def post_tool(payload):
    tool = payload.get("tool_name", "")
    tool_input = payload.get("tool_input")
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    response = response_object(payload.get("tool_response"))
    if tool != "Bash" or not isinstance(command, str):
        # Connector publication can expose a structured PR URL without a shell exit code.
        if "create_pull_request" in tool and response.get("isError") is not True:
            structured = response.get("structuredContent", response)
            if isinstance(structured, dict) and any(re.fullmatch(r"https://github\.com/[^/]+/[^/]+/pull/\d+", str(structured.get(key, ""))) for key in ("url", "html_url")):
                with session_state(payload) as state:
                    state["publication_turn"] = payload.get("turn_id")
                return context("PostToolUse", "PR publication observed. Follow the authorized land workflow through current-head checks and review; report unresolved gates and merge only when authorized.")
        return {}
    status = exit_status(payload.get("tool_response"))
    markers = diagnostic_markers(payload.get("tool_response"))
    if status is None:
        notes = []
        if publication(command):
            with session_state(payload) as state:
                state["publication_attempt_turn"] = payload.get("turn_id")
            notes.append("A publication command returned, but its exit status is unavailable to this hook. Inspect the actual remote/PR status and current-head CI/review gates before claiming completion; merge only when authorized.")
        if markers:
            notes.append("Command output contains diagnostic markers (" + ", ".join(markers) + "), but its exit status is unavailable to this hook. Inspect the actual command result; no failure or success is inferred and retry counters are unchanged." + failure_hint(payload, None, markers))
        return context("PostToolUse", " ".join(notes)) if notes else {}
    key = checksum(payload["cwd"] + "\0" + command)
    use_id = payload.get("tool_use_id")
    event_id = checksum(str(use_id)) if isinstance(use_id, str) and use_id else None
    with session_state(payload) as state:
        seen = state.setdefault("seen_tools", [])
        if event_id and event_id in seen:
            return {}
        if event_id:
            state["seen_tools"] = (seen + [event_id])[-64:]
        failures = state.setdefault("failures", {})
        if status == 0:
            failures.pop(key, None)
            if publication(command):
                state["publication_turn"] = payload.get("turn_id")
            return {}
        count = min(failures.get(key, 0) + 1, 999)
        failures[key] = count
        while len(failures) > 128:
            failures.pop(next(iter(failures)))
    message = f"Command failure {count}: exit status {status}. Preserve this failed result; it is not a passing verification."
    if count >= 3:
        message += " The same command has failed at least three times. Diagnose the cause or report the unresolved gate; respect the active workflow's retry bound."
    if count in (1, 3):
        message += failure_hint(payload, status, markers)
    return context("PostToolUse", message)


def machine_output(text):
    if text.lstrip().startswith("```"):
        return True
    try:
        json.loads(text)
        return True
    except ValueError:
        return False


def stop(payload):
    text = payload.get("last_assistant_message")
    if payload.get("stop_hook_active") or not isinstance(text, str) or not text.strip():
        return {}
    turn = payload.get("turn_id")
    if not isinstance(turn, str) or not turn:
        return {}
    turn_key = checksum(turn)
    notes = []
    with session_state(payload) as state:
        seen = state.setdefault("stop_turns", [])
        if turn_key in seen:
            return {}
        state["stop_turns"] = (seen + [turn_key])[-32:]
        if state.get("publication_turn") == turn:
            notes.append("A publication was observed this turn: report current-head CI/review status and unresolved gates; merge only within existing authorization.")
        elif state.get("publication_attempt_turn") == turn:
            notes.append("A publication command was attempted this turn: inspect its actual outcome and report current-head CI/review status; the hook did not receive its exit status.")
        if not machine_output(text):
            first = text.strip().splitlines()[0]
            if not (re.match(r"^\*\*(?:FYI|DECISION|APPROVAL|INPUT|ACTION)\b", first) and
                    "**You:**" in text and "**Unsure:**" in text and "**Next:**" in text):
                notes.append("Executive-format shadow check: ordinary prose should include a tagged conclusion, You, Unsure, and Next. Exact-output and review protocols take precedence; this warning does not request a rewrite.")
    return {"systemMessage": " ".join(notes)} if notes else {}


def dispatch(payload):
    event = payload.get("hook_event_name")
    if not isinstance(event, str) or event not in EVENTS:
        raise ValueError("invalid or unsupported hook event")
    for key in ("cwd", "session_id"):
        if not isinstance(payload.get(key), str) or not payload[key] or len(payload[key]) > 4096:
            raise ValueError(f"invalid hook {key}")
    if event == "SessionStart":
        return session_start(payload)
    if event == "UserPromptSubmit":
        return prompt_context(payload)
    if event == "PreToolUse":
        return pre_tool(payload)
    if event == "PostToolUse":
        return post_tool(payload)
    if event == "Stop":
        return stop(payload)
    with session_state(payload) as state:
        state["compactions"] = min(state.get("compactions", 0) + 1, 99999)
    return {}


def main():
    try:
        raw = sys.stdin.buffer.read(INPUT_LIMIT + 1)
        if len(raw) > INPUT_LIMIT:
            raise ValueError("hook input exceeds bounded size")
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("invalid hook input object")
        output = dispatch(payload)
        print(json.dumps(output, ensure_ascii=True))
        return 0
    except (OSError, ValueError, TypeError, KeyError) as error:
        # Do not echo tool arguments, prompts, or file contents on parse failures.
        print("codex-config hook failed: " + str(error)[:300], file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
