import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from edon.api.server import PlatformService
from edon.cerebrum import (
    C1OperationsAdapter,
    CerebrumSystem,
    CerebrumSystemError,
    DeterministicShadowProvider,
    InstitutionalStateEngine,
    StateEngineError,
    configured_operations_provider,
)
from edon.common.hashing import sha256_json
from edon.provenance import CausalProvenanceGraph, ProvenanceGraphError


ZERO_SHA = "sha256:" + "0" * 64
ONE_SHA = "sha256:" + "1" * 64


def assertion(
    assertion_id,
    state_class,
    value,
    *,
    occurred_at="2026-08-30T00:00:00+00:00",
    recorded_at="2026-08-30T00:01:00+00:00",
    available_at="2026-08-30T00:02:00+00:00",
    **extra,
):
    return {
        "assertion_id": assertion_id,
        "tenant_id": "tenant-a",
        "world_id": "world-a",
        "state_class": state_class,
        "state_path": ["resources", "beds", "available"],
        "value": value,
        "occurred_at": occurred_at,
        "recorded_at": recorded_at,
        "available_to_controller_at": available_at,
        "source_ref": f"source:{assertion_id}",
        "confidence": 0.9,
        "provenance": {"fixture": True},
        "binding_authority": False,
        **extra,
    }


class CerebrumSystemTests(unittest.TestCase):
    def test_state_classes_remain_separate_and_future_data_is_excluded(self):
        engine = InstitutionalStateEngine("tenant-a", "world-a")
        engine.ingest(assertion("reported", "REPORTED", 0))
        engine.ingest(assertion(
            "inferred",
            "INFERRED",
            1,
            available_at="2026-08-30T00:03:00+00:00",
            model_lineage="c1:fixture",
        ))
        engine.ingest(assertion(
            "committed",
            "COMMITTED",
            0,
            available_at="2026-08-30T00:04:00+00:00",
            authorization_ref_sha256=ZERO_SHA,
            world_version=4,
            committed_state_sha256=ONE_SHA,
        ))

        early = engine.project("2026-08-30T00:03:30+00:00")
        self.assertEqual(early["views"]["REPORTED"]["/resources/beds/available"]["value"], 0)
        self.assertEqual(early["views"]["INFERRED"]["/resources/beds/available"]["value"], 1)
        self.assertEqual(early["views"]["COMMITTED"], {})
        self.assertEqual(early["future_assertions_excluded"], 1)

        complete = engine.project("2026-08-30T00:05:00+00:00")
        self.assertEqual(complete["views"]["COMMITTED"]["/resources/beds/available"]["value"], 0)
        self.assertTrue(complete["separated_state_classes"])
        self.assertFalse(complete["binding_authority"])

    def test_state_engine_requires_lineage_authorization_and_monotonic_times(self):
        engine = InstitutionalStateEngine("tenant-a", "world-a")
        with self.assertRaisesRegex(StateEngineError, "model_lineage"):
            engine.ingest(assertion("bad-inference", "INFERRED", 1))
        with self.assertRaisesRegex(StateEngineError, "authorization_ref_sha256"):
            engine.ingest(assertion("bad-commit", "COMMITTED", 1))
        with self.assertRaisesRegex(StateEngineError, "recorded_at cannot precede"):
            engine.ingest(assertion(
                "backdated",
                "OBSERVED",
                1,
                occurred_at="2026-08-30T00:02:00+00:00",
                recorded_at="2026-08-30T00:01:00+00:00",
            ))

    def test_state_idempotency_and_same_time_conflicts_are_explicit(self):
        engine = InstitutionalStateEngine("tenant-a", "world-a")
        first = engine.ingest(assertion("report-a", "REPORTED", 0))
        self.assertEqual(first, engine.ingest(assertion("report-a", "REPORTED", 0)))
        engine.ingest(assertion("report-b", "REPORTED", 1))
        projected = engine.project("2026-08-30T00:03:00+00:00")
        self.assertEqual(projected["conflicts"][0]["assertion_ids"], ["report-a", "report-b"])
        with self.assertRaisesRegex(StateEngineError, "different content"):
            engine.ingest(assertion("report-a", "REPORTED", 2))

    def test_provenance_is_content_bound_traceable_and_acyclic(self):
        graph = CausalProvenanceGraph("tenant-a", "world-a")
        source = graph.record_node(
            "source:a",
            "SOURCE",
            sha256_json({"source": "a"}),
            occurred_at="2026-08-30T00:00:00+00:00",
            available_to_controller_at="2026-08-30T00:01:00+00:00",
        )
        inference = graph.record_node(
            "c1:a",
            "C1_INFERENCE",
            sha256_json({"proposal": "a"}),
            occurred_at="2026-08-30T00:02:00+00:00",
            available_to_controller_at="2026-08-30T00:02:00+00:00",
        )
        edge = graph.record_edge(
            "edge:a",
            source["node_id"],
            inference["node_id"],
            "INFORMED",
            evidence_status="DECLARED",
            evidence_refs=[source["payload_sha256"]],
            recorded_at="2026-08-30T00:02:00+00:00",
        )
        self.assertEqual(
            graph.trace_paths("source:a", "c1:a"), [["source:a", "c1:a"]]
        )
        self.assertEqual(edge, graph.record_edge(
            "edge:a",
            "source:a",
            "c1:a",
            "INFORMED",
            evidence_status="DECLARED",
            evidence_refs=[source["payload_sha256"]],
            recorded_at="2026-08-30T00:02:00+00:00",
        ))
        with self.assertRaisesRegex(ProvenanceGraphError, "cycle"):
            graph.record_edge(
                "edge:cycle",
                "c1:a",
                "source:a",
                "DERIVED_FROM",
                evidence_status="DECLARED",
                evidence_refs=[inference["payload_sha256"]],
                recorded_at="2026-08-30T00:03:00+00:00",
            )

    def test_cerebrum_cycle_uses_c1_but_cannot_request_or_execute_authority(self):
        adapter = C1OperationsAdapter(
            DeterministicShadowProvider(), model_lineage="c1:deterministic-fixture"
        )
        system = CerebrumSystem("tenant-a", "world-a", adapter)
        system.ingest_state_assertion(assertion("observed", "OBSERVED", 2))
        cycle = system.run_c1_cycle(
            "cycle-a",
            decision_time="2026-08-30T00:03:00+00:00",
            task_context={
                "assignment_proposals": [{
                    "plan_id": "plan-a",
                    "step_id": "step-a",
                    "recommended_agent_id": "agent-a",
                    "dispatchable": True,
                }]
            },
        )
        self.assertEqual(cycle["c1"]["architectural_name"], "C1")
        self.assertEqual(cycle["proposal"]["proposal_type"], "DISPATCH_STEP")
        self.assertFalse(cycle["kernel_authorization_requested"])
        self.assertFalse(cycle["executed"])
        self.assertFalse(cycle["binding_authority"])
        self.assertGreaterEqual(len(system.provenance.snapshot()["nodes"]), 3)

    def test_cerebrum_cycle_rejects_authority_bearing_context(self):
        system = CerebrumSystem(
            "tenant-a",
            "world-a",
            C1OperationsAdapter(
                DeterministicShadowProvider(), model_lineage="c1:fixture"
            ),
        )
        with self.assertRaisesRegex(CerebrumSystemError, "cannot carry execution authority"):
            system.run_c1_cycle(
                "cycle-unsafe",
                decision_time="2026-08-30T00:03:00+00:00",
                task_context={"nested": {"kernel_token": "forged"}},
            )

    def test_c1_environment_names_and_historical_aliases_resolve_identically(self):
        provider, lineage = configured_operations_provider({
            "EDON_C1_PROVIDER": "qwen",
            "EDON_C1_MODEL_LINEAGE": "c1:new-name",
            "EDON_C1_LOAD_IN_4BIT": "0",
        })
        historical_provider, historical_lineage = configured_operations_provider({
            "EDON_CEREBRUM_PROVIDER": "qwen",
            "EDON_CEREBRUM_MODEL_LINEAGE": "c1:historical-name",
            "EDON_CEREBRUM_LOAD_IN_4BIT": "0",
        })
        self.assertEqual(type(provider).__name__, "QwenOperationsProvider")
        self.assertEqual(type(historical_provider).__name__, "QwenOperationsProvider")
        self.assertEqual(lineage, "c1:new-name")
        self.assertEqual(historical_lineage, "c1:historical-name")

    def test_api_reports_explicit_c1_and_preserves_historical_status_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            service = PlatformService(
                directory,
                c1_provider=DeterministicShadowProvider(),
                c1_model_lineage="c1:api-fixture",
            )
            status = service.status()["cerebrum"]
            self.assertEqual(status["system_role"], "NON_AUTHORITATIVE_INSTITUTIONAL_INTELLIGENCE_SYSTEM")
            self.assertEqual(status["c1"]["model_lineage"], "c1:api-fixture")
            self.assertEqual(status["model_lineage"], status["c1"]["model_lineage"])
            self.assertTrue(status["historical_status_fields_preserved"])
            self.assertFalse(status["binding_authority"])

    def test_public_contract_and_migration_documents_are_present(self):
        paths = [
            "schemas/cerebrum/state-assertion.schema.json",
            "schemas/cerebrum/state-projection.schema.json",
            "schemas/cerebrum/system-cycle.schema.json",
            "schemas/cerebrum/c1-model-manifest.schema.json",
            "schemas/provenance/causal-graph.schema.json",
            "governance/architecture/cerebrum-c1-migration.json",
            "product/cerebrum-system/manifest.json",
        ]
        for relative in paths:
            with self.subTest(path=relative):
                payload = json.loads((ROOT / relative).read_text(encoding="utf-8"))
                self.assertFalse(payload.get("binding_authority", False))


if __name__ == "__main__":
    unittest.main()