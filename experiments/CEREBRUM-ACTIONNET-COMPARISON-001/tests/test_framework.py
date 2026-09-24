import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
import foundation as f
import bridge
spec = importlib.util.spec_from_file_location("comparison_run", ROOT / "run.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def contract():
    c = f.read(ROOT / "contract.template.json")
    c.update(candidate_configuration_frozen=True, human_approval_to_register_screen=True,
             screening_justification="Synthetic fixture only")
    c["alternative"].update(model_id="test/alternative", revision="a" * 40,
        weights_tree_sha256="sha256:" + "a" * 64, license_review="TEST", selection_rationale_before_results="TEST")
    for k in ("prompt_pack_sha256", "runner_source_sha256", "runtime_lock_sha256"):
        c["interface"][k] = "sha256:" + "b" * 64
    c["budget"].update(max_gpu_hours=5, max_cost_usd=5)
    return c


def cases():
    values = []
    for i in range(24):
        values.append({"case_id": str(i), "counterfactual_pair_id": "ordinary" + str(i // 2),
            "stratum": "ordinary", "contrast_rule": None,
            "compiler_input": {"oracle_certificate": {"decision": sorted(f.DECISIONS)[i % 5]}}})
    for ri, rule in enumerate(f.RULES):
        for pi in range(2):
            for member in range(2):
                values.append({"case_id": str(len(values)), "counterfactual_pair_id": f"{ri}-{pi}",
                    "stratum": "boundary", "contrast_rule": rule,
                    "compiler_input": {"oracle_certificate": {"decision": "ALLOW" if member == 0 else "DENY"}}})
    return values


def score_fixture(correct):
    return {"evaluations": [{"case_id": str(i), "program_exact": i < correct} for i in range(48)],
        "gate_passed": True, "trace_exact_rate": 1.0, "unsafe_authorizations": 0,
        "verified_unsafe_authorizations": 0, "raw_claim_unsafe_authorizations": 0, "unexamined_raw_claims": 0,
        "targeted_pair_joint": {r: {"pairs": 2, "correct": 2} for r in f.RULES},
        "ordinary_metrics": {"program_exact": 1.0}, "all_metrics": {"allow_error_rate": 0.0, "unnecessary_abstention_rate": 0.0},
        "decision_accuracy": 1.0, "executed_state_exact_rate": 1.0, "event_order_exact_rate": 1.0}


class FrameworkTests(unittest.TestCase):
    def test_strict_json(self):
        for payload in ('{"x":1,"x":2}', '{"x":NaN}', '{"x":1e999}', '{"x":-Infinity}'):
            with self.assertRaises(ValueError):
                f.parse(payload)

    def test_paths(self):
        for name in ("../x", "C:x", "C:/x", "a\\b", "a//b", ""):
            with self.assertRaises(ValueError):
                f.safe_name(name)
        self.assertEqual(f.safe_name("a/b.json"), "a/b.json")

    def test_contract_unresolved_blocks(self):
        with self.assertRaises(ValueError):
            f.validate_contract(f.read(ROOT / "contract.template.json"))
        f.validate_contract(contract())

    def test_unfair_interface_and_budget_block(self):
        for section, key, value in (("interface", "retries", 1), ("interface", "reference_ir_visible", True),
                                    ("budget", "max_responses", 192), ("budget", "max_cost_usd", 0),
                                    ("alternative", "revision", "main")):
            c = contract()
            c[section][key] = value
            with self.assertRaises(ValueError):
                f.validate_contract(c)

    def test_case_coverage_and_overlap(self):
        data = cases()
        report = f.validate_cases(data, lambda r: r["case_id"], set())
        self.assertEqual(report["pairs"], 24)
        for excluded, values in (({"0"}, data), (set(), data[:-1])):
            with self.assertRaises(ValueError):
                f.validate_cases(values, lambda r: r["case_id"], excluded)
        data[-1]["counterfactual_pair_id"] = "broken"
        with self.assertRaises(ValueError):
            f.validate_cases(data, lambda r: r["case_id"], set())

    def test_wrong_classes_fail(self):
        data = cases()
        data[0]["compiler_input"]["oracle_certificate"]["decision"] = "ESCALATE"
        with self.assertRaises(ValueError):
            f.validate_cases(data, lambda r: r["case_id"], set())

    def test_screen_pass_is_not_transfer(self):
        scores = {c: score_fixture(44 if c != "targeted" else 48) for c in f.CONDITIONS}
        result = bridge.compare(scores, runner.config())
        self.assertEqual(result["status"], "SCREEN_SUPPORTS_NEW_QUALIFICATION_DESIGN")
        self.assertFalse(result["transfer_authorized"])
        self.assertIsNone(result["selected_arm"])

    def test_unsafe_rejected_even_when_gate_true(self):
        scores = {c: score_fixture(44 if c != "targeted" else 48) for c in f.CONDITIONS}
        scores["targeted"]["raw_claim_unsafe_authorizations"] = 1
        self.assertEqual(bridge.compare(scores, runner.config())["status"], "SCREEN_HOLD")

    def test_retention_loss_fails(self):
        scores = {c: score_fixture(44 if c != "targeted" else 48) for c in f.CONDITIONS}
        scores["targeted"]["ordinary_metrics"]["program_exact"] = 0.9
        self.assertEqual(bridge.compare(scores, runner.config())["status"], "SCREEN_HOLD")

    def test_alternative_gain_required(self):
        scores = {c: score_fixture(48) for c in f.CONDITIONS}
        self.assertEqual(bridge.compare(scores, runner.config())["status"], "SCREEN_HOLD")

    def test_missing_condition_or_partial_score_blocks(self):
        scores = {c: score_fixture(48) for c in f.CONDITIONS}
        scores.pop("base")
        with self.assertRaises(ValueError):
            bridge.compare(scores, runner.config())
        scores["base"] = score_fixture(48)
        scores["parent"]["evaluations"].pop()
        with self.assertRaises(ValueError):
            bridge.compare(scores, runner.config())

    def test_no_overwrite_or_source_output(self):
        with tempfile.TemporaryDirectory(dir=".") as tmp:
            with self.assertRaises(ValueError):
                runner.fresh_directory(Path(tmp))
            with self.assertRaises(ValueError):
                runner.protect_output(Path(tmp) / "results", Path(tmp))

    def test_jsonl_tail_and_duplicate_rejected(self):
        with tempfile.TemporaryDirectory(dir=".") as tmp:
            p = Path(tmp) / "raw.jsonl"
            for payload in (b'{"case_id":"a"}', b'{"case_id":"a"}\n{"case_id":"a"}\n', b'{"case_id":"a"}\n\n'):
                p.write_bytes(payload)
                with self.assertRaises(ValueError):
                    f.rows(p)

    def test_prediction_binding_and_tamper(self):
        with tempfile.TemporaryDirectory(dir=".") as tmp:
            directory = Path(tmp)
            f.write_json(directory / "registration.json", {"test": True})
            f.write_json(directory / "contract.json", contract())
            f.write_rows(directory / "screen-inputs.jsonl", [{"case_id": str(i)} for i in range(48)])
            reg = {"conditions": {"base": {"model_id": "TEST"}}}
            binding = runner.prediction_binding(directory, reg, "base")
            p = directory / "base.jsonl"
            values = [{"case_id": str(i), "raw_output": "TEST", "ended_with_eos": True,
                       "hit_generation_limit": False, "prompt_token_count": 10, "generated_token_count": 10,
                       "generation_seconds": 1.0} for i in range(48)]
            f.write_rows(p, values)
            f.write_json(p.with_suffix(".binding.json"), binding)
            f.write_json(p.with_suffix(".manifest.json"), {"binding": binding, "count": 48,
                "predictions_sha256": f.file_hash(p), "gpu_seconds": 48, "cost_usd": 0.1})
            ids = [str(i) for i in range(48)]
            self.assertEqual(len(runner.validate_predictions(directory, reg, "base", directory, ids)[0]), 48)
            p.write_bytes(p.read_bytes().replace(b'TEST', b'EDIT'))
            with self.assertRaises(ValueError):
                runner.validate_predictions(directory, reg, "base", directory, ids)

    def test_cli_has_no_paid_stage(self):
        result = subprocess.run([sys.executable, "-B", str(ROOT / "run.py"), "train"], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid choice", result.stderr)

    def test_preflight_is_honest(self):
        r = runner.preflight()
        self.assertFalse(r["gpu_tested"])
        self.assertEqual(r["model_responses"], 240)
        self.assertTrue(r["blockers"])

    def test_extra_prediction_files_block(self):
        with tempfile.TemporaryDirectory(dir=".") as tmp:
            directory = Path(tmp)
            for condition in f.CONDITIONS:
                for suffix in (".jsonl", ".binding.json", ".manifest.json"):
                    (directory / (condition + suffix)).write_bytes(b"test")
            self.assertEqual(len(runner.prediction_inventory(directory)), 15)
            (directory / "unregistered-retry.jsonl").write_bytes(b"test")
            with self.assertRaises(ValueError):
                runner.prediction_inventory(directory)

    def test_audit_missing_run_never_publishes(self):
        with tempfile.TemporaryDirectory(dir=".") as tmp:
            output = Path(tmp) / "audit"
            result = subprocess.run([sys.executable, "-B", str(ROOT / "run.py"), "audit-program005",
                "--workspace", str(Path(tmp) / "missing"), "--parent-search", str(Path(tmp) / "parent"),
                "--output-dir", str(output)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()