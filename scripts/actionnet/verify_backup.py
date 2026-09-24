#!/usr/bin/env python3
"""Verify an ActionNet Platform backup manifest and SQLite integrity."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    backup = args.manifest.parent / manifest["backup"]
    actual_hash = sha256(backup)
    with sqlite3.connect(backup) as connection:
        quick_check = connection.execute("PRAGMA quick_check").fetchone()[0]
        audit_count = connection.execute("SELECT COUNT(*) FROM actionnet_product_audit").fetchone()[0]
    checks = {
        "backup_exists": backup.is_file(),
        "checksum_matches": actual_hash == manifest["backup_sha256"],
        "sqlite_quick_check": quick_check == "ok",
        "audit_table_readable": audit_count >= 0,
    }
    result = {
        "schema_version": "actionnet-platform-backup-verification.v1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "actual_sha256": actual_hash,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())