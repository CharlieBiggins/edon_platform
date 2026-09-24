"""Verify the Vision-001 to Vision-002 architecture-governance chain."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[3]
PREDECESSOR = HERE.parent / "CEREBRUM-PLATFORM-VISION-001"


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


def normalized_hash(path: Path) -> str:
    """Hash UTF-8 text with LF endings and exactly one terminal newline."""
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    payload = (text.rstrip("\n") + "\n").encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def verify() -> dict[str, Any]:
    manifest = read_json(HERE / "manifest.json")
    inventory = read_json(HERE / "inventory.json")
    vision = read_json(HERE / "platform-vision.json")
    predecessor_manifest = read_json(PREDECESSOR / "manifest.json")
    predecessor_inventory = read_json(PREDECESSOR / "inventory.json")
    predecessor_vision = read_json(PREDECESSOR / "platform-vision.json")

    assert manifest["vision_id"] == vision["vision_id"] == "CEREBRUM-PLATFORM-VISION-002"
    assert manifest["status"] == vision["status"] == "FROZEN_CONTROLLING_VISION_NOT_IMPLEMENTED"
    assert manifest["hash_mode"] == "UTF8_LF_SINGLE_TRAILING_NEWLINE"
    assert manifest["artifact"]["sha256"] == normalized_hash(HERE / "platform-vision.json")
    assert manifest["controlling_document"]["sha256"] == normalized_hash(
        ROOT / manifest["controlling_document"]["path"]
    )
    assert manifest["binding_authority"] is False

    predecessor = vision["predecessor"]
    assert predecessor["vision_id"] == predecessor_manifest["vision_id"]
    assert predecessor["artifact_sha256"] == predecessor_manifest["artifact"]["sha256"]
    assert predecessor["artifact_sha256"] == normalized_hash(PREDECESSOR / "platform-vision.json")
    for relative, expected in predecessor_inventory["files"].items():
        path = (PREDECESSOR / relative).resolve()
        assert path.is_file(), relative
        assert normalized_hash(path) == expected, relative

    assert len(vision["canonical_specifications"]) == 9
    assert vision["invariants"]["capability_implies_authority"] is False
    assert vision["invariants"]["human_approval_bypasses_kernel"] is False
    assert vision["invariants"]["compensation_bypasses_kernel"] is False
    assert vision["invariants"]["release_registry_updates_runtime_directly"] is False
    assert vision["claims"]["complete_platform_implemented"] is False
    assert vision["claims"]["production_authorized"] is False

    for relative, expected in inventory["files"].items():
        path = (HERE / relative).resolve()
        assert path.is_file(), relative
        assert normalized_hash(path) == expected, relative

    schema_paths = [
        "schemas/control-graph/node.schema.json",
        "schemas/control-graph/edge.schema.json",
        "schemas/control-graph/snapshot.schema.json",
        "schemas/authority/identity-capability.schema.json",
        "schemas/authority/mandate.schema.json",
        "schemas/authority/commitment.schema.json",
        "schemas/authority/resource-reservation.schema.json",
        "schemas/receipts/decision-receipt.schema.json",
        "schemas/receipts/execution-receipt.schema.json",
        "schemas/receipts/compensation-record.schema.json",
    ]
    schema_ids: set[str] = set()
    for relative in schema_paths:
        schema = read_json(ROOT / relative)
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["type"] == "object"
        assert schema["additionalProperties"] is False
        assert schema["$id"] not in schema_ids
        schema_ids.add(schema["$id"])

    product = read_json(ROOT / "product/cerebrum-platform/manifest.json")
    assert product["vision_id"] == vision["vision_id"]
    assert product["institutional_control_graph_implemented"] is False
    assert product["binding_authority"] is False

    return {
        "schema_version": "edon-platform-vision-preflight.v2",
        "vision_id": vision["vision_id"],
        "predecessor": predecessor["vision_id"],
        "predecessor_inventory_files": len(predecessor_inventory["files"]),
        "predecessor_canonical_specifications": len(predecessor_vision["canonical_specifications"]),
        "status": "PASS",
        "inventory_files": len(inventory["files"]),
        "canonical_specifications": len(vision["canonical_specifications"]),
        "new_schemas": len(schema_paths),
        "binding_authority": False,
    }


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2, sort_keys=True))