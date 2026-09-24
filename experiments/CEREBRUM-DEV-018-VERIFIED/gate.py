#!/usr/bin/env python3
"""Load the frozen 26-check full-regression gate."""

from __future__ import annotations

import importlib.util

from dev018_common import EXPERIMENTS


path = EXPERIMENTS / "CEREBRUM-DEV-014-FULL" / "gate.py"
spec = importlib.util.spec_from_file_location("dev014_gate_for_dev018", path)
if spec is None or spec.loader is None:
    raise RuntimeError(f"cannot load frozen gate: {path}")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
advancement_gate = module.advancement_gate