"""Slow CPU integration test. Temporary oracle fixtures, never model results.

Reconstructs the exact frozen 005 data only in a disposable workspace, exercises
the successor generator and native scorer, and deletes every generated fixture.
Does not publish a screen instrument or access confirmation.
"""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
import foundation as f


class InheritedReferenceTests(unittest.TestCase):
    def test_exact_reconstruction_generation_and_reference_scoring(self):
        workspace = Path(".")
        old = ROOT.parent / "CEREBRUM-END2END-PROGRAM-005"
        reg = f.parse(f.pinned(old / "registration.json", f.REG005))
        helper = old / "verification/restore_program005.py"
        payload = f.pinned(helper, "sha256:bf68844a2deb81eae57f627135a79e56e4a0bf206720c0a0db3960565d9cd32c")
        ns = {"__name__": "test_restore_definitions", "__file__": str(helper)}
        exec(compile(payload, str(helper), "exec"), ns)
        with tempfile.TemporaryDirectory(prefix="comparison001-test-", dir=".") as tmp:
            target_workspace = Path(tmp)
            target = target_workspace / "edon/experiments" / f.PROGRAM005

            def copy_pinned(source, destination, expected):
                data = f.pinned(source, expected)
                if f.digest(data) != expected:
                    data += b"\n"
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(data)

            copy_pinned(old / "registration.json", target / "registration.json", f.REG005)
            for field, source_base, target_base in (("sources", old, target),
                    ("inherited_sources", old.parent, target.parent), ("data", old, target)):
                for name, expected in reg[field].items():
                    if field == "data" and name.endswith(".jsonl"):
                        continue
                    copy_pinned(source_base / f.safe_name(name), target_base / name, expected)
            env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"}
            restored = subprocess.run([sys.executable, "-B", "-c", ns["RECONSTRUCT"]],
                                      cwd=target, env=env, capture_output=True, text=True)
            self.assertEqual(restored.returncode, 0, restored.stdout + restored.stderr)
            test_code = r'''
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import bridge
import foundation as f
loaded = bridge.load(Path(sys.argv[2]))
config = f.read(Path(sys.argv[1]) / "config.json")
values, coverage = bridge.generate(loaded, config)
assert len(values) == 48 and coverage["pairs"] == 24
assert set(coverage["decision_counts"]) == f.DECISIONS
predictions = [{"case_id": r["case_id"], "raw_output": r["trace_completion"] + "\n" + r["completion"],
                "hit_generation_limit": False, "ended_with_eos": True} for r in values]
score = bridge.score_condition(loaded, values, predictions)
assert score["program_exact_rate"] == 1.0, score
assert score["trace_exact_rate"] == 1.0
assert score["raw_claim_unsafe_authorizations"] == 0
assert score["case_failure_inventory"] == []
assert score["verification_interpretation"].startswith("ORACLE_ASSISTED")
predictions[0]["raw_output"] = "malformed"
broken = bridge.score_condition(loaded, values, predictions)
assert broken["unexamined_raw_claims"] >= 1
assert broken["program_exact_rate"] < 1.0
assert broken["case_failure_inventory"][0]["case_id"] == values[0]["case_id"]
print("TEMPORARY_ORACLE_FIXTURE_ONLY: 48 generated; reference scoring and malformed-output detection passed")
'''
            result = subprocess.run([sys.executable, "-B", "-c", test_code, str(ROOT), str(target_workspace)],
                                    env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("TEMPORARY_ORACLE_FIXTURE_ONLY", result.stdout)


if __name__ == "__main__":
    unittest.main()