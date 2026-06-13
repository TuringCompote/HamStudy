"""Curated Basic-exam formula set for the formula-sheet trainer.

The real exam permits the ISED **unlabelled** formula/diagram sheet, so the skill
to train is: recognize an unlabelled formula and know what it computes (and the
reverse). Formulas are facts; the descriptions here are original (constitution §3).
`finds` = plain-language quantity it gives you; `formula` = the expression as it
appears (unlabelled) on the sheet; `vars` = what each symbol means.
"""
from __future__ import annotations

FORMULAS: list[dict] = [
    {"id": "ohm", "section": 5, "finds": "Voltage from current and resistance",
     "formula": "V = I × R", "vars": "V volts · I amps · R ohms"},
    {"id": "power", "section": 5, "finds": "Power from voltage and current",
     "formula": "P = V × I", "vars": "P watts · V volts · I amps"},
    {"id": "power_ir", "section": 5, "finds": "Power from current and resistance",
     "formula": "P = I² × R", "vars": "P watts · I amps · R ohms"},
    {"id": "power_vr", "section": 5, "finds": "Power from voltage and resistance",
     "formula": "P = V² / R", "vars": "P watts · V volts · R ohms"},
    {"id": "r_series", "section": 5, "finds": "Total resistance in series",
     "formula": "R = R₁ + R₂ + …", "vars": "resistances add directly"},
    {"id": "r_parallel", "section": 5, "finds": "Total resistance in parallel",
     "formula": "1/R = 1/R₁ + 1/R₂ + …", "vars": "result is below the smallest branch"},
    {"id": "c_parallel", "section": 5, "finds": "Total capacitance in parallel",
     "formula": "C = C₁ + C₂ + …", "vars": "capacitors add in parallel (opposite of resistors)"},
    {"id": "c_series", "section": 5, "finds": "Total capacitance in series",
     "formula": "1/C = 1/C₁ + 1/C₂ + …", "vars": "below the smallest branch"},
    {"id": "xc", "section": 5, "finds": "Capacitive reactance",
     "formula": "X_C = 1 / (2πfC)", "vars": "X_C ohms · f hertz · C farads — falls as f rises"},
    {"id": "xl", "section": 5, "finds": "Inductive reactance",
     "formula": "X_L = 2πfL", "vars": "X_L ohms · f hertz · L henries — rises as f rises"},
    {"id": "resonance", "section": 5, "finds": "Resonant frequency of an LC circuit",
     "formula": "f = 1 / (2π√(LC))", "vars": "f hertz · L henries · C farads (where X_L = X_C)"},
    {"id": "db_power", "section": 5, "finds": "Decibels from a power ratio",
     "formula": "dB = 10 × log₁₀(P₂/P₁)", "vars": "3 dB ≈ ×2 power · 10 dB = ×10"},
    {"id": "db_volt", "section": 5, "finds": "Decibels from a voltage ratio",
     "formula": "dB = 20 × log₁₀(V₂/V₁)", "vars": "voltage uses 20·log, power uses 10·log"},
    {"id": "rms", "section": 5, "finds": "RMS voltage from peak",
     "formula": "V_rms = V_peak / √2", "vars": "≈ 0.707 × peak (sine wave)"},
    {"id": "period", "section": 5, "finds": "Frequency from period (or vice-versa)",
     "formula": "f = 1 / T", "vars": "f hertz · T seconds"},
    {"id": "time_const", "section": 5, "finds": "RC time constant",
     "formula": "τ = R × C", "vars": "τ seconds · R ohms · C farads (≈63% charge in 1τ)"},
    {"id": "turns", "section": 4, "finds": "Transformer voltage from the turns ratio",
     "formula": "V_p / V_s = N_p / N_s", "vars": "primary/secondary volts ∝ turns"},
    {"id": "wavelength", "section": 6, "finds": "Wavelength from frequency",
     "formula": "λ = 300 / f", "vars": "λ metres · f megahertz"},
    {"id": "dipole", "section": 6, "finds": "Length of a half-wave dipole",
     "formula": "ℓ ≈ 143 / f", "vars": "ℓ metres · f MHz (≈95% of ½λ for wire)"},
    {"id": "vertical", "section": 6, "finds": "Length of a quarter-wave vertical",
     "formula": "ℓ ≈ 71 / f", "vars": "ℓ metres · f MHz"},
    {"id": "swr", "section": 6, "finds": "SWR from the reflection coefficient",
     "formula": "SWR = (1 + |Γ|) / (1 − |Γ|)", "vars": "1:1 is a perfect match"},
]
