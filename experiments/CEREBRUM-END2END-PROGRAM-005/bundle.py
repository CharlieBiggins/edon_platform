"""Reproducible source/data transport. No weights, credentials, or GPU results."""
import io
import zipfile
from core import ROOT, EXPERIMENTS, verify, pinned_bytes, file_hash, write_once, write_json, digest


def bundle():
    reg = verify()
    files = {}
    for name, expected in reg["inherited_sources"].items():
        files["edon/experiments/" + name] = pinned_bytes(EXPERIMENTS / name, expected)
    for name, expected in {**reg["sources"], **reg["data"], "registration.json": file_hash(ROOT / "registration.json")}.items():
        files["edon/experiments/" + ROOT.name + "/" + name] = pinned_bytes(ROOT / name, expected)
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in sorted(files.items()):
            member = zipfile.ZipInfo(name, date_time=(2026, 9, 13, 0, 0, 0))
            member.compress_type = zipfile.ZIP_DEFLATED
            member.external_attr = 0o100644 << 16
            archive.writestr(member, payload)
    payload = stream.getvalue()
    write_once(ROOT / "exports/program005-handoff.zip", payload)
    report = {"archive_sha256": digest(payload), "bytes": len(payload), "files": len(files),
              "registration_sha256": file_hash(ROOT / "registration.json"),
              "parent_weights_included": False, "gpu_results_included": False,
              "gpu_run_started_by_bundle": False,
              "confirmation_materialized": False}
    write_json(ROOT / "exports/program005-handoff.json", report)
    return report