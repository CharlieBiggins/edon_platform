#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib.util, json
from pathlib import Path
from typing import Any
ROOT = Path(__file__).resolve().parent
PREDECESSOR = ROOT.parent / "ACTIONNET-DATA-QUAL-007" / "actionnet_eventnet.py"
OUTPUT = ROOT / "oracle" / "actionnet007_overlap_reference.json"
def canonical(value: Any) -> str: return json.dumps(value, sort_keys=True, separators=(",", ":"))
def digest(value: Any) -> str: return "sha256:" + hashlib.sha256(canonical(value).encode()).hexdigest()
def main() -> int:
    spec = importlib.util.spec_from_file_location("actionnet007", PREDECESSOR)
    if spec is None or spec.loader is None: raise RuntimeError(f"cannot load {PREDECESSOR}")
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    generated = module.generate(); rows = generated["datasets"]["train"] + generated["datasets"]["repair_validation"]
    payload = {"schema_version":"actionnet-overlap-reference.v1","source_result":"ACTIONNET-DATA-QUAL-007-result-v1.0.0","case_ids":sorted({r["case_id"] for r in rows}),"prompt_hashes":sorted({digest(r["input"]) for r in rows}),"binding_authority":False}
    payload["content_sha256"] = digest(payload); OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True)+"\n")
    return 0
if __name__ == "__main__": raise SystemExit(main())