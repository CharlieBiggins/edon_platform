"""Export bound sources and NEW development data, never predecessor datasets."""
from pathlib import Path
import zipfile

from common import ROOT, EXPERIMENTS, verify_freeze, write_json, file_hash


def bundle():
    manifest = verify_freeze()
    if (ROOT / "results/confirmation-access.json").exists():
        raise ValueError("initial handoff export is closed after confirmation access")
    project = EXPERIMENTS.parent.parent
    paths = [EXPERIMENTS / name for name in manifest["sources"]]
    paths += list((ROOT / "tests").glob("*.py"))
    paths += [ROOT / "registration.json", ROOT / "prepared/train.jsonl",
              ROOT / "prepared/development.jsonl", ROOT / "prepared/qualification.json"]
    out = ROOT / "exports/program003-handoff.zip"
    out.parent.mkdir(exist_ok=True)
    # A deterministic ZIP can be regenerated without changing any experimental evidence.
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(set(paths)):
            info = zipfile.ZipInfo(str(path.relative_to(project)), date_time=(2026, 9, 8, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())
    write_json(out.with_suffix(".json"), {"sha256": file_hash(out), "files": len(set(paths)),
               "registration_sha256": file_hash(ROOT / "registration.json"),
               "predecessor_datasets_included": False, "confirmation_included": False})
    print(out.relative_to(project))


if __name__ == "__main__":
    bundle()