"""Behavior tests for experiment evidence, execution limits, and resumability."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "system-configs/.agents/skills/experiment/scripts"


class ExperimentHelpers(unittest.TestCase):
    def setUp(self):
        (ROOT / ".tmp").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="experiment-tests-", dir=ROOT / ".tmp")
        self.directory = Path(self.temp.name)
        self.protocol = {
            "question": "Does a successful command produce an observed true result?",
            "hypothesis": "The treatment succeeds and the control fails.",
            "prediction": "Treatment has rate one and negative control has rate zero.",
            "if_false": "The treatment has a rate less than one.",
            "side_effects": "local", "evidence_kind": "observed",
            "pass_rule": {"type": "rate", "condition": "treatment", "op": ">=", "value": 1},
            "controls": [{"condition": "negative-control", "expect": "fail"}],
        }
        self.plan = {"reps": 2, "timeout_s": 1, "budget_s": 10, "seed": 1,
                     "conditions": [{"name": "treatment", "cmd": "true"},
                                    {"name": "negative-control", "cmd": "false"}]}
        self.save()

    def tearDown(self):
        self.temp.cleanup()

    def save(self):
        for name, data in (("protocol.json", self.protocol), ("plan.json", self.plan)):
            (self.directory / name).write_text(json.dumps(data))

    def call(self, script, *args, code=0, env=None):
        prefix = ["bash"] if script.endswith(".sh") else [sys.executable]
        result = subprocess.run(prefix + [str(SCRIPTS / script), str(self.directory), *args],
                                text=True, capture_output=True, timeout=20,
                                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", **(env or {})})
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return result

    def lock(self):
        self.save()
        self.call("lock.sh")

    def score(self, code=0):
        self.call("score.py", "--json", code=code)
        return json.loads((self.directory / "verdict.json").read_text())

    def rows(self):
        return [json.loads(line) for line in (self.directory / "runs.jsonl").read_text().splitlines()]

    def test_local_trials_resume_without_duplicate_evidence(self):
        self.lock()
        self.call("run.py", "--execute-local")
        first = (self.directory / "runs.jsonl").read_bytes()
        self.call("run.py", "--execute-local")
        self.assertEqual((self.directory / "runs.jsonl").read_bytes(), first)
        result = self.score()
        self.assertEqual(result["verdict"], "SUPPORTED")
        self.assertEqual(result["stats"]["treatment"]["n"], 2)
        self.assertEqual(result["evidence_kind"], "observed")
        self.assertEqual(result["evidence_sha256"]["runs.jsonl"], hashlib.sha256(first).hexdigest())
        self.assertFalse((self.directory / ".runner-lock").exists())
        self.call("lock.sh", code=65)

    def test_edited_protocol_cannot_execute_or_score(self):
        self.lock()
        self.protocol["pass_rule"]["value"] = 0
        self.save()
        self.call("run.py", "--execute-local", code=3)
        self.call("score.py", code=3)
        self.assertFalse((self.directory / "runs.jsonl").exists())

    def test_explicit_execution_required(self):
        self.lock()
        self.call("run.py", code=2)
        self.assertFalse((self.directory / "runs.jsonl").exists())

    def test_external_protocol_never_executes_commands(self):
        self.protocol["side_effects"] = "external"
        self.plan["conditions"][0]["cmd"] = "touch marker"
        self.lock()
        self.call("run.py", "--execute-local", code=3)
        self.assertFalse((self.directory / "work/marker").exists())

    def test_tampered_lock_classification_is_rejected(self):
        self.protocol["side_effects"] = "external"
        self.lock()
        lock = json.loads((self.directory / "lock.json").read_text())
        lock["side_effects"] = "local"
        (self.directory / "lock.json").write_text(json.dumps(lock))
        self.call("run.py", "--execute-local", code=3)

    def test_changed_captured_output_invalidates_evidence(self):
        self.lock()
        self.call("run.py", "--execute-local")
        output = self.directory / "runs/treatment-1.out"
        output.write_text("changed after observation")
        result = self.call("score.py", code=3)
        self.assertIn("evidence changed", result.stderr)

    def test_blind_judgment_uses_anonymized_actual_outputs(self):
        self.plan["conditions"][0].update({"cmd": "printf measured-output", "observe": "judge"})
        self.lock()
        self.call("run.py", "--execute-local")
        self.score(code=2)
        result = subprocess.run([sys.executable, str(SCRIPTS / "score.py"), "--export-blind", str(self.directory)],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        items = [json.loads(line) for line in (self.directory / "blind/items.jsonl").read_text().splitlines()]
        self.assertEqual(len(items), 2)
        self.assertTrue(all(set(item) == {"id", "output"} for item in items))
        self.assertTrue(all(item["output"] == "measured-output" for item in items))
        (self.directory / "blind/judgments.jsonl").write_text("".join(
            json.dumps({"id": item["id"], "value": True, "reason": "matches fixed rubric"}) + "\n"
            for item in items))
        self.score()

    def test_bad_control_makes_verdict_inconclusive(self):
        self.plan["conditions"][1]["cmd"] = "true"
        self.lock()
        self.call("run.py", "--execute-local")
        result = self.score(code=2)
        self.assertIn("control negative-control", result["why"])

    def test_failed_observer_is_invalid_even_if_stdout_says_true(self):
        self.plan["conditions"][0]["observe"] = "printf true; exit 7"
        self.lock()
        self.call("run.py", "--execute-local")
        result = self.score(code=2)
        self.assertEqual(result["stats"]["treatment"]["invalid"], 2)
        self.assertEqual(result["stats"]["treatment"]["n"], 0)

    def test_empty_observer_output_is_missing_evidence(self):
        self.plan["conditions"][0]["observe"] = "true"
        self.lock()
        self.call("run.py", "--execute-local")
        result = self.score(code=2)
        self.assertEqual(result["stats"]["treatment"]["invalid"], 2)
        self.assertEqual(result["stats"]["treatment"]["n"], 0)
        self.assertTrue(all(r.get("value") is None and "empty" in r.get("error", "")
                            for r in self.rows() if r["condition"] == "treatment"))

    def test_whitespace_observer_cannot_satisfy_negative_control(self):
        self.plan["conditions"][1]["observe"] = "printf '  \\n\\t '"
        self.lock()
        self.call("run.py", "--execute-local")
        result = self.score(code=2)
        self.assertEqual(result["stats"]["negative-control"]["invalid"], 2)

    def test_explicit_false_and_zero_observations_remain_valid(self):
        self.plan["conditions"][1]["observe"] = 'if [ "$EXPERIMENT_REP" = 1 ]; then printf false; else printf 0; fi'
        self.lock()
        self.call("run.py", "--execute-local")
        result = self.score()
        self.assertEqual(result["stats"]["negative-control"]["invalid"], 0)
        self.assertEqual(result["stats"]["negative-control"]["n"], 2)

    def test_explicit_json_empty_string_remains_an_observation(self):
        self.plan["conditions"][1]["observe"] = "printf '\"\"'"
        self.lock()
        self.call("run.py", "--execute-local")
        result = self.score()
        self.assertEqual(result["stats"]["negative-control"]["n"], 2)
        self.assertTrue(all(r["value"] == "" and "error" not in r
                            for r in self.rows() if r["condition"] == "negative-control"))

    def test_manual_blind_export_reads_recorded_evidence(self):
        self.protocol["side_effects"] = "external"
        self.plan["reps"] = 1
        self.plan["conditions"][0]["observe"] = "judge"
        self.lock()
        evidence = self.directory / "actual-response.txt"
        evidence.write_text("The actual response captured from the authorized external trial.\n")
        self.call("run.py", "--record", "treatment", "1", "null", "--evidence", evidence.name)
        result = subprocess.run([sys.executable, str(SCRIPTS / "score.py"), "--export-blind", str(self.directory)],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        items = [json.loads(line) for line in (self.directory / "blind/items.jsonl").read_text().splitlines()]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["output"], evidence.read_text())

    def test_blind_export_refuses_changed_evidence(self):
        self.plan["conditions"][0].update({"cmd": "printf actual-output", "observe": "judge"})
        self.lock()
        self.call("run.py", "--execute-local")
        (self.directory / "runs/treatment-1.out").write_text("changed output")
        result = subprocess.run([sys.executable, str(SCRIPTS / "score.py"), "--export-blind", str(self.directory)],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
        self.assertIn("evidence changed", result.stderr)
        self.assertFalse((self.directory / "blind/items.jsonl").exists())

    def test_timeout_cannot_be_counted_as_a_negative_control(self):
        self.plan["reps"] = 1
        self.plan["conditions"][1]["cmd"] = "sleep 2"
        self.lock()
        self.call("run.py", "--execute-local")
        result = self.score(code=2)
        self.assertEqual(result["stats"]["negative-control"]["invalid"], 1)
        self.assertEqual(next(r for r in self.rows() if r["condition"] == "negative-control")["exit"], 124)

    def test_missing_data_and_simulation_label_remain_explicit(self):
        self.protocol["evidence_kind"] = "simulated"
        self.lock()
        result = self.score(code=2)
        self.assertEqual(result["evidence_kind"], "simulated")
        self.assertEqual(result["stats"]["treatment"]["recorded"], 0)

    def test_manual_observation_requires_evidence_and_plan_membership(self):
        self.protocol["side_effects"] = "external"
        self.lock()
        self.call("run.py", "--record", "treatment", "1", "true", code=3)
        (self.directory / "observed.json").write_text('{"actual_result": true}')
        args = ["--evidence", "observed.json"]
        self.call("run.py", "--record", "treatment", "3", "true", *args, code=3)
        self.call("run.py", "--record", "treatment", "1", "true", *args)
        self.call("run.py", "--record", "treatment", "1", "false", *args, code=3)
        self.assertEqual(len(self.rows()), 1)
        self.assertEqual(self.rows()[0]["source"], "manual")

    def test_lock_ownership_prevents_a_second_writer(self):
        self.lock()
        (self.directory / ".runner-lock").mkdir()
        self.call("run.py", "--execute-local", code=3)
        self.call("lock.sh", code=65)
        self.assertTrue((self.directory / ".runner-lock").is_dir())

    def test_clean_environment_and_scratch_home(self):
        self.plan["conditions"][0]["cmd"] = 'test -z "${EXPERIMENT_TEST_SECRET:-}" && test "$HOME" = "$EXPERIMENT_HOME"'
        self.lock()
        self.call("run.py", "--execute-local", env={"EXPERIMENT_TEST_SECRET": "do-not-propagate"})
        self.score()

    def test_mean_requires_numeric_observation_for_every_trial(self):
        self.protocol["pass_rule"] = {"type": "mean", "condition": "treatment", "op": ">=", "value": 0.5}
        self.plan["conditions"][0]["observe"] = 'if [ "$EXPERIMENT_REP" = 1 ]; then printf 1; else printf nope; fi'
        self.lock()
        self.call("run.py", "--execute-local")
        result = self.score(code=2)
        self.assertEqual(result["stats"]["treatment"]["numeric_n"], 1)

    def test_out_of_range_rows_do_not_change_verdict(self):
        self.lock()
        self.call("run.py", "--execute-local")
        with (self.directory / "runs.jsonl").open("a") as out:
            out.write(json.dumps({"condition": "treatment", "rep": 999, "value": False}) + "\n")
            out.write(json.dumps({"condition": "treatment", "rep": 1, "value": False}) + "\n")
        self.score()

    def test_budget_exhaustion_does_not_run_missing_trials_on_resume(self):
        self.plan["reps"] = 1
        self.plan["timeout_s"] = 3
        self.plan["budget_s"] = 1
        self.plan["conditions"][0]["cmd"] = "sleep 2"
        self.lock()
        # The total budget is checked between trials; the last trial can consume
        # the budget and complete the loop with invalid timeout evidence.
        result = subprocess.run([sys.executable, str(SCRIPTS / "run.py"), str(self.directory), "--execute-local"],
                                capture_output=True, text=True, timeout=10)
        self.assertIn(result.returncode, (0, 2), result.stderr)
        before = (self.directory / "runs.jsonl").read_text()
        self.score(code=2)
        result = subprocess.run([sys.executable, str(SCRIPTS / "run.py"), str(self.directory), "--execute-local"],
                                capture_output=True, text=True, timeout=10)
        self.assertIn(result.returncode, (0, 2), result.stderr)
        self.assertEqual((self.directory / "runs.jsonl").read_text(), before)

    def test_supervisor_preserves_exit_and_kills_background_group(self):
        marker = self.directory / "background-marker"
        args = [sys.executable, str(SCRIPTS / "supervise.py"), "1", str(self.directory / "timeout"),
                "--", "bash", "-c", '(sleep 0.3; touch "$1") & exit 7', "bash", str(marker)]
        result = subprocess.run(args, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 7)
        time.sleep(0.4)
        self.assertFalse(marker.exists())


if __name__ == "__main__":
    unittest.main()
