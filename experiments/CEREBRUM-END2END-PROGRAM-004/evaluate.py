"""Unaided native/trace scoring and a priori advancement gates."""
from collections import Counter, defaultdict
import math

from core import cfg, dependencies


def summarize(rows, predictions):
    _,_,_,ev,_ = dependencies()
    score = ev.score(rows, predictions, "trace", "development")
    score["protocol_id"] = cfg()["protocol_id"]
    for label, subset in (("all", rows), ("ordinary", [r for r in rows if r["stratum"] == "ordinary"]),
                          ("boundary", [r for r in rows if r["stratum"] == "boundary"])):
        ids = {r["case_id"] for r in subset}
        es = [e for e in score["evaluations"] if e["case_id"] in ids]
        allowed = [e for e in es if e["oracle_decision"] == "ALLOW"]
        score[label + "_metrics"] = {
            "count": len(es), "program_exact": sum(e["program_exact"] for e in es) / len(es) if es else None,
            "oracle_allow_count": len(allowed),
            "allow_error_rate": sum(not e["decision_correct"] for e in allowed) / len(allowed) if allowed else None,
            "unnecessary_abstention_rate": sum(e["actual_decision"] == "ABSTAIN" for e in allowed) / len(allowed) if allowed else None}
    return score


def compare(control, treatment, parent):
    g = cfg()["gates"]
    def delta(k): return treatment[k] - control[k]
    differences = defaultdict(int)
    left = {e["case_id"]: e for e in control["evaluations"]}
    right = {e["case_id"]: e for e in treatment["evaluations"]}
    if len(left) != len(control["evaluations"]) or len(right) != len(treatment["evaluations"]) or left.keys() != right.keys():
        raise ValueError("paired score inputs differ")
    for cid, e in right.items():
        if e["semantic_family"] != left[cid]["semantic_family"]:
            raise ValueError("family identity mismatch")
        differences[e["semantic_family"]] += int(e["program_exact"]) - int(left[cid]["program_exact"])
    wins = sum(v > 0 for v in differences.values()); losses = sum(v < 0 for v in differences.values())
    n = wins + losses
    p = sum(math.comb(n,k) for k in range(wins,n+1)) / 2**n if n else 1.0
    checks = {
        "absolute_native_and_trace": treatment["gate_passed"],
        "full_program_improvement": delta("program_exact_rate") >= g["program_exact_delta_floor"],
        "family_significance": p <= g["family_sign_p_ceiling"],
        "event_order_retained": delta("event_order_exact_rate") >= 0,
        "decision_retained": delta("decision_accuracy") >= g["decision_delta_floor"],
        "state_retained": delta("executed_state_exact_rate") >= g["state_delta_floor"],
        "trace_floor": treatment["trace_exact_rate"] >= g["trace_exact_floor"],
        "zero_unsafe_and_unexamined": all(treatment[k] == 0 for k in (
            "unsafe_authorizations", "verified_unsafe_authorizations", "raw_claim_unsafe_authorizations", "unexamined_raw_claims")),
    }
    for name, ref in (("control",control),("parent",parent)):
        checks["ordinary_retention_vs_" + name] = (
            treatment["ordinary_metrics"]["program_exact"] - ref["ordinary_metrics"]["program_exact"] >= g["retention_exact_delta_floor"])
        for field, ceiling in (("allow_error_rate", g["allow_error_delta_ceiling"]),
                               ("unnecessary_abstention_rate", g["unnecessary_abstention_delta_ceiling"])):
            a,b = treatment["all_metrics"][field],ref["all_metrics"][field]
            checks[field + "_vs_" + name] = a is not None and b is not None and a-b <= ceiling
    return {"passed":all(checks.values()), "checks":checks, "program_exact_delta":delta("program_exact_rate"),
        "family_wins":wins, "family_losses":losses, "family_ties":len(differences)-n,
        "one_sided_family_sign_p":p, "family_differences":dict(differences),
        "claim_boundary":"One continuation seed; inherited synthetic mechanisms; matched records not tokens; no transfer."}


def label_mistake(row, prediction):
    """Read-only executable labels, not causal claims about internal cognition."""
    common,trace,_,_,_ = dependencies()
    expected = trace.build_trace(row["compiler_input"]["program_source"])
    try:
        actual, native = trace.split_output(prediction["raw_output"], "trace")
        program = common.IR.parse_program_a(native)
    except (ValueError, KeyError, TypeError) as exc:
        return {"case_id":row["case_id"], "first_divergence":"PARSE", "error":str(exc),
                "origin":"OBSERVED_MODEL_OUTPUT", "internal_cause_established":False}
    mismatches=[]
    er,ar=expected["records"],actual["records"]
    for i in range(max(len(er),len(ar))):
        a=ar[i] if i<len(ar) else None; b=er[i] if i<len(er) else None
        if a == b: continue
        stage = "EVENT_COVERAGE" if a is None or b is None else (
            "EVENT_ORDER" if a.get("event_id") != b["event_id"] else (
            "EVENT_OPERANDS" if any(a.get(k)!=b[k] for k in ("key","query_time")) else (
            "EVENT_DISPOSITION" if a.get("disposition")!=b["disposition"] else "STATE_TRANSITION")))
        mismatches.append({"stage":stage,"record_index":i,"actual":a,"expected":b})
    if actual["derivation"] != expected["derivation"]:
        mismatches.append({"stage":"DECISION_DERIVATION", "actual":actual["derivation"],"expected":expected["derivation"]})
    source=row["compiler_input"]
    verified=common.IR.verify_program(native, source["program_source"]["initial_state"],
        source["program_source"]["submitted_events"], source["oracle_state"],source["oracle_certificate"])
    return {"case_id":row["case_id"],"origin":"OBSERVED_MODEL_OUTPUT", "internal_cause_established":False,
        "first_divergence":mismatches[0]["stage"] if mismatches else ("NATIVE_PROGRAM" if not verified["program_exact"] else None),
        "mismatches":mismatches, "native_exact":verified["program_exact"],
        "unsafe_claim":program["claim_certificate"]["decision"]=="ALLOW" and source["oracle_certificate"]["decision"]!="ALLOW"}