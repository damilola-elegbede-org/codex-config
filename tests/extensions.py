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
        migration = json.loads((ROOT / "docs/claude-migration.json").read_text())
        for entry in migration["entries"]:
            self.assertTrue((ROOT / entry["target"]).is_file(), entry)
        for path in SKILLS.rglob("*.py"):
            ast.parse(path.read_text(), filename=str(path))
        for path in AGENTS.glob("*.toml"):
            agent = tomllib.loads(path.read_text())
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
        unrelated = self.live / "skills/personal/SKILL.md"
        unrelated.parent.mkdir()
        unrelated.write_text("personal")
        self.skill("Updated")
        self.helper("stage")
        self.helper("apply", "--backup", str(self.work / "backup"))
        self.assertIn("Original", (self.work / "backup/extensions/skills/example/SKILL.md").read_text())
        self.assertEqual(unrelated.read_text(), "personal")
        target.write_text("locally customized")
        self.helper("stage", success=False)
        self.assertEqual(target.read_text(), "locally customized")

    def test_concurrent_edit_and_source_tampering(self):
        path = self.skill()
        self.helper("stage")
        target = self.live / "skills/example/SKILL.md"
        target.parent.mkdir(parents=True)
        target.write_text("concurrent")
        self.helper("apply", success=False)
        self.assertEqual(target.read_text(), "concurrent")
        target.unlink()
        self.helper("stage")
        (self.stage / "skills/example/SKILL.md").write_text("tampered")
        self.helper("apply", success=False)
        self.assertFalse(target.exists())

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
        results = ranker.rank("routing", paths + [link])
        self.assertEqual([Path(item["path"]).name for item in results], ["api.py", "notes.md"])

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
