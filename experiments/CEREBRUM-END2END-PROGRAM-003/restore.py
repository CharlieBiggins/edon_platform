"""Restore a trusted, hash-pinned handoff/project ZIP into a separate workspace.

Accepts only byte-exact sources or restoration of one stripped trailing LF whose
hash equals the registered original. Does not install packages or call Modal APIs.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import zipfile

RELATIVE = PurePosixPath("edon/experiments/CEREBRUM-END2END-PROGRAM-003")


def digest(data):
    return "sha256:" + hashlib.sha256(data).hexdigest()


def recover(data, expected):
    for candidate in (data, data + b"\n"):
        if digest(candidate) == expected:
            return candidate
    raise ValueError("bytes differ from trusted registration; do not bypass this check")


def restore(archive_path, destination, registration_sha256):
    destination = Path(destination)
    if destination.is_absolute():
        raise ValueError("use a relative, separate destination workspace")
    with zipfile.ZipFile(archive_path) as archive:
        def member(path):
            matches = [n for n in archive.namelist() if n == str(path) or n.endswith("/" + str(path))]
            if len(matches) != 1:
                raise ValueError(f"missing or ambiguous archive member: {path}")
            return archive.read(matches[0])
        rp = RELATIVE / "registration.json"
        registration_bytes = recover(member(rp), registration_sha256)
        reg = json.loads(registration_bytes)
        if reg["protocol_id"] != "CEREBRUM-END2END-PROGRAM-003" or reg["confirmation_materialized"]:
            raise ValueError("wrong protocol or confirmation boundary")
        files = {rp: registration_bytes}
        for name, expected in reg["sources"].items():
            name = PurePosixPath(name)
            if name.is_absolute() or ".." in name.parts:
                raise ValueError("unsafe source path")
            path = PurePosixPath("edon/experiments") / name
            files[path] = recover(member(path), expected)
        # Data can be absent from a Prism export. Recreate ONLY train/development
        # from the bound sources; prepare must reproduce the original registration.
    for path, data in files.items():
        target = destination / path
        # Resolve before writing to reject escape through pre-existing symlinks.
        if not target.resolve().is_relative_to(destination.resolve()):
            raise ValueError("destination symlink escapes workspace")
        if target.exists() and target.read_bytes() != data:
            raise ValueError(f"refusing to overwrite differing file: {target}")
    experiment = destination / RELATIVE
    for name in ("artifacts", "results"):
        if (experiment / name).exists():
            raise ValueError("restore requires a setup-only destination, not a started experiment")
    for path, data in files.items():
        target = destination / path
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            with target.open("xb") as handle:
                handle.write(data)
    subprocess.run([sys.executable, "-u", "run.py", "prepare"], cwd=experiment, check=True)
    subprocess.run([sys.executable, "-u", "run.py", "preflight"], cwd=experiment, check=True)
    if digest((experiment / "registration.json").read_bytes()) != registration_sha256:
        raise ValueError("registration changed during deterministic preparation")
    print("RESTORED_AND_CPU_VERIFIED", experiment)
    return experiment


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("archive", type=Path)
    p.add_argument("destination", type=Path)
    p.add_argument("--registration-sha256", required=True)
    a = p.parse_args()
    restore(a.archive, a.destination, a.registration_sha256)