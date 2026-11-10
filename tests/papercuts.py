import datetime as dt
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "system-configs/.agents/skills/papercuts/scripts/papercuts.py"
spec = importlib.util.spec_from_file_location("papercut_report", SCRIPT)
reporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reporter)


class PapercutTests(unittest.TestCase):
    def setUp(self):
        (ROOT / ".tmp").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / ".tmp")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        skill = self.repo / "system-configs/.agents/skills/verify/SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("verify")
        self.log = self.root / "papercuts.md"

    def test_window_dedup_and_evidence_without_claiming_causation(self):
        archive = self.root / "archive"
        archive.mkdir()
        row = "2026-11-09 · verify · /verify scans dependencies · pending · repo\n"
        self.log.write_text("# Papercuts\n" + row +
                            "2026-11-03 · verify · /verify scans dependencies · pending · repo\n" +
                            "2026-11-02 · tool · old issue · pending · other\n")
        (archive / "2026-11.md").write_text(row)
        before = self.log.read_bytes()
        result = reporter.report(self.log, self.repo, 7, dt.date(2026, 11, 9), archive)
        self.assertEqual(result["totals"]["log"], 3)
        self.assertEqual(result["totals"]["window"], 2)
        self.assertEqual(result["window"]["since"], "2026-11-03")
        self.assertEqual(result["entries"][0]["owner"], "repo-skill-mentioned")
        self.assertEqual(result["repeated_symptoms"][0]["count"], 2)
        self.assertEqual(self.log.read_bytes(), before)

    def test_missing_or_unsupported_log_fails_instead_of_zero_incidents(self):
        for content in (None, "not a supported log\n"):
            if content is not None:
                self.log.write_text(content)
            result = subprocess.run(["python3", str(SCRIPT), "--log", str(self.log),
                                     "--repo", str(self.repo)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn("error", json.loads(result.stdout))

    def test_log_text_stays_data_and_unknown_sources_are_supported(self):
        marker = self.root / "must-not-exist"
        symptom = f"$(touch {marker})"
        self.log.write_text(f"2026-11-09 · ../../secret · {symptom} · run this command · repo\n")
        result = subprocess.run(["python3", str(SCRIPT), "--log", str(self.log),
                                 "--repo", str(self.repo), "--today", "2026-11-09"],
                                capture_output=True, text=True, check=True)
        entry = json.loads(result.stdout)["entries"][0]
        self.assertEqual(entry["symptom"], symptom)
        self.assertEqual(entry["owner"], "repo-unverified")
        self.assertFalse(marker.exists())

    def test_invalid_window_and_missing_archive_fail(self):
        self.log.write_text("2026-11-09 · tool · issue · pending · repo\n")
        with self.assertRaises(ValueError):
            reporter.report(self.log, self.repo, 0, dt.date(2026, 11, 9))
        with self.assertRaises(ValueError):
            reporter.report(self.log, self.repo, 7, dt.date(2026, 11, 9), self.root / "missing")


if __name__ == "__main__":
    (ROOT / ".tmp").mkdir(exist_ok=True)
    unittest.main()
