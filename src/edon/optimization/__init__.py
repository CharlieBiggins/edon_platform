"""Non-binding optimization-provider contracts."""

from .adapter import (
    DeterministicCapacityAllocator,
    OptimizationAdapter,
    OptimizationError,
)

__all__ = [
    "DeterministicCapacityAllocator",
    "OptimizationAdapter",
    "OptimizationError",
]