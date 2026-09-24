"""Verify the frozen Cerebrum platform vision and canonical contract inventory."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[3]


def _pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in items:
        if key in value:
            raise ValueError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _reject_constant(value: str) -> None:
    raise ValueError(f"nonfinite JSON constant: {value}")


def read_json(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_pairs,
        parse_constant=_reject_constant,
    )


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def verify() -> dict[str, Any]:
    manifest = read_json(HERE / "manifest.json")
    inventory = read_json(HERE / "inventory.json")
    vision = read_json(HERE / "platform-vision.json")

    assert manifest["vision_id"] == vision["vision_id"] == "CEREBRUM-PLATFORM-VISION-001"
    assert manifest["status"] == vision["status"] == "FROZEN_CONTROLLING_VISION_NOT_IMPLEMENTED"
    assert manifest["artifact"]["sha256"] == file_hash(HERE / "platform-vision.json")
    assert manifest["controlling_document"]["sha256"] == file_hash(
        ROOT / manifest["controlling_document"]["path"]
    )
    assert manifest["binding_authority"] is False
    assert vision["claims"]["complete_platform_implemented"] is False
    assert vision["claims"]["production_authorized"] is False
    assert len(vision["canonical_specifications"]) == 6

    for relative, expected in inventory["files"].items():
        path = (HERE / relative).resolve()
        assert path.is_file(), relative
        assert file_hash(path) == expected, relative

    schema_paths = [
        "schemas/events/event-envelope.schema.json",
        "schemas/institution/institutional-state.schema.json",
        "schemas/institution/ir-lifecycle.schema.json",
        "schemas/actions/action-proposal.schema.json",
        "schemas/actions/authorization-decision.schema.json",
        "schemas/actions/execution-request.schema.json",
        "schemas/actions/execution-record.schema.json",
        "schemas/releases/release-contract.schema.json",
        "schemas/releases/deployment-approval.schema.json",
        "schemas/releases/runtime-attestation.schema.json",
        "schemas/domain-packs/manifest.schema.json",
        "schemas/workflows/qualification.schema.json",
    ]
    for relative in schema_paths:
        schema = read_json(ROOT / relative)
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["type"] == "object"

    return {
        "schema_version": "edon-platform-vision-preflight.v1",
        "vision_id": vision["vision_id"],
        "status": "PASS",
        "inventory_files": len(inventory["files"]),
        "canonical_specifications": len(vision["canonical_specifications"]),
        "schemas": len(schema_paths),
        "binding_authority": False,
    }


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2, sort_keys=True))