# Q-Matrix Mathematik

Diese Datei beschreibt die mathematische Schicht von ZPL-S. Sie ist
quantenlogisch inspiriert, aber keine Simulation echter Quantenphysik. Ziel ist
ein deterministisches, effizientes und implementierbares Protokoll fuer
Maschinenzustand.

## 1. Feste Skala

Alle Wahrscheinlichkeits- und Phasenwerte werden fuer die Wire-Semantik als
Q4-Festkommawerte behandelt:

```text
Q = 10000
1.0 = 10000
.5  = 5000
.0001 = 1
```

Damit haengt die Protokollsemantik nicht an Float-Details einer Sprache.

## 2. Zustandsvektor

Ein Q-Zustand ist ein sparse Vektor:

```text
psi = [(ref_i, weight_i, phase_i)]
```

Beispiel:

```text
q:[u0/a@.5,u0/b@.5/.5]
```

Bedeutung:

- `u0/a` und `u0/b` sind moegliche Maschinenzustaende.
- `u0` ist ein Layer oder eine Parallelwelt.
- `weight_i` ist das Q4-Gewicht.
- `phase_i` ist die Wellenphase im Bereich `[-1, 1]`.

Norm:

```text
sum(weight_i) = 10000
```

## 3. Verschraenkung

Verschraenkung ist eine Korrelation von entfernten Zustandsreferenzen:

```text
ent:[coder.17,critic.17]
```

Das bedeutet nicht, dass Daten kopiert werden. Es bedeutet:

```text
Dieser lokale Zustand ist semantisch an diese entfernten Slots gekoppelt.
```

Eine Implementierung kann damit entscheiden, welche entfernten Slots bei
Beobachtung, Audit oder Synchronisation gemeinsam betrachtet werden muessen.

## 4. Sparse Gate Matrix

Ein Gate ist eine sparse Matrix aus gerichteten Kanten:

```text
edge = (src, dst, gain, phase_shift)
```

Wire-Form:

```text
src=dst@gain[/phase_shift]
```

Beispiel:

```text
gate:[u0/a=u1/x@.8,u0/b=u1/x@.8,u0/a=u1/y@.2,u0/b=u1/y@.2/-.5]
```

Das ist analog zu einer neuronalen Layer-Transformation:

```text
u0 -> u1
```

aber mit Wellenphase und Interferenz.

## 5. Projektion Durch Ein Gate

Fuer jeden Branch `i` und jede Kante `i -> j`:

```text
mass_ij  = round(weight_i * gain_ij / Q)
phase_ij = wrap(phase_i + phase_shift_ij)
```

`wrap` bildet Phasen wieder auf `[-Q, Q)` ab.

## 6. Interferenz

Alle Beitraege auf dasselbe Ziel `j` werden gruppiert.

Fuer zwei Beitraege `a` und `b`:

```text
distance  = circular_distance(phase_a, phase_b)
coherence = Q - 2 * distance
```

Damit gilt:

```text
gleiche Phase      -> coherence = +Q
halbe Verschiebung -> coherence = 0
Gegenphase         -> coherence = -Q
```

Die Rohmasse eines Zielzustands:

```text
raw_j = sum(mass_i) + sum_pairwise(2 * min(mass_a, mass_b) * coherence / Q)
raw_j = max(0, raw_j)
```

Danach werden alle `raw_j` wieder auf `sum = Q` normiert.

## 7. Beobachtung

Unbeobachtet bleibt der Zustand als Vektor:

```text
q:[revise@.37/-.5,ship@.63]
```

Wenn ein Beobachter explizit wird:

```text
observer = "human"
```

wird deterministisch kollabiert:

```text
material = canonical_json({"frame": frame.canonical(), "observer": observer})
digest64 = first16hex(sha256(material))
bucket   = floor(int(digest64, 16) * Q / 16^16)
```

Die Branches werden in kanonischer Reihenfolge aufsummiert. Der erste Branch,
bei dem

```text
bucket < cumulative_weight
```

gilt, wird `qpick`.

Das ist kein Zufall. Es ist beobachtergebundene, replaybare Materialisierung.

## 8. Warum Das Fuer KI-Agenten Sinn Ergibt

Ein LLM- oder Agentensystem hat oft mehrere plausible naechste Schritte:

```text
revise
ship
ask_human
escalate
```

Normale Protokolle zwingen zu fruehem Commit. ZPL-S kann diese Alternativen
kompakt transportieren, von anderen Agenten transformieren lassen, ueber Layer
projizieren und erst beim menschlichen oder systemischen Beobachter materialisieren.

Kurz:

```text
denken:   mehrere Zustaende
kommunizieren: kompakter Vektor
verarbeiten: Matrix/Gate
beobachten: deterministischer Kollaps
```
