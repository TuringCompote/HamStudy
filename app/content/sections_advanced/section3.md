# Measurements

Measurement questions are small calculations wrapped around one instrument
fact. Know what each instrument *fundamentally* measures and the conversions
that follow.

**Sine-wave amplitudes.** An oscilloscope shows **peak-to-peak** directly — that
is the easy dimension. From there: `V_peak = V_pp / 2`, `V_rms = 0.707 × V_peak`
(= `V_peak / √2`), `V_avg = 0.637 × V_peak` over a half cycle. RMS is the value
that delivers the same heating as DC, which is why power formulas assume it.

**PEP.** Peak envelope power is the average power during one RF cycle at the
*crest* of the modulation envelope: `PEP = (V_peak / √2)² / R = V_pp² / (8R)`
into the load. On a scope across a 50 Ω dummy load, 200 V peak-to-peak is
`200² / 400 = 100 W` PEP. For an unmodulated carrier or key-down CW, PEP equals
average power; for SSB voice the average is a fraction of PEP.

**Dip meter.** A tunable oscillator whose coil you couple to a circuit under
test; when the meter's frequency hits the circuit's resonance, energy is
absorbed and the grid/gate current **dips**. Uses: find a tank's or antenna's
resonant frequency, check a trap, measure an unknown L or C against a known
partner — all with the device *unpowered*. Couple loosely; tight coupling pulls
the reading.

**Frequency counter.** It counts cycles over a gate time set by an internal
timebase. Accuracy is the timebase's accuracy (and its temperature stability);
resolution improves with a longer gate; the input stage's bandwidth limits the
top frequency. Improve accuracy with an oven-controlled or GPS-disciplined
reference.

**Oscilloscope.** Vertical amplifier bandwidth limits what you can see
faithfully (a rule of thumb: bandwidth ≥ 5× the signal's fundamental for a
clean square wave). Feed a signal to the horizontal input and another to the
vertical and you get a **Lissajous** figure — the pattern's loop ratio gives the
frequency ratio, so 100 Hz vs 200 Hz draws a figure with a 1:2 count of
crossings. Use a 10:1 probe to lighten circuit loading.

**Meter movements.** A moving-coil meter is a current device with an internal
resistance. To make a **voltmeter**, add a series multiplier:
`R_mult = V_fs / I_fs − R_m`. To make an **ammeter** of larger range, add a
**shunt** carrying the excess: `R_sh = I_fs × R_m / (I_total − I_fs)`. Sensitivity
in ohms-per-volt is `1 / I_fs` — a 40 µA movement is a 25 kΩ/V meter, and the
"ohms per volt" number tells you how much the meter loads the circuit. The
**Ohm's Law & Power** tool on section 1 is the fastest way to sanity-check these
divider sums.
