from __future__ import annotations


def encode_varint(n: int) -> bytes:
    if isinstance(n, bool) or not isinstance(n, int):
        raise ValueError("varint only supports non-negative integers")
    if n < 0:
        raise ValueError("varint only supports non-negative integers")
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def decode_varint(buf: bytes, offset: int = 0) -> tuple[int, int]:
    if not isinstance(buf, (bytes, bytearray, memoryview)):
        raise ValueError("varint buffer must be bytes-like")
    if isinstance(offset, bool) or not isinstance(offset, int):
        raise ValueError("varint offset must be a non-negative integer")
    if offset < 0:
        raise ValueError("varint offset must be a non-negative integer")
    start = offset
    shift = 0
    result = 0
    while True:
        if offset >= len(buf):
            raise ValueError("incomplete varint")
        b = buf[offset]
        offset += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            if offset - start != len(encode_varint(result)):
                raise ValueError("non-canonical varint")
            return result, offset
        shift += 7
        if shift > 63:
            raise ValueError("varint too long")
