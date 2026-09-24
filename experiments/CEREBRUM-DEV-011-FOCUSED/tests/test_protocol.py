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


def test_preflight_core_and_focus_boundary() -> None:
    subprocess.run([sys.executable, "preflight.py", "--allow-missing-parents"], cwd=ROOT, check=True)
    report = json.loads((ROOT / "results" / "readiness-report.json").read_text(encoding="utf-8"))
    assert report["core_controls_passed"] == report["core_control_count"]
    assert report["status"] in {
        "READY_PENDING_PARENT_ADAPTER_IMPORT",
        "READY_FOR_TWO_PARENT_FOCUSED_GPU_EXECUTION",
    }
    assert report["expected_optimizer_steps_per_parent"] == 48
    assert report["full_regression"] is False
    assert report["transfer_authorized"] is False


def test_perfect_focused_predictions_pass_strict_gate() -> None:
    prepare = load_module("dev011_prepare_test", ROOT / "prepare_data.py")
    scorer = load_module("dev011_score_test", ROOT / "score.py")
    common = load_module("dev011_common_test", ROOT / "dev011_common.py")
    prepare.prepare()
    config = common.read_json(common.CONFIG)
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
    result = scorer.score_seed(expected, predictions, scorer.load_evaluator(), config)
    assert result["focused_gate"]["passed"] is True
    assert result["unsafe_authorizations"] == 0
    assert result["paired_boundary_exact"] == 1.0


def test_trainer_continues_existing_adapter() -> None:
    source = (ROOT / "train_continuation.py").read_text(encoding="utf-8")
    assert "PeftModel.from_pretrained" in source
    assert "is_trainable=True" in source
    assert "get_peft_model" not in source