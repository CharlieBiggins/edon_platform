"""CPU-only adversarial tests of labels, gating, recovery and execution boundaries."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import core
import data
import evaluate
import gpu_worker


class DataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.deps = core.dependencies()
        data.EXCLUDED.clear()
        _, templates = data.ordinary("unit", 91000, 1, 26091391, cls.deps)
        cls.template = templates[0]

    def pair(self, index):
        return data.boundary_pair(self.template, 92000, index, "unit", 26091392, self.deps)

    def test_all_six_rules_executable_balanced_and_deterministic(self):
        for index in range(6):
            with self.subTest(rule=data.RULES[index]):
                pair = self.pair(index)
                self.assertEqual(pair, self.pair(index))
                self.assertEqual(sum(r["compiler_input"]["oracle_certificate"]["decision"] == "ALLOW" for r in pair), 1)
                self.assertEqual(pair[0]["counterfactual_pair_id"], pair[1]["counterfactual_pair_id"])
                for r in pair:
                    data.qualify_row(r, self.deps)

    def test_future_events_deferred(self):
        for index in (0, 1, 4):
            a, b = self.pair(index)
            # Original index is before serialization shuffle; use the sole event at q+1.
            source = b["compiler_input"]["program_source"]
            q = source["initial_state"]["request"]["query_time"]
            event = next(e for e in source["submitted_events"] if e["time"] == q+1)
            records = self.deps[1].build_trace(source)["records"]
            record = next(r for r in records if r["event_id"] == event["event_id"])
            self.assertEqual(record["disposition"], "DEFER")
            self.assertEqual(record["changes"], [])
            self.assertNotEqual(a["compiler_input"]["oracle_certificate"]["decision"], b["compiler_input"]["oracle_certificate"]["decision"])

    def test_receipt_predicate_even_with_true_status(self):
        a, b = self.pair(5)
        src = b["compiler_input"]["program_source"]
        self.assertEqual(src["initial_state"]["evidence"]["status"], "TRUE")
        d = self.deps[1].build_trace(src)["derivation"]
        self.assertEqual(d["first_failure"], "EVIDENCE_UNAVAILABLE")
        self.assertEqual(d["decision"], "ABSTAIN")

    def test_priority_pair_flips_authority(self):
        a, b = self.pair(3)
        self.assertEqual(a["compiler_input"]["oracle_certificate"]["decision"], "DENY")
        self.assertEqual(b["compiler_input"]["oracle_certificate"]["decision"], "ALLOW")

    def test_policy_target_is_not_resource_update(self):
        _, row = self.pair(2)
        records = self.deps[1].build_trace(row["compiler_input"]["program_source"])["records"]
        self.assertTrue(any(["policy.allows", True, False] in r["changes"] for r in records))

    def test_source_order_invariant(self):
        source = self.pair(3)[0]["compiler_input"]["program_source"]
        reversed_source = copy.deepcopy(source)
        reversed_source["submitted_events"].reverse()
        self.assertEqual(self.deps[1].build_trace(source), self.deps[1].build_trace(reversed_source))

    def test_dangling_actor_rejected(self):
        row = self.pair(0)[0]
        row["compiler_input"]["program_source"]["submitted_events"][0]["actor_id"] = "not-an-actor"
        with self.assertRaises(ValueError): data.qualify_row(row, self.deps)

    def test_wrong_target_rejected(self):
        row = self.pair(2)[0]
        row["trace_completion"] += "tampered"
        with self.assertRaises(ValueError): data.qualify_row(row, self.deps)

    def test_confirmation_not_generatable(self):
        with self.assertRaises(ValueError): data.generate("confirmation", self.deps)

    def test_pair_joint_requires_both_trace_and_native(self):
        rowset = self.pair(0)
        predictions = [{"case_id": r["case_id"], "raw_output": self.deps[1].completion_for(r, "trace"),
                        "ended_with_eos": True, "hit_generation_limit": False} for r in rowset]
        # summarize requires a nonempty ordinary stratum as well.
        broad = copy.deepcopy(rowset)
        for r in broad:
            r["case_id"] += "-ordinary"
            r["stratum"] = "ordinary"
            r["contrast_rule"] = None
        predictions += [{"case_id": r["case_id"], "raw_output": self.deps[1].completion_for(r, "trace"),
                         "ended_with_eos": True, "hit_generation_limit": False} for r in broad]
        score = evaluate.summarize(rowset+broad, predictions)
        self.assertEqual(score["targeted_pair_joint"][data.RULES[0]]["correct"], 1)
        predictions[0]["raw_output"] = "invalid output"
        score = evaluate.summarize(rowset+broad, predictions)
        self.assertEqual(score["targeted_pair_joint"][data.RULES[0]]["correct"], 0)


def synthetic_scores():
    es = [{"case_id": str(i), "semantic_family": i//4, "stratum": "ordinary" if i < 48 else "boundary",
           "contrast_rule": None if i < 48 else data.RULES[(i-48)//8],
           "counterfactual_pair_id": str(i//2), "oracle_decision": "ALLOW" if i%2 else "DENY",
           "program_exact": True} for i in range(96)]
    good = {"evaluations": es, "gate_passed": True, "program_exact_rate": 1.0,
            "trace_exact_rate": 1.0, "event_order_exact_rate": 1.0, "decision_accuracy": 1.0,
            "executed_state_exact_rate": 1.0, "unsafe_authorizations": 0,
            "verified_unsafe_authorizations": 0, "raw_claim_unsafe_authorizations": 0,
            "unexamined_raw_claims": 0, "ordinary_metrics": {"program_exact": 1.0},
            "all_metrics": {"allow_error_rate": 0.0, "unnecessary_abstention_rate": 0.0},
            "targeted_pair_joint": {r: {"pairs": 4, "correct": 4, "rate": 1.0} for r in data.RULES}}
    control = copy.deepcopy(good)
    control["program_exact_rate"] = 0.5
    for e in control["evaluations"]: e["program_exact"] = False
    return control, good, copy.deepcopy(control)


class GateTests(unittest.TestCase):
    def test_good_screen_never_authorizes_confirmation(self):
        result = evaluate.compare(*synthetic_scores())
        self.assertTrue(result["screen_passed"])
        self.assertFalse(result["confirmation_authorized"])
        self.assertFalse(result["statistical_confirmation"])

    def test_each_safety_counter_fails_closed(self):
        for key in ("unsafe_authorizations", "verified_unsafe_authorizations", "raw_claim_unsafe_authorizations", "unexamined_raw_claims"):
            scores = synthetic_scores(); scores[1][key] = 1
            self.assertFalse(evaluate.compare(*scores)["screen_passed"], key)

    def test_missing_rule_fails(self):
        scores = synthetic_scores(); scores[1]["targeted_pair_joint"].pop(data.RULES[0])
        self.assertFalse(evaluate.compare(*scores)["screen_passed"])

    def test_pair_floor_fails(self):
        scores = synthetic_scores(); scores[1]["targeted_pair_joint"][data.RULES[0]]["rate"] = 0.5
        self.assertFalse(evaluate.compare(*scores)["screen_passed"])

    def test_partial_screen_rejected(self):
        scores = synthetic_scores(); scores[1]["evaluations"].pop()
        with self.assertRaises(ValueError): evaluate.compare(*scores)

    def test_duplicate_ids_rejected(self):
        scores = synthetic_scores(); scores[1]["evaluations"][1]["case_id"] = "0"
        with self.assertRaises(ValueError): evaluate.compare(*scores)

    def test_metadata_mismatch_rejected(self):
        scores = synthetic_scores(); scores[2]["evaluations"][0]["semantic_family"] = 1000
        with self.assertRaises(ValueError): evaluate.compare(*scores)

    def test_ordinary_retention_is_required(self):
        scores = synthetic_scores(); scores[1]["ordinary_metrics"]["program_exact"] = 47/48
        self.assertFalse(evaluate.compare(*scores)["screen_passed"])

    def test_unsafe_rejection_cannot_be_replaced_by_abstain_all(self):
        scores = synthetic_scores(); scores[1]["all_metrics"]["unnecessary_abstention_rate"] = 1.0
        self.assertFalse(evaluate.compare(*scores)["screen_passed"])


class BoundaryTests(unittest.TestCase):
    def test_strict_json(self):
        for value in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}'):
            with self.assertRaises(ValueError): core.parse(value)

    def test_prefix_preserved_and_bad_interior_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(os.path.relpath(directory)) / "prefix.jsonl"
            payload = b'{"case_id":"a"}\n{"case_id":'
            core.write_once(path, payload)
            records, good = gpu_worker.read_prefix(path, ["a", "b"])
            self.assertEqual(len(records), 1)
            self.assertEqual(good, b'{"case_id":"a"}\n')
            self.assertEqual(path.read_bytes(), payload)
            bad = path.parent / "bad.jsonl"
            core.write_once(bad, b'broken\n{"case_id":"a"}\n')
            with self.assertRaises(ValueError): gpu_worker.read_prefix(bad, ["a"])

    def test_unknown_prefix_id_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(os.path.relpath(directory)) / "bad.jsonl"
            core.write_once(path, b'{"case_id":"wrong"}\n')
            with self.assertRaises(ValueError): gpu_worker.read_prefix(path, ["a"])

    def test_write_once_never_overwrites(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(os.path.relpath(directory)) / "file"
            core.write_once(path, b"first")
            with self.assertRaises(ValueError): core.write_once(path, b"other")
            self.assertEqual(path.read_bytes(), b"first")

    def test_paid_and_confirmation_cli_guards(self):
        script = os.path.relpath(ROOT / "run.py")
        for args in (("development",), ("runtime",), ("confirmation", "--authorize-paid")):
            result = subprocess.run([sys.executable, "-B", script, *args], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("error:", result.stderr)


class RegistrationTests(unittest.TestCase):
    def check_fixture(self, mutation):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(os.path.relpath(directory))
            core.write_once(root/"prepared/data.jsonl", b"original\n")
            reg = {"protocol_id": "fixture", "parent_adapter_sha256": "parent", "sources": {},
                   "inherited_sources": {}, "confirmation_materialized": False,
                   "data": {"prepared/data.jsonl": core.file_hash(root/"prepared/data.jsonl")}}
            core.write_json(root/"registration.json", reg)
            with patch.object(core, "ROOT", root), patch.object(core, "own_sources", return_value={}), \
                 patch.object(core, "inherited_sources", return_value={}), \
                 patch.object(core, "cfg", return_value={"protocol_id": "fixture", "parent_adapter_sha256": "parent"}):
                core.verify()
                mutation(root)
                with self.assertRaises(ValueError): core.verify()

    def test_extra_data_rejected(self):
        self.check_fixture(lambda r: core.write_once(r/"prepared/extra.json", b"{}"))

    def test_confirmation_evidence_rejected(self):
        self.check_fixture(lambda r: core.write_once(r/"results/confirmation-access.json", b"{}"))

    def test_source_tamper_rejected(self):
        with patch.object(core, "read", return_value={"sources": {"bad.py": "bad"}, "inherited_sources": {}}), \
             patch.object(core, "own_sources", return_value={}), \
             patch.object(core, "inherited_sources", return_value={}):
            with self.assertRaises(ValueError): core.verify()


if __name__ == "__main__":
    unittest.main()