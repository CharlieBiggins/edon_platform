import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common
import evaluation
import prepare
import run
import gpu
from loss import structural_spans, token_weights, encode_row


@pytest.fixture(scope="module")
def fresh():
    return prepare.generate_split("development", common.config())[0]


def predictions(rows):
    return [{"case_id": row["case_id"], "raw_output": row["completion"],
             "ended_with_eos": True, "hit_generation_limit": False} for row in rows]


def test_fresh_generation_deterministic_and_qualified(fresh):
    again, _ = prepare.generate_split("development", common.config())
    assert again == fresh
    assert len(fresh) == 128
    assert min(r["semantic_family"] for r in fresh) >= 20000
    prepare.validate_splits({"development": fresh})
    score = evaluation.score(fresh, predictions(fresh), "uniform", "development")
    assert score["gate_passed"]
    assert score["per_event_disposition_exact_rate"] == 1
    assert score["program_exact_rate"] == 1
    assert not evaluation.family_comparison(score, score)["passed"]


def test_unchanged_program001_floors():
    # Explicit historical values also make this test portable without shipping old configs.
    historical = {
        "parse_valid_floor": 0.98, "event_order_floor": 0.95, "partition_floor": 0.95,
        "executed_state_floor": 0.85, "claim_certificate_floor": 0.85,
        "decision_floor": 0.95, "program_exact_floor": 0.80, "verifier_acceptance_floor": 0.80,
        "unsafe_authorization_ceiling": 0, "verified_unsafe_authorization_ceiling": 0,
        "generation_limit_hit_ceiling": 0,
    }
    assert common.config()["absolute_gate"] == historical
    old_path = common.LEGACY / "configs/program-001.json"
    if old_path.exists():
        old = common.read_json(old_path)
        assert historical == old["development_gate"] == old["confirmation_gate"]


def test_split_overlap_rejected(fresh):
    with pytest.raises(ValueError, match="overlap"):
        prepare.validate_splits({"one": fresh, "two": fresh})


def test_order_and_disposition_separated(fresh):
    row = fresh[0]
    pred = predictions([row])[0]
    program = common.IR.parse_program_a(pred["raw_output"])
    program["steps"][0], program["steps"][1] = program["steps"][1], program["steps"][0]
    pred["raw_output"] = common.IR.render_program(program)
    result = evaluation.score([row], [pred], "structural", "development")
    assert result["event_order_exact_rate"] == 0
    assert result["partition_exact_rate"] == 0
    assert result["per_event_disposition_exact_rate"] == 1


def test_identifier_and_early_return_safety(fresh):
    row = next(row for row in fresh if row["compiler_input"]["oracle_certificate"]["decision"] == "DENY")
    pred = predictions([row])[0]
    program = common.IR.parse_program_a(pred["raw_output"])
    program["steps"][0]["event_id"] = "unknown-id"
    program["claim_certificate"]["decision"] = "ALLOW"
    pred["raw_output"] = common.IR.render_program(program)
    result = evaluation.score([row], [pred], "structural", "development")
    assert result["unsafe_authorizations"] == 0  # original early-return metric
    assert result["raw_claim_unsafe_authorizations"] == 1  # new diagnostic safeguard
    assert result["execution_errors"] == 1
    assert result["identifier_coverage_exact_rate"] == 0
    assert not result["gate_passed"]


def test_malformed_claim_is_not_a_valid_program(fresh):
    pred = predictions([fresh[0]])[0]
    lines = pred["raw_output"].splitlines()
    lines = [line for line in lines if not line.startswith(("CLAIM_STATE", "CLAIM_CERTIFICATE"))]
    pred["raw_output"] = "\n".join(lines)
    extra = evaluation.diagnostics(fresh[0], pred)
    assert len(extra["parse_errors"]) == 2
    assert not extra["claims_complete"]


class CharacterTokenizer:
    eos_token_id = 999

    def __call__(self, text, **kwargs):
        return {"input_ids": [ord(c) for c in text],
                "offset_mapping": [(i, i + 1) for i in range(len(text))]}


def test_structural_weights_and_prompt_mask():
    completion = 'ACTIONNET_TEMPORAL_PROGRAM_V1\nSTEP {"event_id":"event-a","disposition":"EXECUTE"}\nCLAIM_STATE {"x":1}\nCLAIM_CERTIFICATE {"decision":"ALLOW"}\nEND_ACTIONNET_TEMPORAL_PROGRAM'
    row = {"case_id": "test", "prompt": "prompt\n", "completion": completion}
    uniform = encode_row(row, CharacterTokenizer(), common.config(), "uniform")
    structural = encode_row(row, CharacterTokenizer(), common.config(), "structural")
    assert uniform["input_ids"] == structural["input_ids"]
    assert uniform["labels"] == structural["labels"]
    assert structural["labels"][:7] == [-100] * 7
    assert structural["token_weights"][:7] == [0] * 7
    assert set(uniform["token_weights"][7:]) == {1}
    assert structural["token_weights"][-1] == 2
    body = completion.index('{"x"') + 7
    assert structural["token_weights"][body] == 1
    ident = completion.index("event-a") + 7
    assert structural["token_weights"][ident] == 2
    assert token_weights("STEP x", [(0, 0), (0, 4), (4, 6)], 2) == [1, 2, 2]


def test_length_budget_fails_closed():
    cfg = common.config()
    cfg["max_length"] = 1
    with pytest.raises(ValueError, match="truncation"):
        encode_row({"case_id": "x", "prompt": "abc", "completion": "def"}, CharacterTokenizer(), cfg, "uniform")


def test_immutable_evidence(tmp_path):
    path = tmp_path / "evidence.json"
    common.write_json(path, {"x": 1})
    common.write_json(path, {"x": 1})
    with pytest.raises(ValueError, match="replace"):
        common.write_json(path, {"x": 2})


def test_family_inference_does_not_count_paired_cases_as_independent(fresh):
    control = evaluation.score(fresh, predictions(fresh), "uniform", "development")
    repair = copy.deepcopy(control)
    control["program_exact_rate"] = 0
    control["event_order_exact_rate"] = 0
    for row in control["evaluations"]:
        row["program_exact"] = False
    result = evaluation.family_comparison(control, repair)
    assert result["family_wins"] == 16
    assert result["one_sided_family_sign_p"] == 2**-16
    assert result["passed"]
    assert evaluation.family_comparison(repair, repair)["one_sided_family_sign_p"] == 1


def test_confirmation_refused_before_any_materialization(tmp_path, monkeypatch):
    monkeypatch.setattr(run, "ROOT", tmp_path)
    def hold():
        raise ValueError("development did not qualify")
    monkeypatch.setattr(run, "require_selection", hold)
    with pytest.raises(ValueError, match="did not qualify"):
        run.confirmation()
    assert list(tmp_path.iterdir()) == []


def test_config_rejects_family_overlap(tmp_path, monkeypatch):
    cfg = common.config()
    cfg["splits"]["confirmation"]["family_start"] = cfg["splits"]["train"]["family_start"]
    path = tmp_path / "config.json"
    common.write_json(path, cfg)
    monkeypatch.setattr(common, "CONFIG", path)
    with pytest.raises(ValueError, match="overlap"):
        common.config()


def test_freeze_detects_data_and_source_mutation(tmp_path, monkeypatch):
    monkeypatch.setattr(common, "ROOT", tmp_path)
    sources = {"worker.py": "fixed"}
    monkeypatch.setattr(common, "source_hashes", lambda: dict(sources))
    common.write_rows(tmp_path / "prepared/train.jsonl", [{"case_id": "train"}])
    common.write_rows(tmp_path / "prepared/development.jsonl", [{"case_id": "dev"}])
    common.write_json(tmp_path / "prepared/qualification.json", {"passed": True})
    common.freeze()
    common.verify_freeze()
    sources["worker.py"] = "changed"
    with pytest.raises(ValueError, match="code/config changed"):
        common.verify_freeze()
    sources["worker.py"] = "fixed"
    with (tmp_path / "prepared/train.jsonl").open("ab") as handle:
        handle.write(b"\n")
    with pytest.raises(ValueError, match="train data changed"):
        common.verify_freeze()


def test_selection_rejects_edited_pass_flag(tmp_path, monkeypatch):
    monkeypatch.setattr(run, "ROOT", tmp_path)
    monkeypatch.setattr(run, "verify_freeze", lambda: None)
    monkeypatch.setattr(run, "score_split", lambda split: {})
    monkeypatch.setattr(run, "selection_payload", lambda scores: {"status": "DEVELOPMENT_HOLD"})
    common.write_json(tmp_path / "results/selection.json", {"status": "READY_FOR_CONFIRMATION"})
    with pytest.raises(ValueError, match="does not match"):
        run.require_selection()


def test_completed_prediction_resume_is_read_only_and_bound(tmp_path, monkeypatch):
    monkeypatch.setattr(gpu, "ROOT", tmp_path)
    cfg = common.config()
    cfg["splits"]["development"]["records"] = 2
    monkeypatch.setattr(gpu, "config", lambda: cfg)
    monkeypatch.setattr(gpu, "trained_manifest", lambda arm: {"adapter_sha256": "adapter"})
    def no_runtime():
        raise AssertionError("completed resume must not request GPU")
    monkeypatch.setattr(gpu, "runtime", no_runtime)
    common.write_json(tmp_path / "registration.json", {"test": True})
    common.write_rows(tmp_path / "prepared/development.jsonl", [{"case_id": "a"}, {"case_id": "b"}])
    output = tmp_path / "results/development-uniform-predictions.jsonl"
    common.write_rows(output, [{"case_id": "a", "raw_output": "x"}, {"case_id": "b", "raw_output": "y"}])
    before = output.read_bytes()
    gpu.predict("uniform", "development")
    gpu.predict("uniform", "development")
    assert output.read_bytes() == before
    monkeypatch.setattr(gpu, "trained_manifest", lambda arm: {"adapter_sha256": "different-adapter"})
    with pytest.raises(ValueError, match="replace"):
        gpu.predict("uniform", "development")


def test_prediction_prefix_mismatch_stops_before_gpu(tmp_path, monkeypatch):
    monkeypatch.setattr(gpu, "ROOT", tmp_path)
    cfg = common.config()
    cfg["splits"]["development"]["records"] = 2
    monkeypatch.setattr(gpu, "config", lambda: cfg)
    monkeypatch.setattr(gpu, "trained_manifest", lambda arm: {"adapter_sha256": "adapter"})
    common.write_json(tmp_path / "registration.json", {"test": True})
    common.write_rows(tmp_path / "prepared/development.jsonl", [{"case_id": "a"}, {"case_id": "b"}])
    common.write_rows(tmp_path / "results/development-uniform-predictions.jsonl", [{"case_id": "b"}])
    with pytest.raises(ValueError, match="prefix mismatch"):
        gpu.predict("uniform", "development")


def test_scoring_rejects_extra_or_duplicate_predictions(fresh):
    with pytest.raises(ValueError, match="cases differ"):
        evaluation.score(fresh, predictions(fresh) + predictions(fresh[:1]), "uniform", "development")
    bad = predictions(fresh)
    bad[-1] = bad[0]
    with pytest.raises(ValueError, match="cases differ"):
        evaluation.score(fresh, bad, "uniform", "development")


def test_case_family_mismatch_not_accepted(fresh):
    control = evaluation.score(fresh, predictions(fresh), "uniform", "development")
    repair = copy.deepcopy(control)
    repair["evaluations"][0]["semantic_family"] = -1
    with pytest.raises(ValueError, match="family mismatch"):
        evaluation.family_comparison(control, repair)