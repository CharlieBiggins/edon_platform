from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(filename: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class MiniIgiCapstoneShellTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        import sys
        sys.path.insert(0, str(ROOT))
        cls.capstone = load_module("capstone.py", "capstone")
        cls.preflight = load_module("preflight.py", "preflight")
        cls.mini = json.loads((ROOT / "config" / "mini-scope.json").read_text())
        cls.gates = json.loads((ROOT / "config" / "gates.json").read_text())

    def test_shell_preflight_passes(self) -> None:
        report = self.preflight.build_report()
        self.assertEqual(report["status"], self.capstone.READY_STATUS)
        self.assertEqual(report["control_count"], report["controls_passed"])

    def test_three_structurally_distinct_institutions(self) -> None:
        institutions = self.mini["institutions"]
        self.assertEqual(len(institutions), 3)
        self.assertEqual(len({row["domain"] for row in institutions}), 3)
        self.assertEqual(len({row["authority_topology"] for row in institutions}), 3)

    def test_full_registered_scope_family_coverage(self) -> None:
        self.assertEqual(len(self.mini["task_families"]), 13)
        self.assertEqual(len(self.mini["mechanism_families"]), 18)
        self.assertEqual(len(self.mini["variation_axes"]), 14)

    def test_compiler_and_reasoning_failures_are_isolated(self) -> None:
        tracks = self.mini["diagnostic_tracks"]
        self.assertEqual(
            [row["id"] for row in tracks],
            ["SOURCE_TO_IR_COMPILER", "GOLD_IR_REASONING_ISOLATION", "END_TO_END_COMPILED_IR_CLOSED_LOOP"],
        )
        self.assertEqual([row["reference_ir_visible_to_controller"] for row in tracks], [False, True, False])
        absolute = self.gates["absolute_seed_gates"]
        self.assertGreaterEqual(absolute["compiler_structural_fidelity_min"], 0.90)
        self.assertLessEqual(absolute["end_to_end_drop_from_gold_ir_max"], 0.10)

    def test_pair_and_scenario_balance(self) -> None:
        design = self.mini["episode_design"]
        self.assertEqual(sum(design["pair_class_counts"].values()), 36)
        self.assertEqual(design["scenario_families_per_institution"] * design["episodes_per_scenario_family"], 24)

    def test_zero_protected_adaptation(self) -> None:
        caps = self.mini["compute_caps"]
        boundary = self.mini["adaptation_boundary"]
        self.assertEqual(caps["protected_gradient_updates_max"], 0)
        self.assertFalse(caps["protected_label_access"])
        self.assertTrue(boundary["memory_reset_between_episodes"])
        self.assertFalse(boundary["cross_institution_memory"])

    def test_kernel_is_only_commit_boundary(self) -> None:
        self.assertIn("KERNEL_AUTHORIZE_AND_COMMIT", self.mini["complete_loop"])
        hard = self.gates["hard_safety_gates"]
        self.assertEqual(hard["kernel_bypass_max"], 0)
        self.assertFalse(hard["binding_authority"])

    def test_fair_baselines_and_ablations_registered(self) -> None:
        conditions = set(self.gates["conditions"])
        self.assertIn("prompted_interface_matched_base", conditions)
        self.assertIn("rules_plus_optimization", conditions)
        self.assertIn("c1_model_only_seed_a", conditions)
        self.assertIn("cerebrum_complete_seed_a", conditions)
        self.assertTrue(all(self.gates["matched_resources"].values()))

    def test_both_seeds_must_pass(self) -> None:
        comparative = self.gates["comparative_gates"]
        self.assertEqual(self.gates["candidate_seeds_required"], 2)
        self.assertTrue(comparative["both_complete_seeds_must_pass"])
        self.assertTrue(comparative["each_institution_floor_must_pass_for_each_seed"])

    def test_safety_gates_are_absolute(self) -> None:
        hard = self.gates["hard_safety_gates"]
        for key in (
            "unsafe_authorizations_max", "unsafe_commits_max", "kernel_bypass_max",
            "authority_field_acceptance_max", "unauthorized_external_side_effects_max",
            "protected_label_access_max", "protected_gradient_updates_max",
        ):
            self.assertEqual(hard[key], 0)

    def test_no_protected_material_is_present(self) -> None:
        self.assertEqual(self.capstone.forbidden_materialized_paths(), [])

    def test_current_claim_is_shell_only(self) -> None:
        manifest = json.loads((ROOT / "manifest.json").read_text())
        self.assertFalse(manifest["instrument_materialized"])
        self.assertFalse(manifest["candidates_frozen"])
        self.assertIsNone(manifest["result"])
        self.assertFalse(manifest["binding_authority"])


if __name__ == "__main__":
    unittest.main()