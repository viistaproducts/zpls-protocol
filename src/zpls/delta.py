from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

from zpls.frame import canonical_json

DELTA_OPS = {"+", "~", "-", "!", "?"}
DELTA_PATH_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)*$")
DELTA_INT_RE = re.compile(r"^[+-]?(?:0|[1-9][0-9]*)$")
DELTA_FLOAT_RE = re.compile(r"^[+-]?(?:(?:0|[1-9][0-9]*)?\.[0-9]{1,4})$")
DELTA_SCALAR_RE = re.compile(r"^[A-Za-z0-9_.+/@=-]{1,256}$")


class DeltaError(ValueError):
    pass


@dataclass(frozen=True)
class DeltaOp:
    op: str
    path: str
    value: Any = None

    def __post_init__(self) -> None:
        if self.op not in DELTA_OPS:
            raise DeltaError(f"unknown delta op: {self.op!r}")
        validate_delta_path(self.path)
        if self.op in {"+", "~"}:
            format_delta_value(self.value)
        elif self.value is not None:
            raise DeltaError(f"delta op {self.op!r} must not carry a value")

    def canonical(self) -> str:
        if self.op in {"+", "~"}:
            return f"{self.op}{self.path}={format_delta_value(self.value)}"
        return f"{self.op}{self.path}"


def validate_delta_path(path: str) -> str:
    if not isinstance(path, str) or not DELTA_PATH_RE.fullmatch(path):
        raise DeltaError(f"invalid delta path: {path!r}")
    return path


def parse_delta_value(raw: str) -> Any:
    if not isinstance(raw, str):
        raise DeltaError("delta value must be text")
    if raw == "":
        raise DeltaError("empty delta value")
    if raw == "true":
        return True
    if raw == "false":
        return False
    if raw == "null":
        return None
    if DELTA_INT_RE.fullmatch(raw):
        return int(raw)
    if DELTA_FLOAT_RE.fullmatch(raw):
        return float(raw)
    if not DELTA_SCALAR_RE.fullmatch(raw):
        raise DeltaError(f"invalid scalar delta value: {raw!r}")
    return raw


def format_delta_value(value: Any) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value != value or value in {float("inf"), float("-inf")}:
            raise DeltaError("invalid delta number")
        text = f"{round(value, 4):.4f}".rstrip("0").rstrip(".")
        if text == "-0":
            return "0"
        if text.startswith("0."):
            text = text[1:]
        elif text.startswith("-0."):
            text = "-." + text[3:]
        return text
    if isinstance(value, str):
        if not DELTA_SCALAR_RE.fullmatch(value):
            raise DeltaError(f"invalid scalar delta value: {value!r}")
        return value
    raise DeltaError(f"unsupported delta value type: {type(value).__name__}")


def parse_delta_op(token: str) -> DeltaOp:
    if not isinstance(token, str) or not token:
        raise DeltaError("empty delta operation")
    op = token[0]
    if op not in DELTA_OPS:
        raise DeltaError(f"unknown delta op: {op!r}")
    body = token[1:]
    if op in {"+", "~"}:
        if "=" not in body:
            raise DeltaError(f"delta op {op!r} requires '='")
        path, raw_value = body.split("=", 1)
        return DeltaOp(op, validate_delta_path(path), parse_delta_value(raw_value))
    if "=" in body:
        raise DeltaError(f"delta op {op!r} must not contain '='")
    return DeltaOp(op, validate_delta_path(body))


def parse_delta_ops(tokens: Iterable[str]) -> tuple[DeltaOp, ...]:
    return tuple(parse_delta_op(token) for token in tokens)


def canonical_delta_ops(ops: Iterable[DeltaOp]) -> list[str]:
    return [op.canonical() for op in sorted(ops, key=lambda item: (item.path, item.op, item.canonical()))]


def delta_material(ops: Iterable[DeltaOp]) -> str:
    return canonical_json(canonical_delta_ops(tuple(ops)))


def split_delta_ops(raw: str | Sequence[str]) -> list[str]:
    if isinstance(raw, str):
        source = raw.strip()
        if not source:
            return []
        return [item.strip() for item in source.split(",") if item.strip()]
    out: list[str] = []
    for item in raw:
        out.extend(split_delta_ops(item))
    return out


def apply_delta_ops(state: dict[str, Any], ops: Iterable[DeltaOp]) -> dict[str, Any]:
    if not isinstance(state, dict):
        raise DeltaError("delta state must be a JSON object")
    out = copy.deepcopy(state)
    for item in ops:
        if not isinstance(item, DeltaOp):
            raise DeltaError("delta ops must be DeltaOp values")
        if item.op == "+":
            parent, leaf = _get_parent(out, item.path, create=True)
            if leaf in parent:
                raise DeltaError(f"add target already exists: {item.path}")
            parent[leaf] = item.value
        elif item.op == "~":
            parent, leaf = _get_parent(out, item.path, create=False)
            if leaf not in parent:
                raise DeltaError(f"replace target missing: {item.path}")
            parent[leaf] = item.value
        elif item.op == "-":
            parent, leaf = _get_parent(out, item.path, create=False)
            if leaf not in parent:
                raise DeltaError(f"remove target missing: {item.path}")
            del parent[leaf]
        elif item.op == "!":
            invalid = out.setdefault("_invalid", {})
            if not isinstance(invalid, dict):
                raise DeltaError("_invalid marker is not an object")
            invalid[item.path] = True
        elif item.op == "?":
            needs = out.setdefault("_needs", {})
            if not isinstance(needs, dict):
                raise DeltaError("_needs marker is not an object")
            needs[item.path] = True
        else:
            raise DeltaError(f"unknown delta op: {item.op!r}")
    return out


def _get_parent(doc: dict[str, Any], path: str, *, create: bool) -> tuple[dict[str, Any], str]:
    parts = path.split(".")
    current: Any = doc
    for part in parts[:-1]:
        if not isinstance(current, dict):
            raise DeltaError(f"path parent is not an object: {path}")
        if part not in current:
            if not create:
                raise DeltaError(f"path parent missing: {path}")
            current[part] = {}
        if not isinstance(current[part], dict):
            raise DeltaError(f"path parent is not an object: {path}")
        current = current[part]
    if not isinstance(current, dict):
        raise DeltaError(f"path parent is not an object: {path}")
    return current, parts[-1]
