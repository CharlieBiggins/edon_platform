#!/usr/bin/env python3
"""Inspect local ActionNet Platform operational readiness without overstating production status."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import stat
from pathlib import Path


REQUIRED_ATTESTATIONS = {
    "external_identity",
    "tls",
    "secret_manager",
    "backup_restore_tested",
    "monitoring_and_alerting",
    "privacy_review",
    "penetration_test",
    "incident_response",
    "production_release_authorization",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-dir", type=Path, default=Path("var/edon"))
    parser.add_argument("--production-attestation", type=Path)
    args = parser.parse_args()
    database = args.state_dir / "actionnet-platform.sqlite3"
    checks: dict[str, bool] = {"database_exists": database.is_file()}
    if database.is_file():
        mode = stat.S_IMODE(database.stat().st_mode)
        checks["database_not_group_or_world_readable"] = mode & 0o077 == 0
        with sqlite3.connect(database) as connection:
            checks["sqlite_integrity"] = connection.execute("PRAGMA quick_check").fetchone()[0] == "ok"
            schema = connection.execute(
                "SELECT value FROM actionnet_product_metadata WHERE key = 'schema_version'"
            ).fetchone()
            checks["schema_version_registered"] = bool(
                schema and schema[0] in {
                    "actionnet-platform-store.v1", "actionnet-platform-store.v2"
                }
            )
    principals = os.environ.get("EDON_API_KEYS", "")
    try:
        mapping = json.loads(principals) if principals else {}
    except json.JSONDecodeError:
        mapping = {}
    checks["api_principals_configured"] = isinstance(mapping, dict) and bool(mapping)
    checks["api_tokens_at_least_32_characters"] = bool(mapping) and all(
        len(str(token)) >= 32 for token in mapping
    )
    attestations: dict[str, bool] = {}
    if args.production_attestation and args.production_attestation.is_file():
        raw = json.loads(args.production_attestation.read_text(encoding="utf-8"))
        attestations = {key: raw.get(key) is True for key in REQUIRED_ATTESTATIONS}
    local_ready = all(checks.values())
    production_ready = local_ready and bool(attestations) and all(attestations.values())
    result = {
        "schema_version": "actionnet-platform-readiness.v1",
        "status": "PRODUCTION_READY" if production_ready else (
            "INTERNAL_MVP_READY" if local_ready else "NOT_READY"
        ),
        "local_checks": checks,
        "production_attestations": attestations,
        "production_ready": production_ready,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if local_ready else 1


if __name__ == "__main__":
    raise SystemExit(main())