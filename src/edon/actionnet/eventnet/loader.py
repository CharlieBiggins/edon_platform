"""Load preserved versioned ActionNet worlds without flattening their identities."""

from __future__ import annotations

import importlib.util
from functools import lru_cache
from pathlib import Path
from types import ModuleType
from typing import Any


WORLD_FILES = {
    "001": ("ACTIONNET-DATA-QUAL-001", "actionnet.py"),
    "002": ("ACTIONNET-DATA-QUAL-002", "actionnet_repair.py"),
    "003": ("ACTIONNET-DATA-QUAL-003", "actionnet_multiview.py"),
    "004": ("ACTIONNET-DATA-QUAL-004", "actionnet_eventnet.py"),
    "005": ("ACTIONNET-DATA-QUAL-005", "actionnet_eventnet.py"),
    "006": ("ACTIONNET-DATA-QUAL-006", "actionnet_eventnet.py"),
    "007": ("ACTIONNET-DATA-QUAL-007", "actionnet_eventnet.py"),
    "008": ("ACTIONNET-DATA-QUAL-008", "actionnet_multidomain.py"),
}


def available_worlds() -> tuple[str, ...]:
    return tuple(WORLD_FILES)


@lru_cache(maxsize=None)
def load_world(version: str) -> ModuleType:
    try:
        directory, filename = WORLD_FILES[version]
    except KeyError as exc:
        raise ValueError(f"unsupported ActionNet world: {version}") from exc
    path = Path(__file__).resolve().parent / "worlds" / directory / filename
    if not path.is_file():
        raise RuntimeError(
            f"ActionNet world {version} is not imported; run scripts/data/import_actionnet_world.py"
        )
    spec = importlib.util.spec_from_file_location(f"edon_actionnet_world_{version}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load ActionNet world: {version}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def generate_world(version: str) -> dict[str, Any]:
    module = load_world(version)
    generated = module.generate()
    controls = generated.get("controls")
    if isinstance(controls, dict) and not all(controls.values()):
        failed = sorted(name for name, passed in generated.get("controls", {}).items() if not passed)
        raise RuntimeError(f"ActionNet world {version} failed controls: {failed}")
    return generated