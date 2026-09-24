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
import dataset
import foundation as f
import scorer
import token_budget

spec = importlib.util.spec_from_file_location("matched_run", ROOT / "run.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def approved_study():
    value = f.read(ROOT / "study.template.json")
    value.update(program005_audit_sha256="sha256:" + "1" * 64,
                 program005_disposition_acknowledged=True,
                 comparison001_decision_rationale="Skip optional reuse screen; run central matched question.",
                 human_approval_to_register=True, claim_boundary_acknowledged=True)
    value["base_snapshot"].update(weights_tree_sha256="sha256:" + "2" * 64,
        tokenizer_tree_sha256="sha256:" + "3" * 64, license_review="Reviewed for bounded internal research")
    value["training_budget"].update(processed_nonpadding_tokens_per_arm=100000,
        maximum_realized_arm_difference_tokens=1000, maximum_gpu_hours_per_run=2,
        maximum_total_gpu_hours=4, gpu_hourly_price_usd=1,
        maximum_cost_usd_per_run=2, maximum_total_cost_usd=4)
    return value


def scenarios():
    values = []
    decisions = sorted(f.DECISIONS)
    for pair_index in range(192):
        pair = "pair-" + str(pair_index)
        for member in range(2):
            decision = decisions[(pair_index + member) % len(decisions)]
            source = {"initial_state": {"x": pair_index, "flag": bool(member)},
                      "submitted_events": [{"event_id": f"event-{pair_index}-{member}", "time": member,
                                             "priority": 1, "sequence": 1, "value": member}]}
            values.append({"case_id": f"case-{pair_index}-{member}",
                "counterfactual_pair_id": pair, "prompt": "PROMPT " + str(pair_index) + " " + str(member),
                "completion": "PROGRAM " + str(member), "trace_completion": "TRACE " + str(member),
                "compiler_input": {"program_source": source,
                    "oracle_state": {"x": pair_index, "flag": bool(member)},
                    "oracle_certificate": {"decision": decision, "semantic_state": "TRUE",
                                           "failed_conditions": []}}})
    return values


def input_and_scores(action_correct=22, ordinary_correct=19):
    inputs = []
    for pair in range(12):
        for member in range(2):
            inputs.append({"case_id": f"c-{pair}-{member}", "counterfactual_pair_id": f"p-{pair}"})
    def one(correct, ordinary_rate):
        evaluations = [{"case_id": row["case_id"], "program_exact": index < correct}
                       for index, row in enumerate(inputs)]
        return {"evaluations": evaluations, "parse_valid_rate": 1.0,
            "event_order_exact_rate": 1.0, "partition_exact_rate": 1.0,
            "executed_state_exact_rate": 1.0, "claim_state_exact_rate": 1.0,
            "decision_accuracy": 1.0, "program_exact_rate": correct / 24,
            "unsafe_authorizations": 0, "raw_claim_unsafe_authorizations": 0,
            "unexamined_raw_claims": 0, "generation_limit_hits": 0,
            "ordinary_metrics": {"program_exact_rate": ordinary_rate}}
    return inputs, {"ordinary": one(ordinary_correct, ordinary_correct / 24),
                    "actionnet": one(action_correct, action_correct / 24)}


class FakeTokenizer:
    eos_token_id = 0
    def __call__(self, text, add_special_tokens=False):
        return {"input_ids": list(range(max(1, len(text.split()))))}


class FrameworkTests(unittest.TestCase):
    def test_strict_json(self):
        for text in ('{"a":1,"a":2}', '{"x":NaN}', '{"x":Infinity}', '{"x":1e999}'):
            with self.assertRaises(ValueError):
                f.parse(text)

    def test_safe_paths(self):
        for value in ("../x", "C:x", "C:/x", "a\\b", "a//b", ""):
            with self.assertRaises(ValueError):
                f.safe_name(value)
        self.assertEqual(f.safe_name("a/b.json"), "a/b.json")

    def test_framework_config_and_preflight(self):
        config = runner.config()
        self.assertEqual(config["arms"], ["ordinary", "actionnet"])
        result = runner.preflight()
        self.assertEqual(result["screen_responses"], 48)
        self.assertFalse(result["training_started"])
        self.assertTrue(result["blockers"])

    def test_unresolved_study_cannot_register_or_execute(self):
        config = runner.config()
        draft = f.read(ROOT / "study.template.json")
        f.validate_study(draft, config, "draft")
        with self.assertRaises(ValueError):
            f.validate_study(draft, config, "registration")
        approved = approved_study()
        f.validate_study(approved, config, "registration")
        with self.assertRaises(ValueError):
            f.validate_study(approved, config, "paid")
        approved["execution"].update(paid_execution_approved=True,
            approval_identity="TEST OPERATOR", approval_date="2026-09-19")
        f.validate_study(approved, config, "paid")

    def test_unfair_interface_rejected(self):
        value = approved_study()
        value["execution"]["retries"] = 1
        with self.assertRaises(ValueError):
            f.validate_study(value, runner.config(), "registration")

    def test_execution_approval_is_separate_and_registration_bound(self):
        study = approved_study()
        with tempfile.TemporaryDirectory(dir=".") as temp:
            run = Path(temp)
            f.write_json(run / "study.json", study)
            f.write_json(run / "registration.json", {"protocol_id": f.ID})
            budget = study["training_budget"]
            approval = {"schema_version": 1, "protocol_id": f.ID,
                "registration_sha256": f.file_hash(run / "registration.json"),
                "study_sha256": f.file_hash(run / "study.json"),
                "maximum_gpu_hours_per_run": budget["maximum_gpu_hours_per_run"],
                "maximum_total_gpu_hours": budget["maximum_total_gpu_hours"],
                "gpu_hourly_price_usd": budget["gpu_hourly_price_usd"],
                "maximum_cost_usd_per_run": budget["maximum_cost_usd_per_run"],
                "maximum_total_cost_usd": budget["maximum_total_cost_usd"],
                "approval_identity": "TEST OPERATOR", "approval_date": "2026-09-19",
                "paid_execution_approved": True,
                "scope": "MATCHED001_RUNTIME_TRAIN_BOTH_ARMS_AND_OPTIONAL_24_CASE_SCREEN_FOR_DECLARED_SEED_ONLY"}
            f.validate_execution_approval(approval, run, study)
            approval["maximum_cost_usd_per_run"] += 1
            with self.assertRaises(ValueError):
                f.validate_execution_approval(approval, run, study)

    def test_actual_billing_receipt_is_bound_and_capped(self):
        study = approved_study()
        with tempfile.TemporaryDirectory(dir=".") as temp:
            run = Path(temp)
            f.write_json(run / "registration.json", {"protocol_id": f.ID})
            receipt = {"schema_version": 1, "protocol_id": f.ID,
                "registration_sha256": f.file_hash(run / "registration.json"),
                "provider": "Modal", "account_profile": "test-profile",
                "included_stages": ["runtime", "train-ordinary", "train-actionnet",
                                    "predict-ordinary", "predict-actionnet"],
                "actual_gpu_hours": 1.5, "actual_cost_usd": 1.5,
                "provider_evidence_sha256": "sha256:" + "4" * 64,
                "reported_by": "TEST OPERATOR", "reported_date": "2026-09-19",
                "provider_billing_attested": True}
            f.validate_billing_receipt(receipt, run, study)
            receipt["actual_cost_usd"] = 5
            with self.assertRaises(ValueError):
                f.validate_billing_receipt(receipt, run, study)

    def test_serializers_share_exact_native_examples_and_scenarios(self):
        ordinary, actionnet = dataset.serialize_training(scenarios())
        self.assertEqual(len(ordinary), 384)
        self.assertEqual(len(actionnet), 960)
        natives = [value for value in actionnet if value["target_kind"] == "native_program"]
        self.assertEqual(ordinary, natives)
        self.assertEqual({case for value in ordinary for case in value["underlying_case_ids"]},
                         {case for value in actionnet for case in value["underlying_case_ids"]})
        broken = copy.deepcopy(actionnet)
        broken[0]["target"] = "CHANGED"
        with self.assertRaises(ValueError):
            dataset.validate_serialization(scenarios(), ordinary, broken)

    def test_token_plans_use_complete_groups_and_match_tolerance(self):
        examples = {"ordinary": [], "actionnet": []}
        for group in range(4):
            for index in range(2):
                examples["ordinary"].append({"example_id": f"o-{group}-{index}", "group_id": f"g-{group}",
                    "target_kind": "native_program", "prompt": "one two", "target": "three four"})
            for index in range(5):
                examples["actionnet"].append({"example_id": f"a-{group}-{index}", "group_id": f"g-{group}",
                    "target_kind": "native_program" if index < 2 else "execution_trace",
                    "prompt": "one", "target": "two"})
        study = approved_study()
        study["training_budget"].update(processed_nonpadding_tokens_per_arm=120,
                                         maximum_realized_arm_difference_tokens=30)
        plans, audit = token_budget.make_plans(examples, FakeTokenizer(), runner.config(), study)
        self.assertTrue(audit["token_budget_matched"])
        for arm in f.ARMS:
            counts = {}
            for row in plans[arm]:
                counts[row["group_id"]] = counts.get(row["group_id"], 0) + 1
            unit = 2 if arm == "ordinary" else 5
            self.assertTrue(all(value % unit == 0 for value in counts.values()))

    def test_budget_too_small_for_first_traversal_rejected(self):
        examples = [{"example_id": "a", "group_id": "g", "target_kind": "native_program",
                     "prompt": "one two", "target": "three four"}]
        counts = {"a": {"nonpadding_tokens": 20, "supervised_tokens": 10}}
        with self.assertRaises(ValueError):
            token_budget.select_complete_groups(examples, counts, 19)

    def test_supported_inconclusive_and_not_supported(self):
        study = approved_study(); study["screen"]["paired_cluster_bootstrap_repetitions"] = 1000
        inputs, scores = input_and_scores(action_correct=22, ordinary_correct=19)
        self.assertEqual(scorer.compare(inputs, scores, study)["status"], "SUPPORTED")
        inputs, scores = input_and_scores(action_correct=20, ordinary_correct=19)
        self.assertEqual(scorer.compare(inputs, scores, study)["status"], "INCONCLUSIVE")
        inputs, scores = input_and_scores(action_correct=22, ordinary_correct=19)
        scores["actionnet"]["raw_claim_unsafe_authorizations"] = 1
        self.assertEqual(scorer.compare(inputs, scores, study)["status"], "NOT_SUPPORTED")
        inputs, scores = input_and_scores(action_correct=17, ordinary_correct=20)
        self.assertEqual(scorer.compare(inputs, scores, study)["status"], "NOT_SUPPORTED")

    def test_snapshot_hashes_require_real_model_and_tokenizer_files(self):
        with tempfile.TemporaryDirectory(dir=".") as temp:
            root = Path(temp)
            (root / "model.safetensors").write_bytes(b"weights")
            (root / "config.json").write_text("{}", encoding="utf-8")
            (root / "tokenizer.json").write_text("{}", encoding="utf-8")
            result = f.snapshot_hashes(root)
            self.assertRegex(result["weights_tree_sha256"], r"^sha256:[0-9a-f]{64}$")
            (root / "model.safetensors").write_bytes(b"changed")
            self.assertNotEqual(result["weights_tree_sha256"], f.snapshot_hashes(root)["weights_tree_sha256"])

    def test_paid_cli_needs_literal_authorization_before_any_gpu_import(self):
        result = subprocess.run([sys.executable, "-B", str(ROOT / "run.py"), "train",
            "--run-dir", "missing", "--base-snapshot", "missing", "--arm", "ordinary"],
            capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--authorize-paid", result.stderr)

    def test_prepare_failure_does_not_publish_destination(self):
        with tempfile.TemporaryDirectory(dir=".") as temp:
            output = Path(temp) / "run"
            result = subprocess.run([sys.executable, "-B", str(ROOT / "run.py"), "prepare",
                "--study", str(ROOT / "study.template.json"), "--program005-audit", "missing.json",
                "--output-dir", str(output)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output.exists())

    def test_no_overwrite_or_nested_output(self):
        with tempfile.TemporaryDirectory(dir=".") as temp:
            with self.assertRaises(ValueError):
                f.fresh_directory(Path(temp))
            with self.assertRaises(ValueError):
                f.protect_output(Path(temp) / "child", Path(temp))


if __name__ == "__main__":
    unittest.main()