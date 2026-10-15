# Receivers

The receiver section is the superheterodyne, inside and out: why it converts,
how it selects, where its limits come from, and what the symptoms of each
weakness look like on the air.

**Why convert?** Mixing the incoming signal with a local oscillator moves it to
a fixed **intermediate frequency** where a single, well-designed filter and
amplifier chain can do all the selectivity and gain. Converting is what makes
constant selectivity across a wide tuning range possible. The IF is chosen as a
compromise: high enough for **image rejection**, low enough for sharp, cheap
filters — which is exactly why **double conversion** exists (a high first IF
for images, a low second IF for selectivity).

**The mixer and its oscillators.** The first mixer combines signal and LO to
produce sum and difference frequencies; the IF filter keeps one. For SSB and
CW the **BFO** (beat-frequency oscillator) reinserts a carrier at the detector,
and a **product detector** multiplies the IF signal by it to recover audio. AM
uses an envelope detector; FM uses a discriminator or ratio detector after a
**limiter**, then **de-emphasis** to undo the transmitter's pre-emphasis.

**Gain distribution and noise.** The receiver's **noise floor** is set by its
own front end (thermal noise, `kTB`, plus the RF stage's noise figure). Put
only as much gain in the RF stage as needed to override mixer noise — too much
and strong signals overload the mixer, producing intermod. The first IF stage
provides the bulk of the gain and the selectivity; **AGC** holds the audio
level roughly constant as signals vary.

**Selectivity and its failures.** **Image response**: a signal at
`f_signal ± 2 × IF` also mixes to the IF; the front-end preselector (before the
mixer) is what rejects it. **Desensitisation** (blocking): a strong adjacent
signal drives the front end into gain compression, so weak signals vanish —
narrow the front-end bandwidth or attenuate. **Cross-modulation**: the strong
signal's modulation gets stamped onto the wanted one. **Intermodulation**:
two strong signals create in-band products. Distortion that appears only on
strong signals points at overload, not a broken detector. The **dynamic range**
of the receiver spans from the noise floor to the onset of these effects.

**Shaping the sound.** Noise blankers gate out impulse noise before the narrow
IF filter rings; notch filters (IF or audio) remove a heterodyne; passband
tuning slides the IF window; a DSP noise reducer works on the audio. Each has a
cost — a noise blanker on a busy band creates its own intermod — so the exam
asks *when* as much as *what*.

Everything here is quantitative in dB: sensitivity, image rejection, blocking
dynamic range. The **Decibel Converter** tool keeps those ratios honest.
