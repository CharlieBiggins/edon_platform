"""Synthetic tests only; these do not verify the user's remote run."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("backup", Path(__file__).with_name("verify_program005_backup.py"))
backup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backup)


class BackupTests(unittest.TestCase):
    def test_strict_json(self):
        for text in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}'):
            with self.assertRaises(ValueError):
                backup.parse(text)

    def test_prefix(self):
        with tempfile.TemporaryDirectory(dir=".") as tmp:
            p = Path(tmp) / "predictions.jsonl"
            p.write_bytes(b'{"case_id":"a"}\n{"case_')
            before = p.read_bytes()
            self.assertEqual(backup.prefix(p, ["a", "b"]), ([{"case_id": "a"}], True))
            self.assertEqual(p.read_bytes(), before)
            for text in (b'bad\n{"case_id":"a"}\n', b'{"case_id":"b"}\n',
                         b'{"case_id":"a"}\n{"case_id":"a"}\n'):
                p.write_bytes(text)
                with self.assertRaises(ValueError):
                    backup.prefix(p, ["a", "b"])

    def test_unsafe_paths(self):
        for name in ("../x", "C:x", "a\\b", "a//b", ""):
            with self.assertRaises(ValueError):
                backup.verify_files(Path("."), {name: "unused"})

    def test_complete_fixture_and_corruption(self):
        with tempfile.TemporaryDirectory(dir=".") as tmp:
            workspace = Path(tmp) / "workspace"
            root = workspace / "edon/experiments" / backup.EXPERIMENT
            old = root.parent / "CEREBRUM-END2END-PROGRAM-003"
            parent = Path(tmp) / "parent"

            def put(path, obj):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(obj), encoding="utf-8")

            put(parent / "adapter_model.safetensors", "FAKE TEST WEIGHTS")
            ph = backup.tree_hash(parent)
            put(old / "config.json", {"required_packages": {"fake": "test"}})
            put(old / "registration.json", {"sources": {}})
            put(root / "config.json", {"max_steps": 24, "parent_adapter_sha256": ph,
                "parent_registration_sha256": backup.file_hash(old / "registration.json")})
            for name in ("train-ordinary", "train-repair", "development"):
                p = root / "prepared" / (name + ".jsonl")
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text("".join(json.dumps({"case_id": str(i)}) + "\n" for i in range(96)), encoding="utf-8")
            reg = {"protocol_id": backup.EXPERIMENT, "confirmation_materialized": False,
                   "parent_adapter_sha256": ph,
                   "sources": {"config.json": backup.file_hash(root / "config.json")},
                   "data": {p.relative_to(root).as_posix(): backup.file_hash(p) for p in (root / "prepared").iterdir()},
                   "inherited_sources": {p.relative_to(root.parent).as_posix(): backup.file_hash(p) for p in old.iterdir()}}
            put(root / "registration.json", reg)
            rh = backup.file_hash(root / "registration.json")
            runtime = {"registration_sha256": rh, "parent_adapter_sha256": ph,
                "packages": {"fake": "test"}, "torch": "2.8.0+cu129", "cuda": "12.9", "gpu": "NVIDIA L4",
                "loss_value_and_gradient_passed": True,
                "datasets": {name: {"records": count, "truncations": 0, "target_budget_violations": 0}
                             for name, count in (("train-ordinary", 384), ("train-repair", 384), ("development", 96))}}
            put(root / "results/runtime-readiness.json", runtime)
            runtime_hash = backup.file_hash(root / "results/runtime-readiness.json")
            adapters = {"parent": ph}
            for arm in ("ordinary", "repair"):
                out = root / "artifacts" / arm
                put(out / "adapter/adapter_model.safetensors", "FAKE " + arm)
                adapters[arm] = backup.tree_hash(out / "adapter")
                binding = {"arm": arm, "registration_sha256": rh, "parent_adapter_sha256": ph,
                           "runtime_sha256": runtime_hash, "train_sha256": backup.file_hash(root / "prepared" / ("train-" + arm + ".jsonl"))}
                put(out / "start.json", binding)
                put(out / "training.json", {"binding": binding, "step": 24, "adapter_sha256": adapters[arm]})
            for arm in ("ordinary", "repair", "parent"):
                p = root / "results" / ("development-" + arm + "-predictions.jsonl")
                n = 4 if arm == "parent" else 96
                p.write_text("".join(json.dumps({"case_id": str(i)}) + "\n" for i in range(n)), encoding="utf-8")
                binding = {"arm": arm, "split": "development", "adapter_sha256": adapters[arm],
                           "registration_sha256": rh, "input_sha256": backup.file_hash(root / "prepared/development.jsonl"),
                           "runtime_sha256": runtime_hash}
                put(p.with_suffix(".binding.json"), binding)
                if n == 96:
                    put(p.with_suffix(".manifest.json"), {**binding, "count": n, "predictions_sha256": backup.file_hash(p)})
            with patch.object(backup, "REGISTRATION", rh), patch.object(backup, "PARENT_HASH", ph), contextlib.redirect_stdout(io.StringIO()):
                before = {p: p.read_bytes() for p in Path(tmp).rglob("*") if p.is_file()}
                self.assertEqual(backup.verify(workspace, parent, True)["parent"]["count"], 4)
                self.assertEqual(before, {p: p.read_bytes() for p in Path(tmp).rglob("*") if p.is_file()})
                put(root / "artifacts/repair/adapter/adapter_model.safetensors", "CORRUPTED")
                with self.assertRaisesRegex(ValueError, "Trained adapter mismatch"):
                    backup.verify(workspace, parent, True)


if __name__ == "__main__":
    unittest.main()