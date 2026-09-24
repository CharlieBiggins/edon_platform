import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from edon.evaluation import run_fed001
from edon.api.server import PlatformService, authorized
from edon.federation import FederationError, InstitutionalFederationStore
from edon.optimization import OptimizationAdapter, OptimizationError
from edon.world import WorldStateStore


class _TamperedProvider:
    def solve(self, request):
        return {
            "allocations": [{
                "supply_id": "supply", "demand_id": "demand",
                "quantity": 99, "unit_cost": 1,
            }]
        }


class FederationOptimizationTests(unittest.TestCase):
    def test_fed001_gate(self):
        result = run_fed001()
        self.assertEqual(result["status"], "PASS", result["gates"])
        self.assertEqual(result["checks_passed"], result["check_count"])
        self.assertEqual(result["check_count"], 12)

    def test_scope_hierarchy_is_tenant_isolated_and_immutable(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "federation.sqlite3"
            store = InstitutionalFederationStore(
                path, WorldStateStore(Path(directory) / "world.sqlite3")
            )
            store.register_scope("tenant-a", "global", "GLOBAL", "Global")
            store.register_scope(
                "tenant-a", "region", "REGION", "Region", parent_scope_id="global"
            )
            self.assertEqual(store.least_common_ancestor("tenant-a", ["region"]), "region")
            with self.assertRaises(FederationError):
                store.get_scope("tenant-b", "region")
            with self.assertRaises(sqlite3.DatabaseError):
                with closing(sqlite3.connect(path)) as connection:
                    connection.execute(
                        "UPDATE federation_scopes SET name = 'Changed' WHERE scope_id = 'region'"
                    )

    def test_optimization_adapter_rejects_capacity_violation(self):
        request = {
            "request_id": "request", "tenant_id": "tenant", "scope_id": "scope",
            "supplies": [{"supply_id": "supply", "capacity": 1}],
            "demands": [{"demand_id": "demand", "quantity": 1}],
            "lanes": [{
                "supply_id": "supply", "demand_id": "demand",
                "unit_cost": 1, "max_quantity": 1,
            }],
        }
        with self.assertRaisesRegex(OptimizationError, "lane capacity|supply capacity"):
            OptimizationAdapter(
                _TamperedProvider(), provider_lineage="tampered-provider:v1"
            ).propose(request)

    def test_platform_exposes_separate_federation_and_optimization_permissions(self):
        self.assertTrue(authorized("FEDERATION_OPERATOR", "federation"))
        self.assertTrue(authorized("FEDERATION_OPERATOR", "optimize"))
        self.assertFalse(authorized("OPTIMIZATION_OPERATOR", "federation"))
        with tempfile.TemporaryDirectory() as directory:
            service = PlatformService(directory)
            service.operations.bootstrap_world(
                "tenant", "facility-world", {"name": "Facility"},
                actor_id="kernel", authorization_ref="bootstrap",
                timestamp="2026-08-22T02:00:00+00:00",
            )
            service.register_federation_scope({
                "tenant_id": "tenant", "scope_id": "global",
                "scope_type": "GLOBAL", "name": "Global",
            })
            service.register_federation_scope({
                "tenant_id": "tenant", "scope_id": "facility",
                "scope_type": "FACILITY", "name": "Facility",
                "parent_scope_id": "global", "world_id": "facility-world",
            })
            projection = service.project_federation_scope({
                "tenant_id": "tenant", "scope_id": "facility",
                "projection_id": "projection",
            })
            self.assertFalse(projection["binding_authority"])
            candidate = service.optimization_candidate({
                "request_id": "request", "tenant_id": "tenant", "scope_id": "global",
                "supplies": [{"supply_id": "supply", "capacity": 1}],
                "demands": [{"demand_id": "demand", "quantity": 1}],
                "lanes": [{
                    "supply_id": "supply", "demand_id": "demand", "unit_cost": 1,
                }],
            })
            self.assertTrue(candidate["requires_kernel_authorization"])
            self.assertEqual(service.status()["counts"]["federation"]["scopes"], 2)


if __name__ == "__main__":
    unittest.main()