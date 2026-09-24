import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class InstitutionalEnvironmentGatewayArchitectureTests(unittest.TestCase):
    def test_architecture_package_is_fail_closed(self):
        manifest = json.loads(
            (
                ROOT
                / "product"
                / "institutional-environment-gateway"
                / "manifest.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(
            manifest["status"],
            "ARCHITECTURE_DEFINED_PARTIALLY_IMPLEMENTED_NOT_PRODUCTION_AUTHORIZED",
        )
        self.assertEqual(manifest["entity_classes"], ["AGENT", "SYSTEM", "RESOURCE"])
        self.assertEqual(manifest["native_system_connectors_implemented"], 0)
        self.assertEqual(manifest["native_resource_adapters_implemented"], 0)
        self.assertFalse(manifest["outbound_environment_delivery_implemented"])
        self.assertFalse(manifest["production_validated"])
        self.assertFalse(manifest["binding_authority"])

    def test_environment_event_contract_cannot_authorize_or_execute(self):
        schema = json.loads(
            (ROOT / "schemas" / "environment" / "event.schema.json").read_text(
                encoding="utf-8"
            )
        )
        properties = schema["properties"]
        self.assertEqual(properties["binding_authority"]["const"], False)
        self.assertEqual(properties["executed"]["const"], False)
        self.assertEqual(
            set(properties["entity_class"]["enum"]), {"AGENT", "SYSTEM", "RESOURCE"}
        )
        self.assertIn("available_to_controller_at", schema["required"])
        self.assertNotIn("authorization_ref", properties)


if __name__ == "__main__":
    unittest.main()