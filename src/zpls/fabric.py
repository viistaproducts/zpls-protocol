from __future__ import annotations

import json
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse

from zpls.frame import OPS, ZPLS_VERSION, ZplsFrame, canonical_json, parse_zpls, semantic_hash, serialize_zpls
from zpls.mesh import ZplsMesh
from zpls.seal import SEAL_KEY, seal_zpls_frame, strip_zpls_seal, verify_zpls_seal

FABRIC_VERSION = "F1"
FABRIC_CONTENT_TYPE = "application/zpls+text"
DEFAULT_TRANSPORTS = ("https+json",)
DEFAULT_FEATURES = ("binary", "mesh", "qfield", "qgate", "qmatrix", "seal")


@dataclass(frozen=True)
class ZplsNodeDescriptor:
    node_id: str
    endpoint: str
    roles: tuple[str, ...] = ("worker",)
    protocol_versions: tuple[str, ...] = (ZPLS_VERSION,)
    transports: tuple[str, ...] = DEFAULT_TRANSPORTS
    features: tuple[str, ...] = DEFAULT_FEATURES
    operations: tuple[str, ...] = tuple(sorted(OPS))
    seal_key_ids: tuple[str, ...] = ("mesh",)

    def __post_init__(self) -> None:
        _validate_token(self.node_id, "node id")
        _validate_endpoint(self.endpoint)
        object.__setattr__(self, "roles", _canonical_tokens(self.roles, "role"))
        object.__setattr__(self, "protocol_versions", _canonical_tokens(self.protocol_versions, "protocol version"))
        object.__setattr__(self, "transports", _canonical_tokens(self.transports, "transport"))
        object.__setattr__(self, "features", _canonical_tokens(self.features, "feature"))
        object.__setattr__(self, "operations", _canonical_tokens(self.operations, "operation"))
        object.__setattr__(self, "seal_key_ids", _canonical_tokens(self.seal_key_ids, "seal key id"))

    def canonical(self) -> dict[str, Any]:
        return {
            "fabric_version": FABRIC_VERSION,
            "node_id": self.node_id,
            "endpoint": self.endpoint,
            "protocol_versions": list(self.protocol_versions),
            "transports": list(self.transports),
            "roles": list(self.roles),
            "operations": list(self.operations),
            "features": list(self.features),
            "seal_key_ids": list(self.seal_key_ids),
        }

    def to_json(self) -> str:
        return canonical_json(self.canonical())


@dataclass(frozen=True)
class CapabilityAgreement:
    protocol_version: str
    transport: str
    operations: tuple[str, ...]
    features: tuple[str, ...]
    seal_key_ids: tuple[str, ...]

    def canonical(self) -> dict[str, Any]:
        return {
            "protocol_version": self.protocol_version,
            "transport": self.transport,
            "operations": list(self.operations),
            "features": list(self.features),
            "seal_key_ids": list(self.seal_key_ids),
        }


@dataclass(frozen=True)
class FabricEnvelope:
    source: str
    destination: str
    frame: ZplsFrame
    trace_id: str
    created_at: int
    ttl: int = 60
    fabric_version: str = FABRIC_VERSION
    content_type: str = FABRIC_CONTENT_TYPE
    route: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.fabric_version != FABRIC_VERSION:
            raise ValueError(f"unsupported ZPL-S fabric version: {self.fabric_version}")
        if self.content_type != FABRIC_CONTENT_TYPE:
            raise ValueError(f"unsupported ZPL-S fabric content type: {self.content_type}")
        _validate_token(self.source, "source")
        _validate_token(self.destination, "destination")
        _validate_token(self.trace_id, "trace id")
        if isinstance(self.created_at, bool) or not isinstance(self.created_at, int) or self.created_at < 0:
            raise ValueError("created_at must be a non-negative integer")
        if isinstance(self.ttl, bool) or not isinstance(self.ttl, int) or not 1 <= self.ttl <= 86_400:
            raise ValueError("ttl must be an integer from 1 to 86400")
        object.__setattr__(self, "route", _canonical_tokens(self.route, "route hop"))

    def canonical(self) -> dict[str, Any]:
        frame_text = serialize_zpls(self.frame)
        return {
            "fabric_version": self.fabric_version,
            "content_type": self.content_type,
            "source": self.source,
            "destination": self.destination,
            "trace_id": self.trace_id,
            "created_at": self.created_at,
            "ttl": self.ttl,
            "route": list(self.route),
            "frame": frame_text,
            "frame_hash": semantic_hash(self.frame),
        }

    def to_json(self) -> str:
        return canonical_json(self.canonical())


@dataclass(frozen=True)
class FabricReceipt:
    accepted: bool
    reason: str
    source: str
    destination: str
    trace_id: str
    frame_hash: str
    receiver: str | None = None

    def canonical(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "reason": self.reason,
            "source": self.source,
            "destination": self.destination,
            "trace_id": self.trace_id,
            "frame_hash": self.frame_hash,
            "receiver": self.receiver,
        }

    def to_json(self) -> str:
        return canonical_json(self.canonical())


class ReplayCache:
    def __init__(self, max_entries: int = 10_000) -> None:
        if isinstance(max_entries, bool) or not isinstance(max_entries, int) or max_entries < 1:
            raise ValueError("max_entries must be a positive integer")
        self.max_entries = max_entries
        self._seen: OrderedDict[tuple[str, str, str], int] = OrderedDict()
        self._lock = threading.Lock()

    def check_and_store(self, envelope: FabricEnvelope, *, now: int) -> bool:
        key = self.key(envelope)
        expires_at = envelope.created_at + envelope.ttl
        with self._lock:
            self._purge_locked(now)
            if key in self._seen:
                return False
            self._seen[key] = expires_at
            self._seen.move_to_end(key)
            while len(self._seen) > self.max_entries:
                self._seen.popitem(last=False)
        return True

    def __len__(self) -> int:
        with self._lock:
            return len(self._seen)

    @staticmethod
    def key(envelope: FabricEnvelope) -> tuple[str, str, str]:
        return (envelope.source, envelope.trace_id, semantic_hash(envelope.frame))

    def _purge_locked(self, now: int) -> None:
        expired = [key for key, expires_at in self._seen.items() if expires_at < now]
        for key in expired:
            del self._seen[key]


class PeerKeyring:
    def __init__(self, keys: Mapping[str, str | bytes] | None = None) -> None:
        self._keys: dict[str, str | bytes] = dict(keys or {})

    def add(self, key_id: str, key: str | bytes) -> None:
        _validate_token(key_id, "seal key id")
        if not key:
            raise ValueError("peer key must not be empty")
        self._keys[key_id] = key

    def mapping(self) -> dict[str, str | bytes]:
        return dict(self._keys)

    def verify(self, frame: ZplsFrame) -> bool:
        return verify_zpls_seal(frame, self._keys)


class ZplsInternetGateway:
    def __init__(
        self,
        descriptor: ZplsNodeDescriptor,
        *,
        keyring: PeerKeyring | None = None,
        mesh: ZplsMesh | None = None,
        require_seal: bool = True,
        replay_cache: ReplayCache | None = None,
        reject_replay: bool = True,
    ) -> None:
        self.descriptor = descriptor
        self.keyring = keyring or PeerKeyring()
        self.require_seal = require_seal
        self.replay_cache = replay_cache if replay_cache is not None else ReplayCache()
        self.reject_replay = reject_replay
        self.mesh = mesh or ZplsMesh()
        for role in descriptor.roles:
            if role not in self.mesh.agents:
                self.mesh.register(role)

    def pack(
        self,
        frame: ZplsFrame,
        *,
        destination: str,
        trace_id: str,
        ttl: int = 60,
        created_at: int | None = None,
        seal_key: str | bytes | None = None,
        seal_key_id: str = "mesh",
    ) -> FabricEnvelope:
        _validate_token(destination, "destination")
        effective = seal_zpls_frame(frame, seal_key, key_id=seal_key_id, replace=True) if seal_key is not None else frame
        return FabricEnvelope(
            source=self.descriptor.node_id,
            destination=destination,
            frame=effective,
            trace_id=trace_id,
            created_at=int(time.time()) if created_at is None else created_at,
            ttl=ttl,
            route=(self.descriptor.node_id,),
        )

    def receive(self, envelope: FabricEnvelope, *, now: int | None = None) -> FabricReceipt:
        now = int(time.time()) if now is None else now
        if envelope.destination not in {self.descriptor.node_id, "*"}:
            return self._receipt(envelope, False, "wrong destination")
        if now > envelope.created_at + envelope.ttl:
            return self._receipt(envelope, False, "expired")
        if self.require_seal and SEAL_KEY not in envelope.frame.delta:
            return self._receipt(envelope, False, "missing seal")
        if SEAL_KEY in envelope.frame.delta and not self.keyring.verify(envelope.frame):
            return self._receipt(envelope, False, "invalid seal")
        if self.reject_replay and not self.replay_cache.check_and_store(envelope, now=now):
            return self._receipt(envelope, False, "replay")
        route_frame = strip_zpls_seal(envelope.frame) if SEAL_KEY in envelope.frame.delta else envelope.frame
        event = self.mesh.route(route_frame, sender=None)
        return FabricReceipt(
            accepted=event.accepted,
            reason=event.reason,
            source=envelope.source,
            destination=envelope.destination,
            trace_id=envelope.trace_id,
            frame_hash=semantic_hash(envelope.frame),
            receiver=event.receiver,
        )

    @staticmethod
    def _receipt(envelope: FabricEnvelope, accepted: bool, reason: str) -> FabricReceipt:
        return FabricReceipt(
            accepted=accepted,
            reason=reason,
            source=envelope.source,
            destination=envelope.destination,
            trace_id=envelope.trace_id,
            frame_hash=semantic_hash(envelope.frame),
        )


def negotiate_capabilities(local: ZplsNodeDescriptor, remote: ZplsNodeDescriptor) -> CapabilityAgreement:
    protocol = _first_common(local.protocol_versions, remote.protocol_versions, "protocol version")
    transport = _first_common(local.transports, remote.transports, "transport")
    operations = _intersection(local.operations, remote.operations)
    features = _intersection(local.features, remote.features)
    seal_key_ids = _intersection(local.seal_key_ids, remote.seal_key_ids)
    if not operations:
        raise ValueError("no common ZPL-S operations")
    return CapabilityAgreement(protocol, transport, operations, features, seal_key_ids)


def parse_node_descriptor(raw: str) -> ZplsNodeDescriptor:
    obj = _json_object(raw, "node descriptor")
    return ZplsNodeDescriptor(
        node_id=_required_text(obj, "node_id"),
        endpoint=_required_text(obj, "endpoint"),
        roles=tuple(_string_list(obj, "roles")),
        protocol_versions=tuple(_string_list(obj, "protocol_versions")),
        transports=tuple(_string_list(obj, "transports")),
        features=tuple(_string_list(obj, "features")),
        operations=tuple(_string_list(obj, "operations")),
        seal_key_ids=tuple(_string_list(obj, "seal_key_ids")),
    )


def parse_fabric_envelope(raw: str) -> FabricEnvelope:
    obj = _json_object(raw, "fabric envelope")
    frame_hash = _required_text(obj, "frame_hash")
    frame = parse_zpls(_required_text(obj, "frame"))
    actual_hash = semantic_hash(frame)
    if frame_hash != actual_hash:
        raise ValueError(f"fabric frame_hash mismatch: {frame_hash} != {actual_hash}")
    return FabricEnvelope(
        source=_required_text(obj, "source"),
        destination=_required_text(obj, "destination"),
        frame=frame,
        trace_id=_required_text(obj, "trace_id"),
        created_at=_required_int(obj, "created_at"),
        ttl=_required_int(obj, "ttl"),
        fabric_version=_required_text(obj, "fabric_version"),
        content_type=_required_text(obj, "content_type"),
        route=tuple(_string_list(obj, "route")),
    )


def _json_object(raw: str, label: str) -> dict[str, Any]:
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid ZPL-S {label} JSON") from exc
    if not isinstance(obj, dict):
        raise ValueError(f"ZPL-S {label} must be a JSON object")
    return obj


def _required_text(obj: Mapping[str, Any], key: str) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"missing or invalid text field: {key}")
    return value


def _required_int(obj: Mapping[str, Any], key: str) -> int:
    value = obj.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"missing or invalid integer field: {key}")
    return value


def _string_list(obj: Mapping[str, Any], key: str) -> list[str]:
    value = obj.get(key)
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise ValueError(f"missing or invalid string list field: {key}")
    return value


def _first_common(local: Sequence[str], remote: Sequence[str], label: str) -> str:
    remote_set = set(remote)
    for item in local:
        if item in remote_set:
            return item
    raise ValueError(f"no common ZPL-S {label}")


def _intersection(left: Sequence[str], right: Sequence[str]) -> tuple[str, ...]:
    right_set = set(right)
    return tuple(item for item in left if item in right_set)


def _canonical_tokens(values: Sequence[str], label: str) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise ValueError(f"ZPL-S {label} values must be a sequence")
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        _validate_token(value, label)
        if value in seen:
            raise ValueError(f"duplicate ZPL-S {label}: {value}")
        seen.add(value)
        out.append(value)
    if not out:
        raise ValueError(f"ZPL-S {label} values must not be empty")
    return tuple(sorted(out))


def _validate_token(value: str, label: str) -> None:
    if not isinstance(value, str) or not value or len(value.encode("utf-8")) > 128:
        raise ValueError(f"invalid ZPL-S fabric {label}: {value}")
    if any(ch.isspace() for ch in value):
        raise ValueError(f"invalid ZPL-S fabric {label}: {value}")


def _validate_endpoint(endpoint: str) -> None:
    parsed = urlparse(endpoint)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"invalid ZPL-S endpoint: {endpoint}")
