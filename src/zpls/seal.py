from __future__ import annotations

import hmac
import re
from dataclasses import dataclass
from hashlib import sha256
from typing import Mapping

from zpls.frame import ZplsFrame, canonical_json

SEAL_KEY = "seal"
SEAL_ALG = "hmac-sha256"
SEAL_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")


@dataclass(frozen=True)
class ZplsSeal:
    alg: str
    key_id: str
    mac: str

    def token(self) -> str:
        return f"{self.alg}.{self.key_id}.{self.mac}"


def has_zpls_seal(frame: ZplsFrame) -> bool:
    return SEAL_KEY in frame.delta


def strip_zpls_seal(frame: ZplsFrame) -> ZplsFrame:
    if SEAL_KEY not in frame.delta:
        return frame
    delta = dict(frame.delta)
    delta.pop(SEAL_KEY, None)
    return ZplsFrame(frame.version, frame.agent, frame.state_hash, frame.op, frame.target, frame.confidence, frame.risk, delta)


def zpls_seal_material(frame: ZplsFrame) -> str:
    return canonical_json(strip_zpls_seal(frame).canonical())


def zpls_seal_digest(frame: ZplsFrame, key: str | bytes) -> str:
    return hmac.new(_key_bytes(key), zpls_seal_material(frame).encode("utf-8"), sha256).hexdigest()


def seal_zpls_frame(
    frame: ZplsFrame,
    key: str | bytes,
    *,
    key_id: str = "mesh",
    replace: bool = False,
) -> ZplsFrame:
    _validate_key_id(key_id)
    if SEAL_KEY in frame.delta and not replace:
        raise ValueError("ZPL-S frame is already sealed")
    base = strip_zpls_seal(frame) if replace else frame
    seal = ZplsSeal(SEAL_ALG, key_id, zpls_seal_digest(base, key))
    delta = dict(base.delta)
    delta[SEAL_KEY] = seal.token()
    return ZplsFrame(base.version, base.agent, base.state_hash, base.op, base.target, base.confidence, base.risk, delta)


def parse_zpls_seal_token(token: str) -> ZplsSeal:
    if not isinstance(token, str):
        raise ValueError("ZPL-S seal must be a scalar token")
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("invalid ZPL-S seal token")
    alg, key_id, mac = parts
    if alg != SEAL_ALG:
        raise ValueError(f"unsupported ZPL-S seal algorithm: {alg}")
    _validate_key_id(key_id)
    if not re.fullmatch(r"[0-9a-f]{64}", mac):
        raise ValueError("invalid ZPL-S seal mac")
    return ZplsSeal(alg, key_id, mac)


def zpls_frame_seal(frame: ZplsFrame) -> ZplsSeal:
    raw = frame.delta.get(SEAL_KEY)
    if raw is None:
        raise ValueError("ZPL-S frame is not sealed")
    return parse_zpls_seal_token(raw)


def verify_zpls_seal(frame: ZplsFrame, keys: str | bytes | Mapping[str, str | bytes]) -> bool:
    try:
        seal = zpls_frame_seal(frame)
    except ValueError:
        return False
    key = _resolve_key(seal, keys)
    if key is None:
        return False
    expected = zpls_seal_digest(frame, key)
    return hmac.compare_digest(seal.mac, expected)


def _resolve_key(seal: ZplsSeal, keys: str | bytes | Mapping[str, str | bytes]) -> str | bytes | None:
    if isinstance(keys, Mapping):
        return keys.get(seal.key_id)
    return keys


def _key_bytes(key: str | bytes) -> bytes:
    if isinstance(key, bytes):
        if not key:
            raise ValueError("ZPL-S seal key must not be empty")
        return key
    if isinstance(key, str):
        if not key:
            raise ValueError("ZPL-S seal key must not be empty")
        return key.encode("utf-8")
    raise ValueError("ZPL-S seal key must be text or bytes")


def _validate_key_id(key_id: str) -> None:
    if not isinstance(key_id, str) or not SEAL_RE.fullmatch(key_id):
        raise ValueError(f"invalid ZPL-S seal key id: {key_id}")
