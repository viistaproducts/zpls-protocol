from __future__ import annotations

import hashlib

from zpls import (
    QBranch,
    QEdge,
    PeerKeyring,
    ZplsInternetGateway,
    ZplsNodeDescriptor,
    apply_qgate_to_frame,
    canonical_json,
    encode_zpls_binary,
    make_qframe,
    negotiate_capabilities,
    observe_qstate,
    parse_zpls,
    q_observation_bucket,
    q_observation_material,
    seal_zpls_frame,
    semantic_hash,
    serialize_zpls,
    verify_zpls_seal,
    zpls_seal_material,
)


def test_core_conformance_vector_1():
    frame = parse_zpls("§S1 a:critic sh:8f3c op:eval t:17 c:.72 r:med Δ{risk:+pricing_stale,next:revise}")

    assert serialize_zpls(frame) == "§S1 a:critic sh:8f3c op:eval t:17 c:.72 r:med Δ{next:revise,risk:+pricing_stale}"
    assert semantic_hash(frame) == "ab45ff627ee8"
    assert (
        encode_zpls_binary(frame).hex()
        == "5a504c530103040204386633630231371c20297b226e657874223a22726576697365222c227269736b223a222b70726963696e675f7374616c65227d"
    )


def test_seal_conformance_vector_4():
    frame = parse_zpls("§S1 a:critic sh:8f3c op:eval t:17 c:.72 r:med Δ{risk:+pricing_stale,next:revise}")
    sealed = seal_zpls_frame(frame, "mesh-secret", key_id="mesh")

    assert zpls_seal_material(sealed) == (
        '{"agent":"critic","confidence":0.72,"delta":{"next":"revise","risk":"+pricing_stale"},'
        '"op":"eval","risk":"med","state_hash":"8f3c","target":"17","version":"S1"}'
    )
    assert serialize_zpls(sealed) == (
        "§S1 a:critic sh:8f3c op:eval t:17 c:.72 r:med "
        "Δ{next:revise,risk:+pricing_stale,"
        "seal:hmac-sha256.mesh.625afd328670f6d36300c16b871cbc0059e57525a49da0332e282816c0db8b2c}"
    )
    assert semantic_hash(sealed) == "5c0eb2ef8627"
    assert (
        encode_zpls_binary(sealed).hex()
        == "5a504c530103040204386633630231371c2084017b226e657874223a22726576697365222c227269736b223a222b70726963696e675f7374616c65222c227365616c223a22686d61632d7368613235362e6d6573682e36323561666433323836373066366433363330306331366238373163626330303539653537353235613439646130333332653238323831366330646238623263227d"
    )
    assert verify_zpls_seal(sealed, "mesh-secret") is True
    assert verify_zpls_seal(sealed, "wrong-secret") is False


def test_fabric_conformance_vector_5():
    planner = ZplsNodeDescriptor("planner.example", "https://planner.example/.well-known/zpls.json", roles=("planner",))
    worker = ZplsNodeDescriptor("worker.example", "https://worker.example/.well-known/zpls.json", roles=("worker",))
    agreement = negotiate_capabilities(worker, planner)
    frame = parse_zpls("§S1 a:planner sh:8f3c op:plan t:17 c:.91 r:low Δ{next:worker}")
    envelope = ZplsInternetGateway(planner, require_seal=False).pack(
        frame,
        destination=worker.node_id,
        trace_id="trace.demo",
        created_at=1,
        ttl=60,
        seal_key="mesh-secret",
        seal_key_id="mesh",
    )
    gateway = ZplsInternetGateway(
        worker,
        keyring=PeerKeyring({"mesh": "mesh-secret"}),
        require_seal=True,
    )
    receipt = gateway.receive(envelope, now=2)
    replay_receipt = gateway.receive(envelope, now=2)

    assert planner.to_json() == (
        '{"endpoint":"https://planner.example/.well-known/zpls.json","fabric_version":"F1",'
        '"features":["binary","mesh","qgate","qmatrix","seal"],"node_id":"planner.example",'
        '"operations":["ack","done","escalate","eval","patch","plan","task"],"protocol_versions":["S1"],'
        '"roles":["planner"],"seal_key_ids":["mesh"],"transports":["https+json"]}'
    )
    assert canonical_json(agreement.canonical()) == (
        '{"features":["binary","mesh","qgate","qmatrix","seal"],'
        '"operations":["ack","done","escalate","eval","patch","plan","task"],'
        '"protocol_version":"S1","seal_key_ids":["mesh"],"transport":"https+json"}'
    )
    assert envelope.to_json() == (
        '{"content_type":"application/zpls+text","created_at":1,"destination":"worker.example",'
        '"fabric_version":"F1","frame":"§S1 a:planner sh:8f3c op:plan t:17 c:.91 r:low '
        'Δ{next:worker,seal:hmac-sha256.mesh.416cc99c44fcfef70c345d03112cdaeca1cd5b4b4ee8591ba8e38e42e60acd5d}",'
        '"frame_hash":"4a66dcefb21e","route":["planner.example"],"source":"planner.example",'
        '"trace_id":"trace.demo","ttl":60}'
    )
    assert receipt.to_json() == (
        '{"accepted":true,"destination":"worker.example","frame_hash":"4a66dcefb21e",'
        '"reason":"delivered","receiver":"worker","source":"planner.example","trace_id":"trace.demo"}'
    )
    assert replay_receipt.to_json() == (
        '{"accepted":false,"destination":"worker.example","frame_hash":"4a66dcefb21e",'
        '"reason":"replay","receiver":null,"source":"planner.example","trace_id":"trace.demo"}'
    )


def test_qgate_conformance_vector_3():
    frame = make_qframe(
        agent="planner",
        state_hash="8f3c",
        op="plan",
        target="17",
        confidence=0.81,
        risk="med",
        branches=[QBranch("u0/a", 0.5), QBranch("u0/b", 0.5, 0.5)],
    )
    edges = [
        QEdge("u0/a", "u1/x", 0.8),
        QEdge("u0/b", "u1/x", 0.8),
        QEdge("u0/a", "u1/y", 0.2),
        QEdge("u0/b", "u1/y", 0.2, -0.5),
    ]
    projected = apply_qgate_to_frame(frame, edges, keep_gate=True)

    assert serialize_zpls(projected) == (
        "§S1 a:planner sh:8f3c op:plan t:17 c:.81 r:med "
        "Δ{gate:[u0/a=u1/x@.8,u0/a=u1/y@.2,u0/b=u1/x@.8,u0/b=u1/y@.2/-.5],"
        "q:[u1/x@.6667/.25,u1/y@.3333]}"
    )
    assert semantic_hash(projected) == "0a56b1189f1a"
    assert (
        encode_zpls_binary(projected).hex()
        == "5a504c530101060204386633630231371fa46e7b2267617465223a5b2275302f613d75312f78402e38222c2275302f613d75312f79402e32222c2275302f623d75312f78402e38222c2275302f623d75312f79402e322f2d2e35225d2c2271223a5b2275312f78402e363636372f2e3235222c2275312f79402e33333333225d7d"
    )


def test_qmatrix_conformance_vector_2():
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
    material = q_observation_material(frame, "human")
    observed = observe_qstate(frame, "human")

    assert serialize_zpls(frame) == (
        "§S1 a:planner sh:8f3c op:plan t:17 c:.81 r:med "
        "Δ{ent:[coder.17,critic.17],q:[revise@.37/-.5,ship@.63]}"
    )
    assert semantic_hash(frame) == "911b59bcd4ce"
    assert (
        encode_zpls_binary(frame).hex()
        == "5a504c530101060204386633630231371fa4427b22656e74223a5b22636f6465722e3137222c226372697469632e3137225d2c2271223a5b22726576697365402e33372f2d2e35222c2273686970402e3633225d7d"
    )
    assert material == (
        '{"frame":{"agent":"planner","confidence":0.81,'
        '"delta":{"ent":["coder.17","critic.17"],"q":["revise@.37/-.5","ship@.63"]},'
        '"op":"plan","risk":"med","state_hash":"8f3c","target":"17","version":"S1"},'
        '"observer":"human"}'
    )
    assert hashlib.sha256(material.encode("utf-8")).hexdigest() == (
        "dfb34f9465e4e61968ee6fee6279472c6f46b85a39a1cee2d3df474cb4d9fbf1"
    )
    assert q_observation_bucket(frame, "human") == 8738
    assert serialize_zpls(observed) == (
        "§S1 a:planner sh:8f3c op:plan t:17 c:.81 r:med "
        "Δ{ent:[coder.17,critic.17],qobs:human,qpick:ship}"
    )
    assert semantic_hash(observed) == "1b02f134f21b"
    assert (
        encode_zpls_binary(observed).hex()
        == "5a504c530101060204386633630231371fa43e7b22656e74223a5b22636f6465722e3137222c226372697469632e3137225d2c22716f6273223a2268756d616e222c22717069636b223a2273686970227d"
    )
