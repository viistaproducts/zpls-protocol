from __future__ import annotations

import hashlib
import json
import re
import struct
from dataclasses import dataclass, field
from typing import Any

from zpls.codec import decode_varint, encode_varint

ZPLS_VERSION = "S1"
MAGIC = b"ZPLS"

ROLES = {"planner", "worker", "critic", "synth", "synthesizer", "coder", "router"}
OPS = {"plan", "task", "ack", "eval", "patch", "done", "escalate"}
RISKS = {"low", "med", "high", "crit"}

ROLE_CODES = {
    "planner": 1,
    "worker": 2,
    "critic": 3,
    "synth": 4,
    "synthesizer": 5,
    "coder": 6,
    "router": 7,
}
OP_CODES = {name: idx for idx, name in enumerate(sorted(OPS), 1)}
RISK_CODES = {name: idx for idx, name in enumerate(["low", "med", "high", "crit"], 1)}

CODE_ROLES = {v: k for k, v in ROLE_CODES.items()}
CODE_OPS = {v: k for k, v in OP_CODES.items()}
CODE_RISKS = {v: k for k, v in RISK_CODES.items()}

HEAD_KEYS = {"a", "sh", "op", "t", "c", "r"}
HEAD_LIMITS = {"a": 64, "sh": 128, "op": 32, "t": 128, "c": 16, "r": 16}
IDENT_RE = re.compile(r"^[A-Za-z0-9_.+/@=-]+$")
CONFIDENCE_RE = re.compile(r"^(?:0(?:\.\d{1,4})?|1(?:\.0{1,4})?|\.\d{1,4})$")
DELTA_KEY_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,63}$")
INT_RE = re.compile(r"^[+-]?\d+$")
FLOAT_RE = re.compile(r"^[+-]?(?:\d+\.\d+|\d+\.|\.\d+)$")
SCALAR_TEXT_RE = re.compile(r"^[A-Za-z0-9_.+/@=-]+$")


@dataclass(frozen=True)
class ZplsFrame:
    version: str
    agent: str
    state_hash: str
    op: str
    target: str
    confidence: float
    risk: str
    delta: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.version != ZPLS_VERSION:
            raise ValueError("ZPL-S v1 only supports version S1")
        _validate_head_value("a", self.agent)
        _validate_head_value("sh", self.state_hash)
        if self.op not in OPS:
            raise ValueError(f"unsupported ZPL-S op: {self.op}")
        _validate_head_value("t", self.target)
        if isinstance(self.confidence, bool) or not isinstance(self.confidence, (int, float)):
            raise ValueError("confidence must be numeric")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        if self.risk not in RISKS:
            raise ValueError(f"unsupported ZPL-S risk: {self.risk}")
        if not isinstance(self.delta, dict):
            raise ValueError("delta must be a dict")
        _validate_delta(self.delta)

    def canonical(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "agent": self.agent,
            "state_hash": self.state_hash,
            "op": self.op,
            "target": self.target,
            "confidence": _canonical_float(self.confidence),
            "risk": self.risk,
            "delta": _canonical_value(self.delta),
        }


def parse_zpls(line: str) -> ZplsFrame:
    raw = line.strip()
    if not raw.startswith("§S1 "):
        raise ValueError("not a valid ZPL-S v1 frame")
    if raw.count("Δ{") != 1 or not raw.endswith("}"):
        raise ValueError("ZPL-S frame requires exactly one delta block")
    head, delta_raw = raw.split("Δ{", 1)
    tokens = _parse_head_tokens(head[4:].strip())
    delta = parse_delta_slots(delta_raw[:-1])
    missing = HEAD_KEYS - set(tokens)
    if missing:
        raise ValueError(f"missing ZPL-S fields: {', '.join(sorted(missing))}")
    return ZplsFrame(
        version=ZPLS_VERSION,
        agent=tokens["a"],
        state_hash=tokens["sh"],
        op=tokens["op"],
        target=tokens["t"],
        confidence=_parse_confidence(tokens["c"]),
        risk=tokens["r"],
        delta=delta,
    )


def serialize_zpls(frame: ZplsFrame) -> str:
    return (
        f"§{frame.version} "
        f"a:{frame.agent} "
        f"sh:{frame.state_hash} "
        f"op:{frame.op} "
        f"t:{frame.target} "
        f"c:{_fmt_confidence(frame.confidence)} "
        f"r:{frame.risk} "
        f"Δ{{{format_delta_slots(frame.delta)}}}"
    )


def encode_zpls_binary(frame: ZplsFrame) -> bytes:
    confidence = round(_canonical_float(frame.confidence) * 10_000)
    if not 0 <= confidence <= 10_000:
        raise ValueError("confidence out of binary range")
    return b"".join(
        [
            MAGIC,
            bytes([1]),
            _encode_symbol(frame.agent, ROLE_CODES),
            _encode_symbol(frame.op, OP_CODES),
            _encode_symbol(frame.risk, RISK_CODES),
            _encode_text(frame.state_hash),
            _encode_text(frame.target),
            struct.pack("!H", confidence),
            _encode_text(canonical_json(frame.delta)),
        ]
    )


def decode_zpls_binary(buf: bytes) -> ZplsFrame:
    if not buf.startswith(MAGIC):
        raise ValueError("not a ZPL-S binary frame")
    off = len(MAGIC)
    if off >= len(buf) or buf[off] != 1:
        raise ValueError("unsupported ZPL-S binary version")
    off += 1
    agent, off = _decode_symbol(buf, off, CODE_ROLES)
    op, off = _decode_symbol(buf, off, CODE_OPS)
    risk, off = _decode_symbol(buf, off, CODE_RISKS)
    state_hash, off = _decode_text(buf, off)
    target, off = _decode_text(buf, off)
    if off + 2 > len(buf):
        raise ValueError("incomplete ZPL-S confidence")
    confidence = struct.unpack("!H", buf[off : off + 2])[0] / 10_000
    off += 2
    delta_json, off = _decode_text(buf, off)
    if off != len(buf):
        raise ValueError("trailing bytes in ZPL-S binary frame")
    delta = _load_binary_delta(delta_json)
    if not isinstance(delta, dict):
        raise ValueError("ZPL-S binary delta must decode to a dict")
    return ZplsFrame(ZPLS_VERSION, agent, state_hash, op, target, confidence, risk, delta)


def canonical_json(value: Any) -> str:
    return json.dumps(_canonical_value(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def semantic_hash(frame: ZplsFrame, length: int = 12) -> str:
    if isinstance(length, bool) or not isinstance(length, int) or not 1 <= length <= 64:
        raise ValueError("semantic hash length must be an integer from 1 to 64")
    return hashlib.sha256(canonical_json(frame.canonical()).encode("utf-8")).hexdigest()[:length]


def explain_zpls(frame: ZplsFrame) -> str:
    return (
        f"{frame.agent} sends {frame.op} for {frame.target} "
        f"against state {frame.state_hash} with confidence {_fmt_confidence(frame.confidence)} "
        f"and {frame.risk} risk; delta={canonical_json(frame.delta)}"
    )


def parse_delta_slots(raw: str) -> dict[str, Any]:
    raw = raw.strip()
    if not raw:
        return {}
    if "Δ{" in raw:
        raise ValueError("multiple ZPL-S delta blocks are not allowed")
    out: dict[str, Any] = {}
    for part in _split_top_level(raw):
        if ":" not in part:
            raise ValueError(f"invalid ZPL-S delta slot: {part}")
        key, value = part.split(":", 1)
        key = key.strip()
        _validate_delta_key(key)
        if key in out:
            raise ValueError(f"duplicate ZPL-S delta key: {key}")
        out[key] = _parse_value(value)
    return out


def format_delta_slots(delta: dict[str, Any]) -> str:
    _validate_delta(delta)
    return ",".join(f"{key}:{_fmt_value(delta[key])}" for key in sorted(delta))


def _parse_head_tokens(head: str) -> dict[str, str]:
    if not head:
        raise ValueError("missing ZPL-S header")
    tokens: dict[str, str] = {}
    for raw_token in head.split():
        if ":" not in raw_token:
            raise ValueError(f"invalid ZPL-S header token: {raw_token}")
        key, value = raw_token.split(":", 1)
        if key not in HEAD_KEYS:
            raise ValueError(f"unknown ZPL-S header token: {key}")
        if key in tokens:
            raise ValueError(f"duplicate ZPL-S header token: {key}")
        _validate_head_value(key, value)
        tokens[key] = value
    return tokens


def _validate_head_value(key: str, value: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"empty ZPL-S header value: {key}")
    if len(value.encode("utf-8")) > HEAD_LIMITS[key]:
        raise ValueError(f"ZPL-S header value too long: {key}")
    if key == "c":
        _parse_confidence(value)
    elif not IDENT_RE.fullmatch(value):
        raise ValueError(f"invalid ZPL-S header value: {key}")


def _parse_confidence(value: str) -> float:
    if not CONFIDENCE_RE.fullmatch(value):
        raise ValueError("invalid ZPL-S confidence")
    return float(value)


def _load_binary_delta(delta_json: str) -> Any:
    try:
        return json.loads(delta_json, object_pairs_hook=_json_object_no_duplicates)
    except json.JSONDecodeError as exc:
        raise ValueError("invalid ZPL-S binary delta JSON") from exc


def _json_object_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"duplicate ZPL-S binary delta key: {key}")
        out[key] = value
    return out


def _encode_symbol(value: str, table: dict[str, int]) -> bytes:
    code = table.get(value, 0)
    if code:
        return bytes([code])
    return bytes([0]) + _encode_text(value)


def _decode_symbol(buf: bytes, off: int, table: dict[int, str]) -> tuple[str, int]:
    if off >= len(buf):
        raise ValueError("incomplete ZPL-S symbol")
    code = buf[off]
    off += 1
    if code:
        try:
            return table[code], off
        except KeyError as exc:
            raise ValueError(f"unknown ZPL-S symbol code: {code}") from exc
    return _decode_text(buf, off)


def _encode_text(value: str) -> bytes:
    raw = value.encode("utf-8")
    return encode_varint(len(raw)) + raw


def _decode_text(buf: bytes, off: int) -> tuple[str, int]:
    size, off = decode_varint(buf, off)
    end = off + size
    if end > len(buf):
        raise ValueError("incomplete ZPL-S text field")
    try:
        return buf[off:end].decode("utf-8"), end
    except UnicodeDecodeError as exc:
        raise ValueError("invalid UTF-8 in ZPL-S text field") from exc


def _split_top_level(s: str, sep: str = ",") -> list[str]:
    out, cur = [], []
    stack: list[str] = []
    pairs = {"[": "]", "{": "}", "(": ")"}
    closing = {"]", "}", ")"}
    for ch in s:
        if ch in pairs:
            stack.append(pairs[ch])
        elif ch in closing:
            if not stack or stack.pop() != ch:
                raise ValueError("unbalanced ZPL-S delta brackets")
        if ch == sep and not stack:
            item = "".join(cur).strip()
            if not item:
                raise ValueError("empty ZPL-S delta slot")
            out.append(item)
            cur = []
        else:
            cur.append(ch)
    if stack:
        raise ValueError("unbalanced ZPL-S delta brackets")
    item = "".join(cur).strip()
    if item:
        out.append(item)
    elif s.endswith(sep):
        raise ValueError("empty ZPL-S delta slot")
    return out


def _parse_value(value: str) -> Any:
    value = value.strip()
    if not value:
        raise ValueError("empty ZPL-S delta value")
    if value.startswith("{") or value.endswith("}") or "{" in value or "}" in value:
        raise ValueError("ZPL-S v1 delta values do not support nested objects")
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        items = []
        for item in _split_top_level(inner):
            if item.strip().startswith("["):
                raise ValueError("ZPL-S v1 delta lists may only contain scalars")
            parsed = _parse_value(item)
            if isinstance(parsed, list):
                raise ValueError("ZPL-S v1 delta lists may only contain scalars")
            items.append(parsed)
        return items
    if value.startswith("[") or value.endswith("]"):
        raise ValueError("unbalanced ZPL-S delta brackets")
    if value in {"true", "false"}:
        return value == "true"
    if INT_RE.fullmatch(value):
        return int(value)
    if FLOAT_RE.fullmatch(value):
        return float(value)
    _validate_scalar_text(value)
    return value


def _fmt_value(value: Any) -> str:
    if isinstance(value, list):
        return "[" + ",".join(_fmt_value(item) for item in value) + "]"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return _fmt_delta_float(value)
    _validate_scalar_text(str(value))
    return str(value)


def _fmt_delta_float(value: float) -> str:
    rounded = _canonical_float(value)
    out = f"{rounded:.4f}".rstrip("0").rstrip(".")
    if out == "0":
        return "0.0"
    if "." not in out:
        out += ".0"
    if out.startswith("0."):
        out = out[1:]
    elif out.startswith("-0."):
        out = "-." + out[3:]
    _validate_scalar_text(out)
    return out


def _fmt_confidence(value: float) -> str:
    out = f"{_canonical_float(value):.4f}".rstrip("0").rstrip(".")
    if out.startswith("0."):
        out = out[1:]
    return out or "0"


def _canonical_float(value: float) -> float:
    rounded = round(value, 4)
    return 0.0 if rounded == 0 else rounded


def _canonical_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _canonical_value(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_canonical_value(item) for item in value]
    if isinstance(value, float):
        return _canonical_float(value)
    return value


def _validate_delta(delta: dict[str, Any]) -> None:
    seen: set[str] = set()
    for key, value in delta.items():
        if not isinstance(key, str):
            raise ValueError("ZPL-S delta keys must be strings")
        _validate_delta_key(key)
        if key in seen:
            raise ValueError(f"duplicate ZPL-S delta key: {key}")
        seen.add(key)
        _validate_delta_value(value)


def _validate_delta_key(key: str) -> None:
    if not key or len(key.encode("utf-8")) > 64 or not DELTA_KEY_RE.fullmatch(key):
        raise ValueError(f"invalid ZPL-S delta key: {key}")


def _validate_delta_value(value: Any, *, in_list: bool = False) -> None:
    if isinstance(value, bool):
        return
    if isinstance(value, int):
        _validate_scalar_text(str(value))
        return
    if isinstance(value, float):
        if value != value or value in {float("inf"), float("-inf")}:
            raise ValueError("invalid ZPL-S delta number")
        _fmt_delta_float(value)
        return
    if isinstance(value, str):
        _validate_scalar_text(value)
        return
    if isinstance(value, list) and not in_list:
        for item in value:
            _validate_delta_value(item, in_list=True)
        return
    if isinstance(value, dict):
        raise ValueError("ZPL-S v1 delta values do not support nested objects")
    raise ValueError("ZPL-S v1 delta values must be scalars or lists of scalars")


def _validate_scalar_text(value: str) -> None:
    if not value or len(value.encode("utf-8")) > 256 or not SCALAR_TEXT_RE.fullmatch(value):
        raise ValueError(f"invalid ZPL-S scalar text: {value}")
