#!/usr/bin/env python3
"""Import the complete preserved ActionNet-001 through ActionNet-008 chain."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
WORKSPACE = REPO.parent
LEGACY_EXPERIMENTS = WORKSPACE / "EDONIFM" / "EDON research v1" / "EDON Research" / "experiments"
VERSIONS = ("001", "002", "003", "004", "005", "006", "007", "008")
IMPLEMENTATIONS = {
    "001": "actionnet.py",
    "002": "actionnet_repair.py",
    "003": "actionnet_multiview.py",
    "004": "actionnet_eventnet.py",
    "005": "actionnet_eventnet.py",
    "006": "actionnet_eventnet.py",
    "007": "actionnet_eventnet.py",
    "008": "actionnet_multidomain.py",
}
WORLD_RESOURCES = {
    version: (implementation,)
    for version, implementation in IMPLEMENTATIONS.items()
}
WORLD_RESOURCES["008"] = (
    "actionnet_multidomain.py",
    "registry/domains.json",
)


def digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def copy_verified(source: Path, destination: Path, records: list[dict[str, object]]) -> None:
    if source.resolve() != destination.resolve():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    source_hash = digest(source)
    if source_hash != digest(destination):
        raise RuntimeError(f"copy hash mismatch: {source} -> {destination}")
    records.append({
        "source": source.relative_to(WORKSPACE).as_posix(),
        "destination": destination.relative_to(REPO).as_posix(),
        "bytes": source.stat().st_size,
        "sha256": source_hash,
    })


def source_root(version: str) -> Path:
    experiment_id = f"ACTIONNET-DATA-QUAL-{version}"
    archived = (
        WORKSPACE / experiment_id
        if version == "008"
        else LEGACY_EXPERIMENTS / experiment_id
    )
    if archived.is_dir():
        return archived
    local = REPO / "experiments" / experiment_id
    if local.is_dir():
        return local
    raise RuntimeError(f"missing preserved or local package: {experiment_id}")


def main() -> int:
    records: list[dict[str, object]] = []
    for version in VERSIONS:
        experiment_id = f"ACTIONNET-DATA-QUAL-{version}"
        package_source = source_root(version)
        destination_root = REPO / "experiments" / experiment_id
        importing_archive = package_source.resolve() != destination_root.resolve()
        for source in sorted(package_source.rglob("*")):
            if not source.is_file() or "__pycache__" in source.parts:
                continue
            relative = source.relative_to(package_source)
            if importing_archive and relative.as_posix() == "README.md":
                copy_verified(source, destination_root / "ORIGINAL_README.md", records)
            if importing_archive and relative.as_posix() == "results/result_manifest.json":
                copy_verified(
                    source,
                    destination_root / "results" / "preserved_result_manifest.json",
                    records,
                )
            copy_verified(source, destination_root / relative, records)

        world_root = REPO / "src" / "edon" / "actionnet" / "eventnet" / "worlds" / experiment_id
        for relative_name in WORLD_RESOURCES[version]:
            source = package_source / relative_name
            if not source.is_file():
                raise RuntimeError(f"missing ActionNet world resource: {source}")
            copy_verified(source, world_root / relative_name, records)

    records.sort(key=lambda row: str(row["destination"]))
    inventory = {
        "schema_version": "edon-actionnet-world-import.v1",
        "date": "2026-08-19",
        "versions": list(VERSIONS),
        "files": len(records),
        "bytes": sum(int(row["bytes"]) for row in records),
        "records": records,
        "custody_boundary": (
            "ActionNet-008 remains source-ungrounded, expert-review pending, and "
            "training_eligible=false. Reserved future-public and protected semantic "
            "families remain unmaterialized exactly as registered."
        ),
    }
    output = REPO / "provenance" / "dataset-lineage" / "actionnet-world-import.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(inventory, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "IMPORTED_VERIFIED",
        "files": inventory["files"],
        "bytes": inventory["bytes"],
        "inventory": output.relative_to(REPO).as_posix(),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())