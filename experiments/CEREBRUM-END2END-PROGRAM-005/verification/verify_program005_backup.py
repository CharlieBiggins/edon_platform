"""Read-only Windows/Linux backup check. Standard library only; no model imports.

Does not score outputs, repair files, or establish source snapshot atomicity.
Training manifests bind child adapters internally; they are not external signatures.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath

REGISTRATION = "sha256:ccbfa43e14dd6138ea3e08dfc9c65b81a34be7aa4ec867bf03d8ad99a7cf2629"
PARENT_HASH = "sha256:5727b95576d13a2a1ffb54ddd5d3d376d9dcd57494e9834733e167aaacad8171"
EXPERIMENT = "CEREBRUM-END2END-PROGRAM-005"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def pairs(items):
    out = {}
    for k, v in items:
        require(k not in out, "Duplicate JSON key: " + k)
        out[k] = v
    return out


def reject_constant(value):
    raise ValueError("Nonfinite JSON: " + value)


def parse(payload):
    return json.loads(payload, object_pairs_hook=pairs, parse_constant=reject_constant)


def read(path):
    return parse(path.read_bytes())


def file_hash(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def object_hash(value):
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode()
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def tree_hash(directory):
    require((directory / "adapter_model.safetensors").is_file(), "Missing adapter weights: " + str(directory))
    paths = sorted(directory.rglob("*"))
    require(not any(p.is_symlink() for p in paths), "Adapter contains symlinks")
    return object_hash({p.relative_to(directory).as_posix(): file_hash(p)
                        for p in paths if p.is_file()})


def verify_files(base, mapping):
    for name, expected in mapping.items():
        p = PurePosixPath(name)
        require(bool(name) and str(p) == name and not p.is_absolute()
                and not PureWindowsPath(name).drive and ".." not in p.parts and "\\" not in name,
                "Unsafe registered path: " + name)
        require(file_hash(base / name) == expected, "Hash mismatch: " + str(base / name))


def prefix(path, ids):
    records = []
    partial = False
    for index, line in enumerate(lines := path.read_bytes().splitlines(keepends=True)):
        try:
            record = parse(line.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            require(index == len(lines) - 1, "Corrupt interior prediction: " + str(path))
            partial = True
            break
        require(isinstance(record, dict) and "case_id" in record, "Invalid prediction record")
        records.append(record)
    actual = [r["case_id"] for r in records]
    require(len(actual) <= len(ids) and actual == ids[:len(actual)] and len(set(actual)) == len(actual),
            "Prediction prefix mismatch: " + str(path))
    return records, partial


def verify(workspace, parent_search, require_parent_stage=False):
    require(workspace.is_dir() and parent_search.is_dir(), "Input directory missing")
    for directory in (workspace, parent_search):
        require(not directory.is_symlink(), "Input directory is a symlink")
        require(not any(p.is_symlink() for p in directory.rglob("*")), "Input contains symlinks")
    experiments = workspace / "edon/experiments"
    root = experiments / EXPERIMENT
    require(file_hash(root / "registration.json") == REGISTRATION, "Original registration hash differs")
    reg = read(root / "registration.json")
    require(reg["protocol_id"] == EXPERIMENT and reg["confirmation_materialized"] is False,
            "Registration identity or confirmation state differs")
    verify_files(root, reg["sources"])
    verify_files(root, reg["data"])
    verify_files(experiments, reg["inherited_sources"])
    require({p.relative_to(root).as_posix() for p in (root / "prepared").rglob("*")
             if p.is_file()} == set(reg["data"]), "Prepared data inventory differs")
    own = list(root.glob("*.py")) + list(root.glob("*.md")) + [root / "config.json"]
    own += list((root / "tests").glob("*.py"))
    require({p.relative_to(root).as_posix() for p in own} == set(reg["sources"]), "Unexpected root source files")
    config = read(root / "config.json")
    old = experiments / "CEREBRUM-END2END-PROGRAM-003"
    require(file_hash(old / "registration.json") == config["parent_registration_sha256"], "Parent registration differs")
    require(reg["parent_adapter_sha256"] == config["parent_adapter_sha256"] == PARENT_HASH, "Parent identity differs")
    require(not (root / "prepared/confirmation.jsonl").exists()
            and not (root / "results/confirmation-access.json").exists(), "Confirmation evidence exists; stop and report")
    print("REGISTRATION, SOURCES AND PREPARED DATA: VERIFIED", flush=True)

    candidates = sorted({p.parent for p in parent_search.rglob("adapter_model.safetensors")})
    matches = [p for p in candidates if tree_hash(p) == PARENT_HASH]
    require(len(matches) == 1, "Expected exactly one matching parent adapter; found " + str(len(matches)))
    print("ORIGINAL PARENT ADAPTER: VERIFIED", flush=True)
    print("PARENT_DIRECTORY=" + str(matches[0]), flush=True)

    runtime_path = root / "results/runtime-readiness.json"
    runtime = read(runtime_path)
    require(runtime["registration_sha256"] == REGISTRATION and runtime["parent_adapter_sha256"] == PARENT_HASH,
            "Runtime identity differs")
    require(runtime["packages"] == read(old / "config.json")["required_packages"], "Runtime package pins differ")
    require((runtime["torch"], runtime["cuda"], runtime["gpu"]) == ("2.8.0+cu129", "12.9", "NVIDIA L4"),
            "Runtime environment differs")
    require(runtime["loss_value_and_gradient_passed"] is True, "Missing runtime loss qualification")
    for name, count in (("train-ordinary", 384), ("train-repair", 384), ("development", 96)):
        d = runtime["datasets"][name]
        require(d["records"] == count and d["truncations"] == 0 and d["target_budget_violations"] == 0,
                "Runtime dataset qualification differs")
    runtime_hash = file_hash(runtime_path)
    adapters = {"parent": PARENT_HASH}
    for arm in ("ordinary", "repair"):
        directory = root / "artifacts" / arm
        m = read(directory / "training.json")
        binding = {"arm": arm, "registration_sha256": REGISTRATION,
                   "parent_adapter_sha256": PARENT_HASH, "runtime_sha256": runtime_hash,
                   "train_sha256": file_hash(root / "prepared" / ("train-" + arm + ".jsonl"))}
        require(m["binding"] == binding and read(directory / "start.json") == binding, "Training binding mismatch: " + arm)
        require(m["step"] == config["max_steps"] == 24, "Incomplete training: " + arm)
        adapters[arm] = tree_hash(directory / "adapter")
        require(adapters[arm] == m["adapter_sha256"], "Trained adapter mismatch: " + arm)
        print(arm.upper() + ": STEP 24 ADAPTER VERIFIED", flush=True)
        print("  " + adapters[arm], flush=True)

    input_path = root / "prepared/development.jsonl"
    ids = [parse(line)["case_id"] for line in input_path.read_bytes().splitlines() if line.strip()]
    require(len(ids) == 96 and len(set(ids)) == 96, "Development IDs invalid")
    summary = {}
    for arm in ("ordinary", "repair", "parent"):
        path = root / "results" / ("development-" + arm + "-predictions.jsonl")
        binding = {"arm": arm, "split": "development", "adapter_sha256": adapters[arm],
                   "registration_sha256": REGISTRATION, "input_sha256": file_hash(input_path),
                   "runtime_sha256": runtime_hash}
        bp = path.with_suffix(".binding.json")
        mp = path.with_suffix(".manifest.json")
        if bp.exists():
            require(read(bp) == binding, "Prediction binding mismatch: " + arm)
        records, partial = ([], False)
        if path.exists():
            require(bp.is_file(), "Prediction binding missing: " + arm)
            records, partial = prefix(path, ids)
        if mp.exists():
            require(path.is_file() and len(records) == len(ids) and not partial, "Incomplete completed predictions")
            require(read(mp) == {**binding, "predictions_sha256": file_hash(path), "count": len(ids)},
                    "Completed prediction manifest differs: " + arm)
        print(f"{arm.upper()}: {len(records)}/96 saved responses", flush=True)
        if partial:
            print("  Partial final line preserved unchanged; recovery belongs to the registered runner", flush=True)
        if path.exists():
            print("  predictions_sha256=" + file_hash(path), flush=True)
        summary[arm] = {"count": len(records), "partial_tail": partial,
                        "completed_manifest": mp.is_file()}
    if require_parent_stage:
        for arm in ("ordinary", "repair"):
            require(summary[arm] == {"count": 96, "partial_tail": False, "completed_manifest": True},
                    "Expected completed evaluation before parent stage: " + arm)
    if (root / "results/selection.json").exists():
        print("SELECTION FILE PRESENT: preserve it; this helper does not validate or interpret scores.", flush=True)
    print("LOCAL_BACKUP_CONTENT_VERIFIED — no files changed; no model scoring performed", flush=True)
    print("This checks bound content, not proof that every latest remote write was downloaded.", flush=True)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--parent-search", type=Path, required=True)
    parser.add_argument("--require-parent-stage", action="store_true",
                        help="Require both trained-arm evaluations to have completed manifests")
    args = parser.parse_args()
    require(not args.workspace.is_absolute() and not args.parent_search.is_absolute(), "Use relative input paths")
    verify(args.workspace, args.parent_search, args.require_parent_stage)


if __name__ == "__main__":
    main()