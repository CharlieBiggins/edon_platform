import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).parent.parent


class InheritedGenerationTest(unittest.TestCase):
    def test_registered_predecessors_reconstruct_and_fresh_bundle_qualifies(self):
        script = r'''
import json,sys
from pathlib import Path
root=Path(sys.argv[1]);sys.path.insert(0,str(root))
import dataset,foundation
bundle=dataset.generate_bundle(foundation.load_config(root))
print(json.dumps({"train":len(bundle["train_scenarios"]),
"ordinary":len(bundle["train_ordinary"]),"actionnet":len(bundle["train_actionnet"]),
"screen":len(bundle["screen_reference"]),"passed":bundle["qualification"]["passed"]}))
'''
        result = subprocess.run([sys.executable, "-B", "-c", script, str(ROOT)],
                                capture_output=True, text=True, timeout=180)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout),
            {"train": 384, "ordinary": 384, "actionnet": 960, "screen": 24, "passed": True})


if __name__ == "__main__":
    unittest.main()