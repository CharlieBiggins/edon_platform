"""Explicit CPU preparation and paid development only; no confirmation command."""
import argparse
import contextlib
import json
import os
from pathlib import Path
import subprocess
import sys
from core import ROOT, cfg, read, rows, verify, write_json, file_hash, object_hash


@contextlib.contextmanager
def lock():
    # Remote paid runtime is Linux. CPU preparation/preflight also support Windows.
    path = ROOT / ".run.lock"
    with path.open("a+b") as stream:
        if os.name == "nt":
            import msvcrt
            stream.seek(0); stream.write(b"0"); stream.flush(); stream.seek(0)
            try:
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise RuntimeError("another Program-005 runner is active") from exc
        else:
            import fcntl
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise RuntimeError("another Program-005 runner is active") from exc
        yield


def worker(stage, arm, parent):
    call = f"w.train({arm!r},p)" if stage == "train" else f"w.predict({arm!r},'development',p)"
    code = f"from pathlib import Path; import gpu_worker as w; p=Path({str(parent)!r}); " + call
    subprocess.run([sys.executable, "-B", "-u", "-c", code], cwd=ROOT, check=True)


def score(parent):
    from gpu_worker import validate_predictions
    from evaluate import summarize, compare
    verify()
    inputs = rows(ROOT / "prepared/development.jsonl")
    scores = {}
    for arm in (*cfg()["arms"], "parent"):
        result = summarize(inputs, validate_predictions(arm, "development", parent))
        result.update(arm=arm, split="development",
                      prediction_sha256=file_hash(ROOT / "results" / f"development-{arm}-predictions.jsonl"))
        write_json(ROOT / "results" / f"development-{arm}-score.json", result)
        scores[arm] = result
    comparison = compare(scores["ordinary"], scores["repair"], scores["parent"])
    result = {"protocol_id": cfg()["protocol_id"], "registration_sha256": file_hash(ROOT / "registration.json"),
              "status": "SCREEN_SUPPORTS_LARGER_EVALUATION" if comparison["screen_passed"] else "DEVELOPMENT_HOLD",
              "selected_arm": None, "comparison": comparison,
              "score_hashes": {a: object_hash(s) for a, s in scores.items()},
              "confirmation_accessed": False, "confirmation_authorized": False,
              "transfer_authorized": False, "binding_authority": False}
    write_json(ROOT / "results/selection.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("prepare", "preflight", "runtime", "development", "score", "bundle"))
    parser.add_argument("--parent", default="../CEREBRUM-END2END-PROGRAM-003/artifacts/trace/adapter",
                        help="Relative to the experiment directory")
    parser.add_argument("--audit-dir", default="prism-uploads", help="Relative to the caller working directory")
    parser.add_argument("--authorize-paid", action="store_true", help="Explicitly permit GPU work; not confirmation")
    args = parser.parse_args()
    if Path(args.parent).is_absolute() or Path(args.audit_dir).is_absolute():
        parser.error("use relative paths")
    if args.stage in ("runtime", "development") and not args.authorize_paid:
        parser.error("GPU stages require --authorize-paid; no GPU work started")
    audit_dir = Path(os.path.relpath(args.audit_dir, ROOT))
    os.chdir(ROOT)
    parent = Path(args.parent)
    with lock():
        if args.stage == "prepare":
            from data import prepare
            result = prepare(audit_dir)
        elif args.stage == "preflight":
            verify()
            result = {"status": "CPU_PREFLIGHT_PASSED", "gpu_tested": False, "parent_adapter_checked": False}
        elif args.stage == "bundle":
            from bundle import bundle
            result = bundle()
        elif args.stage == "score":
            result = score(parent)
        else:
            from gpu_worker import runtime_preflight
            result = runtime_preflight(parent)
            if args.stage == "development":
                for arm in cfg()["arms"]:
                    worker("train", arm, parent)
                for arm in (*cfg()["arms"], "parent"):
                    worker("predict", arm, parent)
                result = score(parent)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()