# Station Assembly, Practice and Safety

This section asks you to read a station as a **block diagram** and to work
safely. Picture the signal path: a receiver chain (antenna → RF amp → mixer +
local oscillator → IF filter/amp → detector → audio), and a transmitter chain
(oscillator → buffer → multiplier/mixer → driver → power amplifier → antenna),
sharing the antenna through a transmit/receive switch.

**Modulation.** Carrying information means varying the carrier: **AM** varies
amplitude; **SSB** transmits just one sideband with the carrier suppressed, so
it's power-efficient and narrow (the HF voice workhorse); **FM** varies frequency
and trades bandwidth for noise immunity (the VHF/UHF voice standard); phase
modulation is a close cousin of FM. Digital modes (RTTY, packet, and modern
soundcard modes) key the carrier with data.

**Power.** Regulated supplies convert AC mains to clean DC and hold voltage
steady under load. Batteries store DC; know the trade-offs and that charging
lead-acid releases hydrogen, so ventilate.

**Safety is the priority topic here.** Respect **RF exposure** limits — keep
antennas clear of people and don't transmit high power into an antenna someone is
touching. For **electrical safety**, the danger is current through the body;
mains and high-voltage supplies can kill, so de-energize before working and
respect the chassis. **Ground** your equipment and install **lightning**
protection (a disconnect and a single-point ground) — bonding everything to one
ground point prevents dangerous potential differences.
