# ZPL-S Core-Spezifikation

Version: `S1`

ZPL-S ist ein kompaktes, deterministisches Frame-Protokoll fuer interne
KI-zu-KI- und Maschine-zu-Maschine-Koordination. Normative Wahrheit ist der
kanonische semantische Frame, nicht die Prosa und nicht eine zufaellige
Textdarstellung.

## 1. Kanonischer Frame

Pflichtfelder in S1:

- `version`: Protokollversion, aktuell `S1`.
- `agent`: sendende Rolle oder kompakte Agent-ID.
- `state_hash`: Referenz auf gemeinsamen Zustand.
- `op`: Operation.
- `target`: Task, Graph-Knoten, Thread oder Slot.
- `confidence`: Zahl in `[0, 1]`.
- `risk`: Risikoklasse.
- `delta`: kompakte Zustandsaenderung.

Die kanonische Darstellung sortiert Objektkeys, rundet Zahlen auf vier
Dezimalstellen und serialisiert ohne irrelevante Leerzeichen.

Die Q-Matrix liegt in `delta`. Sie ist damit Teil desselben semantischen
Frames und wird gleich gehasht, signiert und getestet.

## 2. Operationen

Normative S1-Operationen:

```text
plan task ack eval patch done escalate
```

Reservierte zukuenftige Operationen:

```text
query nack cancel defer handoff sync invalid
```

## 3. Textframe

Kanonische Textreihenfolge:

```text
§S1 a:<agent> sh:<state_hash> op:<op> t:<target> c:<confidence> r:<risk> Δ{<delta>}
```

Beispiel:

```text
§S1 a:critic sh:8f3c op:eval t:17 c:.72 r:med Δ{next:revise,risk:+pricing_stale}
```

Regeln:

- Genau ein `Δ{...}`-Block.
- Keine Tokens nach der schliessenden `}`.
- Headerkeys sind exakt `a`, `sh`, `op`, `t`, `c`, `r`.
- Doppelte oder unbekannte Headerkeys sind ungueltig.
- Deltakeys sind eindeutige ASCII-Identifier und beginnen mit einem Buchstaben.
- Delta-Werte in S1 sind Skalare oder Listen von Skalaren.
- Verschachtelte Objekte und verschachtelte Listen sind in S1-Textframes ungueltig.

## 4. Q-Matrix-Overlay

Die ZPL-S Q-Matrix ist quantenlogisch inspiriert, aber keine Behauptung ueber
echte Quantenphysik. Sie gibt Agenten eine kompakte Methode, mehrere moegliche
Maschinenzustaende gleichzeitig zu tragen, ueber Agenten zu koppeln und erst
bei expliziter Beobachtung zu materialisieren.

Reservierte Q-Deltakeys:

```text
q      Superpositionsvektor
ql     Layer-Superpositionsvektor
ent    verschraenkte oder korrelierte entfernte Zustandsreferenzen
qobs   Beobachter-ID des Kollapses
qpick  ausgewaehlter Zustand nach Beobachtung
qphase optionale Phase des ausgewaehlten Zustands
qlpick ausgewaehlter Layer nach Beobachtung
qlphase optionale Phase des ausgewaehlten Layers
qcoh   Q-Field-Kohaerenz nach Tensorprojektion
gate   sparse Q-Matrix-Kanten
```

`q` ist eine Liste von Branch-Tokens:

```text
<state_ref>@<weight>[/<phase>]
```

`gate` ist eine Liste von Kanten-Tokens:

```text
<src_ref>=<dst_ref>@<gain>[/<phase_shift>]
```

`ql` ist eine Liste von Layer-Tokens:

```text
<layer_ref>@<weight>[/<phase>]
```

Regeln:

- `state_ref` ist eine kompakte skalare Referenz.
- `weight` liegt in `(0, 1]`.
- Branch-Gewichte verwenden Q4-Festkomma: `1.0 == 10000`.
- Branch-Gewichte muessen nach Kanonisierung exakt `10000` Q4-Einheiten ergeben.
- Layer-Gewichte verwenden dieselbe Q4-Skala und muessen ebenfalls exakt
  `10000` Q4-Einheiten ergeben.
- `phase` ist optional und liegt in `[-1, 1]`.
- Branch-Refs sind eindeutig und werden kanonisch nach Ref sortiert.
- Layer-Refs sind eindeutig und werden kanonisch nach Ref sortiert.
- `ent`-Refs sind eindeutig und werden kanonisch sortiert.
- Unbeobachtete Frames tragen `q`.
- Unbeobachtete Q-Fields tragen `q` plus `ql`.
- Beobachtete Frames entfernen `q` und `ql` und tragen `qobs`, `qpick` und
  optional `qlpick`.
- API-Eingaben duerfen numerisch sein; Wire-Tokens sind Dezimaltext mit maximal
  vier Nachkommastellen.
- Wire-Tokens mit mehr als vier Nachkommastellen sind ungueltig.
- Ein `gate` ist eine sparse Uebergangsmatrix ueber Q-State-Refs.
- Gate-Refs duerfen Layerpraefixe wie `u0/a` und `u1/x` tragen.
- Ein Gate projiziert einen Q-Vektor in einen neuen Q-Vektor.
- Beitraege auf dasselbe Ziel interferieren ueber ihre Phase vor der Normierung.
- Ein Q-Field bildet das Tensorprodukt aus States und Layern. Ein State
  `revise@.4/-.25` und ein Layer `prod@.45/-.25` ergeben den Tensorbranch
  `prod/revise@.18/-.5`.
- `qcoh` ist die Q4-normalisierte mittlere Phasenkohaerenz des Tensorfelds.

Unbeobachteter Beispielzustand:

```text
§S1 a:planner sh:8f3c op:plan t:17 c:.81 r:med Δ{ent:[coder.17,critic.17],q:[revise@.37/-.5,ship@.63]}
```

Beobachteter Beispielzustand:

```text
§S1 a:planner sh:8f3c op:plan t:17 c:.81 r:med Δ{ent:[coder.17,critic.17],qobs:human,qpick:ship}
```

Beobachtung ist deterministisch. Implementierungen muessen berechnen:

```text
material = canonical_json({"frame": frame.canonical(), "observer": observer})
digest64 = erste 16 Hex-Zeichen von sha256(material)
bucket   = floor(int(digest64, 16) * 10000 / 16^16)
```

Branches werden in kanonischer Ref-Reihenfolge summiert. Der erste Branch, fuer
den `bucket < cumulative_weight_q4` gilt, wird ausgewaehlt. So entsteht
verspaetete Materialisierung ohne nicht-replaybaren Zufall.

Wenn ein Frame `ql` traegt, muss die Layerbeobachtung eine getrennte Achse
verwenden:

```text
material = canonical_json({"axis":"layer","frame":frame.canonical(),"observer":observer})
```

Der resultierende Bucket wird ueber die kanonisch sortierten Layer summiert und
ergibt `qlpick`.

## 5. Mesh-Kernel

Die Referenzimplementierung enthaelt einen kleinen ausfuehrbaren Mesh-Kernel:

- `ZplsMesh.register(agent_id, role)` registriert Agenten.
- `ZplsMesh.route(frame, sender, observer)` validiert den Sender, beobachtet
  optional einen Q-Zustand und routet an die naechste Inbox.
- Routing erfolgt zuerst ueber `delta.next`, dann ueber direktes `target`, dann
  ueber eine Operation-zu-Rolle-Tabelle.
- Jedes Routing erzeugt ein `RouteEvent` mit `frame_hash`, Sender, Empfaenger,
  Akzeptanz und Grund.
- `ZplsMesh.state_ref()` hasht kanonischen Mesh-Zustand und liefert eine
  kompakte State-Referenz.

Das ist keine verteilte Serverplattform. Es ist der kleinste produktive
Ausfuehrungskern, gegen den externe Implementierungen ihr Verhalten abgleichen
koennen.

## 6. Seal

ZPL-S S1 kann Frames mit einem HMAC-SHA256-Seal versehen. Das Seal ist keine
Verschluesselung. Es beweist Integritaet und gemeinsame Schluesselkenntnis.

Reservierter Deltakey:

```text
seal
```

Wire-Form:

```text
seal:hmac-sha256.<key_id>.<mac_hex_64>
```

Normative Regeln:

- Der MAC wird ueber den kanonischen Frame ohne `delta.seal` berechnet.
- `material = canonical_json(strip_seal(frame).canonical())`
- `mac = hmac_sha256(key, utf8(material)).hexdigest()`
- `key_id` ist ein ASCII-Token mit maximal 64 Zeichen aus `A-Z a-z 0-9 _ . -`.
- `mac` ist exakt 64 Zeichen lowercase Hex.
- Veraendert sich irgendein semantisches Feld, muss die Verifikation fehlschlagen.
- Beobachtung eines Q-Zustands veraendert den Frame. Ein Mesh, das beobachtet,
  muss danach neu siegeln, wenn es gesicherte Zustellung verlangt.
- Ein Seal ist nicht geheim. Der Schluessel ist geheim.

Beispiel:

```text
§S1 a:critic sh:8f3c op:eval t:17 c:.72 r:med Δ{next:revise,risk:+pricing_stale,seal:hmac-sha256.mesh.625afd328670f6d36300c16b871cbc0059e57525a49da0332e282816c0db8b2c}
```

## 7. Internet-Fabric

Die Internet-Fabric ist die interoperable Huelle fuer fremde Knoten. Sie macht
aus lokalen Frames adressierbare, pruefbare Nachrichten zwischen Diensten,
Maschinen, Agenten und Gateways.

### Discovery-Descriptor

Ein Knoten kann unter einem bekannten HTTPS-Endpunkt, z.B.
`/.well-known/zpls.json`, einen Descriptor veroeffentlichen:

```json
{"endpoint":"https://worker.example/.well-known/zpls.json","fabric_version":"F1","features":["binary","mesh","qfield","qgate","qmatrix","seal"],"node_id":"worker.example","operations":["ack","done","escalate","eval","patch","plan","task"],"protocol_versions":["S1"],"roles":["worker"],"seal_key_ids":["mesh"],"transports":["https+json"]}
```

Normative Felder:

- `fabric_version`: aktuell `F1`.
- `node_id`: stabile Internet-Node-ID.
- `endpoint`: HTTP(S)-Endpoint fuer Fabric-Nachrichten oder Discovery.
- `protocol_versions`: unterstuetzte ZPL-S-Versionen.
- `transports`: z.B. `https+json`.
- `roles`: lokale Rollen, die der Knoten routen kann.
- `operations`: akzeptierte Operationen.
- `features`: z.B. `qfield`, `qmatrix`, `qgate`, `seal`, `binary`, `mesh`.
- `seal_key_ids`: bekannte Key-IDs fuer gesiegelte Frames.

### Capability-Negotiation

Zwei Knoten bilden eine Schnittmenge aus Version, Transport, Operationen,
Features und Seal-Key-IDs. Gibt es keine gemeinsame Version, keinen gemeinsamen
Transport oder keine gemeinsamen Operationen, muss die Verbindung abgelehnt
werden.

### Envelope

Ein Internet-Envelope traegt genau einen ZPL-S-Textframe:

```json
{"content_type":"application/zpls+text","created_at":1,"destination":"worker.example","fabric_version":"F1","frame":"§S1 a:planner sh:8f3c op:plan t:17 c:.91 r:low Δ{next:worker,seal:hmac-sha256.mesh.416cc99c44fcfef70c345d03112cdaeca1cd5b4b4ee8591ba8e38e42e60acd5d}","frame_hash":"4a66dcefb21e","route":["planner.example"],"source":"planner.example","trace_id":"trace.demo","ttl":60}
```

Normative Regeln:

- `frame_hash` muss `semantic_hash(frame)` entsprechen.
- `created_at + ttl` begrenzt die Gueltigkeit.
- `destination` muss zur lokalen Node-ID passen oder `*` sein.
- Wenn `require_seal` gilt, muss das Frame ein gueltiges `seal` tragen.
- Ein Gateway mit Replay-Schutz muss `source + trace_id + frame_hash` bis zum
  Ende der Envelope-Gueltigkeit merken und identische Wiederholungen mit
  `reason:"replay"` ablehnen.
- Der Gateway prueft das externe Seal, entfernt es fuer lokales Routing und
  quittiert trotzdem den Hash des urspruenglichen Envelopes.
- `trace_id` bleibt ueber Knoten hinweg stabil.

### Receipt

Empfang erzeugt eine Quittung:

```json
{"accepted":true,"destination":"worker.example","frame_hash":"4a66dcefb21e","reason":"delivered","receiver":"worker","source":"planner.example","trace_id":"trace.demo"}
```

### HTTP Binding

Die Referenzimplementierung stellt ein minimales HTTP-Binding bereit:

```text
GET  /health
GET  /.well-known/zpls.json
POST /fabric/receive
POST /fabric/pack
POST /frame/validate
```

Regeln:

- JSON-Antworten verwenden `application/json; charset=utf-8`.
- `/.well-known/zpls.json` liefert den Node-Descriptor.
- `/fabric/receive` nimmt ein Fabric-Envelope entgegen und liefert ein Receipt.
- `/fabric/pack` packt ein lokales Frame in ein Envelope.
- `/frame/validate` validiert einen Textframe und gibt kanonischen Text plus
  Frame-Hash zurueck.

## 8. Binaerframe

Der aktuelle binaere MVP nutzt:

```text
magic("ZPLS") + version + coded agent/op/risk + state_hash + target + confidence + canonical_delta_json
```

Bekannte Rollen, Operationen und Risiken verwenden Ein-Byte-Symbole. Unbekannte
Agentennamen roundtrippen als laengenpraefigierte UTF-8-Strings.

Produktionsrichtung: deterministisches CBOR mit Integer-Labels und CDDL-Schema.
Labels `0..15` sind fuer Kernfelder reserviert:

```text
0 version
1 frame_id
2 trace_id
3 parent_id
4 agent_role
5 op
6 target
7 state_ref
8 confidence
9 risk
10 delta
11 visibility
12 budget
13 ttl
14 seal
15 error
```

Numerische Labels duerfen nie recycelt werden.

## 9. State-Referenzen

Die produktive Form einer State-Referenz soll sein:

```text
st:<alg>/<display_bits>:<digest>[:slotset]
```

Beispiel:

```text
st:sh256/96:1f2a9c44be61c0d39c4e2a71:plan.17,market.pricing
```

Intern sollten volle SHA-256-Digests erhalten bleiben. Textframes duerfen fuer
Debugging kurze Praefixe zeigen.

## 10. Delta-Algebra

Vorgesehene S1.1-Deltaoperationen:

```text
+path=value      add
~path=value      replace
-path            remove
!path            invalidate
?path            need/request missing value
```

Beispiel:

```text
Δ{!market.pricing,+risk.pricing_stale,~next=revise_pricing,?source.price_feed}
```

## 11. Sicherheit

- ZPL-S ist keine natuerliche Sprache.
- ZPL-S-Text ist keine Verschluesselung.
- Sensibler Zustand muss explizit `local`, `redacted`, versiegelt oder in eine
  freigebbare Substate-View projiziert werden, bevor externe Provider ihn sehen.
- Hochriskante oder unsichere Transitionen muessen `risk` und ggf.
  `op:escalate` verwenden.
- Langlaufende Systeme muessen Budget-, Kosten- und Turnlimits ausserhalb des
  Frame-Parsers erzwingen.

Conformance-Vektoren stehen in `docs/CONFORMANCE_VECTORS.md`.
Das mathematische Modell steht in `docs/Q_MATRIX_MATH.md`.
