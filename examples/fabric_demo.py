from zpls import (
    PeerKeyring,
    ZplsInternetGateway,
    ZplsNodeDescriptor,
    negotiate_capabilities,
    parse_zpls,
)


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

print(planner.to_json())
print(worker.to_json())
print(agreement.canonical())
print(envelope.to_json())
print(receipt.to_json())
