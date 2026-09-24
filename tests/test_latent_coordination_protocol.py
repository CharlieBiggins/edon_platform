import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "CEREBRUM-LATENT-COORD-001"


def load_preflight():
    path = EXPERIMENT / "preflight.py"
    spec = importlib.util.spec_from_file_location("latent_coord_preflight", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load latent coordination preflight")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LatentCoordinationProtocolTests(unittest.TestCase):
    def test_environment_gateway_contract_is_fail_closed(self):
        manifest = json.loads(
            (
                ROOT
                / "product"
                / "institutional-environment-gateway"
                / "manifest.json"
            ).read_text(encoding="utf-8")
        )
        schema = json.loads(
            (ROOT / "schemas" / "environment" / "event.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertFalse(manifest["production_validated"])
        self.assertFalse(manifest["binding_authority"])
        self.assertEqual(schema["properties"]["binding_authority"]["const"], False)
        self.assertEqual(schema["properties"]["executed"]["const"], False)

    def test_latent_coordination_shell_passes_all_controls(self):
        report = load_preflight().build_report()
        self.assertEqual(
            report["status"], "SHELL_READY_INSTRUMENT_AND_CANDIDATE_UNMATERIALIZED"
        )
        self.assertEqual(report["controls_passed"], 35)
        self.assertEqual(report["control_count"], 35)
        self.assertEqual(report["forbidden_materialized_paths"], [])

    def test_coordination_state_and_hypothesis_are_non_authoritative(self):
        state = json.loads(
            (ROOT / "schemas" / "cerebrum" / "coordination-state.schema.json").read_text(
                encoding="utf-8"
            )
        )
        hypothesis = json.loads(
            (
                ROOT
                / "schemas"
                / "cerebrum"
                / "coordination-hypothesis.schema.json"
            ).read_text(encoding="utf-8")
        )
        required_channels = set(state["properties"]["channels"]["required"])
        self.assertIn("agent_communications", required_channels)
        self.assertIn("artifact_lineage", required_channels)
        self.assertIn("code_configuration_changes", required_channels)
        self.assertFalse(state["properties"]["binding_authority"]["const"])
        self.assertFalse(hypothesis["properties"]["binding_authority"]["const"])
        self.assertFalse(hypothesis["properties"]["executed"]["const"])


if __name__ == "__main__":
    unittest.main()