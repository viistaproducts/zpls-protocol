from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Sequence

from zpls.frame import RISKS, ZPLS_VERSION, ZplsFrame, canonical_json

Q_STATE_KEY = "q"
Q_LAYER_KEY = "ql"
ENTANGLE_KEY = "ent"
OBSERVER_KEY = "qobs"
PICK_KEY = "qpick"
LAYER_PICK_KEY = "qlpick"
Q_GATE_KEY = "gate"
Q_COHERENCE_KEY = "qcoh"

REF_RE = re.compile(r"^[A-Za-z0-9_.+/=-]{1,128}$")
EDGE_REF_RE = re.compile(r"^[A-Za-z0-9_.+/-]{1,128}$")
Q_NUMBER_RE = re.compile(r"^[+-]?(?:\d+(?:\.\d{1,4})?|\.\d{1,4})$")
Q_SCALE = 10_000
Q_QUANTUM = Decimal("0.0001")
Q_PHASE_PERIOD = Q_SCALE * 2


@dataclass(frozen=True)
class QBranch:
    ref: str
    weight: float
    phase: float = 0.0

    def __post_init__(self) -> None:
        _validate_ref(self.ref, "Q branch ref")
        _validate_number(self.weight, "Q branch weight")
        _validate_number(self.phase, "Q branch phase")
        if not 0.0 < self.weight <= 1.0:
            raise ValueError("Q branch weight must be in (0, 1]")
        if not -1.0 <= self.phase <= 1.0:
            raise ValueError("Q branch phase must be between -1 and 1")

    def canonical(self) -> dict[str, str | float]:
        return {
            "ref": self.ref,
            "weight": _canonical_number(self.weight),
            "phase": _canonical_number(self.phase),
        }


@dataclass(frozen=True)
class QLayer:
    ref: str
    weight: float
    phase: float = 0.0

    def __post_init__(self) -> None:
        _validate_ref(self.ref, "Q layer ref")
        _validate_number(self.weight, "Q layer weight")
        _validate_number(self.phase, "Q layer phase")
        if not 0.0 < self.weight <= 1.0:
            raise ValueError("Q layer weight must be in (0, 1]")
        if not -1.0 <= self.phase <= 1.0:
            raise ValueError("Q layer phase must be between -1 and 1")

    def canonical(self) -> dict[str, str | float]:
        return {
            "ref": self.ref,
            "weight": _canonical_number(self.weight),
            "phase": _canonical_number(self.phase),
        }


@dataclass(frozen=True)
class QEdge:
    src: str
    dst: str
    gain: float
    phase: float = 0.0

    def __post_init__(self) -> None:
        _validate_edge_ref(self.src, "Q edge source")
        _validate_edge_ref(self.dst, "Q edge destination")
        _validate_number(self.gain, "Q edge gain")
        _validate_number(self.phase, "Q edge phase")
        if not 0.0 < self.gain <= 1.0:
            raise ValueError("Q edge gain must be in (0, 1]")
        if not -1.0 <= self.phase <= 1.0:
            raise ValueError("Q edge phase must be between -1 and 1")

    def canonical(self) -> dict[str, str | float]:
        return {
            "src": self.src,
            "dst": self.dst,
            "gain": _canonical_number(self.gain),
            "phase": _canonical_number(self.phase),
        }


def format_qbranches(branches: Sequence[QBranch]) -> list[str]:
    canonical = _canonical_branches(branches)
    return [_format_branch(branch) for branch in canonical]


def parse_qbranches(tokens: Sequence[str]) -> tuple[QBranch, ...]:
    if isinstance(tokens, (str, bytes)) or not isinstance(tokens, Sequence):
        raise ValueError("Q branches must be a sequence of branch tokens")
    branches = tuple(_parse_branch(token) for token in tokens)
    return _canonical_branches(branches)


def format_qlayers(layers: Sequence[QLayer]) -> list[str]:
    canonical = _canonical_layers(layers)
    return [_format_layer(layer) for layer in canonical]


def parse_qlayers(tokens: Sequence[str]) -> tuple[QLayer, ...]:
    if isinstance(tokens, (str, bytes)) or not isinstance(tokens, Sequence):
        raise ValueError("Q layers must be a sequence of layer tokens")
    layers = tuple(_parse_layer(token) for token in tokens)
    return _canonical_layers(layers)


def format_qedges(edges: Sequence[QEdge]) -> list[str]:
    canonical = _canonical_edges(edges)
    return [_format_edge(edge) for edge in canonical]


def parse_qedges(tokens: Sequence[str]) -> tuple[QEdge, ...]:
    if isinstance(tokens, (str, bytes)) or not isinstance(tokens, Sequence):
        raise ValueError("Q edges must be a sequence of edge tokens")
    return _canonical_edges(tuple(_parse_edge(token) for token in tokens))


def apply_qgate(branches: Sequence[QBranch], edges: Sequence[QEdge]) -> tuple[QBranch, ...]:
    canonical_branches = _canonical_branches(branches)
    canonical_edges = _canonical_edges(edges)
    branch_by_ref = {branch.ref: branch for branch in canonical_branches}
    contributions: dict[str, list[tuple[int, int]]] = {}
    for edge in canonical_edges:
        source = branch_by_ref.get(edge.src)
        if source is None:
            continue
        mass = _mul_units(_to_units(source.weight, "Q branch weight"), _to_units(edge.gain, "Q edge gain"))
        if mass == 0:
            continue
        phase = _wrap_phase_units(_to_units(source.phase, "Q branch phase") + _to_units(edge.phase, "Q edge phase"))
        contributions.setdefault(edge.dst, []).append((mass, phase))
    if not contributions:
        raise ValueError("Q gate produced no reachable output states")
    raw: list[tuple[str, int, int]] = []
    for dst in sorted(contributions):
        mass, phase = _interfere(contributions[dst])
        if mass > 0:
            raw.append((dst, mass, phase))
    if not raw:
        raise ValueError("Q gate cancelled all output states")
    weights = _normalize_raw_weights([(dst, mass) for dst, mass, _phase in raw])
    return tuple(QBranch(dst, _from_units(weights[dst]), _from_units(phase)) for dst, _mass, phase in raw)


def apply_qgate_to_frame(frame: ZplsFrame, edges: Sequence[QEdge], *, keep_gate: bool = False) -> ZplsFrame:
    raw_branches = frame.delta.get(Q_STATE_KEY)
    if not isinstance(raw_branches, list):
        raise ValueError("ZPL-S frame does not carry a Q superposition")
    next_branches = apply_qgate(parse_qbranches(raw_branches), edges)
    delta = dict(frame.delta)
    delta[Q_STATE_KEY] = format_qbranches(next_branches)
    if keep_gate:
        if Q_GATE_KEY in delta:
            raise ValueError("Q gate key already exists")
        delta[Q_GATE_KEY] = format_qedges(edges)
    return ZplsFrame(frame.version, frame.agent, frame.state_hash, frame.op, frame.target, frame.confidence, frame.risk, delta)


def qfield_tensor(branches: Sequence[QBranch], layers: Sequence[QLayer]) -> tuple[QBranch, ...]:
    raw = _qfield_tensor_units(branches, layers)
    weights = _normalize_raw_weights([(ref, mass) for ref, mass, _phase in raw])
    return tuple(QBranch(ref, _from_units(weights[ref]), _from_units(phase)) for ref, _mass, phase in raw)


def qfield_coherence(branches: Sequence[QBranch], layers: Sequence[QLayer]) -> float:
    raw = _qfield_tensor_units(branches, layers)
    weights = _normalize_raw_weights([(ref, mass) for ref, mass, _phase in raw])
    normalized = [(ref, weights[ref], phase) for ref, _mass, phase in raw]
    return _from_units(_qfield_coherence_units(normalized))


def qfield_to_frame(frame: ZplsFrame, *, keep_layers: bool = False) -> ZplsFrame:
    branches = _frame_qbranches(frame)
    layers = _frame_qlayers(frame)
    delta = dict(frame.delta)
    delta[Q_STATE_KEY] = format_qbranches(qfield_tensor(branches, layers))
    delta[Q_COHERENCE_KEY] = qfield_coherence(branches, layers)
    if not keep_layers:
        delta.pop(Q_LAYER_KEY, None)
    return ZplsFrame(frame.version, frame.agent, frame.state_hash, frame.op, frame.target, frame.confidence, frame.risk, delta)


def with_qstate(
    frame: ZplsFrame,
    branches: Sequence[QBranch],
    *,
    layers: Sequence[QLayer] = (),
    entangled: Sequence[str] = (),
    observer: str | None = None,
) -> ZplsFrame:
    delta = _apply_q_delta(frame.delta, branches, layers=layers, entangled=entangled, observer=observer)
    return ZplsFrame(frame.version, frame.agent, frame.state_hash, frame.op, frame.target, frame.confidence, frame.risk, delta)


def make_qframe(
    *,
    agent: str,
    state_hash: str,
    op: str,
    target: str,
    confidence: float,
    risk: str,
    branches: Sequence[QBranch],
    delta: dict[str, object] | None = None,
    layers: Sequence[QLayer] = (),
    entangled: Sequence[str] = (),
    observer: str | None = None,
) -> ZplsFrame:
    if risk not in RISKS:
        raise ValueError(f"unsupported ZPL-S risk: {risk}")
    q_delta = _apply_q_delta(delta or {}, branches, layers=layers, entangled=entangled, observer=observer)
    return ZplsFrame(ZPLS_VERSION, agent, state_hash, op, target, confidence, risk, q_delta)


def observe_qstate(frame: ZplsFrame, observer: str) -> ZplsFrame:
    _validate_ref(observer, "Q observer")
    raw_branches = frame.delta.get(Q_STATE_KEY)
    if not isinstance(raw_branches, list):
        raise ValueError("ZPL-S frame does not carry a Q superposition")
    branches = parse_qbranches(raw_branches)
    picked = _pick_branch(frame, observer, branches)
    delta = dict(frame.delta)
    delta.pop(Q_STATE_KEY, None)
    delta[OBSERVER_KEY] = observer
    delta[PICK_KEY] = picked.ref
    if _canonical_number(picked.phase) != 0.0:
        delta["qphase"] = _canonical_number(picked.phase)
    raw_layers = frame.delta.get(Q_LAYER_KEY)
    if raw_layers is not None:
        if not isinstance(raw_layers, list):
            raise ValueError("Q layers must be encoded as a list")
        picked_layer = _pick_layer(frame, observer, parse_qlayers(raw_layers))
        delta.pop(Q_LAYER_KEY, None)
        delta[LAYER_PICK_KEY] = picked_layer.ref
        if _canonical_number(picked_layer.phase) != 0.0:
            delta["qlphase"] = _canonical_number(picked_layer.phase)
    return ZplsFrame(frame.version, frame.agent, frame.state_hash, frame.op, frame.target, frame.confidence, frame.risk, delta)


def q_observation_material(frame: ZplsFrame, observer: str) -> str:
    _validate_ref(observer, "Q observer")
    return canonical_json({"frame": frame.canonical(), "observer": observer})


def q_observation_bucket(frame: ZplsFrame, observer: str) -> int:
    material = q_observation_material(frame, observer)
    digest64 = int(hashlib.sha256(material.encode("utf-8")).hexdigest()[:16], 16)
    return (digest64 * Q_SCALE) // 16**16


def q_layer_observation_material(frame: ZplsFrame, observer: str) -> str:
    _validate_ref(observer, "Q observer")
    return canonical_json({"axis": "layer", "frame": frame.canonical(), "observer": observer})


def q_layer_observation_bucket(frame: ZplsFrame, observer: str) -> int:
    material = q_layer_observation_material(frame, observer)
    digest64 = int(hashlib.sha256(material.encode("utf-8")).hexdigest()[:16], 16)
    return (digest64 * Q_SCALE) // 16**16


def explain_qstate(frame: ZplsFrame) -> str:
    if Q_STATE_KEY in frame.delta:
        raw_branches = frame.delta[Q_STATE_KEY]
        if not isinstance(raw_branches, list):
            raise ValueError("Q state must be encoded as a list")
        branches = parse_qbranches(raw_branches)
        refs = ", ".join(f"{branch.ref}@{_format_number(branch.weight)}" for branch in branches)
        if Q_LAYER_KEY in frame.delta:
            layers = _frame_qlayers(frame)
            layer_refs = ", ".join(f"{layer.ref}@{_format_number(layer.weight)}" for layer in layers)
            coherence = qfield_coherence(branches, layers)
            return f"unobserved Q-field over states {refs}; layers={layer_refs}; coherence={_format_number(coherence)}"
        entangled = frame.delta.get(ENTANGLE_KEY, [])
        if entangled:
            return f"unobserved Q-state over {refs}; entangled={canonical_json(entangled)}"
        return f"unobserved Q-state over {refs}"
    if PICK_KEY in frame.delta and LAYER_PICK_KEY in frame.delta:
        observer = frame.delta.get(OBSERVER_KEY, "unknown")
        return f"observed Q-field collapsed to {frame.delta[LAYER_PICK_KEY]}/{frame.delta[PICK_KEY]} by {observer}"
    if PICK_KEY in frame.delta:
        observer = frame.delta.get(OBSERVER_KEY, "unknown")
        return f"observed Q-state collapsed to {frame.delta[PICK_KEY]} by {observer}"
    return "frame carries no Q-state"


def _apply_q_delta(
    delta: dict[str, object],
    branches: Sequence[QBranch],
    *,
    layers: Sequence[QLayer],
    entangled: Sequence[str],
    observer: str | None,
) -> dict[str, object]:
    out = dict(delta)
    for key in [
        Q_STATE_KEY,
        Q_LAYER_KEY,
        ENTANGLE_KEY,
        OBSERVER_KEY,
        PICK_KEY,
        LAYER_PICK_KEY,
        Q_GATE_KEY,
        Q_COHERENCE_KEY,
        "qphase",
        "qlphase",
    ]:
        if key in out:
            raise ValueError(f"Q delta key already exists: {key}")
    out[Q_STATE_KEY] = format_qbranches(branches)
    if layers:
        out[Q_LAYER_KEY] = format_qlayers(layers)
    if entangled:
        out[ENTANGLE_KEY] = _canonical_refs(entangled)
    if observer is not None:
        _validate_ref(observer, "Q observer")
        out[OBSERVER_KEY] = observer
    return out


def _canonical_branches(branches: Sequence[QBranch]) -> tuple[QBranch, ...]:
    if not branches:
        raise ValueError("Q superposition requires at least one branch")
    seen: set[str] = set()
    canonical: list[QBranch] = []
    for branch in branches:
        if not isinstance(branch, QBranch):
            raise ValueError("Q branches must be QBranch values")
        if branch.ref in seen:
            raise ValueError(f"duplicate Q branch ref: {branch.ref}")
        seen.add(branch.ref)
        canonical.append(
            QBranch(
                branch.ref,
                _from_units(_to_units(branch.weight, "Q branch weight")),
                _from_units(_to_units(branch.phase, "Q branch phase")),
            )
        )
    total = sum(_to_units(branch.weight, "Q branch weight") for branch in canonical)
    if total != Q_SCALE:
        raise ValueError("Q branch weights must sum to 1.0")
    return tuple(sorted(canonical, key=lambda branch: branch.ref))


def _canonical_layers(layers: Sequence[QLayer]) -> tuple[QLayer, ...]:
    if not layers:
        raise ValueError("Q field requires at least one layer")
    seen: set[str] = set()
    canonical: list[QLayer] = []
    for layer in layers:
        if not isinstance(layer, QLayer):
            raise ValueError("Q layers must be QLayer values")
        if layer.ref in seen:
            raise ValueError(f"duplicate Q layer ref: {layer.ref}")
        seen.add(layer.ref)
        canonical.append(
            QLayer(
                layer.ref,
                _from_units(_to_units(layer.weight, "Q layer weight")),
                _from_units(_to_units(layer.phase, "Q layer phase")),
            )
        )
    total = sum(_to_units(layer.weight, "Q layer weight") for layer in canonical)
    if total != Q_SCALE:
        raise ValueError("Q layer weights must sum to 1.0")
    return tuple(sorted(canonical, key=lambda layer: layer.ref))


def _parse_branch(token: str) -> QBranch:
    if not isinstance(token, str):
        raise ValueError("Q branch token must be text")
    if "@" not in token:
        raise ValueError(f"invalid Q branch token: {token}")
    ref, raw_tail = token.split("@", 1)
    if "/" in raw_tail:
        raw_weight, raw_phase = raw_tail.split("/", 1)
    else:
        raw_weight, raw_phase = raw_tail, "0"
    _validate_ref(ref, "Q branch ref")
    weight = _parse_number(raw_weight, "Q branch weight")
    phase = _parse_number(raw_phase, "Q branch phase")
    return QBranch(ref, weight, phase)


def _parse_layer(token: str) -> QLayer:
    if not isinstance(token, str):
        raise ValueError("Q layer token must be text")
    if "@" not in token:
        raise ValueError(f"invalid Q layer token: {token}")
    ref, raw_tail = token.split("@", 1)
    if "/" in raw_tail:
        raw_weight, raw_phase = raw_tail.split("/", 1)
    else:
        raw_weight, raw_phase = raw_tail, "0"
    _validate_ref(ref, "Q layer ref")
    weight = _parse_number(raw_weight, "Q layer weight")
    phase = _parse_number(raw_phase, "Q layer phase")
    return QLayer(ref, weight, phase)


def _canonical_edges(edges: Sequence[QEdge]) -> tuple[QEdge, ...]:
    if not edges:
        raise ValueError("Q gate requires at least one edge")
    canonical: list[QEdge] = []
    seen: set[tuple[str, str]] = set()
    for edge in edges:
        if not isinstance(edge, QEdge):
            raise ValueError("Q edges must be QEdge values")
        key = (edge.src, edge.dst)
        if key in seen:
            raise ValueError(f"duplicate Q edge: {edge.src}->{edge.dst}")
        seen.add(key)
        canonical.append(
            QEdge(
                edge.src,
                edge.dst,
                _from_units(_to_units(edge.gain, "Q edge gain")),
                _from_units(_to_units(edge.phase, "Q edge phase")),
            )
        )
    return tuple(sorted(canonical, key=lambda edge: (edge.src, edge.dst)))


def _parse_edge(token: str) -> QEdge:
    if not isinstance(token, str):
        raise ValueError("Q edge token must be text")
    if "=" not in token or "@" not in token:
        raise ValueError(f"invalid Q edge token: {token}")
    src, raw_tail = token.split("=", 1)
    dst, raw_gain_phase = raw_tail.split("@", 1)
    if "/" in raw_gain_phase:
        raw_gain, raw_phase = raw_gain_phase.split("/", 1)
    else:
        raw_gain, raw_phase = raw_gain_phase, "0"
    _validate_edge_ref(src, "Q edge source")
    _validate_edge_ref(dst, "Q edge destination")
    return QEdge(src, dst, _parse_number(raw_gain, "Q edge gain"), _parse_number(raw_phase, "Q edge phase"))


def _format_branch(branch: QBranch) -> str:
    out = f"{branch.ref}@{_format_number(branch.weight)}"
    if _canonical_number(branch.phase) != 0.0:
        out += f"/{_format_number(branch.phase)}"
    return out


def _format_layer(layer: QLayer) -> str:
    out = f"{layer.ref}@{_format_number(layer.weight)}"
    if _canonical_number(layer.phase) != 0.0:
        out += f"/{_format_number(layer.phase)}"
    return out


def _format_edge(edge: QEdge) -> str:
    out = f"{edge.src}={edge.dst}@{_format_number(edge.gain)}"
    if _canonical_number(edge.phase) != 0.0:
        out += f"/{_format_number(edge.phase)}"
    return out


def _pick_branch(frame: ZplsFrame, observer: str, branches: Sequence[QBranch]) -> QBranch:
    bucket = q_observation_bucket(frame, observer)
    cursor = 0
    for branch in branches:
        cursor += _to_units(branch.weight, "Q branch weight")
        if bucket < cursor:
            return branch
    return branches[-1]


def _pick_layer(frame: ZplsFrame, observer: str, layers: Sequence[QLayer]) -> QLayer:
    bucket = q_layer_observation_bucket(frame, observer)
    cursor = 0
    for layer in layers:
        cursor += _to_units(layer.weight, "Q layer weight")
        if bucket < cursor:
            return layer
    return layers[-1]


def _frame_qbranches(frame: ZplsFrame) -> tuple[QBranch, ...]:
    raw_branches = frame.delta.get(Q_STATE_KEY)
    if not isinstance(raw_branches, list):
        raise ValueError("ZPL-S frame does not carry a Q superposition")
    return parse_qbranches(raw_branches)


def _frame_qlayers(frame: ZplsFrame) -> tuple[QLayer, ...]:
    raw_layers = frame.delta.get(Q_LAYER_KEY)
    if not isinstance(raw_layers, list):
        raise ValueError("ZPL-S frame does not carry Q layers")
    return parse_qlayers(raw_layers)


def _qfield_tensor_units(branches: Sequence[QBranch], layers: Sequence[QLayer]) -> list[tuple[str, int, int]]:
    canonical_branches = _canonical_branches(branches)
    canonical_layers = _canonical_layers(layers)
    raw: list[tuple[str, int, int]] = []
    for layer in canonical_layers:
        layer_weight = _to_units(layer.weight, "Q layer weight")
        layer_phase = _to_units(layer.phase, "Q layer phase")
        for branch in canonical_branches:
            branch_weight = _to_units(branch.weight, "Q branch weight")
            branch_phase = _to_units(branch.phase, "Q branch phase")
            mass = _mul_units(layer_weight, branch_weight)
            phase = _wrap_phase_units(layer_phase + branch_phase)
            raw.append((f"{layer.ref}/{branch.ref}", mass, phase))
    if not raw or sum(mass for _ref, mass, _phase in raw) <= 0:
        raise ValueError("Q field tensor produced no mass")
    return sorted(raw, key=lambda item: item[0])


def _qfield_coherence_units(items: Sequence[tuple[str, int, int]]) -> int:
    if len(items) < 2:
        return Q_SCALE
    numerator = 0
    denominator = 0
    for idx, (_left_ref, left_mass, left_phase) in enumerate(items):
        for _right_ref, right_mass, right_phase in items[idx + 1 :]:
            pair_mass = _mul_units(left_mass, right_mass)
            if pair_mass == 0:
                continue
            distance = _phase_distance(left_phase, right_phase)
            coherence = Q_SCALE - (2 * distance)
            numerator += pair_mass * coherence
            denominator += pair_mass
    if denominator == 0:
        return Q_SCALE
    return _round_div(numerator, denominator)


def _canonical_refs(refs: Sequence[str]) -> list[str]:
    if isinstance(refs, (str, bytes)) or not isinstance(refs, Sequence):
        raise ValueError("Q entanglement refs must be a sequence")
    out = []
    seen: set[str] = set()
    for ref in refs:
        _validate_ref(ref, "Q entanglement ref")
        if ref in seen:
            raise ValueError(f"duplicate Q entanglement ref: {ref}")
        seen.add(ref)
        out.append(ref)
    return sorted(out)


def _validate_ref(ref: str, label: str) -> None:
    if not isinstance(ref, str) or not REF_RE.fullmatch(ref):
        raise ValueError(f"invalid {label}: {ref}")


def _validate_edge_ref(ref: str, label: str) -> None:
    if not isinstance(ref, str) or not EDGE_REF_RE.fullmatch(ref):
        raise ValueError(f"invalid {label}: {ref}")


def _validate_number(value: float, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be numeric")
    if value != value or value in {float("inf"), float("-inf")}:
        raise ValueError(f"invalid {label}")


def _parse_number(raw: str, label: str) -> float:
    if not isinstance(raw, str) or not Q_NUMBER_RE.fullmatch(raw):
        raise ValueError(f"invalid {label}: {raw}")
    _parse_decimal(raw, label)
    return float(raw)


def _canonical_number(value: float) -> float:
    units = _to_units(value, "Q number")
    return _from_units(units)


def _format_number(value: float) -> str:
    sign = "-" if _to_units(value, "Q number") < 0 else ""
    units = abs(_to_units(value, "Q number"))
    whole, frac = divmod(units, Q_SCALE)
    if frac:
        frac_text = f"{frac:04d}".rstrip("0")
        out = f"{whole}.{frac_text}" if whole else f".{frac_text}"
    else:
        out = str(whole)
    out = sign + out
    if out.startswith("0."):
        out = out[1:]
    elif out.startswith("-0."):
        out = "-." + out[3:]
    return out or "0"


def _parse_decimal(raw: str, label: str) -> Decimal:
    try:
        return Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError(f"invalid {label}: {raw}") from exc


def _to_units(value: float, label: str) -> int:
    _validate_number(value, label)
    try:
        decimal = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(f"invalid {label}") from exc
    quantized = decimal.quantize(Q_QUANTUM, rounding=ROUND_HALF_UP)
    return int(quantized * Q_SCALE)


def _from_units(units: int) -> float:
    return 0.0 if units == 0 else units / Q_SCALE


def _mul_units(left: int, right: int) -> int:
    return (left * right + Q_SCALE // 2) // Q_SCALE


def _mul_signed_units(left: int, signed_right: int) -> int:
    sign = -1 if signed_right < 0 else 1
    return sign * _mul_units(left, abs(signed_right))


def _wrap_phase_units(units: int) -> int:
    shifted = (units + Q_SCALE) % Q_PHASE_PERIOD
    return shifted - Q_SCALE


def _phase_distance(left: int, right: int) -> int:
    diff = abs((left + Q_SCALE) - (right + Q_SCALE)) % Q_PHASE_PERIOD
    return min(diff, Q_PHASE_PERIOD - diff)


def _interfere(contributions: Sequence[tuple[int, int]]) -> tuple[int, int]:
    base_mass = sum(mass for mass, _phase in contributions)
    interference = 0
    for idx, (left_mass, left_phase) in enumerate(contributions):
        for right_mass, right_phase in contributions[idx + 1 :]:
            distance = _phase_distance(left_phase, right_phase)
            coherence = Q_SCALE - (2 * distance)
            interference += _mul_signed_units(2 * min(left_mass, right_mass), coherence)
    mass = max(0, base_mass + interference)
    phase_numerator = sum(mass * phase for mass, phase in contributions)
    phase = 0 if base_mass == 0 else _round_div(phase_numerator, base_mass)
    return mass, _wrap_phase_units(phase)


def _round_div(numerator: int, denominator: int) -> int:
    if denominator <= 0:
        raise ValueError("division denominator must be positive")
    sign = -1 if numerator < 0 else 1
    return sign * ((abs(numerator) + denominator // 2) // denominator)


def _normalize_raw_weights(raw: Sequence[tuple[str, int]]) -> dict[str, int]:
    total = sum(mass for _ref, mass in raw)
    if total <= 0:
        raise ValueError("Q gate output mass must be positive")
    floors: dict[str, int] = {}
    remainders: list[tuple[int, str]] = []
    allocated = 0
    for ref, mass in raw:
        scaled = mass * Q_SCALE
        units, remainder = divmod(scaled, total)
        floors[ref] = units
        remainders.append((remainder, ref))
        allocated += units
    missing = Q_SCALE - allocated
    for _remainder, ref in sorted(remainders, key=lambda item: (-item[0], item[1]))[:missing]:
        floors[ref] += 1
    return floors
