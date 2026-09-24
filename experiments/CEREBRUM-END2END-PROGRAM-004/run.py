"""All paid stages require an explicit command; no automatic cloud launch."""
import argparse
import contextlib
import json
import os
from pathlib import Path
import subprocess
import sys

from core import (ROOT, cfg, rows, read, verify, write_json, write_rows, file_hash,
                  verify_parent, object_hash)


@contextlib.contextmanager
def lock():
    import fcntl
    with (ROOT/".run.lock").open("a+") as f:
        try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise RuntimeError("another Program-004 runner is active")
        yield


def scores(split,parent):
    from evaluate import summarize
    from gpu_worker import validate_predictions
    inputs=rows(ROOT/"prepared"/(split+".jsonl"))
    result={}
    for arm in ("ordinary","boundary","parent"):
        result[arm]=summarize(inputs,validate_predictions(arm,split,parent))
        result[arm]["arm"]=arm;result[arm]["split"]=split
        result[arm]["prediction_sha256"]=file_hash(ROOT/"results"/f"{split}-{arm}-predictions.jsonl")
    return result


def selection(parent):
    from evaluate import compare
    result=scores("development",parent)
    comparison=compare(result["ordinary"],result["boundary"],result["parent"])
    return {"protocol_id":cfg()["protocol_id"],"registration_sha256":file_hash(ROOT/"registration.json"),
        "status":"READY_FOR_CONFIRMATION" if comparison["passed"] else "DEVELOPMENT_HOLD",
        "selected_arm":"boundary" if comparison["passed"] else None,"comparison":comparison,
        "score_hashes":{arm:object_hash(value) for arm,value in result.items()},
        "confirmation_accessed":False,"binding_authority":False,"transfer_authorized":False}


def required_selection(parent):
    verify(); verify_parent(parent)
    value=selection(parent)
    if read(ROOT/"results/selection.json")!=value:raise ValueError("selection differs from raw bound evidence")
    if value["status"]!="READY_FOR_CONFIRMATION":raise ValueError("development hold; confirmation prohibited")
    return value


def access_binding(parent):
    required_selection(parent)
    return {"registration_sha256":file_hash(ROOT/"registration.json"),
            "selection_sha256":file_hash(ROOT/"results/selection.json"),
            "parent_adapter_sha256":verify_parent(parent),"split_spec":cfg()["confirmation"],
            "binding_authority":False,"transfer_authorized":False}


def verify_access(parent):
    if read(ROOT/"results/confirmation-access.json")!=access_binding(parent):
        raise ValueError("confirmation access binding changed")
    manifest=read(ROOT/"results/confirmation-input.json")
    if manifest!={"input_sha256":file_hash(ROOT/"prepared/confirmation.jsonl"),
                  "access_sha256":file_hash(ROOT/"results/confirmation-access.json")}:
        raise ValueError("confirmation input changed")


def materialize_confirmation(parent):
    import data
    from core import dependencies
    write_json(ROOT/"results/confirmation-access.json",access_binding(parent))
    # Access is permanently recorded BEFORE generation, even if generation or budgets subsequently fail.
    if (ROOT/"results/confirmation-input.json").exists():
        verify_access(parent);return
    data.EXCLUDED.clear();data.EXCLUDED.update(read(ROOT/"prepared/exclusions.json"))
    existing={name:rows(ROOT/"prepared"/(name+".jsonl")) for name in ("train-ordinary","train-boundary","development")}
    data.EXCLUDED.update(data.fingerprint(r) for rr in existing.values() for r in rr)
    fresh=data.generate("confirmation",dependencies())
    data.validate_splits({**existing,**fresh})
    write_rows(ROOT/"prepared/confirmation.jsonl",fresh["confirmation"])
    write_json(ROOT/"results/confirmation-input.json",{
        "input_sha256":file_hash(ROOT/"prepared/confirmation.jsonl"),
        "access_sha256":file_hash(ROOT/"results/confirmation-access.json")})


def worker(stage,arm,split,parent):
    code=("from pathlib import Path; import gpu_worker as w; " +
          ("w.train" if stage=="train" else "w.predict") +
          (f"({arm!r},Path({str(parent)!r}))" if stage=="train" else f"({arm!r},{split!r},Path({str(parent)!r}))"))
    subprocess.run([sys.executable,"-B","-u","-c",code],cwd=ROOT,check=True)


def development(parent):
    from gpu_worker import runtime_preflight
    if (ROOT/"results/confirmation-access.json").exists():raise ValueError("development is closed")
    runtime_preflight(parent)
    for arm in cfg()["arms"]:worker("train",arm,"development",parent)
    # Both arms finish before any model is evaluated. Parent is a reference, never selected.
    for arm in (*cfg()["arms"],"parent"):worker("predict",arm,"development",parent)
    for arm,value in scores("development",parent).items():write_json(ROOT/"results"/f"development-{arm}-score.json",value)
    value=selection(parent);write_json(ROOT/"results/selection.json",value)
    return value


def confirmation(parent):
    from gpu_worker import runtime_preflight
    from evaluate import compare
    required_selection(parent);runtime_preflight(parent);materialize_confirmation(parent)
    for arm in (*cfg()["arms"],"parent"):worker("predict",arm,"confirmation",parent)
    result=scores("confirmation",parent)
    for arm,value in result.items():write_json(ROOT/"results"/f"confirmation-{arm}-score.json",value)
    comparison=compare(result["ordinary"],result["boundary"],result["parent"])
    final={"status":"CONFIRMED_SINGLE_SEED_CURRICULUM_SIGNAL" if comparison["passed"] else "CONFIRMATION_HOLD",
        "comparison":comparison,"access":read(ROOT/"results/confirmation-access.json"),
        "score_hashes":{arm:object_hash(value) for arm,value in result.items()},
        "binding_authority":False,"transfer_authorized":False}
    write_json(ROOT/"results/final.json",final);return final


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage",choices=("prepare","preflight","runtime","development","confirmation","bundle"))
    parser.add_argument("--parent",default="../CEREBRUM-END2END-PROGRAM-003/artifacts/trace/adapter")
    args=parser.parse_args()
    os.chdir(ROOT)
    parent=Path(args.parent)
    if parent.is_absolute():raise ValueError("use a workspace-relative parent path")
    with lock():
        if args.stage=="prepare":
            from data import prepare
            result=prepare()
        elif args.stage=="preflight":
            verify();result={"status":"CPU_PREFLIGHT_PASSED","parent_adapter_checked":False,"gpu_runtime_checked":False}
        elif args.stage=="runtime":
            from gpu_worker import runtime_preflight
            result=runtime_preflight(parent)
        elif args.stage=="development":result=development(parent)
        elif args.stage=="confirmation":result=confirmation(parent)
        else:
            from bundle import bundle
            result=bundle()
        print(json.dumps(result,indent=2))


if __name__=="__main__":main()