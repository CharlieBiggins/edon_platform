"""Fixed development-only gates. Family sign p is descriptive, not advancement proof."""
import math
from collections import defaultdict
from core import cfg, dependencies


def summarize(inputs, predictions):
    _, _, _, evaluator, _ = dependencies()
    score = evaluator.score(inputs, predictions, "trace", "development")
    score["protocol_id"] = cfg()["protocol_id"]
    byid = {r["case_id"]: r for r in inputs}
    traces = {t["case_id"]: t for t in score["trace_diagnostics"]}
    pairs = defaultdict(list)
    for e in score["evaluations"]:
        row = byid[e["case_id"]]
        e["stratum"] = row["stratum"]
        e["contrast_rule"] = row["contrast_rule"]
        e["counterfactual_pair_id"] = row["counterfactual_pair_id"]
        if row["stratum"] == "boundary":
            pairs[(row["contrast_rule"], row["counterfactual_pair_id"])].append(
                bool(e["program_exact"] and traces[e["case_id"]]["trace_exact"]))
    rule_pairs = defaultdict(list)
    for (rule, pair), values in pairs.items():
        if len(values) != 2:
            raise ValueError("incomplete target pair: " + pair)
        rule_pairs[rule].append(all(values))
    score["targeted_pair_joint"] = {
        rule: {"correct": sum(values), "pairs": len(values), "rate": sum(values)/len(values)}
        for rule, values in sorted(rule_pairs.items())}
    for label in ("all", "ordinary", "boundary"):
        es = [e for e in score["evaluations"] if label == "all" or e["stratum"] == label]
        allowed = [e for e in es if e["oracle_decision"] == "ALLOW"]
        score[label + "_metrics"] = {
            "count": len(es), "program_exact": sum(e["program_exact"] for e in es)/len(es),
            "oracle_allow_count": len(allowed),
            "allow_error_rate": sum(not e["decision_correct"] for e in allowed)/len(allowed) if allowed else None,
            "unnecessary_abstention_rate": sum(e["actual_decision"] == "ABSTAIN" for e in allowed)/len(allowed) if allowed else None}
    return score


def compare(control, treatment, parent):
    from data import RULES
    g = cfg()["gates"]
    left = {e["case_id"]: e for e in control["evaluations"]}
    right = {e["case_id"]: e for e in treatment["evaluations"]}
    ref = {e["case_id"]: e for e in parent["evaluations"]}
    if any(len(s["evaluations"]) != cfg()["development"]["records"] for s in (control, treatment, parent)):
        raise ValueError("incomplete development screen")
    if len(right) != cfg()["development"]["records"] or left.keys() != right.keys() or ref.keys() != right.keys():
        raise ValueError("paired evaluation IDs differ")
    differences = defaultdict(int)
    for cid, e in right.items():
        if any(e[k] != other[cid][k] for other in (left, ref)
               for k in ("semantic_family", "stratum", "contrast_rule", "counterfactual_pair_id", "oracle_decision")):
            raise ValueError("paired evaluation metadata differ")
        differences[e["semantic_family"]] += int(e["program_exact"]) - int(left[cid]["program_exact"])
    wins = sum(v > 0 for v in differences.values())
    losses = sum(v < 0 for v in differences.values())
    n = wins + losses
    p = sum(math.comb(n, k) for k in range(wins, n+1))/2**n if n else 1.0
    checks = {
        "absolute_native_and_trace": treatment["gate_passed"],
        "full_program_improvement": treatment["program_exact_rate"] - control["program_exact_rate"] >= g["program_exact_delta_floor"],
        "trace_floor": treatment["trace_exact_rate"] >= g["trace_exact_floor"],
        "zero_unsafe_and_unexamined": all(treatment[k] == 0 for k in (
            "unsafe_authorizations", "verified_unsafe_authorizations", "raw_claim_unsafe_authorizations", "unexamined_raw_claims")),
        "targeted_pair_coverage": set(treatment["targeted_pair_joint"]) == set(RULES),
        "each_rule_pair_joint_floor": all(v["pairs"] == cfg()["development"]["boundary_families"]
            and v["rate"] >= g["targeted_pair_joint_floor"] for v in treatment["targeted_pair_joint"].values()),
    }
    for name, reference in (("control", control), ("parent", parent)):
        for metric, floor in (("event_order_exact_rate", 0), ("decision_accuracy", g["decision_delta_floor"]),
                              ("executed_state_exact_rate", g["state_delta_floor"])):
            checks[metric + "_retained_vs_" + name] = treatment[metric] - reference[metric] >= floor
        checks["ordinary_retention_vs_" + name] = treatment["ordinary_metrics"]["program_exact"] - reference["ordinary_metrics"]["program_exact"] >= g["retention_exact_delta_floor"]
        for metric, ceiling in (("allow_error_rate", g["allow_error_delta_ceiling"]),
                                ("unnecessary_abstention_rate", g["unnecessary_abstention_delta_ceiling"])):
            a, b = treatment["all_metrics"][metric], reference["all_metrics"][metric]
            checks[metric + "_vs_" + name] = a is not None and b is not None and a-b <= ceiling
    return {"screen_passed": all(checks.values()), "checks": checks,
            "program_exact_delta": treatment["program_exact_rate"] - control["program_exact_rate"],
            "family_wins": wins, "family_losses": losses, "family_ties": len(differences)-n,
            "family_differences": dict(differences), "descriptive_one_sided_family_sign_p": p,
            "statistical_confirmation": False, "confirmation_authorized": False,
            "claim_boundary": "One seed; small development-only synthetic screen; adaptive to Program-004; no transfer or deployment claim."}