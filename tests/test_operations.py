import json
import sys
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from edon.memory import EpisodicMemoryStore
from edon.operations import InstitutionalControlPlane, OperationsError
from edon.world import WorldStateStore


class InstitutionalOperationsTests(unittest.TestCase):
    def control(self, directory: str) -> InstitutionalControlPlane:
        root = Path(directory)
        return InstitutionalControlPlane(
            WorldStateStore(root / "world.sqlite3"),
            EpisodicMemoryStore(root / "memory.sqlite3"),
        )

    def test_observe_plan_allocate_coordinate_outcome_and_replan(self):
        with tempfile.TemporaryDirectory() as directory:
            control = self.control(directory)
            world = control.bootstrap_world(
                "tenant-a",
                "institution",
                {"name": "Example institution", "institution_ir": "ir:v1"},
                actor_id="kernel",
                authorization_ref="auth-bootstrap",
                source_lineage=["institution-ir:v1"],
                timestamp="2026-08-20T10:00:00+00:00",
            )
            self.assertEqual(world["version"], 0)

            observed = control.ingest_observation(
                "tenant-a",
                "institution",
                "observation-001",
                "TELEMETRY",
                "sensor-grid-a",
                "Telemetry reported an elevated temperature in inspection zone A.",
                {"zone": "A", "temperature_c": 41.5},
                observed_at="2026-08-20T10:01:00+00:00",
                confidence=0.98,
                sensitivity="INTERNAL",
                event_id="event-observation-001",
                actor_id="kernel",
                expected_version=0,
                authorization_ref="auth-observation",
                timestamp="2026-08-20T10:01:01+00:00",
            )
            self.assertEqual(observed["world"]["version"], 1)
            self.assertEqual(observed["observation"]["modality"], "TELEMETRY")

            control.register_agent(
                "tenant-a", "institution", "agent-inspector", "ROBOT",
                ["inspect", "report"],
                event_id="event-agent-001", actor_id="kernel", expected_version=1,
                authorization_ref="auth-agent", max_concurrent=1,
                relationships={"supervised_by": "operations-center"},
                timestamp="2026-08-20T10:02:00+00:00",
            )
            control.register_resource_pool(
                "tenant-a", "institution", "battery", 10, "kwh",
                event_id="event-resource-001", actor_id="kernel", expected_version=2,
                authorization_ref="auth-resource",
                timestamp="2026-08-20T10:03:00+00:00",
            )
            control.create_goal(
                "tenant-a", "institution", "goal-inspection",
                "Inspect the elevated-temperature zone and produce a verified report.",
                event_id="event-goal-001", actor_id="kernel", expected_version=3,
                authorization_ref="auth-goal", priority=90,
                deadline="2026-08-21T10:00:00+00:00",
                owner_id="agent-inspector",
                success_criteria=["zone inspected", "report delivered"],
                timestamp="2026-08-20T10:04:00+00:00",
            )
            control.create_plan(
                "tenant-a", "institution", "plan-inspection-v1", "goal-inspection",
                [
                    {
                        "step_id": "inspect-zone",
                        "action": "Inspect zone A and collect instrument readings.",
                        "required_capabilities": ["inspect"],
                        "resource_requests": {"battery": 3},
                        "expected_outcomes": ["inspection complete"],
                        "deadline": "2026-08-20T18:00:00+00:00",
                        "command": {"adapter": "robot-a", "action": "inspect", "zone": "A"},
                    },
                    {
                        "step_id": "deliver-report",
                        "action": "Deliver the verified inspection report.",
                        "dependencies": ["inspect-zone"],
                        "required_capabilities": ["report"],
                        "resource_requests": {"battery": 1},
                        "expected_outcomes": ["report delivered"],
                        "deadline": "2026-08-20T20:00:00+00:00",
                    },
                ],
                horizon_start="2026-08-20T10:04:00+00:00",
                horizon_end="2026-08-21T10:00:00+00:00",
                event_id="event-plan-001", actor_id="kernel", expected_version=4,
                authorization_ref="auth-plan",
                timestamp="2026-08-20T10:05:00+00:00",
            )
            ready = control.ready_steps(
                "tenant-a", "institution", at="2026-08-20T10:06:00+00:00"
            )
            self.assertEqual([row["step"]["step_id"] for row in ready], ["inspect-zone"])
            self.assertFalse(ready[0]["step"]["command"]["binding_authority"])

            control.allocate_step_resources(
                "tenant-a", "institution", "plan-inspection-v1", "inspect-zone",
                event_id="event-allocation-001", actor_id="kernel", expected_version=5,
                authorization_ref="auth-allocation",
                timestamp="2026-08-20T10:06:00+00:00",
            )
            control.assign_step(
                "tenant-a", "institution", "plan-inspection-v1", "inspect-zone",
                "agent-inspector", event_id="event-assignment-001", actor_id="kernel",
                expected_version=6, authorization_ref="auth-assignment",
                timestamp="2026-08-20T10:07:00+00:00",
            )
            control.start_step(
                "tenant-a", "institution", "plan-inspection-v1", "inspect-zone",
                event_id="event-start-001", actor_id="kernel", expected_version=7,
                authorization_ref="auth-start",
                timestamp="2026-08-20T10:08:00+00:00",
            )
            first = control.record_step_outcome(
                "tenant-a", "institution", "plan-inspection-v1", "inspect-zone", True,
                "The inspection completed and instrument readings were preserved.",
                {"temperature_c": 41.7, "evidence_ref": "reading-set-001"},
                event_id="event-outcome-001", outcome_id="outcome-001", actor_id="kernel",
                expected_version=8, authorization_ref="auth-outcome",
                actual_outcomes=["inspection complete"],
                timestamp="2026-08-20T11:00:00+00:00",
            )
            self.assertIsNone(first["alert"])
            self.assertFalse(first["learning_candidate"]["training_eligible"])
            state = control.operational_state("tenant-a", "institution")["operations"]
            self.assertEqual(state["resource_pools"]["battery"]["allocated"], 0)
            self.assertEqual(
                [row["step"]["step_id"] for row in control.ready_steps(
                    "tenant-a", "institution", at="2026-08-20T11:01:00+00:00"
                )],
                ["deliver-report"],
            )

            control.allocate_step_resources(
                "tenant-a", "institution", "plan-inspection-v1", "deliver-report",
                event_id="event-allocation-002", actor_id="kernel", expected_version=9,
                authorization_ref="auth-allocation-2",
                timestamp="2026-08-20T11:02:00+00:00",
            )
            control.assign_step(
                "tenant-a", "institution", "plan-inspection-v1", "deliver-report",
                "agent-inspector", event_id="event-assignment-002", actor_id="kernel",
                expected_version=10, authorization_ref="auth-assignment-2",
                timestamp="2026-08-20T11:03:00+00:00",
            )
            control.start_step(
                "tenant-a", "institution", "plan-inspection-v1", "deliver-report",
                event_id="event-start-002", actor_id="kernel", expected_version=11,
                authorization_ref="auth-start-2",
                timestamp="2026-08-20T11:04:00+00:00",
            )
            failed = control.record_step_outcome(
                "tenant-a", "institution", "plan-inspection-v1", "deliver-report", False,
                "The report delivery failed because the destination service was unavailable.",
                {"error": "destination_unavailable"},
                event_id="event-outcome-002", outcome_id="outcome-002", actor_id="kernel",
                expected_version=12, authorization_ref="auth-outcome-2",
                actual_outcomes=["delivery failed"],
                timestamp="2026-08-20T11:30:00+00:00",
            )
            self.assertEqual(failed["alert"]["type"], "REPLAN_REQUIRED")
            state = control.operational_state("tenant-a", "institution")["operations"]
            self.assertEqual(state["plans"]["plan-inspection-v1"]["status"], "NEEDS_REPLAN")
            self.assertEqual(state["goals"]["goal-inspection"]["status"], "BLOCKED")
            alerts = control.monitor(
                "tenant-a", "institution", at="2026-08-22T10:00:00+00:00"
            )
            self.assertIn("REPLAN_REQUIRED", {row["type"] for row in alerts})
            self.assertIn("GOAL_OVERDUE", {row["type"] for row in alerts})

            revised = control.replan(
                "tenant-a", "institution", "plan-inspection-v1", "plan-inspection-v2",
                [{
                    "step_id": "deliver-report-alternate",
                    "action": "Deliver the verified report through the alternate channel.",
                    "required_capabilities": ["report"],
                    "resource_requests": {"battery": 1},
                    "expected_outcomes": ["report delivered"],
                    "deadline": "2026-08-20T21:00:00+00:00",
                }],
                horizon_start="2026-08-20T11:31:00+00:00",
                horizon_end="2026-08-21T10:00:00+00:00",
                event_id="event-replan-001", actor_id="kernel", expected_version=13,
                authorization_ref="auth-replan", reason="Primary report channel failed.",
                timestamp="2026-08-20T11:31:00+00:00",
            )
            self.assertEqual(revised["version"], 14)
            state = revised["state"]["operations"]
            self.assertEqual(state["plans"]["plan-inspection-v1"]["status"], "SUPERSEDED")
            self.assertEqual(state["plans"]["plan-inspection-v2"]["revision"], 2)
            self.assertEqual(state["goals"]["goal-inspection"]["status"], "ACTIVE")
            self.assertTrue(control.worlds.verify_world("tenant-a", "institution")["passed"])
            self.assertTrue(control.memory.verify_audit_chain("tenant-a"))

    def test_plan_resource_and_capability_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            control = self.control(directory)
            control.bootstrap_world(
                "tenant-a", "institution", {"name": "Example institution"},
                actor_id="kernel", authorization_ref="bootstrap",
                timestamp="2026-08-20T10:00:00+00:00",
            )
            control.register_agent(
                "tenant-a", "institution", "agent-a", "SOFTWARE", ["read"],
                event_id="agent", actor_id="kernel", expected_version=0,
                authorization_ref="agent-auth", timestamp="2026-08-20T10:01:00+00:00",
            )
            control.register_resource_pool(
                "tenant-a", "institution", "compute", 1, "gpu",
                event_id="resource", actor_id="kernel", expected_version=1,
                authorization_ref="resource-auth", timestamp="2026-08-20T10:02:00+00:00",
            )
            control.create_goal(
                "tenant-a", "institution", "goal-a",
                "Produce a reviewed institutional analysis for the current case.",
                event_id="goal", actor_id="kernel", expected_version=2,
                authorization_ref="goal-auth", timestamp="2026-08-20T10:03:00+00:00",
            )
            with self.assertRaisesRegex(OperationsError, "cycle"):
                control.create_plan(
                    "tenant-a", "institution", "cyclic", "goal-a",
                    [
                        {"step_id": "a", "action": "First action", "dependencies": ["b"]},
                        {"step_id": "b", "action": "Second action", "dependencies": ["a"]},
                    ],
                    horizon_start="2026-08-20T10:00:00+00:00", horizon_end=None,
                    event_id="cyclic", actor_id="kernel", expected_version=3,
                    authorization_ref="plan-auth",
                )
            control.create_plan(
                "tenant-a", "institution", "plan-a", "goal-a",
                [{
                    "step_id": "analyze",
                    "action": "Analyze the current institutional evidence.",
                    "required_capabilities": ["analyze"],
                    "resource_requests": {"compute": 2},
                }],
                horizon_start="2026-08-20T10:00:00+00:00", horizon_end=None,
                event_id="plan", actor_id="kernel", expected_version=3,
                authorization_ref="plan-auth", timestamp="2026-08-20T10:04:00+00:00",
            )
            with self.assertRaisesRegex(OperationsError, "insufficient resource"):
                control.allocate_step_resources(
                    "tenant-a", "institution", "plan-a", "analyze",
                    event_id="allocation", actor_id="kernel", expected_version=4,
                    authorization_ref="allocation-auth",
                )
            with self.assertRaisesRegex(OperationsError, "fully allocated"):
                control.assign_step(
                    "tenant-a", "institution", "plan-a", "analyze", "agent-a",
                    event_id="assign", actor_id="kernel", expected_version=4,
                    authorization_ref="assign-auth",
                )

    def test_operations_api_executes_authenticated_control_loop(self):
        with tempfile.TemporaryDirectory() as directory:
            server = EDONHTTPServer(
                ("127.0.0.1", 0),
                PlatformService(directory),
                {"operations-token-000000": "OPERATIONS_OPERATOR"},
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_address[1]}"

            def post(path: str, body: dict) -> dict:
                request = urllib.request.Request(
                    base + path,
                    data=json.dumps(body).encode("utf-8"),
                    method="POST",
                    headers={
                        "Authorization": "Bearer operations-token-000000",
                        "Content-Type": "application/json",
                    },
                )
                with urllib.request.urlopen(request) as response:
                    self.assertEqual(response.status, 200)
                    return json.loads(response.read().decode("utf-8"))

            try:
                created = post("/api/operations/bootstrap", {
                    "tenant_id": "tenant-a",
                    "world_id": "institution",
                    "institution": {"name": "Example institution"},
                    "authorization_ref": "auth-bootstrap",
                })
                self.assertEqual(created["version"], 0)
                post("/api/agents", {
                    "tenant_id": "tenant-a", "world_id": "institution",
                    "agent_id": "agent-a", "kind": "SOFTWARE",
                    "capabilities": ["analyze"], "event_id": "agent",
                    "expected_version": 0, "authorization_ref": "auth-agent",
                })
                post("/api/goals", {
                    "tenant_id": "tenant-a", "world_id": "institution",
                    "goal_id": "goal-a",
                    "description": "Analyze the current institutional evidence and produce a report.",
                    "event_id": "goal", "expected_version": 1,
                    "authorization_ref": "auth-goal",
                })
                post("/api/plans", {
                    "tenant_id": "tenant-a", "world_id": "institution",
                    "plan_id": "plan-a", "goal_id": "goal-a",
                    "steps": [{
                        "step_id": "analyze", "action": "Analyze institutional evidence.",
                        "required_capabilities": ["analyze"],
                        "expected_outcomes": ["analysis complete"]
                    }],
                    "horizon_start": "2026-08-20T10:00:00+00:00",
                    "event_id": "plan", "expected_version": 2,
                    "authorization_ref": "auth-plan",
                })
                ready = post("/api/ready-steps", {
                    "tenant_id": "tenant-a", "world_id": "institution",
                    "at": "2026-08-20T10:01:00+00:00",
                })
                self.assertEqual(ready["items"][0]["step"]["step_id"], "analyze")
                self.assertFalse(ready["binding_authority"])
                proposals = post("/api/assignment-proposals", {
                    "tenant_id": "tenant-a", "world_id": "institution",
                    "at": "2026-08-20T10:01:00+00:00",
                })
                self.assertEqual(proposals["items"][0]["recommended_agent_id"], "agent-a")
                self.assertTrue(proposals["items"][0]["dispatchable"])
                dispatched = post("/api/dispatches", {
                    "tenant_id": "tenant-a", "world_id": "institution",
                    "plan_id": "plan-a", "step_id": "analyze", "agent_id": "agent-a",
                    "event_id": "dispatch", "expected_version": 3,
                    "authorization_ref": "auth-dispatch",
                })
                self.assertEqual(
                    dispatched["state"]["operations"]["plans"]["plan-a"]["steps"]["analyze"]["status"],
                    "ASSIGNED",
                )
                post("/api/step-starts", {
                    "tenant_id": "tenant-a", "world_id": "institution",
                    "plan_id": "plan-a", "step_id": "analyze",
                    "event_id": "start", "expected_version": 4,
                    "authorization_ref": "auth-start",
                })
                outcome = post("/api/step-outcomes", {
                    "tenant_id": "tenant-a", "world_id": "institution",
                    "plan_id": "plan-a", "step_id": "analyze", "success": True,
                    "summary": "The agent reported completion without the required outcome evidence.",
                    "payload": {"report": "incomplete"}, "actual_outcomes": [],
                    "event_id": "outcome", "outcome_id": "outcome-a",
                    "expected_version": 5, "authorization_ref": "auth-outcome",
                })
                self.assertTrue(outcome["outcome"]["reported_success"])
                self.assertFalse(outcome["outcome"]["success"])
                self.assertEqual(outcome["alert"]["type"], "REPLAN_REQUIRED")
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)

    def test_authorized_cancellation_releases_agent_and_resources(self):
        with tempfile.TemporaryDirectory() as directory:
            control = self.control(directory)
            control.bootstrap_world(
                "tenant-a", "institution", {"name": "Example institution"},
                actor_id="kernel", authorization_ref="bootstrap",
                timestamp="2026-08-20T12:00:00+00:00",
            )
            control.register_agent(
                "tenant-a", "institution", "agent-a", "ROBOT", ["move"],
                event_id="agent", actor_id="kernel", expected_version=0,
                authorization_ref="agent-auth", timestamp="2026-08-20T12:01:00+00:00",
            )
            control.register_resource_pool(
                "tenant-a", "institution", "battery", 5, "kwh",
                event_id="resource", actor_id="kernel", expected_version=1,
                authorization_ref="resource-auth", timestamp="2026-08-20T12:02:00+00:00",
            )
            control.create_goal(
                "tenant-a", "institution", "goal-a",
                "Move the inspection unit to the registered safe staging location.",
                event_id="goal", actor_id="kernel", expected_version=2,
                authorization_ref="goal-auth", timestamp="2026-08-20T12:03:00+00:00",
            )
            control.create_plan(
                "tenant-a", "institution", "plan-a", "goal-a",
                [{
                    "step_id": "move", "action": "Move to the safe staging location.",
                    "required_capabilities": ["move"],
                    "resource_requests": {"battery": 2},
                    "command": {"adapter": "robot-a", "action": "move", "target": "safe-stage"},
                }],
                horizon_start="2026-08-20T12:00:00+00:00", horizon_end=None,
                event_id="plan", actor_id="kernel", expected_version=3,
                authorization_ref="plan-auth", timestamp="2026-08-20T12:04:00+00:00",
            )
            control.dispatch_step(
                "tenant-a", "institution", "plan-a", "move", "agent-a",
                event_id="dispatch", actor_id="kernel", expected_version=4,
                authorization_ref="dispatch-auth", timestamp="2026-08-20T12:05:00+00:00",
            )
            cancelled = control.cancel_step(
                "tenant-a", "institution", "plan-a", "move",
                event_id="cancel", actor_id="kernel", expected_version=5,
                authorization_ref="cancel-auth", reason="Safety operator halted movement.",
                timestamp="2026-08-20T12:06:00+00:00",
            )
            state = cancelled["world"]["state"]["operations"]
            self.assertEqual(state["resource_pools"]["battery"]["allocated"], 0)
            self.assertEqual(state["agents"]["agent-a"]["active_tasks"], [])
            self.assertEqual(state["agents"]["agent-a"]["status"], "AVAILABLE")
            self.assertEqual(state["plans"]["plan-a"]["status"], "NEEDS_REPLAN")
            self.assertEqual(state["plans"]["plan-a"]["steps"]["move"]["status"], "CANCELLED")
            self.assertEqual(cancelled["alert"]["type"], "REPLAN_REQUIRED")


if __name__ == "__main__":
    unittest.main()
from edon.api.server import EDONHTTPServer, PlatformService