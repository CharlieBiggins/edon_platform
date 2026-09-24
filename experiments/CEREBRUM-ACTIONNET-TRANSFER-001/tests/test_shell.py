import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("transfer001", ROOT / "run.py")
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)


class ShellTests(unittest.TestCase):
    def test_shell_contains_no_protected_instrument(self):
        value = module.preflight()
        self.assertFalse(value["protected_cases_present"])
        self.assertFalse((ROOT / "inputs.jsonl").exists())
        self.assertFalse((ROOT / "reference.jsonl").exists())

    def test_template_is_blocked(self):
        with self.assertRaises(ValueError):
            module.validate_custody(module.read(ROOT / "custody.template.json"))


if __name__ == "__main__": unittest.main()