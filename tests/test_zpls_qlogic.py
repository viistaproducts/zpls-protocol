from __future__ import annotations

import pytest

from zpls import (
    QBranch,
    QEdge,
    QLayer,
    Q_SCALE,
    apply_qgate,
    apply_qgate_to_frame,
    decode_zpls_binary,
    encode_zpls_binary,
    explain_qstate,
    format_qedges,
    format_qbranches,
    format_qlayers,
    make_qframe,
    observe_qstate,
    parse_qedges,
    parse_qbranches,
    parse_qlayers,
    q_layer_observation_bucket,
    q_layer_observation_material,
    q_observation_bucket,
    q_observation_material,
    qfield_coherence,
    qfield_tensor,
    qfield_to_frame,
    semantic_hash,
    serialize_zpls,
    with_qstate,
    ZplsFrame,
)


def test_qbranches_are_canonical_compact_superposition_tokens():
    branches = [QBranch("revise", 0.4, 0.25), QBranch("ship", 0.6)]

    tokens = format_qbranches(branches)

    assert tokens == ["revise@.4/.25", "ship@.6"]
    assert parse_qbranches(tokens) == (QBranch("revise", 0.4, 0.25), QBranch("ship", 0.6))


def test_qbranches_use_fixed_q4_units_not_float_cursor_semantics():
    branches = [QBranch("a", 0.1), QBranch("b", 0.2), QBranch("c", 0.7)]

    assert Q_SCALE == 10_000
    assert format_qbranches(branches) == ["a@.1", "b@.2", "c@.7"]


def test_qedges_are_canonical_sparse_matrix_tokens():
    edges = [QEdge("u0/a", "u1/y", 0.4, -0.25), QEdge("u0/a", "u1/x", 0.6)]

    tokens = format_qedges(edges)

    assert tokens == ["u0/a=u1/x@.6", "u0/a=u1/y@.4/-.25"]
    assert parse_qedges(tokens) == (QEdge("u0/a", "u1/x", 0.6), QEdge("u0/a", "u1/y", 0.4, -0.25))


def test_qgate_projects_parallel_layers_with_interference():
    branches = [QBranch("u0/a", 0.5, 0.0), QBranch("u0/b", 0.5, 0.5)]
    edges = [
        QEdge("u0/a", "u1/x", 0.8, 0.0),
        QEdge("u0/b", "u1/x", 0.8, 0.0),
        QEdge("u0/a", "u1/y", 0.2, 0.0),
        QEdge("u0/b", "u1/y", 0.2, -0.5),
    ]

    projected = apply_qgate(branches, edges)

    assert format_qbranches(projected) == ["u1/x@.6667/.25", "u1/y@.3333"]


def test_qgate_can_be_carried_as_compact_delta_matrix():
    frame = make_qframe(
        agent="planner",
        state_hash="8f3c",
        op="plan",
        target="17",
        confidence=0.81,
        risk="med",
        branches=[QBranch("u0/a", 0.5), QBranch("u0/b", 0.5, 0.5)],
    )
    edges = [QEdge("u0/a", "u1/x", 1.0), QEdge("u0/b", "u1/y", 1.0, -0.5)]

    projected = apply_qgate_to_frame(frame, edges, keep_gate=True)

    assert serialize_zpls(projected) == (
        "§S1 a:planner sh:8f3c op:plan t:17 c:.81 r:med "
        "Δ{gate:[u0/a=u1/x@1,u0/b=u1/y@1/-.5],q:[u1/x@.5,u1/y@.5]}"
    )


def test_qframe_encodes_superposition_entanglement_and_observer_in_delta():
    frame = make_qframe(
        agent="planner",
        state_hash="8f3c",
        op="plan",
        target="17",
        confidence=0.81,
        risk="med",
        branches=[QBranch("revise", 0.37, -0.5), QBranch("ship", 0.63)],
        delta={"next": "critic"},
        entangled=["critic.17", "coder.17"],
        observer="human",
    )

    assert serialize_zpls(frame) == (
        "§S1 a:planner sh:8f3c op:plan t:17 c:.81 r:med "
        "Δ{ent:[coder.17,critic.17],next:critic,q:[revise@.37/-.5,ship@.63],qobs:human}"
    )
    assert decode_zpls_binary(encode_zpls_binary(frame)).canonical() == frame.canonical()
    assert "unobserved Q-state" in explain_qstate(frame)


def test_qlayers_are_canonical_parallel_world_tokens():
    layers = [QLayer("sim", 0.55, 0.25), QLayer("prod", 0.45, -0.25)]

    tokens = format_qlayers(layers)

    assert tokens == ["prod@.45/-.25", "sim@.55/.25"]
    assert parse_qlayers(tokens) == (QLayer("prod", 0.45, -0.25), QLayer("sim", 0.55, 0.25))


def test_qfield_tensor_combines_states_and_layers_with_coherence():
    branches = [QBranch("revise", 0.4, -0.25), QBranch("ship", 0.6)]
    layers = [QLayer("sim", 0.55, 0.25), QLayer("prod", 0.45, -0.25)]

    tensor = qfield_tensor(branches, layers)

    assert format_qbranches(tensor) == [
        "prod/revise@.18/-.5",
        "prod/ship@.27/-.25",
        "sim/revise@.22",
        "sim/ship@.33/.25",
    ]
    assert qfield_coherence(branches, layers) == 0.1644


def test_qfield_to_frame_materializes_tensor_without_observing():
    frame = make_qframe(
        agent="planner",
        state_hash="8f3c",
        op="plan",
        target="17",
        confidence=0.81,
        risk="med",
        branches=[QBranch("revise", 0.4, -0.25), QBranch("ship", 0.6)],
        layers=[QLayer("sim", 0.55, 0.25), QLayer("prod", 0.45, -0.25)],
        entangled=["critic.17", "coder.17"],
    )

    tensor_frame = qfield_to_frame(frame)

    assert serialize_zpls(tensor_frame) == (
        "§S1 a:planner sh:8f3c op:plan t:17 c:.81 r:med "
        "Δ{ent:[coder.17,critic.17],"
        "q:[prod/revise@.18/-.5,prod/ship@.27/-.25,sim/revise@.22,sim/ship@.33/.25],qcoh:.1644}"
    )
    assert semantic_hash(tensor_frame) == "fbfe9be78809"
    assert "coherence=.1644" in explain_qstate(frame)


def test_observe_qfield_collapses_state_and_layer_deterministically():
    frame = make_qframe(
        agent="planner",
        state_hash="8f3c",
        op="plan",
        target="17",
        confidence=0.81,
        risk="med",
        branches=[QBranch("revise", 0.4, -0.25), QBranch("ship", 0.6)],
        layers=[QLayer("sim", 0.55, 0.25), QLayer("prod", 0.45, -0.25)],
        entangled=["critic.17", "coder.17"],
    )

    observed = observe_qstate(frame, "human")

    assert q_observation_bucket(frame, "human") == 140
    assert q_layer_observation_bucket(frame, "human") == 3488
    assert q_layer_observation_material(frame, "human") == (
        '{"axis":"layer","frame":{"agent":"planner","confidence":0.81,'
        '"delta":{"ent":["coder.17","critic.17"],"q":["revise@.4/-.25","ship@.6"],'
        '"ql":["prod@.45/-.25","sim@.55/.25"]},"op":"plan","risk":"med",'
        '"state_hash":"8f3c","target":"17","version":"S1"},"observer":"human"}'
    )
    assert serialize_zpls(observed) == (
        "§S1 a:planner sh:8f3c op:plan t:17 c:.81 r:med "
        "Δ{ent:[coder.17,critic.17],qlphase:-.25,qlpick:prod,qobs:human,qphase:-.25,qpick:revise}"
    )
    assert "collapsed to prod/revise" in explain_qstate(observed)


def test_with_qstate_preserves_existing_frame_fields():
    base = ZplsFrame("S1", "critic", "8f3c", "eval", "17", 0.72, "med", {"next": "planner"})

    frame = with_qstate(
        base,
        [QBranch("accept", 0.5), QBranch("revise", 0.5)],
        layers=[QLayer("draft", 1.0)],
        entangled=["planner.17"],
    )

    assert frame.agent == base.agent
    assert frame.op == base.op
    assert frame.delta["next"] == "planner"
    assert frame.delta["q"] == ["accept@.5", "revise@.5"]
    assert frame.delta["ql"] == ["draft@1"]
    assert frame.delta["ent"] == ["planner.17"]


def test_observe_qstate_collapses_superposition_deterministically():
    frame = make_qframe(
        agent="router",
        state_hash="q8",
        op="plan",
        target="mesh",
        confidence=0.9,
        risk="low",
        branches=[QBranch("pathA", 0.25, 0.5), QBranch("pathB", 0.75)],
    )

    first = observe_qstate(frame, "human")
    second = observe_qstate(frame, "human")

    assert first == second
    assert "q" not in first.delta
    assert first.delta["qobs"] == "human"
    assert first.delta["qpick"] in {"pathA", "pathB"}
    assert "collapsed" in explain_qstate(first)


def test_q_observation_conformance_vector_is_stable():
    frame = make_qframe(
        agent="planner",
        state_hash="8f3c",
        op="plan",
        target="17",
        confidence=0.81,
        risk="med",
        branches=[QBranch("revise", 0.37, -0.5), QBranch("ship", 0.63)],
        entangled=["critic.17", "coder.17"],
    )

    assert serialize_zpls(frame) == (
        "§S1 a:planner sh:8f3c op:plan t:17 c:.81 r:med "
        "Δ{ent:[coder.17,critic.17],q:[revise@.37/-.5,ship@.63]}"
    )
    assert q_observation_material(frame, "human") == (
        '{"frame":{"agent":"planner","confidence":0.81,'
        '"delta":{"ent":["coder.17","critic.17"],"q":["revise@.37/-.5","ship@.63"]},'
        '"op":"plan","risk":"med","state_hash":"8f3c","target":"17","version":"S1"},'
        '"observer":"human"}'
    )
    assert q_observation_bucket(frame, "human") == 8738
    assert serialize_zpls(observe_qstate(frame, "human")) == (
        "§S1 a:planner sh:8f3c op:plan t:17 c:.81 r:med "
        "Δ{ent:[coder.17,critic.17],qobs:human,qpick:ship}"
    )


@pytest.mark.parametrize(
    "branches",
    [
        [],
        [QBranch("a", 0.2), QBranch("b", 0.3)],
        [QBranch("a", 0.5), QBranch("a", 0.5)],
    ],
)
def test_invalid_qbranch_sets_fail_closed(branches):
    with pytest.raises(ValueError):
        format_qbranches(branches)


@pytest.mark.parametrize(
    "token",
    ["branch", "branch@1.5", "branch@.5/2", "bad:ref@.5", "branch@.33333"],
)
def test_invalid_qbranch_tokens_fail_closed(token):
    with pytest.raises(ValueError):
        parse_qbranches([token])


@pytest.mark.parametrize(
    "layers",
    [
        [],
        [QLayer("sim", 0.2), QLayer("prod", 0.3)],
        [QLayer("sim", 0.5), QLayer("sim", 0.5)],
    ],
)
def test_invalid_qlayer_sets_fail_closed(layers):
    with pytest.raises(ValueError):
        format_qlayers(layers)


def test_observe_requires_q_superposition():
    frame = ZplsFrame("S1", "critic", "8f3c", "eval", "17", 0.72, "med", {"next": "planner"})

    with pytest.raises(ValueError):
        observe_qstate(frame, "human")
