#!/usr/bin/env python3
"""Shared full-regression scorer for DEV-017."""

from __future__ import annotations

import importlib
import sys
from typing import Any

from dev017_common import BASE
from gate import advancement_gate


def load_evaluator():
    sys.path.insert(0, str(BASE))
    try:
        return importlib.import_module("evaluate")
    finally:
        sys.path.pop(0)


def score_rows(expected: list[dict[str, Any]], predictions: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    result = load_evaluator().score(
        predictions,
        expected,
        config["primary_condition"],
        config["continuation_seed"],
    )
    result["full_regression_gate"] = advancement_gate(result, config["gate"])
    return result