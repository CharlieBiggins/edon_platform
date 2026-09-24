"""CPU contract/regression tests; tensor loss is checked separately on the GPU runtime."""
import json
import sys
from copy import deepcopy
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import IR, config, canonical, immutable_bytes
from trace_ir import (build_trace, render_trace, split_output, derivation, changes,
                      prompt_for, completion_for, strict_json)
from prepare import generate_split, validate_splits
from evaluation import score, family_comparison
from loss import encode_row
from diagnose_claims import replace_claims


@pytest.fixture(scope="module")
def rows():
    return generate_split("development", config())[0]


def predictions(rows, arm):
    return [{"case_id": r["case_id"], "raw_output": completion_for(r, arm),
             "ended_with_eos": True, "hit_generation_limit": False,
             "generated_token_count": 1, "prompt_token_count": 1} for r in rows]


@pytest.mark.parametrize("arm", ["uniform", "trace"])
def test_oracle_end_to_end(rows, arm):
    result = score(rows, predictions(rows, arm), arm, "development")
    assert result["program_exact_rate"] == result["joint_trace_program_exact_rate"] == 1
    assert result["gate_passed"] and result["raw_claim_unsafe_authorizations"] == 0


def test_generation_is_deterministic(rows):
    again, _ = generate_split("development", config())
    assert again == rows
    validate_splits({"development": rows})


def test_confirmation_is_not_materialized():
    with pytest.raises(ValueError, match="authorized access"):
        generate_split("confirmation", config())


def test_overlap_rejected(rows):
    with pytest.raises(ValueError, match="split overlap"):
        validate_splits({"a": rows, "b": rows})


def test_every_trace_replays_both_engines(rows):
    for r in rows:
        source = r["compiler_input"]["program_source"]
        trace = build_trace(source)
        decoded, final = split_output(completion_for(r, "trace"), "trace")
        assert decoded == trace and final == r["completion"]
        assert all(not t["changes"] for t in trace["records"] if t["disposition"] == "DEFER")


def test_time_boundary_inclusive(rows):
    source = deepcopy(rows[0]["compiler_input"]["program_source"])
    event = source["submitted_events"][0]
    source["initial_state"]["request"]["query_time"] = event["time"]
    trace = build_trace(source)
    assert next(t for t in trace["records"] if t["event_id"] == event["event_id"])["disposition"] == "EXECUTE"
    source["initial_state"]["request"]["query_time"] -= 1
    trace = build_trace(source)
    assert next(t for t in trace["records"] if t["event_id"] == event["event_id"])["disposition"] == "DEFER"


def test_order_uses_all_four_keys(rows):
    source = rows[0]["compiler_input"]["program_source"]
    keys = [t["key"] for t in build_trace(source)["records"]]
    assert keys == sorted(keys)


def test_false_trace_cannot_pass_via_correct_final(rows):
    preds = predictions(rows, "trace")
    trace, final = split_output(preds[0]["raw_output"], "trace")
    trace["records"][0]["query_time"] += 1
    # Corrupt every trace: native scores stay perfect, the trace gate must fail.
    for p in preds:
        t, f = split_output(p["raw_output"], "trace")
        t["records"][0]["query_time"] += 1
        p["raw_output"] = render_trace(t) + "\n" + f
    result = score(rows, preds, "trace", "development")
    assert result["program_exact_rate"] == 1
    assert result["trace_exact_rate"] == 0 and not result["gate_passed"]


@pytest.mark.parametrize("text", ["{} trailing", "{\"x\":1,\"x\":2}", "{\"x\":NaN}"])
def test_strict_trace_json(text):
    with pytest.raises(ValueError):
        strict_json(text)


def test_envelope_errors_fail_closed(rows):
    preds = predictions(rows, "trace")
    preds[0]["raw_output"] = "unregistered prose\n" + preds[0]["raw_output"]
    result = score(rows, preds, "trace", "development")
    assert not result["evaluations"][0]["parse_valid"]
    assert result["trace_diagnostics"][0]["envelope_error"]


def test_malformed_trace_does_not_hide_unsafe_claim(rows):
    row = next(r for r in rows if r["compiler_input"]["oracle_certificate"]["decision"] != "ALLOW")
    p = predictions([row], "trace")[0]
    program = IR.parse_program_a(row["completion"])
    program["claim_certificate"]["decision"] = "ALLOW"
    p["raw_output"] = "BROKEN_TRACE\n" + IR.render_program(program)
    result = score([row], [p], "trace", "development")
    assert result["raw_claim_unsafe_authorizations"] == 1
    assert not result["evaluations"][0]["parse_valid"]


def test_no_final_output_repair(rows):
    preds = predictions(rows, "trace")
    t, f = split_output(preds[0]["raw_output"], "trace")
    program = IR.parse_program_a(f)
    program["steps"][0], program["steps"][1] = program["steps"][1], program["steps"][0]
    preds[0]["raw_output"] = render_trace(t) + "\n" + IR.render_program(program)
    result = score(rows, preds, "trace", "development")
    assert not result["evaluations"][0]["event_order_exact"]
    assert not result["evaluations"][0]["program_exact"]


def test_claim_ablation_changes_only_claims(rows):
    row = rows[0]
    p = predictions([row], "uniform")[0]
    program = IR.parse_program_a(p["raw_output"])
    program["claim_certificate"]["decision"] = "BOGUS"
    p["raw_output"] = IR.render_program(program)
    replaced = replace_claims(row, p)
    result = IR.parse_program_a(replaced["raw_output"])
    assert result["steps"] == program["steps"]
    assert result == IR.parse_program_a(row["completion"])


def test_duplicate_predictions_rejected(rows):
    preds = predictions(rows, "uniform")
    preds[1] = preds[0]
    with pytest.raises(ValueError, match="cases differ"):
        score(rows, preds, "uniform", "development")


def test_high_performance_tie_is_hold(rows):
    u = score(rows, predictions(rows, "uniform"), "uniform", "development")
    t = score(rows, predictions(rows, "trace"), "trace", "development")
    comparison = family_comparison(u, t)
    assert comparison["one_sided_family_sign_p"] == 1
    assert not comparison["passed"]


def test_boolean_not_interchangeable_with_integer(rows):
    preds = predictions(rows, "trace")
    t, f = split_output(preds[0]["raw_output"], "trace")
    t["derivation"]["blocked_checks"][0][1] = int(t["derivation"]["blocked_checks"][0][1])
    preds[0]["raw_output"] = render_trace(t) + "\n" + f
    result = score(rows, preds, "trace", "development")
    assert not result["trace_diagnostics"][0]["trace_exact"]


class FakeTokenizer:
    eos_token_id = 0
    def __call__(self, text, **kwargs):
        return {"input_ids": [ord(c) + 1 for c in text]}


@pytest.mark.parametrize("arm", ["uniform", "trace"])
def test_masking_and_eos(rows, arm):
    cfg = {**config(), "max_length": 100000, "max_new_tokens": 100000, "inference_max_input_tokens": 100000}
    encoded = encode_row(rows[0], FakeTokenizer(), cfg, arm)
    n = len(prompt_for(rows[0]["prompt"], arm))
    assert all(x == -100 for x in encoded["labels"][:n])
    assert all(x == 0 for x in encoded["token_weights"][:n])
    assert all(x == 1 for x in encoded["token_weights"][n:])
    assert encoded["labels"][-1] == 0


def test_target_budget_enforced(rows):
    cfg = {**config(), "max_length": 100000, "inference_max_input_tokens": 100000, "max_new_tokens": 1}
    with pytest.raises(ValueError, match="generation budget"):
        encode_row(rows[0], FakeTokenizer(), cfg, "trace")


def test_prompt_independent_of_oracle_fields(rows):
    row = deepcopy(rows[0])
    before = prompt_for(row["prompt"], "trace")
    row["completion"] = row["trace_completion"] = "POISON_ORACLE"
    row["compiler_input"] = {}
    assert prompt_for(row["prompt"], "trace") == before


def test_immutable_evidence(tmp_path):
    path = tmp_path / "evidence.json"
    immutable_bytes(path, b"original")
    immutable_bytes(path, b"original")
    with pytest.raises(ValueError, match="refusing"):
        immutable_bytes(path, b"changed")


def test_forged_selection_and_hold_cannot_open_confirmation(rows, monkeypatch):
    import run
    u = score(rows, predictions(rows, "uniform"), "uniform", "development")
    t = score(rows, predictions(rows, "trace"), "trace", "development")
    for s in (u, t):
        s["prediction_binding"] = {"adapter_sha256": "test-adapter"}
    monkeypatch.setattr(run, "verify_freeze", lambda: {})
    monkeypatch.setattr(run, "file_hash", lambda path: "sha256:test")
    monkeypatch.setattr(run, "score_split", lambda split: {"uniform": u, "trace": t})
    legitimate = run.selection_payload({"uniform": u, "trace": t})
    forged = {**legitimate, "status": "READY_FOR_CONFIRMATION", "selected_arm": "trace"}
    monkeypatch.setattr(run, "read_json", lambda path: forged)
    with pytest.raises(ValueError, match="does not match"):
        run.confirmation()
    monkeypatch.setattr(run, "read_json", lambda path: legitimate)
    with pytest.raises(ValueError, match="did not qualify"):
        run.confirmation()


def test_family_sign_test_uses_families_not_cases(rows):
    u = score(rows, predictions(rows, "uniform"), "uniform", "development")
    t = deepcopy(u)
    # Five positive families, all remaining families tied: p=1/32.
    families = sorted({r["semantic_family"] for r in u["evaluations"]})[:5]
    for family in families:
        next(r for r in u["evaluations"] if r["semantic_family"] == family)["program_exact"] = False
    u["program_exact_rate"] -= 5 / len(rows)
    comparison = family_comparison(u, t)
    assert comparison["family_wins"] == 5
    assert comparison["one_sided_family_sign_p"] == 1 / 32
    assert comparison["passed"]


def test_restore_only_recovers_hash_matching_newline():
    from restore import recover, digest
    assert recover(b"data", digest(b"data\n")) == b"data\n"
    with pytest.raises(ValueError, match="trusted registration"):
        recover(b"changed", digest(b"data\n"))


def test_change_records_retain_arrays_and_types():
    assert changes({"a": [1]}, {"a": [1, 2]}) == [["a", [1], [1, 2]]]
    assert changes(True, 1, "flag") == [["flag", True, 1]]


def test_decision_precedence_and_capacity(rows):
    # Use an oracle-ALLOW final state so unrelated conditions are initially clear.
    row = next(r for r in rows if r["compiler_input"]["oracle_certificate"]["decision"] == "ALLOW")
    state = deepcopy(row["compiler_input"]["oracle_state"])
    state["resources"]["reserved"] = state["resources"]["capacity"]
    d = derivation(state)
    assert d["decision"] == "ABSTAIN" and d["first_failure"] == "RESOURCE_CAPACITY"
    state["policy"]["allows"] = False
    d = derivation(state)
    assert d["decision"] == "DENY" and d["first_failure"] == "POLICY"
    state["request"]["well_formed"] = False
    assert derivation(state)["decision"] == "INVALID"