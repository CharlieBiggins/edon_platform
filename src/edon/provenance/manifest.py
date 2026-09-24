"""Small artifact-manifest contract used across EDON packages."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ArtifactManifest:
    artifact_id: str
    version: str
    sha256: str
    storage_location: str
    license: str
    claim_scope: str

    def __post_init__(self) -> None:
        if not self.sha256.startswith("sha256:") or len(self.sha256) != 71:
            raise ValueError("artifact sha256 must be a prefixed 64-character digest")