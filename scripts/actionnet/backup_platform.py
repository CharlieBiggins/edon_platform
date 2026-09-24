#!/usr/bin/env python3
"""Create a consistent SQLite backup and checksum manifest for ActionNet Platform."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-dir", type=Path, default=Path("var/edon"))
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    source = args.state_dir / "actionnet-platform.sqlite3"
    if not source.is_file():
        raise SystemExit(f"ActionNet Platform database not found: {source}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    destination = args.output_dir / f"actionnet-platform-{timestamp}.sqlite3"
    with sqlite3.connect(source) as source_connection:
        with sqlite3.connect(destination) as destination_connection:
            source_connection.backup(destination_connection)
    with sqlite3.connect(destination) as connection:
        quick_check = connection.execute("PRAGMA quick_check").fetchone()[0]
        schema = connection.execute(
            "SELECT value FROM actionnet_product_metadata WHERE key = 'schema_version'"
        ).fetchone()
    manifest = {
        "schema_version": "actionnet-platform-backup.v1",
        "created_at": datetime.now(UTC).isoformat(),
        "source": str(source),
        "backup": destination.name,
        "backup_sha256": sha256(destination),
        "bytes": destination.stat().st_size,
        "database_schema_version": schema[0] if schema else None,
        "sqlite_quick_check": quick_check,
    }
    manifest_path = destination.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    destination.chmod(0o600)
    manifest_path.chmod(0o600)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0 if quick_check == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())