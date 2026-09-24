import json
import sqlite3
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from edon.cerebrum import (
    DeterministicShadowProvider,
    OperationsProposalAdapter,
    OperationsProposalError,
)
from edon.api.server import EDONHTTPServer, PlatformService
from edon.kernel import KernelAuthorizedWorld, KernelTokenAuthority, KernelTokenError
from edon.memory import EpisodicMemoryStore
from edon.operations import InstitutionalControlPlane
from edon.outbox import TransactionalOutbox
from edon.supervisor import ShadowCycleStore, ShadowSupervisor
from edon.world import WorldStateStore


class KernelTokenAndOutboxTests(unittest.TestCase):
    def test_exact_tokens_replay_protection_and_outbox_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            worlds = WorldStateStore(root / "world.sqlite3")
            authority = KernelTokenAuthority(root / "tokens.sqlite3", b"k" * 32)
            secured = KernelAuthorizedWorld(worlds, authority)
            initial = {"value": 1, "operations": {}}
            creation_mutation = [{"op": "REPLACE_ROOT", "path": [], "value": initial}]
            creation_token = authority.issue_world_event(
                tenant_id="tenant-a", world_id="world-a", actor_id="kernel-actor",
                authority_version="authority:v1", expected_world_version=-1,
                event_id="WORLD_CREATED", event_type="WORLD_CREATED",
                mutations=creation_mutation,
            )
            created = secured.create_world(
                "tenant-a", "world-a", initial, actor_id="kernel-actor",
                authority_version="authority:v1", execution_token=creation_token,
                timestamp="2026-08-21T05:00:00+00:00",
            )
            self.assertEqual(created["version"], 0)

            mutations = [{"op": "SET", "path": ["value"], "value": 2}]
            token = authority.issue_world_event(
                tenant_id="tenant-a", world_id="world-a", actor_id="kernel-actor",
                authority_version="authority:v1", expected_world_version=0,
                event_id="event-001", event_type="VALUE_CHANGED", mutations=mutations,
            )
            with self.assertRaisesRegex(KernelTokenError, "mutations_sha256"):
                secured.append_event(
                    "tenant-a", "world-a", "event-001", "VALUE_CHANGED",
                    [{"op": "SET", "path": ["value"], "value": 999}],
                    actor_id="kernel-actor", authority_version="authority:v1",
                    expected_version=0, execution_token=token,
                )
            updated = secured.append_event(
                "tenant-a", "world-a", "event-001", "VALUE_CHANGED", mutations,
                actor_id="kernel-actor", authority_version="authority:v1",
                expected_version=0, execution_token=token,
                timestamp="2026-08-21T05:01:00+00:00",
            )
            self.assertEqual(updated["state"]["value"], 2)
            repeated = secured.append_event(
                "tenant-a", "world-a", "event-001", "VALUE_CHANGED", mutations,
                actor_id="kernel-actor", authority_version="authority:v1",
                expected_version=0, execution_token=token,
                timestamp="2026-08-21T05:01:00+00:00",
            )
            self.assertEqual(repeated["version"], 1)
            with self.assertRaisesRegex(KernelTokenError, "event_id"):
                authority.verify_world_event(
                    token, tenant_id="tenant-a", world_id="world-a",
                    actor_id="kernel-actor", authority_version="authority:v1",
                    expected_world_version=0, event_id="event-other",
                    event_type="VALUE_CHANGED", mutations=mutations,
                )
            self.assertEqual(authority.consumed_count(), 2)

            old = datetime(2026, 8, 20, tzinfo=UTC)
            expired = authority.issue_world_event(
                tenant_id="tenant-a", world_id="world-a", actor_id="kernel-actor",
                authority_version="authority:v1", expected_world_version=1,
                event_id="expired", event_type="EXPIRED", mutations=mutations,
                ttl_seconds=1, now=old,
            )
            with self.assertRaisesRegex(KernelTokenError, "expired"):
                authority.verify_world_event(
                    expired, tenant_id="tenant-a", world_id="world-a",
                    actor_id="kernel-actor", authority_version="authority:v1",
                    expected_world_version=1, event_id="expired", event_type="EXPIRED",
                    mutations=mutations, now=old + timedelta(seconds=2),
                )

            outbox = TransactionalOutbox(worlds.path)
            messages = outbox.list_messages(status="PENDING")
            self.assertEqual(len(messages), 2)
            claimed = outbox.claim("worker-a", limit=2, now="2026-08-21T05:02:00+00:00")
            self.assertEqual(len(claimed), 2)
            delivered = outbox.acknowledge(
                claimed[0]["message_id"], "worker-a", now="2026-08-21T05:02:01+00:00"
            )
            self.assertEqual(delivered["status"], "DELIVERED")
            retried = outbox.fail(
                claimed[1]["message_id"], "worker-a", "temporary downstream failure",
                retry_after_seconds=1, now="2026-08-21T05:02:01+00:00",
            )
            self.assertEqual(retried["status"], "PENDING")
            reclaimed = outbox.claim(
                "worker-b", limit=2, now="2026-08-21T05:02:03+00:00"
            )
            self.assertEqual([row["message_id"] for row in reclaimed], [claimed[1]["message_id"]])
            outbox.acknowledge(
                reclaimed[0]["message_id"], "worker-b", now="2026-08-21T05:02:04+00:00"
            )
            self.assertEqual(len(outbox.list_messages(status="DELIVERED")), 2)
            self.assertIn("RETRY_SCHEDULED", {row["action"] for row in outbox.audit_events()})

            with self.assertRaises(sqlite3.DatabaseError):
                with closing(sqlite3.connect(authority.path)) as connection:
                    connection.execute("DELETE FROM consumed_kernel_tokens")

    def test_separate_api_authorizer_and_committer_roles(self):
        with tempfile.TemporaryDirectory() as directory:
            server = EDONHTTPServer(
                ("127.0.0.1", 0),
                PlatformService(directory),
                {
                    "authorizer-token-000000": "KERNEL_AUTHORIZER",
                    "committer-token-0000000": "KERNEL_COMMITTER",
                },
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_address[1]}"

            def request(path: str, token: str, body: dict | None = None) -> dict:
                data = json.dumps(body).encode("utf-8") if body is not None else None
                call = urllib.request.Request(
                    base + path, data=data, method="POST" if body is not None else "GET",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                )
                with urllib.request.urlopen(call) as response:
                    return json.loads(response.read().decode("utf-8"))

            try:
                identity = request("/api/whoami", "committer-token-0000000")
                initial = {"status": "READY"}
                mutations = [{"op": "REPLACE_ROOT", "path": [], "value": initial}]
                issued = request("/api/kernel/tokens", "authorizer-token-000000", {
                    "tenant_id": "tenant-a", "world_id": "secure-world",
                    "subject_actor_id": identity["actor_id"],
                    "authority_version": "authority:v1", "expected_world_version": -1,
                    "event_id": "WORLD_CREATED", "event_type": "WORLD_CREATED",
                    "mutations": mutations,
                })
                self.assertTrue(issued["binding_authority"])
                created = request("/api/kernel/worlds", "committer-token-0000000", {
                    "tenant_id": "tenant-a", "world_id": "secure-world",
                    "initial_state": initial, "authority_version": "authority:v1",
                    "execution_token": issued["execution_token"],
                })
                self.assertEqual(created["version"], 0)
                status = request("/api/status", "committer-token-0000000")
                self.assertEqual(status["counts"]["kernel_tokens_consumed"], 1)
                self.assertEqual(status["counts"]["outbox_pending"], 1)
                with self.assertRaises(urllib.error.HTTPError) as tampered:
                    request("/api/kernel/worlds", "committer-token-0000000", {
                        "tenant_id": "tenant-a", "world_id": "secure-world-2",
                        "initial_state": {"status": "TAMPERED"},
                        "authority_version": "authority:v1",
                        "execution_token": issued["execution_token"],
                    })
                self.assertEqual(tampered.exception.code, 400)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)


class CerebrumSupervisorTests(unittest.TestCase):
    def test_shadow_supervisor_proposes_without_committing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            worlds = WorldStateStore(root / "world.sqlite3")
            memory = EpisodicMemoryStore(root / "memory.sqlite3")
            control = InstitutionalControlPlane(worlds, memory)
            control.bootstrap_world(
                "tenant-a", "institution", {"name": "Example institution"},
                actor_id="kernel", authorization_ref="bootstrap",
                timestamp="2026-08-21T06:00:00+00:00",
            )
            control.register_agent(
                "tenant-a", "institution", "agent-a", "SOFTWARE", ["analyze"],
                event_id="agent", actor_id="kernel", expected_version=0,
                authorization_ref="agent-auth", timestamp="2026-08-21T06:01:00+00:00",
            )
            control.create_goal(
                "tenant-a", "institution", "goal-a",
                "Analyze the current institution and prepare a verified operational report.",
                event_id="goal", actor_id="kernel", expected_version=1,
                authorization_ref="goal-auth", timestamp="2026-08-21T06:02:00+00:00",
            )
            control.create_plan(
                "tenant-a", "institution", "plan-a", "goal-a",
                [{
                    "step_id": "analyze", "action": "Analyze institutional state.",
                    "required_capabilities": ["analyze"]
                }],
                horizon_start="2026-08-21T06:00:00+00:00", horizon_end=None,
                event_id="plan", actor_id="kernel", expected_version=2,
                authorization_ref="plan-auth", timestamp="2026-08-21T06:03:00+00:00",
            )
            before = worlds.get_world("tenant-a", "institution")
            adapter = OperationsProposalAdapter(
                DeterministicShadowProvider(), model_lineage="reference-shadow-provider:v1"
            )
            cycles = ShadowCycleStore(root / "cycles.sqlite3")
            supervisor = ShadowSupervisor(control, adapter, cycles)
            cycle = supervisor.run_cycle(
                "tenant-a", "institution", "cycle-001", at="2026-08-21T06:04:00+00:00"
            )
            self.assertEqual(cycle["proposal"]["proposal_type"], "DISPATCH_STEP")
            self.assertFalse(cycle["proposal"]["binding_authority"])
            self.assertEqual(cycle["status"], "SHADOW_ONLY")
            after = worlds.get_world("tenant-a", "institution")
            self.assertEqual(after["version"], before["version"])
            self.assertEqual(after["state_sha256"], before["state_sha256"])
            repeated = supervisor.run_cycle(
                "tenant-a", "institution", "cycle-001", at="2026-08-21T06:04:00+00:00"
            )
            self.assertEqual(repeated["proposal_sha256"], cycle["proposal_sha256"])

    def test_adapter_rejects_authority_smuggling(self):
        class UnsafeProvider:
            def propose(self, context):
                return {
                    "proposal_type": "ABSTAIN",
                    "payload": {},
                    "rationale": "The provider attempts to emit an unauthorized execution token.",
                    "confidence": 1.0,
                    "authorization_ref": "forged",
                }

        adapter = OperationsProposalAdapter(UnsafeProvider(), model_lineage="unsafe:test")
        with self.assertRaisesRegex(OperationsProposalError, "authority fields"):
            adapter.propose({"state": {}})


if __name__ == "__main__":
    unittest.main()