#!/usr/bin/env python3
"""Owned hook installation and dependency boundary regressions."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts/sync-hooks.py"


class HookSync(unittest.TestCase):
    def setUp(self):
        (ROOT / ".tmp").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / ".tmp", prefix="hook-sync-test-")
        self.work = Path(self.temp.name)
        self.source = self.work / "source"
        self.target = self.work / "live"
        self.staged = self.work / "stage"
        self.backup = self.work / "backup"
        self.bin = self.work / "bin"
        for directory in (self.source / "hooks", self.target, self.staged, self.bin):
            directory.mkdir(parents=True)
        (self.source / "hooks/runner.py").write_text("print('{}')\n")
        self.hooks = {"hooks": {"SessionStart": [{"hooks": [{"type": "command", "command": 'python3 "${CODEX_HOME:-$HOME/.codex}/hooks/runner.py"', "timeout": 5}]}]}}
        self.write_hooks()
        self.env = {**os.environ, "PATH": str(self.bin) + os.pathsep + os.environ["PATH"], "HOME": str(self.work / "home")}
        self.npm_log = self.work / "npm.log"

    def tearDown(self):
        self.temp.cleanup()

    def write_hooks(self):
        (self.source / "hooks.json").write_text(json.dumps(self.hooks))

    def run_helper(self, action, *args, ok=True):
        command = ["python3", str(HELPER), action, "--stage", str(self.staged)]
        if action == "stage":
            command += ["--source", str(self.source), "--target", str(self.target)]
        result = subprocess.run(command + list(args), env=self.env, text=True, capture_output=True)
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
        return result

    def dependencies(self):
        directory = self.source / "hooks/jev"
        directory.mkdir()
        package = {"name": "fixture", "version": "1.0.0", "dependencies": {"ai": "7.0.126"}, "engines": {"node": ">=22"}}
        lock = {"name": "fixture", "version": "1.0.0", "lockfileVersion": 3, "packages": {"": package, "node_modules/ai": {"version": "7.0.126", "resolved": "https://registry.npmjs.org/ai/-/ai-7.0.126.tgz", "integrity": "sha512-fixture"}}}
        (directory / "package.json").write_text(json.dumps(package))
        (directory / "package-lock.json").write_text(json.dumps(lock))
        node = self.bin / "node"
        node.write_text("#!/bin/sh\nif [ \"$1\" = --version ]; then echo v22.0.0; fi\n")
        node.chmod(0o700)
        npm = self.bin / "npm"
        npm.write_text("#!/usr/bin/env python3\nimport json, os, pathlib, sys, time\np=pathlib.Path.cwd()\nwith open(os.environ['TEST_NPM_LOG'], 'a') as f: f.write(' '.join(sys.argv[1:])+'\\n')\nif os.environ.get('TEST_NPM_FAIL'): sys.exit(1)\ntime.sleep(float(os.environ.get('TEST_NPM_SLEEP', '0')))\n(p/'node_modules/ai').mkdir(parents=True)\n(p/'node_modules/ai/package.json').write_text(json.dumps({'version':'7.0.126'}))\n")
        npm.chmod(0o700)
        self.env["TEST_NPM_LOG"] = str(self.npm_log)
        self.lock_hash = hashlib.sha256((directory / "package-lock.json").read_bytes()).hexdigest()
        return self.target / ".codex-config-deps/jev" / self.lock_hash

    def run_sync(self, *args, ok=True, overrides=None):
        repo = self.work / "repo"
        if not repo.exists():
            shutil.copytree(ROOT / "scripts", repo / "scripts")
            (repo / "sync-manifests").mkdir()
        (repo / "sync-manifests/test-hooks.json").write_text(json.dumps({"sync": overrides or {}}))
        (self.source / "config.toml").write_text('model = "new"\n')
        (self.source / "AGENTS.md").write_text("Test instructions\n")
        (self.source / "agents").mkdir(exist_ok=True)
        skills = self.work / "skills"
        skills.mkdir(exist_ok=True)
        codex = self.bin / "codex"
        codex.write_text('#!/bin/sh\necho "Model provider __nonexistent__ not found" >&2\nexit 1\n')
        codex.chmod(0o700)
        env = {**self.env, "CODEX_HOME": str(self.target), "CODEX_CONFIG_SOURCE": str(self.source),
               "CODEX_CONFIG_SKILLS_SOURCE": str(skills), "CODEX_SKILLS_HOME": str(self.work / "live-skills"),
               "CODEX_CONFIG_STATION": "test-hooks"}
        result = subprocess.run(["sh", str(repo / "scripts/sync.sh"), "--force", "--no-backup", *args],
                                env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode == 0, ok, result.stdout + result.stderr)
        return result

    def test_stage_writes_no_target(self):
        self.dependencies()
        self.run_helper("stage")
        self.assertEqual(list(self.target.iterdir()), [])
        self.assertFalse(self.npm_log.exists())

    def test_install_preserves_extra_files_and_tracks_ownership(self):
        (self.target / "hooks").mkdir()
        (self.target / "hooks/personal.py").write_text("personal")
        self.run_helper("stage")
        self.run_helper("prepare")
        self.run_helper("apply", "--backup", str(self.backup))
        self.assertEqual((self.target / "hooks/personal.py").read_text(), "personal")
        self.assertEqual((self.target / "hooks.json").read_bytes(), (self.source / "hooks.json").read_bytes())
        index = json.loads((self.target / ".codex-config-managed-hooks.json").read_text())
        self.assertEqual(set(index["files"]), {"hooks.json", "hooks/runner.py"})

    def test_custom_hook_config_is_preserved(self):
        (self.target / "hooks.json").write_text('{"hooks":{}}')
        result = self.run_helper("stage", ok=False)
        self.assertIn("customized or unmanaged", result.stderr)
        self.assertEqual((self.target / "hooks.json").read_text(), '{"hooks":{}}')

    def test_same_existing_files_can_be_adopted(self):
        shutil.copyfile(self.source / "hooks.json", self.target / "hooks.json")
        self.run_helper("stage")
        self.run_helper("apply")
        self.assertTrue((self.target / ".codex-config-managed-hooks.json").is_file())

    def test_identical_adopted_script_gets_required_execute_permission(self):
        source = self.source / "hooks/runner.py"
        source.chmod(0o755)
        (self.target / "hooks").mkdir()
        target = self.target / "hooks/runner.py"
        shutil.copyfile(source, target)
        target.chmod(0o600)
        self.run_helper("stage")
        self.run_helper("apply")
        self.assertEqual(target.stat().st_mode & 0o777, 0o700)

    def test_update_backup_and_custom_edit(self):
        self.run_helper("stage")
        self.run_helper("apply")
        (self.source / "hooks/runner.py").write_text("print('new')\n")
        self.run_helper("stage")
        self.run_helper("apply", "--backup", str(self.backup))
        self.assertEqual((self.backup / "hooks/runner.py").read_text(), "print('{}')\n")
        self.assertTrue((self.backup / ".codex-config-managed-hooks.json").is_file())
        (self.target / "hooks/runner.py").write_text("custom")
        self.run_helper("stage", ok=False)

    def test_late_edit_blocks_apply(self):
        self.run_helper("stage")
        (self.target / "hooks.json").write_text("custom")
        self.run_helper("apply", ok=False)
        self.assertFalse((self.target / "hooks/runner.py").exists())

    def test_late_stage_edit_blocks_apply(self):
        self.run_helper("stage")
        (self.staged / "files/hooks/runner.py").write_text("changed")
        self.run_helper("apply", ok=False)
        self.assertFalse((self.target / "hooks.json").exists())

    def test_target_symlink_rejected(self):
        (self.target / "hooks").symlink_to(self.source / "hooks", target_is_directory=True)
        self.run_helper("stage", ok=False)

    def test_source_symlink_rejected(self):
        (self.source / "hooks/linked.py").symlink_to(self.source / "hooks/runner.py")
        self.run_helper("stage", ok=False)

    def test_invalid_hook_event_and_handler_rejected(self):
        self.hooks["hooks"]["Notification"] = self.hooks["hooks"].pop("SessionStart")
        self.write_hooks()
        self.run_helper("stage", ok=False)
        self.hooks["hooks"]["SessionStart"] = self.hooks["hooks"].pop("Notification")
        self.hooks["hooks"]["SessionStart"][0]["hooks"][0]["type"] = "prompt"
        self.write_hooks()
        self.run_helper("stage", ok=False)

    def test_bad_script_stops_staging(self):
        (self.source / "hooks/runner.py").write_text("def (\n")
        self.run_helper("stage", ok=False)

    def test_missing_referenced_script_is_rejected(self):
        (self.source / "hooks/runner.py").unlink()
        result = self.run_helper("stage", ok=False)
        self.assertIn("missing referenced hook resource", result.stderr)

    def test_corrupted_cache_is_not_reused_or_replaced(self):
        cache = self.dependencies()
        self.run_helper("stage")
        self.run_helper("prepare")
        (cache / "node_modules/ai/package.json").write_text('{"version":"wrong"}')
        result = self.run_helper("prepare", ok=False)
        self.assertIn("incomplete or modified", result.stderr)
        self.assertIn("wrong", (cache / "node_modules/ai/package.json").read_text())
        self.assertEqual(len(self.npm_log.read_text().splitlines()), 1)

    def test_missing_sources_rejected(self):
        (self.source / "hooks.json").unlink()
        self.run_helper("stage", ok=False)

    def test_dependency_install_is_pinned_and_reused(self):
        cache = self.dependencies()
        self.run_helper("stage")
        self.run_helper("prepare")
        self.assertTrue((cache / ".complete.json").is_file())
        self.run_helper("prepare")
        calls = self.npm_log.read_text().splitlines()
        self.assertEqual(len(calls), 1)
        self.assertIn("ci --omit=dev --ignore-scripts", calls[0])
        self.run_helper("apply")

    def test_failed_dependencies_leave_hooks_uninstalled(self):
        cache = self.dependencies()
        self.env["TEST_NPM_FAIL"] = "1"
        self.run_helper("stage")
        self.run_helper("prepare", ok=False)
        self.assertFalse(cache.exists())
        self.assertFalse((self.target / "hooks.json").exists())
        self.run_helper("apply", ok=False)

    def test_dependency_cache_symlink_rejected(self):
        self.dependencies()
        (self.target / ".codex-config-deps").symlink_to(self.work / "outside", target_is_directory=True)
        self.run_helper("stage", ok=False)

    def test_concurrent_preparation_installs_once(self):
        self.dependencies()
        self.env["TEST_NPM_SLEEP"] = "0.15"
        self.run_helper("stage")
        command = ["python3", str(HELPER), "prepare", "--stage", str(self.staged)]
        procs = [subprocess.Popen(command, env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(2)]
        for proc in procs:
            out, err = proc.communicate(timeout=10)
            self.assertEqual(proc.returncode, 0, err)
        self.assertEqual(len(self.npm_log.read_text().splitlines()), 1)

    def test_sync_dry_run_never_installs_dependencies_or_hooks(self):
        self.dependencies()
        self.run_sync("--dry-run")
        self.assertEqual(list(self.target.iterdir()), [])
        self.assertFalse(self.npm_log.exists())

    def test_sync_hook_conflict_prevents_config_write(self):
        (self.target / "config.toml").write_text('model = "old"\n')
        (self.target / "hooks.json").write_text("custom")
        self.run_sync(ok=False)
        self.assertEqual((self.target / "config.toml").read_text(), 'model = "old"\n')
        self.assertEqual((self.target / "hooks.json").read_text(), "custom")

    def test_sync_dependency_failure_prevents_config_write(self):
        self.dependencies()
        self.env["TEST_NPM_FAIL"] = "1"
        (self.target / "config.toml").write_text('model = "old"\n')
        self.run_sync(ok=False)
        self.assertEqual((self.target / "config.toml").read_text(), 'model = "old"\n')
        self.assertFalse((self.target / "hooks.json").exists())

    def test_sync_manifest_optout_preserves_custom_hooks_without_prerequisites(self):
        (self.source / "hooks.json").unlink()
        shutil.rmtree(self.source / "hooks")
        (self.target / "hooks.json").write_text("custom")
        self.run_sync(overrides={"hooks": False})
        self.assertEqual((self.target / "hooks.json").read_text(), "custom")
        self.assertFalse((self.target / ".codex-config-managed-hooks.json").exists())


if __name__ == "__main__":
    unittest.main()
