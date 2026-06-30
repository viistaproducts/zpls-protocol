from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

from zpls.frame import ZPLS_VERSION, ZplsFrame, canonical_json, parse_zpls, semantic_hash
from zpls.qlogic import Q_STATE_KEY, observe_qstate
from zpls.seal import SEAL_KEY, seal_zpls_frame, strip_zpls_seal, verify_zpls_seal

DEFAULT_ROLE_FLOW = {
    "plan": "worker",
    "task": "worker",
    "patch": "critic",
    "eval": "planner",
    "done": "synth",
    "escalate": "planner",
    "ack": "planner",
}


@dataclass
class MeshAgent:
    agent_id: str
    role: str
    inbox: list[ZplsFrame] = field(default_factory=list)


@dataclass(frozen=True)
class RouteEvent:
    frame: ZplsFrame
    frame_hash: str
    sender: str | None
    receiver: str | None
    accepted: bool
    reason: str


class ZplsMesh:
    """Minimal executable kernel for routing canonical ZPL-S frames."""

    def __init__(
        self,
        *,
        role_flow: dict[str, str] | None = None,
        seal_key: str | bytes | None = None,
        seal_key_id: str = "mesh",
        require_seal: bool = False,
    ) -> None:
        self.role_flow = dict(role_flow or DEFAULT_ROLE_FLOW)
        self.seal_key = seal_key
        self.seal_key_id = seal_key_id
        self.require_seal = require_seal
        self.agents: dict[str, MeshAgent] = {}
        self.role_routes: dict[str, str] = {}
        self.state: dict[str, Any] = {}
        self.events: list[RouteEvent] = []

    def register(self, agent_id: str, role: str | None = None) -> MeshAgent:
        _validate_ref(agent_id, "agent id")
        role = role or agent_id
        _validate_ref(role, "agent role")
        if agent_id in self.agents:
            raise ValueError(f"duplicate ZPL-S mesh agent: {agent_id}")
        agent = MeshAgent(agent_id=agent_id, role=role)
        self.agents[agent_id] = agent
        self.role_routes[role] = agent_id
        return agent

    def route(self, frame: ZplsFrame, *, sender: str | None = None, observer: str | None = None) -> RouteEvent:
        if sender is not None and sender not in self.agents:
            event = self._event(frame, sender, None, False, "unknown sender")
            self.events.append(event)
            return event
        if not self._verify_incoming(frame):
            reason = "missing seal" if self.require_seal and SEAL_KEY not in frame.delta else "invalid seal"
            event = self._event(frame, sender, None, False, reason)
            self.events.append(event)
            return event
        effective = observe_qstate(frame, observer) if observer is not None and Q_STATE_KEY in frame.delta else frame
        if observer is not None and self.seal_key is not None and SEAL_KEY in effective.delta:
            effective = self.seal_frame(strip_zpls_seal(effective))
        receiver = self._resolve_receiver(effective)
        if receiver is None:
            event = self._event(effective, sender, None, False, "no route")
            self.events.append(event)
            return event
        self.agents[receiver].inbox.append(effective)
        event = self._event(effective, sender, receiver, True, "delivered")
        self.events.append(event)
        return event

    def route_text(self, text: str, *, sender: str | None = None, observer: str | None = None) -> RouteEvent:
        return self.route(parse_zpls(text), sender=sender, observer=observer)

    def seal_frame(self, frame: ZplsFrame) -> ZplsFrame:
        if self.seal_key is None:
            raise ValueError("ZPL-S mesh has no seal key")
        return seal_zpls_frame(frame, self.seal_key, key_id=self.seal_key_id, replace=True)

    def inbox(self, agent_id: str) -> tuple[ZplsFrame, ...]:
        return tuple(self.agents[agent_id].inbox)

    def history(self) -> tuple[RouteEvent, ...]:
        return tuple(self.events)

    def put_state(self, slot: str, value: Any) -> str:
        _validate_ref(slot, "state slot")
        self.state[slot] = value
        return self.state_ref()

    def state_ref(self, *, length: int = 12) -> str:
        if isinstance(length, bool) or not isinstance(length, int) or not 1 <= length <= 64:
            raise ValueError("state ref length must be an integer from 1 to 64")
        material = canonical_json(self.state)
        return hashlib.sha256(material.encode("utf-8")).hexdigest()[:length]

    def _resolve_receiver(self, frame: ZplsFrame) -> str | None:
        direct_next = frame.delta.get("next")
        if isinstance(direct_next, str):
            if direct_next in self.agents:
                return direct_next
            if direct_next in self.role_routes:
                return self.role_routes[direct_next]
        if frame.target in self.agents:
            return frame.target
        target_role = self.role_flow.get(frame.op)
        if target_role is not None:
            return self.role_routes.get(target_role)
        return None

    def _verify_incoming(self, frame: ZplsFrame) -> bool:
        if SEAL_KEY not in frame.delta:
            return not self.require_seal
        if self.seal_key is None:
            return False
        return verify_zpls_seal(frame, {self.seal_key_id: self.seal_key})

    @staticmethod
    def _event(
        frame: ZplsFrame,
        sender: str | None,
        receiver: str | None,
        accepted: bool,
        reason: str,
    ) -> RouteEvent:
        return RouteEvent(
            frame=frame,
            frame_hash=semantic_hash(frame),
            sender=sender,
            receiver=receiver,
            accepted=accepted,
            reason=reason,
        )


def _validate_ref(value: str, label: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"invalid ZPL-S mesh {label}")
    ZplsFrame(ZPLS_VERSION, value, "mesh", "ack", "mesh", 1.0, "low", {})
