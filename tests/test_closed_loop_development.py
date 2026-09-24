import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "CEREBRUM-CLOSED-LOOP-DEV-001"
sys.path.insert(0, str(ROOT / "src"))

from edon.evaluation.closed_loop_dev import ClosedLoopEnvironment


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


class ClosedLoopDevelopmentRepositoryTests(unittest.TestCase):
    def test_registered_environment_is_ready_and_fail_closed(self):
        spec = importlib.util.spec_from_file_location("closed_loop_preflight", EXPERIMENT / "preflight.py")
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        report = module.build_report()
        self.assertEqual(report["status"], "READY_FOR_TWO_SEED_LEARNED_CLOSED_LOOP_DEVELOPMENT", report)

        episode = read_jsonl(EXPERIMENT / "dataset" / "validation-episodes.jsonl")[0]
        oracle = read_jsonl(EXPERIMENT / "oracle" / "validation-oracle.jsonl")[0]
        environment = ClosedLoopEnvironment(episode, oracle)
        result = environment.step(
            {
                "proposal_type": "CREATE_GOAL",
                "payload": {"goal_id": "invalid", "description": "invalid"},
                "rationale": "This is deliberately the wrong grounded proposal.",
                "confidence": 1.0,
                "binding_authority": False,
            }
        )
        self.assertFalse(result["accepted_by_kernel"])
        self.assertEqual(environment.commit_count, 0)


if __name__ == "__main__":
    unittest.main()