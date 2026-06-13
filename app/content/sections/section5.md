# Basic Electronics and Theory

This is the math core of the exam, and where the interactive tools below earn
their keep. The exam's numerical questions almost all reduce to a handful of
relationships — get fluent moving between them.

**Ohm's Law and power.** `V = I·R` ties voltage, current and resistance; power is
`P = V·I`, which combines with Ohm's law into `P = I²·R = V²/R`. Two of the four
quantities always give you the other two — that's exactly what the **Ohm's Law &
Power** tool lets you feel.

**Series and parallel.** Resistances **add in series**; in parallel the
conductances add, so the combination is always smaller than the smallest branch.
Capacitors do the opposite (add in parallel, combine reciprocally in series), and
inductors behave like resistors. Series circuits share current; parallel circuits
share voltage.

**AC, reactance and resonance.** Capacitors and inductors oppose AC with
**reactance**, not resistance: `X_C = 1/(2πfC)` falls with frequency, while
`X_L = 2πfL` rises. Where they're equal the circuit is at **resonance**,
`f = 1/(2π√(LC))` — the basis of every tuned circuit and filter. **Q** measures
how sharp that resonance is. The **Reactance & Resonance** tool plots both curves
so you can watch them cross.

**Decibels.** Gains and losses multiply, so we add them in **dB**: `dB = 10·log₁₀(P₂/P₁)`
for power (use 20·log for voltage). A 3 dB change doubles/halves power; 10 dB is
×10; and on the S-meter **6 dB ≈ one S-unit**. The **Decibel** tool converts both
ways with worked S-unit examples.
