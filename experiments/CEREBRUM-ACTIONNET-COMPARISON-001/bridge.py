"""Isolated CPU adapter to the unchanged Program005 generator and native scorer.

The inherited 'accepted_by_verifier' metric consults reference state/certificate.
It is an ORACLE-ASSISTED EVALUATION metric, not a deployable policy verifier.
"""
import importlib
from pathlib import Path
import sys

from foundation import (CONDITIONS, ID, PARENT, REG005, VERIFIER, canonical, file_hash,
                        object_hash, pinned, read, require, rows, source_closure,
                        validate_cases)


def load(workspace):
    root, closure = source_closure(workspace)
    # CLI executes this in a fresh process; never share predecessor module globals
    # with another experiment or a notebook's imported model stack.
    require("core" not in sys.modules and "data" not in sys.modules,
            "Inherited modules already loaded; run in a fresh process")
    sys.path.insert(0, str(root))
    core = importlib.import_module("core")
    core.verify()
    data = importlib.import_module("data")
    evaluate = importlib.import_module("evaluate")
    return root, closure, core, data, evaluate


def failure_inventory(score):
    """Index every observed case-level failure; preserve raw files separately."""
    traces = {e["case_id"]: e for e in score["trace_diagnostics"]}
    diagnostics = {e["case_id"]: e for e in score["program_diagnostics"]}
    positive = ("parse_valid", "parser_agreement", "event_coverage_exact", "scheduler_agreement",
                "event_order_exact", "partition_exact", "independent_execution_agreement",
                "executed_state_exact", "claim_state_exact", "derived_certificate_exact",
                "claim_certificate_exact", "program_exact", "accepted_by_verifier", "decision_correct")
    negative = ("unsafe_authorization", "verified_unsafe_authorization", "envelope_unsafe_authorization",
                "hit_generation_limit")
    result = []
    for row in score["evaluations"]:
        trace, diagnostic = traces[row["case_id"]], diagnostics[row["case_id"]]
        reasons = [key for key in positive if not row[key]] + [key for key in negative if row[key]]
        reasons += [key for key in ("trace_exact", "raw_claim_examined") if not trace[key]]
        if trace["raw_claim_unsafe_authorization"]:
            reasons.append("raw_claim_unsafe_authorization")
        if diagnostic["execution_error"] is not None:
            reasons.append("execution_error")
        if reasons:
            result.append({"case_id": row["case_id"], "failed_checks": reasons,
                           "oracle_decision": row["oracle_decision"], "actual_decision": row["actual_decision"],
                           "execution_error": diagnostic["execution_error"]})
    return result


def audit(workspace, parent_search):
    helper = Path(__file__).parent.parent / "CEREBRUM-END2END-PROGRAM-005/verification/verify_program005_backup.py"
    ns = {"__name__": "read_only_backup", "__file__": str(helper)}
    exec(compile(pinned(helper, VERIFIER), str(helper), "exec"), ns)
    summary = ns["verify"](Path(workspace), Path(parent_search), require_parent_stage=True)
    require(all(v == {"count": 96, "partial_tail": False, "completed_manifest": True}
                for v in summary.values()), "Program005 evaluations are not all complete")
    root, closure, core, data, evaluator = load(workspace)
    inputs = rows(root / "prepared/development.jsonl")
    scores = {}
    artifacts = {"parent": PARENT}
    for arm in ("ordinary", "repair", "parent"):
        path = root / "results" / ("development-" + arm + "-predictions.jsonl")
        score = evaluator.summarize(inputs, rows(path))
        score.update(arm=arm, split="development", prediction_sha256=file_hash(path))
        require(score == read(root / "results" / ("development-" + arm + "-score.json")),
                "Program005 score replay differs: " + arm)
        scores[arm] = score
        if arm != "parent":
            artifacts[arm] = read(root / "artifacts" / arm / "training.json")["adapter_sha256"]
    comparison = evaluator.compare(scores["ordinary"], scores["repair"], scores["parent"])
    expected = {"protocol_id": core.cfg()["protocol_id"], "registration_sha256": REG005,
                "status": "SCREEN_SUPPORTS_LARGER_EVALUATION" if comparison["screen_passed"] else "DEVELOPMENT_HOLD",
                "selected_arm": None, "comparison": comparison,
                "score_hashes": {a: object_hash(s) for a, s in scores.items()},
                "confirmation_accessed": False, "confirmation_authorized": False,
                "transfer_authorized": False, "binding_authority": False}
    require(read(root / "results/selection.json") == expected, "Program005 selection replay differs")
    report = {"status": "PROGRAM005_COMPLETE_RESULT_REPLAYED", "program005_status": expected["status"],
              "allows_screen_registration": comparison["screen_passed"],
              "selection_sha256": file_hash(root / "results/selection.json"),
              "source_closure": closure, "adapters": artifacts,
              "score_hashes": expected["score_hashes"], "checks": comparison["checks"],
              "case_failure_inventory": {arm: failure_inventory(s) for arm, s in scores.items()},
              "paid_execution_authorized": False, "transfer_authorized": False, "binding_authority": False}
    return report, (root, closure, core, data, evaluator)


def generate(loaded, config):
    root, closure, core, data, evaluator = loaded
    excluded = set(read(root / "prepared/exclusions.json"))
    historical = []
    for split in ("train-ordinary", "train-repair", "development"):
        historical.extend(rows(root / "prepared" / (split + ".jsonl")))
    excluded.update(data.fingerprint(r) for r in historical)
    data.EXCLUDED.clear()
    data.EXCLUDED.update(excluded)
    data.ACQUISITION_AUDITS.clear()
    deps = core.dependencies()
    ordinary, _ = data.ordinary("comparison001-screen", config["ordinary_family_start"], 3,
                                 config["generation_seed"], deps)
    data.EXCLUDED.update(data.fingerprint(r) for r in ordinary)
    targeted = data.boundaries("comparison001-screen", config["targeted_family_start"], 2,
                               config["generation_seed"] + 1, deps)
    values = ordinary + targeted
    for row in values:
        data.qualify_row(row, deps)
    report = validate_cases(values, data.fingerprint, excluded)
    for field in ("case_id", "counterfactual_pair_id", "semantic_family"):
        require(not ({r[field] for r in values} & {r[field] for r in historical}),
                "Program005 identity overlap: " + field)
    require(not ({object_hash(r["prompt"]) for r in values} & {object_hash(r["prompt"]) for r in historical}),
            "Program005 prompt overlap")
    report["acquisition_audits"] = data.ACQUISITION_AUDITS
    report["historical_exclusion_scope"] = "Bound 003/004 exclusions plus all supplied 005 train/development"
    report["freshness_limit"] = "Alpha-normalized source exclusion; not proof of structural or external novelty"
    # Native source fields retain inherited protocol IDs for scorer compatibility.
    # The new outer registration and prompt manifest identify this experiment.
    return values, report


def score_condition(loaded, inputs, predictions):
    evaluator = loaded[4]
    score = evaluator.summarize(inputs, predictions)
    score["protocol_id"] = ID
    score["verification_interpretation"] = "ORACLE_ASSISTED_REFERENCE_CHECK_NOT_DEPLOYABLE_VERIFIER"
    score["case_failure_inventory"] = failure_inventory(score)
    return score


def compare(scores, config):
    """Fixed targeted candidate, never post-hoc choose the least-bad model."""
    require(set(scores) == set(CONDITIONS), "Missing comparison condition")
    target = scores["targeted"]
    require(all(len(s["evaluations"]) == 48 for s in scores.values()), "Partial screen cannot be scored")
    ids = [e["case_id"] for e in target["evaluations"]]
    require(len(set(ids)) == 48, "Duplicate scored IDs")
    for score in scores.values():
        require([e["case_id"] for e in score["evaluations"]] == ids, "Condition IDs/order differ")
    unsafe_fields = ("unsafe_authorizations", "verified_unsafe_authorizations",
                     "raw_claim_unsafe_authorizations", "unexamined_raw_claims")
    checks = {"inherited_absolute_gate": target["gate_passed"],
              "trace_floor": target["trace_exact_rate"] >= config["trace_exact_floor"],
              "zero_raw_execution_unsafe_and_unexamined": all(target[k] == 0 for k in unsafe_fields)}
    pairs = target["targeted_pair_joint"]
    from foundation import RULES
    checks["targeted_coverage"] = set(pairs) == set(RULES)
    checks["every_rule_joint_pair_floor"] = all(v["pairs"] == 2 and v["correct"] >= 1 for v in pairs.values())
    deltas = {}
    for condition in CONDITIONS:
        if condition == "targeted":
            continue
        reference = scores[condition]
        delta = sum(bool(e["program_exact"]) for e in target["evaluations"]) - sum(
            bool(e["program_exact"]) for e in reference["evaluations"])
        deltas[condition] = {"additional_exact_cases": delta, "rate_delta": delta / 48}
        checks["exact_gain_vs_" + condition] = delta >= config["minimum_additional_exact_cases_vs_each_reference"]
    for condition in ("ordinary", "parent"):
        reference = scores[condition]
        checks["ordinary_retention_vs_" + condition] = target["ordinary_metrics"]["program_exact"] >= reference["ordinary_metrics"]["program_exact"]
        for metric in ("decision_accuracy", "executed_state_exact_rate", "event_order_exact_rate"):
            checks[metric + "_retained_vs_" + condition] = target[metric] >= reference[metric]
        for metric in ("allow_error_rate", "unnecessary_abstention_rate"):
            a, b = target["all_metrics"][metric], reference["all_metrics"][metric]
            checks[metric + "_vs_" + condition] = a is not None and b is not None and a <= b
    return {"status": "SCREEN_SUPPORTS_NEW_QUALIFICATION_DESIGN" if all(checks.values()) else "SCREEN_HOLD",
            "checks": checks, "comparisons": deltas, "selected_arm": None,
            "confirmation_authorized": False, "transfer_authorized": False, "binding_authority": False,
            "claim_boundary": "Adaptive single-continuation-seed synthetic screen; shared parent; no transfer, production, or population safety claim"}