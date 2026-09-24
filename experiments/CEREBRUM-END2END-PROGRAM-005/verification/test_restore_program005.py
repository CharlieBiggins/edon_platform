"""Transport tests outside frozen sources; stdlib only, no GPU or model weights."""
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
spec = importlib.util.spec_from_file_location("restore005", HERE / "restore_program005.py")
restore = importlib.util.module_from_spec(spec)
spec.loader.exec_module(restore)


class RestoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reg = json.loads((ROOT / "registration.json").read_bytes())
        cls.files = {restore.EXPERIMENT + "registration.json": (ROOT / "registration.json").read_bytes()}
        for name in cls.reg["sources"]:
            cls.files[restore.EXPERIMENT + name] = (ROOT / name).read_bytes()
        for name in cls.reg["inherited_sources"]:
            cls.files[restore.PREFIX + name] = (ROOT.parent / name).read_bytes()
        for name in cls.reg["data"]:
            if name not in restore.REGENERABLE:
                cls.files[restore.EXPERIMENT + name] = (ROOT / name).read_bytes()

    def archive(self, path, files=None, duplicate=None, symlink=None):
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for name, payload in (self.files if files is None else files).items():
                # Simulate Prism wrapper prefix and removal of a final LF.
                member = zipfile.ZipInfo("export/" + name)
                member.external_attr = (0o120777 if name == symlink else 0o100644) << 16
                z.writestr(member, payload[:-1] if payload.endswith(b"\n") else payload)
                if name == duplicate:
                    z.writestr("other/" + name, payload)

    def test_collect_verifies_and_restores_only_bound_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(os.path.relpath(tmp)) / "export.zip"
            files = {**self.files, "unrelated/evil.py": b"raise RuntimeError('never execute')"}
            self.archive(path, files)
            collected = restore.collect(path)
            self.assertNotIn("unrelated/evil.py", collected)
            self.assertEqual(restore.digest(collected[restore.EXPERIMENT+"registration.json"]), restore.REGISTRATION)
            for name, expected in self.reg["sources"].items():
                self.assertEqual(restore.digest(collected[restore.EXPERIMENT+name]), expected)
            self.assertFalse(any(restore.EXPERIMENT+n in collected for n in restore.REGENERABLE))

    def test_bad_source_rejected(self):
        files = dict(self.files); files[restore.EXPERIMENT+"core.py"] = b"tampered"
        self.check_rejected(files)

    def test_missing_metadata_rejected(self):
        files = dict(self.files); del files[restore.EXPERIMENT+"prepared/exclusions.json"]
        self.check_rejected(files)

    def test_saved_run_rejected(self):
        files = {**self.files, restore.EXPERIMENT+"results/runtime-readiness.json": b"{}"}
        self.check_rejected(files)

    def test_present_but_corrupt_data_not_regenerated(self):
        files = {**self.files, restore.EXPERIMENT+"prepared/development.jsonl": b"wrong"}
        self.check_rejected(files)

    def check_rejected(self, files):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(os.path.relpath(tmp)) / "export.zip"
            self.archive(path, files)
            with self.assertRaises(ValueError): restore.collect(path)

    def test_duplicate_member_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(os.path.relpath(tmp)) / "export.zip"
            self.archive(path, duplicate=restore.EXPERIMENT+"core.py")
            with self.assertRaises(ValueError): restore.collect(path)

    def test_symlink_member_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(os.path.relpath(tmp)) / "export.zip"
            self.archive(path, symlink=restore.EXPERIMENT+"core.py")
            with self.assertRaises(ValueError): restore.collect(path)

    def test_unsafe_names(self):
        for name in ("/absolute", "a/../b", "a\\b", "a//b", "a/./b", ""):
            with self.subTest(name=name), self.assertRaises(ValueError): restore.safe_name(name)

    def test_parent_tree_hash_convention(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(os.path.relpath(tmp))
            with (directory/"adapter_model.safetensors").open("xb") as stream:
                stream.write(b"test bytes, not real model weights")
            expected = restore.digest(json.dumps({"adapter_model.safetensors": restore.digest(
                b"test bytes, not real model weights")}, sort_keys=True, separators=(",", ":")).encode())
            self.assertEqual(restore.parent_hash(directory), expected)

    def test_full_restore_missing_data_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(os.path.relpath(tmp))
            archive, destination = directory/"export.zip", directory/"new-workspace"
            self.archive(archive)
            helper = os.path.relpath(HERE/"restore_program005.py")
            result = subprocess.run([sys.executable, "-B", helper, str(archive), str(destination)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            print(result.stdout, flush=True)
            root = destination/restore.EXPERIMENT
            for name, expected in self.reg["data"].items():
                self.assertEqual(restore.digest((root/name).read_bytes()), expected)
            self.assertFalse((root/"results").exists())
            self.assertFalse((root/"artifacts").exists())
            self.assertFalse((root/"prepared/confirmation.jsonl").exists())
            result = subprocess.run([sys.executable, "-B", helper, str(archive), str(destination)],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Destination already exists", result.stderr)
            subprocess.run([sys.executable, "-B", "-m", "unittest", "discover", "-s", str(root/"tests")], check=True)


if __name__ == "__main__":
    unittest.main()