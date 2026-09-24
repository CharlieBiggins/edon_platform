"""Replay supplied Program-003 development evidence; never inspect confirmation."""
from collections import Counter
from core import ROOT, read, rows, file_hash, dependencies, write_json

EXPECTED = {
    "development (1).jsonl":"sha256:5d332dd9c124c945195181dd5b2749a72b59ec6d8a7874b5fd9c0fd306be1e21",
    "development-uniform-predictions (1).jsonl":"sha256:9cf5f2c538354b01ccbf586c5ce2652536c76a568300744e12af7d3d88a36631",
    "development-trace-predictions.jsonl":"sha256:a203810bcdb8ee32f496561cd4897f8fe2f84679e89325a718b418e574e52be7",
    "development-uniform-score (1).json":"sha256:16cdcd015718db56cf1d5407d072fb8622fe5f253b731cab528bb0df1a64e158",
    "development-trace-score.json":"sha256:9cef3dda90d673644acbb7603ffcef35a47670441f8d6bf5be44cc1b587977e5"}


def audit():
    from evaluate import label_mistake
    from data import RULES
    uploads=ROOT.parents[2]/"prism-uploads"
    for name,h in EXPECTED.items():
        if file_hash(uploads/name)!=h:raise ValueError("parent audit evidence differs: "+name)
    data=rows(uploads/"development (1).jsonl")
    _,_,_,ev,_=dependencies()
    for arm in ("uniform","trace"):
        predname="development-uniform-predictions (1).jsonl" if arm=="uniform" else "development-trace-predictions.jsonl"
        scorename="development-uniform-score (1).json" if arm=="uniform" else "development-trace-score.json"
        predicted=rows(uploads/predname);stored=read(uploads/scorename)
        if ev.score(data,predicted,arm,"development")!={k:v for k,v in stored.items() if k!="prediction_binding"}:
            raise ValueError("parent score replay mismatch")
    predicted={r["case_id"]:r for r in rows(uploads/"development-trace-predictions.jsonl")}
    labels=[label_mistake(r,predicted[r["case_id"]]) for r in data]
    labels=[x for x in labels if x["first_divergence"] is not None]
    result={"source_hashes":EXPECTED,"both_arms_replayed":True,"labels":labels,
            "first_divergence_counts":dict(Counter(x["first_divergence"] for x in labels)),
            "curriculum_rules":list(RULES),
            "selection_policy":"Rules fixed from mechanism-level audit; no scored case copied or renamed into training.",
            "new_model_mining_calls":0,"diagnostic_labels_are_training_targets":False,
            "confirmation_accessed":False,"binding_authority":False}
    write_json(ROOT/"prepared/parent-development-audit.json",result)
    return result


if __name__=="__main__":
    print(audit()["first_divergence_counts"])