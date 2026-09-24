"""C1 learned-model compatibility layer.

C1 is the architectural name for the learned component historically called
Cerebrum in EDON experiments. Historical classes remain import-compatible.
"""

from __future__ import annotations

from .operations import OperationsProposalAdapter, OperationsProvider


C1Provider = OperationsProvider


class C1OperationsAdapter(OperationsProposalAdapter):
    """Validate C1 output through the historical Cerebrum proposal firewall."""


__all__ = ["C1OperationsAdapter", "C1Provider"]