"""Proposal object passed to deterministic execution authority."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RuntimeProposal:
    proposal_id: str
    mechanism_version: str
    proposed_transition: dict[str, Any]
    model_manifest_sha256: str
    input_sha256: str
    binding_authority: bool = False

    def __post_init__(self) -> None:
        if self.binding_authority:
            raise ValueError("learned proposals must remain non-authoritative")