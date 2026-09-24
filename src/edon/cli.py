"""Repository-level EDON validation CLI."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from edon.compiler import CompilerInputError, compile_to_file


REQUIRED_ROOT_FILES = {
    "README.md", "LICENSE.md", "CITATION.md", "CONTRIBUTING.md", "SECURITY.md",
    "CHANGELOG.md", "pyproject.toml", "requirements-lock.txt", "GITIGNORE.md",
    "ENVIRONMENT.md", "IP_GOVERNANCE.md",
}
REQUIRED_DIRECTORIES = {
    "docs", "papers", "src", "schemas", "data", "experiments", "evaluations",
    "benchmarks", "models", "configs", "scripts", "tests", "infra", "provenance",
    "governance", "results", "examples",
}
EXPERIMENT_FILES = {"README.md", "PROTOCOL.md", "CLAIMS.md", "manifest.json"}
MANIFEST_FIELDS = {
    "schema_version", "experiment_id", "version", "status", "artifact", "model",
    "seeds", "dataset", "license", "claim_scope", "binding_authority",
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_repository(root: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    missing_files = sorted(name for name in REQUIRED_ROOT_FILES if not (root / name).is_file())
    missing_directories = sorted(name for name in REQUIRED_DIRECTORIES if not (root / name).is_dir())
    errors.extend(f"missing root file: {name}" for name in missing_files)
    errors.extend(f"missing root directory: {name}" for name in missing_directories)

    registry_path = root / "experiments" / "registry.json"
    registry = read_json(registry_path) if registry_path.exists() else {"experiments": []}
    registry_ids: set[str] = set()
    for row in registry.get("experiments", []):
        experiment_id = row.get("id")
        path = root / str(row.get("path", ""))
        if not isinstance(experiment_id, str) or not experiment_id:
            errors.append("experiment registry row has no ID")
            continue
        if experiment_id in registry_ids:
            errors.append(f"duplicate experiment registry ID: {experiment_id}")
        registry_ids.add(experiment_id)
        if not path.is_dir():
            errors.append(f"registered experiment directory missing: {path.relative_to(root)}")
            continue
        missing = sorted(name for name in EXPERIMENT_FILES if not (path / name).is_file())
        errors.extend(f"{experiment_id} missing {name}" for name in missing)
        manifest_path = path / "manifest.json"
        if not manifest_path.exists():
            continue
        manifest = read_json(manifest_path)
        absent = sorted(MANIFEST_FIELDS - set(manifest))
        errors.extend(f"{experiment_id} manifest missing field: {name}" for name in absent)
        if manifest.get("experiment_id") != experiment_id:
            errors.append(f"{experiment_id} manifest identity mismatch")
        sha = manifest.get("artifact", {}).get("sha256") if isinstance(manifest.get("artifact"), dict) else None
        if sha is not None and (not isinstance(sha, str) or not sha.startswith("sha256:") or len(sha) != 71):
            errors.append(f"{experiment_id} has invalid artifact SHA-256")
        if manifest.get("binding_authority") is not False:
            errors.append(f"{experiment_id} must declare binding_authority=false")

    claims_path = root / "governance" / "claim-registry" / "claims.json"
    if claims_path.exists():
        claims = read_json(claims_path)
        known = registry_ids
        for claim in claims.get("claims", []):
            for experiment_id in claim.get("evidence", []):
                if experiment_id not in known:
                    errors.append(f"claim {claim.get('id')} references unknown experiment {experiment_id}")
    else:
        errors.append("claim registry missing")

    license_path = root / "LICENSE.md"
    if license_path.exists() and "all rights reserved" in license_path.read_text(encoding="utf-8").lower():
        warnings.append("public license is still pending")
    report = {
        "schema_version": "edon-repository-validation.v1",
        "root": str(root),
        "experiments": len(registry_ids),
        "errors": errors,
        "warnings": warnings,
        "status": "PASS" if not errors else "FAIL",
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(prog="edon")
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate", help="validate repository structure and claim links")
    validate.add_argument("root", nargs="?", type=Path, default=Path("."))
    compile_parser = subparsers.add_parser(
        "compile-institution",
        help="compile structured institutional sources into reviewable candidate IR",
    )
    compile_parser.add_argument("input", type=Path, help="compiler input bundle")
    compile_parser.add_argument("--output", "-o", type=Path, required=True, help="output JSON path")
    serve_parser = subparsers.add_parser("serve", help="run the authenticated EDON API and dashboard")
    serve_parser.add_argument("--state-dir", type=Path, default=Path("var/edon"))
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8080)
    serve_parser.add_argument("--api-keys-env", default="EDON_API_KEYS")
    serve_parser.add_argument("--admin-key-env", default="EDON_API_KEY")
    args = parser.parse_args()
    if args.command == "validate":
        report = validate_repository(args.root.resolve())
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["status"] == "PASS" else 1
    if args.command == "compile-institution":
        try:
            report = compile_to_file(args.input, args.output)
        except CompilerInputError as exc:
            print(json.dumps({"status": "COMPILER_INPUT_REJECTED", "error": str(exc)}, indent=2))
            return 2
        print(json.dumps({
            "status": report["qualification"]["status"],
            "output": str(args.output),
            **report["extraction_summary"],
            "binding_authority": False,
        }, indent=2, sort_keys=True))
        return 0 if report["qualification"]["passed"] else 1
    if args.command == "serve":
        api_keys: dict[str, str | dict[str, str]] = {}
        mapping = os.environ.get(args.api_keys_env, "")
        if mapping:
            try:
                parsed = json.loads(mapping)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, dict):
                api_keys = {
                    str(token): (
                        {str(key): str(value) for key, value in principal.items()}
                        if isinstance(principal, dict) else str(principal)
                    )
                    for token, principal in parsed.items()
                }
        admin_key = os.environ.get(args.admin_key_env, "")
        if not api_keys and admin_key:
            api_keys = {admin_key: "ADMIN"}
        if not api_keys or any(len(token) < 16 for token in api_keys):
            print(json.dumps({
                "status": "SERVER_NOT_STARTED",
                "error": (
                    f"{args.api_keys_env} must be a token-to-role JSON object, or "
                    f"{args.admin_key_env} must contain an admin key of at least 16 characters"
                ),
            }, indent=2))
            return 2
        from edon.api import run_server

        run_server(args.state_dir, args.host, args.port, api_keys)
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())