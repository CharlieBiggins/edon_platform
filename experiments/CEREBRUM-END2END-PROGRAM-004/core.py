"""Versioned curriculum experiment; inherited semantics are read-only."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parent
EXPERIMENTS = ROOT.parent
PARENT = EXPERIMENTS / "CEREBRUM-END2END-PROGRAM-003"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(data):
    return "sha256:" + hashlib.sha256(data).hexdigest()


def object_hash(value):
    return digest(canonical(value).encode())


def strict_pairs(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError("duplicate JSON key: " + k)
        out[k] = v
    return out


def parse(text):
    def reject(value):
        raise ValueError("nonfinite JSON: " + value)
    return json.loads(text, object_pairs_hook=strict_pairs, parse_constant=reject)


def read(path):
    return parse(Path(path).read_text(encoding="utf-8"))


def rows(path):
    result = [parse(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]
    if len({r["case_id"] for r in result}) != len(result):
        raise ValueError("duplicate case IDs")
    return result


def file_hash(path):
    return digest(Path(path).read_bytes())


def write_once(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError("immutable evidence differs: " + str(path))
    else:
        with path.open("xb") as f:
            f.write(data)


def write_json(path, value):
    write_once(path, (canonical(value) + "\n").encode())


def write_rows(path, values):
    write_once(path, "".join(canonical(v) + "\n" for v in values).encode())


def cfg():
    c = read(ROOT / "config.json")
    if c["arms"] != ["ordinary", "boundary"] or c["binding_authority"] or c["transfer_authorized"]:
        raise ValueError("protocol arm/authority mismatch")
    if c["targeted_records"] + c["rehearsal_records"] != c["training_records"]:
        raise ValueError("curriculum mixture count mismatch")
    if c["epochs"] * c["training_records"] != c["max_steps"] * c["effective_batch_size"]:
        raise ValueError("training exposure mismatch")
    if c["train"]["ordinary_families"] * 8 != c["training_records"] or c["train"]["boundary_families"] * 16 != c["targeted_records"]:
        raise ValueError("generator/training count mismatch")
    for split in ("development", "confirmation"):
        s = c[split]
        if s["ordinary_families"] * 8 + s["boundary_families"] * 16 != s["records"]:
            raise ValueError("evaluation count mismatch")
    return c


def pinned_bytes(path, expected):
    """Accept only exact bytes or a single stripped terminal LF; never edit source."""
    b = Path(path).read_bytes()
    if digest(b) == expected:
        return b
    if digest(b + b"\n") == expected:
        return b + b"\n"
    raise ValueError("pinned source mismatch: " + str(path))


def inherited_sources():
    reg_bytes = pinned_bytes(PARENT / "registration.json", cfg()["parent_registration_sha256"])
    reg = parse(reg_bytes.decode())
    for name, expected in reg["sources"].items():
        pinned_bytes(EXPERIMENTS / name, expected)
    return reg["sources"]


def dependencies():
    inherited_sources()
    sys.path.insert(0, str(PARENT))
    import common
    import trace_ir
    import loss
    import evaluation
    sys.path.insert(0, str(common.SOURCE))
    spec = importlib.util.spec_from_file_location("curriculum004_generator", common.SOURCE / "actionnet021.py")
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    generator.PROTOCOL_ID = cfg()["protocol_id"]
    generator.BASE.PROTOCOL_ID = cfg()["protocol_id"]
    # Keep the successor runner ahead of inherited modules with the same basename.
    sys.path.insert(0, str(ROOT))
    return common, trace_ir, loss, evaluation, generator


def tree_hash(directory):
    directory = Path(directory)
    if not directory.is_dir() or not (directory / "adapter_model.safetensors").is_file():
        raise ValueError("complete adapter directory required")
    if any(p.is_symlink() for p in directory.rglob("*")):
        raise ValueError("adapter symlinks forbidden")
    return object_hash({p.relative_to(directory).as_posix(): file_hash(p)
                        for p in sorted(directory.rglob("*")) if p.is_file()})


def verify_parent(directory):
    actual = tree_hash(directory)
    if actual != cfg()["parent_adapter_sha256"]:
        raise ValueError("not the registered Program-003 trace adapter")
    return actual


def own_sources():
    paths = list(ROOT.glob("*.py")) + list(ROOT.glob("*.md")) + [ROOT / "config.json"]
    paths += list((ROOT / "tests").glob("*.py"))
    return {p.relative_to(ROOT).as_posix(): file_hash(p) for p in sorted(paths)}


def freeze():
    write_json(ROOT / "registration.json", {
        "protocol_id": cfg()["protocol_id"], "sources": own_sources(),
        "inherited_sources": inherited_sources(),
        "parent_adapter_sha256": cfg()["parent_adapter_sha256"],
        "data": {p.relative_to(ROOT).as_posix(): file_hash(p)
                 for p in sorted((ROOT / "prepared").glob("*")) if p.is_file()},
        "confirmation_materialized": False, "binding_authority": False})


def verify():
    reg = read(ROOT / "registration.json")
    if reg["sources"] != own_sources() or reg["inherited_sources"] != inherited_sources():
        raise ValueError("frozen implementation changed; create a new version")
    if reg["parent_adapter_sha256"] != cfg()["parent_adapter_sha256"]:
        raise ValueError("parent identity changed")
    for name, expected in reg["data"].items():
        if file_hash(ROOT / name) != expected:
            raise ValueError("frozen data changed: " + name)
    return reg


def runtime_config():
    original = read(PARENT / "config.json")
    return {**original, **{k: cfg()[k] for k in (
        "training_seed", "training_records", "epochs", "max_steps", "effective_batch_size",
        "learning_rate", "warmup_steps")}}