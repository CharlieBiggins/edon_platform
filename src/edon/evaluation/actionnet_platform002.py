"""ACTIONNET-PLATFORM-002 active institutional-experience evaluation."""

from __future__ import annotations

import tempfile
from pathlib import Path

from edon.actionnet.product import (
    ActionNetPlatformStore,
    CompositionExecutionError,
    CounterfactualEngine,
    GovernedAbstractionValidator,
    GovernedIntakeError,
    HumanBehaviorEngine,
    InstitutionalIRError,
    InstitutionalIRValidator,
    MechanismCompositionEngine,
)


def _mechanism_spec(transition: dict, *requirements: str) -> dict:
    return {
        "preconditions": ["registered canonical Institutional IR"],
        "state_transitions": [transition],
        "dependencies": [],
        "interventions": ["registered counterfactual branch"],
        "failure_modes": ["unmitigated institutional consequence"],
        "expected_outcomes": ["typed state transition"],
        "ir_requirements": list(requirements),
    }


def _ir() -> dict:
    return {
        "institution_id": "institution-002",
        "version": "1.0.0",
        "institution_type": "LOGISTICS",
        "objects": [
            {"object_id": "institution", "object_type": "INSTITUTION", "attributes": {"status": "OPERATING"}},
            {
                "object_id": "operator", "object_type": "ACTOR", "attributes": {"shift": "NIGHT"},
                "behavior_model": {
                    "objectives": ["protect-service"], "incentives": ["on-time-performance"],
                    "trust": {"institution": 0.7}, "fatigue": 0.4, "risk_tolerance": 0.3,
                    "information_access": ["delay-evidence"], "cooperation_probability": 0.82,
                    "strategic_behavior": "COOPERATIVE", "bounded_rationality": 0.25,
                },
            },
            {"object_id": "capacity", "object_type": "RESOURCE", "attributes": {"available": 100.0}},
            {"object_id": "authority", "object_type": "AUTHORITY", "attributes": {"active": True}},
            {"object_id": "policy", "object_type": "POLICY", "attributes": {"mode": "NORMAL"}},
            {"object_id": "workflow", "object_type": "WORKFLOW", "attributes": {"queue": 12}},
            {"object_id": "risk", "object_type": "RISK", "attributes": {"score": 0.1}},
            {
                "object_id": "delay-evidence", "object_type": "EVIDENCE",
                "attributes": {"signal": "DELAY_POSSIBLE"},
                "epistemic_state": {
                    "status": "UNKNOWN", "confidence": 0.0, "critical": True,
                    "sources": ["local-telemetry"],
                },
            },
            {"object_id": "deadline", "object_type": "TEMPORAL_CONSTRAINT", "attributes": {"seconds": 3600}},
            {"object_id": "conflict", "object_type": "CONFLICT", "attributes": {"active": False}},
            {"object_id": "outcome", "object_type": "OUTCOME", "attributes": {"service_level": 1.0}},
        ],
        "horizons": [
            {"horizon_id": "ten-minutes", "duration_seconds": 600, "label": "10 minutes"},
            {"horizon_id": "one-day", "duration_seconds": 86400, "label": "24 hours"},
            {"horizon_id": "thirty-days", "duration_seconds": 2592000, "label": "30 days"},
        ],
        "truth_layers": {
            "normative": ["policy"], "operational": ["capacity", "workflow"],
            "behavioral": ["operator"],
        },
    }


def run_actionnet_platform002() -> dict:
    """Exercise Platform 002 without claiming real-institution or learning validity."""
    with tempfile.TemporaryDirectory() as directory:
        store = ActionNetPlatformStore(Path(directory) / "actionnet-platform.sqlite3")
        validator = InstitutionalIRValidator()
        ir_record = store.register_institutional_ir(
            "tenant-002", "institution-002", "1.0.0", _ir(),
            source_lineage=["internal-platform-002-fixture"], created_by="ir-author",
            created_at="2026-08-23T09:00:00+00:00",
        )
        ir = ir_record["institutional_ir"]
        actionability = validator.assess_actionability(ir)
        invalid_ir_blocked = False
        try:
            validator.normalize({
                "institution_id": "bad", "version": "1", "institution_type": "TEST",
                "objects": [{
                    "object_id": "actor", "object_type": "ACTOR", "attributes": {},
                    "references": [{"relation": "USES", "target_id": "missing"}],
                }],
            })
        except InstitutionalIRError:
            invalid_ir_blocked = True

        capacity = store.register_mechanism(
            "tenant-002", "capacity-degradation", "2.0.0", "Capacity degradation",
            "Registered operational capacity decreases after a typed disruption.",
            _mechanism_spec({
                "target_object_id": "capacity", "attribute": "available",
                "operation": "DECREMENT", "value": 20, "at_seconds": 300,
            }, "RESOURCE"), evidence_grade="SYNTHETIC_VERIFIED",
            source_lineage=["platform-002"], created_by="mechanism-author",
            created_at="2026-08-23T09:00:01+00:00",
        )
        authority = store.register_mechanism(
            "tenant-002", "authority-revocation", "2.0.0", "Authority revocation",
            "Registered authority becomes unavailable before mitigation is attempted.",
            _mechanism_spec({
                "target_object_id": "authority", "attribute": "active",
                "operation": "SET", "value": False, "at_seconds": 900,
            }, "AUTHORITY"), evidence_grade="SYNTHETIC_VERIFIED",
            source_lineage=["platform-002"], created_by="mechanism-author",
            created_at="2026-08-23T09:00:02+00:00",
        )
        deadline = store.register_mechanism(
            "tenant-002", "deadline-pressure", "2.0.0", "Deadline pressure",
            "Delayed institutional effects increase registered downstream risk.",
            _mechanism_spec({
                "target_object_id": "risk", "attribute": "score",
                "operation": "INCREMENT", "value": 0.2, "at_seconds": 86400,
            }, "RISK", "TEMPORAL_CONSTRAINT"), evidence_grade="SYNTHETIC_VERIFIED",
            source_lineage=["platform-002"], created_by="mechanism-author",
            created_at="2026-08-23T09:00:03+00:00",
        )
        edge_cause = store.register_composition_edge(
            "tenant-002", "edge-cause", "capacity-degradation", "2.0.0",
            "authority-revocation", "2.0.0", "CAUSES",
            conditions={"required_object_types": ["RESOURCE", "AUTHORITY"]},
            evidence_grade="SYNTHETIC_VERIFIED", provenance={"fixture": "002"},
            created_by="mechanism-author", created_at="2026-08-23T09:00:04+00:00",
        )
        edge_amplify = store.register_composition_edge(
            "tenant-002", "edge-amplify", "authority-revocation", "2.0.0",
            "deadline-pressure", "2.0.0", "AMPLIFIES",
            conditions={"magnitude_multiplier": 2.0, "minimum_horizon_seconds": 86400},
            evidence_grade="SYNTHETIC_VERIFIED", provenance={"fixture": "002"},
            created_by="mechanism-author", created_at="2026-08-23T09:00:05+00:00",
        )
        mechanisms = [
            store.mechanism("tenant-002", item["mechanism_id"], item["version"])
            for item in (capacity, authority, deadline)
        ]
        edges = [
            store.composition_edge("tenant-002", edge_cause["edge_id"]),
            store.composition_edge("tenant-002", edge_amplify["edge_id"]),
        ]
        engine = MechanismCompositionEngine()
        run = engine.compose("composition-002", ir, mechanisms, edges, seed=23)
        run_again = engine.compose("composition-002", ir, mechanisms, edges, seed=23)
        run_record = store.record_composition_run(
            "tenant-002", run, protected=False, created_by="world-lab",
            created_at="2026-08-23T09:00:06+00:00",
        )
        parent = store.record_experience(
            "tenant-002", "experience-composition-002", "SIMULATOR", "LOGISTICS",
            run["mechanism_refs"], run["trajectory"], run["causal_trace"],
            evidence_grade="SYNTHETIC_VERIFIED",
            provenance={"composition_run_sha256": run["run_sha256"]},
            created_by="world-lab", created_at="2026-08-23T09:00:07+00:00",
        )
        cycle_blocked = False
        try:
            engine.compose("bad-cycle", ir, mechanisms[:2], [
                {**edges[0], "edge_id": "cycle-a"},
                {
                    **edges[0], "edge_id": "cycle-b",
                    "source": edges[0]["target"], "target": edges[0]["source"],
                },
            ])
        except CompositionExecutionError:
            cycle_blocked = True

        behavior = HumanBehaviorEngine().generate(ir, seed=17)
        behavior_again = HumanBehaviorEngine().generate(ir, seed=17)
        behavior_record = store.record_behavior_scenario(
            "tenant-002", "behavior-002", "institution-002", "1.0.0", behavior,
            protected=False, created_by="world-lab",
            created_at="2026-08-23T09:00:08+00:00",
        )

        batch = CounterfactualEngine().generate(
            "counterfactual-002", parent["experience_id"], parent["trajectory"],
            [
                {
                    "branch_id": "restore-capacity", "type": "SET_ATTRIBUTE",
                    "target_object_id": "capacity", "attribute": "available",
                    "value": 95.0, "at_seconds": 600,
                },
                {
                    "branch_id": "delay-revocation", "type": "SHIFT_EVENT",
                    "event_id": "composition-002:001:000", "delta_seconds": 86400,
                },
            ],
        )
        children = []
        for branch in batch["branches"]:
            children.append(store.record_experience(
                "tenant-002", f"counterfactual-002-{branch['branch_id']}", "SIMULATOR",
                "LOGISTICS", parent["mechanism_refs"], branch["trajectory"],
                {"intervention": branch["intervention"], "verification": branch["verification"]},
                counterfactual_parent_id=parent["experience_id"],
                evidence_grade="SYNTHETIC_VERIFIED",
                provenance={"branch_sha256": branch["branch_sha256"]},
                created_by="counterfactual-engine",
                created_at="2026-08-23T09:00:09+00:00",
            ))
        batch_record = store.record_counterfactual_batch(
            "tenant-002", batch, [child["experience_id"] for child in children],
            protected=False, created_by="counterfactual-engine",
            created_at="2026-08-23T09:00:10+00:00",
        )

        abstraction_input = {
            "intake_id": "intake-002",
            "institution_ir_ref": {"institution_id": "institution-002", "version": "1.0.0"},
            "source_fingerprint": "sha256:locally-generated-fingerprint",
            "local_processor": {"processor_id": "edge-abstraction", "version": "1.0.0"},
            "rights_basis": "INTERNAL_AUTHORIZATION",
            "data_categories": ["capacity", "outcome"],
            "redaction_summary": {"direct_identifier_fields_removed": 4},
            "attestation": {
                "direct_identifiers_removed": True, "secrets_removed": True,
                "minimum_necessary": True, "raw_payload_retained_locally": True,
                "authorized_for_abstraction": True,
            },
            "mechanism_refs": [{"mechanism_id": "capacity-degradation", "version": "2.0.0"}],
            "trajectory": {"initial_state": {"capacity_band": "NORMAL"}, "outcome": {"capacity_band": "DEGRADED"}},
            "causal_trace": {"path": ["capacity degradation", "reduced service capacity"]},
            "provenance": {"local_site": "site-class-a", "source_bytes_exported": False},
        }
        abstraction = GovernedAbstractionValidator().normalize(abstraction_input)
        real_experience = store.record_experience(
            "tenant-002", "experience-real-abstraction-002", "REAL_GOVERNED_ABSTRACTION",
            "LOGISTICS", abstraction["mechanism_refs"], abstraction["trajectory"],
            abstraction["causal_trace"], evidence_grade="SOURCE_GROUNDED",
            provenance={"intake_id": abstraction["intake_id"], "raw_payload_stored": False},
            created_by="intake-operator", created_at="2026-08-23T09:00:11+00:00",
        )
        intake = store.record_governed_intake(
            "tenant-002", abstraction, real_experience["experience_id"],
            created_by="intake-operator", created_at="2026-08-23T09:00:12+00:00",
        )
        raw_rejected = False
        try:
            GovernedAbstractionValidator().normalize({
                **abstraction_input, "intake_id": "unsafe-intake", "patient_name": "prohibited"
            })
        except GovernedIntakeError:
            raw_rejected = True

        tuple_map = {item["object_type"]: item["tuple_component"] for item in ir["objects"]}
        one_day = next(
            row for row in run["trajectory"]["horizon_states"] if row["horizon_id"] == "one-day"
        )
        gates = {
            "canonical_ir_versioned_and_hash_bound": bool(
                ir_record["record_sha256"] and ir["ir_sha256"]
            ),
            "canonical_ir_preserves_dissertation_tuple": ir["canonical_tuple"] == "I=(X,E,R,A,P,W,T,C,Sigma)",
            "canonical_objects_map_into_tuple": (
                tuple_map["RESOURCE"] == "R" and tuple_map["AUTHORITY"] == "A"
                and tuple_map["POLICY"] == "P" and tuple_map["WORKFLOW"] == "W"
                and tuple_map["CONFLICT"] == "C" and tuple_map["OUTCOME"] == "SIGMA"
            ),
            "ir_references_are_closed": invalid_ir_blocked,
            "time_horizons_are_first_class": [row["duration_seconds"] for row in ir["horizons"]] == [600, 86400, 2592000],
            "critical_unknown_state_requires_evidence": actionability["disposition"] == "ABSTAIN_ACQUIRE_EVIDENCE",
            "epistemic_status_is_preserved": next(item for item in ir["objects"] if item["object_id"] == "delay-evidence")["epistemic_state"]["status"] == "UNKNOWN",
            "human_behavior_is_explicit": bool(next(item for item in ir["objects"] if item["object_id"] == "operator")["behavior_model"]["incentives"]),
            "human_scenario_is_deterministic": behavior == behavior_again,
            "human_scenario_preserves_claim_boundary": behavior_record["scenario"]["model_status"] == "ASSUMPTION_DRIVEN_SCENARIO_NOT_HUMAN_GROUND_TRUTH",
            "composition_causal_order_is_executable": run["causal_trace"]["ordered_mechanisms"] == ["capacity-degradation@2.0.0", "authority-revocation@2.0.0", "deadline-pressure@2.0.0"],
            "composition_amplification_changes_registered_transition": one_day["state"]["objects"]["risk"]["attributes"]["score"] == 0.5,
            "composition_replay_is_deterministic": run["run_sha256"] == run_again["run_sha256"] and run["verification"]["deterministic_replay"],
            "composition_is_bound_to_ir_hash": run_record["run"]["institution_ir"]["ir_sha256"] == ir["ir_sha256"],
            "delayed_effect_appears_at_registered_horizon": one_day["state"]["objects"]["risk"]["attributes"]["score"] > 0.1,
            "composition_creates_ledger_experience": parent["provenance"]["composition_run_sha256"] == run["run_sha256"],
            "cyclic_causal_composition_is_rejected": cycle_blocked,
            "counterfactual_generation_is_active": len(batch["branches"]) == 2,
            "counterfactuals_are_replay_verified": batch["all_branches_replay_verified"],
            "counterfactual_changes_outcome": any(branch["verification"]["outcome_changed"] for branch in batch["branches"]),
            "counterfactual_parentage_is_preserved": all(child["counterfactual_parent_id"] == parent["experience_id"] for child in children),
            "counterfactual_batch_is_custodied": len(batch_record["child_experience_ids"]) == 2,
            "governed_abstraction_stores_no_raw_payload": intake["raw_payload_stored"] is False and abstraction["raw_payload_stored"] is False,
            "unsafe_raw_fields_are_rejected": raw_rejected,
            "real_abstraction_requires_review": real_experience["training_eligible"] is False and real_experience["requires_review"] is True,
            "product_audit_chain_remains_valid": store.verify_audit_chain("tenant-002"),
        }
        return {
            "schema_version": "actionnet-platform-002-evaluation.v1",
            "evaluation_id": "ACTIONNET-PLATFORM-002",
            "status": "PASS" if all(gates.values()) else "FAIL",
            "gates": gates,
            "checks_passed": sum(bool(value) for value in gates.values()),
            "check_count": len(gates),
            "counts": store.counts(),
            "binding_authority": False,
            "production_ready": False,
            "claim_scope": "Internal active-experience product integration evidence only",
        }