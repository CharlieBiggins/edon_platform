#!/usr/bin/env python3
from __future__ import annotations

import importlib
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dev018_common import BASE, CONFIG, read_json, read_jsonl  # noqa: E402
from prepare_data import prepare  # noqa: E402
from scoring import score_rows  # noqa: E402
from verifier import verify_predictions  # noqa: E402


def executor_prediction(row):
    sys.path.insert(0, str(BASE))
    try:
        rules = importlib.import_module("rules_baseline")
        compiler = importlib.import_module("canonicalize")
    finally:
        sys.path.pop(0)
    parsed = rules.predict_input(row["compiler_input"])
    compiled = compiler.compile_prediction(row["task_type"], row["compiler_input"], parsed)
    return {
        "case_id": row["case_id"],
        "task_type": row["task_type"],
        "raw_output": "{}",
        "parsed": parsed,
        "raw_schema_valid": True,
        "compiled": compiled,
        "ended_with_eos": True,
        "hit_generation_limit": False,
        "confidence": 1.0,
    }


class Dev018Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        prepare()
        cls.expected = read_jsonl(ROOT / "prepared" / "development-selection-64.jsonl")
        cls.verifier_inputs = read_jsonl(ROOT / "prepared" / "development-verifier-inputs-64.jsonl")

    def test_verifier_inputs_are_answer_key_free(self):
        self.assertTrue(all(set(row) == {"case_id", "task_type", "compiler_input"} for row in self.verifier_inputs))
        source = (ROOT / "verifier.py").read_text(encoding="utf-8")
        self.assertNotIn('["completion"]', source)

    def test_exact_executor_outputs_are_accepted(self):
        model = [executor_prediction(row) for row in self.verifier_inputs[:4]]
        verified, audits = verify_predictions(self.verifier_inputs[:4], model)
        self.assertTrue(all(row["action"] == "ACCEPT_MODEL" for row in audits))
        self.assertEqual([row["compiled"] for row in verified], [row["compiled"] for row in model])

    def test_unsafe_allow_is_overridden(self):
        candidate = None
        prediction = None
        for row in self.verifier_inputs:
            current = executor_prediction(row)
            if row["task_type"] in {"CERTIFICATE", "TRANSITION"} and current["compiled"].get("decision") != "ALLOW":
                candidate = row
                prediction = current
                break
        self.assertIsNotNone(candidate)
        prediction["compiled"] = dict(prediction["compiled"])
        prediction["compiled"]["decision"] = "ALLOW"
        verified, audits = verify_predictions([candidate], [prediction])
        self.assertEqual(audits[0]["action"], "OVERRIDE_WITH_EXECUTOR")
        self.assertTrue(audits[0]["safety_override"])
        self.assertNotEqual(verified[0]["compiled"]["decision"], "ALLOW")

    def test_executor_bound_hybrid_passes_frozen_gate(self):
        model = [executor_prediction(row) for row in self.verifier_inputs]
        verified, audits = verify_predictions(self.verifier_inputs, model)
        metrics = score_rows(self.expected, verified, read_json(CONFIG), "dev018_test_hybrid")
        self.assertTrue(metrics["full_regression_gate"]["passed"])
        self.assertTrue(all(row["answer_key_accessed"] is False for row in audits))


if __name__ == "__main__":
    unittest.main()