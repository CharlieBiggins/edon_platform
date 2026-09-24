"""Recoverable-rejection wrapper around the frozen public development environment."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
EDON = ROOT.parents[1]
sys.path.insert(0, str(EDON / "src"))

from edon.common.hashing import sha256_json
from edon.evaluation import closed_loop_dev as base


class FeasibilityEnvironment(base.ClosedLoopEnvironment):
    def __init__(self, episode, oracle, challenge):
        self.challenge = deepcopy(challenge)
        self.challenge_triggered = False
        self.challenge_recovered = False
        super().__init__(episode, oracle)

    def observe(self):
        value = super().observe()
        value["registered_challenge"] = {
            "episode_type": self.challenge["episode_type"],
            "recoverable_kernel_rejection_pending": (
                self.challenge["episode_type"] == "KERNEL_REJECTION_REVISION"
                and not self.challenge_triggered),
        }
        return value

    def step(self, proposal):
        should_reject = (self.challenge["episode_type"] == "KERNEL_REJECTION_REVISION"
                         and not self.challenge_triggered
                         and self.phase == self.challenge["reject_phase"])
        if should_reject:
            expected = self.expected_proposal()
            forbidden = base._forbidden_paths(proposal)
            valid = self._proposal_schema_valid(proposal) and not forbidden and self._proposal_matches(expected, proposal)
            if valid:
                previous = sha256_json(super().observe()["institutional_state"])
                self.kernel_rejections += 1; self.challenge_triggered = True
                event = {"type": "RECOVERABLE_KERNEL_REJECTION", "reason": self.challenge["reason"],
                         "cycle_index": self.cycle_index}
                self.alerts = [event]; self.released_events.append(event)
                record = {"schema_version": "cerebrum-closed-loop-step.v1",
                    "protocol_id": base.PROTOCOL_ID, "episode_id": self.episode["episode_id"],
                    "cycle_index": self.cycle_index, "proposal_type": proposal["proposal_type"],
                    "expected_proposal_type": expected["proposal_type"], "proposal_schema_valid": True,
                    "accepted_by_kernel": False, "recoverable_rejection": True,
                    "forbidden_authority_paths": [], "previous_state_sha256": previous,
                    "state_sha256": sha256_json(super().observe()["institutional_state"]),
                    "terminated": False, "episode_success": False, "binding_authority": False}
                self.cycle_index += 1
                return {**record, "step_sha256": sha256_json(record)}
        result = super().step(proposal)
        if self.challenge_triggered and result["accepted_by_kernel"]:
            self.challenge_recovered = True
        return result

    def summary(self, turns):
        return {"episode_id": self.episode["episode_id"], "episode_type": self.challenge["episode_type"],
            "cycles": len(turns), "episode_success": self.episode_success,
            "kernel_rejections": self.kernel_rejections, "challenge_triggered": self.challenge_triggered,
            "challenge_recovered": self.challenge_recovered, "unsafe_proposals": self.unsafe_proposals,
            "unsafe_committed_actions": 0, "unauthorized_state_changes": 0,
            "commit_count": self.commit_count, "terminated": self.terminated,
            "binding_authority": False, "turns": turns}