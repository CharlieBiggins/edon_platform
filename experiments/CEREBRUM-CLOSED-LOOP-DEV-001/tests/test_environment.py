from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EDON_ROOT = ROOT.parents[1]
sys.path.insert(0, str(EDON_ROOT / "src"))

from edon.evaluation.closed_loop_dev import ClosedLoopEnvironment


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def load_preflight():
    spec = importlib.util.spec_from_file_location("closed_loop_preflight", ROOT / "preflight.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ClosedLoopDevelopmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.train_episodes = read_jsonl(ROOT / "dataset" / "train-episodes.jsonl")
        cls.validation_episodes = read_jsonl(ROOT / "dataset" / "validation-episodes.jsonl")
        cls.validation_oracles = {
            row["episode_id"]: row for row in read_jsonl(ROOT / "oracle" / "validation-oracle.jsonl")
        }

    def test_preflight_passes(self) -> None:
        report = load_preflight().build_report()
        self.assertEqual(report["status"], "READY_FOR_TWO_SEED_LEARNED_CLOSED_LOOP_DEVELOPMENT", report)
        self.assertEqual(report["control_count"], report["controls_passed"])

    def test_expected_split_counts_and_separation(self) -> None:
        self.assertEqual(len(self.train_episodes), 288)
        self.assertEqual(len(self.validation_episodes), 72)
        train_profiles = {row["institution"]["profile"] for row in self.train_episodes}
        validation_profiles = {row["institution"]["profile"] for row in self.validation_episodes}
        train_renderers = {row["institution"]["renderer"] for row in self.train_episodes}
        validation_renderers = {row["institution"]["renderer"] for row in self.validation_episodes}
        self.assertFalse(train_profiles & validation_profiles)
        self.assertFalse(train_renderers & validation_renderers)

    def test_reference_replay_covers_success_and_replanning(self) -> None:
        pivotal = [row for row in self.validation_episodes if row["pair_class"] == "PIVOTAL"]
        base = next(row for row in pivotal if row["variant"] == "BASE")
        changed = next(row for row in pivotal if row["variant"] == "CHANGED")
        base_run = ClosedLoopEnvironment(base, self.validation_oracles[base["episode_id"]]).run_reference()
        changed_run = ClosedLoopEnvironment(changed, self.validation_oracles[changed["episode_id"]]).run_reference()
        self.assertTrue(base_run["episode_success"])
        self.assertTrue(changed_run["episode_success"])
        self.assertEqual(base_run["cycles"], 8)
        self.assertEqual(changed_run["cycles"], 10)
        self.assertIn("REPLAN", [row["target"]["proposal_type"] for row in changed_run["turns"]])

    def test_authority_bearing_proposal_is_rejected_without_commit(self) -> None:
        episode = self.validation_episodes[0]
        environment = ClosedLoopEnvironment(episode, self.validation_oracles[episode["episode_id"]])
        before = environment.commit_count
        result = environment.step(
            {
                "proposal_type": "CREATE_GOAL",
                "payload": {"goal_id": "bad", "description": "bad", "kernel_token": "forbidden"},
                "binding_authority": True,
            }
        )
        self.assertFalse(result["accepted_by_kernel"])
        self.assertEqual(environment.commit_count, before)
        self.assertEqual(environment.unsafe_proposals, 1)

    def test_wrong_dispatch_fails_closed(self) -> None:
        episode = self.validation_episodes[0]
        environment = ClosedLoopEnvironment(episode, self.validation_oracles[episode["episode_id"]])
        environment.step(environment.expected_proposal())
        environment.step(environment.expected_proposal())
        expected = environment.expected_proposal()
        expected["payload"]["agent_id"] = episode["agents"][-1]["agent_id"]
        before = environment.commit_count
        result = environment.step(expected)
        self.assertFalse(result["accepted_by_kernel"])
        self.assertEqual(environment.commit_count, before)

    def test_validation_inputs_do_not_contain_targets(self) -> None:
        inputs = read_jsonl(ROOT / "dataset" / "validation-inputs.jsonl")
        labels = read_jsonl(ROOT / "oracle" / "validation-labels.jsonl")
        self.assertTrue(all("target" not in row for row in inputs))
        self.assertEqual({row["record_id"] for row in inputs}, {row["record_id"] for row in labels})

    def test_future_failure_is_not_visible_before_monitoring(self) -> None:
        episode = next(
            row
            for row in self.validation_episodes
            if row["pair_class"] == "PIVOTAL" and row["variant"] == "CHANGED"
        )
        oracle = self.validation_oracles[episode["episode_id"]]
        environment = ClosedLoopEnvironment(episode, oracle)
        for _ in range(3):
            observation = environment.observe()
            self.assertNotIn(oracle["primary_failure_reason"], json.dumps(observation))
            self.assertNotIn("pair_class", observation)
            self.assertNotIn("variant", observation)
            environment.step(environment.expected_proposal())
        monitor_observation = environment.observe()
        self.assertNotIn(oracle["primary_failure_reason"], json.dumps(monitor_observation))
        environment.step(environment.expected_proposal())
        self.assertIn(oracle["primary_failure_reason"], json.dumps(environment.observe()))
        self.assertEqual(environment.expected_proposal()["proposal_type"], "REPLAN")


if __name__ == "__main__":
    unittest.main()