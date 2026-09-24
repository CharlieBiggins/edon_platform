import json
import sys
from copy import deepcopy
from pathlib import Path

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import core
import data
from evaluate import summarize, compare, label_mistake
from gpu_worker import read_prefix


@pytest.fixture(scope="module")
def deps():return core.dependencies()


@pytest.fixture(scope="module")
def pairs(deps):
    broad,templates=data.ordinary("test",79000,1,26091091,deps)
    return [data.boundary_pair(templates[0],79100,i,"test",26091092,deps) for i in range(8)]


@pytest.mark.parametrize("index",range(8))
def test_boundary_contract(index,pairs,deps):
    a,b=pairs[index]
    assert a["counterfactual_pair_id"]==b["counterfactual_pair_id"]
    assert a["case_id"]!=b["case_id"]
    assert a["contrast_rule"]==data.RULES[index]
    for r in (a,b):data.qualify_row(r,deps)
    changed=a["compiler_input"]["oracle_certificate"]["decision"]!=b["compiler_input"]["oracle_certificate"]["decision"]
    assert changed==(index<6)
    if index==7:assert data.fingerprint(a)==data.fingerprint(b)


def test_deterministic_boundary(pairs,deps):
    _,templates=data.ordinary("test",79000,1,26091091,deps)
    assert data.boundary_pair(templates[0],79100,0,"test",26091092,deps)==pairs[0]


@pytest.mark.parametrize("kind",["prompt","trace","completion","actor","event_id"])
def test_corrupt_target_fails(kind,pairs,deps):
    r=deepcopy(pairs[0][0])
    if kind=="prompt":r["prompt"]+="\nHere is the answer: ALLOW"
    elif kind=="trace":r["trace_completion"]+="wrong"
    elif kind=="completion":r["completion"]="wrong"
    elif kind=="actor":r["compiler_input"]["program_source"]["submitted_events"][0]["actor_id"]="unknown"
    else:r["compiler_input"]["program_source"]["submitted_events"][1]["event_id"]=r["compiler_input"]["program_source"]["submitted_events"][0]["event_id"]
    with pytest.raises(ValueError):data.qualify_row(r,deps)


def test_split_protection(pairs):
    pair=pairs[0]
    with pytest.raises(ValueError):data.validate_splits({"train-ordinary":pair,"development":pair})
    with pytest.raises(ValueError):data.validate_splits({"train-ordinary":pair[:1]})
    with pytest.raises(ValueError):data.validate_splits({"train-ordinary":pair},pair)
    assert data.validate_splits({"train-ordinary":pair,"train-boundary":pair})


def test_predicate_first_error(pairs,deps):
    r=pairs[5][1];_,trace,_,_,_=deps
    actual=trace.build_trace(r["compiler_input"]["program_source"])
    actual["derivation"]["decision"]="ALLOW"
    p={"raw_output":trace.render_trace(actual)+"\n"+r["completion"]}
    label=label_mistake(r,p)
    assert label["first_divergence"]=="DECISION_DERIVATION"
    assert label["origin"]=="OBSERVED_MODEL_OUTPUT"
    assert label["internal_cause_established"] is False


def test_parse_error_label(pairs):
    assert label_mistake(pairs[0][0],{"raw_output":"invalid"})["first_divergence"]=="PARSE"


def oracle_predictions(rr):
    return [{"case_id":r["case_id"],"raw_output":r["trace_completion"]+"\n"+r["completion"],
             "ended_with_eos":True,"hit_generation_limit":False} for r in rr]


def test_oracle_scoring_and_tie_hold(pairs):
    rr=[deepcopy(r) for pair in pairs for r in pair]
    for r in rr[:8]:r["stratum"]="ordinary"
    s=summarize(rr,oracle_predictions(rr))
    assert s["program_exact_rate"]==1 and s["trace_exact_rate"]==1
    assert s["all_metrics"]["allow_error_rate"]==0
    assert s["ordinary_metrics"]["count"]==8
    result=compare(s,s,s)
    assert not result["passed"] and result["one_sided_family_sign_p"]==1


def test_gate_rejects_unsafe_and_retention(pairs):
    rr=[deepcopy(r) for pair in pairs for r in pair]
    for r in rr[:8]:r["stratum"]="ordinary"
    s=summarize(rr,oracle_predictions(rr)); bad=deepcopy(s)
    bad["raw_claim_unsafe_authorizations"]=1
    bad["ordinary_metrics"]["program_exact"]=0.9
    bad["all_metrics"]["unnecessary_abstention_rate"]=0.1
    c=compare(s,bad,s)["checks"]
    assert not c["zero_unsafe_and_unexamined"]
    assert not c["ordinary_retention_vs_parent"]
    assert not c["unnecessary_abstention_rate_vs_control"]


def test_immutable_evidence(tmp_path):
    p=tmp_path/"evidence.json"
    core.write_json(p,{"a":1});core.write_json(p,{"a":1})
    with pytest.raises(ValueError):core.write_json(p,{"a":2})
    assert core.read(p)=={"a":1}


@pytest.mark.parametrize("text",["{\"x\":1,\"x\":2}","{\"x\":NaN}","{\"x\":Infinity}"])
def test_strict_json(text):
    with pytest.raises(ValueError):core.parse(text)


def test_prefix_recovery_and_bad_ids(tmp_path):
    p=tmp_path/"predictions.jsonl"
    core.write_once(p,b"{\"case_id\":\"a\"}\n{broken")
    records,valid=read_prefix(p,["a","b"])
    assert len(records)==1 and valid==b"{\"case_id\":\"a\"}\n"
    assert p.read_bytes().endswith(b"{broken") # parser itself does not mutate
    with pytest.raises(ValueError):read_prefix(p,["b","a"])
    q=tmp_path/"interior.jsonl";core.write_once(q,b"broken\n{\"case_id\":\"a\"}\n")
    with pytest.raises(ValueError):read_prefix(q,["a"])


def test_parent_adapter_missing_rejected(tmp_path):
    with pytest.raises(ValueError):core.verify_parent(tmp_path)


def test_parent_pin():
    assert len(core.inherited_sources())==75


def test_hold_never_materializes_confirmation(monkeypatch,tmp_path):
    import run
    monkeypatch.setattr(run,"ROOT",tmp_path)
    monkeypatch.setattr(run,"verify",lambda:None)
    monkeypatch.setattr(run,"verify_parent",lambda _:"parent")
    value={"status":"DEVELOPMENT_HOLD"}
    monkeypatch.setattr(run,"selection",lambda _:value)
    core.write_json(tmp_path/"results/selection.json",value)
    with pytest.raises(ValueError):run.materialize_confirmation(Path("parent"))
    assert not (tmp_path/"results/confirmation-access.json").exists()
    assert not (tmp_path/"prepared/confirmation.jsonl").exists()


def test_changed_selection_rejected(monkeypatch,tmp_path):
    import run
    monkeypatch.setattr(run,"ROOT",tmp_path)
    monkeypatch.setattr(run,"verify",lambda:None)
    monkeypatch.setattr(run,"verify_parent",lambda _:"parent")
    monkeypatch.setattr(run,"selection",lambda _:{"status":"DEVELOPMENT_HOLD"})
    core.write_json(tmp_path/"results/selection.json",{"status":"READY_FOR_CONFIRMATION"})
    with pytest.raises(ValueError):run.required_selection(Path("parent"))


def test_foreign_parent_hash_rejected(tmp_path):
    core.write_once(tmp_path/"adapter_model.safetensors",b"not-a-real-adapter")
    with pytest.raises(ValueError):core.verify_parent(tmp_path)


def test_registered_exposure():
    c=core.cfg()
    assert c["epochs"]*c["training_records"]==512
    assert c["max_steps"]*c["effective_batch_size"]==512
    assert c["targeted_records"]==c["rehearsal_records"]==256
    assert c["development"]["records"]==c["confirmation"]["records"]==256


def test_ordinary_actor_reference_closure(deps):
    rr,_=data.ordinary("reference-test",79500,2,26091100,deps)
    assert len(rr)==16
    for r in rr:
        s=r["compiler_input"]["program_source"]
        ids={a["actor_id"] for a in s["initial_state"]["actors"].values()}
        assert all(e["actor_id"] in ids for e in s["submitted_events"])


def test_single_primitive_change(pairs):
    def leaves(a,b,path=()):
        if type(a) is dict and type(b) is dict:
            return sum((leaves(a[k],b[k],path+(k,)) for k in a),[])
        if type(a) is list and type(b) is list and len(a)==len(b):
            return sum((leaves(x,y,path+(i,)) for i,(x,y) in enumerate(zip(a,b))),[])
        return [] if a==b else [path]
    for i,pair in enumerate(pairs[:7]):
        a,b=[r["compiler_input"]["program_source"] for r in pair]
        assert len(leaves(a,b))==1,(i,leaves(a,b))


def test_actual_hash_bound_parent_score_replay(deps):
    upload=core.ROOT.parents[2]/"prism-uploads"
    if not (upload/"development-trace-predictions.jsonl").exists():pytest.skip("external audit upload absent in handoff")
    from audit_parent import EXPECTED
    for name,h in EXPECTED.items():assert core.file_hash(upload/name)==h
    _,_,_,ev,_=deps
    rr=core.rows(upload/"development (1).jsonl")
    pp=core.rows(upload/"development-trace-predictions.jsonl")
    actual=ev.score(rr,pp,"trace","development")
    expected=core.read(upload/"development-trace-score.json")
    assert actual=={k:v for k,v in expected.items() if k!="prediction_binding"}


def test_nonfinite_prediction_rejected_as_interior(tmp_path):
    p=tmp_path/"bad.jsonl"
    core.write_once(p,b"{\"case_id\":\"a\",\"x\":NaN}\n{\"case_id\":\"b\"}\n")
    with pytest.raises(ValueError):read_prefix(p,["a","b"])


def test_duplicate_prediction_rejected(tmp_path):
    p=tmp_path/"duplicate.jsonl"
    core.write_once(p,b"{\"case_id\":\"a\"}\n{\"case_id\":\"a\"}\n")
    with pytest.raises(ValueError):read_prefix(p,["a","b"])


def test_mixed_report_is_canonical_json(pairs):
    a,b=deepcopy(pairs[0]),deepcopy(pairs[1])
    for r in a:r["contrast_rule"]=None
    report=data.validate_splits({"train-boundary":a+b})
    assert "ORDINARY" in core.canonical(report)