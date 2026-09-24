"""Validate EDON's sanitized public IP-governance records.

This validator checks repository structure and fail-closed status consistency.
It does not evaluate patentability, inventorship, ownership, secrecy, trademark
availability, legal privilege, or freedom to operate.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_ROOT = Path(__file__).resolve().parents[2]

REQUIRED_DOCS = {
    "README.md",
    "IP_STRATEGY.md",
    "INVENTION_FAMILIES.md",
    "PATENT_DISCLOSURE_GUIDE.md",
    "PRIOR_ART_AND_ELIGIBILITY_PLAN.md",
    "PUBLICATION_AND_DISCLOSURE_GATE.md",
    "TRADE_SECRET_PROGRAM.md",
    "TRADEMARK_AND_BRAND_PLAN.md",
    "COPYRIGHT_CONTRACTS_AND_DATA_RIGHTS.md",
    "COUNSEL_HANDOFF.md",
}

REQUIRED_TEMPLATES = {
    "INVENTION_DISCLOSURE_TEMPLATE.md",
    "INVENTOR_CONTRIBUTION_TEMPLATE.md",
    "PUBLIC_DISCLOSURE_RECORD_TEMPLATE.md",
    "TRADE_SECRET_RECORD_TEMPLATE.md",
}

REQUIRED_GOVERNANCE = {
    "README.md",
    "policy.json",
    "candidate-families.json",
    "disclosure-register.json",
    "trademark-register.json",
    "trade-secret-categories.json",
    "rights-register.json",
    "release-review.template.json",
}

REQUIRED_SCHEMAS = {
    "candidate-family-registry.schema.json",
    "disclosure-register.schema.json",
    "release-review.schema.json",
    "trademark-register.schema.json",
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def missing_files(directory: Path, names: set[str]) -> list[str]:
    return sorted(name for name in names if not (directory / name).is_file())


def validate(root: Path = DEFAULT_ROOT) -> dict[str, Any]:
    root = root.resolve()
    docs = root / "docs" / "ip"
    templates = docs / "templates"
    governance = root / "governance" / "ip"
    schemas = governance / "schemas"
    errors: list[str] = []
    warnings: list[str] = []
    checks: dict[str, bool] = {}

    checks["root_entry_point_present"] = (root / "IP_GOVERNANCE.md").is_file()
    errors.extend(
        f"missing IP document: docs/ip/{name}"
        for name in missing_files(docs, REQUIRED_DOCS)
    )
    errors.extend(
        f"missing private-record template: docs/ip/templates/{name}"
        for name in missing_files(templates, REQUIRED_TEMPLATES)
    )
    errors.extend(
        f"missing IP governance record: governance/ip/{name}"
        for name in missing_files(governance, REQUIRED_GOVERNANCE)
    )
    errors.extend(
        f"missing IP governance schema: governance/ip/schemas/{name}"
        for name in missing_files(schemas, REQUIRED_SCHEMAS)
    )
    if not checks["root_entry_point_present"]:
        errors.append("missing root IP_GOVERNANCE.md")

    json_paths = sorted(governance.rglob("*.json"))
    parsed: dict[str, Any] = {}
    for path in json_paths:
        try:
            parsed[str(path.relative_to(governance))] = read_json(path)
        except (json.JSONDecodeError, OSError) as exc:
            errors.append(f"invalid JSON {path.relative_to(root)}: {exc}")
    checks["all_governance_json_parses"] = not any(
        error.startswith("invalid JSON") for error in errors
    )

    required_parsed = {
        name: parsed.get(name)
        for name in REQUIRED_GOVERNANCE
        if name.endswith(".json")
    }
    if any(value is None for value in required_parsed.values()):
        return {
            "schema_version": "edon-ip-governance-validation.v1",
            "root": str(root),
            "checks": checks,
            "errors": errors,
            "warnings": warnings,
            "status": "FAIL",
        }

    policy = required_parsed["policy.json"]
    checks["policy_is_nonbinding"] = policy.get("binding_authority") is False
    checks["policy_is_not_legal_opinion"] = policy.get("legal_opinion") is False
    checks["unverified_filing_cannot_authorize_patent_pending"] = not (
        policy.get("patent_filing_verified") is False
        and policy.get("patent_pending_language_authorized") is True
    )
    checks["policy_registered_symbol_language_is_disabled"] = (
        policy.get("registered_trademark_language_authorized") is False
    )

    families_record = required_parsed["candidate-families.json"]
    families = families_record.get("candidate_families", [])
    family_ids = [row.get("id") for row in families if isinstance(row, dict)]
    checks["candidate_family_ids_unique"] = len(family_ids) == len(set(family_ids))
    checks["candidate_families_are_not_patentability_findings"] = all(
        row.get("patentability_determined") is False for row in families
    )
    checks["unfiled_families_are_not_patent_pending"] = all(
        not (row.get("filing_status") == "NOT_FILED" and row.get("patent_pending") is True)
        for row in families
    )
    missing_sources: list[str] = []
    for row in families:
        for source in row.get("public_sources", []):
            if not (root / source).exists():
                missing_sources.append(f"{row.get('id')}:{source}")
    checks["candidate_public_sources_exist"] = not missing_sources
    errors.extend(f"candidate source does not exist: {source}" for source in missing_sources)

    disclosure = required_parsed["disclosure-register.json"]
    checks["incomplete_disclosure_inventory_blocks_release"] = not (
        disclosure.get("completeness_attested") is False
        and disclosure.get("release_blocked_until_complete") is not True
    )
    if disclosure.get("completeness_attested") is not True:
        warnings.append("prior-public-disclosure inventory remains incomplete")

    marks_record = required_parsed["trademark-register.json"]
    marks = marks_record.get("marks", [])
    mark_ids = [row.get("id") for row in marks if isinstance(row, dict)]
    checks["trademark_ids_unique"] = len(mark_ids) == len(set(mark_ids))
    checks["unregistered_marks_do_not_use_registered_symbol"] = all(
        not (
            row.get("registration_status") != "REGISTERED_VERIFIED"
            and row.get("approved_symbol") == "REGISTERED"
        )
        for row in marks
    )
    checks["global_registered_symbol_is_disabled"] = (
        marks_record.get("registered_symbol_authorized") is False
    )

    secrets = required_parsed["trade-secret-categories.json"]
    checks["public_registry_contains_no_secret_values"] = (
        secrets.get("contains_secret_values") is False
    )
    checks["secret_categories_are_not_public_repository_assets"] = all(
        row.get("public_repository_allowed") is False
        for row in secrets.get("categories", [])
    )

    rights = required_parsed["rights-register.json"]
    checks["public_rights_record_contains_no_signed_or_personal_records"] = (
        rights.get("contains_personal_or_signed_records") is False
    )
    checks["unverified_ownership_blocks_filing_gate"] = not (
        rights.get("status") == "AUDIT_REQUIRED"
        and rights.get("filing_ownership_gate_passed") is True
    )

    release = required_parsed["release-review.template.json"]
    release_checks = release.get("checks", {})
    checks["release_template_fails_closed"] = (
        release.get("release_authorized") is False
        and release.get("binding_authority") is False
        and release_checks
        and all(value is False for value in release_checks.values())
    )
    checks["approval_records_remain_private"] = (
        release.get("approval_records_private") is True
    )

    for name, passed in checks.items():
        if not passed:
            errors.append(f"failed control: {name}")

    report = {
        "schema_version": "edon-ip-governance-validation.v1",
        "root": str(root),
        "candidate_family_count": len(families),
        "trademark_candidate_count": len(marks),
        "trade_secret_category_count": len(secrets.get("categories", [])),
        "control_count": len(checks),
        "controls_passed": sum(checks.values()),
        "checks": checks,
        "errors": errors,
        "warnings": warnings,
        "status": "PASS" if not errors else "FAIL",
        "legal_opinion": False,
        "binding_authority": False,
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    report = validate(args.root)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())