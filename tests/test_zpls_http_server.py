from __future__ import annotations

import json
import threading
import time
from contextlib import contextmanager
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from zpls import (
    PeerKeyring,
    ZplsHttpServerConfig,
    ZplsInternetGateway,
    ZplsNodeDescriptor,
    make_zpls_http_server,
    parse_zpls,
)


@contextmanager
def _running_server(config: ZplsHttpServerConfig):
    server = make_zpls_http_server("127.0.0.1", 0, config)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _get_json(url: str) -> dict:
    with urlopen(url, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def _post(url: str, body: str, content_type: str = "application/json") -> tuple[int, dict]:
    request = Request(url, data=body.encode("utf-8"), method="POST", headers={"Content-Type": content_type})
    try:
        with urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def test_http_server_exposes_health_and_discovery():
    descriptor = ZplsNodeDescriptor("worker.example", "https://worker.example/.well-known/zpls.json", roles=("worker",))
    config = ZplsHttpServerConfig(descriptor, PeerKeyring({"mesh": "mesh-secret"}))

    with _running_server(config) as base:
        assert _get_json(f"{base}/health") == {"node_id": "worker.example", "ok": True}
        discovery = _get_json(f"{base}/.well-known/zpls.json")

    assert discovery["node_id"] == "worker.example"
    assert discovery["fabric_version"] == "F1"
    assert "qmatrix" in discovery["features"]


def test_http_server_receives_signed_fabric_envelope():
    planner = ZplsNodeDescriptor("planner.example", "https://planner.example/zpls", roles=("planner",))
    worker = ZplsNodeDescriptor("worker.example", "https://worker.example/zpls", roles=("worker",))
    frame = parse_zpls("§S1 a:planner sh:8f3c op:plan t:17 c:.91 r:low Δ{next:worker}")
    created_at = int(time.time())
    envelope = ZplsInternetGateway(planner, require_seal=False).pack(
        frame,
        destination="worker.example",
        trace_id="trace.demo",
        created_at=created_at,
        ttl=60,
        seal_key="mesh-secret",
    )
    config = ZplsHttpServerConfig(worker, PeerKeyring({"mesh": "mesh-secret"}))

    with _running_server(config) as base:
        status, receipt = _post(f"{base}/fabric/receive", envelope.to_json())

    assert status == 202
    assert receipt["accepted"] is True
    assert receipt["receiver"] == "worker"


def test_http_server_rejects_unsigned_when_required():
    planner = ZplsNodeDescriptor("planner.example", "https://planner.example/zpls", roles=("planner",))
    worker = ZplsNodeDescriptor("worker.example", "https://worker.example/zpls", roles=("worker",))
    frame = parse_zpls("§S1 a:planner sh:8f3c op:plan t:17 c:.91 r:low Δ{next:worker}")
    created_at = int(time.time())
    envelope = ZplsInternetGateway(planner, require_seal=False).pack(
        frame,
        destination="worker.example",
        trace_id="trace.demo",
        created_at=created_at,
    )
    config = ZplsHttpServerConfig(worker, PeerKeyring({"mesh": "mesh-secret"}))

    with _running_server(config) as base:
        status, receipt = _post(f"{base}/fabric/receive", envelope.to_json())

    assert status == 400
    assert receipt["accepted"] is False
    assert receipt["reason"] == "missing seal"


def test_http_server_packs_and_validates_frames():
    descriptor = ZplsNodeDescriptor("planner.example", "https://planner.example/zpls", roles=("planner",))
    config = ZplsHttpServerConfig(
        descriptor,
        PeerKeyring({"mesh": "mesh-secret"}),
        require_seal=False,
        outbound_seal_key="mesh-secret",
    )
    frame = "§S1 a:planner sh:8f3c op:plan t:17 c:.91 r:low Δ{next:worker}"

    with _running_server(config) as base:
        pack_status, envelope = _post(
            f"{base}/fabric/pack",
            json.dumps({"frame": frame, "destination": "worker.example", "trace_id": "trace.demo", "created_at": 1}),
        )
        validate_status, validation = _post(f"{base}/frame/validate", frame, content_type="text/plain")

    assert pack_status == 200
    assert envelope["source"] == "planner.example"
    assert "hmac-sha256.mesh" in envelope["frame"]
    assert validate_status == 200
    assert validation["ok"] is True
    assert validation["frame_hash"] == "42d035275a14"
