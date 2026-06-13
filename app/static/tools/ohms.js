// ohms.js — Ohm's Law & Power. Enter any TWO of V, I, R, P; the tool solves the
// other two and shows which formula it used. Themes from tokens.css.
"use strict";
(function () {
  const FIELDS = [
    { k: "V", label: "Voltage", unit: "V" },
    { k: "I", label: "Current", unit: "A" },
    { k: "R", label: "Resistance", unit: "Ω" },
    { k: "P", label: "Power", unit: "W" },
  ];

  // solver: given exactly two known keys -> {values, formulas}
  function solve(known) {
    const { V, I, R, P } = known;
    const has = (a, b) => a in known && b in known;
    let v = V, i = I, r = R, p = P;
    const f = {};
    if (has("V", "I")) { r = V / I; p = V * I; f.R = "R = V / I"; f.P = "P = V · I"; }
    else if (has("V", "R")) { i = V / R; p = (V * V) / R; f.I = "I = V / R"; f.P = "P = V² / R"; }
    else if (has("V", "P")) { i = P / V; r = (V * V) / P; f.I = "I = P / V"; f.R = "R = V² / P"; }
    else if (has("I", "R")) { v = I * R; p = I * I * R; f.V = "V = I · R"; f.P = "P = I² · R"; }
    else if (has("I", "P")) { v = P / I; r = P / (I * I); f.V = "V = P / I"; f.R = "R = P / I²"; }
    else if (has("R", "P")) { v = Math.sqrt(P * R); i = Math.sqrt(P / R); f.V = "V = √(P · R)"; f.I = "I = √(P / R)"; }
    return { values: { V: v, I: i, R: r, P: p }, formulas: f };
  }

  Elmer.register("ohms", function (el) {
    const recent = []; // keys edited, most-recent last (max 2 used)
    const inputs = {};

    const grid = Elmer.h("div", { class: "tool-grid" });
    FIELDS.forEach((fd) => {
      const inp = Elmer.h("input", {
        type: "number", step: "any", inputmode: "decimal",
        class: "tool-input mono", placeholder: "—",
      });
      inputs[fd.k] = inp;
      inp.addEventListener("input", () => onEdit(fd.k));
      grid.appendChild(
        Elmer.h("label", { class: "tool-field" }, [
          Elmer.h("span", { class: "tool-label" }, [`${fd.label} (${fd.unit})`]),
          inp,
        ])
      );
    });

    const note = Elmer.h("div", { class: "tool-note muted small" }, [
      "Enter any two values.",
    ]);
    const svg = buildCircuit();

    el.appendChild(grid);
    el.appendChild(svg.root);
    el.appendChild(note);

    function onEdit(k) {
      const val = parseFloat(inputs[k].value);
      const i = recent.indexOf(k);
      if (i !== -1) recent.splice(i, 1);
      if (inputs[k].value !== "" && isFinite(val)) recent.push(k);
      // keep only the two most-recent edited-with-values as knowns
      while (recent.length > 2) {
        const drop = recent.shift();
        // leave the user's text alone; just stop treating it as known
      }
      recompute();
    }

    function recompute() {
      const knownKeys = recent.slice(-2);
      // clear computed (non-known) display styling
      FIELDS.forEach((fd) => inputs[fd.k].classList.remove("computed"));
      if (knownKeys.length < 2) {
        note.textContent = "Enter any two values.";
        svg.update(null);
        return;
      }
      const known = {};
      let bad = false;
      knownKeys.forEach((k) => {
        const v = parseFloat(inputs[k].value);
        if (!isFinite(v)) bad = true;
        known[k] = v;
      });
      if (bad) return;
      const { values, formulas } = solve(known);
      FIELDS.forEach((fd) => {
        if (!knownKeys.includes(fd.k)) {
          inputs[fd.k].value = round(values[fd.k]);
          inputs[fd.k].classList.add("computed");
        }
      });
      note.innerHTML =
        "Using <strong>" + knownKeys.join(" &amp; ") + "</strong> &nbsp;·&nbsp; " +
        Object.values(formulas).map((s) => `<span class="mono">${s}</span>`).join(" &nbsp; ");
      svg.update(values);
    }

    function round(x) {
      if (!isFinite(x)) return "";
      const a = Math.abs(x);
      if (a !== 0 && (a < 1e-3 || a >= 1e6)) return x.toExponential(3);
      return Math.round(x * 1e4) / 1e4;
    }
  });

  // simple series loop: source (V) drives current (I) through resistor (R),
  // dissipating power (P). Labels update live.
  function buildCircuit() {
    const W = 300, H = 150;
    const svg = Elmer.h("svg", {
      class: "tool-svg", viewBox: `0 0 ${W} ${H}`, width: "100%", height: "auto",
      role: "img", "aria-label": "Series circuit: source, current, resistor",
    });
    const wire = (x1, y1, x2, y2) =>
      Elmer.h("line", { x1, y1, x2, y2, class: "wire" });
    svg.appendChild(wire(60, 30, 240, 30));
    svg.appendChild(wire(240, 30, 240, 120));
    svg.appendChild(wire(240, 120, 60, 120));
    svg.appendChild(wire(60, 120, 60, 30));
    // source on the left
    svg.appendChild(Elmer.h("circle", { cx: 60, cy: 75, r: 16, class: "node" }));
    const vlab = Elmer.h("text", { x: 60, y: 79, class: "svg-val", "text-anchor": "middle" }, ["V"]);
    svg.appendChild(vlab);
    // resistor on the right
    svg.appendChild(Elmer.h("rect", { x: 224, y: 55, width: 32, height: 40, rx: 4, class: "node" }));
    const rlab = Elmer.h("text", { x: 240, y: 110, class: "svg-val", "text-anchor": "middle" }, ["R"]);
    svg.appendChild(rlab);
    // current label (top wire) + power label (center)
    const ilab = Elmer.h("text", { x: 150, y: 22, class: "svg-val", "text-anchor": "middle" }, ["I"]);
    svg.appendChild(ilab);
    const plab = Elmer.h("text", { x: 150, y: 79, class: "svg-val accent", "text-anchor": "middle" }, ["P"]);
    svg.appendChild(plab);

    function update(v) {
      if (!v) { vlab.textContent = "V"; ilab.textContent = "I"; rlab.textContent = "R"; plab.textContent = "P"; return; }
      vlab.textContent = Elmer.fmt(v.V, "V");
      ilab.textContent = Elmer.fmt(v.I, "A");
      rlab.textContent = Elmer.fmt(v.R, "Ω");
      plab.textContent = Elmer.fmt(v.P, "W");
    }
    return { root: svg, update };
  }
})();
