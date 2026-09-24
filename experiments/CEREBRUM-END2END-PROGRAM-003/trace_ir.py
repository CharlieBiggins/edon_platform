"""Deterministic execution traces; never called to repair inference outputs."""
from copy import deepcopy
import json

from common import IR, canonical

HEADER = "ACTIONNET_EXECUTION_TRACE_V1"
END = "END_ACTIONNET_EXECUTION_TRACE"


def changes(before, after, path=""):
    if isinstance(before, dict) and isinstance(after, dict):
        if before.keys() != after.keys():
            raise ValueError("state schema changed")
        return [change for key in sorted(before) for change in
                changes(before[key], after[key], f"{path}.{key}" if path else key)]
    return [] if canonical(before) == canonical(after) else [[path, before, after]]


def derivation(state):
    """Explicit ordered predicates, checked against both inherited evaluators."""
    q = state["request"]["query_time"]
    a, e, w, r, p, route = (state[k] for k in
                            ("authority", "evidence", "workflow", "resources", "policy", "routing"))
    checks = [
        ["MALFORMED_REQUEST", not state["request"]["well_formed"]],
        ["UNRESOLVED_CONTEST", bool(state["conflict"] or (w["appeal_open"] and not w["appeal_resolved"]))],
        ["AUTHORITY", bool(not a["active"] or a["revoked"] or not a["scope_match"]
            or state["actors"]["requester"]["rank"] < a["required_rank"]
            or not a["valid_from"] <= q <= a["valid_to"])],
        ["ROUTING_OR_JURISDICTION", bool(route["required"] and
            (not route["accepted"] or not route["jurisdiction_match"]))],
        ["POLICY", bool(not p["allows"] or p["version"] != state["request"]["required_policy_version"]
            or q < p["effective_at"])],
        ["EVIDENCE_FALSE_OR_EXPIRED", bool(e["status"] == "FALSE" or
            (e["valid_until"] is not None and e["valid_until"] < q))],
        ["EVIDENCE_UNAVAILABLE", bool(e["status"] in ("UNKNOWN", "MISSING")
            or e["received_at"] is None or e["received_at"] > q)],
        ["WORKFLOW_APPROVAL", not set(w["required_approvals"]).issubset(w["approvals"])],
        ["RESOURCE_CAPACITY", r["demand"] > r["capacity"] - r["reserved"]],
    ]
    first = next((name for name, blocked in checks if blocked), None)
    if first == "MALFORMED_REQUEST":
        decision, semantic = "INVALID", "INVALID"
    elif first == "UNRESOLVED_CONTEST":
        decision, semantic = "CONTESTED", "CONTESTED"
    elif first in ("AUTHORITY", "ROUTING_OR_JURISDICTION", "POLICY", "EVIDENCE_FALSE_OR_EXPIRED"):
        decision, semantic = "DENY", "FALSE"
    elif first is not None:
        decision = "ABSTAIN"
        semantic = e["status"] if first == "EVIDENCE_UNAVAILABLE" and e["status"] in ("UNKNOWN", "MISSING") else "UNKNOWN"
    else:
        decision, semantic = "ALLOW", "TRUE"
    cert_a, cert_b = IR.BASE.evaluate_a(state), IR.BASE.evaluate_b(state)
    if canonical(cert_a) != canonical(cert_b):
        raise ValueError("certificate engines disagree")
    if (decision, semantic, [] if first is None else [first]) != (
            cert_a["decision"], cert_a["semantic_state"], cert_a["failed_conditions"]):
        raise ValueError("explicit predicates disagree with evaluators")
    return {"blocked_checks": checks, "first_failure": first,
            "decision": decision, "semantic_state": semantic}


def build_trace(source):
    """Oracle construction/scoring ONLY, using public source events and initial state."""
    ordered_a = IR.BASE.schedule_a(source["submitted_events"])
    ordered_b = IR.BASE.schedule_b(source["submitted_events"])
    if canonical(ordered_a) != canonical(ordered_b):
        raise ValueError("schedulers disagree")
    left = deepcopy(source["initial_state"])
    right = deepcopy(left)
    q = left["request"]["query_time"]
    records = []
    for event in ordered_a:
        before = IR.BASE.public_state(left)
        execute = event["time"] <= q
        if execute:
            left = IR.BASE.transition_a(left, deepcopy(event))
            right = IR.BASE.transition_b(right, deepcopy(event))
        after = IR.BASE.public_state(left)
        if canonical(after) != canonical(IR.BASE.public_state(right)):
            raise ValueError("transition engines disagree at event")
        records.append({"event_id": event["event_id"],
            "key": [event["time"], event["priority"], event["sequence"], event["event_id"]],
            "query_time": q, "disposition": "EXECUTE" if execute else "DEFER",
            "changes": changes(before, after)})
    return {"records": records, "derivation": derivation(left)}


def render_trace(trace):
    return "\n".join([HEADER] + ["TRACE " + canonical(r) for r in trace["records"]]
        + ["DERIVE " + canonical(trace["derivation"]), END])


def unique_object(pairs):
    result = {}
    for k, v in pairs:
        if k in result:
            raise ValueError("duplicate JSON key")
        result[k] = v
    return result


def strict_json(text):
    def reject(value):
        raise ValueError(f"non-finite JSON value: {value}")
    return json.loads(text, object_pairs_hook=unique_object, parse_constant=reject)


def split_output(text, arm):
    """Extract a final program without sorting, repairing, or substituting its content."""
    text = text.strip()
    if arm == "uniform":
        return None, text
    if arm != "trace":
        raise ValueError("unregistered arm")
    lines = text.splitlines()
    if not lines or lines[0] != HEADER or lines.count(END) != 1:
        raise ValueError("trace boundary invalid")
    end = lines.index(END)
    if end < 2 or not lines[end - 1].startswith("DERIVE "):
        raise ValueError("trace derivation missing")
    if any(not line.startswith("TRACE ") for line in lines[1:end - 1]):
        raise ValueError("invalid trace statement")
    trace = {"records": [strict_json(line[6:]) for line in lines[1:end - 1]],
             "derivation": strict_json(lines[end - 1][7:])}
    if not isinstance(trace["derivation"], dict) or any(not isinstance(r, dict) for r in trace["records"]):
        raise ValueError("trace record type invalid")
    final = "\n".join(lines[end + 1:])
    if not final.startswith(IR.PROGRAM_HEADER + "\n"):
        raise ValueError("final native program missing")
    return trace, final


def prompt_for(prompt, arm):
    # Input facts are identical. Only the registered response-format instruction differs.
    if arm == "uniform":
        return prompt + "\nResponse format: output only the native temporal program, then stop.\n"
    if arm != "trace":
        raise ValueError("unregistered arm")
    return prompt + (
        "\nResponse format: first output ACTIONNET_EXECUTION_TRACE_V1. For every event in canonical "
        "(time,priority,sequence,event_id) order output TRACE followed by compact JSON with event_id, "
        "key:[time,priority,sequence,event_id], query_time, disposition, changes. "
        "EXECUTE iff time <= query_time; otherwise DEFER with changes:[]. Changes are sorted "
        "[dot_path,before,after] records for changed public-state leaves (arrays are whole leaves). "
        "Then output DERIVE followed by JSON with blocked_checks (ordered [condition,boolean] pairs "
        "for MALFORMED_REQUEST,UNRESOLVED_CONTEST,AUTHORITY,ROUTING_OR_JURISDICTION,POLICY,"
        "EVIDENCE_FALSE_OR_EXPIRED,EVIDENCE_UNAVAILABLE,WORKFLOW_APPROVAL,RESOURCE_CAPACITY), "
        "first_failure (first true condition or null), decision, semantic_state. "
        "Then END_ACTIONNET_EXECUTION_TRACE, then the complete native temporal program with "
        "claims matching the resulting state and derived certificate. No prose or code fences.\n")


def completion_for(row, arm):
    if arm == "uniform":
        return row["completion"]
    if arm != "trace":
        raise ValueError("unregistered arm")
    return row["trace_completion"] + "\n" + row["completion"]