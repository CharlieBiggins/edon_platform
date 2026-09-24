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
    assert report["status"] in {"READY_PENDING_DEV011_PARENT_IMPORT", "READY_FOR_DEV012_FOCUSED_GPU_EXECUTION"}
    assert report["expected_optimizer_steps"] == 24
    assert report["full_regression"] is False
    assert report["transfer_authorized"] is False


def test_perfect_predictions_pass_gate() -> None:
    prepare = load_module("dev012_prepare_test", ROOT / "prepare_data.py")
    common = load_module("dev012_common_test", ROOT / "dev012_common.py")
    scorer = load_module("dev012_score_test", ROOT / "score.py")
    prepare.prepare()
    expected = common.read_jsonl(ROOT / "prepared" / "focused-validation-64.jsonl")
    predictions = [{
        "case_id": row["case_id"],
        "parsed": json.loads(row["completion"]),
        "raw_output": row["completion"],
        "confidence": 1.0,
        "ended_with_eos": True,
        "hit_generation_limit": False,
        "generated_token_count": 1,
        "prompt_token_count": 1,
    } for row in expected]
    parent = scorer.load_parent_scorer()
    result = parent.score_seed(expected, predictions, parent.load_evaluator(), common.read_json(common.CONFIG))
    assert result["focused_gate"]["passed"] is True
    assert result["unsafe_authorizations"] == 0


def test_parent_and_budget_are_frozen() -> None:
    config = json.loads((ROOT / "configs" / "dev012-focused.json").read_text(encoding="utf-8"))
    assert config["parent_training_manifest_sha256"] == "sha256:190c37ec181252b6eee2b4b4e852f1fab42a9d87c0fb11cb8c3849f8fdfee240"
    assert config["max_steps"] == 24
    assert config["save_steps"] == 12