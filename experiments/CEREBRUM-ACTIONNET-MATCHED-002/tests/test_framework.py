import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("matched002_run", ROOT / "run.py")
run = importlib.util.module_from_spec(spec); spec.loader.exec_module(run)


class FrameworkTests(unittest.TestCase):
    def test_preflight_is_blocked(self):
        value = run.preflight()
        self.assertEqual(value["responses"], 192)
        self.assertFalse(value["transfer_authorized"])

    def test_instrument_is_fresh_and_complete(self):
        with tempfile.TemporaryDirectory(dir=".") as tmp:
            destination = Path(tmp) / "instrument"
            report = run.prepare_instrument(destination)
            self.assertEqual((report["records"], report["pairs"]), (48, 24))
            self.assertEqual(run.file_hash(destination / "qualification-reference.jsonl"), report["reference_sha256"])
            self.assertEqual(run.file_hash(destination / "qualification-inputs.jsonl"), report["inputs_sha256"])

    def test_unresolved_study_cannot_register(self):
        study = run.read(ROOT / "study.template.json")
        with self.assertRaises(ValueError):
            run.validate_study(study, True)


if __name__ == "__main__":
    unittest.main()