"""Restore a Prism export to a NEW workspace against the original frozen hashes.

CPU only. Never calls prepare/freeze or materializes confirmation. This transport
helper lives outside the registered experiment sources and is not a new protocol.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import zipfile

REGISTRATION = "sha256:b741af32d0953e76e27273db0518272e8864c8f98899aa1c4bb952ae9f623857"
PREFIX = "edon/experiments/"
EXPERIMENT = PREFIX + "CEREBRUM-END2END-PROGRAM-004/"
PARENT = PREFIX + "CEREBRUM-END2END-PROGRAM-003/"
REGENERABLE = {"prepared/" + n + ".jsonl" for n in
               ("train-ordinary", "train-boundary", "development")}


def digest(payload):
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def pinned(payload, expected, name):
    if digest(payload) == expected:
        return payload
    if digest(payload + b"\n") == expected:
        return payload + b"\n"
    raise ValueError("Frozen hash mismatch: " + name)


def safe_name(name):
    p = PurePosixPath(name)
    if p.is_absolute() or ".." in p.parts or "\\" in name or str(p) != name:
        raise ValueError("Unsafe registered path: " + name)
    return name


def collect(archive):
    """Only allowlisted, hash-verified members are ever extracted or executed."""
    with zipfile.ZipFile(archive) as z:
        members = z.infolist()

        def get(name, expected, optional=False):
            safe_name(name)
            matches = [m for m in members if m.filename == name
                       or m.filename.endswith("/" + name)]
            if not matches and optional:
                return None
            if len(matches) != 1:
                raise ValueError("Missing or ambiguous ZIP member: " + name)
            m = matches[0]
            if (m.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError("Symlink ZIP member: " + name)
            return pinned(z.read(m), expected, name)

        registration = get(EXPERIMENT + "registration.json", REGISTRATION)
        reg = json.loads(registration)
        output = {EXPERIMENT + "registration.json": registration}
        for name, expected in reg["sources"].items():
            output[EXPERIMENT + safe_name(name)] = get(EXPERIMENT + name, expected)
        config = json.loads(output[EXPERIMENT + "config.json"])
        output[PARENT + "registration.json"] = get(
            PARENT + "registration.json", config["parent_registration_sha256"])
        for name, expected in reg["inherited_sources"].items():
            output[PREFIX + safe_name(name)] = get(PREFIX + name, expected)
        for name, expected in reg["data"].items():
            payload = get(EXPERIMENT + safe_name(name), expected, name in REGENERABLE)
            if payload is not None:
                output[EXPERIMENT + name] = payload
        if not REGENERABLE <= set(reg["data"]):
            raise ValueError("Registration does not bind all reconstruction outputs")
        return output


RECONSTRUCT = r"""
import importlib.util
from core import ROOT, PARENT, canonical, dependencies, digest, read, verify, write_once
import data

reg = read(ROOT / "registration.json")
assert not (ROOT / "results/confirmation-access.json").exists()
assert not (ROOT / "prepared/confirmation.jsonl").exists()
dependencies()
spec = importlib.util.spec_from_file_location("parent003_prepare", PARENT / "prepare.py")
old_prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old_prepare)
old = []
for split in ("train", "development"):
    values, _ = old_prepare.generate_split(split, read(PARENT / "config.json"))
    payload = "".join(canonical(v) + "\n" for v in values).encode()
    assert digest(payload) == read(PARENT / "registration.json")[split + "_sha256"], split
    old.extend(values)
print("PARENT TRAIN/DEVELOPMENT RECONSTRUCTION: VERIFIED", flush=True)
deps = dependencies()
data.ACQUISITION_AUDITS.clear()
data.EXCLUDED.clear()
data.EXCLUDED.update(data.fingerprint(r) for r in old)
assert sorted(data.EXCLUDED) == read(ROOT / "prepared/exclusions.json")
splits = data.generate("train", deps)
data.EXCLUDED.update(data.fingerprint(r) for values in splits.values() for r in values)
splits.update(data.generate("development", deps))
report = data.validate_splits(splits, old)
qualification = read(ROOT / "prepared/qualification.json")
assert report == qualification["splits"]
assert data.ACQUISITION_AUDITS == qualification["acquisition_audits"]
pending = {}
for name, values in splits.items():
    relative = "prepared/" + name + ".jsonl"
    payload = "".join(canonical(v) + "\n" for v in values).encode()
    assert digest(payload) == reg["data"][relative], relative + " reconstruction mismatch"
    pending[relative] = payload
for relative, payload in pending.items():
    write_once(ROOT / relative, payload)
    print("REGISTERED DATA RESTORED: " + relative, flush=True)
verify()
assert not (ROOT / "prepared/confirmation.jsonl").exists()
print("ORIGINAL REGISTRATION VERIFIED; CONFIRMATION UNTOUCHED", flush=True)
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    if args.archive.is_absolute() or args.destination.is_absolute():
        parser.error("Use relative archive and destination paths")
    if args.destination.exists():
        parser.error("Destination already exists; choose a NEW workspace, never overwrite a run")
    files = collect(args.archive)
    print("REGISTERED SOURCES AND AVAILABLE DATA: VERIFIED", flush=True)
    args.destination.mkdir(parents=True, exist_ok=False)
    for name, payload in files.items():
        target = args.destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as f:
            f.write(payload)
    experiment = args.destination / EXPERIMENT
    subprocess.run([sys.executable, "-B", "-u", "-c", RECONSTRUCT], cwd=experiment, check=True)
    subprocess.run([sys.executable, "-B", "run.py", "preflight"], cwd=experiment, check=True)
    print("RESTORE COMPLETE — no GPU work, training, or confirmation started")


if __name__ == "__main__":
    main()