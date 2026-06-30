# ZPL-S Protocol

![status](https://img.shields.io/badge/status-protocol%20kernel-blue)
![python](https://img.shields.io/badge/python-3.11%2B-blue)
![protocol](https://img.shields.io/badge/protocol-ZPL--S%20S1-black)
![license](https://img.shields.io/badge/license-Apache--2.0-green)

AI-machine internet protocol: canonical state frames, Q-matrix logic, HMAC
seals, HTTP Fabric and conformance tests.

ZPL-S ist ein kompaktes, deterministisches Protokoll fuer die Kommunikation
zwischen KI-Systemen, Agenten und Maschinen. Es ist keine Chat-Sprache.
Menschen bekommen Erklaerung, Maschinen bekommen Zustandsframes.

Die Grundidee:

```text
Ein Agent sendet nicht "ich denke vielleicht X, Y oder Z",
sondern einen kanonischen Zustandsvektor.
```

Ein normaler Frame sieht so aus:

```text
§S1 a:critic sh:8f3c op:eval t:17 c:.72 r:med Δ{next:revise,risk:+pricing_stale}
```

## Was Neu Daran Ist

ZPL-S soll nicht nur ein kleineres JSON sein. Es modelliert Maschinenzustand als
Matrix:

- mehrere moegliche Zustaende gleichzeitig,
- verschraenkte Referenzen zwischen Agenten,
- Interferenz zwischen konkurrierenden Pfaden,
- mehrere Layer wie parallele Arbeitswelten,
- deterministischer Kollaps erst bei Beobachtung,
- kompakte Frames statt langer Kontextkopien.

Das ist quantenlogisch inspiriert, aber keine Behauptung ueber echte
Quantenphysik. Es ist ein technisches Protokollmodell: replaybar, testbar und
implementierbar.

## Q-Matrix In Einem Bild

Ein unbeobachteter Zustand:

```text
Δ{ent:[coder.17,critic.17],q:[revise@.37/-.5,ship@.63]}
```

Bedeutung:

- `q` ist der Superpositionsvektor.
- `revise@.37/-.5` bedeutet: Zustand `revise`, Gewicht `0.37`, Phase `-0.5`.
- `ship@.63` bedeutet: Zustand `ship`, Gewicht `0.63`, Phase `0`.
- `ent` sind verschraenkte oder korrelierte entfernte Zustandsreferenzen.

Wenn ein Beobachter explizit wird:

```text
Δ{ent:[coder.17,critic.17],qobs:human,qpick:ship}
```

Dann ist der Zustand kollabiert. Nicht zufaellig, sondern deterministisch aus
kanonischem Frame und Beobachter-ID.

## Layer Und Interferenz

Layer werden als Referenzen codiert:

```text
u0/a
u0/b
u1/x
u1/y
```

Ein Gate ist eine sparse Matrix aus Kanten:

```text
gate:[u0/a=u1/x@.8,u0/b=u1/x@.8,u0/a=u1/y@.2,u0/b=u1/y@.2/-.5]
```

Bedeutung:

- `u0/a=u1/x@.8` leitet Zustand `u0/a` mit Gain `0.8` nach `u1/x`.
- Optionale Phase nach `/` verschiebt die Welle.
- Mehrere Beitraege auf dasselbe Ziel interferieren.
- Das Ergebnis ist wieder ein normaler kompakter Q-Vektor.

Die Mathematik dazu steht in [Q_MATRIX_MATH.md](docs/Q_MATRIX_MATH.md).

## Was Dieses Projekt Enthält

- Python-Paket unter `src/zpls`.
- Strikter Parser und Serializer fuer ZPL-S v1 Textframes.
- Kompakte binaere Repraesentation.
- Stabile semantische Hashes.
- Q-Matrix-Helfer fuer Superposition, Verschraenkung, Layer-Gates,
  Interferenz und Beobachtung.
- HMAC-Sealing fuer unveraenderte, pruefbare Maschinenframes.
- Minimaler Mesh-Kernel mit Agent-Registrierung, Routing, Inbox und Eventlog.
- Internet-Fabric fuer Discovery, Capability-Negotiation, signierte Envelopes
  und Gateway-Routing zwischen fremden Knoten.
- HTTP-Server fuer Discovery, Fabric Receive, Frame Validation und Packaging.
- Conformance-Vektoren fuer unabhaengige Implementierungen.
- Tests fuer Roundtrip, Fehlerfaelle, binaere Aequivalenz und Q-Matrix-Logik.

## Schnellstart

```bash
python3.12 -m venv .venv  # oder eine andere Python-Version >= 3.11
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
pytest -q
zpls conformance
```

## CLI Als Greifbarer Einstieg

Nach der Installation gibt es ein echtes Kommando:

```bash
zpls validate '§S1 a:critic sh:8f3c op:eval t:17 c:.72 r:med Δ{risk:+pricing_stale,next:revise}'
zpls seal --key mesh-secret --key-id mesh '§S1 a:critic sh:8f3c op:eval t:17 c:.72 r:med Δ{next:revise}'
zpls verify --key mesh-secret '§S1 a:critic sh:8f3c op:eval t:17 c:.72 r:med Δ{next:revise,seal:hmac-sha256.mesh.67e4f9326fb04daf57b087a1b1ff45fbbacbbbdb5e52581df8865ec85ce5284e}'
zpls conformance
zpls mesh-demo
zpls fabric-demo
zpls serve --node-id worker.local --endpoint http://127.0.0.1:8787/.well-known/zpls.json --key mesh-secret
```

Q-Zustand bauen, durch ein Gate projizieren und beobachten:

```bash
zpls qmake \
  --agent planner --state 8f3c --op plan --target 17 --confidence .81 --risk med \
  --branches 'u0/a@.5,u0/b@.5/.5'

zpls qgate \
  --frame '§S1 a:planner sh:8f3c op:plan t:17 c:.81 r:med Δ{q:[u0/a@.5,u0/b@.5/.5]}' \
  --edges 'u0/a=u1/x@.8,u0/b=u1/x@.8,u0/a=u1/y@.2,u0/b=u1/y@.2/-.5' \
  --keep-gate

zpls observe \
  --observer human --json \
  '§S1 a:planner sh:8f3c op:plan t:17 c:.81 r:med Δ{q:[u1/x@.6667/.25,u1/y@.3333]}'
```

`mesh-demo` startet keinen Server, aber es zeigt die Runtime-Semantik:
Planner und Worker werden registriert, ein Q-Frame wird beobachtet, kollabiert
und an die Worker-Inbox geroutet.

`fabric-demo` zeigt die Internet-Semantik:

- zwei Knoten veroeffentlichen Discovery-Descriptoren,
- sie handeln gemeinsame Features aus,
- ein Planner packt ein gesiegeltes Frame in ein Internet-Envelope,
- ein Worker-Gateway prueft Seal, TTL und Ziel,
- danach wird das Frame lokal ins Mesh geroutet.

`serve` startet einen lokalen HTTP-Fabric-Knoten:

```text
GET  /health
GET  /.well-known/zpls.json
POST /fabric/receive
POST /fabric/pack
POST /frame/validate
```

```python
from zpls import QBranch, QEdge, apply_qgate, format_qbranches

branches = [
    QBranch("u0/a", .5, 0),
    QBranch("u0/b", .5, .5),
]

gate = [
    QEdge("u0/a", "u1/x", .8, 0),
    QEdge("u0/b", "u1/x", .8, 0),
    QEdge("u0/a", "u1/y", .2, 0),
    QEdge("u0/b", "u1/y", .2, -.5),
]

print(format_qbranches(apply_qgate(branches, gate)))
# ['u1/x@.6667/.25', 'u1/y@.3333']
```

## Wichtige Dokumente

- [Core-Spezifikation](docs/ZPL-S_CORE_SPEC.md)
- [Q-Matrix Mathematik](docs/Q_MATRIX_MATH.md)
- [Conformance-Vektoren](docs/CONFORMANCE_VECTORS.md)
- [Manifest](docs/MANIFEST.md)
- [FAQ](docs/FAQ.md)
- [Launch Brief](docs/LAUNCH.md)
- [Whitepaper](docs/WHITEPAPER.md)
- [GitHub Publishing Guide](docs/GITHUB_PUBLISH.md)
- [Security Policy](SECURITY.md)
- [Contributing](CONTRIBUTING.md)

## Verhältnis Zu MCP / A2A

ZPL-S ersetzt MCP oder A2A nicht.

- MCP bleibt Werkzeug- und Ressourcenzugriff.
- A2A bleibt externe Agenten-Interoperabilitaet.
- ZPL-S ist die interne Zustandsmatrix darunter.

Kurz: MCP holt Werkzeuge. A2A spricht mit fremden Agenten. ZPL-S transportiert
den kompakten Maschinenzustand zwischen den Knoten.
