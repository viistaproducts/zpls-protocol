# ZPL-S Conformance-Vektoren

Diese Vektoren sind normative Beispiele fuer unabhaengige Implementierungen.
Eine kompatible Implementierung muss denselben kanonischen Text, dieselben
semantischen Hashes, dasselbe binaere Encoding, dasselbe Q-Beobachtungsmaterial
und denselben Beobachtungs-Bucket erzeugen.

## Vektor 1: Core Text/Binaerframe

Eingabetext:

```text
§S1 a:critic sh:8f3c op:eval t:17 c:.72 r:med Δ{risk:+pricing_stale,next:revise}
```

Kanonischer Text:

```text
§S1 a:critic sh:8f3c op:eval t:17 c:.72 r:med Δ{next:revise,risk:+pricing_stale}
```

Semantischer Hash, Laenge 12:

```text
ab45ff627ee8
```

Binaer-Hex:

```text
5a504c530103040204386633630231371c20297b226e657874223a22726576697365222c227269736b223a222b70726963696e675f7374616c65227d
```

## Vektor 2: Q-Matrix-Beobachtung

Unbeobachteter kanonischer Text:

```text
§S1 a:planner sh:8f3c op:plan t:17 c:.81 r:med Δ{ent:[coder.17,critic.17],q:[revise@.37/-.5,ship@.63]}
```

Semantischer Hash, Laenge 12:

```text
911b59bcd4ce
```

Binaer-Hex:

```text
5a504c530101060204386633630231371fa4427b22656e74223a5b22636f6465722e3137222c226372697469632e3137225d2c2271223a5b22726576697365402e33372f2d2e35222c2273686970402e3633225d7d
```

Beobachter:

```text
human
```

Beobachtungsmaterial:

```json
{"frame":{"agent":"planner","confidence":0.81,"delta":{"ent":["coder.17","critic.17"],"q":["revise@.37/-.5","ship@.63"]},"op":"plan","risk":"med","state_hash":"8f3c","target":"17","version":"S1"},"observer":"human"}
```

SHA-256:

```text
dfb34f9465e4e61968ee6fee6279472c6f46b85a39a1cee2d3df474cb4d9fbf1
```

Beobachtungs-Bucket:

```text
8738
```

Beobachteter kanonischer Text:

```text
§S1 a:planner sh:8f3c op:plan t:17 c:.81 r:med Δ{ent:[coder.17,critic.17],qobs:human,qpick:ship}
```

Beobachteter semantischer Hash, Laenge 12:

```text
1b02f134f21b
```

Beobachtetes Binaer-Hex:

```text
5a504c530101060204386633630231371fa43e7b22656e74223a5b22636f6465722e3137222c226372697469632e3137225d2c22716f6273223a2268756d616e222c22717069636b223a2273686970227d
```

## Vektor 3: Q-Gate Layer-Projektion

Eingangsbranches:

```text
q:[u0/a@.5,u0/b@.5/.5]
```

Sparse Gate:

```text
gate:[u0/a=u1/x@.8,u0/a=u1/y@.2,u0/b=u1/x@.8,u0/b=u1/y@.2/-.5]
```

Projizierter kanonischer Text:

```text
§S1 a:planner sh:8f3c op:plan t:17 c:.81 r:med Δ{gate:[u0/a=u1/x@.8,u0/a=u1/y@.2,u0/b=u1/x@.8,u0/b=u1/y@.2/-.5],q:[u1/x@.6667/.25,u1/y@.3333]}
```

Semantischer Hash, Laenge 12:

```text
0a56b1189f1a
```

Binaer-Hex:

```text
5a504c530101060204386633630231371fa46e7b2267617465223a5b2275302f613d75312f78402e38222c2275302f613d75312f79402e32222c2275302f623d75312f78402e38222c2275302f623d75312f79402e322f2d2e35225d2c2271223a5b2275312f78402e363636372f2e3235222c2275312f79402e33333333225d7d
```

## Vektor 4: HMAC-Seal

Eingangsframe:

```text
§S1 a:critic sh:8f3c op:eval t:17 c:.72 r:med Δ{next:revise,risk:+pricing_stale}
```

Key-ID:

```text
mesh
```

Key:

```text
mesh-secret
```

Seal-Material:

```json
{"agent":"critic","confidence":0.72,"delta":{"next":"revise","risk":"+pricing_stale"},"op":"eval","risk":"med","state_hash":"8f3c","target":"17","version":"S1"}
```

Gesiegelter kanonischer Text:

```text
§S1 a:critic sh:8f3c op:eval t:17 c:.72 r:med Δ{next:revise,risk:+pricing_stale,seal:hmac-sha256.mesh.625afd328670f6d36300c16b871cbc0059e57525a49da0332e282816c0db8b2c}
```

Semantischer Hash, Laenge 12:

```text
5c0eb2ef8627
```

Binaer-Hex:

```text
5a504c530103040204386633630231371c2084017b226e657874223a22726576697365222c227269736b223a222b70726963696e675f7374616c65222c227365616c223a22686d61632d7368613235362e6d6573682e36323561666433323836373066366433363330306331366238373163626330303539653537353235613439646130333332653238323831366330646238623263227d
```

Verifikation mit `mesh-secret` muss erfolgreich sein. Verifikation mit einem
anderen Key oder nach semantischer Veraenderung des Frames muss fehlschlagen.

## Vektor 5: Internet-Fabric Envelope

Planner-Descriptor:

```json
{"endpoint":"https://planner.example/.well-known/zpls.json","fabric_version":"F1","features":["binary","mesh","qgate","qmatrix","seal"],"node_id":"planner.example","operations":["ack","done","escalate","eval","patch","plan","task"],"protocol_versions":["S1"],"roles":["planner"],"seal_key_ids":["mesh"],"transports":["https+json"]}
```

Worker-Descriptor:

```json
{"endpoint":"https://worker.example/.well-known/zpls.json","fabric_version":"F1","features":["binary","mesh","qgate","qmatrix","seal"],"node_id":"worker.example","operations":["ack","done","escalate","eval","patch","plan","task"],"protocol_versions":["S1"],"roles":["worker"],"seal_key_ids":["mesh"],"transports":["https+json"]}
```

Agreement:

```json
{"features":["binary","mesh","qgate","qmatrix","seal"],"operations":["ack","done","escalate","eval","patch","plan","task"],"protocol_version":"S1","seal_key_ids":["mesh"],"transport":"https+json"}
```

Envelope:

```json
{"content_type":"application/zpls+text","created_at":1,"destination":"worker.example","fabric_version":"F1","frame":"§S1 a:planner sh:8f3c op:plan t:17 c:.91 r:low Δ{next:worker,seal:hmac-sha256.mesh.416cc99c44fcfef70c345d03112cdaeca1cd5b4b4ee8591ba8e38e42e60acd5d}","frame_hash":"4a66dcefb21e","route":["planner.example"],"source":"planner.example","trace_id":"trace.demo","ttl":60}
```

Receipt:

```json
{"accepted":true,"destination":"worker.example","frame_hash":"4a66dcefb21e","reason":"delivered","receiver":"worker","source":"planner.example","trace_id":"trace.demo"}
```

Replay-Receipt fuer dasselbe Envelope im selben Gateway:

```json
{"accepted":false,"destination":"worker.example","frame_hash":"4a66dcefb21e","reason":"replay","receiver":null,"source":"planner.example","trace_id":"trace.demo"}
```

## Vektor 6: CLI/Mesh-Mindestverhalten

Der Befehl

```bash
zpls conformance
```

muss ein JSON mit `"ok": true` ausgeben.

Der Befehl

```bash
zpls mesh-demo
```

muss ein akzeptiertes Event mit Empfaenger `worker` ausgeben. Das Frame in
`worker_inbox[0]` muss exakt dem Feld `frame` entsprechen und einen
beobachteten Q-Zustand mit `qobs:human` und `qpick:<state>` enthalten. Welcher
Branch ausgewaehlt wird, ist deterministisch vom vollstaendigen Frame-Material
abhaengig.
