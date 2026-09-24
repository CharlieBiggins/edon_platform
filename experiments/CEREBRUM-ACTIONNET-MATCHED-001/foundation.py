"""Strict local integrity, study validation, and immutable publication helpers."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path, PurePosixPath, PureWindowsPath
import re

ID = "CEREBRUM-ACTIONNET-MATCHED-001"
PROGRAM005 = "CEREBRUM-END2END-PROGRAM-005"
PROGRAM005_REGISTRATION = "sha256:ccbfa43e14dd6138ea3e08dfc9c65b81a34be7aa4ec867bf03d8ad99a7cf2629"
ARMS = ("ordinary", "actionnet")
DECISIONS = {"ALLOW", "DENY", "ABSTAIN", "CONTESTED", "INVALID"}
RULES = (
    "EVIDENCE_RECEIPT_CLOCK", "APPEAL_RESOLUTION_CLOCK", "POLICY_EVENT_EFFECT",
    "REVOCATION_PRIORITY", "APPROVAL_RESTORATION_CLOCK", "EVIDENCE_AVAILABILITY_PREDICATE",
)
SHA256 = re.compile(r"sha256:[0-9a-f]{64}\Z")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique_pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, "Duplicate JSON key: " + key)
        result[key] = value
    return result


def finite_float(text):
    value = float(text)
    require(math.isfinite(value), "Nonfinite JSON number")
    return value


def reject_constant(text):
    raise ValueError("Invalid JSON constant: " + text)


def parse(payload):
    if isinstance(payload, bytes):
        payload = payload.decode("utf-8")
    return json.loads(payload, object_pairs_hook=unique_pairs,
                      parse_constant=reject_constant, parse_float=finite_float)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def digest(payload):
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def object_hash(value):
    return digest(canonical(value).encode())


def read(path):
    return parse(Path(path).read_bytes())


def rows(path, id_field=None):
    payload = Path(path).read_bytes()
    require(payload and payload.endswith(b"\n"), "JSONL must be nonempty and newline terminated: " + str(path))
    lines = payload.splitlines()
    require(all(line.strip() for line in lines), "Blank JSONL row: " + str(path))
    values = [parse(line) for line in lines]
    if id_field:
        ids = [value[id_field] for value in values]
        require(all(isinstance(value, str) and value for value in ids), "Invalid row identifier")
        require(len(ids) == len(set(ids)), "Duplicate row identifier")
    return values


def relative(path):
    path = Path(path)
    require(not path.is_absolute() and not PureWindowsPath(str(path)).drive, "Use relative paths")
    return path


def safe_name(name):
    path = PurePosixPath(name)
    require(bool(name) and str(path) == name and not path.is_absolute()
            and ".." not in path.parts and "\\" not in name
            and not PureWindowsPath(name).drive, "Unsafe manifest path: " + name)
    return name


def no_links(path):
    path = Path(path)
    require(not path.is_symlink(), "Symlink path forbidden: " + str(path))
    if path.exists():
        require(not any(value.is_symlink() for value in path.rglob("*")),
                "Symlink inside tree: " + str(path))


def file_hash(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return "sha256:" + value.hexdigest()


def inventory(directory):
    directory = Path(directory)
    require(directory.is_dir(), "Directory missing: " + str(directory))
    no_links(directory)
    return {path.relative_to(directory).as_posix(): file_hash(path)
            for path in sorted(directory.rglob("*")) if path.is_file()}


def tree_hash(directory):
    values = inventory(directory)
    require(values, "Empty directory: " + str(directory))
    return object_hash(values)


def snapshot_hashes(directory):
    """Hash executable model and tokenizer content separately; ignore prose/cache metadata."""
    values = inventory(directory)
    model, tokenizer = {}, {}
    model_names = {"config.json", "generation_config.json", "model.safetensors.index.json",
                   "pytorch_model.bin.index.json"}
    tokenizer_prefixes = ("tokenizer", "vocab", "merges", "added_tokens", "special_tokens", "chat_template")
    for name, value in values.items():
        base = PurePosixPath(name).name
        if (base in model_names or base.endswith((".safetensors", ".bin"))
                and not base.startswith(tokenizer_prefixes)):
            model[name] = value
        if base.startswith(tokenizer_prefixes) or base in {"spiece.model", "sentencepiece.bpe.model"}:
            tokenizer[name] = value
    require(any(name.endswith((".safetensors", ".bin")) for name in model),
            "Base snapshot has no model weights")
    require(tokenizer, "Base snapshot has no tokenizer files")
    return {"weights_tree_sha256": object_hash(model),
            "tokenizer_tree_sha256": object_hash(tokenizer),
            "model_files": sorted(model), "tokenizer_files": sorted(tokenizer)}


def pinned_payload(path, expected):
    payload = Path(path).read_bytes()
    require(digest(payload) == expected or digest(payload + b"\n") == expected,
            "Pinned source mismatch: " + str(path))
    return payload if digest(payload) == expected else payload + b"\n"


def inherited_source_closure(experiments):
    experiments = Path(experiments)
    root = experiments / PROGRAM005
    registration = parse(pinned_payload(root / "registration.json", PROGRAM005_REGISTRATION))
    require(registration["protocol_id"] == PROGRAM005
            and registration["confirmation_materialized"] is False,
            "Program-005 registration identity differs")
    result = {PROGRAM005 + "/registration.json": PROGRAM005_REGISTRATION}
    for base, prefix, mapping in (
        (root, PROGRAM005 + "/", registration["sources"]),
        (experiments, "", registration["inherited_sources"]),
    ):
        for name, expected in mapping.items():
            pinned_payload(base / safe_name(name), expected)
            result[prefix + name] = expected
    return result


def write_bytes(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(payload)


def write_json(path, value):
    write_bytes(path, (canonical(value) + "\n").encode())


def write_rows(path, values):
    write_bytes(path, "".join(canonical(value) + "\n" for value in values).encode())


def fresh_directory(path):
    path = Path(path)
    require(not path.exists() and not path.is_symlink(), "Destination exists; choose a new directory")
    path.mkdir(parents=True, exist_ok=False)


def protect_output(output, *inputs):
    destination = Path(output).resolve()
    for value in inputs:
        source = Path(value).resolve()
        require(destination != source and source not in destination.parents,
                "Output must be outside source/input directories")


def load_config(root):
    value = read(Path(root) / "config.json")
    require(value["protocol_id"] == ID and value["arms"] == list(ARMS), "Framework identity differs")
    require(value["status"] == "IMPLEMENTED_DRAFT_NOT_REGISTERED"
            and value["stage"] == "A_DEVELOPMENT_SCREEN", "Framework stage differs")
    require(value["fresh_adapter_from_base"] is True and value["parent_adapter"] is None,
            "Matched-001 must use fresh adapters from base")
    require(value["training_records"] == value["training_ordinary_records"] + value["training_targeted_records"] == 384,
            "Training scenario budget differs")
    require(value["screen_records"] == value["screen_ordinary_records"] + value["screen_targeted_records"] == 24,
            "Screen budget differs")
    require(value["per_device_train_batch_size"] == value["gradient_accumulation_steps"] == 1
            and value["lr_scheduler_type"] == "constant" and value["warmup_steps"] == 0,
            "Registered exact-token training schedule differs")
    require(value["development_only"] is True and all(value[key] is False for key in
            ("confirmation_authorized", "transfer_authorized", "binding_authority")),
            "Authority boundary differs")
    return value


def _positive_number(value, name):
    require(type(value) in (int, float) and math.isfinite(value) and value > 0,
            "Set a positive value: " + name)


def validate_study(study, config, stage="draft"):
    require(study["schema_version"] == 1 and study["stage"] == "A_DEVELOPMENT_SCREEN",
            "Study schema/stage differs")
    require(study["training_seed_label"] in config["seed_pairs"],
            "Training seed label differs")
    require(study["comparison001_disposition"] in {"UNEXECUTED_OPTIONAL", "EXECUTED_FROZEN"},
            "Invalid Comparison-001 disposition")
    screen = study["screen"]
    require((screen["records"], screen["responses"]) == (24, 48), "Screen response budget differs")
    require(type(screen["paired_cluster_bootstrap_repetitions"]) is int
            and screen["paired_cluster_bootstrap_repetitions"] >= 1000,
            "Insufficient registered bootstrap repetitions")
    require(0 < screen["confidence_level"] < 1, "Invalid confidence level")
    gates = screen["gates"]
    required_gates = {"parse_valid_floor", "event_order_floor", "partition_floor",
        "executed_state_floor", "decision_floor", "program_exact_floor",
        "program_exact_advantage_floor", "clear_loss_delta_ceiling",
        "ordinary_retention_delta_floor", "unsafe_authorization_ceiling",
        "raw_unsafe_authorization_ceiling", "unexamined_claim_ceiling",
        "generation_limit_hit_ceiling"}
    require(set(gates) == required_gates, "Screen gate inventory differs")
    for name in ("parse_valid_floor", "event_order_floor", "partition_floor",
                 "executed_state_floor", "decision_floor", "program_exact_floor"):
        require(type(gates[name]) in (int, float) and 0 <= gates[name] <= 1, "Invalid floor: " + name)
    require(0 < gates["program_exact_advantage_floor"] <= 1
            and -1 <= gates["clear_loss_delta_ceiling"] < 0
            and -1 <= gates["ordinary_retention_delta_floor"] <= 0,
            "Invalid comparative gate")
    for name in ("unsafe_authorization_ceiling", "raw_unsafe_authorization_ceiling",
                 "unexamined_claim_ceiling", "generation_limit_hit_ceiling"):
        require(type(gates[name]) is int and gates[name] >= 0, "Invalid count ceiling: " + name)
    execution = study["execution"]
    require(execution["do_sample"] is False and execution["retries"] == 0
            and execution["tools"] == [] and execution["reference_answers_visible"] is False,
            "Inference interface is not the registered fair interface")
    if stage == "draft":
        return study
    require(isinstance(study["comparison001_decision_rationale"], str)
            and study["comparison001_decision_rationale"].strip(),
            "Document why optional Comparison-001 is run or skipped")
    require(isinstance(study["program005_audit_sha256"], str)
            and SHA256.fullmatch(study["program005_audit_sha256"])
            and study["program005_disposition_acknowledged"] is True,
            "Program-005 audit/disposition unresolved")
    base = study["base_snapshot"]
    require(base["model_id"] == config["model_name"] and base["revision"] == config["model_revision"],
            "Base identity differs")
    for name in ("weights_tree_sha256", "tokenizer_tree_sha256"):
        require(isinstance(base[name], str) and SHA256.fullmatch(base[name]), "Base snapshot hash unresolved: " + name)
    require(isinstance(base["license_review"], str) and base["license_review"].strip(),
            "Base license review unresolved")
    budget = study["training_budget"]
    require(type(budget["processed_nonpadding_tokens_per_arm"]) is int
            and budget["processed_nonpadding_tokens_per_arm"] > 0,
            "Training token budget unresolved")
    require(type(budget["maximum_realized_arm_difference_tokens"]) is int
            and budget["maximum_realized_arm_difference_tokens"] >= 0,
            "Token matching tolerance unresolved")
    require(budget["stop_before_incomplete_pair_group"] is True, "Partial pair groups forbidden")
    for name in ("maximum_gpu_hours_per_run", "maximum_total_gpu_hours", "gpu_hourly_price_usd",
                 "maximum_cost_usd_per_run", "maximum_total_cost_usd"):
        _positive_number(budget[name], name)
    require(budget["maximum_total_gpu_hours"] >= 2 * budget["maximum_gpu_hours_per_run"]
            and budget["maximum_total_cost_usd"] >= 2 * budget["maximum_cost_usd_per_run"],
            "Total A-stage cap cannot cover two registered runs")
    require(study["human_approval_to_register"] is True
            and study["claim_boundary_acknowledged"] is True,
            "Registration/claim-boundary approval unresolved")
    if stage == "paid":
        require(execution["paid_execution_approved"] is True
                and isinstance(execution["approval_identity"], str) and execution["approval_identity"].strip()
                and re.fullmatch(r"20[0-9]{2}-[0-9]{2}-[0-9]{2}", execution["approval_date"] or ""),
                "Paid execution approval unresolved")
    return study


def validate_program005_audit(path, study):
    require(file_hash(path) == study["program005_audit_sha256"], "Program-005 audit hash differs")
    value = read(path)
    require(value["status"] == "PROGRAM005_COMPLETE_RESULT_REPLAYED"
            and value["program005_status"] in {"DEVELOPMENT_HOLD", "SCREEN_SUPPORTS_LARGER_EVALUATION"},
            "Program-005 audit is incomplete or invalid")
    require(value["paid_execution_authorized"] is False
            and value["transfer_authorized"] is False and value["binding_authority"] is False,
            "Program-005 audit authority differs")
    require(set(value["adapters"]) == {"ordinary", "repair", "parent"}
            and set(value["score_hashes"]) == {"ordinary", "repair", "parent"},
            "Program-005 audit evidence inventory differs")
    return value


def validate_execution_approval(approval, run_dir, study):
    run_dir = Path(run_dir)
    require(approval["schema_version"] == 1 and approval["protocol_id"] == ID,
            "Execution approval identity differs")
    require(approval["registration_sha256"] == file_hash(run_dir / "registration.json")
            and approval["study_sha256"] == file_hash(run_dir / "study.json"),
            "Execution approval binding differs")
    budget = study["training_budget"]
    for name in ("maximum_gpu_hours_per_run", "maximum_total_gpu_hours", "gpu_hourly_price_usd",
                 "maximum_cost_usd_per_run", "maximum_total_cost_usd"):
        require(approval[name] == budget[name], "Execution approval budget differs: " + name)
    require(approval["scope"] == "MATCHED001_RUNTIME_TRAIN_BOTH_ARMS_AND_OPTIONAL_24_CASE_SCREEN_FOR_DECLARED_SEED_ONLY",
            "Execution approval scope differs")
    require(approval["paid_execution_approved"] is True
            and isinstance(approval["approval_identity"], str) and approval["approval_identity"].strip()
            and re.fullmatch(r"20[0-9]{2}-[0-9]{2}-[0-9]{2}", approval["approval_date"] or ""),
            "Paid execution approval unresolved")
    return approval


def validate_billing_receipt(receipt, run_dir, study):
    run_dir = Path(run_dir)
    require(receipt["schema_version"] == 1 and receipt["protocol_id"] == ID
            and receipt["registration_sha256"] == file_hash(run_dir / "registration.json"),
            "Billing receipt identity/binding differs")
    require(receipt["provider"] in {"Modal", "Lightning AI"}
            and isinstance(receipt["account_profile"], str) and receipt["account_profile"].strip(),
            "Billing provider/account unresolved")
    require(receipt["included_stages"] == ["runtime", "train-ordinary", "train-actionnet",
            "predict-ordinary", "predict-actionnet"], "Billing stage inventory differs")
    for name in ("actual_gpu_hours", "actual_cost_usd"):
        require(type(receipt[name]) in (int, float) and math.isfinite(receipt[name]) and receipt[name] >= 0,
                "Invalid actual billing value: " + name)
    budget = study["training_budget"]
    require(receipt["actual_gpu_hours"] <= budget["maximum_total_gpu_hours"]
            and receipt["actual_cost_usd"] <= budget["maximum_total_cost_usd"],
            "Actual provider bill exceeds registered total cap")
    require(isinstance(receipt["provider_evidence_sha256"], str)
            and SHA256.fullmatch(receipt["provider_evidence_sha256"]), "Provider billing evidence hash unresolved")
    require(receipt["provider_billing_attested"] is True
            and isinstance(receipt["reported_by"], str) and receipt["reported_by"].strip()
            and re.fullmatch(r"20[0-9]{2}-[0-9]{2}-[0-9]{2}", receipt["reported_date"] or ""),
            "Provider billing attestation unresolved")
    return receipt


def framework_sources(root):
    root = Path(root)
    paths = [*root.glob("*.py"), *root.glob("*.json"), *root.glob("*.md"), *root.glob("tests/*.py")]
    return {path.relative_to(root).as_posix(): file_hash(path) for path in sorted(paths)}