from __future__ import annotations

import json

import pytest

from zpls import (
    PeerKeyring,
    ZplsInternetGateway,
    ZplsNodeDescriptor,
    negotiate_capabilities,
    parse_fabric_envelope,
    parse_node_descriptor,
    parse_zpls,
)


def test_node_descriptor_is_canonical_discovery_document():
    descriptor = ZplsNodeDescriptor(
        "worker.example",
        "https://worker.example/.well-known/zpls.json",
        roles=("worker", "critic"),
        features=("seal", "qmatrix", "mesh"),
    )

    parsed = parse_node_descriptor(descriptor.to_json())

    assert parsed == descriptor
    assert json.loads(descriptor.to_json()) == {
        "endpoint": "https://worker.example/.well-known/zpls.json",
        "fabric_version": "F1",
        "features": ["mesh", "qmatrix", "seal"],
        "node_id": "worker.example",
        "operations": ["ack", "done", "escalate", "eval", "patch", "plan", "task"],
        "protocol_versions": ["S1"],
        "roles": ["critic", "worker"],
        "seal_key_ids": ["mesh"],
        "transports": ["https+json"],
    }


def test_capability_negotiation_intersects_internet_nodes():
    local = ZplsNodeDescriptor("worker.example", "https://worker.example/zpls", features=("mesh", "qmatrix", "seal"))
    remote = ZplsNodeDescriptor("planner.example", "https://planner.example/zpls", features=("qmatrix", "seal"))

    agreement = negotiate_capabilities(local, remote)

    assert agreement.protocol_version == "S1"
    assert agreement.transport == "https+json"
    assert agreement.features == ("qmatrix", "seal")
    assert "plan" in agreement.operations


def test_gateway_packs_signed_envelope_and_receiver_routes_it():
    planner = ZplsNodeDescriptor("planner.example", "https://planner.example/zpls", roles=("planner",))
    worker = ZplsNodeDescriptor("worker.example", "https://worker.example/zpls", roles=("worker",))
    outbox = ZplsInternetGateway(planner, require_seal=False)
    inbox = ZplsInternetGateway(worker, keyring=PeerKeyring({"mesh": "mesh-secret"}), require_seal=True)
    frame = parse_zpls("§S1 a:planner sh:8f3c op:plan t:17 c:.91 r:low Δ{next:worker}")

    envelope = outbox.pack(
        frame,
        destination="worker.example",
        trace_id="trace.demo",
        created_at=1,
        ttl=60,
        seal_key="mesh-secret",
        seal_key_id="mesh",
    )
    parsed = parse_fabric_envelope(envelope.to_json())
    receipt = inbox.receive(parsed, now=2)

    assert parsed.canonical() == envelope.canonical()
    assert receipt.accepted is True
    assert receipt.reason == "delivered"
    assert receipt.receiver == "worker"
    assert len(inbox.mesh.inbox("worker")) == 1


def test_gateway_rejects_unsigned_expired_and_wrong_destination_envelopes():
    planner = ZplsNodeDescriptor("planner.example", "https://planner.example/zpls", roles=("planner",))
    worker = ZplsNodeDescriptor("worker.example", "https://worker.example/zpls", roles=("worker",))
    outbox = ZplsInternetGateway(planner, require_seal=False)
    inbox = ZplsInternetGateway(worker, keyring=PeerKeyring({"mesh": "mesh-secret"}), require_seal=True)
    frame = parse_zpls("§S1 a:planner sh:8f3c op:plan t:17 c:.91 r:low Δ{next:worker}")

    unsigned = outbox.pack(frame, destination="worker.example", trace_id="trace.unsigned", created_at=1)
    expired = outbox.pack(
        frame,
        destination="worker.example",
        trace_id="trace.expired",
        created_at=1,
        ttl=1,
        seal_key="mesh-secret",
    )
    wrong_destination = outbox.pack(
        frame,
        destination="other.example",
        trace_id="trace.wrong",
        created_at=1,
        seal_key="mesh-secret",
    )

    assert inbox.receive(unsigned, now=2).reason == "missing seal"
    assert inbox.receive(expired, now=3).reason == "expired"
    assert inbox.receive(wrong_destination, now=2).reason == "wrong destination"


def test_parse_envelope_rejects_hash_mismatch():
    planner = ZplsNodeDescriptor("planner.example", "https://planner.example/zpls")
    outbox = ZplsInternetGateway(planner, require_seal=False)
    frame = parse_zpls("§S1 a:planner sh:8f3c op:plan t:17 c:.91 r:low Δ{next:worker}")
    envelope = json.loads(outbox.pack(frame, destination="worker.example", trace_id="trace.demo", created_at=1).to_json())
    envelope["frame_hash"] = "badbadbadbad"

    with pytest.raises(ValueError):
        parse_fabric_envelope(json.dumps(envelope))
