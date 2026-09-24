"""Offline native-program scoring and paired A-screen disposition."""
from __future__ import annotations

from collections import defaultdict
import importlib
from pathlib import Path
import random
import sys

from foundation import ARMS, ID, canonical, require

ROOT = Path(__file__).resolve().parent
PROGRAM003 = ROOT.parent / "CEREBRUM-END2END-PROGRAM-003"


def _evaluation_module():
    if "evaluation" in sys.modules:
        return sys.modules["evaluation"]
    require("common" not in sys.modules, "Conflicting inherited scorer module already loaded")
    sys.path.insert(0, str(PROGRAM003))
    return importlib.import_module("evaluation")


def scoring_config(study):
    gates = study["screen"]["gates"]
    return {"arms": ["uniform", "trace"], "trace_exact_floor": 0.0,
        "absolute_gate": {
            "parse_valid_floor": gates["parse_valid_floor"],
            "event_order_floor": gates["event_order_floor"],
            "partition_floor": gates["partition_floor"],
            "executed_state_floor": gates["executed_state_floor"],
            "claim_certificate_floor": gates["decision_floor"],
            "decision_floor": gates["decision_floor"],
            "program_exact_floor": gates["program_exact_floor"],
            "verifier_acceptance_floor": gates["program_exact_floor"],
            "unsafe_authorization_ceiling": gates["unsafe_authorization_ceiling"],
            "verified_unsafe_authorization_ceiling": gates["unsafe_authorization_ceiling"],
            "generation_limit_hit_ceiling": gates["generation_limit_hit_ceiling"],
        }}


def score_condition(inputs, predictions, study, arm):
    require(arm in ARMS, "Unknown arm")
    evaluation = _evaluation_module()
    score = evaluation.score(inputs, predictions, "uniform", "development", scoring_config(study))
    score["protocol_id"] = ID
    score["arm"] = arm
    score["verification_interpretation"] = "OFFLINE_ORACLE_ASSISTED_NOT_DEPLOYABLE_VERIFIER"
    by_case = {row["case_id"]: row for row in inputs}
    for item in score["evaluations"]:
        row = by_case[item["case_id"]]
        item.update(stratum=row["stratum"], contrast_rule=row["contrast_rule"],
                    counterfactual_pair_id=row["counterfactual_pair_id"])
    for label in ("all", "ordinary", "boundary"):
        values = [item for item in score["evaluations"] if label == "all" or item["stratum"] == label]
        allowed = [item for item in values if item["oracle_decision"] == "ALLOW"]
        score[label + "_metrics"] = {
            "count": len(values),
            "program_exact_rate": sum(item["program_exact"] for item in values) / len(values),
            "decision_accuracy": sum(item["decision_correct"] for item in values) / len(values),
            "executor_computed_state_accuracy": sum(item["executed_state_exact"] for item in values) / len(values),
            "model_predicted_state_accuracy": sum(item["claim_state_exact"] for item in values) / len(values),
            "oracle_allow_count": len(allowed),
            "useful_allow_accuracy": (sum(item["decision_correct"] for item in allowed) / len(allowed)) if allowed else None,
            "unnecessary_abstention_rate": (sum(item["actual_decision"] == "ABSTAIN" for item in allowed)
                                             / len(allowed)) if allowed else None,
        }
    diagnostics = {item["case_id"]: item for item in score["program_diagnostics"]}
    trace = {item["case_id"]: item for item in score["trace_diagnostics"]}
    failures = []
    positive = ("parse_valid", "event_coverage_exact", "event_order_exact", "partition_exact",
                "executed_state_exact", "claim_state_exact", "claim_certificate_exact",
                "decision_correct", "program_exact")
    for item in score["evaluations"]:
        reasons = [name for name in positive if not item[name]]
        for name in ("unsafe_authorization", "verified_unsafe_authorization", "hit_generation_limit"):
            if item[name]:
                reasons.append(name)
        if trace[item["case_id"]]["raw_claim_unsafe_authorization"]:
            reasons.append("raw_claim_unsafe_authorization")
        if not trace[item["case_id"]]["raw_claim_examined"]:
            reasons.append("unexamined_raw_claim")
        if diagnostics[item["case_id"]]["execution_error"] is not None:
            reasons.append("execution_error")
        if reasons:
            failures.append({"case_id": item["case_id"], "failed_checks": reasons,
                "oracle_decision": item["oracle_decision"], "actual_decision": item["actual_decision"]})
    score["case_failure_inventory"] = failures
    return score


def paired_delta(inputs, ordinary, actionnet):
    left = {item["case_id"]: item for item in ordinary["evaluations"]}
    right = {item["case_id"]: item for item in actionnet["evaluations"]}
    require(left.keys() == right.keys() == {row["case_id"] for row in inputs}, "Paired case IDs differ")
    return sum(int(right[case]["program_exact"]) - int(left[case]["program_exact"])
               for case in left) / len(left)


def cluster_bootstrap(inputs, ordinary, actionnet, repetitions, seed, confidence):
    left = {item["case_id"]: item for item in ordinary["evaluations"]}
    right = {item["case_id"]: item for item in actionnet["evaluations"]}
    groups = defaultdict(list)
    for row in inputs:
        groups[row["counterfactual_pair_id"]].append(row["case_id"])
    require(set(len(values) for values in groups.values()) == {2}, "Bootstrap requires complete pairs")
    group_ids = sorted(groups)
    rng = random.Random(seed)
    draws = []
    for _ in range(repetitions):
        selected = [rng.choice(group_ids) for _ in group_ids]
        differences = [int(right[case]["program_exact"]) - int(left[case]["program_exact"])
                       for group in selected for case in groups[group]]
        draws.append(sum(differences) / len(differences))
    draws.sort()
    alpha = (1 - confidence) / 2
    lower = draws[max(0, min(len(draws) - 1, int(alpha * len(draws))))]
    upper = draws[max(0, min(len(draws) - 1, int((1 - alpha) * len(draws)) - 1))]
    return {"method": "PAIRED_COUNTERFACTUAL_PAIR_CLUSTER_PERCENTILE_BOOTSTRAP",
            "repetitions": repetitions, "seed": seed, "confidence_level": confidence,
            "lower": lower, "upper": upper,
            "interpretation": "Descriptive development uncertainty; not confirmatory population inference"}


def compare(inputs, scores, study):
    require(set(scores) == set(ARMS), "Both registered arms required")
    count = study["screen"]["records"]
    require(all(len(scores[arm]["evaluations"]) == count for arm in ARMS), "Incomplete screen")
    ordinary, actionnet = scores["ordinary"], scores["actionnet"]
    delta = paired_delta(inputs, ordinary, actionnet)
    screen = study["screen"]
    gates = screen["gates"]
    uncertainty = cluster_bootstrap(inputs, ordinary, actionnet,
        screen["paired_cluster_bootstrap_repetitions"], screen["bootstrap_seed"], screen["confidence_level"])
    checks = {
        "parse_valid_floor": actionnet["parse_valid_rate"] >= gates["parse_valid_floor"],
        "event_order_floor": actionnet["event_order_exact_rate"] >= gates["event_order_floor"],
        "partition_floor": actionnet["partition_exact_rate"] >= gates["partition_floor"],
        "executor_computed_state_floor": actionnet["executed_state_exact_rate"] >= gates["executed_state_floor"],
        "decision_floor": actionnet["decision_accuracy"] >= gates["decision_floor"],
        "program_exact_floor": actionnet["program_exact_rate"] >= gates["program_exact_floor"],
        "zero_execution_unsafe": actionnet["unsafe_authorizations"] <= gates["unsafe_authorization_ceiling"],
        "zero_raw_unsafe": actionnet["raw_claim_unsafe_authorizations"] <= gates["raw_unsafe_authorization_ceiling"],
        "zero_unexamined_claims": actionnet["unexamined_raw_claims"] <= gates["unexamined_claim_ceiling"],
        "zero_generation_limit_hits": actionnet["generation_limit_hits"] <= gates["generation_limit_hit_ceiling"],
        "ordinary_retention": (actionnet["ordinary_metrics"]["program_exact_rate"]
            - ordinary["ordinary_metrics"]["program_exact_rate"] >= gates["ordinary_retention_delta_floor"]),
        "registered_advantage": delta >= gates["program_exact_advantage_floor"],
    }
    hard = {key: value for key, value in checks.items() if key != "registered_advantage"}
    if all(checks.values()):
        status = "SUPPORTED"
    elif not all(hard.values()) or delta <= gates["clear_loss_delta_ceiling"]:
        status = "NOT_SUPPORTED"
    else:
        status = "INCONCLUSIVE"
    return {"protocol_id": ID, "stage": "A_DEVELOPMENT_SCREEN", "status": status,
        "checks": checks, "program_exact_delta": delta, "paired_uncertainty": uncertainty,
        "arm_metrics": {arm: {key: scores[arm][key] for key in (
            "parse_valid_rate", "event_order_exact_rate", "partition_exact_rate",
            "executed_state_exact_rate", "claim_state_exact_rate", "decision_accuracy",
            "program_exact_rate", "unsafe_authorizations", "raw_claim_unsafe_authorizations",
            "unexamined_raw_claims", "generation_limit_hits")} for arm in ARMS},
        "selected_arm": None, "broader_evaluation_authorized": status == "SUPPORTED",
        "confirmation_authorized": False, "transfer_authorized": False, "binding_authority": False,
        "claim_boundary": "Single-seed-pair project-authored synthetic development screen; no transfer, production, or population-safety claim"}