import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from edon.compiler import CompilerInputError, compile_institution


class InstitutionCompilerTests(unittest.TestCase):
    example = ROOT / "examples" / "hospital" / "compiler-input.json"

    def test_example_compiles_and_preserves_conflicts(self):
        result = compile_institution(self.example)
        self.assertTrue(result["qualification"]["passed"])
        self.assertFalse(result["binding_authority"])
        self.assertEqual(result["extraction_summary"]["mechanism_count"], 2)
        self.assertGreaterEqual(result["extraction_summary"]["conflict_count"], 2)

        candidates = {row["mechanism"]["mechanism_id"]: row for row in result["candidates"]}
        medication = candidates["medication-release"]
        inventory = candidates["inventory-audit"]
        self.assertTrue(medication["focused_review_required"])
        self.assertEqual(medication["required_reviewer_role"], "DOMAIN_AND_SAFETY_REVIEWER")
        self.assertFalse(inventory["focused_review_required"])
        self.assertTrue(all(not row["mechanism"]["approved"] for row in candidates.values()))
        self.assertTrue(all(not row["binding_authority"] for row in candidates.values()))

    def test_compilation_is_deterministic(self):
        first = compile_institution(self.example)
        second = compile_institution(self.example)
        self.assertEqual(first, second)
        self.assertEqual(
            first["compiler_manifest"]["compiled_payload_sha256"],
            second["compiler_manifest"]["compiled_payload_sha256"],
        )

    def test_wrong_declared_source_hash_is_rejected(self):
        raw = json.loads(self.example.read_text(encoding="utf-8"))
        raw["sources"][0]["sha256"] = "sha256:" + "0" * 64
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.json"
            path.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaisesRegex(CompilerInputError, "source hash mismatch"):
                compile_institution(path)

    def test_path_traversal_is_rejected(self):
        raw = {
            "schema_version": "edon-institution-compiler-input.v1",
            "compiler_run_id": "bad-path",
            "institution_id": "example",
            "institution_version": "v1",
            "sources": [{
                "source_id": "bad",
                "version": "v1",
                "truth_layer": "NORMATIVE",
                "kind": "POLICY",
                "format": "STRUCTURED_JSON",
                "path": "../outside.json"
            }]
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.json"
            path.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaisesRegex(CompilerInputError, "stay within"):
                compile_institution(path)

    def test_missing_normative_layer_is_routed_for_review(self):
        raw = {
            "schema_version": "edon-institution-compiler-input.v1",
            "compiler_run_id": "missing-normative",
            "institution_id": "example",
            "institution_version": "v1",
            "sources": [{
                "source_id": "system",
                "version": "v1",
                "truth_layer": "OPERATIONAL",
                "kind": "CONFIG",
                "format": "STRUCTURED_JSON",
                "content": {"statements": [{
                    "mechanism_id": "routing",
                    "primitive_type": "RESOURCE",
                    "subject": "queue",
                    "predicate": "capacity",
                    "value": 10,
                    "confidence": 0.99,
                    "risk_class": "LOW"
                }]}
            }]
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.json"
            path.write_text(json.dumps(raw), encoding="utf-8")
            result = compile_institution(path)
        candidate = result["candidates"][0]
        self.assertTrue(candidate["focused_review_required"])
        self.assertIn("NORMATIVE_SOURCE_MISSING", candidate["failed_checks"])
        self.assertEqual(result["conflicts"][0]["kind"], "MISSING_NORMATIVE")

    def test_invalid_schema_version_is_rejected(self):
        raw = json.loads(self.example.read_text(encoding="utf-8"))
        raw["schema_version"] = "unsupported"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.json"
            path.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaisesRegex(CompilerInputError, "schema_version"):
                compile_institution(path)

    def test_bundle_relative_structured_source_is_loaded(self):
        source = {"statements": [{
            "mechanism_id": "records",
            "primitive_type": "POLICY",
            "subject": "records",
            "predicate": "retention",
            "value": "seven_years",
            "confidence": 1.0,
            "risk_class": "LOW"
        }]}
        raw = {
            "schema_version": "edon-institution-compiler-input.v1",
            "compiler_run_id": "path-source",
            "institution_id": "example",
            "institution_version": "v1",
            "sources": [{
                "source_id": "records-policy",
                "version": "v1",
                "truth_layer": "NORMATIVE",
                "kind": "POLICY",
                "format": "STRUCTURED_JSON",
                "path": "sources/records.json"
            }]
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "sources").mkdir()
            (root / "sources" / "records.json").write_text(json.dumps(source), encoding="utf-8")
            path = root / "input.json"
            path.write_text(json.dumps(raw), encoding="utf-8")
            result = compile_institution(path)
        self.assertEqual(result["source_manifest"][0]["locator"], "sources/records.json")
        self.assertEqual(result["candidates"][0]["mechanism"]["policies"], [
            "records:retention:seven_years"
        ])


if __name__ == "__main__":
    unittest.main()