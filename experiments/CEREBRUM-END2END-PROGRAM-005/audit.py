"""Read-only antecedent audit and exclusion reconstruction; never confirmation."""
import subprocess
import sys
from pathlib import Path
from collections import Counter

from core import (PREDECESSOR, dependencies, cfg, read, rows, file_hash,
                  object_hash, pinned_bytes, parse, canonical, digest)

SELECTION = "sha256:5889ca88fa777f5b6f9020f94c91c201427794741db7e2e47788bf80d8a9acce"


def audit(directory):
    directory = Path(directory)
    selection = read(directory / "selection.json")
    if file_hash(directory / "selection.json") != SELECTION:
        raise ValueError("not the audited Program-004 selection")
    if selection["status"] != "DEVELOPMENT_HOLD" or selection["confirmation_accessed"]:
        raise ValueError("antecedent disposition differs")
    reg = parse(pinned_bytes(PREDECESSOR / "registration.json", cfg()["predecessor_registration_sha256"]))
    inputs = directory / "development (2).jsonl"
    if file_hash(inputs) != reg["data"]["prepared/development.jsonl"]:
        raise ValueError("audited development input differs")
    values = rows(inputs)
    _, _, _, evaluator, _ = dependencies()
    scores = {}
    inputs_bound = {inputs.name: file_hash(inputs), "selection.json": SELECTION}
    for arm in ("ordinary", "boundary", "parent"):
        path = directory / f"development-{arm}-score.json"
        score = read(path)
        if object_hash(score) != selection["score_hashes"][arm]:
            raise ValueError("antecedent score binding differs: " + arm)
        inputs_bound[path.name] = file_hash(path)
        scores[arm] = score
        if arm == "parent":
            continue  # No parent raw predictions were provided: never claim this replay.
        path = directory / f"development-{arm}-predictions.jsonl"
        if file_hash(path) != score["prediction_sha256"]:
            raise ValueError("antecedent predictions differ: " + arm)
        inputs_bound[path.name] = file_hash(path)
        replay = evaluator.score(values, rows(path), "trace", "development")
        # Compare every inherited metric/diagnostic, excluding the successor identity.
        for key, value in replay.items():
            if key in ("protocol_id", "arm"):
                continue
            if value != score[key]:
                raise ValueError("antecedent score replay differs: " + arm + "/" + key)
    boundary = scores["boundary"]
    trace = {e["case_id"]: e for e in boundary["trace_diagnostics"]}
    counts = Counter(e["mechanism"] for e in boundary["evaluations"]
                     if trace[e["case_id"]]["raw_claim_unsafe_authorization"])
    return {"source_files": inputs_bound, "parent_raw_replayed": False,
            "ordinary_and_boundary_inherited_scores_replayed": True,
            "status": selection["status"], "boundary_unsafe_by_mechanism": dict(counts),
            "score_hashes": selection["score_hashes"], "confirmation_accessed": False,
            "usage": "DESIGN_EVIDENCE_ONLY_NOT_TRAINING_ROWS_OR_CONFIRMATION"}


def predecessor_exposures():
    """Isolated interpreter prevents predecessor module globals leaking into 005."""
    code = r'''
import importlib.util
from core import ROOT, PARENT, canonical, read, digest, dependencies
import data
dependencies()
spec = importlib.util.spec_from_file_location("exclusion003", PARENT / "prepare.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
old = []
for split in ("train", "development"):
    values, _ = module.generate_split(split, read(PARENT / "config.json"))
    payload = "".join(canonical(v) + "\n" for v in values).encode()
    if digest(payload) != read(PARENT / "registration.json")[split + "_sha256"]:
        raise ValueError("Program-003 reconstruction differs")
    old.extend(values)
deps = dependencies()
data.EXCLUDED.clear()
data.EXCLUDED.update(data.fingerprint(r) for r in old)
if sorted(data.EXCLUDED) != read(ROOT / "prepared/exclusions.json"):
    raise ValueError("Program-004 exclusions differ")
data.ACQUISITION_AUDITS.clear()
splits = data.generate("train", deps)
data.EXCLUDED.update(data.fingerprint(r) for vv in splits.values() for r in vv)
splits.update(data.generate("development", deps))
reg = read(ROOT / "registration.json")
qualification = read(ROOT / "prepared/qualification.json")
if data.validate_splits(splits, old) != qualification["splits"]:
    raise ValueError("Program-004 split qualification differs")
if data.ACQUISITION_AUDITS != qualification["acquisition_audits"]:
    raise ValueError("Program-004 acquisition audit differs")
for name, values in splits.items():
    payload = "".join(canonical(v) + "\n" for v in values).encode()
    if digest(payload) != reg["data"]["prepared/" + name + ".jsonl"]:
        raise ValueError("Program-004 data reconstruction differs: " + name)
    for value in values:
        print(canonical(value))
'''
    reg = parse(pinned_bytes(PREDECESSOR / "registration.json", cfg()["predecessor_registration_sha256"]))
    for name in ("prepared/exclusions.json", "prepared/qualification.json"):
        pinned_bytes(PREDECESSOR / name, reg["data"][name])
    result = subprocess.run([sys.executable, "-B", "-c", code], cwd=PREDECESSOR,
                            capture_output=True, text=True, encoding="utf-8")
    if result.returncode:
        raise ValueError("read-only predecessor reconstruction failed: " + result.stderr)
    return [parse(line) for line in result.stdout.splitlines()]