from __future__ import annotations

from zpls import (
    SEAL_ALG,
    ZplsFrame,
    decode_zpls_binary,
    encode_zpls_binary,
    parse_zpls,
    seal_zpls_frame,
    serialize_zpls,
    strip_zpls_seal,
    verify_zpls_seal,
    zpls_frame_seal,
    zpls_seal_material,
)


def test_seal_adds_hmac_over_canonical_frame_without_self_reference():
    frame = parse_zpls("§S1 a:critic sh:8f3c op:eval t:17 c:.72 r:med Δ{risk:+pricing_stale,next:revise}")

    sealed = seal_zpls_frame(frame, "mesh-secret", key_id="mesh")
    seal = zpls_frame_seal(sealed)

    assert seal.alg == SEAL_ALG
    assert seal.key_id == "mesh"
    assert len(seal.mac) == 64
    assert verify_zpls_seal(sealed, "mesh-secret") is True
    assert zpls_seal_material(sealed) == zpls_seal_material(frame)
    assert strip_zpls_seal(sealed) == frame
    assert serialize_zpls(sealed).startswith(
        "§S1 a:critic sh:8f3c op:eval t:17 c:.72 r:med Δ{next:revise,risk:+pricing_stale,seal:hmac-sha256.mesh."
    )


def test_seal_rejects_wrong_key_and_tampered_frame():
    frame = ZplsFrame("S1", "planner", "8f3c", "plan", "17", 0.9, "low", {"next": "worker"})
    sealed = seal_zpls_frame(frame, "mesh-secret")

    tampered = ZplsFrame("S1", "planner", "8f3c", "plan", "17", 0.9, "high", dict(sealed.delta))

    assert verify_zpls_seal(sealed, "wrong-secret") is False
    assert verify_zpls_seal(tampered, "mesh-secret") is False


def test_seal_survives_binary_roundtrip():
    frame = ZplsFrame("S1", "planner", "8f3c", "plan", "17", 0.9, "low", {"next": "worker"})
    sealed = seal_zpls_frame(frame, "mesh-secret", key_id="mesh")

    decoded = decode_zpls_binary(encode_zpls_binary(sealed))

    assert decoded.canonical() == sealed.canonical()
    assert verify_zpls_seal(decoded, {"mesh": "mesh-secret"}) is True
