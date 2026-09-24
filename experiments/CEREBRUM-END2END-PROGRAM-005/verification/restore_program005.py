"""CPU-only recovery of a fresh Program-005 workspace from a Prism ZIP export.

Not a protocol change. Never calls prepare/freeze, trains, scores a model, or
materializes confirmation. Refuses existing destinations and exported 005 runs.
Only original-registration-allowlisted, hash-verified bytes can be executed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import zipfile

REGISTRATION = "sha256:ccbfa43e14dd6138ea3e08dfc9c65b81a34be7aa4ec867bf03d8ad99a7cf2629"
PARENT_HASH = "sha256:5727b95576d13a2a1ffb54ddd5d3d376d9dcd57494e9834733e167aaacad8171"
PREFIX = "edon/experiments/"
EXPERIMENT = PREFIX + "CEREBRUM-END2END-PROGRAM-005/"
REGENERABLE = {"prepared/" + name + ".jsonl" for name in
               ("train-ordinary", "train-repair", "development")}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(payload):
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def pinned(payload, expected, name):
    for candidate in (payload, payload + b"\n"):
        if digest(candidate) == expected:
            return candidate
    raise ValueError("Frozen hash mismatch: " + name)


def safe_name(name):
    p = PurePosixPath(name)
    require(bool(name) and not p.is_absolute() and ".." not in p.parts
            and "\\" not in name and str(p) == name,
            "Unsafe registered path: " + name)
    return name


def parent_hash(directory):
    require(directory.is_dir() and not directory.is_symlink(), "Parent directory missing or symlink")
    require((directory / "adapter_model.safetensors").is_file(), "Parent weights missing")
    paths = sorted(directory.rglob("*"))
    require(not any(p.is_symlink() for p in paths), "Parent adapter contains symlinks")
    files = {}
    for path in paths:
        if path.is_file():
            h = hashlib.sha256()
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024*1024), b""):
                    h.update(chunk)
            files[path.relative_to(directory).as_posix()] = "sha256:" + h.hexdigest()
    return digest(json.dumps(files, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False, allow_nan=False).encode())


def collect(archive):
    with zipfile.ZipFile(archive) as z:
        members = z.infolist()
        # This helper must never silently discard saved GPU progress from 005.
        for member in members:
            if not member.is_dir():
                for folder in ("results/", "artifacts/"):
                    marker = EXPERIMENT + folder
                    require(not (member.filename.startswith(marker) or "/" + marker in member.filename),
                            "Export contains Program-005 run state; use a progress backup, not fresh restore")

        def get(name, expected, optional=False):
            safe_name(name)
            matches = [m for m in members if m.filename == name or m.filename.endswith("/" + name)]
            if not matches and optional:
                return None
            require(len(matches) == 1, "Missing or ambiguous ZIP member: " + name)
            member = matches[0]
            require(not member.is_dir() and (member.external_attr >> 16) & 0o170000 != 0o120000,
                    "Directory or symlink ZIP member: " + name)
            return pinned(z.read(member), expected, name)

        registration = get(EXPERIMENT + "registration.json", REGISTRATION)
        reg = json.loads(registration)
        require(reg["protocol_id"] == "CEREBRUM-END2END-PROGRAM-005"
                and reg["parent_adapter_sha256"] == PARENT_HASH
                and reg["confirmation_materialized"] is False, "Registration identity differs")
        output = {EXPERIMENT + "registration.json": registration}
        for name, expected in reg["sources"].items():
            output[EXPERIMENT + safe_name(name)] = get(EXPERIMENT + name, expected)
        for name, expected in reg["inherited_sources"].items():
            output[PREFIX + safe_name(name)] = get(PREFIX + name, expected)
        require(REGENERABLE <= set(reg["data"]), "Registration does not bind reconstruction outputs")
        for name, expected in reg["data"].items():
            payload = get(EXPERIMENT + safe_name(name), expected, name in REGENERABLE)
            if payload is not None:
                output[EXPERIMENT + name] = payload
        return output


RECONSTRUCT = r'''
import importlib.util
from core import ROOT, PARENT, canonical, dependencies, digest, read, verify, write_once
from audit import predecessor_exposures
import data

def require(condition, message):
    if not condition:
        raise ValueError(message)

reg = read(ROOT / "registration.json")
require(not (ROOT / "results").exists(), "Fresh restore cannot contain results")
require(not (ROOT / "artifacts").exists(), "Fresh restore cannot contain artifacts")
require(not (ROOT / "prepared/confirmation.jsonl").exists(), "Confirmation forbidden")
dependencies()
spec = importlib.util.spec_from_file_location("restore_parent003", PARENT / "prepare.py")
old_prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old_prepare)
old = []
for split in ("train", "development"):
    values, _ = old_prepare.generate_split(split, read(PARENT / "config.json"))
    payload = "".join(canonical(v) + "\n" for v in values).encode()
    require(digest(payload) == read(PARENT / "registration.json")[split + "_sha256"],
            "Program-003 reconstruction differs: " + split)
    old.extend(values)
print("PROGRAM-003 TRAIN/DEVELOPMENT: HASH VERIFIED", flush=True)
old.extend(predecessor_exposures())
print("PROGRAM-004 TRAIN/DEVELOPMENT: HASH VERIFIED", flush=True)
deps = dependencies()
data.ACQUISITION_AUDITS.clear()
data.EXCLUDED.clear()
data.EXCLUDED.update(data.fingerprint(r) for r in old)
require(sorted(data.EXCLUDED) == read(ROOT / "prepared/exclusions.json"), "Exclusion set differs")
splits = data.generate("train", deps)
data.EXCLUDED.update(data.fingerprint(r) for values in splits.values() for r in values)
splits.update(data.generate("development", deps))
qualification = read(ROOT / "prepared/qualification.json")
require(data.validate_splits(splits, old) == qualification["splits"], "Split qualification differs")
require(data.ACQUISITION_AUDITS == qualification["acquisition_audits"], "Acquisition audit differs")
require(len(old) == qualification["predecessor_exposure_records_excluded"], "Exposure count differs")
for values in splits.values():
    for row in values:
        data.qualify_row(row, deps)
pending = {}
for name, values in splits.items():
    relative = "prepared/" + name + ".jsonl"
    payload = "".join(canonical(v) + "\n" for v in values).encode()
    require(digest(payload) == reg["data"][relative], "Reconstruction hash differs: " + relative)
    pending[relative] = payload
require(set(pending) == {"prepared/train-ordinary.jsonl", "prepared/train-repair.jsonl",
                         "prepared/development.jsonl"}, "Unexpected reconstruction outputs")
# Check ALL payload hashes before publishing any reconstructed data.
for name, payload in pending.items():
    write_once(ROOT / name, payload)
    print("REGISTERED DATA RESTORED: " + name, flush=True)
verify()
print("ORIGINAL PROGRAM-005 REGISTRATION VERIFIED; NO CONFIRMATION", flush=True)
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--parent", type=Path, help="Optional original adapter check; relative to caller")
    args = parser.parse_args()
    if any(p.is_absolute() for p in (args.archive, args.destination) if p is not None) or (
            args.parent is not None and args.parent.is_absolute()):
        parser.error("Use relative paths")
    if args.destination.exists() or args.destination.is_symlink():
        parser.error("Destination already exists; choose a NEW directory, never overwrite a run")
    files = collect(args.archive)
    if args.parent is not None:
        require(parent_hash(args.parent) == PARENT_HASH, "Original parent adapter hash differs")
        print("ORIGINAL PARENT ADAPTER: HASH VERIFIED (read-only)", flush=True)
    print("FROZEN SOURCES AND AVAILABLE DATA: HASH VERIFIED", flush=True)
    args.destination.mkdir(parents=True, exist_ok=False)
    for name, payload in files.items():
        target = args.destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(payload)
    experiment = args.destination / EXPERIMENT
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"}
    subprocess.run([sys.executable, "-B", "-u", "-c", RECONSTRUCT], cwd=experiment, env=env, check=True)
    subprocess.run([sys.executable, "-B", "run.py", "preflight"], cwd=experiment, env=env, check=True)
    print("CPU RESTORE COMPLETE — no GPU work, training, or confirmation started", flush=True)
    print("WORKSPACE=" + str(args.destination), flush=True)


if __name__ == "__main__":
    main()