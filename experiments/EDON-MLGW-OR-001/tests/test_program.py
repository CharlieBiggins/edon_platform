#!/usr/bin/env python3
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mlgw_program import (
    append_record,
    compare_episodes,
    customer_outage_hours,
    read_jsonl,
    restoration_time,
    seal_record,
    validate_ledger,
    visible_records,
)
from run_synthetic_rehearsal import synthetic_world
from simulator import simulate


def record(record_id: str, available_at: str, evidence_class: str = "OBSERVED") -> dict:
    return {
        "record_id": record_id,
        "event_id": "event",
        "record_type": "TEST",
        "evidence_class": evidence_class,
        "event_time": "2026-08-24T00:00:00-05:00",
        "available_at": available_at,
        "source_id": "source",
        "payload": {"value": record_id},
        "derivation": None,
        "confidence": 1.0,
        "authoritative": False,
        "training_eligible": False,
        "supersedes": None,
    }


class ProgramTests(unittest.TestCase):
    def test_hash_chain_and_append(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.jsonl"
            first = append_record(path, record("a", "2026-08-24T01:00:00-05:00"))
            second = append_record(path, record("b", "2026-08-24T02:00:00-05:00"))
            rows = read_jsonl(path)
            self.assertEqual(second["previous_record_hash"], first["record_hash"])
            self.assertTrue(validate_ledger(rows)["valid"])

    def test_time_cutoff_blocks_future_information(self):
        first = seal_record(record("a", "2026-08-24T01:00:00-05:00"), None)
        second = seal_record(record("b", "2026-08-24T03:00:00-05:00"), first["record_hash"])
        visible = visible_records([first, second], "2026-08-24T02:00:00-05:00")
        self.assertEqual([row["record_id"] for row in visible], ["a"])

    def test_estimate_cannot_be_authoritative(self):
        value = record("estimate", "2026-08-24T01:00:00-05:00", "ESTIMATED")
        value["authoritative"] = True
        with self.assertRaises(ValueError):
            seal_record(value, None)

    def test_outage_hour_and_restoration_metrics(self):
        curve = [
            {"minute": 0, "customers_out": 100},
            {"minute": 60, "customers_out": 50},
            {"minute": 120, "customers_out": 0},
        ]
        self.assertAlmostEqual(customer_outage_hours(curve), 100.0)
        self.assertAlmostEqual(restoration_time(curve, 0.5), 1.0)

    def test_unmatched_resources_rejected(self):
        baseline = simulate(synthetic_world(), "actual_mlgw_replay")
        candidate = simulate(synthetic_world(), "critical_biggest_return")
        candidate["resource_fingerprint"] = "sha256:" + "0" * 64
        with self.assertRaises(ValueError):
            compare_episodes(baseline, candidate)

    def test_synthetic_rehearsal_is_safe_and_matched(self):
        baseline = simulate(synthetic_world(), "actual_mlgw_replay")
        candidate = simulate(synthetic_world(), "critical_biggest_return")
        comparison = compare_episodes(baseline, candidate)
        self.assertTrue(comparison["valid_matched_resources"])
        self.assertTrue(comparison["candidate_safety_gate_passed"])
        self.assertGreater(comparison["customer_outage_hours_reduction"], 0)


if __name__ == "__main__":
    unittest.main()