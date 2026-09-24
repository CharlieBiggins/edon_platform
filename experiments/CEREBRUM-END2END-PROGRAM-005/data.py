"""Fresh ActionNet contrasts; no model outputs are used as supervision."""
from collections import Counter
from copy import deepcopy
import random
import re

from core import (ROOT, PARENT, cfg, dependencies, object_hash, canonical,
                  write_rows, write_json, read, freeze, digest)

RULES = (
    "EVIDENCE_RECEIPT_CLOCK", "APPEAL_RESOLUTION_CLOCK", "POLICY_EVENT_EFFECT",
    "REVOCATION_PRIORITY", "APPROVAL_RESTORATION_CLOCK", "EVIDENCE_AVAILABILITY_PREDICATE",
)
EXCLUDED = set()
ACQUISITION_AUDITS = []


def fingerprint(row):
    """Conservative alpha-normalized source identity, not a novelty proof."""
    source = deepcopy(row["compiler_input"]["program_source"])
    source["submitted_events"].sort(key=lambda e: (e["time"], e["priority"], e["sequence"], e["event_id"]))
    text = canonical(source)
    mapping = {}
    def rename(match):
        key = match.group(0)
        if key not in mapping:
            mapping[key] = "opaque" + str(len(mapping))
        return mapping[key]
    return object_hash(re.sub(r"[A-Za-z][A-Za-z0-9_-]*-[0-9a-f]{16}", rename, text))


def qualify_row(row, deps):
    common, trace, _, _, _ = deps
    src = row["compiler_input"]
    events = src["program_source"]["submitted_events"]
    state = src["program_source"]["initial_state"]
    if len({e["event_id"] for e in events}) != len(events):
        raise ValueError("duplicate source event")
    actors = {a["actor_id"] for a in state["actors"].values()}
    for e in events:
        if e["actor_id"] not in actors or any(type(e[k]) is not int for k in ("time", "priority", "sequence")):
            raise ValueError("invalid event reference/ordering operand")
    result = common.IR.verify_program(row["completion"], state, events,
                                      src["oracle_state"], src["oracle_certificate"])
    if not result["program_exact"] or not result["accepted_by_verifier"]:
        raise ValueError("native target fails executable qualification")
    expected = trace.build_trace(src["program_source"])
    if row["trace_completion"] != trace.render_trace(expected):
        raise ValueError("trace target differs from executable oracle")
    reversed_source = {"initial_state": state, "submitted_events": list(reversed(events))}
    if trace.build_trace(reversed_source) != expected:
        raise ValueError("source serialization changed semantics")
    # Rebuild the exact original renderer; no diagnosis or teacher state enters the prompt.
    _, _, _, _, gen = deps
    media, content = gen.render_familiar_augmented({**src["program_source"], "domain": row["domain"]})
    from prepare_data import SYSTEM_PROMPT
    query = ("Emit one ACTIONNET_TEMPORAL_PROGRAM_V1. List every event exactly once in canonical order, mark "
             "each EXECUTE or DEFER at the disposition boundary, then claim the resulting state and certificate.")
    prompt = f"SYSTEM\n{SYSTEM_PROMPT}\n\nINSTITUTIONAL OBSERVATION\nMEDIA_TYPE={media}\n{content}\n\nTASK\n{query}\n\nOUTPUT\n"
    if prompt != row["prompt"]:
        raise ValueError("prompt is not the registered plain-text rendering")
    return expected


def ordinary(split, start, families, seed, deps):
    common, trace, _, _, gen = deps
    records, trajectories, _, _, _ = gen.make_split(
        split, seed, tuple(range(start, start + 4 * families)),
        tuple(f"curriculum005-{split}-domain-{i}" for i in range(8)), gen.renderer_lineage())
    invalid_pairs = {t["counterfactual_pair_id"] for t in trajectories
        if any(e["actor_id"] not in {a["actor_id"] for a in t["initial_state"]["actors"].values()}
               for e in t["submitted_events"])}
    selected, seen = [], set()
    for i in range(0,len(records),2):
        pair = list(zip(records[i:i+2],trajectories[i:i+2]))
        if any(t["counterfactual_pair_id"] in invalid_pairs for _,t in pair):
            continue
        fs = {fingerprint(common.prepare_row(r)) for r,_ in pair}
        if fs & (seen | EXCLUDED):
            continue
        selected.extend(pair); seen |= fs
        if len(selected) == families * 8: break
    if len(selected) != families * 8:
        raise ValueError("insufficient reference-closed ordinary pairs")
    ACQUISITION_AUDITS.append({"split":split,"start":start,"pool_families":4*families,
        "invalid_actor_reference_pairs":len(invalid_pairs),"selected_records":len(selected),
        "selection":"First complete reference-closed, structurally distinct pairs in deterministic pool order"})
    result = []
    for record, trajectory in selected:
        row = common.prepare_row(record)
        row.update(domain=trajectory["domain"], stratum="ordinary", contrast_rule=None)
        row["trace_completion"] = trace.render_trace(trace.build_trace(row["compiler_input"]["program_source"]))
        qualify_row(row, deps)
        result.append(row)
    return result, [t for _,t in selected]


def boundary_pair(template, family, index, split, seed, deps):
    common, trace, _, _, gen = deps
    rule = RULES[index]
    rng = random.Random(seed + family * 101 + index)
    q = rng.randrange(5, 25)
    t = deepcopy(template)
    base = t["initial_state"]
    # Same schema and mechanism engines; normalize nuisance blockers for an interpretable contrast.
    base["request"].update(query_time=q, well_formed=True)
    base["authority"].update(active=True, revoked=False, scope_match=True, valid_from=1, valid_to=30)
    base["actors"]["requester"]["rank"] = base["authority"]["required_rank"] + 1
    base["evidence"].update(status="TRUE", received_at=2, valid_until=30)
    base["workflow"].update(approvals=list(base["workflow"]["required_approvals"]), appeal_open=False, appeal_resolved=True)
    base["resources"].update(capacity=12 + family % 7, reserved=1, demand=3 + index % 3)
    base["routing"].update(accepted=True, jurisdiction_match=True)
    base["policy"].update(allows=True, version=base["request"]["required_policy_version"], effective_at=1)
    base["conflict"] = False
    pair = gen.BASE.opaque("pair", cfg()["protocol_id"], split, family, rule)
    # A single primitive difference per pair. Event identity is held fixed across variants.
    events = []
    def event(operation, target, value, time, priority=20):
        e = gen.BASE.make_event(pair, len(events), operation, target, value, time=time,
                               priority=priority, actor_id=base["actors"]["requester"]["actor_id"])
        events.append(e)
        return len(events) - 1
    event("NOOP", "policy.allows", True, q - 4)
    event("ADJUST_RESOURCE_RESERVATION", "resources.reserved", 1, q - 3, 30)
    event("NOOP", "policy.allows", True, q + 2, 5)
    mechanism = rule
    if rule == "EVIDENCE_RECEIPT_CLOCK":
        mechanism = "DELAYED_EVIDENCE"
        base["evidence"]["status"] = "MISSING"
        focus = event("SET_EVIDENCE_STATUS", "evidence.status", "TRUE", q)
        path, left, right = ("event", focus, "time"), q, q + 1
    elif rule == "APPEAL_RESOLUTION_CLOCK":
        mechanism = "UNRESOLVED_APPEAL"
        event("OPEN_APPEAL", "workflow.appeal_open", True, q - 2)
        focus = event("RESOLVE_APPEAL", "workflow.appeal_resolved", True, q)
        path, left, right = ("event", focus, "time"), q, q + 1
    elif rule == "POLICY_EVENT_EFFECT":
        mechanism = "POLICY_CHANGE"
        focus = event("SET_POLICY_ALLOWED", "policy.allows", True, q)
        path, left, right = ("event", focus, "value"), True, False
    elif rule == "REVOCATION_PRIORITY":
        mechanism = "PRIORITY_RACE"
        event("SET_DELEGATION_REVOKED", "authority.revoked", True, q - 1, 20)
        focus = event("SET_DELEGATION_REVOKED", "authority.revoked", False, q - 1, 10)
        path, left, right = ("event", focus, "priority"), 10, 30
    elif rule == "APPROVAL_RESTORATION_CLOCK":
        mechanism = "APPROVAL_WITHDRAWAL"
        approval = base["workflow"]["required_approvals"][0]
        event("REMOVE_APPROVAL", "workflow.approvals", approval, q - 2)
        focus = event("ADD_APPROVAL", "workflow.approvals", approval, q)
        path, left, right = ("event", focus, "time"), q, q + 1
    elif rule == "EVIDENCE_AVAILABILITY_PREDICATE":
        mechanism = "DELAYED_EVIDENCE"
        path, left, right = ("state", "evidence", "received_at"), q, q + 1
    else:
        raise ValueError("unknown repair rule")
    # Alternate nuisance order by family; the invariant pair reverses this same list.
    order = list(range(len(events))); rng.shuffle(order)
    result = []
    for variant, value in enumerate((left, right)):
        trajectory = deepcopy(t)
        trajectory.update(semantic_family=family, counterfactual_pair_id=pair,
            trajectory_id=gen.BASE.opaque("trajectory", cfg()["protocol_id"], split, family, rule, variant),
            pair_mechanism=mechanism, intervention_family=rule, variant=("BASE" if variant == 0 else "INTERVENTION"),
            pair_class="PIVOTAL")
        trajectory["submitted_events"] = deepcopy(events)
        if path[0] == "event": trajectory["submitted_events"][path[1]][path[2]] = value
        elif path[0] == "state": trajectory["initial_state"][path[1]][path[2]] = value
        trajectory["submitted_events"] = [trajectory["submitted_events"][i] for i in order]
        if path[0] == "presentation" and value:
            trajectory["submitted_events"].reverse()
        state_a = deepcopy(trajectory["initial_state"]); state_b = deepcopy(state_a)
        for e in gen.BASE.schedule_a(trajectory["submitted_events"]):
            if e["time"] <= q:
                state_a = gen.BASE.transition_a(state_a, e)
                state_b = gen.BASE.transition_b(state_b, e)
        if state_a != state_b or gen.BASE.evaluate_a(state_a) != gen.BASE.evaluate_b(state_b):
            raise ValueError("boundary oracle disagreement")
        trajectory.update(final_state=state_a, outcome=gen.BASE.evaluate_a(state_a))
        row = common.prepare_row(gen.make_record(trajectory, split, gen.renderer_lineage()))
        row.update(domain=trajectory["domain"], stratum="boundary", contrast_rule=rule,
                   contrast_operand=list(path), contrast_value=value)
        row["trace_completion"] = trace.render_trace(trace.build_trace(row["compiler_input"]["program_source"]))
        qualify_row(row, deps)
        result.append(row)
    a,b = result
    changed = a["compiler_input"]["oracle_certificate"]["decision"] != b["compiler_input"]["oracle_certificate"]["decision"]
    if not changed:
        raise ValueError("boundary decision relation is not registered")
    if sum(r["compiler_input"]["oracle_certificate"]["decision"] == "ALLOW" for r in result) != 1:
        raise ValueError("repair pair must contain exactly one ALLOW and one non-ALLOW")
    return result


def boundaries(split, start, families, seed, deps):
    _, templates = ordinary(split + "-templates", start, families, seed, deps)
    result = []; seen = set(EXCLUDED)
    for offset in range(families):
        for index in range(len(RULES)):
            for attempt in range(64):
                pair=boundary_pair(templates[offset * 8], start + offset, index, split, seed + 1009*attempt, deps)
                fs={fingerprint(r) for r in pair}
                if not (fs & seen):
                    seen |= fs;result.extend(pair);break
            else:raise ValueError("boundary uniqueness budget exhausted")
    return result


def generate(split, deps):
    if split not in ("train", "development"):
        raise ValueError("Program-005 cannot generate confirmation")
    spec = cfg()[split]
    broad,_ = ordinary(split, spec["ordinary_start"], spec["ordinary_families"], spec["seed"], deps)
    targeted = boundaries(split, spec["boundary_start"], spec["boundary_families"], spec["seed"] + 1, deps)
    if split == "train":
        # Exactly the same broad rehearsal cases appear in both arms. Unique source count differs.
        control = broad
        treatment = broad[:cfg()["rehearsal_records"]] + targeted
        return {"train-ordinary": control, "train-repair": treatment}
    return {split: broad + targeted}


def validate_splits(splits, exclusions=()):
    seen = {}
    excluded = {fingerprint(r) for r in exclusions}
    report = {}
    for name, values in splits.items():
        if len(values) != (cfg()["training_records"] if name.startswith("train-") else cfg()[name]["records"]):
            raise ValueError("split record budget differs")
        if len({r["case_id"] for r in values}) != len(values):
            raise ValueError("duplicate case")
        groups = Counter(r["counterfactual_pair_id"] for r in values)
        if set(groups.values()) != {2}:
            raise ValueError("contrast pair split or duplicated")
        local = {}
        for r in values:
            f = fingerprint(r)
            if f in excluded:
                raise ValueError("predecessor structural overlap")
            if f in local and local[f] != r["counterfactual_pair_id"]:
                raise ValueError("structural duplicate across pairs")
            local[f] = r["counterfactual_pair_id"]
            for key in (("case", r["case_id"]), ("pair", r["counterfactual_pair_id"]),
                        ("family", r["semantic_family"]), ("semantic", f),
                        ("prompt", object_hash(r["prompt"]))):
                previous = seen.get(key)
                if previous and previous != name and not (previous.startswith("train-") and name.startswith("train-")):
                    raise ValueError("cross-split contamination: " + str(key[0]))
                seen[key] = name
        report[name] = {"records":len(values), "pairs":len(groups),
            "mechanisms":dict(Counter(r["pair_mechanism"] for r in values)),
            "rules":dict(Counter(r["contrast_rule"] or "ORDINARY" for r in values)),
            "decision_counts":dict(Counter(r["compiler_input"]["oracle_certificate"]["decision"] for r in values))}
        if set(report[name]["decision_counts"]) != {"ALLOW", "DENY", "ABSTAIN", "CONTESTED", "INVALID"}:
            raise ValueError("missing decision class: " + name)
        targets = [r for r in values if r["stratum"] == "boundary"]
        if targets:
            expected = cfg()["train" if name.startswith("train-") else name]["boundary_families"] * 2
            if Counter(r["contrast_rule"] for r in targets) != Counter({rule: expected for rule in RULES}):
                raise ValueError("targeted rule imbalance")
    shared = splits["train-ordinary"][:cfg()["rehearsal_records"]]
    if splits["train-repair"][:len(shared)] != shared:
        raise ValueError("shared rehearsal differs between arms")
    return report


def prepare(audit_dir):
    if (ROOT / "registration.json").exists() or (ROOT / "results").exists() or (ROOT / "prepared").exists():
        raise ValueError("prepare requires an untouched Program-005 workspace; never overwrite or re-freeze")
    from audit import audit, predecessor_exposures
    evidence = audit(audit_dir)
    ACQUISITION_AUDITS.clear()
    deps = dependencies()
    # Reconstruct only the parent TRAIN and DEVELOPMENT, never its sealed confirmation.
    import importlib.util
    spec = importlib.util.spec_from_file_location("parent003_prepare", PARENT / "prepare.py")
    parent_prepare = importlib.util.module_from_spec(spec); spec.loader.exec_module(parent_prepare)
    old = []
    for split in ("train", "development"):
        values,_ = parent_prepare.generate_split(split, read(PARENT / "config.json"))
        payload = "".join(canonical(v) + "\n" for v in values).encode()
        if digest(payload) != read(PARENT / "registration.json")[split + "_sha256"]:
            raise ValueError("parent exposure reconstruction mismatch")
        old.extend(values)
    old.extend(predecessor_exposures())
    deps = dependencies()  # Reset generator namespace after predecessor reconstruction.
    EXCLUDED.clear(); EXCLUDED.update(fingerprint(r) for r in old)
    splits = generate("train", deps)
    EXCLUDED.update(fingerprint(r) for values in splits.values() for r in values)
    splits.update(generate("development", deps))
    report = validate_splits(splits, old)
    # Qualification occurs before publishing any data or registration.
    for values in splits.values():
        for row in values:
            qualify_row(row, deps)
    for name, values in splits.items():
        write_rows(ROOT / "prepared" / (name + ".jsonl"), values)
    write_json(ROOT / "prepared/exclusions.json", sorted({fingerprint(r) for r in old}))
    write_json(ROOT / "prepared/program004-audit.json", evidence)
    write_json(ROOT / "prepared/qualification.json", {"passed":True, "splits":report,
        "acquisition_audits":ACQUISITION_AUDITS,
        "predecessor_exposure_records_excluded":len(old), "confirmation_accessed":False,
        "claim_boundary":"Inherited synthetic semantics; no independent-generator or learned result."})
    freeze()
    return report