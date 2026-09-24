"""Verify the draft AWS deployment profile and its Foundation dependency."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[3]
DOCUMENT = ROOT / "docs/deployment/cerebrum-aws-deployment-profile-001.md"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def numbered_items(text: str, heading: str) -> int:
    section = text.split(heading, 1)[1].split("\n## ", 1)[0]
    return len(re.findall(r"^\d+\. ", section, flags=re.MULTILINE))


def verify() -> dict[str, Any]:
    manifest = read_json(HERE / "manifest.json")
    foundation = read_json(
        HERE.parent / "CEREBRUM-PLATFORM-FOUNDATION-001" / "manifest.json"
    )
    document = DOCUMENT.read_text(encoding="utf-8")
    repository_readme = (ROOT / "README.md").read_text(encoding="utf-8")
    product = read_json(ROOT / "product/cerebrum-platform/manifest.json")

    assert manifest["profile_id"] == "CEREBRUM-AWS-DEPLOYMENT-PROFILE-001"
    assert manifest["status"] == "DRAFT_REFERENCE_DEPLOYMENT_NOT_PRODUCTION_QUALIFIED"
    assert manifest["foundation_dependency"] == foundation["specification_id"]
    assert manifest["architecture_dependency"] == foundation["architecture_dependency"]
    assert manifest["hash_frozen"] is False
    assert manifest["profile_qualification_gate_count"] == 12
    assert manifest["infrastructure_deployed"] is False
    assert manifest["production_qualified"] is False
    assert manifest["consequential_writes_authorized"] is False
    assert manifest["binding_authority"] is False

    assert "Status: `DRAFT_REFERENCE_DEPLOYMENT_NOT_PRODUCTION_QUALIFIED`" in document
    assert numbered_items(document, "## Profile qualification gates") == 12
    assert "Fargate is not the proposed GPU runtime" in document
    assert "STS secures AWS resource" in document
    assert "customer ERP" in document and "external systems" in document
    assert "Observation Gateway" in document
    assert "illustrative planning envelopes only" in document
    assert "CEREBRUM-AWS-DEPLOYMENT-PROFILE-001" in repository_readme

    assert product["initial_deployment_profile_id"] == manifest["profile_id"]
    assert product["initial_deployment_profile_status"] == manifest["status"]
    assert product["aws_deployment_profile_qualified"] is False
    assert product["production_validated"] is False
    assert product["binding_authority"] is False

    return {
        "schema_version": "edon-aws-deployment-profile-preflight.v1",
        "profile_id": manifest["profile_id"],
        "foundation_dependency": manifest["foundation_dependency"],
        "status": "PASS",
        "qualification_gates": manifest["profile_qualification_gate_count"],
        "hash_frozen": manifest["hash_frozen"],
        "binding_authority": manifest["binding_authority"],
    }


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2, sort_keys=True))