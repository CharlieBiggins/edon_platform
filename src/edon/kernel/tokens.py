"""Mutation-bound, expiring HMAC execution tokens with durable replay protection."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

from edon.common.hashing import canonical_json, sha256_json
from edon.world.store import normalize_mutations


class KernelTokenError(RuntimeError):
    """Raised when an execution token is malformed, expired, mismatched, or replayed."""


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    try:
        return base64.urlsafe_b64decode((value + padding).encode("ascii"))
    except Exception as exc:
        raise KernelTokenError("execution token contains invalid base64") from exc


def _identifier(value: Any, label: str) -> str:
    normalized = str(value).strip()
    if not normalized or len(normalized) > 200:
        raise KernelTokenError(f"{label} must contain between 1 and 200 characters")
    return normalized


def _epoch(value: datetime | None = None) -> int:
    return int((value or datetime.now(UTC)).timestamp())


class KernelTokenAuthority:
    """Issues exact-request tokens and records successful consumption durably."""

    def __init__(self, path: Path | str, secret: bytes | str, *, key_id: str = "kernel-local-v1"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.secret = secret.encode("utf-8") if isinstance(secret, str) else bytes(secret)
        if len(self.secret) < 32:
            raise KernelTokenError("Kernel signing secret must contain at least 32 bytes")
        self.key_id = _identifier(key_id, "key_id")
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    @contextmanager
    def _connection(self):
        connection = self._connect()
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS consumed_kernel_tokens (
                    token_id TEXT PRIMARY KEY,
                    token_sha256 TEXT NOT NULL UNIQUE,
                    event_identity TEXT NOT NULL,
                    event_hash TEXT NOT NULL,
                    consumed_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS issued_kernel_tokens (
                    token_id TEXT PRIMARY KEY,
                    claims_sha256 TEXT NOT NULL UNIQUE,
                    issuer_id TEXT NOT NULL,
                    issued_at INTEGER NOT NULL,
                    expires_at INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TRIGGER IF NOT EXISTS issued_kernel_tokens_no_update
                BEFORE UPDATE ON issued_kernel_tokens BEGIN
                    SELECT RAISE(ABORT, 'issued Kernel tokens are immutable');
                END;
                CREATE TRIGGER IF NOT EXISTS issued_kernel_tokens_no_delete
                BEFORE DELETE ON issued_kernel_tokens BEGIN
                    SELECT RAISE(ABORT, 'issued Kernel tokens are immutable');
                END;
                CREATE TRIGGER IF NOT EXISTS consumed_kernel_tokens_no_update
                BEFORE UPDATE ON consumed_kernel_tokens BEGIN
                    SELECT RAISE(ABORT, 'consumed Kernel tokens are immutable');
                END;
                CREATE TRIGGER IF NOT EXISTS consumed_kernel_tokens_no_delete
                BEFORE DELETE ON consumed_kernel_tokens BEGIN
                    SELECT RAISE(ABORT, 'consumed Kernel tokens are immutable');
                END;
                """
            )
        self.path.chmod(0o600)

    def _sign(self, payload_segment: str) -> str:
        return _b64encode(hmac.new(self.secret, payload_segment.encode("ascii"), hashlib.sha256).digest())

    def issue_world_event(
        self,
        *,
        tenant_id: str,
        world_id: str,
        actor_id: str,
        authority_version: str,
        expected_world_version: int,
        event_id: str,
        event_type: str,
        mutations: Iterable[dict[str, Any]],
        ttl_seconds: int = 300,
        issuer_id: str = "kernel-authority",
        now: datetime | None = None,
    ) -> str:
        ttl_seconds = int(ttl_seconds)
        if ttl_seconds < 1 or ttl_seconds > 3600:
            raise KernelTokenError("token TTL must be between 1 and 3600 seconds")
        issued_at = _epoch(now)
        normalized = normalize_mutations(mutations)
        payload = {
            "schema_version": "edon-kernel-execution-token.v1",
            "purpose": "WORLD_EVENT_COMMIT",
            "key_id": self.key_id,
            "token_id": secrets.token_urlsafe(18),
            "nonce": secrets.token_urlsafe(18),
            "tenant_id": _identifier(tenant_id, "tenant_id"),
            "world_id": _identifier(world_id, "world_id"),
            "actor_id": _identifier(actor_id, "actor_id"),
            "issuer_id": _identifier(issuer_id, "issuer_id"),
            "authority_version": _identifier(authority_version, "authority_version"),
            "expected_world_version": int(expected_world_version),
            "event_id": _identifier(event_id, "event_id"),
            "event_type": _identifier(event_type, "event_type"),
            "mutations_sha256": sha256_json(normalized),
            "issued_at": issued_at,
            "expires_at": issued_at + ttl_seconds,
            "binding_authority": True,
        }
        segment = _b64encode(canonical_json(payload).encode("utf-8"))
        token = segment + "." + self._sign(segment)
        with self._connection() as connection:
            connection.execute(
                """INSERT INTO issued_kernel_tokens
                   (token_id, claims_sha256, issuer_id, issued_at, expires_at, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    payload["token_id"], sha256_json(payload), payload["issuer_id"],
                    payload["issued_at"], payload["expires_at"],
                    datetime.fromtimestamp(payload["issued_at"], UTC).isoformat(),
                ),
            )
        return token

    def decode_and_verify_signature(self, token: str) -> dict[str, Any]:
        parts = str(token).split(".")
        if len(parts) != 2:
            raise KernelTokenError("execution token must contain payload and signature")
        payload_segment, supplied_signature = parts
        expected_signature = self._sign(payload_segment)
        if not hmac.compare_digest(supplied_signature, expected_signature):
            raise KernelTokenError("execution token signature is invalid")
        try:
            payload = json.loads(_b64decode(payload_segment).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise KernelTokenError("execution token payload is invalid") from exc
        if not isinstance(payload, dict):
            raise KernelTokenError("execution token payload must be an object")
        return payload

    def verify_world_event(
        self,
        token: str,
        *,
        tenant_id: str,
        world_id: str,
        actor_id: str,
        expected_world_version: int,
        event_id: str,
        event_type: str,
        mutations: Iterable[dict[str, Any]],
        authority_version: str | None = None,
        allow_consumed: bool = False,
        expected_event_hash: str | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        payload = self.decode_and_verify_signature(token)
        expected = {
            "schema_version": "edon-kernel-execution-token.v1",
            "purpose": "WORLD_EVENT_COMMIT",
            "key_id": self.key_id,
            "tenant_id": _identifier(tenant_id, "tenant_id"),
            "world_id": _identifier(world_id, "world_id"),
            "actor_id": _identifier(actor_id, "actor_id"),
            "expected_world_version": int(expected_world_version),
            "event_id": _identifier(event_id, "event_id"),
            "event_type": _identifier(event_type, "event_type"),
            "mutations_sha256": sha256_json(normalize_mutations(mutations)),
        }
        for field, value in expected.items():
            if payload.get(field) != value:
                raise KernelTokenError(f"execution token does not match {field}")
        if authority_version is not None and payload.get("authority_version") != authority_version:
            raise KernelTokenError("execution token authority version is stale")
        if payload.get("binding_authority") is not True:
            raise KernelTokenError("execution token does not carry Kernel authority")
        current = _epoch(now)
        if not isinstance(payload.get("issued_at"), int) or not isinstance(payload.get("expires_at"), int):
            raise KernelTokenError("execution token timestamps are invalid")
        if current < payload["issued_at"] - 60:
            raise KernelTokenError("execution token is not yet valid")
        if current > payload["expires_at"]:
            raise KernelTokenError("execution token has expired")
        token_id = _identifier(payload.get("token_id", ""), "token_id")
        event_identity = f"{tenant_id}:{world_id}:{event_id}"
        with self._connection() as connection:
            consumed = connection.execute(
                "SELECT * FROM consumed_kernel_tokens WHERE token_id = ?", (token_id,)
            ).fetchone()
        if consumed:
            if not (
                allow_consumed
                and consumed["event_identity"] == event_identity
                and expected_event_hash is not None
                and consumed["event_hash"] == expected_event_hash
            ):
                raise KernelTokenError("execution token replay detected")
        return payload

    def consume(self, token: str, *, event_identity: str, event_hash: str, now: datetime | None = None) -> None:
        payload = self.decode_and_verify_signature(token)
        token_id = _identifier(payload.get("token_id", ""), "token_id")
        token_hash = "sha256:" + hashlib.sha256(token.encode("utf-8")).hexdigest()
        consumed_at = (now or datetime.now(UTC)).isoformat()
        with self._connection() as connection:
            existing = connection.execute(
                "SELECT * FROM consumed_kernel_tokens WHERE token_id = ?", (token_id,)
            ).fetchone()
            if existing:
                if existing["event_identity"] == event_identity and existing["event_hash"] == event_hash:
                    return
                raise KernelTokenError("execution token replay detected")
            connection.execute(
                """INSERT INTO consumed_kernel_tokens
                   (token_id, token_sha256, event_identity, event_hash, consumed_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (token_id, token_hash, event_identity, event_hash, consumed_at),
            )

    def consumed_count(self) -> int:
        with self._connection() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM consumed_kernel_tokens").fetchone()[0])

    def issued_count(self) -> int:
        with self._connection() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM issued_kernel_tokens").fetchone()[0])