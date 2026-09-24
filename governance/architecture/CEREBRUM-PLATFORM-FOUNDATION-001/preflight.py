"""Verify the draft Platform Foundation registration and claim boundaries."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[3]
DOCUMENT = ROOT / "docs/implementation/cerebrum-platform-foundation-001.md"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def numbered_items(text: str, heading: str) -> int:
    section = text.split(heading, 1)[1].split("\n## ", 1)[0]
    return len(re.findall(r"^\d+\. ", section, flags=re.MULTILINE))


def verify() -> dict[str, Any]:
    manifest = read_json(HERE / "manifest.json")
    document = DOCUMENT.read_text(encoding="utf-8")
    repository_readme = (ROOT / "README.md").read_text(encoding="utf-8")
    product = read_json(ROOT / "product/cerebrum-platform/manifest.json")

    assert manifest["specification_id"] == "CEREBRUM-PLATFORM-FOUNDATION-001"
    assert manifest["status"] == "DRAFT_IMPLEMENTATION_SPECIFICATION_NOT_DEPLOYMENT_AUTHORIZATION"
    assert manifest["architecture_dependency"] == "CEREBRUM-MATURE-PLATFORM-SPEC-001"
    assert manifest["hash_frozen"] is False
    assert manifest["freeze_gate_count"] == 14
    assert manifest["production_authorized"] is False
    assert manifest["consequential_writes_authorized"] is False
    assert manifest["binding_authority"] is False

    assert "Status: `DRAFT_IMPLEMENTATION_SPECIFICATION_NOT_DEPLOYMENT_AUTHORIZATION`" in document
    assert numbered_items(document, "## Freeze gates") == manifest["freeze_gate_count"]
    assert "Customer System" in document and "Observation Gateway" in document
    assert "Reasoning Runtime → no customer credentials" in document
    assert "Evaluation cannot install a component" in document
    assert "CEREBRUM-PLATFORM-FOUNDATION-001" in repository_readme

    assert product["platform_foundation_id"] == manifest["specification_id"]
    assert product["platform_foundation_status"] == manifest["status"]
    assert product["platform_foundation_freeze_gates_passed"] is False
    assert product["production_validated"] is False
    assert product["binding_authority"] is False

    return {
        "schema_version": "edon-platform-foundation-preflight.v1",
        "specification_id": manifest["specification_id"],
        "architecture_dependency": manifest["architecture_dependency"],
        "status": "PASS",
        "freeze_gates": manifest["freeze_gate_count"],
        "hash_frozen": manifest["hash_frozen"],
        "binding_authority": manifest["binding_authority"],
    }


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2, sort_keys=True))