import json
import threading
import time
from urllib.request import Request, urlopen

from zpls import (
    PeerKeyring,
    ZplsHttpServerConfig,
    ZplsInternetGateway,
    ZplsNodeDescriptor,
    make_zpls_http_server,
    parse_zpls,
)


worker = ZplsNodeDescriptor("worker.local", "http://127.0.0.1:8787/.well-known/zpls.json", roles=("worker",))
server = make_zpls_http_server(
    "127.0.0.1",
    8787,
    ZplsHttpServerConfig(worker, PeerKeyring({"mesh": "mesh-secret"})),
)

thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()

try:
    planner = ZplsNodeDescriptor("planner.local", "http://127.0.0.1:8788/.well-known/zpls.json", roles=("planner",))
    frame = parse_zpls("§S1 a:planner sh:8f3c op:plan t:17 c:.91 r:low Δ{next:worker}")
    envelope = ZplsInternetGateway(planner, require_seal=False).pack(
        frame,
        destination="worker.local",
        trace_id="trace.demo",
        created_at=int(time.time()),
        seal_key="mesh-secret",
    )

    with urlopen("http://127.0.0.1:8787/.well-known/zpls.json", timeout=5) as response:
        print(response.read().decode("utf-8"))

    request = Request(
        "http://127.0.0.1:8787/fabric/receive",
        data=envelope.to_json().encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=5) as response:
        print(json.loads(response.read().decode("utf-8")))
finally:
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)
