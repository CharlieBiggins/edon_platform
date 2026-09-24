"""Deterministic fresh 48-case instrument built from the registered generator closure."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
MATCHED001 = ROOT.parent / "CEREBRUM-ACTIONNET-MATCHED-001"
ID = "CEREBRUM-ACTIONNET-MATCHED-002"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(payload):
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def opaque(kind, *parts):
    value = "\x1f".join((ID, kind, *(str(part) for part in parts))).encode()
    return kind + "-" + hashlib.sha256(value).hexdigest()[:24]


def _rename(values):
    pairs, result = {}, []
    for row in values:
        pair = row["counterfactual_pair_id"]
        pairs.setdefault(pair, opaque("pair", pair))
        value = deepcopy(row)
        value["source_case_id"] = row["case_id"]
        value["source_counterfactual_pair_id"] = pair
        value["case_id"] = opaque("case", row["case_id"])
        value["counterfactual_pair_id"] = pairs[pair]
        value["matched_protocol_id"] = ID
        result.append(value)
    return result


def generate():
    sys.path.insert(0, str(MATCHED001))
    import dataset as matched_data
    import foundation as matched_foundation
    config001 = matched_foundation.read(MATCHED001 / "config.json")
    prior = matched_data.generate_bundle(config001)
    inherited_data = sys.modules["data"]
    core = sys.modules["core"]
    deps = core.dependencies()
    prior_rows = prior["train_scenarios"] + prior["screen_reference"]
    inherited_data.EXCLUDED.update(inherited_data.fingerprint(row) for row in prior_rows)
    before = set(inherited_data.EXCLUDED)
    value = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    generation = value["generation"]
    # As in Matched-001, freeze boundary templates first so ordinary-pair
    # acquisition cannot consume their reference-closed candidates.
    targeted = inherited_data.boundaries("matched002-locked", generation["targeted_start"],
        generation["targeted_families"], generation["targeted_seed"], deps)
    require(len(targeted) == 24, "Locked targeted inventory differs")
    inherited_data.EXCLUDED.update(inherited_data.fingerprint(row) for row in targeted)
    broad, _ = inherited_data.ordinary("matched002-locked", generation["ordinary_start"],
        generation["ordinary_families"], generation["ordinary_seed"], deps)
    require(len(broad) == 24, "Locked ordinary inventory differs")
    inherited_data.EXCLUDED.update(inherited_data.fingerprint(row) for row in broad)
    source = broad + targeted
    for row in source:
        inherited_data.qualify_row(row, deps)
        require(inherited_data.fingerprint(row) not in before, "Matched-001 or predecessor overlap")
    rows = _rename(source)
    require(len(rows) == 48 and len({row["case_id"] for row in rows}) == 48, "Case inventory differs")
    pairs = Counter(row["counterfactual_pair_id"] for row in rows)
    require(len(pairs) == 24 and set(pairs.values()) == {2}, "Pair inventory differs")
    require(set(row["compiler_input"]["oracle_certificate"]["decision"] for row in rows)
            == matched_foundation.DECISIONS, "Decision coverage differs")
    targeted_rows = [row for row in rows if row["stratum"] == "boundary"]
    require(Counter(row["contrast_rule"] for row in targeted_rows)
            == {rule: 4 for rule in matched_foundation.RULES}, "Mechanism coverage differs")
    inputs = [{"case_id": row["case_id"], "prompt": matched_data.native_prompt(row)} for row in rows]
    report = {"protocol_id": ID, "records": 48, "pairs": 24,
        "ordinary_records": len(broad), "targeted_records": len(targeted),
        "decision_counts": dict(Counter(row["compiler_input"]["oracle_certificate"]["decision"] for row in rows)),
        "mechanism_counts": dict(Counter((row["contrast_rule"] or "ORDINARY") for row in rows)),
        "matched001_training_records_excluded": len(prior["train_scenarios"]),
        "matched001_screen_records_excluded": len(prior["screen_reference"]),
        "freshness_limit": "Registered alpha-normalized project exposure exclusion; not independent novelty proof",
        "reference_sha256": digest("".join(canonical(row) + "\n" for row in rows).encode()),
        "inputs_sha256": digest("".join(canonical(row) + "\n" for row in inputs).encode()),
        "transfer_authorized": False, "binding_authority": False}
    return rows, inputs, report