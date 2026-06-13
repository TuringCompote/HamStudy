// swr.js — SWR & impedance match. Enter a load (R + optional reactance X) and the
// line impedance Z0; see the reflection coefficient, SWR, reflected power %, and
// return loss. A bar shows how much power is delivered vs reflected.
"use strict";
(function () {
  Elmer.register("swr", function (el) {
    const st = { R: 50, X: 0, Z0: 50 };

    const grid = Elmer.h("div", { class: "tool-grid" });
    const mk = (key, label) => {
      const inp = Elmer.h("input", { type: "number", step: "any", class: "tool-input mono", value: st[key] });
      inp.addEventListener("input", () => { st[key] = parseFloat(inp.value); render(); });
      grid.appendChild(Elmer.h("label", { class: "tool-field" }, [
        Elmer.h("span", { class: "tool-label" }, [label]), inp]));
    };
    mk("R", "Load R (Ω)");
    mk("X", "Load X (Ω, ±)");
    mk("Z0", "Line Z₀ (Ω)");

    const readout = Elmer.h("div", { class: "tool-readout mono" });
    const bar = Elmer.h("div", { class: "swr-bar" });
    const barFwd = Elmer.h("div", { class: "swr-seg fwd" });
    const barRef = Elmer.h("div", { class: "swr-seg ref" });
    bar.appendChild(barFwd); bar.appendChild(barRef);
    const barLbl = Elmer.h("div", { class: "tool-note small muted" });

    el.appendChild(grid);
    el.appendChild(readout);
    el.appendChild(bar);
    el.appendChild(barLbl);
    render();

    function render() {
      const { R, X, Z0 } = st;
      if (!isFinite(R) || !isFinite(Z0) || Z0 <= 0 || R < 0) {
        readout.textContent = "Enter R ≥ 0 and Z₀ > 0.";
        return;
      }
      const x = isFinite(X) ? X : 0;
      // Γ = (ZL - Z0)/(ZL + Z0), ZL = R + jX, Z0 real
      const nRe = R - Z0, nIm = x;
      const dRe = R + Z0, dIm = x;
      const den = dRe * dRe + dIm * dIm;
      const gRe = (nRe * dRe + nIm * dIm) / den;
      const gIm = (nIm * dRe - nRe * dIm) / den;
      const gMag = Math.hypot(gRe, gIm);
      const swr = gMag >= 1 ? Infinity : (1 + gMag) / (1 - gMag);
      const reflPct = gMag * gMag * 100;
      const rl = gMag > 0 ? -20 * Math.log10(gMag) : Infinity;

      readout.innerHTML =
        `SWR = <b class="accent">${swr === Infinity ? "∞" : (Math.round(swr * 100) / 100) + ":1"}</b> &nbsp; ` +
        `|Γ| = <b>${Math.round(gMag * 1000) / 1000}</b> &nbsp; ` +
        `reflected = <b>${Math.round(reflPct * 10) / 10}%</b> &nbsp; ` +
        `return loss = <b>${rl === Infinity ? "∞" : Math.round(rl * 10) / 10 + " dB"}</b>`;

      const fwd = 100 - reflPct;
      barFwd.style.width = fwd + "%";
      barRef.style.width = reflPct + "%";
      barLbl.innerHTML = `delivered ${Math.round(fwd * 10) / 10}% &nbsp;|&nbsp; reflected ${Math.round(reflPct * 10) / 10}%` +
        (Math.abs(st.R - st.Z0) < 1e-9 && x === 0 ? " &nbsp;— perfect match" : "");
    }
  });
})();
