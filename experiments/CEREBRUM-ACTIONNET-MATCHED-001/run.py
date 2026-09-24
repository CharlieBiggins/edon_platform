"""CPU orchestration plus explicit paid-stage dispatch for Matched-001."""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path
import subprocess
import sys

from foundation import (ARMS, ID, canonical, file_hash, framework_sources,
                        fresh_directory, inherited_source_closure, inventory,
                        load_config, no_links, object_hash, protect_output, read,
                        relative, require, rows, snapshot_hashes, validate_program005_audit,
                        validate_billing_receipt, validate_execution_approval, validate_study, write_bytes,
                        write_json, write_rows)
import dataset
import token_budget

ROOT = Path(__file__).resolve().parent
EXPERIMENTS = ROOT.parent
COMPARISON001 = ROOT.parent / "CEREBRUM-ACTIONNET-COMPARISON-001"


def config():
    return load_config(ROOT)


def comparison_audit_sources():
    require(COMPARISON001.is_dir(), "Comparison-001 audit implementation missing")
    return framework_sources(COMPARISON001)


def preflight():
    value = config()
    template = read(ROOT / "study.template.json")
    validate_study(template, value, "draft")
    unresolved = []
    if template["program005_audit_sha256"] is None:
        unresolved.append("Verified complete Program-005 audit and acknowledged disposition")
    if template["base_snapshot"]["weights_tree_sha256"] is None:
        unresolved.append("Local base/tokenizer snapshot hashes and license review")
    if template["training_budget"]["processed_nonpadding_tokens_per_arm"] is None:
        unresolved.append("Processed-token, GPU-hour, price, and currency caps")
    if not template["human_approval_to_register"]:
        unresolved.append("Registration and claim-boundary approval")
    unresolved.append("Separate named paid-execution approval bound after registration")
    return {"protocol_id": ID, "status": value["status"], "stage": value["stage"],
        "framework_source_inventory_sha256": object_hash(framework_sources(ROOT)),
        "training_runs_planned_now": 2, "screen_records": 24, "screen_responses": 48,
        "ordinary_training_scenarios": 384, "actionnet_training_scenarios": 384,
        "ordinary_training_examples_before_token_plan": 384,
        "actionnet_training_examples_before_token_plan": 960,
        "blockers": unresolved, "program005_audited_by_this_command": False,
        "gpu_tested": False, "training_started": False, "screen_materialized": False,
        "confirmation_authorized": False, "transfer_authorized": False,
        "binding_authority": False}


def audit_program005(args):
    comparison = COMPARISON001 / "run.py"
    require(comparison.is_file(), "Comparison-001 audit helper missing")
    command = [sys.executable, "-B", str(comparison), "audit-program005",
        "--workspace", str(args.workspace), "--parent-search", str(args.parent_search),
        "--output-dir", str(args.output_dir)]
    completed = subprocess.run(command, text=True, encoding="utf-8")
    require(completed.returncode == 0, "Program-005 audit failed; no Matched-001 substitution allowed")
    path = args.output_dir / "program005-audit.json"
    require(path.is_file(), "Program-005 audit output missing")
    return {"status": "PROGRAM005_AUDIT_PUBLISHED", "audit_sha256": file_hash(path),
            "directory": str(args.output_dir)}


def _validate_prepared(run_dir, value):
    run_dir = Path(run_dir)
    require(read(run_dir / "config.json") == value, "Run config differs")
    training = rows(run_dir / "prepared/train-scenarios.jsonl", "case_id")
    screen = rows(run_dir / "prepared/screen-reference.jsonl", "case_id")
    ordinary = rows(run_dir / "prepared/train-ordinary.jsonl", "example_id")
    actionnet = rows(run_dir / "prepared/train-actionnet.jsonl", "example_id")
    dataset.validate_serialization(training, ordinary, actionnet)
    require(len(screen) == 24 and len({row["counterfactual_pair_id"] for row in screen}) == 12,
            "Screen inventory differs")
    inputs = rows(run_dir / "prepared/screen-inputs.jsonl", "case_id")
    require(inputs == [{"case_id": row["case_id"], "prompt": dataset.native_prompt(row)} for row in screen],
            "Screen inference inputs differ from shared native interface")
    qualification = read(run_dir / "prepared/qualification.json")
    require(qualification["passed"] is True and qualification["training_scenarios"] == 384
            and qualification["screen_scenarios"] == 24, "Data qualification differs")
    return qualification


def prepare(args):
    value = config()
    study = read(args.study)
    validate_study(study, value, "draft")
    require(isinstance(study["program005_audit_sha256"], str), "Set Program-005 audit hash before preparation")
    validate_program005_audit(args.program005_audit, study)
    require(not args.output_dir.exists(), "Run destination exists")
    bundle = dataset.generate_bundle(value)
    fresh_directory(args.output_dir)
    write_json(args.output_dir / "config.json", value)
    write_json(args.output_dir / "study.json", study)
    write_bytes(args.output_dir / "program005-audit.json", args.program005_audit.read_bytes())
    prepared = args.output_dir / "prepared"
    write_rows(prepared / "train-scenarios.jsonl", bundle["train_scenarios"])
    write_rows(prepared / "train-ordinary.jsonl", bundle["train_ordinary"])
    write_rows(prepared / "train-actionnet.jsonl", bundle["train_actionnet"])
    write_rows(prepared / "screen-reference.jsonl", bundle["screen_reference"])
    write_rows(prepared / "screen-inputs.jsonl", [
        {"case_id": row["case_id"], "prompt": dataset.native_prompt(row)}
        for row in bundle["screen_reference"]])
    write_json(prepared / "qualification.json", bundle["qualification"])
    report = _validate_prepared(args.output_dir, value)
    write_json(args.output_dir / "draft-manifest.json", {
        "protocol_id": ID, "status": "DATA_PREPARED_TOKEN_PLAN_PENDING",
        "study_sha256": file_hash(args.output_dir / "study.json"),
        "program005_audit_sha256": file_hash(args.output_dir / "program005-audit.json"),
        "prepared_inventory_sha256": object_hash(inventory(prepared)),
        "framework_sources_sha256": object_hash(framework_sources(ROOT)),
        "comparison001_audit_sources_sha256": object_hash(comparison_audit_sources()),
        "qualification_sha256": file_hash(prepared / "qualification.json"),
        "training_started": False, "transfer_authorized": False, "binding_authority": False})
    return {"status": "DATA_PREPARED_TOKEN_PLAN_PENDING", "run_dir": str(args.output_dir),
            "training_scenarios": report["training_scenarios"], "screen_records": report["screen_scenarios"],
            "training_started": False}


def token_plan(args):
    value = config(); study = read(args.run_dir / "study.json")
    _validate_prepared(args.run_dir, value)
    return token_budget.materialize(args.run_dir, args.base_snapshot, value, study)


def _registered_data_inventory(run_dir):
    run_dir = Path(run_dir)
    result = {name: file_hash(run_dir / name) for name in
        ("config.json", "study.json", "program005-audit.json", "draft-manifest.json")}
    result.update({"prepared/" + name: value for name, value in inventory(run_dir / "prepared").items()})
    return result


def register(args):
    value = config(); run_dir = args.run_dir
    require(not (run_dir / "registration.json").exists(), "Run is already registered")
    require(not (run_dir / "results").exists() and not (run_dir / "artifacts").exists(),
            "Registration must precede runtime/training")
    allowed = {"config.json", "study.json", "program005-audit.json", "draft-manifest.json", "prepared"}
    require({path.name for path in run_dir.iterdir()} == allowed, "Unexpected pre-registration run file")
    study = read(run_dir / "study.json")
    validate_study(study, value, "registration")
    validate_program005_audit(run_dir / "program005-audit.json", study)
    _validate_prepared(run_dir, value)
    token_audit = token_budget.verify_plans(run_dir, value, study)
    source_inventory = framework_sources(ROOT)
    audit_sources = comparison_audit_sources()
    inherited = inherited_source_closure(EXPERIMENTS)
    registration = {"schema_version": 1, "protocol_id": ID, "stage": value["stage"],
        "framework_version": value["framework_version"],
        "source_inventory": source_inventory, "source_inventory_sha256": object_hash(source_inventory),
        "comparison001_audit_source_inventory": audit_sources,
        "comparison001_audit_source_inventory_sha256": object_hash(audit_sources),
        "inherited_source_inventory": inherited, "inherited_source_inventory_sha256": object_hash(inherited),
        "data_inventory": _registered_data_inventory(run_dir),
        "program005_audit_sha256": file_hash(run_dir / "program005-audit.json"),
        "study_sha256": file_hash(run_dir / "study.json"),
        "token_audit_sha256": file_hash(run_dir / "prepared/token-audit.json"),
        "realized_training_tokens": {arm: token_audit["arms"][arm]["realized_nonpadding_tokens"] for arm in ARMS},
        "base_snapshot": study["base_snapshot"], "paid_execution_approved": False,
        "screen_records": 24, "screen_responses": 48,
        "confirmation_authorized": False, "transfer_authorized": False, "binding_authority": False}
    write_json(run_dir / "registration.json", registration)
    verify_run(run_dir)
    return {"status": "A_STAGE_REGISTERED_NOT_EXECUTED", "run_dir": str(run_dir),
        "registration_sha256": file_hash(run_dir / "registration.json"),
        "paid_execution_approved": registration["paid_execution_approved"], "training_started": False}


def verify_run(run_dir):
    run_dir = Path(run_dir); no_links(run_dir)
    allowed = {"config.json", "study.json", "program005-audit.json", "draft-manifest.json",
               "prepared", "registration.json", "execution-approval.json", "billing-receipt.json",
               "results", "artifacts"}
    require({path.name for path in run_dir.iterdir()} <= allowed, "Unexpected file in registered run root")
    registration = read(run_dir / "registration.json")
    value = config(); study = read(run_dir / "study.json")
    require(registration["protocol_id"] == ID and registration["schema_version"] == 1,
            "Registration identity differs")
    validate_study(study, value, "registration")
    require(registration["study_sha256"] == file_hash(run_dir / "study.json")
            and registration["program005_audit_sha256"] == file_hash(run_dir / "program005-audit.json"),
            "Registration input binding differs")
    validate_program005_audit(run_dir / "program005-audit.json", study)
    _validate_prepared(run_dir, value)
    token_budget.verify_plans(run_dir, value, study)
    sources = framework_sources(ROOT); audit_sources = comparison_audit_sources()
    inherited = inherited_source_closure(EXPERIMENTS)
    require(registration["source_inventory"] == sources
            and registration["source_inventory_sha256"] == object_hash(sources), "Framework changed after registration")
    require(registration["comparison001_audit_source_inventory"] == audit_sources
            and registration["comparison001_audit_source_inventory_sha256"] == object_hash(audit_sources),
            "Program-005 audit helper changed after registration")
    require(registration["inherited_source_inventory"] == inherited
            and registration["inherited_source_inventory_sha256"] == object_hash(inherited),
            "Inherited generator/scorer closure changed")
    require(registration["data_inventory"] == _registered_data_inventory(run_dir),
            "Registered prepared data changed")
    require(registration["confirmation_authorized"] is False
            and registration["transfer_authorized"] is False and registration["binding_authority"] is False,
            "Authority boundary differs")
    return registration


def authorize_execution(args):
    registration = verify_run(args.run_dir)
    require(not (args.run_dir / "execution-approval.json").exists(), "Execution approval already published")
    study = read(args.run_dir / "study.json")
    approval = read(args.approval)
    validate_execution_approval(approval, args.run_dir, study)
    write_bytes(args.run_dir / "execution-approval.json", args.approval.read_bytes())
    return {"status": "A_STAGE_PAID_EXECUTION_APPROVED_NOT_STARTED",
        "registration_sha256": file_hash(args.run_dir / "registration.json"),
        "execution_approval_sha256": file_hash(args.run_dir / "execution-approval.json"),
        "training_started": False, "transfer_authorized": False, "binding_authority": False}


def record_billing(args):
    verify_run(args.run_dir)
    require(not (args.run_dir / "billing-receipt.json").exists(), "Billing receipt already published")
    study = read(args.run_dir / "study.json")
    receipt = read(args.receipt)
    validate_billing_receipt(receipt, args.run_dir, study)
    write_bytes(args.run_dir / "billing-receipt.json", args.receipt.read_bytes())
    return {"status": "A_STAGE_PROVIDER_BILLING_RECORDED",
        "billing_receipt_sha256": file_hash(args.run_dir / "billing-receipt.json"),
        "actual_gpu_hours": receipt["actual_gpu_hours"], "actual_cost_usd": receipt["actual_cost_usd"]}


def _paid(args):
    require(args.authorize_paid, "Paid stage requires literal --authorize-paid")
    value = config(); registration = verify_run(args.run_dir); study = read(args.run_dir / "study.json")
    validate_study(study, value, "registration")
    require((args.run_dir / "execution-approval.json").is_file(), "Separate execution approval missing")
    validate_execution_approval(read(args.run_dir / "execution-approval.json"), args.run_dir, study)
    hashes = snapshot_hashes(args.base_snapshot)
    require(hashes["weights_tree_sha256"] == study["base_snapshot"]["weights_tree_sha256"]
            and hashes["tokenizer_tree_sha256"] == study["base_snapshot"]["tokenizer_tree_sha256"],
            "Base snapshot differs")
    import gpu_worker
    return value, study, registration, gpu_worker


def runtime(args):
    value, study, registration, worker = _paid(args)
    return worker.runtime_preflight(args.run_dir, args.base_snapshot, value, study, registration)


def train(args):
    value, study, registration, worker = _paid(args)
    return worker.train(args.run_dir, args.base_snapshot, args.arm, value, study)


def predict(args):
    value, study, registration, worker = _paid(args)
    return worker.predict(args.run_dir, args.base_snapshot, args.arm, value, study)


def _prediction(run_dir, arm, registration, config_value):
    import gpu_worker
    trained = gpu_worker.trained_manifest(run_dir, arm, config_value)
    path = run_dir / "results" / ("screen-" + arm + "-predictions.jsonl")
    binding = {"protocol_id": ID, "arm": arm,
        "registration_sha256": file_hash(run_dir / "registration.json"),
        "input_sha256": file_hash(run_dir / "prepared/screen-inputs.jsonl"),
        "adapter_sha256": trained["adapter_sha256"],
        "runtime_readiness_sha256": file_hash(run_dir / "results/runtime-readiness.json"),
        "shared_output_format": config_value["shared_output_format"]}
    require(read(path.with_suffix(".binding.json")) == binding, "Prediction binding differs: " + arm)
    manifest = read(path.with_suffix(".manifest.json"))
    require(manifest["binding"] == binding and manifest["count"] == config_value["screen_records"]
            and manifest["predictions_sha256"] == file_hash(path), "Prediction manifest differs: " + arm)
    values = rows(path, "case_id")
    expected = [row["case_id"] for row in rows(run_dir / "prepared/screen-inputs.jsonl", "case_id")]
    require([row["case_id"] for row in values] == expected, "Prediction IDs/order differ: " + arm)
    for row in values:
        require(isinstance(row["raw_output"], str), "Raw output must remain text")
        require(type(row["ended_with_eos"]) is bool and type(row["hit_generation_limit"]) is bool,
                "Generation flags missing")
        require(type(row["prompt_token_count"]) is int and 0 < row["prompt_token_count"] <= config_value["max_input_tokens"],
                "Prompt token count invalid")
        require(type(row["generated_token_count"]) is int and 0 <= row["generated_token_count"] <= config_value["max_new_tokens"],
                "Generated token count invalid")
        require(type(row["generation_seconds"]) in (int, float) and math.isfinite(row["generation_seconds"])
                and row["generation_seconds"] >= 0, "Generation time invalid")
    return values, manifest


def score(args):
    require(not args.output_dir.exists(), "Score destination exists")
    value = config(); registration = verify_run(args.run_dir); study = read(args.run_dir / "study.json")
    validate_study(study, value, "registration")
    require((args.run_dir / "billing-receipt.json").is_file(), "Provider billing receipt required before final scoring")
    billing = validate_billing_receipt(read(args.run_dir / "billing-receipt.json"), args.run_dir, study)
    expected_results = {"runtime-readiness.json"}
    for arm in ARMS:
        expected_results.update({"screen-" + arm + "-predictions.jsonl",
            "screen-" + arm + "-predictions.binding.json", "screen-" + arm + "-predictions.manifest.json"})
    actual_results = {path.name for path in (args.run_dir / "results").iterdir() if path.is_file()}
    unexpected = {name for name in actual_results - expected_results if ".interrupted-" not in name}
    require(not unexpected and expected_results <= actual_results, "Unexpected or missing result files: " + str(sorted(unexpected)))
    require({path.name for path in (args.run_dir / "artifacts").iterdir() if path.is_dir()} == set(ARMS),
            "Artifact arm inventory differs")
    reference = rows(args.run_dir / "prepared/screen-reference.jsonl", "case_id")
    predictions, manifests = {}, {}
    for arm in ARMS:
        predictions[arm], manifests[arm] = _prediction(args.run_dir, arm, registration, value)
    import scorer
    scores = {arm: scorer.score_condition(reference, predictions[arm], study, arm) for arm in ARMS}
    comparison = scorer.compare(reference, scores, study)
    comparison.update(registration_sha256=file_hash(args.run_dir / "registration.json"),
        prediction_hashes={arm: file_hash(args.run_dir / "results" / ("screen-" + arm + "-predictions.jsonl")) for arm in ARMS},
        compute={arm: {"gpu_seconds": manifests[arm]["gpu_seconds"],
                       "estimated_cost_usd": manifests[arm]["estimated_cost_usd"],
                       "billing_attested": manifests[arm]["billing_attested"]} for arm in ARMS},
        provider_billing={"actual_gpu_hours": billing["actual_gpu_hours"],
                          "actual_cost_usd": billing["actual_cost_usd"],
                          "receipt_sha256": file_hash(args.run_dir / "billing-receipt.json")})
    fresh_directory(args.output_dir)
    for arm in ARMS:
        write_json(args.output_dir / (arm + "-score.json"), scores[arm])
    write_json(args.output_dir / "comparison.json", comparison)
    write_json(args.output_dir / "score-manifest.json", {"protocol_id": ID,
        "registration_sha256": file_hash(args.run_dir / "registration.json"),
        "score_hashes": {arm: file_hash(args.output_dir / (arm + "-score.json")) for arm in ARMS},
        "comparison_sha256": file_hash(args.output_dir / "comparison.json"),
        "status": comparison["status"], "selected_arm": None,
        "transfer_authorized": False, "binding_authority": False})
    return comparison


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="stage", required=True)
    sub.add_parser("preflight")
    audit = sub.add_parser("audit-program005")
    audit.add_argument("--workspace", type=relative, required=True)
    audit.add_argument("--parent-search", type=relative, required=True)
    audit.add_argument("--output-dir", type=relative, required=True)
    prepare_parser = sub.add_parser("prepare")
    prepare_parser.add_argument("--study", type=relative, required=True)
    prepare_parser.add_argument("--program005-audit", type=relative, required=True)
    prepare_parser.add_argument("--output-dir", type=relative, required=True)
    plan = sub.add_parser("token-plan")
    register_parser = sub.add_parser("register")
    approval_parser = sub.add_parser("authorize-execution")
    billing_parser = sub.add_parser("record-billing")
    runtime_parser = sub.add_parser("runtime")
    train_parser = sub.add_parser("train")
    predict_parser = sub.add_parser("predict")
    scoring = sub.add_parser("score")
    for item in (plan, register_parser, approval_parser, billing_parser, runtime_parser, train_parser, predict_parser, scoring):
        item.add_argument("--run-dir", type=relative, required=True)
    approval_parser.add_argument("--approval", type=relative, required=True)
    billing_parser.add_argument("--receipt", type=relative, required=True)
    for item in (plan, runtime_parser, train_parser, predict_parser):
        item.add_argument("--base-snapshot", type=relative, required=True)
    for item in (runtime_parser, train_parser, predict_parser):
        item.add_argument("--authorize-paid", action="store_true")
    for item in (train_parser, predict_parser):
        item.add_argument("--arm", choices=ARMS, required=True)
    scoring.add_argument("--output-dir", type=relative, required=True)
    args = parser.parse_args()
    if args.stage == "preflight":
        result = preflight()
    elif args.stage == "audit-program005":
        protect_output(args.output_dir, args.workspace, args.parent_search, ROOT)
        result = audit_program005(args)
    elif args.stage == "prepare":
        protect_output(args.output_dir, args.study, args.program005_audit, ROOT)
        result = prepare(args)
    elif args.stage == "token-plan":
        result = token_plan(args)
    elif args.stage == "register":
        result = register(args)
    elif args.stage == "authorize-execution":
        result = authorize_execution(args)
    elif args.stage == "record-billing":
        result = record_billing(args)
    elif args.stage == "runtime":
        result = runtime(args)
    elif args.stage == "train":
        result = train(args)
    elif args.stage == "predict":
        result = predict(args)
    else:
        protect_output(args.output_dir, args.run_dir, ROOT)
        result = score(args)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()