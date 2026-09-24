"""Fresh shared-scenario construction and arm-specific supervision serialization."""
from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import importlib
import importlib.util
from pathlib import Path
import sys

from foundation import (DECISIONS, ID, PROGRAM005_REGISTRATION, RULES, canonical,
                        digest, object_hash, pinned_payload, require)

ROOT = Path(__file__).resolve().parent
EXPERIMENTS = ROOT.parent
PROGRAM005 = EXPERIMENTS / "CEREBRUM-END2END-PROGRAM-005"


def opaque(kind, *parts):
    payload = "\x1f".join((ID, kind, *(str(value) for value in parts))).encode()
    return kind + "-" + hashlib.sha256(payload).hexdigest()[:24]


def changes(before, after, path=""):
    """Canonical leaf changes; arrays are treated as whole leaves."""
    if isinstance(before, dict) and isinstance(after, dict):
        require(before.keys() == after.keys(), "Pair schema changed")
        result = []
        for key in sorted(before):
            child = key if not path else path + "." + key
            result.extend(changes(before[key], after[key], child))
        return result
    return [] if canonical(before) == canonical(after) else [[path, before, after]]


def native_prompt(row):
    return row["prompt"] + "\nResponse format: output only the native temporal program, then stop.\n"


def trace_prompt(row):
    return row["prompt"] + (
        "\nAuxiliary supervision task: output only ACTIONNET_EXECUTION_TRACE_V1 through "
        "END_ACTIONNET_EXECUTION_TRACE. List every event in canonical "
        "(time,priority,sequence,event_id) order, assign EXECUTE iff time <= query_time, "
        "record exact public-state changes, and derive the first blocking condition, decision, "
        "and semantic state. Do not output the native program in this auxiliary task.\n")


def relation_record(left, right):
    source_left = left["compiler_input"]["program_source"]
    source_right = right["compiler_input"]["program_source"]
    cert_left = left["compiler_input"]["oracle_certificate"]
    cert_right = right["compiler_input"]["oracle_certificate"]
    state_left = left["compiler_input"]["oracle_state"]
    state_right = right["compiler_input"]["oracle_state"]
    relation = {
        "schema": "ACTIONNET_PAIR_RELATION_V1",
        "pair_id": left["counterfactual_pair_id"],
        "input_changes": changes(source_left, source_right),
        "resulting_state_changes": changes(state_left, state_right),
        "left_decision": cert_left["decision"],
        "right_decision": cert_right["decision"],
        "decision_changed": cert_left["decision"] != cert_right["decision"],
        "left_semantic_state": cert_left["semantic_state"],
        "right_semantic_state": cert_right["semantic_state"],
        "first_failure_changed": cert_left.get("failed_conditions") != cert_right.get("failed_conditions"),
    }
    prompt = (
        "SYSTEM\nDerive the explicit causal relationship between two registered institutional "
        "scenarios. Do not invent facts.\n\nMEMBER_A_SOURCE\n" + canonical(source_left)
        + "\n\nMEMBER_B_SOURCE\n" + canonical(source_right)
        + "\n\nTASK\nOutput one compact ACTIONNET_PAIR_RELATION_V1 JSON object containing pair_id, "
        "input_changes, resulting_state_changes, left_decision, right_decision, decision_changed, "
        "left_semantic_state, right_semantic_state, and first_failure_changed.\n\nOUTPUT\n"
    )
    return prompt, "ACTIONNET_PAIR_RELATION_V1\n" + canonical(relation)


def rename_rows(values, split):
    pair_map = {}
    result = []
    for row in values:
        source_pair = row["counterfactual_pair_id"]
        pair_map.setdefault(source_pair, opaque("pair", split, source_pair))
        value = deepcopy(row)
        value["source_case_id"] = row["case_id"]
        value["source_counterfactual_pair_id"] = source_pair
        value["case_id"] = opaque("case", split, row["case_id"])
        value["counterfactual_pair_id"] = pair_map[source_pair]
        value["matched_protocol_id"] = ID
        result.append(value)
    return result


def serialize_training(scenarios):
    grouped = defaultdict(list)
    for row in scenarios:
        grouped[row["counterfactual_pair_id"]].append(row)
    require(set(len(values) for values in grouped.values()) == {2}, "Training pair split")
    ordinary, actionnet = [], []
    for pair_id in sorted(grouped):
        pair = sorted(grouped[pair_id], key=lambda value: value["case_id"])
        for row in pair:
            native = {"example_id": "native-" + row["case_id"], "group_id": pair_id,
                "target_kind": "native_program", "underlying_case_ids": [row["case_id"]],
                "prompt": native_prompt(row), "target": row["completion"]}
            ordinary.append(native)
            actionnet.append(deepcopy(native))
            actionnet.append({"example_id": "trace-" + row["case_id"], "group_id": pair_id,
                "target_kind": "execution_trace", "underlying_case_ids": [row["case_id"]],
                "prompt": trace_prompt(row), "target": row["trace_completion"]})
        prompt, target = relation_record(*pair)
        actionnet.append({"example_id": "relation-" + pair_id, "group_id": pair_id,
            "target_kind": "pair_relation", "underlying_case_ids": [row["case_id"] for row in pair],
            "prompt": prompt, "target": target})
    validate_serialization(scenarios, ordinary, actionnet)
    return ordinary, actionnet


def validate_serialization(scenarios, ordinary, actionnet):
    case_ids = {row["case_id"] for row in scenarios}
    pair_ids = {row["counterfactual_pair_id"] for row in scenarios}
    require(len(scenarios) == 384 and len(case_ids) == 384 and len(pair_ids) == 192,
            "Shared training scenario inventory differs")
    require(len(ordinary) == 384 and len(actionnet) == 960, "Training example inventory differs")
    ordinary_native = {row["example_id"]: row for row in ordinary}
    action_native = {row["example_id"]: row for row in actionnet if row["target_kind"] == "native_program"}
    require(ordinary_native == action_native, "Native supervision differs between arms")
    require({case for row in ordinary for case in row["underlying_case_ids"]} == case_ids,
            "Ordinary underlying scenario coverage differs")
    require({case for row in actionnet for case in row["underlying_case_ids"]} == case_ids,
            "ActionNet introduced an exclusive scenario")
    require(Counter(row["target_kind"] for row in actionnet) == {
        "native_program": 384, "execution_trace": 384, "pair_relation": 192},
        "ActionNet auxiliary mixture differs")
    for values in (ordinary, actionnet):
        ids = [row["example_id"] for row in values]
        require(len(ids) == len(set(ids)), "Duplicate training example ID")
        require(all(row["group_id"] in pair_ids and row["prompt"] and row["target"] for row in values),
                "Invalid training example")


def validate_scenarios(train, screen, fingerprint):
    require((len(train), len(screen)) == (384, 24), "Scenario counts differ")
    for name, values, expected_pairs in (("train", train, 192), ("screen", screen, 12)):
        ids = [row["case_id"] for row in values]
        pairs = Counter(row["counterfactual_pair_id"] for row in values)
        require(len(ids) == len(set(ids)) and len(pairs) == expected_pairs
                and set(pairs.values()) == {2}, name + " pair/case inventory differs")
        require(set(row["compiler_input"]["oracle_certificate"]["decision"] for row in values) == DECISIONS,
                name + " decision coverage differs")
    require(not ({row["case_id"] for row in train} & {row["case_id"] for row in screen}), "Case overlap")
    require(not ({row["counterfactual_pair_id"] for row in train}
                 & {row["counterfactual_pair_id"] for row in screen}), "Pair overlap")
    require(not ({fingerprint(row) for row in train} & {fingerprint(row) for row in screen}),
            "Structural train/screen overlap")
    targeted = [row for row in screen if row["stratum"] == "boundary"]
    require(Counter(row["contrast_rule"] for row in targeted) == {rule: 2 for rule in RULES},
            "Screen targeted-rule coverage differs")


def first_complete_pairs(values, records):
    require(records % 2 == 0, "Pair selection requires an even record count")
    grouped = defaultdict(list)
    order = []
    for value in values:
        pair = value["counterfactual_pair_id"]
        if pair not in grouped:
            order.append(pair)
        grouped[pair].append(value)
    selected = []
    for pair in order[:records // 2]:
        require(len(grouped[pair]) == 2, "Source pair is incomplete")
        selected.extend(grouped[pair])
    require(len(selected) == records, "Insufficient complete pairs")
    return selected


def _load_program005():
    require("core" not in sys.modules and "data" not in sys.modules,
            "Inherited generic modules already loaded; use a fresh process")
    sys.path.insert(0, str(PROGRAM005))
    core = importlib.import_module("core")
    data = importlib.import_module("data")
    audit = importlib.import_module("audit")
    pinned_payload(PROGRAM005 / "registration.json", PROGRAM005_REGISTRATION)
    return core, data, audit


def _reconstruct_exposures(core, data, audit):
    deps = core.dependencies()
    spec = importlib.util.spec_from_file_location("matched_parent003_prepare", core.PARENT / "prepare.py")
    parent_prepare = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(parent_prepare)
    old = []
    for split in ("train", "development"):
        values, _ = parent_prepare.generate_split(split, core.read(core.PARENT / "config.json"))
        payload = "".join(core.canonical(value) + "\n" for value in values).encode()
        require(core.digest(payload) == core.read(core.PARENT / "registration.json")[split + "_sha256"],
                "Program-003 reconstruction differs")
        old.extend(values)
    old.extend(audit.predecessor_exposures())
    deps = core.dependencies()
    data.EXCLUDED.clear()
    data.EXCLUDED.update(data.fingerprint(value) for value in old)
    data.ACQUISITION_AUDITS.clear()
    program005 = data.generate("train", deps)
    data.EXCLUDED.update(data.fingerprint(value) for values in program005.values() for value in values)
    program005.update(data.generate("development", deps))
    qualification = core.read(PROGRAM005 / "prepared/qualification.json")
    require(data.validate_splits(program005, old) == qualification["splits"],
            "Program-005 reconstruction qualification differs")
    require(data.ACQUISITION_AUDITS == qualification["acquisition_audits"],
            "Program-005 reconstruction acquisition audit differs")
    registration = core.read(PROGRAM005 / "registration.json")
    for name, values in program005.items():
        payload = "".join(core.canonical(value) + "\n" for value in values).encode()
        require(core.digest(payload) == registration["data"]["prepared/" + name + ".jsonl"],
                "Program-005 reconstructed data hash differs: " + name)
    return old + [value for values in program005.values() for value in values], deps


def generate_bundle(config):
    """Generate fresh data after reconstructing every registered predecessor exposure."""
    core, data, audit = _load_program005()
    historical, deps = _reconstruct_exposures(core, data, audit)
    excluded = {data.fingerprint(value) for value in historical}
    data.EXCLUDED.clear()
    data.EXCLUDED.update(excluded)
    data.ACQUISITION_AUDITS.clear()
    generation = config["generation"]
    broad, _ = data.ordinary("matched001-train", generation["train_ordinary_start"],
                             generation["train_ordinary_families"], generation["train_seed"], deps)
    data.EXCLUDED.update(data.fingerprint(value) for value in broad)
    targeted = data.boundaries("matched001-train", generation["train_targeted_start"],
                               generation["train_targeted_families"], generation["train_seed"] + 1, deps)
    train_source = broad + targeted
    data.EXCLUDED.update(data.fingerprint(value) for value in targeted)
    # Materialize the rarer boundary templates before consuming additional
    # reference-closed ordinary pairs. This order is part of the frozen data
    # construction and avoids an exclusion-order artifact at the 24-case size.
    screen_targeted = data.boundaries("matched001-screen", generation["screen_targeted_start"],
                                      generation["screen_targeted_families"],
                                      generation["screen_targeted_seed"], deps)
    data.EXCLUDED.update(data.fingerprint(value) for value in screen_targeted)
    screen_broad_pool, _ = data.ordinary("matched001-screen", generation["screen_ordinary_start"],
                                    generation["screen_ordinary_families"], generation["screen_seed"], deps)
    screen_broad = first_complete_pairs(screen_broad_pool, config["screen_ordinary_records"])
    data.EXCLUDED.update(data.fingerprint(value) for value in screen_broad)
    screen_source = screen_broad + screen_targeted
    for value in train_source + screen_source:
        data.qualify_row(value, deps)
        require(data.fingerprint(value) not in excluded, "Historical exposure overlap")
    train = rename_rows(train_source, "train")
    screen = rename_rows(screen_source, "screen")
    validate_scenarios(train, screen, data.fingerprint)
    ordinary, actionnet = serialize_training(train)
    report = {
        "protocol_id": ID, "passed": True,
        "historical_exposure_records_reconstructed": len(historical),
        "historical_exclusion_fingerprints": len(excluded),
        "training_scenarios": len(train), "training_pairs": len(train) // 2,
        "screen_scenarios": len(screen), "screen_pairs": len(screen) // 2,
        "ordinary_examples": len(ordinary), "actionnet_examples": len(actionnet),
        "actionnet_task_counts": dict(Counter(value["target_kind"] for value in actionnet)),
        "training_decisions": dict(Counter(value["compiler_input"]["oracle_certificate"]["decision"] for value in train)),
        "screen_decisions": dict(Counter(value["compiler_input"]["oracle_certificate"]["decision"] for value in screen)),
        "screen_rules": dict(Counter((value["contrast_rule"] or "ORDINARY") for value in screen)),
        "acquisition_audits": data.ACQUISITION_AUDITS,
        "freshness_limit": "Registered alpha-normalized predecessor exclusion; not external novelty proof",
        "confirmation_materialized": False, "transfer_authorized": False, "binding_authority": False,
    }
    return {"train_scenarios": train, "train_ordinary": ordinary,
            "train_actionnet": actionnet, "screen_reference": screen, "qualification": report}