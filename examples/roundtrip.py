from __future__ import annotations

from zpls import decode_zpls_binary, encode_zpls_binary, explain_zpls, parse_zpls, serialize_zpls


line = "§S1 a:critic sh:8f3c op:eval t:17 c:.72 r:med Δ{risk:+pricing_stale,next:revise}"
frame = parse_zpls(line)
blob = encode_zpls_binary(frame)
restored = decode_zpls_binary(blob)

print(serialize_zpls(restored))
print(f"{len(blob)} bytes")
print(explain_zpls(restored))
