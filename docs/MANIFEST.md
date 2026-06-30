# ZPL-S Manifest

## Ein Satz

ZPL-S ist eine kompakte, kanonische und deterministische Zustandsmatrix fuer
KI-Agenten und Maschinen: Frames tragen Rollen, Operationen, Zustandsreferenzen,
Deltas, Vertrauen, Risiko, Sichtbarkeit und Q-Matrix-Zustaende.

## Positionierung

ZPL-S ist nicht MCP und nicht A2A.

- MCP ist Werkzeug-, Ressourcen- und Kontextzugriff.
- A2A ist externe Agenten-Kommunikation.
- ZPL-S ist die interne Matrixschicht darunter.

Das Protokoll soll verhindern, dass Agenten lange Prosa oder ganze Kontexte
hin- und herschieben. Stattdessen senden sie kompakte, hashbare,
delta-basierte und q-matrix-faehige Zustandsframes.

## Axiome

1. Prosa ist fuer Menschen. Zustand ist fuer Maschinen.
2. Alles, was aus gemeinsamem Zustand ableitbar ist, ist Protokollrauschen.
3. Agenten senden typisierte Operationen, keine Stimmungen.
4. Zustand wird referenziert, nicht kopiert.
5. Deltas schlagen Vollkontext, wenn Referenz plus Delta kleiner ist.
6. Vertrauen und Risiko sind getrennte Signale.
7. Sensibler Kontext darf nicht versehentlich propagieren.
8. Maschinenzustand darf unbeobachtet in mehreren Zustaenden bleiben.
9. Beobachtung ist ein explizites Protokollereignis.
10. Interferenz ist eine deterministische Matrixoperation, kein Zufall.
11. Layer koennen selbst Superpositionen sein und mit States Tensorfelder bilden.
12. Maschinenframes muessen bei Bedarf gesiegelt und pruefbar sein.
13. Fremde Knoten muessen ihre Faehigkeiten aushandeln, bevor sie Zustandsframes
    austauschen.
14. Jede Entscheidung muss fuer Menschen erklaerbar sein.

## Die Acht Schichten

1. Kanonischer semantischer Frame:
   Wahrheit fuer Validierung, Hashing, Signierung, Rendering und Tests.
2. Textframe:
   kompakte LLM-, Debug- und Log-Repraesentation.
3. Binaerframe:
   kompakter Maschinentransport.
4. Q-Matrix / Q-Field:
   Superposition, Phase, Layer-Felder, Tensorprodukt,
   Verschraenkungsreferenzen und Beobachtung.
5. Sparse Gate Matrix:
   neuronale/wellenartige Uebergaenge zwischen Layern oder Parallelwelten.
6. Mesh-Kernel:
   Registrierung, Routing, Inbox, Eventlog und State-Referenzen fuer konkrete
   Ausfuehrung.
7. Seal-Schicht:
   HMAC-Integritaet ueber die kanonische Frame-Semantik.
8. Internet-Fabric:
   Discovery, Capability-Negotiation, Envelope, TTL, Receipt und Gateway-Routing.

## Mathematisches Leitbild

Ein Frame kann einen Zustandsvektor tragen:

```text
q:[u0/a@.5,u0/b@.5/.5]
```

Ein Gate beschreibt eine sparse Matrix:

```text
gate:[u0/a=u1/x@.8,u0/b=u1/x@.8,u0/a=u1/y@.2,u0/b=u1/y@.2/-.5]
```

Die Matrix projiziert den Zustand aus Layer `u0` nach Layer `u1`.
Beitraege auf dasselbe Ziel interferieren ueber ihre Phasen. Danach wird wieder
auf einen Q4-normalisierten Zustandsvektor normiert.

Ein Q-Field kann zusaetzlich Layer als eigene Superposition tragen:

```text
ql:[prod@.45/-.25,sim@.55/.25]
```

Das Tensorprodukt aus `q` und `ql` macht parallele Arbeitswelten als kompakte,
hashbare Maschinenmatrix sichtbar.

## Ziele

- Text- und Binaerframes muessen kanonisch rundreisen.
- Semantische Hashes muessen stabil sein.
- Q-Zustaende muessen vor und nach Beobachtung replaybar sein.
- Q-Fields muessen State- und Layerachsen deterministisch tensorisieren koennen.
- Q-Gates muessen mit fester Q4-Integerarithmetik berechenbar sein.
- Ein minimaler Mesh-Kernel muss Frames real an Agent-Inboxes routen koennen.
- Die CLI muss Validierung, Conformance, Q-Gates, Beobachtung und Mesh-Demo
  ausfuehrbar machen.
- Gesiegelte Frames muessen bei jeder semantischen Veraenderung invalidieren.
- Internet-Knoten muessen Discovery-Descriptoren, signierte Envelopes und
  Receipts interoperabel erzeugen koennen.
- Conformance-Vektoren muessen unabhaengige Implementierungen pruefbar machen.
- Fehler muessen geschlossen fehlschlagen.
- Menschen muessen erklaeren koennen, warum ein Zustand kollabiert ist.

## Roadmap

1. S1 Parser, Serializer, binaerer MVP, Hash und Erklaerung.
2. Q-Matrix/Q-Field mit Superposition, Layern, Phase, Verschraenkung und Beobachtung.
3. Sparse Gate Matrix fuer Layer, Interferenz und neuralartige Uebergaenge.
4. CLI und Mesh-Kernel als greifbare Referenzausfuehrung.
5. HMAC-Sealing und Mesh-Policy fuer Integritaet.
6. Internet-Fabric fuer fremde Knoten, Gateways und Maschinen.
7. Formale ABNF fuer Textframes.
8. CDDL/CBOR fuer produktionsreife binaere Frames.
9. Capability Negotiation fuer verschiedene Agenten-Versionen.
10. Fehlerkatalog mit stabilen Fehlercodes.
11. Fuzz- und Property-Tests.
12. Bridges zu AI Mesh, A2A und MCP.
