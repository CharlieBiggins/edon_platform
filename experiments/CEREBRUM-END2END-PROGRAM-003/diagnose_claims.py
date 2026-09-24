"""CPU-only diagnostic: replace claims, never steps; frozen scores are untouched."""
import argparse
from copy import deepcopy
from pathlib import Path

from common import IR, ROOT, read_json, read_rows, file_hash, write_json, summarize, config
from common import legacy_evaluate


def replace_claims(row, prediction):
    source = row["compiler_input"]["program_source"]
    left = IR.parse_program_a(prediction["raw_output"])
    right = IR.parse_program_b(prediction["raw_output"])
    if left != right:
        raise ValueError("parser disagreement")
    a = IR._execute(source["initial_state"], source["submitted_events"], left,
                    IR.BASE.transition_a, IR.BASE.evaluate_a)
    b = IR._execute(source["initial_state"], source["submitted_events"], right,
                    IR.BASE.transition_b, IR.BASE.evaluate_b)
    if a != b:
        raise ValueError("executor disagreement")
    modified = deepcopy(left)
    modified["claim_state"], modified["claim_certificate"] = a
    assert modified["steps"] == left["steps"]
    # Original generation telemetry remains attached; this is NOT a new model output.
    return {**prediction, "raw_output": IR.render_program(modified)}


def diagnostic(inputs, paths, scores):
    rows = read_rows(inputs)
    report = {"kind": "POST_HOC_EXECUTOR_DERIVED_CLAIMS_ABLATION", "arms": {},
              "input_sha256": file_hash(inputs), "steps_modified": False,
              "claim_boundary": "Architectural diagnostic, not learned improvement or promotion.",
              "confirmation_accessed": False, "binding_authority": False,
              "transfer_authorized": False}
    for arm in ("uniform", "structural"):
        original = read_rows(paths[arm])
        saved = read_json(scores[arm])
        binding = saved["prediction_binding"]
        if binding["input_sha256"] != file_hash(inputs) or binding["predictions_sha256"] != file_hash(paths[arm]):
            raise ValueError("uploaded evidence hash mismatch")
        byid = {p["case_id"]: p for p in original}
        baseline = legacy_evaluate(rows, original)
        # Legacy evaluator does not attach family IDs.
        for ev, row in zip(baseline, rows):
            ev["semantic_family"] = row["semantic_family"]
        if baseline != saved["evaluations"]:
            raise ValueError("original evaluation replay differs")
        replaced = [replace_claims(row, byid[row["case_id"]]) for row in rows]
        evaluations = legacy_evaluate(rows, replaced)
        summary = summarize(evaluations, config()["absolute_gate"])
        report["arms"][arm] = {
            "source_predictions_sha256": file_hash(paths[arm]),
            "source_score_sha256": file_hash(scores[arm]),
            "original_program_exact": sum(r["program_exact"] for r in baseline),
            "derived_claims_program_exact": sum(r["program_exact"] for r in evaluations),
            "original_decision_correct": sum(r["decision_correct"] for r in baseline),
            "derived_claims_decision_correct": sum(r["decision_correct"] for r in evaluations),
            "diagnostic_summary": summary, "diagnostic_evaluations": evaluations,
            "recovered_case_ids": [a["case_id"] for a, b in zip(baseline, evaluations)
                                   if not a["program_exact"] and b["program_exact"]],
        }
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--uploads", type=Path, default=Path("prism-uploads"))
    args = parser.parse_args()
    u = args.uploads
    result = diagnostic(u / "development.jsonl",
        {a: u / f"development-{a}-predictions_2.jsonl" for a in ("uniform", "structural")},
        {a: u / f"development-{a}-score.json" for a in ("uniform", "structural")})
    write_json(ROOT / "audits/claim-replacement.json", result)
    for arm, r in result["arms"].items():
        print(arm, "exact", r["original_program_exact"], "->", r["derived_claims_program_exact"],
              "decisions", r["original_decision_correct"], "->", r["derived_claims_decision_correct"])