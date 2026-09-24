import json
import sqlite3
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from edon.api.server import EDONHTTPServer, PlatformService
from edon.memory import EpisodicMemoryStore, MemoryStoreError
from edon.world import WorldStateError, WorldStateStore


INITIAL_STATE = {
    "clock": {"logical_time": 0},
    "goals": {"active": []},
    "resources": {"capacity": 10, "allocated": 0},
    "workflow": {"status": "READY"},
}


class WorldStateTests(unittest.TestCase):
    def test_versioned_events_replay_restore_and_tenant_isolation(self):
        with tempfile.TemporaryDirectory() as directory:
            store = WorldStateStore(Path(directory) / "world.sqlite3")
            created = store.create_world(
                "tenant-a",
                "operations",
                INITIAL_STATE,
                actor_id="kernel",
                authorization_ref="kernel-token-creation",
                source_lineage=["institution-ir:v1"],
                timestamp="2026-08-20T00:00:00+00:00",
            )
            self.assertEqual(created["version"], 0)
            self.assertFalse(created["binding_authority"])

            updated = store.append_event(
                "tenant-a",
                "operations",
                "event-001",
                "GOAL_ACCEPTED",
                [
                    {"op": "APPEND_UNIQUE", "path": ["goals", "active"], "value": "goal-a"},
                    {"op": "INCREMENT", "path": ["resources", "allocated"], "value": 3},
                    {"op": "SET", "path": ["workflow", "status"], "value": "RUNNING"},
                ],
                actor_id="kernel",
                expected_version=0,
                authorization_ref="kernel-token-001",
                source_lineage=["proposal:goal-a", "policy:v4"],
                timestamp="2026-08-20T00:01:00+00:00",
            )
            self.assertEqual(updated["version"], 1)
            self.assertEqual(updated["state"]["resources"]["allocated"], 3)
            self.assertEqual(updated["state"]["goals"]["active"], ["goal-a"])

            duplicate = store.append_event(
                "tenant-a",
                "operations",
                "event-001",
                "GOAL_ACCEPTED",
                [
                    {"op": "APPEND_UNIQUE", "path": ["goals", "active"], "value": "goal-a"},
                    {"op": "INCREMENT", "path": ["resources", "allocated"], "value": 3},
                    {"op": "SET", "path": ["workflow", "status"], "value": "RUNNING"},
                ],
                actor_id="kernel",
                expected_version=0,
                authorization_ref="kernel-token-001",
                source_lineage=["policy:v4", "proposal:goal-a"],
            )
            self.assertEqual(duplicate["version"], 1)
            self.assertEqual(len(store.events("tenant-a", "operations")), 2)

            with self.assertRaisesRegex(WorldStateError, "different content"):
                store.append_event(
                    "tenant-a", "operations", "event-001", "GOAL_ACCEPTED",
                    [{"op": "SET", "path": ["workflow", "status"], "value": "FAILED"}],
                    actor_id="kernel", expected_version=1,
                    authorization_ref="kernel-token-other",
                )
            with self.assertRaisesRegex(WorldStateError, "version conflict"):
                store.append_event(
                    "tenant-a", "operations", "event-stale", "STALE",
                    [{"op": "SET", "path": ["workflow", "status"], "value": "FAILED"}],
                    actor_id="kernel", expected_version=0,
                    authorization_ref="kernel-token-stale",
                )
            with self.assertRaisesRegex(WorldStateError, "not found"):
                store.get_world("tenant-b", "operations")

            restored = store.restore_version(
                "tenant-a",
                "operations",
                0,
                event_id="event-restore",
                actor_id="kernel",
                expected_version=1,
                authorization_ref="kernel-token-restore",
                timestamp="2026-08-20T00:02:00+00:00",
            )
            self.assertEqual(restored["version"], 2)
            self.assertEqual(restored["state"], INITIAL_STATE)
            verification = store.verify_world("tenant-a", "operations")
            self.assertTrue(verification["passed"], verification)

            with self.assertRaises(sqlite3.DatabaseError):
                with sqlite3.connect(store.path) as connection:
                    connection.execute("UPDATE world_events SET event_type = 'TAMPERED'")

    def test_replay_detects_current_state_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            store = WorldStateStore(Path(directory) / "world.sqlite3")
            store.create_world(
                "tenant-a", "operations", INITIAL_STATE,
                actor_id="kernel", authorization_ref="kernel-create",
                timestamp="2026-08-20T00:00:00+00:00",
            )
            with sqlite3.connect(store.path) as connection:
                connection.execute(
                    "UPDATE worlds SET state_json = ? WHERE tenant_id = ? AND world_id = ?",
                    (json.dumps({"tampered": True}), "tenant-a", "operations"),
                )
            verification = store.verify_world("tenant-a", "operations")
            self.assertFalse(verification["passed"])
            self.assertFalse(verification["checks"]["current_state_matches_replay"])


class EpisodicMemoryTests(unittest.TestCase):
    def test_provenance_access_retention_tombstone_and_audit(self):
        with tempfile.TemporaryDirectory() as directory:
            store = EpisodicMemoryStore(Path(directory) / "memory.sqlite3")
            recorded = store.record_episode(
                "tenant-a",
                "memory-001",
                "operations",
                "RESOURCE_DECISION",
                "Allocation for the emergency inspection goal was approved.",
                {"goal_id": "goal-a", "allocated": 3},
                occurred_at="2026-08-20T00:01:00+00:00",
                sensitivity="CONFIDENTIAL",
                actor_id="memory-writer",
                authorization_ref="memory-auth-001",
                source_event_ids=["event-001"],
                provenance={"world_state_sha256": "sha256:" + "a" * 64},
                retention_until="2026-09-20T00:00:00+00:00",
                timestamp="2026-08-20T00:02:00+00:00",
            )
            self.assertEqual(recorded["sensitivity"], "CONFIDENTIAL")
            self.assertFalse(recorded["binding_authority"])

            results = store.query(
                "tenant-a",
                "emergency allocation",
                actor_id="reviewer",
                allowed_sensitivities=["CONFIDENTIAL"],
                world_id="operations",
                as_of="2026-08-21T00:00:00+00:00",
                timestamp="2026-08-21T00:00:01+00:00",
            )
            self.assertEqual([row["memory_id"] for row in results], ["memory-001"])
            self.assertGreater(results[0]["retrieval_score"], 0)

            self.assertEqual(
                store.query(
                    "tenant-b", "emergency", actor_id="reviewer",
                    allowed_sensitivities=["CONFIDENTIAL"],
                    as_of="2026-08-21T00:00:00+00:00",
                ),
                [],
            )
            self.assertEqual(
                store.query(
                    "tenant-a", "emergency", actor_id="viewer",
                    allowed_sensitivities=["PUBLIC", "INTERNAL"],
                    as_of="2026-08-21T00:00:00+00:00",
                ),
                [],
            )
            self.assertEqual(
                store.query(
                    "tenant-a", "emergency", actor_id="reviewer",
                    allowed_sensitivities=["CONFIDENTIAL"],
                    as_of="2026-10-01T00:00:00+00:00",
                ),
                [],
            )

            store.tombstone(
                "tenant-a",
                "memory-001",
                actor_id="privacy-officer",
                reason="retention withdrawal approved",
                authorization_ref="privacy-auth-001",
                timestamp="2026-08-22T00:00:00+00:00",
            )
            with self.assertRaisesRegex(MemoryStoreError, "not found"):
                store.get_episode(
                    "tenant-a", "memory-001", actor_id="reviewer",
                    allowed_sensitivities=["CONFIDENTIAL"],
                )
            self.assertTrue(store.verify_audit_chain("tenant-a"))
            actions = [row["action"] for row in store.audit_events("tenant-a")]
            self.assertIn("MEMORY_RECORDED", actions)
            self.assertIn("MEMORY_QUERY", actions)
            self.assertIn("MEMORY_TOMBSTONED", actions)

            with self.assertRaises(sqlite3.DatabaseError):
                with sqlite3.connect(store.path) as connection:
                    connection.execute("UPDATE memory_entries SET summary = 'tampered'")

    def test_memory_requires_custody_and_idempotent_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            store = EpisodicMemoryStore(Path(directory) / "memory.sqlite3")
            with self.assertRaisesRegex(MemoryStoreError, "source_event_ids or provenance"):
                store.record_episode(
                    "tenant-a", "memory-001", "world", "OBSERVATION",
                    "A sufficiently descriptive institutional observation.", {},
                    occurred_at="2026-08-20T00:00:00+00:00",
                    sensitivity="INTERNAL", actor_id="writer",
                    authorization_ref="auth",
                )
            first = store.record_episode(
                "tenant-a", "memory-001", "world", "OBSERVATION",
                "A sufficiently descriptive institutional observation.", {"value": 1},
                occurred_at="2026-08-20T00:00:00+00:00",
                sensitivity="INTERNAL", actor_id="writer",
                authorization_ref="auth", source_event_ids=["event-001"],
            )
            repeated = store.record_episode(
                "tenant-a", "memory-001", "world", "OBSERVATION",
                "A sufficiently descriptive institutional observation.", {"value": 1},
                occurred_at="2026-08-20T00:00:00+00:00",
                sensitivity="INTERNAL", actor_id="writer",
                authorization_ref="auth", source_event_ids=["event-001"],
            )
            self.assertEqual(first["content_sha256"], repeated["content_sha256"])
            self.assertEqual(store.count_entries(), 1)
            with self.assertRaisesRegex(MemoryStoreError, "different content"):
                store.record_episode(
                    "tenant-a", "memory-001", "world", "OBSERVATION",
                    "A different institutional observation is recorded here.", {"value": 2},
                    occurred_at="2026-08-20T00:00:00+00:00",
                    sensitivity="INTERNAL", actor_id="writer",
                    authorization_ref="auth", source_event_ids=["event-001"],
                )


class ContinuityPlatformTests(unittest.TestCase):
    def test_platform_service_exposes_world_and_memory_counts(self):
        with tempfile.TemporaryDirectory() as directory:
            service = PlatformService(directory)
            world = service.create_world({
                "tenant_id": "tenant-a",
                "world_id": "operations",
                "initial_state": INITIAL_STATE,
                "actor_id": "api-operator",
                "authorization_ref": "kernel-create",
                "source_lineage": ["institution-ir:v1"],
            })
            service.append_world_event({
                "tenant_id": "tenant-a",
                "world_id": "operations",
                "event_id": "event-001",
                "event_type": "GOAL_ACCEPTED",
                "mutations": [
                    {"op": "APPEND_UNIQUE", "path": ["goals", "active"], "value": "goal-a"}
                ],
                "actor_id": "api-operator",
                "expected_version": world["version"],
                "authorization_ref": "kernel-event",
            })
            service.record_memory({
                "tenant_id": "tenant-a",
                "memory_id": "memory-001",
                "world_id": "operations",
                "episode_type": "GOAL_DECISION",
                "summary": "The emergency inspection goal was accepted for execution.",
                "payload": {"goal_id": "goal-a"},
                "occurred_at": "2026-08-20T00:01:00+00:00",
                "sensitivity": "INTERNAL",
                "actor_id": "api-operator",
                "authorization_ref": "memory-auth",
                "source_event_ids": ["event-001"],
            })
            status = service.status()
            self.assertEqual(status["counts"]["institutional_worlds"], 1)
            self.assertEqual(status["counts"]["episodic_memories"], 1)
            self.assertTrue(service.verify_world({
                "tenant_id": "tenant-a", "world_id": "operations"
            })["passed"])

    def test_world_operator_api_enforces_memory_sensitivity(self):
        with tempfile.TemporaryDirectory() as directory:
            server = EDONHTTPServer(
                ("127.0.0.1", 0),
                PlatformService(directory),
                {"world-token-000000": "WORLD_OPERATOR"},
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_address[1]}"

            def post(path: str, body: dict):
                request = urllib.request.Request(
                    base + path,
                    data=json.dumps(body).encode("utf-8"),
                    method="POST",
                    headers={
                        "Authorization": "Bearer world-token-000000",
                        "Content-Type": "application/json",
                    },
                )
                return urllib.request.urlopen(request)

            try:
                with post("/api/worlds", {
                    "tenant_id": "tenant-a",
                    "world_id": "operations",
                    "initial_state": INITIAL_STATE,
                    "authorization_ref": "kernel-create",
                }) as response:
                    self.assertEqual(response.status, 200)

                confidential = {
                    "tenant_id": "tenant-a",
                    "memory_id": "memory-api-001",
                    "world_id": "operations",
                    "episode_type": "OBSERVATION",
                    "summary": "The authorized operator recorded an internal operational observation.",
                    "payload": {"status": "READY"},
                    "occurred_at": "2026-08-20T00:00:00+00:00",
                    "sensitivity": "CONFIDENTIAL",
                    "authorization_ref": "memory-create",
                    "source_event_ids": ["WORLD_CREATED"],
                }
                with post("/api/memories", confidential) as response:
                    self.assertEqual(response.status, 200)

                restricted = dict(confidential)
                restricted["memory_id"] = "memory-api-002"
                restricted["sensitivity"] = "RESTRICTED"
                with self.assertRaises(urllib.error.HTTPError) as denied:
                    post("/api/memories", restricted)
                self.assertEqual(denied.exception.code, 400)

                with self.assertRaises(urllib.error.HTTPError) as denied_query:
                    post("/api/memory-query", {
                        "tenant_id": "tenant-a",
                        "query": "operational observation",
                        "allowed_sensitivities": ["RESTRICTED"],
                    })
                self.assertEqual(denied_query.exception.code, 400)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()