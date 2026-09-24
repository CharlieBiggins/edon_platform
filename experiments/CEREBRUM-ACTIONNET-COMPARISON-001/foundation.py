"""Strict read-only validation and exclusive publication. No model/network imports."""
import hashlib
import json
import math
from pathlib import Path, PurePosixPath, PureWindowsPath
import re

ID = "CEREBRUM-ACTIONNET-COMPARISON-001"
PROGRAM005 = "CEREBRUM-END2END-PROGRAM-005"
REG005 = "sha256:ccbfa43e14dd6138ea3e08dfc9c65b81a34be7aa4ec867bf03d8ad99a7cf2629"
PARENT = "sha256:5727b95576d13a2a1ffb54ddd5d3d376d9dcd57494e9834733e167aaacad8171"
VERIFIER = "sha256:fb44e06abdeff8ebcb7b1d89c4e0d801889189e9de88c09b50939179172df495"
CONDITIONS = ("base", "parent", "ordinary", "targeted", "open_weight_alternative")
DECISIONS = {"ALLOW", "DENY", "ABSTAIN", "CONTESTED", "INVALID"}
RULES = ("EVIDENCE_RECEIPT_CLOCK", "APPEAL_RESOLUTION_CLOCK", "POLICY_EVENT_EFFECT",
         "REVOCATION_PRIORITY", "APPROVAL_RESTORATION_CLOCK", "EVIDENCE_AVAILABILITY_PREDICATE")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def pairs(items):
    out = {}
    for key, value in items:
        require(key not in out, "Duplicate JSON key: " + key)
        out[key] = value
    return out


def finite_float(text):
    value = float(text)
    require(math.isfinite(value), "Nonfinite JSON number")
    return value


def reject(text):
    raise ValueError("Invalid JSON constant: " + text)


def parse(payload):
    return json.loads(payload, object_pairs_hook=pairs, parse_constant=reject, parse_float=finite_float)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(payload):
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def object_hash(value):
    return digest(canonical(value).encode())


def read(path):
    return parse(Path(path).read_bytes())


def rows(path):
    payload = Path(path).read_bytes()
    require(bool(payload) and payload.endswith(b"\n"), "JSONL must be complete and newline terminated")
    lines = payload.splitlines()
    require(all(line.strip() for line in lines), "Blank JSONL record")
    values = [parse(line) for line in lines]
    ids = [v["case_id"] for v in values]
    require(all(isinstance(x, str) and x for x in ids), "Invalid case ID")
    require(len(ids) == len(set(ids)), "Duplicate case IDs")
    return values


def relative(path):
    p = Path(path)
    require(not p.is_absolute() and not PureWindowsPath(str(path)).drive, "Use relative paths")
    return p


def safe_name(name):
    p = PurePosixPath(name)
    require(bool(name) and str(p) == name and not p.is_absolute() and ".." not in p.parts
            and not PureWindowsPath(name).drive and "\\" not in name, "Unsafe manifest path")
    return name


def no_links(path):
    path = Path(path)
    require(not any(p.is_symlink() for p in (path, *path.parents)), "Symlink path forbidden")
    if path.is_dir():
        require(not any(p.is_symlink() for p in path.rglob("*")), "Symlink in tree")


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def inventory(directory):
    no_links(directory)
    return {p.relative_to(directory).as_posix(): file_hash(p)
            for p in sorted(Path(directory).rglob("*")) if p.is_file()}


def pinned(path, expected):
    payload = Path(path).read_bytes()
    # Prism source exports sometimes omit one final LF. Never normalize run data.
    require(digest(payload) == expected or digest(payload + b"\n") == expected,
            "Frozen source mismatch: " + str(path))
    return payload


def source_closure(workspace):
    no_links(workspace)
    experiments = Path(workspace) / "edon/experiments"
    root = experiments / PROGRAM005
    reg = parse(pinned(root / "registration.json", REG005))
    require(reg["protocol_id"] == PROGRAM005 and reg["parent_adapter_sha256"] == PARENT,
            "Program005 identity mismatch")
    paths = [root / "registration.json"]
    for base, mapping in ((root, reg["sources"]), (experiments, reg["inherited_sources"])):
        for name, expected in mapping.items():
            p = base / safe_name(name)
            pinned(p, expected)
            paths.append(p)
    return root, {p.relative_to(workspace).as_posix(): file_hash(p) for p in paths}


def write_json(path, value):
    with Path(path).open("xb") as stream:
        stream.write((canonical(value) + "\n").encode())


def write_rows(path, values):
    with Path(path).open("xb") as stream:
        stream.write("".join(canonical(v) + "\n" for v in values).encode())


def validate_contract(c):
    require(c["version"] == 1 and c["candidate_configuration_frozen"] is True
            and c["human_approval_to_register_screen"] is True, "Candidate/registration approval unresolved")
    for field in ("model_id", "license_review", "selection_rationale_before_results"):
        require(isinstance(c["alternative"][field], str) and c["alternative"][field].strip(),
                "Alternative baseline choice unresolved: " + field)
    require(re.fullmatch(r"[0-9a-f]{40}", c["alternative"]["revision"] or ""), "Pin alternative commit revision")
    for value in (c["alternative"]["weights_tree_sha256"], c["interface"]["prompt_pack_sha256"],
                  c["interface"]["runner_source_sha256"], c["interface"]["runtime_lock_sha256"]):
        require(isinstance(value, str) and re.fullmatch(r"sha256:[0-9a-f]{64}", value), "Unresolved content hash")
    i = c["interface"]
    require(i["output_format"] == "INHERITED_PROGRAM003_TRACE_AND_NATIVE_PROGRAM"
            and i["hardware_class"] == "NVIDIA L4" and i["max_input_tokens"] == 4096
            and i["max_new_tokens"] == 4096 and i["do_sample"] is False and i["retries"] == 0
            and i["tools_during_generation"] == [] and i["reference_ir_visible"] is False,
            "Interface differs from reserved screen")
    require(c["budget"]["max_responses"] == 240, "Screen requires all 240 responses")
    for key in ("max_gpu_hours", "max_cost_usd"):
        value = c["budget"][key]
        require(type(value) in (int, float) and math.isfinite(value) and value > 0, "Set a positive budget: " + key)
    require(isinstance(c["screening_justification"], str) and c["screening_justification"].strip(),
            "Explain the decision this additional screen will inform")


def validate_cases(values, fingerprint, excluded):
    from collections import Counter, defaultdict
    require(len(values) == 48, "Screen must have 48 complete cases")
    require(len({v["case_id"] for v in values}) == 48, "Duplicate cases")
    require(Counter(v["stratum"] for v in values) == {"ordinary": 24, "boundary": 24}, "Stratum mismatch")
    decisions = Counter(v["compiler_input"]["oracle_certificate"]["decision"] for v in values)
    require(set(decisions) == DECISIONS, "All five decision classes must be present")
    groups = defaultdict(list)
    seen = {}
    for row in values:
        pair = row["counterfactual_pair_id"]
        fp = fingerprint(row)
        require(fp not in excluded, "Historical source overlap")
        require(fp not in seen or seen[fp] == pair, "Structural duplicate across pairs")
        seen[fp] = pair
        groups[pair].append(row)
    counts = Counter()
    for pair in groups.values():
        require(len(pair) == 2 and pair[0]["stratum"] == pair[1]["stratum"], "Broken counterfactual pair")
        if pair[0]["stratum"] == "boundary":
            rule = pair[0]["contrast_rule"]
            require(rule == pair[1]["contrast_rule"] and rule in RULES, "Invalid targeted rule")
            require(sum(v["compiler_input"]["oracle_certificate"]["decision"] == "ALLOW" for v in pair) == 1,
                    "Target pair needs one ALLOW and one non-ALLOW")
            counts[rule] += 1
    require(counts == {r: 2 for r in RULES}, "Each targeted rule needs two whole pairs")
    return {"records": 48, "pairs": len(groups), "decision_counts": dict(decisions),
            "targeted_pairs": dict(counts), "independent_transfer": False,
            "coverage_claim": "Six targeted rules plus 24 ordinary cases; not 18-mechanism qualification"}