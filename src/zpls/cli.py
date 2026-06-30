from __future__ import annotations

import argparse
import hashlib
import json
import sys
from typing import Sequence

from zpls import (
    QBranch,
    QLayer,
    Q_LAYER_KEY,
    Q_STATE_KEY,
    PeerKeyring,
    ZplsInternetGateway,
    ZplsHttpServerConfig,
    ZplsMesh,
    ZplsNodeDescriptor,
    apply_qgate_to_frame,
    decode_zpls_binary,
    encode_zpls_binary,
    explain_qstate,
    explain_zpls,
    format_qbranches,
    format_qlayers,
    make_qframe,
    observe_qstate,
    parse_qbranches,
    parse_qlayers,
    parse_qedges,
    parse_fabric_envelope,
    parse_node_descriptor,
    parse_zpls,
    negotiate_capabilities,
    q_observation_bucket,
    q_observation_material,
    q_layer_observation_bucket,
    q_layer_observation_material,
    qfield_coherence,
    qfield_tensor,
    qfield_to_frame,
    run_zpls_http_server,
    seal_zpls_frame,
    semantic_hash,
    serialize_zpls,
    verify_zpls_seal,
    zpls_frame_seal,
    zpls_seal_material,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="zpls", description="ZPL-S Protokoll-Werkzeug")
    sub = parser.add_subparsers(dest="command")

    p_validate = sub.add_parser("validate", help="Frame validieren und kanonisch ausgeben")
    p_validate.add_argument("input", nargs="?", help="Frame-Text, sonst stdin")
    p_validate.set_defaults(func=_cmd_validate)

    p_explain = sub.add_parser("explain", help="Frame menschlich erklaeren")
    p_explain.add_argument("input", nargs="?", help="Frame-Text, sonst stdin")
    p_explain.set_defaults(func=_cmd_explain)

    p_binary = sub.add_parser("binary", help="Frame als binaeres Hex codieren")
    p_binary.add_argument("input", nargs="?", help="Frame-Text, sonst stdin")
    p_binary.set_defaults(func=_cmd_binary)

    p_from_binary = sub.add_parser("from-binary", help="Binaeres Hex als Textframe decodieren")
    p_from_binary.add_argument("hex", nargs="?", help="Hex-String, sonst stdin")
    p_from_binary.set_defaults(func=_cmd_from_binary)

    p_seal = sub.add_parser("seal", help="Frame mit HMAC-SHA256 siegeln")
    p_seal.add_argument("--key", required=True, help="Gemeinsamer Mesh-Schluessel")
    p_seal.add_argument("--key-id", default="mesh", help="Key-ID im Seal")
    p_seal.add_argument("input", nargs="?", help="Frame-Text, sonst stdin")
    p_seal.set_defaults(func=_cmd_seal)

    p_verify = sub.add_parser("verify", help="Frame-Seal pruefen")
    p_verify.add_argument("--key", required=True, help="Gemeinsamer Mesh-Schluessel")
    p_verify.add_argument("input", nargs="?", help="Frame-Text, sonst stdin")
    p_verify.add_argument("--json", action="store_true", help="Pruefmaterial als JSON ausgeben")
    p_verify.set_defaults(func=_cmd_verify)

    p_qmake = sub.add_parser("qmake", help="Q-Frame aus Branches bauen")
    p_qmake.add_argument("--agent", required=True)
    p_qmake.add_argument("--state", required=True, help="State hash/ref")
    p_qmake.add_argument("--op", required=True)
    p_qmake.add_argument("--target", required=True)
    p_qmake.add_argument("--confidence", type=float, required=True)
    p_qmake.add_argument("--risk", required=True)
    p_qmake.add_argument("--branches", required=True, help="Kommagetrennte Q-Branches")
    p_qmake.add_argument("--layers", default="", help="Kommagetrennte Q-Layer")
    p_qmake.add_argument("--entangled", default="", help="Kommagetrennte Entanglement-Refs")
    p_qmake.set_defaults(func=_cmd_qmake)

    p_qgate = sub.add_parser("qgate", help="Sparse Q-Gate auf Q-Frame anwenden")
    p_qgate.add_argument("--frame", help="Q-Frame-Text, sonst stdin")
    p_qgate.add_argument("--edges", required=True, help="Kommagetrennte QEdge-Tokens")
    p_qgate.add_argument("--keep-gate", action="store_true", help="Gate im Delta mit ausgeben")
    p_qgate.set_defaults(func=_cmd_qgate)

    p_qfield = sub.add_parser("qfield", help="Q-State und Q-Layer zu Tensorfeld expandieren")
    p_qfield.add_argument("--frame", help="Q-Frame-Text, sonst stdin")
    p_qfield.add_argument("--as-frame", action="store_true", help="Tensorfeld als kanonischen Frame ausgeben")
    p_qfield.add_argument("--keep-layers", action="store_true", help="Layerliste im Tensorframe behalten")
    p_qfield.set_defaults(func=_cmd_qfield)

    p_observe = sub.add_parser("observe", help="Q-Frame durch Beobachter kollabieren")
    p_observe.add_argument("--observer", required=True)
    p_observe.add_argument("input", nargs="?", help="Q-Frame-Text, sonst stdin")
    p_observe.add_argument("--json", action="store_true", help="Material, Digest und Bucket mit ausgeben")
    p_observe.set_defaults(func=_cmd_observe)

    p_conf = sub.add_parser("conformance", help="Eingebaute Conformance-Vektoren pruefen")
    p_conf.set_defaults(func=_cmd_conformance)

    p_mesh = sub.add_parser("mesh-demo", help="Ausfuehrbare Mini-Mesh-Route demonstrieren")
    p_mesh.set_defaults(func=_cmd_mesh_demo)

    p_fdesc = sub.add_parser("fabric-describe", help="Internet-Fabric Discovery-Dokument ausgeben")
    p_fdesc.add_argument("--node-id", required=True)
    p_fdesc.add_argument("--endpoint", required=True)
    p_fdesc.add_argument("--roles", default="worker")
    p_fdesc.add_argument("--features", default="binary,mesh,qfield,qgate,qmatrix,seal")
    p_fdesc.add_argument("--transports", default="https+json")
    p_fdesc.add_argument("--seal-key-ids", default="mesh")
    p_fdesc.set_defaults(func=_cmd_fabric_describe)

    p_fneg = sub.add_parser("fabric-negotiate", help="Zwei Fabric-Descriptoren aushandeln")
    p_fneg.add_argument("--local", required=True, help="Lokales Descriptor-JSON")
    p_fneg.add_argument("--remote", required=True, help="Remote Descriptor-JSON")
    p_fneg.set_defaults(func=_cmd_fabric_negotiate)

    p_fpack = sub.add_parser("fabric-pack", help="Frame in Internet-Fabric Envelope packen")
    p_fpack.add_argument("--source", required=True)
    p_fpack.add_argument("--endpoint", required=True)
    p_fpack.add_argument("--destination", required=True)
    p_fpack.add_argument("--trace", required=True)
    p_fpack.add_argument("--created-at", type=int)
    p_fpack.add_argument("--ttl", type=int, default=60)
    p_fpack.add_argument("--key")
    p_fpack.add_argument("--key-id", default="mesh")
    p_fpack.add_argument("input", nargs="?", help="Frame-Text, sonst stdin")
    p_fpack.set_defaults(func=_cmd_fabric_pack)

    p_frecv = sub.add_parser("fabric-receive", help="Internet-Fabric Envelope pruefen und lokal routen")
    p_frecv.add_argument("--node-id", required=True)
    p_frecv.add_argument("--endpoint", required=True)
    p_frecv.add_argument("--roles", default="worker")
    p_frecv.add_argument("--key")
    p_frecv.add_argument("--key-id", default="mesh")
    p_frecv.add_argument("--now", type=int)
    p_frecv.add_argument("--allow-unsigned", action="store_true")
    p_frecv.add_argument("input", nargs="?", help="Envelope-JSON, sonst stdin")
    p_frecv.set_defaults(func=_cmd_fabric_receive)

    p_fdemo = sub.add_parser("fabric-demo", help="Signierten Internet-Fabric Austausch demonstrieren")
    p_fdemo.set_defaults(func=_cmd_fabric_demo)

    p_serve = sub.add_parser("serve", help="ZPL-S HTTP-Fabric Server starten")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8787)
    p_serve.add_argument("--node-id", required=True)
    p_serve.add_argument("--endpoint", required=True)
    p_serve.add_argument("--roles", default="worker")
    p_serve.add_argument("--key")
    p_serve.add_argument("--key-id", default="mesh")
    p_serve.add_argument("--allow-unsigned", action="store_true")
    p_serve.set_defaults(func=_cmd_serve)

    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 2
    try:
        return args.func(args)
    except ValueError as exc:
        print(f"zpls error: {exc}", file=sys.stderr)
        return 1


def _read_arg_or_stdin(value: str | None) -> str:
    return value if value is not None else sys.stdin.read()


def _split_csv(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def _cmd_validate(args: argparse.Namespace) -> int:
    frame = parse_zpls(_read_arg_or_stdin(args.input).strip())
    print(serialize_zpls(frame))
    return 0


def _cmd_explain(args: argparse.Namespace) -> int:
    frame = parse_zpls(_read_arg_or_stdin(args.input).strip())
    print(explain_zpls(frame))
    print(explain_qstate(frame))
    return 0


def _cmd_binary(args: argparse.Namespace) -> int:
    frame = parse_zpls(_read_arg_or_stdin(args.input).strip())
    print(encode_zpls_binary(frame).hex())
    return 0


def _cmd_from_binary(args: argparse.Namespace) -> int:
    raw = _read_arg_or_stdin(args.hex).strip()
    frame = decode_zpls_binary(bytes.fromhex(raw))
    print(serialize_zpls(frame))
    return 0


def _cmd_seal(args: argparse.Namespace) -> int:
    frame = parse_zpls(_read_arg_or_stdin(args.input).strip())
    print(serialize_zpls(seal_zpls_frame(frame, args.key, key_id=args.key_id)))
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    frame = parse_zpls(_read_arg_or_stdin(args.input).strip())
    ok = verify_zpls_seal(frame, args.key)
    if args.json:
        try:
            seal = zpls_frame_seal(frame)
            seal_json = {"alg": seal.alg, "key_id": seal.key_id, "mac": seal.mac}
        except ValueError:
            seal_json = None
        print(
            json.dumps(
                {
                    "ok": ok,
                    "seal": seal_json,
                    "material": zpls_seal_material(frame),
                    "frame_hash": semantic_hash(frame),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print("ok" if ok else "fail")
    return 0 if ok else 1


def _cmd_qmake(args: argparse.Namespace) -> int:
    frame = make_qframe(
        agent=args.agent,
        state_hash=args.state,
        op=args.op,
        target=args.target,
        confidence=args.confidence,
        risk=args.risk,
        branches=parse_qbranches(_split_csv(args.branches)),
        layers=parse_qlayers(_split_csv(args.layers)) if args.layers else (),
        entangled=_split_csv(args.entangled),
    )
    print(serialize_zpls(frame))
    return 0


def _cmd_qgate(args: argparse.Namespace) -> int:
    frame = parse_zpls(_read_arg_or_stdin(args.frame).strip())
    projected = apply_qgate_to_frame(frame, parse_qedges(_split_csv(args.edges)), keep_gate=args.keep_gate)
    print(serialize_zpls(projected))
    return 0


def _cmd_qfield(args: argparse.Namespace) -> int:
    frame = parse_zpls(_read_arg_or_stdin(args.frame).strip())
    if args.as_frame:
        print(serialize_zpls(qfield_to_frame(frame, keep_layers=args.keep_layers)))
        return 0
    raw_branches = frame.delta.get(Q_STATE_KEY)
    raw_layers = frame.delta.get(Q_LAYER_KEY)
    if not isinstance(raw_branches, list):
        raise ValueError("ZPL-S frame does not carry a Q superposition")
    if not isinstance(raw_layers, list):
        raise ValueError("ZPL-S frame does not carry Q layers")
    branches = parse_qbranches(raw_branches)
    layers = parse_qlayers(raw_layers)
    tensor = qfield_tensor(branches, layers)
    print(
        json.dumps(
            {
                "coherence": qfield_coherence(branches, layers),
                "layers": format_qlayers(layers),
                "tensor": format_qbranches(tensor),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _cmd_observe(args: argparse.Namespace) -> int:
    frame = parse_zpls(_read_arg_or_stdin(args.input).strip())
    observed = observe_qstate(frame, args.observer)
    if args.json:
        material = q_observation_material(frame, args.observer)
        payload = {
            "material": material,
            "sha256": hashlib.sha256(material.encode("utf-8")).hexdigest(),
            "bucket": q_observation_bucket(frame, args.observer),
            "observed": serialize_zpls(observed),
            "observed_hash": semantic_hash(observed),
        }
        if Q_LAYER_KEY in frame.delta:
            layer_material = q_layer_observation_material(frame, args.observer)
            payload["layer_material"] = layer_material
            payload["layer_sha256"] = hashlib.sha256(layer_material.encode("utf-8")).hexdigest()
            payload["layer_bucket"] = q_layer_observation_bucket(frame, args.observer)
        print(
            json.dumps(
                payload,
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(serialize_zpls(observed))
    return 0


def _cmd_conformance(_args: argparse.Namespace) -> int:
    core = parse_zpls("§S1 a:critic sh:8f3c op:eval t:17 c:.72 r:med Δ{risk:+pricing_stale,next:revise}")
    qframe = make_qframe(
        agent="planner",
        state_hash="8f3c",
        op="plan",
        target="17",
        confidence=0.81,
        risk="med",
        branches=[QBranch("revise", 0.37, -0.5), QBranch("ship", 0.63)],
        entangled=["critic.17", "coder.17"],
    )
    qfield_frame = make_qframe(
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
    qfield_tensor_frame = qfield_to_frame(qfield_frame)
    qfield_observed = observe_qstate(qfield_frame, "human")
    planner = ZplsNodeDescriptor("planner.example", "https://planner.example/.well-known/zpls.json", roles=("planner",))
    worker = ZplsNodeDescriptor("worker.example", "https://worker.example/.well-known/zpls.json", roles=("worker",))
    fabric_frame = parse_zpls("§S1 a:planner sh:8f3c op:plan t:17 c:.91 r:low Δ{next:worker}")
    fabric_envelope = ZplsInternetGateway(planner, require_seal=False).pack(
        fabric_frame,
        destination=worker.node_id,
        trace_id="trace.demo",
        created_at=1,
        ttl=60,
        seal_key="mesh-secret",
        seal_key_id="mesh",
    )
    fabric_gateway = ZplsInternetGateway(
        worker,
        keyring=PeerKeyring({"mesh": "mesh-secret"}),
        require_seal=True,
    )
    fabric_receipt = fabric_gateway.receive(fabric_envelope, now=2)
    fabric_replay = fabric_gateway.receive(fabric_envelope, now=2)
    checks = {
        "core_text": serialize_zpls(core) == "§S1 a:critic sh:8f3c op:eval t:17 c:.72 r:med Δ{next:revise,risk:+pricing_stale}",
        "core_hash": semantic_hash(core) == "ab45ff627ee8",
        "core_seal": verify_zpls_seal(seal_zpls_frame(core, "mesh-secret", key_id="mesh"), "mesh-secret"),
        "fabric_receipt": fabric_receipt.accepted and fabric_receipt.receiver == "worker",
        "fabric_replay": not fabric_replay.accepted and fabric_replay.reason == "replay",
        "q_bucket": q_observation_bucket(qframe, "human") == 8738,
        "q_observed": serialize_zpls(observe_qstate(qframe, "human"))
        == "§S1 a:planner sh:8f3c op:plan t:17 c:.81 r:med Δ{ent:[coder.17,critic.17],qobs:human,qpick:ship}",
        "qfield_tensor": serialize_zpls(qfield_tensor_frame)
        == (
            "§S1 a:planner sh:8f3c op:plan t:17 c:.81 r:med "
            "Δ{ent:[coder.17,critic.17],"
            "q:[prod/revise@.18/-.5,prod/ship@.27/-.25,sim/revise@.22,sim/ship@.33/.25],qcoh:.1644}"
        ),
        "qfield_observed": serialize_zpls(qfield_observed)
        == (
            "§S1 a:planner sh:8f3c op:plan t:17 c:.81 r:med "
            "Δ{ent:[coder.17,critic.17],qlphase:-.25,qlpick:prod,qobs:human,qphase:-.25,qpick:revise}"
        ),
    }
    print(json.dumps({"ok": all(checks.values()), "checks": checks}, indent=2))
    return 0 if all(checks.values()) else 1


def _cmd_mesh_demo(_args: argparse.Namespace) -> int:
    mesh = ZplsMesh()
    mesh.register("planner")
    mesh.register("worker")
    frame = make_qframe(
        agent="planner",
        state_hash=mesh.put_state("plan.17", {"status": "open", "task": "price_check"}),
        op="plan",
        target="17",
        confidence=0.81,
        risk="med",
        branches=[QBranch("revise", 0.37, -0.5), QBranch("ship", 0.63)],
    )
    event = mesh.route(frame, sender="planner", observer="human")
    print(
        json.dumps(
            {
                "accepted": event.accepted,
                "reason": event.reason,
                "sender": event.sender,
                "receiver": event.receiver,
                "frame_hash": event.frame_hash,
                "frame": serialize_zpls(event.frame),
                "worker_inbox": [serialize_zpls(item) for item in mesh.inbox("worker")],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if event.accepted else 1


def _descriptor_from_args(args: argparse.Namespace) -> ZplsNodeDescriptor:
    return ZplsNodeDescriptor(
        node_id=args.node_id,
        endpoint=args.endpoint,
        roles=tuple(_split_csv(args.roles)),
        features=tuple(_split_csv(args.features)),
        transports=tuple(_split_csv(args.transports)),
        seal_key_ids=tuple(_split_csv(args.seal_key_ids)),
    )


def _cmd_fabric_describe(args: argparse.Namespace) -> int:
    print(_descriptor_from_args(args).to_json())
    return 0


def _cmd_fabric_negotiate(args: argparse.Namespace) -> int:
    agreement = negotiate_capabilities(parse_node_descriptor(args.local), parse_node_descriptor(args.remote))
    print(json.dumps(agreement.canonical(), ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


def _cmd_fabric_pack(args: argparse.Namespace) -> int:
    descriptor = ZplsNodeDescriptor(node_id=args.source, endpoint=args.endpoint)
    gateway = ZplsInternetGateway(descriptor, require_seal=False)
    frame = parse_zpls(_read_arg_or_stdin(args.input).strip())
    envelope = gateway.pack(
        frame,
        destination=args.destination,
        trace_id=args.trace,
        ttl=args.ttl,
        created_at=args.created_at,
        seal_key=args.key,
        seal_key_id=args.key_id,
    )
    print(envelope.to_json())
    return 0


def _cmd_fabric_receive(args: argparse.Namespace) -> int:
    descriptor = ZplsNodeDescriptor(node_id=args.node_id, endpoint=args.endpoint, roles=tuple(_split_csv(args.roles)))
    keyring = PeerKeyring()
    if args.key is not None:
        keyring.add(args.key_id, args.key)
    gateway = ZplsInternetGateway(descriptor, keyring=keyring, require_seal=not args.allow_unsigned)
    envelope = parse_fabric_envelope(_read_arg_or_stdin(args.input).strip())
    receipt = gateway.receive(envelope, now=args.now)
    print(receipt.to_json())
    return 0 if receipt.accepted else 1


def _cmd_fabric_demo(_args: argparse.Namespace) -> int:
    planner = ZplsNodeDescriptor("planner.example", "https://planner.example/.well-known/zpls.json", roles=("planner",))
    worker = ZplsNodeDescriptor("worker.example", "https://worker.example/.well-known/zpls.json", roles=("worker",))
    agreement = negotiate_capabilities(worker, planner)
    outbox = ZplsInternetGateway(planner, require_seal=False)
    inbox = ZplsInternetGateway(worker, keyring=PeerKeyring({"mesh": "mesh-secret"}), require_seal=True)
    frame = parse_zpls("§S1 a:planner sh:8f3c op:plan t:17 c:.91 r:low Δ{next:worker}")
    envelope = outbox.pack(
        frame,
        destination=worker.node_id,
        trace_id="trace.demo",
        created_at=1,
        ttl=60,
        seal_key="mesh-secret",
        seal_key_id="mesh",
    )
    receipt = inbox.receive(envelope, now=2)
    print(
        json.dumps(
            {
                "planner": planner.canonical(),
                "worker": worker.canonical(),
                "agreement": agreement.canonical(),
                "envelope": envelope.canonical(),
                "receipt": receipt.canonical(),
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0 if receipt.accepted else 1


def _cmd_serve(args: argparse.Namespace) -> int:
    descriptor = ZplsNodeDescriptor(args.node_id, args.endpoint, roles=tuple(_split_csv(args.roles)))
    keyring = PeerKeyring()
    if args.key is not None:
        keyring.add(args.key_id, args.key)
    config = ZplsHttpServerConfig(
        descriptor=descriptor,
        keyring=keyring,
        require_seal=not args.allow_unsigned,
        outbound_seal_key=args.key,
        outbound_seal_key_id=args.key_id,
    )
    print(f"zpls http server listening on http://{args.host}:{args.port}", file=sys.stderr)
    run_zpls_http_server(args.host, args.port, config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
