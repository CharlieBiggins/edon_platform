"""CPU-only audit, screen preparation, and bound raw-output scoring. No GPU launcher."""
import argparse
import json
import math
from pathlib import Path
import sys

from foundation import (CONDITIONS, ID, PARENT, canonical, file_hash, inventory,
                        no_links, object_hash, read, relative, require, rows,
                        safe_name, source_closure, validate_contract, write_json, write_rows)

ROOT = Path(__file__).parent


def config():
    c = read(ROOT / "config.json")
    require(c["protocol_id"] == ID and c["conditions"] == list(CONDITIONS)
            and (c["screen_records"], c["ordinary_records"], c["targeted_records"], c["model_response_budget"]) == (48, 24, 24, 240)
            and c["minimum_additional_exact_cases_vs_each_reference"] == 2
            and c["minimum_joint_correct_pairs_per_rule"] == 1 and c["targeted_pairs_per_rule"] == 2
            and c["trace_exact_floor"] == 0.95
            and c["development_only"] is True and all(c[k] is False for k in
                ("confirmation_authorized", "transfer_authorized", "binding_authority", "paid_execution_implemented")),
            "Reserved framework configuration differs")
    return c


def own_sources():
    paths = [*ROOT.glob("*.py"), *ROOT.glob("*.json"), *ROOT.glob("*.md"), *ROOT.glob("tests/*.py")]
    return {p.relative_to(ROOT).as_posix(): file_hash(p) for p in sorted(paths)}


def fresh_directory(path):
    no_links(path)
    require(not path.exists(), "Destination exists; never overwrite a run")
    path.mkdir(parents=True, exist_ok=False)


def protect_output(output, *inputs):
    destination = output.resolve()
    for source in (ROOT, *inputs):
        source = Path(source).resolve()
        require(destination != source and source not in destination.parents,
                "Output must be outside source, input and registered run directories")


def preflight():
    c = config()
    return {"protocol_id": ID, "status": c["status"], "source_inventory_sha256": object_hash(own_sources()),
            "screen_records": 48, "learning_conditions": 5, "model_responses": 240,
            "blockers": ["Verified complete Program005 result has not been supplied to this command",
                         "Baseline identity, frozen inference interface and spending caps must be supplied",
                         "Paid inference runner is not implemented by this CPU framework"],
            "gpu_tested": False, "training_started": False, "screen_materialized": False,
            "transfer_authorized": False, "binding_authority": False}


def condition_identities(loaded, audit, contract):
    core = loaded[2]
    c = read(core.PARENT / "config.json")
    base = {"model_id": c["model_name"], "revision": c["model_revision"], "adapter_sha256": None}
    return {"base": base, "parent": {**base, "adapter_sha256": PARENT},
            "ordinary": {**base, "adapter_sha256": audit["adapters"]["ordinary"]},
            "targeted": {**base, "adapter_sha256": audit["adapters"]["repair"]},
            "open_weight_alternative": {"model_id": contract["alternative"]["model_id"],
                "revision": contract["alternative"]["revision"],
                "weights_tree_sha256": contract["alternative"]["weights_tree_sha256"]}}


def prepare(args):
    import bridge
    c = config()
    require(not args.output_dir.exists(), "Screen destination exists")
    contract = read(args.contract)
    validate_contract(contract)
    no_links(args.interface_dir)
    interface_files = {"prompt-pack.txt": "prompt_pack_sha256", "runner.py": "runner_source_sha256",
                       "runtime-lock.json": "runtime_lock_sha256"}
    for filename, field in interface_files.items():
        require(file_hash(args.interface_dir / filename) == contract["interface"][field], "Interface artifact mismatch: " + filename)
    require(args.alternative_dir.is_dir(), "Provide the baseline snapshot directory; no downloads are performed")
    require(object_hash(inventory(args.alternative_dir)) == contract["alternative"]["weights_tree_sha256"],
            "Alternative snapshot tree hash differs")
    report, loaded = bridge.audit(args.workspace, args.parent_search)
    require(report["allows_screen_registration"] is True,
            "Program005 HOLD: preserve the result; a different repair proposal needs a new protocol")
    core = loaded[2]
    require(contract["alternative"]["model_id"] != read(core.PARENT / "config.json")["model_name"],
            "Alternative must not simply rename the base model")
    values, coverage = bridge.generate(loaded, c)
    fresh_directory(args.output_dir)
    for name, obj in (("config.json", c), ("contract.json", contract), ("program005-audit.json", report), ("coverage.json", coverage)):
        write_json(args.output_dir / name, obj)
    write_rows(args.output_dir / "screen-reference.jsonl", values)
    write_rows(args.output_dir / "screen-inputs.jsonl", [{"case_id": r["case_id"], "prompt": r["prompt"]} for r in values])
    (args.output_dir / "interface").mkdir()
    for filename in interface_files:
        with (args.output_dir / "interface" / filename).open("xb") as stream:
            stream.write((args.interface_dir / filename).read_bytes())
    # The reference file is only for offline scoring. Do not expose it to an inference runner.
    registration = {"protocol_id": ID, "schema_version": 1, "source_inventory": own_sources(),
                    "data_inventory": inventory(args.output_dir), "inherited_sources": report["source_closure"],
                    "conditions": condition_identities(loaded, report, contract), "record_count": 48,
                    "paid_execution_authorized": False, "transfer_authorized": False, "binding_authority": False}
    write_json(args.output_dir / "registration.json", registration)
    return {"status": "CPU_SCREEN_REGISTERED_NOT_EXECUTED", "directory": str(args.output_dir),
            "registration_sha256": file_hash(args.output_dir / "registration.json"),
            "model_responses_planned": 240, "paid_execution_authorized": False}


def verify_screen(directory, workspace):
    no_links(directory)
    reg = read(directory / "registration.json")
    require(reg["protocol_id"] == ID and reg["record_count"] == 48 and reg["schema_version"] == 1,
            "Screen identity differs")
    require(reg["source_inventory"] == own_sources(), "Comparison source inventory changed")
    actual = inventory(directory)
    actual.pop("registration.json")
    require(actual == reg["data_inventory"], "Screen file inventory/content differs")
    _, closure = source_closure(workspace)
    require(closure == reg["inherited_sources"], "Inherited scorer closure changed")
    require(read(directory / "config.json") == config(), "Screen config differs")
    validate_contract(read(directory / "contract.json"))
    require(set(reg["conditions"]) == set(CONDITIONS), "Condition inventory differs")
    return reg


def prediction_binding(directory, reg, condition):
    return {"protocol_id": ID, "registration_sha256": file_hash(directory / "registration.json"),
            "condition": condition, "candidate": reg["conditions"][condition],
            "input_sha256": file_hash(directory / "screen-inputs.jsonl"),
            "interface_sha256": object_hash(read(directory / "contract.json")["interface"])}


def validate_predictions(directory, reg, condition, predictions_dir, ids):
    path = predictions_dir / (condition + ".jsonl")
    values = rows(path)
    require([r["case_id"] for r in values] == ids, "Incomplete, reordered or mismatched predictions: " + condition)
    binding = prediction_binding(directory, reg, condition)
    require(read(path.with_suffix(".binding.json")) == binding, "Prediction binding mismatch: " + condition)
    manifest = read(path.with_suffix(".manifest.json"))
    require(manifest["binding"] == binding and manifest["count"] == 48
            and manifest["predictions_sha256"] == file_hash(path), "Prediction completion manifest differs")
    for row in values:
        require(isinstance(row["raw_output"], str), "Raw output must be text, not repaired objects")
        for flag in ("ended_with_eos", "hit_generation_limit"):
            require(type(row[flag]) is bool, "Missing/invalid generation flag")
        for key in ("prompt_token_count", "generated_token_count"):
            require(type(row[key]) is int and 0 < row[key] <= 4096, "Token budget exceeded or missing")
        require(type(row["generation_seconds"]) in (int, float) and math.isfinite(row["generation_seconds"])
                and row["generation_seconds"] >= 0, "Invalid timing")
    for key in ("gpu_seconds", "cost_usd"):
        require(type(manifest[key]) in (int, float) and math.isfinite(manifest[key]) and manifest[key] >= 0,
                "Missing cost/compute accounting")
    require(manifest["gpu_seconds"] >= sum(r["generation_seconds"] for r in values), "GPU accounting below generation time")
    return values, manifest


def prediction_inventory(directory):
    actual = inventory(directory)
    expected = {condition + suffix for condition in CONDITIONS
                for suffix in (".jsonl", ".binding.json", ".manifest.json")}
    require(set(actual) == expected, "Prediction directory must contain exactly the five registered output triplets")
    return actual


def score(args):
    import bridge
    require(not args.output_dir.exists(), "Score destination exists; no overwrite or rescore in place")
    reg = verify_screen(args.screen_dir, args.workspace)
    no_links(args.predictions_dir)
    prediction_files = prediction_inventory(args.predictions_dir)
    inputs = rows(args.screen_dir / "screen-reference.jsonl")
    ids = [r["case_id"] for r in inputs]
    predictions, manifests = {}, {}
    for condition in CONDITIONS:
        predictions[condition], manifests[condition] = validate_predictions(
            args.screen_dir, reg, condition, args.predictions_dir, ids)
    budget = read(args.screen_dir / "contract.json")["budget"]
    totals = {"gpu_hours": sum(m["gpu_seconds"] for m in manifests.values()) / 3600,
              "cost_usd": sum(m["cost_usd"] for m in manifests.values()), "responses": sum(len(v) for v in predictions.values())}
    budget_ok = totals["gpu_hours"] <= budget["max_gpu_hours"] and totals["cost_usd"] <= budget["max_cost_usd"]
    loaded = bridge.load(args.workspace)
    scores = {condition: bridge.score_condition(loaded, inputs, predictions[condition]) for condition in CONDITIONS}
    comparison = bridge.compare(scores, config())
    comparison["budget_within_declared_caps"] = budget_ok
    if not budget_ok:
        comparison["status"] = "SCREEN_HOLD_BUDGET_DEVIATION"
    comparison.update(protocol_id=ID, registration_sha256=file_hash(args.screen_dir / "registration.json"),
                      prediction_inventory=prediction_files, compute=totals,
                      compute_accounting="Runner-reported, not independently attested; CPU scorer cannot stop a remote GPU")
    fresh_directory(args.output_dir)
    for condition, result in scores.items():
        write_json(args.output_dir / (condition + "-score.json"), result)
    write_json(args.output_dir / "comparison.json", comparison)
    return comparison


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="stage", required=True)
    sub.add_parser("preflight")
    audit = sub.add_parser("audit-program005")
    prep = sub.add_parser("prepare-screen")
    scoring = sub.add_parser("score")
    for p in (audit, prep, scoring):
        p.add_argument("--workspace", type=relative, required=True, help="Restored Program005 workspace, relative to caller")
        p.add_argument("--output-dir", type=relative, required=True, help="New directory; never an existing run")
    for p in (audit, prep):
        p.add_argument("--parent-search", type=relative, required=True)
    for name in ("contract", "interface-dir", "alternative-dir"):
        prep.add_argument("--" + name, type=relative, required=True)
    scoring.add_argument("--screen-dir", type=relative, required=True)
    scoring.add_argument("--predictions-dir", type=relative, required=True)
    args = parser.parse_args()
    if args.stage != "preflight":
        protect_output(args.output_dir, args.workspace,
                       *[getattr(args, key) for key in ("screen_dir", "predictions_dir", "parent_search", "interface_dir", "alternative_dir")
                         if hasattr(args, key)])
    if args.stage == "preflight":
        result = preflight()
    elif args.stage == "audit-program005":
        import bridge
        require(not args.output_dir.exists(), "Audit destination exists")
        result, _ = bridge.audit(args.workspace, args.parent_search)
        fresh_directory(args.output_dir)
        write_json(args.output_dir / "program005-audit.json", result)
    elif args.stage == "prepare-screen":
        result = prepare(args)
    else:
        result = score(args)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()