"""Authenticated EDON platform API."""

from .server import PlatformService, run_server

__all__ = ["PlatformService", "run_server"]