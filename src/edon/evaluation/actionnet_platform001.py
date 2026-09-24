"""ACTIONNET-PLATFORM-001 governed product workflow evaluation."""

from __future__ import annotations

import tempfile
from pathlib import Path

from edon.actionnet.product import (
    ActionNetPlatformError,
    ActionNetPlatformStore,
    ProceduralInstitutionGenerator,
)
from edon.common.hashing import sha256_json


def _mechanism_spec(effect: str) -> dict:
    return {
        "preconditions": ["registered institutional state"],
        "state_transitions": [{"effect": effect}],
        "dependencies": [],
        "interventions": ["review and mitigate"],
        "failure_modes": ["unmitigated consequence"],
        "expected_outcomes": ["bounded recovery"],
    }


def run_actionnet_platform001() -> dict:
    """Exercise the governed ActionNet product path with deterministic fixtures."""
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        store = ActionNetPlatformStore(root / "actionnet-platform.sqlite3")
        capacity = store.register_mechanism(
            "tenant-product", "capacity-degradation", "1.0.0",
            "Capacity degradation",
            "A registered resource loses usable capacity under institutional constraints.",
            _mechanism_spec("capacity decreases"), domains=["healthcare", "logistics"],
            evidence_grade="SYNTHETIC_VERIFIED", source_lineage=["actionnet-008"],
            created_by="author", created_at="2026-08-23T08:00:00+00:00",
        )
        authority = store.register_mechanism(
            "tenant-product", "authority-revocation", "1.0.0",
            "Authority revocation",
            "Previously available institutional authority is explicitly withdrawn.",
            _mechanism_spec("authority becomes unavailable"), domains=["banking"],
            evidence_grade="EXPERT_REVIEWED", source_lineage=["expert-pack-001"],
            created_by="author", created_at="2026-08-23T08:00:01+00:00",
        )
        edge = store.register_composition_edge(
            "tenant-product", "edge-capacity-authority",
            "capacity-degradation", "1.0.0", "authority-revocation", "1.0.0",
            "AMPLIFIES", conditions={"when": "mitigation requires revoked authority"},
            evidence_grade="EXPERT_REVIEWED",
            provenance={"source": "bounded expert hypothesis"}, created_by="author",
            created_at="2026-08-23T08:00:02+00:00",
        )

        generator = ProceduralInstitutionGenerator()
        world_spec = {
            "institution_type": "LOGISTICS",
            "departments": 4, "actors": 12, "resources": 8,
            "policies": 6, "workflows": 7, "authority_levels": 3, "goals": 2,
        }
        generated_a = generator.generate("world-001", world_spec, seed=23, adversarial=True)
        generated_b = generator.generate("world-001", world_spec, seed=23, adversarial=True)
        blueprint = store.register_world_blueprint(
            "tenant-product", "world-001", "1.0.0", generated_a,
            generator_seed=23, adversarial=True, protected=False, created_by="author",
            created_at="2026-08-23T08:00:03+00:00",
        )

        experience = store.record_experience(
            "tenant-product", "experience-001", "SIMULATOR", "logistics",
            [{"mechanism_id": "capacity-degradation", "version": "1.0.0"}],
            {
                "initial_state": {"capacity": 100},
                "event": {"capacity_loss": 20},
                "intermediate_states": [{"capacity": 80}],
                "outcome": {"capacity": 80},
            },
            {"path": ["capacity loss", "available capacity decreases"]},
            evidence_grade="SYNTHETIC_VERIFIED",
            provenance={"blueprint_sha256": blueprint["record_sha256"]},
            created_by="author", created_at="2026-08-23T08:00:04+00:00",
        )
        protected = store.record_experience(
            "tenant-product", "protected-001", "SIMULATOR", "logistics",
            [{"mechanism_id": "capacity-degradation", "version": "1.0.0"}],
            {"initial_state": {"capacity": 100}, "outcome": {"capacity": 60}},
            {"path": ["protected disruption", "capacity decreases"]},
            evidence_grade="SYNTHETIC_VERIFIED", provenance={"vault": "sealed"},
            created_by="custodian", protected=True,
            created_at="2026-08-23T08:00:05+00:00",
        )
        counterfactual = store.record_experience(
            "tenant-product", "counterfactual-001", "SIMULATOR", "logistics",
            [{"mechanism_id": "capacity-degradation", "version": "1.0.0"}],
            {"initial_state": {"capacity": 100}, "intervention": "redistribute", "outcome": {"capacity": 90}},
            {"path": ["capacity loss", "redistribution", "partial recovery"]},
            counterfactual_parent_id="experience-001",
            failure_classification="CAPACITY_DEGRADATION",
            evidence_grade="SOLVER_VERIFIED", provenance={"parent": "experience-001"},
            created_by="author", created_at="2026-08-23T08:00:06+00:00",
        )

        reviews = (
            ("review-domain", "domain-reviewer", "ACTIONNET_DOMAIN_REVIEWER", "DOMAIN"),
            ("review-safety", "safety-reviewer", "ACTIONNET_SAFETY_REVIEWER", "SAFETY"),
            ("review-lineage", "custodian", "ACTIONNET_CUSTODIAN", "LINEAGE"),
            ("review-training", "release-reviewer", "ACTIONNET_RELEASE_MANAGER", "TRAINING"),
        )
        for index, (review_id, reviewer_id, role, dimension) in enumerate(reviews):
            store.review_experience(
                "tenant-product", review_id, "experience-001", reviewer_id, role,
                dimension, "APPROVE", f"Approved {dimension.lower()} controls for product release.",
                created_at=f"2026-08-23T08:01:0{index}+00:00",
            )
        store.record_overlap_check(
            "tenant-product", "experience-001", True,
            {"protected_overlap": 0, "duplicate_overlap": 0}, actor_id="custodian",
            created_at="2026-08-23T08:01:10+00:00",
        )
        store.approve_training_eligibility(
            "tenant-product", "experience-001", release_manager_id="release-manager",
            rationale="All required independent reviews and overlap controls passed.",
            created_at="2026-08-23T08:01:11+00:00",
        )
        approved_state = store.experience_state("tenant-product", "experience-001")
        release = store.create_training_release(
            "tenant-product", "actionnet-release-001", ["experience-001"],
            "cerebrum-candidate", release_manager_id="release-manager",
            created_at="2026-08-23T08:01:12+00:00",
        )
        exposure = store.record_model_exposure(
            "tenant-product", "exposure-001", "experience-001", "cerebrum-candidate",
            "TRAIN", created_by="release-manager", dataset_release_id="actionnet-release-001",
            created_at="2026-08-23T08:01:13+00:00",
        )
        protected_blocked = False
        try:
            store.record_model_exposure(
                "tenant-product", "bad-exposure", "protected-001", "cerebrum-candidate",
                "TRAIN", created_by="release-manager",
            )
        except ActionNetPlatformError:
            protected_blocked = True

        coverage = store.coverage_report("tenant-product", minimum_experiences=3, minimum_domains=2)
        snapshot = store.freeze_coverage_snapshot(
            "tenant-product", "coverage-001", created_by="curriculum-operator",
            minimum_experiences=3, minimum_domains=2,
            created_at="2026-08-23T08:01:14+00:00",
        )
        acquisition = store.recommend_acquisition(
            "tenant-product", "acquisition-001", created_by="curriculum-operator",
            minimum_experiences=3, minimum_domains=2,
            created_at="2026-08-23T08:01:15+00:00",
        )
        intervention = store.record_intervention_candidate(
            "tenant-product", "intervention-001", "regional-network", ["experience-001"],
            {"type": "REDISTRIBUTE_CAPACITY", "amount": 10},
            {"service_level": "maximize", "cost": "minimize"},
            {"safety_floor": 0.99, "legal_compliance": "required"},
            {"capacity": 90, "risk": 0.1},
            {"simulator": "passed", "solver": "feasible", "expert": "pending"},
            0.72, created_by="intervention-lab",
            created_at="2026-08-23T08:01:16+00:00",
        )
        authority_smuggling_blocked = False
        try:
            store.record_intervention_candidate(
                "tenant-product", "bad-intervention", "regional-network", ["experience-001"],
                {"type": "REDISTRIBUTE_CAPACITY", "binding_authority": True},
                {}, {}, {}, {}, 0.9, created_by="intervention-lab",
            )
        except ActionNetPlatformError:
            authority_smuggling_blocked = True
        tenant_isolation = False
        try:
            store.experience_state("other-tenant", "experience-001")
        except ActionNetPlatformError:
            tenant_isolation = True

        gates = {
            "mechanism_registry_versioned": capacity["record_sha256"] != authority["record_sha256"],
            "composition_edge_evidence_graded": edge["evidence_grade"] == "EXPERT_REVIEWED",
            "procedural_world_deterministic": generated_a == generated_b,
            "procedural_world_safe_defaults": (
                generated_a["training_eligible"] is False
                and generated_a["binding_authority"] is False
            ),
            "experience_safe_defaults": (
                experience["training_eligible"] is False
                and experience["authoritative"] is False
                and experience["requires_review"] is True
            ),
            "counterfactual_parent_preserved": counterfactual["counterfactual_parent_id"] == "experience-001",
            "protected_vault_blocks_training": protected_blocked and protected["protected"] is True,
            "independent_review_dimensions_required": len(approved_state["reviews"]) == 4,
            "training_eligibility_is_explicit": approved_state["training_eligible"] is True,
            "training_release_hash_bound": release["experience_hashes"]["experience-001"] == experience["content_sha256"],
            "model_exposure_recorded": exposure["purpose"] == "TRAIN",
            "coverage_is_registered_not_universal": "registered product matrix" in coverage["claim_boundary"],
            "coverage_snapshot_frozen": snapshot["report_sha256"] == sha256_json(snapshot["report"]),
            "active_acquisition_targets_gap": "authority-revocation@1.0.0" in acquisition["target_mechanism_ids"],
            "intervention_candidate_non_binding": (
                intervention["binding_authority"] is False
                and intervention["requires_kernel_authorization"] is True
            ),
            "authority_smuggling_rejected": authority_smuggling_blocked,
            "tenant_isolation": tenant_isolation,
            "audit_chain_valid": store.verify_audit_chain("tenant-product"),
        }
        return {
            "schema_version": "actionnet-platform-001-evaluation.v1",
            "evaluation_id": "ACTIONNET-PLATFORM-001",
            "status": "PASS" if all(gates.values()) else "FAIL",
            "gates": gates,
            "checks_passed": sum(gates.values()),
            "check_count": len(gates),
            "binding_authority": False,
            "production_ready": False,
            "claim_scope": "Internal product-workflow evidence only",
        }