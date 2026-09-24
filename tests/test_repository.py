import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from edon.cli import validate_repository


class RepositoryTests(unittest.TestCase):
    def test_repository_structure_and_claim_links(self):
        report = validate_repository(ROOT)
        self.assertEqual(report["status"], "PASS", report["errors"])
        self.assertEqual(report["experiments"], 26)

    def test_all_json_files_parse(self):
        for path in ROOT.rglob("*.json"):
            with self.subTest(path=path.relative_to(ROOT)):
                json.loads(path.read_text(encoding="utf-8"))

    def test_experiment_packages_have_required_files(self):
        registry = json.loads((ROOT / "experiments" / "registry.json").read_text(encoding="utf-8"))
        required = {"README.md", "PROTOCOL.md", "CLAIMS.md", "manifest.json"}
        for row in registry["experiments"]:
            path = ROOT / row["path"]
            self.assertTrue(required.issubset({item.name for item in path.iterdir()}), row["id"])


if __name__ == "__main__":
    unittest.main()