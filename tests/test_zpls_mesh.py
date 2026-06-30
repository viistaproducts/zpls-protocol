from __future__ import annotations

from zpls import QBranch, SEAL_KEY, ZplsFrame, ZplsMesh, make_qframe, serialize_zpls, verify_zpls_seal


def test_mesh_routes_frames_to_explicit_next_agent():
    mesh = ZplsMesh()
    mesh.register("planner")
    mesh.register("worker")
    frame = ZplsFrame("S1", "planner", "8f3c", "plan", "17", 0.9, "low", {"next": "worker"})

    event = mesh.route(frame, sender="planner")

    assert event.accepted is True
    assert event.reason == "delivered"
    assert event.receiver == "worker"
    assert mesh.inbox("worker") == (frame,)
    assert mesh.history() == (event,)


def test_mesh_observes_qstate_before_delivery():
    mesh = ZplsMesh()
    mesh.register("planner")
    mesh.register("worker")
    frame = make_qframe(
        agent="planner",
        state_hash="8f3c",
        op="plan",
        target="17",
        confidence=0.81,
        risk="med",
        branches=[QBranch("revise", 0.37, -0.5), QBranch("ship", 0.63)],
    )

    event = mesh.route(frame, sender="planner", observer="human")

    assert event.accepted is True
    assert event.receiver == "worker"
    assert serialize_zpls(mesh.inbox("worker")[0]) == (
        "§S1 a:planner sh:8f3c op:plan t:17 c:.81 r:med Δ{qobs:human,qphase:-.5,qpick:revise}"
    )


def test_mesh_state_ref_is_canonical_and_stable():
    mesh = ZplsMesh()

    first = mesh.put_state("plan.17", {"status": "open", "step": 1})
    same = mesh.state_ref()
    changed = mesh.put_state("plan.17", {"status": "done", "step": 2})

    assert first == same
    assert changed != first


def test_mesh_rejects_unknown_sender_without_delivery():
    mesh = ZplsMesh()
    mesh.register("worker")
    frame = ZplsFrame("S1", "planner", "8f3c", "plan", "17", 0.9, "low", {"next": "worker"})

    event = mesh.route(frame, sender="planner")

    assert event.accepted is False
    assert event.reason == "unknown sender"
    assert mesh.inbox("worker") == ()


def test_mesh_can_require_signed_frames():
    mesh = ZplsMesh(seal_key="mesh-secret", require_seal=True)
    mesh.register("planner")
    mesh.register("worker")
    frame = ZplsFrame("S1", "planner", "8f3c", "plan", "17", 0.9, "low", {"next": "worker"})

    unsigned = mesh.route(frame, sender="planner")
    signed = mesh.route(mesh.seal_frame(frame), sender="planner")

    assert unsigned.accepted is False
    assert unsigned.reason == "missing seal"
    assert signed.accepted is True
    assert signed.receiver == "worker"
    assert SEAL_KEY in mesh.inbox("worker")[0].delta
    assert verify_zpls_seal(mesh.inbox("worker")[0], {"mesh": "mesh-secret"}) is True


def test_mesh_reseals_observed_qstate_after_verified_input():
    mesh = ZplsMesh(seal_key="mesh-secret", require_seal=True)
    mesh.register("planner")
    mesh.register("worker")
    frame = make_qframe(
        agent="planner",
        state_hash="8f3c",
        op="plan",
        target="17",
        confidence=0.81,
        risk="med",
        branches=[QBranch("revise", 0.37, -0.5), QBranch("ship", 0.63)],
    )

    event = mesh.route(mesh.seal_frame(frame), sender="planner", observer="human")

    delivered = mesh.inbox("worker")[0]
    assert event.accepted is True
    assert "q" not in delivered.delta
    assert delivered.delta["qobs"] == "human"
    assert verify_zpls_seal(delivered, {"mesh": "mesh-secret"}) is True
