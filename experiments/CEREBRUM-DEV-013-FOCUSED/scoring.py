#!/usr/bin/env python3
"""Shared scorer loader for DEV-013."""

from __future__ import annotations

import importlib.util
import sys

from dev013_common import SCORER_PARENT


def load_scorer():
    path = SCORER_PARENT / "score.py"
    spec = importlib.util.spec_from_file_location("dev011_score_for_dev013", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load parent scorer: {path}")
    module = importlib.util.module_from_spec(spec)
    displaced = {
        name: sys.modules.pop(name)
        for name in ("dev011_common", "prepare_data")
        if name in sys.modules
    }
    sys.path.insert(0, str(SCORER_PARENT))
    try:
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)
        sys.modules.pop("dev011_common", None)
        sys.modules.pop("prepare_data", None)
        sys.modules.update(displaced)