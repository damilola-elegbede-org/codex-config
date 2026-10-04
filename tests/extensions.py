"""Hermetic extension migration checks; never reads or writes live Codex homes."""
import ast
import importlib.util
import json
import os
import subprocess
import tempfile
import tomllib
import unittest
import zipfile
import xml.etree.ElementTree as ET
import contextlib
import io
import shlex
import signal
import socket
import sys
import urllib.error
from unittest.mock import patch
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "system-configs/.agents/skills"
AGENTS = ROOT / "system-configs/.codex/agents"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Extensions(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.source = self.work / "source"
        self.live = self.work / "live"
        self.stage = self.work / "stage"
        self.stage.mkdir()
        self.source.mkdir()
        self.live.mkdir()

    def helper(self, mode, *extra, success=True):
        command = ["python3", str(ROOT / "scripts/sync-extensions.py"), mode, "--stage", str(self.stage)]
        if mode == "stage":
            command += ["--skills-source", str(self.source / "skills"), "--agents-source", str(self.source / "agents"),
                        "--skills-target", str(self.live / "skills"), "--agents-target", str(self.live / ".codex/agents"), "--skills", "--agents"]
        result = subprocess.run(command + list(extra), capture_output=True, text=True)
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        return result

    def skill(self, body="Original"):
        path = self.source / "skills/example/SKILL.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('---\nname: "example"\ndescription: "Test workflow"\n---\n' + body)
        return path

    def test_inventory_and_syntax(self):
        validator = load(ROOT / "scripts/validate-extensions.py", "validator")
        self.assertEqual(validator.validate(SKILLS, AGENTS), (38, 8))
        migration = json.loads((ROOT / "docs/claude-migration.json").read_text(encoding="utf-8"))
        for entry in migration["entries"]:
            self.assertTrue((ROOT / entry["target"]).is_file(), entry)
        for path in SKILLS.rglob("*.py"):
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for path in AGENTS.glob("*.toml"):
            agent = tomllib.loads(path.read_text(encoding="utf-8"))
            self.assertNotIn("model", agent)
            self.assertNotIn("model_reasoning_effort", agent)

    def test_install_update_backup_and_custom_collision(self):
        path = self.skill()
        resource = path.parent / "reference.txt"
        resource.write_text("support")
        self.helper("stage")
        self.assertFalse((self.live / "skills").exists())
        self.helper("apply")
        target = self.live / "skills/example/SKILL.md"
        self.assertEqual(target.read_bytes(), path.read_bytes())
        self.assertEqual(target.stat().st_mode & 0o777, 0o600)
        unrelated = self.live / "skills/personal/SKILL.md"
        unrelated.parent.mkdir()
        unrelated.write_text("personal")
        self.skill("Updated")
        self.helper("stage")
        self.helper("apply", "--backup", str(self.work / "backup"))
        self.assertIn("Original", (self.work / "backup/extensions/skills/example/SKILL.md").read_text(encoding="utf-8"))
        self.assertEqual(unrelated.read_text(encoding="utf-8"), "personal")
        target.write_text("locally customized")
        self.helper("stage", success=False)
        self.assertEqual(target.read_text(encoding="utf-8"), "locally customized")

    def test_concurrent_edit_and_source_tampering(self):
        path = self.skill()
        self.helper("stage")
        target = self.live / "skills/example/SKILL.md"
        target.parent.mkdir(parents=True)
        target.write_text("concurrent")
        self.helper("apply", success=False)
        self.assertEqual(target.read_text(encoding="utf-8"), "concurrent")
        target.unlink()
        self.helper("stage")
        (self.stage / "skills/example/SKILL.md").write_text("tampered")
        self.helper("apply", success=False)
        self.assertFalse(target.exists())

    def test_backup_preserves_previous_execute_bit_when_source_mode_changes(self):
        path = self.skill()
        script = path.parent / "helper.py"
        target = self.live / "skills/example/helper.py"
        for previous_mode, new_mode in ((0o700, 0o600), (0o600, 0o700)):
            with self.subTest(previous_mode=previous_mode, new_mode=new_mode):
                script.write_text("print('previous')", encoding="utf-8")
                script.chmod(previous_mode)
                self.helper("stage")
                self.helper("apply")
                script.write_text("print('updated')", encoding="utf-8")
                script.chmod(new_mode)
                self.helper("stage")
                backup_root = self.work / f"backup-{previous_mode}"
                self.helper("apply", "--backup", str(backup_root))
                backup = backup_root / "extensions/skills/example/helper.py"
                self.assertEqual(backup.read_text(encoding="utf-8"), "print('previous')")
                self.assertEqual(backup.stat().st_mode & 0o777, previous_mode)
                self.assertEqual(target.stat().st_mode & 0o777, new_mode)

    def test_unmanaged_collision_and_symlink(self):
        self.skill()
        target = self.live / "skills/example/SKILL.md"
        target.parent.mkdir(parents=True)
        target.write_text("unmanaged")
        self.helper("stage", success=False)
        target.unlink()
        (self.live / "skills/example").rmdir()
        (self.live / "skills/example").symlink_to(self.source / "skills/example", target_is_directory=True)
        self.helper("stage", success=False)

    def test_invalid_source_and_no_pruning(self):
        path = self.skill()
        path.write_text("invalid skill")
        self.helper("stage", success=False)
        self.skill()
        self.helper("stage")
        self.helper("apply")
        path.unlink()
        path.parent.rmdir()
        self.helper("stage")
        self.helper("apply")
        self.assertTrue((self.live / "skills/example/SKILL.md").exists())
        agent = self.source / "agents/reviewer.toml"
        agent.parent.mkdir()
        agent.write_text('name="reviewer"\ndescription="Review"\n')
        self.helper("stage", success=False)

    def test_ranker_filters_private_binary_generated_and_links(self):
        ranker = load(SKILLS / "ask-jev/scripts/rank-files.py", "ranker")
        paths = []
        for name, data in (("api.py", b"routing routing"), ("notes.md", b"other"), (".env", b"routing"),
                           ("work/Visa/private.py", b"routing"), ("vendor/generated.py", b"routing"), ("binary", b"routing\0")):
            path = self.work / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            paths.append(path)
        link = self.work / "linked.py"
        link.symlink_to(paths[0])
        results = ranker.rank("routing", paths + [link], root=self.work)
        self.assertEqual([Path(item["path"]).name for item in results], ["api.py", "notes.md"])

    def test_ranker_allows_repository_under_excluded_ancestor(self):
        ranker = load(SKILLS / "ask-jev/scripts/rank-files.py", "ranker")
        root = self.work / "work/build/project"
        root.mkdir(parents=True)
        eligible = root / "api.py"
        eligible.write_text("routing", encoding="utf-8")
        private = root / "work/Visa/private.py"
        private.parent.mkdir(parents=True)
        private.write_text("routing", encoding="utf-8")
        outside = self.work / "outside.py"
        outside.write_text("routing", encoding="utf-8")
        self.assertEqual([item["path"] for item in ranker.rank("routing", [eligible, private, outside], root)], [str(eligible)])

    def test_utf8_source_validation_in_ascii_locale(self):
        env = dict(os.environ, LC_ALL="C", PYTHONUTF8="0", PYTHONCOERCECLOCALE="0")
        result = subprocess.run(["python3", str(ROOT / "scripts/validate-extensions.py"), str(SKILLS), str(AGENTS)], env=env, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_installed_helper_and_metadata_permissions(self):
        path = self.skill()
        script = path.parent / "helper.py"
        script.write_text("print('helper')", encoding="utf-8")
        script.chmod(0o755)
        self.helper("stage")
        self.helper("apply")
        self.assertEqual((self.live / "skills/example/helper.py").stat().st_mode & 0o777, 0o700)
        self.assertEqual((self.live / ".codex/.codex-config-managed-extensions.json").stat().st_mode & 0o777, 0o600)

    def test_watch_never_uploads_or_reads_keys_without_opt_in(self):
        watch = load(SKILLS / "watch/watch.py", "watch")
        args = SimpleNamespace(source="https://example.com/video", start=None, end=None, no_whisper=False,
                               allow_whisper=False, whisper=None, json=True, max_frames=10, fps=2, resolution=512)
        with patch.object(watch, "fetch_subs_only", return_value=(None, {})), \
             patch.object(watch, "select_whisper_backend", side_effect=AssertionError("credential read without opt-in")), \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(watch.run_transcript_only(args, self.work), 2)
        download = {"video_path": "video.mp4", "info": {}}
        meta = {"duration_seconds": 1000, "width": 100, "height": 100}
        with patch.object(watch, "download_video", return_value=download), \
             patch.object(watch, "ffprobe_meta", return_value=meta), \
             patch.object(watch, "extract_frames", return_value=[]) as extract, \
             patch.object(watch, "select_whisper_backend", side_effect=AssertionError("credential read without opt-in")), \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(watch.run_with_frames(args, self.work), 0)
            self.assertLessEqual(extract.call_args.kwargs["fps"], .01)
        args.allow_whisper = True
        self.assertTrue(watch.whisper_allowed(args))
        args.no_whisper = True
        self.assertFalse(watch.whisper_allowed(args))
        for duration in (0, 5, 1000):
            fps, target = watch._clamp(2, duration, 10)
            self.assertLessEqual(target, 10)
            if duration > 0:
                self.assertLessEqual(fps * duration, 10)

    def test_watch_does_not_use_project_credentials_or_log_provider_errors(self):
        watch = load(SKILLS / "watch/watch.py", "watch")
        home = self.work / "home"
        home.mkdir()
        (self.work / ".env").write_text("OPENAI_API_KEY=project-test-value", encoding="utf-8")
        with patch.dict(os.environ, {}, clear=True), patch.object(watch.Path, "home", return_value=home), \
             patch.object(watch.Path, "cwd", return_value=self.work):
            self.assertIsNone(watch._read_env_key("OPENAI_API_KEY"))
        audio = self.work / "audio.mp3"
        audio.write_bytes(b"test audio")
        error = urllib.error.HTTPError(watch.OPENAI_ENDPOINT, 401, "test error", {}, io.BytesIO(b"private test response"))
        output = io.StringIO()
        with patch.object(watch, "_read_env_key", return_value="test-credential-value"), \
             patch.object(watch, "urlopen", side_effect=error), contextlib.redirect_stderr(output), \
             self.assertRaises(SystemExit) as raised:
            watch._post_whisper("openai", audio)
        self.assertIn("HTTP 401", str(raised.exception))
        self.assertNotIn("private test response", str(raised.exception) + output.getvalue())
        self.assertNotIn("test-credential-value", str(raised.exception) + output.getvalue())

    def test_verify_incomplete_config_and_non_executable_shell_gate(self):
        runner = SKILLS / "verify/scripts/run-checks.mjs"
        (self.work / "pyproject.toml").mkdir()
        command = ["node", str(runner), "--json", "--dir", str(self.work)]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["verdict"], "incomplete")
        self.assertEqual(data["checks"][0]["status"], "unavailable")
        (self.work / "pyproject.toml").rmdir()
        script = self.work / "tests/test.sh"
        script.parent.mkdir()
        script.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        script.chmod(0o644)
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["verdict"], "pass")
        script.write_text('kill -KILL "$$"\n', encoding="utf-8")
        result = subprocess.run(command, capture_output=True, text=True)
        data = json.loads(result.stdout)
        self.assertEqual(data["verdict"], "fail")
        self.assertIn("SIGKILL", data["checks"][0]["output"])
        self.assertNotIn("exceeded", data["checks"][0]["output"])

    @unittest.skipUnless(os.name == "posix", "server helper uses POSIX process groups")
    def test_browser_helper_drains_output_and_stops_child_server(self):
        helper = SKILLS / "webapp-testing/scripts/with_server.py"
        with socket.socket() as temporary_socket:
            temporary_socket.bind(("127.0.0.1", 0))
            port = temporary_socket.getsockname()[1]
        server = self.work / "server.py"
        server.write_text("import socket,sys,time\nsys.stdout.write('x'*200000)\nsys.stdout.flush()\n"
                          f"s=socket.socket();s.bind(('127.0.0.1',{port}));s.listen()\n"
                          "while True: time.sleep(.1)\n", encoding="utf-8")
        command = "cd " + shlex.quote(str(self.work)) + " && " + shlex.quote(sys.executable) + " " + shlex.quote(str(server))
        result = subprocess.run([sys.executable, str(helper), "--server", command, "--port", str(port), "--timeout", "3",
                                 "--", sys.executable, "-c", "print('wrapped command finished')"], capture_output=True, text=True, timeout=12)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("wrapped command finished", result.stdout)
        with self.assertRaises(OSError):
            with socket.create_connection(("127.0.0.1", port), timeout=.3):
                pass

    def test_mcp_eval_requires_observed_success_and_nonempty_cases(self):
        evaluation = load(SKILLS / "mcp-builder/scripts/evaluation.py", "evaluation")
        xml = self.work / "cases.xml"
        xml.write_text("<evaluation/>")
        with self.assertRaises(ValueError):
            evaluation.parse_evaluation_file(xml)
        xml.write_text("<evaluation><qa_pair><question>Question</question><answer>42</answer></qa_pair></evaluation>")
        pair = evaluation.parse_evaluation_file(xml)[0]
        stub = self.work / "codex"
        args = SimpleNamespace(server="target", codex=str(stub), cwd=self.work, model=None, timeout=3)
        events = [dict(type="item.completed", item=dict(type="agent_message", text="<response>42</response>")), dict(type="turn.completed")]
        def write_stub():
            stub.write_text("#!/usr/bin/env python3\nimport sys\nsys.stdin.read()\nprint(" + repr("\n".join(json.dumps(event) for event in events)) + ")\n")
            stub.chmod(0o755)
        write_stub()
        self.assertFalse(evaluation.evaluate(pair, args)["passed"])

        events.insert(0, dict(type="item.completed", item=dict(type="mcp_tool_call", server="target", tool="search", status="completed", result={})))
        write_stub()
        self.assertTrue(evaluation.evaluate(pair, args)["passed"])
        events[0]["item"]["result"] = {"isError": True}
        write_stub()
        self.assertFalse(evaluation.evaluate(pair, args)["passed"])

    def test_office_package_rejects_missing_parts_and_malformed_xml(self):
        checker = load(SKILLS / "office-common/package-check.py", "package_checker")
        path = self.work / "test.docx"
        def create(extra):
            with zipfile.ZipFile(path, "w") as package:
                for name, value in extra.items():
                    package.writestr(name, value)
        create({"word/document.xml": "<document/>"})
        with self.assertRaises(ValueError):
            checker.check(path)
        valid = {"word/document.xml": "<document/>", "[Content_Types].xml": "<Types/>", "_rels/.rels": "<Relationships/>"}
        create(valid)
        self.assertEqual(checker.check(path), 3)
        create(dict(valid, **{"word/document.xml": "<bad>"}))
        with self.assertRaises(ET.ParseError):
            checker.check(path)

    def test_full_sync_dry_run_and_install(self):
        codex = self.work / "bin/codex"
        codex.parent.mkdir()
        codex.write_text('#!/bin/sh\necho "Model provider __nonexistent__ not found" >&2\nexit 1\n')
        codex.chmod(0o755)
        env = dict(os.environ, PATH=str(codex.parent) + os.pathsep + os.environ["PATH"], HOME=str(self.work / "home"),
                   CODEX_HOME=str(self.live / ".codex"), CODEX_SKILLS_HOME=str(self.live / "skills"),
                   CODEX_CONFIG_SOURCE=str(ROOT / "system-configs/.codex"), CODEX_CONFIG_SKILLS_SOURCE=str(SKILLS), CODEX_CONFIG_STATION="test-extensions")
        command = [str(ROOT / "scripts/sync.sh"), "--force", "--no-backup"]
        result = subprocess.run(command + ["--dry-run"], env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse((self.live / ".codex").exists())
        result = subprocess.run(command, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(len(list((self.live / "skills").glob("*/SKILL.md"))), 38)
        self.assertEqual(len(list((self.live / ".codex/agents").glob("*.toml"))), 8)
        self.assertTrue((self.live / "skills/office-common/package-check.py").exists())


if __name__ == "__main__":
    unittest.main()
