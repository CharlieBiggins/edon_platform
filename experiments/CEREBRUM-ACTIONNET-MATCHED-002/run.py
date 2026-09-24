"""CPU preparation, commitment, verification and locked scoring for Matched-002."""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import importlib.util
import json
import math
from pathlib import Path, PureWindowsPath
import shutil
import sys

ROOT = Path(__file__).resolve().parent
MATCHED001 = ROOT.parent / "CEREBRUM-ACTIONNET-MATCHED-001"
ID = "CEREBRUM-ACTIONNET-MATCHED-002"
CANDIDATES = ("ordinary-a", "actionnet-a", "ordinary-b", "actionnet-b")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, "Duplicate JSON key: " + key)
        result[key] = value
    return result


def parse(payload):
    return json.loads(payload, object_pairs_hook=pairs, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def read(path):
    return parse(Path(path).read_bytes())


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def file_hash(path):
    value = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    return "sha256:" + value


def rows(path):
    payload = Path(path).read_bytes()
    require(payload and payload.endswith(b"\n"), "JSONL must be nonempty and newline terminated")
    return [parse(line) for line in payload.splitlines()]


def relative(value):
    path = Path(value)
    require(not path.is_absolute() and not PureWindowsPath(str(path)).drive, "Use relative paths")
    return path


def write_once(path, payload):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(payload)


def write_json(path, value):
    write_once(path, (canonical(value) + "\n").encode())


def config():
    value = read(ROOT / "config.json")
    require(value["protocol_id"] == ID and (value["records"], value["pairs"], value["responses"]) == (48, 24, 192),
            "Configuration identity differs")
    return value


def validate_study(study, registration=False):
    require(study["schema_version"] == 1 and study["stage"] == "PAIRED_SEED_LOCKED_QUALIFICATION",
            "Study identity differs")
    require((study["records"], study["pairs"], study["responses"]) == (48, 24, 192), "Study size differs")
    gates = study["gates"]
    require(set(gates) == {"program_exact_floor", "minimum_program_exact_delta",
        "minimum_additional_correct_cases", "paired_bootstrap_lower_floor",
        "unsafe_authorization_ceiling", "raw_unsafe_authorization_ceiling",
        "unnecessary_abstention_delta_ceiling", "minimum_improved_mechanisms"}, "Gate inventory differs")
    require(0 <= gates["program_exact_floor"] <= 1 and 0 < gates["minimum_program_exact_delta"] <= 1,
            "Invalid accuracy gate")
    require(type(gates["minimum_additional_correct_cases"]) is int and gates["minimum_additional_correct_cases"] > 0,
            "Invalid correct-case gate")
    bootstrap = study["bootstrap"]
    require(bootstrap["repetitions"] >= 1000 and 0 < bootstrap["confidence_level"] < 1, "Bootstrap differs")
    execution = study["execution"]
    require(execution["do_sample"] is False and execution["retries"] == 0 and execution["tools"] == []
            and execution["reference_answers_visible"] is False, "Execution interface differs")
    if registration:
        for key in ("a_registration_sha256", "b_registration_sha256"):
            require(isinstance(study["candidate_runs"][key], str) and study["candidate_runs"][key].startswith("sha256:"),
                    "Candidate registration commitment missing")
        require(isinstance(study["screen_a_disposition_sha256"], str)
                and study["screen_a_disposition_sha256"].startswith("sha256:"), "A-screen commitment missing")
        require(type(execution["maximum_total_gpu_hours"]) in (int, float)
                and execution["maximum_total_gpu_hours"] > 0, "GPU cap missing")
        require(type(execution["maximum_total_cost_usd"]) in (int, float)
                and execution["maximum_total_cost_usd"] > 0, "Cost cap missing")
        require(study["human_approval_to_register"] is True and study["claim_boundary_acknowledged"] is True,
                "Registration approval missing")
    return study


def preflight():
    validate_study(read(ROOT / "study.template.json"), False)
    return {"protocol_id": ID, "status": "BLOCKED_DRAFT", "records": 48, "responses": 192,
        "new_training_runs": 0, "required_registered_training_runs": 2,
        "blockers": ["Supported seed-A screen", "Registered seed-B replication run",
                     "Resolved hashes, gates and inference budget", "Separate paid approval"],
        "transfer_authorized": False, "binding_authority": False}


def prepare_instrument(output_dir):
    require(not output_dir.exists(), "Destination exists")
    spec = importlib.util.spec_from_file_location("matched002_instrument", ROOT / "instrument.py")
    instrument_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(instrument_module)
    reference, inputs, report = instrument_module.generate()
    output_dir.mkdir(parents=True)
    write_once(output_dir / "qualification-reference.jsonl",
        "".join(canonical(row) + "\n" for row in reference).encode())
    write_once(output_dir / "qualification-inputs.jsonl",
        "".join(canonical(row) + "\n" for row in inputs).encode())
    write_json(output_dir / "instrument-manifest.json", report)
    return report


def training_registration(run_dir, expected_label):
    registration = read(run_dir / "registration.json")
    study = read(run_dir / "study.json")
    require(registration["protocol_id"] == "CEREBRUM-ACTIONNET-MATCHED-001", "Training protocol differs")
    require(study["training_seed_label"] == expected_label, "Training seed label differs")
    return registration, study


def register(args):
    require(not args.output_dir.exists(), "Destination exists")
    study = validate_study(read(args.study), True)
    a_registration, a_study = training_registration(args.a_run, "A")
    b_registration, b_study = training_registration(args.b_run, "B")
    require(file_hash(args.a_run / "registration.json") == study["candidate_runs"]["a_registration_sha256"],
            "Seed-A registration hash differs")
    require(file_hash(args.b_run / "registration.json") == study["candidate_runs"]["b_registration_sha256"],
            "Seed-B registration hash differs")
    for key in ("base_snapshot", "training_budget"):
        require(a_study[key] == b_study[key], "A/B registered recipe differs: " + key)
    manifest = read(args.instrument / "instrument-manifest.json")
    require(manifest["protocol_id"] == ID and manifest["records"] == 48, "Instrument differs")
    require(file_hash(args.instrument / "qualification-reference.jsonl") == manifest["reference_sha256"]
            and file_hash(args.instrument / "qualification-inputs.jsonl") == manifest["inputs_sha256"],
            "Instrument content hash differs")
    args.output_dir.mkdir(parents=True)
    for source, name in ((ROOT / "config.json", "config.json"), (args.study, "study.json"),
                         (args.instrument / "instrument-manifest.json", "instrument-manifest.json"),
                         (args.instrument / "qualification-reference.jsonl", "qualification-reference.jsonl"),
                         (args.instrument / "qualification-inputs.jsonl", "qualification-inputs.jsonl")):
        write_once(args.output_dir / name, source.read_bytes())
    commitments = {"ordinary-a": {"training_run": "A", "arm": "ordinary"},
        "actionnet-a": {"training_run": "A", "arm": "actionnet"},
        "ordinary-b": {"training_run": "B", "arm": "ordinary"},
        "actionnet-b": {"training_run": "B", "arm": "actionnet"}}
    for value in commitments.values():
        source = args.a_run if value["training_run"] == "A" else args.b_run
        value["registration_sha256"] = file_hash(source / "registration.json")
    write_json(args.output_dir / "candidate-commitments.json", commitments)
    registration = {"schema_version": 1, "protocol_id": ID,
        "study_sha256": file_hash(args.output_dir / "study.json"),
        "instrument_manifest_sha256": file_hash(args.output_dir / "instrument-manifest.json"),
        "inputs_sha256": file_hash(args.output_dir / "qualification-inputs.jsonl"),
        "reference_sha256": file_hash(args.output_dir / "qualification-reference.jsonl"),
        "candidate_commitments_sha256": file_hash(args.output_dir / "candidate-commitments.json"),
        "screen_a_disposition_sha256": study["screen_a_disposition_sha256"],
        "paid_execution_approved": False, "transfer_authorized": False, "binding_authority": False}
    write_json(args.output_dir / "registration.json", registration)
    return {"status": "REGISTERED_NOT_EXECUTED", "registration_sha256": file_hash(args.output_dir / "registration.json"),
            "responses": 192, "transfer_authorized": False}


def _score_study(study):
    return {"screen": {"gates": {"parse_valid_floor": 0, "event_order_floor": 0,
        "partition_floor": 0, "executed_state_floor": 0, "decision_floor": 0,
        "program_exact_floor": 0, "unsafe_authorization_ceiling": 0,
        "generation_limit_hit_ceiling": 0}}}


def _candidate_predictions(run_dir, candidate):
    path = run_dir / "results" / (candidate + "-predictions.jsonl")
    manifest = read(path.with_suffix(".manifest.json"))
    require(manifest["candidate"] == candidate and manifest["count"] == 48
            and manifest["predictions_sha256"] == file_hash(path), "Prediction manifest differs: " + candidate)
    values = rows(path)
    require(len(values) == 48 and len({row["case_id"] for row in values}) == 48, "Prediction inventory differs")
    return values


def _mechanism_improvements(reference, ordinary_score, actionnet_score):
    left = {row["case_id"]: row for row in ordinary_score["evaluations"]}
    right = {row["case_id"]: row for row in actionnet_score["evaluations"]}
    groups = defaultdict(list)
    for row in reference:
        groups[row["contrast_rule"] or "ORDINARY"].append(row["case_id"])
    result = {}
    for name, cases in groups.items():
        result[name] = sum(int(right[case]["program_exact"]) - int(left[case]["program_exact"])
                           for case in cases) / len(cases)
    return result


def score(args):
    registration = read(args.run_dir / "registration.json")
    require(registration["protocol_id"] == ID, "Registration differs")
    study = validate_study(read(args.run_dir / "study.json"), True)
    require(file_hash(args.a_screen_comparison) == study["screen_a_disposition_sha256"], "A-screen disposition hash differs")
    screen = read(args.a_screen_comparison)
    require(screen["status"] == "SUPPORTED", "Seed-A screen did not authorize qualification")
    reference = rows(args.run_dir / "qualification-reference.jsonl")
    sys.path.insert(0, str(MATCHED001))
    import scorer as inherited_scorer
    scoring_study = _score_study(study)
    predictions = {name: _candidate_predictions(args.run_dir, name) for name in CANDIDATES}
    scores = {name: inherited_scorer.score_condition(reference, predictions[name], scoring_study,
        "ordinary" if name.startswith("ordinary") else "actionnet") for name in CANDIDATES}
    gates = study["gates"]
    pair_results = {}
    hard_failure = False; comparative_failure = False
    for label, seed in (("A", study["bootstrap"]["seed_a"]), ("B", study["bootstrap"]["seed_b"])):
        ordinary = scores["ordinary-" + label.lower()]
        actionnet = scores["actionnet-" + label.lower()]
        delta = inherited_scorer.paired_delta(reference, ordinary, actionnet)
        uncertainty = inherited_scorer.cluster_bootstrap(reference, ordinary, actionnet,
            study["bootstrap"]["repetitions"], seed, study["bootstrap"]["confidence_level"])
        extra = round((actionnet["program_exact_rate"] - ordinary["program_exact_rate"]) * 48)
        mechanism = _mechanism_improvements(reference, ordinary, actionnet)
        ordinary_abstain = ordinary["all_metrics"]["unnecessary_abstention_rate"] or 0
        actionnet_abstain = actionnet["all_metrics"]["unnecessary_abstention_rate"] or 0
        hard = {"program_exact_floor": actionnet["program_exact_rate"] >= gates["program_exact_floor"],
            "unsafe_execution": actionnet["unsafe_authorizations"] <= gates["unsafe_authorization_ceiling"],
            "unsafe_raw": actionnet["raw_claim_unsafe_authorizations"] <= gates["raw_unsafe_authorization_ceiling"],
            "abstention": actionnet_abstain - ordinary_abstain <= gates["unnecessary_abstention_delta_ceiling"]}
        comparative = {"advantage": delta >= gates["minimum_program_exact_delta"]
                            or extra >= gates["minimum_additional_correct_cases"],
            "paired_uncertainty": delta > 0 and uncertainty["lower"] >= gates["paired_bootstrap_lower_floor"],
            "multiple_mechanisms": sum(value > 0 for value in mechanism.values()) >= gates["minimum_improved_mechanisms"]}
        hard_failure |= not all(hard.values()); comparative_failure |= not all(comparative.values())
        pair_results[label] = {"hard_checks": hard, "comparative_checks": comparative,
            "program_exact_delta": delta, "additional_correct_cases": extra,
            "paired_uncertainty": uncertainty, "mechanism_deltas": mechanism,
            "ordinary_program_exact": ordinary["program_exact_rate"],
            "actionnet_program_exact": actionnet["program_exact_rate"]}
    status = "NOT_SUPPORTED" if hard_failure else ("INCONCLUSIVE" if comparative_failure else "SUPPORTED")
    result = {"protocol_id": ID, "status": status, "pair_results": pair_results,
        "claim": "BOUNDED_TWO_SEED_LEARNING_ADVANTAGE" if status == "SUPPORTED" else None,
        "transfer_authorized": False, "binding_authority": False}
    require(not args.output_dir.exists(), "Score destination exists")
    args.output_dir.mkdir(parents=True)
    for name, value in scores.items():
        write_json(args.output_dir / (name + "-score.json"), value)
    write_json(args.output_dir / "comparison.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("preflight")
    prepare = sub.add_parser("prepare-instrument"); prepare.add_argument("--output-dir", type=relative, required=True)
    reg = sub.add_parser("register")
    for name in ("study", "instrument", "a_run", "b_run", "output_dir"):
        reg.add_argument("--" + name.replace("_", "-"), dest=name, type=relative, required=True)
    scoring = sub.add_parser("score")
    for name in ("run_dir", "a_screen_comparison", "output_dir"):
        scoring.add_argument("--" + name.replace("_", "-"), dest=name, type=relative, required=True)
    args = parser.parse_args()
    if args.command == "preflight": result = preflight()
    elif args.command == "prepare-instrument": result = prepare_instrument(args.output_dir)
    elif args.command == "register": result = register(args)
    else: result = score(args)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()