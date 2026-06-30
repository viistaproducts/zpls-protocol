from zpls import parse_zpls, seal_zpls_frame, serialize_zpls, verify_zpls_seal


frame = parse_zpls("§S1 a:critic sh:8f3c op:eval t:17 c:.72 r:med Δ{next:revise,risk:+pricing_stale}")
sealed = seal_zpls_frame(frame, "mesh-secret", key_id="mesh")

print(serialize_zpls(sealed))
print(verify_zpls_seal(sealed, {"mesh": "mesh-secret"}))
