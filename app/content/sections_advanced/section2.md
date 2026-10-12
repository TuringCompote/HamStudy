# Advanced Components and Circuits

This is the largest Advanced section (132 questions, 12 subsections) and it is
mostly *device behaviour*: what a part does, which terminal is which, and what
sets a stage's gain or impedance. Build a mental catalogue, one family at a time.

**Semiconductor materials.** Silicon and germanium sit between metals and
insulators; **doping** with donors (N-type, extra electrons) or acceptors
(P-type, holes) sets the carrier type. Gallium arsenide earns its place at
microwave frequencies because carriers move faster in it. "Fewer free electrons
than pure silicon" describes P-type.

**Diodes.** The ones the exam names: **Zener** (reverse-breakdown at a designed
voltage → references and clamps), **varactor** (reverse-biased junction whose
capacitance tracks voltage → electronic tuning), **Schottky / hot-carrier**
(metal–semiconductor, no minority-carrier storage → fast mixers and detectors,
low forward drop), **PIN** (an intrinsic layer makes it an RF-controlled
resistor → switches and attenuators), **tunnel** (negative resistance). Also
know the **point-contact** and **LED** basics, and reverse-recovery as the
limit on switching speed.

**Bipolar transistors.** `α = I_C / I_E` (a hair under 1) and `β = I_C / I_B`
(tens to hundreds); `β = α / (1 − α)`. NPN conducts from a positive collector
to a negative emitter; PNP the reverse. Saturation, cutoff and the active
region map onto switch-closed, switch-open and amplifier.

**FETs.** A JFET or depletion-mode MOSFET conducts with zero gate voltage and
is pinched off by reverse bias; an **enhancement-mode** MOSFET is off until the
gate is driven past threshold. Gate input impedance is enormous — which is
exactly why MOSFET gates carry built-in Zener protection against static.

**Thyristors.** An SCR has anode, cathode and gate; once triggered it latches
on until anode current falls below the holding value. A triac does it for both
polarities. The physics is a PNP–NPN regenerative pair.

**Amplifier classes.** Conduction angle decides class and efficiency: **A**
(360°, most linear, ~25–50 % efficient), **AB** (a bit over 180° — the SSB
linear-amplifier choice), **B** (180°, push-pull), **C** (well under 180°,
highest efficiency, CW/FM only — it needs a tank to restore the sine). The
**Series / Parallel R & C** tool is a good refresher for the bias networks.

**Stages, impedances and op-amps.** A common-source FET's input impedance is set
by its gate bias network; its output impedance by the drain load. Darlington
pairs multiply β at the cost of a doubled base–emitter drop. An **op-amp** is a
very-high-gain differential amplifier; closed-loop gain is set only by the
feedback network (`A_v = −R_f / R_in` inverting, `1 + R_f / R_in`
non-inverting).

**Mixers, logic and filters.** A mixer multiplies two inputs and outputs the
sum and difference (plus the originals); overdrive it and you get spurious
products. Gates: AND, OR, NAND, NOR, XOR — write out the four-row truth table
rather than memorising sentences. Filters: Butterworth (flat passband,
gradual rolloff), Chebyshev (ripple traded for a steeper skirt), elliptic
(ripple in both bands, steepest), and crystal-lattice filters whose bandwidth is
set by the crystal spacing — ~2.4 kHz for SSB, ~500 Hz for CW.
