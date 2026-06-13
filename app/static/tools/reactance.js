// reactance.js — Reactance & Resonance. Set L and C; sweep frequency. Shows
// X_L = 2πfL (rising) and X_C = 1/(2πfC) (falling), their crossing at the
// resonant frequency f0 = 1/(2π√(LC)), and the values at the chosen frequency.
"use strict";
(function () {
  const TAU = 2 * Math.PI;

  function xl(f, L) { return TAU * f * L; }            // f Hz, L H
  function xc(f, C) { return 1 / (TAU * f * C); }       // f Hz, C F
  function f0(L, C) { return 1 / (TAU * Math.sqrt(L * C)); }

  Elmer.register("reactance", function (el) {
    // state in friendly units: L in µH, C in pF, f in MHz
    const st = { L: 10, C: 100, f: 5 };

    const controls = Elmer.h("div", { class: "tool-grid" });
    const mk = (key, label, min, max, step) => {
      const inp = Elmer.h("input", {
        type: "range", min, max, step, value: st[key], class: "tool-range",
      });
      const num = Elmer.h("input", {
        type: "number", step, value: st[key], class: "tool-input mono",
      });
      const sync = (v) => { st[key] = +v; inp.value = v; num.value = v; render(); };
      inp.addEventListener("input", () => sync(inp.value));
      num.addEventListener("input", () => sync(num.value));
      controls.appendChild(
        Elmer.h("label", { class: "tool-field" }, [
          Elmer.h("span", { class: "tool-label" }, [label]),
          num, inp,
        ])
      );
    };
    mk("L", "Inductance (µH)", 0.1, 100, 0.1);
    mk("C", "Capacitance (pF)", 1, 1000, 1);
    mk("f", "Frequency (MHz)", 0.1, 30, 0.1);

    const readout = Elmer.h("div", { class: "tool-readout mono" });
    const plot = buildPlot();

    el.appendChild(controls);
    el.appendChild(readout);
    el.appendChild(plot.root);
    render();

    function render() {
      const L = st.L * 1e-6, C = st.C * 1e-12, f = st.f * 1e6;
      const XL = xl(f, L), XC = xc(f, C), fr = f0(L, C);
      readout.innerHTML =
        `X<sub>L</sub> = <b>${Elmer.fmt(XL, "Ω")}</b> &nbsp; ` +
        `X<sub>C</sub> = <b>${Elmer.fmt(XC, "Ω")}</b> &nbsp; ` +
        `resonance f₀ = <b class="accent">${Elmer.fmt(fr / 1e6, "MHz")}</b>`;
      plot.update(L, C, f, fr);
    }
  });

  // log-log plot of X_L and X_C across the HF range; mark f0 and current f.
  function buildPlot() {
    const W = 320, H = 180, padL = 8, padR = 8, padT = 10, padB = 18;
    const fMin = 0.1e6, fMax = 30e6;          // 100 kHz .. 30 MHz
    const svg = Elmer.h("svg", {
      class: "tool-svg", viewBox: `0 0 ${W} ${H}`, width: "100%", height: "auto",
      role: "img", "aria-label": "Reactance vs frequency",
    });
    const gx = (f) => padL + (Math.log10(f) - Math.log10(fMin)) /
      (Math.log10(fMax) - Math.log10(fMin)) * (W - padL - padR);
    let yMin = 1, yMax = 1e5;
    const gy = (x) => padT + (Math.log10(yMax) - Math.log10(Math.min(yMax, Math.max(yMin, x)))) /
      (Math.log10(yMax) - Math.log10(yMin)) * (H - padT - padB);

    svg.appendChild(Elmer.h("line", { x1: padL, y1: H - padB, x2: W - padR, y2: H - padB, class: "axis" }));
    const clXL = Elmer.h("polyline", { class: "curve", style: "stroke: var(--accent)" });
    const clXC = Elmer.h("polyline", { class: "curve", style: "stroke: var(--warn)" });
    const fLine = Elmer.h("line", { class: "axis", style: "stroke: var(--muted); stroke-dasharray: 3 3" });
    const fDot = Elmer.h("circle", { r: 3, style: "fill: var(--ink)" });
    const f0Line = Elmer.h("line", { class: "axis", style: "stroke: var(--accent); stroke-dasharray: 2 2" });
    svg.appendChild(clXL); svg.appendChild(clXC);
    svg.appendChild(f0Line); svg.appendChild(fLine); svg.appendChild(fDot);
    svg.appendChild(Elmer.h("text", { x: W - padR, y: H - 6, class: "svg-val", "text-anchor": "end" }, ["30 MHz"]));
    svg.appendChild(Elmer.h("text", { x: padL, y: H - 6, class: "svg-val" }, ["0.1"]));
    const lblL = Elmer.h("text", { class: "svg-val", style: "fill: var(--accent)" }, ["X_L"]);
    const lblC = Elmer.h("text", { class: "svg-val", style: "fill: var(--warn)" }, ["X_C"]);
    svg.appendChild(lblL); svg.appendChild(lblC);

    function curve(fn) {
      const pts = [];
      const steps = 60;
      for (let i = 0; i <= steps; i++) {
        const f = fMin * Math.pow(fMax / fMin, i / steps);
        pts.push(gx(f).toFixed(1) + "," + gy(fn(f)).toFixed(1));
      }
      return pts.join(" ");
    }

    function update(L, C, f, fr) {
      clXL.setAttribute("points", curve((ff) => TAU * ff * L));
      clXC.setAttribute("points", curve((ff) => 1 / (TAU * ff * C)));
      const fx = gx(Math.min(fMax, Math.max(fMin, f)));
      fLine.setAttribute("x1", fx); fLine.setAttribute("x2", fx);
      fLine.setAttribute("y1", padT); fLine.setAttribute("y2", H - padB);
      fDot.setAttribute("cx", fx); fDot.setAttribute("cy", gy(TAU * f * L));
      if (fr >= fMin && fr <= fMax) {
        const rx = gx(fr);
        f0Line.setAttribute("x1", rx); f0Line.setAttribute("x2", rx);
        f0Line.setAttribute("y1", padT); f0Line.setAttribute("y2", H - padB);
        f0Line.style.display = "";
      } else {
        f0Line.style.display = "none";
      }
      lblL.setAttribute("x", W - padR - 26); lblL.setAttribute("y", padT + 10);
      lblC.setAttribute("x", padL + 2); lblC.setAttribute("y", padT + 10);
    }
    return { root: svg, update };
  }
})();
