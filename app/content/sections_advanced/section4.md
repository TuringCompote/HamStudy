# Power Supplies

Four subsections, one story: rectify, filter, regulate, protect. The exam
mostly asks you to compare topologies — which rectifier, which filter, which
regulator — and to reason about ripple, regulation and dissipation.

**Rectifiers.** Half-wave uses one diode, conducts on one half cycle, and
leaves ripple at the line frequency (60 Hz) — the lowest average output and the
hardest to filter. Full-wave centre-tap uses two diodes and a centre-tapped
secondary; each diode sees **twice** the output peak as reverse voltage (PIV).
The bridge uses four diodes, no centre tap, and each diode's PIV is only the
output peak. Both full-wave forms give **120 Hz** ripple, double the frequency,
so the filter has an easier job. For a given secondary voltage the bridge gives
the highest average DC.

**Filters.** A **capacitor-input** filter charges to the peak (`1.414 × V_rms`
minus diode drops), so it yields the highest voltage but the worst regulation
and large, short charging-current pulses. A **choke-input** filter averages the
waveform (≈0.9 × V_rms for full-wave), gives better regulation and gentler
diode current, at the cost of a lower output. Chokes are rated by inductance
*and* the DC current they carry without saturating. A **bleeder resistor** across
the output discharges the capacitors for safety and sets a minimum load that
steadies the choke-input filter.

**Regulators.** A **linear** regulator (series pass transistor, Zener or
band-gap reference) controls the output by dropping the excess voltage across
the pass element — quiet, simple, but it dissipates `(V_in − V_out) × I_load` as
heat. A **switching** regulator chops the input at tens to hundreds of kHz and
filters the result; efficiency is high and heat is low, but it generates RF
noise that needs shielding and filtering in a radio installation. A **shunt**
regulator (plain Zener plus series resistor) burns power whether the load needs
it or not. Regulation is specified as the output change from no load to full
load; **dynamic (output) resistance** is that change divided by the current
change.

**Protection and the numbers.** Crowbar circuits (an SCR that shorts the output
on overvoltage) protect the load; fuses and foldback limiting protect the
supply. Pass-transistor dissipation is the question that catches people:
a 13.8 V supply fed from 20 V delivering 10 A dissipates `(20 − 13.8) × 10 = 62 W`
in the pass device — size the heatsink for that, not for the output power.
Transformer **inrush** and the capacitor's **ripple-current** rating finish the
design.
