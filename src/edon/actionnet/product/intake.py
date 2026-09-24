"""Privacy-preserving governed abstraction intake for ActionNet Platform."""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from edon.common.hashing import sha256_json


class GovernedIntakeError(ValueError):
    """Raised when an abstraction intake contains raw or insufficiently governed data."""


RIGHTS_BASES = {
    "CONSENT", "CONTRACT", "LEGAL_OBLIGATION", "LEGITIMATE_INTEREST",
    "PUBLIC_SOURCE", "INTERNAL_AUTHORIZATION",
}

FORBIDDEN_SENSITIVE_KEYS = {
    "raw", "raw_payload", "raw_record", "raw_source", "customer_data", "patient_data",
    "patient_name", "customer_name", "full_name", "first_name", "last_name", "ssn",
    "social_security_number", "email", "phone", "address", "password", "secret",
    "access_token", "api_key", "biometric", "medical_record_number", "account_number",
}


def _scan(value: Any, path: str = "abstraction") -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            normalized = str(key).strip().lower()
            governance_keys = {"raw_payload_retained_locally", "raw_payload_stored"}
            if normalized in FORBIDDEN_SENSITIVE_KEYS or (
                normalized.startswith("raw_") and normalized not in governance_keys
            ):
                raise GovernedIntakeError(f"governed abstraction cannot contain {path}.{key}")
            _scan(nested, f"{path}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _scan(nested, f"{path}[{index}]")


class GovernedAbstractionValidator:
    """Accepts only locally minimized abstractions; raw institutional records are rejected."""

    def normalize(self, document: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(document, dict):
            raise GovernedIntakeError("governed abstraction must be an object")
        try:
            record = json.loads(json.dumps(document, allow_nan=False))
        except (TypeError, ValueError) as exc:
            raise GovernedIntakeError("governed abstraction must contain finite JSON") from exc
        _scan(record)
        required = {
            "intake_id", "institution_ir_ref", "source_fingerprint", "local_processor",
            "rights_basis", "data_categories", "redaction_summary", "attestation",
            "mechanism_refs", "trajectory", "causal_trace", "provenance",
        }
        missing = sorted(required - set(record))
        if missing:
            raise GovernedIntakeError("governed abstraction missing: " + ", ".join(missing))
        attestation = record["attestation"]
        if not isinstance(attestation, dict):
            raise GovernedIntakeError("attestation must be an object")
        controls = {
            "direct_identifiers_removed",
            "secrets_removed",
            "minimum_necessary",
            "raw_payload_retained_locally",
            "authorized_for_abstraction",
        }
        failed = sorted(control for control in controls if attestation.get(control) is not True)
        if failed:
            raise GovernedIntakeError("governed abstraction attestation failed: " + ", ".join(failed))
        rights_basis = str(record["rights_basis"]).upper()
        if rights_basis not in RIGHTS_BASES:
            raise GovernedIntakeError(f"unsupported source rights basis: {rights_basis}")
        ir_ref = record["institution_ir_ref"]
        if not isinstance(ir_ref, dict) or not {"institution_id", "version"}.issubset(ir_ref):
            raise GovernedIntakeError("institution_ir_ref requires institution_id and version")
        processor = record["local_processor"]
        if not isinstance(processor, dict) or not {"processor_id", "version"}.issubset(processor):
            raise GovernedIntakeError("local_processor requires processor_id and version")
        refs = record["mechanism_refs"]
        if not isinstance(refs, list) or not refs:
            raise GovernedIntakeError("governed abstraction requires mechanism_refs")
        normalized = {
            "schema_version": "actionnet-governed-abstraction.v1",
            "intake_id": str(record["intake_id"]),
            "institution_ir_ref": {
                "institution_id": str(ir_ref["institution_id"]),
                "version": str(ir_ref["version"]),
            },
            "source_fingerprint": str(record["source_fingerprint"]),
            "local_processor": {
                "processor_id": str(processor["processor_id"]),
                "version": str(processor["version"]),
            },
            "rights_basis": rights_basis,
            "data_categories": sorted({str(item) for item in record["data_categories"]}),
            "redaction_summary": deepcopy(record["redaction_summary"]),
            "attestation": {control: True for control in sorted(controls)},
            "mechanism_refs": deepcopy(refs),
            "trajectory": deepcopy(record["trajectory"]),
            "causal_trace": deepcopy(record["causal_trace"]),
            "outcome": deepcopy(record.get("outcome", {})),
            "provenance": deepcopy(record["provenance"]),
            "retention_class": str(record.get("retention_class", "GOVERNED_ABSTRACTION")),
            "raw_payload_stored": False,
            "authoritative": False,
            "training_eligible": False,
            "requires_privacy_review": True,
            "binding_authority": False,
        }
        normalized["abstraction_sha256"] = sha256_json(normalized)
        return normalized