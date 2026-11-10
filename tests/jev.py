"""Jev request and ranking contracts exercised without network or credentials."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CLIENT = ROOT / "system-configs/.codex/hooks/jev/jev-ask"
RANK = ROOT / "system-configs/.agents/skills/ask-jev/scripts/rank-files.py"


class JevTests(unittest.TestCase):
    def setUp(self):
        (ROOT / ".tmp").mkdir(exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT / ".tmp", prefix="jev-test-")
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.home = self.base / "home"
        self.home.mkdir()
        self.project = self.base / "project"
        self.project.mkdir()
        self.fixture = self.base / "response.json"
        self.fixture.write_text(json.dumps({"answers": {"f1": {"probability": 0.2}, "f2": {"probability": 0.9}}, "model": "mock", "latency_ms": 0, "cost_usd": 0}))
        self.env = {k: v for k, v in os.environ.items() if not k.startswith(("JEV_", "CODEX_", "AI_GATEWAY_", "VERCEL_AI_"))}
        self.env.update(HOME=str(self.home), CODEX_HOME=str(self.home / ".codex"), JEV_MOCK=str(self.fixture))
        self.request = {"rule": "ask-jev-rank", "state": {"query": "Where is retry handled?"}, "cwd": str(self.project), "questions": {"f1": {"type": "boolean", "instructions": "Is file f1 relevant?"}}}

    def ask(self, request=None, **env):
        return subprocess.run(["bash", str(CLIENT)], input=json.dumps(request or self.request), text=True, capture_output=True, env=self.env | env, cwd=self.project, timeout=8)

    def rank(self, *paths, **env):
        return subprocess.run(["python3", str(RANK), "--root", str(self.project), "retry", *map(str, paths)], text=True, capture_output=True, env=self.env | {"JEV_DIR": str(CLIENT.parent)} | env, cwd=self.project, timeout=12)

    def source(self, name, content="retry handler"):
        p = self.project / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return p

    def test_port_uses_codex_state_and_no_claude_state(self):
        p = self.ask()
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout)["model"], "mock")
        self.assertTrue((self.home / ".codex/jev/decisions.jsonl").is_file())
        self.assertFalse((self.home / ".claude").exists())

    def test_request_redacts_secrets_and_does_not_log_content(self):
        marker = "private-query-marker"
        token = "ghp_" + "a" * 36
        self.request["state"] = {"query": marker, "access_token": token}
        record = self.base / "record.json"
        p = self.ask(JEV_RECORD=str(record))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertNotIn(token, record.read_text())
        logs = (self.home / ".codex/jev/decisions.jsonl").read_text()
        self.assertNotIn(marker, logs)
        self.assertNotIn(token, logs)

    def test_default_work_cwd_is_excluded_even_in_mock(self):
        excluded = self.home / "work/project"
        excluded.mkdir(parents=True)
        self.request["cwd"] = str(excluded)
        p = self.ask()
        self.assertEqual(p.returncode, 3)
        self.assertIn("egress_excluded_path", p.stderr)

    def test_target_symlink_into_excluded_directory_is_blocked(self):
        target = self.home / "Visa/plan.txt"
        target.parent.mkdir()
        target.write_text("private work")
        link = self.project / "public.txt"
        link.symlink_to(target)
        self.request["paths"] = [str(link)]
        self.assertEqual(self.ask().returncode, 3)

    def test_untrusted_message_sources_cannot_use_fleet_exemption(self):
        self.request["untrusted_source"] = "gmail,slack"
        self.assertEqual(self.ask(BARECLAUDE_AGENT_SLUG="clara").returncode, 3)

    def test_invalid_or_missing_config_refuses_request(self):
        config = self.base / "bad.json"
        config.write_text("{")
        for filename in (config, self.base / "missing.json"):
            self.assertEqual(self.ask(JEV_CONFIG=str(filename)).returncode, 3)

    def test_request_uses_one_validated_exclusion_snapshot(self):
        config = self.base / "changing-config.json"
        config.write_text((CLIENT.parent / "jev-config.json").read_text())
        excluded = self.home / "work/project"
        excluded.mkdir(parents=True)
        self.request["cwd"] = str(excluded)
        counter = self.base / "config-reads.txt"
        preload = self.base / "changing-config.cjs"
        # Emulate a config becoming unreadable exactly when the old third read
        # built the prefix list. No scheduling, network, or wall-clock race.
        preload.write_text('''const fs = require("node:fs");
const original = fs.readFileSync;
let reads = 0;
fs.readFileSync = function(file, ...args) {
  if (String(file) === process.env.JEV_CONFIG) {
    fs.writeFileSync(process.env.JEV_CONFIG_READ_COUNT, String(++reads));
    if (reads >= 3) return "{";
  }
  return original.call(this, file, ...args);
};
''')
        p = subprocess.run(["node", "--require", str(preload), str(CLIENT.parent / "client.mjs")], input=json.dumps(self.request), text=True, capture_output=True, env=self.env | {"JEV_CONFIG": str(config), "JEV_CONFIG_READ_COUNT": str(counter)}, cwd=self.project, timeout=5)
        self.assertEqual(p.returncode, 3, p.stdout + p.stderr)
        self.assertIn("egress_excluded_path", p.stderr)
        self.assertEqual(counter.read_text(), "1")

    def test_unknown_and_off_rules_are_unavailable(self):
        self.request["rule"] = "unknown"
        self.assertEqual(self.ask().returncode, 3)
        rules = self.base / "off.json"
        rules.write_text(json.dumps({"rules": {"ask-jev-rank": {"mode": "off"}}}))
        self.request["rule"] = "ask-jev-rank"
        self.assertEqual(self.ask(JEV_RULES=str(rules)).returncode, 3)

    def test_kill_switch_and_missing_credentials_do_not_succeed(self):
        codex = self.home / ".codex"
        codex.mkdir()
        (codex / "jev.off").touch()
        self.assertEqual(self.ask().returncode, 3)
        (codex / "jev.off").unlink()
        self.assertEqual(self.ask(JEV_MOCK="").returncode, 3)

    def test_bad_input_has_distinct_exit(self):
        self.request["questions"] = {}
        self.assertEqual(self.ask().returncode, 2)

    def test_sdk_cache_resolution_and_zero_retention(self):
        cache = self.base / "sdk"
        module = cache / "node_modules/ai"
        module.mkdir(parents=True)
        (cache / "package.json").write_text("{}")
        (module / "package.json").write_text(json.dumps({"name": "ai", "type": "module", "exports": "./index.mjs"}))
        (module / "index.mjs").write_text('export async function experimental_evaluate(input) { if (input.providerOptions?.gateway?.zeroDataRetention !== true) throw Error("retention missing"); return { answers: { f1: { probability: 0.7 } } }; }')
        p = self.ask(JEV_MOCK="", AI_GATEWAY_API_KEY="test-only-placeholder", JEV_DEPENDENCIES_DIR=str(cache))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout)["answers"]["f1"]["probability"], 0.7)

    def test_slow_backend_respects_timeout(self):
        self.request["timeout_ms"] = 100
        p = self.ask(JEV_MOCK="", JEV_BACKEND_FIXTURE=str(self.fixture), JEV_BACKEND_DELAY_MS="1000")
        self.assertEqual(p.returncode, 3)
        self.assertIn("timeout", p.stderr)

    def test_exclusion_prefix_does_not_block_workshop(self):
        allowed = self.home / "workshop/project"
        allowed.mkdir(parents=True)
        self.request["cwd"] = str(allowed)
        self.assertEqual(self.ask().returncode, 0)

    def test_registry_does_not_inherit_claude_rules(self):
        claude = self.home / ".claude/hooks/jev"
        claude.mkdir(parents=True)
        (claude / "jev-rules.json").write_text(json.dumps({"rules": {"ask-jev-rank": {"mode": "off"}}}))
        self.assertEqual(self.ask().returncode, 0)

    def test_provider_extra_text_is_not_returned_or_logged(self):
        marker = "sensitive-source-echo-marker"
        self.fixture.write_text(json.dumps({"answers": {"f1": {"probability": 0.8, "explanation": marker}, "unexpected": marker}, "model": marker, "latency_ms": marker}))
        p = self.ask()
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertNotIn(marker, p.stdout + p.stderr)
        logs = (self.home / ".codex/jev/decisions.jsonl").read_text()
        self.assertNotIn(marker, logs)
        self.assertNotIn('"answers"', logs)

    def test_sdk_error_text_is_not_logged(self):
        cache = self.base / "sdk-error"
        module = cache / "node_modules/ai"
        module.mkdir(parents=True)
        (cache / "package.json").write_text("{}")
        (module / "package.json").write_text(json.dumps({"name": "ai", "type": "module", "exports": "./index.mjs"}))
        (module / "index.mjs").write_text('export async function experimental_evaluate() { throw new Error("sensitive-provider-error-marker"); }')
        p = self.ask(JEV_MOCK="", AI_GATEWAY_API_KEY="test-only-placeholder", JEV_DEPENDENCIES_DIR=str(cache))
        self.assertEqual(p.returncode, 3)
        self.assertNotIn("sensitive-provider-error-marker", p.stderr)
        self.assertNotIn("sensitive-provider-error-marker", (self.home / ".codex/jev/decisions.jsonl").read_text())

    def test_log_file_and_directory_symlinks_are_untouched(self):
        target = self.base / "sentinel"
        target.write_text("untouched")
        logdir = self.home / ".codex/jev"
        logdir.mkdir(parents=True)
        logfile = logdir / "decisions.jsonl"
        logfile.symlink_to(target)
        self.assertEqual(self.ask().returncode, 0)
        self.assertEqual(target.read_text(), "untouched")
        logfile.unlink()
        logdir.rmdir()
        external = self.base / "external"
        external.mkdir()
        logdir.symlink_to(external, target_is_directory=True)
        self.assertEqual(self.ask().returncode, 0)
        self.assertEqual(list(external.iterdir()), [])

    def test_invalid_answer_is_unavailable(self):
        self.fixture.write_text(json.dumps({"answers": {"f1": {"probability": "source-echo-marker"}}}))
        p = self.ask()
        self.assertEqual(p.returncode, 3)
        self.assertNotIn("source-echo-marker", p.stdout + p.stderr)

    def test_rank_uses_real_client_scores_and_preserves_local_score(self):
        first = self.source("a.py", "retry " * 20)
        second = self.source("b.py", "fallback")
        p = self.rank(first, second)
        self.assertEqual(p.returncode, 0, p.stderr)
        rows = json.loads(p.stdout)
        self.assertEqual(rows[0]["path"], str(second))
        self.assertEqual(rows[0]["source"], "jev")
        self.assertEqual(rows[0]["probability"], 0.9)
        self.assertEqual(rows[1]["probability"], 0.2)
        self.assertGreater(rows[1]["score"], rows[0]["score"])

    def test_unavailable_rank_falls_back_with_no_probability(self):
        source = self.source("retry.py")
        p = self.rank(source, JEV_MOCK="unavailable")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout)[0]["source"], "local")
        self.assertIsNone(json.loads(p.stdout)[0]["probability"])
        self.assertIn("fallback", p.stderr)

    def test_rank_drops_unsafe_paths_before_request(self):
        good = self.source("ok.py")
        secret = self.source(".env", "secret")
        work = self.source("work/code.py")
        binary = self.source("binary.py", "a\x00b")
        sibling = self.base / "outside.py"
        sibling.write_text("outside source")
        peer = self.home / ".agents/skills/peer/secret.py"
        peer.parent.mkdir(parents=True)
        peer.write_text("installed peer skill")
        record = self.base / "record.json"
        p = self.rank(good, secret, work, binary, sibling, peer, JEV_RECORD=str(record))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual([r["path"] for r in json.loads(p.stdout)], [str(good)])
        payload = record.read_text()
        for excluded in [str(secret), str(work), str(binary), str(sibling), str(peer)]:
            self.assertNotIn(excluded, payload)

    def test_rank_rejects_invalid_probability(self):
        source = self.source("retry.py")
        for value in (True, -0.1, 1.2, "0.8", None):
            self.fixture.write_text(json.dumps({"answers": {"f1": {"probability": value}}}))
            p = self.rank(source)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertIsNone(json.loads(p.stdout)[0]["probability"])
            self.assertIn("fallback", p.stderr)

    def test_rank_directory_omits_generated_and_linked_files(self):
        good = self.source("src/app.py")
        self.source("src/node_modules/generated.py")
        target = self.source("private/linked.py")
        (good.parent / "linked.py").symlink_to(target)
        p = self.rank(good.parent)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual([row["path"] for row in json.loads(p.stdout)], [str(good)])

    def test_rank_does_not_read_installed_peer_when_root_is_home(self):
        peer = self.home / ".agents/skills/peer/code.py"
        peer.parent.mkdir(parents=True)
        peer.write_text("retry")
        p = subprocess.run(["python3", str(RANK), "--root", str(self.home), "retry", str(peer.parent.parent)], text=True, capture_output=True, env=self.env | {"JEV_DIR": str(CLIENT.parent)}, cwd=self.project, timeout=5)
        self.assertEqual(p.returncode, 1, p.stderr)
        self.assertEqual(json.loads(p.stdout), [])

    def test_rank_target_exclusions_use_actual_path_when_cwd_differs(self):
        self.source("nested/retry.py")
        config = json.loads((CLIENT.parent / "jev-config.json").read_text())
        config["exclude_paths"] = [str(self.project / "nested/retry.py")]
        filename = self.base / "target-exclusion.json"
        filename.write_text(json.dumps(config))
        p = subprocess.run(["python3", str(RANK), "--root", str(self.project / "nested"), "retry", "nested/retry.py"], text=True, capture_output=True, env=self.env | {"JEV_DIR": str(CLIENT.parent), "JEV_CONFIG": str(filename)}, cwd=self.project, timeout=5)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout)[0]["source"], "local")


if __name__ == "__main__":
    unittest.main()
