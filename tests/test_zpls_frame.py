from __future__ import annotations

import struct

import pytest

from zpls import (
    ZplsFrame,
    decode_varint,
    decode_zpls_binary,
    encode_varint,
    encode_zpls_binary,
    explain_zpls,
    parse_zpls,
    semantic_hash,
    serialize_zpls,
)


def _text_field(value: str | bytes) -> bytes:
    raw = value if isinstance(value, bytes) else value.encode("utf-8")
    assert len(raw) < 128
    return bytes([len(raw)]) + raw


def _frame() -> ZplsFrame:
    return ZplsFrame(
        version="S1",
        agent="critic",
        state_hash="8f3c",
        op="eval",
        target="17",
        confidence=0.72,
        risk="med",
        delta={"risk": "+pricing_stale", "next": "revise"},
    )


def test_text_roundtrip_is_canonical_and_compact():
    text = serialize_zpls(_frame())
    assert text == "§S1 a:critic sh:8f3c op:eval t:17 c:.72 r:med Δ{next:revise,risk:+pricing_stale}"
    assert parse_zpls(text) == _frame()


def test_text_and_binary_roundtrip_are_semantically_equivalent():
    frame = parse_zpls("§S1 a:critic sh:8f3c op:eval t:17 c:.72 r:med Δ{flags:[stale,needs_review],ok:true,n:2}")
    binary_frame = decode_zpls_binary(encode_zpls_binary(frame))
    assert binary_frame.canonical() == frame.canonical()
    assert serialize_zpls(binary_frame) == "§S1 a:critic sh:8f3c op:eval t:17 c:.72 r:med Δ{flags:[stale,needs_review],n:2,ok:true}"


def test_binary_confidence_uses_canonical_four_decimal_rounding():
    frame = ZplsFrame("S1", "critic", "8f3c", "eval", "17", 0.00005, "med", {})
    binary_frame = decode_zpls_binary(encode_zpls_binary(frame))

    assert frame.canonical()["confidence"] == 0.0001
    assert binary_frame.canonical() == frame.canonical()
    assert serialize_zpls(binary_frame) == "§S1 a:critic sh:8f3c op:eval t:17 c:.0001 r:med Δ{}"


def test_binary_is_smaller_than_text_for_known_symbols():
    assert len(encode_zpls_binary(_frame())) < len(serialize_zpls(_frame()).encode("utf-8"))


def test_unknown_agent_names_roundtrip_as_binary_text_fields():
    frame = ZplsFrame("S1", "agent42", "8f3c", "eval", "17", 0.72, "med", {"next": "revise"})
    blob = encode_zpls_binary(frame)

    assert blob.startswith(b"ZPLS\x01\x00\x07agent42")
    assert decode_zpls_binary(blob).canonical() == frame.canonical()


def test_semantic_hash_is_stable_across_delta_order():
    first = _frame()
    second = ZplsFrame("S1", "critic", "8f3c", "eval", "17", 0.72, "med", {"next": "revise", "risk": "+pricing_stale"})
    assert semantic_hash(first) == semantic_hash(second)
    assert encode_zpls_binary(first) == encode_zpls_binary(second)


def test_semantic_hash_length_must_be_explicit_positive_hex_prefix():
    frame = _frame()

    assert len(semantic_hash(frame, length=1)) == 1
    assert len(semantic_hash(frame, length=64)) == 64
    for length in [0, -1, 65, True, False, 1.5, "12"]:
        with pytest.raises(ValueError):
            semantic_hash(frame, length=length)  # type: ignore[arg-type]


def test_semantic_hash_is_stable_across_text_order_whitespace_and_numeric_formatting():
    first = parse_zpls("§S1 a:critic sh:8f3c op:eval t:17 c:.72 r:med Δ{p:.5000,n:2,next:revise}")
    second = parse_zpls("  §S1   r:med c:0.7200 t:17 op:eval sh:8f3c a:critic   Δ{ p : .5 , n : 2 , next:revise }  ")

    assert first.canonical() == second.canonical()
    assert semantic_hash(first) == semantic_hash(second)
    assert serialize_zpls(second) == "§S1 a:critic sh:8f3c op:eval t:17 c:.72 r:med Δ{n:2,next:revise,p:.5}"


def test_integral_delta_floats_preserve_text_roundtrip_semantics():
    frame = ZplsFrame(
        "S1",
        "critic",
        "8f3c",
        "eval",
        "17",
        0.72,
        "med",
        {"neg": -1.0, "one": 1.0, "two": 2.0, "zero": 0.0},
    )
    text = serialize_zpls(frame)

    assert text == "§S1 a:critic sh:8f3c op:eval t:17 c:.72 r:med Δ{neg:-1.0,one:1.0,two:2.0,zero:0.0}"
    assert parse_zpls(text).canonical() == frame.canonical()
    assert semantic_hash(parse_zpls(text)) == semantic_hash(frame)


def test_delta_floats_are_serialized_to_four_decimal_canonical_form():
    frame = ZplsFrame("S1", "critic", "8f3c", "eval", "17", 0.72, "med", {"pi": 3.141592, "p": 0.333333})

    assert serialize_zpls(frame) == "§S1 a:critic sh:8f3c op:eval t:17 c:.72 r:med Δ{p:.3333,pi:3.1416}"
    assert parse_zpls(serialize_zpls(frame)).canonical() == frame.canonical()


def test_signed_zero_is_normalized_for_hashing_and_serialization():
    frame = ZplsFrame("S1", "critic", "8f3c", "eval", "17", -0.0, "med", {"z": -0.0})
    text = serialize_zpls(frame)

    assert text == "§S1 a:critic sh:8f3c op:eval t:17 c:0 r:med Δ{z:0.0}"
    assert parse_zpls(text).canonical() == frame.canonical()
    assert semantic_hash(parse_zpls(text)) == semantic_hash(frame)


@pytest.mark.parametrize(
    ("frame", "prose"),
    [
        (
            ZplsFrame("S1", "planner", "a13f", "task", "t17", 0.86, "low", {"ask": "price_table", "next": "worker"}),
            "The planner agent creates a task for target t17 against shared state hash a13f with low risk and 86 percent confidence. It asks the worker to inspect the price table next.",
        ),
        (
            ZplsFrame("S1", "worker", "b44e", "patch", "t17", 0.79, "med", {"found": "stale_prices", "next": "critic"}),
            "The worker agent patches task t17 against shared state hash b44e with medium risk and 79 percent confidence. It found stale prices and recommends sending the result to the critic.",
        ),
        (
            ZplsFrame("S1", "synth", "c91a", "done", "t17", 0.91, "low", {"result": "accepted"}),
            "The synthesis agent marks task t17 as accepted against shared state hash c91a with low risk and 91 percent confidence, completing the work.",
        ),
    ],
)
def test_zpls_examples_meet_compactness_target(frame: ZplsFrame, prose: str):
    assert len(serialize_zpls(frame)) <= len(prose) * 0.5


def test_explain_provides_human_readable_escape_hatch():
    explanation = explain_zpls(_frame())
    assert "critic sends eval" in explanation
    assert "pricing_stale" in explanation


@pytest.mark.parametrize(
    "line",
    [
        "§S1 a:critic sh:8f3c op:unknown t:17 c:.72 r:med Δ{next:revise}",
        "§S1 a:critic sh:8f3c op:eval t:17 c:.72 r:huge Δ{next:revise}",
        "§S1 a:critic sh:8f3c op:eval t:17 c:1.2 r:med Δ{next:revise}",
        "§S1 a:critic sh:8f3c op:eval t:17 c:.72 r:med",
        "§S1 a:critic op:eval t:17 c:.72 r:med Δ{next:revise}",
        "§S1 a:critic a:worker sh:8f3c op:eval t:17 c:.72 r:med Δ{next:revise}",
        "§S1 a:critic sh:8f3c foo:bar op:eval t:17 c:.72 r:med Δ{next:revise}",
        "§S1 a:critic sh:8f3c op:eval t:17 c:.72 r:med Δ{next:revise} junk",
        "§S1 a:critic sh:8f3c op:eval t:17 c:.72 r:med Δ{next:revise} Δ{more:1}",
        "§S1 a:critic sh:8f3c op:eval t:17 c:.72000 r:med Δ{next:revise}",
        "§S1 a:critic sh:8f3c op:eval t:17 c:.72 r:med Δ{next:revise,next:again}",
        "§S1 a:critic sh:8f3c op:eval t:17 c:.72 r:med Δ{9bad:revise}",
        "§S1 a:critic sh:8f3c op:eval t:17 c:.72 r:med Δ{next:{step:revise}}",
        "§S1 a:critic sh:8f3c op:eval t:17 c:.72 r:med Δ{next:[revise,[again]]}",
        "§S1 a:critic sh:8f3c op:eval t:17 c:.72 r:med Δ{next:revise,}",
    ],
)
def test_invalid_text_frames_are_rejected(line: str):
    with pytest.raises(ValueError):
        parse_zpls(line)


def test_frame_rejects_nested_delta_objects():
    with pytest.raises(ValueError):
        ZplsFrame("S1", "critic", "8f3c", "eval", "17", 0.72, "med", {"nested": {"x": 1}})


@pytest.mark.parametrize("value", [10**300, 1e260, [10**300], [1e260]])
def test_frame_rejects_delta_numbers_that_cannot_render_as_text(value):
    with pytest.raises(ValueError):
        ZplsFrame("S1", "critic", "8f3c", "eval", "17", 0.72, "med", {"x": value})


def test_text_parser_rejects_oversized_delta_numbers():
    with pytest.raises(ValueError):
        parse_zpls(f"§S1 a:critic sh:8f3c op:eval t:17 c:.72 r:med Δ{{x:{10**300}}}")


@pytest.mark.parametrize(
    "blob",
    [
        b"ZPLS\x01\xff\x04\x02" + _text_field("8f3c") + _text_field("17") + struct.pack("!H", 7200) + _text_field("{}"),
        b"ZPLS\x01\x03",
        b"ZPLS\x01\x03\x04\x02" + _text_field(b"\xff") + _text_field("17") + struct.pack("!H", 7200) + _text_field("{}"),
        b"ZPLS\x01\x03\x04\x02" + b"\x84\x00" + b"8f3c" + _text_field("17") + struct.pack("!H", 7200) + _text_field("{}"),
        b"ZPLS\x01\x03\x04\x02" + _text_field("8f3c") + _text_field("17") + struct.pack("!H", 10001) + _text_field("{}"),
        b"ZPLS\x01\x03\x04\x02" + _text_field("8f3c") + _text_field("17") + struct.pack("!H", 7200) + _text_field("{"),
        b"ZPLS\x01\x03\x04\x02" + _text_field("8f3c") + _text_field("17") + struct.pack("!H", 7200) + _text_field("[]"),
        b"ZPLS\x01\x03\x04\x02" + _text_field("8f3c") + _text_field("17") + struct.pack("!H", 7200) + _text_field('{"x":1,"x":2}'),
        encode_zpls_binary(_frame()) + b"x",
        encode_zpls_binary(_frame())[:-1],
    ],
)
def test_invalid_binary_frames_raise_value_error(blob: bytes):
    with pytest.raises(ValueError):
        decode_zpls_binary(blob)


def test_varint_roundtrip_and_errors():
    for n in [0, 1, 42, 127, 128, 300, 2**32]:
        encoded = encode_varint(n)
        decoded, off = decode_varint(encoded)
        assert decoded == n
        assert off == len(encoded)
    with pytest.raises(ValueError):
        encode_varint(-1)
    for invalid in [True, False, 1.5, "1"]:
        with pytest.raises(ValueError):
            encode_varint(invalid)  # type: ignore[arg-type]
    for offset in [True, False, 0.0, "0"]:
        with pytest.raises(ValueError):
            decode_varint(b"\x00", offset=offset)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        decode_varint("0")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        decode_varint(b"\x00", offset=-1)
    with pytest.raises(ValueError):
        decode_varint(b"\x80")
    for overlong in [b"\x80\x00", b"\x81\x00", b"\xff\x00"]:
        with pytest.raises(ValueError):
            decode_varint(overlong)
