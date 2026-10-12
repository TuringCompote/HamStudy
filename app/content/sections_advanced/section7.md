# Feedlines — Matching and Antenna Systems

The Advanced antenna section is about **impedance**: what an antenna presents,
how a feedline transforms it, and how matching networks bring the two
together. The **SWR & Impedance Match** and **Wavelength ↔ Frequency** tools
cover most of the arithmetic.

**Antenna tuners.** A **transformer** type (balun or toroidal transformer)
changes impedance by the square of the turns ratio and handles a limited range;
a **series** type adds a reactance to cancel the antenna's; an **L** network
(one series, one shunt element) matches a wide range but only one way round
for step-up versus step-down; **T** and **π** networks match almost anything at
the cost of higher loss when mistuned.

**Transmission-line transformers.** A **quarter-wave** line inverts: a short
looks like an open, an open like a short, and any load Z_L appears as
`Z_in = Z₀² / Z_L`. Choose `Z₀ = √(Z_in × Z_L)` and a quarter-wave section is a
matching transformer. A **half-wave** line repeats the load impedance exactly.
Remember **velocity factor**: a quarter-wave of coax is `0.25 × λ × VF` long
(≈0.66 for solid dielectric, ≈0.8 for foam). Stubs — shorted or open sections
— provide pure reactance for matching and filtering.

**Feed-point matching.** **Delta** match (spread feeders attached out along a
dipole), **gamma** match (unbalanced; coax braid at the centre, inner
conductor via a series capacitor to a tap), **T** match (the balanced version),
**hairpin/beta** match (a shunt inductor across a shortened element), and the
**stub** match. A **balun** converts balanced to unbalanced and may transform
impedance (1:1 or 4:1).

**Current, voltage and radiation resistance.** On a half-wave dipole, current is
highest at the centre and zero at the ends; voltage is the opposite. Feed at
the centre for a low (≈73 Ω) impedance, at the end for a high one. **Radiation
resistance** is the fictitious resistance that would dissipate the radiated
power at the feed-point current; efficiency is
`R_rad / (R_rad + R_loss)`. It depends on antenna length relative to wavelength,
height above ground, and surroundings — short antennas have low R_rad, which is
why their loss resistance matters so much.

**Polarisation.** Crossed dipoles fed 90° apart produce **circular**
polarisation; helical antennas do it natively. Linear antennas lose ~3 dB to a
circular signal, and cross-polarised linear antennas lose far more. Satellite
work is where this matters.

**Power, loss and ERP.** Feedline loss grows with frequency and length and
**rises further with SWR** because reflected power makes extra trips. Convert
everything to dB: `ERP = P_out − line loss + antenna gain (dBd)`; add 2.15 dB to
get EIRP referenced to isotropic. A 100 W transmitter, 3 dB of loss and a 6 dBd
antenna gives 200 W ERP.

**Patterns, ground and waveguide.** Yagi gain comes from parasitic elements; the
E-plane of a horizontal Yagi is horizontal; ground reflections form the
vertical pattern, with the effective reflecting plane below the physical
surface. **Waveguide** carries microwave energy with very low loss; it is a
high-pass structure with a cutoff frequency set by its width, impractical below
the GHz range, and must be kept dry and clean.
