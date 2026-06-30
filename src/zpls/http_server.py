from __future__ import annotations

import json
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from zpls.fabric import PeerKeyring, ZplsInternetGateway, ZplsNodeDescriptor, parse_fabric_envelope
from zpls.frame import parse_zpls, semantic_hash, serialize_zpls


@dataclass(frozen=True)
class ZplsHttpServerConfig:
    descriptor: ZplsNodeDescriptor
    keyring: PeerKeyring
    require_seal: bool = True
    outbound_seal_key: str | bytes | None = None
    outbound_seal_key_id: str = "mesh"
    max_body_bytes: int = 1_048_576

    def __post_init__(self) -> None:
        if isinstance(self.max_body_bytes, bool) or not isinstance(self.max_body_bytes, int):
            raise ValueError("max_body_bytes must be an integer")
        if not 1 <= self.max_body_bytes <= 16_777_216:
            raise ValueError("max_body_bytes must be between 1 and 16777216")


def make_zpls_http_handler(config: ZplsHttpServerConfig) -> type[BaseHTTPRequestHandler]:
    gateway = ZplsInternetGateway(config.descriptor, keyring=config.keyring, require_seal=config.require_seal)

    class ZplsHttpHandler(BaseHTTPRequestHandler):
        server_version = "ZPLSHTTP/0.1"

        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/health":
                self._json(HTTPStatus.OK, {"ok": True, "node_id": config.descriptor.node_id})
                return
            if self.path == "/.well-known/zpls.json":
                self._json(HTTPStatus.OK, config.descriptor.canonical())
                return
            self._json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not found"})

        def do_POST(self) -> None:  # noqa: N802
            try:
                if self.path == "/fabric/receive":
                    envelope = parse_fabric_envelope(self._read_text_body())
                    receipt = gateway.receive(envelope)
                    status = HTTPStatus.ACCEPTED if receipt.accepted else HTTPStatus.BAD_REQUEST
                    self._json(status, receipt.canonical())
                    return
                if self.path == "/fabric/pack":
                    request = self._read_json_body()
                    frame = parse_zpls(_required_text(request, "frame"))
                    envelope = gateway.pack(
                        frame,
                        destination=_required_text(request, "destination"),
                        trace_id=_required_text(request, "trace_id"),
                        ttl=_optional_int(request, "ttl", 60),
                        created_at=_optional_int_or_none(request, "created_at"),
                        seal_key=config.outbound_seal_key,
                        seal_key_id=config.outbound_seal_key_id,
                    )
                    self._json(HTTPStatus.OK, envelope.canonical())
                    return
                if self.path == "/frame/validate":
                    frame = parse_zpls(self._read_text_body().strip())
                    self._json(
                        HTTPStatus.OK,
                        {
                            "ok": True,
                            "frame": serialize_zpls(frame),
                            "frame_hash": semantic_hash(frame),
                        },
                    )
                    return
                self._json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not found"})
            except ValueError as exc:
                self._json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})

        def log_message(self, _format: str, *args: Any) -> None:
            return

        def _read_text_body(self) -> str:
            size = self._content_length()
            raw = self.rfile.read(size)
            try:
                return raw.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ValueError("request body must be UTF-8") from exc

        def _read_json_body(self) -> dict[str, Any]:
            try:
                obj = json.loads(self._read_text_body())
            except json.JSONDecodeError as exc:
                raise ValueError("request body must be JSON") from exc
            if not isinstance(obj, dict):
                raise ValueError("request body must be a JSON object")
            return obj

        def _content_length(self) -> int:
            raw = self.headers.get("Content-Length")
            if raw is None:
                raise ValueError("missing Content-Length")
            try:
                size = int(raw)
            except ValueError as exc:
                raise ValueError("invalid Content-Length") from exc
            if size < 0 or size > config.max_body_bytes:
                raise ValueError("request body too large")
            return size

        def _json(self, status: HTTPStatus, value: dict[str, Any]) -> None:
            payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
            self.send_response(status.value)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    return ZplsHttpHandler


def make_zpls_http_server(host: str, port: int, config: ZplsHttpServerConfig) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), make_zpls_http_handler(config))


def run_zpls_http_server(host: str, port: int, config: ZplsHttpServerConfig) -> None:
    server = make_zpls_http_server(host, port, config)
    try:
        server.serve_forever()
    finally:
        server.server_close()


def _required_text(obj: dict[str, Any], key: str) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"missing or invalid text field: {key}")
    return value


def _optional_int(obj: dict[str, Any], key: str, default: int) -> int:
    value = obj.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"invalid integer field: {key}")
    return value


def _optional_int_or_none(obj: dict[str, Any], key: str) -> int | None:
    if key not in obj:
        return None
    return _optional_int(obj, key, 0)
