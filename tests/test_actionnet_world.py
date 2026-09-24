import hashlib
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from edon.actionnet import available_worlds, generate_world, load_world


EXPECTED = {
    "001": ({"train": 480, "development": 120, "public_holdout": 120}, 29),
    "002": ({"train": 480, "development": 120, "public_holdout": 120}, 33),
    "003": ({"train": 3600, "repair_validation": 300}, 23),
    "004": ({"train": 5040, "repair_validation": 420}, 31),
    "005": ({"train": 5040, "repair_validation": 420}, 31),
    "006": ({"train": 8064, "repair_validation": 1344}, 35),
    "007": ({"train": 16128, "repair_validation": 1344}, 37),
    "008": ({"authoring_candidates": 4032, "heldout_authoring_validation": 1008}, 42),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CompleteActionNetWorldTests(unittest.TestCase):
    def test_all_versioned_generators_load(self):
        self.assertEqual(available_worlds(), tuple(EXPECTED))
        for version in EXPECTED:
            with self.subTest(version=version):
                self.assertTrue(callable(load_world(version).generate))

    def test_generated_corpora_and_controls_are_complete(self):
        for version, (counts, control_count) in EXPECTED.items():
            package = ROOT / "experiments" / f"ACTIONNET-DATA-QUAL-{version}"
            report = json.loads(
                (package / "results" / "qualification_report.json").read_text(encoding="utf-8")
            )
            self.assertEqual(report["control_count"], control_count)
            self.assertEqual(report["controls_passed"], control_count)
            self.assertTrue(all(report["controls"].values()))
            for split, expected_count in counts.items():
                filename = "public_holdout_inputs.jsonl" if split == "public_holdout" else f"{split}.jsonl"
                path = package / "dataset" / filename
                with self.subTest(version=version, split=split):
                    self.assertTrue(path.is_file())
                    with path.open("r", encoding="utf-8") as handle:
                        self.assertEqual(sum(1 for line in handle if line.strip()), expected_count)

    def test_latest_multidomain_world_is_runtime_loadable_but_not_training_eligible(self):
        generated = generate_world("008")
        self.assertEqual(len(generated["datasets"]["authoring_candidates"]), 4032)
        self.assertEqual(len(generated["datasets"]["heldout_authoring_validation"]), 1008)
        self.assertTrue(all(generated["controls"].values()))
        self.assertTrue(
            all(
                row["metadata"]["training_eligible"] is False
                for rows in generated["datasets"].values()
                for row in rows
            )
        )

    def test_checksum_inventories_match_materialized_files(self):
        for version in EXPECTED:
            package = ROOT / "experiments" / f"ACTIONNET-DATA-QUAL-{version}"
            checksum_file = package / "results" / "checksums.sha256"
            if checksum_file.is_file():
                inventory = [
                    line.split("  ", 1)
                    for line in checksum_file.read_text(encoding="utf-8").splitlines()
                ]
            else:
                result_manifest = json.loads(
                    (package / "results" / "result_manifest.json").read_text(encoding="utf-8")
                )
                inventory = [
                    (value.removeprefix("sha256:"), relative)
                    for relative, value in result_manifest["artifacts"].items()
                ]
            for expected_hash, relative in inventory:
                path = package / relative
                with self.subTest(version=version, path=relative):
                    self.assertTrue(path.is_file())
                    self.assertEqual(sha256(path), expected_hash)

    def test_import_inventory_matches_preserved_sources(self):
        inventory = json.loads(
            (ROOT / "provenance" / "dataset-lineage" / "actionnet-world-import.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(inventory["versions"], list(EXPECTED))
        for record in inventory["records"]:
            destination = record["destination"]
            if any(part in destination for part in ("/lineage/", "/oracle/", "/results/")) and not destination.endswith("preserved_result_manifest.json"):
                # Campaign execution deterministically regenerates these active
                # artifacts. Their current bytes are covered by checksums above.
                continue
            path = ROOT / destination
            with self.subTest(path=destination):
                self.assertEqual("sha256:" + sha256(path), record["sha256"])

    def test_data_qual_005_preserves_archived_manifest_separately(self):
        package = ROOT / "experiments" / "ACTIONNET-DATA-QUAL-005"
        preserved = package / "results" / "preserved_result_manifest.json"
        active = package / "results" / "result_manifest.json"
        self.assertTrue(preserved.is_file())
        self.assertTrue(active.is_file())
        self.assertNotEqual(sha256(preserved), sha256(active))


if __name__ == "__main__":
    unittest.main()