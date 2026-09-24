from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(ROOT))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module


def test_preflight_core() -> None:
    subprocess.run([sys.executable, "preflight.py", "--allow-missing-parent"], cwd=ROOT, check=True)
    report = json.loads((ROOT / "results" / "readiness-report.json").read_text(encoding="utf-8"))
    assert report["core_controls_passed"] == report["core_control_count"]
    assert report["status"] in {"READY_PENDING_DEV013_SELECTED_ADAPTER_IMPORT", "READY_FOR_DEV014_FULL_GPU_REGRESSION"}
    assert report["expected_predictions"] == 192
    assert report["expected_optimizer_steps"] == 0


def test_perfect_predictions_pass_all_26_checks() -> None:
    prepare = load_module("dev014_prepare_test", ROOT / "prepare_data.py")
    common = load_module("dev014_common_test", ROOT / "dev014_common.py")
    gate = load_module("dev014_gate_test", ROOT / "gate.py")
    prepare.prepare()
    expected = common.read_jsonl(ROOT / "prepared" / "full-regression-192.jsonl")
    sys.path.insert(0, str(common.BASE))
    try:
        import canonicalize
        import evaluate
        predictions = []
        for row in expected:
            parsed = json.loads(row["completion"])
            predictions.append({
                "case_id": row["case_id"],
                "task_type": row["task_type"],
                "parsed": parsed,
                "compiled": canonicalize.compile_prediction(row["task_type"], row["compiler_input"], parsed),
                "raw_output": row["completion"],
                "confidence": 1.0,
                "ended_with_eos": True,
                "hit_generation_limit": False,
            })
        result = evaluate.score(predictions, expected, "oracle", None)
    finally:
        sys.path.pop(0)
    config = common.read_json(common.CONFIG)
    scored = gate.advancement_gate(result, config["gate"])
    assert scored["passed"] is True
    assert scored["checks_passed"] == scored["check_count"] == 26


def test_selected_candidate_identity_is_frozen() -> None:
    config = json.loads((ROOT / "configs" / "dev014-full.json").read_text(encoding="utf-8"))
    assert config["selected_candidate_id"] == "continuation-step-6"
    assert config["selected_step"] == 6
    assert config["selected_adapter_tree_sha256"] == "sha256:d03460f927a1e3f8fed967fad8f48c5d7fbb2fa77b3898b5a021eb72680f7396"
    assert config["parent_selection_sha256"] == "sha256:c6d2af80451b65c6f2a52cef6d7aed7003e904a4c2a4b025f2e9dc287c0d6a30"