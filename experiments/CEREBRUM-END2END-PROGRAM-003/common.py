"""Bounded Program-002 paths, frozen dependencies and immutable evidence writes."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXPERIMENTS = ROOT.parent
LEGACY = EXPERIMENTS / "CEREBRUM-END2END-PROGRAM-001"
SOURCE = EXPERIMENTS / "ACTIONNET-DATA-QUAL-021-PROGRAM"
CONFIG = ROOT / "config.json"
PROTOCOL = "CEREBRUM-END2END-PROGRAM-003"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Import only definitions; never call the predecessor prepare/generate/run entrypoints.
sys.path.insert(0, str(LEGACY))
from program_common import IR  # noqa: E402
from prepare_data import prepare_row  # noqa: E402
from scoring import evaluate as legacy_evaluate, summarize  # noqa: E402


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(data):
    return "sha256:" + hashlib.sha256(data).hexdigest()


def file_hash(path):
    return digest(Path(path).read_bytes())


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_rows(path):
    rows = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    if len({row["case_id"] for row in rows}) != len(rows):
        raise ValueError("duplicate case identifiers")
    return rows


def immutable_bytes(path, data):
    """Existing evidence must match byte-for-byte, otherwise stop."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError(f"refusing to replace existing evidence: {path.name}")
    else:
        with path.open("xb") as handle:
            handle.write(data)


def write_json(path, value):
    immutable_bytes(path, (canonical(value) + "\n").encode())


def write_rows(path, rows):
    immutable_bytes(path, ("".join(canonical(row) + "\n" for row in rows)).encode())


def source_hashes():
    # The full inherited Python source chain is bound; no datasets are inspected.
    paths = list(ROOT.glob("*.py")) + list(ROOT.glob("*.md")) + [CONFIG]
    paths += list((ROOT / "tests").glob("*.py"))
    paths += list(LEGACY.glob("*.py"))
    for directory in EXPERIMENTS.glob("ACTIONNET-DATA-QUAL-*"):
        paths.extend(directory.glob("*.py"))
    return {str(p.relative_to(EXPERIMENTS)): file_hash(p) for p in sorted(paths)}


def config():
    value = read_json(CONFIG)
    if value["protocol_id"] != PROTOCOL or value["binding_authority"] or value["transfer_authorized"]:
        raise ValueError("invalid protocol identity/authority boundary")
    if value["parent_adapter"] is not None or not value["fresh_adapter_from_base"]:
        raise ValueError("both arms must start fresh from the base")
    if value["arms"] != ["uniform", "trace"]:
        raise ValueError("registered arms changed")
    if value["intervention"] != "EXPLICIT_EXECUTION_TRACE_SUPERVISION":
        raise ValueError("unexpected intervention")
    if value["training_records"] != value["splits"]["train"]["records"]:
        raise ValueError("training count mismatch")
    if value["max_steps"] * value["effective_batch_size"] != value["epochs"] * value["training_records"]:
        raise ValueError("training exposure mismatch")
    families = []
    for split in value["splits"].values():
        ids = set(range(split["family_start"], split["family_start"] + split["families"]))
        if min(ids) < 30000 or split["records"] != len(ids) * 8:
            raise ValueError("fresh family reservation or split count invalid")
        if any(ids & previous for previous in families):
            raise ValueError("family split overlap")
        families.append(ids)
    return value


def freeze():
    value = config()
    train = ROOT / "prepared/train.jsonl"
    development = ROOT / "prepared/development.jsonl"
    manifest = {
        "protocol_id": PROTOCOL, "sources": source_hashes(),
        "train_sha256": file_hash(train), "development_sha256": file_hash(development),
        "qualification_sha256": file_hash(ROOT / "prepared/qualification.json"),
        "confirmation_materialized": False,
        "training_steps_per_arm": value["max_steps"],
        "binding_authority": False, "transfer_authorized": False,
    }
    write_json(ROOT / "registration.json", manifest)
    return manifest


def verify_freeze():
    manifest = read_json(ROOT / "registration.json")
    if manifest["sources"] != source_hashes():
        raise ValueError("registered code/config changed; create a new protocol instead")
    for name in ("train", "development"):
        if manifest[f"{name}_sha256"] != file_hash(ROOT / f"prepared/{name}.jsonl"):
            raise ValueError(f"frozen {name} data changed")
    if manifest["qualification_sha256"] != file_hash(ROOT / "prepared/qualification.json"):
        raise ValueError("qualification changed")
    return manifest


def tree_hash(path):
    path = Path(path)
    files = sorted(p for p in path.rglob("*") if p.is_file())
    if not files:
        raise ValueError("empty adapter directory")
    return digest(canonical({str(p.relative_to(path)): file_hash(p) for p in files}).encode())