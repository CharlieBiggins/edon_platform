import ast
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "CEREBRUM-PLATFORM-CONTRIB-001"


class CerebrumPlatformContributionTests(unittest.TestCase):
    def test_package_readiness_and_proxy_signal(self):
        completed = subprocess.run(
            [sys.executable, "verify_package.py"], cwd=EXPERIMENT,
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "PROXY_SIGNAL_ESTABLISHED_CONFIRMATORY_QWEN_BLOCKED")
        self.assertEqual(result["checks_passed"], 22)
        self.assertEqual(result["check_count"], 22)

    def test_proxy_is_not_recorded_as_cerebrum_result(self):
        proxy = json.loads((EXPERIMENT / "results" / "proxy_result.json").read_text())
        self.assertEqual(proxy["status"], "PROXY_SIGNAL_ESTABLISHED")
        self.assertFalse(proxy["actual_cerebrum_executed"])
        self.assertGreaterEqual(proxy["platform002_minus_control"]["decision_accuracy"], 0.05)
        self.assertGreaterEqual(proxy["platform002_minus_control"]["joint_accuracy"], 0.10)
        self.assertFalse((EXPERIMENT / "results" / "qwen_result.json").exists())

    def test_protected_generator_has_no_edon_or_actionnet_import(self):
        tree = ast.parse(
            (EXPERIMENT / "independent_protected_institution.py").read_text(encoding="utf-8")
        )
        roots = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                roots.add(node.module.split(".", 1)[0])
        self.assertFalse({"edon", "actionnet"} & roots)

    def test_qwen_preflight_is_honestly_blocked(self):
        result = json.loads((EXPERIMENT / "results" / "preflight.json").read_text())
        self.assertEqual(result["status"], "BLOCKED_MISSING_QWEN_GPU_AND_FRESH_TARGET_CUSTODY")
        self.assertFalse(result["actual_cerebrum_result_exists"])
        self.assertFalse(result["current_target_confirmatory_eligible"])


if __name__ == "__main__":
    unittest.main()