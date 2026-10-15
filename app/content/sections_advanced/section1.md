# Advanced Theory

The Basic exam asked *what* a reactance is; the Advanced exam asks you to
**compute with it** — time constants, resonance, Q and bandwidth, with real
component values. Every numeric question in this section reduces to four
relationships. Know them cold, and know what each one *does* when you change an
input.

**Time constants.** A capacitor charging through a resistor, or a current rising
through an inductor, follows an exponential with a characteristic time
`τ = R·C` (seconds, ohms, farads) or `τ = L / R` (henries over ohms). In one τ
the quantity covers **63.2 %** of its remaining change; after 5τ it is within
1 % of final. The exam loves the inversions: "how long to reach 63 %?" is τ
itself; "what fraction after 2τ?" is `1 − e⁻² ≈ 86.5 %`. Discharge mirrors
charge — 36.8 % remains after one τ.

**Skin effect.** At RF, current crowds into a thin outer layer of a conductor
(skin depth falls as `1/√f`). Consequences: effective resistance rises with
frequency, so losses are set by *surface* area and conductivity — which is why
silver plating, large-diameter tubing, and hollow conductors all work, and why
a conductor's DC resistance tells you little about its RF loss.

**Resonance.** For both series and parallel RLC, `f₀ = 1 / (2π√(LC))`. The R
in the question is a distractor for the *frequency* — it changes nothing — but
it is everything for Q. Practise with the **Reactance & Resonance** tool until
you can predict the crossing point before the sweep draws it. At resonance a
**series** circuit presents minimum impedance (just R, current peaks); a
**parallel** circuit presents maximum impedance (current circulates inside the
tank, line current dips).

**Q and bandwidth.** Series: `Q = X_L / R` — loss in series kills Q. Parallel:
`Q = R / X_L` — a *high* shunt resistance means little damping, so Q rises. Note
the inversion; it is the most-tested trap in the section. Bandwidth follows
directly: `BW = f₀ / Q` (the half-power, −3 dB points). A 14.1 MHz tank with
Q = 94 has a 150 kHz bandwidth; the same tank with Q = 20 is 700 kHz wide. The
**Decibel Converter** tool shows why "half power" is −3 dB and not −6.

**Phase and power factor.** In a reactive circuit, voltage and current are
displaced by `θ = arctan(X / R)`; only the in-phase component does work, so
true power is `P = E·I·cos θ`. Reactive power circulates but is not dissipated
— which is exactly why a resonant tank can carry large circulating currents on
a small supply.

Work the numbers in the drill with a calculator the first time; by the mock
exam you should be estimating orders of magnitude in your head — the
**Formula-sheet trainer** covers every expression above.
