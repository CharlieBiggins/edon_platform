"""Verify the mature platform specification and its frozen vision dependency."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[3]
VISION = HERE.parent / "CEREBRUM-PLATFORM-VISION-002"


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
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    payload = (text.rstrip("\n") + "\n").encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def verify() -> dict[str, Any]:
    manifest = read_json(HERE / "manifest.json")
    inventory = read_json(HERE / "inventory.json")
    specification = read_json(HERE / "platform-specification.json")
    vision_manifest = read_json(VISION / "manifest.json")

    assert manifest["specification_id"] == specification["specification_id"] == "CEREBRUM-MATURE-PLATFORM-SPEC-001"
    assert manifest["status"] == specification["status"] == "FROZEN_CONTROLLING_PRODUCT_SPECIFICATION_NOT_IMPLEMENTED"
    assert manifest["hash_mode"] == "UTF8_LF_SINGLE_TRAILING_NEWLINE"
    assert manifest["artifact"]["sha256"] == normalized_hash(HERE / "platform-specification.json")
    assert manifest["controlling_document"]["sha256"] == normalized_hash(
        ROOT / manifest["controlling_document"]["path"]
    )

    dependency = specification["architecture_dependency"]
    assert dependency["vision_id"] == vision_manifest["vision_id"] == "CEREBRUM-PLATFORM-VISION-002"
    assert dependency["artifact_sha256"] == vision_manifest["artifact"]["sha256"]
    assert dependency["artifact_sha256"] == normalized_hash(VISION / "platform-vision.json")

    assert len(specification["canonical_specifications"]) == 11
    assert specification["kernel_decisions"] == [
        "ALLOW", "DENY", "ABSTAIN", "ESCALATE", "REVISE", "REASSIGN", "APPROVAL_REQUIRED"
    ]
    assert specification["epistemic_states"] == [
        "UNKNOWN", "REPORTED", "OBSERVED", "INFERRED", "DISPUTED", "VERIFIED"
    ]
    assert specification["invariants"]["critic_creates_authority"] is False
    assert specification["invariants"]["model_installs_or_qualifies_itself"] is False
    assert specification["invariants"]["actionnet_updates_production_directly"] is False
    assert specification["claims"]["complete_platform_implemented"] is False
    assert specification["claims"]["bounded_institutional_intelligence_established"] is False
    assert specification["claims"]["production_authorized"] is False
    assert manifest["binding_authority"] is False

    for relative, expected in inventory["files"].items():
        path = (HERE / relative).resolve()
        assert path.is_file(), relative
        assert normalized_hash(path) == expected, relative

    schema_paths = [
        "schemas/intelligence/component-registry.schema.json",
        "schemas/intelligence/routing-decision.schema.json",
        "schemas/intelligence/invocation-receipt.schema.json",
        "schemas/intelligence/data-access-grant.schema.json",
        "schemas/intelligence/runtime-budget.schema.json",
        "schemas/actionnet/mature-experience-learning-contract.schema.json",
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
    assert product["vision_id"] == dependency["vision_id"]
    assert product["mature_specification_id"] == specification["specification_id"]
    assert product["model_routing_runtime_implemented"] is False
    assert product["mature_actionnet_learning_contract_implemented"] is False
    assert product["binding_authority"] is False

    return {
        "schema_version": "edon-mature-platform-preflight.v1",
        "specification_id": specification["specification_id"],
        "architecture_dependency": dependency["vision_id"],
        "status": "PASS",
        "inventory_files": len(inventory["files"]),
        "canonical_specifications": len(specification["canonical_specifications"]),
        "new_schemas": len(schema_paths),
        "binding_authority": False,
    }


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2, sort_keys=True))