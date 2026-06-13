# Feedlines and Antenna Systems

Getting power from the transmitter to the air efficiently is the theme here, and
two tools below make the key relationships tangible.

**Feedlines and characteristic impedance.** A transmission line has a
**characteristic impedance** (Z₀) set by its geometry — commonly 50 Ω coax in
amateur gear. Power flows with least loss when the line is terminated in its Z₀.
Coax is **unbalanced**; antennas like dipoles are **balanced**, so a **balun**
matches the two and keeps current off the coax shield. Every line has **loss**
that rises with frequency and length.

**Standing waves and SWR.** When the load impedance doesn't equal Z₀, some power
**reflects** back, and the forward and reflected waves form a standing-wave
pattern. **SWR** measures the mismatch: 1:1 is perfect, higher means more
reflected power and more loss on a lossy line (and a transmitter that may fold
back power). A matching network or tuner transforms the load back toward Z₀. The
**SWR & Impedance Match** tool shows mismatch → SWR → reflected power.

**Antennas and wavelength.** Antennas are sized in **wavelengths**:
`λ(m) = 300 / f(MHz)`. A **½λ dipole** is the reference; a **¼λ vertical** works
against ground. Physical length runs a few percent shorter than the free-space
figure because of end effects (a **velocity/shortening factor**). Antennas have
**gain**, **directivity**, a radiation **pattern**, **polarization** (orientation
of the E-field), and **bandwidth**. The **Wavelength ↔ Frequency** tool converts
f ↔ λ and sizes dipoles and verticals.
