# Transmitters, Modulation and Processing

Nine subsections trace a signal from oscillator to antenna and then into the
modern digital modes. Learn each block's job and the one number that
characterises it.

**Oscillators.** Positive feedback through a frequency-selective network.
**Hartley** feeds back from a tap on the tank *inductor*; **Colpitts** from a
capacitive divider; **Pierce** uses a crystal as the feedback element itself.
Crystals win on stability; VFOs win on agility; a PLL synthesiser gives both.

**Power amplifiers and neutralisation.** Tuning a plate/collector tank:
dip the plate current, then load for output. A triode in **grounded-grid** has
its input at the cathode — the grid screens output from input, so it needs no
neutralisation; grid-driven stages often do. Parasitic suppressors kill VHF
oscillations in HF amplifiers. Centre-tap returns on filament transformers keep
RF off the heater.

**The two-stage CW transmitter.** Oscillator → buffer/PA. Keying the second
stage (not the oscillator) avoids chirp, because the oscillator never sees the
load change. Collector current rises when the key is down and the stage is
driven.

**SSB generation.** A **balanced modulator** multiplies audio by the carrier and
cancels the carrier by symmetry, leaving a double-sideband suppressed-carrier
signal; a crystal/mechanical filter (≈2.4 kHz) or the phasing method then
removes one sideband. Carrier suppression happens *in the modulator*, sideband
suppression *in the filter*.

**FM numbers.** Modulation index `m = deviation / modulating frequency`;
**deviation ratio** `D = max deviation / max audio frequency` (5 kHz / 3 kHz
≈ 1.67 for narrow-band FM). Occupied bandwidth by Carson's rule is
`2 × (deviation + highest audio)`. A reactance modulator varies a tank's
effective capacitance; a phase modulator followed by audio pre-emphasis
produces the same result.

**Intermodulation.** Two transmitters mixing in a nonlinear stage produce
`2f₁ − f₂` and `2f₂ − f₁` (third-order) products that land in-band. Cure it with
isolators/circulators, cavity filters, and keeping transmitters off shared
antennas — not with more power.

**Speech processing.** **Compression** raises average power relative to PEP by
levelling the audio; **clipping** does it harder and needs filtering. Push it
too far and you add distortion and splatter. ALC keeps the PA out of
flat-topping.

**Digital modes.** Codes with unequal-length elements (Morse, Baudot/varicode)
versus fixed-length (ASCII). The OSI model layers the stack; packet uses
**AX.25** and a **CRC** to detect errors (not correct them — that is ARQ or
forward error correction). Know the differences in bandwidth and throughput
among RTTY, PSK31, FT8, packet.

**Spread spectrum.** **Direct sequence** multiplies the data by a fast
pseudo-random code, spreading the signal across the band; **frequency hopping**
jumps the carrier among channels on a schedule. Both make the signal look like
noise to a receiver without the code, and both are permitted only where the
regulations allow.
