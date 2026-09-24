"""Original exact-program metrics plus independent structural diagnostics."""
from __future__ import annotations

import math
from collections import Counter, defaultdict

from common import IR, PROTOCOL, config, legacy_evaluate, summarize


def diagnostics(row, prediction):
    src = row["compiler_input"]
    events = src["program_source"]["submitted_events"]
    clock = src["program_source"]["initial_state"]["request"]["query_time"]
    result = {"per_event_disposition_exact": False, "identifier_coverage_exact": False,
              "claims_complete": False, "raw_claim_decision": None,
              "raw_claim_unsafe_authorization": False, "execution_error": None,
              "parse_errors": []}
    programs = []
    for parser in (IR.parse_program_a, IR.parse_program_b):
        try:
            programs.append(parser(prediction["raw_output"]))
        except (ValueError, TypeError) as error:
            result["parse_errors"].append(f"{parser.__name__}: {type(error).__name__}: {error}")
    if len(programs) != 2 or programs[0] != programs[1]:
        return result
    program = programs[0]
    result["claims_complete"] = True
    result["raw_claim_decision"] = program["claim_certificate"].get("decision")
    result["raw_claim_unsafe_authorization"] = (
        result["raw_claim_decision"] == "ALLOW" and src["oracle_certificate"]["decision"] != "ALLOW")
    source_ids = [event["event_id"] for event in events]
    ids = [step["event_id"] for step in program["steps"]]
    result["identifier_coverage_exact"] = Counter(ids) == Counter(source_ids)
    expected = {event["event_id"]: "EXECUTE" if event["time"] <= clock else "DEFER" for event in events}
    result["per_event_disposition_exact"] = result["identifier_coverage_exact"] and all(
        step["disposition"] == expected[step["event_id"]] for step in program["steps"])
    try:
        IR._execute(src["program_source"]["initial_state"], events, program,
                    IR.BASE.transition_a, IR.BASE.evaluate_a)
    except (ValueError, KeyError, TypeError) as error:
        result["execution_error"] = f"{type(error).__name__}: {error}"
    return result


def score(rows, predictions, arm, split, cfg=None):
    cfg = cfg or config()
    if len(predictions) != len(rows) or {p["case_id"] for p in predictions} != {r["case_id"] for r in rows}:
        raise ValueError("prediction cases differ from registered evaluation inputs")
    evaluations = legacy_evaluate(rows, predictions)
    result = summarize(evaluations, cfg["absolute_gate"])
    result["evaluations"] = evaluations
    byid = {p["case_id"]: p for p in predictions}
    extra = [{"case_id": row["case_id"], "semantic_family": row["semantic_family"],
              **diagnostics(row, byid[row["case_id"]])} for row in rows]
    for evaluation, diagnostic in zip(result["evaluations"], extra):
        evaluation["semantic_family"] = diagnostic["semantic_family"]
    result.update({"protocol_id": PROTOCOL, "arm": arm, "split": split,
                   "structural_diagnostics": extra, "transfer_authorized": False,
                   "binding_authority": False})
    for field in ("per_event_disposition_exact", "identifier_coverage_exact", "claims_complete"):
        result[field + "_rate"] = sum(e[field] for e in extra) / len(rows)
    result["raw_claim_unsafe_authorizations"] = sum(e["raw_claim_unsafe_authorization"] for e in extra)
    result["execution_errors"] = sum(e["execution_error"] is not None for e in extra)
    # A parsed unsafe claim must not disappear merely because execution failed.
    result["original_absolute_gate_passed"] = result["gate_passed"]
    result["gate_passed"] = result["gate_passed"] and result["raw_claim_unsafe_authorizations"] == 0
    return result


def family_comparison(control, repair, cfg=None):
    cfg = cfg or config()
    left = {r["case_id"]: r for r in control["evaluations"]}
    right = {r["case_id"]: r for r in repair["evaluations"]}
    if len(left) != len(control["evaluations"]) or len(right) != len(repair["evaluations"]) or left.keys() != right.keys():
        raise ValueError("paired comparison case mismatch")
    differences = defaultdict(int)
    for cid in left:
        if left[cid]["semantic_family"] != right[cid]["semantic_family"]:
            raise ValueError("paired family mismatch")
        differences[left[cid]["semantic_family"]] += int(right[cid]["program_exact"]) - int(left[cid]["program_exact"])
    wins = sum(v > 0 for v in differences.values())
    losses = sum(v < 0 for v in differences.values())
    n = wins + losses
    p = sum(math.comb(n, k) for k in range(wins, n + 1)) / 2**n if n else 1.0
    gates = cfg["repair_gate"]
    delta = lambda field: repair[field] - control[field]
    checks = {
        "repair_absolute_gate": repair["gate_passed"],
        "program_exact_improvement": delta("program_exact_rate") >= gates["program_exact_delta_floor"],
        "family_paired_significance": p <= gates["family_sign_test_p_ceiling"],
        "event_order_not_degraded": delta("event_order_exact_rate") >= 0,
        "decision_noninferiority": delta("decision_accuracy") >= gates["decision_delta_floor"],
        "state_noninferiority": delta("executed_state_exact_rate") >= gates["executed_state_delta_floor"],
        "unsafe_not_increased": all(delta(field) <= gates["unsafe_authorization_delta_ceiling"] for field in
            ("unsafe_authorizations", "verified_unsafe_authorizations", "raw_claim_unsafe_authorizations")),
    }
    return {"passed": all(checks.values()), "checks": checks,
            "program_exact_delta": delta("program_exact_rate"),
            "event_order_delta": delta("event_order_exact_rate"),
            "decision_delta": delta("decision_accuracy"),
            "executed_state_delta": delta("executed_state_exact_rate"),
            "family_differences": dict(differences), "family_wins": wins, "family_losses": losses,
            "family_ties": len(differences) - n, "one_sided_family_sign_p": p,
            "inference_unit": "synthetic semantic family; ties excluded",
            "claim_boundary": "Single-seed synthetic matched-training comparison; no transfer or production claim."}